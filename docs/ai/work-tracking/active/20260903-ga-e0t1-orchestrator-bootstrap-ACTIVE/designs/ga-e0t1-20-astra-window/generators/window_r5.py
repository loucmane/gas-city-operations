"""Create-only complete operational R5 successor, never execute a window."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

import build
import startup_r5 as startup

PREP=Path(startup.PREP)
PREP_RESULT_SHA='1e027be4b46422ebeab0f9988b99bd57cdb803554a881f4f2b56704eb00a4a14'
AMEND=Path('/var/tmp/ga-e0t1.20-startup-amendment-20260928-r5')
OLD_WORKSPACE=Path('/var/tmp/ga-e0t1.20-window-20260928-r4/workspace-before.json')
OLD_WORKSPACE_SHA='9ac54bc065f8407cae1d0e5e21befdb4bc99ee43a87e157c7e1501d8bf6b8994'
ROOTS={
    'ga-e0t1.20-window-20260928-r4':'ga-e0t1.20-window-20260928-r5',
    'ga-e0t1.20-window-obs-20260928-r4':'ga-e0t1.20-window-obs-20260928-r5',
    'ga-e0t1.20-integrity-20260928-r6':'ga-e0t1.20-integrity-20260928-r7',
    'ga-e0t1.20-audit-%s-20260928-r4':'ga-e0t1.20-audit-%s-20260928-r5',
    'ga-e0t1.20-audit-route-20260928-r4':'ga-e0t1.20-audit-route-20260928-r5',
    'ga-e0t1.20-audit-resume-20260928-r4':'ga-e0t1.20-audit-resume-20260928-r5',
    'ga-e0t1.20-terminal-20260928-r4':'ga-e0t1.20-terminal-20260928-r5',
    'ga-e0t1.20-candidate-inspection-20260928-r4':'ga-e0t1.20-candidate-inspection-20260928-r5',
    'ga-e0t1.20-startup-release-20260928-r4':'ga-e0t1.20-startup-release-20260928-r5',
    'ga-e0t1.20-r4-close-session.json':'ga-e0t1.20-r5-close-session.json',
    'ga-e0t1.20-r4-close-drain.requested':'ga-e0t1.20-r5-close-drain.requested',
    'ga-e0t1.20-r4-close-':'ga-e0t1.20-r5-close-',
    'ga-e0t1.20-r4-hold-':'ga-e0t1.20-r5-hold-',
    'ga-e0t1.20-r4-watch-':'ga-e0t1.20-r5-watch-',
}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def prep():
    raw=(PREP/'result.json').read_bytes()
    assert sha(raw)==PREP_RESULT_SHA,'native preparation result drift'
    p=json.loads(raw)
    assert p['ok'] is True and p['installed'] is False and p['worker_launched'] is False
    assert p['preparation_only'] is True and p['execution_authorized_by_this_result'] is False
    assert p['only_unsuspended_city_core_agent']=='gascity/codex'
    for name,key in [('city.isolated.toml','city_after_sha256'),('receipt.final.json','receipt_after_sha256'),
                     ('city.baseline.toml','city_before_sha256'),('receipt.before.json','receipt_before_sha256')]:
        assert sha((PREP/name).read_bytes())==p[key],name
    return p


def assemble(cache_ns):
    before,components=startup.components()
    result=prep()
    original=startup.source_module(before['window-base-r11.py'],'r4_baseline')
    assert type(cache_ns) is int and cache_ns>=original.CACHE_PINNED_NS,'cache pin'
    out=dict(before);out.update(components)
    # Supplemental preparation is consumed, never replayable from this window.
    out['operator/PROMPT-PREP-R5.sh']=(b'#!/bin/sh\necho "COMPLETED PREPARATION - replay prohibited" >&2\nexit 125\n'+
                                      out['operator/PROMPT-PREP-R5.sh'].split(b'\n',1)[1])
    for name,raw in list(out.items()):
        if name=='prompt-prep-r5.py':continue
        text=raw.decode()
        for old,new in ROOTS.items():text=text.replace(old,new)
        out[name]=text.encode()
    # New executable assets; historical literal notes stay byte-exact.
    out['legacy-continuation-r4.py']=before['continuation-admission.py']
    out['stranded-recovery.py']=before['stranded-recovery.py']
    out['startup-amendment-contract-r5.py']=(build.HERE/'startup_amendment_contract_r5.py').read_bytes()
    text=(build.HERE/'startup-amendment-r5.py').read_text().replace('PACKAGE',str(build.O/build.NEW))
    out['startup-amendment-r5.py']=text.encode()
    text=before['continuation-admission.py'].decode()
    old="    compare_pair(current, evidence[COMPLETED/'final.json'], parent_audit=True)"
    new="""    amendment_root=Path('AMEND_ROOT')
    amendment=json.loads(w.read(HERE/'startup-amendment-r5.json','AMENDMENT_DATA_SHA'))
    exact=w.module(HERE/'startup-amendment-contract-r5.py','AMENDMENT_CONTRACT_SHA')
    before_amend=json.loads(w.read(amendment_root/'before.json'))
    after_amend=json.loads(w.read(amendment_root/'after.json'))
    applied=json.loads(w.read(amendment_root/'result.json'))
    compare_pair(before_amend,evidence[COMPLETED/'final.json'],parent_audit=True)
    exact.accepted(before_amend,after_amend,applied,amendment,compare_pair)
    compare_pair(current,after_amend,parent_audit=True)""".replace('AMEND_ROOT',str(AMEND))
    text=build.once(text,old,new)
    text=build.once(text,"TASK, PARENT = 'ga-e0t1.20', 'ga-e0t1'", "HERE=Path('"+str(build.O/build.NEW)+"')\nTASK, PARENT = 'ga-e0t1.20', 'ga-e0t1'")
    out['continuation-admission.py']=text.encode()
    text=out['window-base-r11.py'].decode()
    text=build.once(text,repr(str(original.PREP)),repr(str(PREP)))
    text=build.once(text,repr(str(original.ACCEPTED)),repr(startup.PRIOR_TERMINAL+'/observed-after.json'))
    text=build.once(text,repr(original.ACCEPTED_SHA),repr(startup.PRIOR_OBSERVATION))
    text=build.once(text,"Path('/var/tmp/ga-e0t1.20-terminal-20260928-r3/result.json')",
                    "Path('"+startup.PRIOR_TERMINAL+"/result.json')")
    text=build.once(text,"'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'",repr(startup.PRIOR_RESULT))
    text=build.once(text,"and previous['actual_host_verified'] is True and previous['worker_launched'] is False,",
        "and previous['actual_host_verified'] is True and previous['worker_launched'] is False\n"
        "        and previous['worker_started_in_window'] is True and previous['source_release_sent'] is False\n"
        "        and previous['open_sessions']==0 and previous['terminal_suspension_endpoint_bound'] is True,")
    text=build.once(text,"'c68c43bf4c5103b1ed9df95ab88a0f33dd7f30fc6cfe8f686635788ea5506f7f'",repr(PREP_RESULT_SHA))
    for old,new in [(original.CITY_SHA[1],result['city_after_sha256']),
                    (original.RECEIPT_SHA[1],result['receipt_after_sha256']),
                    (original.REVISION[1],result['revision_after'])]:
        text=build.once(text,repr(old),repr(new))
    text=build.once(text,'CACHE_PREV_NS = '+str(original.CACHE_PREV_NS),'CACHE_PREV_NS = '+str(original.CACHE_PINNED_NS))
    text=build.once(text,'CACHE_PINNED_NS = '+str(original.CACHE_PINNED_NS),'CACHE_PINNED_NS = '+str(cache_ns))
    marker="        require(workspace_before==validator.workspace_image(WORK,probe.read_regular),'workspace baseline drift')"
    extra="""        probe.verified_hook()
        launch=module(HERE/'launch-contract-r5.py','LAUNCH_CONTRACT_SHA')
        restored=json.loads(read(Path('OLD_WORKSPACE'),'OLD_WORKSPACE_SHA'))
        launch.initial_runtime_image(restored,workspace_before,contract().RUNTIME_IMAGE)
""".replace('OLD_WORKSPACE_SHA',OLD_WORKSPACE_SHA).replace('OLD_WORKSPACE',str(OLD_WORKSPACE))
    text=build.once(text,marker,extra+marker)
    retry="""        launch=module(HERE/'launch-contract-r5.py','LAUNCH_CONTRACT_SHA')
        if launch.retry_status(status,census,action):
            save('suspension-'+action+'-torn-read-'+str(index)+'.json',dict(status=status,census=census))
            index+=1
            time.sleep(min(1,max(0,deadline-time.monotonic())))
            continue
"""
    text=build.once(text,'        probe=runtime_probe_partial(status)',retry+'        probe=runtime_probe_partial(status)')
    out['window-base-r11.py']=text.encode()
    # Update the inherited materialized tests to the exact expanded startup image.
    text=out['test_contract.py'].decode()
    text=build.once(text,"    return b'\\0'.join(b'!! '+path.encode() for path in c.RULES) + b'\\0'",
        "    return b'\\0'.join(b'!! '+path.encode() for path in sorted(set(c.RULES)|(c.RUNTIME_FILES-{'.codex/hooks.json'}))) + b'\\0?? .codex/hooks.json\\0'")
    text=build.once(text,"    rows=candidate_rows()+b''.join(b'!! '+path.encode()+b'\\0' for path in sorted(c.RUNTIME_FILES))",
                         '    rows=candidate_rows()')
    text=text.replace('def test_two_ignored_policy_files_only():','def test_exact_restored_runtime_and_two_policy_files():')
    out['test_contract.py']=text.encode()
    # A new, separately reviewed note append; no completed BIND/ROUTE entry.
    wrapper=before['operator/BIND.sh'].decode()
    inert='echo "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'
    assert wrapper.count(inert)==1
    wrapper=wrapper.replace(inert,'')
    wrapper=wrapper.replace('BIND.sh','AMEND-STARTUP-R5.sh').replace('bind-task-r5.py','startup-amendment-r5.py')
    wrapper=wrapper.replace('ga-e0t1.20-bind-20260927-r1','ga-e0t1.20-startup-amendment-20260928-r5')
    wrapper=wrapper.replace('/bind-$(date','/amend-startup-r5-$(date')
    wrapper=wrapper.replace('BIND REFUSED','AMEND REFUSED').replace('BIND PASS','AMEND PASS')
    wrapper=wrapper.replace('the one ga-e0t1.20 contract binding (gc.work_dir only)',
                            'only the exact append-forward startup note')
    old_pin=re.search(r'(?m)^STEP_SHA=([0-9a-f]{64})$',wrapper)[1]
    wrapper=build.once(wrapper,'STEP_SHA='+old_pin,'STEP_SHA=AMENDMENT_EXECUTOR_SHA')
    out['operator/AMEND-STARTUP-R5.sh']=wrapper.encode()
    placeholders={
        'WINDOW_BASE_SHA':'window-base-r11.py','LEGACY_CONTINUATION_SHA':'legacy-continuation-r4.py',
        'AMENDMENT_CONTRACT_SHA':'startup-amendment-contract-r5.py',
        'AMENDMENT_DATA_SHA':'startup-amendment-r5.json','AMENDMENT_EXECUTOR_SHA':'startup-amendment-r5.py',
        'LAUNCH_CONTRACT_SHA':'launch-contract-r5.py',
    }
    history={name:{sha(raw)} for name,raw in before.items()}
    for name,raw in components.items():history.setdefault(name,set()).add(sha(raw))
    preserve={'legacy-continuation-r4.py','stranded-recovery.py','prompt-prep-r5.py'}
    for _ in range(80):
        for name,raw in out.items():history.setdefault(name,set()).add(sha(raw))
        mapping={old:sha(out[name]) for name,values in history.items() for old in values if old!=sha(out[name])}
        newer={}
        for name,raw in out.items():
            if name.endswith(('.py','.sh')) and name not in preserve:
                text=raw.decode()
                for token,target in placeholders.items():text=text.replace(token,sha(out[target]))
                # Only standalone digest literals and shell assignment values;
                # never hashes embedded inside preserved historical notes.
                for old,new in mapping.items():
                    for quote in ("'",'"'):text=text.replace(quote+old+quote,quote+new+quote)
                    text=re.sub(r'(?m)(^[A-Z_]+_SHA=)'+old+r'$',lambda m:m[1]+new,text)
                if name=='startup-amendment-r5.py':
                    # The historical comparator intentionally shares the old
                    # continuation digest. It is not the new admission module.
                    text=re.sub(r"(?m)^LEGACY_SHA='[0-9a-f]{64}'$",
                                "LEGACY_SHA='"+sha(out['legacy-continuation-r4.py'])+"'",text)
                raw=text.encode()
            newer[name]=raw
        if newer==out:break
        out=newer
    else:raise RuntimeError('R5 binding graph failed to settle')
    for name,raw in out.items():
        if name.endswith('.py'):ast.parse(raw,filename=name)
    # Completed assets and the already-native-prepared prompt must not drift.
    for name in ('PRECLAIM-R5.md','worker-startup.py','launch-contract-r5.py','skills-suffix-r5.txt','prompt-prep-r5.py'):
        assert out[name]==components[name],name
    assert sha(out['PRECLAIM-R5.md'])==result['prompt_sha256']
    assert out['legacy-continuation-r4.py']==before['continuation-admission.py']
    return before,out


def main(output,cache_ns):
    root=Path(output);assert not root.exists(),'create-only complete R5 assembly'
    before,out=assemble(int(cache_ns));root.mkdir(mode=0o700)
    for name,raw in out.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(raw)
        path.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.restored-startup-r5.v1',predecessor=startup.R4,
        recovery=startup.R4_RECOVERY,preparation_candidate='481e97df3621e570b105d00b63f884e608254770',
        preparation_result_sha256=PREP_RESULT_SHA,cache_pin_ns=int(cache_ns),
        authoring_files={n:sha((rbase/n).read_bytes()) for rbase,n in
            [(build.HERE,n) for n in ('window_r5.py','startup_r5.py','launch_contract_r5.py',
              'startup-amendment-r5.py','startup_amendment_contract_r5.py')]},
        predecessor_files={n:sha(b) for n,b in before.items()},
        files={n:sha(b) for n,b in out.items()},execution_admitted=False,completed_operations_replayed=False)
    with (root/'assembly.json').open('x') as f:json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__':main(*sys.argv[1:])
