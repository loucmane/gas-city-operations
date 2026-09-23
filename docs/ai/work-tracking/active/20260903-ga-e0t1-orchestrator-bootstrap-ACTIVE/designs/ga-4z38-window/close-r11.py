"""Drain and close the one ga-4z38 worker session after CONTAIN, then prove zero residue. Reviewed job.

The gct-m1wh attempt7 containment used the same supported sequence: after city-suspend and rig-suspend,
request a native drain, then close the exact session with `gc session close`. The worker may not be able
to acknowledge the drain from its sandbox (attempt7 could not reach Dolt), so the drain is best-effort
and bounded; the close is required.

Preconditions: the window's rig-suspend event exists (CONTAIN completed), and at most one open session
exists for the template. Steps, each through the owned-phase runner with the support environment
(GIT_OPTIONAL_LOCKS=0):
1. `gc runtime drain <id> --json` (any exit status), then up to 60 seconds of session-list polling.
2. `gc session close <id> --json` (must succeed).
3. Up to 120 seconds until: no open session for the template, no city tmux pane for it, and no
   process whose argv names the worktree or whose cwd is inside it.
It never signals a process, never touches tmux directly, and never replays a lifecycle action. The
output root is fixed and created exclusively. Identity is the base active_epoch() check.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/window-base-r11.py')
BASE_SHA = 'cad1d660b872a352bce7e8c3c5bffda5ca7ac663a732575f48a3b7a9847926cd'
WINDOW = Path('/var/tmp/ga-4z38-window-20260923-r1')
ROOT = Path('/var/tmp/ga-4z38-close-20260923-r1')
TEMPLATE = 'gascity/gc.implementation-worker'
ANY = tuple(range(256))


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
    w = types.ModuleType('close_base')
    w.__file__ = str(BASE)
    exec(compile(raw, str(BASE), 'exec', dont_inherit=True), w.__dict__)
    return w


def processes(work):
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != 1000:
                continue
            argv = (proc/'cmdline').read_bytes().split(b'\0')
            try:
                cwd = os.readlink(proc/'cwd')
            except OSError:
                cwd = ''
            if any(str(work).encode() in arg for arg in argv) or cwd == str(work) or cwd.startswith(str(work) + '/'):
                found.append(dict(pid=int(proc.name), cwd=cwd))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return found


def main():
    w = load()
    w.require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound source launcher required')
    w.read(Path(__file__), _SOURCE_SHA)
    b, o, owned = w.load_support()
    w.require((WINDOW/'suspension-rig-suspend-event.json').exists(), 'CONTAIN has not completed')
    w.ROOT = WINDOW
    w.active_epoch(o)
    ROOT.mkdir(mode=0o700)
    w.ROOT = ROOT
    counter = {'n': 0}

    def run(name, args, expected=(0,)):
        counter['n'] += 1
        return w.phase('%02d-%s' % (counter['n'], name), args, b, owned, expected=expected, timeout=90)

    def open_sessions():
        rows = json.loads(run('sessions', w.GC + ['session', 'list', '--json'])['stdout'])['sessions'] or []
        return [s for s in rows if s.get('template') == TEMPLATE and not s.get('closed')]

    first = open_sessions()
    w.require(len(first) <= 1, 'more than one open worker session')
    session = first[0] if first else None
    w.save('session.json', dict(session=session))
    if session:
        run('drain', w.GC + ['runtime', 'drain', session['id'], '--json'], expected=ANY)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and session.get('state') not in ('stopped', 'asleep', 'drained', 'closed'):
            time.sleep(5)
            rows = open_sessions()
            session = rows[0] if rows else dict(session, state='closed')
        w.save('drain-observed.json', dict(state=session.get('state')))
        run('close', w.GC + ['session', 'close', first[0]['id'], '--json'])
    deadline = time.monotonic() + 120
    while True:
        remaining = open_sessions()
        panes = run('tmux', ['/usr/bin/tmux', '-L', 'city', 'list-panes', '-a', '-F', '#{session_name} #{pane_pid}'],
                    expected=(0, 1))['stdout'].split('\n')
        worker_panes = [p for p in panes if p.strip() and first and first[0].get('session_name')
                        and p.startswith(first[0]['session_name'] + ' ')]
        residue = processes(w.WORK)
        if not remaining and not worker_panes and not residue:
            break
        w.require(time.monotonic() < deadline, 'residue remains: sessions=%d panes=%d processes=%d'
                  % (len(remaining), len(worker_panes), len(residue)))
        time.sleep(5)
    w.ROOT = WINDOW
    w.active_epoch(o)
    w.ROOT = ROOT
    w.complete_containment()
    result = dict(ok=True, closed_session=first[0]['id'] if first else None, open_sessions=0, worker_panes=0,
                  worktree_processes=0, signals_sent=False)
    w.save('result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
