"""Tests for round 2b (the window stack and its wrappers). Run: python3 -B -m unittest test_round2b.

Read-only apart from temporary directories. Regenerates every round-2b output and wrapper from the
reviewed ga-y49e sources and the committed round-2a outputs, and requires byte equality. Loads the
window layer offline (no live command runs) and exercises its provenance binding of the fresh integrity
observation against fabricated observer roots. One live read: `gc bd show ga-4z38` with
GIT_OPTIONAL_LOCKS=0, to prove the task still meets the binding preconditions.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENERATED = ('window-r11.py', 'bind-task-r3.py', 'route-task-r5.py', 'audit-queue-r3.py', 'observe-terminal-r11.py',
             'reconcile-predecessor-r3.py', 'restore-admission-r3.py', 'restore-r9-routes-r3.py', 'route-chain-r1.py')
WRAPPERS = ('RECONCILE.sh', 'FRESHEN.sh', 'HOLD.sh', 'ADMIT.sh', 'OBSERVE.sh', 'BIND.sh', 'PREFLIGHT.sh', 'STAGE.sh', 'ROUTE.sh', 'RESUME.sh', 'WATCH.sh', 'CONTAIN.sh',
            'RESTORE.sh', 'TERMINAL.sh')
LAUNCH = 'gct-m1wh-p6/source-launch.py'
GC_ENV = dict(HOME='/home/loucmane', GC_HOME='/home/loucmane/gascity/home', GIT_OPTIONAL_LOCKS='0',
              PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def constant(text, name):
    [value] = re.findall(r"^%s ?= ?'([0-9a-f]{64})'$" % name, text, re.M)
    return value


def layer():
    m = types.ModuleType('test_window_r11')
    m.__file__ = str(HERE/'window-r11.py')
    exec(compile((HERE/'window-r11.py').read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
    return m


class Regeneration(unittest.TestCase):
    def test_generators_reproduce_every_round_2b_output_and_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp)/'pkg'
            shutil.copytree(HERE, scratch, ignore=shutil.ignore_patterns(*GENERATED, '__pycache__'))
            shutil.rmtree(scratch/'operator')
            for script in ('make_round2b.py', 'make_operators.py'):
                done = subprocess.run([sys.executable, '-B', str(HERE/'generators'/script), str(HERE)],
                                      capture_output=True, text=True, env=dict(os.environ, GA4Z38_OUT=str(scratch)))
                self.assertEqual(done.returncode, 0, done.stderr)
            for name in GENERATED:
                self.assertEqual(sha(scratch/name), sha(HERE/name), name)
            for name in WRAPPERS:
                self.assertEqual(sha(scratch/'operator'/name), sha(HERE/'operator'/name), name)


class Pins(unittest.TestCase):
    def text(self, name):
        return (HERE/name).read_text()

    def test_copies_are_the_reviewed_route_modules(self):
        self.assertEqual(sha(HERE/'restore-r9-routes-r3.py'), '8d041af74297b44c0bedecdbcaa776ac92f433eba801afa0ee0a89a71eecc7c2')
        self.assertEqual(sha(HERE/'route-chain-r1.py'), 'e408e2ddf98d6cb403a45b26f72aba0e47817a3b8dd2adb19adade696a35eacf')

    def test_every_load_is_bound_to_the_file_it_loads(self):
        window = self.text('window-r11.py')
        self.assertEqual(constant(window, 'BASE_SHA'), sha(HERE/'window-base-r11.py'))
        self.assertEqual(constant(window, 'OBSERVER_SHA'), sha(HERE/'observe-integrity-r11.py'))
        bind = self.text('bind-task-r3.py')
        self.assertEqual(constant(bind, 'HELPER_SHA'), sha(HERE/'window-base-r11.py'))
        self.assertEqual(constant(bind, 'BRIEF_SHA'), sha(HERE/'worker-brief.md'))
        route = self.text('route-task-r5.py')
        self.assertEqual(constant(route, 'SHA'), sha(HERE/'window-r11.py'))
        self.assertEqual(constant(route, 'BIND_SHA'), sha(HERE/'bind-task-r3.py'))
        self.assertEqual(constant(route, 'BRIEF_SHA'), sha(HERE/'worker-brief.md'))
        terminal = self.text('observe-terminal-r11.py')
        self.assertEqual(constant(terminal, 'W_SHA'), sha(HERE/'window-obs-r11.py'))
        self.assertEqual(constant(terminal, 'WINDOW_SHA'), sha(HERE/'window-r11.py'))
        self.assertEqual(constant(terminal, 'MANIFEST_SHA'),
                         sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json'))
        for name in ('watch-r11.py', 'freshen-r11.py', 'hold-r11.py'):
            self.assertEqual(re.findall(r"^BASE_SHA = '([0-9a-f]{64})'$", self.text(name), re.M),
                             [sha(HERE/'window-base-r11.py')], name)
        admission = self.text('restore-admission-r3.py')
        self.assertEqual(re.findall(r"^SHA = '([0-9a-f]{64})'$", admission, re.M), [sha(HERE/'window-r11.py')])
        audit = self.text('audit-queue-r3.py')
        self.assertIn(sha(HERE/'..'/'gct-m1wh-p6'/'p6-observe-compose.py'), audit)

    def test_wrappers_run_only_pinned_package_files_through_the_p6_launcher(self):
        for name in WRAPPERS:
            text = (HERE/'operator'/name).read_text()
            pins = dict(re.findall(r'^([A-Z]+_SHA)=([0-9a-f]{64})$', text, re.M))
            steps = re.findall(r'^\s*step \S+ "\$C/([^"]+)" "\$([A-Z]+_SHA)"', text, re.M)
            self.assertTrue(steps, name)
            for target, pin in steps:
                self.assertEqual(pins[pin], sha(HERE/target), (name, target))
            self.assertIn('"$D/%s"' % LAUNCH, text)
            self.assertIn('[ "$(umask)" = 0022 ]', text)
            self.assertIn('--no-optional-locks status --porcelain --untracked-files=all', text)
            self.assertTrue(text.rstrip().endswith('exit 0'), name)


class Layer(unittest.TestCase):
    def test_layer_installs_its_hooks_on_the_base_and_binds_the_window_root(self):
        m = layer()
        w = m.w
        self.assertEqual(str(w.ROOT), '/var/tmp/ga-4z38-window-20260923-r1')
        for hook in ('reload', 'snapshot', 'preservation', 'transition', 'save'):
            self.assertIs(getattr(w, hook), getattr(m, hook), hook)
        self.assertEqual(str(m.INTEGRITY), '/var/tmp/ga-4z38-integrity-20260923-r1')

    def test_integrity_binding_is_recorded_once_and_then_required_exactly(self):
        m = layer()
        with tempfile.TemporaryDirectory() as tmp:
            integrity = Path(tmp)/'integrity'
            integrity.mkdir(mode=0o700)
            root = Path(tmp)/'window'
            root.mkdir(mode=0o700)

            def put(name, value):
                (integrity/name).write_text(json.dumps(value))
            put('intent.json', dict(executor_sha256=m.OBSERVER_SHA, binary_sha256=m.INSPECTOR_SHA,
                                    version_probes_only=True, worker_launch=False))
            put('result.json', dict(ok=True, actual_host_verified=True, admitted_against_p6_with_disposition=True,
                                    report=dict(ok=True, report={'Drifts': None},
                                                schema='ga.platform-inspect-observation.v1'),
                                    root_cache_protected_read_only=True, window_preservation=True,
                                    worker_launched=False))
            put('preservation.json', dict(window_preservation=True, cache_atime_deltas=0,
                                          runtime_child_metadata_policy='unchanged pinned R6', timestamp_writes=False))
            put('observed-after.json', dict(image=1))
            m.INTEGRITY = integrity
            m.w.ROOT = root
            # Before admission recorded a binding, a later snapshot fails closed (the record is absent).
            with self.assertRaises((RuntimeError, OSError)):
                m.integrity_baseline(False)
            self.assertEqual(m.integrity_baseline(True), dict(image=1))
            binding = json.loads((root/'integrity-binding.json').read_text())
            self.assertEqual(binding['observer_sha256'], m.OBSERVER_SHA)
            self.assertEqual(m.integrity_baseline(False), dict(image=1))
            with self.assertRaises(RuntimeError):
                m.integrity_baseline(True)
            put('observed-after.json', dict(image=2))
            with self.assertRaises(RuntimeError):
                m.integrity_baseline(False)
            put('observed-after.json', dict(image=1))
            put('intent.json', dict(executor_sha256='0' * 64, binary_sha256=m.INSPECTOR_SHA,
                                    version_probes_only=True, worker_launch=False))
            with self.assertRaises(RuntimeError):
                m.integrity_baseline(False)

    def test_audit_rig_rule_per_mode(self):
        rule = lambda mode, rigs: all(r['suspended'] == (mode == 'route' or r['name'] != 'gascity') for r in rigs)
        names = ('gas-city-template', 'gascity', 'blog', 'hpfetcher')
        suspended = [dict(name=n, suspended=True) for n in names]
        resumed = [dict(name=n, suspended=n != 'gascity') for n in names]
        self.assertTrue(rule('route', suspended) and not rule('route', resumed))
        self.assertTrue(rule('resume', resumed) and not rule('resume', suspended))
        self.assertIn("r['suspended'] == (MODE == 'route' or r['name'] != 'gascity')", (HERE/'audit-queue-r3.py').read_text())


class Safety(unittest.TestCase):
    def load(self, name):
        m = types.ModuleType(name.replace('-', '_')[:-3])
        m.__file__ = str(HERE/name)
        exec(compile((HERE/name).read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
        return m

    def test_freshen_touch_changes_nothing_but_atime(self):
        f = self.load('freshen-r11.py')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'d'
            directory.mkdir()
            regular = directory/'f'
            regular.write_bytes(b'content')
            for path, action in ((regular, 'read'), (directory, 'listed')):
                before = f.image(str(path))
                self.assertEqual(f.touch(str(path)), action)
                after = f.image(str(path))
                before.pop('atime_ns')
                after.pop('atime_ns')
                self.assertEqual(before, after)
            self.assertEqual(regular.read_bytes(), b'content')
        self.assertEqual(f.YOUNG_HOURS, 19)

    def test_hold_acts_only_on_a_stranded_window_and_never_blocks_its_suspends(self):
        text = (HERE/'hold-r11.py').read_text()
        self.assertIn("w.require(stranded, 'hold is only for a stranded lifecycle; use CONTAIN.sh')", text)
        self.assertIn("intent.name.replace('-intent.json', '-event.json')", text)
        self.assertIn("started.name.replace('-started.json', '-phase.json')", text)
        self.assertIn("w.phase(name, argv, b, owned, expected=ANY)", text)
        self.assertIn("w.require(final == (True, True), 'hold did not suspend the city and rig')", text)

    def test_freshen_object_set_covers_every_exact_atime_object(self):
        f = self.load('freshen-r11.py')
        w = f.load()
        b, o, owned = w.load_support()
        paths = f.objects(w, b)
        accepted = json.loads((Path('/var/tmp/gct-m1wh-p6-adoption-20260923-r2')/'after.json').read_text())
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(set(accepted['pins']) <= set(paths))
        for root, tree in accepted['protected'].items():
            self.assertIn(root, paths)
        self.assertIn('/home/loucmane/.local/share/fnm/node-versions/v22.16.0/installation/bin/claude', paths)
        for path in ('/home/loucmane/gascity/city', '/home/loucmane/gascity/city/.gc/runtime/provisioning',
                     '/home/loucmane/gascity/city/.gc/runtime/provisioning/bin/gct-managed-worker-canary'):
            self.assertIn(path, paths)
        cache = str(b.CACHE)
        self.assertFalse([p for p in paths if p == cache or p.startswith(cache + '/')])
        self.assertFalse([p for p in paths if '/dev/blog' in p or '/dev/hpfetcher' in p])

    def test_worker_environment_inherits_git_optional_locks(self):
        done = subprocess.run([sys.executable, '-B', str(HERE/'proof'/'worker-env-proof.py')],
                              capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        self.assertEqual(done.returncode, 0, done.stdout[-2000:] + done.stderr[-2000:])
        self.assertTrue(json.loads(done.stdout)['ok'])

    def test_watch_uses_index_free_plumbing(self):
        text = (HERE/'watch-r11.py').read_text()
        self.assertIn("['diff-files', '--patch', '--exit-code']", text)
        self.assertIn("['diff-index', '--cached', '--patch', '--exit-code', 'HEAD']", text)
        self.assertNotIn("git + ['diff',", text)
        self.assertIn("'--porcelain=v1', '-z'", text)

    def test_preflight_requires_a_recent_freshen_pass(self):
        text = (HERE/'operator'/'PREFLIGHT.sh').read_text()
        self.assertIn('-path "/var/tmp/ga-4z38-freshen-*/result.json" -mmin -45', text)

    def test_restore_requires_the_admission_pass(self):
        text = (HERE/'operator'/'RESTORE.sh').read_text()
        self.assertIn('[ -e /var/tmp/ga-4z38-window-20260923-r1/restore-admission-pass.json ]', text)
        self.assertIn("assert not (w.ROOT / 'restore-consumed.json').exists()", (HERE/'restore-admission-r3.py').read_text())

    def test_contain_runs_each_suspend_only_once_and_only_after_its_resume(self):
        text = (HERE/'operator'/'CONTAIN.sh').read_text()
        for action, resume in (('city-suspend', 'city-resume'), ('rig-suspend', 'rig-resume')):
            self.assertIn('[ -e /var/tmp/ga-4z38-window-20260923-r1/suspension-%s-event.json ] && '
                          '[ ! -e /var/tmp/ga-4z38-window-20260923-r1/suspension-%s-event.json ]' % (resume, action), text)

    def test_resume_requires_route_and_route_audit(self):
        text = (HERE/'operator'/'RESUME.sh').read_text()
        self.assertIn('/var/tmp/ga-4z38-route-20260923-r1/result.json', text)
        self.assertIn('/var/tmp/ga-4z38-audit-route-20260923-r1/result.json', text)

    def test_watch_uses_the_active_epoch_not_the_quiescent_host(self):
        text = (HERE/'watch-r11.py').read_text()
        self.assertIn('w.active_epoch(o)', text)
        self.assertNotIn('w.host(o)', text)


class Task(unittest.TestCase):
    def test_bind_request_and_metadata_name_ga_4z38(self):
        text = (HERE/'bind-task-r3.py').read_text()
        self.assertIn('"bead_id":"ga-4z38"', text)
        self.assertIn("'.gc/worker-evidence/ga-4z38/implementation-summary.md'", text)
        self.assertIn("WORK='/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles'", text)

    def test_task_still_meets_the_binding_preconditions(self):
        done = subprocess.run(['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city', '--rig', 'gascity',
                               'bd', 'show', 'ga-4z38', '--json'], env=GC_ENV, capture_output=True, text=True,
                              timeout=60, stdin=subprocess.DEVNULL, check=True)
        [bead] = json.loads(done.stdout)
        self.assertEqual(bead['status'], 'open')
        self.assertFalse(bead.get('assignee'))
        self.assertFalse(bead.get('metadata'))
        self.assertFalse(bead.get('dependencies'))

    def test_brief_names_the_exact_identity_and_absent_negative_targets(self):
        brief = (HERE/'worker-brief.md').read_text()
        for line in ('- Worktree /home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles.',
                     '- Branch codex/ga-4z38-typed-route-cycles.',
                     '- Initial HEAD e6366b9ececd3a4ceab2bcaa264a5e317e6eab88.',
                     "`go test ./internal/sling -run '^TestGa4z38CapabilityProbeNoTests$'`",
                     '--worktree /home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles --bead ga-4z38'):
            self.assertIn(line, brief)
        for target in ('/home/loucmane/gascity/.ga-4z38-denied-native-write',
                       '/home/loucmane/gascity/.ga-4z38-denied-shell-write'):
            self.assertIn(target, brief)
            self.assertFalse(os.path.lexists(target))


if __name__ == '__main__':
    unittest.main()
