"""Adapter contract tests with no subprocess, live Bead, service or file writes."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import release_delivery_r11 as d
import release_runtime_r11 as r
from test_release_delivery_r11 import S, M, BEFORE, BASELINE, EXE, CG, ingress, snapshot, START


def harness(monkeypatch, fault=None):
    enqueued = False
    calls, saved = [], {}
    binary = b'fixture-core'
    digest = hashlib.sha256(binary).hexdigest()
    record = dict(id=S['id'], issue_type='session', status='open', labels=['gc:session'], metadata=dict(
        session_name=S['session_name'], template='gascity/codex', provider='codex-managed',
        continuation_epoch='1', **{'gc.trigger_bead_id':'ga-e0t1.20','gc.trigger_bead_store_ref':'rig:gascity'}))
    transcript = Path('/fixture/rollout.jsonl')
    poller = snapshot()['poller']
    queue_path = r.CITY / '.gc/nudges/state.json'
    def phase(label, args, timeout):
        nonlocal enqueued
        assert 0 < timeout <= 15
        calls.append(args)
        assert args[:3] == [EXE, '--city', str(r.CITY)]
        op = args[3:]
        if op == ['bd','show',S['id'],'--json']:
            if fault == 'epoch' and enqueued: record['metadata']['continuation_epoch'] = '2'
            value = [record]
        elif op[:2] == ['bd','list']:
            assert op == ['bd','list','--type','chore','--label','gc:nudge','--include-infra',
                '--all','--metadata-field','session_id='+S['id'],'--limit','2','--json']
            value = snapshot(True, True)['receipts'] if enqueued else []
            if fault == 'ack' and enqueued: value[0]['metadata']['state'] = 'failed'
            if fault == 'existing' and not enqueued: value = snapshot()['receipts']
        else:
            assert not enqueued and op == ['session','nudge',S['id'],M,'--delivery','queue','--json']
            enqueued = True
            value = dict(schema_version='1',ok=True,target='gascity/codex',session_id=S['id'],
                session_name=S['session_name'],delivery='queue',queued=True,outcome='queued')
        return dict(stdout=json.dumps(value))
    def read(path, limit):
        if path == Path(EXE): return binary
        if path == queue_path: return json.dumps(BASELINE).encode()
        if path == transcript: return BEFORE + (ingress() if enqueued else b'')
        assert path.parent == r.CITY / '.gc/nudges/pollers'
        assert path.name.startswith(S['session_name'] + '-')
        return b'123\n'
    def proc(path, limit):
        if path == Path('/proc/self/cgroup'): return CG.encode()
        assert path == Path('/proc/123/exe')
        return binary
    def node(pid, row):
        return dict(exe=EXE, argv=poller['argv'], cgroup='0::/other.service\n' if fault=='cgroup' else CG)
    monkeypatch.setattr(r.os.path, 'lexists', lambda p: False)
    monkeypatch.setattr(r.time, 'time', lambda: START)
    rt = SimpleNamespace(PROC=Path('/proc'),proc_bytes=proc,node=node,
        process_table=lambda:{123:dict(start='456',uid=1000)})
    w = SimpleNamespace(GC=[EXE,'--city',str(r.CITY)],b_gc_sha=lambda:digest,
        save=lambda k,v:saved.setdefault(k,v))
    def run():
        return r.execute(w,phase,SimpleNamespace(file_bytes=read),rt,d,S,
                         dict(transcript_path=str(transcript)),M,BEFORE,lambda:True)
    return run,calls,saved


def test_adapter_enqueues_once_and_requires_real_observation_contract(monkeypatch):
    run,calls,saved = harness(monkeypatch)
    assert run()['delivered']
    assert len([c for c in calls if c[3:5]==['session','nudge']]) == 1
    assert all(c[3:5] not in (['nudge','status'],['nudge','drain'],['nudge','poll']) for c in calls)
    assert saved['delivery-baseline.json']['queue'] == BASELINE
    assert saved['delivery-acknowledged.json']['delivered']


@pytest.mark.parametrize('fault', ['existing','ack','epoch','cgroup'])
def test_adapter_failure_never_resends_or_declares_success(monkeypatch, fault):
    run,calls,saved = harness(monkeypatch,fault)
    with pytest.raises(RuntimeError): run()
    assert len([c for c in calls if c[3:5]==['session','nudge']]) == (0 if fault=='existing' else 1)
    assert 'delivery-acknowledged.json' not in saved
