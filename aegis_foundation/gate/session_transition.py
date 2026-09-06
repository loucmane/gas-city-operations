"""Bounded daily-session transaction; before/after images survive failure."""
from __future__ import annotations

import base64
import contextlib
import fcntl
import functools
import json
import os
import stat
import tempfile
import uuid
from pathlib import Path

from .session_authority import (
    SessionAuthorityError, assert_no_pending_continuation, contained_path,
)

JOURNAL = ".aegis/state/session-continuation.json"
SCHEMA = "aegis.session-continuation.v1"


@contextlib.contextmanager
def session_lock(root: Path, *, shared: bool = False):
    """Lock the existing directory inode: no pre-refusal filesystem writes."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SessionAuthorityError("session authority is in use; retry after the writer finishes") from exc
        yield
    finally:
        os.close(fd)


def serialized_session_writer(function):
    @functools.wraps(function)
    def wrapped(target_dir, *args, **kwargs):
        with session_lock(Path(target_dir).expanduser().resolve()):
            return function(target_dir, *args, **kwargs)
    return wrapped


def image(path: Path) -> dict:
    if path.is_symlink():
        info = path.lstat()
        return {"kind": "link", "target": os.readlink(path), "uid": info.st_uid, "gid": info.st_gid}
    if not path.exists():
        return {"kind": "absent"}
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise SessionAuthorityError(f"session transaction refuses special file: {path}")
    return {"kind": "file", "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            "mode": stat.S_IMODE(info.st_mode), "uid": info.st_uid, "gid": info.st_gid}


def _install(path: Path, value: dict) -> None:
    """Atomic leaf replacement, preserving exact bytes and mode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if value["kind"] == "absent":
        if path.exists() or path.is_symlink():
            path.unlink()
        return
    fd, name = tempfile.mkstemp(prefix=".session-txn-", dir=path.parent)
    temporary = Path(name)
    try:
        if value["kind"] == "file":
            with os.fdopen(fd, "wb") as stream:
                stream.write(base64.b64decode(value["data"], validate=True))
                stream.flush()
                os.fchmod(stream.fileno(), value["mode"])
                if (os.fstat(stream.fileno()).st_uid, os.fstat(stream.fileno()).st_gid) != (value["uid"], value["gid"]):
                    os.fchown(stream.fileno(), value["uid"], value["gid"])
                os.fsync(stream.fileno())
        elif value["kind"] == "link":
            os.close(fd)
            temporary.unlink()
            temporary.symlink_to(value["target"])
            if (temporary.lstat().st_uid, temporary.lstat().st_gid) != (value["uid"], value["gid"]):
                os.lchown(temporary, value["uid"], value["gid"])
        else:
            os.close(fd)
            raise SessionAuthorityError("invalid session transaction image")
        os.replace(temporary, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _json_image(payload: dict) -> dict:
    return {"kind": "file", "data": base64.b64encode(
        (json.dumps(payload, indent=2) + "\n").encode()).decode(),
        "mode": 0o600, "uid": os.getuid(), "gid": os.getgid()}


class SessionTransition:
    """Only caller-declared session surfaces may be written, each with a WAL image."""

    def __init__(self, root: Path, bead: str, paths: list[Path], *, lock_held: bool = False):
        self.root = root.resolve()
        self.lock_held = lock_held
        self.bead = bead
        self.allowed = {p.relative_to(self.root).as_posix() for p in paths}
        self.record = {"schema": SCHEMA, "id": uuid.uuid4().hex, "bead": bead,
                       "status": "pending", "steps": []}
        self.before = {}
        self.created_directories = set()
        for relative in sorted(self.allowed):
            path = contained_path(self.root, relative, "session target", leaf_link=True)
            self.before[relative] = image(path)
            parent = path.parent
            while parent != self.root and not parent.exists():
                self.created_directories.add(parent.relative_to(self.root).as_posix())
                parent = parent.parent
        self.record["created_directories"] = sorted(self.created_directories)

    def __enter__(self):
        self.lock = contextlib.nullcontext() if self.lock_held else session_lock(self.root)
        self.lock.__enter__()
        try:
            assert_no_pending_continuation(self.root)
            for relative, before in self.before.items():
                if image(self.root / relative) != before:
                    raise SessionAuthorityError("session target changed before transaction")
            journal = contained_path(self.root, JOURNAL, "session journal")
            if journal.exists():
                prior = json.loads(journal.read_text())
                self._archive(prior)
            self._save()
            return self
        except BaseException:
            self.lock.__exit__(None, None, None)
            raise

    def _save(self):
        path = contained_path(self.root, JOURNAL, "session journal")
        _install(path, _json_image(self.record))

    def _archive(self, record):
        identity = record.get("id", "")
        if not isinstance(identity, str) or len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
            raise SessionAuthorityError("invalid previous session transaction identity")
        relative = f".aegis/state/session-continuations/{identity}.json"
        path = contained_path(self.root, relative, "session archive")
        expected = _json_image(record)
        if path.exists():
            if image(path) != expected:
                raise SessionAuthorityError("session transaction archive disagrees")
        else:
            _install(path, expected)

    def _change(self, path: Path, after: dict):
        relative = path.relative_to(self.root).as_posix()
        contained_path(self.root, relative, "session target", leaf_link=True)
        if relative not in self.allowed or any(s["path"] == relative for s in self.record["steps"]):
            raise SessionAuthorityError("session transaction target is outside its single-write contract")
        before = self.before[relative]
        if image(path) != before:
            raise SessionAuthorityError("session target changed during transaction")
        self.record["steps"].append({"path": relative, "before": before, "after": after})
        self._save()  # Write-ahead: even a crash after replace has both exact images.
        _install(path, after)
        if image(path) != after:
            raise SessionAuthorityError("session transaction readback failed")

    def write(self, path: Path, data: bytes):
        before = self.before[path.relative_to(self.root).as_posix()]
        if before["kind"] not in {"file", "absent"}:
            raise SessionAuthorityError("session file cannot replace a symlink")
        self._change(path, {"kind": "file", "data": base64.b64encode(data).decode(),
                           "mode": before.get("mode", 0o644),
                           "uid": before.get("uid", os.getuid()), "gid": before.get("gid", os.getgid())})

    def link(self, path: Path, target: Path):
        self._change(path, {"kind": "link", "target": os.path.relpath(target, path.parent),
                           "uid": os.getuid(), "gid": os.getgid()})

    def rollback(self):
        # Precheck ALL images before restoring any: ambiguous concurrent writes survive.
        for step in self.record["steps"]:
            path = contained_path(self.root, step["path"], "rollback target", leaf_link=True)
            current = image(path)
            if current not in (step["before"], step["after"]):
                raise SessionAuthorityError("session rollback refused: ambiguous target mutation")
        for step in reversed(self.record["steps"]):
            _install(self.root / step["path"], step["before"])
            if image(self.root / step["path"]) != step["before"]:
                raise SessionAuthorityError("session rollback readback failed")
        for relative in sorted(self.created_directories, key=lambda p: p.count("/"), reverse=True):
            path = contained_path(self.root, relative, "rollback directory")
            if path.exists():
                path.rmdir()  # Only an empty directory proven absent before this attempt.
        self.record["status"] = "rolled_back"
        self._save()

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is not None:
                try:
                    self.rollback()
                except Exception as rollback_error:
                    raise SessionAuthorityError(
                        f"session continuation failed and rollback is unresolved: {rollback_error}"
                    ) from exc
            else:
                self.record["status"] = "complete"
                try:
                    self._save()
                except Exception as commit_error:
                    try:
                        self.rollback()
                    except Exception as rollback_error:
                        raise SessionAuthorityError(
                            f"session commit failed and rollback is unresolved: {rollback_error}"
                        ) from commit_error
                    raise
        finally:
            self.lock.__exit__(None, None, None)
        return False
