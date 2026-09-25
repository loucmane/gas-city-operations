"""Round 2b r14: rebind the reviewed r13 package to the rebuilt platform inspector and fresh roots.

OBSERVE refused on 2026-09-24 20:28Z: the r13 observers (observe-integrity-r11.py,
observe-terminal-r11.py) run the 09-20 inspector, whose binary embeds the pre-M5 manifest pin a6324753;
the live manifest is the M5-accepted 2d7eadce. The inspector was rebuilt from the reviewed builder at
BUILDER_COMMIT (inspector/inspector-build-r1.py, job INSPECTOR-BUILD) into NEW_BUILD. OBSERVE also created
the r13 integrity root, so that root cannot be reused.

1. Every r13 file is read from the r13 commit object, never from the working tree; the builder files added
   at BUILDER_COMMIT are carried unchanged.
2. Count-asserted substitutions (SUBSTITUTIONS): the inspector build path, the binary digest, the
   build-result digest and the entrypoint digest in both observers; the inspector digest in window-r11.py;
   and the integrity root name wherever it appears (both observers' callers, freshen-r11.py, window-r11.py,
   and the FRESHEN and OBSERVE wrappers).
3. Digest propagation to a fixed point, exactly as r13 (make_epoch_r13.py), with the same provenance pin:
   ROUTE's BIND_SHA keeps the digest BIND recorded at r12.
4. Every other file keeps its r13 bytes. README.md and the tests are hand-edited, never written here.

The build values are read from NEW_BUILD/build-result.json at generation time and must match the digests
given on the command line, so the generator never guesses a digest.

Usage: python3 -B make_epoch_r14.py <package dir> <binary-sha256> <build-result-sha256> [<output dir>]
(without an output dir it rewrites the package; with one it writes every generated and carried file there)
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

R13 = '28693e8c1b694db60f92b299f88860d74ae8f6a4'
BUILDER_COMMIT = 'b780161fd09af450a405980abe352e4ab9acf30d'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_BUILD = '/var/tmp/ga-y49e-platform-inspector-20260920-r1'
NEW_BUILD = '/var/tmp/ga-4z38-platform-inspector-20260924-r1'
OLD_BINARY = '77685c663383d7b61e61e41f5e833a90be19bbfecfd8d95dcabe868d30a06237'
OLD_RESULT = 'c79a3165ccfb3c35fd50a5a781f91b46755d67c27f94efb6c62cf230c946676a'
OLD_ENTRY = 'e9f1fa42cdd5120c97c21ba37b7ca20f5fd14d94282575e4a08b3e17c80fec35'
NEW_ENTRY = 'e5e9872f2b57d70c9fbde8e3d152978eaf9266453af67dbd1a82a4d1886b7ca3'
OLD_ROOT = '/var/tmp/ga-4z38-integrity-20260923-r1'
NEW_ROOT = '/var/tmp/ga-4z38-integrity-20260924-r2'
ROOT_FILES = ('observe-integrity-r11.py', 'freshen-r11.py', 'window-r11.py', 'operator/FRESHEN-1.sh',
              'operator/FRESHEN-2.sh', 'operator/FRESHEN-3.sh', 'operator/OBSERVE.sh')
OBSERVERS = ('observe-integrity-r11.py', 'observe-terminal-r11.py')
DIGEST = re.compile(r'[0-9a-f]{64}')
HAND_EDITED = {'README.md', 'test_round2a.py', 'test_round2b.py', 'proof/worker-env-proof.py',
               'generators/make_epoch_r13.py', 'generators/make_epoch_r14.py'}
PROVENANCE = {'route-task-r5.py': {'591cf9b58cfa86d8cee18af4db8fbcf03408c8932dcb79f17e6c9096969149fa'}}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', WORKTREE, *args],
                          capture_output=True, check=True).stdout


def files_at(commit):
    names = [p for p in git('ls-tree', '-r', '-z', '--name-only', commit, '--', PREFIX).decode().split('\0') if p]
    return {p[len(PREFIX):]: git('show', commit + ':' + p) for p in names}


def substitutions(binary, result):
    subs = {}
    for name in ROOT_FILES:
        subs.setdefault(name, []).append((OLD_ROOT, NEW_ROOT, None))
    for name in OBSERVERS:
        subs.setdefault(name, []).extend([(OLD_BUILD, NEW_BUILD, 1), (OLD_BINARY, binary, 1),
                                          (OLD_RESULT, result, 1), (OLD_ENTRY, NEW_ENTRY, 1)])
    subs.setdefault('window-r11.py', []).append((OLD_BINARY, binary, 1))
    return subs


def rebind(files, subs):
    out = dict(files)
    for name, pairs in subs.items():
        text = out[name].decode()
        for old, new, count in pairs:
            found = text.count(old)
            assert found >= 1 and (count is None or found == count), (name, old, found)
            text = text.replace(old, new)
        out[name] = text.encode()
    history = {name: {sha(raw)} for name, raw in files.items()}
    while True:
        for name, raw in out.items():
            history[name].add(sha(raw))
        renamed = {old: sha(out[n]) for n in out for old in history[n] if old != sha(out[n])}
        changed = False
        for name, raw in out.items():
            if not name.endswith(('.py', '.sh')) or name.startswith('generators/'):
                continue
            text = raw.decode()
            keep = PROVENANCE.get(name, set())
            new = DIGEST.sub(lambda m: m.group(0) if m.group(0) in keep else renamed.get(m.group(0), m.group(0)), text)
            if new != text:
                out[name] = new.encode()
                changed = True
        if not changed:
            return out


def main(package, binary, result, output=None):
    build = Path(NEW_BUILD)
    assert sha((build / 'platform-inspect').read_bytes()) == binary, 'binary digest mismatch'
    raw = (build / 'build-result.json').read_bytes()
    assert sha(raw) == result, 'build-result digest mismatch'
    record = json.loads(raw)
    assert record['binary_sha256'] == binary and record['entrypoint_sha256'] == NEW_ENTRY
    assert record['core_commit'] == '796d9a7a67c42294fdc467c107bb59b76e482301'
    assert record['core_tree'] == 'f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13'
    files = files_at(R13)
    added = {k: v for k, v in files_at(BUILDER_COMMIT).items() if k not in files}
    assert set(added) == {'inspector/inspector-build-r1.py', 'inspector/platform-inspect-main.go',
                          'operator/INSPECTOR-BUILD.sh'}, sorted(added)
    out = rebind(files, substitutions(binary, result))
    if output is not None:
        for name, data in sorted({**out, **added}.items()):
            if name in HAND_EDITED:
                continue
            target = Path(output) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return
    for name, data in sorted(out.items()):
        if name in HAND_EDITED:
            continue
        target = Path(package) / name
        if target.read_bytes() != data:
            target.write_bytes(data)
        if data != files[name]:
            print(name, sha(data))


if __name__ == '__main__':
    main(*sys.argv[1:])
