"""Bind the preserved R9 close without removing any monitoring history."""
import copy
import json
from pathlib import Path

TASK = 'ga-e0t1.20'
SESSION = 'ci-g12rt'
CLOSE_ROOT = Path('/var/tmp/ga-e0t1.20-r9-close-20260928T233159Z')
PAIR = Path('/var/tmp/ga-e0t1.20-window-20260929-r9/admitted-pair.json')
PINS = {
    PAIR: '37790882ebf7dca434c03864a2869a553f04d58b9b34ca5760f2787636dd456c',
    CLOSE_ROOT/'16-claim-phase.json': '43edfda50451bd94109e4b020d62cad1a4dbe61a9ad5808ad07fed0365099961',
    CLOSE_ROOT/'17-close-phase.json': '0807d6f3708c1d2a9d1e403acb59074fe292d936df3ad96bee52397d716dd1d5',
    CLOSE_ROOT/'18-sessions-phase.json': 'c2e5f07f6e44b58160828ebf68a46a68db7f0c3238367594108dfd3b3d730d19',
    CLOSE_ROOT/'result.json': '9ea049d563c686da1a37ff7ce7aa754415bcb493a3e3340addf4b86fde2ccdc2',
}
STARTUP = 'STOPPED: ga-e0t1.20 session=ci-g12rt probe_sha256=9d66d510aec6a81bcfe1e57c2bb248e0a274ea17c2f85cf3f33c3ca9b09cd29d startup probe passed; step 5 exact transport conflicts with higher-priority session permission instructions prohibiting the sandbox_permissions field for any reason. Negative signing probe not attempted; no source edits; waiting for containment.'
CLOSED_METADATA = {
    'gc.continuation_group': '',
    'gc.controller_error': 'claimed work has had no observable progress since 2026-09-28T21:09:34Z; inspect session codex-ci-sgd80 and decide whether to resume, repair, or stop',
    'gc.failure_owner': 'gc.session-reconciler', 'gc.failure_reason': 'progress_stall',
    'gc.failure_subject': 'ci-sgd80',
    'gc.progress_attention_signature': 'bc2c7f90f4b2563aaa35fe4468545c40114057cac6f309dc25d824a961a00ec1',
    'gc.progress_last_observed_at': '2026-09-28T21:09:34Z',
    'gc.routed_to': 'gascity/codex', 'gc.session_affinity': '',
    'gc.session_id': SESSION, 'gc.session_name': 'codex-ci-g12rt',
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
    expected.update(status='in_progress', assignee='codex-ci-g12rt',
        started_at='2026-09-28T13:01:54Z', updated_at='2026-09-28T23:29:40Z',
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
        executor_sha256='83c3cf184a477e255328071b61698da6a31931d3abdee68ca2acbd2a8dc22b72'),
        'prior close result differs')
    closed = copy.deepcopy(claimed)
    closed.pop('assignee')
    closed.update(status='open', updated_at='2026-09-28T23:33:04Z', metadata=copy.deepcopy(CLOSED_METADATA))
    old['task'] = closed
    projected = [row for row in old['parent']['dependencies'] if row.get('id') == TASK]
    require(len(projected) == 1, 'prior parent projection identity')
    for key in ('status', 'updated_at', 'started_at', 'metadata', 'labels', 'notes'):
        projected[0][key] = copy.deepcopy(closed[key])
    return old


def verify(w, current, normalize, compare):
    for name in ('proof.json', 'nudge-intent.json', 'result.json'):
        require(not Path('/var/tmp/ga-e0t1.20-startup-release-20260929-r9', name).exists(),
                'prior source release exists')
    evidence = {p: json.loads(w.read(p, pin)) for p, pin in PINS.items()}
    expected = expected_pair(evidence, normalize)
    compare(current, expected, parent_audit=True)
    return expected
