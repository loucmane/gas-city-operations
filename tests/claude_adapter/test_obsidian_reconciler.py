from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time

import pytest

from aegis_foundation import obsidian_ledger_reader, obsidian_live_index, obsidian_reconciler
from aegis_foundation.obsidian_reconcile_cli import build_parser
from aegis_foundation.obsidian_registry import RegistryError, load_registry


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    _run("git", "init", "-q", cwd=root)
    _run("git", "config", "user.email", "test@example.com", cwd=root)
    _run("git", "config", "user.name", "Test User", cwd=root)
    (root / "README.md").write_text("# Project\n", encoding="utf-8")
    _run("git", "add", "README.md", cwd=root)
    _run("git", "commit", "-qm", "initial", cwd=root)
    return root


def _beads(status: str = "open") -> bytes:
    return (
        json.dumps(
            [
                {
                    "id": "ga-eiyt",
                    "title": "Continuously reconcile Obsidian",
                    "status": status,
                    "priority": 1,
                    "issue_type": "bug",
                    "dependencies": [],
                    "metadata": {"gc.branch": "codex/ga-eiyt-obsidian-reconciler"},
                }
            ],
            sort_keys=True,
        )
        + "\n"
    ).encode()


def _ledger_event_values(root: Path) -> tuple[object, ...]:
    return (
        "1",
        "event-1",
        "2026-08-29T21:00:00Z",
        "session-1",
        "gas-city-operations",
        str(root),
        "codex/ga-ejrm-workflow-foundation",
        "0" * 40,
        str(root),
        "verification",
        "pytest",
        "test",
        "[]",
        "pass",
        "pass",
        1,
        "agent-1",
        "codex",
        None,
        "a" * 64,
        "{}",
    )


def _wal_ledger(root: Path, state_home: Path) -> tuple[sqlite3.Connection, Path]:
    store = obsidian_ledger_reader.ledger_store(root, {"XDG_STATE_HOME": str(state_home)})
    store.mkdir(parents=True)
    database = store / "ledger.db"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.execute("""
        CREATE TABLE events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            schema_version TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE,
            ts TEXT NOT NULL, session_id TEXT, repository_identity TEXT,
            worktree_root TEXT, branch TEXT, head TEXT, cwd TEXT,
            event_type TEXT NOT NULL, tool_name TEXT, handler TEXT,
            paths TEXT NOT NULL DEFAULT '[]', outcome TEXT, exit_class TEXT,
            duration_ms INTEGER, agent_id TEXT, agent_type TEXT,
            parent_agent_id TEXT, payload_digest TEXT,
            extra TEXT NOT NULL DEFAULT '{}'
        )
        """)
    placeholders = ",".join("?" for _ in range(21))
    columns = ",".join(obsidian_ledger_reader._FIELDS)
    connection.execute(
        f"INSERT INTO events ({columns}) VALUES ({placeholders})",
        _ledger_event_values(root),
    )
    connection.commit()
    return connection, database


def test_passive_ledger_uses_writable_snapshot_and_preserves_live_wal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    connection, database = _wal_ledger(root, tmp_path / "state")
    source_bytes = {path.name: path.read_bytes() for path in database.parent.iterdir()}
    opened: list[Path] = []
    original = obsidian_ledger_reader._sqlite_events

    def inspect_snapshot(path: Path, max_events: int) -> list[dict[str, object]]:
        opened.append(path)
        assert path.parent != database.parent
        assert path.parent.name.startswith("aegis-ledger-snapshot-")
        return original(path, max_events)

    monkeypatch.setattr(obsidian_ledger_reader, "_sqlite_events", inspect_snapshot)
    try:
        events = obsidian_ledger_reader.read_events(
            root, env={"XDG_STATE_HOME": str(tmp_path / "state")}
        )
        assert {path.name: path.read_bytes() for path in database.parent.iterdir()} == source_bytes
    finally:
        connection.close()
    assert [event["event_id"] for event in events] == ["event-1"]
    assert len(opened) == 1


def _registry(
    tmp_path: Path,
    root: Path,
    output: Path,
    *,
    live_index: dict[str, object] | None = None,
    continuity_dashboard: dict[str, object] | None = None,
) -> Path:
    path = tmp_path / "registry.json"
    project: dict[str, object] = {
        "id": "gas-city",
        "enabled": True,
        "target_dir": str(root),
        "output_dir": str(output),
        "bead_export_argv": ["/usr/bin/bd", "list", "--json"],
        "include_bead_content": False,
        "freshness_sla_seconds": 180,
    }
    if live_index is not None:
        project["live_index"] = live_index
    payload: dict[str, object] = {
        "schema_version": "1",
        "projects": [project],
    }
    if continuity_dashboard is not None:
        payload["continuity_dashboard"] = continuity_dashboard
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_registry_is_explicit_bounded_and_rejects_ambiguous_paths(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    registry_path = _registry(tmp_path, root, tmp_path / "vault")
    registry = load_registry(registry_path)
    assert registry.projects[0].id == "gas-city"
    assert registry.projects[0].bead_export_argv[0] == "/usr/bin/bd"
    assert registry.projects[0].freshness_sla_seconds == 180

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["projects"][0]["bead_export_argv"][0] = "bd"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="absolute executable"):
        load_registry(registry_path)

    payload["projects"][0]["bead_export_argv"][0] = "/usr/bin/bd"
    payload["projects"][0]["output_dir"] = str(root / "forbidden")
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="outside target_dir"):
        load_registry(registry_path)

    payload["projects"][0]["output_dir"] = str(root.parent)
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="must not overlap target_dir"):
        load_registry(registry_path)


def test_registry_live_index_contract_is_strict_and_not_arbitrary_argv(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    live_index = {
        "obsidian_cli": "/home/example/.local/bin/obsidian",
        "vault": "main",
        "probe_path": "GasCity/gas-city-operations/Aegis/Beads/ga-a9ap.md",
        "timeout_seconds": 15,
    }
    registry_path = _registry(tmp_path, root, tmp_path / "vault", live_index=live_index)
    registry = load_registry(registry_path)
    configured = registry.projects[0].live_index
    assert configured is not None
    assert configured.obsidian_cli == Path("/home/example/.local/bin/obsidian")
    assert configured.vault == "main"
    assert configured.probe_path == "GasCity/gas-city-operations/Aegis/Beads/ga-a9ap.md"
    assert configured.timeout_seconds == 15

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["projects"][0]["live_index"]["obsidian_cli"] = "obsidian"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="absolute executable"):
        load_registry(registry_path)

    payload["projects"][0]["live_index"]["obsidian_cli"] = "/usr/bin/obsidian"
    payload["projects"][0]["live_index"]["probe_path"] = "../outside.md"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="safe relative path"):
        load_registry(registry_path)

    payload["projects"][0]["live_index"]["probe_path"] = "Aegis/Beads/ga-a9ap.md"
    payload["projects"][0]["live_index"]["refresh_argv"] = ["/bin/sh", "-c", "anything"]
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="unknown live_index fields"):
        load_registry(registry_path)


def test_registry_continuity_dashboard_is_strict_and_output_isolated(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault" / "project"
    dashboard = {
        "python": "/usr/bin/python3",
        "entrypoint": "/srv/gas-city-ops/continuity.py",
        "workflow_registry": "/srv/gas-city-ops/projects.json",
        "signing_policies": "/etc/gas-city-signing/signing-policies.json",
        "output_dir": str(tmp_path / "vault" / "Continuity"),
        "live_index": {
            "obsidian_cli": "/usr/bin/obsidian",
            "vault": "main",
            "probe_path": "GasCity/Continuity/Status.md",
        },
    }
    registry_path = _registry(
        tmp_path,
        root,
        output,
        continuity_dashboard=dashboard,
    )
    registry = load_registry(registry_path)
    assert registry.continuity_dashboard is not None
    assert registry.continuity_dashboard.output_dir.name == "Continuity"

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["continuity_dashboard"]["unknown"] = True
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="unknown continuity_dashboard fields"):
        load_registry(registry_path)

    payload["continuity_dashboard"].pop("unknown")
    payload["continuity_dashboard"]["output_dir"] = str(output / "nested")
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RegistryError, match="must not overlap"):
        load_registry(registry_path)


def test_reconcile_publishes_changed_snapshot_and_noops_when_current(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    registry = load_registry(_registry(tmp_path, root, output))
    state_dir = tmp_path / "state"
    exports = [_beads(), _beads()]

    def export(_argv: tuple[str, ...], _timeout: int, **_kwargs) -> bytes:
        return exports.pop(0)

    def clock() -> datetime:
        return datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc)

    first = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=export,
        event_reader=lambda _target: [],
        clock=clock,
    )
    assert first["ok"] is True
    assert first["projects"][0]["status"] == "built"
    assert (output / "Beads" / "ga-eiyt.md").is_file()
    before = (output / ".aegis-vault.json").read_bytes()

    second = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=export,
        event_reader=lambda _target: [],
        clock=clock,
        force=True,
    )
    assert second["ok"] is True
    assert second["projects"][0]["status"] == "current"
    assert (output / ".aegis-vault.json").read_bytes() == before
    state = json.loads((state_dir / "gas-city.json").read_text(encoding="utf-8"))
    assert state["last_success"]["source_digest"] == second["projects"][0]["source_digest"]
    assert state["last_error"] is None


def test_reconcile_publishes_and_checks_continuity_dashboard(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    project_output = tmp_path / "vault" / "project"
    dashboard_output = tmp_path / "vault" / "Continuity"
    project_probe = "GasCity/gas-city/Aegis/Home.md"
    dashboard_probe = "GasCity/Continuity/Status.md"
    registry = load_registry(
        _registry(
            tmp_path,
            root,
            project_output,
            live_index={
                "obsidian_cli": "/usr/bin/obsidian",
                "vault": "main",
                "probe_path": project_probe,
                "timeout_seconds": 15,
            },
            continuity_dashboard={
                "python": "/usr/bin/python3",
                "entrypoint": "/srv/gas-city-ops/continuity.py",
                "workflow_registry": "/srv/gas-city-ops/projects.json",
                "signing_policies": "/etc/gas-city-signing/signing-policies.json",
                "output_dir": str(dashboard_output),
                "live_index": {
                    "obsidian_cli": "/usr/bin/obsidian",
                    "vault": "main",
                    "probe_path": dashboard_probe,
                    "timeout_seconds": 15,
                },
            },
        )
    )
    state_dir = tmp_path / "state"
    live_calls: list[tuple[str, ...]] = []

    def live_index_runner(
        argv: tuple[str, ...], _timeout: int
    ) -> subprocess.CompletedProcess[bytes]:
        live_calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, b"ok\n", b"")

    def dashboard_runner(
        argv: tuple[str, ...], _timeout: int
    ) -> subprocess.CompletedProcess[bytes]:
        output = Path(argv[argv.index("--output") + 1])
        if "snapshot" in argv:
            assert argv[argv.index("--obsidian-cycle-status") + 1] == "idle"
            output.write_text("{}\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        project_state = json.loads((state_dir / "gas-city.json").read_text(encoding="utf-8"))
        assert project_state["last_success"]["live_index"]["status"] == "confirmed"
        report = {
            "schema": "gas-city-workflow.continuity-report.v1",
            "ok": False,
            "snapshot_sha256": "a" * 64,
            "registry_sha256": "b" * 64,
            "summary": {"counts": {"current": 1, "next": 0, "blocked": 0}},
            "work": {
                "current": [{"id": "ga-root", "title": "Initiative", "status": "open"}],
                "next": [],
                "blocked": [],
                "deferred": [],
                "legacy": [],
                "generated": [],
                "orphaned": [],
            },
            "findings": [],
            "next_actions": [],
            "projects": [],
        }
        output.write_text(json.dumps(report) + "\n", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 3, b"", b"")

    def clock() -> datetime:
        return datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc)

    first = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=live_index_runner,
        dashboard_runner=dashboard_runner,
        clock=clock,
        force=True,
    )
    assert first["ok"] is True
    assert first["continuity_dashboard"]["status"] == "built"
    assert first["continuity_dashboard"]["report_ok"] is False
    assert (dashboard_output / "Status.md").is_file()
    assert live_calls == [
        ("/usr/bin/obsidian", "vault=main", "reload"),
        ("/usr/bin/obsidian", "vault=main", "read", f"path={project_probe}"),
        ("/usr/bin/obsidian", "vault=main", "reload"),
        ("/usr/bin/obsidian", "vault=main", "read", f"path={dashboard_probe}"),
    ]

    live_calls.clear()
    second = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=live_index_runner,
        dashboard_runner=dashboard_runner,
        clock=clock,
        force=True,
    )
    assert second["ok"] is True
    assert second["continuity_dashboard"]["status"] == "current"
    assert second["continuity_dashboard"]["changed"] is False
    assert live_calls == [
        ("/usr/bin/obsidian", "vault=main", "read", f"path={project_probe}"),
        ("/usr/bin/obsidian", "vault=main", "read", f"path={dashboard_probe}"),
    ]

    checked = obsidian_reconciler.check_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=live_index_runner,
        dashboard_runner=dashboard_runner,
        clock=clock,
    )
    assert checked["ok"] is True
    assert checked["continuity_dashboard"]["ok"] is True


def test_changed_publication_refreshes_and_probes_live_index_once(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    live_index = {
        "obsidian_cli": "/usr/bin/obsidian",
        "vault": "main",
        "probe_path": "GasCity/gas-city-operations/Aegis/Beads/ga-eiyt.md",
        "timeout_seconds": 15,
    }
    registry = load_registry(_registry(tmp_path, root, output, live_index=live_index))
    state_dir = tmp_path / "state"
    calls: list[tuple[tuple[str, ...], int]] = []

    def run(argv: tuple[str, ...], timeout: int) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, timeout))
        return subprocess.CompletedProcess(argv, 0, b"ok\n", b"")

    first = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=run,
        force=True,
    )
    assert first["ok"] is True
    assert first["projects"][0]["live_index"]["status"] == "confirmed"
    assert calls == [
        (("/usr/bin/obsidian", "vault=main", "reload"), 15),
        (
            (
                "/usr/bin/obsidian",
                "vault=main",
                "read",
                "path=GasCity/gas-city-operations/Aegis/Beads/ga-eiyt.md",
            ),
            15,
        ),
    ]
    state = json.loads((state_dir / "gas-city.json").read_text(encoding="utf-8"))
    assert state["last_success"]["live_index"]["status"] == "confirmed"

    calls.clear()
    second = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=run,
        force=True,
    )
    assert second["ok"] is True
    assert second["projects"][0]["status"] == "current"
    assert second["projects"][0]["live_index"]["status"] == "confirmed"
    assert calls == [
        (
            (
                "/usr/bin/obsidian",
                "vault=main",
                "read",
                "path=GasCity/gas-city-operations/Aegis/Beads/ga-eiyt.md",
            ),
            15,
        )
    ]


def test_registry_cycle_preserves_last_complete_success_until_live_observation(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    registry = load_registry(
        _registry(
            tmp_path,
            root,
            output,
            live_index={
                "obsidian_cli": "/usr/bin/obsidian",
                "vault": "main",
                "probe_path": "GasCity/gas-city/Aegis/Home.md",
            },
        )
    )
    state_dir = tmp_path / "state"
    inspect_pending = False

    def run(argv: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        if inspect_pending:
            state = json.loads((state_dir / "gas-city.json").read_text(encoding="utf-8"))
            assert state["last_success"]["live_index"]["status"] == "confirmed"
            assert state["pending_success"]["live_index"]["status"] == ("pending-cycle-observation")
        return subprocess.CompletedProcess(argv, 0, b"ok\n", b"")

    def clock() -> datetime:
        return datetime(2026, 8, 31, 18, 30, tzinfo=timezone.utc)

    first = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=run,
        clock=clock,
        force=True,
    )
    assert first["ok"] is True

    inspect_pending = True
    second = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=run,
        clock=clock,
        force=True,
    )

    assert second["ok"] is True
    state = json.loads((state_dir / "gas-city.json").read_text(encoding="utf-8"))
    assert "pending_success" not in state
    assert state["last_success"]["live_index"] == {
        "authority": "host-obsidian-ipc",
        "configured": True,
        "observed_at": "2026-08-31T18:30:00Z",
        "ok": True,
        "probe": {
            "detail": "",
            "ok": True,
            "returncode": 0,
            "status": "passed",
        },
        "probe_path": "GasCity/gas-city/Aegis/Home.md",
        "refresh": None,
        "refresh_attempted": False,
        "status": "confirmed",
        "vault": "main",
    }


def test_registry_cycle_lock_makes_concurrent_invocation_a_noop(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    registry = load_registry(_registry(tmp_path, root, tmp_path / "vault"))
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    lock_path = state_dir / "registry-cycle.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = obsidian_reconciler.reconcile_registry(
            registry,
            state_dir=state_dir,
            bead_exporter=lambda _argv, _timeout, **_kwargs: pytest.fail("export must not run"),
            event_reader=lambda _target: pytest.fail("ledger read must not run"),
        )

    assert result["ok"] is True
    assert result["status"] == "already-running"
    assert result["projects"] == []
    assert not (state_dir / "gas-city.json").exists()


def test_registry_check_waits_for_reconciliation_then_checks_stable_snapshot(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    registry = load_registry(_registry(tmp_path, root, output))
    state_dir = tmp_path / "state"
    now = datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc)
    obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        clock=lambda: now,
        force=True,
    )
    lock_path = state_dir / "registry-cycle.lock"
    released = threading.Event()
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        def release_after_overlap() -> None:
            time.sleep(0.05)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            released.set()

        release = threading.Thread(target=release_after_overlap)
        release.start()
        try:
            result = obsidian_reconciler.check_registry(
                registry,
                state_dir=state_dir,
                bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
                event_reader=lambda _target: [],
                clock=lambda: now,
                lock_timeout_seconds=1.0,
            )
        finally:
            release.join(timeout=1.0)

    assert released.is_set()
    assert result["ok"] is True
    assert result["projects"][0]["source_digest"]
    assert result["projects"][0]["problems"] == []


def test_registry_check_times_out_fail_closed_while_cycle_lock_is_held(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    registry = load_registry(_registry(tmp_path, root, tmp_path / "vault"))
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    lock_path = state_dir / "registry-cycle.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = obsidian_reconciler.check_registry(
            registry,
            state_dir=state_dir,
            bead_exporter=lambda _argv, _timeout, **_kwargs: pytest.fail("export must not run"),
            event_reader=lambda _target: pytest.fail("ledger read must not run"),
            lock_timeout_seconds=0.01,
        )

    assert result == {
        "schema_version": "1",
        "ok": False,
        "status": "lock-timeout",
        "lock_timeout_seconds": 0.01,
        "registry_digest": registry.digest,
        "live_index_required": False,
        "projects": [],
        "continuity_dashboard": None,
    }


def test_changed_multi_project_cycle_reloads_shared_obsidian_endpoint_once(
    tmp_path: Path,
) -> None:
    first_root = _repo(tmp_path)
    second_parent = tmp_path / "second"
    second_parent.mkdir()
    second_root = _repo(second_parent)
    registry_path = _registry(
        tmp_path,
        first_root,
        tmp_path / "vault" / "gas-city",
        live_index={
            "obsidian_cli": "/usr/bin/obsidian",
            "vault": "main",
            "probe_path": "GasCity/gas-city/Aegis/Home.md",
            "timeout_seconds": 15,
        },
    )
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["projects"].append(
        {
            "id": "blog",
            "enabled": True,
            "target_dir": str(second_root),
            "output_dir": str(tmp_path / "vault" / "blog"),
            "bead_export_argv": ["/usr/bin/bd", "list", "--json"],
            "include_bead_content": False,
            "freshness_sla_seconds": 180,
            "live_index": {
                "obsidian_cli": "/usr/bin/obsidian",
                "vault": "main",
                "probe_path": "GasCity/blog/Aegis/Home.md",
                "timeout_seconds": 15,
            },
        }
    )
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    registry = load_registry(registry_path)
    calls: list[tuple[tuple[str, ...], int]] = []

    def run(argv: tuple[str, ...], timeout: int) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, timeout))
        return subprocess.CompletedProcess(argv, 0, b"ok\n", b"")

    result = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=tmp_path / "state",
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=run,
        force=True,
    )

    assert result["ok"] is True
    assert [call for call in calls if call[0][-1] == "reload"] == [
        (("/usr/bin/obsidian", "vault=main", "reload"), 15)
    ]
    assert sorted(call[0][-1] for call in calls if "read" in call[0]) == [
        "path=GasCity/blog/Aegis/Home.md",
        "path=GasCity/gas-city/Aegis/Home.md",
    ]
    for project in result["projects"]:
        assert project["live_index"]["status"] == "confirmed"
        state = json.loads(
            (tmp_path / "state" / f"{project['id']}.json").read_text(encoding="utf-8")
        )
        assert state["last_success"]["live_index"]["status"] == "confirmed"


def test_unobservable_obsidian_is_observer_limited_not_publication_failure(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    registry = load_registry(
        _registry(
            tmp_path,
            root,
            output,
            live_index={
                "obsidian_cli": "/usr/bin/obsidian",
                "vault": "main",
                "probe_path": "GasCity/gas-city-operations/Aegis/Home.md",
            },
        )
    )

    def unavailable(argv: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            argv,
            1,
            b"",
            b"The CLI is unable to find Obsidian. Please make sure Obsidian is running.",
        )

    result = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=tmp_path / "state",
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=unavailable,
        force=True,
    )
    assert result["ok"] is True
    project = result["projects"][0]
    assert project["status"] == "built"
    assert project["live_index"]["status"] == "unavailable"
    assert project["live_index"]["authority"] == "observer-limited"
    assert (output / "Beads" / "ga-eiyt.md").is_file()


def test_live_index_is_optional_for_filesystem_check_and_explicitly_gateable(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    registry = load_registry(
        _registry(
            tmp_path,
            root,
            output,
            live_index={
                "obsidian_cli": "/usr/bin/obsidian",
                "vault": "main",
                "probe_path": "GasCity/gas-city-operations/Aegis/Beads/ga-eiyt.md",
            },
        )
    )
    state_dir = tmp_path / "state"

    def ok_runner(argv: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 0, b"ok\n", b"")

    obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=ok_runner,
        force=True,
    )

    def failed_probe(argv: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 2, b"", b"managed note not indexed")

    filesystem = obsidian_reconciler.check_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=failed_probe,
    )
    assert filesystem["ok"] is True

    live = obsidian_reconciler.check_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        live_index_runner=failed_probe,
        require_live_index=True,
    )
    assert live["ok"] is False
    assert live["projects"][0]["filesystem_ok"] is True
    assert live["projects"][0]["live_index"]["status"] == "failed"
    assert "live Obsidian index" in live["projects"][0]["problems"][-1]


def test_live_index_timeout_and_output_overflow_are_bounded(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    registry = load_registry(
        _registry(
            tmp_path,
            root,
            tmp_path / "vault",
            live_index={
                "obsidian_cli": "/usr/bin/obsidian",
                "vault": "main",
                "probe_path": "GasCity/Aegis/Home.md",
            },
        )
    )
    config = registry.projects[0].live_index
    assert config is not None

    def timeout(_argv: tuple[str, ...], seconds: int) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired("obsidian", seconds)

    timed_out = obsidian_live_index.observe(config, refresh=True, runner=timeout)
    assert timed_out["ok"] is False
    assert timed_out["status"] == "timeout"
    assert timed_out["probe"] is None

    def overflow(argv: tuple[str, ...], _seconds: int) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            argv,
            0,
            b"x" * (obsidian_live_index.MAX_OUTPUT_BYTES + 1),
            b"",
        )

    too_large = obsidian_live_index.observe(config, refresh=False, runner=overflow)
    assert too_large["ok"] is False
    assert too_large["status"] == "failed"
    assert "bounded size" in too_large["probe"]["detail"]


def test_cli_has_explicit_live_index_gate_only_on_check() -> None:
    parser = build_parser()
    check = parser.parse_args(
        [
            "check",
            "--registry",
            "/tmp/registry.json",
            "--require-live-index",
        ]
    )
    assert check.require_live_index is True
    assert check.lock_timeout_seconds == obsidian_reconciler.CHECK_LOCK_TIMEOUT_SECONDS
    bounded = parser.parse_args(
        [
            "check",
            "--registry",
            "/tmp/registry.json",
            "--lock-timeout-seconds",
            "2.5",
        ]
    )
    assert bounded.lock_timeout_seconds == 2.5
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "--registry",
                "/tmp/registry.json",
                "--require-live-index",
            ]
        )


def test_export_failure_retains_last_good_vault_and_records_error(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    registry = load_registry(_registry(tmp_path, root, output))
    state_dir = tmp_path / "state"

    obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
        force=True,
    )
    before = {
        path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()
    }

    def fail(_argv: tuple[str, ...], _timeout: int, **_kwargs) -> bytes:
        raise obsidian_reconciler.ReconcileError("Dolt unavailable")

    result = obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=fail,
        event_reader=lambda _target: [],
        force=True,
    )
    assert result["ok"] is False
    assert "Dolt unavailable" in result["projects"][0]["error"]
    after = {
        path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()
    }
    assert after == before
    state = json.loads((state_dir / "gas-city.json").read_text(encoding="utf-8"))
    assert state["last_success"] is not None
    assert state["last_error"]["message"] == "Dolt unavailable"


def test_built_zipapp_reads_explicit_rig_and_preserves_vault_on_unexpected_stderr(
    tmp_path: Path,
) -> None:
    from aegis_foundation.obsidian_install import build_runtime_bytes

    root = _repo(tmp_path)
    output = tmp_path / "vault" / "Aegis"
    output.parent.mkdir()
    state_dir = tmp_path / "state"
    registry_path = _registry(tmp_path, root, output)
    fake_gc = tmp_path / "gc"
    notice = tmp_path / "notice"
    gate = tmp_path / "hpfetcher" / ".beads.gate.lock"
    # cmd/gc/cmd_bd.go:577 discloses the scope before cmd.Run at :731.
    notice.write_text(
        'gc bd: answering from the rig "hpfetcher" store\n'
        "warning: workspace gate acquisition failed, continuing ungated: "
        f"workspacegate: open gate {gate}: open {gate}: read-only file system\n"
    )
    arguments = [
        "--city",
        str(tmp_path / "city"),
        "--rig",
        "hpfetcher",
        "bd",
        "list",
        "--all",
        "--limit",
        "0",
        "--json",
    ]
    fake_gc.write_text(
        f"#!{sys.executable}\n"
        "import sys\nfrom pathlib import Path\n"
        f"assert sys.argv[1:] == {arguments!r}\n"
        f"sys.stdout.buffer.write({_beads().replace(b'ga-eiyt', b'hpf-123')!r})\n"
        f"sys.stderr.write(Path({str(notice)!r}).read_text())\n"
    )
    fake_gc.chmod(0o755)
    payload = json.loads(registry_path.read_text())
    payload["projects"][0]["id"] = "hpfetcher"
    payload["projects"][0]["bead_export_argv"] = [str(fake_gc), *arguments]
    payload["projects"][0]["bead_gate_paths"] = [str(gate)]
    payload["export_dir"] = str(tmp_path / "exports")
    registry_path.write_text(json.dumps(payload))
    runtime = tmp_path / "aegis-obsidian-reconcile"
    runtime.write_bytes(build_runtime_bytes(Path(__file__).parents[2]))
    command = [
        sys.executable,
        str(runtime),
        "run",
        "--registry",
        str(registry_path),
        "--state-dir",
        str(state_dir),
        "--force",
    ]
    export_command = [sys.executable, str(runtime), "export", "--registry", str(registry_path)]
    exported = subprocess.run(export_command, cwd=tmp_path, capture_output=True, check=False)
    assert exported.returncode == 0, exported.stdout + exported.stderr
    first = subprocess.run(command, cwd=tmp_path, capture_output=True, check=False)
    assert first.returncode == 0, first.stdout + first.stderr
    assert json.loads(first.stdout)["ok"] is True
    assert (output / "Beads" / "hpf-123.md").is_file()
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    source_before = (state_dir / "hpfetcher-beads.json").read_bytes()
    notice.write_text('gc bd: answering from the rig "blog" store\n')
    exported = subprocess.run(export_command, cwd=tmp_path, capture_output=True, check=False)
    assert exported.returncode == 1
    failed = subprocess.run(command, cwd=tmp_path, capture_output=True, check=False)
    assert failed.returncode == 1
    assert "unexpected stderr" in json.loads(failed.stdout)["projects"][0]["error"]
    assert {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before
    assert (state_dir / "hpfetcher-beads.json").read_bytes() == source_before
    state = json.loads((state_dir / "hpfetcher.json").read_text())
    assert state["last_success"] is not None
    assert "unexpected stderr" in state["last_error"]["message"]


def test_health_check_detects_source_staleness_not_just_old_timestamps(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "vault"
    registry = load_registry(_registry(tmp_path, root, output))
    state_dir = tmp_path / "state"
    current = [_beads()]
    obsidian_reconciler.reconcile_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: current[0],
        event_reader=lambda _target: [],
        force=True,
    )

    healthy = obsidian_reconciler.check_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads(),
        event_reader=lambda _target: [],
    )
    assert healthy["ok"] is True

    stale = obsidian_reconciler.check_registry(
        registry,
        state_dir=state_dir,
        bead_exporter=lambda _argv, _timeout, **_kwargs: _beads("closed"),
        event_reader=lambda _target: [],
    )
    assert stale["ok"] is False
    assert stale["projects"][0]["fresh"] is False
    assert "source digest" in stale["projects"][0]["problems"][0]
