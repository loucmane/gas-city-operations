"""Aegis hook gate: pretool."""

from __future__ import annotations

import sys
import time
import traceback

from .contracts import (
    AEGIS_DEGRADED_EVENTS_REL,
    ApplyPatchParseError,
    CODEX_APPLY_PATCH_TOOL,
    FILE_MUTATION_TOOLS,
    PayloadLoadError,
)
from .decisions import (
    advisory_enabled,
    advisory_message,
    append_gate_decision,
    block,
    block_unclassifiable_payload,
    gate_allow_or_record,
    gate_block_or_record,
    gate_hard_block,
    project_root,
)
from .payloads import (
    apply_patch_command,
    bash_command,
    file_paths_from_payload,
    is_hookable_tool,
    is_mcp_tool,
    is_protected_path,
    is_workflow_owned_path,
    load_payload_result,
    mcp_aegis_target_dir_violation,
    mcp_path_values,
    normalize_path,
    parse_payload,
    parsed_apply_patch,
    payload_required_field_issue,
    raw_payload_preview,
)
from .runtime_state import (
    clear_client_reload_marker,
    current_work_is_observation,
    hook_invoking_agent,
    required_pending_tracking_events,
    run_readiness,
    write_degraded_event,
)
from .delegation import (
    DelegationPolicyError,
    evaluate_native_delegation,
    is_provider_native_delegation_tool,
    resolve_managed_project,
)
from .permission_modes import deny_plan_mode_mutation
from .hard_policy import hard_policy_violations, raw_hard_policy_families
from .shell_policy import (
    aegis_cli_target_dir_violations,
    degraded_payload_is_non_destructive,
    payload_is_aegis_override,
    payload_is_sanctioned_aegis_workflow_mutation,
    protected_bash_violations,
)
from .evidence import (
    format_pending_tracking,
    payload_is_aegis_bootstrap,
    payload_is_aegis_enforce,
    payload_is_aegis_log,
    payload_is_aegis_pending_log,
    payload_is_aegis_repair_apply,
    payload_is_aegis_runtime_update,
    payload_is_aegis_uninstall_apply,
    payload_is_exact_delivery_discharge,
    payload_is_mutation,
    payload_is_observation_allowed,
    payload_is_post_closeout_delivery,
    payload_is_post_closeout_taskmaster_completion,
    payload_is_read_only,
)


def degraded_pretooluse_fallback(raw_payload: str, exc: BaseException) -> int:
    loaded = parse_payload(raw_payload)
    reason = f"{type(exc).__name__}: {exc}"
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]
    if isinstance(loaded, PayloadLoadError):
        return block_unclassifiable_payload(
            f"gate infrastructure failed after an unclassifiable payload: {reason}",
            loaded.raw_preview,
        )
    root = project_root()
    plan_denial = deny_plan_mode_mutation(root, loaded)
    if plan_denial is not None:
        return plan_denial
    # ga-4p6f: provider-native delegation in a managed project never uses degraded
    # approval; a project context that cannot be resolved counts as managed. This
    # runs before any further import so a second failure cannot skip it.
    if is_provider_native_delegation_tool(loaded.tool_name):
        try:
            managed = resolve_managed_project(root) is not None
        except Exception:  # noqa: BLE001 - an unknown context fails closed.
            managed = True
        if managed:
            return gate_hard_block(
                root,
                loaded,
                "BLOCKED: provider-native delegation cannot use degraded approval",
                reason="native_delegation_degraded",
            )
    from .coordination import request as coordination_request

    try:
        coordinating = coordination_request(root, loaded) is not None
        if not coordinating:
            # ga-fsfg R3: a delivery call is stationary coordination too; it never
            # degrades into an allow.
            from .delivery import delivery_request

            coordinating = delivery_request(root, loaded) is not None
        if not coordinating:
            # ga-fsfg R4: so is an evidence write; it never degrades into the generic
            # Write handling.
            from .evidence_write import evidence_write_claim

            coordinating = evidence_write_claim(root, loaded) is not None
    except Exception:
        coordinating = True
    if coordinating:
        return gate_hard_block(
            root,
            loaded,
            "BLOCKED: coordination cannot use degraded approval",
            reason="coordination_target_invalid",
        )
    if degraded_payload_is_non_destructive(loaded):
        event = write_degraded_event(root, loaded, reason, raw_payload, trace=trace)
        print(
            "DEGRADED | pretooluse gate infrastructure failed; allowed conservative non-destructive action "
            f"and wrote {AEGIS_DEGRADED_EVENTS_REL} event {event['id']}",
            file=sys.stderr,
        )
        return 0
    # Advisory workflow failures record a degraded event and allow, loudly, only
    # after the non-overridable client-mode boundary above. Strict
    # mode keeps failing closed below. The advisory check itself is best-effort:
    # if it crashes too, fail closed.
    try:
        if advisory_enabled(root):
            event = write_degraded_event(
                root,
                loaded,
                reason,
                raw_payload,
                mode="degraded_advisory_allow",
                action_class="mutation_or_unsafe",
                trace=trace,
            )
            print(
                "DEGRADED-ADVISORY | pretooluse gate infrastructure failed while evaluating a mutation; "
                f"enforcement mode is advisory so the action is allowed and recorded as "
                f"{AEGIS_DEGRADED_EVENTS_REL} event {event['id']}. Details: {reason}",
                file=sys.stderr,
            )
            return 0
    except Exception:  # noqa: BLE001 - double infra failure falls through to fail-closed.
        pass
    return block(
        "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
        f"Tool: {loaded.tool_name}\n"
        "Reason: PreToolUse gate infrastructure failed while evaluating a mutation or unsafe action.\n\n"
        f"Details: {reason}\n\n"
        f"Traceback (for diagnosis):\n{trace}\n"
        "Aegis fails closed for destructive, protected, workflow-state, and unclassified actions when the gate cannot render a verdict."
    )


def _prune_delivery_bindings(root) -> None:
    """ga-fsfg R3: expired delivery bindings are pruned by the next PreToolUse.

    Best effort: pruning never decides or disrupts any call.
    """

    try:
        from .delivery_binding import prune_expired

        prune_expired(root)
    except Exception:  # noqa: BLE001 - expired bindings are ignored by every check anyway.
        pass


def pretooluse_gate(raw_payload: str | None = None) -> int:
    # ga-fsfg R3: the delivery deadline is measured from hook entry.
    started = time.monotonic()
    root = project_root()
    loaded = load_payload_result(raw_payload)
    if isinstance(loaded, PayloadLoadError):
        if advisory_enabled(root):
            append_gate_decision(
                root,
                hook="pretooluse",
                payload=None,
                verdict="would_block",
                reason=f"unclassifiable_payload: {loaded.reason}",
                raw_preview=loaded.raw_preview,
            )
            advisory_message("pretooluse", "unclassifiable_payload")
            return 0
        return block_unclassifiable_payload(loaded.reason, loaded.raw_preview)
    payload = loaded
    payload.hook_started = started
    _prune_delivery_bindings(root)
    plan_denial = deny_plan_mode_mutation(root, payload)
    if plan_denial is not None:
        return plan_denial
    try:
        delegation = evaluate_native_delegation(root, payload)
    except DelegationPolicyError as exc:
        return gate_hard_block(
            root,
            payload,
            "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
            f"Tool: {payload.tool_name}\n"
            "Reason: Gas City managed-project delegation policy could not establish an exact safe context.\n\n"
            f"Details: {exc.detail}\n\n"
            "Provider-native delegation fails closed when project identity or reviewed exception bytes are invalid.",
            reason=exc.reason,
        )
    if delegation is not None:
        if not delegation.managed:
            return 0
        if delegation.allowed:
            try:
                append_gate_decision(
                    root,
                    hook="pretooluse",
                    payload=payload,
                    verdict="allow",
                    reason=delegation.reason,
                )
            except (
                Exception
            ) as exc:  # noqa: BLE001 - an exception without audit evidence is not valid.
                return gate_hard_block(
                    root,
                    payload,
                    "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
                    f"Tool: {payload.tool_name}\n"
                    "Reason: the reviewed native-delegation exception could not be recorded.\n\n"
                    f"Details: {type(exc).__name__}: {exc}",
                    reason="native_delegation_exception_invalid",
                )
            return 0
        project_id = delegation.project.project_id if delegation.project is not None else "unknown"
        return gate_hard_block(
            root,
            payload,
            "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
            f"Tool: {payload.tool_name}\n"
            f"Managed project: {project_id}\n"
            f"Request SHA-256: {delegation.request_sha256}\n"
            "Reason: provider-native delegation is not the work-routing authority in a Gas City managed project.\n\n"
            "Create or select the project Bead and use a reviewed `gc sling` route. If Gas City routing fails, stop; do not silently fall back to a provider-native worker.\n"
            "A reviewed exception must be tracked, clean, branch-bound, and exact-request-bound.",
            reason=delegation.reason,
        )
    if not is_hookable_tool(payload.tool_name):
        return 0
    required_field_issue = payload_required_field_issue(payload)
    if required_field_issue:
        if advisory_enabled(root):
            append_gate_decision(
                root,
                hook="pretooluse",
                payload=payload,
                verdict="would_block",
                reason=f"invalid_payload: {required_field_issue}",
            )
            advisory_message("pretooluse", "invalid_payload")
            return 0
        return block_unclassifiable_payload(required_field_issue)

    if payload.tool_name == CODEX_APPLY_PATCH_TOOL:
        try:
            parsed_apply_patch(payload, root)
        except ApplyPatchParseError as exc:
            reason = f"invalid_apply_patch: {exc}"
            if advisory_enabled(root):
                append_gate_decision(
                    root,
                    hook="pretooluse",
                    payload=payload,
                    verdict="would_block",
                    reason=reason,
                )
                advisory_message("pretooluse", reason)
                return 0
            return block_unclassifiable_payload(
                reason, raw_payload_preview(apply_patch_command(payload))
            )

    if payload.tool_name == "Bash":
        hard_families = raw_hard_policy_families(bash_command(payload))
        try:
            hard_violations = hard_policy_violations(bash_command(payload), root)
        except (
            Exception
        ) as exc:  # noqa: BLE001 - safety classifier failures deny, even in advisory mode.
            hard_violations = [
                f"destructive-operation classifier failed closed ({type(exc).__name__}: {exc})"
            ]
        if hard_violations:
            details = "\n".join(f"  - {violation}" for violation in hard_violations)
            destructive_families = {
                "destructive_git",
                "github_governance",
                "nested_synthesis",
            }
            hard_reason = (
                "destructive_git_operation"
                if hard_families and hard_families <= destructive_families
                else "hard_policy_violation"
            )
            return gate_hard_block(
                root,
                payload,
                "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
                f"Tool: Bash\nCommand: {bash_command(payload)}\n"
                f"Non-overridable violation(s):\n{details}\n\n"
                "Aegis advisory mode relaxes workflow ceremony, not destructive Git or repository-governance safety. "
                "Parser and authority-policy failures are equally non-overridable.",
                reason=hard_reason,
            )

    # No global cwd switch and no arbitrary --root exemption: only the exact
    # opt-in canonical workflow entrypoint may select a journal-bound task.
    from .coordination import (
        registered_target_readiness,
        request as coordination_request,
        target_for,
    )

    coordination_log = False
    seat = root
    try:
        target = target_for(root, payload)
        if target is not None:
            # A delivery target (ga-fsfg R3) has no workflow request.
            parsed = coordination_request(root, payload)
            coordination_log = parsed is not None and parsed[0] in {"log", "discharge"}
            root = target
    except Exception as exc:  # An invalid target must not fall through advisory/override.
        return gate_hard_block(
            root,
            payload,
            f"BLOCKED: coordination target invalid: {exc}",
            reason="coordination_target_invalid",
        )

    clear_client_reload_marker(root, hook_invoking_agent(payload))
    aegis_target_violations: list[str] = []
    if payload.tool_name == "Bash":
        aegis_target_violations = aegis_cli_target_dir_violations(bash_command(payload), root)
    elif is_mcp_tool(payload.tool_name):
        violation = mcp_aegis_target_dir_violation(payload, root)
        if violation:
            aegis_target_violations = [violation]
    if aegis_target_violations:
        details = "\n".join(f"  - {violation}" for violation in aegis_target_violations)
        return gate_block_or_record(
            root,
            payload,
            "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
            f"Tool: {payload.tool_name}\n"
            f"Violation(s):\n{details}\n\n"
            "Aegis read-only target selection is confined to the governed project root.",
            reason="aegis_target_dir_violation",
        )
    if payload_is_read_only(payload):
        return gate_allow_or_record(root, payload, reason="read_only")
    is_mutation = payload_is_mutation(payload)
    readiness = None
    if root != seat:
        try:
            readiness = registered_target_readiness(seat, root)
        except Exception as exc:  # noqa: BLE001 - a registered target that cannot be read is invalid.
            return gate_hard_block(
                root,
                payload,
                f"BLOCKED: coordination target invalid: {exc}",
                reason="coordination_target_invalid",
            )
    if readiness is None:
        readiness = run_readiness(root)
    post_closeout_taskmaster_completion = payload_is_post_closeout_taskmaster_completion(
        root, payload
    )
    post_closeout_delivery = payload_is_post_closeout_delivery(root, payload)
    if current_work_is_observation(root) and is_mutation:
        if payload_is_observation_allowed(payload):
            return gate_allow_or_record(root, payload, reason="observation_allowed")
        return gate_block_or_record(
            root,
            payload,
            "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
            f"Tool: {payload.tool_name}\n"
            "Reason: Aegis observation mode only permits observation tooling.\n\n"
            "Allowed while observing: read-only inspection, dev servers, localhost probes, browser/screenshot MCP tools, aegis log, and aegis observe stop.\n"
            "Blocked while observing: source edits, Taskmaster mutations, git mutations, Aegis closeout/apply paths, and unclassified persistent mutations.\n\n"
            'Stop observation with `./.aegis/bin/aegis observe stop --target-dir . --summary "<summary>"` before implementation work.',
            reason="observation_mode_disallowed_mutation",
        )
    if (
        readiness.returncode == 2
        and is_mutation
        and not payload_is_aegis_bootstrap(payload)
        and not payload_is_aegis_pending_log(payload)
        and not payload_is_aegis_runtime_update(payload)
        and not payload_is_aegis_repair_apply(payload)
        and not payload_is_aegis_enforce(payload)
        and not payload_is_aegis_override(payload)
        and not payload_is_aegis_uninstall_apply(payload)
        and not post_closeout_taskmaster_completion
        and not post_closeout_delivery
    ):
        return gate_block_or_record(
            root,
            payload,
            "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
            f"Tool: {payload.tool_name}\n"
            "Reason: Aegis readiness is BLOCKED, so hookable persistent mutations are refused.\n\n"
            f"{readiness.stdout.strip()}\n\n"
            "Run the kickoff workflow or repair task/session/plan/work-tracking state before mutating files, memory, Git, Taskmaster, or other persistent surfaces.",
            reason="readiness_blocked",
            readiness_state=readiness.stdout.strip(),
        )
    if readiness.returncode not in {0, 2} and is_mutation:
        return gate_block_or_record(
            root,
            payload,
            "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
            f"Tool: {payload.tool_name}\n"
            f"Reason: readiness failed with exit {readiness.returncode}.\n\n"
            f"{readiness.stdout.strip()}\n{readiness.stderr.strip()}",
            reason=f"readiness_error:{readiness.returncode}",
            readiness_state=readiness.stdout.strip(),
        )

    pending_events = required_pending_tracking_events(root)
    if (
        pending_events
        and is_mutation
        and not payload_is_aegis_log(payload)
        and not coordination_log
        and not payload_is_exact_delivery_discharge(payload, pending_events)
    ):
        return gate_block_or_record(
            root,
            payload,
            "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
            f"Tool: {payload.tool_name}\n"
            "Reason: pending S:W:H:E tracking must be logged before another persistent mutation.\n\n"
            f"Pending tracking:\n{format_pending_tracking(pending_events)}\n\n"
            "Run the pending-id repair command above, or use the explicit fallback "
            '`aegis log --handler <handler> --evidence <path-or-command> --note "<past-tense note>"`, '
            "so the active session, tracker, plan, implementation log, changelog, "
            "and handoff all contain the required S:W:H:E entry.",
            reason="pending_tracking",
            readiness_state=readiness.stdout.strip(),
        )

    if payload.tool_name in FILE_MUTATION_TOOLS:
        protected = [
            path for path in file_paths_from_payload(payload, root) if is_protected_path(path, root)
        ]
        if protected:
            paths = "\n".join(f"  - {path}" for path in protected)
            return gate_block_or_record(
                root,
                payload,
                "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
                f"Tool: {payload.tool_name}\n"
                f"Protected path(s):\n{paths}\n\n"
                "Task-scoped agents may not edit protected Aegis-owned or agent-owned paths.",
                reason="protected_path",
            )
        workflow_owned = [
            path
            for path in file_paths_from_payload(payload, root)
            if is_workflow_owned_path(path, root)
        ]
        if workflow_owned:
            paths = "\n".join(f"  - {path}" for path in workflow_owned)
            return gate_block_or_record(
                root,
                payload,
                "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
                f"Tool: {payload.tool_name}\n"
                f"Workflow-owned path(s):\n{paths}\n\n"
                "Agents may not directly edit Aegis authority surfaces. Use sanctioned Aegis commands "
                "such as kickoff, log, handoff repair, or closeout so workflow evidence stays structured.",
                reason="workflow_owned_path",
            )

    if payload.tool_name == "Bash":
        violations = protected_bash_violations(bash_command(payload), root)
        if violations:
            details = "\n".join(f"  - {violation}" for violation in violations)
            return gate_block_or_record(
                root,
                payload,
                "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
                f"Tool: Bash\nCommand: {bash_command(payload)}\n"
                f"Violation(s):\n{details}\n\n"
                "Bash may not be used to bypass protected Aegis/Codex-owned path boundaries.",
                reason="protected_bash_violation",
            )

    if is_mcp_tool(payload.tool_name):
        sanctioned_aegis = payload_is_sanctioned_aegis_workflow_mutation(payload)
        protected = [
            normalize_path(path, root)
            for path in mcp_path_values(payload.tool_input)
            if is_protected_path(path, root)
        ]
        if protected:
            paths = "\n".join(f"  - {path}" for path in sorted(set(protected)))
            return gate_block_or_record(
                root,
                payload,
                "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
                f"Tool: {payload.tool_name}\n"
                f"Protected path(s):\n{paths}\n\n"
                "MCP tools may not bypass protected Aegis/Codex-owned path boundaries.",
                reason="mcp_protected_path",
            )
        workflow_owned = [
            normalize_path(path, root)
            for path in mcp_path_values(payload.tool_input)
            if is_workflow_owned_path(path, root)
        ]
        if workflow_owned and not sanctioned_aegis:
            paths = "\n".join(f"  - {path}" for path in sorted(set(workflow_owned)))
            return gate_block_or_record(
                root,
                payload,
                "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
                f"Tool: {payload.tool_name}\n"
                f"Workflow-owned path(s):\n{paths}\n\n"
                "MCP tools may not directly mutate Aegis authority surfaces. Use sanctioned Aegis MCP "
                "handlers so workflow evidence stays structured.",
                reason="mcp_workflow_owned_path",
            )

    return gate_allow_or_record(root, payload, reason="allow")


def pretooluse_gate_with_degraded_fallback(raw_payload: str) -> int:
    try:
        return pretooluse_gate(raw_payload)
    except Exception as exc:
        return degraded_pretooluse_fallback(raw_payload, exc)
