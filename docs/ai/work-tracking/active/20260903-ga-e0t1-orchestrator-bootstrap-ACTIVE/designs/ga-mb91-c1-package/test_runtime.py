"""Offline adapter tests: all process, command and marker inputs are fixtures."""
import copy
import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import release_delivery_r12 as d
import release_runtime_r12 as r
from test_delivery_regression import S, M, BEFORE, BASELINE, EXE, CG, START, ingress, snapshot


def harness(monkeypatch, existing=True, fault=None, task='ga-mb91'):
    enqueued = False
    calls, saved = [], {}
    binary = b'fixture-core'
    digest = hashlib.sha256(binary).hexdigest()
    poller = snapshot()['poller']
    table = {
        r.CORE_PID: dict(start=str(r.CORE_START_TICKS), uid=1000, gid=1000, ppid=77, state='S'),
        123: dict(start='456', uid=1000, gid=1000, ppid=r.CORE_PID if existing else 9, state='S'),
    }
    record = dict(id=S['id'], issue_type='session', status='open', labels=['gc:session'],
        metadata=dict(session_name=S['session_name'], template='gascity/codex',
            provider='codex-managed', continuation_epoch='1',
            **{'gc.trigger_bead_id':task, 'gc.trigger_bead_store_ref':'rig:gascity'}))
    transcript = Path('/fixture/rollout.jsonl')

    def phase(label, args, timeout):
        nonlocal enqueued
        assert 0 < timeout <= 15
        calls.append(args)
        assert args[:3] == [EXE, '--city', str(r.CITY)]
        op = args[3:]
        if op == ['bd', 'show', S['id'], '--json']:
            if fault == 'epoch' and enqueued:
                record['metadata']['continuation_epoch'] = '2'
            value = [record]
        elif op[:2] == ['bd', 'list']:
            assert op[:-3] == ['bd','list','--type','chore','--label','gc:nudge','--include-infra',
                '--all','--metadata-field','session_id='+S['id']]
            assert op[-3] == '--limit' and op[-1] == '--json'
            limit = int(op[-2])
            value = snapshot(True, True)['receipts'] if enqueued else []
            if fault == 'ordinary-reminder' and not enqueued:
                value = snapshot(True, True)['receipts']
                value[0]['metadata']['message'] = 'Ordinary startup reminder'
            if fault == 'prior-release' and not enqueued:
                value = snapshot()['receipts']
            if fault in ('hidden-prior-release', 'many-reminders') and not enqueued:
                reminders = []
                for index in range(3):
                    reminder = copy.deepcopy(snapshot(True, True)['receipts'][0])
                    reminder['id'] = 'reminder-' + str(index)
                    reminder['metadata']['message'] = 'Ordinary startup reminder ' + str(index)
                    reminders.append(reminder)
                value = reminders + (snapshot()['receipts'] if fault == 'hidden-prior-release' else [])
            if fault == 'saturated-before' or (fault == 'saturated-after' and enqueued):
                value = [copy.deepcopy(snapshot(True, True)['receipts'][0]) for _ in range(limit)]
                for index, item in enumerate(value):
                    item['id'] = 'reminder-' + str(index)
                    item['metadata']['message'] = 'Ordinary startup reminder ' + str(index)
            value = value[:limit]
            if fault == 'ack' and enqueued:
                value[0]['metadata']['state'] = 'failed'
        else:
            assert not enqueued and op == ['session','nudge',S['id'],M,'--delivery','queue','--json']
            enqueued = True
            if fault == 'lost-response':
                raise RuntimeError('lost enqueue response')
            value = dict(schema_version='1',ok=True,target='gascity/codex',session_id=S['id'],
                         session_name=S['session_name'],delivery='queue',queued=True,outcome='queued')
        return dict(stdout=json.dumps(value))

    def read(path, limit):
        if path == Path(EXE): return binary
        if path == r.CITY / '.gc/nudges/state.json': return json.dumps(BASELINE).encode()
        if path == transcript:
            return BEFORE + (ingress() if enqueued else b'')
        raise AssertionError(path)

    def proc(path, limit):
        if path == Path('/proc/self/cgroup'):
            return ('0::/generic.slice\n' if fault == 'caller' else CG).encode()
        assert path in (Path('/proc/123/exe'), Path('/proc') / str(r.CORE_PID) / 'exe')
        return b'wrong-image' if fault == 'image' else binary

    def node(pid, row):
        if pid == r.CORE_PID:
            return dict(exe=EXE, argv=r.CORE_ARGV,
                        cgroup='0::/wrong.service\n' if fault == 'core-cgroup' else r.CORE_CGROUP)
        argv = [EXE, 'nudge', 'poll', '--city', str(r.CITY), '--session', S['session_name'], S['id']]
        if fault == 'argv': argv[-1] = 'ci-other'
        cgroup = r.CORE_CGROUP if existing else CG
        if fault == 'poller-cgroup': cgroup = '0::/generic.slice\n'
        return dict(exe='/wrong/gc' if fault == 'exe' else EXE, argv=argv, cgroup=cgroup)

    def process_table():
        current = copy.deepcopy(table)
        if fault == 'core-start': current[r.CORE_PID]['start'] = '1'
        if fault == 'core-uid': current[r.CORE_PID]['uid'] = 0
        if fault == 'ancestry': current[123]['ppid'] = 99
        if fault == 'reparented': current[123]['ppid'] = 77
        if fault == 'uid': current[123]['uid'] = 0
        if fault == 'gid': current[123]['gid'] = 0
        if fault == 'dead': del current[123]
        if fault == 'zombie': current[123]['state'] = 'Z'
        if enqueued and fault == 'pid-reuse': current[123]['start'] = '999'
        if enqueued and fault == 'parent-changed': current[123]['ppid'] += 1
        if enqueued and fault == 'core-changed': current[r.CORE_PID]['ppid'] += 1
        return current

    def marker(path, inspector, require):
        if fault == 'marker-unreadable': raise PermissionError('fixture inaccessible')
        inode = 3 if enqueued and fault == 'marker-replaced' else 2
        return 123, dict(metadata=dict(inode=inode), sha256='a'*64)

    monkeypatch.setattr(r, 'marker_identity', marker)
    monkeypatch.setattr(r, 'marker_directory', lambda *_: None, raising=False)
    monkeypatch.setattr(r.os.path, 'lexists', lambda p: existing or enqueued)
    monkeypatch.setattr(r.time, 'time', lambda: START)
    from test_delivery_regression import Clock
    clock = Clock()
    monkeypatch.setattr(r.time, 'monotonic', clock.now)
    monkeypatch.setattr(r.time, 'sleep', clock.sleep)
    rt = SimpleNamespace(PROC=Path('/proc'), proc_bytes=proc, node=node, process_table=process_table)
    w = SimpleNamespace(GC=[EXE,'--city',str(r.CITY)], b_gc_sha=lambda:digest,
                        save=lambda k,v:saved.setdefault(k,v),
                        load_support=lambda:(None,None,None),
                        foreign_queue=lambda label,*unused:saved.setdefault('guard-'+label,True),
                        read=lambda path:json.dumps(dict(raw_base64=base64.b64encode(json.dumps(BASELINE).encode()).decode())).encode())
    def run():
        return r.execute(w, phase, SimpleNamespace(file_bytes=read), rt, d, S,
                         dict(transcript_path=str(transcript)), M, BEFORE, lambda:True)
    return run, calls, saved


@pytest.mark.parametrize('existing', [False, True])
def test_real_adapter_reaches_ack_once_for_both_authority_classes(monkeypatch, existing):
    run, calls, saved = harness(monkeypatch, existing)
    assert run()['delivered']
    assert sum(c[3:5] == ['session','nudge'] for c in calls) == 1
    assert all(c[3:5] not in (['nudge','status'],['nudge','poll'],['nudge','drain']) for c in calls)
    baseline = saved['delivery-baseline.json']
    assert baseline['poller_mode'] == ('existing-core' if existing else 'new-release-owned')
    assert bool(baseline['initial_poller']) is existing
    assert saved['delivery-acknowledged.json']['delivered']


def test_detached_core_poller_can_be_reparented_to_exact_core_parent(monkeypatch):
    run, _, saved = harness(monkeypatch, fault='reparented')
    assert run()['delivered']
    assert saved['delivery-baseline.json']['initial_poller']['ppid'] == 77


def test_completed_ordinary_reminder_does_not_preclude_exact_release(monkeypatch):
    run, calls, _ = harness(monkeypatch, fault='ordinary-reminder')
    assert run()['delivered']
    assert sum(c[3:5] == ['session','nudge'] for c in calls) == 1


def test_more_than_two_reminders_do_not_hide_prior_release(monkeypatch):
    run, calls, saved = harness(monkeypatch, fault='hidden-prior-release')
    with pytest.raises(RuntimeError): run()
    assert not any(c[3:5] == ['session','nudge'] for c in calls)
    assert 'delivery-acknowledged.json' not in saved


def test_complete_bounded_reminder_history_allows_one_release(monkeypatch):
    run, calls, _ = harness(monkeypatch, fault='many-reminders')
    assert run()['delivered']
    assert sum(c[3:5] == ['session','nudge'] for c in calls) == 1


@pytest.mark.parametrize('existing', [False, True])
def test_saturated_history_refuses_before_enqueue(monkeypatch, existing):
    run, calls, saved = harness(monkeypatch, existing=existing, fault='saturated-before')
    with pytest.raises(RuntimeError, match='history incomplete'): run()
    assert not any(c[3:5] == ['session','nudge'] for c in calls)
    assert 'delivery-acknowledged.json' not in saved


def test_saturated_observation_never_retries(monkeypatch):
    run, calls, saved = harness(monkeypatch, fault='saturated-after')
    with pytest.raises(RuntimeError, match='history incomplete'): run()
    assert sum(c[3:5] == ['session','nudge'] for c in calls) == 1
    assert 'delivery-acknowledged.json' not in saved


@pytest.mark.parametrize('existing', [False, True])
def test_directory_authority_is_checked_before_enqueue(monkeypatch, existing):
    run, calls, saved = harness(monkeypatch, existing=existing)
    def refuse(*_):
        raise RuntimeError('native poller directory authority')
    monkeypatch.setattr(r, 'marker_directory', refuse)
    with pytest.raises(RuntimeError, match='directory authority'): run()
    assert not any(c[3:5] == ['session','nudge'] for c in calls)
    assert 'delivery-acknowledged.json' not in saved


@pytest.mark.parametrize('changed', ['ppid', 'start', 'uid', 'gid', 'state', 'missing'])
def test_process_identity_brackets_the_final_image_read(changed):
    row = dict(start='123', uid=1000, gid=1000, ppid=99, state='S')
    altered = dict(row)
    altered[changed] = {'start':'124', 'state':'Z'}.get(changed, 42)
    snapshots = iter([{8: row}, {8: row}, {} if changed == 'missing' else {8: altered}])
    runtime = SimpleNamespace(PROC=Path('/proc'), process_table=lambda: next(snapshots),
        node=lambda *_: dict(exe=EXE, argv=['fixture'], cgroup=CG),
        proc_bytes=lambda *_: b'image')
    with pytest.raises(RuntimeError, match='changed during read'):
        r.process_identity(runtime, 8, hashlib.sha256(b'image').hexdigest(), d.require)


@pytest.mark.parametrize('changed', ['exe', 'argv', 'cgroup', 'image'])
def test_process_read_rejects_mid_read_runtime_race(changed):
    row = dict(start='123', uid=1000, gid=1000, ppid=99, state='S')
    first = dict(exe=EXE, argv=['fixture'], cgroup=CG)
    last = dict(first)
    last[changed] = ['other'] if changed == 'argv' else 'other'
    nodes = iter([first, last])
    images = iter([b'image', b'other' if changed == 'image' else b'image'])
    runtime = SimpleNamespace(PROC=Path('/proc'), process_table=lambda: {8: row},
        node=lambda *_: next(nodes), proc_bytes=lambda *_: next(images))
    with pytest.raises(RuntimeError, match='changed during read'):
        r.process_identity(runtime, 8, hashlib.sha256(b'image').hexdigest(), d.require)


@pytest.mark.parametrize('changed', ['ppid', 'start', 'uid', 'gid'])
def test_process_read_rejects_identity_race(changed):
    row = dict(start='123', uid=1000, gid=1000, ppid=99, state='S')
    altered = dict(row)
    altered[changed] = '124' if changed == 'start' else 42
    snapshots = iter([{8: row}, {8: altered}])
    runtime = SimpleNamespace(PROC=Path('/proc'), process_table=lambda: next(snapshots),
        node=lambda *_: dict(exe=EXE, argv=['fixture'], cgroup=CG),
        proc_bytes=lambda *_: b'image')
    with pytest.raises(RuntimeError, match='changed during read'):
        r.process_identity(runtime, 8, hashlib.sha256(b'image').hexdigest(), d.require)


@pytest.mark.parametrize('fault', [
    'prior-release','caller','image','core-start','core-uid','core-cgroup',
    'ancestry','uid','gid','dead','zombie','argv','exe','poller-cgroup','marker-unreadable',
])
def test_existing_identity_failures_refuse_before_the_only_enqueue(monkeypatch, fault):
    run, calls, saved = harness(monkeypatch, fault=fault)
    with pytest.raises((RuntimeError, PermissionError)): run()
    assert not any(c[3:5] == ['session','nudge'] for c in calls)
    assert 'delivery-acknowledged.json' not in saved


@pytest.mark.parametrize('fault', [
    'lost-response','epoch','ack','pid-reuse','parent-changed','core-changed','marker-replaced',
])
def test_post_enqueue_failures_never_retry_or_acknowledge(monkeypatch, fault):
    run, calls, saved = harness(monkeypatch, fault=fault)
    with pytest.raises(RuntimeError): run()
    assert sum(c[3:5] == ['session','nudge'] for c in calls) == 1
    assert 'delivery-acknowledged.json' not in saved


def test_old_gate_reproduces_the_preserved_failure(monkeypatch):
    # Run the exact preserved adapter against the same legitimate existing-poller fixture.
    import types
    old = Path(__file__).parent.parent / 'ga-rq5n-c1-window-r2/release-runtime-r11.py'
    raw = old.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'baf4f1c1a8ac4c2a32ec51427cb39ec430795a5d68ab4ac8bbda62db5fd3b936'
    module = types.ModuleType('preserved_r11')
    exec(compile(raw, str(old), 'exec'), module.__dict__)
    run, calls, saved = harness(monkeypatch, existing=True, task='ga-rq5n')
    monkeypatch.setattr(r, 'execute', module.execute)
    with pytest.raises(RuntimeError, match='fresh session already has a poller PID file'):
        run()
    assert not any(c[3:5] == ['session','nudge'] for c in calls)


def test_prebound_identity_cannot_be_relearned_after_enqueue():
    from test_delivery_regression import Clock, SHA
    snap = snapshot(True, True)
    prior = d.poller_identity(snap['poller'], S, EXE, SHA, CG)
    snap['poller']['start_ticks'] += 1
    clock = Clock()
    with pytest.raises(RuntimeError, match='identity changed'):
        d.wait(lambda _: snap, clock.now, clock.sleep, S, M, BEFORE, START, BASELINE,
               EXE, SHA, CG, initial_identity=prior)
