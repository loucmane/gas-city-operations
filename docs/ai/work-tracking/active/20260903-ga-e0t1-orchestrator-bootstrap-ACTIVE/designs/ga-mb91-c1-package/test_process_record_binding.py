"""Operational record binding and before-mutation order; all runtime tests use fixtures."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import types

import pytest

HERE = Path(__file__).parent


def load(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def generated():
    assembler = load(HERE / "window-assembly.py", "assembly_process_test")
    return assembler.assemble(
        observation="/tmp/ga-mb91-readonly-baseline-20260930-r2/observed.json",
        observation_sha="a" * 64, cache_ns=1790766204990519059)[1]


def test_route_uses_fresh_record_not_preserved_old_epoch():
    tree = ast.parse(generated()["route-task.py"])
    values = {node.targets[0].id: node.value for node in tree.body
              if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    assert ast.literal_eval(values["RECORD"].args[0]) == "/tmp/ga-mb91-process-record-20260930-r1.json"
    assert ast.literal_eval(values["RECORD_SHA"]) == "10b956a5458bb88443789cf3fbde1c1abdf99dbcaabc542fa92369db0679e086"


def test_stale_record_is_checked_before_preflight_root_and_stage_consumption():
    source = generated()["window-base.py"].decode()
    preflight = source.index("if action=='preflight':")
    stage = source.index("elif action=='stage':")
    restore = source.index("    else:\n        require((ROOT/'stage-consumed.json')")
    assert source.index("verify_process_record(o)", preflight) < source.index("ROOT.mkdir", preflight)
    assert stage < source.index("verify_process_record(o)", stage) < source.index("save('stage-consumed.json'", stage)
    assert "verify_process_record(o)" not in source[restore:]


@pytest.mark.parametrize("defect", [None, "pid", "start", "cgroup", "members", "hidden", "host-after"])
def test_actual_generated_check_keeps_live_identity_and_quiescence(defect):
    tree = ast.parse(generated()["window-base.py"])
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "verify_process_record"]
    assert len(functions) == 1
    function = ast.Module(body=functions, type_ignores=[])
    record = json.loads(Path("/tmp/ga-mb91-process-record-20260930-r1.json").read_bytes())
    calls = []
    def require(ok, message):
        if not ok:
            raise RuntimeError(message)
    def read(path, pin):
        assert str(path) == "/tmp/ga-mb91-process-record-20260930-r1.json"
        raw = Path(path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pin
        calls.append("pinned-record")
        return raw
    host_value = {"core": {"MainPID": "466463", "ExecMainStartTimestampMonotonic": "517633096016"}}
    def host(_):
        result = copy.deepcopy(host_value)
        if defect == "pid":
            result["core"]["MainPID"] = "2800348"
        if defect == "start" or defect == "host-after" and "city" in calls:
            result["core"]["ExecMainStartTimestampMonotonic"] = "517633106016"
        calls.append("host")
        return result
    def city(_, actual):
        calls.append("city")
        assert actual == record
        return [defect] if defect in {"cgroup", "members", "hidden"} else []
    pr = types.SimpleNamespace(RECORD_KEYS=set(record), user_slice=lambda uid: uid, city_problems=city)
    def module(path, pin):
        calls.append(Path(path).name)
        assert len(pin) == 64
        return pr if Path(path).name == "preroute.py" else object()
    ns = dict(module=module, read=read, host=host, require=require, Path=Path,
              json=json, os=types.SimpleNamespace(sysconf=lambda name: 100))
    exec(compile(function, "generated_process_fixture", "exec"), ns)
    if defect:
        with pytest.raises(RuntimeError):
            ns["verify_process_record"](object())
    else:
        ns["verify_process_record"](object())
        assert calls.count("host") == 2 and calls.count("city") == 1
        assert calls.index("candidate_git.py") < calls.index("preroute.py")


def test_successor_roots_fresh_and_completed_binding_unchanged():
    out = generated()
    assert b"ga-mb91-window-20260930-r3" in out["window-base.py"]
    assert b"ga-mb91-route-20260930-r2" in out["route-task.py"]
    assert b"ga-mb91-integrity-20260930-r5" in out["observe-integrity-r11.py"]
    assert b"ga-mb91-terminal-20260930-r2" in out["observe-terminal-r11.py"]
    assert hashlib.sha256(out["bind-task.py"]).hexdigest() == "028ccef1db747088c7f8552c86094ded85b5db12f1d58d890bd7678fa432adea"
