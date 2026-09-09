"""Fixed caller: real Git/ownership/readiness/sync/WAL, disposable repositories.

Beads transport, runtime observations and the Go subprocess are synthetic. Source
binding has separate real-Git tests with signature verification explicitly stubbed;
these are not production crypto, service or Core documentation acceptance.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / "scripts"))
sys.path.insert(0, str(SOURCE / "plugins/gas-city-workflow/scripts"))

import _core_layout_apply as caller
from _core_layout_state import RelocationError, canonical, digest, freeze, inspect
from tests.meta_workflow_guard.test_core_layout_transaction import originals, snapshot
from tests.meta_workflow_guard.test_gas_city_workflow_transitions import _bead, _run
from tests.meta_workflow_guard.test_workflow_portable_source import PortableRunner, portable_project
from aegis_foundation.gate.session_transition import SessionTransition
from project_context import build_context
from workflow_begin import begin
from workflow_lock import workflow_lock
import workflow_common
import workflow_ownership


DOC_COMMAND = [caller.GO, "test", "-json", "-count=1", "./test/docsync"]
GOOD_EVENTS = '{"Action":"pass","Test":"TestDocumentation"}\n{"Action":"pass","Package":"fixture/test/docsync"}\n'


class CallerRunner(PortableRunner):
    def __init__(self):
        super().__init__(_bead(bead_id=caller.BEAD))
        self.doc_calls = []
        self.doc_result = (0, GOOD_EVENTS, "")

    def run(self, argv, *, cwd=None, env=None, check=True):
        if list(argv) == DOC_COMMAND:
            self.doc_calls.append((list(argv), cwd, env, check))
            return subprocess.CompletedProcess(argv, *self.doc_result)
        return super().run(argv, cwd=cwd, env=env, check=check)


def old_image(value):
    result = dict(value)
    if "mode" in result:
        result["mode"] = oct(result["mode"])
    if result["kind"] == "link":
        result["kind"] = "symlink"
    return result


def baseline_for(plan):
    return {
        "schema": "ga-ecwh.layout-relocation-review-inventory.v1",
        **{key: plan[key] for key in ("root", "head", "branch", "tracked_diff_sha256")},
        "maps": [{"source": a, "destination": b} for a, b in plan["moves"]],
        "entries": [{"source": path, **old_image(value)} for path, value in plan["entries"].items()],
        "protected": {path: old_image(value) for path, value in plan["protected"].items()},
        "session_wal": {path: old_image(value) for path, value in plan["wal_before"].items() if value["kind"] == "file"},
        "index": {"path": plan["external"]["index"]["path"], **old_image(plan["external"]["index"]["image"])},
        "journal": {"path": plan["external"]["ownership"]["path"], **old_image(plan["external"]["ownership"]["image"])},
    }


@pytest.fixture
def bound(tmp_path, monkeypatch):
    canonical_root, registry = portable_project(tmp_path)
    descriptor = canonical_root / ".gas-city-workflow.json"
    data = json.loads(descriptor.read_text())
    data.update(id="gas-city", rig="gascity")
    descriptor.write_text(json.dumps(data))
    _run(canonical_root, "git", "add", ".gas-city-workflow.json")
    _run(canonical_root, "git", "commit", "-m", "Fixture Core identity")
    # Redirect only registry resolution to this disposable project. All actual
    # workspace, journal, ownership and readiness validators still execute.
    for module in (workflow_common, workflow_ownership):
        monkeypatch.setattr(module, "build_context", lambda root, ignored: build_context(root, registry))
    runner = CallerRunner()
    started = begin(canonical_root, caller.BEAD, slug="fixture", goals=["Relocate evidence"],
                    registry=registry, runner=runner)
    root = Path(started["spec"]["worktree"])
    # begin() is below the CLI lock wrapper; seed its existing lock exactly as
    # a real CLI entry would, before freezing the fixture baseline.
    with workflow_lock(runner, root, registry):
        pass
    (root / "engdocs").mkdir()
    for data in (b"first", b"second"):
        path = root / ".aegis/seed"
        with SessionTransition(root, caller.BEAD, [path]) as txn:
            txn.write(path, data)
    runtime = {"fixture": "stable-observation"}
    tools = {"fixture": "stable-toolchain"}
    monkeypatch.setattr(caller, "observe", lambda runner: copy.deepcopy(runtime))
    monkeypatch.setattr(caller, "tool_pins", lambda: copy.deepcopy(tools))
    source_calls = []
    execution = caller.BoundExecution(root, SOURCE, {"fixture": "source-identity"},
                                     lambda: source_calls.append(True), runner=runner, registry=registry)
    plan = freeze(root, caller.BEAD, "a" * 64, ["AGENTS.md"])
    baseline = baseline_for(plan)
    return execution, baseline, runtime, tools, source_calls


def prepare(execution, baseline):
    return execution.prepare(baseline, digest(canonical(baseline)))


def test_complete_caller_real_helpers_then_read_only_replay(bound, capsys):
    execution, baseline, _, _, source_calls = bound
    root = execution.root
    before = snapshot(root)
    bundle = prepare(execution, baseline)
    assert snapshot(root) == before
    capsys.readouterr()
    result = execution.apply(bundle)
    assert capsys.readouterr().out == ""
    assert result["status"] == "PASS" and result["idempotent"] is False
    plan = bundle["plan"]
    for item in plan["external"].values():
        assert inspect(Path(item["path"])) == item["image"]
    directory = Path(plan["common"]) / "gas-city-workflow/layout-relocations" / plan["plan_id"]
    record = json.loads((directory / "transaction.json").read_text())
    assert record["postflight"]["tests_passed"] == 1
    assert record["postflight"]["stdout"] == GOOD_EVENTS
    assert record["plan_sync_stdout"]
    assert len(execution.runner.doc_calls) == 1
    argv, cwd, env, check = execution.runner.doc_calls[0]
    assert argv == DOC_COMMAND and cwd == root and check is False
    assert {key: env[key] for key in ("GOTOOLCHAIN", "GOPROXY", "GOSUMDB", "GOFLAGS")} == {
        "GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOFLAGS": "-mod=readonly"}
    before, audit = snapshot(root), snapshot(directory)
    assert execution.apply(bundle)["idempotent"] is True
    assert snapshot(root) == before and snapshot(directory) == audit
    assert len(execution.runner.doc_calls) == 1 and len(source_calls) >= 6
    assert not any("verify" in call and "workflow.py" in str(call) for call in execution.runner.calls)


@pytest.mark.parametrize("failure", ["nonzero", "malformed", "skip", "empty", "nonobject"])
def test_docsync_failure_preserves_output_and_restores_all_moves(bound, failure):
    execution, baseline, *_ = bound
    bundle = prepare(execution, baseline)
    cases = {
        "nonzero": (1, GOOD_EVENTS, "injected documentation failure"),
        "malformed": (0, "not-json\n", "parser evidence"),
        "skip": (0, GOOD_EVENTS + '{"Action":"skip","Test":"Skipped"}\n', ""),
        "empty": (0, "", ""), "nonobject": (0, "[]\n", ""),
    }
    execution.runner.doc_result = cases[failure]
    with pytest.raises((RelocationError, ValueError)):
        execution.apply(bundle)
    plan = bundle["plan"]
    directory = Path(plan["common"]) / "gas-city-workflow/layout-relocations" / plan["plan_id"]
    record = json.loads((directory / "transaction.json").read_text())
    assert record["status"] == "rolled_back"
    assert record["docsync_attempt"]["stdout"] == cases[failure][1]
    assert record["docsync_attempt"]["stderr"] == cases[failure][2]
    assert originals(execution.root, plan) == plan["entries"]
    assert not (execution.root / ".codex").exists()
    assert (directory / "failed-postimages.json").is_file()


@pytest.mark.parametrize("kind", ["runtime", "tools", "source", "baseline", "policy"])
def test_refuses_drift_before_relocation(bound, kind):
    execution, baseline, runtime, tools, _ = bound
    bundle = prepare(execution, baseline)
    if kind == "runtime":
        runtime["fixture"] = "changed"
    elif kind == "tools":
        tools["fixture"] = "changed"
    elif kind == "source":
        def changed():
            raise RelocationError("source changed")
        execution.source_check = changed
    elif kind == "policy":
        bundle["baseline_sha256"] = "f" * 64
    else:
        baseline["entries"][0]["mode"] = "0o777"
    before = snapshot(execution.root)
    with pytest.raises(RelocationError):
        prepare(execution, baseline) if kind == "baseline" else execution.apply(bundle)
    assert snapshot(execution.root) == before
    directory = Path(bundle["plan"]["common"]) / "gas-city-workflow/layout-relocations"
    assert not directory.exists()
    assert execution.runner.doc_calls == []


def test_prepare_refuses_missing_lock_without_creating_it(bound):
    execution, baseline, *_ = bound
    common = caller.external_paths(execution.root, caller.BEAD)["common"]
    lock = common / "gas-city-workflow/source-transition.lock"
    lock.unlink()  # Disposable fixture only.
    with pytest.raises(RelocationError, match="existing workflow lock"):
        prepare(execution, baseline)
    assert not lock.exists()


@pytest.mark.parametrize("lock_kind", ["workflow", "session"])
def test_existing_locks_prevent_mutation(bound, lock_kind):
    from aegis_foundation.gate.session_transition import session_lock
    from aegis_foundation.gate.session_authority import SessionAuthorityError
    from workflow_common import WorkflowError
    execution, baseline, *_ = bound
    bundle = prepare(execution, baseline)
    before = snapshot(execution.root)
    held = (workflow_lock(execution.runner, execution.root, execution.registry)
            if lock_kind == "workflow" else session_lock(execution.root))
    expected = WorkflowError if lock_kind == "workflow" else SessionAuthorityError
    with held, pytest.raises(expected, match="active|in use"):
        execution.apply(bundle)
    assert snapshot(execution.root) == before


@pytest.mark.parametrize("bad", [None, "rig", "extra", "sessions", "restart", "stopped"])
def test_actual_observer_schema_and_negative_states(bad):
    rigs = {"ok": True, "rigs": [
        {"name": name, "hq": False, "suspended": True, "running": False}
        for name in ("gascity", "gas-city-template", "hpfetcher", "blog")]}
    sessions = {"ok": True, "sessions": [], "summary": {"total": 0}}
    state = {"MainPID": str(os.getpid()), "NRestarts": "0", "ExecMainStartTimestampMonotonic": "1",
             "ActiveState": "active", "SubState": "running"}
    if bad == "rig":
        rigs["rigs"][0]["suspended"] = False
    elif bad == "extra":
        rigs["rigs"].append(dict(rigs["rigs"][0]))
    elif bad == "sessions":
        sessions["sessions"].append({"id": "unexpected"})
    elif bad == "restart":
        state["NRestarts"] = "1"
    elif bad == "stopped":
        state["MainPID"] = "0"

    class ObserverRunner:
        def run(self, argv, **kwargs):
            assert "GC_HOME" in kwargs["env"]
            if "rig" in argv:
                assert argv == [caller.GC, "--city", caller.CITY, "rig", "list", "--json"]
                output = json.dumps(rigs)
            elif "session" in argv:
                assert argv == [caller.GC, "--city", caller.CITY, "session", "list", "--json"]
                output = json.dumps(sessions)
            else:
                assert argv[:4] == ["/usr/bin/systemctl", "--user", "show", caller.SUPERVISOR]
                output = "\n".join(f"{key}={value}" for key, value in state.items())
            return subprocess.CompletedProcess(argv, 0, output, "")
    if bad is None:
        result = caller.observe(ObserverRunner())
        assert result["supervisor"]["boot_id"] and int(result["supervisor"]["start_ticks"]) > 0
    else:
        with pytest.raises(RelocationError):
            caller.observe(ObserverRunner())


def launcher_module():
    path = SOURCE / "scripts/core-evidence-layout"
    module = types.ModuleType("core_layout_launcher_test")
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


@pytest.mark.parametrize("kind", ["duplicate", "hash", "alias", "hardlink"])
def test_frozen_input_rejects_ambiguous_or_unbound_input(tmp_path, kind):
    module = launcher_module()
    path = tmp_path / "input.json"
    data = b'{"x":1,"x":2}' if kind == "duplicate" else b'{"x":1}'
    path.write_bytes(data)
    expected = "a" * 64 if kind == "hash" else digest(data)
    if kind == "alias":
        alias = tmp_path / "alias.json"
        alias.symlink_to(path)
        path = alias
    if kind == "hardlink":
        os.link(path, tmp_path / "other.json")
    with pytest.raises(ValueError):
        module.frozen_json(path, expected)


def test_launcher_requires_isolated_start_before_any_repository_import(tmp_path):
    result = subprocess.run([sys.executable, str(SOURCE / "scripts/core-evidence-layout"), "apply",
                             "--source-head", "a" * 40, "--source-tree", "b" * 40,
                             "--input", str(tmp_path / "absent"), "--expect-input-sha256", "c" * 64],
                            capture_output=True, text=True)
    assert result.returncode == 2 and "requires python3 -I" in result.stderr


def test_isolated_python_loads_actual_sync_helper_without_user_site():
    code = '''
import os, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.dont_write_bytecode = True
sys.pycache_prefix = os.devnull
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONPYCACHEPREFIX"] = os.devnull
for path in (root, root / "scripts", root / "plugins/gas-city-workflow/scripts"):
    sys.path.insert(0, str(path))
from _core_layout_apply import load_sync_source
assert callable(load_sync_source(root).handle_plan_sync)
assert sys.flags.isolated == 1 and sys.flags.no_user_site == 1
print("isolated-helper-load-pass")
'''
    result = subprocess.run(["/usr/bin/python3", "-I", "-c", code, str(SOURCE)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "isolated-helper-load-pass"


@pytest.fixture
def signed_source_fixture(tmp_path, monkeypatch):
    """Real Git object/runtime verification; signature and launch flags simulated."""
    module = launcher_module()
    root = tmp_path / "source"
    for relative in (module.VERIFIER, "scripts/core-evidence-layout", *module.CONFIGS):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((SOURCE / relative).read_bytes())
    _run(root, "git", "init", "-b", "main")
    _run(root, "git", "add", ".")
    _run(root, "git", "commit", "-m", "Unsigned source fixture")
    _run(root, "git", "remote", "add", "origin", "https://github.com/loucmane/gas-city-operations.git")
    head = _run(root, "git", "rev-parse", "HEAD").stdout.strip()
    tree = _run(root, "git", "rev-parse", "HEAD^{tree}").stdout.strip()
    _run(root, "git", "update-ref", "refs/remotes/origin/main", head)
    module.ALLOWED_SOURCES = {root}
    module.sys = types.SimpleNamespace(flags=types.SimpleNamespace(isolated=1, no_site=1),
                                      executable=sys.executable, version_info=sys.version_info)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(sys, "pycache_prefix", os.devnull)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONPYCACHEPREFIX", os.devnull)
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)
    monkeypatch.delenv("GIT_CONFIG_SYSTEM", raising=False)
    real_git = module.git
    calls = []
    def signature_stub(source, *args):
        calls.append(args)
        return b"" if args[0] == "verify-commit" else real_git(source, *args)
    module.git = signature_stub
    return module, root, head, tree, calls


def test_source_binding_checks_real_git_runtime_and_configuration(signed_source_fixture):
    module, root, head, tree, calls = signed_source_fixture
    result = module.source_binding(root, head, tree)
    assert result["head"] == head and result["tree"] == tree
    assert ("verify-commit", "--raw", head) in calls
    assert set(result["configs"]) == set(module.CONFIGS)


@pytest.mark.parametrize("kind", ["source", "config", "head", "tree", "signature", "environment", "mode", "untracked"])
def test_source_binding_refuses_each_drift(signed_source_fixture, monkeypatch, kind):
    module, root, head, tree, _ = signed_source_fixture
    if kind == "source":
        (root / "scripts/core-evidence-layout").write_text("raise RuntimeError('not executed')")
    elif kind == "config":
        (root / module.CONFIGS[0]).write_text("{}")
    elif kind == "mode":
        (root / "scripts/core-evidence-layout").chmod(0o755)
    elif kind == "untracked":
        (root / "scripts/hidden.py").write_text("raise RuntimeError('not executed')")
    elif kind == "head":
        head = "a" * 40
    elif kind == "tree":
        tree = "b" * 40
    elif kind == "environment":
        monkeypatch.setenv("GIT_WORK_TREE", str(root))
    else:
        original = module.git
        def refuse(source, *args):
            if args[0] == "verify-commit":
                raise ValueError("source signature verification failed")
            return original(source, *args)
        module.git = refuse
    with pytest.raises(ValueError):
        module.source_binding(root, head, tree)
