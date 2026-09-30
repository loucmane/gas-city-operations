"""Pure predicates for a bounded native release acknowledgement barrier.

This module grants nothing, enqueues nothing and reads no live state. The frozen
successor adapter must obtain every input from the existing supported native
surfaces while its own oneshot cgroup remains alive. Fresh scoped successor requires exact foreign preservation with no expiry exception.
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
ORDINARY_REMINDER = 'check for assigned work'


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


def ordinary_receipts(rows, session):
    """Only the pinned nudge-on-route text in the exact current epoch."""
    require(type(rows) is list and len(rows) <= 4096, 'ordinary receipt bound')
    result = {}
    for row in rows:
        require(type(row) is dict and type(row.get('metadata', {})) is dict,
                'ordinary receipt shape')
        m = row.get('metadata', {})
        if not (m.get('message') == ORDINARY_REMINDER and m.get('session_id') == session['id']
                and m.get('continuation_epoch') == session['continuation_epoch']):
            continue
        identity = m.get('nudge_id', '')
        require(isinstance(identity, str) and re.fullmatch(r'nudge-[0-9a-f]{12}', identity)
                and identity not in result and isinstance(row.get('id'), str) and row['id']
                and row.get('issue_type') == 'chore' and type(row.get('labels')) is list
                and 'gc:nudge' in row['labels']
                and m.get('agent') == 'gascity/codex' and m.get('source') == 'session',
                'ordinary receipt authority differs')
        state = m.get('state')
        require((state in ('queued', 'in_flight') and row.get('status') == 'open')
                or (state == 'injected' and row.get('status') in ('open', 'closed')
                    and m.get('commit_boundary') == 'provider-nudge-return'
                    and m.get('terminal_reason') == '' and not m.get('last_error')),
                'ordinary receipt failed or unknown')
        result[identity] = row
    return result


def transcript_counts(before, after, message):
    require(type(before) is bytes and type(after) is bytes and len(after) <= 32 << 20,
            'native transcript size or type')
    require(before.endswith(b'\n') and after.startswith(before), 'native transcript prefix changed')
    native_payload(message)  # Validate the exact release string first.
    found = []
    ordinary_count = 0
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
        require(len(texts) == 1, 'native release payload differs')
        text = texts[0].rstrip('\n')
        parts = text.split('\n')
        require(len(parts) >= 7 and parts[0] == '<system-reminder>' and parts[2] == ''
                and parts[-3:] == ['', 'Handle them after this turn.', '</system-reminder>'],
                'native release payload differs')
        entries = parts[3:-3]
        require(0 < len(entries) <= 129, 'native reminder batch bound')
        header = ('You have a deferred reminder that was queued until a safe boundary:'
                  if len(entries) == 1 else
                  'You have '+str(len(entries))+' deferred reminders that were queued until a safe boundary:')
        require(parts[1] == header and all(x in ('- [session] '+message,
                '- [session] '+ORDINARY_REMINDER) for x in entries), 'native release payload differs')
        found.extend(record for x in entries if x == '- [session] '+message)
        ordinary_count += entries.count('- [session] '+ORDINARY_REMINDER)
    require(len(found) <= 1, 'duplicate native release ingress')
    return len(found), ordinary_count


def transcript_before(before, after, message, rows, session):
    releases, ordinary_count = transcript_counts(before, after, message)
    ordinary = ordinary_receipts(rows, session)
    injected = sum(r['metadata']['state'] == 'injected' and r['status'] == 'closed'
                   for r in ordinary.values())
    require(releases == 0, 'release ingress before enqueue')
    return dict(ordinary_ingress=ordinary_count, release_ingress=0,
                settled=ordinary_count <= injected)


def transcript_ingress(before, after, message, *, rows=None, session=None):
    releases, ordinary_count = transcript_counts(before, after, message)
    ordinary = ordinary_receipts(rows, session) if rows is not None else {}
    # Receipt read may precede native injection/close by a few milliseconds.
    # Never infer delivery from transcript alone; the bounded observer rereads.
    injected = sum(r['metadata']['state'] == 'injected' and r['status'] == 'closed'
                   for r in ordinary.values())
    return releases == 1 and ordinary_count <= injected


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
    # Every pre-poller tuple is foreign. Unfenced and older-epoch history remains
    # exact; its presence grants no authority to the new worker.
    return queue_items(queue)


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
    """Session-scoped Core must leave every foreign tuple byte-equivalent."""
    if previous_history is not None:
        require(previous_history == prior, 'historical queue checkpoint differs')
    for identity, before in prior.items():
        require(current.get(identity) == before, 'preserved historical queue changed')
    return []


def fresh_release_items(prior, current, rows, session, message):
    ordinary = ordinary_receipts(rows, session)
    release = []
    for identity, (bucket, item) in current.items():
        if identity in prior:
            continue
        require(item.get('session_id') == session['id'] and item.get('source') == 'session'
                and item.get('agent') == 'gascity/codex'
                and item.get('continuation_epoch') == session['continuation_epoch'],
                'new queued release identity differs')
        require(bucket != 'dead', 'native release delivery failed')
        if item.get('message') == message:
            release.append((bucket, item))
        else:
            row = ordinary.get(identity)
            require(item.get('message') == ORDINARY_REMINDER and row is not None
                    and item.get('bead_id') == row['id'], 'unbacked or unknown owned reminder')
    require(len(release) <= 1, 'unexpected or duplicate new nudge')
    return release


def admit_before(rows, queue, queue_before, session, message):
    absence_before(rows, session, message)
    prior = queue_baseline(queue_before, session); current = queue_items(queue)
    preserved_history(prior, current, session)
    require(not fresh_release_items(prior, current, rows, session, message), 'release already queued')
    return sorted(key for key in current if key not in prior)


def acknowledged(rows, queue, session, message, started_epoch, queue_before, *,
                 baseline_window_ns=None, observed_window_ns=None, previous_history=None):
    require(type(started_epoch) in (int, float) and math.isfinite(started_epoch),
            'release start time malformed')
    matches = matching_receipts(rows, session, message)
    prior = queue_baseline(queue_before, session)
    current = queue_items(queue)
    preserved_history(prior, current, session, baseline_window_ns,
                      observed_window_ns, previous_history)
    fresh = fresh_release_items(prior, current, rows, session, message)
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
    require(row.get('status') in ('open', 'closed') and m.get('commit_boundary') == 'provider-nudge-return'
            and m.get('terminal_reason') == '' and not m.get('last_error'),
            'native delivery acknowledgement differs')
    if row['status'] == 'open':
        return None  # Native SetMetadataBatch and Close are separate writes.
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
        ingress = transcript_ingress(before, snapshot['transcript'], message,
                                     rows=snapshot['receipts'], session=session)
        if receipt is not None and ingress:
            return dict(delivered=True, receipt=receipt, poller=identity,
                        historical_expirations=list(recorded_expirations.values()),
                        transcript_sha256=hashlib.sha256(snapshot['transcript']).hexdigest())
        sleep(min(1, max(0, deadline - monotonic())))
    raise RuntimeError('native release observation count exhausted')
