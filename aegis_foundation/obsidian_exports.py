"""Unsandboxed, pinned Bead reads and atomic envelopes for the sandboxed consumer."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Callable

from aegis_foundation.obsidian_registry import PROJECT_ID, ProjectConfig, Registry

MAX_EXPORT_BYTES = 8 * 1024 * 1024
EXPORTER_VERSION = "1"


class ReconcileError(RuntimeError):
    """A bounded export or reconciliation refusal."""


def _redact_error(value: object) -> str:
    return " ".join(str(value).split())[:1_000]


def _export_scope_notice(argv: tuple[str, ...]) -> bytes | None:
    """Recognize the complete, explicitly scoped gc read emitted by the registry.

    Do not infer a store from a checkout or accept gc's ambient/city fallback.
    Legacy exporters still require empty stderr.
    """
    if not argv or Path(argv[0]).name != "gc":
        return None
    if (
        len(argv) != 11
        or not Path(argv[0]).is_absolute()
        or argv[1] != "--city"
        or not Path(argv[2]).is_absolute()
        or argv[3] != "--rig"
        or not PROJECT_ID.fullmatch(argv[4])
        or argv[5:] != ("bd", "list", "--all", "--limit", "0", "--json")
    ):
        raise ReconcileError(
            "gc bead export requires an explicit city and rig with a complete list"
        )
    return f'gc bd: answering from the rig "{argv[4]}" store'.encode()


def _export_stderr_allowed(
    stderr: bytes, scope_notice: bytes | None, gate_paths: tuple[Path, ...]
) -> bool:
    if scope_notice is None:
        return stderr == b""
    # Remove only ONE optional final LF; blank lines and duplicate notices fail.
    lines = stderr.removesuffix(b"\n").split(b"\n")
    if lines == [scope_notice]:
        return True
    if len(lines) != 2 or lines.count(scope_notice) != 1:
        return False
    warning = lines[1] if lines[0] == scope_notice else lines[0]
    # bd e243402b cmd/bd/workspace_gate.go:222 + workspacegate/gate.go:392.
    # os.OpenFile wraps errno as "open <path>: <reason>"; compare both paths.
    return any(
        warning
        == (
            "warning: workspace gate acquisition failed, continuing ungated: "
            f"workspacegate: open gate {path}: open {path}: read-only file system"
        ).encode()
        for path in gate_paths
    )


def export_beads(
    argv: tuple[str, ...], timeout: int, *, gate_paths: tuple[Path, ...] = ()
) -> bytes:
    scope_notice = _export_scope_notice(argv)
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReconcileError(f"bead export failed: {_redact_error(exc)}") from exc
    if result.returncode != 0:
        # bd can emit the warning on stderr and the actual JSON refusal on stdout.
        # Bound each independently so a long warning cannot hide the refusal again.
        detail = "; ".join(
            f"{name}: {_redact_error(content.decode('utf-8', errors='replace'))[:450]}"
            for name, content in (("stderr", result.stderr), ("stdout", result.stdout))
            if content
        )
        raise ReconcileError(f"bead export refused ({result.returncode}): {detail}")
    if not _export_stderr_allowed(result.stderr, scope_notice, gate_paths):
        detail = _redact_error(result.stderr.decode("utf-8", errors="replace"))
        raise ReconcileError(f"bead export has unexpected stderr (store unconfirmed): {detail}")
    if len(result.stdout) > MAX_EXPORT_BYTES:
        raise ReconcileError(
            f"bead export exceeds size limit ({len(result.stdout)} > {MAX_EXPORT_BYTES})"
        )
    if not result.stdout.strip():
        raise ReconcileError("bead export returned no records")
    if scope_notice is not None:
        try:
            records = json.loads(result.stdout)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ReconcileError("gc bead export is not a JSON list") from exc
        if not isinstance(records, list) or any(
            not isinstance(record, dict)
            or not isinstance(record.get("id"), str)
            or not record["id"]
            for record in records
        ):
            raise ReconcileError("gc bead export requires a JSON list of bead objects with ids")
    return result.stdout


def _json(content: bytes | str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"invalid JSON constant: {value}")

    return json.loads(content, object_pairs_hook=pairs, parse_constant=constant)


def _bead_list(content: bytes) -> list[dict[str, Any]]:
    try:
        records = _json(content)
        if not isinstance(records, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]
            for row in records
        ):
            raise ValueError("expected bead objects with ids")
        return records
    except (ValueError, UnicodeError) as exc:
        raise ReconcileError("bead export is not exactly one JSON list of beads") from exc


def _rig(project: ProjectConfig) -> str:
    if _export_scope_notice(project.bead_export_argv) is None:
        raise ReconcileError("export requires a pinned, explicitly scoped gc command")
    return project.bead_export_argv[4]


def _iso(now: datetime) -> str:
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_export(path: Path, payload: dict[str, Any]) -> None:
    content = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def export_registry(
    registry: Registry,
    *,
    bead_exporter: Callable = export_beads,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    directory = registry.export_dir
    if directory is None:
        raise ReconcileError("registry export_dir is required")
    if directory.is_symlink():
        raise ReconcileError("export_dir must not be a symlink")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    results = []
    for project in registry.projects:
        if not project.enabled:
            continue
        path = directory / f"{project.id}.json"
        try:
            rig = _rig(project)
            content = bead_exporter(
                project.bead_export_argv,
                project.export_timeout_seconds,
                gate_paths=project.bead_gate_paths,
            )
            if len(content) > MAX_EXPORT_BYTES:
                raise ReconcileError("bead export exceeds size limit")
            _bead_list(content)
            # Preserve the exact UTF-8 stdout bytes, including whitespace, for the digest.
            payload = {
                "manifest": {
                    "project_id": project.id,
                    "rig": rig,
                    "command": list(project.bead_export_argv),
                    "completed_at": _iso(clock()),
                    "beads_sha256": hashlib.sha256(content).hexdigest(),
                    "exporter_version": EXPORTER_VERSION,
                },
                "beads_json": content.decode("utf-8"),
            }
            _atomic_export(path, payload)
            results.append({"id": project.id, "ok": True})
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            error = _redact_error(exc)
            # Replace a failed source with an explicit refusal: never re-date old beads.
            try:
                _atomic_export(
                    path, {"project_id": project.id, "failed_at": _iso(clock()), "error": error}
                )
            except OSError as write_exc:
                error += "; failure record write failed: " + _redact_error(write_exc)
            results.append({"id": project.id, "ok": False, "error": error})
    # stdout is captured by journald even when a disk failure prevents a file record.
    return {"ok": all(item["ok"] for item in results), "projects": results}


def read_export(registry: Registry, project: ProjectConfig, *, now: datetime) -> bytes:
    try:
        if registry.export_dir is None:
            raise ValueError("registry export_dir is required")
        path = registry.export_dir / f"{project.id}.json"
        if path.is_symlink() or not path.is_file():
            raise ValueError("export missing or unsafe")
        # JSON string escaping can expand each source byte to six bytes.
        with path.open("rb") as handle:
            raw = handle.read(MAX_EXPORT_BYTES * 6 + 65537)
        if len(raw) > MAX_EXPORT_BYTES * 6 + 65536:
            raise ValueError("export envelope exceeds size limit")
        payload = _json(raw)
        if not isinstance(payload, dict):
            raise ValueError("malformed export envelope")
        if "error" in payload:
            raise ValueError(f"exporter failed: {payload['error']}")
        if set(payload) != {"manifest", "beads_json"}:
            raise ValueError("malformed export envelope")
        manifest = payload["manifest"]
        if not isinstance(manifest, dict) or set(manifest) != {
            "project_id",
            "rig",
            "command",
            "completed_at",
            "beads_sha256",
            "exporter_version",
        }:
            raise ValueError("malformed export manifest")
        if (
            manifest["project_id"] != project.id
            or manifest["rig"] != _rig(project)
            or manifest["command"] != list(project.bead_export_argv)
            or manifest["exporter_version"] != EXPORTER_VERSION
        ):
            raise ValueError("export manifest does not match registry/version")
        completed = datetime.fromisoformat(manifest["completed_at"].replace("Z", "+00:00"))
        if completed.tzinfo is None:
            raise ValueError("export completion time requires timezone")
        age = (now - completed).total_seconds()
        if age < 0 or age > registry.export_max_age_seconds:
            raise ValueError(f"export stale or future-dated (age={age:g}s)")
        content = payload["beads_json"].encode("utf-8")
        if len(content) > MAX_EXPORT_BYTES:
            raise ValueError("bead export exceeds size limit")
        if hashlib.sha256(content).hexdigest() != manifest["beads_sha256"]:
            raise ValueError("export digest mismatch")
        _bead_list(content)
        return content
    except (OSError, ValueError, TypeError, AttributeError, RecursionError, ReconcileError) as exc:
        raise ReconcileError(f"project {project.id} export refused: {_redact_error(exc)}") from exc
