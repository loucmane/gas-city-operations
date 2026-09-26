"""Tests for the ga-e0t1.18 S3 metadata successor package (M7).

  python3 -m pytest -q designs/ga-e0t1.18-deploy/s3/test_s3.py

Offline except for read-only reads of the installed M6 pair, the sequence 15 accepted observation, the
sequence 15 receipt, the build roots and the S1 reproduction clone at deefb98b. Nothing runs git in a
repository the capture pins, so the suite may run inside the quiescent window.
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
M6 = HERE.parent.parent/'ga-e0t1.15-deploy/s3'
INSTALLED = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
SEQ15 = Path('/var/tmp/ga-e0t1.18-seq15-20260926/postflight2.json')
# The S1 reproduction clone of deefb98b, never the Core rig: the capture pins the rig's Git directory and the
# quiescence rule forbids any git there until restore-accepted (review A of 7d86f441, should_fix 2).
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
    return load('manifest_candidate.py', 'm7_candidate')


@pytest.fixture(scope='module')
def old():
    return json.loads(INSTALLED.read_bytes())


@pytest.fixture(scope='module')
def seq15():
    return json.loads(SEQ15.read_bytes())['closure']


def synthetic(m, old, seq15):
    """A closure shaped like capture_m7.py's: the M6 pins and trees, overlaid by the sequence 15 closure."""
    md = old['metadata']
    pins = {p['path']: dict(sha256=p['sha256'], mode=p['mode'], size=0) for p in md['inputs']}
    pins.update(copy.deepcopy(seq15['pins']))
    pins[m.ARTIFACT] = dict(sha256=m.NEW, mode=0o755, size=m.NEW_SIZE)
    pins[m.BACKUP] = dict(sha256=m.OLD, mode=0o755, size=m.OLD_SIZE)
    trees = {p['path']: dict(sha256=p['sha256']) for p in md['trees']}
    trees.update(copy.deepcopy(seq15['trees']))
    links = {p['path']: p['target'] for p in md['links']}
    return dict(host=copy.deepcopy(seq15['host']), pins=pins, trees=trees, links=links)


def parents(m, old):
    base = old['metadata']['parents'][0]
    return [base] + [dict(base, path=m.ROOT + '/' + n, entries=[], mode=0o700, uid=1000, gid=1000,
                          device=1, inode=100 + i) for i, n in enumerate(('b', 't'))]


def build(m, old, closure):
    return m.assemble(copy.deepcopy(old), closure, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)


def test_predecessor_and_evidence_bytes(m):
    assert sha(INSTALLED) == m.OLD_MANIFEST_SHA
    assert sha(m.OLD_ROOT + '/q/manifest.json') == m.OLD_MANIFEST_SHA
    assert sha(INSTALLED.parent/'install-receipt.json') == m.OLD_RECEIPT_SHA
    assert sha(SEQ15) == load('capture_m7.py', 'cap').SEQ15_SHA
    assert sha(m.CITY_CONFIG_BACKUP) == m.CITY_CONFIG_SHA
    for path, value, size in ((m.ARTIFACT, m.NEW, m.NEW_SIZE), (m.BACKUP, m.OLD, m.OLD_SIZE), (m.GC, m.NEW, m.NEW_SIZE)):
        assert sha(path) == value and os.stat(path).st_size == size, path


def test_receipt_is_sequence_15(m):
    value = m.receipt()
    assert value['sequence'] == 15 and value['source']['commit'] == m.COMMIT
    evidence = json.loads(SEQ15.read_bytes())['receipt']
    assert evidence['pin']['sha256'] == m.RECEIPT_SHA and evidence['receipt']['request_id'] == m.REQUEST


def test_build_commit_is_the_version_commit(m):
    version = json.loads(Path('/var/tmp/ga-e0t1.18-build-20260926/version-a.stdout').read_bytes())
    assert version['commit'] == m.COMMIT and version['version'] == m.VERSION


def test_native_successor_rules(m, old, seq15):
    """Core installer.go validateSuccessor at deefb98b, restated for the fields M7 touches."""
    shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', CORE_SOURCE, 'show',
                            m.COMMIT + ':internal/platforminstall/installer.go'], capture_output=True, check=True)
    source = shown.stdout.decode()
    assert 'candidate.PreviousSHA256 != previous.Core.SHA256' in source
    assert 'candidate.Activation.PreviousCommit != previous.Activation.ExpectedCommit' in source
    out, _ = build(m, old, synthetic(m, old, seq15))
    assert out['release_id'] != old['release_id'] and out['previous_sha256'] == old['core']['sha256']
    assert (out['city_path'], out['core']['destination'], out['core']['mode'], out['receipt_path']) == (
        old['city_path'], old['core']['destination'], old['core']['mode'], old['receipt_path'])
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


def test_build_counts_frame_and_identity(m, old, seq15):
    out, report = build(m, old, synthetic(m, old, seq15))
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (689, 49, 23)
    assert report['frame']['remaining_bytes'] > 2048 and report['frame']['upper_bound_bytes'] <= 131072
    assert out['release_id'] == m.RELEASE_ID
    assert out['core'] == dict(old['core'], source=m.ARTIFACT, sha256=m.NEW)
    assert out['activation'] == dict(expected_commit=m.COMMIT, expected_version='dev',
                                     previous_commit=m.OLD_COMMIT, previous_version='dev')
    assert out['previous_sha256'] == m.OLD and out['backup_path'] == m.BACKUP
    assert md['writer']['sha256'] == m.NEW
    assert md['inputs'][-2:] == [dict(name='', path=m.ARTIFACT, sha256=m.NEW, mode=0o755),
                                 dict(name='', path=m.BACKUP, sha256=m.OLD, mode=0o755)]
    assert md['cache_sha256'] == m.CACHE_SHA
    assert out['integrity'] == old['integrity']
    assert out['previous_metadata'] == dict(
        manifest_sha256=m.OLD_MANIFEST_SHA, manifest_backup_path=m.ROOT + '/b/install-manifest.before.json',
        receipt_sha256=m.OLD_RECEIPT_SHA, receipt_backup_path=m.ROOT + '/b/install-receipt.before.json')
    assert md['evidence'] == m.ROOT + '/t'


def test_only_reviewed_fields_change(m, old, seq15):
    out, _ = build(m, old, synthetic(m, old, seq15))
    before = {p['path']: p for p in old['metadata']['inputs']}
    after = {p['path']: p for p in out['metadata']['inputs']}
    assert set(after) - set(before) == {m.ARTIFACT, m.BACKUP} and set(before) <= set(after)
    assert {k for k in before if before[k] != after[k]} == {m.GC}
    trees_before = {p['path']: p for p in old['metadata']['trees']}
    trees_after = {p['path']: p for p in out['metadata']['trees']}
    assert {k for k in trees_before if trees_before[k] != trees_after[k]} == {m.ODB}
    assert out['metadata']['links'] == old['metadata']['links']
    for key in ('runtime', 'protected_trees', 'absent', 'gc_home', 'imports_sha256', 'cache_sha256'):
        assert out['metadata'][key] == old['metadata'][key], key
    assert out['managed_files'] == old['managed_files']
    top = {k for k in old if old[k] != out[k]}
    assert top == {'release_id', 'core', 'previous_sha256', 'backup_path', 'activation', 'metadata',
                   'previous_metadata', 'manifest_sha256'}  # the last is the finalized self digest
    changed_md = {k for k in old['metadata'] if old['metadata'][k] != out['metadata'][k]}
    assert changed_md <= {'writer', 'inputs', 'trees', 'host', 'namespaces', 'transaction', 'attempt', 'parents',
                          'evidence', 'preimages'}


@pytest.mark.parametrize('mutate, reason', [
    (lambda c, m: c['pins'].__setitem__(m.GC, dict(c['pins'][m.GC], sha256='0' * 64)), 'installed sequence 15'),
    (lambda c, m: c['pins'].__setitem__(m.ARTIFACT, dict(c['pins'][m.ARTIFACT], mode=0o644)), 'build source'),
    (lambda c, m: c['pins'].__setitem__(m.BACKUP, dict(c['pins'][m.BACKUP], sha256=m.NEW)), 'previous image backup'),
    (lambda c, m: c['trees'].__setitem__(m.ODB, dict(sha256=m.EXACT_TREES[m.ODB][0])), 'sequence 15 accepted tree'),
    (lambda c, m: c['trees'].__setitem__(m.CACHE, dict(sha256='0' * 64)), 'unchanged cache'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_CONFIG_BACKUP, dict(c['pins'][m.CITY_CONFIG_BACKUP], sha256='0' * 64)),
     'city config'),
    (lambda c, m: c['pins'].__setitem__('/usr/lib/x86_64-linux-gnu/libc.so.6',
                                        dict(c['pins']['/usr/lib/x86_64-linux-gnu/libc.so.6'], sha256='0' * 64)),
     'input differs from the baseline'),
    (lambda c, m: c['trees'].__setitem__(m.O + '/reports/r5/r', dict(sha256='0' * 64)), 'tree differs from the baseline'),
    (lambda c, m: c['links'].pop(next(iter(c['links']))), 'link differs from the baseline'),
])
def test_build_refuses_drift(m, old, seq15, mutate, reason):
    closure = synthetic(m, old, seq15)
    mutate(closure, m)
    with pytest.raises(RuntimeError, match=reason):
        build(m, old, closure)


@pytest.mark.parametrize('field, value, reason', [
    (('activation', 'expected_commit'), 'deefb98b2aed07875df31351d081fbac195cb1cd', 'activation'),
    (('previous_sha256',), 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489', 'previous image'),
    (('core', 'source'), '/var/tmp/ga-e0t1.18-build-20260926/gc-a', 'Core predecessor'),
    (('release_id',), 'other', 'not M6'),
])
def test_build_refuses_wrong_predecessor(m, old, seq15, field, value, reason):
    changed = copy.deepcopy(old)
    target = changed
    for key in field[:-1]:
        target = target[key]
    target[field[-1]] = value
    changed = m.b.finalized(changed)
    with pytest.raises(RuntimeError, match=reason):
        build(m, changed, synthetic(m, old, seq15))


def test_build_refuses_reused_transaction(m, old, seq15):
    closure = synthetic(m, old, seq15)
    with pytest.raises(RuntimeError, match='fresh distinct'):
        m.assemble(copy.deepcopy(old), closure, closure['host'], parents(m, old),
                   old['metadata']['transaction'], 'b' * 64)


def test_build_against_frozen_baseline(m, old):
    path = Path(m.BASELINE_PATH)
    if m.BASELINE_SHA is None or not path.exists():
        pytest.skip('baseline not frozen yet')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.BASELINE_SHA
    record = json.loads(raw)
    assert record['drifts'] == [] and record['seq15_observation_sha256'] == load('capture_m7.py', 'cap').SEQ15_SHA
    closure = record['closure']
    out, report = m.build(INSTALLED.read_bytes(), raw, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (689, 49, 23)
    assert report['frame']['remaining_bytes'] > 2048


def test_watchdog_image_is_the_survivor(m, seq15):
    assert m.WATCHDOG_IMAGE == m.OLDER != m.OLD
    assert seq15['scope']['dolt_members']['watchdog_image'] == 'deleted-old'
    ours = (HERE/'metadata_closure.py').read_text().splitlines()
    theirs = (M6/'metadata_closure.py').read_text().splitlines()
    assert [line for line in theirs if line not in ours] == ['    install_policy(o, s, candidate.OLD)']
    added = [line for line in ours if line not in theirs]
    assert added[-1] == '    install_policy(o, s, candidate.WATCHDOG_IMAGE)' and len(added) == 3
    assert all(line.lstrip().startswith('#') for line in added[:-1])


def test_capture_target(m, old):
    c = load('capture_m7.py', 'cap')
    expected, trees, links = c.target(m, old)
    assert expected[m.GC] == dict(sha256=m.NEW, mode=0o755) and expected[m.ARTIFACT] == dict(sha256=m.NEW, mode=0o755)
    assert expected[m.BACKUP] == dict(sha256=m.OLD, mode=0o755)
    assert expected[m.CITY_CONFIG_BACKUP] == dict(sha256=m.CITY_CONFIG_SHA, mode=0o644)
    assert len(trees) == 49 and len(links) == 23


def test_tree_rule(m, old, seq15):
    c = load('capture_m7.py', 'cap')
    manifest_trees = {t['path']: t['sha256'] for t in old['metadata']['trees']}
    covered = next(iter(seq15['trees']))
    assert not c.tree_drift(covered, dict(seq15['trees'][covered]), seq15['trees'], manifest_trees)
    assert c.tree_drift(covered, dict(seq15['trees'][covered], entries=-1), seq15['trees'], manifest_trees)
    outside = next(p for p in manifest_trees if p not in seq15['trees'])
    assert not c.tree_drift(outside, dict(sha256=manifest_trees[outside]), seq15['trees'], manifest_trees)
    assert c.tree_drift(outside, dict(sha256='0' * 64), seq15['trees'], manifest_trees)


def test_cache_rule(seq15):
    c = load('capture_m7.py', 'cap')
    accepted = seq15['cache']
    assert c.cache_drift(copy.deepcopy(accepted), accepted) == ([], [])
    git_key = next(k for k in accepted['inventory'] if k.split('/')[1:2] == ['.git'])
    live = copy.deepcopy(accepted)
    live['inventory'][git_key].update(mtime_ns=1, ctime_ns=2)
    assert c.cache_drift(live, accepted) == ([dict(path=git_key, fields=['ctime_ns', 'mtime_ns'])], [])
    for mutate in (lambda v: v['inventory'][git_key].update(size=10**9),
                   lambda v: v['inventory'][next(k for k in v['inventory'] if '/' in k and '.git' not in k.split('/'))]
                   .update(mtime_ns=1),
                   lambda v: v['inventory'].pop(git_key),
                   lambda v: v.update(sha256='0' * 64)):
        trial = copy.deepcopy(accepted)
        mutate(trial)
        assert c.cache_drift(trial, accepted)[1]


def test_window_is_access_time_neutral():
    w = load('metadata_window.py', 'w')
    start = dict(boot='00000000-0000-0000-0000-000000000000', mono=10**12, boot_time=10**12, wall=10**18, span=1)
    cache = dict(inventory={'.': dict(mtime_ns=5, ctime_ns=6)})
    window = w.build(start, cache, 'a' * 64)
    assert window['max_atime'] == 1 and window['renewal'] == start['wall'] + 86400 * w.SECOND
    with pytest.raises(RuntimeError, match='access-time neutral'):
        w.build(start, dict(inventory={'.': dict(mtime_ns=5, ctime_ns=6, atime_ns=7)}), 'a' * 64)


def test_source_pins():
    for name in ('source_runtime.py', 'launch.py', 'metadata_executor.py', 'metadata_window.py'):
        assert sha(HERE/name) == sha(M6/name), name
    c = load('capture_m7.py', 'cap')
    assert c.RUNTIME_SHA == sha(HERE/'source_runtime.py')
    assert c.CLOSURE_SHA == sha(HERE/'metadata_closure.py')
    assert c.PREREQS_SHA == sha(c.PREREQS) and c.CAPTURE_M6_SHA == sha(c.CAPTURE_M6)
    ours = (HERE/'record_review.py').read_text().splitlines()
    theirs = (M6/'record_review.py').read_text().splitlines()
    differing = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs) and len(differing) == 5
    assert all('m7' in a.lower() and 'm6' in b.lower() for a, b in differing)


def test_executor_source_inventory():
    """source-pins.json names the launcher's six sources at their committed bytes, in the loader's authority."""
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
