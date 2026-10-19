"""Observer-only project identity; never call the workflow gate's Git readers."""

from pathlib import Path
import subprocess
from typing import Any

from _git_read import run_git_read
import project_context as context
from root_policy import RootPolicyError, _read_policy


def _git(root: Path, *args: str, missing_origin: bool = False) -> str:
    try:
        result = run_git_read(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise context.ContextError(f"cannot observe Git identity at {root}: {exc}") from exc
    if (
        missing_origin and result.returncode == 2 and not result.stdout
        and result.stderr.strip() == "error: No such remote 'origin'"
    ):
        return ""
    if result.returncode != 0 or not result.stdout.strip():
        raise context.ContextError(
            f"cannot observe Git identity at {root}: "
            f"{result.stderr.strip() or 'empty Git response'}"
        )
    return result.stdout.strip()


def build_context(root: Path, registry_path: Path) -> dict[str, Any]:
    """Return only the project/workspace fields consumed by Continuity.

    Reuse descriptor, registry and workspace validation, which perform no Git
    operations. Resolve Git identity here and read retirement policy as data;
    project_context.build_context and root_policy.evaluate_root remain untouched.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise context.ContextError(f"project root is not a directory: {root}")
    top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise context.ContextError(f"--root must name the Git worktree root exactly: {top}")
    common = Path(_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if common.name != ".git" or not common.is_dir():
        raise context.ContextError(f"Git common directory is not a normal checkout: {common}")
    canonical = common.parent
    try:
        policy = _read_policy(context.DEFAULT_ROOT_POLICY)
    except RootPolicyError as exc:
        raise context.ContextError(str(exc)) from exc
    for entry in policy["retired"]:
        if canonical == Path(entry["root"]).resolve():
            raise context.ContextError(
                f"{canonical} is a preserved historical checkout ({entry['reason']}); "
                f"start new work from {policy['canonical']['root']}"
            )
    project, source, registered = context._resolve_project(root, canonical, registry_path.resolve())
    workspace = context._workspace_context(root, canonical, registered)
    remote = _git(root, "remote", "get-url", "origin", missing_origin=True)
    if remote:
        repository = next(
            (match.group("repo") for pattern in context.GITHUB_REMOTE_PATTERNS
             if (match := pattern.fullmatch(remote))), None,
        )
        if repository is None or repository.casefold() != project["repository"].casefold():
            raise context.ContextError("declared repository disagrees with origin")
    return {
        "project": {**project, "root": str(root), "identity_source": source},
        "workspace": workspace,
    }
