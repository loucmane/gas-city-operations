"""Patch-export intake of one Operations candidate (gct-lagl HANDOFF step 4); executes nothing from it.

  intake.py export <root> <common> <worktree> <name> <base> <process-record-json> <process-record-sha256>
                   <out-dir>
  intake.py apply  <root> <common> <export-dir> <reviewed-manifest-sha256> <fresh-worktree>
  intake.py retire <root> <common> <worktree> <name> <bead>

The three commands:
- export writes an export directory (patch, untracked bytes, manifest.json) and prints the manifest
  digest, which the reviewer records.
- apply takes that digest, refuses any other manifest, and applies into a fresh coordinator worktree
  named `<candidate>-intake` (a verified linked worktree directly under gas-city-ops-worktrees). From
  the applied index it re-derives every fact the export claimed (changed set, modes, binary, stop
  paths, privileged set, untracked set and bytes) and requires them to match. If apply refuses, the
  fresh worktree holds unreviewed-consistent bytes and is discarded: retire it like a candidate, and
  never commit from it. After a successful apply and review, the coordinator's own commit, tests and
  pre-commit run the reviewed code under coordinator authority, by design.
- retire moves the candidate worktree into the staging archive and locks it, whatever the outcome.
  If the move fails, it locks the worktree in place. It never deletes.

Rules that hold throughout:
- Every read and write under a worktree walks directory descriptors without following links.
- The export directory and the fresh worktree must be physical and outside the candidate root and
  every sandbox-writable location.
- Before and after export, no process may hold the candidate root, and none may be hidden from /proc
  beyond the recorded pids.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

from candidate_git import Refusal, git, no_drivers, no_gitlinks, require, split_z, verify_linked
import preroute

# The reviewer's attention flag, as an allowlist: only prose under docs/ is ordinary. Every other path may
# be executed, imported or trusted by the coordinator, its gate, its tooling or CI (code, tests, packaging,
# a root-level module shadowing the standard library, readiness records, design executors) and is flagged.
ORDINARY = ("docs/*.md", "docs/*.txt", "docs/*.rst")
# Agent instruction and skill files are trusted by Claude and Codex wherever they sit, and dot-directories
# (.claude/, .codex/, .github/ ...) hold tool configuration, so none of them is ever ordinary.
NEVER_ORDINARY = ("docs/ai/work-tracking/*", "*CLAUDE*.md", "*AGENTS*.md", "*GEMINI*.md", "*SKILL.md")
MAX_IGNORED = 10000
MAX_PATCH_BYTES = 16 << 20
MAX_UNTRACKED_FILES = 1000
MAX_UNTRACKED_BYTES = 32 << 20
STOP_PATHS = ("*.gitattributes", ".gitattributes", ".gitmodules", ".lfsconfig", "*/.gitmodules", "*/.lfsconfig")
SANDBOX_WRITABLE = (Path("/tmp"), Path("/var/tmp"), Path("/dev/shm"))
FRESH_ROOT = Path("/home/loucmane/gas-city-ops-worktrees")
ARCHIVE = Path("/home/loucmane/.local/share/gas-city-staging/candidate-archive")
SLICE: Path | None = None  # tests substitute a fixture cgroup slice; live uses the user's slice
SCHEMA = "gct-lagl.intake-export.v3"
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def outside_candidate_reach(path: Path, root: Path, label: str) -> None:
    require(path.is_absolute() and Path(os.path.realpath(path)) == path, f"{label} is not physical: {path}")
    for forbidden in (root, *SANDBOX_WRITABLE):
        require(path != forbidden and forbidden not in path.parents, f"{label} is inside {forbidden}")


def relative_key(key: str) -> PurePosixPath:
    path = PurePosixPath(key)
    require(bool(key) and not path.is_absolute() and str(path) == key
            and all(part not in {"", ".", "..", ".git"} for part in path.parts), f"unsafe path: {key!r}")
    return path


def open_parent(base: Path, relative: PurePosixPath, create: bool = False) -> int:
    """A descriptor of relative's parent, reached through directory descriptors, never following a link."""
    fd = os.open(base, DIR_FLAGS)
    try:
        for part in relative.parts[:-1]:
            if create:
                try:
                    os.mkdir(part, 0o755, dir_fd=fd)
                except FileExistsError:
                    pass
            try:
                child = os.open(part, DIR_FLAGS, dir_fd=fd)
            except OSError as exc:
                raise Refusal(f"component is not a real directory: {part} in {relative}: {exc.strerror}") from exc
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_regular(base: Path, key: str) -> bytes:
    relative = relative_key(key)
    parent = open_parent(base, relative)
    try:
        try:
            fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        except OSError as exc:
            raise Refusal(f"cannot open without following links: {key}: {exc.strerror}") from exc
    finally:
        os.close(parent)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, f"not a single-link regular file: {key}")
        chunks, size = [], 0
        while block := os.read(fd, 1 << 20):
            chunks.append(block)
            size += len(block)
            require(size <= 64 << 20, f"file too large: {key}")
        require(os.fstat(fd).st_size == size, f"file changed while reading: {key}")
    finally:
        os.close(fd)
    return b"".join(chunks)


def write_new(base: Path, key: str, raw: bytes) -> None:
    relative = relative_key(key)
    parent = open_parent(base, relative, create=True)
    try:
        fd = os.open(relative.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644,
                     dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)


def matches(path: str, patterns) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def privileged(path: str) -> bool:
    dotted = any(part.startswith(".") for part in PurePosixPath(path).parts)
    agent_file = matches(path.lower(), [pattern.lower() for pattern in NEVER_ORDINARY])
    return dotted or agent_file or not matches(path, ORDINARY)


def unsafe_entries(worktree: Path) -> list[str]:
    found = []

    def unreadable(error):
        found.append(f"{error.filename}:unreadable")

    for directory, dirs, names in os.walk(worktree, followlinks=False, onerror=unreadable):
        for name in names + [d for d in dirs if (Path(directory) / d).is_symlink()]:
            path = Path(directory) / name
            if path == worktree / ".git":
                continue
            info = path.lstat()
            if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
                found.append(f"{path.relative_to(worktree)}:multilink")
            elif not (stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                found.append(f"{path.relative_to(worktree)}:special")
    return sorted(found)


def raw_changes(git_dir: Path, worktree: Path, *extra: str) -> list[dict]:
    out = git(git_dir, worktree, "diff", *extra, "--raw", "--no-renames", "-z", "HEAD").split(b"\0")
    changes = []
    for header, path in zip(out[0::2], out[1::2]):
        if not header:
            continue
        fields = header.decode().lstrip(":").split()
        changes.append(dict(path=path.decode("utf-8", "surrogateescape"), old_mode=fields[0], new_mode=fields[1],
                            status=fields[4]))
    return changes


def binary_paths(git_dir: Path, worktree: Path, *extra: str) -> list[str]:
    lines = git(git_dir, worktree, "diff", *extra, "--numstat", "--no-renames", "-z", "HEAD").split(b"\0")
    return sorted(line.split(b"\t", 2)[2].decode("utf-8", "surrogateescape")
                  for line in lines if line.startswith(b"-\t-\t"))


def check_facts(changes: list[dict], binary: list[str], untracked: list[str], ignored: list[str]) -> None:
    for change in changes:
        relative_key(change["path"])
        require(change["new_mode"] in {"100644", "100755", "000000"}, f"link or special mode: {change}")
        require(change["old_mode"] in {change["new_mode"], "000000"} or change["new_mode"] == "000000",
                f"mode change needs explicit review: {change}")
    stops = [p for p in [c["path"] for c in changes] + untracked + ignored if matches(p, STOP_PATHS)]
    require(not stops, f"attribute/module/lfs configuration present: {stops}")
    require(not binary, f"binary changes need explicit review: {binary}")


def quiet_root(root: Path, record: dict, label: str) -> None:
    slice_root = SLICE or preroute.user_slice(os.getuid())
    city = preroute.city_problems(slice_root, record)
    require(not city, f"the city is not quiet {label} export: {city}")
    problems = preroute.survey(root, os.getuid(), slice_root, record["hidden"])
    require(not problems, f"processes hold the candidate root or are hidden {label} export: {problems}")


def export(root: Path, common: Path, worktree: Path, name: str, base: str, record: dict, out: Path) -> dict:
    outside_candidate_reach(out, root, "export directory")
    admin = verify_linked(root, common, worktree, name)
    no_drivers(admin, worktree)
    quiet_root(root, record, "before")
    unsafe = unsafe_entries(worktree)
    require(not unsafe, f"special, multi-link or unreadable entries in the candidate: {unsafe}")
    head = git(admin, worktree, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    require(head == base, f"candidate HEAD {head} is not the coordinator's base {base}")
    no_gitlinks(admin, worktree, head)
    changes = raw_changes(admin, worktree)
    untracked = split_z(git(admin, worktree, "ls-files", "-o", "--exclude-standard", "-z"))
    ignored = split_z(git(admin, worktree, "ls-files", "-o", "-i", "--exclude-standard", "-z"))
    require(len(ignored) <= MAX_IGNORED, f"more than {MAX_IGNORED} ignored files")
    check_facts(changes, binary_paths(admin, worktree), untracked, ignored)
    require(len(untracked) <= MAX_UNTRACKED_FILES, f"more than {MAX_UNTRACKED_FILES} untracked files")
    # The candidate is quiet (surveyed above), so the sizes it has now bound the patch git is about to build.
    sizes = sum(os.lstat(worktree / c["path"]).st_size for c in changes if os.path.lexists(worktree / c["path"]))
    require(sizes <= MAX_PATCH_BYTES, f"changed files exceed {MAX_PATCH_BYTES} bytes")
    patch = git(admin, worktree, "diff", "--binary", "--full-index", "--no-renames", "--no-textconv",
                "--no-ext-diff", "--no-color", "HEAD")
    # The manifest summary must describe exactly the exported patch: re-derive after it and compare.
    require(raw_changes(admin, worktree) == changes and not binary_paths(admin, worktree),
            "the candidate changed while it was being exported")
    require(len(patch) <= 2 * MAX_PATCH_BYTES, "the patch is too large to review")
    out.mkdir(mode=0o700)
    (out / "untracked").mkdir(mode=0o700)
    files, total = {}, 0
    for key in untracked:
        require(not key.endswith("/"), f"nested repository or directory: {key}")
        raw = read_regular(worktree, key)
        total += len(raw)
        require(total <= MAX_UNTRACKED_BYTES, f"untracked files exceed {MAX_UNTRACKED_BYTES} bytes")
        require(b"\0" not in raw, f"binary untracked file needs explicit review: {key}")
        files[key] = sha(raw)
        write_new(out / "untracked", key, raw)
    quiet_root(root, record, "after")
    (out / "candidate.patch").write_bytes(patch)
    changed = sorted(c["path"] for c in changes)
    manifest = dict(schema=SCHEMA, base=base, admin=str(admin), worktree=str(worktree), patch_sha256=sha(patch),
                    untracked=files, ignored=ignored, changed=changed, changes=changes,
                    privileged=sorted(p for p in changed + list(files) if privileged(p)))
    raw_manifest = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    (out / "manifest.json").write_bytes(raw_manifest)
    return dict(manifest, manifest_sha256=sha(raw_manifest))


def apply(root: Path, common: Path, export_dir: Path, reviewed: str, fresh: Path) -> dict:
    outside_candidate_reach(export_dir, root, "export directory")
    outside_candidate_reach(fresh, root, "fresh worktree")
    raw_manifest = read_regular(export_dir, "manifest.json")
    require(sha(raw_manifest) == reviewed, "manifest is not the reviewed export")
    manifest = json.loads(raw_manifest)
    require(manifest["schema"] == SCHEMA, "unknown export schema")
    exported = Path(manifest["worktree"])
    require(exported.parent == root and manifest["admin"] == str(common / "worktrees" / exported.name),
            "the export was not taken from this candidate root and common directory")
    patch = read_regular(export_dir, "candidate.patch")
    require(sha(patch) == manifest["patch_sha256"], "patch digest drift")
    for key in manifest["untracked"]:
        relative_key(key)
    require(fresh.name == Path(manifest["worktree"]).name + "-intake",
            f"fresh worktree must be named {Path(manifest['worktree']).name}-intake")
    fresh_admin = verify_linked(FRESH_ROOT, common, fresh, fresh.name)
    no_drivers(fresh_admin, fresh)
    head = git(fresh_admin, fresh, "rev-parse", "HEAD").decode().strip()
    require(head == manifest["base"], "fresh worktree is not at the candidate base")
    no_gitlinks(fresh_admin, fresh, head)
    require(git(fresh_admin, fresh, "status", "--porcelain", "--ignored", "-z") == b"", "fresh worktree is not clean")
    if patch:
        git(fresh_admin, fresh, "apply", "--index", "--binary", "--whitespace=nowarn",
            str(export_dir / "candidate.patch"), cwd=fresh)
    for key, digest in manifest["untracked"].items():
        raw = read_regular(export_dir / "untracked", key)
        require(sha(raw) == digest, f"untracked digest drift: {key}")
        write_new(fresh, key, raw)
    # Re-derive every exported fact from the applied state, which no candidate process can reach.
    replay = git(fresh_admin, fresh, "diff", "--cached", "--binary", "--full-index", "--no-renames",
                 "--no-textconv", "--no-ext-diff", "--no-color", "HEAD")
    require(sha(replay) == manifest["patch_sha256"], "applied patch differs from the reviewed export")
    changes = raw_changes(fresh_admin, fresh, "--cached")
    landed = sorted(split_z(git(fresh_admin, fresh, "ls-files", "-o", "--exclude-standard", "-z")))
    check_facts(changes, binary_paths(fresh_admin, fresh, "--cached"), landed, [])
    changed = sorted(c["path"] for c in changes)
    require(changed == manifest["changed"], "applied changed set differs from the reviewed export")
    require(landed == sorted(manifest["untracked"]), "untracked set differs from the reviewed export")
    for key, digest in manifest["untracked"].items():
        require(sha(read_regular(fresh, key)) == digest, f"landed untracked bytes differ: {key}")
    flagged = sorted(p for p in changed + landed if privileged(p))
    require(flagged == manifest["privileged"], "privileged set differs from the reviewed export")
    return dict(ok=True, base=head, patch_sha256=manifest["patch_sha256"], untracked=len(landed))


def retire(root: Path, common: Path, worktree: Path, name: str, bead: str) -> dict:
    require(bool(preroute.BEAD.fullmatch(bead)), "invalid bead id")
    archive = ARCHIVE / bead / name
    stage = "verify"
    try:
        require(not os.path.lexists(archive), "archive target exists")
        verify_linked(root, common, worktree, name)
        stage = "archive-target"
        archive.parent.mkdir(parents=True, exist_ok=True)
        outside_candidate_reach(archive.parent, root, "archive")
        require(os.stat(archive.parent).st_dev == os.stat(worktree).st_dev, "archive is on another filesystem")
        stage = "move"
        git(common, None, "worktree", "move", str(worktree), str(archive))
        stage = "lock"
        git(common, None, "worktree", "lock", "--reason", "gct-lagl retired candidate", str(archive))
        return dict(ok=True, archived=str(archive))
    except (Refusal, OSError) as exc:
        # Lock wherever the worktree now is, so nothing reuses it, and stop routing (HANDOFF 4.5).
        where = archive if stage == "lock" else worktree
        git(common, None, "worktree", "lock", "--reason", "gct-lagl retirement failed; do not route",
            str(where), expected=(0, 128))
        raise Refusal(f"retirement failed at {stage}; lock attempted on {where}: {exc}") from exc


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 9 and argv[0] == "export":
            result = export(Path(argv[1]), Path(argv[2]), Path(argv[3]), argv[4], argv[5],
                            preroute.load_record(Path(argv[6]), argv[7]), Path(argv[8]))
        elif len(argv) == 6 and argv[0] == "apply":
            result = apply(Path(argv[1]), Path(argv[2]), Path(argv[3]), argv[4], Path(argv[5]))
        elif len(argv) == 6 and argv[0] == "retire":
            result = retire(Path(argv[1]), Path(argv[2]), Path(argv[3]), argv[4], argv[5])
        else:
            raise Refusal("usage: see module docstring")
    except (Refusal, OSError, KeyError, ValueError) as exc:
        print(json.dumps(dict(ok=False, stop=str(exc))))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
