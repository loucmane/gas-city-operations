from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
READINESS = REPO_ROOT / ".claude" / "scripts" / "readiness.sh"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(tmp_path: Path, *, task_id: int = 103, branch: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert run(["git", "init", "-q"], repo).returncode == 0
    branch = branch or f"feat/task-{task_id}-claude-runtime-adapter"
    assert run(["git", "checkout", "-q", "-b", branch], repo).returncode == 0

    write(
        repo / ".taskmaster" / "tasks" / "tasks.json",
        json.dumps(
            {
                "master": {
                    "tasks": [
                        {
                            "id": task_id,
                            "title": "Claude Runtime Adapter",
                            "status": "in-progress",
                            "subtasks": [],
                        }
                    ]
                }
            }
        ),
    )
    write(repo / ".taskmaster" / "state.json", json.dumps({"currentTag": "master"}))

    session_rel = Path("2026/05/2026-05-06-002-task103-claude-runtime-adapter.md")
    write(
        repo / "sessions" / session_rel,
        f"---\nsession_id: 2026-05-06-002\n---\n\n# Task {task_id} Session\n",
    )
    (repo / "sessions" / "current").symlink_to(session_rel)
    write(
        repo / "sessions" / "state.json",
        json.dumps({"current": session_rel.name, "paused": [], "updated_at": "2026-05-06T17:10:09+02:00"}),
    )

    plan_rel = Path(f"2026-05-06-task{task_id}-claude-runtime-adapter.md")
    write(
        repo / "plans" / plan_rel,
        f"""---
task_ids: [{task_id}]
---

# Plan - Task {task_id}

| Step ID | Description | Evidence | Status |
| --- | --- | --- | --- |
| plan-step-scope | Scope | evidence | completed |
| plan-step-implement | Implement | evidence | pending |
| plan-step-verify | Verify | evidence | pending |
| plan-step-emergency | Emergency | evidence | n/a |
""",
    )
    (repo / "plans" / "current").symlink_to(plan_rel)

    active = repo / "docs" / "ai" / "work-tracking" / "active" / f"20260506-task{task_id}-claude-runtime-adapter-ACTIVE"
    write(
        active / "TRACKER.md",
        f"""# Task {task_id} Claude Runtime Adapter Tracker

## Plan Compliance Checklist
- [x] plan-step-scope - Scope
- [ ] plan-step-implement - Implement
- [ ] plan-step-verify - Verify
- [ ] plan-step-emergency (if applicable)
""",
    )
    return repo


def make_bead_source_repo(
    tmp_path: Path,
    *,
    bead_id: str = "ga-k9sd",
    branch: str | None = None,
) -> Path:
    repo = make_repo(
        tmp_path,
        branch=branch or f"codex/{bead_id}-beads-first-guidance",
    )
    shutil.rmtree(repo / ".taskmaster")

    # Readiness intentionally recognizes bead identity only in an uninstalled
    # Aegis source checkout, never in an arbitrary target repository.
    write(repo / "pyproject.toml", '[project]\nname = "aegis-foundation"\n')
    source_markers = (
        "schemas/aegis/foundation-manifest.schema.json",
        "scripts/_aegis_installer.py",
        ".claude/scripts/readiness.sh",
        "aegis_foundation/assets/.claude/scripts/readiness.sh",
        "aegis_foundation/assets/scripts/codex-guard",
    )
    for marker in source_markers:
        write(repo / marker, "source marker\n")
    shutil.copy2(REPO_ROOT / "scripts/_source_workflow_state.py", repo / "scripts/_source_workflow_state.py")

    session_rel = Path(f"2026/08/2026-08-26-001-{bead_id}-beads-first-guidance.md")
    old_session = (repo / "sessions" / "current").resolve()
    (repo / "sessions" / "current").unlink()
    old_session.unlink()
    write(
        repo / "sessions" / session_rel,
        f"---\nsession_id: 2026-08-26-001\n---\n\n# Bead {bead_id} Session\n",
    )
    (repo / "sessions" / "current").symlink_to(session_rel)
    write(
        repo / "sessions" / "state.json",
        json.dumps({"current": session_rel.name, "paused": [], "updated_at": "2026-08-26T16:00:00+02:00"}),
    )

    plan_rel = Path(f"2026-08-26-{bead_id}-beads-first-guidance.md")
    old_plan = (repo / "plans" / "current").resolve()
    (repo / "plans" / "current").unlink()
    old_plan.unlink()
    active = repo / "docs" / "ai" / "work-tracking" / "active"
    shutil.rmtree(active)
    tracker = active / f"20260826-{bead_id}-beads-first-guidance-ACTIVE" / "TRACKER.md"
    write(
        repo / "plans" / plan_rel,
        f"""---
bead_ids: [{bead_id}]
branch_policy: {branch or f'codex/{bead_id}-beads-first-guidance'}
---

# Plan - Bead {bead_id}

- **Bead IDs**: {bead_id}
- **Branch Policy**: {branch or f'codex/{bead_id}-beads-first-guidance'}

| Step ID | Description | Evidence | Status |
| --- | --- | --- | --- |
| plan-step-scope | Scope | evidence | completed |
| plan-step-implement | Implement | evidence | pending |
| plan-step-verify | Verify | evidence | pending |
| plan-step-emergency | Emergency | evidence | n/a |
""",
    )
    (repo / "plans" / "current").symlink_to(plan_rel)
    write(
        tracker,
        f"""# Bead {bead_id} Tracker

**Status**: ACTIVE

## Plan Compliance Checklist
- [x] plan-step-scope - Scope
- [ ] plan-step-implement - Implement
- [ ] plan-step-verify - Verify
- [ ] plan-step-emergency (if applicable)
""",
    )
    return repo


def readiness(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["bash", str(READINESS), "--root", str(repo), *args], repo)


def write_aegis_current_work(repo: Path, *, task_id: int = 103, taskmaster_required: bool = False) -> None:
    write(
        repo / ".aegis" / "state" / "current-work.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "status": "in-progress",
                "paths": {
                    name: (repo / f"{name}s/current").resolve().relative_to(repo).as_posix()
                    for name in ("session", "plan")
                },
                "task": {
                    "id": str(task_id),
                    "slug": "claude-runtime-adapter",
                    "title": "Claude Runtime Adapter",
                    "status": "in-progress",
                },
                "integrations": {
                    "taskmaster": {
                        "required": taskmaster_required,
                        "detected": True,
                    },
                    "serena": {
                        "required": False,
                        "detected": False,
                    },
                },
            }
        ),
    )


def test_ready_when_task_session_plan_and_tracker_align(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)

    result = readiness(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "STATE: READY" in result.stdout
    assert "Taskmaster Task 103 is in-progress" in result.stdout
    assert "plan-step statuses align" in result.stdout


def test_ready_when_bead_source_branch_session_plan_and_tracker_align(tmp_path: Path) -> None:
    repo = make_bead_source_repo(tmp_path)

    result = readiness(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "STATE: READY" in result.stdout
    assert "TASK: ga-k9sd" in result.stdout
    assert "bead-native source work ga-k9sd" in result.stdout
    assert "plan-step statuses align" in result.stdout


def test_ready_when_hierarchical_bead_source_surfaces_align(tmp_path: Path) -> None:
    repo = make_bead_source_repo(tmp_path, bead_id="ga-ur1c.1")

    result = readiness(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "STATE: READY" in result.stdout
    assert "TASK: ga-ur1c.1" in result.stdout
    assert "bead-native source work ga-ur1c.1" in result.stdout
    assert "plan-step statuses align" in result.stdout


def test_bead_source_readiness_blocks_when_plan_declares_another_bead(tmp_path: Path) -> None:
    repo = make_bead_source_repo(tmp_path)
    plan = (repo / "plans" / "current").resolve()
    plan.write_text(plan.read_text(encoding="utf-8").replace("ga-k9sd", "ga-other"), encoding="utf-8")

    result = readiness(repo)

    assert result.returncode == 2
    assert "current plan does not declare bead ga-k9sd" in result.stdout


def test_bead_source_readiness_blocks_when_branch_policy_differs(tmp_path: Path) -> None:
    repo = make_bead_source_repo(tmp_path)
    plan = (repo / "plans" / "current").resolve()
    plan.write_text(
        plan.read_text(encoding="utf-8").replace(
            "codex/ga-k9sd-beads-first-guidance",
            "codex/ga-k9sd-other-policy",
        ),
        encoding="utf-8",
    )

    result = readiness(repo)

    assert result.returncode == 2
    assert "expected exactly codex/ga-k9sd-beads-first-guidance" in result.stdout


def test_bead_branch_does_not_bypass_readiness_in_arbitrary_repository(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="codex/ga-k9sd-beads-first-guidance")

    result = readiness(repo)

    assert result.returncode == 2
    assert "does not contain a task ID" in result.stdout


def test_readiness_default_verbose_and_all_detail_modes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)

    default = readiness(repo)
    verbose = readiness(repo, "--verbose")
    complete = readiness(repo, "--all")

    assert default.returncode == verbose.returncode == complete.returncode == 0
    assert len(default.stdout.splitlines()) <= 60
    assert len(default.stdout.encode("utf-8")) <= 8 * 1024
    assert len(verbose.stdout.splitlines()) <= 120
    assert len(verbose.stdout.encode("utf-8")) <= 32 * 1024
    assert "Counts: total=" in default.stdout
    assert "Full stdout: rerun readiness.sh with --all." in default.stdout
    assert "Truncated:" not in complete.stdout
    assert complete.stdout.count("[ok]") > default.stdout.count("[ok]")


def test_ready_inside_linked_git_worktree(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert run(["git", "config", "user.email", "test@example.com"], repo).returncode == 0
    assert run(["git", "config", "user.name", "Test User"], repo).returncode == 0
    assert run(["git", "config", "commit.gpgsign", "false"], repo).returncode == 0
    assert run(["git", "add", "."], repo).returncode == 0
    assert run(["git", "commit", "-q", "-m", "init"], repo).returncode == 0
    worktree = tmp_path / "linked-worktree"
    assert run(["git", "worktree", "add", "-q", "-b", "feat/task-103-linked-worktree", str(worktree)], repo).returncode == 0

    result = readiness(worktree)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "STATE: READY" in result.stdout
    assert (worktree / ".git").is_file()


def test_quick_mode_keeps_blocking_exit_code_and_concise_output(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "sessions" / "current").unlink()

    result = readiness(repo, "--quick")

    assert result.returncode == 2
    assert result.stdout.startswith("BLOCKED | task=103")
    assert "sessions/current symlink missing" in result.stdout
    assert "## Checks" not in result.stdout


def test_blocks_when_branch_has_no_task_id(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="feature/claude-runtime-adapter")

    result = readiness(repo)

    assert result.returncode == 2
    assert "does not contain a task ID" in result.stdout


def test_blocks_when_taskmaster_parent_not_in_progress(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    tasks_path = repo / ".taskmaster" / "tasks" / "tasks.json"
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    data["master"]["tasks"][0]["status"] = "pending"
    tasks_path.write_text(json.dumps(data), encoding="utf-8")

    result = readiness(repo)

    assert result.returncode == 2
    assert "expected 'in-progress'" in result.stdout


def test_aegis_current_work_is_authoritative_when_taskmaster_is_optional(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_aegis_current_work(repo, taskmaster_required=False)
    tasks_path = repo / ".taskmaster" / "tasks" / "tasks.json"
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    data["master"]["tasks"][0]["status"] = "done"
    tasks_path.write_text(json.dumps(data), encoding="utf-8")

    result = readiness(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "STATE: READY" in result.stdout
    assert "Aegis current work Task 103 is in-progress" in result.stdout
    assert "Taskmaster Task 103 is optional with status 'done'" in result.stdout


def test_aegis_current_work_can_require_taskmaster_alignment(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_aegis_current_work(repo, taskmaster_required=True)
    tasks_path = repo / ".taskmaster" / "tasks" / "tasks.json"
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    data["master"]["tasks"][0]["status"] = "done"
    tasks_path.write_text(json.dumps(data), encoding="utf-8")

    result = readiness(repo)

    assert result.returncode == 2
    assert "Taskmaster Task 103 status is 'done', expected 'in-progress'" in result.stdout


def test_blocks_when_sessions_current_missing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "sessions" / "current").unlink()

    result = readiness(repo)

    assert result.returncode == 2
    assert "sessions/current symlink missing" in result.stdout


def test_blocks_when_session_state_mismatches_symlink(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write(
        repo / "sessions" / "state.json",
        json.dumps({"current": "wrong-session.md", "paused": [], "updated_at": "2026-05-06T17:10:09+02:00"}),
    )

    result = readiness(repo)

    assert result.returncode == 2
    assert "sessions/state.json current is 'wrong-session.md'" in result.stdout


def test_blocks_when_plans_current_missing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "plans" / "current").unlink()

    result = readiness(repo)

    assert result.returncode == 2
    assert "plans/current symlink missing" in result.stdout


def test_blocks_when_no_active_work_tracking_folder_exists(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    active_root = repo / "docs" / "ai" / "work-tracking" / "active"
    for child in active_root.iterdir():
        if child.is_dir():
            (child / "TRACKER.md").unlink()
            child.rmdir()

    result = readiness(repo)

    assert result.returncode == 2
    assert "expected exactly one ACTIVE work-tracking folder, found 0" in result.stdout


def test_blocks_when_active_folder_task_mismatches_branch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    active_root = repo / "docs" / "ai" / "work-tracking" / "active"
    active = next(active_root.iterdir())
    active.rename(active_root / "20260506-task104-claude-runtime-adapter-ACTIVE")

    result = readiness(repo)

    assert result.returncode == 2
    assert "does not match Task 103" in result.stdout


def test_blocks_when_plan_and_tracker_checklists_diverge(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    tracker = next((repo / "docs" / "ai" / "work-tracking" / "active").iterdir()) / "TRACKER.md"
    text = tracker.read_text(encoding="utf-8").replace("[x] plan-step-scope", "[ ] plan-step-scope")
    tracker.write_text(text, encoding="utf-8")

    result = readiness(repo)

    assert result.returncode == 2
    assert "plan-step-scope mismatch" in result.stdout
