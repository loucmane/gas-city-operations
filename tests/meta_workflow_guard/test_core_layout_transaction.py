"""Actual outer engine, real leaf WAL/sync/readiness; disposable Git only.

The fixture substitutes Beads transport, not filesystem or transaction semantics.
This does not authorize or execute a production Core relocation.
"""
import base64
import copy
import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from tests.meta_workflow_guard.test_layout_relocation_composition import (
    project, task_source, synchronize,
)
from _core_layout_state import CONFIG, PARENTS, RelocationError, canonical, digest, freeze, inspect, tree
from _core_layout_transaction import CoreLayoutTransaction
from aegis_foundation.gate.session_transition import JOURNAL, SessionTransition, session_lock
from workflow_lock import workflow_lock
from workflow_portable import run_portable_readiness
from tests.meta_workflow_guard.test_gas_city_workflow_transitions import _run


@pytest.fixture
def scenario(project):
    root, registry, runner, old_plan, old_tracker, moves = project
    historical = []
    for day in range(1, 10):
        historic = root / f"plans/2020-01-{day:02d}-historical.md"
        historic.write_bytes(f"# Historical evidence {day}: never rewrite\n".encode())
        historical.append(historic.relative_to(root).as_posix())
    _run(root, "git", "add", "--", *historical)
    _run(root, "git", "commit", "-m", "Fixture: nine historical plans")
    assert set(_run(root, "git", "ls-files", "plans").stdout.splitlines()) == set(historical)
    policy = "a" * 64  # Fixture-only source binding, not a review authorization.
    plan = freeze(root, "ga-test", policy, ["AGENTS.md", *historical])
    module = task_source()
    tracker = root / "engdocs/workflow/work-tracking" / old_tracker.relative_to(root / "docs/ai/work-tracking")

    def ready():
        assert "STATE: READY" in run_portable_readiness(runner, root)

    def make(fault=None):
        return CoreLayoutTransaction(
            root, plan, preflight=ready, postflight=ready, fault=fault,
            synchronize=lambda txn, active, sync: synchronize(module, root, active, tracker, txn),
        )

    def execute(transaction):
        with workflow_lock(runner, root, registry), session_lock(root):
            return transaction.apply()

    return root, plan, make, execute


def originals(root, plan):
    result = {}
    for source, _ in plan["moves"]:
        result.update(tree(root, source))
    return result


def snapshot(root):
    result = {}
    for child in sorted(root.iterdir()):
        result.update(tree(root, child.name))
    return result


def test_outer_success_and_exact_read_only_replay(scenario):
    root, plan, make, execute = scenario
    transaction = make()
    assert execute(transaction)["status"] == "PASS"
    assert transaction.leaf.record["created_directories"] == []
    assert len(transaction.leaf.record["steps"]) == 3
    assert (root / ".codex/config.toml").read_bytes() == CONFIG
    for name, expected in plan["protected"].items():
        assert inspect(root / name) == expected
    for name, expected in plan["entries"].items():
        assert inspect(transaction.directory / "originals" / name) == expected
    before = snapshot(root)
    audit_before = snapshot(transaction.directory)
    assert execute(make())["idempotent"] is True
    assert snapshot(root) == before
    assert snapshot(transaction.directory) == audit_before


@pytest.mark.parametrize("stage", [
    *("parent:" + p for p in PARENTS),
    "move:docs/ai/work-tracking", "move:sessions", "move:.plan_state",
    "move:active-plan", "move:plans/current", "config", "plan", "sync",
    "leaf-committed", "postflight",
])
def test_known_failure_restores_five_moves_and_preserves_evidence(scenario, stage):
    root, plan, make, execute = scenario
    if stage == "move:active-plan":
        stage = "move:plans/" + plan["plan_name"]

    def fault(current):
        if current == stage:
            raise RuntimeError("injected known failure")

    transaction = make(fault)
    with pytest.raises(RuntimeError, match="injected known failure"):
        execute(transaction)
    assert transaction.record["status"] == "rolled_back"
    assert originals(root, plan) == plan["entries"]
    assert all(not (root / p).exists() for p in PARENTS)
    assert (transaction.directory / "failed-postimages.json").is_file()
    for name, expected in plan["protected"].items():
        assert inspect(root / name) == expected
    before = snapshot(root)
    with pytest.raises(RelocationError, match="not complete"):
        execute(make())
    assert snapshot(root) == before


@pytest.mark.parametrize("extra", ["engdocs/workflow/unexpected", "engdocs/workflow/plans/unexpected"])
def test_unknown_parent_child_prevents_any_rollback_write(scenario, extra):
    root, plan, make, execute = scenario
    captured = {}

    def fault(stage):
        if stage == "leaf-committed":
            (root / extra).write_bytes(b"unknown concurrent content\n")
            captured.update(snapshot(root))
            raise RuntimeError("injected unknown extra child")

    transaction = make(fault)
    with pytest.raises(RelocationError, match="unresolved"):
        execute(transaction)
    assert snapshot(root) == captured
    assert transaction.record["status"] == "unresolved"


def test_failed_postimages_are_saved_before_leaf_auto_rollback(scenario):
    root, plan, make, execute = scenario

    def fault(stage):
        if stage == "config":
            raise RuntimeError("injected after config")

    transaction = make(fault)
    with pytest.raises(RuntimeError, match="injected"):
        execute(transaction)
    failed = json.loads((transaction.directory / "failed-postimages.json").read_text())
    assert base64.b64decode(failed[".codex/config.toml"]["data_b64"]) == CONFIG
    assert not (root / ".codex").exists()


@pytest.mark.parametrize("when", ["before-archive", "after-archive"])
def test_leaf_entry_failure_is_recognized_and_rolled_back(scenario, monkeypatch, when):
    root, plan, make, execute = scenario
    archive = SessionTransition._archive

    def failing_archive(self, record):
        if when == "after-archive":
            archive(self, record)
        raise OSError("injected leaf entry failure")

    monkeypatch.setattr(SessionTransition, "_archive", failing_archive)
    transaction = make()
    with pytest.raises(OSError, match="injected leaf entry"):
        execute(transaction)
    assert transaction.record["status"] == "rolled_back"
    assert originals(root, plan) == plan["entries"]


@pytest.mark.parametrize("artifact", ["plan.json", "originals/plans/historical-placeholder"])
def test_replay_refuses_changed_audit_artifacts(scenario, artifact):
    root, plan, make, execute = scenario
    transaction = make()
    execute(transaction)
    if artifact.endswith("historical-placeholder"):
        artifact = "originals/plans/" + plan["plan_name"]
    (transaction.directory / artifact).write_bytes(b"unexpected backup mutation\n")
    before = snapshot(root)
    with pytest.raises(RelocationError):
        execute(make())
    assert snapshot(root) == before


def test_abrupt_interruption_is_preserved_and_not_replayed(scenario):
    root, plan, make, execute = scenario

    class Interrupted(BaseException):
        pass

    def fault(stage):
        if stage == "move:sessions":
            raise Interrupted()

    transaction = make(fault)
    with pytest.raises(Interrupted):
        execute(transaction)
    before = snapshot(root)
    # The real preflight can refuse the partial layout before the journal check.
    with pytest.raises(Exception):
        execute(make())
    assert snapshot(root) == before
    assert transaction.record["status"] != "complete"


def test_freeze_requires_target_local_session_link(project):
    root, _, _, old_plan, old_tracker, moves = project
    current = root / "sessions/current"
    current.unlink()
    current.symlink_to("../AGENTS.md")
    with pytest.raises(RelocationError, match="session"):
        freeze(root, "ga-test", "a" * 64, ["AGENTS.md"])


def test_freeze_requires_existing_terminal_session_wal(project):
    root, _, _, old_plan, old_tracker, moves = project
    (root / JOURNAL).unlink()  # Disposable fixture only.
    with pytest.raises(RelocationError, match="WAL"):
        freeze(root, "ga-test", "a" * 64, ["AGENTS.md"])


@pytest.mark.parametrize("fault", ["destination", "extra-link", "hardlink", "fifo", "mode", "protected", "tracked-unprotected", "index", "ownership"])
def test_preflight_drift_refuses_without_transaction_or_target_writes(scenario, fault):
    root, plan, make, execute = scenario
    if fault == "destination":
        (root / "engdocs/workflow").mkdir()
    elif fault == "extra-link":
        (root / "sessions/extra").symlink_to("state.json")
    elif fault == "hardlink":
        os.link(root / ".plan_state/sync.log", root / ".plan_state/extra")
    elif fault == "fifo":
        os.mkfifo(root / "sessions/extra")
    elif fault == "mode":
        (root / ".plan_state/sync.log").chmod(0o600)
    elif fault == "protected":
        (root / "AGENTS.md").write_text("Unexpected source change\n")
    elif fault == "tracked-unprotected":
        path = root / ".gas-city-workflow.json"
        path.write_text(path.read_text() + "\n")
    else:
        path = Path(plan["external"][fault]["path"])
        path.write_bytes(path.read_bytes() + b"unexpected drift\n")
    transaction = make()
    # Special/hardlinked fixtures cannot be hashed by the intentionally strict
    # inventory helper; absence of the audit directory and destination writes
    # proves refusal before the transaction starts.
    with pytest.raises(Exception):
        execute(transaction)
    assert not transaction.directory.exists()
    assert not (root / "engdocs/workflow/sessions").exists()
    assert not (root / ".codex/config.toml").exists()


@pytest.mark.parametrize("stage", ["config", "plan", "sync"])
def test_unknown_content_during_leaf_phase_is_not_partially_restored(scenario, stage):
    root, plan, make, execute = scenario
    before = {}

    def fault(current):
        if current == stage:
            (root / "engdocs/workflow/unknown").write_bytes(b"preserve me\n")
            before.update(snapshot(root))
            raise RuntimeError("unknown leaf-phase writer")

    transaction = make(fault)
    with pytest.raises(RelocationError, match="unresolved"):
        execute(transaction)
    assert snapshot(root) == before


def test_failed_leaf_commit_preserves_postimages_then_restores(scenario, monkeypatch):
    root, plan, make, execute = scenario
    save = SessionTransition._save
    failed = False

    def fail_commit(self):
        nonlocal failed
        if self.record["status"] == "complete" and not failed:
            failed = True
            raise OSError("injected commit write refusal")
        return save(self)

    monkeypatch.setattr(SessionTransition, "_save", fail_commit)
    transaction = make()
    with pytest.raises(OSError, match="injected commit"):
        execute(transaction)
    assert transaction.record["status"] == "rolled_back"
    assert originals(root, plan) == plan["entries"]
    failed_images = json.loads((transaction.directory / "failed-postimages.json").read_text())
    assert base64.b64decode(failed_images[".codex/config.toml"]["data_b64"]) == CONFIG


@pytest.mark.parametrize("fault", ["external-path", "unknown-field", "foreign-wal"])
def test_self_consistent_digest_does_not_authorize_manifest_scope(scenario, fault):
    root, plan, make, execute = scenario
    malformed = copy.deepcopy(plan)
    if fault == "external-path":
        malformed["external"]["../../escaped"] = malformed["external"]["index"]
    elif fault == "unknown-field":
        malformed["arbitrary_command"] = "not an execution surface"
    else:
        malformed["wal_before"]["../../outside"] = {"kind": "absent"}
    seed = {k: v for k, v in malformed.items() if k not in {"plan_id", "plan_after_b64"}}
    malformed["plan_id"] = digest(canonical(seed))
    before = snapshot(root)
    with pytest.raises(RelocationError):
        CoreLayoutTransaction(root, malformed, preflight=None, synchronize=None, postflight=None)
    assert snapshot(root) == before
