"""Execute both real generated provider guards against the pinned M12 fixture.

No provider calls or live mutations. Read/path observation is mocked. The old
signed candidate is compiled as data to preserve the exact refusal regression.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types

import pytest

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('build',HERE/'build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
PIN='114b4a000471ee145d494732db361521ea237b3e4857607b06720b7b105327b9'
PREVIOUS='3c9931721fc8cdd204c8d7debd0c47c739064ccd'


def invoke(raw,providers,monkeypatch,*,bad_digest=False,bad_mode=False,bad_resolution=False):
    m=types.ModuleType('provider_fixture');m.__file__='fixture.py'
    exec(compile(raw,m.__file__,'exec',dont_inherit=True),m.__dict__)
    assert m.MANIFEST_SHA==PIN
    def require(ok,reason):
        if not ok:raise RuntimeError(reason)
    reads=[]
    def read(path,pin):
        assert str(path)=='/home/loucmane/gascity/city/.gc/platform/install-manifest.json'
        assert pin==PIN
        return json.dumps(dict(integrity=dict(providers=providers))).encode()
    def read_file(path):
        reads.append(path)
        p=next(p for p in providers if p['resolved_path']==path)
        return dict(sha256='0'*64 if bad_digest else p['sha256'],
            metadata=dict(uid=1000,gid=1000,mode=0o777 if bad_mode else 0o755)),None
    def resolve(path,strict=False):
        assert strict
        return Path('/wrong') if bad_resolution else Path(next(p['resolved_path'] for p in providers if p['path']==str(path)))
    monkeypatch.setattr(m.Path,'resolve',resolve)
    m.provider_pins(types.SimpleNamespace(read=read,require=require),types.SimpleNamespace(read_file=read_file))
    return reads


@pytest.fixture(scope='module')
def assembled():return b.assemble(final=True)[1]


@pytest.mark.parametrize('name',['observe-integrity-r11.py','observe-terminal-r11.py'])
def test_previous_signed_guard_reproduces_m12_inventory_refusal(name,monkeypatch):
    old=b.git('show',PREVIOUS+':'+b.NEW+'/'+name)
    with pytest.raises(RuntimeError,match='provider inventory'):
        invoke(old,json.loads((HERE/'providers-m12.json').read_bytes()),monkeypatch)


@pytest.mark.parametrize('name',['observe-integrity-r11.py','observe-terminal-r11.py'])
def test_current_m12_inventory_passes_both_guards(name,assembled,monkeypatch):
    providers=json.loads((HERE/'providers-m12.json').read_bytes())
    assert invoke(assembled[name],providers,monkeypatch)==[p['resolved_path'] for p in providers]


@pytest.mark.parametrize('name',['observe-integrity-r11.py','observe-terminal-r11.py'])
@pytest.mark.parametrize('change',['missing','extra','reorder','name','path','hash','args','bytes','mode','resolution'])
def test_m12_drift_still_refuses(name,change,assembled,monkeypatch):
    p=json.loads((HERE/'providers-m12.json').read_bytes())
    if change=='missing':p.pop()
    if change=='extra':p.append(copy.deepcopy(p[-1]))
    if change=='reorder':p[3],p[4]=p[4],p[3]
    if change=='name':p[4]['name']='foreign'
    if change=='path':p[4]['path']='/wrong'
    if change=='hash':p[4]['sha256']='0'*64
    if change=='args':p[4]['version_args']=['--launch']
    with pytest.raises(RuntimeError):
        invoke(assembled[name],p,monkeypatch,bad_digest=change=='bytes',bad_mode=change=='mode',bad_resolution=change=='resolution')


def test_successor_keeps_completed_binding_and_uses_fresh_observation_root(assembled):
    assert b'/var/tmp/ga-e0t1.20-bind-20260927-r1' in assembled['bind-task-r5.py']
    for name in ('observe-integrity-r11.py','operator/OBSERVE.sh','window-r11.py'):
        assert b'/var/tmp/ga-e0t1.20-integrity-20260928-r4' in assembled[name]
        assert b'/var/tmp/ga-e0t1.20-integrity-20260927-r1' not in assembled[name]
    # The task's already-recorded note still matches: no second bind is needed.
    current=types.ModuleType('current_contract');previous=types.ModuleType('prior_contract')
    exec(compile(assembled['contract.py'],'current_contract','exec'),current.__dict__)
    exec(compile(b.git('show',PREVIOUS+':'+b.NEW+'/contract.py'),'prior_contract','exec'),previous.__dict__)
    assert current.BOUND_NOTE==previous.BOUND_NOTE
