"""Tests for the M12 metadata successor (gct-oak5: adopt the Template-candidate codex worklog choice over M11).

  python3 -m pytest -q designs/gct-oak5-activation/m12/test_m12.py

Offline except for read-only reads of the installed M11 pair, the M11 baseline, the live city files and the
sequence 16 reproduction clone. Nothing runs gc or git in a pinned repository.
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
M11 = HERE.parent/'m11'
O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
INSTALLED = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
CORE_SOURCE = '/var/tmp/ga-bebv-build-20260927/repro-source'
RECEIPT = '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, module_name=None, root=HERE):
    path = root/name
    module = types.ModuleType(module_name or path.stem); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def m():
    return load('manifest_candidate.py', 'm12_candidate')


@pytest.fixture(scope='module')
def cap():
    return load('capture_m12.py', 'cap')


@pytest.fixture(scope='module')
def old():
    return json.loads(INSTALLED.read_bytes())


@pytest.fixture(scope='module')
def base(cap):
    raw = cap.REFERENCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == cap.REFERENCE_SHA
    return json.loads(raw)['closure']


def synthetic(m, cap, base):
    """The M11 baseline closure with exactly the admitted changes and the new M12 pin applied."""
    closure = copy.deepcopy(base)
    for path, (_, after) in cap.PIN_CHANGES.items():
        closure['pins'][path] = dict(closure['pins'][path], sha256=after)
    for path, digest, mode in m.NEW_INPUTS:
        closure['pins'].setdefault(path, dict(uid=1000, gid=1000, size=1))
        closure['pins'][path] = dict(closure['pins'][path], sha256=digest, mode=mode)
    return closure


def parents(m, old):
    parent = old['metadata']['parents'][0]
    return [parent] + [dict(parent, path=m.ROOT + '/' + n, entries=[], mode=0o700, uid=1000, gid=1000,
                            device=1, inode=100 + i) for i, n in enumerate(('b', 't'))]


def build(m, old, closure):
    return m.assemble(copy.deepcopy(old), closure, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)


def test_predecessor_and_live_bytes(m):
    assert sha(INSTALLED) == m.OLD_MANIFEST_SHA == sha(O + '/reports/m11/q/manifest.json')
    assert sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json') == m.OLD_RECEIPT_SHA
    assert json.loads(INSTALLED.read_bytes())['release_id'] == m.OLD_RELEASE_ID
    assert sha(m.CITY_TOML) == m.CITY_NEW and sha(m.CITY_OLD_SOURCE) == m.CITY_OLD and sha(m.CITY_OLD_BACKUP) == m.CITY_OLDER
    assert sha(m.BACKUP) == sha(m.ARTIFACT) == m.NEW and os.path.getsize(m.BACKUP) == m.NEW_SIZE
    assert sha('/home/loucmane/gascity/city/.gc/runtime/suspension-state.json') == m.SUSPENSION_SHA
    # The A2 postimage is exactly the reviewed pinned input.
    pins = json.loads((HERE.parent/'codex-choice'/'pins.json').read_bytes())
    assert pins['inputs']['city.toml'] == m.CITY_NEW and pins['city_before'] == m.CITY_OLD


def test_sequence_16_receipt(m):
    assert m.receipt()['sequence'] == 16


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


def test_build_counts_frame_and_identity(m, cap, old, base):
    out, report = build(m, old, synthetic(m, cap, base))
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (692, 50, 23)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR and report['frame']['upper_bound_bytes'] <= 131072
    assert out['release_id'] == m.RELEASE_ID
    assert out['previous_metadata']['manifest_sha256'] == m.OLD_MANIFEST_SHA
    assert out['previous_metadata']['receipt_sha256'] == m.OLD_RECEIPT_SHA
    assert md['evidence'] == m.ROOT + '/t'
    assert [f for f in out['managed_files'] if f['name'] == 'city-config'] == [dict(
        name='city-config', source=m.CITY_SOURCE, destination=m.CITY_TOML, sha256=m.CITY_NEW, mode=0o644,
        previous_sha256=m.CITY_OLD, backup_path=m.CITY_OLD_SOURCE)]


def test_only_reviewed_fields_change(m, cap, old, base):
    out, _ = build(m, old, synthetic(m, cap, base))
    before, after = old['metadata']['inputs'], out['metadata']['inputs']
    assert len(before) == len(after)
    # Exactly two rows change, each in place (row order is preserved).
    changed = sorted(((a['path'], a['sha256']), (b['path'], b['sha256'])) for a, b in zip(before, after) if a != b)
    assert changed == sorted([((m.CITY_TOML, m.CITY_OLD), (m.CITY_TOML, m.CITY_NEW)),
                              ((m.CITY_OLD_BACKUP, m.CITY_OLDER), (m.CITY_SOURCE, m.CITY_NEW))])
    assert all(a['mode'] == b['mode'] == 0o644 and a['name'] == b['name'] == '' for a, b in zip(before, after) if a != b)
    for key in ('trees', 'links', 'runtime', 'protected_trees', 'absent', 'gc_home', 'imports_sha256', 'cache_sha256', 'writer'):
        assert out['metadata'][key] == old['metadata'][key], key
    assert [f for f in out['managed_files'] if f['name'] != 'city-config'] == \
        [f for f in old['managed_files'] if f['name'] != 'city-config']
    assert out['integrity'] == old['integrity']
    top = {k for k in old if old[k] != out[k]}
    assert top == {'release_id', 'metadata', 'managed_files', 'previous_metadata', 'manifest_sha256'}


def test_superseded_row_is_referenced_nowhere_else(m, old):
    referenced = json.dumps({k: v for k, v in old.items() if k != 'metadata'})
    # The M10 source is named only as M11's city-config backup, which M12 replaces.
    assert referenced.count(m.CITY_OLD_BACKUP) == 1
    config = [f for f in old['managed_files'] if f['name'] == 'city-config'][0]
    assert config['backup_path'] == m.CITY_OLD_BACKUP
    assert json.dumps(old['metadata']).count(m.CITY_OLD_BACKUP) == 1


@pytest.mark.parametrize('mutate, reason', [
    (lambda c, m: c['pins'].__setitem__(m.GC, dict(c['pins'][m.GC], sha256='0' * 64)), 'installed image'),
    (lambda c, m: c['pins'].__setitem__(m.BACKUP, dict(c['pins'][m.BACKUP], size=1)), 'previous image backup'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_TOML, dict(c['pins'][m.CITY_TOML], sha256=m.CITY_OLD)),
     'installed city config'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_SOURCE, dict(c['pins'][m.CITY_SOURCE], mode=0o600)), 'successor bytes'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_OLD_SOURCE, dict(c['pins'][m.CITY_OLD_SOURCE], sha256='0' * 64)),
     'city config backup bytes'),
    (lambda c, m: c['trees'].__setitem__(m.CACHE, dict(sha256='0' * 64)), 'unchanged cache'),
    (lambda c, m: c['trees'].__setitem__(m.TEMPLATE + '/.git', dict(sha256='0' * 64)), 'tree differs from the baseline'),
    (lambda c, m: c['links'].pop(next(iter(c['links']))), 'link differs from the baseline'),
])
def test_build_refuses_drift(m, cap, old, base, mutate, reason):
    closure = synthetic(m, cap, base)
    mutate(closure, m)
    with pytest.raises(RuntimeError, match=reason):
        build(m, old, closure)


def test_build_refuses_a_wrong_predecessor(m, cap, old, base):
    for mutate, reason in ((lambda o: o.__setitem__('release_id', 'x'), 'installed release is not M11'),
                           (lambda o: o['integrity']['providers'].pop(), 'exact M11 providers'),
                           (lambda o: o['integrity']['repositories'].pop(), 'exact M11 repositories'),
                           (lambda o: o.__setitem__('backup_path', '/x'), 'exact M11 previous image')):
        trial = copy.deepcopy(old)
        mutate(trial)
        trial = m.b.finalized(trial)
        with pytest.raises(RuntimeError, match=reason):
            m.assemble(trial, synthetic(m, cap, base), base['host'], parents(m, trial), 'a' * 64, 'b' * 64)


def test_build_against_frozen_baseline(m, cap, old):
    path = Path(m.BASELINE_PATH)
    if m.BASELINE_SHA is None or not path.exists():
        pytest.skip('baseline not frozen yet')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.BASELINE_SHA
    record = json.loads(raw)
    assert record['drifts'] == [] and record['m11_baseline_sha256'] == cap.REFERENCE_SHA
    assert sorted(record['pin_changes']) == sorted(cap.PIN_CHANGES)
    closure = record['closure']
    out, report = m.build(INSTALLED.read_bytes(), raw, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)
    assert (len(out['metadata']['inputs']), len(out['metadata']['trees'])) == (692, 50)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR


def test_capture_target(m, cap, old):
    expected, trees, links = cap.target(m, old)
    assert all(expected[p] == dict(sha256=v, mode=mode) for p, v, mode in m.NEW_INPUTS)
    assert m.CITY_OLD_BACKUP not in expected
    assert len(trees) == 50 and len(links) == 23


def test_pin_change_rule(m, cap, base):
    pins = base['pins']
    assert set(cap.PIN_CHANGES) == {m.CITY_TOML, RECEIPT}
    assert cap.PIN_CHANGES[RECEIPT][1] == sha(RECEIPT)
    live = copy.deepcopy(pins)
    for path, (before, after) in cap.PIN_CHANGES.items():
        assert pins[path]['sha256'] == before
        live[path] = dict(live[path], sha256=after, size=live[path]['size'] + 1)
    changed, problems = cap.pin_changes(pins, live, cap.PIN_CHANGES)
    assert problems == [] and sorted(changed) == sorted(cap.PIN_CHANGES)
    for mutate in (lambda v: v.__setitem__(m.CITY_TOML, dict(v[m.CITY_TOML], mode=0o600)),
                   lambda v: v.__setitem__(RECEIPT, dict(v[RECEIPT], sha256='0' * 64)),
                   lambda v: v.__setitem__(m.GC, dict(v[m.GC], sha256='0' * 64))):
        trial = copy.deepcopy(live)
        mutate(trial)
        assert cap.pin_changes(pins, trial, cap.PIN_CHANGES)[1]


def test_capture_differs_from_m11_only_in_reviewed_places(cap):
    ours = (HERE/'capture_m12.py').read_text()
    theirs = (M11/'capture_m11.py').read_text()
    body = lambda text, name: text.split('\ndef %s(' % name)[1].split('\ndef ')[0].split('"""')[2]
    for name in ('pin_changes', 'cache_drift'):
        assert body(ours, name) == body(theirs, name), name
    for name in ('tree_drift',):
        assert body(ours, name) == body(theirs, name), name
    main = ours.split('\ndef main():')[1]
    for fresh in ("'usage: capture_m12.py <candidate sha256>'", "Path(m.O + '/reports/m12-capture')",
                  "schema='gct-oak5.m12-baseline.v1'", 'm11_baseline_sha256=REFERENCE_SHA',
                  "or (status['stdout'] and not repo.get('allow_dirty'))"):
        assert main.count(fresh) == 1, fresh
    theirs_main = theirs.split('\ndef main():')[1]
    assert len(main.splitlines()) == len(theirs_main.splitlines()) + 3


def test_sources_and_rebinding(cap):
    for name in ('source_runtime.py', 'launch.py', 'metadata_executor.py', 'metadata_window.py', 'metadata_closure.py'):
        assert sha(HERE/name) == sha(M11/name), name
    assert cap.RUNTIME_SHA == sha(HERE/'source_runtime.py') and cap.CLOSURE_SHA == sha(HERE/'metadata_closure.py')
    ours = (HERE/'record_review.py').read_text().splitlines()
    theirs = (M11/'record_review.py').read_text().splitlines()
    differing = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs) and len(differing) == 5
    assert all('m12' in a.lower() and 'm11' in b.lower() for a, b in differing)
    extract = (HERE/'operator/gate_extract.py').read_text()
    assert 'reports/m11' not in extract and 'gct-oak5-m11' not in extract and 'designs/gct-oak5-activation/m12' in extract


def test_generator_reproduces_every_file():
    captured = {}
    make = load('make_m12.py')
    make.write = lambda name, text: captured.__setitem__(name, text.encode() if isinstance(text, str) else text) \
        or hashlib.sha256(captured[name]).hexdigest()
    make.main()
    for name, data in captured.items():
        assert (HERE/name).read_bytes() == data, name
    assert len(captured) == 10


def test_prerequisite_paths(m):
    pr = (HERE/'prereqs_m12.py').read_text()
    assert Path(m.CITY_SOURCE).parent == Path(O + '/reports/m12-inputs')
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
