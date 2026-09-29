"""Fresh R11 packaging and R10 preservation, without live execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import pytest
import startup_r11 as s
import recovered_claim_r11 as r
import permissions_baseline_r11 as p
import workspace_r11 as workspace
import startup_r5
import types

def load(path,pin):
    raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
    return json.loads(raw)

def evidence():
    return {path:load(path,pin) for path,pin in r.PINS.items()}

def test_prompt_probe_delta_is_successor_identity_only():
    out=s.components();before=s.frozen('worker-startup-r10.py');after=out['worker-startup-r11.py']
    trees=[ast.parse(raw) for raw in (before,after)]
    for tree in trees:
        nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUT' for t in n.targets)]
        assert len(nodes)==1;nodes[0].value=ast.Constant(value='evidence-root')
    assert ast.dump(trees[0])==ast.dump(trees[1])
    prompt=out['PRECLAIM-R11.md'].decode().replace(s.sha(after),s.sha(before))
    prompt=prompt.replace('worker-startup-r11.py','worker-startup-r10.py').replace('/r11','/r10')
    prompt=prompt.replace('ga-e0t1.20 r11','ga-e0t1.20 r10').replace('exact r11 amendment','exact r10 amendment')
    assert prompt==s.frozen('PRECLAIM-R10.md').decode()
    assert '"sandbox_permissions"' not in prompt

def test_preparation_only_new_root_exact_consumed_release_and_no_install():
    out=s.components();text=out['prompt-prep-r11.py'].decode()
    assert s.ROOT in text and s.CLOSE in text and s.CLOSE_SHA in text
    for path,pin in r.PINS.items():
        if path.parent==r.RELEASE:assert pin in text
    assert "assert not Path('/var/tmp/ga-e0t1.20-startup-release" not in text
    assert 'supplemental_prompt_preparation=True' in text
    assert 'prior_preparation_preserved=True' in text
    assert sha_for(out['operator/PROMPT-PREP-R11.sh'],out['prompt-prep-r11.py'])

def sha_for(wrapper,executor):return s.sha(executor).encode() in wrapper

def test_preserved_r10_exact_claim_close_and_startup_note():
    data=evidence();saved=copy.deepcopy(data);pair=r.expected_pair(data,lambda x:x)
    task=pair['task']
    assert task['status']=='open' and not task.get('assignee')
    assert task['metadata']==r.CLOSED_METADATA and task['metadata']['gc.failure_subject']=='ci-9dp7z'
    assert task['started_at']=='2026-09-28T13:01:54Z' and task['notes'].endswith(r.STARTUP)
    assert data==saved

@pytest.mark.parametrize('kind',['source_edit','metadata','labels','startup_note','close_ack','sessions','cleanup','release'])
def test_recovery_refuses_nonexact_prior_evidence(kind):
    data=evidence()
    path=r.CLOSE_ROOT/'16-claim-phase.json'
    rows=json.loads(data[path]['stdout'])
    if kind=='source_edit':rows[0]['title']='foreign task'
    if kind=='metadata':rows[0]['metadata']['gc.failure_subject']='ci-other'
    if kind=='labels':rows[0]['labels']=[]
    if kind=='startup_note':rows[0]['notes']+=' invented'
    data[path]['stdout']=json.dumps(rows)
    if kind=='close_ack':data[r.CLOSE_ROOT/'17-close-phase.json']['stdout']='{}\n'
    if kind=='sessions':data[r.CLOSE_ROOT/'18-sessions-phase.json']['stdout']='{"ok":true,"sessions":[{}]}'
    if kind=='cleanup':data[path]['cleanup']['owned_process_group_gone']=False
    if kind=='release':data[r.RELEASE/'nudge-intent.json']['session_id']='ci-other'
    with pytest.raises(RuntimeError):r.expected_pair(data,lambda x:x)

def permission_args():
    return [load(p.PRIOR/'images.json','59521dd6056d3d67ca60f87f1b42cea4ce9e9ec4b9648188c742358211c66b48'),
        load(p.PRIOR/'history.json','31b1af6ba05b6baaaf97d049ebd9f59b63d5353558ba869bce012c786965f14d'),
        load(p.CAPTURE/'images.json',p.IMAGES_SHA),load(p.CAPTURE/'history.json',p.HISTORY_SHA)]

def test_permissions_preserve_all_old_entries_and_new_private_r10_transcript():
    args=permission_args();saved=copy.deepcopy(args)
    assert p.expected(*args)==(args[2],args[3]) and args==saved

@pytest.mark.parametrize('kind',['old_mode','old_owner','old_acl','old_hash','new_mode','new_owner','new_hash',
    'day_owner','day_mode','day_acl','extra_image','missing_image','extra_history','missing_history'])
def test_permission_continuation_has_no_unreviewed_delta(kind):
    old,history,images,current=args=permission_args()
    rule='/home/loucmane/.codex/rules/default.rules'
    if kind=='old_mode':images[rule]['stat']['mode']^=0o020
    if kind=='old_owner':images[rule]['stat']['uid']+=1
    if kind=='old_acl':images['/home/loucmane/.codex/rules']['xattrs']={}
    if kind=='old_hash':images[rule]['sha256']='0'*64
    if kind=='new_mode':images[p.TRANSCRIPT]['stat']['mode']^=0o004
    if kind=='new_owner':images[p.TRANSCRIPT]['stat']['uid']+=1
    if kind=='new_hash':images[p.TRANSCRIPT]['sha256']='0'*64
    if kind=='day_owner':images[p.DAY]['stat']['uid']+=1
    if kind=='day_mode':images[p.DAY]['stat']['mode']^=0o004
    if kind=='day_acl':images[p.DAY]['xattrs']={}
    if kind=='extra_image':images['/foreign']=copy.deepcopy(images[rule])
    if kind=='missing_image':images.pop(rule)
    if kind=='extra_history':current['sessions']['/foreign']={}
    if kind=='missing_history':current['sessions'].pop(p.TRANSCRIPT)
    with pytest.raises(AssertionError):p.expected(*args)

def test_create_only_preparation_does_not_replay_existing_root(tmp_path):
    root=tmp_path/'prepared';s.main(str(root))
    manifest=json.loads((root/'prompt-prep-r11-manifest.json').read_text())
    assert manifest['execution_admitted'] is False and manifest['worker_launch_included'] is False
    with pytest.raises(AssertionError):s.main(str(root))

def test_actual_post_r10_workspace_preserves_every_prior_file():
    validator=startup_r5.source_module(s.frozen('startup-validation.py'),'r11_validator_fixture')
    probe=startup_r5.source_module(s.frozen('worker-startup-r10.py'),'r11_probe_fixture')
    contract=startup_r5.source_module(s.frozen('contract.py'),'r11_contract_fixture')
    current=validator.workspace_image(Path(contract.WORK),probe.read_regular)
    def read(path,pin):
        raw=probe.read_regular(path);assert s.sha(raw)==pin;return raw
    def module(path,pin):
        assert path.name=='prior-startup-validation-r10.py'
        assert pin==s.sha(s.frozen('startup-validation.py'))
        return validator
    w=types.SimpleNamespace(HERE=Path('/fixture'),read=read,module=module)
    before=workspace.verify(w,current,contract.RUNTIME_IMAGE)
    assert len(current)==8048 and len(before)==8045
    assert len(workspace.PRIOR_FILES)==10
    for name in workspace.PRIOR_FILES:
        altered=copy.deepcopy(current);altered[name]['sha256']='0'*64
        with pytest.raises(RuntimeError):workspace.verify(w,altered,contract.RUNTIME_IMAGE)
