"""Focused tests for p6-input.py: pure derivation, M5 record verification and trace selection."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

HERE = Path(__file__).parent
LIVE = Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json')
DRAFT_0920 = Path('/home/loucmane/.local/share/gas-city-staging/ga-mutg-20260920/'
                  'ga-ecwh-provisioning-successor-20260920/receipt.input.draft.json')
PROVISIONER = Path(os.environ.get('P6_PROVISIONER', '/nonexistent'))
NEW_REV = 'ab' * 32


def load():
    path = HERE/'p6-input.py'
    module = types.ModuleType('p6_input'); module.__file__ = str(path)
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


class Derive(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.receipt = json.loads(self.m.read(LIVE, self.m.RECEIPT_OLD_SHA))

    def test_exact_delta(self):
        draft = self.m.derive(self.receipt, NEW_REV)
        before = dict(leaves(json.loads(DRAFT_0920.read_bytes())))
        after = dict(leaves(draft))
        self.assertEqual(set(before), set(after))
        changed = {k for k in before if before[k] != after[k]}
        self.assertEqual(changed, {'/template_commit', '/member_heads/2/commit', '/permission_revision',
                                   '/profiles/0/provider/version', '/profiles/0/argv/6'})
        self.assertEqual(after['/profiles/0/argv/6'], 'claude-opus-5-5')
        self.assertEqual(after['/member_heads/2/commit'], self.m.TEMPLATE_NEW)
        self.assertEqual(after['/profiles/0/provider/version'], self.m.VERSION_NEW)
        self.assertEqual(after['/permission_revision'], NEW_REV)

    def test_input_is_not_mutated(self):
        original = copy.deepcopy(self.receipt)
        self.m.derive(self.receipt, NEW_REV)
        self.assertEqual(self.receipt, original)

    def test_refusals(self):
        cases = []
        r = copy.deepcopy(self.receipt); r['template_commit'] = 'x'; cases.append((r, NEW_REV))
        r = copy.deepcopy(self.receipt); r['member_heads'][2]['commit'] = 'x'; cases.append((r, NEW_REV))
        r = copy.deepcopy(self.receipt); r['member_heads'].append(dict(name='template', commit='x'))
        cases.append((r, NEW_REV))
        r = copy.deepcopy(self.receipt); r['profiles'][0]['provider']['version'] = 'x'; cases.append((r, NEW_REV))
        r = copy.deepcopy(self.receipt); r['profiles'][0]['argv'][6] = 'claude-opus-5-5'; cases.append((r, NEW_REV))
        r = copy.deepcopy(self.receipt); r['profiles'][0]['argv'] += ['--model', 'claude-opus-5']
        cases.append((r, NEW_REV))
        r = copy.deepcopy(self.receipt); r['profiles'].append(copy.deepcopy(r['profiles'][0]))
        cases.append((r, NEW_REV))
        r = copy.deepcopy(self.receipt); del r['canary_runner']; cases.append((r, NEW_REV))
        cases += [(self.receipt, self.m.REVISION_OLD), (self.receipt, 'AB' * 32), (self.receipt, 'ab' * 31)]
        for receipt, revision in cases:
            with self.assertRaises((RuntimeError, KeyError)):
                self.m.derive(receipt, revision)

    @unittest.skipUnless(PROVISIONER.is_file(), 'P6_PROVISIONER not given')
    def test_provisioner_accepts_draft(self):
        self.assertEqual(hashlib.sha256(PROVISIONER.read_bytes()).hexdigest(),
                         '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35')
        p = types.ModuleType('reviewed_provisioner'); p.__file__ = str(PROVISIONER)
        import sys
        sys.modules[p.__name__] = p
        exec(compile(PROVISIONER.read_bytes(), str(PROVISIONER), 'exec', dont_inherit=True), p.__dict__)
        runner = self.receipt['canary_runner']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'draft.json'
            path.write_text(json.dumps(self.m.derive(self.receipt, NEW_REV)))
            normalized = p.load_prototype(path, runner)
        self.assertEqual(normalized['template_commit'], self.m.TEMPLATE_NEW)


class Proven(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.m.ROOT = Path(self.tmp.name)/'input'
        self.m.ROOT.mkdir(mode=0o700)
        raw = self.m.read(LIVE, self.m.RECEIPT_OLD_SHA)
        self.m.write('receipt.before.json', raw)
        draft_sha = self.m.write('receipt.input.draft.json', self.m.serialize(self.m.derive(json.loads(raw), NEW_REV)))
        revision_sha = self.m.write('revision.json', dict(config_revision=NEW_REV, seq=1))
        self.m.write('result.json', dict(ok=True, draft_sha256=draft_sha, revision_sha256=revision_sha,
                                         permission_revision=NEW_REV, receipt_before_sha256=self.m.RECEIPT_OLD_SHA,
                                         m5=dict(manifest_sha256='m' * 64)))

    def tearDown(self):
        self.tmp.cleanup()

    def replace(self, name, raw):
        path = self.m.ROOT/name
        path.chmod(0o600); path.unlink(); self.m.write(name, raw)

    def test_accepts_recorded_derivation(self):
        value = self.m.proven_draft()
        self.assertEqual(value['revision'], NEW_REV)
        self.assertEqual(hashlib.sha256(value['raw']).hexdigest(), value['sha256'])

    def test_refuses_any_substitution(self):
        result = json.loads((self.m.ROOT/'result.json').read_text())
        draft = json.loads((self.m.ROOT/'receipt.input.draft.json').read_text())
        draft['profiles'][0]['argv'][6] = 'claude-opus-5'
        raw = self.m.serialize(draft)
        self.replace('receipt.input.draft.json', raw)
        result['draft_sha256'] = hashlib.sha256(raw).hexdigest()
        self.replace('result.json', result)
        with self.assertRaises(RuntimeError):
            self.m.proven_draft()

    def test_refuses_revision_mismatch(self):
        result = json.loads((self.m.ROOT/'result.json').read_text())
        result['permission_revision'] = 'cd' * 32
        self.replace('result.json', result)
        with self.assertRaises(RuntimeError):
            self.m.proven_draft()


class Trace(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def record(self, seq, **changes):
        value = dict(seq=seq, ts=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                     controller_pid=7, gc_commit=self.m.CORE, completion_status='completed',
                     config_revision=NEW_REV, fields=dict(active_template_count=0))
        value.update(changes)
        return value

    def test_newest_record_must_qualify(self):
        self.assertEqual(self.m.latest_cycle([self.record(1), self.record(2)], 7)['seq'], 2)
        for bad in (dict(controller_pid=8), dict(gc_commit='x'), dict(completion_status='failed'),
                    dict(fields=dict(active_template_count=1)), dict(ts='2026-01-01T00:00:00Z')):
            with self.assertRaises(RuntimeError):
                self.m.latest_cycle([self.record(1), self.record(2, **bad)], 7)
        with self.assertRaises(RuntimeError):
            self.m.latest_cycle([], 7)


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.q = root/'q'; self.q.mkdir()
        city = root/'city'; (city/'.gc/platform').mkdir(parents=True)
        self.m.M5 = self.q; self.m.CITY = city
        canonical, receipt = b'{"canonical":1}\n', b'{"receipt":1}\n'
        (city/'.gc/platform/install-manifest.json').write_bytes(canonical)
        (city/'.gc/platform/install-receipt.json').write_bytes(receipt)
        acceptance = dict(ok=True, lease_expired=True, package_sha256='p' * 64, manifest_sha256='m' * 64,
                          receipt_sha256='r' * 64, canonical_file_sha256=hashlib.sha256(canonical).hexdigest(),
                          receipt_file_sha256=hashlib.sha256(receipt).hexdigest())
        self.write('committed-acceptance.json', acceptance)
        self.write('restored.json', dict(ok=True, accepted=True, after={}, historical_reconciler_epoch_not_reset=True))
        self.write('manifest.json', dict(release_id=self.m.M5_RELEASE, previous_sha256='c' * 64,
                                         previous_metadata=dict(manifest_sha256=self.m.R9_MANIFEST_FILE),
                                         manifest_sha256='m' * 64, integrity=dict(repositories=[
                                             dict(name='other', path='/x', commit='y'),
                                             dict(zip(('name', 'path', 'commit'), self.m.M5_AUTHORITY))])))
        bindings = dict(package_sha256='p' * 64,
                        acceptance_sha256=hashlib.sha256((self.q/'committed-acceptance.json').read_bytes()).hexdigest())
        people = []
        for name in ('first', 'second'):
            path = root/(name + '.json')
            raw = json.dumps(dict(reviewer_id=name, verdict='COMMIT_PASS', bindings=bindings,
                                  assessment='checked ' + name)).encode()
            path.write_bytes(raw)
            people.append(dict(reviewer_id=name, provenance_path=str(path),
                               provenance_sha256=hashlib.sha256(raw).hexdigest()))
        self.write('commit-pass.json', dict(verdict='COMMIT_PASS', bindings=bindings, reviewers=people))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        (self.q/name).write_text(json.dumps(value))

    def edit(self, name, change):
        value = json.loads((self.q/name).read_text()); change(value); self.write(name, value)

    def test_accepts_consistent_records(self):
        value = self.m.m5_acceptance()
        self.assertEqual(value['manifest_sha256'], 'm' * 64)
        self.assertEqual(value['receipt_sha256'], 'r' * 64)

    def test_refuses_each_break(self):
        breaks = [
            ('commit-pass.json', lambda v: v.update(verdict='PAIRING_PASS')),
            ('commit-pass.json', lambda v: v['reviewers'][1].update(reviewer_id='first')),
            ('commit-pass.json', lambda v: v['reviewers'].pop()),
            ('commit-pass.json', lambda v: v['reviewers'][1].update(provenance_path=v['reviewers'][0]['provenance_path'],
                                                                   provenance_sha256=v['reviewers'][0]['provenance_sha256'])),
            ('restored.json', lambda v: v.update(accepted=False)),
            ('manifest.json', lambda v: v.update(release_id='other')),
            ('manifest.json', lambda v: v['previous_metadata'].update(manifest_sha256='0' * 64)),
            ('manifest.json', lambda v: v['previous_metadata'].update(
                manifest_sha256='9aa3f8d13b59a2c85a478ff7938d860c7eb681b6cc529580083d69d129ffd9aa')),
            ('manifest.json', lambda v: v['integrity']['repositories'].reverse()),
            ('manifest.json', lambda v: v.update(manifest_sha256='0' * 64)),
        ]
        for name, change in breaks:
            saved = (self.q/name).read_bytes()
            self.edit(name, change)
            with self.assertRaises((RuntimeError, KeyError), msg=name):
                self.m.m5_acceptance()
            (self.q/name).write_bytes(saved)
            self.m.m5_acceptance()

    def test_refuses_acceptance_or_live_drift(self):
        self.edit('committed-acceptance.json', lambda v: v.update(ok=False))
        with self.assertRaises(RuntimeError):
            self.m.m5_acceptance()

    def test_refuses_live_pair_drift(self):
        (self.m.CITY/'.gc/platform/install-receipt.json').write_bytes(b'{}')
        with self.assertRaises(RuntimeError):
            self.m.m5_acceptance()


def constants(name):
    import ast
    tree = ast.parse((HERE/name).read_text())
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return values


def digest(name):
    return hashlib.sha256((HERE/name).read_bytes()).hexdigest()


class Chain(unittest.TestCase):
    def test_each_step_pins_the_previous_source(self):
        self.assertEqual(constants('p6-observe-compose.py')['INPUT_SHA'], digest('p6-input.py'))
        self.assertEqual(constants('p6-readiness.py')['BASE_SHA'], digest('p6-observe-compose.py'))
        self.assertEqual(constants('p6-adopt.py')['READY_SHA'], digest('p6-readiness.py'))
        self.assertEqual(constants('p6-observe-compose.py')['LAUNCHER_SHA'], digest('source-launch.py'))
        self.assertEqual(constants('p6-readiness.py')['LAUNCH_SHA'], digest('source-launch.py'))
        self.assertEqual(digest('typed-interoperability.json'),
                         '315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563')

    def test_fresh_distinct_roots(self):
        import re
        roots = []
        for name in ('p6-input.py', 'p6-observe-compose.py', 'p6-readiness.py', 'p6-adopt.py'):
            found = re.findall(r"^ROOT\s*=\s*Path\('([^']+)'\)$", (HERE/name).read_text(), re.M)
            self.assertEqual(len(found), 1, name)
            self.assertTrue(found[0].startswith('/var/tmp/gct-m1wh-p6-'), name)
            self.assertFalse(os.path.lexists(found[0]), name)
            roots.append(found[0])
        self.assertEqual(len(set(roots)), 4)

    def test_adoption_refuses_until_filled(self):
        values = constants('p6-adopt.py')
        self.assertTrue(all(values[k] is None for k in ('NEW_SHA', 'NEW_SELF', 'READY_RESULT_SHA',
                                                        'READY_BEFORE_SHA', 'READY_PINS_SHA')))
        self.assertEqual(values['OLD_SHA'], '01ed1bce0b99d5c6043804cdacb2b25bc725bffb00dba3450888284e570d0a8a')


class Composition(unittest.TestCase):
    def setUp(self):
        path = HERE/'p6-readiness.py'
        self.r = types.ModuleType('p6_readiness'); self.r.__file__ = str(path)
        exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), self.r.__dict__)
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.r.COMPOSITION = root/'composition.json'
        self.draft = json.loads(DRAFT_0920.read_bytes())
        profile = self.draft['profiles'][0]
        self.observation = dict(profile=profile['name'], argv=profile['argv'], environment=profile['environment'],
                                permission_revision=self.draft['permission_revision'], task_observed=False,
                                worker_launched=False)
        self.write('composition.json', dict(observation=self.observation))
        self.write('result.json', dict(ok=True, unchanged=True, error=None))
        (root/'before.json').write_bytes(b'same'); (root/'after.json').write_bytes(b'same')
        draft = self.draft
        self.base = types.SimpleNamespace(read=lambda p: Path(p).read_bytes(),
                                          recorded_draft=lambda: dict(raw=json.dumps(draft).encode()))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        (self.r.COMPOSITION.parent/name).write_text(json.dumps(value))

    def test_accepts_matching_composition(self):
        self.assertEqual(self.r.composition(self.base), b'same')

    def test_refuses_mismatch(self):
        for key, value in (('argv', []), ('permission_revision', 'x'), ('worker_launched', True),
                           ('environment', {}), ('profile', 'other'), ('task_observed', True)):
            self.write('composition.json', dict(observation=dict(self.observation, **{key: value})))
            with self.assertRaises(RuntimeError, msg=key):
                self.r.composition(self.base)
        self.write('composition.json', dict(observation=self.observation))
        for result in (dict(ok=False, unchanged=True, error=None), dict(ok=True, unchanged=False, error=None),
                       dict(ok=True, unchanged=True, error='x')):
            self.write('result.json', result)
            with self.assertRaises(RuntimeError):
                self.r.composition(self.base)
        self.write('result.json', dict(ok=True, unchanged=True, error=None))
        (self.r.COMPOSITION.parent/'after.json').write_bytes(b'other')
        with self.assertRaises(RuntimeError):
            self.r.composition(self.base)


if __name__ == '__main__':
    unittest.main()
