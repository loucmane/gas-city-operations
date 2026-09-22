"""A canonical conversation coordinates exact worktrees, never arbitrary roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aegis_foundation.gate.hooks.contracts import AEGIS_DEGRADED_EVENTS_REL
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
@pytest.mark.parametrize("boundary", ["pending", "observation"])
def test_both_seat_and_target_constraints_remain(tmp_path, scope, boundary):
    canonical, target, _ = stationary_fixture(tmp_path)
    root = canonical if scope == "canonical" else target
    if boundary == "pending":
        write(
            root / ".aegis/state/pending-tracking.json",
            json.dumps({"events": [{"id": "pending", "status": "pending", "required": True}]}),
        )
    else:
        write(
            root / ".aegis/state/current-work.json",
            '{"kind":"observation","mode":"observation","status":"in-progress"}',
        )
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target)))
    assert result.returncode == 2


@pytest.mark.parametrize("scope", ["canonical", "target"])
def test_advisory_enforcement_coordinates_without_a_native_approval(tmp_path, scope):
    """ga-fsfg R2: advisory relaxes ceremony, never issues the audited native approval."""

    canonical, target, _ = stationary_fixture(tmp_path)
    root = canonical if scope == "canonical" else target
    write(root / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target)))
    assert result.returncode == 0, result.stderr
    assert '"permissionDecision"' not in result.stdout
    assert not read_gate_decisions(canonical)
    # The target keeps the audit record either way; an advisory seat names its reason.
    record = read_gate_decisions(target)[-1]
    assert record["verdict"] == "allow"
    if scope == "canonical":
        assert record["reason"] == "advisory_coordination_no_native_approval"


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


REGISTRY_REL = "plugins/gas-city-workflow/config/projects.json"
CORE_LAYOUT = (
    "[repo_structure]\n"
    'sessions_root = "engdocs/workflow/sessions"\n'
    'plans_root = "engdocs/workflow/plans"\n'
    'plan_state_dir = "engdocs/workflow/plan-state"\n'
    'work_tracking_root = "engdocs/workflow/work-tracking"\n'
)


def registered_fixture(tmp_path: Path, *, layout: str = "default"):
    """Operations seat plus a registered foreign project with its own worktree and journal."""

    import shutil

    canonical, target, _ = stationary_fixture(tmp_path)
    core_parent = tmp_path / "core-project"
    core_parent.mkdir()
    core = make_bead_source_repo(core_parent, bead_id="ga-core")
    git(core, "config", "user.name", "Test")
    git(core, "config", "user.email", "test@example.invalid")
    git(core, "remote", "add", "origin", "git@github.com:example/core-project.git")
    # A registered project never carries the Operations runtime; drop the source
    # markers the readiness fixture plants for Aegis source checkouts.
    for relative in ("aegis_foundation", ".claude", "schemas", "scripts", "pyproject.toml"):
        entry = core / relative
        if entry.is_dir():
            shutil.rmtree(entry)
        elif entry.exists():
            entry.unlink()
    if layout == "engdocs":
        (core / "engdocs/workflow").mkdir(parents=True)
        shutil.move(str(core / "sessions"), str(core / "engdocs/workflow/sessions"))
        shutil.move(str(core / "plans"), str(core / "engdocs/workflow/plans"))
        shutil.move(str(core / "docs/ai/work-tracking"), str(core / "engdocs/workflow/work-tracking"))
        write(core / ".codex/config.toml", CORE_LAYOUT)
    write(core / ".gitignore", ".aegis/\n")
    git(core, "add", "-A")
    git(core, "commit", "-qm", "core fixture")
    base = run(["git", "rev-parse", "HEAD"], core).stdout.strip()
    branch = "codex/ga-core-beads-first-guidance"
    git(core, "checkout", "-qb", "main")
    core_target = core.parent / (core.name + "-worktrees") / "ga-core-beads-first-guidance"
    git(core, "worktree", "add", "-q", str(core_target), branch)
    spec = {
        "project_id": "core-project",
        "rig": "gascity",
        "workflow_profile": "beads-with-aegis-evidence",
        "canonical_root": str(core),
        "worktree_root": str(core_target.parent),
        "worktree": str(core_target),
        "bead_id": "ga-core",
        "branch": branch,
        "base_commit": base,
        "title": "Core fixture",
        "slug": "beads-first-guidance",
    }

    def canonical_json(obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    owner = {
        "schema": "gas-city-workflow.external-owner.v1",
        "kind": "external-coordinator",
        "project": "core-project",
        "city": "/home/loucmane/gascity/city",
        "rig": "gascity",
        "canonical_root": str(core),
        "worktree": str(core_target),
        "branch": branch,
        "primary_bead": "ga-core",
        "transaction_sha256": hashlib.sha256(canonical_json(spec).encode()).hexdigest(),
    }
    binding = "external-coordinator.v1:" + hashlib.sha256(canonical_json(owner).encode()).hexdigest()
    journal = {
        "schema": "gas-city-workflow.transition.v1",
        "phase": "ready",
        "spec": spec,
        "history": [],
        "external_ownership": {"ga-core": {"state": "verified", "binding": binding}},
    }
    core_journal = core / ".git/gas-city-workflow/transactions/ga-core.json"
    write(core_journal, json.dumps(journal))
    registry = {
        "schema": "gas-city-workflow.project-registry.v1",
        "projects": [
            {
                "id": "fixture-project",
                "root": str(canonical),
                "worktree_root": str(target.parent),
                "repository": "example/fixture-project",
                "rig": "gascity",
                "workflow_authority": "beads",
                "workflow_profile": "beads-with-aegis-evidence",
            },
            {
                "id": "core-project",
                "root": str(core),
                "worktree_root": str(core_target.parent),
                "repository": "example/core-project",
                "rig": "gascity",
                "workflow_authority": "beads",
                "workflow_profile": "beads-with-aegis-evidence",
            },
        ],
    }
    value = profile(canonical)
    value["commands"].append("workflow-coordinate")
    value["registered_projects"] = [
        {
            "id": "core-project",
            "repository": "example/core-project",
            "canonical_root": str(core),
            "worktree_root": str(core_target.parent),
            "rig": "gascity",
        }
    ]
    for repo in (canonical, target):
        write(repo / REGISTRY_REL, json.dumps(registry))
        write(repo / PROFILE, json.dumps(value))
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "register core project")
    return canonical, target, core, core_target, core_journal


@pytest.mark.parametrize(
    "verb,flags",
    [
        ("checkpoint", ""),
        ("verify", ""),
        ("publish", ""),
        ("compact-journal", ""),
        ("log", " --evidence README.md --note recorded"),
    ],
)
def test_registered_target_is_coordinated_from_the_canonical_seat(tmp_path, verb, flags):
    """ga-fsfg R2: a registered foreign worktree is a valid stationary target."""

    canonical, _, _, core_target, _ = registered_fixture(tmp_path)
    result = run_gate(
        PRETOOLUSE, canonical, event(canonical, command(canonical, core_target, verb, flags))
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert not read_gate_decisions(canonical)
    assert read_gate_decisions(core_target)[-1]["reason"] == "native_permission:workflow-coordinate"


def test_registered_target_with_layout_override_is_coordinated(tmp_path):
    canonical, _, _, core_target, _ = registered_fixture(tmp_path, layout="engdocs")
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, core_target)))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"


@pytest.mark.parametrize(
    "defect",
    [
        "unregistered-parent",
        "registry-mismatch",
        "profile-mismatch",
        "journal-identity",
        "runtime-shadow",
        "startup-hook",
        "observation",
    ],
)
def test_registered_target_must_be_fully_bound(tmp_path, defect):
    canonical, _, core, core_target, journal = registered_fixture(tmp_path)
    if defect == "unregistered-parent":
        stray = tmp_path / "stray-worktrees" / "ga-core-beads-first-guidance"
        git(core, "worktree", "add", "-qb", "codex/ga-core-stray", str(stray), "main")
        core_target = stray
    elif defect == "registry-mismatch":
        registry = json.loads((canonical / REGISTRY_REL).read_text())
        registry["projects"][1]["rig"] = "other"
        write(canonical / REGISTRY_REL, json.dumps(registry))
        git(canonical, "commit", "-qam", "registry drift")
    elif defect == "profile-mismatch":
        value = json.loads((canonical / PROFILE).read_text())
        value["registered_projects"][0]["repository"] = "example/other"
        write(canonical / PROFILE, json.dumps(value))
        git(canonical, "commit", "-qam", "profile drift")
    elif defect == "journal-identity":
        value = json.loads(journal.read_text())
        value["spec"]["canonical_root"] = str(canonical)
        write(journal, json.dumps(value))
    elif defect == "runtime-shadow":
        write(core_target / "aegis_foundation/gate/hooks/pretool.py", "# shadow\n")
    elif defect == "startup-hook":
        write(core_target / "sitecustomize.py", "import os\n")
    else:
        write(
            core_target / ".aegis/state/current-work.json",
            '{"kind":"observation","mode":"observation","status":"in-progress"}',
        )
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, core_target)))
    assert result.returncode == 2
    assert '"permissionDecision": "allow"' not in result.stdout


def test_registered_target_readiness_uses_portable_scaffold_checks(tmp_path):
    import shutil

    canonical, _, _, core_target, _ = registered_fixture(tmp_path)
    ok = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, core_target, "verify")))
    assert ok.returncode == 0, ok.stderr
    shutil.rmtree(core_target / "docs/ai/work-tracking/active")
    broken = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, core_target, "verify")))
    assert broken.returncode == 2
    assert "BLOCKED |" in broken.stderr
    assert '"permissionDecision": "allow"' not in broken.stdout


def test_registered_target_posttool_records_nothing_without_current_work(tmp_path):
    from test_pretooluse_gates import POSTTOOLUSE

    canonical, _, _, core_target, _ = registered_fixture(tmp_path)
    request = event(canonical, command(canonical, core_target, "checkpoint"))
    assert run_gate(PRETOOLUSE, canonical, request).returncode == 0
    assert run_gate(POSTTOOLUSE, canonical, request).returncode == 0
    assert not (core_target / ".aegis/state/pending-tracking.json").exists()
    assert not (canonical / ".aegis/state/pending-tracking.json").exists()


def test_advisory_seat_coordinates_registered_target_without_native_approval(tmp_path):
    canonical, _, _, core_target, _ = registered_fixture(tmp_path)
    write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    result = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, core_target, "verify")))
    assert result.returncode == 0, result.stderr
    assert '"permissionDecision"' not in result.stdout
    assert not read_gate_decisions(canonical)
    record = read_gate_decisions(core_target)[-1]
    assert record["verdict"] == "allow"
    assert record["reason"] == "advisory_coordination_no_native_approval"


def test_compact_journal_is_reachable_for_an_oversized_target_journal(tmp_path):
    """ga-fsfg R1: the compaction repair is the one verb allowed past the size bound."""

    canonical, target, journal = stationary_fixture(tmp_path)
    data = json.loads(journal.read_text())
    data["coordination"] = {
        "a" * 64: {
            "state": "verified",
            "request": {"bead_id": "ga-one", "action": "note", "fields": {"text": "x"}},
            "before": {"id": "ga-one", "notes": "n" * (1024 * 1024 + 64)},
            "blocker_before": None,
            "after": {"id": "ga-one"},
            "result_bead": "ga-one",
        }
    }
    write(journal, json.dumps(data))
    assert journal.stat().st_size > 1024 * 1024

    blocked = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target, "checkpoint")))
    assert blocked.returncode == 2
    assert "oversized" in blocked.stderr

    allowed = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, target, "compact-journal")))
    assert allowed.returncode == 0, allowed.stderr
    assert json.loads(allowed.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"

    extra = run_gate(
        PRETOOLUSE, canonical, event(canonical, command(canonical, target, "compact-journal", " --force"))
    )
    assert extra.returncode == 2


def test_exact_pending_id_discharge_mirrors_log_target_semantics(tmp_path):
    """ga-fsfg R1: stationary discharge binds one delivery-class target event."""

    from test_pretooluse_gates import POSTTOOLUSE

    canonical, target, _ = stationary_fixture(tmp_path)
    pending_id = "0123456789ab"

    def queue(kind):
        write(
            target / ".aegis/state/pending-tracking.json",
            json.dumps(
                {
                    "events": [
                        {
                            "id": pending_id,
                            "kind": kind,
                            "mode": "strict",
                            "task": {"id": "ga-one", "slug": "beads-first-guidance"},
                        }
                    ]
                }
            ),
        )

    request = event(
        canonical,
        command(canonical, target, "discharge", f" --pending-id {pending_id} --note recorded"),
    )
    queue("mutation")
    assert run_gate(PRETOOLUSE, canonical, request).returncode == 2
    queue("delivery")
    result = run_gate(PRETOOLUSE, canonical, request)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    unresolved = run_gate(POSTTOOLUSE, canonical, request)
    assert unresolved.returncode == 2
    (target / ".aegis/state/pending-tracking.json").unlink()
    assert run_gate(POSTTOOLUSE, canonical, request).returncode == 0
    assert not (canonical / ".aegis/state/pending-tracking.json").exists()
    assert not (target / ".aegis/state/pending-tracking.json").exists()


def test_registry_record_without_worktree_root_uses_the_derived_default(tmp_path):
    """ga-4p6f: the profile cross-check mirrors the plugin's <canonical>-worktrees default."""

    canonical, _, core, core_target, _ = registered_fixture(tmp_path)
    registry = json.loads((canonical / REGISTRY_REL).read_text())
    del registry["projects"][1]["worktree_root"]
    write(canonical / REGISTRY_REL, json.dumps(registry))
    git(canonical, "commit", "-qam", "derive core worktree root")
    derived = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, core_target, "verify")))
    assert derived.returncode == 0, derived.stderr
    assert json.loads(derived.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"

    elsewhere = tmp_path / "elsewhere-worktrees" / "ga-core-beads-first-guidance"
    git(core, "worktree", "add", "-qb", "codex/ga-core-elsewhere", str(elsewhere), "main")
    value = json.loads((canonical / PROFILE).read_text())
    value["registered_projects"][0]["worktree_root"] = str(elsewhere.parent)
    write(canonical / PROFILE, json.dumps(value))
    git(canonical, "commit", "-qam", "profile names a non-derived root")
    refused = run_gate(PRETOOLUSE, canonical, event(canonical, command(canonical, elsewhere, "verify")))
    assert refused.returncode == 2
    assert "registered project disagrees with the canonical registry" in refused.stderr
    assert '"permissionDecision": "allow"' not in refused.stdout


REVIEWER_DEFINITION = (
    "---\nname: aegis-reviewer\n"
    "description: Read-only independent reviewer for one frozen Gas City Bead candidate.\n"
    "tools: Read, Grep, Glob\nmodel: opus\n---\n\nReview the candidate and report a verdict.\n"
)


def reviewer_fixture(tmp_path):
    canonical, _, core, core_target, _ = registered_fixture(tmp_path)
    write(canonical / ".claude/agents/aegis-reviewer.md", REVIEWER_DEFINITION)
    git(canonical, "add", ".")
    git(canonical, "commit", "-qm", "reviewer")
    candidate = run(["git", "rev-parse", "HEAD"], core_target).stdout.strip()
    assert run(["git", "status", "--porcelain"], core_target).stdout == ""
    return canonical, core, core_target, candidate


def review(monkeypatch, canonical, prompt):
    """Evaluate one reviewer request through the production entry point.

    The degraded fallback is included so an unexpected exception can never pass as a
    refusal in these tests while the live hook would allow it.
    """

    from aegis_foundation.gate.hooks.pretool import (
        pretooluse_gate_with_degraded_fallback as pretooluse_gate,
    )

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(canonical))
    monkeypatch.setenv("AEGIS_INVOKING_AGENT", "claude")
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "synthetic",
        "cwd": str(canonical),
        "tool_name": "Agent",
        "tool_input": {
            "description": "Independent review",
            "prompt": prompt,
            "subagent_type": "aegis-reviewer",
        },
    }
    return pretooluse_gate(json.dumps(payload))


def test_reviewer_binds_a_clean_registered_worktree_at_the_candidate(tmp_path, monkeypatch):
    """ga-4p6f: a registered-project candidate is reviewable in its own clean worktree."""

    canonical, _, core_target, candidate = reviewer_fixture(tmp_path)
    prompt = f"Review candidate={candidate} in worktree={core_target} and report a verdict."
    assert review(monkeypatch, canonical, prompt) == 0
    record = read_gate_decisions(canonical)[-1]
    assert record["verdict"] == "allow"
    assert record["reason"] == "read_only_registered_reviewer_delegation"
    # The same commit without the binding is not in the Operations repository.
    assert review(monkeypatch, canonical, f"Review candidate={candidate} and report.") == 2


@pytest.mark.parametrize(
    "defect,detail",
    [
        ("head-mismatch", "HEAD is not the candidate commit"),
        ("tracked-change", "uncommitted or untracked changes"),
        ("untracked-file", "uncommitted or untracked changes"),
        ("unregistered-parent", "not a direct child of a registered worktree root"),
        ("symlinked-path", "exact absolute directory"),
        ("canonical-root", "not a direct child of a registered worktree root"),
        ("nested-path", "not a direct child of a registered worktree root"),
        ("foreign-repository", "not a linked worktree of its registered project"),
        ("two-worktrees", "at most one exact worktree"),
        # A trailing period is part of the path token, naming a different directory.
        ("trailing-punctuation", "worktree does not exist"),
        ("relative-path", "at most one exact worktree"),
        ("missing-path", "worktree does not exist"),
        ("case-variant", "at most one exact worktree"),
        ("fullwidth-equals", "at most one exact worktree"),
        ("embedded-mention", "at most one exact worktree"),
        ("unicode-delimiter", "at most one exact worktree"),
        ("symlink-loop", "worktree does not exist"),
        ("not-a-worktree", "Git inspection failed"),
        ("undecodable-gitdir", "Git inspection failed"),
        ("borrowed-index", "not a linked worktree of its registered project"),
        ("assume-unchanged", "hides index entries from status"),
        ("skip-worktree", "hides index entries from status"),
        ("policy-invalid", "registered-project policy is invalid"),
        ("policy-dirty", "orchestrator-command-profile.json differs from the tracked HEAD bytes"),
        ("definition-before-binding", "differs from the tracked HEAD bytes"),
    ],
)
@pytest.mark.parametrize("mode", ["strict", "advisory"])
def test_reviewer_registered_binding_refuses_every_defect(
    tmp_path, monkeypatch, capsys, defect, detail, mode
):
    canonical, core, core_target, candidate = reviewer_fixture(tmp_path)
    if mode == "advisory":
        write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    worktree = str(core_target)
    prompt = None
    if defect == "case-variant":
        prompt = f"Review candidate={candidate} in Worktree={core_target} now."
    elif defect == "fullwidth-equals":
        prompt = f"Review candidate={candidate} in worktree＝{core_target} now."
    elif defect == "embedded-mention":
        prompt = f"Review candidate={candidate} with git_worktree={core_target} now."
    elif defect == "unicode-delimiter":
        prompt = f"Review candidate={candidate} in worktree={core_target}\x1f/../other now."
    elif defect == "symlink-loop":
        loop = core_target.parent / "loop"
        loop.symlink_to(loop)
        worktree = str(loop)
    elif defect == "not-a-worktree":
        plain = core_target.parent / "plain"
        plain.mkdir()
        worktree = str(plain)
    elif defect == "undecodable-gitdir":
        odd = core_target.parent / "odd"
        odd.mkdir()
        (odd / ".git").write_bytes(b"gitdir: /tmp/\xff\n")
        worktree = str(odd)
    elif defect == "borrowed-index":
        borrowed = core_target.parent / "borrowed"
        borrowed.mkdir()
        private = run(["git", "rev-parse", "--path-format=absolute", "--git-dir"], core_target)
        (borrowed / ".git").write_text(f"gitdir: {private.stdout.strip()}\n")
        for name in run(["git", "ls-files"], core_target).stdout.split():
            source = core_target / name
            (borrowed / name).parent.mkdir(parents=True, exist_ok=True)
            (borrowed / name).write_bytes(source.read_bytes())
        worktree = str(borrowed)
    elif defect in {"assume-unchanged", "skip-worktree"}:
        tracked = run(["git", "ls-files"], core_target).stdout.split()[0]
        flag = "--assume-unchanged" if defect == "assume-unchanged" else "--skip-worktree"
        git(core_target, "update-index", flag, tracked)
        write(core_target / tracked, "hidden change\n")
        assert run(["git", "status", "--porcelain"], core_target).stdout == ""
    elif defect == "policy-invalid":
        value = json.loads((canonical / PROFILE).read_text())
        value["registered_projects"][0]["extra"] = "field"
        write(canonical / PROFILE, json.dumps(value))
        git(canonical, "commit", "-qam", "invalid registered record")
    elif defect == "policy-dirty":
        value = json.loads((canonical / PROFILE).read_text())
        value["registered_projects"][0]["rig"] = "uncommitted"
        write(canonical / PROFILE, json.dumps(value))
    elif defect == "definition-before-binding":
        write(canonical / ".claude/agents/aegis-reviewer.md", REVIEWER_DEFINITION + "\nExtra.\n")
        worktree = str(core_target.parent / "ga-missing-beads-first-guidance")
    elif defect == "head-mismatch":
        write(core_target / "later.txt", "later\n")
        git(core_target, "add", "later.txt")
        git(core_target, "commit", "-qm", "later")
    elif defect == "tracked-change":
        tracked = run(["git", "ls-files"], core_target).stdout.split()[0]
        write(core_target / tracked, "changed\n")
    elif defect == "untracked-file":
        write(core_target / "stray.txt", "stray\n")
    elif defect == "unregistered-parent":
        stray = tmp_path / "stray-worktrees" / "ga-core-beads-first-guidance"
        git(core, "worktree", "add", "-q", "--detach", str(stray), candidate)
        worktree = str(stray)
    elif defect == "symlinked-path":
        alias = core_target.parent / "alias"
        alias.symlink_to(core_target)
        worktree = str(alias)
    elif defect == "canonical-root":
        worktree = str(core)
    elif defect == "nested-path":
        nested = core_target / "docs"
        nested.mkdir(exist_ok=True)
        worktree = str(nested)
    elif defect == "foreign-repository":
        foreign = core_target.parent / "ga-foreign-beads-first-guidance"
        git(canonical, "worktree", "add", "-q", "--detach", str(foreign), "HEAD")
        candidate = run(["git", "rev-parse", "HEAD"], foreign).stdout.strip()
        worktree = str(foreign)
    elif defect == "two-worktrees":
        prompt = f"Review candidate={candidate} in worktree={core_target} and worktree={core_target} now."
    elif defect == "trailing-punctuation":
        prompt = f"Review candidate={candidate} in worktree={core_target}."
    elif defect == "relative-path":
        prompt = f"Review candidate={candidate} in worktree=core-project/ga-core now."
    elif defect == "missing-path":
        worktree = str(core_target.parent / "ga-missing-beads-first-guidance")
    if prompt is None:
        prompt = f"Review candidate={candidate} in worktree={worktree} and report a verdict."
    capsys.readouterr()
    assert review(monkeypatch, canonical, prompt) == 2
    assert detail in capsys.readouterr().err
    assert all(record["verdict"] != "allow" for record in read_gate_decisions(canonical))
    assert not (canonical / AEGIS_DEGRADED_EVENTS_REL).exists()


@pytest.mark.parametrize("mode", ["strict", "advisory"])
@pytest.mark.parametrize("failure", ["reviewer-raises", "reviewer-missing", "evaluation-raises"])
def test_delegation_failures_never_degrade_into_an_allow(
    tmp_path, monkeypatch, capsys, failure, mode
):
    """ga-4p6f: an unexpected reviewer or delegation failure refuses in every mode."""

    import sys

    from aegis_foundation.gate.hooks import pretool, reviewer

    canonical, _, core_target, candidate = reviewer_fixture(tmp_path)
    if mode == "advisory":
        write(canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')

    def explode(*_args, **_kwargs):
        raise RuntimeError("synthetic infrastructure failure")

    if failure == "reviewer-raises":
        monkeypatch.setattr(reviewer, "_reviewer_delegation", explode)
        detail = "reviewer evaluation failed: RuntimeError"
    elif failure == "reviewer-missing":
        monkeypatch.setitem(sys.modules, "aegis_foundation.gate.hooks.reviewer", None)
        detail = "reviewer evaluation failed"
    else:
        monkeypatch.setattr(pretool, "evaluate_native_delegation", explode)
        detail = "provider-native delegation cannot use degraded approval"
    capsys.readouterr()
    prompt = f"Review candidate={candidate} in worktree={core_target} now."
    assert review(monkeypatch, canonical, prompt) == 2
    assert detail in capsys.readouterr().err
    assert all(record["verdict"] != "allow" for record in read_gate_decisions(canonical))


def test_tracked_profile_registrations_agree_with_the_tracked_registry():
    """ga-4p6f: the live profile's registered projects validate against the live registry."""

    from aegis_foundation.gate.hooks.native_permissions import _validate_registered

    root = Path(__file__).resolve().parents[2]
    value = json.loads((root / PROFILE).read_text())
    validated = _validate_registered(
        value["registered_projects"], root, Path(value["worktree_root"])
    )
    assert [entry["id"] for entry in validated] == ["gas-city", "gas-city-template"]
    template = validated[1]
    assert template["worktree_root"] == template["canonical_root"] + "-worktrees"
