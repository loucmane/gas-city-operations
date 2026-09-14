"""Journal-bound discharge of delivery-class pending events (ga-fsfg R1).

A commit, push or pull-request operation enqueues a strict pending event whose
durable evidence already lives in Git or GitHub. Logging it through the tracked
S:W:H:E surfaces re-dirties the tree that the commit just cleaned, so a hooked
seat never reaches `publish`. `discharge` records the event into the workflow
journal instead and removes it from the queue; no tracked file changes.
"""

from __future__ import annotations

import re
from pathlib import Path

from project_context import DEFAULT_REGISTRY, build_context
from workflow_common import (
    CommandRunner,
    WorkflowError,
    git_value,
    record_lifecycle_event,
    result_payload,
)
from workflow_ownership import check_active_ownership
from workflow_portable import load_shared_runtime

PENDING_EVENT_ID = re.compile(r"[0-9a-f]{12}")
DELIVERY_KIND = "delivery"


def discharge(
    root: Path,
    pending_id: str,
    note: str,
    runner: CommandRunner,
    *,
    registry: Path = DEFAULT_REGISTRY,
) -> dict:
    if not isinstance(pending_id, str) or not PENDING_EVENT_ID.fullmatch(pending_id):
        raise WorkflowError("invalid pending event identity")
    if not isinstance(note, str) or not note.strip() or len(note) > 16384 or "\x00" in note:
        raise WorkflowError("discharge note must be nonempty and bounded")
    context = build_context(root, registry)
    if context["workspace"]["location"] != "linked-worktree":
        raise WorkflowError("discharge requires a registered task worktree")
    check_active_ownership(runner, root, registry=registry)
    load_shared_runtime()
    from aegis_foundation.gate.hooks.evidence import write_pending_tracking_events
    from aegis_foundation.gate.hooks.runtime_state import pending_tracking_events

    events = pending_tracking_events(root)
    matches = [event for event in events if str(event.get("id") or "") == pending_id]
    if len(matches) != 1:
        raise WorkflowError("discharge requires exactly one matching pending event")
    event = matches[0]
    if event.get("kind") != DELIVERY_KIND:
        raise WorkflowError(
            "only delivery-class pending events discharge through the journal; use log"
        )
    head = git_value(runner, root, "rev-parse", "HEAD")
    tree = git_value(runner, root, "rev-parse", "HEAD^{tree}")
    path = record_lifecycle_event(
        runner,
        root,
        "discharge",
        "recorded",
        pending_id=pending_id,
        handler=str(event.get("handler") or ""),
        evidence=str(event.get("evidence") or ""),
        recorded_at=str(event.get("created_at") or ""),
        head=head,
        tree=tree,
        note=note,
    )
    write_pending_tracking_events(root, [item for item in events if item is not event])
    if any(str(item.get("id") or "") == pending_id for item in pending_tracking_events(root)):
        raise WorkflowError("discharge readback still lists the pending event")
    check_active_ownership(runner, root, registry=registry)
    return result_payload(
        "discharge", "recorded", pending_id=pending_id, head=head, tree=tree, journal=str(path)
    )
