"""Bounded I/O adapter for the existing native release path, not a new transport.

Called inside the RELEASE oneshot. Its only mutation is one supported enqueue.
Neither receipt observations nor queue-file reads drain or maintain the queue.
Normal unit teardown owns the helper lifetime; this module never signals it.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import time

CITY = Path('/home/loucmane/gascity/city')
EXE = '/home/loucmane/gascity/bin/gc'


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
                and m.get('gc.trigger_bead_id') == 'ga-e0t1.20'
                and m.get('gc.trigger_bead_store_ref') == 'rig:gascity', 'native session authority')
        epoch = m.get('continuation_epoch')
        require(isinstance(epoch, str) and re.fullmatch(r'[1-9][0-9]*', epoch), 'native session epoch')
        return dict(id=session['id'], session_name=session['session_name'], continuation_epoch=epoch)

    def receipts(timeout=15):
        return command('receipts', gc + ['bd', 'list', '--type', 'chore', '--label', 'gc:nudge',
            '--include-infra', '--all', '--metadata-field', 'session_id=' + session['id'],
            '--limit', '2', '--json'], timeout)

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
    require(not os.path.lexists(pid_path), 'fresh session already has a poller PID file')
    require(native_session() == bound, 'session changed before enqueue')
    started = time.time()
    w.save('delivery-baseline.json', dict(session=bound, queue=queue_before,
        transcript_sha256=hashlib.sha256(before).hexdigest(), owned_cgroup=owned_cgroup,
        expected_executable=EXE, expected_sha256=expected_sha, intent_epoch=started,
        exactly_one_enqueue=True, source_delivery_unproven=True))
    # Intent is persisted by the caller before entering this function. Do not
    # replay this command if any later check refuses or its result is lost.
    result = command('enqueue', gc + ['session', 'nudge', bound['id'], message,
                                    '--delivery', 'queue', '--json'])
    d.enqueue_result(result, bound)
    w.save('delivery-enqueued.json', result)

    def observe(remaining):
        begin = time.monotonic()
        def budget():
            value = min(15, remaining - (time.monotonic() - begin))
            require(value > 0, 'native release delivery timeout')
            return value
        require(native_session(budget()) == bound, 'session epoch changed during release')
        rows = receipts(budget())
        pid_raw = stable_read(pid_path, 64)
        require(re.fullmatch(rb'[1-9][0-9]*\n?', pid_raw), 'native poller PID encoding')
        pid = int(pid_raw)
        table = runtime.process_table()
        require(pid in table, 'native poller disappeared')
        node = runtime.node(pid, table[pid])
        require(node['exe'] == EXE, 'native poller executable path differs')
        image = hashlib.sha256(runtime.proc_bytes(runtime.PROC / str(pid) / 'exe', 256 << 20)).hexdigest()
        poller = dict(alive=True, pid=pid, start_ticks=int(table[pid]['start']), uid=table[pid]['uid'],
                      argv=node['argv'], cgroup=node['cgroup'], executable_sha256=image)
        queue = json.loads(stable_read(queue_path, 16 << 20))
        transcript = stable_read(Path(proof['transcript_path']), 32 << 20)
        after = runtime.process_table().get(pid)
        require(after is not None and after.get('state') not in ('Z','X')
                and table[pid].get('state') not in ('Z','X')
                and all(after.get(k) == table[pid].get(k) for k in ('start','uid','gid')),
                'native poller changed during read')
        final_node = runtime.node(pid, after)
        require(all(final_node.get(k) == node.get(k) for k in ('exe','argv','cgroup')),
                'native poller executable or cgroup changed during read')
        require(alive(), 'worker exited during release')
        w.save('delivery-observation-' + str(counter) + '.json', dict(receipts=rows, queue=queue,
            poller=poller, transcript_sha256=hashlib.sha256(transcript).hexdigest()))
        return dict(receipts=rows, queue=queue, poller=poller, transcript=transcript)

    result = d.wait(observe, time.monotonic, time.sleep, bound, message, before, started,
                    queue_before, EXE, expected_sha, owned_cgroup)
    w.save('delivery-acknowledged.json', result)
    return result
