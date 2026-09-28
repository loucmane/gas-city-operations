"""Exercise the generated successor, not an alternate hand-built contract."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import types

import pytest

import successor


def module(raw, name):
    value = types.ModuleType(name)
    value.__file__ = name+'.py'
    exec(compile(raw, value.__file__, 'exec'), value.__dict__)
    return value


@pytest.fixture(scope='module')
def built():
    sources, previous, out = successor.assemble()
    return previous, out, module(out['continuation-admission.py'], 'admission'), module(out['contract.py'], 'contract')


@pytest.fixture
def pair(built):
    m = built[2]
    path = m.COMPLETED/'final.json'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m.PINS[path]
    return json.loads(raw)


def test_exact_completed_live_pair_is_accepted(built, pair):
    built[2].compare_pair(pair, pair, parent_audit=True)
    built[3].validate_task(pair['task'], 'routed')


def test_parent_audit_must_be_mirrored_and_is_not_allowed_after_admission(built, pair):
    after = copy.deepcopy(pair)
    after['parent']['notes'] += '\nSupported append-forward outcome'
    after['parent']['updated_at'] = '2026-09-28T08:30:00Z'
    for key in ('notes', 'updated_at'):
        after['task']['dependencies'][0][key] = after['parent'][key]
    built[2].compare_pair(after, pair, parent_audit=True)
    with pytest.raises(RuntimeError):
        built[2].compare_pair(after, pair)
    after['task']['dependencies'][0]['notes'] = pair['task']['dependencies'][0]['notes']
    with pytest.raises(RuntimeError):
        built[2].compare_pair(after, pair, parent_audit=True)


@pytest.mark.parametrize('key', ['status', 'assignee', 'metadata', 'title', 'description',
                                'acceptance_criteria', 'dependency_count', 'dependent_count', 'unknown'])
@pytest.mark.parametrize('which', ['task', 'parent'])
def test_no_own_field_relaxation(built, pair, key, which):
    after = copy.deepcopy(pair)
    after[which][key] = 'drift'
    with pytest.raises(RuntimeError):
        built[2].compare_pair(after, pair, parent_audit=True)


@pytest.mark.parametrize('kind', ['missing', 'closed', 'type', 'duplicate'])
def test_genuine_parent_prerequisites_remain_exact(built, pair, kind):
    after = copy.deepcopy(pair)
    deps = after['parent']['dependencies']
    row = next(d for d in deps if d['dependency_type'] == 'blocks' and d['status'] != 'closed')
    if kind == 'missing':
        deps.remove(row)
    elif kind == 'closed':
        row['status'] = 'closed'
    elif kind == 'type':
        row['dependency_type'] = 'relates-to'
    else:
        deps.append(copy.deepcopy(row))
    with pytest.raises(RuntimeError):
        built[2].compare_pair(after, pair, parent_audit=True)


@pytest.mark.parametrize('stamp', ['2000-01-01T00:00:00Z', '2026-09-28T08:30:00', 'invalid'])
def test_invalid_parent_audit_time_refuses(built, pair, stamp):
    after = copy.deepcopy(pair)
    after['parent']['updated_at'] = stamp
    with pytest.raises((RuntimeError, ValueError)):
        built[2].compare_pair(after, pair, parent_audit=True)


@pytest.mark.parametrize('kind', ['parent', 'zero-count', 'old-edge', 'claim', 'extra-control'])
def test_real_generated_contract_refuses_wrong_successor_shape(built, pair, kind):
    task = pair['task']
    if kind == 'parent':
        task['parent'] = 'ga-e0t1'
    elif kind == 'zero-count':
        task['dependent_count'] = 0
    elif kind == 'old-edge':
        task['dependencies'][0]['dependency_type'] = 'parent-child'
    elif kind == 'claim':
        task['assignee'] = 'unexpected'
    else:
        task['metadata']['gc.check_path'] = '/invented'
    with pytest.raises(RuntimeError):
        built[3].validate_task(task, 'routed')


def test_binding_graph_and_wrapper_shell_syntax(built, tmp_path):
    previous, out, _, _ = built
    assert successor.assemble()[1:3] == (previous, out)
    assert len(out) == 57
    for name, raw in out.items():
        if not name.endswith('.sh'):
            continue
        path = tmp_path/Path(name).name
        path.write_bytes(raw)
        assert subprocess.run(['/bin/sh', '-n', str(path)]).returncode == 0
        for script, var in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"', raw.decode()):
            [pin] = re.findall(r'^%s=([0-9a-f]{64})$' % var, raw.decode(), re.M)
            assert pin == hashlib.sha256(out[script]).hexdigest(), (name, script)
    for name in ('WORKER-BRIEF.md', 'worker-startup.py', 'common-snapshot-r1.py', 'read-time-accounting.py'):
        assert out[name] == previous[name]


def test_completed_wrappers_cannot_replay(built, tmp_path):
    for name in ('BIND', 'ROUTE'):
        path = tmp_path/(name+'.sh')
        path.write_bytes(built[1]['operator/'+name+'.sh'])
        result = subprocess.run(['/bin/sh', str(path)], capture_output=True)
        assert result.returncode == 125 and result.stdout == b''
        assert b'replay prohibited' in result.stderr


def test_queue_and_ledger_admission_precede_live_stage(built):
    out = built[1]
    stage = out['operator/STAGE.sh'].decode()
    assert stage.index('step audit-route ') < stage.index('step stage ')
    base = out['window-base-r11.py'].decode()
    assert base.index('.admit(') < base.index("save('preflight-pass.json'")
    assert base.index('.recheck(') < base.index("save('stage-consumed.json'")
    assert "w.read(WINDOW/'admitted-task.json')" in out['startup-release.py'].decode()
    assert "w.read(ROUTE/'task-after.json')" not in out['startup-release.py'].decode()


def test_new_window_close_and_output_roots_do_not_adopt_consumed_null_identity(built):
    out = built[1]
    for name, raw in out.items():
        if name in ('continuation-admission.py', 'window-base-r11.py'):
            continue  # Deliberately binds historical read-only evidence.
        for old in successor.ROOTS:
            assert old.encode() not in raw, (name, old)
    close = out['close-r11.py'].decode()
    assert "identity_path=VAR/'ga-e0t1.20-r3-close-session.json'" in close
    assert "drain = VAR/'ga-e0t1.20-r3-close-drain.requested'" in close
    assert "VAR.glob('ga-e0t1.20-r3-hold-*/result.json')" in close


def test_exact_proven_restoration_is_the_baseline_not_pre_window_inodes(built):
    w = module(built[1]['window-base-r11.py'], 'restored_baseline')
    prior = json.loads(w.read(w.ACCEPTED, w.ACCEPTED_SHA))
    observed = json.loads(Path('/tmp/ga-e0t1-20-readonly-baseline-20260928-r11/observed.json').read_bytes())
    expected = w.approved_candidate_cache_image({k: prior[k] for k in w.ACCEPTED_KEYS})
    assert w.dependency_image(expected) == w.dependency_image(observed)
    original = json.loads(Path('/var/tmp/gct-oak5-p13-adoption-20260927/after.json').read_bytes())
    assert prior['pins'][str(w.CITY/'city.toml')]['metadata']['inode'] != original['pins'][str(w.CITY/'city.toml')]['metadata']['inode']
    assert 'previous window was not proven restored' in built[1]['window-base-r11.py'].decode()
    changed = copy.deepcopy(prior)
    changed['cache']['inventory'][w.CACHE_DIRECTORY]['mtime_ns'] += 1
    with pytest.raises(RuntimeError, match='preimage'):
        w.approved_candidate_cache_image(changed)


def test_real_admission_and_recheck_only_read_supported_beads(built, pair):
    m = built[2]
    saved, calls = {}, []
    def read(path, pin):
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pin
        return raw
    def phase(name, argv, *_args, **_kwargs):
        assert argv[:4] == ['gc', '--rig', 'gascity', 'bd']
        assert argv[4] == 'show' and argv[-1] == '--json'
        calls.append(name)
        value = pair['task' if argv[5] == m.TASK else 'parent']
        return dict(stdout=json.dumps([value]))
    w = types.SimpleNamespace(read=read, GC=['gc'], phase=phase, save=lambda n,v: saved.update({n: copy.deepcopy(v)}),
        record=lambda n: saved[n], contract=lambda: built[3])
    m.admit(w, None, None)
    assert saved['admitted-task.json'] == pair['task'] and len(calls) == 4
    m.recheck(w, None, None)
    assert saved['stage-admitted-pair.json'] == pair and len(calls) == 6
    pair['task']['notes'] += 'drift'
    with pytest.raises(RuntimeError):
        m.recheck(w, None, None)
