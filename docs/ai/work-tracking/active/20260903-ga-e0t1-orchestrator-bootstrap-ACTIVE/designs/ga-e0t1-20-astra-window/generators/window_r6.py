"""Create-only complete R6 successor from exact consumed R5 artifacts."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

import build
import startup_r6 as startup
import startup_r5
import recovered_claim_r6 as recovery

R5 = startup.R5
PREP_RESULT_SHA = 'fa5ece092f59610207f2ec4ac8570efc989a7c7a3e34486618d6f9c5c7504686'
OBSERVATION = '/var/tmp/ga-e0t1.20-terminal-20260928-r5/observed-after.json'
OBSERVATION_SHA = 'be40602f3f1a4bcf53fc5d4a5111b8b695f58dc633506b16c17a7a21bf469fe3'
CACHE_PREV = 1790599221652837172
ROOTS = {
    'ga-e0t1.20-window-20260928-r5':'ga-e0t1.20-window-20260928-r6',
    'ga-e0t1.20-window-obs-20260928-r5':'ga-e0t1.20-window-obs-20260928-r6',
    'ga-e0t1.20-integrity-20260928-r7':'ga-e0t1.20-integrity-20260928-r8',
    'ga-e0t1.20-audit-%s-20260928-r5':'ga-e0t1.20-audit-%s-20260928-r6',
    'ga-e0t1.20-audit-route-20260928-r5':'ga-e0t1.20-audit-route-20260928-r6',
    'ga-e0t1.20-audit-resume-20260928-r5':'ga-e0t1.20-audit-resume-20260928-r6',
    'ga-e0t1.20-terminal-20260928-r5':'ga-e0t1.20-terminal-20260928-r6',
    'ga-e0t1.20-candidate-inspection-20260928-r5':'ga-e0t1.20-candidate-inspection-20260928-r6',
    'ga-e0t1.20-startup-release-20260928-r5':'ga-e0t1.20-startup-release-20260928-r6',
    'ga-e0t1.20-startup-amendment-20260928-r5':'ga-e0t1.20-startup-amendment-20260928-r6',
    'ga-e0t1.20-r5-close-session.json':'ga-e0t1.20-r6-close-session.json',
    'ga-e0t1.20-r5-close-drain.requested':'ga-e0t1.20-r6-close-drain.requested',
    'ga-e0t1.20-r5-close-':'ga-e0t1.20-r6-close-',
    'ga-e0t1.20-r5-hold-':'ga-e0t1.20-r6-hold-',
    'ga-e0t1.20-r5-watch-':'ga-e0t1.20-r6-watch-',
}
HISTORICAL = {'legacy-continuation-r4.py','stranded-recovery.py','stranded-r4-recovery.py',
    'prompt-prep-r5.py','worker-startup.py','PRECLAIM-R5.md',
    'startup-amendment-r5.py','startup-amendment-r5.json',
    'operator/AMEND-STARTUP-R5.sh'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def frozen():
    manifest = json.loads(startup.frozen('assembly.json'))
    out = {n:startup.frozen(n) for n in manifest['files']}
    assert {n:sha(v) for n,v in out.items()} == manifest['files']
    return out


def prep():
    root = Path(startup.ROOT)
    raw = (root/'result.json').read_bytes()
    assert sha(raw)==PREP_RESULT_SHA
    value=json.loads(raw)
    assert value['ok'] is True and value['installed'] is False and value['worker_launched'] is False
    assert value['preparation_only'] is True and value['execution_authorized_by_this_result'] is False
    assert value['recovery_result_sha256']==startup.RECOVERY_SHA and value['prior_close_sha256']==startup.CLOSE_SHA
    for name,key in [('city.isolated.toml','city_after_sha256'),('receipt.final.json','receipt_after_sha256'),
                     ('city.baseline.toml','city_before_sha256'),('receipt.before.json','receipt_before_sha256')]:
        assert sha((root/name).read_bytes())==value[key]
    return value


def assemble(cache_ns):
    assert type(cache_ns) is int and cache_ns>=CACHE_PREV, 'cache pin'
    before=frozen(); out=dict(before); result=prep()
    old=startup_r5.source_module(before['window-base-r11.py'],'r5_old')
    # Retarget only new operational attempts, not consumed historical assets.
    for name,raw in before.items():
        if name in HISTORICAL: continue
        text=raw.decode()
        for a,z in ROOTS.items(): text=text.replace(a,z)
        out[name]=text.encode()
    prepared=startup.components()
    for name in ('worker-startup-r6.py','PRECLAIM-R6.md','prompt-prep-r6.py'):
        out[name]=prepared[name]
    for name in ('operator/PROMPT-PREP-R5.sh','operator/AMEND-STARTUP-R5.sh'):
        out[name]=b'#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'+before[name].split(b'\n',1)[1]
    out['operator/PROMPT-PREP-R6.sh']=b'#!/bin/sh\necho "COMPLETED PREPARATION - replay prohibited" >&2\nexit 125\n'+prepared['operator/PROMPT-PREP-R6.sh'].split(b'\n',1)[1]
    out['recovered-claim-r6.py']=(build.HERE/'recovered_claim_r6.py').read_bytes()
    old_contract=startup_r5.source_module(before['contract.py'],'old_contract')
    note_before=old_contract.BOUND_NOTE+'\n'+recovery.STOPPED
    append=('R6 append-forward startup amendment for ga-e0t1.20. Use '+
        str(build.O/build.NEW/'PRECLAIM-R6.md')+' sha256 '+sha(out['PRECLAIM-R6.md'])+
        ' and worker-startup-r6.py sha256 '+sha(out['worker-startup-r6.py'])+
        '. These supersede only startup references. The failed ci-rks41 claim STOPPED note and exact supported close remain history. '
        'No credential permissions scope route workspace base or signing change. Fresh same-session startup proof and source release remain mandatory.')
    amendment=dict(schema='ga-e0t1.20.startup-amendment.v1',before_note=note_before,
        append_note=append,after_note=note_before+'\n'+append,
        worker_probe_sha256=sha(out['worker-startup-r6.py']),prompt_sha256=sha(out['PRECLAIM-R6.md']),
        source_release_required=True,completed_bind_and_route_must_not_replay=True)
    out['startup-amendment-r6.json']=(json.dumps(amendment,sort_keys=True,indent=2)+'\n').encode()
    text=before['contract.py'].decode()
    text=build.once(text,'BOUND_NOTE = '+repr(old_contract.BOUND_NOTE),'BOUND_NOTE = '+repr(amendment['after_note']))
    text=build.once(text,"        expected['gc.routed_to'] = TARGET",
        "        expected.update("+repr(recovery.CLOSED_METADATA)+")\n"
        "        require(value.get('started_at')=='2026-09-28T13:01:54Z', 'prior claim start drift')")
    out['contract.py']=text.encode()
    # The pure recovery binder verifies the actual old claim and native close.
    text=before['startup-amendment-r5.py'].decode()
    for a,z in ROOTS.items():text=text.replace(a,z)
    text=text.replace('startup-amendment-r5.json','startup-amendment-r6.json')
    text=build.once(text,"    legacy.compare_pair(before,completed[legacy.COMPLETED/'final.json'],parent_audit=True)",
        "    prior=w.module(HERE/'recovered-claim-r6.py','RECOVERED_SHA')\n"
        "    prior.verify(w,before,legacy.normalized,legacy.compare_pair)")
    out['startup-amendment-r6.py']=text.encode()
    text=out['continuation-admission.py'].decode().replace('startup-amendment-r5.json','startup-amendment-r6.json')
    text=build.once(text,"    compare_pair(before_amend,evidence[COMPLETED/'final.json'],parent_audit=True)",
        "    prior=w.module(HERE/'recovered-claim-r6.py','RECOVERED_SHA')\n"
        "    prior.verify(w,before_amend,normalized,compare_pair)")
    out['continuation-admission.py']=text.encode()
    # Exact native preparation and complete R5 restoration, not relabeled evidence.
    text=out['window-base-r11.py'].decode()
    for a,z in [(str(old.PREP),startup.ROOT),(str(old.ACCEPTED),OBSERVATION),
                (old.ACCEPTED_SHA,OBSERVATION_SHA),
                ('/var/tmp/ga-e0t1.20-terminal-20260928-r4/result.json',startup.RECOVERY),
                ('459cacbbaf67e60f741af656277ebf11161a4abe3bab49637e7407db40f16438',startup.RECOVERY_SHA),
                ('1e027be4b46422ebeab0f9988b99bd57cdb803554a881f4f2b56704eb00a4a14',PREP_RESULT_SHA),
                (old.CITY_SHA[1],result['city_after_sha256']),
                (old.RECEIPT_SHA[1],result['receipt_after_sha256']),
                (old.REVISION[1],result['revision_after'])]:
        text=build.once(text,repr(a),repr(z))
    text=build.once(text,
        "        and previous['worker_started_in_window'] is True and previous['source_release_sent'] is False\n"
        "        and previous['open_sessions']==0 and previous['terminal_suspension_endpoint_bound'] is True,",
        "        and previous['root_cache_protected_read_only'] is True\n"
        "        and previous['terminal_suspension_endpoint_bound'] is True,")
    text=build.once(text,"    # The R9-era diagnostic pins",
        "    closed=json.loads(read(Path("+repr(startup.CLOSE)+"),"+repr(startup.CLOSE_SHA)+"))\n"
        "    require(closed['ok'] is True and closed['closed_session']=='ci-rks41'\n"
        "        and closed['open_sessions']==0 and closed['city_tmux_sessions']==0\n"
        "        and closed['worktree_processes']==0, 'prior close lacks zero residue')\n"
        "    require(not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r5/proof.json').exists(), 'old source release')\n"
        "    # The R9-era diagnostic pins")
    text=build.once(text,'CACHE_PREV_NS = '+str(old.CACHE_PREV_NS),'CACHE_PREV_NS = '+str(CACHE_PREV))
    text=build.once(text,'CACHE_PINNED_NS = '+str(old.CACHE_PINNED_NS),'CACHE_PINNED_NS = '+str(cache_ns))
    out['window-base-r11.py']=text.encode()
    # The already reviewed R6 worker bytes are used unchanged by all consumers.
    for name in ('window-base-r11.py','startup-release.py','candidate-inspect.py'):
        text=out[name].decode().replace("HERE/'worker-startup.py'","HERE/'worker-startup-r6.py'")
        text=text.replace("HERE/'PRECLAIM-R5.md'","HERE/'PRECLAIM-R6.md'")
        for a,z in [(sha(before['worker-startup.py']),sha(out['worker-startup-r6.py'])),
                    (sha(before['PRECLAIM-R5.md']),sha(out['PRECLAIM-R6.md']))]:
            text=text.replace(repr(a),repr(z))
        out[name]=text.encode()
    # Reclaim bookkeeping is not a fresh-task timestamp, nor the worker Git
    # branch. Core stamps the selected rig store's branch (cmd_hook_claim.go),
    # while the actual sandbox probe and process checks prove the worktree.
    text=before['startup-validation.py'].decode()
    marker="    require('started_at' not in routed, 'routed task already has a start time')"
    retry_time=("    if 'started_at' in routed:\n"
        "        require(routed['started_at']=='2026-09-28T13:01:54Z'\n"
        "            and routed.get('metadata')=="+repr(recovery.CLOSED_METADATA)+", 'unbound prior claim')\n"
        "        started=native_time(task.get('started_at'))\n"
        "        prior=native_time(routed['started_at'])\n"
        "        routed_at=native_time(routed.get('updated_at'))\n"
        "        session_at=native_time(session.get('created_at'))\n"
        "        updated=native_time(task.get('updated_at'))\n"
        "        require(prior<=routed_at<=session_at<=updated, 'reclaim timestamp order')\n"
        "        require(started==prior or session_at<=started<=updated, 'reclaim start time drift')\n"
        "        return\n"+marker)
    text=build.once(text,marker,retry_time)
    text=build.once(text,"    if 'gc.work_branch' in task.get('metadata',{}):expected['gc.work_branch']=BRANCH",
        "    if 'started_at' in routed:\n"
        "        require(routed['metadata']=="+repr(recovery.CLOSED_METADATA)+", 'closed claim metadata differs')\n"
        "        # The exact rig-store branch remains bookkeeping only.\n"
        "    elif 'gc.work_branch' in task.get('metadata',{}):expected['gc.work_branch']=BRANCH")
    out['startup-validation.py']=text.encode()
    wrapper=before['operator/AMEND-STARTUP-R5.sh'].decode()
    wrapper=wrapper.replace('AMEND-STARTUP-R5','AMEND-STARTUP-R6').replace('startup-amendment-r5','startup-amendment-r6')
    wrapper=wrapper.replace('amend-startup-r5-','amend-startup-r6-').replace('20260928-r5','20260928-r6')
    wrapper=re.sub(r'(?m)^STEP_SHA=[0-9a-f]{64}$','STEP_SHA=AMEND_EXECUTOR_SHA',wrapper)
    out['operator/AMEND-STARTUP-R6.sh']=wrapper.encode()
    text=out['test_contract.py'].decode()
    text=build.once(text,"    task['metadata']['gc.routed_to'] = c.TARGET",
        "    task['metadata'].update("+repr(recovery.CLOSED_METADATA)+")\n"
        "    task['started_at']='2026-09-28T13:01:54Z'")
    out['test_contract.py']=text.encode()
    # Old comments cannot describe this run as claim-free.
    text=out['close-r11.py'].decode()
    text=text.replace('Its task attempt is started, so no\nnew session can start for it (taskattempt). The coordinator\'s delivery closeout closes it after the\nmerge; before any later window the audit would stop on it, as it did on ga-y49e.',
        'The closed claim remains historical metadata. A later reviewed successor must\nbind that exact native release and prove sole ready demand again. This close never retries work.')
    out['close-r11.py']=text.encode()
    placeholders={'RECOVERED_SHA':'recovered-claim-r6.py','AMEND_EXECUTOR_SHA':'startup-amendment-r6.py'}
    preserve=HISTORICAL|{'worker-startup-r6.py','PRECLAIM-R6.md','prompt-prep-r6.py',
                         'recovered-claim-r6.py'}
    # Bind changed references, excluding historical literal note strings.
    history={name:{sha(raw)} for name,raw in before.items()}
    history['startup-amendment-r6.json']={sha(before['startup-amendment-r5.json'])}
    binding_pattern=re.compile(r"(?P<quote>['\"])(?P<digest>[0-9a-f]{64})(?P=quote)|(?P<assignment>^[A-Z_]+_SHA=)(?P<shell>[0-9a-f]{64})$", re.M)
    for _ in range(20):
        for name,raw in out.items():history.setdefault(name,set()).add(sha(raw))
        mapping={a:sha(out[n]) for n,values in history.items() for a in values if a!=sha(out[n])}
        # The new amendment's data digest must not be rebound to the retained old file.
        mapping[sha(before['startup-amendment-r5.json'])]=sha(out['startup-amendment-r6.json'])
        newer={}
        for name,raw in out.items():
            if name.endswith(('.py','.sh')) and name not in preserve:
                text=raw.decode()
                for token,target in placeholders.items():text=text.replace(token,sha(out[target]))
                def bind(match):
                    if match['quote']:
                        return match['quote']+mapping.get(match['digest'],match['digest'])+match['quote']
                    return match['assignment']+mapping.get(match['shell'],match['shell'])
                text=binding_pattern.sub(bind,text)
                raw=text.encode()
            newer[name]=raw
        changed_names=[n for n in out if newer[n]!=out[n]]
        if newer==out:break
        out=newer
    else:raise RuntimeError('R6 binding graph failed to settle: '+repr(changed_names))
    for name,raw in out.items():
        if name.endswith('.py'):ast.parse(raw,filename=name)
    for name in ('worker-startup-r6.py','PRECLAIM-R6.md','prompt-prep-r6.py'):
        assert out[name]==prepared[name]
    for name in (HISTORICAL & before.keys())-{'operator/AMEND-STARTUP-R5.sh'}:
        assert out[name]==before[name],name
    return before,out


def main(output,cache_ns):
    root=Path(output);assert not root.exists(),'create-only R6 window'
    before,out=assemble(int(cache_ns));root.mkdir(mode=0o700)
    for name,raw in out.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        p.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.auth-output-window-r6.v1',predecessor=R5,
        preparation_candidate='9ce5afcd9514f147c0432f2e073612a7f9aace39',
        preparation_result_sha256=PREP_RESULT_SHA,cache_pin_ns=int(cache_ns),
        authoring_files={n:sha((build.HERE/n).read_bytes()) for n in ('window_r6.py','recovered_claim_r6.py')},
        predecessor_files={n:sha(raw) for n,raw in before.items()},
        files={n:sha(raw) for n,raw in out.items()},execution_admitted=False,
        completed_operations_replayed=False)
    with (root/'assembly.json').open('x') as f:
        json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__':
    main(*sys.argv[1:])
