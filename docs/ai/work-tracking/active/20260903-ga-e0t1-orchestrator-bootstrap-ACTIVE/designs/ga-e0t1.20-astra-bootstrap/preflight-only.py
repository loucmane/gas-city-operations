"""Invoke the complete WORKTREE preflight, refusing before any persistent write.

This is a diagnostic, never an execution alternative. The only modified runtime
surfaces are fail-closed write blockers and ROOT.mkdir interception. Every actual
pre-mutation source, signature, path, ownership, hazard and identity check runs.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

path = Path(sys.argv[1]).resolve(strict=True)
spec = importlib.util.spec_from_file_location('preflight_only_worktree', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m._SOURCE_SHA = hashlib.sha256(path.read_bytes()).hexdigest()


class PreflightComplete(Exception):
    pass


class ReadOnlyRoot(type(Path())):
    def mkdir(self, *args, **kwargs):
        raise PreflightComplete()


def no_write(*args, **kwargs):
    raise AssertionError('diagnostic refuses write')


old_git = m.git
def read_only_git(*args, **kwargs):
    assert args[0] in ('rev-parse', 'verify-commit', 'config', 'ls-tree'), 'mutating Git forbidden'
    return old_git(*args, **kwargs)


m.ROOT = ReadOnlyRoot(m.ROOT)
m.write = no_write
m.git = read_only_git
try:
    m.main()
except PreflightComplete:
    print(json.dumps({'ok': True, 'complete_pre_mutation_checks': True,
                      'persistent_output_created': False, 'worker_launched': False,
                      'executor_sha256': m._SOURCE_SHA}, sort_keys=True))
else:
    raise AssertionError('diagnostic did not reach the declared mutation boundary')
