#!/usr/bin/env python3
"""Run deterministic Gas City workflow lifecycle transitions."""

from __future__ import annotations

import os
import sys

if __name__ == "__main__":
    # Defense in depth; all runtime integrity and workflow checks remain in force.
    # Set both read/write controls before imports and preserve existing caches.
    sys.dont_write_bytecode = True
    sys.pycache_prefix = os.devnull
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONPYCACHEPREFIX"] = os.devnull

import argparse
import json
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from project_context import DEFAULT_REGISTRY, build_context
from _repo_structure import load_repo_structure
from workflow_attach import attach
from workflow_begin import begin, resume, run_profile_readiness
from workflow_common import (
    CommandRunner,
    WorkflowError,
    active_begin_spec,
    active_bead_id,
    git_value,
    record_lifecycle_event,
    result_payload,
    run_readiness,
    workflow_runtime_root,
)
from workflow_ownership import check_active_ownership
from workflow_lock import workflow_lock
from workflow_portable import uses_portable_scaffold


def _is_lightweight_legacy(context: dict[str, Any]) -> bool:
    return (
        context["project"]["workflow_profile"] == "beads-with-frozen-legacy-evidence"
        and not (Path(context["project"]["root"]) / ".aegis" / "foundation-manifest.json").is_file()
    )


def _active_folder_name(root: Path, bead_id: str) -> str:
    active_root = load_repo_structure(root).work_tracking_active_root
    matches = sorted(
        path.name
        for path in active_root.glob("*-ACTIVE")
        if path.is_dir() and not path.is_symlink() and f"-{bead_id}-" in path.name
    )
    if len(matches) != 1:
        raise WorkflowError(f"expected exactly one ACTIVE folder for {bead_id}; found {matches}")
    return matches[0]


def _sync_plan(
    root: Path,
    context: dict[str, Any],
    runner: CommandRunner,
) -> bool:
    source_task = root / "scripts" / "codex-task"
    if source_task.is_file():
        runner.run([sys.executable, str(source_task), "plan", "sync"], cwd=root)
        return True
    if _is_lightweight_legacy(context) or uses_portable_scaffold(root):
        runtime = workflow_runtime_root()
        bead_id = active_bead_id(root)
        runner.run(
            [
                sys.executable,
                str(runtime / "scripts" / "codex-task"),
                "plan",
                "sync",
                "--target-dir",
                str(root),
                "--folder",
                _active_folder_name(root, bead_id),
            ],
            cwd=runtime,
        )
        return True
    return False


def _run_profile_readiness(
    root: Path,
    context: dict[str, Any],
    runner: CommandRunner,
) -> str:
    if _is_lightweight_legacy(context):
        return run_profile_readiness(runner, active_begin_spec(runner, root))
    return run_readiness(runner, root)


def _checkpoint(root: Path, runner: CommandRunner) -> dict[str, Any]:
    context = build_context(root, DEFAULT_REGISTRY)
    root = Path(context["project"]["root"])
    check_active_ownership(runner, root)
    _sync_plan(root, context, runner)
    _run_profile_readiness(root, context, runner)
    check_active_ownership(runner, root)
    journal = record_lifecycle_event(runner, root, "checkpoint", "ready")
    return result_payload(
        "checkpoint",
        "ready",
        journal=journal.as_posix(),
        context=build_context(root, DEFAULT_REGISTRY),
    )


def _verify(
    root: Path,
    runner: CommandRunner,
    *,
    synchronize: bool = True,
) -> dict[str, Any]:
    context = build_context(root, DEFAULT_REGISTRY)
    root = Path(context["project"]["root"])
    check_active_ownership(runner, root)
    checks: list[str] = ["live-bead-ownership"]
    if synchronize and _sync_plan(root, context, runner):
        checks.append("plan-sync")
    _run_profile_readiness(root, context, runner)
    guard = root / "scripts" / "codex-guard"
    checks.append("readiness")
    if guard.is_file():
        runner.run([sys.executable, str(guard), "validate", "--include-untracked"], cwd=root)
        checks.append("guard")
    runner.run(["git", "-C", str(root), "diff", "--check"])
    runner.run(["git", "-C", str(root), "diff", "--cached", "--check"])
    checks.append("git-diff-check")
    source_task = root / "scripts" / "codex-task"
    if _is_lightweight_legacy(context):
        checks.append("lightweight-bead-scaffold")
    elif uses_portable_scaffold(root):
        checks.append("portable-bead-scaffold")
    elif source_task.is_file() and not (root / ".aegis" / "foundation-manifest.json").is_file():
        runner.run(
            [sys.executable, str(source_task), "work-tracking", "audit"],
            cwd=root,
        )
        checks.append("source-work-tracking-audit")
    else:
        runtime = workflow_runtime_root()
        runner.run(
            [
                sys.executable,
                str(runtime / "scripts" / "codex-task"),
                "aegis",
                "verify",
                "--target-dir",
                str(root),
                "--strict",
            ],
            cwd=runtime,
        )
        checks.append("aegis-strict")
    check_active_ownership(runner, root)
    journal = record_lifecycle_event(runner, root, "verify", "passed", checks=checks)
    return result_payload("verify", "passed", checks=checks, journal=journal.as_posix())


def _publish(root: Path, runner: CommandRunner) -> dict[str, Any]:
    context = build_context(root, DEFAULT_REGISTRY)
    root = Path(context["project"]["root"])
    # Deliver the candidate before its attached repairs' post-merge acceptance.
    # Keep normal source ownership/dependency checks; finish alone requires all
    # blockers closed, both before and after the terminal closeout operation.
    check_active_ownership(runner, root)
    _verify(root, runner, synchronize=False)
    status = git_value(runner, root, "status", "--porcelain=v1")
    if status:
        raise WorkflowError("publication preflight requires a clean worktree")
    head = git_value(runner, root, "rev-parse", "HEAD")
    tree = git_value(runner, root, "rev-parse", "HEAD^{tree}")
    branch = git_value(runner, root, "branch", "--show-current")
    runner.run(["git", "-C", str(root), "verify-commit", head])
    check_active_ownership(runner, root)
    journal = record_lifecycle_event(
        runner,
        root,
        "publish",
        "ready",
        head=head,
        tree=tree,
        branch=branch,
    )
    return result_payload(
        "publish",
        "ready",
        head=head,
        tree=tree,
        branch=branch,
        journal=journal.as_posix(),
        next_action=(
            "Push this exact signed head, run hosted CI, and merge only under the "
            "repository's exact-head/base, green-CI, CLEAN/MERGEABLE, zero-thread rules."
        ),
    )


def _finish(root: Path, runner: CommandRunner, *, apply: bool) -> dict[str, Any]:
    context = build_context(root, DEFAULT_REGISTRY)
    root = Path(context["project"]["root"])
    bead_id = active_bead_id(root)
    bound_spec = check_active_ownership(runner, root, allow_closed=True, dependencies_complete=True)
    _run_profile_readiness(root, context, runner)
    source_task = root / "scripts" / "codex-task"
    if source_task.is_file():
        argv = [sys.executable, str(source_task), "work-tracking", "archive"]
        backend = "source-archive"
    elif _is_lightweight_legacy(context) or uses_portable_scaffold(root):
        canonical_task = workflow_runtime_root() / "scripts" / "codex-task"
        argv = [
            sys.executable,
            str(canonical_task),
            "work-tracking",
            "archive",
            "--target-dir",
            str(root),
            "--folder",
            _active_folder_name(root, bead_id),
        ]
        if not apply:
            argv.insert(2, "--dry-run")
        backend = (
            "lightweight-source-archive"
            if _is_lightweight_legacy(context)
            else "portable-source-archive"
        )
    else:
        canonical_task = workflow_runtime_root() / "scripts" / "codex-task"
        argv = [
            sys.executable,
            str(canonical_task),
            "aegis",
            "closeout",
            "--target-dir",
            str(root),
            "--update-handoff",
            "--require-clean-git",
            "--json",
        ]
        if not apply:
            argv.append("--dry-run")
        backend = "installed-closeout"
    if not apply and backend == "source-archive":
        journal = record_lifecycle_event(
            runner,
            root,
            "finish",
            "planned",
            bound_bead_id=bead_id,
            backend=backend,
        )
        return result_payload(
            "finish",
            "planned",
            backend=backend,
            journal=journal.as_posix(),
            command=argv,
            next_action="Run finish --apply only after implementation publication evidence is recorded.",
        )
    result = runner.run(argv, cwd=root)
    check_active_ownership(
        runner, root, allow_closed=True, spec=bound_spec, dependencies_complete=True
    )
    journal = record_lifecycle_event(
        runner,
        root,
        "finish",
        "applied" if apply else "checked",
        bound_bead_id=bead_id,
        backend=backend,
    )
    return result_payload(
        "finish",
        "applied" if apply else "checked",
        backend=backend,
        journal=journal.as_posix(),
        output=result.stdout.strip(),
        next_action=(
            "Publish any closeout commit, then close the bead and require the terminal "
            "Obsidian projection plus a subsequent no-op reconciliation."
        ),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("begin", "resume", "recover"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", default=".")
        command.add_argument("--registry", default=str(DEFAULT_REGISTRY))
        command.add_argument("--bead", required=name == "begin")
        command.add_argument("--slug")
        command.add_argument("--goal", action="append", default=[])
        if name == "begin":
            command.add_argument("--dry-run", action="store_true")
    attach_command = subparsers.add_parser("attach")
    attach_command.add_argument("--root", default=".")
    attach_command.add_argument("--bead", required=True)
    coordinate_command = subparsers.add_parser("coordinate", allow_abbrev=False)
    coordinate_command.add_argument("--root", required=True)
    coordinate_command.add_argument("--bead", required=True)
    coordinate_command.add_argument("--action", choices=("note", "create", "depend"), required=True)
    for field in ("text", "title", "description", "acceptance", "blocker"):
        coordinate_command.add_argument("--" + field)
    log_command = subparsers.add_parser("log", allow_abbrev=False)
    log_command.add_argument("--root", required=True)
    log_source = log_command.add_mutually_exclusive_group(required=True)
    log_source.add_argument("--evidence")
    log_source.add_argument("--pending-id")
    log_command.add_argument("--note", required=True)
    for name in ("checkpoint", "verify", "publish"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", default=".")
    finish = subparsers.add_parser("finish")
    finish.add_argument("--root", default=".")
    finish.add_argument("--apply", action="store_true")
    adopt = subparsers.add_parser("adopt-external")
    adopt.add_argument("--root", required=True)
    adopt.add_argument("--expect-bead-sha256", required=True)
    adopt.add_argument("--repair-legacy-wire", action="store_true")
    return parser.parse_args(argv)


def _dispatch(args, runner: CommandRunner, root: Path) -> dict[str, Any]:
    if args.command == "begin":
        payload = begin(
            root,
            args.bead,
            slug=args.slug,
            goals=args.goal,
            registry=Path(args.registry),
            dry_run=args.dry_run,
            runner=runner,
        )
    elif args.command in {"resume", "recover"}:
        bead_id = args.bead or active_bead_id(root)
        payload = resume(
            root,
            bead_id,
            slug=args.slug,
            goals=args.goal,
            registry=Path(args.registry),
            runner=runner,
        )
        payload["action"] = args.command
    elif args.command == "attach":
        payload = attach(root, args.bead, runner)
    elif args.command == "coordinate":
        from workflow_coordinate import coordinate

        fields = {
            key: getattr(args, key)
            for key in ("text", "title", "description", "acceptance", "blocker")
            if getattr(args, key) is not None
        }
        payload = coordinate(root, args.bead, args.action, fields, runner)
    elif args.command == "log":
        from workflow_coordinate import log

        payload = log(root, args.evidence, args.note, runner, pending_id=args.pending_id)
    elif args.command == "checkpoint":
        payload = _checkpoint(root, runner)
    elif args.command == "verify":
        payload = _verify(root, runner)
    elif args.command == "publish":
        payload = _publish(root, runner)
    elif args.command == "adopt-external":
        from workflow_ownership_reconcile import adopt_external

        payload = adopt_external(
            root, args.expect_bead_sha256, runner, repair_legacy_wire=args.repair_legacy_wire
        )
    else:
        payload = _finish(root, runner, apply=args.apply)
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runner = CommandRunner()
    root = Path(args.root).expanduser().resolve()
    try:
        dry = args.command == "begin" and args.dry_run
        lock = (
            nullcontext()
            if dry
            else workflow_lock(runner, root, Path(getattr(args, "registry", DEFAULT_REGISTRY)))
        )
        with lock:
            payload = _dispatch(args, runner, root)
    except Exception as exc:  # noqa: BLE001 - stable fail-closed CLI boundary.
        print(f"gas-city-workflow: BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
