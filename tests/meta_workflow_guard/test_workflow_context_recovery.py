"""Exact inherited-context recovery with real Git, scaffold and readiness."""

import json
from pathlib import Path
import subprocess

import pytest

from test_workflow_attachment_recovery import start_portable
from test_workflow_context_preflight import commit_fixture
from test_gas_city_workflow_transitions import _run
from workflow_begin import resume
from workflow_common import (
    WorkflowError, advance_journal, atomic_write_json, derive_begin_spec, initialize_journal,
    journal_path,
)
from workflow_coordinate import coordinate
import workflow_context_recovery as recovery


@pytest.fixture
def inherited(tmp_path):
    parent, registry, runner, parent_path = start_portable(tmp_path)
    original_run = runner.run

    def bidirectional_ledger(argv, **kwargs):
        if "bd" in argv and "dep" in argv and "list" in argv:
            tail = list(argv)[list(argv).index("bd") + 1:]
            assert tail[:2] == ["dep", "list"] and tail[3:] == ["--direction", "up", "--json"]
            runner.calls.append(list(argv))
            rows = [{"id": bead_id, "dependency_type": edge["dependency_type"]}
                    for bead_id, bead in runner.beads.items()
                    for edge in bead.get("dependencies", []) if edge["id"] == tail[2]]
            rows = getattr(runner, "reverse_overrides", {}).get(tail[2], rows)
            return subprocess.CompletedProcess(argv, 0, json.dumps(rows), "")
        return original_run(argv, **kwargs)

    runner.run = bidirectional_ledger
    commit_fixture(parent)
    parent_state = json.loads(parent_path.read_text())
    canonical = Path(parent_state["spec"]["canonical_root"])
    base = _run(parent, "git", "rev-parse", "HEAD").stdout.strip()
    _run(canonical, "git", "update-ref", "refs/remotes/origin/main", base)
    descriptor = canonical / ".gas-city-workflow.json"
    payload = json.loads(descriptor.read_text())
    payload["base_ref"] = "refs/remotes/origin/main"
    descriptor.write_text(json.dumps(payload))
    spec, _, _ = derive_begin_spec(runner, canonical, "ga-other", slug="partial", registry=registry)
    state = initialize_journal(spec)
    advance_journal(state, "worktree-created")
    child_path = journal_path(runner, spec)
    atomic_write_json(child_path, state)
    _run(canonical, "git", "worktree", "add", "-b", spec.branch, spec.worktree, spec.base_commit)
    return parent, registry, runner, parent_path, child_path, Path(spec.worktree)


def preview(fixture):
    parent, registry, runner, *_ = fixture
    return recovery.reconcile_context(parent, "ga-other", runner=runner, registry=registry)


def apply(fixture, digest):
    parent, registry, runner, *_ = fixture
    return recovery.reconcile_context(parent, "ga-other", expected_plan_sha256=digest,
                                      runner=runner, registry=registry)


def writes(runner):
    return [call for call in runner.calls if "update" in call or ("dep" in call and "add" in call)]


def test_preview_is_readonly_and_apply_preserves_both_journals_and_worktrees(inherited):
    parent, registry, runner, parent_path, child_path, child = inherited
    before = {path: recovery._image(path) for path in (parent_path, child_path)}
    refs = _run(parent, "git", "show-ref").stdout
    mutations = len(writes(runner))
    planned = preview(inherited)
    assert planned["status"] == "planned"
    assert len(writes(runner)) == mutations
    assert all(recovery._image(path) == image for path, image in before.items())
    assert not list(child_path.parent.glob("*.context-*.json"))
    result = apply(inherited, planned["plan_sha256"])
    assert result["status"] == "reconciled"
    for name, path in (("parent", parent_path), ("child", child_path)):
        assert recovery._image(Path(result["backups"][name])) == before[path]
    assert _run(parent, "git", "show-ref").stdout == refs
    assert _run(child, "git", "status", "--porcelain").stdout == ""
    assert json.loads(child_path.read_text())["history"] == json.loads(before[child_path][0])["history"]
    assert runner.beads["ga-test"]["status"] == "in_progress"
    assert runner.beads["ga-other"]["metadata"] == runner.beads["ga-test"]["metadata"]
    assert not runner.beads["ga-other"].get("assignee")
    assert "dependents" not in runner.beads["ga-other"]
    after = {path: recovery._image(path) for path in (parent_path, child_path)}
    mutations = len(writes(runner))
    assert apply(inherited, planned["plan_sha256"])["status"] == "unchanged"
    assert len(writes(runner)) == mutations
    assert all(recovery._image(path) == image for path, image in after.items())
    with pytest.raises(WorkflowError):
        resume(child, "ga-other", slug="partial", goals=[], runner=runner, registry=registry)


def test_normal_attachment_refuses_unreconciled_standalone_context_before_mutation(inherited):
    parent, registry, runner, parent_path, child_path, _ = inherited
    before = {path: recovery._image(path) for path in (parent_path, child_path)}
    mutations = len(writes(runner))
    with pytest.raises(WorkflowError, match="standalone"):
        coordinate(parent, "ga-test", "depend", {"blocker": "ga-other"}, runner, registry=registry)
    assert all(recovery._image(path) == image for path, image in before.items())
    assert len(writes(runner)) == mutations


@pytest.mark.parametrize("fault", ["pin", "child-note", "parent-note", "dirty-child", "parent-plan",
                                  "native", "owned", "parent-closed", "parent-journal", "child-journal"])
def test_reviewed_preimage_drift_refuses_without_mutation(inherited, fault):
    parent, _, runner, parent_path, child_path, child = inherited
    planned = preview(inherited)
    digest = planned["plan_sha256"]
    if fault == "pin":
        digest = "0" * 64
    elif fault.endswith("note"):
        runner.beads["ga-other" if fault == "child-note" else "ga-test"]["notes"] = "concurrent note"
    elif fault == "dirty-child":
        (child / "unexpected.txt").write_text("preserve me")
    elif fault == "parent-plan":
        with (parent / "plans/current").open("a") as handle:
            handle.write("\nConcurrent work\n")
    elif fault == "native":
        runner.beads["ga-other"]["assignee"] = "real-native-worker"
    elif fault == "owned":
        runner.beads["ga-other"]["metadata"] = {"workflow.external_owner": "other"}
    elif fault == "parent-closed":
        runner.beads["ga-test"]["status"] = "closed"
    else:
        path = parent_path if fault == "parent-journal" else child_path
        payload = json.loads(path.read_text())
        payload["unrelated"] = "preserve me"
        path.write_text(json.dumps(payload))
    before = {path: recovery._image(path) for path in (parent_path, child_path)}
    mutations = len(writes(runner))
    with pytest.raises(WorkflowError):
        apply(inherited, digest)
    assert all(recovery._image(path) == image for path, image in before.items())
    assert len(writes(runner)) == mutations


@pytest.mark.parametrize("target", ["child", "parent"])
def test_journal_symlink_refuses_before_mutation(inherited, target):
    _, _, runner, parent_path, child_path, _ = inherited
    path = child_path if target == "child" else parent_path
    preserved = path.with_suffix(".preserved")
    path.rename(preserved)
    path.symlink_to(preserved.name)
    mutations = len(writes(runner))
    with pytest.raises((WorkflowError, OSError)):
        preview(inherited)
    assert path.is_symlink()
    assert len(writes(runner)) == mutations


def test_unknown_partial_coordination_is_not_replayed(inherited, monkeypatch):
    planned = preview(inherited)
    parent, _, runner, parent_path, _, _ = inherited
    original = runner.run

    def interrupt(argv, **kwargs):
        result = original(argv, **kwargs)
        if "dep" in argv and "add" in argv:
            raise WorkflowError("lost dependency response")
        return result

    monkeypatch.setattr(runner, "run", interrupt)
    with pytest.raises(WorkflowError, match="lost dependency response"):
        apply(inherited, planned["plan_sha256"])
    image = recovery._image(parent_path)
    mutations = len(writes(runner))
    with pytest.raises(WorkflowError):
        apply(inherited, planned["plan_sha256"])
    assert recovery._image(parent_path) == image
    assert len(writes(runner)) == mutations


@pytest.mark.parametrize("fault", ["note", "snapshot-mode", "source", "child-dirty", "record-symlink"])
def test_completed_replay_refuses_drift_without_writes(inherited, monkeypatch, fault):
    planned = preview(inherited)
    result = apply(inherited, planned["plan_sha256"])
    _, _, runner, parent_path, child_path, child = inherited
    if fault == "note":
        runner.beads["ga-other"]["notes"] = "changed after recovery"
    elif fault == "snapshot-mode":
        Path(result["backups"]["child"]).chmod(0o400)
    elif fault == "source":
        monkeypatch.setattr(recovery, "_sources", lambda: {"unknown.py": "0" * 64})
    elif fault == "child-dirty":
        (child / "new.txt").write_text("preserved")
    else:
        record = child_path.with_name("ga-other.context-recovery.json")
        target = record.with_suffix(".preserved")
        record.rename(target)
        record.symlink_to(target.name)
    before = {path: recovery._image(path) for path in (parent_path, child_path)}
    mutations = len(writes(runner))
    with pytest.raises((WorkflowError, OSError)):
        apply(inherited, planned["plan_sha256"])
    assert all(recovery._image(path) == image for path, image in before.items())
    assert len(writes(runner)) == mutations


@pytest.mark.parametrize("boundary", ["before-retirement", "before-coordinate"])
def test_known_premutation_stop_resumes_only_exact_inputs(inherited, monkeypatch, boundary):
    planned = preview(inherited)
    _, _, runner, _, child_path, _ = inherited
    with monkeypatch.context() as patch:
        if boundary == "before-retirement":
            original = recovery._write_image

            def interrupt(path, image):
                if path == child_path:
                    raise OSError("known prewrite stop")
                return original(path, image)

            patch.setattr(recovery, "_write_image", interrupt)
        else:
            import workflow_coordinate

            def interrupt(*args, **kwargs):
                raise OSError("known prewrite stop")

            patch.setattr(workflow_coordinate, "coordinate", interrupt)
        mutations = len(writes(runner))
        with pytest.raises(OSError, match="known prewrite stop"):
            apply(inherited, planned["plan_sha256"])
        assert len(writes(runner)) == mutations
    assert apply(inherited, planned["plan_sha256"])["status"] == "reconciled"


def test_backup_collision_never_overwrites_history(inherited):
    planned = preview(inherited)
    _, _, runner, parent_path, child_path, _ = inherited
    collision = child_path.with_name(f"ga-other.context-{planned['plan_sha256']}.before.json")
    collision.write_text("other preserved evidence")
    images = {path: recovery._image(path) for path in (parent_path, child_path)}
    mutations = len(writes(runner))
    with pytest.raises(WorkflowError, match="backup differs"):
        apply(inherited, planned["plan_sha256"])
    assert collision.read_text() == "other preserved evidence"
    assert all(recovery._image(path) == image for path, image in images.items())
    assert len(writes(runner)) == mutations


@pytest.mark.parametrize("fault", ["claimed", "ready", "metadata", "retirement", "history"])
def test_only_original_unowned_two_phase_attempt_is_eligible(inherited, fault):
    _, _, runner, _, child_path, _ = inherited
    payload = json.loads(child_path.read_text())
    if fault in {"claimed", "ready"}:
        payload["phase"] = fault
    elif fault == "metadata":
        payload["external_ownership"] = {}
    elif fault == "retirement":
        payload["context_recovery"] = {"parent": "ga-test"}
    else:
        payload["history"].append({"phase": "scaffolded"})
    child_path.write_text(json.dumps(payload))
    mutations = len(writes(runner))
    with pytest.raises(WorkflowError):
        preview(inherited)
    assert len(writes(runner)) == mutations


def test_cli_requires_explicit_root_child_and_full_digest_option():
    from workflow import parse_args

    with pytest.raises(SystemExit):
        parse_args(["reconcile-context"])
    args = ["reconcile-context", "--root", "/fixture", "--bead", "ga-child"]
    assert parse_args(args).expect_plan_sha256 is None
    assert parse_args([*args, "--expect-plan-sha256", "0" * 64]).expect_plan_sha256 == "0" * 64
    with pytest.raises(SystemExit):
        parse_args([*args, "--expect-plan", "0" * 64])


@pytest.mark.parametrize("fault", ["parent-journal", "reverse-edge", "unrelated-file"])
def test_unexpected_postimage_is_preserved_but_not_accepted(inherited, monkeypatch, fault):
    import workflow_coordinate

    planned = preview(inherited)
    parent, _, runner, parent_path, child_path, _ = inherited
    original = workflow_coordinate.coordinate

    def conflicting_write(*args, **kwargs):
        result = original(*args, **kwargs)
        if fault == "parent-journal":
            payload = json.loads(parent_path.read_text())
            payload["unexpected"] = "preserve"
            parent_path.write_text(json.dumps(payload))
        elif fault == "reverse-edge":
            runner.reverse_overrides = {"ga-other": []}
        else:
            (parent / "unexpected.txt").write_text("preserve")
        return result

    monkeypatch.setattr(workflow_coordinate, "coordinate", conflicting_write)
    with pytest.raises(WorkflowError):
        apply(inherited, planned["plan_sha256"])
    record = json.loads(child_path.with_name("ga-other.context-recovery.json").read_text())
    assert record["state"] == "prepared"
    if fault == "parent-journal":
        assert json.loads(parent_path.read_text())["unexpected"] == "preserve"
    elif fault == "unrelated-file":
        assert (parent / "unexpected.txt").read_text() == "preserve"
    mutations = len(writes(runner))
    with pytest.raises(WorkflowError):
        apply(inherited, planned["plan_sha256"])
    assert len(writes(runner)) == mutations


@pytest.mark.parametrize("rows", [None, {}, [None], [{"id": "ga-test"}],
                                [{"id": "ga-test", "dependency_type": ""}],
                                [{"id": "external:ga-test", "dependency_type": "blocks"}],
                                [{"id": "other-task", "dependency_type": "blocks"}],
                                [{"id": "ga-test", "dependency_type": "blocks"}] * 2])
def test_malformed_reverse_dependency_read_refuses_before_preparation(inherited, rows):
    _, _, runner, parent_path, child_path, _ = inherited
    runner.reverse_overrides = {"ga-other": rows}
    before = {path: recovery._image(path) for path in (parent_path, child_path)}
    mutations = len(writes(runner))
    with pytest.raises(WorkflowError):
        preview(inherited)
    assert all(recovery._image(path) == image for path, image in before.items())
    assert len(writes(runner)) == mutations
