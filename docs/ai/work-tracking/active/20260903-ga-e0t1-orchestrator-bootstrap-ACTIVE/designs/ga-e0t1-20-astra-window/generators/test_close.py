"""Real generated CLOSE control flow, wholly mocked host commands and temp files."""
import copy
import importlib.util
import json
from pathlib import Path
import types

import pytest

HERE=Path(__file__).parent

def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

c=load('contract')

def session():
    return dict(id='ci-owned',session_name='codex-ci-owned',template=c.TARGET,rig='gascity',
        provider=c.PROVIDER,work_dir=c.WORK,worker_dir=None,created_at='2026-09-28T00:00:00Z',state='stopped')

def task(s):
    t=json.loads((HERE/'task-own-fields.json').read_bytes())
    t.update(id=c.TASK,status='in_progress',assignee=s['session_name'],metadata={
        'gc.work_dir':c.WORK,'gc.routed_to':c.TARGET,'gc.session_id':s['id'],'gc.session_name':s['session_name']})
    return t

@pytest.fixture(scope='module')
def source():return load('build').assemble(final=True)[1]['close-r11.py']

def run_fixture(source,tmp_path,rows,claim=None):
    m=types.ModuleType('generated_close');m.__file__=str(tmp_path/'close.py')
    exec(compile(source,m.__file__,'exec',dont_inherit=True),m.__dict__)
    m.VAR=tmp_path;m.WINDOW=tmp_path/'window';m.WINDOW.mkdir(exist_ok=True)
    (m.WINDOW/'suspension-rig-suspend-event.json').write_text('{}')
    commands=[];censuses=iter(rows)
    def phase(name,args,*unused,**kwargs):
        commands.append(args)
        if args[1:]==['session','list','--json']:
            return dict(stdout=json.dumps(dict(ok=True,sessions=next(censuses))))
        if 'show' in args:return dict(stdout=json.dumps([claim or task(session())]))
        if args[1:3]==['runtime','drain']:return dict(stdout='{}',exit_code=0)
        if args[1:3]==['session','close']:
            return dict(stdout=json.dumps(dict(ok=True,session_id=args[3])),exit_code=0)
        if args[0]=='/usr/bin/tmux':return dict(stdout='',stderr='no server running',exit_code=1)
        raise AssertionError(args)
    def read(path,*pins):
        return b'' if str(path)==m.__file__ else Path(path).read_bytes()
    w=types.SimpleNamespace(require=c.require,read=read,load_support=lambda:(None,None,None),
        active_epoch=lambda unused:None,complete_containment=lambda:None,contract=lambda:c,
        phase=phase,GC=['gc'],WORK=Path(c.WORK))
    def save(name,value):(w.ROOT/name).write_text(json.dumps(value))
    w.save=save;m.load=lambda:w;m._SOURCE_SHA='fixture-only';m.processes=lambda unused:[]
    m.time=types.SimpleNamespace(monotonic=lambda:1,sleep=lambda unused:None)
    return m,commands

def mutations(commands):return [a for a in commands if a[1:3] in (['runtime','drain'],['session','close'])]

def test_generated_close_mutates_only_bound_id_and_persists_it(source,tmp_path):
    s=session();m,commands=run_fixture(source,tmp_path,[[s],[s],[]]);m.main()
    assert [a[1:4] for a in mutations(commands)]==[['runtime','drain',s['id']],['session','close',s['id']]]
    saved=json.loads((tmp_path/'ga-e0t1.20-close-session.json').read_bytes())
    assert saved['session']==c.close_identity(s)

@pytest.mark.parametrize('key,value',[
    ('work_dir','/tmp/foreign'),('provider','claude'),('template','blog/codex'),
    ('rig','blog'),('id',''),('session_name',''),('created_at','')])
def test_wrong_initial_worker_never_receives_mutation(source,tmp_path,key,value):
    s=session();s[key]=value;m,commands=run_fixture(source,tmp_path,[[s]])
    with pytest.raises(RuntimeError):m.main()
    assert mutations(commands)==[]

def test_substituted_session_never_receives_close(source,tmp_path):
    s=session();other=dict(s,id='ci-other',session_name='codex-ci-other')
    m,commands=run_fixture(source,tmp_path,[[s],[other]])
    with pytest.raises(RuntimeError,match='substituted'):m.main()
    assert [a[1:4] for a in mutations(commands)]==[['runtime','drain',s['id']]]

def test_changed_task_claim_never_receives_drain(source,tmp_path):
    s=session();t=task(s);t['assignee']='foreign'
    m,commands=run_fixture(source,tmp_path,[[s]],t)
    with pytest.raises(RuntimeError,match='claim'):m.main()
    assert mutations(commands)==[]

def test_active_session_substitution_during_poll_never_retargets(source,tmp_path):
    s=dict(session(),state='active')
    other=dict(s,id='ci-other',session_name='codex-ci-other')
    m,commands=run_fixture(source,tmp_path,[[s],[other],[other]])
    with pytest.raises(RuntimeError,match='substituted'):m.main()
    assert [a[1:4] for a in mutations(commands)]==[['runtime','drain',s['id']]]
    assert list(tmp_path.glob('ga-e0t1.20-close-*/drain-poll-refused-*.json'))

def test_persistent_binding_prevents_retarget_on_later_invocation(source,tmp_path):
    s=session();saved=dict(schema='ga-e0t1.20.close-session.v1',task=c.TASK,session=c.close_identity(s))
    (tmp_path/'ga-e0t1.20-close-session.json').write_text(json.dumps(saved))
    other=dict(s,id='ci-replacement');m,commands=run_fixture(source,tmp_path,[[other]])
    with pytest.raises(RuntimeError,match='substituted'):m.main()
    assert mutations(commands)==[]

def test_extra_unrelated_session_refuses_without_filtering(source,tmp_path):
    s=session();m,commands=run_fixture(source,tmp_path,[[s,dict(s,id='ci-extra',template='blog/codex')]])
    with pytest.raises(RuntimeError,match='census'):m.main()
    assert mutations(commands)==[]

def test_published_release_identity_must_match(source,tmp_path):
    s=session();root=tmp_path/'ga-e0t1.20-startup-release-20260927-r1';root.mkdir()
    (root/'proof.json').write_text(json.dumps(dict(session=dict(s,id='ci-another'))))
    m,commands=run_fixture(source,tmp_path,[[s]])
    with pytest.raises(RuntimeError,match='released'):m.main()
    assert mutations(commands)==[]

def test_unclaimed_startup_failure_is_scoped_not_a_foreign_claim():
    s=session();t=task(s);t.update(status='open',assignee='')
    t['metadata']={'gc.work_dir':c.WORK,'gc.routed_to':c.TARGET}
    c.close_claim(t,s)
    t['metadata']['gc.session_id']='foreign'
    with pytest.raises(RuntimeError):c.close_claim(t,s)

def test_documented_order_satisfies_actual_stage_and_route_prerequisites(source):
    readme=(HERE.parent/'README.md').read_text()
    line=next(line for line in readme.splitlines() if line.startswith('1. BIND ->'))
    order=line.removeprefix('1. ').split('. Read')[0].split(' -> ')
    assert order==['BIND','OBSERVE','PREFLIGHT','STAGE','ROUTE','RESUME']
    generated=load('build').assemble(final=True)[1]
    route=generated['route-task-r5.py'].decode();base=generated['window-base-r11.py'].decode()
    assert route.index("'stage-pass.json'") < route.index("run('route',argv)")
    assert base.index("require(record('preflight-pass.json')") < base.index("save('stage-pass.json'")
    assert order.index('PREFLIGHT') < order.index('STAGE') < order.index('ROUTE') < order.index('RESUME')
