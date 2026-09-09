"""Frozen state for the reviewed five-move Core evidence relocation.

Development-side migration support, not an installed plugin or authorization
surface. A reviewed caller still owns source/Bead/runtime and docsync validation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from aegis_foundation.gate.session_authority import assert_no_pending_continuation, contained_path

SCHEMA = "gc.core-evidence-layout-plan.v1"
PARENTS = ("engdocs/workflow", "engdocs/workflow/plans", ".codex")
CONFIG = b'''[repo_structure]
sessions_root = "engdocs/workflow/sessions"
plans_root = "engdocs/workflow/plans"
plan_state_dir = "engdocs/workflow/plan-state"
work_tracking_root = "engdocs/workflow/work-tracking"
'''


class RelocationError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def require(condition, message):
    if not condition:
        raise RelocationError(message)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def tracked_diff(root: Path) -> str:
    result = subprocess.run(["git", "-C", str(root), "diff", "--binary", "HEAD"],
                            check=True, capture_output=True)
    return digest(result.stdout)


def literal_root(root: Path) -> None:
    require(root.is_absolute() and root == root.resolve(), "root must be literal and canonical")
    require(root.is_dir() and not root.is_symlink(), "root is not a real directory")
    require(Path(git(root, "rev-parse", "--show-toplevel")) == root, "root is not the Git worktree")


def inspect(path: Path) -> dict:
    """Hash regular leaves; never follow or accept special/hardlinked files."""
    if not os.path.lexists(path):
        return {"kind": "absent"}
    st = path.lstat()
    value = {"mode": stat.S_IMODE(st.st_mode), "uid": st.st_uid, "gid": st.st_gid}
    require(st.st_uid == os.getuid(), f"unexpected owner: {path}")
    if stat.S_ISLNK(st.st_mode):
        value.update(kind="link", target=os.readlink(path))
    elif stat.S_ISDIR(st.st_mode):
        value["kind"] = "directory"
    else:
        require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, f"special or hardlinked file: {path}")
        value.update(kind="file", size=st.st_size, sha256=digest(path.read_bytes()))
    return value


def tree(root: Path, relative: str) -> dict:
    path = contained_path(root, relative, "relocation path", leaf_link=True)
    result = {relative: inspect(path)}
    if result[relative]["kind"] == "directory":
        for child in sorted(path.iterdir()):
            result.update(tree(root, child.relative_to(root).as_posix()))
    return result


def maps_for(plan_name: str) -> tuple:
    require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9.-]+\.md", plan_name), "invalid plan filename")
    return (
        ("docs/ai/work-tracking", "engdocs/workflow/work-tracking"),
        ("sessions", "engdocs/workflow/sessions"),
        (".plan_state", "engdocs/workflow/plan-state"),
        (f"plans/{plan_name}", f"engdocs/workflow/plans/{plan_name}"),
        ("plans/current", "engdocs/workflow/plans/current"),
    )


def relocate_path(relative: str, moves) -> str:
    for source, destination in moves:
        if relative == source or relative.startswith(source + "/"):
            return destination + relative[len(source):]
    raise RelocationError(f"path is not in the five-move scope: {relative}")


def external_paths(root: Path, bead: str) -> dict:
    common = Path(git(root, "rev-parse", "--git-common-dir"))
    common = (root / common).resolve() if not common.is_absolute() else common.resolve()
    index = Path(git(root, "rev-parse", "--git-path", "index"))
    index = (root / index).resolve() if not index.is_absolute() else index.resolve()
    return {"common": common, "index": index,
            "ownership": common / "gas-city-workflow/transactions" / f"{bead}.json"}


def rewrite_plan(original: bytes, backup: Path) -> bytes:
    text = original.decode("utf-8")
    before, marker, rest = text.partition("## Amendments & Versioning\n")
    history, next_heading, after = rest.partition("## Continuation & Handoff\n")
    require(bool(marker and next_heading), "plan sections are ambiguous")
    require(text.count(marker) == 1 and text.count(next_heading) == 1, "duplicate plan sections")
    require("docs/ai/work-tracking/active/" in before, "active plan has no old evidence root")
    amendment = ("- Layout relocation: active references now use engdocs/workflow; original plan "
                 f"preserved at `{backup}` (SHA-256 {digest(original)}). No task status changed.\n\n")
    return (before.replace("docs/ai/work-tracking", "engdocs/workflow/work-tracking")
            + marker + history + amendment + next_heading
            + after.replace("docs/ai/work-tracking", "engdocs/workflow/work-tracking")
            .replace("`sessions/current`", "`engdocs/workflow/sessions/current`")
            .replace("`plans/current`", "`engdocs/workflow/plans/current`")).encode()


def freeze(root: Path, bead: str, policy_sha256: str, protected: list[str]) -> dict:
    """Read-only proposal; neither a review verdict nor authority to apply."""
    literal_root(root)
    require(re.fullmatch(r"[a-z][a-z0-9]*-[a-z0-9]+(?:\.[1-9][0-9]*)*", bead), "invalid Bead")
    require(re.fullmatch(r"[0-9a-f]{64}", policy_sha256), "invalid policy digest")
    require((root / "plans/current").is_symlink(), "current plan is not a symlink")
    plan_name = os.readlink(root / "plans/current")
    moves = maps_for(plan_name)
    require(bead in plan_name, "plan does not name the Bead")
    require(not git(root, "ls-files", "--", *(source for source, _ in moves)),
            "relocation is limited to untracked internal evidence")
    entries = {}
    for source, destination in moves:
        require(not os.path.lexists(root / destination), "destination collision")
        values = tree(root, source)
        require(values[source]["kind"] != "absent", "source is absent")
        entries.update(values)
    links = {p for p, value in entries.items() if value["kind"] == "link"}
    require(links == {"sessions/current", "plans/current"}, "unexpected symlink in evidence")
    for relative in links:
        target = entries[relative]["target"]
        require(not Path(target).is_absolute() and all(p not in {"", ".", ".."} for p in target.split("/")),
                f"{relative} must be a target-local relative link")
        require((root / relative).resolve().is_relative_to((root / relative).parent),
                f"{relative} escapes its session/plan subtree")
        require((root / relative).is_file(), "current link is broken")
    parents = {p: inspect(root / p) for p in ("engdocs", *PARENTS)}
    require(parents["engdocs"]["kind"] == "directory", "engdocs is not a preserved directory")
    require(all(parents[p]["kind"] == "absent" for p in PARENTS), "new parent already exists")
    config = inspect(root / ".codex/config.toml")
    require(config["kind"] == "absent", "configuration already exists")
    original_plan = (root / "plans" / plan_name).read_bytes()
    original_sync = (root / ".plan_state/sync.log").read_bytes()
    entries_json = json.loads(original_sync)
    require(isinstance(entries_json, list), "sync log is not an array")
    require((json.dumps(entries_json, indent=2) + "\n").encode() == original_sync,
            "original sync serialization is not canonical")
    paths = external_paths(root, bead)
    guarded = {}
    for relative in sorted(set(protected)):
        path = contained_path(root, relative, "protected path")
        require(relative not in entries, "protected file is part of the move")
        guarded[relative] = inspect(path)
        require(guarded[relative]["kind"] == "file", "protected path is not a regular file")
    wal = tree(root, ".aegis/state/session-continuations")
    wal.update(tree(root, ".aegis/state/session-continuation.json"))
    require(wal[".aegis/state/session-continuations"]["kind"] == "directory", "WAL archive directory missing")
    require(wal[".aegis/state/session-continuation.json"]["kind"] == "file", "current WAL missing")
    assert_no_pending_continuation(root)
    for relative, value in wal.items():
        if relative == ".aegis/state/session-continuations":
            continue
        require(value["kind"] == "file" and value["mode"] == 0o600, "WAL file type or mode mismatch")
        data = (root / relative).read_bytes()
        record = json.loads(data)
        require(isinstance(record, dict) and record.get("schema") == "aegis.session-continuation.v1"
                and record.get("status") in {"complete", "rolled_back"}
                and isinstance(record.get("id"), str) and re.fullmatch(r"[0-9a-f]{32}", record["id"]),
                "nonterminal or invalid WAL record")
        require(data == (json.dumps(record, indent=2) + "\n").encode(), "WAL serialization drift")
        if relative != ".aegis/state/session-continuation.json":
            require(relative == f'.aegis/state/session-continuations/{record["id"]}.json', "WAL archive identity drift")
    require(all(inspect(paths[key])["kind"] == "file" for key in ("index", "ownership")),
            "index or ownership journal missing")
    seed = {"schema": SCHEMA, "root": str(root), "bead": bead,
            "policy_sha256": policy_sha256, "plan_name": plan_name,
            "head": git(root, "rev-parse", "HEAD"), "branch": git(root, "branch", "--show-current"),
            "tracked_diff_sha256": tracked_diff(root),
            "moves": [list(pair) for pair in moves], "entries": entries,
            "parents": parents, "protected": guarded, "wal_before": wal,
            "external": {key: {"path": str(paths[key]), "image": inspect(paths[key])}
                         for key in ("index", "ownership")}, "common": str(paths["common"]),
            "plan_before_b64": base64.b64encode(original_plan).decode()}
    plan_id = digest(canonical(seed))
    backup = paths["common"] / "gas-city-workflow/layout-relocations" / plan_id / "originals/plans" / plan_name
    postimage = rewrite_plan(original_plan, backup)
    return {**seed, "plan_id": plan_id, "plan_after_b64": base64.b64encode(postimage).decode()}


def validate_manifest(value: dict) -> None:
    fields = {"schema", "root", "bead", "policy_sha256", "plan_name", "head", "branch",
              "moves", "entries", "parents", "protected", "wal_before", "external", "common",
              "plan_before_b64", "plan_id", "plan_after_b64", "tracked_diff_sha256"}
    require(isinstance(value, dict) and set(value) == fields, "unexpected manifest fields")
    require(value.get("schema") == SCHEMA, "wrong plan schema")
    seed = {k: v for k, v in value.items() if k not in {"plan_id", "plan_after_b64"}}
    require(digest(canonical(seed)) == value.get("plan_id"), "plan identity drift")
    require(value["moves"] == [list(pair) for pair in maps_for(value["plan_name"])], "move scope drift")
    require(set(value["external"]) == {"index", "ownership"}, "external backup scope drift")
    require(set(value["parents"]) == {"engdocs", *PARENTS}, "parent scope drift")
    root = Path(value["root"])
    for relative in value["entries"]:
        contained_path(root, relative, "manifest entry", leaf_link=True)
        relocate_path(relative, value["moves"])
    require(all(source in value["entries"] for source, _ in value["moves"]), "manifest source is missing")
    for relative in value["protected"]:
        contained_path(root, relative, "manifest protected file")
        require(relative not in value["entries"], "protected scope overlaps move")
    for relative in value["wal_before"]:
        require(relative in {".aegis/state/session-continuation.json", ".aegis/state/session-continuations"}
                or re.fullmatch(r"\.aegis/state/session-continuations/[0-9a-f]{32}\.json", relative),
                "WAL backup scope drift")
    backup = Path(value["common"]) / "gas-city-workflow/layout-relocations" / value["plan_id"] / "originals/plans" / value["plan_name"]
    original = base64.b64decode(value["plan_before_b64"], validate=True)
    require(digest(original) == value["entries"]["plans/" + value["plan_name"]]["sha256"],
            "original plan image disagrees with inventory")
    require(base64.b64decode(value["plan_after_b64"], validate=True) == rewrite_plan(original, backup),
            "plan postimage drift")


def check_external(root: Path, plan: dict) -> None:
    literal_root(root)
    require(str(root) == plan["root"], "root identity drift")
    require(git(root, "rev-parse", "HEAD") == plan["head"], "HEAD drift")
    require(git(root, "branch", "--show-current") == plan["branch"], "branch drift")
    require(tracked_diff(root) == plan["tracked_diff_sha256"], "tracked source diff drift")
    paths = external_paths(root, plan["bead"])
    require(str(paths["common"]) == plan["common"], "Git common directory drift")
    for key in ("index", "ownership"):
        require(str(paths[key]) == plan["external"][key]["path"], "external path drift")
        require(inspect(paths[key]) == plan["external"][key]["image"], f"{key} drift")
    for relative, expected in plan["protected"].items():
        path = contained_path(root, relative, "protected path")
        require(inspect(path) == expected, f"protected file drift: {relative}")
