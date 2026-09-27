"""Fixture tests for intake_template.py (no live paths; fixtures live in pytest's tmp_path)."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import types

import pytest

HERE = Path(__file__).parent
ENV = dict(HOME='/nonexistent', PATH='/usr/bin:/bin', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
           GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')


@pytest.fixture
def it(monkeypatch):
    m = types.ModuleType('intake_template')
    m.__file__ = str(HERE/'intake_template.py')
    exec(compile((HERE/'intake_template.py').read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
    m.FORBIDDEN_ROOTS = (Path('/nonexistent-forbidden'),)
    return m


def sh(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, env=ENV, check=True, capture_output=True).stdout


@pytest.fixture
def repo(tmp_path):
    src = tmp_path/'src'
    src.mkdir()
    sh(src, 'init', '-q', '-b', 'main')
    (src/'.gitignore').write_text('__pycache__/\n.gc/\n*.log\n')
    (src/'a.txt').write_text('a\n')
    (src/'bin').mkdir()
    (src/'bin/tool').write_text('#!/bin/sh\n')
    os.chmod(src/'bin/tool', 0o755)
    (src/'gone.txt').write_text('x\n')
    os.symlink('a.txt', src/'current')
    sh(src, 'add', '-A')
    sh(src, 'commit', '-q', '-m', 'base')
    base = sh(src, 'rev-parse', 'HEAD').decode().strip()
    bare = tmp_path/'base.git'
    sh(tmp_path, 'clone', '-q', '--bare', '--no-local', str(src), str(bare))
    work = tmp_path/'work'
    sh(tmp_path, 'clone', '-q', '--no-local', str(src), str(work))
    subprocess.run(['rm', '-rf', str(work/'.git')], check=True)
    (work/'.git').write_text('gitdir: /elsewhere\n')
    return types.SimpleNamespace(tmp=tmp_path, src=src, bare=bare, work=work, base=base)


def run_export(it, r, capsys, name='out'):
    it.export(r.work, r.bare, r.base, r.tmp/name)
    return json.loads(capsys.readouterr().out)


def test_export_tree_stage_round_trip(it, repo, capsys):
    (repo.work/'a.txt').write_text('changed\n')
    os.chmod(repo.work/'bin/tool', 0o644)
    (repo.work/'new.py').write_text('print(1)\n')
    (repo.work/'gone.txt').unlink()
    (repo.work/'bin/__pycache__').mkdir()
    (repo.work/'bin/__pycache__/x.pyc').write_bytes(b'\0')
    (repo.work/'.gc').mkdir()
    (repo.work/'.gc/settings.json').write_text('{}')
    (repo.work/'.codex').mkdir()
    (repo.work/'.codex/hooks.json').write_text('{}')
    (repo.work/'.agents/skills').mkdir(parents=True)
    os.symlink('/somewhere', repo.work/'.agents/skills/core.x')
    out = run_export(it, repo, capsys)
    manifest = json.loads((repo.tmp/'out/manifest.json').read_bytes())
    assert {(e['path'], e['status'], e['mode']) for e in manifest['entries']} == {
        ('a.txt', 'M', '100644'), ('bin/tool', 'M', '100644'), ('new.py', 'A', '100644')}
    assert manifest['deleted'] == ['gone.txt']
    assert {e['path'] for e in manifest['excluded']} == {'.codex/hooks.json', '.agents/skills/core.x'}
    assert manifest['ignored_count'] == 2
    it.tree_cmd(repo.bare, repo.base, repo.tmp/'out', out['manifest_sha256'])
    t = json.loads(capsys.readouterr().out)
    # The same change made with plain git in a checkout gives the same tree.
    check = repo.tmp/'check'
    sh(repo.tmp, 'clone', '-q', '--no-local', str(repo.src), str(check))
    (check/'a.txt').write_text('changed\n')
    os.chmod(check/'bin/tool', 0o644)
    (check/'new.py').write_text('print(1)\n')
    (check/'gone.txt').unlink()
    sh(check, 'add', '-A')
    assert sh(check, 'write-tree').decode().strip() == t['tree']
    sign = repo.tmp/'sign'
    sh(repo.tmp, 'clone', '-q', '--no-local', str(repo.src), str(sign))
    it.stage(sign, repo.base, repo.tmp/'out', t['tree_json_sha256'])
    assert json.loads(capsys.readouterr().out)['tree'] == t['tree']


@pytest.mark.parametrize('case', ['new-link', 'hardlink', 'fifo', 'gitattributes', 'gitignore', 'tracked-link'])
def test_export_refuses(it, repo, capsys, case):
    w = repo.work
    if case == 'new-link':
        os.symlink('a.txt', w/'b')
    elif case == 'hardlink':
        (w/'n.txt').write_text('n\n')
        os.link(w/'n.txt', w/'m.txt')
    elif case == 'fifo':
        os.mkfifo(w/'pipe')
    elif case == 'gitattributes':
        (w/'.gitattributes').write_text('* filter=x\n')
    elif case == 'gitignore':
        (w/'.gitignore').write_text('*\n')
    elif case == 'tracked-link':
        os.unlink(w/'current')
        os.symlink('gone.txt', w/'current')
    with pytest.raises(it.Refusal):
        run_export(it, repo, capsys)


def test_self_ignoring_cache_marker_is_applied(it, repo, capsys):
    (repo.work/'.pytest_cache/v').mkdir(parents=True)
    (repo.work/'.pytest_cache/.gitignore').write_text('# Created by pytest automatically.\n*\n')
    (repo.work/'.pytest_cache/v/nodeids').write_text('[]')
    (repo.work/'new.py').write_text('print(1)\n')
    run_export(it, repo, capsys)
    manifest = json.loads((repo.tmp/'out/manifest.json').read_bytes())
    assert [e['path'] for e in manifest['entries']] == ['new.py']
    assert list(manifest['nested_ignore']) == ['.pytest_cache/.gitignore']


def test_nested_gitignore_hiding_other_files_refuses(it, repo, capsys):
    (repo.work/'pkg').mkdir()
    (repo.work/'pkg/.gitignore').write_text('secret.py\n')
    (repo.work/'pkg/secret.py').write_text('x\n')
    with pytest.raises(it.Refusal):
        run_export(it, repo, capsys)


def test_tree_refuses_altered_export(it, repo, capsys):
    (repo.work/'new.py').write_text('print(1)\n')
    out = run_export(it, repo, capsys)
    (repo.tmp/'out/files/new.py').write_text('print(2)\n')
    with pytest.raises(it.Refusal):
        it.tree_cmd(repo.bare, repo.base, repo.tmp/'out', out['manifest_sha256'])


def test_stage_refuses_a_different_tree(it, repo, capsys):
    (repo.work/'new.py').write_text('print(1)\n')
    out = run_export(it, repo, capsys)
    it.tree_cmd(repo.bare, repo.base, repo.tmp/'out', out['manifest_sha256'])
    t = json.loads(capsys.readouterr().out)
    sign = repo.tmp/'sign'
    sh(repo.tmp, 'clone', '-q', '--no-local', str(repo.src), str(sign))
    (sign/'extra.txt').write_text('x\n')
    with pytest.raises(it.Refusal):
        it.stage(sign, repo.base, repo.tmp/'out', t['tree_json_sha256'])


def test_outputs_refuse_forbidden_roots(tmp_path):
    m = types.ModuleType('intake_template')
    m.__file__ = str(HERE/'intake_template.py')
    exec(compile((HERE/'intake_template.py').read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
    for bad in ('/tmp/x', '/var/tmp/x', '/home/loucmane/gas-city-template-worktrees/x',
                '/home/loucmane/vaults/main/GasCity/x', '/home/loucmane/gas-city-template/x'):
        with pytest.raises(m.Refusal):
            m.outside(bad)
