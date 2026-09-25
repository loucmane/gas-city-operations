"""Drain and close the one ga-gegx worker session after CONTAIN, then prove zero residue. Reviewed job.

The gct-m1wh attempt7 containment used the same supported sequence: after city-suspend and rig-suspend,
request a native drain, then close the exact session with `gc session close`. The worker may not be able
to acknowledge the drain from its sandbox (attempt7 could not reach Dolt), so the drain is best-effort
and bounded; the close is required.

Preconditions: scheduling is held, either by CONTAIN (the window's rig-suspend event exists) or by a
passing HOLD (a /var/tmp/ga-gegx-hold-*/result.json with ok); at most one open session exists for the
template. Steps, each through the owned-phase runner with the support environment (GIT_OPTIONAL_LOCKS=0):
1. Once only, guarded by the exclusive marker /var/tmp/ga-gegx-close-drain.requested:
   `gc runtime drain <id> --json` (any exit status), then up to 60 seconds of session-list polling.
2. `gc session close <id> --json` (must succeed), only while that session is still open.
3. Up to 120 seconds until: no open session for the template, no tmux session at all on the city
   server (every other agent stays suspended in this window), and no process whose argv names the
   worktree or whose cwd is inside it. The server is read with `list-sessions`, which a running server
   answers with exit 0 even when it holds no session; `list-panes -a` would answer "no current target"
   there (tmux 3.4, proof/tmux-probe.py; Core wrapError treats that answer as a live empty server).
   Exit 1 counts only for Core's no-server answers: no server running, error connecting to (no such
   file or connection refused), server exited unexpectedly.
4. The one tmux action, at most once per run: when no open session remains and the city tmux server is
   up with no session, `tmux -u -L city kill-server`. Core sets exit-empty off on every session create
   (internal/runtime/tmux/tmux.go ConfigureServer), so a server started by the worker's `new-session -c
   <worktree>` outlives the session with the worktree in its argv. Core's own `gc stop` ends the server
   the same way once sessions are drained (cmd/gc/cmd_stop.go TeardownServer, KillServer). The ga-5ot6
   R10 restore needed this by hand. An empty server holds no agent work, and scheduling is held.
Declared effect on the task: `gc session close` releases the work assigned to the closed session
(Core cmd/gc/cmd_session.go unclaimWorkAssignedToRetiredSessionBead, work_assignment.go
ReleaseWorkBead), so ga-gegx ends open, unassigned and still routed. Its task attempt is started, so no
new session can start for it (taskattempt). The coordinator's delivery closeout closes it after the
merge; before any later window the audit would stop on it, as it did on ga-y49e.
It never signals a process itself and never replays a lifecycle action. `gc session close --json`
emits JSONL; exactly one record must name the session. Each run uses a fresh timestamped root, so a
refusal can be followed by another run, which never repeats the drain. Identity is the base
active_epoch() check.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-gegx-window/window-base-r11.py')
BASE_SHA = '95b861c4edbcf9c4a405ea28b937e9940f3af382797b4a123c035abc82679970'
WINDOW = Path('/var/tmp/ga-gegx-window-20260925-r2')
VAR = Path('/var/tmp')
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
    drain = VAR/'ga-gegx-close-drain.requested'
    held = (WINDOW/'suspension-rig-suspend-event.json').exists()
    for result in sorted(VAR.glob('ga-gegx-hold-*/result.json')):
        held = held or json.loads(w.read(result)).get('ok') is True
    w.require(held, 'scheduling is not held (no CONTAIN rig-suspend event and no passing HOLD)')
    w.ROOT = WINDOW
    w.active_epoch(o)
    ROOT = VAR/('ga-gegx-close-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
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
    if session and not drain.exists():
        fd = os.open(drain, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(dict(root=str(ROOT), session=session['id']), out)
        try:
            run('drain', w.GC + ['runtime', 'drain', session['id'], '--json'], expected=ANY)
        except Exception as exc:  # recorded; the close below still runs
            w.save('drain-refused.json', dict(error=str(exc)[:1000]))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and session.get('state') not in ('stopped', 'asleep', 'drained', 'closed'):
            time.sleep(5)
            try:
                rows = open_sessions()
            except Exception as exc:  # recorded; the close below still runs
                w.save('drain-poll-refused-%d.json' % counter['n'], dict(error=str(exc)[:1000]))
                break
            session = rows[0] if rows else dict(session, state='closed')
        w.save('drain-observed.json', dict(state=session.get('state')))
    still = open_sessions()
    w.require(len(still) <= 1, 'more than one open worker session before close')
    if still:
        stdout = run('close', w.GC + ['session', 'close', still[0]['id'], '--json'])['stdout']
        records = [json.loads(line) for line in stdout.splitlines() if line.strip()]
        acks = [r for r in records if r.get('session_id') == still[0]['id']]
        w.require(len(acks) == 1 and acks[0].get('ok') is True, 'close not acknowledged')
    deadline = time.monotonic() + 120
    server_killed = False
    while True:
        remaining = open_sessions()
        listed = run('tmux', ['/usr/bin/tmux', '-u', '-L', 'city', 'list-sessions', '-F', '#{session_name}'],
                     expected=(0, 1))
        # Exit 1 counts only when no server answers (Core internal/runtime/tmux wrapError ErrNoServer).
        stderr = listed['stderr']
        w.require(listed['exit_code'] == 0 or 'no server running' in stderr or 'server exited unexpectedly' in stderr
                  or ('error connecting to' in stderr and ('No such file or directory' in stderr
                                                           or 'Connection refused' in stderr)),
                  'tmux listing failed')
        tmux_sessions = [s for s in listed['stdout'].split('\n') if s.strip()] if listed['exit_code'] == 0 else []
        if listed['exit_code'] == 0 and not remaining and not tmux_sessions and not server_killed:
            # An empty city server kept alive by exit-empty off: end it the way `gc stop` does.
            run('tmux-kill-server', ['/usr/bin/tmux', '-u', '-L', 'city', 'kill-server'])
            server_killed = True
            continue
        residue = processes(w.WORK)
        if not remaining and not tmux_sessions and not residue:
            break
        w.require(time.monotonic() < deadline, 'residue remains: sessions=%d tmux_sessions=%d processes=%d'
                  % (len(remaining), len(tmux_sessions), len(residue)))
        time.sleep(5)
    w.ROOT = WINDOW
    w.active_epoch(o)
    w.ROOT = ROOT
    w.complete_containment()
    result = dict(ok=True, closed_session=first[0]['id'] if first else None, open_sessions=0, city_tmux_sessions=0,
                  worktree_processes=0, tmux_server_killed=server_killed, signals_sent=False,
                  executor_sha256=_SOURCE_SHA)
    w.save('result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
