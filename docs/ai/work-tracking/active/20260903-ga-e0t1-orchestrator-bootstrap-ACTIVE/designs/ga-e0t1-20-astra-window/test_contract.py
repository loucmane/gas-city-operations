import copy
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('window_contract', HERE/'contract.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


@pytest.fixture
def task():
    return json.loads((HERE/'task-own-fields.json').read_bytes())


def test_exact_parent_edge_accepts_without_exporting_parent_notes(task):
    original = copy.deepcopy(task)
    c.validate_task(task, 'unbound')
    task['dependencies'][0]['notes'] = 'Historical parent evidence is not worker input'
    c.validate_task(task, 'unbound')
    assert original['dependencies'][0]['dependency_type'] == 'parent-child'


@pytest.mark.parametrize('kind', ['blocks', 'duplicate', 'missing', 'other-parent', 'dependent',
                                  'wrong-count', 'claimed', 'external-owner', 'notes', 'description', 'acceptance'])
def test_task_boundary_refuses(task, kind):
    if kind == 'blocks': task['dependencies'][0]['dependency_type'] = 'blocks'
    elif kind == 'duplicate': task['dependencies'] *= 2
    elif kind == 'missing': task['dependencies'] = []
    elif kind == 'other-parent': task['dependencies'][0]['id'] = 'ga-other'
    elif kind == 'dependent': task['dependents'] = [{'id': 'ga-extra'}]
    elif kind == 'wrong-count': task['dependency_count'] = 0
    elif kind == 'claimed': task['assignee'] = 'ci-extra'
    elif kind == 'external-owner': task['metadata'] = {'workflow.external_owner': 'fake'}
    elif kind == 'notes': task['notes'] = 'new'
    elif kind == 'description': task['description'] += 'changed'
    elif kind == 'acceptance': task['acceptance_criteria'] += 'changed'
    with pytest.raises(RuntimeError): c.validate_task(task, 'unbound')


def test_control_metadata_is_exact_by_phase(task):
    task['metadata'] = {'gc.work_dir': c.WORK}
    task['notes'] = c.BOUND_NOTE
    c.validate_task(task, 'bound')
    with pytest.raises(RuntimeError): c.validate_task(task, 'unbound')
    task['metadata']['gc.routed_to'] = c.TARGET
    c.validate_task(task, 'routed')
    with pytest.raises(RuntimeError): c.validate_task(task, 'bound')
    task['metadata']['gc.check_path'] = '/invented'
    with pytest.raises(RuntimeError): c.validate_task(task, 'routed')


def candidate_rows():
    return rules()+b' M '+c.SOURCE_PATHS[1].encode()+b'\0?? .gc/worker-evidence/'+c.TASK.encode()+b'/report.json\0'


def test_candidate_inventory_separates_scoped_source_and_evidence():
    result=c.candidate_status(candidate_rows())
    assert result['source']==[c.SOURCE_PATHS[1]] and len(result['evidence'])==1


@pytest.mark.parametrize('extra',[
    b'M  source.py\0', b' M unrelated.py\0', b' D .gitignore\0',
    b'?? .codex/hooks.json\0', b'!! secret.txt\0',
    b'?? .gc/worker-evidence/ga-e0t1.20/../outside\0',
    b'?? .gc/worker-evidence/ga-other/report.json\0', b'?? /absolute\0',
])
def test_unaccepted_candidate_status_refuses(extra):
    with pytest.raises(RuntimeError):c.candidate_status(candidate_rows()+extra)


def test_candidate_staged_change_or_duplicate_or_no_source_refuses():
    with pytest.raises(RuntimeError):c.candidate_status(candidate_rows().replace(b' M ',b'M  '))
    with pytest.raises(RuntimeError):c.candidate_status(candidate_rows()+candidate_rows())
    with pytest.raises(RuntimeError):c.candidate_status(rules())


def rules():
    return b'\0'.join(b'!! '+path.encode() for path in c.RULES) + b'\0'


def test_two_ignored_policy_files_only():
    c.validate_rule_status(rules())


@pytest.mark.parametrize('suffix', [b'?? rogue\0', b' M DESIGN.md\0', b'!! .codex/rules/extra.rules\0'])
def test_extra_workspace_file_refuses(suffix):
    with pytest.raises(RuntimeError): c.validate_rule_status(rules()+suffix)


def test_missing_or_duplicate_rule_refuses():
    first = rules().split(b'\0')[0]+b'\0'
    for raw in (b'', first, first+first, rules()[:-1]):
        with pytest.raises(RuntimeError): c.validate_rule_status(raw)


@pytest.fixture
def live():
    return dict(agents=[
        dict(name='codex', qualified_name=c.TARGET, scope='rig', running=True, suspended=False),
        dict(name='codex-ci-example', qualified_name='codex-ci-example', scope='city', running=True, suspended=True),
    ], summary=dict(running_agents=2, active_sessions=1))


@pytest.fixture
def census():
    return dict(ok=True, sessions=[dict(id='ci-example', template=c.TARGET,
                                      session_name='codex-ci-example', closed=False,
                                      work_dir=c.WORK, rig='gascity', provider='codex')])


def test_one_worker_two_display_rows_only_for_suspend(live, census):
    for action in ('city-suspend', 'rig-suspend'):
        assert len(c.running_rows(live, census, action)) == 2
    for action in ('city-resume', 'rig-resume'):
        with pytest.raises(RuntimeError): c.running_rows(live, census, action)


@pytest.mark.parametrize('kind', ['two-sessions', 'wrong-template', 'no-census', 'wrong-id',
                                  'two-session-rows', 'wrong-scope', 'wrong-count', 'bool-count',
                                  'wrong-workspace', 'wrong-provider'])
def test_extra_or_ambiguous_worker_refuses(live, census, kind):
    if kind == 'two-sessions': census['sessions'] *= 2
    elif kind == 'wrong-template': census['sessions'][0]['template'] = 'blog/codex'
    elif kind == 'no-census': census['sessions'] = []
    elif kind == 'wrong-id': census['sessions'][0]['session_name'] = 'other'
    elif kind == 'two-session-rows': live['agents'].append(copy.deepcopy(live['agents'][1])); live['summary']['running_agents'] = 3
    elif kind == 'wrong-scope': live['agents'][1]['scope'] = 'rig'
    elif kind == 'wrong-count': live['summary']['running_agents'] = 1
    elif kind == 'bool-count': live['summary']['active_sessions'] = True
    elif kind == 'wrong-workspace': census['sessions'][0]['work_dir'] = '/somewhere-else'
    elif kind == 'wrong-provider': census['sessions'][0]['provider'] = 'claude'
    with pytest.raises(RuntimeError): c.running_rows(live, census, 'city-suspend')


def test_empty_and_canonical_single_row_are_valid(live, census):
    live['agents'].pop(); live['summary']['running_agents'] = 1
    assert len(c.running_rows(live, census, 'city-resume')) == 1
    assert c.running_rows(dict(agents=[], summary=dict(running_agents=0, active_sessions=0)),
                          dict(ok=True, sessions=[]), 'rig-suspend') == []


def test_source_scope_has_no_signing_or_live_paths():
    c.require_source_scope(list(c.SOURCE_PATHS))
    for paths in ([], ['city.toml'], [c.SOURCE_PATHS[0]]*2,
                  [c.SOURCE_PATHS[0], '.codex/rules/window-restrictions.rules']):
        with pytest.raises(RuntimeError): c.require_source_scope(paths)
