"""Tests for the ga-e0t1.15 S3 metadata successor package (M6).

  python3 -m pytest -q designs/ga-e0t1.15-deploy/s3/test_s3.py

Offline except where marked: the builder tests read the installed M5 manifest and the S2-accepted
observation read-only; the derivation test needs a repository holding cfd353f3 (the canonical Template
after the fetch step, or S3_DERIVE_REPO) and skips otherwise.
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
M5 = HERE.parent.parent/'gct-m1wh-m5'
INSTALLED = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
S2 = Path('/var/tmp/ga-e0t1.15-seq14-recovery-20260925/observation-2.json')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, module_name=None):
    path = HERE/name
    module = types.ModuleType(module_name or path.stem); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def m():
    return load('manifest_candidate.py', 'm6_candidate')


@pytest.fixture(scope='module')
def old():
    return json.loads(INSTALLED.read_bytes())


@pytest.fixture(scope='module')
def s2():
    return json.loads(S2.read_bytes())['closure']


def synthetic(m, old, s2):
    """A closure shaped like capture_m6.py's, from the M5 pins, the S2 trees and the derived coverage."""
    md = old['metadata']
    pins = {p['path']: dict(sha256=p['sha256'], mode=p['mode'], size=0) for p in md['inputs']}
    pins[m.GC] = dict(sha256=m.NEW, mode=0o755, size=m.NEW_SIZE)
    pins[m.ARTIFACT] = dict(sha256=m.NEW, mode=0o755, size=m.NEW_SIZE)
    for path, _, after in m.CHANGED_INPUTS:
        pins[path] = dict(pins[path], sha256=after)
    for relative, digest, mode in m.auth_inputs():
        pins[m.AUTHORITY + '/' + relative] = dict(sha256=digest, mode=mode, size=0)
    trees = {p['path']: dict(sha256=p['sha256']) for p in md['trees']}
    trees.update({path: dict(value) for path, value in s2['trees'].items()})
    trees[m.TEMPLATE_GIT] = dict(sha256='f' * 64)
    for relative in m.AUTH_TREES:
        trees[m.AUTHORITY + '/' + relative] = dict(sha256='e' * 64)
    links = {p['path']: p['target'] for p in md['links']}
    links.update({m.AUTHORITY + '/' + r: t for r, t in m.AUTH_LINKS})
    host = dict(host=s2['host']['host'], namespaces=s2['host']['namespaces'])
    return dict(host=host, pins=pins, trees=trees, links=links)


def parents(m, old):
    base = old['metadata']['parents'][0]
    return [base] + [dict(base, path=m.ROOT + '/' + n, entries=[], mode=0o700, uid=1000, gid=1000,
                          device=1, inode=100 + i) for i, n in enumerate(('b', 't'))]


def build(m, old, closure):
    return m.assemble(copy.deepcopy(old), closure, closure['host'], parents(m, old), 'a' * 64, 'b' * 64)


def test_predecessor_bytes(m):
    assert sha(INSTALLED) == m.OLD_MANIFEST_SHA
    assert sha(m.OLD_ROOT + '/q/manifest.json') == m.OLD_MANIFEST_SHA
    assert sha(S2) == load('prereqs_m6.py', 'p').S2_OBSERVATION_SHA


def test_build_counts_frame_and_identity(m, old, s2):
    out, report = build(m, old, synthetic(m, old, s2))
    md = out['metadata']
    assert (len(md['inputs']), len(md['trees']), len(md['links'])) == (686, 49, 23)
    assert report['frame']['remaining_bytes'] > 0 and report['frame']['upper_bound_bytes'] <= 131072
    assert out['release_id'] == m.RELEASE_ID
    assert out['core'] == dict(old['core'], source=m.ARTIFACT, sha256=m.NEW)
    assert out['activation'] == dict(expected_commit=m.COMMIT, expected_version='dev',
                                     previous_commit=m.OLD_COMMIT, previous_version='dev')
    assert out['previous_sha256'] == m.OLD and out['backup_path'] == m.BACKUP
    assert md['writer']['sha256'] == m.NEW
    assert [p for p in md['inputs'] if p['path'] == m.GC][0]['sha256'] == m.NEW
    assert md['cache_sha256'] == m.EXACT_TREES[m.CACHE][1]
    repos = out['integrity']['repositories']
    assert repos[-1] == dict(name=m.AUTHORITY_NAME, path=m.AUTHORITY, commit=m.TEMPLATE_COMMIT)
    assert m.M5_AUTHORITY_NAME not in {r['name'] for r in repos} and len(repos) == 7
    assert not any(p['path'].startswith(m.M5_AUTHORITY) for kind in ('inputs', 'trees', 'links') for p in md[kind])
    worker = [p for p in out['integrity']['providers'] if p['name'] == 'claude'][0]
    assert worker['version'] == m.VERSION_NEW
    assert out['previous_metadata']['manifest_sha256'] == m.OLD_MANIFEST_SHA
    assert out['previous_metadata']['manifest_backup_path'] == m.ROOT + '/b/install-manifest.before.json'


def test_only_reviewed_fields_change(m, old, s2):
    out, _ = build(m, old, synthetic(m, old, s2))
    under = lambda path: path.startswith(m.M5_AUTHORITY + '/') or path.startswith(m.AUTHORITY + '/')
    before = {p['path']: p for p in old['metadata']['inputs'] if not under(p['path'])}
    after = {p['path']: p for p in out['metadata']['inputs'] if not under(p['path'])}
    assert set(after) - set(before) == {m.ARTIFACT}
    changed = {k for k in before if before[k] != after[k]}
    assert changed == {m.GC} | {p for p, _, _ in m.CHANGED_INPUTS}
    trees_before = {p['path']: p for p in old['metadata']['trees'] if not under(p['path'])}
    trees_after = {p['path']: p for p in out['metadata']['trees'] if not under(p['path'])}
    assert {k for k in trees_before if trees_before[k] != trees_after[k]} == {m.ODB, m.CACHE, m.TEMPLATE_GIT}
    for key in ('runtime', 'protected_trees', 'absent', 'gc_home', 'imports_sha256'):
        assert out['metadata'][key] == old['metadata'][key]
    assert out['managed_files'] == old['managed_files']
    assert out['integrity']['files'] == old['integrity']['files']


@pytest.mark.parametrize('mutate, reason', [
    (lambda c, m: c['pins'].__setitem__(m.GC, dict(c['pins'][m.GC], sha256='0' * 64)), 'installed sequence 14'),
    (lambda c, m: c['pins'].__setitem__(m.ARTIFACT, dict(c['pins'][m.ARTIFACT], mode=0o644)), 'build source'),
    (lambda c, m: c['trees'].__setitem__(m.ODB, dict(sha256='0' * 64)), 'S2-accepted tree'),
    (lambda c, m: c['trees'].__setitem__(m.TEMPLATE_GIT, dict(sha256=m.TEMPLATE_GIT_S2)), 'Template Git tree'),
    (lambda c, m: c['pins'].__setitem__(m.CHANGED_INPUTS[0][0], dict(c['pins'][m.CHANGED_INPUTS[0][0]], sha256='0' * 64)),
     'reviewed successor input'),
    (lambda c, m: c['links'].pop(m.AUTHORITY + '/plans/current'), 'authority link'),
    (lambda c, m: c['pins'].__setitem__(m.AUTHORITY + '/.git', dict(c['pins'][m.AUTHORITY + '/.git'], sha256='0' * 64)),
     'authority file'),
])
def test_build_refuses_drift(m, old, s2, mutate, reason):
    closure = synthetic(m, old, s2)
    mutate(closure, m)
    with pytest.raises(RuntimeError, match=reason):
        build(m, old, closure)


def test_build_refuses_wrong_predecessor(m, old, s2):
    changed = copy.deepcopy(old)
    changed['activation']['expected_commit'] = m.COMMIT
    changed = m.b.finalized(changed)
    with pytest.raises(RuntimeError, match='activation'):
        build(m, changed, synthetic(m, old, s2))


def test_window_is_access_time_neutral():
    w = load('metadata_window.py', 'w')
    start = dict(boot='00000000-0000-0000-0000-000000000000', mono=10**12, boot_time=10**12, wall=10**18, span=1)
    cache = dict(inventory={'.': dict(mtime_ns=5, ctime_ns=6)})
    window = w.build(start, cache, 'a' * 64)
    assert window['max_atime'] == 1 and window['renewal'] == start['wall'] + 86400 * w.SECOND
    w.check(window, dict(start, mono=start['mono'] + w.SECOND), cache, 'a' * 64)
    w.admit(window, dict(start, mono=start['mono'] + w.SECOND), cache, 'a' * 64)
    with pytest.raises(RuntimeError, match='monotonic window expired'):
        w.check(window, dict(start, mono=start['mono'] + w.WINDOW), cache, 'a' * 64)
    with pytest.raises(RuntimeError, match='access-time neutral'):
        w.build(start, dict(inventory={'.': dict(mtime_ns=5, ctime_ns=6, atime_ns=7)}), 'a' * 64)


class FakeObserver:
    SERVICE, RECONCILER, ENV = 'svc', 'rec', {}

    @staticmethod
    def require(ok, reason):
        if not ok:
            raise RuntimeError(reason)

    @staticmethod
    def metadata(value, include_atime=True):
        return dict(value, **({'atime_ns': 1} if include_atime else {}))

    @staticmethod
    def tree_snapshot(root, cache=False, protected=False):
        return dict(sha256='x', inventory={'.': dict(mode=0o755, atime_ns=9, mtime_ns=1)})


def fake_state(members, table):
    return types.SimpleNamespace(members=lambda unit: set(members.get(unit, ())), process_table=lambda: dict(table),
                                 descendants=lambda t, seeds: _descendants(t, seeds), quiet_scope=None)


def _descendants(table, seeds):
    found = set(seeds)
    while True:
        expanded = found | {pid for pid, (ppid, _) in table.items() if ppid in found}
        if expanded == found:
            return found
        found = expanded


def test_policy_strips_access_times():
    closure = load('metadata_closure.py', 'cl')
    o = types.SimpleNamespace(**{k: getattr(FakeObserver, k) for k in ('SERVICE', 'RECONCILER', 'ENV', 'require',
                                                                        'metadata', 'tree_snapshot')})
    s = fake_state({}, {})
    closure.install_policy(o, s, 'a' * 64)
    assert 'atime_ns' not in o.metadata({'mode': 1})
    assert 'atime_ns' not in o.tree_snapshot('/x')['inventory']['.']
    assert s.quiet_scope is not None


def scope_fixture(monkeypatch, closure, watchdog_argv=None, extra=False, exe_suffix=''):
    o = types.SimpleNamespace(**{k: getattr(FakeObserver, k) for k in ('SERVICE', 'RECONCILER', 'ENV', 'require',
                                                                        'metadata', 'tree_snapshot')})
    members = {'svc': {100, 200, 300} | ({400} if extra else set())}
    table = {100: (1, 11), 200: (1, 22), 300: (200, 33), 400: (1, 44)}
    s = fake_state(members, table)
    closure.install_policy(o, s, hashlib.sha256(b'old').hexdigest())
    argvs = {200: watchdog_argv or [closure.GC_BIN, '__gc-managed-dolt-scope-watchdog', closure.DOLT_CFG,
                                    closure.DOLT_LOG, closure.CITY],
             300: ['dolt', 'sql-server', '--config', closure.DOLT_CFG], 400: ['sleep', '1']}
    exes = {200: closure.GC_BIN + exe_suffix, 300: closure.DOLT_BIN, 400: '/usr/bin/sleep'}
    real_read = Path.read_bytes

    def read_bytes(self):
        parts = self.parts
        if parts[:2] == ('/', 'proc') and parts[-1] == 'cmdline':
            return b'\0'.join(a.encode() for a in argvs[int(parts[2])]) + b'\0'
        if parts[:2] == ('/', 'proc') and parts[-1] == 'exe':
            return b'old'
        return real_read(self)
    monkeypatch.setattr(Path, 'read_bytes', read_bytes)
    monkeypatch.setattr(closure.os, 'readlink', lambda path: exes[int(str(path).split('/')[2])])
    monkeypatch.setattr(closure.subprocess, 'run', lambda *a, **k: types.SimpleNamespace(
        returncode=1, stdout=b'', stderr=b'no server running on /tmp/tmux-1000/city'))
    return o, s


def test_quiet_scope_admits_exact_dolt_members(monkeypatch):
    closure = load('metadata_closure.py', 'cl')
    o, s = scope_fixture(monkeypatch, closure)
    value = s.quiet_scope(dict(host=dict(pid=100)))
    assert value['dolt_members']['watchdog'] == 200 and value['dolt_members']['watchdog_image'] == 'live'
    closure = load('metadata_closure.py', 'cl2')
    o, s = scope_fixture(monkeypatch, closure, exe_suffix=' (deleted)')
    assert s.quiet_scope(dict(host=dict(pid=100)))['dolt_members']['watchdog_image'] == 'deleted-old'


@pytest.mark.parametrize('kwargs, reason', [
    (dict(extra=True), 'supervisor scope membership'),
    (dict(watchdog_argv=['/home/loucmane/gascity/bin/gc', '__gc-managed-dolt-scope-watchdog', 'x', 'y', 'z']),
     'dolt watchdog argv'),
])
def test_quiet_scope_refuses(monkeypatch, kwargs, reason):
    closure = load('metadata_closure.py', 'cl3')
    o, s = scope_fixture(monkeypatch, closure, **kwargs)
    with pytest.raises(RuntimeError, match=reason):
        s.quiet_scope(dict(host=dict(pid=100)))


def test_git_bound():
    c = load('capture_m6.py', 'cap')
    before = {'.': dict(m=1), 'objects/aa/bb': dict(m=1), 'worktrees/x/commondir': dict(m=1),
              'worktrees/x/config.worktree': dict(size=0), 'hooks/pre-commit.sample': dict(m=1)}
    ok = dict(before, **{'objects/cc/dd': dict(m=2), 'refs/remotes/origin/main': dict(m=1), 'FETCH_HEAD': dict(m=1),
                         'worktrees/y/gitdir': dict(m=1), 'HEAD': dict(m=3), '.': dict(m=2)})
    assert c.classify(before, ok)['outside_allowed'] == []
    for key, value in (('refs/replace/abc', dict(m=1)), ('objects/info/alternates', dict(m=1)),
                       ('worktrees/y/info/exclude', dict(m=1)), ('shallow', dict(m=1)),
                       ('worktrees/y/config.worktree', dict(size=0)), ('hooks/post-checkout', dict(m=1)),
                       ('worktrees/x/commondir', dict(m=9)), ('gc.pid', dict(m=1))):
        assert c.classify(before, dict(before, **{key: value}))['outside_allowed'], key


def test_git_config_set():
    c = load('capture_m6.py', 'cap')
    listing = '\n'.join(c.CONFIG_EXPECTED + ('branch.main.remote=origin', 'branch.main.merge=refs/heads/main'))
    assert not any(c.config_drift(listing).values())
    assert c.config_drift(listing + '\ncore.hooksPath=/tmp')['unexpected']
    assert c.config_drift(listing + '\nbranch.main.rebase=true')['bad_branch_keys']


def test_capture_target(m, old):
    c = load('capture_m6.py', 'cap')
    expected, trees, links = c.target(m, old)
    assert expected[m.GC]['sha256'] == m.NEW and expected[m.ARTIFACT]['sha256'] == m.NEW
    assert expected[m.CHANGED_INPUTS[1][0]]['sha256'] == m.CHANGED_INPUTS[1][2]
    assert not any(p.startswith(m.M5_AUTHORITY + '/') for p in expected)
    assert sum(p.startswith(m.AUTHORITY + '/') for p in expected) == 12
    assert len(trees) == 49 and len(set(trees)) == 49 and len(links) == 23


def test_quiet_slot_waits_for_idle():
    p = load('prereqs_m6.py', 'p')
    now = [0]
    states = iter([dict(active='active', timer='active', next_us=10**9, started_us=1),
                   dict(active='inactive', timer='active', next_us=100, started_us=1),
                   dict(active='inactive', timer='active', next_us=10**12, started_us=1)])
    slot = p.quiet_slot(clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + 10**9),
                        observe=lambda: next(states))
    assert slot['next_us'] == 10**12


def test_executor_closed(tmp_path):
    p = load('prereqs_m6.py', 'p')
    c = p.Context.__new__(p.Context)
    c.m = types.SimpleNamespace(ROOT=str(tmp_path/'m6'))
    assert c.executor_closed()
    (tmp_path/'m6'/'q').mkdir(parents=True)
    assert c.executor_closed()
    (tmp_path/'m6'/'q'/'preparation-pause-intent.json').write_text('{}')
    assert not c.executor_closed()
    (tmp_path/'m6'/'q'/'restored.json').write_text('{}')
    assert c.executor_closed()
    (tmp_path/'m6'/'q'/'commit-consumed.json').write_text('{}')
    assert not c.executor_closed()


def test_source_pins():
    for name in ('source_runtime.py', 'launch.py', 'metadata_executor.py'):
        assert sha(HERE/name) == sha(M5/name), name
    p = load('prereqs_m6.py', 'p')
    c = load('capture_m6.py', 'cap')
    assert p.RUNTIME_SHA == sha(HERE/'source_runtime.py')
    assert p.CLOSURE_SHA == sha(HERE/'metadata_closure.py')
    assert c.PREREQS_SHA == sha(HERE/'prereqs_m6.py')
    ours = (HERE/'record_review.py').read_text().splitlines()
    theirs = (M5/'record_review.py').read_text().splitlines()
    differing = [(a, b) for a, b in zip(ours, theirs) if a != b]
    assert len(ours) == len(theirs) and len(differing) == 5  # three docstring lines and the two paths
    assert all('m6' in a.lower() and 'm5' in b.lower() for a, b in differing)


def test_derivation_matches_constants(m):
    repo = os.environ.get('S3_DERIVE_REPO', m.TEMPLATE)
    probe = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', repo, 'cat-file', '-e',
                            m.TEMPLATE_COMMIT + '^{commit}'], capture_output=True)
    if probe.returncode != 0:
        pytest.skip('repository does not hold cfd353f3 yet (before the fetch step)')
    derived = json.loads(subprocess.run(['/usr/bin/python3', '-I', '-B', str(HERE/'derive_m6.py'), repo],
                                        capture_output=True, check=True, cwd='/').stdout)
    assert derived['parser_new'] == m.CHANGED_INPUTS[0][2]
    assert derived['worker_version_new'] == m.VERSION_NEW
    assert derived['retained_template_pins'] == {k[len(m.TEMPLATE) + 1:]: v for k, v in m.RETAINED_TEMPLATE_PINS.items()}
    assert derived['tree'] == load('prereqs_m6.py', 'p').TARGET_TREE
    cov = derived['coverage']
    assert [(i['path'], i['sha256'], i['mode']) for i in cov['inputs']] == list(m.auth_inputs())
    assert [t['path'] for t in cov['trees']] == list(m.AUTH_TREES)
    assert [(link['path'], link['target']) for link in cov['links']] == list(m.AUTH_LINKS)
