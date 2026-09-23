"""Emergency scheduling hold for a stranded window. It never replays a lifecycle action and never restores.

The reviewed lifecycle refuses every further action once any suspension-*-failure.json or
suspension-*-refused-after.json exists in the window root (window-base-r11.py lifecycle guard), so
CONTAIN.sh cannot suspend after such a failure. The worst case is a city-resume whose command applied
but whose observation failed: the city stays resumed and the worker stays schedulable.

This job exists only for that state. It runs the same two supported commands the lifecycle suspend
actions use (`gc suspend --json`, then `gc rig suspend gascity --json`, from suspension-lineage.py
ACTIONS) through the owned-phase runner, in a fresh timestamped root, with the support environment
(GIT_OPTIONAL_LOCKS=0). It checks `gc status --json` before and after, and requires the city and the
gascity rig to be suspended at the end. It uses the base active_epoch() identity check, which is valid
while a worker is live. It writes nothing in the window root, so every refusal record there stays
exact. Restoring the window afterwards needs a reviewed successor.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/window-base-r11.py')
BASE_SHA = 'cad1d660b872a352bce7e8c3c5bffda5ca7ac663a732575f48a3b7a9847926cd'
WINDOW = Path('/var/tmp/ga-4z38-window-20260923-r1')


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
    stranded = sorted(p.name for p in WINDOW.glob('suspension-*-failure.json')) + \
        sorted(p.name for p in WINDOW.glob('suspension-*-refused-after.json'))
    w.require(stranded, 'hold is only for a stranded lifecycle; use CONTAIN.sh')
    w.active_epoch(o)
    root = Path('/var/tmp/ga-4z38-hold-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir(mode=0o700)
    w.ROOT = root
    w.save('intent.json', dict(executor_sha256=_SOURCE_SHA, stranded_records=stranded, lifecycle_replay=False))

    def status(name):
        return json.loads(w.phase(name, w.GC + ['status', '--json'], b, owned)['stdout'])
    before = status('status-before')
    [rig] = [r for r in before['rigs'] if r['name'] == 'gascity']
    # Suspend only what is still resumed: city first (stop scheduling), then the rig.
    if before['suspended'] is not True:
        w.phase('city-suspend', w.GC + ['suspend', '--json'], b, owned)
    if rig['suspended'] is not True:
        w.phase('rig-suspend', w.GC + ['rig', 'suspend', 'gascity', '--json'], b, owned)
    after = status('status-after')
    [rig] = [r for r in after['rigs'] if r['name'] == 'gascity']
    w.require(after['suspended'] is True and rig['suspended'] is True, 'hold did not suspend the city and rig')
    w.ROOT = WINDOW
    w.active_epoch(o)
    w.ROOT = root
    w.complete_containment()
    result = dict(ok=True, city_suspended=True, gascity_rig_suspended=True, stranded_records=stranded,
                  city_suspended_before=before.get('suspended'), window_root_written=False,
                  restore_requires_reviewed_successor=True)
    w.save('result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
