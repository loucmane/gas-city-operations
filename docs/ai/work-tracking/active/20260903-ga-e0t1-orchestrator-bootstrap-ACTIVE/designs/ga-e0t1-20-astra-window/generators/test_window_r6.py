"""Offline R6 package and exact recovered-claim regression; no live effects."""
import copy
import json
from pathlib import Path
import subprocess
import types

import pytest
import recovered_claim_r6 as recovered
import window_r6 as r

CACHE=1790603024092118566


@pytest.fixture(scope='module')
def built():
    return r.assemble(CACHE)


@pytest.fixture(scope='module')
def evidence():
    values={}
    for path,pin in recovered.PINS.items():
        raw=path.read_bytes()
        assert r.sha(raw)==pin
        values[path]=json.loads(raw)
    return values


def module(raw,name='r6_fixture'):
    return r.startup_r5.source_module(raw,name)


def test_prior_native_claim_and_close_match_live_own_fields(built,evidence):
    legacy=module(built[1]['legacy-continuation-r4.py'])
    expected=recovered.expected_pair(evidence,legacy.normalized)
    own=json.loads((r.build.HERE/'fixtures/r6-recovered-task-own.json').read_bytes())
    assert {k:v for k,v in expected['task'].items() if k!='dependencies'}==own
    # Historical R5 admission correctly refused this post-close state (RED).
    old=module(built[0]['contract.py'])
    with pytest.raises(RuntimeError):old.validate_task(expected['task'],'routed')
    # R6 admits only after its exact new note append; not before.
    new=module(built[1]['contract.py'])
    with pytest.raises(RuntimeError):new.validate_task(expected['task'],'routed')
    expected['task']['notes']=new.BOUND_NOTE
    new.validate_task(expected['task'],'routed')


@pytest.mark.parametrize('field',['notes','description','acceptance_criteria','status','assignee','metadata','started_at','updated_at'])
def test_prior_claim_extra_change_refuses(built,evidence,field):
    altered=copy.deepcopy(evidence)
    p=recovered.CLOSE_ROOT/'16-claim-phase.json'
    rows=json.loads(altered[p]['stdout'])
    rows[0][field]='changed'
    altered[p]['stdout']=json.dumps(rows)
    with pytest.raises(RuntimeError):
        recovered.expected_pair(altered,module(built[1]['legacy-continuation-r4.py']).normalized)


@pytest.mark.parametrize('fault',['failed','cleanup','ack','census','close-result'])
def test_prior_phase_or_close_mismatch_refuses(built,evidence,fault):
    altered=copy.deepcopy(evidence);p=recovered.CLOSE_ROOT
    if fault=='failed':altered[p/'16-claim-phase.json']['exit_code']=1
    elif fault=='cleanup':altered[p/'17-close-phase.json']['cleanup']['unexpected_survivors']=True
    elif fault=='ack':altered[p/'17-close-phase.json']['stdout']='{"ok":true,"session_id":"other"}'
    elif fault=='census':altered[p/'18-sessions-phase.json']['stdout']='{"ok":true,"sessions":[{}]}'
    else:altered[p/'result.json']['worktree_processes']=1
    with pytest.raises(RuntimeError):
        recovered.expected_pair(altered,module(built[1]['legacy-continuation-r4.py']).normalized)


def test_exact_pair_projection_and_parent_audit_still_bound(built,evidence):
    legacy=module(built[1]['legacy-continuation-r4.py'])
    p=recovered.expected_pair(evidence,legacy.normalized)
    current=copy.deepcopy(p)
    current['parent']['notes']+='\nread-only audit'
    current['parent']['updated_at']='2026-09-28T14:00:00Z'
    for key in ('notes','updated_at'):
        current['task']['dependencies'][0][key]=current['parent'][key]
    w=types.SimpleNamespace(read=lambda path,pin:json.dumps(evidence[path]).encode())
    recovered.verify(w,current,legacy.normalized,legacy.compare_pair)
    for key in ('status','metadata','notes','updated_at','started_at'):
        bad=copy.deepcopy(current);bad['task'][key]='drift'
        with pytest.raises(RuntimeError):recovered.verify(w,bad,legacy.normalized,legacy.compare_pair)
    bad=copy.deepcopy(current)
    bad['parent']['dependencies'][0]['priority']=99
    with pytest.raises(RuntimeError):recovered.verify(w,bad,legacy.normalized,legacy.compare_pair)


def test_r6_is_deterministic_preserves_consumed_and_binds_native_prep(built):
    before,out=built
    assert r.assemble(CACHE)==built
    w=module(out['window-base-r11.py'])
    p=r.prep()
    assert str(w.PREP)==r.startup.ROOT
    assert str(w.ACCEPTED)==r.OBSERVATION and w.ACCEPTED_SHA==r.OBSERVATION_SHA
    assert w.CITY_SHA[1]==p['city_after_sha256'] and w.RECEIPT_SHA[1]==p['receipt_after_sha256']
    assert w.REVISION[1]==p['revision_after']
    assert w.CACHE_PREV_NS==r.CACHE_PREV and w.CACHE_PINNED_NS==CACHE
    for n in (r.HISTORICAL & before.keys())-{'operator/AMEND-STARTUP-R5.sh'}:
        assert out[n]==before[n],n
    for n in ('worker-startup-r6.py','PRECLAIM-R6.md','prompt-prep-r6.py'):
        assert out[n]==r.startup.components()[n]
    assert b"previous['worker_started_in_window']" not in out['window-base-r11.py']
    assert r.startup.CLOSE_SHA.encode() in out['window-base-r11.py']
    assert r.PREP_RESULT_SHA.encode() in out['window-base-r11.py']
    assert out['recovered-claim-r6.py']==(r.build.HERE/'recovered_claim_r6.py').read_bytes()


def test_bindings_replay_refusal_and_shell_parse(built,tmp_path):
    before,out=built
    for n in ('operator/BIND.sh','operator/ROUTE.sh','operator/AMEND-STARTUP-R5.sh',
              'operator/PROMPT-PREP-R5.sh','operator/PROMPT-PREP-R6.sh'):
        assert b'exit 125' in out[n].splitlines()[:4]
    a=module(out['startup-amendment-r6.py'])
    assert a.BASE_SHA==r.sha(out['window-base-r11.py'])
    assert a.AMENDMENT_SHA==r.sha(out['startup-amendment-r6.json'])
    assert a.LEGACY_SHA==r.sha(out['legacy-continuation-r4.py'])
    assert r.sha(out['startup-amendment-r6.py']).encode() in out['operator/AMEND-STARTUP-R6.sh']
    assert r.sha(out['recovered-claim-r6.py']).encode() in out['continuation-admission.py']
    assert r.sha(out['recovered-claim-r6.py']).encode() in out['startup-amendment-r6.py']
    for n in ('window-base-r11.py','startup-release.py'):
        assert b"HERE/'worker-startup-r6.py'" in out[n]
        assert r.sha(out['worker-startup-r6.py']).encode() in out[n]
    assert r.sha(out['PRECLAIM-R6.md']).encode() in out['startup-release.py']
    for n,raw in out.items():
        assert b'RECOVERED_SHA' not in raw and b'AMEND_EXECUTOR_SHA' not in raw,n
        if n.endswith('.sh'):
            p=tmp_path/Path(n).name;p.write_bytes(raw)
            assert subprocess.run(['/bin/sh','-n',str(p)]).returncode==0


@pytest.mark.parametrize('cache',[None,False,str(CACHE),r.CACHE_PREV-1])
def test_cache_not_invented(cache):
    with pytest.raises(AssertionError):r.assemble(cache)


def test_create_only(built,tmp_path):
    root=tmp_path/'out'
    r.main(str(root),str(CACHE))
    manifest=json.loads((root/'assembly.json').read_bytes())
    assert manifest['files']=={n:r.sha(raw) for n,raw in built[1].items()}
    assert manifest['execution_admitted'] is False
    with pytest.raises(AssertionError):r.main(str(root),str(CACHE))

@pytest.mark.parametrize('fault',[None,'before','after','ambiguous'])
def test_generated_r6_amendment_executes_one_append_only(built,evidence,tmp_path,fault):
    out=built[1];m=module(out['startup-amendment-r6.py'],'amend_r6')
    script=tmp_path/'startup-amendment-r6.py';script.write_bytes(out['startup-amendment-r6.py'])
    m.__file__=str(script);m._SOURCE_SHA=r.sha(script.read_bytes())
    m.HERE=tmp_path;m.ROOT=tmp_path/'result';m.WINDOW=tmp_path/'not-yet-window'
    legacy=module(out['legacy-continuation-r4.py'])
    exact=module(out['startup-amendment-contract-r5.py'])
    contract=module(out['contract.py'])
    prior=module(out['recovered-claim-r6.py'])
    state=recovered.expected_pair(evidence,legacy.normalized)
    if fault=='before':state['task']['status']='in_progress'
    amendment=json.loads(out['startup-amendment-r6.json'])
    records={p:p.read_bytes() for p in set(legacy.PINS)|set(recovered.PINS)}
    calls=[];saved={}
    w=types.SimpleNamespace(GC=['/managed/gc','--city','fixture'],CITY=tmp_path/'city',
        RECEIPT=tmp_path/'receipt',CITY_SHA=['baseline'],RECEIPT_SHA=['baseline'],
        load_support=lambda:(None,None,None),pins=lambda:None,host=lambda o:{'stable':True},
        contract=lambda:contract)
    def read(path,pin=None):
        if path in records:raw=records[path]
        elif path.name=='startup-amendment-r6.json':raw=out[path.name]
        else:
            assert path in (w.CITY/'city.toml',w.RECEIPT)
            return b'unchanged'
        if pin is not None:assert r.sha(raw)==pin
        return raw
    w.read=read
    mods={'legacy-continuation-r4.py':legacy,'startup-amendment-contract-r5.py':exact,
          'recovered-claim-r6.py':prior}
    def loadmod(path,pin):
        assert r.sha(out[path.name])==pin
        return mods[path.name]
    w.module=loadmod
    def save(name,value):
        assert name not in saved
        saved[name]=copy.deepcopy(value)
        (w.ROOT/name).write_text(json.dumps(value))
    w.save=save;w.record=lambda n:saved[n]
    def phase(name,argv,*args,**kwargs):
        calls.append((name,argv))
        if 'show' in argv:
            bead=argv[argv.index('show')+1]
            return {'stdout':json.dumps([state['task' if bead==recovered.TASK else 'parent']])}
        assert argv==w.GC+['--rig','gascity','bd','update',recovered.TASK,'--append-notes',amendment['append_note']]
        state['task']['notes']+='\n'+amendment['append_note']
        state['task']['updated_at']='2026-09-28T14:00:00Z'
        row=next(x for x in state['parent']['dependencies'] if x['id']==recovered.TASK)
        for key in ('notes','updated_at'):row[key]=state['task'][key]
        if fault=='after':state['task']['metadata']['injected']='bad'
        if fault=='ambiguous':raise RuntimeError('synthetic ambiguous mutation')
        return {'stdout':''}
    w.phase=phase;w.complete_containment=lambda:saved.setdefault('containment',True)
    m.load=lambda path,pin:w
    if fault:
        with pytest.raises(RuntimeError):m.main()
        assert 'result.json' not in saved
    else:
        m.main()
        assert saved['result.json']['ok'] and saved['containment']
    assert sum(name=='append-startup-note' for name,args in calls)==(0 if fault=='before' else 1)
    count=len(calls)
    with pytest.raises(FileExistsError):m.main()
    assert len(calls)==count


@pytest.mark.parametrize('fresh_started',[False,True])
def test_retry_claim_preserves_history_and_binds_new_worker(built,evidence,fresh_started):
    out=built[1];v=module(out['startup-validation.py']);c=module(out['contract.py'])
    legacy=module(out['legacy-continuation-r4.py'])
    routed=recovered.expected_pair(evidence,legacy.normalized)['task']
    routed['notes']=c.BOUND_NOTE;routed['updated_at']='2026-09-28T14:00:00Z'
    session=dict(id='ci-newproof',session_name='codex-ci-newproof',created_at='2026-09-28T14:01:00Z')
    task=copy.deepcopy(routed)
    task.update(status='in_progress',assignee=session['session_name'],
        updated_at='2026-09-28T14:02:00Z',notes=routed['notes']+'\nSTARTUP READY: ga-e0t1.20 report_sha256=digest')
    task['metadata'].update({'gc.session_id':session['id'],'gc.session_name':session['session_name']})
    if fresh_started:task['started_at']='2026-09-28T14:01:10Z'
    v.live_task(task,routed,session,c,'digest')
    for path in ('session','branch','start','time','note','owner'):
        bad=copy.deepcopy(task)
        if path=='session':bad['metadata']['gc.session_id']='ci-rks41'
        elif path=='branch':bad['metadata']['gc.work_branch']='other'
        elif path=='start':bad['started_at']='2026-09-28T13:02:00Z'
        elif path=='time':bad['updated_at']='2026-09-28T12:00:00Z'
        elif path=='note':bad['notes']+='extra'
        else:bad['assignee']='wrong'
        with pytest.raises(RuntimeError):v.live_task(bad,routed,session,c,'digest')
