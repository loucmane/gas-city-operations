"""Find and verify a delivery worktree by file reads only (ga-fsfg R3).

No Git process runs here. A worktree is located among the direct children of the
Operations worktree root through its gitfile and administrative `HEAD`, and a
branch resolves only through a loose ref or `packed-refs`.
"""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .delivery_grammar import BRANCH

MAX_LINK_BYTES = 4096
MAX_PACKED_REFS_BYTES = 16 * 1024 * 1024
MAX_WORKTREES = 4096
OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
HEAD_PREFIX = "ref: refs/heads/"


@dataclass(frozen=True)
class Checkout:
    """A verified linked worktree: its root, private Git directory and common directory."""

    root: Path
    admin: Path
    common: Path


def read_bounded(path: Path, limit: int = MAX_LINK_BYTES) -> bytes | None:
    """Read a regular file, never through a final symlink, a FIFO or past `limit` bytes."""

    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        return None
    chunks: list[bytes] = []
    size = 0
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                return None
    finally:
        os.close(fd)
    return b"".join(chunks)


def _line(path: Path) -> str | None:
    """One newline-terminated UTF-8 line, as Git writes gitfiles, links and HEAD."""

    raw = read_bounded(path)
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text.endswith("\n") or "\n" in text[:-1] or "\r" in text:
        return None
    return text[:-1]


def _exact_directory(path: Path) -> bool:
    try:
        return path.resolve(strict=True) == path and stat.S_ISDIR(os.lstat(path).st_mode)
    except (OSError, RuntimeError):
        return False


def admin_directory(worktree: Path, common: Path) -> Path | None:
    """The private Git directory a worktree's gitfile names, when it is shaped like one."""

    line = _line(worktree / ".git")
    if line is None or not line.startswith("gitdir: "):
        return None
    admin = Path(line[len("gitdir: ") :])
    if not admin.is_absolute() or admin.parent != common / "worktrees":
        return None
    return admin


def verify_checkout(worktree: Path, canonical: Path, worktree_root: Path) -> Checkout:
    """Prove a direct child of the worktree root is a linked worktree of the canonical repo.

    The gitfile, the back-pointer and `commondir` must all agree, and no path on the
    way may be a symlink.
    """

    common = canonical / ".git"
    if worktree.parent != worktree_root or worktree == canonical:
        raise ValueError("delivery worktree is not a direct child of the Operations worktree root")
    if not _exact_directory(worktree) or not _exact_directory(common):
        raise ValueError("delivery worktree or Git common directory is aliased or missing")
    admin = admin_directory(worktree, common)
    if admin is None or not _exact_directory(admin):
        raise ValueError("delivery worktree is not a linked worktree of the canonical repository")
    if _line(admin / "gitdir") != str(worktree / ".git"):
        raise ValueError("delivery worktree back-pointer does not name the worktree")
    shared = _line(admin / "commondir")
    if shared is None:
        raise ValueError("delivery worktree has no readable commondir")
    target = Path(shared) if Path(shared).is_absolute() else admin / shared
    if Path(os.path.normpath(target)) != common:
        raise ValueError("delivery worktree commondir is not the canonical repository")
    return Checkout(worktree, admin, common)


def head_branch(admin: Path) -> str | None:
    """The branch an administrative `HEAD` names, or None when it is detached or odd."""

    line = _line(admin / "HEAD")
    if line is None or not line.startswith(HEAD_PREFIX):
        return None
    name = line[len(HEAD_PREFIX) :]
    if (
        not BRANCH.fullmatch(name)
        or name.startswith(("-", "/"))
        or name.endswith("/")
        or ".." in name
        or "//" in name
    ):
        return None
    return name


def resolve_branch(common: Path, name: str) -> str | None:
    """Resolve refs/heads/<name> from a loose ref or `packed-refs`, nothing else."""

    if os.path.lexists(common / "reftable"):
        raise ValueError("delivery refuses a reftable reference store")
    loose = common / "refs" / "heads" / name
    if os.path.realpath(loose) != str(loose):
        raise ValueError("delivery refuses an aliased loose reference")
    raw = read_bounded(loose, 256)
    if raw is not None:
        value = raw.decode("ascii", "replace").strip()
        return value if OBJECT_ID.fullmatch(value) else None
    if os.path.lexists(loose):
        raise ValueError("delivery refuses an unreadable loose reference")
    packed_path = common / "packed-refs"
    packed = read_bounded(packed_path, MAX_PACKED_REFS_BYTES)
    if packed is None:
        if os.path.lexists(packed_path):
            raise ValueError("delivery refuses an unreadable packed-refs file")
        return None
    wanted = f"refs/heads/{name}".encode()
    for line in packed.split(b"\n"):
        if not line or line.startswith((b"#", b"^")):
            continue
        oid, _, ref = line.partition(b" ")
        if ref == wanted:
            value = oid.decode("ascii", "replace")
            return value if OBJECT_ID.fullmatch(value) else None
    return None


def _children(worktree_root: Path, canonical: Path, matches: Callable[[Path], bool]) -> list[Path]:
    common = canonical / ".git"
    found: list[Path] = []
    with os.scandir(worktree_root) as entries:
        for count, entry in enumerate(entries, start=1):
            if count > MAX_WORKTREES:
                raise ValueError("delivery worktree root holds too many entries")
            if not entry.is_dir(follow_symlinks=False):
                continue
            path = worktree_root / entry.name
            admin = admin_directory(path, common)
            if admin is not None and matches(admin):
                found.append(path)
    return found


def checkout_for_branch(worktree_root: Path, canonical: Path, branch: str) -> Checkout:
    """The one direct child whose administrative HEAD names the branch."""

    found = _children(worktree_root, canonical, lambda admin: head_branch(admin) == branch)
    if len(found) != 1:
        raise ValueError("delivery needs exactly one Operations worktree on the branch")
    return verify_checkout(found[0], canonical, worktree_root)


def checkout_for_commit(worktree_root: Path, canonical: Path, sha: str) -> Checkout:
    """The one direct child whose branch HEAD resolves to the commit."""

    common = canonical / ".git"

    def matches(admin: Path) -> bool:
        name = head_branch(admin)
        return name is not None and resolve_branch(common, name) == sha

    found = _children(worktree_root, canonical, matches)
    if len(found) != 1:
        raise ValueError("delivery needs exactly one Operations worktree whose HEAD is the commit")
    return verify_checkout(found[0], canonical, worktree_root)
