"""Launch the Template candidate Claude worker with subscription-only authority.

The worker delivers an uncommitted candidate. Publication and signing stay
with the coordinator. It reuses the Core signing worker's exact closed launch
boundary while selecting only the Template candidate policy and dedicated
candidate worktree root.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types
from typing import Sequence

VERSION = 1
MAX_SOURCE_BYTES = 384 * 1024 * 1024


def _stable_source_bytes(path: Path, name: str) -> bytes:
    """Read one local module as the exact bounded source that will execute."""

    try:
        before = path.lstat()
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise RuntimeError(f"{name} source is unreadable") from exc
    try:
        opened_before = os.fstat(descriptor)
        chunks: list[bytes] = []
        remaining = MAX_SOURCE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after = path.lstat()
    except OSError as exc:
        raise RuntimeError(f"{name} source changed while reading") from exc
    if not (
        stat.S_ISREG(before.st_mode)
        and not stat.S_ISLNK(before.st_mode)
        and len(source) <= MAX_SOURCE_BYTES
        and os.path.samestat(before, opened_before)
        and os.path.samestat(opened_before, opened_after)
        and os.path.samestat(opened_after, after)
        and before.st_mode == after.st_mode
        and before.st_size == after.st_size == len(source)
        and before.st_mtime_ns == after.st_mtime_ns
    ):
        raise RuntimeError(f"{name} source is not one stable bounded regular file")
    return source


_CANDIDATE_SOURCE = Path(__file__).resolve()

if __name__ == "__main__" and "_GCT_EXECUTED_TEMPLATE_CANDIDATE_SOURCE" not in globals():
    _source = _stable_source_bytes(_CANDIDATE_SOURCE, "Template candidate worker")
    _namespace = {
        "__name__": "__main__",
        "__file__": str(_CANDIDATE_SOURCE),
        "__package__": None,
        "__builtins__": __builtins__,
        "_GCT_EXECUTED_TEMPLATE_CANDIDATE_SOURCE": _source,
    }
    exec(compile(_source, str(_CANDIDATE_SOURCE), "exec", dont_inherit=True), _namespace)
    raise SystemExit("gct-claude-template-candidate-worker: source bootstrap returned")


_ROOT = _CANDIDATE_SOURCE.parents[1]
_TEMPLATE_COMMON = _ROOT.parent / "gas-city-template" / ".git"
_BOUNDARY_SOURCE = _ROOT / "lib/gct_claude_signing_worker.py"
_EXECUTED_BOUNDARY_SOURCE = _stable_source_bytes(_BOUNDARY_SOURCE, "worker boundary")
boundary = types.ModuleType("_gct_template_candidate_boundary")
boundary.__file__ = str(_BOUNDARY_SOURCE)
boundary.__package__ = ""
sys.modules[boundary.__name__] = boundary
boundary.__dict__["_GCT_EXECUTED_WORKER_SOURCE"] = _EXECUTED_BOUNDARY_SOURCE
exec(
    compile(_EXECUTED_BOUNDARY_SOURCE, str(_BOUNDARY_SOURCE), "exec", dont_inherit=True),
    boundary.__dict__,
)
if "_GCT_EXECUTED_TEMPLATE_CANDIDATE_SOURCE" in globals():
    _EXECUTED_CANDIDATE_SOURCE = globals()["_GCT_EXECUTED_TEMPLATE_CANDIDATE_SOURCE"]
else:
    _EXECUTED_CANDIDATE_SOURCE = _stable_source_bytes(
        _CANDIDATE_SOURCE, "Template candidate worker"
    )
_EXECUTED_SOURCE_DIGESTS = {
    _CANDIDATE_SOURCE: hashlib.sha256(_EXECUTED_CANDIDATE_SOURCE).hexdigest(),
    _BOUNDARY_SOURCE: hashlib.sha256(_EXECUTED_BOUNDARY_SOURCE).hexdigest(),
    **boundary._EXECUTED_SOURCE_DIGESTS,
}

CandidateWorkerError = boundary.SigningWorkerError


def default_config() -> "boundary.LaunchConfig":
    install_root = _ROOT.parent
    return boundary.LaunchConfig(
        claude=install_root / "gascity/bin/claude",
        shared_settings=install_root / "gascity/city/.gc/settings.json",
        control_policy=(
            _ROOT / "templates/claude/template-candidate-control-policy.json"
        ),
        add_dirs=(install_root / "gas-city-template-candidate-worktrees",),
        source_dependencies=(
            _ROOT / "bin/gct-claude-template-candidate-worker",
            _CANDIDATE_SOURCE,
            _BOUNDARY_SOURCE,
            boundary._SUBSCRIPTION_SOURCE,
            _ROOT / "templates/claude/template-candidate-provider.toml",
        ),
    )


def dependency_version(config: "boundary.LaunchConfig") -> str:
    """Return the receipt-pinnable identity of every imported launch input."""

    paths = (config.claude, config.control_policy, *config.source_dependencies)
    if len(set(paths)) != len(paths):
        raise CandidateWorkerError("dependency paths must be unique")
    records = [
        {
            "path": str(path),
            "sha256": _EXECUTED_SOURCE_DIGESTS.get(path)
            or boundary._stable_file_digest(path, f"dependency[{index}]"),
        }
        for index, path in enumerate(paths)
    ]
    domain = json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return (
        f"gct-claude-template-candidate-worker {VERSION} "
        f"dependencies_sha256={hashlib.sha256(domain).hexdigest()}"
    )


def require_candidate_worktree(
    cwd: Path, config: "boundary.LaunchConfig", common: Path
) -> Path:
    """Require one physical linked Template worktree directly below the root."""

    (root,) = config.add_dirs
    if Path(os.path.realpath(cwd)) != cwd or cwd.parent != root:
        raise CandidateWorkerError("session must start in a candidate worktree")
    text = _bounded_regular_text(cwd / ".git")
    prefix = f"gitdir: {common}/worktrees/"
    name = text[len(prefix) : -1] if text.startswith(prefix) and text.endswith("\n") else ""
    if not _WORKTREE_NAME.fullmatch(name) or name in {".", ".."}:
        raise CandidateWorkerError("candidate worktree must be a linked Template worktree")
    admin = common / "worktrees" / name
    for directory in (common / "worktrees", admin):
        try:
            directory_info = directory.lstat()
        except OSError:
            directory_info = None
        if directory_info is None or not stat.S_ISDIR(directory_info.st_mode):
            raise CandidateWorkerError(
                "candidate worktree must be a linked Template worktree"
            )
    if (
        _bounded_regular_text(admin / "gitdir") != f"{cwd}/.git\n"
        or _bounded_regular_text(admin / "commondir") != "../..\n"
    ):
        raise CandidateWorkerError("candidate worktree must be a linked Template worktree")
    return cwd


_WORKTREE_NAME = re.compile(r"[A-Za-z0-9._-]+")
_MAX_GITFILE_BYTES = 4096


def _bounded_regular_text(path: Path) -> str:
    """Return a small regular file's text, or an empty string for any refusal."""

    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        )
    except OSError:
        return ""
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_GITFILE_BYTES:
            return ""
        raw = os.read(descriptor, _MAX_GITFILE_BYTES + 1)
    except OSError:
        return ""
    finally:
        os.close(descriptor)
    if len(raw) > _MAX_GITFILE_BYTES or b"\r" in raw:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def main(arguments: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if arguments is None else arguments)
    config = default_config()
    try:
        if values == ["--version"]:
            print(dependency_version(config))
            return 0
        boundary.launch(
            values,
            parent_environment=os.environ,
            cwd=require_candidate_worktree(Path.cwd(), config, _TEMPLATE_COMMON),
            config=config,
        )
    except (OSError, CandidateWorkerError) as exc:
        print(f"gct-claude-template-candidate-worker: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
