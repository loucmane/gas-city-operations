"""Operational reader regression using disposable fixtures only."""
import hashlib
import importlib.util
import os
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
ORIGINAL = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1.20-astra-bootstrap/worktree.py')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path):
    path = tmp_path/'old-access-time.txt'
    path.write_bytes(b'unchanged pinned content\n')
    os.utime(path, ns=(1_000_000_000, 2_000_000_000))
    return path, hashlib.sha256(b'unchanged pinned content\n').hexdigest()


def test_original_reader_reproduces_self_induced_atime_refusal(tmp_path):
    original = load(ORIGINAL, 'original_atime_reader')
    path, digest = fixture(tmp_path)
    before = path.stat()
    with pytest.raises(AssertionError):
        original.read(path, digest)
    assert path.stat().st_atime_ns != before.st_atime_ns
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert path.stat().st_ctime_ns == before.st_ctime_ns


def test_successor_preserves_every_stat_field(tmp_path):
    fixed = load(HERE/'worktree-noatime.py', 'fixed_atime_reader')
    path, digest = fixture(tmp_path)
    before = path.stat()
    assert fixed.read(path, digest) == b'unchanged pinned content\n'
    assert path.stat() == before


def test_hash_and_symlink_refusals_unchanged(tmp_path):
    fixed = load(HERE/'worktree-noatime.py', 'fixed_atime_negatives')
    path, digest = fixture(tmp_path)
    with pytest.raises(AssertionError):
        fixed.read(path, '0'*64)
    link = tmp_path/'link'
    link.symlink_to(path)
    with pytest.raises(OSError):
        fixed.read(link, digest)


def test_only_two_open_flags_differ():
    original = ORIGINAL.read_text()
    actual = (HERE/'worktree-noatime.py').read_text()
    before = 'os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)'
    assert original.count(before) == 2
    assert actual == original.replace(before, before[:-1]+' | os.O_NOATIME)')
