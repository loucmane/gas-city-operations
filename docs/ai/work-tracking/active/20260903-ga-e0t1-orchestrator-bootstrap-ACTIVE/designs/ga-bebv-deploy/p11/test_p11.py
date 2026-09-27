"""Tests for the P11 worker receipt refresh (ga-bebv S3: Core f45a6262 and the M10 revision).

  python3 -m pytest -q designs/ga-bebv-deploy/p11/test_p11.py

Read-only: the installed receipt, the reviewed provisioner, the diagnostic build roots, the M10 records under
reports/m10/q, the sequence 16 build verification, and one read-only composition run of each diagnostic inside
`bwrap --ro-bind / / --unshare-net`.
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
P10 = HERE.parent.parent/'ga-e0t1.18-deploy'/'p10'
LIVE = Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json')
PROVISIONER = Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
REVISION_OLD = '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add'
REVISION = '03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712'
CORE_OLD = 'deefb98b2aed07875df31351d081fbac195cb1cd'
CORE = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE = 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'
SIGNING = 'gascity/gc.implementation-worker'
CANDIDATE = 'gascity/operations-candidate-worker'
SIGNING_DIGEST = 'ad0c695bbaa88adb6bca263900ab08d285bb970d61ae77d61b23f5490f590347'
CANDIDATE_DIGEST = 'e641dc176bc624e615b1ba42acdf0b161feeae84878ade3586311b2a5e7156aa'
COMPOSE_ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane',
                   PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', GC_HOME='/home/loucmane/gascity/home',
                   GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', LC_ALL='C.UTF-8', GODEBUG='containermaxprocs=0')
BWRAP = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--unshare-pid', '--new-session',
         '--die-with-parent', '--proc', '/proc', '--dev', '/dev', '--']
ROOTS = dict(sign='/var/tmp/ga-bebv-p11-compose-diagnostic-20260927',
             candidate='/var/tmp/ga-bebv-p11-candidate-compose-diagnostic-20260927',
             preflight='/var/tmp/ga-bebv-p11-preflight-diagnostic-20260927')


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
    return load('p11-input.py')


@pytest.fixture(scope='module')
def receipt(p):
    return json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def provisioner():
    module = types.ModuleType('reviewed_provisioner'); module.__file__ = str(PROVISIONER)
    sys.modules[module.__name__] = module
    exec(compile(PROVISIONER.read_bytes(), str(PROVISIONER), 'exec', dont_inherit=True), module.__dict__)
    return module


def test_exact_delta(p, receipt):
    """Exactly two leaves change: the permission revision and the Core member head. Both profiles are equal."""
    draft = p.derive(receipt, REVISION)
    before = dict(leaves(receipt))
    after = dict(leaves(draft))
    removed = {'/canary_runner/path', '/canary_runner/sha256', '/receipt_sha256',
               '/profiles/0/worker_profile_sha256', '/profiles/1/worker_profile_sha256'}
    assert set(before) - set(after) == removed and set(after) <= set(before)
    changed = {k for k in after if before[k] != after[k]}
    core_index = [h['name'] for h in receipt['member_heads']].index('core')
    assert changed == {'/permission_revision', '/member_heads/%d/commit' % core_index}
    assert draft['permission_revision'] == REVISION and draft['member_heads'][core_index]['commit'] == CORE
    assert receipt['permission_revision'] == REVISION_OLD and receipt['member_heads'][core_index]['commit'] == CORE_OLD
    assert [q['name'] for q in draft['profiles']] == [SIGNING, CANDIDATE] and draft['profiles'][1] == p.CANDIDATE
    assert receipt == json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def test_candidate_constant_is_p10s(p):
    assert p.CANDIDATE == load('p10-input.py', P10).CANDIDATE


@pytest.mark.parametrize('mutate', [
    lambda r: r.__setitem__('template_commit', 'x'),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'core'][0].__setitem__('commit', CORE),
    lambda r: r.__setitem__('permission_revision', REVISION),
    lambda r: r['profiles'][0]['provider'].__setitem__('version', 'x'),
    lambda r: r['profiles'][0]['argv'].__setitem__(6, 'claude-opus-5'),
    lambda r: r['profiles'][0].__setitem__('name', CANDIDATE),
    lambda r: r['profiles'][1].__setitem__('argv', r['profiles'][1]['argv'] + ['--x']),
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


def test_reviewed_provisioner_keeps_both_profile_digests(p, receipt):
    assert sha(PROVISIONER) == '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
    module = provisioner()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'draft.json'
        path.write_bytes(p.serialize(p.derive(receipt, REVISION)))
        normalized = module.load_prototype(path, receipt['canary_runner'])
    digests = [q['worker_profile_sha256'] for q in normalized['profiles']]
    assert digests == [SIGNING_DIGEST, CANDIDATE_DIGEST] == [q['worker_profile_sha256'] for q in receipt['profiles']]
    assert normalized['permission_revision'] == REVISION
    assert {h['name']: h['commit'] for h in normalized['member_heads']}['core'] == CORE


@pytest.mark.skipif(not Path('/usr/bin/bwrap').exists(), reason='bwrap required')
def test_both_profiles_are_cores_own_composition_at_f45a6262(p, receipt):
    """Both composition diagnostics, read-only and network-less, compose exactly the draft argv, PATH and revision."""
    compose = load('p11-observe-compose.py')
    draft = p.derive(receipt, REVISION)
    for build, digest, expected in ((compose.BUILD, compose.BINARY_SHA, draft['profiles'][0]),
                                    (compose.CANDIDATE_BUILD, compose.CANDIDATE_BINARY_SHA, draft['profiles'][1])):
        assert sha(build/'compose') == digest
        run = subprocess.run(BWRAP + [str(build/'compose')], env=COMPOSE_ENV, capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr
        observed = json.loads(run.stdout)
        assert observed['profile'] == expected['name'] and observed['permission_revision'] == REVISION
        assert observed['argv'] == expected['argv'] and observed['environment'] == expected['environment']


def test_diagnostic_builds_are_the_p11_builder_over_these_sources():
    make = load('make_p11.py')
    builder = sha(HERE/'prepare-compose-p11.py')
    for key, main in (('sign', HERE/'compose-main.go'), ('candidate', HERE/'candidate'/'compose-main.go')):
        record = json.loads((Path(ROOTS[key])/'build-result.json').read_bytes())
        assert record['core_commit'] == CORE and record['core_tree'] == TREE and record['builder_sha256'] == builder
        assert record['main_sha256'] == sha(main) and record['binary_sha256'] == sha(Path(ROOTS[key])/'compose')
    assert sha(HERE/'compose-main.go') == 'e8cb87a053b07ab8c8f93fd21a6a14c015b81919422ecdbec6c8c7a03201d8b3'
    assert sha(HERE/'candidate'/'compose-main.go') == sha(P10/'compose-main.go')
    assert sha(HERE/'preflight-main.go') == sha(P10/'preflight-main.go')
    root = Path(ROOTS['preflight'])
    preflight = json.loads((root/'build-result.json').read_bytes())
    extraction = json.loads((root/'extraction.json').read_bytes())
    assert preflight['core_commit'] == CORE and preflight['binary_sha256'] == sha(root/'compose') == make.PREFLIGHT_SHA
    assert extraction['source_commit'] == CORE and extraction['reviewed_builder_sha256'] == builder
    assert extraction['main_template_sha256'] == sha(HERE/'preflight-main.go')
    assert extraction['generated_main_sha256'] == preflight['main_sha256']
    assert sha(root/'extraction.json') == make.EXTRACTION_SHA
    assert (make.SIGN_COMPOSE_SHA, make.CANDIDATE_COMPOSE_SHA) == (
        sha(Path(ROOTS['sign'])/'compose'), sha(Path(ROOTS['candidate'])/'compose'))


def test_builders_differ_from_the_reviewed_ones_only_in_bindings():
    ours = (HERE/'prepare-compose-p11.py').read_text().splitlines()
    theirs = (HERE.parent.parent/'ga-e0t1.18-deploy'/'p8'/'prepare-compose-p8.py').read_text().splitlines()
    added = [line for line in ours if line not in theirs]
    # Three docstring lines are inserted (two of text and a blank one) and four bindings are replaced.
    assert len(ours) == len(theirs) + 3 and len(added) == 6
    assert all(('P11' in line or 'f45a6262' in line or 'ga-bebv' in line or 'f1011ada' in line)
               for line in added)


def test_adoption_witness_bindings(p):
    text = (HERE/'p11-adopt.py').read_text()
    assert "CORE='%s'" % CORE in text and "tree='%s'" % TREE in text
    assert "latest['controller_pid']==2800348" in text
    verification = '/var/tmp/ga-bebv-build-20260927/artifact-verification.json'
    assert "'%s','%s')" % (verification, sha(verification)) in text
    compose = (HERE/'p11-observe-compose.py').read_text()
    assert "host['core']['MainPID'] == '2800348'" in compose
    assert "host['core']['ExecMainStartTimestampMonotonic'] == '229642910742'" in compose
    assert sha(HERE.parent/'m10'/'metadata_closure.py') == load('p11-observe-compose.py').POLICY_SHA


def test_m10_acceptance_on_the_real_records(p):
    value = p.m10_acceptance()
    assert value['canonical_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
    assert value['receipt_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json')
    assert value['manifest_sha256'].startswith('f6dd60df')


def test_generator_reproduces_every_file():
    captured = {}
    make = load('make_p11.py')
    make.write = lambda name, text: captured.__setitem__(name, text.encode() if isinstance(text, str) else text) \
        or hashlib.sha256(captured[name]).hexdigest()
    make.diagnostics()
    make.scripts()
    assert set(captured) == {'compose-main.go', 'candidate/compose-main.go', 'preflight-main.go',
                             'prepare-compose-p11.py', 'prepare-compose-candidate-p11.py', 'prepare-preflight-p11.py',
                             'p11-input.py', 'p11-observe-compose.py', 'p11-readiness.py', 'p11-adopt.py',
                             'source-launch.py', 'typed-interoperability.json'}
    filled = re.compile(rb"\n(NEW_SHA|NEW_SELF|READY_RESULT_SHA|READY_BEFORE_SHA|READY_PINS_SHA)='[0-9a-f]{64}'\n")
    for name, data in captured.items():
        disk = (HERE/name).read_bytes()
        if name == 'p11-adopt.py':
            for _ in range(5):
                disk = filled.sub(lambda match: b'\n' + match.group(1) + b'=None\n', disk, count=1)
        assert disk == data, name


def test_every_generated_script_compiles():
    for name in ('p11-input.py', 'p11-observe-compose.py', 'p11-readiness.py', 'p11-adopt.py', 'prepare-compose-p11.py',
                 'prepare-compose-candidate-p11.py', 'prepare-preflight-p11.py', 'source-launch.py', 'make_p11.py'):
        compile((HERE/name).read_bytes(), name, 'exec', dont_inherit=True)


def test_adoption_constants_bind_the_readiness_evidence():
    text = (HERE/'p11-adopt.py').read_text()
    if "\nNEW_SHA=None\n" in text:
        pytest.skip('adoption constants are filled after readiness')
    ready = Path('/var/tmp/ga-bebv-p11-readiness-20260927')
    final = json.loads((ready/'receipt.final.json').read_bytes())
    for name, value in (('NEW_SHA', sha(ready/'receipt.final.json')), ('NEW_SELF', final['receipt_sha256']),
                        ('READY_RESULT_SHA', sha(ready/'result.json')), ('READY_BEFORE_SHA', sha(ready/'before.json')),
                        ('READY_PINS_SHA', sha(ready/'before.json.provider-pins'))):
        assert "\n%s='%s'\n" % (name, value) in text, name
    result = json.loads((ready/'result.json').read_bytes())
    assert result['ok'] is True and result['unchanged'] is True and result['error'] is None
    assert [q['worker_profile_sha256'] for q in final['profiles']] == [SIGNING_DIGEST, CANDIDATE_DIGEST]
    assert final['permission_revision'] == REVISION
