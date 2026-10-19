from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from aegis_foundation import obsidian_continuity
from aegis_foundation.obsidian_registry import ContinuityDashboardConfig


def _config(tmp_path: Path) -> ContinuityDashboardConfig:
    return ContinuityDashboardConfig(
        python=Path("/usr/bin/python3"),
        entrypoint=tmp_path / "continuity.py",
        workflow_registry=tmp_path / "projects.json",
        signing_policies=tmp_path / "signing-policies.json",
        output_dir=tmp_path / "vault" / "Continuity",
        freshness_sla_seconds=180,
        capture_timeout_seconds=30,
        live_index=None,
    )


def _report(*, ok: bool = False) -> dict[str, object]:
    return {
        "schema": "gas-city-workflow.continuity-report.v1",
        "ok": ok,
        "snapshot_sha256": "a" * 64,
        "registry_sha256": "b" * 64,
        "summary": {
            "counts": {"current": 1, "next": 1, "blocked": 1},
            "finding_count": 1,
        },
        "work": {
            "current": [
                {
                    "id": "rig:gascity:ga-root",
                    "bead_id": "ga-root",
                    "title": "Continuity initiative",
                    "status": "open",
                }
            ],
            "next": [],
            "blocked": [
                {
                    "id": "rig:gascity:ga-child",
                    "bead_id": "ga-child",
                    "title": "Blocked child",
                    "status": "open",
                }
            ],
            "deferred": [],
            "legacy": [],
            "generated": [],
            "orphaned": [],
        },
        "next_actions": [
            {
                "id": "rig:gascity:ga-next",
                "bead_id": "ga-next",
                "title": "Next child",
            }
        ],
        "findings": [
            {
                "code": "obsidian-project-unregistered",
                "project_id": "blog",
                "identity": "blog",
                "severity": "error",
                "surface": "obsidian",
                "bead_id": None,
            }
        ],
        "projects": [],
    }


def test_capture_accepts_operationally_blocked_report_and_constructs_fixed_argv(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    state = tmp_path / "state"
    state.mkdir()
    calls: list[tuple[str, ...]] = []

    def runner(argv: tuple[str, ...], _timeout: int) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        output = Path(argv[argv.index("--output") + 1])
        if "snapshot" in argv:
            output.write_text("{}\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        output.write_text(json.dumps(_report()) + "\n", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 3, b"", b"")

    report = obsidian_continuity.capture_report(
        config,
        installed_registry=tmp_path / "obsidian.json",
        state_dir=state,
        runner=runner,
    )

    assert report["ok"] is False
    assert len(calls) == 2
    assert calls[0][2:5] == ("snapshot", "--offline-beads", "--registry")
    assert "--obsidian-registry" in calls[0]
    assert calls[0][calls[0].index("--obsidian-cycle-status") + 1] == "idle"
    assert calls[1][2:4] == ("audit", "--snapshot")


def test_dashboard_is_deterministic_isolated_and_idempotent(tmp_path: Path) -> None:
    output = tmp_path / "vault" / "Continuity"
    output.parent.mkdir(parents=True)
    unrelated = output.parent / "unrelated.md"
    unrelated.write_text("preserve\n", encoding="utf-8")

    first = obsidian_continuity.build_dashboard(_report(), output)
    before = {
        path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()
    }
    second = obsidian_continuity.build_dashboard(_report(), output)

    assert first["status"] == "built" and first["changed"] is True
    assert second["status"] == "current" and second["changed"] is False
    assert {
        path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()
    } == before
    assert unrelated.read_text(encoding="utf-8") == "preserve\n"
    status = (output / "Status.md").read_text(encoding="utf-8")
    assert all(heading in status for heading in ("## Now", "## Next", "## Blocked", "## Drift"))
    assert obsidian_continuity.gate_dashboard(_report(), output)["ok"] is True


def test_dashboard_refuses_unowned_output_and_detects_drift(tmp_path: Path) -> None:
    output = tmp_path / "vault" / "Continuity"
    output.mkdir(parents=True)
    (output / "foreign.md").write_text("not managed\n", encoding="utf-8")
    with pytest.raises(obsidian_continuity.DashboardError, match="not managed"):
        obsidian_continuity.build_dashboard(_report(), output)

    output.rename(tmp_path / "foreign")
    result = obsidian_continuity.build_dashboard(_report(), output)
    assert result["ok"] is True
    (output / "Status.md").write_text("drift\n", encoding="utf-8")
    assert obsidian_continuity.gate_dashboard(_report(), output)["ok"] is False
