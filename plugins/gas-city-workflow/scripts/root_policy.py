#!/usr/bin/env python3
"""Enforce the canonical Gas City Operations root across agent cold starts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_POLICY = SCRIPT_DIR.parent / "config" / "root-policy.json"
SCHEMA = "gas-city-workflow.root-policy.v1"
DECISION_SCHEMA = "gas-city-workflow.root-policy-decision.v1"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MUTATION_TOOLS = {
    "Bash",
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
    "apply_patch",
}


class RootPolicyError(RuntimeError):
    """Raised when root policy is invalid or the selected root is retired."""


def _read_policy(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RootPolicyError(f"root policy must be a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RootPolicyError(f"root policy is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RootPolicyError("root policy must contain an object")
    if set(payload) != {"schema", "canonical", "retired"} or payload.get("schema") != SCHEMA:
        raise RootPolicyError("root policy schema is invalid")
    canonical = payload.get("canonical")
    retired = payload.get("retired")
    if not isinstance(canonical, dict) or set(canonical) != {"root", "repository"}:
        raise RootPolicyError("canonical root policy entry is invalid")
    if not isinstance(retired, list) or not retired:
        raise RootPolicyError("retired root policy entries are invalid")
    entries = [canonical, *retired]
    roots: list[Path] = []
    for index, entry in enumerate(entries):
        expected = {"root", "repository"} if index == 0 else {"root", "repository", "reason"}
        if not isinstance(entry, dict) or set(entry) != expected:
            raise RootPolicyError("root policy entry keys are invalid")
        root = entry.get("root")
        repository = entry.get("repository")
        if not isinstance(root, str) or not Path(root).is_absolute():
            raise RootPolicyError("root policy paths must be absolute")
        if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository):
            raise RootPolicyError("root policy repository is invalid")
        if index and (not isinstance(entry.get("reason"), str) or not entry["reason"].strip()):
            raise RootPolicyError("retired root policy reason is invalid")
        roots.append(Path(root).resolve(strict=False))
    if len(set(roots)) != len(roots):
        raise RootPolicyError("root policy paths must be unique")
    return payload


def _git_common_root(path: Path) -> Path | None:
    candidate = path.expanduser().resolve(strict=False)
    if not candidate.is_dir():
        return None
    result = subprocess.run(
        ["git", "-C", str(candidate), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        check=False,
        capture_output=True,
        text=True,
    )
    common = result.stdout.strip()
    if result.returncode != 0 or not common:
        return None
    resolved = Path(common).resolve(strict=False)
    if resolved.name != ".git":
        raise RootPolicyError(f"Git common directory is not a normal checkout: {resolved}")
    return resolved.parent.resolve(strict=False)


def evaluate_root(root: Path, policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    """Classify a cwd by Git common root so linked worktrees cannot evade retirement."""

    policy = _read_policy(policy_path)
    requested = root.expanduser().resolve(strict=False)
    common_root = _git_common_root(requested)
    identity = common_root or requested
    canonical = Path(policy["canonical"]["root"]).resolve(strict=False)
    retired_entry = next(
        (
            entry
            for entry in policy["retired"]
            if identity == Path(entry["root"]).resolve(strict=False)
        ),
        None,
    )
    if retired_entry is not None:
        classification = "retired"
        reason = retired_entry["reason"]
    elif identity == canonical:
        classification = "canonical"
        reason = "canonical Gas City Operations root"
    else:
        classification = "unmanaged"
        reason = "root is outside this retirement policy"
    return {
        "schema": DECISION_SCHEMA,
        "classification": classification,
        "requested_root": requested.as_posix(),
        "git_common_root": common_root.as_posix() if common_root is not None else None,
        "canonical_root": canonical.as_posix(),
        "reason": reason,
    }


def require_active_root(root: Path, policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    decision = evaluate_root(root, policy_path)
    if decision["classification"] == "retired":
        raise RootPolicyError(
            f"{decision['git_common_root'] or decision['requested_root']} is a preserved "
            f"historical checkout ({decision['reason']}); start new work from "
            f"{decision['canonical_root']}"
        )
    return decision


def _hook_cwd(payload: dict[str, Any], process_cwd: Path) -> Path:
    raw = payload.get("cwd")
    if raw is None:
        return process_cwd
    if not isinstance(raw, str) or not Path(raw).is_absolute():
        raise RootPolicyError("hook cwd must be an absolute path")
    return Path(raw)


def evaluate_hook(
    payload: dict[str, Any],
    policy_path: Path = DEFAULT_POLICY,
    *,
    process_cwd: Path | None = None,
) -> dict[str, str]:
    """Evaluate one Codex/Claude PreToolUse event through the shared root policy."""

    if not isinstance(payload, dict):
        raise RootPolicyError("hook payload must be an object")
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name:
        raise RootPolicyError("hook payload is missing tool_name")
    is_mutation_surface = tool_name in MUTATION_TOOLS or tool_name.startswith("mcp__")
    if not is_mutation_surface:
        return {"decision": "allow", "reason": "tool is outside the mutation matcher"}
    cwd = _hook_cwd(payload, process_cwd or Path.cwd())
    decision = evaluate_root(cwd, policy_path)
    if decision["classification"] != "retired":
        return {"decision": "allow", "reason": "root is not retired"}
    return {
        "decision": "deny",
        "reason": (
            f"{decision['git_common_root'] or decision['requested_root']} is preserved historical "
            f"evidence; new work must use {decision['canonical_root']}"
        ),
    }


def _read_hook_payload() -> dict[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise RootPolicyError(f"hook payload is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RootPolicyError("hook payload must contain an object")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--hook", action="store_true", help="Evaluate a PreToolUse JSON payload")
    mode.add_argument("--check-root", metavar="PATH", help="Classify one root")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="Exact root-policy JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.hook:
            result = evaluate_hook(_read_hook_payload(), Path(args.policy))
            if result["decision"] == "deny":
                print(f"gas-city-root-policy: BLOCKED: {result['reason']}", file=sys.stderr)
                return 2
            return 0
        result = evaluate_root(Path(args.check_root), Path(args.policy))
        print(json.dumps(result, sort_keys=True))
        return 2 if result["classification"] == "retired" else 0
    except RootPolicyError as exc:
        print(f"gas-city-root-policy: BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
