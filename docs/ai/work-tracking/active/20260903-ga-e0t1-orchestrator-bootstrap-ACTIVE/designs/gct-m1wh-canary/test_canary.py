"""Tests for canary-run.py. Run: python3 -B -m unittest test_canary (from this directory).

The pin tests read the live files read-only. Every other test is pure and touches no live state.
"""
import copy
import hashlib
import importlib.util
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('canary_run', os.path.join(HERE, 'canary-run.py'))
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def good_receipt(receipt_sha='a' * 64):
    return {
        'schema': 'gc.canary-receipt.v2', 'canary_run_id': C.RUN_ID, 'result': 'pass',
        'receipt_sha256': receipt_sha,
        'profile': {'name': C.PROFILE, 'profile_kind': 'signing', 'sha256': C.PROFILE_SHA},
        'runner': {'path': C.RUNNER, 'sha256': C.RUNNER_SHA},
        'environment': {
            'provisioning_receipt_sha256': C.PROVISIONING_SELF,
            'gc_binary': {'commit': C.BASE, 'sha256': C.GC_SHA},
            'template_commit': C.TEMPLATE_COMMIT,
            'permission_revision': C.PERMISSION_REVISION,
            'profiles': [{'name': C.PROFILE, 'sha256': C.PROFILE_SHA}],
        },
        'provisioning_receipt': {'receipt_sha256': C.PROVISIONING_SELF, 'template_commit': C.TEMPLATE_COMMIT},
        'scenarios': [{'name': name, 'outcome': 'pass', 'attention_latency_cycles': 1 if name == 'unreadable-mail' else 0}
                      for name in sorted(C.SCENARIOS)],
    }


class LivePins(unittest.TestCase):
    def test_file_pins_match_live_bytes(self):
        state = C.pins()
        self.assertEqual(set(state), {'gc', 'runner', 'provisioning', 'manifest', 'install_receipt', 'legacy',
                                      'legacy_history', 'control_policy'})

    def test_provisioning_receipt_declares_the_pinned_profile_and_runner(self):
        with open(C.PROVISIONING, 'rb') as handle:
            receipt = C.strict_json(handle.read(), 'provisioning')
        self.assertEqual(receipt['receipt_sha256'], C.PROVISIONING_SELF)
        self.assertEqual(receipt['canary_runner'], {'path': C.RUNNER, 'sha256': C.RUNNER_SHA})
        self.assertEqual(receipt['template_commit'], C.TEMPLATE_COMMIT)
        self.assertEqual(receipt['permission_revision'], C.PERMISSION_REVISION)
        [profile] = receipt['profiles']
        self.assertEqual((profile['name'], profile['profile_kind'], profile['worker_profile_sha256']),
                         (C.PROFILE, C.PROFILE_KIND, C.PROFILE_SHA))
        self.assertEqual(profile['control_policy'], {'path': C.CONTROL_POLICY, 'sha256': C.CONTROL_POLICY_SHA})

    def test_install_manifest_names_the_gc_binary_and_base(self):
        with open(C.MANIFEST, 'rb') as handle:
            manifest = json.loads(handle.read())
        self.assertEqual(manifest['core']['sha256'], C.GC_SHA)
        self.assertEqual(manifest['activation']['expected_commit'], C.BASE)

    def test_runner_scenario_set_matches(self):
        with open(C.RUNNER, encoding='utf-8') as handle:
            text = handle.read()
        block = re.search(r'^SCENARIOS = \{(.*?)^\}', text, re.S | re.M).group(1)
        names = set(re.findall(r'"([a-z-]+)"', block))
        self.assertEqual(names - {'candidate-launcher'}, set(C.SCENARIOS))
        self.assertIn('VERSION = 3\n', text)

    def test_profile_receipt_path_is_the_core_hash_slot(self):
        digest = hashlib.sha256(b'gascity/gc.implementation-worker').hexdigest()
        self.assertEqual(C.PROFILE_RECEIPT, C.CITY + '/.gc/runtime/canary/profiles/' + digest + '.json')


class Invocation(unittest.TestCase):
    def test_argv_is_exact(self):
        self.assertEqual(C.canary_argv(), [
            C.GC, '--city', C.CITY, 'platform', 'canary', '--run-id', 'm1wh-20260923-r2',
            '--runner', C.RUNNER, '--runner-sha256', C.RUNNER_SHA,
            '--launcher-source', '/tmp/ga-mutg-build-20260919/repro-source', '--base-commit', C.BASE,
            '--scratch-root', '/home/loucmane/gascity/canary-evidence',
            '--profile', 'gascity/gc.implementation-worker', '--profile-kind', 'signing',
            '--max-wall-time', '30m0s'])

    def test_env_is_fixed_and_excludes_test_switches_and_agent(self):
        env = C.child_env()
        self.assertEqual(env['GC_HOME'], '/home/loucmane/gascity/home')
        self.assertEqual(env['GC_BIN'], C.GC)
        self.assertTrue(env['PATH'].startswith('/home/loucmane/gascity/bin:'))
        self.assertEqual(env['GC_STORE_PATH'],
                         '/home/loucmane/gascity/canary-evidence/m1wh-20260923-r2/clean-launcher/launcher')
        for key in env:
            self.assertFalse(key.startswith('GCT_'), key)
        for key in ('SSH_AUTH_SOCK', 'GC_SUPERVISOR_PRESERVE_SESSIONS_ON_SIGNAL', 'TMUX'):
            self.assertNotIn(key, env)

    def test_run_id_is_safe_and_sockets_fit(self):
        self.assertRegex(C.RUN_ID, r'^[A-Za-z0-9._-]{1,64}$')
        self.assertLessEqual(max(C.socket_lengths().values()), 107)
        self.assertEqual(len(C.socket_lengths()), 9)


class Wrapper(unittest.TestCase):
    def test_wrapper_pins_this_canary_run_and_the_p6_launcher(self):
        with open(os.path.join(HERE, 'operator', 'CANARY.sh'), encoding='utf-8') as handle:
            text = handle.read()
        [pin] = re.findall(r'^RUN_SHA=([0-9a-f]{64})$', text, re.M)
        with open(os.path.join(HERE, 'canary-run.py'), 'rb') as handle:
            self.assertEqual(pin, hashlib.sha256(handle.read()).hexdigest())
        with open(os.path.join(HERE, '..', 'gct-m1wh-p6', 'source-launch.py'), 'rb') as handle:
            self.assertTrue(hashlib.sha256(handle.read()).hexdigest().startswith('31bdeea8'))
        self.assertIn(C.OUT, text)


class Stdout(unittest.TestCase):
    def line(self, digest='b' * 64, path=None, run_id=None):
        return 'platform canary result=pass run_id="%s" receipt_sha256=%s receipt=%s\n' % (
            run_id or C.RUN_ID, digest, path or C.PROFILE_RECEIPT)

    def test_accepts_the_exact_pass_line(self):
        self.assertEqual(C.parse_stdout(self.line()), 'b' * 64)

    def test_rejects_extra_lines_wrong_path_wrong_run(self):
        for text in (self.line() + 'extra\n', self.line(path=C.CITY + '/.gc/runtime/canary/receipt.json'),
                     self.line(run_id='other'), '', self.line().replace('result=pass', 'result=fail')):
            with self.assertRaises(C.Stop):
                C.parse_stdout(text)


class Receipt(unittest.TestCase):
    def test_good_receipt_passes(self):
        latencies = C.verify_receipt(good_receipt(), 'a' * 64)
        self.assertEqual(len(latencies), 9)

    def test_each_binding_refuses(self):
        mutations = [
            lambda r: r.__setitem__('schema', 'gc.canary-receipt.v1'),
            lambda r: r['profile'].__setitem__('profile_kind', 'candidate'),
            lambda r: r['profile'].__setitem__('sha256', 'c' * 64),
            lambda r: r['runner'].__setitem__('sha256', 'c' * 64),
            lambda r: r['environment'].__setitem__('provisioning_receipt_sha256', 'c' * 64),
            lambda r: r['environment']['gc_binary'].__setitem__('commit', 'c' * 40),
            lambda r: r['environment'].__setitem__('permission_revision', 'c' * 64),
            lambda r: r['provisioning_receipt'].__setitem__('receipt_sha256', 'c' * 64),
            lambda r: r['scenarios'].pop(),
            lambda r: r['scenarios'][0].__setitem__('attention_latency_cycles', 2),
            lambda r: r['scenarios'][0].__setitem__('outcome', 'fail'),
            lambda r: r.__setitem__('canary_run_id', 'other'),
        ]
        for mutate in mutations:
            receipt = copy.deepcopy(good_receipt())
            mutate(receipt)
            with self.assertRaises(C.Stop):
                C.verify_receipt(receipt, 'a' * 64)
        with self.assertRaises(C.Stop):
            C.verify_receipt(good_receipt(), 'd' * 64)

    def test_duplicate_keys_refuse(self):
        with self.assertRaises(C.Stop):
            C.strict_json(b'{"a":1,"a":2}', 'x')


class Deltas(unittest.TestCase):
    def test_expected_additions_and_changes(self):
        before = {'receipt.json': {'type': 'file', 'sha256': '1'}, 'history': {'type': 'dir', 'mode': '0o700'}}
        after = dict(before)
        additions = C.expected_additions('e' * 64)
        for name in additions:
            after[name] = {'type': 'file'}
        added, removed, changed = C.tree_delta(before, after)
        self.assertEqual((added, removed, changed), (additions, [], []))
        after['receipt.json'] = {'type': 'file', 'sha256': '2'}
        self.assertEqual(C.tree_delta(before, after)[2], ['receipt.json'])

    def test_leftover_matcher(self):
        rows = [(10, ['tmux', '-L', 'canary-' + C.RUN_ID, 'new-session'], '/'),
                (11, ['dolt', 'sql-server'], C.RUN_ROOT + '/clean-launcher/city'),
                (12, ['gc', 'supervisor', 'run'], '/home/loucmane/gascity/city'),
                (13, ['bash'], C.RUN_ROOT + '-other'),
                (14, [C.RUNNER, '--scenario', 'detached-head', '--run-id', C.RUN_ID], C.LAUNCHER),
                (15, ['python3'], ''),
                (16, ['sh'], C.LAUNCHER),
                # The job runner's own processes must never match.
                (17, ['/usr/bin/python3', '-I', '-S', '-B', '/x/gct-m1wh-p6/source-launch.py', '/x/gct-jobrunner/jobrunner.py',
                      'f' * 64], '/home/loucmane'),
                (18, ['systemd-run', '--user', '--wait', '--collect', '--quiet', '--service-type=oneshot',
                      '--unit=gc-job-canary-r2', '-p', 'UMask=0022', '/bin/sh', '/x/operator/CANARY.sh', 'a' * 40], '/home/loucmane'),
                (19, ['/bin/sh', '/x/gct-m1wh-canary/operator/CANARY.sh', 'a' * 40], '/home/loucmane')]
        self.assertEqual([hit['pid'] for hit in C.leftovers(rows)], [10, 11, 14, 16])

    def test_cache_slots_are_present_live(self):
        for slot in C.CACHE_SLOTS:
            self.assertTrue(os.path.isdir(os.path.join(C.CACHE_REPOS, slot)), slot)


class MainFlow(unittest.TestCase):
    """Drive main() with a fake gc and a temporary canary tree; no live state is touched."""

    def setUp(self):
        import tempfile
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.canary = os.path.join(root, 'canary')
        os.makedirs(os.path.join(self.canary, 'history'))
        with open(os.path.join(self.canary, 'receipt.json'), 'w') as handle:
            handle.write('{}')
        self.run_root = os.path.join(root, 'run')
        os.makedirs(os.path.join(root, 'cache', 'slot'))
        self.receipt = os.path.join(self.canary, 'profiles', 'p.json')
        self.patches = [
            mock.patch.object(C, 'OUT', os.path.join(root, 'out')),
            mock.patch.object(C, 'CANARY_DIR', self.canary),
            mock.patch.object(C, 'PROFILE_RECEIPT', self.receipt),
            mock.patch.object(C, 'RUN_ROOT', self.run_root),
            mock.patch.object(C, 'CACHE_REPOS', os.path.join(root, 'cache')),
            mock.patch.object(C, 'supervisor_identity', lambda: {'pid': 1, 'starttime': 2, 'mnt': 'm'}),
            mock.patch.object(C, 'process_table', lambda: []),
            mock.patch.object(C, 'precheck', self.fake_precheck),
            mock.patch.object(C, 'pins', lambda: {}),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp.cleanup()

    def fake_precheck(self):
        return {'supervisor': C.supervisor_identity(), 'pins': {}, 'canary_tree': C.tree(C.CANARY_DIR),
                'cache_repos': sorted(os.listdir(C.CACHE_REPOS)), 'sockets': {}}

    def run_main(self, rc=0, stdout=b'', stderr=b'', publish=None, timeout=False):
        from unittest import mock
        import subprocess

        real_run = subprocess.run

        def fake_run(*args, **kwargs):
            if args[0][0] != C.GC:
                return real_run(*args, **kwargs)
            if publish:
                publish()
            if timeout:
                raise subprocess.TimeoutExpired('gc', 1, output=b'', stderr=b'slow')
            return subprocess.CompletedProcess(args, rc, stdout, stderr)
        with mock.patch.object(C.subprocess, 'run', fake_run):
            code = C.main()
        with open(os.path.join(C.OUT, 'result.json')) as handle:
            return code, json.load(handle)

    def publish(self, receipt_sha='e' * 64, body=None):
        os.makedirs(os.path.dirname(self.receipt), mode=0o700)
        raw = json.dumps(body if body is not None else good_receipt(receipt_sha)).encode()
        for path in (self.receipt, os.path.join(self.canary, 'history', receipt_sha + '.json')):
            with open(path, 'wb') as handle:
                handle.write(raw)
            os.chmod(path, 0o600)
        for name in C.SCENARIOS:
            os.makedirs(os.path.join(self.run_root, name, 'evidence'), exist_ok=True)
            with open(os.path.join(self.run_root, name, 'evidence', 'scenario.json'), 'w') as handle:
                handle.write('{}')

    def pass_line(self, receipt_sha='e' * 64):
        return ('platform canary result=pass run_id="%s" receipt_sha256=%s receipt=%s\n'
                % (C.RUN_ID, receipt_sha, self.receipt)).encode()

    def test_failed_gc_publishes_nothing_and_stops(self):
        code, result = self.run_main(rc=3, stderr=b'\xff broken utf-8 GC_STORE_PATH is required')
        self.assertEqual((code, result['ok'], result['stage']), (1, False, 'verify'))
        self.assertIn('did not pass', result['error'])
        for name in ('canary.stdout', 'canary.stderr', 'canary.exit', 'after.json'):
            self.assertTrue(os.path.exists(os.path.join(C.OUT, name)), name)

    def test_failed_gc_with_live_additions_stops_loudly(self):
        code, result = self.run_main(rc=3, publish=self.publish)
        self.assertFalse(result['ok'])
        self.assertIn('live canary files appeared', result['error'])

    def test_timeout_is_not_a_pass(self):
        code, result = self.run_main(timeout=True)
        self.assertFalse(result['ok'])

    def test_pin_drift_after_the_run_keeps_after_json(self):
        from unittest import mock

        def drift():
            raise C.Stop('runner digest drift')
        with mock.patch.object(C, 'pins', drift):
            code, result = self.run_main(rc=3)
        self.assertIn('pinned file drift', result['error'])
        self.assertTrue(os.path.exists(os.path.join(C.OUT, 'after.json')))

    def test_good_run_passes(self):
        code, result = self.run_main(rc=0, stdout=self.pass_line(), publish=self.publish)
        self.assertEqual((code, result['ok'], result['stage']), (0, True, 'done'), result.get('error'))
        self.assertEqual(result['receipt']['receipt_sha256'], 'e' * 64)

    def test_published_but_wrong_receipt_is_refused(self):
        bad = good_receipt('e' * 64)
        bad['profile']['profile_kind'] = 'candidate'
        code, result = self.run_main(rc=0, stdout=self.pass_line(), publish=lambda: self.publish(body=bad))
        self.assertFalse(result['ok'])
        self.assertIn('profile', result['error'])

    def test_live_cache_slot_change_stops_a_published_pass(self):
        def publish_and_fetch():
            self.publish()
            os.makedirs(os.path.join(C.CACHE_REPOS, 'new-slot'))
        code, result = self.run_main(rc=0, stdout=self.pass_line(), publish=publish_and_fetch)
        self.assertFalse(result['ok'])
        self.assertIn('pack-cache slots changed', result['error'])

    def test_missing_scenario_evidence_is_refused(self):
        def publish_partial():
            self.publish()
            os.unlink(os.path.join(self.run_root, 'missing-provider', 'evidence', 'scenario.json'))
        code, result = self.run_main(rc=0, stdout=self.pass_line(), publish=publish_partial)
        self.assertIn('missing scenario.json', result['error'])


if __name__ == '__main__':
    unittest.main()
