"""Immutable-base inspection must precede workflow or Git mutations."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.meta_workflow_guard.test_gas_city_workflow_transitions import FixtureRunner, _bead, _run
from tests.meta_workflow_guard.test_workflow_portable_source import portable_project
from workflow_begin import begin
from workflow_common import WorkflowError
from _repo_structure import load_repo_structure
from workflow_preflight import inherited_contexts


def commit_fixture(root):
    _run(root, "git", "add", ".")
    _run(root, "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
         "-c", "commit.gpgsign=false", "commit", "-m", "inherited context")


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("tracking", ["docs/ai/work-tracking", "engdocs/workflow/work-tracking"])
def test_inherited_context_refuses_before_worktree_branch_or_journal(tmp_path, dry_run, tracking):
    root, registry = portable_project(tmp_path, layout={"work_tracking_root": tracking})
    inherited = root / tracking / "active" / "20300101-ga-parent-incomplete-ACTIVE" / "TRACKER.md"
    inherited.parent.mkdir(parents=True)
    inherited.write_text("# Unfinished ga-parent\n- [ ] Acceptance pending\n")
    commit_fixture(root)
    runner = FixtureRunner(_bead())
    before = _run(root, "git", "show-ref").stdout
    with pytest.raises(WorkflowError):
        begin(root, "ga-test", slug="fresh", goals=[], registry=registry, runner=runner, dry_run=dry_run)
    assert _run(root, "git", "show-ref").stdout == before
    assert not (root.parent / "consumer-worktrees").exists()
    assert not (root / ".git/gas-city-workflow/transactions/ga-test.json").exists()
    assert not any("update" in call or "--claim" in call for call in runner.calls)
    assert inherited.read_text() == "# Unfinished ga-parent\n- [ ] Acceptance pending\n"


def test_preflight_uses_selected_base_not_parked_canonical_layout(tmp_path):
    root, registry = portable_project(tmp_path)
    (root / ".codex").mkdir()
    (root / ".codex/config.toml").write_text('[repo_structure]\nwork_tracking_root = "engdocs/workflow/work-tracking"\n')
    inherited = root / "engdocs/workflow/work-tracking/active/20300101-ga-parent-incomplete-ACTIVE/TRACKER.md"
    inherited.parent.mkdir(parents=True)
    inherited.write_text("# Pending\n")
    commit_fixture(root)
    base = _run(root, "git", "rev-parse", "HEAD").stdout.strip()
    _run(root, "git", "update-ref", "refs/remotes/origin/main", base)
    _run(root, "git", "checkout", "HEAD~1")
    assert not (root / ".codex/config.toml").exists()
    payload = json.loads((root / ".gas-city-workflow.json").read_text())
    payload["base_ref"] = "refs/remotes/origin/main"
    (root / ".gas-city-workflow.json").write_text(json.dumps(payload))
    runner = FixtureRunner(_bead())
    with pytest.raises(WorkflowError):
        begin(root, "ga-test", slug="fresh", goals=[], registry=registry, runner=runner)
    assert not (root.parent / "consumer-worktrees").exists()
    assert not (root / ".git/gas-city-workflow/transactions/ga-test.json").exists()


@pytest.mark.parametrize("config", ["malformed", "symlink", "unknown-root", "escape", "active-symlink"])
def test_invalid_selected_base_refuses_before_mutation(tmp_path, config):
    root, registry = portable_project(tmp_path)
    (root / ".codex").mkdir()
    target = root / ".codex/config.toml"
    if config == "symlink":
        target.symlink_to("missing")
    elif config == "malformed":
        target.write_text("[invalid\n")
    elif config == "unknown-root":
        target.write_text('[repo_structure]\nunknown = "missing"\n')
    elif config == "escape":
        target.write_text('[repo_structure]\nwork_tracking_root = "../outside"\n')
    else:
        target.write_text('[repo_structure]\nwork_tracking_root = "tracking"\n')
        (root / "tracking").mkdir()
        (root / "tracking/active").symlink_to("../missing")
    commit_fixture(root)
    base = _run(root, "git", "rev-parse", "HEAD").stdout.strip()
    _run(root, "git", "update-ref", "refs/remotes/origin/main", base)
    _run(root, "git", "checkout", "HEAD~1")
    descriptor = root / ".gas-city-workflow.json"
    payload = json.loads(descriptor.read_text())
    payload["base_ref"] = "refs/remotes/origin/main"
    descriptor.write_text(json.dumps(payload))
    refs = _run(root, "git", "show-ref").stdout
    with pytest.raises(WorkflowError):
        begin(root, "ga-test", slug="fresh", goals=[], registry=registry, runner=FixtureRunner(_bead()))
    assert _run(root, "git", "show-ref").stdout == refs
    assert not (root.parent / "consumer-worktrees").exists()
    assert not (root / ".git/gas-city-workflow/transactions/ga-test.json").exists()


@pytest.mark.parametrize("layout", [{}, {"work_tracking_root": "engdocs/workflow/work-tracking"},
                                  {"work_tracking_root": "workflow/tracking", "plans_root": "workflow/plans",
                                   "sessions_root": "workflow/sessions", "plan_state_dir": "workflow/state"}])
def test_selected_tree_and_shared_layout_resolver_agree(tmp_path, layout):
    root, _ = portable_project(tmp_path, layout=layout)
    active = load_repo_structure(root).work_tracking_active_root
    tracker = active / "20300101-ga-parent-work-ACTIVE/TRACKER.md"
    tracker.parent.mkdir(parents=True)
    tracker.write_text("Unfinished parent\n")
    commit_fixture(root)
    spec = SimpleNamespace(canonical_root=str(root), base_commit=_run(root, "git", "rev-parse", "HEAD").stdout.strip())
    assert inherited_contexts(FixtureRunner(_bead()), spec) == [tracker.parent.name]


@pytest.mark.parametrize("configuration", ['[repo_structure]\nunknown = "path"\n',
    '[repo_structure]\nwork_tracking_root = 42\n', '[repo_structure]\nwork_tracking_root = ""\n',
    '[repo_structure]\nwork_tracking_root = "../escape"\n', '[repo_structure]\nplans_root = "bad//root"\n',
    '[repo_structure]\nsessions_root = "/absolute"\n', '[repo_structure]\nreports_root = "path/.git/dir"\n',
    'repo_structure = []\n', '[invalid\n'])
def test_selected_tree_and_shared_layout_both_refuse_invalid_configuration(tmp_path, configuration):
    root, _ = portable_project(tmp_path)
    (root / ".codex").mkdir()
    (root / ".codex/config.toml").write_text(configuration)
    commit_fixture(root)
    spec = SimpleNamespace(canonical_root=str(root), base_commit=_run(root, "git", "rev-parse", "HEAD").stdout.strip())
    with pytest.raises(ValueError):
        load_repo_structure(root)
    with pytest.raises(WorkflowError):
        inherited_contexts(FixtureRunner(_bead()), spec)
