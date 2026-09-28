"""Offline graph-transition proofs; never invoke main, Beads, or services."""
import copy
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / 'reconcile-task-link.py'
spec = importlib.util.spec_from_file_location('task_link_reconciliation', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def images():
    parent = dict(id=m.PARENT, status='in_progress', notes='history', metadata={'owner': 'external'},
                  dependent_count=21, dependency_count=1,
                  dependencies=[dict(id='real-prerequisite', status='in_progress', dependency_type='blocks')])
    task = dict(id=m.TASK, parent=m.PARENT, status='open', priority=2,
                metadata={'gc.routed_to': 'gascity/codex', 'gc.work_dir': '/existing/worktree'},
                notes='bound contract', updated_at='2026-09-28T06:48:29Z',
                dependency_count=1, dependent_count=0,
                dependencies=[dict(id=m.PARENT, status='in_progress', notes='history', dependency_type='parent-child')])
    return task, parent


@pytest.mark.parametrize('phase', ['removed', 'related'])
def test_exact_graph_projection_preserves_originals(phase):
    before = images()
    snapshot = copy.deepcopy(before)
    task, parent = m.expected_images(*before, phase)
    assert before == snapshot
    assert 'parent' not in task
    assert task['metadata'] == before[0]['metadata']
    assert parent['dependencies'] == before[1]['dependencies']
    if phase == 'removed':
        assert 'dependencies' not in task and task['dependency_count'] == 0
        assert parent['dependent_count'] == 20
    else:
        assert task['dependencies'][0]['dependency_type'] == 'related'
        assert parent == before[1]
    m.require_images(*before, task, parent, phase)


@pytest.mark.parametrize('field,value', [
    ('status', 'closed'), ('metadata', {}), ('notes', 'replacement'),
    ('updated_at', '2026-09-28T07:00:00Z'), ('priority', 1),
    ('assignee', 'made-up-worker'), ('dependency_count', 0), ('dependent_count', 1),
])
def test_child_unrelated_drift_refuses(field, value):
    before = images()
    task, parent = m.expected_images(*before, 'related')
    task[field] = value
    with pytest.raises(RuntimeError, match='child delta'):
        m.require_images(*before, task, parent, 'related')


@pytest.mark.parametrize('change', ['prerequisite', 'notes', 'ownership', 'count'])
def test_parent_changes_refuse(change):
    before = images()
    task, parent = m.expected_images(*before, 'related')
    if change == 'prerequisite':
        parent['dependencies'][0]['status'] = 'closed'
    elif change == 'notes':
        parent['notes'] += ' another coordinator'
    elif change == 'ownership':
        parent['metadata'] = {}
    else:
        parent['dependent_count'] += 1
    with pytest.raises(RuntimeError, match='parent delta'):
        m.require_images(*before, task, parent, 'related')


@pytest.mark.parametrize('kind', ['real-blocks', 'other-parent', 'duplicate', 'unknown-phase'])
def test_only_exact_structural_edge_qualifies(kind):
    task, parent = images()
    phase = 'related'
    if kind == 'real-blocks':
        task['dependencies'][0]['dependency_type'] = 'blocks'
    elif kind == 'other-parent':
        task['dependencies'][0]['id'] = 'ga-other'
    elif kind == 'duplicate':
        task['dependencies'] *= 2
    else:
        phase = 'closed'
    with pytest.raises(RuntimeError):
        m.expected_images(task, parent, phase)


class API:
    def __init__(self, fail=None):
        self.original = images()
        self.state = copy.deepcopy(self.original)
        self.events, self.saved, self.writes = [], {}, []
        self.fail = fail

    def guard(self, name):
        self.events.append(('guard', name))
        if self.fail == name:
            raise RuntimeError('injected guard failure')

    def pair(self, name):
        self.events.append(('read', name))
        if self.fail == name:
            raise RuntimeError('injected read failure')
        return copy.deepcopy(self.state)

    def save(self, name, value):
        assert name not in self.saved
        self.events.append(('intent', name))
        self.saved[name] = value

    def run(self, name, args):
        phase = name.removesuffix('-write')
        assert phase + '-intent.json' in self.saved
        self.writes.append(args)
        self.events.append(('write', name))
        if self.fail == name:
            raise RuntimeError('injected ambiguous write result')
        self.state = m.expected_images(*self.original, phase)


def test_real_transition_function_uses_two_fixed_supported_writes():
    api = API()
    result = m.transact(api, *api.original)
    assert result == m.expected_images(*api.original, 'related')
    assert api.writes == [
        ['--rig', 'gascity', 'bd', 'dep', 'remove', m.TASK, m.PARENT, '--json'],
        ['--rig', 'gascity', 'bd', 'dep', 'add', m.TASK, m.PARENT, '--type', 'related', '--json'],
    ]
    assert all(value['retry'] is False for value in api.saved.values())


@pytest.mark.parametrize('failure,count', [
    ('removed', 0), ('removed-immediate', 0), ('removed-write', 1),
    ('removed-after', 1), ('related', 1), ('related-immediate', 1),
    ('related-write', 2), ('related-after', 2),
])
def test_failure_stops_without_write_replay_or_fallback(failure, count):
    api = API(failure)
    with pytest.raises(RuntimeError):
        m.transact(api, *api.original)
    assert len(api.writes) == count
    assert len({tuple(args) for args in api.writes}) == count


def test_immediate_ledger_drift_prevents_mutation():
    api = API()
    api.state[0]['notes'] = 'concurrent change'
    with pytest.raises(RuntimeError, match='pre-write ledger drift'):
        m.transact(api, *api.original)
    assert api.writes == [] and api.saved == {}


@pytest.mark.parametrize('kind', ['valid', 'session', 'city', 'rig', 'other-rig', 'running'])
def test_live_guard_shapes(kind):
    sessions = dict(ok=True, sessions=[])
    status = dict(suspended=True, summary=dict(running_agents=0),
                  rigs=[dict(name=name, suspended=True) for name in
                        ('gascity', 'gas-city-template', 'hpfetcher', 'blog')])
    if kind == 'session': sessions['sessions'] = [dict(id='unexpected')]
    elif kind == 'city': status['suspended'] = False
    elif kind == 'rig': status['rigs'][0]['suspended'] = False
    elif kind == 'other-rig': status['rigs'][0]['name'] = 'other'
    elif kind == 'running': status['summary']['running_agents'] = 1
    if kind == 'valid':
        m.quiet_value(sessions, status)
    else:
        with pytest.raises(RuntimeError):
            m.quiet_value(sessions, status)
