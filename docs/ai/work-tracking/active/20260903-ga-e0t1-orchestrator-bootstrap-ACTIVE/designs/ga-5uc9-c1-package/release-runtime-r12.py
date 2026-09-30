"""Bounded native release adapter with exact existing-poller admission.

Append-forward R12. No poller is created directly, deleted, signalled or adopted
by rewriting metadata. Exactly one supported enqueue remains the only mutation.
Core process pins are from the reviewed host window, not caller-discovered trust.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

CITY = Path('/home/loucmane/gascity/city')
EXE = '/home/loucmane/gascity/bin/gc'
CORE_PID = 2800348
CORE_START_TICKS = 22964291
CORE_ARGV = ['/home/loucmane/.local/bin/gc', 'supervisor', 'run']
CORE_CGROUP = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gascity-supervisor-home-42adab5d.service\n'
# The explicit query limit bounds work. A full page is not evidence of absence:
# refuse it, since the supported CLI has no completeness token or pagination.
RECEIPT_LIMIT = 129


def process_identity(runtime, pid, expected_sha, require):
    """Bracket every process read, including executable bytes, by exact identity."""
    table = runtime.process_table()
    require(pid in table, 'native process disappeared')
    row = table[pid]
    require(row.get('state') not in ('Z', 'X'), 'native process dead or zombie')
    node = runtime.node(pid, row)
    require(node['exe'] == EXE, 'native process executable path differs')
    image = hashlib.sha256(runtime.proc_bytes(runtime.PROC / str(pid) / 'exe', 256 << 20)).hexdigest()
    require(image == expected_sha, 'native process executable image differs')
    after = runtime.process_table().get(pid)
    require(after is not None and after.get('state') not in ('Z', 'X')
            and all(after.get(k) == row.get(k) for k in ('start', 'uid', 'gid', 'ppid')),
            'native process changed during read')
    final = runtime.node(pid, after)
    require(all(final.get(k) == node.get(k) for k in ('exe', 'argv', 'cgroup')),
            'native process executable or cgroup changed during read')
    require(hashlib.sha256(runtime.proc_bytes(runtime.PROC / str(pid) / 'exe', 256 << 20)).hexdigest()
            == image, 'native process image changed during read')
    final_row = runtime.process_table().get(pid)
    require(final_row is not None and final_row.get('state') not in ('Z', 'X')
            and all(final_row.get(k) == row.get(k) for k in ('start', 'uid', 'gid', 'ppid')),
            'native process changed during read')
    return dict(alive=True, pid=pid, start_ticks=int(row['start']), ppid=row['ppid'],
                uid=row['uid'], gid=row['gid'], argv=node['argv'],
                cgroup=node['cgroup'], executable_sha256=image)


def core_identity(runtime, expected_sha, require):
    value = process_identity(runtime, CORE_PID, expected_sha, require)
    require(value['start_ticks'] == CORE_START_TICKS
            and value['uid'] == value['gid'] == 1000
            and value['argv'] == CORE_ARGV and value['cgroup'] == CORE_CGROUP,
            'reviewed Core process authority differs')
    return value


def marker_directory(path, require):
    """Check the native writer's directory chain even when no marker exists."""
    for parent in (CITY, CITY / '.gc', CITY / '.gc/nudges', path.parent):
        info = parent.lstat()
        require(parent.resolve(strict=True) == parent and stat.S_ISDIR(info.st_mode)
                and info.st_uid == info.st_gid == 1000 and not info.st_mode & 0o022,
                'native poller directory authority')


def marker_identity(path, inspector, require):
    """Use the existing no-follow reader; bind file identity throughout delivery."""
    marker_directory(path, require)
    first = path.lstat()
    raw = inspector.file_bytes(path, 64)
    last = path.lstat()
    def pin(s):
        return dict(dev=s.st_dev, inode=s.st_ino, mode=s.st_mode, uid=s.st_uid,
                    gid=s.st_gid, nlink=s.st_nlink, size=s.st_size,
                    mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)
    require(pin(first) == pin(last), 'native poller marker changed during read')
    require(re.fullmatch(rb'[1-9][0-9]*\n?', raw), 'native poller PID encoding')
    return int(raw), dict(metadata=pin(last), sha256=hashlib.sha256(raw).hexdigest())


def existing_ancestry(poller, core, require):
    # The native Go poller detaches its process group. It may remain Core's
    # direct child or be reparented to Core's own parent after the enqueue CLI
    # exits. Neither numeric ancestry case grants authority: exact Core service
    # cgroup, pinned executable/session argv and stable process identity do.
    # Arbitrary intermediate ancestry is not admitted.
    require(poller['ppid'] in (core['pid'], core['ppid']),
            'native poller ancestry is not reviewed')

def execute(w, phase, inspector, runtime, d, session, proof, message, before, alive):
    require = d.require
    gc = w.GC
    require(gc == [EXE, '--city', str(CITY)], 'release command authority differs')
    require(re.fullmatch(r'ci-[a-z0-9]+', session['id']) is not None
            and session['session_name'] == 'codex-' + session['id'], 'release session shape')
    counter = 0

    def stable_read(path, limit):
        # Atomic queue replacement or an append can overlap observation. Retry
        # only that precise read race, never permission or integrity failures.
        for attempt in range(3):
            try:
                return inspector.file_bytes(path, limit)
            except RuntimeError as exc:
                if str(exc) != 'candidate file changed during read' or attempt == 2:
                    raise

    def command(label, args, timeout=15):
        nonlocal counter
        counter += 1
        require(alive(), 'worker exited during release')
        result = phase('delivery-' + str(counter) + '-' + label, args, timeout)
        return json.loads(result['stdout'])

    def native_session(timeout=15):
        rows = command('session', gc + ['bd', 'show', session['id'], '--json'], timeout)
        require(type(rows) is list and len(rows) == 1, 'native session receipt count')
        row = rows[0]; m = row.get('metadata', {})
        require(row.get('id') == session['id'] and row.get('issue_type') == 'session'
                and row.get('status') == 'open' and 'gc:session' in row.get('labels', [])
                and m.get('session_name') == session['session_name']
                and m.get('template') == 'gascity/codex' and m.get('provider') == 'codex-managed'
                and m.get('gc.trigger_bead_id') == 'ga-5uc9'
                and m.get('gc.trigger_bead_store_ref') == 'rig:gascity', 'native session authority')
        epoch = m.get('continuation_epoch')
        require(isinstance(epoch, str) and re.fullmatch(r'[1-9][0-9]*', epoch), 'native session epoch')
        return dict(id=session['id'], session_name=session['session_name'], continuation_epoch=epoch)

    def receipts(timeout=15):
        rows = command('receipts', gc + ['bd', 'list', '--type', 'chore', '--label', 'gc:nudge',
            '--include-infra', '--all', '--metadata-field', 'session_id=' + session['id'],
            '--limit', str(RECEIPT_LIMIT), '--json'], timeout)
        require(type(rows) is list and len(rows) < RECEIPT_LIMIT,
                'native receipt history incomplete or malformed')
        return rows

    bound = native_session()
    d.absence_before(receipts(), bound, message)
    queue_path = CITY / '.gc/nudges/state.json'
    queue_raw = stable_read(queue_path, 16 << 20)
    queue_before = json.loads(queue_raw)
    d.queue_baseline(queue_before, bound)
    require(stable_read(Path(proof['transcript_path']), 32 << 20) == before,
            'native waiting transcript changed before enqueue')
    expected_sha = w.b_gc_sha()
    require(hashlib.sha256(inspector.file_bytes(Path(EXE), 256 << 20)).hexdigest() == expected_sha,
            'native poller source differs')
    owned_cgroup = runtime.proc_bytes(runtime.PROC / 'self/cgroup', 4096).decode('utf-8', 'strict')
    require(re.fullmatch(r'0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-[A-Za-z0-9_.-]+\.service\n',
                        owned_cgroup), 'release must retain its exact owned oneshot')
    key = hashlib.sha256((bound['session_name'] + '\0' + bound['id']).encode()).digest()[:8].hex()
    pid_path = CITY / '.gc/nudges/pollers' / (bound['session_name'] + '-' + key + '.pid')
    marker_directory(pid_path, require)
    existing = os.path.lexists(pid_path)
    core = None
    initial_identity = None
    marker_before = None
    expected_cgroup = owned_cgroup
    if existing:
        require(d.CORE_CGROUP == CORE_CGROUP, 'Core cgroup contract differs')
        core = core_identity(runtime, expected_sha, require)
        pid, marker_before = marker_identity(pid_path, inspector, require)
        poller = process_identity(runtime, pid, expected_sha, require)
        existing_ancestry(poller, core, require)
        expected_cgroup = CORE_CGROUP
        initial_identity = d.poller_identity(poller, bound, EXE, expected_sha, expected_cgroup)
        require(marker_identity(pid_path, inspector, require) == (pid, marker_before),
                'native poller marker changed before enqueue')
        require(core_identity(runtime, expected_sha, require) == core,
                'Core changed before enqueue')
    require(native_session() == bound, 'session changed before enqueue')
    marker_directory(pid_path, require)
    if existing:
        now_pid, now_marker = marker_identity(pid_path, inspector, require)
        now = process_identity(runtime, now_pid, expected_sha, require)
        require(d.poller_identity(now, bound, EXE, expected_sha, expected_cgroup) == initial_identity
                and now_marker == marker_before, 'native poller changed before enqueue')
    else:
        require(not os.path.lexists(pid_path), 'native poller appeared before enqueue')
    started = time.time()
    w.save('delivery-baseline.json', dict(session=bound, queue=queue_before,
        transcript_sha256=hashlib.sha256(before).hexdigest(), owned_cgroup=owned_cgroup,
        expected_executable=EXE, expected_sha256=expected_sha, intent_epoch=started,
        exactly_one_enqueue=True, source_delivery_unproven=True,
        poller_mode='existing-core' if existing else 'new-release-owned',
        expected_poller_cgroup=expected_cgroup, initial_poller=initial_identity,
        marker_before=marker_before, core=core))
    # Intent is persisted by the caller before entering this function. Do not
    # replay this command if any later check refuses or its result is lost.
    result = command('enqueue', gc + ['session', 'nudge', bound['id'], message,
                                    '--delivery', 'queue', '--json'])
    d.enqueue_result(result, bound)
    w.save('delivery-enqueued.json', result)

    observed_marker = marker_before

    def observe(remaining):
        nonlocal observed_marker
        begin = time.monotonic()
        def budget():
            value = min(15, remaining - (time.monotonic() - begin))
            require(value > 0, 'native release delivery timeout')
            return value
        require(native_session(budget()) == bound, 'session epoch changed during release')
        rows = receipts(budget())
        pid, marker = marker_identity(pid_path, inspector, require)
        if observed_marker is None:
            observed_marker = marker
        require(marker == observed_marker, 'native poller marker identity changed')
        poller = process_identity(runtime, pid, expected_sha, require)
        if existing:
            require(marker == marker_before, 'native poller marker changed after enqueue')
            require(core_identity(runtime, expected_sha, require) == core,
                    'Core changed during release')
            existing_ancestry(poller, core, require)
        queue = json.loads(stable_read(queue_path, 16 << 20))
        transcript = stable_read(Path(proof['transcript_path']), 32 << 20)
        require(process_identity(runtime, pid, expected_sha, require) == poller,
                'native poller changed during observation')
        require(marker_identity(pid_path, inspector, require) == (pid, marker),
                'native poller marker changed during observation')
        require(alive(), 'worker exited during release')
        w.save('delivery-observation-' + str(counter) + '.json', dict(receipts=rows, queue=queue,
            poller=poller, marker=marker, transcript_sha256=hashlib.sha256(transcript).hexdigest()))
        return dict(receipts=rows, queue=queue, poller=poller, transcript=transcript)

    result = d.wait(observe, time.monotonic, time.sleep, bound, message, before, started,
                    queue_before, EXE, expected_sha, expected_cgroup, initial_identity=initial_identity)
    w.save('delivery-acknowledged.json', result)
    return result
