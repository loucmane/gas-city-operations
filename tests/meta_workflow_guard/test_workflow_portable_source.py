"""Real uninstalled consumer boundary; only the Beads transport is substituted."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.meta_workflow_guard.test_gas_city_workflow_transitions import (
    FixtureRunner, _bead, _run,
)
from workflow import _checkpoint, _finish, _verify
from workflow_begin import begin, resume
from workflow_common import CommandRunner, WorkflowError, run_readiness, journal_path_for_root
from workflow_coordinate import log


class PortableRunner(FixtureRunner):
    """Use real Git, wizard, readiness, synchronization and evidence commands."""

    def run(self, argv, *, cwd=None, env=None, check=True):
        if str(argv[0]).endswith("/gc") and "bd" in argv:
            return super().run(argv, cwd=cwd, env=env, check=check)
        self.calls.append(list(argv))
        return CommandRunner.run(self, argv, cwd=cwd, env=env, check=check)


def portable_project(tmp_path):
    root = tmp_path / "consumer"
    root.mkdir()
    (root / "AGENTS.md").write_text("# Consumer\nBeads is authoritative.\n")
    (root / ".gas-city-workflow.json").write_text(json.dumps({
        "schema": "gas-city-workflow.project.v1",
        "id": "consumer",
        "repository": "fixture/consumer",
        "rig": "consumer",
        "workflow_authority": "beads",
        "workflow_profile": "beads-with-aegis-evidence",
    }))
    _run(root, "git", "init", "-b", "main")
    _run(root, "git", "add", ".")
    _run(root, "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
         "-c", "commit.gpgsign=false", "commit", "-m", "portable consumer")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"schema": "gas-city-workflow.project-registry.v1", "projects": []}))
    return root, registry


def start(tmp_path):
    canonical, registry = portable_project(tmp_path)
    runner = PortableRunner(_bead())
    result = begin(canonical, "ga-test", slug="portable", goals=["Prove portable source work"],
                   registry=registry, runner=runner)
    return Path(result["spec"]["worktree"]), registry, runner, result


def test_portable_begin_resume_verify_and_log_use_real_bead_scaffold(tmp_path):
    root, registry, runner, started = start(tmp_path)
    assert started["status"] == "ready"
    assert not (root / "scripts/codex-task").exists()
    assert not (root / ".aegis/foundation-manifest.json").exists()
    before = _run(root, "git", "status", "--porcelain=v1").stdout
    resumed = resume(root, "ga-test", slug=None, goals=[], registry=registry, runner=runner)
    assert resumed["status"] == "ready"
    assert _run(root, "git", "status", "--porcelain=v1").stdout == before
    assert _checkpoint(root, runner)["status"] == "ready"
    verified = _verify(root, runner)
    assert verified["status"] == "passed"
    assert "plan-sync" in verified["checks"]
    assert "portable-bead-scaffold" in verified["checks"]
    assert "aegis-strict" not in verified["checks"]
    assert log(root, "AGENTS.md", "Portable evidence proof", runner)["status"] == "applied"
    assert "Portable evidence proof" in (root / "sessions/current").read_text()
    active = next((root / "docs/ai/work-tracking/active").glob("*-ACTIVE"))
    assert "Portable evidence proof" in (active / "IMPLEMENTATION.md").read_text()
    assert _verify(root, runner)["status"] == "passed"
    after_log = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and not p.is_symlink()}
    assert log(root, "AGENTS.md", "Portable evidence proof", runner)["idempotent"]
    assert all(path.read_bytes() == content for path, content in after_log.items())
    assert _finish(root, runner, apply=False)["backend"] == "portable-source-archive"
    assert active.exists()
    assert all("--claim" not in call for call in runner.calls)


@pytest.mark.parametrize("fault", ["branch", "session", "plan", "tracker", "owner", "native", "pending"])
def test_portable_readiness_refuses_identity_and_authority_drift(tmp_path, fault):
    root, _, runner, _ = start(tmp_path)
    if fault == "branch":
        _run(root, "git", "branch", "-m", "codex/ga-other-portable")
    elif fault == "session":
        state = root / "sessions/state.json"
        payload = json.loads(state.read_text())
        payload["current"] = "unrelated-session.md"
        state.write_text(json.dumps(payload))
    elif fault == "plan":
        plan = root / "plans/current"
        plan.write_text(plan.read_text().replace("bead_ids: [ga-test]", "bead_ids: [ga-other]"))
    elif fault == "tracker":
        active = next((root / "docs/ai/work-tracking/active").glob("*-ACTIVE"))
        tracker = active / "TRACKER.md"
        tracker.write_text(tracker.read_text().replace("**Status**: ACTIVE", "**Status**: COMPLETED"))
    elif fault == "owner":
        runner.bead["metadata"]["workflow.external_owner"] = "wrong"
    elif fault == "native":
        runner.bead["assignee"] = "ci-unexpected"
    else:
        # An installed-runtime marker must never silently select portable mode.
        state = root / ".aegis/state/current-work.json"
        state.parent.mkdir(parents=True)
        state.write_text("{invalid")
    before = _run(root, "git", "status", "--porcelain=v1").stdout
    with pytest.raises(WorkflowError):
        run_readiness(runner, root)
    assert _run(root, "git", "status", "--porcelain=v1").stdout == before


def test_core_registry_binds_reviewed_base_and_established_worktree_root():
    source = Path(__file__).resolve().parents[2]
    projects = json.loads((source / "plugins/gas-city-workflow/config/projects.json").read_text())["projects"]
    core = next(item for item in projects if item["id"] == "gas-city")
    assert core["base_ref"] == "refs/remotes/origin/main"
    assert core["worktree_root"] == "/home/loucmane/gascity-core-worktrees"
    assert core["workflow_profile"] == "beads-with-aegis-evidence"


def test_portable_resume_recovers_claimed_partial_without_new_worktree_or_owner(tmp_path):
    root, registry, runner, _ = start(tmp_path)
    path = journal_path_for_root(runner, root, "ga-test")
    payload = json.loads(path.read_text())
    payload["phase"] = "claimed"
    path.write_text(json.dumps(payload))
    calls = len(runner.calls)
    owner = dict(runner.bead["metadata"])
    result = resume(root, "ga-test", slug=None, goals=[], registry=registry, runner=runner)
    assert result["status"] == "ready"
    assert runner.bead["metadata"] == owner
    assert not any("update" in call or "add" in call for call in runner.calls[calls:])


def test_portable_logging_rolls_back_exactly_on_second_write_failure(tmp_path, monkeypatch):
    from aegis_foundation.gate.session_transition import SessionTransition

    root, _, runner, _ = start(tmp_path)
    before = {p: (p.read_bytes(), p.stat().st_mode) for p in root.rglob("*.md") if not p.is_symlink()}
    real_write = SessionTransition.write
    count = 0

    def fail_second(self, path, data):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("injected second write failure")
        real_write(self, path, data)

    monkeypatch.setattr(SessionTransition, "write", fail_second)
    with pytest.raises(OSError, match="injected"):
        log(root, "AGENTS.md", "Rollback proof", runner)
    assert all((p.read_bytes(), p.stat().st_mode) == value for p, value in before.items())
    assert json.loads((root / ".aegis/state/session-continuation.json").read_text())["status"] == "rolled_back"
    assert "STATE: READY" in run_readiness(runner, root)


@pytest.mark.parametrize("fault", ["escape", "link", "missing", "old-session", "pending-id", "partial-replay"])
def test_portable_log_refuses_before_writing(tmp_path, fault):
    root, _, runner, _ = start(tmp_path)
    evidence, pending_id = "AGENTS.md", None
    if fault == "escape":
        evidence = "../outside.md"
    elif fault == "link":
        (root / "linked.md").symlink_to(root / "AGENTS.md")
        evidence = "linked.md"
    elif fault == "missing":
        evidence = "missing.md"
    elif fault == "old-session":
        import re
        session = (root / "sessions/current").resolve()
        session.write_text(re.sub(r"^date: .*", "date: 2000-01-01", session.read_text(), flags=re.MULTILINE))
    elif fault == "pending-id":
        evidence, pending_id = None, "123456789abc"
    else:
        log(root, evidence, "Proof", runner)
        session = (root / "sessions/current").resolve()
        session.write_text(session.read_text().replace("portable-work-log:", "preserved-partial:"))
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and not p.is_symlink()}
    with pytest.raises((WorkflowError, ValueError)):
        log(root, evidence, "Proof", runner, pending_id=pending_id)
    assert all(p.read_bytes() == value for p, value in before.items())


def test_shared_runtime_loads_from_source_with_no_cwd_or_pythonpath_help(tmp_path):
    source = Path(__file__).resolve().parents[2]
    scripts = source / "plugins/gas-city-workflow/scripts"
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from workflow_portable import load_shared_runtime; load_shared_runtime(); "
        "import aegis_foundation; print(aegis_foundation.__file__)"
    )
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(scripts)],
                            cwd=tmp_path, env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).is_relative_to(source)


@pytest.mark.parametrize("marker", [
    ".aegis/foundation-manifest.json", ".aegis/state/current-work.json",
    ".aegis/state/pending-tracking.json", ".claude/scripts/readiness.sh", "scripts/codex-task",
])
def test_present_adapter_markers_keep_original_readiness_dispatch(tmp_path, marker):
    # Dispatch-selection proof only; this intentionally does not attest adapter READY.
    from workflow_common import readiness_command

    path = tmp_path / marker
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("preserved existing adapter")

    class RecordingRunner(CommandRunner):
        def run(self, argv, **kwargs):
            self.argv = argv
            return subprocess.CompletedProcess(argv, 0, "STATE: READY\n", "")

    runner = RecordingRunner()
    expected, _, _ = readiness_command(tmp_path)
    run_readiness(runner, tmp_path)
    assert runner.argv == expected
