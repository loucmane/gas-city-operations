"""Create-only bindings from an approved delivery call to its worktree (ga-fsfg R3).

PreToolUse writes one binding after every delivery check has passed; PostToolUse
looks up its own call's binding to find the worktree, and PostToolUseFailure
removes it. A binding never approves anything: nothing reads one to decide an
approval. Every file operation is relative to the binding directory's descriptor,
opened component by component without following a symlink.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import stat
import time
from pathlib import Path
from typing import Any

from .contracts import Payload
from .decisions import payload_digest
from .delivery_grammar import OPERATIONS, canonical_absolute

BINDING_PARTS = (".aegis", "state", "delivery-bindings")
BINDING_SCHEMA = "aegis.delivery-binding.v1"
EXPIRY_SECONDS = 30 * 60
MAX_BINDINGS = 16
MAX_BINDING_BYTES = 4096
LOCK_WAIT_SECONDS = 5.0
wall_clock = time.time
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class BindingError(ValueError):
    """The binding store refused an operation."""


def binding_name(payload: Payload) -> str:
    """sha256 of the session id, the hook's tool_use_id and the request digest."""

    if not payload.session_id or not payload.tool_use_id:
        raise BindingError("a delivery binding needs a session id and a tool_use_id")
    material = json.dumps(
        [payload.session_id, payload.tool_use_id, payload_digest(payload)], separators=(",", ":")
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest() + ".json"


def _open_part(parent: int, part: str, *, create: bool) -> int | None:
    try:
        return os.open(part, DIRECTORY_FLAGS, dir_fd=parent)
    except FileNotFoundError:
        if not create:
            return None
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise BindingError("the delivery binding directory is not a real directory") from exc
        raise
    try:
        os.mkdir(part, 0o700 if part == BINDING_PARTS[-1] else 0o755, dir_fd=parent)
    except FileExistsError:
        pass
    return _open_part(parent, part, create=False)


def _open_directory(root: Path, *, create: bool) -> int | None:
    """The binding directory under the canonical root's gate state, never via a symlink."""

    fd = os.open(root, DIRECTORY_FLAGS)
    try:
        for part in BINDING_PARTS:
            child = _open_part(fd, part, create=create)
            if child is None:
                return None
            os.close(fd)
            fd = child
        opened, fd = fd, -1
        return opened
    finally:
        if fd >= 0:
            os.close(fd)


def _lock(fd: int) -> None:
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() > deadline:
                raise BindingError("the delivery binding directory is locked") from None
            time.sleep(0.02)


def _load(fd: int, name: str, now: float) -> dict[str, Any] | None:
    """One binding record, or None when it does not exist.

    A symlink, special or oversized file refuses. A malformed record, or one dated in
    the future, is marked invalid and ages out by its modification time.
    """

    try:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BINDING_BYTES:
        raise BindingError("a delivery binding is not a small regular file")
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
    try:
        raw = os.read(handle, MAX_BINDING_BYTES + 1)
    finally:
        os.close(handle)
    try:
        record = json.loads(raw)
    except ValueError:
        record = None
    if (
        not isinstance(record, dict)
        or set(record) != {"schema", "operation", "worktree", "created"}
        or record["schema"] != BINDING_SCHEMA
        or record["operation"] not in OPERATIONS
        or not canonical_absolute(record["worktree"])
        or not isinstance(record["created"], (int, float))
        or isinstance(record["created"], bool)
        or record["created"] > now + 300
    ):
        return {"invalid": True, "created": min(info.st_mtime, now)}
    return record


def _expired(record: dict[str, Any], now: float) -> bool:
    return now - float(record["created"]) >= EXPIRY_SECONDS


def _live(fd: int, now: float) -> list[dict[str, Any]]:
    """Prune expired records; refuse symlinks and special files; return the rest."""

    live = []
    with os.scandir(fd) as entries:
        names = [entry.name for entry in entries]
    for name in names:
        record = _load(fd, name, now)
        if record is None:
            continue
        if _expired(record, now):
            os.unlink(name, dir_fd=fd)
            continue
        if record.get("invalid"):
            raise BindingError("the delivery binding store holds an invalid record")
        live.append(record)
    return live


def live_binding_for(root: Path, worktree: Path) -> bool:
    """Whether an unexpired binding names the worktree (an early, read-only check)."""

    fd = _open_directory(root, create=False)
    if fd is None:
        return False
    try:
        now = wall_clock()
        with os.scandir(fd) as entries:
            names = [entry.name for entry in entries]
        for name in names:
            record = _load(fd, name, now)
            if record is not None and not _expired(record, now):
                if record.get("invalid") or record["worktree"] == str(worktree):
                    return True
        return False
    finally:
        os.close(fd)


def write_binding(root: Path, payload: Payload, worktree: Path, operation: str) -> str:
    """Create this call's binding under an exclusive lock, one per worktree, sixteen at most."""

    name = binding_name(payload)
    fd = _open_directory(root, create=True)
    assert fd is not None
    try:
        _lock(fd)
        now = wall_clock()
        live = _live(fd, now)
        if any(record["worktree"] == str(worktree) for record in live):
            raise BindingError("a delivery call for this worktree is still in flight")
        if len(live) >= MAX_BINDINGS:
            raise BindingError("too many unconsumed delivery bindings")
        data = json.dumps(
            {
                "schema": BINDING_SCHEMA,
                "operation": operation,
                "worktree": str(worktree),
                "created": now,
            },
            sort_keys=True,
        ).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        handle = os.open(name, flags, 0o600, dir_fd=fd)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(handle, view) :]
        finally:
            os.close(handle)
        return name
    finally:
        os.close(fd)


def prune_expired(root: Path) -> None:
    """Remove expired bindings; best effort, for every PreToolUse at a seat that has any."""

    if not (root / Path(*BINDING_PARTS)).is_dir():
        return
    fd = _open_directory(root, create=False)
    if fd is None:
        return
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # a delivery call holds the lock and prunes under it anyway
        now = wall_clock()
        with os.scandir(fd) as entries:
            names = [entry.name for entry in entries]
        for name in names:
            try:
                record = _load(fd, name, now)
            except BindingError:
                continue  # a symlink or special file stays and keeps refusing delivery
            if record is not None and _expired(record, now):
                os.unlink(name, dir_fd=fd)
    finally:
        os.close(fd)


def read_binding(root: Path, payload: Payload) -> dict[str, Any]:
    """This call's unexpired binding; a missing, expired or odd one refuses."""

    name = binding_name(payload)
    fd = _open_directory(root, create=False)
    if fd is None:
        raise BindingError("no delivery binding exists for this call")
    try:
        _lock(fd)
        now = wall_clock()
        record = _load(fd, name, now)
        if record is None:
            raise BindingError("no delivery binding exists for this call")
        if record.get("invalid"):
            raise BindingError("this call's delivery binding is invalid")
        if _expired(record, now):
            os.unlink(name, dir_fd=fd)
            raise BindingError("this call's delivery binding expired")
        return record
    finally:
        os.close(fd)


def remove_binding(root: Path, payload: Payload, *, required: bool = False) -> bool:
    """Remove this call's binding; with `required`, a missing one refuses."""

    if not payload.session_id or not payload.tool_use_id:
        if required:
            raise BindingError("a delivery binding needs a session id and a tool_use_id")
        return False
    name = binding_name(payload)
    fd = _open_directory(root, create=False)
    if fd is None:
        if required:
            raise BindingError("no delivery binding exists for this call")
        return False
    try:
        _lock(fd)
        if _load(fd, name, wall_clock()) is None:
            if required:
                raise BindingError("this call's delivery binding was already consumed")
            return False
        os.unlink(name, dir_fd=fd)
        return True
    finally:
        os.close(fd)
