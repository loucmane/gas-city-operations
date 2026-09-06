"""ga-e0t1.8: daily session and logging authorities must never diverge."""
from __future__ import annotations

import argparse
import json
import select
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from aegis_foundation.gate.workflow import build_checks
from aegis_foundation.gate import session_transition
from aegis_foundation.gate.session_authority import SessionAuthorityError, verify_session_authority
from scripts import _aegis_installer as installer
from scripts._source_workflow_state import recover_source_current_work
from tests.meta_workflow_guard.test_codex_task import load_task_module
from tests.meta_workflow_guard.test_source_checkout_closeout import (
    _activate_bead_source_state,
    _init_bead_source_repo,
)

BRANCH = "codex/ga-test1-source-closeout"


def active_fixture(tmp_path):
    root, _ = _init_bead_source_repo(tmp_path)
    active = _activate_bead_source_state(root)
    tracker = active / "TRACKER.md"
    tracker.write_text(tracker.read_text() + "\n## Progress Log\n")
    state = recover_source_current_work(root, BRANCH, schema_version="fixture-v1")
    return root, active, state


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): ("link", p.readlink().as_posix()) if p.is_symlink()
        else ("file", p.read_bytes(), p.stat().st_mode & 0o777)
        for p in root.rglob("*")
        if ".git" not in p.relative_to(root).parts and (p.is_symlink() or p.is_file())
    }


def advance_tracked_session(root):
    old = (root / "sessions/current").resolve()
    new = old.with_name(old.name.replace("2030-01-01", "2030-01-02"))
    new.write_text(old.read_text().replace("2030-01-01", "2030-01-02"))
    (root / "sessions/current").unlink()
    (root / "sessions/current").symlink_to(new.relative_to(root / "sessions"))
    state = json.loads((root / "sessions/state.json").read_text())
    state["current"] = new.name
    (root / "sessions/state.json").write_text(json.dumps(state))
    return new


def test_logger_refuses_stale_session_before_any_write(tmp_path):
    root, active, _ = active_fixture(tmp_path)
    advance_tracked_session(root)
    before = snapshot(root)
    with pytest.raises(installer.AegisError, match="session"):
        installer.log_work(
            root, handler="fixture", evidence=str(active.relative_to(root) / "TRACKER.md"),
            note="Must never enter yesterday's session", surfaces=("implementation",),
        )
    assert snapshot(root) == before


def test_pending_transaction_blocks_readiness_even_without_envelope(tmp_path):
    root, _, _ = active_fixture(tmp_path)
    (root / ".aegis/state/current-work.json").unlink()
    (root / session_transition.JOURNAL).write_text('{"status":"pending"}')
    before = snapshot(root)
    _, checks = build_checks(root)
    assert any(c.status == "BLOCKED" and "session" in c.message for c in checks)
    assert snapshot(root) == before


def test_session_state_unrelated_fields_are_preserved(tmp_path, monkeypatch):
    root, _, _ = active_fixture(tmp_path)
    path = root / "sessions/state.json"
    state = json.loads(path.read_text())
    state.update(paused=["preserved-paused-session"], custom={"owner_note": "keep"})
    path.write_text(json.dumps(state))
    module = continuation_module(root, monkeypatch)
    module.handle_sessions_continue(continuation_args())
    actual = json.loads(path.read_text())
    assert actual["paused"] == state["paused"]
    assert actual["custom"] == state["custom"]


def test_overlapping_writer_is_refused_without_mutation(tmp_path, monkeypatch):
    root, _, work = active_fixture(tmp_path)
    module = continuation_module(root, monkeypatch)
    before = snapshot(root)
    with session_transition.session_lock(root):
        with pytest.raises(SessionAuthorityError, match="in use"):
            module.handle_sessions_continue(continuation_args())
        with pytest.raises(SessionAuthorityError, match="in use"):
            installer.log_work(root, handler="fixture", evidence=work["paths"]["plan"], note="refuse")
        _, checks = build_checks(root)
        assert any(c.status == "BLOCKED" and "in use" in c.message for c in checks)
    assert snapshot(root) == before


def test_readiness_blocks_stale_logging_target(tmp_path):
    root, _, _ = active_fixture(tmp_path)
    advance_tracked_session(root)
    before = snapshot(root)
    _, checks = build_checks(root)
    assert any(c.status == "BLOCKED" and "session" in c.message.lower() for c in checks)
    assert snapshot(root) == before


def continuation_module(root, monkeypatch):
    module = load_task_module()
    values = {
        "REPO_ROOT": root,
        "SESSIONS_DIR": root / "sessions",
        "PLANS_DIR": root / "plans",
        "WORK_TRACKING_BASE": root / "docs/ai/work-tracking/active",
        "WORK_TRACKING_ACTIVE_REL": "docs/ai/work-tracking/active",
        "PLAN_CURRENT": root / "plans/current",
        "PLAN_STATE_DIR": root / ".plan_state",
        "PLAN_SYNC_LOG": root / ".plan_state/sync.log",
        "SESSION_STATE_PATH": root / "sessions/state.json",
    }
    for name, value in values.items():
        monkeypatch.setattr(module, name, value)

    class NextDay(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2030, 1, 2, 12, 0, 0)
            return value if tz is None else value.replace(tzinfo=tz)

    monkeypatch.setattr(module, "datetime", NextDay)
    monkeypatch.setattr(module, "_source_checkout_branch", lambda: BRANCH)
    return module


def continuation_args():
    return argparse.Namespace(
        task=None, bead="ga-test1", slug="source-closeout", title=None, work=None,
        folder=None, plan=None, task_source="ga-e0t1.8 synthetic regression", dry_run=False,
    )


def test_continuation_updates_existing_logging_envelope(tmp_path, monkeypatch):
    root, _, old = active_fixture(tmp_path)
    module = continuation_module(root, monkeypatch)
    module.handle_sessions_continue(continuation_args())
    new = json.loads((root / ".aegis/state/current-work.json").read_text())
    assert new["paths"]["session"] == (root / "sessions/current").resolve().relative_to(root).as_posix()
    assert new["task"] == old["task"]
    assert new["authority"] == old["authority"]
    assert new["paths"]["plan"] == old["paths"]["plan"]


def test_continuation_replay_is_byte_and_mode_identical(tmp_path, monkeypatch):
    root, _, _ = active_fixture(tmp_path)
    module = continuation_module(root, monkeypatch)
    module.handle_sessions_continue(continuation_args())
    before = snapshot(root)
    module.handle_sessions_continue(continuation_args())
    assert snapshot(root) == before


def test_missing_envelope_recovers_new_tracked_session(tmp_path, monkeypatch):
    root, _, _ = active_fixture(tmp_path)
    (root / ".aegis/state/current-work.json").unlink()
    module = continuation_module(root, monkeypatch)
    module.handle_sessions_continue(continuation_args())
    recovered = installer._current_work_payload(root)
    session, _ = verify_session_authority(root, recovered)
    assert session.name.startswith("2030-01-02-")
    before = snapshot(root)
    assert installer._current_work_payload(root) == recovered
    assert snapshot(root) == before


@pytest.mark.parametrize("drift", ["bead", "plan", "state", "stale", "symlink", "missing_paths"])
def test_contradiction_refuses_logging_and_continuation_before_writes(tmp_path, monkeypatch, drift):
    root, active, work = active_fixture(tmp_path)
    path = root / ".aegis/state/current-work.json"
    if drift == "missing_paths":
        work.pop("paths")
        path.write_text(json.dumps(work))
    elif drift == "bead":
        work["task"]["id"] = "ga-other"
        path.write_text(json.dumps(work))
    elif drift == "plan":
        plan = (root / "plans/current").resolve()
        plan.write_text(plan.read_text().replace("ga-test1", "ga-other"))
    elif drift == "state":
        (root / "sessions/state.json").write_text('{"current":"wrong.md"}')
    elif drift == "stale":
        advance_tracked_session(root)
    else:
        session = (root / "sessions/current").resolve()
        outside = tmp_path / "outside-session.md"
        outside.write_bytes(session.read_bytes())
        session.unlink()
        session.symlink_to(outside)
    before = snapshot(root)
    with pytest.raises(installer.AegisError):
        installer.log_work(root, handler="fixture", evidence=str(active.relative_to(root) / "TRACKER.md"), note="refuse")
    assert snapshot(root) == before
    module = continuation_module(root, monkeypatch)
    with pytest.raises((SessionAuthorityError, module.TaskError)):
        module.handle_sessions_continue(continuation_args())
    assert snapshot(root) == before


def without_transaction_evidence(files):
    return {p: v for p, v in files.items()
            if not p.startswith(".aegis/state/session-continuation")}


@pytest.mark.parametrize("failure_surface", ["session", "state", "envelope", "sync"])
def test_partial_failure_restores_exact_before_images(tmp_path, monkeypatch, failure_surface):
    root, _, _ = active_fixture(tmp_path)
    (root / ".aegis/state/current-work.json").chmod(0o640)
    before = snapshot(root)
    module = continuation_module(root, monkeypatch)
    original = session_transition._install
    failed = False

    def fail_once(path, value):
        nonlocal failed
        targets = {"session": path.name.startswith("2030-01-02-"),
                   "state": path == root / "sessions/state.json",
                   "envelope": path == root / ".aegis/state/current-work.json",
                   "sync": path == root / ".plan_state/sync.log"}
        if targets[failure_surface] and not failed:
            failed = True
            original(path, value)  # Simulate failure AFTER the atomic replacement.
            raise OSError("injected post-replacement failure")
        return original(path, value)

    monkeypatch.setattr(session_transition, "_install", fail_once)
    with pytest.raises(OSError, match="injected"):
        module.handle_sessions_continue(continuation_args())
    assert failed
    assert without_transaction_evidence(snapshot(root)) == without_transaction_evidence(before)
    journal = json.loads((root / session_transition.JOURNAL).read_text())
    assert journal["status"] == "rolled_back"
    assert journal["steps"] and all("before" in s and "after" in s for s in journal["steps"])
    # A corrected replay is safe; the failed attempt remains archived.
    module.handle_sessions_continue(continuation_args())
    assert (root / f'.aegis/state/session-continuations/{journal["id"]}.json').is_file()
    assert (root / "sessions/current").resolve().name.startswith("2030-01-02-")


def test_same_day_log_and_envelope_recovery_remain_supported(tmp_path, monkeypatch):
    root, active, work = active_fixture(tmp_path)
    class SameDay(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2030, 1, 1, 12)
            return value if tz is None else value.replace(tzinfo=tz)
    monkeypatch.setattr(installer, "datetime", SameDay)
    before = (root / work["paths"]["session"]).read_text()
    installer.log_work(root, handler="fixture", evidence=str(active.relative_to(root) / "TRACKER.md"),
                       note="same-day evidence", surfaces=("implementation",))
    after = (root / work["paths"]["session"]).read_text()
    assert len(after) > len(before) and "S:20300101" in after


def test_pending_transaction_blocks_logger_without_recovering_envelope(tmp_path):
    root, active, _ = active_fixture(tmp_path)
    (root / ".aegis/state/current-work.json").unlink()
    (root / session_transition.JOURNAL).write_text('{"status":"pending"}')
    before = snapshot(root)
    with pytest.raises(installer.AegisError, match="pending"):
        installer.log_work(root, handler="fixture", evidence=str(active.relative_to(root) / "TRACKER.md"), note="refuse")
    assert snapshot(root) == before


def test_ambiguous_mutation_is_preserved_and_leaves_pending_transaction(tmp_path, monkeypatch):
    root, _, _ = active_fixture(tmp_path)
    module = continuation_module(root, monkeypatch)
    original = session_transition._install
    foreign = b"foreign mutation must survive\n"
    changed = None

    def fail_with_foreign_write(path, value):
        nonlocal changed
        if path == root / "sessions/state.json":
            changed = (root / "sessions/current").resolve()
            changed.write_bytes(foreign)
            raise OSError("injected concurrent mutation")
        return original(path, value)

    monkeypatch.setattr(session_transition, "_install", fail_with_foreign_write)
    with pytest.raises(SessionAuthorityError, match="rollback is unresolved"):
        module.handle_sessions_continue(continuation_args())
    assert changed is not None and changed.read_bytes() == foreign
    journal = json.loads((root / session_transition.JOURNAL).read_text())
    assert journal["status"] == "pending"
    _, checks = build_checks(root)
    assert any(c.status == "BLOCKED" and "session" in c.message for c in checks)


def test_dry_run_creates_no_files_or_directories(tmp_path, monkeypatch):
    root, _, _ = active_fixture(tmp_path)
    module = continuation_module(root, monkeypatch)
    args = continuation_args()
    args.dry_run = True
    before = snapshot(root)
    directories = {str(p) for p in root.rglob("*") if p.is_dir()}
    module.handle_sessions_continue(args)
    assert snapshot(root) == before
    assert {str(p) for p in root.rglob("*") if p.is_dir()} == directories


def test_recovery_fingerprint_drift_is_not_resealed_by_continuation(tmp_path, monkeypatch):
    root, _, work = active_fixture(tmp_path)
    work["recovery"]["fingerprint"] = "0" * 64
    (root / ".aegis/state/current-work.json").write_text(json.dumps(work))
    module = continuation_module(root, monkeypatch)
    before = snapshot(root)
    with pytest.raises(SessionAuthorityError, match="fingerprint"):
        module.handle_sessions_continue(continuation_args())
    assert snapshot(root) == before


def test_legacy_readiness_refuses_the_same_stale_envelope_as_logging(tmp_path):
    from tests.claude_adapter.test_readiness_gate import make_repo, write_aegis_current_work

    root = make_repo(tmp_path)
    write_aegis_current_work(root)
    path = root / ".aegis/state/current-work.json"
    work = json.loads(path.read_text())
    work["paths"] = {name: (root / f"{name}s/current").resolve().relative_to(root).as_posix()
                     for name in ("session", "plan")}
    path.write_text(json.dumps(work))
    _, checks = build_checks(root)
    assert all(c.status == "READY" for c in checks), checks
    old = (root / "sessions/current").resolve()
    new = old.with_name("2030-01-02-001-task103-next-day.md")
    new.write_bytes(old.read_bytes())
    (root / "sessions/current").unlink()
    (root / "sessions/current").symlink_to(new.relative_to(root / "sessions"))
    state = json.loads((root / "sessions/state.json").read_text())
    state["current"] = new.name
    (root / "sessions/state.json").write_text(json.dumps(state))
    before = snapshot(root)
    with pytest.raises(installer.AegisError, match="session"):
        installer.log_work(root, handler="fixture", evidence=work["paths"]["plan"], note="refuse")
    _, checks = build_checks(root)
    assert any(c.status == "BLOCKED" and "session authority" in c.message for c in checks)
    assert snapshot(root) == before


def test_legacy_envelope_without_paths_is_not_ready(tmp_path):
    from tests.claude_adapter.test_readiness_gate import make_repo, write_aegis_current_work

    root = make_repo(tmp_path)
    write_aegis_current_work(root)
    path = root / ".aegis/state/current-work.json"
    work = json.loads(path.read_text())
    work.pop("paths")
    path.write_text(json.dumps(work))
    before = snapshot(root)
    _, checks = build_checks(root)
    assert any(c.status == "BLOCKED" and "session authority" in c.message for c in checks)
    assert snapshot(root) == before


@pytest.mark.parametrize("spelling", ["absolute", "alias", "home"])
def test_logger_locks_the_same_normalized_root_it_writes(tmp_path, monkeypatch, spelling):
    root, _, work = active_fixture(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    monkeypatch.setenv("HOME", str(root.parent))
    target = {"absolute": root, "alias": alias, "home": Path("~") / root.name}[spelling]
    assert installer._resolve_target_root(target) == root
    before = snapshot(root)
    with session_transition.session_lock(root):
        with pytest.raises(SessionAuthorityError, match="in use"):
            installer.log_work(target, handler="fixture", evidence=work["paths"]["plan"], note="refuse")
    assert snapshot(root) == before


def test_logger_does_not_climb_from_subdirectory_to_parent_authority(tmp_path):
    root, _, work = active_fixture(tmp_path)
    nested = root / "nested"
    nested.mkdir()
    assert installer._resolve_target_root(nested) == nested
    before = snapshot(root)
    with session_transition.session_lock(root):
        with pytest.raises(installer.AegisError):
            installer.log_work(nested, handler="fixture", evidence=work["paths"]["plan"], note="refuse")
    assert snapshot(root) == before


@pytest.mark.parametrize("drift", ["missing_state", "dangling_pointer", "absolute_path", "parent_path"])
def test_reviewed_migration_negatives_refuse_before_logging(tmp_path, drift):
    root, _, work = active_fixture(tmp_path)
    if drift == "missing_state":
        (root / "sessions/state.json").unlink()
    elif drift == "dangling_pointer":
        (root / "sessions/current").unlink()
        (root / "sessions/current").symlink_to("missing-session.md")
    else:
        work.pop("recovery", None)  # Exercise containment independently of fingerprint refusal.
        work["paths"]["session"] = "/outside.md" if drift == "absolute_path" else "../outside.md"
        (root / ".aegis/state/current-work.json").write_text(json.dumps(work))
    before = snapshot(root)
    with pytest.raises(installer.AegisError):
        installer.log_work(root, handler="fixture", evidence=work["paths"]["plan"], note="refuse")
    _, checks = build_checks(root)
    assert any(c.status == "BLOCKED" and "session authority" in c.message for c in checks)
    assert snapshot(root) == before


def test_pending_after_images_block_every_writer_and_readiness(tmp_path):
    root, _, work = active_fixture(tmp_path)
    state_path = root / "sessions/state.json"
    before_image = session_transition.image(state_path)
    state = json.loads(state_path.read_text())
    state["fixture_after_image"] = True
    state_path.write_text(json.dumps(state))
    journal = {"schema": session_transition.SCHEMA, "id": "a" * 32, "bead": "ga-test1",
               "status": "pending", "created_directories": [], "steps": [{
                   "path": "sessions/state.json", "before": before_image,
                   "after": session_transition.image(state_path)}]}
    (root / session_transition.JOURNAL).write_text(json.dumps(journal))
    before = snapshot(root)
    with pytest.raises(installer.AegisError, match="pending"):
        installer.log_work(root, handler="fixture", evidence=work["paths"]["plan"], note="refuse")
    with pytest.raises(SessionAuthorityError, match="pending"):
        with session_transition.SessionTransition(root, "ga-test1", [state_path]):
            pytest.fail("a pending after-image must not start another transaction")
    _, checks = build_checks(root)
    assert any(c.status == "BLOCKED" and "pending" in c.message for c in checks)
    assert snapshot(root) == before


def test_successful_continuation_preserves_nonstandard_envelope_mode(tmp_path, monkeypatch):
    root, _, _ = active_fixture(tmp_path)
    path = root / ".aegis/state/current-work.json"
    path.chmod(0o640)
    before = path.stat()
    continuation_module(root, monkeypatch).handle_sessions_continue(continuation_args())
    after = path.stat()
    assert (after.st_mode, after.st_uid, after.st_gid) == (before.st_mode, before.st_uid, before.st_gid)


def test_cross_process_lock_prevents_logger_and_continuation(tmp_path, monkeypatch):
    root, _, work = active_fixture(tmp_path)
    command = ("from pathlib import Path; import sys; "
               "from aegis_foundation.gate.session_transition import session_lock; "
               "lock=session_lock(Path(sys.argv[1])); lock.__enter__(); "
               "print('LOCKED', flush=True); sys.stdin.readline(); lock.__exit__(None,None,None)")
    child = subprocess.Popen([sys.executable, "-B", "-c", command, str(root)],
                             cwd=Path(__file__).resolve().parents[2], text=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert select.select([child.stdout], [], [], 10)[0], "fixture child did not acquire lock"
        assert child.stdout.readline().strip() == "LOCKED"
        before = snapshot(root)
        with pytest.raises(SessionAuthorityError, match="in use"):
            installer.log_work(root, handler="fixture", evidence=work["paths"]["plan"], note="refuse")
        with pytest.raises(SessionAuthorityError, match="in use"):
            continuation_module(root, monkeypatch).handle_sessions_continue(continuation_args())
        assert snapshot(root) == before
    finally:
        try:
            _, stderr = child.communicate("release\n", timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()  # Only this owned synthetic test child, never a provider or service.
            child.communicate(timeout=10)
            raise
    assert child.returncode == 0, stderr
