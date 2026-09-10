"""Bounded ledger actions for an externally owned source-work context.

All writes use native APIs inside workflow.py's repository lock. A pending intent
is never replayed automatically: an uncertain create/update must be reconciled,
not duplicated. No command, rig, status, metadata, route or assignee is caller-set.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from project_context import DEFAULT_REGISTRY, build_context
from workflow_attach import attach
from workflow_common import (
    BEAD_PATTERN,
    CommandRunner,
    WorkflowError,
    atomic_write_json,
    journal_path,
    load_bead,
    load_journal,
    managed_environment,
    result_payload,
    run_readiness,
    workflow_runtime_root,
)
from workflow_ownership import (
    bead_digest,
    canonical_json,
    check_active_ownership,
    require_external_candidate,
)

FIELDS = {"note": {"text"}, "create": {"title", "description", "acceptance"}, "depend": {"blocker"}}
PENDING_EVENT_ID = re.compile(r"[0-9a-f]{12}")


def _semantic(bead):
    return {key: value for key, value in bead.items() if key not in {"updated_at"}}


def _gc(context):
    wf = context["workflow"]
    return [str(wf["gc"]), "--city", str(wf["city"]), "--rig", str(wf["rig"]), "bd"]


def coordinate(
    root: Path,
    bead_id: str,
    action: str,
    fields: dict[str, str],
    runner: CommandRunner,
    *,
    registry: Path = DEFAULT_REGISTRY,
) -> dict:
    if action not in FIELDS or set(fields) != FIELDS[action]:
        raise WorkflowError("unknown or overbroad coordination operation")
    if any(
        not isinstance(value, str) or not value.strip() or len(value) > 16384 or "\x00" in value
        for value in fields.values()
    ):
        raise WorkflowError("coordination text must be nonempty and bounded")
    if not BEAD_PATTERN.fullmatch(bead_id):
        raise WorkflowError("invalid coordination bead")
    blocker = fields.get("blocker")
    if blocker is not None and (not BEAD_PATTERN.fullmatch(blocker) or blocker == bead_id):
        raise WorkflowError("invalid blocker")
    context = build_context(root, registry)
    if context["workspace"]["location"] != "linked-worktree":
        raise WorkflowError("coordination writes require a registered task worktree")
    spec = check_active_ownership(runner, root, registry=registry, attaching=blocker)
    path = journal_path(runner, spec)
    journal = load_journal(path)
    if journal is None or journal["phase"] != "ready":
        raise WorkflowError("coordination requires a ready journal")
    if bead_id not in [spec.bead_id, *journal.get("attached_bead_ids", [])]:
        raise WorkflowError("coordination bead is not owned by this workflow")
    if action == "depend" and bead_id != spec.bead_id:
        raise WorkflowError("only the primary Bead may acquire an attached dependency")
    run_readiness(runner, root)
    request = {"bead_id": bead_id, "action": action, "fields": fields}
    key = hashlib.sha256(canonical_json(request).encode()).hexdigest()
    operations = journal.setdefault("coordination", {})
    if not isinstance(operations, dict):
        raise WorkflowError("invalid coordination journal")
    previous = operations.get(key)
    if previous:
        if previous.get("state") != "verified" or previous.get("request") != request:
            raise WorkflowError(
                "pending/ambiguous coordination intent; explicit reconciliation required"
            )
        current = load_bead(runner, context, previous["result_bead"])
        if _semantic(current) != _semantic(previous["after"]):
            raise WorkflowError("completed coordination result drifted; refuse automatic replay")
        return result_payload(
            "coordinate",
            "unchanged",
            request_sha256=key,
            bead_id=previous["result_bead"],
            journal=str(path),
        )
    if any(record.get("state") != "verified" for record in operations.values()):
        raise WorkflowError("another coordination intent is unresolved")
    before = load_bead(runner, context, bead_id)
    blocker_before = None
    if blocker:
        from workflow_context_recovery import require_reconciled_standalone

        require_reconciled_standalone(runner, spec, context, blocker)
        blocker_before = load_bead(runner, context, blocker)
        require_external_candidate(blocker_before)
        if blocker_before.get("status") != "open" or blocker_before.get("metadata", {}).get(
            "workflow.external_owner"
        ):
            raise WorkflowError("blocker must be open and not already owned or routed")
        if blocker.split("-", 1)[0] != bead_id.split("-", 1)[0]:
            raise WorkflowError("cross-store dependencies require separate registration")
    intent = {
        "state": "pending",
        "request": request,
        "before": before,
        "blocker_before": blocker_before,
    }
    operations[key] = intent
    atomic_write_json(path, journal)
    # Revalidate after intent persistence. A repository lock is not a distributed
    # Beads lease; one external coordinator per owned Bead remains required.
    check_active_ownership(runner, root, registry=registry, attaching=blocker)
    if load_bead(runner, context, bead_id) != before:
        raise WorkflowError("coordination Bead changed before mutation")
    gc = _gc(context)
    env = managed_environment()
    result_id = bead_id
    if action == "note":
        runner.run([*gc, "update", bead_id, "--append-notes", fields["text"]], env=env)
        after = load_bead(runner, context, bead_id)
        expected = _semantic(before)
        old = before.get("notes") or ""
        allowed = {old + "\n" + fields["text"]} if old else {fields["text"], "\n" + fields["text"]}
        if after.get("notes") not in allowed:
            raise WorkflowError("unexpected note append")
        expected["notes"] = after["notes"]
        if _semantic(after) != expected:
            raise WorkflowError("unexpected non-note Bead delta")
    elif action == "create":
        result = runner.run(
            [
                *gc,
                "create",
                fields["title"],
                "--type",
                "task",
                "--priority",
                "P2",
                "--description",
                fields["description"],
                "--acceptance",
                fields["acceptance"],
                "--parent",
                bead_id,
                "--no-inherit-labels",
                "--json",
            ],
            env=env,
        )
        try:
            value = json.loads(result.stdout)
            result_id = value["id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowError("ambiguous create response; do not repeat") from exc
        if (
            not isinstance(result_id, str)
            or not BEAD_PATTERN.fullmatch(result_id)
            or not result_id.startswith(bead_id + ".")
        ):
            raise WorkflowError("create returned an unexpected child identity")
        after = load_bead(runner, context, result_id)
        require_external_candidate(after)
        expected = {
            "title": fields["title"],
            "description": fields["description"],
            "acceptance_criteria": fields["acceptance"],
            "status": "open",
            "priority": 2,
            "issue_type": "task",
        }
        if any(after.get(k) != v for k, v in expected.items()):
            raise WorkflowError("created child readback differs from request")
        edges = [
            edge
            for edge in after.get("dependencies", [])
            if edge.get("id", edge.get("depends_on_id")) == bead_id
        ]
        if (
            len(edges) != 1
            or edges[0].get("dependency_type", edges[0].get("type")) != "parent-child"
        ):
            raise WorkflowError("child relationship is not exactly nonblocking parent-child")
    else:
        if load_bead(runner, context, blocker) != blocker_before:
            raise WorkflowError("blocker changed before mutation")
        edges = [
            e
            for e in before.get("dependencies", [])
            if e.get("id", e.get("depends_on_id")) == blocker
        ]
        if not edges:
            runner.run([*gc, "dep", "add", bead_id, blocker, "--type", "blocks"], env=env)
        current = load_bead(runner, context, bead_id)
        edges = [
            e
            for e in current.get("dependencies", [])
            if e.get("id", e.get("depends_on_id")) == blocker
        ]
        if len(edges) != 1 or edges[0].get("dependency_type", edges[0].get("type")) != "blocks":
            raise WorkflowError("dependency readback is not exactly one blocks edge")
        # Reuse the existing ownership + plan + tracker attachment transaction.
        attach(root, blocker, runner, registry=registry)
        after = load_bead(runner, context, bead_id)
    check_active_ownership(runner, root, registry=registry)
    # attach may have advanced the same journal; reload rather than overwrite it.
    journal = load_journal(path)
    intent = journal["coordination"][key]
    intent.update(
        state="verified",
        result_bead=result_id,
        after=after,
        before_sha256=bead_digest(before),
        after_sha256=bead_digest(after),
    )
    atomic_write_json(path, journal)
    return result_payload(
        "coordinate", "applied", bead_id=result_id, request_sha256=key, journal=str(path)
    )


def log(
    root: Path,
    evidence: str | None,
    note: str,
    runner: CommandRunner,
    *,
    pending_id: str | None = None,
) -> dict:
    if (evidence is None) == (pending_id is None):
        raise WorkflowError("log requires exactly one evidence source")
    if not note.strip() or len(note) > 16384 or "\x00" in note:
        raise WorkflowError("log fields must be nonempty and bounded")
    if evidence is not None and (
        not evidence.strip() or len(evidence) > 16384 or "\x00" in evidence
    ):
        raise WorkflowError("log fields must be nonempty and bounded")
    if pending_id is not None and not PENDING_EVENT_ID.fullmatch(pending_id):
        raise WorkflowError("invalid pending event identity")
    check_active_ownership(runner, root)
    runtime = workflow_runtime_root()
    from workflow_portable import uses_portable_scaffold

    if uses_portable_scaffold(root):
        if pending_id is not None:
            raise WorkflowError("portable source logging cannot consume native pending events")
        from workflow_portable_log import log_portable_evidence

        details = log_portable_evidence(root, str(evidence), note, runner)
        return result_payload("log", "applied", target=str(root), **details)
    if pending_id is not None:
        command = [
            sys.executable,
            "-m",
            "aegis_foundation.cli",
            "log",
            "--target-dir",
            str(root),
            "--pending-id",
            pending_id,
            "--note",
            note,
        ]
    else:
        command = [
            sys.executable,
            str(runtime / "scripts/codex-task"),
            "aegis",
            "log",
            "--target-dir",
            str(root),
            "--handler",
            "workflow-coordinate",
            "--evidence",
            str(evidence),
            "--note",
            note,
        ]
    runner.run(command, cwd=runtime)
    check_active_ownership(runner, root)
    details = {"target": str(root)}
    if pending_id is not None:
        details["pending_id"] = pending_id
    return result_payload("log", "applied", **details)
