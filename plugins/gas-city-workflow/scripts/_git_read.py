"""Git observations without repository-selected subprocesses.

Vendored byte-for-byte as gas-city-workflow/scripts/_git_read.py so the
standalone plugin and installed zipapp use the same policy. See the parity test.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Sequence


def run_git_read(argv: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run only the local read forms used by Obsidian and Continuity.

    Global/system configuration is retained, including safe.directory trust.
    Inherited Git overrides are excluded. Named filter drivers from every scope
    are neutralized before status reads (status can run clean/process filters).
    Config enumeration reads names only and cannot launch a driver itself.
    """
    args = list(argv)
    if not args or args.pop(0) != "git":
        raise ValueError("expected a Git observation")
    location: list[str] = []
    if args[:1] == ["-C"] and len(args) >= 3:
        location, args = args[:2], args[2:]
    if not args:
        raise ValueError("missing Git observation")
    command, *options = args
    allowed = (
        command == "rev-parse"
        or command == "status" and options[:1] == ["--porcelain=v1"]
        or command == "symbolic-ref" and options[:1] == ["--quiet"]
        or command == "rev-list" and options[:2] == ["--left-right", "--count"]
        or command == "merge-base" and options[:1] == ["--is-ancestor"]
        or command == "show" and options[:2] == ["-s", "--format=%H %P"]
        or command == "worktree" and options == ["list", "--porcelain"]
        or command == "branch" and options == ["--show-current"]
        or command == "remote" and options == ["get-url", "origin"]
        or command == "for-each-ref"
        and options == ["--format=%(refname)%00%(objectname)", "refs/heads/codex"]
    )
    if not allowed:
        raise ValueError(f"unsupported Git observation: {command}")
    inherited = kwargs.pop("env", None)
    environment = {
        key: value for key, value in (os.environ if inherited is None else inherited).items()
        if not key.startswith("GIT_")
    }
    environment.update({
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_PAGER": "cat",
    })
    prefix = [
        "git", "--no-pager", "--no-optional-locks", *location,
        "-c", "core.fsmonitor=false",
        "-c", "core.hooksPath=/dev/null",
        "-c", "core.attributesFile=/dev/null",
        "-c", "core.pager=cat",
        "-c", "credential.helper=",
        "-c", "protocol.allow=never",
        "-c", "log.showSignature=false",
        "-c", "submodule.recurse=false",
    ]
    if command == "status":
        index = subprocess.run(
            [*prefix, "ls-files", "--stage", "-z"],
            cwd=kwargs.get("cwd"), env=environment, capture_output=True,
            timeout=kwargs.get("timeout", 30), check=False,
        )
        if index.returncode != 0:
            raise RuntimeError("cannot inspect Git index safely")
        if any(entry.startswith(b"160000 ") for entry in index.stdout.split(b"\0")):
            # A child Git would read a second repository's configuration. Do not
            # silently call a checkout clean after omitting its submodule state.
            raise RuntimeError("Git status with submodules requires a separate safe observation")
        keys = subprocess.run(
            [*prefix, "config", "--null", "--name-only", "--get-regexp",
             r"^filter\..*\.(clean|smudge|process|required)$"],
            cwd=kwargs.get("cwd"), env=environment, capture_output=True,
            timeout=kwargs.get("timeout", 30), check=False,
        )
        if keys.returncode not in {0, 1}:
            raise RuntimeError("cannot enumerate Git filter configuration safely")
        for raw in sorted(set(keys.stdout.split(b"\0")) - {b""}):
            key = os.fsdecode(raw)
            prefix.extend(["-c", key + ("=false" if key.endswith(".required") else "=")])
        # Do not delegate status to submodule Git processes with their own config.
        args.append("--ignore-submodules=all")
    if command == "show":
        args[1:1] = ["--no-ext-diff", "--no-textconv", "--no-show-signature"]
    kwargs.setdefault("timeout", 30)
    return subprocess.run([*prefix, *args], env=environment, **kwargs)
