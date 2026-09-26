"""Tests for the ga-e0t1.18 sequence 15 transition package. No phase runs; run outside any Core window.

  python3 -m pytest -q designs/ga-e0t1.18-deploy/test_s2.py

Loading s2_transition.py as a module (not __main__) executes only the reviewed chain loaders and the override
definitions; it needs ROOT/deadlines.py staged (PLAN S2 step 0). The behavioural cases are ported from the
ga-e0t1.15 suite and extended for every sequence 15 rule.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
KEY = '69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f'
OLD_KEY = 'a21cc0a2fbf22c14fbe59cf508d05bcc230774f5c0d9cd386215369d43a2410a'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load():
    path = HERE/'s2_transition.py'
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


# --- generation and constants -------------------------------------------------------------------------------

def test_generator_reproduces_the_transition(tmp_path):
    out = tmp_path/'s2_transition.py'
    subprocess.run([sys.executable, '-I', '-B', str(HERE/'make_s2.py'), str(out)], check=True, capture_output=True)
    assert out.read_bytes() == (HERE/'s2_transition.py').read_bytes()


def test_identity_constants():
    text = (HERE/'s2_transition.py').read_text()
    for line in ("c.OLD='b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'",
                 "c.NEW='fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'",
                 'c.NEW_SIZE=134062284', "m['sequence']==15", "receipt['sequence']==15",
                 "commit='deefb98b2aed07875df31351d081fbac195cb1cd'", "tree='af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'",
                 "blob='e6e9ac576162bcdbde8fc05ecbb1943f55f0ce41'",
                 "receipt['before']==dict(sha256=c.OLD,size=134052980,",
                 "c.o.require(budget>240*d.SECOND,'insufficient one-shot submission budget')",
                 "S14_RECOVERY_ROOT=Path('/var/tmp/ga-e0t1.18-seq15-recovery-20260926')"):
        assert text.count(line) == 1, line


def test_artifact_and_blob():
    artifact = Path('/var/tmp/ga-e0t1.18-build-20260926/gc-a')
    assert sha(artifact) == 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
    assert artifact.stat().st_size == 134062284
    blob = subprocess.run(['git', 'hash-object', '--no-filters', str(artifact)], capture_output=True, text=True,
                          check=True).stdout.strip()
    assert blob == 'e6e9ac576162bcdbde8fc05ecbb1943f55f0ce41'


def test_inventory_is_bound_and_keyed_on_69fe9a2e():
    text = (HERE/'s2_transition.py').read_text()
    assert "S14_LINKS_TSV_SHA='%s'" % sha(HERE/'live-key-links.tsv') in text
    assert "S14_MANIFESTS_TSV_SHA='%s'" % sha(HERE/'live-key-manifests.tsv') in text
    links = [line.split('\t') for line in (HERE/'live-key-links.tsv').read_text().splitlines()]
    assert len(links) == 143 and all(KEY in t and OLD_KEY not in t for _, t in links)
    manifests = [line.split('\t') for line in (HERE/'live-key-manifests.tsv').read_text().splitlines()]
    assert len(manifests) == 9
    assert {(m[1], m[3]) for m in manifests} == {('f51ef6490bbc3ae9c595b2fe0aaf5a4d825c0db4e5edbc56c59d315e6dc3cf10',) * 2}


def test_m6_preimages_are_live():
    text = (HERE/'s2_transition.py').read_text()
    for path, pin in (('/home/loucmane/gascity/city/.gc/platform/install-manifest.json',
                       "sha256='7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb'"),
                      ('/home/loucmane/gascity/city/.gc/platform/install-receipt.json',
                       "sha256='123a01818b86f977ceabab1207c57795a3780261e39599019aa37f7609febaac'")):
        assert pin in text
        assert "sha256='%s'" % sha(path) == pin


def test_live_prior_state_matches_the_admitted_forms():
    """The live Core is OLD, the shim is a7bcaa7c and the surviving watchdog maps the prior image 69d00186."""
    assert sha('/home/loucmane/gascity/bin/gc') == 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'
    assert sha('/home/loucmane/gascity/city/.gc/scripts/gc-beads-bd.sh') == \
        'a7bcaa7cce9261b987bb766fba19db46cc7f4ae8d8b22b6d8059bb884d8788d2'
    images = []
    for pid in os.listdir('/proc'):
        if pid.isdigit():
            try:
                argv = Path('/proc', pid, 'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            if b'__gc-managed-dolt-scope-watchdog' in argv:
                images.append(sha(Path('/proc', pid, 'exe')))
    assert images == ['69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9']


def test_accepted_binding_state():
    accepted = HERE/'accepted.json'
    text = (HERE/'s2_transition.py').read_text()
    if accepted.exists():
        value = json.loads(accepted.read_text())
        assert "ACCEPTED_SHA=%r" % value['sha256'] in text and sha(value['path']) == value['sha256']
    else:
        assert "ACCEPTED_SHA='%s'" % ('0' * 64) in text


def test_watchdog_image_rule_in_source():
    text = (HERE/'s2_transition.py').read_text()
    assert ("in ('69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9',c.OLD),"
            "'surviving watchdog image is not a known prior image')") in text
    assert "==c.OLD,'surviving watchdog image is not OLD')" not in text


# --- transition behaviour -----------------------------------------------------------------------------------

BROKER = dict(MainPID='2940285', ExecMainStartTimestampMonotonic='123477220085', ActiveState='active',
              SubState='running', NRestarts='0', Result='success', UnitFileState='disabled')
SOCKET = dict(ActiveState='active', SubState='running', UnitFileState='enabled', Result='success')


def closure(core_pid, start, watchdog, server, image):
    return dict(
        host=dict(host=dict(pid=core_pid, start=start, listener=str(start)),
                  core=dict(MainPID=str(core_pid), ExecMainStartTimestampMonotonic=str(start), NRestarts='0'),
                  broker=dict(BROKER), broker_socket=dict(SOCKET), signer=dict(MainPID='2310')),
        pins={},
        scope=dict(core_members=[core_pid], reconciler_members=[], descendants=[], city_tmux_absent=True,
                   dolt_members=dict(watchdog=watchdog, server=server, watchdog_image=image,
                                     watchdog_proc=[1, 10], server_proc=[watchdog, 11])),
        cache=dict(inventory={}), trees={'/home/loucmane/gascity/home/cache/repos': dict(sha256='x')},
        suspension={}, protected={}, links={}, parents={})


def pair(s2, dolt='survived', predecessor_image='deleted-old'):
    b = closure(core_pid=2940569, start=1000, watchdog=2852, server=2867, image=predecessor_image)
    b['pins'] = {s2.c.o.GC: dict(sha256=s2.c.OLD, size=s2.c.NEW_SIZE)}
    if dolt == 'fresh':
        a = closure(core_pid=300, start=2000, watchdog=400, server=401, image='live')
        a['scope']['dolt_members']['server_proc'] = [400, 11]
    else:
        a = closure(core_pid=300, start=2000, watchdog=2852, server=2867, image='deleted-old')
    a['pins'] = {s2.c.o.GC: dict(sha256=s2.c.NEW, size=s2.c.NEW_SIZE)}
    a['admitted_cache_keys'] = []
    return b, a


@pytest.mark.parametrize('dolt', ['fresh', 'survived'])
@pytest.mark.parametrize('predecessor_image', ['live', 'deleted-old'])
def test_transition_admits_fresh_or_survived_from_either_predecessor(s2, dolt, predecessor_image):
    b, a = pair(s2, dolt, predecessor_image)
    s2.validate_successor_transition(b, a)


def test_transition_admits_unchanged_running_broker(s2):
    b, a = pair(s2)
    assert a['host']['broker'] == b['host']['broker']
    s2.validate_successor_transition(b, a)


def test_transition_admits_fresh_broker_epoch(s2):
    b, a = pair(s2)
    a['host']['broker'] = dict(BROKER, MainPID='3000000', ExecMainStartTimestampMonotonic='999999999999')
    s2.validate_successor_transition(b, a)


@pytest.mark.parametrize('case, message', [
    ('broker-pid-without-fresh-start', 'broker epoch'),
    ('broker-inactive', 'broker epoch'),
    ('broker-nrestarts', 'broker invariant NRestarts'),
    ('socket-other', 'broker socket transition'),
    ('mixed-dolt', 'neither exactly fresh nor exactly survived'),
    ('survived-changed-proc', 'neither exactly fresh nor exactly survived'),
    ('fresh-with-deleted-image', 'neither exactly fresh nor exactly survived'),
    ('predecessor-image-unknown', 'predecessor watchdog image'),
    ('stray-field', 'unexpected full-closure transition'),
    ('core-not-fresh', 'Core host epoch not fresh'),
])
def test_transition_refusals_name_their_rule(s2, case, message):
    b, a = pair(s2)
    if case == 'broker-pid-without-fresh-start':
        a['host']['broker'] = dict(BROKER, MainPID='3000000', ExecMainStartTimestampMonotonic='1')
    elif case == 'broker-inactive':
        a['host']['broker'] = dict(BROKER, ActiveState='inactive', SubState='dead', MainPID='0',
                                   ExecMainStartTimestampMonotonic='0')
    elif case == 'broker-nrestarts':
        a['host']['broker'] = dict(BROKER, NRestarts='1')
    elif case == 'socket-other':
        a['host']['broker_socket'] = dict(SOCKET, UnitFileState='disabled')
    elif case == 'mixed-dolt':
        a['scope']['dolt_members']['server'] = 999
    elif case == 'survived-changed-proc':
        a['scope']['dolt_members']['watchdog_proc'] = [1, 99]
    elif case == 'fresh-with-deleted-image':
        a['scope']['dolt_members'].update(watchdog=400, server=401, server_proc=[400, 11])
    elif case == 'predecessor-image-unknown':
        b['scope']['dolt_members']['watchdog_image'] = 'deleted-other'
    elif case == 'stray-field':
        a['host']['signer'] = dict(MainPID='9999')
    else:
        a['host']['host'] = dict(b['host']['host'])
    with pytest.raises(Exception, match=message):
        s2.validate_successor_transition(b, a)


# --- cache admission ----------------------------------------------------------------------------------------

META = dict(mode=0o40755, uid=1000, gid=1000, size=4096, nlink=3, mtime_ns=1, ctime_ns=1)


def inventory(**entries):
    return dict(inventory={k: dict(v) for k, v in entries.items()})


def test_cache_with_no_additions_is_admitted_as_empty(s2):
    before = inventory(**{'.': META, KEY: META})
    assert s2.s14_admit_cache(before, copy.deepcopy(before)) == []


@pytest.mark.parametrize('case, message', [
    ('required-key-now-unexpected', 'unexpected cache additions'),
    ('stranger', 'unexpected cache additions'),
    ('removed', 'cache entry removed'),
    ('changed', 'pre-existing cache entry changed'),
    ('root-changed-without-additions', 'cache root changed without additions'),
    ('root-mode', 'cache root metadata'),
])
def test_cache_admission_refusals(s2, case, message):
    before = inventory(**{'.': META, KEY: META})
    after = copy.deepcopy(before)
    if case == 'required-key-now-unexpected':
        after['inventory'][OLD_KEY] = META
    elif case == 'stranger':
        after['inventory']['stranger'] = META
    elif case == 'removed':
        del after['inventory'][KEY]
    elif case == 'changed':
        after['inventory'][KEY] = dict(META, ctime_ns=2)
    elif case == 'root-changed-without-additions':
        after['inventory']['.'] = dict(META, mtime_ns=9, ctime_ns=9)
    else:
        after['inventory']['.'] = dict(META, mode=0o40700)
        after['inventory']['stranger'] = META
    with pytest.raises(Exception, match=message):
        s2.s14_admit_cache(before, after)


# --- settled-scope wait -------------------------------------------------------------------------------------

def run_wait(s2, monkeypatch, outcomes, bound_ns=None):
    calls = iter(outcomes)

    def quiet_scope(host):
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value
    monkeypatch.setattr(s2.c.s, 'quiet_scope', quiet_scope)
    monkeypatch.setattr(s2.c.o, 'host_observation', lambda: {})
    monkeypatch.setattr(s2.time, 'sleep', lambda seconds: None)
    if bound_ns is not None:
        monkeypatch.setattr(s2, 'S15_SCOPE_WAIT_NS', bound_ns)
    return s2.s15_wait_scope_settled()


def test_scope_wait_needs_two_consecutive_passes_and_records_errors(s2, monkeypatch):
    result = run_wait(s2, monkeypatch, [{}, RuntimeError('supervisor scope membership'), {}, {}])
    assert result['settled'] is True and result['reads'] == 4
    assert result['errors'] == ['supervisor scope membership']


def test_scope_wait_times_out_and_refuses(s2, monkeypatch):
    clock = iter(range(0, 10**12, 60 * 10**9))
    monkeypatch.setattr(s2.time, 'monotonic_ns', lambda: next(clock))
    with pytest.raises(Exception, match='supervisor scope not settled within bound'):
        run_wait(s2, monkeypatch, [RuntimeError('residue')] * 100)


# --- recovery gate, retries and window ----------------------------------------------------------------------

def test_recovery_gate_in_source():
    text = (HERE/'s2_transition.py').read_text()
    for needle in ("terminal.get('phase') in ('submit','postflight1','postflight2')",
                   "'postflight2 already accepted; nothing to recover'",
                   "broker_result.get('returncode')==0",
                   "rec('scope-wait-%d.json'%n,s15_wait_scope_settled())",
                   "if len(sys.argv)==4 and sys.argv[1]=='recover' and __name__=='__main__':"):
        assert text.count(needle) == 1, needle


def test_main_refuses_placeholder_before_touching_root(s2):
    if s2.ACCEPTED_SHA != '0' * 64:
        pytest.skip('accepted predecessor bound')
    with pytest.raises(Exception, match='not yet bound'):
        s2.main()


def test_default_roots_without_retry(s2):
    if (HERE/'retry.json').exists():
        pytest.skip('retry in effect')
    assert str(s2.ROOT) == '/var/tmp/ga-e0t1.18-seq15-20260926'
    assert s2.ATTEMPT == 'ga-mutg-adoption-20260926-r16'
    assert str(s2.S14_ACCEPT_ROOT) == '/var/tmp/ga-e0t1.18-predecessor-20260926-r1'


def test_retry_generation(tmp_path):
    work = tmp_path/'pkg'
    work.mkdir()
    for name in ('make_s2.py', 'live-key-links.tsv', 'live-key-manifests.tsv'):
        shutil.copy2(HERE/name, work/name)
    if (HERE/'accepted.json').exists():
        shutil.copy2(HERE/'accepted.json', work/'accepted.json')
    out = tmp_path/'gen.py'
    make = work/'make_s2.py'
    text = make.read_text().replace("HERE.parent/'ga-e0t1.15-deploy'/'s2_transition.py'",
                                    'Path(%r)' % str(HERE.parent/'ga-e0t1.15-deploy'/'s2_transition.py'))
    make.write_text(text)
    (work/'retry.json').write_text('{"retry": 1, "reaccept": true}')
    subprocess.run([sys.executable, '-I', '-B', str(make), str(out)], check=True, capture_output=True)
    text = out.read_text()
    assert "ROOT=Path('/var/tmp/ga-e0t1.18-seq15-20260926-t1')" in text
    assert "ATTEMPT='ga-mutg-adoption-20260926-r17'" in text
    assert "S14_ACCEPT_ROOT=Path('/var/tmp/ga-e0t1.18-predecessor-20260926-r2')" in text
    for bad in ('{"retry": 1, "reaccept": "false"}', '{"retry": 0, "reaccept": true}'):
        (work/'retry.json').write_text(bad)
        assert subprocess.run([sys.executable, '-I', '-B', str(make), str(out)], capture_output=True).returncode != 0


def test_window_keeps_its_bounds(s2):
    start = dict(boot='00000000-0000-0000-0000-000000000000', mono=10**12, boot_time=10**12,
                 wall=1_790_000_000 * 10**9, span=1000)
    w = s2.d.build_window(start, dict(inventory={'.': {}}), 'ga-mutg-adoption-20260926-r16')
    assert w['mono_deadline'] == start['mono'] + s2.d.WINDOW
    expired = dict(start, mono=start['mono'] + s2.d.WINDOW)
    with pytest.raises(Exception, match='monotonic window expired'):
        s2.d.window_check(w, expired)
    with pytest.raises(Exception, match='attempt identity'):
        s2.d.build_window(start, dict(inventory={'.': {}}), 'other-r1')


def test_snapshot_drops_only_atime(s2, tmp_path):
    (tmp_path/'f').write_bytes(b'x')
    value = s2.c.o.tree_snapshot(str(tmp_path), cache=True)
    want = {'device', 'inode', 'uid', 'gid', 'mode', 'type', 'nlink', 'size', 'mtime_ns', 'ctime_ns'}
    for meta in value['inventory'].values():
        assert set(meta) == want
