"""Pure predicates for a bounded native release acknowledgement barrier.

This module grants nothing, enqueues nothing and reads no live state. The frozen
successor adapter must obtain every input from the existing supported native
surfaces while its own oneshot cgroup remains alive. Append-forward R13 accounts only exact native expiration of already-expired foreign pending entries.
All consumed R12 sources remain unchanged.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import re

CORE_CGROUP = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gascity-supervisor-home-42adab5d.service\n'

MAX_WAIT_SECONDS = 90
MAX_OBSERVATIONS = 90


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def enqueue_result(value, session):
    expected = dict(schema_version='1', ok=True, target='gascity/codex',
                    session_id=session['id'], session_name=session['session_name'],
                    delivery='queue', queued=True, outcome='queued')
    require(type(value) is dict and value == expected, 'native enqueue result differs')
    # Native Core does not return a nudge ID here. Never fabricate one.


def native_payload(message):
    require(isinstance(message, str) and message.startswith('SOURCE RELEASE: ')
            and '\n' not in message and '\r' not in message, 'release message shape')
    # Pinned Core f45a6262 cmd_nudge.go:1408-1413 selects this formatter
    # for the observed tmux/non-ACP transport. The ACP formatter differs.
    require(re.fullmatch(r'SOURCE RELEASE: [A-Za-z0-9_.:= -]+', message),
            'release message requires reviewed sanitization')
    return ('<system-reminder>\n'
            'You have a deferred reminder that was queued until a safe boundary:\n\n'
            '- [session] ' + message + '\n\nHandle them after this turn.\n</system-reminder>\n')


def matching_receipts(rows, session, message):
    require(type(rows) is list and len(rows) <= 4096, 'native receipt list shape')
    matches = []
    for row in rows:
        require(type(row) is dict and type(row.get('metadata', {})) is dict,
                'native receipt shape')
        m = row.get('metadata', {})
        if m.get('message') == message or (
                m.get('session_id') == session['id'] and
                str(m.get('message', '')).startswith('SOURCE RELEASE: ')):
            require(m.get('message') == message and m.get('session_id') == session['id'],
                    'foreign or conflicting release receipt')
            require(row.get('issue_type') == 'chore' and type(row.get('labels')) is list
                    and 'gc:nudge' in row['labels'] and m.get('agent') == 'gascity/codex'
                    and m.get('source') == 'session', 'receipt authority differs')
            matches.append(row)
    require(len(matches) <= 1, 'duplicate native release receipts')
    return matches


def absence_before(rows, session, message):
    require(not matching_receipts(rows, session, message), 'release already exists')


def poller_identity(value, session, expected_executable, expected_sha256, owned_cgroup):
    require(type(value) is dict and value.get('alive') is True, 'native poller absent or dead')
    require(type(value.get('pid')) is int and value['pid'] > 1
            and type(value.get('start_ticks')) is int and value['start_ticks'] > 0,
            'native poller identity malformed')
    require(value.get('uid') == value.get('gid') == 1000
            and type(value.get('ppid')) is int and value['ppid'] > 0
            and value.get('executable_sha256') == expected_sha256,
            'native poller executable authority differs')
    require(re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is not None,
            'poller executable binding malformed')
    require(value.get('argv') == [expected_executable, 'nudge', 'poll', '--city',
            '/home/loucmane/gascity/city', '--session', session['session_name'], session['id']],
            'native poller argv differs')
    require(isinstance(owned_cgroup, str) and (
            owned_cgroup == CORE_CGROUP or re.fullmatch(
                r'0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-[A-Za-z0-9_.-]+\.service\n',
                owned_cgroup) is not None)
            and value.get('cgroup') == owned_cgroup, 'native poller outside reviewed service')
    return {k: value[k] for k in ('pid', 'start_ticks', 'ppid', 'uid', 'gid', 'argv',
                                 'executable_sha256', 'cgroup')}


def transcript_ingress(before, after, message):
    require(type(before) is bytes and type(after) is bytes and len(after) <= 32 << 20,
            'native transcript size or type')
    require(before.endswith(b'\n') and after.startswith(before), 'native transcript prefix changed')
    expected = native_payload(message).rstrip('\n')
    found = []
    suffix = after[len(before):]
    # A writer can be between bytes of its last line. Only complete records count.
    lines = suffix.split(b'\n')[:-1]
    for raw in lines:
        require(bool(raw), 'empty native transcript record')
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError('malformed native transcript record') from exc
        require(type(record) is dict, 'native transcript record shape')
        p = record.get('payload', {})
        require(type(p) is dict, 'native transcript payload shape')
        if record.get('type') != 'response_item' or p.get('type') != 'message' or p.get('role') != 'user':
            continue
        content = p.get('content')
        require(type(content) is list and all(type(x) is dict for x in content),
                'native user message shape')
        texts = [x.get('text') for x in content if x.get('type') in ('input_text', 'text')]
        require(all(isinstance(t, str) for t in texts), 'native user text shape')
        require(len(texts) == 1 and texts[0].rstrip('\n') == expected,
                'native release payload differs')
        found.append(record)
    require(len(found) <= 1, 'duplicate native release ingress')
    return bool(found)


def queue_items(queue):
    # Read the native file without invoking `nudge status`: status also runs
    # global expiry maintenance. Empty slices are omitted by Core's encoder.
    require(type(queue) is dict and not set(queue) - {'pending', 'in_flight', 'dead'},
            'native queue file shape')
    result = {}
    for name in ('pending', 'in_flight', 'dead'):
        entries = queue.get(name, [])
        require(type(entries) is list and len(entries) <= 4096, 'native queue collection shape')
        for item in entries:
            require(type(item) is dict and isinstance(item.get('id'), str)
                    and re.fullmatch(r'nudge-[0-9a-f]{12}', item['id']), 'native queued item shape')
            require(item['id'] not in result, 'duplicate native queue identity')
            result[item['id']] = (name, item)
    return result


def queue_baseline(queue, session):
    items = queue_items(queue)
    for name, item in items.values():
        if name != 'dead':
            require(isinstance(item.get('session_id'), str) and item['session_id']
                    and item['session_id'] != session['id'],
                    'prior active nudge is not fenced away from this session')
    return items


def time_window_ns(value):
    require(type(value) in (tuple, list) and len(value) == 2
            and all(type(x) is int and x > 0 for x in value)
            and value[0] <= value[1], 'historical expiry time window malformed')
    return value


def timestamp_ns(value):
    """RFC3339 at integer nanosecond precision; never silently round Go timestamps."""
    require(isinstance(value, str), 'historical expiry timestamp malformed')
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})', value)
    require(match is not None, 'historical expiry timestamp malformed')
    zone = match[3]
    require(zone == 'Z' or (int(zone[1:3]) <= 23 and int(zone[4:6]) <= 59),
            'historical expiry timezone malformed')
    try:
        instant = datetime.fromisoformat(match[1] + match[3].replace('Z', '+00:00'))
        delta = instant.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise RuntimeError('historical expiry timestamp malformed') from exc
    result = (delta.days * 86400 + delta.seconds) * 10**9 + int((match[2] or '').ljust(9, '0'))
    require(result > 0, 'historical expiry timestamp is zero or pre-epoch')
    return result


def preserved_history(prior, current, session, baseline_window_ns=None,
                      observed_window_ns=None, previous_history=None):
    """Exact equality, or Core's single pending-to-dead expiry transformation.

    No removals, in-flight transitions, retained-dead cleanup or arbitrary mutable
    field projection. The first accepted dead tuple stays exact thereafter.
    """
    if previous_history is not None:
        require(type(previous_history) is dict and set(previous_history) == set(prior),
                'historical queue checkpoint differs')
    evidence = []
    for identity, before in prior.items():
        after = current.get(identity)
        require(after is not None, 'preserved historical queue changed')
        previous = previous_history.get(identity) if previous_history is not None else before
        if previous != before:
            require(after == previous, 'accepted historical expiry changed or resurrected')
        if after == before:
            continue
        require(before[0] == 'pending' and after[0] == 'dead'
                and isinstance(before[1].get('session_id'), str)
                and before[1]['session_id'] and before[1]['session_id'] != session['id'],
                'preserved historical queue changed')
        baseline = time_window_ns(baseline_window_ns)
        observed = time_window_ns(observed_window_ns)
        require(observed[0] >= baseline[1], 'historical expiry clock reversed')
        expires = timestamp_ns(before[1].get('expires_at'))
        dead = timestamp_ns(after[1].get('dead_at'))
        require(expires <= baseline[0] <= dead <= observed[1],
                'historical expiry outside captured time bounds')
        require(before[1].get('dead_at') in (None, '0001-01-01T00:00:00Z'),
                'pending historical item already has death time')
        expected = dict(before[1], dead_at=after[1]['dead_at'])
        if expected.get('last_error', '') == '':
            expected['last_error'] = 'expired'
        require(after[1] == expected, 'historical expiry rewrote immutable fields')
        evidence.append(dict(id=identity, before=before, after=after,
                             baseline_window_ns=list(baseline),
                             observed_window_ns=list(observed)))
    return evidence


def acknowledged(rows, queue, session, message, started_epoch, queue_before, *,
                 baseline_window_ns=None, observed_window_ns=None, previous_history=None):
    require(type(started_epoch) in (int, float) and math.isfinite(started_epoch),
            'release start time malformed')
    matches = matching_receipts(rows, session, message)
    prior = queue_baseline(queue_before, session)
    current = queue_items(queue)
    preserved_history(prior, current, session, baseline_window_ns,
                      observed_window_ns, previous_history)
    fresh = [value for key, value in current.items() if key not in prior]
    require(len(fresh) <= 1, 'unexpected or duplicate new nudge')
    for name, item in fresh:
        require(item.get('session_id') == session['id'] and item.get('message') == message
                and item.get('source') == 'session' and item.get('agent') == 'gascity/codex'
                and item.get('continuation_epoch') == session['continuation_epoch'],
                'new queued release identity differs')
        require(name != 'dead', 'native release delivery failed')
    if not matches:
        return None
    row = matches[0]
    m = row['metadata']
    nudge = m.get('nudge_id', '')
    require(re.fullmatch(r'nudge-[0-9a-f]{12}', nudge) is not None, 'native nudge ID malformed')
    try:
        created = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        require(created.tzinfo is not None and created.timestamp() >= math.floor(started_epoch),
                'native release receipt predates intent')
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RuntimeError('native receipt timestamp malformed') from exc
    require(m.get('continuation_epoch') == session['continuation_epoch'],
            'receipt continuation epoch differs')
    for _, item in fresh:
        require(item['id'] == nudge and item.get('bead_id') == row['id'],
                'native queue and receipt differ')
    state = m.get('state')
    if state != 'injected':
        require(row.get('status') == 'open' and state in ('queued', 'in_flight'),
                'native receipt failed or unknown')
        return None
    require(row.get('status') == 'closed' and m.get('commit_boundary') == 'provider-nudge-return'
            and m.get('terminal_reason') == '' and not m.get('last_error'),
            'native delivery acknowledgement differs')
    if fresh:
        return None  # Receipt close and queue removal are not one atomic read.
    return dict(bead_id=row['id'], nudge_id=nudge, commit_boundary=m['commit_boundary'])


def wait(observe, monotonic, sleep, session, message, before, started_epoch, queue_before,
         expected_executable, expected_sha256, owned_cgroup, timeout=MAX_WAIT_SECONDS,
         initial_identity=None, baseline_window_ns=None, record_history=None):
    require(type(timeout) in (int, float) and 0 < timeout <= MAX_WAIT_SECONDS,
            'release wait budget invalid')
    deadline = monotonic() + timeout
    identity = initial_identity
    prior = queue_baseline(queue_before, session)
    previous_history = None
    recorded_expirations = {}
    previous_window = None
    for _ in range(MAX_OBSERVATIONS):
        remaining = deadline - monotonic()
        require(remaining > 0, 'native release delivery timeout')
        snapshot = observe(remaining)
        require(monotonic() <= deadline, 'native release delivery timeout')
        current = poller_identity(snapshot['poller'], session, expected_executable,
                                  expected_sha256, owned_cgroup)
        if identity is None:
            identity = current
        require(identity == current, 'native poller identity changed')
        observed_window = snapshot.get('observed_window_ns')
        if previous_window is not None:
            require(time_window_ns(observed_window)[0] >= previous_window[1],
                    'historical expiry observation clock reversed')
        current_queue = queue_items(snapshot['queue'])
        expirations = preserved_history(prior, current_queue, session, baseline_window_ns,
                                        observed_window, previous_history)
        fresh_expirations = [row for row in expirations if row['id'] not in recorded_expirations]
        if fresh_expirations:
            require(callable(record_history), 'historical expiry evidence recorder required')
            record_history(fresh_expirations)
            recorded_expirations.update((row['id'], row) for row in fresh_expirations)
        receipt = acknowledged(snapshot['receipts'], snapshot['queue'], session, message,
                               started_epoch, queue_before, baseline_window_ns=baseline_window_ns,
                               observed_window_ns=observed_window, previous_history=previous_history)
        previous_history = {key: current_queue[key] for key in prior}
        if observed_window is not None:
            previous_window = tuple(time_window_ns(observed_window))
        ingress = transcript_ingress(before, snapshot['transcript'], message)
        if receipt is not None and ingress:
            return dict(delivered=True, receipt=receipt, poller=identity,
                        historical_expirations=list(recorded_expirations.values()),
                        transcript_sha256=hashlib.sha256(snapshot['transcript']).hexdigest())
        sleep(min(1, max(0, deadline - monotonic())))
    raise RuntimeError('native release observation count exhausted')
