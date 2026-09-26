"""Tests for the P10 typed candidate receipt refresh (the first candidate window's RECEIPT stage).

  python3 -m pytest -q designs/ga-e0t1.18-deploy/p10/test_p10.py

Read-only: the installed receipt, the reviewed provisioner, the diagnostic build roots, the M9 records under
reports/m9/q once they exist, and one read-only composition run of each diagnostic inside
`bwrap --ro-bind / / --unshare-net`.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types

import pytest

HERE = Path(__file__).parent
LIVE = Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json')
PROVISIONER = Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
REVISION = '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add'
CORE = 'deefb98b2aed07875df31351d081fbac195cb1cd'
SIGNING = 'gascity/gc.implementation-worker'
CANDIDATE = 'gascity/operations-candidate-worker'
SIGNING_DIGEST = 'ad0c695bbaa88adb6bca263900ab08d285bb970d61ae77d61b23f5490f590347'
COMPOSE_ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane',
                   PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', GC_HOME='/home/loucmane/gascity/home',
                   GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', LC_ALL='C.UTF-8', GODEBUG='containermaxprocs=0')
BWRAP = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--unshare-pid', '--new-session',
         '--die-with-parent', '--proc', '/proc', '--dev', '/dev', '--']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, extra=None):
    path = HERE/name
    module = types.ModuleType(path.stem.replace('-', '_')); module.__file__ = str(path)
    module.__dict__.update(extra or {})
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
    return load('p10-input.py')


@pytest.fixture(scope='module')
def receipt(p):
    return json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def provisioner():
    module = types.ModuleType('reviewed_provisioner'); module.__file__ = str(PROVISIONER)
    sys.modules[module.__name__] = module
    exec(compile(PROVISIONER.read_bytes(), str(PROVISIONER), 'exec', dont_inherit=True), module.__dict__)
    return module


def test_exact_delta(p, receipt):
    """Exactly one change: the typed candidate profile is appended. The signing profile and the rest are equal."""
    draft = p.derive(receipt, REVISION)
    assert [q['name'] for q in draft['profiles']] == [SIGNING, CANDIDATE]
    assert draft['profiles'][1] == p.CANDIDATE
    before = dict(leaves(receipt))
    after = dict(leaves({k: v for k, v in draft.items() if k != 'profiles'}))
    after.update(dict(leaves({'profiles': draft['profiles'][:1]})))
    removed = {'/canary_runner/path', '/canary_runner/sha256', '/receipt_sha256', '/profiles/0/worker_profile_sha256'}
    assert set(before) - set(after) == removed and set(after) <= set(before)
    assert {k for k in after if before[k] != after[k]} == set()
    heads = {h['name']: h['commit'] for h in draft['member_heads']}
    assert heads['core'] == CORE and heads['template'] == draft['template_commit'] == p.TEMPLATE
    assert draft['permission_revision'] == REVISION
    assert receipt == json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def test_candidate_profile_is_typed_no_sign_and_bound(p):
    c = p.CANDIDATE
    assert c['name'] == CANDIDATE and c['profile_kind'] == 'candidate' and c['signer_identity'] == 'none'
    assert c['argv'].count(c['control_policy']['path']) == 1 and c['argv'][0] == c['provider']['path']
    assert all(not c['control_policy']['path'].startswith(root + '/') for root in c['writable_roots'])
    assert c['control_policy']['sha256'] == sha(c['control_policy']['path'])
    assert c['provider']['sha256'] == sha(c['provider']['path'])
    assert c['toolchains'][0]['executable']['sha256'] == sha('/usr/bin/python3.12')
    assert c['check_path']['sha256'] == sha(c['check_path']['path'])
    registry = json.loads(Path('/home/loucmane/gascity/city/managed/rig-permissions.json').read_bytes())
    record = [r for r in registry['rigs'] if r.get('agents') == ['operations-candidate-worker']][0]
    assert record['environment'] == c['environment'] and record['worktree_root'] == c['writable_roots'][0]
    assert [t['name'] for t in record['toolchains']] == [t['name'] for t in c['toolchains']]
    assert record['toolchains'][0]['executable'] == c['toolchains'][0]['executable']


def test_candidate_provider_is_the_m9_pin(p):
    module = types.ModuleType('m9'); module.__file__ = str(HERE.parent/'m9'/'manifest_candidate.py')
    exec(compile((HERE.parent/'m9'/'manifest_candidate.py').read_bytes(), module.__file__, 'exec',
                 dont_inherit=True), module.__dict__)
    assert p.CANDIDATE['provider'] == module.PROVIDER


@pytest.mark.parametrize('mutate', [
    lambda r: r.__setitem__('template_commit', 'x'),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'core'][0].__setitem__('commit', 'x'),
    lambda r: r.__setitem__('permission_revision', 'ab' * 32),
    lambda r: r['profiles'][0]['provider'].__setitem__('version', 'x'),
    lambda r: r['profiles'][0]['argv'].__setitem__(6, 'claude-opus-5'),
    lambda r: r['profiles'][0].__setitem__('name', CANDIDATE),
    lambda r: r['profiles'][0].__setitem__('check_path', dict(path='/x', sha256='0' * 64)),
    lambda r: r['profiles'].append(copy.deepcopy(r['profiles'][0])),
    lambda r: r.pop('canary_runner'),
])
def test_derive_refuses_predecessor_drift(p, receipt, mutate):
    changed = copy.deepcopy(receipt)
    mutate(changed)
    with pytest.raises((RuntimeError, KeyError)):
        p.derive(changed, REVISION)


@pytest.mark.parametrize('revision', ['2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2', 'ab' * 32])
def test_derive_refuses_a_moved_revision(p, receipt, revision):
    with pytest.raises(RuntimeError, match='revision unchanged'):
        p.derive(receipt, revision)


def test_reviewed_provisioner_accepts_both_profiles_and_keeps_the_signing_digest(p, receipt):
    assert sha(PROVISIONER) == '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
    module = provisioner()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'draft.json'
        path.write_bytes(p.serialize(p.derive(receipt, REVISION)))
        normalized = module.load_prototype(path, receipt['canary_runner'])
    profiles = {q['name']: q for q in normalized['profiles']}
    assert list(profiles) == [SIGNING, CANDIDATE]
    assert profiles[SIGNING]['worker_profile_sha256'] == SIGNING_DIGEST == receipt['profiles'][0]['worker_profile_sha256']
    assert profiles[CANDIDATE]['profile_kind'] == 'candidate' and profiles[CANDIDATE]['signer_identity'] == 'none'
    assert normalized['permission_revision'] == REVISION


def test_provisioner_refuses_a_candidate_with_a_signer(p, receipt):
    module = provisioner()
    draft = p.derive(receipt, REVISION)
    draft['profiles'][1]['signer_identity'] = receipt['profiles'][0]['signer_identity']
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'draft.json'
        path.write_bytes(p.serialize(draft))
        with pytest.raises(module.ProvisionError, match='candidate'):
            module.load_prototype(path, receipt['canary_runner'])


@pytest.mark.skipif(not Path('/usr/bin/bwrap').exists(), reason='bwrap required')
def test_the_candidate_profile_is_cores_own_composition(p):
    """The candidate composition diagnostic, read-only and network-less, composes exactly the draft argv and PATH."""
    compose = load('p10-observe-compose.py')
    for build, digest, name in ((compose.BUILD, compose.BINARY_SHA, SIGNING),
                                (compose.CANDIDATE_BUILD, compose.CANDIDATE_BINARY_SHA, CANDIDATE)):
        assert sha(build/'compose') == digest
        run = subprocess.run(BWRAP + [str(build/'compose')], env=COMPOSE_ENV, capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr
        observed = json.loads(run.stdout)
        assert observed['profile'] == name and observed['permission_revision'] == REVISION
        expected = p.CANDIDATE if name == CANDIDATE else json.loads(LIVE.read_bytes())['profiles'][0]
        if name == CANDIDATE or sha(LIVE) == p.RECEIPT_OLD_SHA:
            assert observed['argv'] == expected['argv'] and observed['environment'] == expected['environment']


def test_diagnostic_builds_are_the_reviewed_builder_over_these_sources():
    compose = json.loads(Path('/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926/build-result.json').read_bytes())
    assert compose['core_commit'] == CORE and compose['builder_sha256'] == '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4'
    assert compose['main_sha256'] == sha(HERE/'compose-main.go')
    assert compose['binary_sha256'] == sha('/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926/compose')
    root = Path('/var/tmp/ga-e0t1.18-p10-preflight-diagnostic-20260926')
    preflight = json.loads((root/'build-result.json').read_bytes())
    extraction = json.loads((root/'extraction.json').read_bytes())
    assert preflight['core_commit'] == CORE and preflight['binary_sha256'] == sha(root/'compose')
    assert extraction['main_template_sha256'] == sha(HERE/'preflight-main.go')
    assert extraction['reviewed_builder_sha256'] == '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4'
    assert extraction['generated_main_sha256'] == preflight['main_sha256']
    readiness = (HERE/'p10-readiness.py').read_text()
    assert "BINARY_SHA='%s'" % sha(root/'compose') in readiness
    assert "'%s')" % sha(root/'extraction.json') in readiness


def test_generator_reproduces_every_file():
    captured = {}
    make = load('make_p10.py')
    make.write = lambda name, text: captured.__setitem__(name, text.encode() if isinstance(text, str) else text) \
        or hashlib.sha256(captured[name]).hexdigest()
    make.diagnostics()
    make.scripts()
    assert set(captured) == {'compose-main.go', 'preflight-main.go', 'prepare-compose-p10.py', 'prepare-preflight-p10.py',
                             'p10-input.py', 'p10-observe-compose.py', 'p10-readiness.py', 'p10-adopt.py',
                             'source-launch.py', 'typed-interoperability.json'}
    filled = re.compile(rb"\n(NEW_SHA|NEW_SELF|READY_RESULT_SHA|READY_BEFORE_SHA|READY_PINS_SHA)='[0-9a-f]{64}'\n")
    for name, data in captured.items():
        disk = (HERE/name).read_bytes()
        if name == 'p10-adopt.py':
            before = disk
            for _ in range(5):
                disk = filled.sub(lambda match: b'\n' + match.group(1) + b'=None\n', disk, count=1)
            assert before.count(b"='") - disk.count(b"='") in (0, 5)
        assert disk == data, name


def test_every_generated_script_compiles():
    for name in ('p10-input.py', 'p10-observe-compose.py', 'p10-readiness.py', 'p10-adopt.py',
                 'prepare-compose-p10.py', 'prepare-preflight-p10.py', 'source-launch.py', 'make_p10.py'):
        compile((HERE/name).read_bytes(), name, 'exec', dont_inherit=True)


def test_m9_acceptance_on_the_real_records(p):
    if not (Path(str(p.M9))/'restored.json').exists():
        pytest.skip('M9 is accepted before P10 runs')
    value = p.m9_acceptance()
    assert value['canonical_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
    assert value['receipt_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json')


def test_adoption_constants_bind_the_readiness_evidence():
    text = (HERE/'p10-adopt.py').read_text()
    if "\nNEW_SHA=None\n" in text:
        pytest.skip('adoption constants are filled after readiness')
    ready = Path('/var/tmp/ga-e0t1.18-p10-readiness-20260926')
    final = json.loads((ready/'receipt.final.json').read_bytes())
    for name, value in (('NEW_SHA', sha(ready/'receipt.final.json')), ('NEW_SELF', final['receipt_sha256']),
                        ('READY_RESULT_SHA', sha(ready/'result.json')), ('READY_BEFORE_SHA', sha(ready/'before.json')),
                        ('READY_PINS_SHA', sha(ready/'before.json.provider-pins'))):
        assert "\n%s='%s'\n" % (name, value) in text, name
    result = json.loads((ready/'result.json').read_bytes())
    assert result['ok'] is True and result['unchanged'] is True and result['error'] is None
    assert [q['name'] for q in final['profiles']] == [SIGNING, CANDIDATE]
    # The signing lane is byte-for-byte unchanged in the evidence the adoption installs (r1 review A should_fix 2).
    assert final['profiles'][0]['worker_profile_sha256'] == SIGNING_DIGEST
    live = json.loads(LIVE.read_bytes())
    assert final['profiles'][0] == live['profiles'][0] or sha(LIVE) == sha(ready/'receipt.final.json')
