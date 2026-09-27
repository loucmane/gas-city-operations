"""gct-oak5 split package r2: close the stale workflow gct-wn1m and create the handover step Beads.

One quiet step (plan r16, sections "Decisions" and "Beads"):
1. preconditions: the city line and the gas-city-template rig suspended (and every other rig), no
   open session Bead, the gct-wn1m member set, kinds, states and blocking edges exactly as pinned,
   and no handover Bead yet;
2. before-exports of the Template and city stores (`bd export --all`);
3. close gct-wn1m in dependency order (bd 1.2.2 refuses to close a Bead with an open `blocks`,
   `conditional-blocks` or `waits-for` blocker): gct-af6u, gct-20mc, gct-svpm, gct-dh6u, gct-v7yb,
   then the root. Each open member gets gc.work_outcome=abandoned and CLOSE_REASON; a member Core
   closed first is attributed to Core. Every write is recorded as an intent before it is made;
4. create the closed spec holders, the closed empty image holders H1 and H2, and the open, unrouted
   steps C1, X and C2 (label handover), with step -> gct-oak5 relates-to edges and the C1 blocks X
   blocks C2 chain;
5. after-exports and exact checks: field deltas on every member and on gct-oak5, exact rows for
   every created Bead, no other change in either store, an empty lane-eligible audit, and a ready
   set holding C1 and neither X nor C2.

Exit 0: done and verified. 1: refused before any write. 2: every write made, verification found
problems. 3: an error after the first write (the record names the last intent).
Output: <stage>/record.json (always written once the stage exists) and the snapshots.
Entry: source-launch.py <this file> <sha256> <stage directory that must not exist>.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTS = HERE / "texts"
TEXT_SHA = {"C1-spec.md": "81d4cd9902ca482bf21f37c46ad58f5814236daa8ef2aafcb4b67558bfdc4f49", "C2-spec.md": "444c6db2c763b652031a56ff35e79c289c9e54bb7f9114ebb6e1b58134de6d91", "X-spec.md": "0940ec187f2b61ef69ea1366acd4bbd88723f7f19704bb93f65a9054260896cc", "step.md": "20889fa155558f35b60facfc10e7ac4ac16b444ee3fe88a315824fb92b928df8"}
GC = "/home/loucmane/gascity/bin/gc"
CITY = "/home/loucmane/gascity/city"
RIG = "gas-city-template"
ENV = {  # the reviewed ga-6utp gc environment
    "HOME": "/home/loucmane",
    "PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin",
    "GC_HOME": "/home/loucmane/gascity/home",
    "GIT_OPTIONAL_LOCKS": "0",
    "BD_DISABLE_METRICS": "1",
    "LANG": "C",
}
ROOT = "gct-oak5"
WN1M = "gct-wn1m"
ORDER = ("gct-af6u", "gct-20mc", "gct-svpm", "gct-dh6u", "gct-v7yb", WN1M)
ALREADY_CLOSED = ("gct-zkfz",)
MEMBERS = frozenset(ORDER + ALREADY_CLOSED)
KINDS = {"gct-af6u": None, "gct-20mc": "ralph", "gct-svpm": None, "gct-dh6u": "workflow-finalize",
         "gct-v7yb": "spec", WN1M: "workflow"}
BLOCKING = frozenset({"blocks", "conditional-blocks", "waits-for"})
CLOSE_REASON = ("Obsolete: stale 2026-08 do-work workflow gct-wn1m, closed before the gct-oak5 handover "
                "on the operator decision of 2026-09-27 (Close as obsolete; ga-e0t1).")
HOLDER_REASON = "gct-oak5 handover holder (closed by design)"
CLOSE_FIELDS = frozenset({"status", "closed_at", "updated_at", "close_reason", "metadata"})
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
HOLDERS = ("C1-spec", "X-spec", "C2-spec", "H1", "H2")
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


def show(bead):
    data = json.loads(gc("bd", "show", bead, "--json").stdout)
    return data[0] if isinstance(data, list) else data


def meta(row):
    return row.get("metadata") or {}


def load_texts():
    """Hash and return the pinned texts from one read of each file."""
    names = {p.name for p in TEXTS.iterdir()}
    if names != set(TEXT_SHA):
        raise Refused("text set differs from the pinned set")
    texts = {}
    for name in sorted(names):
        raw = (TEXTS / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != TEXT_SHA[name]:
            raise Refused(f"text {name} digest mismatch")
        texts[name] = raw.decode("utf-8")
    return texts


def render(texts, ids):
    subst = {"{C1}": ids["C1"], "{X}": ids["X"], "{C2}": ids["C2"], "{H1}": ids["H1"], "{H2}": ids["H2"]}
    rendered = {}
    for name, lane, show_cmd in STEPS:
        spec = texts[f"{name}-spec.md"]
        for key, value in subst.items():
            spec = spec.replace(key, value)
        step = texts["step.md"]
        for key, value in (("{NAME}", name), ("{LANE}", lane), ("{SPEC}", ids[name + "-spec"]),
                           ("{SHOW}", show_cmd), ("{STEP}", ids[name])):
            step = step.replace(key, value)
        for text in (spec, step):
            if re.search(r"\{[A-Z0-9]+\}", text):
                raise Refused(f"unrendered placeholder in {name}")
            if len(text.encode()) > MAX_VIEW:
                raise Refused(f"{name} text over {MAX_VIEW} bytes")
        rendered[name + "-spec"] = spec.rstrip("\n")
        rendered[name] = step.rstrip("\n")
    return rendered


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


def blockers(row):
    return {d.get("depends_on_id") for d in row.get("dependencies") or [] if d.get("type") in BLOCKING}


def check_order(rows):
    """Every blocker of each member is closed before the run or closed earlier in ORDER."""
    done = {k for k, r in rows.items() if r.get("status") == "closed"}
    for bead in ORDER:
        missing = blockers(rows[bead]) - done
        if missing:
            raise Refused(f"{bead} would still be blocked by {sorted(missing)}")
        done.add(bead)


def lane_eligible(template_rows, city_rows, identities):
    hits = []
    for store, rows in (("template", template_rows), ("city", city_rows)):
        for row in rows.values():
            if row.get("status") not in ("open", "in_progress"):
                continue
            m = meta(row)
            routed = m.get("gc.routed_to") or ""
            if routed in LANE_TARGETS:
                hits.append([store, row["id"], "routed", routed])
            if m.get("gc.kind") == "workflow" and not routed and (m.get("gc.run_target") or "") in LANE_TARGETS:
                hits.append([store, row["id"], "run_target", m.get("gc.run_target")])
            if row.get("issue_type") != "message" and (row.get("assignee") or "") in identities:
                hits.append([store, row["id"], "assigned", row.get("assignee")])
    return hits


def city_suspended(status):
    head = status.split("\nAgents:", 1)[0]
    lines = head.splitlines()
    return bool(lines) and lines[0].startswith("city ") and any(
        re.fullmatch(r"\s+Suspended:\s+yes\s*", line) for line in lines[1:])


def preconditions(record):
    if not city_suspended(gc("status", rig=False, check=False).stdout):
        raise Refused("the city line does not show Suspended: yes")
    rigs = json.loads(gc("rig", "list", "--json", rig=False).stdout)["rigs"]
    record["rigs"] = {r["name"]: r.get("suspended") for r in rigs}
    if record["rigs"].get(RIG) is not True:
        raise Refused(f"{RIG} is not listed as suspended")
    awake = [r["name"] for r in rigs if r.get("name") != "city" and not r.get("suspended")]
    if awake:
        raise Refused(f"rigs not suspended: {awake}")


def main(stage_arg):
    stage = Path(stage_arg)
    if stage.exists() or stage.is_symlink():
        raise SystemExit(f"stage already exists: {stage}")
    stage.mkdir(mode=0o700)
    record = {"schema": "gct-oak5.split.v2", "phase": "preconditions", "writes": []}
    try:
        return run(stage, record)
    except Exception as exc:  # every failure is recorded; after a write it is never a plain refusal
        record["error"] = f"{type(exc).__name__}: {exc}"
        wrote = bool(record["writes"])
        print(f"{'FAILED AFTER WRITES' if wrote else 'REFUSED'} in {record['phase']}: {record['error']}")
        return 3 if wrote else 1
    finally:
        (stage / "record.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")


def write(record, intent, *args):
    record["writes"].append(dict(intent, state="intent"))
    gc(*args)
    record["writes"][-1]["state"] = "done"


def run(stage, record):
    texts = load_texts()
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
    for bead, kind in KINDS.items():
        row = t_before[bead]
        if meta(row).get("gc.kind") != kind or row.get("status") != "open" or row.get("assignee"):
            raise Refused(f"{bead} is not an open, unassigned {kind or 'work'} Bead")
    for bead in ALREADY_CLOSED:
        if t_before[bead].get("status") != "closed":
            raise Refused(f"{bead} is not closed")
    check_order(t_before)
    if t_before.get(ROOT, {}).get("status") != "open":
        raise Refused("gct-oak5 is not open")
    if any(set(r.get("labels") or []) & {"handover", "handover-holder"} for r in t_before.values()):
        raise Refused("a handover Bead already exists")
    identities = set(LANE_TARGETS) | {
        meta(r).get("session_name") for r in c_before.values()
        if r.get("issue_type") == "session" and meta(r).get("template") in LANE_TEMPLATES} - {None}
    before_hits = lane_eligible(t_before, c_before, identities)
    if before_hits != [["template", "gct-af6u", "routed", "gas-city-template/gc.implementation-worker"]]:
        raise Refused(f"unexpected lane-eligible rows before: {before_hits}")
    record["lane_eligible_before"] = before_hits

    record["phase"] = "close gct-wn1m"
    closed_by = {}
    for bead in ORDER:
        if show(bead).get("status") == "closed":
            closed_by[bead] = "core"
            continue
        write(record, {"bead": bead, "op": "set gc.work_outcome=abandoned"},
              "bd", "update", bead, "--set-metadata", "gc.work_outcome=abandoned")
        try:
            write(record, {"bead": bead, "op": "close"}, "bd", "close", bead, "--reason", CLOSE_REASON)
            closed_by[bead] = "coordinator"
        except Refused:
            if show(bead).get("status") == "closed":
                closed_by[bead] = "core-race"
                record["writes"][-1]["state"] = "closed by core first"
            else:
                raise
    record["closed_by"] = closed_by

    record["phase"] = "create"
    ids = {}
    for key in HOLDERS:
        title = f"gct-oak5 handover {key} brief" if key[0] != "H" else f"gct-oak5 handover image {key}"
        record["writes"].append({"create": key, "state": "intent"})
        new = gc("bd", "create", title, "--type", "task", "--priority", "P2",
                 "--labels", "handover-holder", "--silent").stdout.strip()
        if not ID.fullmatch(new):
            raise Refused(f"create {key} returned {new!r}")
        ids[key] = new
        record["writes"][-1].update(state="done", bead=new)
    for name, _, _ in STEPS:
        record["writes"].append({"create": name, "state": "intent"})
        new = gc("bd", "create", f"gct-oak5 handover step {name}", "--type", "task", "--priority", "P2",
                 "--labels", "handover", "--silent").stdout.strip()
        if not ID.fullmatch(new):
            raise Refused(f"create step {name} returned {new!r}")
        ids[name] = new
        record["writes"][-1].update(state="done", bead=new)
    record["ids"] = ids

    record["phase"] = "descriptions"
    rendered = render(texts, ids)
    for key, text in rendered.items():
        path = stage / f"{key}.md"
        path.write_text(text)
        write(record, {"bead": ids[key], "op": "description", "sha256": hashlib.sha256(text.encode()).hexdigest()},
              "bd", "update", ids[key], "--body-file", str(path))

    record["phase"] = "close holders"
    for key in HOLDERS:
        write(record, {"bead": ids[key], "op": "close holder"}, "bd", "close", ids[key], "--reason", HOLDER_REASON)

    record["phase"] = "edges"
    for name, _, _ in STEPS:
        write(record, {"edge": [ids[name], ROOT, "relates-to"]},
              "bd", "dep", "add", ids[name], ROOT, "--type", "relates-to")
    write(record, {"edge": [ids["X"], ids["C1"], "blocks"]}, "bd", "dep", "add", ids["X"], ids["C1"], "--type", "blocks")
    write(record, {"edge": [ids["C2"], ids["X"], "blocks"]}, "bd", "dep", "add", ids["C2"], ids["X"], "--type", "blocks")

    record["phase"] = "verify"
    t_raw2, t_after = export(True)
    c_raw2, c_after = export(False)
    (stage / "template-after.jsonl").write_text(t_raw2)
    (stage / "city-after.jsonl").write_text(c_raw2)
    record["after_sha256"] = {"template": hashlib.sha256(t_raw2.encode()).hexdigest(),
                              "city": hashlib.sha256(c_raw2.encode()).hexdigest()}
    ready = {r.get("id") for r in json.loads(gc("bd", "ready", "--json", "--limit", "0").stdout or "[]")}
    problems = verify(record, ids, rendered, closed_by, t_before, t_after, c_before, c_after, identities, ready)
    record["problems"] = problems
    record["phase"] = "done" if not problems else "verify failed"
    print(json.dumps({"ids": ids, "closed_by": closed_by, "problems": problems}, sort_keys=True))
    return 0 if not problems else 2


def changed_fields(before, after):
    return {f for f in set(before) | set(after) if before.get(f) != after.get(f)}


def verify(record, ids, rendered, closed_by, t_before, t_after, c_before, c_after, identities, ready):
    problems = []
    created = set(ids.values())
    changed = {k for k in set(t_before) | set(t_after) if t_before.get(k) != t_after.get(k)}
    record["template_changed"] = sorted(changed)
    extra = sorted(changed - set(ORDER) - created - {ROOT})
    if extra:
        problems.append(f"unexplained Template changes: {extra}")
    c_changed = sorted(k for k in set(c_before) | set(c_after) if c_before.get(k) != c_after.get(k))
    record["city_changed"] = c_changed
    if c_changed:
        problems.append(f"city store changed: {c_changed}")

    for bead in ORDER:
        before, after = t_before[bead], t_after[bead]
        fields = changed_fields(before, after)
        delta = {k: meta(after).get(k) for k in set(meta(before)) | set(meta(after)) if meta(before).get(k) != meta(after).get(k)}
        who = closed_by.get(bead)
        if after.get("status") != "closed" or fields - CLOSE_FIELDS:
            problems.append(f"{bead}: status {after.get('status')}, fields {sorted(fields)}")
        if who == "coordinator" and (delta != {"gc.work_outcome": "abandoned"} or after.get("close_reason") != CLOSE_REASON):
            problems.append(f"{bead}: coordinator close fields {delta} {after.get('close_reason')!r}")
        if who in ("core", "core-race") and delta not in ({}, {"gc.work_outcome": "abandoned"}):
            problems.append(f"{bead}: core close changed metadata {delta}")
        record.setdefault("member_close", {})[bead] = {"by": who, "close_reason": after.get("close_reason"), "metadata_delta": delta}
    root_fields = changed_fields(t_before[ROOT], t_after[ROOT])
    record["root_changed_fields"] = sorted(root_fields)
    if root_fields - {"dependent_count", "updated_at"}:
        problems.append(f"gct-oak5 changed fields {sorted(root_fields)}")

    for key in HOLDERS:
        row = t_after[ids[key]]
        want_desc = rendered.get(key, "")
        if (row.get("status") != "closed" or row.get("close_reason") != HOLDER_REASON or meta(row)
                or (row.get("labels") or []) != ["handover-holder"] or row.get("dependencies")
                or row.get("assignee") or (row.get("description") or "") != want_desc):
            problems.append(f"holder {key} not exactly as created")
    for name, _, _ in STEPS:
        row = t_after[ids[name]]
        deps = sorted((d.get("depends_on_id"), d.get("type")) for d in row.get("dependencies") or [])
        want = [(ROOT, "relates-to")]
        if name == "X":
            want.append((ids["C1"], "blocks"))
        if name == "C2":
            want.append((ids["X"], "blocks"))
        if (row.get("status") != "open" or meta(row) or row.get("assignee")
                or (row.get("labels") or []) != ["handover"] or deps != sorted(want)
                or (row.get("description") or "") != rendered[name]):
            problems.append(f"step {name} not exactly as created")

    after_hits = lane_eligible(t_after, c_after, identities)
    record["lane_eligible_after"] = after_hits
    if after_hits:
        problems.append(f"lane-eligible rows after: {after_hits}")
    record["ready_has"] = {name: ids[name] in ready for name, _, _ in STEPS}
    if record["ready_has"] != {"C1": True, "X": False, "C2": False}:
        problems.append(f"ready set {record['ready_has']} != C1 only")
    return problems


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
