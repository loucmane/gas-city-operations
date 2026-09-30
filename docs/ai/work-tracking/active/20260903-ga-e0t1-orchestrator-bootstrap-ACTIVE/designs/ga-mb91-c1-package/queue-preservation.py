"""Pure full-record preservation for the scoped ga-mb91 window.

No I/O, maintenance, permissions or execution authority. All pre-window queue
records and shadow Beads remain foreign even when they name the same session
with an older epoch. Production observations must be obtained by the bound
read-only adapter before any poller-capable transition.
"""
import copy
import hashlib
import json
import re

LIMIT = 4096


def require(value, message):
    if not value:
        raise RuntimeError(message)


def queue_records(value):
    require(type(value) is dict and not set(value) - {'pending', 'in_flight', 'dead'},
            'queue shape')
    records = {}
    for bucket in ('pending', 'in_flight', 'dead'):
        rows = value.get(bucket, [])
        require(type(rows) is list and len(rows) <= LIMIT, 'queue bucket bound')
        for row in rows:
            require(type(row) is dict and isinstance(row.get('id'), str)
                    and re.fullmatch(r'nudge-[0-9a-f]{12}', row['id']), 'queue identity')
            require(row['id'] not in records, 'duplicate queue identity')
            records[row['id']] = [bucket, copy.deepcopy(row)]
    require(len(records) <= LIMIT, 'total queue bound')
    return records


def bead_records(rows):
    require(type(rows) is list and len(rows) <= LIMIT, 'Bead observation incomplete')
    records = {}
    for row in rows:
        require(type(row) is dict and isinstance(row.get('id'), str) and row['id']
                and type(row.get('metadata')) is dict
                and type(row.get('labels')) is list and 'gc:nudge' in row['labels']
                and row.get('issue_type') == 'chore', 'shadow Bead shape')
        require(row['id'] not in records, 'duplicate shadow Bead')
        records[row['id']] = copy.deepcopy(row)
    return records


def record_sha256(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


def absent_records(q, b, absent_dead):
    require(type(absent_dead) is dict and len(absent_dead) <= LIMIT,
            'historical absence shape')
    ids = set()
    for identity, record in absent_dead.items():
        require(type(record) is dict and set(record) == {'bucket', 'bead_id', 'record_sha256'}
                and record['bucket'] == 'dead' and identity in q
                and q[identity][0] == 'dead'
                and q[identity][1].get('bead_id') == record['bead_id']
                and record_sha256(q[identity]) == record['record_sha256'],
                'historical absence tuple differs')
        bid = record['bead_id']
        require(isinstance(bid, str) and re.fullmatch(r'ci-[a-z0-9-]+', bid)
                and bid not in ids, 'historical absence Bead identity')
        ids.add(bid)
        require(bid not in b and not any(row['metadata'].get('nudge_id') == identity
                                        or 'nudge:' + identity in row['labels']
                                        for row in b.values()),
                'historical shadow appeared or was remapped')
    return copy.deepcopy(absent_dead)


def baseline(queue, beads, absent_dead=None):
    q, b = queue_records(queue), bead_records(beads)
    absent = absent_records(q, b, {} if absent_dead is None else absent_dead)
    for _, row in q.values():
        if row['id'] in absent:
            continue  # Exact, independently frozen DEAD tuple only.
        identity = row.get('bead_id')
        if identity in (None, ''):
            # Core permits an unlinked historical queue row. The adapter's
            # complete global list must prove the shadow absent; never invent
            # a mapping or ignore a row that actually has a shadow.
            require(not any(item['metadata'].get('nudge_id') == row['id']
                            for item in b.values()), 'unlinked queue has ambiguous shadow')
            continue
        require(isinstance(identity, str) and identity in b,
                'queue backing Bead missing')
        require(b[identity]['metadata'].get('nudge_id') == row['id'],
                'queue backing Bead identity differs')
    return dict(schema='ga-mb91.foreign-history.v2', queue=q, beads=b, absent_dead=absent)


def bound_session(session):
    require(type(session) is dict
            and isinstance(session.get('id'), str)
            and re.fullmatch(r'ci-[a-z0-9]+', session['id'])
            and session.get('session_name') == 'codex-' + session['id']
            and isinstance(session.get('continuation_epoch'), str)
            and re.fullmatch(r'[1-9][0-9]*', session['continuation_epoch']),
            'owned session is not exactly bound')


def owned(row, session):
    return (row.get('session_id') == session['id']
            and row.get('continuation_epoch') == session['continuation_epoch']
            and row.get('agent') == 'gascity/codex')


def preserve(frozen, queue, beads, session=None):
    require(type(frozen) is dict and set(frozen) == {'schema', 'queue', 'beads', 'absent_dead'}
            and frozen['schema'] == 'ga-mb91.foreign-history.v2', 'baseline schema')
    q, b = queue_records(queue), bead_records(beads)
    if session is not None:
        bound_session(session)
    for identity, record in frozen['queue'].items():
        require(q.get(identity) == record, 'foreign queue tuple changed: ' + identity)
    for identity, record in frozen['beads'].items():
        require(b.get(identity) == record, 'foreign shadow Bead changed: ' + identity)
    # Before the owned-new-record exception: not even this session may recreate
    # or remap a missing historical shadow.
    absent_records(q, b, frozen['absent_dead'])
    new_q = {key: value for key, value in q.items() if key not in frozen['queue']}
    new_b = {key: value for key, value in b.items() if key not in frozen['beads']}
    if new_q or new_b:
        require(session is not None, 'new history before owned session')
    for _, row in new_q.values():
        require(owned(row, session), 'unexpected new foreign queue record')
    for row in new_b.values():
        require(owned(row['metadata'], session), 'unexpected new foreign shadow Bead')
    # The queue and its shadows are not transactional together. No new mapping
    # is inferred here; delivery has its own receipt/queue/transcript barrier.
    return dict(ok=True, foreign_queue=len(frozen['queue']),
                foreign_beads=len(frozen['beads']), owned_queue=len(new_q), owned_beads=len(new_b))


def scoped_configuration(config, expected, orders, expected_orders):
    require(config == expected and orders == expected_orders, 'native config or orders drift')
    require(config.get('ok') is True and config['config']['Session']['NudgeQueueScope'] == 'session-epoch',
            'session epoch scope missing')
    require(config['config']['Daemon']['NudgeDispatcher'] in ('', 'legacy'),
            'shared dispatcher is active')
    require([row['name'] for row in orders['orders']] == ['nudge-on-route'],
            'shared maintenance is active')
    return True
