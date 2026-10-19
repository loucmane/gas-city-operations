"""Automatic, failure-bounded reconciliation of Aegis Obsidian projections."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Protocol

from aegis_foundation import obsidian_continuity, obsidian_live_index, obsidian_vault
from aegis_foundation.obsidian_ledger_reader import read_events
from aegis_foundation.obsidian_registry import (
    ContinuityDashboardConfig,
    LiveIndexConfig,
    ProjectConfig,
    Registry,
)

from aegis_foundation.obsidian_exports import MAX_EXPORT_BYTES, ReconcileError, read_export

SCHEMA_VERSION = "1"
CHECK_LOCK_TIMEOUT_SECONDS = 60.0
LOCK_POLL_SECONDS = 0.05


class BeadExporter(Protocol):
    def __call__(
        self, argv: tuple[str, ...], timeout: int, *, gate_paths: tuple[Path, ...] = ()
    ) -> bytes: ...


EventReader = Callable[[Path], list[dict[str, Any]]]
Clock = Callable[[], datetime]
LiveIndexRunner = obsidian_live_index.Runner
DashboardRunner = obsidian_continuity.Runner


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _redact_error(value: object) -> str:
    return " ".join(str(value).split())[:1_000]


def _read_state(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _snapshot(
    project: ProjectConfig,
    registry: Registry,
    now: datetime,
    *,
    state_dir: Path,
    bead_exporter: BeadExporter | None,
    event_reader: EventReader,
) -> tuple[dict[str, Any], bytes]:
    exported = (
        read_export(registry, project, now=now)
        if bead_exporter is None
        else bead_exporter(
            project.bead_export_argv,
            project.export_timeout_seconds,
            gate_paths=project.bead_gate_paths,
        )
    )
    if len(exported) > MAX_EXPORT_BYTES:
        raise ReconcileError(
            f"bead export exceeds size limit ({len(exported)} > {MAX_EXPORT_BYTES})"
        )
    descriptor, raw = tempfile.mkstemp(prefix=f".{project.id}.beads.", dir=state_dir)
    temporary = Path(raw)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(exported)
        events = event_reader(project.target_dir)
        snapshot = obsidian_vault.collect_snapshot(
            project.target_dir,
            events,
            bead_snapshot=temporary,
            include_bead_content=project.include_bead_content,
        )
    except (obsidian_vault.VaultError, OSError, ValueError) as exc:
        raise ReconcileError(_redact_error(exc)) from exc
    finally:
        temporary.unlink(missing_ok=True)
    authority = snapshot.get("work_authority", {})
    if authority.get("authority") != "beads":
        raise ReconcileError("snapshot did not resolve exact bead authority")
    if not snapshot.get("work_items"):
        raise ReconcileError("snapshot contains no bead work items")
    return snapshot, exported


def _lock(
    state_dir: Path,
    project_id: str,
    *,
    timeout_seconds: float = 0.0,
) -> tuple[Any, bool]:
    path = state_dir / f"{project_id}.lock"
    handle = path.open("a+", encoding="utf-8")
    os.chmod(path, 0o600)
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return handle, False
            time.sleep(min(LOCK_POLL_SECONDS, remaining))
        else:
            return handle, True


def _attempt_state(
    previous: dict[str, Any],
    *,
    project: ProjectConfig,
    registry: Registry,
    attempted_at: str,
    last_success: dict[str, Any] | None,
    last_error: dict[str, Any] | None,
    pending_success: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project.id,
        "registry_digest": registry.digest,
        "target_dir": project.target_dir.as_posix(),
        "output_dir": project.output_dir.as_posix(),
        "last_attempt_at": attempted_at,
        "last_success": last_success,
        "last_error": last_error,
        "previous_attempt_at": previous.get("last_attempt_at"),
    }
    if pending_success is not None:
        payload["pending_success"] = pending_success
    return payload


def _reconcile_project(
    project: ProjectConfig,
    registry: Registry,
    *,
    state_dir: Path,
    bead_exporter: BeadExporter | None,
    event_reader: EventReader,
    live_index_runner: LiveIndexRunner,
    clock: Clock,
    force: bool,
    defer_live_index: bool = False,
) -> dict[str, Any]:
    state_path = state_dir / f"{project.id}.json"
    previous = _read_state(state_path)
    now = clock()
    previous_attempt = _parse_time(previous.get("last_attempt_at"))
    if (
        not force
        and previous_attempt is not None
        and (now - previous_attempt).total_seconds() < project.min_interval_seconds
    ):
        return {"id": project.id, "ok": True, "status": "debounced", "changed": False}
    lock_handle, acquired = _lock(state_dir, project.id)
    if not acquired:
        lock_handle.close()
        return {"id": project.id, "ok": True, "status": "already-running", "changed": False}
    attempted_at = _iso(now)
    try:
        snapshot, exported = _snapshot(
            project,
            registry,
            now,
            state_dir=state_dir,
            bead_exporter=bead_exporter,
            event_reader=event_reader,
        )
        try:
            built = obsidian_vault.build_vault(
                snapshot,
                project.output_dir,
                target_dir=project.target_dir,
            )
            gates = [
                obsidian_vault.gate_vault(
                    project.output_dir,
                    phase=phase,
                    expected_source_digest=snapshot["source_digest"],
                    expected_work_authority="beads",
                )
                for phase in ("readiness", "closeout", "publication")
            ]
        except (obsidian_vault.VaultError, OSError) as exc:
            raise ReconcileError(_redact_error(exc)) from exc
        if not all(gate["ok"] for gate in gates):
            problems = [problem for gate in gates for problem in gate.get("problems", [])]
            raise ReconcileError("projection gate failed: " + "; ".join(problems))
        if project.live_index is None:
            live_index = obsidian_live_index.not_run(
                configured=False,
                status="not-configured",
            )
        elif defer_live_index:
            live_index = obsidian_live_index.not_run(
                configured=True,
                status="pending-cycle-observation",
            )
        elif built["changed"]:
            live_index = obsidian_live_index.observe(
                project.live_index,
                refresh=True,
                runner=live_index_runner,
            )
        else:
            live_index = obsidian_live_index.observe(
                project.live_index,
                refresh=False,
                runner=live_index_runner,
            )
        bead_digest = hashlib.sha256(exported).hexdigest()
        _atomic_bytes(state_dir / f"{project.id}-beads.json", exported)
        success = {
            "completed_at": attempted_at,
            "source_digest": snapshot["source_digest"],
            "bead_snapshot_sha256": bead_digest,
            "vault_status": built["status"],
            "file_count": built["file_count"],
            "gate_phases": [gate["phase"] for gate in gates],
            "live_index": live_index,
        }
        pending_live_index = defer_live_index and project.live_index is not None
        _atomic_json(
            state_path,
            _attempt_state(
                previous,
                project=project,
                registry=registry,
                attempted_at=attempted_at,
                last_success=(previous.get("last_success") if pending_live_index else success),
                last_error=None,
                pending_success=success if pending_live_index else None,
            ),
        )
        return {
            "id": project.id,
            "ok": True,
            "status": built["status"],
            "changed": built["changed"],
            "source_digest": snapshot["source_digest"],
            "output": project.output_dir.as_posix(),
            "file_count": built["file_count"],
            "live_index": live_index,
        }
    except ReconcileError as exc:
        message = _redact_error(exc)
        _atomic_json(
            state_path,
            _attempt_state(
                previous,
                project=project,
                registry=registry,
                attempted_at=attempted_at,
                last_success=previous.get("last_success"),
                last_error={"failed_at": attempted_at, "message": message},
            ),
        )
        return {"id": project.id, "ok": False, "status": "failed", "error": message}
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def _reconcile_dashboard(
    config: ContinuityDashboardConfig,
    registry: Registry,
    *,
    state_dir: Path,
    live_index_runner: LiveIndexRunner,
    dashboard_runner: DashboardRunner,
    clock: Clock,
    defer_live_index: bool = False,
) -> dict[str, Any]:
    state_path = state_dir / "continuity-dashboard.json"
    previous = _read_state(state_path)
    lock_handle, acquired = _lock(state_dir, "continuity-dashboard")
    if not acquired:
        lock_handle.close()
        return {"ok": True, "status": "already-running", "changed": False}
    attempted_at = _iso(clock())
    try:
        report = obsidian_continuity.capture_report(
            config,
            installed_registry=registry.path,
            state_dir=state_dir,
            runner=dashboard_runner,
        )
        built = obsidian_continuity.build_dashboard(report, config.output_dir)
        gate = obsidian_continuity.gate_dashboard(report, config.output_dir)
        if not gate["ok"]:
            raise ReconcileError("continuity dashboard gate failed: " + "; ".join(gate["problems"]))
        if config.live_index is None:
            live_index = obsidian_live_index.not_run(
                configured=False,
                status="not-configured",
            )
        elif defer_live_index:
            live_index = obsidian_live_index.not_run(
                configured=True,
                status="pending-cycle-observation",
            )
        else:
            live_index = obsidian_live_index.observe(
                config.live_index,
                refresh=bool(built["changed"]),
                runner=live_index_runner,
            )
        success = {
            "completed_at": attempted_at,
            "snapshot_sha256": report["snapshot_sha256"],
            "report_sha256": built["report_sha256"],
            "dashboard_status": built["status"],
            "file_count": built["file_count"],
            "report_ok": bool(report["ok"]),
            "live_index": live_index,
        }
        pending_live_index = defer_live_index and config.live_index is not None
        payload = {
            "schema_version": SCHEMA_VERSION,
            "registry_digest": registry.digest,
            "output_dir": config.output_dir.as_posix(),
            "last_attempt_at": attempted_at,
            "last_success": (previous.get("last_success") if pending_live_index else success),
            "last_error": None,
            "previous_attempt_at": previous.get("last_attempt_at"),
        }
        if pending_live_index:
            payload["pending_success"] = success
        _atomic_json(state_path, payload)
        return {
            "ok": True,
            "status": built["status"],
            "changed": built["changed"],
            "output": config.output_dir.as_posix(),
            "file_count": built["file_count"],
            "snapshot_sha256": report["snapshot_sha256"],
            "report_sha256": built["report_sha256"],
            "report_ok": bool(report["ok"]),
            "live_index": live_index,
        }
    except (obsidian_continuity.DashboardError, ReconcileError, OSError) as exc:
        message = _redact_error(exc)
        _atomic_json(
            state_path,
            {
                "schema_version": SCHEMA_VERSION,
                "registry_digest": registry.digest,
                "output_dir": config.output_dir.as_posix(),
                "last_attempt_at": attempted_at,
                "last_success": previous.get("last_success"),
                "last_error": {"failed_at": attempted_at, "message": message},
                "previous_attempt_at": previous.get("last_attempt_at"),
            },
        )
        return {"ok": False, "status": "failed", "changed": False, "error": message}
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def _record_live_index(state_path: Path, observation: Mapping[str, Any]) -> None:
    payload = _read_state(state_path)
    candidate = payload.get("pending_success", payload.get("last_success"))
    if not isinstance(candidate, dict):
        return
    payload["last_success"] = {**candidate, "live_index": dict(observation)}
    payload.pop("pending_success", None)
    _atomic_json(state_path, payload)


def _reconcile_registry_unlocked(
    registry: Registry,
    *,
    state_dir: str | Path,
    bead_exporter: BeadExporter | None = None,
    event_reader: EventReader = read_events,
    live_index_runner: LiveIndexRunner = obsidian_live_index.run_command,
    dashboard_runner: DashboardRunner = obsidian_continuity.run_command,
    clock: Clock = _now,
    force: bool = False,
) -> dict[str, Any]:
    state = Path(state_dir).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state, 0o700)
    project_results = [
        (
            project,
            _reconcile_project(
                project,
                registry,
                state_dir=state,
                bead_exporter=bead_exporter,
                event_reader=event_reader,
                live_index_runner=live_index_runner,
                clock=clock,
                force=force,
                defer_live_index=True,
            ),
        )
        for project in registry.projects
        if project.enabled
    ]
    projects = [result for _project, result in project_results]
    project_live_configs: list[tuple[str, LiveIndexConfig]] = []
    project_refresh_ids: set[str] = set()
    project_result_bindings: dict[str, tuple[dict[str, Any], Path]] = {}
    for project, result in project_results:
        if not result.get("ok") or project.live_index is None or "live_index" not in result:
            continue
        identity = f"project:{project.id}"
        project_live_configs.append((identity, project.live_index))
        if result.get("changed"):
            project_refresh_ids.add(identity)
        project_result_bindings[identity] = (result, state / f"{project.id}.json")
    project_observations = obsidian_live_index.observe_many(
        project_live_configs,
        refresh_ids=project_refresh_ids,
        runner=live_index_runner,
    )
    for identity, observation in project_observations.items():
        observation = {**observation, "observed_at": _iso(clock())}
        result, state_path = project_result_bindings[identity]
        result["live_index"] = observation
        _record_live_index(state_path, observation)

    dashboard: dict[str, Any] | None = None
    dashboard_config = registry.continuity_dashboard
    if dashboard_config is not None:
        if all(item["ok"] for item in projects):
            dashboard = _reconcile_dashboard(
                dashboard_config,
                registry,
                state_dir=state,
                live_index_runner=live_index_runner,
                dashboard_runner=dashboard_runner,
                clock=clock,
                defer_live_index=True,
            )
        else:
            dashboard = {
                "ok": False,
                "status": "skipped-project-failure",
                "changed": False,
            }
    if (
        dashboard is not None
        and dashboard.get("ok")
        and dashboard_config is not None
        and dashboard_config.live_index is not None
        and "live_index" in dashboard
    ):
        identity = "continuity-dashboard"
        dashboard_observations = obsidian_live_index.observe_many(
            [(identity, dashboard_config.live_index)],
            refresh_ids={identity} if dashboard.get("changed") else frozenset(),
            runner=live_index_runner,
        )
        observation = dashboard_observations[identity]
        observation = {**observation, "observed_at": _iso(clock())}
        dashboard["live_index"] = observation
        _record_live_index(state / "continuity-dashboard.json", observation)
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": bool(projects)
        and all(item["ok"] for item in projects)
        and (dashboard is None or bool(dashboard["ok"])),
        "registry": registry.path.as_posix(),
        "registry_digest": registry.digest,
        "projects": projects,
        "continuity_dashboard": dashboard,
    }


def reconcile_registry(
    registry: Registry,
    *,
    state_dir: str | Path,
    bead_exporter: BeadExporter | None = None,
    event_reader: EventReader = read_events,
    live_index_runner: LiveIndexRunner = obsidian_live_index.run_command,
    dashboard_runner: DashboardRunner = obsidian_continuity.run_command,
    clock: Clock = _now,
    force: bool = False,
) -> dict[str, Any]:
    """Run one atomic registry cycle while preserving the last complete success."""

    state = Path(state_dir).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state, 0o700)
    lock_handle, acquired = _lock(state, "registry-cycle")
    if not acquired:
        lock_handle.close()
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "status": "already-running",
            "registry": registry.path.as_posix(),
            "registry_digest": registry.digest,
            "projects": [],
            "continuity_dashboard": None,
        }
    try:
        return _reconcile_registry_unlocked(
            registry,
            state_dir=state,
            bead_exporter=bead_exporter,
            event_reader=event_reader,
            live_index_runner=live_index_runner,
            dashboard_runner=dashboard_runner,
            clock=clock,
            force=force,
        )
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def _check_registry_unlocked(
    registry: Registry,
    *,
    state_dir: str | Path,
    bead_exporter: BeadExporter | None = None,
    event_reader: EventReader = read_events,
    live_index_runner: LiveIndexRunner = obsidian_live_index.run_command,
    dashboard_runner: DashboardRunner = obsidian_continuity.run_command,
    clock: Clock = _now,
    require_live_index: bool = False,
) -> dict[str, Any]:
    state = Path(state_dir).expanduser().resolve()
    checked: list[dict[str, Any]] = []
    for project in registry.projects:
        if not project.enabled:
            continue
        filesystem_problems: list[str] = []
        state_payload = _read_state(state / f"{project.id}.json")
        last_success = state_payload.get("last_success")
        success_time = _parse_time(
            last_success.get("completed_at") if isinstance(last_success, dict) else None
        )
        age = (clock() - success_time).total_seconds() if success_time is not None else None
        if age is None or age > project.freshness_sla_seconds:
            filesystem_problems.append("last successful reconciliation exceeds freshness SLA")
        try:
            snapshot, _exported = _snapshot(
                project,
                registry,
                clock(),
                state_dir=state,
                bead_exporter=bead_exporter,
                event_reader=event_reader,
            )
            vault = obsidian_vault.gate_vault(
                project.output_dir,
                phase="readiness",
                expected_source_digest=snapshot["source_digest"],
                expected_work_authority="beads",
            )
            filesystem_problems.extend(vault.get("problems", []))
            source_digest = snapshot["source_digest"]
        except (ReconcileError, obsidian_vault.VaultError, OSError) as exc:
            filesystem_problems.append(_redact_error(exc))
            source_digest = None
        if require_live_index and not filesystem_problems:
            if project.live_index is None:
                live_index = obsidian_live_index.not_run(
                    configured=False,
                    status="not-configured",
                )
            else:
                live_index = obsidian_live_index.observe(
                    project.live_index,
                    refresh=False,
                    runner=live_index_runner,
                )
        elif require_live_index:
            live_index = obsidian_live_index.not_run(
                configured=project.live_index is not None,
                status="skipped-filesystem-invalid",
            )
        else:
            raw_success = last_success if isinstance(last_success, dict) else {}
            saved_observation = raw_success.get("live_index")
            live_index = (
                saved_observation
                if isinstance(saved_observation, dict)
                else obsidian_live_index.not_run(
                    configured=project.live_index is not None,
                    status="not-yet-observed",
                )
            )
        problems = list(filesystem_problems)
        if require_live_index and live_index.get("status") != "confirmed":
            problems.append(
                "live Obsidian index is not confirmed: "
                + str(live_index.get("status") or "unknown")
            )
        checked.append(
            {
                "id": project.id,
                "ok": not problems,
                "fresh": not problems,
                "filesystem_ok": not filesystem_problems,
                "live_index_required": require_live_index,
                "live_index": live_index,
                "age_seconds": age,
                "source_digest": source_digest,
                "problems": problems,
            }
        )
    dashboard_check: dict[str, Any] | None = None
    config = registry.continuity_dashboard
    if config is not None:
        dashboard_problems: list[str] = []
        state_payload = _read_state(state / "continuity-dashboard.json")
        last_success = state_payload.get("last_success")
        success_time = _parse_time(
            last_success.get("completed_at") if isinstance(last_success, dict) else None
        )
        age = (clock() - success_time).total_seconds() if success_time is not None else None
        if age is None or age > config.freshness_sla_seconds:
            dashboard_problems.append(
                "last successful dashboard reconciliation exceeds freshness SLA"
            )
        try:
            report = obsidian_continuity.capture_report(
                config,
                installed_registry=registry.path,
                state_dir=state,
                runner=dashboard_runner,
            )
            gate = obsidian_continuity.gate_dashboard(report, config.output_dir)
            dashboard_problems.extend(gate["problems"])
            snapshot_sha256 = report["snapshot_sha256"]
        except (obsidian_continuity.DashboardError, OSError) as exc:
            dashboard_problems.append(_redact_error(exc))
            snapshot_sha256 = None
        if require_live_index and not dashboard_problems:
            if config.live_index is None:
                live_index = obsidian_live_index.not_run(
                    configured=False,
                    status="not-configured",
                )
            else:
                live_index = obsidian_live_index.observe(
                    config.live_index,
                    refresh=False,
                    runner=live_index_runner,
                )
        elif require_live_index:
            live_index = obsidian_live_index.not_run(
                configured=config.live_index is not None,
                status="skipped-filesystem-invalid",
            )
        else:
            raw_success = last_success if isinstance(last_success, dict) else {}
            saved_observation = raw_success.get("live_index")
            live_index = (
                saved_observation
                if isinstance(saved_observation, dict)
                else obsidian_live_index.not_run(
                    configured=config.live_index is not None,
                    status="not-yet-observed",
                )
            )
        if require_live_index and live_index.get("status") != "confirmed":
            dashboard_problems.append(
                "live Obsidian dashboard index is not confirmed: "
                + str(live_index.get("status") or "unknown")
            )
        dashboard_check = {
            "ok": not dashboard_problems,
            "fresh": not dashboard_problems,
            "live_index_required": require_live_index,
            "live_index": live_index,
            "age_seconds": age,
            "snapshot_sha256": snapshot_sha256,
            "problems": dashboard_problems,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": bool(checked)
        and all(item["ok"] for item in checked)
        and (dashboard_check is None or bool(dashboard_check["ok"])),
        "registry_digest": registry.digest,
        "live_index_required": require_live_index,
        "projects": checked,
        "continuity_dashboard": dashboard_check,
    }


def check_registry(
    registry: Registry,
    *,
    state_dir: str | Path,
    bead_exporter: BeadExporter | None = None,
    event_reader: EventReader = read_events,
    live_index_runner: LiveIndexRunner = obsidian_live_index.run_command,
    dashboard_runner: DashboardRunner = obsidian_continuity.run_command,
    clock: Clock = _now,
    require_live_index: bool = False,
    lock_timeout_seconds: float = CHECK_LOCK_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Wait boundedly for the writer, then check one coherent registry snapshot."""

    if not math.isfinite(lock_timeout_seconds) or lock_timeout_seconds < 0:
        raise ValueError("lock timeout must be a finite non-negative number")

    state = Path(state_dir).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state, 0o700)
    lock_handle, acquired = _lock(
        state,
        "registry-cycle",
        timeout_seconds=lock_timeout_seconds,
    )
    if not acquired:
        lock_handle.close()
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "status": "lock-timeout",
            "lock_timeout_seconds": lock_timeout_seconds,
            "registry_digest": registry.digest,
            "live_index_required": require_live_index,
            "projects": [],
            "continuity_dashboard": None,
        }
    try:
        return _check_registry_unlocked(
            registry,
            state_dir=state,
            bead_exporter=bead_exporter,
            event_reader=event_reader,
            live_index_runner=live_index_runner,
            dashboard_runner=dashboard_runner,
            clock=clock,
            require_live_index=require_live_index,
        )
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


__all__ = [
    "CHECK_LOCK_TIMEOUT_SECONDS",
    "MAX_EXPORT_BYTES",
    "ReconcileError",
    "check_registry",
    "reconcile_registry",
]
