"""Content-addressed Bead snapshots for workflow journals (ga-fsfg R1).

Coordination records used to embed full Bead snapshots, so a busy journal grew
past the stationary gate's 1 MiB bound. Snapshots now live beside the journal as
content-addressed files and the journal keeps a reference. Every reader resolves
through this module, so inline legacy snapshots keep working unchanged, and a
supported compaction moves verified inline snapshots out-of-line idempotently.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from workflow_common import WorkflowError, atomic_write_json
from workflow_ownership import bead_digest

REFERENCE_KEY = "$snapshot"
SNAPSHOT_FIELDS = ("before", "blocker_before", "after")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_SNAPSHOT_BOUND = 16 * 1024 * 1024


def snapshot_dir(journal_path: Path) -> Path:
    return journal_path.with_name(f"{journal_path.stem}.snapshots")


def is_reference(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {REFERENCE_KEY}
        and isinstance(value[REFERENCE_KEY], str)
        and bool(_DIGEST.fullmatch(value[REFERENCE_KEY]))
    )


def store_snapshot(journal_path: Path, bead: Mapping[str, Any]) -> dict[str, str]:
    """Persist one Bead snapshot content-addressed by its digest; idempotent."""

    if is_reference(bead):
        return dict(bead)
    if not isinstance(bead, Mapping):
        raise WorkflowError("snapshot requires a Bead object")
    digest = bead_digest(bead)
    directory = snapshot_dir(journal_path)
    path = directory / f"{digest}.json"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise WorkflowError("snapshot path is not a regular file")
    if path.is_file():
        if bead_digest(_load(path)) != digest:
            raise WorkflowError("existing snapshot does not match its digest")
        return {REFERENCE_KEY: digest}
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write_json(path, bead)
    if bead_digest(_load(path)) != digest:
        raise WorkflowError("snapshot readback does not match its digest")
    return {REFERENCE_KEY: digest}


def resolve_snapshot(journal_path: Path, value: Any) -> Any:
    """Return the Bead object for an inline snapshot or a reference."""

    if not is_reference(value):
        return value
    digest = value[REFERENCE_KEY]
    path = snapshot_dir(journal_path) / f"{digest}.json"
    if path.is_symlink() or not path.is_file():
        raise WorkflowError(f"coordination snapshot {digest[:12]} is missing")
    bead = _load(path)
    if bead_digest(bead) != digest:
        raise WorkflowError(f"coordination snapshot {digest[:12]} is corrupt")
    return bead


def resolve_record(journal_path: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a coordination record with every snapshot field resolved."""

    resolved = dict(record)
    for field in SNAPSHOT_FIELDS:
        if field in resolved:
            resolved[field] = resolve_snapshot(journal_path, resolved[field])
    return resolved


def compact_records(journal_path: Path, journal: Mapping[str, Any]) -> int:
    """Move verified inline snapshots out-of-line; return the number moved.

    Pending intents keep their inline snapshots: they are still the exact preimage
    a later verification or reconciliation compares against.
    """

    operations = journal.get("coordination", {})
    if not isinstance(operations, dict):
        raise WorkflowError("invalid coordination journal")
    moved = 0
    for record in operations.values():
        if not isinstance(record, dict) or record.get("state") != "verified":
            continue
        for field in SNAPSHOT_FIELDS:
            value = record.get(field)
            if isinstance(value, Mapping) and not is_reference(value):
                record[field] = store_snapshot(journal_path, value)
                moved += 1
    return moved


def _load(path: Path) -> Any:
    if path.stat().st_size > _SNAPSHOT_BOUND:
        raise WorkflowError("snapshot exceeds bounds")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkflowError(f"snapshot is unreadable: {path.name}") from exc
