"""Tests for the M11 metadata successor (gct-oak5: adopt the Template Claude candidate lane activation over M10).

  python3 -m pytest -q designs/gct-oak5-activation/m11/test_m11.py

Offline except for read-only reads of the installed M10 pair, the M10 baseline, the build roots, the canonical
Template files (and one `--version` of the Template wrapper), and the sequence 16 reproduction clone. Nothing runs
git in a repository the capture pins, and nothing runs gc.
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
M10 = HERE.parent.parent/'ga-bebv-deploy'/'m10'
O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
INSTALLED = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
M10_BASELINE = Path(O + '/reports/m10-capture/baseline.json')
CORE_SOURCE = '/var/tmp/ga-bebv-build-20260927/repro-source'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, module_name=None, root=HERE):
    path = root/name
    module = types.ModuleType(module_name or path.stem); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def m():
    return load('manifest_candidate.py', 'm11_candidate')


@pytest.fixture(scope='module')
def cap():
    return load('capture_m11.py', 'cap')


@pytest.fixture(scope='module')
def old():
    return json.loads(INSTALLED.read_bytes())


@pytest.fixture(scope='module')
def base(cap):
    raw = cap.REFERENCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == cap.REFERENCE_SHA
    return json.loads(raw)['closure']


def synthetic(m, cap, base):
    """The M10 baseline closure with exactly the admitted changes and the new M11 pins applied."""
    closure = copy.deepcopy(base)
    for path, (_, after) in cap.PIN_CHANGES.items():
        closure['pins'][path] = dict(closure['pins'][path], sha256=after)
    for path, digest, mode in m.NEW_INPUTS:
        closure['pins'].setdefault(path, dict(uid=1000, gid=1000, size=1))
        closure['pins'][path] = dict(closure['pins'][path], sha256=digest, mode=mode)
    closure['pins'][m.BACKUP]['size'] = m.NEW_SIZE
    for path, (_, after) in m.EXACT_TREES.items():
        closure['trees'][path] = dict(closure['trees'][path], sha256=after)
    for path, digest in m.NEW_TREES:
        closure['trees'][path] = dict(sha256=digest, entries=8, file_bytes=17943)
    return closure


def parents(m, old):
    parent = old['metadata']['parents'][0]
    return [parent] + [dict(parent, path=m.ROOT + '/' + n, entries=[], mode=0o700, uid=1000, gid=1000,
                            device=1, inode=100 + i) for i, n in enumerate(('b', 't'))]


def build(m, old, closure):
    return m.assemble(copy.deepcopy(old), closure, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)


# Predecessor and live bytes.

def test_predecessor_and_live_bytes(m):
    assert sha(INSTALLED) == m.OLD_MANIFEST_SHA == sha(O + '/reports/m10/q/manifest.json')
    assert sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json') == m.OLD_RECEIPT_SHA
    assert json.loads(INSTALLED.read_bytes())['release_id'] == m.OLD_RELEASE_ID
    assert sha(m.CITY_TOML) == m.CITY_NEW and sha(m.CITY_OLD_SOURCE) == m.CITY_OLD
    for path, _, after in m.CHANGED_INPUTS:
        assert sha(path) == after
    assert sha(m.BACKUP) == sha(m.ARTIFACT) == m.NEW and os.path.getsize(m.BACKUP) == m.NEW_SIZE
    assert sha('/home/loucmane/gascity/city/.gc/runtime/suspension-state.json') == m.SUSPENSION_SHA


def test_template_lane_files_and_version(m):
    assert sha(m.WRAPPER) == m.WRAPPER_SHA and sha(m.WRAPPER_LIB) == m.WRAPPER_LIB_SHA
    for path in (m.WRAPPER, m.WRAPPER_LIB):
        shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', m.TEMPLATE, 'show',
                                m.TEMPLATE_COMMIT + ':' + path[len(m.TEMPLATE) + 1:]], capture_output=True, check=True,
                               env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'})
        assert hashlib.sha256(shown.stdout).hexdigest() == sha(path)
    version = subprocess.run([m.WRAPPER, '--version'], capture_output=True, text=True, check=True,
                             env={'HOME': '/home/loucmane', 'PATH': '/home/loucmane/gascity/bin:/usr/bin:/bin'})
    assert version.stdout.strip() == m.WRAPPER_VERSION
    names = sorted(os.listdir(m.POLICY_DIR))
    assert names == ['candidate-control-policy.json', 'candidate-provider.toml', 'core-signing-control-policy.json',
                     'managed-provider.toml', 'signing-provider.toml', 'template-candidate-control-policy.json',
                     'template-candidate-provider.toml']
    assert set(m.REMOVED_INPUTS) < {m.POLICY_DIR + '/' + n for n in names}


def test_sequence_16_receipt(m):
    assert m.receipt()['sequence'] == 16


# Successor rules, counts and the exact delta.

def test_native_successor_rules(m, cap, old, base):
    for name, needles in (('installer.go', ('candidate.PreviousSHA256 != previous.Core.SHA256',
                                            'candidate.Activation.PreviousCommit != previous.Activation.ExpectedCommit',
                                            'candidateFile.PreviousSHA256 != previousFile.SHA256')),
                          ('metadata_adopt.go', ('metadata-only adoption requires all managed artifacts already installed',
                                                 'metadata-only adoption requires existing managed backup'))):
        shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', CORE_SOURCE, 'show',
                                m.COMMIT + ':internal/platforminstall/' + name], capture_output=True, check=True)
        for needle in needles:
            assert needle in shown.stdout.decode(), (name, needle)
    out, _ = build(m, old, synthetic(m, cap, base))
    assert out['previous_sha256'] == old['core']['sha256'] == out['core']['sha256']
    assert out['activation']['previous_commit'] == old['activation']['expected_commit']
    candidate = {f['name']: f for f in out['managed_files']}
    for previous in old['managed_files']:
        now = candidate[previous['name']]
        assert (now['destination'], now['mode'], now['previous_sha256']) == (
            previous['destination'], previous['mode'], previous['sha256']), previous['name']


def test_writer_mounts_trees_like_inputs():
    text = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', CORE_SOURCE, 'show',
                           'f45a626213dc5b8d0b52f097d978cca56e506df0:internal/platforminstall/metadata_sandbox_linux.go'],
                          capture_output=True, check=True).stdout.decode()
    assert 'for _, pin := range append(append([]FilePin{}, launch.Inputs...), launch.Trees...) {' in text
    assert 'args = append(args, "--ro-bind", pin.Path, pin.Path)' in text


def test_build_counts_frame_and_identity(m, cap, old, base):
    out, report = build(m, old, synthetic(m, cap, base))
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (692, 50, 23)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR and report['frame']['upper_bound_bytes'] <= 131072
    assert out['release_id'] == m.RELEASE_ID
    assert out['core'] == old['core'] and md['writer'] == old['metadata']['writer']
    assert out['previous_sha256'] == m.NEW and out['backup_path'] == m.BACKUP
    assert out['activation'] == dict(expected_commit=m.COMMIT, expected_version='dev',
                                     previous_commit=m.COMMIT, previous_version='dev')
    assert out['previous_metadata']['manifest_sha256'] == m.OLD_MANIFEST_SHA
    assert out['previous_metadata']['receipt_sha256'] == m.OLD_RECEIPT_SHA
    assert md['evidence'] == m.ROOT + '/t'
    assert [f for f in out['managed_files'] if f['name'] == 'city-config'] == [dict(
        name='city-config', source=m.CITY_SOURCE, destination=m.CITY_TOML, sha256=m.CITY_NEW, mode=0o644,
        previous_sha256=m.CITY_OLD, backup_path=m.CITY_OLD_SOURCE)]
    assert out['integrity']['providers'][-1] == m.PROVIDER and len(out['integrity']['providers']) == 5


def test_only_reviewed_fields_change(m, cap, old, base):
    out, _ = build(m, old, synthetic(m, cap, base))
    moved = dict(m.SUPERSEDED_INPUTS)
    new = {path: (digest, mode) for path, digest, mode in m.NEW_INPUTS}
    expected = []
    for row in old['metadata']['inputs']:
        if row['path'] in m.REMOVED_INPUTS:
            continue
        row = dict(row)
        row['path'] = moved.get(row['path'], row['path'])
        if row['path'] in new:
            row.update(sha256=new[row['path']][0], mode=new[row['path']][1])
        expected.append(row)
    assert out['metadata']['inputs'] == expected
    changed = [a['path'] for a, b in zip([r for r in old['metadata']['inputs'] if r['path'] not in m.REMOVED_INPUTS],
                                          out['metadata']['inputs']) if a != b]
    # The four moved rows plus city.toml, the registry and the fragment.
    assert len(changed) == 7
    trees_before = {t['path']: t for t in old['metadata']['trees']}
    trees_after = {t['path']: t for t in out['metadata']['trees']}
    assert set(trees_after) - set(trees_before) == {m.POLICY_DIR}
    assert [p for p in trees_before if trees_before[p] != trees_after[p]] == [m.ODB_TEMPLATE]
    for key in ('links', 'runtime', 'protected_trees', 'absent', 'gc_home', 'imports_sha256', 'cache_sha256'):
        assert out['metadata'][key] == old['metadata'][key], key
    assert [f for f in out['managed_files'] if f['name'] != 'city-config'] == \
        [f for f in old['managed_files'] if f['name'] != 'city-config']
    files_before = {f['path']: f for f in old['integrity']['files']}
    files_after = {f['path']: f for f in out['integrity']['files']}
    assert [p for p in files_before if files_before[p] != files_after[p]] == [p for p, _, _ in m.CHANGED_INPUTS]
    assert out['integrity']['providers'][:4] == old['integrity']['providers']
    assert out['integrity']['repositories'] == old['integrity']['repositories']
    top = {k for k in old if old[k] != out[k]}
    assert top == {'release_id', 'metadata', 'activation', 'managed_files', 'previous_metadata', 'manifest_sha256',
                   'previous_sha256', 'backup_path', 'integrity'}


def test_superseded_rows_are_referenced_nowhere_else(m, old):
    referenced = json.dumps({k: v for k, v in old.items() if k != 'metadata'})
    for old_path, _ in m.SUPERSEDED_INPUTS:
        if old_path in (m.OLD_BACKUP, m.CITY_OLD_BACKUP):
            continue  # the predecessor's own backups, which M11 replaces
        assert old_path not in referenced, old_path
    rows = [p for p in old['metadata']['inputs'] if p['path'] in dict(m.SUPERSEDED_INPUTS)]
    assert len(rows) == 4


@pytest.mark.parametrize('mutate, reason', [
    (lambda c, m: c['pins'].__setitem__(m.GC, dict(c['pins'][m.GC], sha256='0' * 64)), 'installed image'),
    (lambda c, m: c['pins'].__setitem__(m.BACKUP, dict(c['pins'][m.BACKUP], size=1)), 'previous image backup'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_TOML, dict(c['pins'][m.CITY_TOML], sha256=m.CITY_OLD)),
     'installed city config'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_SOURCE, dict(c['pins'][m.CITY_SOURCE], mode=0o600)), 'successor bytes'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_OLD_SOURCE, dict(c['pins'][m.CITY_OLD_SOURCE], sha256='0' * 64)),
     'city config backup bytes'),
    (lambda c, m: c['pins'].__setitem__(m.WRAPPER, dict(c['pins'][m.WRAPPER], sha256='0' * 64)), 'successor bytes'),
    (lambda c, m: c['pins'].__setitem__(m.REGISTRY, dict(c['pins'][m.REGISTRY], sha256='0' * 64)), 'activation postimage'),
    (lambda c, m: c['trees'].__setitem__(m.ODB_TEMPLATE, dict(c['trees'][m.ODB_TEMPLATE], sha256=m.EXACT_TREES[m.ODB_TEMPLATE][0])),
     'captured tree'),
    (lambda c, m: c['trees'].__setitem__(m.POLICY_DIR, dict(sha256='0' * 64)), 'new tree'),
    (lambda c, m: c['trees'].__setitem__(m.CACHE, dict(sha256='0' * 64)), 'unchanged cache'),
    (lambda c, m: c['links'].pop(next(iter(c['links']))), 'link differs from the baseline'),
])
def test_build_refuses_drift(m, cap, old, base, mutate, reason):
    closure = synthetic(m, cap, base)
    mutate(closure, m)
    with pytest.raises(RuntimeError, match=reason):
        build(m, old, closure)


def test_build_refuses_a_wrong_predecessor(m, cap, old, base):
    for mutate, reason in ((lambda o: o.__setitem__('release_id', 'x'), 'installed release is not M10'),
                           (lambda o: o['integrity']['providers'].pop(), 'exact M10 provider list'),
                           (lambda o: o.__setitem__('backup_path', '/x'), 'exact M10 previous image')):
        trial = copy.deepcopy(old)
        mutate(trial)
        trial = m.b.finalized(trial)  # a sealed predecessor, so the named check fires
        with pytest.raises(RuntimeError, match=reason):
            m.assemble(trial, synthetic(m, cap, base), base['host'], parents(m, trial), 'a' * 64, 'b' * 64)


def test_build_against_frozen_baseline(m, cap, old):
    path = Path(m.BASELINE_PATH)
    if m.BASELINE_SHA is None or not path.exists():
        pytest.skip('baseline not frozen yet')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.BASELINE_SHA
    record = json.loads(raw)
    assert record['drifts'] == [] and record['m10_baseline_sha256'] == cap.REFERENCE_SHA
    assert sorted(record['pin_changes']) == sorted(cap.PIN_CHANGES)
    closure = record['closure']
    out, report = m.build(INSTALLED.read_bytes(), raw, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)
    assert (len(out['metadata']['inputs']), len(out['metadata']['trees'])) == (692, 50)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR


# The capture.

def test_capture_target(m, cap, old):
    expected, trees, links = cap.target(m, old)
    assert all(expected[p] == dict(sha256=v, mode=mode) for p, v, mode in m.NEW_INPUTS)
    assert not any(p in expected for p in m.REMOVED_INPUTS)
    assert not any(old_path in expected for old_path, _ in m.SUPERSEDED_INPUTS if old_path != m.OLD_BACKUP)
    assert len(trees) == 50 and trees[m.POLICY_DIR] == 0o755 and len(links) == 23


def test_pin_change_rule(m, cap, base):
    pins = base['pins']
    assert set(cap.PIN_CHANGES) == {m.CITY_TOML, m.REGISTRY, m.FRAGMENT,
                                    m.CITY + '/.gc/runtime/provisioning/receipt.json'}
    live = copy.deepcopy(pins)
    for path, (before, after) in cap.PIN_CHANGES.items():
        assert pins[path]['sha256'] == before
        live[path] = dict(live[path], sha256=after, size=live[path]['size'] + 1)
    changed, problems = cap.pin_changes(pins, live, cap.PIN_CHANGES)
    assert problems == [] and sorted(changed) == sorted(cap.PIN_CHANGES)
    for mutate in (lambda v: v.__setitem__(m.CITY_TOML, dict(v[m.CITY_TOML], mode=0o600)),
                   lambda v: v.__setitem__(m.REGISTRY, dict(v[m.REGISTRY], sha256='0' * 64)),
                   lambda v: v.__setitem__(m.GC, dict(v[m.GC], sha256='0' * 64))):
        trial = copy.deepcopy(live)
        mutate(trial)
        assert cap.pin_changes(pins, trial, cap.PIN_CHANGES)[1]


def test_tree_rule(m, cap, base):
    accepted, manifest = base['trees'], {}
    before, after = m.EXACT_TREES[m.ODB_TEMPLATE]
    assert accepted[m.ODB_TEMPLATE]['sha256'] == before
    ok = dict(accepted[m.ODB_TEMPLATE], sha256=after)
    assert not cap.tree_drift(m.ODB_TEMPLATE, ok, accepted, manifest, m.EXACT_TREES, dict(m.NEW_TREES))
    assert cap.tree_drift(m.ODB_TEMPLATE, accepted[m.ODB_TEMPLATE], accepted, manifest, m.EXACT_TREES, dict(m.NEW_TREES))
    new = dict(sha256=m.NEW_TREES[0][1])
    assert not cap.tree_drift(m.POLICY_DIR, new, accepted, manifest, m.EXACT_TREES, dict(m.NEW_TREES))
    assert cap.tree_drift(m.POLICY_DIR, dict(sha256='0' * 64), accepted, manifest, m.EXACT_TREES, dict(m.NEW_TREES))
    other = next(p for p in accepted if p != m.ODB_TEMPLATE)
    assert cap.tree_drift(other, dict(accepted[other], entries=0), accepted, manifest, m.EXACT_TREES, dict(m.NEW_TREES))


def test_capture_differs_from_m10_only_in_reviewed_places(cap):
    ours = (HERE/'capture_m11.py').read_text()
    theirs = (M10/'capture_m10.py').read_text()
    body = lambda text, name: text.split('\ndef %s(' % name)[1].split('\ndef ')[0].split('"""')[2]
    for name in ('pin_changes', 'cache_drift'):
        assert body(ours, name) == body(theirs, name), name
    main = ours.split('\ndef main():')[1]
    for stale in ('SEQ16', 'm10_candidate', 'm10_closure', "reports/m10-capture')", 'sequence-16-pins'):
        assert stale not in main, stale
    for fresh in ("'usage: capture_m11.py <candidate sha256>'", "Path(m.O + '/reports/m11-capture')",
                  "schema='gct-oak5.m11-baseline.v1'", 'm10_baseline_sha256=REFERENCE_SHA',
                  "m.EXACT_TREES, dict(m.NEW_TREES)"):
        assert main.count(fresh) == 1, fresh


# Sources and the prerequisite.

def test_sources_and_rebinding(cap):
    for name in ('source_runtime.py', 'launch.py', 'metadata_executor.py', 'metadata_window.py', 'metadata_closure.py'):
        assert sha(HERE/name) == sha(M10/name), name
    assert cap.RUNTIME_SHA == sha(HERE/'source_runtime.py') and cap.CLOSURE_SHA == sha(HERE/'metadata_closure.py')
    assert cap.PREREQS_SHA == sha(cap.PREREQS) and cap.CAPTURE_M6_SHA == sha(cap.CAPTURE_M6)
    ours = (HERE/'record_review.py').read_text().splitlines()
    theirs = (M10/'record_review.py').read_text().splitlines()
    differing = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs) and len(differing) == 5
    assert all('m11' in a.lower() and 'm10' in b.lower() for a, b in differing)
    extract = (HERE/'operator/gate_extract.py').read_text()
    assert 'reports/m10' not in extract and 'ga-bebv-m10' not in extract and 'designs/gct-oak5-activation/m11' in extract


def test_prerequisite_paths(m):
    pr = (HERE/'prereqs_m11.py').read_text()
    assert Path(m.CITY_SOURCE).parent == Path(O + '/reports/m11-inputs')
    assert 'os.O_EXCL' in pr and "exact(m.CITY_TOML, m.CITY_NEW, 0o644)" in pr


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
