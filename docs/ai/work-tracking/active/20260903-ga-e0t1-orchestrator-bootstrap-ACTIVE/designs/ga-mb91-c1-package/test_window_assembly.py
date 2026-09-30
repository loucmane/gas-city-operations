"""Complete package fixture proof, not worker or live-window acceptance.

Assembly is in memory. The queue audit executes against a fake control plane;
wrappers receive syntax checks only. No production operation is invoked.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import types

import pytest

HERE = Path(__file__).parent


def load(raw, name):
    m = types.ModuleType(name)
    m.__file__ = str(HERE / (name+'.py'))
    exec(compile(raw, m.__file__, 'exec'), m.__dict__)
    return m


a = load((HERE/'window-assembly.py').read_bytes(), 'window_assembly')
c = load((HERE/'contract.py').read_bytes(), 'window_contract')
PARAMS = dict(observation='/tmp/ga-mb91-readonly-baseline-20260930-r1/observed.json',
              observation_sha='a'*64, cache_ns=1790649221451394669)


@pytest.fixture(scope='module')
def built():
    return a.assemble(**PARAMS)


def test_deterministic_complete_subset_and_immutable_inputs(built):
    before, out = built
    assert a.assemble(**PARAMS) == built
    assert len(out) == 68
    assert {n for n in out if n.startswith('operator/')} == {
        'operator/'+n+'.sh' for n in a.WRAPPERS}
    assert not any(n in out for n in ('operator/WORKTREE.sh', 'operator/PREP.sh'))
    assert all(out[n] == (HERE/n).read_bytes() for n in a.LOCAL)
    for name, raw in out.items():
        if name.endswith('.py'):
            ast.parse(raw, filename=name)
    assert a.rebind(out, before, a.read_inputs()[1], set(a.LOCAL)) == out


def test_no_stale_source_dependencies_or_consumed_task_operations(built):
    before, out = built
    changed = {a.sha(raw) for name, raw in before.items()
               if a.RENAMES.get(name, name) in out and raw != out[a.RENAMES.get(name, name)]}
    changed.update(a.read_inputs()[1].values())
    current = {a.sha(raw) for raw in out.values()}
    for name, raw in out.items():
        if name not in a.LOCAL:
            refs = {m['digest'] or m['shell'] for m in a.HEX.finditer(raw.decode())}
            assert not (refs & (changed-current)), name
        if name == 'window-base.py':
            assert raw.count(b'/var/tmp/ga-jcxb-') == 2
            assert b"closed['closed_session']=='ci-mzoxg'" in raw  # exact completed-session predecessor
        else:
            assert b'ga-e0t1.20' not in raw, name
        assert b'c6b789bbe6ff677dd04336803dbf2c2e017812ba' not in raw, name
        assert b'COMPLETED OPERATION' not in raw, name
    assert b'/var/tmp/ga-mb91-route-20260930-r1' in out['route-task.py']
    assert b"ROUTE/'task-after.json'" in out['startup-release.py']
    assert b'/var/tmp/ga-mb91-route-20260930-r1/task-after.json' in out['close-r11.py']


def test_exact_preparation_and_dynamic_hook_order(built):
    _, out = built
    base = load(out['window-base.py'], 'generated_base')
    prep = a.read_inputs()[3]
    assert str(base.PREP) == str(a.PREP)
    assert base.BASE == c.BASE and str(base.WORK) == c.WORK
    assert base.CITY_SHA[1] == prep['city_after_sha256']
    assert base.RECEIPT_SHA[1] == prep['receipt_after_sha256']
    assert base.REVISION[1] == prep['revision_after']
    assert base.CACHE_PREV_NS == base.CACHE_PINNED_NS == PARAMS['cache_ns']
    assert str(base.ACCEPTED) == PARAMS['observation']
    assert base.ACCEPTED_SHA == PARAMS['observation_sha']
    assert b'probe.verified_hook()' not in out['window-base.py']
    assert b'probe.verified_hook()' in out['startup-release.py']
    assert b'verified_hook()' in out['worker-startup.py']
    assert b'claim-store-branch' in out['window-base.py']
    assert b'validator.CLAIM_BRANCH' in out['window-base.py']


@pytest.mark.parametrize('name', ['common-snapshot-r1.py', 'cache-atime-policy-r1.py',
    'runtime-process-r7.py',
    'route-chain-r1.py', 'read-time-accounting.py', 'suspension-lineage.py'])
def test_inherited_safety_body_unchanged_after_only_identity_and_digest_rebinding(built, name):
    before, out = built
    # Same transform with the complete settled digest graph must reproduce the
    # inherited module byte for byte. No independently rewritten safety logic.
    rebound = a.retarget(before[name].decode())
    if name == 'route-chain-r1.py':
        rebound = rebound.replace('2800348', '466463').replace('229642910742', '517633096016')
    temporary = dict(out, **{name: rebound.encode()})
    actual = a.rebind(temporary, before, a.read_inputs()[1], set(a.LOCAL))
    assert actual[name] == out[name]
    if name == 'common-snapshot-r1.py':
        old = load(before[name], 'old_common')
        new = load(out[name], 'new_common')
        assert len(old.CONFIG_EXCEPTIONS) == 44
        assert new.CONFIG_EXCEPTIONS == old.CONFIG_EXCEPTIONS


@pytest.mark.parametrize('key,value', [('observation','/tmp/old/observed.json'),
    ('observation_sha','broken'), ('cache_ns',None), ('cache_ns',False), ('cache_ns',0)])
def test_missing_exact_baseline_refuses(key, value):
    with pytest.raises(ValueError):
        a.assemble(**dict(PARAMS, **{key:value}))


def test_wrapper_shell_syntax_only_in_disposable_fixture(built, tmp_path):
    for name, raw in built[1].items():
        if name.endswith('.sh'):
            path = tmp_path/Path(name).name
            path.write_bytes(raw)
            result = subprocess.run(['/bin/bash','-n',str(path)], capture_output=True)
            assert result.returncode == 0, (name,result.stderr)
    assert b'audit-stage' in built[1]['operator/STAGE.sh']


def queue_fixture(built, tmp_path, mode, defect=None):
    task = copy.deepcopy(c.BASELINE)
    task['metadata'] = {'gc.work_dir': c.WORK}
    task['notes'] = c.BOUND_NOTE
    if mode != 'stage':task['metadata']['gc.routed_to'] = c.TARGET
    if defect == 'own-fields':task['title'] = 'changed'
    calls = []
    def run(name,args):
        calls.append((name,args))
        if name == 'exact-task':return [task]
        if name == 'fresh-native-ready':
            if defect=='not-native-ready':return []
            if defect=='duplicate-native-ready':return [task,task]
            return [task,dict(id='ga-unrouted-ready')]
        if name == 'live-sessions':return dict(ok=True,sessions=[])
        if name == 'city-status':return dict(suspended=True,summary=dict(running_agents=0),
            rigs=[dict(name=n,suspended=not(mode=='resume' and n=='gascity'))
                  for n in ('gascity','hpfetcher','blog','gas-city-template')])
        if name == 'all-historical-sessions':return []
        if name.endswith('-open') and name == 'gascity-open':
            if defect == 'foreign-claim':
                return [task,dict(id='ga-other',status='open',assignee='ci-unexpected')]
            return [task]
        if name == 'gascity-routed':
            if defect == 'unexpected-route':return [dict(id='ga-other')]
            return [] if mode=='stage' else [task]
        return []
    # Run the real audit decision body. Only its transport/initial loader is
    # replaced with a fixture; no gc, systemd, subprocess or live state exists.
    source = built[1]['audit-queue-r3.py'].decode()
    body = source[source.index('observations = {}'):]
    namespace = dict(MODE=mode,ROOT=tmp_path,run=run,TARGET=c.TARGET,
        ALIASES={c.TARGET,'codex','gascity--codex'},Path=Path,
        hashlib=hashlib,types=types,json=json)
    exec(compile(body,'queue_fixture','exec'),namespace)
    return json.loads((tmp_path/'result.json').read_bytes()),calls


@pytest.mark.parametrize('mode', ['stage','route','resume'])
def test_real_queue_audit_decisions_for_each_phase(built,tmp_path,mode):
    result,calls = queue_fixture(built,tmp_path,mode)
    assert result['ok'] and result['mutation'] is False and result['worker_launched'] is False
    assert result['sole_eligible_target_task'] == (None if mode=='stage' else c.TASK)
    assert ('exact-task',['--rig','gascity','bd','show',c.TASK,'--json']) in calls


@pytest.mark.parametrize('mode', ['stage','route','resume'])
@pytest.mark.parametrize('defect', ['unexpected-route','foreign-claim','own-fields'])
def test_real_queue_audit_refuses_drift(built,tmp_path,mode,defect):
    with pytest.raises((AssertionError,RuntimeError)):
        queue_fixture(built,tmp_path,mode,defect)
    assert not (tmp_path/'result.json').exists()


@pytest.mark.parametrize('different', [False,True])
def test_close_actual_release_session_binding_precedes_drain(built,tmp_path,different):
    release=load(built[1]['startup-release.py'],'generated_release')
    tree=ast.parse(built[1]['close-r11.py'])
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    start=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Assign)
               and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='release')
    snippet=ast.Module(body=main.body[start:start+2],type_ignores=[])
    observed=dict(id='ci-new',session_name='codex-ci-new',template=c.TARGET,
        rig='gascity',provider=c.PROVIDER,work_dir=c.WORK,closed=False,created_at='today')
    expected=c.close_identity(observed)
    other=dict(observed, id='ci-other') if different else observed
    target=tmp_path/release.ROOT.name/'proof.json'
    target.parent.mkdir()
    target.write_text(json.dumps(dict(session=other)))
    reads=[]
    def read(path):
        reads.append(path)
        return path.read_bytes()
    ns=dict(VAR=tmp_path,os=__import__('os'),json=json,contract=c,expected=expected,
            w=types.SimpleNamespace(read=read,require=c.require))
    if different:
        with pytest.raises(RuntimeError,match='released session'):
            exec(compile(snippet,'close_release_binding','exec'),ns)
    else:
        exec(compile(snippet,'close_release_binding','exec'),ns)
    assert ns['release']==target and reads==[target]


@pytest.mark.parametrize('name',['release-runtime-r13.py','release-delivery-r13.py'])
def test_scoped_release_is_exact_local_source(built,name):
    assert built[1][name] == (HERE/name).read_bytes()
    if name=='release-runtime-r13.py':
        assert b"w.foreign_queue('release-before'" in built[1][name]
        assert b"foreign-before.json" in built[1][name]
    else:
        assert b"Session-scoped Core must leave every foreign tuple byte-equivalent" in built[1][name]



def test_transport_pins_are_consumed_by_actual_startup_release(built):
    _,out=built
    text=out['startup-release.py'].decode()
    for name in ('release-runtime-r13.py','release-delivery-r13.py'):
        assert name in text and a.sha(out[name]) in text
    assert 'release-runtime-r11.py' not in text
    assert 'release-delivery-r11.py' not in text
    runtime=load(out['release-runtime-r13.py'],'bound_runtime')
    assert runtime.CORE_PID==466463 and runtime.CORE_START_TICKS==51763309
    assert runtime.RECEIPT_LIMIT==129


def test_generated_bind_references_completed_worktree(built):
    text=built[1]['bind-task.py'].decode()
    assert text.count('c95506c64aca2b7765ce6e39982cfbc91448dbbc019c352b29520d1637297e9a')==2
    assert '/var/tmp/ga-mb91-worktree-20260930-r1' in text
    assert '163cfd690bcd1f0ca7586d3f1f8bad12f49a8a2a7fb5bb8d48175c5b0acf354c' not in text


def test_materialized_package_matches_exact_final_baseline():
    baseline=Path('/tmp/ga-mb91-readonly-baseline-20260930-r1')
    result=json.loads((baseline/'result.json').read_bytes())
    _,out=a.assemble(observation=str(baseline/'observed.json'),
        observation_sha=result['observed_sha256'],cache_ns=result['cache_pin_ns'])
    manifest=json.loads((HERE/'assembly.json').read_bytes())
    assert manifest['files']=={name:a.sha(raw) for name,raw in out.items()}
    assert manifest['cache_pin_ns']==result['cache_pin_ns']
    for name,raw in out.items():
        assert (HERE/name).read_bytes()==raw,name
        if name.endswith('.sh'):
            assert (HERE/name).stat().st_mode & 0o777 == 0o755
    assert str(HERE/'contract.py') in out['audit-queue-r3.py'].decode()


@pytest.mark.parametrize('defect', ['not-native-ready','duplicate-native-ready'])
def test_native_ready_membership_required_before_stage(built,tmp_path,defect):
    with pytest.raises((AssertionError,RuntimeError)):
        queue_fixture(built,tmp_path,'stage',defect)
    assert not (tmp_path/'result.json').exists()


def test_stage_ready_query_is_unfiltered_and_does_not_grant_route(built,tmp_path):
    result,calls=queue_fixture(built,tmp_path,'stage')
    assert ('fresh-native-ready',['--rig','gascity','bd','ready','--json','--limit','0']) in calls
    assert result['native_ready_member'] is True
    assert result['sole_eligible_target_task'] is None
