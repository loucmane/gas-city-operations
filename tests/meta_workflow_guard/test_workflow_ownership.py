"""External source-work tracking must not masquerade as a native session claim."""

import json
from pathlib import Path

import pytest

from tests.meta_workflow_guard.test_gas_city_workflow_transitions import (
    FixtureRunner,
    _bead,
    _fixture_project,
)
from workflow_begin import begin, resume
from workflow_common import WorkflowError, BeginSpec
from workflow import _checkpoint
from workflow_ownership import (
    OWNER_KEY,
    bead_digest,
    owner_binding,
    owner_payload,
    require_binding,
    require_external_candidate,
)
from workflow_ownership_reconcile import adopt_external
from workflow_lock import workflow_lock


def test_begin_tracks_external_source_work_without_claiming_os_user(tmp_path):
    root, registry = _fixture_project(tmp_path)
    bead = _bead()
    bead["metadata"] = {"unrelated": "preserved"}
    runner = FixtureRunner(bead)
    result = begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    assert not bead.get("assignee")
    assert bead["status"] == "in_progress"
    assert bead["metadata"]["unrelated"] == "preserved"
    binding = bead["metadata"]["workflow.external_owner"]
    assert binding.startswith("external-coordinator.v1:")
    assert len(binding) == len("external-coordinator.v1:") + 64
    assert binding == owner_binding(BeginSpec(**result["spec"]), result["context"])
    update = next(call for call in runner.calls if "--set-metadata" in call)
    assert update[update.index("--set-metadata") + 1] == f"{OWNER_KEY}={binding}"
    assert not any(char in binding for char in '\\"{} ')
    assert not any("--claim" in call for call in runner.calls)


@pytest.mark.parametrize("assignee", ["loucmane", "human", "ci-worker"])
def test_begin_never_adopts_an_existing_assignee(tmp_path, assignee):
    root, registry = _fixture_project(tmp_path)
    bead = _bead(status="in_progress")
    bead["assignee"] = assignee
    with pytest.raises(WorkflowError, match="assigned"):
        begin(
            root, "ga-test", slug="fixture", goals=[], registry=registry, runner=FixtureRunner(bead)
        )
    assert not (tmp_path / "future-project-worktrees").exists()


@pytest.mark.parametrize("key", ["gc.session_id", "gc.session_name", "gc.agent", "gc.target"])
def test_begin_never_adopts_native_routing_metadata(tmp_path, key):
    root, registry = _fixture_project(tmp_path)
    bead = _bead()
    bead["metadata"] = {key: "native-identity"}
    with pytest.raises(WorkflowError, match="native"):
        begin(
            root, "ga-test", slug="fixture", goals=[], registry=registry, runner=FixtureRunner(bead)
        )
    assert not (tmp_path / "future-project-worktrees").exists()


def test_resume_does_not_silently_reclaim_reopened_work(tmp_path):
    root, registry = _fixture_project(tmp_path)
    runner = FixtureRunner(_bead())
    first = begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    runner.bead["status"] = "open"
    runner.calls.clear()
    with pytest.raises(WorkflowError, match="ownership|in_progress"):
        resume(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    assert not any("update" in call for call in runner.calls)
    assert json.loads(Path(first["journal"]).read_text())["phase"] == "ready"


def test_checkpoint_checks_live_bead_before_any_local_sync(tmp_path):
    root, registry = _fixture_project(tmp_path)
    runner = FixtureRunner(_bead())
    first = begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    runner.bead["status"] = "open"
    runner.calls.clear()
    with pytest.raises(WorkflowError, match="ownership|in_progress"):
        _checkpoint(Path(first["spec"]["worktree"]), runner)
    assert not any("sync" in call for call in runner.calls)


@pytest.mark.parametrize("mutation", ["assignee", "binding", "native", "dependency"])
def test_checkpoint_refuses_fresh_ownership_drift(tmp_path, mutation):
    root, registry = _fixture_project(tmp_path)
    runner = FixtureRunner(_bead())
    first = begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    if mutation == "assignee":
        runner.bead["assignee"] = "ci-new"
    elif mutation == "binding":
        runner.bead["metadata"][OWNER_KEY] = "another transaction"
    elif mutation == "native":
        runner.bead["metadata"]["gc.routed_to"] = "pool"
    else:
        runner.bead["dependencies"] = [{"id": "ga-other", "status": "open"}]
    runner.calls.clear()
    with pytest.raises(WorkflowError):
        _checkpoint(Path(first["spec"]["worktree"]), runner)
    assert not any("sync" in call or "update" in call for call in runner.calls)


def test_legacy_adoption_requires_exact_digest_and_preserves_evidence(tmp_path):
    root, registry = _fixture_project(tmp_path)
    runner = FixtureRunner(_bead())
    first = begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    worktree = Path(first["spec"]["worktree"])
    path = Path(first["journal"])
    journal = json.loads(path.read_text())
    del journal["external_ownership"]
    path.write_text(json.dumps(journal))
    del runner.bead["metadata"][OWNER_KEY]
    runner.bead["status"] = "open"
    original_plan = (worktree / "plans/current").read_bytes()
    with pytest.raises(WorkflowError, match="explicit"):
        resume(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    with pytest.raises(WorkflowError, match="changed"):
        adopt_external(worktree, "0" * 64, runner)
    runner.calls.clear()
    result = adopt_external(worktree, bead_digest(runner.bead), runner)
    assert result["status"] == "bound"
    assert not runner.bead.get("assignee")
    assert (worktree / "plans/current").read_bytes() == original_plan
    assert json.loads(path.read_text())["history"] == journal["history"]
    assert sum("update" in call for call in runner.calls) == 1
    runner.calls.clear()
    adopt_external(worktree, bead_digest(runner.bead), runner)
    assert not any("update" in call for call in runner.calls)


def test_interrupted_success_reconciles_without_repeating_ledger_mutation(tmp_path):
    root, registry = _fixture_project(tmp_path)

    class Interrupted(FixtureRunner):
        interrupted = False

        def run(self, argv, **kwargs):
            result = super().run(argv, **kwargs)
            if "--set-metadata" in argv and not self.interrupted:
                self.interrupted = True
                raise WorkflowError("response lost after mutation")
            return result

    runner = Interrupted(_bead())
    with pytest.raises(WorkflowError, match="response lost"):
        begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    runner.calls.clear()
    assert (
        begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)["status"]
        == "ready"
    )
    assert not any("update" in call for call in runner.calls)


def test_unexpected_mutation_is_preserved_and_never_auto_retried(tmp_path):
    root, registry = _fixture_project(tmp_path)

    class ConcurrentWriter(FixtureRunner):
        def run(self, argv, **kwargs):
            result = super().run(argv, **kwargs)
            if "--set-metadata" in argv:
                self.bead["notes"] = "concurrent writer"
            return result

    runner = ConcurrentWriter(_bead())
    for _ in range(2):
        with pytest.raises(WorkflowError, match="unexpected ownership write delta"):
            begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    assert sum("update" in call for call in runner.calls) == 1
    assert runner.bead["notes"] == "concurrent writer"


def test_source_cli_lock_refuses_concurrent_transition_and_releases(tmp_path):
    root, registry = _fixture_project(tmp_path)
    runner = FixtureRunner(_bead())
    with workflow_lock(runner, root, registry):
        with pytest.raises(WorkflowError, match="another source"):
            with workflow_lock(runner, root, registry):
                pytest.fail("concurrent lock acquired")
    with workflow_lock(runner, root, registry):
        pass


def test_managed_environment_pins_city_and_scrubs_store_overrides(monkeypatch):
    from workflow_common import managed_environment, OPERATOR_PATH

    monkeypatch.setenv("GC_HOME", "/wrong/home")
    monkeypatch.setenv("BEADS_DIR", "/wrong/store")
    monkeypatch.setenv("BEADS_DB", "/wrong/db")
    monkeypatch.setenv("BEADS_DOLT_SERVER_PORT", "99")
    monkeypatch.setenv("UNRELATED_SETTING", "preserved")
    env = managed_environment()
    assert env["PATH"] == OPERATOR_PATH
    assert env["GC_HOME"] == "/home/loucmane/gascity/home"
    assert env["UNRELATED_SETTING"] == "preserved"
    assert not any(key in env for key in ["BEADS_DIR", "BEADS_DB", "BEADS_DOLT_SERVER_PORT"])


def test_legacy_encoded_pending_intent_is_not_silently_rewritten(tmp_path):
    root, registry = _fixture_project(tmp_path)
    runner = FixtureRunner(_bead())
    first = begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    path = Path(first["journal"])
    journal = json.loads(path.read_text())
    record = journal["external_ownership"]["ga-test"]
    record["state"] = "pending"
    record["binding"] = '{"kind":"external-coordinator"}'
    runner.bead["metadata"][OWNER_KEY] = json.dumps(record["binding"])
    path.write_text(json.dumps(journal))
    runner.calls.clear()
    with pytest.raises(WorkflowError, match="intent drift"):
        begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    assert not any("update" in call for call in runner.calls)
    assert json.loads(path.read_text())["external_ownership"]["ga-test"]["state"] == "pending"


@pytest.mark.parametrize("extra_drift", [False, True])
def test_explicit_wire_repair_matches_only_the_exact_preserved_failure(tmp_path, extra_drift):
    root, registry = _fixture_project(tmp_path)
    runner = FixtureRunner(_bead())
    first = begin(root, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    path = Path(first["journal"])
    worktree = Path(first["spec"]["worktree"])
    journal = json.loads(path.read_text())
    record = journal["external_ownership"]["ga-test"]
    record["state"] = "pending"
    record["binding"] = owner_payload(BeginSpec(**first["spec"]), first["context"])
    runner.bead["metadata"][OWNER_KEY] = json.dumps(record["binding"])
    path.write_text(json.dumps(journal))
    runner.calls.clear()
    if extra_drift:
        runner.bead["notes"] = "unexpected writer"
        with pytest.raises(WorkflowError, match="unexpected ownership write delta"):
            adopt_external(worktree, bead_digest(runner.bead), runner, repair_legacy_wire=True)
        assert not any("update" in call for call in runner.calls)
        return
    adopt_external(worktree, bead_digest(runner.bead), runner, repair_legacy_wire=True)
    updated = json.loads(path.read_text())
    assert updated["ownership_reconciliations"][0]["prior_intent"] == record
    assert updated["external_ownership"]["ga-test"]["state"] == "verified"
    assert runner.bead["metadata"][OWNER_KEY] == owner_binding(
        BeginSpec(**first["spec"]), first["context"]
    )
    assert not runner.bead.get("assignee")
    assert sum("update" in call for call in runner.calls) == 1


_BINDING = "external-coordinator.v1:" + "0" * 64


def _owned(status, **metadata):
    return {"id": "ga-attached", "status": status, "metadata": {OWNER_KEY: _BINDING, **metadata}}


def test_closed_attached_bead_may_carry_core_closeout_outcome():
    # ga-4p6f: Core closeout wrote gc.work_outcome on a closed attached bead,
    # and every coordination verb on the primary was refused from then on.
    require_binding(_owned("closed", **{"gc.work_outcome": "shipped"}), _BINDING, allow_closed=True)


@pytest.mark.parametrize(
    "status, allow_closed, metadata",
    [
        ("in_progress", True, {"gc.work_outcome": "shipped"}),
        ("in_progress", False, {"gc.work_outcome": "shipped"}),
        ("closed", False, {"gc.work_outcome": "shipped"}),
        ("closed", True, {"gc.work_outcome": "shipped", "gc.routed_to": "rig/worker"}),
        ("closed", True, {"gc.session_id": "ci-1"}),
        ("closed", True, {"gc.work_branch": "agent/x"}),
        ("closed", True, {"routed_to": "rig/worker"}),
    ],
)
def test_only_the_closeout_outcome_on_a_closed_bead_is_tolerated(status, allow_closed, metadata):
    with pytest.raises(WorkflowError):
        require_binding(_owned(status, **metadata), _BINDING, allow_closed=allow_closed)


def test_begin_path_still_refuses_closeout_outcome():
    # Adoption and begin call the candidate check without closed_outcome.
    with pytest.raises(WorkflowError, match="native control metadata"):
        require_external_candidate(_owned("closed", **{"gc.work_outcome": "shipped"}))
