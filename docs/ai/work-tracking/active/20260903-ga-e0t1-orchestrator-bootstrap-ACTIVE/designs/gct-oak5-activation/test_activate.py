"""Tests for the Template-lane activate.py against a fixture city, Template repo, fake gc and fake renderer.

The fake gc follows the Core interfaces the live dry run observed (2026-09-27, gc 207a78e2):
- `gc status --json` with partial/partial_errors; `gc reload --json` lifecycle JSON;
- `gc config show --validate` and `--json`: Template agents compose the pack default provider claude, then every
  [[patches.agent]] (city.toml and the managed fragment) in order, then [[rigs.overrides]], which win;
- `gc agent list --json`: qualified_name gas-city-template/gc.<name>, provider and pool from the composition.
The fake renderer emits the real template-candidate-provider.toml from Template 3474abfa with the one grant.
Run: python3 -B -m pytest -q
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import activate  # noqa: E402
import preroute  # noqa: E402

ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
LIVE_TEMPLATE = Path("/home/loucmane/gas-city-template")
MERGE = "3474abfaec255f7ea4266ce8aa35218afcfc89b0"
PYTHON = {"name": "python", "executable": {"path": "/usr/bin/python3.12", "resolved_path": "/usr/bin/python3.12",
                                           "sha256": "e" * 64, "version_args": ["--version"], "version": "Python 3.12.3"}}
NEW_AT_TARGET = ("bin/gct-claude-template-candidate-worker", "lib/gct_claude_template_candidate_worker.py",
                 activate.POLICY, activate.PROVIDER_TEMPLATE, activate.PROFILE)
EXISTING_FRAGMENT = (
    '[providers.claude-signing]\nbase = "provider:claude"\n\n'
    '[[patches.agent]]\ndir = "gascity"\nname = "implementation-worker"\nprovider = "claude-signing"\n'
)
CITY_TOML = (
    '[workspace]\nprovider = "claude"\n\n'
    '[[rigs]]\nname = "gas-city-template"\ndefault_branch = "main"\n\n'
    '[[rigs.overrides]]\nagent = "run-operator"\nprovider = "claude"\n[rigs.overrides.option_defaults]\n'
    'model = "haiku-4-5"\npermission_mode = "auto-edit"\nworktree_access = "template-worktrees-and-git-metadata"\n\n'
    + activate.OVERRIDE_BLOCK +
    '[[rigs]]\nname = "gascity"\n\n'
    '[[patches.agent]]\n' + activate.PATCH_BEFORE + '\n'
    '[[patches.agent]]\ndir = "gas-city-template"\nname = "run-operator"\n'
    'work_dir_roots = ["/home/loucmane/gas-city-template-worktrees"]\n'
)

FAKE_GC = r'''#!/usr/bin/env python3
import json, os, sys, tomllib
city = sys.argv[2]
args = sys.argv[3:]
state = json.loads(open(os.environ["FAKE_GC_STATE"]).read())
def compose():
    cfg = tomllib.loads(open(os.path.join(city, "city.toml")).read())
    if state.get("config_invalid"):
        sys.stderr.write("invalid config\n"); sys.exit(1)
    frag = tomllib.loads(open(os.path.join(city, "managed/rig-permissions.toml")).read())
    agents = {}
    for name in ("implementation-worker", "run-operator"):
        agents[name] = {"Name": name, "Dir": "gas-city-template", "Scope": "rig", "Provider": "claude",
                        "OptionDefaults": None, "WorkDirRoots": None, "MaxActiveSessions": None}
    for patch in cfg.get("patches", {}).get("agent", []) + frag.get("patches", {}).get("agent", []):
        a = agents.get(patch["name"]) if patch.get("dir") == "gas-city-template" else None
        if a is None:
            continue
        if "provider" in patch: a["Provider"] = patch["provider"]
        if "option_defaults" in patch: a["OptionDefaults"] = dict(a["OptionDefaults"] or {}, **patch["option_defaults"])
        if "work_dir_roots" in patch: a["WorkDirRoots"] = patch["work_dir_roots"]
        if "max_active_sessions" in patch: a["MaxActiveSessions"] = patch["max_active_sessions"]
    for rig in cfg.get("rigs", []):
        if rig["name"] != "gas-city-template":
            continue
        for o in rig.get("overrides", []):
            a = agents[o["agent"]]
            a["Provider"] = o.get("provider", a["Provider"])
            a["OptionDefaults"] = o.get("option_defaults", a["OptionDefaults"])
    if state.get("keep_old_provider"):
        agents["implementation-worker"]["Provider"] = "claude"
    return list(agents.values())
if args[:2] == ["status", "--json"]:
    print(json.dumps({"partial": state.get("partial", False), "controller": {"running": True, "pid": state["pid"]},
                      "agents": [{"name": "implementation-worker", "running": state.get("running", False)}],
                      "summary": {"active_sessions": 0},
                      "rigs": [{"name": "gas-city-template", "suspended": state.get("suspended", True)}]}))
elif args[:2] == ["reload", "--json"]:
    print(json.dumps({"schema_version": "1", "ok": True, "command": "reload", "action": "reload", "async": False,
                      "soft": False, "outcome": state.get("outcome", "applied"), "revision": "rev-2"}))
elif args[:2] == ["config", "show"]:
    agents = compose()
    if "--validate" in args:
        sys.exit(0)
    print(json.dumps({"config": {"Agents": agents}}))
elif args[:3] == ["agent", "list", "--json"]:
    agents = compose()
    print(json.dumps({"schema_version": "1", "city_name": os.path.basename(city), "agents": [
        {"name": a["Name"], "qualified_name": "gas-city-template/gc." + a["Name"], "dir": a["Dir"],
         "provider": a["Provider"], "suspended": False,
         "pool": {"min": 0, "max": a["MaxActiveSessions"] if a["MaxActiveSessions"] else -1}} for a in agents]}))
else:
    sys.exit(9)
'''

FAKE_RENDERER = r'''import hashlib, json, pathlib, sys
root = pathlib.Path(__file__).resolve().parents[1]
def arg(name, default):
    return pathlib.Path(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
city = arg("--city", None)
target = arg("--output", city / "managed/rig-permissions.toml")
registry_path = arg("--registry", city / "managed/rig-permissions.json")
raw_registry = registry_path.read_bytes()
registry = json.loads(raw_registry)
provider_text = (root / "templates/claude/template-candidate-provider.toml").read_text()
text = EXISTING
for record in registry["rigs"]:
    if record.get("name") != "gas-city-template":
        continue
    policy = str(root / record["control_policy"]["source"])
    choice = ("[[providers.claude-template-candidate.options_schema.choices]]\nvalue = \"managed-t\"\n"
              "label = \"gas-city-template worktrees under the candidate control policy\"\n"
              "flag_args = " + json.dumps(["--settings", policy, "--add-dir", record["worktree_root"]]) + "\n")
    text += "\n" + provider_text.replace("# @managed-rig-choices@", choice)
    text += PATCH.replace("PATHV", json.dumps(record["environment"]["PATH"]))
new = text.encode()
expected = hashlib.sha256(new).hexdigest()
actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
report = {"state": "drift" if actual else "missing", "expected_sha256": expected, "actual_sha256": actual,
          "registry_file_sha256": hashlib.sha256(raw_registry).hexdigest(),
          "provider_template_sha256s": {"claude-template-candidate": hashlib.sha256(provider_text.encode()).hexdigest()}}
if "--check" in sys.argv:
    print(json.dumps(report)); sys.exit(4)
target.write_bytes(new)
print(json.dumps(dict(report, state="conformant", actual_sha256=expected)))
'''
PATCH = ("\n[[patches.agent]]\ndir = \"gas-city-template\"\nname = \"implementation-worker\"\n"
         "provider = \"claude-template-candidate\"\n[patches.agent.option_defaults]\nmodel = \"opus-5-5\"\n"
         "permission_mode = \"full-auto\"\nmanaged_worktree_access = \"managed-t\"\n\n[patches.agent.env]\nPATH = PATHV\n")


def renderer_source(patch=PATCH):
    return FAKE_RENDERER.replace("EXISTING", repr(EXISTING_FRAGMENT)).replace("PATCH.replace", repr(patch) + ".replace")


def real_provider_template() -> bytes:
    return subprocess.run(["/usr/bin/git", "--no-optional-locks", "-C", str(LIVE_TEMPLATE), "show",
                           f"{MERGE}:{activate.PROVIDER_TEMPLATE}"], capture_output=True, check=True, env=ENV).stdout


def git(*argv, cwd):
    subprocess.run(["/usr/bin/git", "-c", "user.name=t", "-c", "user.email=t@t", *argv], cwd=cwd, env=ENV,
                   check=True, capture_output=True)


def head(repo):
    return subprocess.run(["/usr/bin/git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                          text=True, env=ENV).stdout.strip()


def profile(candidate_root):
    return {"schema": "gc.managed-rig-permissions.v2", "rigs": [
        {"name": "gas-city-template", "repository_path": "/home/loucmane/gas-city-template",
         "worktree_root": candidate_root, "agents": ["implementation-worker"], "git_metadata": False,
         "provider": "claude", "control_policy": {"source": activate.POLICY, "sha256": "0" * 64},
         "environment": {"PATH": "/usr/bin:/bin"}, "toolchains": [PYTHON]}]}


def gc_state(world, **values):
    path = Path(world["pins"]["env"]["FAKE_GC_STATE"])
    state = json.loads(path.read_text())
    state.update(values)
    path.write_text(json.dumps(state))


@pytest.fixture
def world(tmp_path, monkeypatch):
    base = Path(os.path.realpath(tmp_path))
    monkeypatch.setattr(preroute, "CGROUP_FS", base)
    monkeypatch.setattr(preroute, "TMUX_TMP", base)
    monkeypatch.setattr(preroute, "process_environ", lambda pid: {"PATH": "/usr/bin"})
    monkeypatch.setattr(preroute, "GC_BIN", "/x/gc")
    monkeypatch.setattr(preroute, "ptrace_scope", lambda: 1)
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(
        comm="gc", exe="/x/gc", start=1, ppid=1, seccomp=0, nnp=0, argv=["gc", "supervisor", "run"], ns={},
        cgroup=f"/slice/user@{os.getuid()}.service/app.slice/gascity-supervisor.service"))
    candidate_root = base / "candidates"
    city = base / "city"
    (city / "managed").mkdir(parents=True)
    (city / ".gc/runtime").mkdir(parents=True)
    (city / ".gc/runtime/suspension-state.json").write_text('{"suspended": true}\n')
    (city / "city.toml").write_text(CITY_TOML)
    (city / "managed/rig-permissions.json").write_text(
        json.dumps({"schema": "gc.managed-rig-permissions.v2", "rigs": []}, indent=2) + "\n")
    (city / "managed/rig-permissions.toml").write_text(EXISTING_FRAGMENT)
    template = base / "template"
    template.mkdir()
    git("init", "-q", "-b", "main", cwd=template)
    for path in activate.LANE_FILES:
        if path not in NEW_AT_TARGET:
            (template / path).parent.mkdir(parents=True, exist_ok=True)
            (template / path).write_text(f"# before {path}\n")
    git("add", "-A", cwd=template)
    git("commit", "-q", "-m", "before", cwd=template)
    before = head(template)
    for path in activate.LANE_FILES:
        (template / path).parent.mkdir(parents=True, exist_ok=True)
        (template / path).write_text(f"# after {path}\n")
    (template / activate.PROFILE).write_text(json.dumps(profile(str(candidate_root))))
    (template / "bin/gct-managed-rig-permissions").write_text(renderer_source())
    (template / activate.PROVIDER_TEMPLATE).write_bytes(real_provider_template())
    git("add", "-A", cwd=template)
    git("commit", "-q", "-m", "merge", cwd=template)
    after = head(template)
    tree = subprocess.run(["/usr/bin/git", "-C", str(template), "rev-parse", after + "^{tree}"], capture_output=True,
                          text=True, env=ENV).stdout.strip()
    changed = subprocess.run(["/usr/bin/git", "-C", str(template), "diff", "--name-only", before, after],
                             capture_output=True, text=True, env=ENV).stdout.split()
    git("checkout", "-q", "--detach", before, cwd=template)
    slice_root = base / "slice"
    (slice_root / f"user@{os.getuid()}.service").mkdir(parents=True)
    (slice_root / f"user@{os.getuid()}.service" / "cgroup.procs").write_text("")
    controller_group = slice_root / f"user@{os.getuid()}.service/app.slice/gascity-supervisor.service"
    controller_group.mkdir(parents=True)
    (controller_group / "cgroup.procs").write_text(f"{os.getpid()}\n")
    gc = base / "gc"
    gc.write_text(FAKE_GC)
    gc.chmod(0o755)
    (base / "gc-state.json").write_text(json.dumps({"pid": os.getpid()}))
    pins = dict(city=str(city), template=str(template), candidate_root=str(candidate_root),
                gc=str(gc), env={"PATH": "/usr/bin:/bin", "FAKE_GC_STATE": str(base / "gc-state.json")},
                managed_settings=str(base / "managed-settings.json"), managed_mcp=str(base / "managed-mcp.json"),
                claude_json=str(base / "claude.json"), sandbox_writable=["/var/tmp", "/dev/shm"],
                user_slice=str(slice_root), template_changed=changed, template_tree=tree,
                uid=os.getuid(), candidate_path="/usr/bin:/bin", python_toolchain=PYTHON, template_status="",
                registry_before=activate.sha(city / "managed/rig-permissions.json"),
                city_before=activate.sha(city / "city.toml"),
                fragment_before=activate.sha(city / "managed/rig-permissions.toml"),
                template_before=before, template_commit=after,
                renderer_sha=activate.digest(renderer_source().encode()), executor=activate.executor_digests())
    record = activate.candidate_record(profile(str(candidate_root)), PYTHON, str(candidate_root))
    pins["inputs"] = {
        activate.REGISTRY_NAME: activate.digest(activate.new_registry((city / "managed/rig-permissions.json").read_bytes(), record)),
        activate.CITY_NAME: activate.digest(activate.new_city((city / "city.toml").read_bytes(), str(candidate_root)))}
    package = base / "package"
    (package / "records").mkdir(parents=True)
    (package / "inputs").mkdir()
    return dict(base=base, city=city, template=template, pins=pins, package=package, after=after, before=before)


def pkg(world):
    return activate.Package(world["package"], activate.Live(world["pins"]), "p" * 64)


def run_all(world, upto=activate.STEPS):
    for step in upto:
        activate.ACTIONS[step](pkg(world))


def record(world, step):
    return json.loads((world["package"] / "records" / f"{step}.json").read_text())


def upto(step):
    return activate.STEPS[: activate.STEPS.index(step)]


# ---------------------------------------------------------------- the reviewed path

def test_the_full_sequence_reaches_the_reviewed_state(world):
    run_all(world)
    composed = record(world, "reload")["composed"]
    assert composed["worker"] == {"Provider": "claude-template-candidate", "OptionDefaults": {
        "model": "opus-5-5", "permission_mode": "full-auto", "managed_worktree_access": "managed-t"},
        "WorkDirRoots": [world["pins"]["candidate_root"]], "MaxActiveSessions": 1, "Scope": "rig"}
    assert composed["operator"]["Provider"] == "claude"
    assert composed["listed"]["pool"] == {"min": 0, "max": 1}
    assert head(world["template"]) == world["after"]
    checkout = record(world, "checkout")
    assert all(checkout["lane_files"][p] for p in activate.LANE_FILES)
    assert activate.sha(world["city"] / "city.toml") == world["pins"]["inputs"]["city.toml"]


def test_every_record_carries_the_binding(world):
    run_all(world, ("host",))
    assert record(world, "host")["binding"]["pins_sha256"] == "p" * 64
    other = activate.Package(world["package"], activate.Live(world["pins"]), "q" * 64)
    with pytest.raises(activate.Refusal, match="another binding"):
        activate.step_inputs(other)


@pytest.mark.parametrize("problem", ["partial", "running", "unsuspended"])
def test_quiet_refuses_an_unquiet_or_partial_city(world, problem):
    gc_state(world, **{"partial": {"partial": True}, "running": {"running": True},
                       "unsuspended": {"suspended": False}}[problem])
    reason = {"partial": "partial status observation", "running": "an agent is running",
              "unsuspended": "a rig is not suspended"}[problem]
    with pytest.raises(activate.Refusal, match=reason):
        activate.step_host(pkg(world))


def test_steps_run_only_in_order(world):
    with pytest.raises(activate.Refusal, match="earlier step missing"):
        activate.step_render(pkg(world))


# ---------------------------------------------------------------- derivations

def test_new_city_makes_exactly_the_three_edits(world):
    raw = (world["city"] / "city.toml").read_bytes()
    new = activate.new_city(raw, "/c").decode()
    assert activate.OVERRIDE_BLOCK not in new and 'agent = "run-operator"' in new
    assert 'work_dir_roots = ["/c"]\nmax_active_sessions = 1\n' in new
    assert len(raw.decode()) - len(activate.OVERRIDE_BLOCK) + len(activate.patch_after("/c")) \
        - len(activate.PATCH_BEFORE) == len(new)


@pytest.mark.parametrize("change", ["no-override", "two-overrides", "no-patch", "operator-changed", "other-rig"])
def test_new_city_refuses_an_unexpected_predecessor(world, change):
    text = CITY_TOML
    if change == "no-override":
        text = text.replace(activate.OVERRIDE_BLOCK, "")
    elif change == "two-overrides":
        text = text.replace(activate.OVERRIDE_BLOCK, activate.OVERRIDE_BLOCK * 2)
    elif change == "no-patch":
        text = text.replace(activate.PATCH_BEFORE, activate.PATCH_BEFORE.replace("implementation-worker", "x"))
    elif change == "operator-changed":
        text = text.replace('model = "haiku-4-5"', 'model = "opus-5-5"', 1).replace(
            'agent = "run-operator"', 'agent = "other"', 1)
    elif change == "other-rig":
        text = text.replace('[[rigs]]\nname = "gascity"\n', '[[rigs]]\nname = "gascity"\ndefault_branch = "x"\n')
        activate.new_city(text.encode(), "/c")  # another rig's content is carried unchanged, not a refusal
        return
    with pytest.raises(activate.Refusal):
        activate.new_city(text.encode(), "/c")


def test_candidate_record_refuses_a_foreign_profile(world):
    good = profile("/c")
    activate.candidate_record(good, PYTHON, "/c")
    for key, value in (("worktree_root", "/other"), ("git_metadata", True), ("agents", ["x"]),
                       ("toolchains", [dict(PYTHON, name="py")])):
        bad = json.loads(json.dumps(good))
        bad["rigs"][0][key] = value
        with pytest.raises(activate.Refusal):
            activate.candidate_record(bad, PYTHON, "/c")


def test_registry_refuses_a_second_registration(world):
    record_value = activate.candidate_record(profile("/c"), PYTHON, "/c")
    once = activate.new_registry((world["city"] / "managed/rig-permissions.json").read_bytes(), record_value)
    with pytest.raises(activate.Refusal, match="already registered"):
        activate.new_registry(once, record_value)


# ---------------------------------------------------------------- checkout

def test_checkout_moves_to_the_reviewed_merge(world):
    run_all(world, upto("registry"))
    assert head(world["template"]) == world["after"]
    assert record(world, "checkout")["before_commit"] == world["before"]


def test_checkout_refuses_a_dirty_canonical_checkout(world):
    run_all(world, upto("checkout"))
    (world["template"] / "stray.txt").write_text("x")
    with pytest.raises(activate.Refusal, match="not clean"):
        activate.step_checkout(pkg(world))
    assert head(world["template"]) == world["before"]


def test_checkout_refuses_a_different_change_set_or_tree(world):
    run_all(world, upto("checkout"))
    world["pins"]["template_changed"] = world["pins"]["template_changed"][1:]
    with pytest.raises(activate.Refusal, match="change set"):
        activate.step_checkout(pkg(world))
    world["pins"]["template_tree"] = "0" * 40
    with pytest.raises(activate.Refusal, match="reviewed tree"):
        activate.step_checkout(pkg(world))


def test_checkout_refuses_a_group_writable_lane_file(world):
    run_all(world, upto("checkout"))
    os.chmod(world["template"] / "bin/gct-claude-signing-worker", 0o664)
    with pytest.raises(activate.Refusal, match="group- or world-writable"):
        activate.step_checkout(pkg(world))


# ---------------------------------------------------------------- render

def swap_renderer(world, source):
    git("checkout", "-q", "--detach", world["after"], cwd=world["template"])
    (world["template"] / "bin/gct-managed-rig-permissions").write_text(source)
    git("commit", "-q", "-am", "swap", cwd=world["template"])
    world["after"] = head(world["template"])
    world["pins"]["template_tree"] = subprocess.run(["/usr/bin/git", "-C", str(world["template"]), "rev-parse",
                                                     world["after"] + "^{tree}"], capture_output=True, text=True,
                                                    env=ENV).stdout.strip()
    git("checkout", "-q", "--detach", world["before"], cwd=world["template"])
    world["pins"]["template_commit"] = world["after"]
    world["pins"]["renderer_sha"] = activate.digest(source.encode())


@pytest.mark.parametrize("source,reason", [
    (lambda: renderer_source().replace("claude-signing", "claude-x"), "an existing agent patch changed"),
    (lambda: renderer_source(PATCH.replace("PATH = PATHV", 'PATH = "/tmp"')), "Template patch env"),
    (lambda: renderer_source(PATCH.replace('permission_mode = \\"full-auto\\"', 'permission_mode = \\"auto-edit\\"')
                             .replace('permission_mode = "full-auto"', 'permission_mode = "auto-edit"')),
     "option_defaults"),
])
def test_a_wrong_render_refuses_before_any_live_write(world, source, reason):
    swap_renderer(world, source())
    run_all(world, upto("render"))
    before = activate.sha(world["city"] / "managed/rig-permissions.toml")
    with pytest.raises(activate.Refusal, match=reason):
        activate.step_render(pkg(world))
    assert activate.sha(world["city"] / "managed/rig-permissions.toml") == before
    assert not (world["package"] / "records/render.intent.json").exists()


# ---------------------------------------------------------------- city

def test_city_refuses_before_writing_when_core_rejects_the_postimage(world):
    run_all(world, upto("city"))
    gc_state(world, config_invalid=True)
    with pytest.raises(activate.Refusal, match="fails gc config validation|gc config show failed"):
        activate.step_city(pkg(world))
    assert activate.sha(world["city"] / "city.toml") == world["pins"]["city_before"]
    assert not (world["package"] / "records/city.intent.json").exists()
    assert not list(world["base"].glob(".city.gct-validate.*"))


def test_city_refuses_when_the_worker_does_not_resolve_to_the_lane(world):
    run_all(world, upto("city"))
    gc_state(world, keep_old_provider=True)
    with pytest.raises(activate.Refusal, match="worker provider"):
        activate.step_city(pkg(world))
    assert activate.sha(world["city"] / "city.toml") == world["pins"]["city_before"]


def test_city_record_carries_the_shadow_proof(world):
    run_all(world, upto("reload"))
    shadow = record(world, "city")["shadow"]
    assert shadow["worker"]["Provider"] == "claude-template-candidate" and shadow["worker"]["MaxActiveSessions"] == 1
    assert shadow["operator"]["OptionDefaults"]["worktree_access"] == "template-worktrees-and-git-metadata"


def test_a_leftover_shadow_blocks_and_rollback_clears_its_exact_shape(world):
    run_all(world, upto("city"))
    shadow = world["base"] / ".city.gct-validate.oak5-crash"
    shadow.mkdir()
    os.symlink(world["city"] / "managed", shadow / "managed")
    (shadow / "city.toml").write_text("x")
    with pytest.raises(activate.Refusal, match="leftover temporaries"):
        activate.step_city(pkg(world))
    activate.rollback(pkg(world))
    assert not shadow.exists()
    assert json.loads((world["package"] / "records/rollback.json").read_text())["cleared_own_leftovers"] == [str(shadow)]


# ---------------------------------------------------------------- resume and rollback

def test_resume_city_after_the_write(world):
    run_all(world, upto("city"))
    p = pkg(world)
    p.intent("city", p.quiet())
    activate.backup(p, p.live.city_toml, "city.toml")
    activate.replace_atomic(p.live.city_toml, p.pinned_input("city.toml"), 0o644, p.live.uid)
    activate.resume(pkg(world), "city")
    assert record(world, "city")["resumed"] is True
    activate.step_reload(pkg(world))


def test_resume_refuses_without_an_intent(world):
    run_all(world, upto("city"))
    with pytest.raises(activate.Refusal, match="no interrupted intent"):
        activate.resume(pkg(world), "city")


@pytest.mark.parametrize("stop", ["checkout", "registry", "render", "city", "reload"])
def test_rollback_restores_every_file_and_the_checkout(world, stop):
    run_all(world, activate.STEPS[: activate.STEPS.index(stop) + 1])
    activate.rollback(pkg(world))
    assert activate.sha(world["city"] / "city.toml") == world["pins"]["city_before"]
    assert activate.sha(world["city"] / "managed/rig-permissions.toml") == world["pins"]["fragment_before"]
    assert activate.sha(world["city"] / "managed/rig-permissions.json") == world["pins"]["registry_before"]
    assert head(world["template"]) == world["before"]
    assert Path(world["pins"]["candidate_root"]).is_dir()
    with pytest.raises(activate.Refusal, match="rollback consumed"):
        activate.step_host(pkg(world))


def test_rollback_refuses_a_foreign_city_toml(world):
    run_all(world)
    (world["city"] / "city.toml").write_text(CITY_TOML + "\n# foreign\n")
    with pytest.raises(activate.Refusal, match="neither its predecessor nor its reviewed postimage"):
        activate.rollback(pkg(world))
    assert head(world["template"]) == world["after"]


# ---------------------------------------------------------------- live bindings (read-only)

def test_live_pins_are_this_package():
    pins = json.loads((HERE / "pins.json").read_text())
    assert pins["executor"] == activate.executor_digests()
    assert pins["template_commit"] == MERGE and pins["template_tree"] == "55d7a9df30ef012e4ccc17170a5fca8a4d8f87f9"
    assert pins["candidate_root"] == "/home/loucmane/gas-city-template-candidate-worktrees"
    assert pins["inputs"]["city.toml"] == "b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b"


def test_helpers_are_the_reviewed_ga_6utp_bytes():
    old = HERE.parent / "ga-6utp-activation-r10"
    for name in ("preroute.py", "candidate_git.py"):
        assert activate.sha(HERE / name) == activate.sha(old / name)
