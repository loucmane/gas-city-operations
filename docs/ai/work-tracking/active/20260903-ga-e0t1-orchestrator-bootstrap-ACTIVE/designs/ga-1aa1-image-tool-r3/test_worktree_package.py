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
    old = (OLD / "worktree-noatime.py").read_bytes()
    assert sha(old) == OLD_SHA
    expected = old.decode().replace(
        "/var/tmp/ga-e0t1.20-worktree-20260927-r1",
        "/var/tmp/ga-1aa1-worktree-20260929-r1",
    ).replace("ga-e0t1.20", "ga-1aa1").replace(
        "c6b789bbe6ff677dd04336803dbf2c2e017812ba",
        "5b981444bf7d687c0367da4ee3d111ff4b443ead",
    ).replace("codex/ga-1aa1-c1-close-admission", "codex/ga-1aa1-handover-image-r3")
    assert (HERE / "worktree.py").read_text() == expected


def test_wrapper_exact_rebinding_and_script_digest():
    old = (ENTRY / "operator/WORKTREE-R3.sh").read_bytes()
    assert sha(old) == OLD_WRAPPER_SHA
    expected = old.decode().replace(
        "ga-e0t1.20-astra-bootstrap", "ga-1aa1-image-tool-r3",
    ).replace(
        "/var/tmp/ga-e0t1.20-worktree-20260927-r1",
        "/var/tmp/ga-1aa1-worktree-20260929-r1",
    ).replace("worktree-noatime.py", "worktree.py").replace(
        OLD_SHA, sha((HERE / "worktree.py").read_bytes()),
    )
    assert (HERE / "operator/WORKTREE.sh").read_text() == expected
    assert subprocess.run(
        ["/bin/sh", "-n", str(HERE / "operator/WORKTREE.sh")],
        capture_output=True, check=False,
    ).returncode == 0


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
    relative = "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-1aa1-image-tool-r3/operator/WORKTREE.sh"
    assert bindings["WRAPPER"].fullmatch(relative)
    assert not bindings["WRAPPER"].fullmatch(relative.replace("ga-1aa1-image-tool-r3", "ga.evil"))


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
    assert m.BASE == "5b981444bf7d687c0367da4ee3d111ff4b443ead"
    assert m.WORK.name == "ga-1aa1"
    assert m.ADMIN.name == "ga-1aa1"
    assert m.BRANCH == "codex/ga-1aa1-handover-image-r3"
    assert str(m.ROOT) == "/var/tmp/ga-1aa1-worktree-20260929-r1"
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
