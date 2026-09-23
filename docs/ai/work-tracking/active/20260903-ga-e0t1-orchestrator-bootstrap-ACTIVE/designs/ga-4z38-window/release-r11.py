"""Deliver one coordinator release to the live ga-4z38 worker as gc mail, once, as a reviewed job.

The coordinator writes the release body, after its in-window reviews, to
~/.local/share/gas-city-staging/ga-4z38-window/release/<mode>-release.json. This job treats that file
as untrusted input: it validates every field against the live state, sends exactly one gc mail from
the human mailbox to the worker template lane, and reads the message Bead back. Modes:
- source: {schema ga-4z38.source-release.v1, task, session, base, startup_proof_sha256,
  gitignore_entries, reviews}. The startup proof digest must equal the worker's evidence file, and the
  .gitignore entries must be exactly the untracked paths git reports (root-anchored).
- signing: {schema ga-4z38.signing-release.v1, task, session, base, head, tree, reviews}. HEAD must be
  unchanged; the index must stage only the allowed paths with no unstaged or untracked change. The
  signer independently re-verifies the tree.
In both modes: the city is resumed and not yet suspended; exactly one open session exists for the
template and it is the named session; ga-4z38 is in_progress and assigned to that session.

Every gc and git call runs through the owned-phase runner with the support environment
(GIT_OPTIONAL_LOCKS=0). The output root is fixed per mode and created exclusively, so a release is
never sent twice. Uses the base active_epoch() identity check, valid while the worker is live.

Usage (through the source launcher): release-r11.py source|signing
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/window-base-r11.py')
BASE_SHA = 'cad1d660b872a352bce7e8c3c5bffda5ca7ac663a732575f48a3b7a9847926cd'
WINDOW = Path('/var/tmp/ga-4z38-window-20260923-r1')
INPUT = Path('/home/loucmane/.local/share/gas-city-staging/ga-4z38-window/release')
TASK = 'ga-4z38'
TEMPLATE = 'gascity/gc.implementation-worker'
BASE_COMMIT = 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88'
ALLOWED = {'internal/sling/cycle.go', 'internal/sling/cycle_test.go', 'internal/sling/sling_core_test.go', '.gitignore'}
KEYS = dict(source={'schema', 'task', 'session', 'base', 'startup_proof_sha256', 'gitignore_entries', 'reviews'},
            signing={'schema', 'task', 'session', 'base', 'head', 'tree', 'reviews'})


def load():
    fd = os.open(BASE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1
        raw = b''
        while chunk := os.read(fd, 65536):
            raw += chunk
        assert os.fstat(fd) == s and hashlib.sha256(raw).hexdigest() == BASE_SHA, 'base source drift'
    finally:
        os.close(fd)
    w = types.ModuleType('release_base')
    w.__file__ = str(BASE)
    exec(compile(raw, str(BASE), 'exec', dont_inherit=True), w.__dict__)
    return w


def hexdigest(value, size):
    return isinstance(value, str) and len(value) == size and all(c in '0123456789abcdef' for c in value)


def main():
    w = load()
    w.require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound source launcher required')
    w.read(Path(__file__), _SOURCE_SHA)
    w.require(len(sys.argv) == 2 and sys.argv[1] in KEYS, 'mode: source or signing')
    mode = sys.argv[1]
    b, o, owned = w.load_support()
    w.require((WINDOW/'suspension-city-resume-event.json').exists()
              and not (WINDOW/'suspension-city-suspend-intent.json').exists(), 'window is not live')
    w.ROOT = WINDOW
    w.active_epoch(o)
    raw = w.read(INPUT/(mode + '-release.json'))
    w.require(len(raw) < 8192, 'release input size')
    release = json.loads(raw)
    w.require(isinstance(release, dict) and set(release) == KEYS[mode], 'release fields')
    w.require(release['schema'] == 'ga-4z38.%s-release.v1' % mode and release['task'] == TASK
              and release['base'] == BASE_COMMIT, 'release identity')
    w.require(isinstance(release['reviews'], list) and len(release['reviews']) == 2
              and all(isinstance(r, str) and r for r in release['reviews']), 'release reviews')
    root = Path('/var/tmp/ga-4z38-%s-release-20260923-r1' % mode)
    root.mkdir(mode=0o700)
    w.ROOT = root
    w.save('input.json', dict(mode=mode, release=release, received=datetime.now(timezone.utc).isoformat()))

    def run(name, args, expected=(0,)):
        return w.phase(name, args, b, owned, expected=expected, timeout=90)
    sessions = json.loads(run('sessions', w.GC + ['session', 'list', '--json'])['stdout'])['sessions'] or []
    live = [s for s in sessions if s.get('template') == TEMPLATE and not s.get('closed')]
    w.require(len(live) == 1 and live[0]['id'] == release['session'], 'exactly the named worker session is live')
    identities = {live[0].get(k) for k in ('id', 'alias', 'name', 'session_name')} - {None, ''}
    [task] = json.loads(run('task', w.GC + ['--rig', 'gascity', 'bd', 'show', TASK, '--json'])['stdout'])
    w.require(task['status'] == 'in_progress' and task.get('assignee') in identities, 'task claimed by the session')
    git = ['/usr/bin/git', '-C', str(w.WORK)]
    status = run('git-status', git + ['status', '--porcelain=v1', '-z', '--untracked-files=all'])['stdout']
    records = [r for r in status.split('\0') if r]
    if mode == 'source':
        proof = w.read(w.WORK/'.gc/worker-evidence/ga-4z38/startup-proof.json')
        w.require(w.digest(proof) == release['startup_proof_sha256'], 'startup proof digest')
        w.require([r for r in records if not r.startswith('?? ')] == [], 'tracked change before source release')
        untracked = sorted('/' + r[3:] for r in records)
        entries = release['gitignore_entries']
        w.require(isinstance(entries, list) and sorted(entries) == untracked
                  and all(e.startswith('/.claude/') for e in entries), 'gitignore entries are exactly the untracked paths')
    else:
        head = run('git-head', git + ['rev-parse', 'HEAD'])['stdout'].strip()
        w.require(head == release['head'] == BASE_COMMIT and hexdigest(release['tree'], 40), 'signing head and tree')
        staged = run('git-staged-names', git + ['diff-index', '--cached', '--name-only', 'HEAD'])['stdout'].split()
        w.require(staged and set(staged) <= ALLOWED, 'staged paths')
        w.require(all(r[1] == ' ' and r[0] in 'MA' and r[3:] in ALLOWED for r in records), 'clean apart from staged paths')
    body = json.dumps(release, sort_keys=True, separators=(',', ':'))
    subject = '%s_RELEASE %s' % (mode.upper(), TASK)
    w.save('send-intent.json', dict(to=TEMPLATE, subject=subject, body=body))
    sent = json.loads(run('send', w.GC + ['mail', 'send', TEMPLATE, '-s', subject, '-m', body, '--notify', '--json'])['stdout'])
    w.require(sent.get('ok') is True and sent.get('count') == 1 and len(sent.get('messages') or []) == 1, 'one message sent')
    message = sent['messages'][0]['id']
    [bead] = json.loads(run('readback', w.GC + ['bd', 'show', message, '--json'])['stdout'])
    w.require(bead['id'] == message and body in [v for v in bead.values() if isinstance(v, str)],
              'message readback carries the exact body in one field')
    w.ROOT = WINDOW
    w.active_epoch(o)
    w.ROOT = root
    w.complete_containment()
    result = dict(ok=True, mode=mode, message=message, session=release['session'], notified=sent.get('notified'),
                  body_sha256=w.digest(body.encode()))
    w.save('result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
