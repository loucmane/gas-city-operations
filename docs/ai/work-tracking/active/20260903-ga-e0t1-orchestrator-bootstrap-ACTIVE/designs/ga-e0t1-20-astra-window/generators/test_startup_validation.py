"""Synthetic native transcript/identity negatives, not a live capability claim."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

HERE=Path(__file__).parent


def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


v=load('startup-validation')
p=load('worker-startup')


def test_scheduler_state_change_is_not_process_identity_drift():
    before=dict(ppid=10,start='1234',state='S')
    assert v.same_process(before,dict(before,state='R'))
    for after in (None,dict(before,state='Z'),dict(before,state='X'),
                  dict(before,start='1235'),dict(before,ppid=11)):
        assert not v.same_process(before,after)


def argv():
    return [v.CODEX,'-c','mcp_servers.serena.enabled=false','-c','mcp_servers.aegis.enabled=false',
        '--model','gpt-6-astra','-c','model_reasoning_effort=high','--ask-for-approval','never',
        '--sandbox','workspace-write','-c','sandbox_workspace_write.writable_roots='+json.dumps([v.WORK]),
        'Synthetic reviewed prompt']


def test_actual_closed_argv_and_only_prompt_digest():
    result=v.process_arguments(argv())
    assert result['prompt_sha256']==hashlib.sha256(b'Synthetic reviewed prompt').hexdigest()
    assert 'Synthetic reviewed prompt' not in json.dumps(result)


@pytest.mark.parametrize('tail',[
    ['--dangerously-bypass-approvals-and-sandbox'],['--full-auto'],['--model','gpt-6-sol'],
    ['-c','sandbox_workspace_write.writable_roots=["/"]'],['-c','mcp_servers.aegis.enabled=true'],
    ['--ask-for-approval','on-request'],['resume','old-id'],['--config'],
])
def test_extra_duplicate_or_broader_argv_refuses(tail):
    value=argv();value[-1:-1]=tail
    with pytest.raises(RuntimeError):v.process_arguments(value)


def context():
    return dict(cwd=v.WORK,model='gpt-6-astra',effort='high',approval_policy='never',
        sandbox_policy=dict(type='workspace-write',writable_roots=[v.WORK],network_access=False))


KEY='00000000-0000-0000-0000-000000000001'


def transcript():
    return [dict(type='session_meta',payload=dict(id=KEY,cwd=v.WORK,cli_version='0.153.4')),
        dict(type='turn_context',payload=context()),
        dict(type='response_item',payload=dict(type='function_call',call_id='call-1',
            name='functions.exec_command',arguments=json.dumps(dict(cmd='gpg --version',workdir=v.WORK)))),
        dict(type='response_item',payload=dict(type='function_call_output',call_id='call-1',
            output='exec command rejected: blocked by policy'))]


def encoded(rows):return ('\n'.join(json.dumps(row) for row in rows)+'\n').encode()


def test_native_literal_request_output_pair_binds():
    rows=transcript();proof=v.denial_from_rollout(encoded(rows),KEY)
    assert proof['native_policy_denial']['call_id']=='call-1'
    assert proof['rollout_sha256']==hashlib.sha256(encoded(rows)).hexdigest()


def code_transcript():
    rows=transcript()
    rows[2]['payload']=dict(type='custom_tool_call',call_id='call-1',name='exec',input=v.NEGATIVE_SCRIPT)
    rows[3]['payload']=dict(type='custom_tool_call_output',call_id='call-1',output=[
        dict(type='input_text',text='Script completed\nWall time 0.1 seconds\nOutput:\n'),
        dict(type='input_text',text=json.dumps(dict(probe_error='Error: exec command rejected: blocked by policy')))])
    return rows


def test_pinned_cli_code_mode_literal_causal_exception():
    rows=code_transcript()
    assert v.denial_from_rollout(encoded(rows),KEY)['native_policy_denial']['call_id']=='call-1'
    assert v.NEGATIVE_SCRIPT in (HERE/'WORKER-BRIEF.md').read_text()


@pytest.mark.parametrize('change',['echo','second-call','escalation','success','shell-failure',
    'unknown-error','extra-output','mismatched-call','non-completion','wrong-type'])
def test_code_mode_cannot_synthesize_or_substitute_denial(change):
    rows=code_transcript();call=rows[2]['payload'];result=rows[3]['payload']
    if change=='echo':call['input']='text({probe_error:"Error: exec command rejected: blocked by policy"});'
    elif change=='second-call':call['input']+=' text("extra");'
    elif change=='escalation':call['input']=call['input'].replace('use_default','require_escalated')
    elif change=='success':result['output'][1]['text']=json.dumps(dict(probe_return=dict(exit_code=0,output='gpg 2')))
    elif change=='shell-failure':result['output'][1]['text']=json.dumps(dict(probe_return=dict(exit_code=1,output='blocked by policy')))
    elif change=='unknown-error':result['output'][1]['text']=json.dumps(dict(probe_error='permission denied'))
    elif change=='extra-output':result['output'].append(dict(type='input_text',text='extra'))
    elif change=='mismatched-call':result['call_id']='different'
    elif change=='non-completion':result['output'][0]['text']='Script running'
    elif change=='wrong-type':result['type']='function_call_output'
    with pytest.raises(RuntimeError):v.denial_from_rollout(encoded(rows),KEY)


@pytest.mark.parametrize('change',[
    'output-success','output-shell-denied','echo','different-call','worker-text','wrong-model',
    'broader-root','wrong-workspace','wrong-session','other-version','no-turn','extra-turn',
    'duplicate-denial','escalated','partial-line',
])
def test_unproven_native_denials_refuse(change):
    rows=transcript()
    if change=='output-success':rows[-1]['payload']['output']='gpg (GnuPG) 2.4.4'
    elif change=='output-shell-denied':rows[-1]['payload']['output']='zsh: permission denied: gpg'
    elif change=='echo':rows[2]['payload']['arguments']=json.dumps(dict(cmd="echo 'exec command rejected: blocked by policy'"))
    elif change=='different-call':rows[-1]['payload']['call_id']='other'
    elif change=='worker-text':rows[-1]['payload']['type']='message'
    elif change=='wrong-model':rows[1]['payload']['model']='gpt-6-sol'
    elif change=='broader-root':rows[1]['payload']['sandbox_policy']['writable_roots'].append('/')
    elif change=='wrong-workspace':rows[0]['payload']['cwd']='/tmp'
    elif change=='wrong-session':rows[0]['payload']['id']='wrong'
    elif change=='other-version':rows[0]['payload']['cli_version']='unknown'
    elif change=='no-turn':rows.pop(1)
    elif change=='extra-turn':
        extra=context();extra['approval_policy']='never-and-bypass'
        rows.append(dict(type='turn_context',payload=extra))
    elif change=='duplicate-denial':rows.append(copy.deepcopy(rows[-1]))
    elif change=='escalated':rows[2]['payload']['arguments']=json.dumps(dict(cmd='gpg --version',sandbox_permissions='require_escalated'))
    raw=encoded(rows)
    if change=='partial-line':raw=raw[:-1]
    with pytest.raises(RuntimeError):v.denial_from_rollout(raw,KEY)


def session():
    return dict(id='ci-synthetic',session_name='gc__gascity-codex-ci-synthetic',template='gascity/codex',
        rig='gascity',provider='codex-managed',work_dir=v.WORK,closed=False,session_key=KEY)


def test_actual_native_session_shape_and_extra_session_negative():
    s=session();c=dict(ok=True,schema_version='1',sessions=[s])
    assert v.session_row(c)==s
    c['sessions'].append(copy.deepcopy(s))
    with pytest.raises(RuntimeError):v.session_row(c)


def test_claim_uses_tmux_session_name_and_stamps_native_id():
    c=load('contract');c.BOUND_NOTE='synthetic bound note'
    routed=json.loads((HERE/'task-own-fields.json').read_bytes())
    routed.update(status='open',assignee='',metadata={'gc.work_dir':v.WORK,'gc.routed_to':'gascity/codex'},
        notes=c.BOUND_NOTE,dependencies=[dict(id='ga-e0t1',dependency_type='parent-child')])
    s=session();sha='a'*64
    actual=copy.deepcopy(routed)
    actual.update(status='in_progress',assignee=s['session_name'],notes=routed['notes']+'\nSTARTUP READY: '+v.TASK+' report_sha256='+sha)
    actual['metadata'].update({'gc.session_id':s['id'],'gc.session_name':s['session_name'],'gc.work_branch':v.BRANCH})
    v.live_task(actual,routed,s,c,sha)
    actual['metadata'].pop('gc.work_branch')
    v.live_task(actual,routed,s,c,sha)
    actual['metadata']['gc.work_branch']='foreign-branch'
    with pytest.raises(RuntimeError):v.live_task(actual,routed,s,c,sha)
    actual['metadata'].pop('gc.work_branch')
    actual['assignee']=s['id']
    with pytest.raises(RuntimeError):v.live_task(actual,routed,s,c,sha)


def test_pristine_workspace_allows_only_probe_evidence(tmp_path,monkeypatch):
    monkeypatch.setattr(v,'EVIDENCE','.gc/worker-evidence/ga-e0t1.20')
    (tmp_path/'source.txt').write_text('unchanged')
    (tmp_path/'pointer').symlink_to('source.txt')
    before=v.workspace_image(tmp_path,p.read_regular)
    for rel in ('.gc','.gc/worker-evidence',v.EVIDENCE):(tmp_path/rel).mkdir(mode=0o700)
    out=tmp_path/v.EVIDENCE
    p.exclusive(out/'positive-write.txt',b'Owned workspace write proof.\n')
    p.exclusive(out/'startup.json',b'{}\n')
    sha=hashlib.sha256(b'{}\n').hexdigest()
    after=v.workspace_image(tmp_path,p.read_regular)
    v.pristine_startup(before,after,sha,{})
    (tmp_path/'source.txt').write_text('premature change')
    with pytest.raises(RuntimeError,match='pre-edit'):v.pristine_startup(before,v.workspace_image(tmp_path,p.read_regular),sha,{})


def test_release_has_one_native_nudge_after_consumed_intent_and_all_checks():
    text=(HERE/'startup-release.py').read_text()
    assert text.count("w.GC+['session','nudge'")==1
    assert text.index("w.save('nudge-intent.json'") < text.index("phase('source-release'")
    assert text.index('v.pristine_startup(') < text.index("w.save('nudge-intent.json'")
    assert text.index('task2==task') < text.index("w.save('nudge-intent.json'")
    assert 'worker_identity(' in text and 'os.pidfd_open' in text
    assert 'retry=False' in text and "'startup release already consumed'" in text


def test_native_process_transcript_identity_does_not_require_late_core_resume_key():
    path='/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T00-01-02-'+KEY+'.jsonl'
    for s in ({},{'session_key':''},{'session_key':KEY}):assert v.transcript_key(path,s)==KEY
    with pytest.raises(RuntimeError):v.transcript_key(path,{'session_key':'other'})
    with pytest.raises(RuntimeError):v.transcript_key('/tmp/invented.jsonl',{})


@pytest.mark.parametrize('change',['none','wrong-hash','wrong-link','extra-runtime','source-edit','policy-edit'])
def test_closed_core_materialization_preserves_source_and_policy(change):
    c=load('contract')
    before={'source':dict(type=0o100000,mode=0o644,sha256='base',size=4),
            'policy':dict(type=0o100000,mode=0o644,sha256='fixed',size=5)}
    after=copy.deepcopy(dict(before,**c.RUNTIME_IMAGE))
    if change=='wrong-hash':after['.gc/settings.json']['sha256']='changed'
    if change=='wrong-link':after['.agents/skills/core.gc-work']['target']='/tmp/foreign'
    if change=='extra-runtime':after['.gc/tmp/invented']=dict(type=0o100000,mode=0o600,size=0,sha256='')
    if change=='source-edit':after['source']['sha256']='premature'
    if change=='policy-edit':after['policy']['sha256']='changed'
    if change=='none':v.workspace_delta(before,after,c.RUNTIME_IMAGE)
    else:
        with pytest.raises(RuntimeError):v.workspace_delta(before,after,c.RUNTIME_IMAGE)


def test_post_terminal_delta_allows_only_declared_source_and_bounded_evidence():
    c=load('contract');path=c.SOURCE_PATHS[1]
    before={path:dict(type=0o100000,mode=0o644,size=4,sha256='base')}
    after=copy.deepcopy(dict(before,**c.RUNTIME_IMAGE))
    after[path]['sha256']='candidate'
    after[v.EVIDENCE+'/result.json']=dict(type=0o100000,mode=0o600,size=2,sha256='evidence')
    v.workspace_delta(before,after,c.RUNTIME_IMAGE,source=[path],evidence=True)
    after[path]['mode']=0o755
    with pytest.raises(RuntimeError):v.workspace_delta(before,after,c.RUNTIME_IMAGE,source=[path],evidence=True)
