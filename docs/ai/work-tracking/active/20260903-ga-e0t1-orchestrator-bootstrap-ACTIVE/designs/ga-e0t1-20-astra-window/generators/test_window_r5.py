"""Whole R5 generated operational package; no lifecycle or worker execution."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import types

import pytest

import window_r5 as r

CACHE=1790591514698290119


@pytest.fixture(scope='module')
def built():return r.assemble(CACHE)


def mod(raw,name='generated'):
    return r.startup.source_module(raw,name)


def test_deterministic_native_preparation_and_frozen_history(built):
    before,out=built
    assert r.assemble(CACHE)==built
    p=r.prep();w=mod(out['window-base-r11.py'])
    assert str(w.PREP)==r.startup.PREP and w.CITY_SHA[1]==p['city_after_sha256']
    assert w.RECEIPT_SHA[1]==p['receipt_after_sha256'] and w.REVISION[1]==p['revision_after']
    assert str(w.ACCEPTED)==r.startup.PRIOR_TERMINAL+'/observed-after.json'
    assert w.ACCEPTED_SHA==r.startup.PRIOR_OBSERVATION
    assert w.CACHE_PINNED_NS==CACHE and w.CACHE_PREV_NS==CACHE
    assert out['legacy-continuation-r4.py']==before['continuation-admission.py']
    assert out['stranded-recovery.py']==before['stranded-recovery.py']
    assert out['PRECLAIM-R5.md']==(r.build.O/r.build.NEW/'PRECLAIM-R5.md').read_bytes()
    assert out['prompt-prep-r5.py']==(r.build.O/r.build.NEW/'prompt-prep-r5.py').read_bytes()


@pytest.mark.parametrize('cache',[None,False,CACHE-1,'unknown'])
def test_unbound_or_regressed_cache_refuses(cache):
    with pytest.raises(AssertionError):r.assemble(cache)


def test_no_completed_entry_can_replay_and_shells_parse(built,tmp_path):
    out=built[1]
    for name in ('operator/BIND.sh','operator/ROUTE.sh','operator/PROMPT-PREP-R5.sh'):
        assert b'exit 125' in out[name].split(b'\n',4)[0:4]
    for name,raw in out.items():
        if name.endswith('.sh'):
            p=tmp_path/Path(name).name;p.write_bytes(raw)
            assert subprocess.run(['/bin/sh','-n',str(p)]).returncode==0
    assert b'--append-notes' in out['startup-amendment-r5.py']
    assert b'--claim' not in out['startup-amendment-r5.py']
    assert b'sling' not in out['startup-amendment-r5.py']


def test_every_executable_binding_tracks_new_bytes_not_historical_notes(built):
    before,out=built
    w=out['window-base-r11.py'].decode()
    for name in ('contract.py','worker-startup.py','continuation-admission.py','launch-contract-r5.py'):
        assert r.sha(out[name]) in w,name
    a=mod(out['startup-amendment-r5.py'])
    assert a.BASE_SHA==r.sha(out['window-base-r11.py'])
    assert a.LEGACY_SHA==r.sha(out['legacy-continuation-r4.py'])
    assert a.CONTRACT_SHA==r.sha(out['startup-amendment-contract-r5.py'])
    assert a.AMENDMENT_SHA==r.sha(out['startup-amendment-r5.json'])
    assert r.sha(out['startup-amendment-r5.py']).encode() in out['operator/AMEND-STARTUP-R5.sh']
    old=mod(before['contract.py']);new=mod(out['contract.py'])
    assert new.BOUND_NOTE.startswith(old.BOUND_NOTE+'\n')
    assert old.RULES==new.RULES and old.SOURCE_PATHS==new.SOURCE_PATHS
    for name,raw in out.items():
        assert b'WINDOW_BASE_SHA' not in raw and b'AMENDMENT_EXECUTOR_SHA' not in raw,name


def test_restored_inventory_does_not_accept_a_new_baseline(built):
    w=built[1]['window-base-r11.py'].decode()
    assert str(r.OLD_WORKSPACE) in w and r.OLD_WORKSPACE_SHA in w
    assert 'launch.initial_runtime_image(restored,workspace_before,contract().RUNTIME_IMAGE)' in w
    assert 'probe.verified_hook()' in w
    helper=mod(built[1]['launch-contract-r5.py'])
    before=json.loads(r.OLD_WORKSPACE.read_bytes())
    runtime=mod(built[1]['contract.py']).RUNTIME_IMAGE
    after=dict(before,**runtime)
    helper.initial_runtime_image(before,after,runtime)
    changed=copy.deepcopy(after);changed['surprise']=dict(mode=0o600,type=32768,size=0,sha256='x')
    with pytest.raises(RuntimeError):helper.initial_runtime_image(before,changed,runtime)


def test_continuation_requires_exact_append_before_admission(built):
    text=built[1]['continuation-admission.py'].decode()
    assert 'exact.accepted(before_amend,after_amend,applied,amendment,compare_pair)' in text
    assert 'compare_pair(current,after_amend,parent_audit=True)' in text
    assert 'compare_pair(current, w.record(\'admitted-pair.json\'))' in text
    assert 'completed-inputs.json' in text
    assert r.sha(built[1]['startup-amendment-contract-r5.py']) in text


def test_torn_read_is_only_retried_inside_the_original_deadline(built,monkeypatch):
    w=mod(built[1]['window-base-r11.py'],'loop_fixture')
    helper=mod(built[1]['launch-contract-r5.py'],'loop_helper')
    status=dict(ok=True,agents=[dict(running=False)],summary=dict(active_sessions=1,running_agents=0))
    census=dict(ok=True,sessions=[],summary=dict(total=0,active=0,suspended=0,closed=0))
    final=copy.deepcopy(status);final['summary']['active_sessions']=0
    observations=iter([status,census,final,census]);calls=[];saved={};checks=[]
    endpoint=dict(pin=dict(metadata={}))
    s=types.SimpleNamespace(image=lambda value:{})
    w.module=lambda path,pin:s if path.name=='suspension-lineage.py' else helper
    w.suspension_record=lambda o:endpoint
    w.save=lambda name,value:saved.setdefault(name,value)
    w.suspension_read_equal=lambda a,b:True
    w.suspension_atime_stable=lambda *args:True
    w.active_epoch=lambda o:None
    def phase(name,argv,*args,**kwargs):
        calls.append((name,argv))
        return {'stdout':json.dumps(next(observations))}
    w.phase=phase
    def validate(value,*args,**kwargs):
        checks.append(value);assert value==final
        return True
    w.suspension_status_matches=validate
    ticks=iter(range(30))
    monkeypatch.setattr(w,'time',types.SimpleNamespace(monotonic=lambda:next(ticks),sleep=lambda n:None,time_ns=lambda:0))
    monkeypatch.setattr(w,'os',types.SimpleNamespace(ST_NOATIME=1024,ST_RELATIME=4096,
        statvfs=lambda path:types.SimpleNamespace(f_flag=1024)))
    assert w.observed_suspension_endpoint('city-suspend',None,None,None)==endpoint
    assert len(calls)==4 and len(checks)==1 and w.BARRIER_SECONDS==90
    assert all('resume' not in argv and 'suspend' not in argv for _,argv in calls)
    assert 'suspension-city-suspend-torn-read-0.json' in saved


def test_create_only_complete_package(built,tmp_path):
    root=tmp_path/'assembled';r.main(str(root),str(CACHE))
    m=json.loads((root/'assembly.json').read_bytes())
    assert m['execution_admitted'] is False and m['completed_operations_replayed'] is False
    assert m['files']=={n:r.sha(raw) for n,raw in built[1].items()}
    with pytest.raises(AssertionError):r.main(str(root),str(CACHE))
