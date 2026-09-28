"""The whole corrected startup path, without worker or lifecycle execution."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

import startup_r5 as r


@pytest.fixture(scope='module')
def built():
    return r.components()


def test_generation_is_deterministic_and_consumed_r4_unchanged(built):
    assert r.components()==built
    assert r.frozen()==built[0]
    assert b'recovery-only' not in built[0]['window-base-r11.py']


def test_old_real_defects_reproduced_and_all_three_consumers_corrected(built):
    old,new=built
    c=r.source_module(new['contract.py'],'r5_contract')
    full=b'?? .codex/hooks.json\0'+b''.join(b'!! '+p.encode()+b'\0'
        for p in sorted(set(c.RULES)|(c.RUNTIME_FILES-{r.lc.HOOK})))
    oldc=r.source_module(old['contract.py'],'old_contract')
    with pytest.raises(RuntimeError):oldc.validate_rule_status(full)
    c.validate_rule_status(full)
    new_status=full+b' M '+c.SOURCE_PATHS[0].encode()+b'\0!! .gc/worker-evidence/ga-e0t1.20/report.json\0'
    with pytest.raises(RuntimeError):oldc.candidate_status(new_status)
    accepted=c.candidate_status(new_status)
    assert r.lc.HOOK in accepted['runtime']
    assert c.RUNTIME_IMAGE[r.lc.HOOK]==r.lc.HOOK_IMAGE
    assert b"r.stdout == b''" in old['worker-startup.py']
    assert b'verified_hook().startup_status(r.stdout)' in new['worker-startup.py']
    assert b"'unexpected project hook'" in old['startup-release.py']
    assert b'probe.verified_hook()' in new['startup-release.py']
    assert b'candidate generated hook differs' in new['candidate-inspect.py']


@pytest.mark.parametrize('extra',[b'?? surprise\0', b' M AGENTS.md\0', b'A  staged.py\0',
    b'?? .codex/other.json\0',b'!! .codex/other.rules\0'])
def test_new_inventory_still_refuses_every_unreviewed_file(built,extra):
    c=r.source_module(built[1]['contract.py'],'r5_inventory')
    full=b'?? .codex/hooks.json\0'+b''.join(b'!! '+p.encode()+b'\0'
        for p in sorted(set(c.RULES)|(c.RUNTIME_FILES-{r.lc.HOOK})))
    with pytest.raises(RuntimeError):c.validate_rule_status(full+extra)
    with pytest.raises(RuntimeError):c.candidate_status(full+b' M '+c.SOURCE_PATHS[0].encode()+
        b'\0!! .gc/worker-evidence/ga-e0t1.20/report.json\0'+extra)


def test_amendment_is_exact_append_and_keeps_old_digest_history(built):
    old,new=built
    a=json.loads(new['startup-amendment-r5.json'])
    oldc=r.source_module(old['contract.py'],'old_task')
    c=r.source_module(new['contract.py'],'new_task')
    assert a['before_note']==oldc.BOUND_NOTE
    assert c.BOUND_NOTE==a['after_note']==a['before_note']+'\n'+a['append_note']
    assert '7c97d1fcfae3b87ddf76a54a449c34232befb0096b77efde07eb8758b6382de3' in c.BOUND_NOTE
    assert a['worker_probe_sha256']==r.sha(new['worker-startup.py'])
    assert a['prompt_sha256']==r.sha(new['PRECLAIM-R5.md'])
    for name in ('TASK','PARENT','TARGET','PROVIDER','WORK','BASE','BRANCH','DESCRIPTION','ACCEPTANCE','RULES','DEFAULT_RULES','SOURCE_PATHS'):
        assert getattr(c,name)==getattr(oldc,name)


def test_prompt_arrives_before_claim_without_new_permissions(built):
    old,new=built
    body=new['PRECLAIM-R5.md'].decode()
    for argv in (r.lc.CLAIM,r.lc.SHOW,r.lc.UPDATE,r.lc.DRAIN):assert ' '.join(argv) in body
    assert r.sha(new['worker-startup.py']) in body
    assert 'Do not run the\ngeneric gc prime' in body
    assert 'Do not prepend env, change flag order, use bare gc' in body
    assert 'Then WAIT' in body and 'SOURCE RELEASE:' in body
    assert body.endswith(old['WORKER-BRIEF.md'].decode().split('## Phase two:')[1])
    release=new['startup-release.py'].decode()
    assert r.sha(new['PRECLAIM-R5.md']) in release
    assert r.sha(new['skills-suffix-r5.txt']) in release
    assert 'helper.prompt_body(argv[-1],body)' in release


def test_native_rule_matrix_no_control_commands_execute(built):
    # This is an offline policy query, not a claim that the live client loaded it.
    base=['/home/loucmane/gascity/bin/codex','execpolicy','check']
    for path in ['/home/loucmane/.codex/rules/default.rules',
        r.lc.WORK+'/.codex/rules/gas-city-native-control.rules',
        r.lc.WORK+'/.codex/rules/window-restrictions.rules']:
        base+=['--rules',path]
    for argv,decision in [(r.lc.CLAIM,'allow'),(r.lc.SHOW,'allow'),(r.lc.UPDATE+('synthetic-only',),'allow'),
        (r.lc.DRAIN,'allow'),(('gpg','--version'),'forbidden')]:
        done=subprocess.run(base+['--',*argv],capture_output=True,check=True)
        assert json.loads(done.stdout)['decision']==decision


def test_prep_config_changes_only_one_prompt_and_never_installs(built,tmp_path):
    new=built[1]
    for name in ('PRECLAIM-R5.md','launch-contract-r5.py'):(tmp_path/name).write_bytes(new[name])
    prep=r.source_module(new['prompt-prep-r5.py'],'prompt_prep')
    prep.HERE=tmp_path;prep.PROMPT=tmp_path/'PRECLAIM-R5.md'
    prep.ROOT=tmp_path/'uninstalled-output'
    configured=prep.configure()
    assert configured.ROOT==prep.ROOT
    before=Path('/var/tmp/ga-e0t1.20-prep-20260927-r1')
    city=(before/'city.baseline.toml').read_bytes()
    baseline=json.loads((before/'config.baseline.json').read_bytes())
    orders=json.loads((before/'orders.baseline.json').read_bytes())
    changed,*args=configured.build_overlay(city,baseline,orders)
    prior=(before/'city.isolated.toml').read_bytes()
    added=('prompt_template = '+json.dumps(str(prep.PROMPT))+'\n').encode()
    assert changed.count(added)==1 and changed.replace(added,b'')==prior
    import tomllib
    tomllib.loads(changed.decode())
    expected=configured.expected_config(baseline,*args[2:])
    old=json.loads((before/'config.isolated.json').read_bytes())
    r.lc.config_delta(old,expected,str(prep.PROMPT))
    assert configured.receipt_image.__name__=='image'
    assert not configured.ROOT.exists()


@pytest.mark.parametrize('drift',[None,'name','profile','revision'])
def test_prep_keeps_explicit_profile_and_native_revision_checks(built,tmp_path,drift):
    new=built[1]
    for name in ('PRECLAIM-R5.md','launch-contract-r5.py'):(tmp_path/name).write_bytes(new[name])
    prep=r.source_module(new['prompt-prep-r5.py'],'receipt_contract')
    prep.HERE=tmp_path;prep.PROMPT=tmp_path/'PRECLAIM-R5.md'
    configured=prep.configure()
    before=json.loads(Path('/var/tmp/ga-e0t1.20-prep-20260927-r1/receipt.before.json').read_bytes())
    final=copy.deepcopy(before);final['permission_revision']='synthetic-new-revision'
    if drift=='name':before['profiles'][0]['name']='unreviewed-profile'
    if drift=='profile':final['profiles'][0]['synthetic_extra']=True
    if drift=='revision':final['permission_revision']='wrong-revision'
    calls=[]
    def native(*args):
        calls.append(args)
        return json.dumps(final).encode()
    cells=dict(zip(configured.receipt_image.__code__.co_freevars,configured.receipt_image.__closure__))
    cells['native_receipt_image'].cell_contents=native
    def read(path,pin=None):
        if path==configured.RECEIPT:return json.dumps(before).encode()
        assert path==Path(r.PREP)/'composition.after.json'
        return json.dumps({'permission_revision':'synthetic-new-revision'}).encode()
    configured.read=read
    if drift:
        with pytest.raises(AssertionError):configured.receipt_image('owned-child-fixture')
    else:
        assert json.loads(configured.receipt_image('owned-child-fixture'))==final
    assert len(calls)==(0 if drift=='name' else 1)


def test_wrappers_have_only_new_preparation_and_bound_executor(built,tmp_path):
    out=built[1]
    wrappers=[x for x in out if x.endswith('.sh')]
    assert wrappers==['operator/PROMPT-PREP-R5.sh']
    wrapper=out[wrappers[0]]
    p=tmp_path/'prep.sh';p.write_bytes(wrapper)
    assert subprocess.run(['/bin/sh','-n',str(p)]).returncode==0
    assert r.sha(out['prompt-prep-r5.py']).encode() in wrapper
    assert r.PREP.encode() in wrapper and b'ROOT' not in wrapper
    assert b'rig resume' not in wrapper and b'gc sling' not in wrapper


def test_create_only_draft_never_overwrites(built,tmp_path):
    out=tmp_path/'out';r.main(str(out))
    manifest=json.loads((out/'components.json').read_bytes())
    assert manifest['execution_admitted'] is False and manifest['worker_launch_included'] is False
    for name,pin in manifest['files'].items():assert r.sha((out/name).read_bytes())==pin
    with pytest.raises(AssertionError):r.main(str(out))
