"""The ga-nibd package is exactly the successor derivation of the reviewed ga-gegx s3 package."""
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
OWN = {'README.md', 'test_successor.py', 'generators/make_successor.py', 'generators/kick-r1.template'}
RECOVER3 = Path('/var/tmp/ga-gegx-recover-20260925-r3/result.json')
# ga-gegx may appear only in these exact places: history comments, its RECOVER-3 root, RECONCILE's held task.
ALLOWED = ['# ga-gegx s2: ', '# ga-gegx s2 r2: ', 'r4 (ga-gegx, ', 'r5 (ga-gegx)', '(ga-gegx r4)',
           '# ga-gegx r5: ', '(ga-gegx) in keeping', '# ga-gegx: keep Core', '# ga-gegx: every order',
           '# ga-gegx: the visible pane', '/var/tmp/ga-gegx-recover-20260925-r3',
           'the ga-gegx window stopped in RESTORE', 'and the reviewed ga-gegx\n    # RECOVER-3 job',
           'The ga-gegx RESTORE refused on exactly that', 'the ga-gegx prep, rebound to the ga-nibd worktree',
           'The overlay is the ga-gegx r5 overlay', 'It is the reviewed ga-gegx prep, rebound to ga-nibd',
           'ga-f37t and ga-gegx attempts', '(ga-4z38, ga-f37t, ga-gegx)']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_files():
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            yield path


def load_file(name, path):
    spec = __import__('importlib.util').util.spec_from_file_location(name, path)
    module = __import__('importlib.util').util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_ga_gegx_appears_only_where_intended(self):
        for path in package_files():
            rel = str(path.relative_to(HERE))
            if rel in OWN or rel == 'reconcile-predecessor-r3.py':
                continue
            text = path.read_text()
            for phrase in ALLOWED:
                text = text.replace(phrase, '')
            self.assertNotIn('ga-gegx', text, rel)

    def test_reconcile_holds_ga_gegx(self):
        text = (HERE/'reconcile-predecessor-r3.py').read_text()
        self.assertIn("before=bead('ga-gegx');other=bead('ga-f37t');new=bead('ga-nibd')", text)
        self.assertIn("attempt['session_id']=='ci-ki0gd'", text)
        self.assertIn("'/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles'", text)
        self.assertIn("{v['id'] for v in prior}=={'ga-gegx'}", text)
        self.assertIn("ROOT=Path('/var/tmp/ga-nibd-reconcile-20260925-r1')", text)
        self.assertNotIn('ci-yauk5', text)
        self.assertNotIn('ga-4z38', text)
        wrapper = (HERE/'operator'/'RECONCILE.sh').read_text()
        self.assertEqual(set(re.findall(r'/var/tmp/ga-nibd-reconcile-[0-9]+-r[0-9]+', wrapper)),
                         {'/var/tmp/ga-nibd-reconcile-20260925-r1'})

    def test_the_worker_binds_the_fresh_worktree(self):
        self.assertEqual(self.base().WORK, Path('/home/loucmane/gascity-core-worktrees/ga-nibd-typed-route-cycles'))
        self.assertIn("BEAD='ga-nibd'", (HERE/'bind-task-r3.py').read_text())
        [bind] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", (HERE/'route-task-r5.py').read_text(), re.M)
        self.assertEqual(bind, sha(HERE/'bind-task-r3.py'))

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
        for name in ('bind-task-r3.py', 'watch-r11.py', 'release-r11.py', 'close-r11.py', 'hold-r11.py',
                     'window-r11.py', 'window-obs-r11.py', 'kick-r1.py'):
            self.assertIn(base, (HERE/name).read_text(), name)
        window = sha(HERE/'window-r11.py')
        for name in ('route-task-r5.py', 'restore-admission-r3.py', 'observe-terminal-r11.py'):
            self.assertIn(window, (HERE/name).read_text(), name)
        self.assertIn(sha(HERE/'release-r11.py'), (HERE/'kick-r1.py').read_text())

    def test_prep_derives_the_overlay_from_the_ga_gegx_r5_overlay(self):
        prep = (HERE/'prep-r11.py').read_text()
        [pin] = re.findall(r"^OVERLAY_SHA = '([0-9a-f]{64})'$", prep, re.M)
        self.assertIn("ROOT = Path('/var/tmp/ga-nibd-prep-20260925-r1')", prep)
        self.assertIn('OUT=/var/tmp/ga-nibd-prep-20260925-r1\n', (HERE/'operator'/'PREP.sh').read_text())
        g = load_file('gen', HERE/'generators'/'make_successor.py')
        if not g.PREP_OVERLAY.exists():
            self.skipTest('NOT PROVEN on this host: no ga-gegx PREP r5 overlay')
        overlay = g.successor_overlay()
        self.assertEqual(pin, hashlib.sha256(overlay).hexdigest())
        old = g.PREP_OVERLAY.read_text().splitlines()
        new = overlay.decode().splitlines()
        self.assertEqual(len(old), len(new))
        self.assertEqual(sum(a != b for a, b in zip(old, new)), 2)
        self.assertIn('work_dir = "/home/loucmane/gascity-core-worktrees/ga-nibd-typed-route-cycles"', overlay.decode())

    def test_observe_binds_the_recover3_result(self):
        observe = (HERE/'observe-integrity-r11.py').read_text()
        self.assertIn("RECOVER_ROOT='/var/tmp/ga-gegx-recover-20260925-r3'", observe)
        self.assertIn('    w.RECOVERY=(RECOVER_ROOT,RECOVER_SHA)\n', observe)
        [pin] = re.findall(r"^RECOVER_SHA='([0-9a-f]{64})'$", observe, re.M)
        if not RECOVER3.exists():
            self.skipTest('NOT PROVEN on this host: no ga-gegx RECOVER-3 record')
        self.assertEqual(pin, sha(RECOVER3))

    def test_recovery_disposition_admits_the_recover3_city(self):
        if not RECOVER3.exists():
            self.skipTest('NOT PROVEN on this host: no ga-gegx RECOVER-3 record')
        m = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        chained = m.approved_coordinator_cache_image(m.approved_restore_image(
            m.approved_epoch_image(m.approved_historical_image(prior), prior['host'])))
        value = m.approved_recovery_image(chained, str(RECOVER3.parent), sha(RECOVER3))
        recorded = json.loads(RECOVER3.read_text())
        city, receipt, suspension = str(m.CITY/'city.toml'), str(m.RECEIPT), m.SUSPENSION
        self.assertEqual(value['pins'][city], recorded['city_pin'])
        self.assertEqual(value['pins'][receipt], recorded['receipt_pin'])
        self.assertEqual(value['pins'][suspension], recorded['suspension']['pin'])
        rest = json.loads(json.dumps(value))
        for path in (city, receipt, suspension):
            rest['pins'][path] = chained['pins'][path]
        self.assertEqual(rest, chained)
        with self.assertRaises(RuntimeError):
            m.approved_recovery_image(chained, str(RECOVER3.parent), '0' * 64)
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        root.chmod(0o700)
        for change, message in ((lambda r: r['receipt_pin'].update(sha256='0' * 64), 'recovered content differs'),
                                (lambda r: r.update(worker_launched=True), 'recovery result')):
            changed = json.loads(json.dumps(recorded))
            change(changed)
            (root/'result.json').unlink(missing_ok=True)
            (root/'result.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(RuntimeError, message):
                m.approved_recovery_image(chained, str(root), sha(root/'result.json'))

    def test_kick_checks_before_its_one_nudge(self):
        m = load_file('kick', HERE/'kick-r1.py')
        self.assertEqual(m.TASK, 'ga-nibd')
        self.assertEqual(m.WINDOW, self.base().ROOT)
        self.assertFalse(re.search(r'\d', m.MESSAGE), 'a digit could select a numbered menu option')
        self.assertFalse(m.MESSAGE.startswith(('!', '/', '#')))
        self.assertIn('/home/loucmane/gascity/bin/gc hook --claim --json', m.MESSAGE)
        self.assertIn('/home/loucmane/gascity/bin/bd show ga-nibd --json', m.MESSAGE)
        routed = dict(status='open', assignee=None, metadata={'gc.routed_to': m.TEMPLATE})
        self.assertTrue(m.unclaimed(routed))
        for change in (dict(status='in_progress'), dict(assignee='ci-x'), dict(metadata={}),
                       dict(metadata={'gc.routed_to': 'other'})):
            self.assertFalse(m.unclaimed(dict(routed, **change)), change)
        text = (HERE/'kick-r1.py').read_text()
        order = [text.index(s) for s in ("'city is not resumed'", "'exactly one active worker session'",
                                          "'the task is already claimed or not routed; no kick'",
                                          "w.require(not r.dialog_showing(pane)",
                                          "w.require(prompt_ready(pane)",
                                          "'--delivery', 'immediate'")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("'update'", text)
        slots = sorted((HERE/'operator').glob('KICK-*.sh'))
        self.assertEqual([p.stem for p in slots], ['KICK-1', 'KICK-2', 'KICK-3'])
        self.assertEqual(len({re.sub(r'(KICK-|kick-|Slot )\d', r'\1N', p.read_text()) for p in slots}), 1)
        self.assertIn('step budget "$C/budget-r11.py" "$BUDGET_SHA" 60\n', slots[0].read_text())
        # A ready prompt, as the ga-gegx WATCH captured it, and panes that are not ready.
        ready = '\u2500' * 20 + '\n\u276f\u00a0\n' + '\u2500' * 20 + "\n  \u23f5\u23f5 don't ask on\n"
        self.assertTrue(m.prompt_ready(ready))
        self.assertFalse(m.prompt_ready('\u276f 1. Yes, I trust this folder\n'))
        self.assertFalse(m.prompt_ready('\u276f check for assigned work\n'))
        self.assertFalse(m.prompt_ready('Loading...\n'))
        capture = Path('/var/tmp/ga-gegx-watch-20260925T120509Z/pane-0-phase.json')
        if capture.exists():
            self.assertTrue(m.prompt_ready(json.loads(capture.read_text())['stdout']))

    def test_restore_waits_out_the_auto_trace_arm(self):
        g = load_file('gen2', HERE/'generators'/'make_successor.py')
        window = (HERE/'window-r11.py').read_text()
        self.assertIn(g.RELOAD_NEW, window)
        self.assertNotIn(g.RELOAD_OLD, window)
        self.assertIn('step budget "$C/budget-r11.py" "$BUDGET_SHA" 45\n', (HERE/'operator'/'RESTORE.sh').read_text())
        # The predicate, evaluated on the ga-gegx RESTORE's own refused read: armed, so waited out.
        predicate = '(' + re.search(r"            armed=\((.*?)\)\n", window, re.S).group(1) + ')'
        refused = Path('/var/tmp/ga-gegx-window-20260925-r2/restore-reload-trace-0-phase.json')
        if not refused.exists():
            self.skipTest('NOT PROVEN on this host: no ga-gegx RESTORE record')
        rows = json.loads(json.loads(refused.read_text())['stdout'])['records']
        newest = max(rows, key=lambda r: r['seq'])
        fields = newest['fields']
        self.assertTrue(eval(predicate, {'fields': fields}))
        self.assertFalse(eval(predicate, {'fields': dict(fields, decision_counts={'start': 1})}))
        self.assertFalse(eval(predicate, {'fields': dict(fields, templates_touched=['other'])}))

    def test_window_base_pins_the_prep_r6_outputs(self):
        base = (HERE/'window-base-r11.py').read_text()
        for old in ('e6e24bd7', '9c5765b8', '56f39eb2', '22e16a70'):
            self.assertNotIn(old, base)
        root = Path('/var/tmp/ga-nibd-prep-20260925-r1')
        if not (root/'result.json').exists():
            self.skipTest('NOT PROVEN on this host: no ga-nibd PREP r6 evidence')
        result = json.loads((root/'result.json').read_text())
        self.assertTrue(result['ok'])
        self.assertIn("read(PREP/'result.json', '%s')" % sha(root/'result.json'), base)
        self.assertIn("'%s')\nRECEIPT_SHA" % result['city_after_sha256'], base)
        self.assertEqual(result['city_after_sha256'], sha(root/'city.isolated.toml'))
        self.assertIn("'%s')\nREVISION" % result['receipt_after_sha256'], base)
        self.assertEqual(result['receipt_after_sha256'], sha(root/'receipt.final.json'))
        self.assertIn("'%s')\nINPUT" % result['revision_after'], base)

    def test_fresh_roots_and_dropped_files(self):
        for name in ('recover-restore-r1.py', 'operator/RECOVER-3.sh'):
            self.assertFalse((HERE/name).exists(), name)
        code = ''.join(p.read_text() for p in package_files() if p.suffix in ('.py', '.sh'))
        for path in ('/var/tmp/ga-nibd-window-20260925-r2', '/var/tmp/ga-nibd-prep-20260925-r1',
                     '/var/tmp/ga-nibd-reconcile-20260925-r1'):
            self.assertIn(path, code)

    def test_twelve_watch_slots_differ_only_in_slot(self):
        slots = sorted((HERE/'operator').glob('WATCH-*.sh'), key=lambda p: int(p.stem.split('-')[1]))
        self.assertEqual([p.stem for p in slots], ['WATCH-%d' % n for n in range(1, 13)])
        normal = {re.sub(r'(WATCH-|watch-|Slot )\d+', r'\1N', p.read_text()) for p in slots}
        self.assertEqual(len(normal), 1)


if __name__ == '__main__':
    unittest.main()
