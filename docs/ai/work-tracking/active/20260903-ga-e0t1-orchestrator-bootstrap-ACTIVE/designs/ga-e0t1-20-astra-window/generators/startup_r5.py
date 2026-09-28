"""Append-forward startup corrections from the immutable, consumed r4.

Pure assembly and create-only draft output. This does not execute any window,
edit the worker workspace, grant permissions, or replay BIND/ROUTE/PREP.
Final live wrappers require a new native PREP result and exact independent review.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

import build
import launch_contract_r5 as lc

R4 = '78152f1d1400961978b35db610db5eef66babd71'
R4_RECOVERY = '17598e3aca0cbabd391c162f7345284f4132415c'
PREP = '/var/tmp/ga-e0t1.20-prompt-prep-20260928-r5'
PROMPT = str(build.O/build.NEW/'PRECLAIM-R5.md')
PRIOR_TERMINAL = '/var/tmp/ga-e0t1.20-terminal-20260928-r4'
PRIOR_RESULT = '459cacbbaf67e60f741af656277ebf11161a4abe3bab49637e7407db40f16438'
PRIOR_OBSERVATION = '6ef3d9a90f2c52e60a939fdd5641c53fa74bb10fb7663d2516120e09db9968d5'
SUFFIX_MARKER = '\n\n## Skills available to this session\n'
ROLLOUT = Path('/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T12-52-11-01a0e7a4-c9fb-74d1-b7c4-b3e9d4cf5269.jsonl')
ROLLOUT_SHA = 'c7a0faeb98c7fd536ab631465560dca1bfbc41fdeee8345f67cd7c8abe056721'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def frozen():
    manifest = json.loads(build.git('show', R4+':'+build.NEW+'/assembly.json'))
    out = {name:build.git('show', R4+':'+build.NEW+'/'+name) for name in manifest['files']}
    assert {name:sha(raw) for name,raw in out.items()} == manifest['files'], 'consumed r4 source drift'
    return out


def source_module(raw, name):
    import types
    m=types.ModuleType(name);m.__file__=name+'.py'
    exec(compile(raw,m.__file__,'exec'),m.__dict__)
    return m


def skills_suffix():
    # Historical rollout is an immutable observation, never new worker input
    # except the exact Core-produced skills catalog verified in source review.
    raw=ROLLOUT.read_bytes();assert sha(raw)==ROLLOUT_SHA,'rollout drift'
    values=[]
    for line in raw.splitlines():
        row=json.loads(line)
        if row.get('type')!='response_item':continue
        p=row['payload']
        if p.get('type')!='message' or p.get('role')!='user':continue
        for item in p.get('content',[]):
            value=item.get('text','')
            if value.startswith('[city] gascity/codex '):values.append(value)
    assert len(values)==1 and values[0].count(SUFFIX_MARKER)==1
    return SUFFIX_MARKER+values[0].split(SUFFIX_MARKER)[1]


def prepare_worker(before):
    raw=(build.HERE/'launch_contract_r5.py').read_bytes()
    pin=sha(raw)
    load="""def launch_contract():
    path = Path('PACKAGE/launch-contract-r5.py')
    data = read_regular(path)
    require(hashlib.sha256(data).hexdigest() == 'HELPER_SHA', 'launch contract digest')
    import types
    m=types.ModuleType('bound_launch_contract');m.__file__=str(path)
    exec(compile(data,str(path),'exec',dont_inherit=True),m.__dict__)
    return m


def verified_hook():
    helper=launch_contract();path=WORK/helper.HOOK
    raw=read_regular(path);s=path.lstat()
    helper.hook_image(raw,dict(uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink,
        type=stat.S_IFMT(s.st_mode),mode=stat.S_IMODE(s.st_mode),size=s.st_size,
        sha256=hashlib.sha256(raw).hexdigest()))
    return helper


""".replace('PACKAGE',str(build.O/build.NEW)).replace('HELPER_SHA',pin)
    text=before['worker-startup.py'].decode()
    text=build.once(text,'def main(session_id):\n',load+'def main(session_id):\n')
    text=build.once(text,"'status', '--porcelain', '--untracked-files=all'",
        "'status', '--porcelain=v1', '--untracked-files=all', '-z'")
    text=build.once(text,"    require(r.returncode == 0 and r.stdout == b'', 'worker is not pristine before probes')",
        "    require(r.returncode == 0, 'worker Git status failed')\n"
        "    verified_hook().startup_status(r.stdout)")
    return raw,text.encode()


def prompt(before,probe):
    old=before['WORKER-BRIEF.md'].decode()
    phase_two=old[old.index('## Phase two:'):]
    negative=source_module(before['startup-validation.py'],'r4_validation').NEGATIVE_SCRIPT
    path=str(build.O/build.NEW/'worker-startup.py')
    return f'''# ga-e0t1.20 r5 — exact pre-claim operational contract

You are the one Gas City candidate worker using Astra high. Do not run the
generic gc prime instruction in Core's beacon. This task-specific startup
protocol replaces that generic instruction and the superseded r4 startup note.
AGENTS.md's environment-prefix examples are external-coordinator examples, not
the worker's command forms. Existing permission rules are unchanged. No bypass.

Use workdir {lc.WORK} for EVERY tool call, inherited GC_HOME and
GIT_OPTIONAL_LOCKS=0, and exactly one literal command per native tool call.
Do not prepend env, change flag order, use bare gc, chain commands, or request
escalation. An approved native control prefix is the existing reviewed route,
not permission to remove the sandbox from product tools. If denied, report the
exact refusal and wait for containment. Never repair Dolt or native permissions.

1. Claim exactly once with this literal command:
   `{' '.join(lc.CLAIM)}`
   Require task ga-e0t1.20 and its real session identity. No other task.
2. Read only this Bead with the plain-text command, not its parent's history:
   `{' '.join(lc.SHOW)}`
   The historical r4 brief/probe digests remain evidence and are superseded only
   by the exact r5 amendment on this same task. Scope and permissions are unchanged.
3. Verify the current probe with this separate literal command:
   `/usr/bin/sha256sum {path}`
   Require {sha(probe)}. Then run `/usr/bin/python3.12 -I -B {path} ACTUAL_SESSION_ID`
   replacing only ACTUAL_SESSION_ID by your real GC session ID. Run in the ordinary
   sandbox. Do not create a fake result or substitute coordinator evidence.
4. Core's pre-existing .codex/hooks.json is expected at exact SHA-256
   {lc.HOOK_IMAGE['sha256']}, mode 0644. Preserve it byte-for-byte.
   The probe validates it. No hook, trust, rule or configuration edit is permitted.
5. Attempt the native negative signing probe exactly once through this transport:

```javascript
{negative}
```

   Native policy must reject the tool before execution. A returned exit code is
   failure, even if nonzero. Do not fabricate an exception or try another spelling.
6. Hash .gc/worker-evidence/ga-e0t1.20/startup.json with /usr/bin/sha256sum.
   Append exactly one startup note, replacing REPORT_DIGEST by that digest:
   `{' '.join(lc.UPDATE)} 'STARTUP READY: ga-e0t1.20 report_sha256=REPORT_DIGEST'`
   Then WAIT. Do not drain or edit product source before the coordinator's exact
   same-session source release. It must read
   `SOURCE RELEASE: ga-e0t1.20 session=ACTUAL_SESSION_ID report_sha256=REPORT_DIGEST probe_sha256={sha(probe)}`.
   Reject old, different-session or differently bound releases.

On failure after claim, append one STOPPED note using the same literal update
prefix and wait. Before claim, report in this session and wait. No mail, restart,
reroute, extra task, native subagent, signing, staging, commit, push or task close.
If supported containment asks for drain acknowledgement, its existing exact form
is `{' '.join(lc.DRAIN)}`. Never drain merely because startup is waiting.

Base c6b789bbe6ff677dd04336803dbf2c2e017812ba and branch
codex/ga-e0t1.20-c1-close-admission must match. The probe enforces both.
Generated hooks are an observed runtime input, not proof of effective trust.
The coordinator verifies native policy, claim, actual process, sandbox and source
before one release. No additional capability is granted by this prompt.

{phase_two}'''.encode()


def components():
    before=frozen()
    helper,probe=prepare_worker(before)
    body=prompt(before,probe)
    suffix=skills_suffix().encode()
    out={'launch-contract-r5.py':helper,'worker-startup.py':probe,'PRECLAIM-R5.md':body,
         'skills-suffix-r5.txt':suffix}
    contract=before['contract.py'].decode()
    old=source_module(before['contract.py'],'old_contract')
    amendment=('R5 append-forward startup amendment for ga-e0t1.20. The initial prompt is '+PROMPT+
        ' sha256 '+sha(body)+'. The worker-startup.py digest is '+sha(probe)+
        '. These supersede only the r4 startup prompt and probe references. Preserve the existing route '
        'workspace base scope permissions and candidate-only restrictions. Exact Core-generated hooks '
        'sha256 '+lc.HOOK_IMAGE['sha256']+' are preserved. Source release remains mandatory.')
    note=old.BOUND_NOTE+'\n'+amendment
    contract=build.once(contract,'BOUND_NOTE = '+repr(old.BOUND_NOTE),'BOUND_NOTE = '+repr(note))
    contract=build.once(contract,'RUNTIME_FILES={',"RUNTIME_IMAGE['.codex/hooks.json']="+repr(lc.HOOK_IMAGE)+"\nRUNTIME_FILES={")
    contract=build.once(contract,"    expected = {b'!! ' + path.encode() for path in RULES}",
        "    expected = {b'!! ' + path.encode() for path in set(RULES) | (RUNTIME_FILES - {'.codex/hooks.json'})}\n"
        "    expected.add(b'?? .codex/hooks.json')")
    contract=build.once(contract,"elif code == b'!!' and path in RUNTIME_FILES:",
        "elif (code == b'!!' and path in RUNTIME_FILES) or (code == b'??' and path == '.codex/hooks.json'):")
    out['contract.py']=contract.encode()
    out['startup-amendment-r5.json']=(json.dumps(dict(schema='ga-e0t1.20.startup-amendment.v1',
        before_note=old.BOUND_NOTE,append_note=amendment,after_note=note,
        worker_probe_sha256=sha(probe),prompt_sha256=sha(body),source_release_required=True,
        completed_bind_and_route_must_not_replay=True),indent=2,sort_keys=True)+'\n').encode()
    text=(build.HERE/'prompt-prep-r5.py').read_text()
    text=build.once(text,'R5_PROMPT_SHA',sha(body))
    text=build.once(text,'R5_HELPER_SHA',sha(helper))
    out['prompt-prep-r5.py']=text.encode()
    wrapper=build.git('show','1d57ec7c787667dcd891ffb41172aa867e7a52d9:'+
        build.D+'ga-e0t1.20-astra-bootstrap/operator/PREP.sh').decode()
    wrapper=wrapper.replace('ga-e0t1.20-astra-bootstrap','ga-e0t1-20-astra-window')
    wrapper=wrapper.replace('S1 PREP:','R5 PROMPT PREP:')
    wrapper=wrapper.replace('PREP.sh','PROMPT-PREP-R5.sh').replace('/prepare.py','/prompt-prep-r5.py')
    wrapper=wrapper.replace('ga-e0t1.20-prep-20260927-r1','ga-e0t1.20-prompt-prep-20260928-r5')
    wrapper=wrapper.replace('prep-$(date','prompt-prep-r5-$(date')
    wrapper=build.once(wrapper,'40858f94e795425c38f1e5ae8b973aa60e5c3aa67043bc84b6be36389b4ea6c3',sha(out['prompt-prep-r5.py']))
    out['operator/PROMPT-PREP-R5.sh']=wrapper.encode()
    # Whole startup contract: update every consumer, not just the worker probe.
    text=before['startup-release.py'].decode()
    text=build.once(text,"    require(not os.path.lexists(Path(v.WORK)/'.codex/hooks.json'),'unexpected project hook')",
        "    probe.verified_hook()  # exact generated bytes and authority, not a trust grant")
    text=build.once(text,'    args=validator.process_arguments(argv)',
        "    args=validator.process_arguments(argv)\n"
        "    helper=load(HERE/'launch-contract-r5.py','"+sha(helper)+"',read)\n"
        "    body=read(HERE/'PRECLAIM-R5.md').decode('utf-8','strict')\n"
        "    require(hashlib.sha256(body.encode()).hexdigest()=='"+sha(body)+"','launch prompt file drift')\n"
        "    require(helper.prompt_body(argv[-1],body)=='"+sha(suffix)+"','assigned skills suffix differs')")
    loader="""def load(path, pin, read):
    raw=read(path)
    require(hashlib.sha256(raw).hexdigest()==pin,'startup helper binding')
    value=types.ModuleType(path.stem);value.__file__=str(path)
    exec(compile(raw,str(path),'exec',dont_inherit=True),value.__dict__)
    return value


"""
    text=build.once(text,'def process_table():\n',loader+'def process_table():\n')
    out['startup-release.py']=text.encode()
    text=before['candidate-inspect.py'].decode()
    text=build.once(text,"    whole=validator.workspace_image(w.WORK,file_bytes)",
        "    whole=validator.workspace_image(w.WORK,file_bytes)\n"
        "    require(whole.get('.codex/hooks.json')==w.contract().RUNTIME_IMAGE['.codex/hooks.json'],\n"
        "            'candidate generated hook differs')")
    out['candidate-inspect.py']=text.encode()
    # These are component drafts. Native prepare and a complete, independently
    # reviewed successor must bind the live base before any worker execution.
    out['window-base-r11.py']=before['window-base-r11.py']
    # Rebind standalone digest literals only. Do NOT rewrite old hashes inside
    # the preserved original Bead note or the new amendment text.
    for _ in range(40):
        pins={sha(raw):sha(out[name]) for name,raw in before.items()
              if name in out and raw!=out[name]}
        changed={}
        for name,raw in out.items():
            if name.endswith('.py') and name not in ('window-base-r11.py',):
                for old,new in pins.items():
                    raw=raw.replace(("'"+old+"'").encode(),("'"+new+"'").encode())
            changed[name]=raw
        if out==changed:break
        out=changed
    else:raise RuntimeError('component digest bindings did not settle')
    for name,raw in out.items():
        if name.endswith('.py'):ast.parse(raw,filename=name)
    return before,out


def main(output):
    root=Path(output);assert not root.exists(),'create-only r5 component draft'
    before,out=components();root.mkdir(mode=0o700)
    for name,raw in out.items():
        (root/name).parent.mkdir(parents=True,exist_ok=True)
        with (root/name).open('xb') as f:f.write(raw)
    manifest=dict(schema='ga-e0t1.20.startup-r5-component-draft.v1',predecessor=R4,
        recovery=R4_RECOVERY,files={name:sha(raw) for name,raw in out.items()},
        execution_admitted=False,worker_launch_included=False,
        remaining=['native prompt PREP','complete successor binding','independent review','live startup'])
    with (root/'components.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__':main(*sys.argv[1:])
