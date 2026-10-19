"""Deterministic Obsidian dashboard derived from the continuity report."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from aegis_foundation.obsidian_registry import ContinuityDashboardConfig

SCHEMA_VERSION = "1"
REPORT_SCHEMA = "gas-city-workflow.continuity-report.v1"
GENERATOR = "aegis-foundation:continuity-dashboard"
MANIFEST_NAME = ".gas-city-continuity.json"
MAX_REPORT_BYTES = 4 * 1024 * 1024
Runner = Callable[[tuple[str, ...], int], subprocess.CompletedProcess[bytes]]


class DashboardError(RuntimeError):
    """Raised when a continuity report or dashboard is unsafe or incomplete."""


def run_command(argv: tuple[str, ...], timeout: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, capture_output=True, timeout=timeout, check=False)


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _safe_text(value: Any, *, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    text = text.replace("`", "'").replace("[", "(").replace("]", ")")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _run(argv: tuple[str, ...], *, timeout: int, runner: Runner, allowed: set[int]) -> None:
    try:
        result = runner(argv, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DashboardError(f"continuity command failed: {_safe_text(exc, limit=500)}") from exc
    if result.returncode not in allowed:
        detail = (result.stderr or result.stdout or b"").decode("utf-8", errors="replace")
        raise DashboardError(
            f"continuity command refused ({result.returncode}): {_safe_text(detail, limit=800)}"
        )


def capture_report(
    config: ContinuityDashboardConfig,
    *,
    installed_registry: Path,
    state_dir: Path,
    runner: Runner = run_command,
) -> dict[str, Any]:
    """Run the fixed continuity snapshot/audit interface and validate its report."""

    with tempfile.TemporaryDirectory(prefix="continuity-dashboard-", dir=state_dir) as raw:
        temporary = Path(raw)
        snapshot = temporary / "snapshot.json"
        report_path = temporary / "report.json"
        base = (config.python.as_posix(), config.entrypoint.as_posix())
        _run(
            (
                *base,
                "snapshot",
                "--offline-beads",
                "--registry",
                config.workflow_registry.as_posix(),
                "--obsidian-registry",
                installed_registry.as_posix(),
                "--obsidian-state",
                state_dir.as_posix(),
                "--obsidian-cycle-status",
                "idle",
                "--signing-policies",
                config.signing_policies.as_posix(),
                "--output",
                snapshot.as_posix(),
            ),
            timeout=config.capture_timeout_seconds,
            runner=runner,
            allowed={0},
        )
        _run(
            (
                *base,
                "audit",
                "--snapshot",
                snapshot.as_posix(),
                "--output",
                report_path.as_posix(),
            ),
            timeout=config.capture_timeout_seconds,
            runner=runner,
            allowed={0, 3},
        )
        if not report_path.is_file() or report_path.is_symlink():
            raise DashboardError("continuity audit did not produce a regular report")
        content = report_path.read_bytes()
        if len(content) > MAX_REPORT_BYTES:
            raise DashboardError(
                f"continuity report exceeds size limit ({len(content)} > {MAX_REPORT_BYTES})"
            )
        try:
            report = json.loads(content)
        except json.JSONDecodeError as exc:
            raise DashboardError(f"continuity report is invalid JSON: {exc}") from exc
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMA:
        raise DashboardError("continuity report schema is invalid")
    required = {"ok", "summary", "work", "findings", "next_actions", "snapshot_sha256"}
    if not required.issubset(report):
        raise DashboardError("continuity report is missing required fields")
    if not isinstance(report["work"], dict) or not isinstance(report["findings"], list):
        raise DashboardError("continuity report collections are invalid")
    return report


def _work_line(item: Mapping[str, Any]) -> str:
    identity = _safe_text(item.get("bead_id") or item.get("id") or "unknown", limit=120)
    title = _safe_text(item.get("title") or item.get("reason") or "untitled", limit=240)
    status = _safe_text(item.get("status") or item.get("reason") or "unknown", limit=80)
    return f"- `{identity}` — {title} ({status})"


def _section(title: str, values: list[Mapping[str, Any]]) -> list[str]:
    lines = [f"## {title}", ""]
    lines.extend(_work_line(item) for item in values)
    if not values:
        lines.append("- None")
    lines.append("")
    return lines


def render_status(report: Mapping[str, Any]) -> bytes:
    work = report.get("work") if isinstance(report.get("work"), Mapping) else {}
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    counts = summary.get("counts") if isinstance(summary.get("counts"), Mapping) else {}
    current = [item for item in work.get("current", []) if isinstance(item, Mapping)]
    next_items = [item for item in report.get("next_actions", []) if isinstance(item, Mapping)]
    blocked = [item for item in work.get("blocked", []) if isinstance(item, Mapping)]
    findings = [item for item in report.get("findings", []) if isinstance(item, Mapping)]
    drift = [
        {
            "id": item.get("code"),
            "title": f"{item.get('project_id')}: {item.get('identity')}",
            "status": item.get("severity"),
        }
        for item in findings
    ]
    lines = [
        "---",
        'aegis_kind: "continuity-dashboard"',
        f'aegis_schema: "{SCHEMA_VERSION}"',
        'authority: "beads+derived-continuity-report"',
        f"report_ok: {str(bool(report.get('ok'))).lower()}",
        f'snapshot_sha256: "{_safe_text(report.get("snapshot_sha256"), limit=64)}"',
        "---",
        "",
        "# Gas City Continuity",
        "",
        "This is a deterministic view of the continuity report. Beads remain the work authority.",
        "",
        "## Summary",
        "",
        f"- Current: {int(counts.get('current', len(current)))}",
        f"- Next: {int(counts.get('next', len(next_items)))}",
        f"- Blocked: {int(counts.get('blocked', len(blocked)))}",
        f"- Drift findings: {len(findings)}",
        "",
    ]
    lines.extend(_section("Now", current))
    lines.extend(_section("Next", next_items))
    lines.extend(_section("Blocked", blocked))
    lines.extend(_section("Drift", drift))
    return ("\n".join(lines).rstrip() + "\n").encode()


def _desired(report: Mapping[str, Any]) -> dict[str, bytes]:
    report_bytes = _canonical_json(report)
    return {"Status.md": render_status(report), "report.json": report_bytes}


def _manifest(files: Mapping[str, bytes], report: Mapping[str, Any]) -> bytes:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "snapshot_sha256": report.get("snapshot_sha256"),
        "report_sha256": _digest(files["report.json"]),
        "files": {name: _digest(content) for name, content in sorted(files.items())},
    }
    return _canonical_json(payload)


def _read_managed(output: Path) -> dict[str, bytes] | None:
    if not output.exists():
        return None
    if output.is_symlink() or not output.is_dir():
        raise DashboardError(f"dashboard output is not a safe directory: {output}")
    manifest_path = output / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise DashboardError(f"dashboard output is not managed by {GENERATOR}: {output}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DashboardError(f"dashboard manifest is invalid: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("generator") != GENERATOR:
        raise DashboardError("dashboard manifest generator is invalid")
    declared = manifest.get("files")
    if not isinstance(declared, dict):
        raise DashboardError("dashboard manifest file inventory is invalid")
    observed: dict[str, bytes] = {}
    actual = sorted(
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file() and path.name != MANIFEST_NAME
    )
    if actual != sorted(declared):
        raise DashboardError("dashboard file inventory drift")
    for name, digest in declared.items():
        path = output / str(name)
        if path.is_symlink() or not path.is_file():
            raise DashboardError(f"dashboard file is unsafe: {name}")
        content = path.read_bytes()
        if _digest(content) != digest:
            raise DashboardError(f"dashboard file digest drift: {name}")
        observed[str(name)] = content
    return observed


def build_dashboard(report: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    output = output_dir.resolve()
    parent = output.parent
    if parent.is_symlink() or not parent.is_dir():
        raise DashboardError(f"dashboard output parent is missing or unsafe: {parent}")
    files = _desired(report)
    current = _read_managed(output)
    if current == files:
        return {
            "ok": True,
            "status": "current",
            "changed": False,
            "file_count": len(files),
            "report_sha256": _digest(files["report.json"]),
        }

    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=parent))
    backup: Path | None = None
    try:
        os.chmod(temporary, 0o755)
        for name, content in files.items():
            path = temporary / name
            path.write_bytes(content)
            os.chmod(path, 0o644)
        manifest = temporary / MANIFEST_NAME
        manifest.write_bytes(_manifest(files, report))
        os.chmod(manifest, 0o644)
        if output.exists():
            backup = Path(tempfile.mkdtemp(prefix=f".{output.name}.backup.", dir=parent))
            backup.rmdir()
            os.replace(output, backup)
        try:
            os.replace(temporary, output)
        except Exception:
            if backup is not None and backup.exists() and not output.exists():
                os.replace(backup, output)
            raise
        if backup is not None:
            shutil.rmtree(backup)
        return {
            "ok": True,
            "status": "built",
            "changed": True,
            "file_count": len(files),
            "report_sha256": _digest(files["report.json"]),
        }
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def gate_dashboard(report: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    try:
        observed = _read_managed(output_dir.resolve())
        expected = _desired(report)
        problems = (
            [] if observed == expected else ["dashboard bytes do not match continuity report"]
        )
    except DashboardError as exc:
        problems = [str(exc)]
    return {"ok": not problems, "problems": problems}


__all__ = [
    "DashboardError",
    "GENERATOR",
    "MANIFEST_NAME",
    "Runner",
    "build_dashboard",
    "capture_report",
    "gate_dashboard",
    "render_status",
    "run_command",
]
