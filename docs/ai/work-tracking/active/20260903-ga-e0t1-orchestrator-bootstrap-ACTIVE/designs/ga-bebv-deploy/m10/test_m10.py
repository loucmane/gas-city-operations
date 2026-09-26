"""Tests for the M10 metadata successor (ga-bebv S3: the sequence 16 Core and the replace-mode city.toml over M9).

  python3 -m pytest -q designs/ga-bebv-deploy/m10/test_m10.py

Offline except for read-only reads of the installed M9 pair, the sequence 16 accepted observation and receipt,
the M9 baseline, the build roots, the live city.toml with its managed fragments and agent files, and the S1
reproduction clone. Nothing runs git in a repository the capture pins, and nothing runs gc.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib
import types

import pytest

HERE = Path(__file__).parent
M9 = HERE.parent.parent/'ga-e0t1.18-deploy'/'m9'
INSTALLED = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
M9_BASELINE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m9-capture/baseline.json')
CORE_SOURCE = '/var/tmp/ga-bebv-build-20260927/repro-source'
UNSAFE = ('dangerously', 'bypassPermissions', '--yolo', 'danger-full-access')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, module_name=None, root=HERE):
    path = root/name
    module = types.ModuleType(module_name or path.stem); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def m():
    return load('manifest_candidate.py', 'm10_candidate')


@pytest.fixture(scope='module')
def cap():
    return load('capture_m10.py', 'cap')


@pytest.fixture(scope='module')
def old():
    return json.loads(INSTALLED.read_bytes())


@pytest.fixture(scope='module')
def seq16(cap):
    raw = cap.SEQ16.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == cap.SEQ16_SHA
    return json.loads(raw)['closure']


@pytest.fixture(scope='module')
def m9base():
    return json.loads(M9_BASELINE.read_bytes())['closure']


def synthetic(m, cap, seq16, m9base):
    """The sequence 16 closure with the reviewed city change applied, the M9 baseline for what it does not
    cover (the capture proves those against the M9 manifest), and the two new M10 pins."""
    closure = copy.deepcopy(seq16)
    for key in ('pins', 'trees', 'links'):
        for path, value in m9base[key].items():
            closure[key].setdefault(path, value)
    for path, (_, after) in cap.PIN_CHANGES.items():
        closure['pins'][path] = dict(closure['pins'][path], sha256=after)
    closure['pins'][m.CITY_SOURCE] = dict(sha256=m.CITY_NEW, mode=0o644, uid=1000, gid=1000, size=1)
    closure['pins'][m.ARTIFACT] = dict(sha256=m.NEW, mode=0o755, uid=1000, gid=1000, size=m.NEW_SIZE)
    return closure


def parents(m, old):
    base = old['metadata']['parents'][0]
    return [base] + [dict(base, path=m.ROOT + '/' + n, entries=[], mode=0o700, uid=1000, gid=1000,
                          device=1, inode=100 + i) for i, n in enumerate(('b', 't'))]


def build(m, old, closure):
    return m.assemble(copy.deepcopy(old), closure, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)


# Predecessor, build and receipt bytes.

def test_predecessor_and_live_bytes(m, seq16):
    assert sha(INSTALLED) == m.OLD_MANIFEST_SHA
    assert sha(m.OLD_ROOT + '/q/manifest.json') == m.OLD_MANIFEST_SHA
    assert sha(INSTALLED.parent/'install-receipt.json') == m.OLD_RECEIPT_SHA
    assert sha(m.ARTIFACT) == m.NEW and os.stat(m.ARTIFACT).st_size == m.NEW_SIZE
    assert sha(m.BACKUP) == sha(m.OLD_SOURCE) == m.OLD and os.stat(m.BACKUP).st_size == m.OLD_SIZE
    assert sha(m.GC) == m.NEW
    assert sha(m.CITY_CONFIG_BACKUP) == sha(m.CITY_OLD_SOURCE) == m.CITY_OLD
    assert seq16['pins'][m.GC]['sha256'] == m.NEW and seq16['suspension']['sha256'] == m.SUSPENSION_SHA
    assert seq16['trees'][m.ODB]['sha256'] == m.EXACT_TREES[m.ODB][1]
    assert seq16['scope']['dolt_members']['watchdog_image'] == 'deleted-old'


def test_build_result_binds_the_commit(m):
    result = json.loads(Path('/var/tmp/ga-bebv-build-20260927/result.json').read_bytes())
    assert result['ok'] is True and result['head'] == m.COMMIT
    assert [(a['path'], a['sha256'], a['version']['commit'], a['version']['version']) for a in result['artifacts']][0] == (
        m.ARTIFACT, m.NEW, m.COMMIT, m.VERSION)


def test_sequence_16_receipt(m):
    value = m.receipt()
    assert value['sequence'] == 16 and value['source']['tree'] == 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'


# The city.toml derivation, structure and selections.

def test_make_city_reproduces_the_probed_bytes(m):
    make = load('make_city.py', 'make_city')
    live = Path(m.CITY_TOML).read_bytes()
    if hashlib.sha256(live).hexdigest() == m.CITY_NEW:
        pytest.skip('the city prerequisite already ran')
    new = make.derive(live)
    assert hashlib.sha256(new).hexdigest() == m.CITY_NEW == make.CITY_NEW and make.CITY_OLD == m.CITY_OLD
    with pytest.raises(RuntimeError, match='reviewed predecessor'):
        make.derive(live + b'\n')


def city_pair(m):
    make = load('make_city.py', 'make_city')
    old = Path(m.CITY_CONFIG_BACKUP).read_bytes()
    return old.decode(), make.derive(old).decode()


def test_structure_and_selections_hold(m):
    pr = load('prereqs_m10.py', 'prereqs_m10')
    old, new = city_pair(m)
    report = pr.city_structure(old, new)
    assert report == dict(patches=8, claude_keys=['permission_mode', 'effort', 'model', 'worktree_access'],
                          codex_keys=['permission_mode', 'model', 'effort', 'worklog_access'])
    fragments, agents = pr.live_texts()
    result = pr.selections(new, fragments, agents)
    assert result['selected'] >= 20 and 'providers.claude' in result['origins'] and 'providers.codex' in result['origins']


@pytest.mark.parametrize('edit, reason', [
    (lambda t: t.replace('max_active_sessions = 16', 'max_active_sessions = 17', 1), 'outside providers and patches'),
    (lambda t: t.replace('[providers.claude-attention]\nbase = "provider:claude"\n',
                         '[providers.claude-attention]\nbase = "provider:claude"\ntitle_model = "x"\n', 1),
     'another provider changed'),
    (lambda t: t.replace('flag_args = ["--permission-mode", "plan"]', 'flag_args = ["--dangerously-skip-permissions"]', 1),
     'replaced providers'),
    (lambda t: t + '\n[[patches.agent]]\ndir = "blog"\nname = "x"\nwork_dir_roots = ["/"]\n', 'beyond the append'),
])
def test_structure_refuses(m, edit, reason):
    pr = load('prereqs_m10.py', 'prereqs_m10')
    old, new = city_pair(m)
    with pytest.raises(RuntimeError, match=reason):
        pr.city_structure(old, edit(new))


def test_structure_refuses_an_unsafe_reviewed_fragment(m, tmp_path):
    """The unsafe-flag and default checks run over the reviewed fragments themselves."""
    pr = load('prereqs_m10.py', 'prereqs_m10')
    safe, unsafe = ('flag_args = ["--permission-mode", "plan"]', 'flag_args = ["--permission-mode", "bypassPermissions"]')
    for name in ('providers-claude.toml', 'providers-codex.toml', 'patches-work-dir-roots.toml'):
        text = (HERE/name).read_text()
        (tmp_path/name).write_text(text.replace(safe, unsafe) if name == 'providers-claude.toml' else text)
    assert (tmp_path/'providers-claude.toml').read_text().count(unsafe) == 1
    pr.HERE = tmp_path
    old, new = city_pair(m)
    assert new.count(safe) == 1
    with pytest.raises(RuntimeError, match='unrestricted choice'):
        pr.city_structure(old, new.replace(safe, unsafe))


def test_selections_refuse_a_withdrawn_option(m):
    pr = load('prereqs_m10.py', 'prereqs_m10')
    _, new = city_pair(m)
    fragments, agents = pr.live_texts()
    agents = dict(agents, **{'/synthetic/agent.toml': 'provider = "claude"\n[option_defaults]\npermission_mode = "bypass"\n'})
    with pytest.raises(RuntimeError, match='no longer offer'):
        pr.selections(new, fragments, agents)
    withdrawn = new.replace('value = "haiku-4-5"', 'value = "haiku-4"', 1)
    with pytest.raises(RuntimeError, match='no longer offer'):
        pr.selections(withdrawn, pr.live_texts()[0], pr.live_texts()[1])


def test_work_dir_roots_cover_the_candidate_roots():
    patches = tomllib.loads((HERE/'patches-work-dir-roots.toml').read_text())['patches']['agent']
    roots = {(p['dir'], p['name']): p['work_dir_roots'] for p in patches}
    assert roots == {
        ('gas-city-template', 'implementation-worker'): ['/home/loucmane/gas-city-template-worktrees'],
        ('gas-city-template', 'run-operator'): ['/home/loucmane/gas-city-template-worktrees'],
        ('gas-city-template', 'codex'): ['/home/loucmane/gas-city-template-worktrees'],
        ('gascity', 'implementation-worker'): ['/home/loucmane/gascity-core-worktrees'],
        ('gascity', 'operations-candidate-worker'): ['/home/loucmane/gas-city-ops-candidate-worktrees'],
        ('blog', 'implementation-worker'): ['/home/loucmane/dev/blog-worktrees'],
        ('hpfetcher', 'implementation-worker'): ['/home/loucmane/dev/hpfetcher-worktrees'],
        ('hpfetcher', 'run-operator'): ['/home/loucmane/dev/hpfetcher-worktrees'],
    }
    for values in roots.values():
        assert all(os.path.isdir(r) and not os.path.islink(r) and '.git' not in r.split('/') for r in values)


def test_offline_core_probe_evidence():
    """The probe (probe/zz_probe_providers_test.go.txt, run in the ga-6umo worktree at f45a6262 and removed)
    resolved every agent and provider with LoadWithIncludes, ResolveProvider and BuildProviderLaunchCommand.

    probe-current.json is the installed city; probe-full.json is CITY_NEW. The new city offers no unrestricted
    choice anywhere, resolves every entry, and leaves every launch command and default exactly as today. The
    only recorded refusal is the work_dir guard refusing the Blog Git metadata directory.
    """
    now = json.loads((HERE/'probe/probe-current.json').read_bytes())
    new = json.loads((HERE/'probe/probe-full.json').read_bytes())
    assert len(now) == len(new) == 118 and set(now) == set(new)
    assert sum(1 for v in now.values() if any(not u.startswith('guard-') for u in v.get('unsafe_choices') or ())) > 100
    for key, value in new.items():
        assert not value.get('error'), key
        assert all(u.startswith('guard-refused:') for u in value.get('unsafe_choices') or ()), key
        flags = json.dumps(value.get('schema', {}))
        assert not any(u in flags for u in UNSAFE), key
        assert value.get('command') == now[key].get('command') and value.get('defaults') == now[key].get('defaults'), key
    refused = sorted(u for v in new.values() for u in v.get('unsafe_choices') or ())
    assert refused == ['guard-refused:/home/loucmane/dev/blog-worktrees/.git']


# The native successor rules and the pure build.

def test_native_successor_rules(m, cap, old, seq16, m9base):
    for name, needles in (('installer.go', ('candidate.PreviousSHA256 != previous.Core.SHA256',
                                            'candidate.Activation.PreviousCommit != previous.Activation.ExpectedCommit',
                                            'candidateFile.PreviousSHA256 != previousFile.SHA256')),
                          ('metadata_adopt.go', ('metadata-only adoption requires all managed artifacts already installed',
                                                 'metadata-only adoption requires existing managed backup'))):
        shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', CORE_SOURCE, 'show',
                                m.COMMIT + ':internal/platforminstall/' + name], capture_output=True, check=True)
        for needle in needles:
            assert needle in shown.stdout.decode(), (name, needle)
    out, _ = build(m, old, synthetic(m, cap, seq16, m9base))
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


def test_build_counts_frame_and_identity(m, cap, old, seq16, m9base):
    out, report = build(m, old, synthetic(m, cap, seq16, m9base))
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (696, 49, 23)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR and report['frame']['upper_bound_bytes'] <= 131072
    assert out['release_id'] == m.RELEASE_ID
    assert out['core'] == dict(name='gc', source=m.ARTIFACT, destination=m.GC, sha256=m.NEW, mode=0o755)
    assert out['activation'] == dict(expected_commit=m.COMMIT, expected_version='dev',
                                     previous_commit=m.OLD_COMMIT, previous_version='dev')
    assert out['previous_sha256'] == old['previous_sha256'] == m.OLD and out['backup_path'] == old['backup_path'] == m.BACKUP
    assert md['writer'] == dict(name='', path=m.GC, sha256=m.NEW, mode=0o755)
    assert out['previous_metadata']['manifest_sha256'] == m.OLD_MANIFEST_SHA
    assert out['previous_metadata']['receipt_sha256'] == m.OLD_RECEIPT_SHA
    assert md['evidence'] == m.ROOT + '/t'
    config = [f for f in out['managed_files'] if f['name'] == 'city-config']
    assert config == [dict(name='city-config', source=m.CITY_SOURCE, destination=m.CITY_TOML, sha256=m.CITY_NEW,
                           mode=0o644, previous_sha256=m.CITY_OLD, backup_path=m.CITY_CONFIG_BACKUP)]


def test_only_reviewed_fields_change(m, cap, old, seq16, m9base):
    out, _ = build(m, old, synthetic(m, cap, seq16, m9base))
    before = [dict(p) for p in old['metadata']['inputs']]
    after = out['metadata']['inputs']
    # Same order and length; exactly four rows differ, as NEW_INPUTS and SUPERSEDED_INPUTS say.
    moved = {m.OLD_SOURCE: m.ARTIFACT, m.CITY_OLD_SOURCE: m.CITY_SOURCE}
    expected = []
    for row in before:
        row = dict(row)
        row['path'] = moved.get(row['path'], row['path'])
        for path, value, mode in m.NEW_INPUTS:
            if row['path'] == path:
                row.update(sha256=value, mode=mode)
        expected.append(row)
    assert after == expected
    assert sum(1 for a, b in zip(before, after) if a != b) == 4
    assert dict(m.SUPERSEDED_INPUTS) == moved
    trees_before = {t['path']: t for t in old['metadata']['trees']}
    trees_after = {t['path']: t for t in out['metadata']['trees']}
    assert [p for p in trees_before if trees_before[p] != trees_after[p]] == [m.ODB]
    for key in ('links', 'runtime', 'protected_trees', 'absent', 'gc_home', 'imports_sha256', 'cache_sha256'):
        assert out['metadata'][key] == old['metadata'][key], key
    assert [f for f in out['managed_files'] if f['name'] != 'city-config'] == \
        [f for f in old['managed_files'] if f['name'] != 'city-config']
    assert out['integrity'] == old['integrity']
    top = {k for k in old if old[k] != out[k]}
    assert top == {'release_id', 'metadata', 'core', 'activation', 'managed_files', 'previous_metadata',
                   'manifest_sha256'}


@pytest.mark.parametrize('mutate, reason', [
    (lambda c, m: c['pins'].__setitem__(m.GC, dict(c['pins'][m.GC], sha256='0' * 64)), 'installed sequence 16 image'),
    (lambda c, m: c['pins'].__setitem__(m.ARTIFACT, dict(c['pins'][m.ARTIFACT], size=1)), 'sequence 16 build source'),
    (lambda c, m: c['pins'].__setitem__(m.BACKUP, dict(c['pins'][m.BACKUP], sha256='0' * 64)), 'previous image backup'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_TOML, dict(c['pins'][m.CITY_TOML], sha256=m.CITY_OLD)),
     'installed city config'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_SOURCE, dict(c['pins'][m.CITY_SOURCE], mode=0o600)), 'city config source'),
    (lambda c, m: c['pins'].__setitem__(m.CITY_CONFIG_BACKUP, dict(c['pins'][m.CITY_CONFIG_BACKUP], sha256='0' * 64)),
     'city config backup bytes'),
    (lambda c, m: c['trees'].__setitem__(m.ODB, dict(c['trees'][m.ODB], sha256=m.EXACT_TREES[m.ODB][0])),
     'sequence 16 accepted tree'),
    (lambda c, m: c['trees'].__setitem__(m.CACHE, dict(sha256='0' * 64)), 'unchanged cache'),
    (lambda c, m: c['pins'].__setitem__('/usr/lib/x86_64-linux-gnu/libc.so.6',
                                        dict(c['pins']['/usr/lib/x86_64-linux-gnu/libc.so.6'], sha256='0' * 64)),
     'input differs from the baseline'),
    (lambda c, m: c['links'].pop(next(iter(c['links']))), 'link differs from the baseline'),
])
def test_build_refuses_drift(m, cap, old, seq16, m9base, mutate, reason):
    closure = synthetic(m, cap, seq16, m9base)
    mutate(closure, m)
    with pytest.raises(RuntimeError, match=reason):
        build(m, old, closure)


def _config(o):
    return [f for f in o['managed_files'] if f['name'] == 'city-config'][0]


@pytest.mark.parametrize('mutate, reason', [
    (lambda o, m: o.__setitem__('previous_sha256', 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'),
     'previous image'),
    (lambda o, m: o['activation'].__setitem__('previous_commit', '9faeabc2892d8c7133111e13ad55af66790a2ac6'),
     'activation'),
    (lambda o, m: o['core'].__setitem__('sha256', m.NEW), 'exact installed Core predecessor'),
    (lambda o, m: o.__setitem__('release_id', 'other'), 'not M9'),
    (lambda o, m: _config(o).__setitem__('sha256', m.CITY_NEW), 'exact predecessor city config'),
    (lambda o, m: _config(o).__setitem__('backup_path', '/tmp/x'), 'exact predecessor city config'),
    (lambda o, m: o['metadata']['inputs'].append(dict(name='', path=m.ARTIFACT, sha256=m.NEW, mode=0o755)),
     'build source already present'),
    (lambda o, m: o['metadata']['inputs'].append(dict(name='', path=m.CITY_SOURCE, sha256=m.CITY_NEW, mode=0o644)),
     'city source already present'),
    (lambda o, m: o['integrity']['providers'].pop(), 'exact M9 provider list'),
    (lambda o, m: [p for p in o['metadata']['trees'] if p['path'] == m.ODB][0].__setitem__('sha256', '0' * 64),
     'sequence 16 accepted tree'),
])
def test_build_refuses_wrong_predecessor(m, cap, old, seq16, m9base, mutate, reason):
    changed = copy.deepcopy(old)
    mutate(changed, m)
    changed = m.b.finalized(changed)
    with pytest.raises(RuntimeError, match=reason):
        build(m, changed, synthetic(m, cap, seq16, m9base))


def test_build_against_frozen_baseline(m, cap, old):
    path = Path(m.BASELINE_PATH)
    if m.BASELINE_SHA is None or not path.exists():
        pytest.skip('baseline not frozen yet')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.BASELINE_SHA
    record = json.loads(raw)
    assert record['drifts'] == [] and record['seq16_observation_sha256'] == cap.SEQ16_SHA
    assert record['pin_changes'] == [m.CITY_TOML]
    closure = record['closure']
    out, report = m.build(INSTALLED.read_bytes(), raw, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)
    assert (len(out['metadata']['inputs']), len(out['metadata']['trees'])) == (696, 49)
    assert report['frame']['remaining_bytes'] > m.FRAME_FLOOR


# The capture.

def test_capture_target(m, cap, old):
    expected, trees, links = cap.target(m, old)
    assert all(expected[p] == dict(sha256=v, mode=mode) for p, v, mode in m.NEW_INPUTS)
    assert expected[m.BACKUP] == dict(sha256=m.OLD, mode=0o755)
    assert expected[m.CITY_CONFIG_BACKUP]['sha256'] == m.CITY_OLD
    assert len(trees) == 49 and len(links) == 23


def test_pin_change_rule(m, cap, seq16):
    pins = seq16['pins']
    assert set(cap.PIN_CHANGES) == {m.CITY_TOML} and cap.PIN_CHANGES[m.CITY_TOML] == (m.CITY_OLD, m.CITY_NEW)
    assert pins[m.CITY_TOML]['sha256'] == m.CITY_OLD
    live = copy.deepcopy(pins)
    live[m.CITY_TOML] = dict(live[m.CITY_TOML], sha256=m.CITY_NEW, size=live[m.CITY_TOML]['size'] + 1)
    changed, problems = cap.pin_changes(pins, live, cap.PIN_CHANGES)
    assert problems == [] and changed == [m.CITY_TOML]
    for mutate in (lambda v: v.__setitem__(m.CITY_TOML, dict(v[m.CITY_TOML], mode=0o600)),
                   lambda v: v.__setitem__(m.CITY_TOML, dict(v[m.CITY_TOML], sha256='0' * 64)),
                   lambda v: v.__setitem__(m.GC, dict(v[m.GC], sha256='0' * 64))):
        trial = copy.deepcopy(live)
        mutate(trial)
        assert cap.pin_changes(pins, trial, cap.PIN_CHANGES)[1]
    assert m.CITY_TOML in cap.pin_changes(pins, copy.deepcopy(pins), cap.PIN_CHANGES)[1]  # it must have happened


def test_cache_rule(cap, seq16):
    accepted = seq16['cache']
    assert cap.cache_drift(copy.deepcopy(accepted), accepted) == ([], [])
    git_key = next(k for k in accepted['inventory'] if k.split('/')[1:2] == ['.git'])
    live = copy.deepcopy(accepted)
    live['inventory'][git_key].update(mtime_ns=1, ctime_ns=2)
    assert cap.cache_drift(live, accepted)[1] == []
    trial = copy.deepcopy(accepted)
    trial['inventory'][git_key].update(size=10**9)
    assert cap.cache_drift(trial, accepted)[1]


def test_capture_differs_from_m9_only_in_reviewed_places(cap):
    ours = (HERE/'capture_m10.py').read_text()
    theirs = (M9/'capture_m9.py').read_text()
    for name in ('pin_changes', 'cache_drift', 'tree_drift', 'target'):
        body = lambda text: text.split('\ndef %s(' % name)[1].split('\ndef ')[0].split('"""')[2]
        if name == 'target':
            assert body(ours).replace(
                '    # The moved and added pins: the sequence 16 image and build source, the new city.toml and its source.\n',
                '') == body(theirs)
        else:
            assert body(ours) == body(theirs), name
    main = ours.split('\ndef main():')[1]
    for fresh in ("'usage: capture_m10.py <candidate sha256>'", "sys.argv[1], 'm10_candidate')",
                  "CLOSURE_SHA, 'm10_closure')", "Path(m.O + '/reports/m10-capture')",
                  "schema='ga-bebv.m10-baseline.v1'", 'seq16_observation_sha256=SEQ16_SHA',
                  'raw = SEQ16.read_bytes()', "kind='sequence-16-pins'"):
        assert main.count(fresh) == 1, fresh
    for stale in ('m8', 'M8', 'm9', 'M9', 'seq15', 'M7', 'm7'):
        assert stale not in main, stale
    theirs_main = theirs.split('\ndef main():')[1]
    assert len(main.splitlines()) == len(theirs_main.splitlines()) + 1


# Sources and the prerequisite.

def test_source_pins(cap):
    for name in ('source_runtime.py', 'launch.py', 'metadata_executor.py', 'metadata_window.py', 'metadata_closure.py'):
        assert sha(HERE/name) == sha(M9/name), name
    pr = load('prereqs_m10.py', 'prereqs_m10')
    assert cap.RUNTIME_SHA == pr.RUNTIME_SHA == sha(HERE/'source_runtime.py')
    assert cap.CLOSURE_SHA == pr.CLOSURE_SHA == sha(HERE/'metadata_closure.py')
    assert cap.PREREQS_SHA == pr.PREREQS_SHA == sha(cap.PREREQS) and cap.CAPTURE_M6_SHA == sha(cap.CAPTURE_M6)
    assert pr.SEQ16_SHA == cap.SEQ16_SHA
    ours = (HERE/'record_review.py').read_text().splitlines()
    theirs = (M9/'record_review.py').read_text().splitlines()
    differing = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs) and len(differing) == 5
    assert all('m10' in a.lower() and 'm9' in b.lower() for a, b in differing)


def test_prerequisite_paths_and_rollback_bounds(m):
    pr = load('prereqs_m10.py', 'prereqs_m10')
    assert pr.STEPS == ('inputs', 'city') and pr.CITY/'city.toml' == Path(m.CITY_TOML)
    assert pr.temporary('forward').parent == pr.CITY and pr.temporary('forward').name.startswith('.city.toml.ga-bebv-m10.')
    assert pr.temporary('rollback', 3) != pr.temporary('rollback', 4)
    assert Path(m.CITY_SOURCE).parent == Path(m.O + '/reports/m10-inputs')
    assert set(pr.ACTIONS) == {'inputs', 'city', 'rollback'}


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
