"""Read-only parity for tracked daily sessions and the Aegis logging envelope."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from .state import plan_bead_ids, plan_branch_policies, text_references_work


class SessionAuthorityError(ValueError):
    """Contradictory authority must be resolved before a writer starts."""


def contained_path(root: Path, value: object, label: str, *, leaf_link: bool = False) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise SessionAuthorityError(f"{label} must be a relative path")
    parts = value.split("/")
    if any(p in {"", ".", ".."} for p in parts):
        raise SessionAuthorityError(f"{label} escapes the worktree")
    path = root
    for index, part in enumerate(parts):
        path = path / part
        if path.is_symlink() and not (leaf_link and index == len(parts) - 1):
            raise SessionAuthorityError(f"{label} contains a symlink")
    return path


def assert_no_pending_continuation(root: Path) -> None:
    path = contained_path(root, ".aegis/state/session-continuation.json", "session transaction")
    if not path.exists() and not path.is_symlink():
        return
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise SessionAuthorityError("session continuation journal is unreadable") from exc
    if not isinstance(payload, dict) or payload.get("status") not in {"complete", "rolled_back"}:
        raise SessionAuthorityError("session continuation is pending; preserve and reconcile it")
    identity = payload.get("id")
    if (payload.get("schema") != "aegis.session-continuation.v1"
            or not isinstance(identity, str) or len(identity) != 32
            or any(c not in "0123456789abcdef" for c in identity)):
        raise SessionAuthorityError("session continuation journal identity is invalid")


def verify_session_authority(root: Path, work: Mapping, *, during_transition: bool = False) -> tuple[Path, Path]:
    """Validate the same pointer/envelope contract for logging and readiness.

    This grants no permission and performs no recovery, file write, or command.
    Existing branch, ownership, plan/tracker, and permission gates remain required.
    """
    root = root.resolve()
    contained_path(root, ".aegis/state/current-work.json", "session envelope")
    if not during_transition:
        assert_no_pending_continuation(root)
    if not isinstance(work, Mapping) or not isinstance(work.get("paths"), Mapping):
        raise SessionAuthorityError("session authority envelope is invalid")
    recovery = work.get("recovery")
    if isinstance(recovery, Mapping) and recovery.get("kind") == "tracked-source-lifecycle":
        core = {k: v for k, v in work.items() if k not in {"created_at", "updated_at", "recovery"}}
        fingerprint = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if recovery.get("fingerprint") != fingerprint:
            raise SessionAuthorityError("session envelope recovery fingerprint disagrees")
    paths = work["paths"]
    resolved = {}
    for name, directory in (("session", "sessions"), ("plan", "plans")):
        declared = contained_path(root, paths.get(name), f"current-work {name}")
        link = contained_path(root, paths.get(name + "_current", directory + "/current"),
                              f"{name} pointer", leaf_link=True)
        if not declared.is_file() or not link.is_symlink():
            raise SessionAuthorityError(f"{name} authority file or pointer is missing")
        try:
            target = link.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise SessionAuthorityError(f"{name} pointer is broken") from exc
        if target != declared or not target.is_relative_to(root):
            raise SessionAuthorityError(f"current-work {name} disagrees with tracked {name} pointer")
        resolved[name] = declared
        if name == "session":
            state_path = contained_path(
                root, (link.parent / "state.json").relative_to(root).as_posix(), "session state"
            )
            try:
                state = json.loads(state_path.read_text())
            except (OSError, ValueError) as exc:
                raise SessionAuthorityError("session state is missing or invalid") from exc
            if not isinstance(state, dict) or state.get("current") != declared.name:
                raise SessionAuthorityError("session state disagrees with tracked session pointer")
    task = work.get("task")
    if not isinstance(task, Mapping) or not isinstance(task.get("id"), str) or not task["id"]:
        raise SessionAuthorityError("session authority task identity is missing")
    if work.get("mode") == "bead":
        bead = task["id"]
        if not text_references_work(resolved["session"].read_text(), bead):
            raise SessionAuthorityError("session belongs to a different Bead")
        plan = resolved["plan"].read_text()
        if bead not in plan_bead_ids(plan):
            raise SessionAuthorityError("plan belongs to a different Bead")
        branch_record = work.get("branch")
        if not isinstance(branch_record, Mapping):
            raise SessionAuthorityError("session branch identity is missing")
        branch = branch_record.get("current")
        if branch and plan_branch_policies(plan) != {branch}:
            raise SessionAuthorityError("plan branch disagrees with current-work authority")
    return resolved["session"], resolved["plan"]
