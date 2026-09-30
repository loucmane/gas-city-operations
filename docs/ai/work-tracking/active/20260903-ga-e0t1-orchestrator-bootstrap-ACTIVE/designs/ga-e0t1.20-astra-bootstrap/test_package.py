import copy
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess

import pytest

HERE = Path(__file__).parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


@pytest.fixture
def prep():
    return module('prepare')


@pytest.fixture
def baseline():
    return json.loads(base64.b64decode(json.loads((HERE/'inputs.json').read_bytes())['config.baseline.json']))


@pytest.fixture
def declared():
    return json.loads(base64.b64decode(json.loads((HERE/'inputs.json').read_bytes())['window-r2-declared-delta.json']))


def test_assembly_exact():
    record = json.loads((HERE/'assembly.json').read_bytes())
    assert record['live_execution'] is False
    for name, digest in record['files'].items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest() == digest


def test_closed_options_and_no_live_execution(prep):
    old = prep.configure(prep.load())
    assert old.ROOT.name == 'ga-e0t1.20-prep-20260927-r1'
    assert old.RECEIPT_SHA.startswith('7185414e')
    assert old.PRIOR_SHA.startswith('7b8472f6')
    assert old._SOURCE_SHA is None


def test_exact_scoped_configuration(prep, baseline, declared):
    before = copy.deepcopy(baseline)
    value = prep.expected_config(baseline, declared)
    assert baseline == before
    selected = [a for a in value['config']['Agents'] if a['Dir'] in ('', 'gascity') and not a['Suspended']]
    assert [(a['Dir'], a['Name']) for a in selected] == [('gascity', 'codex')]
    assert selected[0]['WorkDirRoots'] == [prep.WORK]
    assert value['config']['Workspace']['MaxActiveSessions'] == 1
    assert len(value['config']['Agents']) == len(baseline['config']['Agents']) == 114
    for a in value['config']['Agents']:
        if a['Provider'] == 'codex-managed' and (a['Dir'], a['Name']) != ('gascity', 'codex'):
            assert a['Suspended']


def test_r3_resume_and_mcp_are_narrow(prep, baseline, declared):
    p = prep.expected_config(baseline, declared)['config']['Providers']['codex-managed']
    args = shlex.split(p['ResumeCommand'])
    assert args[-1] == '{{.SessionKey}}'
    assert 'sandbox_workspace_write.writable_roots=["'+prep.WORK+'"]' in args
    assert 'mcp_servers.serena.enabled=false' in args and 'mcp_servers.aegis.enabled=false' in args
    assert p['ArgsAppend'] == prep.MCP_ARGS and p['PrintArgs'] == []


@pytest.mark.parametrize('kind', ['duplicate', 'missing', 'unknown', 'escaped-root'])
def test_bad_declared_patch_refuses(prep, baseline, declared, kind):
    if kind == 'duplicate':
        declared['patches'][-1] = declared['patches'][0]
    elif kind == 'missing':
        declared['patches'].pop()
    elif kind == 'unknown':
        declared['patches'][-1]['name'] = 'invented'
    else:
        target = next(p for p in declared['patches'] if (p['dir'], p['name']) == ('gascity', 'codex'))
        target['work_dir_roots'] = ['/home/loucmane/gas-city-ops/.git']
    with pytest.raises(AssertionError):
        prep.expected_config(baseline, declared)


@pytest.mark.parametrize('path,mode', [(b'.gitattributes', b'100644'), (b'a/.gitattributes', b'100644'),
    (b'.gitmodules', b'100644'), (b'submodule', b'160000'), (b'.codex/rules/rogue.rules', b'100644')])
def test_unsafe_checkout_tree_refuses(path, mode):
    with pytest.raises(AssertionError):
        module('worktree').source_tree(mode+b' blob '+b'a'*40+b'\t'+path+b'\0')


def test_ordinary_checkout_tree_accepted():
    module('worktree').source_tree(b'100644 blob '+b'a'*40+b'\tdesigns/slots.py\0')


def test_wrapper_source_and_no_lifecycle():
    wrappers = list((HERE/'operator').glob('*.sh'))
    assert sorted(p.stem for p in wrappers) == ['PREP', 'WORKTREE']
    for path in wrappers:
        text = path.read_text()
        source = 'prepare.py' if path.stem == 'PREP' else 'worktree.py'
        assert hashlib.sha256((HERE/source).read_bytes()).hexdigest() in text
        assert 'gct-mbg6' not in text and 'gct-e8ex-window' not in text
        assert 'COMMIT=${1:?' in text and '--untracked-files=all' in text
        assert 'source-launch.py' in text
        subprocess.run(['/bin/sh', '-n', str(path)], check=True)


def test_no_product_implementation_and_no_recovery_delete():
    text = (HERE/'worktree.py').read_text()
    assert "'worktree', 'remove'" not in text and "'reset'" not in text
    assert "'--profile', 'unsigned-candidate'" in text
    assert 'worker_launched=False' in text
    assert "cg.no_drivers(ADMIN, WORK)" in text
    assert "git('verify-commit', '--raw', BASE)" in text
    assert text.index("source_tree(git(") < text.index("git('worktree', 'add'")
    assert text.index("'intent.json'") < text.index("git('worktree', 'add'")


def test_rule_read_refuses_wrong_bytes_or_symlink(tmp_path):
    w = module('worktree')
    target = tmp_path/'a'
    target.write_bytes(b'original')
    sha = hashlib.sha256(b'original').hexdigest()
    assert w.read(target, sha) == b'original'
    with pytest.raises(AssertionError):
        w.read(target, '0'*64)
    link = tmp_path/'link'
    link.symlink_to(target)
    with pytest.raises(OSError):
        w.read(link, sha)


def test_create_only_write(tmp_path):
    w = module('worktree')
    target = tmp_path/'record'
    w.write(target, b'first')
    with pytest.raises(FileExistsError):
        w.write(target, b'second')
    assert target.read_bytes() == b'first'
