"""R1 RED: owned ordinary reminders and exact release are distinct records."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('reminder_delivery',ROOT/'release-delivery-r13.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
S=dict(id='ci-fixture',session_name='codex-ci-fixture',continuation_epoch='1')
M='SOURCE RELEASE: fixture'
O='check for assigned work'
BEFORE=b'{"type":"fixture"}\n'
START=1790760000

def receipt(message=O, identity='nudge-111111111111', state='injected'):
    return dict(id='ci-'+identity[-12:], issue_type='chore', labels=['gc:nudge'],
        status='closed' if state=='injected' else 'open', created_at='2026-09-30T10:40:01Z',
        metadata=dict(session_id=S['id'],continuation_epoch='1',message=message,
          agent='gascity/codex',source='session',nudge_id=identity,state=state,
          commit_boundary='provider-nudge-return',terminal_reason='',last_error=''))

def queued(row):
    m=row['metadata']
    return dict(id=m['nudge_id'],bead_id=row['id'],**{k:m[k] for k in
        ('session_id','continuation_epoch','message','agent','source')})

def ingress(messages):
    head=('a deferred reminder that was' if len(messages)==1 else str(len(messages))+' deferred reminders that were')
    payload='<system-reminder>\nYou have '+head+' queued until a safe boundary:\n\n'
    payload+=''.join('- [session] '+m+'\n' for m in messages)+'\nHandle them after this turn.\n</system-reminder>'
    return (json.dumps(dict(type='response_item',payload=dict(type='message',role='user',
        content=[dict(type='input_text',text=payload)])))+'\n').encode()

def test_ordinary_pending_does_not_become_the_release():
    ordinary=receipt(state='queued');release=receipt(M,'nudge-222222222222')
    assert d.acknowledged([ordinary,release],dict(pending=[queued(ordinary)]),S,M,START,{})['nudge_id']=='nudge-222222222222'

@pytest.mark.parametrize('messages',[[O,M],[M,O]])
def test_receipt_bound_native_batch_keeps_exact_release_proof(messages):
    rows=[receipt(),receipt(M,'nudge-222222222222')]
    assert d.transcript_ingress(BEFORE,BEFORE+ingress(messages),M,rows=rows,session=S)

def test_ordinary_separate_then_release_is_supported():
    rows=[receipt(),receipt(M,'nudge-222222222222')]
    assert d.transcript_ingress(BEFORE,BEFORE+ingress([O])+ingress([M]),M,rows=rows,session=S)

def test_receipt_race_waits_without_false_delivery():
    assert not d.transcript_ingress(BEFORE,BEFORE+ingress([O,M]),M,rows=[receipt(state='queued')],session=S)

@pytest.mark.parametrize('messages',[[M,M],[O,'unknown'],[O,M,'unknown']])
def test_unknown_or_duplicate_ingress_refuses(messages):
    with pytest.raises(RuntimeError):
        d.transcript_ingress(BEFORE,BEFORE+ingress(messages),M,rows=[receipt()],session=S)

@pytest.mark.parametrize('field,value',[('session_id','ci-other'),('continuation_epoch','2'),('source','mail'),('agent','other'),('message','unknown')])
def test_unknown_queue_addition_refuses(field,value):
    ordinary=receipt(state='queued');item=queued(ordinary);item[field]=value
    with pytest.raises(RuntimeError):d.acknowledged([ordinary],dict(pending=[item]),S,M,START,{})

def test_pending_ordinary_is_admitted_before_spending_enqueue():
    ordinary=receipt(state='queued')
    assert d.admit_before([ordinary],dict(pending=[queued(ordinary)]),{},S,M)==['nudge-111111111111']

def test_unbacked_ordinary_refuses_before_enqueue():
    with pytest.raises(RuntimeError):d.admit_before([],dict(pending=[queued(receipt())]),{},S,M)

@pytest.mark.parametrize('messages',[[M],[O,M]])
def test_release_ingress_before_enqueue_refuses(messages):
    with pytest.raises(RuntimeError,match='before enqueue'):
        d.transcript_before(BEFORE,BEFORE+ingress(messages),M,[receipt()],S)

def test_unreceipted_ordinary_ingress_before_enqueue_refuses():
    with pytest.raises(RuntimeError,match='before enqueue'):
        d.transcript_before(BEFORE,BEFORE+ingress([O]),M,[],S)
