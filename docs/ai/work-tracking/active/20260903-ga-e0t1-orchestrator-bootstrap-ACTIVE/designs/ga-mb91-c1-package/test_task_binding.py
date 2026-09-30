"""Real release adapter task-binding regressions; offline fixtures only."""
import pytest
from test_runtime import harness


@pytest.mark.parametrize('existing', [False, True])
def test_fresh_window_task_reaches_native_delivery(monkeypatch, existing):
    run, calls, saved = harness(monkeypatch, existing=existing, task='ga-mb91')
    assert run()['delivered']
    assert sum(c[3:5] == ['session', 'nudge'] for c in calls) == 1
    assert saved['delivery-acknowledged.json']['delivered']


@pytest.mark.parametrize('existing', [False, True])
@pytest.mark.parametrize('task', ['ga-goo5', 'ga-other', '', None])
def test_predecessor_and_other_tasks_refuse_before_enqueue(monkeypatch, existing, task):
    run, calls, saved = harness(monkeypatch, existing=existing, task=task)
    with pytest.raises(RuntimeError, match='native session authority'):
        run()
    assert not any(c[3:5] == ['session', 'nudge'] for c in calls)
    assert 'delivery-baseline.json' not in saved
    assert 'delivery-enqueued.json' not in saved
    assert 'delivery-acknowledged.json' not in saved
