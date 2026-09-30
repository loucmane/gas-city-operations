"""Offline r4 recovery tests. All mutations are disposable fixtures only."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import types

import pytest
import recovery_r4 as recovery


def load(raw, name):
    mod = types.ModuleType(name)
    mod.__file__ = name+'.py'
    exec(compile(raw, mod.__file__, 'exec'), mod.__dict__)
    return mod


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


@pytest.fixture
def case(tmp_path):
    previous, out = recovery.assemble()
    m = load(out[recovery.VERIFIER], 'r4_recovery_fixture')
    lineage = load(out['suspension-lineage.py'], 'r4_lineage_fixture')
    old_roots = (m.WINDOW, m.HOLD, m.CLOSE, m.WATCH)
    roots = tuple(tmp_path/n for n in ('window', 'hold', 'close', 'watch'))
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
    m.WINDOW, m.HOLD, m.CLOSE, m.WATCH = roots
    m.RELEASE = tmp_path/'release'
    m.PINS = pins
    baseline = json.loads((m.WINDOW/'suspension-baseline.json').read_bytes())
    state = json.loads(baseline['raw'])
    state['updated_at'] = '2026-09-28T10:56:23.657621074Z'
    raw = json.dumps(state, indent=2)+'\n'
    assert hashlib.sha256(raw.encode()).hexdigest() == m.ENDPOINT_SHA
    current = dict(raw=raw, pin=dict(sha256=m.ENDPOINT_SHA,
        metadata=dict(m.ENDPOINT_METADATA, atime_ns=1790592983706013453)))

    def read(path, expected):
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, 'evidence digest drift')
        return raw

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
    # Fixture-only digest updates exercise semantics separately from pinned-byte refusal.
    m.PINS[path] = hashlib.sha256(raw).hexdigest()


def test_exact_chain_is_terminal_only_and_read_only(case):
    m, s, w, current, _ = case
    before = {p: p.read_bytes() for p in m.PINS}
    assert m.verify(w, s, current, terminal=True) == current['pin']
    assert before == {p: p.read_bytes() for p in m.PINS}
    with pytest.raises(RuntimeError, match='terminal window'):
        m.verify(w, s, current, terminal=False)


@pytest.mark.parametrize('field', ['device','inode','uid','gid','mode','size','nlink',
                                   'type','mtime_ns','ctime_ns'])
def test_endpoint_identity_drift_refuses(case, field):
    m, s, w, current, _ = case
    current['pin']['metadata'][field] += 1
    with pytest.raises(RuntimeError, match='identity drift'):
        m.verify(w, s, current, terminal=True)


def test_endpoint_bytes_drift_refuses(case):
    m, s, w, current, _ = case
    current['pin']['sha256'] = '0'*64
    with pytest.raises(RuntimeError, match='bytes drift'):
        m.verify(w, s, current, terminal=True)


@pytest.mark.parametrize('name', ['suspension-rig-suspend-intent.json',
    'suspension-city-suspend-event.json', 'suspension-rig-resume-failure.json',
    'suspension-rig-resume-refused-after.json', 'rig-suspend-started.json'])
def test_extra_operation_or_fabricated_success_refuses(case, name):
    m, s, w, current, _ = case
    (m.WINDOW/name).write_text('{}')
    with pytest.raises(RuntimeError):
        m.verify(w, s, current, terminal=True)


def test_release_directory_even_empty_or_symlink_refuses(case):
    m, s, w, current, _ = case
    m.RELEASE.symlink_to('/nonexistent-fixture-target')
    with pytest.raises(RuntimeError, match='unconsumed'):
        m.verify(w, s, current, terminal=True)


def test_preserved_bytes_cannot_change(case):
    m, s, w, current, _ = case
    path = m.WINDOW/'city-suspend-phase.json'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(RuntimeError, match='digest drift'):
        m.verify(w, s, current, terminal=True)


@pytest.mark.parametrize('action', ['rig-resume','city-resume','city-suspend','rig-suspend'])
@pytest.mark.parametrize('field', ['exit_code','timed_out','primary_error','cleanup','cwd','argv'])
def test_every_applied_command_is_exact_successful_and_reaped(case, action, field):
    m, s, w, current, _ = case
    root = m.HOLD if action == 'rig-suspend' else m.WINDOW
    path = root/(action+'-phase.json')
    def change(v):
        v[field] = dict(exit_code=1, timed_out=True, primary_error='failure',
            cwd='/wrong', argv=['/wrong'],
            cleanup=dict(v['cleanup'], direct_child_reaped=False))[field]
    rewrite(case, path, change)
    # Keep mirrored fixture phase in event equal, so the real phase verifier is exercised.
    if action in ('rig-resume','city-resume'):
        result = json.loads(path.read_bytes())
        rewrite(case, root/('suspension-'+action+'-event.json'),
                lambda v: v.update(result=result))
    with pytest.raises(RuntimeError):
        m.verify(w, s, current, terminal=True)


@pytest.mark.parametrize('field', ['open_sessions','city_tmux_sessions','worktree_processes'])
def test_close_residue_refuses(case, field):
    m, s, w, current, _ = case
    rewrite(case, m.CLOSE/'result.json', lambda v: v.update({field:1}))
    with pytest.raises(RuntimeError, match='residue proof'):
        m.verify(w, s, current, terminal=True)


@pytest.mark.parametrize('target', ['refusal','census','worker','hold'])
def test_different_failure_or_history_refuses(case, target):
    m, s, w, current, _ = case
    if target == 'refusal':
        rewrite(case,m.WINDOW/'suspension-city-suspend-failure.json',
                lambda v:v.update(error='unexplained'))
    elif target == 'census':
        def change(v):
            census=json.loads(v['stdout']);census['sessions']=[{'id':'extra'}]
            v['stdout']=json.dumps(census)
        rewrite(case,m.WINDOW/'city-suspend-sessions-0-phase.json',change)
    elif target == 'worker':
        rewrite(case,m.WATCH/'result.json',lambda v:v['live_sessions'][0].update(id='other'))
    else:
        rewrite(case,m.HOLD/'attempts.json',lambda v:v.update({'city-suspend':0}))
    with pytest.raises(RuntimeError):
        m.verify(w,s,current,terminal=True)


def test_generated_package_is_deterministic_and_restore_only(tmp_path):
    previous,out=recovery.assemble()
    assert recovery.assemble()==(previous,out)
    assert len(out)==59
    for name in ('WORKER-BRIEF.md','worker-startup.py','contract.py','suspension-lineage.py',
                 'common-snapshot-r1.py','read-time-accounting.py','stranded-recovery.py'):
        assert out[name]==previous[name]
    assert out[recovery.VERIFIER]==(recovery.HERE/recovery.VERIFIER).read_bytes()
    for name,raw in out.items():
        if not name.endswith('.sh'):
            continue
        path=tmp_path/Path(name).name
        path.write_bytes(raw)
        assert subprocess.run(['/bin/sh','-n',str(path)]).returncode==0
        if name not in recovery.WRAPPERS:
            assert subprocess.run(['/bin/sh',str(path)],capture_output=True).returncode==125
        for script,var in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"',raw.decode()):
            [pin]=re.findall(r'^%s=([0-9a-f]{64})$'%var,raw.decode(),re.M)
            assert pin==hashlib.sha256(out[script]).hexdigest(),(name,script)
    assert ('CLOSE_SHA='+recovery.COMPLETED_CLOSE_SHA).encode() in out['operator/ADMIT.sh']
    assert ("OBSERVER_SHA='"+recovery.COMPLETED_OBSERVER_SHA+"'").encode() in out['window-r11.py']
    assert 'worker_started_in_window=True,source_release_sent=False,open_sessions=0' in out['observe-terminal-r11.py'].decode()


@pytest.mark.parametrize('args',[['preflight'],['stage'],['lifecycle','rig-resume'],['inner','apply','1']])
def test_generated_entry_refuses_new_mutation_before_support(args):
    tree=ast.parse(recovery.assemble()[1]['window-base-r11.py'])
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    ns=dict(require=require,sys=types.SimpleNamespace(argv=['x']+args))
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<fixture>','exec'),ns)
    with pytest.raises(RuntimeError,match='recovery-only'):
        ns['main']()


def test_generated_wiring_calls_actual_terminal_verifier(case):
    m,s,w,current,out=case
    tree=ast.parse(out['window-base-r11.py'])
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verified_lifecycle')
    def module(path,pin):
        assert pin==hashlib.sha256(out[path.name]).hexdigest()
        return s if path.name=='suspension-lineage.py' else m
    ns=dict(vars(w),module=module,HERE=Path('/fixture-source'),
        LINEAGE_SHA=hashlib.sha256(out['suspension-lineage.py']).hexdigest(),
        load_support=lambda:(None,None,None),suspension_record=lambda _:current,types=types)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<fixture>','exec'),ns)
    assert ns['verified_lifecycle'](terminal=True)==current['pin']
    with pytest.raises(RuntimeError,match='terminal window'):
        ns['verified_lifecycle']()
