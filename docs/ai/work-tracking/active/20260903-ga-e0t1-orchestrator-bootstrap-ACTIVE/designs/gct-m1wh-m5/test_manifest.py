"""Offline M5 data-binding tests. Synthetic closure and parents; never an execution manifest.

The synthetic closure is the frozen M3 baseline overlaid with the expected
successor pins. Tree digests are placeholders. Only the frozen capture can
supply real ones, and build() refuses until that capture is pinned. After the
capture, test_build_against_frozen_baseline builds from the real file.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import types
import unittest

HERE = Path(__file__).parent


def load(name, filename):
    path = HERE/filename
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


m = load('candidate_under_test', 'manifest_candidate.py')
derive = load('derive_under_test', 'derive_expected.py')
old_bytes = (Path(m.OLD_ROOT)/'q/manifest.json').read_bytes()
old = json.loads(old_bytes)
M3_BASELINE = Path('/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922/'
                   'gct-m1wh-metadata-20260922-r3/baseline.json')
m3_raw = M3_BASELINE.read_bytes()
assert hashlib.sha256(m3_raw).hexdigest() == 'c411dc6072d3a5d29c79e70883c50c13503014fedcc819a3b6778aae2979daf6'
STAGED_CLI = Path('/home/loucmane/.local/share/gas-city-staging/gct-er3h/claude-2.1.280')
INPUTS = Path(m.O + '/reports/m5-inputs')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def hexd(label):
    return sha(label.encode())


def predecessor(live, backup, digest):
    """Live predecessor bytes before the live step, its preserved copy after."""
    raw = Path(live).read_bytes()
    if sha(raw) != digest:
        raw = Path(backup).read_bytes()
    assert sha(raw) == digest
    return raw


def synthetic_closure():
    closure = copy.deepcopy(json.loads(m3_raw)['closure'])
    pins, trees, links = closure['pins'], closure['trees'], closure['links']
    for path, _, after in m.CHANGED_INPUTS:
        pins[path] = dict(pins[path], sha256=after)
    pins[m.CITY_SOURCE] = dict(sha256=m.CITY_NEW, mode=0o644, uid=1000, gid=1000, size=1)
    for relative, digest, mode in m.AUTH_INPUTS:
        pins[m.AUTHORITY+'/'+relative] = dict(sha256=digest, mode=mode, uid=1000, gid=1000, size=1)
    for path in m.REPINNED_TREES:
        trees[path] = dict(trees[path], sha256=hexd('repinned:'+path))
    for relative in m.AUTH_TREES:
        trees[m.AUTHORITY+'/'+relative] = dict(sha256=hexd('tree:'+relative), entries=1, file_bytes=1)
    for relative, target in m.AUTH_LINKS:
        links[m.AUTHORITY+'/'+relative] = target
    return closure


closure = synthetic_closure()
parents = [copy.deepcopy(old['metadata']['parents'][0])]
for index, name in enumerate(('b', 't')):
    parents.append(dict(path=m.ROOT+'/'+name, device=2096, inode=91000001+index,
        uid=1000, gid=1000, mode=0o700, entries=[]))


def build(**kw):
    args = dict(old=old, closure=closure, host=closure['host'], parents=parents,
                transaction='1'*64, attempt='2'*64)
    args.update(kw)
    return m.assemble(**args)


def git(*args):
    return subprocess.run(['/usr/bin/git', '-C', m.TEMPLATE, *args], capture_output=True, check=True).stdout


def tracked():
    rows = {}
    for line in git('ls-tree', '-r', '--full-tree', m.TEMPLATE_COMMIT).decode().splitlines():
        meta, path = line.split('\t', 1)
        mode, _, obj = meta.split()
        rows[path] = (mode, obj)
    return rows


def blob(path, commit=None):
    return git('show', (commit or m.TEMPLATE_COMMIT)+':'+path)


def variant(mutate):
    value = copy.deepcopy(old)
    mutate(value)
    return m.b.finalized(value)


class SuccessorTests(unittest.TestCase):
    def refuses(self, reason, **kw):
        with self.assertRaisesRegex(Exception, reason):
            build(**kw)

    def test_predecessor_is_installed_r9(self):
        self.assertEqual(sha(old_bytes), m.OLD_MANIFEST_SHA)
        self.assertEqual(sha(Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json').read_bytes()),
                         m.OLD_MANIFEST_SHA)

    def test_native_successor_fields(self):
        new, _ = build()
        self.assertEqual(new['previous_sha256'], old['core']['sha256'])
        self.assertEqual(new['activation']['previous_commit'], old['activation']['expected_commit'])
        self.assertEqual(new['activation']['previous_version'], old['activation']['expected_version'])
        self.assertEqual(new['backup_path'], '/var/tmp/ga-mutg-custody-build-20260920/gc-b')
        for key in ('core',):
            self.assertEqual(new[key], old[key])
        for key in ('protected_trees', 'runtime', 'writer', 'absent', 'cache_sha256', 'imports_sha256',
                    'gc_home', 'host', 'namespaces'):
            self.assertEqual(new['metadata'][key], old['metadata'][key], key)
        self.assertEqual(m.b.finalized(new), new)
        self.assertEqual(build(), build())

    def test_exact_coverage_map(self):
        _, report = build()
        cm = report['coverage_map']
        auth_inputs = {m.AUTHORITY+'/'+r for r, _, _ in m.AUTH_INPUTS}
        self.assertEqual(set(cm['inputs']['added']),
                         auth_inputs | {m.CITY_SOURCE, '/var/tmp/ga-mutg-custody-build-20260920/gc-b'})
        self.assertEqual(len(cm['inputs']['removed']), 57)
        self.assertTrue(all(x.startswith(m.TEST_PREFIX) for x in cm['inputs']['removed']))
        self.assertEqual(set(cm['inputs']['changed']), {p for p, _, _ in m.CHANGED_INPUTS})
        for path, before, after in m.CHANGED_INPUTS:
            row = cm['inputs']['changed'][path]
            self.assertEqual((row['before']['sha256'], row['after']['sha256']), (before, after))
            self.assertEqual({k: v for k, v in row['before'].items() if k != 'sha256'},
                             {k: v for k, v in row['after'].items() if k != 'sha256'})
        self.assertEqual(set(cm['trees']['added']), {m.AUTHORITY+'/'+r for r in m.AUTH_TREES})
        self.assertEqual(cm['trees']['removed'], [])
        self.assertEqual(set(cm['trees']['changed']), set(m.REPINNED_TREES))
        self.assertEqual(set(cm['links']['added']), {m.AUTHORITY+'/'+r for r, _ in m.AUTH_LINKS})
        self.assertEqual((cm['links']['removed'], cm['links']['changed']), ([], {}))
        self.assertEqual((cm['repositories']['added'], cm['repositories']['removed'],
                          cm['repositories']['changed']), ([m.AUTHORITY_NAME], [], {}))
        self.assertEqual(set(cm['providers']['changed']), {'claude-native', 'claude'})
        self.assertEqual((cm['providers']['added'], cm['providers']['removed']), ([], []))
        self.assertEqual(set(cm['files']['changed']), {'rig-permissions.toml', 'rig-permissions.json'})
        self.assertEqual(set(cm['managed_files']['changed']), {'city-config'})
        config = cm['managed_files']['changed']['city-config']
        self.assertEqual({k for k in config['before'] if config['before'][k] != config['after'][k]},
                         {'sha256', 'source'})
        self.assertEqual(config['after']['previous_sha256'], m.CITY_OLD)
        self.assertEqual({row['field'] for row in cm['scalars']}, {
            '/release_id', '/manifest_sha256', '/previous_sha256', '/backup_path', '/activation',
            '/previous_metadata', '/metadata/transaction', '/metadata/attempt',
            '/metadata/evidence', '/metadata/parents', '/metadata/preimages'})

    def test_frame_margin(self):
        _, report = build()
        self.assertLessEqual(report['frame']['upper_bound_bytes'], 131072)
        self.assertGreater(report['frame']['remaining_bytes'], 2048)

    def test_authority_coverage_is_complete_and_exact(self):
        rows = tracked()
        self.assertEqual(len(rows), 277)
        inputs = {r: (d, mode) for r, d, mode in m.AUTH_INPUTS}
        links = dict(m.AUTH_LINKS)
        trees = set(m.AUTH_TREES)
        covered = {}
        for path, (mode, _) in rows.items():
            owners = [t for t in trees if path.startswith(t + '/')]
            if mode == '120000':
                self.assertIn(path, links)
                self.assertEqual(blob(path).decode(), links[path])
                self.assertEqual(owners, [], 'link below a tree: ' + path)
                covered[path] = 'link'
            elif path in inputs:
                self.assertEqual(owners, [])
                self.assertEqual(sha(blob(path)), inputs[path][0])
                self.assertEqual(inputs[path][1], 493 if mode == '100755' else 420)
                covered[path] = 'input'
            else:
                self.assertEqual(len(owners), 1, 'uncovered or doubly covered: ' + path)
                covered[path] = 'tree'
        self.assertEqual(set(covered), set(rows))
        self.assertEqual(set(inputs) - set(rows), {'.git'})
        for tree in trees:
            self.assertTrue(any(p.startswith(tree + '/') for p in rows), 'empty tree: ' + tree)
            self.assertFalse(any(t != tree and t.startswith(tree + '/') for t in trees), 'nested trees')
            self.assertFalse(any(l.startswith(tree + '/') or tree.startswith(l + '/') for l in links))
        for path, target in links.items():
            resolved = str(Path(path).parent / target)
            self.assertIn(resolved, rows)
            self.assertNotEqual(rows[resolved][0], '120000')
        pointer = ('gitdir: ' + m.TEMPLATE + '/.git/worktrees/' + Path(m.AUTHORITY).name + '\n').encode()
        self.assertEqual(sha(pointer), inputs['.git'][0])
        self.assertEqual(derive.coverage()['inputs'], [dict(path=r, sha256=d, mode=mo) for r, d, mo in m.AUTH_INPUTS])

    def test_changed_constants_derive_from_reviewed_bytes(self):
        by_path = {p: after for p, _, after in m.CHANGED_INPUTS}
        parser = m.TEMPLATE + '/lib/gct_claude_signing_worker.py'
        self.assertEqual(sha(blob('lib/gct_claude_signing_worker.py')), by_path[parser])
        self.assertIn(b'MODEL = "claude-opus-5-5"', blob('lib/gct_claude_signing_worker.py'))
        self.assertEqual(sha(STAGED_CLI.read_bytes()), m.CLI_NEW)
        city_old, city_transition, city_final = derive.city_bytes(Path(m.O+'/reports/r5/i/00').read_bytes())
        self.assertEqual((sha(city_old), sha(city_final)), (m.CITY_OLD, m.CITY_NEW))
        self.assertNotIn(b'"opus-5"', city_final)
        self.assertNotIn(b'claude-opus-5"', city_final)
        prereqs = load('prereqs_under_test', 'prereqs.py')
        self.assertEqual(sha(city_transition), prereqs.CITY_TRANSITION)
        registry_old = predecessor('/home/loucmane/gascity/city/managed/rig-permissions.json',
                                   INPUTS/'rig-permissions.json.before', m.REGISTRY_OLD)
        _, registry_new = derive.registry_bytes(registry_old)
        self.assertEqual(sha(registry_new), m.REGISTRY_NEW)
        rig_old = predecessor('/home/loucmane/gascity/city/managed/rig-permissions.toml',
                              INPUTS/'rig-permissions.toml.before', m.RIGPERM_OLD)
        scratch = Path(subprocess.run(['/usr/bin/mktemp', '-d'], capture_output=True, text=True,
                                      check=True).stdout.strip())
        lines = rig_old.decode().splitlines(True)
        self.assertEqual(lines[94], 'model = "opus-5"\n')
        lines[94] = 'model = "opus-5-5"\n'
        self.assertEqual(derive.render(registry_old, scratch), ''.join(lines).encode(),
                         'renderer method must reproduce the live file from the live registry')
        self.assertEqual(sha(derive.render(registry_new, scratch)), m.RIGPERM_NEW)

    def test_retained_template_pins_equal_target_blobs(self):
        inputs = {p['path']: p['sha256'] for p in old['metadata']['inputs']}
        for path, digest in m.RETAINED_TEMPLATE_PINS.items():
            relative = path[len(m.TEMPLATE)+1:]
            self.assertEqual(inputs[path], digest)
            self.assertEqual(sha(blob(relative)), digest)
            self.assertEqual(sha(blob(relative, '51440da2d0ff12912ff7d2ec26d239849e3bc342')), digest)
        worker = next(p for p in old['integrity']['providers'] if p['name'] == 'claude')
        self.assertEqual(worker['sha256'], m.RETAINED_TEMPLATE_PINS[worker['path']])

    def test_worker_version_derivation(self):
        self.assertTrue(derive.deps_version('4f9acd546431f865c2b0bddeec81a4b2bbb7381a32a99b5dd93a155b6be7dcb4',
                                            m.CLI_OLD, '51440da2d0ff12912ff7d2ec26d239849e3bc342').endswith(
                        '8b8b3f7680181c1bad5ee74f6773e8c57616531e3bf16b94649c94bc0f9766a5'))
        self.assertEqual(derive.deps_version(m.CHANGED_INPUTS[0][2], m.CLI_NEW, m.TEMPLATE_COMMIT), m.VERSION_NEW)

    def test_build_against_frozen_baseline(self):
        if m.BASELINE_SHA is None:
            with self.assertRaisesRegex(Exception, 'baseline not yet frozen'):
                m.build(old_bytes, m3_raw, closure['host'], parents, '1'*64, '2'*64)
            return
        raw = Path(m.BASELINE_PATH).read_bytes()
        self.assertEqual(sha(raw), m.BASELINE_SHA)
        real = json.loads(raw)['closure']
        new, report = m.build(old_bytes, raw, real['host'], parents, '1'*64, '2'*64)
        self.assertLessEqual(report['frame']['upper_bound_bytes'], 131072)
        self.assertEqual(set(report['coverage_map']['trees']['changed']), set(m.REPINNED_TREES))

    def test_build_refuses_foreign_baseline_and_manifest(self):
        saved = m.BASELINE_SHA
        m.BASELINE_SHA = hexd('frozen')
        try:
            with self.assertRaisesRegex(Exception, 'current baseline drift'):
                m.build(old_bytes, m3_raw, closure['host'], parents, '1'*64, '2'*64)
            with self.assertRaisesRegex(Exception, 'installed R9 manifest drift'):
                m.build(old_bytes + b' ', m3_raw, closure['host'], parents, '1'*64, '2'*64)
        finally:
            m.BASELINE_SHA = saved

    def test_host_and_identity_refusals(self):
        host = copy.deepcopy(closure['host']); host['host']['pid'] += 1
        self.refuses('manifest/host binding', host=host)
        for overrides in (dict(attempt='1'*64), dict(attempt=old['metadata']['attempt']),
                          dict(transaction=old['metadata']['transaction']), dict(attempt='bad')):
            with self.subTest(overrides=overrides):
                self.refuses('fresh distinct transaction and attempt required', **overrides)

    def test_parent_refusals(self):
        for field, value in (('uid', 0), ('mode', 0o777), ('entries', ['consumed']),
                             ('path', m.ROOT+'/other'), ('inode', 0)):
            changed = copy.deepcopy(parents); changed[1][field] = value
            with self.subTest(field=field):
                self.refuses('fresh output parent identity', parents=changed)
        for value in (parents[2]['inode'], old['metadata']['parents'][1]['inode']):
            changed = copy.deepcopy(parents); changed[1]['inode'] = value
            self.refuses('output alias/reuse', parents=changed)
        changed = copy.deepcopy(parents); changed[0]['inode'] += 1
        self.refuses('platform parent drift', parents=changed)

    def test_refuses_wrong_successor_bytes(self):
        def case(mutate):
            value = copy.deepcopy(closure); mutate(value); return value
        cases = [(case(lambda c, p=path: c['pins'][p].update(sha256=hexd('wrong'))), 'reviewed successor input')
                 for path, _, _ in m.CHANGED_INPUTS]
        cases += [
            (case(lambda c: c['pins'][m.CITY_SOURCE].update(sha256=m.CITY_OLD)), 'city config successor source bytes'),
            (case(lambda c: c['pins'][m.CITY_SOURCE].update(mode=0o600)), 'city config successor source bytes'),
            (case(lambda c: c['pins'][m.O+'/reports/r5/i/00'].update(sha256=m.CITY_NEW)), 'city config backup bytes'),
            (case(lambda c: c['pins'][m.TEMPLATE+'/lib/gct_claude_subscription.py'].update(sha256=hexd('w'))),
             'retained Template bytes'),
            (case(lambda c: c['pins'][m.AUTHORITY+'/AGENTS.md'].update(sha256=hexd('wrong'))), 'authority file'),
            (case(lambda c: c['pins'][m.AUTHORITY+'/.git'].update(mode=0o600)), 'authority file'),
            (case(lambda c: c['trees'].pop(m.AUTHORITY+'/tests')), 'authority tree'),
            (case(lambda c: c['links'].update({m.AUTHORITY+'/plans/current': 'elsewhere.md'})), 'authority link'),
        ]
        for path in m.REPINNED_TREES:
            before = next(t['sha256'] for t in old['metadata']['trees'] if t['path'] == path)
            cases.append((case(lambda c, p=path, d=before: c['trees'][p].update(sha256=d)),
                          'repinned tree unexpectedly unchanged'))
        for index, (value, reason) in enumerate(cases):
            with self.subTest(case=index, reason=reason):
                self.refuses(reason, closure=value)

    def test_refuses_unexpected_predecessor(self):
        def first(rows, key, value):
            return next(p for p in rows if p[key] == value)
        cases = [
            (lambda v: v['metadata']['inputs'].remove(first(v['metadata']['inputs'], 'path',
                                                             '/usr/lib/python3.12/test/__init__.py')),
             'unused stdlib test pin cardinality'),
            (lambda v: v['integrity']['repositories'].append(dict(name='x', path='/x', commit=m.TEMPLATE_COMMIT)),
             'authority already present'),
            (lambda v: first(v['integrity']['providers'], 'name', 'claude-native').update(path='/other'),
             'exact predecessor native provider'),
            (lambda v: first(v['integrity']['providers'], 'name', 'claude').update(resolved_path='/other'),
             'exact predecessor worker'),
            (lambda v: first(v['managed_files'], 'name', 'city-config').update(source='/other'),
             'exact predecessor city config'),
            (lambda v: first(v['integrity']['files'], 'name', 'rig-permissions.json').update(sha256=hexd('w')),
             'exact predecessor integrity file'),
            (lambda v: first(v['metadata']['inputs'], 'path', '/home/loucmane/gascity/bin/claude').update(
                sha256=hexd('w')), 'exact predecessor input'),
            (lambda v: v['metadata']['trees'].append(dict(name='', path='/home/loucmane/gas-city-template-worktrees',
                                                          sha256=hexd('w'), mode=493)),
             'authority coverage overlaps an existing pin'),
        ]
        for index, (mutate, reason) in enumerate(cases):
            with self.subTest(case=index, reason=reason):
                self.refuses(reason, old=variant(mutate))

    def test_more_predecessor_refusals(self):
        def first(rows, key, value):
            return next(p for p in rows if p[key] == value)
        gc_b = '/var/tmp/ga-mutg-custody-build-20260920/gc-b'
        cases = [
            (lambda v: v['core'].update(sha256='0'*64), 'unchanged installed Core binding'),
            (lambda v: v['core'].update(source=gc_b), 'backup alias or duplicate'),
            (lambda v: v['metadata']['inputs'].remove(first(v['metadata']['inputs'], 'path',
                                                             '/home/loucmane/gascity/bin/claude')),
             'changed input cardinality'),
            (lambda v: v['metadata']['inputs'].remove(first(v['metadata']['inputs'], 'path',
                                                             m.TEMPLATE + '/lib/gct_claude_subscription.py')),
             'retained Template input'),
            (lambda v: v['integrity']['files'].remove(first(v['integrity']['files'], 'name', 'rig-permissions.json')),
             'integrity file: rig-permissions.json'),
            (lambda v: v['integrity']['providers'].remove(first(v['integrity']['providers'], 'name', 'claude-native')),
             'native provider'),
            (lambda v: v['integrity']['providers'].remove(first(v['integrity']['providers'], 'name', 'claude')),
             'signing provider'),
            (lambda v: v['managed_files'].remove(first(v['managed_files'], 'name', 'city-config')),
             'city config managed file'),
            (lambda v: v['metadata']['inputs'].append(dict(name='', path=m.CITY_SOURCE, sha256=m.CITY_NEW, mode=420)),
             'city source duplicate'),
            (lambda v: v['metadata']['trees'].remove(first(v['metadata']['trees'], 'path', m.R5R)),
             'repinned tree cardinality'),
            (lambda v: first(v['metadata']['trees'], 'path', m.R5R).update(sha256='0'*64), 'exact predecessor tree'),
            (lambda v: v['previous_metadata'].update(manifest_backup_path='/elsewhere'), 'previous backup binding'),
            (lambda v: v['metadata']['preimages'].pop(0), 'preimage cardinality'),
            (lambda v: v['metadata']['inputs'].append(dict(name='', path=m.AUTHORITY + '/stray', sha256='0'*64,
                                                           mode=420)), 'authority coverage overlaps an existing pin'),
            (lambda v: v['metadata']['trees'].append(dict(name='', path=m.AUTHORITY, sha256='0'*64, mode=493)),
             'authority coverage overlaps an existing pin'),
        ]
        for index, (mutate, reason) in enumerate(cases):
            with self.subTest(case=index, reason=reason):
                self.refuses(reason, old=variant(mutate))

    def test_renderer_and_libexpat_constants(self):
        prereqs = load('prereqs_constants', 'prereqs.py')
        self.assertEqual(sha(blob('bin/gct-managed-rig-permissions')), prereqs.RENDERER_SHA)
        self.assertEqual(prereqs.REGISTRY_EDITS[0], (m.CLI_OLD, m.CLI_NEW))
        path, before, after = m.CHANGED_INPUTS[5]
        self.assertEqual(path, '/usr/lib/x86_64-linux-gnu/libexpat.so.1.9.1')
        raw = Path(path).read_bytes()
        self.assertEqual(sha(raw), after)
        record = Path('/var/lib/dpkg/info/libexpat1:amd64.md5sums').read_text()
        self.assertIn(hashlib.md5(raw).hexdigest() + '  usr/lib/x86_64-linux-gnu/libexpat.so.1.9.1', record)
        installed = next(p for p in old['metadata']['inputs'] if p['path'] == path)
        self.assertEqual(installed['sha256'], before)

    def test_live_and_serialized_host_order_identical(self):
        host = copy.deepcopy(closure['host'])
        host['host'] = {k: host['host'][k] for k in old['metadata']['host']}
        host['namespaces'] = {k: host['namespaces'][k] for k in reversed(list(host['namespaces']))}
        live = build(host=host)
        replay = build(host=json.loads(json.dumps(host, sort_keys=True)))
        self.assertEqual(live, replay)
        self.assertEqual(m.b.encoded(live[0]), m.b.encoded(replay[0]))
        self.assertEqual(list(live[0]['metadata']['host']), list(old['metadata']['host']))
        self.assertEqual(list(live[0]['metadata']['namespaces']), list(old['metadata']['namespaces']))


if __name__ == '__main__':
    unittest.main()
