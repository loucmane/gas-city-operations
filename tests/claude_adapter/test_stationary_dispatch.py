"""ga-fsfg R4: the gate side of `coordinate --action dispatch`.

For a dispatch the gate reads only local state: the closed form, the profile and the
target validation, whose one ownership exemption needs a verified `create` record in
`<W>`'s journal. It never reads the child, so a child the sling routed and a worker
claimed never fails the PostToolUse recheck, and the exact request of a pending
dispatch always reaches the executor.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_native_command_profile import PROFILE, event, git
from test_pretooluse_gates import POSTTOOLUSE, PRETOOLUSE, read_gate_decisions, run_gate, write
from test_stationary_orchestrator import (
    command,
    registered_fixture,
    review_only_fixture,
    stationary_fixture,
)

TARGET = "gascity/worker"
PREROUTE = "gascity/operations-candidate-worker"
CHILD = "ga-one.1"


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    monkeypatch.delenv("AEGIS_INVOKING_AGENT", raising=False)


def set_profile(repos, **changes):
    """Commit one profile change to the seat and every worktree that must agree with it."""

    value = json.loads((repos[0] / PROFILE).read_text())
    value.update(changes)
    value = {key: item for key, item in value.items() if item is not None}
    for repo in repos:
        write(repo / PROFILE, json.dumps(value))
        git(repo, "add", str(PROFILE))
        git(repo, "commit", "-qm", "dispatch profile")


def opt_in(repos, **changes):
    value = json.loads((repos[0] / PROFILE).read_text())
    fields = {
        "commands": [*value["commands"], "dispatch"],
        "dispatch_targets": [TARGET],
        "preroute_targets": [PREROUTE],
    }
    set_profile(repos, **{**fields, **changes})


def add_record(journal: Path, action: str, result_bead: str, *, state="verified", primary="ga-one"):
    data = json.loads(journal.read_text())
    request = {"bead_id": primary, "action": action, "fields": {"marker": result_bead}}
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    record = {"state": state, "request": request, "before": {"id": primary}, "blocker_before": None}
    if state == "verified":
        record.update(result_bead=result_bead, after={"id": result_bead})
    data.setdefault("coordination", {})[key] = record
    write(journal, json.dumps(data))


def dispatch_fixture(tmp_path):
    canonical, target, journal = stationary_fixture(tmp_path)
    opt_in([canonical, target])
    add_record(journal, "create", CHILD)
    return canonical, target, journal


def dispatch(canonical, target, bead=CHILD, agent=TARGET, extra=""):
    flags = f" --bead {bead} --action dispatch --target {agent}{extra}"
    return command(canonical, target, "coordinate", flags)


def approved(result) -> bool:
    if result.returncode != 0 or not result.stdout.strip():
        return False
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    return (
        decision["permissionDecision"] == "allow"
        and decision["permissionDecisionReason"] == "aegis-orchestrator:workflow-coordinate"
    )


def refused(result) -> bool:
    return result.returncode == 2 and '"permissionDecision": "allow"' not in result.stdout


def current_work(target):
    """In-progress Bead work bound to the fixture's real session and plan pointers."""

    write(
        target / ".aegis/state/current-work.json",
        json.dumps(
            {
                "schema_version": "1.0.0",
                "mode": "bead",
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
                    "work_tracking": next(
                        (target / "docs/ai/work-tracking/active").glob("*-ACTIVE")
                    ).relative_to(target).as_posix(),
                },
            }
        ),
    )


def test_dispatch_of_a_created_child_is_approved_as_workflow_coordinate(tmp_path):
    canonical, target, _ = dispatch_fixture(tmp_path)
    result = run_gate(PRETOOLUSE, canonical, event(canonical, dispatch(canonical, target)))
    assert approved(result), result.stderr
    assert not read_gate_decisions(canonical)
    assert read_gate_decisions(target)[-1]["reason"] == "native_permission:workflow-coordinate"


def _journal_edit(journal, change):
    data = json.loads(journal.read_text())
    change(data)
    write(journal, json.dumps(data))


REFUSALS = {
    "primary": ({"bead": "ga-one"}, None, "owned Bead or a malformed identity"),
    "no-create-record": ({"bead": "ga-one.2"}, None, "no verified create record"),
    "note-record": (
        {"bead": "ga-one.3"},
        lambda c, t, j: add_record(j, "note", "ga-one.3"),
        "no verified create record",
    ),
    "depend-record": (
        {"bead": "ga-one.4"},
        lambda c, t, j: add_record(j, "depend", "ga-one.4"),
        "no verified create record",
    ),
    "pending-create": (
        {"bead": "ga-one.5"},
        lambda c, t, j: add_record(j, "create", "ga-one.5", state="pending"),
        "no verified create record",
    ),
    "not-dotted": (
        {"bead": "ga-two.1"},
        lambda c, t, j: add_record(j, "create", "ga-two.1"),
        "not a dotted child",
    ),
    "malformed": ({"bead": "GA-ONE.1"}, None, "invalid coordination bead identity"),
    "inline-text": ({"bead": "'route this child'"}, None, "invalid coordination bead identity"),
    "unlisted-target": ({"agent": "gascity/other"}, None, "not listed in dispatch_targets"),
    "other-rig": ({"agent": "hpfetcher/worker"}, None, "not listed in dispatch_targets"),
    "preroute-target": (
        {"agent": PREROUTE},
        lambda c, t, j: set_profile([c, t], dispatch_targets=[TARGET, PREROUTE]),
        "reviewed window package",
    ),
    "missing-preroute": (
        {},
        lambda c, t, j: set_profile([c, t], preroute_targets=None),
        "requires dispatch_targets and preroute_targets",
    ),
    "empty-preroute": (
        {},
        lambda c, t, j: set_profile([c, t], preroute_targets=[]),
        "non-empty closed list",
    ),
    "lists-without-dispatch": (
        {},
        lambda c, t, j: set_profile(
            [c, t], commands=["project-context", "beads-read", "workflow-begin", "workflow-coordinate"]
        ),
        "require dispatch in commands",
    ),
    "no-dispatch": (
        {},
        lambda c, t, j: set_profile(
            [c, t],
            commands=["project-context", "beads-read", "workflow-begin", "workflow-coordinate"],
            dispatch_targets=None,
            preroute_targets=None,
        ),
        "not opted into",
    ),
    "target-form": ({"agent": "Gascity/Worker"}, None, "invalid dispatch target"),
    "extra-text": ({"extra": " --text evidence"}, None, "unrecognized ledger operation"),
    "target-twice": ({"extra": f" --target {TARGET}"}, None, "unrecognized coordination arguments"),
    "shell": ({"extra": " && touch marker"}, None, "single literal command"),
}


@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_dispatch_refusals(tmp_path, case):
    canonical, target, journal = dispatch_fixture(tmp_path)
    arguments, setup, detail = REFUSALS[case]
    if setup is not None:
        setup(canonical, target, journal)
    result = run_gate(PRETOOLUSE, canonical, event(canonical, dispatch(canonical, target, **arguments)))
    assert refused(result)
    assert detail in result.stderr


def test_an_attached_bead_is_never_dispatched(tmp_path):
    canonical, target, journal = dispatch_fixture(tmp_path)
    plan = (target / "plans/current").resolve()
    write(plan, plan.read_text() + "attached_bead_ids: [ga-two]\n")

    def attach(data):
        data["attached_bead_ids"] = ["ga-two"]
        data["external_ownership"]["ga-two"] = dict(data["external_ownership"]["ga-one"])

    _journal_edit(journal, attach)
    note = run_gate(
        PRETOOLUSE,
        canonical,
        event(canonical, command(canonical, target, "coordinate", " --bead ga-two --action note --text x")),
    )
    assert approved(note), note.stderr  # the attachment itself is valid
    result = run_gate(PRETOOLUSE, canonical, event(canonical, dispatch(canonical, target, bead="ga-two")))
    assert refused(result)
    assert "owned Bead or a malformed identity" in result.stderr


@pytest.mark.parametrize(
    "flags",
    [
        f" --bead {CHILD} --action note --text evidence",
        f" --bead {CHILD} --action create --title t --description d --acceptance a",
        f" --bead {CHILD} --action depend --blocker ga-two",
        f" --bead ga-one --action note --text evidence --target {TARGET}",
    ],
)
def test_the_exemption_opens_no_other_action_on_the_unowned_child(tmp_path, flags):
    canonical, target, _ = dispatch_fixture(tmp_path)
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target, "coordinate", flags)))
    assert refused(result)


@pytest.mark.parametrize("mode", ["plan", "unknown", None])
def test_dispatch_requires_a_known_non_plan_mode(tmp_path, mode):
    canonical, target, _ = dispatch_fixture(tmp_path)
    request = event(canonical, dispatch(canonical, target), permission_mode=mode)
    assert refused(run_gate(PRETOOLUSE, canonical, request))


def test_a_registered_project_worktree_refuses_dispatch(tmp_path):
    canonical, target, _, core_target, core_journal = registered_fixture(tmp_path)
    opt_in([canonical, target])
    add_record(core_journal, "create", "ga-core.1", primary="ga-core")
    result = run_gate(
        PRETOOLUSE, canonical, event(canonical, dispatch(canonical, core_target, bead="ga-core.1"))
    )
    assert refused(result)
    assert "dispatch requires an Operations worktree" in result.stderr


def test_a_review_project_worktree_refuses_dispatch(tmp_path):
    canonical, _, core_target, _ = review_only_fixture(tmp_path)
    opt_in([canonical])
    result = run_gate(
        PRETOOLUSE, canonical, event(canonical, dispatch(canonical, core_target, bead="ga-core.1"))
    )
    assert refused(result)
    assert "coordination target must be a direct registered linked worktree" in result.stderr


def test_advisory_seat_dispatch_is_audited_without_a_native_approval(tmp_path):
    canonical, target, _ = dispatch_fixture(tmp_path)
    write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    result = run_gate(PRETOOLUSE, canonical, event(canonical, dispatch(canonical, target)))
    assert result.returncode == 0, result.stderr
    assert '"permissionDecision"' not in result.stdout
    assert read_gate_decisions(target)[-1]["reason"] == "advisory_coordination_no_native_approval"


def test_degraded_fallback_hard_blocks_dispatch(tmp_path, monkeypatch):
    from aegis_foundation.gate.hooks import pretool

    canonical, target, _ = dispatch_fixture(tmp_path)
    write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    monkeypatch.setattr(pretool, "project_root", lambda: canonical)
    request = event(canonical, dispatch(canonical, target))
    assert pretool.degraded_pretooluse_fallback(request, RuntimeError("fault")) == 2


def pending_dispatch(journal: Path) -> None:
    """The intent the executor writes before its sling, as it would store it."""

    request = {"bead_id": CHILD, "action": "dispatch", "fields": {"target": TARGET}}
    encoded = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    data = json.loads(journal.read_text())
    data.setdefault("coordination", {})[hashlib.sha256(encoded.encode()).hexdigest()] = {
        "state": "pending",
        "request": request,
        "before": {"id": CHILD, "status": "open", "metadata": {}},
        "blocker_before": None,
        "last_sling_at": "2030-01-01T12:00:00.000000Z",
    }
    write(journal, json.dumps(data))


def test_hook_level_dispatch_event_log_and_completion(tmp_path):
    """The child is routed and claimed after the sling; the gate never looks at it."""

    canonical, target, journal = dispatch_fixture(tmp_path)
    current_work(target)
    request = event(canonical, dispatch(canonical, target))
    assert approved(run_gate(PRETOOLUSE, canonical, request))

    # The executor recorded the intent; its sling timed out after the child was routed
    # and a worker claimed it. None of that is local state the gate reads.
    pending_dispatch(journal)
    assert run_gate(POSTTOOLUSE, canonical, request).returncode == 0
    events = json.loads((target / ".aegis/state/pending-tracking.json").read_text())["events"]
    assert len(events) == 1 and not (canonical / ".aegis/state/pending-tracking.json").exists()

    # The re-request waits for the event; log --pending-id discharges it first.
    assert refused(run_gate(PRETOOLUSE, canonical, request))
    pending = events[0]["id"]
    log_request = event(
        canonical, command(canonical, target, "log", f" --pending-id {pending} --note recorded")
    )
    assert approved(run_gate(PRETOOLUSE, canonical, log_request))
    # The executor's log runs the canonical Aegis CLI for exactly this event.
    active = next((target / "docs/ai/work-tracking/active").glob("*-ACTIVE"))
    for name in ("IMPLEMENTATION.md", "CHANGELOG.md", "HANDOFF.md", "FINDINGS.md", "DECISIONS.md"):
        write(active / name, f"# {name}\n\n## Progress Log\n")
    discharged = subprocess.run(
        [
            sys.executable,
            "-m",
            "aegis_foundation.cli",
            "log",
            "--target-dir",
            str(target),
            "--pending-id",
            pending,
            "--note",
            "Recorded the dispatch call",
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert discharged.returncode == 0, discharged.stderr
    queue = target / ".aegis/state/pending-tracking.json"
    assert not queue.exists() or not json.loads(queue.read_text()).get("events")
    assert run_gate(POSTTOOLUSE, canonical, log_request).returncode == 0

    # The exact request of the pending dispatch passes the gate and reaches the executor.
    assert approved(run_gate(PRETOOLUSE, canonical, request))
    note = event(
        canonical,
        command(canonical, target, "coordinate", " --bead ga-one --action note --text routed"),
    )
    assert approved(run_gate(PRETOOLUSE, canonical, note))


def test_the_gate_never_runs_a_gc_read_for_dispatch(tmp_path, monkeypatch, capsys):
    """In-process PreToolUse and PostToolUse with every subprocess recorded."""

    from aegis_foundation.gate.hooks import tracking
    from aegis_foundation.gate.hooks.pretool import pretooluse_gate_with_degraded_fallback

    canonical, target, journal = dispatch_fixture(tmp_path)
    current_work(target)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(canonical))
    monkeypatch.setenv("AEGIS_INVOKING_AGENT", "claude")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONPYCACHEPREFIX", os.devnull)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "pycache_prefix", os.devnull)
    calls = []
    real = subprocess.run

    def recording(argv, *args, **kwargs):
        calls.append([str(item) for item in argv])
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", recording)
    request = event(canonical, dispatch(canonical, target))
    capsys.readouterr()
    assert pretooluse_gate_with_degraded_fallback(request) == 0
    assert '"permissionDecision": "allow"' in capsys.readouterr().out
    pending_dispatch(journal)
    monkeypatch.setattr(sys, "stdin", io.StringIO(request))
    assert tracking.posttooluse_tracking() == 0
    assert calls, "the recorder saw the gate's own Git reads"
    assert not [argv for argv in calls if Path(argv[0]).name in {"gc", "bd"} or "sling" in argv]


# --- Profile validation ---------------------------------------------------------------


def _profile(**changes):
    value = {
        "rig": "gascity",
        "commands": ["workflow-coordinate", "dispatch"],
        "dispatch_targets": [TARGET],
        "preroute_targets": [PREROUTE],
    }
    value.update(changes)
    return {key: item for key, item in value.items() if item is not None}


@pytest.mark.parametrize(
    "changes,detail",
    [
        ({"commands": ["workflow-coordinate"]}, "require dispatch in commands"),
        ({"commands": ["workflow-coordinate"], "dispatch_targets": None}, "require dispatch in commands"),
        ({"dispatch_targets": None}, "requires dispatch_targets and preroute_targets"),
        ({"preroute_targets": None}, "requires dispatch_targets and preroute_targets"),
        ({"commands": ["dispatch"]}, "requires workflow-coordinate"),
        ({"dispatch_targets": []}, "non-empty closed list"),
        ({"preroute_targets": []}, "non-empty closed list"),
        ({"dispatch_targets": "gascity/worker"}, "non-empty closed list"),
        ({"dispatch_targets": [TARGET, TARGET]}, "non-empty closed list"),
        ({"dispatch_targets": [f"gascity/w{index}" for index in range(17)]}, "non-empty closed list"),
        ({"dispatch_targets": ["gascity/Worker"]}, "non-empty closed list"),
        ({"dispatch_targets": ["gascity"]}, "non-empty closed list"),
        ({"preroute_targets": ["gascity/a/b"]}, "non-empty closed list"),
        ({"dispatch_targets": ["hpfetcher/worker"]}, "agent of the profile rig"),
    ],
)
def test_dispatch_profile_fields_are_closed(changes, detail):
    from aegis_foundation.gate.hooks.native_permissions import validate_dispatch_profile

    with pytest.raises(ValueError, match=detail):
        validate_dispatch_profile(_profile(**changes))


def test_dispatch_profile_fields_accept_the_documented_shape():
    from aegis_foundation.gate.hooks.native_permissions import (
        COMMANDS,
        validate_dispatch_profile,
    )

    assert {"dispatch", "evidence-write"} <= COMMANDS
    validate_dispatch_profile(_profile())
    validate_dispatch_profile(_profile(preroute_targets=["other-rig/lane"]))
    validate_dispatch_profile(
        _profile(commands=["workflow-coordinate"], dispatch_targets=None, preroute_targets=None)
    )
    validate_dispatch_profile(_profile(dispatch_targets=["gascity/gc.implementation-worker"]))
