"""The ga-gegx package is exactly the successor derivation of the reviewed ga-f37t s7 package."""
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
           'ga-y49e, ga-4z38 and ga-f37t attempts', "after the ga-f37t window's silent start"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_files():
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            yield path


NUDGE_ENV = {'GC_NUDGE_ON_ROUTE_LOOKBACK': '45m', 'GC_NUDGE_ON_ROUTE_RETENTION': '2h'}


def load_file(name, path):
    spec = __import__('importlib.util').util.spec_from_file_location(name, path)
    module = __import__('importlib.util').util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prep_constant(prep, name):
    import ast
    [value] = [node.value for node in ast.parse(prep).body
               if isinstance(node, ast.Assign) and [t.id for t in node.targets] == [name]]
    return ast.literal_eval(value)


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
        parsed_skip = __import__('tomllib').loads(text)['orders']['skip']
        self.assertNotIn('nudge-on-route', parsed_skip)
        self.assertIn('nudge-mail-sweep', parsed_skip)
        self.assertEqual(len(parsed_skip), 33)
        self.assertIn('work_dir = "/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles"', text)
        parsed = __import__('tomllib').loads(text)
        self.assertEqual(parsed['orders']['overrides'], [dict(name='nudge-on-route', env=NUDGE_ENV)])
        self.assertIn(prep_constant(prep, 'NUDGE_OVERRIDE'), text)
        # The r4 PREP overlay was built from the live inputs; r5 adds only the override block.
        r4 = Path('/var/tmp/ga-gegx-prep-20260923-r2/city.isolated.toml')
        if r4.exists():
            raw = r4.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),
                             '228e5be706ba7ca5d40de9a01b48b26267e2c09f7f7507080203a966e8402b4e')
            self.assertEqual(g.insert_override(raw.decode()).encode(), overlay)
        [pinned] = re.findall(r'^PREP_SHA=([0-9a-f]{64})$', (HERE/'operator'/'PREP.sh').read_text(), re.M)
        self.assertEqual(pinned, sha(HERE/'prep-r11.py'))

    def test_prep_requires_exactly_nudge_on_route_to_remain(self):
        prep = (HERE/'prep-r11.py').read_text()
        self.assertNotIn("empty['orders'] == []", prep)
        self.assertIn("    kept = [o for o in orders['orders'] if o['name'] == 'nudge-on-route']\n", prep)
        self.assertIn("    assert len(kept) == 1 and empty['orders'] == [dict(kept[0], env=NUDGE_ENV)] \\\n"
                      "        and empty['summary']['count'] == 1, 'isolated orders'\n", prep)
        self.assertIn("effective_orders=1, effective_order_names=['nudge-on-route'], nudge_env=NUDGE_ENV", prep)
        self.assertNotIn('effective_orders=0', prep)
        baseline = Path('/var/tmp/ga-f37t-prep-20260923-r2/orders.baseline.json')
        if baseline.exists():
            orders = json.loads(baseline.read_text())['orders']
            kept = [o for o in orders if o['name'] == 'nudge-on-route']
            self.assertEqual(len(kept), 1)
            self.assertTrue(kept[0]['enabled'])
            self.assertEqual((kept[0]['trigger'], kept[0]['on'], kept[0]['type']), ('event', 'bead.updated', 'exec'))

    def test_prep_gives_nudge_on_route_a_long_lookback(self):
        prep = (HERE/'prep-r11.py').read_text()
        self.assertEqual(prep_constant(prep, 'NUDGE_ENV'), NUDGE_ENV)
        self.assertIn("parts = [HEADER, '[orders]\\n', 'skip = ' + json.dumps(names) + '\\n', NUDGE_OVERRIDE]", prep)
        self.assertIn("    expected['config']['Orders']['Overrides'] = [dict(\n", prep)
        self.assertIn("Idempotent=None, Env=NUDGE_ENV)]", prep)
        self.assertNotIn('unchanged except for WORK and HEADER', prep)
        self.assertIn("ROOT = Path('/var/tmp/ga-gegx-prep-20260925-r3')", prep)
        self.assertIn('OUT=/var/tmp/ga-gegx-prep-20260925-r3\n', (HERE/'operator'/'PREP.sh').read_text())
        self.assertIn("PREP = Path('/var/tmp/ga-gegx-prep-20260925-r3')", (HERE/'window-base-r11.py').read_text())
        # The lookback is not a controller-reserved exec env key (Core internal/orders/env.go).
        self.assertTrue(all(key.startswith('GC_NUDGE_ON_ROUTE_') for key in NUDGE_ENV))

    def test_window_base_pins_the_prep_r5_outputs(self):
        base = (HERE/'window-base-r11.py').read_text()
        root = Path('/var/tmp/ga-gegx-prep-20260925-r3')
        self.assertIn("PREP = Path('/var/tmp/ga-gegx-prep-20260925-r3')", base)
        for old in ('9774a569', '0876abb8', '758aa29b', '0c071f7c'):
            self.assertNotIn(old, base)
        if not (root/'result.json').exists():
            self.skipTest('NOT PROVEN on this host: no PREP r5 evidence')
        result = json.loads((root/'result.json').read_text())
        self.assertTrue(result['ok'])
        self.assertEqual(result['nudge_env'], NUDGE_ENV)
        self.assertIn("read(PREP/'result.json', '%s')" % sha(root/'result.json'), base)
        self.assertIn("'%s')\nRECEIPT_SHA" % result['city_after_sha256'], base)
        self.assertEqual(result['city_after_sha256'], sha(root/'city.isolated.toml'))
        self.assertIn("'%s')\nREVISION" % result['receipt_after_sha256'], base)
        self.assertEqual(result['receipt_after_sha256'], sha(root/'receipt.final.json'))
        self.assertIn("'%s')\nINPUT" % result['revision_after'], base)

    def test_watch_records_nudge_evidence_read_only(self):
        watch = (HERE/'watch-r11.py').read_text()
        self.assertIn("ORDER_STATE = Path('/home/loucmane/gascity/city/.gc/runtime/packs/core/nudge-on-route-state.json')", watch)
        self.assertIn("NUDGE_QUEUE = Path('/home/loucmane/gascity/city/.gc/nudges/state.json')", watch)
        self.assertLess(watch.index("w.save('pane-unnamed.json', unnamed)"), watch.index('nudge = nudge_evidence()'))
        m = load_file('watch_s2', HERE/'watch-r11.py')
        self.assertEqual(m.ORDER_KEY, 'ga-gegx|gascity/gc.implementation-worker')
        self.assertEqual(m.EVIDENCE_LIMIT, 1 << 20)
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            m.ORDER_STATE = scratch/'order.json'
            m.NUDGE_QUEUE = scratch/'queue.json'
            absent = m.nudge_evidence()
            self.assertEqual((absent['order_state'], absent['queue'], absent['queued']), ('absent', 'absent', None))
            m.ORDER_STATE.write_text(json.dumps({m.ORDER_KEY: '2026-09-25T12:00:00Z', 'other|x': 'y'}))
            m.NUDGE_QUEUE.write_text(json.dumps(dict(
                pending=[dict(id='n1', agent='gascity/gc.implementation-worker', session_id='ci-x',
                              source='session', message='check for assigned work')],
                in_flight=[], dead=[dict(id='d1'), dict(id='d2')])))
            found = m.nudge_evidence()
            self.assertEqual((found['order_state'], found['queue'], found['order_pair']),
                             ('ok', 'ok', '2026-09-25T12:00:00Z'))
            self.assertEqual((found['queued'], found['dead'], found['pending'][0]['id']), (1, 2, 'n1'))
            # A second link (what a racing rename looks like to the open descriptor) is recorded, not raised.
            os.link(m.ORDER_STATE, scratch/'order.link')
            linked = m.nudge_evidence()
            self.assertTrue(linked['order_state'].startswith('RuntimeError: worker file shape or size'))
            self.assertIsNone(linked['order_pair'])
            os.unlink(scratch/'order.link')
            # Core's prune failure can leave just a newline; a bad or odd queue is recorded too.
            m.ORDER_STATE.write_text('\n')
            m.NUDGE_QUEUE.write_text(json.dumps(dict(pending=[1])))
            odd = m.nudge_evidence()
            self.assertTrue(odd['order_state'].startswith('JSONDecodeError'))
            self.assertTrue(odd['queue'].startswith('unexpected shape'))
            self.assertEqual((odd['queued'], odd['pending']), (None, []))
            m.NUDGE_QUEUE.write_text('[]')
            self.assertEqual(m.nudge_evidence()['queue'], 'unexpected shape: list')
            m.NUDGE_QUEUE.write_bytes(b'{' + b' ' * (1 << 20) + b'}')
            self.assertTrue(m.nudge_evidence()['queue'].startswith('RuntimeError: worker file shape or size'))

    def test_barrier_retries_a_runtime_probe_partial_status(self):
        m = load_file('base_s2r2', HERE/'window-base-r11.py')
        if not Path(m.SUSPENSION).exists():
            self.skipTest('NOT PROVEN on this host: no suspension state path for statvfs')
        rigs = ('gascity', 'gas-city-template', 'hpfetcher', 'blog')
        full = dict(ok=True, city_path=str(m.CITY), running=True, controller=dict(running=True, pid=2331),
                    rigs=[dict(name=n, suspended=True) for n in rigs], suspended=True, agents=[],
                    summary=dict(running_agents=0), health=dict(signals=['city_suspended', 'no_agents_running']))
        partial = dict(full, partial=True, partial_errors=list(m.RUNTIME_PROBE_PARTIAL))
        expected = dict(city=dict(suspended=True), rigs={n: dict(suspended=True) for n in rigs})

        def run(action, statuses):
            clock = [0.0]
            saved = {}
            now = __import__('time').time_ns()
            record = dict(pin=dict(sha256='x', metadata=dict(atime_ns=now, mtime_ns=now - 10, ctime_ns=now - 10)),
                          raw='{}')
            feed = iter(statuses)

            def phase(name, argv, b, owned, timeout=None):
                clock[0] += 9
                return dict(stdout=json.dumps(next(feed)))
            m.phase = phase
            m.module = lambda path, pin: types.SimpleNamespace(image=lambda first: expected)
            m.suspension_record = lambda o: json.loads(json.dumps(record))
            m.save = lambda name, value: saved.__setitem__(name, value)
            m.active_epoch = lambda o: None
            m.time = types.SimpleNamespace(monotonic=lambda: clock[0], time_ns=lambda: now,
                                           sleep=lambda s: clock.__setitem__(0, clock[0] + s))
            return m.observed_suspension_endpoint(action, None, None, None), saved

        # The ga-f37t CONTAIN-1 case: one probe-partial observation, then a complete one.
        endpoint, saved = run('rig-suspend', [partial, full])
        self.assertEqual(endpoint['pin']['sha256'], 'x')
        self.assertIn('suspension-rig-suspend-barrier-partial-0.json', saved)
        self.assertNotIn('suspension-rig-suspend-partial-accepted.json', saved)
        # A suspend that only ever sees the probe partial accepts it in the last PROBE_LATE seconds.
        _, saved = run('city-suspend', [partial] * 20)
        accepted = saved['suspension-city-suspend-partial-accepted.json']
        self.assertTrue(saved['suspension-city-suspend-barrier-partial-%d.json' % accepted['index']]['late'])
        self.assertFalse(saved['suspension-city-suspend-barrier-partial-0.json']['late'])
        # A resume never accepts it, and any other partial status still refuses at once.
        with self.assertRaisesRegex(RuntimeError, 'suspension observation timeout'):
            run('city-resume', [partial] * 20)
        # A late probe partial is still held to every other check.
        stray = dict(partial, agents=[dict(running=True, qualified_name='gascity/gc.other')],
                     summary=dict(running_agents=1), health=dict(signals=['city_suspended']))
        with self.assertRaisesRegex(RuntimeError, 'unexpected live worker'):
            run('city-suspend', [stray] * 20)
        signal = dict(partial, health=dict(signals=['city_suspended', 'something_else']))
        with self.assertRaisesRegex(RuntimeError, 'unexpected city health signal'):
            run('city-suspend', [signal] * 20)
        other = dict(full, partial=True, partial_errors=['store probe incomplete'])
        with self.assertRaisesRegex(RuntimeError, 'incomplete/wrong-controller'):
            run('rig-suspend', [other])
        with self.assertRaisesRegex(RuntimeError, 'incomplete/wrong-controller'):
            m.suspension_status_matches(partial, expected)
        self.assertTrue(m.suspension_status_matches(partial, expected, True))
        evidence = Path('/var/tmp/ga-f37t-window-20260925-r2/rig-suspend-status-0-phase.json')
        if evidence.exists():
            observed = json.loads(json.loads(evidence.read_text())['stdout'])
            self.assertTrue(m.runtime_probe_partial(observed))
            # The recorded ga-f37t status passes every other check, so CONTAIN can finish on it.
            self.assertTrue(m.suspension_status_matches(observed, expected, True))
        self.assertNotIn('cgroup', (HERE/'window-base-r11.py').read_text())

    def test_reconcile_wrapper_checks_the_root_it_writes(self):
        wrapper = (HERE/'operator'/'RECONCILE.sh').read_text()
        [root] = re.findall(r"^ROOT=Path\('([^']+)'\)$", (HERE/'reconcile-predecessor-r3.py').read_text(), re.M)
        self.assertEqual(root, '/var/tmp/ga-gegx-reconcile-20260925-r1')
        self.assertEqual(set(re.findall(r'/var/tmp/ga-gegx-reconcile-[0-9]+-r[0-9]+', wrapper)), {root})
        self.assertNotIn('ga-4z38', wrapper)

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
                     '/var/tmp/ga-gegx-prep-20260925-r3', '/var/tmp/ga-gegx-bind-20260923-r1',
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
