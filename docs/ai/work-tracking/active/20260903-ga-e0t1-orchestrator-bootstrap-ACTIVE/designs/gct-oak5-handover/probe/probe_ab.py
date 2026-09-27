"""gct-oak5 handover inventory probes A and B (Claude lane), a declared lower bound.

Probe A: does a Claude session start (the harness's own git) change the linked worktree's admin
files, and if the index changes, is it a stat-only rewrite (plan rule for the common snapshot)?
Probe B: under the live Template candidate policy, retargeted to a scratch root, is the pinned C2
test command permitted and sandboxed, does it import the worktree's code with the declared temp
paths, and is deleting the temp directory permitted?

The real wrapper cannot run here: it requires a direct child of the candidate root that is a linked
worktree of the canonical Template. So this runs the same Claude binary with the same launch flags
and the same policy bytes, with declared deviations (listed in the report): the directory grant
and Edit rules name the scratch root instead of the candidate root; the policy hooks are removed
(they would call gc against the live city); the five native control commands are removed from
permissions.allow and sandbox.excludedCommands, so every command the session can run is sandboxed
or refused; print mode (-p, stream-json) replaces the interactive session; and the real launch's
subscription authentication step is skipped (the auth-override environment refusal is mirrored).

Nothing here writes to the canonical Template (its policy file is read with O_NOATIME), the live
city or any store. The session itself writes normal Claude project and transcript state under
~/.claude and updates ~/.claude.json, as any Claude run does. --strict-mcp-config with no
--mcp-config starts no MCP server from the operator's configuration; the init event's server list
is recorded, and a non-empty local server list is flagged. The clone comes from GitHub. Codex
startup git is not probed here; the plan takes it from the gct-mbg6 window's byte-identical common
snapshot. Output: <stage>/report.json and the Claude stream in <stage>/claude-stream.jsonl.
Entry: source-launch.py <this file> <its sha256> <stage directory that must not exist>, from
operator/PROBE-AB.sh; main() takes the stage directory.
"""
import hashlib
import json
import os
import signal
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path

BASE = "3474abfaec255f7ea4266ce8aa35218afcfc89b0"
REMOTE = "https://github.com/loucmane/gas-city-template.git"
BRANCH = "codex/gct-oak5-probe"
CLAUDE = "/home/loucmane/gascity/bin/claude"
LIVE_POLICY = "/home/loucmane/gas-city-template/templates/claude/template-candidate-control-policy.json"
LIVE_POLICY_SHA = "6b2f160d4999781db17ddf117b482a9c20432032c1162fed453a06ba7376fec1"  # P12/P13 pin
CONTROL_COMMANDS = (
    "/home/loucmane/gascity/bin/gc hook --claim --json",
    "/home/loucmane/gascity/bin/gc runtime drain-ack",
    "/home/loucmane/gascity/bin/bd close *",
    "/home/loucmane/gascity/bin/bd show *",
    "/home/loucmane/gascity/bin/bd update *",
)
AUTH_OVERRIDE_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_USE_")
AUTH_OVERRIDE_NAMES = frozenset({
    "CLAUDE_CODE_API_KEY_HELPER", "CLAUDE_CODE_API_KEY_HELPER_TTL_MS", "CLAUDE_CODE_FORCE_API_LOGIN",
    "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR",
})
LIVE_ROOT = "/home/loucmane/gas-city-template-candidate-worktrees"
MODEL = "claude-opus-5-5"
TIMEOUT = 900
GIT = ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]

HELPER = '''"""Stable content digest over a set of files (gct-oak5 probe stand-in)."""

import hashlib
from pathlib import Path


def stable_digest(paths):
    """Return one sha256 over the sorted paths and their bytes."""
    digest = hashlib.sha256()
    for path in sorted(Path(item) for item in paths):
        digest.update(str(path).encode() + b"\\0" + path.read_bytes() + b"\\0")
    return digest.hexdigest()
'''

TEST = '''import sys
import tempfile
from pathlib import Path

from lib import gct_handover_digest as digest


def test_imports_worktree_code():
    assert Path(digest.__file__).resolve().is_relative_to(Path.cwd().resolve())


def test_isolation():
    assert sys.dont_write_bytecode
    assert Path(tempfile.gettempdir()).resolve() == (Path.cwd() / ".oak5-c2-tmp/tmp").resolve()


def test_digest(tmp_path):
    assert tmp_path.resolve().is_relative_to((Path.cwd() / ".oak5-c2-tmp/basetemp").resolve())
    item = tmp_path / "a"
    item.write_bytes(b"x")
    assert digest.stable_digest([item]) == digest.stable_digest([str(item)])


def test_leaves_read_only_entries(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "inner").write_bytes(b"y")
    (tmp_path / "ro").write_bytes(b"z")
    (tmp_path / "ro").chmod(0o444)
    locked.chmod(0o555)
'''


def test_command(worktree):
    return (
        f"/usr/bin/env PYTHONDONTWRITEBYTECODE=1 TMPDIR={worktree}/.oak5-c2-tmp/tmp "
        f"/usr/bin/python3.12 -m pytest -q -p no:cacheprovider "
        f"--basetemp={worktree}/.oak5-c2-tmp/basetemp tests/test_gct_handover_digest.py"
    )


COMMANDS = (
    "/usr/bin/mkdir -p .oak5-c2-tmp/tmp .oak5-c2-tmp/basetemp",
    None,  # the test command, filled per worktree
    "/usr/bin/chmod -R u+w -- .oak5-c2-tmp",
    "/usr/bin/rm -r -- .oak5-c2-tmp",
)


def prompt(commands):
    lines = [
        f"This is an inventory probe. Use the Bash tool to run exactly these {len(commands)} commands, one per",
        "call, in this order, each exactly as written, from the current directory. Do not run any",
        "other command, do not edit any file, and do not retry a refused command. After the last,",
        "reply with one line per command: its number, whether it ran or was refused, and its exit code.",
    ]
    for index, command in enumerate(commands, 1):
        lines.append(f"{index}. {command}")
    return "\n".join(lines)


def parse_index(raw):
    """Split a v2 or v3 index into (header, entries without stat data, extensions, checksum).

    v4 (path prefix compression) is refused. Truncation raises ValueError.
    """
    if raw[:4] != b"DIRC" or len(raw) < 32:
        raise ValueError("not an index")
    version, count = struct.unpack(">II", raw[4:12])
    if version not in (2, 3):
        raise ValueError(f"index version {version} not handled")
    pos = 12
    entries = []
    for _ in range(count):
        start = pos
        fixed = raw[pos:pos + 62]
        mode = struct.unpack(">I", fixed[24:28])[0]
        oid = fixed[40:60]
        flags = struct.unpack(">H", fixed[60:62])[0]
        pos += 62
        extended = b""
        if flags & 0x4000:
            if version < 3:
                raise ValueError("extended flag in a v2 index")
            extended = raw[pos:pos + 2]
            pos += 2
        end = raw.index(b"\0", pos, min(len(raw), pos + 4096))
        name = raw[pos:end]
        if (flags & 0xFFF) != min(len(name), 0xFFF):
            raise ValueError("entry name length does not match its flags")
        total = 62 + len(extended) + len(name)
        pos = start + total + (8 - total % 8)
        entries.append((name, mode, oid, flags, extended))
    extensions = []
    while pos < len(raw) - 20:
        sig = raw[pos:pos + 4]
        size = struct.unpack(">I", raw[pos + 4:pos + 8])[0]
        extensions.append((sig, raw[pos + 8:pos + 8 + size]))
        pos += 8 + size
    if pos != len(raw) - 20:
        raise ValueError("index trailer misaligned")
    return raw[:12], entries, extensions, raw[-20:]


def classify_index(before, after):
    if before == after:
        return "identical"
    try:
        hb, eb, xb, _ = parse_index(before)
        ha, ea, xa, _ = parse_index(after)
    except (ValueError, struct.error, IndexError) as exc:
        return f"unparsed: {exc}"
    if hb != ha:
        return "header changed"
    if eb != ea:
        return "entries changed"
    if xb != xa:
        return "extensions changed: " + ",".join(sorted({s.decode("latin-1") for s, _ in xb} ^ {s.decode("latin-1") for s, _ in xa}) or ["bytes"])
    return "stat-only"


def admin_state(admin):
    state = {}
    for dirpath, dirnames, filenames in os.walk(admin):
        dirnames.sort()
        for name in sorted(filenames):
            path = Path(dirpath) / name
            info = path.lstat()
            record = {"mode": oct(info.st_mode), "uid": info.st_uid, "size": info.st_size, "nlink": info.st_nlink}
            if stat.S_ISREG(info.st_mode):
                record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            state[str(path.relative_to(admin))] = record
    return state


def tree_state(worktree):
    state = {}
    for dirpath, dirnames, filenames in os.walk(worktree):
        for name in sorted(dirnames + filenames):
            path = Path(dirpath) / name
            info = path.lstat()
            record = {"mode": oct(info.st_mode)}
            if stat.S_ISREG(info.st_mode):
                record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif stat.S_ISLNK(info.st_mode):
                record["target"] = os.readlink(path)
            state[str(path.relative_to(worktree))] = record
        dirnames[:] = [d for d in dirnames if not (Path(dirpath) / d).is_symlink()]
    return state


def probe_policy(raw, root):
    text = raw.decode("utf-8")
    if text.count(LIVE_ROOT) != 2:
        raise RuntimeError(f"policy names the candidate root {text.count(LIVE_ROOT)} times, expected 2")
    policy = json.loads(text.replace(LIVE_ROOT, str(root)))
    if "hooks" not in policy:
        raise RuntimeError("policy has no hooks section to remove")
    del policy["hooks"]
    allow = [f"Bash({command})" for command in CONTROL_COMMANDS]
    if [e for e in policy["permissions"]["allow"] if e in allow] != allow:
        raise RuntimeError("policy allow list does not hold the five control commands")
    if policy["sandbox"]["excludedCommands"] != list(CONTROL_COMMANDS):
        raise RuntimeError("policy sandbox exclusions are not the five control commands")
    policy["permissions"]["allow"] = [e for e in policy["permissions"]["allow"] if e not in allow]
    policy["sandbox"]["excludedCommands"] = []
    return policy


def child_environment(parent):
    child = {}
    for name, value in parent.items():
        if name == "ANTHROPIC_API_KEY":
            continue
        if name.startswith(AUTH_OVERRIDE_PREFIXES) or name in AUTH_OVERRIDE_NAMES or name.startswith(("GC_", "BEADS_")):
            raise RuntimeError(f"refusing inherited variable {name}")
        child[name] = value
    return child


def run(argv, **kwargs):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=600, env=env, **kwargs)


def main(stage_arg):
    stage = Path(stage_arg)
    if stage.exists() or stage.is_symlink():
        raise SystemExit(f"stage already exists: {stage}")
    environment = child_environment(os.environ)
    stage.mkdir(mode=0o700, parents=False)
    report = {"schema": "gct-oak5.probe-ab.v1", "base": BASE, "stage": str(stage), "deviations": [
        "scratch root replaces the candidate root in --add-dir and the two Edit rules",
        "policy hooks removed",
        "print mode: -p with --output-format stream-json --verbose",
        "clone from GitHub, not a linked worktree of the canonical Template",
        "the five native control commands removed from permissions.allow and sandbox.excludedCommands",
        "subscription authentication step of the real launch skipped",
        "--strict-mcp-config with no --mcp-config: no MCP server from the operator configuration starts",
    ], "not_covered": [
        "codex startup git (taken from the gct-mbg6 window common snapshot instead)",
        "claim-time git (ResolveWorkBranch under gc hook --claim), removed with the control commands; the gct-mbg6 snapshot covers it for the same gc binary",
        "the plain rm -r failure on a read-only directory under the sandbox (the live run uses chmod first; the local test shows the failure)",
    ]}
    fd = os.open(LIVE_POLICY, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        with os.fdopen(fd, "rb", closefd=False) as handle:
            policy_raw = handle.read()
    finally:
        os.close(fd)
    report["live_policy_sha256"] = hashlib.sha256(policy_raw).hexdigest()
    if report["live_policy_sha256"] != LIVE_POLICY_SHA:
        raise SystemExit("live policy digest drift")

    run(GIT + ["clone", "--quiet", "--no-tags", "--single-branch", "--branch", "main", REMOTE, str(stage / "clone")])
    run(GIT + ["-C", str(stage / "clone"), "cat-file", "-e", BASE + "^{commit}"])
    root = stage / "root"
    root.mkdir(mode=0o755)
    worktree = root / "wt"
    run(GIT + ["-C", str(stage / "clone"), "worktree", "add", "--quiet", "-b", BRANCH, str(worktree), BASE])
    admin = stage / "clone/.git/worktrees/wt"
    (worktree / "lib/gct_handover_digest.py").write_text(HELPER)
    (worktree / "tests/test_gct_handover_digest.py").write_text(TEST)

    policy_path = stage / "probe-policy.json"
    policy_path.write_text(json.dumps(probe_policy(policy_raw, root), indent=1) + "\n")
    commands = [COMMANDS[0], test_command(worktree), *COMMANDS[2:]]
    report["commands"] = commands

    admin_before = admin_state(admin)
    git_before = admin_state(stage / "clone/.git")
    index_before = (admin / "index").read_bytes()
    tree_before = tree_state(worktree)

    argv = [CLAUDE, "--add-dir", str(root), "--permission-mode", "dontAsk", "--effort", "max",
            "--model", MODEL, "--setting-sources", "", "--settings", str(policy_path),
            "--strict-mcp-config",
            "-p", "--output-format", "stream-json", "--verbose", prompt(commands)]
    report["argv"] = argv[:-1] + ["<prompt>"]
    stream = stage / "claude-stream.jsonl"
    started = time.time()
    with open(stream, "wb") as out, open(stage / "claude-stderr.txt", "wb") as err:
        proc = subprocess.Popen(argv, cwd=worktree, env=environment, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err, start_new_session=True)
        try:
            report["claude_exit"] = proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            report["claude_exit"] = "timeout"
        finally:
            # Kill whatever is left in the session's process group on every path, before measuring.
            # Children that left the group (sandbox helpers) die with the oneshot unit's cgroup.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            time.sleep(2)
    report["seconds"] = round(time.time() - started, 1)

    admin_after = admin_state(admin)
    git_after = admin_state(stage / "clone/.git")
    index_after = (admin / "index").read_bytes()
    report["probe_a"] = {
        "scope": "the whole Claude session, startup included, not only startup",
        "index": classify_index(index_before, index_after),
        "admin_changed": sorted(k for k in set(admin_before) | set(admin_after) if admin_before.get(k) != admin_after.get(k)),
        "git_changed_outside_admin": sorted(
            k for k in set(git_before) | set(git_after)
            if git_before.get(k) != git_after.get(k) and not k.startswith("worktrees/wt/")),
        "admin_before": admin_before,
        "admin_after": admin_after,
    }
    tree_after = tree_state(worktree)
    report["tree_added"] = sorted(set(tree_after) - set(tree_before))
    report["tree_removed"] = sorted(set(tree_before) - set(tree_after))
    report["tree_changed"] = sorted(k for k in set(tree_before) & set(tree_after) if tree_before[k] != tree_after[k])

    calls, results = [], {}
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") or {}
        content_parts = message.get("content") if isinstance(message, dict) else None
        for part in content_parts if isinstance(content_parts, list) else []:
            if part.get("type") == "tool_use":
                calls.append({"id": part.get("id"), "tool": part.get("name"), "input": part.get("input")})
            elif part.get("type") == "tool_result":
                content = part.get("content")
                if isinstance(content, list):
                    content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                results[part.get("tool_use_id")] = {"is_error": bool(part.get("is_error")), "content": str(content)[:4000]}
        if event.get("type") == "system" and event.get("subtype") == "init":
            servers = event.get("mcp_servers") or []
            report["init_mcp_servers"] = servers
            report["local_mcp_servers_started"] = [
                s for s in servers if isinstance(s, dict) and not str(s.get("name", "")).startswith("claude.ai")]
        if event.get("type") == "result":
            report["final"] = {k: event.get(k) for k in ("subtype", "is_error", "result", "num_turns", "total_cost_usd")}
    report["tool_calls"] = [dict(call, result=results.get(call["id"])) for call in calls]
    executed = [c["input"].get("command") for c in calls if c["tool"] == "Bash" and isinstance(c.get("input"), dict)]
    report["probe_b"] = {
        "exact_commands_only": executed == commands,
        "sandbox_disable_requested": any(
            isinstance(c.get("input"), dict) and c["input"].get("dangerouslyDisableSandbox")
            for c in calls if c["tool"] == "Bash"),
        "sandboxed_by_inference": "with the control commands removed, a command outside the allow list can run under dontAsk only through autoAllowBashIfSandboxed",
        "temp_absent_after": not (worktree / ".oak5-c2-tmp").exists(),
        "no_bytecode": not any("__pycache__" in k or k.endswith(".pyc") for k in tree_after),
        "no_pytest_cache": not any(k.startswith(".pytest_cache") for k in tree_after),
    }
    (stage / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("claude_exit", "seconds", "probe_b", "tree_added", "tree_changed")}, sort_keys=True))
    print(json.dumps({"index": report["probe_a"]["index"], "admin_changed": report["probe_a"]["admin_changed"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
