"""Offline R7 package and exact recovered-claim regression; no live effects."""
import copy
import json
from pathlib import Path
import subprocess
import types
import ast
import hashlib
import re
import os

import pytest
import recovered_claim_r7 as recovered
import window_r7 as r

CACHE=r.CACHE_PREV


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
    assert expected['task']['status']=='open' and not expected['task'].get('assignee')
    assert expected['task']['metadata']==recovered.CLOSED_METADATA
    assert expected['task']['labels']==['needs/operator']
    # Historical R6 admission correctly refused this post-close state (RED).
    old=module(built[0]['contract.py'])
    with pytest.raises(RuntimeError):old.validate_task(expected['task'],'routed')
    # R7 admits only after its exact new note append; not before.
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
    current['parent']['updated_at']='2026-09-28T16:00:00Z'
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
    assert str(w.PREP)==str(r.PREP)
    assert str(w.ACCEPTED)==r.OBSERVATION and w.ACCEPTED_SHA==r.OBSERVATION_SHA
    assert w.CITY_SHA[1]==p['city_after_sha256'] and w.RECEIPT_SHA[1]==p['receipt_after_sha256']
    assert w.REVISION[1]==p['revision_after']
    assert w.CACHE_PREV_NS==r.CACHE_PREV and w.CACHE_PINNED_NS==CACHE
    for n in (r.HISTORICAL & before.keys())-{'operator/AMEND-STARTUP-R6.sh'}:
        assert out[n]==before[n],n
    for n in ('worker-startup-r7.py','PRECLAIM-R7.md','prompt-prep-r7.py'):
        assert out[n]==r.startup_r7.components()[n]
    assert b"previous['worker_started_in_window']" not in out['window-base-r11.py']
    assert r.startup_r7.CLOSE_SHA.encode() in out['window-base-r11.py']
    assert r.PREP_RESULT_SHA.encode() in out['window-base-r11.py']
    assert out['recovered-claim-r7.py']==(r.HERE/'recovered_claim_r7.py').read_bytes()


def test_bindings_replay_refusal_and_shell_parse(built,tmp_path):
    before,out=built
    for n in ('operator/BIND.sh','operator/ROUTE.sh','operator/AMEND-STARTUP-R5.sh','operator/AMEND-STARTUP-R6.sh',
              'operator/PROMPT-PREP-R5.sh','operator/PROMPT-PREP-R6.sh'):
        assert b'exit 125' in out[n].splitlines()[:4]
    a=module(out['startup-amendment-r7.py'])
    assert a.BASE_SHA==r.sha(out['window-base-r11.py'])
    assert a.AMENDMENT_SHA==r.sha(out['startup-amendment-r7.json'])
    assert a.LEGACY_SHA==r.sha(out['legacy-continuation-r4.py'])
    assert r.sha(out['startup-amendment-r7.py']).encode() in out['operator/AMEND-STARTUP-R7.sh']
    assert r.sha(out['recovered-claim-r7.py']).encode() in out['continuation-admission.py']
    assert r.sha(out['recovered-claim-r7.py']).encode() in out['startup-amendment-r7.py']
    for n in ('window-base-r11.py','startup-release.py'):
        assert b"HERE/'worker-startup-r7.py'" in out[n]
        assert r.sha(out['worker-startup-r7.py']).encode() in out[n]
    assert r.sha(out['PRECLAIM-R7.md']).encode() in out['startup-release.py']
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
    out=built[1];m=module(out['startup-amendment-r7.py'],'amend_r6')
    script=tmp_path/'startup-amendment-r7.py';script.write_bytes(out['startup-amendment-r7.py'])
    m.__file__=str(script);m._SOURCE_SHA=r.sha(script.read_bytes())
    m.HERE=tmp_path;m.ROOT=tmp_path/'result';m.WINDOW=tmp_path/'not-yet-window'
    legacy=module(out['legacy-continuation-r4.py'])
    exact=module(out['startup-amendment-contract-r5.py'])
    contract=module(out['contract.py'])
    prior=module(out['recovered-claim-r7.py'])
    state=recovered.expected_pair(evidence,legacy.normalized)
    if fault=='before':state['task']['status']='in_progress'
    amendment=json.loads(out['startup-amendment-r7.json'])
    records={p:p.read_bytes() for p in set(legacy.PINS)|set(recovered.PINS)}
    calls=[];saved={}
    w=types.SimpleNamespace(GC=['/managed/gc','--city','fixture'],CITY=tmp_path/'city',
        RECEIPT=tmp_path/'receipt',CITY_SHA=['baseline'],RECEIPT_SHA=['baseline'],
        load_support=lambda:(None,None,None),pins=lambda:None,host=lambda o:{'stable':True},
        contract=lambda:contract)
    def read(path,pin=None):
        if path in records:raw=records[path]
        elif path.name=='startup-amendment-r7.json':raw=out[path.name]
        else:
            assert path in (w.CITY/'city.toml',w.RECEIPT)
            return b'unchanged'
        if pin is not None:assert r.sha(raw)==pin
        return raw
    w.read=read
    mods={'legacy-continuation-r4.py':legacy,'startup-amendment-contract-r5.py':exact,
          'recovered-claim-r7.py':prior}
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
        state['task']['updated_at']='2026-09-28T16:00:00Z'
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
        if path=='session':bad['metadata']['gc.session_id']='ci-6gwp8'
        elif path=='branch':bad['metadata']['gc.work_branch']='other'
        elif path=='start':bad['started_at']='2026-09-28T13:02:00Z'
        elif path=='time':bad['updated_at']='2026-09-28T12:00:00Z'
        elif path=='note':bad['notes']+='extra'
        else:bad['assignee']='wrong'
        with pytest.raises(RuntimeError):v.live_task(bad,routed,session,c,'digest')


def test_all_local_call_and_wrapper_bindings_resolve(built):
    out=built[1]
    for name,raw in out.items():
        if name in r.HISTORICAL or name.startswith('prior-') or name.startswith('prompt-prep-'):
            continue  # These retain their separately frozen historical dependency sets.
        if name.endswith('.sh'):
            if b'exit 125' in raw.splitlines()[:4]:continue
            for script,var in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"',raw.decode()):
                [pin]=re.findall(r'^%s=([0-9a-f]{64})$'%var,raw.decode(),re.M)
                assert pin==r.sha(out[script]),(name,script)
        if not name.endswith('.py') or name.startswith('test_'):continue
        constants={}
        for n in ast.walk(ast.parse(raw)):
            if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant):
                for target in n.targets:
                    if isinstance(target,ast.Name):constants[target.id]=n.value.value
        for n in ast.walk(ast.parse(raw)):
            if not isinstance(n,ast.Call) or len(n.args)<2:continue
            p=n.args[0]
            if not (isinstance(p,ast.BinOp) and isinstance(p.op,ast.Div)
                    and isinstance(p.left,ast.Name) and p.left.id=='HERE'
                    and isinstance(p.right,ast.Constant) and p.right.value in out):continue
            pin=n.args[1]
            value=pin.value if isinstance(pin,ast.Constant) else constants.get(pin.id) if isinstance(pin,ast.Name) else None
            if isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value):
                assert value==r.sha(out[p.right.value]),(name,p.right.value,value)


@pytest.mark.parametrize('fault',[None,'body','suffix','argv-race','asset','revalidation'])
def test_release_retains_exact_prompt_and_revalidates(built,fault):
    out=built[1];s=module(out['startup-release.py']);v=module(out['startup-validation.py'])
    body=out['PRECLAIM-R7.md'].decode()
    actual='[city] gascity/codex • 2026-09-28T18:10:00\n\nRun `gc prime` to initialize your context.\n\n'+body+out['skills-suffix-r5.txt'].decode()
    if fault=='body':actual=actual.replace('exact pre-claim','inexact pre-claim')
    if fault=='suffix':actual+='extra'
    raw=('codex\0'+actual+'\0').encode()
    proof={'chain':[{'argv_sha256':r.sha(raw[:-1])}]}
    if fault=='argv-race':proof['chain'][0]['argv_sha256']='0'*64
    rechecks=[]
    def revalidate(*args):
        rechecks.append(True)
        if fault=='revalidation':raise RuntimeError('changed graph')
    runtime=types.SimpleNamespace(PROC=Path('/synthetic-proc'),worker_identity=lambda *a:proof,
        proc_bytes=lambda *a:raw,revalidate=revalidate)
    def read(p):
        value=out[p.name]
        return value+b'changed' if fault=='asset' and p.name=='PRECLAIM-R7.md' else value
    if fault:
        with pytest.raises(RuntimeError):s.worker_identity(123,{},v,read,runtime)
    else:
        assert s.worker_identity(123,{},v,read,runtime)==proof and rechecks==[True]


def confined_workspace(raw, work, tmp_path):
    import helper_recovery as h
    h.verify_sandbox_binary()
    source=tmp_path/'validator.py';source.write_bytes(raw)
    code=('from pathlib import Path; import json,sys,types; '
          'p=Path(sys.argv[1]); m=types.ModuleType("snapshot"); m.__file__=str(p); '
          'exec(compile(p.read_bytes(),str(p),"exec"),m.__dict__); '
          'print(json.dumps(m.workspace_image(Path(sys.argv[2]),lambda p:p.read_bytes()),sort_keys=True))')
    result=subprocess.run(h.read_only_argv(['/usr/bin/python3','-I','-S','-B','-c',code,
        str(source),str(work)],tmp_path),capture_output=True,timeout=45)
    assert result.returncode==0,result.stderr.decode()
    return json.loads(result.stdout)


def test_directory_access_time_does_not_weaken_the_workspace_guard(built,tmp_path):
    source=built[1]['prior-startup-validation-r6.py'];v=module(source)
    root=tmp_path/'cold';root.mkdir();(root/'item').write_bytes(b'unchanged')
    os.utime(root,ns=(1,root.stat().st_mtime_ns))
    before=root.lstat()
    with pytest.raises(RuntimeError,match='workspace changed during walk'):
        v.workspace_image(root,lambda p:p.read_bytes())
    after=root.lstat()
    assert before.st_atime_ns!=after.st_atime_ns
    assert all(getattr(before,key)==getattr(after,key) for key in
               ('st_mtime_ns','st_ctime_ns','st_ino','st_mode','st_size','st_uid','st_gid'))
    os.utime(root,ns=(1,root.stat().st_mtime_ns));before=root.lstat()
    image=confined_workspace(source,root,tmp_path)
    assert root.lstat()==before and image['item']['sha256']==r.sha(b'unchanged')


@pytest.mark.parametrize('fault',[None,'entry','mode','inode'])
def test_runtime_workspace_reader_is_nonperturbing_and_still_refuses_drift(built,tmp_path,fault):
    v=module(built[1]['startup-validation.py'])
    root=tmp_path/'cold';root.mkdir();(root/'item').write_bytes(b'unchanged')
    os.utime(root,ns=(1,root.stat().st_mtime_ns));before=root.lstat()
    def read(path):
        raw=path.read_bytes()
        if fault=='entry':(root/'extra').write_bytes(b'new')
        if fault=='mode':root.chmod(0o700)
        if fault=='inode':
            root.rename(tmp_path/'preserved');root.mkdir()
        return raw
    if fault is None:
        image=v.workspace_image(root,read)
        assert root.lstat()==before and image['item']['sha256']==r.sha(b'unchanged')
    else:
        with pytest.raises(RuntimeError,match='workspace changed during walk'):
            v.workspace_image(root,read)


def test_prior_workspace_bytes_preserved_and_new_evidence_separated(built,tmp_path):
    out=built[1];m=module(out['workspace-r7.py']);v=module(out['prior-startup-validation-r6.py'])
    c=module(out['contract.py'])
    before=json.loads(m.BASELINE.read_bytes())
    # Production inspection uses a read-only mount. A plain directory walk can
    # update relatime and correctly trip the unchanged-directory guard itself.
    raw=confined_workspace(out['prior-startup-validation-r6.py'],Path(c.WORK),tmp_path)
    def load(p,pin):
        assert pin==r.sha(out[p.name]);return v
    def read(p,pin):
        content=p.read_bytes();assert r.sha(content)==pin;return content
    w=types.SimpleNamespace(HERE=Path('/fixture'),module=load,read=read)
    m.verify(w,raw,c.RUNTIME_IMAGE)
    for path in m.PRIOR_FILES:
        bad=copy.deepcopy(raw);bad[path]['sha256']='0'*64
        with pytest.raises(RuntimeError):m.verify(w,bad,c.RUNTIME_IMAGE)
    bad=copy.deepcopy(raw);bad['unrelated']={'mode':384,'type':32768,'size':0,'sha256':r.sha(b'')}
    with pytest.raises(RuntimeError):m.verify(w,bad,c.RUNTIME_IMAGE)
    assert len(raw)==len(before)+4
