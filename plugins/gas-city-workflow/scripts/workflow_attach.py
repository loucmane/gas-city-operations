#!/usr/bin/env python3
"""Attach one declared blocking bead to the current source-work context."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping

from project_context import DEFAULT_REGISTRY, build_context
from _repo_structure import load_repo_structure
from workflow_common import (
    CommandRunner,
    WorkflowError,
    active_bead_id,
    atomic_write_json,
    is_blocking_dependency,
    load_bead,
    journal_path,
    load_journal,
    plan_bead_ids,
    record_lifecycle_event,
    require_bead_ready,
    result_payload,
    run_readiness,
)
from workflow_ownership import check_active_ownership, ensure_external_owner


def _dependency_ids(bead: Mapping[str, Any]) -> set[str]:
    return {
        str(item.get("id") or item.get("depends_on_id") or "")
        for item in bead.get("dependencies", [])
        if isinstance(item, Mapping) and is_blocking_dependency(item)
    } - {""}


def _atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _current_plan(root: Path) -> Path:
    link = load_repo_structure(root).current_plan_link
    if not link.is_symlink():
        raise WorkflowError("plans/current is not a symlink")
    try:
        target = link.resolve(strict=True)
    except OSError as exc:
        raise WorkflowError("plans/current is broken") from exc
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise WorkflowError("plans/current escapes the project root") from exc
    if not target.is_file() or target.is_symlink():
        raise WorkflowError("current plan target is not a regular file")
    return target


def _active_tracker(root: Path, primary_bead: str) -> Path:
    active = load_repo_structure(root).work_tracking_active_root
    matches = sorted(
        item
        for item in active.glob("*-ACTIVE")
        if item.is_dir() and not item.is_symlink() and f"-{primary_bead}-" in item.name
    )
    if len(matches) != 1:
        raise WorkflowError(
            f"expected one active tracker for {primary_bead}; found {[item.name for item in matches]}"
        )
    tracker = matches[0] / "TRACKER.md"
    if not tracker.is_file() or tracker.is_symlink():
        raise WorkflowError("active TRACKER.md is not a regular file")
    return tracker


def _attached_bead_ids(text: str) -> list[str]:
    matches = re.findall(r"^attached_bead_ids:\s*\[([^\]]*)\]\s*$", text, re.MULTILINE)
    if not matches:
        return []
    if len(matches) != 1:
        raise WorkflowError("current plan contains multiple attached bead lists")
    return [item.strip() for item in matches[0].split(",") if item.strip()]


def _attach_to_plan(plan: Path, primary_bead: str, bead_id: str) -> list[str]:
    text = plan.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^bead_ids:\s*\[([^\]]+)\]\s*$", text, re.MULTILINE))
    if len(matches) != 1:
        raise WorkflowError("current plan does not identify one bead list")
    primary_ids = [item.strip() for item in matches[0].group(1).split(",")]
    if not primary_ids or primary_ids[0] != primary_bead:
        raise WorkflowError("current plan primary bead does not match active work")
    unexpected = [item for item in primary_ids[1:] if item != bead_id]
    if unexpected:
        raise WorkflowError("current plan contains an unrelated secondary primary bead")
    attached = _attached_bead_ids(text)
    if bead_id not in attached:
        attached.append(bead_id)
    replacement = f"bead_ids: [{primary_bead}]\n" f"attached_bead_ids: [{', '.join(attached)}]"
    if re.search(r"^attached_bead_ids:", text, re.MULTILINE):
        text = re.sub(r"^attached_bead_ids:\s*\[[^\]]*\]\s*\n?", "", text, flags=re.MULTILINE)
        matches = list(re.finditer(r"^bead_ids:\s*\[([^\]]+)\]\s*$", text, re.MULTILINE))
    updated = text[: matches[0].start()] + replacement + text[matches[0].end() :]
    _atomic_write_text(plan, updated)
    return attached


def _attach_to_tracker(tracker: Path, bead_id: str, title: str) -> None:
    text = tracker.read_text(encoding="utf-8")
    marker = f"- `{bead_id}` — {title}"
    if marker in text:
        return
    section = "\n## Attached Blocking Beads\n\n" + marker + "\n"
    _atomic_write_text(tracker, text.rstrip() + "\n" + section)


def attach(
    root: Path,
    bead_id: str,
    runner: CommandRunner | None = None,
    *,
    registry: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    runner = runner or CommandRunner()
    context = build_context(root, registry)
    root = Path(context["project"]["root"])
    primary_id = active_bead_id(root)
    if bead_id == primary_id:
        raise WorkflowError("the requested bead is already the primary active bead")
    spec = check_active_ownership(runner, root, registry=registry, attaching=bead_id)
    primary = load_bead(runner, context, primary_id)
    if bead_id not in _dependency_ids(primary):
        raise WorkflowError(f"{bead_id} is not a declared dependency of active bead {primary_id}")
    plan = _current_plan(root)
    tracker = _active_tracker(root, primary_id)
    require_bead_ready(load_bead(runner, context, bead_id))
    path = journal_path(runner, spec)
    state = load_journal(path)
    if state is None:
        raise WorkflowError("active ownership journal is missing")
    attached = ensure_external_owner(runner, spec, context, state, path, bead_id=bead_id)
    attached_beads = _attach_to_plan(plan, primary_id, bead_id)
    _attach_to_tracker(tracker, bead_id, str(attached.get("title") or bead_id))
    if plan_bead_ids(root) != [primary_id]:
        raise WorkflowError("current plan primary bead readback mismatch")
    if _attached_bead_ids(plan.read_text(encoding="utf-8")) != attached_beads:
        raise WorkflowError("current plan attached bead readback mismatch")
    # Portable readiness checks plan/journal parity. Persist the already-verified
    # membership first; the enclosing coordination intent stays pending until
    # readiness and fresh ownership checks pass. Never replay Bead writes on failure.
    state["attached_bead_ids"] = attached_beads
    atomic_write_json(path, state)
    readiness = run_readiness(runner, root)
    if "STATE: READY" not in readiness:
        raise WorkflowError("readiness succeeded without a READY state")
    check_active_ownership(runner, root, registry=registry)
    journal = record_lifecycle_event(
        runner,
        root,
        "attach",
        "ready",
        bound_bead_id=primary_id,
        attached_bead_id=bead_id,
    )
    return result_payload(
        "attach",
        "ready",
        primary_bead_id=primary_id,
        attached_bead_id=bead_id,
        bead_ids=[primary_id],
        attached_bead_ids=attached_beads,
        plan=plan.as_posix(),
        tracker=tracker.as_posix(),
        journal=journal.as_posix(),
    )
