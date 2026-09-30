"""Read-only R6 close-history binding for the forthcoming R7 window.

The native progress-stall annotation is preserved exactly, never cleared or
treated as a new claim. This file cannot route or resume anything.
"""
import copy
import json
from pathlib import Path

TASK='ga-e0t1.20'
SESSION='ci-6gwp8'
CLOSE_ROOT=Path('/var/tmp/ga-e0t1.20-r6-close-20260928T144139Z')
PAIR=Path('/var/tmp/ga-e0t1.20-window-20260928-r6/admitted-pair.json')
PINS={
    PAIR:'0cbc536d07d9d2fbd9babfbe2f8b7f163dd637d2d536b9e355b93ba00d1cd3f6',
    CLOSE_ROOT/'16-claim-phase.json':'330921ffe0180ab9268472bec619ce349d6a742755519c0f4de1c8ae14ee935e',
    CLOSE_ROOT/'17-close-phase.json':'b4080c4bcc00871fd414c58fb051799de9d416ad6a407fdc71edcdc94fb5196a',
    CLOSE_ROOT/'18-sessions-phase.json':'2bbc141a9efb1a8f0efd0cdc92c3134f9236ce3deac70275a7de5485a48d3b91',
    CLOSE_ROOT/'result.json':'220f7b66a298fd8a48adf355db429f6d0eec259ba0cbb5257e9c474e615f42cf',
}
STARTUP='STARTUP READY: ga-e0t1.20 report_sha256=0ef1635eed2de2b4160ca333c3f3dd411b13c0a7aca72a90ebfd2f8e4bb7455c'
CLOSED_METADATA={
    'gc.continuation_group':'',
    'gc.controller_error':'claimed work has had no observable progress since 2026-09-28T14:34:11Z; inspect session codex-ci-6gwp8 and decide whether to resume, repair, or stop',
    'gc.failure_owner':'gc.session-reconciler',
    'gc.failure_reason':'progress_stall',
    'gc.failure_subject':SESSION,
    'gc.progress_attention_signature':'912e8f1d08f4bcfca3312845f866a9b9dcf010f1ebe7fa9972de061c96313771',
    'gc.progress_last_observed_at':'2026-09-28T14:34:11Z',
    'gc.routed_to':'gascity/codex','gc.session_affinity':'',
    'gc.session_id':SESSION,'gc.session_name':'codex-ci-6gwp8',
    'gc.work_branch':'agent/upstream-pending-create-lease',
    'gc.work_dir':'/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20',
}


def require(ok,why):
    if not ok: raise RuntimeError(why)


def phase(value,argv):
    require(value['argv']==argv and value['exit_code']==0 and value['primary_error'] is None
        and value['timed_out'] is False,'prior phase did not succeed')
    c=value['cleanup']
    require(c['direct_child_reaped'] is True and c['owned_process_group_gone'] is True
        and not c['failures'] and c['unexpected_survivors'] is False,'prior phase containment incomplete')
    return value['stdout']


def expected_pair(evidence,normalize):
    old=copy.deepcopy(evidence[PAIR])
    gc=['/home/loucmane/gascity/bin/gc','--city','/home/loucmane/gascity/city']
    rows=json.loads(phase(evidence[CLOSE_ROOT/'16-claim-phase.json'],gc+['--rig','gascity','bd','show',TASK,'--json']))
    require(isinstance(rows,list) and len(rows)==1,'prior claim cardinality')
    claimed=rows[0]; expected=copy.deepcopy(old['task'])
    expected.update(status='in_progress',assignee='codex-ci-6gwp8',started_at='2026-09-28T13:01:54Z',
        updated_at='2026-09-28T14:39:24Z',metadata=CLOSED_METADATA,labels=['needs/operator'],
        notes=old['task']['notes']+'\n'+STARTUP)
    require(normalize(claimed)==normalize(expected),'prior claim had unrelated changes')
    ack=[json.loads(x) for x in phase(evidence[CLOSE_ROOT/'17-close-phase.json'],
        gc+['session','close',SESSION,'--json']).splitlines() if x.strip()]
    require(ack==[dict(schema_version='1',ok=True,command='session close',action='close',
        session_id=SESSION,state='closed')],'prior close acknowledgement')
    census=json.loads(phase(evidence[CLOSE_ROOT/'18-sessions-phase.json'],gc+['session','list','--json']))
    require(census.get('ok') is True and census.get('sessions')==[],'prior session residue')
    require(evidence[CLOSE_ROOT/'result.json']==dict(ok=True,closed_session=SESSION,open_sessions=0,
        city_tmux_sessions=0,worktree_processes=0,tmux_server_killed=False,signals_sent=False,
        executor_sha256='6bcc5636e6d43989d64e18f43ec745980fb5b9d742883b2eae0c47805e3148f2'),
        'prior close result differs')
    closed=copy.deepcopy(claimed); closed.pop('assignee')
    closed.update(status='open',updated_at='2026-09-28T14:42:44Z',metadata=copy.deepcopy(CLOSED_METADATA))
    old['task']=closed
    projected=[row for row in old['parent']['dependencies'] if row.get('id')==TASK]
    require(len(projected)==1,'prior parent projection identity')
    for key in ('status','updated_at','started_at','metadata','labels','notes'):
        projected[0][key]=copy.deepcopy(closed[key])
    return old


def verify(w,current,normalize,compare):
    for name in ('proof.json','nudge-intent.json','result.json'):
        require(not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r6',name).exists(),
                'prior source release exists')
    evidence={p:json.loads(w.read(p,pin)) for p,pin in PINS.items()}
    expected=expected_pair(evidence,normalize)
    compare(current,expected,parent_audit=True)
    return expected
