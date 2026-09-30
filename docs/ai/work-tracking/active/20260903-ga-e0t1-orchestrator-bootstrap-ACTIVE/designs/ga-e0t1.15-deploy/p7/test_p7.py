"""Tests for the ga-e0t1.15 S3 part 2 (P7) receipt-refresh package.

  python3 -m pytest -q designs/ga-e0t1.15-deploy/p7/test_p7.py

Read-only. They read the installed receipt, the M6 records under reports/m6/q, the reviewed provisioner and
the diagnostic build roots; nothing is written outside pytest's temporary directory.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import types

import pytest

HERE = Path(__file__).parent
LIVE = Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json')
PROVISIONER = Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
TRACED = '2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2'


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
    return load('p7-input.py')


@pytest.fixture(scope='module')
def receipt(p):
    return json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def test_exact_delta(p, receipt):
    draft = p.derive(receipt, TRACED)
    before = dict(leaves(receipt))
    after = dict(leaves(draft))
    heads = {h['name']: i for i, h in enumerate(receipt['member_heads'])}
    removed = {'/canary_runner/path', '/canary_runner/sha256', '/receipt_sha256', '/profiles/0/worker_profile_sha256'}
    assert set(before) - set(after) == removed and set(after) <= set(before)
    changed = {k for k in after if before[k] != after[k]}
    assert changed == {'/template_commit', '/member_heads/%d/commit' % heads['template'],
                       '/member_heads/%d/commit' % heads['core'], '/permission_revision',
                       '/profiles/0/provider/version'}
    assert after['/template_commit'] == p.TEMPLATE_NEW == 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
    assert after['/member_heads/%d/commit' % heads['core']] == p.CORE == '9faeabc2892d8c7133111e13ad55af66790a2ac6'
    assert after['/permission_revision'] == TRACED
    assert after['/profiles/0/provider/version'].endswith('d4e57767d03accd708ce8876580096bb17bce023d6dc6e664fffee4367ea3c57')
    assert receipt == json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))  # the input is not mutated


@pytest.mark.parametrize('mutate', [
    lambda r: r.__setitem__('template_commit', 'x'),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'core'][0].__setitem__('commit', 'x'),
    lambda r: r['member_heads'].append(dict(name='core', commit='796d9a7a67c42294fdc467c107bb59b76e482301')),
    lambda r: r['profiles'][0]['provider'].__setitem__('version', 'x'),
    lambda r: r['profiles'][0]['argv'].__setitem__(6, 'claude-opus-5'),
    lambda r: r['profiles'].append(copy.deepcopy(r['profiles'][0])),
    lambda r: r.pop('canary_runner'),
])
def test_derive_refuses_predecessor_drift(p, receipt, mutate):
    changed = copy.deepcopy(receipt)
    mutate(changed)
    with pytest.raises((RuntimeError, KeyError)):
        p.derive(changed, TRACED)


@pytest.mark.parametrize('revision', ['d6ca85cd96c7aab4ea0b6a7954d2d74e5e6bb211cde0bb820f3b6f815023bd88', 'AB' * 32, 'ab' * 31])
def test_derive_refuses_revision(p, receipt, revision):
    with pytest.raises(RuntimeError):
        p.derive(receipt, revision)


def test_m6_acceptance_on_the_real_records(p):
    value = p.m6_acceptance()
    assert value['canonical_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
    assert value['receipt_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json')
    assert value['manifest_sha256'] == '3076e67e89b83ddb2db1b68b3337f0f98deb309d22b3d1770ca3fd4d67faed5c'
    assert value['acceptance_sha256'] == 'df7db3fa66ae7d7416974dc22806a511b94c7865ecbc21f17390f62335f584a2'


def test_reviewed_provisioner_accepts_the_draft(p, receipt):
    assert sha(PROVISIONER) == '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
    module = types.ModuleType('reviewed_provisioner'); module.__file__ = str(PROVISIONER)
    sys.modules[module.__name__] = module
    exec(compile(PROVISIONER.read_bytes(), str(PROVISIONER), 'exec', dont_inherit=True), module.__dict__)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'draft.json'
        path.write_bytes(p.serialize(p.derive(receipt, TRACED)))
        normalized = module.load_prototype(path, receipt['canary_runner'])
    assert normalized['template_commit'] == p.TEMPLATE_NEW and normalized['permission_revision'] == TRACED


def test_generator_reproduces_every_file():
    captured = {}
    make = load('make_p7.py')
    make.write = lambda name, text: captured.__setitem__(name, text.encode() if isinstance(text, str) else text) \
        or hashlib.sha256(captured[name]).hexdigest()
    make.builders()
    make.scripts()
    assert set(captured) == {'prepare-compose-p7.py', 'prepare-preflight-p7.py', 'compose-main.go', 'preflight-main.go',
                             'p7-input.py', 'p7-observe-compose.py', 'p7-readiness.py', 'p7-adopt.py',
                             'source-launch.py', 'typed-interoperability.json'}
    filled = re.compile(rb"\n(NEW_SHA|NEW_SELF|READY_RESULT_SHA|READY_BEFORE_SHA|READY_PINS_SHA)='[0-9a-f]{64}'\n")
    for name, data in captured.items():
        disk = (HERE/name).read_bytes()
        if name == 'p7-adopt.py':
            # Run-order step 4 fills exactly these five constants from the readiness evidence; nothing else.
            before = disk
            for _ in range(5):
                disk = filled.sub(lambda match: b'\n' + match.group(1) + b'=None\n', disk, count=1)
            assert before.count(b"='") - disk.count(b"='") in (0, 5)
        assert disk == data, name


def test_adoption_constants_bind_the_readiness_evidence():
    ready = Path('/var/tmp/ga-e0t1.15-p7-readiness-20260925')
    text = (HERE/'p7-adopt.py').read_text()
    final = json.loads((ready/'receipt.final.json').read_bytes())
    for name, value in (('NEW_SHA', sha(ready/'receipt.final.json')), ('NEW_SELF', final['receipt_sha256']),
                        ('READY_RESULT_SHA', sha(ready/'result.json')), ('READY_BEFORE_SHA', sha(ready/'before.json')),
                        ('READY_PINS_SHA', sha(ready/'before.json.provider-pins'))):
        assert "\n%s='%s'\n" % (name, value) in text, name
    result = json.loads((ready/'result.json').read_bytes())
    assert result['ok'] is True and result['unchanged'] is True and result['error'] is None
    assert final['template_commit'] == 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
    assert final['permission_revision'] == TRACED


def test_digest_chain_and_builds():
    compose = load('p7-observe-compose.py')
    readiness_text = (HERE/'p7-readiness.py').read_text()
    adopt_text = (HERE/'p7-adopt.py').read_text()
    assert compose.INPUT_SHA == sha(HERE/'p7-input.py')
    assert compose.POLICY_SHA == sha(compose.POLICY) and compose.POLICY.name == 'metadata_closure.py'
    assert compose.BINARY_SHA == sha(compose.BUILD/'compose')
    assert "BASE_SHA='%s'" % sha(HERE/'p7-observe-compose.py') in readiness_text
    assert "READY_SHA='%s'" % sha(HERE/'p7-readiness.py') in adopt_text
    for root in (compose.BUILD, Path('/var/tmp/ga-e0t1.15-preflight-diagnostic-20260925')):
        record = json.loads((root/'build-result.json').read_bytes())
        assert record['core_commit'] == '9faeabc2892d8c7133111e13ad55af66790a2ac6'
        assert record['core_tree'] == 'c9f19d215d271a5dda0bce296dc72c32dfc35499'
        assert record['builder_sha256'] == sha(HERE/'prepare-compose-p7.py')
        assert record['binary_sha256'] == sha(root/'compose')
