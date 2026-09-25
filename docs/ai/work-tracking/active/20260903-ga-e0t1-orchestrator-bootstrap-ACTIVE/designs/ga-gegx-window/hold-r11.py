"""Emergency scheduling hold for a stranded window. It never replays a lifecycle action and never restores.

The reviewed lifecycle refuses every further action once any suspension-*-failure.json or
suspension-*-refused-after.json exists in the window root (window-base-r11.py lifecycle guard), so
CONTAIN.sh cannot suspend after such a failure. The worst case is a city-resume whose command applied
but whose observation failed: the city stays resumed and the worker stays schedulable.

Stranded means any of: a suspension-*-failure.json or -refused-after.json record; a lifecycle intent
without its event (an exception after the command, or a killed job); any *-started.json without its
*-phase.json; or a CONTAIN-1.sh or CONTAIN-2.sh job that ended non-zero in the job runner's done
records (a lifecycle refusal before any intent, such as the active-epoch or lineage check, writes
nothing in the window root). In each of these states CONTAIN cannot complete the suspension.

This job exists only for those states, and it is best-effort so that it never blocks the one safety
action. It records the base active_epoch() identity check and `gc status --json` without requiring
either. It then runs the same two supported commands the lifecycle suspend actions use (`gc suspend
--json`, then `gc rig suspend gascity --json`, from suspension-lineage.py ACTIONS) for whatever is not
known to be suspended, accepting any exit status. It passes only if a final `gc status --json` shows
the city and the gascity rig suspended. Everything runs through the owned-phase runner, in a fresh
timestamped root, with the support environment (GIT_OPTIONAL_LOCKS=0). It writes nothing in the window
root, so every record there stays exact. Restoring the window afterwards needs a reviewed successor.
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
BASE_SHA = '1e807d4179dbe203a45e90770c9c113671b191cdd30b3d8ac43725278f672ecc'
WINDOW = Path('/var/tmp/ga-gegx-window-20260925-r2')
VAR = Path('/var/tmp')
DONE = Path('/home/loucmane/.local/share/gas-city-staging/jobs/done')
CONTAIN = tuple('designs/ga-gegx-window/operator/CONTAIN-%d.sh' % slot for slot in (1, 2))


def stranded(window, done):
    """Every record that shows CONTAIN cannot complete the suspension."""
    found = sorted(p.name for p in window.glob('suspension-*-failure.json'))
    found += sorted(p.name for p in window.glob('suspension-*-refused-after.json'))
    for intent in window.glob('suspension-*-intent.json'):
        if not (window/intent.name.replace('-intent.json', '-event.json')).exists():
            found.append(intent.name)
    for started in window.glob('*-started.json'):
        if not (window/started.name.replace('-started.json', '-phase.json')).exists():
            found.append(started.name)
    for record in sorted(done.glob('*.json')) if done.is_dir() else []:
        try:
            value = json.loads(record.read_text())
        except (OSError, ValueError):
            continue
        job = value.get('job') if isinstance(value, dict) else None
        if isinstance(job, dict) and str(job.get('wrapper', '')).endswith(CONTAIN) and value.get('exit') not in (0, None):
            found.append('runner:' + record.name)
    return sorted(set(found))


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
    w = types.ModuleType('hold_base')
    w.__file__ = str(BASE)
    exec(compile(raw, str(BASE), 'exec', dont_inherit=True), w.__dict__)
    return w


def main():
    w = load()
    w.require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound source launcher required')
    w.read(Path(__file__), _SOURCE_SHA)
    b, o, owned = w.load_support()
    w.ROOT = WINDOW
    w.require((WINDOW/'stage-consumed.json').exists(), 'no staged window to hold')
    records = stranded(WINDOW, DONE)
    w.require(records, 'hold is only for a stranded lifecycle; use CONTAIN')
    try:
        w.active_epoch(o)
        epoch = 'verified'
    except Exception as exc:  # recorded; the hold still acts
        epoch = 'refused: ' + str(exc)[:500]
    root = VAR/('ga-gegx-hold-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir(mode=0o700)
    w.ROOT = root
    w.save('intent.json', dict(executor_sha256=_SOURCE_SHA, stranded_records=records, lifecycle_replay=False,
                               epoch_before=epoch))
    ANY = tuple(range(256))

    def status(name, required):
        try:
            value = json.loads(w.phase(name, w.GC + ['status', '--json'], b, owned)['stdout'])
            w.require(value.get('ok') is True, 'status not ok')
            [rig] = [r for r in value['rigs'] if r['name'] == 'gascity']
            return value['suspended'] is True, rig['suspended'] is True
        except Exception:
            if required:
                raise
            return None, None
    city, rig = status('status-before', False)
    # City first (stop scheduling), then the rig. Each is attempted even if the other refused, with any
    # exit status; only the final status decides.
    attempts = {}
    for name, needed, argv in (('city-suspend', city is not True, w.GC + ['suspend', '--json']),
                               ('rig-suspend', rig is not True, w.GC + ['rig', 'suspend', 'gascity', '--json'])):
        if not needed:
            continue
        try:
            attempts[name] = w.phase(name, argv, b, owned, expected=ANY)['exit_code']
        except Exception as exc:
            attempts[name] = 'refused: ' + str(exc)[:500]
    w.save('attempts.json', attempts)
    # Poll the final status like the lifecycle barrier does: up to 30 seconds for both to read suspended.
    deadline = time.monotonic() + 30
    index = 0
    while True:
        final = status('status-after-%d' % index, True)
        if final == (True, True) or time.monotonic() >= deadline:
            break
        index += 1
        time.sleep(3)
    w.require(final == (True, True), 'hold did not suspend the city and rig')
    w.complete_containment()
    result = dict(ok=True, city_suspended=True, gascity_rig_suspended=True, stranded_records=records,
                  city_suspended_before=city, rig_suspended_before=rig, epoch_before=epoch,
                  window_root_written=False, restore_requires_reviewed_successor=True)
    w.save('result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
