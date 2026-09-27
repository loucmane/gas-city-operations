"""gct-oak5 split package: close the stale workflow gct-wn1m and create the handover step Beads.

One quiet step (plan r15, sections "Decisions" and "Beads"):
1. preconditions: the city and every rig suspended, no open session Bead, the gct-wn1m member set
   exactly as pinned, no handover Bead yet;
2. before-snapshots of the Template and city stores (`bd export --all`);
3. close gct-wn1m: controls first, then work steps, then the root if Core has not closed it, each
   with gc.work_outcome=abandoned and a close reason naming the operator decision;
4. create the closed spec holders, the closed empty image holders H1 and H2, then the open,
   unrouted steps C1, X and C2 (label handover), with step -> gct-oak5 relates-to edges and the
   C1 blocks X blocks C2 chain;
5. after-snapshots, an attribution check of every changed row, the end-state checks and the
   lane-eligible queue audit.

Refuses before any write on a failed precondition. After the first write it never retries: a
failure records what happened and exits non-zero for the coordinator (the runner halts).
Output: <stage>/record.json (always written once the stage exists) and the snapshots.
Entry: source-launch.py <this file> <sha256> <stage directory that must not exist>.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTS = HERE / "texts"
TEXT_SHA = {"C1-spec.md": "81d4cd9902ca482bf21f37c46ad58f5814236daa8ef2aafcb4b67558bfdc4f49", "C2-spec.md": "a7d07602eda935cebf78d94dbe495036d6d380b118393e60b1ac7665ffed2509", "X-spec.md": "e5f48c052e409d18f19a0aaca973d81af0f762e81f6e373f1530f5c565cb83cd", "step.md": "a318e6e5e093584eecd6294e203714b2ec61011803fe4a12c82471fd6f92108f"}
GC = "/home/loucmane/gascity/bin/gc"
CITY = "/home/loucmane/gascity/city"
RIG = "gas-city-template"
ENV = {
    "GC_HOME": "/home/loucmane/gascity/home",
    "PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin",
    "GIT_OPTIONAL_LOCKS": "0",
    "HOME": "/home/loucmane",
}
ROOT = "gct-oak5"
WN1M = "gct-wn1m"
CONTROLS = ("gct-20mc", "gct-dh6u")
WORK = ("gct-af6u", "gct-svpm", "gct-v7yb")
ALREADY_CLOSED = ("gct-zkfz",)
MEMBERS = frozenset((WN1M,) + CONTROLS + WORK + ALREADY_CLOSED)
CONTROL_KINDS = frozenset({"retry", "ralph", "check", "retry-eval", "fanout", "drain", "scope-check", "workflow-finalize"})
CLOSE_REASON = ("Obsolete: stale 2026-08 do-work workflow gct-wn1m, closed before the gct-oak5 handover "
                "on the operator decision of 2026-09-27 (Close as obsolete; ga-e0t1).")
LANE_TARGETS = frozenset({
    "gas-city-template/gc.implementation-worker", "gc.implementation-worker",
    "gas-city-template/gc.implementation-worker-1",
    "gas-city-template/codex", "codex", "gas-city-template/codex-1", "gas-city-template/codex-2",
})
LANE_TEMPLATES = ("gas-city-template/gc.implementation-worker", "gas-city-template/codex")
STEPS = (
    ("C1", "Claude", "/home/loucmane/gascity/bin/bd show"),
    ("X", "Template codex", "/home/loucmane/gascity/bin/gc bd show"),
    ("C2", "Claude", "/home/loucmane/gascity/bin/bd show"),
)
ID = re.compile(r"^gct-[a-z0-9]{2,12}$")
MAX_VIEW = 9000


class Refused(Exception):
    pass


def gc(*args, rig=True, check=True):
    argv = [GC, "--city", CITY] + (["--rig", RIG] if rig else []) + list(args)
    done = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=120)
    if check and done.returncode != 0:
        raise Refused(f"{' '.join(args[:3])} exit {done.returncode}: {done.stderr.strip()[:400]}")
    return done


def export(store_rig):
    out = gc("bd", "export", "--all", rig=store_rig).stdout
    rows = {}
    for line in out.splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["id"]] = row
    return out, rows


def meta(row):
    return row.get("metadata") or {}


def verify_texts():
    for name, want in TEXT_SHA.items():
        got = hashlib.sha256((TEXTS / name).read_bytes()).hexdigest()
        if got != want:
            raise Refused(f"text {name} digest {got} != {want}")
    if set(TEXT_SHA) != {p.name for p in TEXTS.iterdir()}:
        raise Refused("text set differs from the pinned set")


def wn1m_members(rows):
    found = {WN1M}
    for row in rows.values():
        if meta(row).get("gc.root_bead_id") == WN1M:
            found.add(row["id"])
        for dep in row.get("dependencies") or []:
            if dep.get("depends_on_id") == WN1M or dep.get("issue_id") == WN1M:
                found.add(row["id"])
                found.add(dep.get("depends_on_id"))
    return found


def lane_eligible(template_rows, city_rows, identities):
    hits = []
    for store, rows in (("template", template_rows), ("city", city_rows)):
        for row in rows.values():
            if row.get("status") not in ("open", "in_progress"):
                continue
            m = meta(row)
            routed = m.get("gc.routed_to") or ""
            if routed in LANE_TARGETS:
                hits.append((store, row["id"], "routed", routed))
            if m.get("gc.kind") == "workflow" and not routed and (m.get("gc.run_target") or "") in LANE_TARGETS:
                hits.append((store, row["id"], "run_target", m.get("gc.run_target")))
            if row.get("issue_type") != "message" and (row.get("assignee") or "") in identities:
                hits.append((store, row["id"], "assigned", row.get("assignee")))
    return hits


def preconditions(record):
    status = gc("status", rig=False, check=False).stdout
    if not re.search(r"^\s*Suspended:\s+yes\s*$", status, re.M):
        raise Refused("city is not suspended")
    rigs = json.loads(gc("rig", "list", "--json", rig=False).stdout)["rigs"]
    awake = [r["name"] for r in rigs if r.get("name") != "city" and not r.get("suspended")]
    if awake:
        raise Refused(f"rigs not suspended: {awake}")
    record["rigs"] = {r["name"]: r.get("suspended") for r in rigs}


def main(stage_arg):
    stage = Path(stage_arg)
    if stage.exists() or stage.is_symlink():
        raise SystemExit(f"stage already exists: {stage}")
    stage.mkdir(mode=0o700)
    record = {"schema": "gct-oak5.split.v1", "phase": "preconditions", "writes": []}
    try:
        return run(stage, record)
    except Refused as exc:
        record["refused"] = str(exc)
        print(f"REFUSED in {record['phase']}: {exc}")
        return 1
    finally:
        (stage / "record.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")


def run(stage, record):
    verify_texts()
    preconditions(record)
    t_raw, t_before = export(True)
    c_raw, c_before = export(False)
    (stage / "template-before.jsonl").write_text(t_raw)
    (stage / "city-before.jsonl").write_text(c_raw)
    record["before_sha256"] = {"template": hashlib.sha256(t_raw.encode()).hexdigest(),
                               "city": hashlib.sha256(c_raw.encode()).hexdigest()}
    open_sessions = [r["id"] for r in c_before.values() if r.get("issue_type") == "session" and r.get("status") != "closed"]
    if open_sessions:
        raise Refused(f"open session Beads: {open_sessions}")
    members = wn1m_members(t_before)
    if members != MEMBERS:
        raise Refused(f"gct-wn1m members {sorted(members)} != pinned {sorted(MEMBERS)}")
    for bead in CONTROLS:
        if meta(t_before[bead]).get("gc.kind") not in CONTROL_KINDS:
            raise Refused(f"{bead} is not a control")
    for bead in WORK + (WN1M,):
        if meta(t_before[bead]).get("gc.kind") in CONTROL_KINDS:
            raise Refused(f"{bead} is a control")
    for bead in CONTROLS + WORK + (WN1M,):
        if t_before[bead].get("status") != "open" or t_before[bead].get("assignee"):
            raise Refused(f"{bead} is not open and unassigned")
    for bead in ALREADY_CLOSED:
        if t_before[bead].get("status") != "closed":
            raise Refused(f"{bead} is not closed")
    if t_before[ROOT].get("status") != "open":
        raise Refused("gct-oak5 is not open")
    if any("handover" in (r.get("labels") or []) for r in t_before.values()):
        raise Refused("a handover-labelled Bead already exists")
    identities = set(LANE_TARGETS) | {
        meta(r).get("session_name") for r in c_before.values()
        if r.get("issue_type") == "session" and meta(r).get("template") in LANE_TEMPLATES} - {None}
    before_hits = lane_eligible(t_before, c_before, identities)
    if [h for h in before_hits if h[1] != "gct-af6u"]:
        raise Refused(f"unexpected lane-eligible rows before: {before_hits}")
    record["lane_eligible_before"] = before_hits

    # Writes start here: never retried, every one recorded.
    record["phase"] = "close gct-wn1m"
    for bead in CONTROLS + WORK + (WN1M,):
        live = json.loads(gc("bd", "show", bead, "--json").stdout)
        live = live[0] if isinstance(live, list) else live
        if live.get("status") == "closed":
            record["writes"].append({"bead": bead, "closed_by": "core", "close_reason": live.get("close_reason")})
            continue
        gc("bd", "update", bead, "--set-metadata", "gc.work_outcome=abandoned")
        gc("bd", "close", bead, "--reason", CLOSE_REASON)
        record["writes"].append({"bead": bead, "closed_by": "coordinator"})

    record["phase"] = "create holders"
    ids = {}
    for name in ("C1", "X", "C2", "H1", "H2"):
        title = f"gct-oak5 handover {name} spec" if name[0] != "H" else f"gct-oak5 handover image {name}"
        args = ["bd", "create", title, "--type", "task", "--priority", "P2", "--labels", "handover-holder", "--silent"]
        if name[0] != "H":
            args += ["--description", "placeholder"]
        new = gc(*args).stdout.strip()
        if not ID.match(new):
            raise Refused(f"create {name} spec returned {new!r}")
        ids[name + ("-spec" if name[0] != "H" else "")] = new
        record["writes"].append({"bead": new, "created": name})
    record["phase"] = "create steps"
    for name, lane, _ in STEPS:
        new = gc("bd", "create", f"gct-oak5 handover step {name}", "--type", "task", "--priority", "P2",
                 "--labels", "handover", "--description", "placeholder", "--silent").stdout.strip()
        if not ID.match(new):
            raise Refused(f"create step {name} returned {new!r}")
        ids[name] = new
        record["writes"].append({"bead": new, "created": f"step {name}"})
    record["ids"] = ids

    record["phase"] = "render and write descriptions"
    subst = {"{C1}": ids["C1"], "{X}": ids["X"], "{C2}": ids["C2"], "{H1}": ids["H1"], "{H2}": ids["H2"]}
    rendered = {}
    for name, lane, show in STEPS:
        spec = (TEXTS / f"{name}-spec.md").read_text()
        for key, value in subst.items():
            spec = spec.replace(key, value)
        step = (TEXTS / "step.md").read_text()
        for key, value in (("{NAME}", name), ("{LANE}", lane), ("{SPEC}", ids[name + "-spec"]), ("{SHOW}", show)):
            step = step.replace(key, value)
        for text in (spec, step):
            if "{" in text and re.search(r"\{[A-Z0-9]+\}", text):
                raise Refused(f"unrendered placeholder in {name}")
            if len(text.encode()) > MAX_VIEW:
                raise Refused(f"{name} text over {MAX_VIEW} bytes")
        rendered[name + "-spec"] = spec
        rendered[name] = step
    for key, text in rendered.items():
        path = stage / f"{key}.md"
        path.write_text(text)
        gc("bd", "update", ids[key], "--body-file", str(path))
        record["writes"].append({"bead": ids[key], "description_sha256": hashlib.sha256(text.encode()).hexdigest()})

    record["phase"] = "close holders"
    for key in ("C1-spec", "X-spec", "C2-spec", "H1", "H2"):
        gc("bd", "close", ids[key], "--reason", "gct-oak5 handover holder (closed by design)")
        record["writes"].append({"bead": ids[key], "closed_by": "coordinator"})

    record["phase"] = "edges"
    for name, _, _ in STEPS:
        gc("bd", "dep", "add", ids[name], ROOT, "--type", "relates-to")
        record["writes"].append({"edge": [ids[name], ROOT, "relates-to"]})
    gc("bd", "dep", "add", ids["X"], ids["C1"], "--type", "blocks")
    gc("bd", "dep", "add", ids["C2"], ids["X"], "--type", "blocks")
    record["writes"].append({"edge": [ids["X"], ids["C1"], "blocks"]})
    record["writes"].append({"edge": [ids["C2"], ids["X"], "blocks"]})

    record["phase"] = "verify"
    t_raw2, t_after = export(True)
    c_raw2, c_after = export(False)
    (stage / "template-after.jsonl").write_text(t_raw2)
    (stage / "city-after.jsonl").write_text(c_raw2)
    record["after_sha256"] = {"template": hashlib.sha256(t_raw2.encode()).hexdigest(),
                              "city": hashlib.sha256(c_raw2.encode()).hexdigest()}
    problems = verify(record, ids, rendered, t_before, t_after, c_before, c_after, identities)
    record["problems"] = problems
    record["phase"] = "done" if not problems else "verify failed"
    print(json.dumps({"ids": ids, "problems": problems}, sort_keys=True))
    return 0 if not problems else 2


def verify(record, ids, rendered, t_before, t_after, c_before, c_after, identities):
    problems = []
    for bead in MEMBERS:
        if t_after[bead].get("status") != "closed":
            problems.append(f"{bead} not closed")
    created = set(ids.values())
    expected_changed = (MEMBERS - set(ALREADY_CLOSED)) | created | {ROOT}
    changed = {k for k in set(t_before) | set(t_after) if t_before.get(k) != t_after.get(k)}
    record["template_changed"] = sorted(changed)
    unexplained = sorted(changed - expected_changed)
    root_fields = sorted(f for f in set(t_before[ROOT]) | set(t_after[ROOT])
                         if t_before[ROOT].get(f) != t_after[ROOT].get(f))
    record["root_changed_fields"] = root_fields
    if set(root_fields) - {"dependent_count", "updated_at"}:
        problems.append(f"gct-oak5 changed fields {root_fields}")
    if unexplained:
        problems.append(f"unexplained Template changes: {unexplained}")
    c_changed = sorted(k for k in set(c_before) | set(c_after) if c_before.get(k) != c_after.get(k))
    record["city_changed"] = c_changed
    if c_changed:
        problems.append(f"city store changed: {c_changed}")
    for key, text in rendered.items():
        row = t_after[ids[key]]
        if (row.get("description") or "") != text:
            problems.append(f"{key} description differs")
    for key in ("C1-spec", "X-spec", "C2-spec", "H1", "H2"):
        row = t_after[ids[key]]
        if row.get("status") != "closed":
            problems.append(f"{key} not closed")
        if key[0] == "H" and (row.get("description") or ""):
            problems.append(f"{key} not empty")
    for name, _, _ in STEPS:
        row = t_after[ids[name]]
        m = meta(row)
        if row.get("status") != "open" or row.get("assignee") or m.get("gc.routed_to") or m.get("gc.root_bead_id"):
            problems.append(f"step {name} not open, unassigned and unrouted")
        if row.get("labels") != ["handover"]:
            problems.append(f"step {name} labels {row.get('labels')}")
        deps = {(d.get("depends_on_id"), d.get("type")) for d in row.get("dependencies") or []}
        want = {(ROOT, "relates-to")}
        if name == "X":
            want.add((ids["C1"], "blocks"))
        if name == "C2":
            want.add((ids["X"], "blocks"))
        if deps != want:
            problems.append(f"step {name} edges {sorted(deps)} != {sorted(want)}")
    root = t_after[ROOT]
    if root.get("status") != "open" or meta(root) != meta(t_before[ROOT]) or root.get("assignee"):
        problems.append("gct-oak5 changed beyond edges")
    after_hits = lane_eligible(t_after, c_after, identities)
    record["lane_eligible_after"] = after_hits
    if after_hits:
        problems.append(f"lane-eligible rows after: {after_hits}")
    ready = {r.get("id") for r in json.loads(gc("bd", "ready", "--json", "--limit", "0").stdout or "[]")}
    record["ready_has"] = {name: ids[name] in ready for name, _, _ in STEPS}
    if record["ready_has"] != {"C1": True, "X": False, "C2": False}:
        problems.append(f"ready set {record['ready_has']} != C1 only")
    return problems


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
