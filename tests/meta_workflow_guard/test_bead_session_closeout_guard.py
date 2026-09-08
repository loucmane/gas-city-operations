"""Beads-native equivalent of the existing same-task multi-day session rule."""
from pathlib import Path

import pytest

from tests.meta_workflow_guard.test_guard_rules import load_guard_module


def session(root: Path, day: str, bead: str, *, complete=True, declared=None):
    path = root / "sessions" / f"{day}-001-{bead}-work.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"**Bead**: `{declared or bead}`\n" + (
        "SESSION COMPLETE — daily recording period only; no Bead completion.\n" if complete else ""
    ))
    return path


def guard(tmp_path, monkeypatch):
    module = load_guard_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "TODAY_ISO", "2030-01-04")
    monkeypatch.setattr(module, "_find_latest_prior_session", lambda: None)
    current = session(tmp_path, "2030-01-04", "ga-example.2", complete=False)
    monkeypatch.setattr(module, "CURRENT_SESSION_PATH", current)
    return module


def test_completed_same_bead_multi_day_sessions_are_recognized(tmp_path, monkeypatch):
    module = guard(tmp_path, monkeypatch)
    old = [session(tmp_path, f"2030-01-0{day}", "ga-example.2") for day in (1, 2, 3)]
    before = {path: path.read_bytes() for path in old}
    assert module.validate_session_edit_dates(old) == []
    assert all(path.read_bytes() == value for path, value in before.items())


@pytest.mark.parametrize("fault", ["foreign", "prefix", "incomplete", "disagreement", "duplicate", "missing"])
def test_bead_history_exception_stays_exact_and_completion_bound(tmp_path, monkeypatch, fault):
    module = guard(tmp_path, monkeypatch)
    bead = {"foreign": "hpf-other", "prefix": "ga-example.20"}.get(fault, "ga-example.2")
    old = session(tmp_path, "2030-01-01", bead, complete=fault != "incomplete",
                  declared="ga-other" if fault == "disagreement" else None)
    if fault == "duplicate":
        old.write_text(old.read_text() + "**Bead**: `ga-other`\n")
    elif fault == "missing":
        old.write_text("SESSION COMPLETE\n")
    before = old.read_bytes()
    assert module.validate_session_edit_dates([old])
    assert old.read_bytes() == before


def test_bead_guard_does_not_reinterpret_legacy_numeric_task_identity(tmp_path):
    module = load_guard_module()
    assert module._session_task_id(tmp_path / "2030-01-01-001-task99-old.md") == "99"


@pytest.mark.parametrize("declared", ["ga-example.0", "ga-example.02", "ga-example.2 extra", "99", "ga-EXAMPLE"])
def test_malformed_bead_cannot_fall_back_to_numeric_slug(tmp_path, declared):
    module = load_guard_module()
    path = session(tmp_path, "2030-01-01", "ga-example.2-task99", declared=declared)
    assert module._session_task_id(path) is None


def test_bead_identity_is_typed_and_supports_nested_children(tmp_path):
    module = load_guard_module()
    path = session(tmp_path, "2030-01-01", "gct-example.2.11")
    assert module._session_task_id(path) == "bead:gct-example.2.11"


def test_symlink_cannot_supply_session_identity(tmp_path):
    module = load_guard_module()
    target = session(tmp_path, "2030-01-01", "ga-example.2")
    alias = tmp_path / "2030-01-02-001-ga-example.2-work.md"
    alias.symlink_to(target)
    assert module._session_task_id(alias) is None


def test_unreadable_bead_session_cannot_supply_identity(tmp_path):
    module = load_guard_module()
    path = tmp_path / "2030-01-01-001-ga-task99-old.md"
    path.write_bytes(b"\xff")
    assert module._session_task_id(path) is None


@pytest.mark.parametrize("exists", [True, False])
def test_bead_without_declaration_never_falls_back_to_task_substring(tmp_path, exists):
    module = load_guard_module()
    path = tmp_path / "2030-01-01-001-ga-task99.3-work.md"
    if exists:
        path.write_text("SESSION COMPLETE\n")
    assert module._session_task_id(path) is None


def test_current_bead_without_declaration_cannot_activate_legacy_exception(tmp_path, monkeypatch):
    module = guard(tmp_path, monkeypatch)
    current = tmp_path / "sessions/2030-01-04-001-ga-task99.3-work.md"
    current.write_text("Current session without identity declaration\n")
    old = tmp_path / "sessions/2030-01-01-001-ga-task99.3-work.md"
    old.write_text("SESSION COMPLETE\n")
    monkeypatch.setattr(module, "CURRENT_SESSION_PATH", current)
    assert module.validate_session_edit_dates([old])


@pytest.mark.parametrize("legacy", ["task99", "task-99", "task_99"])
def test_historical_numeric_scaffold_remains_filename_based(tmp_path, legacy):
    module = load_guard_module()
    path = tmp_path / f"2030-01-01-001-{legacy}-old.md"
    path.write_bytes(b"Historical Latin-1: \xe9\n")
    assert module._session_task_id(path) == "99"


def test_bead_scaffold_accepts_crlf_without_rewriting_it(tmp_path):
    module = load_guard_module()
    path = tmp_path / "2030-01-01-001-ga-example.2-work.md"
    before = b"**Bead**: `ga-example.2`\r\nSESSION COMPLETE\r\n"
    path.write_bytes(before)
    assert module._session_task_id(path) == "bead:ga-example.2"
    assert path.read_bytes() == before
