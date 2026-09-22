"""Read-only reviewer delegation grammar for managed projects (ga-fsfg, ga-4p6f).

A reviewer is not a worker: one tracked, clean, read-only agent definition may be
delegated one review of one bound candidate commit. Every other provider-native
delegation stays under Gas City routing in `delegation.py`.
"""

from __future__ import annotations

import os
import re
import subprocess
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
# candidate. The token stands alone: it starts the prompt or follows whitespace, and
# its path ends at a space, tab, newline or the end of the prompt. Any other
# `worktree` followed by an equals sign (any case, any whitespace before the sign,
# ASCII or full-width) is ambiguous and refused.
WORKTREE_MENTION = re.compile(r"worktree\s*[=＝]", re.IGNORECASE)
WORKTREE_TOKEN = re.compile(r"(?<!\S)worktree=(/[A-Za-z0-9._/-]+)(?=[ \t\n]|\Z)")
FOREIGN_GIT = "/usr/bin/git"
FOREIGN_GIT_TIMEOUT = 10
MAX_GITDIR_LINK_BYTES = 4096
# Applied to every foreign Git call: no replace objects (HEAD's tree is the
# candidate's own), no index refresh write, and no repository-configured
# filesystem monitor program.
FOREIGN_GIT_OPTIONS = (
    "--no-replace-objects",
    "--no-optional-locks",
    "-c",
    "core.fsmonitor=false",
)
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


def _foreign_git(target: Path, *args: str) -> str:
    """Run the absolute Git binary against a registered worktree, bounded and fail-closed.

    Inherited GIT_* variables are dropped so the caller's environment cannot redirect
    the repository, every call carries FOREIGN_GIT_OPTIONS, and output is decoded
    without raising.
    """

    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        result = subprocess.run(
            [FOREIGN_GIT, "-C", str(target), *FOREIGN_GIT_OPTIONS, *args],
            capture_output=True,
            timeout=FOREIGN_GIT_TIMEOUT,
            env=env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree Git inspection failed"
        ) from exc
    if result.returncode != 0:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer worktree Git inspection failed")
    return result.stdout.decode("utf-8", errors="replace")


def _verify_registered_review_worktree(project: ManagedProject, raw: str, candidate: str) -> None:
    from .native_permissions import _profile

    try:
        profile = _profile(project.worktree_root)
    except (OSError, ValueError) as exc:
        raise DelegationPolicyError(
            REVIEWER_REASON, f"reviewer registered-project policy is invalid: {exc}"
        ) from exc
    entries = (profile or {}).get("registered_projects") or []
    target = Path(raw)
    # The pure path comparison runs first, so no unregistered location is touched.
    entry = next(
        (item for item in entries if target.parent == Path(item["worktree_root"])), None
    )
    if entry is None:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree is not a direct child of a registered worktree root"
        )
    try:
        resolved = target.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise DelegationPolicyError(REVIEWER_REASON, "reviewer worktree does not exist") from exc
    if resolved != target or not target.is_dir():
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree must be an exact absolute directory"
        )
    common = Path(
        _foreign_git(target, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    )
    git_dir = Path(
        _foreign_git(target, "rev-parse", "--path-format=absolute", "--git-dir").strip()
    )
    top = Path(_foreign_git(target, "rev-parse", "--show-toplevel").strip())
    # A linked worktree's private Git directory sits under <common>/worktrees and
    # its gitdir file links back to exactly this worktree's .git file.
    link = git_dir / "gitdir"
    linked = ""
    if link.is_file():
        with link.open("rb") as stream:
            raw_link = stream.read(MAX_GITDIR_LINK_BYTES + 1)
        if len(raw_link) <= MAX_GITDIR_LINK_BYTES:
            linked = raw_link.decode("utf-8", errors="replace").strip()
    if (
        common != Path(entry["canonical_root"]) / ".git"
        or top != target
        or git_dir.parent != common / "worktrees"
        or not linked
        or Path(linked) != target / ".git"
    ):
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree is not a linked worktree of its registered project"
        )
    head = _foreign_git(target, "rev-parse", "--verify", "--quiet", "HEAD^{commit}").strip()
    if head != candidate:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree HEAD is not the candidate commit"
        )
    # Index entries flagged assume-unchanged (lowercase tag) or skip-worktree (S)
    # would let modified files hide from status.
    flagged = [
        entry_line
        for entry_line in _foreign_git(target, "ls-files", "-v", "-z").split("\0")
        if entry_line and (entry_line[0].islower() or entry_line[0] == "S")
    ]
    if flagged:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree hides index entries from status"
        )
    # Stat comparison is pinned to Git's defaults so repository configuration cannot
    # relax change detection.
    status = _foreign_git(
        target,
        "-c",
        "core.checkStat=default",
        "-c",
        "core.trustctime=true",
        "-c",
        "core.ignoreCase=false",
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status.strip():
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer worktree has uncommitted or untracked changes"
        )


def _registered_review_worktree(project: ManagedProject, raw: str, candidate: str) -> None:
    """Bind a reviewer to one clean registered worktree whose HEAD is the candidate.

    The reviewer can only read files, so the binding requires the named worktree to be
    checked out at exactly that commit with nothing uncommitted that Git can see. It
    must be a direct child of a worktree root registered in the seat's tracked command
    profile and a linked worktree of that project's canonical root. Every failure,
    expected or not, is a refusal: an unexpected exception must never reach the
    gate's degraded fallback, which advisory mode would turn into an allow.
    """

    try:
        _verify_registered_review_worktree(project, raw, candidate)
    except DelegationPolicyError:
        raise
    except Exception as exc:  # noqa: BLE001 - every unexpected failure refuses.
        raise DelegationPolicyError(
            REVIEWER_REASON,
            f"reviewer worktree binding could not be verified: {type(exc).__name__}",
        ) from exc


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
    # The read-only definition is checked before any candidate binding so no binding
    # path can be reached with a definition that could edit, run or delegate.
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
    if worktrees:
        _registered_review_worktree(project, worktrees[0], candidates[0])
        return "read_only_registered_reviewer_delegation"
    exists = _git(project.worktree_root, "cat-file", "-e", f"{candidates[0]}^{{commit}}")
    if exists.returncode != 0:
        raise DelegationPolicyError(
            REVIEWER_REASON, "reviewer candidate commit is not present in the repository"
        )
    return "read_only_reviewer_delegation"
