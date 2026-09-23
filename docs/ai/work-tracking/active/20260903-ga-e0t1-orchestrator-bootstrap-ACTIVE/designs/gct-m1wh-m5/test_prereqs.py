"""Behavioural tests for prereqs.py against a sandboxed fake city and a real temporary Git repository.

The live paths are redirected into a temporary directory. The city files are real
predecessor bytes: the r5/i/00 city backup, the live or preserved registry and
rig fragment, and copies of the live agent definitions. The CLI binaries are
small scripts. The Template is a two-commit repository with the untracked set
the live checkout carries. The quiet-host observation is stubbed per test,
because its live form runs only in the supervisor namespaces. quiet_slot is
tested separately with a fake clock and fake observer.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest

HERE = Path(__file__).parent
O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'


def load(name, filename):
    path = HERE/filename
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


candidate = load('candidate_for_prereqs', 'manifest_candidate.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def preserved(live, backup, expected):
    raw = Path(live).read_bytes()
    if sha(raw) != expected:
        raw = Path(backup).read_bytes()
    assert sha(raw) == expected
    return raw


CITY_OLD_BYTES = Path(O + '/reports/r5/i/00').read_bytes()
REGISTRY_OLD_BYTES = preserved('/home/loucmane/gascity/city/managed/rig-permissions.json',
                               O + '/reports/m5-inputs/rig-permissions.json.before', candidate.REGISTRY_OLD)
RIG_OLD_BYTES = preserved('/home/loucmane/gascity/city/managed/rig-permissions.toml',
                          O + '/reports/m5-inputs/rig-permissions.toml.before', candidate.RIGPERM_OLD)
GIT_ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t',
           'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}


def git(repo, *args):
    return subprocess.run(['/usr/bin/git', '-C', str(repo), *args], env=GIT_ENV, capture_output=True,
                          text=True, check=True).stdout.strip()


class Sandbox:
    def __init__(self, tmp):
        self.tmp = tmp
        self.p = load('prereqs_under_test', 'prereqs.py')
        p = self.p
        city = tmp/'city'
        (city/'managed').mkdir(parents=True)
        (city/'.gc/platform').mkdir(parents=True)
        (city/'.gc/runtime').mkdir(parents=True)
        shutil.copytree('/home/loucmane/gascity/city/agents', city/'agents',
                        ignore=lambda d, names: [n for n in names if (Path(d)/n).is_file() and n != 'agent.toml'])
        (city/'city.toml').write_bytes(CITY_OLD_BYTES)
        (city/'managed/rig-permissions.json').write_bytes(REGISTRY_OLD_BYTES)
        (city/'managed/rig-permissions.toml').write_bytes(RIG_OLD_BYTES)
        (city/'.gc/platform/install-manifest.json').write_bytes(b'installed-r9\n')
        (city/'.gc/runtime/suspension-state.json').write_bytes(b'suspended\n')
        (tmp/'bin').mkdir()
        old_cli = b'#!/bin/sh\necho "2.1.263 (Claude Code)"\n'
        self.new_cli = b'#!/bin/sh\necho "2.1.280 (Claude Code)"\n'
        (tmp/'bin/claude').write_bytes(old_cli); os.chmod(tmp/'bin/claude', 0o755)
        (tmp/'staged').write_bytes(self.new_cli)
        (tmp/'ops/reports/r5/i').mkdir(parents=True)
        (tmp/'ops/reports/r5/i/00').write_bytes(CITY_OLD_BYTES)
        for path in (city/'city.toml', city/'managed/rig-permissions.json', city/'managed/rig-permissions.toml'):
            os.chmod(path, 0o644)
        self.template = tmp/'template'
        self.make_template()
        m = types.SimpleNamespace(**{k: v for k, v in vars(candidate).items() if not k.startswith('__')})
        m.O = str(tmp/'ops')
        m.ROOT = str(tmp/'ops/reports/m5')
        m.CITY_SOURCE = str(tmp/'ops/reports/m5-inputs/city.toml')
        m.OLD_MANIFEST_SHA = sha(b'installed-r9\n')
        m.CLI_OLD, m.CLI_NEW = sha(old_cli), sha(self.new_cli)
        m.TEMPLATE = str(self.template)
        m.TEMPLATE_COMMIT = self.new_commit
        m.CHANGED_INPUTS = ((str(self.template/'lib/worker.py'), sha(b'old worker\n'), sha(b'new worker\n')),)
        m.RETAINED_TEMPLATE_PINS = {str(self.template/'lib/keep.py'): sha(b'keep\n')}
        m.AUTHORITY = str(tmp/'authority')
        m.AUTH_INPUTS = (('top.txt', sha(b'top\n'), 420), ('plans/p.md', sha(b'plan\n'), 420),
                         ('.git', sha(('gitdir: %s/.git/worktrees/authority\n' % self.template).encode()), 420))
        m.AUTH_TREES = ('bin', 'lib')
        m.AUTH_LINKS = (('plans/current', 'p.md'),)
        lines = RIG_OLD_BYTES.decode().splitlines(True)
        lines[94] = 'model = "opus-5-5"\n'
        self.rig_new = ''.join(lines).encode()
        m.RIGPERM_NEW = sha(self.rig_new)
        self.m = m
        for name, value in (('TEMPLATE', self.template), ('CITY', city), ('CLI', tmp/'bin/claude'),
                            ('CLI_BACKUP', tmp/'bin/claude.gct-m1wh-before-2.1.280'), ('STAGED', tmp/'staged'),
                            ('RIG', city/'managed/rig-permissions.toml'),
                            ('REGISTRY', city/'managed/rig-permissions.json'),
                            ('INSTALLED', city/'.gc/platform/install-manifest.json'),
                            ('SUSPENSION', city/'.gc/runtime/suspension-state.json'),
                            ('SUSPENSION_SHA', sha(b'suspended\n')), ('OLD_COMMIT', self.old_commit),
                            ('RENDERER_SHA', sha(b'renderer\n')), ('GIT_ENV', dict(GIT_ENV, HOME=str(tmp)))):
            setattr(p, name, value)
        original_owned = p.owned
        p.owned = lambda expected, mode: dict(original_owned(expected, mode), uid=os.getuid(), gid=os.getgid())
        self.ctx = self.context()

    def make_template(self):
        t = self.template
        (t/'lib').mkdir(parents=True); (t/'bin').mkdir(); (t/'plans').mkdir()
        git(t, 'init', '-q')
        (t/'lib/worker.py').write_bytes(b'old worker\n'); (t/'lib/keep.py').write_bytes(b'keep\n')
        (t/'bin/gct-managed-rig-permissions').write_bytes(b'renderer-old\n')
        (t/'top.txt').write_bytes(b'top\n'); (t/'plans/p.md').write_bytes(b'plan\n')
        os.symlink('p.md', t/'plans/current')
        git(t, 'add', '-A'); git(t, 'commit', '-q', '-m', 'old')
        self.old_commit = git(t, 'rev-parse', 'HEAD')
        (t/'lib/worker.py').write_bytes(b'new worker\n')
        (t/'bin/gct-managed-rig-permissions').write_bytes(b'renderer\n')
        git(t, 'add', '-A'); git(t, 'commit', '-q', '-m', 'new')
        self.new_commit = git(t, 'rev-parse', 'HEAD')
        git(t, 'checkout', '-q', '--detach', self.old_commit)
        (t/'deploy').mkdir(); (t/'deploy/x').write_bytes(b'user data\n')
        (t/'gas_city_template.egg-info').mkdir(); (t/'gas_city_template.egg-info/y').write_bytes(b'z\n')

    def context(self):
        p, m = self.p, self.m
        c = p.Context.__new__(p.Context)
        c.m, c.expected, c.inputs = m, 'f'*64, Path(m.O)/'reports/m5-inputs'
        c.quiet = lambda: dict(host='stable', scope='empty', suspension_sha256=p.SUSPENSION_SHA)
        c.slot = lambda: dict(active='failed', timer='active', next_us=0, now_us=0)
        return c

    def fake_render(self, predicted, check_rc=4, written=None, reported=None):
        p, rig = self.p, self.p.RIG
        calls = []
        original = p.run

        def run(argv, env, cwd='/'):
            if argv[:4] == ['/usr/bin/python3.12', '-I', '-B', str(p.TEMPLATE/'bin/gct-managed-rig-permissions')]:
                mode = argv[4]
                calls.append(mode)
                if mode == '--check':
                    report = dict(ok=False, state='drift', expected_sha256=predicted,
                                  actual_sha256=sha(rig.read_bytes()))
                    return dict(argv=argv, returncode=check_rc, stdout='' if check_rc != 4 else json.dumps(report),
                                stderr='boom' if check_rc != 4 else '')
                rig.write_bytes(self.rig_new if written is None else written)
                report = dict(ok=True, state='conformant', changed=True, expected_sha256=reported or predicted,
                              actual_sha256=sha(rig.read_bytes()))
                return dict(argv=argv, returncode=0, stdout=json.dumps(report), stderr='')
            return original(argv, env, cwd)
        p.run = run
        return calls

    def step(self, name):
        self.p.ACTIONS[name](self.ctx)


class PrereqTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.box = Sandbox(Path(self._tmp.name))
        self.p, self.m = self.box.p, self.box.m

    def tearDown(self):
        self._tmp.cleanup()

    def run_through(self, last):
        for name in self.p.STEPS[:self.p.STEPS.index(last) + 1]:
            if name == 'render':
                self.box.fake_render(self.m.RIGPERM_NEW)
            self.box.step(name)

    def inputs(self, name):
        return Path(self.m.O)/'reports/m5-inputs'/name

    def test_full_forward_sequence_and_records(self):
        self.run_through('authority')
        for name in self.p.STEPS:
            record = json.loads(self.inputs('prereq-' + name + '.json').read_text())
            self.assertEqual((record['step'], record['bead'], record['resumed']), (name, 'ga-0t04', False))
            self.assertTrue(self.inputs('prereq-' + name + '.intent.json').exists())
        self.assertEqual(sha(self.p.CLI.read_bytes()), self.m.CLI_NEW)
        self.assertEqual(sha((self.p.CITY/'city.toml').read_bytes()), self.m.CITY_NEW)
        self.assertEqual(sha(self.p.REGISTRY.read_bytes()), self.m.REGISTRY_NEW)
        self.assertEqual(sha(self.p.RIG.read_bytes()), self.m.RIGPERM_NEW)
        self.assertEqual(self.p.checkout_state()[0], self.m.TEMPLATE_COMMIT)
        self.assertEqual(self.p.checkout_state()[2], self.p.UNTRACKED)
        self.assertEqual(git(self.m.AUTHORITY, 'rev-parse', 'HEAD'), self.m.TEMPLATE_COMMIT)

    def test_every_intermediate_config_is_model_consistent(self):
        for name in self.p.STEPS:
            if name == 'render':
                self.box.fake_render(self.m.RIGPERM_NEW)
            self.box.step(name)
            self.p.model_consistency()

    def test_models_refuse_unordered_and_ignore_other_families(self):
        _, transition, final = self.box.ctx.city_bytes()
        agents = self.p.fragment_texts()
        old_rig, new_rig = RIG_OLD_BYTES.decode(), self.box.rig_new.decode()
        self.p.models(transition.decode(), old_rig, agents)
        self.p.models(transition.decode(), new_rig, agents)
        selected = self.p.models(final.decode(), new_rig, agents)['selected']
        self.assertFalse(any(v.startswith('gpt-') for v in selected.values()))
        self.assertTrue(any(k.endswith('sweeper/agent.toml') for k in selected))
        with self.assertRaisesRegex(RuntimeError, 'selects a model it does not offer'):
            self.p.models(final.decode(), old_rig, agents)
        agents = dict(agents)
        agents['/x/agents/probe/agent.toml'] = 'provider = "claude"\noption_defaults = { model = "opus-5" }\n'
        with self.assertRaisesRegex(RuntimeError, 'agents/probe/agent.toml'):
            self.p.models(final.decode(), new_rig, agents)

    def test_quiet_slot_waits_for_natural_drain(self):
        now = [1_000_000_000_000]
        states = iter([dict(active='activating', started_us=1, timer='active', next_us=0),
                       dict(active='failed', started_us=1, timer='active', next_us=1_000_510_000),
                       dict(active='failed', started_us=1, timer='active', next_us=1_100_000_000)])
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds); now[0] += int(seconds * 1e9)
        slot = self.p.quiet_slot(clock=lambda: now[0], sleep=sleep, observe=lambda: next(states))
        self.assertEqual(len(sleeps), 2)
        self.assertGreaterEqual(slot['next_us'] - slot['now_us'], self.p.SLOT_US)
        slot = self.p.quiet_slot(clock=lambda: now[0], sleep=sleep,
                                 observe=lambda: dict(active='inactive', started_us=0, timer='inactive', next_us=0))
        self.assertEqual(slot['timer'], 'inactive')
        with self.assertRaisesRegex(RuntimeError, 'no natural reconciler quiet slot'):
            self.p.quiet_slot(clock=lambda: now[0], sleep=sleep,
                              observe=lambda: dict(active='activating', started_us=1, timer='active', next_us=0))

    def test_step_order_and_no_repeat(self):
        with self.assertRaisesRegex(RuntimeError, 'earlier step missing: inputs'):
            self.box.step('cli')
        self.box.step('inputs')
        with self.assertRaisesRegex(RuntimeError, 'step already consumed: inputs'):
            self.box.step('inputs')

    def test_inputs_validates_before_consuming_directory(self):
        (Path(self.m.O)/'reports/r5/i/00').write_bytes(b'wrong\n')
        with self.assertRaisesRegex(RuntimeError, 'city backup bytes'):
            self.box.step('inputs')
        self.assertFalse(self.inputs('').exists())
        self.p.REGISTRY.write_bytes(b'{}\n')
        with self.assertRaisesRegex(RuntimeError, 'live predecessor bytes'):
            self.box.step('inputs')

    def test_cli_refusals_before_mutation(self):
        self.box.step('inputs')
        self.p.STAGED.write_bytes(b'#!/bin/sh\necho other\n')
        with self.assertRaisesRegex(RuntimeError, 'staged CLI bytes'):
            self.box.step('cli')
        self.p.STAGED.write_bytes(self.box.new_cli)
        self.p.CLI.write_bytes(b'#!/bin/sh\necho other\n')
        with self.assertRaisesRegex(RuntimeError, 'live CLI predecessor identity'):
            self.box.step('cli')
        self.assertFalse(self.p.CLI_BACKUP.exists())
        self.assertFalse(self.inputs('prereq-cli.intent.json').exists())

    def test_finish_refusal_is_resumed_without_repeating_the_mutation(self):
        self.box.step('inputs')
        calls = []
        stable = dict(host='stable', scope='empty', suspension_sha256=self.p.SUSPENSION_SHA)

        def flaky():
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('owned scope residue')
            return stable
        self.box.ctx.quiet = flaky
        with self.assertRaisesRegex(RuntimeError, 'owned scope residue'):
            self.box.step('cli')
        self.assertEqual(sha(self.p.CLI.read_bytes()), self.m.CLI_NEW)
        self.assertFalse(self.inputs('prereq-cli.json').exists())
        with self.assertRaisesRegex(RuntimeError, 'use resume cli'):
            self.box.step('cli')
        self.p.resume(self.box.ctx, 'cli')
        record = json.loads(self.inputs('prereq-cli.json').read_text())
        self.assertTrue(record['resumed'])
        self.box.step('city-transition')

    def test_resume_refuses_without_the_exact_postcondition(self):
        self.box.step('inputs')
        with self.assertRaisesRegex(RuntimeError, 'no interrupted intent'):
            self.p.resume(self.box.ctx, 'cli')
        self.box.ctx.intent('cli', dict(host='stable'))
        with self.assertRaisesRegex(RuntimeError, 'installed CLI identity'):
            self.p.resume(self.box.ctx, 'cli')
        self.assertFalse(self.inputs('prereq-cli.json').exists())

    def test_checkout_proves_target_blobs_before_moving(self):
        self.run_through('city-transition')
        self.p.RENDERER_SHA = sha(b'not the reviewed renderer\n')
        with self.assertRaisesRegex(RuntimeError, 'target renderer blob'):
            self.box.step('checkout')
        self.assertEqual(self.p.checkout_state()[0], self.p.OLD_COMMIT)
        self.assertFalse(self.inputs('prereq-checkout.intent.json').exists())

    def test_render_check_refusals_write_nothing(self):
        self.run_through('registry')
        calls = self.box.fake_render(sha(b'unreviewed render'))
        with self.assertRaisesRegex(RuntimeError, 'render check does not predict the reviewed bytes'):
            self.box.step('render')
        self.assertEqual(calls, ['--check'])
        calls = self.box.fake_render(self.m.RIGPERM_NEW, check_rc=3)
        with self.assertRaisesRegex(RuntimeError, 'render check exit status'):
            self.box.step('render')
        self.assertEqual(calls, ['--check'])
        self.assertEqual(sha(self.p.RIG.read_bytes()), self.m.RIGPERM_OLD)
        self.assertFalse(self.inputs('prereq-render.intent.json').exists())

    def test_render_apply_mismatch_is_recoverable_by_rollback(self):
        self.run_through('registry')
        self.box.fake_render(self.m.RIGPERM_NEW, written=b'unexpected render\n')
        with self.assertRaisesRegex(RuntimeError, 'render report'):
            self.box.step('render')
        self.assertTrue(self.inputs('prereq-render.intent.json').exists())
        with self.assertRaisesRegex(RuntimeError, 'rendered rig permissions identity'):
            self.p.resume(self.box.ctx, 'render')
        self.box.step('rollback')
        self.assertEqual(sha(self.p.RIG.read_bytes()), self.m.RIGPERM_OLD)

    def test_city_steps_require_the_matching_fragment(self):
        self.run_through('render')
        self.p.RIG.write_bytes(RIG_OLD_BYTES)
        with self.assertRaisesRegex(RuntimeError, 'city step fragment/registry predecessor'):
            self.box.step('city-final')
        self.assertFalse(self.inputs('prereq-city-final.intent.json').exists())

    def test_authority_mismatch_refuses_record(self):
        self.run_through('city-final')
        self.m.AUTH_INPUTS = (('top.txt', sha(b'other\n'), 420),) + self.m.AUTH_INPUTS[1:]
        with self.assertRaisesRegex(RuntimeError, 'authority file: top.txt'):
            self.box.step('authority')
        self.assertFalse(self.inputs('prereq-authority.json').exists())

    def test_executor_window_gates_rollback(self):
        self.box.step('inputs')
        q = Path(self.m.ROOT)/'q'
        q.mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, 'M5 package root already exists'):
            self.box.step('cli')
        with self.assertRaisesRegex(RuntimeError, 'executor window is open'):
            self.box.step('rollback')
        (q/'restored.json').write_text('{}')
        (q/'commit-consumed.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'executor window is open'):
            self.box.step('rollback')
        (q/'commit-consumed.json').unlink()
        self.box.step('rollback')
        self.p.INSTALLED.write_bytes(b'successor\n')
        with self.assertRaisesRegex(RuntimeError, 'not the R9 predecessor'):
            self.box.step('cli')

    def test_rollback_from_every_partial_state_through_consistent_configs(self):
        for last in self.p.STEPS[1:]:
            with self.subTest(last=last):
                self.tearDown(); self.setUp()
                self.run_through(last)
                self.box.step('rollback')
                record = json.loads(self.inputs('rollback.json').read_text())
                self.assertFalse([x for x in record['models_after_each'] if 'refused' in x], record)
                self.assertEqual(sha((self.p.CITY/'city.toml').read_bytes()), self.m.CITY_OLD)
                self.assertEqual(sha(self.p.RIG.read_bytes()), self.m.RIGPERM_OLD)
                self.assertEqual(sha(self.p.REGISTRY.read_bytes()), self.m.REGISTRY_OLD)
                self.assertEqual(sha(self.p.CLI.read_bytes()), self.m.CLI_OLD)
                head, _, status = self.p.checkout_state()
                self.assertEqual((head, status), (self.p.OLD_COMMIT, self.p.UNTRACKED))
                with self.assertRaisesRegex(RuntimeError, 'rollback consumed'):
                    self.box.step(self.p.STEPS[min(self.p.STEPS.index(last) + 1, len(self.p.STEPS) - 1)])

    def test_rollback_refuses_corrupt_backup(self):
        self.run_through('cli')
        self.p.CLI_BACKUP.write_bytes(b'corrupt\n')
        with self.assertRaisesRegex(RuntimeError, 'backup bytes differ'):
            self.box.step('rollback')
        self.assertEqual(sha(self.p.CLI.read_bytes()), self.m.CLI_NEW)

    def test_leftover_temporary_file_refuses_and_is_reported(self):
        self.box.step('inputs')
        (self.p.CLI.parent/'.claude.gct-m1wh-m5.forward.tmp').write_bytes(b'left over\n')
        with self.assertRaisesRegex(RuntimeError, 'leftover temporary file'):
            self.box.step('cli')
        self.assertIn(str(self.p.CLI.parent/'.claude.gct-m1wh-m5.forward.tmp'), self.p.leftovers())

    def test_host_change_refuses_record(self):
        self.box.step('inputs')
        states = iter(['before', 'after'])
        self.box.ctx.quiet = lambda: dict(host=next(states), scope='empty', suspension_sha256='x')
        with self.assertRaisesRegex(RuntimeError, 'host identity changed'):
            self.box.step('cli')
        self.assertFalse(self.inputs('prereq-cli.json').exists())

    def test_candidate_digest_is_bound(self):
        with self.assertRaisesRegex(RuntimeError, 'candidate source differs'):
            self.p.load_candidate('0'*64)


if __name__ == '__main__':
    unittest.main()
