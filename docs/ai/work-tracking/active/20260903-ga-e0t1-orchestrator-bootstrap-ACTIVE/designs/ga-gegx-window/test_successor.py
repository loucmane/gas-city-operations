"""The ga-gegx package is exactly the successor derivation of the reviewed ga-f37t s7 package."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWN = {'README.md', 'test_successor.py', 'generators/make_successor.py'}
# ga-f37t may appear only in these exact places (RECONCILE's held predecessor is checked separately).
ALLOWED = ['/var/tmp/ga-f37t-recover-20260925-r2',
           '/var/tmp/ga-f37t-window-20260925-r2/suspension-baseline.json',
           '# ga-f37t s3 disposition, for independent review:',
           '# ga-f37t s4 disposition, operator-approved 2026-09-25, for independent review:',
           '# ga-f37t s5 disposition, operator-approved 2026-09-25 in place of FRESHEN, for independent review:',
           '# ga-f37t s5 start gate, for independent review.',
           'reviewed ga-f37t RECOVER-2 job', 'the ga-f37t window stopped at HOLD and CLOSE',
           'the ga-4z38 and ga-f37t silent starts', 'It is the reviewed ga-f37t prep',
           'ga-y49e, ga-4z38 and ga-f37t attempts']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_files():
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            yield path


class Derivation(unittest.TestCase):
    def base(self):
        m = types.ModuleType('successor_base')
        m.__file__ = str(HERE/'window-base-r11.py')
        exec(compile((HERE/'window-base-r11.py').read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
        return m

    def test_every_file_is_the_successor_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, '-B', str(HERE/'generators'/'make_successor.py'), tmp],
                                  capture_output=True, text=True, timeout=300)
            self.assertEqual(done.returncode, 0, done.stderr)
            produced = {str(p.relative_to(tmp)) for p in Path(tmp).rglob('*') if p.is_file()}
            tracked = {str(p.relative_to(HERE)) for p in package_files()}
            self.assertEqual(tracked - produced, OWN)
            self.assertEqual(produced - tracked, set())
            for name in sorted(produced):
                self.assertEqual(sha(Path(tmp)/name), sha(HERE/name), name)

    def test_ga_f37t_appears_only_where_intended(self):
        for path in package_files():
            rel = str(path.relative_to(HERE))
            if rel in OWN:
                continue
            text = path.read_text()
            for allowed in ALLOWED:
                text = text.replace(allowed, '')
            if path.name == 'reconcile-predecessor-r3.py':
                self.assertIn("before=bead('ga-f37t');other=bead('ga-4z38');new=bead('ga-gegx')", text)
                self.assertIn("attempt['session_id']=='ci-yauk5'", text)
                self.assertIn("closed[0]['metadata']['state']=='stale-session'", text)
                self.assertIn("'bd','update','ga-f37t','--status','blocked'", text)
                continue
            self.assertNotIn('ga-f37t', text, rel)
            self.assertNotIn('f37t', text, rel)

    def test_the_worker_binds_the_fresh_worktree(self):
        brief = (HERE/'worker-brief.md').read_text()
        self.assertIn('Worktree /home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles.', brief)
        self.assertIn('Branch codex/ga-gegx-typed-route-cycles.', brief)
        self.assertIn('TestGagegxCapabilityProbeNoTests', brief)
        self.assertIn("BEAD='ga-gegx'", (HERE/'bind-task-r3.py').read_text())

    def test_route_binds_the_new_bind(self):
        [route] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", (HERE/'route-task-r5.py').read_text(), re.M)
        [brief] = re.findall(r"^BRIEF_SHA='([0-9a-f]{64})'$", (HERE/'route-task-r5.py').read_text(), re.M)
        self.assertEqual(route, sha(HERE/'bind-task-r3.py'))
        self.assertEqual(brief, sha(HERE/'worker-brief.md'))
        self.assertIn(sha(HERE/'worker-brief.md'), (HERE/'bind-task-r3.py').read_text())

    def test_every_wrapper_pin_names_the_file_it_launches(self):
        for wrapper in sorted((HERE/'operator').glob('*.sh')):
            text = wrapper.read_text()
            pins = dict(re.findall(r'^([A-Z_]+_SHA)=([0-9a-f]{64})$', text, re.M))
            steps = re.findall(r'"\$C/([^"]+)" "\$([A-Z_]+_SHA)"', text)
            self.assertTrue(steps, wrapper.name)
            for target, pin in steps:
                self.assertEqual(pins[pin], sha(HERE/target), (wrapper.name, target))

    def test_every_script_pin_names_the_file_it_loads(self):
        base = sha(HERE/'window-base-r11.py')
        for name in ('bind-task-r3.py', 'watch-r11.py', 'release-r11.py', 'close-r11.py',
                     'hold-r11.py', 'window-r11.py', 'window-obs-r11.py'):
            self.assertIn(base, (HERE/name).read_text(), name)
        window = sha(HERE/'window-r11.py')
        for name in ('route-task-r5.py', 'restore-admission-r3.py', 'observe-terminal-r11.py'):
            self.assertIn(window, (HERE/name).read_text(), name)
        obs = sha(HERE/'window-obs-r11.py')
        for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
            [pin] = re.findall(r"^W_SHA='([0-9a-f]{64})'$", (HERE/name).read_text(), re.M)
            self.assertEqual(pin, obs, name)

    def test_prep_keeps_nudge_on_route_and_pins_the_derived_overlay(self):
        prep = (HERE/'prep-r11.py').read_text()
        self.assertIn("    names = [name for name in names if name != 'nudge-on-route']\n", prep)
        self.assertLess(prep.index("len(names) == ORDER_COUNT"), prep.index("name != 'nudge-on-route'"))
        self.assertLess(prep.index("name != 'nudge-on-route'"), prep.index("parts = [HEADER, '[orders]\\n'"))
        [pin] = re.findall(r"^OVERLAY_SHA = '([0-9a-f]{64})'$", prep, re.M)
        spec = __import__('importlib.util').util.spec_from_file_location('g', HERE/'generators'/'make_successor.py')
        g = __import__('importlib.util').util.module_from_spec(spec)
        spec.loader.exec_module(g)
        if not g.OLD_OVERLAY.exists():
            self.skipTest('no ga-f37t PREP overlay on this host')
        overlay = g.successor_overlay()
        self.assertEqual(pin, hashlib.sha256(overlay).hexdigest())
        text = overlay.decode()
        self.assertNotIn('"nudge-on-route"', text)
        self.assertIn('"nudge-mail-sweep"', text)
        self.assertIn('work_dir = "/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles"', text)
        [pinned] = re.findall(r'^PREP_SHA=([0-9a-f]{64})$', (HERE/'operator'/'PREP.sh').read_text(), re.M)
        self.assertEqual(pinned, sha(HERE/'prep-r11.py'))

    def test_observe_binds_the_recover2_result(self):
        observe = (HERE/'observe-integrity-r11.py').read_text()
        self.assertIn("RECOVER_ROOT='/var/tmp/ga-f37t-recover-20260925-r2'", observe)
        self.assertIn('    w.RECOVERY=(RECOVER_ROOT,RECOVER_SHA)\n', observe)
        [pin] = re.findall(r"^RECOVER_SHA='([0-9a-f]{64})'$", observe, re.M)
        result = Path('/var/tmp/ga-f37t-recover-20260925-r2/result.json')
        if result.exists():
            self.assertEqual(pin, sha(result))

    def test_recovery_disposition_admits_the_recovered_city(self):
        result = Path('/var/tmp/ga-f37t-recover-20260925-r2/result.json')
        if not result.exists():
            self.skipTest('no ga-f37t RECOVER-2 record on this host')
        m = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        chained = m.approved_coordinator_cache_image(m.approved_restore_image(
            m.approved_epoch_image(m.approved_historical_image(prior), prior['host'])))
        value = m.approved_recovery_image(chained, str(result.parent), sha(result))
        recorded = json.loads(result.read_text())
        city, receipt, suspension = str(m.CITY/'city.toml'), str(m.RECEIPT), m.SUSPENSION
        self.assertEqual(value['pins'][city], recorded['city_pin'])
        self.assertEqual(value['pins'][receipt], recorded['receipt_pin'])
        self.assertEqual(value['pins'][suspension], recorded['suspension']['pin'])
        rest = json.loads(json.dumps(value))
        for path in (city, receipt, suspension):
            rest['pins'][path] = chained['pins'][path]
        self.assertEqual(rest, chained)
        # Another result digest, changed content, a changed suspension image or a shared root refuses.
        with self.assertRaises(RuntimeError):
            m.approved_recovery_image(chained, str(result.parent), '0' * 64)
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        root.chmod(0o700)
        for change, message in ((lambda r: r['city_pin'].update(sha256='0' * 64), 'recovered content differs'),
                                (lambda r: r['receipt_pin'].update(sha256='0' * 64), 'recovered content differs'),
                                (lambda r: r.update(worker_launched=True), 'recovery result'),
                                (lambda r: r.update(read_errors={'x': 'y'}), 'recovery result')):
            changed = json.loads(json.dumps(recorded))
            change(changed)
            (root/'result.json').unlink(missing_ok=True)
            (root/'result.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(RuntimeError, message):
                m.approved_recovery_image(chained, str(root), sha(root/'result.json'))
        raw = json.loads(recorded['suspension']['raw'])
        raw['city']['suspended'] = False
        changed = json.loads(json.dumps(recorded))
        changed['suspension']['raw'] = json.dumps(raw)
        changed['suspension']['pin']['sha256'] = hashlib.sha256(changed['suspension']['raw'].encode()).hexdigest()
        changed['suspension']['pin']['metadata']['size'] = len(changed['suspension']['raw'].encode())
        (root/'result.json').unlink()
        (root/'result.json').write_text(json.dumps(changed))
        with self.assertRaisesRegex(RuntimeError, 'recovered suspension state differs'):
            m.approved_recovery_image(chained, str(root), sha(root/'result.json'))
        root.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'recovery root authority'):
            m.approved_recovery_image(chained, str(root), sha(root/'result.json'))

    def test_fresh_roots_and_dropped_jobs(self):
        for name in ('recover-stage-r1.py', 'recover-window-r2.py', 'freshen-r11.py', 'operator/RECOVER.sh',
                     'operator/RECOVER-2.sh', 'operator/FRESHEN-1.sh'):
            self.assertFalse((HERE/name).exists(), name)
        self.assertIn("ROOT = Path('/var/tmp/ga-gegx-window-20260925-r2')", (HERE/'window-base-r11.py').read_text())
        self.assertIn("INTEGRITY=Path('/var/tmp/ga-gegx-integrity-20260925-r5')", (HERE/'window-r11.py').read_text())
        for path in ('/var/tmp/ga-gegx-window-20260925-r2', '/var/tmp/ga-gegx-integrity-20260925-r5',
                     '/var/tmp/ga-gegx-prep-20260923-r2', '/var/tmp/ga-gegx-bind-20260923-r1',
                     '/var/tmp/ga-gegx-reconcile-20260925-r1'):
            self.assertIn(path, ''.join(p.read_text() for p in package_files() if p.suffix in ('.py', '.sh')))

    def test_twelve_watch_slots_differ_only_in_slot(self):
        slots = sorted((HERE/'operator').glob('WATCH-*.sh'), key=lambda p: int(p.stem.split('-')[1]))
        self.assertEqual([p.stem for p in slots], ['WATCH-%d' % n for n in range(1, 13)])
        normal = {re.sub(r'(WATCH-|watch-|Slot )\d+', r'\1N', p.read_text()) for p in slots}
        self.assertEqual(len(normal), 1)

    def test_reload_fix_and_read_accounting_are_kept(self):
        window = (HERE/'window-r11.py').read_text()
        self.assertIn("ack['outcome'] in ('applied','no_change') and ack['revision']==w.REVISION[i]", window)
        self.assertIn("pending_routes=dict(name=prefix+'-reload',routes=routes.capture_routes(w,o),", window)
        self.assertIn("accounting['read_time_changes']=w.account_read_times(a,z,accounting['window'])", window)
        base = (HERE/'window-base-r11.py').read_text()
        self.assertIn("    if action=='preflight':\n        stable_read_times()\n        ROOT.mkdir(mode=0o700)\n", base)


if __name__ == '__main__':
    unittest.main()
