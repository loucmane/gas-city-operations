"""Offline tests for the ga-e0t1.15 S2 package. No phase runs and nothing live is touched.

Loading s2_transition.py as a module (not __main__) executes only the reviewed chain loaders and the
override definitions.
"""
import copy
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).parent


def load():
    path = HERE / 's2_transition.py'
    module = types.ModuleType('s2_under_test')
    module.__file__ = str(path)
    saved = sys.argv
    sys.argv = ['pytest']
    try:
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    finally:
        sys.argv = saved
    return module


@pytest.fixture(scope='module')
def s2():
    return load()


def test_generated_file_equals_generator_output(tmp_path):
    out = tmp_path / 'generated.py'
    subprocess.run([sys.executable, '-I', '-B', str(HERE / 'make_s2.py'), str(out)], check=True,
                   capture_output=True)
    assert out.read_bytes() == (HERE / 's2_transition.py').read_bytes()


def test_marker_bytes_match_expectation(s2):
    files = {f['Path']: f for f in json.loads(Path(s2.S14_EXPECTATION).read_bytes())['new']['materialized_files']}
    marker = s2.s14_marker('f895c0ff47d6ee9334ed282a416387eb5b084d24')
    want = files['.gc-bundled-pack-cache.toml']
    assert len(marker) == want['Size'] and hashlib.sha256(marker).hexdigest() == want['SHA256']
    assert len(s2.s14_marker('3b3b89f2011e06d84459aa7bea1552382f13930a')) == want['Size']


def closure(core_pid, start, watchdog, server, image, broker_active):
    broker = (dict(MainPID='4242', ExecMainStartTimestampMonotonic='900', ActiveState='active',
                   SubState='running', NRestarts='0', Result='success', UnitFileState='disabled')
              if broker_active else
              dict(MainPID='0', ExecMainStartTimestampMonotonic='0', ActiveState='inactive',
                   SubState='dead', NRestarts='0', Result='success', UnitFileState='disabled'))
    return dict(
        host=dict(host=dict(pid=core_pid, start=start, listener=str(start)),
                  core=dict(MainPID=str(core_pid), ExecMainStartTimestampMonotonic=str(start), NRestarts='0'),
                  broker=broker,
                  broker_socket=dict(ActiveState='active', SubState='listening' if not broker_active else 'running',
                                     UnitFileState='enabled', Result='success'),
                  signer=dict(MainPID='5550')),
        pins={'/home/loucmane/gascity/bin/gc': dict(sha256='old', size=1)},
        scope=dict(core_members=[core_pid], reconciler_members=[], descendants=[], city_tmux_absent=True,
                   dolt_members=dict(watchdog=watchdog, server=server, watchdog_image=image,
                                     watchdog_proc=[1, 10], server_proc=[watchdog, 11])),
        cache=dict(inventory={}), trees={'/home/loucmane/gascity/home/cache/repos': dict(sha256='x')},
        suspension={}, protected={}, links={}, parents={})


def after_of(s2, before, **kw):
    after = closure(**kw)
    after['pins'] = {s2.c.o.GC: dict(sha256=s2.c.NEW, size=s2.c.NEW_SIZE)}
    after['admitted_cache_keys'] = [s2.S14_NEW_KEY]
    return after


def base(s2):
    b = closure(core_pid=100, start=1000, watchdog=200, server=201, image='live', broker_active=False)
    b['pins'] = {s2.c.o.GC: dict(sha256=s2.c.OLD, size=1)}
    return b


@pytest.mark.parametrize('dolt', ['fresh', 'survived'])
def test_transition_admits_exactly_fresh_or_survived_dolt(s2, dolt):
    b = base(s2)
    kw = dict(core_pid=300, start=2000, broker_active=True)
    if dolt == 'fresh':
        kw.update(watchdog=400, server=401, image='live')
    else:
        kw.update(watchdog=200, server=201, image='deleted-old')
    a = after_of(s2, b, **kw)
    if dolt == 'fresh':
        a['scope']['dolt_members']['server_proc'] = [400, 11]
    a['pins'][s2.c.o.GC]['size'] = s2.c.NEW_SIZE
    b['pins'][s2.c.o.GC]['size'] = s2.c.NEW_SIZE
    s2.validate_successor_transition(b, a)


@pytest.mark.parametrize('case', ['mixed-dolt', 'broker-unchanged', 'socket-other', 'stray-field'])
def test_transition_refuses_everything_else(s2, case):
    b = base(s2)
    b['pins'][s2.c.o.GC]['size'] = s2.c.NEW_SIZE
    a = after_of(s2, b, core_pid=300, start=2000, watchdog=400, server=401, image='live', broker_active=True)
    a['scope']['dolt_members']['server_proc'] = [400, 11]
    if case == 'mixed-dolt':
        a['scope']['dolt_members']['server'] = 201
    elif case == 'broker-unchanged':
        a['host']['broker'] = copy.deepcopy(b['host']['broker'])
    elif case == 'socket-other':
        a['host']['broker_socket']['UnitFileState'] = 'disabled'
    else:
        a['host']['signer'] = dict(MainPID='9999')
    with pytest.raises(Exception):
        s2.validate_successor_transition(b, a)


def test_main_refuses_placeholder_before_touching_root(s2):
    if s2.ACCEPTED_SHA != '0' * 64:
        pytest.skip('accepted predecessor bound')
    with pytest.raises(Exception, match='not yet bound'):
        s2.main()


def fresh_pair(s2):
    b = base(s2)
    b['pins'][s2.c.o.GC]['size'] = s2.c.NEW_SIZE
    a = after_of(s2, b, core_pid=300, start=2000, watchdog=400, server=401, image='live', broker_active=True)
    a['scope']['dolt_members']['server_proc'] = [400, 11]
    return b, a


@pytest.mark.parametrize('case, message', [
    ('fresh-with-deleted-image', 'neither exactly fresh nor exactly survived'),
    ('survived-changed-proc', 'neither exactly fresh nor exactly survived'),
    ('predecessor-not-live', 'predecessor watchdog not live'),
    ('socket-running-to-listening', 'broker socket transition'),
    ('broker-nrestarts', 'broker invariant NRestarts'),
])
def test_transition_refusals_name_their_rule(s2, case, message):
    b, a = fresh_pair(s2)
    if case == 'fresh-with-deleted-image':
        a['scope']['dolt_members']['watchdog_image'] = 'deleted-old'
    elif case == 'survived-changed-proc':
        a['scope']['dolt_members'].update(watchdog=200, server=201, watchdog_image='deleted-old',
                                          watchdog_proc=[1, 99], server_proc=[200, 11])
    elif case == 'predecessor-not-live':
        b['scope']['dolt_members']['watchdog_image'] = 'deleted-old'
    elif case == 'socket-running-to-listening':
        b['host']['broker_socket']['SubState'] = 'running'
        a['host']['broker_socket']['SubState'] = 'listening'
    else:
        a['host']['broker']['NRestarts'] = '1'
    with pytest.raises(Exception, match=message):
        s2.validate_successor_transition(b, a)


def inventory(**entries):
    return dict(inventory={k: dict(v) for k, v in entries.items()})


META = dict(mode=0o40755, uid=1000, gid=1000, size=4096, nlink=3, mtime_ns=1, ctime_ns=1, atime_ns=5)


@pytest.mark.parametrize('case, message', [
    ('removed', 'cache entry removed'),
    ('changed', 'pre-existing cache entry changed'),
    ('unexpected-top', 'unexpected cache additions'),
    ('missing-required', 'unexpected cache additions'),
    ('root-mode', 'cache root metadata'),
])
def test_cache_admission_refusals_before_any_walk(s2, case, message):
    before = inventory(**{'.': META, 'a21': META})
    after = inventory(**{'.': dict(META, mtime_ns=9, ctime_ns=9, nlink=4, atime_ns=9), 'a21': META,
                         s2.S14_NEW_KEY: META})
    if case == 'removed':
        del after['inventory']['a21']
    elif case == 'changed':
        after['inventory']['a21'] = dict(META, atime_ns=6)
    elif case == 'unexpected-top':
        after['inventory']['stranger'] = META
    elif case == 'missing-required':
        del after['inventory'][s2.S14_NEW_KEY]
        after['inventory'][s2.S14_OPTIONAL_KEY] = META
        after['inventory']['stranger'] = META
    else:
        after['inventory']['.']['mode'] = 0o40700
    with pytest.raises(Exception, match=message):
        s2.s14_admit_cache(before, after)


def test_missing_required_key_alone_refuses(s2):
    before = inventory(**{'.': META})
    after = inventory(**{'.': META, s2.S14_OPTIONAL_KEY: META})
    with pytest.raises(Exception, match='unexpected cache additions'):
        s2.s14_admit_cache(before, after)


def test_default_roots_without_retry(s2):
    # freshen_cache.py is unused since r4, so its root coupling is not tested. Without retry.json
    # the generator keeps the first-attempt roots.
    if (HERE / 'retry.json').exists():
        pytest.skip('retry in effect')
    assert str(s2.ROOT) == '/var/tmp/ga-e0t1.15-seq14-20260925'
    assert s2.ATTEMPT == 'ga-mutg-adoption-20260925-r14'


def test_accept_preconditions_are_exact_in_source():
    text = (HERE / 's2_overrides.py.txt').read_text()
    for needle in ("'accepted broker is not exactly inactive'", "'accepted broker socket is not listening'",
                   "'accepted watchdog image is not live'", "ActiveState='inactive',SubState='dead'"):
        assert needle in text


def test_snapshot_drops_only_atime(s2, tmp_path):
    (tmp_path / 'f').write_bytes(b'x')
    value = s2.c.o.tree_snapshot(str(tmp_path), cache=True)
    want = {'device', 'inode', 'uid', 'gid', 'mode', 'type', 'nlink', 'size', 'mtime_ns', 'ctime_ns'}
    for meta in value['inventory'].values():
        assert set(meta) == want
    assert set(s2.c.o.metadata((tmp_path / 'f').stat())) == want


def test_history_check_ignores_atime_but_not_ctime(s2):
    a = inventory(**{'.': META, 'x': META})
    b = inventory(**{'.': dict(META, atime_ns=99), 'x': META})
    assert s2.r4.history_check(a, b) == {}
    c = inventory(**{'.': META, 'x': dict(META, ctime_ns=2)})
    with pytest.raises(Exception, match='historical cache content/authority mismatch'):
        s2.r4.history_check(a, c)


def test_window_keeps_its_bounds(s2):
    start = dict(boot='00000000-0000-0000-0000-000000000000', mono=10**12, boot_time=10**12,
                 wall=1_790_000_000 * 10**9, span=1000)
    w = s2.d.build_window(start, dict(inventory={'.': {}}), 'ga-mutg-adoption-20260925-r14')
    assert w['mono_deadline'] == start['mono'] + s2.d.WINDOW
    assert w['renewal'] == start['wall'] + s2.d.DAY and w['max_atime'] == 1
    assert w['boot_deadline'] == start['boot_time'] - start['span'] + s2.d.WINDOW
    later = dict(start, mono=start['mono'] + 5 * 10**9, boot_time=start['boot_time'] + 5 * 10**9,
                 wall=start['wall'] - 30 * 10**9)
    s2.d.window_check(w, later)  # a backward wall-clock step no longer refuses
    expired = dict(later, mono=start['mono'] + s2.d.WINDOW)
    with pytest.raises(Exception, match='monotonic window expired'):
        s2.d.window_check(w, expired)
    with pytest.raises(Exception, match='attempt identity'):
        s2.d.build_window(start, dict(inventory={'.': {}}), 'other-r1')


def test_retry_generation(tmp_path):
    import shutil
    work = tmp_path / 'pkg'
    work.mkdir()
    for name in ('make_s2.py', 's2_overrides.py.txt'):
        shutil.copy2(HERE / name, work / name)
    if (HERE / 'accepted.json').exists():
        shutil.copy2(HERE / 'accepted.json', work / 'accepted.json')
    (work / 'retry.json').write_text('{"retry": 1, "reaccept": true}')
    out = tmp_path / 'gen.py'
    subprocess.run([sys.executable, '-I', '-B', str(work / 'make_s2.py'), str(out)], check=True, capture_output=True)
    text = out.read_text()
    assert "ROOT=Path('/var/tmp/ga-e0t1.15-seq14-20260925-t1')" in text
    assert "ATTEMPT='ga-mutg-adoption-20260925-r15'" in text
    assert "S14_ACCEPT_ROOT=Path('/var/tmp/ga-e0t1.15-predecessor-20260925-r3')" in text
    for bad in ('{"retry": 1, "reaccept": "false"}', '{"retry": 0, "reaccept": true}'):
        (work / 'retry.json').write_text(bad)
        assert subprocess.run([sys.executable, '-I', '-B', str(work / 'make_s2.py'), str(out)],
                              capture_output=True).returncode != 0


def test_sink_alias_is_exact(s2):
    assert s2.S14_SINK_ALIASES == {'/home/loucmane/gascity/city/rigs/gascity/.agents/skills': '../.claude/skills'}
