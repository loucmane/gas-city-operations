"""R7 operational regression fixtures. No worker, lifecycle or production writes."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).parent
OLD = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
sys.path.insert(0, str(OLD/'generators'))
BASELINE = os.environ.get('R7_BASELINE') == '1'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def validator():
    if BASELINE:
        return module(OLD/'startup-validation.py', 'old_validator')
    import protocol_r7
    import types
    m = types.ModuleType('r7_validator')
    exec(compile(protocol_r7.validator_source(), '<r7-validator>', 'exec'), m.__dict__)
    return m


def native():
    return json.loads((HERE/'native-r6-protocol.json').read_bytes())


def encode(records):
    return ('\n'.join(json.dumps(x) for x in records)+'\n').encode()


def test_actual_native_protocol_is_admitted():
    f = native()
    result = validator().denial_from_rollout(encode(f['records']), f['records'][0]['payload']['id'])
    assert result['native_policy_denial']['call_id'] == 'call_dcwjQFe2ctD9KAreL3q6rxiT'


def test_actual_implicit_cwd_sandbox_is_admitted():
    validator().turn(native()['records'][1]['payload'])


@pytest.mark.parametrize('change', ['root', 'network', 'sandbox', 'unknown-policy', 'tmp-exclusion',
    'workspace-roots', 'filesystem-write', 'profile-write', 'model', 'approval'])
def test_native_posture_negatives(change):
    ctx = native()['records'][1]['payload']
    if change == 'root': ctx['sandbox_policy']['writable_roots'] = ['/']
    elif change == 'network': ctx['sandbox_policy']['network_access'] = True
    elif change == 'sandbox': ctx['sandbox_policy']['type'] = 'danger-full-access'
    elif change == 'unknown-policy': ctx['sandbox_policy']['unknown'] = True
    elif change == 'tmp-exclusion': ctx['sandbox_policy']['exclude_slash_tmp'] = True
    elif change == 'workspace-roots': ctx['workspace_roots'] = ['/tmp']
    elif change == 'filesystem-write': ctx['file_system_sandbox_policy']['entries'].append({'path': {'type':'path','path':'/etc'}, 'access':'write'})
    elif change == 'profile-write': ctx['permission_profile']['file_system']['entries'][0]['access'] = 'write'
    elif change == 'model': ctx['model'] = 'different'
    elif change == 'approval': ctx['approval_policy'] = 'on-request'
    with pytest.raises(RuntimeError): validator().turn(ctx)


@pytest.mark.parametrize('change', ['echo', 'append', 'escalation', 'wrong-command', 'unknown-error',
    'success', 'different-call', 'twice', 'worker-text', 'no-context', 'output-before-call'])
def test_real_native_denial_cannot_be_faked(change):
    rows = native()['records']; call = rows[2]['payload']; out = rows[3]['payload']
    if change == 'echo': call['input'] = 'text({probe_error:"denied"});'
    elif change == 'append': call['input'] += 'text("extra");'
    elif change == 'escalation': call['input'] = call['input'].replace('"max_output_tokens":1000', '"sandbox_permissions":"require_escalated","max_output_tokens":1000')
    elif change == 'wrong-command': call['input'] = call['input'].replace('gpg --version','git status')
    elif change == 'unknown-error': out['output'][1]['text'] = '{"probe_error":"permission denied"}'
    elif change == 'success': out['output'][1]['text'] = '{"probe_return":{"exit_code":1,"output":"Rejected"}}'
    elif change == 'different-call': out['call_id'] = 'other'
    elif change == 'twice': rows.append(copy.deepcopy(rows[-1]))
    elif change == 'worker-text': out['type'] = 'message'
    elif change == 'no-context': rows.pop(1)
    elif change == 'output-before-call': rows[2], rows[3] = rows[3], rows[2]
    with pytest.raises(RuntimeError): validator().denial_from_rollout(encode(rows), rows[0]['payload']['id'])


def fake_host(tmp_path, monkeypatch):
    v = validator()
    r = module(OLD/'startup-release.py', 'old_release') if BASELINE else module(HERE/'runtime_process_r7.py','r7_process')
    proc = tmp_path/'proc'; proc.mkdir()
    rows = {100:dict(ppid=90,start='1000',state='S'),
            101:dict(ppid=100,start='1001',state='S'),
            102:dict(ppid=100,start='1002',state='S')}
    for row in rows.values(): row.update(uid=1000,gid=1000)
    key = native()['records'][0]['payload']['id']
    session = dict(id='ci-fixture',session_name='codex-ci-fixture',session_key=key)
    codehost = str(Path(v.CODEX).with_name('codex-code-mode-host'))
    plugin = '/home/loucmane/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.10-13ceeea1f599'
    argv = [v.CODEX,'-c','mcp_servers.serena.enabled=false','-c','mcp_servers.aegis.enabled=false',
            '--model','gpt-6-astra','-c','model_reasoning_effort=high','--ask-for-approval','never',
            '--sandbox','workspace-write','-c','sandbox_workspace_write.writable_roots='+json.dumps([v.WORK]), 'fixture prompt']
    for pid, exe, cwd, args in ((100,v.CODEX,v.WORK,argv),(101,codehost,v.WORK,[codehost]),
            (102,'/usr/bin/node',plugin,['node','./mcp/server.cjs','--stdio'])):
        p = proc/str(pid); p.mkdir(); (p/'exe').symlink_to(exe); (p/'cwd').symlink_to(cwd)
        (p/'cmdline').write_bytes(b'\0'.join(a.encode() for a in args)+b'\0')
        (p/'cgroup').write_text('0::/user.slice/fixture.service\n')
        (p/'fd').mkdir()
    env = {'GC_SESSION_ID':session['id'],'GC_SESSION_NAME':session['session_name'],
           'GC_HOME':'/home/loucmane/gascity/home','GIT_OPTIONAL_LOCKS':'0','HOME':'/home/loucmane'}
    (proc/'100/environ').write_bytes(b'\0'.join((k+'='+val).encode() for k,val in env.items())+b'\0')
    log = '/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T16-33-11-'+key+'.jsonl'
    (proc/'100/fd/10').symlink_to(log)
    monkeypatch.setattr(r,'process_table',lambda: copy.deepcopy(rows))
    if BASELINE:
        original = Path
        monkeypatch.setattr(r,'Path',lambda p: proc if str(p)=='/proc' else original(p))
    else:
        monkeypatch.setattr(r,'PROC',proc)
        monkeypatch.setattr(r,'verify_assets',lambda read: None)
    read = lambda path,limit=0: encode(native()['records']) if str(path)==log else b'fixture'
    return r,v,proc,rows,session,read


def test_actual_branched_worker_graph_reaches_native_proof(tmp_path,monkeypatch):
    r,v,proc,rows,s,read = fake_host(tmp_path,monkeypatch)
    proof = r.worker_identity(100,s,v,read)
    assert proof['pid'] == 100
    assert {x['pid'] for x in proof['chain']} == {100,101,102}
    assert proof['native']['native_policy_denial']['call_id'] == 'call_dcwjQFe2ctD9KAreL3q6rxiT'


@pytest.mark.parametrize('change',['unknown-child','grandchild','missing-codehost','second-codehost',
    'helper-argv','node-argv','node-cwd','cgroup','dead','root-cwd','override','root-not-codex','owner'])
def test_process_graph_remains_closed(change,tmp_path,monkeypatch):
    r,v,proc,rows,s,read = fake_host(tmp_path,monkeypatch)
    if change == 'unknown-child': rows[103] = dict(ppid=100,start='2000',state='S')
    elif change == 'grandchild': rows[103] = dict(ppid=101,start='2000',state='S')
    elif change == 'missing-codehost': rows.pop(101)
    elif change == 'second-codehost': rows[103] = dict(ppid=100,start='2000',state='S')
    elif change == 'helper-argv': (proc/'101/cmdline').write_bytes(b'codex-code-mode-host\0--extra\0')
    elif change == 'node-argv': (proc/'102/cmdline').write_bytes(b'node\0-e\0evil\0')
    elif change == 'node-cwd': (proc/'102/cwd').unlink(); (proc/'102/cwd').symlink_to('/tmp')
    elif change == 'cgroup': (proc/'101/cgroup').write_text('0::/foreign.scope\n')
    elif change == 'dead': rows[101]['state'] = 'Z'
    elif change == 'root-cwd': (proc/'100/cwd').unlink(); (proc/'100/cwd').symlink_to('/tmp')
    elif change == 'override': (proc/'100/environ').write_bytes((proc/'100/environ').read_bytes()+b'OPENAI_API_KEY=not-a-secret-fixture\0')
    elif change == 'root-not-codex': (proc/'100/exe').unlink(); (proc/'100/exe').symlink_to('/usr/bin/python3')
    elif change == 'owner': rows[101]['uid'] = 0
    with pytest.raises((RuntimeError,FileNotFoundError)): r.worker_identity(100,s,v,read)


@pytest.mark.skipif(BASELINE, reason='new second-observation regression')
@pytest.mark.parametrize('change',['pid-reuse','exec-same-pid','new-child','argv-change','cwd-change'])
def test_immediate_recheck_binds_exec_and_topology(change,tmp_path,monkeypatch):
    r,v,proc,rows,s,read = fake_host(tmp_path,monkeypatch)
    proof = r.worker_identity(100,s,v,read)
    if change == 'pid-reuse': rows[101]['start'] = '9999'
    elif change == 'exec-same-pid': (proc/'101/exe').unlink(); (proc/'101/exe').symlink_to('/usr/bin/python3')
    elif change == 'new-child': rows[103] = dict(ppid=100,start='2000',state='S')
    elif change == 'argv-change': (proc/'102/cmdline').write_bytes(b'node\0-e\0evil\0')
    elif change == 'cwd-change': (proc/'102/cwd').unlink(); (proc/'102/cwd').symlink_to('/tmp')
    with pytest.raises((RuntimeError,FileNotFoundError)): r.revalidate(proof,v,read)


@pytest.mark.skipif(BASELINE, reason='R7 asset and assembly tests')
def test_asset_authority_and_hash_fail_closed(tmp_path, monkeypatch):
    r=module(HERE/'runtime_process_r7.py','r7_assets')
    p=tmp_path/'helper'; raw=b'pinned fixture'; p.write_bytes(raw); p.chmod(0o644)
    monkeypatch.setattr(r,'PINS',{str(p):(os.getuid(),0o644,hashlib.sha256(raw).hexdigest())})
    r.verify_assets(lambda p,limit:p.read_bytes())
    p.write_bytes(b'changed')
    with pytest.raises(RuntimeError): r.verify_assets(lambda p,limit:p.read_bytes())
    p.write_bytes(raw); p.chmod(0o666)
    with pytest.raises(RuntimeError): r.verify_assets(lambda p,limit:p.read_bytes())
    with pytest.raises(RuntimeError): r.root_binary('/usr/bin/python3')


@pytest.mark.skipif(BASELINE, reason='new exact equivalent transport tests')
@pytest.mark.parametrize('explicit,newline',[(False,False),(False,True),(True,False),(True,True)])
def test_four_closed_equivalent_probe_spellings(explicit,newline):
    v=validator(); rows=native()['records']
    script=v.NEGATIVE_SCRIPT
    if not explicit: script=script.replace('"sandbox_permissions":"use_default",','')
    rows[2]['payload']['input']=script+('\n' if newline else '')
    v.denial_from_rollout(encode(rows),rows[0]['payload']['id'])


@pytest.mark.skipif(BASELINE, reason='new release wiring tests')
def test_release_revalidates_graph_after_task_before_nudge():
    import protocol_r7 as p
    raw=(HERE/'runtime_process_r7.py').read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    source=p.release_source(sha)
    assert source.count("w.GC+['session','nudge'")==1
    assert source.index('task2==task') < source.index('runtime.revalidate(proof,v,inspector.file_bytes)')
    assert source.index('runtime.revalidate(proof,v,inspector.file_bytes)') < source.index("w.save('nudge-intent.json'")
    assert sha in source
    assert 'retry=False' in source


@pytest.mark.skipif(BASELINE, reason='new evidence isolation test')
def test_r7_probe_uses_fresh_directory_without_altering_r6():
    import protocol_r7 as p
    raw=p.worker_probe().decode()
    assert "OUT = WORK/'.gc/worker-evidence/ga-e0t1.20/r7'" in raw
    assert 'directory(OUT, create=True)' in raw
    assert 'os.O_EXCL' in raw
    old=p.frozen('worker-startup-r6.py')
    assert raw.replace("OUT = WORK/'.gc/worker-evidence/ga-e0t1.20/r7'",
                       "OUT = WORK/'.gc/worker-evidence/ga-e0t1.20'").encode()==old
