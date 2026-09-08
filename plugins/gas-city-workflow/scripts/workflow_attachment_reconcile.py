"""Explicit, digest-bound completion of a known pending dependency attachment.

Writes only the existing journal and its exact backup. Never repeats a Beads,
plan, or tracker mutation. The CLI holds the normal repository workflow lock.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

from project_context import DEFAULT_REGISTRY, build_context
from workflow_attach import _active_tracker, _attached_bead_ids, _current_plan
from workflow_common import (
    BEAD_PATTERN, CommandRunner, WorkflowError, active_begin_spec, journal_path,
    load_bead, load_journal, plan_bead_ids, result_payload, run_readiness,
)
from workflow_ownership import (
    bead_digest, canonical_json, check_active_ownership, owner_binding,
    require_binding, require_workspace,
)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _image(path):
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid():
            raise WorkflowError("reconciliation requires an owned regular file")
        data = handle.read(16 * 1024 * 1024 + 1)
        after = os.fstat(handle.fileno())
        if (len(data) > 16 * 1024 * 1024 or identity(before) != identity(after)
                or identity(path.lstat()) != identity(after)):
            raise WorkflowError("reconciliation file changed while reading or exceeded bounds")
        return data, stat.S_IMODE(after.st_mode), after.st_uid, after.st_gid


def _write_image(path, image):
    data, mode, uid, gid = image
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.reconcile-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchown(handle.fileno(), uid, gid)
            os.fchmod(handle.fileno(), mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _backup(path, image):
    if path.exists() or path.is_symlink():
        if _image(path) != image:
            raise WorkflowError("attachment backup differs; preserve and stop")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        os.fchown(handle.fileno(), image[2], image[3])
        os.fchmod(handle.fileno(), image[1])
        handle.write(image[0])
        handle.flush()
        os.fsync(handle.fileno())
    if _image(path) != image:
        raise WorkflowError("attachment backup verification failed")


def _body(bead):
    # Hydrated dependency descriptions belong to the referenced Beads, not this
    # write. Bind their actual edge identities separately. Counts/timestamps are
    # native readback consequences; all other top-level fields remain exact.
    return {k: v for k, v in bead.items() if k not in {
        "updated_at", "dependency_count", "dependent_count", "dependencies", "dependents",
    }}


def _edges(bead):
    edges = [
        (edge.get("id", edge.get("depends_on_id")),
         edge.get("dependency_type", edge.get("type")))
        for edge in bead.get("dependencies", [])
    ]
    if any(not all(isinstance(item, str) and item for item in edge) for edge in edges):
        raise WorkflowError("dependency readback lacks exact typed identities")
    if len(edges) != len({edge[0] for edge in edges}):
        raise WorkflowError("duplicate dependency readback")
    return set(edges)


def _beads(runner, context, spec, journal, intent, blocker):
    binding = owner_binding(spec, context)
    records = journal["external_ownership"]
    for bead_id in (spec.bead_id, blocker):
        if records[bead_id].get("state") != "verified" or records[bead_id].get("binding") != binding:
            raise WorkflowError("attachment ownership was not verified")
    primary = load_bead(runner, context, spec.bead_id)
    child = load_bead(runner, context, blocker)
    require_binding(primary, binding)
    require_binding(child, binding)
    before = intent["before"]
    child_record = records[blocker]
    if (_body(primary) != _body(before)
            or _body(child_record["before"]) != _body(intent["blocker_before"])
            or _body(child) != _body(child_record["after"])):
        raise WorkflowError("attachment Bead fields drifted from the recorded transaction")
    if (_edges(primary) != _edges(before) | {(blocker, "blocks")}
            or _edges(child) != _edges(child_record["after"])):
        raise WorkflowError("attachment dependency graph drifted")
    return primary


def reconcile_attachment(
    root, request_sha256, expected_journal_sha256, expected_plan_sha256,
    expected_tracker_sha256, runner=None, *, registry=DEFAULT_REGISTRY,
):
    runner = runner or CommandRunner()
    pins = {
        "request_sha256": request_sha256, "journal_sha256": expected_journal_sha256,
        "plan_sha256": expected_plan_sha256, "tracker_sha256": expected_tracker_sha256,
    }
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in pins.values()):
        raise WorkflowError("reconciliation requires four exact SHA-256 values")
    context = build_context(root, registry)
    if context["workspace"]["location"] != "linked-worktree":
        raise WorkflowError("attachment recovery requires the registered task worktree")
    spec = active_begin_spec(runner, root)
    require_workspace(runner, spec, context)
    path = journal_path(runner, spec)
    before_image = _image(path)
    journal = load_journal(path)
    if journal is None or journal["phase"] != "ready":
        raise WorkflowError("attachment recovery requires the existing ready journal")
    intent = journal.get("coordination", {}).get(request_sha256, {})
    request = intent.get("request", {})
    blocker = request.get("fields", {}).get("blocker", "")
    if (request != {"action": "depend", "bead_id": spec.bead_id, "fields": {"blocker": blocker}}
            or not BEAD_PATTERN.fullmatch(blocker) or blocker == spec.bead_id
            or blocker.split("-", 1)[0] != spec.bead_id.split("-", 1)[0]
            or _sha(canonical_json(request).encode()) != request_sha256):
        raise WorkflowError("not the exact recorded same-store dependency request")
    if any(key != request_sha256 and value.get("state") != "verified"
           for key, value in journal["coordination"].items()):
        raise WorkflowError("another coordination transaction is unresolved")
    plan, tracker = _current_plan(root), _active_tracker(root, spec.bead_id)
    plan_image, tracker_image = _image(plan), _image(tracker)
    if _sha(plan_image[0]) != expected_plan_sha256 or _sha(tracker_image[0]) != expected_tracker_sha256:
        raise WorkflowError("attachment plan/tracker digest drift")
    attached = journal.get("attached_bead_ids", [])
    if (not isinstance(attached, list) or len(attached) != len(set(attached))
            or spec.bead_id in attached):
        raise WorkflowError("invalid existing attachment membership")
    expected = attached if blocker in attached else [*attached, blocker]
    if plan_bead_ids(root) != [spec.bead_id] or _attached_bead_ids(plan_image[0].decode()) != expected:
        raise WorkflowError("plan is not the exact one-Bead attachment postimage")
    primary = _beads(runner, context, spec, journal, intent, blocker)
    title = journal["external_ownership"][blocker]["after"]["title"]
    if tracker_image[0].decode().splitlines().count(f"- `{blocker}` — {title}") != 1:
        raise WorkflowError("tracker is not the exact attachment postimage")
    backup = path.with_name(f"{path.stem}.attachment-{request_sha256}-{expected_journal_sha256}.before.json")
    if intent.get("state") == "verified":
        backup_image = _image(backup)
        if (intent.get("attachment_recovery") != pins
                or _sha(backup_image[0]) != expected_journal_sha256
                or backup_image[1:] != before_image[1:]):
            raise WorkflowError("not an exact completed attachment recovery")
        check_active_ownership(runner, root, registry=registry)
        if "STATE: READY" not in run_readiness(runner, root):
            raise WorkflowError("attachment recovery replay is not ready")
        _beads(runner, context, spec, journal, intent, blocker)
        if _image(path) != before_image or _image(plan) != plan_image or _image(tracker) != tracker_image:
            raise WorkflowError("attachment recovery replay changed inputs")
        return result_payload("reconcile-attachment", "unchanged", request_sha256=request_sha256)
    if intent.get("state") != "pending" or _sha(before_image[0]) != expected_journal_sha256:
        raise WorkflowError("attachment journal digest/state drift")
    _backup(backup, before_image)
    if _image(path) != before_image or _image(plan) != plan_image or _image(tracker) != tracker_image:
        raise WorkflowError("attachment inputs changed before reconciliation")
    journal["attached_bead_ids"] = expected
    staged = (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode()
    staged_image = (staged, *before_image[1:])
    try:
        _write_image(path, staged_image)
        check_active_ownership(runner, root, registry=registry)
        if "STATE: READY" not in run_readiness(runner, root):
            raise WorkflowError("attachment reconciliation is not ready")
        primary = _beads(runner, context, spec, journal, intent, blocker)
        if _image(plan) != plan_image or _image(tracker) != tracker_image or _image(path) != staged_image:
            raise WorkflowError("attachment inputs changed during reconciliation")
        intent.update(state="verified", result_bead=spec.bead_id, after=primary,
                      before_sha256=bead_digest(intent["before"]), after_sha256=bead_digest(primary),
                      attachment_recovery=pins)
        final_image = ((json.dumps(journal, indent=2, sort_keys=True) + "\n").encode(), *before_image[1:])
        _write_image(path, final_image)
        if _image(path) != final_image:
            raise WorkflowError("completed attachment journal readback differs")
    except Exception as exc:
        current = _image(path)
        if current == staged_image:
            _write_image(path, before_image)
            if _image(path) != before_image:
                raise WorkflowError("attachment rollback verification failed") from exc
        elif current != before_image:
            raise WorkflowError("unexpected journal mutation; rollback refused, preserve evidence") from exc
        raise
    return result_payload("reconcile-attachment", "reconciled", request_sha256=request_sha256,
                          journal=str(path), backup=str(backup), bead_id=blocker)
