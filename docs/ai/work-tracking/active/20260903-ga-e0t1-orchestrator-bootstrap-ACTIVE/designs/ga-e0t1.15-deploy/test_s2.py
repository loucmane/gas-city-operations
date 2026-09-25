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
    before = (HERE / 's2_transition.py').read_bytes()
    subprocess.run([sys.executable, '-I', '-B', str(HERE / 'make_s2.py')], check=True, capture_output=True)
    assert (HERE / 's2_transition.py').read_bytes() == before


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
