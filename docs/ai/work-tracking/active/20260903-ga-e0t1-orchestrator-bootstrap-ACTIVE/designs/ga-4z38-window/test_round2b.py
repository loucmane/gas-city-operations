"""Tests for round 2b (the window stack and its wrappers). Run: python3 -B -m unittest test_round2b.

Read-only apart from temporary directories. Regenerates every round-2b output and wrapper from the
reviewed ga-y49e sources and the committed round-2a outputs, and requires byte equality. Loads the
window layer offline (no live command runs) and exercises its provenance binding of the fresh integrity
observation against fabricated observer roots. One live read: `gc bd show ga-4z38` with
GIT_OPTIONAL_LOCKS=0, to prove the task still meets the binding preconditions.
"""
import contextlib
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENERATED = ('window-r11.py', 'bind-task-r3.py', 'route-task-r5.py', 'audit-queue-r3.py', 'observe-terminal-r11.py',
             'reconcile-predecessor-r3.py', 'restore-admission-r3.py', 'restore-r9-routes-r3.py', 'route-chain-r1.py')
# Every generated wrapper, numbered slots included (PREP.sh belongs to round 1).
WRAPPERS = tuple(sorted(p.name for p in (HERE/'operator').glob('*.sh') if p.name != 'PREP.sh'))
LAUNCH = 'gct-m1wh-p6/source-launch.py'
GC_ENV = dict(HOME='/home/loucmane', GC_HOME='/home/loucmane/gascity/home', GIT_OPTIONAL_LOCKS='0',
              PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def constant(text, name):
    [value] = re.findall(r"^%s ?= ?'([0-9a-f]{64})'$" % name, text, re.M)
    return value


class FakeOwned:
    """The owned-phase runner, faked: it answers each argv from a responder and writes the phase record the
    real base phase() and complete_containment() read. Everything else is the real window-base-r11.py."""

    def __init__(self, respond):
        self.respond = respond
        self.calls = []

    def _run_owned_phase(self, name, argv, cwd, environment, timeout, evidence_path):
        self.calls.append((name, list(argv)))
        exit_code, stdout, stderr = self.respond(list(argv))
        result = dict(phase=name, argv=argv, cwd=str(cwd), exit_code=exit_code, stdout=stdout, stderr=stderr,
                      timed_out=False, primary_error=None,
                      cleanup=dict(direct_child_reaped=True, owned_process_group_gone=True, failures=[],
                                   unexpected_survivors=[]))
        Path(evidence_path).write_text(json.dumps(result))
        return result


class Clock:
    """Fake datetime for the jobs' timestamped roots, one second per call."""
    n = 0

    @classmethod
    def now(cls, tz=None):
        cls.n += 1
        return datetime.datetime(2026, 9, 23, 20, 0, 0, tzinfo=tz) + datetime.timedelta(seconds=cls.n)


def real_base(tmp, owned):
    w = types.ModuleType('fake_window_base')
    w.__file__ = str(HERE/'window-base-r11.py')
    exec(compile((HERE/'window-base-r11.py').read_bytes(), w.__file__, 'exec', dont_inherit=True), w.__dict__)
    w.load_support = lambda: (types.SimpleNamespace(ENV={}), None, owned)
    w.active_epoch = lambda o: None
    w.WORK = tmp/'work'
    w.GC = ['gc']
    return w


def git(repo, *args, home=None, check=True):
    env = dict(PATH='/usr/bin:/bin', HOME=str(home or repo), GIT_CONFIG_NOSYSTEM='1', LC_ALL='C')
    return subprocess.run(['/usr/bin/git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-C', str(repo),
                           *args], env=env, capture_output=True, check=check)


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
        for name in ('watch-r11.py', 'freshen-r11.py', 'hold-r11.py', 'release-r11.py', 'close-r11.py'):
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
        self.assertIn("w.require(records, 'hold is only for a stranded lifecycle; use CONTAIN')", text)
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
        self.assertTrue(all(f.relatime(p) for p in paths), [p for p in paths if not f.relatime(p)][:5])

    def test_hold_stranded_detection_over_fabricated_roots(self):
        h = self.load('hold-r11.py')
        with tempfile.TemporaryDirectory() as tmp:
            window = Path(tmp)/'window'
            done = Path(tmp)/'done'
            window.mkdir()
            done.mkdir()
            (window/'suspension-rig-resume-intent.json').write_text('{}')
            (window/'suspension-rig-resume-event.json').write_text('{}')
            (window/'rig-resume-started.json').write_text('{}')
            (window/'rig-resume-phase.json').write_text('{}')
            self.assertEqual(h.stranded(window, done), [])
            (window/'suspension-city-resume-intent.json').write_text('{}')
            self.assertEqual(h.stranded(window, done), ['suspension-city-resume-intent.json'])
            (window/'suspension-city-resume-event.json').write_text('{}')
            (window/'city-resume-started.json').write_text('{}')
            self.assertEqual(h.stranded(window, done), ['city-resume-started.json'])
            (window/'city-resume-phase.json').write_text('{}')
            (window/'suspension-city-suspend-failure.json').write_text('{}')
            self.assertEqual(h.stranded(window, done), ['suspension-city-suspend-failure.json'])
            (window/'suspension-city-suspend-failure.json').unlink()
            wrapper = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/operator/'
            (done/'ok.json').write_text(json.dumps(dict(exit=0, job=dict(wrapper=wrapper + 'CONTAIN-1.sh'))))
            (done/'other.json').write_text(json.dumps(dict(exit=1, job=dict(wrapper=wrapper + 'STAGE.sh'))))
            self.assertEqual(h.stranded(window, done), [])
            (done/'contain.json').write_text(json.dumps(dict(exit=1, job=dict(wrapper=wrapper + 'CONTAIN-1.sh'))))
            self.assertEqual(h.stranded(window, done), ['runner:contain.json'])
            (done/'contain-2.json').write_text(json.dumps(dict(exit=1, job=dict(wrapper=wrapper + 'CONTAIN-2.sh'))))
            self.assertEqual(h.stranded(window, done), ['runner:contain-2.json', 'runner:contain.json'])

    def test_budget_gate_counts_the_four_hour_bound_from_before_json(self):
        g = self.load('budget-r11.py')
        with tempfile.TemporaryDirectory() as tmp:
            g.WINDOW = Path(tmp)
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)

            def gate(age_minutes, required):
                (Path(tmp)/'before.json').write_text(json.dumps(dict(cache_access_clock=dict(start=dict(
                    boot=boot, boot_before_ns=now - age_minutes * 60 * 10**9)))))
                sys.argv[1:] = [str(required)]
                return g.main()
            self.assertEqual(gate(60, 40), 0)
            self.assertEqual(gate(210, 40), 1)
            self.assertEqual(gate(216, 25), 1)
            self.assertEqual(gate(200, 25), 0)

    def test_release_validates_everything_before_its_single_post(self):
        text = (HERE/'release-r11.py').read_text()
        validate = text.index('    session, task = validate_live(w, mode, release, run)')
        marker = text.index('fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)')
        post = text.index("run('post'")
        self.assertLess(validate, marker)
        self.assertLess(marker, post)
        body = text[text.index('def validate_live('):text.index('def main(')]
        for check in ("'exactly the named worker session is live'", "'task claimed by the session'",
                      "'startup proof digest'", "'gitignore entries are exactly the untracked paths'",
                      "'signing head and tree'", "'staged paths'", "'the worker session is not active'",
                      "'release differs from the worker candidate checkpoint'", "'staged patch digest'"):
            self.assertIn(check, body)
        self.assertIn("'the release line is the last one with its prefix'", text)
        self.assertIn("'--delivery', 'immediate', '--json'", text)
        self.assertIn("nudge.get('outcome') == 'delivered', 'nudge not delivered'", text)
        self.assertIn("validate_worktree(w, mode, release, run, root)\n        w.require(not release_lines(task.get('notes'), mode)", text)
        self.assertIn("['diff-index', '--cached', '--patch', '--binary', '--full-index', '--output=' + str(root/'staged.patch'), 'HEAD']", text)
        self.assertIn('`git diff-index --cached --patch --binary --full-index --output=.gc/worker-evidence/ga-4z38/candidate.patch HEAD`',
                      (HERE/'worker-brief.md').read_text())
        self.assertIn('with /home/loucmane/gascity/bin/bd show %s --json.', text)
        self.assertNotIn('last_json', text)
        self.assertNotIn('splitlines()[-1]', text)
        after = text[text.index('    if marker.exists():'):text.index('    else:\n        validate_worktree')]
        self.assertNotIn('validate_worktree', after)
        self.assertNotIn("run('post'", after)
        self.assertIn("root = VAR/('ga-4z38-%s-release-%s'", text)
        self.assertEqual(text.count("run('post'"), 1)
        # The pane is checked after the live validation, before either branch, and again before the nudge.
        main = text[text.index('def main('):]
        self.assertLess(main.index("pane_clear(w, run, session, 'pane-before-post')"), main.index('    if marker.exists():'))
        self.assertLess(main.index("pane_clear(w, run, session, 'pane-before-nudge')"), main.index("nudge = document(run('nudge'"))
        self.assertIn("['/usr/bin/tmux', '-u', '-L', 'city', 'capture-pane', '-p', '-t', session['session_name']]", text)

    def test_close_drains_once_and_closes_only_an_open_session(self):
        text = (HERE/'close-r11.py').read_text()
        self.assertIn('if session and not drain.exists():', text)
        self.assertIn('fd = os.open(drain, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)', text)
        self.assertIn("    still = open_sessions()\n    w.require(len(still) <= 1, 'more than one open worker session before close')", text)
        self.assertIn("listed['exit_code'] == 0 or 'no server running' in stderr", text)
        self.assertIn("('error connecting to' in stderr and ('No such file or directory' in stderr", text)
        self.assertIn("or 'Connection refused' in stderr))", text)
        self.assertIn("ROOT = VAR/('ga-4z38-close-' + datetime.now(timezone.utc)", text)
        self.assertIn("glob('ga-4z38-hold-*/result.json')", text)

    def test_repeatable_steps_have_numbered_slots_and_no_unnumbered_wrapper(self):
        names = set(WRAPPERS)
        for base, count in (('FRESHEN', 3), ('WATCH', 8), ('SOURCE-RELEASE', 3), ('SIGNING-RELEASE', 3), ('CLOSE', 2),
                            ('HOLD', 2), ('CONTAIN', 2)):
            self.assertNotIn(base + '.sh', names)
            for slot in range(1, count + 1):
                self.assertIn('%s-%d.sh' % (base, slot), names)
        for single in ('RECONCILE', 'BIND', 'OBSERVE', 'PREFLIGHT', 'STAGE', 'ROUTE', 'RESUME',
                       'ADMIT', 'RESTORE', 'TERMINAL'):
            self.assertIn(single + '.sh', names)

    def test_admit_requires_a_passing_close(self):
        text = (HERE/'operator'/'ADMIT.sh').read_text()
        self.assertIn('-path "/var/tmp/ga-4z38-close-*/result.json"', text)
        self.assertIn('xargs -r grep -l "$CLOSE_SHA"', text)
        [pin] = re.findall(r'^CLOSE_SHA=([0-9a-f]{64})$', text, re.M)
        self.assertEqual(pin, sha(HERE/'close-r11.py'))
        for name, minutes in (('SOURCE-RELEASE-1.sh', 100), ('SIGNING-RELEASE-1.sh', 85)):
            body = (HERE/'operator'/name).read_text()
            self.assertLess(body.index('step budget "$C/budget-r11.py" "$BUDGET_SHA" %d' % minutes),
                            body.index('step %s' % name.split('-1')[0].lower()), name)

    def test_cli_shapes_the_jobs_use(self):
        done = subprocess.run([sys.executable, '-B', str(HERE/'proof'/'cli-proof.py')],
                              capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        self.assertEqual(done.returncode, 0, done.stdout[-2000:] + done.stderr[-2000:])
        self.assertTrue(json.loads(done.stdout)['ok'])

    def test_hold_reads_the_real_runner_record_shape(self):
        h = self.load('hold-r11.py')
        real = json.loads(Path('/home/loucmane/.local/share/gas-city-staging/jobs/done/ga-4z38-prep-r3.json').read_text())
        self.assertTrue(real['job']['wrapper'].endswith('designs/ga-4z38-window/operator/PREP.sh'))
        self.assertEqual(real['exit'], 0)
        with tempfile.TemporaryDirectory() as tmp:
            window = Path(tmp)/'window'
            done = Path(tmp)/'done'
            window.mkdir()
            done.mkdir()
            record = json.loads(json.dumps(real))
            record['job']['wrapper'] = record['job']['wrapper'].replace('operator/PREP.sh', 'operator/CONTAIN-2.sh')
            record['exit'] = 1
            (done/'contain.json').write_text(json.dumps(record))
            self.assertEqual(h.stranded(window, done), ['runner:contain.json'])

    def test_singleton_is_preserved_while_it_owns_the_task(self):
        done = subprocess.run([sys.executable, '-B', str(HERE/'proof'/'singleton-proof.py')],
                              capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        self.assertEqual(done.returncode, 0, done.stdout[-2000:] + done.stderr[-2000:])
        self.assertTrue(json.loads(done.stdout)['ok'])

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
        self.assertIn('-exec grep -l \'"ok": true\' {} + | xargs -r grep -l "$FRESHEN_SHA"', text)
        [pin] = re.findall(r'^FRESHEN_SHA=([0-9a-f]{64})$', text, re.M)
        self.assertEqual(pin, sha(HERE/'freshen-r11.py'))
        for name, minutes in (('ADMIT.sh', 40), ('RESTORE.sh', 25), ('TERMINAL.sh', 8)):
            body = (HERE/'operator'/name).read_text()
            self.assertIn('step budget "$C/budget-r11.py" "$BUDGET_SHA" %d' % minutes, body, name)
            self.assertLess(body.index('step budget'), body.index('step', body.index('step budget') + 5), name)

    def test_restore_requires_the_admission_pass(self):
        text = (HERE/'operator'/'RESTORE.sh').read_text()
        self.assertIn('[ -e /var/tmp/ga-4z38-window-20260923-r1/restore-admission-pass.json ]', text)
        self.assertIn("assert not (w.ROOT / 'restore-consumed.json').exists()", (HERE/'restore-admission-r3.py').read_text())

    def test_contain_runs_each_suspend_only_once_and_only_after_its_resume(self):
        for slot in ('CONTAIN-1.sh', 'CONTAIN-2.sh'):
            text = (HERE/'operator'/slot).read_text()
            for action, resume in (('city-suspend', 'city-resume'), ('rig-suspend', 'rig-resume')):
                self.assertIn('[ -e /var/tmp/ga-4z38-window-20260923-r1/suspension-%s-event.json ] && '
                              '[ ! -e /var/tmp/ga-4z38-window-20260923-r1/suspension-%s-event.json ]' % (resume, action),
                              text)

    def test_resume_requires_route_and_route_audit(self):
        text = (HERE/'operator'/'RESUME.sh').read_text()
        self.assertIn('/var/tmp/ga-4z38-route-20260923-r1/result.json', text)
        self.assertIn('/var/tmp/ga-4z38-audit-route-20260923-r1/result.json', text)

    def test_watch_uses_the_active_epoch_not_the_quiescent_host(self):
        text = (HERE/'watch-r11.py').read_text()
        self.assertIn('w.active_epoch(o)', text)
        self.assertNotIn('w.host(o)', text)

    def test_watch_compares_routes_with_the_stage_reload_capture(self):
        text = (HERE/'watch-r11.py').read_text()
        self.assertIn("w.module(BASE.parent/'restore-r9-routes-r3.py', '%s')" % sha(HERE/'restore-r9-routes-r3.py'), text)
        self.assertIn("WINDOW/'stage-reload-generated-routes.json'", text)
        self.assertIn("routes_unchanged = routes_since_stage(w, o, routes, WINDOW/'stage-reload-generated-routes.json')", text)
        self.assertIn('routes_unchanged_since_stage=routes_unchanged', text)

    def test_release_line_selection_and_json_documents(self):
        r = self.load('release-r11.py')
        source = r.line_for('source', dict(b=1, a=2))
        self.assertEqual(source, 'SOURCE_RELEASE ga-4z38 {"a":2,"b":1}')
        notes = '\n'.join(['old note', source, 'SIGNING_RELEASE ga-4z38 {}', 'SOURCE_RELEASE ga-4z38x {}',
                           ' SOURCE_RELEASE ga-4z38 {}', 'SOURCE_RELEASE ga-4z38 {"later":1}'])
        self.assertEqual(r.release_lines(notes, 'source'), [source, 'SOURCE_RELEASE ga-4z38 {"later":1}'])
        self.assertEqual(r.release_lines(notes, 'signing'), ['SIGNING_RELEASE ga-4z38 {}'])
        self.assertEqual(r.release_lines(None, 'source'), [])
        self.assertEqual(r.document('{\n  "ok": true,\n  "suspended": false\n}\n'), dict(ok=True, suspended=False))
        self.assertEqual(r.document('{"sessions":[]}\n'), dict(sessions=[]))

    def test_release_main_runs_every_slot_against_the_real_base(self):
        r = self.load('release-r11.py')
        r._SOURCE_SHA = sha(HERE/'release-r11.py')
        r.datetime = Clock
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            state = dict(notes='BIND request', pane='CANDIDATE_REVIEW_READY\n\n> \n', patch=b'diff --git a/x b/x\n')
            index = '100644 %s 0\tinternal/sling/cycle.go\0' % ('a' * 40)
            listing = '100644 blob %s\tinternal/sling/cycle.go\0' % ('a' * 40)

            def respond(argv):
                if argv[:1] == ['gc']:
                    rest = argv[1:]
                    if rest == ['status', '--json']:
                        return 0, '{\n  "ok": true,\n  "suspended": false\n}\n', ''
                    if rest == ['session', 'list', '--json']:
                        return 0, json.dumps(dict(sessions=[dict(id='ci-1', template=r.TEMPLATE, closed=False,
                                                                 state='active', session_name='gc-ci-1')])) + '\n', ''
                    if rest[:4] == ['--rig', 'gascity', 'bd', 'show']:
                        return 0, json.dumps([dict(status='in_progress', assignee='ci-1', notes=state['notes'])]), ''
                    if rest[:4] == ['--rig', 'gascity', 'bd', 'update']:
                        state['notes'] += '\n' + rest[-1]
                        return 0, '', ''
                    if rest[:2] == ['session', 'nudge']:
                        return 0, '{"ok":true,"outcome":"delivered"}\n', ''
                if argv[:4] == ['/usr/bin/tmux', '-u', '-L', 'city']:
                    return 0, state['pane'], ''
                if argv[0] == '/usr/bin/git':
                    sub = argv[argv.index('-C') + 2:]
                    if sub[0] == 'status':
                        return 0, state['status'], ''
                    if sub == ['rev-parse', 'HEAD']:
                        return 0, r.BASE_COMMIT + '\n', ''
                    if sub[:3] == ['diff-index', '--cached', '--name-only']:
                        return 0, 'internal/sling/cycle.go\n', ''
                    if sub[0] == 'ls-tree':
                        return 0, listing, ''
                    if sub[0] == 'ls-files':
                        return 0, index, ''
                    if sub[:5] == ['diff-index', '--cached', '--patch', '--binary', '--full-index']:
                        Path(sub[5].split('=', 1)[1]).write_bytes(state['patch'])
                        return 0, '', ''
                raise AssertionError('unexpected argv %r' % argv)
            owned = FakeOwned(respond)
            w = real_base(tmp, owned)
            r.load = lambda: w
            for name in ('window', 'input', 'var'):
                (tmp/name).mkdir()
            evidence = tmp/'work'/'.gc/worker-evidence/ga-4z38'
            evidence.mkdir(parents=True)
            (tmp/'window'/'suspension-city-resume-event.json').write_text('{}')
            r.WINDOW, r.INPUT, r.VAR = tmp/'window', tmp/'input', tmp/'var'
            (evidence/'startup-proof.json').write_text('{"proof": 1}')
            reviews = ['review one', 'review two']
            source = dict(schema='ga-4z38.source-release.v1', task='ga-4z38', session='ci-1', base=r.BASE_COMMIT,
                          startup_proof_sha256=sha(evidence/'startup-proof.json'),
                          gitignore_entries=['/.claude/settings.local.json'], reviews=reviews)
            (tmp/'input'/'source-release.json').write_text(json.dumps(source))
            state['status'] = '?? .claude/settings.local.json\0'

            def slot(mode):
                sys.argv[1:] = [mode]
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    r.main()
                return json.loads(out.getvalue())
            # A dialog on the pane refuses before the marker: nothing is consumed.
            state['pane'] = ' Do you want to proceed?\n \u276f 1. Yes\n'
            with self.assertRaises(RuntimeError):
                slot('source')
            self.assertFalse((tmp/'var'/'ga-4z38-source-release.posted').exists())
            state['pane'] = 'STARTUP_PROOF_READY\n\n> \n'
            first = slot('source')
            self.assertTrue(first['ok'] and first['posted_now'] and first['nudge'] == 'delivered')
            again = slot('source')
            self.assertTrue(again['ok'] and not again['posted_now'])
            self.assertEqual(len(r.release_lines(state['notes'], 'source')), 1)
            # The signing release, with the staged index, the tree and the worker checkpoint.
            state['status'] = 'M  internal/sling/cycle.go\0'
            (evidence/'candidate.patch').write_bytes(state['patch'])
            signing = dict(schema='ga-4z38.signing-release.v1', task='ga-4z38', session='ci-1', base=r.BASE_COMMIT,
                           head=r.BASE_COMMIT, tree='b' * 40, staged_patch_sha256=sha(evidence/'candidate.patch'),
                           reviews=reviews)
            (evidence/'candidate.json').write_text(json.dumps(dict(head=signing['head'], tree=signing['tree'],
                                                                   staged_patch_sha256=signing['staged_patch_sha256'])))
            (tmp/'input'/'signing-release.json').write_text(json.dumps(signing))
            self.assertTrue(slot('signing')['posted_now'])
            self.assertFalse(slot('signing')['posted_now'])
            self.assertEqual(len(r.release_lines(state['notes'], 'signing')), 1)
            posts = [argv for name, argv in owned.calls if name == 'post']
            self.assertEqual(len(posts), 2)
            names = [name for name, argv in owned.calls]
            self.assertEqual(names.count('pane-before-post'), 5)
            self.assertEqual(names.count('pane-before-nudge'), 4)
            # A tree that does not list the staged index refuses before the post.
            (tmp/'var'/'ga-4z38-signing-release.posted').unlink()
            state['notes'] = state['notes'].replace(r.release_lines(state['notes'], 'signing')[0], 'withdrawn')
            listing = '100644 blob %s\tinternal/sling/cycle.go\0' % ('c' * 40)
            with self.assertRaisesRegex(RuntimeError, 'release tree differs from the staged index'):
                slot('signing')
            self.assertFalse((tmp/'var'/'ga-4z38-signing-release.posted').exists())

    def test_close_main_ends_only_an_empty_city_server(self):
        c = self.load('close-r11.py')
        c._SOURCE_SHA = sha(HERE/'close-r11.py')
        c.datetime = Clock
        ticks = {'t': 0.0}

        def monotonic():
            ticks['t'] += 7.0
            return ticks['t']
        c.time = types.SimpleNamespace(monotonic=monotonic, sleep=lambda seconds: None)
        for panes, expect_kill in (('', True), ('gc-other 4242\n', False)):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                row = dict(id='ci-1', template=c.TEMPLATE, closed=False, state='active')
                state = dict(open=[row], server=True, procs=[dict(pid=7, cwd='/')])

                def respond(argv):
                    if argv[:4] == ['gc', 'session', 'list', '--json']:
                        return 0, json.dumps(dict(sessions=state['open'])) + '\n', ''
                    if argv[:3] == ['gc', 'runtime', 'drain']:
                        state['open'] = [dict(row, state='stopped')]
                        return 0, '{"ok":true,"status":"draining"}\n', ''
                    if argv[:3] == ['gc', 'session', 'close']:
                        state['open'] = []
                        return 0, '{"ok":true,"command":"session close","session_id":"ci-1"}\n', ''
                    if argv[:5] == ['/usr/bin/tmux', '-u', '-L', 'city', 'list-panes']:
                        if state['server']:
                            return 0, panes, ''
                        return 1, '', 'no server running on /tmp/tmux-1000/city\n'
                    if argv == ['/usr/bin/tmux', '-u', '-L', 'city', 'kill-server']:
                        state['server'] = False
                        state['procs'] = []
                        return 0, '', ''
                    raise AssertionError('unexpected argv %r' % argv)
                owned = FakeOwned(respond)
                w = real_base(tmp, owned)
                c.load = lambda: w
                c.processes = lambda work: list(state['procs'])
                (tmp/'window').mkdir()
                (tmp/'var').mkdir()
                (tmp/'window'/'suspension-rig-suspend-event.json').write_text('{}')
                c.WINDOW, c.VAR = tmp/'window', tmp/'var'
                if expect_kill:
                    with contextlib.redirect_stdout(io.StringIO()) as out:
                        c.main()
                    result = json.loads(out.getvalue())
                    self.assertTrue(result['ok'] and result['tmux_server_killed'])
                else:
                    with self.assertRaisesRegex(RuntimeError, 'residue remains'):
                        c.main()
                kills = [argv for name, argv in owned.calls if argv[-1] == 'kill-server']
                self.assertEqual(len(kills), 1 if expect_kill else 0)
                self.assertTrue((tmp/'var'/'ga-4z38-close-drain.requested').exists())

    def test_watch_main_runs_before_and_after_stage_against_the_real_base(self):
        watch = self.load('watch-r11.py')
        watch._SOURCE_SHA = sha(HERE/'watch-r11.py')
        watch.datetime = Clock
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            def respond(argv):
                if argv[:1] == ['gc']:
                    rest = argv[1:]
                    if rest == ['session', 'list', '--json']:
                        return 0, '{"sessions":[]}\n', ''
                    if rest[:4] == ['--rig', 'gascity', 'bd', 'show']:
                        return 0, json.dumps([dict(status='open', assignee=None, metadata={})]), ''
                    if rest[:2] == ['bd', 'list']:
                        return 0, '[]', ''
                    if rest[:2] == ['trace', 'show']:
                        return 0, '{"records":[]}', ''
                if argv[0] == '/usr/bin/git':
                    sub = argv[argv.index('-C') + 2:]
                    if sub == ['rev-parse', 'HEAD']:
                        return 0, 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88\n', ''
                    if sub[0] == 'branch':
                        return 0, 'codex/ga-4z38-typed-route-cycles\n', ''
                    if sub[0] == 'status':
                        return 0, '?? .claude/settings.local.json\0', ''
                    if sub[0] in ('diff-files', 'diff-index'):
                        return 0, '', ''
                if argv[:3] == ['/usr/bin/tmux', '-L', 'city']:
                    return 1, '', 'no server running on /tmp/tmux-1000/city\n'
                raise AssertionError('unexpected argv %r' % argv)
            w = real_base(tmp, FakeOwned(respond))
            rows = {'/r': dict(metadata=dict(atime_ns=1), parent=dict(mtime_ns=2), content='x', sha256='y')}
            w.module = lambda path, pin: types.SimpleNamespace(capture_routes=lambda w, o: json.loads(json.dumps(rows)))
            watch.load = lambda: w
            (tmp/'work'/'.claude').mkdir(parents=True)
            (tmp/'work'/'.claude'/'settings.local.json').write_text('{}')
            (tmp/'window').mkdir()
            (tmp/'var').mkdir()
            (tmp/'window'/'preflight-pass.json').write_text('{}')
            watch.WINDOW, watch.VAR = tmp/'window', tmp/'var'
            for stage in (False, True):
                if stage:
                    (tmp/'window'/'stage-reload-generated-routes.json').write_text(json.dumps(dict(after=rows)))
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    watch.main()
                summary = json.loads(out.getvalue())
                self.assertTrue(summary['ok'])
                self.assertEqual(summary['routes_unchanged_since_stage'], True if stage else None)
                result = json.loads((Path(summary['root'])/'result.json').read_text())
                self.assertEqual(result['staged'], [])
                self.assertEqual(result['status_records'], ['?? .claude/settings.local.json'])

    def test_watch_routes_since_stage(self):
        watch = self.load('watch-r11.py')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            w = real_base(tmp, None)
            event = tmp/'stage-reload-generated-routes.json'
            rows = {'/r': dict(metadata=dict(atime_ns=1, inode=2), parent=dict(mtime_ns=3), content='x', sha256='y')}
            routes = types.SimpleNamespace(capture_routes=lambda w, o: json.loads(json.dumps(rows)))
            self.assertIsNone(watch.routes_since_stage(w, None, routes, event))
            event.write_text(json.dumps(dict(after=rows)))
            self.assertIs(watch.routes_since_stage(w, None, routes, event), True)
            rows['/r']['metadata']['atime_ns'] = 9
            self.assertEqual(watch.routes_since_stage(w, None, routes, event), ['/r metadata.atime_ns'])

            def refuse(w, o):
                raise RuntimeError('route authority')
            self.assertEqual(watch.routes_since_stage(w, None, types.SimpleNamespace(capture_routes=refuse), event),
                             'refused: route authority')

    def test_tree_listing_equals_the_staged_index_in_a_real_repository(self):
        r = self.load('release-r11.py')
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)/'repo'
            repo.mkdir()
            git(repo, 'init', '-q')
            (repo/'dir').mkdir()
            (repo/'a.txt').write_text('a\n')
            (repo/'dir'/'b.txt').write_text('b\n')
            git(repo, 'add', '-A')
            tree = git(repo, 'write-tree').stdout.decode().strip()
            listing = git(repo, 'ls-tree', '-r', '-z', '--full-tree', tree).stdout.decode()
            index = git(repo, 'ls-files', '-s', '-z').stdout.decode()
            self.assertEqual(r.tree_entries(listing), r.index_entries(index))
            self.assertEqual(len(r.index_entries(index)), 2)
            (repo/'a.txt').write_text('changed\n')
            git(repo, 'add', 'a.txt')
            self.assertNotEqual(r.tree_entries(listing), r.index_entries(git(repo, 'ls-files', '-s', '-z').stdout.decode()))
            self.assertIsNone(r.index_entries('100644 %s 2\tx\0' % ('a' * 40)))

    def test_patch_bytes_ignore_diff_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            repo = tmp/'repo'
            repo.mkdir()
            git(repo, 'init', '-q')
            (repo/'a.txt').write_text(''.join('line %d\n' % i for i in range(40)))
            (repo/'bin.dat').write_bytes(bytes(range(256)))
            git(repo, 'add', '-A')
            git(repo, 'commit', '-q', '-m', 'base')
            (repo/'a.txt').write_text(''.join('line %d\n' % (i if i != 20 else 99) for i in range(40)))
            (repo/'bin.dat').write_bytes(bytes(reversed(range(256))))
            (repo/'new.txt').write_text('new\n')
            git(repo, 'add', '-A')
            plain, noisy = tmp/'plain', tmp/'noisy'
            plain.mkdir()
            noisy.mkdir()
            (noisy/'.gitconfig').write_text('[diff]\n\tnoprefix = true\n\tmnemonicPrefix = true\n\talgorithm = patience\n'
                                            '\tcontext = 9\n\trenames = copies\n[core]\n\tabbrev = 4\n'
                                            '[color]\n\tui = always\n\tdiff = always\n')
            outputs = []
            for home, extra in ((plain, []), (noisy, []), (plain, ['-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null'])):
                out = tmp/('patch-%d' % len(outputs))
                git(repo, *extra, 'diff-index', '--cached', '--patch', '--binary', '--full-index', '--output=' + str(out),
                    'HEAD', home=home)
                outputs.append(out.read_bytes())
            self.assertTrue(outputs[0])
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])
            self.assertIn(b'GIT binary patch', outputs[0])

    def test_release_refuses_to_nudge_over_a_permission_dialog(self):
        r = self.load('release-r11.py')
        dialog = ('\u25cf Bash(rm -rf build)\n  rm -rf build\n\n Do you want to proceed?\n \u276f 1. Yes\n'
                  "   2. Yes, and don't ask again\n   3. No, and tell Claude what to do differently (esc)\n")
        self.assertTrue(r.dialog_showing(dialog))
        self.assertTrue(r.dialog_showing(' Do you want to make this edit to cycle.go?\n'))
        self.assertTrue(r.dialog_showing('\u25cf Bash(go test)\nThis command requires approval\n'))
        self.assertTrue(r.dialog_showing('   \u276f 1. Yes\n'))
        self.assertTrue(r.dialog_showing('Which approach?\n\u276f 1. Keep the cycle check\n  2. Split it\n'))
        self.assertTrue(r.dialog_showing(' \u276f 1. Stop and wait for limit to reset\n'))
        self.assertFalse(r.dialog_showing('Steps:\n1. Ran the RED test\n2. Made it GREEN\n'))
        idle = ('CANDIDATE_REVIEW_READY\n\n\u256d\u2500\u2500\u2500\u256e\n\u2502 > \u2502\n'
                '\u2570\u2500\u2500\u2500\u256f\n  ? for shortcuts\n')
        self.assertFalse(r.dialog_showing(idle))
        self.assertFalse(r.dialog_showing('Reported: 1 test failed, then 1 passed. Yesterday it passed.\n'))
        self.assertFalse(r.dialog_showing(''))


class Task(unittest.TestCase):
    def test_bind_request_and_metadata_name_ga_4z38(self):
        text = (HERE/'bind-task-r3.py').read_text()
        self.assertIn('"bead_id":"ga-4z38"', text)
        self.assertIn("'.gc/worker-evidence/ga-4z38/implementation-summary.md'", text)
        self.assertIn("WORK='/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles'", text)

    def test_task_still_meets_the_binding_preconditions(self):
        if os.path.lexists('/var/tmp/ga-4z38-bind-20260923-r1'):
            self.skipTest('BIND has run; the route checks the bound image instead')
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
