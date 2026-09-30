"""R2 packaging regressions only; no control-plane or live operation."""
import ast
import hashlib
from pathlib import Path
import types
import pytest
HERE=Path(__file__).parent
a=types.ModuleType("r2_assembly");a.__file__=str(HERE/"window-assembly.py")
exec(compile((HERE/"window-assembly.py").read_bytes(),a.__file__,"exec"),a.__dict__)
PARAMS=dict(observation="/tmp/ga-goo5-readonly-baseline-20260930-r2/observed.json",observation_sha="a"*64,cache_ns=1790731796031801386)

def test_completed_binding_is_preserved_and_route_binds_actual_executor():
    _,out=a.assemble(**PARAMS)
    pin="44c8db6cc3ef3a2a3616b5ea60c5ee8ccb983ee1844859058e5b297177c16c12"
    assert hashlib.sha256(out["bind-task.py"]).hexdigest()==pin
    route=out["route-task.py"].decode()
    assert "BIND_SHA = '"+pin+"'" in route or "BIND_SHA='"+pin+"'" in route
    assert "ga-goo5-bind-20260930-r1" in route

def test_completed_binding_drift_refuses(monkeypatch):
    original=Path.read_bytes
    def changed(path):
        raw=original(path)
        return raw+b"\n" if path==HERE/"bind-task.py" else raw
    monkeypatch.setattr(Path,"read_bytes",changed)
    with pytest.raises(ValueError,match="completed BIND source drift"):
        a.assemble(**PARAMS)

def test_only_consumed_observation_root_advances():
    _,out=a.assemble(**PARAMS)
    assert b"/var/tmp/ga-goo5-integrity-20260930-r2" in out["observe-integrity-r11.py"]
    assert b"/var/tmp/ga-goo5-integrity-20260930-r1" not in out["observe-integrity-r11.py"]
    assert b"/var/tmp/ga-goo5-window-20260930-r1" in out["window-base.py"]
    assert b"/var/tmp/ga-goo5-prep-20260930-r1" in out["window-base.py"]

def test_failed_latch_helper_has_one_exact_attempt_and_two_evidence_pins():
    raw=(HERE/"preserve-observe-refusal.py").read_text()
    tree=ast.parse(raw)
    literal={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            try: literal[n.targets[0].id]=ast.literal_eval(n.value)
            except (ValueError,TypeError): pass
    assert literal["JOB_COMMITS"]=={"ga-goo5-observe-r1":"a5e924eb7c9a406b6b2475970d75e8a5730f818a"}
    assert literal["EXPECTED_EXIT"]==1
    assert literal["expected"]=={
        "intent.json":"3415e29c59d50c143ae66a66135b7101b616376d80698a897a6f6d8ab0526829",
        "before-refused-observation.json":"3f97554b5355ffd1bb5469b8388a1c17f334ebd874844aecba2757e8c34fe625"}
    assert "window already started" in raw and "task already routed" in raw
    assert "unit_state_after" in raw and "renameat2" in raw
    assert "submit_job" not in raw
