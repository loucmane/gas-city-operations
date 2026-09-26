"""The `evidence-write` class: a create-only native Write into `<W>`'s reports (ga-fsfg R4).

A canonical-seat Claude session may create one new evidence file under the `reports/`
directory of the single ACTIVE work-tracking folder of an Operations worktree `<W>`.
The Write is stationary, like the coordination verbs: `<W>` passes the target
validation `coordinate` uses, and readiness, observation, the pending event and
advisory handling are evaluated at `<W>`. `workflow.py log --root <W> --pending-id
<id>` discharges the event.

Claude's own Write tool performs the write, so the gate cannot open the file itself.
The pre-check reads every existing component with `lstat` and never follows a link;
a path swapped between that check and the write is an accepted race.
"""

from __future__ import annotations

import fnmatch
import os
import stat
import sys
from pathlib import Path
from typing import Any

from .contracts import Payload

ACTIVE = ("docs", "ai", "work-tracking", "active")
ACTIVE_MARKER = "/docs/ai/work-tracking/active/"
ACTIVE_SUFFIX = "-ACTIVE"
REPORTS = "reports"
DESCRIPTOR = Path(".gas-city-workflow.json")
MAX_BYTES = 1024 * 1024
SUFFIXES = frozenset({".md", ".txt", ".json", ".jsonl", ".log"})
# Names an agent, a test runner or the interpreter may load as instructions or code.
# Matched against the case-folded name, so any spelling refuses.
TRUSTED_NAMES = (
    "claude*.md",
    "agents*.md",
    "gemini*.md",
    "*skill.md",
    "conftest.py",
    "*.pth",
    "*.py",
)
KNOWN_MODES = frozenset({"default", "manual", "dontAsk", "acceptEdits", "auto"})


def evidence_write_claim(seat: Path, payload: Payload) -> tuple[dict[str, Any], Path, str] | None:
    """The profile, worktree root and path when this class owns the Write, else None.

    The class owns a Write whose absolute path names `docs/ai/work-tracking/active/`
    below a direct child of the Operations worktree root or of a registered or review
    project's worktree root, sent from a canonical seat whose profile lists
    `evidence-write`. Anything else keeps today's behaviour. An owned Write that breaks
    any rule is refused by `evidence_write_target`.
    """

    from .native_permissions import EVIDENCE_WRITE, PROFILE, _profile

    if payload.tool_name != "Write":
        return None
    path = payload.tool_input.get("file_path")
    if not isinstance(path, str) or not path.startswith("/") or ACTIVE_MARKER not in path:
        return None
    # A linked worktree's own session (a gitfile, not a directory) is never the seat.
    if not (seat / PROFILE).exists() or not (seat / ".git").is_dir():
        return None
    profile = _profile(seat)
    if (
        profile is None
        or EVIDENCE_WRITE not in profile["commands"]
        or str(seat) != profile["canonical_root"]
    ):
        return None
    roots = [profile["worktree_root"]]
    for key in ("registered_projects", "review_projects"):
        roots.extend(entry["worktree_root"] for entry in profile.get(key, []))
    for root in roots:
        if path.startswith(root + "/"):
            return profile, Path(root), path
    return None


def evidence_write_target(
    seat: Path, payload: Payload, *, post_success: bool = False
) -> Path | None:
    """Select `<W>` for an evidence write, or None when the Write is not one.

    PostToolUse does not rerun the "must not exist" rule, which the write itself makes
    false: it rechecks `<W>`, the single ACTIVE `reports/` directory and the written file.
    """

    claim = evidence_write_claim(seat, payload)
    if claim is None:
        return None
    profile, worktree_root, path = claim
    if worktree_root != Path(profile["worktree_root"]):
        raise ValueError(
            "evidence-write requires an Operations worktree; registered-project and "
            "review-project worktrees refuse"
        )
    if payload.cwd != str(seat):
        raise ValueError("evidence-write must originate at the canonical seat")
    if payload.permission_mode not in KNOWN_MODES:
        raise ValueError("evidence-write requires a known non-plan permission mode")
    if not path.isprintable():
        raise ValueError("evidence-write path contains a control character")
    if os.path.normpath(path) != path or path.startswith("//"):
        raise ValueError("evidence-write path must be a canonical absolute path")
    parts = Path(path).relative_to(worktree_root).parts
    if (
        len(parts) < 8
        or parts[1:5] != ACTIVE
        or not parts[5].endswith(ACTIVE_SUFFIX)
        or parts[6] != REPORTS
    ):
        raise ValueError(
            "evidence-write path must lie under "
            "<W>/docs/ai/work-tracking/active/<folder>-ACTIVE/reports/"
        )
    below = parts[7:]
    for name in below:
        _ordinary(name)
    if Path(below[-1]).suffix not in SUFFIXES:
        raise ValueError("evidence-write file suffix must be .md, .txt, .json, .jsonl or .log")
    target = worktree_root / parts[0]
    _validate_target(seat, profile, target)
    reports = _single_active_reports(target, parts[5])
    if post_success:
        _written(reports, below)
    else:
        _creatable(reports, below)
        content = payload.tool_input.get("content")
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_BYTES:
            raise ValueError("evidence-write content must be text of at most 1 MiB")
    return target


def _ordinary(name: str) -> None:
    folded = name.casefold()
    if name.startswith(".") or any(
        fnmatch.fnmatchcase(folded, pattern) for pattern in TRUSTED_NAMES
    ):
        raise ValueError(f"evidence-write refuses the name {name!r} below reports/")


def _validate_target(seat: Path, profile: dict[str, Any], target: Path) -> None:
    """The target validation `coordinate` applies to an Operations worktree."""

    from .coordination import _journal, _reviewed_target_runtime
    from .native_permissions import EVIDENCE_WRITE, _bound_bytes, _profile
    from .runtime_state import current_work_is_observation, required_pending_tracking_events

    if (
        target.resolve(strict=True) != target
        or target.parent != Path(profile["worktree_root"])
        or target == seat
    ):
        raise ValueError("evidence-write target must be a direct registered linked worktree")
    if _profile(target) != profile or _bound_bytes(target, DESCRIPTOR) != _bound_bytes(
        seat, DESCRIPTOR
    ):
        raise ValueError("evidence-write target has divergent project policy")
    _reviewed_target_runtime(target, seat)
    _journal(target, seat, profile, EVIDENCE_WRITE, {})
    for governed in (seat, target):
        if current_work_is_observation(governed):
            raise ValueError("evidence-write requires non-observation state at seat and target")
        if required_pending_tracking_events(governed):
            raise ValueError("evidence-write requires pending tracking to be resolved")


def _real_directory(path: Path) -> None:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        raise ValueError(f"evidence-write never creates {path}") from None
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"evidence-write requires {path} to be a real directory, not a link")


def _single_active_reports(target: Path, folder: str) -> Path:
    """`<W>`'s only `*-ACTIVE` folder must be the named one, with an existing `reports/`."""

    directory = target
    for name in ACTIVE:
        directory = directory / name
        _real_directory(directory)
    with os.scandir(directory) as entries:
        active = sorted(entry.name for entry in entries if entry.name.endswith(ACTIVE_SUFFIX))
    if active != [folder]:
        raise ValueError(
            "evidence-write requires exactly one ACTIVE folder in <W>, the one the path names"
        )
    _real_directory(directory / folder)
    _real_directory(directory / folder / REPORTS)
    return directory / folder / REPORTS


def _creatable(reports: Path, below: tuple[str, ...]) -> None:
    """PreToolUse: every existing component below reports/ is a real directory; no target."""

    current = reports
    for name in below[:-1]:
        current = current / name
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return  # The Write creates the rest; nothing below this component exists.
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("evidence-write path has a link or non-directory component")
    try:
        os.lstat(current / below[-1])
    except FileNotFoundError:
        return
    raise ValueError("evidence-write target already exists; the class only creates files")


def _written(reports: Path, below: tuple[str, ...]) -> None:
    """PostToolUse: the written file is regular, singly linked and within the bound."""

    current = reports
    for name in below[:-1]:
        current = current / name
        if not stat.S_ISDIR(os.lstat(current).st_mode):
            raise ValueError("evidence-write path has a link or non-directory component")
    info = os.lstat(current / below[-1])
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
        raise ValueError(
            "evidence-write target is not a regular, singly linked file of at most 1 MiB"
        )


def record_evidence_write_event(worktree: Path, payload: Payload) -> int:
    """PostToolUse: record the Write's pending event on `<W>`, never through delivery."""

    from .evidence import record_pending_tracking_event

    try:
        record_pending_tracking_event(worktree, payload)
    except Exception as exc:  # noqa: BLE001 - reported below; the tracking is incomplete.
        print(
            f"Aegis: evidence-write tracking on {worktree} failed ({type(exc).__name__}: "
            f"{exc}); stop and reconcile before further work.",
            file=sys.stderr,
        )
        return 2
    return 0
