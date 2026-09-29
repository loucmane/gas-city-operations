"""Read-only successor admission of the completed task-link and route.

Only an append-forward parent audit may differ before admission. After the
preflight snapshot, both complete Bead images must stay exact until staging.
No Bead write, route, lifecycle operation or subprocess implementation here.
"""
import copy
from datetime import datetime
import json
from pathlib import Path

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
TASK, PARENT = 'ga-e0t1.20', 'ga-e0t1'
COMPLETED = Path('/var/tmp/ga-e0t1.20-link-completion-20260928-r2')
PINS = {
    COMPLETED/'result.json': '9882f6fb7170bd548a1158cc27ce418730759cba454b1a47f0c6c9d9ce7dc906',
    COMPLETED/'final.json': 'c990516ad6e1e5d7b341e575a457fc3addbed88205953a4e624f9ee7b81f99a6',
    Path('/var/tmp/ga-e0t1.20-route-20260927-r1/result.json'): 'fffdda735c940dd428493eb07c9750cb15d2a935c7184e5d4854493171be1f73',
    Path('/var/tmp/ga-e0t1.20-route-20260927-r1/task-after.json'): 'e579bd71f426c920b9b6b52719443139ba181ab507b792bb56c2c51ac2af4c49',
    Path('/var/tmp/ga-e0t1.20-bind-20260927-r1/result.json'): '0e8003f3fa54558537cd93dcd2863ab5bcd0aef8be8af1ec11c198472ad022d2',
}


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def normalized(value):
    value = copy.deepcopy(value)
    rows = value.get('dependencies', [])
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), 'dependency rows')
    ids = [r.get('id') for r in rows]
    require(all(isinstance(i, str) for i in ids) and len(ids) == len(set(ids)), 'dependency identity')
    if 'dependencies' in value:
        value['dependencies'] = sorted(rows, key=lambda r: r['id'])
    return value


def compare_pair(actual, baseline, *, parent_audit=False):
    require(set(actual) == set(baseline) == {'task', 'parent'}, 'pair shape')
    expected = copy.deepcopy(baseline)
    require(actual['task'].get('id') == TASK and actual['parent'].get('id') == PARENT, 'pair identity')
    if parent_audit:
        old, new = baseline['parent'], actual['parent']
        require(isinstance(new.get('notes'), str) and isinstance(old.get('notes'), str)
                and new['notes'].startswith(old['notes']), 'parent audit erasure')
        a, z = datetime.fromisoformat(old['updated_at']), datetime.fromisoformat(new['updated_at'])
        require(a.tzinfo is not None and z.tzinfo is not None and z >= a, 'parent audit time')
        for key in ('notes', 'updated_at'):
            expected['parent'][key] = new[key]
            require(len(expected['task']['dependencies']) == 1
                    and expected['task']['dependencies'][0]['id'] == PARENT, 'parent projection')
            expected['task']['dependencies'][0][key] = new[key]
    for key in expected:
        require(normalized(actual[key]) == normalized(expected[key]), 'continuation ' + key + ' drift')


def pair(w, b, owned, prefix):
    result = {}
    for key, bead in (('task', TASK), ('parent', PARENT)):
        raw = w.phase(prefix+'-'+key, w.GC+['--rig', 'gascity', 'bd', 'show', bead, '--json'],
                      b, owned, timeout=45)['stdout']
        rows = json.loads(raw)
        require(isinstance(rows, list) and len(rows) == 1 and rows[0].get('id') == bead, 'store identity')
        result[key] = rows[0]
    return result


def admit(w, b, owned):
    evidence = {path: json.loads(w.read(path, pin)) for path, pin in PINS.items()}
    result = evidence[COMPLETED/'result.json']
    require(result['ok'] is True and result['sole_target_ready'] is True
            and result['parent_prerequisites_preserved'] is True
            and result['existing_route_preserved'] is True and result['worker_launched'] is False,
            'link completion did not pass')
    current = pair(w, b, owned, 'admission')
    amendment_root=Path('/var/tmp/ga-e0t1.20-startup-amendment-20260929-r10')
    amendment=json.loads(w.read(HERE/'startup-amendment-r10.json','1cc86b25633ed830e2f85d4b235ef50b8544834dd8a33127e486551a14ddbec8'))
    exact=w.module(HERE/'startup-amendment-contract-r5.py','85963b400979ba14561bc70e6a6d03b189fb641db5650788bd2a0a5906f77ca9')
    before_amend=json.loads(w.read(amendment_root/'before.json'))
    after_amend=json.loads(w.read(amendment_root/'after.json'))
    applied=json.loads(w.read(amendment_root/'result.json'))
    prior=w.module(HERE/'recovered-claim-r10.py','54d39350c8616dc369eaea91d86af855f30fbfe8824e0d27d0702b26ad5c24a5')
    prior.verify(w,before_amend,normalized,compare_pair)
    exact.accepted(before_amend,after_amend,applied,amendment,compare_pair)
    compare_pair(current,after_amend,parent_audit=True)
    w.contract().validate_task(current['task'], 'routed')
    compare_pair(pair(w, b, owned, 'admission-repeat'), current)
    w.save('admitted-pair.json', current)
    w.save('admitted-task.json', current['task'])
    w.save('completed-inputs.json', {str(path): pin for path, pin in PINS.items()})


def recheck(w, b, owned):
    current = pair(w, b, owned, 'stage-admission')
    compare_pair(current, w.record('admitted-pair.json'))
    w.contract().validate_task(current['task'], 'routed')
    w.save('stage-admitted-pair.json', current)
