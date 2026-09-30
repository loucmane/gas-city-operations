"""Complete only the conclusively verified R1 intermediate using native dep relate.

No removal, route, lifecycle, retry or fallback. The supported relate command
itself performs two writes; any partial or unexpected result remains HOLD.
"""
import copy
import json
import os
from pathlib import Path
import stat

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
ROOT = Path('/var/tmp/ga-e0t1.20-link-completion-20260928-r2')
PREVIOUS = Path('/var/tmp/ga-e0t1.20-link-reconciliation-20260928-r1')
TASK, PARENT = 'ga-e0t1.20', 'ga-e0t1'
PINS = {
    'before.json': '404cde16554560c6c1dc1c9ba0b85f910e2774fb6f33481e840d2d2f4fb5581b',
    'removed-after.json': '96fe63db6309f8516107844eb35a7e087453632713f6dbdf3d578f841f3c6595',
    'related-write-phase.json': 'fec65cd6ad5e2fb1eebe7ae46bacd104df3dcd50e28a868251d6a38121c0f844',
}
GRAPH_FIELDS = {'dependencies', 'dependents', 'dependency_count', 'dependent_count', 'comment_count', 'parent'}
ARGV = ['--rig', 'gascity', 'bd', 'dep', 'relate', TASK, PARENT, '--json']


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def issue(value):
    return {k: copy.deepcopy(v) for k, v in value.items() if k not in GRAPH_FIELDS}


def normalized(value):
    """Only dependency presentation order is not authority; duplicates still fail."""
    result = copy.deepcopy(value)
    if 'dependencies' in result:
        deps = result['dependencies']
        require(isinstance(deps, list) and all(isinstance(d, dict) for d in deps), 'dependency shape')
        ids = [d.get('id') for d in deps]
        require(all(isinstance(i, str) for i in ids) and len(ids) == len(set(ids)), 'dependency identity')
        result['dependencies'] = sorted(deps, key=lambda d: d['id'])
    return result


def expected_after(before):
    child, parent = copy.deepcopy(before['task']), copy.deepcopy(before['parent'])
    require(child['id'] == TASK and parent['id'] == PARENT, 'pair identity')
    require(not child.get('dependencies') and 'parent' not in child
            and child.get('dependency_count') == child.get('dependent_count') == 0, 'not R1 intermediate')
    require(all(d['id'] != TASK for d in parent.get('dependencies', [])), 'relation already exists')
    child['dependencies'] = [dict(issue(parent), dependency_type='relates-to')]
    child['dependency_count'] = child['dependent_count'] = 1
    parent['dependencies'] = parent.get('dependencies', []) + [dict(issue(before['task']), dependency_type='relates-to')]
    parent['dependency_count'] += 1
    parent['dependent_count'] += 1
    return dict(task=normalized(child), parent=normalized(parent))


def verify_pair(actual, expected):
    require(set(actual) == set(expected) == {'task', 'parent'}, 'pair keys')
    for name in expected:
        require(normalized(actual[name]) == normalized(expected[name]), 'unexpected ' + name + ' image')


def transition(api, before):
    api.guard('before')
    verify_pair(api.pair('immediate'), before)
    api.save('relate-intent.json', dict(argv=ARGV, before=before, retry=False,
             limitation='Native relate performs two writes and is not an atomic pair transaction'))
    result = api.run('relate-write', ARGV)
    require(result == dict(id1=TASK, id2=PARENT, related=True), 'native relate acknowledgement')
    after = api.pair('after')
    verify_pair(after, expected_after(before))
    api.guard('after')
    return after


def main():
    # Reuse only reviewed source loaders and guards; never invoke the R1 executor.
    import hashlib
    import types
    path = HERE / 'reconcile-task-link.py'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and path.resolve(strict=True) == path and s.st_uid == s.st_gid == 1000
                and s.st_nlink == 1 and s.st_size <= 1 << 20 and not s.st_mode & 0o022,
                'R1 source authority')
        raw = os.read(fd, (1 << 20) + 1)
        require(os.fstat(fd) == s == path.lstat() and len(raw) == s.st_size, 'R1 source changed')
    finally:
        os.close(fd)
    require(hashlib.sha256(raw).hexdigest() == '730e46cab83f4314cdd0972fbf4b0dab2c4b8c90f4e5c2bccf35267a4ad14254',
            'R1 source digest')
    old = types.ModuleType('r1_readers'); old.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), old.__dict__)
    require(os.getuid() == os.geteuid() == 1000 and globals().get('_SOURCE_SHA'), 'bound user entry')
    old.read(Path(__file__), _SOURCE_SHA)
    values = {name: json.loads(old.read(PREVIOUS / name, pin)) for name, pin in PINS.items()}
    original, before, failure = values['before.json'], values['removed-after.json'], values['related-write-phase.json']
    removed = old.expected_images(original['task'], original['parent'], 'removed')
    verify_pair(before, dict(task=removed[0], parent=removed[1]))
    require(failure['argv'] == ['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city',
            '--rig', 'gascity', 'bd', 'dep', 'add', TASK, PARENT, '--type', 'related', '--json']
            and failure['exit_code'] == 1 and not failure['timed_out'] and not failure['primary_error'],
            'not the exact refused second write')
    c = failure['cleanup']
    require(c['direct_child_reaped'] and c['owned_process_group_gone']
            and not c['unexpected_survivors'] and not c['failures'], 'prior containment')
    require(not os.path.lexists(ROOT), 'completion consumed')
    w = old.load(HERE / 'window-base-r11.py', old.BASE_SHA)
    ROOT.mkdir(mode=0o700); w.ROOT = ROOT
    b, observer, owned = w.load_support()
    host = w.host(observer)
    suspension = w.read(Path(w.SUSPENSION))

    class API:
        def save(self, name, value):
            w.save(name, value)

        def run(self, name, args):
            return json.loads(w.phase(name, w.GC + args, b, owned, timeout=45)['stdout'])

        def pair(self, name):
            pair = {}
            for key, bead in (('task', TASK), ('parent', PARENT)):
                rows = self.run(name + '-' + bead, ['--rig', 'gascity', 'bd', 'show', bead, '--json'])
                require(isinstance(rows, list) and len(rows) == 1 and rows[0].get('id') == bead, 'store identity')
                pair[key] = rows[0]
            self.save(name + '.json', pair)
            return pair

        def guard(self, name):
            require(w.host(observer) == host, 'host epoch or native census changed')
            w.read(w.CITY / 'city.toml', w.CITY_SHA[0])
            w.read(w.RECEIPT, w.RECEIPT_SHA[0])
            require(w.read(Path(w.SUSPENSION)) == suspension, 'suspension changed')
            old.quiet_value(self.run(name + '-sessions', ['session', 'list', '--json']),
                            self.run(name + '-status', ['status', '--json']))

    api = API()
    api.save('intent.json', dict(executor_sha256=_SOURCE_SHA, previous=str(PREVIOUS),
             previous_pins=PINS, worker_release=False, remove_replayed=False))
    verify_pair(api.pair('initial'), before)
    ready_args = ['--rig', 'gascity', 'bd', 'ready', '--metadata-field',
                  'gc.routed_to=gascity/codex', '--unassigned', '--exclude-type=epic', '--json', '--limit', '0']
    require([v['id'] for v in api.run('ready-before', ready_args)] == [TASK], 'sole readiness before')
    blocked = api.run('blocked-before', ['--rig', 'gascity', 'bd', 'blocked', '--json'])
    after = transition(api, before)
    require([v['id'] for v in api.run('ready-after', ready_args)] == [TASK], 'sole readiness after')
    blocked_after = api.run('blocked-after', ['--rig', 'gascity', 'bd', 'blocked', '--json'])
    require(not any(v['id'] == TASK for v in blocked_after), 'child blocked')
    require({v['id']: v['blocked_by'] for v in blocked} ==
            {v['id']: v['blocked_by'] for v in blocked_after}, 'blocking changed')
    verify_pair(api.pair('final'), after)
    api.guard('final')
    w.complete_containment()
    api.save('result.json', dict(ok=True, task=TASK, parent=PARENT, relationship='bidirectional relates-to',
             parent_prerequisites_preserved=True, sole_target_ready=True, existing_route_preserved=True,
             worker_launched=False, lifecycle_changed=False, remove_replayed=False,
             successor_window_still_requires_review=True))
    print(json.dumps(w.record('result.json')))


if __name__ == '__main__':
    main()
