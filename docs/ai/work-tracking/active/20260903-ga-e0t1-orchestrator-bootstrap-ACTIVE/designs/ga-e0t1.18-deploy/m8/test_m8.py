"""Tests for the M8 metadata successor (the Operations candidate lane adoption over M7).

  python3 -m pytest -q designs/ga-e0t1.18-deploy/m8/test_m8.py

Offline except for read-only reads of the installed M7 pair, the frozen M7 baseline, the sequence 15 receipt,
the build roots, the live city files M8 adopts and the S1 reproduction clone. Nothing runs git in a repository
the capture pins.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import types

import pytest

HERE = Path(__file__).parent
S3 = HERE.parent/'s3'
INSTALLED = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
M7_BASELINE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m7-capture/baseline.json')
CORE_SOURCE = '/var/tmp/ga-e0t1.18-build-20260926/repro-source'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, module_name=None, root=HERE):
    path = root/name
    module = types.ModuleType(module_name or path.stem); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def m():
    return load('manifest_candidate.py', 'm8_candidate')


@pytest.fixture(scope='module')
def old():
    return json.loads(INSTALLED.read_bytes())


@pytest.fixture(scope='module')
def m7():
    return json.loads(M7_BASELINE.read_bytes())['closure']


def synthetic(m, old, m7):
    """The M7 baseline closure with the three reviewed changes applied, plus the new M8 pins."""
    c = load('capture_m8.py', 'cap')
    closure = copy.deepcopy(m7)
    for path, (_, after) in c.PIN_CHANGES.items():
        closure['pins'][path] = dict(closure['pins'][path], sha256=after)
    closure['pins'][m.BACKUP] = dict(closure['pins'][m.ARTIFACT])
    for path, value in m.AGENT_FILES:
        closure['pins'][path] = dict(sha256=value, mode=0o644, uid=1000, gid=1000, size=1)
    return closure


def parents(m, old):
    base = old['metadata']['parents'][0]
    return [base] + [dict(base, path=m.ROOT + '/' + n, entries=[], mode=0o700, uid=1000, gid=1000,
                          device=1, inode=100 + i) for i, n in enumerate(('b', 't'))]


def build(m, old, closure):
    return m.assemble(copy.deepcopy(old), closure, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)


def test_predecessor_and_live_bytes(m):
    assert sha(INSTALLED) == m.OLD_MANIFEST_SHA
    assert sha(m.OLD_ROOT + '/q/manifest.json') == m.OLD_MANIFEST_SHA
    assert sha(INSTALLED.parent/'install-receipt.json') == m.OLD_RECEIPT_SHA
    assert sha(M7_BASELINE) == load('capture_m8.py', 'cap').M7_BASELINE_SHA
    assert sha(m.BACKUP) == sha(m.ARTIFACT) == m.NEW and os.stat(m.BACKUP).st_size == m.NEW_SIZE
    for path, _, after in m.CHANGED_INPUTS:
        assert sha(path) == after, path
    for path, value in m.AGENT_FILES:
        assert sha(path) == value, path


def test_the_pinned_agent_definition_is_suspended_and_unscoped(m):
    import tomllib
    agent = tomllib.loads(Path(m.AGENT_FILES[0][0]).read_text())
    assert agent['dir'] == 'gascity' and agent['suspended'] is True and 'scope' not in agent
    assert agent['max_active_sessions'] == 1


def test_native_successor_rules(m, old, m7):
    shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', CORE_SOURCE, 'show',
                            m.COMMIT + ':internal/platforminstall/installer.go'], capture_output=True, check=True)
    source = shown.stdout.decode()
    assert 'candidate.PreviousSHA256 != previous.Core.SHA256' in source
    assert 'candidate.Activation.PreviousCommit != previous.Activation.ExpectedCommit' in source
    out, _ = build(m, old, synthetic(m, old, m7))
    assert out['release_id'] != old['release_id'] and out['previous_sha256'] == old['core']['sha256']
    assert out['activation']['previous_commit'] == old['activation']['expected_commit']
    assert out['activation']['previous_version'] == old['activation']['expected_version']
    candidate = {f['name']: f for f in out['managed_files']}
    for previous in old['managed_files']:
        now = candidate[previous['name']]
        assert (now['destination'], now['mode'], now['previous_sha256']) == (
            previous['destination'], previous['mode'], previous['sha256']), previous['name']
    paths = [out['core']['source'], out['core']['destination'], out['backup_path'], out['receipt_path'],
             out['city_path'] + '/.gc/platform/install-manifest.json',
             out['previous_metadata']['manifest_backup_path'], out['previous_metadata']['receipt_backup_path']]
    paths += [f[k] for f in out['managed_files'] for k in ('source', 'destination', 'backup_path')]
    assert len(paths) == len(set(paths))


def test_build_counts_frame_and_identity(m, old, m7):
    out, report = build(m, old, synthetic(m, old, m7))
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (692, 49, 23)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR and report['frame']['upper_bound_bytes'] <= 131072
    assert out['release_id'] == m.RELEASE_ID
    assert out['core'] == old['core']
    assert out['activation'] == dict(old['activation'], previous_commit=m.COMMIT)
    assert out['previous_sha256'] == m.NEW and out['backup_path'] == m.BACKUP
    files = {f['path']: f['sha256'] for f in out['integrity']['files']}
    for path, _, after in m.CHANGED_INPUTS:
        assert files[path] == after and [p for p in md['inputs'] if p['path'] == path][0]['sha256'] == after
    assert out['previous_metadata']['manifest_sha256'] == m.OLD_MANIFEST_SHA
    assert md['evidence'] == m.ROOT + '/t'


def test_only_reviewed_fields_change(m, old, m7):
    out, _ = build(m, old, synthetic(m, old, m7))
    before = {p['path']: p for p in old['metadata']['inputs']}
    after = {p['path']: p for p in out['metadata']['inputs']}
    assert set(after) - set(before) == {m.BACKUP} | {p for p, _ in m.AGENT_FILES} and set(before) <= set(after)
    assert {k for k in before if before[k] != after[k]} == {p for p, _, _ in m.CHANGED_INPUTS}
    assert out['metadata']['trees'] == old['metadata']['trees']
    assert out['metadata']['links'] == old['metadata']['links']
    for key in ('runtime', 'protected_trees', 'absent', 'gc_home', 'imports_sha256', 'cache_sha256', 'writer'):
        assert out['metadata'][key] == old['metadata'][key], key
    assert out['managed_files'] == old['managed_files']
    assert out['integrity']['providers'] == old['integrity']['providers']
    assert out['integrity']['repositories'] == old['integrity']['repositories']
    changed_files = [f['path'] for f, g in zip(old['integrity']['files'], out['integrity']['files']) if f != g]
    assert sorted(changed_files) == sorted(p for p, _, _ in m.CHANGED_INPUTS)
    top = {k for k in old if old[k] != out[k]}
    assert top == {'release_id', 'previous_sha256', 'backup_path', 'activation', 'metadata', 'integrity',
                   'previous_metadata', 'manifest_sha256'}


@pytest.mark.parametrize('mutate, reason', [
    (lambda c, m: c['pins'].__setitem__(m.GC, dict(c['pins'][m.GC], sha256='0' * 64)), 'installed image'),
    (lambda c, m: c['pins'].__setitem__(m.BACKUP, dict(c['pins'][m.BACKUP], sha256='0' * 64)), 'previous image backup'),
    (lambda c, m: c['pins'].__setitem__(m.REGISTRY, dict(c['pins'][m.REGISTRY], sha256='0' * 64)), 'activation postimage'),
    (lambda c, m: c['pins'].__setitem__(m.AGENT_FILES[0][0], dict(c['pins'][m.AGENT_FILES[0][0]], sha256='0' * 64)),
     'agent file bytes'),
    (lambda c, m: c['trees'].__setitem__(m.CACHE, dict(sha256='0' * 64)), 'unchanged cache'),
    (lambda c, m: c['pins'].__setitem__('/usr/lib/x86_64-linux-gnu/libc.so.6',
                                        dict(c['pins']['/usr/lib/x86_64-linux-gnu/libc.so.6'], sha256='0' * 64)),
     'input differs from the baseline'),
    (lambda c, m: c['links'].pop(next(iter(c['links']))), 'link differs from the baseline'),
])
def test_build_refuses_drift(m, old, m7, mutate, reason):
    closure = synthetic(m, old, m7)
    mutate(closure, m)
    with pytest.raises(RuntimeError, match=reason):
        build(m, old, closure)


@pytest.mark.parametrize('field, value, reason', [
    (('previous_sha256',), 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b', 'previous image'),
    (('activation', 'previous_commit'), 'deefb98b2aed07875df31351d081fbac195cb1cd', 'activation'),
    (('release_id',), 'other', 'not M7'),
])
def test_build_refuses_wrong_predecessor(m, old, m7, field, value, reason):
    changed = copy.deepcopy(old)
    target = changed
    for key in field[:-1]:
        target = target[key]
    target[field[-1]] = value
    changed = m.b.finalized(changed)
    with pytest.raises(RuntimeError, match=reason):
        build(m, changed, synthetic(m, old, m7))


def test_build_against_frozen_baseline(m, old):
    path = Path(m.BASELINE_PATH)
    if m.BASELINE_SHA is None or not path.exists():
        pytest.skip('baseline not frozen yet')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.BASELINE_SHA
    record = json.loads(raw)
    assert record['drifts'] == [] and record['m7_baseline_sha256'] == load('capture_m8.py', 'cap').M7_BASELINE_SHA
    closure = record['closure']
    out, report = m.build(INSTALLED.read_bytes(), raw, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)
    assert (len(out['metadata']['inputs']), len(out['metadata']['trees'])) == (692, 49)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR


def test_capture_target(m, old):
    c = load('capture_m8.py', 'cap')
    expected, trees, links = c.target(m, old)
    for path, _, after in m.CHANGED_INPUTS:
        assert expected[path]['sha256'] == after
    assert expected[m.BACKUP] == dict(sha256=m.NEW, mode=0o755)
    assert all(expected[p] == dict(sha256=v, mode=0o644) for p, v in m.AGENT_FILES)
    assert len(trees) == 49 and len(links) == 23


def test_pin_change_rule(m7):
    c = load('capture_m8.py', 'cap')
    pins = m7['pins']
    live = copy.deepcopy(pins)
    for path, (_, after) in c.PIN_CHANGES.items():
        live[path] = dict(live[path], sha256=after, size=live[path]['size'] + 1)
    changed, problems = c.pin_changes(pins, live, c.PIN_CHANGES)
    assert problems == [] and sorted(changed) == sorted(c.PIN_CHANGES)
    registry = next(p for p in c.PIN_CHANGES if p.endswith('rig-permissions.json'))
    for mutate in (lambda v: v.__setitem__(registry, dict(v[registry], mode=0o600)),
                   lambda v: v.__setitem__(registry, dict(v[registry], sha256='0' * 64)),
                   lambda v: v.__setitem__('/usr/lib/x86_64-linux-gnu/libc.so.6',
                                           dict(v['/usr/lib/x86_64-linux-gnu/libc.so.6'], sha256='0' * 64))):
        trial = copy.deepcopy(live)
        mutate(trial)
        assert c.pin_changes(pins, trial, c.PIN_CHANGES)[1]
    assert registry in c.pin_changes(pins, copy.deepcopy(pins), c.PIN_CHANGES)[1]  # an allowed change must happen


def test_cache_rule(m7):
    c = load('capture_m8.py', 'cap')
    accepted = m7['cache']
    assert c.cache_drift(copy.deepcopy(accepted), accepted) == ([], [])
    git_key = next(k for k in accepted['inventory'] if k.split('/')[1:2] == ['.git'])
    live = copy.deepcopy(accepted)
    live['inventory'][git_key].update(mtime_ns=1, ctime_ns=2)
    assert c.cache_drift(live, accepted)[1] == []
    trial = copy.deepcopy(accepted)
    trial['inventory'][git_key].update(size=10**9)
    assert c.cache_drift(trial, accepted)[1]


def test_source_pins():
    for name in ('source_runtime.py', 'launch.py', 'metadata_executor.py', 'metadata_window.py', 'metadata_closure.py'):
        assert sha(HERE/name) == sha(S3/name), name
    c = load('capture_m8.py', 'cap')
    assert c.RUNTIME_SHA == sha(HERE/'source_runtime.py')
    assert c.CLOSURE_SHA == sha(HERE/'metadata_closure.py')
    assert c.PREREQS_SHA == sha(c.PREREQS) and c.CAPTURE_M6_SHA == sha(c.CAPTURE_M6)
    ours = (HERE/'record_review.py').read_text().splitlines()
    theirs = (S3/'record_review.py').read_text().splitlines()
    differing = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs) and len(differing) == 5
    assert all('m8' in a.lower() and 'm7' in b.lower() for a, b in differing)


def test_executor_source_inventory():
    import stat as _stat
    path = HERE/'source-pins.json'
    if not path.exists():
        pytest.skip('source pins are written at the binding step')
    pins = json.loads(path.read_bytes())
    launch = load('launch.py', 'launch')
    assert set(pins) == launch.NAMES
    for name, digest in pins.items():
        info = os.lstat(HERE/name)
        assert sha(HERE/name) == digest, name
        assert (_stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid, info.st_nlink) == (0o644, 1000, 1000, 1), name
