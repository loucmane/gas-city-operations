"""Read-only reviewer delegation grammar for managed projects (ga-fsfg, ga-4p6f).

A reviewer is not a worker: one tracked, clean, read-only agent definition may be
delegated one review of one bound candidate commit. Every other provider-native
delegation stays under Gas City routing in `delegation.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

from .contracts import Payload
from .delegation import DelegationPolicyError, ManagedProject, _git, _head_bound_bytes


# ga-fsfg: a read-only reviewer is not a worker. One tracked agent definition that may
# hold only Read, Grep and Glob can be delegated to review exactly one candidate
# commit; every other provider-native delegation stays under Gas City routing.
REVIEWER_AGENT_TYPES = frozenset({"aegis-reviewer"})
REVIEWER_AGENTS_REL = Path(".claude/agents")
REVIEWER_TOOLS = frozenset({"Read", "Grep", "Glob"})
REVIEWER_INPUT_KEYS = frozenset({"description", "prompt", "subagent_type"})
REVIEWER_FRONTMATTER_KEYS = frozenset({"name", "description", "tools", "model", "color"})
REVIEWER_PROMPT_BOUND = 65536
REVIEWER_REASON = "native_delegation_reviewer_invalid"
CANDIDATE_TOKEN = re.compile(r"(?<![0-9A-Za-z=_-])candidate=([0-9a-f]{40})(?![0-9A-Za-z])")
# ga-4p6f: a reviewer may also name the registered-project worktree holding the
# candidate. Any `worktree=` mention that is not one exact absolute path followed by
# whitespace or the end of the prompt is ambiguous and refused.
WORKTREE_MENTION = re.compile(r"(?<![0-9A-Za-z=_-])worktree=")
WORKTREE_TOKEN = re.compile(r"(?<![0-9A-Za-z=_-])worktree=(/[A-Za-z0-9._/-]+)(?!\S)")
FRONTMATTER_FIELD = re.compile(r"^([a-z_]+):[ \t]*(.*?)[ \t]*$")


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
    unsupported = sorted(set(fields) - REVIEWER_FRONTMATTER_KEYS)
    if unsupported:
        raise DelegationPolicyError(
            REVIEWER_REASON,
            f"reviewer agent definition carries unsupported frontmatter: {unsupported}",
        )
    return fields


def _registered_review_worktree(project: ManagedProject, raw: str, candidate: str) -> None:
    """Bind a reviewer to one clean registered worktree whose HEAD is the candidate.

    The reviewer can only read files, so the candidate is what it sees only when the
    named worktree is checked out at exactly that commit with nothing uncommitted.
    The worktree must be a direct child of a worktree root registered in the seat's
    tracked command profile, and a linked worktree of that project's canonical root.
    """

    from .native_permissions import _profile

    try:
        profile = _profile(project.worktree_root)
    except (OSError, ValueError) as exc:
        raise DelegationPolicyError(
            REVIEWER_REASON, f"reviewer registered-project policy is invalid: {exc}"
        ) from exc
    entries = (profile or {}).get("registered_projects") or []
    target = Path(raw)
    try:
        resolved = target.resolve(strict=True)
    except OSError as exc:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer worktree does not exist") from exc
    if resolved != target or not target.is_dir():
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree must be an exact absolute directory"
        )
    entry = next(
        (item for item in entries if target.parent == Path(item["worktree_root"])), None
    )
    if entry is None:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree is not a direct child of a registered worktree root"
        )
    common = _git(target, "rev-parse", "--path-format=absolute", "--git-common-dir")
    top = _git(target, "rev-parse", "--show-toplevel")
    if (
        common.returncode
        or top.returncode
        or Path(str(common.stdout).strip()) != Path(entry["canonical_root"]) / ".git"
        or Path(str(top.stdout).strip()) != target
    ):
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree is not a linked worktree of its registered project"
        )
    head = _git(target, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    if head.returncode or str(head.stdout).strip() != candidate:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree HEAD is not the candidate commit"
        )
    # No index refresh write and no repository-configured filesystem monitor.
    status = _git(
        target,
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status.returncode or str(status.stdout).strip():
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree has uncommitted or untracked changes"
        )


def _reviewer_delegation(
    project: ManagedProject, payload: Payload, normalized_tool: str, adapter: str
) -> str | None:
    """Allow one read-only reviewer sub-agent bound to one existing candidate commit.

    Closed grammar: the Claude `Agent` tool, an allowlisted agent type whose tracked
    and clean definition declares only Read, Grep and Glob, no isolation or other
    options, and a prompt naming exactly one commit present in the repository, or
    (ga-4p6f) one commit checked out cleanly in one named registered-project
    worktree. Everything else is a worker request and stays under Gas City routing.
    Returns the audit reason for an allowed reviewer, or None for a non-reviewer.
    """

    tool_input = payload.tool_input if isinstance(payload.tool_input, dict) else {}
    agent_type = tool_input.get("subagent_type")
    if adapter != "claude" or normalized_tool != "agent" or agent_type not in REVIEWER_AGENT_TYPES:
        return None
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
    worktrees = WORKTREE_TOKEN.findall(prompt)
    if len(WORKTREE_MENTION.findall(prompt)) != len(worktrees) or len(worktrees) > 1:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer delegation may name at most one exact worktree"
        )
    if worktrees:
        _registered_review_worktree(project, worktrees[0], candidates[0])
        reason = "read_only_registered_reviewer_delegation"
    else:
        exists = _git(project.worktree_root, "cat-file", "-e", f"{candidates[0]}^{{commit}}")
        if exists.returncode != 0:
            raise DelegationPolicyError(
                REVIEWER_REASON, "reviewer candidate commit is not present in the repository"
            )
        reason = "read_only_reviewer_delegation"
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
    return reason
