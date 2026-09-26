"""Activate the Operations candidate lane (gct-lagl), one guarded step per invocation.

  python3 -I -B activate.py <package-dir> <pins-sha256> host|inputs|root|checkout|registry|city|render|reload
  python3 -I -B activate.py <package-dir> <pins-sha256> resume <step>
  python3 -I -B activate.py <package-dir> <pins-sha256> rollback

Runs only after the ga-4z38 window's TERMINAL and after Template PR 70 merged. r10 (ga-e0t1.18): the live
canonical checkout is already at cfd353f3 (PR 70 and PR 71), so the base and target pins are equal and the
checkout step proves the lane files without moving; M8 then adopts the changed city files. The reviewed pins
digest is passed on every invocation. Every intent and record binds that digest and the digest of
this executor. The discipline follows the reviewed M5 prereqs.py:
- Every step proves its exact predecessor state and a quiet city before it writes an intent. It
  then makes one bounded change, proves the exact postcondition and the same quiet city, and writes
  one exclusive record under <package-dir>/records.
- After an intent, only `resume` is accepted. `resume` proves the postcondition and never repeats a
  mutation. The one exception is `resume reload`: a reload is idempotent, so it is re-issued and must
  report applied or no_change.
- `rollback` refuses on any live file that is neither its predecessor nor its reviewed postimage. It
  restores every changed file from a digest-verified backup through an atomic replace, in reverse
  order. It moves the prompt aside under a fresh name, restores the checkout with hooks off, then
  reloads and proves the candidate agent is gone. It never deletes; the candidate root stays.

The steps, in order:
- host: read-only host facts.
  - No managed-policy settings or managed MCP file.
  - No project trust entry approves MCP servers for the candidate root. User-scope MCP servers are
    recorded; gct-1ldk tracks whether they start in worker sessions.
  - The Operations common directory chain is physical.
  - git writes absolute worktree paths.
  - Every candidate PATH entry exists and passes on both its lexical and its resolved chain: nothing
    under the candidate root or a sandbox-writable location, every owner root or the operator,
    nothing group- or world-writable.
- inputs: derives, writes and pins every new byte string (registry, city.toml, prompt).
- root: creates the candidate root, operator-owned, 0755, empty.
- checkout: requires the canonical Template checkout to have its pinned status and the reviewed change
  set, with no filter attribute at either commit. It proves every lane file present at the base (bytes
  and executable bit) and the absence of the rest, moves it with hooks, fsmonitor and attributes off to
  the reviewed merge commit, and proves every lane file there.
- registry: appends the candidate record.
- city: installs the prompt and appends the gascity-bound agent: suspended, max_active_sessions = 1.
- render: renders into a package-local scratch city first and proves that fragment key by key before
  anything live is written. The live --check must predict exactly those bytes, against the reviewed
  registry and provider template. The intent records them, and --apply must produce exactly them, so
  resume and rollback always recognise the fragment.
- reload: the controller reports applied or no_change and a revision. `gc agent list --json`, which
  proves the on-disk composition, must resolve exactly gascity/operations-candidate-worker on
  claude-candidate, suspended, with cap 1, and the prompt bytes are proven.

No worker, route, rig resume, receipt, signer or Bead action. The candidate receipt and the unsuspend
belong to the first candidate window's own package. The gct-lagl step-3 items are a documented
assumption about Claude Code's sandbox (operator decision, 2026-09-24); see preroute.py.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preroute  # noqa: E402

STEPS = ("host", "inputs", "root", "checkout", "registry", "city", "render", "reload")
AGENT = "operations-candidate-worker"
PROMPT_NAME = "operations-candidate-prompt.template.md"
EXECUTOR = Path(__file__).resolve()
# The executor and every module it imports from this package; their digests are reviewed pins.
EXECUTOR_FILES = ("activate.py", "preroute.py", "candidate_git.py", "intake.py")
# Every file the candidate or signing lane executes or loads from the canonical Template checkout.
LANE_FILES = (
    "bin/gct-managed-rig-permissions", "bin/gct-claude-candidate-worker", "bin/gct-claude-signing-worker",
    "lib/gct_claude_candidate_worker.py", "lib/gct_claude_signing_worker.py", "lib/gct_claude_subscription.py",
    "templates/claude/candidate-control-policy.json", "templates/claude/candidate-provider.toml",
    "templates/claude/core-signing-control-policy.json", "templates/claude/signing-provider.toml",
    "templates/claude/managed-provider.toml",
)


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
        self.ops = Path(pins["ops"])
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
    prompt = property(lambda self: self.city / "managed" / PROMPT_NAME)
    suspension = property(lambda self: self.city / ".gc/runtime/suspension-state.json")


def run(argv, env, cwd="/", timeout=120, binary=False):
    try:
        result = subprocess.run(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                                text=not binary, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise Refusal(f"timed out after {timeout}s: {argv[:4]}") from exc
    return dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


GIT_ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_ATTR_NOSYSTEM": "1"}


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
        candidate = directory / f".{stem}.gct-lagl.{index}"
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
            found += sorted(str(p) for p in directory.glob(".*.gct-lagl.*"))
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
        body = dict(value, step=step, bead="ga-6utp", resumed=resumed, before=before, after=after, binding=self.binding)
        write_exclusive(self.record(step), (json.dumps(body, sort_keys=True, indent=1) + "\n").encode())
        print(json.dumps(dict(step=step, ok=True, resumed=resumed)))

    def pinned_input(self, name):
        raw = (self.inputs / name).read_bytes()
        require(digest(raw) == self.pins["inputs"][name], f"input digest drift: {name}")
        return raw


# ---------------------------------------------------------------- derivations (pure)

def candidate_record(profile: dict, python_toolchain: dict) -> dict:
    (record,) = [r for r in profile["rigs"] if r.get("provider") == "claude"]
    record = json.loads(json.dumps(record))
    require(record["git_metadata"] is False and record["agents"] == [AGENT], "unexpected candidate record")
    record["toolchains"] = [python_toolchain]
    return record


def new_registry(raw: bytes, record: dict) -> bytes:
    value = json.loads(raw)
    require(value["schema"] == "gc.managed-rig-permissions.v2", "registry schema")
    require(all(AGENT not in r["agents"] for r in value["rigs"]), "candidate already registered")
    require((json.dumps(value, indent=2) + "\n").encode() == raw, "registry is not in the live serialization")
    value["rigs"].append(json.loads(json.dumps(record, sort_keys=True)))
    return (json.dumps(value, indent=2) + "\n").encode()


def agent_block(prompt_path: Path) -> str:
    return (
        "\n# gct-lagl: Operations candidate worker, bound to the gascity rig only. The managed\n"
        "# fragment patches it onto the closed claude-candidate provider. It stays suspended\n"
        "# until the first candidate window's own reviewed package unsuspends it.\n"
        "[[agent]]\n"
        'dir = "gascity"\n'
        f'name = "{AGENT}"\n'
        'description = "Operations candidate worker: delivers an uncommitted candidate (gct-lagl)"\n'
        'provider = "claude"\n'
        f'prompt_template = "{prompt_path}"\n'
        "max_active_sessions = 1\n"
        "suspended = true\n"
    )


def new_city(raw: bytes, prompt_path: Path) -> bytes:
    text = raw.decode()
    require(AGENT not in text, "candidate agent already in city.toml")
    require(text.endswith("\n"), "city.toml must end with a newline")
    new = text + agent_block(prompt_path)
    agents = [a for a in tomllib.loads(new).get("agent", []) if a.get("name") == AGENT]
    require(len(agents) == 1 and agents[0]["dir"] == "gascity" and agents[0]["suspended"] is True
            and agents[0]["max_active_sessions"] == 1 and "session" not in agents[0], "derived city agent")
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
    # The record derives the socket and refuses TMUX_TMPDIR, GC_AGENT_SLICE and GC_SESSION in the
    # controller environment; gc must agree on the city name.
    process_record = shared(preroute.observe_city, Path(p.pins["user_slice"]), before["controller"], p.live.city)
    require(Path(process_record["tmux_socket"]).name == gc_city_name(p), "gc and the record disagree on the city name")
    require(not os.path.lexists(live.managed_settings), f"managed-policy settings present: {live.managed_settings}")
    require(not os.path.lexists(live.managed_mcp), f"managed MCP configuration present: {live.managed_mcp}")
    trust = json.loads(live.claude_json.read_text()) if live.claude_json.exists() else {}
    for project, entry in (trust.get("projects") or {}).items():
        if project == str(live.candidate_root) or project.startswith(str(live.candidate_root) + "/"):
            require(not entry.get("enabledMcpjsonServers") and not entry.get("enableAllProjectMcpServers")
                    and not entry.get("mcpServers"), f"project MCP servers approved for {project}")
    ops_entry = (trust.get("projects") or {}).get(str(live.ops)) or {}
    require(not ops_entry.get("enabledMcpjsonServers") and not ops_entry.get("enableAllProjectMcpServers")
            and not ops_entry.get("mcpServers"), "the Operations project entry approves MCP servers")
    current = live.ops / ".git"
    while True:
        require(Path(os.path.realpath(current)) == current and stat.S_ISDIR(current.lstat().st_mode),
                f"not a physical directory: {current}")
        if current == current.parent:
            break
        current = current.parent
    relative = git(live.ops, "config", "--get", "worktree.useRelativePaths")
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


def step_inputs(p: Package):
    before = p.begin("inputs")
    live = p.live
    require(sha(live.registry) == p.pins["registry_before"], "registry predecessor")
    require(sha(live.city_toml) == p.pins["city_before"], "city predecessor")
    prompt_raw = Path(p.pins["prompt_source"]).read_bytes()
    profile = json.loads(blob(live.template, p.pins["template_commit"],
                              "managed/profiles/gascity-operations-candidate-claude.json"))
    record = candidate_record(profile, p.pins["python_toolchain"])
    derived = {"rig-permissions.json": new_registry(live.registry.read_bytes(), record),
               "city.toml": new_city(live.city_toml.read_bytes(), live.prompt),
               PROMPT_NAME: prompt_raw}
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
    require(not os.path.lexists(root), "candidate root already exists")
    require(stat.S_ISDIR(root.parent.lstat().st_mode) and Path(os.path.realpath(root.parent)) == root.parent,
            "candidate root parent is not physical")
    p.intent("root", before)
    os.mkdir(root, 0o755)
    os.chmod(root, 0o755)
    require(root_postcondition(p), "candidate root postcondition")
    p.finish("root", before, dict(root=str(root)))


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
    # r10: ga-e0t1.15 S3 already moved the canonical checkout to cfd353f3, which contains PR 70. When the base is
    # the target the step only proves it: no git checkout runs, so the Template Git directory that M7 pins is
    # left untouched.
    if head != target:
        moved = git(p.live.template, "checkout", "--detach", target)
        require(moved["returncode"] == 0, "checkout failed: " + moved["stderr"])
    after_head, after_status = checkout_state(p)
    require(after_head == target and after_status == p.pins["template_status"], "checkout postcondition")
    p.finish("checkout", before, dict(before_commit=head, after_commit=target, lane_files=lane_files_match(p, target)))


def step_registry(p: Package):
    before = p.begin("registry")
    new = p.pinned_input("rig-permissions.json")
    require(identity(p.live.registry) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["registry_before"]),
            "registry predecessor identity")
    backup(p, p.live.registry, "rig-permissions.json")
    p.intent("registry", before)
    replace_atomic(p.live.registry, new, 0o644, p.live.uid)
    p.finish("registry", before, dict(after_sha256=digest(new)))


def step_city(p: Package):
    before = p.begin("city")
    new = p.pinned_input("city.toml")
    prompt = p.pinned_input(PROMPT_NAME)
    require(identity(p.live.city_toml) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["city_before"]),
            "city predecessor identity")
    require(not os.path.lexists(p.live.prompt), "prompt already exists")
    backup(p, p.live.city_toml, "city.toml")
    p.intent("city", before)
    replace_atomic(p.live.prompt, prompt, 0o644, p.live.uid)
    replace_atomic(p.live.city_toml, new, 0o644, p.live.uid)
    # Until render, the agent composes on the base provider; it must be suspended there.
    composed = listed_candidate(p)
    require(composed.get("suspended") is True, "candidate agent is not suspended after the city step")
    p.finish("city", before, dict(city_sha256=digest(new), prompt_sha256=digest(prompt), composed=composed))


def backup(p: Package, live_path: Path, name: str):
    target = p.root / "backups" / name
    target.parent.mkdir(mode=0o700, exist_ok=True)
    if not target.exists():
        write_exclusive(target, live_path.read_bytes(), 0o600)
    require(sha(target) == sha(live_path), f"backup of {name} differs from live")


def fragment_structure(p: Package, before_raw: bytes, after_raw: bytes) -> dict:
    """The rendered fragment adds exactly the reviewed candidate grant and changes nothing else."""
    old, new = tomllib.loads(before_raw.decode()), tomllib.loads(after_raw.decode())
    require({k: v for k, v in new.items() if k not in ("providers", "patches")}
            == {k: v for k, v in old.items() if k not in ("providers", "patches")}, "a non-provider table changed")
    require(set(new.get("patches", {})) == set(old.get("patches", {})) | {"agent"}, "patch table kinds changed")
    for kind, value in old.get("patches", {}).items():
        if kind != "agent":
            require(new["patches"][kind] == value, f"patch table {kind} changed")
    patches = {(a["dir"], a["name"]): a for a in new["patches"]["agent"]}
    old_patches = {(a["dir"], a["name"]): a for a in old.get("patches", {}).get("agent", [])}
    require(len(patches) == len(new["patches"]["agent"]), "duplicate agent patches in the new fragment")
    require(set(patches) - set(old_patches) == {("gascity", AGENT)}, "exactly one new agent patch")
    require(all(patches[k] == v for k, v in old_patches.items()), "an existing agent patch changed")
    for name, block in old.get("providers", {}).items():
        require(new["providers"].get(name) == block, f"existing provider {name} changed")
    require(set(new["providers"]) - set(old.get("providers", {})) == {"claude-candidate"}, "exactly one new provider")
    patch = patches[("gascity", AGENT)]
    require(set(patch) == {"dir", "name", "provider", "option_defaults", "env"}, f"candidate patch keys {sorted(patch)}")
    choice = patch["option_defaults"].get("managed_worktree_access")
    require(patch["provider"] == "claude-candidate" and patch["option_defaults"] == {
        "model": "opus-5-5", "permission_mode": "full-auto", "managed_worktree_access": choice},
        f"candidate patch option_defaults {patch['option_defaults']}")
    require(patch["env"] == {"PATH": p.pins["candidate_path"]}, "candidate patch env")
    template = tomllib.loads(blob(p.live.template, p.pins["template_commit"],
                                  "templates/claude/candidate-provider.toml").decode())["providers"]["claude-candidate"]
    provider = new["providers"]["claude-candidate"]
    require({k: v for k, v in provider.items() if k != "options_schema"}
            == {k: v for k, v in template.items() if k != "options_schema"}, "candidate provider body")
    require([o["key"] for o in provider["options_schema"]] == [o["key"] for o in template["options_schema"]],
            "candidate provider options")
    for got, want in zip(provider["options_schema"], template["options_schema"]):
        if got["key"] != "managed_worktree_access":
            require(got == want, f"candidate provider option {got['key']}")
            continue
        require({k: v for k, v in got.items() if k != "choices"} == {k: v for k, v in want.items() if k != "choices"}
                and got["choices"][: len(want["choices"])] == want["choices"]
                and len(got["choices"]) == len(want["choices"]) + 1, "candidate access option")
        granted = got["choices"][-1]
        policy = str(p.live.template / "templates/claude/candidate-control-policy.json")
        require(set(granted) == {"value", "label", "flag_args"} and granted["value"] == choice
                and granted["flag_args"] == ["--settings", policy, "--add-dir", str(p.live.candidate_root)],
                f"candidate grant {granted}")
    return dict(choice=choice)


def post_city_predecessors(p: Package) -> None:
    require(identity(p.live.registry) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"]["rig-permissions.json"]),
            "registry is not the reviewed postimage")
    require(identity(p.live.city_toml) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"]["city.toml"]),
            "city.toml is not the reviewed postimage")
    require(sha(p.live.prompt) == p.pins["inputs"][PROMPT_NAME], "prompt is not the reviewed bytes")


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


def step_render(p: Package):
    before = p.begin("render")
    require(identity(p.live.fragment) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["fragment_before"]),
            "fragment predecessor identity")
    post_city_predecessors(p)
    renderer = p.live.template / "bin/gct-managed-rig-permissions"
    require(sha(renderer) == p.pins["renderer_sha"], "renderer bytes")
    # The renderer may import lane files; prove them all again right before it runs.
    require(checkout_state(p) == (p.pins["template_commit"], p.pins["template_status"]), "checkout drifted")
    lanes = lane_files_match(p, p.pins["template_commit"])
    argv = ["/usr/bin/python3.12", "-I", "-B", str(renderer)]
    tail = ["--json", "--city", str(p.live.city)]
    scratch_raw = prerender(p, argv)
    structure = fragment_structure(p, p.live.fragment.read_bytes(), scratch_raw)
    checked = run(argv + ["--check"] + tail, p.live.env)
    report = json.loads(checked["stdout"] or "{}")
    expected = report.get("expected_sha256")
    provider_template = digest(blob(p.live.template, p.pins["template_commit"], "templates/claude/candidate-provider.toml"))
    require(checked["returncode"] == 4 and report.get("state") == "drift" and expected == digest(scratch_raw)
            and report.get("actual_sha256") == p.pins["fragment_before"]
            and report.get("registry_file_sha256") == p.pins["inputs"]["rig-permissions.json"]
            and (report.get("provider_template_sha256s") or {}).get("claude-candidate") == provider_template,
            "render check does not match the reviewed inputs; nothing written")
    backup(p, p.live.fragment, "rig-permissions.toml")
    # The intent records the expected bytes, so rollback recognizes them even if this step dies.
    p.intent("render", dict(before, expected_fragment_sha256=expected))
    applied = run(argv + ["--apply"] + tail, p.live.env)
    report = json.loads(applied["stdout"] or "{}")
    require(applied["returncode"] == 0 and report.get("actual_sha256") == expected == sha(p.live.fragment),
            "render apply did not produce the checked bytes")
    p.finish("render", before, dict(check=checked, apply=applied, fragment_sha256=expected, structure=structure,
                                    lane_files=lanes))


def listed_agents(p: Package) -> list[dict]:
    listed = run([p.live.gc, "--city", str(p.live.city), "agent", "list", "--json"], p.live.env, timeout=60)
    require(listed["returncode"] == 0, "gc agent list failed")
    value = json.loads(listed["stdout"])
    require(value.get("schema_version") == "1" and isinstance(value.get("agents"), list), "agent list shape")
    return [a for a in value["agents"] if a.get("name") == AGENT]


def listed_candidate(p: Package) -> dict:
    agents = listed_agents(p)
    require(len(agents) == 1, f"expected one candidate agent, found {len(agents)}")
    return agents[0]


def agent_proof(p: Package) -> dict:
    agent = listed_candidate(p)
    require(agent.get("qualified_name") == f"gascity/{AGENT}" and agent.get("dir") == "gascity",
            f"identity {agent.get('qualified_name')!r}")
    require(agent.get("provider") == "claude-candidate", f"provider {agent.get('provider')!r}")
    require(agent.get("suspended") is True, "agent is not suspended")
    require(agent.get("pool") == {"min": 0, "max": 1}, f"cap {agent.get('pool')}")
    require(sha(p.live.prompt) == p.pins["inputs"][PROMPT_NAME], "prompt bytes")
    return agent


def reload(p: Package) -> dict:
    reloaded = run([p.live.gc, "--city", str(p.live.city), "reload", "--json"], p.live.env, timeout=480)
    ack = json.loads(reloaded["stdout"] or "{}")
    require(reloaded["returncode"] == 0 and ack.get("ok") is True and ack.get("async") is False
            and ack.get("soft") is False and ack.get("outcome") in {"applied", "no_change"} and ack.get("revision"),
            f"reload acknowledgement {ack}")
    return ack


def step_reload(p: Package):
    before = p.begin("reload")
    post_city_predecessors(p)
    render = json.loads(p.record("render").read_text())
    require(sha(p.live.fragment) == render["fragment_sha256"], "fragment is not the recorded render")
    p.intent("reload", before)
    ack = reload(p)
    p.finish("reload", before, dict(reload=ack, agent=agent_proof(p)))


ACTIONS = {"host": step_host, "inputs": step_inputs, "root": step_root, "checkout": step_checkout,
           "registry": step_registry, "city": step_city, "render": step_render, "reload": step_reload}


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
        require(identity(p.live.registry) == (stat.S_IFREG, 0o644, p.live.uid, 1, p.pins["inputs"]["rig-permissions.json"]),
                "registry postcondition does not hold; inspect, then rollback")
    elif step == "city":
        post_city_predecessors(p)
        composed = listed_candidate(p)
        require(composed.get("suspended") is True, "candidate agent is not suspended after the city step")
        extra = dict(city_sha256=sha(p.live.city_toml), prompt_sha256=sha(p.live.prompt), composed=composed)
    elif step == "render":
        post_city_predecessors(p)
        expected = recorded["before"].get("expected_fragment_sha256")
        require(sha(p.live.fragment) == expected, "render postcondition does not hold; inspect, then rollback")
        # The structure was proven on exactly these bytes before the write; prove it again from the backup.
        backup = (p.root / "backups" / "rig-permissions.toml").read_bytes()
        require(digest(backup) == p.pins["fragment_before"], "backup rig-permissions.toml differs from its pin")
        structure = fragment_structure(p, backup, p.live.fragment.read_bytes())
        require(checkout_state(p) == (p.pins["template_commit"], p.pins["template_status"]), "checkout drifted")
        extra = dict(fragment_sha256=expected, structure=structure,
                     lane_files=lane_files_match(p, p.pins["template_commit"]))
    elif step == "reload":
        post_city_predecessors(p)
        require(sha(p.live.fragment) == json.loads(p.record("render").read_text())["fragment_sha256"],
                "fragment is not the recorded render")
        extra = dict(reload=reload(p), agent=agent_proof(p))
    p.finish(step, before, dict(extra, resumed_from_intent=True), resumed=True)


def rollback(p: Package):
    """Restore every changed live file from digest-verified backups; refuse on any foreign state."""
    require(os.path.isdir(p.records) and not os.path.lexists(p.records / "rollback.json"), "rollback state")
    require(any(p.records.glob("*.json")), "nothing recorded; there is nothing to roll back")
    # Every validation below comes before the first live write, so a refusal there changes nothing. A
    # refusal after the writes (checkout move, final proofs, reload, quiet) leaves a partial restore and no
    # record; rerunning rollback is idempotent over it.
    observed = p.quiet()
    require(not [q for q in p.leftovers() if ".tmp" in q or "gct-validate" in q],
            f"leftover temporaries: {p.leftovers()}")
    head, status = checkout_state(p)
    if (head, status) == (p.pins["template_commit"], p.pins["template_status"]):
        lane_files_match(p, p.pins["template_commit"])
    else:
        # A checkout interrupted before HEAD moved leaves a mixed tree; restoring it would need force,
        # restore or reset, which are not used here, so it is an explicit stop for a human.
        require((head, status) == (p.pins["template_before"], p.pins["template_status"]),
                "canonical Template checkout is neither the clean predecessor nor the reviewed target; "
                "stop and inspect by hand")
        lane_files_match(p, p.pins["template_before"])
    restores = []
    for name, live_path, pre, post in (
        ("rig-permissions.toml", p.live.fragment, p.pins["fragment_before"], None),
        ("city.toml", p.live.city_toml, p.pins["city_before"], p.pins["inputs"]["city.toml"]),
        ("rig-permissions.json", p.live.registry, p.pins["registry_before"], p.pins["inputs"]["rig-permissions.json"]),
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
    # After the restores city.toml is always its predecessor, so a present prompt is always moved aside.
    prompt = os.path.lexists(p.live.prompt)
    if prompt:
        require(sha(p.live.prompt) == p.pins["inputs"][PROMPT_NAME], "prompt is not the reviewed bytes; refusing")
    # Everything is validated; only now write.
    actions = []
    for name, live_path, raw in restores:
        replace_atomic(live_path, raw, 0o644, p.live.uid)
        actions.append(name)
    if prompt:
        os.rename(p.live.prompt, fresh_name(p.live.prompt.parent, PROMPT_NAME + ".rolled-back"))
        actions.append("prompt")
    if head != p.pins["template_before"]:
        moved = git(p.live.template, "checkout", "--detach", p.pins["template_before"])
        require(moved["returncode"] == 0, "checkout rollback failed: " + moved["stderr"])
        actions.append("checkout")
    require(checkout_state(p) == (p.pins["template_before"], p.pins["template_status"]),
            "canonical Template checkout is not the clean predecessor after rollback; stop and inspect by hand")
    lane_files_match(p, p.pins["template_before"])
    ack = reload(p)
    require(not listed_agents(p), "candidate agent still composed after rollback")
    after = p.quiet()
    require(after == observed, f"the city changed during rollback: {observed} -> {after}")
    value = dict(actions=actions, quiet=observed, quiet_after=after, reload=ack, leftovers=p.leftovers(),
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
