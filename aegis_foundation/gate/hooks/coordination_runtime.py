"""Verify source-only coordinator runtime bytes, including ignored import inputs.

Git status is not an integrity manifest: ignored files, caches, assume-unchanged,
and skip-worktree can hide executable changes. Read bytes against canonical Git
objects instead. Mandatory source-only loading makes preserved caches inert;
their payloads are neither read nor unmarshalled by this verifier.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

TREES = ("scripts", "aegis_foundation", ".claude/scripts", "plugins/gas-city-workflow/scripts")
INSTALLED = (
    ".aegis/bin",
    ".aegis/runtime",
    ".aegis/runtime.env",
    ".aegis/foundation-manifest.json",
)
MAX_FILE = 16 * 1024 * 1024
MAX_FILES = 4096


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(root), *args], capture_output=True, timeout=10, check=False
    )
    if result.returncode:
        raise ValueError("canonical runtime object inventory failed")
    return result.stdout


def _regular_input(path: Path) -> None:
    if path.resolve(strict=True) != path:
        raise ValueError("coordination executable input is aliased")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE:
        raise ValueError("coordination executable input is special or oversized")


def _bytes(path: Path) -> bytes:
    _regular_input(path)
    data = path.read_bytes()
    if len(data) > MAX_FILE:
        raise ValueError("coordination executable input exceeds byte bound")
    return data


def _manifest(canonical: Path) -> tuple[str, dict[str, tuple[str, str]]]:
    algorithm = _git(canonical, "rev-parse", "--show-object-format").decode().strip()
    if algorithm not in {"sha1", "sha256"}:
        raise ValueError("unsupported canonical Git object format")
    raw = _git(canonical, "ls-tree", "-rz", "HEAD", "--", *TREES)
    manifest = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        fields, raw_path = record.split(b"\t", 1)
        mode, kind, oid = fields.decode().split()
        relative = raw_path.decode()
        if (
            mode not in {"100644", "100755"}
            or kind != "blob"
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise ValueError("canonical runtime must contain regular tracked source files")
        manifest[relative] = (mode, oid)
    if not manifest or len(manifest) > MAX_FILES:
        raise ValueError("canonical runtime inventory is empty or exceeds bound")
    return algorithm, manifest


def _preserved_cache(path: Path, root: Path, manifest: dict) -> None:
    # reviewed_runtime enforces source-only loading before reaching this check.
    # Keep source, path, alias, special-file and size constraints; this is not an
    # exemption for arbitrary ignored files or importable sourceless modules.
    if path.parent.name != "__pycache__":
        raise ValueError("unreviewed runtime file is not a preserved source cache")
    extensionless = re.fullmatch(r"([^.]+)cpython-[0-9]+(?:\.opt-[12])?\.pyc", path.name)
    if extensionless:
        # cache_from_source omits the separating dot for extensionless scripts.
        # SourceFileLoader also caches nonexecutable Python source. Require the
        # exact same-directory tracked source below; _verify separately binds its
        # bytes and actual mode to the reviewed Git object, without loading caches.
        source = path.parent.parent / extensionless[1]
    elif re.fullmatch(r".+\.[A-Za-z0-9_-]+(?:\.opt-[12])?\.pyc", path.name):
        source = Path(importlib.util.source_from_cache(str(path)))
    else:
        raise ValueError("unreviewed runtime file is not a preserved source cache")
    relative = source.relative_to(root).as_posix()
    if relative not in manifest:
        raise ValueError("runtime cache has no reviewed source")
    _regular_input(path)


def _verify(root: Path, algorithm: str, manifest: dict[str, tuple[str, str]]) -> None:
    for relative in INSTALLED:
        path = root / relative
        if path.exists() or path.is_symlink():
            raise ValueError("stationary coordination requires a source-only runtime")
    # Python startup imports these before the ordinary entrypoint. They are not
    # permitted task-controlled additions to this source-only runtime.
    for name in ("sitecustomize.py", "usercustomize.py"):
        if (root / name).exists() or (root / name).is_symlink():
            raise ValueError("task-controlled Python startup customization is not permitted")
    for relative, (mode, oid) in manifest.items():
        path = root / relative
        data = _bytes(path)
        actual = hashlib.new(
            algorithm, b"blob " + str(len(data)).encode() + b"\0" + data
        ).hexdigest()
        executable = bool(path.stat().st_mode & 0o111)
        if actual != oid or executable != (mode == "100755"):
            raise ValueError("runtime file bytes/mode differ from canonical Git objects")
    count = 0
    for relative in TREES:
        directory = root / relative
        if not directory.exists():
            continue
        if directory.resolve(strict=True) != directory or not directory.is_dir():
            raise ValueError("runtime directory is aliased or not a directory")
        for parent, dirs, files in os.walk(directory, followlinks=False, onerror=_inventory_error):
            for child in [*dirs, *files]:
                path = Path(parent) / child
                if path.is_symlink():
                    raise ValueError("runtime contains an aliased import input")
            for child in files:
                count += 1
                if count > MAX_FILES:
                    raise ValueError("runtime filesystem inventory exceeds bound")
                path = Path(parent) / child
                if path.relative_to(root).as_posix() not in manifest:
                    _preserved_cache(path, root, manifest)


def _inventory_error(error: OSError) -> None:
    raise ValueError("runtime filesystem inventory is unreadable") from error


def _source_only_loading() -> None:
    """Require the trusted entrypoints' loading policy before accepting inert caches."""
    if (
        sys.dont_write_bytecode is not True
        or sys.pycache_prefix != os.devnull
        or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1"
        or os.environ.get("PYTHONPYCACHEPREFIX") != os.devnull
    ):
        raise ValueError("stationary coordination requires source-only loading")
    null = Path(os.devnull)
    info = null.lstat()
    if (
        sys.platform != "linux"
        or null != Path("/dev/null")
        or not stat.S_ISCHR(info.st_mode)
        or info.st_rdev != os.makedev(1, 3)
        or null.resolve(strict=True) != null
    ):
        raise ValueError("source-only cache sink is not the exact Linux null device")


def reviewed_runtime(target: Path, canonical: Path) -> None:
    """Read-only integrity check; no cache cleanup, repair or candidate execution."""
    _source_only_loading()
    algorithm, manifest = _manifest(canonical)
    _verify(canonical, algorithm, manifest)
    _verify(target, algorithm, manifest)


FOREIGN_RUNTIME_SHADOWS = (
    *INSTALLED,
    "aegis_foundation",
    "plugins/gas-city-workflow",
    ".claude/scripts",
    "sitecustomize.py",
    "usercustomize.py",
    # ga-4p6f: the canonical executor runs these from the target when they exist
    # (workflow.py checkpoint, verify and finish), so a registered target that
    # carries either would supply unreviewed code to an approved command.
    "scripts/codex-task",
    "scripts/codex-guard",
)


def reviewed_registered_target(target: Path, canonical: Path) -> None:
    """A registered foreign target never supplies runtime (ga-fsfg R2).

    The canonical executor is verified exactly as for an Operations target; the
    foreign worktree must carry no Operations runtime tree, installed runtime or
    Python startup hook that could shadow it.
    """

    _source_only_loading()
    algorithm, manifest = _manifest(canonical)
    _verify(canonical, algorithm, manifest)
    for relative in FOREIGN_RUNTIME_SHADOWS:
        path = target / relative
        if path.exists() or path.is_symlink():
            raise ValueError("registered target must not carry an Operations runtime tree")
