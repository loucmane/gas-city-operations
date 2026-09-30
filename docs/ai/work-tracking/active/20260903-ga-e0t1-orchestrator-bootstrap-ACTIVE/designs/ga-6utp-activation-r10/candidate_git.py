"""Shared, hardened primitives for coordinator handling of Operations candidate worktrees.

Nothing here executes content from a candidate worktree. Every git command runs with no system or
global configuration, no optional locks, hooks and fsmonitor disabled, an explicit admin git-dir,
a minimal environment and a timeout.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import subprocess

GIT = "/usr/bin/git"
NAME = re.compile(r"[A-Za-z0-9._-]+")
MAX_SMALL = 4096
TIMEOUT = 120


class Refusal(RuntimeError):
    """A deterministic stop; never an invitation to retry differently."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def small_regular_text(path: Path) -> str:
    """A small regular file's text, read without following links or blocking; '' otherwise."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        return ""
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SMALL:
            return ""
        raw = os.read(fd, MAX_SMALL + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_SMALL or b"\r" in raw:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def real_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def verify_linked(root: Path, common: Path, worktree: Path, name: str) -> Path:
    """Return the admin directory of a verified linked candidate worktree, or refuse."""
    require(Path(os.path.realpath(common)) == common and real_directory(common), "common directory is not physical")
    require(Path(os.path.realpath(root)) == root and real_directory(root), "candidate root is not physical")
    require(Path(os.path.realpath(worktree)) == worktree and worktree.parent == root, "not a direct child of the root")
    require(bool(NAME.fullmatch(name)) and name not in {".", ".."}, "invalid worktree name")
    admin = common / "worktrees" / name
    require(real_directory(common / "worktrees") and real_directory(admin), "admin directory is not real")
    require(small_regular_text(worktree / ".git") == f"gitdir: {admin}\n", "gitfile does not name the recorded admin directory")
    require(small_regular_text(admin / "gitdir") == f"{worktree}/.git\n", "admin back-pointer mismatch")
    require(small_regular_text(admin / "commondir") == "../..\n", "admin commondir mismatch")
    return admin


def environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "HOME": "/nonexistent",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ATTR_NOSYSTEM": "1",
    }


def git(git_dir: Path, work_tree: Path | None, *args: str, expected=(0,), timeout: int = TIMEOUT,
        cwd: Path | None = None) -> bytes:
    argv = [GIT, "--no-optional-locks", f"--git-dir={git_dir}"]
    if work_tree is not None:
        argv.append(f"--work-tree={work_tree}")
    argv += ["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "core.attributesFile=/dev/null", *args]
    try:
        result = subprocess.run(argv, env=environment(), cwd=str(cwd or "/"), stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise Refusal(f"git timed out: {args[:2]}") from exc
    require(result.returncode in expected, f"git {args[:2]} exited {result.returncode}: {result.stderr[-400:]!r}")
    return result.stdout


def no_drivers(git_dir: Path, work_tree: Path) -> None:
    """The effective configuration (includes and config.worktree too) defines no content driver."""
    out = git(git_dir, work_tree, "config", "--includes", "--show-origin", "--get-regexp",
              r"^(filter|diff|merge)\.", expected=(0, 1))
    require(out == b"", "a filter/diff/merge driver is configured: " + out[:400].decode("utf-8", "replace"))
    for extra in (git_dir / "info" / "attributes", git_dir.parent.parent / "info" / "attributes"):
        require(not os.path.lexists(extra), f"repository attributes file present: {extra}")


def no_gitlinks(git_dir: Path, work_tree: Path, commit: str) -> None:
    """The tree holds no gitlink, so no git command spawns a child git in a directory the candidate controls."""
    listing = git(git_dir, work_tree, "ls-tree", "-r", "-z", "--full-tree", commit)
    links = [entry.split(b"\t", 1)[-1].decode("utf-8", "replace") for entry in listing.split(b"\0")
             if entry.startswith(b"160000 ")]
    require(not links, f"gitlinks in the tree at {commit}: {links[:10]}")


def split_z(raw: bytes) -> list[str]:
    return [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]
