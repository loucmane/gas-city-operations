"""Tests for activate.py against a fixture city, Template repo, fake gc and fake renderer.

The fakes follow Core 728178bf's actual interfaces:
- `gc status --json` (cmd_citystatus.go), with partial/partial_errors.
- `gc reload --json` (lifecycleActionJSON: ok, outcome, revision, async, soft).
- `gc agent list --json` (AgentListJSON {schema_version, agents:[AgentListItem]}). It composes the
  managed fragment's patch, and always emits pool, because Core's default pool check is non-empty.

The renderer fake honours --check/--apply/--registry/--output/--city. It uses the real
candidate-provider.toml from the gct-lagl Template tree and emits the real report keys. As in the
real Template, the candidate-lane files are absent at the base commit.
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
PYTHON = {"name": "python", "executable": {"path": "/usr/bin/python3.12"}}
REAL_PROVIDER = Path("/home/loucmane/gas-city-template-worktrees/gct-lagl-ops-signing-lane/templates/claude/"
                     "candidate-provider.toml")
NEW_AT_TARGET = ("bin/gct-claude-candidate-worker", "lib/gct_claude_candidate_worker.py",
                 "templates/claude/candidate-provider.toml")
EXISTING_FRAGMENT = (
    '[providers.claude-signing]\nbase = "provider:claude"\n\n'
    '[[patches.agent]]\ndir = "gascity"\nname = "implementation-worker"\nprovider = "claude-signing"\n'
)

FAKE_GC = r'''#!/usr/bin/env python3
import json, os, sys, tomllib
city = sys.argv[2]
args = sys.argv[3:]
state = json.loads(open(os.environ["FAKE_GC_STATE"]).read())
if args[:2] == ["status", "--json"]:
    print(json.dumps({"partial": state.get("partial", False), "controller": {"running": True, "pid": state["pid"]},
                      "agents": [{"name": "implementation-worker", "running": state.get("running", False)}],
                      "summary": {"active_sessions": 0},
                      "rigs": [{"name": "gascity", "suspended": state.get("suspended", True)}]}))
elif args[:2] == ["reload", "--json"]:
    if "reload_pid" in state:
        state["pid"] = state.pop("reload_pid")
        open(os.environ["FAKE_GC_STATE"], "w").write(json.dumps(state))
    print(json.dumps({"schema_version": "1", "ok": True, "command": "reload", "action": "reload", "async": False,
                      "soft": False, "outcome": state.get("outcome", "applied"), "revision": "rev-2"}))
elif args[:3] == ["agent", "list", "--json"] or args[:2] == ["config", "show"]:
    # Like the deployed Core: a PackV1 [[agent]] table in city.toml fails every config load.
    cfg = tomllib.loads(open(os.path.join(city, "city.toml")).read())
    if cfg.get("agent") or state.get("config_invalid"):
        sys.stderr.write("PackV1 config surfaces are no longer supported: unsupported PackV1 [[agent]] tables\n")
        sys.exit(1)
    agents = []
    agents_dir = os.path.join(city, "agents")
    for entry in sorted(os.listdir(agents_dir)) if os.path.isdir(agents_dir) else []:
        if entry.startswith((".", "_")) or not os.path.isdir(os.path.join(agents_dir, entry)):
            continue
        path = os.path.join(agents_dir, entry, "agent.toml")
        a = tomllib.loads(open(path).read()) if os.path.exists(path) else {}
        agents.append(dict(a, name=entry))
    if args[:2] == ["config", "show"]:
        if "--validate" in args:
            sys.exit(0)
        print(json.dumps({"config": {"Agents": [
            {"Name": a["name"], "Dir": a.get("dir", ""), "Scope": a.get("scope", ""),
             "Suspended": a.get("suspended", False), "MaxActiveSessions": a.get("max_active_sessions", 0),
             "Provider": a.get("provider", "")} for a in agents]}}))
        sys.exit(0)
    fragment = tomllib.loads(open(os.path.join(city, "managed/rig-permissions.toml")).read())
    patches = {(p["dir"], p["name"]): p for p in fragment.get("patches", {}).get("agent", [])}
    items = []
    for a in agents:
        if not a.get("dir"):
            continue
        provider = patches.get((a.get("dir"), a["name"]), {}).get("provider", a.get("provider"))
        items.append({"name": a["name"], "qualified_name": a["dir"] + "/" + a["name"], "dir": a["dir"],
                      "provider": provider, "suspended": state.get("agent_suspended", a.get("suspended", False)),
                      "work_query": "",
                      "sling_query": "", "pool": {"min": 0, "max": a.get("max_active_sessions", -1)}})
    print(json.dumps({"schema_version": "1", "city_path": city, "city_name": os.path.basename(city), "agents": items}))
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
provider_text = (root / "templates/claude/candidate-provider.toml").read_text()
text = EXISTING
for record in registry["rigs"]:
    if record.get("provider") != "claude":
        continue
    policy = str(root / record["control_policy"]["source"])
    choice = ("[[providers.claude-candidate.options_schema.choices]]\nvalue = \"managed-x\"\n"
              "label = \"gascity worktrees under the candidate control policy\"\n"
              "flag_args = " + json.dumps(["--settings", policy, "--add-dir", record["worktree_root"]]) + "\n")
    text += "\n" + provider_text.replace("# @managed-rig-choices@", choice)
    text += PATCH.replace("NAME", record["agents"][0]).replace("PATHV", json.dumps(record["environment"]["PATH"]))
new = text.encode()
expected = hashlib.sha256(new).hexdigest()
actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
report = {"state": "drift" if actual else "missing", "expected_sha256": expected, "actual_sha256": actual,
          "registry_file_sha256": hashlib.sha256(raw_registry).hexdigest(),
          "provider_template_sha256s": {"claude-candidate": hashlib.sha256(provider_text.encode()).hexdigest()}}
if "--check" in sys.argv:
    print(json.dumps(report)); sys.exit(4)
target.write_bytes(new)
print(json.dumps(dict(report, state="conformant", actual_sha256=expected)))
'''
PATCH = ("\n[[patches.agent]]\ndir = \"gascity\"\nname = \"NAME\"\nprovider = \"claude-candidate\"\n"
         "[patches.agent.option_defaults]\nmodel = \"opus-5-5\"\npermission_mode = \"full-auto\"\n"
         "managed_worktree_access = \"managed-x\"\n\n[patches.agent.env]\nPATH = PATHV\n")


def renderer_source(patch=PATCH):
    return FAKE_RENDERER.replace("EXISTING", repr(EXISTING_FRAGMENT)).replace("PATCH.replace", repr(patch) + ".replace")


def git(*argv, cwd):
    subprocess.run(["/usr/bin/git", "-c", "user.name=t", "-c", "user.email=t@t", *argv], cwd=cwd, env=ENV,
                   check=True, capture_output=True)


def head(repo):
    return subprocess.run(["/usr/bin/git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                          text=True, env=ENV).stdout.strip()


def profile(candidate_root):
    return {"schema": "gc.managed-rig-permissions.v2", "rigs": [
        {"name": "gascity", "provider": "codex-managed", "agents": ["implementation-worker"], "git_metadata": True},
        {"name": "gascity", "provider": "claude", "agents": ["operations-candidate-worker"], "git_metadata": False,
         "repository_path": "/home/loucmane/gas-city-ops", "worktree_root": candidate_root,
         "control_policy": {"source": "templates/claude/candidate-control-policy.json", "sha256": "0" * 64},
         "environment": {"PATH": "/usr/bin:/bin"}, "toolchains": []}]}


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
    (city / "city.toml").write_text('[workspace]\nprovider = "claude"\n')
    (city / "agents/builder").mkdir(parents=True)
    (city / "agents/builder/agent.toml").write_text('scope = "rig"\nprovider = "codex"\n')
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
    (template / "managed/profiles").mkdir(parents=True)
    (template / "managed/profiles/gascity-operations-candidate-claude.json").write_text(
        json.dumps(profile(str(candidate_root))))
    (template / "bin/gct-managed-rig-permissions").write_text(renderer_source())
    shutil.copyfile(REAL_PROVIDER, template / "templates/claude/candidate-provider.toml")
    git("add", "-A", cwd=template)
    git("commit", "-q", "-m", "merge", cwd=template)
    after = head(template)
    changed = subprocess.run(["/usr/bin/git", "-C", str(template), "diff", "--name-only", before, after],
                             capture_output=True, text=True, env=ENV).stdout.split()
    git("checkout", "-q", "--detach", before, cwd=template)
    ops = base / "ops"
    (ops / ".git").mkdir(parents=True)
    slice_root = base / "slice"
    (slice_root / f"user@{os.getuid()}.service").mkdir(parents=True)
    (slice_root / f"user@{os.getuid()}.service" / "cgroup.procs").write_text("")
    controller_group = slice_root / f"user@{os.getuid()}.service/app.slice/gascity-supervisor.service"
    controller_group.mkdir(parents=True)
    (controller_group / "cgroup.procs").write_text(f"{os.getpid()}\n")  # a real, visible pid
    gc = base / "gc"
    gc.write_text(FAKE_GC)
    gc.chmod(0o755)
    (base / "gc-state.json").write_text(json.dumps({"pid": os.getpid()}))
    prompt = base / "prompt.md"
    prompt.write_text("# candidate prompt\n")
    pins = dict(city=str(city), template=str(template), ops=str(ops), candidate_root=str(candidate_root),
                gc=str(gc), env={"PATH": "/usr/bin:/bin", "FAKE_GC_STATE": str(base / "gc-state.json")},
                managed_settings=str(base / "managed-settings.json"), managed_mcp=str(base / "managed-mcp.json"),
                claude_json=str(base / "claude.json"), sandbox_writable=["/var/tmp", "/dev/shm"],
                user_slice=str(slice_root), template_changed=changed,
                uid=os.getuid(), candidate_path="/usr/bin:/bin", python_toolchain=PYTHON, template_status="",
                registry_before=activate.sha(city / "managed/rig-permissions.json"),
                city_before=activate.sha(city / "city.toml"),
                fragment_before=activate.sha(city / "managed/rig-permissions.toml"),
                template_before=before, template_commit=after, prompt_source=str(prompt),
                renderer_sha=activate.digest(renderer_source().encode()), executor=activate.executor_digests())
    live = activate.Live(pins)
    record = activate.candidate_record(profile(str(candidate_root)), PYTHON)
    registry = activate.new_registry((city / "managed/rig-permissions.json").read_bytes(), record)
    pins["inputs"] = {"rig-permissions.json": activate.digest(registry),
                      activate.AGENT_TOML_NAME: activate.digest(activate.agent_toml()),
                      activate.PROMPT_NAME: activate.digest(prompt.read_bytes())}
    package = base / "package"
    (package / "records").mkdir(parents=True)
    (package / "inputs").mkdir()
    return dict(base=base, city=city, template=template, pins=pins, package=package, after=after, before=before)


def pkg(world):
    return activate.Package(world["package"], activate.Live(world["pins"]), "p" * 64)


def install_agent_dir(p):
    """What an interrupted city step leaves after its rename: the reviewed agent directory."""
    staged = activate.stage_agent_dir(p, p.live.city / "agents", p.pinned_input(activate.AGENT_TOML_NAME),
                                      p.pinned_input(activate.PROMPT_NAME))
    os.rename(staged, p.live.agent_dir)


def run_all(world, upto=activate.STEPS):
    for step in upto:
        activate.ACTIONS[step](pkg(world))


def swap_renderer(world, source):
    """Replace the renderer at the target commit (tests only), keeping the pins consistent."""
    git("checkout", "-q", "--detach", world["after"], cwd=world["template"])
    (world["template"] / "bin/gct-managed-rig-permissions").write_text(source)
    git("commit", "-q", "-am", "swap", cwd=world["template"])
    world["after"] = head(world["template"])
    git("checkout", "-q", "--detach", world["before"], cwd=world["template"])
    world["pins"]["template_commit"] = world["after"]
    world["pins"]["renderer_sha"] = activate.digest(source.encode())


def test_the_full_sequence_reaches_the_reviewed_state(world):
    run_all(world)
    reload = json.loads((world["package"] / "records/reload.json").read_text())
    assert reload["agent"]["provider"] == "claude-candidate" and reload["agent"]["pool"] == {"min": 0, "max": 1}
    assert all((world["package"] / "records" / f"{s}.json").exists() for s in activate.STEPS)
    checkout = json.loads((world["package"] / "records/checkout.json").read_text())
    assert all(checkout["lane_files"][p] for p in activate.LANE_FILES)


def at_target(world):
    """r10: the canonical checkout already sits at the target, so base and target pins are equal."""
    git("checkout", "-q", "--detach", world["after"], cwd=world["template"])
    world["pins"]["template_before"] = world["after"]
    world["pins"]["template_changed"] = []


def test_r10_checkout_at_the_target_proves_without_moving(world, monkeypatch):
    at_target(world)
    calls = []
    real = activate.git
    monkeypatch.setattr(activate, "git", lambda repo, *args, **kw: calls.append(args) or real(repo, *args, **kw))
    run_all(world)
    assert not [a for a in calls if a and a[0] == "checkout"]
    checkout = json.loads((world["package"] / "records/checkout.json").read_text())
    assert checkout["before_commit"] == checkout["after_commit"] == world["after"]
    assert all(checkout["lane_files"][p] for p in activate.LANE_FILES)
    assert head(world["template"]) == world["after"]


def test_r10_rollback_at_the_target_restores_files_without_a_checkout(world, monkeypatch):
    at_target(world)
    run_all(world)
    calls = []
    real = activate.git
    monkeypatch.setattr(activate, "git", lambda repo, *args, **kw: calls.append(args) or real(repo, *args, **kw))
    activate.rollback(pkg(world))
    assert not [a for a in calls if a and a[0] == "checkout"]
    assert head(world["template"]) == world["after"]
    assert activate.sha(world["pins"]["city"] and pkg(world).live.city_toml) == world["pins"]["city_before"]


def test_r10_checkout_at_the_target_refuses_a_lane_file_drift(world):
    at_target(world)
    lane = world["template"] / "bin/gct-claude-candidate-worker"
    lane.write_bytes(lane.read_bytes() + b"\n# drift\n")
    world["pins"]["template_status"] = activate.checkout_state(pkg(world))[1]
    with pytest.raises(activate.Refusal, match="lane file differs"):
        run_all(world, ("host", "inputs", "root", "checkout"))


def test_every_record_carries_the_binding(world):
    run_all(world, ("host",))
    assert json.loads((world["package"] / "records/host.json").read_text())["binding"]["pins_sha256"] == "p" * 64
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


def test_a_controller_change_during_a_step_refuses(world):
    p = pkg(world)
    before = p.quiet()
    gc_state(world, pid=8)
    with pytest.raises(activate.Refusal, match="city changed"):
        p.finish("host", before, {})


def test_host_records_hidden_by_design_processes_and_refuses_others(world):
    user = f"user@{os.getuid()}.service"
    slice_root = Path(world["pins"]["user_slice"])
    (slice_root / user / "init.scope").mkdir()
    (slice_root / user / "init.scope" / "cgroup.procs").write_text("999999999\n")
    run_all(world, ("host",))
    host = json.loads((world["package"] / "records/host.json").read_text())
    assert host["process_record"]["hidden"] == {f"{user}/init.scope": [999999999]}
    raw = (world["package"] / "records/process-record.json").read_bytes()
    assert activate.digest(raw) == host["process_record_sha256"] and json.loads(raw) == host["process_record"]


def test_host_refuses_a_hidden_process_outside_the_reviewed_cgroups(world):
    slice_root = Path(world["pins"]["user_slice"])
    (slice_root / "session-1.scope").mkdir()
    (slice_root / "session-1.scope" / "cgroup.procs").write_text("999999998\n")
    with pytest.raises(activate.Refusal, match="outside the reviewed cgroups"):
        activate.step_host(pkg(world))


def test_checkout_refuses_a_dirty_canonical_checkout(world):
    run_all(world, ("host", "inputs", "root"))
    (world["template"] / "stray.txt").write_text("x")
    with pytest.raises(activate.Refusal, match="not clean"):
        activate.step_checkout(pkg(world))


def test_checkout_refuses_a_lane_file_present_on_disk_but_absent_at_the_base(world):
    run_all(world, ("host", "inputs", "root"))
    world["pins"]["template_status"] = "?? bin/gct-claude-candidate-worker\n"
    (world["template"] / "bin/gct-claude-candidate-worker").write_text("planted\n")
    with pytest.raises(activate.Refusal, match="present on disk but absent"):
        activate.step_checkout(pkg(world))


def test_checkout_refuses_a_different_change_set(world):
    run_all(world, ("host", "inputs", "root"))
    world["pins"]["template_changed"] = world["pins"]["template_changed"][1:]
    with pytest.raises(activate.Refusal, match="change set"):
        activate.step_checkout(pkg(world))


def test_the_city_step_proves_the_agent_is_suspended(world):
    run_all(world, activate.STEPS[:6])
    city = json.loads((world["package"] / "records/city.json").read_text())
    assert city["composed"]["suspended"] is True and city["composed"]["provider"] == "claude"


def test_a_render_that_changes_an_existing_section_refuses_before_any_live_write(world):
    swap_renderer(world, renderer_source().replace("claude-signing", "claude-x"))
    run_all(world, activate.STEPS[:6])
    before = activate.sha(world["city"] / "managed/rig-permissions.toml")
    with pytest.raises(activate.Refusal, match="an existing agent patch changed"):
        activate.step_render(pkg(world))
    assert activate.sha(world["city"] / "managed/rig-permissions.toml") == before
    assert not (world["package"] / "records/render.intent.json").exists()


def test_duplicate_candidate_patches_refuse_before_any_live_write(world):
    swap_renderer(world, renderer_source(PATCH + PATCH.replace("\n[patches.agent.env]\nPATH = PATHV\n", "")))
    run_all(world, activate.STEPS[:6])
    with pytest.raises(activate.Refusal, match="duplicate agent patches"):
        activate.step_render(pkg(world))


def test_a_render_with_a_wrong_candidate_env_refuses(world):
    swap_renderer(world, renderer_source(PATCH.replace("PATH = PATHV", 'PATH = "/tmp"')))
    run_all(world, activate.STEPS[:6])
    with pytest.raises(activate.Refusal, match="candidate patch env"):
        activate.step_render(pkg(world))


def test_a_render_that_dies_after_apply_resumes_or_rolls_back(world):
    run_all(world, activate.STEPS[:6])
    p = pkg(world)
    renderer = str(world["template"] / "bin/gct-managed-rig-permissions")
    scratch = activate.prerender(p, ["/usr/bin/python3.12", "-I", "-B", renderer])
    expected = activate.digest(scratch)
    activate.backup(p, p.live.fragment, "rig-permissions.toml")  # the step backs up before its intent
    p.intent("render", dict(p.quiet(), expected_fragment_sha256=expected))
    (world["city"] / "managed/rig-permissions.toml").write_bytes(scratch)  # the apply landed, then the step died
    activate.rollback(pkg(world))
    assert activate.sha(world["city"] / "managed/rig-permissions.toml") == world["pins"]["fragment_before"]
    assert activate.sha(world["city"] / "city.toml") == world["pins"]["city_before"]


def died_after_apply(world):
    p = pkg(world)
    renderer = str(world["template"] / "bin/gct-managed-rig-permissions")
    scratch = activate.prerender(p, ["/usr/bin/python3.12", "-I", "-B", renderer])
    activate.backup(p, p.live.fragment, "rig-permissions.toml")
    p.intent("render", dict(p.quiet(), expected_fragment_sha256=activate.digest(scratch)))
    (world["city"] / "managed/rig-permissions.toml").write_bytes(scratch)


@pytest.mark.parametrize("then", ["reload", "rollback"])
def test_resume_render_then_reload_or_rollback(world, then):
    run_all(world, activate.STEPS[:6])
    died_after_apply(world)
    activate.resume(pkg(world), "render")
    record = json.loads((world["package"] / "records/render.json").read_text())
    assert record["fragment_sha256"] and record["structure"]["choice"] == "managed-x"
    if then == "reload":
        activate.step_reload(pkg(world))
        assert (world["package"] / "records/reload.json").exists()
    else:
        activate.rollback(pkg(world))
        assert activate.sha(world["city"] / "managed/rig-permissions.toml") == world["pins"]["fragment_before"]


def test_resume_city_proves_the_suspended_composition(world):
    """The agent directory is the reviewed postimage, but Core composes the agent unsuspended."""
    run_all(world, activate.STEPS[:5])
    p = pkg(world)
    p.intent("city", p.quiet())
    install_agent_dir(p)
    gc_state(world, agent_suspended=False)
    with pytest.raises(activate.Refusal, match="not suspended"):
        activate.resume(pkg(world), "city")


def test_a_changed_non_agent_patch_table_refuses():
    p = type("P", (), {})()
    old = EXISTING_FRAGMENT + '\n[[patches.rig]]\nname = "gascity"\nsuspended = true\n'
    new = EXISTING_FRAGMENT.replace("", "", 1) + '\n[[patches.rig]]\nname = "gascity"\nsuspended = false\n' + \
        '\n[[patches.agent]]\ndir = "gascity"\nname = "operations-candidate-worker"\n'
    with pytest.raises(activate.Refusal, match="patch table rig changed"):
        activate.fragment_structure(p, old.encode(), new.encode())


def test_render_refuses_a_registry_that_is_not_the_reviewed_postimage(world):
    run_all(world, activate.STEPS[:6])
    registry = world["city"] / "managed/rig-permissions.json"
    activate.replace_atomic(registry, registry.read_bytes() + b"\n", 0o644, os.getuid())
    with pytest.raises(activate.Refusal, match="registry is not the reviewed postimage"):
        activate.step_render(pkg(world))


@pytest.mark.parametrize("problem", ["mode", "bytes", "filter", "local-attributes"])
def test_checkout_lane_and_attribute_proofs(world, problem):
    run_all(world, ("host", "inputs", "root"))
    template = world["template"]
    if problem == "mode":
        (template / "bin/gct-managed-rig-permissions").chmod(0o755)
        world["pins"]["template_status"] = " M bin/gct-managed-rig-permissions\n"
    elif problem == "bytes":
        (template / "bin/gct-claude-signing-worker").write_text("# tampered\n")
        world["pins"]["template_status"] = " M bin/gct-claude-signing-worker\n"
    elif problem == "filter":
        git("checkout", "-q", "--detach", world["after"], cwd=template)
        (template / ".gitattributes").write_text("* filter=lfs\n")
        git("add", "-A", cwd=template)
        git("commit", "-q", "-m", "attrs", cwd=template)
        world["after"] = head(template)
        world["pins"]["template_commit"] = world["after"]
        world["pins"]["template_changed"] = sorted(world["pins"]["template_changed"] + [".gitattributes"])
        git("checkout", "-q", "--detach", world["before"], cwd=template)
    else:
        (template / ".git" / "info").mkdir(exist_ok=True)
        (template / ".git" / "info" / "attributes").write_text("* filter=lfs\n")
    reasons = {"mode": "mode differs", "bytes": "differs from", "filter": "filter attribute",
               "local-attributes": "repository-local attributes"}
    with pytest.raises(activate.Refusal, match=reasons[problem]):
        activate.step_checkout(pkg(world))


@pytest.mark.parametrize("outcome, ok", [("no_change", True), ("accepted", False)])
def test_reload_outcomes(world, outcome, ok):
    run_all(world, activate.STEPS[:7])
    gc_state(world, outcome=outcome)
    if ok:
        activate.step_reload(pkg(world))
    else:
        with pytest.raises(activate.Refusal, match="reload acknowledgement"):
            activate.step_reload(pkg(world))


def test_reload_refuses_a_foreign_fragment(world):
    run_all(world, activate.STEPS[:7])
    fragment = world["city"] / "managed/rig-permissions.toml"
    fragment.write_text(fragment.read_text() + "\n# foreign\n")
    with pytest.raises(activate.Refusal, match="not the recorded render"):
        activate.step_reload(pkg(world))


def test_agent_proof_refuses_an_uncapped_agent(world):
    run_all(world, activate.STEPS[:7])
    agent = world["city"] / "agents" / activate.AGENT / "agent.toml"
    agent.write_text(agent.read_text().replace("max_active_sessions = 1", "max_active_sessions = 2"))
    with pytest.raises(activate.Refusal, match="cap"):
        activate.agent_proof(pkg(world))


def test_steps_refuse_out_of_order_and_replay(world):
    with pytest.raises(activate.Refusal, match="earlier step missing"):
        activate.step_registry(pkg(world))
    run_all(world, ("host", "inputs"))
    with pytest.raises(activate.Refusal, match="already consumed"):
        activate.step_inputs(pkg(world))


def test_an_interrupted_step_can_only_resume(world):
    run_all(world, ("host", "inputs", "root", "checkout"))
    p = pkg(world)
    p.intent("registry", p.quiet())
    with pytest.raises(activate.Refusal, match="use resume"):
        activate.step_registry(pkg(world))
    with pytest.raises(activate.Refusal, match="postcondition does not hold"):
        activate.resume(pkg(world), "registry")


def test_r11_root_adopts_only_an_empty_operator_directory(world):
    root = Path(world["pins"]["candidate_root"])
    root.mkdir(mode=0o755)
    os.chmod(root, 0o755)
    run_all(world, ("host", "inputs", "root"))
    assert json.loads((world["package"] / "records/root.json").read_text())["adopted_existing"] is True


@pytest.mark.parametrize("problem", ["file", "mode"])
def test_r11_root_refuses_a_foreign_existing_root(world, problem):
    root = Path(world["pins"]["candidate_root"])
    root.mkdir(mode=0o755)
    os.chmod(root, 0o755)
    if problem == "file":
        (root / "x").write_text("x")
    else:
        os.chmod(root, 0o700)
    run_all(world, ("host", "inputs"))
    with pytest.raises(activate.Refusal, match="not an empty operator directory"):
        activate.step_root(pkg(world))


def test_resume_root_checks_mode_owner_and_emptiness(world):
    run_all(world, ("host", "inputs"))
    p = pkg(world)
    p.intent("root", p.quiet())
    root = Path(world["pins"]["candidate_root"])
    root.mkdir(mode=0o755)
    (root / "planted").mkdir()
    with pytest.raises(activate.Refusal, match="postcondition does not hold"):
        activate.resume(pkg(world), "root")


def test_the_agent_is_gascity_bound_suspended_and_capped():
    import tomllib
    parsed = tomllib.loads(activate.agent_toml().decode())
    assert parsed["dir"] == "gascity" and parsed["scope"] == "city" and parsed["suspended"] is True
    assert parsed["max_active_sessions"] == 1 and "session" not in parsed and "prompt_template" not in parsed


def test_r11_the_city_step_never_writes_city_toml_and_installs_the_agent_directory(world):
    before = activate.sha(world["city"] / "city.toml")
    run_all(world, activate.STEPS[:6])
    p = pkg(world)
    assert activate.sha(p.live.city_toml) == before
    assert activate.agent_dir_state(p) == activate.expected_agent_state(p)
    assert not [e for e in os.listdir(world["city"] / "agents") if e.startswith(".")]
    assert not list(world["base"].glob(".city.gct-validate.*"))


def test_r11_a_city_config_gc_rejects_refuses_before_any_live_write(world):
    run_all(world, activate.STEPS[:5])
    gc_state(world, config_invalid=True)
    with pytest.raises(activate.Refusal, match="fails gc config validation"):
        activate.step_city(pkg(world))
    p = pkg(world)
    assert activate.agent_dir_state(p) is None and not p.record("city", ".intent").exists()
    assert not [e for e in os.listdir(world["city"] / "agents") if e.startswith(".")]
    assert not list(world["base"].glob(".city.gct-validate.*"))


def test_r11_a_packv1_agent_table_is_what_the_fake_core_rejects(world):
    """The r10 failure, reproduced: a city.toml [[agent]] table fails every config load."""
    city_toml = world["city"] / "city.toml"
    city_toml.write_text(city_toml.read_text() + '\n[[agent]]\nname = "x"\n')
    with pytest.raises(activate.Refusal, match="gc agent list failed"):
        activate.listed_agents(pkg(world))


def test_r11_the_staged_directory_is_invisible_and_a_leftover_blocks_the_next_step(world):
    run_all(world, activate.STEPS[:5])
    p = pkg(world)
    staged = activate.stage_agent_dir(p, p.live.city / "agents", b"x", b"y")
    assert staged.name.startswith(".") and not [a for a in activate.listed_agents(p)]
    with pytest.raises(activate.Refusal, match="leftover temporaries"):
        activate.step_city(pkg(world))


def test_only_the_candidate_record_is_merged_and_existing_bytes_are_kept():
    record = activate.candidate_record(profile("/r"), PYTHON)
    live = (json.dumps({"schema": "gc.managed-rig-permissions.v2", "rigs": [{"z": 1, "agents": ["implementation-worker"]}]},
                       indent=2) + "\n").encode()
    merged = activate.new_registry(live, record)
    assert merged.startswith(live[: live.index(b"}\n  ]")])


@pytest.mark.parametrize("problem", ["managed-settings", "managed-mcp", "mcp-approved", "ops-mcp", "writable-path",
                                     "tmp-path"])
def test_host_facts_refuse(world, problem):
    if problem == "managed-settings":
        Path(world["pins"]["managed_settings"]).write_text("{}")
    elif problem == "managed-mcp":
        Path(world["pins"]["managed_mcp"]).write_text("{}")
    elif problem == "mcp-approved":
        Path(world["pins"]["claude_json"]).write_text(json.dumps({"projects": {
            world["pins"]["candidate_root"] + "/ga-x": {"enableAllProjectMcpServers": True}}}))
    elif problem == "ops-mcp":
        Path(world["pins"]["claude_json"]).write_text(json.dumps({"projects": {
            world["pins"]["ops"]: {"mcpServers": {"x": {}}}}}))
    elif problem == "writable-path":
        open_dir = world["base"] / "open"
        open_dir.mkdir()
        open_dir.chmod(0o777)
        world["pins"]["sandbox_writable"] = []
        world["pins"]["candidate_path"] = str(open_dir)
    else:
        world["pins"]["sandbox_writable"] = [str(world["base"])]
        world["pins"]["candidate_path"] = str(world["base"])
    reason = {"managed-settings": "managed-policy settings present", "managed-mcp": "managed MCP configuration present",
              "mcp-approved": "project MCP servers approved", "ops-mcp": "Operations project entry approves",
              "writable-path": "group/world-writable", "tmp-path": "inside a sandbox-writable path"}[problem]
    with pytest.raises(activate.Refusal, match=reason):
        activate.step_host(pkg(world))


def test_a_drifted_input_refuses_before_any_write(world):
    run_all(world, ("host",))
    world["pins"]["inputs"][activate.AGENT_TOML_NAME] = "0" * 64
    with pytest.raises(activate.Refusal, match="differs from the reviewed pin"):
        activate.step_inputs(pkg(world))
    assert not (world["package"] / "inputs" / activate.AGENT_TOML_NAME).exists()


def test_rollback_restores_every_live_file_the_checkout_and_reloads(world):
    run_all(world)
    activate.rollback(pkg(world))
    city = world["city"]
    assert activate.sha(city / "city.toml") == world["pins"]["city_before"]
    assert activate.sha(city / "managed/rig-permissions.json") == world["pins"]["registry_before"]
    assert activate.sha(city / "managed/rig-permissions.toml") == world["pins"]["fragment_before"]
    assert head(world["template"]) == world["before"] and not (city / "agents" / activate.AGENT).exists()
    assert [e for e in os.listdir(city / "agents") if e.startswith(".")] == [
        "." + activate.AGENT + ".rolled-back.gct-lagl.0"]
    assert json.loads((world["package"] / "records/rollback.json").read_text())["reload"]["outcome"] == "applied"


def test_rollback_after_an_interrupted_city_step(world):
    run_all(world, activate.STEPS[:5])
    p = pkg(world)
    p.intent("city", p.quiet())
    install_agent_dir(p)
    activate.rollback(pkg(world))
    assert not p.live.agent_dir.exists() and activate.sha(p.live.city_toml) == world["pins"]["city_before"]


def test_rollback_refuses_a_foreign_change_and_an_empty_package(world):
    with pytest.raises(activate.Refusal, match="nothing recorded"):
        activate.rollback(pkg(world))
    run_all(world)
    (world["city"] / "managed/rig-permissions.json").write_text("# foreign\n")
    with pytest.raises(activate.Refusal, match="neither its predecessor"):
        activate.rollback(pkg(world))


def test_r11_rollback_refuses_a_foreign_city_toml_or_agent_directory(world):
    run_all(world)
    agent = world["city"] / "agents" / activate.AGENT / "agent.toml"
    original = agent.read_bytes()
    agent.write_bytes(original + b"# foreign\n")
    with pytest.raises(activate.Refusal, match="agent directory is not the reviewed postimage"):
        activate.rollback(pkg(world))
    agent.write_bytes(original)
    (world["city"] / "city.toml").write_text("# foreign\n")
    with pytest.raises(activate.Refusal, match="city.toml is not its predecessor"):
        activate.rollback(pkg(world))


def test_rollback_refuses_a_failed_reload(world):
    run_all(world)
    gc_state(world, outcome="accepted")
    with pytest.raises(activate.Refusal, match="reload acknowledgement"):
        activate.rollback(pkg(world))


def test_rollback_refuses_over_an_interrupted_checkout(world):
    """HEAD still at the base, but the tree is partly at the target: an explicit stop, never a success."""
    run_all(world, ("host", "inputs", "root"))
    p = pkg(world)
    p.intent("checkout", p.quiet())
    (world["template"] / "bin/gct-claude-signing-worker").write_text("# after bin/gct-claude-signing-worker\n")
    before = {n: activate.sha(world["city"] / n) for n in ("city.toml", "managed/rig-permissions.json",
                                                            "managed/rig-permissions.toml")}
    with pytest.raises(activate.Refusal, match="neither the clean predecessor nor the reviewed target"):
        activate.rollback(pkg(world))
    assert not (world["package"] / "records/rollback.json").exists()
    assert {n: activate.sha(world["city"] / n) for n in before} == before


def test_host_refuses_a_controller_outside_the_user_slice(world, monkeypatch):
    monkeypatch.setattr(preroute, "process_facts", lambda pid: dict(comm="gc", exe="/x/gc", start=1, ppid=1, seccomp=0,
                                                                    nnp=0, argv=["gc", "supervisor", "run"], ns={},
                                                                    cgroup="/init.scope"))
    with pytest.raises(activate.Refusal, match="outside the user slice"):
        activate.step_host(pkg(world))


def test_host_records_the_controller(world):
    activate.step_host(pkg(world))
    host = json.loads((world["package"] / "records/host.json").read_text())
    assert host["process_record"]["controller"] == dict(
        pid=os.getpid(), exe="/x/gc", start=1, cgroup=f"user@{os.getuid()}.service/app.slice/gascity-supervisor.service")
    assert host["process_record"]["controller_members"] == [dict(pid=os.getpid(), role="controller", exe="/x/gc", start=1)]
    assert host["process_record"]["tmux_socket"] == str(Path(world["base"]) / f"tmux-{os.getuid()}" / "city")


@pytest.mark.parametrize("name", ["TMUX_TMPDIR", "GC_AGENT_SLICE", "GC_SESSION"])
def test_host_refuses_a_controller_environment_that_moves_panes(world, monkeypatch, name):
    monkeypatch.setattr(preroute, "process_environ", lambda pid: {name: "x"})
    with pytest.raises(activate.Refusal, match="moves the tmux socket or panes"):
        activate.step_host(pkg(world))


@pytest.mark.parametrize("line, reason", [('[session]\nsocket = "x"\n', "overrides the tmux socket"),
                                          ('[session]\nprovider = "acp"\n', "non-tmux session backend")])
def test_host_refuses_socket_and_backend_overrides(world, line, reason):
    city_toml = world["city"] / "city.toml"
    city_toml.write_text(city_toml.read_text() + "\n" + line)
    world["pins"]["city_before"] = activate.sha(city_toml)
    with pytest.raises(activate.Refusal, match=reason):
        activate.step_host(pkg(world))


def test_host_refuses_a_city_name_gc_disagrees_with(world):
    city_toml = world["city"] / "city.toml"
    city_toml.write_text(city_toml.read_text().replace("[workspace]\n", '[workspace]\nname = "other"\n'))
    world["pins"]["city_before"] = activate.sha(city_toml)
    with pytest.raises(activate.Refusal, match="disagree on the city name"):
        activate.step_host(pkg(world))


def test_host_refuses_a_non_tmux_session_backend(world):
    city_toml = world["city"] / "city.toml"
    city_toml.write_text(city_toml.read_text() + '\n[session]\nprovider = "subprocess"\n')
    world["pins"]["city_before"] = activate.sha(city_toml)
    with pytest.raises(activate.Refusal, match="non-tmux session backend"):
        activate.step_host(pkg(world))


def test_host_refuses_a_running_city_tmux_server(world):
    import socket
    directory = Path(world["base"]) / f"tmux-{os.getuid()}"
    directory.mkdir()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(directory / "city"))
    server.listen(16)
    try:
        with pytest.raises(activate.Refusal, match="a city tmux server is running"):
            activate.step_host(pkg(world))
    finally:
        server.close()


def test_the_committed_pins_bind_the_committed_executors():
    pins = json.loads((Path(__file__).resolve().parent / "pins.json").read_text())
    assert pins["executor"] == activate.executor_digests()


def test_executor_files_must_be_the_reviewed_bytes(world):
    world["pins"]["executor"] = dict(world["pins"]["executor"], **{"preroute.py": "0" * 64})
    with pytest.raises(activate.Refusal, match="executor files are not the reviewed bytes"):
        pkg(world)


def test_rollback_validates_every_file_before_writing(world):
    run_all(world)
    (world["city"] / "managed/rig-permissions.json").write_text("{}\n")  # foreign registry, valid fragment
    fragment = activate.sha(world["city"] / "managed/rig-permissions.toml")
    with pytest.raises(activate.Refusal, match="rig-permissions.json is neither"):
        activate.rollback(pkg(world))
    assert activate.sha(world["city"] / "managed/rig-permissions.toml") == fragment


def test_render_reproves_the_lane_files(world):
    run_all(world, activate.STEPS[:6])
    (world["template"] / "lib").mkdir(exist_ok=True)
    lane = next(path for path in activate.LANE_FILES if path.startswith("lib/"))
    (world["template"] / lane).write_text("# drifted\n")
    with pytest.raises(activate.Refusal, match="checkout drifted"):
        activate.step_render(pkg(world))
    assert activate.sha(world["city"] / "managed/rig-permissions.toml") == world["pins"]["fragment_before"]


def test_rollback_refuses_a_city_that_changed_across_its_reload(world):
    run_all(world)
    gc_state(world, reload_pid=424242)
    with pytest.raises(activate.Refusal, match="the city changed during rollback"):
        activate.rollback(pkg(world))
    assert not (world["package"] / "records/rollback.json").exists()


def test_rollback_refuses_a_city_that_is_not_quiet(world):
    run_all(world)
    gc_state(world, running=True)
    with pytest.raises(activate.Refusal, match="an agent is running"):
        activate.rollback(pkg(world))
    assert not (world["package"] / "records/rollback.json").exists()


def test_rollback_refuses_renderer_leftovers(world):
    run_all(world)
    (world["city"] / "managed" / ".rig-permissions.toml.tmp.1").write_text("x")
    with pytest.raises(activate.Refusal, match="leftover temporaries"):
        activate.rollback(pkg(world))


def test_resume_render_refuses_a_backup_that_is_not_the_pin(world):
    run_all(world, activate.STEPS[:6])
    died_after_apply(world)
    backup = world["package"] / "backups/rig-permissions.toml"
    backup.chmod(0o644)
    backup.write_bytes(backup.read_bytes() + b"# drift\n")
    with pytest.raises(activate.Refusal, match="differs from its pin"):
        activate.resume(pkg(world), "render")
