"""Real validator/plan-sync adapter for the one reviewed Core relocation.

Only the source-bound launcher may call this in production. It adds no workflow
event to the Core ownership journal and never runs a lifecycle command.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import types

from _core_layout_state import canonical, check_external, digest, external_paths, freeze, inspect, require
from _core_layout_transaction import CoreLayoutTransaction
from aegis_foundation.gate.session_transition import session_lock
from project_context import DEFAULT_REGISTRY, build_context
from workflow_common import CommandRunner, managed_environment
from workflow_lock import workflow_lock
from workflow_portable import run_portable_readiness

CORE = Path("/home/loucmane/gascity-core-worktrees/ga-ecwh-typed-worker-receipts")
BEAD = "ga-ecwh"
GC = "/home/loucmane/gascity/bin/gc"
GO = "/home/loucmane/.local/bin/go"
CITY = "/home/loucmane/gascity/city"
SUPERVISOR = "gascity-supervisor-home-42adab5d.service"
BUNDLE_SCHEMA = "gc.core-evidence-layout-execution.v1"


def tool_pins():
    result = {}
    for name in (GC, GO, "/home/loucmane/gascity/bin/bd", "/usr/bin/git", "/usr/bin/systemctl"):
        path = Path(name).resolve(strict=True)
        info = path.stat()
        require(path.is_file() and info.st_uid in {0, os.getuid()} and not info.st_mode & 0o022,
                "unexpected executable owner/permissions")
        result[name] = {"resolved": str(path), "sha256": digest(path.read_bytes()), "mode": info.st_mode & 0o7777}
    return result


def observe(runner):
    env = managed_environment()
    rigs = json.loads(runner.run([GC, "--city", CITY, "rig", "list", "--json"], env=env).stdout)
    sessions = json.loads(runner.run([GC, "--city", CITY, "session", "list", "--json"], env=env).stdout)
    require(rigs.get("ok") is True and sessions.get("ok") is True, "city observation failed")
    projects = [r for r in rigs["rigs"] if r.get("hq") is False]
    require({r["name"] for r in projects} == {"gascity", "gas-city-template", "hpfetcher", "blog"}
            and len(projects) == 4, "project rig inventory drift")
    require(all(r.get("suspended") is True and r.get("running") is False for r in projects),
            "every project rig must remain suspended")
    require(sessions.get("sessions") == [] and sessions["summary"]["total"] == 0,
            "native session residue")
    fields = ("MainPID", "NRestarts", "ExecMainStartTimestampMonotonic", "ActiveState", "SubState")
    unit = runner.run(["/usr/bin/systemctl", "--user", "show", SUPERVISOR,
                       *(item for field in fields for item in ("-p", field))], env=env).stdout
    state = dict(line.split("=", 1) for line in unit.splitlines())
    require(set(state) == set(fields) and state["ActiveState"] == "active"
            and state["SubState"] == "running" and state["NRestarts"] == "0"
            and int(state["MainPID"]) > 0 and int(state["ExecMainStartTimestampMonotonic"]) > 0,
            "supervisor is not stable and active")
    pid = state["MainPID"]
    stat_fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    state["start_ticks"] = stat_fields[19]
    state["boot_id"] = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    return {"rigs": sorted(projects, key=lambda r: r["name"]), "sessions": [], "supervisor": state}


def normalize_image(value):
    result = {k: v for k, v in value.items() if k not in {"source", "destination", "path"}}
    if "mode" in result:
        result["mode"] = int(result["mode"], 8)
    if result["kind"] == "symlink":
        result["kind"] = "link"
    return result


def compare_baseline(plan, baseline):
    require(baseline["schema"] == "ga-ecwh.layout-relocation-review-inventory.v1", "wrong baseline schema")
    require(plan["root"] == baseline["root"] and plan["head"] == baseline["head"]
            and plan["branch"] == baseline["branch"], "baseline identity drift")
    require(plan["moves"] == [[p["source"], p["destination"]] for p in baseline["maps"]], "baseline move drift")
    require(plan["entries"] == {v["source"]: normalize_image(v) for v in baseline["entries"]},
            "evidence changed since reviewed baseline; explain and re-freeze")
    require(plan["protected"] == {k: normalize_image(v) for k, v in baseline["protected"].items()},
            "protected inventory drift")
    for name, value in baseline["session_wal"].items():
        require(plan["wal_before"].get(name) == normalize_image(value), "baseline WAL drift")
    require({p for p, v in plan["wal_before"].items() if v["kind"] == "file"} == set(baseline["session_wal"]),
            "baseline WAL inventory drift")
    for key, old_key in (("index", "index"), ("ownership", "journal")):
        require(plan["external"][key] == {"path": baseline[old_key]["path"],
                                         "image": normalize_image(baseline[old_key])}, "baseline external drift")
    require(plan["tracked_diff_sha256"] == baseline["tracked_diff_sha256"], "baseline tracked diff drift")


def load_sync_source(source):
    path = source / "scripts/codex-task"
    module = types.ModuleType("core_layout_bound_plan_sync")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    # The launcher has verified every runtime file against the signed source
    # tree and disabled repository bytecode loading before this import.
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


class BoundExecution:
    def __init__(self, root, source, source_identity, source_check, *, runner=None, registry=DEFAULT_REGISTRY):
        self.root, self.source = root, source
        self.source_identity, self.source_check = source_identity, source_check
        self.runner, self.registry = runner or CommandRunner(), registry

    def readiness(self):
        self.source_check()
        context = build_context(self.root, self.registry)
        require(context["project"]["id"] == "gas-city" and context["project"]["rig"] == "gascity"
                and context["workspace"]["location"] == "linked-worktree", "Core project identity drift")
        require("STATE: READY" in run_portable_readiness(self.runner, self.root), "Core is not READY")

    def prepare(self, baseline, baseline_sha):
        self.readiness()
        self.existing_lock()
        runtime = observe(self.runner)
        policy = {"schema": BUNDLE_SCHEMA, "source": self.source_identity,
                  "baseline_sha256": baseline_sha, "runtime": runtime, "tools": tool_pins()}
        with workflow_lock(self.runner, self.root, self.registry), session_lock(self.root):
            self.readiness()
            plan = freeze(self.root, BEAD, digest(canonical(policy)), list(baseline["protected"]))
            compare_baseline(plan, baseline)
            require(observe(self.runner) == runtime and tool_pins() == policy["tools"], "preparation drift")
        return {**policy, "plan": plan}

    def existing_lock(self):
        path = external_paths(self.root, BEAD)["common"] / "gas-city-workflow/source-transition.lock"
        value = inspect(path)
        require(value["kind"] == "file" and value["mode"] == 0o600,
                "existing workflow lock is required; prepare must not create one")

    def apply(self, bundle):
        require(set(bundle) == {"schema", "source", "baseline_sha256", "runtime", "tools", "plan"}
                and bundle["schema"] == BUNDLE_SCHEMA, "invalid execution bundle")
        require(bundle["source"] == self.source_identity, "execution source drift")
        plan = bundle["plan"]
        require(plan["bead"] == BEAD and plan["root"] == str(self.root), "wrong Core work identity")
        require(plan["policy_sha256"] == digest(canonical({k: v for k, v in bundle.items() if k != "plan"})),
                "execution policy drift")
        self.source_check()
        self.existing_lock()
        sync_source = load_sync_source(self.source)

        def before():
            self.readiness()
            require(observe(self.runner) == bundle["runtime"], "runtime epoch or rig drift")
            require(tool_pins() == bundle["tools"], "toolchain drift")

        def synchronize(txn, active, sync):
            trackers = list((self.root / "engdocs/workflow/work-tracking/active").glob(f"*-{BEAD}-*-ACTIVE/TRACKER.md"))
            require(len(trackers) == 1, "relocated tracker is ambiguous")
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    sync_source.handle_plan_sync(argparse.Namespace(
                        target_dir=str(self.root), plan=str(active.relative_to(self.root)),
                        tracker=str(trackers[0].relative_to(self.root)), folder=None,
                        dry_run=False, _session_transaction=txn,
                    ))
            finally:
                transaction.record["plan_sync_stdout"] = output.getvalue()
                transaction._save()

        def after():
            before()
            # An exact replay has already checked all accepted images. Keep it
            # read-only: validate the prior bound result, do not re-run Go or log.
            if transaction.record_path.exists():
                record = json.loads(transaction.record_path.read_text())
                if record.get("status") == "complete":
                    proof = record.get("postflight", {})
                    require(proof.get("command") == [GO, "test", "-json", "-count=1", "./test/docsync"]
                            and proof.get("returncode") == 0 and proof.get("tests_passed", 0) > 0,
                            "completed transaction lacks documentation proof")
                    return proof
            argv = [GO, "test", "-json", "-count=1", "./test/docsync"]
            env = {**managed_environment(), "GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOFLAGS": "-mod=readonly"}
            result = self.runner.run(argv, cwd=self.root, env=env, check=False)
            proof = {"command": argv, "returncode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr}
            transaction.record["docsync_attempt"] = proof
            transaction._save()  # Preserve failed output before the outer rollback.
            events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            require(all(isinstance(event, dict) for event in events), "invalid documentation result event")
            passed = sum(e.get("Action") == "pass" and "Test" in e for e in events)
            proof["tests_passed"] = passed
            transaction._save()
            require(result.returncode == 0 and passed > 0 and not any(e.get("Action") in {"fail", "skip"} for e in events),
                    "Core documentation checks did not all pass")
            before()
            check_external(self.root, plan)
            return proof

        transaction = CoreLayoutTransaction(self.root, plan, preflight=before, synchronize=synchronize, postflight=after)
        with workflow_lock(self.runner, self.root, self.registry), session_lock(self.root):
            return transaction.apply()
