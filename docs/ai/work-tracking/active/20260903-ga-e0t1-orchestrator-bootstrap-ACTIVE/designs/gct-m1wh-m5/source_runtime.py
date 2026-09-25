"""Load frozen helper sources into a private module graph; never load bytecode.

Import aliases exist only during compilation and are restored even on failure.
The returned modules retain explicit references to this private graph.
"""
import hashlib
import os
from pathlib import Path
import stat
import sys
import types

HERE = Path(__file__).parent
LEGACY = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/reports/ga-e0t1.14-rollout-r1/package-r4/resume-r4b/recovery-source-r2')
PINS = {
    'observe_recovery': 'f5357d222f0a2f7ceb9e1a830533f20a4868fe5f3beb247de335843b730bdd78',
    'build_manifest': '235f935513d7c8629fee7c8b63f2060a40015e20ab890a4bf592e9b54fd13a06',
    'prepare_short_artifacts': '486eecff8096c00d323d64d712a0ef487ded0a340abecf33558ce21ba933add1',
    'recovery_state': '288bea35d1b20f97bcb54db9298c6bb8eecdc8fc86a8d86cafbab0d3f7db4d9d',
    'recovery_native': 'ea05872ed62b44bc35330f9aa351f40dfdfb8dc7e49604fadf3ecd91f2531be0',
    'recovery_final': '87533c597d32e0e7ade474c606f50fc708bc4733632e97d364ca0dcf709e2a00',
    'recovery_controller': 'dcc78e45698ea9e7b345b06352a70334073de21b3f7e77dcf8d05e50432ec97d',
}


def source(path, expected=None):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise RuntimeError('source path alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
    try:
        before = os.fstat(fd)
        if not (stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o644
                and before.st_uid == before.st_gid == 1000 and before.st_nlink == 1
                and 0 < before.st_size <= 1024 * 1024):
            raise RuntimeError('source identity/mode/size')
        chunks = []
        while True:
            data = os.read(fd, 65536)
            if not data:
                break
            chunks.append(data)
            if sum(map(len, chunks)) > 1024 * 1024:
                raise RuntimeError('source grew')
        raw = b''.join(chunks)
        if before != os.fstat(fd) or len(raw) != before.st_size:
            raise RuntimeError('source changed while reading')
    finally:
        os.close(fd)
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise RuntimeError('source digest drift: ' + str(path))
    return raw, digest


def module(name, path, expected, aliases=None):
    raw, _ = source(path, expected)
    value = types.ModuleType(name)
    value.__file__ = str(path)
    absent = object()
    previous = {key: sys.modules.get(key, absent) for key in aliases or {}}
    try:
        sys.modules.update(aliases or {})
        exec(compile(raw, str(path), 'exec', dont_inherit=True, optimize=0), value.__dict__)
    finally:
        for key, old in previous.items():
            if old is absent:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = old
    return value


def legacy():
    graph = {}
    for name, digest in PINS.items():
        graph[name] = module(name, LEGACY / (name + '.py'), digest, graph)
    return graph
