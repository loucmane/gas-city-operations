#!/usr/bin/env python3
"""Transactional begin/resume implementation for Gas City workflow worktrees."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from project_context import DEFAULT_REGISTRY, build_context
from _repo_structure import load_repo_structure
from workflow_common import (
    PHASES,
    BeginSpec,
    CommandRunner,
    WorkflowError,
    advance_journal,
    atomic_write_json,
    derive_begin_spec,
    initialize_journal,
    journal_path,
    load_bead,
    load_journal,
    require_journal_spec,
    result_payload,
    run_readiness,
    workflow_runtime_root,
)
from workflow_ownership import (
    ensure_external_owner,
    require_binding,
    require_external_candidate,
    owner_binding,
)


def _phase_at_least(journal: Mapping[str, Any], phase: str) -> bool:
    return PHASES.index(str(journal["phase"])) >= PHASES.index(phase)


def _worktree_records(runner: CommandRunner, canonical: Path) -> list[dict[str, str]]:
    result = runner.run(["git", "-C", str(canonical), "worktree", "list", "--porcelain"])
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines() + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key in {"worktree", "HEAD", "branch"}:
            current[key] = value
    return records


def _matching_worktree(
    runner: CommandRunner,
    spec: BeginSpec,
) -> dict[str, str] | None:
    expected_branch = f"refs/heads/{spec.branch}"
    matches = [
        item
        for item in _worktree_records(runner, Path(spec.canonical_root))
        if item.get("worktree") == spec.worktree or item.get("branch") == expected_branch
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise WorkflowError("branch/worktree identity resolves to multiple Git worktrees")
    record = matches[0]
    if record.get("worktree") != spec.worktree or record.get("branch") != expected_branch:
        raise WorkflowError("existing branch/worktree pair disagrees with the derived target")
    return record


def _ensure_worktree(
    runner: CommandRunner,
    spec: BeginSpec,
    journal: dict[str, Any],
    path: Path,
) -> None:
    existing = _matching_worktree(runner, spec)
    target = Path(spec.worktree)
    if existing is None:
        if target.exists():
            raise WorkflowError(f"derived worktree path already exists outside Git: {target}")
        branch_exists = (
            runner.run(
                [
                    "git",
                    "-C",
                    spec.canonical_root,
                    "show-ref",
                    "--verify",
                    "--quiet",
                    f"refs/heads/{spec.branch}",
                ],
                check=False,
            ).returncode
            == 0
        )
        if branch_exists:
            if not _phase_at_least(journal, "worktree-created"):
                raise WorkflowError("derived branch exists without a matching journal/worktree")
            runner.run(
                [
                    "git",
                    "-C",
                    spec.canonical_root,
                    "worktree",
                    "add",
                    spec.worktree,
                    spec.branch,
                ]
            )
        else:
            runner.run(
                [
                    "git",
                    "-C",
                    spec.canonical_root,
                    "worktree",
                    "add",
                    "-b",
                    spec.branch,
                    spec.worktree,
                    spec.base_commit,
                ]
            )
        existing = _matching_worktree(runner, spec)
    if existing is None or not target.is_dir():
        raise WorkflowError("Git did not materialize the derived worktree")
    if existing.get("HEAD") != spec.base_commit and not _phase_at_least(journal, "scaffolded"):
        status = runner.run(["git", "-C", spec.worktree, "status", "--porcelain=v1"]).stdout.strip()
        ancestor = runner.run(
            [
                "git",
                "-C",
                spec.canonical_root,
                "merge-base",
                "--is-ancestor",
                str(existing.get("HEAD") or ""),
                spec.base_commit,
            ],
            check=False,
        )
        if status or ancestor.returncode != 0:
            raise WorkflowError(
                "existing unscaffolded worktree cannot be safely fast-forwarded to the "
                "canonical base"
            )
        runner.run(["git", "-C", spec.worktree, "merge", "--ff-only", spec.base_commit])
        existing = _matching_worktree(runner, spec)
        if existing is None or existing.get("HEAD") != spec.base_commit:
            raise WorkflowError("worktree fast-forward did not reach the canonical base")
    if not _phase_at_least(journal, "worktree-created"):
        advance_journal(journal, "worktree-created")
        atomic_write_json(path, journal)


def _active_dirs(root: Path) -> list[Path]:
    active_root = load_repo_structure(root).work_tracking_active_root
    if not active_root.is_dir():
        return []
    return sorted(
        item for item in active_root.iterdir() if item.is_dir() and item.name.endswith("-ACTIVE")
    )


def _preserved_legacy_tracker(
    runner: CommandRunner,
    root: Path,
    spec: BeginSpec,
    tracker: Path,
) -> bool:
    if spec.workflow_profile != "beads-with-frozen-legacy-evidence":
        return False
    relative = tracker.relative_to(root).as_posix()
    exists_at_base = runner.run(
        [
            "git",
            "-C",
            str(root),
            "cat-file",
            "-e",
            f"{spec.base_commit}:{relative}/TRACKER.md",
        ],
        check=False,
    )
    unchanged = runner.run(
        ["git", "-C", str(root), "diff", "--quiet", spec.base_commit, "--", relative],
        check=False,
    )
    return exists_at_base.returncode == 0 and unchanged.returncode == 0


def _scaffold_state(runner: CommandRunner, root: Path, spec: BeginSpec) -> str:
    layout = load_repo_structure(root)
    active = _active_dirs(root)
    matching = [item for item in active if f"-{spec.bead_id}-" in item.name]
    unrelated = [item for item in active if item not in matching]
    preserved = all(_preserved_legacy_tracker(runner, root, spec, item) for item in unrelated)
    session_state = layout.session_state_path
    session_bead = None
    if session_state.is_file():
        try:
            payload = json.loads(session_state.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkflowError("sessions/state.json is invalid JSON") from exc
        task = payload.get("task") if isinstance(payload, dict) else None
        if isinstance(task, dict):
            session_bead = task.get("id")
    if session_bead is None:
        current_session = layout.current_session_link
        if current_session.is_symlink():
            try:
                session_text = current_session.resolve(strict=True).read_text(encoding="utf-8")
            except OSError as exc:
                raise WorkflowError("sessions/current is broken") from exc
            if f"**Bead**: `{spec.bead_id}`" in session_text:
                session_bead = spec.bead_id
    plan = layout.current_plan_link
    plan_text = ""
    if plan.is_symlink():
        try:
            plan_text = plan.resolve(strict=True).read_text(encoding="utf-8")
        except OSError as exc:
            raise WorkflowError("plans/current is broken") from exc
    exact = (
        len(matching) == 1
        and preserved
        and session_bead == spec.bead_id
        and f"bead_ids: [{spec.bead_id}]" in plan_text
        and f"branch_policy: {spec.branch}" in plan_text
    )
    if exact:
        return "exact"
    if (
        matching
        or not preserved
        or session_bead == spec.bead_id
        or f"bead_ids: [{spec.bead_id}]" in plan_text
    ):
        raise WorkflowError("partial or mismatched workflow scaffold requires explicit diagnosis")
    return "absent"


def run_profile_readiness(runner: CommandRunner, spec: BeginSpec) -> str:
    root = Path(spec.worktree)
    if spec.workflow_profile != "beads-with-frozen-legacy-evidence":
        return run_readiness(runner, root)
    branch = runner.run(["git", "-C", str(root), "branch", "--show-current"]).stdout.strip()
    if branch != spec.branch:
        raise WorkflowError(f"active branch is {branch or '<detached>'}, expected {spec.branch}")
    ancestor = runner.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", spec.base_commit, "HEAD"],
        check=False,
    )
    if ancestor.returncode != 0:
        raise WorkflowError("frozen workflow base is not an ancestor of HEAD")
    if _scaffold_state(runner, root, spec) != "exact":
        raise WorkflowError("lightweight bead-native scaffold is not exact")
    return "STATE: READY\nPROFILE: beads-with-frozen-legacy-evidence\n"


def _kickoff_command(
    spec: BeginSpec,
    goals: Sequence[str],
    registry: Path,
) -> tuple[list[str], Path]:
    target = Path(spec.worktree)
    goal_args = [part for goal in goals for part in ("--goal", goal)]
    foundation = target / ".aegis" / "foundation-manifest.json"
    runtime_root = workflow_runtime_root(registry)
    canonical_task = runtime_root / "scripts" / "codex-task"
    if not foundation.is_file():
        force_args = (
            ["--force"]
            if spec.workflow_profile == "beads-with-frozen-legacy-evidence" and _active_dirs(target)
            else []
        )
        return (
            [
                sys.executable,
                str(canonical_task),
                "wizard",
                "kickoff",
                "--target-dir",
                str(target),
                "--bead",
                spec.bead_id,
                "--slug",
                spec.slug,
                "--title",
                spec.title,
                "--task-source",
                f"Gas City bead {spec.bead_id}",
                "--handler-target",
                ".",
                *force_args,
                *goal_args,
            ],
            runtime_root,
        )
    return (
        [
            sys.executable,
            str(canonical_task),
            "aegis",
            "kickoff",
            "--target-dir",
            str(target),
            "--bead",
            spec.bead_id,
            "--slug",
            spec.slug,
            "--title",
            spec.title,
            "--no-create-branch",
            *goal_args,
        ],
        runtime_root,
    )


def _ensure_scaffold(
    runner: CommandRunner,
    spec: BeginSpec,
    journal: dict[str, Any],
    path: Path,
    goals: Sequence[str],
    registry: Path,
) -> None:
    target = Path(spec.worktree)
    if _scaffold_state(runner, target, spec) == "absent":
        argv, cwd = _kickoff_command(spec, goals, registry)
        runner.run(argv, cwd=cwd)
    if _scaffold_state(runner, target, spec) != "exact":
        raise WorkflowError("workflow kickoff did not create the exact expected scaffold")
    if not _phase_at_least(journal, "scaffolded"):
        advance_journal(journal, "scaffolded")
        atomic_write_json(path, journal)


def _ensure_ownership(
    runner: CommandRunner,
    spec: BeginSpec,
    journal: dict[str, Any],
    path: Path,
    registry: Path,
) -> dict[str, Any]:
    context = build_context(Path(spec.worktree), registry)
    bead = ensure_external_owner(runner, spec, context, journal, path)
    if not _phase_at_least(journal, "claimed"):
        advance_journal(journal, "claimed")
        atomic_write_json(path, journal)
    return bead


def begin(
    root: Path,
    bead_id: str,
    *,
    slug: str | None,
    goals: Sequence[str],
    registry: Path = DEFAULT_REGISTRY,
    dry_run: bool = False,
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    runner = runner or CommandRunner()
    spec, context, bead = derive_begin_spec(runner, root, bead_id, slug=slug, registry=registry)
    require_external_candidate(bead)
    path = journal_path(runner, spec)
    journal = load_journal(path)
    if journal is None:
        journal = initialize_journal(spec)
    else:
        stored_base = journal.get("spec", {}).get("base_commit")
        if not isinstance(stored_base, str) or not stored_base:
            raise WorkflowError("transition journal base commit is invalid")
        spec = replace(spec, base_commit=stored_base)
        require_journal_spec(journal, spec)
    ownership = journal.get("external_ownership", {}).get(bead_id)
    if ownership and ownership.get("state") == "verified":
        require_binding(bead, owner_binding(spec, context))
    elif journal["phase"] in {"claimed", "ready"} and not ownership:
        raise WorkflowError("legacy ownership requires explicit exact-digest reconciliation")
    elif bead.get("status") != "open" and not ownership:
        raise WorkflowError("in_progress work without external ownership cannot be adopted")
    if dry_run:
        return result_payload(
            "begin",
            "planned",
            spec=spec.payload(),
            phase=journal["phase"],
            journal=path.as_posix(),
            bead_status=bead.get("status"),
        )

    atomic_write_json(path, journal)
    _ensure_worktree(runner, spec, journal, path)
    _ensure_scaffold(runner, spec, journal, path, goals, registry)
    bead = _ensure_ownership(runner, spec, journal, path, registry)
    readiness = run_profile_readiness(runner, spec)
    if "STATE: READY" not in readiness:
        raise WorkflowError("readiness command succeeded without a READY state")
    if not _phase_at_least(journal, "ready"):
        advance_journal(journal, "ready")
        atomic_write_json(path, journal)
    context = build_context(Path(spec.worktree), registry)
    require_binding(load_bead(runner, context, bead_id), owner_binding(spec, context))
    return result_payload(
        "begin",
        "ready",
        spec=spec.payload(),
        phase=journal["phase"],
        journal=path.as_posix(),
        bead_status=bead.get("status"),
        readiness="READY",
        context=context,
    )


def resume(
    root: Path,
    bead_id: str,
    *,
    slug: str | None,
    goals: Sequence[str],
    registry: Path = DEFAULT_REGISTRY,
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    runner = runner or CommandRunner()
    if slug is None:
        provisional, _, _ = derive_begin_spec(
            runner,
            root,
            bead_id,
            slug=None,
            registry=registry,
        )
        existing = load_journal(journal_path(runner, provisional))
        if existing is not None:
            stored_slug = existing.get("spec", {}).get("slug")
            if not isinstance(stored_slug, str) or not stored_slug:
                raise WorkflowError("transition journal slug is invalid")
            slug = stored_slug
    return begin(
        root,
        bead_id,
        slug=slug,
        goals=goals,
        registry=registry,
        dry_run=False,
        runner=runner,
    )
