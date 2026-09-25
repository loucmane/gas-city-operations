"""Round 2b r13: rebind the reviewed r12 package to the host epoch of the 2026-09-24 boot.

The host rebooted on 2026-09-24 (up 09:16 CEST) before FRESHEN, so the window never started. The r12 package
(f8c4dde9, two SOURCE_PASS reviews) is bound to the old boot's host epoch. The reboot also cleared /tmp,
which held the upstream sources the round 1/2 generators read, so r13 derives from the reviewed r12 blobs
in git instead, and changes nothing but the epoch:

1. Every r12 file of this package is read from the r12 commit object (`git show <R12>:<path>`), never
   from the working tree.
2. The six old-epoch sites get count-asserted substitutions (EPOCH below): the boot id, the core, signer
   and broker service epochs in window-base-r11.py host(), and the controller pid in window-base-r11.py
   (suspension status and reload trace), window-r11.py (reload trace) and route-chain-r1.py (reload
   event validation). The broker is socket-activated and inactive in this boot; nothing in the window
   uses it, so its epoch is the inactive one (MainPID 0, start 0), and any activation during the window
   is refused as epoch drift, like any other.
3. Digest propagation: every full SHA-256 of a changed file is replaced by its new digest in every other
   .py and .sh file of the package, repeated to a fixed point, so each pin (BASE_SHA, WINDOW_SHA,
   wrapper pins, module pins) names the rebound file. README.md is never rewritten.
4. Every other file keeps its r12 bytes.
5. One bounded disposition (after the r13 reviews): window-base-r11.py snapshot() compared the live host
   block with the P6 accepted host block, recorded on the old boot. approved_epoch_image() replaces the
   P6 host block with the live one only after host() has required the rebound epoch, and only when both
   blocks have exactly the same shape; pins, cache and protected trees stay compared exactly.
6. One provenance pin keeps its r12 value (PROVENANCE): ROUTE's BIND_SHA must equal the executor digest
   BIND recorded when it ran at r12. The hand-edited r13 files (HAND_EDITED) are never written.

Usage: python3 -B make_epoch_r13.py <package dir> [<output dir>]   (output defaults to the package dir)
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

R12 = 'f8c4dde9777fe4a8b48271b6d85be1f01701fc32'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
# Observed read-only on 2026-09-24 from the supervisor's own PID namespace (pid:[4026532223], shared with
# init): /proc/sys/kernel/random/boot_id; `systemctl --user show gascity-supervisor-home-42adab5d.service`
# (the observer's SERVICE); `systemctl show gas-city-managed-git-signerd.service` and
# `gas-city-privileged-provision.service`; `gc status --json` controller pid.
EPOCH = dict(boot='3f1f4534-ea17-4cb4-b2f2-a3f8bce1a8fa',
             core=('2331', '39708112'), signer=('2310', '39660502'), broker=('0', '0'), controller=2331)
SUBSTITUTIONS = {
    'window-base-r11.py': [
        ("        if dependency_image(approved_historical_image(prior)) != dependency_image(value):",
         "        if dependency_image(approved_epoch_image(approved_historical_image(prior), h)) != dependency_image(value):"),
        ("\ndef directories(o):", '''\ndef shape(value):\n    if isinstance(value, dict):\n        return {k: shape(v) for k, v in value.items()}\n    return type(value).__name__\n\ndef approved_epoch_image(prior, h):\n    # ga-4z38 r13 disposition, for independent review: the host rebooted on 2026-09-24 after the P6\n    # accepted snapshot, so the P6 host block records the old boot. host() has already required the\n    # live epoch (boot, and the core, signer and broker service epochs) to equal the rebound pins. The\n    # P6 host block is replaced by that verified live block only when both have exactly the same shape.\n    # Pins, cache and protected trees stay compared exactly as before. Never reuse this for fresh drift.\n    value=json.loads(json.dumps(prior))\n    require(shape(value['host']) == shape(h), 'host block shape drift')\n    value['host']=h\n    return value\n''' + "\ndef directories(o):"),
        ("require(h['host']['boot'] == 'f4e38c6a-bfc9-4532-a713-0497904c5b1a', 'boot drift')",
         "require(h['host']['boot'] == '%s', 'boot drift')" % EPOCH['boot']),
        ("[('core','3150812','84619011818'), ('signer','5550','208267863'), ('broker','2862577','77125780270')]",
         "[('core','%s','%s'), ('signer','%s','%s'), ('broker','%s','%s')]"
         % (EPOCH['core'] + EPOCH['signer'] + EPOCH['broker'])),
        ("value['controller']['pid']==3150812,", "value['controller']['pid']==%d," % EPOCH['controller']),
        ("require(newest['controller_pid']==3150812, 'controller trace epoch drift')",
         "require(newest['controller_pid']==%d, 'controller trace epoch drift')" % EPOCH['controller']),
    ],
    'window-r11.py': [
        ("w.require(newest['controller_pid']==3150812 and 0<=age<=120",
         "w.require(newest['controller_pid']==%d and 0<=age<=120" % EPOCH['controller']),
    ],
    'route-chain-r1.py': [
        ("require(cycle['controller_pid']==3150812 and cycle['config_revision']==revision",
         "require(cycle['controller_pid']==%d and cycle['config_revision']==revision" % EPOCH['controller']),
    ],
}
DIGEST = re.compile(r'[0-9a-f]{64}')
HAND_EDITED = {'README.md', 'test_round2a.py', 'test_round2b.py', 'proof/worker-env-proof.py',
               'generators/make_epoch_r13.py'}
# Provenance pins validate a record written by a job that already ran at r12, so they keep the r12 digest.
# BIND ran at r12 and recorded executor_sha256 = the r12 bind-task-r3.py digest in
# /var/tmp/ga-4z38-bind-20260923-r1/binding-intent.json; ROUTE requires that value exactly. The r13
# bind-task-r3.py and BIND.sh bytes are never executed (BIND is not repeated).
PROVENANCE = {'route-task-r5.py': {'591cf9b58cfa86d8cee18af4db8fbcf03408c8932dcb79f17e6c9096969149fa'}}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def r12_files():
    listing = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', WORKTREE, 'ls-tree', '-r', '-z', '--name-only',
                              R12, '--', PREFIX], capture_output=True, check=True).stdout.decode()
    files = {}
    for path in (p for p in listing.split('\0') if p):
        raw = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', WORKTREE, 'show', R12 + ':' + path],
                             capture_output=True, check=True).stdout
        files[path[len(PREFIX):]] = raw
    return files


def rebind(files):
    out = dict(files)
    for name, pairs in SUBSTITUTIONS.items():
        text = out[name].decode()
        for old, new in pairs:
            assert text.count(old) == 1, (name, old)
            text = text.replace(old, new)
        out[name] = text.encode()
    # Every digest a file has had (its r12 digest and each intermediate one) maps to its current digest.
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


def main(package, output=None):
    output = Path(output or package)
    files = r12_files()
    out = rebind(files)
    for name, raw in sorted(out.items()):
        target = output/name
        if name in HAND_EDITED and output == Path(package):
            continue  # r13 hand edits live only in the package; the generator never overwrites them
        if not target.exists() or target.read_bytes() != raw:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        if raw != files[name]:
            print(name, sha(raw))


if __name__ == '__main__':
    main(*sys.argv[1:])
