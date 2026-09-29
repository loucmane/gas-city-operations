"""Offline replay of the precise route-comparator failure and bounded correction.
No gc, systemd, worker, signing or production write occurs in these tests.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import types

import pytest

HERE=Path(__file__).parent
OLD=HERE.parent/'ga-rq5n-c1-package'

def load(raw,name,path=HERE):
    m=types.ModuleType(name);m.__file__=str(path/(name+'.py'))
    exec(compile(raw,m.__file__,'exec',dont_inherit=True),m.__dict__)
    return m

a=load((HERE/'assemble.py').read_bytes(),'assembler')
c=load((OLD/'contract.py').read_bytes(),'contract')
PARAMS=dict(observation='/tmp/ga-rq5n-readonly-baseline-20260929-r3/observed.json',
            observation_sha='a'*64,cache_ns=1790698733306040648)

@pytest.fixture(scope='module')
def built():
    return a.assemble(**PARAMS)

@pytest.fixture
def pair():
    # Genuine completed BIND evidence, read-only, unchanged by this fixture.
    bound=json.loads(Path('/var/tmp/ga-rq5n-bind-20260929-r1/task-after.json').read_bytes())
    current=copy.deepcopy(bound)
    d=json.loads((HERE/'held-predecessor-disposition.json').read_bytes())
    [row]=[r for r in current['dependencies'] if r['id']=='ga-9olv']
    assert row==d['before_projection']
    row.clear();row.update(copy.deepcopy(d['after_projection']))
    return current,bound

def runtime(built, disposition=None):
    files=dict(built[1])
    route=load(files['route-task.py'],'route')
    if disposition is not None:
        files['held-predecessor-disposition.json']=json.dumps(disposition).encode()
        # Test semantic rejection separately after passing an explicitly
        # fixture-bound digest. Production digest remains fixed and is tested.
        route.DISPOSITION_SHA=hashlib.sha256(files['held-predecessor-disposition.json']).hexdigest()
    def read(path,pin):
        raw=files[path.name]
        assert hashlib.sha256(raw).hexdigest()==pin
        return raw
    def module(path,pin):
        return load(read(path,pin),'admission')
    w=types.SimpleNamespace(read=read,module=module,contract=lambda:c)
    return route,w

def test_real_r1_route_refuses_two_edges_before_any_route(pair):
    current,bound=pair
    old=load((OLD/'route-task.py').read_bytes(),'old_route')
    with pytest.raises(AssertionError):
        old.continued_task(bound,bound)

def test_exact_supported_disposition_and_real_r2_route_pass(built,pair):
    current,bound=pair
    original=copy.deepcopy(bound)
    route,w=runtime(built)
    route.continued_task(current,bound,w)
    assert bound==original  # historical receipt never rewritten
    tree=ast.parse(built[1]['route-task.py'])
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    calls=[n for n in ast.walk(main) if isinstance(n,ast.Call)
           and isinstance(n.func,ast.Name) and n.func.id=='continued_task']
    assert len(calls)==1 and [n.id for n in calls[0].args]==['before','bound','w']

@pytest.mark.parametrize('kind',['reordered','parent-audit'])
def test_only_previously_allowed_parent_audit_and_set_order_pass(built,pair,kind):
    current,bound=pair
    if kind=='reordered':
        current['dependencies'].reverse()
    else:
        [parent]=[r for r in current['dependencies'] if r['id']=='ga-e0t1']
        parent['notes']+='\nAppend-only audit fixture'
        parent['updated_at']='2026-09-29T20:00:00Z'
    route,w=runtime(built)
    route.continued_task(current,bound,w)

@pytest.mark.parametrize('kind',[
    'held-open','held-closed','held-notes','held-metadata','held-time','held-title',
    'own-title','own-notes','own-metadata','own-time','missing','duplicate','extra',
    'blocking-edge','parent-erasure','parent-backwards','parent-status'])
def test_unreviewed_drift_refuses(built,pair,kind):
    current,bound=pair
    [held]=[r for r in current['dependencies'] if r['id']=='ga-9olv']
    [parent]=[r for r in current['dependencies'] if r['id']=='ga-e0t1']
    if kind=='held-open':held['status']='open'
    elif kind=='held-closed':held['status']='closed'
    elif kind=='held-notes':held['notes']+='not admitted'
    elif kind=='held-metadata':held['metadata']={'changed':True}
    elif kind=='held-time':held['updated_at']='2026-09-30T01:00:00Z'
    elif kind=='held-title':held['title']='changed'
    elif kind=='own-title':current['title']='changed'
    elif kind=='own-notes':current['notes']+='changed'
    elif kind=='own-metadata':current['metadata']['unexpected']='changed'
    elif kind=='own-time':current['updated_at']='2026-09-30T01:00:00Z'
    elif kind=='missing':current['dependencies'].pop()
    elif kind=='duplicate':current['dependencies']=[parent,parent]
    elif kind=='extra':current['dependencies'].append(copy.deepcopy(held))
    elif kind=='blocking-edge':held['dependency_type']='blocks'
    elif kind=='parent-erasure':parent['notes']='erased'
    elif kind=='parent-backwards':parent['updated_at']='2020-01-01T00:00:00Z'
    elif kind=='parent-status':parent['status']='closed'
    route,w=runtime(built)
    with pytest.raises((AssertionError,RuntimeError,ValueError)):
        route.continued_task(current,bound,w)

@pytest.mark.parametrize('kind',['extra-field','allow-notes','pass','closed','preimage','backwards'])
def test_disposition_semantics_refuse_even_with_fixture_rebound_digest(built,pair,kind):
    current,bound=pair
    d=json.loads(built[1]['held-predecessor-disposition.json'])
    if kind=='extra-field':d['extra']=True
    elif kind=='allow-notes':d['allowed_fields'].append('notes')
    elif kind=='pass':d['pass_closeout']=True
    elif kind=='closed':d['after_projection']['status']='closed'
    elif kind=='preimage':
        d['before_projection']['title']='changed'
        d['after_projection']['title']='changed'
    elif kind=='backwards':d['after_projection']['updated_at']='2020-01-01T00:00:00Z'
    route,w=runtime(built,d)
    with pytest.raises((AssertionError,RuntimeError,ValueError)):
        route.continued_task(current,bound,w)

def test_disposition_digest_refuses(built,pair):
    route,w=runtime(built)
    route.DISPOSITION_SHA='0'*64
    with pytest.raises(AssertionError):
        route.continued_task(*pair,w)

def test_assembly_exact_inputs_no_completed_operation_replay(built):
    before,out=built
    assert len(out)==65 and a.assemble(**PARAMS)==built
    assert sum(n.startswith('operator/') for n in out)==28
    assert not {'bind-task.py','operator/BIND.sh','operator/PREP.sh','operator/WORKTREE.sh'} & set(out)
    assert all(out[n]==before[n] for n in a.LOCAL)
    route=load(out['route-task.py'],'route')
    assert str(route.BIND)=='/var/tmp/ga-rq5n-bind-20260929-r1'
    assert route.BIND_SHA=='3ed6c04c0e1647bdbd7cd47512bf5ffdb04cafda23267c184bc87fec6532faec'
    assert str(route.ROOT)=='/var/tmp/ga-rq5n-route-20260929-r2'
    assert route.ADMISSION_SHA==a.sha(before['fresh-admission.py'])
    for name,raw in out.items():
        if name.endswith('.py'):ast.parse(raw,filename=name)
        if name not in a.LOCAL:
            assert b'/var/tmp/ga-rq5n-window-20260929-r1' not in raw
            assert b'/var/tmp/ga-rq5n-route-20260929-r1' not in raw
    helper=a.load((OLD/'window-assembly.py').read_bytes(),'rebinder',OLD/'window-assembly.py')
    assert helper.rebind(out,before,{},a.LOCAL|{'held-predecessor-disposition.json'})==out

@pytest.mark.parametrize('key,value',[
    ('observation','/tmp/ga-rq5n-readonly-baseline-20260929-r2/observed.json'),
    ('observation_sha','bad'),('cache_ns',False),('cache_ns',0)])
def test_exact_fresh_input_pins_required(key,value):
    with pytest.raises(ValueError):a.assemble(**dict(PARAMS,**{key:value}))

def test_old_queue_gate_unchanged_after_root_and_digest_rebinding(built):
    before,out=built
    helper=a.load((OLD/'window-assembly.py').read_bytes(),'rebinder',OLD/'window-assembly.py')
    raw=a.retarget(before['audit-queue-r3.py'].decode()).encode()
    check=helper.rebind(dict(out,**{'audit-queue-r3.py':raw}),before,{},a.LOCAL|{'held-predecessor-disposition.json'})
    assert check['audit-queue-r3.py']==out['audit-queue-r3.py']

def halt_fixture(tmp_path, defect=None):
    source=(HERE/'preserve-halt.py').read_text()
    tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.If)
              and ast.unparse(n.test)=='EXPECTED_EXIT == 1')
    evidence=Path('/tmp/ga-rq5n-prestage-stop-20260929-r1/prestage-disposition.json').read_bytes()
    files={
      '/tmp/ga-rq5n-prestage-stop-20260929-r1/prestage-disposition.json':evidence,
      '/home/loucmane/gascity/city/city.toml':b'city baseline',
      '/var/tmp/ga-rq5n-window-20260929-r1/city.before.toml':b'city baseline',
      '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json':b'receipt baseline',
      '/var/tmp/ga-rq5n-window-20260929-r1/receipt.before.json':b'receipt baseline',
    }
    halt='babb489e079572081261a95d8086886b66602a477e3d8e4319c9ecac903f95c4'
    done='2de86612ca1d637e0508606d075abe21a1d7a32c12e2a6a977dbc8c7d60a128a'
    if defect=='halt':halt='0'*64
    elif defect=='done':done='0'*64
    elif defect=='evidence':files[next(iter(files))]=b'changed'
    elif defect=='city':files['/home/loucmane/gascity/city/city.toml']=b'changed'
    elif defect=='receipt':files['/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json']=b'changed'
    class FakePath:
        def __init__(self,path):self.path=str(path)
        def __truediv__(self,name):return FakePath(self.path+'/'+name)
        def read_bytes(self):return files[self.path]
    os=types.SimpleNamespace(path=types.SimpleNamespace(
        lexists=lambda p: p.path.endswith(defect) if defect in (
            'stage-consumed.json','stage-pass.json','rig-resume-started.json') else False))
    ns=dict(EXPECTED_EXIT=1,halt_sha=halt,done_sha=done,hashlib=hashlib,json=json,Path=FakePath,os=os)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'halt_adjudication','exec'),ns)
    return ns

def test_failed_halt_disposition_exact_proof_passes(tmp_path):
    assert halt_fixture(tmp_path)['disposition']['ok']

@pytest.mark.parametrize('defect',['halt','done','evidence','city','receipt',
    'stage-consumed.json','stage-pass.json','rig-resume-started.json'])
def test_failed_halt_disposition_refuses_drift(tmp_path,defect):
    with pytest.raises(AssertionError):halt_fixture(tmp_path,defect)
