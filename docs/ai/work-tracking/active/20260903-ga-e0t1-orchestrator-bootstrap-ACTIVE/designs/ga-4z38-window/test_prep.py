"""Tests for prep-r11.py. Run: python3 -B -m unittest test_prep (from this directory).

These read live files and run read-only `gc config show` and `gc order list` with
GIT_OPTIONAL_LOCKS=0, which leaves the pack cache untouched. The R3 proof test also runs, all in
read-only bwrap: gc under the pinned overlay, the Template provisioner through the source launcher,
and Core `compose finalize`. Nothing is written outside a temporary directory.
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('prep', os.path.join(HERE, 'prep-r11.py'))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
# The coordinator derived this overlay twice, from a text transform of the reviewed ga-y49e
# overlay and from this generator over live config; both gave these bytes.
OVERLAY_SHA = '5f3b60e1c1e391b5a1f66de62a2e767ea226570ce7549c6dfb526cd072e6530d'
ENV = dict(P.ENV)


def live(*args):
    done = subprocess.run([str(P.GC), '--city', str(P.CITY), *args], env=ENV, capture_output=True, text=True,
                          timeout=60, stdin=subprocess.DEVNULL, check=True)
    return json.loads(done.stdout)


class Pins(unittest.TestCase):
    def test_every_pinned_file_matches(self):
        for path, digest in ((P.GC, P.GC_SHA), (P.COMPOSE, P.COMPOSE_SHA), (P.BUILD/'compose', P.FINALIZE_SHA),
                             (P.BUILD/'phase_runner.py', P.RUNNER_PHASE_SHA), (P.PROVISIONER, P.PROVISIONER_SHA),
                             (P.CANARY, P.CANARY_SHA), (P.PRIOR, P.PRIOR_SHA),
                             (P.CITY/'city.toml', P.CITY_SHA), (P.RECEIPT, P.RECEIPT_SHA)):
            self.assertEqual(P.read(path, digest) is not None, True, str(path))

    def test_revision_is_the_live_receipt_revision(self):
        receipt = json.loads(P.read(P.RECEIPT, P.RECEIPT_SHA))
        self.assertEqual(receipt['permission_revision'], P.REVISION)
        draft = json.loads(P.read(P.PRIOR, P.PRIOR_SHA))
        self.assertEqual(draft['permission_revision'], P.REVISION)

    def test_city_is_the_platform_managed_m5_city(self):
        manifest = json.loads(open('/home/loucmane/gascity/city/.gc/platform/install-manifest.json', 'rb').read())
        [managed] = [f for f in manifest['managed_files'] if f['destination'] == str(P.CITY/'city.toml')]
        self.assertEqual(managed['sha256'], P.CITY_SHA)

    def test_worktree_is_clean_at_base(self):
        git = ['git', '-c', 'core.fsmonitor=false', '-C', P.WORK, '--no-optional-locks']
        self.assertEqual(subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
                         'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88')
        self.assertEqual(subprocess.run(git + ['status', '--porcelain', '--untracked-files=all'],
                                        capture_output=True, text=True).stdout, '')

    def test_root_is_outside_repositories_and_holds_the_job_result(self):
        # Job ga-4z38-prep-r3 (e508fe84) consumed the root at 16:37Z with PREP PASS.
        self.assertTrue(str(P.ROOT).startswith('/var/tmp/'))
        with open(P.ROOT/'result.json') as handle:
            result = json.load(handle)
        self.assertTrue(result['ok'])
        self.assertEqual(result['city_after_sha256'], P.OVERLAY_SHA)
        self.assertEqual(result['receipt_after_sha256'], '392ea0b6c0a9a3c0cb88971b04c45b1326de50e9ea35c4e63c83bf1a602a3e46')


class Overlay(unittest.TestCase):
    def test_generator_reproduces_the_expected_overlay_from_live_config(self):
        city = P.read(P.CITY/'city.toml', P.CITY_SHA)
        candidate, patches, names, target, selected = P.build_overlay(city, live('config', 'show', '--json'),
                                                                      live('order', 'list', '--json'))
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), OVERLAY_SHA)
        self.assertEqual(len(names), 34)
        self.assertEqual(sum(1 for patch in patches if not patch['suspended']), 1)
        [open_patch] = [patch for patch in patches if not patch['suspended']]
        self.assertEqual((open_patch['dir'], open_patch['name'], open_patch['work_dir'], open_patch['max_active_sessions']),
                         ('gascity', 'implementation-worker', P.WORK, 1))

    def test_overlay_differs_from_the_city_only_by_cap_and_appended_block(self):
        city = P.read(P.CITY/'city.toml', P.CITY_SHA)
        candidate, *_ = P.build_overlay(city, live('config', 'show', '--json'), live('order', 'list', '--json'))
        head = city.replace(b'max_active_sessions = 16\n', b'max_active_sessions = 1\n', 1)
        self.assertTrue(candidate.startswith(head))
        self.assertIn(b'ga-4z38 bounded one-worker window', candidate[len(head):])
        self.assertNotIn(b'ga-y49e', candidate)


class R2(unittest.TestCase):
    def test_overlay_pin_matches_the_test_pin(self):
        self.assertEqual(P.OVERLAY_SHA, OVERLAY_SHA)

    def test_singleton_warning_is_exactly_the_observed_one(self):
        observed = '/var/tmp/ga-4z38-prep-20260923-r1/config.isolated.json'
        baseline = '/var/tmp/ga-4z38-prep-20260923-r1/config.baseline.json'
        with open(observed) as handle:
            after = json.load(handle)['validation']['warnings']
        with open(baseline) as handle:
            before = json.load(handle)['validation']['warnings']
        self.assertEqual([w for w in after if w not in before], [P.SINGLETON_WARNING])
        self.assertEqual(after, sorted(before + [P.SINGLETON_WARNING]))

    def test_launcher_pin(self):
        self.assertTrue(P.read(P.LAUNCH, P.LAUNCH_SHA))


class R3(unittest.TestCase):
    R1 = '/var/tmp/ga-4z38-prep-20260923-r1'

    def r1(self, name):
        with open(os.path.join(self.R1, name), 'rb') as handle:
            return handle.read()

    def test_r1_overlay_bytes_are_the_pinned_overlay(self):
        self.assertEqual(hashlib.sha256(self.r1('city.isolated.toml')).hexdigest(), P.OVERLAY_SHA)

    def test_expected_config_replays_the_r1_observation(self):
        baseline = json.loads(self.r1('config.baseline.json'))
        candidate, patches, names, target, selected = P.build_overlay(
            self.r1('city.baseline.toml'), baseline, json.loads(self.r1('orders.baseline.json')))
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), P.OVERLAY_SHA)
        self.assertEqual(P.expected_config(baseline, selected, target, names),
                         json.loads(self.r1('config.isolated.json')))

    def test_main_checks_the_launcher_before_creating_the_root(self):
        with open(os.path.join(HERE, 'prep-r11.py'), encoding='utf-8') as handle:
            body = handle.read().split('\ndef main():\n', 1)[1]
        self.assertLess(body.index("'prep must run under the source launcher'"), body.index('ROOT.mkdir('))

    def test_offline_proof_runs_the_exact_child_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            scratch = os.path.join(tmp, 'proof')
            done = subprocess.run([sys.executable, '-B', os.path.join(HERE, 'proof', 'prep-proof.py'), scratch],
                                  capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
            self.assertEqual(done.returncode, 0, done.stderr[-3000:])
            report = json.loads(done.stdout)
        self.assertTrue(report['ok'])
        self.assertEqual(report['orders_isolated']['orders'], [])
        self.assertEqual(report['d6ca85cd']['final_sha256'], P.RECEIPT_SHA)
        self.assertEqual(report['6b31d83a']['differences'], ['permission_revision', 'receipt_sha256'])


class Wrapper(unittest.TestCase):
    def test_wrapper_pins_prep_and_the_p6_launcher(self):
        with open(os.path.join(HERE, 'operator', 'PREP.sh'), encoding='utf-8') as handle:
            text = handle.read()
        [pin] = re.findall(r'^PREP_SHA=([0-9a-f]{64})$', text, re.M)
        with open(os.path.join(HERE, 'prep-r11.py'), 'rb') as handle:
            self.assertEqual(pin, hashlib.sha256(handle.read()).hexdigest())
        with open(os.path.join(HERE, '..', 'gct-m1wh-p6', 'source-launch.py'), 'rb') as handle:
            self.assertTrue(hashlib.sha256(handle.read()).hexdigest().startswith('31bdeea8'))
        self.assertIn('OUT=' + str(P.ROOT) + '\n', text)
        self.assertIn('exit "$rc"', text)


if __name__ == '__main__':
    unittest.main()
