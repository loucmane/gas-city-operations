"""Offline M5 data-binding tests; synthetic closure and parents, never an execution manifest.

The synthetic closure is the frozen M3 baseline overlaid with the expected
successor pins. Tree digests are placeholders: only the frozen capture can
supply real ones, and build() refuses until that capture is pinned.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import types
import unittest

HERE = Path(__file__).parent
p = HERE/'manifest_candidate.py'
m = types.ModuleType('candidate_under_test'); m.__file__ = str(p)
exec(compile(p.read_bytes(), str(p), 'exec', dont_inherit=True), m.__dict__)
old_bytes = (Path(m.OLD_ROOT)/'q/manifest.json').read_bytes()
old = json.loads(old_bytes)
M3_BASELINE = Path('/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922/'
                   'gct-m1wh-metadata-20260922-r3/baseline.json')
m3_raw = M3_BASELINE.read_bytes()
assert hashlib.sha256(m3_raw).hexdigest() == 'c411dc6072d3a5d29c79e70883c50c13503014fedcc819a3b6778aae2979daf6'
STAGED_CLI = Path('/home/loucmane/.local/share/gas-city-staging/gct-er3h/claude-2.1.280')


def hexd(label):
    return hashlib.sha256(label.encode()).hexdigest()


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


def tracked():
    out = subprocess.run(['/usr/bin/git', '-C', m.TEMPLATE, 'ls-tree', '-r', '--full-tree', m.TEMPLATE_COMMIT],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    rows = {}
    for line in out:
        meta, path = line.split('\t', 1)
        mode, _, obj = meta.split()
        rows[path] = (mode, obj)
    return rows


def blob(path):
    return subprocess.run(['/usr/bin/git', '-C', m.TEMPLATE, 'show', m.TEMPLATE_COMMIT+':'+path],
                          capture_output=True, check=True).stdout


class SuccessorTests(unittest.TestCase):
    def test_native_successor_fields(self):
        new, _ = build()
        self.assertEqual(new['previous_sha256'], old['core']['sha256'])
        self.assertEqual(new['activation']['previous_commit'], old['activation']['expected_commit'])
        self.assertEqual(new['activation']['previous_version'], old['activation']['expected_version'])
        self.assertEqual(new['backup_path'], '/var/tmp/ga-mutg-custody-build-20260920/gc-b')
        self.assertEqual(new['core'], old['core'])
        self.assertEqual(new['metadata']['protected_trees'], old['metadata']['protected_trees'])
        self.assertEqual(new['metadata']['runtime'], old['metadata']['runtime'])
        self.assertEqual(new['metadata']['writer'], old['metadata']['writer'])
        self.assertEqual(new['metadata']['absent'], old['metadata']['absent'])
        self.assertEqual(new['metadata']['cache_sha256'], old['metadata']['cache_sha256'])
        self.assertEqual(new['metadata']['imports_sha256'], old['metadata']['imports_sha256'])
        self.assertEqual(m.b.finalized(new), new)
        self.assertEqual(build(), build())

    def test_exact_coverage_map(self):
        new, report = build()
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
        self.assertEqual(set(cm['files']['changed']), {'rig-permissions.toml'})
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
                self.assertEqual(hashlib.sha256(blob(path)).hexdigest(), inputs[path][0])
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
        self.assertEqual(hashlib.sha256(pointer).hexdigest(), inputs['.git'][0])

    def test_changed_constants_derive_from_reviewed_bytes(self):
        self.assertEqual(hashlib.sha256(blob('lib/gct_claude_signing_worker.py')).hexdigest(),
                         m.CHANGED_INPUTS[0][2])
        self.assertIn(b'MODEL = "claude-opus-5-5"', blob('lib/gct_claude_signing_worker.py'))
        self.assertEqual(hashlib.sha256(STAGED_CLI.read_bytes()).hexdigest(), m.CLI_NEW)
        backup = Path(m.O + '/reports/r5/i/00').read_bytes()
        self.assertEqual(hashlib.sha256(backup).hexdigest(), m.CITY_OLD)
        lines = backup.decode().splitlines(True)
        edits = {21: ('model = "opus-5"\n', 'model = "opus-5-5"\n'),
                 28: ('default = "opus-5"\n', 'default = "opus-5-5"\n'),
                 31: ('value = "opus-5"\n', 'value = "opus-5-5"\n'),
                 32: ('label = "Claude Opus 5"\n', 'label = "Claude Opus 5.5"\n'),
                 33: ('flag_args = ["--model", "claude-opus-5"]\n', 'flag_args = ["--model", "claude-opus-5-5"]\n'),
                 236: ('model = "opus-5"\n', 'model = "opus-5-5"\n')}
        for number, (before, after) in edits.items():
            self.assertEqual(lines[number-1], before)
            lines[number-1] = after
        new_city = ''.join(lines).encode()
        self.assertEqual(hashlib.sha256(new_city).hexdigest(), m.CITY_NEW)
        self.assertNotIn(b'"opus-5"', new_city)
        self.assertNotIn(b'claude-opus-5"', new_city)

    def test_worker_version_derivation(self):
        def version(parser, cli, commit):
            root = m.TEMPLATE
            def at(path):
                raw = subprocess.run(['/usr/bin/git', '-C', root, 'show', commit+':'+path],
                                     capture_output=True, check=True).stdout
                return hashlib.sha256(raw).hexdigest()
            records = [dict(path='/home/loucmane/gascity/bin/claude', sha256=cli),
                       dict(path=root+'/templates/claude/core-signing-control-policy.json',
                            sha256=at('templates/claude/core-signing-control-policy.json')),
                       dict(path=root+'/bin/gct-claude-signing-worker', sha256=at('bin/gct-claude-signing-worker')),
                       dict(path=root+'/lib/gct_claude_signing_worker.py', sha256=parser),
                       dict(path=root+'/lib/gct_claude_subscription.py', sha256=at('lib/gct_claude_subscription.py')),
                       dict(path=root+'/templates/claude/signing-provider.toml',
                            sha256=at('templates/claude/signing-provider.toml'))]
            domain = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            return 'gct-claude-signing-worker 1 dependencies_sha256=' + hashlib.sha256(domain).hexdigest()
        # The method reproduces the reviewed M3 value before deriving M5's.
        self.assertTrue(version('4f9acd546431f865c2b0bddeec81a4b2bbb7381a32a99b5dd93a155b6be7dcb4', m.CLI_OLD,
                                '51440da2d0ff12912ff7d2ec26d239849e3bc342').endswith(
                        '8b8b3f7680181c1bad5ee74f6773e8c57616531e3bf16b94649c94bc0f9766a5'))
        self.assertEqual(version(m.CHANGED_INPUTS[0][2], m.CLI_NEW, m.TEMPLATE_COMMIT), m.VERSION_NEW)

    def test_build_refuses_until_baseline_frozen(self):
        with self.assertRaises(Exception):
            m.build(old_bytes, m3_raw, closure['host'], parents, '1'*64, '2'*64)

    def test_manifest_tamper(self):
        with self.assertRaises(Exception):
            m.build(old_bytes + b' ', m3_raw, closure['host'], parents, '1'*64, '2'*64)

    def test_host_drift(self):
        host = copy.deepcopy(closure['host']); host['host']['pid'] += 1
        with self.assertRaises(Exception):
            build(host=host)

    def test_attempt_reuse(self):
        for overrides in (dict(attempt='1'*64), dict(attempt=old['metadata']['attempt']),
                          dict(transaction=old['metadata']['transaction']), dict(attempt='bad')):
            with self.subTest(overrides=overrides), self.assertRaises(Exception):
                build(**overrides)

    def test_parent_authority_alias_reuse(self):
        for field, value in (('uid', 0), ('mode', 0o777), ('entries', ['consumed']),
                             ('path', m.ROOT+'/other'), ('inode', 0)):
            changed = copy.deepcopy(parents); changed[1][field] = value
            with self.subTest(field=field), self.assertRaises(Exception):
                build(parents=changed)
        for value in (parents[2]['inode'], old['metadata']['parents'][1]['inode']):
            changed = copy.deepcopy(parents); changed[1]['inode'] = value
            with self.assertRaises(Exception):
                build(parents=changed)
        changed = copy.deepcopy(parents); changed[0]['inode'] += 1
        with self.assertRaises(Exception):
            build(parents=changed)

    def test_refuses_wrong_successor_bytes(self):
        cases = []
        for path, _, _ in m.CHANGED_INPUTS:
            c = copy.deepcopy(closure); c['pins'][path]['sha256'] = hexd('wrong'); cases.append(c)
        c = copy.deepcopy(closure); c['pins'][m.CITY_SOURCE]['sha256'] = m.CITY_OLD; cases.append(c)
        c = copy.deepcopy(closure); c['pins'][m.O+'/reports/r5/i/00']['sha256'] = m.CITY_NEW; cases.append(c)
        c = copy.deepcopy(closure); c['pins'][m.AUTHORITY+'/AGENTS.md']['sha256'] = hexd('wrong'); cases.append(c)
        c = copy.deepcopy(closure); c['pins'][m.AUTHORITY+'/.git']['mode'] = 0o600; cases.append(c)
        c = copy.deepcopy(closure); del c['trees'][m.AUTHORITY+'/tests']; cases.append(c)
        c = copy.deepcopy(closure); c['links'][m.AUTHORITY+'/plans/current'] = 'elsewhere.md'; cases.append(c)
        c = copy.deepcopy(closure); c['trees'][m.R5R] = dict(c['trees'][m.R5R], sha256=
            next(t['sha256'] for t in old['metadata']['trees'] if t['path'] == m.R5R)); cases.append(c)
        for index, case in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(Exception):
                build(closure=case)

    def test_refuses_unexpected_predecessor(self):
        variant = copy.deepcopy(old)
        variant['metadata']['inputs'] = [p for p in variant['metadata']['inputs']
                                         if p['path'] != '/usr/lib/python3.12/test/__init__.py']
        with self.assertRaises(Exception):
            build(old=m.b.finalized(variant))
        variant = copy.deepcopy(old)
        variant['integrity']['repositories'].append(dict(name='x', path=m.AUTHORITY, commit='0'*40))
        with self.assertRaises(Exception):
            build(old=m.b.finalized(variant))

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
