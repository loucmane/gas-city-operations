"""Transactional evidence notes for journal-owned, uninstalled source projects.

This is not an Aegis installation or a native pending-event consumer. The workflow
journal remains the ownership authority; all writes reuse the session WAL.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from workflow_common import CommandRunner, WorkflowError
from workflow_ownership import check_active_ownership
from workflow_portable import load_shared_runtime, run_portable_readiness


def log_portable_evidence(root: Path, evidence: str, note: str, runner: CommandRunner) -> dict:
    """Append a single exact-file note to current S:W:H:E surfaces, or no-op."""
    load_shared_runtime()
    from aegis_foundation.gate.session_authority import contained_path
    from aegis_foundation.gate.session_transition import SessionTransition, session_lock

    root = root.resolve()
    if any(char in evidence + note for char in ("\n", "\r", "\x00")) or any(
        char in evidence for char in ("[", "]", "|")
    ):
        raise WorkflowError("portable evidence notes must be single-line and delimiter-safe")
    with session_lock(root):
        run_portable_readiness(runner, root)
        spec = check_active_ownership(runner, root)
        artifact = contained_path(root, evidence, "portable evidence")
        if not artifact.is_file():
            raise WorkflowError("portable evidence must name an existing target-local file")
        session = (root / "sessions/current").resolve(strict=True)
        # Validate physical ancestors too: a contained symlink is not a write grant.
        contained_path(root, session.relative_to(root).as_posix(), "portable session")
        front_matter = session.read_text().split("---", 2)
        if len(front_matter) != 3 or front_matter[0].strip():
            raise WorkflowError("portable session front matter is invalid")
        dates = re.findall(r"^date: (\d{4}-\d{2}-\d{2})$", front_matter[1], re.MULTILINE)
        now = datetime.now().astimezone()
        if dates != [now.date().isoformat()]:
            raise WorkflowError("portable logging requires the current daily session; continue it first")
        active = next((root / "docs/ai/work-tracking/active").glob("*-ACTIVE"))
        paths = [session] + [active / name for name in (
            "TRACKER.md", "IMPLEMENTATION.md", "CHANGELOG.md", "FINDINGS.md", "DECISIONS.md", "HANDOFF.md"
        )]
        if artifact in paths:
            raise WorkflowError("portable evidence cannot be a surface changed by this log")
        before = {}
        for path in paths:
            contained_path(root, path.relative_to(root).as_posix(), "portable log target")
            if not path.is_file():
                raise WorkflowError("portable log target is missing")
            before[path] = path.read_bytes()
        evidence_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
        identity = hashlib.sha256(json.dumps({
            "bead": spec.bead_id, "session": session.relative_to(root).as_posix(),
            "evidence": evidence, "evidence_sha256": evidence_sha256, "note": note,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        marker = f"<!-- portable-work-log:{identity} -->"
        occurrences = [text.count(marker.encode()) for text in before.values()]
        if any(occurrences):
            if occurrences != [1] * len(paths):
                raise WorkflowError("portable log replay is partial or duplicated; preserve and reconcile")
            return {"backend": "portable-source-log", "idempotent": True, "record_sha256": identity}
        swhe = f"[S:{now:%Y%m%d}|W:{spec.bead_id}-{spec.slug}|H:workflow-coordinate|E:{evidence}]"
        entry = f"\n- **[{now:%H:%M}]** — {swhe} {note} (sha256={evidence_sha256}) {marker}\n"
        with SessionTransition(root, spec.bead_id, paths, lock_held=True) as transaction:
            for path in paths:
                transaction.write(path, before[path] + entry.encode())
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != evidence_sha256:
                raise WorkflowError("portable evidence changed while logging")
            check_active_ownership(runner, root)
        run_portable_readiness(runner, root)
        return {"backend": "portable-source-log", "idempotent": False, "record_sha256": identity}
