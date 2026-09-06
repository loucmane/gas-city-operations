from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest
from aegis_foundation.gate.hooks import pretool as gate_pretool


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_LIB = REPO_ROOT / ".claude" / "scripts" / "gate_lib.py"
PRETOOLUSE = REPO_ROOT / ".claude" / "scripts" / "pretooluse-gate.sh"
POSTTOOLUSE = REPO_ROOT / ".claude" / "scripts" / "posttooluse-tracking.sh"


def run(
    cmd: list[str],
    cwd: Path,
    *,
    input_text: str = "",
    env: dict[str, str] | None = None,
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


def payload(command: str, *, repo: Path | None = None) -> str:
    body: dict[str, object] = {
        "tool_name": "apply_patch",
        "tool_input": {"command": command},
        "session_id": "codex-task248-smoke",
    }
    if repo is not None:
        body["cwd"] = str(repo)
    return json.dumps(body)


def run_gate(script: Path, repo: Path, hook_payload: str) -> subprocess.CompletedProcess[str]:
    return run(
        ["bash", str(script)],
        repo,
        input_text=hook_payload,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    )


def load_gate_lib_module():
    module_name = "codex_apply_patch_gate_lib_under_test"
    spec = importlib.util.spec_from_file_location(module_name, GATE_LIB)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path: Path, *, ready: bool = True) -> Path:
    repo = tmp_path / ("ready" if ready else "blocked")
    repo.mkdir(parents=True)
    assert run(["git", "init", "-q"], repo).returncode == 0
    branch = "feat/task-248-codex-hook-adapter" if ready else "feature/no-task"
    assert run(["git", "checkout", "-q", "-b", branch], repo).returncode == 0
    if not ready:
        return repo

    write(
        repo / ".taskmaster" / "tasks" / "tasks.json",
        json.dumps(
            {
                "master": {
                    "tasks": [
                        {
                            "id": 248,
                            "title": "Implement First-Class Codex Hook Adapter",
                            "status": "in-progress",
                        }
                    ]
                }
            }
        ),
    )
    session_rel = Path("2026/07/2026-07-13-004-task248-codex-hook-adapter.md")
    write(repo / "sessions" / session_rel, "# Task 248 Session\n")
    (repo / "sessions" / "current").symlink_to(session_rel)
    write(
        repo / "sessions" / "state.json",
        json.dumps(
            {"current": session_rel.name, "paused": [], "updated_at": "2026-07-13T21:00:00+02:00"}
        ),
    )
    plan_rel = Path("2026-07-13-task248-codex-hook-adapter.md")
    write(
        repo / "plans" / plan_rel,
        """---
task_ids: [248]
---

# Plan - Task 248

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
        / "20260713-task248-codex-hook-adapter-ACTIVE"
    )
    write(
        active / "TRACKER.md",
        """# Task 248 Codex Hook Adapter Tracker

## Plan Compliance Checklist
- [x] plan-step-scope - Scope
- [ ] plan-step-implement - Implement
- [ ] plan-step-verify - Verify
""",
    )
    write(
        repo / ".aegis" / "state" / "current-work.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "status": "in-progress",
                "task": {"id": "248", "slug": "codex-hook-adapter", "status": "in-progress"},
                "paths": {
                    "session": (Path("sessions") / session_rel).as_posix(),
                    "plan": (Path("plans") / plan_rel).as_posix(),
                },
            }
        ),
    )
    return repo


def set_advisory(repo: Path) -> None:
    write(
        repo / ".aegis" / "state" / "enforcement.json",
        json.dumps(
            {
                "mode": "advisory",
                "set_at": "2026-07-13T21:00:00Z",
                "set_by": "test",
                "reason": "Task 248 regression",
            }
        ),
    )


ADD_PATCH = """*** Begin Patch
*** Add File: src/new.py
+print(\"new\")
*** End Patch"""

UPDATE_PATCH = """*** Begin Patch
*** Update File: src/existing.py
@@
-old
+new
*** End Patch"""

DELETE_PATCH = """*** Begin Patch
*** Delete File: src/old.py
*** End Patch"""

MOVE_PATCH = """*** Begin Patch
*** Update File: src/old-name.py
*** Move to: src/new-name.py
@@
-old
+new
*** End Patch"""


@pytest.mark.parametrize(
    ("command", "operation", "paths"),
    [
        (ADD_PATCH, "add", ["src/new.py"]),
        (UPDATE_PATCH, "update", ["src/existing.py"]),
        (DELETE_PATCH, "delete", ["src/old.py"]),
        (MOVE_PATCH, "update", ["src/old-name.py", "src/new-name.py"]),
    ],
)
def test_parse_canonical_apply_patch_operations(
    tmp_path: Path,
    command: str,
    operation: str,
    paths: list[str],
) -> None:
    gate_lib = load_gate_lib_module()
    repo = make_repo(tmp_path)

    parsed = gate_lib.parse_apply_patch(command, repo)

    assert parsed.operations[0].operation == operation
    assert list(parsed.affected_paths) == paths
    assert parsed.patch_digest == sha256(command.encode("utf-8")).hexdigest()
    if command == MOVE_PATCH:
        assert parsed.operations[0].destination_path == "src/new-name.py"


@pytest.mark.parametrize(
    "command",
    [
        "",
        "*** Begin Patch\n*** End Patch",
        "*** Add File: src/no-envelope.py\n+bad",
        "*** Begin Patch\n*** Add File: src/no-end.py\n+x",
        "*** Begin Patch\n*** Add File: src/empty.py\n*** End Patch",
        "*** Begin Patch\n*** Update File: src/empty.py\n*** End Patch",
        "*** Begin Patch\n*** Delete File: src/old.py\n+unexpected\n*** End Patch",
        "*** Begin Patch\n*** Move to: src/new.py\n*** End Patch",
        "*** Begin Patch\n*** Update File: src/a.py\n@@\n*** Move to: src/b.py\n*** End Patch",
        "*** Begin Patch\n*** Add File: ../escape.py\n+x\n*** End Patch",
        "*** Begin Patch\n*** Add File: src/a.py\n+x\n*** Update File: src/a.py\n@@\n+y\n*** End Patch",
        "*** Begin Patch\n*** Unsupported File: src/a.py\n+x\n*** End Patch",
        "*** Begin Patch\n*** Begin Patch\n*** Delete File: src/a.py\n*** End Patch",
    ],
)
def test_parse_rejects_malformed_ambiguous_or_unsupported_patches(
    tmp_path: Path, command: str
) -> None:
    gate_lib = load_gate_lib_module()
    repo = make_repo(tmp_path)

    with pytest.raises(gate_lib.ApplyPatchParseError):
        gate_lib.parse_apply_patch(command, repo)


def test_parse_rejects_absolute_path_even_when_it_resolves_inside_repo(tmp_path: Path) -> None:
    gate_lib = load_gate_lib_module()
    repo = make_repo(tmp_path)
    command = (
        "*** Begin Patch\n"
        f"*** Add File: {(repo / 'src' / 'absolute.py').as_posix()}\n"
        "+value = True\n"
        "*** End Patch"
    )

    with pytest.raises(gate_lib.ApplyPatchParseError, match="repository-relative"):
        gate_lib.parse_apply_patch(command, repo)


def test_pretooluse_allows_ready_multifile_patch_and_checks_every_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    command = """*** Begin Patch
*** Add File: src/first.py
+first = True
*** Update File: src/second.py
@@
-old
+new
*** End Patch"""

    result = run_gate(PRETOOLUSE, repo, payload(command, repo=repo))

    assert result.returncode == 0
    assert result.stderr == ""


def test_pretooluse_blocks_apply_patch_when_readiness_is_blocked(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, ready=False)

    result = run_gate(PRETOOLUSE, repo, payload(ADD_PATCH, repo=repo))

    assert result.returncode == 2
    assert "readiness is BLOCKED" in result.stderr
    assert "Tool: apply_patch" in result.stderr


def test_observation_mode_blocks_apply_patch_strictly_and_records_it_advisorially(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    current_work_path = repo / ".aegis" / "state" / "current-work.json"
    current_work = json.loads(current_work_path.read_text(encoding="utf-8"))
    current_work["mode"] = "observation"
    write(current_work_path, json.dumps(current_work))

    strict = run_gate(PRETOOLUSE, repo, payload(ADD_PATCH, repo=repo))
    assert strict.returncode == 2
    assert "observation mode only permits observation tooling" in strict.stderr

    set_advisory(repo)
    advisory = run_gate(PRETOOLUSE, repo, payload(ADD_PATCH, repo=repo))
    assert advisory.returncode == 0
    assert "observation_mode_disallowed_mutation" in advisory.stderr
    decision = json.loads(
        (repo / ".aegis" / "reports" / "gate-decisions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    assert decision["verdict"] == "would_block"
    assert decision["reason"] == "observation_mode_disallowed_mutation"


@pytest.mark.parametrize(
    ("later_header", "expected_reason"),
    [
        ("*** Add File: .codex/hooks.json\n+{}", "Protected path(s)"),
        ("*** Update File: plans/current\n@@\n-old\n+new", "Workflow-owned path(s)"),
        (
            "*** Update File: src/name.py\n*** Move to: .claude/owned.py\n@@\n-old\n+new",
            "Protected path(s)",
        ),
    ],
)
def test_safe_first_path_never_hides_guarded_later_path(
    tmp_path: Path,
    later_header: str,
    expected_reason: str,
) -> None:
    repo = make_repo(tmp_path)
    command = (
        f"*** Begin Patch\n*** Add File: src/safe.py\n+safe = True\n{later_header}\n*** End Patch"
    )

    result = run_gate(PRETOOLUSE, repo, payload(command, repo=repo))

    assert result.returncode == 2
    assert expected_reason in result.stderr


def test_malformed_apply_patch_is_strictly_blocked_and_advisory_recorded(tmp_path: Path) -> None:
    malformed = "*** Begin Patch\n*** Add File: src/empty.py\n*** End Patch"
    strict_repo = make_repo(tmp_path / "strict")
    advisory_repo = make_repo(tmp_path / "advisory")
    set_advisory(advisory_repo)

    strict_result = run_gate(PRETOOLUSE, strict_repo, payload(malformed, repo=strict_repo))
    advisory_result = run_gate(PRETOOLUSE, advisory_repo, payload(malformed, repo=advisory_repo))

    assert strict_result.returncode == 2
    assert "invalid_apply_patch" in strict_result.stderr
    assert advisory_result.returncode == 0
    assert "ADVISORY" in advisory_result.stderr
    decisions = [
        json.loads(line)
        for line in (advisory_repo / ".aegis" / "reports" / "gate-decisions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert decisions[-1]["tool_name"] == "apply_patch"
    assert decisions[-1]["verdict"] == "would_block"
    assert str(decisions[-1]["reason"]).startswith("invalid_apply_patch:")


def test_degraded_apply_patch_fails_closed_in_strict_and_records_allow_in_advisory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_lib = load_gate_lib_module()
    strict_repo = make_repo(tmp_path / "strict")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(strict_repo))
    monkeypatch.setattr(
        gate_pretool,
        "pretooluse_gate",
        lambda _raw: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    raw = payload(ADD_PATCH, repo=strict_repo)

    assert gate_lib.pretooluse_gate_with_degraded_fallback(raw) == 2

    advisory_repo = make_repo(tmp_path / "advisory")
    set_advisory(advisory_repo)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(advisory_repo))
    raw = payload(ADD_PATCH, repo=advisory_repo)

    assert gate_lib.pretooluse_gate_with_degraded_fallback(raw) == 0
    degraded = json.loads(
        (advisory_repo / ".aegis" / "state" / "degraded-events.json").read_text(encoding="utf-8")
    )
    assert degraded["events"][0]["mode"] == "degraded_advisory_allow"
    assert degraded["events"][0]["tool"] == "apply_patch"


def test_posttooluse_records_one_atomic_event_with_every_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    command = """*** Begin Patch
*** Add File: src/first.py
+first = True
*** Update File: src/old.py
*** Move to: src/new.py
@@
-old
+new
*** Delete File: src/gone.py
*** End Patch"""

    first = run_gate(POSTTOOLUSE, repo, payload(command, repo=repo))
    duplicate = run_gate(POSTTOOLUSE, repo, payload(command, repo=repo))

    assert first.returncode == 0
    assert duplicate.returncode == 0
    pending = json.loads(
        (repo / ".aegis" / "state" / "pending-tracking.json").read_text(encoding="utf-8")
    )
    assert len(pending["events"]) == 1
    event = pending["events"][0]
    assert event["handler"] == "codex:apply_patch"
    assert event["evidence"] == "src/first.py"
    assert event["affected_paths"] == ["src/first.py", "src/old.py", "src/new.py", "src/gone.py"]
    assert [item["operation"] for item in event["operations"]] == ["add", "move", "delete"]
    assert event["operations"][1]["content_operation"] == "update"
    assert event["patch_digest"] == sha256(command.encode("utf-8")).hexdigest()


def test_posttooluse_records_malformed_patch_as_one_atomic_diagnostic_event(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    malformed = "*** Begin Patch\n*** Add File: src/empty.py\n*** End Patch"

    result = run_gate(POSTTOOLUSE, repo, payload(malformed, repo=repo))

    assert result.returncode == 0
    pending = json.loads(
        (repo / ".aegis" / "state" / "pending-tracking.json").read_text(encoding="utf-8")
    )
    assert len(pending["events"]) == 1
    event = pending["events"][0]
    assert event["handler"] == "codex:apply_patch"
    assert event["affected_paths"] == []
    assert event["operations"] == []
    assert event["patch_digest"] == sha256(malformed.encode("utf-8")).hexdigest()
    assert "Add File requires" in event["parse_error"]


def test_distinct_patches_with_same_primary_path_remain_distinct_atomic_events(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    first = UPDATE_PATCH
    second = UPDATE_PATCH.replace("+new", "+newer")

    assert run_gate(POSTTOOLUSE, repo, payload(first, repo=repo)).returncode == 0
    assert run_gate(POSTTOOLUSE, repo, payload(second, repo=repo)).returncode == 0

    pending = json.loads(
        (repo / ".aegis" / "state" / "pending-tracking.json").read_text(encoding="utf-8")
    )
    assert len(pending["events"]) == 2
    assert len({event["patch_digest"] for event in pending["events"]}) == 2
    assert {event["evidence"] for event in pending["events"]} == {"src/existing.py"}
