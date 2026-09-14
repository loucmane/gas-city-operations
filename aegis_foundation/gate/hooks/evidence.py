"""Aegis hook gate: evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any

from .contracts import (
    AEGIS_PENDING_TRACKING_REL,
    AEGIS_VERIFY_REPORT_REL,
    ApplyPatchParseError,
    CODEX_APPLY_PATCH_TOOL,
    FILE_MUTATION_TOOLS,
    OBSERVATION_BROWSER_MCP_RE,
    PENDING_TRACKING_SAMPLE_LIMIT,
    Payload,
    SHELL_CONTROL_SPLIT_RE,
    SHELL_REDIRECT_TOKEN_RE,
    TASKMASTER_GENERATE_RE,
    TASKMASTER_SET_STATUS_RE,
    UNSUPPORTED_READ_ONLY_SHELL_RE,
)
from .decisions import enforcement_mode
from .payloads import (
    apply_patch_command,
    apply_patch_event_metadata,
    bash_command,
    command_name,
    file_paths_from_payload,
    is_mcp_tool,
    is_shell_assignment,
    mcp_is_mutation,
    mcp_is_taskmaster_tool,
    mcp_path_values,
    normalize_path,
    normalized_mcp_tool_name,
    option_value,
    safe_expanduser,
    shlex_tokens,
    strip_shell_prefixes,
)
from .runtime_state import (
    current_git_branch,
    current_work,
    current_work_branch_name,
    current_work_closeout_completed,
    pending_tracking_events,
    pending_tracking_path,
    required_pending_tracking_events,
    write_json,
)
from .shell_policy import (
    bash_is_aegis_bootstrap,
    bash_is_aegis_closeout,
    bash_is_aegis_enforce,
    bash_is_aegis_log,
    bash_is_aegis_observe_start,
    bash_is_aegis_observe_stop,
    bash_is_aegis_pending_log,
    bash_is_aegis_repair_apply,
    bash_is_aegis_runtime_update,
    bash_is_aegis_uninstall_apply,
    bash_is_aegis_verify,
    bash_is_delivery_command,
    bash_is_mutation,
    bash_is_observation_tooling,
    bash_is_read_only,
    bash_segment_is_read_only,
    is_persistent_redirect_target,
    mcp_tool_is_aegis_verify,
    payload_is_codex_task_logging,
    redirect_targets,
    workflow_discharge_pending_id,
)


def write_pending_tracking_events(root: Path, events: list[dict[str, Any]]) -> None:
    path = pending_tracking_path(root)
    if not events:
        if path.exists():
            path.unlink()
        return
    write_json(
        path,
        {
            "schema_version": "1.0.0",
            "updated_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "events": events,
        },
    )


def first_redirect_target(command: str, root: Path) -> str | None:
    for target in redirect_targets(command):
        if is_persistent_redirect_target(target):
            return normalize_path(target, root)
    return None


def payload_evidence(payload: Payload, root: Path) -> str:
    if payload.tool_name in FILE_MUTATION_TOOLS:
        paths = file_paths_from_payload(payload, root)
        if paths:
            return paths[0]
    if payload.tool_name == "Bash":
        command = bash_command(payload)
        if bash_is_aegis_verify(command):
            return AEGIS_VERIFY_REPORT_REL
        redirect_target = first_redirect_target(command, root)
        if redirect_target:
            return redirect_target
        return f"cmd`{command}`"
    if is_mcp_tool(payload.tool_name):
        if mcp_tool_is_aegis_verify(payload.tool_name):
            return AEGIS_VERIFY_REPORT_REL
        paths = mcp_path_values(payload.tool_input)
        if paths:
            return normalize_path(paths[0], root)
        return payload.tool_name
    return payload.tool_name or "unknown"


def _path_for_evidence(root: Path, evidence: str) -> Path | None:
    if not evidence or evidence.startswith("cmd`"):
        return None
    candidate = safe_expanduser(evidence)
    if candidate.is_absolute():
        return candidate
    return root / evidence


def _line_count(path: Path) -> int | None:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None


def _display_location(path_text: str, line_start: int | None, line_end: int | None) -> str:
    if line_start is None:
        return path_text
    if line_end is None or line_end == line_start:
        return f"{path_text}:{line_start}"
    return f"{path_text}:{line_start}-{line_end}"


def _snippet_line_range(path: Path, snippet: str) -> tuple[int, int] | None:
    if not snippet:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    offset = text.find(snippet)
    if offset < 0:
        return None
    line_start = text[:offset].count("\n") + 1
    line_span = max(1, len(snippet.splitlines()) or 1)
    return line_start, line_start + line_span - 1


def _file_snapshot_location(root: Path, evidence: str, *, source: str) -> dict[str, Any] | None:
    path = _path_for_evidence(root, evidence)
    if path is None:
        return None
    count = _line_count(path)
    if count is None:
        return {
            "path": evidence,
            "source": source,
            "confidence": "unavailable",
            "display": evidence,
        }
    line_start = 1 if count > 0 else None
    line_end = count if count > 0 else None
    return {
        "path": evidence,
        "line_start": line_start,
        "line_end": line_end,
        "line_count": count,
        "source": source,
        "confidence": "file_snapshot",
        "display": _display_location(evidence, line_start, line_end),
    }


def payload_evidence_location(payload: Payload, root: Path, evidence: str) -> dict[str, Any] | None:
    path = _path_for_evidence(root, evidence)
    if payload.tool_name == CODEX_APPLY_PATCH_TOOL:
        return _file_snapshot_location(root, evidence, source="codex_apply_patch_file_snapshot")
    if payload.tool_name == "Edit" and path is not None:
        new_string = payload.tool_input.get("new_string")
        if isinstance(new_string, str):
            found = _snippet_line_range(path, new_string)
            if found:
                line_start, line_end = found
                return {
                    "path": evidence,
                    "line_start": line_start,
                    "line_end": line_end,
                    "source": "tool_input.new_string",
                    "confidence": "best_effort",
                    "display": _display_location(evidence, line_start, line_end),
                }
        return _file_snapshot_location(root, evidence, source="edit_file_snapshot")

    if payload.tool_name == "MultiEdit" and path is not None:
        edits = payload.tool_input.get("edits")
        ranges: list[dict[str, int]] = []
        if isinstance(edits, list):
            for edit in edits:
                if not isinstance(edit, dict):
                    continue
                new_string = edit.get("new_string")
                if not isinstance(new_string, str):
                    continue
                found = _snippet_line_range(path, new_string)
                if found:
                    ranges.append({"line_start": found[0], "line_end": found[1]})
        if ranges:
            line_start = min(item["line_start"] for item in ranges)
            line_end = max(item["line_end"] for item in ranges)
            return {
                "path": evidence,
                "line_start": line_start,
                "line_end": line_end,
                "ranges": ranges,
                "source": "tool_input.edits.new_string",
                "confidence": "best_effort",
                "display": _display_location(evidence, line_start, line_end),
            }
        return _file_snapshot_location(root, evidence, source="multiedit_file_snapshot")

    if payload.tool_name == "Write":
        return _file_snapshot_location(root, evidence, source="write_file_snapshot")

    if payload.tool_name == "NotebookEdit":
        return _file_snapshot_location(root, evidence, source="notebook_file_snapshot")

    if payload.tool_name == "Bash" and not evidence.startswith("cmd`"):
        return _file_snapshot_location(root, evidence, source="bash_file_snapshot")

    if is_mcp_tool(payload.tool_name) and not evidence.startswith("cmd`"):
        return _file_snapshot_location(root, evidence, source="mcp_file_snapshot")

    return None


def payload_handler(payload: Payload) -> str:
    if payload.tool_name == CODEX_APPLY_PATCH_TOOL:
        return "codex:apply_patch"
    if payload.tool_name == "Bash":
        if bash_is_aegis_verify(bash_command(payload)):
            return "aegis:verify"
        tokens = shlex_tokens(bash_command(payload))
        for token in tokens:
            if is_shell_assignment(token):
                continue
            return f"bash:{token}"
        return "bash"
    if mcp_tool_is_aegis_verify(payload.tool_name):
        return "aegis:verify"
    return f"claude:{payload.tool_name}" if payload.tool_name else "claude:unknown"


def payload_is_aegis_log(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_log(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith("log")
    return False


def payload_is_aegis_observe_start(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_observe_start(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith("observe_start")
    return False


def payload_is_aegis_observe_stop(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_observe_stop(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith("observe_stop")
    return False


def payload_is_aegis_runtime_update(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_runtime_update(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith("runtime_update")
    return False


def payload_is_aegis_repair_apply(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_repair_apply(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = normalized_mcp_tool_name(payload.tool_name)
        return (
            "aegis" in normalized
            and normalized.endswith("aegis_repair")
            and payload.tool_input.get("apply") is True
        )
    return False


def payload_is_aegis_pending_log(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_pending_log(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return (
            "aegis" in normalized
            and normalized.endswith("log")
            and bool(
                payload.tool_input.get("pending_id")
                or payload.tool_input.get("pending-id")
                or payload.tool_input.get("pendingEventId")
            )
        )
    return False


def payload_is_aegis_uninstall_apply(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_uninstall_apply(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return (
            "aegis" in normalized
            and normalized.endswith("uninstall")
            and payload.tool_input.get("apply") is True
        )
    return False


def payload_is_aegis_enforce(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_enforce(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith("enforce")
    return False


def payload_is_mutation(payload: Payload) -> bool:
    if payload.tool_name in FILE_MUTATION_TOOLS:
        return True
    if payload.tool_name == "Bash":
        return bash_is_mutation(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        return mcp_is_mutation(payload)
    return False


def payload_is_read_only(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_read_only(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        return not mcp_is_mutation(payload)
    return False


def payload_is_observation_allowed(payload: Payload) -> bool:
    if payload.tool_name in FILE_MUTATION_TOOLS:
        return False
    if payload_is_read_only(payload):
        return True
    if payload_is_aegis_log(payload) or payload_is_aegis_observe_stop(payload):
        return True
    if payload.tool_name == "Bash":
        command = bash_command(payload)
        return bash_is_observation_tooling(command)
    if is_mcp_tool(payload.tool_name):
        return bool(OBSERVATION_BROWSER_MCP_RE.match(payload.tool_name))
    return False


def payload_is_aegis_bootstrap(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_bootstrap(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith(("start", "kickoff", "observe_start"))
    return False


def payload_is_aegis_closeout(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        return bash_is_aegis_closeout(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith("closeout")
    return False


def bash_is_post_closeout_taskmaster_completion(command: str, task_id: str) -> bool:
    if TASKMASTER_GENERATE_RE.search(command):
        return True
    for match in TASKMASTER_SET_STATUS_RE.finditer(command):
        tokens = shlex_tokens(f"task-master set-status {match.group('args')}")
        status = (option_value(tokens, "--status") or "").strip().lower()
        requested_id = (option_value(tokens, "--id") or "").strip()
        if status in {"done", "completed"} and requested_id == task_id:
            return True
    return False


def command_segments(command: str) -> list[str]:
    return [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]


def cleaned_shell_tokens(segment: str) -> list[str]:
    tokens = strip_shell_prefixes(shlex_tokens(segment))
    return [token for token in tokens if not SHELL_REDIRECT_TOKEN_RE.match(token)]


def shell_args_have_positional(args: list[str], value_options: set[str] | None = None) -> bool:
    value_options = value_options or set()
    skip_next = False
    for token in args:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            if token in value_options:
                skip_next = True
            continue
        return True
    return False


def bash_segment_is_current_branch_push(segment: str, branch: str) -> bool:
    tokens = cleaned_shell_tokens(segment)
    if len(tokens) < 3:
        return False
    if command_name(tokens[0]) != "git" or tokens[1] != "push":
        return False
    if any(
        token in {"-f", "--force", "--force-with-lease", "--mirror", "--all", "--tags", "--delete"}
        or token.startswith("--force-with-lease=")
        for token in tokens[2:]
    ):
        return False
    args = tokens[2:]
    if not args:
        return False
    if args[0] in {"-u", "--set-upstream"}:
        args = args[1:]
    if len(args) != 2:
        return False
    remote, ref = args
    if remote != "origin":
        return False
    return ref in {branch, "HEAD"}


def bash_segment_is_current_branch_pr_create(segment: str, branch: str) -> bool:
    tokens = cleaned_shell_tokens(segment)
    if len(tokens) < 3:
        return False
    if command_name(tokens[0]) != "gh" or tokens[1:3] != ["pr", "create"]:
        return False
    if "--web" in tokens[3:] or option_value(tokens, "--repo") or "-R" in tokens[3:]:
        return False
    head = option_value(tokens, "--head")
    if head:
        return head == branch or head.endswith(f":{branch}")
    return True


def bash_segment_is_current_branch_pr_ready(segment: str, branch: str) -> bool:
    tokens = cleaned_shell_tokens(segment)
    if len(tokens) < 3:
        return False
    if command_name(tokens[0]) != "gh" or tokens[1:3] != ["pr", "ready"]:
        return False
    args = tokens[3:]
    if "--undo" in args or "--web" in args or option_value(tokens, "--repo") or "-R" in args:
        return False
    return not shell_args_have_positional(args, {"--repo", "-R"})


def bash_segment_is_current_branch_pr_merge(segment: str, branch: str) -> bool:
    tokens = cleaned_shell_tokens(segment)
    if len(tokens) < 3:
        return False
    if command_name(tokens[0]) != "gh" or tokens[1:3] != ["pr", "merge"]:
        return False
    args = tokens[3:]
    if "--admin" in args or "--web" in args or option_value(tokens, "--repo") or "-R" in args:
        return False
    if not any(method in args for method in {"--merge", "--squash", "--rebase"}):
        return False
    value_options = {"--subject", "--body", "--body-file", "--author-email", "--match-head-commit"}
    return not shell_args_have_positional(args, value_options)


def bash_is_post_closeout_delivery(command: str, branch: str) -> bool:
    if not branch:
        return False
    if UNSUPPORTED_READ_ONLY_SHELL_RE.search(command):
        return False
    if any(is_persistent_redirect_target(target) for target in redirect_targets(command)):
        return False
    segments = command_segments(command)
    if not segments:
        return False
    first, rest = segments[0], segments[1:]
    if not (
        bash_segment_is_current_branch_push(first, branch)
        or bash_segment_is_current_branch_pr_create(first, branch)
        or bash_segment_is_current_branch_pr_ready(first, branch)
        or bash_segment_is_current_branch_pr_merge(first, branch)
    ):
        return False
    return all(bash_segment_is_read_only(segment) for segment in rest)


def mcp_is_post_closeout_taskmaster_completion(payload: Payload, task_id: str) -> bool:
    normalized = normalized_mcp_tool_name(payload.tool_name)
    if not mcp_is_taskmaster_tool(payload.tool_name):
        return False
    if normalized.endswith("generate"):
        return True
    if not normalized.endswith("set_task_status"):
        return False
    requested_id = str(
        payload.tool_input.get("id")
        or payload.tool_input.get("task_id")
        or payload.tool_input.get("taskId")
        or ""
    ).strip()
    status = str(payload.tool_input.get("status") or "").strip().lower()
    return requested_id == task_id and status in {"done", "completed"}


def payload_is_post_closeout_taskmaster_completion(root: Path, payload: Payload) -> bool:
    work = current_work_closeout_completed(root)
    if work is None or required_pending_tracking_events(root):
        return False
    task = work.get("task") if isinstance(work.get("task"), dict) else {}
    task_id = str(task.get("id") or "").strip()
    if not task_id:
        return False
    if payload.tool_name == "Bash":
        return bash_is_post_closeout_taskmaster_completion(bash_command(payload), task_id)
    if is_mcp_tool(payload.tool_name):
        return mcp_is_post_closeout_taskmaster_completion(payload, task_id)
    return False


def payload_is_post_closeout_delivery(root: Path, payload: Payload) -> bool:
    work = current_work_closeout_completed(root)
    if work is None or required_pending_tracking_events(root):
        return False
    if payload.tool_name != "Bash":
        return False
    branch = current_git_branch(root)
    if not branch:
        return False
    recorded_branch = current_work_branch_name(work)
    if recorded_branch and recorded_branch != branch:
        return False
    return bash_is_post_closeout_delivery(bash_command(payload), branch)


def payload_is_workflow_discharge(payload: Payload) -> bool:
    """One literal task-seat `workflow.py discharge --pending-id <id>` (ga-fsfg R1)."""

    return payload.tool_name == "Bash" and (
        workflow_discharge_pending_id(bash_command(payload)) is not None
    )


def payload_is_exact_delivery_discharge(
    payload: Payload, pending_events: list[dict[str, Any]]
) -> bool:
    """True only when the discharge names exactly one queued delivery-class event."""

    if payload.tool_name != "Bash":
        return False
    pending_id = workflow_discharge_pending_id(bash_command(payload))
    if pending_id is None:
        return False
    matches = [event for event in pending_events if str(event.get("id") or "") == pending_id]
    return len(matches) == 1 and matches[0].get("kind") == "delivery"


def pending_event_kind(payload: Payload) -> str:
    if payload.tool_name == "Bash" and bash_is_delivery_command(bash_command(payload)):
        return "delivery"
    return "mutation"


def record_pending_tracking_event(root: Path, payload: Payload) -> None:
    work = current_work(root)
    if not work:
        return
    if work.get("status") != "in-progress":
        return
    if work.get("mode") == "observation":
        return
    if (
        not payload_is_mutation(payload)
        or payload_is_aegis_bootstrap(payload)
        or payload_is_aegis_runtime_update(payload)
        or payload_is_aegis_log(payload)
        or payload_is_aegis_closeout(payload)
        or payload_is_codex_task_logging(payload)
        or payload_is_workflow_discharge(payload)
    ):
        return
    kind = pending_event_kind(payload)
    handler = payload_handler(payload)
    patch_metadata: dict[str, Any] | None = None
    patch_parse_error: str | None = None
    if payload.tool_name == CODEX_APPLY_PATCH_TOOL:
        try:
            patch_metadata = apply_patch_event_metadata(payload, root)
            evidence = str(patch_metadata["affected_paths"][0])
            evidence_location = payload_evidence_location(payload, root, evidence)
        except ApplyPatchParseError as exc:
            patch_parse_error = str(exc)
            digest = sha256(apply_patch_command(payload).encode("utf-8")).hexdigest()
            patch_metadata = {
                "affected_paths": [],
                "operations": [],
                "patch_digest": digest,
            }
            evidence = f"apply_patch:{digest[:12]}"
            evidence_location = None
    else:
        evidence = payload_evidence(payload, root)
        evidence_location = payload_evidence_location(payload, root, evidence)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    task = work.get("task") if isinstance(work.get("task"), dict) else {}
    task_id = str(task.get("id") or "")
    slug = str(task.get("slug") or "")
    identity_suffix = str(patch_metadata.get("patch_digest")) if patch_metadata else evidence
    event_id = sha1(
        f"{now}|{payload.tool_name}|{handler}|{identity_suffix}".encode("utf-8")
    ).hexdigest()[:12]
    events = pending_tracking_events(root)
    for event in events:
        same_event = event.get("evidence") == evidence and event.get("handler") == handler
        if patch_metadata is not None:
            same_event = event.get("handler") == handler and event.get(
                "patch_digest"
            ) == patch_metadata.get("patch_digest")
        if same_event:
            event["updated_at"] = now
            event.setdefault("kind", kind)
            if enforcement_mode(root) == "strict":
                event["mode"] = "strict"
            if evidence_location:
                event["evidence_location"] = evidence_location
            write_pending_tracking_events(root, events)
            return
    event = {
        "id": event_id,
        "created_at": now,
        "updated_at": now,
        "tool": payload.tool_name,
        "handler": handler,
        "evidence": evidence,
        "kind": kind,
        "task": {
            "id": task_id,
            "slug": slug,
        },
        "mode": enforcement_mode(root),
        "reason": "Mutation requires S:W:H:E entries in sessions/current and active TRACKER.md.",
    }
    if evidence_location:
        event["evidence_location"] = evidence_location
    if patch_metadata is not None:
        event.update(patch_metadata)
    if patch_parse_error is not None:
        event["parse_error"] = patch_parse_error
    events.append(event)
    write_pending_tracking_events(root, events)


def format_pending_tracking(events: list[dict[str, Any]]) -> str:
    lines = []
    for event in events[:PENDING_TRACKING_SAMPLE_LIMIT]:
        event_id = event.get("id", "<unknown>")
        lines.append(
            f"  - {event_id}: H={event.get('handler', '<unknown>')} E={event.get('evidence', '<unknown>')}"
        )
        location = event.get("evidence_location")
        if isinstance(location, dict) and location.get("display"):
            confidence = str(location.get("confidence") or "unknown")
            lines.append(f"    location: {location['display']} ({confidence})")
        lines.append(
            "    repair: ./.aegis/bin/aegis log --pending-id "
            f'{event_id} --note "<past-tense note>" '
            "--plan-step <plan-step-id> --plan-status completed"
        )
    omitted = len(events) - min(len(events), PENDING_TRACKING_SAMPLE_LIMIT)
    if omitted:
        lines.append(
            f"  ... {omitted} more pending events; inspect {AEGIS_PENDING_TRACKING_REL} "
            f"for all {len(events)}."
        )
    return "\n".join(lines)
