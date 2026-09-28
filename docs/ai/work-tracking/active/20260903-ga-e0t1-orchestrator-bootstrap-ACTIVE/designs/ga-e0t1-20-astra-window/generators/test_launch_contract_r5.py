"""Offline launch-contract tests. No provider, control command or live writes."""
import copy
import hashlib
from pathlib import Path
import stat

import pytest

import launch_contract_r5 as c


def test_only_generated_hook_is_allowed_in_preedit_status():
    c.startup_status(b'?? .codex/hooks.json\0')


@pytest.mark.parametrize('raw', [b'', b'?? .codex/hooks.json\n', b' M .codex/hooks.json\0',
    b'?? .codex/hooks.json\0?? extra\0', b'?? .codex/hooks.json\0?? .codex/hooks.json\0',
    b'?? .codex/../hooks.json\0'])
def test_status_does_not_hide_missing_hook_extra_source_or_staging(raw):
    with pytest.raises(RuntimeError):
        c.startup_status(raw)


def test_preserved_hook_matches_full_exact_contract():
    p = Path(c.WORK)/c.HOOK
    raw = p.read_bytes()
    s = p.lstat()
    row = dict(uid=s.st_uid, gid=s.st_gid, nlink=s.st_nlink, mode=stat.S_IMODE(s.st_mode),
        type=stat.S_IFMT(s.st_mode), size=s.st_size, sha256=hashlib.sha256(raw).hexdigest())
    c.hook_image(raw, row)
    assert b'PreToolUse' not in raw  # No new native allow grant is in this Core hook.
    for key, value in [('mode',0o666), ('type',stat.S_IFLNK), ('uid',0), ('gid',0), ('nlink',2),
                       ('size',1239), ('sha256','0'*64)]:
        with pytest.raises(RuntimeError):
            c.hook_image(raw, dict(row, **{key:value}))
    with pytest.raises(RuntimeError):
        c.hook_image(raw+b'\n', row)


def test_restored_full_tree_not_just_git_clean():
    old = {'source':{'sha256':'old'}}
    runtime = {'.gc':dict(type=stat.S_IFDIR,mode=0o700)}
    current = dict(old, **runtime, **{c.HOOK:c.HOOK_IMAGE})
    c.initial_runtime_image(old,current,runtime)
    for path in current:
        bad = copy.deepcopy(current);bad.pop(path)
        with pytest.raises(RuntimeError):c.initial_runtime_image(old,bad,runtime)
        bad = copy.deepcopy(current);bad[path]['mode']=0o777
        with pytest.raises(RuntimeError):c.initial_runtime_image(old,bad,runtime)
    with pytest.raises(RuntimeError):c.initial_runtime_image(old,dict(current,extra={}),runtime)


def test_only_target_prompt_changes():
    old = {'config':{'Agents':[dict(Dir='gascity',Name='codex',Provider='codex-managed',PromptTemplate='old'),
        dict(Dir='blog',Name='codex',Provider='codex')]},'warnings':[]}
    new = copy.deepcopy(old);new['config']['Agents'][0]['PromptTemplate']='/exact/prompt.md'
    c.config_delta(old,new,'/exact/prompt.md')
    for key,value in [('Provider','claude'),('WorkDir','/tmp'),('OptionDefaults',{'permission':'bypass'})]:
        bad=copy.deepcopy(new);bad['config']['Agents'][0][key]=value
        with pytest.raises(RuntimeError):c.config_delta(old,bad,'/exact/prompt.md')
    bad=copy.deepcopy(new);bad['config']['Agents'][1]['PromptTemplate']='changed'
    with pytest.raises(RuntimeError):c.config_delta(old,bad,'/exact/prompt.md')


def test_actual_prompt_has_exact_body_and_bound_legacy_beacon():
    body='the whole startup contract\n'
    beacon='[city] gascity/codex \u2022 2026-09-28T12:52:11\n\nRun `gc prime` to initialize your context.\n\n'
    suffix='\n\nassigned skills'
    assert c.prompt_body(beacon+body+suffix,body)==hashlib.sha256(suffix.encode()).hexdigest()
    for value in [body,beacon+'Run gc prime\n\n'+body,beacon+body+body,beacon+body.upper()]:
        with pytest.raises(RuntimeError):c.prompt_body(value,body)


def test_one_torn_status_read_retries_but_never_accepts_or_relaxes_resume():
    status=dict(summary=dict(active_sessions=1,running_agents=0),agents=[dict(running=False)])
    census=dict(ok=True,sessions=[],summary=dict(total=0,active=0,suspended=0,closed=0))
    assert c.retry_status(status,census,'city-suspend')
    assert c.retry_status(status,census,'rig-suspend')
    assert not c.retry_status(status,census,'rig-resume')
    for value in [True,1.0,'1',2,None]:
        bad=copy.deepcopy(status);bad['summary']['active_sessions']=value
        assert not c.retry_status(bad,census,'city-suspend')
    bad=copy.deepcopy(census);bad['sessions']=[{}]
    assert not c.retry_status(status,bad,'city-suspend')
    bad=copy.deepcopy(status);bad['agents'][0]['running']=True
    assert not c.retry_status(bad,census,'city-suspend')


def test_control_commands_use_existing_literal_native_prefixes():
    assert c.CLAIM[:5]==(c.GC,'hook','--claim','--drain-ack','--json')
    assert c.SHOW[:4]==(c.GC,'bd','show',c.TASK)
    assert c.UPDATE[:4]==(c.GC,'bd','update',c.TASK)
    assert c.DRAIN[:3]==(c.GC,'runtime','drain-ack')
    for argv in (c.CLAIM,c.SHOW,c.UPDATE,c.DRAIN):
        assert argv.count('--city')==argv.count('--rig')==1
        assert argv[argv.index('--city')+1]==c.CITY
        assert argv[argv.index('--rig')+1]=='gascity'
