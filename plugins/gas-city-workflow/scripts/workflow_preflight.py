"""Inspect the immutable source base before creating a workflow context."""

from pathlib import PurePosixPath
import tomllib

from _repo_structure import DEFAULT_REPO_STRUCTURE
from workflow_common import WorkflowError


def inherited_contexts(runner, spec):
    """Return ACTIVE contexts from the selected Git tree, without checkout I/O."""
    command = ["git", "-C", spec.canonical_root]
    output = runner.run([*command, "ls-tree", "-r", "-z", spec.base_commit]).stdout
    if len(output.encode()) > 16 * 1024 * 1024:
        raise WorkflowError("workflow base inventory exceeds bounds")
    entries = {}
    for record in output.split("\0"):
        if not record:
            continue
        header, separator, name = record.partition("\t")
        fields = header.split()
        if not separator or len(fields) != 3 or name in entries:
            raise WorkflowError("invalid workflow base tree inventory")
        entries[name] = fields
    if ".codex" in entries:
        raise WorkflowError("workflow base configuration parent is not a directory")
    config = entries.get(".codex/config.toml")
    overrides = {}
    if config is not None:
        mode, kind, object_id = config
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise WorkflowError("workflow base configuration must be a regular file")
        size = runner.run([*command, "cat-file", "-s", object_id]).stdout.strip()
        if not size.isdecimal() or int(size) > 1024 * 1024:
            raise WorkflowError("workflow base configuration exceeds bounds")
        content = runner.run([*command, "cat-file", "blob", object_id]).stdout
        try:
            overrides = tomllib.loads(content).get("repo_structure", {})
        except ValueError as error:
            raise WorkflowError("invalid workflow base configuration") from error
    if not isinstance(overrides, dict) or set(overrides) - set(DEFAULT_REPO_STRUCTURE):
        raise WorkflowError("invalid workflow base repo_structure table")
    roots = {**DEFAULT_REPO_STRUCTURE, **overrides}
    for value in roots.values():
        if (not isinstance(value, str) or not value or PurePosixPath(value).is_absolute()
                or "\\" in value or any(char in value for char in ("\0", "\n", "\r"))
                or any(part in {"", ".", "..", ".git"} for part in value.split("/"))):
            raise WorkflowError("workflow base layout requires normalized relative roots")
        parts = value.split("/")
        if any("/".join(parts[:index]) in entries for index in range(1, len(parts) + 1)):
            raise WorkflowError("workflow base layout root is not a directory")
    active = roots["work_tracking_root"] + "/active/"
    if active.rstrip("/") in entries:
        raise WorkflowError("workflow base ACTIVE root is not a directory")
    return sorted({name[len(active):].split("/", 1)[0] for name in entries
                   if name.startswith(active) and name[len(active):].split("/", 1)[0].endswith("-ACTIVE")})


def preflight_inherited_context(runner, spec):
    """Fail before worktree/ref/journal writes for a modern inherited conflict."""
    if spec.workflow_profile != "beads-with-aegis-evidence":
        return
    conflicts = [name for name in inherited_contexts(runner, spec) if f"-{spec.bead_id}-" not in name]
    if conflicts:
        raise WorkflowError(
            "inherited workflow context conflicts with new work: " + ", ".join(conflicts)
            + "; preserve the unfinished context and use its supported dependency workflow"
        )
