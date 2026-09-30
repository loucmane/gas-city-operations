"""Create-only R11 window; exact R10 recovery and reviewed prompt-only correction."""
import ast
import json
from pathlib import Path
import re
import sys

import build
import startup_r5
import startup_r11 as startup
import window_r10
import recovered_claim_r10 as prior_recovery
import recovered_claim_r11 as recovery
import workspace_r10 as prior_workspace
import workspace_r11 as workspace

HERE=Path(__file__).parent
BASE=startup.BASE
PREP=Path(startup.ROOT)
PREP_RESULT_SHA='c1869bb42078ed77d2506a428d7ae038cac19e9a11dca95b5593e2f1a2632391'
# Final exact capture after all coordinator logging and workflow verification.
OBSERVATION='/tmp/ga-e0t1-20-readonly-baseline-20260929-r16/observed.json'
OBSERVATION_SHA='2c5300a9ce628e8ca617f1016ec9d7a153ea274a951ff7e9328e6f011b75870b'
CACHE_PIN=1790649221451394669
ROOTS={v:v.replace('20260929-r10','20260929-r11').replace('.20-r10-','.20-r11-')
       for v in window_r10.ROOTS.values() if '20260929-r10' in v or '.20-r10-' in v}
ROOTS['ga-e0t1.20-integrity-20260929-r12']='ga-e0t1.20-integrity-20260929-r13'
HISTORICAL=window_r10.HISTORICAL|{'worker-startup-r10.py','PRECLAIM-R10.md','prompt-prep-r10.py',
    'recovered-claim-r10.py','workspace-r10.py','prior-startup-validation-r9.py',
    'permissions-baseline-r10.py','startup-amendment-r10.py','startup-amendment-r10.json',
    'operator/PROMPT-PREP-R10.sh'}
COMPLETED={'operator/AMEND-STARTUP-R10.sh','operator/PROMPT-PREP-R11.sh'}
sha=build.sha


def module(raw):return startup_r5.source_module(raw,'r11_offline')


def frozen():
    manifest=json.loads(build.git('show',BASE+':'+build.NEW+'/assembly.json'))
    out={n:build.git('show',BASE+':'+build.NEW+'/'+n) for n in manifest['files']}
    assert {n:sha(v) for n,v in out.items()}==manifest['files'],'R10 assembly binding'
    return out


def prep():
    raw=(PREP/'result.json').read_bytes();assert sha(raw)==PREP_RESULT_SHA
    r=json.loads(raw)
    assert r['ok'] is True and r['installed'] is False and r['worker_launched'] is False
    assert r['preparation_only'] is True and r['execution_authorized_by_this_result'] is False
    assert r['prior_close_sha256']==startup.CLOSE_SHA
    assert r['permissions_result_sha256']=='baae65a63de589bc354a11d8ea673bded479be63aa004170256430073c44c862'
    assert r['permissions_postimage_sha256']=='709e74b448d50a0f4fc5a3fcaa7fc1728b5b364cfe8a76082ffe90cbd7e03010'
    assert r['preserved_r10_transcript_sha256']=='7368ea8e311109d97e479ab7308ea8dd9ccec11b85ca860c0fb761c0cf71ab0d'
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
    out['recovered-claim-r11.py']=(HERE/'recovered_claim_r11.py').read_bytes()
    out['workspace-r11.py']=(HERE/'workspace_r11.py').read_bytes()
    out['prior-startup-validation-r10.py']=before['startup-validation.py']
    old_contract=module(before['contract.py'])
    note_before=old_contract.BOUND_NOTE+'\n'+recovery.STARTUP
    append=('R11 append-forward startup amendment for ga-e0t1.20. Use '+str(build.O/build.NEW/'PRECLAIM-R11.md')+
        ' sha256 '+sha(out['PRECLAIM-R11.md'])+' and worker-startup-r11.py sha256 '+sha(out['worker-startup-r11.py'])+
        '. Supersede only startup references. Omit the optional sandbox_permissions field under native never mode. '
        'Preserve exact closed ci-9dp7z claim and native progress-stall annotations and all startup files. '
        'No route workspace base provider permission or signing change. Fresh same-session startup refusal proof and '
        'exact source release remain mandatory. Store new evidence in '+startup.EVIDENCE+'.')
    amendment=dict(schema='ga-e0t1.20.startup-amendment.v1',before_note=note_before,append_note=append,
        after_note=note_before+'\n'+append,worker_probe_sha256=sha(out['worker-startup-r11.py']),
        prompt_sha256=sha(out['PRECLAIM-R11.md']),source_release_required=True,
        completed_bind_and_route_must_not_replay=True)
    out['startup-amendment-r11.json']=(json.dumps(amendment,sort_keys=True,indent=2)+'\n').encode()
    text=before['contract.py'].decode()
    text=build.once(text,'BOUND_NOTE = '+repr(old_contract.BOUND_NOTE),'BOUND_NOTE = '+repr(amendment['after_note']))
    text=build.once(text,repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    text=build.once(text,"session['id']!='ci-g12rt' and session['session_name']!='codex-ci-g12rt'",
        "session['id']!='ci-9dp7z' and session['session_name']!='codex-ci-9dp7z'")
    assert text.count(repr(prior_workspace.PRIOR_FILES))==2
    text=text.replace(repr(prior_workspace.PRIOR_FILES),repr(workspace.PRIOR_FILES))
    text=build.once(text,repr('.gc/worker-evidence/ga-e0t1.20/r10/'),repr(startup.EVIDENCE+'/'))
    out['contract.py']=text.encode()
    for n,source in [('startup-amendment-r11.py','startup-amendment-r10.py'),('continuation-admission.py','continuation-admission.py')]:
        text=retarget(before[source].decode())
        text=text.replace('startup-amendment-r10.json','startup-amendment-r11.json').replace('recovered-claim-r10.py','recovered-claim-r11.py')
        out[n]=text.encode()
    text=out['window-base-r11.py'].decode()
    for a,z in [(str(old.ACCEPTED),OBSERVATION),(old.ACCEPTED_SHA,OBSERVATION_SHA),
        (str(old.PREP),str(PREP)),(window_r10.PREP_RESULT_SHA,PREP_RESULT_SHA),
        (old.CITY_SHA[1],result['city_after_sha256']),(old.RECEIPT_SHA[1],result['receipt_after_sha256']),
        (old.REVISION[1],result['revision_after']),
        ('/var/tmp/ga-e0t1.20-terminal-20260929-r9/result.json','/var/tmp/ga-e0t1.20-terminal-20260929-r10/result.json'),
        (window_r10.startup.CLOSE,startup.CLOSE),(window_r10.startup.CLOSE_SHA,startup.CLOSE_SHA)]:
        text=build.once(text,repr(a),repr(z))
    text=build.once(text,"closed['closed_session']=='ci-g12rt'","closed['closed_session']=='ci-9dp7z'")
    text=build.once(text,
        "    require(all(not Path('/var/tmp/ga-e0t1.20-startup-release-20260929-r9',n).exists() for n in ('proof.json','nudge-intent.json','result.json')), 'old source release')",
        "    # Preserve the consumed R10 enqueue attempt instead of asserting absence.\n" +
        "\n".join("    read(Path("+repr(str(p))+"), "+repr(pin)+")" for p,pin in recovery.PINS.items() if p.parent==recovery.RELEASE))
    text=build.once(text,'CACHE_PREV_NS = '+str(old.CACHE_PREV_NS),'CACHE_PREV_NS = '+str(CACHE_PIN))
    text=build.once(text,'CACHE_PINNED_NS = '+str(old.CACHE_PINNED_NS),'CACHE_PINNED_NS = '+str(CACHE_PIN))
    text=text.replace("HERE/'workspace-r10.py'","HERE/'workspace-r11.py'")
    text=text.replace("HERE/'permissions-baseline-r10.py'","HERE/'permissions-baseline-r11.py'")
    out['window-base-r11.py']=text.encode()
    text=before['startup-validation.py'].decode().replace('.gc/worker-evidence/ga-e0t1.20/r10',startup.EVIDENCE)
    assert text.count(repr(prior_recovery.CLOSED_METADATA))==2
    out['startup-validation.py']=text.replace(repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA)).encode()
    for n in ('window-base-r11.py','startup-release.py'):
        text=out[n].decode().replace('worker-startup-r10.py','worker-startup-r11.py').replace('PRECLAIM-R10.md','PRECLAIM-R11.md')
        text=text.replace(sha(before['worker-startup-r10.py']),sha(out['worker-startup-r11.py']))
        text=text.replace(sha(before['PRECLAIM-R10.md']),sha(out['PRECLAIM-R11.md']))
        out[n]=text.encode()
    # R10 monitoring and completed-waiting guards are already present, unchanged.
    out['release-delivery-r11.py']=(HERE/'release_delivery_r11.py').read_bytes()
    out['release-runtime-r11.py']=(HERE/'release_runtime_r11.py').read_bytes()
    text=out['startup-release.py'].decode()
    text=build.once(text,"    common=w.module(HERE/'common-snapshot-r1.py',COMMON_SHA)",
        "    common=w.module(HERE/'common-snapshot-r1.py',COMMON_SHA)\n"+
        "    delivery=w.module(HERE/'release-delivery-r11.py',"+repr(sha(out['release-delivery-r11.py']))+")\n"+
        "    transport=w.module(HERE/'release-runtime-r11.py',"+repr(sha(out['release-runtime-r11.py']))+")")
    text=build.once(text,'    def phase(name,args):return w.phase(name,args,b,owned,timeout=90)',
        '    def phase(name,args,timeout=90):return w.phase(name,args,b,owned,timeout=timeout)')
    text=build.once(text,"        phase('source-release',w.GC+['session','nudge',s['id'],message])",
        "        delivered=transport.execute(w,phase,inspector,runtime,delivery,s,proof,message,waiting_raw,\n"+
        "            lambda:not poll.poll(0))\n"+
        "        require(delivered.get('delivered') is True,'source release not acknowledged')")
    text=build.once(text,'report_sha256=sha,worker_launched=False,worker_result_unproven=True,retry=False))',
        'report_sha256=sha,source_delivery_acknowledged=True,delivery=delivered,\n'+
        '        worker_launched=False,worker_result_unproven=True,retry=False))')
    out['startup-release.py']=text.encode()
    out['candidate-inspect.py']=out['candidate-inspect.py'].replace(b'.gc/worker-evidence/ga-e0t1.20/r10',startup.EVIDENCE.encode())
    text=retarget(before['operator/AMEND-STARTUP-R10.sh'].decode())
    text=text.replace('AMEND-STARTUP-R10','AMEND-STARTUP-R11').replace('startup-amendment-r10','startup-amendment-r11').replace('amend-startup-r10-','amend-startup-r11-')
    text=re.sub(r'(?m)^STEP_SHA=[0-9a-f]{64}$','STEP_SHA=AMEND_EXECUTOR_SHA',text)
    out['operator/AMEND-STARTUP-R11.sh']=text.encode()
    text=out['test_contract.py'].decode().replace(repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    text=text.replace(repr(prior_workspace.PRIOR_FILES),repr(workspace.PRIOR_FILES)).replace("b'/r10/report.json\\0'","b'/r11/report.json\\0'")
    out['test_contract.py']=text.encode()
    preserve=HISTORICAL|COMPLETED|set(startup.components())|{'recovered-claim-r11.py','workspace-r11.py','prior-startup-validation-r10.py','release-delivery-r11.py','release-runtime-r11.py'}
    history={n:{sha(raw)} for n,raw in before.items()}
    pattern=re.compile(r"(?P<quote>['\"])(?P<digest>[0-9a-f]{64})(?P=quote)|(?P<assignment>^[A-Z_]+_SHA=)(?P<shell>[0-9a-f]{64})$",re.M)
    for _ in range(24):
        for n,raw in out.items():history.setdefault(n,set()).add(sha(raw))
        mapping={a:sha(out[n]) for n,values in history.items() for a in values if a!=sha(out[n])}
        for a,z in [('startup-amendment-r10.json','startup-amendment-r11.json'),('recovered-claim-r10.py','recovered-claim-r11.py'),('workspace-r10.py','workspace-r11.py'),('permissions-baseline-r10.py','permissions-baseline-r11.py')]:
            mapping[sha(before[a])]=sha(out[z])
        newer={}
        for n,raw in out.items():
            if n.endswith(('.py','.sh')) and n not in preserve:
                text=raw.decode().replace('AMEND_EXECUTOR_SHA',sha(out['startup-amendment-r11.py']))
                def bind(m):
                    return m['quote']+mapping.get(m['digest'],m['digest'])+m['quote'] if m['quote'] else m['assignment']+mapping.get(m['shell'],m['shell'])
                raw=pattern.sub(bind,text).encode()
            newer[n]=raw
        if newer==out:break
        out=newer
    else:raise RuntimeError('R11 binding graph did not settle')
    for n,raw in out.items():
        if n.endswith('.py'):ast.parse(raw,filename=n)
    for n in HISTORICAL & before.keys():assert out[n]==before[n],n
    return before,out


def main(output):
    root=Path(output);assert not root.exists(),'create-only R11 window'
    before,out=assemble();root.mkdir(mode=0o700)
    for n,raw in out.items():
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        p.chmod(0o755 if n.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.runtime-window-r11.v1',predecessor=BASE,
        preparation_candidate='0808b65528812ecc88ed97e1a2cd1ab233940a43',preparation_result_sha256=PREP_RESULT_SHA,
        cache_pin_ns=CACHE_PIN,authoring_files={n:sha((HERE/n).read_bytes()) for n in
        ('window_r11.py','workspace_r11.py','recovered_claim_r11.py')},
        predecessor_files={n:sha(v) for n,v in before.items()},files={n:sha(v) for n,v in out.items()},
        execution_admitted=False,completed_operations_replayed=False)
    with (root/'assembly.json').open('x') as f:json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__':main(*sys.argv[1:])
