"""Regression against the actual R9 native launch contract; no live execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import types

import pytest

import startup_r10 as candidate
import permissions_baseline_r10 as permissions
import workspace_r10 as workspace

ROLLOUT = Path('/home/loucmane/.codex/sessions/2026/09/29/rollout-2026-09-29T01-28-56-01a0ea59-9af7-7aa1-a484-2797e9b282d1.jsonl')
ROLLOUT_SHA = '429a0c47118e51df7d5d805039a00e4b4b56de6c83544970cd969ab86911a3ad'


def test_negative_probe_respects_actual_cli_never_instruction():
    raw = ROLLOUT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ROLLOUT_SHA
    records = [json.loads(line) for line in raw.splitlines()]
    developer = [r['payload'] for r in records if r.get('type') == 'response_item'
                 and r.get('payload', {}).get('role') == 'developer']
    text = '\n'.join(c.get('text', '') for item in developer for c in item['content'])
    assert 'Do not provide the `sandbox_permissions` for any reason' in text
    prompt = candidate.components()['PRECLAIM-R10.md'].decode()
    transport = prompt.split('```javascript\n', 1)[1].split('\n```', 1)[0]
    assert '"sandbox_permissions"' not in transport


def module(raw):
    m=types.ModuleType('r10_fixture');m.__file__='r10_fixture.py'
    exec(compile(raw,'r10_fixture.py','exec',dont_inherit=True),m.__dict__)
    return m


def test_prompt_delta_only_bindings_and_forbidden_optional_field():
    out=candidate.components()
    old=candidate.frozen('PRECLAIM-R9.md').decode()
    normalized=out['PRECLAIM-R10.md'].decode()
    normalized=normalized.replace(candidate.sha(out['worker-startup-r10.py']),candidate.sha(candidate.frozen('worker-startup-r9.py')))
    normalized=normalized.replace('worker-startup-r10.py','worker-startup-r9.py').replace('/r10','/r9')
    normalized=normalized.replace('ga-e0t1.20 r10','ga-e0t1.20 r9').replace('exact r10 amendment','exact r9 amendment')
    assert normalized==old.replace('"sandbox_permissions":"use_default",','')


def test_probe_has_only_evidence_root_change():
    before=ast.parse(candidate.frozen('worker-startup-r9.py'))
    after=ast.parse(candidate.components()['worker-startup-r10.py'])
    for tree in (before,after):
        nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUT' for t in n.targets)]
        assert len(nodes)==1
        nodes[0].value=ast.Constant(value='same-evidence-root')
    assert ast.dump(before)==ast.dump(after)


def test_existing_validator_already_accepts_implicit_default_transport():
    validator=module(candidate.frozen('startup-validation.py'))
    text=candidate.components()['PRECLAIM-R10.md'].decode()
    transport=text.split('```javascript\n',1)[1].split('\n```',1)[0]
    assert transport in validator.NEGATIVE_SCRIPTS
    explicit=transport.replace('"max_output_tokens":1000','"sandbox_permissions":"use_default","max_output_tokens":1000')
    assert set(validator.NEGATIVE_SCRIPTS)=={transport,transport+'\n',explicit,explicit+'\n'}
    assert 'gpg --version' in transport and 'probe_error' in transport


def evidence():
    prior=module(candidate.frozen('permissions-baseline-r9.py'))
    def load(path,pin):
        raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
        return json.loads(raw)
    return (prior,load(prior.POSTIMAGE,prior.POSTIMAGE_SHA),load(prior.HISTORY,prior.HISTORY_SHA),
            load(permissions.CAPTURE/'images.json',permissions.IMAGES_SHA),
            load(permissions.CAPTURE/'history.json',permissions.HISTORY_SHA),
            bytes.fromhex('0200000001000700ffffffff04000000ffffffff20000000ffffffff'))


def test_exact_post_r9_capture_preserves_history_and_private_permissions():
    args=evidence();saved=copy.deepcopy(args[1:])
    images,history=permissions.expected(*args)
    assert (images,history)==(args[3],args[4])
    assert args[1:]==saved


@pytest.mark.parametrize('kind', ['old_mode','old_owner','old_acl','old_hash','old_transcript',
    'new_mode','new_hash','new_day_acl','new_day_mode','parent_nlink','parent_clock',
    'parent_owner','missing_image','extra_image','extra_history','missing_history','old_history'])
def test_permission_capture_rejects_any_unreviewed_difference(kind):
    args=list(evidence());images=args[3];history=args[4]
    rules='/home/loucmane/.codex/rules/default.rules'
    parent=str(Path(permissions.DAY).parent)
    if kind=='old_mode':images[rules]['stat']['mode']^=0o020
    elif kind=='old_owner':images[rules]['stat']['uid']+=1
    elif kind=='old_acl':images['/home/loucmane/.codex/rules']['xattrs']={}
    elif kind=='old_hash':images[rules]['sha256']='0'*64
    elif kind=='old_transcript':images[args[0].TRANSCRIPT]['sha256']='0'*64
    elif kind=='new_mode':images[permissions.TRANSCRIPT]['stat']['mode']^=0o020
    elif kind=='new_hash':images[permissions.TRANSCRIPT]['sha256']='0'*64
    elif kind=='new_day_acl':images[permissions.DAY]['xattrs']={}
    elif kind=='new_day_mode':images[permissions.DAY]['stat']['mode']^=0o020
    elif kind=='parent_nlink':images[parent]['stat']['nlink']+=1
    elif kind=='parent_clock':images[parent]['stat']['ctime_ns']+=1
    elif kind=='parent_owner':images[parent]['stat']['uid']+=1
    elif kind=='missing_image':images.pop(permissions.TRANSCRIPT)
    elif kind=='extra_image':images['/tmp/unrelated']=copy.deepcopy(images[rules])
    elif kind=='extra_history':history['sessions']['/tmp/unrelated']={}
    elif kind=='missing_history':history['sessions'].pop(permissions.TRANSCRIPT)
    elif kind=='old_history':history['sessions']['/home/loucmane/.codex/sessions']['mtime_ns']+=1
    with pytest.raises(AssertionError):permissions.expected(*args)


def test_preparation_remains_uninstalled_and_consumed_roots_are_not_reused(tmp_path):
    out=candidate.components()
    executor=out['prompt-prep-r10.py'].decode()
    assert candidate.CLOSE in executor and candidate.CLOSE_SHA in executor
    assert "closed_session='ci-g12rt'" in executor
    assert candidate.ROOT in executor and 'typed profiles changed' in executor
    assert "old._verify_host_assets()" in executor
    assert not out['operator/PROMPT-PREP-R10.sh'].startswith(b'#!/bin/sh\necho "COMPLETED OPERATION')
    output=tmp_path/'new'
    candidate.main(str(output))
    manifest=json.loads((output/'prompt-prep-r10-manifest.json').read_bytes())
    assert manifest['worker_launch_included'] is False and manifest['execution_admitted'] is False
    assert all(candidate.sha((output/name).read_bytes())==pin for name,pin in manifest['files'].items())
    with pytest.raises(AssertionError):candidate.main(str(output))


def test_actual_post_r9_workspace_and_every_prior_file_remain_strict():
    v=module(candidate.frozen('startup-validation.py'))
    probe=module(candidate.frozen('worker-startup-r9.py'))
    contract=module(candidate.frozen('contract.py'))
    current=v.workspace_image(Path(contract.WORK),probe.read_regular)
    def read(p,pin):
        raw=probe.read_regular(p);assert candidate.sha(raw)==pin;return raw
    def load(p,pin):
        assert p.name=='prior-startup-validation-r9.py' and pin==candidate.sha(candidate.frozen('startup-validation.py'))
        return v
    w=types.SimpleNamespace(HERE=Path('/fixture'),read=read,module=load)
    before=workspace.verify(w,current,contract.RUNTIME_IMAGE)
    assert len(current)==8045 and len(before)==8042
    assert len(workspace.PRIOR_FILES)==8
    for name in workspace.PRIOR_FILES:
        altered=copy.deepcopy(current)
        altered[name]['sha256']='0'*64
        with pytest.raises(RuntimeError):workspace.verify(w,altered,contract.RUNTIME_IMAGE)
