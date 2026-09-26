"""Tests for intake.py and preroute.py against real `git worktree` fixtures. Run: python3 -B -m pytest -q"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import candidate_git  # noqa: E402
import intake  # noqa: E402
import preroute  # noqa: E402

ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
       "LC_ALL": "C"}
UID = os.getuid()
MANAGER = f"user@{UID}.service"
CONTROLLER = os.getpid()  # a real, visible pid: the consistency survey skips its own lineage
CTL_GROUP = f"{MANAGER}/app.slice/gascity-supervisor.service"
CTL_CGROUP = f"/slice/{CTL_GROUP}"
CONTROLLER_FACTS = dict(comm="gc", exe="/x/gc", start=1, ppid=1, seccomp=0, nnp=0, argv=["gc", "supervisor", "run"],
                        cgroup=CTL_CGROUP, ns={"mnt": "mnt:[9]", "pid": "pid:[9]", "time": "time:[9]"})


def run(*argv, cwd):
    subprocess.run(["/usr/bin/git", "-c", "user.name=t", "-c", "user.email=t@t", *argv], cwd=cwd, env=ENV,
                   check=True, capture_output=True)


def head(repo):
    return subprocess.run(["/usr/bin/git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                          env=ENV).stdout.strip()


@pytest.fixture
def layout(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, "SANDBOX_WRITABLE", ())  # tmp_path is under /tmp; the refusal is tested alone
    base = Path(os.path.realpath(tmp_path))
    monkeypatch.setattr(intake, "ARCHIVE", base / "archive")
    slice_root = base / "slice"
    (slice_root / MANAGER / "app.slice").mkdir(parents=True)
    (slice_root / MANAGER / "cgroup.procs").write_text("")
    monkeypatch.setattr(intake, "SLICE", slice_root)
    monkeypatch.setattr(preroute, "CGROUP_FS", base)
    monkeypatch.setattr(preroute, "GC_BIN", "/x/gc")
    monkeypatch.setattr(preroute, "TMUX_TMP", base)
    monkeypatch.setattr(preroute, "ptrace_scope", lambda: 1)
    monkeypatch.setattr(preroute, "process_environ", lambda pid: {"PATH": "/usr/bin"})
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS))
    city = base / "city"
    city.mkdir()
    (city / "city.toml").write_text("[workspace]\n")
    (base / f"tmux-{UID}").mkdir()
    write_group(slice_root, CTL_GROUP, [CONTROLLER])
    repo = base / "gas-city-ops"
    repo.mkdir()
    run("init", "-q", "-b", "main", cwd=repo)
    (repo / "a.py").write_text("print('a')\n")
    (repo / ".gitignore").write_text("__pycache__/\n")
    run("add", "-A", cwd=repo)
    run("commit", "-q", "-m", "base", cwd=repo)
    root = base / "gas-city-ops-candidate-worktrees"
    root.mkdir()
    worktree = root / "ga-x"
    run("worktree", "add", "-q", "-b", "codex/ga-x", str(worktree), cwd=repo)
    fresh_root = base / "gas-city-ops-worktrees"
    fresh_root.mkdir()
    monkeypatch.setattr(intake, "FRESH_ROOT", fresh_root)
    record = dict(controller=dict(pid=CONTROLLER, exe="/x/gc", start=1, cgroup=CTL_GROUP),
                  controller_members=[dict(pid=CONTROLLER, role="controller", exe="/x/gc", start=1)],
                  tmux_socket=str(base / f"tmux-{UID}" / "city"), hidden={}, ptrace_scope=1)
    return dict(base=base, repo=repo, common=repo / ".git", root=root, worktree=worktree, fresh_root=fresh_root,
                slice=slice_root, head=head(repo), record=record, city=city)


def fresh(layout, name="ga-x-intake"):
    target = layout["fresh_root"] / name
    run("worktree", "add", "-q", "--detach", str(target), "HEAD", cwd=layout["repo"])
    return target


def export(layout, out_name="export", base=None):
    return intake.export(layout["root"], layout["common"], layout["worktree"], "ga-x", base or layout["head"],
                         layout["record"], layout["base"] / out_name)


def apply(layout, manifest, target, out_name="export"):
    return intake.apply(layout["root"], layout["common"], layout["base"] / out_name, manifest["manifest_sha256"], target)


def test_round_trip_exports_reviews_and_applies_exact_bytes(layout):
    wt = layout["worktree"]
    (wt / "a.py").write_text("print('changed')\n")
    (wt / "pkg").mkdir()
    (wt / "pkg" / "new.py").write_text("print('new')\n")
    manifest = export(layout)
    assert manifest["changed"] == ["a.py"] and list(manifest["untracked"]) == ["pkg/new.py"]
    target = fresh(layout)
    assert apply(layout, manifest, target)["ok"]
    assert (target / "pkg/new.py").read_text() == "print('new')\n" and (target / "a.py").read_text() == "print('changed')\n"


def test_export_refuses_a_head_other_than_the_coordinator_base(layout):
    with pytest.raises(candidate_git.Refusal, match="not the coordinator's base"):
        export(layout, base="0" * 40)


def test_apply_refuses_a_manifest_other_than_the_reviewed_one(layout):
    (layout["worktree"] / "a.py").write_text("changed\n")
    manifest = export(layout)
    path = layout["base"] / "export" / "manifest.json"
    path.write_text(path.read_text().replace('"a.py"', '"a.py" ', 1))
    with pytest.raises(candidate_git.Refusal, match="not the reviewed export"):
        apply(layout, manifest, fresh(layout))


def test_a_traversing_untracked_key_is_refused_even_in_a_reviewed_manifest(layout):
    (layout["worktree"] / "n.py").write_text("x\n")
    export(layout)
    path = layout["base"] / "export" / "manifest.json"
    value = json.loads(path.read_text())
    value["untracked"] = {"../escape.py": value["untracked"]["n.py"]}
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw)
    with pytest.raises(candidate_git.Refusal, match="unsafe path"):
        intake.apply(layout["root"], layout["common"], layout["base"] / "export", intake.sha(raw), fresh(layout))


def test_a_raced_mode_change_in_the_patch_is_caught_at_apply(layout):
    """A patch whose bytes carry a mode change the export facts did not show is refused on re-derivation."""
    (layout["worktree"] / "a.py").write_text("changed\n")
    export(layout)
    # The bytes git itself would emit for the raced state: the same edit plus chmod +x.
    side = layout["base"] / "side"
    run("worktree", "add", "-q", "--detach", str(side), "HEAD", cwd=layout["repo"])
    (side / "a.py").write_text("changed\n")
    (side / "a.py").chmod(0o755)
    raw = subprocess.run(["/usr/bin/git", "-C", str(side), "diff", "--binary", "--full-index", "--no-renames",
                          "--no-textconv", "--no-ext-diff", "--no-color", "HEAD"], capture_output=True, env=ENV,
                         check=True).stdout
    assert b"new mode 100755" in raw
    patch = layout["base"] / "export" / "candidate.patch"
    patch.write_bytes(raw)
    path = layout["base"] / "export" / "manifest.json"
    value = json.loads(path.read_text())
    value["patch_sha256"] = intake.sha(raw)
    raw_manifest = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw_manifest)
    with pytest.raises(candidate_git.Refusal, match="mode change needs explicit review"):
        intake.apply(layout["root"], layout["common"], layout["base"] / "export", intake.sha(raw_manifest),
                     fresh(layout))


def test_the_fresh_worktree_must_be_a_linked_worktree_under_the_fresh_root(layout):
    (layout["worktree"] / "a.py").write_text("changed\n")
    manifest = export(layout)
    elsewhere = layout["base"] / "elsewhere"
    elsewhere.mkdir()
    target = elsewhere / "ga-x-intake"
    run("worktree", "add", "-q", "--detach", str(target), "HEAD", cwd=layout["repo"])
    with pytest.raises(candidate_git.Refusal, match="not a direct child"):
        apply(layout, manifest, target)


@pytest.mark.parametrize("where", ["inside-root", "tmp"])
def test_export_and_fresh_must_be_outside_candidate_reach(layout, monkeypatch, where):
    if where == "inside-root":
        out = layout["root"] / "export"
    else:
        monkeypatch.setattr(intake, "SANDBOX_WRITABLE", (layout["base"],))
        out = layout["base"] / "export"
    with pytest.raises(candidate_git.Refusal, match="export directory"):
        intake.export(layout["root"], layout["common"], layout["worktree"], "ga-x", layout["head"], layout["record"], out)


@pytest.mark.parametrize("path", [".gitattributes", "sub/.gitattributes", ".gitmodules", ".lfsconfig"])
def test_attribute_module_and_lfs_changes_stop_intake(layout, path):
    target = layout["worktree"] / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("* filter=lfs diff=lfs\n")
    with pytest.raises(candidate_git.Refusal, match="attribute/module/lfs"):
        export(layout)


def test_an_ignored_gitattributes_still_stops_intake(layout):
    (layout["worktree"] / "__pycache__").mkdir()
    (layout["worktree"] / "__pycache__" / ".gitattributes").write_text("* filter=x\n")
    with pytest.raises(candidate_git.Refusal, match="attribute/module/lfs"):
        export(layout)


def test_a_driver_in_the_common_config_stops_intake(layout):
    run("config", "filter.x.clean", "cat", cwd=layout["repo"])
    with pytest.raises(candidate_git.Refusal, match="driver is configured"):
        export(layout)


def test_an_included_driver_is_found(layout, tmp_path):
    included = tmp_path / "included.cfg"
    included.write_text('[diff "x"]\n\ttextconv = cat\n')
    run("config", "include.path", str(included), cwd=layout["repo"])
    with pytest.raises(candidate_git.Refusal, match="driver is configured"):
        export(layout)


@pytest.mark.parametrize("kind", ["hardlink", "symlink-untracked", "fifo", "nested-repo", "unreadable-dir", "binary"])
def test_unsafe_untracked_entries_stop_intake(layout, kind, tmp_path):
    wt = layout["worktree"]
    secret = tmp_path / "secret"
    secret.write_text("vault\n")
    if kind == "hardlink":
        os.link(secret, wt / "notes.md")
    elif kind == "symlink-untracked":
        (wt / "notes.md").symlink_to(secret)
    elif kind == "fifo":
        os.mkfifo(wt / "notes.md")
    elif kind == "nested-repo":
        run("init", "-q", str(wt / "inner"), cwd=wt)
    elif kind == "binary":
        (wt / "blob.bin").write_bytes(b"\x00\x01")
    else:
        (wt / "locked").mkdir()
        (wt / "locked" / "hidden").write_text("x")
        (wt / "locked").chmod(0)
    reason = {"hardlink": "notes.md:multilink", "symlink-untracked": "without following links", "fifo": "notes.md:special",
              "nested-repo": "nested repository", "binary": "binary untracked file", "unreadable-dir": "locked:unreadable"}[kind]
    try:
        with pytest.raises(candidate_git.Refusal, match=reason):
            export(layout)
    finally:
        if kind == "unreadable-dir":
            (wt / "locked").chmod(0o755)


def test_an_intermediate_symlink_is_never_followed_on_read(layout, tmp_path):
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "secret").write_text("vault\n")
    link_parent = layout["base"] / "reader"
    link_parent.mkdir()
    (link_parent / "d").symlink_to(tmp_path / "outside")
    with pytest.raises(candidate_git.Refusal, match="not a real directory"):
        intake.read_regular(link_parent, "d/secret")


@pytest.mark.parametrize("change", ["tracked-symlink", "mode", "binary", "tracked-hardlink"])
def test_link_mode_binary_and_hardlink_changes_stop_intake(layout, change, tmp_path):
    wt = layout["worktree"]
    if change == "tracked-symlink":
        (wt / "a.py").unlink()
        (wt / "a.py").symlink_to("/home/loucmane/gas-city-ops/.git/hooks")
    elif change == "mode":
        (wt / "a.py").chmod(0o755)
    elif change == "binary":
        (wt / "a.py").write_bytes(b"\x00\x01binary")
    else:
        secret = tmp_path / "secret"
        secret.write_text("vault\n")
        (wt / "a.py").unlink()
        os.link(secret, wt / "a.py")
    reason = {"tracked-symlink": "link or special mode", "mode": "mode change needs explicit review",
              "binary": "binary changes need explicit review", "tracked-hardlink": "a.py:multilink"}[change]
    with pytest.raises(candidate_git.Refusal, match=reason):
        export(layout)


def test_ignored_content_is_listed_never_imported(layout):
    cache = layout["worktree"] / "__pycache__"
    cache.mkdir()
    (cache / "a.cpython-312.pyc").write_bytes(b"planted")
    manifest = export(layout)
    assert manifest["ignored"] == ["__pycache__/a.cpython-312.pyc"] and manifest["untracked"] == {}
    target = fresh(layout)
    apply(layout, manifest, target)
    assert not (target / "__pycache__").exists()


def test_privileged_paths_are_reported_and_rederived(layout):
    (layout["worktree"] / ".claude").mkdir()
    (layout["worktree"] / ".claude" / "settings.json").write_text("{}\n")
    (layout["worktree"] / ".pre-commit-config.yaml").write_text("repos: []\n")
    (layout["worktree"] / "docs").mkdir()
    (layout["worktree"] / "docs" / "guide.md").write_text("# guide\n")
    manifest = export(layout)
    assert manifest["privileged"] == [".claude/settings.json", ".pre-commit-config.yaml"]
    assert apply(layout, manifest, fresh(layout))["ok"]


@pytest.mark.parametrize("path", [
    "tomllib.py", "sitecustomize.py", "x.pth", "pytest.ini", "tests/test_x.py", "aegis_mcp/server.py",
    "CLAUDE.local.md", "docs/ai/work-tracking/active/x/designs/ga-6utp-activation/preroute.py",
    "docs/ai/work-tracking/active/x/HANDOFF.md", "plans/current", "sessions/x.md", ".taskmaster/tasks.json",
    "docs/x/CLAUDE.md", "docs/tool.py", "a.py", "docs/aegis/.claude/skills/x/SKILL.md", "docs/x/.claude/agents/y.md",
    "docs/AGENTS.override.md", "docs/x/.codex/y.md", "docs/skills/z/SKILL.md", "docs/GEMINI.md", "docs/claude.md",
    "docs/Agents.md", "docs/x/skill.md"])
def test_everything_but_prose_under_docs_is_privileged(path):
    assert intake.privileged(path)


@pytest.mark.parametrize("path", ["docs/guide.md", "docs/a/b.txt", "docs/x.rst"])
def test_prose_under_docs_is_ordinary(path):
    assert not intake.privileged(path)


def test_an_export_beyond_the_untracked_bounds_refuses(layout, monkeypatch):
    monkeypatch.setattr(intake, "MAX_UNTRACKED_FILES", 2)
    for n in range(3):
        (layout["worktree"] / f"n{n}.txt").write_text("x\n")
    with pytest.raises(candidate_git.Refusal, match="more than 2 untracked files"):
        export(layout)
    monkeypatch.setattr(intake, "MAX_UNTRACKED_FILES", 10)
    monkeypatch.setattr(intake, "MAX_UNTRACKED_BYTES", 4)
    with pytest.raises(candidate_git.Refusal, match="untracked files exceed"):
        export(layout, out_name="export-2")


def test_an_oversized_change_refuses_before_the_patch(layout, monkeypatch):
    monkeypatch.setattr(intake, "MAX_PATCH_BYTES", 8)
    (layout["worktree"] / "a.py").write_text("print('much longer now')\n")
    with pytest.raises(candidate_git.Refusal, match="changed files exceed"):
        export(layout)


def test_a_gitlink_in_the_base_refuses(layout):
    blob = subprocess.run(["/usr/bin/git", "-C", str(layout["repo"]), "rev-parse", "HEAD"], capture_output=True,
                          text=True, env=ENV).stdout.strip()
    run("update-index", "--add", "--cacheinfo", f"160000,{blob},sub", cwd=layout["repo"])
    run("commit", "-q", "-m", "gitlink", cwd=layout["repo"])
    new = head(layout["repo"])
    run("checkout", "-q", "--detach", new, cwd=layout["worktree"])
    with pytest.raises(candidate_git.Refusal, match="gitlinks in the tree"):
        export(layout, base=new)


def test_apply_binds_the_common_directory(layout):
    manifest = export(layout)
    other = layout["base"] / "other.git"
    with pytest.raises(candidate_git.Refusal, match="not taken from this candidate root and common directory"):
        intake.apply(layout["root"], other, layout["base"] / "export", manifest["manifest_sha256"], fresh(layout))


@pytest.mark.parametrize("facts", [dict(cgroup="/init.scope"), dict(comm="bash"), dict(start=2), dict(exe="/tmp/gc"),
                                   dict(seccomp=2), dict(nnp=1),
                                   dict(cgroup=f"/slice/{MANAGER}/app.slice/../app.slice/gascity-supervisor.service")])
def test_export_and_preroute_refuse_a_controller_that_is_not_the_recorded_one(layout, tmp_path, monkeypatch, facts):
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, **facts))
    with pytest.raises(candidate_git.Refusal, match="the city is not quiet before export.*not the recorded process"):
        export(layout)
    with pytest.raises(candidate_git.Refusal, match="the city is not quiet.*not the recorded process"):
        check(layout, bead(tmp_path, layout["worktree"]))


def test_a_pane_scope_member_stops_the_city(layout):
    write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-1234.scope", [999999981])
    assert preroute.city_problems(layout["slice"], layout["record"]) == [
        "city: pane-members=[999999981] extra-controller-members=[] missing-recorded=[]"]


def test_an_unrecorded_controller_cgroup_member_stops_the_city(layout, monkeypatch):
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, 999999982])
    assert preroute.city_problems(layout["slice"], layout["record"]) == [
        "city: pane-members=[] extra-controller-members=[999999982] missing-recorded=[]"]
    # A recorded member missing from the controller cgroup counts as missing even if its pid lives elsewhere.
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER])
    write_group(layout["slice"], f"{MANAGER}/app.slice/other.service", [999999983])
    stale = dict(layout["record"], controller_members=layout["record"]["controller_members"] + [
        dict(pid=999999983, role="dolt", exe="/x/gc", start=1)])
    assert preroute.city_problems(layout["slice"], stale) == [
        "city: pane-members=[] extra-controller-members=[] missing-recorded=[999999983]"]


def test_a_reused_member_pid_is_not_the_recorded_process(layout, monkeypatch):
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, start=1 if pid == CONTROLLER else 9))
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, 999999987])
    record = dict(layout["record"], controller_members=layout["record"]["controller_members"] + [
        dict(pid=999999987, role="dolt", exe="/x/gc", start=1)])
    assert preroute.city_problems(layout["slice"], record) == [
        "controller cgroup member 999999987 (dolt) is not the recorded process"]


def test_the_record_accepts_only_reviewed_roles(layout, monkeypatch):
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, 999999988])
    rogue = dict(CONTROLLER_FACTS, exe="/tmp/x", argv=["x"])
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS) if pid == CONTROLLER else rogue)
    with pytest.raises(candidate_git.Refusal, match="999999988 has no reviewed role"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])
    # A second supervisor is a reviewed role but not a second time.
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS))
    with pytest.raises(candidate_git.Refusal, match="not one controller"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])


def test_member_roles_match_the_live_argv_shapes(monkeypatch):
    monkeypatch.setattr(preroute, "GC_BIN", "/b/gc")
    monkeypatch.setattr(preroute, "DOLT_BIN", "/b/dolt")
    city = Path("/c")
    cfg = "/c/.gc/runtime/packs/dolt/dolt-config.yaml"
    free = dict(seccomp=0, nnp=0)
    assert preroute.member_role(dict(free, exe="/b/gc", argv=["/h/.local/bin/gc", "supervisor", "run"]), city) == "controller"
    assert preroute.member_role(dict(free, exe="/b/gc", argv=["gc", "__gc-managed-dolt-scope-watchdog", cfg,
                                                              "/c/.gc/runtime/packs/dolt/dolt.log", "/c"]), city) == "dolt-watchdog"
    assert preroute.member_role(dict(free, exe="/b/dolt", argv=["dolt", "sql-server", "--config", cfg]), city) == "dolt"
    assert preroute.member_role(dict(free, exe="/b/dolt", argv=["dolt", "sql-server", "--config", "/tmp/x"]), city) is None
    assert preroute.member_role(dict(free, exe="/tmp/gc", argv=["gc", "supervisor", "run"]), city) is None


def test_r10_a_deleted_watchdog_takes_its_role_only_with_the_surviving_image(monkeypatch):
    monkeypatch.setattr(preroute, "GC_BIN", "/b/gc")
    monkeypatch.setattr(preroute, "DOLT_BIN", "/b/dolt")
    city = Path("/c")
    cfg = "/c/.gc/runtime/packs/dolt/dolt-config.yaml"
    watchdog = dict(seccomp=0, nnp=0, exe="/b/gc (deleted)",
                    argv=["gc", "__gc-managed-dolt-scope-watchdog", cfg, "/c/.gc/runtime/packs/dolt/dolt.log", "/c"])
    survivor = next(iter(preroute.SURVIVING_WATCHDOG_IMAGES))
    assert preroute.member_role(watchdog, city, image=lambda: survivor) == "dolt-watchdog"
    assert preroute.member_role(watchdog, city, image=lambda: "0" * 64) is None
    assert preroute.member_role(watchdog, city) is None
    calls = []
    # A deleted controller or dolt never takes a role, and the image is never read for them.
    assert preroute.member_role(dict(watchdog, argv=["gc", "supervisor", "run"]), city,
                                image=lambda: calls.append(1) or survivor) is None
    assert preroute.member_role(dict(watchdog, exe="/b/dolt (deleted)", argv=["dolt", "sql-server", "--config", cfg]),
                                city, image=lambda: calls.append(1) or survivor) is None
    assert calls == []
    assert preroute.member_role(dict(watchdog, nnp=1), city, image=lambda: survivor) is None
    assert preroute.member_role(dict(watchdog, exe="/tmp/gc (deleted)"), city, image=lambda: survivor) is None


@pytest.mark.parametrize("state", [dict(seccomp=2, nnp=1), dict(seccomp=0, nnp=1), dict(seccomp=2, nnp=0)])
def test_a_sandboxed_process_never_takes_a_role(monkeypatch, state):
    """A leftover keeps its seccomp filter and no_new_privs across exec, so reviewed argv is not enough."""
    monkeypatch.setattr(preroute, "DOLT_BIN", "/b/dolt")
    cfg = "/c/.gc/runtime/packs/dolt/dolt-config.yaml"
    assert preroute.member_role(dict(state, exe="/b/dolt", argv=["dolt", "sql-server", "--config", cfg]), Path("/c")) is None


def test_the_record_refuses_a_dolt_without_its_watchdog_parent(layout, monkeypatch):
    city = layout["city"]
    cfg = f"{city}/.gc/runtime/packs/dolt/dolt-config.yaml"
    watchdog = dict(CONTROLLER_FACTS, argv=["gc", "__gc-managed-dolt-scope-watchdog", cfg,
                                            f"{city}/.gc/runtime/packs/dolt/dolt.log", str(city)])
    dolt = dict(CONTROLLER_FACTS, exe="/x/dolt", argv=["dolt", "sql-server", "--config", cfg], ppid=999999970)
    facts = {CONTROLLER: dict(CONTROLLER_FACTS), 999999970: watchdog, 999999971: dolt}
    monkeypatch.setattr(preroute, "DOLT_BIN", "/x/dolt")
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(facts[pid]))
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, 999999970, 999999971])
    monkeypatch.setattr(preroute, "hidden_by_cgroup", lambda slice_root: {})
    record = preroute.observe_city(layout["slice"], CONTROLLER, city)
    assert [m["role"] for m in record["controller_members"]] == ["controller", "dolt-watchdog", "dolt"]
    facts[999999971] = dict(dolt, ppid=1)
    with pytest.raises(candidate_git.Refusal, match="not the child of the recorded watchdog"):
        preroute.observe_city(layout["slice"], CONTROLLER, city)
    facts[999999971] = dict(dolt, ns=dict(CONTROLLER_FACTS["ns"], mnt="mnt:[1]"))
    with pytest.raises(candidate_git.Refusal, match="does not share the controller's namespaces"):
        preroute.observe_city(layout["slice"], CONTROLLER, city)
    facts[999999971] = dict(dolt, ns=dict(CONTROLLER_FACTS["ns"], time="time:[1]"))
    with pytest.raises(candidate_git.Refusal, match="does not share the controller's namespaces"):
        preroute.observe_city(layout["slice"], CONTROLLER, city)
    facts[999999971] = dolt
    facts[999999970] = dict(watchdog, ppid=5)
    with pytest.raises(candidate_git.Refusal, match="not started like the controller"):
        preroute.observe_city(layout["slice"], CONTROLLER, city)


def test_a_controller_start_changed_after_the_clean_read_is_caught(layout, monkeypatch):
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    starts = iter([1, 1, 7, 7, 7, 7])
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, start=next(starts)))
    write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-6.scope", [999999976])
    real = preroute.cgroup_members

    def members(slice_root):
        result = real(slice_root)
        write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-6.scope", [])
        return result

    monkeypatch.setattr(preroute, "cgroup_members", members)
    assert preroute.city_problems(layout["slice"], layout["record"]) == [
        "controller is not the recorded process; refresh the record"]


@pytest.mark.parametrize("change", [dict(start=9), dict(ns={"mnt": "mnt:[1]", "pid": "pid:[9]"}), dict(seccomp=2),
                                    dict(nnp=1), dict(ns={"mnt": "mnt:[9]", "pid": "pid:[9]", "time": "time:[1]"})])
def test_a_recorded_member_changed_on_the_check_path_is_caught(layout, monkeypatch, change):
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    member = 999999977
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, member])
    record = dict(layout["record"], controller_members=layout["record"]["controller_members"] + [
        dict(pid=member, role="dolt", exe="/x/gc", start=1)])
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, **change)
                        if pid == member else dict(CONTROLLER_FACTS))
    assert preroute.city_problems(layout["slice"], record) == [
        f"controller cgroup member {member} (dolt) is not the recorded process"]


def test_a_member_pid_reused_only_after_the_clean_read_is_caught(layout, monkeypatch):
    """The controller is unchanged; the recorded dolt pid is reused between the rereads and the re-proof."""
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    member = 999999978
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, member])
    record = dict(layout["record"], controller_members=layout["record"]["controller_members"] + [
        dict(pid=member, role="dolt", exe="/x/gc", start=1)])
    reads = []

    def facts(pid):
        if pid == member:
            reads.append(1)
            return dict(CONTROLLER_FACTS, start=1 if len(reads) == 1 else 5)
        return dict(CONTROLLER_FACTS)

    monkeypatch.setattr(preroute, "process_facts", facts)
    assert preroute.city_problems(layout["slice"], record) == [
        f"controller cgroup member {member} (dolt) is not the recorded process"]
    assert len(reads) == 2  # once before the membership reads, once after the clean read


def test_the_record_refuses_a_member_that_left_the_controller_cgroup(layout, monkeypatch):
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, 999999979])
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS) if pid == CONTROLLER
                        else dict(CONTROLLER_FACTS, cgroup=f"/slice/{MANAGER}/app.slice/other.service"))
    with pytest.raises(candidate_git.Refusal, match="member 999999979 left the controller cgroup"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])


@pytest.mark.parametrize("role_argv", [["gc", "supervisor", "run"], None])
def test_a_sandboxed_controller_or_watchdog_never_takes_a_role(monkeypatch, role_argv):
    monkeypatch.setattr(preroute, "GC_BIN", "/b/gc")
    cfg = "/c/.gc/runtime/packs/dolt/dolt-config.yaml"
    argv = role_argv or ["gc", "__gc-managed-dolt-scope-watchdog", cfg, "/c/.gc/runtime/packs/dolt/dolt.log", "/c"]
    for state in (dict(seccomp=2, nnp=0), dict(seccomp=0, nnp=1)):
        assert preroute.member_role(dict(state, exe="/b/gc", argv=argv), Path("/c")) is None
    assert preroute.member_role(dict(seccomp=0, nnp=0, exe="/b/gc", argv=argv), Path("/c")) is not None


def test_an_nnp_only_server_is_refused(layout, monkeypatch):
    fake_server = 999999980
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, fake_server])
    monkeypatch.setattr(preroute, "peer_pid", lambda path: fake_server)
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, exe="/usr/bin/tmux", nnp=1)
                        if pid == fake_server else dict(CONTROLLER_FACTS))
    assert "(sandboxed)" in preroute.city_problems(layout["slice"], layout["record"])[0]


def test_process_facts_reads_every_namespace_including_time():
    assert set(preroute.process_facts(os.getpid())["ns"]) == set(preroute.NS_KINDS) and "time" in preroute.NS_KINDS


def test_the_consistency_recheck_drops_transients_and_keeps_persistent_findings(tmp_path, monkeypatch):
    root = tmp_path / "slice"
    write_group(root, f"{MANAGER}/app.slice/x.service", [])
    calls = []

    def holds(root_, uid, proc, pids=None, members=frozenset(), allowed_hidden=frozenset()):
        calls.append(pids)
        if len(calls) % 2:  # the full scan
            return ["111:fd-unreadable", "222:cwd"]
        return ["222:cwd"]  # the recheck: 111 was transient

    monkeypatch.setattr(preroute, "process_holds", holds)
    assert preroute.survey(tmp_path / "candidates", UID, root, {}) == ["222:cwd"]
    assert calls[1] == {111, 222}


def test_the_record_and_every_check_require_yama(layout, monkeypatch):
    monkeypatch.setattr(preroute, "ptrace_scope", lambda: 0)
    with pytest.raises(candidate_git.Refusal, match="ptrace_scope is 0"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])
    assert preroute.city_problems(layout["slice"], layout["record"]) == ["Yama ptrace_scope dropped below 1"]


def test_the_record_refuses_hidden_pids_outside_the_reviewed_cgroups(layout):
    write_group(layout["slice"], f"{MANAGER}/app.slice/x.service", [999999972])
    with pytest.raises(candidate_git.Refusal, match="outside the reviewed cgroups"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])


def test_an_unobservable_or_sandboxed_server_is_refused(layout, monkeypatch):
    fake_server = 999999973
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, fake_server])
    monkeypatch.setattr(preroute, "peer_pid", lambda path: fake_server)

    def hidden(pid):
        if pid == fake_server:
            raise FileNotFoundError("hidden")
        return dict(CONTROLLER_FACTS)

    monkeypatch.setattr(preroute, "process_facts", hidden)
    assert preroute.city_problems(layout["slice"], layout["record"])[0].startswith(
        f"city tmux server {fake_server} is not tmux in the controller cgroup: unobservable")
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, exe="/usr/bin/tmux", seccomp=2)
                        if pid == fake_server else dict(CONTROLLER_FACTS))
    assert "(sandboxed)" in preroute.city_problems(layout["slice"], layout["record"])[0]


def test_the_server_is_rederived_on_every_read(layout, monkeypatch):
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    calls = []

    def server(path):
        calls.append(1)
        return 999999974 if len(calls) == 1 else None

    monkeypatch.setattr(preroute, "peer_pid", server)
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, exe="/usr/bin/tmux")
                        if pid == 999999974 else dict(CONTROLLER_FACTS))
    # The first read sees the server's pid in the cgroup with a pending pane; the server then vanishes and
    # its pid lingers as an ordinary member, which must now count as extra.
    write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-5.scope", [999999975])
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, 999999974])
    real = preroute.cgroup_members

    def members(slice_root):
        result = real(slice_root)
        write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-5.scope", [])
        return result

    monkeypatch.setattr(preroute, "cgroup_members", members)
    assert preroute.city_problems(layout["slice"], layout["record"]) == [
        "city: pane-members=[] extra-controller-members=[999999974] missing-recorded=[]"]


def test_peer_pid_refuses_an_unreadable_socket(layout):
    import socket
    path = Path(layout["record"]["tmux_socket"])
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen(16)
    try:
        path.chmod(0)
        with pytest.raises(candidate_git.Refusal, match="city tmux socket unreadable"):
            preroute.peer_pid(path)
    finally:
        path.chmod(0o700)
        server.close()


def test_a_transient_controller_child_is_tolerated_on_reread(layout, monkeypatch):
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    real, reads = preroute.cgroup_members, []

    def transient(slice_root):
        reads.append(1)
        write_group(layout["slice"], CTL_GROUP, [CONTROLLER, 999999984] if len(reads) == 1 else [CONTROLLER])
        return real(slice_root)

    monkeypatch.setattr(preroute, "cgroup_members", transient)
    assert preroute.city_problems(layout["slice"], layout["record"]) == [] and len(reads) == 2


def test_a_city_tmux_server_must_be_in_the_controller_cgroup(layout, monkeypatch):
    import socket
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(layout["record"]["tmux_socket"])
    server.listen(16)
    me = os.getpid()
    try:
        assert preroute.peer_pid(Path(layout["record"]["tmux_socket"])) == me
    finally:
        server.close()
    fake_server = 999999986
    monkeypatch.setattr(preroute, "peer_pid", lambda path: fake_server)
    monkeypatch.setattr(preroute.time, "sleep", lambda s: None)
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS, exe="/usr/bin/tmux")
                        if pid == fake_server else dict(CONTROLLER_FACTS))
    write_group(layout["slice"], f"{MANAGER}/init.scope", [fake_server])
    problems = preroute.city_problems(layout["slice"], layout["record"])
    assert problems[0] == (f"city tmux server {fake_server} is not tmux in the controller cgroup: "
                           f"/usr/bin/tmux in {MANAGER}/init.scope")
    write_group(layout["slice"], f"{MANAGER}/init.scope", [])
    write_group(layout["slice"], CTL_GROUP, [CONTROLLER, fake_server])
    assert preroute.city_problems(layout["slice"], layout["record"]) == []
    # A listener that is not tmux, in the controller cgroup, is refused (a leftover on the socket path).
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(CONTROLLER_FACTS))
    assert preroute.city_problems(layout["slice"], layout["record"])[0].startswith(
        f"city tmux server {fake_server} is not tmux in the controller cgroup: /x/gc in {CTL_GROUP}")
    monkeypatch.undo()
    # A stale socket file with no listener means no server.
    assert preroute.peer_pid(Path(layout["record"]["tmux_socket"])) is None


def test_peer_pid_refuses_a_non_socket(tmp_path):
    (tmp_path / "plain").write_text("x")
    with pytest.raises(candidate_git.Refusal, match="is not a socket"):
        preroute.peer_pid(tmp_path / "plain")
    assert preroute.peer_pid(tmp_path / "absent") is None


@pytest.mark.parametrize("line, reason", [('[session]\nsocket = "x"\n', "overrides the tmux socket"),
                                          ('[session]\nprovider = "k8s"\n', "non-tmux session backend")])
def test_the_record_refuses_socket_and_backend_overrides(layout, line, reason):
    (layout["city"] / "city.toml").write_text("[workspace]\n" + line)
    with pytest.raises(candidate_git.Refusal, match=reason):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])


@pytest.mark.parametrize("name", ["TMUX_TMPDIR", "GC_AGENT_SLICE", "GC_SESSION"])
def test_the_record_refuses_a_controller_environment_that_moves_panes(layout, monkeypatch, name):
    monkeypatch.setattr(preroute, "process_environ", lambda pid: {name: "x"})
    with pytest.raises(candidate_git.Refusal, match="moves the tmux socket or panes"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])


def test_the_record_uses_the_workspace_name(layout):
    (layout["city"] / "city.toml").write_text('[workspace]\nname = "blue"\n')
    record = preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])
    assert record["tmux_socket"] == str(layout["base"] / f"tmux-{UID}" / "blue")


def test_record_main_writes_exclusively(layout, monkeypatch, capsys):
    monkeypatch.setattr(preroute, "user_slice", lambda uid: layout["slice"])
    out = layout["base"] / "record.json"
    assert preroute.main(["record", str(UID), str(CONTROLLER), str(layout["city"]), str(out)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert preroute.load_record(out, printed["sha256"]) == layout["record"]
    assert preroute.main(["record", str(UID), str(CONTROLLER), str(layout["city"]), str(out)]) == 2
    assert "File exists" in capsys.readouterr().out


def test_an_export_beyond_the_ignored_bound_refuses(layout, monkeypatch):
    monkeypatch.setattr(intake, "MAX_IGNORED", 1)
    cache = layout["worktree"] / "__pycache__"
    cache.mkdir()
    (cache / "a.pyc").write_bytes(b"x")
    (cache / "b.pyc").write_bytes(b"x")
    with pytest.raises(candidate_git.Refusal, match="more than 1 ignored files"):
        export(layout)


def test_process_facts_parses_the_real_proc():
    facts = preroute.process_facts(os.getpid())
    assert facts["comm"] and os.path.isabs(facts["exe"]) and facts["start"] > 0 and facts["cgroup"].startswith("/")


def test_the_city_record_refuses_pane_members_and_a_running_server(layout, monkeypatch):
    write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-9.scope", [999999985])
    with pytest.raises(candidate_git.Refusal, match="tmux pane scopes have members"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])
    # A member in a sub-cgroup of a pane scope is still a pane member.
    write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-9.scope", [])
    write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-9.scope/sub", [999999989])
    with pytest.raises(candidate_git.Refusal, match="tmux pane scopes have members"):
        preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])
    write_group(layout["slice"], f"{MANAGER}/app.slice/tmux-spawn-9.scope/sub", [])
    record = preroute.observe_city(layout["slice"], CONTROLLER, layout["city"])
    assert record == layout["record"]


THREAD_CWD = """
import os, threading, time
def work():
    os.unshare(os.CLONE_FS)
    os.chdir(os.environ["TARGET"])
    time.sleep(30)
threading.Thread(target=work, daemon=True).start()
time.sleep(30)
"""


def test_a_thread_with_its_own_cwd_under_the_root_is_a_hold(layout):
    import time
    holder = subprocess.Popen([sys.executable, "-c", THREAD_CWD], cwd="/",
                              env=dict(os.environ, TARGET=str(layout["worktree"])))
    try:
        time.sleep(0.5)
        held = preroute.process_holds(layout["root"], UID)
        assert [h for h in held if h.startswith(f"{holder.pid}:")] == [f"{holder.pid}:task-cwd"]
    finally:
        holder.kill()
        holder.wait()


def test_an_unreadable_cgroup_directory_refuses_the_survey(tmp_path):
    root = tmp_path / "slice"
    write_group(root, f"{MANAGER}/app.slice/x.service", [])
    (root / MANAGER / "app.slice").chmod(0)
    try:
        with pytest.raises(candidate_git.Refusal, match="cgroup walk error"):
            preroute.survey(tmp_path / "candidates", UID, root, {})
    finally:
        (root / MANAGER / "app.slice").chmod(0o755)


@pytest.mark.parametrize("tamper", ["gitfile-retargeted", "commondir", "backpointer"])
def test_a_tampered_link_refuses_before_any_git(layout, tamper):
    admin = layout["common"] / "worktrees" / "ga-x"
    if tamper == "gitfile-retargeted":
        other = layout["fresh_root"] / "coord"
        run("worktree", "add", "-q", "--detach", str(other), "HEAD", cwd=layout["repo"])
        (layout["worktree"] / ".git").write_text(f"gitdir: {layout['common']}/worktrees/coord\n")
    elif tamper == "commondir":
        (admin / "commondir").write_text("/elsewhere\n")
    else:
        (admin / "gitdir").write_text("/elsewhere/.git\n")
    reason = {"gitfile-retargeted": "gitfile does not name", "commondir": "admin commondir mismatch",
              "backpointer": "admin back-pointer mismatch"}[tamper]
    with pytest.raises(candidate_git.Refusal, match=reason):
        export(layout)


def test_apply_refuses_a_dirty_fresh_worktree(layout):
    (layout["worktree"] / "a.py").write_text("changed\n")
    manifest = export(layout)
    target = fresh(layout)
    (target / "stray").write_text("x")
    with pytest.raises(candidate_git.Refusal, match="not clean"):
        apply(layout, manifest, target)


def test_retire_moves_and_locks_the_candidate(layout):
    result = intake.retire(layout["root"], layout["common"], layout["worktree"], "ga-x", "ga-x")
    assert Path(result["archived"]).is_dir() and not layout["worktree"].exists()
    assert (layout["common"] / "worktrees" / "ga-x" / "locked").exists()


def test_a_failed_retirement_locks_in_place(layout):
    (layout["common"] / "worktrees" / "ga-x" / "gitdir").write_text("/elsewhere/.git\n")
    with pytest.raises(candidate_git.Refusal, match="retirement failed at verify; lock attempted on"):
        intake.retire(layout["root"], layout["common"], layout["worktree"], "ga-x", "ga-x")
    assert layout["worktree"].exists()


# ---------------------------------------------------------------- preroute

def bead(tmp_path, work_dir, description="d"):
    path = tmp_path / "bead.json"
    path.write_text(json.dumps([{"id": "ga-x", "description": description,
                                 "metadata": {"gc.work_dir": str(work_dir)}}]))
    return path


def check(layout, bead_path, expected=None, base=None, description="d"):
    return preroute.check(layout["root"], layout["common"], "ga-x", bead_path, UID,
                          dict(layout["record"], hidden=expected or {}),
                          base or layout["head"], hashlib.sha256(description.encode()).hexdigest(), layout["slice"])


def test_preroute_passes_a_fresh_clean_worktree(layout, tmp_path):
    assert check(layout, bead(tmp_path, layout["worktree"]))["ok"]


NONDUMPABLE = "import ctypes, time; ctypes.CDLL(None).prctl(4, 0, 0, 0, 0); time.sleep(30)"


@pytest.mark.parametrize("problem", ["extra-entry", "dirty", "ignored", "work-dir", "process", "non-dumpable",
                                     "base", "description"])
def test_preroute_refuses(layout, tmp_path, problem):
    work_dir, holder, base, description = layout["worktree"], None, None, "d"
    if problem == "extra-entry":
        (layout["root"] / "leftover").mkdir()
    elif problem == "dirty":
        (layout["worktree"] / "a.py").write_text("x\n")
    elif problem == "ignored":
        (layout["worktree"] / "__pycache__").mkdir()
        (layout["worktree"] / "__pycache__" / "p.pyc").write_bytes(b"x")
    elif problem == "work-dir":
        work_dir = layout["base"] / "elsewhere"
    elif problem == "process":
        holder = subprocess.Popen(["/usr/bin/sleep", "30"], cwd=layout["worktree"])
    elif problem == "non-dumpable":
        # Under hidepid=2 it is invisible in /proc and only cgroup membership shows it (hidden:...); without
        # hidepid it stays visible but its cwd is unreadable (cwd-unreadable). Both are the same refusal.
        holder = subprocess.Popen([sys.executable, "-c", NONDUMPABLE], cwd="/")
        import time
        time.sleep(0.5)
        (layout["slice"] / MANAGER / "app.slice" / "cgroup.procs").write_text(f"{holder.pid}\n")
    elif problem == "base":
        base = "0" * 40
    else:
        description = "tampered"
    reason = {"extra-entry": "must hold exactly", "dirty": "not freshly clean", "ignored": "not freshly clean",
              "work-dir": "gc.work_dir", "process": "hold the candidate root", "non-dumpable": "hold the candidate root",
              "base": "is not the coordinator's base", "description": "description is not the one"}[problem]
    try:
        with pytest.raises(candidate_git.Refusal, match=reason):
            check(layout, bead(tmp_path, work_dir), base=base, description="d" if problem != "description" else "d2")
    finally:
        if holder:
            holder.kill()
            holder.wait()


def write_group(root, group, pids):
    (root / group).mkdir(parents=True, exist_ok=True)
    (root / group / "cgroup.procs").write_text("".join(f"{p}\n" for p in pids))


def test_hidden_pids_are_accepted_only_as_the_exact_recorded_set(tmp_path):
    root = tmp_path / "slice"
    init, gpg = f"{MANAGER}/init.scope", f"{MANAGER}/app.slice/gpg-agent.service"
    write_group(root, init, [999999999, 999999998])
    write_group(root, gpg, [999999997])
    expected = {init: [999999998, 999999999], gpg: [999999997]}
    assert preroute.hidden_processes(root, expected, UID) == []
    # A hidden process that moved itself into init.scope changes the recorded set.
    write_group(root, init, [999999999, 999999998, 999999996])
    assert preroute.hidden_processes(root, expected, UID) == [f"hidden:{init}:[999999996, 999999998, 999999999]"]


def test_a_member_that_toggles_visibility_between_scans_is_caught(tmp_path, monkeypatch):
    """r3 review B: hidden while the holds scan reaches it, visible again at the hidden check."""
    root, proc = tmp_path / "slice", tmp_path / "proc"
    write_group(root, f"{MANAGER}/app.slice/x.service", [424242])
    proc.mkdir()
    real = preroute.cgroup_members
    calls = []

    def toggling(slice_root):
        calls.append(1)
        entry = proc / "424242"
        if len(calls) % 2:          # the membership read that feeds the holds scan: hide
            if entry.exists():
                entry.rmdir()
        else:                       # the membership read that feeds the hidden check: show
            entry.mkdir(exist_ok=True)
        return real(slice_root)

    monkeypatch.setattr(preroute, "cgroup_members", toggling)
    problems = preroute.survey(tmp_path / "candidates", UID, root, {}, proc)
    assert problems == ["424242:hidden-during-scan:entry"] and len(calls) == 4


def test_a_recorded_hidden_pid_is_not_a_scan_finding(tmp_path):
    root, proc = tmp_path / "slice", tmp_path / "proc"
    gpg = f"{MANAGER}/app.slice/gpg-agent.service"
    write_group(root, gpg, [424243])
    proc.mkdir()
    assert preroute.survey(tmp_path / "candidates", UID, root, {gpg: [424243]}, proc) == []


def test_an_unreadable_cgroup_directory_refuses(tmp_path):
    root = tmp_path / "slice"
    write_group(root, f"{MANAGER}/app.slice/x.service", [])
    (root / MANAGER / "app.slice").chmod(0)
    try:
        with pytest.raises(candidate_git.Refusal, match="cgroup walk error"):
            preroute.hidden_by_cgroup(root)
    finally:
        (root / MANAGER / "app.slice").chmod(0o755)


def test_expected_hidden_may_only_name_reviewed_cgroups(tmp_path):
    root = tmp_path / "slice"
    write_group(root, MANAGER, [])
    with pytest.raises(candidate_git.Refusal, match="non-reviewed cgroup"):
        preroute.hidden_processes(root, {f"{MANAGER}/app.slice/x.service": [1]}, UID)


def test_a_process_holding_the_root_stops_export(layout):
    holder = subprocess.Popen(["/usr/bin/sleep", "30"], cwd=layout["worktree"])
    try:
        with pytest.raises(candidate_git.Refusal, match="hold the candidate root or are hidden before"):
            export(layout)
    finally:
        holder.kill()
        holder.wait()


def test_a_stale_hidden_record_is_itself_a_stop(tmp_path):
    root = tmp_path / "slice"
    gpg = f"{MANAGER}/app.slice/gpg-agent.service"
    write_group(root, gpg, [])
    assert preroute.hidden_processes(root, {gpg: [999999997]}, UID) == [f"hidden:{gpg}:[]"]


def test_a_hidden_member_is_never_treated_as_exited(tmp_path):
    """A pid listed in the slice but invisible in /proc is hidden, whatever /proc listed earlier."""
    root = tmp_path / "slice"
    write_group(root, f"{MANAGER}/app.slice/x.service", [999999995])
    problems = preroute.survey(tmp_path / "no-root", UID, root, {})
    assert problems == ["999999995:hidden-during-scan:entry", f"hidden:{MANAGER}/app.slice/x.service:[999999995]"]


def test_the_process_record_is_bound_by_digest_and_shape(tmp_path, layout):
    path = tmp_path / "record.json"
    raw = preroute.encode_record(layout["record"])
    path.write_bytes(raw)
    with pytest.raises(candidate_git.Refusal, match="not the reviewed record"):
        preroute.load_record(path, "0" * 64)
    assert preroute.load_record(path, hashlib.sha256(raw).hexdigest()) == layout["record"]
    path.write_text("{}")
    with pytest.raises(candidate_git.Refusal, match="process record shape"):
        preroute.load_record(path, hashlib.sha256(b"{}").hexdigest())


def test_the_fresh_worktree_must_be_named_for_its_candidate(layout):
    (layout["worktree"] / "a.py").write_text("changed\n")
    manifest = export(layout)
    with pytest.raises(candidate_git.Refusal, match="must be named ga-x-intake"):
        apply(layout, manifest, fresh(layout, name="ga-other-intake"))
