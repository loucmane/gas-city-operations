"""Generated operation tests using disposable fixtures and a fake control plane.

No real gc, Bead, Git, systemd or worker invocation. Exact source rebinding and
negative input tests accompany execution of the real generated BIND body.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import types

import pytest

HERE = Path(__file__).parent
OLD = HERE.parent / 'ga-e0t1-20-astra-window'


def load(raw, name='fixture', path=None):
    m = types.ModuleType(name)
    m.__file__ = str(path or HERE / (name + '.py'))
    exec(compile(raw, m.__file__, 'exec'), m.__dict__)
    return m


c = load((HERE / 'contract.py').read_bytes(), 'fresh_contract')
a = load((HERE / 'task-assembly.py').read_bytes(), 'task_assembly')
BASE_SHA, WINDOW_SHA = 'a' * 64, 'b' * 64


def scripts():
    bind = a.binding((OLD / 'bind-task-r5.py').read_bytes(), base_sha=BASE_SHA, contract=c)
    route = a.routing((OLD / 'route-task-r5.py').read_bytes(), window_sha=WINDOW_SHA,
                      binding_sha=a.sha(bind), contract=c)
    return bind, route


def test_generated_identity_scope_and_provenance():
    bind, route = scripts()
    bm, rm = load(bind), load(route)
    assert str(bm.ROOT) == a.ROOT and str(rm.ROOT) == a.ROUTE
    assert bm.HELPER_SHA == BASE_SHA and rm.SHA == WINDOW_SHA
    assert rm.BIND_SHA == a.sha(bind)
    assert bm.DESCRIPTION_SHA == rm.DESCRIPTION_SHA == c.DESCRIPTION
    assert bm.WORK == c.WORK
    assert bm.WORKTREE_SHA == a.WORKTREE
    assert not any(old in bind + route for old in (
        b'ga-e0t1.20', b'COMPLETED OPERATION', b'0f85dbaa6de8c174',
        b'e58d90d46f6422aeb', b'recovered-claim',
    ))


@pytest.mark.parametrize('which', ['bind', 'route'])
def test_changed_predecessor_refuses(which):
    with pytest.raises(ValueError, match='predecessor'):
        if which == 'bind':
            a.binding(b'not the reviewed predecessor', base_sha=BASE_SHA, contract=c)
        else:
            a.routing(b'not the reviewed predecessor', window_sha=WINDOW_SHA,
                      binding_sha=BASE_SHA, contract=c)


@pytest.mark.parametrize('value', ['', 'short', 'A' * 64, 'a' * 65, None])
def test_exact_helper_pins_required(value):
    with pytest.raises(ValueError):
        a.binding((OLD / 'bind-task-r5.py').read_bytes(), base_sha=value, contract=c)


def setup_binding(tmp_path):
    bind, _ = scripts()
    script = tmp_path / 'bind-task.py'
    script.write_bytes(bind)
    m = load(bind, path=script)
    helper = tmp_path / 'window-base.py'
    helper.write_bytes(b'pass\n')
    m.HELPER, m.HELPER_SHA = helper, a.sha(helper.read_bytes())
    m._SOURCE_SHA = a.sha(bind)
    m.ROOT = tmp_path / 'binding'
    m.WORKTREE_RESULT = tmp_path / 'completed-worktree.json'
    state = dict(task=copy.deepcopy(c.BASELINE), mutations=[], host_calls=0)
    w = types.ModuleType('fake_window')
    w.ROOT = tmp_path / 'never-created-window'
    w.ADMIN = Path('/home/loucmane/gas-city-ops/.git/worktrees/ga-x2wz')
    w.BASE = c.BASE
    w.CITY = tmp_path / 'fake-city'
    w.RECEIPT = tmp_path / 'fake-receipt.json'
    w.CITY_SHA = ['city-before']
    w.RECEIPT_SHA = ['receipt-before']
    w.GC = ['gc', '--city', str(w.CITY)]
    w.contract = lambda: c
    w.load_support = lambda: (None, None, None)
    w.pins = lambda: None
    def host(unused):
        state['host_calls'] += 1
        return dict(epoch=1)
    w.host = host
    made = dict(ok=True, worker_launched=False, tracked_clean=True, worktree=c.WORK,
                admin=str(w.ADMIN), base=c.BASE, branch=c.BRANCH,
                local_rules=c.RULES, default_rules_unchanged=True)
    def read(path, expected=None):
        if path == m.WORKTREE_RESULT:
            assert expected == a.WORKTREE
            return json.dumps(made).encode()
        if path == w.CITY / 'city.toml':
            assert expected == w.CITY_SHA[0]
            return b'city'
        if path == w.RECEIPT:
            assert expected == w.RECEIPT_SHA[0]
            return b'receipt'
        return Path(path).read_bytes()
    w.read = read
    w.save = lambda name, value: (w.ROOT / name).write_text(json.dumps(value))
    w.record = lambda name: json.loads((w.ROOT / name).read_bytes())
    def phase(name, args, *unused):
        if name == 'task-bind':
            expected = w.GC + ['--rig', 'gascity', 'bd', 'update', c.TASK,
                '--set-metadata', 'gc.work_dir=' + c.WORK, '--append-notes', c.BIND_NOTE]
            assert args == expected
            state['mutations'].append(args)
            state['task']['metadata'] = {'gc.work_dir': c.WORK}
            state['task']['notes'] += '\n' + c.BIND_NOTE
        else:
            assert args == w.GC + ['--rig', 'gascity', 'bd', 'show', c.TASK, '--json']
        return dict(stdout=json.dumps([state['task']]))
    w.phase = phase
    # Substitute only the dependency loader in this disposable test. The
    # generated executor body runs unchanged; production modules never do this.
    m.types = types.SimpleNamespace(ModuleType=lambda name: w)
    return m, w, state, made


def test_bind_executes_exactly_one_append_forward_supported_update(tmp_path):
    m, w, state, _ = setup_binding(tmp_path)
    original = copy.deepcopy(state['task'])
    m.main()
    assert len(state['mutations']) == 1
    assert state['task']['notes'] == original['notes'] + '\n' + c.BIND_NOTE
    assert w.record('result.json') == dict(ok=True, bead=c.TASK, contract_bound=True,
        routed=False, assigned=False, worker_launched=False, live_configuration_changed=False)
    assert w.record('binding-intent.json')['before'] == original
    assert w.record('binding-intent.json')['note'] == c.BIND_NOTE
    assert (m.ROOT / 'sandbox-negative').is_dir()
    assert state['host_calls'] == 2


@pytest.mark.parametrize('key,value', [('branch', 'wrong'), ('base', '0'*40),
    ('worker_launched', True), ('tracked_clean', False), ('default_rules_unchanged', False)])
def test_invalid_worktree_proof_refuses_before_mutation(tmp_path, key, value):
    m, w, state, made = setup_binding(tmp_path)
    made[key] = value
    with pytest.raises(AssertionError):
        m.main()
    assert state['mutations'] == []
    assert not m.ROOT.exists()


def test_bind_preserves_consumed_root_and_refuses_replay(tmp_path):
    m, w, state, _ = setup_binding(tmp_path)
    m.main()
    original = (m.ROOT / 'result.json').read_bytes()
    # Production reloads a fresh helper module for each process. Reset only
    # this fixture's reused module root to model that load before the retry.
    w.ROOT = tmp_path / 'never-created-window'
    with pytest.raises(FileExistsError):
        m.main()
    assert len(state['mutations']) == 1
    assert (m.ROOT / 'result.json').read_bytes() == original


def test_bad_task_refuses_without_bead_write(tmp_path):
    m, w, state, _ = setup_binding(tmp_path)
    state['task']['status'] = 'in_progress'
    with pytest.raises(RuntimeError):
        m.main()
    assert not state['mutations']
    assert (m.ROOT / 'task-before.json').exists()
    assert not (m.ROOT / 'binding-intent.json').exists()


def test_partial_update_is_recorded_and_never_retried(tmp_path):
    m, w, state, _ = setup_binding(tmp_path)
    original = w.phase
    def drift(name, *args, **kwargs):
        answer = original(name, *args, **kwargs)
        if name == 'task-bind':
            state['task']['title'] = 'unexpected mutation'
        return answer
    w.phase = drift
    with pytest.raises(RuntimeError):
        m.main()
    assert len(state['mutations']) == 1
    assert (m.ROOT / 'binding-intent.json').exists()
    assert (m.ROOT / 'task-after.json').exists()
    assert not (m.ROOT / 'result.json').exists()


def test_route_receipt_accepts_only_new_complete_bind_proof(tmp_path):
    m, w, state, _ = setup_binding(tmp_path)
    m.main()
    _, route = scripts()
    r = load(route)
    r.BIND = m.ROOT
    r.BIND_SHA = m._SOURCE_SHA
    w.WORK = Path(c.WORK)
    assert r.completed_binding(w) == state['task']
    (m.ROOT / 'result.json').write_text(json.dumps(dict(ok=True, worker_launched=True)))
    with pytest.raises(AssertionError):
        r.completed_binding(w)


def test_route_has_one_dry_run_then_one_live_call_and_closed_delta():
    _, route = scripts()
    text = route.decode()
    assert text.index("run('route-preview'") < text.index("w.save('route-intent.json'") < text.index("run('route',argv)")
    assert text.count("run('route',argv)") == 1
    assert "'--no-formula','--no-convoy','--json'" in text
    assert 'w.contract().validate_route_delta(before,after)' in text
    assert text.count('assert w.host(o)==before_host') == 2
    assert text.count('assert w.host(o)==before_host') == (OLD / 'route-task-r5.py').read_text().count('assert w.host(o)==before_host')
    assert 'fresh_full_queue_audit_required_before_resume=True' in text


def test_unrelated_preroute_controls_are_unchanged():
    _, route = scripts()
    original = (OLD / 'route-task-r5.py').read_text()
    start = "    # ga-e0t1.20:"
    stop = "    after=bead('task-after-read')"
    previous = a.retarget(original[original.index(start):original.index(stop)])
    previous = previous.replace("variant='template-root-pieces'", "variant='candidate-root-pieces'")
    text = route.decode()
    assert previous == text[text.index("    # ga-x2wz:"):text.index(stop)]
