"""Fresh-task read-only admission before staging; no historical claim reuse.

The frozen contract is the authority for the bound task. BIND and ROUTE have
their own separately reviewed executor receipts. This module never treats
those receipts, or a parent audit note, as permission to route or launch.
"""
import copy
from datetime import datetime
import json

TASK, PARENT = 'ga-goo5', 'ga-e0t1'


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
            rows = expected['task']['dependencies']
            require(len(rows) == 1 and rows[0].get('id') == PARENT, 'parent projection')
            [parent_row] = [row for row in rows if row['id'] == PARENT]
            parent_row[key] = new[key]
    for key in expected:
        require(normalized(actual[key]) == normalized(expected[key]), 'admission ' + key + ' drift')


def continued_task(current, bound, contract):
    """Only parent audit text/time may advance between BIND and preflight."""
    contract.validate_task(current, 'bound')
    contract.validate_task(bound, 'bound')
    require(set(current) == set(bound), 'bound task field set')
    for key in bound:
        if key != 'dependencies':
            require(current[key] == bound[key], 'bound task changed: ' + key)
    old_rows = {row['id']: row for row in bound['dependencies']}
    new_rows = {row['id']: row for row in current['dependencies']}
    require(set(old_rows) == set(new_rows) == {PARENT}, 'dependency identities')
    old, new = old_rows[PARENT], new_rows[PARENT]
    require(set(old) == set(new), 'parent projection field set')
    for key in old:
        if key not in ('notes', 'updated_at'):
            require(new[key] == old[key], 'parent projection changed: ' + key)
    # The native store embeds a full parent readback. Missing audit fields are
    # not a reason to broaden the comparison or infer an unchanged parent.
    require(isinstance(old.get('notes'), str) and isinstance(new.get('notes'), str)
            and new['notes'].startswith(old['notes']), 'parent audit erased')
    a, z = datetime.fromisoformat(old['updated_at']), datetime.fromisoformat(new['updated_at'])
    require(a.tzinfo is not None and z.tzinfo is not None and z >= a, 'parent audit time')


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
    # PREFLIGHT precedes STAGE and ROUTE. No routed/claimed/recovered task is
    # admitted here. Freeze complete readbacks for an exact pre-STAGE recheck.
    current = pair(w, b, owned, 'admission')
    w.contract().validate_task(current['task'], 'bound')
    compare_pair(pair(w, b, owned, 'admission-repeat'), current)
    w.save('admitted-pair.json', current)
    w.save('bound-task.json', current['task'])


def recheck(w, b, owned):
    current = pair(w, b, owned, 'stage-admission')
    compare_pair(current, w.record('admitted-pair.json'))
    w.contract().validate_task(current['task'], 'bound')
    w.save('stage-admitted-pair.json', current)
