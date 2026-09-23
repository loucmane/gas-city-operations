"""Tests for jobrunner.py. Run: python3 -B -m unittest test_jobrunner (from this directory).

Every test except LiveShape works in a temporary directory, and nothing touches the live queue or
systemd. LiveShape only reads: the start wrapper's pin, and the signature on the real worktree HEAD.
"""
import json
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location('jobrunner', os.path.join(HERE, 'jobrunner.py'))
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)

COMMIT = 'a' * 40
WRAPPER = J.PREFIX + 'gct-m1wh-canary/operator/CANARY.sh'


def transcript(agent, commit=COMMIT, verdict='SOURCE_PASS', wrapper=WRAPPER, prompt=None, handbacks=1,
               sidechain=True, extra=None):
    """A reviewer transcript in the Claude subagent JSONL shape."""
    first = prompt if prompt is not None else 'candidate=%s\n\nReview the package. Wrapper: %s\n' % (commit, wrapper)
    records = [{'type': 'user', 'agentId': agent, 'isSidechain': sidechain, 'message': {'role': 'user', 'content': first}},
               {'type': 'assistant', 'agentId': agent, 'isSidechain': sidechain,
                'message': {'content': [{'type': 'text', 'text': 'reading SOURCE_PASS %s maybe' % commit}]}}]
    for _ in range(handbacks):
        records.append({'type': 'assistant', 'agentId': agent, 'isSidechain': sidechain, 'message': {'content': [
            {'type': 'tool_use', 'name': 'SubagentHandback', 'input': {'message': '%s %s\nmust_fix: (none)' % (verdict, commit)}}]}})
    records.extend(extra or [])
    return '\n'.join(json.dumps(record) for record in records) + '\n'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.cfg = dict(J.CONFIG, stage=os.path.join(root, 'stage'), worktree=os.path.join(root, 'wt'), uid=os.getuid())
        self.where = J.paths(self.cfg)
        for name in ('queue', 'done', 'reviews', 'state'):
            os.makedirs(self.where[name])
        self.wrapper = os.path.join(self.cfg['worktree'], WRAPPER)
        os.makedirs(os.path.dirname(self.wrapper))
        with open(self.wrapper, 'w') as handle:
            handle.write('#!/bin/sh\necho ok\n')
        self.digest = J.sha(self.wrapper)
        self.review_dir = os.path.join(self.where['reviews'], COMMIT)
        os.makedirs(self.review_dir)
        self.reviews = [self.file_review('aaaa1111bbbb'), self.file_review('cccc2222dddd')]
        self.deps = {'head': lambda cfg: COMMIT, 'clean': lambda cfg: True, 'signed': lambda cfg, commit: True,
                     'blob_sha': lambda cfg, commit, rel: self.digest if rel == WRAPPER else None}
        self.launched = []

    def tearDown(self):
        self.tmp.cleanup()

    def file_review(self, agent, name=None, **kwargs):
        path = os.path.join(self.review_dir, name or 'agent-%s.jsonl' % agent)
        with open(path, 'w') as handle:
            handle.write(transcript(agent, **kwargs))
        return path

    def job(self, job_id='canary-r2', **changes):
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

    def refused(self, path, reason, deps=None):
        with self.assertRaises(J.Refuse) as caught:
            J.admit(self.cfg, path, deps or self.deps)
        self.assertIn(reason, str(caught.exception))
        if os.path.lexists(path) and not os.path.isdir(path):
            os.unlink(path)


class Admission(Fixture):
    def test_good_job_is_admitted(self):
        self.assertEqual(J.admit(self.cfg, self.job(), self.deps)['job_id'], 'canary-r2')

    def test_shape_refusals(self):
        self.refused(self.job(extra=1), 'job keys')
        path = self.job()
        with open(path, 'w') as handle:
            handle.write('{"job_id":"x","job_id":"y"}')
        self.refused(path, 'duplicate key')
        for changes, reason in (({'commit': 'A' * 40}, 'full lowercase'), ({'wrapper_sha256': 'b' * 63}, 'SHA-256'),
                                ({'wrapper': J.PREFIX + 'pkg/operator/../../x.sh'}, 'wrapper must'),
                                ({'wrapper': J.PREFIX + 'pkg/tools/X.sh'}, 'wrapper must'),
                                ({'wrapper': J.PREFIX + 'gct-jobrunner/operator/JOBRUNNER.sh'}, 'wrapper must'),
                                ({'wrapper': J.PREFIX + 'pkg/operator/x.sh'}, 'wrapper must')):
            self.refused(self.job(**changes), reason)
        self.refused(self.job(job_id='Bad_Id'), 'job_id must')

    def test_file_name_must_match_job_id(self):
        path = self.job()
        other = os.path.join(self.where['queue'], 'other.json')
        os.rename(path, other)
        self.refused(other, 'file name')

    def test_links_and_fifos_refused_without_blocking(self):
        path = self.job()
        link = os.path.join(self.where['queue'], 'canary-link.json')
        os.symlink(path, link)
        self.refused(link, 'cannot be opened safely')
        hard = os.path.join(self.tmp.name, 'hard.json')
        os.link(path, hard)
        self.refused(path, 'small regular file')
        fifo = os.path.join(self.where['queue'], 'fifo.json')
        os.mkfifo(fifo)
        self.refused(fifo, 'small regular file')

    def test_git_state_refusals(self):
        for key, value, reason in (('head', lambda cfg: 'b' * 40, 'HEAD'), ('clean', lambda cfg: False, 'clean'),
                                   ('signed', lambda cfg, commit: False, 'signature'),
                                   ('blob_sha', lambda cfg, commit, rel: 'c' * 64, 'committed wrapper blob')):
            self.refused(self.job(), reason, dict(self.deps, **{key: value}))

    def test_working_wrapper_must_match_committed_blob(self):
        with open(self.wrapper, 'a') as handle:
            handle.write('echo changed\n')
        self.refused(self.job(), 'working wrapper differs')

    def test_wrapper_symlink_refused(self):
        target = self.wrapper + '.real'
        os.rename(self.wrapper, target)
        os.symlink(target, self.wrapper)
        self.refused(self.job(), 'resolves elsewhere')

    def test_same_wrapper_at_same_commit_never_runs_twice(self):
        J.process(self.cfg, self.job('canary-r2'), self.deps, self.launch)
        self.refused(self.job('canary-r2b'), 'already ran at this commit')


class Reviews(Fixture):
    def test_any_filed_hold_refuses(self):
        self.file_review('eeee3333ffff', verdict='HOLD')
        self.refused(self.job(), 'does not pass the commit')

    def test_pass_text_outside_the_handback_does_not_count(self):
        self.file_review('eeee3333ffff', verdict='HOLD', extra=[{'type': 'assistant', 'agentId': 'eeee3333ffff',
                         'isSidechain': True, 'message': {'content': [{'type': 'text', 'text': 'SOURCE_PASS %s' % COMMIT}]}}])
        self.refused(self.job(), 'does not pass the commit')

    def test_prompt_binding(self):
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', prompt='Review this.\ncandidate=%s\n%s' % (COMMIT, WRAPPER))
        self.refused(self.job(), 'only candidate')
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', prompt='candidate=%s\ncandidate=%s %s' % (COMMIT, COMMIT, WRAPPER))
        self.refused(self.job(), 'only candidate')
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', wrapper='elsewhere')
        self.refused(self.job(), 'does not name the wrapper')

    def test_transcript_identity(self):
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', sidechain=False)
        self.refused(self.job(), 'reviewer subagent transcript')
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', name='agent-other0000.jsonl')
        self.refused(self.job(), 'named after its agent id')
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', handbacks=0)
        self.refused(self.job(), 'handback reports')
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', handbacks=2)
        self.refused(self.job(), 'handback reports')
        os.unlink(self.reviews[1])
        self.reviews[1] = self.file_review('cccc2222dddd', extra=[{'type': 'user', 'agentId': 'zzzz9999zzzz'}])
        self.refused(self.job(), 'mixes transcripts')

    def test_coordinator_transcript_is_refused(self):
        os.unlink(self.reviews[1])
        path = os.path.join(self.review_dir, 'agent-cccc2222dddd.jsonl')
        with open(path, 'w') as handle:
            handle.write(json.dumps({'type': 'user', 'message': {'content': 'candidate=%s %s' % (COMMIT, WRAPPER)}}) + '\n')
        self.refused(self.job(), 'reviewer subagent transcript')

    def test_same_review_twice_or_outside_the_directory(self):
        self.refused(self.job(reviews=[self.reviews[0], self.reviews[0]]), 'same reviewer')
        outside = os.path.join(self.tmp.name, 'agent-cccc2222dddd.jsonl')
        os.rename(self.reviews[1], outside)
        self.refused(self.job(reviews=[self.reviews[0], outside]), 'filed directly')


class Cycle(Fixture):
    def test_admitted_job_records_started_before_launch_and_runs_exact_argv(self):
        path = self.job()

        def launch(argv):
            self.assertTrue(os.path.exists(os.path.join(self.where['done'], 'canary-r2.started.json')))
            self.assertFalse(os.path.exists(path))
            return self.launch(argv)
        record = J.cycle(self.cfg, self.deps, launch)
        self.assertTrue(record['admitted'])
        self.assertEqual(self.launched, [[
            'systemd-run', '--user', '--wait', '--collect', '--quiet', '--unit=gc-job-canary-r2', '-p', 'UMask=0022',
            '/bin/sh', self.wrapper, COMMIT]])
        self.assertEqual(J.cycle(self.cfg, self.deps, self.launch), 'idle')

    def test_failure_halts_every_later_job(self):
        self.job()
        J.cycle(self.cfg, self.deps, lambda argv: (1, '', 'failed'))
        self.assertTrue(os.path.exists(self.where['halted']))
        self.job('next-job', wrapper=WRAPPER)
        self.assertEqual(J.cycle(self.cfg, self.deps, self.launch), 'halted')
        self.assertEqual(self.launched, [])

    def test_launch_error_halts(self):
        self.job()
        record = J.cycle(self.cfg, self.deps, lambda argv: ('launch-error', '', 'no systemd-run'))
        self.assertEqual(record['exit'], 'launch-error')
        self.assertTrue(os.path.exists(self.where['halted']))

    def test_pause_holds_the_queue(self):
        path = self.job()
        open(self.where['pause'], 'w').close()
        self.assertEqual(J.cycle(self.cfg, self.deps, self.launch), 'paused')
        self.assertTrue(os.path.exists(path))
        os.unlink(self.where['pause'])
        self.assertTrue(J.cycle(self.cfg, self.deps, self.launch)['admitted'])

    def test_more_than_one_queued_job_runs_nothing(self):
        self.job('first')
        self.job('second')
        self.assertEqual(J.cycle(self.cfg, self.deps, self.launch), 'multiple')
        self.assertEqual(self.launched, [])

    def test_unfinished_job_blocks_until_resolved(self):
        with open(os.path.join(self.where['done'], 'crashed.started.json'), 'w') as handle:
            json.dump({'job': {'commit': 'b' * 40, 'wrapper': WRAPPER}}, handle)
        self.job()
        self.assertEqual(J.cycle(self.cfg, self.deps, self.launch), 'unfinished crashed')
        with open(os.path.join(self.where['done'], 'crashed.resolved.json'), 'w') as handle:
            handle.write('{}')
        self.assertTrue(J.cycle(self.cfg, self.deps, self.launch)['admitted'])

    def test_replayed_job_id_is_refused(self):
        self.job()
        J.cycle(self.cfg, self.deps, self.launch)
        record = J.process(self.cfg, self.job(), self.deps, self.launch)
        self.assertFalse(record['admitted'])
        self.assertIn('already used', record['refusal'])
        self.assertEqual(len(self.launched), 1)

    def test_refusal_is_recorded_and_dequeued_without_launch(self):
        path = self.job(wrapper_sha256='c' * 64)
        record = J.cycle(self.cfg, self.deps, self.launch)
        self.assertFalse(record['admitted'])
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.launched, [])
        self.assertFalse(os.path.exists(self.where['halted']))

    def test_directory_in_queue_is_moved_aside(self):
        os.mkdir(os.path.join(self.where['queue'], 'weird.json'))
        record = J.cycle(self.cfg, self.deps, self.launch)
        self.assertFalse(record['admitted'])
        self.assertEqual(os.listdir(self.where['queue']), [])


class Identity(unittest.TestCase):
    def test_only_the_runner_unit_passes(self):
        good = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gas-city-jobrunner.service\n'
        self.assertIsNone(J.own_unit(J.CONFIG, good, {'INVOCATION_ID': 'x'}))
        for text, environ in (
                (good.replace('gas-city-jobrunner', 'gc-job-x'), {'INVOCATION_ID': 'x'}),
                (good, {}),
                ('12:pids:/x\n' + good, {'INVOCATION_ID': 'x'}),
                ('0::/user.slice/user-1000.slice/session-3.scope\n', {'INVOCATION_ID': 'x'})):
            self.assertIsNotNone(J.own_unit(J.CONFIG, text, environ))


class RealGit(unittest.TestCase):
    def test_helpers_against_a_temporary_repository(self):
        with tempfile.TemporaryDirectory() as root:
            env = dict(J.ENV, HOME=root, GIT_CONFIG_NOSYSTEM='1')
            run = lambda *args: subprocess.run(['git', '-C', root, *args], check=True, capture_output=True, env=env)
            run('init', '-q')
            os.makedirs(os.path.join(root, os.path.dirname(WRAPPER)))
            with open(os.path.join(root, WRAPPER), 'w') as handle:
                handle.write('echo\n')
            run('add', '-A')
            run('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'x')
            cfg = dict(J.CONFIG, worktree=root)
            head = J.real_head(cfg)
            self.assertRegex(head, '^[0-9a-f]{40}$')
            self.assertTrue(J.real_clean(cfg))
            self.assertEqual(J.real_blob_sha(cfg, head, WRAPPER), J.sha(os.path.join(root, WRAPPER)))
            self.assertIsNone(J.real_blob_sha(cfg, head, J.PREFIX + 'other/operator/X.sh'))
            self.assertIsNone(J.real_blob_sha(cfg, head, os.path.dirname(WRAPPER)))
            self.assertFalse(J.real_signed(cfg, head))
            with open(os.path.join(root, 'new.txt'), 'w') as handle:
                handle.write('x')
            self.assertFalse(J.real_clean(cfg))


class LiveShape(unittest.TestCase):
    def test_start_wrapper_pins_this_runner_and_the_p6_launcher(self):
        with open(os.path.join(HERE, 'operator', 'JOBRUNNER.sh'), encoding='utf-8') as handle:
            text = handle.read()
        [pin] = re.findall(r'^RUNNER_SHA=([0-9a-f]{64})$', text, re.M)
        self.assertEqual(pin, J.sha(os.path.join(HERE, 'jobrunner.py')))
        self.assertEqual(J.sha(os.path.join(HERE, '..', 'gct-m1wh-p6', 'source-launch.py')),
                         '31bdeea8' + J.sha(os.path.join(HERE, '..', 'gct-m1wh-p6', 'source-launch.py'))[8:])
        self.assertIn('--no-optional-locks status --porcelain --untracked-files=all', text)

    def test_real_worktree_head_verifies_against_the_operator_key(self):
        self.assertTrue(J.real_signed(J.CONFIG, J.real_head(J.CONFIG)))

    def test_configuration(self):
        self.assertEqual(J.CONFIG['worktree'], '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap')
        self.assertEqual(J.CONFIG['signer'], '7720D1FE503A88EDECA61A6F0C7D823543E01875')
        self.assertTrue(J.WRAPPER.fullmatch(WRAPPER))
        self.assertIsNone(J.WRAPPER.fullmatch(J.PREFIX + 'gct-jobrunner/operator/JOBRUNNER.sh'))


if __name__ == '__main__':
    unittest.main()
