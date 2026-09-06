"""Explicit exact-plan reconciliation of one stale source-session envelope.

This does not edit session history, pointers, plans, Beads or permission policy.
Planning is read-only. Applying requires the full current plan digest; the existing
session transaction retains exact images and refuses pending/ambiguous recovery.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import date
from pathlib import Path

from ..version import SCHEMA_VERSION
from .session_authority import (
    SessionAuthorityError, assert_no_pending_continuation, contained_path,
    verify_session_authority,
)
from .session_transition import JOURNAL, SessionTransition, image, session_lock
from .state import run_git, text_references_work

ENVELOPE = ".aegis/state/current-work.json"


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _pin(root: Path, relative: str) -> str:
    return _digest(image(contained_path(root, relative, "reconciliation input", leaf_link=True)))


def _prepare(root: Path, bead: str):
    # This command is source-checkout recovery, not an installer/runtime reset.
    from scripts._source_workflow_state import (
        _active_source_current_work_payload, derive_active_source_work,
        is_uninstalled_aegis_source_checkout,
    )
    if not is_uninstalled_aegis_source_checkout(root):
        raise SessionAuthorityError("reconciliation requires an uninstalled source checkout")
    assert_no_pending_continuation(root)
    code, branch, _ = run_git(root, "branch", "--show-current")
    if code:
        raise SessionAuthorityError("cannot bind reconciliation branch")
    code, head, _ = run_git(root, "rev-parse", "HEAD")
    if code:
        raise SessionAuthorityError("cannot bind reconciliation HEAD")
    active = derive_active_source_work(root, branch)
    if active.work_kind != "bead" or active.work_id != bead:
        raise SessionAuthorityError("reconciliation Bead identity mismatch")
    path = contained_path(root, ENVELOPE, "reconciliation envelope")
    before_image = image(path)
    if before_image["kind"] != "file":
        raise SessionAuthorityError("reconciliation requires an existing regular envelope")
    if (before_image["uid"], before_image["gid"]) != (os.geteuid(), os.getegid()):
        raise SessionAuthorityError("reconciliation envelope requires another writer identity")
    before = json.loads(path.read_text())
    if (not isinstance(before, dict) or not isinstance(before.get("paths"), dict)
            or not isinstance(before.get("recovery"), dict)):
        raise SessionAuthorityError("reconciliation envelope shape is invalid")
    expected = _active_source_current_work_payload(
        root, active, schema_version=SCHEMA_VERSION,
        recovered_at=before.get("created_at"),
    )
    core = {k:v for k,v in before.items() if k not in {"created_at", "updated_at", "recovery"}}
    recovery = before.get("recovery", {})
    if recovery.get("kind") != "tracked-source-lifecycle" or recovery.get("fingerprint") != _digest(core):
        raise SessionAuthorityError("reconciliation refuses invalid original recovery fingerprint")
    old = contained_path(root, before["paths"]["session"], "prior session")
    if not old.is_file() or not text_references_work(old.read_text(), bead):
        raise SessionAuthorityError("reconciliation prior session is missing or belongs to another Bead")
    new = active.session_path
    after = copy.deepcopy(before)
    after["paths"]["session"] = new.relative_to(root).as_posix()
    after["recovery"]["fingerprint"] = expected["recovery"]["fingerprint"]
    after_core = {k:v for k,v in after.items() if k not in {"created_at", "updated_at", "recovery"}}
    expected_core = {k:v for k,v in expected.items() if k not in {"created_at", "updated_at", "recovery"}}
    if after_core != expected_core:
        raise SessionAuthorityError("reconciliation refuses drift beyond the daily session binding")
    verify_session_authority(root, after)
    needed = old != new
    if needed and date.fromisoformat(old.name[:10]) >= date.fromisoformat(new.name[:10]):
        raise SessionAuthorityError("reconciliation requires a later tracked daily session")
    relatives = {ENVELOPE, old.relative_to(root).as_posix(), new.relative_to(root).as_posix(),
                 active.plan_path.relative_to(root).as_posix(),
                 (active.active_folder / "TRACKER.md").relative_to(root).as_posix(),
                 "sessions/current", "sessions/state.json", "plans/current"}
    inputs = {rel: _pin(root, rel) for rel in sorted(relatives)}
    if image(path) != before_image or inputs[ENVELOPE] != _digest(before_image):
        raise SessionAuthorityError("reconciliation envelope changed during planning")
    encoded = (json.dumps(after, indent=2, sort_keys=True) + "\n").encode()
    plan = {"schema": "aegis.source-session-reconciliation.v1", "root": str(root),
            "bead": bead, "head": head, "branch": branch, "needed": needed,
            "inputs": inputs, "before_session": old.relative_to(root).as_posix(),
            "after_session": new.relative_to(root).as_posix(),
            "executor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "after_sha256": hashlib.sha256(encoded).hexdigest()}
    return {**plan, "plan_id": _digest(plan)}, after, encoded


def reconcile_source_session(root: Path, bead: str, *, expect_plan_id: str | None = None):
    root = Path(root).expanduser().resolve()
    with session_lock(root):
        plan, after, encoded = _prepare(root, bead)
        if expect_plan_id is None:
            return plan
        if not plan["needed"]:
            journal = contained_path(root, JOURNAL, "reconciliation journal")
            record = json.loads(journal.read_text()) if journal.is_file() else {}
            prior = record.get("reconciliation", {})
            steps = record.get("steps", [])
            if (record.get("status") != "complete" or prior.get("plan_id") != expect_plan_id
                    or _digest({k:v for k,v in prior.items() if k != "plan_id"}) != expect_plan_id
                    or prior.get("root") != str(root) or prior.get("bead") != bead
                    or prior.get("head") != plan["head"] or prior.get("branch") != plan["branch"]
                    or len(steps) != 1 or steps[0].get("path") != ENVELOPE
                    or image(root / ENVELOPE) != steps[0].get("after")
                    or not prior.get("inputs")
                    or any(_pin(root, rel) != pin for rel, pin in prior["inputs"].items() if rel != ENVELOPE)):
                raise SessionAuthorityError("reconciliation replay does not match the completed exact plan")
            return {"status": "already_applied", "plan_id": expect_plan_id}
        if plan["plan_id"] != expect_plan_id:
            raise SessionAuthorityError("reconciliation plan drift or incorrect plan id")
        transaction = SessionTransition(root, bead, [root / ENVELOPE], lock_held=True)
        if (_digest(transaction.before[ENVELOPE]) != plan["inputs"][ENVELOPE]
                or any(_pin(root, rel) != pin for rel, pin in plan["inputs"].items())):
            raise SessionAuthorityError("reconciliation inputs changed before transaction")
        transaction.record["reconciliation"] = plan
        with transaction:
            transaction.write(root / ENVELOPE, encoded)
            verify_session_authority(root, after, during_transition=True)
            if any(_pin(root, rel) != pin for rel, pin in plan["inputs"].items() if rel != ENVELOPE):
                raise SessionAuthorityError("reconciliation authority changed during apply")
        return {"status": "applied", "plan_id": expect_plan_id,
                "journal_id": transaction.record["id"]}
