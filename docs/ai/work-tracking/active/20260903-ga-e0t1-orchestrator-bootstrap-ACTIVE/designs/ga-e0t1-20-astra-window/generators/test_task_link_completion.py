"""Native relate-shaped fixed fixtures; no live calls or main execution."""
import copy
import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / 'complete-task-link.py'
spec = importlib.util.spec_from_file_location('link_completion', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def before():
    return dict(
        task=dict(id='ga-e0t1.20', status='open', notes='brief', metadata={'gc.routed_to': 'gascity/codex'},
                  dependency_count=0, dependent_count=0, comment_count=0),
        parent=dict(id='ga-e0t1', status='in_progress', notes='audit', metadata={'owner': 'external'},
                    dependencies=[dict(id='ga-real', status='open', dependency_type='blocks')],
                    dependency_count=1, dependent_count=20, comment_count=0))


def after():
    # Specified independently: the fake never calls production expected_after.
    return dict(
        task=dict(id='ga-e0t1.20', status='open', notes='brief', metadata={'gc.routed_to': 'gascity/codex'},
                  dependency_count=1, dependent_count=1, comment_count=0,
                  dependencies=[dict(id='ga-e0t1', status='in_progress', notes='audit',
                                     metadata={'owner': 'external'}, dependency_type='relates-to')]),
        parent=dict(id='ga-e0t1', status='in_progress', notes='audit', metadata={'owner': 'external'},
                    dependencies=[dict(id='ga-real', status='open', dependency_type='blocks'),
                                  dict(id='ga-e0t1.20', status='open', notes='brief',
                                       metadata={'gc.routed_to': 'gascity/codex'}, dependency_type='relates-to')],
                    dependency_count=2, dependent_count=21, comment_count=0))


class API:
    def __init__(self, fail=None):
        self.events, self.writes = [], []
        self.state, self.fail = before(), fail

    def event(self, kind, name):
        self.events.append((kind, name))
        if self.fail == (kind, name):
            raise RuntimeError('injected failure')

    def guard(self, name):
        self.event('guard', name)

    def pair(self, name):
        self.event('read', name)
        return copy.deepcopy(self.state)

    def save(self, name, value):
        self.event('save', name)
        assert value['retry'] is False and value['before'] == before()

    def run(self, name, args):
        self.writes.append(args)
        self.event('write', name)
        self.state = after()
        return dict(id1='ga-e0t1.20', id2='ga-e0t1', related=True)


def test_independent_fixed_projection():
    original = before()
    assert m.expected_after(original) == {k: m.normalized(v) for k, v in after().items()}
    assert original == before()


def test_real_transition_uses_supported_see_also_not_dep_add_or_remove():
    api = API()
    result = m.transition(api, before())
    assert result == after()
    assert api.writes == [['--rig', 'gascity', 'bd', 'dep', 'relate', 'ga-e0t1.20', 'ga-e0t1', '--json']]
    assert api.events == [('guard', 'before'), ('read', 'immediate'), ('save', 'relate-intent.json'),
                          ('write', 'relate-write'), ('read', 'after'), ('guard', 'after')]


@pytest.mark.parametrize('point,count', [
    (('guard', 'before'), 0), (('read', 'immediate'), 0), (('save', 'relate-intent.json'), 0),
    (('write', 'relate-write'), 1), (('read', 'after'), 1), (('guard', 'after'), 1)])
def test_each_failure_including_intent_and_post_guard_has_no_replay(point, count):
    api = API(point)
    with pytest.raises(RuntimeError):
        m.transition(api, before())
    assert len(api.writes) == count


@pytest.mark.parametrize('key', ['status', 'notes', 'metadata', 'updated_at', 'assignee', 'dependency_count', 'dependent_count'])
@pytest.mark.parametrize('name', ['task', 'parent'])
def test_every_nonrelation_delta_refuses(name, key):
    actual = after()
    actual[name][key] = 'unrelated change'
    with pytest.raises(RuntimeError):
        m.verify_pair(actual, m.expected_after(before()))


def test_one_sided_relation_is_not_complete():
    actual = after()
    actual['parent'] = before()['parent']
    with pytest.raises(RuntimeError):
        m.verify_pair(actual, m.expected_after(before()))


def test_parent_blocking_prerequisite_never_disappears_or_changes_type():
    for replacement in ([], [dict(id='ga-real', status='closed', dependency_type='blocks')],
                         [dict(id='ga-real', status='open', dependency_type='related')]):
        actual = after()
        actual['parent']['dependencies'] = replacement + [after()['parent']['dependencies'][1]]
        with pytest.raises(RuntimeError):
            m.verify_pair(actual, m.expected_after(before()))


def test_only_order_is_normalized_not_duplicates_or_extra_fields():
    actual = after()
    actual['parent']['dependencies'].reverse()
    m.verify_pair(actual, m.expected_after(before()))
    actual['parent']['dependencies'].append(actual['parent']['dependencies'][0])
    with pytest.raises(RuntimeError):
        m.verify_pair(actual, m.expected_after(before()))


def test_bad_acknowledgement_cannot_pass():
    api = API()
    api.run = lambda *_: dict(related=True)
    with pytest.raises(RuntimeError, match='acknowledgement'):
        m.transition(api, before())


def test_immediate_drift_stops_before_intent_and_write():
    api = API()
    api.state['task']['notes'] = 'changed'
    with pytest.raises(RuntimeError):
        m.transition(api, before())
    assert api.writes == [] and not any(kind == 'save' for kind, _ in api.events)


def test_consumed_or_structural_input_cannot_be_adopted():
    for value in (after(), before()):
        if value == before():
            value['task']['parent'] = 'ga-e0t1'
        with pytest.raises(RuntimeError):
            m.expected_after(value)

