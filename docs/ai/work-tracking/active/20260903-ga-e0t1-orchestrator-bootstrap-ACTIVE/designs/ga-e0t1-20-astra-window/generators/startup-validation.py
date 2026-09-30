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

WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
BASE = 'c6b789bbe6ff677dd04336803dbf2c2e017812ba'
TASK = 'ga-e0t1.20'
BRANCH = 'codex/ga-e0t1.20-c1-close-admission'
CODEX = '/home/loucmane/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex'
EVIDENCE = '.gc/worker-evidence/'+TASK
NEGATIVE_SCRIPT = ('try { text({probe_return: await tools.exec_command({"cmd":"gpg --version",'
    '"workdir":"'+WORK+'","sandbox_permissions":"use_default","max_output_tokens":1000})}); } '
    'catch (error) { text({probe_error: String(error)}); }')
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
    # Only this first native claim may introduce started_at. This is bounded
    # bookkeeping, not identity evidence; exact claim/source checks remain.
    require('started_at' not in routed, 'routed task already has a start time')
    started=native_time(task.get('started_at'))
    created=native_time(routed.get('created_at'))
    routed_at=native_time(routed.get('updated_at'))
    session_at=native_time(session.get('created_at'))
    updated=native_time(task.get('updated_at'))
    require(created <= routed_at <= started <= updated and session_at <= started,
            'native claim timestamp order')


def live_task(task, routed, session, contract, startup_digest):
    require(task.get('id') == TASK and task.get('status') == 'in_progress', 'task not in progress')
    require(task.get('assignee') == session['session_name'], 'native claim owner differs')
    expected = dict(routed['metadata'], **{
        'gc.session_id':session['id'],'gc.session_name':session['session_name']})
    if 'gc.work_branch' in task.get('metadata',{}):expected['gc.work_branch']=BRANCH
    require(task.get('metadata') == expected, 'claim metadata differs')
    note = 'STARTUP READY: '+TASK+' report_sha256='+startup_digest
    require(task.get('notes') == routed['notes']+'\n'+note, 'startup note is not exact or single')
    claim_time(task,routed,session)
    for key in set(task) | set(routed):
        if key not in ('status','assignee','metadata','notes','updated_at','started_at'):
            require(task.get(key) == routed.get(key), 'task changed outside claim and startup note: '+key)
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
    expected = dict(schema='ga-e0t1.20.worker-startup.v1', task=TASK, session_id=session['id'],
        worktree=WORK, base=BASE, branch=BRANCH, subscription='ChatGPT', provider_overrides_absent=True,
        credential_values_exported=False, codex_sha256=probe.CODEX_SHA, local_rules=probe.RULES,
        default_rules_sha256=probe.DEFAULT_SHA, workspace_write=True, source_edit_released=False)
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
    require(isinstance(policy,dict) and policy.get('type') == 'workspace-write'
        and policy.get('writable_roots') == [WORK] and policy.get('network_access') is False,
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
                if original.get('name') != 'exec' or original.get('input') != NEGATIVE_SCRIPT:continue
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
                require(output.startswith('exec command rejected:')
                        and ('blocked by policy' in output or 'forbidden by policy' in output),
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
            names = sorted(path.iterdir())
            for child in names:visit(child)
            require(sorted(path.iterdir()) == names and path.lstat() == s, 'workspace changed during walk')
    visit(root)
    return entries


def workspace_delta(before, after, runtime, source=(), evidence=False):
    for path in set(before)|set(after):
        if path in source:
            require(path in before and path in after and before[path]['type']==after[path]['type']==stat.S_IFREG
                    and before[path]['mode']==after[path]['mode'],'source authority changed: '+path)
        elif path in before:require(before[path]==after.get(path),'pre-edit workspace mutation: '+path)
        elif path in runtime:require(after[path]==runtime[path],'Core materialization differs: '+path)
        elif evidence and (path==EVIDENCE or path.startswith(EVIDENCE+'/') or path=='.gc/worker-evidence'):
            require(after[path]['type'] in (stat.S_IFREG,stat.S_IFDIR),'unsafe evidence type')
        else:raise RuntimeError('unexpected startup file: '+path)


def pristine_startup(before, after, report_sha, runtime):
    allowed = {'.gc','.gc/worker-evidence',EVIDENCE,
               EVIDENCE+'/startup.json',EVIDENCE+'/positive-write.txt'}
    additions={path:row for path,row in after.items() if path not in before and path in allowed}
    workspace_delta(before,after,dict(runtime,**additions))
    for path in ('.gc','.gc/worker-evidence',EVIDENCE):
        require(after.get(path) == dict(mode=0o700,type=stat.S_IFDIR)
                or path in before, 'startup directory shape')
    positive=b'Owned workspace write proof.\n'
    require(after.get(EVIDENCE+'/positive-write.txt') == dict(mode=0o600,type=stat.S_IFREG,
        size=len(positive),sha256=hashlib.sha256(positive).hexdigest()), 'positive marker differs')
    item=after.get(EVIDENCE+'/startup.json',{})
    require(item.get('sha256') == report_sha and item.get('mode') == 0o600
            and item.get('type') == stat.S_IFREG, 'startup report file differs')
