"""Tests for the gct-oak5 probe A/B helpers (no provider launch, no network)."""
import hashlib
import importlib.util
import struct
import json
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("probe_ab", HERE / "probe_ab.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/nonexistent",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def git(*args, cwd):
    subprocess.run(["/usr/bin/git", "-c", "commit.gpgsign=false", *args], cwd=cwd, env=GIT_ENV,
                   check=True, capture_output=True)


@pytest.fixture
def linked(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    for name in ("a.txt", "lib/b.py", "tests/c.py"):
        path = repo / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(name)
    git("add", ".", cwd=repo)
    git("commit", "-q", "-m", "base", cwd=repo)
    worktree = tmp_path / "root" / "wt"
    worktree.parent.mkdir()
    git("worktree", "add", "-q", "-b", "probe", str(worktree), "main", cwd=repo)
    return worktree, repo / ".git/worktrees/wt/index"


def test_parse_real_index_round_trip(linked):
    _, index = linked
    header, entries, extensions, _ = probe.parse_index(index.read_bytes())
    assert [e[0] for e in entries] == [b"a.txt", b"lib/b.py", b"tests/c.py"]
    assert header[:4] == b"DIRC"


def test_identical(linked):
    _, index = linked
    raw = index.read_bytes()
    assert probe.classify_index(raw, raw) == "identical"


def test_stat_only_refresh(linked):
    worktree, index = linked
    before = index.read_bytes()
    target = worktree / "a.txt"
    stamp = target.stat().st_mtime_ns + 5_000_000_000
    os.utime(target, ns=(stamp, stamp))
    git("update-index", "--refresh", cwd=worktree)
    after = index.read_bytes()
    assert after != before
    assert probe.classify_index(before, after) == "stat-only"


def test_entry_change_is_not_stat_only(linked):
    worktree, index = linked
    before = index.read_bytes()
    (worktree / "a.txt").write_text("changed")
    git("add", "a.txt", cwd=worktree)
    assert probe.classify_index(before, index.read_bytes()) == "entries changed"


def test_v3_index_with_skip_worktree(linked):
    worktree, index = linked
    before = index.read_bytes()
    git("update-index", "--skip-worktree", "a.txt", cwd=worktree)
    after = index.read_bytes()
    assert after[4:8] == b"\x00\x00\x00\x03"
    _, entries, _, _ = probe.parse_index(after)
    assert [e[0] for e in entries] == [b"a.txt", b"lib/b.py", b"tests/c.py"]
    assert entries[0][4] != b""
    assert probe.classify_index(before, after) == "header changed"
    stamp = (worktree / "lib/b.py").stat().st_mtime_ns + 5_000_000_000
    os.utime(worktree / "lib/b.py", ns=(stamp, stamp))
    git("update-index", "--refresh", cwd=worktree)
    assert probe.classify_index(after, index.read_bytes()) == "stat-only"


def test_truncated_index_is_reported_not_raised(linked):
    _, index = linked
    raw = index.read_bytes()
    assert probe.classify_index(raw, raw[:40]).startswith("unparsed")
    assert probe.classify_index(raw, raw[:-30]).startswith("unparsed")


def with_extension(raw, payload):
    body = raw[:-20] + b"UNTR" + struct.pack(">I", len(payload)) + payload
    return body + hashlib.sha1(body).digest()


def test_extension_change_detected(linked):
    _, index = linked
    raw = index.read_bytes()
    _, _, extensions, _ = probe.parse_index(raw)
    assert [sig for sig, _ in extensions] == [b"TREE"]
    before = with_extension(raw, b"\x00-1 0\n")
    after = with_extension(raw, b"\x00-1 1\n")
    assert probe.classify_index(before, after) == "extensions changed: bytes"
    assert probe.classify_index(raw, before) == "extensions changed: UNTR"


def test_v4_index_is_unparsed(linked):
    _, index = linked
    raw = bytearray(index.read_bytes())
    raw[4:8] = struct.pack(">I", 4)
    assert probe.classify_index(index.read_bytes(), bytes(raw)).startswith("unparsed")


def test_name_length_mismatch_is_unparsed(linked):
    _, index = linked
    raw = bytearray(index.read_bytes())
    raw[12 + 60:12 + 62] = struct.pack(">H", 3)  # first entry is a.txt, length 5
    assert probe.classify_index(index.read_bytes(), bytes(raw)).startswith("unparsed")


def live_policy_bytes():
    fd = os.open(probe.LIVE_POLICY, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read()
    finally:
        os.close(fd)
    assert hashlib.sha256(raw).hexdigest() == probe.LIVE_POLICY_SHA
    return raw


def test_probe_policy_retargets_and_drops_hooks(tmp_path):
    raw = live_policy_bytes()
    policy = probe.probe_policy(raw, tmp_path)
    assert "hooks" not in policy
    text = json.dumps(policy)
    assert probe.LIVE_ROOT not in text
    assert f"Edit(/{tmp_path}/*/**)" in policy["permissions"]["allow"]
    assert f"Edit(/{tmp_path}/*/.git)" in policy["permissions"]["deny"]
    live = json.loads(raw)
    assert policy["sandbox"]["excludedCommands"] == []
    assert {k: v for k, v in policy["sandbox"].items() if k != "excludedCommands"} == {
        k: v for k, v in live["sandbox"].items() if k != "excludedCommands"}
    assert not any(e.startswith("Bash(") for e in policy["permissions"]["allow"])
    assert all(f"Bash({c})" not in text for c in probe.CONTROL_COMMANDS)
    assert policy["permissions"]["deny"] == [
        e.replace(probe.LIVE_ROOT, str(tmp_path)) for e in live["permissions"]["deny"]]


def test_probe_policy_refuses_unexpected_root_count(tmp_path):
    raw = live_policy_bytes().replace(probe.LIVE_ROOT.encode(), b"/elsewhere", 1)
    with pytest.raises(RuntimeError):
        probe.probe_policy(raw, tmp_path)


def test_child_environment():
    child = probe.child_environment({"PATH": "/usr/bin", "ANTHROPIC_API_KEY": "k", "HOME": "/h"})
    assert child == {"PATH": "/usr/bin", "HOME": "/h"}
    for name in ("ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK", "GC_CITY", "BEADS_DIR",
                 "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_API_KEY_HELPER"):
        with pytest.raises(RuntimeError):
            probe.child_environment({name: "x"})


def test_commands_and_prompt():
    command = probe.test_command("/w")
    assert command == ("/usr/bin/python3.12 -B -m pytest -q -p no:cacheprovider "
                       "--basetemp=/w/.oak5-c2-tmp/basetemp tests/test_gct_handover_digest.py")
    assert "=" not in command.split(" ", 1)[0] and "env" not in command
    text = probe.prompt([probe.COMMANDS[0], command, *probe.COMMANDS[2:]])
    assert "exactly these 5 commands" in text
    assert "1. /usr/bin/mkdir -p .oak5-c2-tmp/basetemp" in text
    assert "3. " + probe.TEMPDIR_COMMAND in text
    assert "4. /usr/bin/chmod -R u+w -- .oak5-c2-tmp" in text
    assert "5. /usr/bin/rm -r -- .oak5-c2-tmp" in text


def test_parse_stream_and_mcp_flag():
    lines = [
        json.dumps({"type": "system", "subtype": "init", "mcp_servers": [
            {"name": "claude.ai Gmail", "status": "connected"}, {"name": "aegis", "status": "connected"}]}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": [{"type": "text", "text": "denied"}]}]}}),
        "not json",
        json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "ok", "num_turns": 2}),
    ]
    calls, final, servers = probe.parse_stream(lines)
    assert calls == [{"id": "t1", "tool": "Bash", "input": {"command": "ls"}, "result": {"is_error": True, "content": "denied"}}]
    assert final["result"] == "ok"
    assert probe.local_servers(servers) == [{"name": "aegis", "status": "connected"}]
    assert probe.local_servers([{"name": "claude.ai Docs"}]) == []
    assert probe.local_servers([]) == []
    assert probe.local_servers(probe.parse_stream(lines[1:])[2]) == ["<no init event>"]


def test_wrapper_pins_this_probe():
    wrapper = (HERE.parent / "operator/PROBE-AB.sh").read_text()
    digest = hashlib.sha256((HERE / "probe_ab.py").read_bytes()).hexdigest()
    assert f"PROBE_SHA={digest}\n" in wrapper
    assert "STAGE=$S/probe-ab-r3\n" in wrapper


def test_seeded_test_passes_with_pinned_command(tmp_path):
    worktree = tmp_path / "wt"
    (worktree / "lib").mkdir(parents=True)
    (worktree / "tests").mkdir()
    (worktree / "lib/gct_handover_digest.py").write_text(probe.HELPER)
    (worktree / "tests/test_gct_handover_digest.py").write_text(probe.TEST)
    subprocess.run(["/usr/bin/mkdir", "-p", ".oak5-c2-tmp/basetemp"], cwd=worktree, check=True)
    result = subprocess.run(probe.test_command(worktree), shell=True, cwd=worktree, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout
    plain = subprocess.run(["/usr/bin/rm", "-r", "--", ".oak5-c2-tmp"], cwd=worktree, capture_output=True)
    assert plain.returncode != 0  # the read-only directory needs the chmod step first
    subprocess.run(["/usr/bin/chmod", "-R", "u+w", "--", ".oak5-c2-tmp"], cwd=worktree, check=True)
    subprocess.run(["/usr/bin/rm", "-r", "--", ".oak5-c2-tmp"], cwd=worktree, check=True)
    assert not (worktree / ".oak5-c2-tmp").exists()
    assert not any(p.name == "__pycache__" for p in worktree.rglob("*"))
