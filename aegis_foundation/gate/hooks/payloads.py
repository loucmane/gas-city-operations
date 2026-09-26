"""Aegis hook gate: payloads."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

from .contracts import (
    AEGIS_READ_ONLY_MCP_TOOL_SUFFIXES,
    APPLY_PATCH_MOVE_RE,
    APPLY_PATCH_PATH_RE,
    ApplyPatchOperation,
    ApplyPatchParseError,
    CODEX_APPLY_PATCH_TOOL,
    HOOKABLE_TOOLS,
    MCP_MUTATION_TOOL_RE,
    MCP_READ_ONLY_TOOL_RE,
    ORCHESTRATOR_ENVIRONMENT,
    ORCHESTRATOR_ENV_UNSET,
    PATH_FIELD_NAMES,
    PROTECTED_EXACT,
    PROTECTED_NAME_PREFIXES,
    PROTECTED_PREFIXES,
    ParsedApplyPatch,
    Payload,
    PayloadLoadError,
    REQUIRED_TOOL_INPUT_FIELDS,
    TASKMASTER_READ_ONLY_MCP_TOOL_SUFFIXES,
    WORKFLOW_LINK_PREFIXES,
    WORKFLOW_REPORT_SEGMENT,
    WORKFLOW_TRACKING_PREFIX,
)
from .decisions import project_root


def raw_payload_preview(raw: str, *, limit: int = 160) -> str:
    preview = raw.replace("\n", "\\n").replace("\r", "\\r")
    if len(preview) > limit:
        return f"{preview[:limit]}..."
    return preview


def parse_payload(raw: str) -> Payload | PayloadLoadError:
    if not raw.strip():
        return Payload(tool_name="", tool_input={})
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return PayloadLoadError(
            reason=f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            raw_preview=raw_payload_preview(raw),
        )
    if not isinstance(data, dict):
        return PayloadLoadError(
            reason=f"hook payload JSON must be an object, got {type(data).__name__}",
            raw_preview=raw_payload_preview(raw),
        )
    tool_name = str(data.get("tool_name") or "")
    if not tool_name and data:
        return PayloadLoadError(
            reason="hook payload missing required field 'tool_name'",
            raw_preview=raw_payload_preview(raw),
        )
    raw_tool_input = data.get("tool_input")
    if raw_tool_input is None:
        tool_input: dict[str, Any] = {}
    elif isinstance(raw_tool_input, dict):
        tool_input = raw_tool_input
    else:
        return PayloadLoadError(
            reason=f"hook payload field 'tool_input' must be an object, got {type(raw_tool_input).__name__}",
            raw_preview=raw_payload_preview(raw),
        )
    return Payload(
        tool_name=str(data.get("tool_name") or ""),
        tool_input=tool_input,
        session_id=str(data["session_id"]) if isinstance(data.get("session_id"), str) else None,
        cwd=str(data["cwd"]) if isinstance(data.get("cwd"), str) else None,
        permission_mode=(
            str(data["permission_mode"]) if isinstance(data.get("permission_mode"), str) else None
        ),
        tool_use_id=str(data["tool_use_id"]) if isinstance(data.get("tool_use_id"), str) else None,
    )


def load_payload_result(raw: str | None = None) -> Payload | PayloadLoadError:
    return parse_payload(sys.stdin.read() if raw is None else raw)


def load_payload() -> Payload | None:
    result = load_payload_result()
    return result if isinstance(result, Payload) else None


def payload_required_field_issue(payload: Payload) -> str | None:
    required_fields = REQUIRED_TOOL_INPUT_FIELDS.get(payload.tool_name)
    if not required_fields:
        return None
    if any(
        isinstance(payload.tool_input.get(field), str) and payload.tool_input.get(field)
        for field in required_fields
    ):
        return None
    fields = ", ".join(required_fields)
    return f"{payload.tool_name} payload missing required input field(s): {fields}"


def safe_expanduser(path_text: str) -> Path:
    """``Path.expanduser`` that survives sandboxed environments (no HOME, no passwd
    entry), where pathlib raises ``RuntimeError: Could not determine home directory``.
    The unexpanded literal is the safe fallback: a ``~``-prefixed path never matches a
    repo-relative protected/workflow path, and home-relative classification elsewhere
    checks the ``~`` prefix textually."""

    path = Path(path_text)
    try:
        return path.expanduser()
    except RuntimeError:
        return path


def normalize_path(path_text: str, root: Path | None = None) -> str:
    if not path_text:
        return ""
    path = safe_expanduser(path_text)
    root = root or project_root()
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return path.as_posix()
    rel = path.as_posix()
    if rel.startswith("./"):
        return rel[2:]
    return rel


def apply_patch_command(payload: Payload) -> str:
    command = payload.tool_input.get("command")
    return command if isinstance(command, str) else ""


def _normalize_apply_patch_path(path_text: str, root: Path) -> str:
    if not path_text:
        raise ApplyPatchParseError("patch path is empty")
    if path_text != path_text.strip():
        raise ApplyPatchParseError("patch path has ambiguous leading or trailing whitespace")
    if any(ord(character) < 32 or ord(character) == 127 for character in path_text):
        raise ApplyPatchParseError("patch path contains control characters")

    root_resolved = root.resolve()
    path = safe_expanduser(path_text)
    if path.is_absolute():
        raise ApplyPatchParseError("patch path must be repository-relative")
    candidate = root_resolved / path
    try:
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(root_resolved).as_posix()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ApplyPatchParseError(f"patch path escapes the governed project: {path_text}") from exc
    if relative in {"", "."}:
        raise ApplyPatchParseError("patch path resolves to the project root")
    return relative


def parse_apply_patch(command: str, root: Path) -> ParsedApplyPatch:
    """Parse the canonical Codex apply_patch envelope without interpreting diff hunks.

    Aegis needs the operation graph and every affected path, not a second patch
    application engine. Structural directives are therefore strict while hunk bodies
    remain opaque after the operation-specific minimum checks below.
    """

    if not command:
        raise ApplyPatchParseError("apply_patch command is empty")
    lines = command.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines or lines[0] != "*** Begin Patch":
        raise ApplyPatchParseError("patch must begin with an exact *** Begin Patch marker")
    if lines[-1] != "*** End Patch":
        raise ApplyPatchParseError("patch must end with an exact *** End Patch marker")
    if any(line == "*** Begin Patch" for line in lines[1:]):
        raise ApplyPatchParseError("nested or duplicate *** Begin Patch marker")
    if any(line == "*** End Patch" for line in lines[1:-1]):
        raise ApplyPatchParseError("early or duplicate *** End Patch marker")

    header_re = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+)$")
    move_re = re.compile(r"^\*\*\* Move to: (.+)$")
    operations: list[ApplyPatchOperation] = []
    current_action: str | None = None
    current_source: str | None = None
    current_destination: str | None = None
    current_body: list[str] = []

    def finalize_current() -> None:
        nonlocal current_action, current_source, current_destination, current_body
        if current_action is None or current_source is None:
            return
        body_has_content = any(line.strip() for line in current_body)
        if current_action == "add":
            if not current_body or not all(line.startswith("+") for line in current_body):
                raise ApplyPatchParseError("Add File requires one or more + content lines")
        elif current_action == "update":
            if not body_has_content and current_destination is None:
                raise ApplyPatchParseError(
                    "Update File requires a hunk body or Move to destination"
                )
        elif current_action == "delete" and body_has_content:
            raise ApplyPatchParseError("Delete File does not accept a patch body")
        operations.append(
            ApplyPatchOperation(
                operation=current_action,
                source_path=current_source,
                destination_path=current_destination,
            )
        )
        current_action = None
        current_source = None
        current_destination = None
        current_body = []

    for line in lines[1:-1]:
        header_match = header_re.fullmatch(line)
        if header_match:
            finalize_current()
            current_action = header_match.group(1).lower()
            current_source = _normalize_apply_patch_path(header_match.group(2), root)
            continue

        move_match = move_re.fullmatch(line)
        if move_match:
            if current_action != "update" or current_source is None:
                raise ApplyPatchParseError("Move to is valid only inside an Update File operation")
            if current_destination is not None:
                raise ApplyPatchParseError("Update File contains more than one Move to directive")
            if any(body_line.strip() for body_line in current_body):
                raise ApplyPatchParseError("Move to must appear before the Update File hunk body")
            current_destination = _normalize_apply_patch_path(move_match.group(1), root)
            if current_destination == current_source:
                raise ApplyPatchParseError("Move to destination must differ from its source path")
            continue

        if line.startswith("*** "):
            raise ApplyPatchParseError(f"unsupported patch directive: {line}")
        if current_action is None:
            if line.strip():
                raise ApplyPatchParseError("patch content appears outside an operation")
            continue
        current_body.append(line)

    finalize_current()
    if not operations:
        raise ApplyPatchParseError("patch contains no file operations")

    affected_paths: list[str] = []
    seen_paths: set[str] = set()
    for operation in operations:
        for path in (operation.source_path, operation.destination_path):
            if path is None:
                continue
            if path in seen_paths:
                raise ApplyPatchParseError(f"patch affects path more than once: {path}")
            seen_paths.add(path)
            affected_paths.append(path)

    return ParsedApplyPatch(
        operations=tuple(operations),
        affected_paths=tuple(affected_paths),
        patch_digest=sha256(command.encode("utf-8")).hexdigest(),
    )


def parsed_apply_patch(payload: Payload, root: Path) -> ParsedApplyPatch:
    if payload.tool_name != CODEX_APPLY_PATCH_TOOL:
        raise ApplyPatchParseError(f"tool is not {CODEX_APPLY_PATCH_TOOL}")
    if payload.parsed_apply_patch is None:
        payload.parsed_apply_patch = parse_apply_patch(apply_patch_command(payload), root)
    return payload.parsed_apply_patch


def apply_patch_event_metadata(payload: Payload, root: Path) -> dict[str, Any]:
    parsed = parsed_apply_patch(payload, root)
    return {
        "affected_paths": list(parsed.affected_paths),
        "operations": [operation.as_event_record() for operation in parsed.operations],
        "patch_digest": parsed.patch_digest,
    }


def is_protected_path(path_text: str, root: Path | None = None) -> bool:
    rel = normalize_path(path_text, root)
    if rel in PROTECTED_EXACT:
        return True
    if rel.startswith(PROTECTED_PREFIXES):
        return True
    return rel.startswith(PROTECTED_NAME_PREFIXES)


def is_workflow_report_path(path_text: str, root: Path | None = None) -> bool:
    rel = normalize_path(path_text, root)
    return rel.startswith(WORKFLOW_TRACKING_PREFIX) and WORKFLOW_REPORT_SEGMENT in f"/{rel}/"


def is_workflow_owned_path(path_text: str, root: Path | None = None) -> bool:
    rel = normalize_path(path_text, root)
    if rel.startswith(WORKFLOW_LINK_PREFIXES):
        return True
    if rel.startswith(WORKFLOW_TRACKING_PREFIX):
        return not is_workflow_report_path(rel, root)
    return False


def is_guarded_mutation_path(path_text: str, root: Path | None = None) -> bool:
    return is_protected_path(path_text, root) or is_workflow_owned_path(path_text, root)


def is_mcp_tool(tool_name: str) -> bool:
    return tool_name.startswith("mcp__")


def normalized_mcp_tool_name(tool_name: str) -> str:
    return tool_name.lower().replace(".", "_").replace("-", "_")


def mcp_is_taskmaster_tool(tool_name: str) -> bool:
    normalized = normalized_mcp_tool_name(tool_name)
    return "taskmaster" in normalized or "task_master" in normalized


def mcp_is_read_only_taskmaster_discovery(payload: Payload) -> bool:
    if not is_mcp_tool(payload.tool_name) or not mcp_is_taskmaster_tool(payload.tool_name):
        return False
    normalized = normalized_mcp_tool_name(payload.tool_name)
    return any(
        normalized.endswith(f"__{suffix}") for suffix in TASKMASTER_READ_ONLY_MCP_TOOL_SUFFIXES
    )


def is_hookable_tool(tool_name: str) -> bool:
    return tool_name in HOOKABLE_TOOLS or is_mcp_tool(tool_name)


def file_paths_from_payload(payload: Payload, root: Path | None = None) -> list[str]:
    if payload.tool_name == CODEX_APPLY_PATCH_TOOL:
        return list(parsed_apply_patch(payload, root or project_root()).affected_paths)
    candidates = [
        payload.tool_input.get("file_path"),
        payload.tool_input.get("notebook_path"),
    ]
    paths: list[str] = []
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            paths.append(normalize_path(candidate, root))
    if payload.tool_name == "apply_patch":
        patch = payload.tool_input.get("command")
        if isinstance(patch, str):
            for candidate in APPLY_PATCH_PATH_RE.findall(patch) + APPLY_PATCH_MOVE_RE.findall(
                patch
            ):
                paths.append(normalize_path(candidate, root))
    return list(dict.fromkeys(paths))


def mcp_path_values(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str) and key.lower() in PATH_FIELD_NAMES and isinstance(nested, str):
                paths.append(nested)
            else:
                paths.extend(mcp_path_values(nested))
    elif isinstance(value, list):
        for nested in value:
            paths.extend(mcp_path_values(nested))
    return paths


def mcp_is_mutation(payload: Payload) -> bool:
    if not is_mcp_tool(payload.tool_name):
        return False
    normalized = normalized_mcp_tool_name(payload.tool_name)
    if "aegis" in normalized and normalized.endswith("runtime_update"):
        return payload.tool_input.get("apply") is True
    if "aegis" in normalized and normalized.endswith("repair"):
        return payload.tool_input.get("apply") is True
    if "aegis" in normalized and normalized.endswith("handoff_repair"):
        return payload.tool_input.get("apply") is True
    if "aegis" in normalized and any(
        normalized.endswith(suffix) for suffix in AEGIS_READ_ONLY_MCP_TOOL_SUFFIXES
    ):
        return mcp_aegis_target_dir_violation(payload) is not None
    if mcp_is_taskmaster_tool(payload.tool_name):
        return not mcp_is_read_only_taskmaster_discovery(payload)
    # Browser-observation tools (chrome-devtools / playwright) drive a live browser, not the
    # project tree (TM 191). They are read-only w.r.t. the repo UNLESS the call writes a repo
    # path (e.g. take_screenshot/save with a path field) — so observation churn (snapshot,
    # click, navigate, console, evaluate) stops arming pending-tracking while a path-bearing
    # write still tracks. Conservative: any repo path field present => treat as a mutation.
    if "__chrome_devtools__" in normalized or "__playwright__" in normalized:
        return bool(mcp_path_values(payload.tool_input))
    if MCP_MUTATION_TOOL_RE.search(payload.tool_name):
        return True
    if MCP_READ_ONLY_TOOL_RE.search(payload.tool_name):
        return False
    # Unknown MCP tools are treated as persistent by default. This is intentionally
    # conservative because MCP tools can mutate remote systems, local files, or memory.
    return True


def bash_command(payload: Payload) -> str:
    command = payload.tool_input.get("command")
    return command if isinstance(command, str) else ""


def shlex_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def option_value(tokens: list[str], option: str) -> str | None:
    for index, token in enumerate(tokens):
        if token == option and index + 1 < len(tokens):
            return tokens[index + 1]
        prefix = f"{option}="
        if token.startswith(prefix):
            return token[len(prefix) :]
    return None


def target_dir_confinement_violation(
    target_dir: str | None, root: Path | None = None
) -> str | None:
    if not target_dir:
        return None
    root = (root or project_root()).resolve()
    raw = safe_expanduser(target_dir)
    try:
        resolved = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    except (OSError, ValueError) as exc:
        return f"target_dir {target_dir!r} could not be resolved safely: {exc}"
    if resolved == root or root in resolved.parents:
        return None
    return (
        "target_dir escapes governed project root "
        f"(target_dir={target_dir!r}, resolved={resolved.as_posix()}, root={root.as_posix()})"
    )


def mcp_aegis_target_dir_violation(payload: Payload, root: Path | None = None) -> str | None:
    if not is_mcp_tool(payload.tool_name):
        return None
    normalized = normalized_mcp_tool_name(payload.tool_name)
    if "aegis" not in normalized:
        return None
    target_dir = payload.tool_input.get("target_dir")
    if not isinstance(target_dir, str):
        return None
    return target_dir_confinement_violation(target_dir, root)


def is_shell_assignment(token: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token))


def command_name(token: str) -> str:
    return Path(token).name


def strip_shell_prefixes(tokens: list[str]) -> list[str]:
    """Strip only reviewed literal environment setup, never arbitrary injection.

    An invalid prefix retains an unrecognized sentinel so it cannot accidentally
    basename to an allowlisted executable. Hard-policy parsing remains separate.
    """
    stripped = list(tokens)
    invalid = ["__aegis_untrusted_environment__", *tokens]
    seen: set[str] = set()

    def assignments() -> bool:
        while stripped and is_shell_assignment(stripped[0]):
            key, value = stripped.pop(0).split("=", 1)
            if key in seen or ORCHESTRATOR_ENVIRONMENT.get(key) != value:
                return False
            seen.add(key)
        return True

    if not assignments():
        return invalid
    if stripped and command_name(stripped[0]) == "env":
        executable = stripped.pop(0)
        if executable == "env":
            path = ORCHESTRATOR_ENVIRONMENT["PATH"] if "PATH" in seen else None
            executable = shutil.which(executable, path=path) or ""
        if executable not in {"/usr/bin/env", "/bin/env"}:
            return invalid
        unset: set[str] = set()
        while stripped and stripped[0] == "-u":
            if len(stripped) < 2 or stripped[1] not in ORCHESTRATOR_ENV_UNSET:
                return invalid
            if stripped[1] in unset:
                return invalid
            unset.add(stripped[1])
            del stripped[:2]
        if not assignments() or (stripped and stripped[0].startswith("-")):
            return invalid
    if seen and not stripped:
        return invalid  # a standalone assignment mutates the shell environment
    if "PATH" in seen and stripped and "/" not in stripped[0]:
        resolved = shutil.which(stripped[0], path=ORCHESTRATOR_ENVIRONMENT["PATH"])
        if resolved:
            stripped[0] = resolved
    return stripped
