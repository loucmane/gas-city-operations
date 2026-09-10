"""Retire one unowned inherited scaffold attempt into its unfinished parent.

The CLI holds the repository lock. Review the read-only plan before supplying
its digest. Unknown partial writes are preserved and refused, never replayed.
"""

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from project_context import DEFAULT_REGISTRY, build_context
from _repo_structure import load_repo_structure
from workflow_attachment_reconcile import _backup, _body, _edges, _image, _write_image
from workflow_attach import (
    _active_tracker, _current_plan, _render_plan_attachment, _render_tracker_attachment,
)
from workflow_common import (
    BEAD_PATTERN, BeginSpec, CommandRunner, WorkflowError,
    derive_begin_spec, git_value, journal_path, load_bead, load_journal, managed_environment,
    require_journal_spec, result_payload, run_readiness,
)
from workflow_ownership import (
    OWNER_KEY, bead_digest, canonical_json, check_active_ownership, owner_binding, require_binding,
    require_external_candidate, require_workspace,
)
from workflow_preflight import inherited_contexts

SCHEMA = "gas-city-workflow.context-recovery.v1"


def _digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _pin(image):
    return {"sha256": hashlib.sha256(image[0]).hexdigest(), "mode": image[1],
            "uid": image[2], "gid": image[3]}


def _safe_image(path):
    if any(parent.is_symlink() for parent in path.parents):
        raise WorkflowError("context recovery refuses symlink parents")
    image = _image(path)
    if image[1] & 0o022:
        raise WorkflowError("context recovery refuses group/world-writable inputs")
    return image


def _entry(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"missing": True}
    if stat.S_ISLNK(info.st_mode):
        if info.st_uid != os.geteuid():
            raise WorkflowError("context recovery requires owned pointers")
        return {"symlink": os.readlink(path), "uid": info.st_uid, "gid": info.st_gid}
    return _pin(_safe_image(path))


def _workspace(runner, root):
    status = git_value(runner, root, "status", "--porcelain=v1", "--untracked-files=all")
    names = set()
    for command in (("diff", "--name-only", "-z", "HEAD"),
                    ("ls-files", "--others", "--exclude-standard", "-z")):
        output = runner.run(["git", "-C", str(root), *command]).stdout
        if len(output.encode()) > 1024 * 1024:
            raise WorkflowError("context recovery worktree inventory exceeds bounds")
        names.update(name for name in output.split("\0") if name)
    return {"head": git_value(runner, root, "rev-parse", "HEAD"), "status": status,
            "files": {name: _entry(root / name) for name in sorted(names)}}


def _sources():
    return {path.name: _pin(_safe_image(path))["sha256"]
            for path in sorted(Path(__file__).parent.glob("*.py"))}


def _paths(parent_path, child_id):
    return parent_path.with_name(f"{child_id}.json"), parent_path.with_name(f"{child_id}.context-recovery.json")


def _marker(plan, digest):
    return {"schema": SCHEMA, "plan_sha256": digest, "parent_bead": plan["parent"]["bead_id"],
            "parent_binding": plan["binding"], "state": "retired-unowned-context"}


def _encoded(payload, image):
    return ((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(), *image[1:])


def _retired(plan, digest, original):
    payload = json.loads(original[0])
    payload["context_recovery"] = _marker(plan, digest)
    return _encoded(payload, original)


def _backups(path, plan, digest):
    return {name: path.with_name(f"{plan[name]['bead_id']}.context-{digest}.before.json")
            for name in ("parent", "child")}


def _record(path):
    image = _safe_image(path)
    record = json.loads(image[0])
    if (not isinstance(record, dict) or record.get("schema") != SCHEMA
            or record.get("state") not in {"prepared", "completed"}
            or not isinstance(record.get("plan"), dict)
            or record.get("plan_sha256") != _digest(record["plan"])):
        raise WorkflowError("invalid context recovery record")
    plan, digest = record["plan"], record["plan_sha256"]
    backups = _backups(path, plan, digest)
    for name, backup in backups.items():
        if _pin(_safe_image(backup)) != plan["before"]["journals"][name]:
            raise WorkflowError("context recovery original snapshot drift")
        original = load_journal(backup)
        if original is None or original["spec"] != plan[name]:
            raise WorkflowError("context recovery original spec drift")
        if name == "child":
            _require_partial(original)
        elif original["phase"] != "ready":
            raise WorkflowError("context recovery original parent is not ready")
    return record, image, backups


def _require_partial(journal):
    if (journal is None or journal["phase"] != "worktree-created"
            or set(journal) != {"schema", "phase", "spec", "created_at", "updated_at", "history"}
            or [item.get("phase") for item in journal["history"]] != ["planned", "worktree-created"]):
        raise WorkflowError("context recovery requires the untouched unowned worktree-created attempt")


def require_reconciled_standalone(runner, spec, context, bead_id):
    if bead_id == spec.bead_id:
        return
    child_path, record_path = _paths(journal_path(runner, spec), bead_id)
    if not child_path.exists() and not child_path.is_symlink():
        if record_path.exists() or record_path.is_symlink():
            raise WorkflowError("standalone context journal disappeared")
        return
    if not record_path.exists():
        raise WorkflowError("standalone context requires exact inherited-context reconciliation")
    record, _, backups = _record(record_path)
    plan = record["plan"]
    if (plan["parent"] != spec.payload() or plan["child"]["bead_id"] != bead_id
            or plan["binding"] != owner_binding(spec, context)
            or _safe_image(child_path) != _retired(plan, record["plan_sha256"], _safe_image(backups["child"]))):
        raise WorkflowError("standalone context retirement binding drift")


def _reverse_edges(runner, context, bead_id):
    workflow = context["workflow"]
    result = runner.run([str(workflow["gc"]), "--city", str(workflow["city"]),
                         "--rig", str(workflow["rig"]), "bd", "dep", "list", bead_id,
                         "--direction", "up", "--json"], env=managed_environment())
    if len(result.stdout.encode()) > 16 * 1024 * 1024:
        raise WorkflowError("reverse dependency readback exceeds bounds")
    try:
        rows = json.loads(result.stdout)
    except ValueError as error:
        raise WorkflowError("invalid reverse dependency JSON") from error
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise WorkflowError("reverse dependency readback must be a list of records")
    edges = _edges({"dependencies": rows})
    if any(not BEAD_PATTERN.fullmatch(target) or target.split("-", 1)[0] != bead_id.split("-", 1)[0]
           for target, _ in edges):
        raise WorkflowError("reverse dependency readback contains an invalid same-store identity")
    return [list(edge) for edge in sorted(edges)]


def _facts(runner, root, spec, child, context, paths, registry):
    layout = load_repo_structure(root)
    evidence = {"plan": _current_plan(root), "tracker": _active_tracker(root, spec.bead_id),
                "session_state": layout.session_state_path}
    facts = {
        "journals": {name: _pin(_safe_image(path)) for name, path in paths.items()},
        "evidence": {name: {"path": str(path), **_pin(_safe_image(path))} for name, path in evidence.items()},
        "pointers": {str(path): _entry(path) for path in (layout.current_plan_link, layout.current_session_link)},
        "parent_workspace": _workspace(runner, root),
        "child_workspace": _workspace(runner, Path(child.worktree)),
        "beads": {name: load_bead(runner, context, bead_id)
                  for name, bead_id in (("parent", spec.bead_id), ("child", child.bead_id))},
        "reverse_edges": {name: _reverse_edges(runner, context, bead_id)
                          for name, bead_id in (("parent", spec.bead_id), ("child", child.bead_id))},
        "registry": _pin(_safe_image(registry)),
        "context": build_context(root, registry),
        "sources": _sources(),
    }
    if facts["child_workspace"] != {"head": child.base_commit, "status": "", "files": {}}:
        raise WorkflowError("standalone child worktree is not clean at its exact recorded base")
    return facts


def _validate_parent(runner, root, registry, child_id):
    context = build_context(root, registry)
    if context["workspace"]["location"] != "linked-worktree":
        raise WorkflowError("context recovery requires the existing parent task worktree")
    spec = check_active_ownership(runner, root, registry=registry, attaching=child_id)
    if spec.workflow_profile != "beads-with-aegis-evidence":
        raise WorkflowError("context recovery requires modern Beads source evidence")
    if child_id == spec.bead_id or child_id.split("-", 1)[0] != spec.bead_id.split("-", 1)[0]:
        raise WorkflowError("context recovery requires a distinct same-store child")
    if "STATE: READY" not in run_readiness(runner, root):
        raise WorkflowError("context recovery parent is not ready")
    return spec, context


def reconcile_context(root, bead_id, expected_plan_sha256=None, runner=None, *, registry=DEFAULT_REGISTRY):
    if not BEAD_PATTERN.fullmatch(bead_id):
        raise WorkflowError("invalid context recovery child")
    if expected_plan_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", expected_plan_sha256):
        raise WorkflowError("context recovery requires an exact plan SHA-256")
    runner = runner or CommandRunner()
    root = Path(root)
    spec, context = _validate_parent(runner, root, registry, bead_id)
    parent_path = journal_path(runner, spec)
    child_path, record_path = _paths(parent_path, bead_id)
    paths = {"parent": parent_path, "child": child_path}
    parent_image, child_image = _safe_image(parent_path), _safe_image(child_path)
    record = None
    if record_path.exists() or record_path.is_symlink():
        record, record_image, backups = _record(record_path)
        plan, digest = record["plan"], record["plan_sha256"]
        if plan["parent"] != spec.payload() or plan["child"]["bead_id"] != bead_id:
            raise WorkflowError("context recovery parent/child binding drift")
        child = BeginSpec(**plan["child"])
        child_image = _safe_image(backups["child"])
    else:
        journal = load_journal(child_path)
        _require_partial(journal)
        child, _, bead = derive_begin_spec(runner, Path(spec.canonical_root), bead_id,
                                          slug=journal["spec"].get("slug"), registry=registry)
        child = replace(child, base_commit=journal["spec"].get("base_commit"))
        require_journal_spec(journal, child)
        require_external_candidate(bead)
        if bead.get("status") != "open" or OWNER_KEY in bead.get("metadata", {}):
            raise WorkflowError("context recovery child must be open and unowned")
        parent_journal = load_journal(parent_path)
        if (parent_journal["phase"] != "ready"
                or any(item.get("state") != "verified" for item in parent_journal.get("coordination", {}).values())
                or bead_id in parent_journal.get("attached_bead_ids", [])):
            raise WorkflowError("context recovery parent has conflicting transactions")
        plan = {"schema": SCHEMA, "parent": spec.payload(), "child": child.payload(),
                "binding": owner_binding(spec, context)}
        digest = None
    child_context = build_context(Path(child.worktree), registry)
    require_workspace(runner, child, child_context)
    if any(getattr(child, field) != getattr(spec, field) for field in (
            "canonical_root", "worktree_root", "project_id", "rig", "workflow_profile")):
        raise WorkflowError("context recovery scope mismatch")
    inherited = inherited_contexts(runner, child)
    if inherited != [_active_tracker(root, spec.bead_id).parent.name]:
        raise WorkflowError("child did not inherit exactly the unfinished parent context")
    parent_head = git_value(runner, root, "rev-parse", "HEAD")
    if runner.run(["git", "-C", str(root), "merge-base", "--is-ancestor", parent_head, child.base_commit],
                  check=False).returncode:
        raise WorkflowError("parent head is not an ancestor of the preserved child base")
    facts = _facts(runner, root, spec, child, context, paths, registry)
    if record is None:
        plan["before"] = facts
        digest = _digest(plan)
        backups = _backups(record_path, plan, digest)
    elif record["state"] == "completed":
        if expected_plan_sha256 is not None and expected_plan_sha256 != digest:
            raise WorkflowError("context recovery plan digest drift")
        if facts != record["after"]:
            raise WorkflowError("completed context recovery drift; refuse replay")
        return result_payload("reconcile-context", "unchanged", plan_sha256=digest)
    else:
        expected = json.loads(canonical_json(plan["before"]))
        if _safe_image(child_path) == _retired(plan, digest, child_image):
            expected["journals"]["child"] = _pin(_safe_image(child_path))
        if facts != expected:
            raise WorkflowError("partial context recovery is ambiguous; preserve and reconcile explicitly")
    if expected_plan_sha256 is None:
        return result_payload("reconcile-context", "planned", plan_sha256=digest, plan=plan)
    if expected_plan_sha256 != digest:
        raise WorkflowError("context recovery plan digest drift")
    evidence_images = {name: _safe_image(Path(facts["evidence"][name]["path"]))
                       for name in ("plan", "tracker")}
    if any(_pin(image) != {key: value for key, value in facts["evidence"][name].items() if key != "path"}
           for name, image in evidence_images.items()):
        raise WorkflowError("context recovery evidence changed before preparation")
    if record is None:
        for name, image in (("parent", parent_image), ("child", child_image)):
            _backup(backups[name], image)
        record = {"schema": SCHEMA, "state": "prepared", "plan": plan, "plan_sha256": digest}
        record_image = _encoded(record, (b"", 0o600, os.geteuid(), os.getegid()))
        _backup(record_path, record_image)
    if (_facts(runner, root, spec, child, context, paths, registry) != facts
            or _safe_image(record_path) != record_image):
        raise WorkflowError("context recovery inputs changed before mutation")
    retired = _retired(plan, digest, child_image)
    if _safe_image(child_path) != retired:
        _write_image(child_path, retired)
    require_reconciled_standalone(runner, spec, context, bead_id)
    from workflow_coordinate import coordinate

    coordinate(root, spec.bead_id, "depend", {"blocker": bead_id}, runner, registry=registry)
    check_active_ownership(runner, root, registry=registry)
    if "STATE: READY" not in run_readiness(runner, root):
        raise WorkflowError("reconciled parent did not pass readiness")
    after = _facts(runner, root, spec, child, context, paths, registry)
    _verify_postimage(plan, after, evidence_images)
    _verify_parent_journal(plan, json.loads(_safe_image(backups["parent"])[0]), load_journal(parent_path), after)
    primary, attached = after["beads"]["parent"], after["beads"]["child"]
    require_binding(primary, plan["binding"])
    require_binding(attached, plan["binding"])
    if (_body(primary) != _body(plan["before"]["beads"]["parent"])
            or _edges(primary) != _edges(plan["before"]["beads"]["parent"]) | {(bead_id, "blocks")}
            or _safe_image(child_path) != retired
            or _safe_image(record_path) != record_image):
        raise WorkflowError("context recovery unexpected postimage; preserve and stop")
    record.update(state="completed", after=after)
    completed_image = _encoded(record, record_image)
    _write_image(record_path, completed_image)
    if _safe_image(record_path) != completed_image:
        raise WorkflowError("context recovery completion readback differs")
    return result_payload("reconcile-context", "reconciled", plan_sha256=digest,
                          parent_bead=spec.bead_id, bead_id=bead_id,
                          backups={name: str(path) for name, path in backups.items()})


def _verify_postimage(plan, after, images):
    before = plan["before"]
    child_id, parent_id = plan["child"]["bead_id"], plan["parent"]["bead_id"]
    expected_child = _body(before["beads"]["child"])
    expected_child.update(status="in_progress", metadata={**expected_child.get("metadata", {}), OWNER_KEY: plan["binding"]})
    observed_child = _body(after["beads"]["child"])
    expected_child.pop("started_at", None)
    observed_child.pop("started_at", None)
    if (observed_child != expected_child
            or _edges(after["beads"]["child"]) != _edges(before["beads"]["child"])
            or {tuple(edge) for edge in after["reverse_edges"]["child"]}
            != {tuple(edge) for edge in before["reverse_edges"]["child"]} | {(parent_id, "blocks")}
            or after["reverse_edges"]["parent"] != before["reverse_edges"]["parent"]):
        raise WorkflowError("context recovery unexpected child delta")
    expected_text = {
        "plan": _render_plan_attachment(images["plan"][0].decode(), parent_id, child_id)[0],
        "tracker": _render_tracker_attachment(images["tracker"][0].decode(), child_id,
                                               before["beads"]["child"]["title"]),
    }
    for name, text in expected_text.items():
        expected_image = (text.encode(), *images[name][1:])
        if after["evidence"][name] != {"path": before["evidence"][name]["path"], **_pin(expected_image)}:
            raise WorkflowError("context recovery unexpected plan/tracker delta")
    for field in ("pointers", "child_workspace", "registry", "sources"):
        if before[field] != after[field]:
            raise WorkflowError("context recovery changed preserved inputs")
    if before["evidence"]["session_state"] != after["evidence"]["session_state"]:
        raise WorkflowError("context recovery changed the parent session")
    contexts = [json.loads(canonical_json(facts["context"])) for facts in (before, after)]
    for context in contexts:
        context["git"].pop("clean")
        context["git"].pop("status_entries")
    if contexts[0] != contexts[1]:
        raise WorkflowError("context recovery registration/workspace drift")
    allowed = {str(Path(before["evidence"][name]["path"]).relative_to(plan["parent"]["worktree"]))
               for name in ("plan", "tracker")}
    workspaces = [facts["parent_workspace"] for facts in (before, after)]
    if (workspaces[0]["head"] != workspaces[1]["head"]
            or {name: value for name, value in workspaces[0]["files"].items() if name not in allowed}
            != {name: value for name, value in workspaces[1]["files"].items() if name not in allowed}):
        raise WorkflowError("context recovery changed unrelated parent work")


def _verify_parent_journal(plan, before, after, facts):
    child_id, parent_id = plan["child"]["bead_id"], plan["parent"]["bead_id"]
    allowed = {"updated_at", "events", "coordination", "external_ownership", "attached_bead_ids"}
    if ({key: value for key, value in before.items() if key not in allowed}
            != {key: value for key, value in after.items() if key not in allowed}
            or after.get("attached_bead_ids") != [*before.get("attached_bead_ids", []), child_id]):
        raise WorkflowError("context recovery unexpected parent journal delta")
    request = {"bead_id": parent_id, "action": "depend", "fields": {"blocker": child_id}}
    request_id = _digest(request)
    intent = after.get("coordination", {}).get(request_id, {})
    expected = {"state": "verified", "request": request,
                "before": plan["before"]["beads"]["parent"], "blocker_before": plan["before"]["beads"]["child"],
                "result_bead": parent_id, "after": facts["beads"]["parent"],
                "before_sha256": bead_digest(plan["before"]["beads"]["parent"]),
                "after_sha256": bead_digest(facts["beads"]["parent"])}
    if (intent != expected or request_id in before.get("coordination", {})
            or after["coordination"] != {**before.get("coordination", {}), request_id: intent}):
        raise WorkflowError("context recovery unexpected coordination journal delta")
    ownership = after.get("external_ownership", {}).get(child_id, {})
    if (ownership.get("state") != "verified" or ownership.get("binding") != plan["binding"]
            or ownership.get("after") != facts["beads"]["child"]
            or after["external_ownership"] != {**before.get("external_ownership", {}), child_id: ownership}):
        raise WorkflowError("context recovery unexpected ownership journal delta")
    events = after.get("events", [])
    if len(events) != len(before.get("events", [])) + 1 or events[:-1] != before.get("events", []):
        raise WorkflowError("context recovery changed historical lifecycle events")
    event = events[-1]
    if ({key: value for key, value in event.items() if key != "at"}
            != {"action": "attach", "status": "ready", "attached_bead_id": child_id}
            or not isinstance(event.get("at"), str)):
        raise WorkflowError("context recovery unexpected lifecycle event")
