"""In-memory assembly of one fresh ga-mb91 worker window.

Inputs are the exact successful R11 runtime, completed WORKTREE/PREP, and
the fresh-task contracts beside this file. Historical retry machinery is not
selected. No CLI, file writer, job submission or execution admission is provided.
Final host observation and cache disposition must be supplied explicitly and
the complete output must be signed and independently reviewed before execution.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import types

HERE = Path(__file__).parent
OLD = HERE.parent / 'ga-e0t1-20-astra-window'
MANIFEST_SHA = '25faae1f8b21f1ffbb2db3388450e1217c46a54d92a192d5ae3c2d1b8b96a8e3'
PREP = Path('/var/tmp/ga-mb91-prep-20260930-r1')
PREP_SHA = '74e69f6f1f43098f236cb89d0b35709fd15b6b05ea76460249769d1d428310d7'
OLD_NAMES = (
    'audit-queue-r3.py', 'bind-task-r5.py', 'route-task-r5.py',
    'budget-r11.py', 'cache-atime-policy-r1.py', 'candidate-inspect.py',
    'close-r11.py', 'common-snapshot-r1.py', 'hold-r11.py',
    'observe-integrity-r11.py', 'observe-terminal-r11.py',
    'read-time-accounting.py', 'release-delivery-r11.py', 'release-runtime-r11.py',
    'restore-admission-r3.py', 'restore-r9-routes-r3.py', 'route-chain-r1.py',
    'runtime-process-r7.py', 'skills-suffix-r5.txt', 'stranded-recovery.py',
    'suspension-lineage.py', 'watch-r11.py', 'window-base-r11.py',
    'window-obs-r11.py', 'window-r11.py',
)
WRAPPERS = ('BIND', 'OBSERVE', 'PREFLIGHT', 'STAGE', 'ROUTE', 'RESUME',
            'RELEASE', 'CONTAIN-1', 'CONTAIN-2', 'HOLD-1', 'HOLD-2',
            'CLOSE-1', 'CLOSE-2', 'ADMIT', 'RESTORE', 'TERMINAL', 'INSPECT',
            *('WATCH-'+str(i) for i in range(1, 13)))
RENAMES = {
    'release-runtime-r11.py': 'release-runtime-r13.py',
    'release-delivery-r11.py': 'release-delivery-r13.py',
    'bind-task-r5.py': 'bind-task.py', 'route-task-r5.py': 'route-task.py',
    'window-base-r11.py': 'window-base.py', 'window-r11.py': 'window.py',
    'continuation-admission.py': 'fresh-admission.py', 'workspace-r11.py': 'fresh-workspace.py',
    'permissions-baseline-r11.py': 'permissions-baseline.py',
    'launch-contract-r5.py': 'launch-contract.py', 'worker-startup-r11.py': 'worker-startup.py',
    'PRECLAIM-R11.md': 'PRECLAIM.md',
}
LOCAL = ('contract.py', 'startup-validation.py', 'worker-startup.py', 'PRECLAIM.md',
         'WORKER-BRIEF.md', 'permissions-baseline.py', 'launch-contract.py',
         'fresh-admission.py', 'fresh-workspace.py', 'FILE-SCOPE.json', 'create-only-patch.py',
         'release-runtime-r13.py', 'release-delivery-r13.py',
         'queue-preservation.py', 'queue-guard.py')
HEX = re.compile(r"(?P<quote>['\"])(?P<digest>[0-9a-f]{64})(?P=quote)|(?P<assignment>^[A-Z_]+_SHA=)(?P<shell>[0-9a-f]{64})$", re.M)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(raw, name):
    m = types.ModuleType(name)
    m.__file__ = str(HERE / name)
    exec(compile(raw, m.__file__, 'exec', dont_inherit=True), m.__dict__)
    return m


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('missing or ambiguous anchor: ' + before[:100])
    return text.replace(before, after)


def read_inputs():
    raw = (OLD / 'assembly.json').read_bytes()
    if sha(raw) != MANIFEST_SHA:
        raise ValueError('successful R11 manifest drift')
    manifest = json.loads(raw)
    names = (*OLD_NAMES, *('operator/'+name+'.sh' for name in WRAPPERS))
    sources = {name: (OLD / name).read_bytes() for name in names}
    if any(sha(raw) != manifest['files'][name] for name, raw in sources.items()):
        raise ValueError('successful R11 source drift')
    # These are replaced, not copied. Their old digests bind source references
    # in the selected R11 modules to the new exact local components.
    references = {name: manifest['files'][name] for name in
        ('contract.py', 'startup-validation.py', 'permissions-baseline-r11.py',
         'launch-contract-r5.py', 'worker-startup-r11.py', 'PRECLAIM-R11.md',
         'continuation-admission.py', 'workspace-r11.py')}
    local = {name: (HERE / name).read_bytes() for name in LOCAL}
    prep_raw = (PREP / 'result.json').read_bytes()
    if sha(prep_raw) != PREP_SHA:
        raise ValueError('completed PREP receipt drift')
    prep = json.loads(prep_raw)
    if not (prep['ok'] is True and prep['installed'] is False
            and prep['worker_launched'] is False and prep['preparation_only'] is True
            and prep['execution_authorized_by_this_result'] is False
            and prep['task'] == 'ga-mb91' and prep['workspace_capacity'] == 1
            and prep['nudge_queue_scope'] == 'session-epoch'):
        raise ValueError('PREP is not the expected uninstalled single-task preparation')
    for name, key in (
        ('city.baseline.toml', 'city_before_sha256'), ('city.isolated.toml', 'city_after_sha256'),
        ('receipt.before.json', 'receipt_before_sha256'), ('receipt.final.json', 'receipt_after_sha256'),
    ):
        if sha((PREP / name).read_bytes()) != prep[key]:
            raise ValueError('completed PREP artifact drift: ' + name)
    for name,key in (('PRECLAIM.md','prompt_sha256'),('WORKER-BRIEF.md','worker_brief_sha256'),
                     ('worker-startup.py','worker_probe_sha256'),('FILE-SCOPE.json','file_scope_sha256')):
        if sha(local[name])!=prep[key]:
            raise ValueError('prepared worker input drift: '+name)
    return sources, references, local, prep


def retarget(text):
    text = text.replace('ga-e0t1-20-astra-window', 'ga-mb91-c1-package')
    text = text.replace('codex/ga-e0t1.20-c1-close-admission', 'codex/ga-mb91-c1-package')
    text = text.replace('c6b789bbe6ff677dd04336803dbf2c2e017812ba',
                        '801a5a9d5b0d72f665c949a86573357f02c9f1ac')
    text = text.replace('ga-e0t1.20', 'ga-mb91')
    # Also bind Path(VAR) / relative names, not only absolute path literals.
    text = re.sub(r'(ga-mb91-[a-z%0-9.-]+)-202609[0-9]{2}-r[0-9]+',
                  r'\1-20260930-r1', text)
    # R1/R2 OBSERVE were consumed without live mutation. Only the successor uses r3;
    # WORKTREE, PREP and the completed BIND retain their original receipts.
    text = text.replace('ga-mb91-integrity-20260930-r1',
                        'ga-mb91-integrity-20260930-r3')
    text = text.replace('ga-mb91-r11-', 'ga-mb91-r1-')
    text = text.replace('.gc/worker-evidence/ga-mb91/r11', '.gc/worker-evidence/ga-mb91/r1')
    # The completed PREP probe and fresh BIND both bind September 30.
    for before, after in RENAMES.items():
        text = text.replace(before, after)
    return text


def base_source(raw, prep, *, observation, observation_sha, cache_ns):
    text = retarget(raw.decode())
    # Prior success is historical evidence only, never authority to replay.
    start = text.index('    previous=json.loads(', text.index('def pins():'))
    stop = text.index('    # The R9-era diagnostic pins', start)
    text = text[:start] + """    previous=json.loads(read(Path('/var/tmp/ga-jcxb-terminal-20260930-r1/result.json'),
        'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'))
    require(previous['ok'] is True and previous['accepted_restoration_bound'] is True
        and previous['actual_host_verified'] is True and previous['worker_launched'] is False
        and previous['root_cache_protected_read_only'] is True
        and previous['terminal_suspension_endpoint_bound'] is True,
        'previous window was not proven restored')
    closed=json.loads(read(Path('/var/tmp/ga-jcxb-r1-close-20260930T041304Z/result.json'),
        '8f65d7d473dacdddbb6a6654f74c6d749346375bf47b3989f335ca229e3d656c'))
    require(closed['ok'] is True and closed['closed_session']=='ci-mzoxg'
        and closed['open_sessions']==0 and closed['city_tmux_sessions']==0
        and closed['worktree_processes']==0, 'prior close lacks zero residue')
""" + text[stop:]
    text = once(text, "PREP = Path('/var/tmp/ga-mb91-prompt-prep-20260930-r1')",
                'PREP = Path('+repr(str(PREP))+')')
    old = load(raw, 'previous_window_base')
    for before, after in (
        (old.CITY_SHA[1], prep['city_after_sha256']),
        (old.RECEIPT_SHA[1], prep['receipt_after_sha256']),
        (old.REVISION[1], prep['revision_after']),
        (str(old.ACCEPTED), observation), (old.ACCEPTED_SHA, observation_sha),
        ('c1869bb42078ed77d2506a428d7ae038cac19e9a11dca95b5593e2f1a2632391', PREP_SHA),
    ):
        text = once(text, repr(before), repr(after))
    text = once(text, 'CACHE_PREV_NS = '+str(old.CACHE_PREV_NS), 'CACHE_PREV_NS = '+str(cache_ns))
    text = once(text, 'CACHE_PINNED_NS = '+str(old.CACHE_PINNED_NS), 'CACHE_PINNED_NS = '+str(cache_ns))
    text = once(text, '        probe.verified_hook()\n',
        '        # Fresh workspace has no Core hook yet. The worker probe and\n'
        '        # independent source-release check verify it after materialization.\n')
    text = once(text, "        save('workspace-before.json',workspace_before)",
        "        save('workspace-before.json',workspace_before)\n"
        "        claim_branch=phase('claim-store-branch',['/usr/bin/git','--no-optional-locks','-C',\n"
        "            '/home/loucmane/gascity/city/rigs/gascity','symbolic-ref','--short','HEAD'],b,owned)\n"
        "        require(claim_branch['stdout'].strip()==validator.CLAIM_BRANCH,'claim store branch drift')")
    return text.encode()


def queue_source(raw, contract_sha):
    text = retarget(raw.decode())
    text = once(text, "assert MODE in ('route', 'resume'), 'audit mode'",
                "assert MODE in ('stage', 'route', 'resume'), 'audit mode'")
    text = once(text, "(['ga-mb91'] if store=='gascity' else [])",
                "(['ga-mb91'] if store=='gascity' and MODE!='stage' else [])")
    text = once(text, "assert routed and not a and v['status']=='open', 'expected open task drift'",
        "assert routed==(MODE!='stage') and not a and v['status']=='open', 'expected open task drift'\n"
        "                if MODE=='stage':assert not m.get('gc.routed_to') and not legacy,'premature route'")
    text = once(text, "(MODE == 'route' or r['name'] != 'gascity')",
                "(MODE != 'resume' or r['name'] != 'gascity')")
    text = once(text, "result = dict(ok=True, mode=MODE,",
        "CONTRACT=Path("+repr(str(HERE/'contract.py'))+")\n"
        "contract_raw=CONTRACT.read_bytes()\n"
        "assert hashlib.sha256(contract_raw).hexdigest()=="+repr(contract_sha)+",'task contract digest'\n"
        "contract=types.ModuleType('fresh_queue_contract');contract.__file__=str(CONTRACT)\n"
        "exec(compile(contract_raw,str(CONTRACT),'exec',dont_inherit=True),contract.__dict__)\n"
        "shown=run('exact-task',['--rig','gascity','bd','show','ga-mb91','--json'])\n"
        "assert isinstance(shown,list) and len(shown)==1,'exact task readback'\n"
        "contract.validate_task(shown[0],'bound' if MODE=='stage' else 'routed')\n"
        "native_ready_member=None\n"
        "if MODE=='stage':\n"
        "    ready=run('fresh-native-ready',['--rig','gascity','bd','ready','--json','--limit','0'])\n"
        "    assert isinstance(ready,list) and all(isinstance(row,dict) for row in ready),'native ready shape'\n"
        "    assert sum(row.get('id')=='ga-mb91' for row in ready)==1,'fresh task not uniquely native ready'\n"
        "    native_ready_member=True\n"
        "result = dict(ok=True, mode=MODE, native_ready_member=native_ready_member,")
    text = once(text, "sole_eligible_target_task='ga-mb91',",
                "sole_eligible_target_task=None if MODE=='stage' else 'ga-mb91',")
    return text.encode()


def rebind(out, initial, references, immutable):
    history = {RENAMES.get(n, n): {sha(raw)} for n, raw in initial.items()}
    for name, digest in references.items():
        history.setdefault(RENAMES.get(name, name), set()).add(digest)
    for _ in range(40):
        for name, raw in out.items():
            history.setdefault(name, set()).add(sha(raw))
        mapping = {old: sha(out[name]) for name, values in history.items()
                   for old in values if name in out and old != sha(out[name])}
        newer = {}
        for name, raw in out.items():
            if name.endswith(('.py', '.sh')) and name not in immutable:
                def bind(match):
                    if match['quote']:
                        return match['quote']+mapping.get(match['digest'], match['digest'])+match['quote']
                    return match['assignment']+mapping.get(match['shell'], match['shell'])
                raw = HEX.sub(bind, raw.decode()).encode()
            newer[name] = raw
        if newer == out:
            return out
        out = newer
    raise ValueError('source binding graph did not settle')


def bind_inspector(sources):
    """Bind both readers and their consumer to one exact offline-built M15 adapter."""
    build = Path('/var/tmp/ga-mb91-platform-inspector-m15-20260930-r1')
    result_raw = (build/'build-result.json').read_bytes()
    if sha(result_raw) != 'eb6ceaa800c4c5b07d6deef1e7246edff119882f5cc96aa6b397675382b13e51':
        raise ValueError('M15 inspector build receipt drift')
    result = json.loads(result_raw)
    if (result['manifest_sha256'] != 'd02a3adbd044ebaf4f1dd4606c0af5dea50bcab4bca5efb2f3da5aab14e68481'
            or result['core_commit'] != '53f2e232da03a1e176cf64cf4fe1aa9c3f3beb6b'
            or result['core_tree'] != '2a253aabadc432c3c9f8953961b7a0db96291191'
            or sha((build/'platform-inspect').read_bytes()) != result['binary_sha256']
            or sha((HERE/'inspector-m15/platform-inspect-main.go').read_bytes()) != result['entrypoint_sha256']
            or sha((HERE/'inspector-m15/inspector-build.py').read_bytes()) != result['builder_sha256']):
        raise ValueError('M15 inspector source or binary drift')
    out = dict(sources)
    for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
        text = out[name].decode()
        for before, after in (
            ('/var/tmp/gct-oak5-platform-inspector-m12-20260927', str(build)),
            ('0da1ff146cb3e1e1ba7329d669f2135bbc7d26c6c0f35999e6dad1bef88d08c6', result['binary_sha256']),
            ('2ec7df2d33d0fddc9b9204c51cf65879a683f628dfd2cf2109c04c030416aed0', sha(result_raw)),
            ('f45a626213dc5b8d0b52f097d978cca56e506df0', result['core_commit']),
            ('f1011adaf673937fbda1d254a53c8f0eadf17c5c', result['core_tree']),
            ('367056c801f85a4409589d231a0e91243f7ed1d9c6ded9a2e658865c8e3b0ad4', result['entrypoint_sha256']),
            (",\n        'build binding')", "\n        and result['manifest_sha256']==MANIFEST_SHA,\n        'build binding')"),
        ):
            text = once(text, before, after)
        out[name] = text.encode()
    out['window.py'] = once(out['window.py'].decode(),
        '0da1ff146cb3e1e1ba7329d669f2135bbc7d26c6c0f35999e6dad1bef88d08c6',
        result['binary_sha256']).encode()
    return out


def assemble(*, observation, observation_sha, cache_ns):
    if re.fullmatch(r'/tmp/ga-mb91-readonly-baseline-20260930-r[1-9][0-9]*/observed.json',
                    observation) is None:
        raise ValueError('fresh task observation path required')
    if re.fullmatch(r'[0-9a-f]{64}', observation_sha) is None:
        raise ValueError('observation SHA256 required')
    if type(cache_ns) is not int or cache_ns <= 0:
        raise ValueError('exact cache timestamp required')
    before, references, local, prep = read_inputs()
    c = load(local['contract.py'], 'fresh_window_contract')
    tasks = load((HERE/'task-assembly.py').read_bytes(), 'fresh_task_assembly')
    out = {RENAMES.get(n, n): retarget(raw.decode()).encode() for n, raw in before.items()}
    out.update(local)
    out['window-base.py'] = base_source(before['window-base-r11.py'], prep,
        observation=observation, observation_sha=observation_sha, cache_ns=cache_ns)
    out['bind-task.py'] = (HERE/'bind-task.py').read_bytes()
    if sha(out['bind-task.py']) != '028ccef1db747088c7f8552c86094ded85b5db12f1d58d890bd7678fa432adea':
        raise ValueError('completed BIND executor drift')
    out['route-task.py'] = tasks.routing(before['route-task-r5.py'],
        window_sha=sha(before['window-r11.py']), binding_sha=sha(before['bind-task-r5.py']),
        admission_sha=sha(local['fresh-admission.py']), contract=c)
    out['audit-queue-r3.py'] = queue_source(before['audit-queue-r3.py'], sha(local['contract.py']))
    # Release and containment bind the actual post-route task, not the fresh
    # preflight bound snapshot. This is still the same task, not a retry.
    for name in ('startup-release.py',):
        source = (OLD/name).read_bytes()
        manifest = json.loads((OLD/'assembly.json').read_bytes())
        if sha(source) != manifest['files'][name]:
            raise ValueError('source release predecessor drift')
        before[name] = source
        text = retarget(source.decode())
        text = once(text, "WINDOW/'admitted-task.json'", "ROUTE/'task-after.json'")
        out[name] = text.encode()
    text = out['close-r11.py'].decode()
    text = once(text, "WINDOW/'admitted-task.json'",
                "Path('/var/tmp/ga-mb91-route-20260930-r1/task-after.json')")
    out['close-r11.py'] = text.encode()
    # Only fresh roots regain their BIND/ROUTE wrappers. Historical wrappers
    # and all WORKTREE/PREP operations are excluded rather than re-enabled.
    for name in ('ROUTE',):
        key = 'operator/'+name+'.sh'
        out[key] = once(out[key].decode(),
            'echo "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n', '').encode()
    out['operator/STAGE.sh'] = once(out['operator/STAGE.sh'].decode(),
        'step audit-route "$C/audit-queue-r3.py" "$AUDIT_SHA" route',
        'step audit-stage "$C/audit-queue-r3.py" "$AUDIT_SHA" stage').encode()
    # Post-terminal inspection remains read-only. New files are untracked, so
    # an ordinary git diff would omit them. Encode only the exact inspected
    # new text files, without staging or running any worker-controlled code.
    inspector = out['candidate-inspect.py'].decode()
    old = "    patch = git(admin, w.WORK, 'diff', '--no-ext-diff', '--no-textconv', '--binary', '--', *accepted['source'])"
    new = ("    encoder=w.module(HERE/'create-only-patch.py', "+repr(sha(local['create-only-patch.py']))+")\n"
           "    payload={rel:file_bytes(w.WORK/rel, w.contract().MAX_PRODUCT_BYTES) for rel in accepted['source']}\n"
           "    require(all(w.digest(raw)==sources[rel]['sha256'] for rel,raw in payload.items()), 'new file read drift')\n"
           "    patch=encoder.encode(payload,w.contract().SOURCE_MODES,w.contract().MAX_PRODUCT_BYTES)")
    out['candidate-inspect.py'] = once(inspector,old,new).encode()
    wiring=load((HERE/'queue-wiring.py').read_bytes(),'queue_wiring')
    out=wiring.apply(out,prep)
    out=bind_inspector(out)
    out = rebind(out, before, references, set(LOCAL) | {'bind-task.py'})
    for name, raw in out.items():
        if name.endswith('.py'):
            ast.parse(raw, filename=name)
    # Existing prepared worker inputs must not drift in the window assembly.
    for name in LOCAL:
        if out[name] != local[name]:
            raise ValueError('prepared local component changed: '+name)
    return before, out
