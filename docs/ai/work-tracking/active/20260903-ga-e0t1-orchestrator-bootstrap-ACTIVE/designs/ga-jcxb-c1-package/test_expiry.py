"""Pure fixture coverage of Core's already-expired foreign pending transition.

Incident contents are digest-pinned. R12 did not capture wall-clock brackets;
those in the incident test are synthetic inputs, NOT recovered live proof.
No command, service, Bead mutation or queue write is performed by these tests.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import release_delivery_r12 as d
from test_delivery_regression import (
    S, M, BEFORE, EXE, SHA, CG, START, OLD, BASELINE, Clock, snapshot,
)

T = 1790642685000000000
BASE = [T, T + 100]
OBS = [T + 200, T + 400]
EXP = '2026-09-29T00:44:44.999999999Z'
DEAD = '2026-09-29T00:44:45.000000300Z'


def fixture(delivered=False, received=False):
    before = copy.deepcopy(BASELINE)
    item = before['pending'][0]
    item.update(expires_at=EXP, created_at='2026-09-28T23:44:44Z',
                source='session', agent='gascity/codex', continuation_epoch='3',
                attempts=2, next_attempt_at='2026-09-29T00:40:00Z',
                claim='preserved', lease_owner='preserved', arbitrary={'nested': [1, 2]})
    snap = snapshot(delivered, received)
    snap['queue']['pending'] = [x for x in snap['queue']['pending'] if x['id'] != OLD['id']]
    snap['queue']['dead'].append(dict(item, dead_at=DEAD, last_error='expired'))
    snap['observed_window_ns'] = list(OBS)
    return before, snap


def account(before, snap, baseline=BASE, observed=OBS, previous=None):
    return d.preserved_history(d.queue_baseline(before, S), d.queue_items(snap['queue']),
                              S, baseline, observed, previous)


def wait_for(before, snaps, recorder=None, timeout=4):
    clock = Clock()
    count = 0
    def observe(_):
        nonlocal count
        result = copy.deepcopy(snaps[min(count, len(snaps) - 1)])
        count += 1
        return result
    return d.wait(observe, clock.now, clock.sleep, S, M, BEFORE, START, before,
                  EXE, SHA, CG, timeout, baseline_window_ns=BASE, record_history=recorder)


def test_exact_transition_is_evidence_not_delivery():
    before, snap = fixture()
    rows = account(before, snap)
    assert len(rows) == 1 and rows[0]['id'] == OLD['id']
    assert rows[0]['before'][1] == before['pending'][0]
    assert rows[0]['after'][1] == snap['queue']['dead'][-1]
    assert d.acknowledged(snap['receipts'], snap['queue'], S, M, START, before,
                         baseline_window_ns=BASE, observed_window_ns=OBS) is None


@pytest.mark.parametrize('original_error', [None, '', 'prior transport problem'])
def test_conditional_last_error_rule_is_exact(original_error):
    before, snap = fixture()
    old = before['pending'][0]
    if original_error is not None:
        old['last_error'] = original_error
    snap['queue']['dead'][-1] = dict(old, dead_at=DEAD,
                                    last_error=original_error or 'expired')
    assert len(account(before, snap)) == 1
    snap['queue']['dead'][-1]['last_error'] = 'replacement'
    with pytest.raises(RuntimeError): account(before, snap)


@pytest.mark.parametrize('field', [
    'session_id', 'message', 'source', 'agent', 'continuation_epoch',
    'attempts', 'next_attempt_at', 'claim', 'lease_owner', 'created_at',
    'expires_at', 'arbitrary', 'unknown_field',
])
def test_every_other_field_is_whole_object_bound(field):
    before, snap = fixture()
    snap['queue']['dead'][-1][field] = 'different'
    with pytest.raises(RuntimeError): account(before, snap)


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'new-id', 'old-inflight',
    'after-inflight', 'current-session', 'blank-session', 'no-session',
    'not-expired', 'old-death', 'no-death', 'wrong-error', 'removed-old-dead'])
def test_non_native_or_unfenced_transition_refuses(kind):
    before, snap = fixture()
    old = before['pending'][0]
    new = snap['queue']['dead'][-1]
    if kind == 'missing': snap['queue']['dead'].pop()
    elif kind == 'duplicate': snap['queue']['pending'].append(dict(old))
    elif kind == 'new-id': new['id'] = 'nudge-abcdefabcdef'
    elif kind == 'old-inflight': before['in_flight'] = before.pop('pending')
    elif kind == 'after-inflight': snap['queue']['in_flight'] = [snap['queue']['dead'].pop()]
    elif kind in ('current-session', 'blank-session', 'no-session'):
        if kind == 'no-session':
            old.pop('session_id'); new.pop('session_id')
        else: old['session_id'] = new['session_id'] = S['id'] if kind == 'current-session' else ''
    elif kind == 'not-expired': old['expires_at'] = new['expires_at'] = '2026-09-29T00:44:46Z'
    elif kind == 'old-death': old['dead_at'] = DEAD
    elif kind == 'no-death': new.pop('dead_at')
    elif kind == 'wrong-error': new['last_error'] = ''
    elif kind == 'removed-old-dead': snap['queue']['dead'].pop(0)
    with pytest.raises(RuntimeError): account(before, snap)


@pytest.mark.parametrize('value', [
    None, 1, True, '', '2026-09-29T00:44:45', '2026-09-29 00:44:45Z',
    '2026-02-30T00:00:00Z', '2026-09-29T24:00:00Z',
    '2026-09-29T00:44:45.1234567890Z', '2026-09-29T00:44:45+01:60',
    '2026-09-29T00:44:45+24:00', '0001-01-01T00:00:00Z',
    '1970-01-01T00:00:00Z', '1969-12-31T23:59:59Z',
])
def test_timestamp_shape_and_precision_refuse(value):
    with pytest.raises(RuntimeError): d.timestamp_ns(value)


def test_nanosecond_precision_and_timezone_equivalence():
    assert d.timestamp_ns(DEAD) == T + 300
    assert d.timestamp_ns('2026-09-29T02:44:45.000000300+02:00') == T + 300
    assert d.timestamp_ns(EXP) == T - 1
    before, snap = fixture()
    assert account(before, snap, observed=[T + 200, T + 300])
    with pytest.raises(RuntimeError): account(before, snap, observed=[T + 200, T + 299])
    with pytest.raises(RuntimeError): account(before, snap, baseline=[T - 2, T + 100])
    snap['queue']['dead'][-1]['dead_at'] = EXP
    with pytest.raises(RuntimeError): account(before, snap)


@pytest.mark.parametrize('window', [None, [], [1], [1, 2, 3], [True, 2], [1.0, 2],
                                  [-1, 2], [0, 2], [2, 1], {'lo': 1, 'hi': 2}])
def test_exact_integer_wall_clock_brackets_required(window):
    before, snap = fixture()
    with pytest.raises(RuntimeError): account(before, snap, baseline=window)
    with pytest.raises(RuntimeError): account(before, snap, observed=window)


def test_reversed_capture_brackets_refuse():
    before, snap = fixture()
    with pytest.raises(RuntimeError, match='clock reversed'):
        account(before, snap, observed=[T + 99, T + 400])


def test_expiry_recorded_once_then_receipt_and_ingress_still_required():
    before, queued = fixture()
    _, done = fixture(True, True)
    done['observed_window_ns'] = [T + 500, T + 600]
    recorded = []
    result = wait_for(before, [queued, done], recorder=recorded.extend)
    assert result['delivered'] and result['historical_expirations'] == recorded
    assert len(recorded) == 1
    assert recorded[0]['observed_window_ns'] == OBS


@pytest.mark.parametrize('delivered,received', [(False, False), (True, False), (False, True)])
def test_accounting_never_substitutes_for_both_delivery_proofs(delivered, received):
    before, snap = fixture(delivered, received)
    # Fixed fixture interval remains nondecreasing; real adapter captures fresh bounds.
    snap['observed_window_ns'] = [T + 400, T + 400]
    with pytest.raises(RuntimeError, match='timeout'):
        wait_for(before, [snap], recorder=lambda _: None)


def test_evidence_write_failure_or_missing_recorder_cannot_pass():
    before, snap = fixture(True, True)
    with pytest.raises(RuntimeError, match='recorder required'): wait_for(before, [snap])
    def fail(_): raise OSError('fixture evidence write failed')
    with pytest.raises(OSError): wait_for(before, [snap], recorder=fail)


@pytest.mark.parametrize('change', ['resurrect', 'rewrite-death', 'disappear', 'error', 'removed-dead'])
def test_first_accepted_history_is_pinned_in_later_observations(change):
    before, queued = fixture()
    _, done = fixture(True, True)
    done['observed_window_ns'] = [T + 500, T + 600]
    row = done['queue']['dead'][-1]
    if change == 'resurrect':
        done['queue']['dead'].pop(); done['queue']['pending'].append(dict(before['pending'][0]))
    elif change == 'rewrite-death': row['dead_at'] = '2026-09-29T00:44:45.000000550Z'
    elif change == 'disappear': done['queue']['dead'].pop()
    elif change == 'error': row['last_error'] = 'different'
    elif change == 'removed-dead': done['queue']['dead'].pop(0)
    with pytest.raises(RuntimeError): wait_for(before, [queued, done], recorder=lambda _: None)


def test_observation_clock_reversal_after_accounting_refuses():
    before, queued = fixture()
    _, done = fixture(True, True)
    done['observed_window_ns'] = [T + 399, T + 600]
    with pytest.raises(RuntimeError, match='observation clock reversed'):
        wait_for(before, [queued, done], recorder=lambda _: None)


def test_preserved_incident_with_synthetic_time_inputs_is_pending_not_pass():
    root = Path('/var/tmp/ga-goo5-startup-release-20260930-r1')
    def pinned(name, digest):
        raw = (root / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        return json.loads(raw)
    before = pinned('delivery-baseline.json', 'e66e115eb32d45063d0dc2876d92f8b25c91fcd736a8dc751754303aeec015ff')
    after = pinned('delivery-observation-6.json', '50c86fbc7a3868aea55e5256086ab08fda572706cfa4d3c7d7b357b33d9eb240')
    intent = pinned('nudge-intent.json', '524689db31c673fa6c53f6a54581ff3d86995ad97834e5c6a3e606173a6c3eba')
    baseline = [d.timestamp_ns('2026-09-30T02:07:00Z'),
                d.timestamp_ns('2026-09-30T02:07:01Z')]
    observed = [d.timestamp_ns('2026-09-30T02:08:03Z'),
                d.timestamp_ns('2026-09-30T02:08:05Z')]
    assert after['transcript_sha256'] == before['transcript_sha256']
    assert d.acknowledged(after['receipts'], after['queue'], before['session'],
                         intent['message'], before['intent_epoch'], before['queue'],
                         baseline_window_ns=baseline, observed_window_ns=observed) is None
    # Without new capture evidence the old attempt remains failed, never retro-PASS.
    with pytest.raises(RuntimeError):
        d.acknowledged(after['receipts'], after['queue'], before['session'],
                       intent['message'], before['intent_epoch'], before['queue'])
