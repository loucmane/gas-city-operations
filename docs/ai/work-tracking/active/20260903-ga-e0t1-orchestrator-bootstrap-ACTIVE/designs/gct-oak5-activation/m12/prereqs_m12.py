"""M12 input prerequisite: the city-config source file. No live change.

  python3 -I -B prereqs_m12.py <manifest_candidate.py sha256>

Core's metadata-only adoption requires the managed file already installed (the A2 codex-choice
activation installed city.toml bdcec254) and a pinned source holding the same bytes. This writes reports/m12-inputs/city.toml exactly
once (O_EXCL, 0644) from the installed bytes, after proving the installed file and the M11 source that becomes the
predecessor backup. Rerunning after success refuses; if it is interrupted after the directory exists, inspect by hand.
"""
import hashlib
import os
from pathlib import Path
import stat
import sys
import types

HERE = Path(__file__).parent


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def exact(path, sha, mode):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        data = b''
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            data += chunk
        require(os.fstat(fd) == before and len(data) == before.st_size, 'read race: ' + str(path))
    finally:
        os.close(fd)
    require(stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode) == mode and before.st_uid == 1000
            and before.st_nlink == 1 and digest(data) == sha, 'unexpected bytes or authority: ' + str(path))
    return data


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    require(len(sys.argv) == 2 and len(sys.argv[1]) == 64, 'usage: prereqs_m12.py <candidate sha256>')
    raw = (HERE/'manifest_candidate.py').read_bytes()
    require(digest(raw) == sys.argv[1], 'manifest_candidate.py is not the reviewed candidate')
    m = types.ModuleType('m12_candidate'); m.__file__ = str(HERE/'manifest_candidate.py')
    exec(compile(raw, m.__file__, 'exec', dont_inherit=True), m.__dict__)
    data = exact(m.CITY_TOML, m.CITY_NEW, 0o644)
    exact(m.CITY_OLD_SOURCE, m.CITY_OLD, 0o644)
    target = Path(m.CITY_SOURCE)
    require(not os.path.lexists(target.parent), 'm12-inputs already exists; inspect by hand')
    os.mkdir(target.parent, 0o755)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(target, 0o644)
    exact(target, m.CITY_NEW, 0o644)
    print('{"ok": true, "source": "%s", "sha256": "%s"}' % (target, m.CITY_NEW))


if __name__ == '__main__':
    main()
