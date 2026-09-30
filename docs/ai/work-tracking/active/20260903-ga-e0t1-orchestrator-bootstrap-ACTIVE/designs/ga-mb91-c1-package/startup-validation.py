"""Closed, fixture-testable rules for the one Astra startup release.

This file does not grant authority, invoke a provider or issue commands.
The release job supplies real host observations and native rollout bytes.
"""
import errno
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91'
BASE = '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
TASK = 'ga-mb91'
BRANCH = 'codex/ga-mb91-c1-package'
CODEX = '/home/loucmane/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex'
EVIDENCE = '.gc/worker-evidence/ga-mb91/r1'
NEGATIVE_SCRIPT = ('try { text({probe_return: await tools.exec_command({"cmd":"gpg --version",'
    '"workdir":"'+WORK+'","sandbox_permissions":"use_default","max_output_tokens":1000})}); } '
    'catch (error) { text({probe_error: String(error)}); }')
NEGATIVE_SCRIPTS = tuple(s+suffix for s in (NEGATIVE_SCRIPT,
    NEGATIVE_SCRIPT.replace('"sandbox_permissions":"use_default",',''))
    for suffix in ('','\n'))
NATIVE_ERROR = 'exec_command failed: CreateProcess { message: "Rejected(\\"`/usr/bin/zsh -lc \'gpg --version\'` rejected: Unsigned candidate workers must not invoke GPG directly; return the candidate for approved managed delivery.\\")" }'
NATIVE_POSTURE = {'workspace_roots': ['/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91'], 'sandbox_policy': {'type': 'workspace-write', 'network_access': False, 'exclude_tmpdir_env_var': False, 'exclude_slash_tmp': False}, 'permission_profile': {'type': 'managed', 'file_system': {'type': 'restricted', 'entries': [{'path': {'type': 'special', 'value': {'kind': 'root'}}, 'access': 'read'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91'}, 'access': 'write'}, {'path': {'type': 'special', 'value': {'kind': 'slash_tmp'}}, 'access': 'write'}, {'path': {'type': 'special', 'value': {'kind': 'tmpdir'}}, 'access': 'write'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91'}, 'access': 'write'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.git'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.agents'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.codex'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops/.git/worktrees/ga-mb91'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.git'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.agents'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.codex'}, 'access': 'read', 'missing_path_behavior': 'skip'}]}, 'network': 'restricted'}, 'file_system_sandbox_policy': {'kind': 'restricted', 'entries': [{'path': {'type': 'special', 'value': {'kind': 'root'}}, 'access': 'read'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91'}, 'access': 'write'}, {'path': {'type': 'special', 'value': {'kind': 'slash_tmp'}}, 'access': 'write'}, {'path': {'type': 'special', 'value': {'kind': 'tmpdir'}}, 'access': 'write'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91'}, 'access': 'write'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.git'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.agents'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.codex'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops/.git/worktrees/ga-mb91'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.git'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.agents'}, 'access': 'read', 'missing_path_behavior': 'skip'}, {'path': {'type': 'path', 'path': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91/.codex'}, 'access': 'read', 'missing_path_behavior': 'skip'}]}}
# Runtime input pinning is performed by the bound contract/probe. No duplicated
# permission-file digest is accepted as an independent authority here.


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def same_process(before, after):
    # R and S are scheduler substates, not new process identities. Still reject
    # disappearance, reparenting, PID reuse and zombie/dead processes.
    return (isinstance(after, dict) and after.get('state') not in ('Z','X')
            and all(before.get(key) == after.get(key) for key in ('ppid','start')))


def process_arguments(argv):
    require(argv and argv[0] in (CODEX, '/home/loucmane/gascity/bin/codex', 'codex'), 'worker executable argv')
    flags, config, prompt = {}, {}, []
    pos = 1
    while pos < len(argv):
        value = argv[pos]
        if value in ('--model', '--ask-for-approval', '--sandbox', '-c'):
            require(pos+1 < len(argv), 'truncated worker flag')
            argument = argv[pos+1]
            if value == '-c':
                key, sep, item = argument.partition('=')
                require(sep and key not in config, 'duplicate or malformed worker config')
                config[key] = item
            else:
                require(value not in flags, 'duplicate worker flag')
                flags[value] = argument
            pos += 2
        else:
            require(not value.startswith('-') and pos == len(argv)-1 and value != 'resume',
                    'unexpected worker argument or restart')
            prompt.append(value)
            pos += 1
    require(flags == {'--model':'gpt-6-astra','--ask-for-approval':'never','--sandbox':'workspace-write'},
            'worker flags differ')
    require(config == {'model_reasoning_effort':'high',
        'sandbox_workspace_write.writable_roots':json.dumps([WORK], separators=(',',':')),
        'mcp_servers.serena.enabled':'false','mcp_servers.aegis.enabled':'false'}, 'worker config differs')
    require(len(prompt) == 1 and prompt[0], 'missing bound worker prompt')
    return dict(flags=flags, config=config, prompt_sha256=hashlib.sha256(prompt[0].encode()).hexdigest())


def native_time(value):
    # Native UTC RFC3339/RFC3339Nano only. Keep nanoseconds for ordering;
    # datetime alone would silently truncate the last three digits.
    require(isinstance(value,str), 'native timestamp type')
    match=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z',value)
    require(match is not None, 'native timestamp format')
    try:whole=datetime.strptime(match[1],'%Y-%m-%dT%H:%M:%S')
    except ValueError as exc:raise RuntimeError('native timestamp calendar') from exc
    return whole,int((match[2] or '').ljust(9,'0'))


def claim_time(task, routed, session):
    # A new task has no prior claim, timestamp or retry exception.
    require('started_at' not in routed, 'routed task already has a start time')
    started = native_time(task.get('started_at'))
    created = native_time(routed.get('created_at'))
    routed_at = native_time(routed.get('updated_at'))
    session_at = native_time(session.get('created_at'))
    updated = native_time(task.get('updated_at'))
    require(created <= routed_at <= started <= updated and session_at <= started,
            'native claim timestamp order')


# The pinned Core claim resolves a branch in the selected rig store, not the
# external worker cwd. This is bookkeeping only; probe, argv, native cwd and
# workspace images independently prove the actual candidate branch and base.
CLAIM_BRANCH = 'agent/upstream-pending-create-lease'


def claim_metadata(routed, session, actual):
    require(isinstance(actual, dict), 'claim metadata shape')
    expected = dict(routed['metadata'], **{
        'gc.session_id': session['id'], 'gc.session_name': session['session_name']})
    if 'gc.work_branch' in actual:
        expected['gc.work_branch'] = CLAIM_BRANCH
    require(actual == expected, 'claim metadata differs')
    return expected


def live_task(task, routed, session, contract, startup_digest):
    require(task.get('id') == TASK and task.get('status') == 'in_progress', 'task not in progress')
    require(task.get('assignee') == session['session_name'], 'native claim owner differs')
    claim_metadata(routed, session, task.get('metadata'))
    note = 'STARTUP READY: ' + TASK + ' report_sha256=' + startup_digest
    require(task.get('notes') == routed['notes'] + '\n' + note, 'startup note is not exact or single')
    claim_time(task, routed, session)
    for key in set(task) | set(routed):
        if key not in ('status', 'assignee', 'metadata', 'notes', 'updated_at', 'started_at'):
            require(task.get(key) == routed.get(key), 'task changed outside claim and startup note: ' + key)
    contract.validate_task(routed, 'routed')
    return note


def session_row(census):
    require(census.get('ok') is True and isinstance(census.get('sessions'),list)
            and len(census['sessions']) == 1, 'expected exactly one native session')
    [s] = census['sessions']
    require(s.get('template') == 'gascity/codex' and s.get('rig') == 'gascity'
            and s.get('provider') == 'codex-managed' and s.get('work_dir') == WORK
            and not s.get('closed'), 'session capability or workspace differs')
    for key in ('id','session_name'):
        require(isinstance(s.get(key),str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{1,127}',s[key]),
                'malformed native session identity')
    return s


def transcript_key(path, session):
    match=re.fullmatch(r'rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl',Path(path).name)
    require(match is not None,'native transcript filename')
    key=match[1]
    require(session.get('session_key') in (None,'',key),'Core provider session key disagrees')
    return key


def report(value, session, probe):
    expected = dict(schema='ga-mb91.worker-startup.v1', task=TASK, session_id=session['id'],
        worktree=WORK, base=BASE, branch=BRANCH, subscription='ChatGPT', provider_overrides_absent=True,
        credential_values_exported=False, codex_sha256=probe.CODEX_SHA, local_rules=probe.RULES,
        default_rules_sha256=probe.DEFAULT_SHA, workspace_write=True, source_edit_released=False,
        predecessor_read=dict(commit=probe.PREDECESSOR, blobs=probe.PREDECESSOR_INPUTS, read_only=True))
    foreign = value.get('foreign_write')
    require(isinstance(foreign,dict) and set(foreign) == {'denied','errno','path'}
        and foreign['denied'] is True and type(foreign['errno']) is int
        and foreign['errno'] in (errno.EACCES,errno.EPERM,errno.EROFS)
        and foreign['path'] == str(probe.FOREIGN/'unexpected-write'), 'sandbox negative not proven')
    require(value == dict(expected,foreign_write=foreign), 'startup report contract differs')


def turn(value):
    require(value.get('cwd') == WORK and value.get('approval_policy') == 'never'
        and value.get('model') == 'gpt-6-astra' and value.get('effort') == 'high', 'native turn posture')
    policy = value.get('sandbox_policy')
    explicit = dict(type='workspace-write',writable_roots=[WORK],network_access=False)
    if policy == explicit:
        # Retain the old closed synthetic/native form. If the newer fields are
        # present they must agree too, rather than silently accepting a conflict.
        for key, expected in NATIVE_POSTURE.items():
            if key != 'sandbox_policy' and key in value:
                require(value[key] == expected, 'native permission detail drift')
    else:
        # 0.153.4 serializes the cwd write root implicitly, while retaining the
        # complete restricted permission profile. Require every observed field.
        require(all(value.get(key) == expected for key, expected in NATIVE_POSTURE.items()),
                'native sandbox posture')


def denial_from_rollout(raw, provider_id):
    """Use a literal request/result pair from the actual CLI-owned transcript.

    Worker text, an execpolicy query, an echo of an error, a failed shell command
    and a different call's refusal are not evidence. Unknown formats refuse.
    """
    require(len(raw) <= 32 << 20 and raw.endswith(b'\n'), 'native rollout bound or partial line')
    records = [json.loads(line) for line in raw.splitlines()]
    require(records and records[0].get('type') == 'session_meta', 'missing native session metadata')
    meta = records[0]['payload']
    require(meta.get('id') == provider_id and meta.get('cwd') == WORK
            and meta.get('cli_version') == '0.153.4', 'rollout identity differs')
    calls, matches, context, turns = {}, [], None, 0
    for record in records:
        if record.get('type') == 'turn_context':
            context = record['payload'];turn(context);turns += 1
        if record.get('type') != 'response_item':continue
        p = record.get('payload',{})
        if p.get('type') in ('function_call','custom_tool_call'):
            call = p.get('call_id')
            require(isinstance(call,str) and call not in calls, 'duplicate native call')
            calls[call] = p
        elif p.get('type') in ('function_call_output','custom_tool_call_output') and p.get('call_id') in calls:
            original = calls[p['call_id']]
            if original.get('type') == 'custom_tool_call':
                if original.get('name') != 'exec' or original.get('input') not in NEGATIVE_SCRIPTS:continue
                require(p.get('type') == 'custom_tool_call_output' and context is not None,
                        'native code-mode response context')
                blocks=p.get('output')
                require(isinstance(blocks,list) and len(blocks)==2
                        and all(isinstance(b,dict) and set(b)=={'type','text'}
                                and b['type']=='input_text' and isinstance(b['text'],str) for b in blocks),
                        'native code-mode response shape')
                require(re.fullmatch(r'Script completed\nWall time [0-9.]+ seconds\nOutput:\n',blocks[0]['text']),
                        'native code-mode execution did not complete')
                require(len(blocks[1]['text'])<=4096,'native code-mode error bound')
                result=json.loads(blocks[1]['text'])
                require(isinstance(result,dict) and set(result)=={'probe_error'}
                        and isinstance(result['probe_error'],str),'negative command returned rather than rejected')
                output=result['probe_error']
                if output.startswith('Error: '):output=output[7:]
                require(output == NATIVE_ERROR or (
                        output.startswith('exec command rejected:')
                        and ('blocked by policy' in output or 'forbidden by policy' in output)),
                        'not a native code-mode policy refusal')
                matches.append(dict(call_id=p['call_id'],request=original,output=p,turn_context=context))
                continue
            require(p.get('type')=='function_call_output','mismatched native response type')
            if original.get('name','').split('.')[-1] not in ('exec_command','shell_command'):continue
            args = json.loads(original['arguments'])
            if args.get('cmd',args.get('command')) != 'gpg --version':continue
            require(context is not None and args.get('sandbox_permissions','use_default') == 'use_default'
                    and args.get('workdir',WORK) == WORK, 'negative request context')
            output = p.get('output')
            require(isinstance(output,str) and len(output) <= 4096, 'native refusal format')
            require(output.startswith('exec command rejected:')
                    and ('blocked by policy' in output or 'forbidden by policy' in output),
                    'not a native policy refusal')
            matches.append(dict(call_id=p['call_id'],request=original,output=p,
                                turn_context=context))
    require(turns > 0 and len(matches) == 1, 'native negative missing or repeated')
    return dict(provider_session_id=provider_id, rollout_sha256=hashlib.sha256(raw).hexdigest(),
                native_policy_denial=matches[0])


def workspace_image(root, read):
    """Plain filesystem read only. Never Git or execution while the worker lives."""
    root = Path(root)
    require(root.resolve(strict=True) == root, 'workspace alias')
    entries, size = {}, 0
    def visit(path):
        nonlocal size
        s = path.lstat()
        require(s.st_uid == s.st_gid == 1000 and (stat.S_ISLNK(s.st_mode) or not s.st_mode & 0o022),
                'workspace authority')
        rel = path.relative_to(root).as_posix()
        item = dict(mode=stat.S_IMODE(s.st_mode),type=stat.S_IFMT(s.st_mode))
        require(len(entries) < 30000, 'workspace entry bound')
        if stat.S_ISREG(s.st_mode):
            raw = read(path);size += len(raw)
            require(size <= 512 << 20, 'workspace size bound')
            item.update(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        elif stat.S_ISLNK(s.st_mode):item['target']=os.readlink(path)
        else:require(stat.S_ISDIR(s.st_mode), 'workspace special file')
        entries[rel] = item
        if stat.S_ISDIR(s.st_mode):
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
            try:
                require(os.fstat(fd)==s,'workspace directory open drift')
                names=sorted(os.listdir(fd))
                for name in names:visit(path/name)
                require(sorted(os.listdir(fd))==names and os.fstat(fd)==s and path.lstat()==s,
                        'workspace changed during walk')
            finally:os.close(fd)
    visit(root)
    return entries


SOURCE_MODES = json.loads("{\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/README.md\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/audit-queue-r3.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/bind-task-r5.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/budget-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-census.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-contract.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-probe.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-store.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/cache-atime-policy-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/close-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/common-snapshot-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/generators/make_successor.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/h1-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/hold-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/image1-record-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/observe-integrity-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/observe-terminal-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/ADMIT.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/BIND.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/CLOSE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/CONTAIN-2.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/H1.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/HOLD-1.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/HOLD-2.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/OBSERVE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/PREFLIGHT.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/PREP.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/RESTORE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/RESUME.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/ROUTE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/STAGE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/TERMINAL.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/WATCH-LOOP-2.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/WATCH-LOOP.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/WORKTREE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/pin-s1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/prep-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/restore-admission-r3.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/restore-r9-routes-r3.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/route-chain-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/route-task-r5.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/s1-pins.json\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/suspension-lineage.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/test_c1_contract.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/test_successor.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/test_watch_loop.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/watch-loop-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/watch-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/window-base-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/window-obs-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/window-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/worktree-task-r1.py\":420}")
SOURCE_DIRECTORIES = frozenset(["docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/generators","docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator"])
MAX_PRODUCT_BYTES = 2 << 20


def workspace_delta(before, after, runtime, source=(), evidence=False):
    require(len(source)==len(set(source)) and set(source)<=set(SOURCE_MODES),
            'invalid create-only source inventory')
    for path in source:
        require(path not in before and path in after, 'source is not a new file: '+path)
    total = 0
    for path, expected in runtime.items():
        require(after.get(path)==expected,'required Core materialization absent or different: '+path)
    for path in set(before)|set(after):
        if path in source:
            item=after[path]
            require(item.get('type')==stat.S_IFREG and item.get('mode')==SOURCE_MODES[path]
                    and type(item.get('size')) is int and 0<=item['size']<=MAX_PRODUCT_BYTES,
                    'new source authority or bound: '+path)
            total+=item['size']
        elif path in before:require(before[path]==after.get(path),'pre-edit workspace mutation: '+path)
        elif path in runtime:require(after[path]==runtime[path],'Core materialization differs: '+path)
        elif source and path in SOURCE_DIRECTORIES:
            require(after[path]==dict(mode=0o755,type=stat.S_IFDIR),'new source directory authority')
        elif evidence and path in ('.gc/worker-evidence','.gc/worker-evidence/'+TASK,EVIDENCE):
            require(after[path]==dict(mode=0o700,type=stat.S_IFDIR),'evidence directory authority')
        elif evidence and path.startswith(EVIDENCE+'/'):
            require(after[path]['type'] in (stat.S_IFREG,stat.S_IFDIR),'unsafe evidence type')
        else:raise RuntimeError('unexpected startup file: '+path)
    require(total<=MAX_PRODUCT_BYTES,'total new source bound')


def pristine_startup(before, after, report_sha, runtime):
    allowed = {'.gc','.gc/worker-evidence','.gc/worker-evidence/'+TASK,EVIDENCE,
               EVIDENCE+'/startup.json',EVIDENCE+'/positive-write.txt'}
    additions={path:row for path,row in after.items() if path not in before and path in allowed}
    workspace_delta(before,after,dict(runtime,**additions))
    for path in ('.gc','.gc/worker-evidence','.gc/worker-evidence/'+TASK,EVIDENCE):
        require(after.get(path) == dict(mode=0o700,type=stat.S_IFDIR)
                or path in before, 'startup directory shape')
    positive=b'Owned workspace write proof.\n'
    require(after.get(EVIDENCE+'/positive-write.txt') == dict(mode=0o600,type=stat.S_IFREG,
        size=len(positive),sha256=hashlib.sha256(positive).hexdigest()), 'positive marker differs')
    item=after.get(EVIDENCE+'/startup.json',{})
    require(item.get('sha256') == report_sha and item.get('mode') == 0o600
            and item.get('type') == stat.S_IFREG, 'startup report file differs')


import calendar

from datetime import datetime, timezone

import hashlib

import json

import re

KEYS = frozenset((
    'gc.controller_error', 'gc.failure_owner', 'gc.failure_reason',
    'gc.failure_subject', 'gc.progress_attention_signature',
    'gc.progress_last_observed_at',
))

def stamp(value, *, offset=False, canonical=True):
    """RFC3339Nano without float or sub-microsecond truncation."""
    require(isinstance(value, str), 'review wait timestamp type')
    match = re.fullmatch(
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?'
        r'(Z|[+-]\d{2}:\d{2})', value)
    require(match is not None and (offset or match[3] == 'Z'),
            'review wait timestamp format')
    zone = match[3]
    require(zone == 'Z' or (int(zone[1:3]) < 24 and int(zone[4:]) < 60
                           and zone != '-00:00'), 'review wait timestamp offset')
    fraction = match[2] or ''
    # Core uses RFC3339Nano, whose fractional suffix has no redundant zeros.
    require(not canonical or not fraction or not fraction.endswith('0'),
            'noncanonical review wait fraction')
    try:
        whole = datetime.fromisoformat(match[1] + match[3].replace('Z', '+00:00'))
        seconds = calendar.timegm(whole.astimezone(timezone.utc).utctimetuple())
    except (ValueError, OverflowError) as exc:
        raise RuntimeError('review wait timestamp calendar or offset') from exc
    return seconds * 10**9 + int(fraction.ljust(9, '0'))

def monitoring_state(task, routed, session, observed_at):
    """Fresh task: no inherited failure or progress-stall exception."""
    require(isinstance(task, dict) and isinstance(routed, dict) and isinstance(session, dict),
            'monitoring input shape')
    require(task.get('id') == routed.get('id') == TASK
            and task.get('status') == 'in_progress'
            and task.get('assignee') == session.get('session_name')
            and isinstance(session.get('id'), str)
            and re.fullmatch(r'ci-[a-z0-9]+', session['id'])
            and session.get('session_name') == 'codex-' + session['id'],
            'monitoring claim identity')
    claim_metadata(routed, session, task.get('metadata'))
    require(task.get('labels') == routed.get('labels'), 'monitoring labels differ')
    require(stamp(session.get('created_at')) <= stamp(task.get('updated_at')) <= stamp(observed_at),
            'monitoring chronology')
    return {'kind': 'exact-fresh-claim', 'source_release_authorized_by_this_check': False}


def waiting_turn(raw, session, report_digest, probe_digest, observed_at):
    """Require native completion of the exact waiting turn, not a stuck tool.

    The existing native transcript reader separately binds CLI identity and
    permissions. This additional proof is deliberately non-authoritative.
    """
    require(isinstance(raw, bytes) and len(raw) <= 32 << 20 and raw.endswith(b'\n'),
            'waiting transcript bound or partial line')
    rows = [json.loads(line) for line in raw.splitlines()]
    require(rows and rows[0].get('type') == 'session_meta', 'waiting transcript metadata')
    for value in (report_digest, probe_digest):
        require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value),
                'waiting digest format')
    marker = ('WAITING FOR SOURCE RELEASE: ga-mb91 session=' + session['id']
              + ' report_sha256=' + report_digest + ' probe_sha256=' + probe_digest)
    meaningful = [r for r in rows if not (r.get('type') == 'token_usage_record'
                  or r.get('type') == 'event_msg'
                  and r.get('payload', {}).get('type') == 'token_count')]
    require(len(meaningful) >= 3, 'incomplete waiting turn')
    final, done = meaningful[-2:]
    payload = final.get('payload', {})
    require(final.get('type') == 'response_item' and payload.get('type') == 'message'
            and payload.get('role') == 'assistant' and payload.get('phase') == 'final_answer'
            and payload.get('content') == [{'type': 'output_text', 'text': marker}],
            'native final answer is not exact waiting marker')
    require(done.get('type') == 'event_msg'
            and done.get('payload', {}).get('type') == 'task_complete'
            and done['payload'].get('last_agent_message') == marker,
            'native waiting turn is not complete')
    # Native records retain millisecond zero suffixes. Core strings remain canonical.
    final_ns = stamp(final.get('timestamp'), canonical=False)
    complete_ns = stamp(done.get('timestamp'), canonical=False)
    require(stamp(session.get('created_at')) <= final_ns
            <= complete_ns <= stamp(observed_at), 'native waiting chronology')
    native_id = rows[0].get('payload', {}).get('id')
    turn_id = done['payload'].get('turn_id')
    usage_keys = {'input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
                  'output_tokens', 'reasoning_output_tokens', 'total_tokens'}
    for row in rows[rows.index(final) + 1:]:
        if row.get('type') != 'token_usage_record':
            continue  # Only the already classified token_count and completion remain.
        accounting = row.get('payload')
        require(set(row) == {'timestamp', 'ordinal', 'type', 'payload'}
                and type(row['ordinal']) is int and row['ordinal'] >= 0,
                'native accounting record shape')
        require(isinstance(accounting, dict) and set(accounting) == {
            'thread_id', 'turn_id', 'session_id', 'root_turn_id', 'response_id',
            'usage', 'turn_token_usage', 'thread_token_usage'}, 'native accounting payload')
        require(isinstance(native_id, str) and native_id
                and accounting['thread_id'] == accounting['session_id'] == native_id
                and isinstance(turn_id, str) and turn_id
                and accounting['turn_id'] == accounting['root_turn_id'] == turn_id,
                'native accounting identity')
        require(isinstance(accounting['response_id'], str)
                and re.fullmatch(r'resp_[0-9a-f]+', accounting['response_id']),
                'native accounting response identity')
        for key in ('usage', 'turn_token_usage', 'thread_token_usage'):
            counters = accounting[key]
            require(isinstance(counters, dict) and set(counters) == usage_keys
                    and all(type(value) is int and value >= 0 for value in counters.values()),
                    'native accounting counters')
        require(final_ns <= stamp(row['timestamp'], canonical=False) <= complete_ns,
                'native accounting chronology')
    require(complete_ns // 10**9 == stamp(session.get('last_active'), offset=True) // 10**9,
            'waiting turn differs from independently observed last activity')
    return {'completed_waiting_turn': True, 'session_id': session['id'],
            'completed_at': done['timestamp'], 'rollout_sha256': hashlib.sha256(raw).hexdigest(),
            'source_release_authorized_by_this_check': False}
