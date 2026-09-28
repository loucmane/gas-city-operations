"""Exact approved baseline exception only; disposable trees, no host mutation."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import types

import pytest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('builder', HERE/'build.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
PIN = '5b2f7a167ffadb8879d859121b4a4cfbc44e79d1a5615950df0bdf73ed65e8b2'


@pytest.fixture(scope='module')
def source(): return b.assemble(final=True)[1]['common-snapshot-r1.py']


def module(raw, root):
    m = types.ModuleType('common_fixture')
    exec(compile(raw, 'common_fixture', 'exec'), m.__dict__)
    m.COMMON = root
    return m


def fixture(root):
    pins = json.loads((HERE/'common-config-exceptions.json').read_bytes())
    for rel, value in pins.items():
        path = root/rel; path.parent.mkdir(parents=True, exist_ok=True)
        assert value['size'] == 0 and value['sha256'] == hashlib.sha256(b'').hexdigest()
        path.write_bytes(b''); path.chmod(value['mode'])
    return pins


def test_real_manifest_is_exactly_the_approved_44():
    raw = (HERE/'common-config-exceptions.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN
    pins = json.loads(raw)
    assert len(pins) == 44
    for rel, p in pins.items():
        assert rel == 'config.worktree' or (Path(rel).parts[0] == 'worktrees'
            and len(Path(rel).parts) == 3 and Path(rel).name == 'config.worktree')
        assert p == dict(mode=0o664, type=stat.S_IFREG, uid=1000, gid=1000,
                         nlink=1, size=0, sha256=hashlib.sha256(b'').hexdigest())


def test_approved_baseline_passes_with_no_access_time_change(source, tmp_path):
    pins = fixture(tmp_path); m = module(source, tmp_path)
    before = {rel: (tmp_path/rel).stat() for rel in pins}
    image = m.walk()
    assert {rel: image[rel] for rel in pins} == pins
    assert {rel: (tmp_path/rel).stat() for rel in pins} == before


def test_previous_real_guard_reproduces_refusal(tmp_path):
    fixture(tmp_path)
    old = b.git('show', '785618505af3b47b9c2fbae965dd2476bd1a3b05:'+b.NEW+'/common-snapshot-r1.py')
    m = module(old, tmp_path)
    with pytest.raises(AssertionError, match='common Git authority'): m.walk()


@pytest.mark.parametrize('change', ['bytes', 'mode', 'world-write', 'exec', 'missing', 'extra', 'renamed', 'symlink', 'parent-symlink', 'hardlink', 'directory', 'fifo'])
def test_exception_never_admits_changed_missing_or_additional_file(source, tmp_path, change):
    fixture(tmp_path); m = module(source, tmp_path); p = tmp_path/'config.worktree'
    if change == 'bytes': p.write_bytes(b'evil')
    elif change == 'mode': p.chmod(0o644)
    elif change == 'world-write': p.chmod(0o666)
    elif change == 'exec': p.chmod(0o764)
    elif change == 'missing': p.unlink()
    elif change == 'extra':
        q = tmp_path/'extra'; q.write_bytes(b''); q.chmod(0o664)
    elif change == 'renamed': p.rename(tmp_path/'renamed-config.worktree')
    elif change == 'symlink':
        p.unlink(); p.symlink_to(tmp_path/'config-target'); (tmp_path/'config-target').write_bytes(b'')
    elif change == 'parent-symlink':
        q = tmp_path/'worktrees'; q.rename(tmp_path/'original-worktrees'); q.symlink_to(tmp_path/'original-worktrees', target_is_directory=True)
    elif change == 'hardlink': os.link(p, tmp_path/'linked')
    elif change == 'directory': p.unlink(); p.mkdir(mode=0o664)
    elif change == 'fifo': p.unlink(); os.mkfifo(p, 0o664)
    with pytest.raises(AssertionError): m.walk()


@pytest.mark.parametrize('key', ['st_uid', 'st_gid'])
def test_exception_retains_owner_checks(source, tmp_path, monkeypatch, key):
    fixture(tmp_path); m = module(source, tmp_path); p = tmp_path/'config.worktree'
    original = Path.lstat; real = original(p)
    fake = types.SimpleNamespace(**{name: getattr(real, name) for name in dir(real) if name.startswith('st_')})
    setattr(fake, key, 0)
    monkeypatch.setattr(Path, 'lstat', lambda path: fake if path == p else original(path))
    with pytest.raises(AssertionError, match='authority'): m.entry(p)


def test_exception_does_not_admit_same_shape_elsewhere(source, tmp_path):
    fixture(tmp_path); m = module(source, tmp_path)
    other = tmp_path/'outside'; other.mkdir()
    p = other/'config.worktree'; p.write_bytes(b''); p.chmod(0o664)
    with pytest.raises(AssertionError, match='authority'): m.entry(p)


def test_after_comparison_keeps_full_exception_metadata(source, tmp_path):
    pins = fixture(tmp_path); m = module(source, tmp_path)
    before = dict(entries=m.walk(), candidate_branch=m.BASE)
    assert not m.compare(before, copy.deepcopy(before))
    for key in pins['config.worktree']:
        after = copy.deepcopy(before)
        after['entries']['config.worktree'][key] = 'changed'
        assert m.compare(before, after) == ['config.worktree']


def test_no_replay_of_consumed_window_and_exact_original_bind():
    _, out = b.assemble(final=True)
    for name, raw in out.items():
        assert b'/var/tmp/ga-e0t1.20-window-20260927-r1' not in raw, name
    assert b'/var/tmp/ga-e0t1.20-window-20260928-r2' in out['window-base-r11.py']
    assert b.COMPLETED_BIND_EXECUTOR.encode() in out['route-task-r5.py']
    assert b'/var/tmp/ga-e0t1.20-bind-20260927-r1' in out['route-task-r5.py']
