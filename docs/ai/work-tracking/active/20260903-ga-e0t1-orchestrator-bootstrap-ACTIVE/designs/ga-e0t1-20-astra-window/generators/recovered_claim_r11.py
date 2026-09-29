"""Bind restored R10, including its enqueue-only attempt; never erase history."""
import copy
import json
from pathlib import Path

TASK='ga-e0t1.20'
SESSION='ci-9dp7z'
CLOSE_ROOT=Path('/var/tmp/ga-e0t1.20-r10-close-20260929T005551Z')
PAIR=Path('/var/tmp/ga-e0t1.20-window-20260929-r10/admitted-pair.json')
RELEASE=Path('/var/tmp/ga-e0t1.20-startup-release-20260929-r10')
PINS={
    PAIR:'705e9f79ffd7d954c7787134639d632a1b7d3a1f3b1afff05ac261329508af49',
    CLOSE_ROOT/'16-claim-phase.json':'e0d6c0ffe3f64ed19eefd97b8e8bbb05e59d29142f23c22fcc4de42d3a506d45',
    CLOSE_ROOT/'17-close-phase.json':'8dcdc4249d0de317a5b1ef0b59b041ad5d207edf87bd26e6ce8077bae0bc555d',
    CLOSE_ROOT/'18-sessions-phase.json':'e4387676540049db6f9aaa9a5683187f31df94a79599121aebd47af9d3e808d7',
    CLOSE_ROOT/'result.json':'9c4c4e2537c1c12276b4730cbfd909c606a366880580806f1bed290be1ff6aa9',
    RELEASE/'proof.json':'f2074a8659d377f3be6a5a1c997b4fdf3ab9b0184b44ccc2d59979fb6216e473',
    RELEASE/'nudge-intent.json':'5e3313c93f996c7608bbb456eea6b4b068485438e00f13926b89304b37ce175d',
    RELEASE/'result.json':'e07d5763534d37507a0b5972cd10712a7ffcb92dfd4ca220b9a0eab77d2d781a',
}
STARTUP='STARTUP READY: ga-e0t1.20 report_sha256=e8e6fa2832cbf10fee1d24ffae3a753047d87838d38d00c7745f36efece4849d'
CLOSED_METADATA={
    'gc.continuation_group':'',
    'gc.controller_error':'claimed work has had no observable progress since 2026-09-29T00:38:13Z; inspect session codex-ci-9dp7z and decide whether to resume, repair, or stop',
    'gc.failure_owner':'gc.session-reconciler','gc.failure_reason':'progress_stall','gc.failure_subject':SESSION,
    'gc.progress_attention_signature':'9a102bd39abab636559f81a776c687df9dafbd1fdee5889c6438249986250839',
    'gc.progress_last_observed_at':'2026-09-29T00:38:13Z','gc.routed_to':'gascity/codex','gc.session_affinity':'',
    'gc.session_id':SESSION,'gc.session_name':'codex-ci-9dp7z','gc.work_branch':'agent/upstream-pending-create-lease',
    'gc.work_dir':'/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20',
}

def require(ok,why):
    if not ok:raise RuntimeError(why)

def phase(value,argv):
    require(value['argv']==argv and value['exit_code']==0 and value['primary_error'] is None
            and value['timed_out'] is False,'prior phase did not succeed')
    c=value['cleanup']
    require(c['direct_child_reaped'] is True and c['owned_process_group_gone'] is True
            and not c['failures'] and c['unexpected_survivors'] is False,'prior containment incomplete')
    return value['stdout']

def expected_pair(evidence,normalize):
    old=copy.deepcopy(evidence[PAIR])
    gc=['/home/loucmane/gascity/bin/gc','--city','/home/loucmane/gascity/city']
    rows=json.loads(phase(evidence[CLOSE_ROOT/'16-claim-phase.json'],gc+['--rig','gascity','bd','show',TASK,'--json']))
    require(type(rows) is list and len(rows)==1,'prior claim cardinality')
    claimed=rows[0];expected=copy.deepcopy(old['task'])
    expected.update(status='in_progress',assignee='codex-ci-9dp7z',started_at='2026-09-28T13:01:54Z',
        updated_at='2026-09-29T00:43:24Z',metadata=CLOSED_METADATA,labels=['needs/operator'],
        notes=old['task']['notes']+'\n'+STARTUP)
    require(normalize(claimed)==normalize(expected),'prior claim had unrelated changes')
    ack=[json.loads(x) for x in phase(evidence[CLOSE_ROOT/'17-close-phase.json'],gc+['session','close',SESSION,'--json']).splitlines() if x.strip()]
    require(ack==[dict(schema_version='1',ok=True,command='session close',action='close',session_id=SESSION,state='closed')],'prior close acknowledgement')
    census=json.loads(phase(evidence[CLOSE_ROOT/'18-sessions-phase.json'],gc+['session','list','--json']))
    require(census.get('ok') is True and census.get('sessions')==[],'prior session residue')
    require(evidence[CLOSE_ROOT/'result.json']==dict(ok=True,closed_session=SESSION,open_sessions=0,
        city_tmux_sessions=0,worktree_processes=0,tmux_server_killed=False,signals_sent=False,
        executor_sha256='9362df9405236b9a11277b4ddcab363632c988933d1e5fe83ae2d429038e46a9'),'prior close result differs')
    require(evidence[RELEASE/'result.json']['source_release_sent'] is True
            and evidence[RELEASE/'nudge-intent.json']['session_id']==SESSION,'prior enqueue evidence differs')
    closed=copy.deepcopy(claimed);closed.pop('assignee')
    closed.update(status='open',updated_at='2026-09-29T00:56:56Z',metadata=copy.deepcopy(CLOSED_METADATA))
    old['task']=closed
    projected=[row for row in old['parent']['dependencies'] if row.get('id')==TASK]
    require(len(projected)==1,'prior parent projection identity')
    for key in ('status','updated_at','started_at','metadata','labels','notes'):projected[0][key]=copy.deepcopy(closed[key])
    return old

def verify(w,current,normalize,compare):
    evidence={p:json.loads(w.read(p,pin)) for p,pin in PINS.items()}
    expected=expected_pair(evidence,normalize)
    compare(current,expected,parent_audit=True)
    return expected
