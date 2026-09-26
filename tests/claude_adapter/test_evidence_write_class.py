"""ga-fsfg R4: the `evidence-write` class, a stationary create-only native Write.

The canonical seat may create one new file under the single ACTIVE work-tracking
folder's `reports/` directory of an Operations worktree `<W>`. Readiness, observation,
the pending event and advisory handling belong to `<W>`; `workflow.py log --root <W>
--pending-id <id>` discharges the event. Everything else keeps today's behaviour.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_native_command_profile import PROFILE, event, git
from test_pretooluse_gates import (
    POSTTOOLUSE,
    PRETOOLUSE,
    REPO_ROOT,
    read_gate_decisions,
    run_gate,
    write,
)
from test_stationary_orchestrator import command, registered_fixture, stationary_fixture

ACTIVE = "docs/ai/work-tracking/active/20260826-ga-one-beads-first-guidance-ACTIVE"
PENDING = ".aegis/state/pending-tracking.json"


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    monkeypatch.delenv("AEGIS_INVOKING_AGENT", raising=False)


def opt_in(repos):
    value = json.loads((repos[0] / PROFILE).read_text())
    value["commands"].append("evidence-write")
    for repo in repos:
        write(repo / PROFILE, json.dumps(value))
        git(repo, "add", str(PROFILE))
        git(repo, "commit", "-qm", "evidence-write opt-in")


def current_work(target, mode="bead"):
    write(
        target / ".aegis/state/current-work.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "mode": mode,
                "status": "in-progress",
                "task": {
                    "id": "ga-one",
                    "slug": "beads-first-guidance",
                    "source": "gas-city-bead",
                    "status": "in-progress",
                },
                "branch": {"current": "codex/ga-one-beads-first-guidance"},
                "paths": {
                    "session": (target / "sessions/current").resolve().relative_to(target).as_posix(),
                    "plan": (target / "plans/current").resolve().relative_to(target).as_posix(),
                    "work_tracking": ACTIVE,
                },
            }
        ),
    )


def evidence_fixture(tmp_path, *, opted_in=True):
    canonical, target, journal = stationary_fixture(tmp_path)
    if opted_in:
        opt_in([canonical, target])
    (target / ACTIVE / "reports").mkdir()
    current_work(target)
    return canonical, target, journal


def write_payload(canonical, path, content="evidence\n", tool="Write", **extra):
    tool_input = {"file_path": str(path), "content": content}
    if tool == "Edit":
        tool_input = {"file_path": str(path), "old_string": "a", "new_string": "b"}
    elif tool == "MultiEdit":
        tool_input = {"file_path": str(path), "edits": [{"old_string": "a", "new_string": "b"}]}
    elif tool == "NotebookEdit":
        tool_input = {"notebook_path": str(path), "new_source": "x"}
    data = {
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": str(canonical),
        "session_id": "synthetic",
        "permission_mode": "dontAsk",
    }
    data.update(extra)
    return json.dumps(data)


def approved(result) -> bool:
    if result.returncode != 0 or not result.stdout.strip():
        return False
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    return (
        decision["permissionDecision"] == "allow"
        and decision["permissionDecisionReason"] == "aegis-orchestrator:evidence-write"
    )


def refused(result) -> bool:
    return result.returncode == 2 and '"permissionDecision": "allow"' not in result.stdout


def report(target, *names):
    return target.joinpath(ACTIVE, "reports", *names)


# --- Approval, tracking and discharge ---------------------------------------------------


@pytest.mark.parametrize("names", [("r4-proof.md",), ("run", "results.jsonl"), ("notes.txt",)])
def test_evidence_write_is_approved_and_audited_on_the_worktree(tmp_path, names):
    canonical, target, _ = evidence_fixture(tmp_path)
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, report(target, *names)))
    assert approved(result), result.stderr
    assert not read_gate_decisions(canonical)
    assert read_gate_decisions(target)[-1]["reason"] == "native_permission:evidence-write"


def test_the_event_lands_on_the_worktree_after_the_file_exists_and_log_discharges_it(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path)
    path = report(target, "r4-proof.md")
    request = write_payload(canonical, path, "measured evidence\n")
    assert approved(run_gate(PRETOOLUSE, canonical, request))
    path.write_text("measured evidence\n")  # Claude's own Write tool performs the write.

    assert run_gate(POSTTOOLUSE, canonical, request).returncode == 0
    assert not (canonical / PENDING).exists()
    [pending] = json.loads((target / PENDING).read_text())["events"]
    assert pending["handler"] == "claude:Write"
    assert pending["evidence"] == f"{ACTIVE}/reports/r4-proof.md"

    log = command(canonical, target, "log", f" --pending-id {pending['id']} --note recorded")
    assert json.loads(run_gate(PRETOOLUSE, canonical, event(canonical, log)).stdout)[
        "hookSpecificOutput"
    ]["permissionDecisionReason"] == "aegis-orchestrator:workflow-coordinate"
    # The executor's log runs the canonical Aegis CLI for exactly this event; it appends
    # the S:W:H:E entry to the ACTIVE folder's surfaces.
    for name in ("IMPLEMENTATION.md", "CHANGELOG.md", "HANDOFF.md", "FINDINGS.md", "DECISIONS.md"):
        write(target / ACTIVE / name, f"# {name}\n\n## Progress Log\n")
    discharged = subprocess.run(
        [
            sys.executable,
            "-m",
            "aegis_foundation.cli",
            "log",
            "--target-dir",
            str(target),
            "--pending-id",
            pending["id"],
            "--note",
            "Recorded the evidence write",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert discharged.returncode == 0, discharged.stderr
    assert pending["id"] not in pending_ids(target)
    tracker = (target / ACTIVE / "TRACKER.md").read_text()
    assert f"|H:claude:Write|E:{ACTIVE}/reports/r4-proof.md]" in tracker
    assert run_gate(POSTTOOLUSE, canonical, event(canonical, log)).returncode == 0


def pending_ids(root):
    path = root / PENDING
    if not path.exists():
        return []
    return [item["id"] for item in json.loads(path.read_text()).get("events", [])]


# --- Refusals ------------------------------------------------------------------------


def _second_active(canonical, target):
    (target / "docs/ai/work-tracking/active/20260901-ga-two-other-ACTIVE").mkdir()


def _symlinked_reports(canonical, target):
    real = target / "elsewhere-reports"
    real.mkdir()
    report(target).rmdir()
    report(target).symlink_to(real, target_is_directory=True)


def _symlinked_component(canonical, target):
    real = target / "elsewhere"
    real.mkdir()
    report(target, "sub").symlink_to(real, target_is_directory=True)


def _dangling(canonical, target):
    report(target, "new.md").symlink_to(target / "missing.md")


def _observation(root):
    write(
        root / ".aegis/state/current-work.json",
        '{"kind":"observation","mode":"observation","status":"in-progress"}',
    )


def _pending(root):
    write(
        root / PENDING,
        json.dumps({"events": [{"id": "0123456789ab", "mode": "strict", "task": {"id": "ga-one"}}]}),
    )


def _runtime(canonical, target):
    write(target / "aegis_foundation/unreviewed.py", "import os\n")


REFUSALS = {
    # A claimed path that breaks a rule refuses as an invalid coordination target.
    "outside-reports": (lambda c, t: t / ACTIVE / "notes.md", None, "must lie under"),
    "active-root": (lambda c, t: t / "docs/ai/work-tracking/active/new.md", None, "must lie under"),
    "missing-active": (
        lambda c, t: t / "docs/ai/work-tracking/active/20990101-ga-one-x-ACTIVE/reports/new.md",
        None,
        "exactly one ACTIVE folder",
    ),
    "two-active": (lambda c, t: report(t, "new.md"), _second_active, "exactly one ACTIVE folder"),
    "no-reports": (
        lambda c, t: report(t, "new.md"),
        lambda c, t: report(t).rmdir(),
        "never creates",
    ),
    "existing-target": (
        lambda c, t: report(t, "old.md"),
        lambda c, t: report(t, "old.md").write_text("kept\n"),
        "already exists",
    ),
    "dangling-symlink": (lambda c, t: report(t, "new.md"), _dangling, "already exists"),
    "symlinked-reports": (lambda c, t: report(t, "new.md"), _symlinked_reports, "not a link"),
    "symlinked-component": (
        lambda c, t: report(t, "sub", "new.md"),
        _symlinked_component,
        "link or non-directory component",
    ),
    "control-character": (lambda c, t: report(t, "new\x01.md"), None, "control character"),
    "dot-dot": (lambda c, t: Path(f"{report(t)}/../reports/new.md"), None, "canonical absolute"),
    "claude-md": (lambda c, t: report(t, "CLAUDE.md"), None, "refuses the name"),
    "claude-prefix": (lambda c, t: report(t, "claude-notes.md"), None, "refuses the name"),
    "agents-md": (lambda c, t: report(t, "AGENTS.override.md"), None, "refuses the name"),
    "gemini-md": (lambda c, t: report(t, "Gemini.md"), None, "refuses the name"),
    "skill-md": (lambda c, t: report(t, "review-SKILL.md"), None, "refuses the name"),
    "conftest": (lambda c, t: report(t, "conftest.py"), None, "refuses the name"),
    "pth": (lambda c, t: report(t, "hook.pth"), None, "refuses the name"),
    "python": (lambda c, t: report(t, "tool.py"), None, "refuses the name"),
    "python-directory": (lambda c, t: report(t, "pkg.py", "notes.md"), None, "refuses the name"),
    "dot-file": (lambda c, t: report(t, ".hidden.md"), None, "refuses the name"),
    "dot-directory": (lambda c, t: report(t, ".cache", "notes.md"), None, "refuses the name"),
    "suffix-sh": (lambda c, t: report(t, "run.sh"), None, "suffix must be"),
    "suffix-upper": (lambda c, t: report(t, "data.JSON"), None, "suffix must be"),
    "no-suffix": (lambda c, t: report(t, "README"), None, "suffix must be"),
    "observation-seat": (lambda c, t: report(t, "new.md"), lambda c, t: _observation(c), "observation"),
    "observation-target": (
        lambda c, t: report(t, "new.md"),
        lambda c, t: _observation(t),
        "observation",
    ),
    "pending-seat": (lambda c, t: report(t, "new.md"), lambda c, t: _pending(c), "pending tracking"),
    "pending-target": (
        lambda c, t: report(t, "new.md"),
        lambda c, t: _pending(t),
        "pending tracking",
    ),
    "divergent-runtime": (lambda c, t: report(t, "new.md"), _runtime, "runtime"),
}


@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_evidence_write_refusals(tmp_path, case):
    canonical, target, _ = evidence_fixture(tmp_path)
    locate, setup, detail = REFUSALS[case]
    if setup is not None:
        setup(canonical, target)
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, locate(canonical, target)))
    assert refused(result)
    assert detail in result.stderr
    assert not (target / ACTIVE / "reports" / "new.md").is_file()


def test_an_oversized_write_refuses(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path)
    content = "x" * (1024 * 1024 + 1)
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, report(target, "big.log"), content))
    assert refused(result) and "at most 1 MiB" in result.stderr
    exact = run_gate(
        PRETOOLUSE, canonical, write_payload(canonical, report(target, "full.log"), content[:-1])
    )
    assert approved(exact), exact.stderr


@pytest.mark.parametrize("mode", ["plan", "unknown", None])
def test_evidence_write_requires_a_known_non_plan_mode(tmp_path, mode):
    canonical, target, _ = evidence_fixture(tmp_path)
    request = write_payload(canonical, report(target, "new.md"), permission_mode=mode)
    assert refused(run_gate(PRETOOLUSE, canonical, request))


def test_evidence_write_must_originate_at_the_canonical_seat(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path)
    request = write_payload(canonical, report(target, "new.md"), cwd=str(target))
    result = run_gate(PRETOOLUSE, canonical, request)
    assert refused(result) and "must originate at the canonical seat" in result.stderr


def test_a_registered_project_worktree_refuses(tmp_path):
    canonical, target, _, core_target, _ = registered_fixture(tmp_path)
    opt_in([canonical, target])
    reports = core_target / ACTIVE.replace("ga-one", "ga-core") / "reports"
    reports.mkdir(parents=True)
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, reports / "new.md"))
    assert refused(result)
    assert "registered-project and review-project worktrees refuse" in result.stderr


def test_an_unregistered_directory_under_the_worktree_root_refuses(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path)
    fake = target.parent / "ga-fake-slug"
    (fake / ACTIVE / "reports").mkdir(parents=True)
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, fake / ACTIVE / "reports/new.md"))
    assert refused(result)
    assert "coordination target invalid" in result.stderr


@pytest.mark.parametrize("place", ["canonical-root", "worktree-elsewhere", "source-file"])
def test_paths_outside_the_class_keep_todays_behaviour(tmp_path, place):
    """Not claimed: judged at the canonical seat, where readiness is BLOCKED by design."""

    canonical, target, _ = evidence_fixture(tmp_path)
    if place == "canonical-root":
        path = canonical / ACTIVE / "reports/new.md"
    elif place == "worktree-elsewhere":
        stray = tmp_path / "stray" / "ga-one-stray"
        git(canonical, "worktree", "add", "-qb", "codex/ga-one-stray", str(stray), "main")
        (stray / ACTIVE / "reports").mkdir(parents=True)
        path = stray / ACTIVE / "reports/new.md"
    else:
        path = target / "docs/evidence.md"
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, path))
    assert refused(result)
    assert read_gate_decisions(canonical)[-1]["reason"] == "readiness_blocked"
    assert not read_gate_decisions(target)


def test_without_the_opt_in_a_reports_write_keeps_todays_behaviour(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path, opted_in=False)
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, report(target, "new.md")))
    assert refused(result)
    assert read_gate_decisions(canonical)[-1]["reason"] == "readiness_blocked"


@pytest.mark.parametrize("tool", ["Edit", "MultiEdit", "NotebookEdit"])
def test_other_file_tools_keep_todays_behaviour(tmp_path, tool):
    canonical, target, _ = evidence_fixture(tmp_path)
    path = report(target, "existing.md")
    path.write_text("a\n")
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, path, tool=tool))
    assert refused(result)
    assert read_gate_decisions(canonical)[-1]["reason"] == "readiness_blocked"
    assert not read_gate_decisions(target)


def test_a_worktree_session_keeps_its_own_write_behaviour(tmp_path):
    """A Claude session inside <W> writes its reports exactly as before: no approval."""

    canonical, target, _ = evidence_fixture(tmp_path)
    request = write_payload(target, report(target, "own.md"))
    result = run_gate(PRETOOLUSE, target, request)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_an_advisory_seat_is_validated_and_audited_without_approval(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path)
    write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, report(target, "new.md")))
    assert result.returncode == 0, result.stderr
    assert '"permissionDecision"' not in result.stdout
    record = read_gate_decisions(target)[-1]
    assert record["verdict"] == "allow"
    assert record["reason"] == "advisory_evidence_write_no_native_approval"
    invalid = run_gate(PRETOOLUSE, canonical, write_payload(canonical, report(target, "CLAUDE.md")))
    assert refused(invalid)


def test_an_advisory_target_gets_no_native_approval(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path)
    write(target / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    result = run_gate(PRETOOLUSE, canonical, write_payload(canonical, report(target, "new.md")))
    assert result.returncode == 0, result.stderr
    assert '"permissionDecision"' not in result.stdout


# --- Degraded fallback ------------------------------------------------------------------


def test_the_degraded_fallback_hard_blocks_an_evidence_write(tmp_path, monkeypatch):
    from aegis_foundation.gate.hooks import evidence_write, pretool

    canonical, target, _ = evidence_fixture(tmp_path)
    write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    monkeypatch.setattr(pretool, "project_root", lambda: canonical)
    request = write_payload(canonical, report(target, "new.md"))
    assert pretool.degraded_pretooluse_fallback(request, RuntimeError("fault")) == 2

    def explode(*_args, **_kwargs):
        raise RuntimeError("detector failure")

    monkeypatch.setattr(evidence_write, "evidence_write_claim", explode)
    assert pretool.degraded_pretooluse_fallback(request, RuntimeError("fault")) == 2


# --- PostToolUse ------------------------------------------------------------------------


def _in_process(monkeypatch, canonical):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(canonical))
    monkeypatch.setenv("AEGIS_INVOKING_AGENT", "claude")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONPYCACHEPREFIX", os.devnull)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "pycache_prefix", os.devnull)


def test_posttool_takes_the_evidence_write_branch_not_delivery(tmp_path, monkeypatch):
    from aegis_foundation.gate.hooks import delivery, evidence_write, tracking

    canonical, target, _ = evidence_fixture(tmp_path)
    _in_process(monkeypatch, canonical)
    chosen = []

    def never(*_args, **_kwargs):
        raise AssertionError("an evidence write never reaches the delivery branch")

    real = evidence_write.record_evidence_write_event

    def recorded(worktree, payload):
        chosen.append(worktree)
        return real(worktree, payload)

    monkeypatch.setattr(delivery, "record_delivery_event", never)
    monkeypatch.setattr(evidence_write, "record_evidence_write_event", recorded)
    path = report(target, "branch.md")
    path.write_text("evidence\n")
    monkeypatch.setattr(sys, "stdin", io.StringIO(write_payload(canonical, path)))
    assert tracking.posttooluse_tracking() == 0
    assert chosen == [target]
    [pending] = json.loads((target / PENDING).read_text())["events"]
    assert pending["tool"] == "Write" and pending["kind"] == "mutation"


def _hardlink(path):
    os.link(path, path.with_name("twin.md"))


def _swap_symlink(path):
    real = path.with_name("real.md")
    path.rename(real)
    path.symlink_to(real)


@pytest.mark.parametrize(
    "damage",
    ["missing", "symlink", "hardlink", "oversized", "reports-symlink", "directory"],
)
def test_posttool_rechecks_the_written_file(tmp_path, damage):
    canonical, target, _ = evidence_fixture(tmp_path)
    path = report(target, "new.md")
    request = write_payload(canonical, path)
    assert approved(run_gate(PRETOOLUSE, canonical, request))
    path.write_text("evidence\n")
    if damage == "missing":
        path.unlink()
    elif damage == "symlink":
        _swap_symlink(path)
    elif damage == "hardlink":
        _hardlink(path)
    elif damage == "oversized":
        path.write_text("x" * (1024 * 1024 + 1))
    elif damage == "directory":
        path.unlink()
        path.mkdir()
    else:
        moved = target / "moved-reports"
        report(target).rename(moved)
        report(target).symlink_to(moved, target_is_directory=True)
    result = run_gate(POSTTOOLUSE, canonical, request)
    assert result.returncode == 2
    assert "stop and reconcile" in result.stderr
    assert not (target / PENDING).exists()
    assert read_gate_decisions(canonical)[-1]["reason"] == "coordination_target_invalid"


def test_the_must_not_exist_rule_is_not_rerun_after_the_write(tmp_path):
    canonical, target, _ = evidence_fixture(tmp_path)
    path = report(target, "sub", "deep.md")
    request = write_payload(canonical, path)
    assert approved(run_gate(PRETOOLUSE, canonical, request))
    path.parent.mkdir()
    path.write_text("evidence\n")
    assert run_gate(POSTTOOLUSE, canonical, request).returncode == 0
    [pending] = json.loads((target / PENDING).read_text())["events"]
    assert pending["evidence"] == f"{ACTIVE}/reports/sub/deep.md"


# --- Native permission unit -------------------------------------------------------------


def test_native_permission_never_approves_an_unclaimed_write(tmp_path, monkeypatch):
    from aegis_foundation.gate.hooks import native_permissions
    from aegis_foundation.gate.hooks.contracts import Payload

    canonical, target, _ = evidence_fixture(tmp_path)
    monkeypatch.setattr(native_permissions, "hook_invoking_agent", lambda _payload: "claude")
    for root, path in ((canonical, canonical / "notes.md"), (target, report(target, "x.md"))):
        payload = Payload("Write", {"file_path": str(path), "content": "x"}, cwd=str(root))
        assert native_permissions.native_permission(root, payload) is None
