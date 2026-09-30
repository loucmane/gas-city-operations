"""Read-only permission-history continuation for completed ga-5uc9.
Only create-only evidence beneath the named /tmp root is written.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import types

D = Path("/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs")
ROOT = Path("/tmp/ga-goo5-permission-capture-20260930-r1")
PRIOR = Path("/tmp/ga-e0t1-21-permission-capture-20260929-r1")
MONTH = "/home/loucmane/.codex/sessions/2026/09"
DAY = MONTH + "/30"
TRANSCRIPT = DAY + "/rollout-2026-09-30T02-06-40-01a0efa2-863e-73b2-af85-668e760270a5.jsonl"
TRANSCRIPT_SHA = "970154de8cabb57c5bc97d0b121033eaf8ff5c10abcf91a23499895c8dc4523b"
READERS = (
    ("ga-1aa1-image-tool-r3", "971f5ffde5be045624e7df8d0b3b10b3658d5b1d10c9b12e9c3a3fb3e4ccfd45"),
    ("ga-x2wz-c1-package", "29b9e38fc676fa1e21a1ef94aa4b310f43bae5f0e268915eeba42a762aad3e15"),
    ("ga-9olv-c1-package", "4428d83183beb88fb1b321b124fb1514c11f7e861afb6cf5c24242e7990e5371"),
    ("ga-rq5n-c1-package", "470b0afc0cca1c55005f716676949e2a96f0dddd912be94fa5f3fd046bf1dc76"),
    ("ga-xyqo-c1-package", "2074e4bf524d6c0e0e182970ac8c197f9734fc726e17029010121672610c0ccd"),
    ("ga-5uc9-c1-package", "a1e721390e3c2bcd31790f4bfe40e7b85af0b5df577334bf1ac644e97c395f04"),
)


def pinned(path, digest):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1
        assert s.st_size < 2 << 20
        raw = os.read(fd, (2 << 20) + 1)
        assert len(raw) == s.st_size and s == os.fstat(fd) == Path(path).lstat()
        assert hashlib.sha256(raw).hexdigest() == digest
        return raw
    finally:
        os.close(fd)


def module(path, digest):
    raw = pinned(path, digest)
    m = types.ModuleType(path.parent.name)
    m.__file__ = str(path)
    exec(compile(raw, str(path), "exec", dont_inherit=True), m.__dict__)
    return m


def main():
    assert os.getuid() == os.geteuid() == 1000 and not os.path.lexists(ROOT)
    m = module(D / "ga-e0t1-20-codex-permissions/permissions.py",
               "b560e231944f54533e6dfa7150e791769d3f29996221a4b1e86362f052e0f442")
    old = json.loads(pinned(PRIOR / "images.json", "a2f66984af301ae7e1b6447e5ab146ec58822c7d31f0cd0ef584459b9ea2f739"))
    history = json.loads(pinned(PRIOR / "history.json", "f80ab5820e393c3d5a9b862e0de38dc75dc96721366266e340b01951e23772a1"))
    terminal = json.loads(pinned(Path("/var/tmp/ga-5uc9-terminal-20260930-r1/result.json"),
        "dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8"))
    assert all(terminal.get(k) is True for k in ("ok", "actual_host_verified",
        "terminal_suspension_endpoint_bound", "accepted_restoration_bound"))
    closed = json.loads(pinned(Path("/var/tmp/ga-5uc9-r1-close-20260930T001616Z/result.json"),
        "8001c4ffa2892ba0ff8332c81afa4f0654f79988be0d04b48643ed73eb0cc782"))
    assert closed == dict(ok=True, closed_session="ci-f6fgu", open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False,
        signals_sent=False, executor_sha256="6f009bb1ac48fafcde113745b522aa3d71faf1f24fd5bbca180e8b573e9d72bb")
    readers = [module(D / name / "permissions-baseline.py", digest) for name, digest in READERS]
    assert len({r.TRANSCRIPT for r in readers}) == len(readers)

    def observe(path, fd):
        for reader in readers:
            if path == reader.TRANSCRIPT:
                return reader.completed_transcript_image(m, fd)
        return m.image(fd)

    entries = {}
    try:
        images = {}
        for path, before in old.items():
            fd = m.open_exact(path, directory=stat.S_ISDIR(before["stat"]["mode"]))
            entries[path] = fd
            actual = observe(path, fd)
            aligned = copy.deepcopy(actual)
            if path == MONTH:
                assert actual["stat"]["nlink"] == before["stat"]["nlink"] + 1
                assert actual["stat"]["mtime_ns"] == actual["stat"]["ctime_ns"] == 1790726801116744598
                for key in ("nlink", "mtime_ns", "ctime_ns"):
                    aligned["stat"][key] = before["stat"][key]
            assert aligned == before, "historical permission drift: " + path
            images[path] = actual
        assert DAY not in old and TRANSCRIPT not in old
        fd = m.open_exact(DAY, directory=True)
        entries[DAY] = fd
        image = m.image(fd)
        assert image["stat"]["mode"] == 0o40700 and image["stat"]["nlink"] == 2
        assert image["stat"]["mtime_ns"] == image["stat"]["ctime_ns"] == 1790726801116744598
        assert image["xattrs"] == {m.DEFAULT: m.PRIVATE.hex()}
        images[DAY] = image
        fd = m.open_exact(TRANSCRIPT)
        entries[TRANSCRIPT] = fd
        image = m.image(fd)
        assert image["stat"]["mode"] == 0o100600 and image["stat"]["size"] == 178998
        assert image["xattrs"] == {} and image["sha256"] == TRANSCRIPT_SHA
        os.lseek(fd, 0, os.SEEK_SET)
        data = os.read(fd, 178999)
        assert len(data) == 178998
        first = json.loads(data.split(b"\n", 1)[0])
        assert first["type"] == "session_meta"
        assert first["payload"]["id"] == "01a0efa2-863e-73b2-af85-668e760270a5"
        assert first["payload"]["cwd"] == "/home/loucmane/gas-city-ops-candidate-worktrees/ga-5uc9"
        assert first["payload"]["model_provider"] == "openai" and first["payload"]["source"] == "cli"
        images[TRANSCRIPT] = image
        current = {k: m.inventory("/home/loucmane/.codex/" + k) for k in ("rules", "sessions")}
        expected = copy.deepcopy(history)
        for path in (MONTH, DAY, TRANSCRIPT):
            expected["sessions"][path] = images[path]["stat"]
        assert current == expected, "unrelated inventory delta"
        for path, fd in entries.items():
            m.stable_identity(path, fd)
            assert observe(path, fd) == images[path], "capture race"
        assert current == {k: m.inventory("/home/loucmane/.codex/" + k) for k in ("rules", "sessions")}
        ROOT.mkdir(mode=0o700)
        m.save(ROOT, "images.json", images)
        m.save(ROOT, "history.json", current)
        m.save(ROOT, "result.json", dict(ok=True, completed_session="ci-f6fgu",
            added_paths=[DAY, TRANSCRIPT], changed_prior_path=MONTH,
            allowed_prior_fields=["nlink", "mtime_ns", "ctime_ns"],
            added_child_directory_count=1, transcript_size=178998,
            transcript_sha256=TRANSCRIPT_SHA, permissions_changed=False,
            worker_launched=False, historical_entries_preserved=True))
        print(json.dumps(dict(ok=True, root=str(ROOT), permissions_changed=False)))
    finally:
        for fd in entries.values():
            os.close(fd)


if __name__ == "__main__":
    main()
