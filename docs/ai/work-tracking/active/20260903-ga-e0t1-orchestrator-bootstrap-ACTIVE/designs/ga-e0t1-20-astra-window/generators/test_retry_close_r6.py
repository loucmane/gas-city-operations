"""Execute generated retry CLOSE with only disposable state and fake controls."""
import copy
import json
from pathlib import Path

import pytest

import test_close as flow
import test_window_r6 as fixtures
import window_r6 as build


@pytest.fixture(scope='module')
def assets():
    return build.assemble(1790603075048109174)[1]


@pytest.fixture
def state(assets):
    contract = fixtures.module(assets['contract.py'])
    evidence = {path: json.loads(path.read_bytes()) for path in build.recovery.PINS}
    legacy = fixtures.module(assets['legacy-continuation-r4.py'])
    task = build.recovery.expected_pair(evidence, legacy.normalized)['task']
    task['notes'] = contract.BOUND_NOTE
    task['updated_at'] = '2026-09-28T14:15:00Z'
    session = dict(flow.session(), id='ci-fresh', session_name='codex-ci-fresh',
                   created_at='2026-09-28T14:16:00.123Z')
    contract.validate_task(task, 'routed')
    return contract, task, session


def fixture(assets, state, tmp_path, monkeypatch, claims=None):
    contract, task, session = state
    monkeypatch.setattr(flow, 'c', contract)
    m, commands = flow.run_fixture(assets['close-r11.py'], tmp_path,
                                  [[session], [session], []], claim=task)
    (m.WINDOW/'admitted-task.json').write_text(json.dumps(task))
    if claims is not None:
        w = m.load()
        original = w.phase
        pending = iter(claims)
        def phase(name, argv, *args, **kwargs):
            if 'show' in argv:
                commands.append(argv)
                return dict(stdout=json.dumps([next(pending)]))
            return original(name, argv, *args, **kwargs)
        w.phase = phase
    return m, commands


def test_exact_unclaimed_retry_drains_and_closes_fresh_session(assets, state, tmp_path, monkeypatch):
    before = copy.deepcopy(state[1])
    m, commands = fixture(assets, state, tmp_path, monkeypatch)
    m.main()
    assert [a[1:4] for a in flow.mutations(commands)] == [
        ['runtime', 'drain', 'ci-fresh'], ['session', 'close', 'ci-fresh']]
    assert state[1] == before
    assert before['metadata']['gc.session_id'] == 'ci-rks41'
    assert json.loads((m.WINDOW/'admitted-task.json').read_text()) == before


@pytest.mark.parametrize('field', ['notes', 'updated_at', 'metadata', 'description',
                                  'acceptance_criteria', 'dependencies', 'started_at', 'assignee'])
def test_unclaimed_drift_refuses_before_drain(assets, state, tmp_path, monkeypatch, field):
    bad = copy.deepcopy(state[1])
    bad[field] = 'unrelated'
    m, commands = fixture(assets, state, tmp_path, monkeypatch, [bad])
    with pytest.raises(RuntimeError):
        m.main()
    assert flow.mutations(commands) == []


def test_foreign_claim_between_drain_and_close_refuses(assets, state, tmp_path, monkeypatch):
    foreign = copy.deepcopy(state[1])
    foreign.update(status='in_progress', assignee='codex-ci-foreign')
    foreign['metadata'].update({'gc.session_id': 'ci-foreign', 'gc.session_name': 'codex-ci-foreign'})
    m, commands = fixture(assets, state, tmp_path, monkeypatch, [state[1], foreign])
    with pytest.raises(RuntimeError):
        m.main()
    assert [a[1:4] for a in flow.mutations(commands)] == [['runtime', 'drain', 'ci-fresh']]


def test_real_fresh_claim_between_drain_and_close_remains_supported(assets, state, tmp_path, monkeypatch):
    claimed = copy.deepcopy(state[1])
    claimed.update(status='in_progress', assignee='codex-ci-fresh')
    claimed['metadata'].update({'gc.session_id': 'ci-fresh', 'gc.session_name': 'codex-ci-fresh'})
    m, commands = fixture(assets, state, tmp_path, monkeypatch, [state[1], claimed])
    m.main()
    assert [a[1:4] for a in flow.mutations(commands)][-1] == ['session', 'close', 'ci-fresh']


@pytest.mark.parametrize('change', ['old-id', 'old-name', 'old-time', 'bad-time', 'no-admitted'])
def test_historical_or_unbound_session_cannot_use_exception(assets, state, tmp_path, monkeypatch, change):
    contract, task, session = state
    if change == 'old-id': session['id'] = 'ci-rks41'
    elif change == 'old-name': session['session_name'] = 'codex-ci-rks41'
    elif change == 'old-time': session['created_at'] = '2026-09-28T13:01:40Z'
    elif change == 'bad-time': session['created_at'] = 'not-a-time'
    m, commands = fixture(assets, state, tmp_path, monkeypatch)
    if change == 'no-admitted': (m.WINDOW/'admitted-task.json').unlink()
    with pytest.raises((RuntimeError, FileNotFoundError)):
        m.main()
    assert flow.mutations(commands) == []


def test_active_historical_owner_is_not_reinterpreted_as_unclaimed(assets, state, tmp_path, monkeypatch):
    old = copy.deepcopy(state[1])
    old.update(status='in_progress', assignee='codex-ci-rks41')
    m, commands = fixture(assets, state, tmp_path, monkeypatch, [old])
    with pytest.raises(RuntimeError): m.main()
    assert flow.mutations(commands) == []
