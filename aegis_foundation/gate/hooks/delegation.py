"""Managed-project provider-native delegation policy.

Gas City is the delegation authority for managed projects.  This module is kept
inside the installed hook runtime so both Claude and Codex enforce the same
decision before a provider-native worker can be created or resumed.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import Payload
from .decisions import payload_digest


DESCRIPTOR_NAME = ".gas-city-workflow.json"
DESCRIPTOR_SCHEMA = "gas-city-workflow.project.v1"
REGISTRY_SCHEMA = "gas-city-workflow.project-registry.v1"
EXCEPTIONS_NAME = ".gas-city-delegation-exceptions.json"
EXCEPTIONS_SCHEMA = "gas-city.delegation-exceptions.v1"
REGISTRY_REL = Path("plugins/gas-city-workflow/config/projects.json")
RUNTIME_ENV_REL = Path(".aegis/runtime.env")
MAX_POLICY_BYTES = 1024 * 1024
MAX_EXCEPTIONS = 64

ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
BEAD_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(?:\.[0-9]+)*$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BASE_REF_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|refs/(?:heads|remotes)/[A-Za-z0-9._/-]+)$")
BRANCH_PATTERN = re.compile(r"^codex/[A-Za-z0-9._/-]+$")
REVIEW_REF_PATTERN = re.compile(
    r"^(?:[0-9a-f]{40}|refs/remotes/origin/[A-Za-z0-9._/-]+)$"
)
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REMOTE_PATTERNS = (
    re.compile(r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$"),
    re.compile(r"^ssh://git@github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$"),
    re.compile(r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?/?$"),
)

CLAUDE_DELEGATION_TOOLS = frozenset({"agent", "task"})
CODEX_DELEGATION_TOOLS = frozenset(
    {"spawn_agent", "assign_agent_task", "followup_task", "resume_agent"}
)
PROVIDER_NATIVE_DELEGATION_TOOLS = CLAUDE_DELEGATION_TOOLS | CODEX_DELEGATION_TOOLS

# ga-fsfg: a read-only reviewer is not a worker. One tracked agent definition that may
# hold only Read, Grep and Glob can be delegated to review exactly one candidate
# commit; every other provider-native delegation stays under Gas City routing.
REVIEWER_AGENT_TYPES = frozenset({"aegis-reviewer"})
REVIEWER_AGENTS_REL = Path(".claude/agents")
REVIEWER_TOOLS = frozenset({"Read", "Grep", "Glob"})
REVIEWER_INPUT_KEYS = frozenset({"description", "prompt", "subagent_type", "model"})
REVIEWER_PROMPT_BOUND = 65536
REVIEWER_REASON = "native_delegation_reviewer_invalid"
CANDIDATE_TOKEN = re.compile(r"(?<![0-9A-Za-z=_-])candidate=([0-9a-f]{40})(?![0-9A-Za-z])")
FRONTMATTER_FIELD = re.compile(r"^([a-z_]+):[ \t]*(.*?)[ \t]*$")


class DelegationPolicyError(RuntimeError):
    """A delegation policy decision could not be made safely."""

    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ManagedProject:
    project_id: str
    repository: str
    canonical_root: Path
    worktree_root: Path
    identity_source: str
    review_ref: str


@dataclass(frozen=True)
class DelegationVerdict:
    managed: bool
    allowed: bool
    reason: str
    request_sha256: str
    normalized_tool: str
    adapter: str
    project: ManagedProject | None


def normalize_delegation_tool(tool_name: str) -> str:
    """Normalize only the provider namespace, never the request body."""

    value = str(tool_name or "").strip().replace("__", ".")
    return value.rsplit(".", 1)[-1].lower()


def is_provider_native_delegation_tool(tool_name: str) -> bool:
    return normalize_delegation_tool(tool_name) in PROVIDER_NATIVE_DELEGATION_TOOLS


def _adapter_for_tool(normalized_tool: str) -> str:
    if normalized_tool in CLAUDE_DELEGATION_TOOLS:
        return "claude"
    if normalized_tool in CODEX_DELEGATION_TOOLS:
        return "codex"
    raise DelegationPolicyError("managed_project_context_invalid", "unsupported delegation tool")


def _git(root: Path, *args: str, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    )


def _git_text(root: Path, *args: str) -> str:
    result = _git(root, *args)
    if result.returncode != 0:
        detail = result.stderr.strip() if isinstance(result.stderr, str) else "git command failed"
        raise DelegationPolicyError("managed_project_context_invalid", detail or "git command failed")
    return str(result.stdout).strip()


def _worktree_and_canonical_root(root: Path) -> tuple[Path, Path]:
    requested = root.resolve()
    top = Path(_git_text(requested, "rev-parse", "--show-toplevel")).resolve()
    common = Path(
        _git_text(top, "rev-parse", "--path-format=absolute", "--git-common-dir")
    ).resolve()
    if common.name != ".git" or not common.is_dir():
        raise DelegationPolicyError(
            "managed_project_context_invalid",
            f"Git common directory is not a normal checkout: {common}",
        )
    canonical = common.parent.resolve()
    if not canonical.is_dir():
        raise DelegationPolicyError(
            "managed_project_context_invalid",
            f"canonical Git checkout is not a directory: {canonical}",
        )
    return top, canonical


def _regular_file_bytes(
    path: Path,
    label: str,
    *,
    reason: str = "managed_project_context_invalid",
) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise DelegationPolicyError(reason, f"{label} cannot be inspected: {exc}") from exc
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise DelegationPolicyError(reason, f"{label} must be a regular non-symlink file")
    if info.st_size > MAX_POLICY_BYTES:
        raise DelegationPolicyError(reason, f"{label} exceeds {MAX_POLICY_BYTES} bytes")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise DelegationPolicyError(reason, f"{label} cannot be read: {exc}") from exc


def _head_bound_bytes(repo: Path, path: Path, label: str, *, reason: str) -> bytes:
    try:
        relative = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise DelegationPolicyError(reason, f"{label} is outside its Git repository") from exc
    live = _regular_file_bytes(path, label, reason=reason)
    result = _git(repo, "show", f"HEAD:{relative}", binary=True)
    if result.returncode != 0:
        raise DelegationPolicyError(reason, f"{label} is not tracked at HEAD")
    if bytes(result.stdout) != live:
        raise DelegationPolicyError(reason, f"{label} differs from the tracked HEAD bytes")
    return live


def _json_object(raw: bytes, label: str, *, reason: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DelegationPolicyError(reason, f"{label} is invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DelegationPolicyError(reason, f"{label} must contain one JSON object")
    return payload


def _validate_project(project: dict[str, Any], *, allow_root: bool) -> dict[str, str]:
    required = {"id", "repository", "rig", "workflow_authority", "workflow_profile"}
    optional = {"base_ref"}
    if allow_root:
        required.add("root")
        optional.update({"rig_root", "worktree_root"})
    if not required.issubset(project) or not set(project).issubset(required | optional):
        raise DelegationPolicyError(
            "managed_project_context_invalid", "project identity keys are incomplete or unsupported"
        )
    project_id = project.get("id")
    repository = project.get("repository")
    rig = project.get("rig")
    if not isinstance(project_id, str) or not ID_PATTERN.fullmatch(project_id):
        raise DelegationPolicyError("managed_project_context_invalid", "project id is invalid")
    if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository):
        raise DelegationPolicyError("managed_project_context_invalid", "project repository is invalid")
    if not isinstance(rig, str) or not ID_PATTERN.fullmatch(rig):
        raise DelegationPolicyError("managed_project_context_invalid", "project rig is invalid")
    if project.get("workflow_authority") != "beads":
        raise DelegationPolicyError(
            "managed_project_context_invalid", "workflow_authority must be beads"
        )
    if project.get("workflow_profile") not in {
        "beads-with-aegis-evidence",
        "beads-with-frozen-legacy-evidence",
    }:
        raise DelegationPolicyError("managed_project_context_invalid", "workflow_profile is invalid")
    base_ref = project.get("base_ref")
    if base_ref is not None and (
        not isinstance(base_ref, str)
        or not BASE_REF_PATTERN.fullmatch(base_ref)
        or ".." in base_ref
        or "//" in base_ref
        or base_ref.endswith("/")
    ):
        raise DelegationPolicyError("managed_project_context_invalid", "project base_ref is invalid")
    if allow_root:
        for key in ("root", "rig_root", "worktree_root"):
            value = project.get(key)
            if value is not None and (not isinstance(value, str) or not Path(value).is_absolute()):
                raise DelegationPolicyError(
                    "managed_project_context_invalid", f"registered project {key} must be absolute"
                )
    return {key: str(value) for key, value in project.items()}


def _descriptor(worktree_root: Path) -> dict[str, str] | None:
    path = worktree_root / DESCRIPTOR_NAME
    tracked = _git(worktree_root, "cat-file", "-e", f"HEAD:{DESCRIPTOR_NAME}").returncode == 0
    if not path.exists() and not path.is_symlink():
        if tracked:
            raise DelegationPolicyError(
                "managed_project_context_invalid", "tracked project descriptor is missing"
            )
        return None
    raw = _head_bound_bytes(
        worktree_root,
        path,
        "project descriptor",
        reason="managed_project_context_invalid",
    )
    payload = _json_object(raw, "project descriptor", reason="managed_project_context_invalid")
    if payload.pop("schema", None) != DESCRIPTOR_SCHEMA:
        raise DelegationPolicyError(
            "managed_project_context_invalid", "project descriptor schema is invalid"
        )
    return _validate_project(payload, allow_root=False)


def _runtime_source_root(worktree_root: Path) -> Path | None:
    path = worktree_root / RUNTIME_ENV_REL
    if not path.exists() and not path.is_symlink():
        return None
    raw = _regular_file_bytes(path, "Aegis runtime environment")
    values: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise DelegationPolicyError(
                "managed_project_context_invalid", "Aegis runtime environment is malformed"
            )
        key, value = stripped.split("=", 1)
        if key != "AEGIS_SOURCE_ROOT" or key in values or not value:
            raise DelegationPolicyError(
                "managed_project_context_invalid", "Aegis runtime environment is malformed"
            )
        values[key] = value
    source = values.get("AEGIS_SOURCE_ROOT")
    if source is None or not Path(source).is_absolute():
        raise DelegationPolicyError(
            "managed_project_context_invalid", "Aegis source root is missing or not absolute"
        )
    # A retired source checkout can remain only as a stale pointer. The
    # canonical user registry may recover that state; ``_registry`` still
    # fails closed when no validated fallback exists.
    return Path(source).resolve()


def _user_workflow_registry_path() -> Path | None:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        base = Path(config_home).expanduser().resolve()
    else:
        home = os.environ.get("HOME")
        if not home:
            return None
        base = (Path(home).expanduser().resolve() / ".config")
    path = base / "aegis/obsidian-projects.json"
    if not path.exists() and not path.is_symlink():
        return None
    raw = _regular_file_bytes(path, "Aegis Obsidian project registry")
    payload = _json_object(
        raw,
        "Aegis Obsidian project registry",
        reason="managed_project_context_invalid",
    )
    dashboard = payload.get("continuity_dashboard")
    workflow_registry = dashboard.get("workflow_registry") if isinstance(dashboard, dict) else None
    if payload.get("schema_version") != "1" or not isinstance(workflow_registry, str):
        raise DelegationPolicyError(
            "managed_project_context_invalid",
            "Aegis Obsidian project registry lacks the canonical workflow registry pointer",
        )
    candidate = Path(workflow_registry)
    if not candidate.is_absolute():
        raise DelegationPolicyError(
            "managed_project_context_invalid", "canonical workflow registry path is not absolute"
        )
    return candidate.resolve()


def _load_registry_path(path: Path) -> tuple[list[dict[str, str]], bytes]:
    repo_text = _git_text(path.parent, "rev-parse", "--show-toplevel")
    repo = Path(repo_text).resolve()
    raw = _head_bound_bytes(
        repo,
        path,
        "Gas City project registry",
        reason="managed_project_context_invalid",
    )
    payload = _json_object(raw, "Gas City project registry", reason="managed_project_context_invalid")
    if set(payload) != {"schema", "projects"} or payload.get("schema") != REGISTRY_SCHEMA:
        raise DelegationPolicyError(
            "managed_project_context_invalid", "Gas City project registry schema is invalid"
        )
    projects = payload.get("projects")
    if not isinstance(projects, list) or not all(isinstance(item, dict) for item in projects):
        raise DelegationPolicyError(
            "managed_project_context_invalid", "Gas City project registry entries are invalid"
        )
    validated = [_validate_project(item, allow_root=True) for item in projects]
    roots = [item["root"] for item in validated]
    ids = [item["id"] for item in validated]
    if len(roots) != len(set(roots)) or len(ids) != len(set(ids)):
        raise DelegationPolicyError(
            "managed_project_context_invalid", "Gas City registry identities are not unique"
        )
    return validated, raw


def _registry(worktree_root: Path) -> list[dict[str, str]]:
    source_root = _runtime_source_root(worktree_root)
    runtime_path = source_root / REGISTRY_REL if source_root is not None else None
    user_path = _user_workflow_registry_path()
    paths: list[Path] = []
    if runtime_path is not None and runtime_path.is_file() and not runtime_path.is_symlink():
        paths.append(runtime_path.resolve())
    if user_path is not None:
        paths.append(user_path)
    unique_paths = list(dict.fromkeys(paths))
    if not unique_paths:
        if runtime_path is not None:
            raise DelegationPolicyError(
                "managed_project_context_invalid",
                "Aegis runtime source has no workflow registry and no canonical user fallback",
            )
        return []
    loaded = [_load_registry_path(path) for path in unique_paths]
    baseline = loaded[0][0]
    if any(projects != baseline for projects, _raw in loaded[1:]):
        raise DelegationPolicyError(
            "managed_project_context_invalid",
            "runtime and canonical user workflow registries disagree",
        )
    return baseline


def _verify_remote(worktree_root: Path, expected: str) -> None:
    remote = _git_text(worktree_root, "remote", "get-url", "origin")
    observed = None
    for pattern in REMOTE_PATTERNS:
        match = pattern.fullmatch(remote)
        if match:
            observed = match.group("repo")
            break
    if observed is None or observed.casefold() != expected.casefold():
        raise DelegationPolicyError(
            "managed_project_context_invalid",
            f"declared repository {expected} disagrees with origin",
        )


def _review_ref(identity: dict[str, str]) -> str:
    base_ref = identity.get("base_ref")
    if base_ref is None:
        return "refs/remotes/origin/main"
    if re.fullmatch(r"[0-9a-f]{40}", base_ref):
        return base_ref
    if base_ref.startswith("refs/remotes/origin/"):
        return base_ref
    if base_ref.startswith("refs/heads/"):
        return f"refs/remotes/origin/{base_ref.removeprefix('refs/heads/')}"
    raise DelegationPolicyError(
        "managed_project_context_invalid",
        "project base_ref cannot establish the reviewed delegation base",
    )


def resolve_managed_project(root: Path) -> ManagedProject | None:
    requested = root.resolve()
    descriptor_path = requested / DESCRIPTOR_NAME
    runtime_path = requested / RUNTIME_ENV_REL
    local_indicator = (
        descriptor_path.exists()
        or descriptor_path.is_symlink()
        or runtime_path.exists()
        or runtime_path.is_symlink()
    )
    top = _git(requested, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        if local_indicator:
            raise DelegationPolicyError(
                "managed_project_context_invalid", "managed project marker is outside a Git worktree"
            )
        return None
    resolved_top = Path(str(top.stdout).strip()).resolve()
    tracked = _git(
        resolved_top,
        "cat-file",
        "-e",
        f"HEAD:{DESCRIPTOR_NAME}",
    )
    user_registry = _user_workflow_registry_path()
    if not local_indicator and tracked.returncode != 0 and user_registry is None:
        return None
    worktree_root, canonical_root = _worktree_and_canonical_root(root)
    descriptor = _descriptor(worktree_root)
    registry = _registry(worktree_root)
    registered = next(
        (item for item in registry if Path(item["root"]).resolve() == canonical_root), None
    )
    if registered is None and descriptor is not None:
        registered = next((item for item in registry if item["id"] == descriptor["id"]), None)
    if descriptor is None and registered is None:
        return None
    if registered is not None and Path(registered["root"]).resolve() != canonical_root:
        raise DelegationPolicyError(
            "managed_project_context_invalid",
            "registered canonical root disagrees with the Git common directory",
        )
    if descriptor is not None and registered is not None:
        comparable = {
            key: value
            for key, value in registered.items()
            if key not in {"root", "rig_root", "worktree_root"}
        }
        if descriptor != comparable:
            raise DelegationPolicyError(
                "managed_project_context_invalid",
                "project descriptor disagrees with the Gas City registry",
            )
        identity = descriptor
        identity_source = "descriptor+registry"
    elif descriptor is not None:
        identity = descriptor
        identity_source = "descriptor"
    else:
        assert registered is not None
        identity = registered
        identity_source = "registry"
    _verify_remote(worktree_root, identity["repository"])
    return ManagedProject(
        project_id=identity["id"],
        repository=identity["repository"],
        canonical_root=canonical_root,
        worktree_root=worktree_root,
        identity_source=identity_source,
        review_ref=_review_ref(identity),
    )


def _exception_records(project: ManagedProject) -> list[dict[str, str]] | None:
    path = project.worktree_root / EXCEPTIONS_NAME
    if not path.exists() and not path.is_symlink():
        return None
    raw = _head_bound_bytes(
        project.worktree_root,
        path,
        "delegation exception file",
        reason="native_delegation_exception_invalid",
    )
    payload = _json_object(
        raw, "delegation exception file", reason="native_delegation_exception_invalid"
    )
    if set(payload) != {"schema", "exceptions"} or payload.get("schema") != EXCEPTIONS_SCHEMA:
        raise DelegationPolicyError(
            "native_delegation_exception_invalid", "delegation exception schema is invalid"
        )
    records = payload.get("exceptions")
    if not isinstance(records, list) or len(records) > MAX_EXCEPTIONS:
        raise DelegationPolicyError(
            "native_delegation_exception_invalid", "delegation exception list is invalid"
        )
    required = {
        "project_id",
        "adapter",
        "tool_name",
        "request_sha256",
        "branch",
        "bead_id",
        "review_ref",
        "review_evidence",
    }
    validated: list[dict[str, str]] = []
    identities: set[tuple[str, ...]] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != required:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation exception keys are invalid"
            )
        if not all(isinstance(record[key], str) for key in required):
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation exception values must be strings"
            )
        normalized = {key: str(record[key]) for key in required}
        tool = normalized["tool_name"]
        branch = normalized["branch"]
        bead = normalized["bead_id"]
        review_ref = normalized["review_ref"]
        evidence = normalized["review_evidence"]
        if normalized["project_id"] != project.project_id:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation exception project is invalid"
            )
        if normalized["adapter"] not in {"claude", "codex"}:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation exception adapter is invalid"
            )
        if tool not in PROVIDER_NATIVE_DELEGATION_TOOLS or normalize_delegation_tool(tool) != tool:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation exception tool is invalid"
            )
        if not DIGEST_PATTERN.fullmatch(normalized["request_sha256"]):
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation request digest is invalid"
            )
        if (
            not BRANCH_PATTERN.fullmatch(branch)
            or ".." in branch
            or "//" in branch
            or branch.endswith("/")
        ):
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation exception branch is invalid"
            )
        if not BEAD_PATTERN.fullmatch(bead):
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation exception bead is invalid"
            )
        if (
            review_ref != project.review_ref
            or not REVIEW_REF_PATTERN.fullmatch(review_ref)
            or ".." in review_ref
            or "//" in review_ref
            or review_ref.endswith("/")
        ):
            raise DelegationPolicyError(
                "native_delegation_exception_invalid",
                "delegation review ref is not the project's canonical reviewed base",
            )
        if not evidence.startswith(f"bead:{bead}#") or len(evidence) > 512:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "delegation review evidence is invalid"
            )
        identity_tuple = tuple(normalized[key] for key in sorted(required))
        if identity_tuple in identities:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid", "duplicate delegation exception"
            )
        reviewed = _git(
            project.worktree_root,
            "show",
            f"{review_ref}:{EXCEPTIONS_NAME}",
            binary=True,
        )
        if reviewed.returncode != 0 or bytes(reviewed.stdout) != raw:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid",
                "delegation exception bytes are not present on the declared remote review ref",
            )
        ancestry = _git(
            project.worktree_root,
            "merge-base",
            "--is-ancestor",
            review_ref,
            "HEAD",
        )
        if ancestry.returncode != 0:
            raise DelegationPolicyError(
                "native_delegation_exception_invalid",
                "delegation review ref is not an ancestor of the executing branch",
            )
        identities.add(identity_tuple)
        validated.append(normalized)
    return validated


def _reviewer_frontmatter(raw: bytes) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer agent definition is not UTF-8") from exc
    if not text.startswith("---\n"):
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer agent definition lacks frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer agent definition frontmatter is unterminated")
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = FRONTMATTER_FIELD.match(line)
        if match is None or match.group(1) in fields:
            raise DelegationPolicyError(REVIEWER_REASON, "reviewer agent definition frontmatter is malformed")
        fields[match.group(1)] = match.group(2)
    return fields


def _reviewer_delegation(
    project: ManagedProject, payload: Payload, normalized_tool: str, adapter: str
) -> bool:
    """Allow one read-only reviewer sub-agent bound to one existing candidate commit.

    Closed grammar: the Claude `Agent` tool, an allowlisted agent type whose tracked
    and clean definition declares only Read, Grep and Glob, no isolation or other
    options, and a prompt naming exactly one commit present in the repository.
    Everything else is a worker request and stays under Gas City routing.
    """

    tool_input = payload.tool_input if isinstance(payload.tool_input, dict) else {}
    agent_type = tool_input.get("subagent_type")
    if adapter != "claude" or normalized_tool != "agent" or agent_type not in REVIEWER_AGENT_TYPES:
        return False
    extra = sorted(set(tool_input) - REVIEWER_INPUT_KEYS)
    if extra:
        raise DelegationPolicyError(
            REVIEWER_REASON, f"reviewer delegation carries unsupported options: {extra}"
        )
    prompt = tool_input.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > REVIEWER_PROMPT_BOUND:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer prompt is missing, empty or oversized")
    candidates = CANDIDATE_TOKEN.findall(prompt)
    if len(candidates) != 1:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer delegation must name exactly one candidate commit"
        )
    exists = _git(project.worktree_root, "cat-file", "-e", f"{candidates[0]}^{{commit}}")
    if exists.returncode != 0:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer candidate commit is not present in the repository"
        )
    definition = project.worktree_root / REVIEWER_AGENTS_REL / f"{agent_type}.md"
    raw = _head_bound_bytes(
        project.worktree_root, definition, "reviewer agent definition", reason=REVIEWER_REASON
    )
    fields = _reviewer_frontmatter(raw)
    if fields.get("name") != agent_type:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer agent definition name mismatch")
    declared = fields.get("tools")
    if declared is None:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer agent definition must declare its tools")
    tools = {item.strip() for item in declared.split(",") if item.strip()}
    if not tools or not tools <= REVIEWER_TOOLS:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer agent definition is not read-only")
    return True


def evaluate_native_delegation(root: Path, payload: Payload) -> DelegationVerdict | None:
    normalized_tool = normalize_delegation_tool(payload.tool_name)
    if normalized_tool not in PROVIDER_NATIVE_DELEGATION_TOOLS:
        return None
    adapter = _adapter_for_tool(normalized_tool)
    request_sha256 = payload_digest(payload)
    project = resolve_managed_project(root)
    if project is None:
        return DelegationVerdict(
            managed=False,
            allowed=True,
            reason="unmanaged_project",
            request_sha256=request_sha256,
            normalized_tool=normalized_tool,
            adapter=adapter,
            project=None,
        )
    if _reviewer_delegation(project, payload, normalized_tool, adapter):
        return DelegationVerdict(
            managed=True,
            allowed=True,
            reason="read_only_reviewer_delegation",
            request_sha256=request_sha256,
            normalized_tool=normalized_tool,
            adapter=adapter,
            project=project,
        )
    records = _exception_records(project)
    if records is not None:
        branch = _git_text(project.worktree_root, "branch", "--show-current")
        for record in records:
            if (
                record["adapter"] == adapter
                and record["tool_name"] == normalized_tool
                and record["request_sha256"] == request_sha256
                and record["branch"] == branch
            ):
                return DelegationVerdict(
                    managed=True,
                    allowed=True,
                    reason="reviewed_native_delegation_exception",
                    request_sha256=request_sha256,
                    normalized_tool=normalized_tool,
                    adapter=adapter,
                    project=project,
                )
        reason = "native_delegation_exception_mismatch"
    else:
        reason = "native_delegation_requires_gas_city"
    return DelegationVerdict(
        managed=True,
        allowed=False,
        reason=reason,
        request_sha256=request_sha256,
        normalized_tool=normalized_tool,
        adapter=adapter,
        project=project,
    )
