"""Offline tests for the gct-oak5 split package (no gc, no store): a fake gc emulates bd 1.2.2."""
import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("apply_split", HERE / "apply_split.py")
split = importlib.util.module_from_spec(spec)
spec.loader.exec_module(split)

LANE = "gas-city-template/gc.implementation-worker"


def row(bead, status="open", kind=None, routed=None, assignee=None, root=None, deps=(), itype="task", labels=None):
    metadata = {}
    if kind:
        metadata["gc.kind"] = kind
    if routed:
        metadata["gc.routed_to"] = routed
    if root:
        metadata["gc.root_bead_id"] = root
    return {"id": bead, "status": status, "assignee": assignee, "issue_type": itype, "metadata": metadata,
            "labels": labels, "description": "", "dependent_count": 0,
            "dependencies": [{"issue_id": bead, "depends_on_id": d, "type": t} for d, t in deps]}


def pinned_template():
    """The live gct-wn1m shape (tx-now.jsonl, 2026-09-27), reduced to the fields the package reads."""
    w = "gct-wn1m"
    rows = [
        row(w, kind="workflow", routed="gas-city-template/gc.run-operator", deps=[("gct-dh6u", "blocks")]),
        row("gct-af6u", routed=LANE, root=w, deps=[("gct-zkfz", "blocks"), (w, "tracks")]),
        row("gct-20mc", kind="ralph", root=w, deps=[(w, "tracks"), ("gct-af6u", "blocks"), ("gct-zkfz", "blocks")]),
        row("gct-svpm", root=w, deps=[(w, "tracks"), ("gct-20mc", "blocks")]),
        row("gct-dh6u", kind="workflow-finalize", root=w, deps=[(w, "tracks"), ("gct-svpm", "blocks")]),
        row("gct-v7yb", kind="spec", root=w, deps=[(w, "tracks")]),
        row("gct-zkfz", status="closed", root=w, deps=[(w, "tracks")]),
        row("gct-oak5"),
        row("gct-other", status="closed"),
    ]
    return {r["id"]: r for r in rows}


class FakeGC:
    """Emulates the gc/bd subset apply_split uses, with bd 1.2.2 close and ready semantics."""

    def __init__(self, template, city=None, core_closes=None, suspended=True):
        self.t = template
        self.c = city or {"ci-1": row("ci-1", status="closed", itype="session")}
        self.core_closes = core_closes or {}
        self.suspended = suspended
        self.calls = []
        self.n = 0

    def blocked(self, bead):
        return [d["depends_on_id"] for d in self.t[bead].get("dependencies") or []
                if d["type"] in split.BLOCKING and self.t.get(d["depends_on_id"], {}).get("status") != "closed"]

    def __call__(self, *args, rig=True, check=True):
        self.calls.append(args)
        out, code = "", 0
        if args[0] == "status":
            out = f"city  /x\n  Suspended:  {'yes' if self.suspended else 'no'}\n\nAgents:\n  a  stopped\n"
        elif args[0] == "rig":
            out = json.dumps({"rigs": [{"name": "city", "suspended": False},
                                       {"name": "gas-city-template", "suspended": self.suspended}]})
        elif args[:2] == ("bd", "export"):
            rows = self.t if rig else self.c
            out = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows.values())
        elif args[:2] == ("bd", "show"):
            out = json.dumps([self.t[args[2]]])
        elif args[:2] == ("bd", "update"):
            bead = self.t[args[2]]
            if args[3] == "--set-metadata":
                key, value = args[4].split("=", 1)
                bead["metadata"][key] = value
            elif args[3] == "--body-file":
                bead["description"] = Path(args[4]).read_text()
        elif args[:2] == ("bd", "close"):
            bead = args[2]
            if self.t[bead]["status"] == "closed" or self.blocked(bead):
                out, code = "", 1
            else:
                self.t[bead].update(status="closed", close_reason=args[4], closed_at="now")
                for later in self.core_closes.get(bead, ()):
                    self.t[later].update(status="closed", close_reason="core auto-close", closed_at="now")
        elif args[:2] == ("bd", "create"):
            self.n += 1
            new = f"gct-new{self.n}"
            labels = args[args.index("--labels") + 1].split(",")
            self.t[new] = row(new, labels=labels)
            out = new + "\n"
        elif args[:3] == ("bd", "dep", "add"):
            self.t[args[3]]["dependencies"].append({"issue_id": args[3], "depends_on_id": args[4], "type": args[6]})
            self.t[args[4]]["dependent_count"] += 1
        elif args[:2] == ("bd", "ready"):
            ready = [r for r in self.t.values() if r["status"] == "open"
                     and not any(d["type"] in ("blocks", "conditional-blocks", "waits-for", "parent-child")
                                 and self.t.get(d["depends_on_id"], {}).get("status") != "closed"
                                 for d in r.get("dependencies") or [])]
            out = json.dumps(ready)
        if check and code:
            raise split.Refused(f"{args[:3]} exit {code}")
        return SimpleNamespace(stdout=out, returncode=code, stderr="")


@pytest.fixture
def fake(monkeypatch):
    def make(**kw):
        g = FakeGC(pinned_template(), **kw)
        monkeypatch.setattr(split, "gc", g)
        return g
    return make


def run_job(tmp_path):
    stage = tmp_path / "stage"
    rc = split.main(str(stage))
    return rc, json.loads((stage / "record.json").read_text())


def test_success_path(fake, tmp_path):
    g = fake()
    rc, record = run_job(tmp_path)
    assert rc == 0, record
    assert record["problems"] == []
    assert record["closed_by"] == {b: "coordinator" for b in split.ORDER}
    closes = [a[2] for a in g.calls if a[:2] == ("bd", "close") and a[2] in split.ORDER]
    assert closes == list(split.ORDER)
    assert record["ready_has"] == {"C1": True, "X": False, "C2": False}
    assert all(w["state"] == "done" for w in record["writes"])
    ids = record["ids"]
    assert g.t[ids["X"]]["description"].count(ids["X-spec"]) >= 1
    assert "drain-ack" in g.t[ids["C1"]]["description"]


def test_old_controls_first_order_would_fail(fake, tmp_path, monkeypatch):
    fake()
    monkeypatch.setattr(split, "ORDER", ("gct-20mc", "gct-dh6u", "gct-af6u", "gct-svpm", "gct-v7yb", "gct-wn1m"))
    rc, record = run_job(tmp_path)
    assert rc == 1 and "would still be blocked" in record["error"]
    assert record["writes"] == []


def test_refuses_before_any_write(fake, tmp_path):
    g = fake(suspended=False)
    rc, record = run_job(tmp_path)
    assert rc == 1 and record["writes"] == []
    assert not [a for a in g.calls if a[:2] in (("bd", "update"), ("bd", "close"), ("bd", "create"))]


def test_member_drift_refuses(fake, tmp_path):
    g = fake()
    g.t["gct-new"] = row("gct-new", root="gct-wn1m")
    rc, record = run_job(tmp_path)
    assert rc == 1 and "members" in record["error"]


def test_core_auto_close_is_attributed(fake, tmp_path):
    fake(core_closes={"gct-v7yb": ("gct-wn1m",)})
    rc, record = run_job(tmp_path)
    assert rc == 0, record
    assert record["closed_by"]["gct-wn1m"] == "core"
    assert record["member_close"]["gct-wn1m"]["metadata_delta"] == {}


def test_failure_after_writes_is_exit_3_with_intent(fake, tmp_path):
    g = fake()
    g.t["gct-svpm"]["dependencies"].append({"issue_id": "gct-svpm", "depends_on_id": "gct-other2", "type": "tracks"})
    original = g.__call__

    def failing(*args, **kw):
        if args[:3] == ("bd", "close", "gct-svpm"):
            raise split.Refused("close exit 1")
        return original(*args, **kw)
    split.gc = failing
    rc, record = run_job(tmp_path)
    assert rc == 3
    assert record["writes"][-1] == {"bead": "gct-svpm", "op": "close", "state": "intent"}


def test_verify_catches_unexpected_field_change(fake, tmp_path):
    g = fake()
    original = g.__call__

    def tamper(*args, **kw):
        result = original(*args, **kw)
        if args[:3] == ("bd", "close", "gct-v7yb"):
            g.t["gct-v7yb"]["metadata"]["gc.routed_to"] = LANE
        return result
    split.gc = tamper
    rc, record = run_job(tmp_path)
    assert rc == 2
    assert any("gct-v7yb" in p for p in record["problems"])


def test_text_digests_are_pinned():
    shas = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "texts").iterdir()}
    assert split.TEXT_SHA == shas
    split.load_texts()


def test_wrapper_pins_apply_script():
    wrapper = (HERE.parent / "operator" / "SPLIT.sh").read_text()
    digest = hashlib.sha256((HERE / "apply_split.py").read_bytes()).hexdigest()
    assert f"APPLY_SHA={digest}\n" in wrapper
    assert "STAGE=$S/split-r2\n" in wrapper


IDS = {"C1": "gct-aaa1", "X": "gct-aaa2", "C2": "gct-aaa3", "H1": "gct-aaa4", "H2": "gct-aaa5",
       "C1-spec": "gct-aaa6", "X-spec": "gct-aaa7", "C2-spec": "gct-aaa8"}


def test_render_all():
    rendered = split.render(split.load_texts(), IDS)
    assert set(rendered) == {"C1", "X", "C2", "C1-spec", "X-spec", "C2-spec"}
    for key, text in rendered.items():
        assert not re.search(r"\{[A-Z0-9]+\}", text)
        assert len(text.encode()) <= split.MAX_VIEW
        assert not text.endswith("\n")
    for name in ("C1", "X", "C2"):
        assert IDS[name + "-spec"] in rendered[name] and IDS[name] in rendered[name]
        assert "drain-ack" in rendered[name] and "Never touch any other Bead" in rendered[name]
    c1, x, c2 = rendered["C1-spec"], rendered["X-spec"], rendered["C2-spec"]
    assert "lib/gct_handover_digest.py" in c1 and "docs/native-findings.md" in c1
    assert "tests/test_gct_handover_digest.py" in x and "docs/bead-conventions.md" in x
    assert "/usr/bin/python3.12 -B -m pytest -q -p no:cacheprovider --basetemp=/home/loucmane/gas-city-template-candidate-worktrees/gct-oak5/.oak5-c2-tmp/basetemp tests/test_gct_handover_digest.py" in c2
    assert "PROBE DONE gct-oak5 C1" in c1 and "PROBE SKIPPED gct-oak5 C1" in c1
    assert "commit --allow-empty -m probe" in x and "run no tests" in x
    assert IDS["H1"] in x and IDS["H2"] in c2


def test_city_suspended_reads_the_city_line_only():
    assert split.city_suspended("city  /x\n  Suspended:  yes\n\nAgents:\n")
    assert not split.city_suspended("city  /x\n  Suspended:  no\n\nAgents:\n  r  Suspended:  yes\n")


def test_lane_eligible_rules():
    rows = {r["id"]: r for r in (
        row("a", routed="gas-city-template/codex"),
        row("b", status="closed", routed="gas-city-template/codex"),
        row("c", kind="workflow"),
        row("d", assignee="codex-ci-xyz"),
        row("e", assignee="codex-ci-xyz", itype="message"),
    )}
    rows["c"]["metadata"]["gc.run_target"] = "gc.implementation-worker"
    assert sorted(h[1] for h in split.lane_eligible(rows, {}, {"codex-ci-xyz"})) == ["a", "c", "d"]
