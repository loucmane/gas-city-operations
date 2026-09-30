"""Bind the preserved R7 close without clearing its progress-stall history."""
import copy
import json
from pathlib import Path

TASK='ga-e0t1.20'
SESSION='ci-zcoet'
CLOSE_ROOT=Path('/var/tmp/ga-e0t1.20-r7-close-20260928T174426Z')
PAIR=Path('/var/tmp/ga-e0t1.20-window-20260928-r7/admitted-pair.json')
PINS={
    PAIR:'fbb60f10f96cc569a902eff17916b86b0f2e90c9866cf1eb6f6a091f955d1b1c',
    CLOSE_ROOT/'17-claim-phase.json':'c2d116dbe8056efa02dfcf32e28f2a989298304442135c6bc94c6eea0c054f23',
    CLOSE_ROOT/'18-close-phase.json':'95adac457da92a234a7535a6ae6e90728d37bb229cf98edd5676bf446d061d81',
    CLOSE_ROOT/'19-sessions-phase.json':'c3deb082025a2e097496c709f10d09c3569c19cf04cb40570b300a9fc7361d51',
    CLOSE_ROOT/'result.json':'15a5a5911abe86bc55a7291b3cea366e8eda9a515353b26968cf8030aa6520d0',
}
STARTUP='STARTUP READY: ga-e0t1.20 report_sha256=03c8af6ecc7bf28e1af31319047647578bc52a01042a94fafb820cdb8110f074'
CLOSED_METADATA={
    'gc.continuation_group':'',
    'gc.controller_error':'claimed work has had no observable progress since 2026-09-28T17:37:20Z; inspect session codex-ci-zcoet and decide whether to resume, repair, or stop',
    'gc.failure_owner':'gc.session-reconciler',
    'gc.failure_reason':'progress_stall',
    'gc.failure_subject':SESSION,
    'gc.progress_attention_signature':'575c8b2b58ecf16d8f0695677eb5c869c2139efe8f458eaf950e21f938c5ebdd',
    'gc.progress_last_observed_at':'2026-09-28T17:37:20Z',
    'gc.routed_to':'gascity/codex','gc.session_affinity':'',
    'gc.session_id':SESSION,'gc.session_name':'codex-ci-zcoet',
    'gc.work_branch':'agent/upstream-pending-create-lease',
    'gc.work_dir':'/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20',
}


def require(ok,why):
    if not ok:raise RuntimeError(why)


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
    rows=json.loads(phase(evidence[CLOSE_ROOT/'17-claim-phase.json'],gc+['--rig','gascity','bd','show',TASK,'--json']))
    require(isinstance(rows,list) and len(rows)==1,'prior claim cardinality')
    claimed=rows[0];expected=copy.deepcopy(old['task'])
    expected.update(status='in_progress',assignee='codex-ci-zcoet',started_at='2026-09-28T13:01:54Z',
        updated_at='2026-09-28T17:42:24Z',metadata=CLOSED_METADATA,labels=['needs/operator'],
        notes=old['task']['notes']+'\n'+STARTUP)
    require(normalize(claimed)==normalize(expected),'prior claim had unrelated changes')
    ack=[json.loads(x) for x in phase(evidence[CLOSE_ROOT/'18-close-phase.json'],
        gc+['session','close',SESSION,'--json']).splitlines() if x.strip()]
    require(ack==[dict(schema_version='1',ok=True,command='session close',action='close',
        session_id=SESSION,state='closed')],'prior close acknowledgement')
    census=json.loads(phase(evidence[CLOSE_ROOT/'19-sessions-phase.json'],gc+['session','list','--json']))
    require(census.get('ok') is True and census.get('sessions')==[],'prior session residue')
    require(evidence[CLOSE_ROOT/'result.json']==dict(ok=True,closed_session=SESSION,open_sessions=0,
        city_tmux_sessions=0,worktree_processes=0,tmux_server_killed=False,signals_sent=False,
        executor_sha256='694f56ef124d7f93ee674ea376484a194a47a572413b70a2bb7c11f3eefb31ef'),
        'prior close result differs')
    closed=copy.deepcopy(claimed);closed.pop('assignee')
    closed.update(status='open',updated_at='2026-09-28T17:45:35Z',metadata=copy.deepcopy(CLOSED_METADATA))
    old['task']=closed
    projected=[row for row in old['parent']['dependencies'] if row.get('id')==TASK]
    require(len(projected)==1,'prior parent projection identity')
    for key in ('status','updated_at','started_at','metadata','labels','notes'):
        projected[0][key]=copy.deepcopy(closed[key])
    return old


def verify(w,current,normalize,compare):
    for name in ('proof.json','nudge-intent.json','result.json'):
        require(not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r7',name).exists(),
                'prior source release exists')
    evidence={p:json.loads(w.read(p,pin)) for p,pin in PINS.items()}
    expected=expected_pair(evidence,normalize)
    compare(current,expected,parent_audit=True)
    return expected
