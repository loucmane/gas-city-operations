"""Real target-local daily continuation; no live Beads, services or providers."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess

import pytest

from aegis_foundation.gate.session_transition import session_lock
from aegis_foundation.gate.session_authority import SessionAuthorityError
from tests.meta_workflow_guard.test_codex_task import load_task_module


class StartDay(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2030, 1, 1, 12, 0).astimezone(tz)


class NextDay(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2030, 1, 2, 12, 0).astimezone(tz)


def snapshot(root):
    return {
        p.relative_to(root).as_posix():
        ("link", str(p.readlink())) if p.is_symlink() else
        ("file", p.read_bytes(), p.stat().st_mode & 0o777)
        for p in root.rglob("*")
        if ".git" not in p.relative_to(root).parts and (p.is_symlink() or p.is_file())
    }


def args(target, **changes):
    return argparse.Namespace(**{
        "task": None, "bead": "ga-test1", "slug": "portable",
        "title": "Portable continuation", "work": "ga-test1-portable",
        "folder": None, "plan": None, "task_source": "Synthetic Bead",
        "dry_run": False, "target_dir": str(target), **changes,
    })


@pytest.fixture
def projects(tmp_path, monkeypatch, request):
    module = load_task_module()
    monkeypatch.setattr(module, "datetime", StartDay)
    roots = [tmp_path / "shared-source", tmp_path / "consumer"]
    for root in roots:
        root.mkdir()
        subprocess.run(["git", "init", "-b", "codex/ga-test1-portable"],
                       cwd=root, check=True, capture_output=True)
        if root == roots[1] and getattr(request, "param", False):
            (root / ".codex").mkdir()
            (root / ".codex/config.toml").write_text(
                '[repo_structure]\n'
                'sessions_root = "engdocs/workflow/sessions"\n'
                'plans_root = "engdocs/workflow/plans"\n'
                'plan_state_dir = "engdocs/workflow/plan-state"\n'
                'work_tracking_root = "engdocs/workflow/work-tracking"\n'
            )
        module.handle_wizard_kickoff(argparse.Namespace(
            task=None, bead="ga-test1", slug="portable", title=root.name,
            goal=["Preserve the task across days"], task_source="Synthetic Bead",
            handler_target=".", target_dir=str(root), force=False, dry_run=False,
        ))
        # Keep locking overhead out of no-mutation assertions. All actual
        # continuation and target-validation code still runs, without stubs.
        with session_lock(root):
            pass
    module._configure_workflow_target(str(roots[0]))
    monkeypatch.setattr(module, "datetime", NextDay)
    return module, roots[0], roots[1]


def test_parser_exposes_explicit_optional_continuation_target():
    parser = load_task_module().build_parser()
    parsed = parser.parse_args([
        "sessions", "continue", "--bead", "ga-test1", "--target-dir", "/tmp/consumer",
    ])
    assert parsed.target_dir == "/tmp/consumer"
    assert parser.parse_args(["sessions", "continue", "--bead", "ga-test1"]).target_dir is None


@pytest.mark.parametrize("projects", [False, True], indirect=True)
def test_continuation_changes_only_selected_git_root(projects):
    module, source, target = projects
    untouched = snapshot(source)
    layout = target / "engdocs/workflow" if (target / ".codex/config.toml").exists() else target
    old_session = (layout / "sessions/current").resolve()
    old_bytes = old_session.read_bytes()
    plan = (layout / "plans/current").resolve()
    plan_bytes = plan.read_bytes()
    module.handle_sessions_continue(args(target))
    current = (layout / "sessions/current").resolve()
    assert current.name == "2030-01-02-001-ga-test1-portable.md"
    assert current.is_relative_to(layout / "sessions")
    assert json.loads((layout / "sessions/state.json").read_text())["current"] == current.name
    assert old_session.read_bytes() == old_bytes
    assert (layout / "plans/current").resolve() == plan and plan.read_bytes() == plan_bytes
    assert snapshot(source) == untouched
    assert not (target / ".taskmaster").exists()
    wal = json.loads((target / ".aegis/state/session-continuation.json").read_text())
    assert wal["status"] == "complete"
    sync = layout / "plan-state/sync.log" if layout != target else target / ".plan_state/sync.log"
    assert sync.is_file()


@pytest.mark.parametrize("kind", ["missing", "not-git", "subdirectory"])
def test_invalid_target_refuses_before_writes(projects, tmp_path, kind):
    module, source, target = projects
    bad = tmp_path / "missing"
    if kind == "not-git":
        bad = tmp_path / "plain"
        bad.mkdir()
    elif kind == "subdirectory":
        bad = target / "sessions"
    before = snapshot(source), snapshot(target)
    with pytest.raises(module.TaskError, match="Workflow target"):
        module.handle_sessions_continue(args(bad))
    assert (snapshot(source), snapshot(target)) == before


def test_numeric_task_cannot_cross_project_boundary(projects, monkeypatch):
    module, source, target = projects
    before = snapshot(source), snapshot(target)
    monkeypatch.setattr(module, "_load_task_metadata",
                        lambda *a: pytest.fail("must refuse before reading Taskmaster"))
    with pytest.raises(module.TaskError, match="requires --bead"):
        module.handle_sessions_continue(args(target, bead=None, task="42"))
    assert (snapshot(source), snapshot(target)) == before


def test_target_branch_mismatch_refuses_before_writes(projects):
    module, source, target = projects
    subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"],
                   cwd=target, check=True, capture_output=True)
    before = snapshot(source), snapshot(target)
    with pytest.raises(module.TaskError, match="branch"):
        module.handle_sessions_continue(args(target))
    assert (snapshot(source), snapshot(target)) == before


def test_target_lock_is_not_bypassed(projects):
    module, source, target = projects
    before = snapshot(source), snapshot(target)
    with session_lock(target):
        with pytest.raises(SessionAuthorityError, match="in use"):
            module.handle_sessions_continue(args(target))
    assert (snapshot(source), snapshot(target)) == before
