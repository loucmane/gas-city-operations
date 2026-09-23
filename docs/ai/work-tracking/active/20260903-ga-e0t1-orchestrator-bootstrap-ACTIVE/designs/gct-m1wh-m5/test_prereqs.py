"""Behavioural tests for prereqs.py against a sandboxed fake city and a real temporary Git repository.

The live paths are redirected into a temporary directory. The city files are real
predecessor bytes (the r5/i/00 city backup, and the live or preserved registry and
rig fragment). The CLI binaries are small scripts. The Template is a two-commit
repository with the untracked set the live checkout carries. Quiet-host
observation is stubbed; its live form runs only in the supervisor namespaces.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
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


def preserved(live, backup, digest):
    raw = Path(live).read_bytes()
    if sha(raw) != digest:
        raw = Path(backup).read_bytes()
    assert sha(raw) == digest
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
        (city/'city.toml').write_bytes(CITY_OLD_BYTES)
        (city/'managed/rig-permissions.json').write_bytes(REGISTRY_OLD_BYTES)
        (city/'managed/rig-permissions.toml').write_bytes(RIG_OLD_BYTES)
        (city/'.gc/platform/install-manifest.json').write_bytes(b'installed-r9\n')
        (city/'.gc/runtime/suspension-state.json').write_bytes(b'suspended\n')
        (tmp/'bin').mkdir()
        old_cli = b'#!/bin/sh\necho "2.1.263 (Claude Code)"\n'
        new_cli = b'#!/bin/sh\necho "2.1.280 (Claude Code)"\n'
        (tmp/'bin/claude').write_bytes(old_cli); os.chmod(tmp/'bin/claude', 0o755)
        (tmp/'staged').write_bytes(new_cli)
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
        m.CLI_OLD, m.CLI_NEW = sha(old_cli), sha(new_cli)
        m.TEMPLATE = str(self.template)
        m.TEMPLATE_COMMIT = self.new_commit
        m.CHANGED_INPUTS = ((str(self.template/'lib/worker.py'), sha(b'old worker\n'), sha(b'new worker\n')),)
        m.RETAINED_TEMPLATE_PINS = {str(self.template/'lib/keep.py'): sha(b'keep\n')}
        m.AUTHORITY = str(tmp/'authority')
        m.AUTH_INPUTS = (('top.txt', sha(b'top\n'), 420), ('plans/p.md', sha(b'plan\n'), 420),
                         ('.git', sha(('gitdir: %s/.git/worktrees/authority\n' % self.template).encode()), 420))
        m.AUTH_TREES = ('bin', 'lib')
        m.AUTH_LINKS = (('plans/current', 'p.md'),)
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
        uid = os.getuid()
        original_owned = p.owned
        p.owned = lambda digest, mode: dict(original_owned(digest, mode), uid=uid, gid=os.getgid())
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
        return c

    def fake_render(self, predicted):
        p, rig = self.p, self.p.RIG
        calls = []

        def run(argv, env, cwd='/'):
            if argv[:4] == ['/usr/bin/python3.12', '-I', '-B', str(p.TEMPLATE/'bin/gct-managed-rig-permissions')]:
                mode = argv[4]
                calls.append(mode)
                if mode == '--check':
                    report = dict(ok=False, state='drift', expected_sha256=predicted,
                                  actual_sha256=sha(rig.read_bytes()))
                    return dict(argv=argv, returncode=4, stdout=json.dumps(report), stderr='')
                rig.write_bytes(self.rig_new)
                report = dict(ok=True, state='conformant', changed=True, expected_sha256=predicted,
                              actual_sha256=sha(rig.read_bytes()))
                return dict(argv=argv, returncode=0, stdout=json.dumps(report), stderr='')
            return original(argv, env, cwd)
        original = p.run
        p.run = run
        return calls

    def step(self, name):
        self.p.ACTIONS[name](self.ctx)


class PrereqTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.box = Sandbox(Path(self._tmp.name))
        self.p, self.m = self.box.p, self.box.m
        lines = RIG_OLD_BYTES.decode().splitlines(True)
        lines[94] = 'model = "opus-5-5"\n'
        self.box.rig_new = ''.join(lines).encode()
        self.m.RIGPERM_NEW = sha(self.box.rig_new)

    def tearDown(self):
        self._tmp.cleanup()

    def run_through(self, last):
        for name in self.p.STEPS[:self.p.STEPS.index(last) + 1]:
            if name == 'render':
                self.box.fake_render(self.m.RIGPERM_NEW)
            self.box.step(name)

    def test_full_forward_sequence_and_records(self):
        self.run_through('authority')
        inputs = Path(self.m.O)/'reports/m5-inputs'
        for name in self.p.STEPS:
            record = json.loads((inputs/('prereq-' + name + '.json')).read_text())
            self.assertEqual((record['step'], record['bead']), (name, 'ga-0t04'))
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
        self.assertFalse((Path(self.m.O)/'reports/m5-inputs').exists())

    def test_cli_refuses_unexpected_live_binary_without_mutation(self):
        self.box.step('inputs')
        self.p.CLI.write_bytes(b'#!/bin/sh\necho other\n')
        with self.assertRaisesRegex(RuntimeError, 'live CLI predecessor identity'):
            self.box.step('cli')
        self.assertFalse(self.p.CLI_BACKUP.exists())

    def test_render_check_mismatch_writes_nothing(self):
        self.run_through('registry')
        calls = self.box.fake_render(sha(b'unreviewed render'))
        with self.assertRaisesRegex(RuntimeError, 'render check does not predict the reviewed bytes'):
            self.box.step('render')
        self.assertEqual(calls, ['--check'])
        self.assertEqual(sha(self.p.RIG.read_bytes()), self.m.RIGPERM_OLD)

    def test_refuses_when_package_root_exists_or_installed_changed(self):
        self.box.step('inputs')
        os.mkdir(self.m.ROOT)
        with self.assertRaisesRegex(RuntimeError, 'M5 package root already exists'):
            self.box.step('cli')
        with self.assertRaisesRegex(RuntimeError, 'M5 package root exists'):
            self.box.step('rollback')
        os.rmdir(self.m.ROOT)
        self.p.INSTALLED.write_bytes(b'successor\n')
        with self.assertRaisesRegex(RuntimeError, 'not the R9 predecessor'):
            self.box.step('cli')
        with self.assertRaisesRegex(RuntimeError, 'rollback refused'):
            self.box.step('rollback')

    def test_rollback_from_every_partial_state(self):
        for last in self.p.STEPS[1:]:
            with self.subTest(last=last):
                self.tearDown(); self.setUp()
                self.run_through(last)
                self.box.step('rollback')
                self.assertEqual(sha((self.p.CITY/'city.toml').read_bytes()), self.m.CITY_OLD)
                self.assertEqual(sha(self.p.RIG.read_bytes()), self.m.RIGPERM_OLD)
                self.assertEqual(sha(self.p.REGISTRY.read_bytes()), self.m.REGISTRY_OLD)
                self.assertEqual(sha(self.p.CLI.read_bytes()), self.m.CLI_OLD)
                head, _, status = self.p.checkout_state()
                self.assertEqual((head, status), (self.p.OLD_COMMIT, self.p.UNTRACKED))
                with self.assertRaisesRegex(RuntimeError, 'rollback consumed'):
                    self.box.step(self.p.STEPS[self.p.STEPS.index(last) + 1]
                                  if last != 'authority' else 'authority')

    def test_rollback_restores_an_unreviewed_render(self):
        self.run_through('registry')
        self.p.RIG.write_bytes(b'unreviewed render output\n')
        self.box.step('rollback')
        self.assertEqual(sha(self.p.RIG.read_bytes()), self.m.RIGPERM_OLD)

    def test_rollback_refuses_corrupt_backup(self):
        self.run_through('cli')
        self.p.CLI_BACKUP.write_bytes(b'corrupt\n')
        with self.assertRaisesRegex(RuntimeError, 'backup bytes differ'):
            self.box.step('rollback')

    def test_leftover_temporary_file_refuses(self):
        self.box.step('inputs')
        (self.p.CLI.parent/'.claude.gct-m1wh-m5.forward.tmp').write_bytes(b'left over\n')
        with self.assertRaisesRegex(RuntimeError, 'leftover temporary file'):
            self.box.step('cli')

    def test_host_change_refuses_record(self):
        self.box.step('inputs')
        states = iter(['before', 'after'])
        self.box.ctx.quiet = lambda: dict(host=next(states), scope='empty', suspension_sha256='x')
        with self.assertRaisesRegex(RuntimeError, 'host identity changed'):
            self.box.step('cli')
        self.assertFalse((Path(self.m.O)/'reports/m5-inputs/prereq-cli.json').exists())

    def test_candidate_digest_is_bound(self):
        with self.assertRaisesRegex(RuntimeError, 'candidate source differs'):
            self.p.load_candidate('0'*64)


if __name__ == '__main__':
    unittest.main()
