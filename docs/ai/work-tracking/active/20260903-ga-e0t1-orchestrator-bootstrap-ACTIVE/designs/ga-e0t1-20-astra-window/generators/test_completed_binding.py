"""Execute generated receipt validation on the preserved completed BIND.

Reads historical evidence only. Package main, gc, providers and jobs never run.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types

import pytest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('binding_builder', HERE/'build.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
ROOT = Path('/var/tmp/ga-e0t1.20-bind-20260927-r1')
EXECUTOR = '9fd6c49adecf7fb991f9b8cd2c6279c25fcf73455bfa0911609a2079928495e7'
PINS = {
    'binding-intent.json': '0f85dbaa6de8c174c3bc4950955777bb23621cb3bc8bd55ce9546c5e029e4b37',
    'result.json': '0e8003f3fa54558537cd93dcd2863ab5bcd0aef8be8af1ec11c198472ad022d2',
    'task-after.json': 'e58d90d46f6422aeb6d65a135daf41389fb5d1b9e0115f1019f6b2027abf7dcb',
}


def module(raw):
    m = types.ModuleType('route_fixture'); m.__file__ = 'route_fixture.py'
    exec(compile(raw, m.__file__, 'exec'), m.__dict__)
    return m


def invoke(m, records):
    def read(path, pin=None):
        raw = records[path.name]
        if pin is not None:
            assert hashlib.sha256(raw).hexdigest() == pin, 'bound receipt digest'
        return raw
    w = types.SimpleNamespace(read=read)
    if hasattr(m, 'completed_binding'):
        return m.completed_binding(w)
    # Exact historical block, not a reimplementation of the old assertion.
    source = b.git('show', '96160355321144a7bc3626962aa13bcd727c12b4:'+b.NEW+'/route-task-r5.py')
    main = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    start = next(i for i,n in enumerate(main.body) if ast.unparse(n) == 's = BIND.lstat()')
    end = next(i for i,n in enumerate(main.body) if ast.unparse(n).startswith('w.read(w.CITY'))
    fn = ast.FunctionDef(name='historical_binding', args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='w')],kwonlyargs=[],kw_defaults=[],defaults=[]),
        body=main.body[start:end]+[ast.Return(value=ast.Name(id='bound',ctx=ast.Load()))], decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])), 'historical_block', 'exec'), m.__dict__)
    return m.historical_binding(w)


@pytest.fixture(scope='module')
def records():
    result = {name:(ROOT/name).read_bytes() for name in PINS}
    assert {name:hashlib.sha256(raw).hexdigest() for name,raw in result.items()} == PINS
    return result


@pytest.fixture(scope='module')
def built():
    out = b.assemble(final=True)[1]
    return out, module(out['route-task-r5.py'])


def test_previous_signed_route_reproduces_completed_executor_refusal(records):
    old = module(b.git('show', '96160355321144a7bc3626962aa13bcd727c12b4:'+b.NEW+'/route-task-r5.py'))
    assert old.BIND_SHA != EXECUTOR
    with pytest.raises(AssertionError): invoke(old, records)


def test_current_route_accepts_exact_completed_binding(records,built):
    out,m = built
    assert invoke(m,records) == json.loads(records['task-after.json'])
    assert m.BIND_SHA == EXECUTOR
    assert hashlib.sha256(out['bind-task-r5.py']).hexdigest() != EXECUTOR


@pytest.mark.parametrize('name',list(PINS))
def test_any_completed_receipt_byte_change_refuses(name,records,built):
    changed = dict(records); changed[name] += b' '
    with pytest.raises(AssertionError,match='bound receipt digest'): invoke(built[1],changed)


def test_parent_audit_append_does_not_change_bound_task_authority(records,built):
    m = built[1]; old=json.loads(records['task-after.json']); current=copy.deepcopy(old)
    current['dependencies'][0]['notes'] += '\nPreserved audit outcome'
    current['dependencies'][0]['updated_at'] = '2026-09-28T00:00:00Z'
    m.continued_task(current,old)


@pytest.mark.parametrize('field',['metadata','notes','description','status','assignee','updated_at','unknown'])
def test_any_own_task_drift_refuses(field,records,built):
    old=json.loads(records['task-after.json']); current=copy.deepcopy(old)
    current[field]='changed'
    with pytest.raises(AssertionError): built[1].continued_task(current,old)


@pytest.mark.parametrize('field',['id','dependency_type','status','metadata','title','unknown'])
def test_non_audit_parent_drift_refuses(field,records,built):
    old=json.loads(records['task-after.json']); current=copy.deepcopy(old)
    current['dependencies'][0][field]='changed'
    with pytest.raises(AssertionError): built[1].continued_task(current,old)


def test_parent_audit_erasure_refuses(records,built):
    old=json.loads(records['task-after.json']); current=copy.deepcopy(old)
    current['dependencies'][0]['notes']='replacement'
    with pytest.raises(AssertionError): built[1].continued_task(current,old)


@pytest.mark.parametrize('stamp',['2000-01-01T00:00:00Z','2026-09-28T00:00:00','invalid'])
def test_parent_audit_time_refuses(stamp,records,built):
    old=json.loads(records['task-after.json']); current=copy.deepcopy(old)
    current['dependencies'][0]['updated_at']=stamp
    with pytest.raises((AssertionError,ValueError)): built[1].continued_task(current,old)
