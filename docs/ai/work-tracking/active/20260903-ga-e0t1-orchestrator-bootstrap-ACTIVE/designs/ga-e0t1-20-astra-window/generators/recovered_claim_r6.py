"""Read-only binding of the completed R5 claim and supported close.

No metadata is cleared. Historical session fields are admitted only as the
exact closed predecessor, never as an active or transferable worker claim.
"""
import copy
import json
from pathlib import Path

TASK = 'ga-e0t1.20'
SESSION = 'ci-rks41'
CLOSE_ROOT = Path('/var/tmp/ga-e0t1.20-r5-close-20260928T130452Z')
PAIR = Path('/var/tmp/ga-e0t1.20-window-20260928-r5/admitted-pair.json')
PINS = {
    PAIR: '80c0253d52b7f3192ec9b5071f5af937a50d821a33c7b6acb1d010fe3326b9f6',
    CLOSE_ROOT/'16-claim-phase.json': '95022d47c1151014cf57e86531ad42c3ccbbd1620049827aabb518802bbfa560',
    CLOSE_ROOT/'17-close-phase.json': '2eb89fbb5e9f0065fa2e55f17fb50fa09102ad4acb5cf1b832088b0d207825dc',
    CLOSE_ROOT/'18-sessions-phase.json': 'aaedd0c271fc08bd5ed84cba68c3c2ffcf32b8a655e35fd8187e6f15aa40b76c',
    CLOSE_ROOT/'result.json': '53b7501005e7f48722f022e023995ba6c9c8b83f3e7adcfa4c6d9e6089da46ea',
}
STOPPED = ('STOPPED: ga-e0t1.20 session=ci-rks41 '
    'probe_sha256=1766846356f763e1b98ed6276b916e53daf7493786e4f73fb7f6648146ab1f67 '
    'startup probe exited 1: RuntimeError: subscription identity unproven. '
    'No source edits; waiting for containment.')
METADATA = {
    'gc.routed_to': 'gascity/codex',
    'gc.work_dir': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20',
    'gc.session_id': SESSION, 'gc.session_name': 'codex-ci-rks41',
    'gc.work_branch': 'agent/upstream-pending-create-lease',
}
CLOSED_METADATA = dict(METADATA, **{'gc.session_affinity':'', 'gc.continuation_group':''})


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def phase(value, argv):
    require(value['argv'] == argv and value['exit_code'] == 0
        and value['primary_error'] is None and value['timed_out'] is False,
        'prior phase did not succeed')
    c = value['cleanup']
    require(c['direct_child_reaped'] is True and c['owned_process_group_gone'] is True
        and not c['failures'] and c['unexpected_survivors'] is False,
        'prior phase containment incomplete')
    return value['stdout']


def expected_pair(evidence, normalize):
    old = copy.deepcopy(evidence[PAIR])
    gc = ['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city']
    rows = json.loads(phase(evidence[CLOSE_ROOT/'16-claim-phase.json'],
        gc+['--rig','gascity','bd','show',TASK,'--json']))
    require(isinstance(rows,list) and len(rows)==1, 'prior claim cardinality')
    claimed = rows[0]
    expected = copy.deepcopy(old['task'])
    expected.update(status='in_progress', assignee='codex-ci-rks41',
        started_at='2026-09-28T13:01:54Z', updated_at='2026-09-28T13:02:23Z',
        metadata=METADATA, notes=old['task']['notes']+'\n'+STOPPED)
    require(normalize(claimed)==normalize(expected), 'prior claim had unrelated changes')
    ack = [json.loads(x) for x in phase(evidence[CLOSE_ROOT/'17-close-phase.json'],
        gc+['session','close',SESSION,'--json']).splitlines() if x.strip()]
    require(ack == [dict(schema_version='1',ok=True,command='session close',
        action='close',session_id=SESSION,state='closed')], 'prior close acknowledgement')
    census = json.loads(phase(evidence[CLOSE_ROOT/'18-sessions-phase.json'],
        gc+['session','list','--json']))
    require(census.get('ok') is True and census.get('sessions')==[], 'prior session residue')
    require(evidence[CLOSE_ROOT/'result.json'] == dict(ok=True,closed_session=SESSION,
        open_sessions=0,city_tmux_sessions=0,worktree_processes=0,
        tmux_server_killed=False,signals_sent=False,
        executor_sha256='33f22aafa01ac42f7589c6f856e3bae06baaec93a60233ee3f167ffc3adaff40'),
        'prior close result differs')
    closed = copy.deepcopy(claimed)
    closed.pop('assignee')
    closed.update(status='open',updated_at='2026-09-28T13:05:59Z',
                  metadata=copy.deepcopy(CLOSED_METADATA))
    old['task'] = closed
    projected = [row for row in old['parent']['dependencies'] if row.get('id')==TASK]
    require(len(projected)==1, 'prior parent projection identity')
    # Projection excludes dependency graph but otherwise preserves exact fields.
    for key in ('status','updated_at','started_at','metadata','notes'):
        projected[0][key] = copy.deepcopy(closed[key])
    return old


def verify(w, current, normalize, compare):
    require(not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r5/proof.json').exists(),
            'prior source release exists')
    evidence = {path:json.loads(w.read(path,pin)) for path,pin in PINS.items()}
    expected = expected_pair(evidence, normalize)
    compare(current,expected,parent_audit=True)
    return expected
