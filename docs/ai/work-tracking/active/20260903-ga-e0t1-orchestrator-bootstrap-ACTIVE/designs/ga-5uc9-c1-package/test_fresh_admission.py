"""Offline fresh admission ordering and negative cases; no host or Bead I/O."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import types

import pytest

HERE = Path(__file__).parent


def load(name):
    m = types.ModuleType(name.replace('-', '_'))
    m.__file__ = str(HERE / name)
    exec(compile((HERE / name).read_bytes(), m.__file__, 'exec'), m.__dict__)
    return m


c = load('contract.py')
a = load('fresh-admission.py')
ws = load('fresh-workspace.py')


def baseline():
    task = copy.deepcopy(c.BASELINE)
    task['notes'] = c.BOUND_NOTE
    task['metadata'] = {'gc.work_dir': c.WORK}
    parent = dict(id=c.PARENT, notes='preserved parent evidence',
                  updated_at='2026-09-29T07:00:00Z', status='in_progress')
    task['dependencies'] = [dict(parent, dependency_type='relates-to')]
    return dict(task=task, parent=parent)


class Window:
    GC = ['gc', '--city', '/fixture/city']
    require = staticmethod(c.require)
    contract = staticmethod(lambda: c)

    def __init__(self, value):
        self.value = value
        self.saved = {}
        self.calls = []

    def phase(self, name, args, b, owned, timeout):
        assert timeout == 45
        assert args[:4] == ['gc', '--city', '/fixture/city', '--rig']
        assert args[4:7] == ['gascity', 'bd', 'show']
        assert args[-1] == '--json'
        self.calls.append((name, args))
        key = 'task' if args[7] == c.TASK else 'parent'
        return dict(stdout=json.dumps([self.value[key]]))

    def save(self, name, value):
        assert name not in self.saved
        self.saved[name] = copy.deepcopy(value)

    def record(self, name):
        return copy.deepcopy(self.saved[name])


def test_bound_admission_and_exact_stage_recheck():
    w = Window(baseline())
    a.admit(w, None, None)
    a.recheck(w, None, None)
    assert len(w.calls) == 6
    assert set(w.saved) == {'admitted-pair.json', 'bound-task.json', 'stage-admitted-pair.json'}
    assert w.saved['admitted-pair.json'] == w.saved['stage-admitted-pair.json']
    assert all(args[5:7] == ['bd', 'show'] for _, args in w.calls)


@pytest.mark.parametrize('field,value', [
    ('status', 'in_progress'), ('assignee', 'codex-ci-old'),
    ('metadata', {'gc.work_dir': c.WORK, 'gc.routed_to': c.TARGET}),
    ('notes', c.UNBOUND_NOTE), ('started_at', '2026-09-29T08:00:00Z'),
])
def test_preflight_rejects_old_or_premature_authority(field, value):
    state = baseline()
    state['task'][field] = value
    w = Window(state)
    with pytest.raises(RuntimeError):
        a.admit(w, None, None)
    assert w.saved == {}


@pytest.mark.parametrize('target,field,value', [
    ('task', 'notes', c.BOUND_NOTE + '\\nnew'),
    ('parent', 'notes', 'new parent entry'),
    ('parent', 'status', 'closed'),
    ('task', 'updated_at', '2026-09-29T08:00:00Z'),
])
def test_between_preflight_and_stage_every_delta_refuses(target, field, value):
    w = Window(baseline())
    a.admit(w, None, None)
    w.value[target][field] = value
    with pytest.raises(RuntimeError):
        a.recheck(w, None, None)
    assert 'stage-admitted-pair.json' not in w.saved


def test_two_reads_must_match_before_admission():
    w = Window(baseline())
    original = w.phase
    def changed(name, *args, **kwargs):
        if name == 'admission-repeat-task':
            w.value['task']['notes'] += 'drift'
        return original(name, *args, **kwargs)
    w.phase = changed
    with pytest.raises(RuntimeError):
        a.admit(w, None, None)
    assert not w.saved


def test_only_parent_append_forward_audit_between_bind_and_preflight():
    before = baseline()['task']
    after = copy.deepcopy(before)
    after['dependencies'][0]['notes'] += '\\nnext'
    after['dependencies'][0]['updated_at'] = '2026-09-29T07:01:00Z'
    a.continued_task(after, before, c)
    after['dependencies'][0]['status'] = 'closed'
    with pytest.raises(RuntimeError):
        a.continued_task(after, before, c)


@pytest.mark.parametrize('field,value', [
    ('notes', 'replacement'), ('updated_at', '2026-09-29T06:59:59Z'),
    ('updated_at', '2026-09-29T07:01:00'),
    ('dependency_type', 'blocks'), ('id', 'ga-wrong'),
])
def test_parent_projection_cannot_smuggle_authority(field, value):
    before = baseline()['task']
    after = copy.deepcopy(before)
    after['dependencies'][0][field] = value
    with pytest.raises(RuntimeError):
        a.continued_task(after, before, c)


def image():
    entries = {name: dict(type=stat.S_IFREG, mode=0o644, sha256=pin)
               for name, pin in ws.PINS.items()}
    entries.update({path: dict(type=stat.S_IFREG, mode=0o644, sha256=pin)
                    for path, pin in c.RULES.items()})
    return entries


def test_fresh_workspace_accepts_only_before_startup_state():
    value = image()
    assert ws.verify(Window(baseline()), value, c.RUNTIME_IMAGE) == value


@pytest.mark.parametrize('path', sorted(c.RUNTIME_FILES) + [
    '.gc/worker-evidence', '.gc/worker-evidence/ga-5uc9/r1/startup.json',
])
def test_prior_runtime_or_evidence_refuses(path):
    value = image()
    value[path] = dict(c.RUNTIME_IMAGE.get(path, dict(type=stat.S_IFREG)))
    with pytest.raises(RuntimeError):
        ws.verify(Window(baseline()), value, c.RUNTIME_IMAGE)


@pytest.mark.parametrize('field,value', [
    ('mode', 0o664), ('mode', 0o755), ('sha256', '0' * 64), ('type', stat.S_IFLNK),
])
def test_pinned_source_and_policy_drift_refuse(field, value):
    for path in (next(iter(ws.PINS)), next(iter(c.RULES))):
        entries = image()
        entries[path][field] = value
        with pytest.raises(RuntimeError):
            ws.verify(Window(baseline()), entries, c.RUNTIME_IMAGE)


def test_previous_pair_comparison_checks_are_preserved():
    import ast
    old = HERE.parent / 'ga-e0t1-20-astra-window/continuation-admission.py'
    old_tree = ast.parse(old.read_bytes())
    new_tree = ast.parse((HERE / 'fresh-admission.py').read_bytes())
    def node(tree, name):
        return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    assert ast.dump(node(old_tree, 'normalized')) == ast.dump(node(new_tree, 'normalized'))
    # The only acceptance delta is equivalent exact one-parent selection; every
    # surrounding comparator check remains byte-identical after normalization.
    original = ast.unparse(node(old_tree, 'compare_pair')).replace('continuation ', 'admission ')
    before = """require(len(expected['task']['dependencies']) == 1 and expected['task']['dependencies'][0]['id'] == PARENT, 'parent projection')
            expected['task']['dependencies'][0][key] = new[key]"""
    after = """rows = expected['task']['dependencies']
            require(len(rows) == 1 and rows[0].get('id') == PARENT, 'parent projection')
            [parent_row] = [row for row in rows if row['id'] == PARENT]
            parent_row[key] = new[key]"""
    assert original.count(before) == 1
    assert original.replace(before, after) == ast.unparse(node(new_tree, 'compare_pair'))


@pytest.mark.parametrize('field,value', [('notes','changed seed'),('updated_at','2026-09-29T07:01:00Z'),('id','ga-other'),('dependency_type','blocks')])
def test_added_predecessor_edge_never_admitted(field, value):
    before = baseline()['task']
    after = copy.deepcopy(before)
    after['dependencies'].append(dict(id='ga-9olv',dependency_type='relates-to',notes='held seed'))
    after['dependencies'][1][field] = value
    with pytest.raises(RuntimeError):
        a.continued_task(after, before, c)


def test_single_parent_audit_still_advances():
    before = baseline()['task']
    after = copy.deepcopy(before)
    after['dependencies'].reverse()
    parent = next(row for row in after['dependencies'] if row['id'] == c.PARENT)
    parent['notes'] += ' appended audit'
    parent['updated_at'] = '2026-09-29T07:01:00Z'
    a.continued_task(after, before, c)


def test_pair_parent_audit_only_changes_exact_parent_projection():
    before = baseline()
    after = copy.deepcopy(before)
    after['parent']['notes'] += ' appended audit'
    after['parent']['updated_at'] = '2026-09-29T07:01:00Z'
    after['task']['dependencies'][0].update(
        notes=after['parent']['notes'], updated_at=after['parent']['updated_at'])
    after['task']['dependencies'].reverse()
    a.compare_pair(after, before, parent_audit=True)
    after['task']['dependencies'][0]['notes'] = 'changed held seed'
    with pytest.raises(RuntimeError):
        a.compare_pair(after, before, parent_audit=True)
