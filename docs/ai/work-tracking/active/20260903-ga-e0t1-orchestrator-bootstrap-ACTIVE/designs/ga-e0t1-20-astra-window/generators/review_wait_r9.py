"""Validate monitoring-only changes during the exact worker's startup review.

No writes or grant. The caller still proves the host, native transcript, deliberate
waiting, pristine workspace, full task and permissions before its sole release.
The Core signature is consistency evidence, not an authentication mechanism.
"""
import calendar
from datetime import datetime, timezone
import hashlib
import json
import re


KEYS = frozenset((
    'gc.controller_error', 'gc.failure_owner', 'gc.failure_reason',
    'gc.failure_subject', 'gc.progress_attention_signature',
    'gc.progress_last_observed_at',
))


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def stamp(value, *, offset=False, canonical=True):
    """RFC3339Nano without float or sub-microsecond truncation."""
    require(isinstance(value, str), 'review wait timestamp type')
    match = re.fullmatch(
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?'
        r'(Z|[+-]\d{2}:\d{2})', value)
    require(match is not None and (offset or match[3] == 'Z'),
            'review wait timestamp format')
    zone = match[3]
    require(zone == 'Z' or (int(zone[1:3]) < 24 and int(zone[4:]) < 60
                           and zone != '-00:00'), 'review wait timestamp offset')
    fraction = match[2] or ''
    # Core uses RFC3339Nano, whose fractional suffix has no redundant zeros.
    require(not canonical or not fraction or not fraction.endswith('0'),
            'noncanonical review wait fraction')
    try:
        whole = datetime.fromisoformat(match[1] + match[3].replace('Z', '+00:00'))
        seconds = calendar.timegm(whole.astimezone(timezone.utc).utctimetuple())
    except (ValueError, OverflowError) as exc:
        raise RuntimeError('review wait timestamp calendar or offset') from exc
    return seconds * 10**9 + int(fraction.ljust(9, '0'))


def monitoring_state(task, routed, session, observed_at):
    """Return an auditable classification; never alter either input.

    Frozen historical monitoring is exact. The only alternative is the complete
    deployed-Core stall envelope for this same live claim, corroborated by the
    independent host session census. Every other metadata field stays exact.
    """
    require(isinstance(task, dict) and isinstance(routed, dict) and isinstance(session, dict),
            'review wait input shape')
    baseline = routed.get('metadata')
    actual = task.get('metadata')
    require(isinstance(baseline, dict) and isinstance(actual, dict), 'review wait metadata shape')
    require(task.get('id') == routed.get('id') == 'ga-e0t1.20'
            and task.get('status') == 'in_progress'
            and task.get('assignee') == session.get('session_name')
            and isinstance(session.get('id'), str)
            and re.fullmatch(r'ci-[a-z0-9]+', session['id'])
            and session.get('session_name') == 'codex-' + session['id'],
            'review wait claim identity')
    expected = dict(baseline, **{'gc.session_id': session['id'],
                                'gc.session_name': session['session_name']})
    if actual == expected:
        return {'kind': 'exact-inherited-monitoring'}
    require({k: v for k, v in actual.items() if k not in KEYS}
            == {k: v for k, v in expected.items() if k not in KEYS},
            'non-monitoring claim metadata differs')
    require(KEYS <= actual.keys(), 'incomplete current-session monitoring envelope')
    require(task.get('labels') == routed.get('labels') == ['needs/operator'],
            'review wait labels differ')
    last = actual['gc.progress_last_observed_at']
    last_ns = stamp(last)
    require(stamp(session.get('created_at')) <= last_ns
            == stamp(session.get('last_active'), offset=True)
            <= stamp(task.get('updated_at')) <= stamp(observed_at),
            'review wait chronology or independent progress differs')
    require(stamp(task['updated_at']) - last_ns >= 300 * 10**9,
            'stall predates reviewed inactivity threshold')
    signature = hashlib.sha256('\0'.join((session['id'], task['id'],
        task['status'], task['assignee'], last)).encode()).hexdigest()
    envelope = {
        'gc.controller_error': 'claimed work has had no observable progress since '
            + last + '; inspect session ' + session['session_name']
            + ' and decide whether to resume, repair, or stop',
        'gc.failure_owner': 'gc.session-reconciler',
        'gc.failure_reason': 'progress_stall',
        'gc.failure_subject': session['id'],
        'gc.progress_attention_signature': signature,
        'gc.progress_last_observed_at': last,
    }
    require({k: actual[k] for k in KEYS} == envelope, 'current-session monitoring envelope differs')
    return {'kind': 'verified-current-session-review-wait', 'session_id': session['id'],
            'last_progress': last, 'core_signature': signature,
            'attention_preserved': True, 'source_release_authorized_by_this_check': False}


def waiting_turn(raw, session, report_digest, probe_digest, observed_at):
    """Require native completion of the exact waiting turn, not a stuck tool.

    The existing native transcript reader separately binds CLI identity and
    permissions. This additional proof is deliberately non-authoritative.
    """
    require(isinstance(raw, bytes) and len(raw) <= 32 << 20 and raw.endswith(b'\n'),
            'waiting transcript bound or partial line')
    rows = [json.loads(line) for line in raw.splitlines()]
    require(rows and rows[0].get('type') == 'session_meta', 'waiting transcript metadata')
    for value in (report_digest, probe_digest):
        require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value),
                'waiting digest format')
    marker = ('WAITING FOR SOURCE RELEASE: ga-e0t1.20 session=' + session['id']
              + ' report_sha256=' + report_digest + ' probe_sha256=' + probe_digest)
    meaningful = [r for r in rows if not (r.get('type') == 'token_usage_record'
                  or r.get('type') == 'event_msg'
                  and r.get('payload', {}).get('type') == 'token_count')]
    require(len(meaningful) >= 3, 'incomplete waiting turn')
    final, done = meaningful[-2:]
    payload = final.get('payload', {})
    require(final.get('type') == 'response_item' and payload.get('type') == 'message'
            and payload.get('role') == 'assistant' and payload.get('phase') == 'final_answer'
            and payload.get('content') == [{'type': 'output_text', 'text': marker}],
            'native final answer is not exact waiting marker')
    require(done.get('type') == 'event_msg'
            and done.get('payload', {}).get('type') == 'task_complete'
            and done['payload'].get('last_agent_message') == marker,
            'native waiting turn is not complete')
    # Native records retain millisecond zero suffixes. Core strings remain canonical.
    final_ns = stamp(final.get('timestamp'), canonical=False)
    complete_ns = stamp(done.get('timestamp'), canonical=False)
    require(stamp(session.get('created_at')) <= final_ns
            <= complete_ns <= stamp(observed_at), 'native waiting chronology')
    native_id = rows[0].get('payload', {}).get('id')
    turn_id = done['payload'].get('turn_id')
    usage_keys = {'input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
                  'output_tokens', 'reasoning_output_tokens', 'total_tokens'}
    for row in rows[rows.index(final) + 1:]:
        if row.get('type') != 'token_usage_record':
            continue  # Only the already classified token_count and completion remain.
        accounting = row.get('payload')
        require(set(row) == {'timestamp', 'ordinal', 'type', 'payload'}
                and type(row['ordinal']) is int and row['ordinal'] >= 0,
                'native accounting record shape')
        require(isinstance(accounting, dict) and set(accounting) == {
            'thread_id', 'turn_id', 'session_id', 'root_turn_id', 'response_id',
            'usage', 'turn_token_usage', 'thread_token_usage'}, 'native accounting payload')
        require(isinstance(native_id, str) and native_id
                and accounting['thread_id'] == accounting['session_id'] == native_id
                and isinstance(turn_id, str) and turn_id
                and accounting['turn_id'] == accounting['root_turn_id'] == turn_id,
                'native accounting identity')
        require(isinstance(accounting['response_id'], str)
                and re.fullmatch(r'resp_[0-9a-f]+', accounting['response_id']),
                'native accounting response identity')
        for key in ('usage', 'turn_token_usage', 'thread_token_usage'):
            counters = accounting[key]
            require(isinstance(counters, dict) and set(counters) == usage_keys
                    and all(type(value) is int and value >= 0 for value in counters.values()),
                    'native accounting counters')
        require(final_ns <= stamp(row['timestamp'], canonical=False) <= complete_ns,
                'native accounting chronology')
    require(complete_ns // 10**9 == stamp(session.get('last_active'), offset=True) // 10**9,
            'waiting turn differs from independently observed last activity')
    return {'completed_waiting_turn': True, 'session_id': session['id'],
            'completed_at': done['timestamp'], 'rollout_sha256': hashlib.sha256(raw).hexdigest(),
            'source_release_authorized_by_this_check': False}
