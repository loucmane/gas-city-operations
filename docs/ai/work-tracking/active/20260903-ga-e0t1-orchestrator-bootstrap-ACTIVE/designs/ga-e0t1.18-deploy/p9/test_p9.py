"""Tests for the P9 worker receipt refresh (the revision moved by the ga-6utp r12 lane activation).

  python3 -m pytest -q designs/ga-e0t1.18-deploy/p9/test_p9.py

Read-only: the installed receipt, the M8 records under reports/m8/q, the reviewed provisioner and P8's diagnostic
build roots.
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
OLD_REVISION = '2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2'
NEW_REVISION = '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add'  # the activation reload record
CORE = 'deefb98b2aed07875df31351d081fbac195cb1cd'


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
    return load('p9-input.py')


@pytest.fixture(scope='module')
def receipt(p):
    return json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


def test_exact_delta(p, receipt):
    """Exactly one leaf changes: permission_revision 2113693e -> the traced revision."""
    draft = p.derive(receipt, NEW_REVISION)
    before = dict(leaves(receipt))
    after = dict(leaves(draft))
    removed = {'/canary_runner/path', '/canary_runner/sha256', '/receipt_sha256', '/profiles/0/worker_profile_sha256'}
    assert set(before) - set(after) == removed and set(after) <= set(before)
    assert {k for k in after if before[k] != after[k]} == {'/permission_revision'}
    assert before['/permission_revision'] == OLD_REVISION and after['/permission_revision'] == NEW_REVISION
    heads = {h['name']: h['commit'] for h in draft['member_heads']}
    assert heads['core'] == CORE and heads['template'] == draft['template_commit'] == p.TEMPLATE
    assert receipt == json.loads(p.read(LIVE, p.RECEIPT_OLD_SHA))


@pytest.mark.parametrize('mutate', [
    lambda r: r.__setitem__('template_commit', 'x'),
    lambda r: [h for h in r['member_heads'] if h['name'] == 'core'][0].__setitem__('commit', 'x'),
    lambda r: r['member_heads'].append(dict(name='core', commit=CORE)),
    lambda r: r.__setitem__('permission_revision', 'ab' * 32),
    lambda r: r['profiles'][0]['provider'].__setitem__('version', 'x'),
    lambda r: r['profiles'][0]['argv'].__setitem__(6, 'claude-opus-5'),
    lambda r: r['profiles'].append(copy.deepcopy(r['profiles'][0])),
    lambda r: r.pop('canary_runner'),
])
def test_derive_refuses_predecessor_drift(p, receipt, mutate):
    changed = copy.deepcopy(receipt)
    mutate(changed)
    with pytest.raises((RuntimeError, KeyError)):
        p.derive(changed, NEW_REVISION)


@pytest.mark.parametrize('revision', [OLD_REVISION, 'AB' * 32, 'ab' * 31])
def test_derive_refuses_an_unmoved_or_malformed_revision(p, receipt, revision):
    with pytest.raises(RuntimeError, match='revision predecessor'):
        p.derive(receipt, revision)


def test_the_activation_recorded_the_new_revision():
    reload = json.loads(Path('/home/loucmane/.local/share/gas-city-staging/ga-6utp-activation-r12-20260926/'
                             'records/reload.json').read_text())
    assert reload['reload']['revision'] == NEW_REVISION


def test_m8_acceptance_on_the_real_records(p):
    value = p.m8_acceptance()
    assert value['canonical_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')
    assert value['receipt_file_sha256'] == sha('/home/loucmane/gascity/city/.gc/platform/install-receipt.json')
    assert value['manifest_sha256'] == 'fc9a68fe2bf638f2f7aa59de4e1ccfbce967fe0d04021229732d76908d7a6061'
    assert value['acceptance_sha256'] == '7f7e72ebea779204d87af73aa7a320b9bed9ed7a773efd4cf5466ec53e466801'


def test_reviewed_provisioner_accepts_the_draft(p, receipt):
    assert sha(PROVISIONER) == '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
    module = types.ModuleType('reviewed_provisioner'); module.__file__ = str(PROVISIONER)
    sys.modules[module.__name__] = module
    exec(compile(PROVISIONER.read_bytes(), str(PROVISIONER), 'exec', dont_inherit=True), module.__dict__)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'draft.json'
        path.write_bytes(p.serialize(p.derive(receipt, NEW_REVISION)))
        normalized = module.load_prototype(path, receipt['canary_runner'])
    assert normalized['permission_revision'] == NEW_REVISION


def test_generator_reproduces_every_file():
    captured = {}
    make = load('make_p9.py')
    make.write = lambda name, text: captured.__setitem__(name, text.encode() if isinstance(text, str) else text) \
        or hashlib.sha256(captured[name]).hexdigest()
    make.scripts()
    assert set(captured) == {'p9-input.py', 'p9-observe-compose.py', 'p9-readiness.py', 'p9-adopt.py',
                             'source-launch.py', 'typed-interoperability.json'}
    filled = re.compile(rb"\n(NEW_SHA|NEW_SELF|READY_RESULT_SHA|READY_BEFORE_SHA|READY_PINS_SHA)='[0-9a-f]{64}'\n")
    for name, data in captured.items():
        disk = (HERE/name).read_bytes()
        if name == 'p9-adopt.py':
            before = disk
            for _ in range(5):
                disk = filled.sub(lambda match: b'\n' + match.group(1) + b'=None\n', disk, count=1)
            assert before.count(b"='") - disk.count(b"='") in (0, 5)
        assert disk == data, name


def test_reused_p8_builds_and_sources():
    compose = load('p9-observe-compose.py')
    readiness_text = (HERE/'p9-readiness.py').read_text()
    assert compose.INPUT_SHA == sha(HERE/'p9-input.py')
    assert compose.BINARY_SHA == sha(compose.BUILD/'compose') and str(compose.BUILD).endswith('compose-diagnostic-20260926')
    assert compose.POLICY_SHA == sha(compose.POLICY)
    assert "BASE_SHA='%s'" % sha(HERE/'p9-observe-compose.py') in readiness_text
    assert "SUCCESSOR=HERE.parent/'p8'" in readiness_text
    assert "READY_SHA='%s'" % sha(HERE/'p9-readiness.py') in (HERE/'p9-adopt.py').read_text()
    for root in (compose.BUILD, Path('/var/tmp/ga-e0t1.18-preflight-diagnostic-20260926')):
        record = json.loads((root/'build-result.json').read_bytes())
        assert record['core_commit'] == CORE and record['binary_sha256'] == sha(root/'compose')


def test_adoption_constants_bind_the_readiness_evidence():
    text = (HERE/'p9-adopt.py').read_text()
    if "\nNEW_SHA=None\n" in text:
        pytest.skip('adoption constants are filled after readiness')
    ready = Path('/var/tmp/ga-e0t1.18-p9-readiness-20260926')
    final = json.loads((ready/'receipt.final.json').read_bytes())
    for name, value in (('NEW_SHA', sha(ready/'receipt.final.json')), ('NEW_SELF', final['receipt_sha256']),
                        ('READY_RESULT_SHA', sha(ready/'result.json')), ('READY_BEFORE_SHA', sha(ready/'before.json')),
                        ('READY_PINS_SHA', sha(ready/'before.json.provider-pins'))):
        assert "\n%s='%s'\n" % (name, value) in text, name
    result = json.loads((ready/'result.json').read_bytes())
    assert result['ok'] is True and result['unchanged'] is True and result['error'] is None
    assert final['permission_revision'] == NEW_REVISION
