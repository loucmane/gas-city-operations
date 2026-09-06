"""Exact-plan recovery of a derived session binding; no historical-file edits."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from aegis_foundation.gate import session_transition
from aegis_foundation.gate.session_authority import SessionAuthorityError
from aegis_foundation.version import SCHEMA_VERSION
from tests.meta_workflow_guard.test_daily_session_authority import (
    active_fixture as _active_fixture, advance_tracked_session, snapshot,
)
from tests.meta_workflow_guard.test_codex_task import load_task_module
from tests.meta_workflow_guard.test_source_checkout_closeout import _commit_fixture


def active_fixture(tmp_path):
    root, active, work = _active_fixture(tmp_path)
    work["schema_version"] = SCHEMA_VERSION
    core = {k:v for k,v in work.items() if k not in {"created_at", "updated_at", "recovery"}}
    work["recovery"]["fingerprint"] = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (root / ".aegis/state/current-work.json").write_text(json.dumps(work))
    _commit_fixture(root)
    return root, active, work


def reconcile(*args, **kwargs):
    from aegis_foundation.gate.session_reconciliation import reconcile_source_session
    return reconcile_source_session(*args, **kwargs)


def mismatch(tmp_path):
    root, active, work = active_fixture(tmp_path)
    current = advance_tracked_session(root)
    return root, active, work, current


def test_plan_is_read_only_and_apply_changes_only_derived_binding(tmp_path):
    root, _, old, current = mismatch(tmp_path)
    before = snapshot(root)
    plan = reconcile(root, "ga-test1")
    assert plan["needed"] is True
    assert snapshot(root) == before
    result = reconcile(root, "ga-test1", expect_plan_id=plan["plan_id"])
    assert result["status"] == "applied"
    work = json.loads((root / ".aegis/state/current-work.json").read_text())
    assert work["paths"]["session"] == current.relative_to(root).as_posix()
    expected = copy.deepcopy(old)
    expected["paths"]["session"] = work["paths"]["session"]
    expected["recovery"]["fingerprint"] = work["recovery"]["fingerprint"]
    assert work == expected
    after = snapshot(root)
    assert {p for p in before if before[p] != after[p]} == {".aegis/state/current-work.json"}
    assert set(after) - set(before) == {session_transition.JOURNAL}
    assert reconcile(root, "ga-test1", expect_plan_id=plan["plan_id"])["status"] == "already_applied"
    assert snapshot(root) == after


def test_unknown_plan_id_refuses_without_any_write(tmp_path):
    root, _, _, _ = mismatch(tmp_path)
    before = snapshot(root)
    with pytest.raises(SessionAuthorityError, match="plan"):
        reconcile(root, "ga-test1", expect_plan_id="f" * 64)
    assert snapshot(root) == before


def test_plan_pins_authority_file_bytes_not_only_semantics(tmp_path):
    root, _, work, _ = mismatch(tmp_path)
    plan = reconcile(root, "ga-test1")
    path = root / work["paths"]["plan"]
    path.write_text(path.read_text() + "\n")
    before = snapshot(root)
    with pytest.raises(SessionAuthorityError, match="plan"):
        reconcile(root, "ga-test1", expect_plan_id=plan["plan_id"])
    assert snapshot(root) == before


@pytest.mark.parametrize("field", ["task", "plan", "fingerprint", "session-state", "schema"])
def test_only_stale_session_binding_is_repairable(tmp_path, field):
    root, _, work, _ = mismatch(tmp_path)
    if field == "session-state":
        path = root / "sessions/state.json"
        value = json.loads(path.read_text())
        value["current"] = "different-session.md"
    else:
        path = root / ".aegis/state/current-work.json"
        value = copy.deepcopy(work)
        if field == "task":
            value["task"]["title"] = "unreviewed identity drift"
        elif field == "plan":
            value["paths"]["plan"] = "plans/other.md"
        elif field == "schema":
            value["schema_version"] = "unsupported-version"
        else:
            value["recovery"]["fingerprint"] = "f" * 64
        if field != "fingerprint":
            core = {k:v for k,v in value.items() if k not in {"created_at", "updated_at", "recovery"}}
            value["recovery"]["fingerprint"] = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    path.write_text(json.dumps(value))
    before = snapshot(root)
    with pytest.raises((SessionAuthorityError, ValueError)):
        reconcile(root, "ga-test1")
    assert snapshot(root) == before


def test_write_failure_restores_exact_envelope_and_retains_rollback(tmp_path, monkeypatch):
    root, _, _, _ = mismatch(tmp_path)
    plan = reconcile(root, "ga-test1")
    before = snapshot(root)
    install = session_transition._install
    failed = False
    def fail_once(path, value):
        nonlocal failed
        if path.name == "current-work.json" and not failed:
            failed = True
            install(path, value)
            raise OSError("injected post-replace failure")
        return install(path, value)
    monkeypatch.setattr(session_transition, "_install", fail_once)
    with pytest.raises(OSError, match="injected"):
        reconcile(root, "ga-test1", expect_plan_id=plan["plan_id"])
    after = snapshot(root)
    assert all(after[p] == before[p] for p in before)
    assert json.loads((root / session_transition.JOURNAL).read_text())["status"] == "rolled_back"


def test_current_authority_is_noop_and_unknown_replay_refuses(tmp_path):
    root, _, _ = active_fixture(tmp_path)
    before = snapshot(root)
    assert reconcile(root, "ga-test1")["needed"] is False
    with pytest.raises(SessionAuthorityError, match="replay"):
        reconcile(root, "ga-test1", expect_plan_id="f" * 64)
    assert snapshot(root) == before


def test_pending_transaction_and_competing_writer_refuse(tmp_path):
    root, _, _, _ = mismatch(tmp_path)
    before = snapshot(root)
    with session_transition.session_lock(root):
        with pytest.raises(SessionAuthorityError, match="in use"):
            reconcile(root, "ga-test1")
    assert snapshot(root) == before
    (root / session_transition.JOURNAL).write_text('{"status":"pending"}')
    before = snapshot(root)
    with pytest.raises(SessionAuthorityError, match="pending"):
        reconcile(root, "ga-test1")
    assert snapshot(root) == before


def test_cli_is_read_only_by_default_and_requires_exact_plan_for_apply(tmp_path, monkeypatch, capsys):
    root, _, _, _ = mismatch(tmp_path)
    module = load_task_module()
    parser = module.build_parser()
    monkeypatch.setattr(module, "REPO_ROOT", root)
    args = parser.parse_args(["sessions", "reconcile-current", "--bead", "ga-test1"])
    before = snapshot(root)
    args.func(args)
    plan = json.loads(capsys.readouterr().out)
    assert plan["needed"] is True and snapshot(root) == before
    args = parser.parse_args(["sessions", "reconcile-current", "--bead", "ga-test1", "--expect-plan-id", plan["plan_id"]])
    args.func(args)
    assert json.loads(capsys.readouterr().out)["status"] == "applied"


@pytest.mark.parametrize("value", [[], {"paths": [], "recovery": {}}, {"paths": {}, "recovery": []}])
def test_malformed_envelope_is_pre_mutation_refusal(tmp_path, value):
    root, _, _, _ = mismatch(tmp_path)
    (root / ".aegis/state/current-work.json").write_text(json.dumps(value))
    before = snapshot(root)
    with pytest.raises(SessionAuthorityError, match="shape"):
        reconcile(root, "ga-test1")
    assert snapshot(root) == before


def test_missing_prior_history_is_not_reconstructed(tmp_path):
    root, _, old, _ = mismatch(tmp_path)
    (root / old["paths"]["session"]).unlink()
    before = snapshot(root)
    with pytest.raises(SessionAuthorityError, match="prior session"):
        reconcile(root, "ga-test1")
    assert snapshot(root) == before


def test_wrong_writer_identity_refuses_before_transaction(tmp_path, monkeypatch):
    root, _, _, _ = mismatch(tmp_path)
    import os
    uid = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: uid + 1)
    before = snapshot(root)
    with pytest.raises(SessionAuthorityError, match="writer identity"):
        reconcile(root, "ga-test1")
    assert snapshot(root) == before


def test_envelope_changed_before_transaction_is_preserved(tmp_path, monkeypatch):
    from aegis_foundation.gate import session_reconciliation as module
    root, _, _, _ = mismatch(tmp_path)
    plan = reconcile(root, "ga-test1")
    original = module.SessionTransition
    changed = None
    def concurrent_change(*args, **kwargs):
        nonlocal changed
        path = root / ".aegis/state/current-work.json"
        path.write_text(path.read_text() + "\n")
        changed = snapshot(root)
        return original(*args, **kwargs)
    monkeypatch.setattr(module, "SessionTransition", concurrent_change)
    with pytest.raises(SessionAuthorityError, match="before transaction"):
        reconcile(root, "ga-test1", expect_plan_id=plan["plan_id"])
    assert snapshot(root) == changed
