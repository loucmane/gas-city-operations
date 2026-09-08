"""Tests for repo-structure configuration loading."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import pytest

from tests.meta_workflow_guard.cross_project_fixtures import REPO_SHAPES, write_repo_config


def load_repo_structure_module():
    name = "repo_structure_test_module"
    if name in sys.modules:
        del sys.modules[name]
    path = Path("scripts/_repo_structure.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.loader.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_load_repo_structure_uses_defaults_without_config(tmp_path) -> None:
    module = load_repo_structure_module()
    structure = module.load_repo_structure(tmp_path)

    assert structure.sessions_root == (tmp_path / "sessions").resolve()
    assert structure.current_session_link == (tmp_path / "sessions" / "current").resolve()
    assert structure.work_tracking_active_root == (tmp_path / "docs" / "ai" / "work-tracking" / "active").resolve()
    assert structure.taskmaster_tasks_json == (tmp_path / ".taskmaster" / "tasks" / "tasks.json").resolve()
    assert structure.performance_report_dir == (tmp_path / "reports" / "template-performance").resolve()
    assert structure.cost_report_dir == (tmp_path / "reports" / "cost-tracking").resolve()
    assert structure.migration_health_report_dir == (tmp_path / "reports" / "migration-health").resolve()
    assert structure.emergency_response_report_dir == (tmp_path / "reports" / "emergency-response").resolve()


def test_plugin_and_packaged_layout_resolvers_match_the_shared_source():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts/_repo_structure.py").read_bytes()
    assert (root / "aegis_foundation/assets/scripts/_repo_structure.py").read_bytes() == source
    assert (root / "aegis_foundation/gate/repo_structure.py").read_bytes() == source
    assert (root / "plugins/gas-city-workflow/scripts/_repo_structure.py").read_bytes() == source


def test_load_repo_structure_reads_repo_local_overrides(tmp_path) -> None:
    module = load_repo_structure_module()
    config_dir = tmp_path / ".codex"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        """
[repo_structure]
templates_root = "template-system"
sessions_root = "state/sessions"
plans_root = "state/plans"
plan_state_dir = "state/plan-sync"
taskmaster_root = "ops/taskmaster"
work_tracking_root = "state/work-tracking"
reports_root = "state/reports"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    structure = module.load_repo_structure(tmp_path)

    assert structure.templates_root == (tmp_path / "template-system").resolve()
    assert structure.sessions_root == (tmp_path / "state" / "sessions").resolve()
    assert structure.current_plan_link == (tmp_path / "state" / "plans" / "current").resolve()
    assert structure.taskmaster_tasks_dir == (tmp_path / "ops" / "taskmaster" / "tasks").resolve()
    assert structure.work_tracking_archive_root == (tmp_path / "state" / "work-tracking" / "archive").resolve()
    assert structure.metrics_report_dir == (tmp_path / "state" / "reports" / "template-metrics").resolve()
    assert structure.monitoring_report_dir == (tmp_path / "state" / "reports" / "template-monitoring").resolve()
    assert structure.phase0_validation_report_dir == (
        tmp_path / "state" / "reports" / "phase0-scanner-validation"
    ).resolve()
    assert structure.performance_report_dir == (tmp_path / "state" / "reports" / "template-performance").resolve()
    assert structure.template_monitoring_policy_path == (
        tmp_path / "template-system" / "metadata" / "template-monitoring-policy.json"
    ).resolve()
    assert structure.template_performance_policy_path == (
        tmp_path / "template-system" / "metadata" / "template-performance-policy.json"
    ).resolve()
    assert structure.template_cost_policy_path == (
        tmp_path / "template-system" / "metadata" / "template-cost-policy.json"
    ).resolve()
    assert structure.emergency_response_policy_path == (
        tmp_path / "template-system" / "metadata" / "emergency-response-policy.json"
    ).resolve()
    assert structure.migration_health_report_dir == (
        tmp_path / "state" / "reports" / "migration-health"
    ).resolve()


def test_load_repo_structure_supports_cross_project_repo_shapes(tmp_path) -> None:
    module = load_repo_structure_module()

    for name, shape in REPO_SHAPES.items():
        repo_root = tmp_path / name
        write_repo_config(repo_root, shape)
        structure = module.load_repo_structure(repo_root)

        assert structure.templates_root == (repo_root / shape.roots["templates_root"]).resolve()
        assert structure.sessions_root == (repo_root / shape.roots["sessions_root"]).resolve()
        assert structure.plans_root == (repo_root / shape.roots["plans_root"]).resolve()
        assert structure.plan_state_dir == (repo_root / shape.roots["plan_state_dir"]).resolve()
        assert structure.taskmaster_root == (repo_root / shape.roots["taskmaster_root"]).resolve()
        assert structure.work_tracking_root == (repo_root / shape.roots["work_tracking_root"]).resolve()
        assert structure.reports_root == (repo_root / shape.roots["reports_root"]).resolve()
        assert structure.phase0_validation_report_dir == (
            repo_root / shape.roots["reports_root"] / "phase0-scanner-validation"
        ).resolve()
        assert structure.performance_report_dir == (
            repo_root / shape.roots["reports_root"] / "template-performance"
        ).resolve()
        assert structure.cost_report_dir == (
            repo_root / shape.roots["reports_root"] / "cost-tracking"
        ).resolve()
        assert structure.migration_health_report_dir == (
            repo_root / shape.roots["reports_root"] / "migration-health"
        ).resolve()
        assert structure.emergency_response_report_dir == (
            repo_root / shape.roots["reports_root"] / "emergency-response"
        ).resolve()


@pytest.mark.parametrize("value", ['"../outside"', '"/tmp/outside"', '"."', '"a//b"', '"a/../b"', '".git/objects"', '""', '42', 'true', '["sessions"]'])
def test_evidence_layout_refuses_invalid_or_escaping_roots(tmp_path, value):
    module = load_repo_structure_module()
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/config.toml").write_text(f"[repo_structure]\nsessions_root = {value}\n")
    with pytest.raises(ValueError):
        module.load_repo_structure(tmp_path)


@pytest.mark.parametrize("fault", ["root-link", "config-link", "config-parent-link"])
def test_evidence_layout_refuses_symlink_indirection(tmp_path, fault):
    module = load_repo_structure_module()
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    if fault == "config-parent-link":
        (root / ".codex").symlink_to(outside, target_is_directory=True)
        (outside / "config.toml").write_text('[repo_structure]\nsessions_root = "engdocs/sessions"\n')
    else:
        (root / ".codex").mkdir()
        if fault == "config-link":
            (outside / "config.toml").write_text('[repo_structure]\nsessions_root = "engdocs/sessions"\n')
            (root / ".codex/config.toml").symlink_to(outside / "config.toml")
        else:
            (root / "engdocs").symlink_to(outside, target_is_directory=True)
            (root / ".codex/config.toml").write_text('[repo_structure]\nsessions_root = "engdocs/sessions"\n')
    with pytest.raises(ValueError):
        module.load_repo_structure(root)


@pytest.mark.parametrize("config", ['repo_structure = "sessions"', '[repo_structure]\nsesion_root = "engdocs/sessions"'])
def test_evidence_layout_refuses_malformed_or_unknown_configuration(tmp_path, config):
    module = load_repo_structure_module()
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/config.toml").write_text(config + "\n")
    with pytest.raises(ValueError):
        module.load_repo_structure(tmp_path)
