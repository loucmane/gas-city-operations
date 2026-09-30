"""One exact parent-child to related correction; no routing or lifecycle.

Both supported dependency writes have durable intents. This is not a database
transaction: a command error, ambiguous result or unexpected readback stops
without replay, rollback guessing, SQL, or a worker release. The consumed root
and known intermediate image remain evidence for a separately reviewed recovery.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import types

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
ROOT = Path('/var/tmp/ga-e0t1.20-link-reconciliation-20260928-r1')
TASK, PARENT = 'ga-e0t1.20', 'ga-e0t1'
BASE_SHA = 'b8bc25946cfa9d23e7989e89abcdac4eabed6ee1737e0b5c0674ffa144a53313'
ROUTE_SHA = '8516e8b96918779419c0921c4adc43a56c32f8fc740885231423bafe1741877c'
TERMINAL = Path('/var/tmp/ga-e0t1.20-terminal-20260927-r1/result.json')
TERMINAL_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
ROUTED = Path('/var/tmp/ga-e0t1.20-route-20260927-r1/task-after.json')
ROUTED_SHA = 'e579bd71f426c920b9b6b52719443139ba181ab507b792bb56c2c51ac2af4c49'
BLOCKERS = {'ga-e0t1.13', 'ga-fjoi', 'ga-fc6p', 'ga-fsfg', 'ga-e0t1.8'}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def read(path, pin):
    require(path.resolve(strict=True) == path, 'source alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 1000
                and before.st_nlink == 1 and not before.st_mode & 0o022
                and before.st_size <= 16 << 20, 'source authority')
        raw = b''
        while part := os.read(fd, 65536):
            raw += part
            require(len(raw) <= 16 << 20, 'source bound')
        require(before == os.fstat(fd) == path.lstat() and len(raw) == before.st_size,
                'source changed')
    finally:
        os.close(fd)
    require(hashlib.sha256(raw).hexdigest() == pin, 'source digest')
    return raw


def load(path, pin):
    module = types.ModuleType(path.stem)
    module.__file__ = str(path)
    exec(compile(read(path, pin), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def expected_images(task, parent, phase):
    """Only computed graph projections change, never issue-owned fields."""
    require(phase in ('removed', 'related'), 'unknown graph phase')
    require(task.get('id') == TASK and parent.get('id') == PARENT, 'graph identities')
    require(task.get('parent') == PARENT and task.get('dependency_count') == 1
            and task.get('dependent_count') == 0, 'original graph cardinality')
    deps = task.get('dependencies')
    require(isinstance(deps, list) and len(deps) == 1
            and deps[0].get('id') == PARENT
            and deps[0].get('dependency_type') == 'parent-child', 'original graph edge')
    require(type(parent.get('dependent_count')) is int and parent['dependent_count'] > 0,
            'parent dependent cardinality')
    child, primary = copy.deepcopy(task), copy.deepcopy(parent)
    child.pop('parent')
    if phase == 'removed':
        child.pop('dependencies')
        child['dependency_count'] = 0
        primary['dependent_count'] -= 1
    else:
        child['dependencies'][0]['dependency_type'] = 'related'
    return child, primary


def require_images(task, parent, observed_task, observed_parent, phase):
    child, primary = expected_images(task, parent, phase)
    require(observed_task == child, 'unexpected child delta at ' + phase)
    require(observed_parent == primary, 'unexpected parent delta at ' + phase)


def quiet_value(sessions, status):
    require(sessions.get('ok') is True and sessions.get('sessions') == [], 'native session present')
    require(status.get('suspended') is True and status.get('summary', {}).get('running_agents') == 0,
            'city not suspended and empty')
    rigs = status.get('rigs')
    require(isinstance(rigs, list) and len(rigs) == 4
            and {r.get('name') for r in rigs} == {'gascity', 'gas-city-template', 'hpfetcher', 'blog'}
            and all(r.get('suspended') is True for r in rigs), 'rig suspension drift')


def transact(api, task, parent):
    """Never retry a write, including a failure before its readback."""
    for phase, args in (
        ('removed', ['dep', 'remove', TASK, PARENT, '--json']),
        ('related', ['dep', 'add', TASK, PARENT, '--type', 'related', '--json']),
    ):
        api.guard(phase)
        expected = (task, parent) if phase == 'removed' else expected_images(task, parent, 'removed')
        require(api.pair(phase + '-immediate') == expected, 'pre-write ledger drift')
        api.save(phase + '-intent.json', dict(task=TASK, parent=PARENT, argv=args,
                 task_before=expected[0], parent_before=expected[1], retry=False))
        api.run(phase + '-write', ['--rig', 'gascity', 'bd', *args])
        child_after, parent_after = api.pair(phase + '-after')
        require_images(task, parent, child_after, parent_after, phase)
        api.guard(phase + '-after')
    return child_after, parent_after


def main():
    require(os.getuid() == os.geteuid() == 1000 and globals().get('_SOURCE_SHA'), 'bound user entry')
    read(Path(__file__), _SOURCE_SHA)
    w = load(HERE / 'window-base-r11.py', BASE_SHA)
    route = load(HERE / 'route-task-r5.py', ROUTE_SHA)
    terminal = json.loads(read(TERMINAL, TERMINAL_SHA))
    require(terminal.get('ok') is True and terminal.get('window_preservation') is True
            and terminal.get('accepted_restoration_bound') is True
            and terminal.get('terminal_suspension_endpoint_bound') is True
            and terminal.get('actual_host_verified') is True
            and terminal.get('root_cache_protected_read_only') is True
            and terminal.get('worker_launched') is False, 'prior recovery incomplete')
    routed = json.loads(read(ROUTED, ROUTED_SHA))
    require(not os.path.lexists(ROOT), 'reconciliation root consumed')
    ROOT.mkdir(mode=0o700)
    w.ROOT = ROOT
    b, observer, owned = w.load_support()
    baseline_host = w.host(observer)
    baseline_suspension = w.read(Path(w.SUSPENSION))

    class API:
        def save(self, name, value):
            w.save(name, value)

        def run(self, name, args):
            result = w.phase(name, w.GC + args, b, owned, timeout=45)
            return json.loads(result['stdout'])

        def pair(self, name):
            values = []
            for bead in (TASK, PARENT):
                rows = self.run(name + '-' + bead, ['--rig', 'gascity', 'bd', 'show', bead, '--json'])
                require(isinstance(rows, list) and len(rows) == 1 and rows[0].get('id') == bead,
                        'wrong store or bead')
                values.append(rows[0])
            self.save(name + '.json', dict(task=values[0], parent=values[1]))
            return tuple(values)

        def guard(self, name):
            require(w.host(observer) == baseline_host, 'host epoch or native census changed')
            w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
            w.read(w.RECEIPT, w.RECEIPT_SHA[0])
            require(w.read(Path(w.SUSPENSION)) == baseline_suspension, 'suspension changed')
            sessions = self.run(name + '-sessions', ['session', 'list', '--json'])
            status = self.run(name + '-status', ['status', '--json'])
            quiet_value(sessions, status)

    api = API()
    w.save('intent.json', dict(executor_sha256=_SOURCE_SHA, terminal_sha256=TERMINAL_SHA,
           routed_sha256=ROUTED_SHA, task=TASK, parent=PARENT,
           edge_before='parent-child', edge_after='related', worker_release=False,
           limitation='Two supported API writes; any partial failure stops without replay'))
    api.guard('initial')
    task, parent = api.pair('before')
    route.continued_task(task, routed)
    w.contract().validate_task(task, 'routed')
    require(parent.get('status') == 'in_progress', 'parent status changed')
    unresolved = {d['id'] for d in parent.get('dependencies', [])
                  if d.get('dependency_type') == 'blocks' and d.get('status') not in ('closed', 'pinned')}
    require(unresolved == BLOCKERS, 'parent prerequisites changed')
    blocked = api.run('blocked-before', ['--rig', 'gascity', 'bd', 'blocked', '--json'])
    require([v.get('blocked_by') for v in blocked if v.get('id') == TASK] == [[PARENT]],
            'task not blocked solely by parent inheritance')
    ready_args = ['--rig', 'gascity', 'bd', 'ready', '--metadata-field',
                  'gc.routed_to=gascity/codex', '--unassigned', '--exclude-type=epic', '--json', '--limit', '0']
    require(api.run('ready-before', ready_args) == [], 'unexpected ready work before reconciliation')
    after, primary = transact(api, task, parent)
    ready = api.run('ready-after', ready_args)
    require(isinstance(ready, list) and [v.get('id') for v in ready] == [TASK],
            'corrected task is not sole ready target')
    blocked_after = api.run('blocked-after', ['--rig', 'gascity', 'bd', 'blocked', '--json'])
    require(not any(v.get('id') == TASK for v in blocked_after), 'task remains blocked')
    require({v['id']: v['blocked_by'] for v in blocked if v.get('id') != TASK}
            == {v['id']: v['blocked_by'] for v in blocked_after}, 'unrelated blocking changed')
    require(api.pair('final') == (after, primary), 'final ledger drift')
    api.guard('final')
    w.complete_containment()
    w.save('result.json', dict(ok=True, task=TASK, edge='related',
           task_sha256=w.digest(json.dumps(after, sort_keys=True, separators=(',', ':')).encode()),
           parent_prerequisites_preserved=True, sole_target_ready=True,
           existing_route_preserved=True, worker_launched=False, lifecycle_changed=False,
           successor_window_still_requires_review=True))
    print(json.dumps(w.record('result.json')))


if __name__ == '__main__':
    main()
