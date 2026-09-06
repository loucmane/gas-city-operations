"""Aegis Foundation installer core.

This module is intentionally independent of argparse so the future MCP wrapper can call
the same deterministic planning, install, and verify behavior as the CLI.
"""

from __future__ import annotations

import json
import fnmatch
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import hashlib
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

_REPO_ROOT = Path(__file__).resolve().parents[1]
if _REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, _REPO_ROOT.as_posix())

from aegis_foundation import managed_update as _managed_update  # noqa: E402
from aegis_foundation import observation_audit as _observation_audit  # noqa: E402
from aegis_foundation.gate.session_authority import (  # noqa: E402
    SessionAuthorityError,
    assert_no_pending_continuation,
    verify_session_authority,
)
from aegis_foundation.gate.session_transition import serialized_session_writer  # noqa: E402
from aegis_foundation.gate.hooks.contracts import (  # noqa: E402
    CLAUDE_PRETOOLUSE_MATCHER,
    CODEX_PRETOOLUSE_MATCHER,
)
from aegis_foundation.version import (  # noqa: E402
    FOUNDATION_NAME,
    FOUNDATION_VERSION,
    INSTALLER_VERSION,
    SCHEMA_VERSION,
)

PROFILE_GENERIC = "generic"
PRIMARY_AGENT_CHOICES = {"claude", "codex", "gemini", "multi", "none"}
AGENT_CHOICES = {"claude", "codex", "gemini"}
AEGIS_MANIFEST_REL = ".aegis/foundation-manifest.json"
AEGIS_CONTRACT_REL = ".aegis/contract.md"
AEGIS_REPORTS_REL = ".aegis/reports"
AEGIS_STATE_REL = ".aegis/state"
AEGIS_LOCAL_BIN_REL = ".aegis/bin/aegis"
AEGIS_RUNTIME_ENV_REL = ".aegis/runtime.env"
AEGIS_LOCAL_GATE_RUNTIME_ROOT_REL = ".aegis/runtime/python"
AEGIS_BRIEF_REL = ".aegis/brief.json"
AEGIS_CURRENT_WORK_REL = ".aegis/state/current-work.json"
AEGIS_CLIENT_RELOAD_REL = ".aegis/state/client-reload-required.json"
AEGIS_PENDING_TRACKING_REL = ".aegis/state/pending-tracking.json"
AEGIS_PENDING_TRACKING_SAMPLE_LIMIT = 5
AEGIS_PENDING_TRACKING_SAMPLE_TEXT_LIMIT = 240
AEGIS_DEGRADED_EVENTS_REL = ".aegis/state/degraded-events.json"
AEGIS_ENFORCEMENT_REL = ".aegis/state/enforcement.json"
AEGIS_DELIVERY_POLICY_REL = "aegis.delivery-policy.json"
AEGIS_DELIVERY_POLICY_SCHEMA_REL = "schemas/aegis/delivery-policy.schema.json"
AEGIS_GATE_DECISIONS_REL = ".aegis/reports/gate-decisions.jsonl"
AEGIS_LOCAL_TASKS_REL = ".aegis/state/local-tasks.json"
TASKMASTER_TASKS_REL = ".taskmaster/tasks/tasks.json"
AEGIS_PLAN_REPORT_REL = ".aegis/reports/install-plan.json"
AEGIS_INSTALL_REPORT_REL = ".aegis/reports/install-report.json"
AEGIS_VERIFY_REPORT_REL = ".aegis/reports/verification-report.json"
AEGIS_UPDATE_REPORT_REL = ".aegis/reports/update-report.json"
AEGIS_CLOSEOUT_REPORT_REL = ".aegis/reports/closeout-report.json"
AEGIS_REPAIR_REPORT_REL = ".aegis/reports/repair-report.json"
AEGIS_KICKOFF_REPORT_REL = ".aegis/reports/kickoff-report.json"
AEGIS_OBSERVATION_REPORT_REL = ".aegis/reports/observation-report.json"
AEGIS_OBSERVATION_REPORT_DETAIL_REL = ".aegis/reports/observation-report-detail.json"
AEGIS_OBSERVATION_BASELINE_REL = ".aegis/state/observation-baseline.json"
# TM #197 size budgets: guidance payloads carry capped samples + counts-by-prefix with
# truncation markers; full enumerations live in linked artifact files. Detection logic
# is unchanged (the existing !!-ignored runtime mechanism still classifies deltas) —
# this is purely a report-size fix for the 8MB observation-report / 69MB next class.
# Per-repo overrides: brief.json {"observation": {"sample_cap": N, "prefix_cap": N}}.
OBSERVATION_SAMPLE_CAP_DEFAULT = 50
OBSERVATION_PREFIX_CAP_DEFAULT = 20
AEGIS_OBSERVATION_ARTIFACT_ROOT_REL = ".aegis/reports/observations"
AEGIS_RELEASE_CERT_REPORT_REL = "reports/aegis-release-certification/certification-report.json"
AEGIS_UNINSTALL_TRANSIENT_NOTE = (
    "current Claude hook scripts are preserved by default so an already-running Claude "
    "session can finish; restart Claude, then rerun uninstall with --remove-hook-scripts "
    "or delete .claude/scripts after .claude/settings.json is gone"
)
AEGIS_WORKFLOW_TEMPLATE_SOURCE_ROOT = "templates/aegis/workflow"
AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT = ".aegis/templates/workflow"
AEGIS_WORKFLOW_TEMPLATE_NAMES = (
    "session.md",
    "plan.md",
    "tracker.md",
    "findings.md",
    "decisions.md",
    "handoff.md",
    "implementation.md",
    "changelog.md",
)
BEAD_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*-[a-z0-9][a-z0-9-]*(?:\.[1-9][0-9]*)*$")
AEGIS_LOG_SURFACES = {
    "implementation": "IMPLEMENTATION.md",
    "changelog": "CHANGELOG.md",
    "handoff": "HANDOFF.md",
    "findings": "FINDINGS.md",
    "decisions": "DECISIONS.md",
}
AEGIS_DEFAULT_LOG_SURFACES = ("implementation", "changelog", "handoff")
AEGIS_LOG_EVENT_CLASSES = ("scope", "implementation", "verification", "note")
AEGIS_EVENT_DEFAULT_LOG_SURFACES = {
    "scope": ("findings", "decisions", "handoff"),
    "implementation": ("implementation", "changelog", "handoff"),
    "verification": ("implementation", "changelog", "handoff"),
    "note": AEGIS_DEFAULT_LOG_SURFACES,
}
AEGIS_OBSERVATION_FINGERPRINT_MAX_FILES = 512
AEGIS_OBSERVATION_FINGERPRINT_MAX_BYTES = 8 * 1024 * 1024
AEGIS_OBSERVATION_ARTIFACT_DIRS = (".playwright-mcp",)
AEGIS_OBSERVATION_ROOT_SCREENSHOT_PATTERNS = (
    "audit-*.png",
    "*-desktop.png",
    "*-mobile.png",
    "_home_fixed.png",
)
AEGIS_OBSERVATION_RUNTIME_PREFIXES = (
    ".wrangler",
    "worker/.wrangler",
    "worker/node_modules/.mf",
)
AEGIS_PENDING_EVENT_SENTINELS = {"current", "latest"}
AEGIS_PLAN_STATUS_CHOICES = {"pending", "in-progress", "completed", "done", "n/a"}
AEGIS_ENFORCEMENT_MODES = {"strict", "advisory"}
AEGIS_DELIVERY_POLICY_MODES = {"attended", "evidence-gated"}
AEGIS_ROUTINE_AUTHORITY_FIELDS = (
    "allow_taskmaster_transitions",
    "allow_safe_repairs",
    "allow_verified_closeout",
    "allow_commit_push_pr",
    "allow_ci_remediation",
)
AEGIS_CLAUDE_BLOCK_BEGIN = "<!-- AEGIS:BEGIN claude-runtime -->"
AEGIS_CLAUDE_BLOCK_END = "<!-- AEGIS:END claude-runtime -->"
AEGIS_CODEX_BLOCK_BEGIN = "<!-- AEGIS:BEGIN codex-runtime -->"
AEGIS_CODEX_BLOCK_END = "<!-- AEGIS:END codex-runtime -->"
AEGIS_AGENTS_BLOCK_BEGIN = "<!-- AEGIS:BEGIN agents-runtime -->"
AEGIS_AGENTS_BLOCK_END = "<!-- AEGIS:END agents-runtime -->"
AEGIS_MANAGED_ENTRYPOINT_MAX_NONBLANK_LINES = 25

CLAUDE_PRETOOLUSE_COMMAND = "bash $CLAUDE_PROJECT_DIR/.claude/scripts/pretooluse-gate.sh"
CLAUDE_POSTTOOLUSE_COMMAND = "bash $CLAUDE_PROJECT_DIR/.claude/scripts/posttooluse-tracking.sh"
CLAUDE_STOP_TRACKING_COMMAND = "bash $CLAUDE_PROJECT_DIR/.claude/scripts/tracking-stop-gate.sh"
# Capsule PR-1b recorder: async so it can never block or slow a tool call. Shell-form
# command on purpose: live probe (2026-06-10) showed $CLAUDE_PROJECT_DIR is NOT expanded
# in exec-form args on CLI 2.1.170, so the spec section 1.1 exec-form directive fails its
# own payload reality check; async is the load-bearing property.
CLAUDE_LEDGER_RECORD_COMMAND = "bash $CLAUDE_PROJECT_DIR/.claude/scripts/ledger-record.sh"
CLAUDE_SESSION_BRIEF_COMMAND = "bash $CLAUDE_PROJECT_DIR/.claude/scripts/session-brief.sh"
CLAUDE_SESSION_START_MATCHER = "startup|resume|clear|compact"
CLAUDE_REQUIRED_FILES = (
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/scripts/readiness.sh",
    ".claude/scripts/pretooluse-gate.sh",
    ".claude/scripts/posttooluse-tracking.sh",
    ".claude/scripts/tracking-stop-gate.sh",
    ".claude/scripts/bash-command-guard.sh",
    ".claude/scripts/codex-path-guard.sh",
    ".claude/scripts/ledger-record.sh",
    ".claude/scripts/session-brief.sh",
)
CLAUDE_SUPPORT_FILES = (
    ".claude/scripts/gate_lib.py",
    ".claude/scripts/ledger_lib.py",
    ".claude/scripts/brief_lib.py",
    ".claude/scripts/witness_lib.py",
)
CLAUDE_GATE_IDS = (
    "claude.readiness",
    "claude.pretooluse",
    "claude.posttooluse_tracking",
    "claude.stop_tracking",
    "claude.bash_command",
    "claude.protected_path",
)
CODEX_HOOKS_REL = ".codex/hooks.json"
CODEX_HOOK_TRUST_REVIEW_COMMAND = "/hooks"
CODEX_HOOK_TRUST_HASH_SCOPE = "exact_hook_definition"
CODEX_HOOK_TRUST_UNSUPPORTED_REASON = (
    "Codex records trust outside the project against the exact hook-definition hash; "
    "review the generated definitions with /hooks after reconnecting."
)
CODEX_SESSION_START_MATCHER = "startup|resume|clear|compact"
CODEX_HOOK_MATCHER = CODEX_PRETOOLUSE_MATCHER
CODEX_POSTTOOLUSE_MATCHER = CODEX_HOOK_MATCHER
CODEX_SUBAGENT_MATCHER = ".*"
CODEX_HOOK_ROOT = "$(git rev-parse --show-toplevel)"
CODEX_HOOK_COMMAND_PREFIX = f'AEGIS_INVOKING_AGENT=codex "{CODEX_HOOK_ROOT}/.aegis/bin/aegis" hook'
CODEX_SESSION_START_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} sessionstart"
CODEX_SUBAGENT_START_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} subagentstart"
CODEX_SUBAGENT_STOP_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} recordjson"
CODEX_PRETOOLUSE_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} pretooluse"
CODEX_POSTTOOLUSE_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} posttooluse"
CODEX_LEDGER_RECORD_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} record"
CODEX_SESSION_BRIEF_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} sessionstart"
CODEX_STOP_TRACKING_COMMAND = f"{CODEX_HOOK_COMMAND_PREFIX} stop"
CODEX_SHARED_RUNTIME_FILES = (
    ".claude/scripts/readiness.sh",
    ".claude/scripts/pretooluse-gate.sh",
    ".claude/scripts/posttooluse-tracking.sh",
    ".claude/scripts/tracking-stop-gate.sh",
    ".claude/scripts/bash-command-guard.sh",
    ".claude/scripts/codex-path-guard.sh",
    ".claude/scripts/ledger-record.sh",
    ".claude/scripts/session-brief.sh",
    *CLAUDE_SUPPORT_FILES,
)
CODEX_MANAGED_HOOK_COMMANDS = frozenset(
    {
        CODEX_PRETOOLUSE_COMMAND,
        CODEX_POSTTOOLUSE_COMMAND,
        CODEX_LEDGER_RECORD_COMMAND,
        CODEX_SESSION_BRIEF_COMMAND,
        CODEX_STOP_TRACKING_COMMAND,
        CODEX_SESSION_START_COMMAND,
        CODEX_SUBAGENT_START_COMMAND,
        CODEX_SUBAGENT_STOP_COMMAND,
    }
)
CODEX_LEGACY_GIT_ROOT_COMMANDS = frozenset(
    {
        f'AEGIS_INVOKING_AGENT=codex bash "{CODEX_HOOK_ROOT}/.claude/scripts/pretooluse-gate.sh"',
        f'AEGIS_INVOKING_AGENT=codex bash "{CODEX_HOOK_ROOT}/.claude/scripts/posttooluse-tracking.sh"',
        f'AEGIS_INVOKING_AGENT=codex bash "{CODEX_HOOK_ROOT}/.claude/scripts/ledger-record.sh"',
        f'AEGIS_INVOKING_AGENT=codex bash "{CODEX_HOOK_ROOT}/.claude/scripts/session-brief.sh"',
        f'AEGIS_INVOKING_AGENT=codex bash "{CODEX_HOOK_ROOT}/.claude/scripts/tracking-stop-gate.sh"',
        f'"{CODEX_HOOK_ROOT}/.aegis/bin/aegis" hook sessionstart',
        f'"{CODEX_HOOK_ROOT}/.aegis/bin/aegis" hook record',
        f'"{CODEX_HOOK_ROOT}/.aegis/bin/aegis" hook recordjson',
    }
)
CODEX_LEGACY_BASH_HOOK_SCRIPTS = frozenset(
    {
        "pretooluse-gate.sh",
        "posttooluse-tracking.sh",
        "tracking-stop-gate.sh",
        "ledger-record.sh",
        "session-brief.sh",
        "handoff-nudge.sh",
    }
)
CODEX_REQUIRED_FILES = (
    "CODEX.md",
    CODEX_HOOKS_REL,
    *CODEX_SHARED_RUNTIME_FILES,
    "scripts/_aegis_installer.py",
    "scripts/aegis-delivery-policy",
    "scripts/codex-task",
    "scripts/codex-guard",
    "scripts/_repo_structure.py",
    "scripts/template_registry.py",
    "scripts/template_governance.py",
    "scripts/template_versioning.py",
)
CODEX_GATE_IDS = (
    "codex.readiness",
    "codex.pretooluse",
    "codex.posttooluse_tracking",
    "codex.posttooluse_ledger",
    "codex.session_brief",
    "codex.stop_tracking",
    "codex.apply_patch",
    "codex.hook_trust",
    "codex.guard",
    "codex.work_tracking_audit",
    "codex.sessionstart_capture",
    "codex.posttooluse_capture",
    "codex.subagent_start_capture",
    "codex.subagent_stop_capture",
)

CLAUDE_RUNTIME_HOOK_PHASES = {
    ".claude/scripts/readiness.sh": "readiness",
    ".claude/scripts/pretooluse-gate.sh": "pretooluse",
    ".claude/scripts/posttooluse-tracking.sh": "posttooluse",
    ".claude/scripts/tracking-stop-gate.sh": "stop",
    ".claude/scripts/bash-command-guard.sh": "bash",
    ".claude/scripts/codex-path-guard.sh": "path",
    ".claude/scripts/ledger-record.sh": "record",
    ".claude/scripts/session-brief.sh": "sessionstart",
}
SHARED_SCHEMA_FILES = (
    AEGIS_DELIVERY_POLICY_SCHEMA_REL,
    "schemas/aegis/delegation-exceptions.schema.json",
    "schemas/aegis/foundation-manifest.schema.json",
    "schemas/aegis/profile.schema.json",
    "schemas/aegis/install-plan.schema.json",
)


class AegisError(ValueError):
    """Raised for predictable Aegis installer failures."""


Asset = _managed_update.Asset


@dataclass(frozen=True)
class TaskmasterState:
    """Taskmaster task authority state for a target repository."""

    state: str
    source: str
    reason: str = ""
    message: str = ""
    tasks: tuple[Mapping[str, Any], ...] = ()

    @property
    def present(self) -> bool:
        return self.state != "absent"

    @property
    def valid(self) -> bool:
        return self.state == "valid"

    def details(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source": self.source,
            "state": self.state,
            "present": self.present,
            "valid": self.valid,
            "task_count": len(self.tasks) if self.valid else 0,
        }
        if self.reason:
            payload["reason"] = self.reason
        if self.message:
            payload["message"] = self.message
        if self.state == "invalid":
            payload["repair_guidance"] = _taskmaster_repair_guidance()
        return payload


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_target_root(target_dir: str | Path) -> Path:
    path = Path(target_dir).expanduser()
    return path.resolve()


def _repo_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_bytes(source_root: Path, rel_path: str) -> bytes:
    path = source_root / rel_path
    if not path.exists():
        raise AegisError(f"Required source asset is missing: {rel_path}")
    return path.read_bytes()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _dump_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_schema(source_root: Path, name: str) -> dict[str, Any]:
    path = source_root / "schemas" / "aegis" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_with_schema(source_root: Path, schema_name: str, payload: Mapping[str, Any]) -> None:
    schema = _load_schema(source_root, schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(payload)


def _manifest_schema_failure_message(
    source_root: Path, target_root: Path, manifest: Mapping[str, Any], exc: ValidationError
) -> str:
    """Skew-aware manifest_schema failure (TM 215, HP-Coach 2026-06-12 incident).

    A stale CLI/MCP bundle validates with ITS packaged schemas and rejects fields a
    newer installer legitimately wrote (e.g. `runtime`), surfacing as a bare
    jsonschema error that reads like target corruption. When the target's installed
    schema mirror is newer and accepts the manifest, the validator itself is the
    stale party — say so, and name the source root used.
    """

    base = f"{exc.message} [validated with schemas from {Path(source_root).as_posix()}]"
    mirror = Path(target_root) / "schemas" / "aegis" / "foundation-manifest.schema.json"
    try:
        mirror_schema = json.loads(mirror.read_text(encoding="utf-8"))
        if mirror_schema == _load_schema(Path(source_root), "foundation-manifest.schema.json"):
            return base
        Draft202012Validator(mirror_schema, format_checker=FormatChecker()).validate(dict(manifest))
    except ValidationError:
        return base
    except (OSError, ValueError):
        return base
    return (
        f"{exc.message} — validator runtime is STALE: the schemas packaged with this "
        f"Aegis CLI/MCP (source root {Path(source_root).as_posix()}) are older than the "
        "schema mirror installed in the target repo, and the mirror accepts this "
        "manifest. Update or re-register the Aegis runtime (re-run `aegis runtime "
        "update`, or repoint the MCP server at the current source) and re-run verify."
    )


def _enabled_agents(primary_agent: str, agents: Sequence[str] | None) -> tuple[str, ...]:
    if primary_agent not in PRIMARY_AGENT_CHOICES:
        raise AegisError(f"Unsupported primary agent: {primary_agent}")
    requested = tuple(dict.fromkeys(agents or ()))
    unknown = sorted(set(requested) - AGENT_CHOICES)
    if unknown:
        raise AegisError(f"Unsupported enabled agent(s): {', '.join(unknown)}")
    if primary_agent == "none":
        if requested:
            raise AegisError("primary_agent=none cannot be combined with enabled agents")
        return ()
    if not requested:
        raise AegisError("Aegis install requires at least one explicit --agent value")
    if primary_agent == "multi" and len(requested) < 2:
        raise AegisError("primary_agent=multi requires at least two enabled agents")
    if primary_agent in AGENT_CHOICES and primary_agent not in requested:
        raise AegisError(
            f"primary_agent={primary_agent} must also be listed with --agent {primary_agent}"
        )
    return requested


def profile_payload() -> dict[str, Any]:
    """Return the built-in generic profile contract."""

    return {
        "schema_version": SCHEMA_VERSION,
        "name": PROFILE_GENERIC,
        "description": "Generic Aegis install profile for unknown repositories.",
        "default_primary_agent": "claude",
        "supported_agents": ["claude", "codex"],
        "agent_selection_required": True,
        "paths": {
            "manifest": AEGIS_MANIFEST_REL,
            "reports": AEGIS_REPORTS_REL,
            "state": AEGIS_STATE_REL,
            "local_cli": AEGIS_LOCAL_BIN_REL,
        },
        "adapter_requirements": {
            "claude": {
                "entrypoint": "CLAUDE.md",
                "required_files": list(CLAUDE_REQUIRED_FILES),
                "required_hook_registrations": [
                    {
                        "settings_path": ".claude/settings.json",
                        "event": "PreToolUse",
                        "matcher": CLAUDE_PRETOOLUSE_MATCHER,
                        "command": CLAUDE_PRETOOLUSE_COMMAND,
                    },
                    {
                        "settings_path": ".claude/settings.json",
                        "event": "PostToolUse",
                        "matcher": CLAUDE_PRETOOLUSE_MATCHER,
                        "command": CLAUDE_POSTTOOLUSE_COMMAND,
                    },
                    {
                        "settings_path": ".claude/settings.json",
                        "event": "Stop",
                        "command": CLAUDE_STOP_TRACKING_COMMAND,
                    },
                ],
            },
            "codex": {
                "entrypoint": "CODEX.md",
                "required_files": list(CODEX_REQUIRED_FILES),
                "required_hook_registrations": [
                    {
                        "settings_path": CODEX_HOOKS_REL,
                        "event": "PreToolUse",
                        "matcher": CODEX_HOOK_MATCHER,
                        "command": CODEX_PRETOOLUSE_COMMAND,
                    },
                    {
                        "settings_path": CODEX_HOOKS_REL,
                        "event": "PostToolUse",
                        "matcher": CODEX_HOOK_MATCHER,
                        "command": CODEX_POSTTOOLUSE_COMMAND,
                    },
                    {
                        "settings_path": CODEX_HOOKS_REL,
                        "event": "PostToolUse",
                        "matcher": CODEX_HOOK_MATCHER,
                        "command": CODEX_LEDGER_RECORD_COMMAND,
                    },
                    {
                        "settings_path": CODEX_HOOKS_REL,
                        "event": "SessionStart",
                        "matcher": CLAUDE_SESSION_START_MATCHER,
                        "command": CODEX_SESSION_BRIEF_COMMAND,
                    },
                    {
                        "settings_path": CODEX_HOOKS_REL,
                        "event": "Stop",
                        "command": CODEX_STOP_TRACKING_COMMAND,
                    },
                    {
                        "settings_path": CODEX_HOOKS_REL,
                        "event": "SubagentStart",
                        "matcher": CODEX_SUBAGENT_MATCHER,
                        "command": CODEX_SUBAGENT_START_COMMAND,
                    },
                    {
                        "settings_path": CODEX_HOOKS_REL,
                        "event": "SubagentStop",
                        "matcher": CODEX_SUBAGENT_MATCHER,
                        "command": CODEX_SUBAGENT_STOP_COMMAND,
                    },
                ],
            },
        },
        "conditional_gates": {
            "agents.claude.enabled": list(CLAUDE_GATE_IDS),
            "agents.codex.enabled": list(CODEX_GATE_IDS),
        },
        "verification": {
            "required_commands": ["aegis verify --strict", "aegis closeout"],
            "optional_smoke_tests": [
                "cold-session mutation blocked",
                "Aegis-native kickoff reaches READY without Taskmaster or Serena",
                "READY evidence write allowed",
                "aegis log updates session, tracker, event-aware canonical surfaces, and explicit plan evidence",
                "aegis closeout --dry-run reports closeout readiness without mutation",
                "aegis closeout blocks completion until strict verification, plan evidence, and semantic handoff pass",
            ],
        },
    }


def _render_mode_aware_entrypoint(
    title: str,
    *,
    identity_lines: Sequence[str] = (),
) -> bytes:
    text = "\n".join(
        [
            title,
            "",
            "This project uses Aegis Foundation.",
            *identity_lines,
            "",
            "At orientation, inspect enforcement mode once:",
            "`aegis enforce status` (or `./.aegis/bin/aegis enforce status`).",
            "",
            "## Advisory mode",
            "- Work normally: hooks record evidence and would-block decisions passively; no per-mutation logging or pending-event reconciliation is required.",
            "- Use `aegis brief` for current orientation and `aegis witness` before delivery.",
            "- Do not manually drain advisory pending events or run handoff repair/closeout as routine ceremony.",
            "",
            "## Strict mode",
            "- `.aegis/contract.md` is authoritative for readiness, kickoff, logging, verification, and closeout.",
            "- Use `aegis next` to resolve the single sanctioned workflow step.",
            "",
            "## Always",
            "- Use native agent tools for source edits, tests, and Git inspection; use Aegis CLI/MCP only for workflow state.",
            "- Follow the project-declared external work authority. Beads-first projects use the Gas City bead surface and `aegis kickoff --bead`; Taskmaster is historical compatibility unless the project explicitly declares numeric-task authority.",
            "- In a Gas City managed project, delegated work goes through a Bead and reviewed `gc sling`; provider-native Agent/Task/subagent tools are blocked unless an exact canonical-base-reviewed request exception exists.",
            "- Never write `.aegis/` directly.",
            "- If install/update reports a required client reload, restart that client before mutations.",
            "- Missing hooks or unsupported clients are degraded coverage, not successful capture.",
            "",
            "## Continuation",
            "",
            AEGIS_ENTRYPOINT_CONTINUATION_SUMMARY,
            "",
        ]
    )
    return text.encode("utf-8")


def _render_agents_doc(primary_agent: str, enabled_agents: Sequence[str]) -> bytes:
    agents = ", ".join(enabled_agents) if enabled_agents else "none"
    return _render_mode_aware_entrypoint(
        "# Agents",
        identity_lines=(
            f"- Primary agent: `{primary_agent}`",
            f"- Enabled adapters: `{agents}`",
        ),
    )


def _render_contract(primary_agent: str, enabled_agents: Sequence[str]) -> bytes:
    agents = ", ".join(enabled_agents) if enabled_agents else "none"
    text = "\n".join(
        [
            "# Aegis Foundation Contract",
            "",
            "Aegis Foundation is the shared portable runtime for this repository.",
            "",
            "## Agent Setup",
            "",
            f"- Primary agent: `{primary_agent}`",
            f"- Enabled adapters: `{agents}`",
            "",
            "## Access Policy",
            "",
            "- `.aegis/` is readable shared foundation state.",
            "- Direct writes to `.aegis/` are not allowed.",
            "- Mutating foundation operations go through `aegis ...`, the project-local `./.aegis/bin/aegis ...` CLI shim, or `aegis.*` MCP tools.",
            "- Taskmaster and Serena are optional integrations. Aegis-native state is sufficient for READY when they are absent.",
            "",
            "## Control Plane vs Implementation Tools",
            "",
            "- Use Aegis MCP tools, or the project-local Aegis CLI, for Aegis workflow state: init, inspect, plan-install, install, status, next, start, kickoff, log, verify, closeout dry-runs, closeout, and future reconciliation.",
            "- Use native agent tools for normal project implementation: reading files, editing source files, running project tests, and inspecting git status or diffs.",
            "- The installed Aegis runtime, not the MCP session, is responsible for enforcement.",
            "- Installed hooks govern persistent mutations regardless of whether the attempted mutation comes from MCP, Bash, Edit, Write, or another supported tool surface.",
            "- In Gas City managed projects, PreToolUse also blocks provider-native delegation before worker creation or resumption; SubagentStart remains passive lifecycle evidence, not the authorization boundary.",
            "- MCP is the bootstrap and control-plane interface. It is not a replacement for the agent's editor, shell, test runner, or normal implementation workflow.",
            "- Claude Code loads `.claude/settings.json` hooks at session start. If Aegis just created or changed Claude settings/hooks, restart Claude before source edits so enforcement is active.",
            "",
            "## Verification",
            "",
            "- Required gates must pass `aegis verify --strict` before work is declared complete.",
            "- `aegis closeout` is the final completion gate. Do not report task completion until it writes a passing closeout report.",
            "- Missing, non-executable, unconfigured, or failing required gates make verification fail.",
            "- Policy-only gates are documented limitations, not proof of enforcement.",
            "",
            "## Work Kickoff",
            "",
            '- When a Gas City bead is authoritative, use `aegis kickoff --bead <bead-id> --slug <slug> --title "<title>"`; never create or mutate Taskmaster work for the same scope.',
            '- Start local work with `aegis start "<task title>"` only when no external work id exists.',
            "- Use `aegis kickoff --task <id> ...` only for an explicitly historical numeric-task compatibility flow.",
            "- Kickoff creates Aegis-native current work state, session, plan, and work-tracking files.",
            "- `.aegis/state/current-work.json` is the portable authority for READY.",
            "- In beads-first projects, Taskmaster remains a read-only historical input and its MCP mutation surface should not be registered.",
            "- Normal feature work is: confirm readiness and `aegis next`; read the authoritative bead; run bead-native kickoff; mark scope complete with `aegis log --plan-step auto`; make the bead-scoped change with native tools; log pending tracking; run focused verification; run `aegis verify --strict`; preflight and complete closeout; then close the bead through its rig-scoped surface.",
            '- After every meaningful mutation, run `aegis log --pending-id <id> --note "<past-tense note>"` to write S:W:H:E entries to the active session, tracker, and event-aware canonical surfaces.',
            "- `aegis log` updates plan state only when `--plan-step` is supplied. This prevents generic evidence logs from accidentally changing an unrelated plan step.",
            "- The next persistent mutation is blocked until pending S:W:H:E tracking is logged; this is what makes the workflow mechanical rather than advisory.",
            "- Omit `--surface` for event-aware defaults. Scope logs update findings, decisions, and handoff; implementation and verification logs update implementation, changelog, and handoff. Use `--surface` only for targeted repairs.",
            "- `aegis closeout --dry-run --update-handoff` checks closeout gates without writing reports, handoff updates, or current-work state.",
            "- `aegis closeout --update-handoff` may refresh Aegis-owned semantic handoff sections before validation. It preserves the Progress Log.",
            "",
            "## Continuation Contract",
            "",
            "How to interpret a short continuation intent (continue / go / proceed / next / resume). This grants no authority to bypass any gate.",
            "",
            *AEGIS_CONTINUATION_LINES,
            "",
        ]
    )
    return text.encode("utf-8")


def _render_claude_entrypoint() -> bytes:
    return _render_mode_aware_entrypoint("# Claude Runtime Entry")


def _render_codex_continuation_block() -> bytes:
    return _render_mode_aware_entrypoint("## Aegis Runtime")


def _render_claude_settings() -> bytes:
    payload = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "permissions": {
            "allow": [
                "Bash(bash .claude/scripts/readiness.sh:*)",
                "Bash(./.aegis/bin/aegis gate readiness:*)",
                "Bash(bash .claude/scripts/pretooluse-gate.sh:*)",
                "Bash(bash .claude/scripts/posttooluse-tracking.sh:*)",
                "Bash(bash .claude/scripts/tracking-stop-gate.sh:*)",
                "Bash(bash .claude/scripts/codex-path-guard.sh:*)",
                "Bash(bash .claude/scripts/bash-command-guard.sh:*)",
                "Bash(aegis inspect:*)",
                "Bash(aegis init:*)",
                "Bash(aegis status:*)",
                "Bash(aegis next:*)",
                "Bash(aegis start:*)",
                "Bash(aegis mcp register:*)",
                "Bash(aegis kickoff:*)",
                "Bash(aegis log:*)",
                "Bash(aegis verify:*)",
                "Bash(aegis closeout:*)",
                "Bash(./.aegis/bin/aegis inspect:*)",
                "Bash(./.aegis/bin/aegis init:*)",
                "Bash(./.aegis/bin/aegis status:*)",
                "Bash(./.aegis/bin/aegis next:*)",
                "Bash(./.aegis/bin/aegis start:*)",
                "Bash(./.aegis/bin/aegis mcp register:*)",
                "Bash(./.aegis/bin/aegis kickoff:*)",
                "Bash(./.aegis/bin/aegis log:*)",
                "Bash(./.aegis/bin/aegis verify:*)",
                "Bash(./.aegis/bin/aegis closeout:*)",
                "Bash(git status:*)",
                "Bash(git diff:*)",
                "Bash(date:*)",
                "Bash(ls:*)",
                "Bash(cat:*)",
                "Bash(rg:*)",
            ],
            "deny": [
                "Bash(rm -rf:*)",
                "Bash(git push --force:*)",
                "Bash(git push -f:*)",
                "Bash(git reset --hard:*)",
            ],
        },
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": CLAUDE_PRETOOLUSE_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CLAUDE_PRETOOLUSE_COMMAND,
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": CLAUDE_PRETOOLUSE_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CLAUDE_POSTTOOLUSE_COMMAND,
                        }
                    ],
                },
                {
                    "matcher": CLAUDE_PRETOOLUSE_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CLAUDE_LEDGER_RECORD_COMMAND,
                            "async": True,
                        }
                    ],
                },
            ],
            "SessionStart": [
                {
                    "matcher": CLAUDE_SESSION_START_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CLAUDE_SESSION_BRIEF_COMMAND,
                        }
                    ],
                }
            ],
            "PostToolUseFailure": [
                {
                    "matcher": CLAUDE_PRETOOLUSE_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CLAUDE_LEDGER_RECORD_COMMAND,
                            "async": True,
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": CLAUDE_STOP_TRACKING_COMMAND,
                        }
                    ],
                }
            ],
        },
    }
    return _dump_json(payload).encode("utf-8")


def _codex_hooks_payload() -> dict[str, Any]:
    """Return the complete Codex hook registrations owned by Aegis.

    Codex skips asynchronous command handlers, so every handler is synchronous.
    Commands resolve from the Git root because Codex sessions and subagents may run
    from any repository worktree or subdirectory.
    """

    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": CODEX_HOOK_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CODEX_PRETOOLUSE_COMMAND,
                            "timeout": 30,
                            "statusMessage": "Evaluating Aegis policy",
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": CODEX_HOOK_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CODEX_POSTTOOLUSE_COMMAND,
                            "timeout": 30,
                            "statusMessage": "Recording Aegis tracking",
                        },
                        {
                            "type": "command",
                            "command": CODEX_LEDGER_RECORD_COMMAND,
                            "timeout": 30,
                            "statusMessage": "Recording Aegis evidence",
                        },
                    ],
                }
            ],
            "SessionStart": [
                {
                    "matcher": CODEX_SESSION_START_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CODEX_SESSION_BRIEF_COMMAND,
                            "timeout": 30,
                            "statusMessage": "Loading Aegis brief and session evidence",
                        },
                    ],
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": CODEX_STOP_TRACKING_COMMAND,
                            "timeout": 30,
                            "statusMessage": "Checking Aegis completion evidence",
                        }
                    ],
                }
            ],
            "SubagentStart": [
                {
                    "matcher": CODEX_SUBAGENT_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CODEX_SUBAGENT_START_COMMAND,
                            "timeout": 30,
                            "statusMessage": "Recording Aegis subagent start",
                        }
                    ],
                }
            ],
            "SubagentStop": [
                {
                    "matcher": CODEX_SUBAGENT_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": CODEX_SUBAGENT_STOP_COMMAND,
                            "timeout": 30,
                            "statusMessage": "Recording Aegis subagent completion",
                        }
                    ],
                }
            ],
        }
    }


def _render_codex_hooks() -> bytes:
    return _dump_json(_codex_hooks_payload()).encode("utf-8")


def _parse_codex_hooks(content: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    hooks = payload.get("hooks")
    if hooks is not None and not isinstance(hooks, dict):
        return None
    return payload


def _classify_codex_hook_command(command: object) -> str:
    """Classify a hook command without guessing ownership from a substring."""

    if not isinstance(command, str) or not command.strip():
        return "project"
    if command in CODEX_MANAGED_HOOK_COMMANDS:
        return "managed"
    if command in CODEX_LEGACY_GIT_ROOT_COMMANDS:
        return "legacy"
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "aegis-unknown" if "/.claude/scripts/" in command else "project"
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens.pop(0)
    if len(tokens) == 2 and tokens[0] == "bash":
        script = Path(tokens[1])
        if (
            script.is_absolute()
            and script.parent.as_posix().endswith("/.claude/scripts")
            and script.name in CODEX_LEGACY_BASH_HOOK_SCRIPTS
        ):
            return "legacy"
    if len(tokens) == 3 and Path(tokens[0]).name in {"python", "python3"}:
        script = Path(tokens[1])
        if (
            script.is_absolute()
            and script.as_posix().endswith("/.claude/scripts/gate_lib.py")
            and tokens[2]
            in {
                "pretooluse",
                "posttooluse",
                "stop",
                "path",
                "bash",
                "configchange",
                "record",
                "recordjson",
                "posttoolusefailure",
                "sessionstart",
                "sessionend",
                "subagentstart",
            }
        ):
            return "legacy"
    if len(tokens) == 3:
        executable = Path(tokens[0])
        if (
            executable.is_absolute()
            and executable.as_posix().endswith("/.aegis/bin/aegis")
            and tokens[1] == "hook"
            and tokens[2]
            in {
                "pretooluse",
                "posttooluse",
                "stop",
                "path",
                "bash",
                "configchange",
                "readiness",
                "record",
                "recordjson",
                "posttoolusefailure",
                "sessionstart",
                "sessionend",
                "subagentstart",
            }
        ):
            return "legacy"
    if any("/.claude/scripts/" in token or "/.aegis/bin/aegis" in token for token in tokens):
        return "aegis-unknown"
    return "project"


def _codex_hooks_adoptable(content: bytes) -> bool:
    """Allow adoption only when every Aegis-like command has a known shape."""

    payload = _parse_codex_hooks(content)
    if payload is None:
        return False
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return False
    saw_legacy = False
    for groups in hooks.values():
        if not isinstance(groups, list):
            return False
        for group in groups:
            if not isinstance(group, dict):
                return False
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                return False
            for handler in handlers:
                if not isinstance(handler, dict):
                    return False
                classification = _classify_codex_hook_command(handler.get("command"))
                if classification == "aegis-unknown":
                    return False
                saw_legacy = saw_legacy or classification == "legacy"
    return saw_legacy


def _remove_managed_codex_hook_handlers(payload: MutableMapping[str, Any]) -> bool:
    """Remove only exact Aegis-owned handlers, preserving every unrelated hook."""

    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event, entries in list(hooks.items()):
        if not isinstance(entries, list):
            continue
        retained_groups: list[Any] = []
        for group in entries:
            if not isinstance(group, dict):
                retained_groups.append(group)
                continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                retained_groups.append(group)
                continue
            retained_handlers = [
                handler
                for handler in handlers
                if not (
                    isinstance(handler, dict)
                    and _classify_codex_hook_command(handler.get("command"))
                    in {"managed", "legacy"}
                )
            ]
            if len(retained_handlers) == len(handlers):
                retained_groups.append(group)
                continue
            changed = True
            if retained_handlers:
                retained_group = dict(group)
                retained_group["hooks"] = retained_handlers
                retained_groups.append(retained_group)
        if retained_groups:
            hooks[event] = retained_groups
        else:
            hooks.pop(event, None)
    if not hooks:
        payload.pop("hooks", None)
    return changed


def _merge_codex_hooks(existing: bytes, desired: bytes | None = None) -> bytes | None:
    """Structurally merge Aegis handlers without replacing project-owned hooks."""

    payload = _parse_codex_hooks(existing)
    wanted = _parse_codex_hooks(desired or _render_codex_hooks())
    if payload is None or wanted is None:
        return None
    _remove_managed_codex_hook_handlers(payload)
    hooks = payload.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return None
    wanted_hooks = wanted.get("hooks")
    if not isinstance(wanted_hooks, dict):
        return None
    for event, groups in wanted_hooks.items():
        existing_groups = hooks.setdefault(event, [])
        if not isinstance(existing_groups, list) or not isinstance(groups, list):
            return None
        # JSON round-tripping prevents later callers from mutating the canonical
        # desired payload through a shared list/dict reference.
        existing_groups.extend(json.loads(json.dumps(groups)))
    return _dump_json(payload).encode("utf-8")


def _render_local_cli_shim(source_root: Path) -> bytes:
    source = source_root.resolve().as_posix()
    text = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            'SELF="$0"',
            'SELF_RESOLVED="$(cd "$(dirname "$SELF")" && pwd -P)/$(basename "$SELF")"',
            'AEGIS_DIR="$(cd "$(dirname "$SELF_RESOLVED")/.." && pwd -P)"',
            'AEGIS_TARGET_ROOT="$(cd "$AEGIS_DIR/.." && pwd -P)"',
            "export AEGIS_TARGET_ROOT",
            'AEGIS_RUNTIME_ENV="$AEGIS_DIR/runtime.env"',
            'AEGIS_LOCAL_RUNTIME="$AEGIS_DIR/runtime/python"',
            "",
            "aegis_degraded_hook() {",
            '  local phase="$1"',
            '  local marker="$AEGIS_TARGET_ROOT/.aegis/state/hook-bootstrap-$phase.warned"',
            '  mkdir -p "$AEGIS_TARGET_ROOT/.aegis/state" 2>/dev/null || true',
            '  if mkdir "$marker" 2>/dev/null; then',
            '    case "$phase" in',
            "      pretooluse|path|bash|configchange|readiness)",
            '        echo "target-local Aegis hook runtime is unavailable for $phase; refusing mutation" >&2',
            "        ;;",
            "      *)",
            '        echo "target-local Aegis hook runtime is unavailable for $phase; passive evidence capture is degraded" >&2',
            "        ;;",
            "    esac",
            "  fi",
            '  case "$phase" in',
            "    pretooluse|path|bash|configchange|readiness)",
            "      return 2",
            "      ;;",
            "    *)",
            "      return 0",
            "      ;;",
            "  esac",
            "}",
            "",
            "aegis_clear_hook_marker() {",
            '  if [ -n "$AEGIS_HOOK_PHASE" ]; then',
            '    rmdir "$AEGIS_TARGET_ROOT/.aegis/state/hook-bootstrap-$AEGIS_HOOK_PHASE.warned" 2>/dev/null || true',
            "  fi",
            "}",
            "",
            "# Hook dispatch is deliberately target-local. A central source checkout may be",
            "# unavailable or mid-update while hooks are firing in other repositories.",
            'AEGIS_HOOK_PHASE=""',
            'if [ "${1:-}" = "hook" ]; then',
            '  AEGIS_HOOK_PHASE="${2:-}"',
            '  case "$AEGIS_HOOK_PHASE" in',
            "    pretooluse|posttooluse|stop|path|bash|configchange|readiness|record|recordjson|posttoolusefailure|sessionstart|sessionend|subagentstart)",
            "      ;;",
            "    *)",
            '      echo "unsupported Aegis hook phase: ${AEGIS_HOOK_PHASE:-<missing>}" >&2',
            "      exit 2",
            "      ;;",
            "  esac",
            '  if [ -d "$AEGIS_LOCAL_RUNTIME/aegis_foundation/gate" ]; then',
            '    export PYTHONPATH="$AEGIS_LOCAL_RUNTIME${PYTHONPATH:+:$PYTHONPATH}"',
            "  fi",
            '  if [ "$AEGIS_HOOK_PHASE" != "readiness" ]; then',
            '    AEGIS_HOOK_RUNTIME="$AEGIS_TARGET_ROOT/.claude/scripts/gate_lib.py"',
            '    if [ -f "$AEGIS_HOOK_RUNTIME" ]; then',
            "      aegis_clear_hook_marker",
            "      shift 2",
            '      exec python3 -B "$AEGIS_HOOK_RUNTIME" "$AEGIS_HOOK_PHASE" "$@"',
            "    fi",
            '    aegis_degraded_hook "$AEGIS_HOOK_PHASE"',
            "    exit $?",
            "  fi",
            '  if [ -d "$AEGIS_LOCAL_RUNTIME/aegis_foundation/gate" ]; then',
            "    aegis_clear_hook_marker",
            "    shift 2",
            '    exec python3 -B -m aegis_foundation.gate.readiness "$@"',
            "  fi",
            "fi",
            "",
            'if [ "${1:-}" = "gate" ] && [ "${2:-}" = "readiness" ] && [ -d "$AEGIS_LOCAL_RUNTIME/aegis_foundation/gate" ]; then',
            '  export PYTHONPATH="$AEGIS_LOCAL_RUNTIME${PYTHONPATH:+:$PYTHONPATH}"',
            "  shift 2",
            '  exec python3 -B -m aegis_foundation.gate.readiness "$@"',
            "fi",
            "",
            f'AEGIS_SOURCE_FALLBACK="{source}"',
            'if [ -z "${AEGIS_SOURCE_ROOT:-}" ] && [ -f "$AEGIS_RUNTIME_ENV" ]; then',
            '  while IFS="=" read -r key value; do',
            '    case "$key" in',
            "      AEGIS_SOURCE_ROOT|source_root)",
            '        AEGIS_SOURCE_ROOT="$value"',
            "        ;;",
            "    esac",
            '  done < "$AEGIS_RUNTIME_ENV"',
            "fi",
            'if [ -n "${AEGIS_SOURCE_ROOT:-}" ]; then',
            '  AEGIS_SOURCE_FALLBACK="$AEGIS_SOURCE_ROOT"',
            "fi",
            "",
            'if [ -d "$AEGIS_SOURCE_FALLBACK" ]; then',
            '  for AEGIS_PYTHONPATH_CANDIDATE in "$AEGIS_SOURCE_FALLBACK" "$AEGIS_SOURCE_FALLBACK/.." "$AEGIS_SOURCE_FALLBACK/../.."; do',
            "    if PYTHONPATH=\"$AEGIS_PYTHONPATH_CANDIDATE${PYTHONPATH:+:$PYTHONPATH}\" python3 -c 'import aegis_foundation.cli' >/dev/null 2>&1; then",
            '      export PYTHONPATH="$AEGIS_PYTHONPATH_CANDIDATE${PYTHONPATH:+:$PYTHONPATH}"',
            "      aegis_clear_hook_marker",
            '      exec python3 -m aegis_foundation.cli --source-root "$AEGIS_SOURCE_FALLBACK" "$@"',
            "    fi",
            "  done",
            "fi",
            "",
            "if command -v aegis >/dev/null 2>&1; then",
            '  RESOLVED="$(command -v aegis)"',
            '  RESOLVED_ABS="$(cd "$(dirname "$RESOLVED")" && pwd -P)/$(basename "$RESOLVED")"',
            '  if [ "$RESOLVED_ABS" != "$SELF_RESOLVED" ]; then',
            "    aegis_clear_hook_marker",
            '    exec "$RESOLVED" "$@"',
            "  fi",
            "fi",
            "",
            "if python3 -c 'import aegis_foundation.cli' >/dev/null 2>&1; then",
            "  aegis_clear_hook_marker",
            '  exec python3 -m aegis_foundation.cli "$@"',
            "fi",
            "",
            'if [ -n "$AEGIS_HOOK_PHASE" ]; then',
            '  aegis_degraded_hook "$AEGIS_HOOK_PHASE"',
            "  exit $?",
            "fi",
            "",
            'echo "Aegis CLI is unavailable. Install aegis-foundation, add aegis to PATH, or set AEGIS_SOURCE_ROOT." >&2',
            "exit 127",
            "",
        ]
    )
    return text.encode("utf-8")


def _render_runtime_env(source_root: Path, *, updated_at: str | None = None) -> bytes:
    source = source_root.resolve().as_posix()
    lines = [
        "# Aegis runtime pointer. Managed by aegis runtime update.",
        f"AEGIS_SOURCE_ROOT={source}",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _render_claude_runtime_dispatcher(phase: str) -> bytes:
    text = "\n".join(
        [
            "#!/usr/bin/env bash",
            "# Aegis dispatcher hook. Keep this bootstrap stable; runtime fixes live behind .aegis/bin/aegis.",
            "",
            "set -u",
            "",
            'PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"',
            'if [ -z "$PROJECT_DIR" ]; then',
            '  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"',
            "fi",
            'AEGIS_BIN="$PROJECT_DIR/.aegis/bin/aegis"',
            'if [ -x "$AEGIS_BIN" ]; then',
            f'  exec "$AEGIS_BIN" hook {phase} "$@"',
            "fi",
            "",
            'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            'if [ "$PHASE" = "readiness" ]; then',
            '  echo "Aegis runtime dispatcher fallback cannot execute readiness without .aegis/bin/aegis." >&2',
            "  exit 1",
            "fi",
            'exec python3 "$SCRIPT_DIR/gate_lib.py" "$PHASE"',
            "",
        ]
    )
    text = text.replace('"$PHASE"', f'"{phase}"')
    return text.encode("utf-8")


def _managed_asset_build_policy() -> _managed_update.AssetBuildPolicy:
    return _managed_update.AssetBuildPolicy(
        contract_rel=AEGIS_CONTRACT_REL,
        local_bin_rel=AEGIS_LOCAL_BIN_REL,
        runtime_env_rel=AEGIS_RUNTIME_ENV_REL,
        brief_rel=AEGIS_BRIEF_REL,
        shared_schema_files=tuple(SHARED_SCHEMA_FILES),
        workflow_template_source_root=AEGIS_WORKFLOW_TEMPLATE_SOURCE_ROOT,
        workflow_template_target_root=AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
        workflow_template_names=tuple(AEGIS_WORKFLOW_TEMPLATE_NAMES),
        claude_required_files=tuple(CLAUDE_REQUIRED_FILES),
        claude_support_files=tuple(CLAUDE_SUPPORT_FILES),
        claude_runtime_hook_phases=CLAUDE_RUNTIME_HOOK_PHASES,
        codex_required_files=tuple(CODEX_REQUIRED_FILES),
        codex_shared_runtime_files=tuple(CODEX_SHARED_RUNTIME_FILES),
        codex_hooks_rel=CODEX_HOOKS_REL,
    )


def _managed_asset_renderers() -> _managed_update.AssetRenderers:
    return _managed_update.AssetRenderers(
        read_bytes=_read_bytes,
        render_agents_doc=_render_agents_doc,
        render_contract=_render_contract,
        render_local_cli_shim=_render_local_cli_shim,
        render_runtime_env=_render_runtime_env,
        render_default_brief=_render_default_brief,
        render_claude_entrypoint=_render_claude_entrypoint,
        render_claude_settings=_render_claude_settings,
        render_claude_runtime_dispatcher=_render_claude_runtime_dispatcher,
        render_codex_hooks=_render_codex_hooks,
    )


def _asset_from_source(source_root: Path, rel_path: str, *, kind: str = "managed") -> Asset:
    return _managed_update.asset_from_source(
        source_root,
        rel_path,
        read_bytes=_read_bytes,
        kind=kind,
    )


def _asset_from_source_as(
    source_root: Path, source_rel_path: str, target_rel_path: str, *, kind: str = "managed"
) -> Asset:
    return _managed_update.asset_from_source_as(
        source_root,
        source_rel_path,
        target_rel_path,
        read_bytes=_read_bytes,
        kind=kind,
    )


def _render_default_brief() -> bytes:
    """Default `.aegis/brief.json` (capsule PR-1d gate registry, seed-once).

    Pattern VALUES are per-repo configuration shipped via each repo's deployment doc —
    never hardcoded in Aegis, so the generic default ships empty gates.
    """

    payload = {
        "gates": {},
        "source_roots": [],
        "thresholds": {"branch_count": 30, "unignored_file_mb": 5},
        "redact_extra": [],
        "archive_keep": 20,
        "inject": True,
    }
    return _dump_json(payload).encode("utf-8")


def _base_assets(
    source_root: Path, primary_agent: str, enabled_agents: Sequence[str]
) -> list[Asset]:
    return _managed_update.build_base_assets(
        source_root,
        primary_agent,
        enabled_agents,
        policy=_managed_asset_build_policy(),
        renderers=_managed_asset_renderers(),
    )


def _gate_runtime_source_root(source_root: Path) -> Path | None:
    candidates = [source_root]
    if source_root.name == "assets" and source_root.parent.name == "aegis_foundation":
        candidates.append(source_root.parent.parent)
    return next(
        (
            candidate
            for candidate in dict.fromkeys(candidates)
            if (candidate / "aegis_foundation" / "gate").is_dir()
        ),
        None,
    )


def _local_gate_runtime_assets(source_root: Path) -> list[Asset]:
    """Install a self-contained gate runtime for hooks and readiness.

    The full CLI may continue following ``runtime.env`` to a reviewed source
    checkout. Hook authorization cannot depend on that checkout being mounted or
    importable, so the narrowly scoped gate package is copied into each target.
    """

    runtime_source_root = _gate_runtime_source_root(source_root)
    if runtime_source_root is None:
        raise AegisError("canonical Aegis gate runtime is missing from the source package")

    source_paths = [
        "aegis_foundation/__init__.py",
        "aegis_foundation/version.py",
        *(
            path.relative_to(runtime_source_root).as_posix()
            for path in sorted((runtime_source_root / "aegis_foundation" / "gate").rglob("*.py"))
        ),
    ]
    return [
        _asset_from_source_as(
            runtime_source_root,
            source_path,
            f"{AEGIS_LOCAL_GATE_RUNTIME_ROOT_REL}/{source_path}",
            kind="runtime",
        )
        for source_path in source_paths
    ]


def _adapter_assets(
    source_root: Path, primary_agent: str, enabled_agents: Sequence[str]
) -> list[Asset]:
    del primary_agent  # Preserved for compatibility with existing private callers.
    return _managed_update.build_adapter_assets(
        source_root,
        enabled_agents,
        policy=_managed_asset_build_policy(),
        renderers=_managed_asset_renderers(),
    )


def _managed_assets(
    source_root: Path, primary_agent: str, enabled_agents: Sequence[str]
) -> list[Asset]:
    assets = _managed_update.build_managed_assets(
        source_root,
        primary_agent,
        enabled_agents,
        policy=_managed_asset_build_policy(),
        renderers=_managed_asset_renderers(),
    )
    return [*_local_gate_runtime_assets(source_root), *assets]


def _claude_runtime_block(aegis_entrypoint: bytes) -> str:
    entrypoint = aegis_entrypoint.decode("utf-8").strip()
    return "\n".join(
        [
            AEGIS_CLAUDE_BLOCK_BEGIN,
            entrypoint,
            AEGIS_CLAUDE_BLOCK_END,
            "",
        ]
    )


def _managed_runtime_block(
    *,
    begin_marker: str,
    end_marker: str,
    entrypoint: bytes,
) -> str:
    text = entrypoint.decode("utf-8").strip()
    return "\n".join([begin_marker, text, end_marker, ""])


def _merge_managed_entrypoint(
    existing: bytes,
    aegis_entrypoint: bytes,
    *,
    begin_marker: str,
    end_marker: str,
    existing_heading: str,
) -> bytes | None:
    if existing == aegis_entrypoint:
        return aegis_entrypoint
    try:
        existing_text = existing.decode("utf-8")
    except UnicodeDecodeError:
        return None
    block = _managed_runtime_block(
        begin_marker=begin_marker,
        end_marker=end_marker,
        entrypoint=aegis_entrypoint,
    )
    if begin_marker in existing_text and end_marker in existing_text:
        pattern = re.compile(
            rf"{re.escape(begin_marker)}.*?{re.escape(end_marker)}\n?",
            re.DOTALL,
        )
        return pattern.sub(block, existing_text, count=1).encode("utf-8")
    prefix = f"{block}\n---\n\n## {existing_heading}\n\n"
    return f"{prefix}{existing_text}".encode("utf-8")


def _merge_claude_entrypoint(existing: bytes, aegis_entrypoint: bytes) -> bytes | None:
    """Return CLAUDE.md with an Aegis-managed block while preserving project content."""

    return _merge_managed_entrypoint(
        existing,
        aegis_entrypoint,
        begin_marker=AEGIS_CLAUDE_BLOCK_BEGIN,
        end_marker=AEGIS_CLAUDE_BLOCK_END,
        existing_heading="Existing Project Instructions",
    )


def _merge_codex_entrypoint(existing: bytes, aegis_entrypoint: bytes) -> bytes | None:
    """Return CODEX.md with an Aegis-managed block while preserving project content."""

    return _merge_managed_entrypoint(
        existing,
        aegis_entrypoint,
        begin_marker=AEGIS_CODEX_BLOCK_BEGIN,
        end_marker=AEGIS_CODEX_BLOCK_END,
        existing_heading="Existing Codex Instructions",
    )


def _merge_agents_entrypoint(existing: bytes, aegis_entrypoint: bytes) -> bytes | None:
    """Return AGENTS.md with an Aegis-managed block while preserving project content."""

    return _merge_managed_entrypoint(
        existing,
        aegis_entrypoint,
        begin_marker=AEGIS_AGENTS_BLOCK_BEGIN,
        end_marker=AEGIS_AGENTS_BLOCK_END,
        existing_heading="Existing Agent Instructions",
    )


def _strip_managed_entrypoint(
    existing: bytes,
    *,
    begin_marker: str,
    end_marker: str,
    existing_heading: str,
) -> bytes | None:
    """Remove one Aegis-managed block while preserving project-owned content."""

    try:
        existing_text = existing.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if begin_marker not in existing_text or end_marker not in existing_text:
        return existing
    pattern = re.compile(
        rf"{re.escape(begin_marker)}.*?{re.escape(end_marker)}\n?",
        re.DOTALL,
    )
    stripped = pattern.sub("", existing_text, count=1)
    stripped = re.sub(
        rf"^\s*---\s*\n\s*## {re.escape(existing_heading)}\s*\n+",
        "",
        stripped,
        count=1,
    )
    stripped = stripped.lstrip("\n")
    return stripped.encode("utf-8")


def _strip_claude_entrypoint(existing: bytes) -> bytes | None:
    return _strip_managed_entrypoint(
        existing,
        begin_marker=AEGIS_CLAUDE_BLOCK_BEGIN,
        end_marker=AEGIS_CLAUDE_BLOCK_END,
        existing_heading="Existing Project Instructions",
    )


def _strip_codex_entrypoint(existing: bytes) -> bytes | None:
    return _strip_managed_entrypoint(
        existing,
        begin_marker=AEGIS_CODEX_BLOCK_BEGIN,
        end_marker=AEGIS_CODEX_BLOCK_END,
        existing_heading="Existing Codex Instructions",
    )


def _strip_agents_entrypoint(existing: bytes) -> bytes | None:
    return _strip_managed_entrypoint(
        existing,
        begin_marker=AEGIS_AGENTS_BLOCK_BEGIN,
        end_marker=AEGIS_AGENTS_BLOCK_END,
        existing_heading="Existing Agent Instructions",
    )


def _assets_for_target(target_root: Path, assets: Sequence[Asset]) -> list[Asset]:
    """Materialize target-specific assets such as merged Claude entrypoints."""

    return _managed_update.materialize_assets_for_target(
        target_root,
        assets,
        manifest_rel=AEGIS_MANIFEST_REL,
        codex_hooks_rel=CODEX_HOOKS_REL,
        claude_block_begin=AEGIS_CLAUDE_BLOCK_BEGIN,
        materializers=_managed_update.TargetMaterializers(
            read_json=_read_json,
            wrap_claude_entrypoint=lambda content: _claude_runtime_block(content).encode("utf-8"),
            merge_claude_entrypoint=_merge_claude_entrypoint,
            render_codex_continuation_block=_render_codex_continuation_block,
            merge_codex_entrypoint=_merge_codex_entrypoint,
            merge_codex_hooks=_merge_codex_hooks,
            merge_agents_entrypoint=_merge_agents_entrypoint,
            wrap_agents_entrypoint=lambda content: _managed_runtime_block(
                begin_marker=AEGIS_AGENTS_BLOCK_BEGIN,
                end_marker=AEGIS_AGENTS_BLOCK_END,
                entrypoint=content,
            ).encode("utf-8"),
            codex_hooks_adoptable=_codex_hooks_adoptable,
        ),
    )


def _agent_records(
    enabled_agents: Sequence[str], managed_assets: Sequence[Asset]
) -> dict[str, dict[str, Any]]:
    managed_by_agent: dict[str, list[str]] = {
        "claude": [
            asset.path
            for asset in managed_assets
            if asset.path == "CLAUDE.md" or asset.path.startswith(".claude/")
        ],
        "codex": [
            asset.path
            for asset in managed_assets
            if asset.path == "CODEX.md"
            or asset.path == CODEX_HOOKS_REL
            or asset.path in CODEX_SHARED_RUNTIME_FILES
            or asset.path.startswith("scripts/")
        ],
        "gemini": [],
    }
    return {
        "claude": {
            "enabled": "claude" in enabled_agents,
            "available": True,
            "entrypoint": "CLAUDE.md",
            "managed_files": managed_by_agent["claude"],
            "gate_ids": list(CLAUDE_GATE_IDS) if "claude" in enabled_agents else [],
        },
        "codex": {
            "enabled": "codex" in enabled_agents,
            "available": True,
            "entrypoint": "CODEX.md",
            "managed_files": managed_by_agent["codex"],
            "gate_ids": list(CODEX_GATE_IDS) if "codex" in enabled_agents else [],
        },
        "gemini": {
            "enabled": "gemini" in enabled_agents,
            "available": False,
            "entrypoint": None,
            "managed_files": [],
            "gate_ids": [],
        },
    }


def _gate(
    gate_id: str,
    *,
    required: bool,
    enforcement: str,
    scope: str,
    adapter: str | None = None,
    path: str | None = None,
    command: str | None = None,
    settings_path: str | None = None,
    hook_event: str | None = None,
    hook_matcher: str | None = None,
    unsupported_reason: str | None = None,
    review_command: str | None = None,
    hash_scope: str | None = None,
    bypass_allowed: bool | None = None,
    method: str,
    failure_mode: str,
    expected: str | bool | None = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": gate_id,
        "required": required,
        "enforcement": enforcement,
        "scope": scope,
        "verification": {
            "method": method,
            "failure_mode": failure_mode,
            "expected": expected,
        },
    }
    for key, value in {
        "adapter": adapter,
        "path": path,
        "command": command,
        "settings_path": settings_path,
        "hook_event": hook_event,
        "hook_matcher": hook_matcher,
        "unsupported_reason": unsupported_reason,
        "review_command": review_command,
        "hash_scope": hash_scope,
        "bypass_allowed": bypass_allowed,
    }.items():
        if value is not None:
            payload[key] = value
    return payload


def _gates(enabled_agents: Sequence[str]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    if "claude" in enabled_agents:
        gates.extend(
            [
                _gate(
                    "claude.readiness",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="claude",
                    path=".claude/scripts/readiness.sh",
                    method="executable",
                    failure_mode="fail",
                ),
                _gate(
                    "claude.pretooluse",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="claude",
                    path=".claude/scripts/pretooluse-gate.sh",
                    settings_path=".claude/settings.json",
                    hook_event="PreToolUse",
                    hook_matcher=CLAUDE_PRETOOLUSE_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CLAUDE_PRETOOLUSE_COMMAND,
                ),
                _gate(
                    "claude.posttooluse_tracking",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="claude",
                    path=".claude/scripts/posttooluse-tracking.sh",
                    settings_path=".claude/settings.json",
                    hook_event="PostToolUse",
                    hook_matcher=CLAUDE_PRETOOLUSE_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CLAUDE_POSTTOOLUSE_COMMAND,
                ),
                _gate(
                    "claude.stop_tracking",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="claude",
                    path=".claude/scripts/tracking-stop-gate.sh",
                    settings_path=".claude/settings.json",
                    hook_event="Stop",
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CLAUDE_STOP_TRACKING_COMMAND,
                ),
                _gate(
                    "claude.bash_command",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="claude",
                    path=".claude/scripts/bash-command-guard.sh",
                    method="executable",
                    failure_mode="fail",
                ),
                _gate(
                    "claude.protected_path",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="claude",
                    path=".claude/scripts/codex-path-guard.sh",
                    method="executable",
                    failure_mode="fail",
                ),
            ]
        )
    if "codex" in enabled_agents:
        gates.extend(
            [
                _gate(
                    "codex.readiness",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=".claude/scripts/readiness.sh",
                    method="executable",
                    failure_mode="fail",
                ),
                _gate(
                    "codex.pretooluse",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=".claude/scripts/pretooluse-gate.sh",
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="PreToolUse",
                    hook_matcher=CODEX_HOOK_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_PRETOOLUSE_COMMAND,
                ),
                _gate(
                    "codex.posttooluse_tracking",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=".claude/scripts/posttooluse-tracking.sh",
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="PostToolUse",
                    hook_matcher=CODEX_HOOK_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_POSTTOOLUSE_COMMAND,
                ),
                _gate(
                    "codex.posttooluse_ledger",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=".claude/scripts/ledger-record.sh",
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="PostToolUse",
                    hook_matcher=CODEX_HOOK_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_LEDGER_RECORD_COMMAND,
                ),
                _gate(
                    "codex.session_brief",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=".claude/scripts/session-brief.sh",
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="SessionStart",
                    hook_matcher=CLAUDE_SESSION_START_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_SESSION_BRIEF_COMMAND,
                ),
                _gate(
                    "codex.stop_tracking",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=".claude/scripts/tracking-stop-gate.sh",
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="Stop",
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_STOP_TRACKING_COMMAND,
                ),
                _gate(
                    "codex.apply_patch",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=".claude/scripts/gate_lib.py",
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="PreToolUse",
                    hook_matcher=CODEX_HOOK_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_PRETOOLUSE_COMMAND,
                ),
                _gate(
                    "codex.hook_trust",
                    required=False,
                    enforcement="policy",
                    scope="adapter",
                    adapter="codex",
                    path=CODEX_HOOKS_REL,
                    settings_path=CODEX_HOOKS_REL,
                    unsupported_reason=CODEX_HOOK_TRUST_UNSUPPORTED_REASON,
                    review_command=CODEX_HOOK_TRUST_REVIEW_COMMAND,
                    hash_scope=CODEX_HOOK_TRUST_HASH_SCOPE,
                    bypass_allowed=False,
                    method="manual",
                    failure_mode="unsupported",
                    expected=None,
                ),
                _gate(
                    "codex.guard",
                    required=True,
                    enforcement="verification",
                    scope="adapter",
                    adapter="codex",
                    path="scripts/codex-guard",
                    method="executable",
                    failure_mode="fail",
                ),
                _gate(
                    "codex.work_tracking_audit",
                    required=True,
                    enforcement="verification",
                    scope="adapter",
                    adapter="codex",
                    path="scripts/codex-task",
                    method="executable",
                    failure_mode="fail",
                ),
                _gate(
                    "codex.sessionstart_capture",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=CODEX_HOOKS_REL,
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="SessionStart",
                    hook_matcher=CODEX_SESSION_START_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_SESSION_START_COMMAND,
                ),
                _gate(
                    "codex.posttooluse_capture",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=CODEX_HOOKS_REL,
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="PostToolUse",
                    hook_matcher=CODEX_POSTTOOLUSE_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_LEDGER_RECORD_COMMAND,
                ),
                _gate(
                    "codex.subagent_start_capture",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=CODEX_HOOKS_REL,
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="SubagentStart",
                    hook_matcher=CODEX_SUBAGENT_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_SUBAGENT_START_COMMAND,
                ),
                _gate(
                    "codex.subagent_stop_capture",
                    required=True,
                    enforcement="mechanical",
                    scope="adapter",
                    adapter="codex",
                    path=CODEX_HOOKS_REL,
                    settings_path=CODEX_HOOKS_REL,
                    hook_event="SubagentStop",
                    hook_matcher=CODEX_SUBAGENT_MATCHER,
                    method="settings_hook",
                    failure_mode="fail",
                    expected=CODEX_SUBAGENT_STOP_COMMAND,
                ),
            ]
        )
    gates.append(
        _gate(
            "mcp.memory_write",
            required=False,
            enforcement="policy",
            scope="shared",
            unsupported_reason="MCP memory writes are not mechanically hookable in every client.",
            method="manual",
            failure_mode="unsupported",
            expected=None,
        )
    )
    return gates


def _source_git_commit(source_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _source_git_dirty_paths(source_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "status", "--short"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    dirty: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        dirty.append(line)
    return dirty


def _runtime_payload(source_root: Path, *, updated_at: str) -> dict[str, Any]:
    source = source_root.resolve()
    dirty_paths = _source_git_dirty_paths(source)
    return {
        "mode": "source-root",
        "source_root": source.as_posix(),
        "source_commit": _source_git_commit(source),
        "source_dirty": bool(dirty_paths),
        "source_dirty_paths": dirty_paths,
        "pointer": AEGIS_RUNTIME_ENV_REL,
        "updated_at": updated_at,
        "update_command": "aegis runtime update",
        "reinstall_required_for": [
            ".aegis/runtime/python gate snapshot changes",
            ".aegis/bin/aegis shim changes",
            ".claude/settings.json hook registration changes",
            ".claude/scripts/* dispatcher bootstrap changes",
        ],
    }


def _looks_like_aegis_source_root(path: Path) -> bool:
    gate_source_root = _gate_runtime_source_root(path)
    return (
        (path / "schemas" / "aegis" / "foundation-manifest.schema.json").is_file()
        and (path / "scripts" / "_aegis_installer.py").is_file()
        and gate_source_root is not None
        and (gate_source_root / "aegis_foundation" / "gate" / "readiness.py").is_file()
        and (gate_source_root / "aegis_foundation" / "gate" / "hooks" / "entrypoint.py").is_file()
        and (path / ".claude" / "scripts" / "gate_lib.py").is_file()
        and (path / ".claude" / "scripts" / "readiness.sh").is_file()
    )


def _runtime_env_path(target_root: Path) -> Path:
    return target_root / AEGIS_RUNTIME_ENV_REL


def _parse_runtime_env(target_root: Path) -> dict[str, str]:
    path = _runtime_env_path(target_root)
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _enforcement_path(target_root: Path) -> Path:
    return target_root / AEGIS_ENFORCEMENT_REL


def _read_enforcement_state(target_root: Path) -> dict[str, Any]:
    path = _enforcement_path(target_root)
    raw = _read_json(path)
    configured = isinstance(raw, Mapping)
    mode = str(raw.get("mode") if isinstance(raw, Mapping) else "strict").strip().lower()
    valid = mode in AEGIS_ENFORCEMENT_MODES
    if not valid:
        mode = "strict"
    state = {
        "mode": mode,
        "configured": configured,
        "valid": valid or not configured,
        "path": AEGIS_ENFORCEMENT_REL,
        "gate_decisions": AEGIS_GATE_DECISIONS_REL,
        "set_at": raw.get("set_at") if isinstance(raw, Mapping) else None,
        "set_by": raw.get("set_by") if isinstance(raw, Mapping) else None,
        "reason": raw.get("reason") if isinstance(raw, Mapping) else None,
    }
    if configured and not valid:
        state["invalid_mode"] = raw.get("mode")
    return state


def _read_delivery_policy_state(target_root: Path) -> dict[str, Any]:
    path = target_root / AEGIS_DELIVERY_POLICY_REL
    state: dict[str, Any] = {
        "mode": "attended",
        "configured": path.exists(),
        "valid": not path.exists(),
        "active": False,
        "policy_id": None,
        "path": AEGIS_DELIVERY_POLICY_REL,
        "requires_per_pr_approval": True,
        "autonomous_delivery": False,
        "routine_authority": {key: False for key in AEGIS_ROUTINE_AUTHORITY_FIELDS},
        "reason": "delivery policy is absent; attended mode is the backward-compatible default",
    }
    if not path.exists():
        return state
    if not path.is_file() or path.is_symlink():
        state["reason"] = "delivery policy must be a regular file"
        return state
    raw = _read_json(path)
    if not isinstance(raw, Mapping):
        state["reason"] = "delivery policy is invalid JSON or not an object"
        return state
    schema = _read_json(target_root / AEGIS_DELIVERY_POLICY_SCHEMA_REL)
    if not isinstance(schema, Mapping):
        state["reason"] = "delivery policy schema is unavailable; failing closed to attended mode"
        return state
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(raw)
    except Exception as exc:  # noqa: BLE001 - status must stay non-fatal and fail closed.
        message = exc.message if isinstance(exc, ValidationError) else str(exc)
        state["reason"] = f"delivery policy is malformed; failing closed: {message}"
        return state
    mode = str(raw.get("mode") or "").strip()
    policy_id = str(raw.get("policy_id") or "").strip()
    repository = raw.get("repository")
    authority = raw.get("authority")
    if (
        mode not in AEGIS_DELIVERY_POLICY_MODES
        or not policy_id
        or not isinstance(repository, Mapping)
        or not isinstance(authority, Mapping)
    ):
        state["reason"] = "delivery policy normalization failed; failing closed to attended mode"
        return state
    active = authority.get("status") == "active"
    effective_mode = mode if active else "attended"
    autonomous = effective_mode == "evidence-gated"
    routine = raw.get("routine") if isinstance(raw.get("routine"), Mapping) else {}
    return {
        "mode": effective_mode,
        "configured": True,
        "valid": True,
        "active": active,
        "policy_id": policy_id,
        "path": AEGIS_DELIVERY_POLICY_REL,
        "repository": {
            "full_name": str(repository.get("full_name") or ""),
            "default_branch": str(repository.get("default_branch") or ""),
        },
        "requires_per_pr_approval": not autonomous,
        "autonomous_delivery": autonomous,
        "routine_authority": {
            key: autonomous and bool(routine.get(key)) for key in AEGIS_ROUTINE_AUTHORITY_FIELDS
        },
        "reason": (
            "trusted evidence-gated delivery is active"
            if autonomous
            else (
                "delivery authority is revoked; attended mode is active"
                if not active
                else "attended delivery policy is active"
            )
        ),
    }


def enforcement_status(
    target_dir: str | Path,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    target_root = _resolve_target_root(target_dir)
    state = _read_enforcement_state(target_root)
    pending = _classify_pending_tracking(target_root)
    mode = str(state.get("mode") or "strict")
    advisory_count = int(pending["counts"]["advisory"])
    strict_reentry: dict[str, Any] | None = None
    if advisory_count:
        strict_reentry = {
            "advisory_pending_events": advisory_count,
            "suggested_cli": None,
            "message": (
                "Advisory-era pending events are preserved audit evidence; they do not "
                "require repair or draining before strict re-entry."
            ),
        }
    if not pending["delivery_allowed"]:
        strict_reentry = {
            "advisory_pending_events": advisory_count,
            "suggested_cli": "aegis doctor --target-dir .",
            "message": (
                "Pending tracking contains required or untrusted state; strict enforcement "
                "remains fail-closed until the exact queue evidence is resolved."
            ),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": mode,
        "checked_at": _iso_now(),
        "target_root": target_root.as_posix(),
        "read_only": True,
        "enforcement": state,
        "pending": {
            **pending,
            "advisory": advisory_count,
            "advisory_event_ids": [
                str(item.get("id") or "")
                for item in pending["sample"]
                if item.get("mode") == "advisory"
            ],
        },
        "workflow_guidance": {
            "mode": mode,
            "message": (
                "Aegis is in advisory mode: gates record would-block decisions but do not block."
                if mode == "advisory"
                else "Aegis is in strict mode: gates block according to readiness, pending tracking, and protected-path policy."
            ),
            "strict_reentry": strict_reentry,
        },
    }


def enforce_mode(
    target_dir: str | Path,
    *,
    mode: str,
    reason: str = "",
    set_by: str | None = None,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    target_root = _resolve_target_root(target_dir)
    normalized = mode.strip().lower()
    if normalized not in AEGIS_ENFORCEMENT_MODES:
        raise AegisError(f"unsupported Aegis enforcement mode: {mode}")
    previous = _read_enforcement_state(target_root)
    now = _iso_now()
    actor = set_by or os.environ.get("USER") or os.environ.get("LOGNAME") or "aegis-cli"
    state = {
        "mode": normalized,
        "set_at": now,
        "set_by": actor,
        "reason": reason.strip(),
    }
    _write_text(target_root, AEGIS_ENFORCEMENT_REL, _dump_json(state))
    status_payload = enforcement_status(target_root, source_root=source_root)
    status_payload.update(
        {
            "status": "updated",
            "read_only": False,
            "updated_at": now,
            "previous_mode": previous.get("mode"),
        }
    )
    return status_payload


def runtime_status(target_dir: str | Path, *, source_root: str | Path) -> dict[str, Any]:
    target_root = _resolve_target_root(target_dir)
    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    env_values = _parse_runtime_env(target_root)
    recorded_source = env_values.get("AEGIS_SOURCE_ROOT") or env_values.get("source_root")
    active_source = (
        Path(recorded_source).expanduser().resolve()
        if recorded_source
        else Path(source_root).resolve()
    )
    runtime = manifest.get("runtime") if isinstance(manifest, Mapping) else None
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "installed" if isinstance(manifest, Mapping) else "not_installed",
        "target_root": target_root.as_posix(),
        "runtime_env_path": AEGIS_RUNTIME_ENV_REL,
        "runtime_env_present": _runtime_env_path(target_root).is_file(),
        "runtime_env": env_values,
        "active_source_root": active_source.as_posix(),
        "active_source_valid": _looks_like_aegis_source_root(active_source),
        "active_source_commit": _source_git_commit(active_source),
        "active_source_dirty_paths": _source_git_dirty_paths(active_source),
        "manifest_runtime": runtime if isinstance(runtime, Mapping) else None,
        "reinstall_required_for": (
            runtime.get("reinstall_required_for")
            if isinstance(runtime, Mapping)
            else [
                ".aegis/runtime/python gate snapshot changes",
                ".aegis/bin/aegis shim changes",
                ".claude/settings.json hook registration changes",
                ".claude/scripts/* dispatcher bootstrap changes",
            ]
        ),
    }


def runtime_update(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    apply: bool,
) -> dict[str, Any]:
    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).expanduser().resolve()
    if not _looks_like_aegis_source_root(source):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "refused",
            "reason": "source_root does not look like an Aegis source root",
            "target_root": target_root.as_posix(),
            "source_root": source.as_posix(),
            "required_paths": [
                "schemas/aegis/foundation-manifest.schema.json",
                "scripts/_aegis_installer.py",
                "aegis_foundation/gate/readiness.py",
                "aegis_foundation/gate/hooks/entrypoint.py",
                ".claude/scripts/gate_lib.py",
                ".claude/scripts/readiness.sh",
            ],
        }

    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    if not isinstance(manifest, MutableMapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "refused",
            "reason": "Aegis runtime update requires an installed foundation manifest",
            "target_root": target_root.as_posix(),
            "manifest_path": AEGIS_MANIFEST_REL,
        }

    updated_at = _iso_now()
    runtime = _runtime_payload(source, updated_at=updated_at)
    operations = [
        {
            "path": AEGIS_RUNTIME_ENV_REL,
            "classification": "modify" if _runtime_env_path(target_root).exists() else "create",
            "safe_to_apply": True,
            "managed": True,
            "reason": "Update the project runtime pointer only; no scaffold files are rewritten.",
        },
        {
            "path": AEGIS_MANIFEST_REL,
            "classification": "modify",
            "safe_to_apply": True,
            "managed": True,
            "reason": "Refresh manifest runtime metadata only.",
        },
    ]
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "preview" if not apply else "applied",
        "target_root": target_root.as_posix(),
        "source_root": source.as_posix(),
        "runtime": runtime,
        "operations": operations,
        "reinstall_required": False,
        "reinstall_required_for": runtime["reinstall_required_for"],
        "hygiene": gitignore_hygiene_report(target_root),
    }
    if not apply:
        return report

    manifest["runtime"] = runtime
    managed_files = manifest.get("managed_files")
    if isinstance(managed_files, list) and not any(
        isinstance(item, Mapping) and item.get("path") == AEGIS_RUNTIME_ENV_REL
        for item in managed_files
    ):
        managed_files.append({"path": AEGIS_RUNTIME_ENV_REL, "kind": "runtime"})
    _validate_with_schema(source, "foundation-manifest.schema.json", dict(manifest))
    _write_text(
        target_root,
        AEGIS_RUNTIME_ENV_REL,
        _render_runtime_env(source, updated_at=updated_at).decode("utf-8"),
    )
    _write_text(target_root, AEGIS_MANIFEST_REL, _dump_json(dict(manifest)))
    return report


def _load_source_brief_lib(source_root: Path):
    script = source_root / ".claude" / "scripts" / "brief_lib.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_aegis_update_brief_lib", script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capsule_update_step(target_root: Path, source_root: Path, *, apply: bool) -> dict[str, Any]:
    brief_lib = _load_source_brief_lib(source_root)
    if brief_lib is None:
        return {
            "status": "unavailable",
            "reason": "source root does not provide .claude/scripts/brief_lib.py",
            "compiled": False,
        }
    before = brief_lib.capsule_status(target_root)
    if not apply:
        return {
            "status": "preview",
            "compiled": False,
            "fresh_before": bool(before.get("fresh")),
            "status_before": before,
            "would_compile": not bool(before.get("fresh")),
        }
    capsule = brief_lib.compile_capsule(target_root, reason="manual")
    markdown = brief_lib.render_markdown(capsule)
    brief_lib.write_capsule(target_root, capsule, markdown)
    ok, problems = brief_lib.check_capsule(target_root)
    return {
        "status": "compiled",
        "compiled": True,
        "path_json": ".aegis/capsule/current.json",
        "path_markdown": ".aegis/capsule/current.md",
        "compiled_at": capsule.get("capsule_meta", {}).get("compiled_at"),
        "compile_reason": capsule.get("capsule_meta", {}).get("compile_reason"),
        "check": {"ok": ok, "problems": list(problems)},
        "status_before": before,
        "status_after": brief_lib.capsule_status(target_root),
    }


def _update_product_file_safety(plan: Mapping[str, Any]) -> dict[str, Any]:
    operations = [op for op in plan.get("operations", []) if isinstance(op, Mapping)]
    changed = [
        str(op.get("path"))
        for op in operations
        if op.get("classification") in {"create", "modify", "manual-review", "conflict"}
    ]
    unsafe = [str(op.get("path")) for op in _unsafe_operations(plan)]
    manual = [
        str(op.get("path"))
        for op in operations
        if op.get("classification") in {"manual-review", "conflict"}
    ]
    non_managed = [
        str(op.get("path"))
        for op in operations
        if op.get("classification") != "skip" and op.get("managed") is not True
    ]
    managed_entrypoints = [
        path for path in changed if path in {"AGENTS.md", "CLAUDE.md", "CODEX.md"}
    ]
    return {
        "safe": not unsafe and not manual and not non_managed,
        "changed_paths": changed,
        "unsafe_paths": unsafe,
        "manual_review_paths": manual,
        "non_managed_paths": non_managed,
        "managed_entrypoint_paths": managed_entrypoints,
        "note": (
            "Only installer-managed assets are eligible for apply. Managed AGENTS.md/CLAUDE.md "
            "entrypoint blocks preserve existing project instructions below the Aegis block."
        ),
    }


WORKFLOW_STATE_EVIDENCE_GATE_IDS = {"mutation.pending_tracking_empty"}
WORKFLOW_STATE_EVIDENCE_PREFIXES = ("workflow.",)


def _is_workflow_state_evidence_check(check: Mapping[str, Any]) -> bool:
    gate_id = str(check.get("gate_id") or check.get("id") or "")
    category = str(check.get("category") or "")
    return (
        category == "workflow"
        or gate_id.startswith(WORKFLOW_STATE_EVIDENCE_PREFIXES)
        or gate_id in WORKFLOW_STATE_EVIDENCE_GATE_IDS
    )


def _update_workflow_state_evidence(verification: Mapping[str, Any] | None) -> dict[str, Any]:
    note = (
        "Strict workflow-state verification failures are update evidence only. They do not "
        "change project_update status unless runtime, managed-asset, or capsule apply fails "
        "or is refused."
    )
    if not isinstance(verification, Mapping):
        return {
            "status": "not_run",
            "source": "aegis verify --strict",
            "failed_required": 0,
            "gate_ids": [],
            "checks": [],
            "note": note,
        }

    failed: list[dict[str, Any]] = []
    checks = verification.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, Mapping):
                continue
            if check.get("required") is not True or check.get("status") != "fail":
                continue
            if not _is_workflow_state_evidence_check(check):
                continue
            details = check.get("details")
            failed.append(
                {
                    "gate_id": str(check.get("gate_id") or check.get("id") or ""),
                    "category": str(check.get("category") or ""),
                    "status": str(check.get("status") or ""),
                    "message": str(check.get("message") or ""),
                    "details": dict(details) if isinstance(details, Mapping) else {},
                }
            )

    return {
        "status": "present" if failed else "clean",
        "source": "aegis verify --strict",
        "failed_required": len(failed),
        "gate_ids": [item["gate_id"] for item in failed],
        "checks": failed,
        "note": note,
    }


def project_update(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    apply: bool,
    profile: str = PROFILE_GENERIC,
    strict_verify: bool = True,
) -> dict[str, Any]:
    """One-command update flow for an already-installed target repository.

    This composes the existing safe primitives instead of bypassing them:
    runtime pointer preview/update, managed install plan/apply, strict verify, and capsule
    compile. Verification failures are reported but do not make the managed update itself
    fail; stale workflow-state is exactly what this command is meant to surface without
    stranding the operator.
    """

    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).expanduser().resolve()
    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    if not isinstance(manifest, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "refused",
            "reason": "Aegis update requires an installed foundation manifest",
            "target_root": target_root.as_posix(),
            "manifest_path": AEGIS_MANIFEST_REL,
        }
    primary_agent = _manifest_primary_agent(manifest)
    enabled_agents = _manifest_enabled_agents(manifest)
    runtime_before = runtime_status(target_root, source_root=source)
    runtime_plan = runtime_update(target_root, source_root=source, apply=False)
    install_plan = plan_install(
        target_root,
        source_root=source,
        profile=profile,
        primary_agent=primary_agent,
        agents=enabled_agents,
        baseline_manifest=manifest,
    )
    safety = _update_product_file_safety(install_plan)
    unsafe = _unsafe_operations(install_plan)
    capsule = _capsule_update_step(target_root, source, apply=False)
    verification_preview = verify(
        target_root, source_root=source, strict=strict_verify, dry_run=True
    )
    base_report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "preview" if not apply else "pending",
        "mode": "apply" if apply else "dry_run",
        "target_root": target_root.as_posix(),
        "source_root": source.as_posix(),
        "agent_selection": {
            "primary_agent": primary_agent,
            "enabled_agents": list(enabled_agents),
        },
        "runtime": {
            "before": runtime_before,
            "plan": runtime_plan,
        },
        "install": {
            "plan": install_plan,
            "summary": install_plan.get("summary", {}),
        },
        "product_file_safety": safety,
        "verification": verification_preview,
        "workflow_state_evidence": _update_workflow_state_evidence(verification_preview),
        "capsule": capsule,
        "enforcement": _read_enforcement_state(target_root),
        "delivery_policy": _read_delivery_policy_state(target_root),
        "report_path": AEGIS_UPDATE_REPORT_REL if apply else None,
    }
    if unsafe:
        base_report.update(
            {
                "status": "refused",
                "reason": "Unsafe overwrite or manual-review operation present in install plan.",
                "unsafe_operations": list(unsafe),
            }
        )
        return base_report
    if not apply:
        return base_report

    install_applied = install(
        target_root,
        source_root=source,
        profile=profile,
        primary_agent=primary_agent,
        agents=enabled_agents,
        apply=True,
        baseline_manifest=manifest,
    )
    if install_applied.get("status") in {"refused", "failed"}:
        base_report.update(
            {
                "status": install_applied.get("status"),
                "reason": install_applied.get("reason", "Install apply did not complete."),
                "install": {**base_report["install"], "applied": install_applied},
            }
        )
        return base_report
    runtime_applied = runtime_update(target_root, source_root=source, apply=True)
    if runtime_applied.get("status") == "refused":
        base_report.update(
            {
                "status": "refused",
                "reason": "Runtime pointer update was refused after managed install.",
                "runtime": {**base_report["runtime"], "applied": runtime_applied},
                "install": {**base_report["install"], "applied": install_applied},
            }
        )
        return base_report
    verification = verify(target_root, source_root=source, strict=strict_verify)
    capsule_applied = _capsule_update_step(target_root, source, apply=True)
    report = {
        **base_report,
        "status": "applied",
        "applied_at": _iso_now(),
        "runtime": {
            **base_report["runtime"],
            "applied": runtime_applied,
            "after": runtime_status(target_root, source_root=source),
        },
        "install": {
            **base_report["install"],
            "applied": install_applied,
        },
        "verification": verification,
        "workflow_state_evidence": _update_workflow_state_evidence(verification),
        "capsule": capsule_applied,
        "enforcement": _read_enforcement_state(target_root),
    }
    reports_dir = target_root / AEGIS_REPORTS_REL
    reports_dir.mkdir(parents=True, exist_ok=True)
    (target_root / AEGIS_UPDATE_REPORT_REL).write_text(_dump_json(report), encoding="utf-8")
    return report


def _manifest_payload(
    source_root: Path,
    target_root: Path,
    primary_agent: str,
    enabled_agents: Sequence[str],
    *,
    installed_at: str,
    assets: Sequence[Asset] | None = None,
) -> dict[str, Any]:
    managed_assets = (
        list(assets)
        if assets is not None
        else _managed_assets(source_root, primary_agent, enabled_agents)
    )
    existing = _read_json(target_root / AEGIS_MANIFEST_REL)
    verification = (
        existing.get("verification")
        if existing and isinstance(existing.get("verification"), Mapping)
        else {
            "status": "never",
            "last_verified_at": None,
            "reports": [],
        }
    )
    runtime = (
        existing.get("runtime")
        if existing and isinstance(existing.get("runtime"), Mapping)
        else _runtime_payload(source_root, updated_at=installed_at)
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "foundation_name": FOUNDATION_NAME,
        "foundation_version": FOUNDATION_VERSION,
        "installer_version": INSTALLER_VERSION,
        "installed_at": installed_at,
        "profile": PROFILE_GENERIC,
        "primary_agent": primary_agent,
        "entrypoints": {
            "shared": "AGENTS.md",
            "contract": AEGIS_CONTRACT_REL,
            "codex": "CODEX.md" if "codex" in enabled_agents else None,
            "claude": "CLAUDE.md" if "claude" in enabled_agents else None,
            "gemini": None,
        },
        "interfaces": {
            "cli": {
                "command": "aegis",
            },
            "mcp": {
                "namespace": "aegis",
                "available": False,
                "endpoint": None,
            },
        },
        "runtime": runtime,
        "access_policy": {
            "read_interface": "direct_read_or_aegis_cli",
            "write_interface": "aegis_cli_or_mcp",
            "direct_aegis_writes": False,
        },
        "agents": _agent_records(enabled_agents, managed_assets),
        "capabilities": {
            "taskmaster": (target_root / ".taskmaster").exists(),
            "work_tracking": (target_root / "docs" / "ai" / "work-tracking").exists(),
            "ci": (target_root / ".github" / "workflows").exists(),
            "mcp_contract": True,
        },
        "gates": _gates(enabled_agents),
        "managed_files": [
            {"path": AEGIS_MANIFEST_REL, "kind": "managed"},
            *(
                {
                    "path": asset.path,
                    "kind": asset.kind,
                    "checksum": _content_checksum(asset.content),
                }
                for asset in managed_assets
            ),
        ],
        "customized_files": [],
        "verification": verification,
    }
    _validate_with_schema(source_root, "foundation-manifest.schema.json", payload)
    return payload


def _installed_at_for_plan(target_root: Path) -> str:
    existing = _read_json(target_root / AEGIS_MANIFEST_REL)
    if existing and isinstance(existing.get("installed_at"), str):
        return str(existing["installed_at"])
    return _iso_now()


def _manifest_path_set(manifest: Mapping[str, Any], key: str) -> set[str]:
    return _managed_update.manifest_path_set(manifest, key)


def _content_checksum(content: bytes) -> str:
    return _managed_update.content_checksum(content)


def _manifest_file_record(
    manifest: Mapping[str, Any], key: str, path: str
) -> Mapping[str, Any] | None:
    return _managed_update.manifest_file_record(manifest, key, path)


def _recorded_managed_checksum(manifest: Mapping[str, Any], path: str) -> str | None:
    return _managed_update.recorded_managed_checksum(manifest, path)


def _managed_plan_policy() -> _managed_update.PlanPolicy:
    return _managed_update.PlanPolicy(
        manifest_rel=AEGIS_MANIFEST_REL,
        codex_hooks_rel=CODEX_HOOKS_REL,
        shared_schema_files=tuple(SHARED_SCHEMA_FILES),
        claude_support_files=tuple(CLAUDE_SUPPORT_FILES),
        codex_required_files=tuple(CODEX_REQUIRED_FILES),
        workflow_template_source_root=AEGIS_WORKFLOW_TEMPLATE_SOURCE_ROOT,
        workflow_template_target_root=AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
        workflow_template_names=tuple(AEGIS_WORKFLOW_TEMPLATE_NAMES),
    )


def _source_path_for_managed_asset(path: str) -> str | None:
    runtime_prefix = f"{AEGIS_LOCAL_GATE_RUNTIME_ROOT_REL}/"
    if path.startswith(runtime_prefix):
        return path.removeprefix(runtime_prefix)
    return _managed_update.source_path_for_managed_asset(
        path,
        policy=_managed_plan_policy(),
    )


def _git_blob_checksum(source_root: Path, commit: str, source_path: str) -> str | None:
    return _managed_update.git_blob_checksum(source_root, commit, source_path)


def _legacy_managed_checksum(
    manifest: Mapping[str, Any], current_source_root: Path, path: str
) -> str | None:
    return _managed_update.legacy_managed_checksum(
        manifest,
        current_source_root,
        path,
        policy=_managed_plan_policy(),
    )


def _managed_baseline_checksum(
    manifest: Mapping[str, Any], current_source_root: Path, path: str
) -> tuple[str | None, str | None]:
    checksum = _recorded_managed_checksum(manifest, path)
    if checksum is not None:
        return checksum, "manifest checksum"
    checksum = _legacy_managed_checksum(manifest, current_source_root, path)
    if checksum is not None:
        return checksum, "legacy source commit"
    return None, None


def _plan_operations(
    target_root: Path,
    assets: Sequence[Asset],
    manifest_bytes: bytes,
    *,
    source_root: Path,
    baseline_manifest: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return _managed_update.plan_operations(
        target_root,
        assets,
        manifest_bytes,
        source_root=source_root,
        policy=_managed_plan_policy(),
        read_json=_read_json,
        render_codex_hooks=_render_codex_hooks,
        merge_codex_hooks=_merge_codex_hooks,
        codex_hooks_adoptable_fn=_codex_hooks_adoptable,
        managed_baseline_checksum_fn=_managed_baseline_checksum,
        source_path_for_managed_asset_fn=_source_path_for_managed_asset,
        baseline_manifest=baseline_manifest,
    )


def _summary(operations: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return _managed_update.summarize_operations(operations)


def _client_reload_marker_path(target_root: Path) -> Path:
    return target_root / AEGIS_CLIENT_RELOAD_REL


def _client_reload_marker(target_root: Path) -> dict[str, Any] | None:
    payload = _read_json(_client_reload_marker_path(target_root))
    return payload if isinstance(payload, dict) else None


def invoking_agent_from_environment(
    env: Mapping[str, str] | None = None,
) -> str | None:
    """Identify a supported agent only when the process environment is explicit."""

    values = os.environ if env is None else env
    explicit = str(values.get("AEGIS_INVOKING_AGENT") or "").strip().lower()
    if explicit in AGENT_CHOICES:
        return explicit

    # Prefer the most specific client marker when nested environments expose more than one.
    claude_markers = ("CLAUDE_PROJECT_DIR", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
    if any(values.get(name) for name in claude_markers):
        return "claude"
    if values.get("CODEX_THREAD_ID") or values.get("CODEX_CI") == "1":
        return "codex"
    if values.get("GEMINI_CLI") or values.get("GEMINI_PROJECT_DIR"):
        return "gemini"
    return None


def _client_reload_agents(marker: Mapping[str, Any]) -> tuple[str, ...]:
    raw_agents = marker.get("agents")
    agents: list[str] = []
    if isinstance(raw_agents, list):
        agents.extend(
            str(agent).strip().lower()
            for agent in raw_agents
            if str(agent).strip().lower() in AGENT_CHOICES
        )
    legacy_agent = str(marker.get("agent") or "").strip().lower()
    if legacy_agent in AGENT_CHOICES:
        agents.append(legacy_agent)
    return tuple(dict.fromkeys(agents))


def _client_reload_blocks_agent(marker: Mapping[str, Any], invoking_agent: str | None) -> bool:
    marker_agents = _client_reload_agents(marker)
    normalized_invoker = str(invoking_agent or "").strip().lower()
    if not marker_agents or normalized_invoker not in AGENT_CHOICES:
        return True
    return normalized_invoker in marker_agents


def _write_client_reload_marker(target_root: Path, report: Mapping[str, Any]) -> None:
    changed_paths = [
        str(path) for path in report.get("changed_paths", []) if isinstance(path, str) and path
    ]
    report_agents = report.get("agents")
    agents = (
        [
            str(agent).strip().lower()
            for agent in report_agents
            if str(agent).strip().lower() in AGENT_CHOICES
        ]
        if isinstance(report_agents, list)
        else []
    )
    legacy_agent = str(report.get("agent") or "").strip().lower()
    if legacy_agent in AGENT_CHOICES:
        agents.append(legacy_agent)
    agents = list(dict.fromkeys(agents)) or ["claude"]
    changed_paths_by_agent = report.get("changed_paths_by_agent")
    if not isinstance(changed_paths_by_agent, Mapping):
        changed_paths_by_agent = {agent: changed_paths for agent in agents}
    clearance_by_agent = {
        "claude": {
            "method": "installed_agent_pretooluse_hook",
            "path": ".claude/scripts/pretooluse-gate.sh",
            "description": (
                "A restarted Claude session proves hook activation when PreToolUse runs "
                "and clears only the Claude marker."
            ),
        },
        "codex": {
            "method": "installed_agent_pretooluse_hook",
            "path": CODEX_HOOKS_REL,
            "description": (
                "A trusted Codex project hook proves activation when SessionStart runs "
                "and clears only the Codex marker."
            ),
        },
    }
    active_clearance = {
        agent: clearance_by_agent[agent] for agent in agents if agent in clearance_by_agent
    }
    agent_label = str(report.get("agent") or (agents[0] if len(agents) == 1 else "multi"))
    hook_trust = report.get("hook_trust") if isinstance(report.get("hook_trust"), Mapping) else {}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "required",
        "agent": agent_label,
        "agents": agents,
        "created_at": _iso_now(),
        "changed_paths": changed_paths,
        "changed_paths_by_agent": {
            str(agent): [str(path) for path in paths if isinstance(path, str) and path]
            for agent, paths in changed_paths_by_agent.items()
            if str(agent) in agents and isinstance(paths, list)
        },
        "reason": report.get("reason"),
        "instructions": report.get("instructions"),
        "clearance": active_clearance.get(agents[0], {}),
        "clearance_by_agent": active_clearance,
        "hook_trust": dict(hook_trust),
    }
    target = target_root / AEGIS_CLIENT_RELOAD_REL
    _atomic_write_bytes(
        target,
        _dump_json(payload).encode("utf-8"),
        mode=(target.stat().st_mode & 0o7777) if target.exists() else 0o644,
    )


def _client_reload_report(
    target_root: Path, plan: Mapping[str, Any], enabled_agents: Sequence[str]
) -> dict[str, Any]:
    changed_by_agent: dict[str, list[str]] = {
        agent: [] for agent in enabled_agents if agent in AGENT_CHOICES
    }
    for operation in plan.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        classification = str(operation.get("classification") or "")
        rel_path = str(operation.get("path") or "")
        if classification not in {"create", "modify"}:
            continue
        if "claude" in enabled_agents and (
            rel_path == "CLAUDE.md" or rel_path.startswith(".claude/")
        ):
            changed_by_agent["claude"].append(rel_path)
        if "codex" in enabled_agents and (
            rel_path in {"CODEX.md", CODEX_HOOKS_REL} or rel_path in CODEX_SHARED_RUNTIME_FILES
        ):
            changed_by_agent["codex"].append(rel_path)

    unique_by_agent = {
        agent: sorted(set(paths)) for agent, paths in changed_by_agent.items() if paths
    }
    marker = _client_reload_marker(target_root)
    marker_agents = _client_reload_agents(marker or {})
    marker_by_agent = (marker or {}).get("changed_paths_by_agent")
    if not isinstance(marker_by_agent, Mapping):
        legacy_paths = [
            str(path)
            for path in (marker or {}).get("changed_paths", [])
            if isinstance(path, str) and path
        ]
        marker_by_agent = {agent: legacy_paths for agent in marker_agents}
    effective_by_agent: dict[str, list[str]] = {}
    for agent in dict.fromkeys([*enabled_agents, *marker_agents]):
        paths = [*unique_by_agent.get(agent, [])]
        marker_paths = (
            marker_by_agent.get(agent, []) if isinstance(marker_by_agent, Mapping) else []
        )
        if isinstance(marker_paths, list):
            paths.extend(str(path) for path in marker_paths if isinstance(path, str) and path)
        if paths or agent in marker_agents:
            effective_by_agent[agent] = sorted(set(paths))
    effective_agents = list(effective_by_agent)
    effective_paths = sorted({path for paths in effective_by_agent.values() for path in paths})
    required = bool(effective_agents) or marker is not None
    only_claude = effective_agents == ["claude"]
    only_codex = effective_agents == ["codex"]
    if only_claude:
        reason = (
            "Claude Code loads project hook settings at session start; newly created or changed "
            ".claude/settings.json and .claude/scripts/* hooks are not guaranteed to govern this already-running session."
        )
        instructions = (
            "HARD STOP: if this install ran inside Claude Code, do not edit source files, run project verification, "
            "mutate Taskmaster, or call aegis.start/aegis.kickoff in this same session. restart Claude in this "
            "project so newly installed hooks are active. After restart, run aegis.next and start or kickoff tracked "
            "work before mutating files."
        )
    elif only_codex:
        reason = (
            "Codex loads project hooks at session start and requires hash-based trust for new or changed "
            ".codex/hooks.json command handlers."
        )
        instructions = (
            "HARD STOP: restart Codex in this project, open /hooks and trust the reviewed project hooks, then "
            "run /clear (or restart once more) so the trusted SessionStart recorder proves activation. Run "
            "aegis.next before tracked mutations."
        )
    else:
        reason = "One or more enabled agent adapters changed lifecycle hooks that are loaded and trusted per client session."
        instructions = (
            "HARD STOP for each listed adapter until it proves its own hook activation. Restart Claude where enabled; "
            "for Codex, restart, review/trust the project hooks with /hooks, then run /clear or restart again."
        )
    agent_label = (
        effective_agents[0] if len(effective_agents) == 1 else "multi" if effective_agents else None
    )
    marker_hook_trust = (
        (marker or {}).get("hook_trust")
        if isinstance((marker or {}).get("hook_trust"), Mapping)
        else {}
    )
    codex_trust_required = "codex" in effective_agents and (
        CODEX_HOOKS_REL in effective_paths or bool(marker_hook_trust.get("required"))
    )
    return {
        "required": required,
        "agent": agent_label,
        "agents": effective_agents,
        "severity": "hard_stop" if required else "none",
        "must_stop": required,
        "pending_marker": marker is not None,
        "marker_path": AEGIS_CLIENT_RELOAD_REL if required else None,
        "changed_paths": effective_paths,
        "changed_paths_by_agent": effective_by_agent,
        "reason": (
            reason if required else "No enabled adapter lifecycle hooks changed in this install."
        ),
        "instructions": (
            instructions if required else "No adapter restart is required by this install."
        ),
        "hook_trust": {
            "required": codex_trust_required,
            "settings_path": CODEX_HOOKS_REL if "codex" in enabled_agents else None,
            "review_command": "/hooks" if "codex" in enabled_agents else None,
            "hash_scope": "exact_hook_definition" if "codex" in enabled_agents else None,
            "bypass_allowed": False,
            "instructions": (
                "Review and trust the exact project hook hashes with /hooks; changed hashes remain skipped until trusted."
                if codex_trust_required
                else (
                    "No Codex hook hash changed in this install; use /hooks whenever a future definition changes."
                    if "codex" in enabled_agents
                    else "The Codex adapter is not enabled."
                )
            ),
        },
        "forbidden_until_reload": (
            [
                "source edits",
                "project verification commands",
                "Taskmaster mutations",
                "aegis.start",
                "aegis.kickoff",
                "aegis.verify",
                "aegis.closeout",
            ]
            if required
            else []
        ),
        "allowed_until_reload": (
            [
                "read-only Aegis inspect/status/next/doctor",
                "review the adapter-specific restart/trust instructions",
                "tell the user which enabled clients must restart or reconnect",
                "open /hooks only to review Codex hook definitions and hashes",
            ]
            if required
            else []
        ),
    }


def _expected_manifest_summary(primary_agent: str, enabled_agents: Sequence[str]) -> dict[str, Any]:
    return {
        "path": AEGIS_MANIFEST_REL,
        "profile": PROFILE_GENERIC,
        "primary_agent": primary_agent,
        "agents": {
            agent: {
                "enabled": agent in enabled_agents,
                "gate_ids": list(
                    CLAUDE_GATE_IDS
                    if agent == "claude"
                    else CODEX_GATE_IDS if agent == "codex" else ()
                ),
            }
            for agent in ("claude", "codex", "gemini")
        },
        "gates": [gate["id"] for gate in _gates(enabled_agents)],
    }


def _verification_requirements(enabled_agents: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "gate_id": gate["id"],
            "required": bool(gate["required"]),
            "enforcement": str(gate["enforcement"]),
            "failure_mode": str(gate["verification"]["failure_mode"]),
        }
        for gate in _gates(enabled_agents)
    ]


def inspect_project(
    target_dir: str | Path,
    *,
    profile: str = PROFILE_GENERIC,
    source_root: str | Path | None = None,
    default_primary_agent: str = "claude",
    default_agents: Sequence[str] | None = None,
    invoking_agent: str | None = None,
) -> dict[str, Any]:
    if profile != PROFILE_GENERIC:
        raise AegisError(f"Unsupported Aegis profile in V1: {profile}")
    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    return {
        "schema_version": SCHEMA_VERSION,
        "target_root": str(target_root),
        "profile": profile,
        "exists": target_root.exists(),
        "aegis": {
            "installed": manifest is not None,
            "manifest_path": AEGIS_MANIFEST_REL,
            "foundation_version": manifest.get("foundation_version") if manifest else None,
            "primary_agent": manifest.get("primary_agent") if manifest else None,
        },
        "detected_agents": {
            "claude": (target_root / "CLAUDE.md").exists() or (target_root / ".claude").exists(),
            "codex": (target_root / "CODEX.md").exists() or (target_root / ".codex").exists(),
            "gemini": (target_root / "GEMINI.md").exists() or (target_root / ".gemini").exists(),
        },
        "paths": {
            "manifest": str(target_root / AEGIS_MANIFEST_REL),
            "reports": str(target_root / AEGIS_REPORTS_REL),
            "state": str(target_root / AEGIS_STATE_REL),
        },
        "workflow_guidance": next_action(
            target_root,
            source_root=source,
            default_primary_agent=default_primary_agent,
            default_agents=default_agents,
            invoking_agent=invoking_agent,
        ),
    }


def _ledger_status_block(target_root: Path, source_root: Path) -> dict[str, Any]:
    """Resolve the out-of-worktree ledger store for status discoverability (PR-1a).

    Read-only and best-effort: a missing ledger_lib, a non-git target, or any
    resolution failure degrades to a null store_path with a reason, never an error.
    """

    block: dict[str, Any] = {
        "backend": "sqlite",
        "store_path": None,
        "exists": False,
        "size_bytes": None,
        "schema_doc": "docs/aegis/LEDGER_SCHEMA.md",
    }
    script = Path(source_root) / ".claude" / "scripts" / "ledger_lib.py"
    if not script.is_file():
        block["note"] = "ledger_lib.py not present in source root"
        return block
    try:
        spec = importlib.util.spec_from_file_location("_aegis_status_ledger_lib", script)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load {script}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        resolved = module.store_path(cwd=target_root)
    except Exception as exc:  # noqa: BLE001 - status must stay read-only and non-fatal.
        block["note"] = f"ledger store unresolved: {exc}"
        return block
    block["store_path"] = resolved.as_posix()
    if resolved.is_file():
        block["exists"] = True
        block["size_bytes"] = resolved.stat().st_size
    return block


def status(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    default_primary_agent: str = "claude",
    default_agents: Sequence[str] | None = None,
    invoking_agent: str | None = None,
) -> dict[str, Any]:
    """Report installed Aegis release state without mutating the target."""

    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve()
    manifest_path = target_root / AEGIS_MANIFEST_REL
    manifest_exists = manifest_path.exists()
    manifest = _read_json(manifest_path)
    current_versions = {
        "foundation_version": FOUNDATION_VERSION,
        "installer_version": INSTALLER_VERSION,
        "schema_version": SCHEMA_VERSION,
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "target_root": str(target_root),
        "manifest_path": AEGIS_MANIFEST_REL,
        "read_only": True,
        "installed": manifest is not None,
        "current": current_versions,
        "installed_versions": None,
        "migration_required": False,
        "status": "not_installed",
        "enforcement": _read_enforcement_state(target_root),
        "pending_tracking": _classify_pending_tracking(target_root),
        "delivery_policy": _read_delivery_policy_state(target_root),
        "ledger": _ledger_status_block(target_root, source),
        "checks": [],
        "recommended_actions": [
            "Run aegis plan-install before applying Aegis to this target.",
        ],
    }
    if manifest is None:
        if manifest_exists:
            payload["status"] = "invalid_manifest"
            payload["recommended_actions"] = [
                "Repair or restore .aegis/foundation-manifest.json before upgrading.",
                "Use git history or recorded backups for rollback.",
            ]
        payload["workflow_guidance"] = next_action(
            target_root,
            source_root=source,
            default_primary_agent=default_primary_agent,
            default_agents=default_agents,
            invoking_agent=invoking_agent,
        )
        payload["workflow_guidance"]["enforcement"] = payload["enforcement"]
        payload["workflow_guidance"]["delivery_policy"] = payload["delivery_policy"]
        return payload

    installed_versions = {
        "foundation_version": manifest.get("foundation_version"),
        "installer_version": manifest.get("installer_version"),
        "schema_version": manifest.get("schema_version"),
    }
    checks: list[dict[str, Any]] = []
    try:
        _validate_with_schema(source, "foundation-manifest.schema.json", manifest)
        checks.append(
            {
                "id": "manifest_schema",
                "status": "pass",
                "message": "manifest schema valid",
            }
        )
    except ValidationError as exc:
        checks.append(
            {
                "id": "manifest_schema",
                "status": "fail",
                "message": _manifest_schema_failure_message(source, target_root, manifest, exc),
            }
        )

    for key, current_value in current_versions.items():
        installed_value = installed_versions.get(key)
        checks.append(
            {
                "id": key,
                "status": "pass" if installed_value == current_value else "fail",
                "installed": installed_value,
                "current": current_value,
            }
        )

    failed = [check for check in checks if check.get("status") == "fail"]
    payload.update(
        {
            "installed": True,
            "installed_versions": installed_versions,
            "migration_required": bool(failed),
            "status": "migration_required" if failed else "current",
            "checks": checks,
            "recommended_actions": (
                [
                    "Run aegis plan-install and review managed-file changes before upgrading.",
                    "Run aegis install --apply only after reviewing the plan.",
                    "Run aegis verify after upgrading and keep .aegis/reports/ as evidence.",
                ]
                if failed
                else [
                    "No Aegis package migration is required.",
                    "Run aegis verify after local environment or hook changes.",
                ]
            ),
        }
    )
    payload["workflow_guidance"] = next_action(
        target_root,
        source_root=source,
        default_primary_agent=default_primary_agent,
        default_agents=default_agents,
        invoking_agent=invoking_agent,
    )
    payload["workflow_guidance"]["enforcement"] = payload["enforcement"]
    payload["workflow_guidance"]["delivery_policy"] = payload["delivery_policy"]
    if payload["enforcement"].get("mode") == "advisory":
        payload["recommended_actions"] = [
            "Aegis enforcement is advisory: gates record would-block decisions but do not block.",
            'Return to strict with `aegis enforce --mode strict --reason "<reason>"` after product work.',
            *payload["recommended_actions"],
        ]
    return payload


AEGIS_ARCHITECTURE_NOTES = (
    "Aegis CLI/MCP controls workflow state and evidence. Native agent tools perform "
    "source reads, edits, and project tests. Installed hooks and guards enforce tracking "
    "and protected-path behavior."
)

# TM 188: the cross-agent continuation contract. ONE source of truth, reused by the
# installed-guidance renderers (contract.md / AGENTS.md / CLAUDE.md) and, via the brief
# (TM 189), by `aegis next`. It describes how an agent INTERPRETS a short continuation
# intent and where it STOPS for confirmation — it grants no authority to bypass any gate.
# A bare continuation advances one safe step and then re-consults. Delivery authority is
# resolved from aegis.delivery-policy.json; attended remains the backward-compatible default.
AEGIS_CONTINUATION_LINES = (
    'A short continuation intent — "continue", "go", "proceed", "next", "keep going", '
    '"resume" — is NOT a new authority. It means: advance the current Aegis workflow by '
    "exactly ONE safe step, then re-consult.",
    "",
    "Resolve the intent from live runtime state, never from memory or chat history:",
    "- Run `aegis next` (or the `aegis.next` MCP tool) and perform its `next_safe_action` — "
    "the single sanctioned step. Run `aegis doctor` when `aegis next` reports a repair or "
    "blocked state.",
    '- If readiness is BLOCKED, "continue" means fix workflow state, not mutate.',
    "- Follow the project-declared external work authority. In beads-first projects, inspect "
    "the Gas City bead and use bead kickoff; never allocate parallel local or Taskmaster work.",
    "- Perform the brief's one `next_safe_action`, then re-run `aegis next`. Do not chain "
    "implement -> log -> verify -> closeout across a single intent.",
    "",
    "A bare continuation MAY, without re-asking: read; run read-only inspection and project "
    "tests; edit task-scoped source files; `aegis log`; `aegis verify`; "
    "`aegis closeout --dry-run`; `aegis doctor`; advance one plan step.",
    "",
    "SURFACE before mutation: safe repair plans, closeout preflight, task transitions, "
    "delivery scope, and CI remediation. A valid active evidence-gated policy may authorize "
    "routine external work-item transitions, deterministic safe repairs, verified closeout, "
    "commit/push/PR, and CI remediation without another chat approval. Absent, invalid, "
    "revoked, attended, disabled-capability, manual-review, or protected/owned-path cases "
    "require explicit confirmation. Merge authority comes only from trusted GitHub policy "
    "after closeout passes.",
    "",
    "NEVER automatic on any intent: force-push, `reset --hard`, `branch -D`, history "
    "rewrite, direct `.aegis/` writes, bypassing BLOCKED readiness, skipping S:W:H:E "
    "tracking, or delivery outside the active repository policy. A valid active "
    "evidence-gated policy may authorize an eligible exact-head merge through trusted CI; "
    "absent, invalid, revoked, or attended policy requires owner approval.",
    "",
    'Completion-flavored intents ("finish this", "wrap up", "done") advance one safe step '
    "like any continuation. They do NOT authorize skipping closeout or the active delivery "
    "policy.",
)
AEGIS_CONTINUATION_CONTRACT = "\n".join(AEGIS_CONTINUATION_LINES)
AEGIS_CONTINUATION_SUMMARY = (
    "Continuation contract: a short intent (continue / go / proceed / next / resume) advances "
    "the Aegis workflow by exactly ONE safe step — resolved from `aegis next` (its "
    "`next_safe_action`), never from memory — then re-consult. It is not new authority. "
    "Surface routine workflow mutations and follow the active repository policy. A valid "
    "evidence-gated policy may authorize safe repairs, verified closeout, work-item transitions, "
    "commit/push/PR, CI remediation, and trusted exact-head merge; attended/default policy "
    "requires confirmation. Never automatic: manual-review repair, force-push, history "
    "rewrite, direct `.aegis/` writes, "
    'BLOCKED-readiness bypass, or skipping S:W:H:E. "Finish this" still stops at these '
    "boundaries. Full text in `.aegis/contract.md`."
)
AEGIS_ENTRYPOINT_CONTINUATION_SUMMARY = (
    "Continuation contract: resolve continue / go / next from live `aegis next`, perform "
    "exactly one safe step, then re-consult. Routine repair/closeout/delivery authority "
    "comes only from the active repository policy; manual review, protected-path edits, and "
    "bypass remain attended. Full text in "
    "`.aegis/contract.md`."
)


# TM 189: the continuation brief. Per-state interpretation of a short continuation intent,
# derived from the contract (TM 188) vocabulary. Keyed by next_action's `state` so every state
# gets a coherent brief with no per-site edits. Fields not set here fall back to universal
# defaults in _continuation_brief. continue_means/confirmation/stop must never describe an
# auto merge/push or a BLOCKED-readiness bypass — see test_continuation_brief.
_CONTINUATION_UNIVERSAL_STOP = (
    "readiness BLOCKED",
    "pending tracking unlogged",
    "a protected or owned path edit is required",
    "a user-confirmation boundary is reached",
)
CONTINUATION_BRIEF_BY_STATE: dict[str, dict[str, Any]] = {
    "not_installed": {
        "continue_means": "initialize Aegis before any source edit",
        "next_safe_action": "initialize",
    },
    "invalid_manifest": {
        "continue_means": "repair the Aegis manifest before mutating",
        "next_safe_action": "repair_manifest",
    },
    "client_reload_required": {
        "continue_means": "restart the client so hooks load, then re-run aegis next",
        "next_safe_action": "restart_client",
    },
    "installed_taskmaster_invalid": {
        "continue_means": "repair Taskmaster task state",
        "next_safe_action": "repair_taskmaster",
    },
    "installed_taskmaster_present": {
        "continue_means": "select the next Taskmaster task and kickoff",
        "next_safe_action": "taskmaster_next_then_kickoff",
        "confirmation_boundary": [
            "active evidence-gated policy may authorize a routine transition; attended/default policy requires confirmation"
        ],
    },
    "installed_no_current_work": {
        "continue_means": "pick a Taskmaster task, or start tracked local work",
        "next_safe_action": "start_or_select",
        "confirmation_boundary": ["start a new task"],
    },
    "no_taskmaster": {
        "continue_means": "no task ledger exists yet; initialize Taskmaster for task-driven planning, or start tracked local work — never bind or invent a task id before the ledger exists",
        "next_safe_action": "init_taskmaster_or_start_local",
        "confirmation_boundary": [
            "creating the Taskmaster ledger (task-master init) is a setup mutation; surface it first",
            "do not invent or pin a task id before the ledger exists",
        ],
        "artifact_policy": "setup-only: init the ledger or start local tracked work; do not edit product source",
    },
    "taskmaster_empty": {
        "continue_means": "the ledger is initialized but empty; seed planning by adding a task or authoring and parsing a PRD — never bind a fabricated task to begin work",
        "next_safe_action": "seed_tasks",
        "confirmation_boundary": [
            "parsing a PRD requires explicit user approval",
            "adding the first task is a planning mutation; surface it first",
            "do not bind a placeholder or fake task id",
        ],
        "artifact_policy": "planning-only: write task entries into the ledger; do not edit product source",
    },
    "prd_available_not_parsed": {
        "continue_means": "a PRD is present but not parsed; surface the PRD and the parse plan and get explicit approval before parsing — never assume task ids the parse has not created",
        "next_safe_action": "propose_parse_prd",
        "confirmation_boundary": [
            "running parse-prd requires explicit user approval before it generates tasks",
            "do not assume or fabricate task ids the parse has not created",
        ],
        "artifact_policy": "read the PRD and present the parse plan; run the planning mutation only after explicit approval",
    },
    "prd_parsed_tasks_pending": {
        "continue_means": "the PRD parsed into pending tasks and none is started; review and optionally expand the generated tasks, then select a real task — do not jump into product code",
        "next_safe_action": "review_then_select_task",
        "confirmation_boundary": [
            "selecting and kicking off a task is a workflow mutation; surface the task id first",
            "expanding a task is a planning mutation; surface it first",
            "switch the active task only with explicit confirmation",
        ],
        "artifact_policy": "planning-only: read tasks and expand into subtasks; do not edit product source",
    },
    "first_task_ready": {
        "continue_means": "a real ledger task is ready and none is started; kick off that specific task to open a tracked session — do not edit source before kickoff",
        "next_safe_action": "kickoff_first_task",
        "confirmation_boundary": [
            "kickoff binds and starts the selected task; surface the task id first",
            "active evidence-gated policy may authorize the routine kickoff; attended/default policy requires confirmation",
        ],
        "artifact_policy": "setup-only: kickoff records the session/plan/tracker for the real task; do not edit product source",
    },
    "pending_tracking": {
        "continue_means": "log the pending S:W:H:E event before any other mutation",
        "next_safe_action": "log_pending",
    },
    "observation_completed": {
        "continue_means": "stop observation and proceed to implementation",
        "next_safe_action": "exit_observation",
    },
    "observation_active": {
        "continue_means": "continue read-only observation; stop with aegis observe stop",
        "next_safe_action": "observe_stop",
        "artifact_policy": "save screenshots/notes under reports/; do not edit source",
    },
    "closeout_passed": {
        "continue_means": "task complete; deliver under the active repository authority policy",
        "next_safe_action": "deliver",
        "confirmation_boundary": [
            "aegis.delivery-policy.json controls delivery authority",
            "absent, invalid, revoked, or attended policy requires confirmation",
        ],
    },
    "delivery_pending": {
        "continue_means": "the task is closed; advance delivery under the active repository authority policy",
        "next_safe_action": "deliver_under_policy",
        "confirmation_boundary": [
            "attended mode requires confirmation",
            "evidence-gated mode delegates eligible exact-head merge to trusted GitHub policy",
        ],
        "artifact_policy": "delivery is git/GitHub only; no source edits",
    },
    "delivery_unknown": {
        "continue_means": "inspect git/branch state before any delivery step",
        "next_safe_action": "inspect_git_state",
        "confirmation_boundary": [
            "do not deliver until git state is resolved and the active repository policy can evaluate it"
        ],
        "artifact_policy": "read-only git inspection only",
    },
    "workflow_scaffold_incomplete": {
        "continue_means": "repair the workflow scaffold (plan/tracker pointers)",
        "next_safe_action": "repair_scaffold",
    },
    "safe_repair_available": {
        "continue_means": "review the repair plan (aegis doctor / aegis next), then apply only the safe repairs with aegis repair --apply after surfacing the plan",
        "next_safe_action": "review_repair_plan_then_apply_safe",
        "confirmation_boundary": [
            "active evidence-gated policy may authorize deterministic safe repairs after the plan is surfaced",
            "attended/default or disabled safe-repair authority requires confirmation",
            "any manual-review action needs explicit user confirmation",
        ],
        "artifact_policy": "aegis repair writes the changes; show the plan before applying and do not hand-edit .aegis/",
    },
    "manual_review_repair": {
        "continue_means": "surface the repair plan only; manual-review actions need an explicit human decision and are never auto-applied",
        "next_safe_action": "surface_repair_plan_for_review",
        "confirmation_boundary": [
            "every manual-review repair action requires explicit user confirmation before it is applied",
            "manual-review actions are never applied by aegis repair --apply",
        ],
        "artifact_policy": "read-only: present the plan; do not run aegis repair --apply and do not hand-edit .aegis/",
    },
    "scope_required": {
        "continue_means": "log task scope, then begin the source change",
        "next_safe_action": "log_scope",
        "artifact_policy": "log scope evidence (e.g. FINDINGS.md)",
    },
    "implementation_required": {
        "continue_means": "make the task-scoped change with native tools, then log the pending mutation",
        "next_safe_action": "implement_and_log",
        "confirmation_boundary": ["cross a protected/owned path", "switch the active task"],
        "artifact_policy": "log the changed file as evidence",
    },
    "task_verification_required": {
        "continue_means": "run task verification and log it",
        "next_safe_action": "verify_and_log",
        "artifact_policy": "save verification under reports/, then log",
    },
    "strict_verification_required": {
        "continue_means": "run aegis verify --strict and log the report",
        "next_safe_action": "strict_verify",
        "artifact_policy": "log the strict-verify report",
    },
    "closeout_required": {
        "continue_means": "run aegis closeout --dry-run; after strict verification, active evidence-gated policy may authorize non-dry-run closeout",
        "next_safe_action": "run_closeout_dry_run",
        "confirmation_boundary": [
            "attended/default or disabled verified-closeout authority requires confirmation before non-dry-run closeout"
        ],
        "artifact_policy": "closeout writes the report; do not hand-edit .aegis/",
    },
}


def _continuation_brief(
    state: str, phase: str, *, current_task_authority: str | None = None
) -> dict[str, Any]:
    """Build the per-state continuation brief (TM 189), derived from the TM 188 contract.
    read_only is always True — the brief proves `aegis next` grants no mutation authority."""

    spec = CONTINUATION_BRIEF_BY_STATE.get(state, {})
    extra_stop = tuple(spec.get("stop_conditions") or ())
    brief: dict[str, Any] = {
        "workflow_phase": phase,
        "current_task_authority": current_task_authority or "none",
        "continue_means": spec.get(
            "continue_means", "perform the single next_safe_action, then re-run aegis next"
        ),
        "next_safe_action": spec.get("next_safe_action", state),
        "confirmation_boundary": list(spec.get("confirmation_boundary") or []),
        "artifact_policy": spec.get(
            "artifact_policy", "log evidence via aegis log; do not hand-edit .aegis/"
        ),
        "stop_conditions": [*_CONTINUATION_UNIVERSAL_STOP, *extra_stop],
        "read_only": True,
    }
    return brief


def _workflow_guidance_payload(
    *,
    phase: str,
    state: str,
    next_required_action: str,
    suggested_cli: str,
    suggested_mcp_tool: str | None = None,
    suggested_mcp_arguments: Mapping[str, Any] | None = None,
    missing_gates: Sequence[str] | None = None,
    copyable_repairs: Sequence[str] | None = None,
    details: Mapping[str, Any] | None = None,
    current_task_authority: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "phase": phase,
        "state": state,
        "next_required_action": next_required_action,
        "suggested_cli": suggested_cli,
        "suggested_mcp_call": (
            {
                "tool": suggested_mcp_tool,
                "arguments": dict(suggested_mcp_arguments or {}),
            }
            if suggested_mcp_tool
            else None
        ),
        "missing_gates": list(missing_gates or []),
        "copyable_repairs": list(copyable_repairs or []),
        "read_only": True,
        "architecture_notes": AEGIS_ARCHITECTURE_NOTES,
        "continuation_brief": _continuation_brief(
            state, phase, current_task_authority=current_task_authority
        ),
    }
    if details:
        payload["details"] = dict(details)
    return payload


def _plan_step_completed(plan_rows: Mapping[str, Mapping[str, Any]], step: str) -> bool:
    row = plan_rows.get(step)
    return isinstance(row, Mapping) and str(row.get("status") or "").lower() in {
        "completed",
        "done",
    }


def _strict_verify_passed(target_root: Path) -> bool:
    report = _read_json(target_root / AEGIS_VERIFY_REPORT_REL)
    if not isinstance(report, Mapping):
        return False
    return report.get("mode") == "strict" and report.get("status") == "passed"


def _closeout_passed(
    target_root: Path,
    current_work: Mapping[str, Any] | None,
) -> bool:
    report = _read_json(target_root / AEGIS_CLOSEOUT_REPORT_REL)
    if isinstance(report, Mapping) and report.get("status") == "passed":
        return _closeout_report_matches_current_work(report, current_work)
    return isinstance(current_work, Mapping) and bool(current_work.get("closeout_passed_at"))


def _pr_merge_commit_oid(pr: Mapping[str, Any]) -> str:
    merge_commit = pr.get("mergeCommit")
    if not isinstance(merge_commit, Mapping):
        return ""
    return str(merge_commit.get("oid") or "").strip()


def _merged_delivery_proof(
    target_root: Path,
    *,
    current_branch: str,
    pr: Mapping[str, Any],
) -> dict[str, Any]:
    base_branch = str(pr.get("baseRefName") or "").strip()
    merge_commit = _pr_merge_commit_oid(pr)
    proof: dict[str, Any] = {
        "status": "unproven",
        "current_branch": current_branch,
        "base_branch": base_branch,
        "merge_commit": merge_commit or None,
    }
    if not merge_commit:
        proof["reason"] = "missing_merge_commit"
        return proof
    if not base_branch or current_branch != base_branch:
        proof["reason"] = "current_branch_is_not_pr_base"
        return proof

    upstream_result = _run_target_git(
        target_root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    upstream = upstream_result.stdout.strip() if upstream_result.returncode == 0 else ""
    proof["upstream"] = upstream or None
    if not upstream:
        proof["reason"] = "missing_upstream"
        return proof
    if upstream != base_branch and not upstream.endswith(f"/{base_branch}"):
        proof["reason"] = "upstream_does_not_match_pr_base"
        return proof

    ancestor = _run_target_git(
        target_root,
        "merge-base",
        "--is-ancestor",
        merge_commit,
        "HEAD",
    )
    proof["merge_commit_in_head"] = ancestor.returncode == 0
    if ancestor.returncode != 0:
        proof["reason"] = "merge_commit_not_in_head"
        return proof

    synchronized = _run_target_git(
        target_root,
        "rev-list",
        "--left-right",
        "--count",
        "HEAD...@{u}",
    )
    if synchronized.returncode != 0:
        proof["reason"] = "upstream_comparison_failed"
        return proof
    counts = synchronized.stdout.strip().split()
    if len(counts) != 2:
        proof["reason"] = "invalid_upstream_comparison"
        return proof
    try:
        ahead, behind = (int(value) for value in counts)
    except ValueError:
        proof["reason"] = "invalid_upstream_comparison"
        return proof
    proof["ahead"] = ahead
    proof["behind"] = behind
    if ahead != 0 or behind != 0:
        proof["reason"] = "upstream_not_synchronized"
        return proof
    proof["status"] = "synchronized"
    return proof


def _post_closeout_delivery_guidance(
    target_root: Path,
    current_work: Mapping[str, Any],
) -> dict[str, Any]:
    delivery_policy = _read_delivery_policy_state(target_root)
    requires_approval = bool(delivery_policy.get("requires_per_pr_approval", True))
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    recorded_branch = _current_work_branch_name(current_work, paths).strip()
    try:
        branch = _current_branch(target_root)
    except AegisError as exc:
        return {
            "state": "delivery_unknown",
            "next_safe_action": "inspect_git_state",
            "next_required_action": "inspect git branch state before delivery",
            "suggested_cli": "git status --short --branch",
            "copyable_repairs": ["git status --short --branch"],
            "details": {"reason": str(exc), "recorded_branch": recorded_branch},
        }
    if recorded_branch and recorded_branch != branch:
        gh = _run_gh_pr_list(target_root)
        if not gh.get("available"):
            proof = {
                "status": "unproven",
                "reason": "github_unavailable",
                "github_reason": gh.get("reason"),
            }
        else:
            matching_prs = [
                dict(pr)
                for pr in gh.get("prs", [])
                if isinstance(pr, Mapping) and str(pr.get("headRefName") or "") == recorded_branch
            ]
            merged_prs = [
                pr
                for pr in matching_prs
                if str(pr.get("state") or "").upper() == "MERGED" or pr.get("mergedAt")
            ]
            if merged_prs:
                pr = merged_prs[0]
                proof = _merged_delivery_proof(
                    target_root,
                    current_branch=branch,
                    pr=pr,
                )
                if proof.get("status") == "synchronized":
                    return {
                        "state": "merged_complete",
                        "next_safe_action": "merged_complete",
                        "next_required_action": "no workflow action required",
                        "suggested_cli": "./.aegis/bin/aegis status --target-dir .",
                        "copyable_repairs": [],
                        "details": {
                            "current_branch": branch,
                            "recorded_branch": recorded_branch,
                            "pr": pr,
                            "delivery_proof": proof,
                            "delivery_policy": delivery_policy,
                        },
                    }
            else:
                proof = {
                    "status": "unproven",
                    "reason": "matching_merged_pr_not_found",
                    "matching_prs": matching_prs,
                }
        return {
            "state": "delivery_unknown",
            "next_safe_action": "inspect_git_state",
            "next_required_action": (
                "inspect branch state before delivery because current branch does not match closed work"
            ),
            "suggested_cli": "git status --short --branch",
            "copyable_repairs": ["git status --short --branch"],
            "details": {
                "current_branch": branch,
                "recorded_branch": recorded_branch,
                "delivery_proof": proof,
                "delivery_policy": delivery_policy,
            },
        }

    upstream = _run_target_git(
        target_root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    if upstream.returncode != 0 or not upstream.stdout.strip():
        command = f"git push -u origin {branch}"
        return {
            "state": "delivery_pending",
            "next_safe_action": "push_branch",
            "next_required_action": "push the closed task branch before opening a PR",
            "suggested_cli": command,
            "copyable_repairs": [command],
            "details": {
                "current_branch": branch,
                "upstream": None,
                "sanctioned_after_closeout": True,
                "merge_requires_explicit_user_approval": requires_approval,
                "delivery_policy": delivery_policy,
            },
        }

    gh = _run_gh_pr_list(target_root)
    if not gh.get("available"):
        command = f"gh pr create --draft --base main --head {branch}"
        return {
            "state": "delivery_pending",
            "next_safe_action": "open_pr",
            "next_required_action": (
                "branch is pushed; open a draft PR or inspect GitHub state manually"
            ),
            "suggested_cli": command,
            "copyable_repairs": [command],
            "details": {
                "current_branch": branch,
                "upstream": upstream.stdout.strip(),
                "github": {"available": False, "reason": gh.get("reason")},
                "merge_requires_explicit_user_approval": requires_approval,
                "delivery_policy": delivery_policy,
            },
        }

    prs = [
        dict(pr)
        for pr in gh.get("prs", [])
        if isinstance(pr, Mapping) and str(pr.get("headRefName") or "") == branch
    ]
    merged = [
        pr for pr in prs if str(pr.get("state") or "").upper() == "MERGED" or pr.get("mergedAt")
    ]
    if merged:
        pr = merged[0]
        return {
            "state": "merged_complete",
            "next_safe_action": "merged_complete",
            "next_required_action": "no workflow action required",
            "suggested_cli": "./.aegis/bin/aegis status --target-dir .",
            "copyable_repairs": [],
            "details": {"current_branch": branch, "pr": pr},
        }
    open_prs = [pr for pr in prs if str(pr.get("state") or "").upper() == "OPEN"]
    if open_prs:
        pr = open_prs[0]
        pr_number = pr.get("number")
        detail = _run_gh_pr_view(target_root, pr_number)
        if detail.get("available") and isinstance(detail.get("pr"), Mapping):
            pr = {**pr, **dict(detail["pr"])}
        checks = _summarize_pr_checks(pr)
        checks_command = f"gh pr checks {pr_number}"
        view_command = f"gh pr view {pr_number} --web"
        details = {
            "current_branch": branch,
            "upstream": upstream.stdout.strip(),
            "pr": pr,
            "checks": checks,
            "merge_requires_explicit_user_approval": requires_approval,
            "delivery_policy": delivery_policy,
        }
        if not detail.get("available"):
            details["github_detail"] = {"available": False, "reason": detail.get("reason")}
        if checks.get("state") == "passed":
            if bool(pr.get("isDraft")):
                command = "gh pr ready"
                return {
                    "state": "delivery_pending",
                    "next_safe_action": "mark_ready_for_review",
                    "next_required_action": (
                        "PR checks passed; mark the current-branch draft PR ready before merge"
                    ),
                    "suggested_cli": command,
                    "copyable_repairs": [command, checks_command, view_command],
                    "details": details,
                }
            if not requires_approval:
                return {
                    "state": "delivery_pending",
                    "next_safe_action": "await_evidence_gated_merge",
                    "next_required_action": (
                        "trusted GitHub delivery policy must revalidate and merge the exact head; "
                        "no per-PR owner approval is required"
                    ),
                    "suggested_cli": checks_command,
                    "copyable_repairs": [checks_command, view_command],
                    "details": details,
                }
            return {
                "state": "delivery_pending",
                "next_safe_action": "ask_before_merge",
                "next_required_action": (
                    "PR checks passed; ask for explicit user approval before merging"
                ),
                "suggested_cli": checks_command,
                "copyable_repairs": [checks_command, view_command],
                "details": details,
            }
        if checks.get("state") == "failed":
            return {
                "state": "delivery_blocked",
                "next_safe_action": "fix_ci",
                "next_required_action": "PR checks failed; inspect CI before merge",
                "suggested_cli": checks_command,
                "copyable_repairs": [checks_command, view_command],
                "details": details,
            }
        command = checks_command
        return {
            "state": "delivery_pending",
            "next_safe_action": "wait_for_ci",
            "next_required_action": (
                "PR is open; wait for CI and then follow the active delivery policy"
            ),
            "suggested_cli": command,
            "copyable_repairs": [command, view_command],
            "details": details,
        }

    command = f"gh pr create --draft --base main --head {branch}"
    return {
        "state": "delivery_pending",
        "next_safe_action": "open_pr",
        "next_required_action": "branch is pushed but no PR was found; open a draft PR",
        "suggested_cli": command,
        "copyable_repairs": [command],
        "details": {
            "current_branch": branch,
            "upstream": upstream.stdout.strip(),
            "matching_prs": prs,
            "merge_requires_explicit_user_approval": requires_approval,
            "delivery_policy": delivery_policy,
        },
    }


def _numeric_task_id(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d+", text) else None


TASKMASTER_STATUS_CHOICES = {
    "pending",
    "in-progress",
    "done",
    "completed",
    "deferred",
    "cancelled",
    "blocked",
}


def _taskmaster_repair_guidance() -> list[str]:
    return [
        f"Inspect and repair {TASKMASTER_TASKS_REL}.",
        "Run task-master validate-dependencies after repairing Taskmaster state.",
        "Run python3 scripts/codex-task taskmaster health when the project helper exists.",
    ]


def _invalid_taskmaster_state(reason: str, message: str) -> TaskmasterState:
    return TaskmasterState(
        state="invalid",
        source=TASKMASTER_TASKS_REL,
        reason=reason,
        message=message,
    )


def _empty_taskmaster_state() -> TaskmasterState:
    # TM 190: an initialized-but-taskless ledger is a fresh-project bootstrap phase, NOT
    # corruption. Distinct from `invalid` so next_action can route it to the PRD/empty bootstrap
    # states instead of "repair Taskmaster".
    return TaskmasterState(
        state="empty",
        source=TASKMASTER_TASKS_REL,
        reason="empty_taskmaster_tasks",
        message="Taskmaster ledger is initialized but has no tasks yet",
    )


def _iter_taskmaster_tasks(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    task_lists: list[Any] = []
    root_tasks = payload.get("tasks")
    if isinstance(root_tasks, list):
        task_lists.append(root_tasks)
    for value in payload.values():
        if isinstance(value, Mapping) and isinstance(value.get("tasks"), list):
            task_lists.append(value["tasks"])

    tasks: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for task_list in task_lists:
        for item in task_list:
            if not isinstance(item, Mapping):
                continue
            task_id = _numeric_task_id(item.get("id"))
            if task_id is None or task_id in seen_ids:
                continue
            seen_ids.add(task_id)
            tasks.append(item)
    return tasks


def _taskmaster_task_lists(payload: Mapping[str, Any]) -> tuple[list[Any], TaskmasterState | None]:
    task_lists: list[Any] = []
    if "tasks" in payload:
        root_tasks = payload.get("tasks")
        if not isinstance(root_tasks, list):
            return [], _invalid_taskmaster_state(
                "malformed_task_container",
                "root tasks field must be a list",
            )
        task_lists.append(root_tasks)
    for tag, value in payload.items():
        if not isinstance(value, Mapping) or "tasks" not in value:
            continue
        tagged_tasks = value.get("tasks")
        if not isinstance(tagged_tasks, list):
            return [], _invalid_taskmaster_state(
                "malformed_task_container",
                f"tag {tag!s} tasks field must be a list",
            )
        task_lists.append(tagged_tasks)
    if not task_lists:
        return [], _invalid_taskmaster_state(
            "missing_task_container",
            "Taskmaster payload must contain at least one tasks list",
        )
    return task_lists, None


def _validate_taskmaster_tasks(task_lists: Sequence[Sequence[Any]]) -> TaskmasterState | None:
    seen_ids: set[str] = set()
    for list_index, task_list in enumerate(task_lists):
        for item_index, item in enumerate(task_list):
            location = f"tasks list {list_index} item {item_index}"
            if not isinstance(item, Mapping):
                return _invalid_taskmaster_state(
                    "malformed_task",
                    f"{location} must be an object",
                )
            task_id = _numeric_task_id(item.get("id"))
            if task_id is None:
                return _invalid_taskmaster_state(
                    "invalid_task_id",
                    f"{location} must have a numeric id",
                )
            if task_id in seen_ids:
                return _invalid_taskmaster_state(
                    "duplicate_task_id",
                    f"Taskmaster task id {task_id} appears more than once",
                )
            seen_ids.add(task_id)
            raw_status = item.get("status")
            if not isinstance(raw_status, str) or not raw_status.strip():
                return _invalid_taskmaster_state(
                    "invalid_task_status",
                    f"task {task_id} must have a non-empty string status",
                )
            status = raw_status.strip().lower()
            if status not in TASKMASTER_STATUS_CHOICES:
                return _invalid_taskmaster_state(
                    "invalid_task_status",
                    f"task {task_id} has unsupported status {raw_status!r}",
                )
            raw_dependencies = item.get("dependencies")
            if raw_dependencies is None:
                continue
            if not isinstance(raw_dependencies, list):
                return _invalid_taskmaster_state(
                    "invalid_task_dependencies",
                    f"task {task_id} dependencies must be a list when present",
                )
            for dependency in raw_dependencies:
                if _numeric_task_id(dependency) is None:
                    return _invalid_taskmaster_state(
                        "invalid_task_dependency",
                        f"task {task_id} dependency {dependency!r} is not a numeric task id",
                    )
    if not seen_ids:
        # TM 190: zero tasks is the fresh-project "empty" bootstrap phase, not corruption.
        return _empty_taskmaster_state()
    return None


def _taskmaster_state(target_root: Path) -> TaskmasterState:
    path = target_root / TASKMASTER_TASKS_REL
    if not path.exists():
        return TaskmasterState(state="absent", source=TASKMASTER_TASKS_REL)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _invalid_taskmaster_state(
            "json_decode_error",
            f"{TASKMASTER_TASKS_REL} is not valid JSON: {exc.msg}",
        )
    except OSError as exc:
        return _invalid_taskmaster_state(
            "unreadable",
            f"{TASKMASTER_TASKS_REL} could not be read: {exc}",
        )
    if not isinstance(payload, Mapping):
        return _invalid_taskmaster_state(
            "non_object_payload",
            "Taskmaster payload root must be a JSON object",
        )
    task_lists, invalid = _taskmaster_task_lists(payload)
    if invalid is not None:
        return invalid
    invalid = _validate_taskmaster_tasks(task_lists)
    if invalid is not None:
        return invalid
    return TaskmasterState(
        state="valid",
        source=TASKMASTER_TASKS_REL,
        tasks=tuple(_iter_taskmaster_tasks(payload)),
    )


_PRD_PLACEHOLDER_MARKERS = (
    "[Provide a high-level overview of your product here",
    "[List and describe the main features of your product",
)
_PRD_READ_LIMIT = (
    1_000_000  # PRDs are small text docs; bound the read so a pathological file can't OOM.
)


def _prd_read_head(path: Path) -> str | None:
    """Read at most _PRD_READ_LIMIT chars; return None on read error or binary (NUL) content."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            text = handle.read(_PRD_READ_LIMIT)
    except OSError:
        return None
    if "\x00" in text:  # binary file masquerading as prd.txt
        return None
    return text


def _prd_state(target_root: Path) -> Path | None:
    """TM 190: return the path to an AVAILABLE, real PRD under .taskmaster/docs, else None.

    Read-only and bounded. Only the canonical `prd.txt`/`prd.md` count (a generic `*.md` would
    false-positive on unrelated docs; non-lowercase/other names are intentionally a conservative
    miss that still steers toward PRD authoring). The canonical names are never the example file,
    so the shipped template is excluded implicitly by name AND defensively by content-equality to
    the live `.taskmaster/templates/example_prd.txt` plus placeholder markers — never by a
    hard-coded hash, so it survives template drift. Binary/empty/huge files are rejected."""

    docs = target_root / ".taskmaster" / "docs"
    if not docs.is_dir():
        return None
    template = target_root / ".taskmaster" / "templates" / "example_prd.txt"
    template_text: str | None = None
    if template.is_file():
        head = _prd_read_head(template)
        template_text = head.strip() if head is not None else None
    for candidate in (docs / "prd.txt", docs / "prd.md"):
        if not candidate.is_file():
            continue
        text = _prd_read_head(candidate)
        if text is None:
            continue
        stripped = text.strip()
        if not stripped:
            continue
        if template_text is not None and stripped == template_text:
            continue
        if any(marker in text for marker in _PRD_PLACEHOLDER_MARKERS):
            continue
        return candidate
    return None


def _normalise_default_agent_selection(
    primary_agent: str = "claude",
    agents: Sequence[str] | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Return a valid default install agent selection for guidance payloads."""

    primary = primary_agent if primary_agent in PRIMARY_AGENT_CHOICES else "claude"
    requested = tuple(dict.fromkeys(agents or ()))
    if not requested and primary in AGENT_CHOICES:
        requested = (primary,)
    if not requested and primary == "none":
        requested = ()
    try:
        selected = _enabled_agents(primary, requested)
    except AegisError:
        primary = "claude"
        selected = ("claude",)
    return primary, selected


def _agent_selection_cli_args(primary_agent: str, agents: Sequence[str]) -> str:
    parts = [f"--primary-agent {primary_agent}"]
    parts.extend(f"--agent {agent}" for agent in agents)
    return " ".join(parts)


def _enabled_agents_from_manifest(manifest: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(manifest, Mapping):
        return ()
    agents = manifest.get("agents")
    if not isinstance(agents, Mapping):
        return ()
    enabled: list[str] = []
    for name, payload in agents.items():
        if name not in AGENT_CHOICES or not isinstance(payload, Mapping):
            continue
        if bool(payload.get("enabled")):
            enabled.append(str(name))
    return tuple(enabled)


def _workflow_handler_prefix(target_root: Path) -> str:
    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    primary = (
        str(manifest.get("primary_agent") or "").strip() if isinstance(manifest, Mapping) else ""
    )
    if primary in AGENT_CHOICES:
        return primary
    enabled = _enabled_agents_from_manifest(manifest)
    if len(enabled) == 1:
        return enabled[0]
    return "agent"


def _workflow_log_handler(target_root: Path, event_class: str) -> str:
    return f"{_workflow_handler_prefix(target_root)}:{event_class}"


def _workflow_cli_command(target_root: Path) -> str:
    if (target_root / ".aegis" / "bin" / "aegis").is_file():
        return "./.aegis/bin/aegis"
    if (target_root / "scripts" / "codex-task").is_file():
        return f"{_quote_cli(sys.executable)} scripts/codex-task aegis"
    return "aegis"


def _expects_pending_tracking(target_root: Path) -> bool:
    """Return true when the active workflow requires per-mutation reconciliation."""

    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    if not isinstance(manifest, Mapping):
        return True
    if _read_enforcement_state(target_root).get("mode") == "advisory":
        return False
    primary = str(manifest.get("primary_agent") or "").strip()
    return primary == "claude" and "claude" in _enabled_agents_from_manifest(manifest)


def next_action(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    default_primary_agent: str = "claude",
    default_agents: Sequence[str] | None = None,
    invoking_agent: str | None = None,
    _ignore_client_reload: bool = False,
) -> dict[str, Any]:
    """Return read-only workflow guidance for the next Aegis action."""

    target_root = _resolve_target_root(target_dir)
    manifest_path = target_root / AEGIS_MANIFEST_REL
    manifest_exists = manifest_path.exists()
    manifest = _read_json(manifest_path)
    guidance_primary_agent, guidance_agents = _normalise_default_agent_selection(
        default_primary_agent,
        default_agents,
    )
    public_init_cli = (
        "aegis init"
        if guidance_primary_agent == "claude" and guidance_agents == ("claude",)
        else f"aegis init {_agent_selection_cli_args(guidance_primary_agent, guidance_agents)}"
    )
    plan_install_cli = f"aegis plan-install --target-dir . {_agent_selection_cli_args(guidance_primary_agent, guidance_agents)}"
    install_cli = f"aegis install --target-dir . {_agent_selection_cli_args(guidance_primary_agent, guidance_agents)} --apply"
    if manifest is None:
        if manifest_exists:
            return _workflow_guidance_payload(
                phase="bootstrap",
                state="invalid_manifest",
                next_required_action="repair or restore .aegis/foundation-manifest.json before continuing",
                suggested_cli="./.aegis/bin/aegis status --target-dir .",
                suggested_mcp_tool="aegis.status",
                suggested_mcp_arguments={"target_dir": "."},
                missing_gates=["aegis.manifest_schema"],
                copyable_repairs=[
                    "Restore .aegis/foundation-manifest.json from git history or reinstall Aegis after reviewing plan-install output."
                ],
            )
        return _workflow_guidance_payload(
            phase="bootstrap",
            state="not_installed",
            next_required_action=(
                "HARD STOP before source edits: when Aegis MCP is available, call "
                "suggested_mcp_call (aegis.init) before starting work. Use suggested_cli "
                "only as a CLI fallback when `aegis` is already on PATH. Do not run "
                "project verification, Taskmaster mutation, or Aegis start/kickoff first."
            ),
            suggested_cli=public_init_cli,
            suggested_mcp_tool="aegis.init",
            suggested_mcp_arguments={
                "target_dir": ".",
                "profile": PROFILE_GENERIC,
                "primary_agent": guidance_primary_agent,
                "agents": list(guidance_agents),
                "apply": True,
                "verify_after_install": True,
            },
            missing_gates=["aegis.manifest"],
            copyable_repairs=[
                public_init_cli,
                plan_install_cli,
                install_cli,
            ],
            details={
                "default_primary_agent": guidance_primary_agent,
                "default_agents": list(guidance_agents),
                "preferred_invocation": "mcp",
                "mcp_preferred_when_available": True,
                "cli_requires_aegis_on_path": True,
                "must_initialize_before_source_edits": True,
                "forbidden_until_init": [
                    "source edits",
                    "project verification",
                    "Taskmaster mutations",
                    "aegis.start",
                    "aegis.kickoff",
                ],
                "allowed_until_init": [
                    "read-only project inspection",
                    "Taskmaster next/show discovery",
                    "aegis.inspect",
                    "aegis.status",
                    "aegis.next",
                    "aegis.init",
                ],
            },
        )

    current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    reload_marker = _client_reload_marker(target_root)
    if reload_marker is not None and not _ignore_client_reload:
        if not _client_reload_blocks_agent(reload_marker, invoking_agent):
            payload = next_action(
                target_root,
                source_root=source_root,
                default_primary_agent=default_primary_agent,
                default_agents=default_agents,
                invoking_agent=invoking_agent,
                _ignore_client_reload=True,
            )
            marker_agents = list(_client_reload_agents(reload_marker))
            marker_agent = marker_agents[0] if marker_agents else "unknown"
            pending_reload = {
                "status": "required_for_other_agent",
                "agent": marker_agent,
                "agents": marker_agents,
                "invoking_agent": invoking_agent,
                "blocks_invoking_agent": False,
                "marker_path": AEGIS_CLIENT_RELOAD_REL,
                "changed_paths": reload_marker.get("changed_paths", []),
                "clearance": reload_marker.get("clearance", {}),
            }
            payload["adapter_reload_pending"] = pending_reload
            details = payload.get("details")
            if not isinstance(details, dict):
                details = {}
                payload["details"] = details
            details["pending_adapter_reload"] = pending_reload
            return payload
        marker_agents = list(_client_reload_agents(reload_marker))
        normalized_invoker = str(invoking_agent or "").strip().lower()
        marker_agent = (
            normalized_invoker
            if normalized_invoker in marker_agents
            else marker_agents[0] if marker_agents else "unknown"
        )
        if marker_agent == "codex":
            reload_action = (
                "restart Codex, trust the reviewed project hooks with /hooks, then run /clear "
                "before start/kickoff or source edits"
            )
            suggested_reload = (
                "Restart Codex in this project; open /hooks and trust .codex/hooks.json; "
                "run /clear; then run ./.aegis/bin/aegis next --target-dir ."
            )
            reload_repairs = [
                "Exit this Codex session.",
                "Start Codex again in this same project directory.",
                "Open /hooks and trust the reviewed project hooks.",
                "Run /clear so the trusted SessionStart recorder executes.",
                "./.aegis/bin/aegis next --target-dir .",
            ]
        elif marker_agent == "claude":
            reload_action = "restart Claude before start/kickoff or source edits so newly installed hooks are active"
            suggested_reload = "Restart Claude Code in this project, then run ./.aegis/bin/aegis next --target-dir ."
            reload_repairs = [
                "Exit this Claude session.",
                "Start Claude again in this same project directory.",
                "./.aegis/bin/aegis next --target-dir .",
            ]
        else:
            reload_action = "reload and trust every pending agent adapter before tracked mutations"
            suggested_reload = (
                "Follow the adapter-specific instructions in the client reload marker."
            )
            reload_repairs = [suggested_reload]
        return _workflow_guidance_payload(
            phase="bootstrap",
            state="client_reload_required",
            next_required_action=reload_action,
            suggested_cli=suggested_reload,
            suggested_mcp_tool="aegis.next",
            suggested_mcp_arguments={"target_dir": "."},
            missing_gates=[f"{marker_agent}.client_reload"],
            copyable_repairs=reload_repairs,
            details={
                "client_reload_required": True,
                "agent": marker_agent,
                "agents": marker_agents,
                "marker_path": AEGIS_CLIENT_RELOAD_REL,
                "changed_paths": reload_marker.get("changed_paths", []),
                "clearance": reload_marker.get("clearance", {}),
            },
        )
    if not isinstance(current_work, Mapping):
        if _uses_beads_first_authority(target_root):
            return _workflow_guidance_payload(
                phase="start",
                state="beads_first_ready",
                next_required_action=(
                    "read the authoritative Gas City bead, then start bead-native Aegis "
                    "work without creating or mutating Taskmaster state"
                ),
                suggested_cli=(
                    "./.aegis/bin/aegis kickoff --target-dir . --bead <bead-id> "
                    "--slug <slug> --title '<title>'"
                ),
                suggested_mcp_tool="aegis.bead_kickoff",
                suggested_mcp_arguments={
                    "target_dir": ".",
                    "bead": "<bead-id>",
                    "slug": "<slug>",
                    "title": "<title>",
                    "apply": True,
                },
                missing_gates=["aegis.current_work", "beads.authoritative_work"],
                copyable_repairs=[
                    "Read the selected bead through the rig-scoped Gas City bead surface.",
                    (
                        "./.aegis/bin/aegis kickoff --target-dir . --bead <bead-id> "
                        "--slug <slug> --title '<title>'"
                    ),
                    "./.aegis/bin/aegis observe start --target-dir . 'Read-only audit title'",
                ],
                details={
                    "work_authority": "gas-city-beads",
                    "taskmaster": {
                        "present": (target_root / ".taskmaster").exists(),
                        "mutation_allowed": False,
                        "compatibility": "historical-read-only",
                    },
                },
            )
        taskmaster = _taskmaster_state(target_root)
        prd_path = _prd_state(target_root)
        if taskmaster.state == "absent":
            # TM 190: no task ledger yet. Offer BOTH local tracked work (aegis start) and the
            # task-driven path (task-master init + PRD); never bind a fabricated task id.
            no_tm_repairs = [
                "./.aegis/bin/aegis start '<task title>'",
                "# or, for task-driven planning, stand up Taskmaster then re-check:",
                "task-master init",
                "./.aegis/bin/aegis next --target-dir .",
                "./.aegis/bin/aegis observe start --target-dir . 'Read-only audit title'",
            ]
            no_tm_details: dict[str, Any] = {
                "present": False,
                "bootstrap_phase": "no_taskmaster",
                "local_fallback_allowed": True,
            }
            if prd_path is not None:
                # A PRD already exists; after init it can be parsed (with approval) rather than re-authored.
                prd_rel = prd_path.relative_to(target_root).as_posix()
                no_tm_repairs.insert(
                    3,
                    f"# a PRD already exists at {prd_rel}; after init, parse it (with approval) rather than re-authoring",
                )
                no_tm_details["prd"] = prd_rel
            return _workflow_guidance_payload(
                phase="start",
                state="no_taskmaster",
                next_required_action=(
                    "no task ledger yet: either start tracked local work, or initialize "
                    "Taskmaster (then add a PRD/task) for task-driven planning — never bind a "
                    "fabricated task id before the ledger exists"
                ),
                suggested_cli="./.aegis/bin/aegis start '<task title>'",
                suggested_mcp_tool="aegis.start",
                suggested_mcp_arguments={
                    "target_dir": ".",
                    "title": "<title>",
                    "apply": True,
                },
                missing_gates=["aegis.current_work"],
                copyable_repairs=no_tm_repairs,
                details={"taskmaster": no_tm_details},
            )
        if taskmaster.state == "empty":
            if prd_path is not None:
                prd_rel = prd_path.relative_to(target_root).as_posix()
                return _workflow_guidance_payload(
                    phase="start",
                    state="prd_available_not_parsed",
                    next_required_action=(
                        f"a PRD ({prd_rel}) is present but not parsed: surface the parse plan and "
                        "get explicit user approval before running parse-prd — never assume task "
                        "ids the parse has not created"
                    ),
                    suggested_cli=f"task-master parse-prd --input={prd_rel}",
                    missing_gates=["aegis.current_work", "taskmaster.tasks_present"],
                    copyable_repairs=[
                        f"less {prd_rel}",
                        "# only after explicit user approval, run the planning mutation:",
                        f"task-master parse-prd --input={prd_rel}",
                        "./.aegis/bin/aegis next --target-dir .",
                    ],
                    details={
                        "taskmaster": {
                            "state": "empty",
                            "present": True,
                            "bootstrap_phase": "prd_available_not_parsed",
                            "prd": prd_rel,
                        }
                    },
                )
            return _workflow_guidance_payload(
                phase="start",
                state="taskmaster_empty",
                next_required_action=(
                    "Taskmaster ledger is initialized but empty: seed planning (add a task, or "
                    "author a PRD and parse it with explicit approval) before kickoff — never "
                    "bind a fabricated task id"
                ),
                suggested_cli="task-master add-task --prompt '<first planned task>'",
                missing_gates=["aegis.current_work", "taskmaster.tasks_present"],
                copyable_repairs=[
                    "task-master add-task --prompt '<first planned task>'",
                    "# or author a PRD, then parse it with explicit approval:",
                    "$EDITOR .taskmaster/docs/prd.txt",
                    "task-master parse-prd --input=.taskmaster/docs/prd.txt",
                    "./.aegis/bin/aegis next --target-dir .",
                ],
                details={
                    "taskmaster": {
                        "state": "empty",
                        "present": True,
                        "bootstrap_phase": "taskmaster_empty",
                    }
                },
            )
        if taskmaster.state == "invalid":
            return _workflow_guidance_payload(
                phase="start",
                state="installed_taskmaster_invalid",
                next_required_action=(
                    "repair Taskmaster task state before Aegis can start or select work"
                ),
                suggested_cli="python3 scripts/codex-task taskmaster health",
                missing_gates=["aegis.current_work", "taskmaster.tasks_json_valid"],
                copyable_repairs=_taskmaster_repair_guidance(),
                details={
                    "taskmaster": {
                        **taskmaster.details(),
                        "task_selection_authority": "taskmaster",
                        "aegis_task_selection": "suppressed",
                        "local_fallback_allowed": False,
                    }
                },
            )
        if taskmaster.state == "valid":
            # "started" = real progress (in-progress/done/completed). pending and the terminal
            # non-progress statuses (cancelled/deferred/blocked) are NOT started, so an
            # all-terminal ledger still routes to the pre-kickoff states; that is safe (Taskmaster
            # remains the authority and surfaces only an actionable task, no fabricated id), and
            # the guidance is worded to defer to `task-master next` rather than promise one exists.
            started = any(
                str(task.get("status") or "").strip().lower()
                in {"in-progress", "done", "completed"}
                for task in taskmaster.tasks
            )
            if not started:
                # TM 190: valid ledger with nothing started yet — the pre-kickoff bootstrap
                # states. PRD present => still in the parsed-tasks review phase; no PRD => a
                # curated ledger ready for first kickoff. Both bind only a real ledger task.
                if prd_path is not None:
                    return _workflow_guidance_payload(
                        phase="start",
                        state="prd_parsed_tasks_pending",
                        next_required_action=(
                            "PRD-parsed tasks are pending and none is started: review (and "
                            "optionally expand) the generated tasks, then kick off a real task"
                        ),
                        suggested_cli="task-master list --status=pending && task-master next",
                        missing_gates=["aegis.current_work"],
                        copyable_repairs=[
                            "task-master list --status=pending",
                            "task-master analyze-complexity",
                            "task-master expand --id=<id>",
                            "task-master next && task-master show <id>",
                            "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'",
                            "./.aegis/bin/aegis observe start --target-dir . 'Read-only audit title'",
                        ],
                        details={
                            "taskmaster": {
                                **taskmaster.details(),
                                "task_selection_authority": "taskmaster",
                                "aegis_task_selection": "suppressed",
                                "kickoff_requires_explicit_taskmaster_id": True,
                                "local_fallback_allowed": False,
                                "bootstrap_phase": "prd_parsed_tasks_pending",
                            }
                        },
                    )
                return _workflow_guidance_payload(
                    phase="start",
                    state="first_task_ready",
                    next_required_action=(
                        "the ledger has tasks and none is started: select the first available "
                        "task via Taskmaster next/show (if one is actionable) and kick it off — "
                        "bind only a real ledger task id"
                    ),
                    suggested_cli=(
                        "task-master next && task-master show <id> && "
                        "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'"
                    ),
                    missing_gates=["aegis.current_work"],
                    copyable_repairs=[
                        "task-master next",
                        "task-master show <id>",
                        "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'",
                        "./.aegis/bin/aegis observe start --target-dir . 'Read-only audit title'",
                    ],
                    details={
                        "taskmaster": {
                            **taskmaster.details(),
                            "task_selection_authority": "taskmaster",
                            "aegis_task_selection": "suppressed",
                            "kickoff_requires_explicit_taskmaster_id": True,
                            "local_fallback_allowed": False,
                            "bootstrap_phase": "first_task_ready",
                        }
                    },
                )
            return _workflow_guidance_payload(
                phase="start",
                state="installed_taskmaster_present",
                next_required_action=(
                    "use Taskmaster next/show as task authority, then start Aegis with an explicit "
                    "Taskmaster numeric task id before mutating files"
                ),
                suggested_cli=(
                    "task-master next && task-master show <id> && "
                    "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'"
                ),
                missing_gates=["aegis.current_work"],
                copyable_repairs=[
                    "task-master next",
                    "task-master show <id>",
                    "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'",
                    "./.aegis/bin/aegis observe start --target-dir . 'Read-only audit title'",
                    (
                        "task-master set-status --id=<id> --status=done "
                        "only after aegis closeout and aegis doctor pass"
                    ),
                ],
                details={
                    "taskmaster": {
                        **taskmaster.details(),
                        "task_selection_authority": "taskmaster",
                        "aegis_task_selection": "suppressed",
                        "kickoff_requires_explicit_taskmaster_id": True,
                        "local_fallback_allowed": False,
                        "observation_mode": (
                            "For pre-task audits, screenshots, and app-driving that define future work, "
                            "use aegis observe start instead of binding an unrelated task."
                        ),
                        "ordering": [
                            "task-master next/show",
                            "aegis.kickoff",
                            "native source edit",
                            "aegis.verify",
                            "aegis.closeout",
                            "aegis.doctor",
                            "task-master set-status --status=done",
                        ],
                    }
                },
            )
        # Defensive fallthrough: with TM 190's absent/empty/invalid/valid branches above, every
        # _taskmaster_state outcome returns earlier, so this is unreachable today. Kept as a safe
        # default if _taskmaster_state ever grows a new state; its local-work guidance is otherwise
        # fully preserved by the no_taskmaster branch. (The installed_no_current_work brief + the
        # live _classify_doctor_state usage must stay.)
        return _workflow_guidance_payload(
            phase="start",
            state="installed_no_current_work",
            next_required_action="start task-scoped local work before mutating files",
            suggested_cli="./.aegis/bin/aegis start '<task title>'",
            suggested_mcp_tool="aegis.start",
            suggested_mcp_arguments={
                "target_dir": ".",
                "title": "<title>",
                "apply": True,
            },
            missing_gates=["aegis.current_work"],
            copyable_repairs=[
                "./.aegis/bin/aegis start '<task title>'",
                "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'",
                "./.aegis/bin/aegis observe start --target-dir . 'Read-only audit title'",
            ],
        )

    # An active work record exists from here on: a bare "continue" must not be read as
    # "switch tasks". Name the authoritative task/session so the continuation brief can say so.
    active_task_id = _current_work_task_id(current_work)
    if str(current_work.get("mode") or "") == "observation":
        current_task_authority = "observation-session"
    elif str(current_work.get("mode") or "") == "bead" and active_task_id:
        current_task_authority = f"beads:{active_task_id}"
    elif active_task_id:
        current_task_authority = f"taskmaster:{active_task_id}"
    else:
        current_task_authority = "local-tracked-work"

    pending_tracking = _classify_pending_tracking(target_root)
    if not pending_tracking["delivery_allowed"]:
        required_samples = [
            item
            for item in pending_tracking["sample"]
            if isinstance(item, Mapping) and item.get("mode") == "strict"
        ]
        first_required_id = str(required_samples[0].get("id") or "") if required_samples else ""
        required_event_action = bool(first_required_id)
        pending_event_id = (
            "current"
            if pending_tracking["counts"]["total"] == 1
            and pending_tracking["counts"]["required"] == 1
            else first_required_id
        )
        suggested_cli = (
            "./.aegis/bin/aegis log --target-dir . "
            f"--pending-id {_quote_cli(pending_event_id)} "
            "--note '<past-tense note>' --plan-step auto --plan-status completed"
            if required_event_action
            else "./.aegis/bin/aegis doctor --target-dir . --all --json"
        )
        return _workflow_guidance_payload(
            phase="track",
            state="pending_tracking",
            next_required_action=(
                "log the unresolved required S:W:H:E event before any further mutation"
                if required_event_action
                else (
                    "inspect the malformed, mixed, or unknown pending queue; Aegis is "
                    "failing closed and will not invent a repair"
                )
            ),
            current_task_authority=current_task_authority,
            suggested_cli=suggested_cli,
            suggested_mcp_tool="aegis.log" if required_event_action else "aegis.doctor",
            suggested_mcp_arguments=(
                {
                    "target_dir": ".",
                    "pending_event_id": pending_event_id,
                    "note": "<past-tense note>",
                    "plan_step": "auto",
                    "plan_status": "completed",
                    "apply": True,
                }
                if required_event_action
                else {"target_dir": "."}
            ),
            missing_gates=["mutation.pending_tracking_empty"],
            copyable_repairs=[suggested_cli],
            details={"pending_tracking": pending_tracking},
        )

    if (
        str(current_work.get("mode") or "") == "observation"
        and str(current_work.get("status") or "") == "completed"
    ):
        paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
        observation = (
            current_work.get("observation")
            if isinstance(current_work.get("observation"), Mapping)
            else {}
        )
        return _workflow_guidance_payload(
            phase="start",
            state="observation_completed",
            next_required_action=(
                "review the completed observation evidence, then kickoff a task before mutating files or Taskmaster"
            ),
            current_task_authority=current_task_authority,
            suggested_cli="./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'",
            suggested_mcp_tool="aegis.kickoff",
            suggested_mcp_arguments={
                "target_dir": ".",
                "task": "<id>",
                "slug": "<slug>",
                "title": "<title>",
                "apply": True,
            },
            missing_gates=["aegis.current_work.in_progress"],
            copyable_repairs=[
                "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title '<title>'",
                "./.aegis/bin/aegis observe start --target-dir . 'Read-only audit title'",
            ],
            details={
                "mode": "observation",
                "status": "completed",
                "completed_at": current_work.get("completed_at"),
                "observation": dict(observation),
                "paths": dict(paths),
            },
        )

    if str(current_work.get("mode") or "") == "observation":
        paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
        reports_rel = str(
            paths.get("reports") or "docs/ai/work-tracking/active/<folder>/reports"
        ).strip()
        observation = (
            current_work.get("observation")
            if isinstance(current_work.get("observation"), Mapping)
            else {}
        )
        return _workflow_guidance_payload(
            phase="observe",
            state="observation_active",
            next_required_action=(
                "run observation tooling without source edits or Taskmaster mutation, record findings if useful, "
                "then stop observation so Aegis can verify the working-tree delta and collect known audit artifacts"
            ),
            current_task_authority=current_task_authority,
            suggested_cli=(
                "./.aegis/bin/aegis observe stop --target-dir . "
                "--summary '<what was observed>' --collect-artifacts"
            ),
            suggested_mcp_tool="aegis.observe_stop",
            suggested_mcp_arguments={
                "target_dir": ".",
                "summary": "<what was observed>",
                "collect_artifacts": True,
                "apply": True,
            },
            missing_gates=[],
            copyable_repairs=[
                f"Save screenshots or notes under {reports_rel}/",
                (
                    "./.aegis/bin/aegis observe stop --target-dir . "
                    "--summary '<what was observed>' --collect-artifacts"
                ),
            ],
            details={
                "mode": "observation",
                "observation": dict(observation),
                "allowed_until_stop": [
                    "dev servers and localhost probes",
                    "browser/screenshot MCP tools",
                    "read-only source and git inspection",
                    "aegis log observation notes",
                ],
                "blocked_until_kickoff": [
                    "source edits",
                    "Taskmaster mutations",
                    "git mutations",
                    "Aegis closeout/apply paths",
                ],
            },
        )

    if _closeout_passed(target_root, current_work):
        delivery = _post_closeout_delivery_guidance(target_root, current_work)
        if delivery.get("state") != "merged_complete":
            return _workflow_guidance_payload(
                phase="deliver",
                state=str(delivery.get("state") or "delivery_pending"),
                next_required_action=str(
                    delivery.get("next_required_action")
                    or "deliver the closed task branch through GitHub"
                ),
                suggested_cli=str(delivery.get("suggested_cli") or "git status --short --branch"),
                current_task_authority=current_task_authority,
                missing_gates=["github.delivery"],
                copyable_repairs=[
                    str(item) for item in delivery.get("copyable_repairs", []) if str(item)
                ],
                details={
                    "closeout_report": AEGIS_CLOSEOUT_REPORT_REL,
                    "delivery": {
                        key: value
                        for key, value in delivery.items()
                        if key not in {"copyable_repairs"}
                    },
                },
            )
        return _workflow_guidance_payload(
            phase="complete",
            state="closeout_passed",
            next_required_action="no workflow action required",
            suggested_cli="./.aegis/bin/aegis status --target-dir .",
            suggested_mcp_tool="aegis.status",
            suggested_mcp_arguments={"target_dir": "."},
            current_task_authority=current_task_authority,
            details={"closeout_report": AEGIS_CLOSEOUT_REPORT_REL},
        )

    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    work_rel = str(paths.get("work_tracking") or "").strip()
    plan_rel = str(paths.get("plan") or "plans/current").strip()
    tracker_rel = (
        f"{work_rel}/TRACKER.md" if work_rel else "docs/ai/work-tracking/active/<folder>/TRACKER.md"
    )
    findings_rel = (
        f"{work_rel}/FINDINGS.md"
        if work_rel
        else "docs/ai/work-tracking/active/<folder>/FINDINGS.md"
    )
    reports_rel = str(paths.get("reports") or f"{work_rel}/reports/<slug>").strip()
    plan_path = target_root / plan_rel
    tracker_path = target_root / tracker_rel
    scope_handler = _workflow_log_handler(target_root, "scope")
    implementation_handler = _workflow_log_handler(target_root, "implementation")
    verification_handler = _workflow_log_handler(target_root, "verification")
    pending_tracking_expected = _expects_pending_tracking(target_root)
    if not plan_path.exists() or not tracker_path.exists():
        missing = []
        if not plan_path.exists():
            missing.append("workflow.plan")
        if not tracker_path.exists():
            missing.append("workflow.tracker")
        return _workflow_guidance_payload(
            phase="repair",
            state="workflow_scaffold_incomplete",
            next_required_action="repair current work, plan, and tracker pointers before continuing",
            suggested_cli="./.aegis/bin/aegis status --target-dir .",
            suggested_mcp_tool="aegis.status",
            suggested_mcp_arguments={"target_dir": "."},
            current_task_authority=current_task_authority,
            missing_gates=missing,
            copyable_repairs=[
                "Re-run kickoff only after preserving existing task evidence, or restore missing workflow files from git history."
            ],
        )

    # TM 225: surface fixable drift as a repair state BEFORE the scope/implement/verify/closeout
    # ladder, so a bare "continue" repairs first, then re-consults. Read-only detection (NOT
    # doctor(), which calls next_action() and would recurse): reuse the canonical classifier
    # _classify_doctor_state and trigger only on its "repairable" severity. Gating on severity
    # (not mere presence of a repair action) is essential — a healthy task still yields a
    # cosmetic normalize_plan_table action, which must NOT preempt the ladder. The
    # terminal/observation/scaffold branches above already returned, so only active-work drift
    # reaches here.
    repair_checks = _strict_verification_checks(target_root, manifest)
    repair_actions = _doctor_repair_actions(
        target_root, Path(source_root).resolve(), manifest, current_work
    )
    _, repair_severity = _classify_doctor_state(
        manifest=manifest,
        current_work=current_work,
        checks=repair_checks,
        repair_actions=repair_actions,
    )
    # normalize_plan_table is cosmetic and ever-present (a healthy kickoff table triggers it
    # too), so it is not a reliable repair signal. Route to a repair state ONLY on SUBSTANTIVE
    # drift (missing managed files, broken pointers, manual-review issues). When "repairable"
    # severity is driven by a condition with no substantive repair action — a branch/task
    # misalignment, or only a cosmetic plan-table normalization — fall through to the ladder so
    # the real condition is never masked by a no-op `repair --apply` that "succeeds" without
    # fixing it.
    substantive_repairs = [
        action for action in repair_actions if action.get("kind") != "normalize_plan_table"
    ]
    if repair_severity == "repairable" and substantive_repairs:
        safe_actions, manual_actions = _repair_plan_split(substantive_repairs)
        if safe_actions:
            return _workflow_guidance_payload(
                phase="repair",
                state="safe_repair_available",
                next_required_action="review the repair plan, then apply only the safe repairs",
                suggested_cli="./.aegis/bin/aegis doctor --target-dir .",
                suggested_mcp_tool="aegis.doctor",
                suggested_mcp_arguments={"target_dir": "."},
                current_task_authority=current_task_authority,
                missing_gates=["aegis.repair_plan_clean"],
                copyable_repairs=[
                    "./.aegis/bin/aegis doctor --target-dir .",
                    "./.aegis/bin/aegis repair --target-dir .",
                    "./.aegis/bin/aegis repair --target-dir . --apply",
                ],
                details={
                    "repair_plan": {
                        "available": True,
                        "safe": len(safe_actions),
                        "manual_review": len(manual_actions),
                        "apply_command": "aegis repair --apply",
                    }
                },
            )
        return _workflow_guidance_payload(
            phase="repair",
            state="manual_review_repair",
            next_required_action="surface the repair plan; manual-review actions require explicit human resolution",
            suggested_cli="./.aegis/bin/aegis doctor --target-dir .",
            suggested_mcp_tool="aegis.doctor",
            suggested_mcp_arguments={"target_dir": "."},
            current_task_authority=current_task_authority,
            missing_gates=["aegis.repair_plan_clean"],
            copyable_repairs=[
                "./.aegis/bin/aegis doctor --target-dir .",
                "Review each manual-review repair action in the doctor report and resolve it by hand; do NOT run aegis repair --apply.",
            ],
            details={
                "repair_plan": {
                    "available": True,
                    "safe": 0,
                    "manual_review": len(manual_actions),
                    "apply_command": None,
                }
            },
        )

    plan_rows = _parse_plan_rows(plan_path)
    if not _plan_step_completed(plan_rows, "plan-step-scope"):
        return _workflow_guidance_payload(
            phase="scope",
            state="scope_required",
            next_required_action="log task scope before source edits",
            current_task_authority=current_task_authority,
            suggested_cli=(
                f"./.aegis/bin/aegis log --target-dir . --handler {scope_handler} "
                f"--evidence {_quote_cli(findings_rel)} --note 'Confirmed task scope before implementation' "
                "--plan-step auto --plan-status completed"
            ),
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments={
                "target_dir": ".",
                "handler": scope_handler,
                "evidence": findings_rel,
                "note": "Confirmed task scope before implementation",
                "event_class": "scope",
                "plan_step": "auto",
                "plan_status": "completed",
                "apply": True,
            },
            missing_gates=["plan.scope", "tracker.scope"],
            copyable_repairs=[
                f"./.aegis/bin/aegis log --target-dir . --handler {scope_handler} "
                f"--evidence {_quote_cli(findings_rel)} --note 'Confirmed task scope before implementation' "
                "--plan-step auto --plan-status completed"
            ],
        )

    if not _plan_step_completed(plan_rows, "plan-step-implement"):
        if pending_tracking_expected:
            suggested_cli = (
                "./.aegis/bin/aegis log --target-dir . --pending-id current "
                "--note '<past-tense implementation note>' --plan-step auto --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "pending_event_id": "current",
                "note": "<past-tense implementation note>",
                "plan_step": "auto",
                "plan_status": "completed",
                "apply": True,
            }
            copyable_repairs = [
                "Use native agent tools for the source edit.",
                suggested_cli,
            ]
            next_required_action = (
                "make the task-scoped change with native tools, then log the pending mutation"
            )
        else:
            suggested_cli = (
                f"./.aegis/bin/aegis log --target-dir . --handler {implementation_handler} "
                "--evidence '<changed-file-or-command>' --note '<past-tense implementation note>' "
                "--plan-step plan-step-implement --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "handler": implementation_handler,
                "evidence": "<changed-file-or-command>",
                "note": "<past-tense implementation note>",
                "event_class": "implementation",
                "plan_step": "plan-step-implement",
                "plan_status": "completed",
                "apply": True,
            }
            copyable_repairs = [
                "Use native agent tools for the source edit.",
                suggested_cli,
            ]
            next_required_action = "make the task-scoped change with native tools, then log explicit implementation evidence"
        return _workflow_guidance_payload(
            phase="implement",
            state="implementation_required",
            next_required_action=next_required_action,
            current_task_authority=current_task_authority,
            suggested_cli=suggested_cli,
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments=suggested_mcp_arguments,
            missing_gates=["plan.implement", "tracker.implement"],
            copyable_repairs=copyable_repairs,
            details={"pending_tracking_expected": pending_tracking_expected},
        )

    if not _plan_step_completed(plan_rows, "plan-step-verify"):
        verification_report_rel = f"{reports_rel}/task-verification.md"
        if pending_tracking_expected:
            suggested_cli = (
                f"# Save task verification under {_quote_cli(reports_rel)}/, then:\n"
                "./.aegis/bin/aegis log --target-dir . --pending-id current "
                "--note 'Recorded task-specific verification evidence' --plan-step auto --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "pending_event_id": "current",
                "note": "Recorded task-specific verification evidence",
                "plan_step": "auto",
                "plan_status": "completed",
                "apply": True,
            }
            copyable_repairs = [
                f"Save task verification under {reports_rel}/",
                "./.aegis/bin/aegis log --target-dir . --pending-id current --note 'Recorded task-specific verification evidence' --plan-step auto --plan-status completed",
            ]
        else:
            suggested_cli = (
                f"# Save task verification at {_quote_cli(verification_report_rel)}, then:\n"
                f"./.aegis/bin/aegis log --target-dir . --handler {verification_handler} "
                f"--evidence {_quote_cli(verification_report_rel)} "
                "--note 'Recorded task-specific verification evidence' "
                "--plan-step plan-step-verify --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "handler": verification_handler,
                "evidence": verification_report_rel,
                "note": "Recorded task-specific verification evidence",
                "event_class": "verification",
                "plan_step": "plan-step-verify",
                "plan_status": "completed",
                "apply": True,
            }
            copyable_repairs = [
                f"Save task verification at {verification_report_rel}",
                suggested_cli.splitlines()[-1],
            ]
        return _workflow_guidance_payload(
            phase="verify",
            state="task_verification_required",
            next_required_action="run project verification, save evidence, then log it",
            current_task_authority=current_task_authority,
            suggested_cli=suggested_cli,
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments=suggested_mcp_arguments,
            missing_gates=["plan.verify", "tracker.verify"],
            copyable_repairs=copyable_repairs,
            details={"pending_tracking_expected": pending_tracking_expected},
        )

    if not _strict_verify_passed(target_root):
        return _workflow_guidance_payload(
            phase="verify",
            state="strict_verification_required",
            next_required_action="run strict Aegis verification and log its pending event",
            current_task_authority=current_task_authority,
            suggested_cli="./.aegis/bin/aegis verify --target-dir . --strict",
            suggested_mcp_tool="aegis.verify",
            suggested_mcp_arguments={
                "target_dir": ".",
                "strict": True,
                "acknowledge_report_write": True,
            },
            missing_gates=["strict_verification"],
            copyable_repairs=[
                "./.aegis/bin/aegis verify --target-dir . --strict",
                "./.aegis/bin/aegis log --target-dir . --pending-id current --note 'Recorded strict verification evidence' --plan-step auto --plan-status completed",
            ],
        )

    return _workflow_guidance_payload(
        phase="closeout",
        state="closeout_required",
        next_required_action="run closeout dry-run/readiness, then final closeout before reporting the task complete",
        current_task_authority=current_task_authority,
        suggested_cli="./.aegis/bin/aegis closeout --target-dir . --dry-run --update-handoff",
        suggested_mcp_tool="aegis.closeout_ready",
        suggested_mcp_arguments={
            "target_dir": ".",
            "update_handoff": True,
        },
        missing_gates=["closeout.readiness"],
        copyable_repairs=[
            "./.aegis/bin/aegis closeout --target-dir . --dry-run --update-handoff",
            "./.aegis/bin/aegis closeout --target-dir . --update-handoff",
        ],
    )


def plan_install(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    profile: str = PROFILE_GENERIC,
    primary_agent: str,
    agents: Sequence[str] | None,
    mode: str = "dry_run",
    apply_confirmed: bool = False,
    baseline_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if profile != PROFILE_GENERIC:
        raise AegisError(f"Unsupported Aegis profile in V1: {profile}")
    if mode not in {"dry_run", "apply"}:
        raise AegisError(f"Unsupported install mode: {mode}")
    enabled_agents = _enabled_agents(primary_agent, agents)
    source = Path(source_root).resolve()
    target_root = _resolve_target_root(target_dir)
    installed_at = _installed_at_for_plan(target_root)
    assets = _assets_for_target(target_root, _managed_assets(source, primary_agent, enabled_agents))
    manifest = _manifest_payload(
        source,
        target_root,
        primary_agent,
        enabled_agents,
        installed_at=installed_at,
        assets=assets,
    )
    manifest_bytes = _dump_json(manifest).encode("utf-8")
    operations = _plan_operations(
        target_root,
        assets,
        manifest_bytes,
        source_root=source,
        baseline_manifest=baseline_manifest,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": f"aegis-{profile}-{_utc_now().strftime('%Y%m%d%H%M%S')}",
        "generated_at": _iso_now(),
        "target_root": ".",
        "profile": profile,
        "mode": mode,
        "apply_confirmed": apply_confirmed,
        "agent_selection": {
            "source": "non_interactive",
            "primary_agent": primary_agent,
            "enabled_agents": list(enabled_agents),
            "explicit_flags_required": True,
        },
        "operations": operations,
        "expected_manifest": _expected_manifest_summary(primary_agent, enabled_agents),
        "verification_requirements": _verification_requirements(enabled_agents),
        "reports": {
            "plan_json": AEGIS_PLAN_REPORT_REL,
            "install_json": AEGIS_INSTALL_REPORT_REL if mode == "apply" else None,
            "verification_json": AEGIS_VERIFY_REPORT_REL if mode == "apply" else None,
            "markdown": ".aegis/reports/install-plan.md",
        },
        "summary": _summary(operations),
    }
    _validate_with_schema(source, "install-plan.schema.json", payload)
    return payload


AEGIS_HYGIENE_SIZE_THRESHOLD_BYTES = 5 * 1024 * 1024
AEGIS_GITIGNORE_OUTPUT_PREFIXES = (".aegis/reports/", ".aegis/state/", ".aegis/capsule/")


def _path_is_git_ignored(target_root: Path, rel_path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", rel_path],
            cwd=str(target_root),
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def gitignore_hygiene_report(target_root: Path) -> dict[str, Any]:
    """Capsule PR-1b hygiene rider: warn when Aegis output paths are commit-capable.

    Motivating incident: a 36 MB .aegis/reports/observation-report.json one
    `git add -A` away from a repo. Warn-only — install/upgrade never fail on hygiene.
    """

    warnings: list[str] = []
    gitignore = target_root / ".gitignore"
    lines: set[str] = set()
    if gitignore.is_file():
        try:
            lines = {
                line.strip()
                for line in gitignore.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            }
        except OSError:
            lines = set()
    aegis_covered = bool({".aegis/", ".aegis", ".aegis/**"} & lines)
    uncovered = []
    for prefix in AEGIS_GITIGNORE_OUTPUT_PREFIXES:
        if aegis_covered or prefix in lines or prefix.rstrip("/") in lines:
            continue
        uncovered.append(prefix)
        warnings.append(f".gitignore does not cover Aegis output path {prefix}")
    oversized: list[dict[str, Any]] = []
    aegis_dir = target_root / ".aegis"
    if aegis_dir.is_dir():
        for path in sorted(aegis_dir.rglob("*")):
            try:
                if not path.is_file() or path.stat().st_size < AEGIS_HYGIENE_SIZE_THRESHOLD_BYTES:
                    continue
            except OSError:
                continue
            rel = path.relative_to(target_root).as_posix()
            if _path_is_git_ignored(target_root, rel):
                continue
            size = path.stat().st_size
            oversized.append({"path": rel, "size_bytes": size})
            warnings.append(
                f"unignored Aegis-generated file exceeds {AEGIS_HYGIENE_SIZE_THRESHOLD_BYTES} bytes: {rel} ({size} bytes)"
            )
    return {
        "gitignore_covers_aegis_output": not uncovered,
        "uncovered_prefixes": uncovered,
        "oversized_unignored": oversized,
        "warnings": warnings,
    }


def _unsafe_operations(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        operation for operation in plan.get("operations", []) if not operation.get("safe_to_apply")
    ]


def _atomic_write_bytes(target: Path, content: bytes, *, mode: int) -> None:
    """Atomically replace one file without exposing partially written runtime bytes."""

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.aegis-",
        dir=target.parent,
    )
    temp_path = Path(temp_name)
    try:
        handle = os.fdopen(descriptor, "wb")
        descriptor = -1
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(mode)
        os.replace(temp_path, target)
    except Exception:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def _write_asset(target_root: Path, asset: Asset) -> None:
    target = target_root / asset.path
    if target.exists():
        mode = target.stat().st_mode & 0o7777
        if asset.executable:
            mode |= 0o111
    else:
        mode = 0o755 if asset.executable else 0o644
    _atomic_write_bytes(target, asset.content, mode=mode)


def _install_asset_priority(asset: Asset) -> int:
    """Order dependencies before entrypoints and activation configuration."""

    if asset.path.startswith(f"{AEGIS_LOCAL_GATE_RUNTIME_ROOT_REL}/"):
        return -10
    if asset.path == ".claude/scripts/gate_lib.py":
        return 0
    if asset.path in CLAUDE_SUPPORT_FILES or asset.path == AEGIS_RUNTIME_ENV_REL:
        return 10
    if asset.path == AEGIS_LOCAL_BIN_REL:
        return 20
    if asset.path in CLAUDE_RUNTIME_HOOK_PHASES:
        return 30
    if asset.path in {CODEX_HOOKS_REL, ".claude/settings.json"}:
        return 40
    return 10


def _ordered_install_assets(assets: Sequence[Asset]) -> list[Asset]:
    """Return a stable dependency-first install order."""

    indexed = list(enumerate(assets))
    indexed.sort(key=lambda item: (_install_asset_priority(item[1]), item[0]))
    return [asset for _index, asset in indexed]


def _snapshot_existing_paths(
    target_root: Path,
    rel_paths: Iterable[str],
) -> dict[str, tuple[bytes, int]]:
    snapshots: dict[str, tuple[bytes, int]] = {}
    for rel_path in dict.fromkeys(rel_paths):
        target = target_root / rel_path
        if target.is_file():
            snapshots[rel_path] = (target.read_bytes(), target.stat().st_mode & 0o7777)
    return snapshots


def _restore_existing_paths(
    target_root: Path,
    snapshots: Mapping[str, tuple[bytes, int]],
) -> dict[str, Any]:
    restored: list[str] = []
    errors: list[dict[str, str]] = []
    for rel_path, (content, mode) in snapshots.items():
        try:
            _atomic_write_bytes(target_root / rel_path, content, mode=mode)
            restored.append(rel_path)
        except OSError as exc:
            errors.append({"path": rel_path, "error": str(exc)})
    return {
        "status": "partial" if errors else "completed",
        "restored_paths": sorted(restored),
        "errors": errors,
    }


def _cleanup_created_paths(target_root: Path, rel_paths: Iterable[str]) -> dict[str, Any]:
    removed: list[str] = []
    errors: list[dict[str, str]] = []
    targets = sorted(
        {target_root / rel_path for rel_path in rel_paths},
        key=lambda path: len(path.parts),
        reverse=True,
    )
    parent_candidates: set[Path] = set()
    for target in targets:
        parent_candidates.add(target.parent)
        try:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()
            else:
                continue
            removed.append(_repo_path(target, target_root))
        except OSError as exc:
            errors.append({"path": _repo_path(target, target_root), "error": str(exc)})

    for parent in sorted(parent_candidates, key=lambda path: len(path.parts), reverse=True):
        current = parent
        while current != target_root and target_root in current.parents:
            try:
                current.rmdir()
                removed.append(_repo_path(current, target_root))
            except OSError:
                break
            current = current.parent

    return {
        "status": "partial" if errors else "completed",
        "removed_paths": sorted(set(removed)),
        "errors": errors,
    }


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise AegisError("slug must contain at least one alphanumeric character")
    return slug


def _local_tasks_payload(target_root: Path) -> dict[str, Any]:
    payload = _read_json(target_root / AEGIS_LOCAL_TASKS_REL)
    if isinstance(payload, Mapping):
        tasks = payload.get("tasks")
        if isinstance(tasks, list):
            return dict(payload)
    return {
        "schema_version": SCHEMA_VERSION,
        "next_id": 1,
        "tasks": [],
    }


def _allocate_local_task(target_root: Path, title: str, slug: str) -> dict[str, Any]:
    payload = _local_tasks_payload(target_root)
    raw_next = payload.get("next_id", 1)
    try:
        task_id = int(raw_next)
    except (TypeError, ValueError):
        task_id = 1
    if task_id < 1:
        task_id = 1
    existing_ids = {
        int(task.get("id"))
        for task in payload.get("tasks", [])
        if isinstance(task, Mapping) and str(task.get("id") or "").isdigit()
    }
    while task_id in existing_ids:
        task_id += 1
    task = {
        "id": str(task_id),
        "slug": slug,
        "title": title,
        "status": "in-progress",
        "source": "aegis-local",
        "created_at": _iso_now(),
        "updated_at": _iso_now(),
    }
    payload["next_id"] = task_id + 1
    payload.setdefault("tasks", []).append(task)
    payload["updated_at"] = _iso_now()
    _write_text(target_root, AEGIS_LOCAL_TASKS_REL, _dump_json(payload))
    return task


def _normalize_task_id(task_id: str | int) -> str:
    value = str(task_id).strip()
    if not re.fullmatch(r"\d+", value):
        raise AegisError("Aegis kickoff currently requires a numeric task id")
    return value


def _normalize_bead_id(bead_id: str) -> str:
    value = str(bead_id).strip()
    if not BEAD_ID_PATTERN.fullmatch(value):
        raise AegisError("Aegis bead kickoff requires a lowercase bead id such as ga-zbmk")
    return value


def _normalize_task_slug(slug: str, *, task_id: str | int) -> str:
    normalized = _slugify(slug)
    task_text = _normalize_task_id(task_id)
    for prefix in (f"task-{task_text}-", f"{task_text}-"):
        if normalized.startswith(prefix):
            stripped = normalized[len(prefix) :].strip("-")
            if stripped:
                return stripped
    return normalized


def _normalize_bead_slug(slug: str, *, bead_id: str) -> str:
    normalized = _slugify(slug)
    normalized_bead_id = _normalize_bead_id(bead_id)
    prefix = f"{normalized_bead_id}-"
    if normalized.startswith(prefix):
        stripped = normalized[len(prefix) :].strip("-")
        if stripped:
            return stripped
    return normalized


def _run_target_git(target_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(target_root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _current_branch(target_root: Path) -> str:
    result = _run_target_git(target_root, "branch", "--show-current")
    if result.returncode != 0 or not result.stdout.strip():
        detail = (result.stderr or result.stdout or "empty branch").strip()
        raise AegisError(f"could not determine current git branch: {detail}")
    return result.stdout.strip()


def _ensure_git_work_tree(target_root: Path) -> None:
    result = _run_target_git(target_root, "rev-parse", "--is-inside-work-tree")
    if result.returncode != 0 or result.stdout.strip() != "true":
        detail = (result.stderr or result.stdout or "not a git work tree").strip()
        raise AegisError(f"Aegis kickoff requires a git work tree: {detail}")


def _branch_task_id(branch: str) -> str | None:
    match = re.search(r"(?:^|[-_/])task-?(\d+)(?:[-_/]|$)", branch)
    return match.group(1) if match else None


def _branch_bead_id(branch: str, *, expected_id: str) -> str | None:
    prefix = f"codex/{expected_id}"
    return expected_id if branch == prefix or branch.startswith(prefix + "-") else None


def _task_ids_from_text(value: str) -> list[str]:
    """Extract probable task ids from branch/title text for reconciliation only."""

    ids = {
        match.group(1)
        for match in re.finditer(r"(?:^|[^a-z0-9])task[-_\s#]*(\d+)(?:[^a-z0-9]|$)", value.lower())
    }
    return sorted(ids, key=lambda item: int(item))


def _taskmaster_tasks_by_id_from_state(
    taskmaster: TaskmasterState,
) -> dict[str, dict[str, Any]]:
    if taskmaster.state != "valid":
        return {}
    tasks: dict[str, dict[str, Any]] = {}
    for task in taskmaster.tasks:
        task_id = _numeric_task_id(task.get("id"))
        if task_id is None:
            continue
        tasks[task_id] = {
            "id": task_id,
            "title": str(task.get("title") or f"Task {task_id}").strip() or f"Task {task_id}",
            "status": str(task.get("status") or "").strip().lower() or "unknown",
            "raw": dict(task),
        }
    return tasks


def _taskmaster_tasks_by_id(target_root: Path) -> dict[str, dict[str, Any]]:
    return _taskmaster_tasks_by_id_from_state(_taskmaster_state(target_root))


def _git_ref_exists(target_root: Path, ref: str) -> bool:
    return _run_target_git(target_root, "rev-parse", "--verify", "--quiet", ref).returncode == 0


def _validate_reconcile_base_ref(base_ref: str | None) -> str:
    requested = (base_ref or "origin/main").strip() or "origin/main"
    if requested.startswith("-") or any(ch.isspace() for ch in requested) or "\0" in requested:
        raise AegisError(
            "invalid reconcile base_ref: expected a ref-like value without whitespace, NUL bytes, or leading '-'"
        )
    return requested


def _resolve_reconcile_base_ref(target_root: Path, base_ref: str | None) -> dict[str, Any]:
    requested = _validate_reconcile_base_ref(base_ref)
    candidates = [requested]
    if requested == "origin/main":
        candidates.extend(["main", "master"])
    for candidate in dict.fromkeys(candidates):
        if _git_ref_exists(target_root, candidate):
            return {
                "requested": requested,
                "selected": candidate,
                "available": True,
                "fallback_used": candidate != requested,
            }
    return {
        "requested": requested,
        "selected": requested,
        "available": False,
        "fallback_used": False,
    }


def _git_commit_for_ref(target_root: Path, ref: str) -> str | None:
    result = _run_target_git(target_root, "rev-parse", "--verify", ref)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _reconcile_branch_kind(name: str) -> str:
    return (
        "remote"
        if "/" in name and not name.startswith(("feat/", "fix/", "docs/", "chore/", "task-"))
        else "local"
    )


def _reconcile_branch_candidates(target_root: Path) -> list[dict[str, Any]]:
    result = _run_target_git(
        target_root,
        "for-each-ref",
        "--format=%(refname:short)",
        "refs/heads",
        "refs/remotes",
    )
    if result.returncode != 0:
        return []
    branches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in result.stdout.splitlines():
        name = raw.strip()
        if not name or name.endswith("/HEAD") or name in seen:
            continue
        seen.add(name)
        task_id = _branch_task_id(name)
        if task_id is None:
            continue
        branches.append(
            {
                "name": name,
                "kind": _reconcile_branch_kind(name),
                "task_id": task_id,
                "commit": _git_commit_for_ref(target_root, name),
            }
        )
    return sorted(branches, key=lambda branch: (int(branch["task_id"]), branch["name"]))


def _branch_merge_truth(
    target_root: Path, branch: Mapping[str, Any], base: Mapping[str, Any]
) -> dict[str, Any]:
    if not base.get("available"):
        return {
            "status": "unknown",
            "proof": "base_ref_missing",
            "confidence": "none",
            "reason": "base ref is unavailable; cannot prove ancestry",
        }
    branch_name = str(branch.get("name") or "")
    if not branch.get("commit"):
        return {
            "status": "unknown",
            "proof": "branch_ref_unresolved",
            "confidence": "none",
            "reason": "branch ref could not be resolved",
        }
    base_commit = _git_commit_for_ref(target_root, str(base["selected"]))
    if base_commit and str(branch.get("commit")) == base_commit:
        return {
            "status": "unknown",
            "proof": "branch_at_base",
            "confidence": "none",
            "reason": "branch points at the base ref; no task-specific merge proof exists yet",
        }
    result = _run_target_git(
        target_root, "merge-base", "--is-ancestor", branch_name, str(base["selected"])
    )
    if result.returncode == 0:
        return {
            "status": "merged",
            "proof": "git_ancestor",
            "confidence": "high",
            "reason": f"{branch_name} is an ancestor of {base['selected']}",
        }
    if result.returncode == 1:
        return {
            "status": "unknown",
            "proof": "git_non_ancestor",
            "confidence": "low",
            "reason": "branch tip is not an ancestor; this may be unmerged work or a squash merge",
        }
    return {
        "status": "unknown",
        "proof": "git_merge_base_error",
        "confidence": "none",
        "reason": (result.stderr or result.stdout or "git merge-base failed").strip(),
    }


def _run_gh_pr_list(target_root: Path) -> dict[str, Any]:
    gh = shutil.which("gh")
    if gh is None:
        return {"available": False, "reason": "gh executable not found", "prs": []}
    result = subprocess.run(
        [
            gh,
            "pr",
            "list",
            "--state",
            "all",
            "--limit",
            "200",
            "--json",
            "number,state,title,headRefName,headRefOid,baseRefName,mergeCommit,mergedAt,closedAt,url,isDraft",
        ],
        cwd=target_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return {
            "available": False,
            "reason": (result.stderr or result.stdout or "gh pr list failed").strip(),
            "prs": [],
        }
    try:
        raw_prs = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"available": False, "reason": "gh pr list returned invalid JSON", "prs": []}
    if not isinstance(raw_prs, list):
        return {"available": False, "reason": "gh pr list returned non-list JSON", "prs": []}
    prs = [dict(pr) for pr in raw_prs if isinstance(pr, Mapping)]
    return {"available": True, "reason": "", "prs": prs}


def _run_gh_pr_view(target_root: Path, number: Any) -> dict[str, Any]:
    gh = shutil.which("gh")
    if gh is None:
        return {"available": False, "reason": "gh executable not found", "pr": {}}
    pr_number = str(number or "").strip()
    if not pr_number:
        return {"available": False, "reason": "PR number is missing", "pr": {}}
    result = subprocess.run(
        [
            gh,
            "pr",
            "view",
            pr_number,
            "--json",
            "number,state,title,headRefName,headRefOid,baseRefName,mergeCommit,mergedAt,closedAt,url,isDraft,mergeStateStatus,statusCheckRollup",
        ],
        cwd=target_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return {
            "available": False,
            "reason": (result.stderr or result.stdout or "gh pr view failed").strip(),
            "pr": {},
        }
    try:
        raw_pr = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"available": False, "reason": "gh pr view returned invalid JSON", "pr": {}}
    if not isinstance(raw_pr, Mapping):
        return {"available": False, "reason": "gh pr view returned non-object JSON", "pr": {}}
    return {"available": True, "reason": "", "pr": dict(raw_pr)}


def _summarize_pr_checks(pr: Mapping[str, Any]) -> dict[str, Any]:
    raw_checks = pr.get("statusCheckRollup")
    if not isinstance(raw_checks, list) or not raw_checks:
        return {"state": "unknown", "checks": [], "reason": "no status checks reported"}

    checks: list[dict[str, Any]] = []
    pending: list[str] = []
    failed: list[str] = []
    passed: list[str] = []
    success_conclusions = {"SUCCESS", "NEUTRAL", "SKIPPED"}
    for item in raw_checks:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("workflowName") or "unnamed check")
        status = str(item.get("status") or "").upper()
        conclusion = str(item.get("conclusion") or "").upper()
        check = {
            "name": name,
            "status": status,
            "conclusion": conclusion,
            "detailsUrl": item.get("detailsUrl"),
        }
        checks.append(check)
        if status != "COMPLETED":
            pending.append(name)
        elif conclusion in success_conclusions:
            passed.append(name)
        else:
            failed.append(name)

    if failed:
        return {"state": "failed", "checks": checks, "failed": failed, "pending": pending}
    if pending:
        return {"state": "pending", "checks": checks, "pending": pending}
    if passed:
        return {"state": "passed", "checks": checks, "passed": passed}
    return {"state": "unknown", "checks": checks, "reason": "no classifiable checks reported"}


def delivery_snapshot(
    target_dir: str | Path,
    *,
    pr_number: str | int | None = None,
    branch: str | None = None,
) -> dict[str, Any]:
    """Return machine-observed git/GitHub delivery state without mutating the target."""

    target_root = Path(target_dir).resolve()
    selected_branch = str(branch or "").strip()
    if not selected_branch:
        try:
            selected_branch = _current_branch(target_root)
        except AegisError as exc:
            return {
                "available": False,
                "reason": str(exc),
                "recordable": False,
            }

    upstream_result = _run_target_git(
        target_root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        f"{selected_branch}@{{upstream}}",
    )
    upstream = upstream_result.stdout.strip() if upstream_result.returncode == 0 else None

    selected_pr: dict[str, Any] | None = None
    requested_pr = str(pr_number or "").strip()
    if requested_pr:
        detail = _run_gh_pr_view(target_root, requested_pr)
        if not detail.get("available") or not isinstance(detail.get("pr"), Mapping):
            return {
                "available": False,
                "reason": str(detail.get("reason") or "GitHub PR state unavailable"),
                "recordable": False,
                "branch": selected_branch,
                "upstream": upstream,
                "pr_number": requested_pr,
            }
        selected_pr = dict(detail["pr"])
        selected_branch = str(selected_pr.get("headRefName") or selected_branch)
    else:
        listing = _run_gh_pr_list(target_root)
        if not listing.get("available"):
            return {
                "available": False,
                "reason": str(listing.get("reason") or "GitHub PR state unavailable"),
                "recordable": False,
                "branch": selected_branch,
                "upstream": upstream,
            }
        matches = [
            dict(pr)
            for pr in listing.get("prs", [])
            if isinstance(pr, Mapping) and str(pr.get("headRefName") or "") == selected_branch
        ]
        if matches:
            open_matches = [pr for pr in matches if str(pr.get("state") or "").upper() == "OPEN"]
            selected_pr = (open_matches or matches)[0]
            detail = _run_gh_pr_view(target_root, selected_pr.get("number"))
            if detail.get("available") and isinstance(detail.get("pr"), Mapping):
                selected_pr = {**selected_pr, **dict(detail["pr"])}

    if selected_pr is None:
        action = "branch_pushed" if upstream else "local_only"
        return {
            "available": True,
            "recordable": bool(upstream),
            "action": action,
            "branch": selected_branch,
            "upstream": upstream,
            "head_commit": _git_commit_for_ref(target_root, selected_branch)
            or _git_commit_for_ref(target_root, "HEAD"),
            "pr": None,
            "checks": {"state": "not_applicable", "checks": []},
        }

    # An exact post-merge PR lookup may start from main and then resolve the PR's deleted
    # or non-current head branch. Recompute upstream against that observed branch so main's
    # upstream is never attributed to the delivered branch.
    upstream_result = _run_target_git(
        target_root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        f"{selected_branch}@{{upstream}}",
    )
    upstream = upstream_result.stdout.strip() if upstream_result.returncode == 0 else None

    state = str(selected_pr.get("state") or "").upper()
    merged_at = selected_pr.get("mergedAt")
    if state == "MERGED" or merged_at:
        action = "pr_merged"
    elif state == "OPEN" and bool(selected_pr.get("isDraft")):
        action = "pr_draft"
    elif state == "OPEN":
        action = "pr_open"
    elif state == "CLOSED":
        action = "pr_closed"
    else:
        return {
            "available": False,
            "reason": f"unrecognized GitHub PR state: {state or '<empty>'}",
            "recordable": False,
            "branch": selected_branch,
            "upstream": upstream,
            "pr": selected_pr,
        }

    return {
        "available": True,
        "recordable": True,
        "action": action,
        "branch": selected_branch,
        "upstream": upstream,
        "head_commit": selected_pr.get("headRefOid")
        or _git_commit_for_ref(target_root, selected_branch)
        or _git_commit_for_ref(target_root, "HEAD"),
        "pr": selected_pr,
        "checks": _summarize_pr_checks(selected_pr),
    }


def _task_ids_for_pr(pr: Mapping[str, Any]) -> list[str]:
    ids = set(_task_ids_from_text(str(pr.get("headRefName") or "")))
    ids.update(_task_ids_from_text(str(pr.get("title") or "")))
    return sorted(ids, key=lambda item: int(item))


def _prs_by_task_id(gh: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for pr in gh.get("prs", []):
        if not isinstance(pr, Mapping):
            continue
        clean = {
            "number": pr.get("number"),
            "state": str(pr.get("state") or "").upper(),
            "title": str(pr.get("title") or ""),
            "headRefName": str(pr.get("headRefName") or ""),
            "baseRefName": str(pr.get("baseRefName") or ""),
            "mergedAt": pr.get("mergedAt"),
            "url": pr.get("url"),
            "isDraft": bool(pr.get("isDraft")),
        }
        for task_id in _task_ids_for_pr(clean):
            grouped.setdefault(task_id, []).append(clean)
    return grouped


def _github_truth_for_prs(prs: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    merged = [
        pr for pr in prs if str(pr.get("state") or "").upper() == "MERGED" or pr.get("mergedAt")
    ]
    if merged:
        pr = merged[0]
        return {
            "status": "merged",
            "proof": "github_pr_merged",
            "confidence": "high",
            "reason": f"PR #{pr.get('number')} is merged",
            "pr": dict(pr),
        }
    open_prs = [pr for pr in prs if str(pr.get("state") or "").upper() == "OPEN"]
    if open_prs:
        pr = open_prs[0]
        return {
            "status": "not_merged",
            "proof": "github_pr_open",
            "confidence": "high",
            "reason": f"PR #{pr.get('number')} is still open",
            "pr": dict(pr),
        }
    closed = [pr for pr in prs if str(pr.get("state") or "").upper() == "CLOSED"]
    if closed:
        pr = closed[0]
        return {
            "status": "not_merged",
            "proof": "github_pr_closed_unmerged",
            "confidence": "high",
            "reason": f"PR #{pr.get('number')} is closed without merge metadata",
            "pr": dict(pr),
        }
    return None


def _task_merge_truth(
    target_root: Path,
    branches: Sequence[Mapping[str, Any]],
    prs: Sequence[Mapping[str, Any]],
    base: Mapping[str, Any],
) -> dict[str, Any]:
    github_truth = _github_truth_for_prs(prs)
    branch_truths = [_branch_merge_truth(target_root, branch, base) for branch in branches]
    if github_truth is not None and github_truth["status"] == "merged":
        return {**github_truth, "branches": branch_truths}
    for truth in branch_truths:
        if truth["status"] == "merged":
            return {**truth, "branches": branch_truths}
    if github_truth is not None:
        return {**github_truth, "branches": branch_truths}
    if branch_truths:
        return {
            "status": "unknown",
            "proof": "git_only_non_ancestor_or_missing_base",
            "confidence": "low",
            "reason": "git ancestry did not prove merge; without GitHub metadata this may be squash-merged or unmerged",
            "branches": branch_truths,
        }
    return {
        "status": "no_evidence",
        "proof": "no_branch_or_pr",
        "confidence": "none",
        "reason": "no task branch or PR metadata was found",
        "branches": [],
    }


def _current_aegis_work_summary(target_root: Path) -> dict[str, Any] | None:
    current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    if not isinstance(current_work, Mapping):
        return None
    task = current_work.get("task") if isinstance(current_work.get("task"), Mapping) else {}
    branch = current_work.get("branch") if isinstance(current_work.get("branch"), Mapping) else {}
    return {
        "status": str(current_work.get("status") or ""),
        "task_id": _numeric_task_id(task.get("id")),
        "task_status": str(task.get("status") or ""),
        "task_slug": str(task.get("slug") or ""),
        "branch": str(branch.get("current") or branch.get("name") or ""),
        "closeout_passed_at": current_work.get("closeout_passed_at"),
    }


def _local_aegis_task_stubs(target_root: Path) -> list[dict[str, Any]]:
    payload = _read_json(target_root / AEGIS_LOCAL_TASKS_REL)
    if not isinstance(payload, Mapping):
        return []
    stubs: list[dict[str, Any]] = []
    for task in payload.get("tasks", []):
        if not isinstance(task, Mapping):
            continue
        task_id = _numeric_task_id(task.get("id"))
        if task_id is None:
            continue
        stubs.append(
            {
                "id": task_id,
                "title": str(task.get("title") or f"Local task {task_id}"),
                "status": str(task.get("status") or "").lower(),
                "slug": str(task.get("slug") or ""),
                "source": str(task.get("source") or "aegis-local"),
            }
        )
    return stubs


def _reconcile_finding(
    kind: str,
    *,
    severity: str,
    task_id: str,
    message: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "severity": severity,
        "task_id": task_id,
        "message": message,
        "evidence": dict(evidence or {}),
    }


RECONCILE_PREVIEW_BLOCKED_REASON = "report-only per Task 147 contract"
RECONCILE_PREVIEW_ROLLBACK_CONTRACT_REL = "docs/aegis/reconcile-mutation-rollback-contract.md"
RECONCILE_PREVIEW_ACTUAL_BLAST_RADIUS_AUTHORITY = (
    "No live apply-time blast-radius oracle is wired; Task 145 is test-side proof only"
)


def _reconcile_finding_proof(finding: Mapping[str, Any]) -> str:
    evidence = finding.get("evidence") if isinstance(finding.get("evidence"), Mapping) else {}
    merge_truth = (
        evidence.get("merge_truth") if isinstance(evidence.get("merge_truth"), Mapping) else {}
    )
    return str(merge_truth.get("proof") or "")


def _taskmaster_generated_task_markdown_rel(task_id: str) -> str:
    try:
        suffix = f"{int(task_id):03d}"
    except ValueError:
        suffix = task_id
    return f".taskmaster/tasks/task_{suffix}.md"


def _reconcile_preview_exclusion(kind: str, proof: str) -> tuple[str, list[str]]:
    if kind == "merged_but_not_done" and proof == "github_pr_merged":
        return (
            "excluded from first candidate preview because GitHub/squash proof needs a separate contract",
            ["separate github_pr_merged precision, blast-radius, and rollback evidence"],
        )
    if kind == "done_but_not_merged":
        return (
            "excluded from first candidate preview because done-but-not-merged repair is a different mutation class",
            ["separate not-merged status correction contract"],
        )
    if kind in {
        "multi_pr_epic_ambiguity",
        "abandoned_in_progress_branch",
        "stale_local_stub",
        "local_ad_hoc_stub",
    }:
        return (
            "manual-only by reconcile precision contract",
            ["operator review outside reconcile mutation preview"],
        )
    if proof == "git_only_non_ancestor_or_missing_base":
        return (
            "excluded because git-only non-ancestor merge truth is unknown, not drift",
            ["positive merge proof from GitHub metadata or another separate proof contract"],
        )
    return (
        "excluded from first candidate preview by Task 147 boundary",
        ["separate precision, blast-radius, rollback, and inertness evidence"],
    )


def _reconcile_mutation_candidate_preview(findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for finding in findings:
        kind = str(finding.get("kind") or "")
        task_id = str(finding.get("task_id") or "")
        proof = _reconcile_finding_proof(finding)
        if kind == "merged_but_not_done" and proof == "git_ancestor":
            candidates.append(
                {
                    "record_type": "mutation_candidate",
                    "task_id": task_id,
                    "finding_kind": kind,
                    "proof": proof,
                    "executable": False,
                    "apply_path_exists": False,
                    "blocked_reason": RECONCILE_PREVIEW_BLOCKED_REASON,
                    "operator_confirmation_required": True,
                    "predicted_blast_radius_paths": [
                        ".taskmaster/tasks/tasks.json",
                        _taskmaster_generated_task_markdown_rel(task_id),
                    ],
                    "rollback_contract": {
                        "path": RECONCILE_PREVIEW_ROLLBACK_CONTRACT_REL,
                        "requires_before_snapshot": True,
                        "requires_before_audit_breadcrumb": True,
                        "requires_after_audit_breadcrumb": True,
                        "requires_rollback_verification": True,
                    },
                    "actual_blast_radius_authority": RECONCILE_PREVIEW_ACTUAL_BLAST_RADIUS_AUTHORITY,
                    "prediction_authority": "Task 147 isolated Taskmaster done-cascade inventory",
                    "candidate_boundary": "only merged_but_not_done with git_ancestor proof",
                }
            )
            continue

        reason, would_require = _reconcile_preview_exclusion(kind, proof)
        excluded.append(
            {
                "record_type": "contract_exclusion",
                "task_id": task_id,
                "class": kind,
                "proof": proof or None,
                "reason": reason,
                "would_require": would_require,
                "manual_only": kind
                in {
                    "multi_pr_epic_ambiguity",
                    "abandoned_in_progress_branch",
                    "stale_local_stub",
                    "local_ad_hoc_stub",
                },
            }
        )
    return {
        "enabled": True,
        "read_only": True,
        "executable": False,
        "apply_path_exists": False,
        "blocked_reason": RECONCILE_PREVIEW_BLOCKED_REASON,
        "candidates": candidates,
        "excluded": excluded,
        "notes": [
            "This opt-in preview is inert data for operator review, not an execution surface.",
            "A future live mutation task must add a separate apply-time side-effect oracle before claiming actual mutation-time blast-radius verification.",
        ],
    }


def reconcile(
    target_dir: str | Path,
    *,
    source_root: str | Path | None = None,
    base_ref: str | None = None,
    use_github: bool = True,
    preview_candidates: bool = False,
) -> dict[str, Any]:
    """Report Taskmaster/Aegis/git/PR drift without mutating any repository state."""

    target_root = _resolve_target_root(target_dir)
    _ensure_git_work_tree(target_root)
    taskmaster = _taskmaster_state(target_root)
    tasks = _taskmaster_tasks_by_id_from_state(taskmaster)
    branches = _reconcile_branch_candidates(target_root)
    branches_by_task: dict[str, list[dict[str, Any]]] = {}
    for branch in branches:
        branches_by_task.setdefault(str(branch["task_id"]), []).append(branch)
    gh = (
        _run_gh_pr_list(target_root)
        if use_github
        else {"available": False, "reason": "disabled", "prs": []}
    )
    prs_by_task = _prs_by_task_id(gh)
    base = _resolve_reconcile_base_ref(target_root, base_ref)
    current_work = _current_aegis_work_summary(target_root)
    active_task_id = (
        current_work.get("task_id")
        if current_work and current_work.get("status") == "in-progress"
        else None
    )
    try:
        current_branch = _current_branch(target_root)
    except AegisError:
        current_branch = ""
    current_branch_task_id = _branch_task_id(current_branch)
    local_stubs = _local_aegis_task_stubs(target_root)
    if taskmaster.state == "invalid":
        all_task_ids: list[str] = []
    else:
        all_task_ids = sorted(
            set(tasks)
            | set(branches_by_task)
            | set(prs_by_task)
            | {stub["id"] for stub in local_stubs},
            key=lambda item: int(item),
        )

    task_reports: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    if taskmaster.state == "invalid":
        findings.append(
            _reconcile_finding(
                "taskmaster_invalid",
                severity="warning",
                task_id="",
                message=(
                    f"{TASKMASTER_TASKS_REL} is present but invalid; repair Taskmaster "
                    "before deriving task/branch drift"
                ),
                evidence=taskmaster.details(),
            )
        )
    done_statuses = {"done", "completed"}
    for task_id in all_task_ids:
        task = tasks.get(task_id)
        task_status = str(task.get("status") if task else "missing")
        task_branches = branches_by_task.get(task_id, [])
        task_prs = prs_by_task.get(task_id, [])
        merge_truth = _task_merge_truth(target_root, task_branches, task_prs, base)
        report = {
            "task_id": task_id,
            "task": task,
            "taskmaster_status": task_status,
            "branches": task_branches,
            "pull_requests": task_prs,
            "merge_truth": merge_truth,
            "active_aegis_current_work": active_task_id == task_id,
        }
        task_reports.append(report)

        if task is None:
            for branch in task_branches:
                findings.append(
                    _reconcile_finding(
                        "stale_local_stub",
                        severity="warning",
                        task_id=task_id,
                        message=f"branch {branch['name']} references task {task_id}, but Taskmaster has no such task",
                        evidence={"branch": branch},
                    )
                )
            for stub in [stub for stub in local_stubs if stub["id"] == task_id]:
                findings.append(
                    _reconcile_finding(
                        "local_ad_hoc_stub",
                        severity="warning",
                        task_id=task_id,
                        message=f"Aegis local task {task_id} exists without a Taskmaster task",
                        evidence={"local_task": stub},
                    )
                )
            continue

        if len(task_prs) > 1:
            findings.append(
                _reconcile_finding(
                    "multi_pr_epic_ambiguity",
                    severity="warning",
                    task_id=task_id,
                    message=f"task {task_id} has {len(task_prs)} PR candidates; merge truth requires review",
                    evidence={"pull_requests": task_prs},
                )
            )
        if task_status not in done_statuses and merge_truth["status"] == "merged":
            findings.append(
                _reconcile_finding(
                    "merged_but_not_done",
                    severity="error",
                    task_id=task_id,
                    message=f"task {task_id} is {task_status}, but merge truth says merged",
                    evidence={"merge_truth": merge_truth},
                )
            )
        if task_status in done_statuses and merge_truth["status"] == "not_merged":
            findings.append(
                _reconcile_finding(
                    "done_but_not_merged",
                    severity="error",
                    task_id=task_id,
                    message=f"task {task_id} is {task_status}, but PR metadata says it is not merged",
                    evidence={"merge_truth": merge_truth},
                )
            )
        if (
            task_status == "in-progress"
            and task_branches
            and active_task_id != task_id
            and current_branch_task_id != task_id
        ):
            findings.append(
                _reconcile_finding(
                    "abandoned_in_progress_branch",
                    severity="warning",
                    task_id=task_id,
                    message=f"task {task_id} is in-progress with task branches but no matching active Aegis current work",
                    evidence={"branches": task_branches, "active_aegis_task_id": active_task_id},
                )
            )

    severity_counts = {
        severity: sum(1 for finding in findings if finding["severity"] == severity)
        for severity in ("error", "warning", "info")
    }
    status_value = (
        "drift"
        if severity_counts["error"]
        else "needs_review" if severity_counts["warning"] else "clean"
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status_value,
        "read_only": True,
        "generated_at": _iso_now(),
        "target_root": target_root.as_posix(),
        "source_root": Path(source_root).resolve().as_posix() if source_root is not None else None,
        "base_ref": base,
        "github": {
            "enabled": bool(use_github),
            "available": bool(gh.get("available")),
            "reason": gh.get("reason") or "",
            "pr_count": len(gh.get("prs", [])),
        },
        "taskmaster": {
            **taskmaster.details(),
            "path": TASKMASTER_TASKS_REL,
            "available": taskmaster.state == "valid",
            "task_count": len(tasks),
        },
        "active_aegis_current_work": current_work,
        "tasks": task_reports,
        "findings": findings,
        "summary": {
            "tasks_checked": len(task_reports),
            "findings": len(findings),
            "errors": severity_counts["error"],
            "warnings": severity_counts["warning"],
            "info": severity_counts["info"],
        },
        "notes": [
            "This command is read-only and never mutates Taskmaster, Aegis state, git refs, or PRs.",
            "Git ancestry proves true merges and fast-forwards; non-ancestor branches are reported as unknown without GitHub merge metadata because squash merges are possible.",
            "GitHub PR state is optional acceleration; when unavailable, squash-ambiguous cases remain unknown instead of being reported as not merged.",
        ],
    }
    if preview_candidates:
        preview = _reconcile_mutation_candidate_preview(findings)
        report["mutation_candidate_preview"] = preview
        report["summary"]["mutation_candidates"] = len(preview["candidates"])
        report["summary"]["mutation_candidate_exclusions"] = len(preview["excluded"])
    return report


def format_reconcile_summary(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    lines = [
        f"Aegis reconcile: {str(report.get('status') or 'unknown').upper()}",
        f"target: {report.get('target_root')}",
        f"base_ref: {report.get('base_ref', {}).get('selected') if isinstance(report.get('base_ref'), Mapping) else None}",
        (
            "summary: "
            f"{summary.get('tasks_checked', 0)} tasks, "
            f"{summary.get('findings', 0)} findings "
            f"({summary.get('errors', 0)} errors, {summary.get('warnings', 0)} warnings, {summary.get('info', 0)} info)"
        ),
    ]
    github = report.get("github") if isinstance(report.get("github"), Mapping) else {}
    lines.append(
        "github: "
        + (
            f"available ({github.get('pr_count', 0)} PRs scanned)"
            if github.get("available")
            else f"unavailable/disabled ({github.get('reason') or 'no reason reported'})"
        )
    )
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    if findings:
        lines.append("findings:")
        for finding in findings[:20]:
            if not isinstance(finding, Mapping):
                continue
            lines.append(
                f"- [{finding.get('severity')}] {finding.get('kind')} task {finding.get('task_id')}: "
                f"{finding.get('message')}"
            )
        if len(findings) > 20:
            lines.append(
                f"- ... {len(findings) - 20} more finding(s); rerun with --json for full detail"
            )
    else:
        lines.append("findings: none")
    preview = (
        report.get("mutation_candidate_preview")
        if isinstance(report.get("mutation_candidate_preview"), Mapping)
        else None
    )
    if preview:
        lines.append(
            "mutation_candidate_preview: "
            f"report-only, executable=false, candidates={len(preview.get('candidates', []))}, "
            f"excluded={len(preview.get('excluded', []))}"
        )
    lines.append("")
    return "\n".join(lines)


def _ensure_task_branch(
    target_root: Path, task_id: str, slug: str, *, create_branch: bool
) -> dict[str, Any]:
    before = _current_branch(target_root)
    if _branch_task_id(before) == task_id:
        return {
            "before": before,
            "current": before,
            "action": "already_on_task_branch",
            "created": False,
        }
    if not create_branch:
        raise AegisError(
            f"current branch '{before}' does not contain task id {task_id}; rerun with branch creation enabled"
        )

    branch_name = f"feat/task-{task_id}-{slug}"
    exists = _run_target_git(target_root, "rev-parse", "--verify", "--quiet", branch_name)
    if exists.returncode == 0:
        switch = _run_target_git(target_root, "switch", branch_name)
        action = "switched_existing_branch"
        created = False
    else:
        switch = _run_target_git(target_root, "switch", "-c", branch_name)
        action = "created_branch"
        created = True
    if switch.returncode != 0:
        detail = (switch.stderr or switch.stdout or "git switch failed").strip()
        raise AegisError(f"could not switch to task branch '{branch_name}': {detail}")
    return {
        "before": before,
        "current": _current_branch(target_root),
        "action": action,
        "created": created,
    }


def _ensure_bead_branch(
    target_root: Path, bead_id: str, slug: str, *, create_branch: bool
) -> dict[str, Any]:
    before = _current_branch(target_root)
    if _branch_bead_id(before, expected_id=bead_id) == bead_id:
        return {
            "before": before,
            "current": before,
            "action": "already_on_bead_branch",
            "created": False,
        }
    if not create_branch:
        raise AegisError(
            f"current branch '{before}' does not contain bead id {bead_id}; "
            "rerun with branch creation enabled"
        )

    branch_name = f"codex/{bead_id}-{slug}"
    exists = _run_target_git(target_root, "rev-parse", "--verify", "--quiet", branch_name)
    if exists.returncode == 0:
        switch = _run_target_git(target_root, "switch", branch_name)
        action = "switched_existing_branch"
        created = False
    else:
        switch = _run_target_git(target_root, "switch", "-c", branch_name)
        action = "created_branch"
        created = True
    if switch.returncode != 0:
        detail = (switch.stderr or switch.stdout or "git switch failed").strip()
        raise AegisError(f"could not switch to bead branch '{branch_name}': {detail}")
    return {
        "before": before,
        "current": _current_branch(target_root),
        "action": action,
        "created": created,
    }


def _replace_symlink(link: Path, target: str) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        if not link.is_symlink():
            raise AegisError(f"cannot replace non-symlink current pointer: {link}")
        link.unlink()
    link.symlink_to(target)


def _next_session_rel(
    target_root: Path,
    task_id: str,
    slug: str,
    now: datetime,
    *,
    work_mode: str = "task",
) -> str:
    date_text = now.strftime("%Y-%m-%d")
    month_rel = Path("sessions") / now.strftime("%Y") / now.strftime("%m")
    identity = f"task{task_id}" if work_mode == "task" else task_id
    for index in range(1, 1000):
        candidate = month_rel / f"{date_text}-{index:03d}-{identity}-{slug}.md"
        if not (target_root / candidate).exists():
            return candidate.as_posix()
    raise AegisError("could not allocate session file name")


def _plan_rel(task_id: str, slug: str, now: datetime, *, work_mode: str = "task") -> str:
    identity = f"task{task_id}" if work_mode == "task" else task_id
    return f"plans/{now.strftime('%Y-%m-%d')}-{identity}-{slug}.md"


def _work_tracking_rel(task_id: str, slug: str, now: datetime, *, work_mode: str = "task") -> str:
    identity = f"task{task_id}" if work_mode == "task" else task_id
    return f"docs/ai/work-tracking/active/{now.strftime('%Y%m%d')}-{identity}-{slug}-ACTIVE"


def _normalize_observation_slug(slug: str, title: str) -> str:
    normalized = _slugify(slug or title)
    if not normalized:
        raise AegisError("observation title or slug is required")
    return normalized


def _observation_id(slug: str, now: datetime) -> str:
    return f"obs-{now.strftime('%Y%m%d-%H%M%S')}-{slug}"


def _observation_session_rel(target_root: Path, observation_id: str, now: datetime) -> str:
    date_text = now.strftime("%Y-%m-%d")
    month_rel = Path("sessions") / now.strftime("%Y") / now.strftime("%m")
    for index in range(1, 1000):
        candidate = month_rel / f"{date_text}-{index:03d}-{observation_id}.md"
        if not (target_root / candidate).exists():
            return candidate.as_posix()
    raise AegisError("could not allocate observation session file name")


def _observation_plan_rel(slug: str, now: datetime) -> str:
    return f"plans/{now.strftime('%Y-%m-%d')}-observe-{slug}.md"


def _observation_work_tracking_rel(slug: str, now: datetime) -> str:
    return f"docs/ai/work-tracking/active/{now.strftime('%Y%m%d')}-observe-{slug}-ACTIVE"


def _is_safe_relative_rel(rel_path: str) -> bool:
    path = Path(rel_path)
    return bool(rel_path) and not path.is_absolute() and ".." not in path.parts


def _completed_work_tracking_archive_rel(work_rel: str) -> str:
    if not _is_safe_relative_rel(work_rel):
        return ""
    active_prefix = "docs/ai/work-tracking/active/"
    if not work_rel.startswith(active_prefix):
        return ""
    name = Path(work_rel).name
    if not name.endswith("-ACTIVE"):
        return ""
    archive_name = f"{name[: -len('-ACTIVE')]}-COMPLETED"
    return f"docs/ai/work-tracking/archive/{archive_name}"


def _completed_observation_work_tracking_archive_rel(work_rel: str) -> str:
    return _completed_work_tracking_archive_rel(work_rel)


def _is_observation_active_work_tracking_rel(work_rel: str) -> bool:
    archive_rel = _completed_observation_work_tracking_archive_rel(work_rel)
    if not archive_rel:
        return False
    return "-observe-" in Path(work_rel).name


def _is_task_active_work_tracking_rel(work_rel: str) -> bool:
    archive_rel = _completed_work_tracking_archive_rel(work_rel)
    if not archive_rel:
        return False
    return re.search(r"(?:^|-)task\d+(?:-|$)", Path(work_rel).name) is not None


def _unique_work_tracking_archive_rel(target_root: Path, archive_rel: str) -> str:
    archive_path = target_root / archive_rel
    if not archive_path.exists():
        return archive_rel
    parent = archive_path.parent
    name = archive_path.name
    for index in range(2, 1000):
        candidate = parent / f"{name}-{index}"
        if not candidate.exists():
            return candidate.relative_to(target_root).as_posix()
    raise AegisError(f"could not allocate completed observation archive path for {archive_rel}")


def _replace_work_tracking_path_prefix(paths: MutableMapping[str, Any], old: str, new: str) -> None:
    for key in ("work_tracking", "reports"):
        value = str(paths.get(key) or "")
        if value == old:
            paths[key] = new
        elif value.startswith(f"{old}/"):
            paths[key] = f"{new}{value[len(old) :]}"


def _archive_completed_observation_work_tracking_path(
    target_root: Path,
    work_rel: str,
) -> dict[str, str] | None:
    archive_rel = _completed_work_tracking_archive_rel(work_rel)
    if not archive_rel:
        return None
    source = target_root / work_rel
    if not source.is_dir():
        return None
    actual_archive_rel = _unique_work_tracking_archive_rel(target_root, archive_rel)
    destination = target_root / actual_archive_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return {"from": work_rel, "to": actual_archive_rel}


def _archive_completed_work_tracking_path(
    target_root: Path,
    work_rel: str,
) -> dict[str, str] | None:
    return _archive_completed_observation_work_tracking_path(target_root, work_rel)


def _archive_current_completed_work_tracking(
    target_root: Path,
    current_work: MutableMapping[str, Any],
) -> dict[str, str] | None:
    paths = (
        current_work.get("paths") if isinstance(current_work.get("paths"), MutableMapping) else None
    )
    if paths is None:
        return None
    work_rel = str(paths.get("work_tracking") or "").strip()
    archived = _archive_completed_work_tracking_path(target_root, work_rel)
    if archived is None:
        return None
    _replace_work_tracking_path_prefix(paths, archived["from"], archived["to"])
    return archived


def _archive_current_completed_observation_work_tracking(
    target_root: Path,
    current_work: MutableMapping[str, Any],
) -> dict[str, str] | None:
    if str(current_work.get("mode") or "") != "observation":
        return None
    if str(current_work.get("status") or "") != "completed":
        return None
    paths = (
        current_work.get("paths") if isinstance(current_work.get("paths"), MutableMapping) else None
    )
    if paths is None:
        return None
    work_rel = str(paths.get("work_tracking") or "").strip()
    archived = _archive_completed_observation_work_tracking_path(target_root, work_rel)
    if archived is None:
        return None
    _replace_work_tracking_path_prefix(paths, archived["from"], archived["to"])
    return archived


def _update_observation_report_archived_work_tracking(
    target_root: Path,
    archived: Mapping[str, str],
) -> None:
    report_path = target_root / AEGIS_OBSERVATION_REPORT_REL
    report = _read_json(report_path)
    if not isinstance(report, MutableMapping):
        return
    paths = report.get("paths") if isinstance(report.get("paths"), MutableMapping) else None
    if paths is not None:
        _replace_work_tracking_path_prefix(paths, str(archived["from"]), str(archived["to"]))
    report["archived_work_tracking"] = dict(archived)
    report_path.write_text(_dump_json(report), encoding="utf-8")


def _git_status_snapshot(target_root: Path) -> list[str]:
    result = _run_target_git(target_root, "status", "--short", "--untracked-files=all", "--ignored")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git status failed").strip()
        raise AegisError(f"could not snapshot git status: {detail}")
    return [line.rstrip() for line in result.stdout.splitlines() if line.strip()]


def _hash_file(path: Path, *, byte_limit: int | None = None) -> tuple[str, int, bool]:
    digest = hashlib.sha256()
    total = 0
    truncated = False
    with path.open("rb") as handle:
        while True:
            chunk_size = 1024 * 1024
            if byte_limit is not None:
                remaining = byte_limit - total
                if remaining <= 0:
                    truncated = True
                    break
                chunk_size = min(chunk_size, remaining)
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total, truncated


def _fingerprint_status_path(path: Path) -> str:
    if path.is_symlink():
        try:
            return f"symlink:{path.readlink().as_posix()}"
        except OSError as exc:
            return f"symlink-error:{exc}"
    if path.is_file():
        try:
            digest, size, truncated = _hash_file(
                path,
                byte_limit=AEGIS_OBSERVATION_FINGERPRINT_MAX_BYTES,
            )
            return f"file:{size}:{digest}:truncated={str(truncated).lower()}"
        except OSError as exc:
            return f"file-error:{exc}"
    if path.is_dir():
        digest = hashlib.sha256()
        files_seen = 0
        bytes_seen = 0
        truncated = False
        try:
            children = sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix())
            for child in children:
                rel_child = child.relative_to(path).as_posix()
                if child.is_dir() and not child.is_symlink():
                    digest.update(f"D\t{rel_child}\n".encode("utf-8"))
                    continue
                files_seen += 1
                if files_seen > AEGIS_OBSERVATION_FINGERPRINT_MAX_FILES:
                    truncated = True
                    break
                if child.is_symlink():
                    digest.update(
                        f"L\t{rel_child}\t{child.readlink().as_posix()}\n".encode("utf-8")
                    )
                    continue
                if not child.is_file():
                    digest.update(f"O\t{rel_child}\n".encode("utf-8"))
                    continue
                remaining = AEGIS_OBSERVATION_FINGERPRINT_MAX_BYTES - bytes_seen
                if remaining <= 0:
                    truncated = True
                    break
                child_hash, child_bytes, child_truncated = _hash_file(child, byte_limit=remaining)
                bytes_seen += child_bytes
                truncated = truncated or child_truncated
                digest.update(f"F\t{rel_child}\t{child_bytes}\t{child_hash}\n".encode("utf-8"))
                if truncated:
                    break
        except OSError as exc:
            return f"dir-error:{exc}"
        return (
            f"dir:{files_seen}:{bytes_seen}:{digest.hexdigest()}:truncated={str(truncated).lower()}"
        )
    if path.exists():
        return "other"
    return "missing"


def _git_status_rel_path(line: str) -> str:
    body = line[3:] if len(line) > 3 else line
    if " -> " in body:
        body = body.rsplit(" -> ", 1)[-1]
    return body.strip().strip('"')


def _git_status_fingerprints(target_root: Path, status_lines: Sequence[str]) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for line in status_lines:
        rel_path = _git_status_rel_path(str(line))
        if not rel_path:
            continue
        path = target_root / rel_path
        fingerprints[rel_path] = _fingerprint_status_path(path)
    return fingerprints


def _observation_allowed_prefixes(current_work: Mapping[str, Any]) -> list[str]:
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    observation = (
        current_work.get("observation")
        if isinstance(current_work.get("observation"), Mapping)
        else {}
    )
    prefixes = {
        AEGIS_CURRENT_WORK_REL,
        AEGIS_MANIFEST_REL,
        AEGIS_OBSERVATION_REPORT_REL,
        AEGIS_OBSERVATION_REPORT_DETAIL_REL,
        AEGIS_OBSERVATION_BASELINE_REL,
        "sessions/state.json",
        "sessions/current",
        "plans/current",
    }
    for key in ("session", "plan", "work_tracking", "reports"):
        value = str(paths.get(key) or "").strip()
        if value:
            prefixes.add(value.rstrip("/"))
    artifact_root = str(
        paths.get("observation_artifacts") or observation.get("artifact_root") or ""
    ).strip()
    if artifact_root:
        prefixes.add(artifact_root.rstrip("/"))
    else:
        observation_id = str(observation.get("id") or "").strip()
        if observation_id:
            prefixes.add(
                f"{AEGIS_OBSERVATION_ARTIFACT_ROOT_REL}/{_slugify(observation_id)}/artifacts"
            )
    return sorted(prefixes)


def _rel_path_matches_prefix(rel_path: str, prefix: str) -> bool:
    rel_path = rel_path.rstrip("/")
    normalized = prefix.rstrip("/")
    return rel_path == normalized or rel_path.startswith(f"{normalized}/")


def _status_line_matches_prefix(line: str, prefix: str) -> bool:
    return _rel_path_matches_prefix(_git_status_rel_path(line), prefix)


def _observation_budget_config(target_root: Path) -> dict[str, Any]:
    """TM #197: report summarization budgets, extensible via brief.json."""

    brief = _read_json(target_root / AEGIS_BRIEF_REL)
    section = brief.get("observation") if isinstance(brief, Mapping) else None
    section = section if isinstance(section, Mapping) else {}

    def _int_or(value: Any, default: int) -> int:
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return default

    return {
        "sample_cap": _int_or(section.get("sample_cap"), OBSERVATION_SAMPLE_CAP_DEFAULT),
        "prefix_cap": _int_or(section.get("prefix_cap"), OBSERVATION_PREFIX_CAP_DEFAULT),
    }


def _summarize_path_lines(lines: Sequence[str], config: Mapping[str, Any]) -> dict[str, Any]:
    """Capped sample + counts by path prefix + truncation marker (TM #197)."""

    sample_cap = int(config.get("sample_cap") or OBSERVATION_SAMPLE_CAP_DEFAULT)
    prefix_cap = int(config.get("prefix_cap") or OBSERVATION_PREFIX_CAP_DEFAULT)
    texts = [str(line).rstrip() for line in lines if str(line).strip()]
    by_prefix: dict[str, int] = {}
    for text in texts:
        rel = _git_status_rel_path(text) or text
        parts = rel.strip("/").split("/")
        prefix = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
    top_prefixes = dict(sorted(by_prefix.items(), key=lambda item: -item[1])[:prefix_cap])
    return {
        "total": len(texts),
        "sample": texts[:sample_cap],
        "by_prefix": top_prefixes,
        "prefixes_truncated": len(by_prefix) > prefix_cap,
        "truncated": len(texts) > sample_cap,
    }


def _load_observation_baseline(target_root: Path, current_work: MutableMapping[str, Any]) -> None:
    """Hydrate full baseline lists from the baseline artifact file (TM #197).

    current-work.json carries only a baseline_ref + summary so guidance payloads stay
    small; the comparison logic keeps reading the inline fields, which this loader
    restores in memory. Legacy state with inline baselines is untouched.
    """

    observation = current_work.get("observation")
    if not isinstance(observation, MutableMapping):
        return
    if observation.get("baseline_git_status") or observation.get("baseline_git_fingerprints"):
        return
    ref = observation.get("baseline_ref")
    if not isinstance(ref, str) or not ref:
        return
    baseline = _read_json(target_root / ref)
    if not isinstance(baseline, Mapping):
        return
    status = baseline.get("baseline_git_status")
    fingerprints = baseline.get("baseline_git_fingerprints")
    if isinstance(status, list):
        observation["baseline_git_status"] = [str(line) for line in status]
    if isinstance(fingerprints, Mapping):
        observation["baseline_git_fingerprints"] = {
            str(key): str(value) for key, value in fingerprints.items()
        }
    if "gate_audit" in baseline:
        observation["gate_audit"] = baseline["gate_audit"]


def _observation_status_delta_lines(
    current_work: Mapping[str, Any],
    current_status: Sequence[str],
) -> list[str]:
    observation = (
        current_work.get("observation")
        if isinstance(current_work.get("observation"), Mapping)
        else {}
    )
    baseline = {
        str(line).rstrip()
        for line in observation.get("baseline_git_status", [])
        if isinstance(line, str) and line.strip()
    }
    allowed_prefixes = _observation_allowed_prefixes(current_work)
    deltas: list[str] = []
    for line in current_status:
        stripped = str(line).rstrip()
        if not stripped or stripped in baseline:
            continue
        if any(_status_line_matches_prefix(stripped, prefix) for prefix in allowed_prefixes):
            continue
        deltas.append(stripped)
    return deltas


def _observation_fingerprint_delta_lines(
    current_work: Mapping[str, Any],
    current_fingerprints: Mapping[str, str],
) -> list[str]:
    observation = (
        current_work.get("observation")
        if isinstance(current_work.get("observation"), Mapping)
        else {}
    )
    baseline_fingerprints = (
        observation.get("baseline_git_fingerprints")
        if isinstance(observation.get("baseline_git_fingerprints"), Mapping)
        else {}
    )
    allowed_prefixes = _observation_allowed_prefixes(current_work)
    deltas: list[str] = []
    for rel_path, baseline_fingerprint in sorted(baseline_fingerprints.items()):
        rel_text = str(rel_path)
        if any(
            rel_text == prefix.rstrip("/") or rel_text.startswith(f"{prefix.rstrip('/')}/")
            for prefix in allowed_prefixes
        ):
            continue
        current_fingerprint = current_fingerprints.get(rel_text)
        if current_fingerprint is None:
            deltas.append(f"removed status-visible path: {rel_text}")
        elif current_fingerprint != baseline_fingerprint:
            deltas.append(f"changed status-visible path: {rel_text}")
    return deltas


def _unexpected_observation_status_lines(
    current_work: Mapping[str, Any],
    current_status: Sequence[str],
    current_fingerprints: Mapping[str, str],
) -> list[str]:
    unexpected: list[str] = []
    unexpected.extend(_observation_status_delta_lines(current_work, current_status))
    unexpected.extend(_observation_fingerprint_delta_lines(current_work, current_fingerprints))
    return unexpected


def _observation_ignored_status_rels(status_lines: Sequence[str]) -> list[str]:
    rels: list[str] = []
    for line in status_lines:
        stripped = str(line).rstrip()
        if not stripped.startswith("!! "):
            continue
        rel_path = _git_status_rel_path(stripped).rstrip("/")
        if rel_path:
            rels.append(rel_path)
    return rels


def _observation_runtime_rel(rel_path: str) -> str | None:
    normalized = rel_path.rstrip("/")
    if any(
        _rel_path_matches_prefix(normalized, prefix)
        for prefix in AEGIS_OBSERVATION_RUNTIME_PREFIXES
    ):
        return normalized
    return None


def _observation_runtime_status_delta_lines(
    status_delta_lines: Sequence[str],
) -> list[str]:
    allowed: list[str] = []
    for line in status_delta_lines:
        stripped = str(line).rstrip()
        if not stripped.startswith("!! "):
            continue
        if _observation_runtime_rel(_git_status_rel_path(stripped)):
            allowed.append(stripped)
    return allowed


def _observation_fingerprint_delta_rel(line: str) -> str | None:
    stripped = str(line).rstrip()
    for prefix in ("changed status-visible path: ", "removed status-visible path: "):
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip().rstrip("/") or None
    return None


def _observation_runtime_fingerprint_delta_lines(
    current_work: Mapping[str, Any],
    fingerprint_delta_lines: Sequence[str],
) -> list[str]:
    observation = (
        current_work.get("observation")
        if isinstance(current_work.get("observation"), Mapping)
        else {}
    )
    ignored_baseline_rels = _observation_ignored_status_rels(
        [
            str(line)
            for line in observation.get("baseline_git_status", [])
            if isinstance(line, str) and line.strip()
        ]
    )
    allowed: list[str] = []
    for line in fingerprint_delta_lines:
        stripped = str(line).rstrip()
        rel_path = _observation_fingerprint_delta_rel(stripped)
        if not rel_path or not _observation_runtime_rel(rel_path):
            continue
        if any(_rel_path_matches_prefix(rel_path, ignored) for ignored in ignored_baseline_rels):
            allowed.append(stripped)
    return allowed


def _observation_artifact_root_rel(current_work: Mapping[str, Any]) -> str:
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    observation = (
        current_work.get("observation")
        if isinstance(current_work.get("observation"), Mapping)
        else {}
    )
    configured = str(
        paths.get("observation_artifacts") or observation.get("artifact_root") or ""
    ).strip()
    if configured:
        return configured.strip("/")
    observation_id = str(observation.get("id") or "unknown-observation")
    return f"{AEGIS_OBSERVATION_ARTIFACT_ROOT_REL}/{_slugify(observation_id)}/artifacts"


def _observation_artifact_source_rel(line: str) -> str | None:
    stripped = str(line).rstrip()
    if not (stripped.startswith("?? ") or stripped.startswith("!! ")):
        return None
    rel_path = _git_status_rel_path(stripped).rstrip("/")
    if not rel_path:
        return None
    first_part = rel_path.split("/", 1)[0]
    if first_part in AEGIS_OBSERVATION_ARTIFACT_DIRS:
        return first_part
    if "/" not in rel_path and any(
        fnmatch.fnmatchcase(rel_path, pattern)
        for pattern in AEGIS_OBSERVATION_ROOT_SCREENSHOT_PATTERNS
    ):
        return rel_path
    return None


def _observation_cleanable_artifact_rels(
    target_root: Path,
    status_delta_lines: Sequence[str],
    artifact_root_rel: str,
) -> list[str]:
    candidates: set[str] = set()
    normalized_root = artifact_root_rel.rstrip("/")
    for line in status_delta_lines:
        rel_path = _observation_artifact_source_rel(str(line))
        if not rel_path:
            continue
        if rel_path == normalized_root or rel_path.startswith(f"{normalized_root}/"):
            continue
        source = target_root / rel_path
        if source.is_symlink():
            continue
        if not source.exists():
            continue
        candidates.add(rel_path)
    return sorted(candidates)


def _unique_observation_artifact_destination(artifact_root: Path, name: str) -> Path:
    candidate = artifact_root / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(2, 1000):
        alternative = artifact_root / f"{stem}-{index}{suffix}"
        if not alternative.exists():
            return alternative
    raise AegisError(f"could not allocate observation artifact destination for {name}")


def _collect_observation_artifacts(
    target_root: Path,
    artifact_root_rel: str,
    cleanable_artifact_rels: Sequence[str],
) -> list[dict[str, str]]:
    artifact_root = target_root / artifact_root_rel
    artifact_root.mkdir(parents=True, exist_ok=True)
    collected: list[dict[str, str]] = []
    for rel_path in cleanable_artifact_rels:
        source = target_root / rel_path
        if source.is_symlink():
            raise AegisError(f"refusing to collect symlink observation artifact: {rel_path}")
        if not source.exists():
            continue
        destination = _unique_observation_artifact_destination(artifact_root, source.name)
        source.rename(destination)
        collected.append(
            {
                "from": rel_path,
                "to": destination.relative_to(target_root).as_posix(),
            }
        )
    return collected


def _default_goals() -> list[str]:
    return [
        "Define scope and constraints before implementation",
        "Implement only task-scoped changes",
        "Verify behavior with captured evidence before completion",
    ]


def _read_workflow_template(target_root: Path, source_root: Path | None, template_name: str) -> str:
    candidates: list[Path] = []
    if source_root is not None:
        candidates.append(source_root / AEGIS_WORKFLOW_TEMPLATE_SOURCE_ROOT / template_name)
    candidates.append(target_root / AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT / template_name)
    candidates.append(_REPO_ROOT / AEGIS_WORKFLOW_TEMPLATE_SOURCE_ROOT / template_name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    raise AegisError(f"Required workflow template is missing: {template_name}")


def _render_workflow_template(
    target_root: Path,
    source_root: Path | None,
    template_name: str,
    context: Mapping[str, str],
) -> str:
    rendered = _read_workflow_template(target_root, source_root, template_name)
    for key, value in sorted(context.items(), key=lambda item: len(item[0]), reverse=True):
        rendered = rendered.replace("{{" + key + "}}", value)
    unresolved = sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", rendered)))
    if unresolved:
        raise AegisError(
            f"Workflow template {template_name} has unresolved variable(s): {', '.join(unresolved)}"
        )
    return rendered.rstrip() + "\n"


def _workflow_template_context(
    *,
    task_id: str,
    title: str,
    slug: str,
    goals: Sequence[str],
    now: datetime,
    branch_current: str,
    session_rel: str,
    plan_rel: str,
    work_rel: str,
    reports_rel: str,
    work_context: str | None = None,
    work_mode: str = "task",
) -> dict[str, str]:
    if work_mode not in {"task", "bead"}:
        raise AegisError(f"unsupported workflow template mode: {work_mode}")
    selected_goals = list(goals or _default_goals())
    session_id = Path(session_rel).stem
    is_bead = work_mode == "bead"
    work_kind = "Bead" if is_bead else "Task"
    work_kind_lower = work_kind.lower()
    work_label = f"{work_kind} {task_id}"
    resolved_work_context = work_context or (
        f"{task_id}-{slug}" if is_bead else f"task{task_id}-{slug}"
    )
    tracker_rel = f"{work_rel}/TRACKER.md"
    return {
        "task_id": task_id,
        "work_id": task_id,
        "work_mode": work_mode,
        "work_kind": work_kind,
        "work_kind_lower": work_kind_lower,
        "work_label": work_label,
        "identity_frontmatter_key": "bead_ids" if is_bead else "task_ids",
        "identity_header": "Bead IDs" if is_bead else "Task IDs",
        "branch_policy": branch_current if is_bead else "feature-required",
        "branch_requirement": (
            f"the bead branch `{branch_current}`"
            if is_bead
            else f"a branch containing `task-{task_id}`"
        ),
        "work_scope": f"{work_label} only",
        "authority_summary": (
            f"Gas City bead `{task_id}` plus Aegis current-work state"
            if is_bead
            else "Aegis-native workflow state"
        ),
        "integration_summary": (
            "Taskmaster is historical read-only compatibility; Serena is optional continuity only."
            if is_bead
            else "Taskmaster and Serena may be used when present, but are not required for READY unless this task marks them required."
        ),
        "title": title,
        "slug": slug,
        "session_id": session_id,
        "session_value": now.strftime("%Y%m%d"),
        "work_context": resolved_work_context,
        "date": now.strftime("%Y-%m-%d"),
        "time_label": now.strftime("%H:%M %Z").strip(),
        "time_hm": now.strftime("%H:%M"),
        "timestamp_full": now.strftime("%Y-%m-%d %H:%M:%S %Z %z").strip(),
        "timestamp_tracker": now.strftime("%Y-%m-%d %H:%M %Z").strip(),
        "created_at": now.isoformat(),
        "branch_current": branch_current,
        "current_work_rel": AEGIS_CURRENT_WORK_REL,
        "session_rel": session_rel,
        "plan_rel": plan_rel,
        "work_rel": work_rel,
        "tracker_rel": tracker_rel,
        "reports_rel": reports_rel,
        "goals_checklist": "\n".join(f"- [ ] {goal}" for goal in selected_goals),
        "goals_bullets": "\n".join(f"- {goal}" for goal in selected_goals),
    }


def _write_text(target_root: Path, rel_path: str, content: str) -> None:
    path = target_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _quote_cli(value: str) -> str:
    return shlex.quote(value)


def _workflow_next_action(
    action: str,
    message: str,
    *,
    suggested_cli: str | None = None,
    suggested_mcp_tool: str | None = None,
    suggested_mcp_arguments: Mapping[str, Any] | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action": action,
        "message": message,
        "native_tools_policy": (
            "Use native agent tools for source reads, edits, and project tests. "
            "Use Aegis CLI/MCP only for workflow state: install, bead kickoff, standalone start, "
            "historical numeric kickoff, log, verify, and closeout."
        ),
    }
    if suggested_cli:
        payload["suggested_cli"] = suggested_cli
    if suggested_mcp_tool:
        payload["suggested_mcp"] = {
            "tool": suggested_mcp_tool,
            "arguments": dict(suggested_mcp_arguments or {}),
        }
    if details:
        payload["details"] = dict(details)
    return payload


def _uses_beads_first_authority(target_root: Path) -> bool:
    agents_path = target_root / "AGENTS.md"
    if not agents_path.is_file():
        return False
    try:
        text = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return (
        "Gas City beads are the authoritative work ledger for new work" in text
        or "Gas City beads are authoritative for all new work" in text
    )


def _post_init_next_action(install_report: Mapping[str, Any]) -> dict[str, Any]:
    client_reload = install_report.get("client_reload")
    if isinstance(client_reload, Mapping) and bool(client_reload.get("required")):
        reload_agents = [
            str(agent).strip().lower()
            for agent in client_reload.get("agents", [])
            if isinstance(agent, str) and str(agent).strip().lower() in AGENT_CHOICES
        ]
        reload_agent = str(client_reload.get("agent") or "").strip().lower()
        if not reload_agents and reload_agent in AGENT_CHOICES:
            reload_agents = [reload_agent]
        if reload_agents == ["claude"]:
            action = "restart_claude_before_mutation"
            suggested_cli = (
                "Restart Claude Code in this project, then run "
                "./.aegis/bin/aegis next --target-dir ."
            )
        elif reload_agents == ["codex"]:
            action = "restart_codex_before_mutation"
            suggested_cli = (
                "Reconnect Codex in this project, use /hooks to review and trust the exact "
                "definitions and hashes, then run ./.aegis/bin/aegis next --target-dir ."
            )
        else:
            action = "restart_clients_before_mutation"
            suggested_cli = (
                "Restart or reconnect every enabled client named in details.agents, complete "
                "any Codex /hooks trust review, then run ./.aegis/bin/aegis next --target-dir ."
            )
        changed_paths = [
            str(path)
            for path in client_reload.get("changed_paths", [])
            if isinstance(path, str) and path
        ]
        return _workflow_next_action(
            action,
            str(client_reload.get("instructions") or "Client adapter reload is required."),
            suggested_cli=suggested_cli,
            suggested_mcp_tool="aegis.next",
            suggested_mcp_arguments={"target_dir": "."},
            details={
                "client_reload_required": True,
                "must_stop": True,
                "agent": client_reload.get("agent"),
                "agents": reload_agents,
                "changed_paths": changed_paths,
                "reload_reason": client_reload.get("reason"),
                "hook_trust": client_reload.get("hook_trust", {}),
                "forbidden_until_reload": client_reload.get("forbidden_until_reload", []),
                "allowed_until_reload": client_reload.get("allowed_until_reload", []),
                "post_reload": "Run aegis.next, then start/kickoff tracked work before source edits.",
            },
        )

    return _workflow_next_action(
        "start_tracked_work",
        "Aegis is installed. Start local tracked work before mutating source files.",
        suggested_cli='./.aegis/bin/aegis start "<task title>"',
        suggested_mcp_tool="aegis.start",
        suggested_mcp_arguments={
            "target_dir": ".",
            "title": "<task title>",
            "apply": True,
        },
        details={
            "public_flow": "aegis init -> aegis start -> native edit -> aegis log/verify/closeout"
        },
    )


def _update_manifest_after_kickoff(target_root: Path) -> None:
    manifest_path = target_root / AEGIS_MANIFEST_REL
    manifest = _read_json(manifest_path)
    if manifest is None:
        return
    capabilities = manifest.get("capabilities")
    if isinstance(capabilities, dict):
        capabilities["work_tracking"] = True
    manifest_path.write_text(_dump_json(manifest), encoding="utf-8")


def _ensure_client_reload_cleared(
    target_root: Path,
    operation: str,
    *,
    invoking_agent: str | None = None,
) -> None:
    marker = _client_reload_marker(target_root)
    if marker is None or not _client_reload_blocks_agent(marker, invoking_agent):
        return
    marker_agent = str(marker.get("agent") or "Claude").strip().title()
    raise AegisError(
        f"Aegis {operation} is blocked because the {marker_agent} adapter must reload before "
        f"that agent performs workflow mutations. Marker: {AEGIS_CLIENT_RELOAD_REL}. Please "
        f"restart {marker_agent} in this project so its installed hooks run, then call "
        "aegis.next and retry."
    )


def kickoff(
    target_dir: str | Path,
    *,
    task_id: str | int,
    slug: str,
    title: str,
    goals: Sequence[str] | None = None,
    create_branch: bool = True,
    source_root: str | Path | None = None,
    invoking_agent: str | None = None,
    _work_mode: str = "task",
) -> dict[str, Any]:
    """Create Aegis-native current work state for an installed target project."""

    target_root = _resolve_target_root(target_dir)
    resolved_source = Path(source_root).resolve() if source_root is not None else None
    if not (target_root / AEGIS_MANIFEST_REL).is_file():
        raise AegisError("Aegis kickoff requires an installed .aegis/foundation-manifest.json")
    _ensure_client_reload_cleared(
        target_root,
        "kickoff",
        invoking_agent=invoking_agent,
    )
    _ensure_git_work_tree(target_root)

    if _work_mode == "bead":
        normalized_task_id = _normalize_bead_id(str(task_id))
        normalized_slug = _normalize_bead_slug(slug, bead_id=normalized_task_id)
    elif _work_mode == "task":
        normalized_task_id = _normalize_task_id(task_id)
        normalized_slug = _normalize_task_slug(slug, task_id=normalized_task_id)
    else:
        raise AegisError(f"unsupported Aegis kickoff work mode: {_work_mode}")
    clean_title = title.strip()
    if not clean_title:
        raise AegisError("title is required")
    work_label = (
        f"bead {normalized_task_id}" if _work_mode == "bead" else f"task {normalized_task_id}"
    )
    task_payload = {
        "id": normalized_task_id,
        "slug": normalized_slug,
        "title": clean_title,
        "status": "in-progress",
    }
    if _work_mode == "bead":
        task_payload["source"] = "gas-city-bead"

    existing_current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    if isinstance(existing_current_work, Mapping):
        existing_status = str(existing_current_work.get("status") or "")
        existing_task = (
            existing_current_work.get("task")
            if isinstance(existing_current_work.get("task"), Mapping)
            else {}
        )
        existing_id = str(existing_task.get("id") or "")
        existing_slug = str(existing_task.get("slug") or "")
        if existing_status == "in-progress":
            if existing_id == normalized_task_id and existing_slug == normalized_slug:
                return _already_started_report(target_root, existing_current_work)
            raise AegisError(
                "Aegis current work is already in progress: "
                f"{existing_id} {existing_slug}. Close it out before starting {work_label} {normalized_slug}."
            )
        if isinstance(existing_current_work, MutableMapping):
            archived_observation_work = _archive_current_completed_observation_work_tracking(
                target_root,
                existing_current_work,
            )
            if archived_observation_work is not None:
                _update_observation_report_archived_work_tracking(
                    target_root,
                    archived_observation_work,
                )
                _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(existing_current_work))

    now = datetime.now().astimezone().replace(microsecond=0)
    selected_goals = list(goals or _default_goals())
    branch = (
        _ensure_bead_branch(
            target_root, normalized_task_id, normalized_slug, create_branch=create_branch
        )
        if _work_mode == "bead"
        else _ensure_task_branch(
            target_root, normalized_task_id, normalized_slug, create_branch=create_branch
        )
    )

    session_rel = _next_session_rel(
        target_root, normalized_task_id, normalized_slug, now, work_mode=_work_mode
    )
    plan_rel = _plan_rel(normalized_task_id, normalized_slug, now, work_mode=_work_mode)
    work_rel = _work_tracking_rel(normalized_task_id, normalized_slug, now, work_mode=_work_mode)
    reports_rel = f"{work_rel}/reports/{normalized_slug}"
    template_context = _workflow_template_context(
        task_id=normalized_task_id,
        title=clean_title,
        slug=normalized_slug,
        goals=selected_goals,
        now=now,
        branch_current=str(branch["current"]),
        session_rel=session_rel,
        plan_rel=plan_rel,
        work_rel=work_rel,
        reports_rel=reports_rel,
        work_mode=_work_mode,
    )

    _write_text(
        target_root,
        session_rel,
        _render_workflow_template(target_root, resolved_source, "session.md", template_context),
    )
    _replace_symlink(
        target_root / "sessions" / "current", str(Path(session_rel).relative_to("sessions"))
    )
    state_payload = {
        "schema_version": SCHEMA_VERSION,
        "current": Path(session_rel).name,
        "current_path": session_rel,
        "task": dict(task_payload),
        "updated_at": _iso_now(),
    }
    _write_text(target_root, "sessions/state.json", _dump_json(state_payload))

    _write_text(
        target_root,
        plan_rel,
        _render_workflow_template(target_root, resolved_source, "plan.md", template_context),
    )
    _replace_symlink(target_root / "plans" / "current", Path(plan_rel).name)

    work_files = {
        f"{work_rel}/TRACKER.md": _render_workflow_template(
            target_root, resolved_source, "tracker.md", template_context
        ),
        f"{work_rel}/FINDINGS.md": _render_workflow_template(
            target_root, resolved_source, "findings.md", template_context
        ),
        f"{work_rel}/DECISIONS.md": _render_workflow_template(
            target_root, resolved_source, "decisions.md", template_context
        ),
        f"{work_rel}/HANDOFF.md": _render_workflow_template(
            target_root, resolved_source, "handoff.md", template_context
        ),
        f"{work_rel}/IMPLEMENTATION.md": _render_workflow_template(
            target_root, resolved_source, "implementation.md", template_context
        ),
        f"{work_rel}/CHANGELOG.md": _render_workflow_template(
            target_root, resolved_source, "changelog.md", template_context
        ),
    }
    for rel_path, content in work_files.items():
        _write_text(target_root, rel_path, content)
    (target_root / work_rel / "designs").mkdir(parents=True, exist_ok=True)
    (target_root / reports_rel).mkdir(parents=True, exist_ok=True)

    current_work = {
        "schema_version": SCHEMA_VERSION,
        "mode": _work_mode,
        "status": "in-progress",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": _iso_now(),
        "task": dict(task_payload),
        "branch": branch,
        "paths": {
            "session": session_rel,
            "session_current": "sessions/current",
            "plan": plan_rel,
            "plan_current": "plans/current",
            "work_tracking": work_rel,
            "reports": reports_rel,
            "workflow_templates": AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
        },
        "integrations": {
            "taskmaster": {
                "required": False,
                "detected": (target_root / ".taskmaster").exists(),
                **({"mutation_allowed": False} if _work_mode == "bead" else {}),
            },
            "serena": {
                "required": False,
                "detected": (target_root / ".serena").exists(),
            },
        },
    }
    if _work_mode == "bead":
        current_work["authority"] = {
            "kind": "gas-city-bead",
            "id": normalized_task_id,
            "mutable": True,
        }
    _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(current_work))
    _update_manifest_after_kickoff(target_root)

    scope_handler = _workflow_log_handler(target_root, "scope")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "started",
        "started_at": _iso_now(),
        "target_root": str(target_root),
        "task": current_work["task"],
        "branch": branch,
        "paths": current_work["paths"],
        "integrations": current_work["integrations"],
        "workflow_templates": AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
        "next_action": _workflow_next_action(
            "log_scope_before_edit",
            "Before any source edit, record scope against plan-step-scope so closeout can pass first time.",
            suggested_cli=(
                f"./.aegis/bin/aegis log --target-dir . --handler {scope_handler} "
                f"--evidence {_quote_cli(f'{work_rel}/FINDINGS.md')} "
                "--note 'Confirmed task scope before implementation' "
                "--plan-step auto --plan-status completed"
            ),
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments={
                "target_dir": ".",
                "handler": scope_handler,
                "evidence": f"{work_rel}/FINDINGS.md",
                "note": "Confirmed task scope before implementation",
                "event_class": "scope",
                "plan_step": "auto",
                "plan_status": "completed",
                "apply": True,
            },
            details={
                "scope_evidence": f"{work_rel}/FINDINGS.md",
                "required_before": "native source edits",
            },
        ),
    }
    _write_text(target_root, AEGIS_KICKOFF_REPORT_REL, _dump_json(report))
    return report


def kickoff_bead(
    target_dir: str | Path,
    *,
    bead_id: str,
    slug: str,
    title: str,
    goals: Sequence[str] | None = None,
    create_branch: bool = True,
    source_root: str | Path | None = None,
    invoking_agent: str | None = None,
) -> dict[str, Any]:
    """Create bead-native Aegis current-work state without Taskmaster mutation."""

    return kickoff(
        target_dir,
        task_id=bead_id,
        slug=slug,
        title=title,
        goals=goals,
        create_branch=create_branch,
        source_root=source_root,
        invoking_agent=invoking_agent,
        _work_mode="bead",
    )


def start_observation(
    target_dir: str | Path,
    *,
    title: str,
    slug: str = "",
    goals: Sequence[str] | None = None,
    source_root: str | Path | None = None,
    invoking_agent: str | None = None,
) -> dict[str, Any]:
    """Start a non-task observation window for audits, screenshots, and app-driving."""

    target_root = _resolve_target_root(target_dir)
    resolved_source = Path(source_root).resolve() if source_root is not None else None
    if not (target_root / AEGIS_MANIFEST_REL).is_file():
        raise AegisError("Aegis observe requires an installed .aegis/foundation-manifest.json")
    _ensure_client_reload_cleared(
        target_root,
        "observe start",
        invoking_agent=invoking_agent,
    )
    _ensure_git_work_tree(target_root)

    clean_title = title.strip()
    if not clean_title:
        raise AegisError("title is required")
    normalized_slug = _normalize_observation_slug(slug, clean_title)

    existing_current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    if (
        isinstance(existing_current_work, Mapping)
        and str(existing_current_work.get("status") or "") == "in-progress"
    ):
        return _already_started_report(target_root, existing_current_work)
    if isinstance(existing_current_work, MutableMapping):
        archived_observation_work = _archive_current_completed_observation_work_tracking(
            target_root,
            existing_current_work,
        )
        if archived_observation_work is not None:
            _update_observation_report_archived_work_tracking(
                target_root, archived_observation_work
            )
            _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(existing_current_work))

    now = datetime.now().astimezone().replace(microsecond=0)
    observation_id = _observation_id(normalized_slug, now)
    branch_current = _current_branch(target_root)
    observation_budget = _observation_budget_config(target_root)
    baseline_status = _git_status_snapshot(target_root)
    baseline_fingerprints = _git_status_fingerprints(target_root, baseline_status)
    try:
        gate_audit_baseline = _observation_audit.capture(target_root)
    except (OSError, ValueError) as exc:
        raise AegisError("cannot bind observation gate audit safely") from exc
    selected_goals = list(
        goals
        or [
            "Run observation tooling without source edits or Taskmaster mutation",
            "Capture findings, screenshots, and reproduction notes",
            "Stop observation and verify no unexpected working-tree delta",
        ]
    )

    session_rel = _observation_session_rel(target_root, observation_id, now)
    plan_rel = _observation_plan_rel(normalized_slug, now)
    work_rel = _observation_work_tracking_rel(normalized_slug, now)
    reports_rel = f"{work_rel}/reports/{normalized_slug}"
    artifact_root_rel = f"{AEGIS_OBSERVATION_ARTIFACT_ROOT_REL}/{observation_id}/artifacts"
    template_context = _workflow_template_context(
        task_id=observation_id,
        title=clean_title,
        slug=normalized_slug,
        goals=selected_goals,
        now=now,
        branch_current=branch_current,
        session_rel=session_rel,
        plan_rel=plan_rel,
        work_rel=work_rel,
        reports_rel=reports_rel,
        work_context=f"observe-{normalized_slug}",
    )

    _write_text(
        target_root,
        session_rel,
        _render_workflow_template(target_root, resolved_source, "session.md", template_context),
    )
    _replace_symlink(
        target_root / "sessions" / "current", str(Path(session_rel).relative_to("sessions"))
    )
    state_payload = {
        "schema_version": SCHEMA_VERSION,
        "current": Path(session_rel).name,
        "current_path": session_rel,
        "mode": "observation",
        "task": {
            "id": observation_id,
            "slug": normalized_slug,
            "title": clean_title,
            "status": "in-progress",
            "source": "aegis-observation",
        },
        "updated_at": _iso_now(),
    }
    _write_text(target_root, "sessions/state.json", _dump_json(state_payload))

    _write_text(
        target_root,
        plan_rel,
        _render_workflow_template(target_root, resolved_source, "plan.md", template_context),
    )
    _replace_symlink(target_root / "plans" / "current", Path(plan_rel).name)

    work_files = {
        f"{work_rel}/TRACKER.md": _render_workflow_template(
            target_root, resolved_source, "tracker.md", template_context
        ),
        f"{work_rel}/FINDINGS.md": _render_workflow_template(
            target_root, resolved_source, "findings.md", template_context
        ),
        f"{work_rel}/DECISIONS.md": _render_workflow_template(
            target_root, resolved_source, "decisions.md", template_context
        ),
        f"{work_rel}/HANDOFF.md": _render_workflow_template(
            target_root, resolved_source, "handoff.md", template_context
        ),
        f"{work_rel}/IMPLEMENTATION.md": _render_workflow_template(
            target_root, resolved_source, "implementation.md", template_context
        ),
        f"{work_rel}/CHANGELOG.md": _render_workflow_template(
            target_root, resolved_source, "changelog.md", template_context
        ),
    }
    for rel_path, content in work_files.items():
        _write_text(target_root, rel_path, content)
    (target_root / work_rel / "designs").mkdir(parents=True, exist_ok=True)
    (target_root / reports_rel).mkdir(parents=True, exist_ok=True)

    current_work = {
        "schema_version": SCHEMA_VERSION,
        "mode": "observation",
        "status": "in-progress",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": _iso_now(),
        "task": {
            "id": observation_id,
            "slug": normalized_slug,
            "title": clean_title,
            "status": "in-progress",
            "source": "aegis-observation",
        },
        "observation": {
            "id": observation_id,
            "slug": normalized_slug,
            "title": clean_title,
            "artifact_root": artifact_root_rel,
            # TM #197: the full baseline lives in the linked artifact file so
            # current-work.json (and every payload embedding it) stays small.
            "baseline_ref": AEGIS_OBSERVATION_BASELINE_REL,
            "baseline_summary": _summarize_path_lines(baseline_status, observation_budget),
            "allowed_paths": [],
        },
        "branch": {
            "before": branch_current,
            "current": branch_current,
            "action": "observation_no_branch_change",
            "created": False,
            "requires_task_id": False,
        },
        "paths": {
            "session": session_rel,
            "session_current": "sessions/current",
            "plan": plan_rel,
            "plan_current": "plans/current",
            "work_tracking": work_rel,
            "reports": reports_rel,
            "observation_artifacts": artifact_root_rel,
            "workflow_templates": AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
        },
        "integrations": {
            "taskmaster": {
                "required": False,
                "detected": (target_root / ".taskmaster").exists(),
            },
            "serena": {
                "required": False,
                "detected": (target_root / ".serena").exists(),
            },
        },
    }
    current_work["observation"]["allowed_paths"] = _observation_allowed_prefixes(current_work)
    _write_text(
        target_root,
        AEGIS_OBSERVATION_BASELINE_REL,
        _dump_json(
            {
                "schema_version": SCHEMA_VERSION,
                "captured_at": _iso_now(),
                "baseline_git_status": baseline_status,
                "baseline_git_fingerprints": baseline_fingerprints,
                "gate_audit": gate_audit_baseline,
            }
        ),
    )
    _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(current_work))
    _update_manifest_after_kickoff(target_root)

    stop_arguments = {
        "target_dir": ".",
        "summary": "<what was observed>",
        "apply": True,
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "started",
        "mode": "observation",
        "started_at": _iso_now(),
        "target_root": str(target_root),
        "task": current_work["task"],
        "observation": current_work["observation"],
        "branch": current_work["branch"],
        "paths": current_work["paths"],
        "integrations": current_work["integrations"],
        "workflow_templates": AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
        "next_action": _workflow_next_action(
            "observe_then_stop",
            "Observation mode is active. Run app-driving, browser, screenshot, and read-only audit tooling without source edits or Taskmaster mutations; then stop observation to verify the working tree delta.",
            suggested_cli=(
                "./.aegis/bin/aegis observe stop --target-dir . "
                "--summary '<what was observed>' --collect-artifacts"
            ),
            suggested_mcp_tool="aegis.observe_stop",
            suggested_mcp_arguments={**stop_arguments, "collect_artifacts": True},
            details={
                "allowed": [
                    "dev servers and localhost probes",
                    "browser/screenshot MCP tools",
                    "read-only source and git inspection",
                    "aegis log for observation notes",
                ],
                "blocked": [
                    "source edits",
                    "Taskmaster mutations",
                    "git mutations",
                    "Aegis closeout/apply paths",
                ],
                "artifact_root": artifact_root_rel,
                "side_effect_guard": "aegis observe stop compares git status to the start snapshot, can collect known observation artifacts with --collect-artifacts, and refuses unexpected deltas unless --allow-dirty is explicit.",
            },
        ),
    }
    _write_text(target_root, AEGIS_OBSERVATION_REPORT_REL, _dump_json(report))
    return report


def stop_observation(
    target_dir: str | Path,
    *,
    summary: str = "",
    allow_dirty: bool = False,
    collect_artifacts: bool = False,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    """End an observation window and refuse if unexpected working-tree deltas appeared."""

    del source_root
    target_root = _resolve_target_root(target_dir)
    if not (target_root / AEGIS_MANIFEST_REL).is_file():
        raise AegisError("Aegis observe stop requires an installed .aegis/foundation-manifest.json")
    _ensure_git_work_tree(target_root)

    current_work_path = target_root / AEGIS_CURRENT_WORK_REL
    current_work = _read_json(current_work_path)
    if not isinstance(current_work, MutableMapping):
        raise AegisError(f"{AEGIS_CURRENT_WORK_REL} missing or invalid; no observation is active")
    if str(current_work.get("mode") or "") != "observation":
        raise AegisError("aegis observe stop requires active observation-mode current work")
    if str(current_work.get("status") or "") != "in-progress":
        if str(current_work.get("status") or "") == "completed":
            finished_at = _iso_now()
            archived_observation_work = _archive_current_completed_observation_work_tracking(
                target_root,
                current_work,
            )
            if archived_observation_work is not None:
                _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(current_work))
            report = _read_json(target_root / AEGIS_OBSERVATION_REPORT_REL)
            if not isinstance(report, MutableMapping):
                report = {
                    "schema_version": SCHEMA_VERSION,
                    "status": "completed",
                    "mode": "observation",
                    "target_root": str(target_root),
                    "task": dict(current_work.get("task") or {}),
                    "paths": dict(current_work.get("paths") or {}),
                }
            report["status"] = "completed"
            report["mode"] = "observation"
            report["target_root"] = str(target_root)
            report["idempotent"] = True
            report["already_completed"] = True
            report["checked_at"] = finished_at
            if archived_observation_work is not None:
                report_paths = (
                    report.get("paths") if isinstance(report.get("paths"), MutableMapping) else None
                )
                if report_paths is not None:
                    _replace_work_tracking_path_prefix(
                        report_paths,
                        archived_observation_work["from"],
                        archived_observation_work["to"],
                    )
                report["archived_work_tracking"] = dict(archived_observation_work)
                _write_text(target_root, AEGIS_OBSERVATION_REPORT_REL, _dump_json(report))
            report["next_action"] = _workflow_next_action(
                "observation_already_closed",
                "Observation was already completed; review evidence, then kickoff task-scoped work before mutating.",
                details={
                    "completed_at": current_work.get("completed_at"),
                    "observation_report": AEGIS_OBSERVATION_REPORT_REL,
                },
            )
            return dict(report)
        raise AegisError("aegis observe stop requires an in-progress observation")

    finished_at = _iso_now()
    observation_budget = _observation_budget_config(target_root)
    _load_observation_baseline(target_root, current_work)
    current_status = _git_status_snapshot(target_root)
    current_fingerprints = _git_status_fingerprints(target_root, current_status)
    artifact_root_rel = _observation_artifact_root_rel(current_work)
    status_deltas = _observation_status_delta_lines(current_work, current_status)
    fingerprint_deltas = _observation_fingerprint_delta_lines(current_work, current_fingerprints)
    gate_audit = _observation_audit.verify(
        target_root, current_work.get("observation", {}).get("gate_audit")
    )
    audit_deltas = []
    if gate_audit["status"] == "verified":
        audit_deltas = [
            line for line in status_deltas if _git_status_rel_path(line) == AEGIS_GATE_DECISIONS_REL
        ]
        audit_deltas += [
            line
            for line in fingerprint_deltas
            if _observation_fingerprint_delta_rel(line) == AEGIS_GATE_DECISIONS_REL
        ]
    cleanable_artifacts = _observation_cleanable_artifact_rels(
        target_root,
        status_deltas,
        artifact_root_rel,
    )
    cleanable_set = set(cleanable_artifacts)
    runtime_status_deltas = _observation_runtime_status_delta_lines(status_deltas)
    runtime_fingerprint_deltas = _observation_runtime_fingerprint_delta_lines(
        current_work,
        fingerprint_deltas,
    )
    runtime_delta_set = {*runtime_status_deltas, *runtime_fingerprint_deltas, *audit_deltas}
    unsafe_status_deltas = [
        line
        for line in status_deltas
        if (
            (_observation_artifact_source_rel(line) or "") not in cleanable_set
            and line not in runtime_delta_set
        )
    ]
    unsafe_fingerprint_deltas = [
        line for line in fingerprint_deltas if line not in runtime_delta_set
    ]
    unexpected = [*unsafe_status_deltas, *unsafe_fingerprint_deltas]
    collected_artifacts: list[dict[str, str]] = []
    if collect_artifacts and cleanable_artifacts and not unexpected:
        collected_artifacts = _collect_observation_artifacts(
            target_root,
            artifact_root_rel,
            cleanable_artifacts,
        )
        current_status = _git_status_snapshot(target_root)
        current_fingerprints = _git_status_fingerprints(target_root, current_status)
        status_deltas = _observation_status_delta_lines(current_work, current_status)
        fingerprint_deltas = _observation_fingerprint_delta_lines(
            current_work, current_fingerprints
        )
        runtime_status_deltas = _observation_runtime_status_delta_lines(status_deltas)
        runtime_fingerprint_deltas = _observation_runtime_fingerprint_delta_lines(
            current_work,
            fingerprint_deltas,
        )
        runtime_delta_set = {*runtime_status_deltas, *runtime_fingerprint_deltas, *audit_deltas}
        unexpected = [
            *[line for line in status_deltas if line not in runtime_delta_set],
            *[line for line in fingerprint_deltas if line not in runtime_delta_set],
        ]
        cleanable_artifacts = []
    elif cleanable_artifacts:
        unexpected = [
            *[line for line in status_deltas if line not in runtime_delta_set],
            *[line for line in fingerprint_deltas if line not in runtime_delta_set],
        ]
    allowed_runtime_changes = [*runtime_status_deltas, *runtime_fingerprint_deltas, *audit_deltas]
    if gate_audit["status"] == "invalid":
        unexpected.append(gate_audit["error"])
    blocked = bool(unexpected and not allow_dirty)
    # TM #197: guidance payloads carry capped summaries with truncation markers; the
    # full enumerations live in the linked detail artifact. Unexpected deltas keep a
    # sample large enough to act on; nothing is silently dropped.
    sample_cap = int(observation_budget["sample_cap"])
    allowed_summary = _summarize_path_lines(allowed_runtime_changes, observation_budget)
    final_status_summary = _summarize_path_lines(current_status, observation_budget)
    unexpected_sample = unexpected[:sample_cap]
    unexpected_truncated = len(unexpected) > sample_cap
    _write_text(
        target_root,
        AEGIS_OBSERVATION_REPORT_DETAIL_REL,
        _dump_json(
            {
                "schema_version": SCHEMA_VERSION,
                "finished_at": finished_at,
                "allowed_runtime_changes": allowed_runtime_changes,
                "unexpected_changes": unexpected,
                "final_git_status": current_status,
                "final_git_fingerprints": current_fingerprints,
            }
        ),
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked" if blocked else "completed",
        "mode": "observation",
        "finished_at": finished_at,
        "target_root": str(target_root),
        "summary": summary,
        "allow_dirty": allow_dirty,
        "collect_artifacts": collect_artifacts,
        "artifact_root": artifact_root_rel,
        "cleanable_artifacts": cleanable_artifacts,
        "collected_artifacts": collected_artifacts,
        "allowed_runtime_changes_summary": allowed_summary,
        "gate_audit": gate_audit,
        "unexpected_changes": unexpected_sample,
        "unexpected_changes_total": len(unexpected),
        "unexpected_changes_truncated": unexpected_truncated,
        "final_git_status_summary": final_status_summary,
        "detail_ref": AEGIS_OBSERVATION_REPORT_DETAIL_REL,
        "task": dict(current_work.get("task") or {}),
        "paths": dict(current_work.get("paths") or {}),
        "next_action": _workflow_next_action(
            "resolve_unexpected_delta" if blocked else "observation_closed",
            (
                "Observation stop refused because unexpected working-tree deltas appeared. "
                "Revert them, rerun with --collect-artifacts for known observation artifacts, "
                "or intentionally keep them with --allow-dirty."
                if blocked
                else "Observation closed; no unexpected working-tree delta was detected."
            ),
            details={
                "unexpected_changes": unexpected_sample,
                "unexpected_changes_total": len(unexpected),
                "unexpected_changes_truncated": unexpected_truncated,
                "cleanable_artifacts": cleanable_artifacts,
                "collected_artifacts": collected_artifacts,
                "allowed_runtime_changes_summary": allowed_summary,
                "detail_ref": AEGIS_OBSERVATION_REPORT_DETAIL_REL,
                "allow_dirty": allow_dirty,
                "collect_artifacts": collect_artifacts,
                "artifact_root": artifact_root_rel,
            },
        ),
    }
    _write_text(target_root, AEGIS_OBSERVATION_REPORT_REL, _dump_json(report))
    if blocked:
        return report

    current_work["status"] = "completed"
    current_work["updated_at"] = finished_at
    current_work["completed_at"] = finished_at
    task = current_work.get("task")
    if isinstance(task, MutableMapping):
        task["status"] = "completed"
    observation = current_work.get("observation")
    if isinstance(observation, MutableMapping):
        observation["completed_at"] = finished_at
        observation["summary"] = summary
        # TM #197: persisted state carries summaries + the detail artifact link; the
        # hydrated full baselines are stripped so current-work.json stays small.
        observation.pop("baseline_git_status", None)
        observation.pop("baseline_git_fingerprints", None)
        observation["final_git_status_summary"] = final_status_summary
        observation["unexpected_changes"] = unexpected_sample
        observation["unexpected_changes_total"] = len(unexpected)
        observation["unexpected_changes_truncated"] = unexpected_truncated
        observation["allow_dirty"] = allow_dirty
        observation["collect_artifacts"] = collect_artifacts
        observation["artifact_root"] = artifact_root_rel
        observation["collected_artifacts"] = collected_artifacts
        observation["allowed_runtime_changes_summary"] = allowed_summary
        observation["detail_ref"] = AEGIS_OBSERVATION_REPORT_DETAIL_REL
    archived_observation_work = _archive_current_completed_observation_work_tracking(
        target_root,
        current_work,
    )
    if archived_observation_work is not None:
        report_paths = (
            report.get("paths") if isinstance(report.get("paths"), MutableMapping) else None
        )
        if report_paths is not None:
            _replace_work_tracking_path_prefix(
                report_paths,
                archived_observation_work["from"],
                archived_observation_work["to"],
            )
        report["archived_work_tracking"] = dict(archived_observation_work)
    _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(current_work))
    if archived_observation_work is not None:
        _write_text(target_root, AEGIS_OBSERVATION_REPORT_REL, _dump_json(report))
    return report


def _already_started_report(target_root: Path, current_work: Mapping[str, Any]) -> dict[str, Any]:
    task = current_work.get("task") if isinstance(current_work.get("task"), Mapping) else {}
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    work_rel = str(paths.get("work_tracking") or "")
    task_id = str(task.get("id") or "")
    slug = str(task.get("slug") or "")
    scope_handler = _workflow_log_handler(target_root, "scope")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "already_started",
        "started_at": current_work.get("created_at"),
        "checked_at": _iso_now(),
        "target_root": str(target_root),
        "task": dict(task),
        "branch": current_work.get("branch"),
        "paths": dict(paths),
        "integrations": current_work.get("integrations", {}),
        "workflow_templates": AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
        "idempotent": True,
        "next_action": _workflow_next_action(
            "continue_existing_work",
            "Current work already exists; continue by logging scope, implementation, or verification evidence as appropriate.",
            suggested_cli=(
                (
                    f"./.aegis/bin/aegis log --target-dir . --handler {scope_handler} "
                    f"--evidence {_quote_cli(f'{work_rel}/FINDINGS.md')} "
                    "--note 'Confirmed task scope before implementation' "
                    "--plan-step auto --plan-status completed"
                )
                if work_rel
                else None
            ),
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments=(
                {
                    "target_dir": ".",
                    "handler": scope_handler,
                    "evidence": f"{work_rel}/FINDINGS.md",
                    "note": "Confirmed task scope before implementation",
                    "event_class": "scope",
                    "plan_step": "auto",
                    "plan_status": "completed",
                    "apply": True,
                }
                if work_rel
                else None
            ),
            details={"task": task_id, "slug": slug},
        ),
    }
    if isinstance(current_work.get("local_task"), Mapping):
        report["local_task"] = dict(current_work["local_task"])
        report["public_command"] = 'aegis start "<task title>"'
    return report


def start_local_work(
    target_dir: str | Path,
    *,
    title: str,
    slug: str | None = None,
    goals: Sequence[str] | None = None,
    create_branch: bool = True,
    source_root: str | Path | None = None,
    invoking_agent: str | None = None,
) -> dict[str, Any]:
    """Allocate local work only for projects without an external work authority."""

    target_root = _resolve_target_root(target_dir)
    if not (target_root / AEGIS_MANIFEST_REL).is_file():
        raise AegisError(
            "Aegis start requires an installed .aegis/foundation-manifest.json; run aegis init first"
        )
    _ensure_client_reload_cleared(
        target_root,
        "start",
        invoking_agent=invoking_agent,
    )
    _ensure_git_work_tree(target_root)
    clean_title = title.strip()
    if not clean_title:
        raise AegisError("task title is required")
    if _uses_beads_first_authority(target_root):
        raise AegisError(
            "Gas City beads are the declared work authority for this project; use "
            "./.aegis/bin/aegis kickoff --target-dir . --bead <bead-id> --slug <slug> "
            "--title '<title>' instead of allocating a local Aegis task"
        )
    normalized_slug = _slugify(slug or clean_title)
    existing_current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    if isinstance(existing_current_work, Mapping):
        existing_status = str(existing_current_work.get("status") or "")
        existing_task = (
            existing_current_work.get("task")
            if isinstance(existing_current_work.get("task"), Mapping)
            else {}
        )
        existing_slug = str(existing_task.get("slug") or "")
        existing_title = str(existing_task.get("title") or "")
        if existing_status == "in-progress":
            if existing_slug == normalized_slug and existing_title == clean_title:
                return _already_started_report(target_root, existing_current_work)
            raise AegisError(
                "Aegis current work is already in progress: "
                f"task {existing_task.get('id')} {existing_slug}. Close it out before starting {normalized_slug}."
            )
        if isinstance(existing_current_work, MutableMapping):
            archived_observation_work = _archive_current_completed_observation_work_tracking(
                target_root,
                existing_current_work,
            )
            if archived_observation_work is not None:
                _update_observation_report_archived_work_tracking(
                    target_root,
                    archived_observation_work,
                )
                _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(existing_current_work))
    taskmaster = _taskmaster_state(target_root)
    if taskmaster.state == "invalid":
        raise AegisError(
            "Taskmaster task state is present but invalid at "
            f"{TASKMASTER_TASKS_REL}; repair it before starting Aegis work. "
            f"Reason: {taskmaster.reason}. "
            "Run task-master validate-dependencies or python3 scripts/codex-task taskmaster health."
        )
    if taskmaster.state == "valid":
        raise AegisError(
            "Taskmaster is present at "
            f"{TASKMASTER_TASKS_REL}; use task-master next/show and then "
            "./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> "
            "--title '<title>' instead of aegis start. Aegis local task allocation is only "
            "available when Taskmaster is absent."
        )
    local_task = _allocate_local_task(target_root, clean_title, normalized_slug)
    report = kickoff(
        target_root,
        task_id=local_task["id"],
        slug=normalized_slug,
        title=clean_title,
        goals=goals,
        create_branch=create_branch,
        source_root=source_root,
        invoking_agent=invoking_agent,
    )
    current_work_path = target_root / AEGIS_CURRENT_WORK_REL
    current_work = _read_json(current_work_path)
    if isinstance(current_work, MutableMapping):
        task_payload = current_work.get("task")
        if isinstance(task_payload, MutableMapping):
            task_payload["source"] = "aegis-local"
        current_work["local_task"] = local_task
        current_work_path.write_text(_dump_json(current_work), encoding="utf-8")
    report["local_task"] = local_task
    report["public_command"] = 'aegis start "<task title>"'
    return report


def _recover_source_current_work_payload(target_root: Path) -> dict[str, Any] | None:
    """Recover ignored runtime state for this repository's uninstalled source checkout."""

    helper_path = target_root / "scripts" / "_source_workflow_state.py"
    if not helper_path.is_file() or helper_path.is_symlink():
        return None
    module_name = (
        "_aegis_source_current_work_recovery_"
        + hashlib.sha256(target_root.as_posix().encode("utf-8")).hexdigest()[:16]
    )
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    if spec is None or spec.loader is None:
        raise AegisError("could not load source workflow recovery helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        if not module.is_uninstalled_aegis_source_checkout(target_root):
            return None
        recovered = module.recover_source_current_work(
            target_root,
            _current_branch(target_root),
            schema_version=SCHEMA_VERSION,
        )
    except Exception as exc:  # noqa: BLE001 - normalize source recovery failures.
        raise AegisError(f"Aegis source current-work recovery refused: {exc}") from exc
    finally:
        sys.modules.pop(module_name, None)
    if not isinstance(recovered, dict):
        raise AegisError("Aegis source current-work recovery returned an invalid payload")
    return recovered


def _current_work_payload(target_root: Path) -> dict[str, Any]:
    current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    if current_work is None:
        current_work = _recover_source_current_work_payload(target_root)
    if current_work is None:
        raise AegisError(
            "Aegis log requires .aegis/state/current-work.json; run aegis kickoff first"
        )
    return current_work


def _normalize_evidence(target_root: Path, evidence: str) -> str:
    if not evidence.strip():
        raise AegisError("evidence is required")
    path = Path(evidence).expanduser()
    if path.is_absolute():
        try:
            return path.resolve().relative_to(target_root).as_posix()
        except ValueError:
            return path.as_posix()
    clean = evidence.strip()
    return clean[2:] if clean.startswith("./") else clean


def _append_progress_entry(path: Path, heading: str, line: str) -> None:
    if not path.is_file():
        raise AegisError(f"required workflow file missing: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        heading_index = next(index for index, value in enumerate(lines) if value.strip() == heading)
    except StopIteration:
        lines.extend(["", heading, line])
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return

    insert_at = len(lines)
    for index in range(heading_index + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("#") and stripped != heading:
            insert_at = index
            break
    while insert_at > heading_index + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, line)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _normalize_log_event_class(value: str | None) -> str:
    clean = (value or "").strip().lower().replace("-", "_")
    aliases = {
        "implement": "implementation",
        "implementation": "implementation",
        "verify": "verification",
        "verification": "verification",
        "scope": "scope",
        "note": "note",
        "generic": "note",
    }
    if not clean:
        return ""
    if clean not in aliases:
        choices = ", ".join(AEGIS_LOG_EVENT_CLASSES)
        raise AegisError(f"unknown log event class: {value}; expected one of: {choices}")
    return aliases[clean]


def _infer_log_event_class(
    *,
    plan_step: str | None,
    handler: str,
    evidence: str,
    explicit_event_class: str | None = None,
) -> str:
    explicit = _normalize_log_event_class(explicit_event_class)
    if explicit:
        return explicit

    step = (plan_step or "").strip().lower()
    if "scope" in step:
        return "scope"
    if "verify" in step:
        return "verification"
    if "implement" in step:
        return "implementation"

    handler_lower = handler.lower()
    evidence_lower = evidence.lower()
    if "scope" in handler_lower:
        return "scope"
    if (
        "verify" in handler_lower
        or "verification" in handler_lower
        or evidence_lower == AEGIS_VERIFY_REPORT_REL.lower()
        or "/verification" in evidence_lower
        or evidence_lower.endswith("verification-report.json")
    ):
        return "verification"
    return "note"


def _default_log_surfaces_for_event(event_class: str) -> tuple[str, ...]:
    return AEGIS_EVENT_DEFAULT_LOG_SURFACES.get(event_class, AEGIS_DEFAULT_LOG_SURFACES)


def _normalize_log_surfaces(
    surfaces: Sequence[str] | None,
    *,
    default_surfaces: Sequence[str] = AEGIS_DEFAULT_LOG_SURFACES,
) -> tuple[str, ...]:
    selected = tuple(default_surfaces if surfaces is None else surfaces)
    if not selected:
        return ()
    normalized: list[str] = []
    unknown: list[str] = []
    for value in selected:
        key = value.strip().lower()
        if not key:
            continue
        if key not in AEGIS_LOG_SURFACES:
            unknown.append(value)
            continue
        if key not in normalized:
            normalized.append(key)
    if unknown:
        choices = ", ".join(sorted(AEGIS_LOG_SURFACES))
        raise AegisError(
            f"unknown log surface(s): {', '.join(unknown)}; expected one of: {choices}"
        )
    return tuple(normalized)


def _normalize_plan_status(status: str | None) -> str:
    clean = (status or "in-progress").strip().lower()
    if clean not in AEGIS_PLAN_STATUS_CHOICES:
        choices = ", ".join(sorted(AEGIS_PLAN_STATUS_CHOICES))
        raise AegisError(f"unknown plan status: {status}; expected one of: {choices}")
    return "completed" if clean == "done" else clean


AEGIS_PLAN_STEP_IDS = ("plan-step-scope", "plan-step-implement", "plan-step-verify")
AEGIS_PLAN_STEP_ROW_RE = re.compile(r"^\|\s*(plan-step-[A-Za-z0-9_-]+)\s*\|")
AEGIS_PLAN_STEP_DEFAULTS: dict[str, dict[str, str]] = {
    "plan-step-scope": {
        "description": "Confirm task scope, constraints, expected outputs, and affected files before implementation",
        "status": "in-progress",
    },
    "plan-step-implement": {
        "description": "Make only task-scoped changes and record implementation notes",
        "status": "pending",
    },
    "plan-step-verify": {
        "description": "Run verification, capture reports, and update handoff state",
        "status": "pending",
    },
    "plan-step-emergency": {
        "description": "Optional - only if a bypass is explicitly authorized",
        "evidence": "Waiver plus post-mortem note in DECISIONS.md and FINDINGS.md",
        "status": "n/a",
    },
}


def _pending_event_is_confident_implementation(pending_event: Mapping[str, Any] | None) -> bool:
    if not isinstance(pending_event, Mapping):
        return False
    event_class_value = str(
        pending_event.get("event_class") or pending_event.get("classification") or ""
    )
    if event_class_value.strip().lower().replace("-", "_") == "implementation":
        return True
    tool_name = str(pending_event.get("tool") or pending_event.get("tool_name") or "")
    return tool_name in {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _infer_auto_plan_step(
    *,
    event_class: str,
    handler: str,
    evidence: str,
    pending_event: Mapping[str, Any] | None,
) -> tuple[str, str]:
    candidates: dict[str, str] = {}

    if event_class == "scope":
        candidates["plan-step-scope"] = "event_class=scope"
    elif event_class == "implementation":
        candidates["plan-step-implement"] = "event_class=implementation"
    elif event_class == "verification":
        candidates["plan-step-verify"] = "event_class=verification"

    handler_lower = handler.lower()
    evidence_lower = evidence.lower()
    if "scope" in handler_lower:
        candidates.setdefault("plan-step-scope", "handler contains scope")
    if (
        evidence_lower == AEGIS_VERIFY_REPORT_REL.lower()
        or "verify" in handler_lower
        or "verification" in handler_lower
    ):
        candidates.setdefault("plan-step-verify", "verification handler/evidence")

    if _pending_event_is_confident_implementation(pending_event):
        candidates.setdefault("plan-step-implement", "pending file mutation event")

    if len(candidates) == 1:
        step, reason = next(iter(candidates.items()))
        return step, reason

    choices = ", ".join(AEGIS_PLAN_STEP_IDS)
    if not candidates:
        raise AegisError(
            f"plan-step auto could not infer a deterministic plan step; pass one of: {choices}"
        )
    observed = ", ".join(f"{step} ({reason})" for step, reason in candidates.items())
    raise AegisError(
        "plan-step auto is ambiguous; "
        f"observed candidates: {observed}; pass one explicit plan step: {choices}"
    )


def _resolve_plan_step_argument(
    plan_step: str | None,
    *,
    event_class: str,
    handler: str,
    evidence: str,
    pending_event: Mapping[str, Any] | None,
) -> tuple[str, bool, str | None]:
    clean = (plan_step or "").strip()
    if not clean:
        return "", False, None
    if clean.lower() != "auto":
        return clean, False, None
    inferred, reason = _infer_auto_plan_step(
        event_class=event_class,
        handler=handler,
        evidence=evidence,
        pending_event=pending_event,
    )
    return inferred, True, reason


def _update_tracker_timestamp(tracker_path: Path, timestamp: str) -> None:
    lines = tracker_path.read_text(encoding="utf-8").splitlines()
    changed = False
    for index, line in enumerate(lines):
        if line.startswith("**Last Updated**:"):
            lines[index] = f"**Last Updated**: {timestamp}"
            changed = True
            break
    if changed:
        tracker_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _update_tracker_plan_step(tracker_path: Path, plan_step: str, plan_status: str) -> None:
    if plan_status != "completed":
        return
    lines = tracker_path.read_text(encoding="utf-8").splitlines()
    changed = False
    for index, line in enumerate(lines):
        if line.startswith("- [ ] ") and plan_step in line:
            lines[index] = line.replace("- [ ] ", "- [x] ", 1)
            changed = True
    if changed:
        tracker_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _markdown_table_cell(value: str) -> str:
    """Render untrusted evidence text as a single markdown-table cell."""
    collapsed = re.sub(r"\s+", " ", str(value)).strip()
    return collapsed.replace("|", "&#124;")


def _canonical_plan_step_rows(current_work: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    work_rel = str(paths.get("work_tracking") or "docs/ai/work-tracking/active/<folder>")
    reports_rel = str(paths.get("reports") or f"{work_rel}/reports")
    tracker_rel = f"{work_rel}/TRACKER.md"
    rows = {step: dict(payload) for step, payload in AEGIS_PLAN_STEP_DEFAULTS.items()}
    rows["plan-step-scope"]["evidence"] = f"{work_rel}/FINDINGS.md; {work_rel}/DECISIONS.md"
    rows["plan-step-implement"]["evidence"] = f"{work_rel}/IMPLEMENTATION.md; changed files"
    rows["plan-step-verify"]["evidence"] = f"{reports_rel}/; {work_rel}/HANDOFF.md; {tracker_rel}"
    return rows


def _plan_table_row_line(step: str, row: Mapping[str, str]) -> str:
    description = _markdown_table_cell(str(row.get("description") or ""))
    evidence = _markdown_table_cell(str(row.get("evidence") or ""))
    status = str(row.get("status") or "pending").strip().lower()
    if status not in AEGIS_PLAN_STATUS_CHOICES:
        status = "pending"
    return f"| {step} | {description} | {evidence} | {status} |"


def _recover_plan_table_row(
    step: str,
    block: Sequence[str],
    *,
    canonical_rows: Mapping[str, Mapping[str, str]],
    tracker_steps: Mapping[str, str],
) -> dict[str, str]:
    canonical = canonical_rows[step]
    joined = " ".join(line.strip() for line in block if line.strip())
    cells = [cell.strip() for cell in joined.strip().strip("|").split("|")]
    status = str(canonical.get("status") or "pending").strip().lower()
    status_index: int | None = None
    for index in range(len(cells) - 1, 1, -1):
        candidate = cells[index].strip().lower()
        if candidate in AEGIS_PLAN_STATUS_CHOICES:
            status = candidate
            status_index = index
            break
    if status_index is None and tracker_steps.get(step) == "completed":
        status = "completed"
    evidence_cells = cells[2:status_index] if status_index is not None else cells[2:]
    evidence = " | ".join(cell for cell in evidence_cells if cell).strip()
    if not evidence:
        evidence = str(canonical.get("evidence") or "")
    return {
        "description": str(canonical.get("description") or ""),
        "evidence": evidence,
        "status": status,
    }


def _normalize_plan_table_text(
    text: str,
    current_work: Mapping[str, Any],
    *,
    tracker_steps: Mapping[str, str] | None = None,
) -> tuple[str, list[str]]:
    canonical_rows = _canonical_plan_step_rows(current_work)
    tracker_statuses = dict(tracker_steps or {})
    lines = text.splitlines()
    output: list[str] = []
    repaired_steps: list[str] = []
    seen_steps: set[str] = set()
    index = 0
    while index < len(lines):
        line = lines[index]
        match = AEGIS_PLAN_STEP_ROW_RE.match(line)
        if match and match.group(1) in canonical_rows:
            step = match.group(1)
            block = [line]
            index += 1
            while index < len(lines):
                next_line = lines[index]
                if AEGIS_PLAN_STEP_ROW_RE.match(next_line) or next_line.lstrip().startswith("## "):
                    break
                block.append(next_line)
                index += 1
            repaired = _recover_plan_table_row(
                step,
                block,
                canonical_rows=canonical_rows,
                tracker_steps=tracker_statuses,
            )
            repaired_line = _plan_table_row_line(step, repaired)
            if block != [repaired_line]:
                repaired_steps.append(step)
            output.append(repaired_line)
            seen_steps.add(step)
            continue
        output.append(line)
        index += 1

    missing_steps = [step for step in canonical_rows if step not in seen_steps]
    if missing_steps:
        try:
            separator_index = next(
                idx
                for idx, value in enumerate(output)
                if value.strip() == "| --- | --- | --- | --- |"
            )
        except StopIteration:
            separator_index = -1
        if separator_index >= 0:
            insertion = separator_index + 1
            for step in missing_steps:
                output.insert(insertion, _plan_table_row_line(step, canonical_rows[step]))
                repaired_steps.append(step)
                insertion += 1
    normalized = "\n".join(output).rstrip() + "\n"
    return normalized, sorted(
        set(repaired_steps), key=lambda step: tuple(canonical_rows).index(step)
    )


def _plan_table_repair_preview(
    target_root: Path,
    current_work: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(current_work, Mapping):
        return None
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    plan_rel = str(paths.get("plan") or "").strip()
    work_rel = str(paths.get("work_tracking") or "").strip()
    if not plan_rel:
        return None
    plan_path = target_root / plan_rel
    if not plan_path.is_file():
        return None
    tracker_path = target_root / work_rel / "TRACKER.md" if work_rel else None
    tracker_steps = _parse_tracker_plan_steps(tracker_path) if tracker_path is not None else {}
    original = plan_path.read_text(encoding="utf-8")
    normalized, repaired_steps = _normalize_plan_table_text(
        original,
        current_work,
        tracker_steps=tracker_steps,
    )
    if normalized == original:
        return None
    return {
        "path": plan_rel,
        "text": normalized,
        "steps": repaired_steps,
    }


def _update_plan_table(
    plan_path: Path,
    *,
    plan_step: str,
    plan_status: str,
    evidence_rel: str,
    timestamp: str,
) -> bool:
    if not plan_path.is_file():
        raise AegisError(f"required workflow file missing: {plan_path}")
    lines = plan_path.read_text(encoding="utf-8").splitlines()
    changed = False
    for index, line in enumerate(lines):
        if not line.startswith(f"| {plan_step} |"):
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) != 4:
            raise AegisError(f"plan row for {plan_step} is malformed")
        evidence = columns[2]
        evidence_cell = _markdown_table_cell(evidence_rel)
        if evidence_cell not in evidence:
            evidence = f"{evidence}; {evidence_cell}" if evidence else evidence_cell
        current_status = columns[3]
        next_status = current_status
        if current_status not in {"completed", "n/a"} or plan_status == "completed":
            next_status = plan_status
        lines[index] = f"| {columns[0]} | {columns[1]} | {evidence} | {next_status} |"
        changed = True
        break
    if not changed:
        raise AegisError(f"plan step not found in current plan: {plan_step}")
    amendment_evidence = _markdown_table_cell(evidence_rel).replace("`", "'")
    amendment = f"- {timestamp} - `aegis log` updated `{plan_step}` to `{plan_status}` with evidence `{amendment_evidence}`."
    if amendment not in lines:
        try:
            heading_index = next(
                index
                for index, value in enumerate(lines)
                if value.strip() == "## Amendments & Versioning"
            )
        except StopIteration:
            lines.extend(["", "## Amendments & Versioning", amendment])
        else:
            insert_at = len(lines)
            for index in range(heading_index + 1, len(lines)):
                stripped = lines[index].strip()
                if stripped.startswith("#") and stripped != "## Amendments & Versioning":
                    insert_at = index
                    break
            while insert_at > heading_index + 1 and not lines[insert_at - 1].strip():
                insert_at -= 1
            lines.insert(insert_at, amendment)
    plan_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def _bounded_pending_value(value: Any) -> str:
    text = str(value or "")
    if len(text) <= AEGIS_PENDING_TRACKING_SAMPLE_TEXT_LIMIT:
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:10]
    suffix = f"…#{digest}"
    return text[: AEGIS_PENDING_TRACKING_SAMPLE_TEXT_LIMIT - len(suffix)] + suffix


def _pending_event_sample(event: Any, index: int) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        return {
            "index": index,
            "valid": False,
            "type": type(event).__name__,
            "mode": "unknown",
        }
    affected_paths = event.get("affected_paths")
    affected = (
        [
            _bounded_pending_value(path)
            for path in affected_paths[:AEGIS_PENDING_TRACKING_SAMPLE_LIMIT]
        ]
        if isinstance(affected_paths, list)
        else []
    )
    sample: dict[str, Any] = {
        "index": index,
        "valid": True,
        "id": _bounded_pending_value(event.get("id")),
        "mode": _bounded_pending_value(event.get("mode")),
        "tool": _bounded_pending_value(event.get("tool")),
        "handler": _bounded_pending_value(event.get("handler")),
        "evidence": _bounded_pending_value(event.get("evidence")),
    }
    if isinstance(affected_paths, list):
        sample["affected_path_count"] = len(affected_paths)
        sample["affected_paths"] = affected
        sample["affected_paths_truncated"] = len(affected_paths) > len(affected)
    return sample


def _classify_pending_tracking(target_root: Path) -> dict[str, Any]:
    """Classify the complete pending queue without mutating or silently filtering it.

    Advisory-only events are retained audit evidence and are delivery-safe. Explicit
    strict events and every untrusted queue shape fail closed. The returned payload is
    intentionally bounded; the queue artifact remains the complete source of evidence.
    """

    pending_path = target_root / AEGIS_PENDING_TRACKING_REL
    base: dict[str, Any] = {
        "path": AEGIS_PENDING_TRACKING_REL,
        "file_exists": pending_path.exists() or pending_path.is_symlink(),
        "queue_valid": True,
        "provenance_trusted": True,
        "classification": "absent",
        "delivery_allowed": True,
        "advisory_preserved": False,
        "required_unresolved": False,
        "untrusted_unresolved": False,
        "counts": {
            "total": 0,
            "advisory": 0,
            "required": 0,
            "unknown": 0,
        },
        "sample": [],
        "sample_limit": AEGIS_PENDING_TRACKING_SAMPLE_LIMIT,
        "sample_truncated": False,
        "reason": "pending tracking queue absent",
    }
    if not base["file_exists"]:
        return base
    if not pending_path.is_file() or pending_path.is_symlink():
        return {
            **base,
            "queue_valid": False,
            "provenance_trusted": False,
            "classification": "malformed",
            "delivery_allowed": False,
            "untrusted_unresolved": True,
            "reason": "pending tracking queue must be a regular file",
        }
    try:
        raw = pending_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {
            **base,
            "queue_valid": False,
            "provenance_trusted": False,
            "classification": "malformed",
            "delivery_allowed": False,
            "untrusted_unresolved": True,
            "reason": f"pending tracking queue is unreadable: {type(exc).__name__}",
        }
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {
            **base,
            "queue_valid": False,
            "provenance_trusted": False,
            "classification": "malformed",
            "delivery_allowed": False,
            "untrusted_unresolved": True,
            "reason": "pending tracking queue is invalid JSON",
        }
    if not isinstance(payload, Mapping):
        return {
            **base,
            "queue_valid": False,
            "provenance_trusted": False,
            "classification": "malformed",
            "delivery_allowed": False,
            "untrusted_unresolved": True,
            "reason": "pending tracking queue payload is not an object",
        }
    events = payload.get("events")
    if not isinstance(events, list):
        return {
            **base,
            "queue_valid": False,
            "provenance_trusted": False,
            "classification": "malformed",
            "delivery_allowed": False,
            "untrusted_unresolved": True,
            "reason": "pending tracking queue events field is not a list",
        }

    advisory_count = 0
    required_count = 0
    unknown_count = 0
    invalid_event_shape = False
    sample: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if len(sample) < AEGIS_PENDING_TRACKING_SAMPLE_LIMIT:
            sample.append(_pending_event_sample(event, index))
        if not isinstance(event, Mapping):
            invalid_event_shape = True
            unknown_count += 1
            continue
        mode = str(event.get("mode") or "").strip().lower()
        if mode == "advisory":
            advisory_count += 1
        elif mode == "strict":
            required_count += 1
        else:
            unknown_count += 1

    if not events:
        classification = "empty"
        reason = "pending tracking queue empty"
    elif unknown_count:
        classification = "unknown"
        reason = "pending tracking queue contains invalid events or untrusted provenance"
    elif advisory_count and required_count:
        classification = "mixed"
        reason = "pending tracking queue mixes advisory evidence with required strict events"
    elif required_count:
        classification = "required_only"
        reason = "pending tracking queue contains unresolved required strict events"
    else:
        classification = "advisory_only"
        reason = "advisory pending events are preserved audit evidence and do not block delivery"

    delivery_allowed = classification in {"empty", "advisory_only"}
    return {
        **base,
        "queue_valid": not invalid_event_shape,
        "provenance_trusted": unknown_count == 0,
        "classification": classification,
        "delivery_allowed": delivery_allowed,
        "advisory_preserved": classification == "advisory_only",
        "required_unresolved": required_count > 0,
        "untrusted_unresolved": unknown_count > 0,
        "counts": {
            "total": len(events),
            "advisory": advisory_count,
            "required": required_count,
            "unknown": unknown_count,
        },
        "sample": sample,
        "sample_truncated": len(events) > len(sample),
        "reason": reason,
    }


def _pending_tracking_events(target_root: Path) -> list[dict[str, Any]]:
    payload = _read_json(target_root / AEGIS_PENDING_TRACKING_REL)
    if not payload:
        return []
    events = payload.get("events")
    return (
        [event for event in events if isinstance(event, dict)] if isinstance(events, list) else []
    )


def _degraded_events(target_root: Path) -> list[dict[str, Any]]:
    payload = _read_json(target_root / AEGIS_DEGRADED_EVENTS_REL)
    if not payload:
        return []
    events = payload.get("events")
    return (
        [event for event in events if isinstance(event, dict)] if isinstance(events, list) else []
    )


def _write_pending_tracking_events(target_root: Path, events: list[dict[str, Any]]) -> None:
    path = target_root / AEGIS_PENDING_TRACKING_REL
    if not events:
        if path.exists():
            path.unlink()
        return
    _write_text(
        target_root,
        AEGIS_PENDING_TRACKING_REL,
        _dump_json(
            {
                "schema_version": SCHEMA_VERSION,
                "updated_at": _iso_now(),
                "events": events,
            }
        ),
    )


def _event_matches_current_work(event: Mapping[str, Any], *, task_id: str, slug: str) -> bool:
    task = event.get("task") if isinstance(event.get("task"), Mapping) else {}
    return str(task.get("id") or "") == task_id and str(task.get("slug") or "") == slug


_TARGET_GATE_LIB_CACHE: dict[str, Any] = {}


def _load_target_gate_lib(target_root: Path) -> Any | None:
    """Import the TARGET repo's .claude/scripts/gate_lib.py for read-only classification
    at drain time (TM 221). Uses the target's own copy so events are classified by the
    same gate version that recorded them. Fail-None on any problem — callers fail-KEEP."""

    script = Path(target_root) / ".claude" / "scripts" / "gate_lib.py"
    key = str(script.resolve()) if script.exists() else str(script)
    if key in _TARGET_GATE_LIB_CACHE:
        return _TARGET_GATE_LIB_CACHE[key]
    module: Any | None = None
    try:
        if script.is_file():
            spec = importlib.util.spec_from_file_location("_aegis_log_gate_lib", script)
            if spec is not None and spec.loader is not None:
                candidate = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = candidate  # required before exec for dataclasses
                spec.loader.exec_module(candidate)
                module = candidate
    except Exception:  # noqa: BLE001 - any import failure => fail-KEEP (treat as mutation)
        module = None
    _TARGET_GATE_LIB_CACHE[key] = module
    return module


def _stored_event_is_read_only(target_root: Path, event: Mapping[str, Any]) -> bool:
    """Strict, fail-KEEP classifier for a stored pending-tracking event (TM 221).

    Returns True ONLY when the event's originating action is provably read-only, so its
    evidence can be drained/purged without accreting into required closeout evidence.
    Classifies by tool + recovered command/tool-name, NEVER by evidence-token shape (a
    read-only `cat app/x.ts` is byte-identical to a real edit of app/x.ts). Any
    uncertainty — unknown tool, lost command, apply-gated MCP, import failure — returns
    False so genuine mutations are never discarded.
    """

    try:
        gl = _load_target_gate_lib(target_root)
        if gl is None:
            return False
        tool = str(event.get("tool") or "")
        evidence = str(event.get("evidence") or "")
        if tool in getattr(
            gl, "FILE_MUTATION_TOOLS", {"Edit", "Write", "MultiEdit", "NotebookEdit"}
        ):
            return False
        if tool == "Bash":
            # The command is recoverable only when evidence kept the cmd`...` wrapper.
            # Redirect-target / aegis-verify evidence means the command was already a
            # mutation (bash_is_read_only is False on persistent redirects) -> KEEP.
            if evidence.startswith("cmd`") and evidence.endswith("`") and len(evidence) > 5:
                inner = evidence[4:-1]
                return bool(gl.bash_is_read_only(inner))
            return False
        if tool.startswith("mcp__"):
            # Name-only classification (tool_input is NOT persisted in the event). Discard
            # ONLY unconditionally repo-non-mutating tools. Apply-gated aegis tools
            # (repair/runtime_update/handoff_repair) and target-dir-sensitive aegis
            # read-only tools depend on un-persisted tool_input, so they are KEPT — closing
            # the apply-gated escape the adversarial review flagged.
            if gl.MCP_MUTATION_TOOL_RE.search(tool):
                return False
            normalized = gl.normalized_mcp_tool_name(tool)
            if "__chrome_devtools__" in normalized or "__playwright__" in normalized:
                return True  # browser observation never mutates the repo, no apply gate
            if any(
                normalized.endswith(f"__{suffix}")
                for suffix in getattr(gl, "TASKMASTER_READ_ONLY_MCP_TOOL_SUFFIXES", set())
            ):
                return True
            if gl.MCP_READ_ONLY_TOOL_RE.search(tool):
                return True
            return False  # aegis suffixes, apply-gated, and unknown MCP tools -> KEEP
        return False
    except Exception:  # noqa: BLE001 - fail-KEEP on any classifier fault.
        return False


def _resolve_pending_tracking_event(
    events: Sequence[Mapping[str, Any]],
    pending_event_id: str,
    *,
    task_id: str,
    slug: str,
) -> Mapping[str, Any]:
    clean = pending_event_id.strip()
    if not clean:
        raise AegisError("pending event id cannot be empty")
    current_events = [
        event for event in events if _event_matches_current_work(event, task_id=task_id, slug=slug)
    ]
    valid_ids = [str(event.get("id") or "unknown") for event in current_events]
    valid = ", ".join(valid_ids[:AEGIS_PENDING_TRACKING_SAMPLE_LIMIT]) or "<none>"
    if len(valid_ids) > AEGIS_PENDING_TRACKING_SAMPLE_LIMIT:
        valid += (
            f", ... {len(valid_ids) - AEGIS_PENDING_TRACKING_SAMPLE_LIMIT} more "
            f"(inspect {AEGIS_PENDING_TRACKING_REL})"
        )
    if clean in AEGIS_PENDING_EVENT_SENTINELS:
        if len(current_events) != 1:
            raise AegisError(
                f"pending event sentinel '{clean}' requires exactly one current-work event; valid ids: {valid}"
            )
        return current_events[0]
    matches = [event for event in current_events if str(event.get("id") or "") == clean]
    if len(matches) == 1:
        return matches[0]
    raise AegisError(f"unknown pending event id: {clean}; valid ids: {valid}")


def _format_pending_tracking_for_error(events: Sequence[Mapping[str, Any]]) -> str:
    lines = []
    for event in events[:AEGIS_PENDING_TRACKING_SAMPLE_LIMIT]:
        event_id = event.get("id", "unknown")
        lines.append(
            f"- {event_id}: "
            f"H={event.get('handler', 'unknown')} "
            f"E={event.get('evidence', 'unknown')}"
        )
        location = event.get("evidence_location")
        if isinstance(location, Mapping) and location.get("display"):
            lines.append(
                f"  location: {location['display']} ({location.get('confidence', 'unknown')})"
            )
        lines.append(
            "  repair: aegis log --pending-id "
            f'{event_id} --note "<past-tense note>" '
            "--plan-step <plan-step-id> --plan-status completed"
        )
    omitted = len(events) - min(len(events), AEGIS_PENDING_TRACKING_SAMPLE_LIMIT)
    if omitted:
        lines.append(
            f"... {omitted} more pending events; inspect {AEGIS_PENDING_TRACKING_REL} "
            f"for all {len(events)}."
        )
    return "\n".join(lines)


def _evidence_file_location(target_root: Path, evidence_rel: str) -> dict[str, Any] | None:
    if not evidence_rel or evidence_rel.startswith("cmd`"):
        return None
    path = Path(evidence_rel)
    resolved = path if path.is_absolute() else target_root / evidence_rel
    try:
        line_count = len(resolved.read_text(encoding="utf-8").splitlines())
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    line_start = 1 if line_count > 0 else None
    line_end = line_count if line_count > 0 else None
    display = evidence_rel
    if line_start is not None:
        display = (
            f"{evidence_rel}:{line_start}"
            if line_end == line_start
            else f"{evidence_rel}:{line_start}-{line_end}"
        )
    return {
        "path": evidence_rel,
        "line_start": line_start,
        "line_end": line_end,
        "line_count": line_count,
        "source": "log_file_snapshot",
        "confidence": "file_snapshot",
        "display": display,
    }


def _next_action_after_log(
    *,
    target_root: Path,
    remaining: Sequence[Mapping[str, Any]],
    normalized_plan_step: str,
    normalized_plan_status: str,
    evidence_rel: str,
    work_rel: str,
    reports_rel: str,
) -> dict[str, Any]:
    implementation_handler = _workflow_log_handler(target_root, "implementation")
    verification_handler = _workflow_log_handler(target_root, "verification")
    pending_tracking_expected = _expects_pending_tracking(target_root)
    workflow_cli = _workflow_cli_command(target_root)
    if remaining:
        event_ids = [str(event.get("id") or "unknown") for event in remaining]
        return _workflow_next_action(
            "log_remaining_pending_event",
            "A pending mutation still exists. Log it before any further mutation or closeout.",
            suggested_cli=(
                f"{workflow_cli} log --target-dir . --pending-id current "
                "--note '<past-tense note>' --plan-step <plan-step-id> --plan-status completed"
            ),
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments={
                "target_dir": ".",
                "pending_event_id": "current",
                "note": "<past-tense note>",
                "plan_step": "<plan-step-id>",
                "plan_status": "completed",
                "apply": True,
            },
            details={"remaining_pending_event_ids": event_ids},
        )
    if normalized_plan_step == "plan-step-scope" and normalized_plan_status == "completed":
        if pending_tracking_expected:
            after_mutation = (
                f"{workflow_cli} log --target-dir . --pending-id current "
                "--note '<past-tense note>' --plan-step plan-step-implement --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "pending_event_id": "current",
                "note": "<past-tense implementation note>",
                "plan_step": "plan-step-implement",
                "plan_status": "completed",
                "apply": True,
            }
        else:
            after_mutation = (
                f"{workflow_cli} log --target-dir . --handler {implementation_handler} "
                "--evidence '<changed-file-or-command>' --note '<past-tense implementation note>' "
                "--plan-step plan-step-implement --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "handler": implementation_handler,
                "evidence": "<changed-file-or-command>",
                "note": "<past-tense implementation note>",
                "event_class": "implementation",
                "plan_step": "plan-step-implement",
                "plan_status": "completed",
                "apply": True,
            }
        return _workflow_next_action(
            "make_task_scoped_source_change",
            (
                "Scope is logged. Make the requested code/docs change with native tools, "
                "then log the pending event."
                if pending_tracking_expected
                else "Scope is logged. Make the requested code/docs change with native tools, then log explicit implementation evidence."
            ),
            suggested_cli=after_mutation,
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments=suggested_mcp_arguments,
            details={
                "after_mutation": after_mutation,
                "pending_tracking_expected": pending_tracking_expected,
            },
        )
    if normalized_plan_step == "plan-step-implement" and normalized_plan_status == "completed":
        verification_rel = f"{reports_rel}/task-verification.md"
        if pending_tracking_expected:
            suggested_cli = (
                "# write verification evidence, then:\n"
                f"{workflow_cli} log --target-dir . --pending-id current "
                "--note 'Recorded task-specific verification evidence' "
                "--plan-step plan-step-verify --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "pending_event_id": "current",
                "note": "Recorded task-specific verification evidence",
                "plan_step": "plan-step-verify",
                "plan_status": "completed",
                "apply": True,
            }
        else:
            suggested_cli = (
                f"# write verification evidence, then:\n"
                f"{workflow_cli} log --target-dir . --handler {verification_handler} "
                f"--evidence {_quote_cli(verification_rel)} "
                "--note 'Recorded task-specific verification evidence' "
                "--plan-step plan-step-verify --plan-status completed"
            )
            suggested_mcp_arguments = {
                "target_dir": ".",
                "handler": verification_handler,
                "evidence": verification_rel,
                "note": "Recorded task-specific verification evidence",
                "event_class": "verification",
                "plan_step": "plan-step-verify",
                "plan_status": "completed",
                "apply": True,
            }
        return _workflow_next_action(
            "run_task_specific_verification",
            "Implementation is logged. Run the project's relevant verification and save a short report before strict Aegis verify.",
            suggested_cli=suggested_cli,
            suggested_mcp_tool="aegis.log",
            suggested_mcp_arguments=suggested_mcp_arguments,
            details={
                "verification_report_pattern": verification_rel,
                "pending_tracking_expected": pending_tracking_expected,
            },
        )
    if normalized_plan_step == "plan-step-verify" and normalized_plan_status == "completed":
        if evidence_rel == AEGIS_VERIFY_REPORT_REL:
            return _workflow_next_action(
                "run_closeout",
                "Strict verification is logged. Run closeout readiness/dry-run, then final closeout before reporting the task complete.",
                suggested_cli=f"{workflow_cli} closeout --target-dir . --dry-run --update-handoff",
                suggested_mcp_tool="aegis.closeout_ready",
                suggested_mcp_arguments={
                    "target_dir": ".",
                    "update_handoff": True,
                },
            )
        return _workflow_next_action(
            "run_strict_verify",
            "Task-specific verification is logged. Run strict Aegis verification next, then log its pending event.",
            suggested_cli=f"{workflow_cli} verify --target-dir . --strict",
            suggested_mcp_tool="aegis.verify",
            suggested_mcp_arguments={
                "target_dir": ".",
                "strict": True,
                "acknowledge_report_write": True,
            },
        )
    return _workflow_next_action(
        "continue_workflow",
        "Progress was logged. Check readiness and pending tracking before the next mutation.",
        suggested_cli=f"{workflow_cli} gate readiness --quick --target-dir .",
    )


@serialized_session_writer
def log_work(
    target_dir: str | Path,
    *,
    handler: str | None = None,
    evidence: str | None = None,
    note: str,
    surfaces: Sequence[str] | None = None,
    plan_step: str | None = None,
    plan_status: str | None = "in-progress",
    event_class: str | None = None,
    pending_event_id: str | None = None,
) -> dict[str, Any]:
    """Append S:W:H:E progress entries, update workflow surfaces, and clear pending tracking."""

    target_root = _resolve_target_root(target_dir)
    try:
        assert_no_pending_continuation(target_root)
    except SessionAuthorityError as exc:
        raise AegisError(str(exc)) from exc
    current_work = _current_work_payload(target_root)
    try:
        verify_session_authority(target_root, current_work)
    except SessionAuthorityError as exc:
        raise AegisError(str(exc)) from exc
    task = current_work.get("task") if isinstance(current_work.get("task"), dict) else {}
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), dict) else {}
    task_id = str(task.get("id") or "").strip()
    slug = str(task.get("slug") or "").strip()
    if not task_id or not slug:
        raise AegisError("current work task id and slug are required before logging")
    clean_note = note.strip()
    if not clean_note:
        raise AegisError("note is required")

    session_rel = str(paths.get("session") or "")
    plan_rel = str(paths.get("plan") or "")
    work_rel = str(paths.get("work_tracking") or "")
    reports_rel = str(paths.get("reports") or f"{work_rel}/reports/<slug>")
    if not session_rel or not plan_rel or not work_rel:
        raise AegisError("current work paths are incomplete; rerun aegis kickoff")
    session_path = target_root / session_rel
    plan_path = target_root / plan_rel
    tracker_path = target_root / work_rel / "TRACKER.md"

    pending_before = _pending_tracking_events(target_root)
    resolved_pending_event: Mapping[str, Any] | None = None
    if pending_event_id:
        resolved_pending_event = _resolve_pending_tracking_event(
            pending_before,
            pending_event_id,
            task_id=task_id,
            slug=slug,
        )
        # TM 221: a read-only/inspection pending event (pre-#224 backlog false-positive)
        # must NOT accrete its evidence into surfaces or the plan-step required-evidence
        # cell. Drain it from the queue and return without writing anything.
        if _stored_event_is_read_only(target_root, resolved_pending_event):
            resolved_id = str(resolved_pending_event.get("id") or "")
            remaining = [e for e in pending_before if str(e.get("id") or "") != resolved_id]
            _write_pending_tracking_events(target_root, remaining)
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "purged_read_only",
                "logged_at": _iso_now(),
                "target_root": str(target_root),
                "entry": None,
                "purged_event": {
                    "id": resolved_id,
                    "tool": resolved_pending_event.get("tool"),
                    "evidence": resolved_pending_event.get("evidence"),
                },
                "paths": {"pending_tracking": AEGIS_PENDING_TRACKING_REL},
            }
        handler = str(resolved_pending_event.get("handler") or "")
        evidence = str(resolved_pending_event.get("evidence") or "")

    clean_handler = (handler or "").strip()
    if not clean_handler:
        raise AegisError("handler is required unless --pending-id identifies a pending event")
    evidence_rel = _normalize_evidence(target_root, evidence or "")
    pending_location = (
        resolved_pending_event.get("evidence_location")
        if isinstance(resolved_pending_event, Mapping)
        else None
    )
    evidence_location = (
        dict(pending_location)
        if isinstance(pending_location, Mapping)
        else _evidence_file_location(target_root, evidence_rel)
    )
    normalized_event_class = _infer_log_event_class(
        plan_step="" if (plan_step or "").strip().lower() == "auto" else (plan_step or "").strip(),
        handler=clean_handler,
        evidence=evidence_rel,
        explicit_event_class=event_class,
    )
    if normalized_event_class == "note" and _pending_event_is_confident_implementation(
        resolved_pending_event
    ):
        normalized_event_class = "implementation"
    normalized_plan_step, plan_step_inferred, plan_inference_reason = _resolve_plan_step_argument(
        plan_step,
        event_class=normalized_event_class,
        handler=clean_handler,
        evidence=evidence_rel,
        pending_event=resolved_pending_event,
    )
    normalized_plan_status = _normalize_plan_status(plan_status) if normalized_plan_step else ""
    log_surfaces = _normalize_log_surfaces(
        surfaces,
        default_surfaces=_default_log_surfaces_for_event(normalized_event_class),
    )

    now = datetime.now().astimezone().replace(microsecond=0)
    session_value = now.strftime("%Y%m%d")
    date_value = now.strftime("%Y-%m-%d")
    work_mode = str(current_work.get("mode") or "task").strip()
    work_context = f"{task_id}-{slug}" if work_mode == "bead" else f"task{task_id}-{slug}"
    swhe = f"[S:{session_value}|W:{work_context}|H:{clean_handler}|E:{evidence_rel}]"
    session_line = f"- **[{now.strftime('%H:%M')}]** - {swhe} {clean_note}"
    tracker_line = f"- **{now.strftime('%Y-%m-%d %H:%M %Z').strip()}** - {swhe} {clean_note}"

    existing_session_text = _read_text_or_empty(session_path)
    existing_tracker_text = _read_text_or_empty(tracker_path)
    already_logged = swhe in existing_session_text and swhe in existing_tracker_text

    if resolved_pending_event is not None:
        resolved_id = str(resolved_pending_event.get("id") or "")
        cleared = [event for event in pending_before if str(event.get("id") or "") == resolved_id]
    else:
        cleared = [
            event for event in pending_before if str(event.get("evidence") or "") == evidence_rel
        ]
    if pending_before and not cleared:
        pending_summary = _format_pending_tracking_for_error(pending_before)
        raise AegisError(
            "aegis log evidence does not match any pending S:W:H:E tracking event. "
            "Log the pending evidence first or inspect .aegis/state/pending-tracking.json.\n"
            f"Pending tracking:\n{pending_summary}"
        )
    if already_logged and not pending_before:
        updated_surfaces: dict[str, str] = {}
        replay_line = f"- **{now.strftime('%Y-%m-%d %H:%M %Z').strip()}** - {swhe} {clean_note}"
        for surface in log_surfaces:
            rel_path = f"{work_rel}/{AEGIS_LOG_SURFACES[surface]}"
            surface_path = target_root / rel_path
            if swhe in _read_text_or_empty(surface_path):
                continue
            _append_progress_entry(surface_path, "## Progress Log", replay_line)
            updated_surfaces[surface] = rel_path

        plan_updated = False
        if normalized_plan_step:
            plan_rows = _parse_plan_rows(plan_path)
            row = plan_rows.get(normalized_plan_step)
            evidence_text = str(row.get("evidence") or "") if isinstance(row, Mapping) else ""
            row_status = str(row.get("status") or "") if isinstance(row, Mapping) else ""
            evidence_cell = _markdown_table_cell(evidence_rel)
            needs_plan_update = evidence_cell not in evidence_text or (
                normalized_plan_status == "completed" and row_status not in {"completed", "done"}
            )
            if needs_plan_update:
                plan_updated = _update_plan_table(
                    plan_path,
                    plan_step=normalized_plan_step,
                    plan_status=normalized_plan_status,
                    evidence_rel=evidence_rel,
                    timestamp=date_value,
                )
                _update_tracker_plan_step(
                    tracker_path, normalized_plan_step, normalized_plan_status
                )

        if updated_surfaces or plan_updated:
            _update_tracker_timestamp(tracker_path, date_value)
            current_work["updated_at"] = _iso_now()
            _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(current_work))

        return {
            "schema_version": SCHEMA_VERSION,
            "status": "logged" if (updated_surfaces or plan_updated) else "already_logged",
            "logged_at": _iso_now(),
            "target_root": str(target_root),
            "entry": {
                "session": session_line,
                "tracker": tracker_line,
                "s": session_value,
                "w": work_context,
                "h": clean_handler,
                "e": evidence_rel,
                "note": clean_note,
                "event_class": normalized_event_class,
                "evidence_location": evidence_location,
            },
            "paths": {
                "session": session_rel,
                "plan": plan_rel,
                "tracker": f"{work_rel}/TRACKER.md",
                "surfaces": updated_surfaces,
                "pending_tracking": AEGIS_PENDING_TRACKING_REL,
            },
            "plan": {
                "updated": plan_updated,
                "step": normalized_plan_step or None,
                "status": normalized_plan_status or None,
                "evidence": evidence_rel,
                "inferred": plan_step_inferred,
                "inference_reason": plan_inference_reason,
                "strict_verification_evidence": (
                    evidence_rel == AEGIS_VERIFY_REPORT_REL
                    and normalized_plan_step == "plan-step-verify"
                ),
            },
            "pending": {
                "cleared": 0,
                "remaining": 0,
                "cleared_events": [],
                "pending_event_id": pending_event_id or None,
            },
            "idempotent": not (updated_surfaces or plan_updated),
            "replay_completed_missing_surfaces": bool(updated_surfaces or plan_updated),
            "next_action": _next_action_after_log(
                target_root=target_root,
                remaining=[],
                normalized_plan_step=normalized_plan_step,
                normalized_plan_status=normalized_plan_status,
                evidence_rel=evidence_rel,
                work_rel=work_rel,
                reports_rel=reports_rel,
            ),
        }

    _append_progress_entry(session_path, "### Progress Log", session_line)
    _append_progress_entry(tracker_path, "## Progress Log", tracker_line)
    _update_tracker_timestamp(tracker_path, date_value)

    updated_surfaces: dict[str, str] = {}
    for surface in log_surfaces:
        rel_path = f"{work_rel}/{AEGIS_LOG_SURFACES[surface]}"
        _append_progress_entry(target_root / rel_path, "## Progress Log", tracker_line)
        updated_surfaces[surface] = rel_path

    plan_updated = False
    if normalized_plan_step:
        plan_updated = _update_plan_table(
            plan_path,
            plan_step=normalized_plan_step,
            plan_status=normalized_plan_status,
            evidence_rel=evidence_rel,
            timestamp=date_value,
        )
        _update_tracker_plan_step(tracker_path, normalized_plan_step, normalized_plan_status)

    if resolved_pending_event is not None:
        resolved_id = str(resolved_pending_event.get("id") or "")
        remaining = [event for event in pending_before if str(event.get("id") or "") != resolved_id]
    else:
        remaining = [
            event for event in pending_before if str(event.get("evidence") or "") != evidence_rel
        ]
    _write_pending_tracking_events(target_root, remaining)

    current_work["updated_at"] = _iso_now()
    _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(current_work))

    entry_payload: dict[str, Any] = {
        "session": session_line,
        "tracker": tracker_line,
        "s": session_value,
        "w": work_context,
        "h": clean_handler,
        "e": evidence_rel,
        "note": clean_note,
        "event_class": normalized_event_class,
    }
    if evidence_location:
        entry_payload["evidence_location"] = evidence_location

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "logged",
        "logged_at": _iso_now(),
        "target_root": str(target_root),
        "entry": entry_payload,
        "paths": {
            "session": session_rel,
            "plan": plan_rel,
            "tracker": f"{work_rel}/TRACKER.md",
            "surfaces": updated_surfaces,
            "pending_tracking": AEGIS_PENDING_TRACKING_REL,
        },
        "plan": {
            "updated": plan_updated,
            "step": normalized_plan_step or None,
            "status": normalized_plan_status or None,
            "evidence": evidence_rel,
            "inferred": plan_step_inferred,
            "inference_reason": plan_inference_reason,
            "strict_verification_evidence": (
                evidence_rel == AEGIS_VERIFY_REPORT_REL
                and normalized_plan_step == "plan-step-verify"
            ),
        },
        "pending": {
            "cleared": len(cleared),
            "remaining": len(remaining),
            "cleared_events": cleared,
            "pending_event_id": pending_event_id or None,
        },
        "next_action": _next_action_after_log(
            target_root=target_root,
            remaining=remaining,
            normalized_plan_step=normalized_plan_step,
            normalized_plan_status=normalized_plan_status,
            evidence_rel=evidence_rel,
            work_rel=work_rel,
            reports_rel=reports_rel,
        ),
    }


def install(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    profile: str = PROFILE_GENERIC,
    primary_agent: str,
    agents: Sequence[str] | None,
    apply: bool,
    baseline_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not apply:
        return plan_install(
            target_dir,
            source_root=source_root,
            profile=profile,
            primary_agent=primary_agent,
            agents=agents,
            mode="dry_run",
            apply_confirmed=False,
            baseline_manifest=baseline_manifest,
        )
    target_root = _resolve_target_root(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    enabled_agents = _enabled_agents(primary_agent, agents)
    source = Path(source_root).resolve()
    plan = plan_install(
        target_root,
        source_root=source,
        profile=profile,
        primary_agent=primary_agent,
        agents=enabled_agents,
        mode="apply",
        apply_confirmed=True,
        baseline_manifest=baseline_manifest,
    )
    unsafe = _unsafe_operations(plan)
    if unsafe:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "refused",
            "reason": "Unsafe overwrite or manual-review operation present.",
            "plan": plan,
            "unsafe_operations": list(unsafe),
        }

    installed_at = _installed_at_for_plan(target_root)
    assets = _assets_for_target(target_root, _managed_assets(source, primary_agent, enabled_agents))
    ordered_assets = _ordered_install_assets(assets)
    manifest = _manifest_payload(
        source,
        target_root,
        primary_agent,
        enabled_agents,
        installed_at=installed_at,
        assets=assets,
    )
    manifest_asset = Asset(AEGIS_MANIFEST_REL, _dump_json(manifest).encode("utf-8"))
    created_plan_paths = [
        str(operation["path"])
        for operation in plan.get("operations", [])
        if operation.get("classification") == "create" and isinstance(operation.get("path"), str)
    ]
    runtime_report_paths = [
        rel_path
        for rel_path in (
            AEGIS_PLAN_REPORT_REL,
            AEGIS_INSTALL_REPORT_REL,
            AEGIS_CLIENT_RELOAD_REL,
        )
        if not (target_root / rel_path).exists()
    ]
    snapshots = _snapshot_existing_paths(
        target_root,
        [
            *(asset.path for asset in ordered_assets),
            manifest_asset.path,
            AEGIS_PLAN_REPORT_REL,
            AEGIS_INSTALL_REPORT_REL,
            AEGIS_CLIENT_RELOAD_REL,
        ],
    )
    try:
        for asset in [*ordered_assets, manifest_asset]:
            target = target_root / asset.path
            if target.exists() and target.is_file() and target.read_bytes() == asset.content:
                continue
            if asset.kind == "config" and target.exists():
                # Seed-once: per-repo configuration is owner-maintained after creation.
                continue
            _write_asset(target_root, asset)

        reports_dir = target_root / AEGIS_REPORTS_REL
        reports_dir.mkdir(parents=True, exist_ok=True)
        plan_report_path = target_root / AEGIS_PLAN_REPORT_REL
        _atomic_write_bytes(
            plan_report_path,
            _dump_json(plan).encode("utf-8"),
            mode=(plan_report_path.stat().st_mode & 0o7777) if plan_report_path.exists() else 0o644,
        )
        client_reload = _client_reload_report(target_root, plan, enabled_agents)
        if client_reload.get("required") and not client_reload.get("pending_marker"):
            _write_client_reload_marker(target_root, client_reload)
            client_reload = _client_reload_report(target_root, plan, enabled_agents)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "applied",
            "applied_at": _iso_now(),
            "target_root": str(target_root),
            "plan": plan,
            "manifest_path": AEGIS_MANIFEST_REL,
            "client_reload": client_reload,
            "hygiene": gitignore_hygiene_report(target_root),
        }
        install_report_path = target_root / AEGIS_INSTALL_REPORT_REL
        _atomic_write_bytes(
            install_report_path,
            _dump_json(report).encode("utf-8"),
            mode=(
                (install_report_path.stat().st_mode & 0o7777)
                if install_report_path.exists()
                else 0o644
            ),
        )
        return report
    except Exception as exc:
        rollback = _restore_existing_paths(target_root, snapshots)
        cleanup = _cleanup_created_paths(target_root, [*created_plan_paths, *runtime_report_paths])
        if cleanup["status"] != "completed":
            rollback["status"] = "partial"
        rollback["cleanup"] = cleanup
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "failed",
            "reason": str(exc),
            "failed_at": _iso_now(),
            "target_root": str(target_root),
            "plan": plan,
            "cleanup": cleanup,
            "rollback": rollback,
        }


def initialize_project(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    profile: str = PROFILE_GENERIC,
    primary_agent: str = "claude",
    agents: Sequence[str] | None = None,
    verify_after_install: bool = True,
) -> dict[str, Any]:
    """Install Aegis into a project using public task-master-init style defaults."""

    target_root = _resolve_target_root(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    selected_agents = list(agents or [primary_agent])
    enabled_agents = _enabled_agents(primary_agent, selected_agents)
    inspect_before = inspect_project(
        target_root,
        profile=profile,
        source_root=source_root,
        default_primary_agent=primary_agent,
        default_agents=enabled_agents,
    )
    plan = plan_install(
        target_root,
        source_root=source_root,
        profile=profile,
        primary_agent=primary_agent,
        agents=enabled_agents,
        mode="apply",
        apply_confirmed=True,
    )
    install_report = install(
        target_root,
        source_root=source_root,
        profile=profile,
        primary_agent=primary_agent,
        agents=enabled_agents,
        apply=True,
    )
    verification: dict[str, Any] | None = None
    status_value = str(install_report.get("status") or "unknown")
    if status_value == "applied" and verify_after_install:
        verification = verify(
            target_root,
            source_root=source_root,
            default_primary_agent=primary_agent,
            default_agents=enabled_agents,
        )
        if verification.get("status") == "failed":
            status_value = "failed"

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "initialized" if status_value == "applied" else status_value,
        "initialized_at": _iso_now(),
        "target_root": str(target_root),
        "profile": profile,
        "agent_selection": {
            "source": "public_defaults",
            "primary_agent": primary_agent,
            "enabled_agents": list(enabled_agents),
        },
        "public_commands": {
            "status": "aegis status",
            "next": "aegis next",
            "start": 'aegis start "<task title>"',
            "verify": "aegis verify --strict",
            "closeout": "aegis closeout --update-handoff",
        },
        "inspect_before": inspect_before,
        "plan": plan,
        "install": install_report,
        "verification": verification,
        "reports": {
            "plan_json": AEGIS_PLAN_REPORT_REL,
            "install_json": AEGIS_INSTALL_REPORT_REL,
            "verification_json": AEGIS_VERIFY_REPORT_REL if verification is not None else None,
        },
        "next_action": _post_init_next_action(install_report),
    }
    return payload


def _check_settings_hook(target_root: Path, gate: Mapping[str, Any]) -> tuple[bool, str]:
    settings_path = target_root / str(gate.get("settings_path") or "")
    if not settings_path.exists():
        return False, f"settings file missing: {_repo_path(settings_path, target_root)}"
    settings = _read_json(settings_path)
    if not settings:
        return False, f"settings file is not valid JSON: {_repo_path(settings_path, target_root)}"
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False, "settings hooks object missing"
    event = str(gate.get("hook_event") or "")
    matcher = str(gate.get("hook_matcher") or "")
    expected = str(gate.get("verification", {}).get("expected") or "")
    entries = hooks.get(event)
    if not isinstance(entries, list):
        return False, f"settings hook event missing: {event}"
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if matcher and entry.get("matcher") != matcher:
            continue
        hook_items = entry.get("hooks")
        if not isinstance(hook_items, list):
            continue
        for hook in hook_items:
            if isinstance(hook, dict) and hook.get("command") == expected:
                return True, "hook registered"
    label = f"{event} / {matcher}" if matcher else event
    return False, f"hook registration missing for {label}"


def _verify_gate(target_root: Path, gate: Mapping[str, Any]) -> dict[str, Any]:
    verification = gate.get("verification") if isinstance(gate.get("verification"), Mapping) else {}
    method = verification.get("method")
    gate_id = str(gate.get("id"))
    path_value = gate.get("path")
    result: dict[str, Any] = {
        "gate_id": gate_id,
        "required": bool(gate.get("required")),
        "enforcement": gate.get("enforcement"),
        "method": method,
        "status": "pass",
        "message": "ok",
    }
    if method == "manual":
        result["status"] = "unsupported" if gate.get("enforcement") == "policy" else "warn"
        result["message"] = str(gate.get("unsupported_reason") or "manual verification required")
        return result
    if method in {"exists", "executable"}:
        target = target_root / str(path_value or "")
        if not target.exists():
            result["status"] = "fail"
            result["message"] = f"path missing: {_repo_path(target, target_root)}"
        elif method == "executable" and not os.access(target, os.X_OK):
            result["status"] = "fail"
            result["message"] = f"path not executable: {_repo_path(target, target_root)}"
        return result
    if method == "settings_hook":
        ok, message = _check_settings_hook(target_root, gate)
        result["status"] = "pass" if ok else "fail"
        result["message"] = message
        return result
    if method == "command":
        command = str(gate.get("command") or "")
        result["status"] = "warn"
        result["message"] = f"command gate not executed by V1 verifier: {command}"
        return result
    result["status"] = "warn"
    result["message"] = f"unsupported verification method: {method}"
    return result


def _strict_check(
    check_id: str,
    *,
    category: str,
    required: bool,
    passed: bool,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "gate_id": check_id,
        "id": check_id,
        "category": category,
        "required": required,
        "enforcement": "strict",
        "method": "strict",
        "status": "pass" if passed else "fail",
        "message": message,
    }
    if details is not None:
        result["details"] = dict(details)
    return result


def _strict_path_check(
    target_root: Path,
    check_id: str,
    *,
    category: str,
    rel_path: str,
    required: bool = True,
    directory: bool = False,
    executable: bool = False,
) -> dict[str, Any]:
    target = target_root / rel_path
    exists = target.exists()
    kind_ok = target.is_dir() if directory else target.is_file()
    executable_ok = not executable or os.access(target, os.X_OK)
    passed = exists and kind_ok and executable_ok
    if not exists:
        message = f"path missing: {rel_path}"
    elif not kind_ok:
        expected = "directory" if directory else "file"
        message = f"path is not a {expected}: {rel_path}"
    elif not executable_ok:
        message = f"path not executable: {rel_path}"
    else:
        message = "ok"
    return _strict_check(
        check_id,
        category=category,
        required=required,
        passed=passed,
        message=message,
        details={
            "path": rel_path,
            "directory": directory,
            "executable": executable,
        },
    )


def _agent_enabled(manifest: Mapping[str, Any], agent: str) -> bool:
    agents = manifest.get("agents")
    if not isinstance(agents, Mapping):
        return False
    agent_payload = agents.get(agent)
    return isinstance(agent_payload, Mapping) and agent_payload.get("enabled") is True


def _strict_managed_files_check(target_root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    managed_files = manifest.get("managed_files")
    if not isinstance(managed_files, list):
        return _strict_check(
            "manifest.managed_files",
            category="manifest",
            required=True,
            passed=False,
            message="managed_files is missing or not a list",
        )
    missing: list[str] = []
    directories: list[str] = []
    checked: list[str] = []
    for item in managed_files:
        if not isinstance(item, Mapping):
            continue
        rel_path = str(item.get("path") or "").strip()
        if not rel_path:
            continue
        checked.append(rel_path)
        target = target_root / rel_path
        if not target.exists():
            missing.append(rel_path)
        elif target.is_dir():
            directories.append(rel_path)
    passed = not missing and not directories
    message = (
        "all manifest managed files exist"
        if passed
        else "manifest managed files missing or invalid"
    )
    return _strict_check(
        "manifest.managed_files",
        category="manifest",
        required=True,
        passed=passed,
        message=message,
        details={
            "checked": len(checked),
            "missing": missing,
            "directories": directories,
        },
    )


def _strict_workflow_template_check(target_root: Path) -> dict[str, Any]:
    missing = [
        template_name
        for template_name in AEGIS_WORKFLOW_TEMPLATE_NAMES
        if not (target_root / AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT / template_name).is_file()
    ]
    return _strict_check(
        "runtime.workflow_templates",
        category="runtime",
        required=True,
        passed=not missing,
        message="all workflow templates installed" if not missing else "workflow templates missing",
        details={
            "template_root": AEGIS_WORKFLOW_TEMPLATE_TARGET_ROOT,
            "missing": missing,
        },
    )


def _strict_current_work_checks(
    target_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    current_work_path = target_root / AEGIS_CURRENT_WORK_REL
    current_work = _read_json(current_work_path)
    if current_work is None:
        return [
            _strict_check(
                "workflow.current_work",
                category="workflow",
                required=True,
                passed=False,
                message=f"{AEGIS_CURRENT_WORK_REL} missing or invalid JSON",
            )
        ], None

    task = current_work.get("task") if isinstance(current_work.get("task"), Mapping) else {}
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    task_id = str(task.get("id") or "").strip()
    task_slug = str(task.get("slug") or "").strip()
    work_mode = str(current_work.get("mode") or "task").strip() or "task"
    missing_path_keys = [
        key
        for key in (
            "session",
            "session_current",
            "plan",
            "plan_current",
            "work_tracking",
            "reports",
            "workflow_templates",
        )
        if not str(paths.get(key) or "").strip()
    ]
    work_status = str(current_work.get("status") or "").strip()
    active_payload = work_status == "in-progress"
    completed_payload = work_status == "completed" and (
        bool(current_work.get("closeout_passed_at")) or work_mode == "observation"
    )
    valid_payload = (
        (active_payload or completed_payload)
        and bool(task_id)
        and bool(task_slug)
        and not missing_path_keys
    )
    status_message = (
        "current work payload is active and complete"
        if active_payload
        else (
            "current work payload is completed and closeout-passed"
            if completed_payload
            else "current work payload is incomplete"
        )
    )
    checks = [
        _strict_check(
            "workflow.current_work",
            category="workflow",
            required=True,
            passed=valid_payload,
            message=status_message,
            details={
                "task": task,
                "mode": work_mode,
                "status": work_status,
                "missing_path_keys": missing_path_keys,
            },
        )
    ]

    if task_id and work_mode == "observation":
        try:
            branch = _current_branch(target_root)
            checks.append(
                _strict_check(
                    "workflow.branch_task_alignment",
                    category="workflow",
                    required=True,
                    passed=True,
                    message="observation mode does not require a task-id branch",
                    details={
                        "branch": branch,
                        "current_work_task_id": task_id,
                        "mode": work_mode,
                    },
                )
            )
        except AegisError as exc:
            checks.append(
                _strict_check(
                    "workflow.branch_task_alignment",
                    category="workflow",
                    required=True,
                    passed=False,
                    message=str(exc),
                    details={"mode": work_mode},
                )
            )
    elif task_id and work_mode == "bead":
        try:
            branch = _current_branch(target_root)
            branch_bead = _branch_bead_id(branch, expected_id=task_id)
            branch_matches = branch_bead == task_id
            checks.append(
                _strict_check(
                    "workflow.branch_task_alignment",
                    category="workflow",
                    required=True,
                    passed=branch_matches,
                    message=(
                        "branch bead id matches current work"
                        if branch_matches
                        else "branch bead id does not match current work"
                    ),
                    details={
                        "branch": branch,
                        "branch_bead_id": branch_bead,
                        "current_work_bead_id": task_id,
                        "mode": work_mode,
                    },
                )
            )
        except AegisError as exc:
            checks.append(
                _strict_check(
                    "workflow.branch_task_alignment",
                    category="workflow",
                    required=True,
                    passed=False,
                    message=str(exc),
                    details={"mode": work_mode},
                )
            )
    elif task_id:
        try:
            branch = _current_branch(target_root)
            branch_task = _branch_task_id(branch)
            branch_matches = branch_task == task_id
            checks.append(
                _strict_check(
                    "workflow.branch_task_alignment",
                    category="workflow",
                    required=True,
                    passed=branch_matches,
                    message=(
                        "branch task id matches current work"
                        if branch_matches
                        else "branch task id does not match current work"
                    ),
                    details={
                        "branch": branch,
                        "branch_task_id": branch_task,
                        "current_work_task_id": task_id,
                    },
                )
            )
        except AegisError as exc:
            checks.append(
                _strict_check(
                    "workflow.branch_task_alignment",
                    category="workflow",
                    required=True,
                    passed=False,
                    message=str(exc),
                )
            )

    for key, check_id, directory in (
        ("session", "workflow.session_file", False),
        ("session_current", "workflow.session_current", False),
        ("plan", "workflow.plan_file", False),
        ("plan_current", "workflow.plan_current", False),
        ("work_tracking", "workflow.work_tracking", True),
        ("reports", "workflow.reports", True),
        ("workflow_templates", "workflow.workflow_templates_path", True),
    ):
        rel_path = str(paths.get(key) or "").strip()
        if rel_path:
            checks.append(
                _strict_path_check(
                    target_root,
                    check_id,
                    category="workflow",
                    rel_path=rel_path,
                    directory=directory,
                )
            )

    plan_rel = str(paths.get("plan") or "").strip()
    if plan_rel and (target_root / plan_rel).is_file():
        plan_rows = _parse_plan_rows(target_root / plan_rel)
        expected_rows = _canonical_plan_step_rows(current_work)
        missing_steps = [step for step in expected_rows if step not in plan_rows]
        malformed_steps = [
            step
            for step, row in plan_rows.items()
            if str(step).startswith("plan-step-")
            and isinstance(row, Mapping)
            and row.get("malformed")
        ]
        checks.append(
            _strict_check(
                "workflow.plan_table",
                category="workflow",
                required=True,
                passed=not missing_steps and not malformed_steps,
                message=(
                    "active plan table is parseable"
                    if not missing_steps and not malformed_steps
                    else "active plan table has malformed or missing rows"
                ),
                details={
                    "path": plan_rel,
                    "missing_steps": missing_steps,
                    "malformed_steps": malformed_steps,
                },
            )
        )

    work_rel = str(paths.get("work_tracking") or "").strip()
    if work_rel:
        missing_surfaces = [
            name
            for name in (
                "TRACKER.md",
                "FINDINGS.md",
                "DECISIONS.md",
                "IMPLEMENTATION.md",
                "CHANGELOG.md",
                "HANDOFF.md",
            )
            if not (target_root / work_rel / name).is_file()
        ]
        checks.append(
            _strict_check(
                "workflow.tracking_surfaces",
                category="workflow",
                required=True,
                passed=not missing_surfaces,
                message=(
                    "all work-tracking surfaces exist"
                    if not missing_surfaces
                    else "work-tracking surfaces missing"
                ),
                details={
                    "work_tracking": work_rel,
                    "missing": missing_surfaces,
                },
            )
        )
    return checks, current_work


def _strict_pending_tracking_check(
    target_root: Path,
    pending_tracking: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = (
        dict(pending_tracking)
        if isinstance(pending_tracking, Mapping)
        else _classify_pending_tracking(target_root)
    )
    return _strict_check(
        "mutation.pending_tracking_empty",
        category="mutation",
        required=True,
        passed=bool(state.get("delivery_allowed")),
        message=str(state.get("reason") or "pending tracking state unavailable"),
        details=state,
    )


def _strict_claude_checks(target_root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    required = _agent_enabled(manifest, "claude")
    if not required:
        return [
            _strict_check(
                "claude.adapter_enabled",
                category="claude",
                required=False,
                passed=True,
                message="Claude adapter is not enabled for this install",
            )
        ]

    missing_required_files = [
        rel_path for rel_path in CLAUDE_REQUIRED_FILES if not (target_root / rel_path).is_file()
    ]
    checks = [
        _strict_check(
            "claude.required_files",
            category="claude",
            required=True,
            passed=not missing_required_files,
            message=(
                "all Claude required files exist"
                if not missing_required_files
                else "Claude required files missing"
            ),
            details={"missing": missing_required_files},
        )
    ]

    hook_gate_ids = {
        "claude.pretooluse",
        "claude.posttooluse_tracking",
        "claude.stop_tracking",
    }
    hook_results = [
        _verify_gate(target_root, gate)
        for gate in manifest.get("gates", [])
        if isinstance(gate, Mapping) and gate.get("id") in hook_gate_ids
    ]
    failed_hooks = [
        str(result.get("gate_id")) for result in hook_results if result.get("status") != "pass"
    ]
    checks.append(
        _strict_check(
            "claude.hooks_registered",
            category="claude",
            required=True,
            passed=len(hook_results) == len(hook_gate_ids) and not failed_hooks,
            message=(
                "Claude hook registrations are present"
                if not failed_hooks and len(hook_results) == len(hook_gate_ids)
                else "Claude hook registrations are missing or invalid"
            ),
            details={
                "expected": sorted(hook_gate_ids),
                "observed": [str(result.get("gate_id")) for result in hook_results],
                "failed": failed_hooks,
            },
        )
    )
    checks.append(
        _strict_check(
            "protection.codex_owned_paths",
            category="protection",
            required=True,
            passed=(target_root / ".claude/scripts/codex-path-guard.sh").is_file()
            and os.access(target_root / ".claude/scripts/codex-path-guard.sh", os.X_OK)
            and (target_root / ".claude/scripts/bash-command-guard.sh").is_file()
            and os.access(target_root / ".claude/scripts/bash-command-guard.sh", os.X_OK),
            message="Codex-owned path guard scripts are installed and executable",
            details={
                "file_tool_guard": ".claude/scripts/codex-path-guard.sh",
                "bash_guard": ".claude/scripts/bash-command-guard.sh",
            },
        )
    )
    return checks


def _tracked_codex_hook_trust_guidance(manifest: Mapping[str, Any]) -> dict[str, Any]:
    gates = manifest.get("gates")
    if not isinstance(gates, list):
        return {}
    matching = [
        gate for gate in gates if isinstance(gate, Mapping) and gate.get("id") == "codex.hook_trust"
    ]
    if len(matching) != 1:
        return {}
    gate = matching[0]
    verification = gate.get("verification")
    if not isinstance(verification, Mapping):
        return {}
    if not (
        gate.get("required") is False
        and gate.get("enforcement") == "policy"
        and gate.get("scope") == "adapter"
        and gate.get("adapter") == "codex"
        and gate.get("path") == CODEX_HOOKS_REL
        and gate.get("settings_path") == CODEX_HOOKS_REL
        and gate.get("unsupported_reason") == CODEX_HOOK_TRUST_UNSUPPORTED_REASON
        and gate.get("review_command") == CODEX_HOOK_TRUST_REVIEW_COMMAND
        and gate.get("hash_scope") == CODEX_HOOK_TRUST_HASH_SCOPE
        and gate.get("bypass_allowed") is False
        and verification.get("method") == "manual"
        and verification.get("failure_mode") == "unsupported"
        and verification.get("expected") is None
    ):
        return {}
    return {
        "settings_path": gate.get("settings_path"),
        "review_command": gate.get("review_command"),
        "hash_scope": gate.get("hash_scope"),
        "bypass_allowed": gate.get("bypass_allowed"),
        "source": "manifest_gate",
    }


def _supplemental_codex_hook_trust_evidence(target_root: Path) -> dict[str, Any]:
    """Describe generated install guidance without treating it as trust authority."""

    report_path = target_root / AEGIS_INSTALL_REPORT_REL
    install_report = _read_json(report_path)
    reload_report = (
        install_report.get("client_reload")
        if isinstance(install_report, Mapping)
        and isinstance(install_report.get("client_reload"), Mapping)
        else {}
    )
    hook_trust = (
        reload_report.get("hook_trust")
        if isinstance(reload_report, Mapping)
        and isinstance(reload_report.get("hook_trust"), Mapping)
        else {}
    )
    matches_contract = bool(hook_trust) and (
        hook_trust.get("settings_path") == CODEX_HOOKS_REL
        and hook_trust.get("review_command") == CODEX_HOOK_TRUST_REVIEW_COMMAND
        and hook_trust.get("hash_scope") == CODEX_HOOK_TRUST_HASH_SCOPE
        and hook_trust.get("bypass_allowed") is False
    )
    return {
        "install_report_present": report_path.is_file(),
        "install_report_parsed": isinstance(install_report, Mapping),
        "hook_trust_guidance_present": bool(hook_trust),
        "matches_tracked_contract": matches_contract,
        "client_trust_asserted": False,
    }


def _strict_codex_checks(target_root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    required = _agent_enabled(manifest, "codex")
    if not required:
        return [
            _strict_check(
                "codex.adapter_enabled",
                category="codex",
                required=False,
                passed=True,
                message="Codex adapter is not enabled for this install",
            )
        ]

    missing_required_files = [
        rel_path for rel_path in CODEX_REQUIRED_FILES if not (target_root / rel_path).is_file()
    ]
    checks = [
        _strict_check(
            "codex.required_files",
            category="codex",
            required=True,
            passed=not missing_required_files,
            message=(
                "all Codex required files exist"
                if not missing_required_files
                else "Codex required files missing"
            ),
            details={"missing": missing_required_files},
        )
    ]

    hook_gate_ids = {
        "codex.pretooluse",
        "codex.posttooluse_tracking",
        "codex.posttooluse_ledger",
        "codex.session_brief",
        "codex.stop_tracking",
        "codex.apply_patch",
    }
    hook_results = [
        _verify_gate(target_root, gate)
        for gate in manifest.get("gates", [])
        if isinstance(gate, Mapping) and gate.get("id") in hook_gate_ids
    ]
    failed_hooks = [
        str(result.get("gate_id")) for result in hook_results if result.get("status") != "pass"
    ]
    checks.append(
        _strict_check(
            "codex.hooks_registered",
            category="codex",
            required=True,
            passed=len(hook_results) == len(hook_gate_ids) and not failed_hooks,
            message=(
                "Codex hook registrations are present"
                if not failed_hooks and len(hook_results) == len(hook_gate_ids)
                else "Codex hook registrations are missing or invalid"
            ),
            details={
                "expected": sorted(hook_gate_ids),
                "observed": [str(result.get("gate_id")) for result in hook_results],
                "failed": failed_hooks,
            },
        )
    )

    hook_trust = _tracked_codex_hook_trust_guidance(manifest)
    supplemental_hook_trust = _supplemental_codex_hook_trust_evidence(target_root)
    trust_guidance_ok = (
        hook_trust.get("settings_path") == CODEX_HOOKS_REL
        and hook_trust.get("review_command") == CODEX_HOOK_TRUST_REVIEW_COMMAND
        and hook_trust.get("hash_scope") == CODEX_HOOK_TRUST_HASH_SCOPE
        and hook_trust.get("bypass_allowed") is False
    )
    checks.append(
        _strict_check(
            "codex.hook_trust_guidance",
            category="codex",
            required=True,
            passed=trust_guidance_ok,
            message=(
                "Codex exact-hash hook trust guidance is present"
                if trust_guidance_ok
                else "Codex hook trust guidance is missing or permits bypass"
            ),
            details={
                "settings_path": hook_trust.get("settings_path"),
                "review_command": hook_trust.get("review_command"),
                "hash_scope": hook_trust.get("hash_scope"),
                "bypass_allowed": hook_trust.get("bypass_allowed"),
                "source": hook_trust.get("source"),
                "client_trust_asserted": False,
                "supplemental_install_evidence": supplemental_hook_trust,
            },
        )
    )
    return checks


def _strict_integration_checks(
    target_root: Path, current_work: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    integrations = (
        current_work.get("integrations")
        if isinstance(current_work, Mapping)
        and isinstance(current_work.get("integrations"), Mapping)
        else {}
    )
    checks: list[dict[str, Any]] = []
    for name, rel_path in (("taskmaster", ".taskmaster"), ("serena", ".serena")):
        integration = integrations.get(name) if isinstance(integrations, Mapping) else {}
        required = isinstance(integration, Mapping) and integration.get("required") is True
        detected = (target_root / rel_path).exists()
        checks.append(
            _strict_check(
                f"integrations.{name}_optional",
                category="integrations",
                required=required,
                passed=(detected or not required),
                message=(
                    f"{name} integration present"
                    if detected
                    else (
                        f"{name} integration is optional and absent"
                        if not required
                        else f"{name} integration is required but absent"
                    )
                ),
                details={
                    "path": rel_path,
                    "required": required,
                    "detected": detected,
                },
            )
        )
    return checks


def _strict_verification_checks(
    target_root: Path,
    manifest: Mapping[str, Any],
    *,
    pending_tracking: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        _strict_managed_files_check(target_root, manifest),
        _strict_path_check(
            target_root,
            "runtime.local_cli_shim",
            category="runtime",
            rel_path=AEGIS_LOCAL_BIN_REL,
            executable=True,
        ),
        _strict_workflow_template_check(target_root),
    ]
    workflow_checks, current_work = _strict_current_work_checks(target_root)
    checks.extend(workflow_checks)
    checks.append(_strict_pending_tracking_check(target_root, pending_tracking))
    checks.extend(_strict_claude_checks(target_root, manifest))
    checks.extend(_strict_codex_checks(target_root, manifest))
    checks.extend(_strict_integration_checks(target_root, current_work))
    return checks


def _manifest_primary_agent(manifest: Mapping[str, Any]) -> str:
    primary = str(manifest.get("primary_agent") or "claude")
    return primary if primary in PRIMARY_AGENT_CHOICES else "claude"


def _manifest_enabled_agents(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    agents = manifest.get("agents")
    if not isinstance(agents, Mapping):
        return ("claude",)
    enabled = [
        name
        for name, payload in agents.items()
        if name in AGENT_CHOICES and isinstance(payload, Mapping) and payload.get("enabled") is True
    ]
    return tuple(enabled or ("claude",))


def _doctor_summary(checks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(checks)
    failed_required = sum(
        1 for check in checks if check.get("required") is True and check.get("status") == "fail"
    )
    warnings = sum(
        1 for check in checks if check.get("required") is False and check.get("status") == "fail"
    )
    return {
        "total": total,
        "failed_required": failed_required,
        "warnings": warnings,
    }


def _doctor_action(
    action_id: str,
    *,
    kind: str,
    path: str,
    reason: str,
    safe: bool = True,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "id": action_id,
        "kind": kind,
        "path": path,
        "reason": reason,
        "safe": safe,
    }
    if details:
        action["details"] = dict(details)
    return action


def _doctor_manifest_assets(
    target_root: Path,
    source_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Asset]:
    primary_agent = _manifest_primary_agent(manifest)
    enabled_agents = _manifest_enabled_agents(manifest)
    assets = _assets_for_target(
        target_root,
        _managed_assets(source_root, primary_agent, enabled_agents),
    )
    return {asset.path: asset for asset in assets}


def _current_work_pointer_actions(
    target_root: Path,
    current_work: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(current_work, Mapping):
        return []
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    actions: list[dict[str, Any]] = []
    for key, target_key in (("session_current", "session"), ("plan_current", "plan")):
        link_rel = str(paths.get(key) or "").strip()
        target_rel = str(paths.get(target_key) or "").strip()
        if not link_rel or not target_rel:
            continue
        link = target_root / link_rel
        target = target_root / target_rel
        if not target.is_file():
            continue
        desired = os.path.relpath(target, start=link.parent)
        needs_repair = False
        if not link.exists() and not link.is_symlink():
            needs_repair = True
        elif link.is_symlink():
            try:
                needs_repair = os.readlink(link) != desired
            except OSError:
                needs_repair = True
        else:
            needs_repair = True
        if needs_repair:
            actions.append(
                _doctor_action(
                    f"workflow.recreate_{key}",
                    kind="recreate_symlink",
                    path=link_rel,
                    reason=f"{link_rel} should point at {target_rel}",
                    details={"target": target_rel, "link_target": desired},
                )
            )
    reports_rel = str(paths.get("reports") or "").strip()
    if reports_rel and not (target_root / reports_rel).is_dir():
        actions.append(
            _doctor_action(
                "workflow.ensure_reports_dir",
                kind="ensure_directory",
                path=reports_rel,
                reason="active reports directory is missing",
            )
        )
    return actions


def _completed_closeout_action(
    target_root: Path,
    current_work: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(current_work, Mapping):
        return None
    status_value = str(current_work.get("status") or "")
    if status_value == "completed" and current_work.get("closeout_passed_at"):
        return None
    closeout_report = _read_json(target_root / AEGIS_CLOSEOUT_REPORT_REL)
    if not isinstance(closeout_report, Mapping) or closeout_report.get("status") != "passed":
        return None
    if not _closeout_report_matches_current_work(closeout_report, current_work):
        return None
    return _doctor_action(
        "workflow.normalize_completed_closeout",
        kind="normalize_completed_closeout",
        path=AEGIS_CURRENT_WORK_REL,
        reason="closeout report passed but current-work is not marked completed",
        details={"closeout_report": AEGIS_CLOSEOUT_REPORT_REL},
    )


def _current_work_task_id(current_work: Mapping[str, Any] | None) -> str:
    if not isinstance(current_work, Mapping):
        return ""
    task = current_work.get("task") if isinstance(current_work.get("task"), Mapping) else {}
    return str(task.get("id") or "").strip()


def _current_work_tracking_rel(current_work: Mapping[str, Any] | None) -> str:
    if not isinstance(current_work, Mapping):
        return ""
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    return str(paths.get("work_tracking") or "").strip()


def _closeout_report_current_work(closeout_report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(closeout_report, Mapping):
        return {}
    current = closeout_report.get("current_work")
    return current if isinstance(current, Mapping) else {}


def _closeout_report_matches_current_work(
    closeout_report: Mapping[str, Any] | None,
    current_work: Mapping[str, Any] | None,
) -> bool:
    report_work = _closeout_report_current_work(closeout_report)
    return (
        bool(report_work)
        and bool(_current_work_task_id(current_work))
        and _current_work_task_id(report_work) == _current_work_task_id(current_work)
        and _current_work_tracking_rel(report_work) == _current_work_tracking_rel(current_work)
    )


def _completed_task_work_tracking_action(
    target_root: Path,
    current_work: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    closeout_report = _read_json(target_root / AEGIS_CLOSEOUT_REPORT_REL)
    if not isinstance(closeout_report, Mapping) or closeout_report.get("status") != "passed":
        return None
    report_work = _closeout_report_current_work(closeout_report)
    work_rel = _current_work_tracking_rel(report_work)
    if not work_rel:
        return None
    is_current_completed_task = (
        isinstance(current_work, Mapping)
        and str(current_work.get("mode") or "") != "observation"
        and str(current_work.get("status") or "") == "completed"
        and _current_work_task_id(current_work) == _current_work_task_id(report_work)
    )
    if work_rel == _current_work_tracking_rel(current_work) and not is_current_completed_task:
        return None
    if not _is_task_active_work_tracking_rel(work_rel):
        return None
    if not (target_root / work_rel).is_dir():
        return None
    return _doctor_action(
        "workflow.archive_completed_task_work_tracking",
        kind="archive_completed_task_work_tracking",
        path=work_rel,
        reason="completed task work-tracking folder is still marked ACTIVE",
        details={
            "archive_path": _completed_work_tracking_archive_rel(work_rel),
            "closeout_report": AEGIS_CLOSEOUT_REPORT_REL,
            "task_id": _current_work_task_id(report_work),
        },
    )


def _mismatched_closeout_metadata_action(
    target_root: Path,
    current_work: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(current_work, Mapping):
        return None
    if not (current_work.get("closeout_passed_at") or current_work.get("closeout_report")):
        return None
    closeout_report = _read_json(target_root / AEGIS_CLOSEOUT_REPORT_REL)
    if not isinstance(closeout_report, Mapping) or closeout_report.get("status") != "passed":
        return None
    report_work = _closeout_report_current_work(closeout_report)
    if not report_work:
        return None
    current_id = _current_work_task_id(current_work)
    report_id = _current_work_task_id(report_work)
    if (
        not current_id
        or not report_id
        or _closeout_report_matches_current_work(closeout_report, current_work)
    ):
        return None
    return _doctor_action(
        "workflow.remove_mismatched_closeout_metadata",
        kind="remove_mismatched_closeout_metadata",
        path=AEGIS_CURRENT_WORK_REL,
        reason="current-work contains closeout metadata from a different task envelope",
        details={
            "current_task_id": current_id,
            "closeout_task_id": report_id,
            "current_work_tracking": _current_work_tracking_rel(current_work),
            "closeout_work_tracking": _current_work_tracking_rel(report_work),
            "closeout_report": AEGIS_CLOSEOUT_REPORT_REL,
        },
    )


def _completed_observation_work_tracking_action(
    target_root: Path,
    current_work: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    current_work_rel = ""
    if isinstance(current_work, Mapping):
        current_paths = (
            current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
        )
        current_work_rel = str(current_paths.get("work_tracking") or "").strip()

    candidate_rels: list[str] = []
    if (
        isinstance(current_work, Mapping)
        and str(current_work.get("mode") or "") == "observation"
        and str(current_work.get("status") or "") == "completed"
    ):
        paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
        candidate_rels.append(str(paths.get("work_tracking") or "").strip())
    report = _read_json(target_root / AEGIS_OBSERVATION_REPORT_REL)
    if (
        isinstance(report, Mapping)
        and str(report.get("mode") or "") == "observation"
        and str(report.get("status") or "") == "completed"
    ):
        paths = report.get("paths") if isinstance(report.get("paths"), Mapping) else {}
        candidate_rels.append(str(paths.get("work_tracking") or "").strip())

    active_root = target_root / "docs" / "ai" / "work-tracking" / "active"
    if active_root.is_dir():
        for path in sorted(active_root.glob("*-observe-*-ACTIVE")):
            if path.is_dir():
                candidate_rels.append(path.relative_to(target_root).as_posix())

    seen: set[str] = set()
    for work_rel in candidate_rels:
        if work_rel in seen:
            continue
        seen.add(work_rel)
        if work_rel == current_work_rel and not (
            isinstance(current_work, Mapping)
            and str(current_work.get("mode") or "") == "observation"
            and str(current_work.get("status") or "") == "completed"
        ):
            continue
        archive_rel = _completed_observation_work_tracking_archive_rel(work_rel)
        if not archive_rel:
            continue
        if not _is_observation_active_work_tracking_rel(work_rel):
            continue
        if not (target_root / work_rel).is_dir():
            continue
        return _doctor_action(
            "workflow.archive_completed_observation_work_tracking",
            kind="archive_completed_observation_work_tracking",
            path=work_rel,
            reason="completed observation work-tracking folder is still marked ACTIVE",
            details={
                "archive_path": archive_rel,
                "observation_report": AEGIS_OBSERVATION_REPORT_REL,
            },
        )
    return None


def _doctor_repair_actions(
    target_root: Path,
    source_root: Path,
    manifest: Mapping[str, Any] | None,
    current_work: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if isinstance(manifest, Mapping):
        asset_map = _doctor_manifest_assets(target_root, source_root, manifest)
        managed_files = manifest.get("managed_files")
        if isinstance(managed_files, list):
            for item in managed_files:
                if not isinstance(item, Mapping):
                    continue
                rel_path = str(item.get("path") or "").strip()
                if not rel_path:
                    continue
                target = target_root / rel_path
                asset = asset_map.get(rel_path)
                if not target.exists() and asset is not None:
                    actions.append(
                        _doctor_action(
                            f"managed.restore:{rel_path}",
                            kind="restore_managed_file",
                            path=rel_path,
                            reason="manifest-managed file is missing",
                            details={"executable": asset.executable, "managed_kind": asset.kind},
                        )
                    )
                elif target.is_dir():
                    actions.append(
                        _doctor_action(
                            f"managed.manual:{rel_path}",
                            kind="manual_review",
                            path=rel_path,
                            reason="manifest-managed path is a directory, not a file",
                            safe=False,
                        )
                    )
        shim = target_root / AEGIS_LOCAL_BIN_REL
        if shim.is_file() and not os.access(shim, os.X_OK):
            actions.append(
                _doctor_action(
                    "runtime.chmod_local_cli_shim",
                    kind="chmod_executable",
                    path=AEGIS_LOCAL_BIN_REL,
                    reason="project-local Aegis CLI shim is not executable",
                )
            )
    actions.extend(_current_work_pointer_actions(target_root, current_work))
    plan_table_repair = _plan_table_repair_preview(target_root, current_work)
    if plan_table_repair is not None:
        actions.append(
            _doctor_action(
                "workflow.normalize_plan_table",
                kind="normalize_plan_table",
                path=str(plan_table_repair["path"]),
                reason="active plan table has malformed or unsafe markdown rows",
                details={"steps": plan_table_repair["steps"]},
            )
        )
    mismatched_closeout_action = _mismatched_closeout_metadata_action(target_root, current_work)
    if mismatched_closeout_action is not None:
        actions.append(mismatched_closeout_action)
    completed_task_action = _completed_task_work_tracking_action(target_root, current_work)
    if completed_task_action is not None:
        actions.append(completed_task_action)
    completed_action = _completed_closeout_action(target_root, current_work)
    if completed_action is not None:
        actions.append(completed_action)
    completed_observation_action = _completed_observation_work_tracking_action(
        target_root,
        current_work,
    )
    if completed_observation_action is not None:
        actions.append(completed_observation_action)
    return actions


def _repair_plan_split(
    repair_actions: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Split repair actions into (safe, manual_review).

    safe=True actions are auto-applyable by `aegis repair --apply`; everything else needs
    explicit human resolution (and is skipped by `_apply_repair_action`). Single-sourced so
    `next_action` (TM 225) and `doctor` classify repairs by exactly the same predicate."""

    safe = [action for action in repair_actions if action.get("safe") is True]
    manual = [action for action in repair_actions if action.get("safe") is not True]
    return safe, manual


def _classify_doctor_state(
    *,
    manifest: Mapping[str, Any] | None,
    current_work: Mapping[str, Any] | None,
    checks: Sequence[Mapping[str, Any]],
    repair_actions: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    if manifest is None:
        return "not_installed", "failed"
    if not isinstance(current_work, Mapping):
        return "installed_no_current_work", (
            "healthy" if not _doctor_summary(checks)["failed_required"] else "repairable"
        )
    pending_check = next(
        (check for check in checks if check.get("id") == "mutation.pending_tracking_empty"),
        None,
    )
    if isinstance(pending_check, Mapping) and pending_check.get("status") == "fail":
        return "pending_tracking", "blocked"
    status_value = str(current_work.get("status") or "")
    work_mode = str(current_work.get("mode") or "task")
    if work_mode == "observation" and status_value == "completed":
        summary = _doctor_summary(checks)
        if summary["failed_required"]:
            return "observation_completed", "repairable"
        return "observation_completed", "degraded" if summary["warnings"] else "healthy"
    if status_value == "completed" and current_work.get("closeout_passed_at"):
        summary = _doctor_summary(checks)
        if summary["failed_required"]:
            return "completed_closeout", "repairable"
        return "completed_closeout", "degraded" if summary["warnings"] else "healthy"
    workflow_failed = any(
        check.get("category") == "workflow" and check.get("status") == "fail" for check in checks
    )
    if workflow_failed:
        return "workflow_scaffold_incomplete", "repairable" if repair_actions else "failed"
    summary = _doctor_summary(checks)
    if summary["failed_required"]:
        return "installed_with_failures", "repairable" if repair_actions else "failed"
    if summary["warnings"]:
        return (
            "observation_ready" if work_mode == "observation" else "in_progress_ready"
        ), "degraded"
    return ("observation_ready" if work_mode == "observation" else "in_progress_ready"), "healthy"


def doctor(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    default_primary_agent: str = "claude",
    default_agents: Sequence[str] | None = None,
    invoking_agent: str | None = None,
) -> dict[str, Any]:
    """Diagnose installed Aegis state without mutating the target repository."""

    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve()
    manifest_path = target_root / AEGIS_MANIFEST_REL
    manifest = _read_json(manifest_path)
    pending_tracking = _classify_pending_tracking(target_root)
    checks: list[dict[str, Any]] = []
    current_work: dict[str, Any] | None = None

    if manifest is None:
        checks.append(
            _strict_check(
                "aegis.manifest",
                category="manifest",
                required=True,
                passed=False,
                message="Aegis manifest missing or invalid JSON",
                details={"path": AEGIS_MANIFEST_REL},
            )
        )
    else:
        try:
            _validate_with_schema(source, "foundation-manifest.schema.json", manifest)
            checks.append(
                _strict_check(
                    "aegis.manifest",
                    category="manifest",
                    required=True,
                    passed=True,
                    message="Aegis manifest is valid",
                    details={"path": AEGIS_MANIFEST_REL},
                )
            )
        except ValidationError as exc:
            checks.append(
                _strict_check(
                    "aegis.manifest",
                    category="manifest",
                    required=True,
                    passed=False,
                    message=f"Aegis manifest schema validation failed: {exc.message}",
                    details={"path": AEGIS_MANIFEST_REL, "schema_path": list(exc.schema_path)},
                )
            )
        strict_checks = _strict_verification_checks(
            target_root,
            manifest,
            pending_tracking=pending_tracking,
        )
        checks.extend(strict_checks)
        current_work_path = target_root / AEGIS_CURRENT_WORK_REL
        current_work = _read_json(current_work_path)
        if not current_work_path.exists():
            for check in checks:
                if check.get("id") == "workflow.current_work":
                    check["required"] = False
                    check["status"] = "pass"
                    check["message"] = (
                        "no active current work; run aegis start or aegis kickoff before source edits"
                    )

    repair_actions = _doctor_repair_actions(target_root, source, manifest, current_work)
    active_root = target_root / "docs/ai/work-tracking/active"
    active_folders = sorted(
        path.relative_to(target_root).as_posix()
        for path in active_root.glob("*-ACTIVE")
        if path.is_dir()
    )
    current_work_rel = ""
    if isinstance(current_work, Mapping):
        paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
        current_work_rel = str(paths.get("work_tracking") or "").strip()
    stale_active = [path for path in active_folders if path != current_work_rel]
    if stale_active:
        checks.append(
            _strict_check(
                "workflow.stale_active_folders",
                category="workflow",
                required=False,
                passed=False,
                message="non-current ACTIVE work-tracking folders exist",
                details={"folders": stale_active, "current": current_work_rel},
            )
        )
    degraded_events = _degraded_events(target_root)
    unacknowledged_degraded = [
        event
        for event in degraded_events
        if not event.get("acknowledged_at") and not event.get("resolved_at")
    ]
    checks.append(
        _strict_check(
            "runtime.degraded_events_acknowledged",
            category="runtime",
            required=False,
            passed=not unacknowledged_degraded,
            message=(
                "no unacknowledged degraded gate events"
                if not unacknowledged_degraded
                else "unacknowledged degraded gate events require operator review"
            ),
            details={
                "path": AEGIS_DEGRADED_EVENTS_REL,
                "total": len(degraded_events),
                "unacknowledged": unacknowledged_degraded,
            },
        )
    )
    enforcement = _read_enforcement_state(target_root)
    checks.append(
        _strict_check(
            "runtime.enforcement_mode",
            category="runtime",
            required=False,
            passed=enforcement.get("mode") != "advisory",
            message=(
                "Aegis enforcement is strict"
                if enforcement.get("mode") != "advisory"
                else "Aegis enforcement is advisory; gates record would-block decisions but do not block"
            ),
            details=enforcement,
        )
    )

    current_state, status_value = _classify_doctor_state(
        manifest=manifest,
        current_work=current_work,
        checks=checks,
        repair_actions=repair_actions,
    )
    safe_actions, manual_actions = _repair_plan_split(repair_actions)
    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": _iso_now(),
        "target_root": str(target_root),
        "read_only": True,
        "status": status_value,
        "current_state": current_state,
        "enforcement": enforcement,
        "pending_tracking": pending_tracking,
        "checks": checks,
        "summary": _doctor_summary(checks),
        "repair_plan": {
            "available": bool(repair_actions),
            "safe": len(safe_actions),
            "manual_review": len(manual_actions),
            "actions": repair_actions,
            "apply_command": "aegis repair --apply" if safe_actions else None,
        },
        "next_action": next_action(
            target_root,
            source_root=source,
            default_primary_agent=default_primary_agent,
            default_agents=default_agents,
            invoking_agent=invoking_agent,
        ),
    }


def _apply_repair_action(
    target_root: Path,
    source_root: Path,
    manifest: Mapping[str, Any] | None,
    action: Mapping[str, Any],
) -> dict[str, Any]:
    kind = str(action.get("kind") or "")
    rel_path = str(action.get("path") or "")
    target = target_root / rel_path
    if action.get("safe") is not True:
        return {"id": action.get("id"), "status": "skipped", "reason": "manual review action"}
    if kind == "restore_managed_file":
        if not isinstance(manifest, Mapping):
            return {"id": action.get("id"), "status": "skipped", "reason": "manifest unavailable"}
        asset = _doctor_manifest_assets(target_root, source_root, manifest).get(rel_path)
        if asset is None:
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "managed asset unavailable",
            }
        if target.exists():
            return {"id": action.get("id"), "status": "skipped", "reason": "path already exists"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(asset.content)
        if asset.executable:
            target.chmod(target.stat().st_mode | 0o755)
        return {"id": action.get("id"), "status": "applied", "path": rel_path}
    if kind == "chmod_executable":
        if not target.is_file():
            return {"id": action.get("id"), "status": "skipped", "reason": "file missing"}
        target.chmod(target.stat().st_mode | 0o755)
        return {"id": action.get("id"), "status": "applied", "path": rel_path}
    if kind == "ensure_directory":
        target.mkdir(parents=True, exist_ok=True)
        return {"id": action.get("id"), "status": "applied", "path": rel_path}
    if kind == "recreate_symlink":
        details = action.get("details") if isinstance(action.get("details"), Mapping) else {}
        target_rel = str(details.get("target") or "")
        link_target = str(details.get("link_target") or "")
        if not target_rel or not (target_root / target_rel).is_file():
            return {"id": action.get("id"), "status": "skipped", "reason": "target file missing"}
        if target.exists() and not target.is_symlink():
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "non-symlink path exists",
            }
        if target.is_symlink():
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(
            link_target or os.path.relpath(target_root / target_rel, start=target.parent)
        )
        return {"id": action.get("id"), "status": "applied", "path": rel_path}
    if kind == "normalize_completed_closeout":
        current_path = target_root / AEGIS_CURRENT_WORK_REL
        current_work = _read_json(current_path)
        closeout_report = _read_json(target_root / AEGIS_CLOSEOUT_REPORT_REL)
        if (
            not isinstance(current_work, MutableMapping)
            or not isinstance(closeout_report, Mapping)
            or closeout_report.get("status") != "passed"
        ):
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "completed closeout evidence unavailable",
            }
        if not _closeout_report_matches_current_work(closeout_report, current_work):
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "closeout evidence belongs to a different work envelope",
            }
        current_work["status"] = "completed"
        task = (
            current_work.get("task")
            if isinstance(current_work.get("task"), MutableMapping)
            else None
        )
        if task is not None:
            task["status"] = "completed"
        current_work["closeout_passed_at"] = str(
            closeout_report.get("closed_at") or closeout_report.get("checked_at") or _iso_now()
        )
        current_work["closeout_report"] = AEGIS_CLOSEOUT_REPORT_REL
        current_path.write_text(_dump_json(current_work), encoding="utf-8")
        return {"id": action.get("id"), "status": "applied", "path": rel_path}
    if kind == "remove_mismatched_closeout_metadata":
        current_path = target_root / AEGIS_CURRENT_WORK_REL
        current_work = _read_json(current_path)
        closeout_report = _read_json(target_root / AEGIS_CLOSEOUT_REPORT_REL)
        if (
            not isinstance(current_work, MutableMapping)
            or not isinstance(closeout_report, Mapping)
            or closeout_report.get("status") != "passed"
        ):
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "mismatched closeout evidence unavailable",
            }
        if _closeout_report_matches_current_work(closeout_report, current_work):
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "closeout evidence matches current work",
            }
        if not (current_work.get("closeout_passed_at") or current_work.get("closeout_report")):
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "current work has no closeout metadata",
            }
        current_work.pop("closeout_passed_at", None)
        current_work.pop("closeout_report", None)
        current_work["status"] = "in-progress"
        current_work["updated_at"] = _iso_now()
        task = (
            current_work.get("task")
            if isinstance(current_work.get("task"), MutableMapping)
            else None
        )
        if task is not None:
            task["status"] = "in-progress"
        current_path.write_text(_dump_json(current_work), encoding="utf-8")
        return {"id": action.get("id"), "status": "applied", "path": rel_path}
    if kind == "archive_completed_task_work_tracking":
        archived = _archive_completed_work_tracking_path(target_root, rel_path)
        if archived is None:
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "completed task ACTIVE folder unavailable",
                "path": rel_path,
            }
        report_path = target_root / AEGIS_CLOSEOUT_REPORT_REL
        report = _read_json(report_path)
        if isinstance(report, MutableMapping):
            report_current = (
                report.get("current_work")
                if isinstance(report.get("current_work"), MutableMapping)
                else None
            )
            if report_current is not None:
                report_paths = (
                    report_current.get("paths")
                    if isinstance(report_current.get("paths"), MutableMapping)
                    else None
                )
                if report_paths is not None:
                    _replace_work_tracking_path_prefix(
                        report_paths,
                        archived["from"],
                        archived["to"],
                    )
            report["archived_work_tracking"] = dict(archived)
            report_path.write_text(_dump_json(report), encoding="utf-8")
        current_path = target_root / AEGIS_CURRENT_WORK_REL
        current_work = _read_json(current_path)
        if isinstance(current_work, MutableMapping):
            paths = (
                current_work.get("paths")
                if isinstance(current_work.get("paths"), MutableMapping)
                else None
            )
            if paths is not None:
                _replace_work_tracking_path_prefix(paths, archived["from"], archived["to"])
                current_path.write_text(_dump_json(current_work), encoding="utf-8")
        return {
            "id": action.get("id"),
            "status": "applied",
            "path": archived["from"],
            "details": {"archive_path": archived["to"]},
        }
    if kind == "archive_completed_observation_work_tracking":
        archived = _archive_completed_observation_work_tracking_path(target_root, rel_path)
        if archived is None:
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "completed observation ACTIVE folder unavailable",
                "path": rel_path,
            }
        report_path = target_root / AEGIS_OBSERVATION_REPORT_REL
        report = _read_json(report_path)
        if isinstance(report, MutableMapping):
            report_paths = (
                report.get("paths") if isinstance(report.get("paths"), MutableMapping) else None
            )
            if report_paths is not None:
                _replace_work_tracking_path_prefix(report_paths, archived["from"], archived["to"])
            report["archived_work_tracking"] = dict(archived)
            report_path.write_text(_dump_json(report), encoding="utf-8")
        current_path = target_root / AEGIS_CURRENT_WORK_REL
        current_work = _read_json(current_path)
        if (
            isinstance(current_work, MutableMapping)
            and str(current_work.get("mode") or "") == "observation"
            and str(current_work.get("status") or "") == "completed"
        ):
            paths = (
                current_work.get("paths")
                if isinstance(current_work.get("paths"), MutableMapping)
                else None
            )
            if paths is not None:
                _replace_work_tracking_path_prefix(paths, archived["from"], archived["to"])
            current_path.write_text(_dump_json(current_work), encoding="utf-8")
        return {
            "id": action.get("id"),
            "status": "applied",
            "path": archived["from"],
            "details": {"archive_path": archived["to"]},
        }
    if kind == "normalize_plan_table":
        current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
        preview = _plan_table_repair_preview(target_root, current_work)
        if preview is None:
            return {
                "id": action.get("id"),
                "status": "skipped",
                "reason": "plan table already clean",
            }
        plan_path = target_root / str(preview["path"])
        plan_path.write_text(str(preview["text"]), encoding="utf-8")
        return {
            "id": action.get("id"),
            "status": "applied",
            "path": str(preview["path"]),
            "details": {"steps": list(preview["steps"])},
        }
    return {
        "id": action.get("id"),
        "status": "skipped",
        "reason": f"unsupported repair kind: {kind}",
    }


def purge_read_only_pending(target_dir: str | Path, *, apply: bool = False) -> dict[str, Any]:
    """Batch-purge read-only/inspection events from the pending-tracking queue (TM 221).

    Cleans a pre-#224 backlog of read-only false-positives so they are never drained into
    a plan step's required-evidence. Preview by default; mutates only with apply=True.
    Fail-KEEP: only events _stored_event_is_read_only proves read-only are dropped; any
    classification or import uncertainty retains the event. Touches ONLY the pending
    queue file — never surfaces or plan cells.
    """

    target_root = _resolve_target_root(target_dir)
    events = _pending_tracking_events(target_root)
    read_only = [e for e in events if _stored_event_is_read_only(target_root, e)]
    kept = [e for e in events if not _stored_event_is_read_only(target_root, e)]
    purged_ids = [str(e.get("id") or "") for e in read_only]
    if apply and read_only:
        _write_pending_tracking_events(target_root, kept)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "purged" if (apply and read_only) else "preview",
        "applied": bool(apply and read_only),
        "target_root": str(target_root),
        "total_pending": len(events),
        "read_only_count": len(read_only),
        "kept_count": len(kept),
        "purged": [
            {"id": str(e.get("id") or ""), "tool": e.get("tool"), "evidence": e.get("evidence")}
            for e in read_only
        ],
        "purged_ids": purged_ids,
        "paths": {"pending_tracking": AEGIS_PENDING_TRACKING_REL},
    }


def repair(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    apply: bool = False,
) -> dict[str, Any]:
    """Preview or apply safe Aegis state repairs."""

    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve()
    preflight = doctor(target_root, source_root=source)
    actions = list(preflight.get("repair_plan", {}).get("actions") or [])
    safe_actions = [
        action for action in actions if isinstance(action, Mapping) and action.get("safe") is True
    ]
    if not apply:
        return {
            "schema_version": SCHEMA_VERSION,
            "checked_at": _iso_now(),
            "target_root": str(target_root),
            "read_only": True,
            "status": "preview",
            "current_state": preflight.get("current_state"),
            "repair_plan": preflight.get("repair_plan"),
            "applied": [],
            "report_written": False,
        }
    if preflight.get("current_state") == "pending_tracking":
        return {
            "schema_version": SCHEMA_VERSION,
            "checked_at": _iso_now(),
            "target_root": str(target_root),
            "read_only": False,
            "status": "blocked",
            "reason": "pending S:W:H:E tracking must be logged before repair can mutate workflow state",
            "current_state": preflight.get("current_state"),
            "repair_plan": preflight.get("repair_plan"),
            "applied": [],
            "report_written": False,
            "next_action": preflight.get("next_action"),
        }

    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    applied = [
        _apply_repair_action(target_root, source, manifest, action) for action in safe_actions
    ]
    postflight = doctor(target_root, source_root=source)
    report = {
        "schema_version": SCHEMA_VERSION,
        "checked_at": _iso_now(),
        "target_root": str(target_root),
        "read_only": False,
        "status": "applied",
        "preflight": {
            "status": preflight.get("status"),
            "current_state": preflight.get("current_state"),
            "summary": preflight.get("summary"),
        },
        "applied": applied,
        "postflight": {
            "status": postflight.get("status"),
            "current_state": postflight.get("current_state"),
            "summary": postflight.get("summary"),
        },
        "report_written": True,
        "reports": [AEGIS_REPAIR_REPORT_REL],
    }
    report_path = target_root / AEGIS_REPAIR_REPORT_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_dump_json(report), encoding="utf-8")
    return report


def _entrypoint_uninstall_operation(
    target_root: Path,
    rel_path: str,
    *,
    begin_marker: str,
    end_marker: str,
    existing_heading: str,
    expected_aegis_content: bytes | None = None,
) -> dict[str, Any] | None:
    target = target_root / rel_path
    if not target.is_file():
        return None
    existing = target.read_bytes()
    stripped = _strip_managed_entrypoint(
        existing,
        begin_marker=begin_marker,
        end_marker=end_marker,
        existing_heading=existing_heading,
    )
    if stripped is None:
        return {
            "action": "manual-review",
            "path": rel_path,
            "classification": "manual-review",
            "safe_to_apply": False,
            "reason": "entrypoint is not UTF-8; Aegis cannot safely remove the managed block",
        }
    if stripped == existing:
        if expected_aegis_content is not None and existing == expected_aegis_content:
            return {
                "action": "remove",
                "path": rel_path,
                "classification": "remove",
                "safe_to_apply": True,
                "reason": "remove entrypoint that exactly matches Aegis-managed default content",
            }
        return None
    if stripped.strip():
        return {
            "action": "modify",
            "path": rel_path,
            "classification": "modify",
            "safe_to_apply": True,
            "reason": "remove Aegis-managed runtime block and preserve project-owned content",
            "content": stripped.decode("utf-8"),
        }
    return {
        "action": "remove",
        "path": rel_path,
        "classification": "remove",
        "safe_to_apply": True,
        "reason": "remove entrypoint containing only the Aegis-managed runtime block",
    }


def _codex_hooks_uninstall_operation(target_root: Path) -> dict[str, Any] | None:
    target = target_root / CODEX_HOOKS_REL
    if not target.is_file():
        return None
    payload = _parse_codex_hooks(target.read_bytes())
    if payload is None:
        return {
            "action": "manual-review",
            "path": CODEX_HOOKS_REL,
            "classification": "manual-review",
            "safe_to_apply": False,
            "reason": "Codex hooks are not valid mergeable JSON; refusing to remove project hooks.",
        }
    if not _remove_managed_codex_hook_handlers(payload):
        return None
    if not payload:
        return {
            "action": "remove",
            "path": CODEX_HOOKS_REL,
            "classification": "remove",
            "safe_to_apply": True,
            "reason": "remove Codex hooks file containing only Aegis-managed handlers",
        }
    return {
        "action": "modify",
        "path": CODEX_HOOKS_REL,
        "classification": "modify",
        "safe_to_apply": True,
        "reason": "remove exact Aegis Codex handlers and preserve every unrelated project hook",
        "content": _dump_json(payload),
    }


def _path_uninstall_operation(target_root: Path, rel_path: str) -> dict[str, Any] | None:
    target = target_root / rel_path
    if not target.exists() and not target.is_symlink():
        return None
    return {
        "action": "remove",
        "path": rel_path,
        "classification": "remove",
        "safe_to_apply": True,
        "reason": "remove Aegis-managed install or workflow artifact",
    }


def _current_work_uninstall_paths(target_root: Path) -> list[str]:
    current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    if not isinstance(current_work, Mapping):
        return []
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    candidates = [
        str(paths.get("session_current") or "sessions/current"),
        str(paths.get("session") or ""),
        "sessions/state.json",
        str(paths.get("plan_current") or "plans/current"),
        str(paths.get("plan") or ""),
        str(paths.get("work_tracking") or ""),
    ]
    return [path for path in candidates if path]


def _uninstall_operations(
    target_root: Path,
    *,
    remove_hook_scripts: bool,
    source_root: Path | None,
) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    manifest = _read_json(target_root / AEGIS_MANIFEST_REL)
    enabled_agents = _enabled_agents_from_manifest(manifest) or ("claude",)
    primary_agent = str((manifest or {}).get("primary_agent") or enabled_agents[0])
    for operation in (
        _codex_hooks_uninstall_operation(target_root),
        _entrypoint_uninstall_operation(
            target_root,
            "CLAUDE.md",
            begin_marker=AEGIS_CLAUDE_BLOCK_BEGIN,
            end_marker=AEGIS_CLAUDE_BLOCK_END,
            existing_heading="Existing Project Instructions",
            expected_aegis_content=(
                _render_claude_entrypoint() if "claude" in enabled_agents else None
            ),
        ),
        _entrypoint_uninstall_operation(
            target_root,
            "CODEX.md",
            begin_marker=AEGIS_CODEX_BLOCK_BEGIN,
            end_marker=AEGIS_CODEX_BLOCK_END,
            existing_heading="Existing Codex Instructions",
            expected_aegis_content=None,
        ),
        _entrypoint_uninstall_operation(
            target_root,
            "AGENTS.md",
            begin_marker=AEGIS_AGENTS_BLOCK_BEGIN,
            end_marker=AEGIS_AGENTS_BLOCK_END,
            existing_heading="Existing Agent Instructions",
            expected_aegis_content=(
                _render_agents_doc(primary_agent, enabled_agents)
                if source_root is not None
                else None
            ),
        ),
    ):
        if operation is not None:
            operations.append(operation)

    remove_paths = [
        ".claude/settings.json",
        *SHARED_SCHEMA_FILES,
        *_current_work_uninstall_paths(target_root),
    ]
    if remove_hook_scripts:
        remove_paths.extend(
            [
                *[path for path in CLAUDE_REQUIRED_FILES if path.startswith(".claude/scripts/")],
                *CLAUDE_SUPPORT_FILES,
            ]
        )
    remove_paths.append(".aegis")

    for rel_path in dict.fromkeys(remove_paths):
        operation = _path_uninstall_operation(target_root, rel_path)
        if operation is not None:
            operations.append(operation)
    return operations


def _remove_path(target_root: Path, rel_path: str) -> dict[str, Any]:
    target = target_root / rel_path
    try:
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()
        else:
            return {"path": rel_path, "status": "skipped", "reason": "path missing"}
    except OSError as exc:
        return {"path": rel_path, "status": "failed", "reason": str(exc)}
    removed = [rel_path]
    current = target.parent
    while current != target_root and target_root in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        removed.append(_repo_path(current, target_root))
        current = current.parent
    return {"path": rel_path, "status": "applied", "removed": removed}


def _apply_uninstall_operation(target_root: Path, operation: Mapping[str, Any]) -> dict[str, Any]:
    if operation.get("safe_to_apply") is not True:
        return {
            "path": operation.get("path"),
            "status": "skipped",
            "reason": "manual review action",
        }
    action = str(operation.get("action") or "")
    rel_path = str(operation.get("path") or "")
    if action == "modify":
        content = operation.get("content")
        if not isinstance(content, str):
            return {"path": rel_path, "status": "failed", "reason": "missing replacement content"}
        _write_text(target_root, rel_path, content)
        return {"path": rel_path, "status": "applied", "action": "modify"}
    if action == "remove":
        return {"action": "remove", **_remove_path(target_root, rel_path)}
    return {"path": rel_path, "status": "skipped", "reason": f"unsupported action: {action}"}


def uninstall(
    target_dir: str | Path,
    *,
    source_root: str | Path | None = None,
    apply: bool = False,
    remove_hook_scripts: bool = False,
) -> dict[str, Any]:
    """Preview or remove Aegis-managed install/workflow artifacts from a target project."""

    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve() if source_root is not None else None
    operations = _uninstall_operations(
        target_root,
        remove_hook_scripts=remove_hook_scripts,
        source_root=source,
    )
    manual_review = [
        operation for operation in operations if operation.get("safe_to_apply") is not True
    ]
    if not apply:
        return {
            "schema_version": SCHEMA_VERSION,
            "checked_at": _iso_now(),
            "target_root": str(target_root),
            "read_only": True,
            "status": "preview",
            "operations": [
                {key: value for key, value in operation.items() if key != "content"}
                for operation in operations
            ],
            "summary": {
                "operations": len(operations),
                "safe": len(operations) - len(manual_review),
                "manual_review": len(manual_review),
            },
            "current_session_note": (
                AEGIS_UNINSTALL_TRANSIENT_NOTE
                if not remove_hook_scripts
                else "hook scripts are selected for removal; use outside an active Claude session"
            ),
        }
    if manual_review:
        return {
            "schema_version": SCHEMA_VERSION,
            "checked_at": _iso_now(),
            "target_root": str(target_root),
            "read_only": False,
            "status": "refused",
            "reason": "manual-review uninstall operations must be resolved before apply",
            "operations": [
                {key: value for key, value in operation.items() if key != "content"}
                for operation in operations
            ],
            "applied": [],
        }
    applied = [_apply_uninstall_operation(target_root, operation) for operation in operations]
    failures = [item for item in applied if item.get("status") == "failed"]
    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": _iso_now(),
        "target_root": str(target_root),
        "read_only": False,
        "status": "failed" if failures else "applied",
        "operations": [
            {key: value for key, value in operation.items() if key != "content"}
            for operation in operations
        ],
        "applied": applied,
        "summary": {
            "operations": len(operations),
            "applied": sum(1 for item in applied if item.get("status") == "applied"),
            "skipped": sum(1 for item in applied if item.get("status") == "skipped"),
            "failed": len(failures),
        },
        "current_session_note": (
            AEGIS_UNINSTALL_TRANSIENT_NOTE
            if not remove_hook_scripts
            else "hook scripts were selected for removal"
        ),
    }


def format_doctor_summary(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    repair_plan = (
        report.get("repair_plan") if isinstance(report.get("repair_plan"), Mapping) else {}
    )
    enforcement = (
        report.get("enforcement") if isinstance(report.get("enforcement"), Mapping) else {}
    )
    pending = (
        report.get("pending_tracking")
        if isinstance(report.get("pending_tracking"), Mapping)
        else {}
    )
    pending_counts = pending.get("counts") if isinstance(pending.get("counts"), Mapping) else {}
    return "\n".join(
        [
            f"Aegis doctor: {report.get('status')} ({report.get('current_state')})",
            f"Enforcement: {enforcement.get('mode', 'strict')}",
            (
                "Pending tracking: "
                f"{pending_counts.get('total', 0)} "
                f"({pending.get('classification', 'unknown')})"
            ),
            f"Checks: {summary.get('total', 0)} total, {summary.get('failed_required', 0)} required failures, {summary.get('warnings', 0)} warnings",
            f"Repair plan: {repair_plan.get('safe', 0)} safe, {repair_plan.get('manual_review', 0)} manual-review",
            "",
        ]
    )


def format_next_summary(payload: Mapping[str, Any]) -> str:
    """TM 189: concise human rendering of `aegis next`, leading with the continuation brief.

    A bare "continue" means: do exactly the one next_safe_action below, honour the
    confirmation boundaries, then re-run `aegis next`. The full payload (`--all --json`) carries
    suggested CLI/MCP calls and copyable repairs."""

    brief = (
        payload.get("continuation_brief")
        if isinstance(payload.get("continuation_brief"), Mapping)
        else {}
    )
    boundaries = [str(item) for item in (brief.get("confirmation_boundary") or []) if str(item)]
    stops = [str(item) for item in (brief.get("stop_conditions") or []) if str(item)]
    lines = [
        f"Aegis next: {payload.get('state')} (phase: {payload.get('phase')})",
        f"Active authority: {brief.get('current_task_authority', 'none')}",
        f'"continue" means: {brief.get("continue_means", "")}',
        f"Next safe action: {brief.get('next_safe_action', payload.get('next_required_action', ''))}",
        f"Required: {payload.get('next_required_action', '')}",
        f"Suggested: {payload.get('suggested_cli', '')}",
    ]
    if boundaries:
        lines.append("Confirm first: " + "; ".join(boundaries))
    if stops:
        lines.append("Stop if: " + "; ".join(stops))
    lines.append(f"Artifact policy: {brief.get('artifact_policy', '')}")
    lines.append(
        "(read-only guidance — aegis next grants no mutation authority; re-run after the one step)"
    )
    lines.append("")
    return "\n".join(lines)


def format_repair_summary(report: Mapping[str, Any]) -> str:
    applied = report.get("applied") if isinstance(report.get("applied"), list) else []
    return "\n".join(
        [
            f"Aegis repair: {report.get('status')}",
            f"Applied/skipped actions: {len(applied)}",
            f"Report written: {report.get('report_written')}",
            "",
        ]
    )


def format_uninstall_summary(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    return "\n".join(
        [
            f"Aegis uninstall: {report.get('status')}",
            f"Operations: {summary.get('operations', 0)}",
            f"Applied: {summary.get('applied', 0)}",
            f"Failed: {summary.get('failed', 0)}",
            f"Note: {report.get('current_session_note')}",
            "",
        ]
    )


def verify(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    strict: bool = False,
    dry_run: bool = False,
    default_primary_agent: str = "claude",
    default_agents: Sequence[str] | None = None,
) -> dict[str, Any]:
    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve()
    manifest_path = target_root / AEGIS_MANIFEST_REL
    manifest = _read_json(manifest_path)
    enforcement = _read_enforcement_state(target_root)
    pending_tracking = _classify_pending_tracking(target_root)
    mode = "strict" if strict else "standard"
    checks: list[dict[str, Any]] = []
    if manifest is None:
        guidance_primary_agent, guidance_agents = _normalise_default_agent_selection(
            default_primary_agent,
            default_agents,
        )
        install_cli = (
            f"./.aegis/bin/aegis install --target-dir . "
            f"{_agent_selection_cli_args(guidance_primary_agent, guidance_agents)} --apply"
        )
        report = {
            "schema_version": SCHEMA_VERSION,
            "mode": mode,
            "status": "failed",
            "verified_at": _iso_now(),
            "target_root": str(target_root),
            "manifest_path": AEGIS_MANIFEST_REL,
            "enforcement": enforcement,
            "pending_tracking": pending_tracking,
            "dry_run": dry_run,
            "report_written": False,
            "checks": [
                {
                    "gate_id": "aegis.manifest",
                    "required": True,
                    "status": "fail",
                    "message": "Aegis manifest missing or invalid JSON.",
                }
            ],
            "summary": {
                "total": 1,
                "failed_required": 1,
                "warnings": 0,
                "unsupported": 0,
            },
            "next_action": _workflow_next_action(
                "install_aegis_before_verify",
                "Aegis is not installed in this target. Install it before running strict verification.",
                suggested_cli=install_cli,
                suggested_mcp_tool="aegis.install",
                suggested_mcp_arguments={
                    "target_dir": ".",
                    "profile": "generic",
                    "primary_agent": guidance_primary_agent,
                    "agents": list(guidance_agents),
                    "apply": True,
                },
            ),
        }
        if not dry_run:
            _write_verify_report(target_root, report)
            report["report_written"] = True
        return report

    try:
        _validate_with_schema(source, "foundation-manifest.schema.json", manifest)
        checks.append(
            {
                "gate_id": "aegis.manifest_schema",
                "required": True,
                "status": "pass",
                "message": "manifest schema valid",
            }
        )
    except ValidationError as exc:
        checks.append(
            {
                "gate_id": "aegis.manifest_schema",
                "required": True,
                "status": "fail",
                "message": _manifest_schema_failure_message(source, target_root, manifest, exc),
            }
        )

    for gate in manifest.get("gates", []) if isinstance(manifest.get("gates"), list) else []:
        if isinstance(gate, Mapping):
            checks.append(_verify_gate(target_root, gate))

    if strict:
        checks.extend(
            _strict_verification_checks(
                target_root,
                manifest,
                pending_tracking=pending_tracking,
            )
        )
    if enforcement.get("mode") == "advisory":
        checks.append(
            {
                "gate_id": "runtime.enforcement_mode",
                "required": False,
                "status": "warn",
                "message": "Aegis enforcement is advisory; gates record would-block decisions but do not block.",
                "details": enforcement,
            }
        )

    failed_required = [
        check for check in checks if check.get("required") and check.get("status") == "fail"
    ]
    pending_tracking_expected = _expects_pending_tracking(target_root)
    verification_handler = _workflow_log_handler(target_root, "verification")
    if pending_tracking_expected:
        strict_log_cli = (
            "./.aegis/bin/aegis log --target-dir . --pending-id current "
            "--note 'Recorded strict verification evidence' "
            "--plan-step plan-step-verify --plan-status completed"
        )
        strict_log_mcp_arguments = {
            "target_dir": ".",
            "pending_event_id": "current",
            "note": "Recorded strict verification evidence",
            "plan_step": "plan-step-verify",
            "plan_status": "completed",
            "apply": True,
        }
    else:
        strict_log_cli = (
            f"./.aegis/bin/aegis log --target-dir . --handler {verification_handler} "
            f"--evidence {AEGIS_VERIFY_REPORT_REL} "
            "--note 'Recorded strict verification evidence' "
            "--plan-step plan-step-verify --plan-status completed"
        )
        strict_log_mcp_arguments = {
            "target_dir": ".",
            "handler": verification_handler,
            "evidence": AEGIS_VERIFY_REPORT_REL,
            "note": "Recorded strict verification evidence",
            "event_class": "verification",
            "plan_step": "plan-step-verify",
            "plan_status": "completed",
            "apply": True,
        }

    report = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "status": "failed" if failed_required else "passed",
        "verified_at": _iso_now(),
        "target_root": str(target_root),
        "manifest_path": AEGIS_MANIFEST_REL,
        "enforcement": enforcement,
        "pending_tracking": pending_tracking,
        "dry_run": dry_run,
        "report_written": False,
        "summary": {
            "total": len(checks),
            "failed_required": len(failed_required),
            "warnings": sum(1 for check in checks if check.get("status") == "warn"),
            "unsupported": sum(1 for check in checks if check.get("status") == "unsupported"),
        },
        "checks": checks,
        "next_action": (
            _workflow_next_action(
                "log_strict_verification_before_closeout",
                "Strict verification passed. Log the verification evidence against plan-step-verify before closeout.",
                suggested_cli=strict_log_cli,
                suggested_mcp_tool="aegis.log",
                suggested_mcp_arguments=strict_log_mcp_arguments,
                details={
                    "evidence": AEGIS_VERIFY_REPORT_REL,
                    "pending_tracking_expected": pending_tracking_expected,
                },
            )
            if strict and not failed_required
            else (
                _workflow_next_action(
                    "repair_verify_failures",
                    "Verification failed. Fix failed required checks before closeout.",
                    details={
                        "failed_required_gates": [
                            str(check.get("gate_id")) for check in failed_required
                        ]
                    },
                )
                if failed_required
                else _workflow_next_action(
                    "standard_verify_complete",
                    "Standard verification report was written. Run strict verification before closeout.",
                    suggested_cli="./.aegis/bin/aegis verify --target-dir . --strict",
                    suggested_mcp_tool="aegis.verify",
                    suggested_mcp_arguments={
                        "target_dir": ".",
                        "strict": True,
                        "acknowledge_report_write": True,
                    },
                )
            )
        ),
    }
    if not dry_run:
        _write_verify_report(target_root, report)
        report["report_written"] = True
    if report["status"] == "passed" and not dry_run:
        manifest["verification"] = {
            "status": "passed",
            "last_verified_at": report["verified_at"],
            "reports": [AEGIS_VERIFY_REPORT_REL],
        }
        manifest_path.write_text(_dump_json(manifest), encoding="utf-8")
    return report


def _write_verify_report(target_root: Path, report: Mapping[str, Any]) -> None:
    reports_dir = target_root / AEGIS_REPORTS_REL
    reports_dir.mkdir(parents=True, exist_ok=True)
    (target_root / AEGIS_VERIFY_REPORT_REL).write_text(_dump_json(report), encoding="utf-8")


def _closeout_check(
    check_id: str,
    *,
    passed: bool,
    message: str,
    category: str = "closeout",
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return _strict_check(
        check_id,
        category=category,
        required=True,
        passed=passed,
        message=message,
        details=details,
    )


def _read_text_or_empty(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _parse_plan_rows(plan_path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for index, line in enumerate(_read_text_or_empty(plan_path).splitlines()):
        if not line.startswith("| plan-step-"):
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) != 4:
            rows[columns[0] if columns else f"malformed-{index}"] = {
                "id": columns[0] if columns else "",
                "description": "",
                "evidence": "",
                "status": "malformed",
                "index": index,
                "malformed": True,
            }
            continue
        rows[columns[0]] = {
            "id": columns[0],
            "description": columns[1],
            "evidence": columns[2],
            "status": columns[3].lower(),
            "index": index,
            "malformed": False,
        }
    return rows


def _parse_tracker_plan_steps(tracker_path: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    pattern = re.compile(r"^-\s+\[(?P<mark>[ xX])\]\s+`?(?P<step>plan-step-[A-Za-z0-9_-]+)`?")
    for line in _read_text_or_empty(tracker_path).splitlines():
        match = pattern.match(line.strip())
        if match:
            statuses[match.group("step")] = (
                "completed" if match.group("mark").lower() == "x" else "pending"
            )
    return statuses


def _semicolon_closes_html_entity(value: str, index: int) -> bool:
    amp_index = value.rfind("&", 0, index)
    if amp_index == -1:
        return False
    candidate = value[amp_index : index + 1]
    return bool(re.fullmatch(r"&(?:#\d+|#[xX][0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);", candidate))


def _unescape_markdown_table_cell(value: str) -> str:
    return str(value).replace("&#124;", "|")


def _clean_evidence_token(value: str) -> str:
    clean = _unescape_markdown_table_cell(value.strip())
    if clean.startswith("`") and clean.endswith("`") and len(clean) > 1:
        return clean[1:-1].strip()
    return clean


def _split_evidence_tokens(raw_evidence: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    in_backticks = False
    for index, char in enumerate(raw_evidence):
        if char == "`":
            in_backticks = not in_backticks
            current.append(char)
            continue
        if (
            char == ";"
            and not in_backticks
            and not _semicolon_closes_html_entity(raw_evidence, index)
        ):
            clean = _clean_evidence_token("".join(current))
            if clean and clean != "_TBD_":
                tokens.append(clean)
            current = []
            continue
        current.append(char)
    if current:
        clean = _clean_evidence_token("".join(current))
        if clean and clean != "_TBD_":
            tokens.append(clean)
    return tokens


def _surface_contains_evidence(surface_text: str, token: str) -> bool:
    if token in surface_text:
        return True
    escaped_token = _markdown_table_cell(token)
    return escaped_token != token and escaped_token in surface_text


_EVIDENCE_COMMAND_METACHARS = set("|&;<>$(){}*?!`'\"")


def _evidence_token_is_path_like(token: str) -> bool:
    """A token is a stable artifact reference (a repo-relative path) rather than a
    free-text command: no whitespace, no shell metacharacters, and it either contains a
    path separator or ends in a file extension."""

    canon = str(token).strip()
    if canon.startswith("./"):
        canon = canon[2:]
    canon = canon.replace("\\", "/").rstrip("/")
    if not canon:
        return False
    if any(ch.isspace() for ch in canon):
        return False
    if any(ch in _EVIDENCE_COMMAND_METACHARS for ch in canon):
        return False
    return ("/" in canon) or bool(re.search(r"\.[A-Za-z0-9]{1,8}\Z", canon))


def _is_closeout_required_evidence(token: str) -> bool:
    if token == "changed files":
        return False
    if token.endswith("/"):
        return False
    if Path(token).name in {
        "TRACKER.md",
        "FINDINGS.md",
        "DECISIONS.md",
        "IMPLEMENTATION.md",
        "CHANGELOG.md",
        "HANDOFF.md",
    }:
        return False
    # TM 218: free-text/compound-command evidence tokens are ADVISORY, not required. A
    # `cmd`...`` (or `note`...`) token records a command an operator ran, not a durable
    # artifact; requiring its verbatim multi-line string in all six surfaces is brittle and
    # becomes unrecoverable once the originating pending event is consumed (HP-Coach 2026-06-13).
    # The source-truth gates (closeout.strict_verify, mutation.pending_tracking_empty) are
    # independent and computed, so demoting command narration never lets un-evidenced work pass.
    if token.startswith("cmd`") or token.startswith("note`"):
        return False
    # Defensive fallback for command tokens whose marker prefix was stripped upstream:
    # command-shaped (whitespace or shell metachar) and not a path is advisory; real
    # artifact paths (no whitespace/metachars) stay required.
    if not _evidence_token_is_path_like(token) and (
        any(ch.isspace() for ch in token) or any(ch in _EVIDENCE_COMMAND_METACHARS for ch in token)
    ):
        return False
    return True


def _markdown_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## ") and lines[index].strip() != heading:
            end = index
            break
    return "\n".join(lines[start + 1 : end]).strip()


def _markdown_before_heading(text: str, heading: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return "\n".join(lines[:index]).strip()
    return text


def _replace_markdown_section(text: str, heading: str, body_lines: Sequence[str]) -> str:
    lines = text.splitlines()
    replacement = [heading, *body_lines]
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        insert_at = len(lines)
        while insert_at > 0 and not lines[insert_at - 1].strip():
            insert_at -= 1
        next_lines = lines[:insert_at] + ["", *replacement] + lines[insert_at:]
        return "\n".join(next_lines).rstrip() + "\n"

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## ") and lines[index].strip() != heading:
            end = index
            break
    next_lines = lines[:start] + replacement + lines[end:]
    return "\n".join(next_lines).rstrip() + "\n"


def _replace_handoff_semantic_section(text: str, heading: str, body_lines: Sequence[str]) -> str:
    """Replace or insert a closeout-owned HANDOFF section before Progress Log."""

    if any(line.strip() == heading for line in text.splitlines()):
        return _replace_markdown_section(text, heading, body_lines)

    lines = text.splitlines()
    replacement = [heading, *body_lines]
    for index, line in enumerate(lines):
        if line.strip() == "## Progress Log":
            insert_at = index
            while insert_at > 0 and not lines[insert_at - 1].strip():
                insert_at -= 1
            next_lines = lines[:insert_at] + ["", *replacement] + lines[insert_at:]
            return "\n".join(next_lines).rstrip() + "\n"
    return _replace_markdown_section(text, heading, body_lines)


def _first_markdown_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.strip()
    return fallback


def _markdown_tail_from_heading(text: str, heading: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return "\n".join(lines[index:]).rstrip()
    return ""


def _bullet_lines(tokens: Sequence[str], *, fallback: str) -> list[str]:
    unique_tokens = list(dict.fromkeys(token for token in tokens if token))
    if not unique_tokens:
        return [f"- {fallback}"]
    return [f"- `{token}`" for token in unique_tokens]


def _current_work_branch_name(current_work: Mapping[str, Any], paths: Mapping[str, Any]) -> str:
    branch_payload = current_work.get("branch")
    if isinstance(branch_payload, Mapping):
        return str(branch_payload.get("current") or branch_payload.get("name") or "")
    if isinstance(branch_payload, str):
        return branch_payload
    path_branch = paths.get("branch")
    return path_branch if isinstance(path_branch, str) else ""


def _strict_verify_report_is_green(target_root: Path) -> bool:
    report = _read_json(target_root / AEGIS_VERIFY_REPORT_REL)
    return (
        isinstance(report, Mapping)
        and report.get("mode") == "strict"
        and report.get("status") == "passed"
    )


def _handoff_current_state_ok(current_state: str) -> bool:
    return bool(current_state.strip()) and not (
        "has been kicked off through Aegis" in current_state
        and "ready for closeout validation" not in current_state
    )


_HANDOFF_KICKOFF_ONLY_PHRASES = (
    "has been kicked off through Aegis",
    "Confirm scope before implementation",
    "Capture verification evidence",
    "_Pending_",
)


def _handoff_next_steps_ok(next_steps: str) -> bool:
    return bool(next_steps.strip()) and not any(
        phrase in next_steps for phrase in _HANDOFF_KICKOFF_ONLY_PHRASES
    )


def _repair_closeout_handoff_text(
    existing_text: str,
    *,
    current_work: Mapping[str, Any],
    implementation_tokens: Sequence[str],
    verification_tokens: Sequence[str],
    strict_verify_rel: str,
    strict_verify_report_green: bool,
) -> str:
    task = current_work.get("task") if isinstance(current_work.get("task"), Mapping) else {}
    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    task_id = str(task.get("id") or "")
    slug = str(task.get("slug") or "")
    title = str(task.get("title") or f"Task {task_id}")
    branch = _current_work_branch_name(current_work, paths)
    work_label = f"task{task_id}-{slug}" if task_id or slug else "current-work"
    text = existing_text
    if not text.strip():
        text = _first_markdown_title(existing_text, f"# Task {task_id} {title} - Handoff Summary")

    if not _handoff_current_state_ok(_markdown_section(text, "## Current State")):
        text = _replace_handoff_semantic_section(
            text,
            "## Current State",
            [
                f"- Task {task_id} `{slug}` is ready for closeout validation.",
                f"- Title: {title}.",
                f"- Branch: `{branch}`.",
                f"- Current work: `{work_label}`.",
                f"- Strict verification report: `{strict_verify_rel}`.",
                f"- Closeout report target: `{AEGIS_CLOSEOUT_REPORT_REL}`.",
            ],
        )

    if not _handoff_next_steps_ok(_markdown_section(text, "## Next Steps")):
        text = _replace_handoff_semantic_section(
            text,
            "## Next Steps",
            [
                f"1. Review `{AEGIS_CLOSEOUT_REPORT_REL}` after final closeout writes it.",
                "2. Commit and open a pull request with normal git/GitHub commands when delegated.",
                "3. Archive or continue the active work-tracking folder according to the project lifecycle.",
            ],
        )

    handoff_verification_tokens = [
        token
        for token in verification_tokens
        if token != strict_verify_rel or strict_verify_report_green
    ]
    text = _replace_handoff_semantic_section(
        text,
        "## Implementation Evidence",
        _bullet_lines(
            implementation_tokens, fallback="No implementation evidence tokens were available."
        ),
    )
    text = _replace_handoff_semantic_section(
        text,
        "## Verification Evidence",
        _bullet_lines(
            handoff_verification_tokens,
            fallback="No task-specific verification evidence tokens were available.",
        ),
    )
    strict_lines = (
        [f"- `{strict_verify_rel}`"]
        if strict_verify_report_green
        else ["- Strict verification report has not passed on disk."]
    )
    text = _replace_handoff_semantic_section(
        text,
        "## Strict Verification Evidence",
        strict_lines,
    )
    return text.rstrip() + "\n"


def _closeout_progress_line(
    *,
    now: datetime,
    surface: str,
    current_work: Mapping[str, Any],
    handler: str,
    evidence: str,
    note: str,
) -> str:
    task = current_work.get("task") if isinstance(current_work.get("task"), Mapping) else {}
    task_id = str(task.get("id") or "").strip()
    slug = str(task.get("slug") or "").strip()
    session_value = now.strftime("%Y%m%d")
    work_context = f"task{task_id}-{slug}" if task_id or slug else "current-work"
    swhe = f"[S:{session_value}|W:{work_context}|H:{handler}|E:{evidence}]"
    if surface == "session":
        return f"- **[{now.strftime('%H:%M')}]** - {swhe} {note}"
    return f"- **{now.strftime('%Y-%m-%d %H:%M %Z').strip()}** - {swhe} {note}"


def _populate_closeout_surfaces(
    target_root: Path,
    *,
    current_work: Mapping[str, Any],
    surface_paths: Mapping[str, Path],
    surface_texts: MutableMapping[str, str],
    evidence_matrix: Mapping[str, Mapping[str, bool]],
    implementation_tokens: Sequence[str],
    verification_tokens: Sequence[str],
    strict_verify_rel: str,
    strict_verify_report_green: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Back-fill closeout-owned surface references from already-logged plan evidence."""

    entries_by_evidence = _swhe_entries_by_evidence(surface_texts)
    eligible_tokens = list(dict.fromkeys([*implementation_tokens, *verification_tokens]))
    if strict_verify_rel in eligible_tokens and not strict_verify_report_green:
        eligible_tokens = [token for token in eligible_tokens if token != strict_verify_rel]

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "strict_verify_report_green": strict_verify_report_green,
        "eligible_tokens": eligible_tokens,
        "updated_surfaces": [],
        "would_update_surfaces": [],
        "skipped": [],
    }
    now = datetime.now().astimezone().replace(microsecond=0)
    progress_headings = {
        "session": "### Progress Log",
        "tracker": "## Progress Log",
        "implementation": "## Progress Log",
        "changelog": "## Progress Log",
    }
    for token in eligible_tokens:
        present_entries = entries_by_evidence.get(token, [])
        inferred = present_entries[0] if present_entries else {}
        handler = str(inferred.get("handler") or "").strip()
        note = str(inferred.get("note") or "").strip()
        if not handler or not note:
            report["skipped"].append(
                {
                    "evidence": token,
                    "reason": "no_existing_swhe_entry_for_plan_evidence",
                }
            )
            continue
        for surface, heading in progress_headings.items():
            if evidence_matrix.get(token, {}).get(surface):
                continue
            surface_path = surface_paths.get(surface)
            if surface_path is None or not surface_path.is_file():
                report["skipped"].append(
                    {
                        "surface": surface,
                        "evidence": token,
                        "reason": "surface_missing",
                    }
                )
                continue
            item = {"surface": surface, "evidence": token}
            if dry_run:
                report["would_update_surfaces"].append(item)
                continue
            line = _closeout_progress_line(
                now=now,
                surface=surface,
                current_work=current_work,
                handler=handler,
                evidence=token,
                note=note,
            )
            _append_progress_entry(surface_path, heading, line)
            surface_texts[surface] = _read_text_or_empty(surface_path)
            report["updated_surfaces"].append(item)

    handoff_path = surface_paths.get("handoff")
    if handoff_path is not None and handoff_path.is_file():
        before = surface_texts.get("handoff", "")
        repaired = _repair_closeout_handoff_text(
            before,
            current_work=current_work,
            implementation_tokens=implementation_tokens,
            verification_tokens=verification_tokens,
            strict_verify_rel=strict_verify_rel,
            strict_verify_report_green=strict_verify_report_green,
        )
        handoff_changed = repaired != before
        report["handoff"] = {
            "path": _repo_path(handoff_path, target_root),
            "changed": handoff_changed,
            "updated": handoff_changed and not dry_run,
            "would_update": handoff_changed and dry_run,
            "preserved_progress_log": "## Progress Log" in before,
        }
        if handoff_changed and not dry_run:
            handoff_path.write_text(repaired, encoding="utf-8")
            surface_texts["handoff"] = repaired
    else:
        report["handoff"] = {
            "path": _repo_path(handoff_path, target_root) if handoff_path is not None else "",
            "changed": False,
            "updated": False,
            "would_update": False,
            "missing": True,
        }
    return report


def _closeout_readiness(
    target_root: Path, current_work: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    current_work_status = str((current_work or {}).get("status") or "").strip()
    if current_work_status == "completed" and bool((current_work or {}).get("closeout_passed_at")):
        return {
            "status": "passed",
            "command": None,
            "returncode": 0,
            "stdout": "READY from completed closeout state",
            "stderr": "",
            "current_work_status": current_work_status,
        }

    from aegis_foundation.gate import readiness as workflow_readiness

    task_id, readiness_checks, readiness_state = workflow_readiness.evaluate(target_root)
    if readiness_checks:
        return {
            "status": "passed" if readiness_state != workflow_readiness.BLOCKED else "failed",
            "command": "aegis gate readiness --quick --target-dir .",
            "returncode": 2 if readiness_state == workflow_readiness.BLOCKED else 0,
            "stdout": f"{readiness_state} | task={task_id or 'unknown'}",
            "stderr": "",
            "checks": [
                {"status": check.status, "message": check.message} for check in readiness_checks
            ],
        }

    workflow_checks, _current_work = _strict_current_work_checks(target_root)
    failed = [
        check
        for check in workflow_checks
        if check.get("required") and check.get("status") == "fail"
    ]
    return {
        "status": "passed" if not failed else "failed",
        "command": None,
        "returncode": 0 if not failed else 2,
        "stdout": (
            "READY from strict current-work checks"
            if not failed
            else "BLOCKED by strict current-work checks"
        ),
        "stderr": "",
        "checks": workflow_checks,
    }


def _closeout_handoff_checks(
    handoff_text: str,
    *,
    implementation_tokens: Sequence[str],
    verification_tokens: Sequence[str],
    strict_verify_rel: str,
) -> list[dict[str, Any]]:
    current_state = _markdown_section(handoff_text, "## Current State")
    next_steps = _markdown_section(handoff_text, "## Next Steps")
    semantic_text = _markdown_before_heading(handoff_text, "## Progress Log")
    kickoff_only_phrases = (
        "has been kicked off through Aegis",
        "Confirm scope before implementation",
        "Capture verification evidence",
        "_Pending_",
    )
    current_state_ok = bool(current_state.strip()) and not (
        "has been kicked off through Aegis" in current_state
        and "ready for closeout validation" not in current_state
    )
    next_steps_ok = bool(next_steps.strip()) and not any(
        phrase in next_steps for phrase in kickoff_only_phrases
    )

    checks = [
        _closeout_check(
            "closeout.handoff.current_state",
            passed=current_state_ok,
            message=(
                "handoff current state is semantic"
                if current_state_ok
                else "handoff current state is still placeholder/kickoff-oriented"
            ),
        ),
        _closeout_check(
            "closeout.handoff.next_steps",
            passed=next_steps_ok,
            message=(
                "handoff next steps are semantic"
                if next_steps_ok
                else "handoff next steps are still placeholder/kickoff-oriented"
            ),
        ),
    ]

    for check_id, tokens, label in (
        ("closeout.handoff.implementation_evidence", implementation_tokens, "implementation"),
        ("closeout.handoff.verification_evidence", verification_tokens, "verification"),
        ("closeout.handoff.strict_verify_evidence", [strict_verify_rel], "strict verification"),
    ):
        missing = [token for token in tokens if token not in semantic_text]
        checks.append(
            _closeout_check(
                check_id,
                passed=not missing,
                message=(
                    f"handoff semantic sections reference {label} evidence"
                    if not missing
                    else f"handoff semantic sections missing {label} evidence"
                ),
                details={"missing": missing},
            )
        )
    return checks


def _closeout_git_report(
    target_root: Path, *, require_clean_git: bool, include_guidance: bool
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    status_result = _run_target_git(target_root, "status", "--short")
    status_short = (
        status_result.stdout.strip().splitlines() if status_result.returncode == 0 else []
    )
    if require_clean_git:
        checks.append(
            _closeout_check(
                "closeout.git.clean",
                passed=status_result.returncode == 0 and not status_short,
                message=(
                    "git worktree is clean"
                    if status_result.returncode == 0 and not status_short
                    else "git worktree has uncommitted changes"
                ),
                category="git",
                details={"status_short": status_short, "stderr": status_result.stderr.strip()},
            )
        )
    guidance = []
    if include_guidance:
        guidance = [
            "git status --short",
            "git add <paths>",
            'git commit -m "<type(scope): summary>"',
            "git push",
            "gh pr create",
        ]
    return {
        "require_clean_git": require_clean_git,
        "status_available": status_result.returncode == 0,
        "status_short": status_short,
        "guidance": guidance,
        "legacy_manual_only": ["gac"],
    }, checks


SWHE_LINE_RE = re.compile(
    r"\[S:(?P<s>[^\]|]+)\|W:(?P<w>[^\]|]+)\|H:(?P<h>[^\]|]+)\|E:(?P<e>[^\]]+)\]\s*(?P<note>.*)"
)


def _swhe_entries_by_evidence(surface_texts: Mapping[str, str]) -> dict[str, list[dict[str, str]]]:
    entries: dict[str, list[dict[str, str]]] = {}
    for surface, text in surface_texts.items():
        for line in text.splitlines():
            match = SWHE_LINE_RE.search(line)
            if not match:
                continue
            evidence = match.group("e")
            entries.setdefault(evidence, []).append(
                {
                    "surface": surface,
                    "handler": match.group("h"),
                    "note": match.group("note").strip(),
                }
            )
    return entries


def _suggested_plan_step_for_evidence(
    evidence: str,
    *,
    implementation_tokens: Sequence[str],
    verification_tokens: Sequence[str],
    strict_verify_rel: str,
) -> str | None:
    if evidence == strict_verify_rel or evidence in verification_tokens:
        return "plan-step-verify"
    if evidence in implementation_tokens:
        return "plan-step-implement"
    return None


def _build_closeout_repair_guidance(
    *,
    surface_texts: Mapping[str, str],
    evidence_matrix: Mapping[str, Mapping[str, bool]],
    implementation_tokens: Sequence[str],
    verification_tokens: Sequence[str],
    strict_verify_rel: str,
    pending_tracking: Mapping[str, Any],
    target_root: Path,
    checks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    entries_by_evidence = _swhe_entries_by_evidence(surface_texts)
    repair_items: list[dict[str, Any]] = []
    for evidence, surfaces in evidence_matrix.items():
        present_entries = entries_by_evidence.get(evidence, [])
        inferred = present_entries[0] if present_entries else {}
        handler = inferred.get("handler")
        note = inferred.get("note")
        suggested_plan_step = _suggested_plan_step_for_evidence(
            evidence,
            implementation_tokens=implementation_tokens,
            verification_tokens=verification_tokens,
            strict_verify_rel=strict_verify_rel,
        )
        suggested_event_class = _infer_log_event_class(
            plan_step=suggested_plan_step,
            handler=handler or "",
            evidence=evidence,
        )
        for surface, present in surfaces.items():
            if present:
                continue
            item: dict[str, Any] = {
                "kind": "missing_evidence_reference",
                "surface": surface,
                "evidence": evidence,
                "suggested_event_class": suggested_event_class,
                "suggested_plan_step": suggested_plan_step,
                "source_surface": inferred.get("surface"),
                "handler": handler,
                "note": note,
            }
            if handler and note:
                command_parts = [
                    "aegis",
                    "log",
                    "--handler",
                    _quote_cli(handler),
                    "--evidence",
                    _quote_cli(evidence),
                    "--note",
                    _quote_cli(note),
                ]
                if surface in AEGIS_LOG_SURFACES:
                    command_parts.extend(["--surface", _quote_cli(surface)])
                elif surface == "plan" and suggested_plan_step:
                    command_parts.extend(
                        [
                            "--plan-step",
                            _quote_cli(suggested_plan_step),
                            "--plan-status",
                            "completed",
                        ]
                    )
                item["command"] = " ".join(command_parts)
            else:
                command_template = (
                    "aegis log --handler <handler> --evidence "
                    f'{_quote_cli(evidence)} --note "<past-tense note>"'
                )
                if surface in AEGIS_LOG_SURFACES:
                    command_template = f"{command_template} --surface {_quote_cli(surface)}"
                elif surface == "plan" and suggested_plan_step:
                    command_template = (
                        f"{command_template} --plan-step {_quote_cli(suggested_plan_step)} "
                        "--plan-status completed"
                    )
                item["command_template"] = command_template
            repair_items.append(item)

    if not pending_tracking.get("delivery_allowed"):
        required_events = [
            event
            for event in _pending_tracking_events(target_root)
            if str(event.get("mode") or "").strip().lower() == "strict"
        ]
        for event in required_events[:AEGIS_PENDING_TRACKING_SAMPLE_LIMIT]:
            event_id = str(event.get("id") or "")
            repair_items.append(
                {
                    "kind": "pending_tracking_event",
                    "pending_event_id": event_id,
                    "handler": event.get("handler"),
                    "evidence": event.get("evidence"),
                    "command_template": (
                        "aegis log --pending-id "
                        f'{_quote_cli(event_id)} --note "<past-tense note>" '
                        "--plan-step <plan-step-id> --plan-status completed"
                    ),
                }
            )
        if pending_tracking.get("untrusted_unresolved"):
            repair_items.append(
                {
                    "kind": "pending_tracking_manual_review",
                    "classification": pending_tracking.get("classification"),
                    "artifact": AEGIS_PENDING_TRACKING_REL,
                    "command": "aegis doctor --target-dir . --all --json",
                    "reason": (
                        "Aegis cannot safely infer a mutation or deletion for malformed "
                        "or unknown-provenance pending evidence."
                    ),
                }
            )

    failing_gate_ids = [
        str(check.get("gate_id"))
        for check in checks
        if check.get("required") and check.get("status") == "fail"
    ]
    return {
        "summary": {
            "items": len(repair_items),
            "failing_required_gates": failing_gate_ids,
        },
        "items": repair_items,
    }


def _handoff_repairable_closeout_failure(gate_ids: Sequence[str]) -> bool:
    """Return true when deterministic handoff repair is the right next action."""

    if not gate_ids:
        return False
    return all(
        gate_id.startswith("closeout.handoff.") or gate_id == "closeout.evidence.handoff"
        for gate_id in gate_ids
    )


def _closeout_failed_required_gate_ids(report: Mapping[str, Any]) -> list[str]:
    return [
        str(check.get("gate_id") or check.get("id") or "unknown")
        for check in report.get("checks", [])
        if isinstance(check, Mapping) and check.get("required") and check.get("status") == "fail"
    ]


def format_closeout_summary(report: Mapping[str, Any]) -> str:
    """Render a concise human closeout summary while preserving JSON reports for automation."""

    dry_run = bool(report.get("dry_run"))
    label = "Aegis closeout readiness" if dry_run else "Aegis closeout"
    status = str(report.get("status") or "unknown").upper()
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    pending = (
        report.get("pending_tracking")
        if isinstance(report.get("pending_tracking"), Mapping)
        else {}
    )
    pending_counts = pending.get("counts") if isinstance(pending.get("counts"), Mapping) else {}
    failed_gates = _closeout_failed_required_gate_ids(report)
    next_action = (
        report.get("next_action") if isinstance(report.get("next_action"), Mapping) else {}
    )
    repair_guidance = (
        report.get("repair_guidance") if isinstance(report.get("repair_guidance"), Mapping) else {}
    )
    repair_items = (
        repair_guidance.get("items") if isinstance(repair_guidance.get("items"), list) else []
    )
    first_repair = repair_items[0] if repair_items and isinstance(repair_items[0], Mapping) else {}
    first_repair_command = str(
        first_repair.get("command") or first_repair.get("command_template") or ""
    ).strip()
    report_written = bool(report.get("report_written"))
    closeout_report_state = "written" if report_written else "not written by this run"
    lines = [
        f"{label}: {status}",
        f"mode: {'dry-run' if dry_run else 'final'}",
        f"failed_required: {summary.get('failed_required', 0)}",
        f"warnings: {summary.get('warnings', 0)}",
        (
            "pending_tracking: "
            f"{pending_counts.get('total', 0)} "
            f"({pending.get('classification', 'unknown')})"
        ),
        f"closeout_report: {AEGIS_CLOSEOUT_REPORT_REL} ({closeout_report_state})",
    ]
    if failed_gates:
        lines.append("failed_gates:")
        lines.extend(f"- {gate}" for gate in failed_gates[:10])
        if len(failed_gates) > 10:
            lines.append(f"- ... {len(failed_gates) - 10} more")
    if first_repair_command:
        lines.append(f"repair: {first_repair_command}")
    suggested_cli = str(next_action.get("suggested_cli") or "").strip()
    if suggested_cli:
        lines.append(f"next: {suggested_cli}")
    lines.append("json: rerun with --all --json for the full structured report")
    return "\n".join(lines) + "\n"


def repair_handoff(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Repair Aegis-owned semantic HANDOFF.md sections without final closeout side effects."""

    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve()
    checked_at = _iso_now()
    current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    if not isinstance(current_work, dict):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "failed",
            "dry_run": dry_run,
            "report_written": False,
            "state_updated": False,
            "checked_at": checked_at,
            "target_root": str(target_root),
            "reason": f"{AEGIS_CURRENT_WORK_REL} missing or invalid; run aegis kickoff first",
            "next_action": _workflow_next_action(
                "kickoff_before_handoff_repair",
                "Aegis handoff repair requires active current work state.",
                suggested_cli='./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title "<title>"',
                suggested_mcp_tool="aegis.kickoff",
            ),
        }

    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    plan_rel = str(paths.get("plan") or "")
    work_rel = str(paths.get("work_tracking") or "")
    plan_path = target_root / plan_rel if plan_rel else target_root / "plans" / "current"
    work_path = (
        target_root / work_rel
        if work_rel
        else target_root / "docs" / "ai" / "work-tracking" / "active"
    )
    handoff_path = work_path / "HANDOFF.md"
    if not handoff_path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "failed",
            "dry_run": dry_run,
            "report_written": False,
            "state_updated": False,
            "checked_at": checked_at,
            "target_root": str(target_root),
            "current_work": current_work,
            "handoff": {
                "path": _repo_path(handoff_path, target_root),
                "exists": False,
                "updated": False,
                "would_update": False,
            },
            "reason": "HANDOFF.md is missing from the active work-tracking folder.",
            "next_action": _workflow_next_action(
                "repair_missing_work_tracking_before_handoff_repair",
                "Aegis handoff repair can only update an existing active HANDOFF.md.",
                suggested_cli='./.aegis/bin/aegis kickoff --target-dir . --task <id> --slug <slug> --title "<title>"',
            ),
        }

    before = closeout(
        target_root,
        source_root=source,
        update_handoff=True,
        dry_run=True,
    )
    plan_rows = _parse_plan_rows(plan_path)
    implementation_tokens = [
        token
        for token in _split_evidence_tokens(
            str(plan_rows.get("plan-step-implement", {}).get("evidence") or "")
        )
        if _is_closeout_required_evidence(token)
    ]
    verification_tokens = [
        token
        for token in _split_evidence_tokens(
            str(plan_rows.get("plan-step-verify", {}).get("evidence") or "")
        )
        if _is_closeout_required_evidence(token)
    ]
    strict_verify_rel = _normalize_evidence(target_root, AEGIS_VERIFY_REPORT_REL)
    before_text = _read_text_or_empty(handoff_path)
    repaired_text = _repair_closeout_handoff_text(
        before_text,
        current_work=current_work,
        implementation_tokens=implementation_tokens,
        verification_tokens=verification_tokens,
        strict_verify_rel=strict_verify_rel,
        strict_verify_report_green=_strict_verify_report_is_green(target_root),
    )
    changed = repaired_text != before_text
    after: dict[str, Any] | None = None
    if not dry_run and changed:
        handoff_path.write_text(repaired_text, encoding="utf-8")
        after = closeout(
            target_root,
            source_root=source,
            update_handoff=True,
            dry_run=True,
        )
    elif not dry_run:
        after = before

    failing_before = [
        str(check.get("gate_id"))
        for check in before.get("checks", [])
        if check.get("required") and check.get("status") == "fail"
    ]
    failing_after = [
        str(check.get("gate_id"))
        for check in (after or {}).get("checks", [])
        if check.get("required") and check.get("status") == "fail"
    ]
    status_value = "planned" if dry_run else "repaired"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status_value,
        "dry_run": dry_run,
        "report_written": False,
        "state_updated": False,
        "checked_at": checked_at,
        "target_root": str(target_root),
        "current_work": current_work,
        "handoff": {
            "path": _repo_path(handoff_path, target_root),
            "exists": True,
            "updated": changed and not dry_run,
            "would_update": changed and dry_run,
            "changed": changed,
            "preserved_progress_log": "## Progress Log" in before_text,
            "sections": [
                "Current State",
                "What Was Done",
                "Implementation Evidence",
                "Verification Evidence",
                "Strict Verification Evidence",
                "Current Issues/Blockers",
                "Next Steps",
                "Important Context",
            ],
        },
        "evidence": {
            "implementation": implementation_tokens,
            "verification": verification_tokens,
            "strict_verify": strict_verify_rel,
        },
        "closeout_ready_before": {
            "status": before.get("status"),
            "failed_required_gates": failing_before,
            "repair_items": before.get("repair_guidance", {}).get("summary", {}).get("items"),
        },
        "closeout_ready_after": (
            {
                "status": after.get("status"),
                "failed_required_gates": failing_after,
                "repair_items": after.get("repair_guidance", {}).get("summary", {}).get("items"),
            }
            if after is not None
            else None
        ),
        "preview": repaired_text if dry_run else None,
        "next_action": (
            _workflow_next_action(
                "apply_handoff_repair",
                "Aegis can repair the active handoff without writing closeout reports or current-work state.",
                suggested_cli="./.aegis/bin/aegis handoff repair --target-dir .",
                suggested_mcp_tool="aegis.handoff_repair",
                suggested_mcp_arguments={"target_dir": ".", "apply": True},
            )
            if dry_run and changed
            else (
                _workflow_next_action(
                    "rerun_closeout_ready",
                    "Handoff repair applied. Re-run closeout_ready; if it passes, run final closeout.",
                    suggested_cli="./.aegis/bin/aegis closeout --target-dir . --dry-run --update-handoff",
                    suggested_mcp_tool="aegis.closeout_ready",
                    suggested_mcp_arguments={"target_dir": ".", "update_handoff": True},
                    details={
                        "closeout_ready_status": (
                            after.get("status") if after else before.get("status")
                        )
                    },
                )
                if not dry_run
                else _workflow_next_action(
                    "no_handoff_repair_needed",
                    "The active handoff already matches the deterministic repair rendering.",
                    suggested_cli="./.aegis/bin/aegis closeout --target-dir . --dry-run --update-handoff",
                )
            )
        ),
    }


def closeout(
    target_dir: str | Path,
    *,
    source_root: str | Path,
    update_handoff: bool = False,
    require_clean_git: bool = False,
    include_git_guidance: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Validate that Aegis workflow state is complete enough to report task completion."""

    target_root = _resolve_target_root(target_dir)
    source = Path(source_root).resolve()
    checked_at = _iso_now()
    checks: list[dict[str, Any]] = []

    current_work = _read_json(target_root / AEGIS_CURRENT_WORK_REL)
    current_work_status = (
        str(current_work.get("status") or "").strip() if isinstance(current_work, Mapping) else ""
    )
    current_work_ok = isinstance(current_work, dict) and (
        current_work_status == "in-progress"
        or (current_work_status == "completed" and bool(current_work.get("closeout_passed_at")))
    )
    current_work_message = (
        "current work payload is active"
        if current_work_status == "in-progress"
        else (
            "current work payload is completed"
            if current_work_ok
            else f"{AEGIS_CURRENT_WORK_REL} missing, invalid, or not active/completed"
        )
    )
    checks.append(
        _closeout_check(
            "closeout.current_work",
            passed=current_work_ok,
            message=current_work_message,
            details={"path": AEGIS_CURRENT_WORK_REL, "status": current_work_status},
        )
    )
    if not isinstance(current_work, dict):
        current_work = {}

    paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
    session_rel = str(paths.get("session") or "")
    plan_rel = str(paths.get("plan") or "")
    work_rel = str(paths.get("work_tracking") or "")
    session_path = (
        target_root / session_rel if session_rel else target_root / "sessions" / "current"
    )
    plan_path = target_root / plan_rel if plan_rel else target_root / "plans" / "current"
    work_path = (
        target_root / work_rel
        if work_rel
        else target_root / "docs" / "ai" / "work-tracking" / "active"
    )
    tracker_path = work_path / "TRACKER.md"
    implementation_path = work_path / "IMPLEMENTATION.md"
    changelog_path = work_path / "CHANGELOG.md"
    handoff_path = work_path / "HANDOFF.md"

    readiness = _closeout_readiness(target_root, current_work=current_work)
    checks.append(
        _closeout_check(
            "closeout.readiness",
            passed=readiness.get("status") == "passed",
            message=(
                "readiness is READY"
                if readiness.get("status") == "passed"
                else "readiness is not READY"
            ),
            details=readiness,
        )
    )

    pending_tracking = _classify_pending_tracking(target_root)
    checks.append(
        _closeout_check(
            "closeout.pending_tracking",
            passed=bool(pending_tracking.get("delivery_allowed")),
            message=str(pending_tracking.get("reason") or "pending tracking state unavailable"),
            details=pending_tracking,
        )
    )
    degraded_events = _degraded_events(target_root)
    unacknowledged_degraded = [
        event
        for event in degraded_events
        if not event.get("acknowledged_at") and not event.get("resolved_at")
    ]
    checks.append(
        _closeout_check(
            "closeout.degraded_events_acknowledged",
            passed=not unacknowledged_degraded,
            message=(
                "degraded gate events are acknowledged or resolved"
                if not unacknowledged_degraded
                else "unacknowledged degraded gate events block closeout"
            ),
            details={
                "path": AEGIS_DEGRADED_EVENTS_REL,
                "total": len(degraded_events),
                "unacknowledged": unacknowledged_degraded,
            },
        )
    )

    strict_verify = verify(target_root, source_root=source, strict=True, dry_run=dry_run)
    checks.append(
        _closeout_check(
            "closeout.strict_verify",
            passed=strict_verify.get("status") == "passed",
            message=(
                "strict verification passed"
                if strict_verify.get("status") == "passed"
                else "strict verification failed"
            ),
            details={
                "report": AEGIS_VERIFY_REPORT_REL,
                "summary": strict_verify.get("summary", {}),
            },
        )
    )

    plan_rows = _parse_plan_rows(plan_path)
    tracker_steps = _parse_tracker_plan_steps(tracker_path)
    required_steps = ("plan-step-scope", "plan-step-implement", "plan-step-verify")
    for step in required_steps:
        row = plan_rows.get(step)
        plan_completed = isinstance(row, Mapping) and row.get("status") in {"completed", "done"}
        checks.append(
            _closeout_check(
                f"closeout.plan.{step.removeprefix('plan-step-')}",
                passed=plan_completed,
                message=(
                    f"{step} completed in current plan"
                    if plan_completed
                    else f"{step} missing or not completed in current plan"
                ),
                category="plan",
                details={"row": row},
            )
        )
        tracker_completed = tracker_steps.get(step) == "completed"
        checks.append(
            _closeout_check(
                f"closeout.tracker.{step.removeprefix('plan-step-')}",
                passed=tracker_completed,
                message=(
                    f"{step} completed in tracker"
                    if tracker_completed
                    else f"{step} missing or unchecked in tracker"
                ),
                category="tracker",
                details={"tracker_status": tracker_steps.get(step)},
            )
        )

    ordered = all(step in plan_rows for step in required_steps) and [
        int(plan_rows[step]["index"]) for step in required_steps
    ] == sorted(int(plan_rows[step]["index"]) for step in required_steps)
    checks.append(
        _closeout_check(
            "closeout.plan.order",
            passed=ordered,
            message=(
                "required plan steps are in scope -> implement -> verify order"
                if ordered
                else "required plan steps are missing or out of order"
            ),
            category="plan",
            details={"order": [step for step in plan_rows if step in required_steps]},
        )
    )

    implementation_tokens = [
        token
        for token in _split_evidence_tokens(
            str(plan_rows.get("plan-step-implement", {}).get("evidence") or "")
        )
        if _is_closeout_required_evidence(token)
    ]
    verification_tokens = [
        token
        for token in _split_evidence_tokens(
            str(plan_rows.get("plan-step-verify", {}).get("evidence") or "")
        )
        if _is_closeout_required_evidence(token)
    ]
    strict_verify_rel = _normalize_evidence(target_root, AEGIS_VERIFY_REPORT_REL)
    required_evidence = tuple(
        dict.fromkeys([*implementation_tokens, *verification_tokens, strict_verify_rel])
    )

    surface_paths = {
        "session": session_path,
        "tracker": tracker_path,
        "implementation": implementation_path,
        "changelog": changelog_path,
        "handoff": handoff_path,
        "plan": plan_path,
    }
    surface_texts = {surface: _read_text_or_empty(path) for surface, path in surface_paths.items()}
    evidence_matrix = {
        token: {
            surface: _surface_contains_evidence(text, token)
            for surface, text in surface_texts.items()
        }
        for token in required_evidence
    }
    strict_verify_report_green = _strict_verify_report_is_green(target_root)
    populate_report: dict[str, Any] = {
        "dry_run": dry_run,
        "strict_verify_report_green": strict_verify_report_green,
        "eligible_tokens": [],
        "updated_surfaces": [],
        "would_update_surfaces": [],
        "skipped": [],
        "enabled": False,
        "reason": (
            "strict verification must pass and pending tracking must be delivery-safe "
            "before population"
        ),
    }
    if pending_tracking.get("delivery_allowed") and strict_verify.get("status") == "passed":
        populate_report = _populate_closeout_surfaces(
            target_root,
            current_work=current_work,
            surface_paths=surface_paths,
            surface_texts=surface_texts,
            evidence_matrix=evidence_matrix,
            implementation_tokens=implementation_tokens,
            verification_tokens=verification_tokens,
            strict_verify_rel=strict_verify_rel,
            strict_verify_report_green=strict_verify_report_green,
            dry_run=dry_run,
        )
        populate_report["enabled"] = True
        if not dry_run:
            evidence_matrix = {
                token: {
                    surface: _surface_contains_evidence(surface_texts[surface], token)
                    for surface in surface_texts
                }
                for token in required_evidence
            }
    for surface, text in surface_texts.items():
        missing = [
            token for token in required_evidence if not _surface_contains_evidence(text, token)
        ]
        checks.append(
            _closeout_check(
                f"closeout.evidence.{surface}",
                passed=not missing,
                message=(
                    f"{surface} references all required evidence"
                    if not missing
                    else f"{surface} is missing required evidence"
                ),
                category="evidence",
                details={"missing": missing},
            )
        )

    checks.extend(
        _closeout_handoff_checks(
            surface_texts["handoff"],
            implementation_tokens=implementation_tokens,
            verification_tokens=verification_tokens,
            strict_verify_rel=strict_verify_rel,
        )
    )

    integrations = (
        current_work.get("integrations")
        if isinstance(current_work.get("integrations"), Mapping)
        else {}
    )
    integration_report: dict[str, Any] = {}
    for name, rel_path in (("taskmaster", ".taskmaster"), ("serena", ".serena")):
        integration = integrations.get(name) if isinstance(integrations, Mapping) else {}
        required = isinstance(integration, Mapping) and integration.get("required") is True
        detected = (target_root / rel_path).exists()
        integration_report[name] = {
            "detected": detected,
            "required": required,
            "status": (
                "present" if detected else "optional_absent" if not required else "required_missing"
            ),
        }

    git_report, git_checks = _closeout_git_report(
        target_root,
        require_clean_git=require_clean_git,
        include_guidance=include_git_guidance,
    )
    checks.extend(git_checks)

    failed_required = [
        check for check in checks if check.get("required") and check.get("status") == "fail"
    ]
    failed_required_gate_ids = [str(check.get("gate_id")) for check in failed_required]
    status_value = "failed" if failed_required else "passed"
    repair_guidance = _build_closeout_repair_guidance(
        surface_texts=surface_texts,
        evidence_matrix=evidence_matrix,
        implementation_tokens=implementation_tokens,
        verification_tokens=verification_tokens,
        strict_verify_rel=strict_verify_rel,
        pending_tracking=pending_tracking,
        target_root=target_root,
        checks=checks,
    )
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status_value,
        "dry_run": dry_run,
        "report_written": False,
        "state_updated": False,
        "checked_at": checked_at,
        "target_root": str(target_root),
        "current_work": current_work,
        "readiness": readiness,
        "strict_verify": {
            "status": strict_verify.get("status"),
            "report": AEGIS_VERIFY_REPORT_REL,
            "summary": strict_verify.get("summary", {}),
        },
        "plan": {
            "path": _repo_path(plan_path, target_root),
            "required_steps": {step: plan_rows.get(step) for step in required_steps},
            "tracker_steps": {step: tracker_steps.get(step) for step in required_steps},
        },
        "pending_tracking": pending_tracking,
        "degraded_events": {
            "path": AEGIS_DEGRADED_EVENTS_REL,
            "events": degraded_events,
            "unacknowledged": unacknowledged_degraded,
        },
        "evidence_matrix": evidence_matrix,
        "handoff": {
            "path": _repo_path(handoff_path, target_root),
            "updated": bool(populate_report.get("handoff", {}).get("updated")),
            "would_update": bool(populate_report.get("handoff", {}).get("would_update")),
            "update_handoff_requested": update_handoff,
        },
        "populate": populate_report,
        "integrations": integration_report,
        "git": git_report,
        "repair_guidance": repair_guidance,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "failed_required": len(failed_required),
            "warnings": 0,
        },
        "next_action": (
            _workflow_next_action(
                "run_closeout_to_write_report",
                "Closeout readiness passed. Run non-dry-run closeout to write the closeout report before reporting the task complete.",
                suggested_cli="./.aegis/bin/aegis closeout --target-dir . --update-handoff",
                suggested_mcp_tool="aegis.closeout",
                suggested_mcp_arguments={
                    "target_dir": ".",
                    "acknowledge_report_write": True,
                    "update_handoff": True,
                },
                details={"dry_run": True, "closeout_report": AEGIS_CLOSEOUT_REPORT_REL},
            )
            if status_value == "passed"
            and dry_run
            and not (
                current_work_status == "completed" and bool(current_work.get("closeout_passed_at"))
            )
            else (
                _workflow_next_action(
                    "run_post_closeout_doctor",
                    "Closeout passed and wrote the report. Run read-only doctor once before the final user report.",
                    suggested_cli="./.aegis/bin/aegis doctor --target-dir .",
                    suggested_mcp_tool="aegis.doctor",
                    suggested_mcp_arguments={"target_dir": "."},
                    details={"closeout_report": AEGIS_CLOSEOUT_REPORT_REL},
                )
                if status_value == "passed" and not dry_run
                else (
                    _workflow_next_action(
                        "task_complete",
                        "Closeout passed. It is now valid to report the task complete and proceed with normal git/GitHub commands.",
                        suggested_cli="git status --short",
                        details={"closeout_report": AEGIS_CLOSEOUT_REPORT_REL},
                    )
                    if status_value == "passed"
                    else (
                        _workflow_next_action(
                            "apply_handoff_repair_before_retry",
                            "Closeout failed only on handoff gates. Run deterministic handoff repair, then re-run closeout readiness.",
                            suggested_cli="./.aegis/bin/aegis handoff repair --target-dir .",
                            suggested_mcp_tool="aegis.handoff_repair",
                            suggested_mcp_arguments={
                                "target_dir": ".",
                                "apply": True,
                            },
                            details={
                                "failed_required_gates": failed_required_gate_ids,
                                "repair_items": repair_guidance["summary"]["items"],
                                "after_repair": "./.aegis/bin/aegis closeout --target-dir . --dry-run --update-handoff",
                            },
                        )
                        if _handoff_repairable_closeout_failure(failed_required_gate_ids)
                        else _workflow_next_action(
                            "repair_closeout_gates_before_retry",
                            "Closeout failed. Do not report the task complete; apply repair_guidance and retry closeout.",
                            suggested_cli=(
                                "./.aegis/bin/aegis closeout --target-dir . --dry-run --update-handoff"
                                if dry_run
                                else "./.aegis/bin/aegis closeout --target-dir . --update-handoff"
                            ),
                            suggested_mcp_tool=(
                                "aegis.closeout_ready" if dry_run else "aegis.closeout"
                            ),
                            suggested_mcp_arguments={
                                "target_dir": ".",
                                "update_handoff": True,
                                **({} if dry_run else {"acknowledge_report_write": True}),
                            },
                            details={
                                "failed_required_gates": failed_required_gate_ids,
                                "repair_items": repair_guidance["summary"]["items"],
                            },
                        )
                    )
                )
            )
        ),
    }
    if status_value == "passed" and not dry_run:
        report["closed_at"] = _iso_now()

    if status_value == "passed" and current_work and not dry_run:
        current_work["updated_at"] = _iso_now()
        current_work["closeout_passed_at"] = report["closed_at"]
        current_work["closeout_report"] = AEGIS_CLOSEOUT_REPORT_REL
        current_work["status"] = "completed"
        task_payload = current_work.get("task")
        if isinstance(task_payload, dict):
            task_payload["status"] = "completed"
        archived_work_tracking = _archive_current_completed_work_tracking(
            target_root,
            current_work,
        )
        if archived_work_tracking is not None:
            report["archived_work_tracking"] = dict(archived_work_tracking)
        _write_text(target_root, AEGIS_CURRENT_WORK_REL, _dump_json(current_work))
        report["state_updated"] = True

    if not dry_run:
        report["report_written"] = True
        reports_dir = target_root / AEGIS_REPORTS_REL
        reports_dir.mkdir(parents=True, exist_ok=True)
        (target_root / AEGIS_CLOSEOUT_REPORT_REL).write_text(_dump_json(report), encoding="utf-8")

    return report


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_cert_command(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    expected_returncodes: Sequence[int] = (0,),
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = result.stdout + result.stderr
    payload = {
        "command": list(command),
        "cwd": cwd.as_posix(),
        "returncode": result.returncode,
        "status": "passed" if result.returncode in expected_returncodes else "failed",
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
        "output_tail": output[-4000:],
        "expected_returncodes": list(expected_returncodes),
    }
    return result, payload


def _git_provenance(source_root: Path) -> dict[str, Any]:
    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", source_root.as_posix(), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    commit = run_git("rev-parse", "HEAD")
    status = run_git("status", "--short")
    branch = run_git("branch", "--show-current")
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
        "status_short": status.stdout.splitlines() if status.returncode == 0 else [],
        "available": commit.returncode == 0,
    }


def _artifact_kind(path: Path) -> str:
    name = path.name
    if name.endswith(".whl"):
        return "wheel"
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "sdist"
    return "unknown"


def _artifact_members(path: Path) -> list[str]:
    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            return sorted(archive.namelist())
    if path.name.endswith(".tar.gz") or path.name.endswith(".tgz"):
        with tarfile.open(path, "r:gz") as archive:
            return sorted(member.name for member in archive.getmembers())
    return []


def _required_artifact_suffixes(kind: str) -> tuple[str, ...]:
    shared = (
        "aegis_foundation/cli.py",
        "aegis_foundation/gate/readiness.py",
        "aegis_foundation/gate/hooks/entrypoint.py",
        "aegis_foundation/gate/hooks/pretool.py",
        "aegis_mcp/server.py",
        "aegis_foundation/assets/.claude/scripts/pretooluse-gate.sh",
        "aegis_foundation/assets/.claude/scripts/posttooluse-tracking.sh",
        "aegis_foundation/assets/.claude/scripts/tracking-stop-gate.sh",
        "aegis_foundation/assets/scripts/_aegis_installer.py",
        "aegis_foundation/assets/scripts/codex-task",
        "aegis_foundation/assets/schemas/aegis/foundation-manifest.schema.json",
        "aegis_foundation/assets/templates/aegis/workflow/session.md",
        "aegis_foundation/assets/templates/aegis/workflow/tracker.md",
    )
    if kind == "wheel":
        return (*shared, "entry_points.txt")
    if kind == "sdist":
        return (*shared, "pyproject.toml")
    return shared


def _inspect_release_artifact(path: Path) -> dict[str, Any]:
    kind = _artifact_kind(path)
    members = _artifact_members(path)
    required = _required_artifact_suffixes(kind)
    missing = [
        suffix for suffix in required if not any(member.endswith(suffix) for member in members)
    ]
    return {
        "path": path.as_posix(),
        "name": path.name,
        "kind": kind,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "member_count": len(members),
        "required_suffixes": list(required),
        "missing_required_suffixes": missing,
        "status": "passed" if kind != "unknown" and not missing else "failed",
    }


def _certify_clean_cli_smoke(wheel: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aegis-release-cert-") as tmp:
        tmp_root = Path(tmp)
        venv_dir = tmp_root / "venv"
        target = tmp_root / "target"
        target.mkdir()
        steps: list[dict[str, Any]] = []

        venv_result, step = _run_cert_command(
            [sys.executable, "-m", "venv", venv_dir.as_posix()],
            cwd=tmp_root,
        )
        step["name"] = "create_venv"
        steps.append(step)
        if venv_result.returncode != 0:
            return {"status": "failed", "steps": steps}

        python = venv_dir / "bin" / "python"
        install_result, step = _run_cert_command(
            [python.as_posix(), "-m", "pip", "install", wheel.as_posix()],
            cwd=tmp_root,
        )
        step["name"] = "install_wheel"
        steps.append(step)
        if install_result.returncode != 0:
            return {"status": "failed", "steps": steps}

        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("AEGIS_SOURCE_ROOT", None)
        aegis_bin = venv_dir / "bin" / "aegis"

        command_steps: list[
            tuple[str, list[str], Path, Sequence[int], str | None, Mapping[str, str] | None]
        ] = [
            ("aegis_version", [aegis_bin.as_posix(), "--version"], target, (0,), None, env),
            ("git_init", ["git", "init", "-b", "main"], target, (0,), None, env),
            (
                "aegis_inspect",
                [aegis_bin.as_posix(), "inspect", "--target-dir", "."],
                target,
                (0,),
                None,
                env,
            ),
            (
                "aegis_plan_install",
                [
                    aegis_bin.as_posix(),
                    "plan-install",
                    "--target-dir",
                    ".",
                    "--primary-agent",
                    "claude",
                    "--agent",
                    "claude",
                ],
                target,
                (0,),
                None,
                env,
            ),
            (
                "aegis_install",
                [
                    aegis_bin.as_posix(),
                    "install",
                    "--target-dir",
                    ".",
                    "--primary-agent",
                    "claude",
                    "--agent",
                    "claude",
                    "--apply",
                ],
                target,
                (0,),
                None,
                env,
            ),
            (
                "aegis_status",
                [aegis_bin.as_posix(), "status", "--target-dir", "."],
                target,
                (0,),
                None,
                env,
            ),
            (
                "aegis_kickoff",
                [
                    aegis_bin.as_posix(),
                    "kickoff",
                    "--target-dir",
                    ".",
                    "--task",
                    "42",
                    "--slug",
                    "release-cert",
                    "--title",
                    "Release Certification",
                ],
                target,
                (0,),
                None,
                env,
            ),
            (
                "readiness_quick",
                ["./.aegis/bin/aegis", "gate", "readiness", "--quick", "--target-dir", "."],
                target,
                (0,),
                None,
                env,
            ),
        ]
        for name, command, cwd, expected, input_text, command_env in command_steps:
            result, step = _run_cert_command(
                command,
                cwd=cwd,
                env=command_env,
                input_text=input_text,
                expected_returncodes=expected,
            )
            step["name"] = name
            steps.append(step)
            if result.returncode not in expected:
                return {"status": "failed", "steps": steps}

        current_work = _read_json(target / AEGIS_CURRENT_WORK_REL)
        if current_work is None:
            steps.append(
                {
                    "name": "read_current_work",
                    "status": "failed",
                    "message": f"{AEGIS_CURRENT_WORK_REL} missing after kickoff",
                }
            )
            return {"status": "failed", "steps": steps}
        paths = current_work.get("paths") if isinstance(current_work.get("paths"), Mapping) else {}
        reports_rel = str(paths.get("reports") or "").strip()
        if not reports_rel:
            steps.append(
                {
                    "name": "read_current_work_reports",
                    "status": "failed",
                    "message": "current work reports path missing",
                }
            )
            return {"status": "failed", "steps": steps}
        evidence_rel = f"{reports_rel}/release-certification-evidence.txt"
        claude_env = {**env, "CLAUDE_PROJECT_DIR": target.as_posix()}
        tracking_steps: list[
            tuple[str, list[str], Sequence[int], str | None, Mapping[str, str]]
        ] = [
            (
                "pretooluse_allowed_evidence_write",
                ["bash", ".claude/scripts/pretooluse-gate.sh"],
                (0,),
                json.dumps({"tool_name": "Write", "tool_input": {"file_path": evidence_rel}}),
                claude_env,
            ),
            (
                "posttooluse_pending_tracking",
                ["bash", ".claude/scripts/posttooluse-tracking.sh"],
                (0,),
                json.dumps({"tool_name": "Write", "tool_input": {"file_path": evidence_rel}}),
                claude_env,
            ),
            (
                "pretooluse_blocks_before_log",
                ["bash", ".claude/scripts/pretooluse-gate.sh"],
                (2,),
                json.dumps(
                    {
                        "tool_name": "Write",
                        "tool_input": {"file_path": f"{reports_rel}/blocked-before-log.txt"},
                    }
                ),
                claude_env,
            ),
            (
                "aegis_log_tracking",
                [
                    aegis_bin.as_posix(),
                    "log",
                    "--target-dir",
                    ".",
                    "--handler",
                    "certification:write",
                    "--evidence",
                    evidence_rel,
                    "--note",
                    "Recorded release certification smoke evidence",
                ],
                (0,),
                None,
                env,
            ),
            (
                "aegis_verify_strict",
                [aegis_bin.as_posix(), "verify", "--target-dir", ".", "--strict"],
                (0,),
                None,
                env,
            ),
            (
                "protected_path_refusal",
                ["bash", ".claude/scripts/pretooluse-gate.sh"],
                (2,),
                json.dumps(
                    {
                        "tool_name": "Bash",
                        "tool_input": {
                            "command": "printf blocked > templates/should-not-land.md",
                        },
                    }
                ),
                claude_env,
            ),
        ]
        evidence_path = target / evidence_rel
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        for name, command, expected, input_text, command_env in tracking_steps:
            if name == "posttooluse_pending_tracking":
                evidence_path.write_text("release certification smoke evidence\n", encoding="utf-8")
                steps.append(
                    {
                        "name": "write_evidence_file",
                        "status": "passed",
                        "path": evidence_rel,
                    }
                )
            result, step = _run_cert_command(
                command,
                cwd=target,
                env=command_env,
                input_text=input_text,
                expected_returncodes=expected,
            )
            step["name"] = name
            steps.append(step)
            if result.returncode not in expected:
                return {"status": "failed", "steps": steps}

        verification_report = target / AEGIS_VERIFY_REPORT_REL
        return {
            "status": "passed",
            "steps": steps,
            "strict_verification_report": (
                verification_report.read_text(encoding="utf-8")
                if verification_report.is_file()
                else None
            ),
        }


def _certify_mcp_server_config_smoke(wheel: Path) -> dict[str, Any]:
    uvx = shutil.which("uvx")
    if uvx is None:
        return {
            "status": "skipped",
            "reason": "uvx is not available for local wheel MCP server config smoke",
        }
    with tempfile.TemporaryDirectory(prefix="aegis-release-mcp-") as tmp:
        tmp_root = Path(tmp)
        target = tmp_root / "target"
        target.mkdir()
        result, step = _run_cert_command(
            [
                uvx,
                "--from",
                wheel.as_posix(),
                "aegis-mcp-server",
                "--default-target-dir",
                target.as_posix(),
                "--describe-config",
            ],
            cwd=target,
        )
        step["name"] = "mcp_describe_config_from_local_wheel"
        if result.returncode != 0:
            return {"status": "failed", "steps": [step]}
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "status": "failed",
                "steps": [step],
                "reason": "aegis-mcp-server --describe-config did not return JSON",
            }
        checks = [
            {
                "id": "asset_origin_package",
                "status": "pass" if payload.get("asset_origin") == "package" else "fail",
                "observed": payload.get("asset_origin"),
            },
            {
                "id": "distribution_name",
                "status": (
                    "pass" if payload.get("distribution_name") == "aegis-foundation" else "fail"
                ),
                "observed": payload.get("distribution_name"),
            },
            {
                "id": "default_target_dir",
                "status": (
                    "pass" if payload.get("default_target_dir") == target.as_posix() else "fail"
                ),
                "observed": payload.get("default_target_dir"),
            },
        ]
        failed = [check for check in checks if check["status"] != "pass"]
        return {
            "status": "failed" if failed else "passed",
            "steps": [step],
            "checks": checks,
            "failed_required": len(failed),
            "config": payload,
        }


def certify_release_candidate(
    source_dir: str | Path,
    *,
    dist_dir: str | Path,
    report_file: str | Path | None = None,
    build: bool = True,
    run_smoke: bool = True,
) -> dict[str, Any]:
    source_root = _resolve_target_root(source_dir)
    dist_path = Path(dist_dir).expanduser()
    if not dist_path.is_absolute():
        dist_path = source_root / dist_path
    dist_path.mkdir(parents=True, exist_ok=True)
    report_path = Path(report_file or AEGIS_RELEASE_CERT_REPORT_REL).expanduser()
    if not report_path.is_absolute():
        report_path = source_root / report_path

    build_payload: dict[str, Any]
    if build:
        uv = shutil.which("uv")
        command = (
            [uv, "build", "--sdist", "--wheel", "--out-dir", dist_path.as_posix()]
            if uv
            else [
                sys.executable,
                "-m",
                "build",
                "--sdist",
                "--wheel",
                "--outdir",
                dist_path.as_posix(),
            ]
        )
        build_result, build_payload = _run_cert_command(command, cwd=source_root)
    else:
        build_payload = {
            "status": "skipped",
            "command": None,
            "reason": "build disabled by caller",
        }

    artifact_paths = sorted(
        [
            *dist_path.glob("*.whl"),
            *dist_path.glob("*.tar.gz"),
            *dist_path.glob("*.tgz"),
        ]
    )
    artifacts = [_inspect_release_artifact(path) for path in artifact_paths]
    artifact_kinds = {artifact["kind"] for artifact in artifacts}
    missing_kinds = sorted({"wheel", "sdist"} - artifact_kinds)

    wheel_paths = [path for path in artifact_paths if _artifact_kind(path) == "wheel"]
    if run_smoke and wheel_paths:
        cli_smoke = _certify_clean_cli_smoke(wheel_paths[0])
        mcp_config_smoke = _certify_mcp_server_config_smoke(wheel_paths[0])
    elif run_smoke:
        cli_smoke = {
            "status": "failed",
            "reason": "no wheel artifact available for clean CLI smoke",
        }
        mcp_config_smoke = {
            "status": "failed",
            "reason": "no wheel artifact available for MCP server config smoke",
        }
    else:
        cli_smoke = {"status": "skipped", "reason": "clean CLI smoke disabled by caller"}
        mcp_config_smoke = {
            "status": "skipped",
            "reason": "MCP server config smoke disabled by caller",
        }

    failures: list[dict[str, Any]] = []
    if build_payload.get("status") == "failed":
        failures.append({"stage": "build", "message": "artifact build failed"})
    if missing_kinds:
        failures.append(
            {
                "stage": "artifacts",
                "message": "required artifact kind missing",
                "missing": missing_kinds,
            }
        )
    for artifact in artifacts:
        if artifact.get("status") == "failed":
            failures.append(
                {
                    "stage": "artifact_inspection",
                    "artifact": artifact.get("name"),
                    "missing": artifact.get("missing_required_suffixes"),
                }
            )
    if cli_smoke.get("status") == "failed":
        failures.append({"stage": "clean_cli_smoke", "message": "clean CLI smoke failed"})
    if mcp_config_smoke.get("status") == "failed":
        failures.append(
            {"stage": "mcp_server_config_smoke", "message": "MCP server config smoke failed"}
        )

    status_value = "failed" if failures else "passed"
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status_value,
        "generated_at": _iso_now(),
        "source_root": source_root.as_posix(),
        "dist_dir": dist_path.as_posix(),
        "report_file": report_path.as_posix(),
        "provenance": {
            "python": sys.version.split()[0],
            "git": _git_provenance(source_root),
            "foundation_version": FOUNDATION_VERSION,
            "installer_version": INSTALLER_VERSION,
            "schema_version": SCHEMA_VERSION,
        },
        "build": build_payload,
        "artifacts": artifacts,
        "smokes": {
            "clean_cli": cli_smoke,
            "mcp_server_config": mcp_config_smoke,
            "mcp_stdio": {
                "status": "covered_by_focused_pytest",
                "test": "tests/meta_workflow_guard/test_aegis_mcp_e2e_targets.py::test_local_wheel_mcp_real_target_project_smoke_when_enabled",
                "reason": "Full install/kickoff/log/verify/closeout MCP stdio artifact proof is intentionally exercised by the focused pytest target.",
            },
        },
        "failures": failures,
        "publishing_handoff": {
            "github_release_candidate_ready": status_value == "passed"
            and cli_smoke.get("status") == "passed",
            "pypi_ready": False,
            "notes": [
                "GitHub release-candidate artifacts remain the first recommended public channel.",
                "PyPI publication requires a separate explicit release task.",
            ],
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_dump_json(report), encoding="utf-8")
    return report


def list_profiles(*, source_root: str | Path) -> dict[str, Any]:
    source = Path(source_root).resolve()
    profile = profile_payload()
    _validate_with_schema(source, "profile.schema.json", profile)
    return {
        "schema_version": SCHEMA_VERSION,
        "profiles": [
            {
                "name": PROFILE_GENERIC,
                "default_primary_agent": "claude",
                "agent_selection_required": True,
                "supported_agents": ["claude", "codex"],
            }
        ],
    }


def explain_profile(profile: str, *, source_root: str | Path) -> dict[str, Any]:
    if profile != PROFILE_GENERIC:
        raise AegisError(f"Unsupported Aegis profile in V1: {profile}")
    payload = profile_payload()
    _validate_with_schema(Path(source_root).resolve(), "profile.schema.json", payload)
    return payload
