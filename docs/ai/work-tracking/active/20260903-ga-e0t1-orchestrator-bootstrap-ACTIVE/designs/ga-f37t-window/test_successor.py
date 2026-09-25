"""The ga-f37t package is exactly the successor derivation of the reviewed ga-4z38 r14 package."""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
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
        r2 = Path('/var/tmp/ga-f37t-integrity-20260924-r2/before-refused-observation.json')
        r3 = Path('/var/tmp/ga-f37t-integrity-20260925-r3/before-refused-observation.json')
        if not (r2.exists() and r3.exists()):
            self.skipTest('no s2 r2 and s3 r4 refused observations on this host')
        m, json = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        # The s3 r4 refusal (r3) is admitted by the full chain, and by nothing shorter.
        value = json.loads(r3.read_text())
        epoch = m.approved_epoch_image(m.approved_historical_image(prior), value['host'])
        restored = m.approved_restore_image(epoch)
        full = m.approved_coordinator_cache_image(restored)
        self.assertEqual(m.dependency_image(full), m.dependency_image(value))
        self.assertNotEqual(m.dependency_image(restored), m.dependency_image(value))
        self.assertNotEqual(m.dependency_image(m.approved_coordinator_cache_image(epoch)), m.dependency_image(value))
        no_epoch = m.approved_coordinator_cache_image(m.approved_restore_image(m.approved_historical_image(prior)))
        self.assertNotEqual(m.dependency_image(no_epoch), m.dependency_image(value))
        with self.assertRaisesRegex(RuntimeError, 'coordinator cache exception preimage'):
            m.approved_coordinator_cache_image(m.approved_restore_image(m.approved_epoch_image(prior, value['host'])))
        # The s2 r2 refusal (r2) equals the chain without the cache disposition: between r2 and r3 only the
        # pack cache .git times changed.
        older = json.loads(r2.read_text())
        before_cache = m.approved_restore_image(m.approved_epoch_image(m.approved_historical_image(prior), older['host']))
        self.assertEqual(m.dependency_image(before_cache), m.dependency_image(older))

    def test_coordinator_cache_disposition_refuses_another_preimage(self):
        m, json = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        entry = prior['cache']['inventory'][m.CACHE_DIRECTORY]
        # P6 carries the pre-historical value, so the cache disposition alone must refuse it.
        with self.assertRaisesRegex(RuntimeError, 'coordinator cache exception preimage'):
            m.approved_coordinator_cache_image(prior)
        historical = m.approved_historical_image(prior)
        image = m.approved_coordinator_cache_image(historical)
        changed = {k for k in entry if image['cache']['inventory'][m.CACHE_DIRECTORY][k] != entry[k]}
        self.assertEqual(changed, {'mtime_ns', 'ctime_ns'})
        for key in ('mtime_ns', 'ctime_ns'):
            self.assertEqual(historical['cache']['inventory'][m.CACHE_DIRECTORY][key], 1790178703592685769)
            self.assertEqual(image['cache']['inventory'][m.CACHE_DIRECTORY][key], 1790289546179167691)
            other = json.loads(json.dumps(historical))
            other['cache']['inventory'][m.CACHE_DIRECTORY][key] += 1
            with self.assertRaisesRegex(RuntimeError, 'coordinator cache exception preimage'):
                m.approved_coordinator_cache_image(other)
        # Nothing but the cache directory entry differs from the historical image.
        rest = json.loads(json.dumps(image))
        rest['cache']['inventory'][m.CACHE_DIRECTORY] = historical['cache']['inventory'][m.CACHE_DIRECTORY]
        self.assertEqual(rest, historical)

    def test_preflight_requires_no_freshen(self):
        text = (HERE/'operator'/'PREFLIGHT.sh').read_text()
        self.assertNotIn('FRESHEN_SHA', text)
        self.assertNotIn('ga-f37t-freshen-', text)
        self.assertIn('account_read_times', text)

    def read_times(self, lifecycle=False):
        m, json = self.base()
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        if lifecycle:
            (root/'suspension-rig-resume-intent.json').write_text('{}')
        m.ROOT = root
        return m, json

    def record(self, atime, mtime=100 * 10**9, ctime=100 * 10**9, inode=7):
        return dict(atime_ns=atime, mtime_ns=mtime, ctime_ns=ctime, inode=inode, mode=0o644)

    def test_read_times_admit_only_relatime_forward_changes_in_window(self):
        m, json = self.read_times()
        day = 24 * 3600 * 10**9
        window = dict(earliest_ns=10 * day, latest_ns=11 * day)
        # Old access time not newer than mtime/ctime: any forward change in the window is a read.
        a = dict(pins={'/x': dict(sha256='s', metadata=self.record(50 * 10**9))})
        z = json.loads(json.dumps(a)); z['pins']['/x']['metadata']['atime_ns'] = 10 * day + 5
        changes = m.account_read_times(a, z, window)
        self.assertEqual(z, a)
        self.assertEqual(changes, [dict(path=['pins', '/x', 'metadata'], before_ns=50 * 10**9, after_ns=10 * day + 5)])
        # Fresh old access time (newer than mtime/ctime) under 24 hours old: relatime cannot write it.
        a = dict(pins={'/x': dict(sha256='s', metadata=self.record(10 * day - 3600 * 10**9))})
        z = json.loads(json.dumps(a)); z['pins']['/x']['metadata']['atime_ns'] = 10 * day + 5
        with self.assertRaisesRegex(RuntimeError, 'relatime cannot write'):
            m.account_read_times(a, z, window)
        # At least 24 hours later: relatime writes it.
        a = dict(protected={'/p': dict(inventory={'f': self.record(9 * day)})})
        z = json.loads(json.dumps(a)); z['protected']['/p']['inventory']['f']['atime_ns'] = 10 * day
        self.assertEqual(len(m.account_read_times(a, z, window)), 1)
        self.assertEqual(z, a)
        # Backwards, or outside the window, refuses.
        for new in (40 * 10**9, 12 * day):
            a = dict(pins={'/x': dict(sha256='s', metadata=self.record(50 * 10**9))})
            z = json.loads(json.dumps(a)); z['pins']['/x']['metadata']['atime_ns'] = new
            with self.assertRaisesRegex(RuntimeError, 'outside the observed window'):
                m.account_read_times(a, z, window)

    def test_read_times_never_align_other_changes(self):
        m, json = self.read_times()
        day = 24 * 3600 * 10**9
        window = dict(earliest_ns=10 * day, latest_ns=11 * day)
        a = dict(pins={'/x': dict(sha256='s', metadata=self.record(50 * 10**9))},
                 cache=dict(inventory={'.': self.record(1)}), cache_access_clock={'atime_ns': 1})
        z = json.loads(json.dumps(a))
        z['pins']['/x']['metadata'].update(atime_ns=10 * day + 5, inode=8)
        z['cache']['inventory']['.']['atime_ns'] = 10 * day + 5
        z['cache_access_clock']['atime_ns'] = 2
        before = json.loads(json.dumps(z))
        self.assertEqual(m.account_read_times(a, z, window), [])
        # An inode change keeps its new access time, and the cache and clock keys are never touched.
        self.assertEqual(z, before)
        self.assertNotEqual(m.dependency_image(z), m.dependency_image(a))

    def test_read_times_leave_the_suspension_state_to_the_lineage(self):
        day = 24 * 3600 * 10**9
        window = dict(earliest_ns=10 * day, latest_ns=11 * day)
        for lifecycle in (False, True):
            m, json = self.read_times(lifecycle)
            path = str(m.SUSPENSION)
            a = dict(pins={path: dict(sha256='s', metadata=self.record(50 * 10**9))})
            z = json.loads(json.dumps(a)); z['pins'][path]['metadata']['atime_ns'] = 10 * day + 5
            changes = m.account_read_times(a, z, window)
            self.assertEqual(len(changes), 0 if lifecycle else 1)
            self.assertEqual(z == a, not lifecycle)

    def test_read_times_boundaries_and_scope(self):
        m, json = self.read_times()
        day = 24 * 3600 * 10**9
        window = dict(earliest_ns=0, latest_ns=100 * day)
        fresh = 10 * day  # newer than mtime and ctime (100 s)
        # Relatime writes at 24 hours in whole seconds, not at 86399 seconds.
        for delta, admitted in ((day - 10**9, False), (day, True)):
            a = dict(pins={'/x': dict(sha256='s', metadata=self.record(fresh))})
            z = json.loads(json.dumps(a)); z['pins']['/x']['metadata']['atime_ns'] = fresh + delta
            if admitted:
                self.assertEqual(len(m.account_read_times(a, z, window)), 1)
            else:
                with self.assertRaisesRegex(RuntimeError, 'relatime cannot write'):
                    m.account_read_times(a, z, window)
        # A content, mtime, ctime, size or mode change is never aligned.
        for field, value in (('sha256', 't'), ('mtime_ns', 200 * 10**9), ('ctime_ns', 200 * 10**9), ('size', 9), ('mode', 0o600)):
            a = dict(pins={'/x': dict(sha256='s', metadata=dict(self.record(50 * 10**9), size=1))})
            z = json.loads(json.dumps(a)); z['pins']['/x']['metadata']['atime_ns'] = 5 * day
            if field == 'sha256':
                z['pins']['/x']['sha256'] = value
            else:
                z['pins']['/x']['metadata'][field] = value
            kept = json.loads(json.dumps(z))
            m.account_read_times(a, z, window)
            if field == 'sha256':
                # The metadata record may align, but the content digest stays compared, so it still differs.
                self.assertEqual(z['pins']['/x']['sha256'], 't')
                self.assertNotEqual(z, a)
            else:
                self.assertEqual(z, kept, field)
        # Runtime children and cache mounts are never walked.
        a = dict(directories=dict(runtime_children={'.gc': {'f': self.record(fresh)}}, city={'.': self.record(50 * 10**9)}),
                 cache_access_mounts=[{'atime_ns': 1}])
        z = json.loads(json.dumps(a))
        z['directories']['runtime_children']['.gc']['f']['atime_ns'] = fresh + 5
        z['directories']['city']['.']['atime_ns'] = 5 * day
        z['cache_access_mounts'][0]['atime_ns'] = 2
        changes = m.account_read_times(a, z, window)
        self.assertEqual([c['path'] for c in changes], [['directories', 'city', '.']])
        self.assertEqual(z['directories']['runtime_children']['.gc']['f']['atime_ns'], fresh + 5)
        self.assertEqual(z['cache_access_mounts'][0]['atime_ns'], 2)

    def test_stable_read_times_gate(self):
        m, json = self.base()
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        path = root/'f'
        path.write_text('x')
        s = path.lstat()
        hour = 3600 * 10**9
        base = max(s.st_mtime_ns, s.st_ctime_ns)
        if not os.statvfs(path).f_flag & os.ST_RELATIME:
            self.skipTest('scratch directory is not on a relatime mount')
        # Access time newer than mtime/ctime and under 19 hours old passes.
        os.utime(path, ns=(base + hour, s.st_mtime_ns))
        t = path.lstat()
        m.stable_read_times([path], now_ns=t.st_atime_ns + 19 * hour - 1)
        with self.assertRaisesRegex(RuntimeError, 'not stable for the window'):
            m.stable_read_times([path], now_ns=t.st_atime_ns + 19 * hour)
        # Newer than mtime but not newer than ctime (utime sets ctime to now) refuses.
        os.utime(path, ns=(0, 0))
        u = path.lstat()
        os.utime(path, ns=(u.st_ctime_ns - 1, 0))
        v = path.lstat()
        if v.st_atime_ns <= v.st_ctime_ns and v.st_atime_ns > v.st_mtime_ns:
            with self.assertRaisesRegex(RuntimeError, 'not stable for the window'):
                m.stable_read_times([path], now_ns=v.st_atime_ns + hour)
        # The default path set is exactly the four objects.
        self.assertEqual(m.stable_read_paths(), (m.SUSPENSION, m.CITY, m.CITY/'.beads', m.RECEIPT.parent))
        # An access time not newer than mtime/ctime (refreshable by any read) refuses.
        os.utime(path, ns=(0, s.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError, 'not stable for the window'):
            m.stable_read_times([path], now_ns=time.time_ns())
        text = (HERE/'window-base-r11.py').read_text()
        # The gate runs before the window root is created, so a refusal consumes nothing.
        gate = "    if action=='preflight':\n        stable_read_times()\n        ROOT.mkdir(mode=0o700)\n"
        self.assertEqual(text.count(gate), 1)
        self.assertEqual(text.count('stable_read_times()'), 1)

    def test_both_preservation_layers_account_read_times(self):
        call = "    accounting['read_time_changes']=w.account_read_times(a,z,accounting['window'])\n"
        for name in ('window-r11.py', 'window-obs-r11.py'):
            text = (HERE/name).read_text()
            self.assertEqual(text.count(call), 1, name)
            self.assertLess(text.index(call), text.index("original_preservation(a,z,city_pin,receipt_pin)"), name)

    def test_restore_disposition_refuses_changed_content(self):
        if not Path('/var/tmp/ga-4z38-terminal-20260923-r1/observed-after.json').exists():
            self.skipTest('no ga-4z38 TERMINAL record on this host')
        m, json = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        prior['pins']['/home/loucmane/gascity/city/city.toml']['sha256'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'restored content differs'):
            m.approved_restore_image(prior)

    def test_restore_disposition_refuses_every_other_change(self):
        refused = Path('/var/tmp/ga-f37t-integrity-20260925-r3/before-refused-observation.json')
        if not refused.exists():
            self.skipTest('no s3 r4 refused observation on this host')
        m, json = self.base()
        prior = json.loads(m.read(m.ACCEPTED, m.ACCEPTED_SHA))
        suspension = '/home/loucmane/gascity/city/.gc/runtime/suspension-state.json'
        city = '/home/loucmane/gascity/city/city.toml'
        # A suspension state other than the recorded one refuses.
        original = m.RESTORED_PINS[suspension]
        m.RESTORED_PINS[suspension] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'restored suspension state differs'):
            m.approved_restore_image(prior)
        m.RESTORED_PINS[suspension] = original
        # A missing pin refuses.
        missing = json.loads(json.dumps(prior))
        del missing['pins'][city]
        with self.assertRaisesRegex(RuntimeError, 'restore disposition pin set'):
            m.approved_restore_image(missing)
        # A changed pin shape refuses.
        shaped = json.loads(json.dumps(prior))
        shaped['pins'][city]['extra'] = 1
        with self.assertRaisesRegex(RuntimeError, 'restore pin shape drift'):
            m.approved_restore_image(shaped)
        # A restored file with any other inode, and any other pin that drifts, still differ.
        value = json.loads(refused.read_text())
        chained = m.approved_coordinator_cache_image(
            m.approved_restore_image(m.approved_epoch_image(m.approved_historical_image(prior), value['host'])))
        self.assertEqual(m.dependency_image(chained), m.dependency_image(value))
        for path in (city, next(p for p in sorted(value['pins']) if p not in m.RESTORED_PINS)):
            drifted = json.loads(json.dumps(value))
            drifted['pins'][path]['metadata']['inode'] += 1
            self.assertNotEqual(m.dependency_image(chained), m.dependency_image(drifted), path)

    def test_observers_pin_the_window_observer(self):
        obs = sha(HERE/'window-obs-r11.py')
        for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
            [pin] = re.findall(r"^W_SHA='([0-9a-f]{64})'$", (HERE/name).read_text(), re.M)
            self.assertEqual(pin, obs, name)

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
