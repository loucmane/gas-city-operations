"""Complete create-only R7 operational successor; product work remains worker-only."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

import build
import protocol_r7 as protocol
import startup_r5
import startup_r7
import startup_r7b
import window_r6
import recovered_claim_r6 as prior_recovery
import recovered_claim_r7 as recovery
import workspace_r7 as workspace

HERE=Path(__file__).parent
PREP=Path(startup_r7b.ROOT)
PREP_RESULT_SHA='ecd7512d4ea84340374514acf91a16a27ad33053fd6a1bc68a517eb3be54d24f'
OBSERVATION='/var/tmp/ga-e0t1.20-terminal-20260928-r6/observed-after.json'
OBSERVATION_SHA='4da0cc43981ff042e82319f4dd9f2c5c9d8811fed5c716d532cd83c274f690d3'
CACHE_PREV=1790604770227789531
ROOTS={z:z.replace('20260928-r6','20260928-r7').replace('.20-r6-','.20-r7-')
       for z in window_r6.ROOTS.values() if '20260928-r6' in z or '.20-r6-' in z}
ROOTS['ga-e0t1.20-integrity-20260928-r8']='ga-e0t1.20-integrity-20260928-r9'
HISTORICAL=window_r6.HISTORICAL|{'worker-startup-r6.py','PRECLAIM-R6.md','prompt-prep-r6.py',
    'recovered-claim-r6.py','startup-amendment-r6.py','startup-amendment-r6.json',
    'operator/AMEND-STARTUP-R6.sh','operator/PROMPT-PREP-R6.sh'}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def module(raw):return startup_r5.source_module(raw,'r7_offline')


def frozen():
    manifest=json.loads(protocol.frozen('assembly.json'))
    out={name:protocol.frozen(name) for name in manifest['files']}
    assert {n:sha(v) for n,v in out.items()}==manifest['files']
    return out


def prep():
    raw=(PREP/'result.json').read_bytes();assert sha(raw)==PREP_RESULT_SHA
    r=json.loads(raw)
    assert r['ok'] is True and r['installed'] is False and r['worker_launched'] is False
    assert r['preparation_only'] is True and r['execution_authorized_by_this_result'] is False
    assert r['recovery_result_sha256']==startup_r7.RECOVERY_SHA and r['prior_close_sha256']==startup_r7.CLOSE_SHA
    for name,key in [('city.isolated.toml','city_after_sha256'),('receipt.final.json','receipt_after_sha256'),
                     ('city.baseline.toml','city_before_sha256'),('receipt.before.json','receipt_before_sha256')]:
        assert sha((PREP/name).read_bytes())==r[key]
    return r


def retarget(text):
    for a,z in ROOTS.items():text=text.replace(a,z)
    return text


def assemble(cache_ns):
    assert type(cache_ns) is int and cache_ns>=CACHE_PREV,'cache pin'
    before=frozen();out=dict(before);result=prep();old=module(before['window-base-r11.py'])
    for name,raw in before.items():
        if name not in HISTORICAL:out[name]=retarget(raw.decode()).encode()
    prepared=startup_r7.components()
    for name,raw in prepared.items():
        if name not in ('startup-validation-r7.py','startup-release-r7-draft.py','operator/PROMPT-PREP-R7.sh'):
            out[name]=raw
    out.update(startup_r7b.components())
    for name in ('operator/AMEND-STARTUP-R6.sh','operator/PROMPT-PREP-R7.sh','operator/PROMPT-PREP-R7B.sh'):
        raw=before[name] if name in before else (prepared[name] if name in prepared else out[name])
        out[name]=b'#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'+raw.split(b'\n',1)[1]
    out['recovered-claim-r7.py']=(HERE/'recovered_claim_r7.py').read_bytes()
    out['workspace-r7.py']=(HERE/'workspace_r7.py').read_bytes()
    out['prior-startup-validation-r6.py']=before['startup-validation.py']
    old_contract=module(before['contract.py'])
    note_before=old_contract.BOUND_NOTE+'\n'+recovery.STARTUP
    append=('R7 append-forward startup amendment for ga-e0t1.20. Use '+str(build.O/build.NEW/'PRECLAIM-R7.md')+
        ' sha256 '+sha(out['PRECLAIM-R7.md'])+' and worker-startup-r7.py sha256 '+sha(out['worker-startup-r7.py'])+
        '. Supersede only startup references. Preserve exact closed ci-6gwp8 claim progress-stall annotations and startup files. '
        'The coordinator has inspected and disposed the old stopped window. No permission route workspace base or signing change. '
        'Fresh same-session startup proof and exact source release remain mandatory. Store all new evidence in '+protocol.EVIDENCE+'.')
    amendment=dict(schema='ga-e0t1.20.startup-amendment.v1',before_note=note_before,append_note=append,
        after_note=note_before+'\n'+append,worker_probe_sha256=sha(out['worker-startup-r7.py']),
        prompt_sha256=sha(out['PRECLAIM-R7.md']),source_release_required=True,
        completed_bind_and_route_must_not_replay=True)
    out['startup-amendment-r7.json']=(json.dumps(amendment,sort_keys=True,indent=2)+'\n').encode()
    text=before['contract.py'].decode()
    text=build.once(text,'BOUND_NOTE = '+repr(old_contract.BOUND_NOTE),'BOUND_NOTE = '+repr(amendment['after_note']))
    text=build.once(text,repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    text=build.once(text,"        require(value.get('started_at')", "        require(value.get('labels')==['needs/operator'], 'prior attention label drift')\n        require(value.get('started_at')")
    text=build.once(text,"session['id']!='ci-rks41' and session['session_name']!='codex-ci-rks41'",
        "session['id']!='ci-6gwp8' and session['session_name']!='codex-ci-6gwp8'")
    text=build.once(text,"    expected.add(b'?? .codex/hooks.json')",
        "    expected.update(b'!! '+p.encode() for p in "+repr(workspace.PRIOR_FILES)+")\n    expected.add(b'?? .codex/hooks.json')")
    text=build.once(text,"    evidence_root = '.gc/worker-evidence/'+TASK+'/'", "    evidence_root = "+repr(protocol.EVIDENCE+'/'))
    text=build.once(text,"        elif code in (b'??', b'!!') and path.startswith(evidence_root):",
        "        elif code == b'!!' and path in "+repr(workspace.PRIOR_FILES)+":\n"
        "            pass  # exact prior bytes are independently protected by workspace baseline\n"
        "        elif code in (b'??', b'!!') and path.startswith(evidence_root):")
    out['contract.py']=text.encode()
    for name in ('startup-amendment-r7.py','continuation-admission.py'):
        text=retarget(before['startup-amendment-r6.py' if name.startswith('startup-amendment') else name].decode())
        text=text.replace('startup-amendment-r6.json','startup-amendment-r7.json').replace('recovered-claim-r6.py','recovered-claim-r7.py')
        out[name]=text.encode()
    text=out['window-base-r11.py'].decode()
    # Observation is historical, not the as-yet nonexistent R7 terminal.
    text=build.once(text,repr(str(old.ACCEPTED)),repr(OBSERVATION))
    for a,z in [(str(old.PREP),str(PREP)),(old.ACCEPTED_SHA,OBSERVATION_SHA),
                ('/var/tmp/ga-e0t1.20-terminal-20260928-r5/result.json',startup_r7.RECOVERY)]:
        text=build.once(text,repr(a),repr(z))
    prior_terminal='/var/tmp/ga-e0t1.20-terminal-20260928-r5/result.json'
    prior_raw=Path(prior_terminal).read_bytes()
    text=build.once(text,repr(sha(prior_raw)),repr(startup_r7.RECOVERY_SHA))
    for a,z in [(window_r6.PREP_RESULT_SHA,PREP_RESULT_SHA),(old.CITY_SHA[1],result['city_after_sha256']),
                (old.RECEIPT_SHA[1],result['receipt_after_sha256']),(old.REVISION[1],result['revision_after']),
                (window_r6.startup.CLOSE,startup_r7.CLOSE),(window_r6.startup.CLOSE_SHA,startup_r7.CLOSE_SHA)]:
        text=build.once(text,repr(a),repr(z))
    text=build.once(text,"closed['closed_session']=='ci-rks41'","closed['closed_session']=='ci-6gwp8'")
    text=build.once(text,"require(not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r5/proof.json').exists(), 'old source release')",
        "require(all(not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r6',n).exists() for n in ('proof.json','nudge-intent.json','result.json')), 'old source release')")
    text=build.once(text,'CACHE_PREV_NS = '+str(old.CACHE_PREV_NS),'CACHE_PREV_NS = '+str(CACHE_PREV))
    text=build.once(text,'CACHE_PINNED_NS = '+str(old.CACHE_PINNED_NS),'CACHE_PINNED_NS = '+str(cache_ns))
    text=build.once(text,"        restored=json.loads(read(Path('/var/tmp/ga-e0t1.20-window-20260928-r4/workspace-before.json'),'9ac54bc065f8407cae1d0e5e21befdb4bc99ee43a87e157c7e1501d8bf6b8994'))\n        launch.initial_runtime_image(restored,workspace_before,contract().RUNTIME_IMAGE)",
        "        module(HERE/'workspace-r7.py','WORKSPACE_SHA').verify(types.SimpleNamespace(**globals()),workspace_before,contract().RUNTIME_IMAGE)")
    out['window-base-r11.py']=text.encode()
    text=protocol.validator_source()
    assert text.count(repr(prior_recovery.CLOSED_METADATA))==2
    text=text.replace(repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    text=build.once(text,
        "            names = sorted(path.iterdir())\n"
        "            for child in names:visit(child)\n"
        "            require(sorted(path.iterdir()) == names and path.lstat() == s, 'workspace changed during walk')",
        "            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)\n"
        "            try:\n"
        "                require(os.fstat(fd)==s,'workspace directory open drift')\n"
        "                names=sorted(os.listdir(fd))\n"
        "                for name in names:visit(path/name)\n"
        "                require(sorted(os.listdir(fd))==names and os.fstat(fd)==s and path.lstat()==s,\n"
        "                        'workspace changed during walk')\n"
        "            finally:os.close(fd)")
    out['startup-validation.py']=text.encode()
    text=retarget(protocol.release_source(sha(out['runtime-process-r7.py'])))
    # The new branching process graph must retain the old prompt-body proof.
    text=build.replace_function(text,'worker_identity',
        "def worker_identity(pane, session, validator, read, runtime):\n"
        "    proof=runtime.worker_identity(pane,session,validator,read)\n"
        "    raw=runtime.proc_bytes(runtime.PROC/str(pane)/'cmdline',1<<20)\n"
        "    require(raw.endswith(b'\\0') and raw!=b'\\0','prompt argv encoding')\n"
        "    argv=raw[:-1].decode('utf-8','strict').split('\\0')\n"
        "    require(hashlib.sha256(raw[:-1]).hexdigest()==proof['chain'][0]['argv_sha256'],'prompt argv changed')\n"
        "    helper=load(HERE/'launch-contract-r5.py',"+repr(sha(out['launch-contract-r5.py']))+",read)\n"
        "    body=read(HERE/'PRECLAIM-R7.md').decode('utf-8','strict')\n"
        "    require(hashlib.sha256(body.encode()).hexdigest()=="+repr(sha(out['PRECLAIM-R7.md']))+",'launch prompt file drift')\n"
        "    require(helper.prompt_body(argv[-1],body)=='53682c1d8952f8f6345813a1519e9ee76ce72c70145b85de2663e80540c3eae8','assigned skills suffix differs')\n"
        "    runtime.revalidate(proof,validator,read)\n"
        "    return proof\n")
    out['startup-release.py']=text.encode()
    text=out['candidate-inspect.py'].decode()
    text=build.once(text,"evidence_root = w.WORK/'.gc/worker-evidence/ga-e0t1.20'","evidence_root = w.WORK/"+repr(protocol.EVIDENCE))
    text=build.once(text,"prefix = '.gc/worker-evidence/ga-e0t1.20/'",'prefix = '+repr(protocol.EVIDENCE+'/'))
    out['candidate-inspect.py']=text.encode()
    for name in ('window-base-r11.py','startup-release.py'):
        text=out[name].decode().replace("HERE/'worker-startup-r6.py'","HERE/'worker-startup-r7.py'").replace("HERE/'PRECLAIM-R6.md'","HERE/'PRECLAIM-R7.md'")
        text=text.replace(repr(sha(before['worker-startup-r6.py'])),repr(sha(out['worker-startup-r7.py'])))
        text=text.replace(repr(sha(before['PRECLAIM-R6.md'])),repr(sha(out['PRECLAIM-R7.md'])))
        out[name]=text.encode()
    wrapper=retarget(before['operator/AMEND-STARTUP-R6.sh'].decode())
    wrapper=wrapper.replace('AMEND-STARTUP-R6','AMEND-STARTUP-R7').replace('startup-amendment-r6','startup-amendment-r7').replace('amend-startup-r6-','amend-startup-r7-')
    wrapper=re.sub(r'(?m)^STEP_SHA=[0-9a-f]{64}$','STEP_SHA=AMEND_EXECUTOR_SHA',wrapper)
    out['operator/AMEND-STARTUP-R7.sh']=wrapper.encode()
    text=out['test_contract.py'].decode().replace(repr(prior_recovery.CLOSED_METADATA),repr(recovery.CLOSED_METADATA))
    text=build.once(text,"    task['started_at']='2026-09-28T13:01:54Z'", "    task['started_at']='2026-09-28T13:01:54Z'\n    task['labels']=['needs/operator']")
    text=build.once(text,"b'/report.json\\0'", "b'/r7/report.json\\0'")
    text=build.once(text,"set(c.RULES)|(c.RUNTIME_FILES-{'.codex/hooks.json'})", "set(c.RULES)|(c.RUNTIME_FILES-{'.codex/hooks.json'})|set("+repr(workspace.PRIOR_FILES)+")")
    out['test_contract.py']=text.encode()
    preserve=HISTORICAL|{'worker-startup-r7.py','PRECLAIM-R7.md','prompt-prep-r7.py','prompt-prep-r7b.py',
        'runtime-process-r7.py','prior-startup-validation-r6.py','recovered-claim-r7.py','workspace-r7.py'}
    history={n:{sha(raw)} for n,raw in before.items()}
    pattern=re.compile(r"(?P<quote>['\"])(?P<digest>[0-9a-f]{64})(?P=quote)|(?P<assignment>^[A-Z_]+_SHA=)(?P<shell>[0-9a-f]{64})$",re.M)
    for _ in range(24):
        for n,raw in out.items():history.setdefault(n,set()).add(sha(raw))
        mapping={a:sha(out[n]) for n,values in history.items() for a in values if a!=sha(out[n])}
        mapping[sha(before['startup-amendment-r6.json'])]=sha(out['startup-amendment-r7.json'])
        mapping[sha(before['recovered-claim-r6.py'])]=sha(out['recovered-claim-r7.py'])
        newer={}
        for name,raw in out.items():
            if name.endswith(('.py','.sh')) and name not in preserve:
                text=raw.decode().replace('WORKSPACE_SHA',sha(out['workspace-r7.py'])).replace('AMEND_EXECUTOR_SHA',sha(out['startup-amendment-r7.py']))
                def bind(m):
                    return m['quote']+mapping.get(m['digest'],m['digest'])+m['quote'] if m['quote'] else m['assignment']+mapping.get(m['shell'],m['shell'])
                raw=pattern.sub(bind,text).encode()
            newer[name]=raw
        if newer==out:break
        out=newer
    else:raise RuntimeError('R7 binding graph did not settle')
    for name,raw in out.items():
        if name.endswith('.py'):ast.parse(raw,filename=name)
    for name in HISTORICAL-{'operator/AMEND-STARTUP-R6.sh'}:
        if name in before:assert out[name]==before[name],name
    return before,out


def main(output,cache_ns):
    root=Path(output);assert not root.exists(),'create-only complete R7'
    before,out=assemble(int(cache_ns));root.mkdir(mode=0o700)
    for n,raw in out.items():
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        p.chmod(0o755 if n.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.runtime-window-r7.v1',predecessor=protocol.R6,
        preparation_candidate='bd5b64d3fb08863ea6d8d448413172109fb81d46',
        preparation_result_sha256=PREP_RESULT_SHA,cache_pin_ns=int(cache_ns),
        authoring_files={n:sha((HERE/n).read_bytes()) for n in ('window_r7.py','workspace_r7.py','recovered_claim_r7.py')},
        predecessor_files={n:sha(v) for n,v in before.items()},files={n:sha(v) for n,v in out.items()},
        execution_admitted=False,completed_operations_replayed=False)
    with (root/'assembly.json').open('x') as f:json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__': main(*sys.argv[1:])
