"""Tests for jobrunner.py. Run: python3 -B -m unittest test_jobrunner (from this directory).

Every test works in a temporary directory. Nothing touches the live queue, the worktree or systemd.
The real git helpers are exercised against a temporary repository.
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('jobrunner', os.path.join(HERE, 'jobrunner.py'))
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)

COMMIT = 'a' * 40
WRAPPER = J.PREFIX + 'gct-m1wh-canary/operator/CANARY.sh'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.cfg = dict(J.CONFIG, stage=os.path.join(root, 'stage'), worktree=os.path.join(root, 'wt'),
                        uid=os.getuid())
        self.where = J.paths(self.cfg)
        for name in ('queue', 'done', 'reviews', 'state'):
            os.makedirs(self.where[name])
        self.wrapper = os.path.join(self.cfg['worktree'], WRAPPER)
        os.makedirs(os.path.dirname(self.wrapper))
        with open(self.wrapper, 'w') as handle:
            handle.write('#!/bin/sh\necho ok\n')
        self.digest = J.sha(self.wrapper)
        review_dir = os.path.join(self.where['reviews'], COMMIT)
        os.makedirs(review_dir)
        self.reviews = []
        for index in (1, 2):
            path = os.path.join(review_dir, 'r%d.jsonl' % index)
            with open(path, 'w') as handle:
                handle.write('{"prompt":"candidate=%s lens %d"}\n{"text":"SOURCE_PASS %s\\nmust_fix: (none)"}\n'
                             % (COMMIT, index, COMMIT))
            self.reviews.append(path)
        self.deps = {'head': lambda cfg: COMMIT, 'clean': lambda cfg: True,
                     'signed': lambda cfg, commit: True, 'tracked': lambda cfg, commit, rel: rel == WRAPPER}
        self.launched = []

    def tearDown(self):
        self.tmp.cleanup()

    def job(self, job_id='canary-r1', **changes):
        value = {'job_id': job_id, 'commit': COMMIT, 'wrapper': WRAPPER, 'wrapper_sha256': self.digest,
                 'reviews': self.reviews}
        value.update(changes)
        path = os.path.join(self.where['queue'], job_id + '.json')
        with open(path, 'w') as handle:
            json.dump(value, handle)
        return path

    def launch(self, argv):
        self.launched.append(argv)
        return 0, '', ''

    def refused(self, path, deps=None):
        with self.assertRaises(J.Refuse):
            J.admit(self.cfg, path, deps or self.deps)


class Admission(Fixture):
    def test_good_job_is_admitted(self):
        self.assertEqual(J.admit(self.cfg, self.job(), self.deps)['job_id'], 'canary-r1')

    def test_shape_refusals(self):
        self.refused(self.job(extra=1))
        path = self.job()
        with open(path, 'w') as handle:
            handle.write('{"job_id":"x","job_id":"y"}')
        self.refused(path)
        for changes in ({'commit': 'A' * 40}, {'commit': 'a' * 39}, {'wrapper_sha256': 'b' * 63},
                        {'wrapper': J.PREFIX + 'pkg/operator/../../x.sh'}, {'wrapper': J.PREFIX + 'pkg/tools/X.sh'},
                        {'wrapper': '/etc/X.sh'}, {'wrapper': J.PREFIX + 'pkg/operator/x.sh'}, {'reviews': self.reviews[:1]},
                        {'reviews': [self.reviews[0], self.reviews[0]]}):
            self.refused(self.job(**changes))
        self.refused(self.job(job_id='Bad_Id'))

    def test_file_name_must_match_job_id(self):
        path = self.job()
        other = os.path.join(self.where['queue'], 'other.json')
        os.rename(path, other)
        self.refused(other)

    def test_symlinked_or_hardlinked_job_refused(self):
        path = self.job()
        link = os.path.join(self.where['queue'], 'linked.json')
        os.symlink(path, link)
        self.refused(link)
        hard = os.path.join(self.tmp.name, 'hard.json')
        os.link(path, hard)
        self.refused(path)

    def test_git_state_refusals(self):
        for key, value in (('head', lambda cfg: 'b' * 40), ('clean', lambda cfg: False),
                           ('signed', lambda cfg, commit: False), ('tracked', lambda cfg, commit, rel: False)):
            self.refused(self.job(), dict(self.deps, **{key: value}))

    def test_wrapper_digest_and_symlink_refused(self):
        self.refused(self.job(wrapper_sha256='c' * 64))
        target = self.wrapper + '.real'
        os.rename(self.wrapper, target)
        os.symlink(target, self.wrapper)
        self.refused(self.job())

    def test_review_content_refusals(self):
        for body in ('SOURCE_PASS %s' % COMMIT, 'candidate=%s' % COMMIT,
                     'candidate=%s SOURCE_PASS %s HOLD %s' % (COMMIT, COMMIT, COMMIT)):
            with open(self.reviews[1], 'w') as handle:
                handle.write(body)
            self.refused(self.job())

    def test_review_outside_commit_dir_refused(self):
        other_dir = os.path.join(self.where['reviews'], 'b' * 40)
        os.makedirs(other_dir)
        moved = os.path.join(other_dir, 'r2.jsonl')
        os.rename(self.reviews[1], moved)
        self.refused(self.job(reviews=[self.reviews[0], moved]))
        link = os.path.join(self.where['reviews'], COMMIT, 'r3.jsonl')
        os.symlink(moved, link)
        self.refused(self.job(reviews=[self.reviews[0], link]))


class Processing(Fixture):
    def test_admitted_job_records_started_before_launch_and_runs_exact_argv(self):
        path = self.job()

        def launch(argv):
            self.assertTrue(os.path.exists(os.path.join(self.where['done'], 'canary-r1.started.json')))
            self.assertFalse(os.path.exists(path))
            return self.launch(argv)
        record = J.process(self.cfg, path, self.deps, launch)
        self.assertTrue(record['admitted'])
        self.assertEqual(self.launched, [[
            'systemd-run', '--user', '--wait', '--collect', '--quiet', '--unit=gc-job-canary-r1', '-p', 'UMask=0022',
            '/bin/sh', self.wrapper, COMMIT]])
        with open(os.path.join(self.where['done'], 'canary-r1.json')) as handle:
            self.assertEqual(json.load(handle)['exit'], 0)

    def test_replay_after_crash_is_refused(self):
        J.process(self.cfg, self.job(), self.deps, self.launch)
        os.unlink(os.path.join(self.where['done'], 'canary-r1.json'))
        record = J.process(self.cfg, self.job(), self.deps, self.launch)
        self.assertFalse(record['admitted'])
        self.assertIn('already used', record['refusal'])
        self.assertEqual(len(self.launched), 1)

    def test_refusal_is_recorded_and_dequeued_without_launch(self):
        path = self.job(wrapper_sha256='c' * 64)
        record = J.process(self.cfg, path, self.deps, self.launch)
        self.assertFalse(record['admitted'])
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.launched, [])
        self.assertEqual(len([n for n in os.listdir(self.where['done']) if '.refused-' in n]), 1)

    def test_directory_in_queue_is_moved_aside(self):
        path = os.path.join(self.where['queue'], 'weird.json')
        os.mkdir(path)
        record = J.process(self.cfg, path, self.deps, self.launch)
        self.assertFalse(record['admitted'])
        self.assertFalse(os.path.exists(path))

    def test_launch_error_is_recorded(self):
        record = J.process(self.cfg, self.job(), self.deps, lambda argv: ('launch-error', '', 'no systemd-run'))
        self.assertEqual(record['exit'], 'launch-error')


class RealGit(unittest.TestCase):
    def test_head_clean_tracked_against_a_temporary_repository(self):
        with tempfile.TemporaryDirectory() as root:
            env = dict(J.ENV, HOME=root, GIT_CONFIG_NOSYSTEM='1')
            run = lambda *args: subprocess.run(['git', '-C', root, *args], check=True, capture_output=True, env=env)
            run('init', '-q')
            os.makedirs(os.path.join(root, os.path.dirname(WRAPPER)))
            with open(os.path.join(root, WRAPPER), 'w') as handle:
                handle.write('echo\n')
            run('add', '-A')
            run('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-c', 'commit.gpgsign=false',
                'commit', '-qm', 'x')
            cfg = dict(J.CONFIG, worktree=root)
            head = J.real_head(cfg)
            self.assertRegex(head, '^[0-9a-f]{40}$')
            self.assertTrue(J.real_clean(cfg))
            self.assertTrue(J.real_tracked(cfg, head, WRAPPER))
            self.assertFalse(J.real_tracked(cfg, head, J.PREFIX + 'other/operator/X.sh'))
            self.assertFalse(J.real_signed(cfg, head))
            with open(os.path.join(root, 'new.txt'), 'w') as handle:
                handle.write('x')
            self.assertFalse(J.real_clean(cfg))


class Wrapper(unittest.TestCase):
    def test_start_wrapper_pins_this_runner_and_the_p6_launcher(self):
        import re
        with open(os.path.join(HERE, 'operator', 'JOBRUNNER.sh'), encoding='utf-8') as handle:
            text = handle.read()
        [pin] = re.findall(r'^RUNNER_SHA=([0-9a-f]{64})$', text, re.M)
        self.assertEqual(pin, J.sha(os.path.join(HERE, 'jobrunner.py')))
        self.assertTrue(J.sha(os.path.join(HERE, '..', 'gct-m1wh-p6', 'source-launch.py')).startswith('31bdeea8'))
        self.assertIn('--no-optional-locks status --porcelain', text)


class LiveShape(unittest.TestCase):
    def test_configuration_names_the_ga_e0t1_worktree_and_operator_key(self):
        self.assertEqual(J.CONFIG['worktree'], '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap')
        self.assertEqual(J.CONFIG['signer'], '7720D1FE503A88EDECA61A6F0C7D823543E01875')
        self.assertTrue(J.WRAPPER.fullmatch(WRAPPER))
        for key in ('SSH_AUTH_SOCK', 'GNUPGHOME', 'GC_HOME'):
            self.assertNotIn(key, J.ENV)


if __name__ == '__main__':
    unittest.main()
