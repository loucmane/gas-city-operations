"""Pure real-schema regressions; no lifecycle, live fixture read or execution."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('zero_session_contract', HERE / 'contract.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
ACTIONS = ('rig-resume', 'city-resume', 'city-suspend', 'rig-suspend')


@pytest.fixture
def observed():
    return tuple(json.loads((HERE / 'fixtures' / name).read_bytes()) for name in
                 ('zero-session-status.json', 'zero-session-census.json'))


@pytest.mark.parametrize('action', ACTIONS)
def test_actual_zero_omission_and_explicit_zero_are_equivalent(observed, action):
    status, census = observed
    assert 'active_sessions' not in status['summary']
    before = copy.deepcopy(observed)
    assert c.running_rows(status, census, action) == []
    assert observed == before
    status['summary']['active_sessions'] = 0
    assert c.running_rows(status, census, action) == []


def suspended_session():
    return dict(id='ci-example', session_name='codex-ci-example', template=c.TARGET,
                work_dir=c.WORK, rig='gascity', provider=c.PROVIDER,
                state='suspended', closed=False)


@pytest.mark.parametrize('action', ACTIONS)
def test_omission_with_one_proven_suspended_nonrunning_session(observed, action):
    status, census = observed
    census['sessions'] = [suspended_session()]
    census['summary'].update(total=1, suspended=1)
    assert c.running_rows(status, census, action) == []


@pytest.mark.parametrize('bad', [None, False, True, '0', 0.0, -1, 2, [], {}])
def test_present_invalid_active_count_never_defaults_to_zero(observed, bad):
    status, census = observed
    status['summary']['active_sessions'] = bad
    with pytest.raises(RuntimeError):
        c.running_rows(status, census, 'rig-resume')


@pytest.mark.parametrize('kind', [
    'failed-census', 'missing-summary', 'missing-active', 'boolean-active',
    'string-total', 'extra-count', 'active-count', 'closed-count', 'missing-rows',
    'extra-row', 'active-row', 'stateless-row', 'wrong-worker', 'running-row',
    'running-count', 'two-sessions',
])
def test_omission_requires_independent_zero_and_no_running_worker(observed, kind):
    status, census = observed
    if kind == 'failed-census': census['ok'] = False
    elif kind == 'missing-summary': census.pop('summary')
    elif kind == 'missing-active': census['summary'].pop('active')
    elif kind == 'boolean-active': census['summary']['active'] = False
    elif kind == 'string-total': census['summary']['total'] = '0'
    elif kind == 'extra-count': census['summary']['total'] = 1
    elif kind == 'active-count': census['summary']['active'] = 1
    elif kind == 'closed-count': census['summary']['closed'] = 1
    elif kind == 'missing-rows': census.pop('sessions')
    elif kind in ('extra-row', 'active-row', 'stateless-row', 'wrong-worker', 'two-sessions'):
        census['sessions'] = [suspended_session()]
        if kind != 'extra-row': census['summary'].update(total=1, suspended=1)
        if kind == 'active-row': census['sessions'][0]['state'] = 'active'
        if kind == 'stateless-row': census['sessions'][0].pop('state')
        if kind == 'wrong-worker': census['sessions'][0]['template'] = 'blog/codex'
        if kind == 'two-sessions':
            census['sessions'] *= 2
            census['summary'].update(total=2, suspended=2)
    elif kind == 'running-row':
        status['agents'][-1]['running'] = True
        status['summary']['running_agents'] = 1
    elif kind == 'running-count': status['summary']['running_agents'] = 1
    with pytest.raises(RuntimeError):
        c.running_rows(status, census, 'rig-suspend')


def test_nonzero_still_requires_a_census_session(observed):
    status, census = observed
    status['summary']['active_sessions'] = 1
    with pytest.raises(RuntimeError):
        c.running_rows(status, census, 'city-resume')


def test_nonzero_canonical_worker_keeps_identity_checks(observed):
    status, census = observed
    status['agents'][-1]['running'] = True
    status['summary'].update(running_agents=1, active_sessions=1)
    census['sessions'] = [dict(suspended_session(), state='active')]
    census['summary'].update(total=1, active=1)
    assert len(c.running_rows(status, census, 'city-resume')) == 1
    census['sessions'][0]['provider'] = 'claude'
    with pytest.raises(RuntimeError):
        c.running_rows(status, census, 'city-resume')
