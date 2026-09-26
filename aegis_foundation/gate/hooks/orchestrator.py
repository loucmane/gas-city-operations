"""Closed, non-executing command contracts for pre-kickoff orchestration.

Recognition exempts readiness only. It never grants filesystem, ledger, lifecycle,
publication, or operator authority, and never runs the recognized command.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from .payloads import shlex_tokens, strip_shell_prefixes

MANAGED_BIN = Path("/home/loucmane/gascity/bin")
CITY = "/home/loucmane/gascity/city"
WORKFLOW_REL = Path("plugins/gas-city-workflow/scripts/workflow.py")
CONTEXT_REL = Path("plugins/gas-city-workflow/scripts/project_context.py")
WIZARD_REL = Path("scripts/codex-task")
SOURCE_ROOT = Path(__file__).resolve().parents[3]
BEAD = re.compile(r"[a-z][a-z0-9]*-[a-z0-9][a-z0-9-]*(?:\.[1-9][0-9]*)*")
IDENTIFIER = re.compile(r"[a-z][a-z0-9-]*")
# ga-fsfg R4: a qualified Gas City agent name, `<rig>/<agent>`, for example
# `gascity/operations-candidate-worker`.
AGENT = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}/[a-z0-9][a-z0-9._-]{0,127}")
SHELL_SYNTAX = re.compile(r"[\n\r;&|<>`$]")


def _managed_binary(token: str, name: str) -> bool:
    expected = MANAGED_BIN / name
    actual = shutil.which(token) if token == name else token
    # This classifies the exact invocation, not host installation readiness. A
    # missing binary fails at execution; an alternate path/alias gets no exemption.
    return actual == str(expected) and not expected.is_symlink()


def _python(token: str) -> bool:
    actual = shutil.which(token) if token in {"python", "python3"} else token
    allowed = {"/usr/bin/python3", "/bin/python3", "/usr/local/bin/python3", sys.executable}
    return actual in allowed


def _script(token: str, relative: Path, root: Path) -> bool:
    candidate = Path(token)
    if not candidate.is_absolute():
        candidate = root / candidate
    # Do not accept aliases/symlinked scripts even when they resolve to trusted bytes.
    sources = {root.resolve(), SOURCE_ROOT}
    # A linked Operations checkout still advertises the canonical shared runtime.
    # Derive it from Git, never by guessing a sibling directory name.
    common = subprocess.run(
        [
            "/usr/bin/git",
            "-C",
            str(SOURCE_ROOT),
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if common.returncode == 0:
        git_dir = Path(common.stdout.strip())
        if git_dir.name == ".git":
            sources.add(git_dir.parent)
    for source in sources:
        expected = source / relative
        if candidate == expected and expected.is_file() and expected.resolve() == expected:
            return True
    return False


def read_only_utility(tokens: list[str]) -> bool:
    if not tokens or Path(tokens[0]).name not in {"sha256sum", "readlink"}:
        return False
    name = Path(tokens[0]).name
    actual = shutil.which(name) if tokens[0] == name else tokens[0]
    return actual in {f"/usr/bin/{name}", f"/bin/{name}"}


def _options(
    tokens: list[str], *, values: set[str], switches: set[str], repeatable: set[str] = frozenset()
) -> dict[str, list[str]] | None:
    result: dict[str, list[str]] = {}
    index = 0
    while index < len(tokens):
        flag = tokens[index]
        if flag in result and flag not in repeatable:
            return None
        if flag in switches:
            result[flag] = []
        elif flag in values and index + 1 < len(tokens):
            index += 1
            value = tokens[index]
            if not value or value.startswith("-") or SHELL_SYNTAX.search(value):
                return None
            result.setdefault(flag, []).append(value)
        else:
            return None
        index += 1
    return result


def _target_is_current(options: dict[str, list[str]], flag: str, root: Path) -> bool:
    values = options.get(flag)
    if values is None:
        return False
    path = Path(values[0])
    target = path if path.is_absolute() else root / path
    return target.resolve() == root.resolve()


def read_only_beads(tokens: list[str]) -> bool:
    if not tokens or len(tokens) < 2:
        return False
    if _managed_binary(tokens[0], "gc"):
        # The wrapper must select the city and rig explicitly, once and in order.
        if (
            len(tokens) < 7
            or tokens[1:3] != ["--city", CITY]
            or tokens[3] != "--rig"
            or not IDENTIFIER.fullmatch(tokens[4])
            or tokens[5] != "bd"
        ):
            return False
        args = tokens[6:]
    elif _managed_binary(tokens[0], "bd"):
        args = tokens[1:]
    else:
        return False
    verb, *args = args
    if verb not in {"show", "list", "ready"}:
        return False
    if verb == "show":
        if not args or not BEAD.fullmatch(args.pop(0)):
            return False
    switches = {"--json", "--readonly"}
    values: set[str] = set()
    if verb == "list":
        switches |= {"--all", "--no-pager"}
        values |= {"--limit"}
    options = _options(args, values=values, switches=switches)
    if options is None:
        return False
    return "--limit" not in options or bool(re.fullmatch(r"[0-9]+", options["--limit"][0]))


def read_only_context(tokens: list[str], root: Path) -> bool:
    if len(tokens) < 3 or not _python(tokens[0]) or not _script(tokens[1], CONTEXT_REL, root):
        return False
    options = _options(tokens[2:], values={"--root"}, switches={"--check"})
    return (
        options is not None and "--check" in options and _target_is_current(options, "--root", root)
    )


def trusted_bootstrap(command: str, root: Path) -> bool:
    # One invocation only: not a generic exemption for compound shell payloads.
    if SHELL_SYNTAX.search(command):
        return False
    tokens = strip_shell_prefixes(shlex_tokens(command))
    if len(tokens) < 4 or not _python(tokens[0]):
        return False
    if _script(tokens[1], WORKFLOW_REL, root) and tokens[2] == "begin":
        options = _options(
            tokens[3:],
            values={"--root", "--bead", "--slug", "--goal"},
            switches={"--dry-run"},
            repeatable={"--goal"},
        )
        if options is None or not _target_is_current(options, "--root", root):
            return False
    elif _script(tokens[1], WIZARD_REL, root) and tokens[2:4] == ["wizard", "kickoff"]:
        options = _options(
            tokens[4:],
            values={"--bead", "--slug", "--title", "--goal", "--target-dir"},
            switches=set(),
            repeatable={"--goal"},
        )
        if options is None or not {"--bead", "--slug", "--title"} <= options.keys():
            return False
        if "--target-dir" in options and not _target_is_current(options, "--target-dir", root):
            return False
        # The compatibility wizard defaults to its source root, unlike workflow.py.
        if "--target-dir" not in options:
            script = Path(tokens[1])
            if not script.is_absolute():
                script = root / script
            if script != root / WIZARD_REL:
                return False
    else:
        return False
    bead = options.get("--bead", [""])[0]
    slug = options.get("--slug", ["repair"])[0]
    return bool(BEAD.fullmatch(bead) and IDENTIFIER.fullmatch(slug))
