#!/usr/bin/env python3
"""Shared primitives for the modular Gas City workflow CLI."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from project_context import DEFAULT_REGISTRY, build_context

WORKFLOW_SCHEMA = "gas-city-workflow.transition.v1"
RESULT_SCHEMA = "gas-city-workflow.result.v1"
PHASES = ("planned", "worktree-created", "scaffolded", "claimed", "ready")
BEAD_PATTERN = re.compile(r"^[a-z][a-z0-9]*-[a-z0-9][a-z0-9-]*(?:\.[1-9][0-9]*)*$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NONBLOCKING_RELATIONSHIP_TYPES = frozenset({"parent-child", "relates-to", "tracks"})

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PLUGIN_ROOT.parent.parent
OPERATOR_PATH = "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin"


class WorkflowError(RuntimeError):
    """Raised when a workflow transition cannot proceed without guessing."""


class CommandRunner:
    """List-argv subprocess runner that is replaceable in focused tests."""

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            list(argv),
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise WorkflowError(
                f"command failed ({result.returncode}): {' '.join(argv)}"
                + (f": {detail}" if detail else "")
            )
        return result


@dataclass(frozen=True)
class BeginSpec:
    project_id: str
    rig: str
    workflow_profile: str
    canonical_root: str
    worktree_root: str
    bead_id: str
    title: str
    slug: str
    branch: str
    worktree: str
    base_commit: str

    def payload(self) -> dict[str, str]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug or not SLUG_PATTERN.fullmatch(slug):
        raise WorkflowError("could not derive a safe workflow slug")
    return slug[:64].rstrip("-")


def _git(
    runner: CommandRunner,
    root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return runner.run(["git", "-C", str(root), *args], check=check)


def git_value(runner: CommandRunner, root: Path, *args: str) -> str:
    return _git(runner, root, *args).stdout.strip()


def managed_environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"BEADS_DIR", "BEADS_DB"} and not key.startswith("BEADS_DOLT_SERVER_")
    }
    return {**env, "PATH": OPERATOR_PATH, "GC_HOME": "/home/loucmane/gascity/home"}


def workflow_runtime_root(registry: Path = DEFAULT_REGISTRY) -> Path:
    if (SOURCE_ROOT / "scripts" / "codex-task").is_file():
        return SOURCE_ROOT
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError("cannot resolve the canonical workflow runtime") from exc
    projects = payload.get("projects") if isinstance(payload, dict) else None
    matches = [
        item
        for item in projects or []
        if isinstance(item, dict) and item.get("id") == "gas-city-operations"
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("root"), str):
        raise WorkflowError("registry does not identify one Gas City Operations runtime")
    root = Path(str(matches[0]["root"])).resolve()
    if not (root / "scripts" / "codex-task").is_file():
        raise WorkflowError("canonical Gas City Operations runtime is unavailable")
    return root


def load_bead(
    runner: CommandRunner,
    context: Mapping[str, Any],
    bead_id: str,
) -> dict[str, Any]:
    if not BEAD_PATTERN.fullmatch(bead_id):
        raise WorkflowError(f"invalid bead id: {bead_id}")
    workflow = context["workflow"]
    result = runner.run(
        [
            str(workflow["gc"]),
            "--city",
            str(workflow["city"]),
            "--rig",
            str(workflow["rig"]),
            "bd",
            "show",
            bead_id,
            "--json",
        ],
        env=managed_environment(),
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise WorkflowError("bead readback returned invalid JSON") from exc
    if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
        bead = payload[0]
    elif isinstance(payload, dict):
        bead = payload
    else:
        raise WorkflowError("bead readback did not identify exactly one bead")
    if bead.get("id") != bead_id:
        raise WorkflowError("bead readback identity mismatch")
    return bead


def is_blocking_dependency(item: Mapping[str, Any]) -> bool:
    """Treat only known non-blocking relationships as informational.

    Missing and unknown relationship types remain blocking so an API/schema change cannot
    silently make real prerequisites startable.
    """

    relationship_type = str(item.get("dependency_type") or item.get("type") or "").strip()
    return relationship_type not in NONBLOCKING_RELATIONSHIP_TYPES


def require_bead_ready(bead: Mapping[str, Any]) -> None:
    status = str(bead.get("status") or "")
    if status not in {"open", "in_progress"}:
        raise WorkflowError(f"bead is not startable: status={status or 'unknown'}")
    open_dependencies = [
        str(item.get("id") or item.get("depends_on_id") or "<unknown>")
        for item in bead.get("dependencies", [])
        if (
            isinstance(item, Mapping)
            and str(item.get("status") or "closed") != "closed"
            and is_blocking_dependency(item)
        )
    ]
    if open_dependencies:
        raise WorkflowError(
            "bead has unresolved dependencies: " + ", ".join(sorted(open_dependencies))
        )


def derive_begin_spec(
    runner: CommandRunner,
    root: Path,
    bead_id: str,
    *,
    slug: str | None = None,
    registry: Path = DEFAULT_REGISTRY,
) -> tuple[BeginSpec, dict[str, Any], dict[str, Any]]:
    context = build_context(root, registry)
    bead = load_bead(runner, context, bead_id)
    require_bead_ready(bead)
    canonical = Path(context["workspace"]["canonical_root"])
    worktree_root = Path(context["workspace"]["worktree_root"])
    title = str(bead.get("title") or "").strip()
    if not title:
        raise WorkflowError("bead title is missing")
    normalized_slug = slugify(slug or title)
    if slug is not None and normalized_slug != slug:
        raise WorkflowError("explicit slug must already be normalized")
    configured_base = context["project"].get("base_ref")
    base_ref = str(configured_base) if configured_base is not None else "HEAD"
    base_commit = git_value(runner, canonical, "rev-parse", "--verify", f"{base_ref}^{{commit}}")
    branch = f"codex/{bead_id}-{normalized_slug}"
    worktree = worktree_root / f"{bead_id}-{normalized_slug}"
    spec = BeginSpec(
        project_id=str(context["project"]["id"]),
        rig=str(context["workflow"]["rig"]),
        workflow_profile=str(context["project"]["workflow_profile"]),
        canonical_root=canonical.as_posix(),
        worktree_root=worktree_root.as_posix(),
        bead_id=bead_id,
        title=title,
        slug=normalized_slug,
        branch=branch,
        worktree=worktree.as_posix(),
        base_commit=base_commit,
    )
    return spec, context, bead


def git_common_dir(runner: CommandRunner, canonical_root: Path) -> Path:
    value = git_value(
        runner,
        canonical_root,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
    )
    path = Path(value).resolve()
    if path.name != ".git" or not path.is_dir():
        raise WorkflowError(f"unsupported Git common directory: {path}")
    return path


def journal_path(runner: CommandRunner, spec: BeginSpec) -> Path:
    common = git_common_dir(runner, Path(spec.canonical_root))
    return common / "gas-city-workflow" / "transactions" / f"{spec.bead_id}.json"


def plan_bead_ids(root: Path) -> list[str]:
    plan = root / "plans" / "current"
    if not plan.is_symlink():
        raise WorkflowError("active session does not contain a valid bead id")
    try:
        plan_text = plan.resolve(strict=True).read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowError("plans/current is broken") from exc
    matches = re.findall(r"^bead_ids:\s*\[([^\]]+)\]\s*$", plan_text, re.MULTILINE)
    if len(matches) != 1:
        raise WorkflowError("current plan does not identify one bead list")
    bead_ids = [item.strip() for item in matches[0].split(",")]
    if (
        not bead_ids
        or len(bead_ids) != len(set(bead_ids))
        or any(not BEAD_PATTERN.fullmatch(item) for item in bead_ids)
    ):
        raise WorkflowError("current plan bead list is invalid")
    return bead_ids


def active_bead_id(root: Path) -> str:
    state = root / "sessions" / "state.json"
    if not state.is_file() or state.is_symlink():
        raise WorkflowError("sessions/state.json does not identify active work")
    try:
        payload = json.loads(state.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowError("sessions/state.json is invalid JSON") from exc
    task = payload.get("task") if isinstance(payload, dict) else None
    bead_id = task.get("id") if isinstance(task, dict) else None
    if isinstance(bead_id, str) and BEAD_PATTERN.fullmatch(bead_id):
        return bead_id
    return plan_bead_ids(root)[0]


def journal_path_for_root(runner: CommandRunner, root: Path, bead_id: str) -> Path:
    context = build_context(root, DEFAULT_REGISTRY)
    common = git_common_dir(runner, Path(context["workspace"]["canonical_root"]))
    return common / "gas-city-workflow" / "transactions" / f"{bead_id}.json"


def active_begin_spec(runner: CommandRunner, root: Path) -> BeginSpec:
    bead_id = active_bead_id(root)
    journal = load_journal(journal_path_for_root(runner, root, bead_id))
    if journal is None:
        raise WorkflowError("active work has no Gas City workflow transition journal")
    try:
        spec = BeginSpec(**journal["spec"])
    except (KeyError, TypeError) as exc:
        raise WorkflowError("active transition journal spec is invalid") from exc
    if Path(spec.worktree).resolve() != root.resolve():
        raise WorkflowError("active transition journal targets another worktree")
    return spec


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            os.chmod(temporary, 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_journal(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if not path.is_file() or path.is_symlink():
        raise WorkflowError(f"transition journal is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowError("transition journal contains invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != WORKFLOW_SCHEMA:
        raise WorkflowError("transition journal schema is invalid")
    if payload.get("phase") not in PHASES or not isinstance(payload.get("spec"), dict):
        raise WorkflowError("transition journal phase/spec is invalid")
    if not isinstance(payload.get("history"), list):
        raise WorkflowError("transition journal history is invalid")
    return payload


def initialize_journal(spec: BeginSpec) -> dict[str, Any]:
    timestamp = utc_now()
    return {
        "schema": WORKFLOW_SCHEMA,
        "phase": "planned",
        "spec": spec.payload(),
        "created_at": timestamp,
        "updated_at": timestamp,
        "history": [{"phase": "planned", "at": timestamp}],
    }


def advance_journal(journal: dict[str, Any], phase: str) -> None:
    current = str(journal["phase"])
    if PHASES.index(phase) < PHASES.index(current):
        raise WorkflowError(f"journal phase would regress: {current} -> {phase}")
    if phase == current:
        return
    timestamp = utc_now()
    journal["phase"] = phase
    journal["updated_at"] = timestamp
    journal["history"].append({"phase": phase, "at": timestamp})


def require_journal_spec(journal: Mapping[str, Any], spec: BeginSpec) -> None:
    if journal.get("spec") != spec.payload():
        raise WorkflowError("transition journal disagrees with live project/bead/workspace state")


def record_lifecycle_event(
    runner: CommandRunner,
    root: Path,
    action: str,
    status: str,
    *,
    bound_bead_id: str | None = None,
    **details: Any,
) -> Path:
    bead_id = bound_bead_id or active_bead_id(root)
    if not BEAD_PATTERN.fullmatch(bead_id):
        raise WorkflowError("lifecycle event bead id is invalid")
    path = journal_path_for_root(runner, root, bead_id)
    journal = load_journal(path)
    if journal is None:
        raise WorkflowError("active work has no Gas City workflow transition journal")
    expected = Path(str(journal["spec"].get("worktree", ""))).resolve()
    actual = Path(build_context(root, DEFAULT_REGISTRY)["project"]["root"]).resolve()
    if expected != actual:
        raise WorkflowError("active journal is bound to a different worktree")
    timestamp = utc_now()
    event = {"action": action, "status": status, "at": timestamp, **details}
    events = journal.setdefault("events", [])
    if not isinstance(events, list):
        raise WorkflowError("transition journal events are invalid")
    events.append(event)
    journal["updated_at"] = timestamp
    atomic_write_json(path, journal)
    return path


def result_payload(action: str, status: str, **details: Any) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "action": action,
        "status": status,
        "observed_at": utc_now(),
        **details,
    }


def readiness_command(root: Path) -> tuple[list[str], Path, dict[str, str] | None]:
    adapter = root / ".claude" / "scripts" / "readiness.sh"
    if adapter.is_file():
        return ["bash", str(adapter), "--root", str(root), "--all"], root, None
    runtime_root = workflow_runtime_root()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(runtime_root)
    return (
        [
            sys.executable,
            "-m",
            "aegis_foundation.gate.readiness",
            "--root",
            str(root),
            "--all",
        ],
        runtime_root,
        env,
    )


def run_readiness(runner: CommandRunner, root: Path) -> str:
    from workflow_portable import run_portable_readiness, uses_portable_scaffold

    if uses_portable_scaffold(root):
        return run_portable_readiness(runner, root)
    argv, cwd, env = readiness_command(root)
    return runner.run(argv, cwd=cwd, env=env).stdout
