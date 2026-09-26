"""Closed grammar and profile fields for the delivery class (ga-fsfg R3).

Pure parsing and validation: no process and no filesystem access. The Git and gh
reads live in `delivery_checks.py`, worktree discovery in `delivery_worktree.py`
and the orchestration in `delivery.py`.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from typing import Any

from .orchestrator import SHELL_SYNTAX

COMMAND = "delivery"
ENV = "/usr/bin/env"
GIT = "/usr/bin/git"
GH = "/usr/bin/gh"
PUSH = "push"
PR_CREATE = "pr-create"
PR_MERGE = "pr-merge"
OPERATIONS = frozenset({PUSH, PR_CREATE, PR_MERGE})
DELIVERY_KEYS = frozenset(
    {
        "repository",
        "default_branch",
        "remote_url",
        "signing_key",
        "required_checks",
        "delivery_path",
        "delivery_home",
        "credential_helpers",
    }
)
MAX_COMMAND = 16384
MAX_REQUIRED_CHECKS = 64
MAX_CHECK_NAME = 256
MAX_CREDENTIAL_ENTRIES = 16
MAX_CREDENTIAL_VALUE = 1024
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
# The fingerprint git reports as %GF: 40 hex digits for a v4 key, 64 for v5/v6.
FINGERPRINT = re.compile(r"[0-9A-F]{40}(?:[0-9A-F]{24})?")
SAFE_PATH = re.compile(r"/[A-Za-z0-9._/-]+")
BRANCH = re.compile(r"[A-Za-z0-9._/-]+")
FORBIDDEN_BRANCH_PREFIXES = ("-", "refs/", "heads/", "tags/", "remotes/")
CREDENTIAL_KEY = re.compile(r"credential\.(?:[!-~]+\.)?[a-z][a-z0-9-]*")
REMOTE_URL = re.compile(r"[!-~]{1,1024}")
# Decimal digits only; a pull request number never starts with zero.
NUMBER = re.compile(r"[1-9][0-9]{0,9}")
SHA = re.compile(r"[0-9a-f]{40}")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")


@dataclass(frozen=True)
class DeliveryRequest:
    """One parsed delivery call. Which fields are set depends on the operation."""

    operation: str
    branch: str | None = None
    worktree: str | None = None
    title: str | None = None
    body_file: str | None = None
    number: str | None = None
    sha: str | None = None


def canonical_absolute(text: object) -> bool:
    """An absolute path written in canonical form: no `.`, `..`, doubled or trailing slash."""

    return (
        isinstance(text, str)
        and SAFE_PATH.fullmatch(text) is not None
        and os.path.normpath(text) == text
        and not text.startswith("//")
    )


def branch_violation(branch: str, default_branch: str) -> str | None:
    """Pure branch-name rules; `git check-ref-format --branch` runs in the checks too."""

    if not BRANCH.fullmatch(branch) or branch.startswith(FORBIDDEN_BRANCH_PREFIXES):
        return "delivery branch is not a plain branch name"
    if branch.endswith("HEAD"):
        return "delivery branch may not be a HEAD-like name"
    if branch == default_branch:
        return "delivery may not name the default branch"
    return None


def validate_delivery_profile(value: dict[str, Any]) -> None:
    """Validate the delivery fields; all of them are required once any is present.

    A profile that lists the class must carry every field. The class refuses when a
    field is missing or invalid, and so does every other class, because `_profile()`
    raises (the same fail-closed rule as a drifted `review_projects` record).
    """

    present = DELIVERY_KEYS & set(value)
    if not present and COMMAND not in value["commands"]:
        return
    if present != DELIVERY_KEYS:
        raise ValueError("delivery profile fields are missing")
    repository = value["repository"]
    if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
        raise ValueError("delivery repository must be exactly owner/name")
    default_branch = value["default_branch"]
    if (
        not isinstance(default_branch, str)
        or not BRANCH.fullmatch(default_branch)
        or default_branch.startswith("-")
    ):
        raise ValueError("delivery default_branch is invalid")
    url = value["remote_url"]
    if not isinstance(url, str) or not REMOTE_URL.fullmatch(url) or "::" in url:
        raise ValueError("delivery remote_url is invalid")
    key = value["signing_key"]
    if not isinstance(key, str) or not FINGERPRINT.fullmatch(key):
        raise ValueError("delivery signing_key must be an uppercase hex fingerprint")
    checks = value["required_checks"]
    if (
        not isinstance(checks, list)
        or not checks
        or len(checks) > MAX_REQUIRED_CHECKS
        or not all(
            isinstance(name, str) and 0 < len(name) <= MAX_CHECK_NAME and name.isprintable()
            for name in checks
        )
        or len(set(checks)) != len(checks)
    ):
        raise ValueError("delivery required_checks must be a non-empty list of unique names")
    path = value["delivery_path"]
    parts = path.split(":") if isinstance(path, str) else []
    if not parts or len(set(parts)) != len(parts) or not all(map(canonical_absolute, parts)):
        raise ValueError("delivery_path must list distinct canonical absolute directories")
    if not canonical_absolute(value["delivery_home"]):
        raise ValueError("delivery_home must be a canonical absolute path")
    helpers = value["credential_helpers"]
    if not isinstance(helpers, list) or len(helpers) > MAX_CREDENTIAL_ENTRIES:
        raise ValueError("delivery credential_helpers must be a bounded list")
    for entry in helpers:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"key", "value"}
            or not isinstance(entry["key"], str)
            or not CREDENTIAL_KEY.fullmatch(entry["key"])
            or not isinstance(entry["value"], str)
            or len(entry["value"]) > MAX_CREDENTIAL_VALUE
            or any(character in entry["value"] for character in "\n\r\0")
        ):
            raise ValueError("delivery credential_helpers entry is invalid")


def delivery_shaped(command: str) -> bool:
    """`env -i`, assignments, then a git or gh executable: a form only this parser owns.

    `strip_shell_prefixes` never trusts `env -i`, so claiming these forms cannot turn a
    command other classes approve into a refusal.
    """

    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if len(tokens) < 3 or os.path.basename(tokens[0]) != "env" or tokens[1] != "-i":
        return False
    for token in tokens[2:]:
        if ASSIGNMENT.match(token):
            continue
        return os.path.basename(token) in {"git", "gh"}
    return False


def parse_delivery(command: str, profile: dict[str, Any]) -> DeliveryRequest:
    """Parse one closed delivery command, raising ValueError for anything else.

    The command must be the canonical shell rendering of its own tokens (Python's
    `shlex.join`), so the shell and this parser always see the same words: no word is
    left unquoted where the shell would expand it.
    """

    if len(command) > MAX_COMMAND or SHELL_SYNTAX.search(command):
        raise ValueError("delivery requires one literal command without shell syntax")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise ValueError("delivery command does not tokenize") from exc
    if shlex.join(tokens) != command:
        raise ValueError("delivery command must use canonical quoting (Python shlex.join)")
    prefix = [ENV, "-i", f"HOME={profile['delivery_home']}", f"PATH={profile['delivery_path']}"]
    if tokens[:4] != prefix:
        raise ValueError("delivery requires the exact fixed-environment prefix")
    words = tokens[4:]
    if words[:1] == [GIT]:
        return _push(words, profile)
    if words[:3] == [GH, "pr", "create"]:
        return _pr_create(words, profile)
    if words[:3] == [GH, "pr", "merge"]:
        return _pr_merge(words, profile)
    raise ValueError("delivery accepts only git push, gh pr create and gh pr merge")


def _branch(branch: str, profile: dict[str, Any]) -> None:
    violation = branch_violation(branch, profile["default_branch"])
    if violation:
        raise ValueError(violation)


def _push(words: list[str], profile: dict[str, Any]) -> DeliveryRequest:
    if len(words) < 4 or words[1] != "-C" or words[3] != "push":
        raise ValueError("delivery push allows no Git global option but -C <worktree>")
    if len(words) != 6 or any(word.startswith("-") for word in words[4:]):
        raise ValueError("delivery push takes exactly `push origin <branch>` and no flag")
    worktree, remote, branch = words[2], words[4], words[5]
    if remote != "origin":
        raise ValueError("delivery push accepts only the origin remote")
    if not canonical_absolute(worktree):
        raise ValueError("delivery worktree must be a canonical absolute path")
    _branch(branch, profile)
    return DeliveryRequest(PUSH, branch=branch, worktree=worktree)


def _pr_create(words: list[str], profile: dict[str, Any]) -> DeliveryRequest:
    fixed = {
        3: "--repo",
        4: f"github.com/{profile['repository']}",
        5: "--base",
        6: profile["default_branch"],
        7: "--head",
        9: "--title",
        11: "--body-file",
    }
    if len(words) != 13 or any(words[index] != value for index, value in fixed.items()):
        raise ValueError(
            "delivery pr create takes exactly --repo, --base, --head, --title and --body-file"
        )
    branch, title, body = words[8], words[10], words[12]
    if not title or title.startswith("-") or not title.isprintable():
        raise ValueError("delivery --title must be printable and may not start with -")
    if body.startswith("-") or not canonical_absolute(body):
        raise ValueError("delivery --body-file must be a canonical absolute path")
    _branch(branch, profile)
    return DeliveryRequest(PR_CREATE, branch=branch, title=title, body_file=body)


def _pr_merge(words: list[str], profile: dict[str, Any]) -> DeliveryRequest:
    tail = ["--repo", f"github.com/{profile['repository']}", "--merge", "--match-head-commit"]
    if len(words) != 9 or words[4:8] != tail:
        raise ValueError(
            "delivery pr merge takes exactly <number> --repo <repository> --merge "
            "--match-head-commit <sha>"
        )
    number, sha = words[3], words[8]
    if not NUMBER.fullmatch(number):
        raise ValueError("delivery pull request number must be decimal digits")
    if not SHA.fullmatch(sha):
        raise ValueError("delivery head commit must be 40 lowercase hex characters")
    return DeliveryRequest(PR_MERGE, number=number, sha=sha)
