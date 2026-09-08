"""Shared repo-structure configuration for Codex workflow scripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import tomllib


DEFAULT_REPO_STRUCTURE = {
    "templates_root": "templates",
    "sessions_root": "sessions",
    "plans_root": "plans",
    "plan_state_dir": ".plan_state",
    "taskmaster_root": ".taskmaster",
    "work_tracking_root": "docs/ai/work-tracking",
    "reports_root": "reports",
}


@dataclass(frozen=True)
class RepoStructure:
    repo_root: Path
    templates_root: Path
    sessions_root: Path
    plans_root: Path
    plan_state_dir: Path
    taskmaster_root: Path
    work_tracking_root: Path
    reports_root: Path

    @property
    def current_session_link(self) -> Path:
        return self.sessions_root / "current"

    @property
    def session_state_path(self) -> Path:
        return self.sessions_root / "state.json"

    @property
    def current_plan_link(self) -> Path:
        return self.plans_root / "current"

    @property
    def plan_sync_log(self) -> Path:
        return self.plan_state_dir / "sync.log"

    @property
    def taskmaster_tasks_dir(self) -> Path:
        return self.taskmaster_root / "tasks"

    @property
    def taskmaster_tasks_json(self) -> Path:
        return self.taskmaster_tasks_dir / "tasks.json"

    @property
    def work_tracking_active_root(self) -> Path:
        return self.work_tracking_root / "active"

    @property
    def work_tracking_archive_root(self) -> Path:
        return self.work_tracking_root / "archive"

    @property
    def template_metadata_policy_path(self) -> Path:
        return self.templates_root / "metadata" / "template-metadata-policy.json"

    @property
    def template_monitoring_policy_path(self) -> Path:
        return self.templates_root / "metadata" / "template-monitoring-policy.json"

    @property
    def template_performance_policy_path(self) -> Path:
        return self.templates_root / "metadata" / "template-performance-policy.json"

    @property
    def template_cost_policy_path(self) -> Path:
        return self.templates_root / "metadata" / "template-cost-policy.json"

    @property
    def emergency_response_policy_path(self) -> Path:
        return self.templates_root / "metadata" / "emergency-response-policy.json"

    @property
    def continuation_guard_dir(self) -> Path:
        return self.reports_root / "session-continuation"

    @property
    def drift_report_dir(self) -> Path:
        return self.reports_root / "template-drift"

    @property
    def metrics_report_dir(self) -> Path:
        return self.reports_root / "template-metrics"

    @property
    def monitoring_report_dir(self) -> Path:
        return self.reports_root / "template-monitoring"

    @property
    def phase0_validation_report_dir(self) -> Path:
        return self.reports_root / "phase0-scanner-validation"

    @property
    def performance_report_dir(self) -> Path:
        return self.reports_root / "template-performance"

    @property
    def cost_report_dir(self) -> Path:
        return self.reports_root / "cost-tracking"

    @property
    def migration_health_report_dir(self) -> Path:
        return self.reports_root / "migration-health"

    @property
    def emergency_response_report_dir(self) -> Path:
        return self.reports_root / "emergency-response"


def _load_repo_structure_section(config_path: Path) -> Dict[str, str]:
    if config_path.parent.is_symlink() or config_path.is_symlink():
        raise ValueError("repository layout configuration must not contain symlinks")
    if config_path.parent.exists() and not config_path.parent.is_dir():
        raise ValueError("repository configuration parent must be a directory")
    if not config_path.exists():
        return {}
    if not config_path.is_file():
        raise ValueError("repository layout configuration must be a regular file")
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    section = data.get("repo_structure", {})
    if not isinstance(section, dict):
        raise ValueError("repo_structure must be a table")
    if set(section) - set(DEFAULT_REPO_STRUCTURE):
        raise ValueError("repo_structure contains unknown roots")
    if any(not isinstance(value, str) for value in section.values()):
        raise ValueError("repo_structure roots must be strings")
    return dict(section)


def _resolve_path(repo_root: Path, raw_value: str) -> Path:
    if (not raw_value or Path(raw_value).is_absolute() or "\\" in raw_value
            or any(char in raw_value for char in ("\x00", "\n", "\r"))
            or any(part in {"", ".", "..", ".git"} for part in raw_value.split("/"))):
        raise ValueError("repo_structure roots must be normalized worktree-relative paths")
    path = repo_root
    for part in raw_value.split("/"):
        path = path / part
        if path.is_symlink():
            raise ValueError("repo_structure roots must not contain symlinks")
        if path.exists() and not path.is_dir():
            raise ValueError("repo_structure roots must be directories")
    return path


def load_repo_structure(repo_root: Path) -> RepoStructure:
    repo_root = repo_root.resolve()
    config_path = repo_root / ".codex" / "config.toml"
    overrides = _load_repo_structure_section(config_path)
    values = {**DEFAULT_REPO_STRUCTURE, **overrides}
    return RepoStructure(
        repo_root=repo_root,
        templates_root=_resolve_path(repo_root, values["templates_root"]),
        sessions_root=_resolve_path(repo_root, values["sessions_root"]),
        plans_root=_resolve_path(repo_root, values["plans_root"]),
        plan_state_dir=_resolve_path(repo_root, values["plan_state_dir"]),
        taskmaster_root=_resolve_path(repo_root, values["taskmaster_root"]),
        work_tracking_root=_resolve_path(repo_root, values["work_tracking_root"]),
        reports_root=_resolve_path(repo_root, values["reports_root"]),
    )
