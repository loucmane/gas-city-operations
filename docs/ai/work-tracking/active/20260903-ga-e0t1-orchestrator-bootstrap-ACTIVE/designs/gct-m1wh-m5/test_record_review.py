"""Tests for record_review.py, checked against the real recovery_controller.review()."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).parent
LEGACY = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/'
              'active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/reports/ga-e0t1.14-rollout-r1/package-r4/'
              'resume-r4b/recovery-source-r2')


def load():
    path = HERE/'record_review.py'
    module = types.ModuleType('record_review'); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def controller():
    sys.dont_write_bytecode = True
    if str(LEGACY) not in sys.path:
        sys.path.insert(0, str(LEGACY))
    import recovery_controller
    assert hashlib.sha256((LEGACY/'recovery_controller.py').read_bytes()).hexdigest() == \
        'dcc78e45698ea9e7b345b06352a70334073de21b3f7e77dcf8d05e50432ec97d'
    return recovery_controller


class Recorder(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.o = self.m.observer()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.m.Q = root/'m5'/'q'; self.m.Q.mkdir(parents=True)
        self.m.REVIEWS = root/'m5-reviews'
        self.drafts = root/'drafts'; self.drafts.mkdir()
        for name, value in (('prepared.json', dict(sources={'/a.py': 'a' * 64}, manifest_file_sha256='b' * 64,
                                                   preparation_only=True)),
                            ('observe-result.json', dict(phase='observe', exit_code=0)),
                            ('after-observation.json', dict(ok=True)),
                            ('window.json', dict(deadline=1)),
                            ('committed-acceptance.json', dict(ok=True, note='<&>'))):
            (self.m.Q/name).write_bytes(self.o.encoded(value))

    def tearDown(self):
        self.tmp.cleanup()

    def draft(self, name, **fields):
        path = self.drafts/name
        path.write_bytes(self.o.encoded(fields))
        return str(path)

    def pair(self, kind, **changes):
        expected = self.m.bindings(self.o, kind)
        first = dict(reviewer_id='agent-a', verdict=kind, bindings=expected, assessment='checked a')
        second = dict(reviewer_id='agent-b', verdict=kind, bindings=expected, assessment='checked b')
        second.update(changes)
        return self.draft(kind + '-1.json', **first), self.draft(kind + '-2.json', **second)

    def test_records_satisfy_the_real_controller(self):
        rc = controller()
        prior = rc.s.RECORDS
        rc.s.RECORDS = self.m.Q
        try:
            for kind in self.m.KINDS:
                self.m.record(self.o, kind, self.pair(kind))
                rc.review(kind, self.m.bindings(self.o, kind))
        finally:
            rc.s.RECORDS = prior

    def test_consumer_formulas_not_the_recorder(self):
        """Non-circular: the real consumers build the expected bindings themselves."""
        rc = controller()
        prior = rc.s.RECORDS
        rc.s.RECORDS = self.m.Q
        try:
            self.m.record(self.o, 'SOURCE_PASS', self.pair('SOURCE_PASS'))
            package = hashlib.sha256((self.m.Q/'prepared.json').read_bytes()).hexdigest()
            prepared = self.o.decode((self.m.Q/'prepared.json').read_bytes())
            rc.source_review(package, prepared)  # recovery_controller.py:130-132, the real formula
            self.m.record(self.o, 'PAIRING_PASS', self.pair('PAIRING_PASS'))
            digest = lambda name: hashlib.sha256((self.m.Q/name).read_bytes()).hexdigest()
            # The executor sets recovery_native.PROBE_LIMIT to its float 36.0; the record must match it.
            rc.review('PAIRING_PASS', dict(package_sha256=package, observation_result_sha256=digest('observe-result.json'),
                                           after_observation_sha256=digest('after-observation.json'),
                                           window_sha256=digest('window.json'), probe_limit_seconds=36.0))
        finally:
            rc.s.RECORDS = prior

    def test_binding_keys_match_consumer_source(self):
        import ast

        def keywords(path, function, kind):
            tree = ast.parse(Path(path).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function:
                    for call in ast.walk(node):
                        if (isinstance(call, ast.Call) and call.args and isinstance(call.args[0], ast.Constant)
                                and call.args[0].value == kind and len(call.args) == 2):
                            return {k.arg for k in call.args[1].keywords}
            raise AssertionError((function, kind))
        self.assertEqual(keywords(LEGACY/'recovery_controller.py', 'source_review', 'SOURCE_PASS'),
                         set(self.m.bindings(self.o, 'SOURCE_PASS')))
        self.assertEqual(keywords(LEGACY/'recovery_controller.py', 'paired', 'PAIRING_PASS'),
                         set(self.m.bindings(self.o, 'PAIRING_PASS')))
        self.assertEqual(keywords(HERE/'metadata_executor.py', 'restore', 'COMMIT_PASS'),
                         set(self.m.bindings(self.o, 'COMMIT_PASS')))
        text = (HERE/'metadata_executor.py').read_text()
        self.assertIn('PROBE_LIMIT = 36.0\n', text)
        self.assertIn('n.PROBE_LIMIT = PROBE_LIMIT\n', text)
        self.assertEqual((self.m.PROBE_LIMIT, type(self.m.PROBE_LIMIT)), (36.0, float))

    def test_atomic_publication_leaves_no_partial_or_temporary(self):
        target = self.m.Q/'atomic.json'
        self.m.exclusive(target, b'{"a":1}')
        self.assertEqual(target.read_bytes(), b'{"a":1}')
        with self.assertRaises(FileExistsError):
            self.m.exclusive(target, b'{"b":2}')
        self.assertEqual(target.read_bytes(), b'{"a":1}')
        self.assertEqual([p.name for p in self.m.Q.iterdir() if p.name.startswith('.')], [])

    def test_bindings_follow_the_executor(self):
        package = hashlib.sha256((self.m.Q/'prepared.json').read_bytes()).hexdigest()
        self.assertEqual(self.m.bindings(self.o, 'SOURCE_PASS'),
                         dict(package_sha256=package, sources={'/a.py': 'a' * 64}, manifest_file_sha256='b' * 64))
        pairing = self.m.bindings(self.o, 'PAIRING_PASS')
        self.assertEqual(set(pairing), {'package_sha256', 'observation_result_sha256', 'after_observation_sha256',
                                        'window_sha256', 'probe_limit_seconds'})
        self.assertEqual(pairing['probe_limit_seconds'], 36)
        self.assertEqual(self.m.bindings(self.o, 'COMMIT_PASS')['acceptance_sha256'],
                         hashlib.sha256((self.m.Q/'committed-acceptance.json').read_bytes()).hexdigest())

    def test_refusals(self):
        cases = [dict(verdict='HOLD'), dict(reviewer_id='agent-a'), dict(assessment='  '),
                 dict(bindings=dict(package_sha256='0' * 64)), dict(reviewer_id='bad id/x')]
        for change in cases:
            with self.assertRaises(RuntimeError, msg=str(change)):
                self.m.record(self.o, 'SOURCE_PASS', self.pair('SOURCE_PASS', **change))
            self.assertFalse((self.m.Q/'source-pass.json').exists())
        path = self.draft('extra.json', reviewer_id='agent-c', verdict='SOURCE_PASS',
                          bindings=self.m.bindings(self.o, 'SOURCE_PASS'), assessment='x', extra=1)
        with self.assertRaises(RuntimeError):
            self.m.record(self.o, 'SOURCE_PASS', (self.pair('SOURCE_PASS')[0], path))

    def test_retry_after_partial_refusal(self):
        first, _ = self.pair('SOURCE_PASS')
        taken = self.m.REVIEWS
        taken.mkdir(mode=0o700)
        (taken/'source-pass-agent-b.json').write_bytes(b'{}')
        with self.assertRaises(RuntimeError):
            self.m.record(self.o, 'SOURCE_PASS', self.pair('SOURCE_PASS'))
        self.assertFalse((self.m.Q/'source-pass.json').exists())
        self.assertEqual(sorted(p.name for p in taken.iterdir()), ['source-pass-agent-b.json'])
        retry = self.draft('retry.json', reviewer_id='agent-c', verdict='SOURCE_PASS',
                           bindings=self.m.bindings(self.o, 'SOURCE_PASS'), assessment='checked c')
        self.m.record(self.o, 'SOURCE_PASS', (first, retry))
        self.assertEqual((taken/'source-pass-agent-b.json').read_bytes(), b'{}')

    def test_never_overwrites(self):
        self.m.record(self.o, 'COMMIT_PASS', self.pair('COMMIT_PASS'))
        before = (self.m.Q/'commit-pass.json').read_bytes()
        with self.assertRaises(RuntimeError):
            self.m.record(self.o, 'COMMIT_PASS', self.pair('COMMIT_PASS'))
        self.assertEqual((self.m.Q/'commit-pass.json').read_bytes(), before)

    def test_records_canonical_encoding(self):
        self.m.record(self.o, 'COMMIT_PASS', self.pair('COMMIT_PASS'))
        raw = (self.m.Q/'commit-pass.json').read_bytes()
        self.assertEqual(raw, self.o.encoded(json.loads(raw)))
        self.assertEqual((self.m.Q/'commit-pass.json').stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
