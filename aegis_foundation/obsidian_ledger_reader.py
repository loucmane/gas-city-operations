"""Bounded, read-only reader for the passive Aegis event ledger."""

from __future__ import annotations

from aegis_foundation.git_read import run_git_read

import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
from typing import Any, Mapping

MAX_EVENTS = 200_000
MAX_SHARD_BYTES = 128 * 1024 * 1024
MAX_SQLITE_SNAPSHOT_BYTES = 256 * 1024 * 1024
MAX_SQLITE_SNAPSHOT_ATTEMPTS = 4
_FIELDS = (
    "schema_version",
    "event_id",
    "ts",
    "session_id",
    "repository_identity",
    "worktree_root",
    "branch",
    "head",
    "cwd",
    "event_type",
    "tool_name",
    "handler",
    "paths",
    "outcome",
    "exit_class",
    "duration_ms",
    "agent_id",
    "agent_type",
    "parent_agent_id",
    "payload_digest",
    "extra",
)


class LedgerReadError(RuntimeError):
    """Raised when ledger evidence cannot be read safely and completely."""


def _git_common_dir(target: Path) -> Path:
    result = run_git_read(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=target,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise LedgerReadError(f"target is not a Git repository: {target}")
    common = Path(result.stdout.strip())
    if not common.is_absolute():
        common = target / common
    return common.resolve()


def ledger_store(target: str | Path, env: Mapping[str, str] | None = None) -> Path:
    environment = env if env is not None else os.environ
    base = Path(
        environment.get("XDG_STATE_HOME")
        or (Path(environment.get("HOME") or Path.home()) / ".local" / "state")
    )
    key = hashlib.sha1(_git_common_dir(Path(target).resolve()).as_posix().encode()).hexdigest()
    return base / "aegis" / key


def _decode_row(row: tuple[Any, ...]) -> dict[str, Any]:
    event = dict(zip(_FIELDS, row, strict=True))
    for field, fallback in (("paths", []), ("extra", {})):
        raw = event.get(field)
        if isinstance(raw, str):
            try:
                event[field] = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise LedgerReadError(f"invalid ledger {field} JSON") from exc
        elif raw is None:
            event[field] = fallback
    return event


def _sqlite_events(path: Path, max_events: int) -> list[dict[str, Any]]:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error as exc:
        raise LedgerReadError(f"unable to open passive ledger: {exc}") from exc
    try:
        count = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        if count > max_events:
            raise LedgerReadError(f"ledger exceeds event limit ({count} > {max_events})")
        columns = ",".join(_FIELDS)
        return [
            _decode_row(tuple(row))
            for row in connection.execute(f"SELECT {columns} FROM events ORDER BY seq")
        ]
    except sqlite3.Error as exc:
        raise LedgerReadError(f"unable to read passive ledger: {exc}") from exc
    finally:
        connection.close()


def _file_signature(path: Path) -> tuple[int, int, int, int] | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise LedgerReadError(f"passive ledger component is not a regular file: {path.name}")
    return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_snapshot(path: Path, max_events: int) -> list[dict[str, Any]]:
    """Read a stable DB+WAL snapshot without granting ledger write access.

    SQLite WAL readers may need to create or update ``-shm`` coordination state. The
    reconciler deliberately runs with ``ProtectHome=read-only``, so opening the live
    ledger directly is not reliable while a writer has WAL state. Copy only the database
    and WAL into a private writable directory, prove that the source pair stayed
    byte-stable across the copy, and let SQLite rebuild transient ``-shm`` state there.
    """

    components = (path, Path(f"{path}-wal"))
    for _attempt in range(MAX_SQLITE_SNAPSHOT_ATTEMPTS):
        before = tuple(_file_signature(component) for component in components)
        if before[0] is None:
            raise LedgerReadError("passive ledger disappeared before snapshot")
        total_bytes = sum(item[2] for item in before if item is not None)
        if total_bytes > MAX_SQLITE_SNAPSHOT_BYTES:
            raise LedgerReadError(
                "passive SQLite ledger exceeds snapshot byte limit "
                f"({total_bytes} > {MAX_SQLITE_SNAPSHOT_BYTES})"
            )
        with tempfile.TemporaryDirectory(prefix="aegis-ledger-snapshot-") as temporary:
            snapshot = Path(temporary) / "ledger.db"
            copied_hashes: list[str | None] = []
            for source, signature in zip(components, before, strict=True):
                if signature is None:
                    copied_hashes.append(None)
                    continue
                destination = snapshot if source == path else Path(f"{snapshot}-wal")
                shutil.copyfile(source, destination)
                copied_hashes.append(_sha256(destination))
            after_copy = tuple(_file_signature(component) for component in components)
            if after_copy != before:
                continue
            source_hashes = tuple(
                _sha256(component) if signature is not None else None
                for component, signature in zip(components, after_copy, strict=True)
            )
            after_hash = tuple(_file_signature(component) for component in components)
            if after_hash != before or tuple(copied_hashes) != source_hashes:
                continue
            return _sqlite_events(snapshot, max_events)
    raise LedgerReadError(
        "passive SQLite ledger remained unstable across "
        f"{MAX_SQLITE_SNAPSHOT_ATTEMPTS} snapshot attempts"
    )


def _shard_events(path: Path, max_events: int) -> list[dict[str, Any]]:
    shards = sorted(path.glob("*.jsonl")) if path.is_dir() else []
    total_bytes = sum(item.stat().st_size for item in shards)
    if total_bytes > MAX_SHARD_BYTES:
        raise LedgerReadError(
            f"ledger shards exceed byte limit ({total_bytes} > {MAX_SHARD_BYTES})"
        )
    events: list[dict[str, Any]] = []
    for shard in shards:
        for number, line in enumerate(shard.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LedgerReadError(f"invalid ledger shard {shard.name}:{number}") from exc
            if not isinstance(value, dict):
                raise LedgerReadError(
                    f"ledger shard event must be an object: {shard.name}:{number}"
                )
            events.append(value)
            if len(events) > max_events:
                raise LedgerReadError(f"ledger exceeds event limit ({len(events)} > {max_events})")
    events.sort(key=lambda item: (str(item.get("ts") or ""), str(item.get("event_id") or "")))
    return events


def read_events(
    target: str | Path,
    *,
    env: Mapping[str, str] | None = None,
    max_events: int = MAX_EVENTS,
) -> list[dict[str, Any]]:
    store = ledger_store(target, env)
    database = store / "ledger.db"
    if database.is_file() and not database.is_symlink():
        return _sqlite_snapshot(database, max_events)
    return _shard_events(store / "shards", max_events)


__all__ = ["LedgerReadError", "ledger_store", "read_events"]
