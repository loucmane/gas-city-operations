#!/usr/bin/env python3
"""Transactionally install the shared Gas City Operations root policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codex_hook_trust import (  # noqa: E402
    DEFAULT_CODEX,
    HOOK_HASH_PATTERN,
    CodexAppServer,
    _only_blank_line_changes,
    _parse_toml,
    _strip_hook_trust_tables,
    _user_config_version,
)

SCHEMA = "gas-city-workflow.root-policy-install.v1"
PLUGIN_ROOT = SCRIPT_DIR.parent
DEFAULT_POLICY_SOURCE = PLUGIN_ROOT / "config" / "root-policy.json"
DEFAULT_RUNTIME_SOURCE = SCRIPT_DIR / "root_policy.py"
DEFAULT_RUNTIME_DIR = Path.home() / ".local/libexec/gas-city-workflow/root-policy-v1"
DEFAULT_CODEX_HOOKS = Path.home() / ".codex/hooks.json"
DEFAULT_CLAUDE_SETTINGS = Path.home() / ".claude/settings.json"
DEFAULT_CODEX_CONFIG = Path.home() / ".codex/config.toml"
DEFAULT_CLAUDE_CONFIG = Path.home() / ".claude.json"
DEFAULT_EVIDENCE_PARENT = Path.home() / ".local/state/gas-city-workflow/root-policy-installs"
RETIRED_ROOT = "/home/loucmane/codex"
CANONICAL_ROOT = "/home/loucmane/gas-city-ops"
MATCHER = "^(Bash|Edit|Write|MultiEdit|NotebookEdit|apply_patch|mcp__.*)$"
MANAGED_EXECUTABLE_PATTERN = re.compile(r"/gas-city-workflow/root-policy-v[0-9]+/root-policy\Z")


class InstallError(RuntimeError):
    """Raised when a bounded root-policy install cannot be proven safe."""


@dataclass(frozen=True)
class Snapshot:
    path: Path
    existed: bool
    data: bytes | None
    mode: int | None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _json_object(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallError(f"{label} is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise InstallError(f"{label} must contain an object")
    return payload


def _regular_bytes(path: Path, *, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise InstallError(f"{label} must be a regular file: {path}")
    return path.read_bytes()


def hook_registration(command: str) -> dict[str, Any]:
    return {
        "matcher": MATCHER,
        "hooks": [{"type": "command", "command": command}],
    }


def _is_managed_registration(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    hooks = value.get("hooks")
    if not isinstance(hooks, list):
        return False
    for handler in hooks:
        if not isinstance(handler, dict) or not isinstance(handler.get("command"), str):
            continue
        try:
            argv = shlex.split(handler["command"])
        except ValueError:
            continue
        candidates = argv[:2] if argv and argv[0] == "/usr/bin/python3" else argv[:1]
        if (
            any(MANAGED_EXECUTABLE_PATTERN.search(value) for value in candidates)
            and "--hook" in argv[1:]
        ):
            return True
    return False


def render_hooks_config(before: bytes, command: str, *, platform: str) -> bytes:
    """Append one exact user PreToolUse hook while preserving unrelated semantics."""

    if platform not in {"codex", "claude"}:
        raise InstallError(f"unsupported hook platform: {platform}")
    payload = _json_object(before, label=f"{platform} user hook settings")
    hooks = payload.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallError(f"{platform} user hooks must be an object")
    pre = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre, list):
        raise InstallError(f"{platform} PreToolUse hooks must be a list")
    managed = [index for index, value in enumerate(pre) if _is_managed_registration(value)]
    expected = hook_registration(command)
    if len(managed) > 1:
        raise InstallError(f"{platform} contains duplicate managed root-policy hooks")
    if managed:
        if pre[managed[0]] != expected:
            raise InstallError(f"{platform} managed root-policy hook drifted")
    else:
        pre.append(expected)
    return _json_bytes(payload)


def render_codex_config(before: bytes) -> bytes:
    """Set only retired-root trust to untrusted; canonical trust must remain trusted."""

    try:
        parsed_before = tomllib.loads(before.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise InstallError("Codex config is invalid TOML") from exc
    projects = parsed_before.get("projects")
    if not isinstance(projects, dict):
        raise InstallError("Codex config projects table is missing")
    old = projects.get(RETIRED_ROOT)
    new = projects.get(CANONICAL_ROOT)
    if not isinstance(old, dict) or old.get("trust_level") not in {"trusted", "untrusted"}:
        raise InstallError("retired Codex root trust entry is missing or invalid")
    if not isinstance(new, dict) or new.get("trust_level") != "trusted":
        raise InstallError("canonical Codex root must remain trusted")
    if old["trust_level"] == "untrusted":
        return before

    text = before.decode("utf-8")
    header = f"[projects.{json.dumps(RETIRED_ROOT)}]"
    lines = text.splitlines(keepends=True)
    indexes = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == header]
    if len(indexes) != 1:
        raise InstallError("retired Codex project table is missing or ambiguous")
    start = indexes[0] + 1
    end = next(
        (index for index in range(start, len(lines)) if lines[index].lstrip().startswith("[")),
        len(lines),
    )
    trust_pattern = re.compile(
        r'^(?P<indent>\s*)trust_level\s*=\s*"trusted"(?P<tail>\s*)(?P<nl>\r?\n)?$'
    )
    matches = [(index, trust_pattern.fullmatch(lines[index])) for index in range(start, end)]
    matches = [(index, match) for index, match in matches if match is not None]
    if len(matches) != 1:
        raise InstallError("retired Codex trust assignment is missing or ambiguous")
    index, match = matches[0]
    assert match is not None
    lines[index] = (
        f'{match.group("indent")}trust_level = "untrusted"{match.group("tail")}'
        f'{match.group("nl") or ""}'
    )
    after = "".join(lines).encode("utf-8")
    try:
        parsed_after = tomllib.loads(after.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise InstallError("rendered Codex config is invalid TOML") from exc
    expected = json.loads(json.dumps(parsed_before))
    expected["projects"][RETIRED_ROOT]["trust_level"] = "untrusted"
    if parsed_after != expected:
        raise InstallError("Codex config renderer changed unrelated semantics")
    return after


def render_claude_config(before: bytes) -> bytes:
    """Repoint only the top-level Aegis MCP package source to the canonical root."""

    payload = _json_object(before, label="Claude config")
    servers = payload.get("mcpServers")
    aegis = servers.get("aegis") if isinstance(servers, dict) else None
    args = aegis.get("args") if isinstance(aegis, dict) else None
    if not isinstance(args, list) or any(not isinstance(value, str) for value in args):
        raise InstallError("Claude top-level Aegis MCP args are missing or invalid")
    old_count = args.count(RETIRED_ROOT)
    canonical_count = args.count(CANONICAL_ROOT)
    if old_count == 1 and canonical_count == 0:
        args[args.index(RETIRED_ROOT)] = CANONICAL_ROOT
    elif old_count == 0 and canonical_count == 1:
        return before
    else:
        raise InstallError("Claude Aegis MCP source is missing or ambiguous")
    return _json_bytes(payload)


def _snapshot(path: Path, *, allow_missing_parent: bool = False) -> Snapshot:
    if path.exists() or path.is_symlink():
        if not path.is_file() or path.is_symlink():
            raise InstallError(f"managed path is not a regular file: {path}")
        details = path.stat()
        if details.st_uid != os.getuid():
            raise InstallError(f"managed path is not owned by the executing user: {path}")
        return Snapshot(path, True, path.read_bytes(), stat.S_IMODE(details.st_mode))
    parent = path.parent
    if allow_missing_parent and not parent.exists():
        return Snapshot(path, False, None, None)
    if not parent.is_dir() or parent.is_symlink():
        raise InstallError(f"managed parent is missing or unsafe: {parent}")
    if parent.stat().st_uid != os.getuid():
        raise InstallError(f"managed parent is not owned by the executing user: {parent}")
    return Snapshot(path, False, None, None)


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _restore(snapshot: Snapshot) -> None:
    if snapshot.existed:
        assert snapshot.data is not None and snapshot.mode is not None
        _atomic_write(snapshot.path, snapshot.data, snapshot.mode)
    elif snapshot.path.exists():
        snapshot.path.unlink()


def _missing_directories(path: Path) -> list[Path]:
    missing: list[Path] = []
    candidate = path
    while not candidate.exists():
        missing.append(candidate)
        candidate = candidate.parent
    if not candidate.is_dir() or candidate.is_symlink():
        raise InstallError(f"runtime ancestor is unsafe: {candidate}")
    if candidate.stat().st_uid != os.getuid():
        raise InstallError(f"runtime ancestor is not owned by the executing user: {candidate}")
    return list(reversed(missing))


def _managed_hook_from_listing(
    payload: dict[str, Any], hooks_path: Path, command: str, *, trusted: bool
) -> dict[str, str]:
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise InstallError("Codex hooks/list returned an unexpected project set")
    hooks = data[0].get("hooks")
    if not isinstance(hooks, list):
        raise InstallError("Codex hooks/list omitted hooks")
    matches = [
        item
        for item in hooks
        if isinstance(item, dict)
        and item.get("sourcePath") == hooks_path.as_posix()
        and item.get("command") == command
    ]
    if len(matches) != 1:
        raise InstallError("Codex hooks/list did not return exactly one managed user hook")
    hook = matches[0]
    expected = {
        "eventName": "preToolUse",
        "handlerType": "command",
        "command": command,
        "async": False,
        "matcher": MATCHER,
        "sourcePath": hooks_path.as_posix(),
        "enabled": True,
        "isManaged": False,
    }
    if any(hook.get(key) != value for key, value in expected.items()):
        raise InstallError("Codex managed user hook metadata drifted")
    key = hook.get("key")
    current_hash = hook.get("currentHash")
    trust_status = hook.get("trustStatus")
    if not isinstance(key, str) or not key.startswith(f"{hooks_path}:"):
        raise InstallError("Codex managed user hook key is invalid")
    if not isinstance(current_hash, str) or not HOOK_HASH_PATTERN.fullmatch(current_hash):
        raise InstallError("Codex managed user hook hash is invalid")
    if trusted and trust_status != "trusted":
        raise InstallError("Codex managed user hook is not trusted")
    if not trusted and trust_status not in {"untrusted", "modified", "trusted"}:
        raise InstallError("Codex managed user hook trust state is invalid")
    return {"key": key, "current_hash": current_hash, "trust_status": str(trust_status)}


def trust_codex_user_hook(codex_config: Path, hooks_path: Path, command: str) -> dict[str, Any]:
    """Trust only the installed user hook through Codex's supported app-server API."""

    if not DEFAULT_CODEX.is_file():
        raise InstallError(f"managed Codex binary is missing: {DEFAULT_CODEX}")
    before = _regular_bytes(codex_config, label="Codex config")
    with CodexAppServer(DEFAULT_CODEX, codex_config, Path(CANONICAL_ROOT)) as server:
        config = server.request("config/read", {"cwd": CANONICAL_ROOT, "includeLayers": True})
        version = _user_config_version(config, codex_config)
        pre = _managed_hook_from_listing(
            server.request("hooks/list", {"cwds": [CANONICAL_ROOT]}),
            hooks_path,
            command,
            trusted=False,
        )
        write = server.request(
            "config/batchWrite",
            {
                "edits": [
                    {
                        "keyPath": f"hooks.state.{json.dumps(pre['key'])}.trusted_hash",
                        "value": pre["current_hash"],
                        "mergeStrategy": "upsert",
                    }
                ],
                "expectedVersion": version,
                "filePath": codex_config.as_posix(),
                "reloadUserConfig": True,
            },
        )
        if write.get("status") != "ok" or write.get("filePath") != codex_config.as_posix():
            raise InstallError("Codex user-hook trust write failed")
        post = _managed_hook_from_listing(
            server.request("hooks/list", {"cwds": [CANONICAL_ROOT]}),
            hooks_path,
            command,
            trusted=True,
        )
    if (pre["key"], pre["current_hash"]) != (post["key"], post["current_hash"]):
        raise InstallError("Codex user hook identity changed during trust")
    after = _regular_bytes(codex_config, label="Codex config after hook trust")
    before_unmanaged, _ = _strip_hook_trust_tables(before, [pre["key"]])
    after_unmanaged, keys = _strip_hook_trust_tables(after, [pre["key"]])
    if before_unmanaged != after_unmanaged:
        if not _only_blank_line_changes(before_unmanaged, after_unmanaged):
            raise InstallError("Codex hook trust changed unrelated config bytes")
        if _parse_toml(before_unmanaged, label="Codex config before trust") != _parse_toml(
            after_unmanaged, label="Codex config after trust"
        ):
            raise InstallError("Codex hook trust changed unrelated config semantics")
    if keys != {pre["key"]}:
        raise InstallError("Codex hook trust table is missing")
    return {"before": pre, "after": post}


def _verify_hook(runtime: Path, policy: Path, cwd: Path, *, denied: bool) -> None:
    result = subprocess.run(
        ["/usr/bin/python3", str(runtime), "--hook", "--policy", str(policy)],
        cwd=cwd,
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "true"}}),
        check=False,
        capture_output=True,
        text=True,
    )
    expected = 2 if denied else 0
    if result.returncode != expected:
        raise InstallError(
            f"installed root-policy hook returned {result.returncode}, expected {expected}: "
            f"{result.stderr.strip()}"
        )


def _git_observation(root: Path) -> dict[str, str]:
    if not root.is_dir() or root.is_symlink():
        raise InstallError(f"historical root is missing or unsafe: {root}")
    commands = {
        "head": ("rev-parse", "HEAD"),
        "branch": ("branch", "--show-current"),
        "status": ("status", "--porcelain=v2", "--untracked-files=all"),
        "worktrees": ("worktree", "list", "--porcelain"),
        "unstaged_diff": ("diff", "--no-ext-diff", "--binary"),
        "staged_diff": ("diff", "--cached", "--no-ext-diff", "--binary"),
    }
    result: dict[str, str] = {}
    for label, args in commands.items():
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise InstallError(f"could not observe historical Git {label}: {detail}")
        result[label] = _sha256(completed.stdout)
    return result


def install(
    *,
    policy_source: Path = DEFAULT_POLICY_SOURCE,
    runtime_source: Path = DEFAULT_RUNTIME_SOURCE,
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
    codex_hooks: Path = DEFAULT_CODEX_HOOKS,
    claude_settings: Path = DEFAULT_CLAUDE_SETTINGS,
    codex_config: Path = DEFAULT_CODEX_CONFIG,
    claude_config: Path = DEFAULT_CLAUDE_CONFIG,
    evidence_root: Path,
    hook_truster: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply the exact user-level transition with byte-exact rollback."""

    policy_data = _regular_bytes(policy_source, label="root policy source")
    runtime_data = _regular_bytes(runtime_source, label="root policy runtime source")
    runtime_executable = runtime_dir / "root-policy"
    installed_policy = runtime_dir / "root-policy.json"
    command = f"/usr/bin/python3 {runtime_executable} --hook --policy {installed_policy}"
    managed_paths = (
        runtime_executable,
        installed_policy,
        codex_hooks,
        claude_settings,
        codex_config,
        claude_config,
    )
    if runtime_dir.exists() and (not runtime_dir.is_dir() or runtime_dir.is_symlink()):
        raise InstallError("runtime directory is unsafe")
    if runtime_dir.exists() and runtime_dir.stat().st_uid != os.getuid():
        raise InstallError("runtime directory is not owned by the executing user")
    snapshots = {
        path: _snapshot(path, allow_missing_parent=path.parent == runtime_dir)
        for path in managed_paths
    }
    runtime_created_dirs = _missing_directories(runtime_dir)
    runtime_states = (snapshots[runtime_executable], snapshots[installed_policy])
    if any(snapshot.existed for snapshot in runtime_states):
        if not all(snapshot.existed for snapshot in runtime_states):
            raise InstallError("installed root-policy runtime is incomplete")
        expected_runtime = ((runtime_data, 0o755), (policy_data, 0o644))
        for snapshot, (expected_data, expected_mode) in zip(
            runtime_states, expected_runtime, strict=True
        ):
            if snapshot.data != expected_data or snapshot.mode != expected_mode:
                raise InstallError("installed root-policy runtime drifted")
    codex_hooks_before = snapshots[codex_hooks].data or b"{}\n"
    claude_settings_before = snapshots[claude_settings].data or b"{}\n"
    codex_config_before = snapshots[codex_config].data
    claude_config_before = snapshots[claude_config].data
    if codex_config_before is None or claude_config_before is None:
        raise InstallError("Codex and Claude user configuration must already exist")
    rendered = {
        runtime_executable: (runtime_data, 0o755),
        installed_policy: (policy_data, 0o644),
        codex_hooks: (render_hooks_config(codex_hooks_before, command, platform="codex"), 0o600),
        claude_settings: (
            render_hooks_config(claude_settings_before, command, platform="claude"),
            snapshots[claude_settings].mode or 0o600,
        ),
        codex_config: (
            render_codex_config(codex_config_before),
            snapshots[codex_config].mode or 0o600,
        ),
        claude_config: (
            render_claude_config(claude_config_before),
            snapshots[claude_config].mode or 0o600,
        ),
    }
    historical_before = _git_observation(Path(RETIRED_ROOT))
    if evidence_root.exists() or evidence_root.is_symlink():
        raise InstallError(f"evidence root already exists: {evidence_root}")
    evidence_root.mkdir(parents=True, mode=0o700)
    for path, snapshot in snapshots.items():
        backup = evidence_root / (hashlib.sha256(path.as_posix().encode()).hexdigest() + ".before")
        if snapshot.existed:
            assert snapshot.data is not None
            _atomic_write(backup, snapshot.data, 0o600)
    manifest = {
        "schema": SCHEMA,
        "status": "applying",
        "targets": {
            path.as_posix(): {
                "before_sha256": _sha256(snapshot.data) if snapshot.data is not None else None,
                "before_mode": f"{snapshot.mode:04o}" if snapshot.mode is not None else None,
                "after_sha256": _sha256(rendered[path][0]),
                "after_mode": f"{rendered[path][1]:04o}",
            }
            for path, snapshot in snapshots.items()
        },
        "historical_git_before": historical_before,
    }
    _atomic_write(evidence_root / "manifest.json", _json_bytes(manifest), 0o600)
    try:
        for directory in runtime_created_dirs:
            directory.mkdir()
        for path in managed_paths:
            data, mode = rendered[path]
            _atomic_write(path, data, mode)
        for path, (data, mode) in rendered.items():
            if path.read_bytes() != data or stat.S_IMODE(path.stat().st_mode) != mode:
                raise InstallError(f"installed readback mismatch: {path}")
        truster = hook_truster or trust_codex_user_hook
        trust = truster(codex_config, codex_hooks, command)
        _verify_hook(runtime_executable, installed_policy, Path(RETIRED_ROOT), denied=True)
        _verify_hook(runtime_executable, installed_policy, Path(CANONICAL_ROOT), denied=False)
        historical_after = _git_observation(Path(RETIRED_ROOT))
        if historical_after != manifest["historical_git_before"]:
            raise InstallError("historical checkout or worktree inventory changed during install")
        for path in managed_paths:
            installed = path.read_bytes()
            manifest["targets"][path.as_posix()]["installed_sha256"] = _sha256(installed)
            manifest["targets"][path.as_posix()][
                "installed_mode"
            ] = f"{stat.S_IMODE(path.stat().st_mode):04o}"
        manifest["status"] = "pass"
        manifest["hook_trust"] = trust
        manifest["historical_git_after"] = historical_after
        _atomic_write(evidence_root / "result.json", _json_bytes(manifest), 0o600)
        return manifest
    except Exception as exc:
        rollback_errors: list[str] = []
        for path in reversed(managed_paths):
            try:
                _restore(snapshots[path])
            except Exception as rollback_exc:  # noqa: BLE001 - aggregate exact rollback failures.
                rollback_errors.append(f"{path}: {rollback_exc}")
        for directory in reversed(runtime_created_dirs):
            try:
                directory.rmdir()
            except OSError as rollback_exc:
                rollback_errors.append(f"{directory}: {rollback_exc}")
        failure = {
            **manifest,
            "status": "fail",
            "error": str(exc),
            "rollback": "pass" if not rollback_errors else "fail",
            "rollback_errors": rollback_errors,
        }
        _atomic_write(evidence_root / "result.json", _json_bytes(failure), 0o600)
        if rollback_errors:
            raise InstallError(
                f"root-policy install failed ({exc}); rollback failed: {'; '.join(rollback_errors)}"
            ) from exc
        raise InstallError(f"root-policy install failed and rolled back: {exc}") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "apply"))
    parser.add_argument("--evidence-root")
    parser.add_argument("--policy-source", default=str(DEFAULT_POLICY_SOURCE))
    parser.add_argument("--runtime-source", default=str(DEFAULT_RUNTIME_SOURCE))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy = _regular_bytes(Path(args.policy_source), label="root policy source")
        runtime = _regular_bytes(Path(args.runtime_source), label="root policy runtime source")
        if args.mode == "check":
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "ok": True,
                        "policy_sha256": _sha256(policy),
                        "runtime_sha256": _sha256(runtime),
                    },
                    sort_keys=True,
                )
            )
            return 0
        if not args.evidence_root:
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            evidence = DEFAULT_EVIDENCE_PARENT / timestamp
        else:
            evidence = Path(args.evidence_root)
        result = install(
            policy_source=Path(args.policy_source),
            runtime_source=Path(args.runtime_source),
            evidence_root=evidence,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except InstallError as exc:
        print(f"gas-city-root-policy-install: REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
