"""Offline-only admission matrix for ga-jcxb; no worker or host mutation."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import types

import pytest

HERE = Path(__file__).parent


def load():
    m = types.ModuleType("fresh_window_contract")
    m.__file__ = str(HERE / "contract.py")
    exec(compile((HERE / "contract.py").read_bytes(), m.__file__, "exec"), m.__dict__)
    return m


c = load()


@pytest.fixture
def task():
    return json.loads((HERE / "task-own-fields.json").read_bytes())


def bound(task):
    task = copy.deepcopy(task)
    task["metadata"] = {"gc.work_dir": c.WORK}
    task["notes"] = c.BOUND_NOTE
    return task


def routed(task):
    task = bound(task)
    task["metadata"]["gc.routed_to"] = c.TARGET
    return task


def rules():
    return b"".join(b"!! " + x.encode() + b"\0" for x in c.RULES)


def candidate():
    return rules() + b"".join(b"?? "+p.encode()+b"\0" for p in c.SOURCE_PATHS) + b"?? " + c.EVIDENCE_ROOT.encode() + b"report.json\0"


def test_fresh_same_store_snapshot_matches(task):
    assert task == c.BASELINE
    c.validate_task(task, "unbound")
    assert task["dependencies"] == [{"id": "ga-e0t1", "dependency_type": "relates-to"}]
    assert c.UNBOUND_NOTE == "" and "notes" not in task and "parent" not in task
    # Parent history is not an input to the child's mutation authority.
    task["dependencies"][0]["notes"] = "Changing historical parent audit"
    c.validate_task(task, "unbound")


@pytest.mark.parametrize("key,value", [
    ("id", "ga-other"), ("title", "Re-scoped work"), ("status", "in_progress"),
    ("priority", 1), ("issue_type", "feature"), ("assignee", "codex-ci-old"),
    ("description", "different"), ("acceptance_criteria", "different"),
    ("notes", "unexpected"), ("notes", c.BIND_NOTE), ("labels", ["needs/operator"]),
    ("comment_count", 1), ("dependency_count", 3), ("dependent_count", 1),
    ("parent", "ga-wrong"), ("parent", "ga-e0t1"), ("parent", None), ("started_at", "2026-09-28T13:01:54Z"),
    ("metadata", {"gc.session_id": "ci-9dp7z"}), ("metadata", None),
    ("metadata", {"workflow.external_owner": "fake"}),
    ("unknown_authority", "never silently accepted"),
])
def test_own_field_drift_refuses(task, key, value):
    task[key] = value
    with pytest.raises(RuntimeError):
        c.validate_task(task, "unbound")


@pytest.mark.parametrize("kind", ["blocks", "parent-child", "missing", "duplicate", "other", "dependent"])
def test_wrong_relationship_refuses(task, kind):
    if kind in ("blocks", "parent-child"):
        task["dependencies"][0]["dependency_type"] = kind
    elif kind == "missing":
        task["dependencies"] = []
    elif kind == "duplicate":
        task["dependencies"] *= 2
    elif kind == "other":
        task["dependencies"][0]["id"] = "ga-other"
    else:
        task["dependents"] = [{"id": "ga-extra"}]
    with pytest.raises(RuntimeError):
        c.validate_task(task, "unbound")


def test_binding_is_notes_append_and_workdir_only(task):
    after = bound(task)
    after["updated_at"] = "2026-09-29T12:00:00Z"
    c.validate_binding_delta(task, after)
    assert "notes" not in task and after["notes"] == c.BIND_NOTE
    assert after["notes"].count(c.BIND_NOTE) == 1
    with pytest.raises(RuntimeError):
        c.validate_task(after, "unbound")
    c.validate_route_delta(after, routed(task))
    with pytest.raises(RuntimeError):
        c.validate_task(routed(task), "bound")


@pytest.mark.parametrize("key,value", [
    ("gc.session_id", "ci-old"), ("gc.session_name", "codex-ci-old"),
    ("gc.failure_owner", "gc.session-reconciler"), ("gc.failure_reason", "progress_stall"),
    ("gc.work_branch", "agent/upstream-pending-create-lease"),
    ("gc.routed_to", "blog/codex"), ("gc.work_dir", "/other"),
])
def test_old_recovery_metadata_never_authorizes_fresh_route(task, key, value):
    after = routed(task)
    after["metadata"][key] = value
    with pytest.raises(RuntimeError):
        c.validate_task(after, "routed")


def test_atomic_delta_checks_preserve_embedded_parent_snapshot(task):
    after = bound(task)
    after["dependencies"][0]["notes"] = "A concurrent update"
    with pytest.raises(RuntimeError):
        c.validate_binding_delta(task, after)
    before = bound(task)
    after = routed(task)
    after["dependencies"][0]["notes"] = "A concurrent update"
    with pytest.raises(RuntimeError):
        c.validate_route_delta(before, after)


def test_fresh_preroute_requires_exact_two_policies():
    c.validate_rule_status(rules())
    for extra in (b"?? .codex/hooks.json\0", b"!! .gc/settings.json\0",
                  b"!! .gc/worker-evidence/ga-jcxb/r1/startup.json\0",
                  b" M unrelated\0", rules()):
        with pytest.raises(RuntimeError):
            c.validate_rule_status(rules() + extra)
    for raw in (b"", rules()[:-1], rules().split(b"\0")[0] + b"\0"):
        with pytest.raises(RuntimeError):
            c.validate_rule_status(raw)


def test_post_terminal_scope_and_evidence():
    result = c.candidate_status(candidate())
    assert result["source"] == sorted(c.SOURCE_PATHS)
    assert result["rules"] == sorted(c.RULES)
    assert result["evidence"] == [c.EVIDENCE_ROOT + "report.json"]
    runtime = b"".join((b"?? " if p == ".codex/hooks.json" else b"!! ") + p.encode() + b"\0"
                       for p in sorted(c.RUNTIME_FILES))
    assert c.candidate_status(candidate() + runtime)["runtime"] == sorted(c.RUNTIME_FILES)


@pytest.mark.parametrize("extra", [
    b"M  source.py\0", b" M unrelated.py\0", b" D .gitignore\0",
    b"!! .codex/rules/extra.rules\0", b"?? .gc/settings.json.backup\0",
    b"!! .gc/worker-evidence/ga-e0t1.20/r11/startup.json\0",
    b"!! .gc/worker-evidence/ga-jcxb/r0/startup.json\0",
    b"?? .gc/worker-evidence/ga-jcxb/r1/../outside\0",
    b"?? .gc/worker-evidence/ga-jcxb/r1//empty\0",
    b"?? .gc/worker-evidence/ga-other/report.json\0", b"?? /absolute\0",
])
def test_post_terminal_extra_paths_refuse(extra):
    with pytest.raises(RuntimeError):
        c.candidate_status(candidate() + extra)


def test_post_terminal_requires_changes_unique_rows_and_bounded_evidence():
    for raw in (rules(), candidate()[:-1], candidate() + candidate(),
                candidate().replace(b"?? ", b"A  ", 1)):
        with pytest.raises(RuntimeError):
            c.candidate_status(raw)
    many = candidate() + b"".join(b"?? " + c.EVIDENCE_ROOT.encode() + str(i).encode() + b".txt\0"
                                 for i in range(128))
    with pytest.raises(RuntimeError):
        c.candidate_status(many)
    for paths in ([], [c.SOURCE_PATHS[0]] * 2, ["city.toml"],
                  [c.SCOPE_ROOT + "pins.json"], [c.SCOPE_ROOT + "make_pins.py"]):
        with pytest.raises(RuntimeError):
            c.require_source_scope(paths)


def session():
    return dict(id="ci-new", session_name="codex-ci-new", template=c.TARGET,
                rig="gascity", provider=c.PROVIDER, work_dir=c.WORK, worker_dir=c.WORK,
                created_at="2026-09-29T12:00:00Z", closed=False)


def test_exact_claim_and_unclaimed_close(task):
    s = session()
    unclaimed = routed(task)
    c.close_claim(unclaimed, s, unclaimed)
    with pytest.raises(RuntimeError):
        c.close_claim(unclaimed, s)
    claimed = copy.deepcopy(unclaimed)
    claimed.update(status="in_progress", assignee=s["session_name"])
    claimed["metadata"].update({"gc.session_id": s["id"], "gc.session_name": s["session_name"]})
    c.close_claim(claimed, s)
    for key, value in (("gc.session_id", "ci-old"), ("gc.session_name", "codex-ci-old"),
                       ("gc.work_dir", "/wrong"), ("gc.routed_to", "blog/codex")):
        changed = copy.deepcopy(claimed)
        changed["metadata"][key] = value
        with pytest.raises(RuntimeError):
            c.close_claim(changed, s)


def test_predecessor_runtime_and_session_functions_are_byte_equivalent():
    old = HERE.parent / "ga-e0t1-20-astra-window/contract.py"
    raw = old.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "55655618cb4c92c6729467b39f2eab869c8fb115b3707c37f8300735c1a0dd10"
    before = {n.name: ast.dump(n) for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}
    after = {n.name: ast.dump(n) for n in ast.parse((HERE / "contract.py").read_bytes()).body
             if isinstance(n, ast.FunctionDef)}
    for name in ("close_identity", "close_census", "running_rows"):
        assert after[name] == before[name]
    m = types.ModuleType("prior")
    exec(compile(raw, str(old), "exec"), m.__dict__)
    assert c.RUNTIME_IMAGE == m.RUNTIME_IMAGE
    assert c.RULES == m.RULES and c.DEFAULT_RULES == m.DEFAULT_RULES


def test_no_live_mutations_are_present():
    tree = ast.parse((HERE / "contract.py").read_bytes())
    imports = {n.names[0].name for n in tree.body if isinstance(n, ast.Import)}
    assert imports == {"hashlib", "json", "re", "stat"}
    assert "ci-9dp7z" not in (HERE / "contract.py").read_text()


def test_exact_native_parent_rejects_missing_duplicate_or_added_predecessor(task):
    task["dependencies"].reverse()
    c.validate_task(task, "unbound")
    for replacement in (
        [],
        [task["dependencies"][0], task["dependencies"][0]],
        task["dependencies"] + [{"id": "ga-9olv", "dependency_type": "relates-to"}],
    ):
        bad = copy.deepcopy(task)
        bad["dependencies"] = replacement
        with pytest.raises(RuntimeError):
            c.validate_task(bad, "unbound")
