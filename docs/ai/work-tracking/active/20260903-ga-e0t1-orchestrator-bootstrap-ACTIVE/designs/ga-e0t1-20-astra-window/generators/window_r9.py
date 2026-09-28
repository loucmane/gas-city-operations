"""Create-only R9 successor after reviewed native waiting correction and exact R8 recovery."""
import ast
import json
from pathlib import Path
import re
import sys

import build
import startup_r5
import startup_r9 as startup
import window_r8
import monitoring_r9
import recovered_claim_r8 as prior_recovery
import recovered_claim_r9 as recovery
import workspace_r8 as prior_workspace
import workspace_r9 as workspace

HERE=Path(__file__).parent
BASE=startup.BASE
PREP=Path(startup.ROOT)
PREP_RESULT_SHA='9da96928da9fcbb49828231f36065a3f5cb2c8ffa07068128b896c4ed12c6fd6'
OBSERVATION='/tmp/ga-e0t1-20-readonly-baseline-20260929-r14/observed.json'
OBSERVATION_SHA='78426edf72630e2d9d7511a2027941333cef8b78fd9bfd8c5801d3466dc0d48c'
CACHE_PREV=1790637004449701379
CACHE_PIN=1790637004449701379
ROOTS={v:v.replace('20260928-r8','20260929-r9').replace('.20-r8-','.20-r9-')
       for v in window_r8.ROOTS.values() if '20260928-r8' in v or '.20-r8-' in v}
ROOTS['ga-e0t1.20-integrity-20260928-r10']='ga-e0t1.20-integrity-20260929-r11'
HISTORICAL=window_r8.HISTORICAL|{'worker-startup-r8.py','PRECLAIM-R8.md','prompt-prep-r8.py',
    'recovered-claim-r8.py','workspace-r8.py','prior-startup-validation-r7.py',
    'permissions-baseline-r8.py','startup-amendment-r8.py','startup-amendment-r8.json',
    'operator/PROMPT-PREP-R8.sh'}
COMPLETED={'operator/AMEND-STARTUP-R8.sh','operator/PROMPT-PREP-R9.sh'}
sha=build.sha


def module(raw):return startup_r5.source_module(raw,'r9_offline')


def gitfile(name):return build.git('show',BASE+':'+build.NEW+'/'+name)


def frozen():
    manifest=json.loads(gitfile('assembly.json'))
    out={n:gitfile(n) for n in manifest['files']}
    assert {n:sha(v) for n,v in out.items()}==manifest['files'],'R8 assembly binding'
    return out


def prep():
    raw=(PREP/'result.json').read_bytes();assert sha(raw)==PREP_RESULT_SHA
    r=json.loads(raw)
    assert r['ok'] is True and r['installed'] is False and r['worker_launched'] is False
    assert r['preparation_only'] is True and r['execution_authorized_by_this_result'] is False
    assert r['prior_close_sha256']==startup.CLOSE_SHA
    assert r['permissions_result_sha256']=='baae65a63de589bc354a11d8ea673bded479be63aa004170256430073c44c862'
    assert r['permissions_postimage_sha256']=='709e74b448d50a0f4fc5a3fcaa7fc1728b5b364cfe8a76082ffe90cbd7e03010'
    for n,k in [('city.baseline.toml','city_before_sha256'),('city.isolated.toml','city_after_sha256'),
                ('receipt.before.json','receipt_before_sha256'),('receipt.final.json','receipt_after_sha256')]:
        assert sha((PREP/n).read_bytes())==r[k]
    return r


def retarget(text):
    for a,z in ROOTS.items():text=text.replace(a,z)
    return text


def assemble():
    before=frozen();out=dict(before);result=prep();old=module(before['window-base-r11.py'])
    for n,raw in before.items():
        if n not in HISTORICAL:out[n]=retarget(raw.decode()).encode()
    out.update(startup.components())
    for n in COMPLETED:
        raw=before[n] if n in before else out[n]
        out[n]=b'#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'+raw.split(b'\n',1)[1]
    out['recovered-claim-r9.py']=(HERE/'recovered_claim_r9.py').read_bytes()
    out['workspace-r9.py']=(HERE/'workspace_r9.py').read_bytes()
    out['prior-startup-validation-r8.py']=before['startup-validation.py']
    old_contract=module(before['contract.py'])
    note_before=old_contract.BOUND_NOTE+'\n'+recovery.STARTUP
    append=('R9 append-forward startup amendment for ga-e0t1.20. Use '+str(build.O/build.NEW/'PRECLAIM-R9.md')+
        ' sha256 '+sha(out['PRECLAIM-R9.md'])+' and worker-startup-r9.py sha256 '+sha(out['worker-startup-r9.py'])+
        '. Supersede only startup references. Preserve exact closed ci-sgd80 claim progress-stall annotations and startup files. '
        'Exact private transcript history and native completed waiting proof are bound. No route workspace base provider or signing change. '
        'Fresh same-session startup proof and exact source release remain mandatory. Store new evidence in '+startup.EVIDENCE+'.')
    amendment=dict(schema='ga-e0t1.20.startup-amendment.v1',before_note=note_before,append_note=append,
        after_note=note_before+'\n'+append,worker_probe_sha256=sha(out['worker-startup-r9.py']),
        prompt_sha256=sha(out['PRECLAIM-R9.md']),source_release_required=True,
        completed_bind_and_route_must_not_replay=True)
    out['startup-amendment-r9.json']=(json.dumps(amendment,sort_keys=True,indent=2)+'\n').encode()
    text=before['contract.py'].decode()
    text=build.once(text,'BOUND_NOTE = '+repr(old_contract.BOUND_NOTE),'BOUND_NOTE = '+repr(amendment['after_note']))
    text=build.once(text,repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    text=build.once(text,"session['id']!='ci-zcoet' and session['session_name']!='codex-ci-zcoet'",
        "session['id']!='ci-sgd80' and session['session_name']!='codex-ci-sgd80'")
    assert text.count(repr(prior_workspace.PRIOR_FILES))==2
    text=text.replace(repr(prior_workspace.PRIOR_FILES),repr(workspace.PRIOR_FILES))
    text=build.once(text,repr('.gc/worker-evidence/ga-e0t1.20/r8/'),repr(startup.EVIDENCE+'/'))
    out['contract.py']=text.encode()
    for n,source in [('startup-amendment-r9.py','startup-amendment-r8.py'),('continuation-admission.py','continuation-admission.py')]:
        text=retarget(before[source].decode())
        text=text.replace('startup-amendment-r8.json','startup-amendment-r9.json').replace('recovered-claim-r8.py','recovered-claim-r9.py')
        out[n]=text.encode()
    text=out['window-base-r11.py'].decode()
    for a,z in [(str(old.ACCEPTED),OBSERVATION),(old.ACCEPTED_SHA,OBSERVATION_SHA),
        (str(old.PREP),str(PREP)),(window_r8.PREP_RESULT_SHA,PREP_RESULT_SHA),
        (old.CITY_SHA[1],result['city_after_sha256']),(old.RECEIPT_SHA[1],result['receipt_after_sha256']),
        (old.REVISION[1],result['revision_after']),
        ('/var/tmp/ga-e0t1.20-terminal-20260928-r7/result.json','/var/tmp/ga-e0t1.20-terminal-20260928-r8/result.json'),
        (window_r8.startup.CLOSE,startup.CLOSE),(window_r8.startup.CLOSE_SHA,startup.CLOSE_SHA)]:
        text=build.once(text,repr(a),repr(z))
    text=build.once(text,"closed['closed_session']=='ci-zcoet'","closed['closed_session']=='ci-sgd80'")
    text=build.once(text,"Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r7',n)",
        "Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r8',n)")
    # Final read-only comparison follows all coordinator verification. Its only
    # R8 deltas are the exact cache directory timestamps; require this image as-is.
    text=build.once(text,'CACHE_PREV_NS = '+str(old.CACHE_PREV_NS),'CACHE_PREV_NS = '+str(CACHE_PREV))
    text=build.once(text,'CACHE_PINNED_NS = '+str(old.CACHE_PINNED_NS),'CACHE_PINNED_NS = '+str(CACHE_PIN))
    text=text.replace("HERE/'workspace-r8.py'","HERE/'workspace-r9.py'")
    text=text.replace("HERE/'permissions-baseline-r8.py'","HERE/'permissions-baseline-r9.py'")
    out['window-base-r11.py']=text.encode()
    text=before['startup-validation.py'].decode()
    text=text.replace('.gc/worker-evidence/ga-e0t1.20/r8',startup.EVIDENCE)
    assert text.count(repr(prior_recovery.CLOSED_METADATA))==2
    text=text.replace(repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    out['startup-validation.py']=text.encode()
    for n in ('window-base-r11.py','startup-release.py'):
        text=out[n].decode().replace('worker-startup-r8.py','worker-startup-r9.py').replace('PRECLAIM-R8.md','PRECLAIM-R9.md')
        text=text.replace(sha(before['worker-startup-r8.py']),sha(out['worker-startup-r9.py']))
        text=text.replace(sha(before['PRECLAIM-R8.md']),sha(out['PRECLAIM-R9.md']))
        out[n]=text.encode()
    out['startup-validation.py'],out['startup-release.py']=monitoring_r9.sources(out['startup-validation.py'],out['startup-release.py'])
    text=out['candidate-inspect.py'].decode().replace('.gc/worker-evidence/ga-e0t1.20/r8',startup.EVIDENCE)
    out['candidate-inspect.py']=text.encode()
    text=retarget(before['operator/AMEND-STARTUP-R8.sh'].decode())
    text=text.replace('AMEND-STARTUP-R8','AMEND-STARTUP-R9').replace('startup-amendment-r8','startup-amendment-r9').replace('amend-startup-r8-','amend-startup-r9-')
    text=re.sub(r'(?m)^STEP_SHA=[0-9a-f]{64}$','STEP_SHA=AMEND_EXECUTOR_SHA',text)
    out['operator/AMEND-STARTUP-R9.sh']=text.encode()
    text=out['test_contract.py'].decode().replace(repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    text=text.replace(repr(prior_workspace.PRIOR_FILES),repr(workspace.PRIOR_FILES)).replace("b'/r8/report.json\\0'","b'/r9/report.json\\0'")
    out['test_contract.py']=text.encode()
    preserve=HISTORICAL|COMPLETED|set(startup.components())|{'recovered-claim-r9.py','workspace-r9.py','prior-startup-validation-r8.py'}
    history={n:{sha(raw)} for n,raw in before.items()}
    pattern=re.compile(r"(?P<quote>['\"])(?P<digest>[0-9a-f]{64})(?P=quote)|(?P<assignment>^[A-Z_]+_SHA=)(?P<shell>[0-9a-f]{64})$",re.M)
    for _ in range(24):
        for n,raw in out.items():history.setdefault(n,set()).add(sha(raw))
        mapping={a:sha(out[n]) for n,values in history.items() for a in values if a!=sha(out[n])}
        for a,z in [('startup-amendment-r8.json','startup-amendment-r9.json'),('recovered-claim-r8.py','recovered-claim-r9.py'),('workspace-r8.py','workspace-r9.py'),('permissions-baseline-r8.py','permissions-baseline-r9.py')]:
            mapping[sha(before[a])]=sha(out[z])
        newer={}
        for n,raw in out.items():
            if n.endswith(('.py','.sh')) and n not in preserve:
                text=raw.decode().replace('AMEND_EXECUTOR_SHA',sha(out['startup-amendment-r9.py']))
                def bind(m):
                    return m['quote']+mapping.get(m['digest'],m['digest'])+m['quote'] if m['quote'] else m['assignment']+mapping.get(m['shell'],m['shell'])
                raw=pattern.sub(bind,text).encode()
            newer[n]=raw
        if newer==out:break
        out=newer
    else:raise RuntimeError('R9 binding graph did not settle')
    for n,raw in out.items():
        if n.endswith('.py'):ast.parse(raw,filename=n)
    for n in HISTORICAL & before.keys():assert out[n]==before[n],n
    return before,out


def main(output):
    root=Path(output);assert not root.exists(),'create-only R9 window'
    before,out=assemble();root.mkdir(mode=0o700)
    for n,raw in out.items():
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        p.chmod(0o755 if n.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.runtime-window-r9.v1',predecessor=BASE,
        preparation_candidate='3808f5b5b83d7e8c813cad4de5b64dcece560698',preparation_result_sha256=PREP_RESULT_SHA,
        cache_pin_ns=CACHE_PIN,authoring_files={n:sha((HERE/n).read_bytes()) for n in
        ('window_r9.py','workspace_r9.py','recovered_claim_r9.py','monitoring_r9.py','review_wait_r9.py')},
        predecessor_files={n:sha(v) for n,v in before.items()},files={n:sha(v) for n,v in out.items()},
        execution_admitted=False,completed_operations_replayed=False)
    with (root/'assembly.json').open('x') as f:json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__':main(*sys.argv[1:])
