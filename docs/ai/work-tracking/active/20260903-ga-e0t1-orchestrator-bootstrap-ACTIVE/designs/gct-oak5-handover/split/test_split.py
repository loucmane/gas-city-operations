"""Offline tests for the gct-oak5 split package (no gc, no store)."""
import hashlib
import importlib.util
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("apply_split", HERE / "apply_split.py")
split = importlib.util.module_from_spec(spec)
spec.loader.exec_module(split)

IDS = {"C1": "gct-aaa1", "X": "gct-aaa2", "C2": "gct-aaa3", "H1": "gct-aaa4", "H2": "gct-aaa5",
       "C1-spec": "gct-aaa6", "X-spec": "gct-aaa7", "C2-spec": "gct-aaa8"}


def render(name):
    text = (HERE / "texts" / f"{name}-spec.md").read_text()
    for key in ("C1", "X", "C2", "H1", "H2"):
        text = text.replace("{" + key + "}", IDS[key])
    return text


def test_text_digests_are_pinned():
    shas = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "texts").iterdir()}
    assert split.TEXT_SHA == shas
    split.verify_texts()


def test_wrapper_pins_apply_script():
    wrapper = (HERE.parent / "operator" / "SPLIT.sh").read_text()
    digest = hashlib.sha256((HERE / "apply_split.py").read_bytes()).hexdigest()
    assert f"APPLY_SHA={digest}\n" in wrapper
    assert "STAGE=$S/split-r1\n" in wrapper


@pytest.mark.parametrize("name", ["C1", "X", "C2"])
def test_specs_render_fully_and_fit(name):
    text = render(name)
    assert not re.search(r"\{[A-Z0-9]+\}", text)
    assert len(text.encode()) <= split.MAX_VIEW
    assert IDS[name] in text
    assert "gc runtime drain-ack" in text
    assert "gct-oak5-handover-proof" in text


def test_step_template_points_to_spec():
    step = (HERE / "texts" / "step.md").read_text()
    assert set(re.findall(r"\{([A-Z]+)\}", step)) == {"NAME", "LANE", "SPEC", "SHOW"}


def test_contract_paths():
    c1, x, c2 = render("C1"), render("X"), render("C2")
    assert "lib/gct_handover_digest.py" in c1 and "docs/native-findings.md" in c1
    assert "tests/test_gct_handover_digest.py" in x and "docs/bead-conventions.md" in x
    assert "/usr/bin/python3.12 -B -m pytest -q -p no:cacheprovider --basetemp=/home/loucmane/gas-city-template-candidate-worktrees/gct-oak5/.oak5-c2-tmp/basetemp tests/test_gct_handover_digest.py" in c2
    assert "/usr/bin/chmod -R u+w -- .oak5-c2-tmp" in c2 and "/usr/bin/rm -r -- .oak5-c2-tmp" in c2
    assert "PROBE DONE gct-oak5 C1" in c1 and "PROBE SKIPPED gct-oak5 C1" in c1
    assert "git -C /home/loucmane/gas-city-template-candidate-worktrees/gct-oak5 commit --allow-empty -m probe" in x
    assert "probe-target/X" in x and "probe-target/C2" in c2
    assert IDS["H1"] in x and IDS["H2"] in c2


def row(bead, status="open", kind=None, routed=None, assignee=None, root=None, deps=(), itype="task"):
    metadata = {}
    if kind:
        metadata["gc.kind"] = kind
    if routed:
        metadata["gc.routed_to"] = routed
    if root:
        metadata["gc.root_bead_id"] = root
    return {"id": bead, "status": status, "assignee": assignee, "issue_type": itype, "metadata": metadata,
            "dependencies": [{"issue_id": bead, "depends_on_id": d, "type": t} for d, t in deps]}


def test_members_follow_root_and_edges():
    rows = {r["id"]: r for r in (
        row("gct-wn1m", deps=[("gct-dh6u", "blocks")]),
        row("gct-af6u", deps=[("gct-wn1m", "tracks")]),
        row("gct-new", root="gct-wn1m"),
        row("gct-other"),
    )}
    assert split.wn1m_members(rows) == {"gct-wn1m", "gct-dh6u", "gct-af6u", "gct-new"}


def test_lane_eligible_rules():
    rows = {r["id"]: r for r in (
        row("a", routed="gas-city-template/codex"),
        row("b", status="closed", routed="gas-city-template/codex"),
        row("c", kind="workflow"),
        row("d", assignee="codex-ci-xyz"),
        row("e", assignee="codex-ci-xyz", itype="message"),
    )}
    rows["c"]["metadata"]["gc.run_target"] = "gc.implementation-worker"
    hits = split.lane_eligible(rows, {}, {"codex-ci-xyz"})
    assert sorted(h[1] for h in hits) == ["a", "c", "d"]
