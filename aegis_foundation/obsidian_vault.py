"""Deterministic, read-only Obsidian projection for Aegis evidence.

The vault is a disposable view, never workflow authority.  It consumes normalized
ledger events plus repository-owned task, capsule, and legacy workflow files and
renders a bounded graph of Markdown notes and Obsidian Bases.  It never writes to
the target repository, never copies raw commands, and never edits an existing
directory that it cannot prove it owns.
"""

from __future__ import annotations

from aegis_foundation.git_read import run_git_read

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from aegis_foundation import work_authority

SCHEMA_VERSION = "1"
GENERATOR = "aegis-foundation:obsidian-vault"
MANIFEST_NAME = ".aegis-vault.json"
DEFAULT_VAULT_DIRNAME = "obsidian-vault"

HIGH_SIGNAL_EVENT_TYPES = frozenset(
    {
        "checkpoint",
        "delivery",
        "operator_authority",
        "risk",
        "scope",
        "session_begin",
        "session_end",
        "bead_truth",
        "task_truth",
        "tool_failure",
        "verification",
        "witness",
        "work_truth",
    }
)
EVIDENCE_EVENT_TYPES = frozenset(
    {
        "delivery",
        "operator_authority",
        "risk",
        "bead_truth",
        "task_truth",
        "tool_failure",
        "verification",
        "witness",
        "work_truth",
    }
)
LEGACY_PREFIXES = (
    "sessions/",
    "plans/",
    "docs/ai/work-tracking/",
)
LEGACY_ROOT_FILES = frozenset({"HANDOFF.md", "STATUS.md"})
SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(authorization\s*[:=]\s*)[^\s]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/=]+"), "Bearer [REDACTED]"),
    (re.compile(r"\b(?:ghp|github_pat|sk)_[A-Za-z0-9_\-]{8,}\b"), "[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}(?:\.[A-Za-z0-9_\-]+){1,2}"), "[REDACTED]"),
)
_TASK_IN_TEXT = re.compile(r"(?i)(?:task[-_ ]?)(\d+(?:\.\d+)?)")
_TASK_BRANCH = re.compile(r"(?i)(?:^|/)feat/task-(\d+)(?:-|$)")
_BEAD_IN_TEXT = re.compile(
    r"(?<![a-z0-9])([a-z][a-z0-9]*-[a-z0-9][a-z0-9-]*(?:\.[1-9][0-9]*)*)(?![a-z0-9.-])"
)
_BEAD_BRANCH = re.compile(
    r"(?i)^codex/([a-z][a-z0-9]*-[a-z0-9][a-z0-9-]*(?:\.[1-9][0-9]*)*)(?:-|$)"
)
_MARKER_BEGIN = re.compile(r"<!--\s*AEGIS:BEGIN\b")
_MARKER_END = re.compile(r"<!--\s*AEGIS:END\b")


class VaultError(RuntimeError):
    """Raised when a vault cannot be derived or safely replaced."""


@dataclass(frozen=True)
class VaultLimits:
    """Hard ceilings that keep the derived view safe for agents and humans."""

    max_tasks: int = 2_000
    # Per-bead worktrees multiply sessions, branches and worktrees (blog had 547
    # sessions on 2026-10-19). max_identity_edges still bounds the projection.
    max_sessions: int = 5_000
    max_branches: int = 5_000
    max_agents: int = 5_000
    max_worktrees: int = 5_000
    max_identity_edges: int = 5_000
    max_evidence_notes: int = 1_000
    max_legacy_documents: int = 5_000
    max_legacy_bytes: int = 2 * 1024 * 1024
    max_body_chars: int = 2_000


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_json(value: Any) -> str:
    return _digest_bytes(_canonical_json(value).encode("utf-8"))


def _redact(value: Any, *, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    if len(text) > limit:
        suffix = "…#" + _digest_bytes(text.encode("utf-8"))[:10]
        text = text[: max(0, limit - len(suffix))] + suffix
    return text


def _yaml_value(value: Any) -> str:
    """Render JSON scalars/collections; JSON is valid YAML and deterministic."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _frontmatter(properties: Mapping[str, Any]) -> str:
    lines = ["---"]
    for key in sorted(properties):
        lines.append(f"{key}: {_yaml_value(properties[key])}")
    lines.extend(("---", ""))
    return "\n".join(lines)


def _markdown(properties: Mapping[str, Any], title: str, body: Iterable[str]) -> str:
    lines = [_frontmatter(properties), f"# {_redact(title, limit=200)}", ""]
    lines.extend(body)
    return "\n".join(lines).rstrip() + "\n"


def _slug(value: Any, *, fallback: str = "unknown", limit: int = 60) -> str:
    source = _redact(value, limit=300).lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", source).strip("-._") or fallback
    slug = slug[:limit].rstrip("-._") or fallback
    return f"{slug}-{_digest_bytes(source.encode('utf-8'))[:8]}"


def _link(path: str, label: str | None = None) -> str:
    target = path[:-3] if path.endswith(".md") else path
    return f"[[{target}|{_redact(label, limit=160)}]]" if label else f"[[{target}]]"


def _git(target: Path, *args: str) -> str:
    try:
        result = run_git_read(
            ["git", *args],
            cwd=str(target),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise VaultError(f"unable to inspect git repository at {target}: {exc}") from exc
    if result.returncode != 0:
        detail = _redact(result.stderr or result.stdout, limit=300)
        raise VaultError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def repository_root(target_dir: str | Path) -> Path:
    target = Path(target_dir).expanduser().resolve()
    root = Path(_git(target, "rev-parse", "--show-toplevel")).resolve()
    if not root.is_dir():
        raise VaultError(f"repository root does not exist: {root}")
    return root


def default_vault_path(ledger_store_dir: str | Path) -> Path:
    return Path(ledger_store_dir).expanduser().resolve() / DEFAULT_VAULT_DIRNAME


def _natural_id_key(value: str) -> tuple[Any, ...]:
    return tuple(int(part) if part.isdigit() else part for part in re.split(r"[.-]", value))


def _selected_capsule(root: Path) -> dict[str, Any]:
    path = root / ".aegis" / "capsule" / "current.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid"}
    if not isinstance(payload, Mapping):
        return {"status": "invalid"}
    selected: dict[str, Any] = {"status": "available"}
    keys = (
        "active_work",
        "active_task",
        "active_subtask",
        "next_action",
        "orientation_source",
        "branch",
        "head",
        "suggested_next",
    )
    containers = [payload]
    for name in ("task_truth", "orientation", "repository", "git"):
        value = payload.get(name)
        if isinstance(value, Mapping):
            containers.append(value)
    for key in keys:
        for container in containers:
            if key in container:
                value = container[key]
                if isinstance(value, Mapping):
                    selected[key] = {
                        str(item_key): _redact(item_value, limit=240)
                        for item_key, item_value in value.items()
                        if item_key in {"id", "title", "status", "action", "command", "reason"}
                    }
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    selected[key] = _redact(value, limit=500) if isinstance(value, str) else value
                break
    selected["source_digest"] = _digest_bytes(path.read_bytes())
    return selected


def _legacy_kind(path: Path) -> str:
    name = path.name.upper()
    if name == "DECISIONS.MD":
        return "decision-record"
    if name in {"FINDINGS.MD", "HANDOFF.MD"}:
        return "risk-context"
    if name == "TRACKER.MD":
        return "tracker"
    if name == "IMPLEMENTATION.MD":
        return "implementation"
    if name == "CHANGELOG.MD":
        return "changelog"
    if "SESSION" in name or path.parts[0:1] == ("sessions",):
        return "session"
    if "PLAN" in name or path.parts[0:1] == ("plans",):
        return "plan"
    return "legacy-document"


def _legacy_inventory(root: Path, limits: VaultLimits) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    for prefix in LEGACY_PREFIXES:
        base = root / prefix
        if base.is_dir():
            candidates.extend(
                path for path in base.rglob("*.md") if path.is_file() and not path.is_symlink()
            )
    for filename in LEGACY_ROOT_FILES:
        path = root / filename
        if path.is_file() and not path.is_symlink():
            candidates.append(path)
    unique = sorted({path.resolve() for path in candidates})
    if len(unique) > limits.max_legacy_documents:
        raise VaultError(
            f"legacy projection exceeds document limit ({len(unique)} > {limits.max_legacy_documents})"
        )
    records: list[dict[str, Any]] = []
    for path in unique:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        size = path.stat().st_size
        if size > limits.max_legacy_bytes:
            records.append(
                {
                    "path": relative,
                    "kind": _legacy_kind(Path(relative)),
                    "bytes": size,
                    "status": "oversized-not-read",
                    "human_nonblank_lines": None,
                    "headings": [],
                    "checkboxes": None,
                    "sweh_entries": None,
                    "generated_blocks": None,
                    "task_ids": sorted(set(_TASK_IN_TEXT.findall(relative)), key=_natural_id_key),
                    "work_ids": sorted(
                        set(_TASK_IN_TEXT.findall(relative)) | set(_BEAD_IN_TEXT.findall(relative))
                    ),
                    "content_digest": None,
                }
            )
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        outside: list[str] = []
        headings: list[str] = []
        generated_depth = 0
        generated_blocks = 0
        for line in text.splitlines():
            if _MARKER_BEGIN.search(line):
                generated_depth += 1
                generated_blocks += 1
                continue
            if _MARKER_END.search(line):
                generated_depth = max(0, generated_depth - 1)
                continue
            if generated_depth:
                continue
            if line.strip():
                outside.append(line.rstrip())
                if line.lstrip().startswith("#") and len(headings) < 24:
                    headings.append(_redact(line.lstrip("# "), limit=180))
        normalized = "\n".join(" ".join(line.split()) for line in outside)
        task_ids = set(_TASK_IN_TEXT.findall(relative + "\n" + "\n".join(headings)))
        bead_ids = set(_BEAD_IN_TEXT.findall(relative + "\n" + "\n".join(headings)))
        records.append(
            {
                "path": relative,
                "kind": _legacy_kind(Path(relative)),
                "bytes": size,
                "status": "read",
                "human_nonblank_lines": len(outside),
                "headings": headings,
                "checkboxes": sum(1 for line in outside if re.match(r"^\s*[-*]\s+\[[ xX]\]", line)),
                "sweh_entries": sum(1 for line in outside if "[S:" in line and "|W:" in line),
                "generated_blocks": generated_blocks,
                "task_ids": sorted(task_ids, key=_natural_id_key),
                "work_ids": sorted(task_ids | bead_ids),
                "content_digest": _digest_bytes(normalized.encode("utf-8")),
            }
        )
    return records


def _safe_extra(event: Mapping[str, Any]) -> dict[str, Any]:
    raw_extra = event.get("extra")
    extra: Mapping[str, Any] = raw_extra if isinstance(raw_extra, Mapping) else {}
    allowed = (
        "action",
        "gate",
        "package",
        "passed",
        "pr_number",
        "reason",
        "report_path",
        "status",
        "bead_id",
        "task_id",
        "work_authority",
        "work_id",
    )
    result: dict[str, Any] = {}
    for key in allowed:
        value = extra.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = _redact(value, limit=500) if isinstance(value, str) else value
    return result


def _event_record(event: Mapping[str, Any]) -> dict[str, Any]:
    raw_paths = event.get("paths")
    paths: list[Any] = raw_paths if isinstance(raw_paths, list) else []
    return {
        "event_id": _redact(event.get("event_id"), limit=100),
        "ts": _redact(event.get("ts"), limit=80),
        "event_type": _redact(event.get("event_type"), limit=80) or "unknown",
        "session_id": _redact(event.get("session_id"), limit=160),
        "branch": _redact(event.get("branch"), limit=240),
        "head": _redact(event.get("head"), limit=80),
        "worktree": _redact(event.get("worktree_root"), limit=500),
        "agent_id": _redact(event.get("agent_id"), limit=240),
        "agent_type": _redact(event.get("agent_type"), limit=80),
        "parent_agent_id": _redact(event.get("parent_agent_id"), limit=240),
        "outcome": _redact(event.get("outcome"), limit=40),
        "exit_class": _redact(event.get("exit_class"), limit=40),
        "handler": _redact(event.get("handler"), limit=120),
        "tool_name": _redact(event.get("tool_name"), limit=120),
        "paths": [_redact(path, limit=400) for path in paths[:64]],
        "extra": _safe_extra(event),
    }


def _identity_records(
    events: Sequence[Mapping[str, Any]], limits: VaultLimits
) -> list[dict[str, str]]:
    """Deduplicate stable topology from all rows without copying low-level events."""

    fields = (
        "session_id",
        "branch",
        "worktree",
        "agent_id",
        "agent_type",
        "parent_agent_id",
    )
    records = {
        tuple(str(event.get(field) or "") for field in fields)
        for event in events
        if any(event.get(field) for field in fields)
    }
    if len(records) > limits.max_identity_edges:
        raise VaultError(
            "identity projection exceeds edge limit "
            f"({len(records)} > {limits.max_identity_edges})"
        )
    result = [dict(zip(fields, values)) for values in sorted(records)]
    ceilings = {
        "session_id": limits.max_sessions,
        "branch": limits.max_branches,
        "agent_id": limits.max_agents,
        "worktree": limits.max_worktrees,
    }
    for field, ceiling in ceilings.items():
        values = {record[field] for record in result if record[field]}
        if field == "agent_id":
            values.update(
                record["parent_agent_id"] for record in result if record["parent_agent_id"]
            )
        if len(values) > ceiling:
            raise VaultError(
                f"identity projection exceeds {field} limit ({len(values)} > {ceiling})"
            )
    return result


def _work_from_event(event: Mapping[str, Any]) -> str:
    raw_extra = event.get("extra")
    extra: Mapping[str, Any] = raw_extra if isinstance(raw_extra, Mapping) else {}
    for value in (
        extra.get("bead_id"),
        extra.get("work_id"),
        extra.get("task_id"),
        extra.get("task"),
    ):
        if isinstance(value, Mapping):
            value = value.get("id")
        text = str(value or "").strip()
        if work_authority.BEAD_ID_PATTERN.fullmatch(text):
            return text
        if text.isdigit() or re.fullmatch(r"\d+(?:\.\d+)+", text):
            return text
        match = _TASK_IN_TEXT.search(text)
        if match:
            return match.group(1)
    branch = str(event.get("branch") or "")
    bead_match = _BEAD_BRANCH.search(branch)
    if bead_match:
        return bead_match.group(1)
    task_match = _TASK_BRANCH.search(branch)
    return task_match.group(1) if task_match else ""


def collect_snapshot(
    target_dir: str | Path,
    events: Sequence[Mapping[str, Any]],
    *,
    repository_identity: str | None = None,
    bead_snapshot: str | Path | None = None,
    include_bead_content: bool = False,
    limits: VaultLimits | None = None,
) -> dict[str, Any]:
    """Collect a deterministic, redacted model without modifying the target."""

    active_limits = limits or VaultLimits()
    root = repository_root(target_dir)
    normalized_events = [_event_record(event) for event in events]
    high_signal = [
        event for event in normalized_events if event["event_type"] in HIGH_SIGNAL_EVENT_TYPES
    ]
    high_signal.sort(key=lambda event: (event["ts"], event["event_id"]))
    common_dir = Path(_git(root, "rev-parse", "--git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    canonical_name = common_dir.parent.name if common_dir.name == ".git" else root.name
    context_identity = repository_identity or next(
        (
            _redact(event.get("repository_identity"), limit=160)
            for event in events
            if event.get("repository_identity")
        ),
        "",
    )
    if not context_identity:
        context_identity = "sha256:" + _digest_bytes(common_dir.as_posix().encode("utf-8"))
    try:
        work = work_authority.collect_work_authority(
            root,
            bead_snapshot=bead_snapshot,
            include_bead_content=include_bead_content,
            max_items=active_limits.max_tasks,
        )
    except work_authority.WorkAuthorityError as exc:
        raise VaultError(str(exc)) from exc
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "repository": {
            "name": _redact(canonical_name, limit=160),
            "identity": context_identity,
            "head": _git(root, "rev-parse", "HEAD"),
            "branch": _git(root, "branch", "--show-current"),
        },
        "work_authority": {key: value for key, value in work.items() if key != "items"},
        "work_items": work["items"],
        "tasks": [item for item in work["items"] if item["authority"] == "taskmaster"],
        "capsule": _selected_capsule(root),
        "legacy_documents": _legacy_inventory(root, active_limits),
        "events": high_signal,
        "identities": _identity_records(normalized_events, active_limits),
        "event_summary": {
            "high_signal_count": len(high_signal),
            "by_type": dict(sorted(Counter(event["event_type"] for event in high_signal).items())),
            "latest_ts": max((event["ts"] for event in high_signal), default=""),
        },
        "limits": active_limits.__dict__,
    }
    snapshot["source_digest"] = _digest_json(snapshot)
    return snapshot


def _relation_maps(snapshot: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    work = {
        str(item["id"]): (
            f"Beads/{item['id']}.md"
            if item.get("authority") == "beads"
            else f"Tasks/task-{item['id']}.md"
        )
        for item in snapshot.get("work_items", snapshot.get("tasks", []))
    }
    tasks = {
        str(item["id"]): work[str(item["id"])]
        for item in snapshot.get("work_items", snapshot.get("tasks", []))
        if item.get("authority") == "taskmaster"
    }
    beads = {
        str(item["id"]): work[str(item["id"])]
        for item in snapshot.get("work_items", [])
        if item.get("authority") == "beads"
    }
    identities = [item for item in snapshot.get("identities", []) if isinstance(item, Mapping)]
    sessions = sorted(
        {str(item.get("session_id") or "") for item in identities if item.get("session_id")}
    )
    branches = sorted({str(item.get("branch") or "") for item in identities if item.get("branch")})
    agents = sorted(
        {
            value
            for item in identities
            for value in (
                str(item.get("agent_id") or ""),
                str(item.get("parent_agent_id") or ""),
            )
            if value
        }
    )
    worktrees = sorted(
        {str(item.get("worktree") or "") for item in identities if item.get("worktree")}
    )
    return {
        "work": work,
        "tasks": tasks,
        "beads": beads,
        "sessions": {value: f"Sessions/{_slug(value)}.md" for value in sessions},
        "branches": {value: f"Branches/{_slug(value)}.md" for value in branches},
        "agents": {value: f"Agents/{_slug(value)}.md" for value in agents},
        "worktrees": {value: f"Worktrees/{_slug(value)}.md" for value in worktrees},
    }


def _event_links(event: Mapping[str, Any], maps: Mapping[str, Mapping[str, str]]) -> list[str]:
    links: list[str] = []
    work_id = _work_from_event(event)
    if work_id not in maps["work"]:
        branch = str(event.get("branch") or "")
        for bead_id in sorted(maps["beads"], key=len, reverse=True):
            if branch == f"codex/{bead_id}" or branch.startswith(f"codex/{bead_id}-"):
                work_id = bead_id
                break
    if work_id in maps["work"]:
        kind = "Bead" if work_id in maps["beads"] else "Task"
        links.append(_link(maps["work"][work_id], f"{kind} {work_id}"))
    for field, key, label in (
        ("session_id", "sessions", "Session"),
        ("branch", "branches", "Branch"),
        ("agent_id", "agents", "Agent"),
        ("parent_agent_id", "agents", "Parent agent"),
        ("worktree", "worktrees", "Worktree"),
    ):
        value = str(event.get(field) or "")
        if value and value in maps[key]:
            display = Path(value).name if field == "worktree" else value
            links.append(_link(maps[key][value], f"{label}: {_redact(display, limit=80)}"))
    return links


def _render_base(kind: str, title: str, columns: Sequence[str]) -> str:
    order = "\n".join(f"      - {column}" for column in columns)
    return (
        "filters:\n"
        "  and:\n"
        f"    - 'aegis_kind == \"{kind}\"'\n"
        "views:\n"
        "  - type: table\n"
        f"    name: {_yaml_value(title)}\n"
        "    order:\n"
        f"{order}\n"
    )


def _render_work_base() -> str:
    return (
        "filters:\n"
        "  or:\n"
        "    - 'aegis_kind == \"bead\"'\n"
        "    - 'aegis_kind == \"task\"'\n"
        "views:\n"
        "  - type: table\n"
        '    name: "Work"\n'
        "    order:\n"
        "      - file.name\n"
        "      - authority\n"
        "      - status\n"
        "      - priority\n"
        "      - work_id\n"
    )


def render_vault(snapshot: Mapping[str, Any]) -> dict[str, bytes]:
    """Render every owned file as UTF-8 bytes, excluding the ownership manifest."""

    limits = VaultLimits(**dict(snapshot.get("limits") or {}))
    maps = _relation_maps(snapshot)
    files: dict[str, bytes] = {}

    def add(path: str, text: str) -> None:
        normalized = Path(path).as_posix()
        if normalized.startswith("/") or ".." in Path(normalized).parts:
            raise VaultError(f"unsafe generated path: {path}")
        files[normalized] = text.encode("utf-8")

    repository = snapshot["repository"]
    event_summary = snapshot["event_summary"]
    legacy = snapshot["legacy_documents"]
    authority = snapshot.get("work_authority", {})
    work_items = snapshot.get("work_items", snapshot.get("tasks", []))
    home_body = [
        "This vault is a generated, read-only view of Aegis evidence. Edit the authoritative repository or ledger—not these notes.",
        "",
        "## Current repository truth",
        f"- Branch: `{_redact(repository['branch'], limit=160)}`",
        f"- HEAD: `{_redact(repository['head'], limit=80)}`",
        f"- Work authority: `{_redact(authority.get('authority'), limit=40)}`",
        f"- Work items: {len(work_items)}",
        f"- High-signal ledger events: {event_summary['high_signal_count']}",
        f"- Stable identity relationships: {len(snapshot.get('identities') or [])}",
        f"- Preserved legacy documents inventoried: {len(legacy)}",
        "- Low-level mutation and gate traffic is intentionally not expanded into notes.",
        "",
        "## Views",
        "- " + _link("Views/Work.base", "Current work authority"),
        "- " + _link("Views/Tasks.base", "Tasks"),
        "- " + _link("Views/Evidence.base", "Evidence"),
        "- " + _link("Views/Legacy.base", "Legacy documents"),
        "- " + _link("Orientation.md", "Computed orientation snapshot"),
        "- " + _link("Indexes/Activity.md", "Activity and evidence index"),
    ]
    add(
        "Home.md",
        _markdown(
            {
                "aegis_kind": "home",
                "aegis_schema": SCHEMA_VERSION,
                "repository": repository["name"],
                "source_digest": snapshot["source_digest"],
                "tags": ["aegis-vault"],
            },
            f"{repository['name']} Aegis Knowledge Vault",
            home_body,
        ),
    )
    add(
        "README.md",
        _markdown(
            {
                "aegis_kind": "readme",
                "aegis_schema": SCHEMA_VERSION,
                "tags": ["aegis-vault", "generated"],
            },
            "About this generated vault",
            [
                "- Authority remains in Git, Gas City beads when explicitly supplied, the passive Aegis ledger, and deterministic delivery evidence.",
                "- Taskmaster is a read-only compatibility source when no bead snapshot is supplied.",
                "- Rebuild with `aegis vault build`; verify with `aegis vault check`; gate readiness or closeout with `aegis vault gate`.",
                "- The generator refuses directories containing files it does not own.",
                "- Raw commands and low-level event payloads are not copied into the vault.",
                "- `.obsidian/` configuration and third-party plugins are intentionally not generated.",
            ],
        ),
    )

    raw_capsule = snapshot.get("capsule")
    capsule: Mapping[str, Any] = raw_capsule if isinstance(raw_capsule, Mapping) else {}
    orientation_body = [
        "The capsule is a computed orientation input; this note is only its bounded projection.",
        "",
    ]
    for key in sorted(capsule):
        if key == "source_digest":
            continue
        orientation_body.append(f"- **{key}**: `{_redact(capsule[key], limit=500)}`")
    active_work = capsule.get("active_work", capsule.get("active_task"))
    if isinstance(active_work, Mapping):
        work_id = str(active_work.get("id") or "")
        if work_id in maps["work"]:
            kind = "Bead" if work_id in maps["beads"] else "Task"
            orientation_body.append(
                f"- Related: {_link(maps['work'][work_id], f'{kind} {work_id}')}"
            )
    add(
        "Orientation.md",
        _markdown(
            {
                "aegis_kind": "orientation",
                "aegis_schema": SCHEMA_VERSION,
                "branch": repository["branch"],
                "head": repository["head"],
                "tags": ["aegis-vault", "orientation"],
            },
            "Computed orientation",
            orientation_body,
        ),
    )

    legacy_by_work: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for document in legacy:
        for work_id in document.get("work_ids", document.get("task_ids", [])):
            legacy_by_work[work_id].append(document)
    for item in work_items:
        work_id = str(item["id"])
        item_authority = str(item.get("authority") or "unknown")
        item_kind = "bead" if item_authority == "beads" else "task"
        display_kind = item_kind.title()
        body = [
            f"- Authority: **{item_authority}**",
            f"- Status: **{item['status']}**",
            f"- Priority: `{item['priority']}`",
            f"- Type: `{item.get('issue_type') or 'unknown'}`",
        ]
        if item.get("assignee"):
            body.append(f"- Assignee: `{item['assignee']}`")
        if item.get("updated_at"):
            body.append(f"- Updated: `{item['updated_at']}`")
        if item.get("description"):
            body.extend(("", "## Description", item["description"]))
        dependencies = []
        for dependency in item.get("dependencies", []):
            dependency_id = str(dependency.get("id") or "")
            relationship = str(dependency.get("type") or "related")
            if dependency_id in maps["work"]:
                dependencies.append(
                    f"`{relationship}` → {_link(maps['work'][dependency_id], dependency_id)}"
                )
            elif dependency_id:
                dependencies.append(f"`{relationship}` → `{dependency_id}` (external/unprojected)")
        if dependencies:
            body.extend(("", "## Dependencies", *(f"- {item}" for item in dependencies)))
        metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
        if metadata:
            body.extend(
                (
                    "",
                    "## Bounded metadata",
                    *(
                        f"- **{key}**: `{_redact(value, limit=500)}`"
                        for key, value in sorted(metadata.items())
                    ),
                )
            )
        related_legacy = legacy_by_work.get(work_id, [])
        if related_legacy:
            body.extend(
                (
                    "",
                    "## Preserved legacy context",
                    *(
                        f"- {_link('Legacy/' + _slug(item['path']) + '.md', item['path'])}"
                        for item in related_legacy[:40]
                    ),
                )
            )
        add(
            maps["work"][work_id],
            _markdown(
                {
                    "aegis_kind": item_kind,
                    "aegis_schema": SCHEMA_VERSION,
                    "authority": item_authority,
                    "priority": item["priority"],
                    "status": item["status"],
                    "work_id": work_id,
                    "task_id": work_id if item_kind == "task" else None,
                    "bead_id": work_id if item_kind == "bead" else None,
                    "tags": ["aegis-vault", f"aegis/{item_kind}"],
                },
                (
                    f"{display_kind} {work_id}: {item['title']}"
                    if item.get("title")
                    else f"{display_kind} {work_id}"
                ),
                body,
            ),
        )

    grouped_fields = {
        "sessions": "session_id",
        "branches": "branch",
        "agents": "agent_id",
        "worktrees": "worktree",
    }
    identity_records = [
        item for item in snapshot.get("identities", []) if isinstance(item, Mapping)
    ]
    for group, field in grouped_fields.items():
        grouped: dict[str, list[Mapping[str, Any]]] = {value: [] for value in maps[group]}
        identity_grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for event in snapshot["events"]:
            value = str(event.get(field) or "")
            if value:
                grouped[value].append(event)
            if group == "agents":
                parent = str(event.get("parent_agent_id") or "")
                if parent and parent != value:
                    grouped[parent].append(event)
        for identity in identity_records:
            value = str(identity.get(field) or "")
            if value:
                identity_grouped[value].append(identity)
            if group == "agents":
                parent = str(identity.get("parent_agent_id") or "")
                if parent and parent != value:
                    identity_grouped[parent].append(identity)
        for value in sorted(grouped):
            events = grouped[value]
            associations = identity_grouped[value]
            kind = group[:-1] if group.endswith("s") else group
            display = Path(value).name if group == "worktrees" else value
            event_types = dict(sorted(Counter(event["event_type"] for event in events).items()))
            body = [
                f"- High-signal evidence events: {len(events)}",
                f"- Stable identity relationships: {len(associations)}",
            ]
            if events:
                body.append(
                    f"- Latest high-signal evidence: `{max(event['ts'] for event in events)}`"
                )
            if event_types:
                body.append(
                    "- Event classes: "
                    + ", ".join(f"`{key}`={count}" for key, count in event_types.items())
                )
            relations: list[str] = []
            for event in events:
                relations.extend(_event_links(event, maps))
            for association in associations:
                relations.extend(_event_links(association, maps))
            unique_relations = list(dict.fromkeys(relations))[:80]
            if unique_relations:
                body.extend(("", "## Related nodes", *(f"- {item}" for item in unique_relations)))
            properties: dict[str, Any] = {
                "aegis_kind": kind,
                "aegis_schema": SCHEMA_VERSION,
                "event_count": len(events),
                "identity_relationships": len(associations),
                "tags": ["aegis-vault", f"aegis/{kind}"],
            }
            if events:
                properties["latest_evidence"] = max(event["ts"] for event in events)
            if group == "worktrees":
                properties["worktree_fingerprint"] = _digest_bytes(value.encode("utf-8"))
            elif group == "agents":
                properties["agent_fingerprint"] = _digest_bytes(value.encode("utf-8"))
                types = sorted(
                    {
                        str(item.get("agent_type"))
                        for item in [*events, *associations]
                        if item.get("agent_type")
                    }
                )
                properties["agent_types"] = types
            else:
                properties[field] = value
            add(maps[group][value], _markdown(properties, f"{kind.title()}: {display}", body))

    evidence = [
        event for event in snapshot["events"] if event["event_type"] in EVIDENCE_EVENT_TYPES
    ]
    evidence = evidence[-limits.max_evidence_notes :]
    evidence_links: list[str] = []
    for event in evidence:
        event_id = event["event_id"] or _digest_json(event)
        note_path = f"Evidence/{event['event_type']}/{_slug(event['ts'] + '-' + event_id)}.md"
        evidence_links.append(_link(note_path, f"{event['event_type']} {event['ts']}"))
        body = [
            f"- Timestamp: `{event['ts']}`",
            f"- Outcome: `{event['outcome'] or event['exit_class'] or 'unknown'}`",
            f"- Handler: `{event['handler'] or event['tool_name'] or 'unknown'}`",
        ]
        if event["head"]:
            body.append(f"- HEAD: `{event['head']}`")
        if event["paths"]:
            body.extend(("", "## Affected paths", *(f"- `{path}`" for path in event["paths"][:20])))
        if event["extra"]:
            body.extend(
                (
                    "",
                    "## Bounded metadata",
                    *(
                        f"- **{key}**: `{_redact(value, limit=500)}`"
                        for key, value in sorted(event["extra"].items())
                    ),
                )
            )
        relations = _event_links(event, maps)
        if relations:
            body.extend(("", "## Relations", *(f"- {item}" for item in relations)))
        add(
            note_path,
            _markdown(
                {
                    "aegis_kind": "evidence",
                    "aegis_schema": SCHEMA_VERSION,
                    "event_id": event_id,
                    "event_type": event["event_type"],
                    "outcome": event["outcome"] or event["exit_class"] or "unknown",
                    "timestamp": event["ts"],
                    "tags": ["aegis-vault", "aegis/evidence", f"aegis/{event['event_type']}"],
                },
                f"{event['event_type'].replace('_', ' ').title()} evidence",
                body,
            ),
        )

    legacy_links: list[str] = []
    for document in legacy:
        note_path = f"Legacy/{_slug(document['path'])}.md"
        legacy_links.append(_link(note_path, document["path"]))
        body = [
            "This note inventories preserved human-authored workflow context. The source file remains authoritative for its narrative.",
            "",
            f"- Source: `{document['path']}`",
            f"- Bytes: {document['bytes']}",
            f"- Human-authored nonblank lines: {document['human_nonblank_lines']}",
            f"- Generated Aegis blocks: {document['generated_blocks']}",
            f"- Checkboxes: {document['checkboxes']}",
            f"- S:W:H:E entries outside generated blocks: {document['sweh_entries']}",
        ]
        if document["headings"]:
            body.extend(("", "## Headings", *(f"- {heading}" for heading in document["headings"])))
        work_links = []
        for work_id in document.get("work_ids", document.get("task_ids", [])):
            if work_id not in maps["work"]:
                continue
            kind = "Bead" if work_id in maps["beads"] else "Task"
            work_links.append(_link(maps["work"][work_id], f"{kind} {work_id}"))
        if work_links:
            body.extend(("", "## Related work", *(f"- {item}" for item in work_links)))
        add(
            note_path,
            _markdown(
                {
                    "aegis_kind": "legacy-document",
                    "aegis_schema": SCHEMA_VERSION,
                    "content_digest": document["content_digest"],
                    "document_kind": document["kind"],
                    "human_nonblank_lines": document["human_nonblank_lines"],
                    "source_path": document["path"],
                    "tags": ["aegis-vault", "aegis/legacy", f"aegis/{document['kind']}"],
                },
                document["path"],
                body,
            ),
        )

    activity_body = ["## High-signal evidence by class"]
    activity_body.extend(
        f"- `{key}`: {value}" for key, value in sorted(event_summary["by_type"].items())
    )
    if evidence_links:
        activity_body.extend(
            ("", "## Recent evidence", *(f"- {item}" for item in evidence_links[-100:]))
        )
    if legacy_links:
        activity_body.extend(
            ("", "## Preserved legacy context", *(f"- {item}" for item in legacy_links[:100]))
        )
    add(
        "Indexes/Activity.md",
        _markdown(
            {
                "aegis_kind": "index",
                "aegis_schema": SCHEMA_VERSION,
                "latest_evidence": event_summary["latest_ts"],
                "tags": ["aegis-vault", "aegis/index"],
            },
            "Activity and evidence index",
            activity_body,
        ),
    )
    add(
        "Views/Work.base",
        _render_work_base(),
    )
    add(
        "Views/Tasks.base",
        _render_base("task", "Tasks", ("file.name", "status", "priority", "task_id")),
    )
    add(
        "Views/Evidence.base",
        _render_base("evidence", "Evidence", ("timestamp", "event_type", "outcome", "file.name")),
    )
    add(
        "Views/Legacy.base",
        _render_base(
            "legacy-document",
            "Legacy context",
            ("source_path", "document_kind", "human_nonblank_lines", "file.name"),
        ),
    )
    return dict(sorted(files.items()))


def _manifest(snapshot: Mapping[str, Any], files: Mapping[str, bytes]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "managed_root": True,
        "repository_identity": snapshot["repository"]["identity"],
        "repository_name": snapshot["repository"]["name"],
        "source_branch": snapshot["repository"]["branch"],
        "source_head": snapshot["repository"]["head"],
        "source_digest": snapshot["source_digest"],
        "work_authority": snapshot.get("work_authority", {}).get("authority", "none"),
        "work_source_digest": snapshot.get("work_authority", {}).get("source_digest", ""),
        "latest_evidence_ts": snapshot["event_summary"]["latest_ts"],
        "counts": {
            "files": len(files),
            "high_signal_events": snapshot["event_summary"]["high_signal_count"],
            "identity_relationships": len(snapshot.get("identities") or []),
            "legacy_documents": len(snapshot["legacy_documents"]),
            "work_items": len(snapshot.get("work_items", snapshot.get("tasks", []))),
            "beads": sum(
                1 for item in snapshot.get("work_items", []) if item.get("authority") == "beads"
            ),
            "tasks": len(snapshot["tasks"]),
        },
        "files": {path: _digest_bytes(content) for path, content in sorted(files.items())},
    }


def _read_manifest(root: Path) -> dict[str, Any]:
    path = root / MANIFEST_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VaultError(
            f"existing vault is not Aegis-owned (missing {MANIFEST_NAME}): {root}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise VaultError(f"invalid vault ownership manifest at {path}: {exc}") from exc
    if (
        not isinstance(payload, Mapping)
        or payload.get("generator") != GENERATOR
        or payload.get("managed_root") is not True
    ):
        raise VaultError(f"existing directory is not an Aegis-owned vault: {root}")
    return dict(payload)


def check_vault(
    output_dir: str | Path,
    *,
    expected_source_digest: str | None = None,
) -> dict[str, Any]:
    """Verify ownership, exact file inventory, hashes, and optional freshness."""

    requested = Path(output_dir).expanduser()
    if requested.is_symlink():
        return {
            "status": "failed",
            "ok": False,
            "output": requested.absolute().as_posix(),
            "problems": ["vault directory is missing or is a symlink"],
        }
    root = requested.resolve()
    if not root.is_dir() or root.is_symlink():
        return {
            "status": "failed",
            "ok": False,
            "output": root.as_posix(),
            "problems": ["vault directory is missing or is a symlink"],
        }
    try:
        manifest = _read_manifest(root)
    except VaultError as exc:
        return {"status": "failed", "ok": False, "output": root.as_posix(), "problems": [str(exc)]}
    raw_declared = manifest.get("files")
    declared: Mapping[str, Any] = raw_declared if isinstance(raw_declared, Mapping) else {}
    actual_files = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    )
    expected_files = sorted([MANIFEST_NAME, *declared.keys()])
    problems: list[str] = []
    if actual_files != expected_files:
        missing = sorted(set(expected_files) - set(actual_files))
        extra = sorted(set(actual_files) - set(expected_files))
        if missing:
            problems.append("missing owned files: " + ", ".join(missing[:20]))
        if extra:
            problems.append("unknown files present: " + ", ".join(extra[:20]))
    for relative, expected in sorted(declared.items()):
        path = root / relative
        if path.is_symlink():
            problems.append(f"owned file is a symlink: {relative}")
            continue
        if path.is_file() and _digest_bytes(path.read_bytes()) != expected:
            problems.append(f"hash mismatch: {relative}")
    fresh = (
        expected_source_digest is None or manifest.get("source_digest") == expected_source_digest
    )
    if not fresh:
        problems.append("vault source digest is stale")
    return {
        "status": "passed" if not problems else "failed",
        "ok": not problems,
        "fresh": fresh,
        "output": root.as_posix(),
        "source_digest": manifest.get("source_digest"),
        "work_authority": manifest.get("work_authority", "none"),
        "counts": manifest.get("counts", {}),
        "file_count": len(declared),
        "problems": problems,
    }


def gate_vault(
    output_dir: str | Path,
    *,
    phase: str,
    expected_source_digest: str,
    expected_work_authority: str,
) -> dict[str, Any]:
    """Evaluate the explicit readiness/closeout/publication vault boundary."""

    if phase not in {"readiness", "closeout", "publication"}:
        raise VaultError(f"unsupported vault gate phase: {phase}")
    checked = check_vault(
        output_dir,
        expected_source_digest=expected_source_digest,
    )
    problems = list(checked.get("problems") or [])
    actual_authority = str(checked.get("work_authority") or "none")
    if actual_authority != expected_work_authority:
        problems.append(
            "vault work authority drift: "
            f"expected {expected_work_authority}, found {actual_authority}"
        )
    counts = checked.get("counts") if isinstance(checked.get("counts"), Mapping) else {}
    if expected_work_authority != "none" and int(counts.get("work_items") or 0) < 1:
        problems.append("vault contains no projected work items")
    return {
        **checked,
        "status": "passed" if not problems else "blocked",
        "ok": not problems,
        "gate": f"obsidian-{phase}",
        "phase": phase,
        "expected_work_authority": expected_work_authority,
        "problems": problems,
        "next_action": (
            "continue workflow"
            if not problems
            else "rebuild the managed Aegis vault from the exact current sources, then rerun this gate"
        ),
    }


def _assert_output_safe(output: Path, repository: Path) -> None:
    requested = output.expanduser()
    if requested.is_symlink():
        raise VaultError(f"vault output must not be a symlink: {requested.absolute()}")
    resolved = requested.resolve()
    if resolved == repository or repository in resolved.parents:
        raise VaultError("vault output must live outside the source repository")


def _missing_owned_files_are_recoverable(
    output: Path,
    previous: Mapping[str, Any],
    expected_files: Mapping[str, bytes],
) -> bool:
    """Accept only a pure, digest-proven loss inside an owned generated projection."""

    raw_declared = previous.get("files")
    if not isinstance(raw_declared, Mapping):
        return False
    declared = dict(raw_declared)
    actual = {
        path.relative_to(output).as_posix(): path
        for path in output.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    actual.pop(MANIFEST_NAME, None)
    if set(actual) - set(declared):
        return False
    missing = set(declared) - set(actual)
    if not missing:
        return False
    for relative, path in actual.items():
        if path.is_symlink() or _digest_bytes(path.read_bytes()) != declared.get(relative):
            return False
    for relative in missing:
        replacement = expected_files.get(relative)
        if replacement is not None and _digest_bytes(replacement) != declared.get(relative):
            return False
    return True


def _validate_existing_for_replacement(
    output: Path,
    *,
    expected_files: Mapping[str, bytes],
) -> tuple[dict[str, Any] | None, bool]:
    if not output.exists():
        return None, False
    if not output.is_dir() or output.is_symlink():
        raise VaultError(f"vault output exists but is not a regular directory: {output}")
    if not any(output.iterdir()):
        return None, False
    result = check_vault(output)
    if not result["ok"]:
        try:
            previous = _read_manifest(output)
        except VaultError:
            previous = None
        if previous is not None and _missing_owned_files_are_recoverable(
            output, previous, expected_files
        ):
            return previous, True
        raise VaultError(
            "refusing to replace untrusted or modified vault: " + "; ".join(result["problems"])
        )
    return _read_manifest(output), False


def build_vault(
    snapshot: Mapping[str, Any],
    output_dir: str | Path,
    *,
    target_dir: str | Path,
) -> dict[str, Any]:
    """Atomically replace an owned vault; leave source and unknown files untouched."""

    repository = repository_root(target_dir)
    requested_output = Path(output_dir).expanduser()
    _assert_output_safe(requested_output, repository)
    output = requested_output.resolve()
    files = render_vault(snapshot)
    manifest = _manifest(snapshot, files)
    previous, repairing_missing = _validate_existing_for_replacement(
        output,
        expected_files=files,
    )
    if (
        previous is not None
        and not repairing_missing
        and previous.get("source_digest") == manifest["source_digest"]
        and previous.get("files") == manifest["files"]
    ):
        return {
            "status": "current",
            "changed": False,
            "output": output.as_posix(),
            "source_digest": manifest["source_digest"],
            "file_count": len(files),
            "counts": manifest["counts"],
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=str(output.parent)))
    backup: Path | None = None
    try:
        for relative, content in files.items():
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        (stage / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        staged_check = check_vault(stage, expected_source_digest=manifest["source_digest"])
        if not staged_check["ok"]:
            raise VaultError(
                "staged vault failed self-check: " + "; ".join(staged_check["problems"])
            )
        if output.exists():
            backup = Path(
                tempfile.mkdtemp(prefix=f".{output.name}.backup-", dir=str(output.parent))
            )
            backup.rmdir()
            os.replace(output, backup)
        try:
            os.replace(stage, output)
        except Exception:
            if backup is not None and backup.exists() and not output.exists():
                os.replace(backup, output)
            raise
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if backup is not None and backup.exists() and output.exists():
            shutil.rmtree(backup)
    return {
        "status": "repaired" if repairing_missing else "built",
        "changed": True,
        "output": output.as_posix(),
        "source_digest": manifest["source_digest"],
        "file_count": len(files),
        "counts": manifest["counts"],
    }


__all__ = [
    "DEFAULT_VAULT_DIRNAME",
    "GENERATOR",
    "HIGH_SIGNAL_EVENT_TYPES",
    "MANIFEST_NAME",
    "SCHEMA_VERSION",
    "VaultError",
    "VaultLimits",
    "build_vault",
    "check_vault",
    "collect_snapshot",
    "default_vault_path",
    "gate_vault",
    "render_vault",
    "repository_root",
]
