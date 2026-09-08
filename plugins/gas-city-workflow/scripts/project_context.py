#!/usr/bin/env python3
"""Render a deterministic, read-only Gas City project context capsule."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from root_policy import RootPolicyError, require_active_root  # noqa: E402
from _repo_structure import load_repo_structure  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = PLUGIN_ROOT / "config" / "projects.json"
DEFAULT_ROOT_POLICY = PLUGIN_ROOT / "config" / "root-policy.json"
DESCRIPTOR_NAME = ".gas-city-workflow.json"
REGISTRY_SCHEMA = "gas-city-workflow.project-registry.v1"
DESCRIPTOR_SCHEMA = "gas-city-workflow.project.v1"
CONTEXT_SCHEMA = "gas-city-workflow.project-context.v1"
try:
    _MANIFEST = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
except (OSError, json.JSONDecodeError):
    _MANIFEST = {}
PLUGIN_VERSION = str(_MANIFEST.get("version") or "unknown")
CITY = "/home/loucmane/gascity/city"
GC = "/home/loucmane/gascity/bin/gc"
BD = "/home/loucmane/gascity/bin/bd"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BASE_REF_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|refs/(?:heads|remotes)/[A-Za-z0-9._/-]+)$")
GITHUB_REMOTE_PATTERNS = (
    re.compile(r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$"),
    re.compile(r"^ssh://git@github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$"),
    re.compile(r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?/?$"),
)


class ContextError(RuntimeError):
    """Raised when project identity cannot be derived without guessing."""


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ContextError(f"{label} must be a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContextError(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContextError(f"{label} must contain a JSON object")
    return payload


def _validate_project(project: dict[str, Any], *, allow_root: bool) -> dict[str, Any]:
    expected = {
        "id",
        "repository",
        "rig",
        "workflow_authority",
        "workflow_profile",
    }
    optional = {"base_ref"}
    if allow_root:
        optional.update({"rig_root", "worktree_root"})
    if allow_root:
        expected.add("root")
    if not expected.issubset(project) or not set(project).issubset(expected | optional):
        allowed = sorted(expected | optional)
        raise ContextError(f"project keys must contain {sorted(expected)} and only {allowed}")
    project_id = project.get("id")
    rig = project.get("rig")
    repository = project.get("repository")
    if not isinstance(project_id, str) or not ID_PATTERN.fullmatch(project_id):
        raise ContextError("project id is invalid")
    if not isinstance(rig, str) or not ID_PATTERN.fullmatch(rig):
        raise ContextError("project rig is invalid")
    if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository):
        raise ContextError("project repository is invalid")
    if project.get("workflow_authority") != "beads":
        raise ContextError("workflow_authority must be beads")
    profile = project.get("workflow_profile")
    if profile not in {
        "beads-with-aegis-evidence",
        "beads-with-frozen-legacy-evidence",
    }:
        raise ContextError("workflow_profile is invalid")
    base_ref = project.get("base_ref")
    if base_ref is not None and (
        not isinstance(base_ref, str)
        or not BASE_REF_PATTERN.fullmatch(base_ref)
        or ".." in base_ref
        or "//" in base_ref
        or base_ref.endswith("/")
    ):
        raise ContextError("project base_ref is invalid")
    result: dict[str, Any] = {key: str(value) for key, value in project.items()}
    if allow_root:
        root_value = project.get("root")
        if not isinstance(root_value, str) or not Path(root_value).is_absolute():
            raise ContextError("registered project root must be absolute")
        worktree_root = project.get("worktree_root")
        if worktree_root is not None and (
            not isinstance(worktree_root, str) or not Path(worktree_root).is_absolute()
        ):
            raise ContextError("registered project worktree_root must be absolute")
        rig_root = project.get("rig_root")
        if rig_root is not None and (
            not isinstance(rig_root, str) or not Path(rig_root).is_absolute()
        ):
            raise ContextError("registered project rig_root must be absolute")
    return result


def _load_registry(path: Path) -> list[dict[str, Any]]:
    payload = _read_json_object(path, "project registry")
    if set(payload) != {"schema", "projects"} or payload.get("schema") != REGISTRY_SCHEMA:
        raise ContextError("project registry schema is invalid")
    projects = payload.get("projects")
    if not isinstance(projects, list):
        raise ContextError("project registry projects must be a list")
    validated = [
        _validate_project(project, allow_root=True)
        for project in projects
        if isinstance(project, dict)
    ]
    if len(validated) != len(projects):
        raise ContextError("project registry contains a non-object entry")
    roots = [project["root"] for project in validated]
    ids = [project["id"] for project in validated]
    if len(set(roots)) != len(roots) or len(set(ids)) != len(ids):
        raise ContextError("project registry roots and ids must be unique")
    worktree_roots = [
        project["worktree_root"] for project in validated if "worktree_root" in project
    ]
    if len(set(worktree_roots)) != len(worktree_roots):
        raise ContextError("project registry worktree roots must be unique")
    return validated


def _git(root: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip()


def _remote_repository(root: Path, expected: str) -> tuple[str | None, str]:
    code, remote = _git(root, "remote", "get-url", "origin")
    if code != 0 or not remote:
        return None, "unconfigured"
    repository = None
    for pattern in GITHUB_REMOTE_PATTERNS:
        match = pattern.fullmatch(remote)
        if match:
            repository = match.group("repo")
            break
    if repository is None:
        raise ContextError("origin is not a supported GitHub repository URL")
    if repository.casefold() != expected.casefold():
        raise ContextError(f"declared repository {expected} disagrees with origin {repository}")
    return repository, "exact"


def _resolve_git_root(requested: Path) -> Path:
    root = requested.expanduser().resolve()
    if not root.is_dir():
        raise ContextError(f"project root is not a directory: {root}")
    code, top = _git(root, "rev-parse", "--show-toplevel")
    if code != 0 or not top:
        raise ContextError(f"project root is not inside a Git worktree: {root}")
    resolved = Path(top).resolve()
    if resolved != root:
        raise ContextError(f"--root must name the Git worktree root exactly: {resolved}")
    return root


def _canonical_git_root(root: Path) -> Path:
    code, common_dir = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if code != 0 or not common_dir:
        raise ContextError("could not resolve the Git common directory")
    resolved = Path(common_dir).resolve()
    if resolved.name != ".git" or not resolved.is_dir():
        raise ContextError(f"Git common directory is not a normal checkout: {resolved}")
    canonical = resolved.parent.resolve()
    if not canonical.is_dir():
        raise ContextError(f"canonical Git checkout is not a directory: {canonical}")
    return canonical


def _default_worktree_root(canonical_root: Path) -> Path:
    return canonical_root.with_name(f"{canonical_root.name}-worktrees")


def _resolve_project(
    root: Path,
    canonical_root: Path,
    registry_path: Path,
) -> tuple[dict[str, str], str, dict[str, Any] | None]:
    descriptor_path = root / DESCRIPTOR_NAME
    descriptor: dict[str, str] | None = None
    if descriptor_path.exists():
        payload = _read_json_object(descriptor_path, "project descriptor")
        if payload.pop("schema", None) != DESCRIPTOR_SCHEMA:
            raise ContextError("project descriptor schema is invalid")
        descriptor = _validate_project(payload, allow_root=False)

    registry = _load_registry(registry_path)
    registered = next(
        (project for project in registry if Path(project["root"]).resolve() == canonical_root),
        None,
    )
    if registered is None and descriptor is not None:
        registered = next(
            (project for project in registry if project["id"] == descriptor["id"]),
            None,
        )
    if descriptor is not None and registered is not None:
        comparable = {
            key: value
            for key, value in registered.items()
            if key not in {"rig_root", "root", "worktree_root"}
        }
        if descriptor != comparable:
            raise ContextError("project descriptor disagrees with the central registry")
        return descriptor, "descriptor+registry", registered
    if descriptor is not None:
        return descriptor, "descriptor", None
    if registered is not None:
        return (
            {
                key: value
                for key, value in registered.items()
                if key not in {"rig_root", "root", "worktree_root"}
            },
            "registry",
            registered,
        )
    raise ContextError(
        f"project is not registered and has no {DESCRIPTOR_NAME}; onboard it before work"
    )


def _workspace_context(
    root: Path,
    canonical_root: Path,
    registered: dict[str, Any] | None,
) -> dict[str, Any]:
    if registered is not None:
        expected_canonical = Path(registered["root"]).resolve()
        if canonical_root != expected_canonical:
            raise ContextError(
                "canonical Git checkout disagrees with the central registry: "
                f"expected {expected_canonical}, observed {canonical_root}"
            )
        configured = registered.get("worktree_root")
        worktree_root = (
            Path(configured).resolve()
            if isinstance(configured, str)
            else _default_worktree_root(canonical_root)
        )
        policy_source = "registry" if configured is not None else "derived"
    else:
        worktree_root = _default_worktree_root(canonical_root)
        policy_source = "derived"

    if root == canonical_root:
        location = "canonical"
    elif root.parent == worktree_root:
        location = "linked-worktree"
    else:
        raise ContextError(
            "linked worktree is outside the approved worktree root: "
            f"expected a direct child of {worktree_root}, observed {root}"
        )
    return {
        "canonical_root": canonical_root.as_posix(),
        "worktree_root": worktree_root.as_posix(),
        "location": location,
        "policy_source": policy_source,
        "enforced": True,
    }


def _pointer_target(root: Path, relative: str) -> str | None:
    pointer = root / relative
    if not pointer.is_symlink():
        return None
    try:
        target = pointer.resolve(strict=True)
    except OSError:
        return "<broken>"
    try:
        return target.relative_to(root).as_posix()
    except ValueError:
        return "<outside-root>"


def build_context(root: Path, registry_path: Path) -> dict[str, Any]:
    if PLUGIN_VERSION == "unknown":
        raise ContextError("plugin manifest version is unavailable")
    root = _resolve_git_root(root)
    try:
        require_active_root(root, DEFAULT_ROOT_POLICY)
    except RootPolicyError as exc:
        raise ContextError(str(exc)) from exc
    canonical_root = _canonical_git_root(root)
    project, identity_source, registered = _resolve_project(
        root,
        canonical_root,
        registry_path.resolve(),
    )
    workspace = _workspace_context(root, canonical_root, registered)
    branch_code, branch = _git(root, "branch", "--show-current")
    head_code, head = _git(root, "rev-parse", "HEAD")
    status_code, status = _git(root, "status", "--porcelain=v1")
    if branch_code != 0 or head_code != 0 or status_code != 0:
        raise ContextError("could not read Git branch, head, or worktree status")
    remote_repository, remote_status = _remote_repository(root, str(project["repository"]))
    try:
        layout = load_repo_structure(root)
    except (OSError, ValueError) as exc:
        raise ContextError(f"invalid repository evidence layout: {exc}") from exc
    active_root = layout.work_tracking_active_root
    active = (
        sorted(
            path.name
            for path in active_root.iterdir()
            if path.is_dir() and path.name.endswith("-ACTIVE")
        )
        if active_root.is_dir()
        else []
    )
    readiness = (
        ".claude/scripts/readiness.sh"
        if (root / ".claude" / "scripts" / "readiness.sh").is_file()
        else None
    )
    lifecycle = (PLUGIN_ROOT / "scripts" / "workflow.py").as_posix()
    rig = project["rig"]
    return {
        "schema": CONTEXT_SCHEMA,
        "plugin_version": PLUGIN_VERSION,
        "project": {
            **project,
            "root": root.as_posix(),
            "identity_source": identity_source,
        },
        "workspace": workspace,
        "git": {
            "branch": branch or None,
            "head": head,
            "clean": not bool(status),
            "status_entries": len(status.splitlines()) if status else 0,
            "origin_repository": remote_repository,
            "origin_status": remote_status,
        },
        "workflow": {
            "authority": "beads",
            "city": CITY,
            "gc": GC,
            "bd": BD,
            "rig": rig,
            "readiness_entrypoint": readiness,
            "lifecycle_entrypoint": lifecycle,
            "plan_current": _pointer_target(root, layout.current_plan_link.relative_to(root).as_posix()),
            "session_current": _pointer_target(root, layout.current_session_link.relative_to(root).as_posix()),
            "active_trackers": active,
            "commands": {
                "ready": [GC, "--city", CITY, "--rig", rig, "bd", "ready"],
                "show": [GC, "--city", CITY, "--rig", rig, "bd", "show", "<bead-id>"],
                "begin": [
                    sys.executable,
                    lifecycle,
                    "begin",
                    "--root",
                    canonical_root.as_posix(),
                    "--bead",
                    "<bead-id>",
                ],
                "resume": [
                    sys.executable,
                    lifecycle,
                    "resume",
                    "--root",
                    root.as_posix(),
                ],
            },
        },
        "adapters": {
            "codex": {"instructions": "AGENTS.md", "present": (root / "AGENTS.md").is_file()},
            "fable": {"instructions": "CLAUDE.md", "present": (root / "CLAUDE.md").is_file()},
        },
        "permissions": {
            "mutates_project": False,
            "widens_permissions": False,
            "note": "Context generation performs only filesystem reads and read-only Git queries.",
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Exact Git worktree root")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Project registry JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and emit a compact PASS line",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        context = build_context(Path(args.root), Path(args.registry))
    except ContextError as exc:
        print(f"gas-city-workflow: BLOCKED: {exc}", file=sys.stderr)
        return 2
    if args.check:
        project = context["project"]
        print(
            "gas-city-workflow: PASS "
            f"project={project['id']} rig={project['rig']} "
            f"authority={project['workflow_authority']} permissions=unchanged "
            f"identity_source={project['identity_source']} "
            f"canonical_root={context['workspace']['canonical_root']} "
            f"worktree_root={context['workspace']['worktree_root']}"
        )
    else:
        print(json.dumps(context, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
