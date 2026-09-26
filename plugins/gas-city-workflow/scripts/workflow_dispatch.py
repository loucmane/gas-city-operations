"""The `dispatch` coordination action: route a child `<W>` created (ga-fsfg R4).

`<W>` never routes a Bead it owns. Every owned Bead carries the external-owner binding,
and `require_external_candidate` refuses routing metadata on it, so a routed owned Bead
would fail every later ownership check at `<W>`. Only the child of a verified `create`
record in `<W>`'s journal qualifies, and `<W>` does not own it.

The executor reads the orchestrator profile through the gate's own validated loader,
so the gate and the executor judge the same bytes. Every live gc read runs here, under
the repository lock, with a fixed environment, a 30 s timeout and an output cap. Each
sling attempt is first stamped in the journal (`last_sling_at`), and another attempt
waits at least 60 s from the latest stamp. A pending dispatch is completed only by its
exact request; nothing retries on its own.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from project_context import GC
from workflow_common import (
    BEAD_PATTERN,
    OPERATOR_PATH,
    CommandRunner,
    WorkflowError,
    atomic_write_json,
    load_journal,
    parse_bead_readback,
    result_payload,
    workflow_runtime_root,
)
from workflow_ownership import NATIVE_KEYS, OWNER_KEY, bead_digest, check_active_ownership
from workflow_portable import load_shared_runtime
from workflow_snapshots import resolve_snapshot, store_snapshot

ACTION = "dispatch"
# The reviewed ga-6utp gc environment (pins.json `env`); nothing else is inherited.
ENVIRONMENT = {
    "HOME": "/home/loucmane",
    "PATH": OPERATOR_PATH,
    "GC_HOME": "/home/loucmane/gascity/home",
    "GIT_OPTIONAL_LOCKS": "0",
    "BD_DISABLE_METRICS": "1",
    "LANG": "C",
}
TIMEOUT = 30
# Checked after capture: the caps bound what is accepted, the timeout bounds the wait.
OUTPUT_CAP = 1024 * 1024
READY_CAP = 16 * 1024 * 1024
RESLING_AFTER = timedelta(seconds=60)
# What a pool claim may add or change, as observed live in the ga-x7lx window
# (2026-09-26). Core writes the rig checkout's branch to gc.work_branch (ga-l7gz).
CLAIM_FIELDS = frozenset({"status", "assignee", "updated_at", "started_at"})
CLAIM_METADATA = frozenset({"gc.session_id", "gc.session_name", "gc.work_branch"})
ROUTING_MARKERS = ("work_pack", "work-pack", "workpack", "workspace")
ROUTE_LABELS = ("pool:", "agent:", "session:", "route:")
_MISSING = object()


def _clock() -> datetime:
    return datetime.now(UTC)


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _runtime_seat() -> Path:
    """The canonical root of the runtime this executor runs from (Git common dir's parent)."""

    from aegis_foundation.gate.hooks.delegation import _worktree_and_canonical_root

    return _worktree_and_canonical_root(workflow_runtime_root())[1]


def load_profile(seat: Path | None = None) -> dict[str, Any]:
    """The gate's validated profile at the canonical seat; `seat` is injectable for tests."""

    try:
        load_shared_runtime()
        from aegis_foundation.gate.hooks.native_permissions import _profile

        root = _runtime_seat() if seat is None else seat
        profile = _profile(root)
    except Exception as exc:  # noqa: BLE001 - ValueError, DelegationPolicyError, OSError ...
        raise WorkflowError(f"dispatch cannot load the orchestrator profile: {exc}") from exc
    if profile is None:
        raise WorkflowError("dispatch requires the orchestrator command profile")
    if str(root) != profile["canonical_root"]:
        raise WorkflowError("dispatch profile does not belong to the canonical runtime")
    return profile


def preflight(
    context: Mapping[str, Any],
    spec: Any,
    journal: Mapping[str, Any],
    bead_id: str,
    target: str,
    *,
    seat: Path | None = None,
) -> dict[str, Any]:
    """The local dispatch checks, run for every dispatch request before the replay lookup."""

    profile = load_profile(seat)
    workflow = context["workflow"]
    if workflow["city"] != profile["city"] or workflow["rig"] != profile["rig"]:
        raise WorkflowError("dispatch city and rig must equal the orchestrator profile's")
    if (
        context["project"]["id"] != profile["project_id"]
        or spec.project_id != profile["project_id"]
        or context["workspace"]["canonical_root"] != profile["canonical_root"]
        or Path(context["project"]["root"]).parent != Path(profile["worktree_root"])
    ):
        raise WorkflowError(
            "dispatch requires an Operations worktree; registered and review projects refuse"
        )
    child_checks(journal, [spec.bead_id, *journal.get("attached_bead_ids", [])], bead_id)
    target_checks(profile, target)
    return profile


def child_checks(journal: Mapping[str, Any], owned: list[str], bead_id: str) -> None:
    """A dotted child of an owned Bead, produced by a verified `create` record. Journal reads."""

    if not BEAD_PATTERN.fullmatch(bead_id) or bead_id in owned:
        raise WorkflowError("dispatch routes a child, never an owned or malformed Bead")
    if not any(bead_id.startswith(parent + ".") for parent in owned):
        raise WorkflowError("dispatch Bead is not a dotted child of an owned Bead")
    records = journal.get("coordination", {})
    if not isinstance(records, dict) or not any(
        isinstance(record, dict)
        and record.get("state") == "verified"
        and isinstance(record.get("request"), dict)
        and record["request"].get("action") == "create"
        and record.get("result_bead") == bead_id
        for record in records.values()
    ):
        raise WorkflowError("dispatch Bead has no verified create record in this journal")


def target_checks(profile: Mapping[str, Any], target: str) -> None:
    if ACTION not in profile["commands"]:
        raise WorkflowError("dispatch is not opted into by the orchestrator profile")
    if target not in profile.get("dispatch_targets", []):
        raise WorkflowError("dispatch target is not listed in dispatch_targets")
    preroute = profile.get("preroute_targets")
    if not isinstance(preroute, list) or not preroute:
        raise WorkflowError("dispatch requires a non-empty preroute_targets list")
    if target in preroute:
        raise WorkflowError("dispatch target is routed only by its reviewed window package")


def pending_dispatch(operations: Mapping[str, Any]) -> bool:
    return any(
        isinstance(record, dict)
        and record.get("state") == "pending"
        and isinstance(record.get("request"), dict)
        and record["request"].get("action") == ACTION
        for record in operations.values()
    )


def _gc(runner: CommandRunner, argv: list[str], cap: int, what: str) -> str:
    result = runner.run(argv, env=dict(ENVIRONMENT), timeout=TIMEOUT)
    if len(result.stdout.encode("utf-8")) > cap:
        raise WorkflowError(f"dispatch {what} output exceeds its {cap}-byte cap")
    return result.stdout


def _json(stdout: str, what: str) -> Any:
    try:
        return json.loads(stdout)
    except ValueError as exc:
        raise WorkflowError(f"dispatch {what} returned invalid JSON") from exc


def show(runner: CommandRunner, profile: Mapping[str, Any], bead_id: str) -> dict[str, Any]:
    argv = [GC, "--city", profile["city"], "--rig", profile["rig"], "bd", "show", bead_id]
    return parse_bead_readback(_gc(runner, [*argv, "--json"], OUTPUT_CAP, "bd show"), bead_id)


def sling_argv(profile: Mapping[str, Any], target: str, bead_id: str) -> list[str]:
    """The reviewed ga-4z38 routing form."""

    return [
        GC,
        "--city",
        profile["city"],
        "--rig",
        profile["rig"],
        "sling",
        target,
        bead_id,
        "--no-formula",
        "--no-convoy",
        "--json",
    ]


def require_unrouted(bead: Mapping[str, Any]) -> None:
    """Open, unassigned, unowned, and carrying no routing state of any kind."""

    metadata = bead.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise WorkflowError("dispatch child metadata is not an object")
    if bead.get("status") != "open":
        raise WorkflowError(f"dispatch requires an open child (status={bead.get('status')!r})")
    if bead.get("assignee"):
        raise WorkflowError("dispatch refuses an assigned child")
    if any(bead.get(key) for key in NATIVE_KEYS | {"routed", "session", "agent_id"}):
        raise WorkflowError("dispatch refuses a child with native routing or session state")
    if OWNER_KEY in metadata:
        raise WorkflowError("dispatch refuses an externally owned child")
    if any(key.startswith("gc.") for key in metadata):
        raise WorkflowError(
            "dispatch refuses a child with gc.* metadata; "
            "a reviewed window routes a Bead it prepared"
        )
    if any(marker in key.lower() for key in metadata for marker in ROUTING_MARKERS):
        raise WorkflowError("dispatch refuses a child with work-pack or workspace metadata")
    labels = bead.get("labels") or []
    if not isinstance(labels, list) or any(str(label).startswith(ROUTE_LABELS) for label in labels):
        raise WorkflowError("dispatch refuses a child with native route labels")


def listed_ready(runner: CommandRunner, profile: Mapping[str, Any], bead_id: str) -> None:
    argv = [GC, "--city", profile["city"], "--rig", profile["rig"], "bd", "ready"]
    rows = _json(_gc(runner, [*argv, "--limit", "0", "--json"], READY_CAP, "bd ready"), "bd ready")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise WorkflowError("dispatch bd ready readback must be a list of records")
    if not any(row.get("id") == bead_id for row in rows):
        raise WorkflowError(
            f"dispatch refuses {bead_id}: bd ready does not list it. bd 1.2.2 blocks a child "
            "whose parent-child parent is blocked, for example by a depend prerequisite, and "
            "such a child never reaches a worker. Dispatch never removes that edge itself."
        )


def _fold(record: Mapping[str, Any]) -> dict[str, Any]:
    """Keys lower-cased without underscores, so `work_dir`, `WorkDir` and `workdir` agree."""

    return {str(key).lower().replace("_", ""): value for key, value in record.items()}


def _folded(record: Mapping[str, Any]) -> dict[str, Any]:
    folded = _fold(record)
    if len(folded) != len(record):
        raise WorkflowError("dispatch agent record has ambiguous field names")
    return folded


def _agent_names(record: Mapping[str, Any]) -> set[str]:
    fields = _fold(record)
    names = {fields[key] for key in ("qualifiedname", "name") if isinstance(fields.get(key), str)}
    name = fields.get("name")
    for key in ("rig", "dir"):
        scope = fields.get(key)
        if isinstance(scope, str) and scope and isinstance(name, str) and "/" not in name:
            names.add(f"{scope}/{name}")
    return names


def _canonical_checkout(workdir: str, profile: Mapping[str, Any]) -> bool:
    roots = [Path(profile["canonical_root"])]
    for key in ("registered_projects", "review_projects"):
        roots.extend(Path(entry["canonical_root"]) for entry in profile.get(key, []))
    candidates = {Path(os.path.normpath(workdir)), Path(workdir).resolve()}
    return any(
        candidate == root or candidate.is_relative_to(root)
        for candidate in candidates
        for root in roots
    )


def target_agent(runner: CommandRunner, profile: Mapping[str, Any], target: str) -> None:
    """`agent list` shows the target once, not suspended, and not in a canonical checkout."""

    argv = [GC, "--city", profile["city"], "agent", "list", "--json"]
    value = _json(_gc(runner, argv, OUTPUT_CAP, "agent list"), "agent list")
    if isinstance(value, dict):
        nested = [item for key, item in value.items() if str(key).lower() == "agents"]
        value = nested[0] if len(nested) == 1 else None
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise WorkflowError("dispatch agent list readback must be a list of agent records")
    matches = [record for record in value if target in _agent_names(record)]
    if len(matches) != 1:
        raise WorkflowError(f"dispatch target {target} is not exactly one agent in agent list")
    record = _folded(matches[0])
    if record.get("suspended") is not False:
        raise WorkflowError(
            f"dispatch target {target} is suspended, or agent list does not show that it is not"
        )
    for key in ("workdir", "workingdir", "cwd"):
        workdir = record.get(key)
        if isinstance(workdir, str) and workdir.startswith("/"):
            if _canonical_checkout(workdir, profile):
                raise WorkflowError(f"dispatch target {target} works in a canonical checkout")


def routed(before: Mapping[str, Any], after: Mapping[str, Any], target: str) -> bool:
    """The readback shows the route to `target` and nothing beyond the route and claim delta.

    The route adds `gc.routed_to`. A pool claim may add or change `status` (only to
    `in_progress`), `assignee`, `updated_at`, `started_at` and the metadata keys
    `gc.session_id`, `gc.session_name` and `gc.work_branch`; any subset of them, since a
    readback can race the claim. Nothing may be removed, and every other field, nested
    dependency entries included, must be unchanged. The claim is accepted, not proven
    to belong to the target's pool.
    """

    old_meta = before.get("metadata") or {}
    new_meta = after.get("metadata") or {}
    if (
        not isinstance(old_meta, dict)
        or not isinstance(new_meta, dict)
        or new_meta.get("gc.routed_to") != target
    ):
        return False
    expected = {**old_meta, "gc.routed_to": target}
    for key in set(expected) | set(new_meta):
        old, new = expected.get(key, _MISSING), new_meta.get(key, _MISSING)
        if old != new and (key not in CLAIM_METADATA or new is _MISSING):
            return False
    for key in (set(before) | set(after)) - {"metadata"}:
        old, new = before.get(key, _MISSING), after.get(key, _MISSING)
        if old == new:
            continue
        if key not in CLAIM_FIELDS or (key == "status" and new != "in_progress"):
            return False
        if key != "updated_at" and new is _MISSING:
            return False
    return True


def untouched(before: Mapping[str, Any], live: Mapping[str, Any]) -> bool:
    """Equal to the recorded snapshot in every field except `updated_at`."""

    return {key: value for key, value in before.items() if key != "updated_at"} == {
        key: value for key, value in live.items() if key != "updated_at"
    }


def _state(bead: Mapping[str, Any]) -> str:
    metadata = bead.get("metadata") if isinstance(bead.get("metadata"), dict) else {}
    return (
        f"status={bead.get('status')!r}, assignee={bead.get('assignee')!r}, "
        f"gc.routed_to={metadata.get('gc.routed_to')!r}"
    )


def last_sling(record: Mapping[str, Any], now: datetime) -> datetime:
    value = record.get("last_sling_at")
    try:
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError(value)
        moment = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise WorkflowError(
            "dispatch last_sling_at is missing or unparsable; operator reconciliation required"
        ) from None
    if moment > now:
        raise WorkflowError(
            "dispatch last_sling_at lies in the future; operator reconciliation required"
        )
    return moment


def start(
    runner: CommandRunner,
    root: Path,
    profile: Mapping[str, Any],
    path: Path,
    journal: dict[str, Any],
    key: str,
    request: Mapping[str, Any],
    *,
    registry: Path,
) -> dict[str, Any]:
    """A first dispatch: live checks, the intent, then one stamped sling."""

    bead_id, target = request["bead_id"], request["fields"]["target"]
    before = show(runner, profile, bead_id)
    require_unrouted(before)
    listed_ready(runner, profile, bead_id)
    target_agent(runner, profile, target)
    journal["coordination"][key] = {
        "state": "pending",
        "request": dict(request),
        "before": store_snapshot(path, before),
        "blocker_before": None,
        # Every pending dispatch carries the time of its latest sling attempt.
        "last_sling_at": _stamp(_clock()),
    }
    atomic_write_json(path, journal)
    return _sling(runner, root, profile, path, key, request, before, before, registry=registry)


def complete(
    runner: CommandRunner,
    root: Path,
    profile: Mapping[str, Any],
    path: Path,
    key: str,
    record: Mapping[str, Any],
    *,
    registry: Path,
) -> dict[str, Any]:
    """The exact request of a pending dispatch: verify a landed route, or sling once more."""

    request = record["request"]
    bead_id, target = request["bead_id"], request["fields"]["target"]
    now = _clock()
    latest = last_sling(record, now)
    before = resolve_snapshot(path, record["before"])
    live = show(runner, profile, bead_id)
    if routed(before, live, target):
        return _verify(
            runner, root, path, key, request, before, live, registry=registry, slung=False
        )
    if not untouched(before, live):
        raise WorkflowError(
            "pending dispatch: the child is neither routed to the target with an accepted delta "
            f"nor unrouted as recorded ({_state(live)}); report it to the operator"
        )
    if now - latest < RESLING_AFTER:
        raise WorkflowError(
            "pending dispatch: the latest sling attempt was less than 60 s ago; "
            "repeat the exact request later"
        )
    require_unrouted(live)
    listed_ready(runner, profile, bead_id)
    target_agent(runner, profile, target)
    return _sling(runner, root, profile, path, key, request, before, live, registry=registry)


def _stamp_attempt(path: Path, key: str) -> None:
    try:
        journal = load_journal(path)
        journal["coordination"][key]["last_sling_at"] = _stamp(_clock())
        atomic_write_json(path, journal)
    except Exception as exc:  # noqa: BLE001 - any failure refuses before the sling.
        raise WorkflowError("dispatch could not record last_sling_at; no sling was sent") from exc


def _sling(
    runner: CommandRunner,
    root: Path,
    profile: Mapping[str, Any],
    path: Path,
    key: str,
    request: Mapping[str, Any],
    before: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    registry: Path,
) -> dict[str, Any]:
    bead_id, target = request["bead_id"], request["fields"]["target"]
    # Revalidate as every coordination action does; the stamp is the last journal write.
    check_active_ownership(runner, root, registry=registry)
    if show(runner, profile, bead_id) != expected:
        raise WorkflowError("dispatch child changed before the sling; the intent stays pending")
    _stamp_attempt(path, key)
    result = _json(_gc(runner, sling_argv(profile, target, bead_id), OUTPUT_CAP, "sling"), "sling")
    if (
        not isinstance(result, dict)
        or result.get("success") is not True
        or result.get("routed") is not True
        or result.get("dry_run")
        or result.get("convoy_id")
        or result.get("molecule_id")
        or result.get("bead_id", bead_id) != bead_id
        or result.get("target", target) != target
    ):
        raise WorkflowError(
            "sling did not report one plain route (success and routed, no convoy or molecule); "
            "the intent stays pending"
        )
    after = show(runner, profile, bead_id)
    if not routed(before, after, target):
        raise WorkflowError(
            f"dispatch readback is not an accepted route and claim delta ({_state(after)}); "
            "the intent stays pending"
        )
    return _verify(runner, root, path, key, request, before, after, registry=registry, slung=True)


def _verify(
    runner: CommandRunner,
    root: Path,
    path: Path,
    key: str,
    request: Mapping[str, Any],
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    registry: Path,
    slung: bool,
) -> dict[str, Any]:
    check_active_ownership(runner, root, registry=registry)
    journal = load_journal(path)
    journal["coordination"][key].update(
        state="verified",
        result_bead=request["bead_id"],
        after=store_snapshot(path, after),
        before_sha256=bead_digest(before),
        after_sha256=bead_digest(after),
    )
    atomic_write_json(path, journal)
    return result_payload(
        "coordinate",
        "applied",
        bead_id=request["bead_id"],
        target=request["fields"]["target"],
        request_sha256=key,
        slung=slung,
        journal=str(path),
    )
