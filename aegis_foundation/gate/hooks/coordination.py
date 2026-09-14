"""Bind a stationary seat to one explicit workflow target, never change its root.

Only reviewed canonical workflow commands may select a target. The journal is
cross-checked evidence, not ledger authority: the executor revalidates live Bead
ownership under its existing repository lock immediately before mutation.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from .contracts import Payload
from .coordination_runtime import reviewed_runtime
from .orchestrator import BEAD, SHELL_SYNTAX, WORKFLOW_REL, _options, _python
from .payloads import bash_command, shlex_tokens, strip_shell_prefixes

VERBS = frozenset(
    {"attach", "checkpoint", "verify", "coordinate", "log", "discharge", "compact-journal"}
)
KIND = "workflow-coordinate"
PENDING_EVENT_ID = re.compile(r"[0-9a-f]{12}")


def request(root: Path, payload: Payload) -> tuple[str, dict[str, list[str]]] | None:
    """Parse one closed invocation; foreign executables receive no new treatment."""
    if payload.tool_name != "Bash":
        return None
    command = bash_command(payload)
    tokens = strip_shell_prefixes(shlex_tokens(command))
    if len(tokens) < 3 or not _python(tokens[0]):
        return None
    script = Path(tokens[1])
    if not script.is_absolute():
        script = root / script
    if script != root / WORKFLOW_REL or tokens[2] not in VERBS:
        return None
    if SHELL_SYNTAX.search(command):
        raise ValueError("coordination requires a single literal command")
    verb = tokens[2]
    values = {"--root"}
    required = {"--root"}
    if verb == "attach":
        values |= {"--bead"}
        required |= {"--bead"}
    elif verb == "coordinate":
        values |= {
            "--bead",
            "--action",
            "--text",
            "--title",
            "--description",
            "--acceptance",
            "--blocker",
        }
        required |= {"--bead", "--action"}
    elif verb == "log":
        values |= {"--evidence", "--note", "--pending-id"}
        required |= {"--note"}
    elif verb == "discharge":
        values |= {"--pending-id", "--note"}
        required |= {"--pending-id", "--note"}
    options = _options(tokens[3:], values=values, switches=set())
    if options is None or not required <= options.keys():
        raise ValueError("unrecognized coordination arguments")
    if verb == "discharge" and not PENDING_EVENT_ID.fullmatch(options["--pending-id"][0]):
        raise ValueError("invalid coordination pending event identity")
    if verb == "coordinate":
        shapes = {
            "note": {"--text"},
            "create": {"--title", "--description", "--acceptance"},
            "depend": {"--blocker"},
        }
        action = options["--action"][0]
        if action not in shapes or set(options) != required | shapes[action]:
            raise ValueError("unrecognized ledger operation")
    elif verb == "log":
        evidence_sources = {"--evidence", "--pending-id"} & set(options)
        if len(evidence_sources) != 1:
            raise ValueError("coordination log requires exactly one evidence source")
        if "--pending-id" in options and not PENDING_EVENT_ID.fullmatch(options["--pending-id"][0]):
            raise ValueError("invalid coordination pending event identity")
    for field in ("--bead", "--blocker"):
        if field in options and not BEAD.fullmatch(options[field][0]):
            raise ValueError("invalid coordination bead identity")
    if any(len(value[0]) > 16384 for value in options.values()):
        raise ValueError("coordination argument exceeds bound")
    return verb, options


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode:
        raise ValueError("coordination Git identity check failed")
    return result.stdout.strip()


def _journal(target: Path, canonical: Path, profile: dict, verb: str, options: dict) -> None:
    from .native_permissions import _unique_object

    # The current plan is an explicit primary identifier, not a global active-seat selector.
    plan = target / "plans/current"
    resolved = plan.resolve(strict=True)
    if not plan.is_symlink() or not resolved.is_relative_to(target) or not resolved.is_file():
        raise ValueError("coordination current plan escapes target")
    plan_text = resolved.read_text(encoding="utf-8")
    ids = re.findall(r"^bead_ids:\s*\[([^\]]+)\]\s*$", plan_text, re.MULTILINE)
    if len(ids) != 1 or not BEAD.fullmatch(ids[0]):
        raise ValueError("coordination requires exactly one primary Bead")
    bead = ids[0]
    common = Path(_git(target, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    if common != canonical / ".git":
        raise ValueError("coordination Git common directory mismatch")
    path = common / "gas-city-workflow/transactions" / f"{bead}.json"
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError("coordination journal is aliased or oversized")
    # compact-journal is the supported repair for an oversized journal; every other
    # verb keeps the bound so an unbounded journal cannot be coordinated blindly.
    if verb != "compact-journal" and path.stat().st_size > 1024 * 1024:
        raise ValueError("coordination journal is aliased or oversized")
    journal = json.loads(path.read_text(), object_pairs_hook=_unique_object)
    if (
        journal.get("schema") != "gas-city-workflow.transition.v1"
        or journal.get("phase") != "ready"
    ):
        raise ValueError("coordination journal is not ready")
    spec = journal["spec"]
    expected = {
        "project_id": profile["project_id"],
        "rig": profile["rig"],
        "canonical_root": str(canonical),
        "worktree_root": profile["worktree_root"],
        "worktree": str(target),
        "bead_id": bead,
    }
    if any(spec.get(key) != value for key, value in expected.items()):
        raise ValueError("coordination journal target identity mismatch")
    if (
        spec.get("branch") != _git(target, "branch", "--show-current")
        or spec["branch"] != f"codex/{bead}-{spec.get('slug')}"
        or target.name != f"{bead}-{spec.get('slug')}"
    ):
        raise ValueError("coordination branch/worktree mismatch")
    _git(target, "merge-base", "--is-ancestor", spec["base_commit"], "HEAD")
    attached = journal.get("attached_bead_ids", [])
    if not isinstance(attached, list) or any(
        not isinstance(item, str) or not BEAD.fullmatch(item) for item in attached
    ):
        raise ValueError("invalid attached identities")
    if len(set([bead, *attached])) != 1 + len(attached):
        raise ValueError("duplicate attached identities")
    plan_attached = re.findall(r"^attached_bead_ids:\s*\[([^\]]*)\]\s*$", plan_text, re.MULTILINE)
    if (
        len(plan_attached) > 1
        or ([v.strip() for v in plan_attached[0].split(",") if v.strip()] if plan_attached else [])
        != attached
    ):
        raise ValueError("coordination plan/journal mismatch")

    def canonical_json(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    owner = {
        "schema": "gas-city-workflow.external-owner.v1",
        "kind": "external-coordinator",
        "project": spec["project_id"],
        "city": profile["city"],
        "rig": spec["rig"],
        "canonical_root": str(canonical),
        "worktree": str(target),
        "branch": spec["branch"],
        "primary_bead": bead,
        "transaction_sha256": hashlib.sha256(canonical_json(spec).encode()).hexdigest(),
    }
    binding = (
        "external-coordinator.v1:" + hashlib.sha256(canonical_json(owner).encode()).hexdigest()
    )
    for owned in [bead, *attached]:
        record = journal.get("external_ownership", {}).get(owned, {})
        if record.get("state") != "verified" or record.get("binding") != binding:
            raise ValueError("coordination ownership journal is not verified")
    if verb == "coordinate" and options["--bead"][0] not in [bead, *attached]:
        raise ValueError("ledger operation does not name an owned Bead")


def target_for(root: Path, payload: Payload, *, post_success: bool = False) -> Path | None:
    from .decisions import advisory_enabled
    from .native_permissions import PROFILE, _bound_bytes, _canonical_runtime, _profile
    from .runtime_state import current_work_is_observation, required_pending_tracking_events

    if not (root / PROFILE).exists():
        return None
    parsed = request(root, payload)
    if parsed is None:
        return None
    profile = _profile(root)
    if profile is None or KIND not in profile["commands"]:
        return None
    if str(root) != profile["canonical_root"] or payload.cwd != str(root):
        raise ValueError("coordination must originate at the canonical seat")
    if payload.permission_mode not in {"default", "manual", "dontAsk", "acceptEdits", "auto"}:
        raise ValueError("coordination requires a known non-plan permission mode")
    verb, options = parsed
    target = Path(options["--root"][0])
    if (
        not target.is_absolute()
        or target.resolve(strict=True) != target
        or target.parent != Path(profile["worktree_root"])
        or target == root
    ):
        raise ValueError("coordination target must be a direct registered linked worktree")
    _canonical_runtime(
        strip_shell_prefixes(shlex_tokens(bash_command(payload))), root, root, WORKFLOW_REL
    )
    if _profile(target) != profile or _bound_bytes(
        target, Path(".gas-city-workflow.json")
    ) != _bound_bytes(root, Path(".gas-city-workflow.json")):
        raise ValueError("coordination target has divergent project policy")
    _reviewed_target_runtime(target, root)
    _journal(target, root, profile, verb, options)
    for governed in (root, target):
        if advisory_enabled(governed) or current_work_is_observation(governed):
            raise ValueError(
                "coordination requires strict non-observation state at seat and target"
            )
        pending = required_pending_tracking_events(governed)
        if verb in {"log", "discharge"} and governed == target:
            if "--pending-id" in options:
                matches = [
                    event
                    for event in pending
                    if str(event.get("id") or "") == options["--pending-id"][0]
                ]
                if verb == "discharge" and not post_success:
                    # Only delivery-class events (commit, push, PR) discharge into the
                    # journal; everything else still needs the S:W:H:E log.
                    matches = [event for event in matches if event.get("kind") == "delivery"]
                expected = 0 if post_success else 1
                if len(matches) != expected:
                    state = "resolved" if post_success else "exact"
                    raise ValueError(f"coordination pending event is not {state} for target")
            continue
        if pending:
            raise ValueError("coordination requires pending tracking to be resolved")
    return target


def _reviewed_target_runtime(target: Path, canonical: Path) -> None:
    reviewed_runtime(target, canonical)
