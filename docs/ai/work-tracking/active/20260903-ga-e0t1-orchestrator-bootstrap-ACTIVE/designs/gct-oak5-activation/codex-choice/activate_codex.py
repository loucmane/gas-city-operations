"""Add the Template-candidate codex worklog choice (gct-oak5 handover), one guarded step per invocation.

  python3 -I -B activate_codex.py <package-dir> <pins-sha256> inputs|city|reload
  python3 -I -B activate_codex.py <package-dir> <pins-sha256> resume city|reload
  python3 -I -B activate_codex.py <package-dir> <pins-sha256> rollback

Operator decision 2026-09-27 ("New codex choice"): the gct-oak5 handover runs C1 (Claude), X (Template codex) and
C2 (Claude) in ONE worktree. The Claude candidate lane edits only under the Template candidate root, and the
Template codex lane writes only under the Template worktrees root. This package makes exactly two city.toml edits
so that a window can give the codex segment that one worktree:
1. one new `providers.codex` worklog_access choice, `classified-vault-and-template-candidate-worktrees`, whose
   sandbox write roots are exactly the GasCity vault and the Template candidate root (no Git metadata). It is
   inserted directly after `classified-vault-and-template-worktrees`, the choice the gct-mbg6 window used;
2. the Template codex agent's `work_dir_roots` gains the candidate root after its existing Template worktrees root,
   so the ga-6umo work_dir guard admits a task worktree there.
The codex default (`classified-vault-template-worktrees-and-git-metadata`), every other choice, provider, agent,
patch and rig are unchanged and asserted at the TOML level. The window, not this package, selects the new choice.

The step discipline is the reviewed gct-oak5 activation executor's (activate.py, whose helpers this file imports
by reviewed digest): every step proves a quiet city (no running agent or session, every rig suspended) before and
after, writes an intent before its one change, and records one exclusive result. After an intent only `resume` is
accepted; `resume reload` re-issues the idempotent reload. `rollback` restores city.toml from its digest-verified
backup only when it is exactly the reviewed postimage, reloads, and proves the codex agent is back on its
predecessor work_dir_roots.
- inputs: derives the city.toml postimage from the live predecessor and pins it.
- city: a throwaway shadow city (every entry symlinked except a copied postimage city.toml) must pass
  `gc config show --validate` and compose the codex agent as below; then city.toml is replaced atomically.
- reload: the controller reports applied or no_change; `gc config show --json` composes the Template codex agent
  on provider codex, its unchanged default and cap 1, and the two work_dir_roots; the live city.toml parses to the
  new choice with exactly its flag_args.

No worker, route, rig resume, receipt, signer or Bead action. The revision moves: M12 adopts city.toml and P13
re-pins the receipt's permission_revision; no Claude worker may launch between `city` and P13 (the receipt
revision mismatch makes Core's start preflight refuse, fail closed).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import activate  # noqa: E402

Refusal, require, digest, sha, run = activate.Refusal, activate.require, activate.digest, activate.sha, activate.run
write_exclusive, replace_atomic, identity = activate.write_exclusive, activate.replace_atomic, activate.identity

STEPS = ("inputs", "city", "reload")
RIG = "gas-city-template"
AGENT = "codex"
TAG = "gct-oak5-codex"
CITY_NAME = "city.toml"
EXECUTOR = Path(__file__).resolve()
# This executor and the reviewed modules it loads.
EXECUTOR_FILES = {"activate_codex.py": EXECUTOR, "activate.py": EXECUTOR.parent.parent / "activate.py",
                  "preroute.py": EXECUTOR.parent.parent / "preroute.py",
                  "candidate_git.py": EXECUTOR.parent.parent / "candidate_git.py"}
VAULT = "/home/loucmane/vaults/main/GasCity"
TEMPLATE_ROOT = "/home/loucmane/gas-city-template-worktrees"
DEFAULT = "classified-vault-template-worktrees-and-git-metadata"
ANCHOR = "classified-vault-and-template-worktrees"
CHOICE = "classified-vault-and-template-candidate-worktrees"


def choice_block(candidate_root: str) -> str:
    roots = '[\\"%s\\",\\"%s\\"]' % (VAULT, candidate_root)
    return ('[[providers.codex.options_schema.choices]]\n'
            f'value = "{CHOICE}"\n'
            'label = "Classified GasCity vault and Template candidate worktrees"\n'
            f'flag_args = ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.writable_roots={roots}"]\n'
            '\n')


def choice_flags(candidate_root: str) -> list:
    return ["--sandbox", "workspace-write", "-c",
            'sandbox_workspace_write.writable_roots=["%s","%s"]' % (VAULT, candidate_root)]


ANCHOR_BLOCK = (
    '[[providers.codex.options_schema.choices]]\n'
    f'value = "{ANCHOR}"\n'
    'label = "Classified GasCity vault and template worktrees"\n'
    'flag_args = ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.writable_roots=[\\"'
    '/home/loucmane/vaults/main/GasCity\\",\\"/home/loucmane/gas-city-template-worktrees\\"]"]\n'
    '\n'
)
PATCH_BEFORE = (
    'dir = "gas-city-template"\n'
    'name = "codex"\n'
    'work_dir_roots = ["/home/loucmane/gas-city-template-worktrees"]\n'
)


def patch_after(candidate_root: str) -> str:
    return ('dir = "gas-city-template"\n'
            'name = "codex"\n'
            f'work_dir_roots = ["/home/loucmane/gas-city-template-worktrees", "{candidate_root}"]\n')


def codex_choices(cfg: dict) -> list:
    (option,) = [o for o in cfg["providers"]["codex"]["options_schema"] if o["key"] == "worklog_access"]
    return option["choices"]


def root_patches(cfg: dict) -> list:
    return [a for a in cfg["patches"]["agent"]
            if a.get("dir") == RIG and a.get("name") == AGENT and "work_dir_roots" in a]


def new_city(raw: bytes, candidate_root: str) -> bytes:
    """The reviewed city.toml postimage: exactly the two edits, proven again at the TOML level."""
    text = raw.decode()
    require(text.count(ANCHOR_BLOCK) == 1, "the anchor codex choice is not exactly once")
    require(text.count(PATCH_BEFORE) == 1, "the codex work_dir_roots patch is not exactly once")
    require(CHOICE not in text, "the new codex choice already exists")
    new = text.replace(ANCHOR_BLOCK, ANCHOR_BLOCK + choice_block(candidate_root), 1)
    new = new.replace(PATCH_BEFORE, patch_after(candidate_root), 1)
    old_cfg, new_cfg = tomllib.loads(text), tomllib.loads(new)
    old_choices, new_choices = codex_choices(old_cfg), codex_choices(new_cfg)
    index = [c["value"] for c in old_choices].index(ANCHOR) + 1
    added = dict(value=CHOICE, label="Classified GasCity vault and Template candidate worktrees",
                 flag_args=choice_flags(candidate_root))
    require(new_choices == old_choices[:index] + [added] + old_choices[index:], "codex choices beyond the one insert")
    old_codex, new_codex = dict(old_cfg["providers"]["codex"]), dict(new_cfg["providers"]["codex"])
    old_codex["options_schema"] = [o for o in old_codex["options_schema"] if o["key"] != "worklog_access"]
    new_codex["options_schema"] = [o for o in new_codex["options_schema"] if o["key"] != "worklog_access"]
    require(new_codex == old_codex, "the codex provider changed beyond worklog_access")
    (old_option,) = [o for o in old_cfg["providers"]["codex"]["options_schema"] if o["key"] == "worklog_access"]
    (new_option,) = [o for o in new_cfg["providers"]["codex"]["options_schema"] if o["key"] == "worklog_access"]
    require({k: v for k, v in new_option.items() if k != "choices"} == {k: v for k, v in old_option.items() if k != "choices"}
            and new_option["default"] == "classified-vault", "worklog_access option header changed")
    require({k: v for k, v in new_cfg["providers"].items() if k != "codex"}
            == {k: v for k, v in old_cfg["providers"].items() if k != "codex"}, "another provider changed")
    require(root_patches(old_cfg) == [dict(dir=RIG, name=AGENT, work_dir_roots=[TEMPLATE_ROOT])], "predecessor patch")
    require(root_patches(new_cfg) == [dict(dir=RIG, name=AGENT, work_dir_roots=[TEMPLATE_ROOT, candidate_root])],
            "postimage patch")
    others = lambda cfg: [a for a in cfg["patches"]["agent"] if a not in root_patches(cfg)]
    require(others(new_cfg) == others(old_cfg), "another agent patch changed")
    require({k: v for k, v in new_cfg["patches"].items() if k != "agent"}
            == {k: v for k, v in old_cfg["patches"].items() if k != "agent"}, "another patch table changed")
    require({k: v for k, v in new_cfg.items() if k not in ("providers", "patches")}
            == {k: v for k, v in old_cfg.items() if k not in ("providers", "patches")}, "a non-provider table changed")
    return new.encode()


def executor_digests() -> dict:
    return {name: sha(path) for name, path in EXECUTOR_FILES.items()}


class Package:
    def __init__(self, root: Path, pins: dict, pins_sha: str):
        self.root, self.pins = root, pins
        self.records, self.inputs = root / "records", root / "inputs"
        self.city = Path(pins["city"])
        self.city_toml = self.city / CITY_NAME
        self.candidate_root = pins["candidate_root"]
        self.gc, self.env, self.uid = pins["gc"], pins["env"], int(pins["uid"])
        executor = executor_digests()
        require(pins.get("executor") == executor, "executor files are not the reviewed bytes")
        self.binding = dict(pins_sha256=pins_sha, executor_sha256=digest(json.dumps(executor, sort_keys=True).encode()))

    def record(self, step, suffix=""):
        return self.records / f"{step}{suffix}.json"

    def shadows(self):
        return sorted(self.city.parent.glob("." + self.city.name + ".gct-validate.codex-*"))

    def common(self, step):
        require(not os.path.lexists(self.records / "rollback.json"), "rollback consumed; start a new package")
        require(not os.path.lexists(self.record(step)), f"step already consumed: {step}")
        for earlier in STEPS[: STEPS.index(step)]:
            require(os.path.lexists(self.record(earlier)), f"earlier step missing: {earlier}")
            recorded = json.loads(self.record(earlier).read_text())
            require(recorded.get("binding") == self.binding, f"{earlier} was recorded under another binding")

    def begin(self, step):
        self.common(step)
        require(not os.path.lexists(self.record(step, ".intent")), f"interrupted after intent; use resume {step}")
        require(not self.shadows(), f"leftover validation shadows: {self.shadows()}")
        require(not list(self.city.glob(f".city.toml.tmp.{activate.TAG}.*")), "leftover city.toml temporaries")
        return self.quiet()

    def quiet(self):
        status = run([self.gc, "--city", str(self.city), "status", "--json"], self.env, timeout=60)
        require(status["returncode"] == 0, "gc status failed: " + status["stderr"][-300:])
        value = json.loads(status["stdout"])
        require(not value.get("partial") and not value.get("partial_errors"), "partial status observation")
        agents, rigs = value["agents"], value["rigs"]
        require(isinstance(agents, list) and isinstance(rigs, list) and rigs, "status shape")
        require(not [a["name"] for a in agents if a["running"]], "an agent is running")
        require(value["summary"].get("active_sessions", 0) == 0, "a session is active")
        require(all(r["suspended"] is True for r in rigs), "a rig is not suspended")
        pid = value["controller"]["pid"]
        require(isinstance(pid, int) and pid > 0, "controller pid")
        return dict(controller=pid, rigs=sorted(r["name"] for r in rigs),
                    suspension_sha256=sha(self.city / ".gc/runtime/suspension-state.json"))

    def intent(self, step, before):
        write_exclusive(self.record(step, ".intent"),
                        (json.dumps(dict(step=step, before=before, binding=self.binding), sort_keys=True) + "\n").encode())

    def finish(self, step, before, value, resumed=False):
        after = self.quiet()
        require(after == before, f"city changed during the step: {before} -> {after}")
        body = dict(value, step=step, bead="gct-oak5", resumed=resumed, before=before, after=after, binding=self.binding)
        write_exclusive(self.record(step), (json.dumps(body, sort_keys=True, indent=1) + "\n").encode())
        print(json.dumps(dict(step=step, ok=True, resumed=resumed)))

    def pinned_input(self):
        raw = (self.inputs / CITY_NAME).read_bytes()
        require(digest(raw) == self.pins["inputs"][CITY_NAME], "input digest drift: city.toml")
        return raw


def codex_agent(p: Package, city: Path) -> dict:
    shown = run([p.gc, "--city", str(city), "config", "show", "--json"], p.env, timeout=120)
    require(shown["returncode"] == 0, "gc config show failed: " + shown["stderr"][-300:])
    agents = [a for a in json.loads(shown["stdout"])["config"]["Agents"] if a.get("Dir") == RIG and a.get("Name") == AGENT]
    require(len(agents) == 1, f"Template codex resolves {len(agents)} times")
    return agents[0]


def codex_proof(p: Package, agent: dict, roots: list) -> dict:
    require(agent.get("Provider") == "codex", f"codex provider {agent.get('Provider')!r}")
    require(agent.get("OptionDefaults") == {"worklog_access": DEFAULT}, f"codex default {agent.get('OptionDefaults')}")
    require(agent.get("WorkDirRoots") == roots, f"codex work_dir_roots {agent.get('WorkDirRoots')}")
    require(agent.get("MaxActiveSessions") == 1, f"codex cap {agent.get('MaxActiveSessions')}")
    return {k: agent.get(k) for k in ("Provider", "OptionDefaults", "WorkDirRoots", "MaxActiveSessions", "Suspended")}


def validate_city(p: Package, city_raw: bytes) -> dict:
    """Prove Core loads and composes the city with the postimage city.toml before anything live changes."""
    shadow = Path(tempfile.mkdtemp(prefix="." + p.city.name + ".gct-validate.codex-", dir=p.city.parent))
    try:
        for entry in sorted(os.listdir(p.city)):
            if entry != CITY_NAME:
                os.symlink(p.city / entry, shadow / entry)
        write_exclusive(shadow / CITY_NAME, city_raw, 0o644)
        checked = run([p.gc, "--city", str(shadow), "config", "show", "--validate"], p.env, timeout=120)
        require(checked["returncode"] == 0, "postimage fails gc config validation: " + checked["stderr"][-400:])
        return codex_proof(p, codex_agent(p, shadow), [TEMPLATE_ROOT, p.candidate_root])
    finally:
        for entry in os.listdir(shadow):
            os.unlink(shadow / entry)
        os.rmdir(shadow)


def live_choice(p: Package) -> dict:
    (found,) = [c for c in codex_choices(tomllib.loads(p.city_toml.read_text())) if c["value"] == CHOICE]
    require(found["flag_args"] == choice_flags(p.candidate_root), "live choice flags")
    return found


def reload(p: Package) -> dict:
    """activate.reload's acknowledgement contract: synchronous, not soft, applied or no_change, with a revision."""
    reloaded = run([p.gc, "--city", str(p.city), "reload", "--json"], p.env, timeout=480)
    ack = json.loads(reloaded["stdout"] or "{}")
    require(reloaded["returncode"] == 0 and ack.get("ok") is True and ack.get("async") is False
            and ack.get("soft") is False and ack.get("outcome") in {"applied", "no_change"} and ack.get("revision"),
            f"reload acknowledgement {ack}")
    return ack


def step_inputs(p: Package):
    before = p.begin("inputs")
    require(sha(p.city_toml) == p.pins["city_before"], "city predecessor")
    raw = new_city(p.city_toml.read_bytes(), p.candidate_root)
    require(digest(raw) == p.pins["inputs"][CITY_NAME], "derived city.toml differs from the reviewed pin")
    p.intent("inputs", before)
    write_exclusive(p.inputs / CITY_NAME, raw, 0o644)
    p.finish("inputs", before, dict(inputs={CITY_NAME: digest(raw)}))


def backup(p: Package):
    target = p.root / "backups" / CITY_NAME
    target.parent.mkdir(mode=0o700, exist_ok=True)
    if not target.exists():
        write_exclusive(target, p.city_toml.read_bytes(), 0o600)
    require(sha(target) == sha(p.city_toml) == p.pins["city_before"], "backup of city.toml differs from live")


def step_city(p: Package):
    before = p.begin("city")
    new = p.pinned_input()
    require(identity(p.city_toml) == (stat.S_IFREG, 0o644, p.uid, 1, p.pins["city_before"]), "city.toml predecessor identity")
    proof = validate_city(p, new)
    backup(p)
    p.intent("city", before)
    replace_atomic(p.city_toml, new, 0o644, p.uid)
    p.finish("city", before, dict(city_sha256=digest(new), shadow=proof))


def postimage(p: Package) -> None:
    require(identity(p.city_toml) == (stat.S_IFREG, 0o644, p.uid, 1, p.pins["inputs"][CITY_NAME]),
            "city.toml is not the reviewed postimage")


def step_reload(p: Package):
    before = p.begin("reload")
    postimage(p)
    p.intent("reload", before)
    ack = reload(p)
    p.finish("reload", before, dict(reload=ack, choice=live_choice(p),
                                    composed=codex_proof(p, codex_agent(p, p.city), [TEMPLATE_ROOT, p.candidate_root])))


ACTIONS = {"inputs": step_inputs, "city": step_city, "reload": step_reload}


def resume(p: Package, step: str):
    require(step in ("city", "reload"), "resume needs city or reload")
    p.common(step)
    intent = p.record(step, ".intent")
    require(os.path.lexists(intent), f"no interrupted intent for {step}")
    recorded = json.loads(intent.read_text())
    require(recorded.get("binding") == p.binding, "intent belongs to another binding")
    postimage(p)
    extra = dict(city_sha256=sha(p.city_toml))
    if step == "reload":
        extra.update(reload=reload(p), choice=live_choice(p))
    extra["composed"] = codex_proof(p, codex_agent(p, p.city), [TEMPLATE_ROOT, p.candidate_root]) \
        if step == "reload" else None
    p.finish(step, recorded["before"], dict(extra, resumed_from_intent=True), resumed=True)


def rollback(p: Package):
    """Restore city.toml from its digest-verified backup; refuse on any foreign state."""
    require(os.path.isdir(p.records) and not os.path.lexists(p.records / "rollback.json"), "rollback state")
    require(any(p.records.glob("*.json")), "nothing recorded; there is nothing to roll back")
    observed = p.quiet()
    require(not p.shadows(), f"leftover validation shadows: {p.shadows()}")
    current = sha(p.city_toml)
    actions = []
    if current != p.pins["city_before"]:
        require(current == p.pins["inputs"][CITY_NAME], "city.toml is neither its predecessor nor its postimage; refusing")
        raw = (p.root / "backups" / CITY_NAME).read_bytes()
        require(digest(raw) == p.pins["city_before"], "backup city.toml differs from its pin")
        replace_atomic(p.city_toml, raw, 0o644, p.uid)
        actions.append(CITY_NAME)
    ack = reload(p)
    composed = codex_proof(p, codex_agent(p, p.city), [TEMPLATE_ROOT])
    require(CHOICE not in p.city_toml.read_text(), "the new choice survived rollback")
    after = p.quiet()
    require(after == observed, f"the city changed during rollback: {observed} -> {after}")
    value = dict(actions=actions, quiet=observed, quiet_after=after, reload=ack, composed=composed, binding=p.binding)
    write_exclusive(p.records / "rollback.json", (json.dumps(value, indent=1, sort_keys=True) + "\n").encode())
    print(json.dumps(dict(rollback=actions, ok=True)))


def main(argv):
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            "isolated source-only UID1000 invocation required")
    require(len(argv) in (3, 4) and len(argv[1]) == 64,
            "usage: activate_codex.py <package-dir> <pins-sha256> <step>|resume <step>|rollback")
    root = Path(argv[0])
    pins_raw = (root / "pins.json").read_bytes()
    require(digest(pins_raw) == argv[1], "pins.json is not the reviewed pins")
    package = Package(root, json.loads(pins_raw), argv[1])
    package.records.mkdir(mode=0o700, exist_ok=True)
    package.inputs.mkdir(mode=0o700, exist_ok=True)
    os.umask(0o022)
    if argv[2] == "resume":
        require(len(argv) == 4, "resume needs a step")
        resume(package, argv[3])
    elif argv[2] == "rollback":
        rollback(package)
    else:
        require(argv[2] in ACTIONS, "unknown step")
        ACTIONS[argv[2]](package)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (Refusal, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps(dict(ok=False, stop=f"{type(exc).__name__}: {exc}")))
        raise SystemExit(2)
