from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from aegis_foundation import obsidian_install

REPO_ROOT = Path(__file__).parents[2]


def test_rendered_user_units_are_reboot_persistent_and_output_scoped(tmp_path: Path) -> None:
    home = tmp_path / "home"
    output = home / "vaults" / "main" / "GasCity" / "Aegis"
    registry = home / ".config" / "aegis" / "obsidian-projects.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "projects": [
                    {
                        "id": "gas-city",
                        "enabled": True,
                        "target_dir": str(home / "codex"),
                        "output_dir": str(output),
                        "bead_export_argv": ["/usr/bin/bd", "list", "--json"],
                        "freshness_sla_seconds": 180,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assets = obsidian_install.render_assets(home=home, registry_path=registry)
    service = assets["aegis-obsidian-reconcile.service"].decode()
    timer = assets["aegis-obsidian-reconcile.timer"].decode()

    assert (
        f'ExecStart="{home}/.local/bin/aegis-obsidian-reconcile" run '
        f'--registry "{registry}"' in service
    )
    assert f'ReadWritePaths="{output.parent}"' in service
    assert f'ReadWritePaths="{output}"\n' not in service
    assert f'ReadWritePaths="{home}/.local/state/aegis/obsidian-reconciler"' in service
    assert "NoNewPrivileges=true" in service
    assert "ProtectSystem=strict" in service
    assert "ProtectHome=read-only" in service
    assert f'Environment="GC_HOME={home}/gascity/home"' in service
    assert 'Environment="GIT_OPTIONAL_LOCKS=0"' in service
    assert "OnBootSec=45s" in timer
    assert "OnActiveSec=60s" in timer
    assert "OnUnitInactiveSec=60s" in timer
    assert "OnUnitActiveSec=" not in timer
    assert "Persistent=true" in timer


def test_tracked_registry_grants_write_access_to_all_nine_project_folders(tmp_path: Path) -> None:
    assets = obsidian_install.render_assets(
        home=tmp_path / "home",
        registry_path=REPO_ROOT / "plugins/gas-city-workflow/config/obsidian-projects.json",
    )
    service = assets["aegis-obsidian-reconcile.service"].decode()
    write_lines = {line for line in service.splitlines() if line.startswith("ReadWritePaths=")}
    vault_root = Path("/home/loucmane/vaults/main/GasCity")
    expected_projects = {
        "gas-city-operations", "gas-city", "hpfetcher", "blog", "gas-city-template",
        "bounty", "vernissage", "harpoon", "gas-city-hq",
    }
    assert write_lines == {
        *(f'ReadWritePaths="{vault_root / project}"' for project in expected_projects),
        f'ReadWritePaths="{vault_root}"',
        f'ReadWritePaths="{tmp_path}/home/.local/state/aegis/obsidian-reconciler"',
    }
    assert "ProtectSystem=strict" in service
    assert "ProtectHome=read-only" in service


def test_runtime_archive_is_byte_deterministic(tmp_path: Path) -> None:
    first = obsidian_install.build_runtime_bytes(Path(__file__).parents[2])
    second = obsidian_install.build_runtime_bytes(Path(__file__).parents[2])
    assert first == second
    assert first.startswith(b"#!/usr/bin/env python3\nPK")
    runtime = tmp_path / "aegis-obsidian-reconcile"
    runtime.write_bytes(first)
    runtime.chmod(0o755)
    result = subprocess.run(
        [str(runtime), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "run" in result.stdout
    assert "check" in result.stdout


def test_source_installer_plans_from_external_working_directory(tmp_path: Path) -> None:
    home = tmp_path / "home"
    registry = _source_registry(tmp_path, home)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/install-aegis-obsidian-reconciler"),
            "--plan",
            "--registry-source",
            str(registry),
            "--home",
            str(home),
            "--source-root",
            str(REPO_ROOT),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["schema_version"] == "1"
    assert plan["service_transition"] == [
        "stop aegis-obsidian-reconcile.timer",
        "wait for aegis-obsidian-reconcile.service to become inactive",
        "wait for aegis-obsidian-export.service to become inactive",
        "systemctl --user daemon-reload",
        "enable aegis-obsidian-reconcile.timer",
        "start aegis-obsidian-reconcile.service",
        "check installed reconciliation while timer remains inactive",
        "start aegis-obsidian-reconcile.timer",
    ]


def test_systemctl_start_uses_reconciliation_wide_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(obsidian_install.subprocess, "run", run)

    obsidian_install._run_systemctl("start", "aegis-obsidian-reconcile.service")
    obsidian_install._run_systemctl("start", "aegis-obsidian-reconcile.timer")

    assert calls[0][1]["timeout"] == 600
    assert calls[1][1]["timeout"] == 30


def test_quiescence_waits_for_activating_oneshot(monkeypatch):
    states = iter([
        {"active": False, "active_value": "activating"},
        {"active": False, "active_value": "inactive"},
    ])
    waits = []
    monkeypatch.setattr(obsidian_install, "_unit_state", lambda unit: next(states))
    monkeypatch.setattr(obsidian_install.time, "sleep", waits.append)
    result = obsidian_install._wait_for_service_inactive("aegis-obsidian-export.service")
    assert result["active_value"] == "inactive"
    assert waits == [0.25]


def _source_registry(tmp_path: Path, home: Path) -> Path:
    path = tmp_path / "registry-source.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "projects": [
                    {
                        "id": "gas-city",
                        "enabled": True,
                        "target_dir": str(home / "codex"),
                        "output_dir": str(home / "vaults/main/GasCity/Aegis"),
                        "bead_export_argv": ["/usr/bin/bd", "list", "--json"],
                        "freshness_sla_seconds": 180,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("defer_activation", [False, True])
def test_install_applies_exact_user_files_and_enables_timer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defer_activation: bool
) -> None:
    home = tmp_path / "home"
    registry = _source_registry(tmp_path, home)
    output_parent = home / "vaults/main/GasCity"
    output_parent.mkdir(parents=True)
    systemctl_calls: list[tuple[str, ...]] = []
    timer_enabled = True
    timer_active = True

    def systemctl(*arguments: str) -> subprocess.CompletedProcess[str]:
        nonlocal timer_active, timer_enabled
        systemctl_calls.append(arguments)
        if arguments[:2] == ("stop", "aegis-obsidian-reconcile.timer"):
            timer_active = False
        if arguments[:2] == ("enable", "aegis-obsidian-reconcile.timer"):
            timer_enabled = True
        if arguments[:2] == ("start", "aegis-obsidian-reconcile.timer"):
            timer_active = True
        if arguments[:2] == ("start", "aegis-obsidian-reconcile.service"):
            state = home / ".local/state/aegis/obsidian-reconciler"
            assert state.is_dir()
            assert state.stat().st_mode & 0o777 == 0o700
        if arguments[0] == "is-enabled":
            enabled = timer_enabled if arguments[1].endswith(".timer") else False
            return subprocess.CompletedProcess(
                arguments,
                0 if enabled else 1,
                "enabled\n" if enabled else "disabled\n",
                "",
            )
        if arguments[0] == "is-active":
            active = timer_active if arguments[1].endswith(".timer") else False
            return subprocess.CompletedProcess(
                arguments,
                0 if active else 1,
                "active\n" if active else "inactive\n",
                "",
            )
        if arguments[0] == "show" and "SubState" in arguments:
            value = "waiting\n" if arguments[1].endswith(".timer") and timer_active else "dead\n"
            return subprocess.CompletedProcess(arguments, 0, value, "")
        if arguments[0] == "show" and "Result" in arguments:
            return subprocess.CompletedProcess(arguments, 0, "success\n", "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(obsidian_install, "_run_systemctl", systemctl)
    monkeypatch.setattr(
        obsidian_install.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, '{"ok":true}\n', ""),
    )

    result = obsidian_install.install(
        home=home,
        source_root=Path(__file__).parents[2],
        registry_source=registry,
        **({"defer_activation": True} if defer_activation else {}),
    )

    assert result["ok"] is True
    assert (home / ".config/systemd/user/aegis-obsidian-export.service").is_file()
    assert (home / ".local/state/aegis/obsidian-exports").stat().st_mode & 0o777 == 0o700
    assert (home / ".local/bin/aegis-obsidian-reconcile").stat().st_mode & 0o777 == 0o755
    assert (home / ".config/aegis/obsidian-projects.json").stat().st_mode & 0o777 == 0o600
    assert (home / ".local/state/aegis/obsidian-reconciler/install-manifest.json").is_file()
    if defer_activation:
        assert result["status"] == "installed-awaiting-validation"
        assert not any(call[0] in {"start", "enable"} for call in systemctl_calls)
        assert not timer_active
        assert obsidian_install.main([
            "--check", "--defer-activation", "--home", str(home),
            "--source-root", str(REPO_ROOT), "--registry-source", str(registry),
        ]) == 0
        # Model a previously installed version with its own correct manifest.
        # Upgrade must replace both bytes and hashes while keeping scheduling off.
        runtime = home / ".local/bin/aegis-obsidian-reconcile"
        manifest_path = home / ".local/state/aegis/obsidian-reconciler/install-manifest.json"
        prior = json.loads(manifest_path.read_text())
        runtime.write_bytes(b"previous reviewed runtime\n")
        prior["files"][str(runtime)] = hashlib.sha256(runtime.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(prior))
        arguments = [
            "--defer-activation", "--home", str(home), "--source-root", str(REPO_ROOT),
            "--registry-source", str(registry),
        ]
        assert obsidian_install.main(["--check", *arguments]) == 1
        prior_manifest = manifest_path.read_bytes()
        real_write = obsidian_install._atomic_write

        def fail_manifest(path, content, mode):
            if path == manifest_path and content != prior_manifest:
                raise OSError("fixture manifest publication failure")
            real_write(path, content, mode)

        monkeypatch.setattr(obsidian_install, "_atomic_write", fail_manifest)
        assert obsidian_install.main(["--apply", *arguments]) == 1
        assert manifest_path.read_bytes() == prior_manifest
        assert runtime.read_bytes() == b"previous reviewed runtime\n"
        assert not timer_active
        monkeypatch.setattr(obsidian_install, "_atomic_write", real_write)
        assert obsidian_install.main(["--apply", *arguments]) == 0
        assert obsidian_install.main(["--check", *arguments]) == 0
        assert manifest_path.read_bytes() != prior_manifest
        assert not any(call[0] == "start" for call in systemctl_calls)
        return
    assert ("enable", "--now", "aegis-obsidian-reconcile.timer") not in systemctl_calls
    assert ("enable", "aegis-obsidian-reconcile.timer") in systemctl_calls
    assert systemctl_calls.index(
        ("start", "aegis-obsidian-reconcile.service")
    ) < systemctl_calls.index(("start", "aegis-obsidian-reconcile.timer"))


def test_rollback_unit_policy_ignores_transient_preflight_substates() -> None:
    errors = obsidian_install._rollback_unit_policy_errors(
        before_timer={"enabled": True, "active": True, "substate": "running"},
        baseline_service={
            "enabled": False,
            "active": False,
            "substate": "dead",
            "result": "success",
        },
        restored_timer={"enabled": True, "active": True, "substate": "waiting"},
        restored_service={
            "enabled": False,
            "active": False,
            "substate": "dead",
            "result": "success",
        },
    )

    assert errors == []


def test_quiescence_failure_restores_timer_without_stopping_active_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    registry = _source_registry(tmp_path, home)
    (home / "vaults/main/GasCity").mkdir(parents=True)
    calls: list[tuple[str, ...]] = []
    timer_active = True

    def systemctl(*arguments: str) -> subprocess.CompletedProcess[str]:
        nonlocal timer_active
        calls.append(arguments)
        if arguments[:2] == ("stop", "aegis-obsidian-reconcile.timer"):
            timer_active = False
        if arguments[:2] == ("start", "aegis-obsidian-reconcile.timer"):
            timer_active = True
        if arguments[0] == "is-enabled":
            enabled = arguments[1].endswith(".timer")
            return subprocess.CompletedProcess(
                arguments, 0 if enabled else 1, "enabled\n" if enabled else "disabled\n", ""
            )
        if arguments[0] == "is-active":
            active = timer_active if arguments[1].endswith(".timer") else True
            return subprocess.CompletedProcess(
                arguments, 0 if active else 1, "active\n" if active else "inactive\n", ""
            )
        if arguments[0] == "show" and "SubState" in arguments:
            return subprocess.CompletedProcess(arguments, 0, "running\n", "")
        if arguments[0] == "show" and "Result" in arguments:
            return subprocess.CompletedProcess(arguments, 0, "success\n", "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(obsidian_install, "_run_systemctl", systemctl)
    monkeypatch.setattr(
        obsidian_install,
        "_wait_for_service_inactive",
        lambda _service: (_ for _ in ()).throw(RuntimeError("service still active")),
    )

    with pytest.raises(RuntimeError, match="service still active"):
        obsidian_install.install(
            home=home,
            source_root=Path(__file__).parents[2],
            registry_source=registry,
        )

    assert ("stop", "aegis-obsidian-reconcile.service") not in calls
    assert ("start", "aegis-obsidian-reconcile.timer") in calls
    assert not (home / ".local/bin/aegis-obsidian-reconcile").exists()


@pytest.mark.parametrize(
    ("baseline_result", "expected_service_starts", "expected_reset_count"),
    [("success", 2, 2), ("failed", 1, 1)],
)
@pytest.mark.parametrize("prior_exports", [False, True])
def test_install_failure_rolls_back_new_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    baseline_result: str,
    expected_service_starts: int,
    expected_reset_count: int,
    prior_exports: bool,
) -> None:
    home = tmp_path / "home"
    registry = _source_registry(tmp_path, home)
    output = home / "vaults/main/GasCity/Aegis"
    output.mkdir(parents=True)
    (output / "before.md").write_text("before\n", encoding="utf-8")
    state = home / ".local/state/aegis/obsidian-reconciler"
    state.mkdir(parents=True)
    state.chmod(0o700)
    (state / "before.json").write_text('{"before":true}\n', encoding="utf-8")
    exports = home / ".local/state/aegis/obsidian-exports"
    if prior_exports:
        exports.mkdir(mode=0o700)
        (exports / "before.json").write_text('{"before":true}\n')
    systemctl_calls: list[tuple[str, ...]] = []
    service_starts = 0
    restoring_timer = False
    timer_substate_reads = 0

    def systemctl(*arguments: str) -> subprocess.CompletedProcess[str]:
        nonlocal restoring_timer, service_starts, timer_substate_reads
        systemctl_calls.append(arguments)
        if arguments[:2] == ("start", "aegis-obsidian-reconcile.service"):
            service_starts += 1
            if exports.is_dir():
                (exports / "before.json").write_text('{"mutated":true}\n')
            (output / "before.md").write_text("mutated\n", encoding="utf-8")
            (output / "transient.md").write_text("transient\n", encoding="utf-8")
            (state / "before.json").write_text('{"before":false}\n', encoding="utf-8")
            (state / "transient.json").write_text("{}\n", encoding="utf-8")
            if service_starts == 1:
                return subprocess.CompletedProcess(arguments, 1, "", "simulated refusal")
            return subprocess.CompletedProcess(arguments, 0, "", "")
        if arguments[:2] == ("start", "aegis-obsidian-reconcile.timer"):
            restoring_timer = True
            (output / "before.md").write_text("catch-up\n", encoding="utf-8")
            (output / "catch-up.md").write_text("catch-up\n", encoding="utf-8")
            (state / "before.json").write_text('{"catch-up":true}\n', encoding="utf-8")
            (state / "catch-up.json").write_text("{}\n", encoding="utf-8")
            return subprocess.CompletedProcess(arguments, 0, "", "")
        if arguments[0] == "is-enabled":
            enabled = arguments[1] == "aegis-obsidian-reconcile.timer"
            return subprocess.CompletedProcess(
                arguments, 0 if enabled else 1, "enabled\n" if enabled else "disabled\n", ""
            )
        if arguments[0] == "is-active":
            active = arguments[1] == "aegis-obsidian-reconcile.timer" or (
                arguments[1] == "aegis-obsidian-reconcile.service"
                and restoring_timer
                and timer_substate_reads <= 1
            )
            return subprocess.CompletedProcess(
                arguments, 0 if active else 1, "active\n" if active else "inactive\n", ""
            )
        if arguments[0] == "show" and "SubState" in arguments:
            if arguments[1] == "aegis-obsidian-reconcile.timer":
                if restoring_timer:
                    timer_substate_reads += 1
                    value = "elapsed\n" if timer_substate_reads == 1 else "waiting\n"
                else:
                    value = "waiting\n"
            else:
                value = (
                    "running\n"
                    if restoring_timer and timer_substate_reads <= 1
                    else "dead\n"
                )
            return subprocess.CompletedProcess(arguments, 0, value, "")
        if arguments[0] == "show" and "Result" in arguments:
            return subprocess.CompletedProcess(arguments, 0, f"{baseline_result}\n", "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(obsidian_install, "_run_systemctl", systemctl)
    monkeypatch.setattr(obsidian_install.time, "sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="initial reconciliation failed"):
        obsidian_install.install(
            home=home,
            source_root=Path(__file__).parents[2],
            registry_source=registry,
        )

    assert not (home / ".local/bin/aegis-obsidian-reconcile").exists()
    assert not (home / ".config/aegis/obsidian-projects.json").exists()
    assert not (home / ".config/systemd/user/aegis-obsidian-reconcile.service").exists()
    assert not (home / ".config/systemd/user/aegis-obsidian-export.service").exists()
    if prior_exports:
        assert (exports / "before.json").read_text() == '{"before":true}\n'
    else:
        assert not exports.exists()
    assert not (home / ".local/state/aegis/obsidian-reconciler/install-manifest.json").exists()
    assert (state / "before.json").read_text(encoding="utf-8") == '{"before":true}\n'
    assert not (state / "transient.json").exists()
    assert (output / "before.md").read_text(encoding="utf-8") == "before\n"
    assert not (output / "transient.md").exists()
    assert not (output / "catch-up.md").exists()
    assert not (state / "catch-up.json").exists()
    assert systemctl_calls.count(
        ("reset-failed", "aegis-obsidian-reconcile.service")
    ) == expected_reset_count
    timer_restore_index = max(
        index
        for index, call in enumerate(systemctl_calls)
        if call == ("start", "aegis-obsidian-reconcile.timer")
    )
    if expected_reset_count == 2:
        reset_restore_index = max(
            index
            for index, call in enumerate(systemctl_calls)
            if call == ("reset-failed", "aegis-obsidian-reconcile.service")
        )
        assert timer_restore_index < reset_restore_index
    assert service_starts == expected_service_starts
    assert timer_substate_reads >= 2


def test_install_refuses_missing_output_parent_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    registry = _source_registry(tmp_path, home)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        obsidian_install,
        "_run_systemctl",
        lambda *arguments: (
            calls.append(arguments) or subprocess.CompletedProcess(arguments, 0, "", "")
        ),
    )

    with pytest.raises(RuntimeError, match="output parent is missing or unsafe"):
        obsidian_install.install(
            home=home,
            source_root=Path(__file__).parents[2],
            registry_source=registry,
        )

    assert calls == []
    assert not (home / ".local/bin/aegis-obsidian-reconcile").exists()
    assert not (home / ".local/state/aegis/obsidian-reconciler").exists()


def test_install_creates_only_declared_parent_under_managed_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    managed_root = home / "vaults" / "main" / "GasCity"
    managed_root.mkdir(parents=True)
    registry = _source_registry(tmp_path, home)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["managed_output_root"] = str(managed_root)
    payload["projects"][0]["output_dir"] = str(managed_root / "gas-city" / "Aegis")
    registry.write_text(json.dumps(payload), encoding="utf-8")
    timer_active = True

    def systemctl(*arguments: str) -> subprocess.CompletedProcess[str]:
        nonlocal timer_active
        if arguments[:2] == ("stop", "aegis-obsidian-reconcile.timer"):
            timer_active = False
        if arguments[:2] == ("start", "aegis-obsidian-reconcile.timer"):
            timer_active = True
        if arguments[0] == "is-enabled":
            enabled = arguments[1].endswith(".timer")
            return subprocess.CompletedProcess(
                arguments, 0 if enabled else 1, "enabled\n" if enabled else "disabled\n", ""
            )
        if arguments[0] == "is-active":
            active = timer_active if arguments[1].endswith(".timer") else False
            return subprocess.CompletedProcess(
                arguments, 0 if active else 1, "active\n" if active else "inactive\n", ""
            )
        if arguments[0] == "show" and "SubState" in arguments:
            value = "waiting\n" if arguments[1].endswith(".timer") and timer_active else "dead\n"
            return subprocess.CompletedProcess(arguments, 0, value, "")
        if arguments[0] == "show" and "Result" in arguments:
            return subprocess.CompletedProcess(arguments, 0, "success\n", "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(obsidian_install, "_run_systemctl", systemctl)
    monkeypatch.setattr(
        obsidian_install.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, '{"ok":true}\n', ""),
    )

    result = obsidian_install.install(
        home=home,
        source_root=Path(__file__).parents[2],
        registry_source=registry,
    )

    assert result["ok"] is True
    assert (managed_root / "gas-city").is_dir()


def test_install_removes_new_empty_managed_parent_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    managed_root = home / "vaults" / "main" / "GasCity"
    managed_root.mkdir(parents=True)
    registry = _source_registry(tmp_path, home)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["managed_output_root"] = str(managed_root)
    payload["projects"][0]["output_dir"] = str(managed_root / "gas-city" / "Aegis")
    registry.write_text(json.dumps(payload), encoding="utf-8")

    def systemctl(*arguments: str) -> subprocess.CompletedProcess[str]:
        if arguments[:2] == ("start", "aegis-obsidian-reconcile.service"):
            return subprocess.CompletedProcess(arguments, 1, "", "simulated refusal")
        if arguments[0] in {"is-enabled", "is-active"}:
            value = "inactive\n" if arguments[0] == "is-active" else "disabled\n"
            return subprocess.CompletedProcess(arguments, 1, value, "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    monkeypatch.setattr(obsidian_install, "_run_systemctl", systemctl)

    with pytest.raises(RuntimeError, match="initial reconciliation failed"):
        obsidian_install.install(
            home=home,
            source_root=Path(__file__).parents[2],
            registry_source=registry,
        )

    assert not (managed_root / "gas-city").exists()
