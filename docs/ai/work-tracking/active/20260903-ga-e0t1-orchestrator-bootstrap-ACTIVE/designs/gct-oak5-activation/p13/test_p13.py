"""Tests for the P13 worker receipt revision refresh (gct-oak5: the A2 codex-choice revision over M12).

  python3 -m pytest -q designs/gct-oak5-activation/p13/test_p13.py

Read-only: the installed receipt, the reviewed provisioner, the reused diagnostic build roots, the M12 records under
reports/m12/q, and one read-only composition run of each diagnostic inside `bwrap --ro-bind / / --unshare-net`.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types

import pytest

HERE = Path(__file__).parent
P12 = HERE.parent/'p12'
LIVE = Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json')
PROVISIONER = Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
REVISION_OLD = '06076790c31448212545edc1e741f592ed5b23ac54debbefb5e6da847143d753'
REVISION = 'a61666b33528c1cb8b497f55d9c6b8b37df2ce74ed9853345de8d7321e18f58f'
TEMPLATE = '3474abfaec255f7ea4266ce8aa35218afcfc89b0'
CORE = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE = 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'
SIGNING = 'gascity/gc.implementation-worker'
CANDIDATE = 'gascity/operations-candidate-worker'
TEMPLATE_PROFILE = 'gas-city-template/gc.implementation-worker'
DIGESTS = {SIGNING: 'ad0c695bbaa88adb6bca263900ab08d285bb970d61ae77d61b23f5490f590347',
           CANDIDATE: 'e641dc176bc624e615b1ba42acdf0b161feeae84878ade3586311b2a5e7156aa',
           TEMPLATE_PROFILE: '2341a9a0a6acf13c2a14dd9f8a6fd831d2ac4a263a78b0ba429a4e79713abfb6'}
COMPOSE_ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane',
                   PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', GC_HOME='/home/loucmane/gascity/home',
                   GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', LC_ALL='C.UTF-8', GODEBUG='containermaxprocs=0')
BWRAP = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--unshare-pid', '--new-session',
         '--die-with-parent', '--proc', '/proc', '--dev', '/dev', '--']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, root=HERE):
    path = root/name
    module = types.ModuleType(path.stem.replace('-', '_')); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def leaves(value, prefix=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, prefix + '/' + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, prefix + '/' + str(index))
    else:
        yield prefix, value


@pytest.fixture(scope='module')
def p():
    return load('p13-input.py')


@pytest.fixture(scope='module')
def receipt(p):
    return json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def provisioner():
    module = types.ModuleType('reviewed_provisioner'); module.__file__ = str(PROVISIONER)
    sys.modules[module.__name__] = module
    exec(compile(PROVISIONER.read_bytes(), str(PROVISIONER), 'exec', dont_inherit=True), module.__dict__)
    return module


def test_exact_delta(p, receipt):
    """Exactly the revision changes; the profiles are the installed ones, reordered to the P12 input order."""
    draft = p.derive(receipt, REVISION)
    assert [q['name'] for q in receipt['profiles']] == [TEMPLATE_PROFILE, SIGNING, CANDIDATE]
    assert [q['name'] for q in draft['profiles']] == [SIGNING, CANDIDATE, TEMPLATE_PROFILE]
    installed = {q['name']: {k: v for k, v in q.items() if k != 'worker_profile_sha256'} for q in receipt['profiles']}
    assert {q['name']: q for q in draft['profiles']} == installed
    top = {k for k in set(draft) | set(receipt) if draft.get(k) != receipt.get(k)}
    assert top == {'permission_revision', 'profiles', 'canary_runner', 'receipt_sha256'}
    assert 'canary_runner' not in draft and 'receipt_sha256' not in draft
    assert draft['permission_revision'] == REVISION and receipt['permission_revision'] == REVISION_OLD
    assert draft['profiles'][1] == p.CANDIDATE and draft['profiles'][2] == p.TEMPLATE_CANDIDATE
    assert receipt == json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def test_profile_constants_are_p12s(p):
    p12 = load('p12-input.py', P12)
    assert p.CANDIDATE == p12.CANDIDATE and p.TEMPLATE_CANDIDATE == p12.TEMPLATE_CANDIDATE


@pytest.mark.parametrize('mutate', [
    lambda r: r.__setitem__('template_commit', 'x'),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'template'][0].__setitem__('commit', 'x'),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'core'][0].__setitem__('commit', 'x'),
    lambda r: r.__setitem__('permission_revision', REVISION),
    lambda r: [q for q in r['profiles'] if q['name'] == SIGNING][0]['provider'].__setitem__('version', 'x'),
    lambda r: [q for q in r['profiles'] if q['name'] == SIGNING][0].__setitem__('profile_kind', 'candidate'),
    lambda r: [q for q in r['profiles'] if q['name'] == CANDIDATE][0].__setitem__('argv', ['x']),
    lambda r: [q for q in r['profiles'] if q['name'] == TEMPLATE_PROFILE][0].__setitem__('writable_roots', ['/x']),
    lambda r: r['profiles'].pop(),
    lambda r: r['profiles'].append(copy.deepcopy(r['profiles'][0])),
    lambda r: r.pop('canary_runner'),
])
def test_derive_refuses_predecessor_drift(p, receipt, mutate):
    changed = copy.deepcopy(receipt)
    mutate(changed)
    with pytest.raises((RuntimeError, KeyError, ValueError)):
        p.derive(changed, REVISION)


@pytest.mark.parametrize('revision', [REVISION_OLD, 'ab' * 32])
def test_derive_refuses_any_other_revision(p, receipt, revision):
    with pytest.raises(RuntimeError, match='revision predecessor'):
        p.derive(receipt, revision)


def test_reviewed_provisioner_keeps_all_three_profile_digests(p, receipt):
    assert sha(PROVISIONER) == '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
    module = provisioner()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'draft.json'
        path.write_bytes(p.serialize(p.derive(receipt, REVISION)))
        normalized = module.load_prototype(path, receipt['canary_runner'])
    assert {q['name']: q['worker_profile_sha256'] for q in normalized['profiles']} == DIGESTS
    assert {q['name']: q['worker_profile_sha256'] for q in receipt['profiles']} == DIGESTS
    assert normalized['permission_revision'] == REVISION
    rest = lambda r: {k: v for k, v in r.items() if k not in ('permission_revision', 'receipt_sha256')}
    assert rest(normalized) == rest(receipt)


@pytest.mark.skipif(not Path('/usr/bin/bwrap').exists(), reason='bwrap required')
def test_three_profiles_are_cores_own_composition(p, receipt):
    compose = load('p13-observe-compose.py')
    draft = p.derive(receipt, REVISION)
    for build, digest, expected in ((compose.BUILD, compose.BINARY_SHA, draft['profiles'][0]),
                                    (compose.CANDIDATE_BUILD, compose.CANDIDATE_BINARY_SHA, draft['profiles'][1]),
                                    (compose.TEMPLATE_BUILD, compose.TEMPLATE_BINARY_SHA, draft['profiles'][2])):
        assert sha(build/'compose') == digest
        run = subprocess.run(BWRAP + [str(build/'compose')], env=COMPOSE_ENV, capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr
        observed = json.loads(run.stdout)
        assert observed['profile'] == expected['name'] and observed['permission_revision'] == REVISION
        assert observed['argv'] == expected['argv'] and observed['environment'] == expected['environment']


def test_reused_diagnostics_are_p12s():
    ours, theirs = load('p13-observe-compose.py'), load('p12-observe-compose.py', P12)
    for key in ('BUILD', 'BINARY_SHA', 'CANDIDATE_BUILD', 'CANDIDATE_BINARY_SHA', 'TEMPLATE_BUILD', 'TEMPLATE_BINARY_SHA',
                'BUILDER_SHA', 'POLICY_SHA'):
        assert getattr(ours, key) == getattr(theirs, key), key
    assert sha(HERE.parent/'m12'/'metadata_closure.py') == ours.POLICY_SHA
    r13, r12 = load('p13-readiness.py'), load('p12-readiness.py', P12)
    for key in ('BUILD', 'BINARY_SHA', 'SUCCESSOR', 'LAUNCH_SHA', 'NATIVE_SHA', 'PROVISIONER_SHA', 'RUNNER_SHA'):
        assert getattr(r13, key) == getattr(r12, key), key


def test_adoption_witness_bindings():
    text = (HERE/'p13-adopt.py').read_text()
    assert "CORE='%s'" % CORE in text and "tree='%s'" % TREE in text
    assert "latest['controller_pid']==2800348" in text
    assert sha(HERE/'typed-interoperability.json') == sha(P12/'typed-interoperability.json')
    assert sha(HERE/'source-launch.py') == sha(P12/'source-launch.py')


def test_m12_acceptance_on_the_real_records(p):
    value = p.m12_acceptance()
    assert value['canonical_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
    assert value['receipt_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json')
    assert value['canonical_file_sha256'].startswith('114b4a00') and value['manifest_sha256'].startswith('3f3b51eb')
    assert value['acceptance_sha256'].startswith('fc841bf3')


def test_generator_reproduces_every_file():
    captured = {}
    make = load('make_p13.py')
    make.write = lambda name, text: captured.__setitem__(name, text.encode() if isinstance(text, str) else text) \
        or hashlib.sha256(captured[name]).hexdigest()
    make.main()
    assert set(captured) == {'p13-input.py', 'p13-observe-compose.py', 'p13-readiness.py', 'p13-adopt.py',
                             'source-launch.py', 'typed-interoperability.json'}
    filled = re.compile(rb"\n(NEW_SHA|NEW_SELF|READY_RESULT_SHA|READY_BEFORE_SHA|READY_PINS_SHA)='[0-9a-f]{64}'\n")
    for name, data in captured.items():
        disk = (HERE/name).read_bytes()
        if name == 'p13-adopt.py':
            for _ in range(5):
                disk = filled.sub(lambda match: b'\n' + match.group(1) + b'=None\n', disk, count=1)
        assert disk == data, name


def test_every_generated_script_compiles():
    for name in ('p13-input.py', 'p13-observe-compose.py', 'p13-readiness.py', 'p13-adopt.py', 'source-launch.py',
                 'make_p13.py'):
        compile((HERE/name).read_bytes(), name, 'exec', dont_inherit=True)


def test_adoption_constants_bind_the_readiness_evidence():
    text = (HERE/'p13-adopt.py').read_text()
    if "\nNEW_SHA=None\n" in text:
        pytest.skip('adoption constants are filled after readiness')
    ready = Path('/var/tmp/gct-oak5-p13-readiness-20260927')
    final = json.loads((ready/'receipt.final.json').read_bytes())
    for name, value in (('NEW_SHA', sha(ready/'receipt.final.json')), ('NEW_SELF', final['receipt_sha256']),
                        ('READY_RESULT_SHA', sha(ready/'result.json')), ('READY_BEFORE_SHA', sha(ready/'before.json')),
                        ('READY_PINS_SHA', sha(ready/'before.json.provider-pins'))):
        assert "\n%s='%s'\n" % (name, value) in text, name
    result = json.loads((ready/'result.json').read_bytes())
    assert result['ok'] is True and result['unchanged'] is True and result['error'] is None
    assert {q['name']: q['worker_profile_sha256'] for q in final['profiles']} == DIGESTS
    assert final['permission_revision'] == REVISION and final['template_commit'] == TEMPLATE
