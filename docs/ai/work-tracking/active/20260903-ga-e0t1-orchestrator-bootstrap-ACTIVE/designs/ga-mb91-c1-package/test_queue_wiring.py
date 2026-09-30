"""Actual generated call-order tests; offline only, no window execution."""
import ast
import hashlib
from pathlib import Path
import types
import pytest

HERE=Path(__file__).parent

def load(name):
    m=types.ModuleType(name);m.__file__=str(HERE/name)
    exec(compile((HERE/name).read_bytes(),m.__file__,'exec'),m.__dict__)
    return m

def test_generated_helper_precedes_entrypoint_and_exact_guard_is_bound():
    text=(HERE/'window-base.py').read_text()
    assert text.index('def foreign_queue(')<text.index("if __name__=='__main__':")
    assert hashlib.sha256((HERE/'queue-guard.py').read_bytes()).hexdigest() in text
    w=load('window-base.py');calls=[]
    w.module=lambda path,pin:types.SimpleNamespace(checkpoint=lambda *a,**k:calls.append((a,k)))
    w.foreign_queue('probe','b','o','owned',fatal=False)
    args,kwargs=calls[0]
    assert args[1:]==('probe','b','o','owned') and kwargs=={'fatal':False}
    assert args[0].ROOT==w.ROOT

@pytest.mark.parametrize('action,fatal',[('rig-resume',True),('city-resume',True),
                                         ('city-suspend',False),('rig-suspend',False)])
def test_real_generated_post_transition_call_never_blocks_containment(action,fatal):
    tree=ast.parse((HERE/'window-base.py').read_bytes())
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='lifecycle')
    call=next(n for n in f.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
              and isinstance(n.value.func,ast.Name) and n.value.func.id=='foreign_queue')
    seen=[]
    def guard(*args,**kwargs):
        seen.append((args,kwargs))
        if kwargs['fatal']:raise RuntimeError('fixture drift')
        return {'ok':False}
    ns=dict(action=action,b='b',o='o',owned='owned',foreign_queue=guard)
    code=compile(ast.Module(body=[call],type_ignores=[]),'actual_lifecycle_tail','exec')
    if fatal:
        with pytest.raises(RuntimeError,match='fixture drift'):exec(code,ns)
    else:exec(code,ns)
    assert seen==[((action+'-after','b','o','owned'),{'fatal':fatal})]

def test_early_capture_and_all_lifecycle_boundaries_are_wired():
    text=(HERE/'window-base.py').read_text()
    assert text.index("foreign_queue('preflight'")<text.index("save('preflight-pass.json'")
    assert text.index("foreign_queue('stage-before'")<text.index("save('stage-consumed.json'")
    assert text.index("foreign_queue('stage-after'")<text.index("save('stage-pass.json'")
    assert text.index("foreign_queue('restore-before'")<text.index("save('restore-consumed.json'")
    assert text.index("foreign_queue('restore-after'")<text.index("save('restore-pass.json'")
    assert "if action.endswith('resume'):foreign_queue(action+'-before'" in text
    release=(HERE/'release-runtime-r13.py').read_text()
    assert release.index("w.foreign_queue('release-before'")<release.index("result = command('enqueue'")
    assert "w.foreign_queue('release-observe-'" in release
    assert "w.foreign_queue('restore-admission'" in (HERE/'restore-admission-r3.py').read_text()
    terminal=(HERE/'observe-terminal-r11.py').read_text()
    assert "w.foreign_queue('terminal-before'" in terminal and "w.foreign_queue('terminal-after'" in terminal

def test_shadow_failure_before_release_cannot_enqueue(monkeypatch):
    from test_runtime import harness,r
    run,calls,saved=harness(monkeypatch)
    original=r.execute
    def wrapped(w,*args):
        def refusal(*a,**k):raise RuntimeError('foreign shadow drift')
        w.foreign_queue=refusal
        return original(w,*args)
    monkeypatch.setattr(r,'execute',wrapped)
    with pytest.raises(RuntimeError,match='foreign shadow drift'):run()
    assert not any(c[3:5]==['session','nudge'] for c in calls)
    assert 'delivery-enqueued.json' not in saved
