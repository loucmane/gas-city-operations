"""Strict source-work checks for consumers without an installed Aegis runtime."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from workflow_common import CommandRunner, WorkflowError, plan_bead_ids, workflow_runtime_root
from workflow_ownership import check_active_ownership
from _repo_structure import load_repo_structure


def uses_portable_scaffold(root: Path) -> bool:
    """Never replace a present (even broken) installed or source adapter."""
    markers = (
        ".aegis/foundation-manifest.json",
        ".aegis/state/current-work.json",
        ".aegis/state/pending-tracking.json",
        ".claude/scripts/readiness.sh",
        "scripts/codex-task",
    )
    return not any(os.path.lexists(root / name) for name in markers)


def load_shared_runtime() -> None:
    """Use the selected Operations source, not the consumer or a stale install."""
    runtime = workflow_runtime_root().resolve()
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    import aegis_foundation

    if not Path(aegis_foundation.__file__).resolve().is_relative_to(runtime):
        raise WorkflowError("portable checks loaded a different Aegis runtime")


def run_portable_readiness(runner: CommandRunner, root: Path) -> str:
    """Reuse the strict Beads scaffold checks, with live external ownership."""
    load_shared_runtime()
    from aegis_foundation.gate.models import BLOCKED
    from aegis_foundation.gate.session_authority import assert_no_pending_continuation
    from aegis_foundation.gate.workflow import build_bead_source_checks

    if not uses_portable_scaffold(root):
        raise WorkflowError("portable readiness cannot replace a present Aegis adapter")
    spec = check_active_ownership(runner, root)
    if spec.workflow_profile != "beads-with-aegis-evidence":
        raise WorkflowError("portable readiness requires the modern Beads evidence profile")
    if plan_bead_ids(root) != [spec.bead_id]:
        raise WorkflowError("portable plan must name exactly the journal primary Bead")
    layout = load_repo_structure(root)
    for link in (layout.current_session_link, layout.current_plan_link):
        if not link.is_symlink() or not link.resolve().is_relative_to(root.resolve()):
            raise WorkflowError(f"portable {link.relative_to(root)} must be a target-local symlink")
    try:
        assert_no_pending_continuation(root)
        _, checks = build_bead_source_checks(root, spec.branch, spec.bead_id)
    except (OSError, ValueError, RuntimeError) as exc:
        raise WorkflowError(f"portable scaffold inspection failed: {exc}") from exc
    failures = [check.message for check in checks if check.status == BLOCKED]
    if failures:
        raise WorkflowError("portable readiness blocked: " + "; ".join(failures))
    check_active_ownership(runner, root)
    return "STATE: READY\nPROFILE: portable-beads-source\n" + "\n".join(
        f"[ready] {check.message}" for check in checks
    ) + "\n"
