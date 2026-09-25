"""ga-f37t s6 recovery: return the city to its accepted image after the refused s5 r5 STAGE, once.

STAGE in the window root REFUSED_ROOT replaced city.toml with the staged overlay, then refused at the reload
acknowledgement: the controller had already applied the change, so gc reload answered outcome no_change at the
staged revision. The receipt was never applied, no lifecycle ran, and no route or worker exists. This job checks
that exact recorded state, puts city.toml back to its accepted bytes with the reviewed confined atomic replace,
reloads, and waits until the controller has completed the accepted revision. Its result records the recovered
city.toml pin, which the next window's OBSERVE admits (approved_recovery_image). Finally it makes ordinary reads
of the four objects the next PREFLIGHT start gate checks, so relatime refreshes any access time it may refresh.
It never writes the receipt, the suspension state or a Bead, and never starts a worker. It writes no route
itself; the controller regenerates the route files after the city write, and the script checks their content
is unchanged.
"""
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
REFUSED_ROOT = Path('/var/tmp/ga-f37t-window-20260923-r1')
ROOT = Path('/var/tmp/ga-f37t-recover-20260925-r1')
REFUSED_FILES = ['before.json', 'cache-atime-6a519f4c7176a5556f5a6f146dc8148f4bf15c3e3c836bca136a616824f046df-6b5b1c3e236f931e09155d427367c3632f4ae7e28a56f5dcbb794820fabc3bcf.json', 'cache-atime-6b5b1c3e236f931e09155d427367c3632f4ae7e28a56f5dcbb794820fabc3bcf-0963c0552b35801eb38fd04dd4bd3d28d67446b40f9ec02e498f2ce81fb69869.json', 'city.before.toml', 'git-head-phase.json', 'git-head-started.json', 'git-status-phase.json', 'git-status-started.json', 'integrity-binding.json', 'preflight-intent.json', 'preflight-pass.json', 'receipt.before.json', 'route-accounting-2373b80dda0e0d55d75fa8492119508f5ce7bf418aeb8a5046ac1d64f7d32865-c1c932a619ab32115050cac3d2cd8feeb84d181b2017f787fc76d35e53ab9d75.json', 'route-accounting-c1c932a619ab32115050cac3d2cd8feeb84d181b2017f787fc76d35e53ab9d75-f14e0c998485ad25116900e4a13d9f07df175c09ba5fbe0ba4dd618c5f900171.json', 'stage-city-intent.json', 'stage-city-phase.json', 'stage-city-started.json', 'stage-consumed.json', 'stage-immediate.json', 'stage-refused.json', 'stage-reload-intent.json', 'stage-reload-phase.json', 'stage-reload-started.json', 'suspension-baseline.json']
REFUSED_SHA = 'aa882bf9c5d3a58d8b213a80ae97aaf09c7a5494d3fd5f13ae5ac27974db5f76'
BEFORE_SHA = 'bbf6ef91576e6634867d363995b5c3fe73c99bd5d9994802f4886bb23ca6500c'
RELOAD_SHA = 'dc61729ece6ce942e1dce1e9162527cd476b9fd2b1c755c89e5c347ca8c025c7'
BASELINE_SHA = '771107c0d53eed26780fe63f4f2311849b54a1d373e9d12770633e2348d4c137'


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
    w = load(HERE / 'window-base-r11.py', BASE_SHA, 'recovery_base')
    routes = load(HERE / 'restore-r9-routes-r3.py', ROUTES_SHA, 'recovery_routes')
    w.read(Path(__file__), _SOURCE_SHA)
    b, o, owned = w.load_support()
    w.pins()
    s = w.module(HERE / 'suspension-lineage.py', w.LINEAGE_SHA)
    # 1. The refused window root holds exactly the recorded refusal.
    w.require(sorted(os.listdir(REFUSED_ROOT)) == REFUSED_FILES, 'refused window root contents')
    w.require(json.loads(w.read(REFUSED_ROOT / 'stage-refused.json', REFUSED_SHA))
              == dict(automatic_replay=False, error='reload acknowledgement'), 'refusal record')
    phase = json.loads(w.read(REFUSED_ROOT / 'stage-reload-phase.json', RELOAD_SHA))
    c = phase['cleanup']
    w.require(phase['exit_code'] == 0 and not phase['timed_out'] and not phase['primary_error']
              and c['direct_child_reaped'] and c['owned_process_group_gone'] and not c['failures']
              and not c['unexpected_survivors'], 'refused reload containment')
    ack = json.loads(phase['stdout'])
    w.require(ack['ok'] is True and ack['async'] is False and ack['soft'] is False
              and ack['outcome'] == 'no_change' and ack['revision'] == w.REVISION[1], 'refused reload answer')
    before = json.loads(w.read(REFUSED_ROOT / 'before.json', BEFORE_SHA))
    baseline = json.loads(w.read(REFUSED_ROOT / 'suspension-baseline.json', BASELINE_SHA))
    s.chain(baseline, [], baseline, str(REFUSED_ROOT))
    w.require(baseline['pin'] == before['pins'][w.SUSPENSION], 'suspension baseline binding')
    # 2. The live city is the staged city.toml with the accepted receipt, still fully suspended.
    w.host(o)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[1])
    w.read(w.RECEIPT, w.RECEIPT_SHA[0])
    w.require(without_atime(w.suspension_record(o)) == without_atime(baseline), 'suspension changed since PREFLIGHT')
    routes_before = routes.capture_routes(w, o)
    for root, row in routes_before.items():
        w.require(row['content'] == before['generated_routes'][root]['content'], 'route content changed')
    # 3. Restore city.toml once, reload, and wait for the accepted revision.
    ROOT.mkdir(mode=0o700)
    w.ROOT = ROOT
    w.__file__ = str(HERE / 'window-base-r11.py')
    w._SOURCE_SHA = BASE_SHA
    w.save('intent.json', dict(executor_sha256=_SOURCE_SHA, refused_root=str(REFUSED_ROOT),
                               operation='restore-city-and-reload-only'))
    w.save('recover-city-intent.json', dict(before=w.CITY_SHA[1], after=w.CITY_SHA[0]))
    w.phase('recover-city', w.confined(['inner', 'city', '0'], 'city'), b, owned)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
    result = w.phase('recover-reload', w.GC + ['reload', '--json'], b, owned)
    answer = json.loads(result['stdout'])
    # The controller may already have applied the restored city.toml by itself (no_change); the trace below
    # proves it completed the accepted revision either way.
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
    # 4. The recovered state: accepted city.toml and receipt, same suspension, same route content.
    w.host(o)
    w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
    w.read(w.RECEIPT, w.RECEIPT_SHA[0])
    w.require(without_atime(w.suspension_record(o)) == without_atime(baseline), 'suspension changed during recovery')
    routes_after = routes.capture_routes(w, o)
    for root, row in routes_after.items():
        w.require(row['content'] == routes_before[root]['content'], 'route content changed during recovery')
    city_pin = o.read_file(str(w.CITY / 'city.toml'))[0]
    w.complete_containment()
    # 5. Ordinary reads of the start-gate objects, so relatime may refresh their access times.
    gate_before = {str(p): o.metadata(os.lstat(p)) for p in w.stable_read_paths()}
    for path in w.stable_read_paths():
        if Path(path).is_dir():
            os.listdir(path)
        else:
            with open(path, 'rb') as f:
                f.read(1)
    gate_after = {str(p): o.metadata(os.lstat(p)) for p in w.stable_read_paths()}
    w.save('result.json', dict(ok=True, city_pin=city_pin, receipt_sha256=w.RECEIPT_SHA[0],
                               revision=w.REVISION[0], reload=answer, cycle=newest,
                               routes_before=routes_before, routes_after=routes_after,
                               gate_before=gate_before, gate_after=gate_after,
                               receipt_written=False, worker_launched=False))
    print(json.dumps(dict(ok=True, recovered=True, worker_launched=False)))


if __name__ == '__main__':
    main()
