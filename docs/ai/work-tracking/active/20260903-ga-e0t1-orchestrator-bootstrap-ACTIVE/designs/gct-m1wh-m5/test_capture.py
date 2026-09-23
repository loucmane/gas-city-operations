"""Offline tests of the pure capture bounds: re-pinned tree classification, the Git config check, the
reviewed M1 bound baselines and the carried-forward pin-change guard."""
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


cap = load('capture_under_test', 'capture.py')
cap.load_candidate(hashlib.sha256((HERE/'manifest_candidate.py').read_bytes()).hexdigest())
m = cap.m


def meta(size=1, mtime=1, atime=1):
    return dict(device=1, inode=size, uid=1000, gid=1000, mode=420, type=32768, nlink=1, size=size,
                mtime_ns=mtime, ctime_ns=mtime, atime_ns=atime)


class CaptureBoundTests(unittest.TestCase):
    def test_r5r_allows_only_the_index(self):
        before = {'.': meta(), '.git': meta(), '.git/index': meta(), 'README.md': meta()}
        now = dict(before, **{'.git': meta(mtime=2), '.git/index': meta(size=2, mtime=2)})
        self.assertEqual(cap.classify('r5r', before, now)['outside_allowed'], [])
        now_atime = dict(before, **{'README.md': meta(atime=9)})
        self.assertEqual(cap.classify('r5r', before, now_atime)['outside_allowed'], [])
        for change in ({'README.md': meta(size=3)}, {'new.txt': meta()}):
            with self.subTest(change=change):
                self.assertTrue(cap.classify('r5r', before, dict(before, **change))['outside_allowed'])
        removed = {k: v for k, v in before.items() if k != 'README.md'}
        self.assertEqual(cap.classify('r5r', before, removed)['outside_allowed'], ['README.md'])

    def test_template_git_bound(self):
        before = {'.': meta(), 'HEAD': meta(), 'config': meta(), 'description': meta(), 'hooks': meta(),
                  'hooks/post-checkout': meta(), 'objects': meta(), 'objects/ab/cd': meta(),
                  'worktrees': meta(), 'worktrees/x': meta(), 'worktrees/x/index': meta()}
        allowed = dict(before, **{'HEAD': meta(mtime=2), 'config': meta(size=5), 'objects/ef/01': meta(),
                                  'worktrees/y/HEAD': meta(), 'rr-cache/zz/preimage': meta(),
                                  'refs/heads/new': meta(), 'logs/HEAD': meta(),
                                  'gas-city-workflow/transactions/a.json': meta()})
        del allowed['objects/ab/cd']
        self.assertEqual(cap.classify('git', before, allowed)['outside_allowed'], [])
        for change, removal in (({'hooks/pre-commit': meta()}, None), ({'description': meta(size=9)}, None),
                                ({'info/exclude': meta()}, None), ({'worktrees/x/config.worktree': meta()}, None),
                                ({'config.worktree': meta()}, None), ({}, 'hooks/post-checkout'),
                                ({'modules/sub/HEAD': meta()}, None)):
            now = dict(before, **change)
            if removal:
                del now[removal]
            with self.subTest(change=change, removal=removal):
                self.assertTrue(cap.classify('git', before, now)['outside_allowed'])

    def test_config_check_is_complete(self):
        listing = subprocess.run(['/usr/bin/git', '--no-optional-locks', 'config', '--file',
                                  m.TEMPLATE + '/.git/config', '--list'],
                                 capture_output=True, text=True, check=True).stdout
        self.assertFalse(any(cap.config_drift(listing).values()))
        for extra, key in (('include.path=/tmp/x', 'unexpected'), ('credential.helper=store', 'unexpected'),
                           ('extensions.worktreeconfig=true', 'unexpected'), ('gpg.program=/tmp/g', 'unexpected'),
                           ('branch.main.pushremote=evil', 'bad_branch_keys')):
            with self.subTest(extra=extra):
                self.assertTrue(cap.config_drift(listing + extra + '\n')[key])
        trimmed = '\n'.join(line for line in listing.splitlines() if not line.startswith('user.signingkey'))
        self.assertEqual(cap.config_drift(trimmed)['missing'], ['user.signingkey=FD5585922F5335BC378AD8D42ECF4432C7E7982D!'])
        self.assertTrue(cap.config_drift(listing + 'core.bare=false\n')['duplicate'])

    def test_bound_baselines_are_the_reviewed_digests(self):
        raw = cap.M1_AUDIT.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), cap.M1_AUDIT_SHA)
        trees = json.loads(raw)['trees']
        for path, expected in cap.M1_TREE_DIGESTS.items():
            self.assertEqual(trees[path]['sha256'], expected)
        self.assertEqual(cap.M1_TREE_DIGESTS[m.R5R], m.REPINNED_TREE_PREDECESSORS[m.R5R])
        m3 = (Path('/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922/'
                   'gct-m1wh-metadata-20260922-r3/manifest_candidate.py')).read_text()
        self.assertIn("TREE_NEW = '%s'" % cap.M1_TREE_DIGESTS[m.TEMPLATE + '/.git'], m3)

    def test_pin_change_guard(self):
        successors = {p: after for p, _, after in m.CHANGED_INPUTS}
        path = m.CHANGED_INPUTS[1][0]
        good = [dict(path=path, before=dict(sha256=m.CLI_OLD), after=dict(sha256=m.CLI_NEW))]
        self.assertEqual(cap.unexpected_changes(good, successors), [])
        wrong = [dict(path=path, before=dict(sha256=m.CLI_OLD), after=dict(sha256='0'*64))]
        other = [dict(path='/etc/systemd/system/x.service', before=dict(sha256='1'*64), after=dict(sha256='2'*64))]
        self.assertEqual(cap.unexpected_changes(wrong + other, successors), [path, '/etc/systemd/system/x.service'])

    def test_capture_requires_the_reviewed_candidate(self):
        with self.assertRaisesRegex(RuntimeError, 'candidate source differs'):
            cap.load_candidate('0'*64)


if __name__ == '__main__':
    unittest.main()
