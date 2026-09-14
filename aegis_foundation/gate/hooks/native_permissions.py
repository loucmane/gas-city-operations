"""Opt-in Claude approvals, issued only after the strict Aegis gate succeeds.

This is not another shell allowlist. It reuses the closed orchestrator grammar,
narrows it to the configured project/store, and never approves general Bash,
file tools, direct bd, delegation, publication, or lifecycle commands.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .contracts import Payload
from .delegation import DESCRIPTOR_NAME, _head_bound_bytes, resolve_managed_project
from .orchestrator import (
    CITY,
    CONTEXT_REL,
    MANAGED_BIN,
    SHELL_SYNTAX,
    WORKFLOW_REL,
    read_only_beads,
    read_only_context,
    trusted_bootstrap,
)
from .payloads import bash_command, shlex_tokens, strip_shell_prefixes
from .runtime_state import hook_invoking_agent

PROFILE = Path(".claude/orchestrator-command-profile.json")
SCHEMA = "aegis.claude-orchestrator-command-profile.v1"
COMMANDS = frozenset({"project-context", "beads-read", "workflow-begin", "workflow-coordinate"})
KEYS = {"schema", "project_id", "canonical_root", "worktree_root", "city", "rig", "commands"}
# ga-fsfg R2: optional registered projects whose direct-child worktrees the seat may
# coordinate. Each record must agree with the tracked canonical registry.
OPTIONAL_KEYS = {"registered_projects"}
REGISTERED_KEYS = {"id", "repository", "canonical_root", "worktree_root", "rig"}
MAX_REGISTERED = 16


def _validate_registered(
    entries: Any, canonical: Path, worktrees: Path
) -> list[dict[str, str]]:
    from .delegation import ID_PATTERN, REGISTRY_REL, REPOSITORY_PATTERN, _load_registry_path

    if not isinstance(entries, list) or len(entries) > MAX_REGISTERED:
        raise ValueError("invalid registered project list")
    registry, _raw = _load_registry_path(canonical / REGISTRY_REL)
    by_id = {item["id"]: item for item in registry}
    seen_ids: set[str] = set()
    seen_roots: set[Path] = set()
    validated: list[dict[str, str]] = []
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or set(entry) != REGISTERED_KEYS
            or not all(isinstance(item, str) and item for item in entry.values())
        ):
            raise ValueError("invalid registered project record")
        if (
            not ID_PATTERN.fullmatch(entry["id"])
            or not ID_PATTERN.fullmatch(entry["rig"])
            or not REPOSITORY_PATTERN.fullmatch(entry["repository"])
        ):
            raise ValueError("invalid registered project identity")
        croot = Path(entry["canonical_root"])
        wroot = Path(entry["worktree_root"])
        if (
            not croot.is_absolute()
            or croot.resolve() != croot
            or not wroot.is_absolute()
            or wroot.resolve() != wroot
            or croot == canonical
            or wroot == worktrees
            or wroot == croot
        ):
            raise ValueError("registered project roots are invalid")
        if entry["id"] in seen_ids or wroot in seen_roots:
            raise ValueError("duplicate registered project")
        seen_ids.add(entry["id"])
        seen_roots.add(wroot)
        item = by_id.get(entry["id"])
        if (
            item is None
            or item.get("root") != entry["canonical_root"]
            or item.get("worktree_root") != entry["worktree_root"]
            or item.get("rig") != entry["rig"]
            or item.get("repository") != entry["repository"]
        ):
            raise ValueError("registered project disagrees with the canonical registry")
        validated.append(dict(entry))
    return validated


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate command-profile field")
        result[key] = value
    return result


def _bound_bytes(root: Path, relative: Path, *, limit: int = 16384) -> bytes:
    path = root / relative
    if path.resolve() != path or path.stat().st_size > limit:
        raise ValueError("command profile/descriptor/runtime is aliased or oversized")
    return _head_bound_bytes(root, path, str(relative), reason="claude_command_profile_invalid")


def _profile(root: Path) -> dict[str, Any] | None:
    path = root / PROFILE
    if not path.exists() and not path.is_symlink():
        return None
    raw = _bound_bytes(root, PROFILE)
    value = json.loads(raw, object_pairs_hook=_unique_object)
    if (
        not isinstance(value, dict)
        or set(value) - OPTIONAL_KEYS != KEYS
        or value["schema"] != SCHEMA
    ):
        raise ValueError("invalid command-profile schema")
    if not all(isinstance(value[key], str) and value[key] for key in KEYS - {"commands"}):
        raise ValueError("invalid command-profile identity")
    commands = value["commands"]
    if (
        not isinstance(commands, list)
        or not commands
        or not all(isinstance(item, str) for item in commands)
        or len(set(commands)) != len(commands)
        or not set(commands) <= COMMANDS
    ):
        raise ValueError("invalid command-profile command set")
    project = resolve_managed_project(root)
    if project is None or project.project_id != value["project_id"]:
        raise ValueError("command profile does not bind a managed project")
    canonical = Path(value["canonical_root"])
    worktrees = Path(value["worktree_root"])
    if (
        not canonical.is_absolute()
        or canonical.resolve() != canonical
        or canonical != project.canonical_root
        or not worktrees.is_absolute()
        or worktrees.resolve() != worktrees
        or worktrees != canonical.parent / (canonical.name + "-worktrees")
        or root != project.worktree_root
        or (root != canonical and root.parent != worktrees)
        or value["city"] != CITY
    ):
        raise ValueError("command-profile repository, worktree, or city mismatch")
    # A task branch cannot grant itself new authority: the exact opt-in must also
    # be tracked and unchanged in the preserved canonical checkout.
    if _bound_bytes(canonical, PROFILE) != raw:
        raise ValueError("task command profile differs from canonical policy")
    descriptor = json.loads(
        _bound_bytes(root, Path(DESCRIPTOR_NAME)), object_pairs_hook=_unique_object
    )
    if descriptor.get("rig") != value["rig"]:
        raise ValueError("command-profile rig differs from the managed descriptor")
    if "registered_projects" in value:
        value["registered_projects"] = _validate_registered(
            value["registered_projects"], canonical, worktrees
        )
    return value


def _canonical_runtime(tokens: list[str], root: Path, canonical: Path, relative: Path) -> bool:
    script = Path(tokens[1])
    if not script.is_absolute():
        script = root / script
    if script != canonical / relative:
        return False
    _bound_bytes(canonical, relative, limit=1024 * 1024)
    # Approval never blesses an uncommitted replacement for an internal check or
    # an untracked Python module injected into the shared import path.
    state = subprocess.run(
        [
            "/usr/bin/git",
            "-C",
            str(canonical),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            "plugins/gas-city-workflow/scripts",
            "aegis_foundation",
            "scripts",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if state.returncode != 0 or state.stdout.strip():
        raise ValueError("canonical command runtime has unreviewed changes")
    return True


def native_permission(root: Path, payload: Payload) -> str | None:
    """Return a narrow approval kind, or defer to ordinary native permissions.

    Caller identity selects the output protocol only, never command authority.
    Profile/identity failures raise so the gate can refuse rather than approve.
    No recognized command is executed here.
    """
    if payload.tool_name != "Bash" or hook_invoking_agent(payload) != "claude":
        return None
    # Stationary commands retain the original payload/cwd for the request digest.
    # Only the explicitly validated workflow target receives task readiness/evidence.
    if payload.cwd and Path(payload.cwd) != root:
        from .coordination import KIND, target_for
        from .decisions import advisory_enabled

        seat = Path(payload.cwd)
        if target_for(seat, payload) == root:
            # An advisory seat is validated and audited but never handed a native
            # approval; Claude's ordinary permissions decide instead.
            return None if advisory_enabled(seat) else KIND
        return None
    profile_path = root / PROFILE
    if not profile_path.exists() and not profile_path.is_symlink():
        return None
    if not payload.cwd or Path(payload.cwd).resolve() != root:
        return None
    command = bash_command(payload)
    if SHELL_SYNTAX.search(command):
        return None
    tokens = strip_shell_prefixes(shlex_tokens(command))
    kind = None
    if read_only_context(tokens, root):
        kind = "project-context"
    elif tokens and tokens[0] == str(MANAGED_BIN / "gc") and read_only_beads(tokens):
        kind = "beads-read"
    elif (
        payload.permission_mode in {"default", "manual", "dontAsk", "acceptEdits", "auto"}
        and len(tokens) > 2
        and tokens[2] == "begin"
        and trusted_bootstrap(command, root)
    ):
        kind = "workflow-begin"
    if kind is None:
        return None  # Do not disrupt unrelated commands' existing permissions.
    profile = _profile(root)
    if profile is None:
        return None
    canonical = Path(profile["canonical_root"])
    if kind == "project-context" and not _canonical_runtime(tokens, root, canonical, CONTEXT_REL):
        return None
    if kind == "beads-read" and tokens[:6] != [
        str(MANAGED_BIN / "gc"),
        "--city",
        CITY,
        "--rig",
        profile["rig"],
        "bd",
    ]:
        return None
    if kind == "workflow-begin" and (
        root != canonical or not _canonical_runtime(tokens, root, canonical, WORKFLOW_REL)
    ):
        return None
    return kind if kind in profile["commands"] else None
