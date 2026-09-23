"""Tests for round 2a (the observer stack). Run: python3 -B -m unittest test_round2a (from this directory).

Read-only. Regenerates every output into a temporary directory from the reviewed ga-y49e sources and
requires byte equality with the committed files. The forecast test runs proof/admission-forecast.py:
the generated base's pins() and its before.json admission comparison against the P6 accepted snapshot
plus the disposition, over the live cache, pins and protected trees (O_NOATIME reads; the host block
needs the supervisor namespaces and is left to the job).
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PREP = '/var/tmp/ga-4z38-prep-20260923-r2'
P6 = '/var/tmp/gct-m1wh-p6-adoption-20260923-r2'
CACHE_GIT = '/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git'


def sha_file(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def constant(text, name):
    [value] = re.findall(r"^%s ?= ?'([0-9a-f]{64})'$" % name, text, re.M)
    return value


class Regeneration(unittest.TestCase):
    def test_generators_reproduce_every_committed_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Generators embed the package path, so regenerate with the real package path as the
            # target text and compare after writing to a scratch copy of the package directory.
            scratch = os.path.join(tmp, 'pkg')
            shutil.copytree(HERE, scratch, ignore=shutil.ignore_patterns('window-base-r11.py', 'window-obs-r11.py',
                                                                          'observe-integrity-r11.py', '__pycache__'))
            for script, args in (('make_window_base_r11.py', [HERE, PREP]), ('make_round2a.py', [HERE])):
                gen = os.path.join(HERE, 'generators', script)
                out = subprocess.run([sys.executable, '-B', gen, *args], capture_output=True, text=True,
                                     env=dict(os.environ, GA4Z38_OUT=scratch))
                self.assertEqual(out.returncode, 0, out.stderr)
            for name in ('window-base-r11.py', 'window-obs-r11.py', 'observe-integrity-r11.py'):
                self.assertEqual(sha_file(os.path.join(scratch, name)), sha_file(os.path.join(HERE, name)), name)


class Pins(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(HERE, 'window-base-r11.py'), encoding='utf-8') as handle:
            self.base = handle.read()

    def test_base_pins_match_their_files(self):
        self.assertEqual(constant(self.base, 'WITNESS_SHA'), sha_file(P6 + '/typed-support.json'))
        self.assertEqual(constant(self.base, 'ACCEPTED_SHA'), sha_file(P6 + '/after.json'))
        self.assertEqual(constant(self.base, 'PROVIDER_SHA'), sha_file(P6 + '/after.json.provider-pins'))

    def test_base_binds_the_prep_outputs(self):
        with open(PREP + '/result.json') as handle:
            result = json.load(handle)
        self.assertIn(result['receipt_after_sha256'], self.base)
        self.assertIn(result['revision_after'], self.base)
        self.assertIn(result['city_after_sha256'], self.base)
        self.assertEqual(result['city_after_sha256'], '5f3b60e1c1e391b5a1f66de62a2e767ea226570ce7549c6dfb526cd072e6530d')

    def test_disposition_matches_p6_and_the_live_cache_directory(self):
        with open(P6 + '/after.json') as handle:
            accepted = json.load(handle)
        entry = accepted['cache']['inventory']['954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git']
        self.assertEqual((entry['mtime_ns'], entry['ctime_ns']), (1790165454882697018, 1790165454882697018))
        live = os.lstat(CACHE_GIT)
        self.assertEqual((live.st_mtime_ns, live.st_ctime_ns), (1790178703592685769, 1790178703592685769))
        self.assertIn('1790165454882697018', self.base)
        self.assertIn('1790178703592685769', self.base)

    def test_copied_modules_are_byte_identical(self):
        for name, digest in (('cache-atime-policy-r1.py', '61c3e38e4475061c658a853036922742ab2ce69d44a4577e3f91490674047783'),
                             ('suspension-lineage.py', '4b0d4c5bb713dc4ac802efc5c45f126d026c83fb5ea03fcb5f40d0c680cacbf0')):
            self.assertEqual(sha_file(os.path.join(HERE, name)), digest)

    def test_layer_and_observer_bind_their_loads(self):
        with open(os.path.join(HERE, 'window-obs-r11.py'), encoding='utf-8') as handle:
            layer = handle.read()
        self.assertEqual(constant(layer, 'BASE_SHA'), sha_file(os.path.join(HERE, 'window-base-r11.py')))
        with open(os.path.join(HERE, 'observe-integrity-r11.py'), encoding='utf-8') as handle:
            observer = handle.read()
        self.assertEqual(constant(observer, 'W_SHA'), sha_file(os.path.join(HERE, 'window-obs-r11.py')))
        self.assertEqual(constant(observer, 'MANIFEST_SHA'),
                         sha_file('/home/loucmane/gascity/city/.gc/platform/install-manifest.json'))

    def test_wrapper_pins_the_observer(self):
        with open(os.path.join(HERE, 'operator', 'OBSERVE.sh'), encoding='utf-8') as handle:
            text = handle.read()
        [pin] = re.findall(r'^OBSERVE_SHA=([0-9a-f]{64})$', text, re.M)
        self.assertEqual(pin, sha_file(os.path.join(HERE, 'observe-integrity-r11.py')))
        self.assertIn('OUT=/var/tmp/ga-4z38-integrity-20260923-r1\n', text)
        self.assertIn('exit "$rc"', text)


class Forecast(unittest.TestCase):
    def test_admission_forecast_matches_p6_with_the_disposition(self):
        done = subprocess.run([sys.executable, '-B', os.path.join(HERE, 'proof', 'admission-forecast.py')],
                              capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
        self.assertEqual(done.returncode, 0, done.stdout[-3000:] + done.stderr[-3000:])
        report = json.loads(done.stdout)
        self.assertTrue(report['admission_equal'] and report['providers_equal'])
        self.assertEqual(report['base_sha256'], sha_file(os.path.join(HERE, 'window-base-r11.py')))


class Observer(unittest.TestCase):
    def test_result_makes_no_claim_about_the_ga_y49e_window(self):
        with open(os.path.join(HERE, 'observe-integrity-r11.py'), encoding='utf-8') as handle:
            text = handle.read()
        self.assertNotIn('original_restoration_comparator_remains_hold', text)
        self.assertIn('admitted_against_p6_with_disposition=True', text)
        self.assertNotIn('verified_lifecycle', text)


if __name__ == '__main__':
    unittest.main()
