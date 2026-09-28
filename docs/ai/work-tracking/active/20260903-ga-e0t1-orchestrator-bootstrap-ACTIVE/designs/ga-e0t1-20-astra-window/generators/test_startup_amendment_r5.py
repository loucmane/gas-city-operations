"""Pure exact-note reconciliation on preserved Bead fixtures. No ledger calls."""
import copy
import json
from pathlib import Path

import pytest

import startup_r5 as r
import startup_amendment_contract_r5 as c


@pytest.fixture
def case():
    before=json.loads(Path('/var/tmp/ga-e0t1.20-link-completion-20260928-r2/final.json').read_bytes())
    amendment=json.loads(r.components()[1]['startup-amendment-r5.json'])
    legacy=r.source_module(r.frozen()['continuation-admission.py'],'legacy')
    after=copy.deepcopy(before)
    after['task']['notes']=amendment['after_note']
    after['task']['updated_at']='2026-09-28T12:30:00+00:00'
    [projection]=[row for row in after['parent']['dependencies'] if row['id']==c.TASK]
    for key in ('notes','updated_at'):projection[key]=after['task'][key]
    return before,after,amendment,legacy.compare_pair


def test_only_exact_append_and_projection_change_pass(case):
    before,after,amend,compare=case
    pins=c.delta(*case)
    result=dict(pins,ok=True,task=c.TASK,only_startup_note_appended=True,
                route_preserved=True,assigned=False,worker_launched=False)
    assert c.accepted(before,after,result,amend,compare)==after
    assert before['task']['notes']==amend['before_note']


@pytest.mark.parametrize('field',['status','metadata','description','title','assignee','unknown'])
def test_no_other_task_field_can_change(case,field):
    before,after,amend,compare=case
    after['task'][field]='changed'
    with pytest.raises(RuntimeError):c.delta(before,after,amend,compare)


@pytest.mark.parametrize('kind',['erase','duplicate','suffix','missing-projection','wrong-projection','parent-edit'])
def test_note_and_parent_negatives(case,kind):
    before,after,amend,compare=case
    if kind=='erase':after['task']['notes']=amend['append_note']
    if kind=='duplicate':after['task']['notes']+='\n'+amend['append_note']
    if kind=='suffix':after['task']['notes']+=' other'
    if kind=='missing-projection':
        after['parent']['dependencies']=[r for r in after['parent']['dependencies'] if r['id']!=c.TASK]
    if kind=='wrong-projection':
        [row]=[r for r in after['parent']['dependencies'] if r['id']==c.TASK]
        row['notes']='different'
    if kind=='parent-edit':after['parent']['notes']+=' concurrent'
    with pytest.raises(RuntimeError):c.delta(before,after,amend,compare)


@pytest.mark.parametrize('stamp',['2000-01-01T00:00:00Z','2026-09-28T13:00:00','bad',False])
def test_time_refuses(case,stamp):
    before,after,amend,compare=case
    after['task']['updated_at']=stamp
    with pytest.raises((RuntimeError,ValueError)):c.delta(before,after,amend,compare)


def test_replay_preimage_refuses(case):
    before,after,amend,compare=case
    with pytest.raises(RuntimeError):c.delta(after,after,amend,compare)


def test_result_is_exact_and_not_claim_or_route_authority(case):
    before,after,amend,compare=case
    result=dict(c.delta(*case),ok=True,task=c.TASK,only_startup_note_appended=True,
                route_preserved=True,assigned=False,worker_launched=False)
    for key in ('before_pair_sha256','after_pair_sha256','task_note_after_sha256','worker_launched','assigned'):
        changed=copy.deepcopy(result);changed[key]='changed'
        with pytest.raises(RuntimeError):c.accepted(before,after,changed,amend,compare)
