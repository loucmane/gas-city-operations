from __future__ import annotations

import importlib.util
import inspect
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from aegis_foundation.gate.hooks import pretool as gate_pretool


REPO_ROOT = Path(__file__).resolve().parents[2]
PRETOOLUSE = REPO_ROOT / ".claude" / "scripts" / "pretooluse-gate.sh"
POSTTOOLUSE = REPO_ROOT / ".claude" / "scripts" / "posttooluse-tracking.sh"
PATH_GUARD = REPO_ROOT / ".claude" / "scripts" / "codex-path-guard.sh"
BASH_GUARD = REPO_ROOT / ".claude" / "scripts" / "bash-command-guard.sh"
HARD_POLICY_CORPUS = REPO_ROOT / "tests" / "fixtures" / "aegis" / "gate-hard-policy-corpus.json"


def run(
    cmd: list[str], cwd: Path, *, input_text: str = "", env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_gate_decisions(repo: Path) -> list[dict[str, object]]:
    path = repo / ".aegis" / "reports" / "gate-decisions.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def payload(tool_name: str, **tool_input: object) -> str:
    return json.dumps({"tool_name": tool_name, "tool_input": tool_input})


def load_gate_lib_module():
    module_name = "gate_lib_under_test"
    spec = importlib.util.spec_from_file_location(
        module_name, REPO_ROOT / ".claude" / "scripts" / "gate_lib.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path: Path, *, ready: bool) -> Path:
    repo = tmp_path / ("ready-repo" if ready else "blocked-repo")
    repo.mkdir()
    assert run(["git", "init", "-q"], repo).returncode == 0
    branch = "feat/task-103-claude-runtime-adapter" if ready else "feature/no-task"
    assert run(["git", "checkout", "-q", "-b", branch], repo).returncode == 0
    if not ready:
        return repo

    write(
        repo / ".taskmaster" / "tasks" / "tasks.json",
        json.dumps(
            {
                "master": {
                    "tasks": [
                        {"id": 103, "title": "Claude Runtime Adapter", "status": "in-progress"}
                    ]
                }
            }
        ),
    )
    session_rel = Path("2026/05/2026-05-06-002-task103-claude-runtime-adapter.md")
    write(repo / "sessions" / session_rel, "# Task 103 Session\n")
    (repo / "sessions" / "current").symlink_to(session_rel)
    write(
        repo / "sessions" / "state.json",
        json.dumps(
            {"current": session_rel.name, "paused": [], "updated_at": "2026-05-06T17:35:54+02:00"}
        ),
    )
    plan_rel = Path("2026-05-06-task103-claude-runtime-adapter.md")
    write(
        repo / "plans" / plan_rel,
        """---
task_ids: [103]
---

# Plan - Task 103

| Step ID | Description | Evidence | Status |
| --- | --- | --- | --- |
| plan-step-scope | Scope | evidence | completed |
| plan-step-implement | Implement | evidence | pending |
| plan-step-verify | Verify | evidence | pending |
""",
    )
    (repo / "plans" / "current").symlink_to(plan_rel)
    active = (
        repo
        / "docs"
        / "ai"
        / "work-tracking"
        / "active"
        / "20260506-task103-claude-runtime-adapter-ACTIVE"
    )
    write(
        active / "TRACKER.md",
        """# Task 103 Claude Runtime Adapter Tracker

## Plan Compliance Checklist
- [x] plan-step-scope - Scope
- [ ] plan-step-implement - Implement
- [ ] plan-step-verify - Verify
""",
    )
    return repo


def make_completed_closeout_repo(tmp_path: Path) -> Path:
    repo = make_repo(tmp_path, ready=True)
    write(
        repo / ".aegis" / "state" / "current-work.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "status": "completed",
                "closeout_passed_at": "2026-05-30T15:48:41Z",
                "task": {
                    "id": "103",
                    "slug": "claude-runtime-adapter",
                    "status": "completed",
                    "title": "Claude Runtime Adapter",
                },
                "paths": {},
            }
        ),
    )
    return repo


def gate_env(repo: Path) -> dict[str, str]:
    import os

    return {**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}


def run_gate(script: Path, repo: Path, hook_payload: str) -> subprocess.CompletedProcess[str]:
    return run(["bash", str(script)], repo, input_text=hook_payload, env=gate_env(repo))


def hard_policy_corpus() -> list[dict[str, object]]:
    document = json.loads(HARD_POLICY_CORPUS.read_text(encoding="utf-8"))
    assert document["schema_version"] == "1.0.0"
    cases = document["cases"]
    assert isinstance(cases, list)
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    return cases


@pytest.mark.parametrize("case", hard_policy_corpus(), ids=lambda case: str(case["id"]))
def test_hard_policy_adversarial_corpus(tmp_path: Path, case: dict[str, object]) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=case["command"]))

    expected = case["expected"]
    assert result.returncode == (2 if expected == "block" else 0), result.stderr
    if expected == "block":
        assert "Non-overridable violation" in result.stderr


@pytest.mark.parametrize("case", hard_policy_corpus(), ids=lambda case: str(case["id"]))
def test_raw_hard_policy_preclassifier_is_total_and_covers_sensitive_families(
    case: dict[str, object],
) -> None:
    gate_lib = load_gate_lib_module()

    actual = gate_lib.raw_hard_policy_families(case["command"])

    assert isinstance(actual, frozenset)
    assert set(case["families"]).issubset(actual)


def test_mutating_taskmaster_regex_recognizes_newline_command_boundary() -> None:
    gate_lib = load_gate_lib_module()

    assert gate_lib.MUTATING_TASKMASTER_RE.search(
        "true\ntask-master set-status --id=103 --status=done"
    )


def test_pretooluse_blocks_file_write_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Write", file_path="README.md"))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr
    assert "branch 'feature/no-task' does not contain a task ID" in result.stderr


def test_pretooluse_advisory_records_would_block_without_blocking(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)
    write(
        repo / ".aegis" / "state" / "enforcement.json",
        json.dumps(
            {
                "mode": "advisory",
                "set_at": "2026-06-10T10:00:00Z",
                "set_by": "test",
                "reason": "regression test",
            }
        ),
    )

    result = run_gate(PRETOOLUSE, repo, payload("Write", file_path="README.md"))

    assert result.returncode == 0
    assert "ADVISORY | pretooluse would have blocked" in result.stderr
    decisions = read_gate_decisions(repo)
    assert len(decisions) == 1
    assert decisions[0]["hook"] == "pretooluse"
    assert decisions[0]["tool_name"] == "Write"
    assert decisions[0]["verdict"] == "would_block"
    assert decisions[0]["reason"] == "readiness_blocked"
    assert decisions[0]["mode"] == "advisory"
    assert "branch 'feature/no-task' does not contain a task ID" in str(
        decisions[0]["readiness_state"]
    )


def test_pretooluse_allows_read_only_bash_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command="git status --short"))

    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD~1",
        "env AEGIS_TEST=1 git -C . reset --merge HEAD~1",
        "bash -lc 'git clean -fdx'",
        "echo ok && git push --force-with-lease origin feat/task-103-claude-runtime-adapter",
        "/usr/bin/git push -f origin feat/task-103-claude-runtime-adapter",
        "git push origin main",
        "git push origin HEAD:main",
        "git push origin :main",
        "git push --delete origin old-feature",
        "git remote set-url origin git@github.com:attacker/repo.git",
        "git config remote.origin.url git@github.com:attacker/repo.git",
        "git checkout -- README.md",
        "git restore README.md",
        "git switch --discard-changes main",
        "git branch -D abandoned-work",
        "gh api --method DELETE repos/example/project/branches/main/protection",
        "gh api repos/example/project/rulesets -f name=unsafe",
        "curl -X DELETE https://api.github.com/repos/example/project/branches/main/protection",
    ],
)
def test_pretooluse_hard_blocks_destructive_git_and_governance_commands(
    tmp_path: Path,
    command: str,
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 2
    assert "Non-overridable violation" in result.stderr
    assert "destructive Git or repository-governance safety" in result.stderr
    assert "NOT override-eligible" in result.stderr


def test_pretooluse_hard_blocks_implicit_push_from_protected_branch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)
    assert run(["git", "checkout", "-q", "-b", "main"], repo).returncode == 0

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command="git push"))

    assert result.returncode == 2
    assert "implicit push from protected branch 'main'" in result.stderr


def test_pretooluse_destructive_git_policy_remains_hard_in_advisory_mode(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)
    write(
        repo / ".aegis" / "state" / "enforcement.json",
        json.dumps(
            {
                "mode": "advisory",
                "set_at": "2026-07-12T18:00:00Z",
                "set_by": "test",
                "reason": "prove hard-policy independence",
            }
        ),
    )

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command="git reset --hard HEAD"))

    assert result.returncode == 2
    assert "ADVISORY" not in result.stderr
    decisions = read_gate_decisions(repo)
    assert decisions[-1]["verdict"] == "block"
    assert decisions[-1]["reason"] == "destructive_git_operation"
    assert decisions[-1]["mode"] == "advisory"


def test_pretooluse_hard_policy_classifier_failure_denies_in_advisory_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_repo(tmp_path, ready=True)
    write(
        repo / ".aegis" / "state" / "enforcement.json",
        json.dumps({"mode": "advisory", "set_by": "test", "reason": "fail-closed regression"}),
    )
    gate_lib = load_gate_lib_module()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))

    def fail_classifier(*_args: object, **_kwargs: object) -> list[str]:
        raise RuntimeError("simulated classifier failure")

    monkeypatch.setattr(gate_pretool, "hard_policy_violations", fail_classifier)

    result = gate_lib.pretooluse_gate(payload("Bash", command="git status --short"))

    assert result == 2
    assert "classifier failed closed" in capsys.readouterr().err
    decisions = read_gate_decisions(repo)
    assert decisions[-1]["verdict"] == "block"
    assert decisions[-1]["mode"] == "advisory"


@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "git add README.md",
        "git commit -S -m 'test commit'",
        "git push origin feat/task-103-claude-runtime-adapter",
        "git push -u origin HEAD",
        "git restore --staged README.md",
        "git clean -ndx",
        "git checkout feat/task-103-claude-runtime-adapter",
        "git switch feat/task-103-claude-runtime-adapter",
        "git config --get remote.origin.url",
        "gh api --method GET repos/example/project/branches/main/protection",
        "curl https://api.github.com/repos/example/project/rulesets",
        "echo 'git reset --hard is blocked by policy'",
    ],
)
def test_pretooluse_hard_policy_preserves_normal_delivery_and_inspection(
    tmp_path: Path,
    command: str,
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 0
    assert "Non-overridable violation" not in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "cat sessions/state.json",
        "sed -n '1,40p' README.md",
        "rg task",
        "git diff -- src/main.ts",
        "git branch --show-current",
        "task-master next",
        "task-master show 138",
        "./.aegis/bin/aegis reconcile --target-dir .",
        "npm run verify",
        "uv run python -m pytest tests/foo.py",
        "npm run verify 2>&1 | tail -15",
    ],
)
def test_pretooluse_allows_known_read_only_bash_before_readiness(
    tmp_path: Path, command: str
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize(
    "command",
    [
        "git fetch origin",
        "git fetch --prune origin",
        "git fetch -q --tags origin",
        "git -C /tmp/elsewhere fetch origin",
        "git ls-remote origin refs/heads/main",
        "git ls-remote --heads origin",
        "gh pr view 44 -R loucmane/gascity --json state,mergeable",
        "gh pr list --repo loucmane/gascity --state open --json number",
        "gh pr checks 44 -R loucmane/gascity --watch --interval 30",
        "gh pr diff 44 -R loucmane/gascity",
        "gh pr status",
        "gh run list -R loucmane/gascity --branch main --limit 3 --json conclusion",
        "gh run view 1 -R loucmane/gascity --log-failed",
        "gh run watch 1 -R loucmane/gascity",
        "gh auth status",
        "gh repo view loucmane/gascity --json defaultBranchRef",
        "gh pr checks 44 -R loucmane/gascity 2>&1 | grep -v pass",
    ],
)
def test_pretooluse_allows_remote_read_only_observation_before_readiness(
    tmp_path: Path, command: str
) -> None:
    """ga-fsfg R1: a BLOCKED seat may observe remote PR, CI and ref state."""

    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create -R loucmane/gascity --base main --head codex/x --title t --body b",
        "gh pr merge 44 -R loucmane/gascity --merge",
        "gh pr ready 44",
        "gh pr comment 44 --body hello",
        "gh pr edit 44 --title renamed",
        "gh pr view 44 --web",
        "gh pr checks 44 -w",
        "gh run rerun 1 --failed",
        "gh run cancel 1",
        "gh run download 1",
        "gh api repos/loucmane/gascity/pulls/44",
        "gh repo clone loucmane/gascity",
        "gh auth login",
        "git fetch origin main:main",
        "git fetch --update-head-ok origin",
        "git fetch origin +refs/heads/*:refs/remotes/origin/*",
        "git fetch --force origin",
        "git fetch --depth=1 origin",
        "git fetch origin main other",
        "git pull --ff-only origin main",
        "git ls-remote --exit-code origin main && git merge origin/main",
    ],
)
def test_pretooluse_remote_writes_stay_hookable_mutations_before_readiness(
    tmp_path: Path, command: str
) -> None:
    """ga-fsfg R1: only the closed read grammar is exempt; everything else stays gated."""

    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 2
    assert '"permissionDecision": "allow"' not in result.stdout


def test_pretooluse_blocks_read_only_aegis_cli_target_outside_project_before_readiness(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, ready=False)
    outside = tmp_path / "outside-project"
    outside.mkdir()

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("Bash", command=f"./.aegis/bin/aegis reconcile --target-dir {outside.as_posix()}"),
    )

    assert result.returncode == 2
    assert "target_dir escapes governed project root" in result.stderr
    assert "readiness is BLOCKED" not in result.stderr


def test_pretooluse_blocks_read_only_aegis_mcp_target_outside_project_before_readiness(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, ready=False)
    outside = tmp_path / "outside-project"
    outside.mkdir()

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("mcp__aegis__aegis_reconcile", target_dir=outside.as_posix()),
    )

    assert result.returncode == 2
    assert "target_dir escapes governed project root" in result.stderr
    assert "readiness is BLOCKED" not in result.stderr


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("mcp__aegis__aegis_repair", {"apply": False}),
        ("mcp__aegis__aegis_repair", {"apply": True}),
        ("mcp__aegis__aegis_handoff_repair", {"apply": False}),
        (
            "mcp__aegis__aegis_kickoff",
            {
                "task": "157",
                "slug": "read-only-classification",
                "title": "Task 157",
                "apply": True,
            },
        ),
        ("mcp__aegis__aegis_start", {"title": "Task 157", "apply": True}),
    ],
)
def test_pretooluse_confines_every_aegis_mcp_target_dir_before_readiness(
    tmp_path: Path, tool_name: str, tool_input: dict[str, object]
) -> None:
    repo = make_repo(tmp_path, ready=False)
    outside = tmp_path / "outside-project"
    outside.mkdir()

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload(tool_name, **{**tool_input, "target_dir": outside.as_posix()}),
    )

    assert result.returncode == 2
    assert "target_dir escapes governed project root" in result.stderr
    assert "readiness is BLOCKED" not in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "./.aegis/bin/aegis repair --target-dir . --apply",
        "python3 -m aegis_foundation.cli repair --target-dir . --apply",
    ],
)
def test_pretooluse_allows_aegis_repair_apply_when_readiness_blocked(
    tmp_path: Path, command: str
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_allows_aegis_mcp_repair_apply_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("mcp__aegis__aegis_repair", target_dir=".", apply=True),
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_allows_aegis_enforce_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("Bash", command="./.aegis/bin/aegis enforce --mode advisory --reason pause"),
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_blocks_compounded_aegis_enforce_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("Bash", command="./.aegis/bin/aegis enforce --mode advisory && touch state.txt"),
    )

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_pretooluse_blocks_compounded_aegis_repair_apply_when_readiness_blocked(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload(
            "Bash", command="./.aegis/bin/aegis repair --target-dir . --apply && touch state.txt"
        ),
    )

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_pretooluse_blocks_aegis_repair_apply_while_pending_tracking_exists(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)
    write(
        repo / ".aegis" / "state" / "pending-tracking.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "events": [
                    {
                        "id": "pending-1",
                        "h": "bash:test",
                        "e": "cmd`touch state.txt`",
                    }
                ],
            }
        ),
    )

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("Bash", command="./.aegis/bin/aegis repair --target-dir . --apply"),
    )

    assert result.returncode == 2
    assert "pending S:W:H:E tracking must be logged" in result.stderr


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("mcp__aegis__aegis_closeout", {"target_dir": "."}),
        ("mcp__taskmaster_ai__set_task_status", {"id": "183", "status": "done"}),
        ("Write", {"file_path": "README.md"}),
    ],
)
def test_pretooluse_still_blocks_non_repair_mutations_when_readiness_blocked(
    tmp_path: Path, tool_name: str, tool_input: dict[str, object]
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload(tool_name, **tool_input))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_pretooluse_short_circuits_read_only_before_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path, ready=False)
    gate_lib = load_gate_lib_module()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    monkeypatch.setattr(
        gate_lib.sys, "stdin", io.StringIO(payload("Bash", command="git status --short"))
    )

    def fail_readiness(root: Path) -> subprocess.CompletedProcess[str]:
        raise AssertionError(f"readiness should not run for read-only payloads: {root}")

    monkeypatch.setattr(gate_pretool, "run_readiness", fail_readiness)

    assert gate_lib.pretooluse_gate() == 0


def test_pretooluse_degraded_allows_non_destructive_when_gate_infra_crashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = make_repo(tmp_path, ready=True)
    gate_lib = load_gate_lib_module()
    raw = payload("Bash", command="git status --short")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))

    def fail_classifier(_payload: object) -> bool:
        raise RuntimeError("synthetic classifier crash")

    monkeypatch.setattr(gate_pretool, "payload_is_read_only", fail_classifier)

    assert gate_lib.pretooluse_gate_with_degraded_fallback(raw) == 0
    captured = capsys.readouterr()
    assert "DEGRADED" in captured.err
    degraded = json.loads(
        (repo / ".aegis" / "state" / "degraded-events.json").read_text(encoding="utf-8")
    )
    event = degraded["events"][0]
    assert event["mode"] == "degraded_allow"
    assert event["action_class"] == "non_destructive"
    assert event["tool"] == "Bash"
    assert event["event_hash"]


def test_pretooluse_degraded_fails_closed_for_mutation_when_gate_infra_crashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = make_repo(tmp_path, ready=True)
    gate_lib = load_gate_lib_module()
    raw = payload("Write", file_path="src/main.ts")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))

    def fail_classifier(_payload: object) -> bool:
        raise RuntimeError("synthetic classifier crash")

    monkeypatch.setattr(gate_pretool, "payload_is_read_only", fail_classifier)

    assert gate_lib.pretooluse_gate_with_degraded_fallback(raw) == 2
    captured = capsys.readouterr()
    assert "fails closed" in captured.err
    assert not (repo / ".aegis" / "state" / "degraded-events.json").exists()


def test_stop_gate_advisory_records_would_block_without_blocking(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)
    write(
        repo / ".aegis" / "state" / "enforcement.json",
        json.dumps(
            {
                "mode": "advisory",
                "set_at": "2026-06-10T10:00:00Z",
                "set_by": "test",
                "reason": "regression test",
            }
        ),
    )
    write(
        repo / ".aegis" / "state" / "pending-tracking.json",
        json.dumps(
            {"events": [{"id": "pending-1", "handler": "bash:touch", "evidence": "cmd`touch x`"}]}
        ),
    )

    result = run(
        ["bash", str(REPO_ROOT / ".claude" / "scripts" / "tracking-stop-gate.sh")],
        repo,
        env=gate_env(repo),
    )

    assert result.returncode == 0
    assert "ADVISORY | stop would have blocked" in result.stderr
    decisions = read_gate_decisions(repo)
    assert decisions[-1]["hook"] == "stop"
    assert decisions[-1]["verdict"] == "would_block"
    assert decisions[-1]["reason"] == "pending_tracking"
    assert decisions[-1]["mode"] == "advisory"


def test_posttooluse_tags_pending_tracking_with_enforcement_mode(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)
    write(
        repo / ".aegis" / "state" / "current-work.json",
        json.dumps(
            {
                "status": "in-progress",
                "task": {"id": "103", "slug": "claude-runtime-adapter"},
            }
        ),
    )
    write(
        repo / ".aegis" / "state" / "enforcement.json",
        json.dumps(
            {
                "mode": "advisory",
                "set_at": "2026-06-10T10:00:00Z",
                "set_by": "test",
                "reason": "regression test",
            }
        ),
    )

    result = run(
        ["bash", str(POSTTOOLUSE)],
        repo,
        input_text=payload("Bash", command="touch state.txt"),
        env=gate_env(repo),
    )

    assert result.returncode == 0
    pending = json.loads(
        (repo / ".aegis" / "state" / "pending-tracking.json").read_text(encoding="utf-8")
    )
    assert pending["events"][0]["mode"] == "advisory"


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("Bash", {"command": "git status --short"}),
        ("Bash", {"command": "./.aegis/bin/aegis reconcile --target-dir ."}),
        ("Bash", {"command": "jq -c . .aegis/reports/reconcile.json"}),
        ("Bash", {"command": "git status --short > status.txt"}),
        ("Bash", {"command": "git status --short | tee status.txt"}),
        ("Bash", {"command": "sed -i 's/a/b/' README.md"}),
        ("Bash", {"command": "python3 -c \"open('state.txt','w').write('x')\""}),
        ("mcp__aegis__aegis_reconcile", {"target_dir": "."}),
        ("mcp__aegis__aegis_repair", {"target_dir": ".", "apply": False}),
        (
            "mcp__aegis__aegis_kickoff",
            {
                "target_dir": "__OUTSIDE__",
                "task": "157",
                "slug": "x",
                "title": "X",
                "apply": True,
            },
        ),
        ("mcp__unknown__write_state", {"path": "state.txt"}),
        ("mcp__taskmaster_ai__next_task", {}),
        ("mcp__taskmaster_ai__set_task_status", {"id": "157", "status": "done"}),
        ("Write", {"file_path": "src/main.py"}),
    ],
)
def test_degraded_classifier_matches_main_classifier_for_accessors_and_write_sinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    tool_input: dict[str, object],
) -> None:
    repo = make_repo(tmp_path, ready=True)
    outside = tmp_path / "outside-project"
    outside.mkdir()
    gate_lib = load_gate_lib_module()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))

    resolved_input = {
        key: (outside.as_posix() if value == "__OUTSIDE__" else value)
        for key, value in tool_input.items()
    }
    classified = gate_lib.Payload(tool_name, resolved_input)

    assert gate_lib.payload_is_read_only(
        classified
    ) is gate_lib.degraded_payload_is_non_destructive(classified)


def test_degraded_gate_has_no_dead_safe_command_allowlist() -> None:
    live_hook = (REPO_ROOT / ".claude" / "scripts" / "gate_lib.py").read_text(encoding="utf-8")
    packaged_hook = (
        REPO_ROOT / "aegis_foundation" / "assets" / ".claude" / "scripts" / "gate_lib.py"
    ).read_text(encoding="utf-8")

    assert live_hook == packaged_hook
    assert "DEGRADED_SAFE_SIMPLE_BASH_COMMANDS" not in live_hook
    assert "DEGRADED_SAFE_SIMPLE_BASH_COMMANDS" not in packaged_hook


def test_degraded_classifier_structurally_delegates_to_main_classifier() -> None:
    gate_lib = load_gate_lib_module()
    degraded_bash_segment_source = inspect.getsource(
        gate_lib.degraded_bash_segment_is_non_destructive
    )
    degraded_bash_source = inspect.getsource(gate_lib.degraded_bash_is_non_destructive)
    degraded_payload_source = inspect.getsource(gate_lib.degraded_payload_is_non_destructive)
    degraded_source = "\n".join(
        [degraded_bash_segment_source, degraded_bash_source, degraded_payload_source]
    )

    assert "return bash_segment_is_read_only(segment)" in degraded_bash_segment_source
    assert "return bash_is_read_only(command)" in degraded_bash_source
    assert "return not mcp_is_mutation(payload)" in degraded_payload_source
    assert "DEGRADED_SAFE_SIMPLE_BASH_COMMANDS" not in degraded_source
    assert "READ_ONLY_GIT_SUBCOMMANDS" not in degraded_source
    assert "READ_ONLY_AEGIS_SUBCOMMANDS" not in degraded_source
    assert "READ_ONLY_TASKMASTER_SUBCOMMANDS" not in degraded_source


def test_pretooluse_mutation_still_invokes_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path, ready=False)
    gate_lib = load_gate_lib_module()
    calls: list[Path] = []
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    monkeypatch.setattr(
        gate_lib.sys, "stdin", io.StringIO(payload("Bash", command="unknown-tool --maybe-mutates"))
    )

    def fake_readiness(root: Path) -> subprocess.CompletedProcess[str]:
        calls.append(root)
        return subprocess.CompletedProcess(["readiness"], 2, "BLOCKED | synthetic\n", "")

    monkeypatch.setattr(gate_pretool, "run_readiness", fake_readiness)

    assert gate_lib.pretooluse_gate() == 2
    assert calls == [repo.resolve()]


@pytest.mark.parametrize(
    "command",
    [
        "python3 -c \"print('unknown')\"",
        "npm run build",
        "find . -delete",
        "pytest --junitxml=reports/results.xml",
        "cat README.md > out.txt",
        "jq -c . .aegis/reports/reconcile.json > out.json",
        "task-master generate",
        "git commit -m test",
    ],
)
def test_pretooluse_blocks_unknown_or_writing_bash_when_readiness_blocked(
    tmp_path: Path, command: str
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "jq -c . .aegis/reports/reconcile.json",
        "column -t data.tsv",
        "cut -d, -f1 data.csv",
    ],
)
def test_pretooluse_allows_read_only_inspection_when_readiness_blocked(
    tmp_path: Path, command: str
) -> None:
    # Read-only inspection is permitted even when readiness is BLOCKED (TM 216):
    # these write only to stdout, so they must not be treated as mutations. A
    # redirect to a file makes them writes — that case stays blocked above.
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 0, result.stderr


def test_pretooluse_blocks_bash_mutation_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command="echo x > README.md"))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


@pytest.mark.parametrize("hook_payload", ["", "{}"])
def test_pretooluse_allows_empty_payload_when_readiness_blocked(
    tmp_path: Path, hook_payload: str
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, hook_payload)

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_blocks_malformed_nonempty_payload(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, '{"tool_name": "Write",')

    assert result.returncode == 2
    assert "could not be parsed or classified safely" in result.stderr
    assert "invalid JSON" in result.stderr


def test_pretooluse_blocks_non_object_payload(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, '["Write"]')

    assert result.returncode == 2
    assert "hook payload JSON must be an object" in result.stderr


def test_pretooluse_blocks_payload_missing_tool_name(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, json.dumps({"tool_input": {"file_path": "src/main.ts"}}))

    assert result.returncode == 2
    assert "missing required field 'tool_name'" in result.stderr


@pytest.mark.parametrize(
    ("tool_name", "expected_field"),
    [
        ("Write", "file_path"),
        ("Edit", "file_path"),
        ("MultiEdit", "file_path"),
        ("NotebookEdit", "notebook_path"),
        ("Bash", "command"),
    ],
)
def test_pretooluse_blocks_hookable_payload_missing_required_tool_input(
    tmp_path: Path, tool_name: str, expected_field: str
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload(tool_name))

    assert result.returncode == 2
    assert "could not be parsed or classified safely" in result.stderr
    assert expected_field in result.stderr


def test_pretooluse_blocks_codex_owned_file_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Edit", file_path="CODEX.md"))

    assert result.returncode == 2
    assert "Protected path" in result.stderr
    assert "CODEX.md" in result.stderr


def test_pretooluse_allows_task_source_file_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Write", file_path="src/main.ts"))

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_allows_task_report_file_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)
    report_path = "docs/ai/work-tracking/active/20260506-task103-claude-runtime-adapter-ACTIVE/reports/verify.txt"

    result = run_gate(PRETOOLUSE, repo, payload("Write", file_path=report_path))

    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize(
    "workflow_path",
    [
        "sessions/current",
        "plans/current",
        "docs/ai/work-tracking/active/20260506-task103-claude-runtime-adapter-ACTIVE/HANDOFF.md",
    ],
)
def test_pretooluse_blocks_direct_workflow_owned_file_edits_when_ready(
    tmp_path: Path, workflow_path: str
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Write", file_path=workflow_path))

    assert result.returncode == 2
    assert "Workflow-owned path" in result.stderr
    assert workflow_path in result.stderr


@pytest.mark.parametrize(
    "protected_path",
    [
        "CLAUDE.md",
        "AGENTS.md",
        ".aegis/foundation-manifest.json",
        ".claude/settings.json",
    ],
)
def test_pretooluse_blocks_aegis_runtime_files_when_ready(
    tmp_path: Path, protected_path: str
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Write", file_path=protected_path))

    assert result.returncode == 2
    assert "Protected path" in result.stderr
    assert protected_path in result.stderr


def test_pretooluse_blocks_bash_redirect_to_codex_path_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command="printf 'x' > CODEX.md"))

    assert result.returncode == 2
    assert "redirection targets protected path CODEX.md" in result.stderr


def test_pretooluse_blocks_bash_redirect_to_aegis_runtime_path_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(
        PRETOOLUSE, repo, payload("Bash", command="printf 'x' > .aegis/foundation-manifest.json")
    )

    assert result.returncode == 2
    assert "redirection targets protected path .aegis/foundation-manifest.json" in result.stderr


def test_pretooluse_blocks_bash_sed_i_template_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command="sed -i 's/a/b/' templates/foo.md"))

    assert result.returncode == 2
    assert "sed -i targets protected path templates/foo.md" in result.stderr


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "printf 'x' > sessions/current",
            "redirection targets workflow-owned path sessions/current",
        ),
        ("touch plans/current", "touch references workflow-owned path plans/current"),
        (
            "python3 -c \"open('docs/ai/work-tracking/active/t/HANDOFF.md','w').write('x')\"",
            "python write targets workflow-owned path docs/ai/work-tracking/active/t/HANDOFF.md",
        ),
    ],
)
def test_pretooluse_blocks_bash_workflow_owned_mutations_when_ready(
    tmp_path: Path, command: str, expected: str
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 2
    assert expected in result.stderr


def test_pretooluse_allows_bash_writes_to_task_reports_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload(
            "Bash",
            command="printf 'ok\\n' > docs/ai/work-tracking/active/t/reports/task-verification.txt",
        ),
    )

    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize(
    "command",
    [
        "./.aegis/bin/aegis log --target-dir . --handler test --evidence docs/ai/work-tracking/active/t/FINDINGS.md --note ok",
        "./.aegis/bin/aegis handoff repair --target-dir .",
        "./.aegis/bin/aegis closeout --target-dir . --update-handoff",
    ],
)
def test_pretooluse_allows_sanctioned_aegis_cli_workflow_mutations_when_ready(
    tmp_path: Path, command: str
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_blocks_protected_mutation_after_sanctioned_aegis_cli_segment_when_ready(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, ready=True)
    command = (
        "./.aegis/bin/aegis log --target-dir . --handler test "
        "--evidence docs/ai/work-tracking/active/t/FINDINGS.md --note ok && touch sessions/current"
    )

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 2
    assert "touch references workflow-owned path sessions/current" in result.stderr


def test_pretooluse_does_not_treat_bare_aegis_as_sanctioned_mutation_when_blocked(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(
        PRETOOLUSE, repo, payload("Bash", command='aegis kickoff --task 1 --slug x --title "X"')
    )

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_pretooluse_allows_project_local_aegis_bootstrap_when_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("Bash", command='./.aegis/bin/aegis kickoff --task 1 --slug x --title "X"'),
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_posttooluse_tracks_aegis_verify_as_report_evidence(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)
    write(
        repo / ".aegis" / "state" / "current-work.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "status": "in-progress",
                "task": {"id": "103", "slug": "claude-runtime-adapter"},
                "paths": {},
            }
        ),
    )

    result = run_gate(
        POSTTOOLUSE, repo, payload("Bash", command="./.aegis/bin/aegis verify --strict")
    )

    assert result.returncode == 0, result.stderr
    pending = json.loads(
        (repo / ".aegis" / "state" / "pending-tracking.json").read_text(encoding="utf-8")
    )
    assert pending["events"][0]["handler"] == "aegis:verify"
    assert pending["events"][0]["evidence"] == ".aegis/reports/verification-report.json"


def test_pretooluse_allows_safe_read_only_bash_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command="cat sessions/state.json"))

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_blocks_mutating_mcp_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(
        PRETOOLUSE, repo, payload("mcp__taskmaster_ai__set_task_status", id="105", status="done")
    )

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("mcp__taskmaster_ai__help", {}),
        ("mcp__taskmaster_ai__get_tasks", {}),
        ("mcp__taskmaster_ai__next_task", {}),
        ("mcp__taskmaster_ai__get_task", {"id": "105"}),
        ("mcp__taskmaster-ai__help", {}),
        ("mcp__taskmaster-ai__next_task", {}),
        ("mcp__taskmaster-ai__get_task", {"id": "105"}),
        ("mcp__aegis__aegis_reconcile", {"target_dir": "."}),
    ],
)
def test_pretooluse_allows_taskmaster_read_only_discovery_when_readiness_blocked(
    tmp_path: Path, tool_name: str, tool_input: dict[str, str]
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload(tool_name, **tool_input))

    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("mcp__taskmaster_ai__set_task_status", {"id": "105", "status": "done"}),
        ("mcp__taskmaster_ai__update_task", {"id": "105", "prompt": "notes"}),
        ("mcp__taskmaster_ai__update_subtask", {"id": "105.1", "prompt": "notes"}),
        ("mcp__taskmaster_ai__add_task", {"prompt": "new task"}),
        ("mcp__taskmaster_ai__expand_task", {"id": "105"}),
        ("mcp__taskmaster_ai__parse_prd", {"input": ".taskmaster/docs/prd.txt"}),
        ("mcp__taskmaster_ai__generate", {}),
        ("mcp__taskmaster_ai__add_dependency", {"id": "105", "depends_on": "104"}),
        ("mcp__taskmaster_ai__move_task", {"from_id": "105", "to_id": "106"}),
        ("mcp__taskmaster_ai__show", {"id": "105"}),
        ("mcp__taskmaster_ai__forget_task", {"id": "105"}),
        ("mcp__taskmaster_ai__sync_remote_state", {}),
    ],
)
def test_pretooluse_blocks_taskmaster_mcp_mutations_and_unknowns_when_readiness_blocked(
    tmp_path: Path, tool_name: str, tool_input: dict[str, str]
) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload(tool_name, **tool_input))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_pretooluse_blocks_unknown_mcp_when_readiness_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload("mcp__custom__sync_remote_state", target="prod"))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_pretooluse_allows_matching_taskmaster_done_after_closeout(tmp_path: Path) -> None:
    repo = make_completed_closeout_repo(tmp_path)

    result = run_gate(
        PRETOOLUSE, repo, payload("Bash", command="task-master set-status --id=103 --status=done")
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_allows_taskmaster_generate_after_closeout(tmp_path: Path) -> None:
    repo = make_completed_closeout_repo(tmp_path)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload("Bash", command="test -f scripts/codex-task; task-master generate"),
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_allows_matching_taskmaster_mcp_done_after_closeout(tmp_path: Path) -> None:
    repo = make_completed_closeout_repo(tmp_path)

    result = run_gate(
        PRETOOLUSE, repo, payload("mcp__taskmaster_ai__set_task_status", id="103", status="done")
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_blocks_nonmatching_taskmaster_done_after_closeout(tmp_path: Path) -> None:
    repo = make_completed_closeout_repo(tmp_path)

    result = run_gate(
        PRETOOLUSE, repo, payload("Bash", command="task-master set-status --id=999 --status=done")
    )

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_pretooluse_blocks_source_mutation_after_closeout(tmp_path: Path) -> None:
    repo = make_completed_closeout_repo(tmp_path)

    result = run_gate(PRETOOLUSE, repo, payload("Write", file_path="src/main.ts"))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr


def test_posttooluse_does_not_track_post_closeout_taskmaster_done(tmp_path: Path) -> None:
    repo = make_completed_closeout_repo(tmp_path)

    result = run_gate(
        POSTTOOLUSE, repo, payload("Bash", command="task-master set-status --id=103 --status=done")
    )

    assert result.returncode == 0, result.stderr
    assert not (repo / ".aegis" / "state" / "pending-tracking.json").exists()


def test_pretooluse_blocks_mcp_protected_path_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(
        PRETOOLUSE, repo, payload("mcp__serena__create_text_file", relative_path="CODEX.md")
    )

    assert result.returncode == 2
    assert "Protected path" in result.stderr
    assert "CODEX.md" in result.stderr


def test_pretooluse_blocks_mcp_workflow_owned_path_when_ready(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload(
            "mcp__serena__create_text_file",
            relative_path="docs/ai/work-tracking/active/t/HANDOFF.md",
        ),
    )

    assert result.returncode == 2
    assert "Workflow-owned path" in result.stderr
    assert "docs/ai/work-tracking/active/t/HANDOFF.md" in result.stderr


def test_pretooluse_allows_sanctioned_aegis_mcp_workflow_mutation_when_ready(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(
        PRETOOLUSE,
        repo,
        payload(
            "mcp__aegis__aegis_log",
            target_dir=repo.as_posix(),
            path="docs/ai/work-tracking/active/t/FINDINGS.md",
            note="Recorded structured evidence",
        ),
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_path_guard_blocks_direct_protected_file_payload(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(PATH_GUARD, repo, payload("Write", file_path="templates/runtime.md"))

    assert result.returncode == 2
    assert "templates/runtime.md" in result.stderr


def test_bash_guard_blocks_python_open_write_to_protected_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=True)

    result = run_gate(
        BASH_GUARD,
        repo,
        payload("Bash", command="python3 -c \"open('scripts/codex-task','w').write('x')\""),
    )

    assert result.returncode == 2
    assert "scripts/codex-task" in result.stderr
