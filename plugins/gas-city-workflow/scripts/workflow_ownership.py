"""Ledger-bound external source coordination, not a native worker claim.

This is an activity binding, not dispatch authority or a distributed scheduler lock.
Never clear an assignee, impersonate a session, or repair drift by re-claiming.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from project_context import DEFAULT_REGISTRY, build_context
from _repo_structure import load_repo_structure
from workflow_common import (
    BeginSpec,
    CommandRunner,
    WorkflowError,
    active_begin_spec,
    atomic_write_json,
    git_value,
    is_blocking_dependency,
    journal_path,
    load_bead,
    load_journal,
    managed_environment,
)

OWNER_KEY = "workflow.external_owner"
OWNER_SCHEMA = "gas-city-workflow.external-owner.v1"
NATIVE_KEYS = frozenset(
    {
        "agent",
        "session_id",
        "session_name",
        "assigned_to",
        "routed_to",
        "target",
        "workflow_id",
        "molecule_id",
        "formula",
        "hook_bead",
        "hook_bead_id",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def bead_digest(bead: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(bead).encode()).hexdigest()


def require_external_candidate(bead: Mapping[str, Any]) -> None:
    if os.environ.get("GC_SESSION_ID") or os.environ.get("GC_SESSION_NAME"):
        raise WorkflowError("native sessions must retain the managed claim protocol")
    if bead.get("assignee"):
        raise WorkflowError("external source workflow refuses assigned work")
    if any(bead.get(key) for key in NATIVE_KEYS | {"routed", "session", "agent_id"}):
        raise WorkflowError("external source workflow refuses native routing/session state")
    metadata = bead.get("metadata", {})
    if not isinstance(metadata, dict):
        raise WorkflowError("bead metadata is not an object")
    if any(
        value and (key.startswith("gc.") or key in NATIVE_KEYS) for key, value in metadata.items()
    ):
        raise WorkflowError("external source workflow refuses native control metadata")
    if any(
        str(label).startswith(("pool:", "agent:", "session:", "route:"))
        for label in bead.get("labels", [])
    ):
        raise WorkflowError("external source workflow refuses native route labels")


def owner_payload(spec: BeginSpec, context: Mapping[str, Any]) -> str:
    return canonical_json(
        {
            "schema": OWNER_SCHEMA,
            "kind": "external-coordinator",
            "project": spec.project_id,
            "city": str(context["workflow"]["city"]),
            "rig": spec.rig,
            "canonical_root": spec.canonical_root,
            "worktree": spec.worktree,
            "branch": spec.branch,
            "primary_bead": spec.bead_id,
            "transaction_sha256": hashlib.sha256(
                canonical_json(spec.payload()).encode()
            ).hexdigest(),
        }
    )


def owner_binding(spec: BeginSpec, context: Mapping[str, Any]) -> str:
    # bd --set-metadata is key=value, not a JSON-string argument. Keep the wire
    # value typed ASCII; the full binding is reproducible from the journal spec.
    return (
        "external-coordinator.v1:"
        + hashlib.sha256(owner_payload(spec, context).encode()).hexdigest()
    )


def require_binding(bead: Mapping[str, Any], binding: str, *, allow_closed: bool = False) -> None:
    require_external_candidate(bead)
    if bead.get("metadata", {}).get(OWNER_KEY) != binding:
        raise WorkflowError(
            "external ownership binding missing or changed; explicit reconciliation required"
        )
    statuses = {"in_progress", "closed"} if allow_closed else {"in_progress"}
    if bead.get("status") not in statuses:
        raise WorkflowError(
            "external ownership requires in_progress; do not silently reclaim reopened work"
        )


def require_workspace(runner: CommandRunner, spec: BeginSpec, context: Mapping[str, Any]) -> None:
    if (
        context["project"]["id"] != spec.project_id
        or context["workflow"]["rig"] != spec.rig
        or context["workspace"]["canonical_root"] != spec.canonical_root
        or Path(context["project"]["root"]).resolve() != Path(spec.worktree).resolve()
    ):
        raise WorkflowError("ownership project/rig/worktree identity drift")
    if git_value(runner, Path(spec.worktree), "branch", "--show-current") != spec.branch:
        raise WorkflowError("ownership branch identity drift")
    if runner.run(
        ["git", "-C", spec.worktree, "merge-base", "--is-ancestor", spec.base_commit, "HEAD"],
        check=False,
    ).returncode:
        raise WorkflowError("ownership base is no longer an ancestor of HEAD")


def ensure_external_owner(
    runner: CommandRunner,
    spec: BeginSpec,
    context: Mapping[str, Any],
    journal: dict[str, Any],
    path: Path,
    *,
    bead_id: str | None = None,
    reconcile_digest: str | None = None,
) -> dict[str, Any]:
    """Write one bounded status+metadata patch, preserving before/after evidence.

    A pending intent can complete only from the exact before or exact after state.
    A verified binding is never repaired automatically. No rollback guesses at a
    concurrent writer's state. The supported CLI has no metadata/status CAS; callers
    must keep this Bead out of concurrent routing and use one coordinator workflow.
    """
    bead_id = bead_id or spec.bead_id
    require_workspace(runner, spec, context)
    bead = load_bead(runner, context, bead_id)
    require_external_candidate(bead)
    binding = owner_binding(spec, context)
    records = journal.setdefault("external_ownership", {})
    if not isinstance(records, dict):
        raise WorkflowError("external ownership journal is invalid")
    record = records.get(bead_id)
    current = bead.get("metadata", {}).get(OWNER_KEY)
    if record and record.get("state") == "verified":
        if record.get("binding") != binding:
            raise WorkflowError("ownership journal binding drift")
        require_binding(bead, binding)
        return bead
    if record:
        if record.get("state") != "pending" or record.get("binding") != binding:
            raise WorkflowError("ownership journal intent drift")
        if current == binding and bead.get("status") == "in_progress":
            _verify_delta(record["before"], bead, binding)
        elif bead != record.get("before"):
            raise WorkflowError("ambiguous partial ownership mutation; preserve evidence")
    else:
        if current is not None:
            raise WorkflowError("ownership metadata has no matching local intent; refuse adoption")
        legacy = journal["phase"] in {"claimed", "ready"} and bead_id == spec.bead_id
        if legacy or bead.get("status") != "open":
            if reconcile_digest != bead_digest(bead):
                raise WorkflowError(
                    "legacy ownership requires explicit exact-digest reconciliation"
                )
        if bead.get("status") not in {"open", "in_progress"}:
            raise WorkflowError("terminal or blocked work cannot acquire external ownership")
        record = {
            "state": "pending",
            "binding": binding,
            "before": bead,
            "reconciliation": reconcile_digest is not None,
        }
        records[bead_id] = record
        atomic_write_json(path, journal)
    if current != binding:
        # A second fresh read catches drift after intent persistence, before mutation.
        if load_bead(runner, context, bead_id) != record["before"]:
            raise WorkflowError("bead changed before ownership mutation")
        workflow = context["workflow"]
        runner.run(
            [
                str(workflow["gc"]),
                "--city",
                str(workflow["city"]),
                "--rig",
                str(workflow["rig"]),
                "bd",
                "update",
                bead_id,
                "--status",
                "in_progress",
                "--set-metadata",
                f"{OWNER_KEY}={binding}",
            ],
            env=managed_environment(),
        )
        bead = load_bead(runner, context, bead_id)
        _verify_delta(record["before"], bead, binding)
    require_binding(bead, binding)
    record.update(state="verified", after=bead)
    atomic_write_json(path, journal)
    return bead


def _verify_delta(before: Mapping[str, Any], after: Mapping[str, Any], binding: str) -> None:
    def semantic(value: Mapping[str, Any]) -> dict[str, Any]:
        # These timestamps are native consequences of starting work, not caller patches.
        return {key: item for key, item in value.items() if key not in {"updated_at", "started_at"}}

    expected = semantic(before)
    expected["status"] = "in_progress"
    expected["metadata"] = {**before.get("metadata", {}), OWNER_KEY: binding}
    if semantic(after) != expected:
        raise WorkflowError("unexpected ownership write delta; no automatic rollback or retry")


def check_active_ownership(
    runner: CommandRunner,
    root: Path,
    *,
    registry: Path = DEFAULT_REGISTRY,
    allow_closed: bool = False,
    spec: BeginSpec | None = None,
    dependencies_complete: bool = False,
    attaching: str | None = None,
) -> BeginSpec:
    spec = spec or active_begin_spec(runner, root)
    context = build_context(root, registry)
    require_workspace(runner, spec, context)
    journal = load_journal(journal_path(runner, spec))
    records = (journal or {}).get("external_ownership", {})
    if not isinstance(records, dict):
        raise WorkflowError("external ownership journal is invalid")
    binding = owner_binding(spec, context)
    attached = (journal or {}).get("attached_bead_ids", [])
    if not isinstance(attached, list) or any(not isinstance(item, str) for item in attached):
        raise WorkflowError("attached ownership journal is invalid")
    if len(attached) != len(set(attached)) or spec.bead_id in attached:
        raise WorkflowError("duplicate attached ownership identity")
    # Source closeout can archive pointers. Before that, the active plan must agree.
    plan_link = load_repo_structure(root).current_plan_link
    if plan_link.exists():
        plan = plan_link.resolve()
        if not plan.is_relative_to(root.resolve()):
            raise WorkflowError("ownership plan escapes worktree")
        matches = re.findall(
            r"^attached_bead_ids:\s*\[([^\]]*)\]\s*$", plan.read_text(), re.MULTILINE
        )
        plan_ids = (
            [item.strip() for item in matches[0].split(",") if item.strip()] if matches else []
        )
        if len(matches) > 1 or plan_ids != attached:
            raise WorkflowError("plan/journal attached ownership mismatch")
    elif not allow_closed:
        raise WorkflowError("ownership current plan is missing")
    ids = [spec.bead_id, *attached]
    for bead_id in ids:
        record = records.get(bead_id, {})
        if record.get("state") != "verified" or record.get("binding") != binding:
            raise WorkflowError("external ownership not verified in journal; reconcile explicitly")
        bead = load_bead(runner, context, bead_id)
        require_binding(bead, binding, allow_closed=allow_closed or bead_id != spec.bead_id)
        unresolved = [
            item.get("id") or item.get("depends_on_id")
            for item in bead.get("dependencies", [])
            if isinstance(item, dict)
            and is_blocking_dependency(item)
            and item.get("status") != "closed"
        ]
        allowed = set(attached) if bead_id == spec.bead_id and not dependencies_complete else set()
        if bead_id == spec.bead_id and attaching is not None and not dependencies_complete:
            allowed.add(attaching)
        if any(item not in allowed for item in unresolved):
            raise WorkflowError("external source workflow has unresolved unattached dependencies")
    return spec
