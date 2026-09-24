"""The ga-f37t package is exactly the successor derivation of the reviewed ga-4z38 r14 package."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWN = {'README.md', 'test_successor.py', 'generators/make_successor.py'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Derivation(unittest.TestCase):
    def test_every_file_is_the_successor_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, '-B', str(HERE/'generators'/'make_successor.py'), tmp],
                                  capture_output=True, text=True, timeout=300)
            self.assertEqual(done.returncode, 0, done.stderr)
            produced = {str(p.relative_to(tmp)) for p in Path(tmp).rglob('*') if p.is_file()}
            tracked = {str(p.relative_to(HERE)) for p in HERE.rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts}
            self.assertEqual(tracked - produced, OWN)
            self.assertEqual(produced - tracked, set())
            for name in sorted(produced):
                self.assertEqual(sha(Path(tmp)/name), sha(HERE/name), name)

    def test_only_reconcile_names_the_held_predecessor(self):
        for path in HERE.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.name in {'README.md', 'test_successor.py'}:
                continue
            if path.relative_to(HERE).parts[0] == 'generators':
                continue
            text = path.read_text().replace('/var/tmp/ga-4z38-platform-inspector-20260924-r1', '')
            if path.name == 'reconcile-predecessor-r3.py':
                self.assertIn("before=bead('ga-4z38')", text)
                self.assertIn("attempt['session_id']=='ci-gi0lh'", text)
                self.assertIn("closed[0]['metadata']['state']=='stale-session'", text)
                self.assertIn("new=bead('ga-f37t')", text)
                continue
            self.assertNotIn('ga-4z38', text, str(path))

    def test_the_rebuilt_inspector_path_is_kept(self):
        for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
            text = (HERE/name).read_text()
            self.assertIn("BUILD=Path('/var/tmp/ga-4z38-platform-inspector-20260924-r1')", text, name)
            self.assertIn('b8ebcde38a9ee8078752949226f6736ea14a25413fba73db4d95076261658d13', text, name)

    def test_the_worker_binds_the_fresh_worktree(self):
        brief = (HERE/'worker-brief.md').read_text()
        self.assertIn('Worktree /home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles.', brief)
        self.assertIn('Branch codex/ga-f37t-typed-route-cycles.', brief)
        bind = (HERE/'bind-task-r3.py').read_text()
        self.assertIn("BEAD='ga-f37t'", bind)


if __name__ == '__main__':
    unittest.main()
