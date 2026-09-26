"""Hardened Git and gh reads for the delivery class (ga-fsfg R3).

Every read runs an absolute binary with a fixed environment, and its timeout is
the smaller of 30 seconds and the time left before the hook-entry deadline. Any
failed or late read refuses. `run_checks` is step 4 of the evaluation; the
configuration check (step 3) is `config_refusals`.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .delivery_grammar import GH, GIT, PR_CREATE, PR_MERGE, DeliveryRequest, branch_violation
from .delivery_worktree import OBJECT_ID, Checkout, head_branch, read_bounded

clock = time.monotonic
READ_TIMEOUT = 30.0
# Every delivery Git read: no replace objects, no commit-graph, no hooks, no
# filesystem monitor, no attributes file, and only the OpenPGP verifier.
GIT_BASE = ("--no-optional-locks", "--no-replace-objects")
GIT_HARDENING = (
    "-c",
    "core.commitGraph=false",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.attributesFile=/dev/null",
    "-c",
    "gpg.program=/usr/bin/gpg",
    "-c",
    "gpg.ssh.program=/bin/false",
    "-c",
    "gpg.x509.program=/bin/false",
)
# Change detection pinned to Git's defaults, as the reviewer binding does.
STATUS_PINS = (
    "-c",
    "core.checkStat=default",
    "-c",
    "core.trustctime=true",
    "-c",
    "core.ignoreCase=false",
    "-c",
    "core.fileMode=true",
    "-c",
    "core.untrackedCache=false",
)
PGP_ARMOR = b"-----BEGIN PGP SIGNATURE-----"
MAX_COMMITS = 1000
MAX_BODY_BYTES = 64 * 1024
MAX_ATTRIBUTES_BYTES = 1024 * 1024
MAX_ROLLUP = 100
STANDARD_FETCH = "+refs/heads/*:refs/remotes/origin/*"
JUDGED_SECTIONS = frozenset(
    {
        "remote",
        "url",
        "push",
        "credential",
        "http",
        "protocol",
        "gpg",
        "filter",
        "diff",
        "merge",
        "submodule",
        "hook",
    }
)
JUDGED_CORE = frozenset(
    {
        "core.sshcommand",
        "core.askpass",
        "core.hookspath",
        "core.gitproxy",
        "core.fsmonitor",
        "core.alternaterefscommand",
        "core.attributesfile",
    }
)
# The global git-lfs entries exactly as they are live; no attribute may select them.
ALLOWED_ENTRIES = frozenset(
    {
        ("push.autosetupremote", "true"),
        ("gpg.program", "/usr/bin/gpg"),
        ("filter.lfs.clean", "git-lfs clean -- %f"),
        ("filter.lfs.smudge", "git-lfs smudge -- %f"),
        ("filter.lfs.process", "git-lfs filter-process"),
        ("filter.lfs.required", "true"),
    }
)
DRIVER_SELECTORS = (b"filter=", b"diff=", b"merge=")
ATTRIBUTES_PATHSPEC = ":(glob)**/.gitattributes"
PR_FIELDS = "state,baseRefName,headRefName,headRefOid,isCrossRepository,statusCheckRollup"


class DeliveryRefusal(ValueError):
    """A delivery precondition failed, so the gate refuses the call."""


@dataclass
class Reader:
    """Bounded Git and gh reads sharing one hook-entry deadline."""

    home: str
    path: str
    deadline: float

    def remaining(self) -> float:
        left = self.deadline - clock()
        if left <= 0:
            raise DeliveryRefusal("delivery evaluation exceeded its deadline")
        return left

    def timeout(self) -> float:
        return min(READ_TIMEOUT, self.remaining())

    def git_environment(self) -> dict[str, str]:
        return {
            "HOME": self.home,
            "PATH": self.path,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_ATTR_NOSYSTEM": "1",
        }

    def gh_environment(self) -> dict[str, str]:
        return {"HOME": self.home, "PATH": self.path}

    def git(self, cwd: Path, *args: str, hardened: bool = True, stdin: bytes = b"") -> bytes:
        options = (*GIT_BASE, *GIT_HARDENING) if hardened else GIT_BASE
        argv = [GIT, *options, "-C", str(cwd), *args]
        subcommand = next((word for word in args if word[:1] != "-" and "=" not in word), "")
        return self._run(argv, cwd, self.git_environment(), stdin, f"git {subcommand}")

    def gh(self, cwd: Path, *args: str) -> bytes:
        return self._run([GH, *args], cwd, self.gh_environment(), b"", f"gh {' '.join(args[:2])}")

    def _run(
        self, argv: list[str], cwd: Path, env: dict[str, str], stdin: bytes, label: str
    ) -> bytes:
        timeout = self.timeout()
        try:
            result = subprocess.run(
                argv,
                cwd=str(cwd),
                env=env,
                input=stdin,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeliveryRefusal(f"delivery read failed or ran late: {label}") from exc
        if result.returncode != 0:
            raise DeliveryRefusal(f"delivery read failed: {label}")
        return result.stdout


def branch_format_accepted(name: str, cwd: Path) -> bool:
    """`git check-ref-format --branch` for a profile field (not a delivery read)."""

    try:
        result = subprocess.run(
            [GIT, "check-ref-format", "--branch", name],
            cwd=str(cwd),
            env={"PATH": "/usr/bin:/bin"},
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.decode("utf-8", "replace").strip() == name


def parse_config(raw: bytes) -> list[tuple[str, str, str | None]]:
    """Parse `git config --list --show-scope --null` into (scope, key, value) entries."""

    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 2:
        raise DeliveryRefusal("delivery configuration listing is malformed")
    entries = []
    for scope, item in zip(fields[0::2], fields[1::2]):
        try:
            text = item.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DeliveryRefusal("delivery configuration is not UTF-8") from exc
        key, newline, value = text.partition("\n")
        entries.append((scope.decode("ascii", "replace"), key, value if newline else None))
    return entries


def config_refusals(
    entries: list[tuple[str, str, str | None]], profile: dict[str, Any]
) -> list[str]:
    """Judge the effective configuration over the delivery namespaces; list refused keys."""

    refused: list[str] = []
    credentials: list[dict[str, str | None]] = []
    urls = fetches = 0
    for _scope, key, value in entries:
        lowered = key.lower()
        if lowered.partition(".")[0] not in JUDGED_SECTIONS and lowered not in JUDGED_CORE:
            continue
        if lowered.startswith("credential."):
            credentials.append({"key": key, "value": value})
        elif key == "remote.origin.url" and value == profile["remote_url"]:
            urls += 1
        elif key == "remote.origin.fetch" and value == STANDARD_FETCH:
            fetches += 1
        elif (key, value) not in ALLOWED_ENTRIES:
            refused.append(key)
    if urls != 1:
        refused.append("remote.origin.url")
    if fetches != 1:
        refused.append("remote.origin.fetch")
    if credentials != profile["credential_helpers"]:
        refused.append("credential.*")
    return sorted(set(refused))


def hooks_violation(directories: tuple[Path, ...]) -> str | None:
    """Only git's regular `*.sample` files may sit in a hooks directory (by lstat)."""

    for directory in directories:
        hooks = directory / "hooks"
        try:
            info = os.lstat(hooks)
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(info.st_mode):
            return f"hooks path {hooks} is not a plain directory"
        with os.scandir(hooks) as entries:
            for entry in entries:
                mode = entry.stat(follow_symlinks=False).st_mode
                if not (stat.S_ISREG(mode) and entry.name.endswith(".sample")):
                    return f"hook {entry.name} is installed in {hooks}"
    return None


def history_violation(reader: Reader, root: Path, common: Path) -> str | None:
    if reader.git(root, "for-each-ref", "--format=%(refname)", "refs/replace/").strip():
        return "a replace ref could rewrite history"
    for name in ("info/grafts", "shallow"):
        if os.path.lexists(common / name):
            return f"{name} could rewrite history"
    return None


def _batch(reader: Reader, root: Path, objects: list[str]) -> Iterator[tuple[str, str, bytes]]:
    if not objects:
        return
    listing = "".join(f"{oid}\n" for oid in objects).encode()
    data = reader.git(root, "cat-file", "--batch", stdin=listing)
    offset = 0
    while offset < len(data):
        end = data.index(b"\n", offset)
        fields = data[offset:end].decode("ascii", "replace").split(" ")
        if len(fields) != 3 or not fields[2].isdigit():
            raise DeliveryRefusal("delivery object read returned a missing object")
        size = int(fields[2])
        yield fields[0], fields[1], data[end + 1 : end + 1 + size]
        offset = end + 1 + size + 1


def global_attribute_files(profile: dict[str, Any]) -> list[Path]:
    files = [Path(profile["delivery_home"]) / ".config/git/attributes"]
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg and Path(xdg).is_absolute():
        files.append(Path(xdg) / "git/attributes")
    return files


def attributes_violation(
    reader: Reader, root: Path, directories: tuple[Path, ...], profile: dict[str, Any]
) -> str | None:
    """No attribute may select a filter, diff or merge driver; no gitlink in HEAD."""

    for directory in directories:
        if os.path.lexists(directory / "info" / "attributes"):
            return f"{directory / 'info/attributes'} is present"
    for path in global_attribute_files(profile):
        if os.path.lexists(path):
            return f"global attributes file {path} is present"
    blobs: list[str] = []
    for record in reader.git(root, "ls-tree", "-r", "-z", "--full-tree", "HEAD").split(b"\0"):
        if not record:
            continue
        meta, _, name = record.partition(b"\t")
        mode, _kind, oid = meta.decode("ascii").split(" ")
        if mode == "160000":
            return f"gitlink {name.decode('utf-8', 'replace')} is present in HEAD"
        if name == b".gitattributes" or name.endswith(b"/.gitattributes"):
            blobs.append(oid)
    paths: list[bytes] = []
    staged = reader.git(root, "ls-files", "-z", "-s", "--", ATTRIBUTES_PATHSPEC)
    for record in staged.split(b"\0"):
        if record:
            meta, _, name = record.partition(b"\t")
            blobs.append(meta.decode("ascii").split(" ")[1])
            paths.append(name)
    others = reader.git(root, "ls-files", "-z", "--others", "--", ATTRIBUTES_PATHSPEC)
    paths.extend(name for name in others.split(b"\0") if name)
    for _oid, _kind, content in _batch(reader, root, sorted(set(blobs))):
        if any(selector in content for selector in DRIVER_SELECTORS):
            return "a committed or staged .gitattributes selects a driver"
    for name in paths:
        path = root / os.fsdecode(name)
        if not os.path.lexists(path):
            continue
        content = read_bounded(path, MAX_ATTRIBUTES_BYTES)
        if content is None:
            return f"{path} is not a bounded regular file"
        if any(selector in content for selector in DRIVER_SELECTORS):
            return f"{path} selects a driver"
    return None


def origin_violation(reader: Reader, root: Path, profile: dict[str, Any]) -> str | None:
    urls = reader.git(root, "remote", "get-url", "--push", "--all", "origin")
    if urls.decode("utf-8", "replace").splitlines() != [profile["remote_url"]]:
        return "origin push URL is not exactly remote_url"
    return None


def remote_object(reader: Reader, root: Path, ref: str) -> str:
    """The object `git ls-remote origin <ref>` names in exactly one line for exactly `ref`."""

    lines = reader.git(root, "ls-remote", "origin", ref).decode("ascii", "replace").splitlines()
    if len(lines) != 1:
        raise DeliveryRefusal(f"ls-remote origin did not return exactly one {ref}")
    oid, tab, name = lines[0].partition("\t")
    if not tab or name != ref or not OBJECT_ID.fullmatch(oid):
        raise DeliveryRefusal(f"ls-remote origin did not name exactly {ref}")
    return oid


def _signature_header(raw: bytes) -> bytes | None:
    headers = raw.split(b"\n\n", 1)[0].split(b"\n")
    signatures = [line[len(b"gpgsig ") :] for line in headers if line.startswith(b"gpgsig ")]
    return signatures[0] if len(signatures) == 1 else None


def signature_violation(reader: Reader, root: Path, base: str, key: str) -> str | None:
    """Every commit in base..HEAD carries an OpenPGP signature good by exactly `key`."""

    listing = reader.git(root, "rev-list", f"--max-count={MAX_COMMITS + 1}", f"{base}..HEAD")
    commits = listing.decode("ascii", "replace").split()
    if len(commits) > MAX_COMMITS:
        return "too many commits to verify"
    if not commits:
        return None
    for oid, kind, raw in _batch(reader, root, commits):
        if kind != "commit" or _signature_header(raw) != PGP_ARMOR:
            return f"commit {oid} carries no OpenPGP signature"
    log = reader.git(
        root,
        "log",
        "--no-walk=unsorted",
        "--no-show-signature",
        "--format=%H%x1f%G?%x1f%GF%x1e",
        *commits,
    )
    verdicts: dict[str, tuple[str, ...]] = {}
    for record in log.decode("ascii", "replace").split("\x1e"):
        fields = tuple(record.strip().split("\x1f"))
        if len(fields) == 3:
            verdicts[fields[0]] = fields[1:]
    for commit in commits:
        if verdicts.get(commit) != ("G", key):
            return f"commit {commit} is not good-signed by the profile's signing key"
    return None


def clean_violation(reader: Reader, root: Path) -> str | None:
    """The tracked tree is clean, the index matches HEAD and no entry hides from status."""

    for entry in reader.git(root, "ls-files", "-v", "-z").split(b"\0"):
        if entry and not entry.startswith(b"H "):
            return "an index entry is assume-unchanged, skip-worktree or unmerged"
    status = reader.git(
        root,
        *STATUS_PINS,
        "status",
        "--porcelain=v1",
        "--untracked-files=no",
        "--ignore-submodules=none",
    )
    return "the tracked tree or index differs from HEAD" if status.strip() else None


def branch_rules_violation(
    reader: Reader, checkout: Checkout, branch: str, profile: dict[str, Any]
) -> str | None:
    violation = branch_violation(branch, profile["default_branch"])
    if violation:
        return violation
    printed = reader.git(checkout.root, "check-ref-format", "--branch", branch)
    if printed.decode("utf-8", "replace").strip() != branch:
        return "branch is not accepted by git check-ref-format --branch"
    shadows = reader.git(
        checkout.root,
        "for-each-ref",
        "--format=%(refname)",
        f"refs/{branch}",
        f"refs/tags/{branch}",
        f"refs/remotes/{branch}",
        f"refs/remotes/{branch}/HEAD",
    )
    if shadows.strip():
        return "another ref shares the branch name"
    for directory in {checkout.admin, checkout.common}:
        if os.path.lexists(directory / branch):
            return "a pseudo-ref shares the branch name"
    return None


def body_violation(reader: Reader, checkout: Checkout, body_file: str) -> str | None:
    """The PR body is a singly linked regular file inside the worktree, equal to HEAD's blob."""

    body = Path(body_file)
    if not body.is_relative_to(checkout.root) or body == checkout.root:
        return "the body file is not inside the worktree"
    try:
        if body.resolve(strict=True) != body:
            return "the body file path has a symlink component"
        info = os.lstat(body)
    except (OSError, RuntimeError):
        return "the body file does not exist"
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BODY_BYTES:
        return "the body file is not a singly linked regular file of at most 64 KiB"
    relative = body.relative_to(checkout.root).as_posix()
    listing = reader.git(checkout.root, "ls-tree", "-z", "HEAD", "--", relative)
    records = [record for record in listing.split(b"\0") if record]
    if len(records) != 1:
        return "the body file is not tracked at HEAD"
    meta, _, name = records[0].partition(b"\t")
    mode, kind, oid = meta.decode("ascii").split(" ")
    if name.decode("utf-8", "replace") != relative or kind != "blob":
        return "the body file is not a tracked blob at HEAD"
    if mode not in {"100644", "100755"}:
        return "the body file is not a tracked regular file at HEAD"
    actual = reader.git(checkout.root, "hash-object", "--no-filters", "--", str(body))
    if actual.decode("ascii", "replace").strip() != oid:
        return "the body file bytes differ from HEAD's blob"
    return None


def rollup_violation(rollup: Any, required: list[str]) -> str | None:
    """Every status entry is green and every required check is present."""

    if not isinstance(rollup, list):
        return "the status check rollup is missing"
    if len(rollup) >= MAX_ROLLUP:
        return "the status check rollup has 100 or more entries and may be partial"
    names: set[str] = set()
    for entry in rollup:
        kind = entry.get("__typename") if isinstance(entry, dict) else None
        if kind == "CheckRun":
            name, green = entry.get("name"), entry.get("conclusion") == "SUCCESS"
        elif kind == "StatusContext":
            name, green = entry.get("context"), entry.get("state") == "SUCCESS"
        else:
            return f"unknown status entry {kind!r}"
        if not green:
            return f"check {name!r} is not green"
        names.add(str(name))
    missing = [name for name in required if name not in names]
    return f"required checks are missing: {missing}" if missing else None


def pull_request_violation(
    reader: Reader, seat: Path, request: DeliveryRequest, branch: str, profile: dict[str, Any]
) -> str | None:
    raw = reader.gh(
        seat,
        "pr",
        "view",
        str(request.number),
        "--repo",
        f"github.com/{profile['repository']}",
        "--json",
        PR_FIELDS,
    )
    try:
        view = json.loads(raw)
    except ValueError:
        return "gh pr view did not return JSON"
    if not isinstance(view, dict):
        return "gh pr view did not return an object"
    if view.get("state") != "OPEN":
        return "the pull request is not OPEN"
    if view.get("isCrossRepository") is not False:
        return "the pull request is cross-repository"
    if view.get("baseRefName") != profile["default_branch"]:
        return "the pull request base is not the default branch"
    if view.get("headRefName") != branch:
        return "the pull request head is not the worktree's branch"
    if view.get("headRefOid") != request.sha:
        return "the pull request head commit is not the named commit"
    return rollup_violation(view.get("statusCheckRollup"), profile["required_checks"])


def gh_socket_violation(reader: Reader, seat: Path) -> str | None:
    for args in (
        ("config", "get", "http_unix_socket"),
        ("config", "get", "-h", "github.com", "http_unix_socket"),
    ):
        if reader.gh(seat, *args).strip():
            return "gh http_unix_socket is set"
    return None


def path_git_violation(profile: dict[str, Any]) -> str | None:
    """gh runs git through PATH, so the first git there must be /usr/bin/git."""

    if shutil.which("git", path=profile["delivery_path"]) != GIT:
        return "the first git on delivery_path is not /usr/bin/git"
    return None


def _refuse(violation: str | None) -> None:
    if violation:
        raise DeliveryRefusal(f"delivery refused: {violation}")


def run_checks(
    reader: Reader,
    seat: Path,
    checkout: Checkout,
    request: DeliveryRequest,
    profile: dict[str, Any],
) -> None:
    """Step 4: every delivery read after the configuration check, in a fixed order."""

    _refuse(path_git_violation(profile))
    _refuse(gh_socket_violation(reader, seat))
    branch = head_branch(checkout.admin)
    if branch is None:
        raise DeliveryRefusal("delivery refused: the worktree has no current branch")
    for root, directories in (
        (checkout.root, (checkout.common, checkout.admin)),
        (seat, (seat / ".git",)),
    ):
        _refuse(hooks_violation(directories))
        _refuse(attributes_violation(reader, root, directories, profile))
        _refuse(origin_violation(reader, root, profile))
    _refuse(history_violation(reader, checkout.root, checkout.common))
    _refuse(branch_rules_violation(reader, checkout, branch, profile))
    head = reader.git(checkout.root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    head_oid = head.decode("ascii", "replace").strip()
    main = remote_object(reader, checkout.root, f"refs/heads/{profile['default_branch']}")
    reader.git(checkout.root, "cat-file", "-e", f"{main}^{{commit}}")
    reader.git(checkout.root, "merge-base", "--is-ancestor", main, "HEAD")
    _refuse(signature_violation(reader, checkout.root, main, profile["signing_key"]))
    _refuse(clean_violation(reader, checkout.root))
    if request.operation == PR_CREATE:
        if remote_object(reader, checkout.root, f"refs/heads/{branch}") != head_oid:
            raise DeliveryRefusal("delivery refused: the pushed branch is not the worktree's HEAD")
        _refuse(body_violation(reader, checkout, str(request.body_file)))
    elif request.operation == PR_MERGE:
        if head_oid != request.sha:
            raise DeliveryRefusal("delivery refused: the worktree's HEAD is not the named commit")
        _refuse(pull_request_violation(reader, seat, request, branch, profile))
