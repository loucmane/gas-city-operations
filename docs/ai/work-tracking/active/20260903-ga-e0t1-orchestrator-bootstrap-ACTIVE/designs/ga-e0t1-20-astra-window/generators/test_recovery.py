"""Offline recovery-only proofs. All writes are disposable pytest fixtures."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import types

import pytest

import recovery
import successor


def load(raw, name):
    m = types.ModuleType(name)
    m.__file__ = name+'.py'
    exec(compile(raw, m.__file__, 'exec'), m.__dict__)
    return m


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


@pytest.fixture
def case(tmp_path):
    previous, out = recovery.assemble()
    m = load(out['stranded-recovery.py'], 'recovery_fixture')
    lineage = load(out['suspension-lineage.py'], 'lineage_fixture')
    old_roots = (m.WINDOW, m.HOLD, m.CLOSE)
    roots = tuple(tmp_path/n for n in ('window', 'hold', 'close'))
    for root in roots:
        root.mkdir()
    pins = {}
    for source, pin in m.PINS.items():
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pin
        target = None
        for old, new in zip(old_roots, roots):
            if source.parent == old:
                target = new/source.name
            raw = raw.replace(str(old).encode(), str(new).encode())
        assert target is not None
        target.write_bytes(raw)
        pins[target] = hashlib.sha256(raw).hexdigest()
    m.WINDOW, m.HOLD, m.CLOSE = roots
    m.PINS = pins
    baseline = json.loads((m.WINDOW/'suspension-baseline.json').read_bytes())
    state = json.loads(baseline['raw'])
    state['updated_at'] = '2026-09-28T08:30:20.57979539Z'
    raw = json.dumps(state, indent=2)+'\n'
    assert hashlib.sha256(raw.encode()).hexdigest() == m.ENDPOINT_SHA
    current = dict(raw=raw, pin=dict(sha256=m.ENDPOINT_SHA,
        metadata=dict(m.ENDPOINT_METADATA, atime_ns=1790584220575668043)))

    def read(path, expected):
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected, 'evidence digest drift')
        return data

    def read_equal(a, b):
        a, b = copy.deepcopy(a), copy.deepcopy(b)
        a['pin']['metadata'].pop('atime_ns')
        b['pin']['metadata'].pop('atime_ns')
        return a == b
    w = types.SimpleNamespace(ROOT=m.WINDOW, require=require, read=read,
                              suspension_read_equal=read_equal)
    return m, lineage, w, current, out


def rewrite(case, path, change):
    m = case[0]
    value = json.loads(path.read_bytes())
    change(value)
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    # Synthetic fixture authority changes deliberately to test semantic checks,
    # separately from the production fixed-digest negative.
    m.PINS[path] = hashlib.sha256(raw).hexdigest()


def test_exact_preserved_evidence_accepts_terminal_only(case):
    m, s, w, current, _ = case
    before = {p: p.read_bytes() for p in m.PINS}
    assert m.verify(w, s, current, terminal=True) == current['pin']
    assert before == {p: p.read_bytes() for p in m.PINS}
    with pytest.raises(RuntimeError, match='terminal window'):
        m.verify(w, s, current, terminal=False)


@pytest.mark.parametrize('field', ['inode', 'uid', 'gid', 'mode', 'size', 'mtime_ns', 'ctime_ns'])
def test_endpoint_metadata_drift_refuses(case, field):
    m, s, w, current, _ = case
    current['pin']['metadata'][field] += 1
    with pytest.raises(RuntimeError, match='identity drift'):
        m.verify(w, s, current, terminal=True)


def test_endpoint_bytes_drift_refuses(case):
    m, s, w, current, _ = case
    current['pin']['sha256'] = '0'*64
    with pytest.raises(RuntimeError, match='bytes drift'):
        m.verify(w, s, current, terminal=True)


@pytest.mark.parametrize('name', ['suspension-city-resume-intent.json',
    'suspension-rig-resume-event.json', 'suspension-city-suspend-failure.json',
    'suspension-city-suspend-refused-after.json', 'city-resume-started.json'])
def test_extra_operations_and_fabricated_events_refuse(case, name):
    m, s, w, current, _ = case
    (m.WINDOW/name).write_text('{}')
    with pytest.raises(RuntimeError):
        m.verify(w, s, current, terminal=True)


def test_preserved_digest_changed_refuses(case):
    m, s, w, current, _ = case
    p = m.WINDOW/'rig-resume-phase.json'
    p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(RuntimeError, match='digest drift'):
        m.verify(w, s, current, terminal=True)


@pytest.mark.parametrize('action', ['rig-resume', 'rig-suspend'])
@pytest.mark.parametrize('field', ['exit_code', 'timed_out', 'primary_error', 'cleanup', 'cwd', 'argv'])
def test_both_commands_must_be_exact_and_reaped(case, action, field):
    m, s, w, current, _ = case
    path = (m.WINDOW if action == 'rig-resume' else m.HOLD)/(action+'-phase.json')
    def change(v):
        values = dict(exit_code=1, timed_out=True, primary_error='failure',
                      cwd='/wrong', argv=['/wrong'], cleanup=dict(v['cleanup'], direct_child_reaped=False))
        v[field] = values[field]
    rewrite(case, path, change)
    with pytest.raises(RuntimeError):
        m.verify(w, s, current, terminal=True)


def test_wrong_refusal_and_worker_census_refuse(case):
    m, s, w, current, _ = case
    rewrite(case, m.WINDOW/'suspension-rig-resume-failure.json',
            lambda v: v.update(error='unexplained failure'))
    with pytest.raises(RuntimeError, match='different refusal'):
        m.verify(w, s, current, terminal=True)


@pytest.mark.parametrize('field', ['open_sessions', 'city_tmux_sessions', 'worktree_processes'])
def test_residue_refuses(case, field):
    m, s, w, current, _ = case
    rewrite(case, m.CLOSE/'result.json', lambda v: v.update({field: 1}))
    with pytest.raises(RuntimeError, match='residue proof'):
        m.verify(w, s, current, terminal=True)


def test_no_worker_census_is_required(case):
    m, s, w, current, _ = case
    def change(v):
        census = json.loads(v['stdout'])
        census['sessions'] = [{'id': 'unexpected'}]
        v['stdout'] = json.dumps(census)
    rewrite(case, m.WINDOW/'rig-resume-sessions-0-phase.json', change)
    with pytest.raises(RuntimeError, match='worker existed'):
        m.verify(w, s, current, terminal=True)


def test_deterministic_graph_and_historical_pins(tmp_path):
    previous, out = recovery.assemble()
    assert recovery.assemble() == (previous, out)
    assert previous == successor.assemble()[2]
    assert len(out) == 58
    assert out['stranded-recovery.py'] == (recovery.HERE/'stranded-recovery.py').read_bytes()
    for name in ('WORKER-BRIEF.md', 'worker-startup.py', 'contract.py', 'suspension-lineage.py',
                 'common-snapshot-r1.py', 'read-time-accounting.py'):
        assert out[name] == previous[name]
    for name, raw in out.items():
        if not name.endswith('.sh'):
            continue
        target = tmp_path/Path(name).name
        target.write_bytes(raw)
        assert subprocess.run(['/bin/sh', '-n', str(target)]).returncode == 0
        if Path(name).stem not in ('ADMIT', 'RESTORE', 'TERMINAL'):
            result = subprocess.run(['/bin/sh', str(target)], capture_output=True)
            assert result.returncode == 125
        for script, var in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"', raw.decode()):
            [pin] = re.findall(r'^%s=([0-9a-f]{64})$' % var, raw.decode(), re.M)
            assert pin == hashlib.sha256(out[script]).hexdigest(), (name, script)
    assert ('CLOSE_SHA='+recovery.COMPLETED_CLOSE_SHA).encode() in out['operator/ADMIT.sh']
    assert "recovery-only package cannot preflight stage or resume" in out['window-base-r11.py'].decode()


def test_generated_entrypoint_refuses_new_lifecycle_before_support_calls():
    import ast
    out = recovery.assemble()[1]
    tree = ast.parse(out['window-base-r11.py'])
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    for argv in (['x', 'preflight'], ['x', 'stage'], ['x', 'lifecycle', 'rig-resume']):
        ns = dict(require=require, sys=types.SimpleNamespace(argv=argv))
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<fixture>', 'exec'), ns)
        with pytest.raises(RuntimeError, match='recovery-only'):
            ns['main']()


def test_generated_verified_lifecycle_calls_the_real_recovery(case):
    import ast
    m, s, w, current, out = case
    tree = ast.parse(out['window-base-r11.py'])
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == 'verified_lifecycle')
    def module(path, pin):
        if path.name == 'suspension-lineage.py':
            assert pin == hashlib.sha256(out[path.name]).hexdigest()
            return s
        assert path.name == 'stranded-recovery.py'
        assert pin == hashlib.sha256(out[path.name]).hexdigest()
        return m
    ns = dict(vars(w), module=module, HERE=Path('/fixture-source'),
        LINEAGE_SHA=hashlib.sha256(out['suspension-lineage.py']).hexdigest(),
        load_support=lambda: (None, None, None), suspension_record=lambda _: current,
        types=types)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), '<fixture>', 'exec'), ns)
    assert ns['verified_lifecycle'](terminal=True) == current['pin']
    with pytest.raises(RuntimeError, match='terminal window'):
        ns['verified_lifecycle']()
    ns['ROOT'] = Path('/wrong-window')
    with pytest.raises(RuntimeError, match='terminal window'):
        ns['verified_lifecycle'](terminal=True)


def historical_integrity_fixture(tmp_path, *, corrupt=None):
    """Run the generated historical gate on byte-exact completed OBSERVE data.

    Only the fixture directory name in the binding is translated. No live
    executor, provider, service or write surface is invoked.
    """
    import ast
    out = recovery.assemble()[1]
    tree = ast.parse(out['window-r11.py'])
    selected = [node for node in tree.body if
        isinstance(node, ast.FunctionDef) and node.name == 'integrity_baseline'
        or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
            and t.id in {'INTEGRITY', 'OBSERVER_SHA', 'INSPECTOR_SHA'} for t in node.targets)]
    ns = dict(Path=Path, json=json, stat=__import__('stat'), os=__import__('os'))
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<generated-integrity>', 'exec'), ns)
    original = ns['INTEGRITY']
    root = tmp_path/'integrity'
    root.mkdir(mode=0o700)
    files = ('intent.json', 'result.json', 'preservation.json', 'observed-after.json')
    for name in files:
        (root/name).write_bytes((original/name).read_bytes())
    binding = json.loads(Path('/var/tmp/ga-e0t1.20-window-20260928-r3/integrity-binding.json').read_bytes())
    assert binding['root'] == str(original)
    assert binding['observer_sha256'] == '091457e1027f2115b5321f894278fcbe3d8dc57639f871f0d9486ffc243651ed'
    binding['root'] = str(root)
    if corrupt == 'executor':
        value = json.loads((root/'intent.json').read_bytes())
        value['executor_sha256'] = '0'*64
        (root/'intent.json').write_text(json.dumps(value))
    elif corrupt == 'binding':
        binding['observed_after_sha256'] = '0'*64
    ns['INTEGRITY'] = root
    ns['w'] = types.SimpleNamespace(require=require, ROOT=tmp_path/'window',
        read=lambda p: p.read_bytes(), record=lambda name: binding,
        digest=lambda raw: hashlib.sha256(raw).hexdigest())
    return ns, json.loads((root/'observed-after.json').read_bytes()), out


def test_completed_observe_identity_survives_recovery_admission(tmp_path):
    ns, expected, out = historical_integrity_fixture(tmp_path)
    assert ns['integrity_baseline'](False) == expected
    # This must remain the actual completed observer, not regenerated code.
    assert ns['OBSERVER_SHA'] != hashlib.sha256(out['observe-integrity-r11.py']).hexdigest()


@pytest.mark.parametrize('corrupt,reason', [('executor', 'integrity executor'),
    ('binding', 'integrity baseline changed')])
def test_historical_observe_drift_still_refuses(tmp_path, corrupt, reason):
    ns, _, _ = historical_integrity_fixture(tmp_path, corrupt=corrupt)
    with pytest.raises(RuntimeError, match=reason):
        ns['integrity_baseline'](False)
