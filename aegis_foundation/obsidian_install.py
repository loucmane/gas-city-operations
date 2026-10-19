"""Deterministic user-level installation assets for Obsidian reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time
from typing import NamedTuple, Sequence
import zipfile

from aegis_foundation.obsidian_registry import Registry, load_registry

RUNTIME_MODULES = (
    "obsidian_exports.py",
    "obsidian_continuity.py",
    "obsidian_reconcile_cli.py",
    "obsidian_reconciler.py",
    "obsidian_registry.py",
    "obsidian_live_index.py",
    "obsidian_ledger_reader.py",
    "obsidian_vault.py",
    "work_authority.py",
)
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


class TreeEntry(NamedTuple):
    kind: str
    mode: int
    content: bytes | None = None


TreeSnapshot = dict[str, TreeEntry] | None


def _zip_info(name: str, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    return info


def build_runtime_bytes(source_root: str | Path) -> bytes:
    root = Path(source_root).resolve()
    package = root / "aegis_foundation"
    files: dict[str, bytes] = {
        "__main__.py": (
            "from aegis_foundation.obsidian_reconcile_cli import main\nraise SystemExit(main())\n"
        ).encode(),
        "aegis_foundation/__init__.py": b'"""Installed Aegis Obsidian runtime."""\n',
    }
    for name in RUNTIME_MODULES:
        source = package / name
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"runtime source is missing or unsafe: {source}")
        files[f"aegis_foundation/{name}"] = source.read_bytes()
    buffer = io.BytesIO()
    buffer.write(b"#!/usr/bin/env python3\n")
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in sorted(files.items()):
            archive.writestr(_zip_info(name), content)
    return buffer.getvalue()


def _unit_quote(value: str | Path) -> str:
    raw = str(value)
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise RuntimeError(f"systemd unit path contains a control character: {raw!r}")
    return '"' + raw.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_assets(
    *,
    home: str | Path,
    registry_path: str | Path,
    registry: Registry | None = None,
) -> dict[str, bytes]:
    resolved_home = Path(home).resolve()
    active_registry = registry or load_registry(registry_path)
    stable_registry_path = Path(registry_path).resolve()
    runtime = resolved_home / ".local" / "bin" / "aegis-obsidian-reconcile"
    state = resolved_home / ".local" / "state" / "aegis" / "obsidian-reconciler"
    exports = active_registry.export_dir or state.with_name("obsidian-exports")
    if exports == state or exports in state.parents or state in exports.parents:
        raise RuntimeError("export_dir must not overlap reconciler state")
    writable = {
        state,
        *(item.output_dir.parent for item in active_registry.projects if item.enabled),
    }
    if active_registry.continuity_dashboard is not None:
        writable.add(active_registry.continuity_dashboard.output_dir.parent)
    write_lines = "\n".join(f"ReadWritePaths={_unit_quote(path)}" for path in sorted(writable))
    service = f"""[Unit]
Description=Reconcile deterministic Aegis evidence into Obsidian
Wants=aegis-obsidian-export.service
After=default.target aegis-obsidian-export.service

[Service]
Type=oneshot
ExecStart={_unit_quote(runtime)} run --registry {_unit_quote(stable_registry_path)} --state-dir {_unit_quote(state)}
Environment={_unit_quote(f"PATH={resolved_home}/gascity/bin:/usr/local/bin:/usr/bin:/bin")}
Environment={_unit_quote(f"GC_HOME={resolved_home}/gascity/home")}
Environment="GIT_OPTIONAL_LOCKS=0"
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadOnlyPaths={_unit_quote(exports)}
{write_lines}
ProtectControlGroups=true
ProtectKernelModules=true
ProtectKernelTunables=true
RestrictSUIDSGID=true
LockPersonality=true
"""
    exporter = f"""[Unit]
Description=Export pinned Bead snapshots for Obsidian
After=default.target

[Service]
Type=oneshot
ExecStart={_unit_quote(runtime)} export --registry {_unit_quote(stable_registry_path)}
Environment={_unit_quote(f"PATH={resolved_home}/gascity/bin:/usr/local/bin:/usr/bin:/bin")}
Environment={_unit_quote(f"GC_HOME={resolved_home}/gascity/home")}
Environment="GIT_OPTIONAL_LOCKS=0"
UMask=0077
NoNewPrivileges=true
"""
    timer = """[Unit]
Description=Keep deterministic Aegis Obsidian projections fresh

[Timer]
OnBootSec=45s
OnActiveSec=60s
OnUnitInactiveSec=60s
RandomizedDelaySec=5s
AccuracySec=1s
Persistent=true
Unit=aegis-obsidian-reconcile.service

[Install]
WantedBy=timers.target
"""
    return {
        "aegis-obsidian-export.service": exporter.encode(),
        "aegis-obsidian-reconcile.service": service.encode(),
        "aegis-obsidian-reconcile.timer": timer.encode(),
    }


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if mode == 0o600 else 0o755)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
    finally:
        temporary.unlink(missing_ok=True)


def _snapshot_tree(root: Path) -> TreeSnapshot:
    if not root.exists() and not root.is_symlink():
        return None
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"managed tree is missing or unsafe: {root}")
    snapshot = {".": TreeEntry("dir", stat.S_IMODE(root.stat().st_mode))}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"managed tree contains a symlink: {path}")
        if path.is_dir():
            snapshot[relative] = TreeEntry("dir", stat.S_IMODE(path.stat().st_mode))
        elif path.is_file():
            snapshot[relative] = TreeEntry(
                "file", stat.S_IMODE(path.stat().st_mode), path.read_bytes()
            )
        else:
            raise RuntimeError(f"managed tree contains a special file: {path}")
    return snapshot


def _remove_managed_tree(root: Path) -> None:
    if not root.exists() and not root.is_symlink():
        return
    _snapshot_tree(root)
    shutil.rmtree(root)


def _restore_tree(root: Path, snapshot: TreeSnapshot) -> None:
    _remove_managed_tree(root)
    if snapshot is None:
        return
    root_entry = snapshot.get(".")
    if root_entry is None or root_entry.kind != "dir":
        raise RuntimeError(f"managed tree snapshot is invalid: {root}")
    root.mkdir(parents=True, mode=root_entry.mode)
    directories = sorted(
        (
            (Path(relative), entry)
            for relative, entry in snapshot.items()
            if relative != "." and entry.kind == "dir"
        ),
        key=lambda item: (len(item[0].parts), item[0].as_posix()),
    )
    for relative, entry in directories:
        path = root / relative
        path.mkdir(mode=entry.mode)
        os.chmod(path, entry.mode)
    for relative, entry in sorted(snapshot.items()):
        if relative == "." or entry.kind == "dir":
            continue
        if entry.kind != "file" or entry.content is None:
            raise RuntimeError(f"managed tree snapshot entry is invalid: {root / relative}")
        _atomic_write(root / relative, entry.content, entry.mode)
    for relative, entry in reversed(directories):
        os.chmod(root / relative, entry.mode)
    os.chmod(root, root_entry.mode)


def _missing_directories(paths: set[Path]) -> list[Path]:
    missing: set[Path] = set()
    for path in paths:
        cursor = path
        while not cursor.exists() and not cursor.is_symlink():
            missing.add(cursor)
            if cursor == cursor.parent:
                raise RuntimeError(f"managed directory has no existing ancestor: {path}")
            cursor = cursor.parent
        if cursor.is_symlink() or not cursor.is_dir():
            raise RuntimeError(f"managed directory ancestor is unsafe: {cursor}")
    return sorted(missing, key=lambda item: (len(item.parts), item.as_posix()), reverse=True)


def _run_systemctl(*arguments: str) -> subprocess.CompletedProcess[str]:
    timeout = 600 if arguments[:2] == ("start", "aegis-obsidian-reconcile.service") else 30
    return subprocess.run(
        ["systemctl", "--user", *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _unit_state(unit: str) -> dict[str, object]:
    enabled = _run_systemctl("is-enabled", unit)
    active = _run_systemctl("is-active", unit)
    substate = _run_systemctl("show", unit, "-p", "SubState", "--value")
    result = _run_systemctl("show", unit, "-p", "Result", "--value")
    return {
        "enabled": enabled.returncode == 0 and enabled.stdout.strip() == "enabled",
        "active": active.returncode == 0 and active.stdout.strip() == "active",
        "enabled_value": enabled.stdout.strip(),
        "active_value": active.stdout.strip(),
        "substate": substate.stdout.strip() if substate.returncode == 0 else "",
        "result": result.stdout.strip() if result.returncode == 0 else "",
    }


def _wait_for_timer_waiting(
    timer: str,
    service: str,
    *,
    timeout_seconds: float = 180,
    poll_seconds: float = 0.25,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    timer_state = _unit_state(timer)
    service_state = _unit_state(service)
    while not (
        timer_state["active"]
        and timer_state["substate"] == "waiting"
        and not service_state["active"]
    ):
        if time.monotonic() >= deadline:
            raise RuntimeError(
                "restored timer did not settle to waiting with an inactive service: "
                f"timer={timer_state} service={service_state}"
            )
        time.sleep(poll_seconds)
        timer_state = _unit_state(timer)
        service_state = _unit_state(service)
    return timer_state


def _wait_for_service_inactive(
    service: str,
    *,
    timeout_seconds: float = 360,
    poll_seconds: float = 0.25,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    state = _unit_state(service)
    while state["active_value"] not in {"inactive", "failed"}:
        if time.monotonic() >= deadline:
            raise RuntimeError(f"reconciler service did not quiesce before snapshot: {state}")
        time.sleep(poll_seconds)
        state = _unit_state(service)
    return state


def _rollback_unit_policy_errors(
    *,
    before_timer: dict[str, object],
    baseline_service: dict[str, object],
    restored_timer: dict[str, object],
    restored_service: dict[str, object],
) -> list[str]:
    """Compare stable scheduler intent, never transient timer/service substates."""

    errors: list[str] = []
    for key in ("enabled", "active"):
        if before_timer.get(key) != restored_timer.get(key):
            errors.append(
                f"timer {key} restore drift: expected={before_timer.get(key)!r} "
                f"observed={restored_timer.get(key)!r}"
            )
    if before_timer.get("active") and restored_timer.get("substate") != "waiting":
        errors.append(
            "timer stable substate restore drift: expected='waiting' "
            f"observed={restored_timer.get('substate')!r}"
        )
    for key in ("enabled", "active", "substate", "result"):
        if baseline_service.get(key) != restored_service.get(key):
            errors.append(
                f"service {key} restore drift: expected={baseline_service.get(key)!r} "
                f"observed={restored_service.get(key)!r}"
            )
    return errors


def _expected_files(
    *,
    home: Path,
    source_root: Path,
    registry_source: Path,
) -> tuple[dict[Path, tuple[bytes, int]], Registry]:
    registry = load_registry(registry_source)
    registry_destination = home / ".config" / "aegis" / "obsidian-projects.json"
    assets = render_assets(
        home=home,
        registry_path=registry_destination,
        registry=registry,
    )
    files: dict[Path, tuple[bytes, int]] = {
        home / ".local/bin/aegis-obsidian-reconcile": (
            build_runtime_bytes(source_root),
            0o755,
        ),
        registry_destination: (registry_source.read_bytes(), 0o600),
    }
    files.update(
        {home / ".config/systemd/user" / name: (content, 0o644) for name, content in assets.items()}
    )
    return files, registry


def _manifest_path(home: Path) -> Path:
    return home / ".local/state/aegis/obsidian-reconciler/install-manifest.json"


def _read_manifest(path: Path) -> dict[str, object] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _verify_previous(
    files: dict[Path, tuple[bytes, int]], manifest: dict[str, object] | None
) -> None:
    declared = manifest.get("files") if isinstance(manifest, dict) else None
    declared_files = declared if isinstance(declared, dict) else {}
    for path, (expected, _mode) in files.items():
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"managed destination is not a regular file: {path}")
        current = _digest(path.read_bytes())
        prior = declared_files.get(path.as_posix())
        if prior is None and current != _digest(expected):
            raise RuntimeError(f"refusing unknown existing installation file: {path}")
        if isinstance(prior, str) and current != prior:
            raise RuntimeError(f"installed file drift: {path}")


def install(
    *,
    home: Path,
    source_root: Path,
    registry_source: Path,
) -> dict[str, object]:
    files, registry = _expected_files(
        home=home,
        source_root=source_root,
        registry_source=registry_source,
    )
    manifest_path = _manifest_path(home)
    previous_manifest = _read_manifest(manifest_path)
    _verify_previous(files, previous_manifest)
    output_dirs = sorted({project.output_dir for project in registry.projects if project.enabled})
    if registry.continuity_dashboard is not None:
        output_dirs.append(registry.continuity_dashboard.output_dir)
        output_dirs = sorted(set(output_dirs))
    output_parents = sorted(
        {project.output_dir.parent for project in registry.projects if project.enabled}
    )
    if registry.continuity_dashboard is not None:
        output_parents.append(registry.continuity_dashboard.output_dir.parent)
        output_parents = sorted(set(output_parents))
    managed_root = registry.managed_output_root
    if managed_root is not None and (managed_root.is_symlink() or not managed_root.is_dir()):
        raise RuntimeError(f"managed Obsidian output root is missing or unsafe: {managed_root}")
    for parent in output_parents:
        if parent.is_dir() and not parent.is_symlink():
            continue
        if parent.exists() or parent.is_symlink():
            raise RuntimeError(f"registered Obsidian output parent is unsafe: {parent}")
        if managed_root is None or parent.parent != managed_root:
            raise RuntimeError(f"registered Obsidian output parent is missing or unsafe: {parent}")
    previous_files = {
        path: (
            path.read_bytes() if path.is_file() and not path.is_symlink() else None,
            stat.S_IMODE(path.stat().st_mode) if path.is_file() and not path.is_symlink() else None,
        )
        for path in files
    }
    timer = "aegis-obsidian-reconcile.timer"
    service = "aegis-obsidian-reconcile.service"
    before_timer = _unit_state(timer)
    before_service = _unit_state(service)
    baseline_service = before_service
    state_dir = manifest_path.parent
    export_dir = registry.export_dir or state_dir.with_name("obsidian-exports")
    exporter = "aegis-obsidian-export.service"
    output_dirs.append(export_dir)
    initially_missing_directories = _missing_directories(
        {state_dir, export_dir, *output_parents, *(path.parent for path in files)}
    )
    state_snapshot: TreeSnapshot = None
    output_snapshots: dict[Path, TreeSnapshot] = {}
    snapshots_captured = False
    try:
        if before_timer["active"]:
            stopped = _run_systemctl("stop", timer)
            if stopped.returncode != 0:
                raise RuntimeError(f"timer stop failed: {stopped.stderr.strip()}")
        baseline_service = _wait_for_service_inactive(service)
        _wait_for_service_inactive(exporter)
        stopped = _run_systemctl("stop", service)
        if stopped.returncode != 0:
            raise RuntimeError(f"service stabilization stop failed: {stopped.stderr.strip()}")
        baseline_service = _wait_for_service_inactive(service)
    except Exception as exc:
        rollback_errors: list[str] = []
        if before_timer["enabled"]:
            enabled = _run_systemctl("enable", timer)
            if enabled.returncode != 0:
                rollback_errors.append(f"timer enable restore failed: {enabled.stderr.strip()}")
        if before_timer["active"]:
            started = _run_systemctl("start", timer)
            if started.returncode != 0:
                rollback_errors.append(f"timer active restore failed: {started.stderr.strip()}")
        restored_timer = _unit_state(timer)
        for key in ("enabled", "active"):
            if before_timer[key] != restored_timer[key]:
                rollback_errors.append(
                    f"timer {key} restore drift: expected={before_timer[key]!r} "
                    f"observed={restored_timer[key]!r}"
                )
        if rollback_errors:
            raise RuntimeError(f"{exc}; rollback failed: {'; '.join(rollback_errors)}") from exc
        raise
    try:
        state_snapshot = _snapshot_tree(state_dir)
        output_snapshots = {path: _snapshot_tree(path) for path in output_dirs}
        snapshots_captured = True
        for parent in output_parents:
            if parent.is_dir() and not parent.is_symlink():
                continue
            parent.mkdir(mode=0o755)
        state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if state_dir.is_symlink() or not state_dir.is_dir():
            raise RuntimeError(f"reconciler state directory is unsafe: {state_dir}")
        os.chmod(state_dir, 0o700)
        export_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if export_dir.is_symlink() or not export_dir.is_dir():
            raise RuntimeError(f"export directory is unsafe: {export_dir}")
        os.chmod(export_dir, 0o700)
        for path, (content, mode) in files.items():
            _atomic_write(path, content, mode)
        reload_result = _run_systemctl("daemon-reload")
        if reload_result.returncode != 0:
            raise RuntimeError(f"systemd user daemon-reload failed: {reload_result.stderr.strip()}")
        enabled = _run_systemctl("enable", timer)
        if enabled.returncode != 0:
            raise RuntimeError(f"timer enable failed: {enabled.stderr.strip()}")
        reset = _run_systemctl("reset-failed", service)
        if reset.returncode != 0:
            raise RuntimeError(f"service reset-failed failed: {reset.stderr.strip()}")
        started = _run_systemctl("start", "aegis-obsidian-reconcile.service")
        if started.returncode != 0:
            raise RuntimeError(f"initial reconciliation failed: {started.stderr.strip()}")
        state = _unit_state(timer)
        if not state["enabled"] or state["active"]:
            raise RuntimeError(f"timer was not held enabled and inactive for validation: {state}")
        runtime_check = subprocess.run(
            [
                str(home / ".local/bin/aegis-obsidian-reconcile"),
                "check",
                "--registry",
                str(home / ".config/aegis/obsidian-projects.json"),
                "--state-dir",
                str(home / ".local/state/aegis/obsidian-reconciler"),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if runtime_check.returncode != 0:
            raise RuntimeError(f"installed reconciler check failed: {runtime_check.stdout.strip()}")
        started = _run_systemctl("start", timer)
        if started.returncode != 0:
            raise RuntimeError(f"timer start failed: {started.stderr.strip()}")
        state = _wait_for_timer_waiting(timer, service)
        settled_service = _unit_state(service)
        if settled_service["result"] != "success":
            raise RuntimeError(
                f"initial reconciliation did not leave a successful service: {settled_service}"
            )
        manifest = {
            "schema_version": "1",
            "registry_digest": registry.digest,
            "files": {
                path.as_posix(): _digest(content) for path, (content, _mode) in files.items()
            },
            "timer": state,
        }
        _atomic_write(
            manifest_path,
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
            0o600,
        )
        return {"ok": True, "status": "installed", **manifest}
    except Exception as exc:
        rollback_errors: list[str] = []
        disabled = _run_systemctl("disable", "--now", timer)
        if disabled.returncode != 0:
            rollback_errors.append(f"timer disable failed: {disabled.stderr.strip()}")
        stopped = _run_systemctl("stop", service)
        if stopped.returncode != 0:
            rollback_errors.append(f"service stop failed: {stopped.stderr.strip()}")
        stopped = _run_systemctl("stop", exporter)
        if stopped.returncode != 0:
            rollback_errors.append(f"exporter stop failed: {stopped.stderr.strip()}")
        for path, (content, mode) in previous_files.items():
            try:
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, content, int(mode or 0o600))
            except OSError as rollback_exc:
                rollback_errors.append(f"file restore failed for {path}: {rollback_exc}")
        reload_result = _run_systemctl("daemon-reload")
        if reload_result.returncode != 0:
            rollback_errors.append(f"systemd daemon-reload failed: {reload_result.stderr.strip()}")
        if snapshots_captured:
            try:
                _restore_tree(state_dir, state_snapshot)
                for path, snapshot in output_snapshots.items():
                    _restore_tree(path, snapshot)
            except (OSError, RuntimeError) as rollback_exc:
                rollback_errors.append(f"managed tree restore failed: {rollback_exc}")
        if before_timer["active"] and baseline_service.get("result") == "success":
            primed = _run_systemctl("start", service)
            if primed.returncode != 0:
                rollback_errors.append(
                    f"timer reference service restore failed: {primed.stderr.strip()}"
                )
            elif snapshots_captured:
                try:
                    _restore_tree(state_dir, state_snapshot)
                    for path, snapshot in output_snapshots.items():
                        _restore_tree(path, snapshot)
                except (OSError, RuntimeError) as rollback_exc:
                    rollback_errors.append(
                        f"post-prime managed tree restore failed: {rollback_exc}"
                    )
        for directory in initially_missing_directories:
            try:
                if not directory.exists() and not directory.is_symlink():
                    continue
                if directory.is_symlink() or not directory.is_dir():
                    raise RuntimeError(f"new managed directory became unsafe: {directory}")
                if any(directory.iterdir()):
                    raise RuntimeError(f"new managed directory is not empty: {directory}")
                directory.rmdir()
            except OSError as rollback_exc:
                rollback_errors.append(
                    f"managed directory restore failed for {directory}: {rollback_exc}"
                )
            except RuntimeError as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        if before_timer["enabled"]:
            enabled = _run_systemctl("enable", timer)
            if enabled.returncode != 0:
                rollback_errors.append(f"timer enable restore failed: {enabled.stderr.strip()}")
        if before_timer["active"]:
            started = _run_systemctl("start", timer)
            if started.returncode != 0:
                rollback_errors.append(f"timer active restore failed: {started.stderr.strip()}")
            else:
                try:
                    _wait_for_timer_waiting(timer, service)
                    if snapshots_captured:
                        _restore_tree(state_dir, state_snapshot)
                        for path, snapshot in output_snapshots.items():
                            _restore_tree(path, snapshot)
                except (OSError, RuntimeError) as rollback_exc:
                    rollback_errors.append(
                        f"timer catch-up restore failed: {rollback_exc}"
                    )
        if baseline_service.get("result") == "success":
            reset = _run_systemctl("reset-failed", service)
            if reset.returncode != 0:
                rollback_errors.append(f"service reset-failed failed: {reset.stderr.strip()}")
        restored_timer = _unit_state(timer)
        restored_service = _unit_state(service)
        rollback_errors.extend(
            _rollback_unit_policy_errors(
                before_timer=before_timer,
                baseline_service=baseline_service,
                restored_timer=restored_timer,
                restored_service=restored_service,
            )
        )
        if rollback_errors:
            raise RuntimeError(f"{exc}; rollback failed: {'; '.join(rollback_errors)}") from exc
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="install-aegis-obsidian-reconciler")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--registry-source")
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--source-root", default=str(Path(__file__).resolve().parent.parent))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    home = Path(args.home).resolve()
    source_root = Path(args.source_root).resolve()
    registry_source = (
        Path(args.registry_source).resolve()
        if args.registry_source
        else home / ".config/aegis/obsidian-projects.json"
    )
    files, registry = _expected_files(
        home=home,
        source_root=source_root,
        registry_source=registry_source,
    )
    expected = {path.as_posix(): _digest(content) for path, (content, _mode) in files.items()}
    if args.plan:
        print(
            json.dumps(
                {
                    "schema_version": "1",
                    "registry_digest": registry.digest,
                    "export_dir": str(registry.export_dir or home / ".local/state/aegis/obsidian-exports"),
                    "expected": expected,
                    "service_transition": [
                        "stop aegis-obsidian-reconcile.timer",
                        "wait for aegis-obsidian-reconcile.service to become inactive",
                        "wait for aegis-obsidian-export.service to become inactive",
                        "systemctl --user daemon-reload",
                        "enable aegis-obsidian-reconcile.timer",
                        "start aegis-obsidian-reconcile.service",
                        "check installed reconciliation while timer remains inactive",
                        "start aegis-obsidian-reconcile.timer",
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.apply:
        try:
            result = install(
                home=home,
                source_root=source_root,
                registry_source=registry_source,
            )
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(json.dumps({"ok": False, "status": "failed", "error": str(exc)}, sort_keys=True))
            return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    manifest = _read_manifest(_manifest_path(home))
    declared = manifest.get("files") if isinstance(manifest, dict) else {}
    problems = []
    export_dir = registry.export_dir or home / ".local/state/aegis/obsidian-exports"
    if (export_dir.is_symlink() or not export_dir.is_dir()
            or stat.S_IMODE(export_dir.stat().st_mode) != 0o700):
        problems.append(f"missing, unsafe or non-private export directory: {export_dir}")
    for raw, digest in expected.items():
        path = Path(raw)
        if not path.is_file() or path.is_symlink():
            problems.append(f"missing or unsafe: {path}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append(f"digest drift: {path}")
        elif not isinstance(declared, dict) or declared.get(raw) != digest:
            problems.append(f"install manifest drift: {path}")
    timer = _unit_state("aegis-obsidian-reconcile.timer")
    if not timer["enabled"] or not timer["active"]:
        problems.append(f"reconciler timer is not enabled and active: {timer}")
    if problems:
        print("\n".join(problems))
        return 1
    print("Aegis Obsidian reconciler installation files match reviewed source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
