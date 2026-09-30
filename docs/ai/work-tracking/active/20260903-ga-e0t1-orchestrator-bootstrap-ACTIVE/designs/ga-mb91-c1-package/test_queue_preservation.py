import copy
from pathlib import Path
import types

import pytest

HERE = Path(__file__).parent
p = types.ModuleType('queue_preservation')
p.__file__ = str(HERE/'queue-preservation.py')
exec(compile((HERE/'queue-preservation.py').read_bytes(), p.__file__, 'exec'), p.__dict__)

SESSION = dict(id='ci-owned', session_name='codex-ci-owned', continuation_epoch='2')


def fixture():
    buckets = {'pending': [], 'in_flight': [], 'dead': []}
    beads = []
    for i, (bucket, sid, epoch) in enumerate([
        ('pending', 'ci-foreign', '1'), ('in_flight', 'ci-foreign', '1'),
        ('dead', 'ci-foreign', '1'), ('pending', '', ''), ('dead', 'ci-owned', '1'),
        ('pending', 'ci-owned', '1'),
    ]):
        ident, bid = 'nudge-' + format(i, '012x'), 'ci-shadow' + str(i)
        row = dict(id=ident, bead_id=bid, session_id=sid, continuation_epoch=epoch,
                   agent='gascity/codex', message='preserved', expires_at='2020-01-01T00:00:00Z')
        buckets[bucket].append(row)
        beads.append(dict(id=bid, issue_type='chore', status='closed' if bucket == 'dead' else 'open',
                          labels=['gc:nudge'], metadata=dict(nudge_id=ident, session_id=sid,
                          continuation_epoch=epoch, agent='gascity/codex', state=bucket)))
    return buckets, beads


def test_empty_owned_first_tick_preserves_expired_unfenced_old_epoch_and_dead():
    q, b = fixture()
    frozen = p.baseline(q, b)
    assert p.preserve(frozen, q, b) == dict(ok=True, foreign_queue=6, foreign_beads=6,
                                         owned_queue=0, owned_beads=0)
    assert p.preserve(frozen, q, b, SESSION)['ok']


@pytest.mark.parametrize('bucket', ['pending', 'in_flight', 'dead'])
@pytest.mark.parametrize('mutation', ['delete', 'move', 'message', 'epoch', 'expiry'])
def test_every_foreign_queue_mutation_refuses(bucket, mutation):
    q, b = fixture(); frozen = p.baseline(q, b)
    row = q[bucket][0]
    if mutation == 'delete': q[bucket].pop(0)
    elif mutation == 'move': q['dead' if bucket != 'dead' else 'pending'].append(q[bucket].pop(0))
    elif mutation == 'message': row['message'] = 'changed'
    elif mutation == 'epoch': row['continuation_epoch'] = '2'
    else: row['dead_at'] = '2026-09-30T00:00:00Z'
    with pytest.raises(RuntimeError, match='foreign queue tuple changed'):
        p.preserve(frozen, q, b, SESSION)


@pytest.mark.parametrize('mutation', ['delete', 'close', 'metadata', 'labels', 'notes'])
def test_every_foreign_shadow_mutation_refuses(mutation):
    q, b = fixture(); frozen = p.baseline(q, b)
    if mutation == 'delete': b.pop()
    elif mutation == 'close': b[0]['status'] = 'closed'
    elif mutation == 'metadata': b[0]['metadata']['state'] = 'injected'
    elif mutation == 'labels': b[0]['labels'].append('modified')
    else: b[0]['notes'] = 'modified'
    with pytest.raises(RuntimeError, match='foreign shadow Bead changed'):
        p.preserve(frozen, q, b, SESSION)


def add_owned(q, b):
    ident = 'nudge-ffffffffffff'
    row = dict(id=ident, bead_id='ci-fresh', session_id=SESSION['id'],
               continuation_epoch='2', agent='gascity/codex', message='SOURCE RELEASE: frozen')
    q['pending'].append(row)
    b.append(dict(id='ci-fresh', issue_type='chore', status='open', labels=['gc:nudge'],
                  metadata=dict(row, nudge_id=ident, state='queued')))


def test_owned_enqueue_ack_and_withdrawal_do_not_rewrite_foreign_history():
    q, b = fixture(); frozen = p.baseline(q, b); add_owned(q, b)
    assert p.preserve(frozen, q, b, SESSION)['owned_queue'] == 1
    q['pending'].pop(); b[-1]['status'] = 'closed'; b[-1]['metadata']['state'] = 'injected'
    assert p.preserve(frozen, q, b, SESSION)['owned_beads'] == 1
    b[-1]['metadata']['state'] = 'failed'
    assert p.preserve(frozen, q, b, SESSION)['ok']


@pytest.mark.parametrize('field,value', [('session_id','ci-other'),('continuation_epoch','1'),('agent','hpfetcher/codex')])
def test_new_foreign_records_never_exempt(field, value):
    q, b = fixture(); frozen = p.baseline(q, b); add_owned(q, b)
    q['pending'][-1][field] = value
    with pytest.raises(RuntimeError, match='new foreign queue'):
        p.preserve(frozen, q, b, SESSION)
    q['pending'].pop(); b[-1]['metadata'][field] = value
    with pytest.raises(RuntimeError, match='new foreign shadow'):
        p.preserve(frozen, q, b, SESSION)


def test_no_new_history_before_session_is_bound():
    q, b = fixture(); frozen = p.baseline(q, b); add_owned(q, b)
    with pytest.raises(RuntimeError, match='before owned session'): p.preserve(frozen, q, b)


def test_baseline_deepcopies_and_requires_backing_identity():
    q, b = fixture(); frozen = p.baseline(q, b)
    q['dead'][0]['message'] = 'new'
    assert frozen['queue']['nudge-000000000002'][1]['message'] == 'preserved'
    b[0]['metadata']['nudge_id'] = 'wrong'
    with pytest.raises(RuntimeError, match='backing Bead identity'): p.baseline(q, b)
    b.pop(0)
    with pytest.raises(RuntimeError, match='backing Bead missing'): p.baseline(q, b)


def config():
    return dict(ok=True, config=dict(Session=dict(NudgeQueueScope='session-epoch'),
                                    Daemon=dict(NudgeDispatcher='')))


@pytest.mark.parametrize('scope', ['', 'global', 'invalid', None])
def test_scope_must_be_exact_even_if_supplied_expected_is_wrong(scope):
    c=config(); c['config']['Session']['NudgeQueueScope']=scope
    orders=dict(orders=[dict(name='nudge-on-route')])
    with pytest.raises(RuntimeError, match='scope missing'):
        p.scoped_configuration(c, c, orders, orders)


def test_dispatcher_orders_and_native_drift_refused():
    c=config(); orders=dict(orders=[dict(name='nudge-on-route')])
    assert p.scoped_configuration(c,c,orders,orders)
    wrong=copy.deepcopy(c); wrong['config']['Daemon']['NudgeDispatcher']='singleton'
    with pytest.raises(RuntimeError, match='dispatcher'): p.scoped_configuration(wrong,wrong,orders,orders)
    wrong=copy.deepcopy(orders); wrong['orders'].append(dict(name='nudge-mail-sweep'))
    with pytest.raises(RuntimeError, match='maintenance'): p.scoped_configuration(c,c,wrong,wrong)
    wrong=copy.deepcopy(c); wrong['extra']=1
    with pytest.raises(RuntimeError, match='drift'): p.scoped_configuration(wrong,c,orders,orders)


def test_raw_serialization_order_is_not_semantic_mutation():
    q,b=fixture(); frozen=p.baseline(q,b)
    q['pending'].reverse(); b.reverse()
    assert p.preserve(frozen,q,b)['ok']


def test_duplicate_queue_bead_and_full_page_refuse():
    q,b=fixture(); q['dead'].append(copy.deepcopy(q['pending'][0]))
    with pytest.raises(RuntimeError, match='duplicate queue'): p.baseline(q,b)
    q,b=fixture(); b.append(copy.deepcopy(b[0]))
    with pytest.raises(RuntimeError, match='duplicate shadow'): p.baseline(q,b)
    with pytest.raises(RuntimeError, match='incomplete'): p.bead_records([{}]*(p.LIMIT+1))


def test_exact_absence_for_historical_unlinked_row_is_preserved():
    q,b=fixture(); row=q['dead'][0]; bid=row.pop('bead_id')
    with pytest.raises(RuntimeError, match='ambiguous shadow'): p.baseline(q,b)
    b=[record for record in b if record['id']!=bid]
    frozen=p.baseline(q,b)
    assert p.preserve(frozen,q,b)['ok']
    row['bead_id']=bid
    with pytest.raises(RuntimeError, match='foreign queue tuple changed'): p.preserve(frozen,q,b)
