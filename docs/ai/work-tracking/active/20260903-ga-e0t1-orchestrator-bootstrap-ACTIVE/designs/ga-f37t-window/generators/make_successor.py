"""Successor s1: derive the ga-f37t window package from the reviewed ga-4z38 r14 package.

  python3 -B make_successor.py <output package dir>

ga-4z38 r14 (69cdc6b6, two SOURCE_PASS) reached TERMINAL on 2026-09-24, but its one-shot attempt
(session ci-gi0lh) never claimed and is consumed. ga-f37t is the fourth successor, with a fresh worktree
/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles at Core e6366b9e.

1. Every source is read from the r14 commit object (git blobs), never from a working tree.
2. Kept: every executable, operator wrapper and the worker brief. Dropped: README.md, the tests and the
   generators (their provenance chains are ga-4z38-specific; test_successor.py replaces them), and the
   INSPECTOR-BUILD wrapper and builder (the inspector is built; its path is reused).
3. RECONCILE is retargeted first (RECONCILE_SUBS): it holds ga-4z38, whose consumed attempt is session
   ci-gi0lh (state stale-session), instead of ga-y49e; ga-y49e (already blocked) is the unrelated
   predecessor that must stay exact.
4. Global identity substitutions (IDENTITY), in order, with the rebuilt inspector path protected.
5. Digest propagation to a fixed point, as in make_epoch_r13/r14. No provenance pin is kept: BIND runs
   again for ga-f37t, so ROUTE pins the new bind-task digest.
6. The PREP outputs pinned in window-base-r11.py still name the ga-4z38 prep; s2 re-pins them after the
   ga-f37t PREP job has run. s1 admits only PREP (its reviews name only operator/PREP.sh).
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

R14 = '69cdc6b6d5d32e61746c0b0e8f50cb66420ae882'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
DROP = ('README.md', 'test_prep.py', 'test_round2a.py', 'test_round2b.py', 'operator/INSPECTOR-BUILD.sh')
DROP_DIRS = ('generators/', 'inspector/')
PROTECT = '/var/tmp/ga-4z38-platform-inspector-20260924-r1'
PLACEHOLDER = '\x00INSPECTOR\x00'
NOTE_OLD = ("NOTE=('Failed-attempt hold 2026-09-23: session ci-b24ev failed-create on '\n"
            "      '2026-09-21 (the positional-prompt defect, since fixed and live through M5); '\n"
            "      'its native attempt remains permanently consumed. Fresh successor ga-4z38 owns '\n"
            "      'the remaining implementation proof. This task is blocked pending successor '\n")
NOTE_NEW = ("NOTE=('Failed-attempt hold 2026-09-25: session ci-gi0lh woke on 2026-09-24 and never '\n"
            "      'claimed; Core closed it stale (cause undetermined, no pane captured); '\n"
            "      'its native attempt remains permanently consumed. Fresh successor ga-f37t owns '\n"
            "      'the remaining implementation proof. This task is blocked pending successor '\n")
# Applied to reconcile-predecessor-r3.py before the global identity substitutions. PRED is a placeholder
# for the held predecessor, so the global ga-4z38 -> ga-f37t rename cannot touch it.
PRED = '\x00PRED\x00'
RECONCILE_SUBS = [
    ("(the ga-e0t1.14 hold) to ga-y49e, whose\nconsumed attempt",
     "(the ga-e0t1.14 hold) to ga-y49e; for the fourth\nsuccessor it holds " + PRED + " instead, whose consumed attempt", 1),
    (NOTE_OLD, NOTE_NEW.replace('ga-f37t', '\x00SUCC\x00'), 1),
    ("'This reviewed status-only reconciliation follows the ga-e0t1.14 precedent; '",
     "'This reviewed status-only reconciliation follows the ga-y49e precedent; '", 1),
    ("other=bead('ga-e0t1.14')", "other=bead('ga-y49e-HOLD')", 1),
    ("otherafter=bead('ga-e0t1.14')", "otherafter=bead('ga-y49e-HOLD')", 1),
    ("'ga-y49e'", "'" + PRED + "'", None),
    ('ga-y49e has no dependency edges', PRED + ' has no dependency edges', 1),
    ('No dependency edge names ga-y49e', 'No dependency edge names ' + PRED, 1),
    ("'ci-b24ev'", "'ci-gi0lh'", None),
    ("closed[0]['metadata']['state']=='failed-create'", "closed[0]['metadata']['state']=='stale-session'", 1),
    ("'/home/loucmane/gascity-core-worktrees/ga-y49e-typed-route-cycles'",
     "'/home/loucmane/gascity-core-worktrees/" + PRED + "-typed-route-cycles'", 1),
]
IDENTITY = [
    ('/designs/ga-4z38-window', '/designs/ga-f37t-window'),
    ('/gas-city-staging/ga-4z38-window', '/gas-city-staging/ga-f37t-window'),
    ('/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles',
     '/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles'),
    ('codex/ga-4z38-typed-route-cycles', 'codex/ga-f37t-typed-route-cycles'),
    ('/var/tmp/ga-4z38-', '/var/tmp/ga-f37t-'),
    ('ga-4z38', 'ga-f37t'),
]
DIGEST = re.compile(r'[0-9a-f]{64}')
# PREP pins the exact overlay it generates. The reviewed ga-4z38 overlay (5f3b60e1, written by the ga-4z38
# PREP job) differs from the ga-f37t one only in the worker's work_dir and the header comment, so the
# expected ga-f37t overlay is derived from those bytes and its digest replaces OVERLAY_SHA.
OLD_OVERLAY = Path('/var/tmp/ga-4z38-prep-20260923-r2/city.isolated.toml')
OLD_OVERLAY_SHA = '5f3b60e1c1e391b5a1f66de62a2e767ea226570ce7549c6dfb526cd072e6530d'
OVERLAY_SUBS = [
    (b'\n# ga-4z38 bounded one-worker window; restore exact preserved baseline.\n',
     b'\n# ga-f37t bounded one-worker window; restore exact preserved baseline.\n'),
    (b'work_dir = "/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles"\n',
     b'work_dir = "/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles"\n'),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def successor_overlay():
    import tomllib
    raw = OLD_OVERLAY.read_bytes()
    assert sha(raw) == OLD_OVERLAY_SHA, 'reviewed ga-4z38 overlay drift'
    for old, new in OVERLAY_SUBS:
        assert raw.count(old) == 1, old
        raw = raw.replace(old, new)
    assert b'ga-4z38' not in raw
    tomllib.loads(raw.decode())
    return raw


def git(*args):
    return subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', WORKTREE, *args],
                          capture_output=True, check=True).stdout


def sources():
    names = [p for p in git('ls-tree', '-r', '-z', '--name-only', R14, '--', PREFIX).decode().split('\0') if p]
    out = {}
    for path in names:
        name = path[len(PREFIX):]
        if name in DROP or name.startswith(DROP_DIRS):
            continue
        out[name] = git('show', R14 + ':' + path)
    return out


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = raw.decode()
        if name == 'reconcile-predecessor-r3.py':
            for old, new, count in RECONCILE_SUBS:
                found = text.count(old)
                assert found >= 1 and (count is None or found == count), (name, old[:60], found)
                text = text.replace(old, new)
        text = text.replace(PROTECT, PLACEHOLDER)
        for old, new in IDENTITY:
            text = text.replace(old, new)
        text = (text.replace(PLACEHOLDER, PROTECT).replace(PRED, 'ga-4z38')
                .replace('\x00SUCC\x00', 'ga-f37t').replace('ga-y49e-HOLD', 'ga-y49e'))
        if name == 'prep-r11.py':
            overlay = sha(successor_overlay())
            for old, new in (("OVERLAY_SHA = '%s'" % OLD_OVERLAY_SHA, "OVERLAY_SHA = '%s'" % overlay),
                             ("'overlay bytes differ from the reviewed 5f3b60e1'",
                              "'overlay bytes differ from the derived %s'" % overlay[:8])):
                assert text.count(old) == 1, old
                text = text.replace(old, new)
        out[name] = text.encode()
    history = {name: {sha(raw)} for name, raw in files.items()}
    while True:
        for name, raw in out.items():
            history[name].add(sha(raw))
        renamed = {old: sha(out[n]) for n in out for old in history[n] if old != sha(out[n])}
        changed = False
        for name, raw in out.items():
            if not name.endswith(('.py', '.sh')):
                continue
            text = raw.decode()
            new = DIGEST.sub(lambda m: renamed.get(m.group(0), m.group(0)), text)
            if new != text:
                out[name] = new.encode()
                changed = True
        if not changed:
            return out


def main(output):
    files = sources()
    out = rebind(files)
    root = Path(output)
    for name, data in sorted(out.items()):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(len(out), 'files written to', root)


if __name__ == '__main__':
    main(*sys.argv[1:])
