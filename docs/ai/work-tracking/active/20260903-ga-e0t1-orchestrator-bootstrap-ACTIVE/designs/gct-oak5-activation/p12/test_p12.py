"""Tests for the P12 worker receipt refresh (gct-oak5: the Template candidate lane and the M11 revision).

  python3 -m pytest -q designs/gct-oak5-activation/p12/test_p12.py

Read-only: the installed receipt, the reviewed provisioner, the diagnostic build roots, the M11 records under
reports/m11/q, and one read-only composition run of each diagnostic inside `bwrap --ro-bind / / --unshare-net`.
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
P11 = HERE.parent.parent/'ga-bebv-deploy'/'p11'
LIVE = Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json')
PROVISIONER = Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
REVISION_OLD = '03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712'
REVISION = '06076790c31448212545edc1e741f592ed5b23ac54debbefb5e6da847143d753'
TEMPLATE_OLD = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
TEMPLATE = '3474abfaec255f7ea4266ce8aa35218afcfc89b0'
CORE = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE = 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'
SIGNING = 'gascity/gc.implementation-worker'
CANDIDATE = 'gascity/operations-candidate-worker'
TEMPLATE_PROFILE = 'gas-city-template/gc.implementation-worker'
SIGNING_DIGEST = 'ad0c695bbaa88adb6bca263900ab08d285bb970d61ae77d61b23f5490f590347'
CANDIDATE_DIGEST = 'e641dc176bc624e615b1ba42acdf0b161feeae84878ade3586311b2a5e7156aa'
COMPOSE_ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane',
                   PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', GC_HOME='/home/loucmane/gascity/home',
                   GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', LC_ALL='C.UTF-8', GODEBUG='containermaxprocs=0')
BWRAP = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--unshare-pid', '--new-session',
         '--die-with-parent', '--proc', '/proc', '--dev', '/dev', '--']
TEMPLATE_BUILD = Path('/var/tmp/gct-oak5-p12-template-compose-diagnostic-20260927')


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
    return load('p12-input.py')


@pytest.fixture(scope='module')
def receipt(p):
    return json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def provisioner():
    module = types.ModuleType('reviewed_provisioner'); module.__file__ = str(PROVISIONER)
    sys.modules[module.__name__] = module
    exec(compile(PROVISIONER.read_bytes(), str(PROVISIONER), 'exec', dont_inherit=True), module.__dict__)
    return module


def test_exact_delta(p, receipt):
    """Three leaves change and one profile is appended; the two existing profiles are equal."""
    draft = p.derive(receipt, REVISION)
    before = dict(leaves(receipt))
    after = dict(leaves(draft))
    removed = {'/canary_runner/path', '/canary_runner/sha256', '/receipt_sha256',
               '/profiles/0/worker_profile_sha256', '/profiles/1/worker_profile_sha256'}
    assert set(before) - set(after) == removed
    added = {k for k in after if k not in before}
    assert added and all(k.startswith('/profiles/2/') for k in added)
    changed = {k for k in after if k in before and before[k] != after[k]}
    template_index = [h['name'] for h in receipt['member_heads']].index('template')
    assert changed == {'/permission_revision', '/template_commit', '/member_heads/%d/commit' % template_index}
    assert draft['permission_revision'] == REVISION and receipt['permission_revision'] == REVISION_OLD
    assert draft['template_commit'] == TEMPLATE and receipt['template_commit'] == TEMPLATE_OLD
    assert draft['member_heads'][template_index]['commit'] == TEMPLATE
    assert [q['name'] for q in draft['profiles']] == [SIGNING, CANDIDATE, TEMPLATE_PROFILE]
    assert draft['profiles'][1] == p.CANDIDATE and draft['profiles'][2] == p.TEMPLATE_CANDIDATE
    assert receipt == json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def test_candidate_constant_is_p11s(p):
    assert p.CANDIDATE == load('p11-input.py', P11).CANDIDATE


def test_template_profile_binds_live_files(p):
    t = p.TEMPLATE_CANDIDATE
    assert sha(t['provider']['path']) == t['provider']['sha256']
    assert sha(t['control_policy']['path']) == t['control_policy']['sha256']
    assert sha(t['check_path']['path']) == t['check_path']['sha256']
    assert t['toolchains'] == p.CANDIDATE['toolchains'] and t['check_path'] == p.CANDIDATE['check_path']
    assert Path(t['writable_roots'][0]).is_dir() and t['argv'][t['argv'].index('--add-dir') + 1] == t['writable_roots'][0]
    policy = json.loads(Path(t['control_policy']['path']).read_bytes())
    reference = json.loads(Path(p.CANDIDATE['control_policy']['path']).read_bytes())
    assert policy['sandbox'] == reference['sandbox'] and len(policy['sandbox']['excludedCommands']) == 5
    manifest = (HERE.parent/'m11'/'manifest_candidate.py').read_text()
    assert "WRAPPER_SHA = '%s'" % t['provider']['sha256'] in manifest
    assert t['provider']['version'].split('dependencies_sha256=')[1] in manifest


@pytest.mark.parametrize('mutate', [
    lambda r: r.__setitem__('template_commit', TEMPLATE),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'template'][0].__setitem__('commit', TEMPLATE),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'core'][0].__setitem__('commit', 'x'),
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


def test_reviewed_provisioner_keeps_both_existing_profile_digests(p, receipt):
    assert sha(PROVISIONER) == '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
    module = provisioner()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'draft.json'
        path.write_bytes(p.serialize(p.derive(receipt, REVISION)))
        normalized = module.load_prototype(path, receipt['canary_runner'])
    # The provisioner sorts profiles by name, so the Template profile ('gas-city-template/...') comes first.
    assert [q['name'] for q in normalized['profiles']] == [TEMPLATE_PROFILE, SIGNING, CANDIDATE]
    digests = {q['name']: q['worker_profile_sha256'] for q in normalized['profiles']}
    assert [digests[SIGNING], digests[CANDIDATE]] == [SIGNING_DIGEST, CANDIDATE_DIGEST] == [
        q['worker_profile_sha256'] for q in receipt['profiles']]
    assert re.fullmatch('[0-9a-f]{64}', digests[TEMPLATE_PROFILE])
    assert digests[TEMPLATE_PROFILE] not in (SIGNING_DIGEST, CANDIDATE_DIGEST)
    assert normalized['permission_revision'] == REVISION and normalized['template_commit'] == TEMPLATE
    assert {h['name']: h['commit'] for h in normalized['member_heads']} == {
        h['name']: (TEMPLATE if h['name'] == 'template' else h['commit']) for h in receipt['member_heads']}


@pytest.mark.skipif(not Path('/usr/bin/bwrap').exists(), reason='bwrap required')
def test_three_profiles_are_cores_own_composition_at_f45a6262(p, receipt):
    """The three composition diagnostics, read-only and network-less, compose exactly the draft argv, PATH and revision."""
    compose = load('p12-observe-compose.py')
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


def test_template_diagnostic_is_the_p11_builder_over_this_source():
    make = load('make_p12.py')
    record = json.loads((TEMPLATE_BUILD/'build-result.json').read_bytes())
    assert record['core_commit'] == CORE and record['core_tree'] == TREE
    assert record['builder_sha256'] == sha(P11/'prepare-compose-p11.py') == make.P11_BUILDER_SHA
    assert record['builder_sha256'] == load('p12-observe-compose.py').BUILDER_SHA
    assert record['main_sha256'] == sha(HERE/'template'/'compose-main.go')
    assert record['binary_sha256'] == sha(TEMPLATE_BUILD/'compose') == make.TEMPLATE_COMPOSE_SHA
    ours = (HERE/'template'/'compose-main.go').read_text().splitlines()
    theirs = (P11/'candidate'/'compose-main.go').read_text().splitlines()
    assert len(ours) == len(theirs) + 1
    assert [line for line in ours if line not in theirs] == [
        '// P12: the same composition for the Template candidate identity and provider (make_p12.py).',
        'const target = "gas-city-template/gc.implementation-worker"',
        ' if p.BuiltinAncestor != "claude" || p.Name != "claude-template-candidate" {']


def test_reused_p11_diagnostics_are_unchanged():
    compose = load('p12-observe-compose.py')
    ready = load('p12-readiness.py')
    for build, digest in ((compose.BUILD, compose.BINARY_SHA), (compose.CANDIDATE_BUILD, compose.CANDIDATE_BINARY_SHA),
                          (ready.BUILD, ready.BINARY_SHA)):
        assert sha(build/'compose') == digest
    make11 = load('make_p11.py', P11)
    assert (compose.BINARY_SHA, compose.CANDIDATE_BINARY_SHA, ready.BINARY_SHA) == (
        make11.SIGN_COMPOSE_SHA, make11.CANDIDATE_COMPOSE_SHA, make11.PREFLIGHT_SHA)
    assert sha(HERE.parent/'m11'/'metadata_closure.py') == compose.POLICY_SHA


def test_adoption_witness_bindings():
    text = (HERE/'p12-adopt.py').read_text()
    assert "CORE='%s'" % CORE in text and "tree='%s'" % TREE in text
    assert "latest['controller_pid']==2800348" in text
    verification = '/var/tmp/ga-bebv-build-20260927/artifact-verification.json'
    assert "'%s','%s')" % (verification, sha(verification)) in text
    assert sha(HERE/'typed-interoperability.json') == sha(P11/'typed-interoperability.json')
    assert sha(HERE/'source-launch.py') == sha(P11/'source-launch.py')


def test_m11_acceptance_on_the_real_records(p):
    value = p.m11_acceptance()
    assert value['canonical_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
    assert value['receipt_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json')
    assert value['canonical_file_sha256'].startswith('9f60c3bf') and value['manifest_sha256'].startswith('599ccc58')
    assert value['acceptance_sha256'].startswith('cc21edc1')


def test_generator_reproduces_every_file():
    captured = {}
    make = load('make_p12.py')
    make.write = lambda name, text: captured.__setitem__(name, text.encode() if isinstance(text, str) else text) \
        or hashlib.sha256(captured[name]).hexdigest()
    make.diagnostics()
    make.scripts()
    assert set(captured) == {'template/compose-main.go', 'prepare-compose-template-p12.py', 'p12-input.py',
                             'p12-observe-compose.py', 'p12-readiness.py', 'p12-adopt.py', 'source-launch.py',
                             'typed-interoperability.json'}
    filled = re.compile(rb"\n(NEW_SHA|NEW_SELF|READY_RESULT_SHA|READY_BEFORE_SHA|READY_PINS_SHA)='[0-9a-f]{64}'\n")
    for name, data in captured.items():
        disk = (HERE/name).read_bytes()
        if name == 'p12-adopt.py':
            for _ in range(5):
                disk = filled.sub(lambda match: b'\n' + match.group(1) + b'=None\n', disk, count=1)
        assert disk == data, name


def test_every_generated_script_compiles():
    for name in ('p12-input.py', 'p12-observe-compose.py', 'p12-readiness.py', 'p12-adopt.py',
                 'prepare-compose-template-p12.py', 'source-launch.py', 'make_p12.py'):
        compile((HERE/name).read_bytes(), name, 'exec', dont_inherit=True)


def test_m10_is_named_only_in_the_succession_link():
    text = (HERE/'p12-input.py').read_text()
    assert [line for line in text.splitlines() if 'M10' in line] == [
        'succeeding the M10 file 2b902a83.',
        '# The succession link is previous_metadata.manifest_sha256, the M10 canonical FILE digest. The top-level']


def test_adoption_constants_bind_the_readiness_evidence():
    text = (HERE/'p12-adopt.py').read_text()
    if "\nNEW_SHA=None\n" in text:
        pytest.skip('adoption constants are filled after readiness')
    ready = Path('/var/tmp/gct-oak5-p12-readiness-20260927')
    final = json.loads((ready/'receipt.final.json').read_bytes())
    for name, value in (('NEW_SHA', sha(ready/'receipt.final.json')), ('NEW_SELF', final['receipt_sha256']),
                        ('READY_RESULT_SHA', sha(ready/'result.json')), ('READY_BEFORE_SHA', sha(ready/'before.json')),
                        ('READY_PINS_SHA', sha(ready/'before.json.provider-pins'))):
        assert "\n%s='%s'\n" % (name, value) in text, name
    result = json.loads((ready/'result.json').read_bytes())
    assert result['ok'] is True and result['unchanged'] is True and result['error'] is None
    digests = {q['name']: q['worker_profile_sha256'] for q in final['profiles']}
    assert [digests[SIGNING], digests[CANDIDATE]] == [SIGNING_DIGEST, CANDIDATE_DIGEST] and len(digests) == 3
    assert final['permission_revision'] == REVISION and final['template_commit'] == TEMPLATE
