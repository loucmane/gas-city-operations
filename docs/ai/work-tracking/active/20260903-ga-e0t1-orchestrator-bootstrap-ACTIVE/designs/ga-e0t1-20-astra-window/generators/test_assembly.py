"""Offline assembly and real generated-function tests; no lifecycle command."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import types

import pytest

HERE=Path(__file__).parent


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def built():
    g=load(HERE/'build.py','assembler')
    old,new=g.assemble()
    return g,old,new


def test_deterministic_and_original_input_unchanged(built):
    g,old,new=built
    assert g.assemble()==(old,new)
    assert len(new)==50
    assert 'operator/WORKTREE.sh' not in new and 'operator/PREP.sh' not in new


def test_all_wrappers_are_inert_drafts_and_parse(built,tmp_path):
    g,old,new=built
    for name,raw in new.items():
        if not name.endswith('.sh'):continue
        path=tmp_path/Path(name).name;path.write_bytes(raw)
        assert subprocess.run(['/bin/sh','-n',str(path)]).returncode==0
        result=subprocess.run(['/bin/sh',str(path)],capture_output=True)
        assert result.returncode==125 and result.stdout==b''
        assert b'DRAFT ONLY' in result.stderr


def test_every_wrapper_hash_matches_generated_source(built):
    g,old,new=built
    for name,raw in new.items():
        if not name.endswith('.sh'):continue
        text=raw.decode()
        for script,var in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"',text):
            [pin]=re.findall(r'^%s=([0-9a-f]{64})$'%var,text,re.M)
            assert pin==hashlib.sha256(new[script]).hexdigest(),(name,script)


def test_no_old_mutation_target_or_consumed_window_survives(built):
    g,old,new=built
    for name,raw in new.items():
        if name in ('task-own-fields.json','test_contract.py'):continue
        text=raw.decode()
        assert 'gct-mbg6' not in text,name
        assert 'gas-city-template/codex' not in text,name
        assert not re.search(r'/var/tmp/ga-e0t1\.20-[a-z%_-]+-20260926-r[123]',text),name
        assert not re.search(r"['\"]--rig['\"], ?['\"]gas-city-template['\"]",text),name


def test_no_inherited_stranded_acceptance_or_approval(built):
    g,old,new=built
    text=new['window-base-r11.py'].decode()
    assert 'STRANDED_RECORDS' not in text and 'STRANDED_HOLD' not in text
    assert 'CACHE_PINNED_NS = None' in text
    assert "'unreviewed stranded lifecycle'" in text
    assert text.count("historical disposition is not authority for this window")==5


def test_startup_contract_is_bound_before_route(built):
    g,old,new=built
    text=new['bind-task-r5.py'].decode()
    assert "argv += ['--append-notes',note]" in text
    assert "if key not in ('metadata','notes','updated_at'):" in text
    assert "(ROOT/'sandbox-negative').mkdir(mode=0o700)" in text
    assert "w.contract().validate_task(after,'bound')" in text
    note=new['contract.py'].decode()
    for name in ('WORKER-BRIEF.md','worker-startup.py'):
        assert hashlib.sha256(new[name]).hexdigest() in note
    assert 'DRAFT worker brief is not yet bound' not in note
    assert 'No product edit until the coordinator verifies startup' in note


def test_real_generated_status_matcher_uses_census(built):
    g,old,new=built
    m=types.ModuleType('generated_base');m.__file__='window-base-r11.py'
    exec(compile(new['window-base-r11.py'],m.__file__,'exec',dont_inherit=True),m.__dict__)
    c=load(HERE/'contract.py','contract_for_base');m.contract=lambda:c
    expected=dict(city=dict(suspended=True),rigs={r:dict(suspended=True) for r in ('gascity','gas-city-template','hpfetcher','blog')})
    value=dict(ok=True,city_path=str(m.CITY),running=True,controller=dict(running=True,pid=2800348),
        rigs=[dict(name=r,suspended=True) for r in expected['rigs']],suspended=True,
        agents=[],summary=dict(running_agents=0,active_sessions=0),health=dict(signals=['city_suspended','no_agents_running']))
    assert m.suspension_status_matches(value,expected,census=dict(ok=True,sessions=[]),action='rig-suspend')
    with pytest.raises(RuntimeError):
        m.suspension_status_matches(value,expected,census=dict(ok=False,sessions=[]),action='rig-suspend')
    value['controller']['pid']=1
    with pytest.raises(RuntimeError):
        m.suspension_status_matches(value,expected,census=dict(ok=True,sessions=[]),action='rig-suspend')


def test_original_policy_is_byte_identical(built):
    g,old,new=built
    assert old['cache-atime-policy-r1.py']==new['cache-atime-policy-r1.py']
    assert old['route-chain-r1.py']==new['route-chain-r1.py']


def test_watch_applies_existing_bounded_accounting(built):
    g,old,new=built
    text=new['watch-r11.py'].decode()
    assert 'policy.bounds(baseline' in text and 'w.account_read_times(dict(directories=a)' in text
    assert 'w.directory_preservation(a, z)' in text
    assert text.index('w.account_read_times(dict(directories=a)') < text.index('w.directory_preservation(a, z)')


def test_all_generated_python_compiles(built):
    for name,raw in built[2].items():
        if name.endswith('.py'):ast.parse(raw,filename=name)


def test_source_generator_never_invokes_lifecycle():
    g=load(HERE/'build.py','readonly_generator')
    calls=[n for n in ast.walk(ast.parse((HERE/'build.py').read_bytes())) if isinstance(n,ast.Call)
           and isinstance(n.func,ast.Attribute) and n.func.attr=='run']
    assert len(calls)==1
    assert 'git' in ast.unparse(calls[0])
