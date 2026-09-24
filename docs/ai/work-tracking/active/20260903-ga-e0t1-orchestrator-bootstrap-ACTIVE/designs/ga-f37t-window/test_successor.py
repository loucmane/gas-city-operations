"""The ga-f37t package is exactly the successor derivation of the reviewed ga-4z38 r14 package."""
import hashlib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWN = {'README.md', 'test_successor.py', 'generators/make_successor.py'}
# ga-4z38 may appear only in these exact places (RECONCILE's held predecessor is checked separately).
ALLOWED = ['/var/tmp/ga-4z38-platform-inspector-20260924-r1',
           'r2 (after job ga-4z38-prep refused fail-closed at 16:06:01Z; root -r1 preserved):',
           '# ga-4z38 disposition, for independent review:',
           '# ga-4z38 r13 disposition, for independent review:',
           'It is the reviewed ga-4z38 prep r3 rebound to ga-f37t',
           'belong to the ga-4z38 jobs',
           'the consumed predecessor ga-4z38\n',
           'ga-y49e and ga-4z38 attempts',
           'The ga-4z38 worker went silent',
           '/var/tmp/ga-4z38-terminal-20260923-r1/observed-after.json',
           'the ga-4z38 window restored the city exactly']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_files():
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            yield path


class Derivation(unittest.TestCase):
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

    def test_ga_4z38_appears_only_where_intended(self):
        for path in package_files():
            rel = str(path.relative_to(HERE))
            if rel in OWN:
                continue
            text = path.read_text()
            for allowed in ALLOWED:
                text = text.replace(allowed, '')
            if path.name == 'reconcile-predecessor-r3.py':
                self.assertIn("before=bead('ga-4z38')", text)
                self.assertIn("attempt['session_id']=='ci-gi0lh'", text)
                self.assertIn("closed[0]['metadata']['state']=='stale-session'", text)
                self.assertIn("new=bead('ga-f37t')", text)
                continue
            self.assertNotIn('ga-4z38', text, rel)
            self.assertNotIn('4z38', text, rel)

    def test_the_rebuilt_inspector_path_is_kept(self):
        for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
            text = (HERE/name).read_text()
            self.assertIn("BUILD=Path('/var/tmp/ga-4z38-platform-inspector-20260924-r1')", text, name)
            self.assertIn('b8ebcde38a9ee8078752949226f6736ea14a25413fba73db4d95076261658d13', text, name)

    def test_the_worker_binds_the_fresh_worktree(self):
        brief = (HERE/'worker-brief.md').read_text()
        self.assertIn('Worktree /home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles.', brief)
        self.assertIn('Branch codex/ga-f37t-typed-route-cycles.', brief)
        self.assertIn("BEAD='ga-f37t'", (HERE/'bind-task-r3.py').read_text())

    def test_route_binds_the_bind_that_ran(self):
        # BIND ran once, at s2 r2; ROUTE checks its record, so ROUTE pins that executor digest.
        import json
        [route] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", (HERE/'route-task-r5.py').read_text(), re.M)
        [brief] = re.findall(r"^BRIEF_SHA='([0-9a-f]{64})'$", (HERE/'route-task-r5.py').read_text(), re.M)
        self.assertEqual(route, '159452692546d4d08512d2b1a11a2b479bc1438e40e83fe009d05427a110417a')
        self.assertEqual(brief, sha(HERE/'worker-brief.md'))
        intent = Path('/var/tmp/ga-f37t-bind-20260923-r1/binding-intent.json')
        if intent.exists():
            recorded = json.loads(intent.read_text())
            self.assertEqual(recorded['executor_sha256'], route)
            self.assertEqual(recorded['brief_sha256'], brief)
        [wrapper] = re.findall(r'^BIND_SHA=([0-9a-f]{64})$', (HERE/'operator'/'BIND.sh').read_text(), re.M)
        self.assertEqual(wrapper, sha(HERE/'bind-task-r3.py'))

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
        for name in ('bind-task-r3.py', 'freshen-r11.py', 'watch-r11.py', 'release-r11.py', 'close-r11.py',
                     'hold-r11.py', 'window-r11.py', 'window-obs-r11.py'):
            text = (HERE/name).read_text()
            self.assertIn(base, text, name)
        window = sha(HERE/'window-r11.py')
        for name in ('route-task-r5.py', 'restore-admission-r3.py', 'observe-terminal-r11.py'):
            self.assertIn(window, (HERE/name).read_text(), name)
        self.assertIn(sha(HERE/'worker-brief.md'), (HERE/'bind-task-r3.py').read_text())

    def test_twelve_watch_slots_differ_only_in_slot(self):
        slots = sorted((HERE/'operator').glob('WATCH-*.sh'), key=lambda p: int(p.stem.split('-')[1]))
        self.assertEqual([p.stem for p in slots], ['WATCH-%d' % n for n in range(1, 13)])
        normal = {re.sub(r'(WATCH-|watch-|Slot )\d+', r'\1N', p.read_text()) for p in slots}
        self.assertEqual(len(normal), 1)

    def base(self):
        import json
        import types
        m = types.ModuleType('successor_base')
        m.__file__ = str(HERE/'window-base-r11.py')
        exec(compile((HERE/'window-base-r11.py').read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
        return m, json

    def test_restore_disposition_admits_the_restored_city(self):
        refused = Path('/var/tmp/ga-f37t-integrity-20260924-r2/before-refused-observation.json')
        if not refused.exists():
            self.skipTest('no s2 r2 refused observation on this host')
        m, json = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        value = json.loads(refused.read_text())
        chained = m.approved_restore_image(m.approved_epoch_image(m.approved_historical_image(prior), value['host']))
        self.assertEqual(m.dependency_image(chained), m.dependency_image(value))
        without = m.approved_epoch_image(m.approved_historical_image(prior), value['host'])
        self.assertNotEqual(m.dependency_image(without), m.dependency_image(value))

    def test_restore_disposition_refuses_changed_content(self):
        if not Path('/var/tmp/ga-4z38-terminal-20260923-r1/observed-after.json').exists():
            self.skipTest('no ga-4z38 TERMINAL record on this host')
        m, json = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        prior['pins']['/home/loucmane/gascity/city/city.toml']['sha256'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'restored content differs'):
            m.approved_restore_image(prior)

    def test_prep_wrapper_pins_prep(self):
        text = (HERE/'operator'/'PREP.sh').read_text()
        [pin] = re.findall(r'^PREP_SHA=([0-9a-f]{64})$', text, re.M)
        self.assertEqual(pin, sha(HERE/'prep-r11.py'))

    def test_window_base_pins_the_ga_f37t_prep_outputs(self):
        base = (HERE/'window-base-r11.py').read_text()
        for digest in ('9774a5692ec5537713b212bc3fef5c88edc34c82cb6fdcc11e949e7eefc8343e',
                       '0876abb88879ce546502e34228a710a60a69a2b20f85791b3c9ce9f0ebce2451',
                       '758aa29b154babfe18468c6e2f650e04c23be18f9ba0c4a2bb4ccb087553d87f',
                       '0c071f7c97706059792bdec16ce3de952bf9114159ba493b5baad62d71e5d6d1'):
            self.assertEqual(base.count(digest), 1, digest)
        prep = Path('/var/tmp/ga-f37t-prep-20260923-r2')
        if prep.exists():
            self.assertEqual(sha(prep/'result.json'), '0c071f7c97706059792bdec16ce3de952bf9114159ba493b5baad62d71e5d6d1')
            self.assertEqual(sha(prep/'city.isolated.toml'), '9774a5692ec5537713b212bc3fef5c88edc34c82cb6fdcc11e949e7eefc8343e')
            self.assertEqual(sha(prep/'receipt.final.json'), '0876abb88879ce546502e34228a710a60a69a2b20f85791b3c9ce9f0ebce2451')

    def test_watch_captures_each_live_pane(self):
        watch = (HERE/'watch-r11.py').read_text()
        self.assertIn("'capture-pane', '-p', '-t', name]", watch)
        self.assertIn("if not isinstance(name, str) or not name:", watch)
        self.assertIn("w.save('pane-unnamed.json', unnamed)", watch)
        self.assertNotIn('send-keys', watch)
        self.assertFalse((HERE/'proof').exists())


if __name__ == '__main__':
    unittest.main()
