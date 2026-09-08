"""Real portable attachment/readiness; only Beads transport is simulated."""

import hashlib
import json
from pathlib import Path

import pytest

from test_workflow_coordinate import LedgerRunner
from tests.meta_workflow_guard.test_workflow_portable_source import portable_project
from workflow_begin import begin
from workflow_common import CommandRunner
from workflow_coordinate import coordinate
from workflow_common import WorkflowError
import workflow_attach
import workflow_attachment_reconcile as recovery


class PortableLedger(LedgerRunner):
    def run(self, argv, *, cwd=None, env=None, check=True):
        args = list(argv)
        if str(args[0]).endswith("/gc"):
            assert "bd" in args, "No live Gas City invocation in this fixture"
            tail = args[args.index("bd") + 1:]
            assert ((tail[0] == "show" and tail[1] in self.beads)
                    or (tail[0] == "update" and "--set-metadata" in tail and tail[1] in self.beads)
                    or tail[:2] == ["dep", "add"]), "Unexpected Beads invocation"
            return super().run(args, cwd=cwd, env=env, check=check)
        self.calls.append(args)
        return CommandRunner.run(self, args, cwd=cwd, env=env, check=check)


def start_portable(tmp_path):
    canonical, registry = portable_project(tmp_path)
    runner = PortableLedger()
    started = begin(canonical, "ga-test", slug="attach", goals=[], registry=registry, runner=runner)
    return Path(started["spec"]["worktree"]), registry, runner, Path(started["journal"])


def test_portable_dependency_attachment_runs_real_readiness(tmp_path):
    root, registry, runner, journal = start_portable(tmp_path)
    result = coordinate(root, "ga-test", "depend", {"blocker": "ga-other"}, runner, registry=registry)
    assert result["status"] == "applied"
    state = json.loads(journal.read_text())
    assert state["attached_bead_ids"] == ["ga-other"]
    assert all(item["state"] == "verified" for item in state["coordination"].values())


@pytest.fixture
def partial(tmp_path, monkeypatch):
    root, registry, runner, path = start_portable(tmp_path)
    write = workflow_attach.atomic_write_json

    def interrupt_before_membership(target, payload):
        if payload.get("attached_bead_ids") == ["ga-other"]:
            raise OSError("interrupted before membership publication")
        write(target, payload)

    with monkeypatch.context() as patch:
        patch.setattr(workflow_attach, "atomic_write_json", interrupt_before_membership)
        with pytest.raises(OSError, match="interrupted before membership"):
            coordinate(root, "ga-test", "depend", {"blocker": "ga-other"}, runner, registry=registry)
    state = json.loads(path.read_text())
    assert "attached_bead_ids" not in state
    request = next(iter(state["coordination"]))
    plan = workflow_attach._current_plan(root)
    tracker = workflow_attach._active_tracker(root, "ga-test")
    images = {p: recovery._image(p) for p in (path, plan, tracker)}
    pins = [hashlib.sha256(images[p][0]).hexdigest() for p in (path, plan, tracker)]
    return root, registry, runner, path, request, pins, images


def complete(partial, pins=None):
    root, registry, runner, _, request, expected, _ = partial
    return recovery.reconcile_attachment(root, request, *(pins or expected), runner, registry=registry)


def test_exact_legacy_partial_recovery_and_noop_never_repeat_bead_writes(partial):
    _, _, runner, path, request, _, images = partial
    calls = len(runner.calls)
    result = complete(partial)
    assert result["status"] == "reconciled"
    assert recovery._image(Path(result["backup"])) == images[path]
    state = json.loads(path.read_text())
    assert state["coordination"][request]["state"] == "verified"
    assert state["attached_bead_ids"] == ["ga-other"]
    after = recovery._image(path)
    assert complete(partial)["status"] == "unchanged"
    assert recovery._image(path) == after
    assert all(recovery._image(p) == image for p, image in images.items() if p != path)
    assert not any("update" in call or "dep" in call for call in runner.calls[calls:])


@pytest.mark.parametrize("index", range(3))
def test_recovery_requires_every_exact_preimage_digest(partial, index):
    *_, pins, images = partial
    wrong = list(pins)
    wrong[index] = "0" * 64
    with pytest.raises(WorkflowError, match="digest"):
        complete(partial, wrong)
    assert all(recovery._image(path) == image for path, image in images.items())


@pytest.mark.parametrize("fault", ["owner", "primary-note", "child-note", "extra-edge", "native", "closed"])
def test_live_authority_or_graph_drift_refuses_before_journal_write(partial, fault):
    _, _, runner, path, _, _, images = partial
    if fault == "owner":
        runner.beads["ga-other"]["metadata"]["workflow.external_owner"] = "wrong"
    elif fault == "primary-note":
        runner.beads["ga-test"]["notes"] = "unrelated concurrent note"
    elif fault == "child-note":
        runner.beads["ga-other"]["notes"] = "unrelated concurrent note"
    elif fault == "extra-edge":
        runner.beads["ga-test"]["dependencies"].append({"id": "ga-third", "dependency_type": "blocks"})
    elif fault == "native":
        runner.beads["ga-other"]["assignee"] = "worker-session"
    else:
        runner.beads["ga-other"]["status"] = "closed"
    with pytest.raises(WorkflowError):
        complete(partial)
    assert recovery._image(path) == images[path]
    assert not list(path.parent.glob("*.before.json"))


def test_failed_readiness_rolls_back_only_the_exact_journal(partial, monkeypatch):
    _, _, _, path, _, _, images = partial

    def fail(*args, **kwargs):
        raise WorkflowError("injected readiness refusal")

    monkeypatch.setattr(recovery, "run_readiness", fail)
    with pytest.raises(WorkflowError, match="injected readiness refusal"):
        complete(partial)
    assert all(recovery._image(p) == image for p, image in images.items())
    backups = list(path.parent.glob("*.before.json"))
    assert len(backups) == 1 and recovery._image(backups[0]) == images[path]


def test_unknown_journal_change_is_never_overwritten_by_rollback(partial, monkeypatch):
    _, _, _, path, _, _, _ = partial

    def drift(*args, **kwargs):
        path.write_text("unexpected concurrent image")
        raise WorkflowError("injected refusal after unrelated write")

    monkeypatch.setattr(recovery, "run_readiness", drift)
    with pytest.raises(WorkflowError, match="rollback refused"):
        complete(partial)
    assert path.read_text() == "unexpected concurrent image"


def test_backup_collision_refuses_without_overwriting_evidence(partial):
    _, _, _, path, request, pins, images = partial
    backup = path.with_name(f"{path.stem}.attachment-{request}-{pins[0]}.before.json")
    backup.write_text("preserved other evidence")
    with pytest.raises(WorkflowError, match="backup differs"):
        complete(partial)
    assert backup.read_text() == "preserved other evidence"
    assert recovery._image(path) == images[path]


def test_completed_replay_refuses_backup_mode_drift(partial):
    _, _, _, path, _, _, _ = partial
    result = complete(partial)
    after = recovery._image(path)
    backup = Path(result["backup"])
    backup.chmod(recovery._image(backup)[1] ^ 0o100)
    with pytest.raises(WorkflowError, match="not an exact completed"):
        complete(partial)
    assert recovery._image(path) == after


def test_journal_symlink_is_refused(partial):
    _, _, _, path, _, _, _ = partial
    preserved = path.with_suffix(".preserved")
    path.rename(preserved)
    path.symlink_to(preserved.name)
    with pytest.raises((WorkflowError, OSError)):
        complete(partial)
    assert path.is_symlink()


def test_cli_requires_all_pins_and_rejects_abbreviated_flags():
    from workflow import parse_args

    argv = ["reconcile-attachment", "--root", "/fixture"]
    with pytest.raises(SystemExit):
        parse_args(argv)
    for flag in ("request-sha256", "expect-journal-sha256", "expect-plan-sha256", "expect-tracker-sha256"):
        argv += ["--" + flag, "0" * 64]
    assert parse_args(argv).command == "reconcile-attachment"
    argv[1] = "--roo"
    with pytest.raises(SystemExit):
        parse_args(argv)
