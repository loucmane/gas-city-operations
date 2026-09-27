"""Tests for the gct-oak5 image tool: a real repository, linked worktree and bare clone in tmp_path."""
import base64
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("image_tool", HERE / "image_tool.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
       "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@example.invalid"}
BRANCH = "codex/gct-oak5-handover-proof"


def git(*args, cwd):
    return subprocess.run(["/usr/bin/git", "-c", "commit.gpgsign=false", *args], cwd=cwd, env=ENV, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def world(tmp_path, monkeypatch):
    repo = tmp_path / "canonical"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    files = {".gitignore": ".gc/\n__pycache__/\n", "docs/native-findings.md": "# findings\n",
             "docs/bead-conventions.md": "# conventions\n", "lib/keep.py": "x = 1\n", "AGENTS.md": "agents\n",
             ".claude/skills/obsidian-cli/SKILL.md": "skill\n", ".codex/config.toml": "a = 1\n"}
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    git("add", ".", cwd=repo)
    git("commit", "-q", "-m", "base", cwd=repo)
    base = git("rev-parse", "HEAD", cwd=repo)
    root = tmp_path / "candidate"
    root.mkdir()
    wt = root / "gct-oak5"
    git("worktree", "add", "-q", "-b", BRANCH, str(wt), base, cwd=repo)
    (repo / ".git/worktrees/gct-oak5/config.worktree").write_text("")
    clone = tmp_path / "base.git"
    git("clone", "-q", "--bare", str(repo), str(clone), cwd=tmp_path)
    city = tmp_path / "city"
    (city / "scripts").mkdir(parents=True)
    (city / "settings.json").write_text('{"s": 1}')
    (city / "scripts/mol.sh").write_text("#!/bin/sh\n")
    monkeypatch.setattr(tool, "WORKTREE", str(wt))
    monkeypatch.setattr(tool, "CANONICAL_GIT", repo / ".git")
    monkeypatch.setattr(tool, "FORBIDDEN_ROOTS", (root,))
    monkeypatch.setattr(tool, "CITY_FILES", {".gc/settings.json": (str(city / "settings.json"), 0o644),
                                             ".gc/scripts/mol-dog-stale-db.sh": (str(city / "scripts/mol.sh"), 0o755)})
    return dict(repo=repo, wt=wt, clone=clone, base=base, city=city, out=tmp_path / "out")


def add_runtime(wt, city, lane):
    gc = wt / ".gc"
    for d, mode in ((gc, 0o700), (gc / "tmp", 0o700), (gc / "scripts", 0o755)):
        d.mkdir(exist_ok=True)
        os.chmod(d, mode)
    (gc / "settings.json").write_bytes((city / "settings.json").read_bytes())
    os.chmod(gc / "settings.json", 0o644)
    (gc / "scripts/mol-dog-stale-db.sh").write_bytes((city / "scripts/mol.sh").read_bytes())
    os.chmod(gc / "scripts/mol-dog-stale-db.sh", 0o755)
    sink = wt / tool.LANES[lane]["sink"]
    sink.mkdir(parents=True, exist_ok=True)
    if lane == "codex":
        os.chmod(wt / ".agents", 0o755)
        os.chmod(sink, 0o755)
    (sink / ".gc-skill-ownership.json").write_bytes(tool.OWNERSHIP_BYTES)
    os.chmod(sink / ".gc-skill-ownership.json", 0o644)
    for name, target in tool.SKILL_MAP.items():
        os.symlink(target, sink / name)
    catalog = {"Entries": [{"Name": n, "Source": t, "Origin": "core", "Description": "d"} for n, t in tool.SKILL_MAP.items()],
               "OwnedRoots": tool.OWNED_ROOTS, "Shadowed": None}
    path = wt / tool.LANES[lane]["catalog"]
    path.write_bytes(base64.b64encode(json.dumps(catalog, separators=(",", ":")).encode()))
    os.chmod(path, 0o600)
    if lane == "codex":
        hooks = wt / ".codex/hooks.json"
        hooks.write_text('{"hooks": {}}')
        os.chmod(hooks, 0o644)


def export(w, name, runtime="claude", hooks=None):
    argv = ["export", "--worktree", str(w["wt"]), "--clone", str(w["clone"]), "--base", w["base"],
            "--out", str(w["out"].parent / name), "--runtime", runtime]
    if hooks:
        argv += ["--codex-hooks-sha", hooks]
    rc = tool.main(argv)
    return rc, (w["out"].parent / name / "image.json")


def refusal(w, name, capsys, **kw):
    rc, _ = export(w, name, **kw)
    out = capsys.readouterr().out.strip().splitlines()[-1]
    return rc, json.loads(out)


def image1(w):
    (w["wt"] / "docs/native-findings.md").write_text("# findings\n\n## Handover digest helper\n")
    (w["wt"] / "lib/gct_handover_digest.py").write_text('"""digest"""\n')
    add_runtime(w["wt"], w["city"], "claude")


def compare(w, prev, nxt, contract, carry=None):
    argv = ["compare", "--prev", str(prev), "--next", str(nxt), "--contract", contract]
    if carry:
        argv += ["--carry", carry]
    return tool.main(argv)


def test_image0_then_image1_contract(world, capsys):
    rc0, i0 = export(world, "i0", runtime="none")
    assert rc0 == 0
    image1(world)
    rc1, i1 = export(world, "i1")
    assert rc1 == 0, capsys.readouterr().out
    img = json.loads(i1.read_text())
    assert {e["path"]: e["status"] for e in img["entries"]} == {"docs/native-findings.md": "M", "lib/gct_handover_digest.py": "A"}
    assert len(img["runtime"]) == 2 + 1 + len(tool.SKILL_MAP) + 1
    assert img["git"]["branch_ref"] == world["base"]
    assert compare(world, i0, i1, "docs/native-findings.md:M,lib/gct_handover_digest.py:A") == 0


def test_image2_with_codex_and_carry(world, capsys):
    image1(world)
    _, i1 = export(world, "i1")
    (world["wt"] / "docs/bead-conventions.md").write_text("# conventions\n\n## Handover image digests\n")
    (world["wt"] / "tests").mkdir()
    (world["wt"] / "tests/test_gct_handover_digest.py").write_text("def test_x():\n    pass\n")
    add_runtime(world["wt"], world["city"], "codex")
    hooks = tool.sha256((world["wt"] / ".codex/hooks.json").read_bytes())
    rc, i2 = export(world, "i2", runtime="claude,codex", hooks=hooks)
    assert rc == 0, capsys.readouterr().out
    assert compare(world, i1, i2, "docs/bead-conventions.md:M,tests/test_gct_handover_digest.py:A",
                   carry="docs/native-findings.md,lib/gct_handover_digest.py") == 0


def test_contract_violation_refused(world, capsys):
    _, i0 = export(world, "i0", runtime="none")
    image1(world)
    (world["wt"] / "lib/keep.py").write_text("x = 2\n")
    _, i1 = export(world, "i1")
    assert compare(world, i0, i1, "docs/native-findings.md:M,lib/gct_handover_digest.py:A") == 1


def test_control_path_refused_in_compare(world, capsys):
    _, i0 = export(world, "i0", runtime="none")
    image1(world)
    (world["wt"] / "AGENTS.md").write_text("changed\n")
    _, i1 = export(world, "i1")
    assert compare(world, i0, i1, "docs/native-findings.md:M,lib/gct_handover_digest.py:A,AGENTS.md:M") == 1


def test_planted_codex_hooks_refused_in_claude_image(world, capsys):
    image1(world)
    (world["wt"] / ".codex/hooks.json").write_text("{}")
    rc, out = refusal(world, "i1", capsys)
    assert rc == 2 and "control-namespace" in out["refused"]


def test_escaping_skill_link_refused(world, capsys):
    image1(world)
    link = world["wt"] / ".claude/skills/core.gc-city"
    link.unlink()
    os.symlink(tool.SKILL_MAP["core.gc-city"] + "/../../../../../../../tmp", link)
    rc, out = refusal(world, "i1", capsys)
    assert rc == 2 and "runtime link differs" in out["refused"]


def test_extra_skill_link_refused(world, capsys):
    image1(world)
    os.symlink("/tmp", world["wt"] / ".claude/skills/evil")
    rc, out = refusal(world, "i1", capsys)
    assert rc == 2


def test_frozen_catalog_dir_refused(world, capsys):
    image1(world)
    os.chmod(world["wt"] / ".gc/tmp", 0o500)
    try:
        rc, out = refusal(world, "i1", capsys)
    finally:
        os.chmod(world["wt"] / ".gc/tmp", 0o700)
    assert rc == 2 and "runtime dir mode" in out["refused"]


def test_forged_catalog_refused(world, capsys):
    image1(world)
    path = world["wt"] / tool.LANES["claude"]["catalog"]
    path.write_bytes(base64.b64encode(b'{"Entries":[],"OwnedRoots":[],"Shadowed":null}'))
    rc, out = refusal(world, "i1", capsys)
    assert rc == 2 and "catalog" in out["refused"]


def test_nested_git_refused(world, capsys):
    image1(world)
    (world["wt"] / "lib/.GIT").mkdir()
    rc, out = refusal(world, "i1", capsys)
    assert rc == 2 and "nested .git" in out["refused"]


def test_ignored_entry_recorded_and_refused_by_compare(world, capsys):
    _, i0 = export(world, "i0", runtime="none")
    image1(world)
    (world["wt"] / "lib/__pycache__").mkdir()
    (world["wt"] / "lib/__pycache__/x.pyc").write_bytes(b"pyc")
    rc, i1 = export(world, "i1")
    assert rc == 0
    img = json.loads(i1.read_text())
    assert [i["path"] for i in img["ignored"]] == ["lib/__pycache__/x.pyc"]
    assert compare(world, i0, i1, "docs/native-findings.md:M,lib/gct_handover_digest.py:A") == 1


def test_ignored_link_refused(world, capsys):
    image1(world)
    (world["wt"] / "lib/__pycache__").mkdir()
    os.symlink("/etc/passwd", world["wt"] / "lib/__pycache__/x.pyc")
    rc, out = refusal(world, "i1", capsys)
    assert rc == 2


def test_hard_link_refused(world, capsys):
    image1(world)
    os.link(world["wt"] / "lib/gct_handover_digest.py", world["wt"] / "lib/copy.py")
    rc, out = refusal(world, "i1", capsys)
    assert rc == 2 and "single-link" in out["refused"]


def test_tampered_byte_detected(world, capsys):
    image1(world)
    _, i1 = export(world, "i1")
    (world["wt"] / "lib/gct_handover_digest.py").write_text('"""digesT"""\n')
    _, again = export(world, "again")
    a, b = json.loads(i1.read_text()), json.loads(again.read_text())
    assert a["entries"] != b["entries"]
    a2 = dict(a, worktree="x")
    assert a2["runtime"] == b["runtime"] and a2["git"] == b["git"]


def test_holder_lines(world, capsys):
    image1(world)
    _, i1 = export(world, "i1")
    capsys.readouterr()
    assert tool.main(["holder", "--manifest", str(i1), "--paths", "docs/native-findings.md,lib/gct_handover_digest.py"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[2].startswith("DIGEST docs/native-findings.md ") and lines[3].startswith("DIGEST lib/gct_handover_digest.py ")


def test_image0_refuses_runtime_entries(world, capsys):
    add_runtime(world["wt"], world["city"], "claude")
    rc, out = refusal(world, "i0", capsys, runtime="none")
    assert rc == 2 and "control-namespace" in out["refused"]


def test_output_under_forbidden_root_refused(world, capsys):
    rc, _ = tool.main(["export", "--worktree", str(world["wt"]), "--clone", str(world["clone"]), "--base", world["base"],
                       "--out", str(world["wt"].parent / "o"), "--runtime", "claude"]), None
    assert rc == 2
