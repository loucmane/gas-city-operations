"""ga-f37t s7 recovery: return the city to its accepted image after the s6 r5 window stopped, once.

The window in STOPPED_ROOT staged the city (city.toml and receipt), resumed, and its worker never received
its task. CONTAIN-1 suspended the city and ran rig-suspend, but its status observation was partial, so the
lifecycle is stranded; HOLD-1 confirmed the city and the gascity rig suspended, CLOSE-1 left no session, tmux
server or worktree process, and the window stopped before ADMIT, so the reviewed RESTORE cannot run. This job
checks that exact recorded state, then performs the window's own restore transition (window-base transition
direction 0): the confined city.toml restore, a reload (applied or no_change at the accepted revision, then a
trace wait for it), and the confined receipt check, apply and verify back to the accepted receipt. It records
the recovered city.toml, receipt and suspension-state pins for the next successor's admission, then makes
ordinary reads of the start-gate objects and the route files. It writes no suspension state, route or Bead
and starts no worker.
"""
import copy
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import stat
import sys
import time
import types

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-f37t-window')
BASE_SHA = 'ea03593f4e764a6e4667b80d62a65f4af73b8dca82f4c9f411c705cb3d58430e'
ROUTES_SHA = '8d041af74297b44c0bedecdbcaa776ac92f433eba801afa0ee0a89a71eecc7c2'
STOPPED_ROOT = Path('/var/tmp/ga-f37t-window-20260925-r2')
ROOT = Path('/var/tmp/ga-f37t-recover-20260925-r2')
HOLD_RESULT = Path('/var/tmp/ga-f37t-hold-20260925T095013Z/result.json')
CLOSE_RESULT = Path('/var/tmp/ga-f37t-close-20260925T095042Z/result.json')
LISTING_SHA = '4fdd196ad8619e7b08ec570a538ac4b9d10280cfbba7e7d09ea37342ac24da8c'
STAGE_PASS_SHA = '6bb8e83a4eda116261f2868c93fb6a7ab677fffea41385510028dbe2097e19c1'
BASELINE_SHA = '771107c0d53eed26780fe63f4f2311849b54a1d373e9d12770633e2348d4c137'
BEFORE_SHA = '06a5a3bf05e0ae965804e46bc67aa24c3f345adeb6c328dbc2916e9f055d3f99'
FAILURE_SHA = 'b332d55fd11fbdc035435cb068d960a7d262dbae70f4d5ed562220219be29a6a'
HOLD_SHA = '40b8a9bb4f52b28aa7bf58794df96ae59de186681b0dfcdf5310038836e2a52d'
CLOSE_SHA = 'c31cc0864cf6a943ac673fdc995a84802c882d2fdefe8a6d436bcbb6509e833e'


def load(path, expected, name):
    assert path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1 and s.st_size <= 1024 * 1024
        raw = b''
        while chunk := os.read(fd, 65536):
            raw += chunk
        assert os.fstat(fd) == s and len(raw) == s.st_size and hashlib.sha256(raw).hexdigest() == expected
    finally:
        os.close(fd)
    m = types.ModuleType(name)
    m.__file__ = str(path)
    sys.modules[name] = m
    exec(compile(raw, str(path), 'exec', dont_inherit=True), m.__dict__)
    return m


def without_atime(record):
    value = json.loads(json.dumps(record))
    value['pin']['metadata'].pop('atime_ns')
    return value


def main():
    assert globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000
    w = load(HERE / 'window-base-r11.py', BASE_SHA, 'recovery2_base')
    routes = load(HERE / 'restore-r9-routes-r3.py', ROUTES_SHA, 'recovery2_routes')
    w.read(Path(__file__), _SOURCE_SHA)
    b, o, owned = w.load_support()
    w.pins()
    s = w.module(HERE / 'suspension-lineage.py', w.LINEAGE_SHA)
    # 1. The stopped window root, HOLD and CLOSE hold exactly the recorded stop.
    names = sorted(os.listdir(STOPPED_ROOT))
    w.require(hashlib.sha256('\n'.join(names).encode()).hexdigest() == LISTING_SHA, 'stopped window root contents')
    w.require(not any(n.startswith(('restore-', 'restored')) for n in names), 'restore already attempted')
    w.require(json.loads(w.read(STOPPED_ROOT / 'stage-pass.json', STAGE_PASS_SHA)) == dict(ok=True, worker_launched=False),
              'stage record')
    w.require(json.loads(w.read(STOPPED_ROOT / 'suspension-rig-suspend-failure.json', FAILURE_SHA))
              == dict(automatic_replay=False, error='incomplete/wrong-controller suspension observation'),
              'stranded rig-suspend record')
    before = json.loads(w.read(STOPPED_ROOT / 'before.json', BEFORE_SHA))
    baseline = json.loads(w.read(STOPPED_ROOT / 'suspension-baseline.json', BASELINE_SHA))
    s.chain(baseline, [], baseline, str(STOPPED_ROOT))
    hold = json.loads(w.read(HOLD_RESULT, HOLD_SHA))
    w.require(hold['ok'] is True and hold['city_suspended'] is True and hold['gascity_rig_suspended'] is True
              and hold['window_root_written'] is False, 'hold record')
    close = json.loads(w.read(CLOSE_RESULT, CLOSE_SHA))
    w.require(close['ok'] is True and close['open_sessions'] == 0 and close['city_tmux_sessions'] == 0
              and close['worktree_processes'] == 0, 'close record')
    # 2. The live city is the staged city.toml and receipt, back at the fully suspended baseline image.
    w.host(o)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[1])
    w.read(w.RECEIPT, w.RECEIPT_SHA[1])
    current = w.suspension_record(o)
    image = s.image(current)
    expected = copy.deepcopy(s.image(baseline))
    expected['updated_at'] = image['updated_at']
    w.require(image == expected, 'suspension not at the fully suspended baseline image')
    routes_before = routes.capture_routes(w, o)
    for root, row in routes_before.items():
        w.require(row['content'] == before['generated_routes'][root]['content'], 'route content changed')
    # 3. The window's restore transition, once: city.toml, reload, receipt.
    ROOT.mkdir(mode=0o700)
    w.ROOT = ROOT
    w.__file__ = str(HERE / 'window-base-r11.py')
    w._SOURCE_SHA = BASE_SHA
    w.save('intent.json', dict(executor_sha256=_SOURCE_SHA, stopped_root=str(STOPPED_ROOT),
                               operation='restore-city-receipt-and-reload-only'))
    w.save('recover-city-intent.json', dict(before=w.CITY_SHA[1], after=w.CITY_SHA[0]))
    w.phase('recover-city', w.confined(['inner', 'city', '0'], 'city'), b, owned)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
    result = w.phase('recover-reload', w.GC + ['reload', '--json'], b, owned)
    answer = json.loads(result['stdout'])
    w.require(answer['ok'] is True and answer['async'] is False and answer['soft'] is False
              and answer['outcome'] in ('applied', 'no_change') and answer['revision'] == w.REVISION[0],
              'recovery reload answer')
    deadline = time.monotonic() + 120
    index = 0
    while True:
        remaining = deadline - time.monotonic()
        w.require(remaining > 0, 'revision observation timeout; no mutation replay')
        trace = w.phase('recover-trace-' + str(index), w.GC + ['trace', 'show', '--type', 'cycle_result',
                        '--since', '2m', '--json'], b, owned, timeout=min(90, remaining))
        rows = json.loads(trace['stdout'])['records']
        newest = max(rows, key=lambda row: row['seq']) if rows else None
        if newest:
            age = time.time() - datetime.fromisoformat(newest['ts'].replace('Z', '+00:00')).timestamp()
            w.require(newest['controller_pid'] == 2331 and 0 <= age <= 120
                      and newest['fields']['active_template_count'] == 0, 'stale/active controller revision')
            if newest['config_revision'] == w.REVISION[0] and newest['completion_status'] == 'completed':
                break
        index += 1
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    w.phase('recover-receipt-check', w.confined(['inner', 'check', '0']), b, owned)
    w.save('recover-receipt-intent.json', dict(before=w.RECEIPT_SHA[1], after=w.RECEIPT_SHA[0]))
    w.phase('recover-receipt-apply', w.confined(['inner', 'apply', '0'], 'receipt'), b, owned)
    w.phase('recover-receipt-verify', w.confined(['inner', 'verify', '0']), b, owned)
    # 4. The recovered state: accepted city.toml and receipt, same suspension, same route content.
    w.host(o)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
    w.read(w.RECEIPT, w.RECEIPT_SHA[0])
    after = w.suspension_record(o)
    w.require(without_atime(after) == without_atime(current), 'suspension changed during recovery')
    routes_after = routes.capture_routes(w, o)
    for root, row in routes_after.items():
        w.require(row['content'] == routes_before[root]['content'], 'route content changed during recovery')
    city_pin = o.read_file(str(w.CITY / 'city.toml'))[0]
    receipt_pin = o.read_file(str(w.RECEIPT))[0]
    w.complete_containment()
    # 5. Ordinary reads of the start-gate objects and of the route files and their .beads directories, so
    # relatime refreshes whatever it may (regenerated route files start with atime at mtime).
    read_paths = list(w.stable_read_paths())
    for _, root in routes.RIGS:
        read_paths += [Path(root) / '.beads', Path(root) / '.beads' / 'routes.jsonl']
    gate_before = {str(p): o.metadata(os.lstat(p)) for p in read_paths}
    read_errors = {}
    for path in read_paths:
        try:
            if Path(path).is_dir():
                os.listdir(path)
            else:
                with open(path, 'rb') as f:
                    f.read(1)
        except OSError as exc:
            read_errors[str(path)] = str(exc)
    gate_after = {str(p): o.metadata(os.lstat(p)) for p in read_paths}
    w.save('result.json', dict(ok=True, city_pin=city_pin, receipt_pin=receipt_pin, suspension=after,
                               revision=w.REVISION[0], reload=answer, cycle=newest,
                               routes_before=routes_before, routes_after=routes_after,
                               gate_before=gate_before, gate_after=gate_after, read_errors=read_errors,
                               receipt_written=True, worker_launched=False))
    print(json.dumps(dict(ok=True, recovered=True, worker_launched=False)))


if __name__ == '__main__':
    main()
