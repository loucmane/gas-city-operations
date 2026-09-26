"""Aegis hook gate: entrypoint."""

from __future__ import annotations

import sys

from .decisions import block, project_root
from .payloads import bash_command, file_paths_from_payload, is_protected_path, load_payload
from .shell_policy import protected_bash_violations
from .tracking import ledger_record, posttooluse_tracking
from .lifecycle import config_change_guard, session_start_hook, stop_gate
from .pretool import pretooluse_gate_with_degraded_fallback


def path_guard() -> int:
    payload = load_payload()
    if payload is None:
        return 0
    root = project_root()
    protected = [
        path for path in file_paths_from_payload(payload, root) if is_protected_path(path, root)
    ]
    if not protected:
        return 0
    paths = "\n".join(f"  - {path}" for path in protected)
    return block(
        "BLOCKED by .claude/scripts/codex-path-guard.sh\n\n"
        f"Tool: {payload.tool_name}\n"
        f"Protected path(s):\n{paths}\n\n"
        "Claude-owned work must not modify CODEX.md, templates/**, scripts/codex-*, "
        "scripts/template-*, or .codex/**. Use a Codex-led follow-up for shared changes."
    )


def bash_guard() -> int:
    payload = load_payload()
    if payload is None:
        return 0
    command = bash_command(payload)
    violations = protected_bash_violations(command)
    if not violations:
        return 0
    details = "\n".join(f"  - {violation}" for violation in violations)
    return block(
        "BLOCKED by .claude/scripts/bash-command-guard.sh\n\n"
        f"Command: {command}\n"
        f"Violation(s):\n{details}\n\n"
        "Bash may not be used to bypass protected Aegis/Codex-owned path boundaries."
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: gate_lib.py "
            "<pretooluse|posttooluse|stop|path|bash|record|recordjson|deliveryfailure>",
            file=sys.stderr,
        )
        return 1
    command = sys.argv[1]
    if command == "pretooluse":
        return pretooluse_gate_with_degraded_fallback(sys.stdin.read())
    if command == "posttooluse":
        return posttooluse_tracking()
    if command == "stop":
        return stop_gate()
    if command == "path":
        return path_guard()
    if command == "bash":
        return bash_guard()
    if command == "configchange":
        return config_change_guard()
    if command == "sessionstart":
        return session_start_hook()
    if command in {"record", "posttoolusefailure", "sessionend", "subagentstart"}:
        return ledger_record()
    if command == "deliveryfailure":
        # ga-fsfg R3: the synchronous PostToolUseFailure handler that removes a failed
        # delivery call's binding; the async ledger recorder stays separate.
        from .delivery import delivery_failure

        return delivery_failure()
    if command == "recordjson":
        result = ledger_record()
        print("{}")
        return result
    print(f"unknown gate command: {command}", file=sys.stderr)
    return 1
