"""Real layout/plan-sync/session-WAL composition in disposable repositories.

These prove the proposed leaf-transaction composition, not the not-yet-built
outer rename journal, crash recovery, production invocation or live migration.
Only Beads transport is simulated by the existing portable fixture.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys
import types

import pytest

from tests.meta_workflow_guard.test_workflow_portable_source import start
from aegis_foundation.gate.session_authority import (
    SessionAuthorityError, assert_no_pending_continuation,
)
from aegis_foundation.gate.session_transition import (
    JOURNAL, SessionTransition, image, session_lock,
)
from project_context import build_context
from workflow_lock import workflow_lock
from workflow_portable import run_portable_readiness


CONFIG = b'''[repo_structure]
sessions_root = "engdocs/workflow/sessions"
plans_root = "engdocs/workflow/plans"
plan_state_dir = "engdocs/workflow/plan-state"
work_tracking_root = "engdocs/workflow/work-tracking"
'''
PARENTS = ("engdocs/workflow", "engdocs/workflow/plans", ".codex")


def task_source():
    """Test-side source-only loader; no cache or alternative command writer."""
    source = Path(__file__).resolve().parents[2] / "scripts/codex-task"
    name = "layout_composition_task_fixture"
    module = types.ModuleType(name)
    module.__file__ = str(source)
    sys.modules[name] = module
    exec(compile(source.read_bytes(), str(source), "exec"), module.__dict__)
    return module


@pytest.fixture
def project(tmp_path):
    root, registry, runner, _ = start(tmp_path)
    assert root == root.resolve()
    (root / "engdocs").mkdir(mode=0o755)
    # Two real completed transactions give both a current WAL and an archive.
    seed = root / ".aegis/fixture-seed.txt"
    for content in (b"first\n", b"second\n"):
        with SessionTransition(root, "ga-test", [seed]) as transaction:
            transaction.write(seed, content)
    plan = (root / "plans/current").resolve()
    tracker = next((root / "docs/ai/work-tracking/active").glob("*/TRACKER.md"))
    moves = (
        ("docs/ai/work-tracking", "engdocs/workflow/work-tracking"),
        ("sessions", "engdocs/workflow/sessions"),
        (".plan_state", "engdocs/workflow/plan-state"),
        (str(plan.relative_to(root)), f"engdocs/workflow/plans/{plan.name}"),
        ("plans/current", "engdocs/workflow/plans/current"),
    )
    return root, registry, runner, plan, tracker, moves


def move_fixture(root, moves):
    """Test setup only: this is deliberately NOT the production outer WAL."""
    for parent in PARENTS:
        (root / parent).mkdir(mode=0o755)
    for source, destination in moves:
        (root / source).rename(root / destination)


def reverse_fixture(root, moves):
    for source, destination in reversed(moves):
        (root / destination).rename(root / source)
    for parent in reversed(PARENTS):
        (root / parent).rmdir()


def leaves(root, plan, tracker):
    return (
        root / ".codex/config.toml",
        root / "engdocs/workflow/plans" / plan.name,
        root / "engdocs/workflow/plan-state/sync.log",
        root / "engdocs/workflow/work-tracking" / tracker.relative_to(root / "docs/ai/work-tracking"),
    )


def rewritten_fixture_plan(original):
    """Change current-reference sections; preserve the historical amendment body."""
    before, marker, rest = original.partition("## Amendments & Versioning\n")
    history, following, continuation = rest.partition("## Continuation & Handoff\n")
    assert marker and following
    return (
        before.replace("docs/ai/work-tracking", "engdocs/workflow/work-tracking")
        + marker + history
        + "- Fixture-only layout relocation; original image retained by the test.\n\n"
        + following
        + continuation.replace("docs/ai/work-tracking", "engdocs/workflow/work-tracking")
        .replace("`sessions/current`", "`engdocs/workflow/sessions/current`")
    ).encode()


def synchronize(module, root, plan, tracker, transaction):
    module.handle_plan_sync(argparse.Namespace(
        target_dir=str(root), plan=str(plan.relative_to(root)),
        tracker=str(tracker.relative_to(root)), folder=None,
        dry_run=False, _session_transaction=transaction,
    ))


def test_real_sync_after_rename_has_three_owned_leaves_and_ready_poststate(project):
    root, registry, runner, old_plan, old_tracker, moves = project
    originals = {source: image(root / source) for source, _ in moves if (root / source).is_file()}
    session_before = (root / "sessions/current").read_bytes()
    tracker_before = old_tracker.read_bytes()
    plan_before = old_plan.read_text()
    prior_wal = image(root / JOURNAL)
    prior_record = json.loads((root / JOURNAL).read_text())
    archives = {p.name: image(p) for p in (root / ".aegis/state/session-continuations").glob("*.json")}
    old_entries = json.loads((root / ".plan_state/sync.log").read_text())
    assert (json.dumps(old_entries, indent=2) + "\n").encode() == (root / ".plan_state/sync.log").read_bytes()
    module = task_source()

    with workflow_lock(runner, root, registry), session_lock(root):
        move_fixture(root, moves)
        config, plan, sync, tracker = leaves(root, old_plan, old_tracker)
        transaction = SessionTransition(root, "ga-test", [config, plan, sync], lock_held=True)
        assert transaction.record["created_directories"] == []
        assert transaction.before[plan.relative_to(root).as_posix()]["kind"] == "file"
        assert transaction.before[sync.relative_to(root).as_posix()]["kind"] == "file"
        with transaction:
            transaction.write(config, CONFIG)
            transaction.write(plan, rewritten_fixture_plan(plan_before))
            synchronize(module, root, plan, tracker, transaction)
            with pytest.raises(SessionAuthorityError, match="pending"):
                assert_no_pending_continuation(root)
        assert_no_pending_continuation(root)
        assert "STATE: READY" in run_portable_readiness(runner, root)

        # The actual timestamped output, not a predicted hash, is the accepted image.
        accepted = next(s["after"] for s in transaction.record["steps"] if s["path"].endswith("sync.log"))
        assert image(sync) == accepted
        assert base64.b64decode(accepted["data"]) == sync.read_bytes()
        entries = json.loads(sync.read_text())
        assert entries[:-1] == old_entries
        assert entries[-1]["plan"] == plan.relative_to(root).as_posix()
        assert module.REPO_ROOT == root
        assert module.PLAN_SYNC_LOG == sync
        assert tracker.read_bytes() == tracker_before
        assert (root / "engdocs/workflow/sessions/current").read_bytes() == session_before
        context = build_context(root, registry)
        assert context["workflow"]["plan_current"] == plan.relative_to(root).as_posix()
        assert context["workflow"]["session_current"].startswith("engdocs/workflow/sessions/")
        for source, before in originals.items():
            if source != old_plan.relative_to(root).as_posix():
                destination = dict(moves)[source]
                assert image(root / destination) == before
        archive = root / ".aegis/state/session-continuations" / f'{prior_record["id"]}.json'
        assert image(archive) == prior_wal
        assert all(image(archive.parent / name) == before for name, before in archives.items())


@pytest.mark.parametrize("fault", ["config", "plan", "sync", "postcheck"])
def test_leaf_rollback_then_reverse_renames_restores_exact_scaffold(project, fault):
    root, registry, runner, old_plan, old_tracker, moves = project
    old_bytes = {p.relative_to(root): image(p) for base, _ in moves for p in
                 ([root / base] if (root / base).is_file() else (root / base).rglob("*"))
                 if p.is_file() or p.is_symlink()}
    plan_before = old_plan.read_text()
    module = task_source()
    with workflow_lock(runner, root, registry), session_lock(root):
        move_fixture(root, moves)
        config, plan, sync, tracker = leaves(root, old_plan, old_tracker)
        transaction = SessionTransition(root, "ga-test", [config, plan, sync], lock_held=True)
        assert transaction.record["created_directories"] == []
        with pytest.raises(RuntimeError, match="injected"):
            try:
                with transaction:
                    transaction.write(config, CONFIG)
                    if fault == "config":
                        raise RuntimeError("injected config failure")
                    transaction.write(plan, rewritten_fixture_plan(plan_before))
                    if fault == "plan":
                        raise RuntimeError("injected plan failure")
                    synchronize(module, root, plan, tracker, transaction)
                    if fault == "sync":
                        raise RuntimeError("injected sync failure")
                assert transaction.record["status"] == "complete"
                assert "STATE: READY" in run_portable_readiness(runner, root)
                raise RuntimeError("injected postcheck failure after commit")
            except RuntimeError:
                if transaction.record["status"] == "complete":
                    transaction.rollback()
                assert transaction.record["status"] == "rolled_back"
                assert not config.exists()
                assert (root / ".codex").is_dir()  # Outer parent owner still owns it.
                reverse_fixture(root, moves)
                raise
        assert all(image(root / relative) == before for relative, before in old_bytes.items())
        assert all(not (root / path).exists() for path in PARENTS)
        assert (root / "engdocs").is_dir()
        assert "STATE: READY" in run_portable_readiness(runner, root)
        assert json.loads((root / JOURNAL).read_text())["status"] == "rolled_back"


def test_postcommit_unknown_leaf_prevents_all_rollback_writes(project):
    root, registry, runner, old_plan, old_tracker, moves = project
    module = task_source()
    original = old_plan.read_text()
    with workflow_lock(runner, root, registry), session_lock(root):
        move_fixture(root, moves)
        config, plan, sync, tracker = leaves(root, old_plan, old_tracker)
        with SessionTransition(root, "ga-test", [config, plan, sync], lock_held=True) as transaction:
            transaction.write(config, CONFIG)
            transaction.write(plan, rewritten_fixture_plan(original))
            synchronize(module, root, plan, tracker, transaction)
        plan.write_bytes(b"unexplained fixture mutation\n")
        before = {p: image(p) for p in (config, plan, sync, root / JOURNAL)}
        with pytest.raises(SessionAuthorityError, match="ambiguous"):
            transaction.rollback()
        assert all(image(path) == value for path, value in before.items())
        assert (root / "engdocs/workflow/sessions").exists()
        assert not (root / "sessions").exists()  # No reverse rename after refusal.


def test_real_sync_invalid_tracker_rolls_back_without_rewriting_old_sync(project):
    root, registry, runner, old_plan, old_tracker, moves = project
    original = old_plan.read_text()
    module = task_source()
    with workflow_lock(runner, root, registry), session_lock(root):
        move_fixture(root, moves)
        config, plan, sync, tracker = leaves(root, old_plan, old_tracker)
        before = image(sync)
        tracker.write_text("# Invalid fixture tracker\n")
        with pytest.raises(module.TaskError, match="Tracker"):
            with SessionTransition(root, "ga-test", [config, plan, sync], lock_held=True) as transaction:
                transaction.write(config, CONFIG)
                transaction.write(plan, rewritten_fixture_plan(original))
                synchronize(module, root, plan, tracker, transaction)
        assert image(sync) == before
        assert not config.exists()
        assert plan.read_text() == original
        assert transaction.record["status"] == "rolled_back"


def test_real_sync_refuses_both_tracker_selectors_without_a_sync_write(project):
    """Preserve the R2 design defect as a refusal regression, not a waived check."""
    root, registry, runner, old_plan, old_tracker, moves = project
    module = task_source()
    original = old_plan.read_text()
    with workflow_lock(runner, root, registry), session_lock(root):
        move_fixture(root, moves)
        config, plan, sync, tracker = leaves(root, old_plan, old_tracker)
        before = image(sync)
        with pytest.raises(module.TaskError, match="either --tracker or --folder"):
            with SessionTransition(root, "ga-test", [config, plan, sync], lock_held=True) as transaction:
                transaction.write(config, CONFIG)
                transaction.write(plan, rewritten_fixture_plan(original))
                module.handle_plan_sync(argparse.Namespace(
                    target_dir=str(root), plan=str(plan.relative_to(root)),
                    tracker=str(tracker.relative_to(root)), folder=tracker.parent.name,
                    dry_run=False, _session_transaction=transaction,
                ))
        assert image(sync) == before
        assert all(not step["path"].endswith("sync.log") for step in transaction.record["steps"])
        assert not config.exists() and plan.read_text() == original
