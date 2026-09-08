"""Architecture and compatibility contracts for the modular Aegis gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_ROOT = REPO_ROOT / "aegis_foundation" / "gate"
HOOK_ROOT = GATE_ROOT / "hooks"


def nonblank_lines(path: Path) -> int:
    return sum(bool(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())


def test_adapter_launchers_are_thin_and_policy_free() -> None:
    wrappers = (
        REPO_ROOT / ".claude" / "scripts" / "readiness.sh",
        REPO_ROOT / ".claude" / "scripts" / "gate_lib.py",
    )
    forbidden = (
        "def build_checks",
        "def pretooluse_gate",
        "RAW_DESTRUCTIVE_GIT_RE",
        "RECOVERY_CONTRACT =",
        "TaskmasterState",
    )
    for wrapper in wrappers:
        text = wrapper.read_text(encoding="utf-8")
        assert nonblank_lines(wrapper) <= 80
        assert not any(token in text for token in forbidden)


def test_live_and_packaged_compatibility_launchers_are_identical() -> None:
    for name in ("readiness.sh", "gate_lib.py"):
        assert (REPO_ROOT / ".claude" / "scripts" / name).read_bytes() == (
            REPO_ROOT / "aegis_foundation" / "assets" / ".claude" / "scripts" / name
        ).read_bytes()


def test_modular_gate_inventory_and_size_budget() -> None:
    expected = {
        "contracts.py",
        "coordination.py",
        "coordination_runtime.py",
        "decisions.py",
        "delegation.py",
        "entrypoint.py",
        "evidence.py",
        "hard_policy.py",
        "lifecycle.py",
        "loaders.py",
        "native_permissions.py",
        "orchestrator.py",
        "payloads.py",
        "permission_modes.py",
        "pretool.py",
        "runtime_state.py",
        "shell_policy.py",
        "tracking.py",
    }
    assert {path.name for path in HOOK_ROOT.glob("*.py") if path.name != "__init__.py"} == expected
    for module in HOOK_ROOT.glob("*.py"):
        assert nonblank_lines(module) <= 700, module
    for module in GATE_ROOT.glob("*.py"):
        assert nonblank_lines(module) <= 700, module


def test_public_gate_readiness_command_matches_compatibility_command() -> None:
    legacy = subprocess.run(
        ["bash", ".claude/scripts/readiness.sh", "--quick", "--root", "."],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    canonical = subprocess.run(
        [
            sys.executable,
            "-m",
            "aegis_foundation.cli",
            "gate",
            "readiness",
            "--quick",
            "--target-dir",
            ".",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert canonical.returncode == legacy.returncode
    assert canonical.stdout == legacy.stdout


def test_bead_scaffold_extraction_preserves_public_entrypoint() -> None:
    from aegis_foundation.gate.bead_scaffold import build_bead_source_checks
    from aegis_foundation.gate import workflow

    assert workflow.build_bead_source_checks is build_bead_source_checks
    assert "aegis_foundation.assets" not in (GATE_ROOT / "bead_scaffold.py").read_text()


def test_generic_installer_does_not_opt_consumers_into_orchestrator_permissions(
    tmp_path: Path,
) -> None:
    from scripts import _aegis_installer as installer

    plan = installer.plan_install(
        tmp_path, source_root=REPO_ROOT, primary_agent="claude", agents=["claude"]
    )
    paths = {operation["path"] for operation in plan["operations"]}
    assert ".claude/orchestrator-command-profile.json" not in paths


def test_hook_launcher_fails_closed_when_canonical_runtime_is_unavailable(tmp_path: Path) -> None:
    launcher = tmp_path / "gate_lib.py"
    launcher.write_bytes((REPO_ROOT / ".claude" / "scripts" / "gate_lib.py").read_bytes())

    mutation = subprocess.run(
        [sys.executable, "-S", launcher.as_posix(), "pretooluse"],
        cwd=tmp_path,
        input='{"tool_name":"Bash","tool_input":{"command":"npm test"}}',
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin"},
    )
    passive = subprocess.run(
        [sys.executable, "-S", launcher.as_posix(), "posttooluse"],
        cwd=tmp_path,
        input="{}",
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin"},
    )

    assert mutation.returncode == 2
    assert "canonical hook runtime is unavailable" in mutation.stderr
    assert passive.returncode == 0
