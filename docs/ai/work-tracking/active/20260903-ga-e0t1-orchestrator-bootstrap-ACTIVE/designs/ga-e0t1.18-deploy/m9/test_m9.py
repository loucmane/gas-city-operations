"""Tests for the M9 metadata successor (the candidate provider wrapper pin over M8).

  python3 -m pytest -q designs/ga-e0t1.18-deploy/m9/test_m9.py

Offline except for read-only reads of the installed M8 pair, the frozen M8 baseline, the sequence 15 receipt,
the build roots, the candidate wrapper files (and one `--version` run of the wrapper, which only hashes its
dependencies) and the S1 reproduction clone. Nothing runs git in a repository the capture pins.
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
M8 = HERE.parent/'m8'
INSTALLED = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
M8_BASELINE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m8-capture/baseline.json')
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
    return load('manifest_candidate.py', 'm9_candidate')


@pytest.fixture(scope='module')
def old():
    return json.loads(INSTALLED.read_bytes())


@pytest.fixture(scope='module')
def m8():
    return json.loads(M8_BASELINE.read_bytes())['closure']


def synthetic(m, old, m8):
    """The M8 baseline closure with the reviewed P9 change applied, plus the new M9 pins."""
    c = load('capture_m9.py', 'cap')
    closure = copy.deepcopy(m8)
    for path, (_, after) in c.PIN_CHANGES.items():
        closure['pins'][path] = dict(closure['pins'][path], sha256=after)
    for path, value, mode in m.NEW_INPUTS:
        closure['pins'][path] = dict(sha256=value, mode=mode, uid=1000, gid=1000, size=1)
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
    assert sha(M8_BASELINE) == load('capture_m9.py', 'cap').M8_BASELINE_SHA
    assert sha(m.BACKUP) == sha(m.ARTIFACT) == m.NEW and os.stat(m.BACKUP).st_size == m.NEW_SIZE
    for path, value, mode in m.NEW_INPUTS:
        info = os.lstat(path)
        assert sha(path) == value and (info.st_mode & 0o7777) == mode, path
    for path, value in m.AGENT_FILES:
        assert sha(path) == value, path


def test_the_wrapper_reports_the_pinned_version(m):
    """Core's provider inspection runs `<path> --version` and compares the whole line."""
    run = subprocess.run([m.WRAPPER, '--version'], capture_output=True, text=True, timeout=30,
                         env=dict(PATH='/usr/bin:/bin', HOME=os.environ['HOME']))
    assert run.returncode == 0 and run.stdout.strip() == m.WRAPPER_VERSION
    assert m.PROVIDER['version'] == m.WRAPPER_VERSION and m.PROVIDER['sha256'] == sha(m.WRAPPER)


def test_the_wrapper_is_the_rendered_candidate_provider(m):
    """The claude-candidate provider the activation rendered runs exactly this wrapper."""
    fragment = Path(m.FRAGMENT).read_text()
    assert sha(m.FRAGMENT) == m.FRAGMENT_SHA and m.WRAPPER in fragment
    registry = json.loads(Path(m.REGISTRY).read_bytes())
    assert sha(m.REGISTRY) == m.REGISTRY_SHA and 'operations-candidate-worker' in json.dumps(registry)


def test_core_keys_provider_pins_by_name_and_path(m):
    shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', CORE_SOURCE, 'show',
                            m.COMMIT + ':internal/platforminstall/integrity.go'], capture_output=True, check=True)
    source = shown.stdout.decode()
    assert 'providerKeys[pin.Key()]' in source and 'duplicate integrity provider pin' in source


def test_native_successor_rules(m, old, m8):
    shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', CORE_SOURCE, 'show',
                            m.COMMIT + ':internal/platforminstall/installer.go'], capture_output=True, check=True)
    source = shown.stdout.decode()
    assert 'candidate.PreviousSHA256 != previous.Core.SHA256' in source
    assert 'candidate.Activation.PreviousCommit != previous.Activation.ExpectedCommit' in source
    out, _ = build(m, old, synthetic(m, old, m8))
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


def test_build_counts_frame_and_identity(m, old, m8):
    out, report = build(m, old, synthetic(m, old, m8))
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (694, 49, 23)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR and report['frame']['upper_bound_bytes'] <= 131072
    assert out['release_id'] == m.RELEASE_ID
    assert out['core'] == old['core'] and out['activation'] == old['activation']
    assert out['previous_sha256'] == old['previous_sha256'] == m.NEW and out['backup_path'] == old['backup_path']
    providers = out['integrity']['providers']
    assert providers[:3] == old['integrity']['providers'] and providers[3] == m.PROVIDER
    assert len({(p['name'], p['path']) for p in providers}) == 4
    assert out['previous_metadata']['manifest_sha256'] == m.OLD_MANIFEST_SHA
    assert out['previous_metadata']['receipt_sha256'] == m.OLD_RECEIPT_SHA
    assert md['evidence'] == m.ROOT + '/t'


def test_only_reviewed_fields_change(m, old, m8):
    out, _ = build(m, old, synthetic(m, old, m8))
    before = {p['path']: p for p in old['metadata']['inputs']}
    after = {p['path']: p for p in out['metadata']['inputs']}
    assert set(after) - set(before) == {p for p, _, _ in m.NEW_INPUTS} and set(before) <= set(after)
    assert all(before[k] == after[k] for k in before)
    for key in ('trees', 'links', 'runtime', 'protected_trees', 'absent', 'gc_home', 'imports_sha256',
                'cache_sha256', 'writer'):
        assert out['metadata'][key] == old['metadata'][key], key
    assert out['managed_files'] == old['managed_files']
    assert out['integrity']['files'] == old['integrity']['files']
    assert out['integrity']['repositories'] == old['integrity']['repositories']
    assert out['integrity']['providers'] == old['integrity']['providers'] + [m.PROVIDER]
    top = {k for k in old if old[k] != out[k]}
    assert top == {'release_id', 'metadata', 'integrity', 'previous_metadata', 'manifest_sha256'}


@pytest.mark.parametrize('mutate, reason', [
    (lambda c, m: c['pins'].__setitem__(m.GC, dict(c['pins'][m.GC], sha256='0' * 64)), 'installed image'),
    (lambda c, m: c['pins'].__setitem__(m.BACKUP, dict(c['pins'][m.BACKUP], sha256='0' * 64)), 'previous image backup'),
    (lambda c, m: c['pins'].__setitem__(m.WRAPPER, dict(c['pins'][m.WRAPPER], sha256='0' * 64)), 'wrapper bytes'),
    (lambda c, m: c['pins'].__setitem__(m.WRAPPER_LIB, dict(c['pins'][m.WRAPPER_LIB], mode=0o755)), 'wrapper bytes'),
    (lambda c, m: c['pins'].__setitem__(m.REGISTRY, dict(c['pins'][m.REGISTRY], sha256='0' * 64)),
     'input differs from the baseline: .*rig-permissions.json'),
    (lambda c, m: c['pins'].__setitem__(m.AGENT_FILES[0][0], dict(c['pins'][m.AGENT_FILES[0][0]], sha256='0' * 64)),
     'input differs from the baseline'),
    (lambda c, m: c['trees'].__setitem__(m.CACHE, dict(sha256='0' * 64)), 'unchanged cache'),
    (lambda c, m: c['pins'].__setitem__('/usr/lib/x86_64-linux-gnu/libc.so.6',
                                        dict(c['pins']['/usr/lib/x86_64-linux-gnu/libc.so.6'], sha256='0' * 64)),
     'input differs from the baseline'),
    (lambda c, m: c['links'].pop(next(iter(c['links']))), 'link differs from the baseline'),
])
def test_build_refuses_drift(m, old, m8, mutate, reason):
    closure = synthetic(m, old, m8)
    mutate(closure, m)
    with pytest.raises(RuntimeError, match=reason):
        build(m, old, closure)


def _signing(o):
    return [p for p in o['integrity']['providers'] if p['name'] == 'claude'][0]


@pytest.mark.parametrize('mutate, reason', [
    (lambda o, m: o.__setitem__('previous_sha256', 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'),
     'previous image'),
    (lambda o, m: o['activation'].__setitem__('previous_commit', '9faeabc2892d8c7133111e13ad55af66790a2ac6'),
     'activation'),
    (lambda o, m: o.__setitem__('release_id', 'other'), 'not M8'),
    (lambda o, m: o['integrity']['providers'].append(copy.deepcopy(m.PROVIDER)), 'provider list'),
    (lambda o, m: _signing(o).__setitem__('sha256', '0' * 64), 'signing provider'),
    (lambda o, m: o['metadata']['inputs'].append(dict(name='', path=m.WRAPPER, sha256=m.WRAPPER_SHA, mode=0o755)),
     'wrapper input already pinned'),
])
def test_build_refuses_wrong_predecessor(m, old, m8, mutate, reason):
    changed = copy.deepcopy(old)
    mutate(changed, m)
    changed = m.b.finalized(changed)
    with pytest.raises(RuntimeError, match=reason):
        build(m, changed, synthetic(m, old, m8))


def test_build_against_frozen_baseline(m, old):
    path = Path(m.BASELINE_PATH)
    if m.BASELINE_SHA is None or not path.exists():
        pytest.skip('baseline not frozen yet')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.BASELINE_SHA
    record = json.loads(raw)
    assert record['drifts'] == [] and record['m8_baseline_sha256'] == load('capture_m9.py', 'cap').M8_BASELINE_SHA
    closure = record['closure']
    out, report = m.build(INSTALLED.read_bytes(), raw, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)
    assert (len(out['metadata']['inputs']), len(out['metadata']['trees'])) == (694, 49)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR


def test_capture_target(m, old):
    c = load('capture_m9.py', 'cap')
    expected, trees, links = c.target(m, old)
    assert all(expected[p] == dict(sha256=v, mode=mode) for p, v, mode in m.NEW_INPUTS)
    assert expected[m.REGISTRY]['sha256'] == m.REGISTRY_SHA and expected[m.BACKUP] == dict(sha256=m.NEW, mode=0o755)
    assert len(trees) == 49 and len(links) == 23


def test_pin_change_rule(m8):
    c = load('capture_m9.py', 'cap')
    pins = m8['pins']
    assert set(c.PIN_CHANGES) == {c.RECEIPT_PATH} and pins[c.RECEIPT_PATH]['sha256'] == c.PIN_CHANGES[c.RECEIPT_PATH][0]
    assert sha(c.RECEIPT_PATH) == c.PIN_CHANGES[c.RECEIPT_PATH][1]
    live = copy.deepcopy(pins)
    for path, (_, after) in c.PIN_CHANGES.items():
        live[path] = dict(live[path], sha256=after, size=live[path]['size'] + 1)
    changed, problems = c.pin_changes(pins, live, c.PIN_CHANGES)
    assert problems == [] and sorted(changed) == sorted(c.PIN_CHANGES)
    receipt = c.RECEIPT_PATH
    for mutate in (lambda v: v.__setitem__(receipt, dict(v[receipt], mode=0o644)),
                   lambda v: v.__setitem__(receipt, dict(v[receipt], sha256='0' * 64)),
                   lambda v: v.__setitem__('/usr/lib/x86_64-linux-gnu/libc.so.6',
                                           dict(v['/usr/lib/x86_64-linux-gnu/libc.so.6'], sha256='0' * 64))):
        trial = copy.deepcopy(live)
        mutate(trial)
        assert c.pin_changes(pins, trial, c.PIN_CHANGES)[1]
    assert receipt in c.pin_changes(pins, copy.deepcopy(pins), c.PIN_CHANGES)[1]  # an allowed change must happen


def test_cache_rule(m8):
    c = load('capture_m9.py', 'cap')
    accepted = m8['cache']
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
        assert sha(HERE/name) == sha(S3/name) == sha(M8/name), name
    c = load('capture_m9.py', 'cap')
    assert c.RUNTIME_SHA == sha(HERE/'source_runtime.py')
    assert c.CLOSURE_SHA == sha(HERE/'metadata_closure.py')
    assert c.PREREQS_SHA == sha(c.PREREQS) and c.CAPTURE_M6_SHA == sha(c.CAPTURE_M6)
    ours = (HERE/'record_review.py').read_text().splitlines()
    theirs = (M8/'record_review.py').read_text().splitlines()
    differing = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs) and len(differing) == 5
    assert all('m9' in a.lower() and 'm8' in b.lower() for a, b in differing)


def test_capture_differs_from_m8_only_in_reviewed_places():
    """main() is M8's with every successor name moved by one; the three pure rules keep M8's bodies."""
    ours = (HERE/'capture_m9.py').read_text()
    theirs = (M8/'capture_m8.py').read_text()
    assert ours.split('\ndef main():')[1].replace('m9', 'm8').replace('M9', 'M8') == \
        theirs.split('\ndef main():')[1].replace('m7', 'm8').replace('M7', 'M8')
    for name in ('pin_changes', 'cache_drift', 'tree_drift'):
        body = lambda text: text.split('\ndef %s(' % name)[1].split('\ndef ')[0].split('"""')[2]
        assert body(ours) == body(theirs), name


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
