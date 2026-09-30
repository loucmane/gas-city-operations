"""Read-only exact continuation capture after the restored failed ga-jcxb worker.

No chmod, ACL, transcript, config or service writes. Only a create-only evidence
directory is produced after the full historical comparison succeeds.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import types

D = Path("/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs")
SOURCE = D / "ga-e0t1-20-codex-permissions/permissions.py"
SOURCE_SHA = "b560e231944f54533e6dfa7150e791769d3f29996221a4b1e86362f052e0f442"
PRIOR = Path("/tmp/ga-jcxb-permission-capture-20260930-r1")
ROOT = Path("/tmp/ga-mb91-permission-capture-20260930-r1")
DAY = "/home/loucmane/.codex/sessions/2026/09/30"
TRANSCRIPT = DAY + "/rollout-2026-09-30T06-02-25-01a0f07a-5bfe-7082-9f37-d03b7217886f.jsonl"
TRANSCRIPT_SIZE = 914734


def pinned(path, digest):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_uid == 1000 and before.st_nlink == 1
        assert before.st_size < 2 << 20
        raw = os.read(fd, (2 << 20) + 1)
        assert len(raw) == before.st_size and before == os.fstat(fd) == Path(path).lstat()
        assert hashlib.sha256(raw).hexdigest() == digest
        return raw
    finally:
        os.close(fd)


def main():
    assert os.getuid() == os.geteuid() == 1000 and not os.path.lexists(ROOT)
    raw = pinned(SOURCE, SOURCE_SHA)
    m = types.ModuleType("permission_reader")
    m.__file__ = str(SOURCE)
    exec(compile(raw, str(SOURCE), "exec", dont_inherit=True), m.__dict__)
    old = json.loads(pinned(PRIOR / "images.json", "1c01117e466acc94faa41f764ea6a35a706f28b24ab5781810a900c838587684"))
    history = json.loads(pinned(PRIOR / "history.json", "38105b8429a71376ba7d0344a3f63328ac4d572ef51da88bbadfdafb652dfa72"))
    terminal = json.loads(pinned(Path("/var/tmp/ga-jcxb-terminal-20260930-r1/result.json"),
        "dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8"))
    assert all(terminal.get(k) is True for k in ("ok", "actual_host_verified",
        "terminal_suspension_endpoint_bound", "accepted_restoration_bound"))
    closed = json.loads(pinned(Path("/var/tmp/ga-jcxb-r1-close-20260930T041304Z/result.json"),
        "8f65d7d473dacdddbb6a6654f74c6d749346375bf47b3989f335ca229e3d656c"))
    assert closed == dict(ok=True, closed_session="ci-mzoxg", open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False,
        signals_sent=False, executor_sha256="fb7e9dd7221bdba1936eedd7ffc4482d0595486b3155cbb0c3c39479f144d7cb")
    prior_path = D / "ga-x2wz-c1-package/permissions-baseline.py"
    prior_raw = pinned(prior_path, "29b9e38fc676fa1e21a1ef94aa4b310f43bae5f0e268915eeba42a762aad3e15")
    previous = types.ModuleType("previous_permission_baseline")
    previous.__file__ = str(prior_path)
    exec(compile(prior_raw, str(prior_path), "exec", dont_inherit=True), previous.__dict__)
    older_path = D / "ga-1aa1-image-tool-r3/permissions-baseline.py"
    older_raw = pinned(older_path, "971f5ffde5be045624e7df8d0b3b10b3658d5b1d10c9b12e9c3a3fb3e4ccfd45")
    older = types.ModuleType("older_permission_baseline")
    older.__file__ = str(older_path)
    exec(compile(older_raw, str(older_path), "exec", dont_inherit=True), older.__dict__)
    latest_path = D / "ga-9olv-c1-package/permissions-baseline.py"
    latest_raw = pinned(latest_path, "4428d83183beb88fb1b321b124fb1514c11f7e861afb6cf5c24242e7990e5371")
    latest = types.ModuleType("latest_permission_baseline")
    latest.__file__ = str(latest_path)
    exec(compile(latest_raw, str(latest_path), "exec", dont_inherit=True), latest.__dict__)
    newest_path = D / "ga-rq5n-c1-package/permissions-baseline.py"
    newest_raw = pinned(newest_path, "470b0afc0cca1c55005f716676949e2a96f0dddd912be94fa5f3fd046bf1dc76")
    newest = types.ModuleType("newest_permission_baseline")
    newest.__file__ = str(newest_path)
    exec(compile(newest_raw, str(newest_path), "exec", dont_inherit=True), newest.__dict__)
    previous_successor_path = D / "ga-xyqo-c1-package/permissions-baseline.py"
    previous_successor_raw = pinned(previous_successor_path, "2074e4bf524d6c0e0e182970ac8c197f9734fc726e17029010121672610c0ccd")
    previous_successor = types.ModuleType("previous_successor_permission_baseline")
    previous_successor.__file__ = str(previous_successor_path)
    exec(compile(previous_successor_raw, str(previous_successor_path), "exec", dont_inherit=True), previous_successor.__dict__)
    last_path = D / "ga-5uc9-c1-package/permissions-baseline.py"
    last_raw = pinned(last_path, "a1e721390e3c2bcd31790f4bfe40e7b85af0b5df577334bf1ac644e97c395f04")
    last = types.ModuleType("last_permission_baseline")
    last.__file__ = str(last_path)
    exec(compile(last_raw, str(last_path), "exec"), last.__dict__)
    completed_path = D / "ga-goo5-c1-package/permissions-baseline.py"
    completed_raw = pinned(completed_path, "e655c6cb042f7ff44b3e71ae12cc4770eae8452010f2c44e2faf31e0e1280090")
    completed = types.ModuleType("completed_permission_baseline")
    completed.__file__ = str(completed_path)
    exec(compile(completed_raw, str(completed_path), "exec"), completed.__dict__)
    immediate_path = D / "ga-jcxb-c1-package/permissions-baseline.py"
    immediate_raw = pinned(immediate_path, "60c0b823051d51693e1898f266eea0aecea4a4d5a91c02e164e7a8b87e1ab9b5")
    immediate = types.ModuleType("immediate_permission_baseline")
    immediate.__file__ = str(immediate_path)
    exec(compile(immediate_raw, str(immediate_path), "exec"), immediate.__dict__)
    def observe(path, fd):
        if path == immediate.TRANSCRIPT:
            return immediate.completed_transcript_image(m, fd)
        if path == last.TRANSCRIPT:
            return last.completed_transcript_image(m, fd)
        if path == completed.TRANSCRIPT:
            return completed.completed_transcript_image(m, fd)
        if path == previous_successor.TRANSCRIPT:
            return previous_successor.completed_transcript_image(m, fd)
        if path == newest.TRANSCRIPT:
            return newest.completed_transcript_image(m, fd)
        if path == latest.TRANSCRIPT:
            return latest.completed_transcript_image(m, fd)
        if path == previous.TRANSCRIPT:
            return previous.completed_transcript_image(m, fd)
        if path == older.TRANSCRIPT:
            return older.completed_transcript_image(m, fd)
        return m.image(fd)
    entries = {}
    try:
        images = {}
        for path, before in old.items():
            fd = m.open_exact(path, directory=stat.S_ISDIR(before["stat"]["mode"]))
            entries[path] = fd
            observed = observe(path, fd)
            aligned = copy.deepcopy(observed)
            if path == DAY:
                assert aligned["stat"]["mtime_ns"] == aligned["stat"]["ctime_ns"] == 1790740946322072573
                for key in ("mtime_ns", "ctime_ns"):
                    aligned["stat"][key] = before["stat"][key]
            assert aligned == before, "historical permission drift: " + path
            images[path] = observed
        # Bind this completed worker transcript to its exact size and hash.
        # Both existing large transcript readers remain exact and unchanged.
        fd = m.open_exact(TRANSCRIPT)
        entries[TRANSCRIPT] = fd
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1
        assert before.st_uid == before.st_gid == 1000 and stat.S_IMODE(before.st_mode) == 0o600
        assert before.st_size == TRANSCRIPT_SIZE and not os.listxattr(fd)
        data = os.read(fd, TRANSCRIPT_SIZE + 1)
        assert len(data) == TRANSCRIPT_SIZE and os.fstat(fd) == before
        assert hashlib.sha256(data).hexdigest() == "1682f38779c6920b8d78b4a8645257fa79535d160b5ab4d0cbf98027e0c271c3"
        first = json.loads(data.split(b"\n", 1)[0])
        assert first["type"] == "session_meta"
        assert first["payload"]["id"] == "01a0f07a-5bfe-7082-9f37-d03b7217886f"
        assert first["payload"]["cwd"] == "/home/loucmane/gas-city-ops-candidate-worktrees/ga-jcxb"
        assert first["payload"]["model_provider"] == "openai" and first["payload"]["source"] == "cli"
        images[TRANSCRIPT] = dict(stat={k: getattr(before, "st_" + k) for k in m.FIELDS},
            xattrs={}, sha256=hashlib.sha256(data).hexdigest())
        current = {k: m.inventory("/home/loucmane/.codex/" + k) for k in ("rules", "sessions")}
        expected = copy.deepcopy(history)
        assert TRANSCRIPT not in expected["sessions"]
        expected["sessions"][DAY] = images[DAY]["stat"]
        expected["sessions"][TRANSCRIPT] = images[TRANSCRIPT]["stat"]
        assert current == expected, "unrelated inventory delta"
        for path, fd in entries.items():
            m.stable_identity(path, fd)
            if path != TRANSCRIPT:
                assert observe(path, fd) == images[path]
        assert current == {k: m.inventory("/home/loucmane/.codex/" + k) for k in ("rules", "sessions")}
        ROOT.mkdir(mode=0o700)
        m.save(ROOT, "images.json", images)
        m.save(ROOT, "history.json", current)
        m.save(ROOT, "result.json", dict(ok=True, completed_session="ci-mzoxg",
            only_added_path=TRANSCRIPT, only_changed_prior_path=DAY,
            allowed_prior_fields=["mtime_ns", "ctime_ns"], transcript_size=TRANSCRIPT_SIZE,
            transcript_sha256=images[TRANSCRIPT]["sha256"], permissions_changed=False,
            worker_launched=False, historical_entries_preserved=True))
        print(json.dumps(dict(ok=True, root=str(ROOT), permissions_changed=False,
            transcript_sha256=images[TRANSCRIPT]["sha256"])))
    finally:
        for fd in entries.values():
            os.close(fd)


if __name__ == "__main__":
    main()
