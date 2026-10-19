from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import runpy

import pytest

from aegis_foundation import obsidian_exports as exports
from aegis_foundation.obsidian_install import render_assets
from aegis_foundation.obsidian_reconciler import check_registry, reconcile_registry
from aegis_foundation.obsidian_registry import load_registry

NOW = datetime(2026, 10, 19, 14, tzinfo=timezone.utc)
BEADS = b'[{"id":"fx-123","title":"Fixture","status":"open"}]\n'


@pytest.fixture
def registry(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for args in (
        ["init", "-q"],
        [
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "export_dir": str(tmp_path / "exports"),
                "export_max_age_seconds": 600,
                "projects": [
                    {
                        "id": p,
                        "target_dir": str(root),
                        "output_dir": str(tmp_path / "vault" / p),
                        "bead_export_argv": [
                            "/fixture/gc",
                            "--city",
                            "/fixture/city",
                            "--rig",
                            p,
                            "bd",
                            "list",
                            "--all",
                            "--limit",
                            "0",
                            "--json",
                        ],
                    }
                    for p in ("alpha", "beta")
                ],
            }
        )
    )
    return load_registry(path)


def good_export(argv, timeout, **kwargs):
    return BEADS


def publish(registry):
    return exports.export_registry(registry, bead_exporter=good_export, clock=lambda: NOW)


def test_export_manifest_permissions_and_no_vault_writes(registry):
    assert publish(registry)["ok"]
    assert registry.export_dir.stat().st_mode & 0o777 == 0o700
    for project in registry.projects:
        path = registry.export_dir / f"{project.id}.json"
        assert path.stat().st_mode & 0o777 == 0o600
        value = json.loads(path.read_bytes())
        assert value["manifest"] == {
            "project_id": project.id,
            "rig": project.id,
            "command": list(project.bead_export_argv),
            "completed_at": "2026-10-19T14:00:00Z",
            "beads_sha256": hashlib.sha256(BEADS).hexdigest(),
            "exporter_version": exports.EXPORTER_VERSION,
        }
        assert exports.read_export(registry, project, now=NOW) == BEADS
        assert not project.output_dir.exists()


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "stale",
        "digest",
        "project",
        "rig",
        "command",
        "malformed",
        "deep-json",
        "future",
        "version",
    ],
)
def test_refusal_preserves_last_good_and_other_project_continues(registry, tmp_path, defect):
    publish(registry)
    state = tmp_path / "state"
    first = reconcile_registry(
        registry, state_dir=state, clock=lambda: NOW, event_reader=lambda root: []
    )
    assert first["ok"]
    before = {
        p.relative_to(registry.projects[0].output_dir): p.read_bytes()
        for p in registry.projects[0].output_dir.rglob("*")
        if p.is_file()
    }
    path = registry.export_dir / "alpha.json"
    value = json.loads(path.read_bytes())
    if defect == "missing":
        path.unlink()
    elif defect == "malformed":
        path.write_text("{torn")
    elif defect == "deep-json":
        path.write_text("[" * 2000 + "]" * 2000)
    else:
        field, replacement = {
            "stale": ("completed_at", "2026-10-19T13:49:59Z"),
            "future": ("completed_at", "2026-10-20T14:00:00Z"),
            "digest": ("beads_sha256", "0" * 64),
            "project": ("project_id", "beta"),
            "rig": ("rig", "beta"),
            "command": ("command", ["/fixture/bd"]),
            "version": ("exporter_version", "unknown"),
        }[defect]
        value["manifest"][field] = replacement
        path.write_text(json.dumps(value))
    result = reconcile_registry(
        registry, state_dir=state, clock=lambda: NOW, force=True, event_reader=lambda root: []
    )
    assert [p["ok"] for p in result["projects"]] == [False, True]
    assert before == {
        p.relative_to(registry.projects[0].output_dir): p.read_bytes()
        for p in registry.projects[0].output_dir.rglob("*")
        if p.is_file()
    }


def test_default_reconciler_never_executes_exporter(registry, tmp_path, monkeypatch):
    publish(registry)
    original = subprocess.run
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        assert Path(argv[0]).name not in {"gc", "bd"}
        return original(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    assert reconcile_registry(
        registry, state_dir=tmp_path / "state", clock=lambda: NOW, event_reader=lambda root: []
    )["ok"]
    assert check_registry(
        registry, state_dir=tmp_path / "state", clock=lambda: NOW, event_reader=lambda root: []
    )["ok"]
    assert calls  # The real projection still performs its Git reads.


def test_partial_write_failure_preserves_complete_previous_file(registry, monkeypatch):
    publish(registry)
    path = registry.export_dir / "alpha.json"
    before = path.read_bytes()

    def crash(fd):
        assert path.read_bytes() == before
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(exports.os, "fsync", crash)
    result = publish(registry)
    assert not result["ok"]
    assert path.read_bytes() == before
    assert exports.read_export(registry, registry.projects[0], now=NOW) == BEADS
    assert not list(registry.export_dir.glob(".*.tmp*"))


def test_process_death_during_temp_write_cannot_tear_published_file(registry):
    publish(registry)
    path = registry.export_dir / "alpha.json"
    before = path.read_bytes()
    script = (
        "import os, sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(Path(__file__).parents[2])!r})\n"
        "from aegis_foundation import obsidian_exports as e\n"
        "e.os.fsync = lambda fd: os._exit(73)\n"
        f"e._atomic_export(Path({str(path)!r}), {{'incomplete': True}})\n"
    )
    result = subprocess.run([sys.executable, "-c", script], check=False)
    assert result.returncode == 73
    assert path.read_bytes() == before
    assert exports.read_export(registry, registry.projects[0], now=NOW) == BEADS


@pytest.mark.parametrize(
    "stdout,stderr,code",
    [
        (BEADS, b'gc bd: answering from the rig "wrong" store\n', 0),
        (BEADS, b'gc bd: answering from the rig "alpha" store\nextra\n', 0),
        (BEADS, b'gc bd: answering from the rig "alpha" store\n', 1),
        (b"{}", b'gc bd: answering from the rig "alpha" store\n', 0),
        (b"[][]", b'gc bd: answering from the rig "alpha" store\n', 0),
        (b'[{"id":"a", "id":"b"}]', b'gc bd: answering from the rig "alpha" store\n', 0),
    ],
)
def test_exporter_validates_before_publication(registry, monkeypatch, stdout, stderr, code):
    def run(argv, **kwargs):
        assert argv == registry.projects[0].bead_export_argv
        assert not kwargs.get("shell")
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    monkeypatch.setattr(subprocess, "run", run)
    from dataclasses import replace

    one = replace(registry, projects=registry.projects[:1])
    assert not exports.export_registry(one)["ok"]
    assert "error" in json.loads((registry.export_dir / "alpha.json").read_bytes())


def test_smoke_uses_all_rendered_properties_without_running_systemd(
    registry, tmp_path, monkeypatch
):
    smoke = runpy.run_path(str(Path(__file__).parents[2] / "scripts/obsidian-sandbox-smoke"))
    root = tmp_path / "smoke"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke",
            "--plan",
            "--registry",
            str(registry.path),
            "--runtime",
            str(tmp_path / "runtime"),
            "--project",
            "alpha",
            "--home",
            str(tmp_path),
            "--fixture-root",
            str(root),
        ],
    )

    def forbidden(*args, **kwargs):
        pytest.fail("--plan must never start a process")

    monkeypatch.setattr(subprocess, "run", forbidden)
    assert smoke["main"]() == 0
    commands = json.loads((root / "commands.json").read_text())
    for name, command in zip(("consumer", "exporter"), commands):
        properties = [command[i + 1] for i, word in enumerate(command) if word == "--property"]
        assert properties == smoke["service_properties"]((root / f"{name}.service").read_bytes())
        assert command[0] == "systemd-run"
        assert all(flag in command for flag in ("--user", "--wait", "--pipe"))


def test_smoke_fixture_and_exec_audit_work_with_fake_systemd(registry, tmp_path, monkeypatch):
    """Exercise the smoke machinery; this is explicitly not a namespace proof."""
    from aegis_foundation.obsidian_install import build_runtime_bytes

    smoke = runpy.run_path(str(Path(__file__).parents[2] / "scripts/obsidian-sandbox-smoke"))
    runtime = tmp_path / "runtime"
    runtime.write_bytes(build_runtime_bytes(Path(__file__).parents[2]))
    fake_gc = tmp_path / "gc"
    fake_gc.write_text(
        "#!/usr/bin/python3\nimport sys\n"
        f"sys.stdout.buffer.write({BEADS!r})\n"
        "sys.stderr.write('gc bd: answering from the rig \"alpha\" store\\n')\n"
    )
    fake_gc.chmod(0o755)
    payload = json.loads(registry.path.read_text())
    payload["projects"][0]["bead_export_argv"][0] = str(fake_gc)
    registry.path.write_text(json.dumps(payload))
    root = tmp_path / "smoke-run"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke",
            "--run",
            "--registry",
            str(registry.path),
            "--runtime",
            str(runtime),
            "--project",
            "alpha",
            "--home",
            str(tmp_path),
            "--fixture-root",
            str(root),
        ],
    )
    original = subprocess.run
    systemd_calls = []

    def run(argv, **kwargs):
        if argv[0] != "systemd-run":
            return original(argv, **kwargs)
        systemd_calls.append(argv)
        fixture_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(root / "home"),
            "TMPDIR": str(root),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        for word in argv:
            if word.startswith("--setenv="):
                key, value = word.removeprefix("--setenv=").split("=", 1)
                fixture_env[key] = value
        return original(argv[argv.index("--") + 1 :], env=fixture_env, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    assert smoke["main"]() == 0
    assert len(systemd_calls) == 2
    assert (root / "consumer.stdout").is_file()
    assert len(list((root / "real-exports").glob("*.json"))) == 1


def test_one_failed_export_is_recorded_and_does_not_block_others(registry):
    def exporter(argv, timeout, **kwargs):
        if argv[4] == "alpha":
            raise RuntimeError("fixture failure")
        return BEADS

    result = exports.export_registry(registry, bead_exporter=exporter, clock=lambda: NOW)
    assert [p["ok"] for p in result["projects"]] == [False, True]
    assert "fixture failure" in (registry.export_dir / "alpha.json").read_text()
    with pytest.raises(RuntimeError, match="fixture failure"):
        exports.read_export(registry, registry.projects[0], now=NOW)
    assert exports.read_export(registry, registry.projects[1], now=NOW) == BEADS


def test_exact_split_unit_contract(registry, tmp_path):
    assets = render_assets(home=tmp_path, registry_path=registry.path, registry=registry)
    export = assets["aegis-obsidian-export.service"].decode()
    # Allowlist all service directives: adding any namespace switch fails this test.
    settings = {
        line.split("=", 1)[0] for line in export.split("[Service]\n")[1].splitlines() if "=" in line
    }
    assert settings == {"Type", "ExecStart", "Environment", "UMask", "NoNewPrivileges"}
    assert " export --registry " in export
    assert "UMask=0077" in export and "NoNewPrivileges=true" in export
    assert f'Environment="GC_HOME={tmp_path}/gascity/home"' in export
    assert f'Environment="PATH={tmp_path}/gascity/bin:/usr/local/bin:/usr/bin:/bin"' in export
    assert 'Environment="GIT_OPTIONAL_LOCKS=0"' in export
    reconcile = assets["aegis-obsidian-reconcile.service"].decode()
    assert "Wants=aegis-obsidian-export.service" in reconcile
    assert "After=default.target aegis-obsidian-export.service" in reconcile
    assert "Requires=" not in reconcile
    assert f'ReadOnlyPaths="{registry.export_dir}"' in reconcile
    for option in (
        "PrivateTmp=true",
        "ProtectHome=read-only",
        "ProtectSystem=strict",
        "ProtectControlGroups=true",
        "ProtectKernelModules=true",
        "ProtectKernelTunables=true",
        "RestrictSUIDSGID=true",
        "LockPersonality=true",
    ):
        assert option in reconcile
    assert (
        "Unit=aegis-obsidian-reconcile.service" in assets["aegis-obsidian-reconcile.timer"].decode()
    )
