"""Aegis hook gate: shell policy."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .contracts import (
    AEGIS_LOCAL_BIN_REL,
    CODEX_TASK_LOGGING_SUBCOMMANDS,
    FILE_MUTATION_TOOLS,
    GH_AUTH_SECRET_FLAG_PREFIX,
    GH_AUTH_SECRET_FLAGS,
    GH_INTERACTIVE_FLAG_PREFIX,
    GH_INTERACTIVE_FLAGS,
    GH_SHORT_CLUSTER_RE,
    GIT_LS_REMOTE_POSITIONAL_BOUND,
    GIT_REF_PATTERN_RE,
    GIT_REMOTE_NAME_RE,
    LOCALHOST_URL_RE,
    PYTHON_WRITE_RE,
    Payload,
    READ_ONLY_AEGIS_SUBCOMMANDS,
    READ_ONLY_GH_SUBCOMMANDS,
    READ_ONLY_GIT_FETCH_FLAGS,
    READ_ONLY_GIT_LS_REMOTE_FLAGS,
    READ_ONLY_GIT_SUBCOMMANDS,
    READ_ONLY_NPM_SCRIPTS,
    READ_ONLY_SIMPLE_COMMANDS,
    READ_ONLY_TASKMASTER_SUBCOMMANDS,
    READ_ONLY_WRITE_FLAG_GUARDS,
    REDIRECT_RE,
    SANCTIONED_AEGIS_MCP_MUTATION_SUFFIXES,
    SHELL_CONTROL_SPLIT_RE,
    UNSUPPORTED_READ_ONLY_SHELL_RE,
)
from .decisions import project_root
from .payloads import (
    bash_command,
    command_name,
    is_mcp_tool,
    is_protected_path,
    is_workflow_owned_path,
    mcp_is_mutation,
    normalize_path,
    normalized_mcp_tool_name,
    option_value,
    shlex_tokens,
    strip_shell_prefixes,
    target_dir_confinement_violation,
)
from .hard_policy import has_read_only_test_output_option
from .orchestrator import (
    WORKFLOW_REL,
    _options,
    _python,
    read_only_beads,
    read_only_context,
    read_only_utility,
    trusted_bootstrap,
)


def redirect_targets(command: str) -> list[str]:
    return [match.group(2) for match in REDIRECT_RE.finditer(command)]


def is_persistent_redirect_target(target: str) -> bool:
    return target not in {"/dev/null", "NUL", "nul"}


def bash_is_mutation(command: str) -> bool:
    if not command.strip():
        return False
    if bash_is_read_only(command):
        return False
    # Classification is allowlist-based: anything not proven read-only is a mutation.
    # Keep this explicit instead of presenting an incomplete blocklist as authoritative.
    return True


def read_only_git_segment(tokens: list[str]) -> bool:
    remainder = tokens[1:]
    while remainder and remainder[0].startswith("-"):
        if remainder[0] == "-C" and len(remainder) >= 2:
            remainder = remainder[2:]
        else:
            remainder = remainder[1:]
    if not remainder:
        return False
    if remainder[0] == "branch":
        return "--show-current" in remainder[1:]
    if remainder[0] == "fetch":
        return read_only_git_fetch(remainder[1:])
    if remainder[0] == "ls-remote":
        return read_only_git_ls_remote(remainder[1:])
    return remainder[0] in READ_ONLY_GIT_SUBCOMMANDS


def read_only_git_fetch(args: list[str]) -> bool:
    """Only a refspec-free fetch is observation: it moves remote-tracking refs alone."""

    positionals: list[str] = []
    for token in args:
        if token.startswith("-"):
            if token not in READ_ONLY_GIT_FETCH_FLAGS:
                return False
        else:
            positionals.append(token)
    if len(positionals) > 1:
        return False
    return not any(":" in value or value.startswith("+") for value in positionals)


def read_only_git_ls_remote(args: list[str]) -> bool:
    """Only a plain listing of a configured remote is observation.

    Closed grammar: listed flags, a remote named like a configured remote (never a
    path, URL or `ext::` helper) and plain ref patterns. `--upload-pack`, server
    options and every unlisted flag run or steer a program, so they stay hookable
    mutations.
    """

    positionals: list[str] = []
    for token in args:
        if token.startswith("-"):
            if token not in READ_ONLY_GIT_LS_REMOTE_FLAGS:
                return False
        else:
            positionals.append(token)
    if len(positionals) > GIT_LS_REMOTE_POSITIONAL_BOUND:
        return False
    if positionals and not GIT_REMOTE_NAME_RE.fullmatch(positionals[0]):
        return False
    return all(GIT_REF_PATTERN_RE.fullmatch(pattern) for pattern in positionals[1:])


def read_only_gh_segment(tokens: list[str]) -> bool:
    """Closed `gh` read grammar: listed noun/verb pairs, never a browser or a token."""

    if len(tokens) < 3 or (tokens[1], tokens[2]) not in READ_ONLY_GH_SUBCOMMANDS:
        return False
    for token in tokens[3:]:
        if token in GH_INTERACTIVE_FLAGS or token.startswith(GH_INTERACTIVE_FLAG_PREFIX):
            return False
        cluster = GH_SHORT_CLUSTER_RE.fullmatch(token) is not None
        if cluster and "w" in token:
            return False
        if tokens[1] == "auth" and (
            token in GH_AUTH_SECRET_FLAGS
            or token.startswith(GH_AUTH_SECRET_FLAG_PREFIX)
            or (cluster and "t" in token)
        ):
            return False
    return True


# ga-fsfg R1: delivery-class mutations leave their evidence in Git or GitHub. Their
# pending events discharge into the workflow journal instead of tracked files.
DELIVERY_GIT_SUBCOMMANDS = {"commit", "push"}
DELIVERY_GH_PR_VERBS = {"create", "ready", "merge"}
PENDING_EVENT_ID_RE = re.compile(r"[0-9a-f]{12}")


def bash_is_delivery_command(command: str) -> bool:
    segments = [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]
    if len(segments) != 1:
        return False
    tokens = strip_shell_prefixes(shlex_tokens(segments[0]))
    if not tokens:
        return False
    name = command_name(tokens[0])
    if name == "git":
        remainder = tokens[1:]
        while remainder and remainder[0].startswith("-"):
            if remainder[0] == "-C" and len(remainder) >= 2:
                remainder = remainder[2:]
            else:
                remainder = remainder[1:]
        return bool(remainder) and remainder[0] in DELIVERY_GIT_SUBCOMMANDS
    if name == "gh":
        return len(tokens) >= 3 and tokens[1] == "pr" and tokens[2] in DELIVERY_GH_PR_VERBS
    return False


def workflow_discharge_pending_id(command: str, root: Path | None = None) -> str | None:
    """Return the exact pending id of one literal task-seat `workflow.py discharge`.

    Closed grammar: the governed root's own workflow entrypoint, `--root` naming that
    root, one literal 12-hex `--pending-id`, one `--note`, no shell composition.
    """

    if SHELL_CONTROL_SPLIT_RE.search(command) or UNSUPPORTED_READ_ONLY_SHELL_RE.search(command):
        return None
    root = root or project_root()
    tokens = strip_shell_prefixes(shlex_tokens(command))
    if len(tokens) < 3 or not _python(tokens[0]) or tokens[2] != "discharge":
        return None
    if normalize_path(tokens[1], root) != WORKFLOW_REL.as_posix():
        return None
    options = _options(tokens[3:], values={"--root", "--pending-id", "--note"}, switches=set())
    if options is None or set(options) != {"--root", "--pending-id", "--note"}:
        return None
    if normalize_path(options["--root"][0], root) != ".":
        return None
    pending_id = options["--pending-id"][0]
    if not PENDING_EVENT_ID_RE.fullmatch(pending_id):
        return None
    return pending_id


def read_only_taskmaster_segment(tokens: list[str]) -> bool:
    return len(tokens) >= 2 and tokens[1] in READ_ONLY_TASKMASTER_SUBCOMMANDS


def aegis_cli_remainder(
    tokens: list[str], root: Path | None = None, *, allow_bare: bool = False
) -> list[str] | None:
    if not tokens:
        return None
    root = root or project_root()
    executable = tokens[0]
    if normalize_path(executable, root) == AEGIS_LOCAL_BIN_REL:
        return tokens[1:]
    if executable == "aegis":
        resolved = shutil.which("aegis")
        if resolved and normalize_path(resolved, root) == AEGIS_LOCAL_BIN_REL:
            return tokens[1:]
        return tokens[1:] if allow_bare else None
    if (
        len(tokens) >= 4
        and command_name(executable) in {"python", "python3"}
        and tokens[1:3]
        == [
            "-m",
            "aegis_foundation.cli",
        ]
    ):
        return tokens[3:]
    return None


def read_only_aegis_remainder(remainder: list[str]) -> bool:
    return bool(remainder) and (
        remainder[0] in READ_ONLY_AEGIS_SUBCOMMANDS
        or (len(remainder) >= 2 and remainder[0] == "ledger" and remainder[1] == "path")
        or (len(remainder) >= 2 and remainder[0] == "runtime" and remainder[1] == "status")
        or (
            len(remainder) >= 2
            and remainder[0] == "runtime"
            and remainder[1] == "update"
            and "--apply" not in remainder[2:]
        )
        or (remainder[0] == "closeout" and "--dry-run" in remainder[1:])
        or (remainder[0] == "uninstall" and "--apply" not in remainder[1:])
        or (remainder[0] == "enforce" and "--mode" not in remainder[1:])
    )


def aegis_cli_target_dir_violation_from_remainder(
    remainder: list[str],
    root: Path | None = None,
) -> str | None:
    target_dir = option_value(remainder, "--target-dir")
    return target_dir_confinement_violation(target_dir, root)


def aegis_cli_target_dir_violations(command: str, root: Path | None = None) -> list[str]:
    root = root or project_root()
    violations: list[str] = []
    for segment in [
        segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()
    ]:
        tokens = strip_shell_prefixes(shlex_tokens(segment))
        remainder = aegis_cli_remainder(tokens, root, allow_bare=True)
        if remainder is None:
            continue
        violation = aegis_cli_target_dir_violation_from_remainder(remainder, root)
        if violation:
            violations.append(violation)
    return sorted(set(violations))


def read_only_aegis_segment(tokens: list[str]) -> bool:
    remainder = aegis_cli_remainder(tokens, allow_bare=True)
    if remainder is None:
        return False
    return read_only_aegis_remainder(
        remainder
    ) and not aegis_cli_target_dir_violation_from_remainder(remainder)


def read_only_node_segment(tokens: list[str]) -> bool:
    if len(tokens) >= 2 and tokens[0] in {"npm", "pnpm", "yarn"}:
        if tokens[1] in {"test", "verify"}:
            return not has_read_only_test_output_option(tokens)
        if len(tokens) >= 3 and tokens[1] == "run" and tokens[2] in READ_ONLY_NPM_SCRIPTS:
            return not has_read_only_test_output_option(tokens)
    if tokens[0] == "npx" and len(tokens) >= 2:
        return read_only_node_segment(tokens[1:])
    if tokens[0] == "vitest":
        return not has_read_only_test_output_option(tokens)
    if tokens[0] == "tsc":
        return "--noEmit" in tokens and not has_read_only_test_output_option(tokens)
    return False


def read_only_python_test_segment(tokens: list[str]) -> bool:
    if tokens[0] == "pytest":
        return not has_read_only_test_output_option(tokens)
    if command_name(tokens[0]) in {"python", "python3"}:
        return (
            len(tokens) >= 3
            and tokens[1:3] == ["-m", "pytest"]
            and not has_read_only_test_output_option(tokens)
        )
    if tokens[0] == "uv" and len(tokens) >= 3 and tokens[1] == "run":
        return read_only_python_test_segment(tokens[2:])
    return False


def read_only_find_segment(tokens: list[str]) -> bool:
    return (
        tokens[0] == "find"
        and "-delete" not in tokens
        and "-exec" not in tokens
        and "-execdir" not in tokens
    )


def command_has_write_flag(arg_tokens: list[str], write_flags: tuple[str, ...]) -> bool:
    """Detect a file-mutating flag among a command's args, robust to bundled short
    clusters. A short flag like ``-i`` mutates whether written ``-i``, ``-i.bak``,
    ``-ni`` (bundled with another boolean), or ``-uo`` (cluster ending in a value flag);
    a long flag like ``--inplace`` must match a whole token. Scanning stops at a literal
    ``--`` end-of-options terminator, after which tokens are operands, not flags."""

    short_letters = {
        flag[1:]
        for flag in write_flags
        if flag.startswith("-") and not flag.startswith("--") and len(flag) == 2
    }
    long_flags = {flag for flag in write_flags if flag.startswith("--")}
    for token in arg_tokens:
        if token == "--":
            break
        # Long form, bare or with attached value: --output, --in-place=.bak.
        if token in long_flags or any(token.startswith(flag + "=") for flag in long_flags):
            return True
        if token.startswith("-") and not token.startswith("--"):
            # Alpha prefix of the short cluster, e.g. "-ni"->"ni", "-i.bak"->"i", "-uo"->"uo".
            cluster = ""
            for char in token[1:]:
                if char.isalpha():
                    cluster += char
                else:
                    break
            if any(letter in cluster for letter in short_letters):
                return True
    return False


def bash_segment_is_read_only(segment: str) -> bool:
    tokens = strip_shell_prefixes(shlex_tokens(segment))
    if not tokens:
        return True
    if read_only_beads(tokens) or read_only_utility(tokens) or read_only_context(tokens, project_root()):
        return True
    name = command_name(tokens[0])
    tokens[0] = name
    if name == "cd":
        return True
    if name == "git":
        return read_only_git_segment(tokens)
    if name == "gh":
        return read_only_gh_segment(tokens)
    if name == "task-master":
        return read_only_taskmaster_segment(tokens)
    if read_only_aegis_segment(tokens):
        return True
    if name in READ_ONLY_SIMPLE_COMMANDS:
        write_flags = READ_ONLY_WRITE_FLAG_GUARDS.get(name)
        if write_flags and command_has_write_flag(tokens[1:], write_flags):
            return False
        return True
    if read_only_find_segment(tokens):
        return True
    if read_only_node_segment(tokens):
        return True
    if read_only_python_test_segment(tokens):
        return True
    return False


def bash_is_read_only(command: str) -> bool:
    if not command.strip():
        return True
    if UNSUPPORTED_READ_ONLY_SHELL_RE.search(command):
        return False
    if any(is_persistent_redirect_target(target) for target in redirect_targets(command)):
        return False
    segments = [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]
    return bool(segments) and all(bash_segment_is_read_only(segment) for segment in segments)


def npm_command_words(tokens: list[str]) -> list[str]:
    words: list[str] = []
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token in {"-C", "--prefix", "--cwd", "--dir", "--filter", "--workspace"}:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        words.append(token)
    return words


def localhost_probe_segment(tokens: list[str]) -> bool:
    if tokens[0] == "curl":
        curl_file_output_flags = {
            "--cookie-jar",
            "--config",
            "--dump-header",
            "--etag-save",
            "--output",
            "--output-dir",
            "--remote-header-name",
            "--remote-name",
            "--remote-name-all",
            "--trace",
            "--trace-ascii",
        }
        for token in tokens[1:]:
            if token in curl_file_output_flags or any(
                token.startswith(f"{flag}=") for flag in curl_file_output_flags
            ):
                return False
            if token in {"-D", "-J", "-K", "-O", "-o", "-c"}:
                return False
            if (
                token.startswith("-D")
                or token.startswith("-K")
                or token.startswith("-o")
                or token.startswith("-c")
            ):
                return False
            if token.startswith("-") and "O" in token[1:]:
                return False
        return any(LOCALHOST_URL_RE.match(token) for token in tokens[1:])
    if tokens[0] == "wget":
        stdout = False
        for index, token in enumerate(tokens[1:], start=1):
            if token == "-O" and index + 1 < len(tokens) and tokens[index + 1] == "-":
                stdout = True
            elif token == "-O-":
                stdout = True
            elif token == "--output-document=-":
                stdout = True
            elif token.startswith("--output-document="):
                return False
            elif token == "--output-document":
                return False
            elif token in {"-e", "--config"} or token.startswith("--config="):
                return False
            elif token.startswith("-O") and token != "-O-":
                return False
        return stdout and any(LOCALHOST_URL_RE.match(token) for token in tokens[1:])
    if tokens[0] not in {"curl", "wget"}:
        return False
    return False


def dev_server_segment(tokens: list[str]) -> bool:
    name = tokens[0]
    if name in {"npm", "pnpm", "yarn", "bun"}:
        words = npm_command_words(tokens)
        if not words:
            return False
        if words[0] in {"dev", "start"}:
            return True
        return len(words) >= 2 and words[0] == "run" and words[1] in {"dev", "start"}
    if name in {"vite", "next", "astro", "wrangler"}:
        return len(tokens) >= 2 and tokens[1] in {"dev", "start"}
    return False


def bash_segment_is_observation_tooling(segment: str) -> bool:
    tokens = strip_shell_prefixes(shlex_tokens(segment))
    if not tokens:
        return True
    name = command_name(tokens[0])
    tokens[0] = name
    if bash_segment_is_read_only(segment):
        return True
    return dev_server_segment(tokens) or localhost_probe_segment(tokens)


def bash_is_observation_tooling(command: str) -> bool:
    if not command.strip():
        return True
    if any(is_persistent_redirect_target(target) for target in redirect_targets(command)):
        return False
    segments = [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]
    return bool(segments) and all(
        bash_segment_is_observation_tooling(segment) for segment in segments
    )


def degraded_bash_segment_is_non_destructive(segment: str) -> bool:
    return bash_segment_is_read_only(segment)


def degraded_bash_is_non_destructive(command: str) -> bool:
    return bash_is_read_only(command)


def degraded_payload_is_non_destructive(payload: Payload) -> bool:
    try:
        if payload.tool_name in FILE_MUTATION_TOOLS:
            return False
        if payload.tool_name == "Bash":
            return degraded_bash_is_non_destructive(bash_command(payload))
        if is_mcp_tool(payload.tool_name):
            return not mcp_is_mutation(payload)
        return not payload.tool_name
    except Exception:  # noqa: BLE001 - degraded mode must fail closed on classifier faults.
        return False


def bash_is_aegis_bootstrap(command: str) -> bool:
    return trusted_bootstrap(command, project_root()) or bash_has_trusted_aegis_subcommand(
        command, {"start", "kickoff"}
    ) or bash_is_aegis_observe_start(command)


def bash_is_aegis_log(command: str) -> bool:
    return bash_has_trusted_aegis_subcommand(command, {"log"})


def codex_task_remainder(tokens: list[str], root: Path | None = None) -> list[str] | None:
    """Return the subcommand tokens after a `scripts/codex-task` invocation, else None."""

    if len(tokens) < 2:
        return None
    root = root or project_root()
    if command_name(tokens[0]) not in {"python", "python3"}:
        return None
    if normalize_path(tokens[1], root) == "scripts/codex-task":
        return tokens[2:]
    return None


def _segment_is_codex_task_logging(segment: str) -> bool:
    tokens = strip_shell_prefixes(shlex_tokens(segment))
    remainder = codex_task_remainder(tokens)
    return (
        bool(remainder)
        and len(remainder) >= 2
        and (remainder[0], remainder[1]) in CODEX_TASK_LOGGING_SUBCOMMANDS
    )


def bash_is_codex_task_logging(command: str) -> bool:
    """Whole-payload-AND: a codex-task logging command excludes the payload from
    pending-tracking only when every other segment is read-only. Without this,
    ``codex-task plan sync; rm -rf src`` would exclude the whole payload and let the
    mutation escape (TM 216 adversarial review)."""

    saw_logging = False
    for segment in [
        segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()
    ]:
        if _segment_is_codex_task_logging(segment):
            saw_logging = True
        elif not bash_is_read_only(segment):
            return False
    return saw_logging


def payload_is_codex_task_logging(payload: Payload) -> bool:
    return payload.tool_name == "Bash" and bash_is_codex_task_logging(bash_command(payload))


def bash_is_aegis_pending_log(command: str) -> bool:
    return bash_has_trusted_aegis_subcommand(command, {"log"}, required_option="--pending-id")


def bash_is_aegis_uninstall_apply(command: str) -> bool:
    return bash_has_trusted_aegis_subcommand(command, {"uninstall"}, require_apply=True)


def bash_is_aegis_verify(command: str) -> bool:
    return bash_has_trusted_aegis_subcommand(command, {"verify"})


def bash_is_aegis_observe_start(command: str) -> bool:
    return bash_has_trusted_aegis_nested_subcommand(command, "observe", {"start"})


def bash_is_aegis_observe_stop(command: str) -> bool:
    return bash_has_trusted_aegis_nested_subcommand(command, "observe", {"stop"})


def bash_is_aegis_runtime_update(command: str) -> bool:
    return bash_has_trusted_aegis_nested_subcommand(command, "runtime", {"update"})


def bash_is_aegis_enforce(command: str) -> bool:
    segments = [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]
    if len(segments) != 1:
        return False
    tokens = strip_shell_prefixes(shlex_tokens(segments[0]))
    remainder = aegis_cli_remainder(tokens, project_root(), allow_bare=False)
    return bool(remainder) and remainder[0] == "enforce"


def bash_is_aegis_override(command: str) -> bool:
    segments = [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]
    if len(segments) != 1:
        return False
    tokens = strip_shell_prefixes(shlex_tokens(segments[0]))
    remainder = aegis_cli_remainder(tokens, project_root(), allow_bare=False)
    return bool(remainder) and remainder[0] == "override"


def payload_is_aegis_override(payload: Payload) -> bool:
    """Minting a break-glass token must itself run while BLOCKED (TM #201).

    It writes only `.aegis/state/override-token.json` and is rate-limited + audited; it
    does not perform the user's mutation, so sanctioning it is not a bypass.
    """

    if payload.tool_name == "Bash":
        return bash_is_aegis_override(bash_command(payload))
    if is_mcp_tool(payload.tool_name):
        normalized = payload.tool_name.lower().replace(".", "_").replace("-", "_")
        return "aegis" in normalized and normalized.endswith("override")
    return False


def mcp_tool_is_aegis_verify(tool_name: str) -> bool:
    if not is_mcp_tool(tool_name):
        return False
    normalized = tool_name.lower().replace(".", "_").replace("-", "_")
    return "aegis" in normalized and normalized.endswith("verify")


def bash_is_aegis_closeout(command: str) -> bool:
    return bash_has_trusted_aegis_subcommand(command, {"closeout"})


def _segment_is_trusted_aegis(
    segment: str,
    subcommands: set[str],
    root: Path,
    *,
    require_apply: bool,
    required_option: str | None,
    handoff_repair: bool,
) -> bool:
    tokens = strip_shell_prefixes(shlex_tokens(segment))
    remainder = aegis_cli_remainder(tokens, root, allow_bare=False)
    if not remainder:
        return False
    if handoff_repair:
        return len(remainder) >= 2 and remainder[0] == "handoff" and remainder[1] == "repair"
    if remainder[0] not in subcommands:
        return False
    if require_apply and "--apply" not in remainder[1:]:
        return False
    if required_option and required_option not in remainder[1:]:
        return False
    return True


def bash_has_trusted_aegis_subcommand(
    command: str,
    subcommands: set[str],
    *,
    require_apply: bool = False,
    required_option: str | None = None,
    handoff_repair: bool = False,
) -> bool:
    """A compound command is a trusted aegis invocation only when at least one segment
    is the trusted subcommand AND every other segment is itself read-only. Otherwise a
    real mutation chained with a sanctioned command (``aegis log && rm -rf src``) would
    be wrongly trusted — escaping both the readiness gate and pending-tracking (TM 216
    adversarial review)."""

    root = project_root()
    saw_trusted = False
    for segment in [
        segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()
    ]:
        if _segment_is_trusted_aegis(
            segment,
            subcommands,
            root,
            require_apply=require_apply,
            required_option=required_option,
            handoff_repair=handoff_repair,
        ):
            saw_trusted = True
        elif not bash_is_read_only(segment):
            return False
    return saw_trusted


def bash_is_aegis_repair_apply(command: str) -> bool:
    segments = [segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()]
    if len(segments) != 1:
        return False
    tokens = strip_shell_prefixes(shlex_tokens(segments[0]))
    remainder = aegis_cli_remainder(tokens, project_root(), allow_bare=False)
    return bool(remainder) and remainder[0] == "repair" and "--apply" in remainder[1:]


def bash_has_trusted_aegis_nested_subcommand(
    command: str,
    first: str,
    seconds: set[str],
) -> bool:
    """Whole-payload-AND, like bash_has_trusted_aegis_subcommand: a trusted nested
    invocation only when every non-trusted segment is read-only."""

    root = project_root()
    saw_trusted = False
    for segment in [
        segment for segment in SHELL_CONTROL_SPLIT_RE.split(command) if segment.strip()
    ]:
        tokens = strip_shell_prefixes(shlex_tokens(segment))
        remainder = aegis_cli_remainder(tokens, root, allow_bare=False)
        if len(remainder or []) >= 2 and remainder[0] == first and remainder[1] in seconds:
            saw_trusted = True
        elif not bash_is_read_only(segment):
            return False
    return saw_trusted


def payload_is_sanctioned_aegis_workflow_mutation(payload: Payload) -> bool:
    if payload.tool_name == "Bash":
        command = bash_command(payload)
        return (
            bash_is_aegis_bootstrap(command)
            or bash_is_aegis_log(command)
            or bash_is_aegis_verify(command)
            or bash_is_aegis_closeout(command)
            or bash_is_aegis_runtime_update(command)
            or bash_is_aegis_enforce(command)
            or bash_has_trusted_aegis_subcommand(command, {"repair"}, require_apply=True)
            or bash_has_trusted_aegis_subcommand(command, set(), handoff_repair=True)
        )
    if is_mcp_tool(payload.tool_name):
        normalized = normalized_mcp_tool_name(payload.tool_name)
        return "aegis" in normalized and any(
            normalized.endswith(suffix) for suffix in SANCTIONED_AEGIS_MCP_MUTATION_SUFFIXES
        )
    return False


def guarded_bash_path_violation(action: str, target: str, root: Path) -> str | None:
    normalized = normalize_path(target, root)
    if is_protected_path(target, root):
        return f"{action} protected path {normalized}"
    if is_workflow_owned_path(target, root):
        return f"{action} workflow-owned path {normalized}"
    return None


def protected_bash_violations(command: str, root: Path | None = None) -> list[str]:
    root = root or project_root()
    violations: list[str] = []
    violations.extend(aegis_cli_target_dir_violations(command, root))

    for match in REDIRECT_RE.finditer(command):
        target = match.group(2)
        if not is_persistent_redirect_target(target):
            continue
        violation = guarded_bash_path_violation("redirection targets", target, root)
        if violation:
            violations.append(violation)

    tokens = shlex_tokens(command)
    for index, token in enumerate(tokens):
        lower = token.lower()
        if lower == "sed" and "-i" in tokens[index + 1 : index + 4]:
            for candidate in tokens[index + 1 :]:
                if candidate.startswith("-") or candidate.startswith("s/"):
                    continue
                violation = guarded_bash_path_violation("sed -i targets", candidate, root)
                if violation:
                    violations.append(violation)
        if lower == "tee":
            for candidate in tokens[index + 1 :]:
                if candidate.startswith("-"):
                    continue
                violation = guarded_bash_path_violation("tee targets", candidate, root)
                if violation:
                    violations.append(violation)
        if lower in {"rm", "mv", "cp", "install", "touch", "chmod", "chown", "mkdir", "rmdir"}:
            for candidate in tokens[index + 1 :]:
                if candidate.startswith("-"):
                    continue
                violation = guarded_bash_path_violation(f"{lower} references", candidate, root)
                if violation:
                    violations.append(violation)

    for match in PYTHON_WRITE_RE.finditer(command):
        target = match.group(1)
        if target:
            violation = guarded_bash_path_violation("python write targets", target, root)
            if violation:
                violations.append(violation)

    return sorted(set(violations))
