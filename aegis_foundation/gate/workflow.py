"""Workflow-authority policies for Aegis readiness."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from .models import BLOCKED, READY, Check
from .session_authority import SessionAuthorityError, assert_no_pending_continuation, verify_session_authority
from .session_transition import session_lock
from .state import (
    aegis_integration_required,
    aegis_work_mode,
    aegis_work_task,
    bead_id_from_branch,
    check_plan_tracker_alignment,
    find_task,
    parse_plan_statuses,
    parse_tracker_statuses,
    plan_bead_ids,
    plan_branch_policies,
    read_json,
    read_text,
    run_git,
    symlink_target,
    task_id_from_branch,
    taskmaster_tasks_payload,
    text_references_task,
    text_references_work,
)


def check_taskmaster_task(root: Path, task_id: str, *, required: bool, checks: list[Check]) -> None:
    tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
    if not tasks_path.is_file():
        if required:
            checks.append(
                Check(
                    BLOCKED,
                    "Taskmaster is required by Aegis current work but tasks file is missing",
                )
            )
        return

    try:
        payload = taskmaster_tasks_payload(read_json(tasks_path))
    except Exception as exc:  # noqa: BLE001 - surface exact readiness failure.
        if required:
            checks.append(Check(BLOCKED, f"could not read required Taskmaster tasks: {exc}"))
        else:
            checks.append(Check(READY, f"Taskmaster present but optional and unreadable: {exc}"))
        return

    if payload is None:
        if required:
            checks.append(Check(BLOCKED, "required Taskmaster tasks JSON has an unsupported shape"))
        else:
            checks.append(Check(READY, "Taskmaster present but optional and has unsupported shape"))
        return

    tag, tasks = payload
    task = find_task(tasks, task_id)
    if not task:
        if required:
            checks.append(
                Check(BLOCKED, f"required Taskmaster Task {task_id} missing from tag '{tag}'")
            )
        else:
            checks.append(
                Check(
                    READY,
                    f"Taskmaster present but optional; Task {task_id} not found in tag '{tag}'",
                )
            )
        return

    status = task.get("status")
    if status != "in-progress":
        if required:
            checks.append(
                Check(
                    BLOCKED,
                    f"Taskmaster Task {task_id} status is {status!r}, expected 'in-progress'",
                )
            )
        else:
            checks.append(
                Check(READY, f"Taskmaster Task {task_id} is optional with status {status!r}")
            )
        return

    prefix = "Required Taskmaster" if required else "Optional Taskmaster"
    checks.append(Check(READY, f"{prefix} Task {task_id} is in-progress"))


def load_source_workflow_state(root: Path):
    """Load the source-only resolver only from an uninstalled Aegis source tree."""

    if (root / ".aegis" / "foundation-manifest.json").exists():
        return None
    if (root / ".aegis" / "state" / "current-work.json").exists():
        return None
    markers = (
        root / "schemas" / "aegis" / "foundation-manifest.schema.json",
        root / "scripts" / "_aegis_installer.py",
        root / ".claude" / "scripts" / "readiness.sh",
        root / "aegis_foundation" / "assets" / ".claude" / "scripts" / "readiness.sh",
        root / "aegis_foundation" / "assets" / "scripts" / "codex-guard",
    )
    if not all(path.is_file() for path in markers):
        return None
    try:
        pyproject_text = read_text(root / "pyproject.toml")
    except OSError:
        return None
    if not re.search(r'^name\s*=\s*["\']aegis-foundation["\']\s*$', pyproject_text, re.MULTILINE):
        return None

    helper_path = root / "scripts" / "_source_workflow_state.py"
    if not helper_path.is_file():
        return None
    module_name = "_aegis_source_workflow_state_runtime"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load source workflow helper: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    previous_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_dont_write_bytecode
    return module


def build_completed_source_checks(
    root: Path,
    work_id: str,
    source_work: object,
    checks: list[Check],
) -> tuple[str | None, list[Check]]:
    tracker_path = Path(getattr(source_work, "tracker_path"))
    archive_folder = Path(getattr(source_work, "archive_folder"))
    work_kind = str(getattr(source_work, "work_kind", "task"))
    is_bead = work_kind == "bead"
    label = f"Bead {work_id}" if is_bead else f"Task {work_id}"
    if is_bead:
        checks.append(
            Check(READY, f"completed source Bead {work_id} evidence is internally consistent")
        )
    else:
        checks.append(
            Check(READY, f"Taskmaster Task {work_id} is done for derived source closeout")
        )
    checks.append(
        Check(
            READY,
            f"completed source tracker derived from {archive_folder.relative_to(root).as_posix()}",
        )
    )

    session_current = root / "sessions" / "current"
    session_path, session_target = symlink_target(session_current)
    if session_path is None or session_target is None:
        checks.append(Check(BLOCKED, "sessions/current symlink missing"))
    elif not session_path.is_file():
        checks.append(Check(BLOCKED, f"sessions/current points to missing file: {session_target}"))
    else:
        session_text = read_text(session_path)
        references = text_references_work if is_bead else text_references_task
        if not references(session_text, work_id):
            checks.append(
                Check(BLOCKED, f"current session does not reference completed {label}")
            )
        else:
            checks.append(Check(READY, f"current session references completed {label}"))

        state_path = root / "sessions" / "state.json"
        if not state_path.is_file():
            checks.append(Check(BLOCKED, "sessions/state.json missing"))
        else:
            try:
                state = read_json(state_path)
            except Exception as exc:  # noqa: BLE001 - surface exact readiness failure.
                checks.append(Check(BLOCKED, f"sessions/state.json invalid: {exc}"))
            else:
                current_value = state.get("current") if isinstance(state, dict) else None
                if current_value != session_path.name:
                    checks.append(
                        Check(
                            BLOCKED,
                            f"sessions/state.json current is {current_value!r}, expected {session_path.name!r}",
                        )
                    )
                else:
                    checks.append(
                        Check(READY, "sessions/state.json current matches sessions/current")
                    )

    plan_current = root / "plans" / "current"
    plan_path, plan_target = symlink_target(plan_current)
    plan_text: str | None = None
    if plan_path is None or plan_target is None:
        checks.append(Check(BLOCKED, "plans/current symlink missing"))
    elif not plan_path.is_file():
        checks.append(Check(BLOCKED, f"plans/current points to missing file: {plan_target}"))
    else:
        plan_text = read_text(plan_path)
        references = text_references_work if is_bead else text_references_task
        if not references(plan_text, work_id):
            checks.append(
                Check(BLOCKED, f"current plan does not reference completed {label}")
            )
        else:
            checks.append(Check(READY, f"current plan references completed {label}"))

    tracker_text = read_text(tracker_path)
    checks.append(Check(READY, f"completed tracker references {label}"))
    if plan_text is not None:
        alignment_issues = check_plan_tracker_alignment(plan_text, tracker_text)
        plan_statuses = parse_plan_statuses(plan_text)
        tracker_statuses = parse_tracker_statuses(tracker_text)
        for step in ("plan-step-scope", "plan-step-implement", "plan-step-verify"):
            if plan_statuses.get(step) != "completed":
                alignment_issues.append(
                    f"completed source plan has {step}={plan_statuses.get(step)!r}"
                )
            if tracker_statuses.get(step) != "completed":
                alignment_issues.append(
                    f"completed source tracker has {step}={tracker_statuses.get(step)!r}"
                )
        if alignment_issues:
            for issue in alignment_issues:
                checks.append(Check(BLOCKED, f"completed plan/tracker alignment failure: {issue}"))
        else:
            checks.append(Check(READY, "completed plan and tracker steps align"))

    return work_id, checks


def build_observation_checks(
    root: Path, branch: str, aegis_work: object
) -> tuple[str | None, list[Check]]:
    checks: list[Check] = []
    task = aegis_work_task(aegis_work)
    paths = (
        aegis_work.get("paths")
        if isinstance(aegis_work, dict) and isinstance(aegis_work.get("paths"), dict)
        else {}
    )
    work_id = str(task.get("id") if task else "").strip()
    slug = str(task.get("slug") if task else "").strip()
    status = str(aegis_work.get("status") if isinstance(aegis_work, dict) else "").strip()

    if not task or not work_id or not slug or status != "in-progress":
        checks.append(
            Check(BLOCKED, "observation current work is missing id, slug, or in-progress status")
        )
        return work_id or None, checks

    checks.append(
        Check(READY, f"branch '{branch}' is accepted for observation mode without a task ID")
    )
    checks.append(Check(READY, f"Aegis observation {work_id} is in-progress"))

    session_rel = str(paths.get("session") or "").strip()
    plan_rel = str(paths.get("plan") or "").strip()
    work_rel = str(paths.get("work_tracking") or "").strip()
    if not session_rel or not plan_rel or not work_rel:
        checks.append(Check(BLOCKED, "observation current work paths are incomplete"))
        return work_id, checks

    session_current = root / "sessions" / "current"
    session_path, session_target = symlink_target(session_current)
    if session_path is None or session_target is None:
        checks.append(Check(BLOCKED, "sessions/current symlink missing"))
    elif session_path.relative_to(root).as_posix() != session_rel:
        checks.append(
            Check(BLOCKED, f"sessions/current does not point to observation session {session_rel}")
        )
    elif not session_path.is_file():
        checks.append(Check(BLOCKED, f"sessions/current points to missing file: {session_target}"))
    else:
        session_text = read_text(session_path)
        if not text_references_work(session_text, work_id):
            checks.append(
                Check(BLOCKED, f"active session does not reference observation {work_id}")
            )
        else:
            checks.append(Check(READY, f"active session references observation {work_id}"))

    plan_current = root / "plans" / "current"
    plan_path, plan_target = symlink_target(plan_current)
    plan_text: str | None = None
    if plan_path is None or plan_target is None:
        checks.append(Check(BLOCKED, "plans/current symlink missing"))
    elif plan_path.relative_to(root).as_posix() != plan_rel:
        checks.append(
            Check(BLOCKED, f"plans/current does not point to observation plan {plan_rel}")
        )
    elif not plan_path.is_file():
        checks.append(Check(BLOCKED, f"plans/current points to missing file: {plan_target}"))
    else:
        plan_text = read_text(plan_path)
        if not text_references_work(plan_text, work_id):
            checks.append(Check(BLOCKED, f"active plan does not reference observation {work_id}"))
        else:
            checks.append(Check(READY, f"active plan references observation {work_id}"))

    tracker_path = root / work_rel / "TRACKER.md"
    tracker_text: str | None = None
    if not (root / work_rel).is_dir():
        checks.append(Check(BLOCKED, f"observation work-tracking folder missing: {work_rel}"))
    elif not tracker_path.is_file():
        checks.append(Check(BLOCKED, f"{tracker_path.relative_to(root)} missing"))
    else:
        tracker_text = read_text(tracker_path)
        if not text_references_work(tracker_text, work_id):
            checks.append(
                Check(BLOCKED, f"active tracker does not reference observation {work_id}")
            )
        else:
            checks.append(Check(READY, f"active tracker references observation {work_id}"))

    if plan_text is not None and tracker_text is not None:
        alignment_issues = check_plan_tracker_alignment(plan_text, tracker_text)
        if alignment_issues:
            for issue in alignment_issues:
                checks.append(Check(BLOCKED, f"plan/tracker alignment failure: {issue}"))
        else:
            checks.append(Check(READY, "plan-step statuses align between plan and tracker"))

    return work_id, checks


def build_bead_source_checks(root: Path, branch: str, bead_id: str) -> tuple[str, list[Check]]:
    checks: list[Check] = [
        Check(READY, f"branch '{branch}' maps to bead-native source work {bead_id}")
    ]

    session_current = root / "sessions" / "current"
    session_path, session_target = symlink_target(session_current)
    if session_path is None or session_target is None:
        checks.append(Check(BLOCKED, "sessions/current symlink missing"))
    elif not session_path.is_file():
        checks.append(Check(BLOCKED, f"sessions/current points to missing file: {session_target}"))
    else:
        session_text = read_text(session_path)
        if not text_references_work(session_text, bead_id):
            checks.append(Check(BLOCKED, f"current session does not reference bead {bead_id}"))
        else:
            checks.append(Check(READY, f"current session references bead {bead_id}"))

        state_path = root / "sessions" / "state.json"
        if not state_path.is_file():
            checks.append(Check(BLOCKED, "sessions/state.json missing"))
        else:
            try:
                state = read_json(state_path)
            except Exception as exc:  # noqa: BLE001 - surface exact readiness failure.
                checks.append(Check(BLOCKED, f"sessions/state.json invalid: {exc}"))
            else:
                current_value = state.get("current") if isinstance(state, dict) else None
                if current_value != session_path.name:
                    checks.append(
                        Check(
                            BLOCKED,
                            f"sessions/state.json current is {current_value!r}, expected {session_path.name!r}",
                        )
                    )
                else:
                    checks.append(
                        Check(READY, "sessions/state.json current matches sessions/current")
                    )

    plan_current = root / "plans" / "current"
    plan_path, plan_target = symlink_target(plan_current)
    plan_text: str | None = None
    if plan_path is None or plan_target is None:
        checks.append(Check(BLOCKED, "plans/current symlink missing"))
    elif not plan_path.is_file():
        checks.append(Check(BLOCKED, f"plans/current points to missing file: {plan_target}"))
    else:
        plan_text = read_text(plan_path)
        bead_ids = plan_bead_ids(plan_text)
        if bead_id not in bead_ids:
            checks.append(Check(BLOCKED, f"current plan does not declare bead {bead_id}"))
        else:
            checks.append(Check(READY, f"current plan declares bead {bead_id}"))
        policies = plan_branch_policies(plan_text)
        if policies != {branch}:
            rendered = ", ".join(sorted(policies)) or "none"
            checks.append(
                Check(
                    BLOCKED, f"current plan branch policy is {rendered}, expected exactly {branch}"
                )
            )
        else:
            checks.append(Check(READY, f"current plan branch policy matches {branch}"))

    active_root = root / "docs" / "ai" / "work-tracking" / "active"
    tracker_text: str | None = None
    if not active_root.is_dir():
        checks.append(Check(BLOCKED, "active work-tracking root missing"))
    else:
        active_folders = sorted(
            path
            for path in active_root.iterdir()
            if path.is_dir() and path.name.endswith("-ACTIVE")
        )
        if len(active_folders) != 1:
            checks.append(
                Check(
                    BLOCKED,
                    f"expected exactly one ACTIVE work-tracking folder, found {len(active_folders)}",
                )
            )
        else:
            active_folder = active_folders[0]
            bead_token = re.compile(
                rf"(?:^|[-_]){re.escape(bead_id)}(?:[-_]|$)", flags=re.IGNORECASE
            )
            if not bead_token.search(active_folder.name):
                checks.append(
                    Check(
                        BLOCKED,
                        f"ACTIVE folder '{active_folder.name}' does not match bead {bead_id}",
                    )
                )
            else:
                checks.append(
                    Check(READY, f"ACTIVE folder '{active_folder.name}' matches bead {bead_id}")
                )

            tracker_path = active_folder / "TRACKER.md"
            if not tracker_path.is_file():
                checks.append(Check(BLOCKED, f"{tracker_path.relative_to(root)} missing"))
            else:
                tracker_text = read_text(tracker_path)
                if not text_references_work(tracker_text, bead_id):
                    checks.append(
                        Check(BLOCKED, f"active tracker does not reference bead {bead_id}")
                    )
                elif not re.search(
                    r"^\*\*Status\*\*:\s*ACTIVE\s*$", tracker_text, flags=re.MULTILINE
                ):
                    checks.append(Check(BLOCKED, "active tracker status is not ACTIVE"))
                else:
                    checks.append(Check(READY, f"active tracker references bead {bead_id}"))

    if plan_text is not None and tracker_text is not None:
        alignment_issues = check_plan_tracker_alignment(plan_text, tracker_text)
        if alignment_issues:
            for issue in alignment_issues:
                checks.append(Check(BLOCKED, f"plan/tracker alignment failure: {issue}"))
        else:
            checks.append(Check(READY, "plan-step statuses align between plan and tracker"))

    return bead_id, checks


def build_checks(root: Path) -> tuple[str | None, list[Check]]:
    checks: list[Check] = []

    code, inside_work_tree, err = run_git(root, "rev-parse", "--is-inside-work-tree")
    if code != 0 or inside_work_tree != "true":
        checks.append(
            Check(BLOCKED, f"{root} is not a git work tree: {err or inside_work_tree or 'unknown'}")
        )
        return None, checks

    code, branch, err = run_git(root, "branch", "--show-current")
    if code != 0 or not branch:
        checks.append(
            Check(BLOCKED, f"could not determine current git branch: {err or 'empty branch'}")
        )
        return None, checks

    aegis_work_path = root / ".aegis" / "state" / "current-work.json"
    try:
        assert_no_pending_continuation(root)
    except SessionAuthorityError as exc:
        checks.append(Check(BLOCKED, f"session authority mismatch: {exc}"))
        return None, checks
    aegis_work: object | None = None
    ignore_current_work_for_readiness = False
    if aegis_work_path.is_file():
        try:
            aegis_work = read_json(aegis_work_path)
        except Exception as exc:  # noqa: BLE001 - surface exact readiness failure.
            checks.append(Check(BLOCKED, f"could not read Aegis current work state: {exc}"))
            return None, checks
        if aegis_work_mode(aegis_work) == "observation":
            status = str(aegis_work.get("status") if isinstance(aegis_work, dict) else "").strip()
            if status == "in-progress":
                return build_observation_checks(root, branch, aegis_work)
            if status == "completed":
                task = aegis_work_task(aegis_work)
                work_id = str(task.get("id") if task else "").strip()
                checks.append(
                    Check(READY, f"Aegis observation {work_id or '<unknown>'} is completed")
                )
                ignore_current_work_for_readiness = True
            else:
                checks.append(
                    Check(
                        BLOCKED,
                        f"Aegis observation status is {status!r}, expected 'in-progress' or 'completed'",
                    )
                )
                return None, checks
        if aegis_work_mode(aegis_work) == "bead":
            task = aegis_work_task(aegis_work)
            bead_id = str(task.get("id") if task else "").strip()
            status = str(task.get("status") if task else "").strip()
            branch_bead_id = bead_id_from_branch(branch)
            if not task or not bead_id or status != "in-progress":
                checks.append(
                    Check(BLOCKED, "bead current work is missing id or in-progress status")
                )
                return bead_id or None, checks
            if branch_bead_id != bead_id:
                checks.append(
                    Check(
                        BLOCKED,
                        f"branch bead is {branch_bead_id!r}, expected current-work bead {bead_id}",
                    )
                )
                return bead_id, checks
            try:
                with session_lock(root, shared=True):
                    verify_session_authority(root, aegis_work)
            except (SessionAuthorityError, OSError, ValueError) as exc:
                checks.append(Check(BLOCKED, f"session authority mismatch: {exc}"))
                return bead_id, checks
            work_id, bead_checks = build_bead_source_checks(root, branch, bead_id)
            bead_checks.insert(1, Check(READY, f"Aegis current work bead {bead_id} is in-progress"))
            return work_id, bead_checks

    source_work = None
    if not aegis_work_path.is_file():
        try:
            source_module = load_source_workflow_state(root)
            source_lifecycle = (
                source_module.derive_source_lifecycle(root, branch)
                if source_module is not None
                else None
            )
        except Exception as exc:  # noqa: BLE001 - source contradictions fail closed.
            checks.append(Check(BLOCKED, f"source closeout derivation failed: {exc}"))
            # Preserve the lifecycle contradiction as a hard block, but continue with
            # the branch-specific source checks when possible. Those checks expose the
            # exact session/plan/tracker mismatch that an operator can repair instead
            # of collapsing every contradiction into the derivation exception alone.
            source_bead_id = bead_id_from_branch(branch)
            if source_bead_id is not None:
                work_id, bead_checks = build_bead_source_checks(root, branch, source_bead_id)
                return work_id, checks + bead_checks
            return task_id_from_branch(branch), checks
        if source_lifecycle is not None:
            lifecycle_state = str(getattr(source_lifecycle, "state"))
            lifecycle_work_id = getattr(source_lifecycle, "work_id", None)
            if lifecycle_state == source_module.LIFECYCLE_CLOSEOUT_PENDING:
                checks.append(
                    Check(
                        BLOCKED,
                        "source lifecycle is CLOSEOUT_PENDING; run "
                        "`python3 scripts/codex-task work-tracking reconcile` before kickoff or mutation",
                    )
                )
                return str(lifecycle_work_id) if lifecycle_work_id else None, checks
            checks.append(Check(READY, f"source lifecycle is {lifecycle_state}"))
            branch_work_id = bead_id_from_branch(branch) or task_id_from_branch(branch)
            if lifecycle_state == source_module.LIFECYCLE_IDLE and (
                branch_work_id is None or branch_work_id == lifecycle_work_id
            ):
                source_work = getattr(source_lifecycle, "completed_work", None)
        if source_work is not None:
            work_id = str(getattr(source_work, "work_id", source_work.task_id))
            work_kind = str(getattr(source_work, "work_kind", "task"))
            if work_kind == "bead":
                branch_bead_id = bead_id_from_branch(branch)
                message = (
                    f"branch '{branch}' maps to completed source Bead {work_id}"
                    if branch_bead_id
                    else f"default branch '{branch}' derives completed source Bead {work_id}"
                )
            else:
                branch_task_id = task_id_from_branch(branch)
                message = (
                    f"branch '{branch}' maps to Task {work_id}"
                    if branch_task_id
                    else f"default branch '{branch}' derives completed source Task {work_id}"
                )
            checks.append(Check(READY, message))
            return build_completed_source_checks(root, work_id, source_work, checks)
        source_bead_id = bead_id_from_branch(branch)
        if source_module is not None and source_bead_id is not None:
            work_id, bead_checks = build_bead_source_checks(root, branch, source_bead_id)
            return work_id, checks + bead_checks

    task_id = task_id_from_branch(branch)
    if not task_id:
        checks.append(Check(BLOCKED, f"branch '{branch}' does not contain a task ID"))
        return None, checks
    checks.append(Check(READY, f"branch '{branch}' maps to Task {task_id}"))

    if aegis_work_path.is_file() and not ignore_current_work_for_readiness:
        try:
            aegis_work = aegis_work if aegis_work is not None else read_json(aegis_work_path)
            task = aegis_work_task(aegis_work)
        except Exception as exc:  # noqa: BLE001 - surface exact readiness failure.
            checks.append(Check(BLOCKED, f"could not read Aegis current work state: {exc}"))
        else:
            if task is None:
                checks.append(Check(BLOCKED, "Aegis current work state has an unsupported shape"))
            elif str(task.get("id")) != task_id:
                checks.append(
                    Check(
                        BLOCKED,
                        f"Aegis current work task is {task.get('id')!r}, expected Task {task_id}",
                    )
                )
            elif task.get("status") != "in-progress":
                checks.append(
                    Check(
                        BLOCKED,
                        f"Aegis current work status is {task.get('status')!r}, expected 'in-progress'",
                    )
                )
            else:
                try:
                    with session_lock(root, shared=True):
                        verify_session_authority(root, aegis_work)
                except (SessionAuthorityError, OSError, ValueError) as exc:
                    checks.append(Check(BLOCKED, f"session authority mismatch: {exc}"))
                    return task_id, checks
                checks.append(Check(READY, f"Aegis current work Task {task_id} is in-progress"))
                check_taskmaster_task(
                    root,
                    task_id,
                    required=aegis_integration_required(aegis_work, "taskmaster"),
                    checks=checks,
                )
    elif (root / ".taskmaster" / "tasks" / "tasks.json").is_file():
        check_taskmaster_task(root, task_id, required=True, checks=checks)
    else:
        checks.append(Check(BLOCKED, "no Taskmaster tasks file or Aegis current work state found"))

    session_current = root / "sessions" / "current"
    session_path, session_target = symlink_target(session_current)
    if session_path is None or session_target is None:
        checks.append(Check(BLOCKED, "sessions/current symlink missing"))
    elif not session_path.is_file():
        checks.append(Check(BLOCKED, f"sessions/current points to missing file: {session_target}"))
    else:
        session_text = read_text(session_path)
        if not text_references_task(session_text, task_id):
            checks.append(Check(BLOCKED, f"active session does not reference Task {task_id}"))
        else:
            checks.append(Check(READY, f"active session references Task {task_id}"))

        state_path = root / "sessions" / "state.json"
        if not state_path.is_file():
            checks.append(Check(BLOCKED, "sessions/state.json missing"))
        else:
            try:
                state = read_json(state_path)
            except Exception as exc:  # noqa: BLE001 - surface exact readiness failure.
                checks.append(Check(BLOCKED, f"sessions/state.json invalid: {exc}"))
            else:
                current_value = state.get("current") if isinstance(state, dict) else None
                if current_value != session_path.name:
                    checks.append(
                        Check(
                            BLOCKED,
                            f"sessions/state.json current is {current_value!r}, expected {session_path.name!r}",
                        )
                    )
                else:
                    checks.append(
                        Check(READY, "sessions/state.json current matches sessions/current")
                    )

    plan_current = root / "plans" / "current"
    plan_path, plan_target = symlink_target(plan_current)
    plan_text: str | None = None
    if plan_path is None or plan_target is None:
        checks.append(Check(BLOCKED, "plans/current symlink missing"))
    elif not plan_path.is_file():
        checks.append(Check(BLOCKED, f"plans/current points to missing file: {plan_target}"))
    else:
        plan_text = read_text(plan_path)
        if not text_references_task(plan_text, task_id):
            checks.append(Check(BLOCKED, f"active plan does not reference Task {task_id}"))
        else:
            checks.append(Check(READY, f"active plan references Task {task_id}"))

    active_root = root / "docs" / "ai" / "work-tracking" / "active"
    tracker_text: str | None = None
    if not active_root.is_dir():
        checks.append(Check(BLOCKED, "active work-tracking root missing"))
    else:
        active_folders = sorted(
            path
            for path in active_root.iterdir()
            if path.is_dir() and path.name.endswith("-ACTIVE")
        )
        if len(active_folders) != 1:
            checks.append(
                Check(
                    BLOCKED,
                    f"expected exactly one ACTIVE work-tracking folder, found {len(active_folders)}",
                )
            )
        else:
            active_folder = active_folders[0]
            if not re.search(
                rf"(?:^|[-_])task-?{re.escape(task_id)}(?:[-_]|$)", active_folder.name
            ):
                checks.append(
                    Check(
                        BLOCKED,
                        f"ACTIVE folder '{active_folder.name}' does not match Task {task_id}",
                    )
                )
            else:
                checks.append(
                    Check(READY, f"ACTIVE folder '{active_folder.name}' matches Task {task_id}")
                )

            tracker_path = active_folder / "TRACKER.md"
            if not tracker_path.is_file():
                checks.append(Check(BLOCKED, f"{tracker_path.relative_to(root)} missing"))
            else:
                tracker_text = read_text(tracker_path)
                if not text_references_task(tracker_text, task_id):
                    checks.append(
                        Check(BLOCKED, f"active tracker does not reference Task {task_id}")
                    )
                else:
                    checks.append(Check(READY, f"active tracker references Task {task_id}"))

    if plan_text is not None and tracker_text is not None:
        alignment_issues = check_plan_tracker_alignment(plan_text, tracker_text)
        if alignment_issues:
            for issue in alignment_issues:
                checks.append(Check(BLOCKED, f"plan/tracker alignment failure: {issue}"))
        else:
            checks.append(Check(READY, "plan-step statuses align between plan and tracker"))

    return task_id, checks
