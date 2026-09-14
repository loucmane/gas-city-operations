"""Aegis hook gate: contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CODEX_APPLY_PATCH_TOOL = "apply_patch"


CLAUDE_PRETOOLUSE_MATCHER = "^(Edit|Write|MultiEdit|NotebookEdit|Bash|Agent|Task|mcp__.*)$"


CODEX_PRETOOLUSE_MATCHER = (
    "^(Bash|apply_patch|(?:collaboration(?:\\.|__))?"
    "(?:spawn_agent|assign_agent_task|followup_task|resume_agent)|mcp__.*)$"
)


FILE_MUTATION_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", CODEX_APPLY_PATCH_TOOL}


PROVIDER_NATIVE_DELEGATION_TOOL_NAMES = {
    "Agent",
    "Task",
    "spawn_agent",
    "collaboration.spawn_agent",
    "collaboration__spawn_agent",
    "assign_agent_task",
    "collaboration.assign_agent_task",
    "collaboration__assign_agent_task",
    "followup_task",
    "collaboration.followup_task",
    "collaboration__followup_task",
    "resume_agent",
    "collaboration.resume_agent",
    "collaboration__resume_agent",
}


HOOKABLE_TOOLS = FILE_MUTATION_TOOLS | {"Bash"} | PROVIDER_NATIVE_DELEGATION_TOOL_NAMES


REQUIRED_TOOL_INPUT_FIELDS = {
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "MultiEdit": ("file_path",),
    "NotebookEdit": ("notebook_path",),
    CODEX_APPLY_PATCH_TOOL: ("command",),
    "Bash": ("command",),
}


AEGIS_CURRENT_WORK_REL = ".aegis/state/current-work.json"


AEGIS_CLIENT_RELOAD_REL = ".aegis/state/client-reload-required.json"


AEGIS_PENDING_TRACKING_REL = ".aegis/state/pending-tracking.json"


AEGIS_DEGRADED_EVENTS_REL = ".aegis/state/degraded-events.json"


AEGIS_ENFORCEMENT_REL = ".aegis/state/enforcement.json"


AEGIS_GATE_DECISIONS_REL = ".aegis/reports/gate-decisions.jsonl"


AEGIS_VERIFY_REPORT_REL = ".aegis/reports/verification-report.json"


AEGIS_LOCAL_BIN_REL = ".aegis/bin/aegis"


PENDING_TRACKING_SAMPLE_LIMIT = 5


PROTECTED_PREFIXES = ("templates/", ".codex/", ".aegis/", ".claude/")


PROTECTED_EXACT = {"CODEX.md", "CLAUDE.md", "AGENTS.md"}


PROTECTED_NAME_PREFIXES = ("scripts/codex-", "scripts/template-")


WORKFLOW_LINK_PREFIXES = ("sessions/", "plans/")


WORKFLOW_TRACKING_PREFIX = "docs/ai/work-tracking/"


WORKFLOW_REPORT_SEGMENT = "/reports/"


SANCTIONED_AEGIS_MCP_MUTATION_SUFFIXES = {
    "kickoff",
    "start",
    "observe_start",
    "observe_stop",
    "runtime_update",
    "log",
    "handoff_repair",
    "closeout",
    "repair",
    "enforce",
}


MUTATING_GIT_RE = re.compile(
    r"(^|[;&|]\s*)git\s+("
    r"switch\s+-c|checkout\s+-b|branch\s+(-m|-d|-D)|commit\b|stash\b|reset\b|"
    r"merge\b|rebase\b|push\b|tag\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


MUTATING_TASKMASTER_RE = re.compile(
    r"(^|[;&|]\s*)task-master\s+("
    r"add-task|add-subtask|set-status|update|update-task|update-subtask|"
    r"expand|generate|parse-prd|move|add-dependency|remove-dependency|fix-dependencies"
    r")\b",
    re.IGNORECASE | re.MULTILINE,
)


MUTATING_AEGIS_RE = re.compile(
    r"(^|[;&|]\s*)(aegis|(?:\./)?\.aegis/bin/aegis|python3?\s+-m\s+aegis_foundation\.cli)\s+("
    r"install|uninstall|verify|start|kickoff|observe|log|closeout|enforce"
    r")\b",
    re.IGNORECASE | re.MULTILINE,
)


AEGIS_REPAIR_APPLY_RE = re.compile(
    r"(^|[;&|]\s*)(aegis|(?:\./)?\.aegis/bin/aegis|python3?\s+-m\s+aegis_foundation\.cli)\s+repair\b[^\n;&|]*\s--apply\b",
    re.IGNORECASE,
)


AEGIS_BOOTSTRAP_RE = re.compile(
    r"(^|[;&|]\s*)(aegis|(?:\./)?\.aegis/bin/aegis|python3?\s+-m\s+aegis_foundation\.cli)\s+(start|kickoff)\b",
    re.IGNORECASE,
)


AEGIS_LOG_RE = re.compile(
    r"(^|[;&|]\s*)(aegis|(?:\./)?\.aegis/bin/aegis|python3?\s+-m\s+aegis_foundation\.cli)\s+log\b",
    re.IGNORECASE,
)


AEGIS_VERIFY_RE = re.compile(
    r"(^|[;&|]\s*)(aegis|(?:\./)?\.aegis/bin/aegis|python3?\s+-m\s+aegis_foundation\.cli)\s+verify\b",
    re.IGNORECASE,
)


AEGIS_WITNESS_RE = re.compile(
    r"(^|[;&|]\s*)(aegis|(?:\./)?\.aegis/bin/aegis|python3?\s+-m\s+aegis_foundation\.cli)\s+witness\b",
    re.IGNORECASE,
)


AEGIS_CLOSEOUT_RE = re.compile(
    r"(^|[;&|]\s*)(aegis|(?:\./)?\.aegis/bin/aegis|python3?\s+-m\s+aegis_foundation\.cli)\s+closeout\b",
    re.IGNORECASE,
)


LOCALHOST_URL_RE = re.compile(
    r"^https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?(?:/|$)", re.IGNORECASE
)


OBSERVATION_BROWSER_MCP_RE = re.compile(
    r"^mcp__(?:playwright|browser|puppeteer|chrome(?:[-_]devtools)?|chromium)__",
    re.IGNORECASE,
)


REDIRECT_RE = re.compile(r"(?<![<])(?:>>|>)(?![>&])\s*([\"']?)([^\"'\s;&|]+)\1")


APPLY_PATCH_PATH_RE = re.compile(
    r"^\*\*\*\s+(?:Add|Update|Delete)\s+File:\s*(.+?)\s*$",
    re.MULTILINE,
)


APPLY_PATCH_MOVE_RE = re.compile(r"^\*\*\*\s+Move\s+to:\s*(.+?)\s*$", re.MULTILINE)


SHELL_CONTROL_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")


HARD_POLICY_SHELL_CONTROL_TOKENS = {"&", "&&", "(", ")", ";", "|", "||"}


HARD_POLICY_SHELLS = {"bash", "dash", "ksh", "sh", "zsh"}


RAW_DESTRUCTIVE_GIT_RE = re.compile(
    r"\bgit(?:\s+(?:-C|-c|--git-dir|--work-tree)\s+\S+)*\s+"
    r"(?:reset|clean|push|checkout|switch|restore|branch|remote|config)\b",
    re.IGNORECASE | re.MULTILINE,
)


RAW_TASKMASTER_WRITE_RE = re.compile(
    r"(?:\b(?:cp|install|mv|rm|tee|touch)\b|(?<![<])>>?)" r"[^\n;&|]*\.taskmaster(?:/|\\)",
    re.IGNORECASE | re.MULTILINE,
)


RAW_BEADS_AUTHORITY_RE = re.compile(
    r"(?:^|[\s;&|()`])(?:[^\s;&|()]*/)?bd\s+"
    r"(?:claim|close|create|delete|import|migrate|remove|set|sync|update)\b",
    re.IGNORECASE | re.MULTILINE,
)


RAW_DOLT_AUTHORITY_RE = re.compile(
    r"(?:^|[\s;&|()`])(?:[^\s;&|()]*/)?dolt\s+"
    r"(?:add|branch|checkout|commit|fetch|merge|pull|push|remote|reset|schema|sql|sql-server|table)\b",
    re.IGNORECASE | re.MULTILINE,
)


RAW_NESTED_SYNTHESIS_RE = re.compile(
    r"`|\$\(|<<|<\(|>\(|(?:^|[\s;&|()])(?:eval|source)\b|"
    r"(?:^|[\s;&|()])(?:bash|dash|ksh|sh|zsh)\b[^\n;&|]*\s-[A-Za-z]*c[A-Za-z]*\b|"
    r"(?:^|[\s;&|()])python3?\s+-c\b",
    re.IGNORECASE | re.MULTILINE,
)


RAW_UNSUPPORTED_SYNTHESIS_RE = re.compile(
    r"`|\$\(|<<|<\(|>\(|(?:^|[\s;&|()])python3?\s+-c\b",
    re.IGNORECASE | re.MULTILINE,
)


RAW_SHELL_EVALUATOR_RE = re.compile(
    r"(?:^|[\s;&|()])(?:eval|source)\b",
    re.IGNORECASE | re.MULTILINE,
)


GITHUB_GOVERNANCE_PATH_RE = re.compile(
    r"(?:^|/|\s)repos/[^/\s]+/[^/\s]+/(?:branches/[^/\s]+/protection(?:/|\s|$)|rulesets(?:/|\s|$))",
    re.IGNORECASE,
)


GITHUB_GOVERNANCE_GRAPHQL_RE = re.compile(
    r"\b(?:create|delete|update)(?:BranchProtectionRule|RepositoryRuleset)\b",
    re.IGNORECASE,
)


UNSUPPORTED_READ_ONLY_SHELL_RE = re.compile(r"(`|\$\(|<<|<\(|>\(|\b(?:python|python3?)\s+-c\b)")


PYTHON_WRITE_RE = re.compile(
    r"(?:open|Path)\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*['\"][^'\"]*[wa+][^'\"]*['\"])?"
    r"|write_text\(\s*['\"]",
    re.IGNORECASE,
)


READ_ONLY_SIMPLE_COMMANDS = {
    "basename",
    "cat",
    "cmp",
    "column",
    "comm",
    "cut",
    "date",
    "diff",
    "dirname",
    "echo",
    "false",
    "file",
    "fmt",
    "fold",
    "grep",
    "head",
    "jq",
    "ls",
    "nl",
    "od",
    "paste",
    "printf",
    "pwd",
    "realpath",
    "rg",
    "sed",
    "sort",
    "stat",
    "tail",
    "test",
    "tr",
    "true",
    "wc",
    "which",
    "yq",
}


# The reviewed Gas City operator environment, not a generic shell-prefix bypass.
ORCHESTRATOR_ENVIRONMENT = {
    "PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin",
    "GC_HOME": "/home/loucmane/gascity/home",
}
ORCHESTRATOR_ENV_UNSET = frozenset({"BEADS_DIR", "BEADS_DB"})


READ_ONLY_WRITE_FLAG_GUARDS = {
    "sed": ("-i", "--in-place"),
    "yq": ("-i", "--inplace"),
    "sort": ("-o", "--output"),
}


READ_ONLY_GIT_SUBCOMMANDS = {
    "branch",
    "diff",
    "grep",
    "log",
    "ls-files",
    "rev-parse",
    "show",
    "status",
}


# ga-fsfg R1: remote observation a BLOCKED seat may perform. A refspec-free
# `git fetch` touches only remote-tracking refs, and the listed `gh` reads never
# open a browser. `gh api`, `gh pr create|merge`, and refspec fetches stay
# hookable mutations.
READ_ONLY_GIT_FETCH_FLAGS = {
    "--all",
    "--dry-run",
    "--no-tags",
    "--prune",
    "--quiet",
    "--tags",
    "--verbose",
    "-p",
    "-q",
    "-t",
    "-v",
}


# A `git ls-remote` may list only a configured remote by name and plain ref
# patterns. `--upload-pack`, server options, paths, URLs and `ext::` helpers can
# run a program before readiness, so they stay hookable mutations.
READ_ONLY_GIT_LS_REMOTE_FLAGS = {
    "--branches",
    "--exit-code",
    "--get-url",
    "--heads",
    "--quiet",
    "--refs",
    "--symref",
    "--tags",
    "-b",
    "-h",
    "-q",
    "-t",
}
GIT_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
GIT_REF_PATTERN_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./*-]*$")
GIT_LS_REMOTE_POSITIONAL_BOUND = 4


READ_ONLY_GH_SUBCOMMANDS = {
    ("auth", "status"),
    ("issue", "list"),
    ("issue", "view"),
    ("pr", "checks"),
    ("pr", "diff"),
    ("pr", "list"),
    ("pr", "status"),
    ("pr", "view"),
    ("release", "list"),
    ("release", "view"),
    ("repo", "view"),
    ("run", "list"),
    ("run", "view"),
    ("run", "watch"),
}


GH_INTERACTIVE_FLAGS = {"--web", "-w"}
GH_INTERACTIVE_FLAG_PREFIX = "--web="
GH_SHORT_CLUSTER_RE = re.compile(r"^-[A-Za-z]+$")
# `gh auth status` may never print the account token into the transcript.
GH_AUTH_SECRET_FLAGS = {"--show-token", "-t"}
GH_AUTH_SECRET_FLAG_PREFIX = "--show-token="


READ_ONLY_TASKMASTER_SUBCOMMANDS = {
    "complexity-report",
    "list",
    "next",
    "show",
    "validate-dependencies",
}


READ_ONLY_AEGIS_SUBCOMMANDS = {
    "brief",
    "replay",
    "witness",
    "doctor",
    "explain-profile",
    "inspect",
    "list-profiles",
    "next",
    "plan-install",
    "reconcile",
    "status",
}


READ_ONLY_NPM_SCRIPTS = {"check", "lint", "test", "typecheck", "verify"}


READ_ONLY_TEST_OUTPUT_OPTIONS = {
    "--junitxml",
    "--json-report-file",
    "--outputFile",
    "--output-file",
    "--reporter=json",
    "--reporter=json-summary",
}


MCP_READ_ONLY_TOOL_RE = re.compile(
    r"^mcp__.*__(get|list|read|search|find|query|show|help|check|resolve|fetch|open|is_|has_)",
    re.IGNORECASE,
)


MCP_MUTATION_TOOL_RE = re.compile(
    r"^mcp__.*__(add|create|update|set|write|edit|delete|remove|rename|move|parse|expand|generate|archive|init|initialize|start|kickoff)",
    re.IGNORECASE,
)


TASKMASTER_SET_STATUS_RE = re.compile(
    r"(^|[;&|]\s*)task-master\s+set-status\b(?P<args>[^;&|]*)",
    re.IGNORECASE | re.MULTILINE,
)


TASKMASTER_GENERATE_RE = re.compile(
    r"(^|[;&|]\s*)task-master\s+generate\b", re.IGNORECASE | re.MULTILINE
)


SHELL_REDIRECT_TOKEN_RE = re.compile(r"^\d?>&\d$")


AEGIS_READ_ONLY_MCP_TOOL_SUFFIXES = {
    "inspect",
    "status",
    "runtime_status",
    "next",
    "doctor",
    "reconcile",
    "plan_install",
    "closeout_ready",
    "list_profiles",
    "explain_profile",
}


TASKMASTER_READ_ONLY_MCP_TOOL_SUFFIXES = {
    "help",
    "get_tasks",
    "next_task",
    "get_task",
}


PATH_FIELD_NAMES = {
    "file_path",
    "filepath",
    "path",
    "relative_path",
    "notebook_path",
    "target_path",
    "source_path",
    "old_path",
    "new_path",
    "destination",
    "dest",
}


class ApplyPatchParseError(ValueError):
    """Raised when a canonical Codex apply_patch payload cannot be classified safely."""


@dataclass(frozen=True)
class ApplyPatchOperation:
    operation: str
    source_path: str
    destination_path: str | None = None

    def as_event_record(self) -> dict[str, Any]:
        record = {
            "operation": "move" if self.destination_path is not None else self.operation,
            "source_path": self.source_path,
        }
        if self.destination_path is not None:
            record["destination_path"] = self.destination_path
            record["content_operation"] = self.operation
        return record


@dataclass(frozen=True)
class ParsedApplyPatch:
    operations: tuple[ApplyPatchOperation, ...]
    affected_paths: tuple[str, ...]
    patch_digest: str


@dataclass
class Payload:
    tool_name: str
    tool_input: dict[str, Any]
    # Hook-envelope attribution (capsule PR-1c): optional so every existing call site
    # and test remains valid; populated by parse_payload from the hook stdin JSON.
    session_id: str | None = None
    cwd: str | None = None
    parsed_apply_patch: ParsedApplyPatch | None = None
    permission_mode: str | None = None


@dataclass
class PayloadLoadError:
    reason: str
    raw_preview: str


AEGIS_OVERRIDE_TOKEN_REL = ".aegis/state/override-token.json"


OVERRIDE_ELIGIBLE_REASONS = {"readiness_blocked", "pending_tracking"}


RECOVERY_CONTRACT: dict[str, dict[str, str]] = {
    "coordination_target_invalid": {
        "tier": "c",
        "repair": "Inspect the registered target, canonical runtime, journal and live ownership; use no root or permission override.",
        "alt_repair": "",
        "audit": ".aegis/reports/gate-decisions.jsonl + ledger",
        "escalation": "Preserve the failed request and request a scoped repair if the target cannot be proven.",
    },
    "plan_mode_mutation": {
        "tier": "c",
        "repair": "Continue read-only inspection in plan mode; execute already-authorized work only from a non-plan session.",
        "alt_repair": "",
        "audit": ".aegis/reports/gate-decisions.jsonl + ledger",
        "escalation": "Keep the existing task scope and native permission rules. NOT override-eligible; no plan-file exemption.",
        "override_eligible": "false",
    },
    "readiness_blocked": {
        "tier": "b",
        "repair": "Inspect workflow state first; apply only the reviewed, bounded repair (preserve completed archives).",
        "alt_repair": "python3 plugins/gas-city-workflow/scripts/workflow.py begin --root . --bead <bead-id> --goal '<goal>' (authorized bootstrap mutation, not read-only)",
        "audit": ".aegis/reports/gate-decisions.jsonl + ledger",
        "escalation": 'If repair/kickoff cannot resolve it, break glass: aegis override --reason "<why>" (workflow-state only).',
        "override_eligible": "true",
    },
    "pending_tracking": {
        "tier": "a",
        "repair": 'aegis log --pending-id current   # or: aegis log --handler <h> --evidence <e> --note "<past-tense>"',
        "alt_repair": "",
        "audit": "sessions/current + active TRACKER.md + ledger",
        "escalation": 'If the pending event is unmatchable, break glass: aegis override --reason "<why>".',
        "override_eligible": "true",
    },
    "observation_mode_disallowed_mutation": {
        "tier": "c",
        "repair": "./.aegis/bin/aegis observe stop --target-dir . --summary '<what was observed>' --collect-artifacts",
        "alt_repair": "",
        "audit": ".aegis/reports/observation-report.json + ledger",
        "escalation": "Stop observation before implementation work. NOT override-eligible (boundary, not workflow state).",
        "override_eligible": "false",
    },
    "destructive_git_operation": {
        "tier": "c",
        "repair": "Use a normal feature branch and protected PR delivery; use `git restore --staged <path>` only for index cleanup.",
        "alt_repair": "For recovery, create a backup branch and use a reviewed revert or repair PR instead of destructive Git.",
        "audit": ".aegis/reports/gate-decisions.jsonl + ledger",
        "escalation": "Human-executed recovery outside the autonomous session. NOT override-eligible.",
        "override_eligible": "false",
    },
    "native_delegation_requires_gas_city": {
        "tier": "c",
        "repair": "Create or select a Bead in the managed project's rig, then use a reviewed `gc sling` route.",
        "alt_repair": "For an exceptional provider-native request, commit one exact request-bound .gas-city-delegation-exceptions.json record for review.",
        "audit": ".aegis/reports/gate-decisions.jsonl + ledger + Bead evidence",
        "escalation": "Stop if Gas City routing fails; provider-native delegation is never a fallback. NOT override-eligible.",
        "override_eligible": "false",
    },
    "managed_project_context_invalid": {
        "tier": "c",
        "repair": "Repair the tracked .gas-city-workflow.json / source-root project registry parity, then rerun project-context --check.",
        "alt_repair": "Do not remove the project descriptor or runtime pointer to bypass managed status.",
        "audit": ".aegis/reports/gate-decisions.jsonl + ledger",
        "escalation": "Resolve project identity before delegation. NOT override-eligible.",
        "override_eligible": "false",
    },
    "native_delegation_exception_invalid": {
        "tier": "c",
        "repair": "Restore exact tracked HEAD bytes or replace the exception through a reviewed signed source change.",
        "alt_repair": "Route through Gas City instead of using a provider-native exception.",
        "audit": ".aegis/reports/gate-decisions.jsonl + ledger + Bead evidence",
        "escalation": "Exception-file drift is fail-closed and NOT override-eligible.",
        "override_eligible": "false",
    },
}


RECOVERY_CONTRACT_DEFAULT = {
    "tier": "c",
    "repair": "./.aegis/bin/aegis next --target-dir .   # inspect the prescribed next action",
    "alt_repair": "",
    "audit": ".aegis/reports/gate-decisions.jsonl + ledger",
    "escalation": "Resolve the underlying state. NOT override-eligible by default.",
    "override_eligible": "false",
}


class HardPolicyParseError(ValueError):
    """The hard-policy shell subset could not be parsed safely."""


CODEX_TASK_LOGGING_SUBCOMMANDS = {
    ("work-tracking", "update"),
    ("work-tracking", "audit"),
    ("sessions", "update"),
    ("plan", "sync"),
    ("scanner", "run"),
}


DELIVERY_COMMAND_RE = re.compile(
    r"(^|[;&|]\s*)(git\s+push\b|gh\s+pr\s+(create|merge|ready)\b)",
    re.IGNORECASE,
)


TASKMASTER_TASKS_JSON_SUFFIX = ".taskmaster/tasks/tasks.json"


CAPSULE_RISK_SEED_SUFFIX = ".aegis/capsule/risk-seed.json"


AEGIS_BRIEF_REL = ".aegis/brief.json"


TASK_BRANCH_RE = re.compile(r"task-?(\d+)", re.IGNORECASE)


BARE_REDIRECT_OP_RE = re.compile(r"^(?:\d?>{1,2}|<|&>{1,2})$")


REDIRECT_TOKEN_RE = re.compile(r"^(?:\d?>{1,2}\S+|\d?>>?&\d|<\S+|&>{1,2}\S+)$")
