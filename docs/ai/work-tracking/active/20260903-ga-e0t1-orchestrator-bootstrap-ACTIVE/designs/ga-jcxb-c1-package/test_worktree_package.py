"""Offline proofs for the mechanically rebound preparation-only WORKTREE job."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import types

import pytest

HERE = Path(__file__).resolve().parent
DESIGNS = HERE.parent
OLD = DESIGNS / "ga-e0t1.20-astra-bootstrap"
ENTRY = DESIGNS / "ga-e0t1-20-astra-entry"
OLD_SHA = "21a3e4270ab05c68cf1ae9795f42e2302ed3c9fa5bd839c6467de879d941ec6f"
OLD_WRAPPER_SHA = "da48f232fe1a9cdcfd37ad08ece818fdc963547eb0512babe34bb73b7d8fefae"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module():
    m = types.ModuleType("worktree_candidate")
    m.__file__ = str(HERE / "worktree.py")
    exec(compile((HERE / "worktree.py").read_bytes(), m.__file__, "exec"), m.__dict__)
    return m


def test_exact_predecessor_and_only_identity_rebinding():
    previous = DESIGNS / "ga-goo5-c1-package"
    raw = (previous / "worktree.py").read_bytes()
    assert sha(raw) == "08e6d140c6a0fb20ea59ba455377b2e45a50863d9a26acc08505a4f843e24784"
    assert (HERE / "worktree.py").read_bytes() == raw.replace(b"ga-goo5", b"ga-jcxb")


def test_wrapper_exact_rebinding_and_script_digest():
    previous = DESIGNS / "ga-goo5-c1-package"
    raw = (previous / "operator/WORKTREE.sh").read_bytes()
    assert sha(raw) == "7913ce00ea9dec0dec2d252d5dc72a850dbaba933b327eaec9b20d5bbc1387e6"
    expected = raw.decode().replace("ga-goo5", "ga-jcxb").replace(
        "08e6d140c6a0fb20ea59ba455377b2e45a50863d9a26acc08505a4f843e24784", sha((HERE / "worktree.py").read_bytes()))
    assert (HERE / "operator/WORKTREE.sh").read_text() == expected
    assert subprocess.run(["/bin/sh", "-n", str(HERE / "operator/WORKTREE.sh")], capture_output=True).returncode == 0


def test_minimal_input_preserves_exact_deny_only_rules():
    current = json.loads((HERE / "inputs.json").read_bytes())
    old = json.loads((OLD / "inputs.json").read_bytes())
    assert set(current) == {"window-restrictions.rules"}
    assert current["window-restrictions.rules"] == old["window-restrictions.rules"]
    raw = base64.b64decode(current["window-restrictions.rules"], validate=True)
    assert sha(raw) == module().RESTRICTION_SHA
    rules = ast.parse(raw.decode())
    calls = [n for n in rules.body if isinstance(n, ast.Expr)]
    assert len(calls) == 7
    for node in calls:
        assert isinstance(node.value, ast.Call)
        assert node.value.func.id == "prefix_rule"
        assert next(k.value.value for k in node.value.keywords if k.arg == "decision") == "forbidden"


def test_runner_accepts_exact_wrapper_shape():
    text = (DESIGNS / "gct-jobrunner/jobrunner.py").read_text()
    tree = ast.parse(text)
    bindings = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = getattr(node.targets[0], "id", "")
            if name == "PREFIX":
                bindings[name] = ast.literal_eval(node.value)
            elif name == "WRAPPER":
                bindings[name] = eval(compile(ast.Expression(node.value), "<regex>", "eval"),
                                      {"re": re, **bindings})
    relative = "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-jcxb-c1-package/operator/WORKTREE.sh"
    assert bindings["WRAPPER"].fullmatch(relative)
    assert not bindings["WRAPPER"].fullmatch(relative.replace("ga-jcxb-c1-package", "ga.evil"))


@pytest.mark.parametrize("entry", [
    b"160000 commit abc\tmodule\0",
    b"100644 blob abc\t.gitattributes\0",
    b"100644 blob abc\tnested/.gitattributes\0",
    b"100644 blob abc\t.gitmodules\0",
    b"100644 blob abc\t.codex/rules/extra.rules\0",
])
def test_unsafe_source_tree_refuses(entry):
    with pytest.raises(AssertionError):
        module().source_tree(entry)


def test_ordinary_source_tree_admitted():
    module().source_tree(b"100644 blob abc\tfile.py\0")


def test_noatime_regular_file_and_digest(tmp_path):
    m = module()
    p = tmp_path / "input"
    p.write_bytes(b"immutable")
    before = p.stat().st_atime_ns
    assert m.read(p, sha(b"immutable")) == b"immutable"
    assert p.stat().st_atime_ns == before
    with pytest.raises(AssertionError):
        m.read(p, "0" * 64)


def test_symlink_input_refused(tmp_path):
    p = tmp_path / "input"
    p.write_bytes(b"x")
    link = tmp_path / "link"
    link.symlink_to(p)
    with pytest.raises(OSError):
        module().read(link, sha(b"x"))


def test_create_only_evidence_preserves_existing(tmp_path):
    m = module()
    p = tmp_path / "evidence.json"
    m.write(p, {"ok": True})
    before = p.read_bytes()
    with pytest.raises(FileExistsError):
        m.write(p, {"ok": False})
    assert p.read_bytes() == before


def test_base_and_new_owned_roots():
    m = module()
    assert m.BASE == "801a5a9d5b0d72f665c949a86573357f02c9f1ac"
    assert m.WORK.name == "ga-jcxb"
    assert m.ADMIN.name == "ga-jcxb"
    assert m.BRANCH == "codex/ga-jcxb-c1-package"
    assert str(m.ROOT) == "/var/tmp/ga-jcxb-worktree-20260930-r1"
    assert m.WORK.parent == m.CANDIDATE_ROOT
    assert not any(n in (HERE / "worktree.py").read_text()
                   for n in ["'sling'", "'resume'", "'rig'", "'agent'", "'claim'"])


def test_missing_launcher_marker_refuses_before_writes(monkeypatch):
    m = module()
    def no_reads(*args, **kwargs):
        pytest.fail("read reached before mandatory launcher marker")
    monkeypatch.setattr(m, "read", no_reads)
    with pytest.raises(AssertionError):
        m.main()


def test_predecessor_latch_is_one_exact_completed_job():
    tree = ast.parse((HERE / "preserve-predecessor-halt.py").read_bytes())
    bindings = [n for n in tree.body if isinstance(n, ast.Assign) and
                any(getattr(t, "id", "") == "JOB_COMMITS" for t in n.targets)]
    assert len(bindings) == 1
    assert ast.literal_eval(bindings[0].value) == {
        "ga-goo5-terminal-r2": "ace2461aa4ccd969c19da98fcb420ff6c6403333"}
    text = (HERE / "preserve-predecessor-halt.py").read_text()
    for guard in ("assert job in JOB_COMMITS", "done['exit']==EXPECTED_EXIT", "done['unit_state_after']=='inactive'",
                  "blob==Path(__file__).read_bytes()", "rename(directory,b'HALTED',directory,archive.encode(),1)"):
        assert guard in text
    assert "os.unlink" not in text and ".unlink(" not in text


def test_worktree_job_does_not_copy_or_execute_partial_product():
    text = (HERE / "worktree.py").read_text()
    assert "ga-xyqo" not in text
    assert "digest-history" not in text
    assert "gct-oak5-c1-window" not in text


def test_unassigned_standalone_informational_relation():
    bead = json.loads((HERE / "LEDGER-BINDING.json").read_bytes())
    assert bead["id"] == "ga-jcxb" and bead["status"] == "open"
    assert not bead.get("assignee") and not bead.get("metadata")
    assert bead["dependencies"] == [
        {"id": "ga-e0t1", "dependency_type": "relates-to"}]
    assert not bead.get("parent")


def test_preserve_all_five_true_initiative_blockers_policy():
    text = (HERE / "CONTINUATION.md").read_text()
    for bead in ("ga-e0t1.13", "ga-fjoi", "ga-fc6p", "ga-fsfg", "ga-e0t1.8"):
        assert bead in text
    assert "Native bd ready --limit 0 returned ga-jcxb" in text
