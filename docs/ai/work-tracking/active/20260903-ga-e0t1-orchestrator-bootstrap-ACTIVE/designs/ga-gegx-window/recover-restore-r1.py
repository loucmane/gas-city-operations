"""ga-gegx s3 recovery: finish the refused RESTORE (receipt only), once, and record the accepted image.

The window in STOPPED_ROOT staged the city, resumed, and its worker (ci-ki0gd) was reaped unclaimed. CONTAIN-1
completed city-suspend and rig-suspend. CLOSE-1 left no session, city tmux server or worktree process, and
ADMIT passed. RESTORE then wrote the accepted city.toml and received a reload answer of no_change at the
accepted revision. Its trace wait refused on the first read: the newest cycle was already at the accepted
revision, but it counted one active template. Core had auto-armed detailed tracing for the worker template
on the session start (`gc trace status`: source auto, trigger start, ten-minute expiry), and every cycle
counts an armed template as touched. The receipt was never restored, and RESTORE is consumed.

This job checks that exact recorded state:
- the stopped window root's listing and the RESTORE, CONTAIN, ADMIT and CLOSE records, pinned by digest;
- the live city.toml is accepted, the receipt is still the staged image, and the suspension state is the
  CONTAIN endpoint.

It writes no city.toml and runs no reload. It waits, for up to 20 minutes, for a controller cycle at the
accepted revision that counts no active template (the auto arm has expired). A cycle at any other revision,
another controller or a stale read refuses. A cycle that still counts an armed template is waited out, not
refused. It then runs the window's confined receipt check, apply and verify back to the accepted receipt
(window-base transition direction 0). It records the recovered city.toml, receipt and suspension-state pins
for the next successor's admission, then makes ordinary reads of the start-gate objects and the route
files. It writes no suspension state, route or Bead, and starts no worker.
"""
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import stat
import sys
import time
import types

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-gegx-window')
BASE_SHA = '70a9a7cd6efe24a14662f272d5934d22aaf57cd9bace27e3598492c687d1a943'
ROUTES_SHA = '8d041af74297b44c0bedecdbcaa776ac92f433eba801afa0ee0a89a71eecc7c2'
STOPPED_ROOT = Path('/var/tmp/ga-gegx-window-20260925-r2')
ROOT = Path('/var/tmp/ga-gegx-recover-20260925-r3')
CLOSE_RESULT = Path('/var/tmp/ga-gegx-close-20260925T121204Z/result.json')
LISTING_SHA = 'eb7db917c99974ed2baeb8e45e6a78c9e48fe5b9d5e78c37cf542b4cf09207f0'
PINNED = {
    'stage-pass.json': '6bb8e83a4eda116261f2868c93fb6a7ab677fffea41385510028dbe2097e19c1',
    'before.json': '1c240d212141298a576a71b671742202ac13a4274b3153d64930a0d81969aae6',
    'suspension-baseline.json': 'a34be50f6986b7c7d3cc73058b7bc140a6232d0722957717abbd8e8cae5ec782',
    'restore-city-phase.json': 'f652e0e49581f79ede8d8bb7cbae3434e9006c07270a76e6e15856f8f5a0852f',
    'restore-reload-phase.json': '6f1c44795aa95ce4dbbcb3c21ad533abc04162fcdf0680bff528809281c6cb47',
    'restore-reload-trace-0-phase.json': 'dd022f880c7dff5fe0bcb137eb1894ba552b94bf8fa9b991874f2676498edf76',
    'restore-consumed.json': '5ed6274e42a893c41a4ce9cec0957e5d7cfcd9509a64011280f037cb25724746',
    'restore-admission-pass.json': 'a4f45076de000cb1d0abf6f3993eb5d1b9bfde3581aab68e3227f0d882e64e11',
    'suspension-city-suspend-event.json': '4a62d1c4906e287d4941d0543bca93a2f704452127d4dc3180c8dec694a0a883',
    'suspension-rig-suspend-event.json': '87ea3c71a21502681f6d22b48022306918caada937515e9a9526aa5c2718570f',
}
CLOSE_SHA = 'd3664c719b090d5ce353c6e842e26bef92642918122aa3dad72121e48a91e1ce'
WINDOW_SHA = '98f78c207a5c142fa24f99f5a6423b62faa59ec173d21f5af9df02c290131ba8'
TEMPLATE = 'gascity/gc.implementation-worker'
ARM_WAIT_SECONDS = 20 * 60


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


def settled_cycle(rows, revision, now):
    """The accepting cycle among `rows`, or None to keep waiting. Refuses on any other controller, revision,
    incomplete or stale newest cycle. A newest cycle at `revision` that still counts only the auto-armed
    worker template is not accepted yet."""
    if not rows:
        return None
    newest = max(rows, key=lambda row: row['seq'])
    age = now - datetime.fromisoformat(newest['ts'].replace('Z', '+00:00')).timestamp()
    if newest['controller_pid'] != 2331 or not 0 <= age <= 120:
        raise RuntimeError('stale or foreign controller cycle')
    if newest['config_revision'] != revision or newest['completion_status'] != 'completed':
        raise RuntimeError('controller cycle not at the accepted revision')
    fields = newest['fields']
    if fields['active_template_count'] == 0:
        return newest
    if fields['active_template_count'] == 1 and fields.get('templates_touched') == [TEMPLATE] \
            and not fields.get('decision_counts') and not fields.get('mutation_counts'):
        return None
    raise RuntimeError('unexpected active template in controller cycle')


def main():
    assert globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000
    w = load(HERE / 'window-base-r11.py', BASE_SHA, 'recovery3_base')
    routes = load(HERE / 'restore-r9-routes-r3.py', ROUTES_SHA, 'recovery3_routes')
    w.read(Path(__file__), _SOURCE_SHA)
    b, o, owned = w.load_support()
    w.pins()
    s = w.module(HERE / 'suspension-lineage.py', w.LINEAGE_SHA)
    # 1. The stopped window root, CLOSE and ADMIT hold exactly the recorded stop.
    w.require(w.ROOT == STOPPED_ROOT, 'window root binding')
    names = sorted(os.listdir(STOPPED_ROOT))
    w.require(hashlib.sha256('\n'.join(names).encode()).hexdigest() == LISTING_SHA, 'stopped window root contents')
    w.require('restored.json' not in names and not any(n.startswith('restore-receipt') for n in names),
              'receipt restore already attempted')
    records = {name: json.loads(w.read(STOPPED_ROOT / name, pin)) for name, pin in PINNED.items()}
    w.require(records['stage-pass.json'] == dict(ok=True, worker_launched=False), 'stage record')
    w.require(records['restore-consumed.json'] == dict(executor_sha256=WINDOW_SHA), 'restore consumption record')
    w.require(records['restore-admission-pass.json']['ok'] is True
              and records['restore-admission-pass.json']['restore_executed'] is False, 'admission record')
    city_phase = records['restore-city-phase.json']
    w.require(city_phase['exit_code'] == 0 and json.loads(city_phase['stdout']) == dict(ok=True, city_sha256=w.CITY_SHA[0]),
              'restore city record')
    answer = json.loads(records['restore-reload-phase.json']['stdout'])
    w.require(answer['ok'] is True and answer['outcome'] in ('applied', 'no_change') and answer['revision'] == w.REVISION[0],
              'restore reload record')
    close = json.loads(w.read(CLOSE_RESULT, CLOSE_SHA))
    w.require(close['ok'] is True and close['open_sessions'] == 0 and close['city_tmux_sessions'] == 0
              and close['worktree_processes'] == 0, 'close record')
    # The completed lifecycle: baseline, rig-resume, city-resume, city-suspend, rig-suspend, and the live
    # suspension state equal to its endpoint.
    endpoint = w.verified_lifecycle(terminal=True)
    # 2. The live city: accepted city.toml, the staged receipt, the lifecycle endpoint.
    w.host(o)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
    w.read(w.RECEIPT, w.RECEIPT_SHA[1])
    current = w.suspension_record(o)
    endpoint_image = without_atime(dict(pin=endpoint))
    w.require(without_atime(dict(pin=current['pin'])) == endpoint_image, 'suspension state is not the lifecycle endpoint')
    before = records['before.json']
    routes_before = routes.capture_routes(w, o)
    for root, row in routes_before.items():
        w.require(row['content'] == before['generated_routes'][root]['content'], 'route content changed')
    # 3. Wait out the auto trace arm, then the window's receipt transition, direction 0, once.
    ROOT.mkdir(mode=0o700)
    w.ROOT = ROOT
    w.__file__ = str(HERE / 'window-base-r11.py')
    w._SOURCE_SHA = BASE_SHA
    w.save('intent.json', dict(executor_sha256=_SOURCE_SHA, stopped_root=str(STOPPED_ROOT),
                               operation='receipt-only-after-settled-cycle'))
    deadline = time.monotonic() + ARM_WAIT_SECONDS
    index = 0
    while True:
        remaining = deadline - time.monotonic()
        w.require(remaining > 0, 'auto trace arm did not settle; no mutation made')
        trace = w.phase('recover-trace-' + str(index), w.GC + ['trace', 'show', '--type', 'cycle_result',
                        '--since', '2m', '--json'], b, owned, timeout=min(90, remaining))
        cycle = settled_cycle(json.loads(trace['stdout'])['records'], w.REVISION[0], time.time())
        if cycle is not None:
            break
        index += 1
        time.sleep(min(15, max(0, deadline - time.monotonic())))
    w.save('recover-settled-cycle.json', cycle)
    w.host(o)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
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
                               revision=w.REVISION[0], cycle=cycle, trace_reads=index + 1,
                               routes_before=routes_before, routes_after=routes_after,
                               gate_before=gate_before, gate_after=gate_after, read_errors=read_errors,
                               receipt_written=True, worker_launched=False))
    print(json.dumps(dict(ok=True, recovered=True, trace_reads=index + 1, worker_launched=False)))


if __name__ == '__main__':
    main()
