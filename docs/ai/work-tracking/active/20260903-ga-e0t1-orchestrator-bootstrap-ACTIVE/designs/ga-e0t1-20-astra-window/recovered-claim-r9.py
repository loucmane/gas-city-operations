"""Bind the preserved R8 close without removing any monitoring history."""
import copy
import json
from pathlib import Path

TASK = 'ga-e0t1.20'
SESSION = 'ci-sgd80'
CLOSE_ROOT = Path('/var/tmp/ga-e0t1.20-r8-close-20260928T212000Z')
PAIR = Path('/var/tmp/ga-e0t1.20-window-20260928-r8/admitted-pair.json')
PINS = {
    PAIR: '65eaa0c7886476fa5d29a6a9987ebf116fd0b39d05a725069d445f4b21d27bfe',
    CLOSE_ROOT/'16-claim-phase.json': '8a673ba91d23d3d1c00c59c04ccc5e80a8a3df272ec353768f0b71674fe561d6',
    CLOSE_ROOT/'17-close-phase.json': 'b9d7905ec7ff177b0da8e93361fe9c6cfa6f13e802cf91cdd5507c79458c714f',
    CLOSE_ROOT/'18-sessions-phase.json': 'c9e8f37a9edbc3d8d27cf290b723881b21bafe01445763b5bd12694f919325d5',
    CLOSE_ROOT/'result.json': '21ef1b7d95ac018b902e14b4ce6486cb16ac8820158682455e1b7a864d79cff6',
}
STARTUP = 'STARTUP READY: ga-e0t1.20 report_sha256=eea89174ed3b2ec78bc01253c674e12049c044ffc10967a961dbb4b66431079b'
CLOSED_METADATA = {
    'gc.continuation_group': '',
    'gc.controller_error': 'claimed work has had no observable progress since 2026-09-28T21:09:34Z; inspect session codex-ci-sgd80 and decide whether to resume, repair, or stop',
    'gc.failure_owner': 'gc.session-reconciler', 'gc.failure_reason': 'progress_stall',
    'gc.failure_subject': SESSION,
    'gc.progress_attention_signature': 'bc2c7f90f4b2563aaa35fe4468545c40114057cac6f309dc25d824a961a00ec1',
    'gc.progress_last_observed_at': '2026-09-28T21:09:34Z',
    'gc.routed_to': 'gascity/codex', 'gc.session_affinity': '',
    'gc.session_id': SESSION, 'gc.session_name': 'codex-ci-sgd80',
    'gc.work_branch': 'agent/upstream-pending-create-lease',
    'gc.work_dir': '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20',
}


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def phase(value, argv):
    require(value['argv'] == argv and value['exit_code'] == 0 and value['primary_error'] is None
            and value['timed_out'] is False, 'prior phase did not succeed')
    c = value['cleanup']
    require(c['direct_child_reaped'] is True and c['owned_process_group_gone'] is True
            and not c['failures'] and c['unexpected_survivors'] is False,
            'prior phase containment incomplete')
    return value['stdout']


def expected_pair(evidence, normalize):
    old = copy.deepcopy(evidence[PAIR])
    gc = ['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city']
    rows = json.loads(phase(evidence[CLOSE_ROOT/'16-claim-phase.json'],
        gc + ['--rig', 'gascity', 'bd', 'show', TASK, '--json']))
    require(isinstance(rows, list) and len(rows) == 1, 'prior claim cardinality')
    claimed = rows[0]
    expected = copy.deepcopy(old['task'])
    expected.update(status='in_progress', assignee='codex-ci-sgd80',
        started_at='2026-09-28T13:01:54Z', updated_at='2026-09-28T21:14:39Z',
        metadata=CLOSED_METADATA, labels=['needs/operator'], notes=old['task']['notes']+'\n'+STARTUP)
    require(normalize(claimed) == normalize(expected), 'prior claim had unrelated changes')
    ack = [json.loads(x) for x in phase(evidence[CLOSE_ROOT/'17-close-phase.json'],
        gc + ['session', 'close', SESSION, '--json']).splitlines() if x.strip()]
    require(ack == [dict(schema_version='1', ok=True, command='session close', action='close',
        session_id=SESSION, state='closed')], 'prior close acknowledgement')
    census = json.loads(phase(evidence[CLOSE_ROOT/'18-sessions-phase.json'], gc+['session', 'list', '--json']))
    require(census.get('ok') is True and census.get('sessions') == [], 'prior session residue')
    require(evidence[CLOSE_ROOT/'result.json'] == dict(ok=True, closed_session=SESSION, open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False, signals_sent=False,
        executor_sha256='eb991994ba5f35ff3d88dd2cfa5e8fe645eafc3e0907da0ac78ef5492986f7b0'),
        'prior close result differs')
    closed = copy.deepcopy(claimed)
    closed.pop('assignee')
    closed.update(status='open', updated_at='2026-09-28T21:21:04Z', metadata=copy.deepcopy(CLOSED_METADATA))
    old['task'] = closed
    projected = [row for row in old['parent']['dependencies'] if row.get('id') == TASK]
    require(len(projected) == 1, 'prior parent projection identity')
    for key in ('status', 'updated_at', 'started_at', 'metadata', 'labels', 'notes'):
        projected[0][key] = copy.deepcopy(closed[key])
    return old


def verify(w, current, normalize, compare):
    for name in ('proof.json', 'nudge-intent.json', 'result.json'):
        require(not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r8', name).exists(),
                'prior source release exists')
    evidence = {p: json.loads(w.read(p, pin)) for p, pin in PINS.items()}
    expected = expected_pair(evidence, normalize)
    compare(current, expected, parent_audit=True)
    return expected
