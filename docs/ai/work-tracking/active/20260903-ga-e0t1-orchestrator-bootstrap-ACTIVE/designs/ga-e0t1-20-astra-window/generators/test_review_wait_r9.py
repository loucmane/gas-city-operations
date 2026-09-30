"""Exact R8 failure fixture and adversarial monitoring-envelope regression."""
import copy
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import types

import pytest
import build
import review_wait_r9 as guard
import monitoring_r9


FROZEN = 'c637868cf25442b48418234ac9f1a094ddaac163'
SHA = 'eea89174ed3b2ec78bc01253c674e12049c044ffc10967a961dbb4b66431079b'
NOW = '2026-09-28T21:17:34Z'


def frozen_validator():
    raw = build.git('show', FROZEN + ':' + build.NEW + '/startup-validation.py')
    assert hashlib.sha256(raw).hexdigest() == '3c2ad7f7322b0560a74698d557ae016ab874a1ce02dfdc87ad2f1a3fc1eb2dd2'
    module = types.ModuleType('r8_validator')
    exec(compile(raw, 'frozen_r8_startup_validation', 'exec'), module.__dict__)
    return module


@pytest.fixture
def case():
    session = dict(id='ci-sgd80', session_name='codex-ci-sgd80',
                   created_at='2026-09-28T21:08:39Z', last_active='2026-09-28T23:09:34+02:00')
    baseline = {
        'gc.continuation_group': '',
        'gc.controller_error': 'claimed work has had no observable progress since 2026-09-28T17:37:20Z; inspect session codex-ci-zcoet and decide whether to resume, repair, or stop',
        'gc.failure_owner': 'gc.session-reconciler', 'gc.failure_reason': 'progress_stall',
        'gc.failure_subject': 'ci-zcoet',
        'gc.progress_attention_signature': '575c8b2b58ecf16d8f0695677eb5c869c2139efe8f458eaf950e21f938c5ebdd',
        'gc.progress_last_observed_at': '2026-09-28T17:37:20Z',
        'gc.routed_to': 'gascity/codex', 'gc.session_affinity': '',
        'gc.session_id': 'ci-zcoet', 'gc.session_name': 'codex-ci-zcoet',
        'gc.work_branch': 'agent/upstream-pending-create-lease',
        'gc.work_dir': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20',
    }
    routed = dict(id='ga-e0t1.20', status='open', assignee=None,
                  started_at='2026-09-28T13:01:54Z', updated_at='2026-09-28T21:00:48Z',
                  metadata=baseline, labels=['needs/operator'], notes='preserved history')
    task = copy.deepcopy(routed)
    task.update(status='in_progress', assignee=session['session_name'],
                updated_at='2026-09-28T21:14:39Z',
                notes=routed['notes'] + '\nSTARTUP READY: ga-e0t1.20 report_sha256=' + SHA)
    task['metadata'].update({
        'gc.session_id': session['id'], 'gc.session_name': session['session_name'],
        'gc.controller_error': 'claimed work has had no observable progress since 2026-09-28T21:09:34Z; inspect session codex-ci-sgd80 and decide whether to resume, repair, or stop',
        'gc.failure_subject': session['id'],
        'gc.progress_attention_signature': 'bc2c7f90f4b2563aaa35fe4468545c40114057cac6f309dc25d824a961a00ec1',
        'gc.progress_last_observed_at': '2026-09-28T21:09:34Z',
    })
    return task, routed, session


def test_recorded_r8_refusal_is_reproduced_by_frozen_code(case):
    task, routed, session = case
    with pytest.raises(RuntimeError, match='claim metadata differs'):
        frozen_validator().live_task(task, routed, session, None, SHA)


def test_exact_current_stall_is_consistent_not_authorization(case):
    prior = copy.deepcopy(case)
    result = guard.monitoring_state(*case, NOW)
    assert result == dict(kind='verified-current-session-review-wait', session_id='ci-sgd80',
        last_progress='2026-09-28T21:09:34Z',
        core_signature='bc2c7f90f4b2563aaa35fe4468545c40114057cac6f309dc25d824a961a00ec1',
        attention_preserved=True, source_release_authorized_by_this_check=False)
    assert case == prior


def test_exact_inherited_monitoring_is_unchanged(case):
    task, routed, session = case
    task['metadata'] = dict(routed['metadata'], **{'gc.session_id': session['id'],
                                                'gc.session_name': session['session_name']})
    assert guard.monitoring_state(*case, NOW) == {'kind': 'exact-inherited-monitoring'}


@pytest.mark.parametrize('key', sorted(guard.KEYS))
def test_partial_mixed_or_missing_envelope_refuses(case, key):
    case[0]['metadata'][key] = case[1]['metadata'][key] + 'changed'
    with pytest.raises(RuntimeError): guard.monitoring_state(*case, NOW)
    del case[0]['metadata'][key]
    with pytest.raises(RuntimeError): guard.monitoring_state(*case, NOW)


@pytest.mark.parametrize('key,value', [
    ('gc.session_id', 'ci-other'), ('gc.session_name', 'codex-ci-other'),
    ('gc.routed_to', 'hpfetcher/codex'), ('gc.work_dir', '/tmp/other'),
    ('gc.work_branch', 'changed'), ('unrelated', 'added'),
    ('gc.last_heartbeat_at', '2026-09-28T21:16:00Z'),
])
def test_non_monitoring_metadata_is_exact(case, key, value):
    case[0]['metadata'][key] = value
    with pytest.raises(RuntimeError): guard.monitoring_state(*case, NOW)


@pytest.mark.parametrize('key,value', [
    ('id', 'ga-other'), ('status', 'open'), ('assignee', 'codex-ci-other'),
    ('labels', []), ('labels', ['needs/operator', 'extra']),
    ('updated_at', '2026-09-28T21:09:33Z'), ('updated_at', '2026-09-28T21:14:33Z'),
    ('updated_at', '2026-09-28T21:17:35Z'),
])
def test_claim_label_and_chronology_changes_refuse(case, key, value):
    case[0][key] = value
    with pytest.raises(RuntimeError): guard.monitoring_state(*case, NOW)


@pytest.mark.parametrize('key,value', [
    ('id', 'ci-other'), ('session_name', 'codex-ci-other'),
    ('created_at', '2026-09-28T21:09:35Z'),
    ('last_active', '2026-09-28T23:09:35+02:00'),
    ('last_active', None),
])
def test_independent_session_observation_required(case, key, value):
    case[2][key] = value
    with pytest.raises(RuntimeError): guard.monitoring_state(*case, NOW)


@pytest.mark.parametrize('value', [None, 123, '', '2026-09-28', '2026-09-28T21:09:34',
    '2026-09-28T21:09:34+00:00', '2026-09-28T21:09:34.000Z',
    '2026-02-30T21:09:34Z', '2026-09-28T21:09:60Z', '2026-09-28T21:09:34.1234567891Z'])
def test_noncanonical_progress_time_refuses(value):
    with pytest.raises(RuntimeError): guard.stamp(value)


def test_nanoseconds_and_timezone_are_not_truncated():
    assert guard.stamp('2026-09-28T23:09:34.123456789+02:00', offset=True) == guard.stamp('2026-09-28T21:09:34.123456789Z')
    assert guard.stamp('2026-09-28T21:09:34.123456789Z') - guard.stamp('2026-09-28T21:09:34.123456788Z') == 1


@pytest.mark.parametrize('zone', ['+24:00', '+02:60', '-00:00', '-30:00'])
def test_noncanonical_zone_refuses(zone):
    with pytest.raises(RuntimeError):
        guard.stamp('2026-09-28T21:09:34' + zone, offset=True)


def test_exact_real_r8_snapshot_matches_fixture(case):
    path = Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r8/task-before-phase.json')
    if not path.exists(): pytest.skip('local preserved live evidence not present')
    task = json.loads(json.loads(path.read_text())['stdout'])[0]
    assert task['metadata'] == case[0]['metadata']
    assert task['labels'] == case[0]['labels']
    assert task['updated_at'] == case[0]['updated_at']
    assert guard.monitoring_state(task, case[1], case[2], NOW)['kind'] == 'verified-current-session-review-wait'


def corrected():
    validator = build.git('show', FROZEN + ':' + build.NEW + '/startup-validation.py')
    release = build.git('show', FROZEN + ':' + build.NEW + '/startup-release.py')
    new_validator, new_release = monitoring_r9.sources(validator, release)
    module = types.ModuleType('r9_validator')
    exec(compile(new_validator, 'inert_r9_validation', 'exec'), module.__dict__)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 28, 21, 17, 34, 123400, tzinfo=timezone.utc)

    module.datetime = Clock
    return module, validator, new_validator, new_release


def test_corrected_full_task_preserves_baseline_contract_and_inputs(case):
    module, _, _, _ = corrected()
    before = copy.deepcopy(case)
    calls = []
    contract = types.SimpleNamespace(validate_task=lambda *args: calls.append(args))
    assert module.live_task(*case, contract, SHA).startswith('STARTUP READY: ')
    assert calls == [(case[1], 'routed')]
    assert case == before


@pytest.mark.parametrize('key,value', [
    ('description', 'different scope'), ('notes', 'different notes'),
    ('assignee', 'codex-ci-other'), ('labels', []), ('priority', 0),
])
def test_corrected_full_task_does_not_waive_other_fields(case, key, value):
    module, _, _, _ = corrected()
    case[0][key] = value
    contract = types.SimpleNamespace(validate_task=lambda *args: None)
    with pytest.raises(RuntimeError):
        module.live_task(*case, contract, SHA)


def test_only_original_live_task_function_changes():
    _, old, new, _ = corrected()
    def functions(raw):
        return {n.name: ast.dump(n, include_attributes=False)
                for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}
    a, b = functions(old), functions(new)
    assert {k for k in a if a[k] != b[k]} == {'live_task'}
    assert set(b) - set(a) == {'stamp', 'monitoring_state', 'waiting_turn'}


def test_release_validates_twice_before_exact_race_hold_and_nudge():
    _, _, _, raw = corrected()
    tree = ast.parse(raw)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)]
    validates = sorted(n.lineno for n in calls if ast.unparse(n.func) == 'v.live_task')
    equality = [n for n in calls if ast.unparse(n.func) == 'require'
                and n.args and ast.unparse(n.args[0]) == 'task2 == task']
    nudge = [n for n in calls if ast.unparse(n.func) == 'phase'
             and n.args and isinstance(n.args[0], ast.Constant)
             and n.args[0].value == 'source-release']
    assert len(validates) == 2 and len(equality) == len(nudge) == 1
    assert validates[0] < validates[1] < equality[0].lineno < nudge[0].lineno
    assert 'monitoring_adjudication=monitoring' in raw.decode()


def wait_rows(case):
    marker = ('WAITING FOR SOURCE RELEASE: ga-e0t1.20 session=' + case[2]['id']
              + ' report_sha256=' + SHA + ' probe_sha256=' + 'a' * 64)
    return [dict(type='session_meta', payload={}),
            dict(timestamp='2026-09-28T21:09:34.497Z', type='response_item',
                 payload=dict(type='message', role='assistant', phase='final_answer',
                              content=[dict(type='output_text', text=marker)])),
            dict(timestamp='2026-09-28T21:09:34.518Z', type='event_msg',
                 payload=dict(type='task_complete', last_agent_message=marker))]


def wait_bytes(rows):
    return b''.join(json.dumps(r).encode() + b'\n' for r in rows)


def test_waiting_native_completion_is_required_but_grants_nothing(case):
    result = guard.waiting_turn(wait_bytes(wait_rows(case)), case[2], SHA, 'a' * 64, NOW)
    assert result['completed_waiting_turn'] is True
    assert result['source_release_authorized_by_this_check'] is False


@pytest.mark.parametrize('kind', ['task_started', 'turn_aborted', 'item_completed'])
def test_intervening_native_activity_refuses(case, kind):
    rows = wait_rows(case)
    rows.append(dict(type='event_msg', payload=dict(type=kind)))
    with pytest.raises(RuntimeError):
        guard.waiting_turn(wait_bytes(rows), case[2], SHA, 'a' * 64, NOW)


def test_stuck_or_incomplete_native_turn_refuses(case):
    with pytest.raises(RuntimeError):
        guard.waiting_turn(wait_bytes(wait_rows(case)[:-1]), case[2], SHA, 'a' * 64, NOW)


def test_wrong_session_or_digest_in_waiting_text_refuses(case):
    rows = wait_rows(case)
    raw = wait_bytes(rows).replace(SHA.encode(), b'b' * 64)
    with pytest.raises(RuntimeError):
        guard.waiting_turn(raw, case[2], SHA, 'a' * 64, NOW)


def test_later_host_activity_or_future_completion_refuses(case):
    raw = wait_bytes(wait_rows(case))
    case[2]['last_active'] = '2026-09-28T23:09:35+02:00'
    with pytest.raises(RuntimeError):
        guard.waiting_turn(raw, case[2], SHA, 'a' * 64, NOW)
    case[2]['last_active'] = '2026-09-28T23:09:34+02:00'
    with pytest.raises(RuntimeError):
        guard.waiting_turn(raw, case[2], SHA, 'a' * 64, '2026-09-28T21:09:34.517Z')


def test_only_native_token_accounting_may_follow_completion(case):
    rows = wait_rows(case)
    rows.append(dict(type='event_msg', payload=dict(type='token_count')))
    assert guard.waiting_turn(wait_bytes(rows), case[2], SHA, 'a' * 64, NOW)['completed_waiting_turn']


def captured_wait_rows(case):
    path = Path('/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T23-08-40-01a0e9d9-331e-7943-864b-f638923703d8.jsonl')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '606cc6668ac00b1655cb9a648ece40cba296848bc461f78a02b3776d208c9147'
    rows = [json.loads(line) for line in raw.splitlines()]
    marker = wait_rows(case)[1]['payload']['content'][0]['text']
    assert [row['type'] for row in rows[-4:]] == ['response_item', 'token_usage_record', 'event_msg', 'event_msg']
    # Synthetic marker substitution only; actual native ordering/accounting stays exact.
    rows[-4]['payload']['content'] = [{'type': 'output_text', 'text': marker}]
    rows[-1]['payload']['last_agent_message'] = marker
    return rows


def test_actual_native_completion_sequence_with_synthetic_wait_marker(case):
    rows = captured_wait_rows(case)
    assert guard.waiting_turn(wait_bytes(rows), case[2], SHA, 'a' * 64, NOW)['completed_waiting_turn']


@pytest.mark.parametrize('fraction', ['000', '050', '510', '830', '123456780'])
def test_native_fractional_zero_suffix_is_valid_not_core_canonicalization(case, fraction):
    rows = wait_rows(case)
    rows[1]['timestamp'] = rows[2]['timestamp'] = '2026-09-28T21:09:34.' + fraction + 'Z'
    assert guard.waiting_turn(wait_bytes(rows), case[2], SHA, 'a' * 64, NOW)['completed_waiting_turn']


@pytest.mark.parametrize('fault', ['thread', 'session', 'turn', 'root_turn', 'extra', 'counter', 'boolean', 'time', 'type', 'activity'])
def test_native_accounting_is_bounded_and_cannot_hide_activity(case, fault):
    rows = captured_wait_rows(case)
    row = rows[-3]
    if fault in ('thread', 'session', 'turn', 'root_turn'):
        row['payload'][fault + '_id'] = 'foreign'
    elif fault == 'extra': row['payload']['tool_call'] = {}
    elif fault == 'counter': row['payload']['usage']['input_tokens'] = -1
    elif fault == 'boolean': row['payload']['usage']['input_tokens'] = True
    elif fault == 'time': row['timestamp'] = '2026-09-28T21:10:34.510Z'
    elif fault == 'type': row['type'] = 'turn_context'
    else: rows.insert(-1, dict(type='event_msg', payload=dict(type='task_started')))
    with pytest.raises(RuntimeError):
        guard.waiting_turn(wait_bytes(rows), case[2], SHA, 'a' * 64, NOW)
