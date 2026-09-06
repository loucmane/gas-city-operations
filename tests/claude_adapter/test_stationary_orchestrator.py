"""A canonical conversation coordinates exact worktrees, never arbitrary roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from test_native_command_profile import PROFILE, WORKFLOW_REL, event, git, profile
from test_pretooluse_gates import PRETOOLUSE, read_gate_decisions, run, run_gate, write
from test_readiness_gate import make_bead_source_repo


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    monkeypatch.delenv("AEGIS_INVOKING_AGENT", raising=False)


def stationary_fixture(tmp_path: Path, bead: str = "ga-one"):
    canonical = make_bead_source_repo(tmp_path, bead_id=bead)
    git(canonical, "config", "user.name", "Test")
    git(canonical, "config", "user.email", "test@example.invalid")
    git(canonical, "remote", "add", "origin", "git@github.com:example/fixture-project.git")
    write(canonical / ".gitignore", ".aegis/\n")
    descriptor = {
        "schema": "gas-city-workflow.project.v1",
        "id": "fixture-project",
        "repository": "example/fixture-project",
        "rig": "gascity",
        "workflow_authority": "beads",
        "workflow_profile": "beads-with-aegis-evidence",
    }
    write(canonical / ".gas-city-workflow.json", json.dumps(descriptor))
    value = profile(canonical)
    value["commands"].append("workflow-coordinate")
    write(canonical / PROFILE, json.dumps(value))
    write(canonical / WORKFLOW_REL, "# synthetic runtime, not executed by gate\n")
    git(canonical, "add", ".")
    git(canonical, "commit", "-qm", "fixture")
    base = run(["git", "rev-parse", "HEAD"], canonical).stdout.strip()
    branch = f"codex/{bead}-beads-first-guidance"
    git(canonical, "checkout", "-qb", "main")
    target = canonical.parent / (canonical.name + "-worktrees") / f"{bead}-beads-first-guidance"
    git(canonical, "worktree", "add", "-q", str(target), branch)
    spec = {
        "project_id": "fixture-project",
        "rig": "gascity",
        "workflow_profile": "beads-with-aegis-evidence",
        "canonical_root": str(canonical),
        "worktree_root": str(target.parent),
        "worktree": str(target),
        "bead_id": bead,
        "branch": branch,
        "base_commit": base,
        "title": "Fixture",
        "slug": "beads-first-guidance",
    }

    def canonical_json(obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    owner = {
        "schema": "gas-city-workflow.external-owner.v1",
        "kind": "external-coordinator",
        "project": "fixture-project",
        "city": "/home/loucmane/gascity/city",
        "rig": "gascity",
        "canonical_root": str(canonical),
        "worktree": str(target),
        "branch": branch,
        "primary_bead": bead,
        "transaction_sha256": hashlib.sha256(canonical_json(spec).encode()).hexdigest(),
    }
    binding = (
        "external-coordinator.v1:" + hashlib.sha256(canonical_json(owner).encode()).hexdigest()
    )
    journal = {
        "schema": "gas-city-workflow.transition.v1",
        "phase": "ready",
        "spec": spec,
        "history": [],
        "external_ownership": {bead: {"state": "verified", "binding": binding}},
    }
    path = canonical / ".git/gas-city-workflow/transactions" / f"{bead}.json"
    write(path, json.dumps(journal))
    return canonical, target, path


def command(canonical, target, verb="checkpoint", flags=""):
    return f"python3 {canonical / WORKFLOW_REL} {verb} --root {target}{flags}"


@pytest.mark.parametrize(
    "verb,flags",
    [
        ("checkpoint", ""),
        ("verify", ""),
        ("attach", " --bead ga-two"),
        ("coordinate", " --bead ga-one --action note --text evidence"),
        (
            "coordinate",
            " --bead ga-one --action create --title repair --description scope --acceptance proof",
        ),
        ("coordinate", " --bead ga-one --action depend --blocker ga-two"),
        ("log", " --evidence test-proof --note verified"),
    ],
)
def test_canonical_session_can_coordinate_ready_target(tmp_path, verb, flags):
    canonical, target, _ = stationary_fixture(tmp_path)
    result = run_gate(
        PRETOOLUSE, canonical, event(canonical, command(canonical, target, verb, flags))
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert not read_gate_decisions(canonical)
    assert read_gate_decisions(target)[-1]["reason"] == "native_permission:workflow-coordinate"


@pytest.mark.parametrize(
    "defect",
    [
        "foreign",
        "symlink",
        "journal",
        "ownership",
        "branch",
        "descriptor",
        "profile",
        "runtime",
        "unready",
    ],
)
def test_target_must_be_fully_bound(tmp_path, defect):
    canonical, target, path = stationary_fixture(tmp_path)
    if defect == "foreign":
        target = tmp_path / "other"
    elif defect == "symlink":
        alias = target.parent / "alias"
        alias.symlink_to(target, target_is_directory=True)
        target = alias
    elif defect in {"journal", "ownership"}:
        value = json.loads(path.read_text())
        if defect == "journal":
            value["spec"]["worktree"] = str(canonical)
        else:
            value["external_ownership"]["ga-one"]["binding"] = "forged"
        write(path, json.dumps(value))
    elif defect == "branch":
        git(target, "checkout", "-qb", "codex/ga-other")
    elif defect == "unready":
        (target / "plans/current").unlink()
    elif defect == "runtime":
        write(canonical / WORKFLOW_REL, "# unreviewed\n")
    else:
        write(target / (PROFILE if defect == "profile" else ".gas-city-workflow.json"), "{}")
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target)))
    assert result.returncode == 2
    assert '"permissionDecision": "allow"' not in result.stdout


@pytest.mark.parametrize(
    "suffix",
    [
        " --root /tmp",
        " --registry /tmp/registry",
        " --force",
        " && touch marker",
        " > marker",
        " --bead ga-other",
    ],
)
def test_closed_grammar_refuses_additional_authority(tmp_path, suffix):
    canonical, target, _ = stationary_fixture(tmp_path)
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target) + suffix))
    assert result.returncode == 2


@pytest.mark.parametrize("mode", ["plan", "unknown", None])
def test_mutation_requires_known_non_plan_mode(tmp_path, mode):
    canonical, target, _ = stationary_fixture(tmp_path)
    result = run_gate(
        PRETOOLUSE, canonical, event(canonical, command(canonical, target), permission_mode=mode)
    )
    assert result.returncode == 2


@pytest.mark.parametrize("scope", ["canonical", "target"])
@pytest.mark.parametrize("boundary", ["pending", "observation", "advisory"])
def test_both_seat_and_target_constraints_remain(tmp_path, scope, boundary):
    canonical, target, _ = stationary_fixture(tmp_path)
    root = canonical if scope == "canonical" else target
    if boundary == "pending":
        write(
            root / ".aegis/state/pending-tracking.json",
            json.dumps({"events": [{"id": "pending", "status": "pending", "required": True}]}),
        )
    elif boundary == "observation":
        write(
            root / ".aegis/state/current-work.json",
            '{"kind":"observation","mode":"observation","status":"in-progress"}',
        )
    else:
        write(root / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target)))
    assert result.returncode == 2


def test_raw_ledger_and_source_writes_stay_blocked(tmp_path):
    canonical, target, _ = stationary_fixture(tmp_path)
    for cmd in [
        "touch marker",
        "/home/loucmane/gascity/bin/gc --city /home/loucmane/gascity/city --rig gascity bd create unsafe",
    ]:
        assert run_gate(PRETOOLUSE, canonical, event(canonical, cmd)).returncode == 2


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/_source_workflow_state.py",
        ".claude/scripts/readiness.sh",
        "aegis_foundation/unreviewed.py",
        ".aegis/bin/aegis",
    ],
)
def test_target_helpers_cannot_execute_before_approval(tmp_path, relative):
    canonical, target, _ = stationary_fixture(tmp_path)
    marker = tmp_path / "executed-unreviewed-code"
    write(
        target / relative, f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\n"
    )
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target)))
    assert result.returncode == 2
    assert not marker.exists()


def test_ordinary_candidate_source_remains_editable_by_the_worker(tmp_path):
    canonical, target, _ = stationary_fixture(tmp_path)
    write(target / "src/feature.py", "candidate = True\n")
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target)))
    assert result.returncode == 0, result.stderr


def test_two_targets_from_one_unchanged_seat(tmp_path):
    import shutil

    canonical, one, journal_path = stationary_fixture(tmp_path)
    template_root = tmp_path / "second"
    template_root.mkdir()
    template = make_bead_source_repo(template_root, bead_id="ga-two")
    two = one.parent / "ga-two-beads-first-guidance"
    git(canonical, "worktree", "add", "-qb", "codex/ga-two-beads-first-guidance", str(two), "main")
    for relative in ("plans", "sessions", "docs"):
        shutil.rmtree(two / relative)
        shutil.copytree(template / relative, two / relative, symlinks=True)
    value = json.loads(journal_path.read_text())
    value["spec"].update(
        bead_id="ga-two", worktree=str(two), branch="codex/ga-two-beads-first-guidance"
    )
    spec = value["spec"]

    def encoded(obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    owner = {
        "schema": "gas-city-workflow.external-owner.v1",
        "kind": "external-coordinator",
        "project": spec["project_id"],
        "city": "/home/loucmane/gascity/city",
        "rig": "gascity",
        "canonical_root": str(canonical),
        "worktree": str(two),
        "branch": spec["branch"],
        "primary_bead": "ga-two",
        "transaction_sha256": hashlib.sha256(encoded(spec).encode()).hexdigest(),
    }
    binding = "external-coordinator.v1:" + hashlib.sha256(encoded(owner).encode()).hexdigest()
    value["external_ownership"] = {"ga-two": {"state": "verified", "binding": binding}}
    write(journal_path.with_name("ga-two.json"), json.dumps(value))
    before = run(["git", "status", "--porcelain"], canonical).stdout
    for target in (one, two, one):
        result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target)))
        assert result.returncode == 0, result.stderr
        assert '"permissionDecision": "allow"' in result.stdout
    assert run(["git", "branch", "--show-current"], canonical).stdout.strip() == "main"
    assert run(["git", "status", "--porcelain"], canonical).stdout == before
    assert len(read_gate_decisions(one)) == 2
    assert len(read_gate_decisions(two)) == 1


def test_degraded_advisory_cannot_bypass_target_validation(tmp_path, monkeypatch):
    from aegis_foundation.gate.hooks import pretool

    canonical, target, _ = stationary_fixture(tmp_path)
    write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    monkeypatch.setattr(pretool, "project_root", lambda: canonical)
    assert (
        pretool.degraded_pretooluse_fallback(
            event(canonical, command(canonical, target)), RuntimeError("fault")
        )
        == 2
    )


def test_posttool_tracking_belongs_to_target_and_log_is_reachable(tmp_path):
    from test_pretooluse_gates import POSTTOOLUSE

    canonical, target, _ = stationary_fixture(tmp_path)
    # Logging authority must bind the real fixture pointers, not merely a Bead ID.
    write(
        target / ".aegis/state/current-work.json",
        json.dumps({
            "schema_version": "1.0.0", "mode": "bead", "status": "in-progress",
            "task": {"id": "ga-one", "slug": "beads-first-guidance",
                     "source": "gas-city-bead", "status": "in-progress"},
            "branch": {"current": "codex/ga-one-beads-first-guidance"},
            "paths": {
                "session": (target / "sessions/current").resolve().relative_to(target).as_posix(),
                "plan": (target / "plans/current").resolve().relative_to(target).as_posix(),
            },
        }),
    )
    request = event(canonical, command(canonical, target))
    preflight = run_gate(PRETOOLUSE, canonical, request)
    assert preflight.returncode == 0, preflight.stderr
    assert run_gate(POSTTOOLUSE, canonical, request).returncode == 0
    assert (target / ".aegis/state/pending-tracking.json").is_file()
    assert not (canonical / ".aegis/state/pending-tracking.json").exists()
    log_request = event(
        canonical, command(canonical, target, "log", " --evidence proof --note checked")
    )
    result = run_gate(PRETOOLUSE, canonical, log_request)
    assert result.returncode == 0, result.stderr


def test_exact_pending_id_log_is_reachable_only_for_selected_target_event(tmp_path):
    from test_pretooluse_gates import POSTTOOLUSE

    canonical, target, _ = stationary_fixture(tmp_path)
    pending_id = "0123456789ab"
    write(
        target / ".aegis/state/pending-tracking.json",
        json.dumps(
            {
                "events": [
                    {
                        "id": pending_id,
                        "mode": "strict",
                        "task": {"id": "ga-one", "slug": "beads-first-guidance"},
                    }
                ]
            }
        ),
    )
    request = event(
        canonical,
        command(canonical, target, "log", f" --pending-id {pending_id} --note recorded"),
    )
    result = run_gate(PRETOOLUSE, canonical, request)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    (target / ".aegis/state/pending-tracking.json").unlink()
    assert run_gate(POSTTOOLUSE, canonical, request).returncode == 0
    assert not (canonical / ".aegis/state/pending-tracking.json").exists()


def test_exact_pending_id_log_posttool_refuses_unresolved_target_event(tmp_path):
    from test_pretooluse_gates import POSTTOOLUSE

    canonical, target, _ = stationary_fixture(tmp_path)
    pending_id = "0123456789ab"
    write(
        target / ".aegis/state/pending-tracking.json",
        json.dumps(
            {
                "events": [
                    {
                        "id": pending_id,
                        "mode": "strict",
                        "task": {"id": "ga-one", "slug": "beads-first-guidance"},
                    }
                ]
            }
        ),
    )
    request = event(
        canonical,
        command(canonical, target, "log", f" --pending-id {pending_id} --note recorded"),
    )
    assert run_gate(PRETOOLUSE, canonical, request).returncode == 0
    result = run_gate(POSTTOOLUSE, canonical, request)
    assert result.returncode == 2
    assert "stop and reconcile" in result.stderr


@pytest.mark.parametrize(
    "flags",
    [
        " --pending-id current --note recorded",
        " --pending-id latest --note recorded",
        " --pending-id abcdefabcdef --note recorded",
        " --pending-id 0123456789ab --evidence proof --note recorded",
        " --pending-id 0123456789ab",
        " --pending-id 0123456789ab --pending-id 0123456789ab --note recorded",
        " --note recorded",
    ],
)
def test_pending_id_log_closed_grammar_refuses_ambiguous_or_wrong_requests(tmp_path, flags):
    canonical, target, _ = stationary_fixture(tmp_path)
    write(
        target / ".aegis/state/pending-tracking.json",
        json.dumps(
            {
                "events": [
                    {
                        "id": "0123456789ab",
                        "mode": "strict",
                        "task": {"id": "ga-one", "slug": "beads-first-guidance"},
                    }
                ]
            }
        ),
    )
    result = run_gate(
        PRETOOLUSE, canonical, event(canonical, command(canonical, target, "log", flags))
    )
    assert result.returncode == 2
    assert '"permissionDecision": "allow"' not in result.stdout


def test_target_pending_log_does_not_bypass_canonical_pending_tracking(tmp_path):
    canonical, target, _ = stationary_fixture(tmp_path)
    pending_id = "0123456789ab"
    event_payload = {
        "events": [
            {
                "id": pending_id,
                "mode": "strict",
                "task": {"id": "ga-one", "slug": "beads-first-guidance"},
            }
        ]
    }
    write(target / ".aegis/state/pending-tracking.json", json.dumps(event_payload))
    write(canonical / ".aegis/state/pending-tracking.json", json.dumps(event_payload))
    result = run_gate(
        PRETOOLUSE,
        canonical,
        event(
            canonical,
            command(canonical, target, "log", f" --pending-id {pending_id} --note recorded"),
        ),
    )
    assert result.returncode == 2


def test_posttool_target_drift_is_visible_not_silent_success(tmp_path):
    from test_pretooluse_gates import POSTTOOLUSE

    canonical, target, journal = stationary_fixture(tmp_path)
    request = event(canonical, command(canonical, target))
    assert run_gate(PRETOOLUSE, canonical, request).returncode == 0
    journal.unlink()
    result = run_gate(POSTTOOLUSE, canonical, request)
    assert result.returncode == 2
    assert "stop and reconcile" in result.stderr
    assert read_gate_decisions(canonical)[-1]["reason"] == "coordination_target_invalid"
    assert not (canonical / ".aegis/state/pending-tracking.json").exists()
