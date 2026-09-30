"""Offline successor, recovery, and negative binding checks. No launch."""
import copy
import json
from pathlib import Path
import subprocess
import types

import pytest
import recovered_claim_r10 as recovery
import workspace_r10 as workspace
import window_r10 as r
import ast


@pytest.fixture(scope='module')
def built():return r.assemble()


@pytest.fixture(scope='module')
def evidence():
    out={}
    for p,pin in recovery.PINS.items():
        raw=p.read_bytes();assert r.sha(raw)==pin;out[p]=json.loads(raw)
    return out


def test_exact_predecessor_and_deterministic_bindings(built):
    before,out=built;assert r.assemble()==built
    w=r.module(out['window-base-r11.py']);result=r.prep()
    assert str(w.PREP)==str(r.PREP) and str(w.ACCEPTED)==r.OBSERVATION
    assert w.ACCEPTED_SHA==r.OBSERVATION_SHA
    assert w.CITY_SHA[1]==result['city_after_sha256']
    assert w.RECEIPT_SHA[1]==result['receipt_after_sha256']
    assert w.REVISION[1]==result['revision_after']
    assert w.CACHE_PREV_NS==r.CACHE_PIN
    assert w.CACHE_PINNED_NS==r.CACHE_PIN
    for n in r.HISTORICAL & before.keys():assert before[n]==out[n],n
    for n in r.COMPLETED:assert b'exit 125' in out[n].splitlines()[:4],n
    for n in ('startup-amendment-r10.py','continuation-admission.py'):
        assert r.sha(out['recovered-claim-r10.py']).encode() in out[n]
    a=r.module(out['startup-amendment-r10.py'])
    assert a.BASE_SHA==r.sha(out['window-base-r11.py'])
    assert a.AMENDMENT_SHA==r.sha(out['startup-amendment-r10.json'])
    for n in ('window-base-r11.py','startup-release.py'):
        assert r.sha(out['worker-startup-r10.py']).encode() in out[n]
    assert r.sha(out['PRECLAIM-R10.md']).encode() in out['startup-release.py']
    assert out['prior-startup-validation-r9.py']==before['startup-validation.py']
    assert r.sha(out['permissions-baseline-r10.py']).encode() in out['window-base-r11.py']
    assert out['window-base-r11.py'].count(b'verify_prelaunch_permissions()')==3


def test_actual_selected_cache_baseline_needs_no_second_disposition(built):
    w=r.module(built[1]['window-base-r11.py'])
    raw=Path(r.OBSERVATION).read_bytes()
    assert r.sha(raw)==r.OBSERVATION_SHA
    prior=json.loads(raw)
    accepted={k:prior[k] for k in w.ACCEPTED_KEYS}
    original=copy.deepcopy(accepted)
    assert w.approved_candidate_cache_image(accepted)==original
    assert accepted==original
    assert w.CACHE_PREV_NS==w.CACHE_PINNED_NS==r.CACHE_PIN


def test_final_baseline_retains_r9_except_two_exact_directory_timestamps(built):
    w=r.module(built[1]['window-base-r11.py'])
    old_raw=Path('/var/tmp/ga-e0t1.20-terminal-20260929-r9/observed-after.json').read_bytes()
    assert r.sha(old_raw)=='da799408dc9cc40a331e60fab82fab5e13bbef5f10efcec4997ddf2f8ca5c0e6'
    new_raw=Path(r.OBSERVATION).read_bytes()
    assert r.sha(new_raw)==r.OBSERVATION_SHA
    prior=json.loads(old_raw); current=json.loads(new_raw)
    prior={k:prior[k] for k in w.ACCEPTED_KEYS}
    current={k:current[k] for k in w.ACCEPTED_KEYS}
    for field in ('mtime_ns','ctime_ns'):
        entry=prior['cache']['inventory'][w.CACHE_DIRECTORY]
        assert entry[field]==1790637004449701379
        assert current['cache']['inventory'][w.CACHE_DIRECTORY][field]==r.CACHE_PIN
        entry[field]=r.CACHE_PIN
    assert w.dependency_image(prior)==w.dependency_image(current)


@pytest.mark.parametrize('field',['mtime_ns','ctime_ns'])
@pytest.mark.parametrize('delta',[-1,1])
def test_restored_cache_baseline_rejects_either_timestamp_drift(built,field,delta):
    w=r.module(built[1]['window-base-r11.py'])
    prior=json.loads(Path(r.OBSERVATION).read_bytes())
    prior['cache']['inventory'][w.CACHE_DIRECTORY][field]+=delta
    with pytest.raises(RuntimeError):w.approved_candidate_cache_image(prior)


def test_exact_closed_claim_and_new_append(built,evidence):
    before,out=built;legacy=r.module(out['legacy-continuation-r4.py'])
    current=recovery.expected_pair(evidence,legacy.normalized)
    assert current['task']['status']=='open' and not current['task'].get('assignee')
    assert current['task']['metadata']==recovery.CLOSED_METADATA
    old=r.module(before['contract.py']);new=r.module(out['contract.py'])
    with pytest.raises(RuntimeError):old.validate_task(current['task'],'routed')
    with pytest.raises(RuntimeError):new.validate_task(current['task'],'routed')
    amend=json.loads(out['startup-amendment-r10.json'])
    assert current['task']['notes']==amend['before_note']
    current['task']['notes']=amend['after_note'];new.validate_task(current['task'],'routed')
    assert amend['completed_bind_and_route_must_not_replay'] and amend['source_release_required']


@pytest.mark.parametrize('field',['notes','description','acceptance_criteria','status','assignee','metadata','started_at','updated_at'])
def test_claim_drift_refuses(built,evidence,field):
    bad=copy.deepcopy(evidence);p=recovery.CLOSE_ROOT/'16-claim-phase.json'
    rows=json.loads(bad[p]['stdout']);rows[0][field]='unexpected';bad[p]['stdout']=json.dumps(rows)
    with pytest.raises(RuntimeError):recovery.expected_pair(bad,r.module(built[1]['legacy-continuation-r4.py']).normalized)


@pytest.mark.parametrize('fault',['exit','survivor','ack','census','result'])
def test_failed_close_evidence_refuses(built,evidence,fault):
    bad=copy.deepcopy(evidence);p=recovery.CLOSE_ROOT
    if fault=='exit':bad[p/'16-claim-phase.json']['exit_code']=1
    elif fault=='survivor':bad[p/'17-close-phase.json']['cleanup']['unexpected_survivors']=True
    elif fault=='ack':bad[p/'17-close-phase.json']['stdout']='{}'
    elif fault=='census':bad[p/'18-sessions-phase.json']['stdout']='{"ok":true,"sessions":[{}]}'
    else:bad[p/'result.json']['worktree_processes']=1
    with pytest.raises(RuntimeError):recovery.expected_pair(bad,r.module(built[1]['legacy-continuation-r4.py']).normalized)


def test_prelaunch_permission_check_is_not_postlaunch_assumption(built,monkeypatch):
    w=r.module(built[1]['window-base-r11.py']);calls=[]
    def load(path,pin):
        assert path.name=='permissions-baseline-r10.py' and pin==r.sha(built[1][path.name])
        return types.SimpleNamespace(verify=lambda read,module:calls.append((read,module)))
    monkeypatch.setattr(w,'module',load);w.verify_prelaunch_permissions()
    assert len(calls)==1
    def refuse(path,pin):raise RuntimeError('permission drift')
    monkeypatch.setattr(w,'module',refuse)
    with pytest.raises(RuntimeError):w.verify_prelaunch_permissions()
    # Frozen strict transcript reader is retained; no mode relaxation.
    old=built[0]['startup-validation.py'].replace(b'.gc/worker-evidence/ga-e0t1.20/r9',b'.gc/worker-evidence/ga-e0t1.20/r10')
    old=old.replace(repr(r.prior_recovery.CLOSED_METADATA).encode(),repr(recovery.CLOSED_METADATA).encode())
    def functions(raw):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
    a,b=functions(old),functions(built[1]['startup-validation.py'])
    assert a==b
    release=built[1]['startup-release.py']
    assert release.count(b'v.live_task(')==2
    assert b'v.waiting_turn(' in release and b'task2==task' in release


def test_shell_parse_and_consumed_wrappers(built,tmp_path):
    for name,raw in built[1].items():
        if name.endswith('.sh'):
            p=tmp_path/Path(name).name;p.write_bytes(raw)
            assert subprocess.run(['/bin/sh','-n',str(p)]).returncode==0
    assert b'exit 125' not in built[1]['operator/AMEND-STARTUP-R10.sh'].splitlines()[:4]


def test_create_only_and_eight_exact_prior_files(built,tmp_path):
    root=tmp_path/'new';r.main(str(root))
    assert len(workspace.PRIOR_FILES)==8
    assert json.loads((root/'assembly.json').read_bytes())['files']=={n:r.sha(v) for n,v in built[1].items()}
    with pytest.raises(AssertionError):r.main(str(root))


def test_every_local_call_and_wrapper_pin_resolves(built,monkeypatch):
    import test_window_r7 as previous
    monkeypatch.setattr(previous,'r',r)
    previous.test_all_local_call_and_wrapper_bindings_resolve(built)


@pytest.mark.parametrize('fresh_started',[False,True])
def test_new_claim_keeps_exact_history_and_requires_new_identity(built,evidence,fresh_started):
    out=built[1];v=r.module(out['startup-validation.py']);c=r.module(out['contract.py'])
    routed=recovery.expected_pair(evidence,r.module(out['legacy-continuation-r4.py']).normalized)['task']
    routed['notes']=c.BOUND_NOTE;routed['updated_at']='2026-09-28T23:34:00Z'
    session=dict(id='ci-newproof',session_name='codex-ci-newproof',created_at='2026-09-28T23:35:00Z')
    task=copy.deepcopy(routed)
    task.update(status='in_progress',assignee=session['session_name'],updated_at='2026-09-28T23:36:00Z',
        notes=routed['notes']+'\nSTARTUP READY: ga-e0t1.20 report_sha256=digest')
    task['metadata'].update({'gc.session_id':session['id'],'gc.session_name':session['session_name']})
    if fresh_started:task['started_at']='2026-09-28T23:35:10Z'
    v.live_task(task,routed,session,c,'digest')
    for field in ('session','branch','start','time','note','owner'):
        bad=copy.deepcopy(task)
        if field=='session':bad['metadata']['gc.session_id']=recovery.SESSION
        elif field=='branch':bad['metadata']['gc.work_branch']='other'
        elif field=='start':bad['started_at']='2026-09-28T13:02:00Z'
        elif field=='time':bad['updated_at']='2026-09-28T12:00:00Z'
        elif field=='note':bad['notes']+='extra'
        else:bad['assignee']='wrong'
        with pytest.raises(RuntimeError):v.live_task(bad,routed,session,c,'digest')


def test_current_r10_workspace_has_exact_r9_history(built):
    out=built[1];m=r.module(out['workspace-r10.py']);v=r.module(out['prior-startup-validation-r9.py'])
    c=r.module(out['contract.py']);probe=r.module(out['worker-startup-r10.py'])
    image=v.workspace_image(Path(c.WORK),probe.read_regular)
    def load(p,pin):
        assert pin==r.sha(out[p.name]);return v
    def read(p,pin):
        raw=probe.read_regular(p);assert r.sha(raw)==pin;return raw
    w=types.SimpleNamespace(HERE=Path('/fixture'),module=load,read=read)
    before=m.verify(w,image,c.RUNTIME_IMAGE)
    assert len(image)==len(before)+3
    for p in m.PRIOR_FILES:
        bad=copy.deepcopy(image);bad[p]['sha256']='0'*64
        with pytest.raises(RuntimeError):m.verify(w,bad,c.RUNTIME_IMAGE)
    bad=copy.deepcopy(image);bad['unrelated']={'mode':384,'type':32768,'size':0,'sha256':r.sha(b'')}
    with pytest.raises(RuntimeError):m.verify(w,bad,c.RUNTIME_IMAGE)

def test_generated_native_waiter_accepts_real_shape_and_keeps_failure_negatives(built):
    import test_review_wait_r9 as captured
    case=captured.case.__wrapped__()
    rows=captured.captured_wait_rows(case)
    v=r.module(built[1]['startup-validation.py'])
    assert v.waiting_turn(captured.wait_bytes(rows),case[2],captured.SHA,'a'*64,captured.NOW)['completed_waiting_turn']
    rows.insert(-1,dict(type='event_msg',payload=dict(type='task_started')))
    with pytest.raises(RuntimeError):
        v.waiting_turn(captured.wait_bytes(rows),case[2],captured.SHA,'a'*64,captured.NOW)
