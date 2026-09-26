"""Aegis hook gate: tracking."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

from .contracts import (
    AEGIS_BRIEF_REL,
    AEGIS_VERIFY_RE,
    AEGIS_WITNESS_RE,
    ApplyPatchParseError,
    BARE_REDIRECT_OP_RE,
    CAPSULE_RISK_SEED_SUFFIX,
    CODEX_APPLY_PATCH_TOOL,
    DELIVERY_COMMAND_RE,
    MUTATING_TASKMASTER_RE,
    Payload,
    REDIRECT_TOKEN_RE,
    SHELL_CONTROL_SPLIT_RE,
    TASKMASTER_SET_STATUS_RE,
    TASKMASTER_TASKS_JSON_SUFFIX,
    TASK_BRANCH_RE,
)
from .loaders import _load_brief_lib_module, _load_ledger_lib_module
from .decisions import _read_json_object, append_gate_decision, payload_digest, project_root
from .payloads import (
    apply_patch_command,
    apply_patch_event_metadata,
    bash_command,
    command_name,
    file_paths_from_payload,
    load_payload,
    option_value,
    shlex_tokens,
    strip_shell_prefixes,
)
from .evidence import (
    cleaned_shell_tokens,
    command_segments,
    payload_handler,
    payload_is_mutation,
    record_pending_tracking_event,
)
from .runtime_state import pending_tracking_events
from .shell_policy import workflow_discharge_pending_id


def posttooluse_tracking() -> int:
    payload = load_payload()
    if payload is None:
        return 0
    root = project_root()
    from .coordination import request as coordination_request, target_for

    try:
        target = target_for(root, payload, post_success=True)
        if target is not None:
            parsed = coordination_request(root, payload)
            if parsed is None:
                # ga-fsfg R3: a target without a workflow request came from the call's
                # delivery binding; record the delivery event on <W> and consume it.
                from .delivery import record_delivery_event

                return record_delivery_event(root, target, payload)
            if parsed[0] in {"log", "discharge"}:
                return 0  # The supported command already reconciled target evidence.
            root = target
    except Exception:
        # Never misattribute an ambiguous cross-worktree event to canonical main.
        # It is a failed seat-level reconciliation, not silent tracking success.
        try:
            append_gate_decision(
                root,
                hook="PostToolUse",
                payload=payload,
                verdict="block",
                reason="coordination_target_invalid",
            )
        except Exception:
            pass  # Audit failure cannot turn unresolved tracking into success.
        print(
            "Aegis: coordination tracking could not revalidate the target; "
            "stop and reconcile the preserved request before further work.",
            file=sys.stderr,
        )
        return 2
    discharged = (
        workflow_discharge_pending_id(bash_command(payload), root)
        if payload.tool_name == "Bash"
        else None
    )
    if discharged is not None:
        # ga-fsfg R1: a discharge that exits without resolving its event fails closed;
        # a successful one is journal-bound evidence and enqueues nothing.
        if any(str(event.get("id") or "") == discharged for event in pending_tracking_events(root)):
            print(
                f"Aegis: discharge exited without resolving pending event {discharged}; "
                "stop and reconcile the workflow journal before further work.",
                file=sys.stderr,
            )
            return 2
        return 0
    record_pending_tracking_event(root, payload)
    _maybe_emit_scope_nudge(root, payload)
    return 0


def _maybe_emit_scope_nudge(root: Path, payload: Payload) -> None:
    """Capsule PR-1d (spec section 2.1): ONE non-blocking additionalContext nudge per
    branch when scope inference was ambiguous. Fully failure-proof — this runs on the
    synchronous hook path and must never gain a failure mode."""

    try:
        ledger_lib = _load_ledger_lib_module()
        if ledger_lib is None:
            return
        store = ledger_lib.store_path(cwd=root)
        if not store.is_file():
            return
        branch = _record_branch(payload.cwd or str(root))
        if not branch:
            return
        ledger = ledger_lib.open_ledger(cwd=root)
        try:
            events = _scope_events_for_branch(ledger, branch)
            needs = any(
                event.get("extra", {}).get("needs_confirmation")
                and not event.get("extra", {}).get("confirmed")
                for event in events
            )
            confirmed = any(event.get("extra", {}).get("confirmed") for event in events)
            nudged = any(event.get("extra", {}).get("nudge") for event in events)
            if not needs or confirmed or nudged:
                return
            ledger.append(
                {
                    "session_id": payload.session_id,
                    "branch": branch,
                    "event_type": "scope",
                    "extra": {"nudge": True},
                }
            )
        finally:
            ledger.close()
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": (
                            f"Aegis scope note: branch '{branch}' has no inferable task id. "
                            "If this work belongs to a task, run "
                            "`aegis scope set <task-id> [path-globs...]` once to record its scope "
                            "(used by the delivery witness). This is advisory and will not be asked again."
                        ),
                    }
                }
            )
        )
    except Exception:  # noqa: BLE001 - nudge is strictly best-effort.
        return


def load_brief(root: Path) -> dict[str, Any]:
    """Read `.aegis/brief.json` (capsule PR-1d gate registry); {} on any failure."""

    data = _read_json_object(root / AEGIS_BRIEF_REL)
    return data if isinstance(data, dict) else {}


def _normalize_command_text(text: str) -> str:
    tokens = shlex_tokens(text)
    # Preserve the historical post-execution evidence label for this harmless
    # cache-suppression prefix. This matcher does not authorize execution; the
    # pre-kickoff classifier still rejects the non-operator environment setting.
    if tokens[:1] == ["PYTHONDONTWRITEBYTECODE=1"]:
        tokens = tokens[1:]
    tokens = strip_shell_prefixes(tokens)
    kept: list[str] = []
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if BARE_REDIRECT_OP_RE.match(token):
            # A bare redirect operator consumes the following target token too.
            skip_next = True
            continue
        if REDIRECT_TOKEN_RE.match(token):
            continue
        kept.append(token)
    return " ".join(kept)


def normalized_command_segments(command: str) -> list[str]:
    """Normalized candidate forms of a Bash command for gate-registry matching.

    Splits on shell control operators, strips env-assignment prefixes and redirect
    tokens, collapses whitespace, and joins adjacent `cd X` + command pairs back into
    `cd X && command` so cd-prefix patterns match alongside `-C`/`--dir` variants.
    """

    raw_segments = [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]
    normalized = [
        form for form in (_normalize_command_text(segment) for segment in raw_segments) if form
    ]
    candidates = list(normalized)
    for index in range(len(normalized) - 1):
        if normalized[index].startswith("cd "):
            candidates.append(f"{normalized[index]} && {normalized[index + 1]}")
    return candidates


def match_gate_command(command: str, gates: dict[str, Any]) -> tuple[str, str] | None:
    """Return (package, gate) when the command matches a registered gate pattern.

    Matching is exact equality on normalized forms; pattern VALUES are per-repo
    configuration from `.aegis/brief.json`, never hardcoded here.
    """

    if not gates or not command:
        return None
    candidates = set(normalized_command_segments(command))
    if not candidates:
        return None
    for package, package_gates in gates.items():
        if not isinstance(package_gates, dict):
            continue
        for gate, patterns in package_gates.items():
            if not isinstance(patterns, (list, tuple)):
                continue
            for pattern in patterns:
                if isinstance(pattern, str) and _normalize_command_text(pattern) in candidates:
                    return str(package), str(gate)
    return None


def _record_head_commit(cwd: str | None) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    commit = result.stdout.strip()
    return commit or None


def _scope_events_for_branch(ledger: Any, branch: str) -> list[dict[str, Any]]:
    return [event for event in ledger.read(event_type="scope") if event.get("branch") == branch]


def _ensure_scope_record(
    ledger: Any,
    *,
    branch: str | None,
    session_id: Any,
    cwd: Any,
    agent_id: str | None,
    agent_type: str | None,
    parent_agent_id: str | None,
    brief: dict[str, Any],
) -> None:
    """Capsule PR-1d (spec section 2.1): infer a scope record at the first recorded
    mutation on a new branch. One record per branch; never blocks, never re-asks."""

    if not branch:
        return
    existing = _scope_events_for_branch(ledger, branch)
    if any(not event.get("extra", {}).get("nudge") for event in existing):
        return
    match = TASK_BRANCH_RE.search(branch)
    task_id = match.group(1) if match else None
    gates = brief.get("gates") if isinstance(brief.get("gates"), dict) else {}
    source_roots = brief.get("source_roots") if isinstance(brief.get("source_roots"), list) else []
    ledger.append(
        {
            "session_id": session_id,
            "branch": branch,
            "cwd": cwd,
            "event_type": "scope",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "parent_agent_id": parent_agent_id,
            "extra": {
                "task_id": task_id,
                "path_globs": list(source_roots),
                "gates": sorted(
                    f"{package}:{gate}"
                    for package, package_gates in gates.items()
                    if isinstance(package_gates, dict)
                    for gate in package_gates
                ),
                "inferred": True,
                "needs_confirmation": task_id is None,
            },
        }
    )


def _record_branch(cwd: str | None) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    branch = result.stdout.strip()
    return branch or None


def _hook_adapter(data: dict[str, Any]) -> str:
    return "codex" if data.get("model") or data.get("turn_id") else "claude"


def _response_mappings(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _response_mappings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _response_mappings(nested)


def _hook_outcome(data: dict[str, Any]) -> str:
    hook_event = str(data.get("hook_event_name") or "")
    if hook_event == "PostToolUseFailure":
        return "fail"
    if data.get("is_interrupt") is True:
        return "interrupted"
    response = data.get("tool_response")
    for mapping in _response_mappings(response):
        if mapping.get("interrupted") is True or mapping.get("is_interrupt") is True:
            return "interrupted"
        if mapping.get("is_error") is True or mapping.get("isError") is True:
            return "fail"
        if mapping.get("success") is False or mapping.get("ok") is False:
            return "fail"
        status = str(mapping.get("status") or "").strip().lower()
        if status in {"cancelled", "canceled", "interrupted"}:
            return "interrupted"
        if status in {"error", "failed", "failure"}:
            return "fail"
        for key in ("exit_code", "exitCode", "returncode", "return_code"):
            value = mapping.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value != 0:
                return "fail"
            if isinstance(value, str) and value.strip().lstrip("-").isdigit() and int(value) != 0:
                return "fail"
    return "pass" if hook_event == "PostToolUse" else "unknown"


def _hook_agent_identity(data: dict[str, Any]) -> tuple[str | None, str | None, str | None, str]:
    adapter = _hook_adapter(data)
    session_id = str(data.get("session_id") or os.environ.get("AEGIS_SESSION_ID") or "").strip()
    payload_agent = str(data.get("agent_id") or "").strip()
    env_agent = str(os.environ.get("AEGIS_AGENT_ID") or "").strip()
    agent_id = payload_agent or env_agent or (f"session:{session_id}" if session_id else None)
    payload_parent = str(data.get("parent_agent_id") or "").strip()
    env_parent = str(os.environ.get("AEGIS_PARENT_AGENT_ID") or "").strip()
    root_agent = f"session:{session_id}" if session_id else None
    parent_agent_id = payload_parent or env_parent or None
    if parent_agent_id is None and agent_id is not None and root_agent and agent_id != root_agent:
        parent_agent_id = root_agent
    agent_type = (
        str(
            data.get("agent_type")
            or os.environ.get("AEGIS_AGENT_TYPE")
            or (f"{adapter}-session" if agent_id == root_agent else "")
        ).strip()
        or None
    )
    if payload_parent:
        source = "payload-parent"
    elif env_parent:
        source = "environment-parent"
    elif parent_agent_id:
        source = "session-root-parent"
    elif agent_id == root_agent:
        source = "session-root"
    elif payload_agent:
        source = "payload-agent"
    elif env_agent:
        source = "environment-agent"
    else:
        source = "unavailable"
    return agent_id, agent_type, parent_agent_id, source


def _record_handler(data: dict[str, Any], payload: Payload | None) -> str:
    adapter = _hook_adapter(data)
    if payload is None:
        hook_event = str(data.get("hook_event_name") or "unknown").lower()
        return f"{adapter}:{hook_event}"
    handler = payload_handler(payload)
    if adapter == "codex" and handler.startswith("claude:"):
        return "codex:" + handler.split(":", 1)[1]
    return handler


def _ledger_delivery_command(root: Path | None, command: str) -> bool:
    """ga-fsfg R3: the delivery parser, not a widened pattern, classifies its own forms."""

    if root is None:
        return False
    try:
        from .delivery import delivery_operation

        return delivery_operation(root, command) is not None
    except Exception:  # noqa: BLE001 - the passive recorder never fails on a classifier.
        return False


def _classify_record_event(
    data: dict[str, Any],
    payload: Payload | None,
    paths: list[str],
    outcome: str,
    root: Path | None = None,
) -> str:
    hook_event = str(data.get("hook_event_name") or "")
    if hook_event == "PostToolUseFailure":
        return "tool_failure"
    if hook_event == "SessionStart":
        return "session_begin"
    if hook_event == "SessionEnd":
        return "session_end"
    if hook_event == "SubagentStart":
        return "subagent_begin"
    if hook_event == "SubagentStop":
        return "subagent_end"
    if payload is not None and payload.tool_name == "Bash":
        command = bash_command(payload)
        if DELIVERY_COMMAND_RE.search(command) or _ledger_delivery_command(root, command):
            return "delivery"
        if MUTATING_TASKMASTER_RE.search(command):
            return "task_truth"
    if any(path.endswith(TASKMASTER_TASKS_JSON_SUFFIX) for path in paths):
        return "task_truth"
    if hook_event == "PostToolUse":
        return "tool_failure" if outcome in {"fail", "interrupted"} else "mutation"
    return "unknown"


def _bash_segment_is_any_pr_merge(segment: str) -> bool:
    tokens = cleaned_shell_tokens(segment)
    if len(tokens) < 3:
        return False
    if command_name(tokens[0]) != "gh" or tokens[1:3] != ["pr", "merge"]:
        return False
    args = tokens[3:]
    if "--admin" in args or "--web" in args or option_value(tokens, "--repo") or "-R" in args:
        return False
    return any(method in args for method in {"--merge", "--squash", "--rebase"})


def _capsule_compile_reason_for_event(
    payload: Payload | None,
    paths: list[str],
    event_type: str,
) -> str | None:
    if any(path.endswith(CAPSULE_RISK_SEED_SUFFIX) for path in paths):
        return "risk-register-change"
    if any(path.endswith(TASKMASTER_TASKS_JSON_SUFFIX) for path in paths):
        return "task-status-change"
    if event_type == "verification":
        return "verification"
    if event_type == "task_truth":
        return "task-status-change"
    if payload is None or payload.tool_name != "Bash":
        return None
    command = bash_command(payload)
    if AEGIS_WITNESS_RE.search(command):
        return "pre-delivery"
    if AEGIS_VERIFY_RE.search(command):
        return "verification"
    if TASKMASTER_SET_STATUS_RE.search(command):
        return "task-status-change"
    if any(_bash_segment_is_any_pr_merge(segment) for segment in command_segments(command)):
        return "post-merge"
    return None


def ledger_record() -> int:
    """Append one passive ledger event for a hook payload (capsule PR-1b).

    The recorder must NEVER block, fail, or slow the session: every error path
    degrades to exit 0. It runs as an async hook, so nothing it prints or returns
    can influence tool behavior by design.
    """

    try:
        raw = sys.stdin.read()
        data = json.loads(raw or "{}")
        if not isinstance(data, dict):
            return 0
        ledger_lib = _load_ledger_lib_module()
        if ledger_lib is None:
            return 0
        root = project_root()
        tool_name = data.get("tool_name")
        tool_input = data.get("tool_input")
        payload = (
            Payload(str(tool_name), dict(tool_input))
            if isinstance(tool_name, str) and isinstance(tool_input, dict)
            else None
        )
        patch_metadata: dict[str, Any] | None = None
        patch_parse_error: str | None = None
        if payload is not None and payload.tool_name == CODEX_APPLY_PATCH_TOOL:
            try:
                patch_metadata = apply_patch_event_metadata(payload, root)
                paths = list(patch_metadata["affected_paths"])
            except ApplyPatchParseError as exc:
                patch_parse_error = str(exc)
                paths = []
                patch_metadata = {
                    "affected_paths": [],
                    "operations": [],
                    "patch_digest": sha256(
                        apply_patch_command(payload).encode("utf-8")
                    ).hexdigest(),
                }
        else:
            paths = file_paths_from_payload(payload, root) if payload is not None else []
        hook_event = str(data.get("hook_event_name") or "")
        outcome = _hook_outcome(data)
        agent_id, agent_type, parent_agent_id, attribution_source = _hook_agent_identity(data)
        extra: dict[str, Any] = {
            "hook_event_name": hook_event or None,
            "tool_use_id": data.get("tool_use_id"),
            "turn_id": data.get("turn_id"),
            "model": data.get("model"),
            "permission_mode": data.get("permission_mode"),
            "transcript_path": data.get("transcript_path"),
            "agent_transcript_path": data.get("agent_transcript_path"),
            "agent_attribution_source": attribution_source,
            "adapter": _hook_adapter(data),
            "error": data.get("error"),
            "source": data.get("source"),
            "reason": data.get("reason"),
        }
        if payload is not None:
            extra["is_mutation"] = payload_is_mutation(payload)
            if payload.tool_name == "Bash":
                extra["command"] = bash_command(payload)
            if patch_metadata is not None:
                extra.update(patch_metadata)
                if paths:
                    extra["primary_evidence_path"] = paths[0]
            if patch_parse_error is not None:
                extra["parse_error"] = patch_parse_error
        brief = load_brief(root)
        gates = brief.get("gates") if isinstance(brief.get("gates"), dict) else {}
        redact_extra = (
            brief.get("redact_extra") if isinstance(brief.get("redact_extra"), list) else []
        )
        cwd_value = data.get("cwd") if isinstance(data.get("cwd"), str) else None
        branch = _record_branch(cwd_value)
        event_type = _classify_record_event(data, payload, paths, outcome, root)
        if (
            payload is not None
            and payload.tool_name == "Bash"
            and hook_event in {"PostToolUse", "PostToolUseFailure"}
        ):
            matched = match_gate_command(bash_command(payload), gates)
            if matched is not None:
                event_type = "verification"
                extra["package"], extra["gate"] = matched
                extra["commit"] = _record_head_commit(cwd_value)
        capsule_reason = _capsule_compile_reason_for_event(payload, paths, event_type)
        if capsule_reason:
            extra["capsule_refresh_reason"] = capsule_reason
        event = {
            "session_id": data.get("session_id"),
            "branch": branch,
            "cwd": data.get("cwd"),
            "event_type": event_type,
            "tool_name": tool_name if isinstance(tool_name, str) else None,
            "handler": _record_handler(data, payload),
            "paths": paths,
            "outcome": outcome,
            "exit_class": outcome,
            "duration_ms": data.get("duration_ms"),
            "agent_id": agent_id,
            "agent_type": agent_type,
            "parent_agent_id": parent_agent_id,
            "payload_digest": payload_digest(payload) if payload is not None else None,
            "extra": {key: value for key, value in extra.items() if value is not None},
        }
        ledger = ledger_lib.open_ledger(
            cwd=root, redact_patterns=[p for p in redact_extra if isinstance(p, str)]
        )
        try:
            ledger.append(event)
            if hook_event == "PostToolUse" and extra.get("is_mutation"):
                _ensure_scope_record(
                    ledger,
                    branch=branch,
                    session_id=data.get("session_id"),
                    cwd=cwd_value,
                    agent_id=agent_id,
                    agent_type=agent_type,
                    parent_agent_id=parent_agent_id,
                    brief=brief,
                )
            if capsule_reason:
                _refresh_capsule_if_stale(root, reason=capsule_reason)
        finally:
            ledger.close()
    except Exception:  # noqa: BLE001 - the recorder must never break a session.
        return 0
    return 0


def _refresh_capsule_if_stale(root: Path, *, reason: str) -> None:
    """Best-effort boundary refresh; never block hook execution."""

    try:
        brief_lib = _load_brief_lib_module()
        if brief_lib is None:
            return
        status = brief_lib.capsule_status(root)
        if status.get("fresh"):
            return
        capsule = brief_lib.compile_capsule(root, reason=reason)
        brief_lib.write_capsule(root, capsule, brief_lib.render_markdown(capsule))
    except Exception:  # noqa: BLE001 - capsule freshness must never break hooks.
        return
