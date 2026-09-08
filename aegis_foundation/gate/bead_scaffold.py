"""Beads-native scaffold checks for the shared repository evidence layout."""

from __future__ import annotations

import re
from pathlib import Path

from .models import BLOCKED, READY, Check
from .repo_structure import load_repo_structure
from .state import (
    check_plan_tracker_alignment,
    plan_bead_ids,
    plan_branch_policies,
    read_json,
    read_text,
    symlink_target,
    text_references_work,
)


def build_bead_source_checks(root: Path, branch: str, bead_id: str) -> tuple[str, list[Check]]:
    checks: list[Check] = [
        Check(READY, f"branch '{branch}' maps to bead-native source work {bead_id}")
    ]

    try:
        layout = load_repo_structure(root)
    except (OSError, ValueError) as exc:
        return bead_id, [Check(BLOCKED, f"invalid repository evidence layout: {exc}")]
    session_current = layout.current_session_link
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

        state_path = layout.session_state_path
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

    plan_current = layout.current_plan_link
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

    active_root = layout.work_tracking_active_root
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
