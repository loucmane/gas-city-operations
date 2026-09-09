"""Outer five-move relocation WAL composed with the existing leaf transaction.

There is intentionally no command-line apply entry point here. A separately
reviewed, source-bound caller must supply real preflight, sync and postflight
checks. A pending or ambiguous prior attempt is never resumed automatically.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from aegis_foundation.gate.session_authority import assert_no_pending_continuation, contained_path
from aegis_foundation.gate.session_transition import JOURNAL, SessionTransition, image
from workflow_common import atomic_write_json
from _core_layout_state import (
    CONFIG, PARENTS, RelocationError, canonical, check_external, digest, inspect,
    literal_root, relocate_path, require, tree, validate_manifest,
)


def fsync_directory(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def metadata(value: dict) -> dict:
    if value["kind"] == "file":
        data = base64.b64decode(value["data"], validate=True)
        return {"kind": "file", "mode": value["mode"], "uid": value["uid"],
                "gid": value["gid"], "size": len(data), "sha256": digest(data)}
    return value


class _OuterOwnedLeaf(SessionTransition):
    """Reuse leaf WAL writes, but reserve ALL rollback for the outer precheck.

    The base context manager normally restores its three leaves immediately.
    Here that would precede validation of the five moves and lose the failed
    postimages. This fixed-scope composition changes no shared helper behavior.
    """

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                self.record["status"] = "complete"
                self._save()
        finally:
            self.lock.__exit__(None, None, None)
        return False


class CoreLayoutTransaction:
    """One cooperative writer; callbacks and both locks belong to reviewed caller.

    The class checks its exact filesystem envelope; it does not impersonate a
    scheduler lock, independently grant ownership, or trust a review marker.
    """

    def __init__(self, root: Path, plan: dict, *, preflight, synchronize, postflight, fault=None):
        literal_root(root)
        validate_manifest(plan)
        require(str(root) == plan["root"], "plan targets a different root")
        self.root, self.plan = root, plan
        self.preflight, self.synchronize, self.postflight = preflight, synchronize, postflight
        self.fault = fault or (lambda stage: None)
        self.directory = Path(plan["common"]) / "gas-city-workflow/layout-relocations" / plan["plan_id"]
        self.record_path = self.directory / "transaction.json"
        self.record = {"schema": "gc.core-evidence-layout-transaction.v1", "plan_id": plan["plan_id"],
                       "plan_sha256": digest(canonical(plan)), "status": "prepared", "actions": []}
        self.leaf = None
        self.leaf_entered = False

    def _save(self):
        atomic_write_json(self.record_path, self.record)
        fsync_directory(self.directory)

    def _audit_path(self):
        common = Path(self.plan["common"])
        relative = self.directory.relative_to(common).as_posix()
        contained_path(common, relative, "relocation audit directory")
        for path in (self.directory.parent, self.directory):
            if path.exists():
                require(inspect(path) == {"kind": "directory", "mode": 0o700,
                                          "uid": os.getuid(), "gid": os.getgid()},
                        "audit directory metadata drift")

    def _current_wals(self):
        result = tree(self.root, ".aegis/state/session-continuations")
        result.update(tree(self.root, JOURNAL))
        return result

    def _check_before(self):
        check_external(self.root, self.plan)
        assert_no_pending_continuation(self.root)
        current = {}
        for source, destination in self.plan["moves"]:
            current.update(tree(self.root, source))
            require(not os.path.lexists(self.root / destination), "destination collision")
        require(current == self.plan["entries"], "source inventory drift")
        require({p: inspect(self.root / p) for p in self.plan["parents"]} == self.plan["parents"],
                "parent inventory drift")
        require(self._current_wals() == self.plan["wal_before"], "session WAL drift")
        require(inspect(self.root / ".codex/config.toml")["kind"] == "absent", "configuration drift")

    def _write_backup(self, relative: str, source: Path, expected: dict):
        destination = self.directory / "originals" / relative
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(inspect(source) == expected, "source changed before backup")
        if expected["kind"] == "directory":
            destination.mkdir(mode=expected["mode"], exist_ok=True)
            os.chmod(destination, expected["mode"])
        elif expected["kind"] == "link":
            destination.symlink_to(expected["target"])
        elif expected["kind"] == "file":
            data = source.read_bytes()
            require(digest(data) == expected["sha256"], "backup read drift")
            with destination.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fchmod(stream.fileno(), expected["mode"])
                os.fsync(stream.fileno())
        else:
            return
        if destination.lstat().st_gid != expected["gid"]:
            os.chown(destination, expected["uid"], expected["gid"], follow_symlinks=False)
        require(inspect(destination) == expected, "backup readback drift")
        fsync_directory(destination.parent)

    def _backups(self):
        for relative, expected in sorted(self.plan["entries"].items()):
            self._write_backup(relative, self.root / relative, expected)
        for relative, expected in self.plan["wal_before"].items():
            self._write_backup(relative, self.root / relative, expected)
        for key, item in self.plan["external"].items():
            self._write_backup("external/" + key, Path(item["path"]), item["image"])
        self.record["backups_complete"] = True
        self.record["backup_state"] = tree(self.directory, "originals")
        self._save()

    def _check_backups(self, record):
        plan_path = self.directory / "plan.json"
        value = inspect(plan_path)
        require(value["kind"] == "file" and value["mode"] == 0o600, "saved plan metadata drift")
        require(plan_path.read_bytes() == (json.dumps(self.plan, indent=2, sort_keys=True) + "\n").encode(),
                "saved plan bytes drift")
        require(record.get("backups_complete") is True, "backups are incomplete")
        require(tree(self.directory, "originals") == record.get("backup_state"), "backup inventory drift")
        expected = {**self.plan["entries"], **self.plan["wal_before"]}
        expected.update({"external/" + k: v["image"] for k, v in self.plan["external"].items()})
        for relative, before in expected.items():
            require(inspect(self.directory / "originals" / relative) == before, "original backup drift")

    def _mkdir(self, relative):
        path = self.root / relative
        require(not os.path.lexists(path), "parent appeared before creation")
        action = {"kind": "parent", "path": relative, "state": "intent"}
        self.record["actions"].append(action)
        self._save()
        path.mkdir(mode=0o700)
        os.chmod(path, 0o755)
        fsync_directory(path.parent)
        require(inspect(path) == {"kind": "directory", "mode": 0o755,
                                 "uid": os.getuid(), "gid": os.getgid()}, "parent creation readback failed")
        action["state"] = "applied"
        self._save()
        self.fault("parent:" + relative)

    def _rename(self, source, destination):
        src, dst = self.root / source, self.root / destination
        require(not os.path.lexists(dst), "rename destination collision")
        require(src.lstat().st_dev == dst.parent.stat().st_dev, "cross-device relocation refused")
        action = {"kind": "move", "source": source, "destination": destination, "state": "intent"}
        self.record["actions"].append(action)
        self._save()
        # The reviewed caller holds both cooperative locks and excludes other
        # writers. No distributed compare-and-swap guarantee is claimed here.
        src.rename(dst)
        fsync_directory(src.parent)
        fsync_directory(dst.parent)
        action["state"] = "applied"
        self._save()
        self.fault("move:" + source)

    def _move_locations(self):
        locations = {}
        for source, destination in self.plan["moves"]:
            src, dst = self.root / source, self.root / destination
            left, right = os.path.lexists(src), os.path.lexists(dst)
            require(left != right, "ambiguous move state; preserve both sides")
            locations[source] = destination if right else source
        return locations

    def _check_data(self, *, terminal=False):
        """Validate every entry, extra/missing path and known leaf alternative."""
        check_external(self.root, self.plan)
        locations = self._move_locations()
        actual, expected = {}, {}
        steps = {s["path"]: s for s in self.leaf.record["steps"]} if self.leaf else {}
        for source, location in locations.items():
            actual.update(tree(self.root, location))
            for relative, value in self.plan["entries"].items():
                if relative == source or relative.startswith(source + "/"):
                    current = location + relative[len(source):]
                    expected[current] = value
        require(set(actual) == set(expected), "unexpected or missing evidence entry")
        for relative, value in actual.items():
            alternatives = [expected[relative]]
            if relative in steps:
                alternatives += [metadata(steps[relative]["before"]), metadata(steps[relative]["after"])]
            require(value in alternatives, "unexplained evidence mutation: " + relative)
            if terminal and relative in steps:
                require(value == metadata(steps[relative]["after"]), "terminal leaf does not match WAL")
        config = inspect(self.root / ".codex/config.toml")
        step = steps.get(".codex/config.toml")
        alternatives = [{"kind": "absent"}]
        if step:
            alternatives.append(metadata(step["after"]))
        require(config in alternatives, "unexpected config mutation")
        if terminal:
            require(step and config == metadata(step["after"]), "terminal config missing")
            require(all(locations[s] == d for s, d in self.plan["moves"]), "incomplete relocation")
        require(inspect(self.root / "engdocs") == self.plan["parents"]["engdocs"], "preserved parent drift")
        created = {a["path"] for a in self.record["actions"] if a["kind"] == "parent"}
        for relative in PARENTS:
            value = inspect(self.root / relative)
            if relative not in created:
                require(value["kind"] == "absent", "unowned parent appeared")
            elif terminal and value["kind"] == "absent":
                raise RelocationError("terminal parent is missing")
            elif value["kind"] != "absent":
                require(value in ({"kind": "directory", "mode": mode, "uid": os.getuid(), "gid": os.getgid()}
                                  for mode in ((0o755,) if terminal else (0o700, 0o755))), "created parent drift")
        # Cover siblings of moved roots too, before ANY rollback write.
        children = {p: set() for p in PARENTS}
        paths = [d for s, d in self.plan["moves"] if locations[s] == d]
        paths += [p for p in PARENTS if os.path.lexists(self.root / p)]
        if config["kind"] != "absent":
            paths.append(".codex/config.toml")
        for path in paths:
            parent = str(Path(path).parent)
            if parent in children:
                children[parent].add(Path(path).name)
        for relative, names in children.items():
            parent = self.root / relative
            if parent.exists():
                require({p.name for p in parent.iterdir()} == names, "unexpected child of created parent")
        return locations

    def _check_wals(self):
        if not self.leaf:
            require(self._current_wals() == self.plan["wal_before"], "session WAL changed without leaf transaction")
            return False
        current = self._current_wals()
        old = self.plan["wal_before"]
        for relative, value in old.items():
            if relative != JOURNAL:
                require(current.get(relative) == value, "prior WAL archive drift")
        prior_path = self.directory / "originals" / JOURNAL
        prior = json.loads(prior_path.read_text())
        archived = f'.aegis/state/session-continuations/{prior["id"]}.json'
        expected_paths = set(old)
        if archived in current:
            require(current[archived] == old[JOURNAL], "prior current WAL not archived exactly")
            expected_paths.add(archived)
        require(set(current) == expected_paths, "unexpected WAL path")
        if current[JOURNAL] == old[JOURNAL]:
            require(not self.leaf_entered and not self.leaf.record["steps"], "leaf WAL unexpectedly reverted")
            return False  # Failed __enter__: no new leaf WAL or leaf writes.
        require(archived in current, "prior current WAL was not archived")
        actual = json.loads((self.root / JOURNAL).read_text())
        require((self.root / JOURNAL).read_bytes() == (json.dumps(actual, indent=2) + "\n").encode(),
                "current leaf WAL serialization drift")
        # A failed final commit can leave the exact pending predecessor of the
        # complete record. No other alternate content or missing steps qualify.
        allowed = [self.leaf.record]
        if self.leaf.record["status"] == "complete":
            allowed.append({**self.leaf.record, "status": "pending"})
        require(actual in allowed, "current leaf WAL drift")
        wal_image = inspect(self.root / JOURNAL)
        require(wal_image["mode"] == 0o600 and wal_image["gid"] == os.getgid(), "leaf WAL metadata drift")
        return True

    def _accepted_state(self):
        value = tree(self.root, "engdocs/workflow")
        value.update(tree(self.root, ".codex"))
        value.update(self._current_wals())
        value.update({p: inspect(self.root / p) for p in ("engdocs", *PARENTS)})
        return value

    def _preserve_failed(self):
        data = {}
        for source, destination in self.plan["moves"]:
            for relative in (source, destination):
                for name, value in tree(self.root, relative).items():
                    path = self.root / name
                    data[name] = {**value, **({"data_b64": base64.b64encode(path.read_bytes()).decode()}
                                            if value["kind"] == "file" else {})}
        for relative in (".codex/config.toml", JOURNAL):
            path = self.root / relative
            value = inspect(path)
            data[relative] = {**value, **({"data_b64": base64.b64encode(path.read_bytes()).decode()}
                                        if value["kind"] == "file" else {})}
        atomic_write_json(self.directory / "failed-postimages.json", data)
        fsync_directory(self.directory)

    def _rollback(self):
        if self.record.get("backups_complete"):
            self._check_backups(self.record)
        locations = self._check_data()
        leaf_current = self._check_wals()
        self._preserve_failed()  # Preserve exact known postimages before restoration.
        if leaf_current and self.leaf.record["status"] != "rolled_back":
            self.leaf.rollback()
        for source, destination in reversed(self.plan["moves"]):
            if locations[source] == destination:
                require(not os.path.lexists(self.root / source), "rollback destination collision")
                (self.root / destination).rename(self.root / source)
                fsync_directory((self.root / source).parent)
                fsync_directory((self.root / destination).parent)
        created = {a["path"] for a in self.record["actions"] if a["kind"] == "parent"}
        for relative in reversed(PARENTS):
            if relative in created and (self.root / relative).exists():
                (self.root / relative).rmdir()  # Only owned, empty parents.
                fsync_directory((self.root / relative).parent)
        check_external(self.root, self.plan)
        restored = {}
        for source, destination in self.plan["moves"]:
            restored.update(tree(self.root, source))
            require(not os.path.lexists(self.root / destination), "rollback left a destination")
        require(restored == self.plan["entries"], "rollback original evidence mismatch")
        require({p: inspect(self.root / p) for p in self.plan["parents"]} == self.plan["parents"],
                "rollback parent mismatch")
        self._check_wals()

    def apply(self):
        """Caller must hold workflow_lock then session_lock across this call."""
        self.preflight()
        check_external(self.root, self.plan)
        self._audit_path()
        if self.directory.exists():
            info = inspect(self.record_path)
            require(info["kind"] == "file" and info["mode"] == 0o600, "prior attempt lacks an intact terminal record")
            record = json.loads(self.record_path.read_text())
            require(record.get("schema") == self.record["schema"] and record.get("plan_id") == self.plan["plan_id"],
                    "prior record identity drift")
            require(record.get("plan_sha256") == digest(canonical(self.plan)), "prior plan binding drift")
            require(record.get("status") == "complete", "prior attempt is not complete; do not retry")
            self._check_backups(record)
            require(self._accepted_state() == record.get("accepted"), "accepted state drift; refuse replay")
            require(all(not os.path.lexists(self.root / s) for s, _ in self.plan["moves"]), "old source reappeared")
            self.postflight()
            return {"status": "PASS", "idempotent": True, "plan_id": self.plan["plan_id"]}
        self._check_before()
        self.directory.parent.mkdir(mode=0o700, exist_ok=True)
        self.directory.mkdir(mode=0o700)
        self._audit_path()
        atomic_write_json(self.directory / "plan.json", self.plan)
        self._save()
        try:
            self._backups()
            self._check_before()
            for relative in PARENTS:
                self._mkdir(relative)
            for source, destination in self.plan["moves"]:
                self._rename(source, destination)
            config = self.root / ".codex/config.toml"
            plan = self.root / "engdocs/workflow/plans" / self.plan["plan_name"]
            sync = self.root / "engdocs/workflow/plan-state/sync.log"
            self.leaf = _OuterOwnedLeaf(self.root, self.plan["bead"], [config, plan, sync], lock_held=True)
            require(self.leaf.record["created_directories"] == [], "inner transaction would create a parent")
            self.record.update(status="leaf-pending", leaf_id=self.leaf.record["id"])
            self._save()
            with self.leaf:
                self.leaf_entered = True
                self.leaf.write(config, CONFIG)
                self.fault("config")
                self.leaf.write(plan, base64.b64decode(self.plan["plan_after_b64"], validate=True))
                self.fault("plan")
                original_sync = json.loads((self.directory / "originals/.plan_state/sync.log").read_text())
                self.synchronize(self.leaf, plan, sync)
                current_sync = json.loads(sync.read_text())
                require(current_sync[:-1] == original_sync and len(current_sync) == len(original_sync) + 1,
                        "sync changed historical records")
                require(current_sync[-1]["plan"] == plan.relative_to(self.root).as_posix(), "sync selected wrong plan")
                self.fault("sync")
            self.record["status"] = "leaf-committed"
            self._save()
            self.fault("leaf-committed")
            postflight = self.postflight()
            self.fault("postflight")
            self._check_data(terminal=True)
            self._check_wals()
            self.record.update(status="complete", accepted=self._accepted_state(), postflight=postflight)
            self._save()
            return {"status": "PASS", "idempotent": False, "plan_id": self.plan["plan_id"]}
        except Exception as failure:
            self.record["failure"] = str(failure)
            try:
                self._rollback()
                self.record["status"] = "rolled_back"
                self._save()
            except Exception as rollback_failure:
                self.record.update(status="unresolved", rollback_failure=str(rollback_failure))
                self._save()
                raise RelocationError("rollback unresolved; preserve evidence and stop") from rollback_failure
            raise
