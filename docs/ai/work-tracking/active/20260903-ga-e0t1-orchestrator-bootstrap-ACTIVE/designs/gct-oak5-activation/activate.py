"""Activate the Template Claude candidate lane (gct-mbg6, Template PR 72), one guarded step per invocation.

  python3 -I -B activate.py <package-dir> <pins-sha256> host|inputs|root|checkout|registry|render|city|reload
  python3 -I -B activate.py <package-dir> <pins-sha256> resume <step>
  python3 -I -B activate.py <package-dir> <pins-sha256> rollback

This is the ga-6utp r12 executor (Operations candidate lane) adapted to the Template lane named by the merged
docs (docs/managed-worker-provisioning.md "Template candidate lane"). The step discipline is unchanged:
- Every step proves its exact predecessor state and a quiet city (no running agent or session, every rig
  suspended) before it writes an intent. It then makes one bounded change, proves the exact postcondition and
  the same quiet city, and writes one exclusive record under <package-dir>/records.
- After an intent, only `resume` is accepted. `resume` proves the postcondition and never repeats a mutation,
  except `resume reload`: a reload is idempotent, so it is re-issued and must report applied or no_change.
- `rollback` refuses on any live file that is neither its predecessor nor its reviewed postimage, restores every
  changed file from a digest-verified backup through an atomic replace in reverse order, moves the checkout back
  with hooks off, reloads, and proves the Template worker is back on its predecessor composition. It never
  deletes; the candidate root stays.

The steps, in order:
- host: read-only host facts (as ga-6utp): no managed-policy settings or MCP file; no project trust entry that
  approves MCP servers for the candidate root; the Template common directory chain is physical; git writes
  absolute worktree paths; every candidate PATH entry passes on its lexical and resolved chain.
- inputs: derives and pins the registry postimage (the live registry plus the Template profile record) and the
  city.toml postimage (see city).
- root: creates /home/loucmane/gas-city-template-candidate-worktrees, operator-owned, 0755, empty. The renderer
  refuses a record whose worktree_root does not exist, so root precedes render.
- checkout: moves the canonical Template checkout from the reviewed base to the reviewed merge commit
  (detached, hooks, fsmonitor and attributes off) after proving the pinned status, ancestry, the exact reviewed
  change set, filter-free attributes at both commits and every lane file at the base; then proves every lane
  file at the target. The merge commit's objects are fetched beforehand by a refspec-free `git fetch`.
- registry: appends the Template candidate record.
- render: renders into a package-local scratch city first and proves the fragment key by key (exactly one new
  provider, claude-template-candidate, from the reviewed provider template with the one Template grant, and
  exactly one new agent patch, gas-city-template/implementation-worker); the live --check must predict those
  bytes and --apply must produce them.
- city: rewrites city.toml to its reviewed postimage, which (1) removes the Template [[rigs.overrides]] entry
  that forces implementation-worker back to plain claude, auto-edit and template-worktrees-and-git-metadata
  (pack overrides apply after city patches, so a surviving override silently cancels the lane), (2) moves the
  worker's work_dir_roots to the candidate root, the only root the wrapper admits, and (3) caps it at
  max_active_sessions = 1 (the handover decision of 2026-09-24). The run-operator override is unchanged. Before
  anything is written, a throwaway shadow city (every entry symlinked except a copied postimage city.toml) must
  pass `gc config show --validate` and resolve the worker as below.
- reload: the controller reports applied or no_change and a revision; `gc config show --json` and `gc agent list
  --json` must resolve gas-city-template/gc.implementation-worker on claude-template-candidate, full-auto, the
  Template grant, the candidate work_dir_roots and cap 1, and run-operator on its unchanged override.

No worker, route, rig resume, receipt, signer or Bead action. The receipt refresh (the typed Template candidate
profile) is the P12 successor; M11 adopts the changed city files and the Template pin first. Until P12 the
worker receipt pins the old Template commit, so every signing launch refuses on the version mismatch (fails
closed); no worker may launch between checkout and P12.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tempfile
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preroute  # noqa: E402

STEPS = ("host", "inputs", "root", "checkout", "registry", "render", "city", "reload")
RIG = "gas-city-template"
AGENT = "implementation-worker"
QUALIFIED = f"{RIG}/gc.{AGENT}"
PROVIDER = "claude-template-candidate"
PROFILE = "managed/profiles/gas-city-template-candidate-claude.json"
POLICY = "templates/claude/template-candidate-control-policy.json"
PROVIDER_TEMPLATE = "templates/claude/template-candidate-provider.toml"
CITY_NAME = "city.toml"
REGISTRY_NAME = "rig-permissions.json"
TAG = "gct-oak5"
EXECUTOR = Path(__file__).resolve()
# The executor and every module it imports from this package; their digests are reviewed pins.
EXECUTOR_FILES = ("activate.py", "preroute.py", "candidate_git.py")
# Every file a Claude lane executes or loads from the canonical Template checkout (the three lanes the renderer
# composes), plus the Template profile source.
LANE_FILES = (
    "bin/gct-managed-rig-permissions", "bin/gct-claude-candidate-worker", "bin/gct-claude-signing-worker",
    "bin/gct-claude-template-candidate-worker",
    "lib/gct_claude_candidate_worker.py", "lib/gct_claude_signing_worker.py", "lib/gct_claude_subscription.py",
    "lib/gct_claude_template_candidate_worker.py",
    "templates/claude/candidate-control-policy.json", "templates/claude/candidate-provider.toml",
    "templates/claude/core-signing-control-policy.json", "templates/claude/signing-provider.toml",
    "templates/claude/managed-provider.toml", POLICY, PROVIDER_TEMPLATE, PROFILE,
)
# The exact city.toml edits (asserted counts). The override block is removed with its trailing blank line.
OVERRIDE_BLOCK = (
    '[[rigs.overrides]]\n'
    'agent = "implementation-worker"\n'
    'provider = "claude"\n'
    '[rigs.overrides.option_defaults]\n'
    'model = "opus-5-5"\n'
    'permission_mode = "auto-edit"\n'
    'worktree_access = "template-worktrees-and-git-metadata"\n'
    '\n'
)
PATCH_BEFORE = (
    'dir = "gas-city-template"\n'
    'name = "implementation-worker"\n'
    'work_dir_roots = ["/home/loucmane/gas-city-template-worktrees"]\n'
)


def patch_after(candidate_root: str) -> str:
    return ('dir = "gas-city-template"\n'
            'name = "implementation-worker"\n'
            f'work_dir_roots = ["{candidate_root}"]\n'
            'max_active_sessions = 1\n')


class Refusal(RuntimeError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refusal(reason)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha(path: Path) -> str:
    return digest(Path(path).read_bytes())


class Live:
    """Every live path and pin in one place; tests substitute a fixture layout."""

    def __init__(self, pins: dict):
        self.pins = pins
        self.city = Path(pins["city"])
        self.template = Path(pins["template"])
        self.candidate_root = Path(pins["candidate_root"])
        self.gc = pins["gc"]
        self.env = pins["env"]
        self.managed_settings = Path(pins["managed_settings"])
        self.managed_mcp = Path(pins["managed_mcp"])
        self.claude_json = Path(pins["claude_json"])
        self.uid = int(pins["uid"])
        self.sandbox_writable = tuple(Path(p) for p in pins["sandbox_writable"])

    registry = property(lambda self: self.city / "managed/rig-permissions.json")
    fragment = property(lambda self: self.city / "managed/rig-permissions.toml")
    city_toml = property(lambda self: self.city / "city.toml")
    suspension = property(lambda self: self.city / ".gc/runtime/suspension-state.json")


def run(argv, env, cwd="/", timeout=120, binary=False):
    try:
        result = subprocess.run(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                                text=not binary, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise Refusal(f"timed out after {timeout}s: {argv[:4]}") from exc
    return dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


GIT_ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_ATTR_NOSYSTEM": "1", "GIT_NO_REPLACE_OBJECTS": "1"}


def git(repo: Path, *args, binary=False):
    return run(["/usr/bin/git", "--no-optional-locks", "-C", str(repo), "-c", "core.hooksPath=/dev/null",
                "-c", "core.fsmonitor=false", "-c", "core.attributesFile=/dev/null", *args], GIT_ENV, binary=binary)


def blob(repo: Path, commit: str, path: str) -> bytes:
    result = git(repo, "show", f"{commit}:{path}", binary=True)
    require(result["returncode"] == 0, f"git show {commit}:{path} failed")
    return result["stdout"]


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_exclusive(path: Path, raw: bytes, mode=0o600) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, mode)
    fsync_dir(path.parent)


def identity(path: Path):
    info = path.lstat()
    return (stat.S_IFMT(info.st_mode), stat.S_IMODE(info.st_mode), info.st_uid, info.st_nlink, sha(path))


def fresh_name(directory: Path, stem: str) -> Path:
    for index in range(1000):
        candidate = directory / f".{stem}.{TAG}.{index}"
        if not os.path.lexists(candidate):
            return candidate
    raise Refusal(f"no free name for {stem}")


def replace_atomic(path: Path, raw: bytes, mode: int, uid: int) -> None:
    temporary = fresh_name(path.parent, path.name + ".tmp")
    write_exclusive(temporary, raw, mode)
    os.replace(temporary, path)
    fsync_dir(path.parent)
    require(identity(path) == (stat.S_IFREG, mode, uid, 1, digest(raw)), f"{path} postimage identity")


class Package:
    def __init__(self, root: Path, live: Live, pins_sha: str):
        self.root = root
        self.live = live
        self.records = root / "records"
        self.inputs = root / "inputs"
        self.pins = live.pins
        executor = executor_digests()
        require(self.pins.get("executor") == executor, "executor files are not the reviewed bytes")
        self.binding = dict(pins_sha256=pins_sha,
                            executor_sha256=digest(json.dumps(executor, sort_keys=True).encode()))

    def record(self, step, suffix=""):
        return self.records / f"{step}{suffix}.json"

    def leftovers(self):
        found = []
        for directory in (self.live.city, self.live.city / "managed"):
            found += sorted(str(p) for p in directory.glob(f".*.{TAG}.*"))
        found += sorted(str(p) for p in (self.live.city / "managed").glob(".rig-permissions.toml.tmp.*"))
        found += sorted(str(p) for p in self.live.city.parent.glob("." + self.live.city.name + ".gct-validate.*"))
        return found

    def common(self, step):
        require(not os.path.lexists(self.records / "rollback.json"), "rollback consumed; start a new package")
        require(not os.path.lexists(self.record(step)), f"step already consumed: {step}")
        for earlier in STEPS[: STEPS.index(step)]:
            require(os.path.lexists(self.record(earlier)), f"earlier step missing: {earlier}")
        for earlier in STEPS[: STEPS.index(step)]:
            recorded = json.loads(self.record(earlier).read_text())
            require(recorded.get("binding") == self.binding, f"{earlier} was recorded under another binding")

    def begin(self, step):
        self.common(step)
        require(not os.path.lexists(self.record(step, ".intent")), f"interrupted after intent; use resume {step}")
        require(not [p for p in self.leftovers() if ".tmp" in p or "gct-validate" in p],
                f"leftover temporaries: {self.leftovers()}")
        return self.quiet()

    def quiet(self):
        status = run([self.live.gc, "--city", str(self.live.city), "status", "--json"], self.live.env, timeout=60)
        require(status["returncode"] == 0, "gc status failed: " + status["stderr"][-300:])
        value = json.loads(status["stdout"])
        require(not value.get("partial") and not value.get("partial_errors"), "partial status observation")
        agents, rigs = value["agents"], value["rigs"]
        require(isinstance(agents, list) and isinstance(rigs, list) and rigs, "status shape")
        require(not [a["name"] for a in agents if a["running"]], "an agent is running")
        # Core emits active_sessions with omitempty, so an absent key is exactly zero.
        require(value["summary"].get("active_sessions", 0) == 0, "a session is active")
        require(all(r["suspended"] is True for r in rigs), "a rig is not suspended")
        pid = value["controller"]["pid"]
        require(isinstance(pid, int) and pid > 0, "controller pid")
        return dict(controller=pid, rigs=sorted(r["name"] for r in rigs), suspension_sha256=sha(self.live.suspension))

    def intent(self, step, before):
        write_exclusive(self.record(step, ".intent"),
                        (json.dumps(dict(step=step, before=before, binding=self.binding), sort_keys=True) + "\n").encode())

    def finish(self, step, before, value, resumed=False):
        after = self.quiet()
        require(after == before, f"city changed during the step: {before} -> {after}")
        body = dict(value, step=step, bead="gct-oak5", resumed=resumed, before=before, after=after,
                    binding=self.binding)
        write_exclusive(self.record(step), (json.dumps(body, sort_keys=True, indent=1) + "\n").encode())
        print(json.dumps(dict(step=step, ok=True, resumed=resumed)))

    def pinned_input(self, name):
        raw = (self.inputs / name).read_bytes()
        require(digest(raw) == self.pins["inputs"][name], f"input digest drift: {name}")
        return raw


# ---------------------------------------------------------------- derivations (pure)

def candidate_record(profile: dict, python_toolchain: dict, candidate_root: str) -> dict:
    require(profile.get("schema") == "gc.managed-rig-permissions.v2", "profile schema")
    (record,) = profile["rigs"]
    record = json.loads(json.dumps(record))
    require(record["name"] == RIG and record["agents"] == [AGENT] and record["git_metadata"] is False
            and record["provider"] == "claude" and record["worktree_root"] == candidate_root
            and record["control_policy"]["source"] == POLICY, "unexpected Template candidate record")
    require(record["toolchains"] == [python_toolchain], "the profile's Python pin is not the measured toolchain")
    return record


def new_registry(raw: bytes, record: dict) -> bytes:
    value = json.loads(raw)
    require(value["schema"] == "gc.managed-rig-permissions.v2", "registry schema")
    require(not [r for r in value["rigs"] if r["name"] == RIG and AGENT in r["agents"]],
            "the Template worker is already registered")
    require((json.dumps(value, indent=2) + "\n").encode() == raw, "registry is not in the live serialization")
    value["rigs"].append(json.loads(json.dumps(record, sort_keys=True)))
    return (json.dumps(value, indent=2) + "\n").encode()


def template_rig(config: dict) -> dict:
    (rig,) = [r for r in config["rigs"] if r["name"] == RIG]
    return rig


def worker_patches(config: dict) -> list:
    return [a for a in config.get("patches", {}).get("agent", []) if a.get("dir") == RIG and a.get("name") == AGENT]


def new_city(raw: bytes, candidate_root: str) -> bytes:
    """The reviewed city.toml postimage: exactly the three edits, proven again at the TOML level."""
    text = raw.decode()
    require(text.count(OVERRIDE_BLOCK) == 1, "the implementation-worker override block is not exactly once")
    require(text.count(PATCH_BEFORE) == 1, "the implementation-worker work_dir_roots patch is not exactly once")
    new = text.replace(OVERRIDE_BLOCK, "", 1).replace(PATCH_BEFORE, patch_after(candidate_root), 1)
    old_cfg, new_cfg = tomllib.loads(text), tomllib.loads(new)
    old_rig, new_rig = template_rig(old_cfg), template_rig(new_cfg)
    require([o["agent"] for o in old_rig["overrides"]] == ["run-operator", AGENT], "predecessor overrides")
    require(new_rig["overrides"] == [old_rig["overrides"][0]], "only the run-operator override may remain")
    require({k: v for k, v in new_rig.items() if k != "overrides"} == {k: v for k, v in old_rig.items() if k != "overrides"},
            "the Template rig changed beyond its overrides")
    require(worker_patches(old_cfg) == [dict(dir=RIG, name=AGENT, work_dir_roots=["/home/loucmane/gas-city-template-worktrees"])],
            "predecessor worker patch")
    require(worker_patches(new_cfg) == [dict(dir=RIG, name=AGENT, work_dir_roots=[candidate_root], max_active_sessions=1)],
            "postimage worker patch")
    others = lambda cfg: [a for a in cfg["patches"]["agent"] if not (a.get("dir") == RIG and a.get("name") == AGENT)]
    require(others(new_cfg) == others(old_cfg), "another agent patch changed")
    require({k: v for k, v in new_cfg["patches"].items() if k != "agent"} == {k: v for k, v in old_cfg["patches"].items() if k != "agent"},
            "another patch table changed")
    require([r for r in new_cfg["rigs"] if r["name"] != RIG] == [r for r in old_cfg["rigs"] if r["name"] != RIG],
            "another rig changed")
    require({k: v for k, v in new_cfg.items() if k not in ("rigs", "patches")}
            == {k: v for k, v in old_cfg.items() if k not in ("rigs", "patches")}, "a non-rig table changed")
    return new.encode()


# ---------------------------------------------------------------- steps

def path_chain_ok(p: Package, path: Path, entry: str) -> None:
    for walk in (path, Path(os.path.realpath(path))):
        require(not any(walk == w or w in walk.parents for w in (p.live.candidate_root, *p.live.sandbox_writable)),
                f"PATH entry inside a sandbox-writable path: {entry}")
        while True:
            info = walk.lstat()
            require(info.st_uid in (0, p.live.uid), f"PATH component owner: {walk}")
            require(stat.S_ISLNK(info.st_mode) or not info.st_mode & 0o022, f"PATH component group/world-writable: {walk}")
            if walk == walk.parent:
                break
            walk = walk.parent


def shared(function, *args):
    """Run a shared preroute check, turning its refusal into this executor's refusal."""
    try:
        return function(*args)
    except preroute.Refusal as exc:
        raise Refusal(str(exc)) from exc


def executor_digests() -> dict:
    return {name: sha(EXECUTOR.parent / name) for name in EXECUTOR_FILES}


def gc_city_name(p: Package) -> str:
    listed = run([p.live.gc, "--city", str(p.live.city), "agent", "list", "--json"], p.live.env, timeout=60)
    require(listed["returncode"] == 0, "gc agent list failed")
    value = json.loads(listed["stdout"])
    require(isinstance(value, dict) and isinstance(value.get("city_name"), str), "gc agent list has no city_name")
    return value["city_name"]


def step_host(p: Package):
    before = p.begin("host")
    live = p.live
    process_record = shared(preroute.observe_city, Path(p.pins["user_slice"]), before["controller"], p.live.city)
    require(Path(process_record["tmux_socket"]).name == gc_city_name(p), "gc and the record disagree on the city name")
    require(not os.path.lexists(live.managed_settings), f"managed-policy settings present: {live.managed_settings}")
    require(not os.path.lexists(live.managed_mcp), f"managed MCP configuration present: {live.managed_mcp}")
    trust = json.loads(live.claude_json.read_text()) if live.claude_json.exists() else {}
    for project, entry in (trust.get("projects") or {}).items():
        if project == str(live.candidate_root) or project.startswith(str(live.candidate_root) + "/"):
            require(not entry.get("enabledMcpjsonServers") and not entry.get("enableAllProjectMcpServers")
                    and not entry.get("mcpServers"), f"project MCP servers approved for {project}")
    current = live.template / ".git"
    while True:
        require(Path(os.path.realpath(current)) == current and stat.S_ISDIR(current.lstat().st_mode),
                f"not a physical directory: {current}")
        if current == current.parent:
            break
        current = current.parent
    relative = git(live.template, "config", "--get", "worktree.useRelativePaths")
    require(relative["returncode"] in (0, 1) and relative["stdout"].strip() in {"", "false"},
            "git would write relative worktree paths")
    for entry in p.pins["candidate_path"].split(":"):
        path = Path(entry)
        require(path.is_absolute() and path.is_dir(), f"PATH entry missing: {entry}")
        path_chain_ok(p, path, entry)
    allowed = {g.format(uid=live.uid) for g in preroute.ALLOWED_HIDDEN_CGROUPS}
    hidden = process_record["hidden"]
    require(set(hidden) <= allowed, f"processes hidden from /proc outside the reviewed cgroups: {hidden}")
    p.intent("host", before)
    raw_record = preroute.encode_record(process_record)
    write_exclusive(p.records / "process-record.json", raw_record)
    p.finish("host", before, dict(read_only=True, user_mcp_servers=sorted((trust.get("mcpServers") or {}).keys()),
                                  process_record=process_record, process_record_sha256=digest(raw_record)))


def derive_inputs(p: Package) -> dict:
    live = p.live
    profile = json.loads(blob(live.template, p.pins["template_commit"], PROFILE))
    record = candidate_record(profile, p.pins["python_toolchain"], str(live.candidate_root))
    return {REGISTRY_NAME: new_registry(live.registry.read_bytes(), record),
            CITY_NAME: new_city(live.city_toml.read_bytes(), str(live.candidate_root))}


def step_inputs(p: Package):
    before = p.begin("inputs")
    live = p.live
    require(sha(live.registry) == p.pins["registry_before"], "registry predecessor")
    require(sha(live.city_toml) == p.pins["city_before"], "city predecessor")
    derived = derive_inputs(p)
    for name, raw in derived.items():
        require(digest(raw) == p.pins["inputs"][name], f"derived {name} differs from the reviewed pin")
    p.intent("inputs", before)
    for name, raw in derived.items():
        write_exclusive(p.inputs / name, raw, 0o644)
    p.finish("inputs", before, dict(inputs={n: digest(r) for n, r in derived.items()}))


def root_postcondition(p: Package) -> bool:
    root = p.live.candidate_root
    try:
        info = root.lstat()
    except FileNotFoundError:
        return False
    return (stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o755 and info.st_uid == p.live.uid
            and os.listdir(root) == [])


def step_root(p: Package):
    before = p.begin("root")
    root = p.live.candidate_root
    require(stat.S_ISDIR(root.parent.lstat().st_mode) and Path(os.path.realpath(root.parent)) == root.parent,
            "candidate root parent is not physical")
    adopted = os.path.lexists(root)
    require(not adopted or root_postcondition(p), "candidate root exists and is not an empty operator directory")
    p.intent("root", before)
    if not adopted:
        os.mkdir(root, 0o755)
        os.chmod(root, 0o755)
    require(root_postcondition(p), "candidate root postcondition")
    p.finish("root", before, dict(root=str(root), adopted_existing=adopted))


def checkout_state(p: Package):
    head = git(p.live.template, "rev-parse", "HEAD")["stdout"].strip()
    status = git(p.live.template, "status", "--porcelain=v1", "--untracked-files=normal")["stdout"]
    return head, status


def tree_entry(p: Package, commit: str, path: str):
    listed = git(p.live.template, "ls-tree", "-z", commit, "--", path, binary=True)
    require(listed["returncode"] == 0, f"ls-tree {commit} {path} failed")
    if not listed["stdout"]:
        return None
    mode, kind, _rest = listed["stdout"].split(b"\0")[0].split(b" ", 2)
    require(kind == b"blob" and mode in (b"100644", b"100755"), f"lane path is not a regular blob: {path}")
    return mode.decode()


def lane_files_match(p: Package, commit: str) -> dict:
    """Every lane file present at commit equals its blob on disk, bytes and executable bit; absent ones are absent."""
    found = {}
    for path in LANE_FILES:
        mode = tree_entry(p, commit, path)
        on_disk = p.live.template / path
        if mode is None:
            require(not os.path.lexists(on_disk), f"lane file present on disk but absent at {commit}: {path}")
            found[path] = None
            continue
        info = on_disk.lstat()
        require(stat.S_ISREG(info.st_mode), f"lane file is not a regular file: {path}")
        require(bool(info.st_mode & 0o100) == (mode == "100755"), f"lane file mode differs from {commit}: {path}")
        require(not info.st_mode & 0o022, f"lane file is group- or world-writable: {path}")
        require(digest(on_disk.read_bytes()) == digest(blob(p.live.template, commit, path)),
                f"lane file differs from {commit}: {path}")
        found[path] = digest(on_disk.read_bytes())
    return found


def no_local_attributes(p: Package) -> None:
    located = git(p.live.template, "rev-parse", "--git-path", "info/attributes")
    require(located["returncode"] == 0, "cannot locate info/attributes")
    path = Path(located["stdout"].strip())
    path = path if path.is_absolute() else p.live.template / path
    require(not os.path.lexists(path), f"repository-local attributes present: {path}")


def attributes_free_of_filters(p: Package, commit: str) -> None:
    listed = git(p.live.template, "ls-tree", "-r", "--name-only", "-z", commit, binary=True)
    require(listed["returncode"] == 0, "ls-tree failed")
    for name in listed["stdout"].split(b"\0"):
        if name and name.split(b"/")[-1] == b".gitattributes":
            text = blob(p.live.template, commit, name.decode())
            require(b"filter=" not in text, f"a filter attribute exists at {commit}: {name.decode()}")


def step_checkout(p: Package):
    before = p.begin("checkout")
    head, status = checkout_state(p)
    require(head == p.pins["template_before"], "canonical checkout predecessor")
    require(status == p.pins["template_status"], f"canonical checkout is not clean: {status!r}")
    target = p.pins["template_commit"]
    require(git(p.live.template, "merge-base", "--is-ancestor", head, target)["returncode"] == 0,
            "target is not a descendant of the checkout")
    require(git(p.live.template, "rev-parse", target + "^{tree}")["stdout"].strip() == p.pins["template_tree"],
            "target tree is not the reviewed tree")
    require(digest(blob(p.live.template, target, "bin/gct-managed-rig-permissions")) == p.pins["renderer_sha"],
            "target renderer blob")
    changed = git(p.live.template, "diff", "--name-only", "--no-renames", head, target)
    require(changed["returncode"] == 0 and sorted(changed["stdout"].split()) == sorted(p.pins["template_changed"]),
            "the reviewed Template change set differs")
    attributes_free_of_filters(p, head)
    attributes_free_of_filters(p, target)
    no_local_attributes(p)
    lane_files_match(p, head)
    p.intent("checkout", before)
    if head != target:
        moved = git(p.live.template, "checkout", "--detach", target)
        require(moved["returncode"] == 0, "checkout failed: " + moved["stderr"])
    after_head, after_status = checkout_state(p)
    require(after_head == target and after_status == p.pins["template_status"], "checkout postcondition")
    p.finish("checkout", before, dict(before_commit=head, after_commit=target, lane_files=lane_files_match(p, target)))


def backup(p: Package, live_path: Path, name: str):
    target = p.root / "backups" / name
    target.parent.mkdir(mode=0o700, exist_ok=True)
    if not target.exists():
        write_exclusive(target, live_path.read_bytes(), 0o600)
    require(sha(target) == sha(live_path), f"backup of {name} differs from live")


def step_registry(p: Package):
    before = p.begin("registry")
    new = p.pinned_input(REGISTRY_NAME)
    require(identity(p.live.registry) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["registry_before"]),
            "registry predecessor identity")
    backup(p, p.live.registry, REGISTRY_NAME)
    p.intent("registry", before)
    replace_atomic(p.live.registry, new, 0o644, p.live.uid)
    p.finish("registry", before, dict(after_sha256=digest(new)))


def fragment_structure(p: Package, before_raw: bytes, after_raw: bytes) -> dict:
    """The rendered fragment adds exactly the reviewed Template provider and patch and changes nothing else."""
    old, new = tomllib.loads(before_raw.decode()), tomllib.loads(after_raw.decode())
    require({k: v for k, v in new.items() if k not in ("providers", "patches")}
            == {k: v for k, v in old.items() if k not in ("providers", "patches")}, "a non-provider table changed")
    require(set(new.get("patches", {})) == set(old.get("patches", {})), "patch table kinds changed")
    for kind, value in old.get("patches", {}).items():
        if kind != "agent":
            require(new["patches"][kind] == value, f"patch table {kind} changed")
    patches = {(a["dir"], a["name"]): a for a in new["patches"]["agent"]}
    old_patches = {(a["dir"], a["name"]): a for a in old["patches"]["agent"]}
    require(len(patches) == len(new["patches"]["agent"]), "duplicate agent patches in the new fragment")
    require(set(patches) - set(old_patches) == {(RIG, AGENT)} and set(old_patches) <= set(patches),
            "exactly one new agent patch")
    require(all(patches[k] == v for k, v in old_patches.items()), "an existing agent patch changed")
    for name, block in old.get("providers", {}).items():
        require(new["providers"].get(name) == block, f"existing provider {name} changed")
    require(set(new["providers"]) - set(old.get("providers", {})) == {PROVIDER}, "exactly one new provider")
    patch = patches[(RIG, AGENT)]
    require(set(patch) == {"dir", "name", "provider", "option_defaults", "env"}, f"Template patch keys {sorted(patch)}")
    choice = patch["option_defaults"].get("managed_worktree_access")
    require(patch["provider"] == PROVIDER and patch["option_defaults"] == {
        "model": "opus-5-5", "permission_mode": "full-auto", "managed_worktree_access": choice},
        f"Template patch option_defaults {patch['option_defaults']}")
    require(patch["env"] == {"PATH": p.pins["candidate_path"]}, "Template patch env")
    template = tomllib.loads(blob(p.live.template, p.pins["template_commit"], PROVIDER_TEMPLATE).decode())
    template = template["providers"][PROVIDER]
    provider = new["providers"][PROVIDER]
    require({k: v for k, v in provider.items() if k != "options_schema"}
            == {k: v for k, v in template.items() if k != "options_schema"}, "Template provider body")
    require([o["key"] for o in provider["options_schema"]] == [o["key"] for o in template["options_schema"]],
            "Template provider options")
    for got, want in zip(provider["options_schema"], template["options_schema"]):
        if got["key"] != "managed_worktree_access":
            require(got == want, f"Template provider option {got['key']}")
            continue
        require({k: v for k, v in got.items() if k != "choices"} == {k: v for k, v in want.items() if k != "choices"}
                and got["choices"][: len(want["choices"])] == want["choices"]
                and len(got["choices"]) == len(want["choices"]) + 1, "Template access option")
        granted = got["choices"][-1]
        policy = str(p.live.template / POLICY)
        require(set(granted) == {"value", "label", "flag_args"} and granted["value"] == choice
                and granted["flag_args"] == ["--settings", policy, "--add-dir", str(p.live.candidate_root)],
                f"Template grant {granted}")
    return dict(choice=choice)


def prerender(p: Package, argv: list[str]) -> bytes:
    """Render into a package-local scratch city first; validation is the live apply's job."""
    for index in range(1000):
        scratch = p.root / f"render-scratch-{index}"
        if not os.path.lexists(scratch):
            break
    else:
        raise Refusal("no free render scratch name")
    (scratch / "managed").mkdir(parents=True, mode=0o700)
    write_exclusive(scratch / "city.toml", p.live.city_toml.read_bytes(), 0o600)
    env = dict(p.live.env, GCT_SKIP_CONFIG_VALIDATION="1")
    result = run(argv + ["--apply", "--json", "--registry", str(p.live.registry), "--city", str(scratch),
                         "--output", str(scratch / "managed/rig-permissions.toml")], env)
    require(result["returncode"] == 0, "scratch render failed: " + result["stderr"][-300:])
    return (scratch / "managed/rig-permissions.toml").read_bytes()


def post_registry_predecessors(p: Package) -> None:
    require(identity(p.live.registry) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"][REGISTRY_NAME]),
            "registry is not the reviewed postimage")
    require(checkout_state(p) == (p.pins["template_commit"], p.pins["template_status"]), "checkout drifted")
    require(root_postcondition(p), "candidate root is not the empty operator directory")


def step_render(p: Package):
    before = p.begin("render")
    require(identity(p.live.fragment) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["fragment_before"]),
            "fragment predecessor identity")
    require(identity(p.live.city_toml) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["city_before"]),
            "city.toml predecessor identity")
    post_registry_predecessors(p)
    renderer = p.live.template / "bin/gct-managed-rig-permissions"
    require(sha(renderer) == p.pins["renderer_sha"], "renderer bytes")
    lanes = lane_files_match(p, p.pins["template_commit"])
    argv = ["/usr/bin/python3.12", "-I", "-B", str(renderer)]
    tail = ["--json", "--city", str(p.live.city)]
    scratch_raw = prerender(p, argv)
    structure = fragment_structure(p, p.live.fragment.read_bytes(), scratch_raw)
    # The render check validates the composed live configuration, which still carries the override; the city
    # step removes it after this fragment exists, so the new provider resolves.
    checked = run(argv + ["--check"] + tail, p.live.env)
    report = json.loads(checked["stdout"] or "{}")
    expected = report.get("expected_sha256")
    provider_template = digest(blob(p.live.template, p.pins["template_commit"], PROVIDER_TEMPLATE))
    require(checked["returncode"] == 4 and report.get("state") == "drift" and expected == digest(scratch_raw)
            and report.get("actual_sha256") == p.pins["fragment_before"]
            and report.get("registry_file_sha256") == p.pins["inputs"][REGISTRY_NAME]
            and (report.get("provider_template_sha256s") or {}).get(PROVIDER) == provider_template,
            "render check does not match the reviewed inputs; nothing written")
    backup(p, p.live.fragment, "rig-permissions.toml")
    p.intent("render", dict(before, expected_fragment_sha256=expected))
    applied = run(argv + ["--apply"] + tail, p.live.env)
    report = json.loads(applied["stdout"] or "{}")
    require(applied["returncode"] == 0 and report.get("actual_sha256") == expected == sha(p.live.fragment),
            "render apply did not produce the checked bytes")
    p.finish("render", before, dict(check=checked, apply=applied, fragment_sha256=expected, structure=structure,
                                    lane_files=lanes))


def resolved(p: Package, city: Path) -> dict:
    """The composed Template worker and run-operator from `gc config show --json` for the given city directory."""
    shown = run([p.live.gc, "--city", str(city), "config", "show", "--json"], p.live.env, timeout=120)
    require(shown["returncode"] == 0, "gc config show failed: " + shown["stderr"][-300:])
    agents = json.loads(shown["stdout"])["config"]["Agents"]
    worker = [a for a in agents if a.get("Dir") == RIG and a.get("Name") == AGENT]
    operator = [a for a in agents if a.get("Dir") == RIG and a.get("Name") == "run-operator"]
    require(len(worker) == 1 and len(operator) == 1, f"Template agents resolve {len(worker)}/{len(operator)} times")
    return dict(worker=worker[0], operator=operator[0])


def worker_proof(p: Package, value: dict, choice: str) -> dict:
    worker, operator = value["worker"], value["operator"]
    require(worker.get("Provider") == PROVIDER, f"worker provider {worker.get('Provider')!r}")
    require(worker.get("OptionDefaults") == {"model": "opus-5-5", "permission_mode": "full-auto",
                                            "managed_worktree_access": choice},
            f"worker option defaults {worker.get('OptionDefaults')}")
    require(worker.get("WorkDirRoots") == [str(p.live.candidate_root)], f"worker work_dir_roots {worker.get('WorkDirRoots')}")
    require(worker.get("MaxActiveSessions") == 1, f"worker cap {worker.get('MaxActiveSessions')}")
    require(worker.get("Scope") == "rig", f"worker scope {worker.get('Scope')!r}")
    require(operator.get("Provider") == "claude" and operator.get("OptionDefaults") == {
        "model": "haiku-4-5", "permission_mode": "auto-edit", "worktree_access": "template-worktrees-and-git-metadata"},
        f"run-operator override changed: {operator.get('Provider')} {operator.get('OptionDefaults')}")
    return dict(worker={k: worker.get(k) for k in ("Provider", "OptionDefaults", "WorkDirRoots", "MaxActiveSessions", "Scope")},
                operator={k: operator.get(k) for k in ("Provider", "OptionDefaults")})


def validate_city(p: Package, city_raw: bytes, choice: str) -> dict:
    """Prove Core loads and composes the city with the postimage city.toml before anything live changes.

    A throwaway shadow beside the city symlinks every entry except city.toml, which is a copy of the postimage
    (the managed fragment is the live, just-rendered one). The shadow's gc config loads may rewrite Core's own
    runtime assets under the live .gc, the same bytes every quiet() gc status call writes (ga-6utp r12 note).
    """
    shadow = Path(tempfile.mkdtemp(prefix="." + p.live.city.name + ".gct-validate.oak5-", dir=p.live.city.parent))
    try:
        for entry in sorted(os.listdir(p.live.city)):
            if entry != "city.toml":
                os.symlink(p.live.city / entry, shadow / entry)
        write_exclusive(shadow / "city.toml", city_raw, 0o644)
        checked = run([p.live.gc, "--city", str(shadow), "config", "show", "--validate"], p.live.env, timeout=120)
        require(checked["returncode"] == 0, "postimage fails gc config validation: " + checked["stderr"][-400:])
        return worker_proof(p, resolved(p, shadow), choice)
    finally:
        for entry in os.listdir(shadow):
            os.unlink(shadow / entry)
        os.rmdir(shadow)


def clear_own_leftovers(p: Package) -> list[str]:
    """Remove only this package's own crash leftovers, in their exact shape: a validation shadow whose entries are
    all symlinks plus one regular city.toml. Anything else is left for a human and still blocks."""
    removed = []
    for shadow in sorted(p.live.city.parent.glob("." + p.live.city.name + ".gct-validate.oak5-*")):
        info = shadow.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != p.live.uid:
            continue
        entries = {name: (shadow / name).lstat() for name in os.listdir(shadow)}
        real = [n for n, s in entries.items() if not stat.S_ISLNK(s.st_mode)]
        if real not in ([], ["city.toml"]) or ("city.toml" in real and not stat.S_ISREG(entries["city.toml"].st_mode)):
            continue
        for name in os.listdir(shadow):
            os.unlink(shadow / name)
        os.rmdir(shadow)
        removed.append(str(shadow))
    return removed


def post_render_predecessors(p: Package) -> dict:
    post_registry_predecessors(p)
    render = json.loads(p.record("render").read_text())
    require(identity(p.live.fragment) == (stat.S_IFREG, 0o644, p.live.uid, 1, render["fragment_sha256"]),
            "fragment is not the recorded render")
    return render


def step_city(p: Package):
    before = p.begin("city")
    render = post_render_predecessors(p)
    new = p.pinned_input(CITY_NAME)
    require(identity(p.live.city_toml) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["city_before"]),
            "city.toml predecessor identity")
    proof = validate_city(p, new, render["structure"]["choice"])
    backup(p, p.live.city_toml, CITY_NAME)
    p.intent("city", before)
    replace_atomic(p.live.city_toml, new, 0o644, p.live.uid)
    p.finish("city", before, dict(city_sha256=digest(new), shadow=proof))


def listed_worker(p: Package) -> dict:
    listed = run([p.live.gc, "--city", str(p.live.city), "agent", "list", "--json"], p.live.env, timeout=60)
    require(listed["returncode"] == 0, "gc agent list failed")
    value = json.loads(listed["stdout"])
    require(value.get("schema_version") == "1" and isinstance(value.get("agents"), list), "agent list shape")
    found = [a for a in value["agents"] if a.get("qualified_name") == QUALIFIED]
    require(len(found) == 1, f"expected one {QUALIFIED}, found {len(found)}")
    return found[0]


def reload(p: Package) -> dict:
    reloaded = run([p.live.gc, "--city", str(p.live.city), "reload", "--json"], p.live.env, timeout=480)
    ack = json.loads(reloaded["stdout"] or "{}")
    require(reloaded["returncode"] == 0 and ack.get("ok") is True and ack.get("async") is False
            and ack.get("soft") is False and ack.get("outcome") in {"applied", "no_change"} and ack.get("revision"),
            f"reload acknowledgement {ack}")
    return ack


def live_proof(p: Package, choice: str) -> dict:
    proof = worker_proof(p, resolved(p, p.live.city), choice)
    listed = listed_worker(p)
    require(listed.get("provider") == PROVIDER and listed.get("pool") == {"min": 0, "max": 1},
            f"agent list {listed.get('provider')} {listed.get('pool')}")
    return dict(proof, listed={k: listed.get(k) for k in ("qualified_name", "provider", "pool", "suspended")})


def step_reload(p: Package):
    before = p.begin("reload")
    render = post_render_predecessors(p)
    require(identity(p.live.city_toml) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"][CITY_NAME]),
            "city.toml is not the reviewed postimage")
    p.intent("reload", before)
    ack = reload(p)
    p.finish("reload", before, dict(reload=ack, composed=live_proof(p, render["structure"]["choice"])))


ACTIONS = {"host": step_host, "inputs": step_inputs, "root": step_root, "checkout": step_checkout,
           "registry": step_registry, "render": step_render, "city": step_city, "reload": step_reload}


def resume(p: Package, step: str):
    require(step in STEPS and step != "host", "resume needs a mutating step")
    p.common(step)
    intent = p.record(step, ".intent")
    require(os.path.lexists(intent), f"no interrupted intent for {step}")
    recorded = json.loads(intent.read_text())
    require(recorded.get("binding") == p.binding, "intent belongs to another binding")
    before = {k: v for k, v in recorded["before"].items() if k != "expected_fragment_sha256"}
    extra = {}
    if step == "inputs":
        require(all((p.inputs / n).exists() and sha(p.inputs / n) == d for n, d in p.pins["inputs"].items()),
                "inputs postcondition does not hold; inspect, then rollback")
    elif step == "root":
        require(root_postcondition(p), "root postcondition does not hold; inspect, then rollback")
    elif step == "checkout":
        require(checkout_state(p) == (p.pins["template_commit"], p.pins["template_status"]),
                "checkout postcondition does not hold; inspect, then rollback")
        extra = dict(lane_files=lane_files_match(p, p.pins["template_commit"]))
    elif step == "registry":
        require(identity(p.live.registry) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"][REGISTRY_NAME]),
                "registry postcondition does not hold; inspect, then rollback")
    elif step == "render":
        post_registry_predecessors(p)
        expected = recorded["before"].get("expected_fragment_sha256")
        require(sha(p.live.fragment) == expected, "render postcondition does not hold; inspect, then rollback")
        saved = (p.root / "backups" / "rig-permissions.toml").read_bytes()
        require(digest(saved) == p.pins["fragment_before"], "backup rig-permissions.toml differs from its pin")
        extra = dict(fragment_sha256=expected, structure=fragment_structure(p, saved, p.live.fragment.read_bytes()),
                     lane_files=lane_files_match(p, p.pins["template_commit"]))
    elif step == "city":
        render = post_render_predecessors(p)
        require(identity(p.live.city_toml) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"][CITY_NAME]),
                "city postcondition does not hold; inspect, then rollback")
        extra = dict(city_sha256=sha(p.live.city_toml),
                     composed=worker_proof(p, resolved(p, p.live.city), render["structure"]["choice"]))
    elif step == "reload":
        render = post_render_predecessors(p)
        require(identity(p.live.city_toml) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"][CITY_NAME]),
                "city.toml is not the reviewed postimage")
        extra = dict(reload=reload(p), composed=live_proof(p, render["structure"]["choice"]))
    p.finish(step, before, dict(extra, resumed_from_intent=True), resumed=True)


def rollback(p: Package):
    """Restore every changed live file from digest-verified backups; refuse on any foreign state."""
    require(os.path.isdir(p.records) and not os.path.lexists(p.records / "rollback.json"), "rollback state")
    require(any(p.records.glob("*.json")), "nothing recorded; there is nothing to roll back")
    observed = p.quiet()
    cleared = clear_own_leftovers(p)
    require(not [q for q in p.leftovers() if ".tmp" in q or "gct-validate" in q],
            f"leftover temporaries: {p.leftovers()}")
    head, status = checkout_state(p)
    if (head, status) == (p.pins["template_commit"], p.pins["template_status"]):
        lane_files_match(p, p.pins["template_commit"])
    else:
        require((head, status) == (p.pins["template_before"], p.pins["template_status"]),
                "canonical Template checkout is neither the clean predecessor nor the reviewed target; "
                "stop and inspect by hand")
        lane_files_match(p, p.pins["template_before"])
    restores = []
    for name, live_path, pre, post in (
        (CITY_NAME, p.live.city_toml, p.pins["city_before"], p.pins["inputs"][CITY_NAME]),
        ("rig-permissions.toml", p.live.fragment, p.pins["fragment_before"], None),
        (REGISTRY_NAME, p.live.registry, p.pins["registry_before"], p.pins["inputs"][REGISTRY_NAME]),
    ):
        current = sha(live_path)
        if current == pre:
            continue
        if post is not None:
            require(current == post, f"{name} is neither its predecessor nor its reviewed postimage; refusing")
        else:
            known = set()
            if os.path.lexists(p.record("render")):
                known.add(json.loads(p.record("render").read_text())["fragment_sha256"])
            if os.path.lexists(p.record("render", ".intent")):
                known.add(json.loads(p.record("render", ".intent").read_text())["before"].get("expected_fragment_sha256"))
            require(current in known, f"{name} is not the recorded or intended render; refusing")
        raw = (p.root / "backups" / name).read_bytes()
        require(digest(raw) == pre, f"backup {name} differs from its pin")
        restores.append((name, live_path, raw))
    # Everything is validated; only now write, in reverse step order (city, fragment, registry, checkout).
    actions = []
    for name, live_path, raw in restores:
        replace_atomic(live_path, raw, 0o644, p.live.uid)
        actions.append(name)
    if head != p.pins["template_before"]:
        moved = git(p.live.template, "checkout", "--detach", p.pins["template_before"])
        require(moved["returncode"] == 0, "checkout rollback failed: " + moved["stderr"])
        actions.append("checkout")
    require(checkout_state(p) == (p.pins["template_before"], p.pins["template_status"]),
            "canonical Template checkout is not the clean predecessor after rollback; stop and inspect by hand")
    lane_files_match(p, p.pins["template_before"])
    ack = reload(p)
    composed = resolved(p, p.live.city)
    require(composed["worker"].get("Provider") == "claude"
            and composed["worker"].get("WorkDirRoots") == ["/home/loucmane/gas-city-template-worktrees"],
            "Template worker is not back on its predecessor composition after rollback")
    after = p.quiet()
    require(after == observed, f"the city changed during rollback: {observed} -> {after}")
    value = dict(actions=actions, quiet=observed, quiet_after=after, reload=ack, leftovers=p.leftovers(),
                 cleared_own_leftovers=cleared,
                 candidate_root_left_in_place=os.path.lexists(p.live.candidate_root), binding=p.binding)
    write_exclusive(p.records / "rollback.json", (json.dumps(value, indent=1, sort_keys=True) + "\n").encode())
    print(json.dumps(dict(rollback=actions, ok=True)))


def main(argv):
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            "isolated source-only UID1000 invocation required")
    require(len(argv) in (3, 4) and len(argv[1]) == 64,
            "usage: activate.py <package-dir> <pins-sha256> <step>|resume <step>|rollback")
    root = Path(argv[0])
    pins_raw = (root / "pins.json").read_bytes()
    require(digest(pins_raw) == argv[1], "pins.json is not the reviewed pins")
    package = Package(root, Live(json.loads(pins_raw)), argv[1])
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
