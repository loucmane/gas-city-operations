"""Offline four-object read-time contract, never a production refresh."""
import importlib.util
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import types

import pytest

HERE = Path(__file__).parent
HOUR = 3600 * 10**9
SECOND = 10**9
NOW = 100 * HOUR
WINDOW = dict(earliest_ns=NOW, latest_ns=NOW+10*SECOND)


def load(raw, name):
    module = types.ModuleType(name)
    module.__file__ = name + '.py'
    exec(compile(raw, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def generated():
    spec = importlib.util.spec_from_file_location('read_time_build', HERE / 'build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder.assemble(final=True)[1]


@pytest.mark.parametrize('age', [20 * HOUR, 25 * HOUR])
def test_preflight_does_not_require_a_recent_read(generated, monkeypatch, age):
    base = load(generated['window-base-r11.py'], 'read_time_base')
    now = 100 * HOUR
    value = types.SimpleNamespace(st_atime_ns=now-age, st_mtime_ns=HOUR,
                                  st_ctime_ns=HOUR)
    monkeypatch.setattr(base.os, 'statvfs', lambda path: types.SimpleNamespace(f_flag=os.ST_RELATIME))
    monkeypatch.setattr(base.os, 'lstat', lambda path: value)
    base.stable_read_times(paths=[Path('/disposable-fixture')], now_ns=now)


@pytest.fixture
def runtime(generated):
    base = load(generated['window-base-r11.py'], 'generated_base')
    policy = load(generated['read-time-accounting.py'], 'read_policy')
    evidence = []
    base.read_time_policy = lambda: policy
    base.read_time_bounds = lambda: WINDOW
    base.read_time_evidence = lambda *args: evidence.append(copy.deepcopy(args))
    return base, policy, evidence


def meta(kind=stat.S_IFDIR, **changes):
    value = dict(device=2, inode=17, uid=1000, gid=1000, mode=0o755,
                 type=kind, nlink=1, size=4096, mtime_ns=HOUR,
                 ctime_ns=HOUR, atime_ns=75*HOUR)
    value.update(changes)
    return value


@pytest.mark.parametrize('flag', [0, os.ST_NOATIME, os.ST_RELATIME | os.ST_NOATIME])
def test_mount_contract_still_refuses(generated, monkeypatch, flag):
    base = load(generated['window-base-r11.py'], 'bad_mount')
    monkeypatch.setattr(base.os, 'statvfs', lambda _: types.SimpleNamespace(f_flag=flag))
    with pytest.raises(RuntimeError, match='mount policy'):
        base.stable_read_times([Path('/fixture')], NOW)


def test_future_metadata_still_refuses(generated, monkeypatch):
    base = load(generated['window-base-r11.py'], 'future_metadata')
    monkeypatch.setattr(base.os, 'statvfs', lambda _: types.SimpleNamespace(f_flag=os.ST_RELATIME))
    monkeypatch.setattr(base.os, 'lstat', lambda _: types.SimpleNamespace(
        st_atime_ns=NOW+1, st_mtime_ns=HOUR, st_ctime_ns=HOUR))
    with pytest.raises(RuntimeError, match='future'):
        base.stable_read_times([Path('/fixture')], NOW)


@pytest.mark.parametrize('path', sorted(load((HERE/'read-time-accounting.py').read_bytes(), 'paths').PATHS))
def test_exact_four_paths_accept_only_comparison_copy(runtime, path):
    _, p, _ = runtime
    a = meta(stat.S_IFREG if path == p.SUSPENSION else stat.S_IFDIR)
    z = dict(a, atime_ns=NOW+SECOND)
    frozen = copy.deepcopy((a,z))
    aligned, changes = p.metadata(path,a,z,WINDOW)
    assert aligned == a and len(changes) == 1
    assert (a,z) == frozen
    assert changes[0]['attribution'] == 'read-compatible, not process attribution'


@pytest.mark.parametrize('key', sorted({'device','inode','uid','gid','mode','type','nlink','size','mtime_ns','ctime_ns'}))
def test_non_access_fields_refuse(runtime, key):
    _, p, _ = runtime
    a = meta(); z = dict(a,atime_ns=NOW+SECOND); z[key] += 1
    with pytest.raises(RuntimeError):
        p.metadata(p.CITY,a,z,WINDOW)


@pytest.mark.parametrize('new', [74*HOUR, NOW-1, NOW+11*SECOND])
def test_backward_and_out_of_window_refuse(runtime, new):
    _, p, _ = runtime
    with pytest.raises(RuntimeError):
        p.metadata(p.CITY,meta(),meta(atime_ns=new),WINDOW)


def test_path_and_schema_refuse(runtime):
    _, p, _ = runtime
    for path in (p.CITY+'/.gc',p.CITY+'/../city',p.CITY+'/.beads/routes.jsonl'):
        with pytest.raises(RuntimeError): p.metadata(path,meta(),meta(),WINDOW)
    for z in (dict(meta(),extra=0),dict(meta(),atime_ns=True)):
        with pytest.raises(RuntimeError): p.metadata(p.CITY,meta(),z,WINDOW)
    with pytest.raises(RuntimeError):
        p.metadata(p.CITY,meta(),meta(),dict(earliest_ns=2,latest_ns=1))


def test_relatime_eligibility_is_not_arbitrary_time_waiver(runtime):
    _, p, _ = runtime
    a = meta(atime_ns=80*HOUR)
    with pytest.raises(RuntimeError,match='relatime'):
        p.metadata(p.CITY,a,dict(a,atime_ns=NOW+SECOND),WINDOW)
    a['mtime_ns'] = a['atime_ns']
    assert p.metadata(p.CITY,a,dict(a,atime_ns=NOW+SECOND),WINDOW)[0] == a


def test_existing_parent_rename_times_remain_visible_and_bounded(runtime):
    _, p, _ = runtime
    a = meta(atime_ns=99*HOUR)
    z = dict(a,atime_ns=NOW+2*SECOND,mtime_ns=NOW+SECOND,ctime_ns=NOW+SECOND)
    aligned, changes = p.metadata(p.CITY,a,z,WINDOW,renamed=True)
    assert changes and aligned['mtime_ns'] == z['mtime_ns']
    assert aligned['ctime_ns'] == z['ctime_ns']
    with pytest.raises(RuntimeError): p.metadata(p.CITY,a,z,WINDOW)
    with pytest.raises(RuntimeError):
        p.metadata(p.CITY,a,dict(z,ctime_ns=NOW+20*SECOND),WINDOW,renamed=True)
    with pytest.raises(RuntimeError):
        p.metadata(p.SUSPENSION,meta(stat.S_IFREG),meta(stat.S_IFREG),WINDOW,renamed=True)


def directories():
    return dict(city={'.':meta(),'.beads':meta(),'.gc':meta(),'city.toml':meta(stat.S_IFREG)},
                provision={'.':meta(),'receipt.json':meta(stat.S_IFREG)},
                runtime_children={'.gc':{},'.beads':{}})


def test_real_directory_preservation_accounts_three_parents(runtime):
    w,_,evidence = runtime
    a=directories(); z=copy.deepcopy(a)
    for section,key in (('city','.'),('city','.beads'),('provision','.')):
        z[section][key]['atime_ns']=NOW+SECOND
    original=copy.deepcopy(z)
    with pytest.raises(RuntimeError): w.directory_preservation(a,z)
    w.directory_preservation(a,z,read_window=WINDOW)
    assert z==original and len(evidence[-1][3])==3
    z['city']['.gc']['atime_ns']=NOW+SECOND
    with pytest.raises(RuntimeError): w.directory_preservation(a,z,read_window=WINDOW)


@pytest.mark.parametrize('key', ['mode','uid','gid','inode','size','nlink'])
def test_directory_authority_still_refuses(runtime,key):
    w,_,_ = runtime
    a=directories(); z=copy.deepcopy(a)
    z['city']['.'][key]+=1
    with pytest.raises(RuntimeError): w.directory_preservation(a,z,read_window=WINDOW)


def suspension_record(suspended=True, inode=17, atime=75*HOUR):
    raw=json.dumps(dict(city=dict(suspended=True),rigs=dict(
        gascity=dict(suspended=suspended),hpfetcher=dict(suspended=True),
        blog=dict(suspended=True)),updated_at='2026-09-28T06:00:00Z'))
    return dict(raw=raw,pin=dict(sha256=hashlib.sha256(raw.encode()).hexdigest(),
        metadata=meta(stat.S_IFREG,mode=0o644,size=len(raw),inode=inode,atime_ns=atime)))


def test_real_lineage_empty_gap_and_content_refusal(generated,runtime):
    w,p,evidence=runtime
    s=load(generated['suspension-lineage.py'],'lineage')
    a=suspension_record();z=copy.deepcopy(a);z['pin']['metadata']['atime_ns']=NOW+SECOND
    with pytest.raises(RuntimeError):s.chain(a,[],z,'/fixture',terminal=True)
    assert s.chain(a,[],z,'/fixture',terminal=True,read_account=w.suspension_read_equal)==z['pin']
    assert evidence[-1][0]=='suspension'
    bad=copy.deepcopy(z);bad['raw']+=' '
    with pytest.raises(RuntimeError):p.suspension(a,bad,WINDOW)
    bad=copy.deepcopy(z);bad['pin']['sha256']='0'*64
    with pytest.raises(RuntimeError):p.suspension(a,bad,WINDOW)


def phase(action, s):
    intent=dict(phase=action,argv=s.ACTIONS[action][2],cwd='/fixture')
    result=dict(intent,exit_code=0,timed_out=False,primary_error=None,stderr='',
        cleanup=dict(direct_child_reaped=True,owned_process_group_gone=True,
                     failures=[],unexpected_survivors=[]))
    return intent,result


def test_real_lineage_predecessor_atomic_change_and_noop(generated,runtime):
    w,_,_=runtime;s=load(generated['suspension-lineage.py'],'lineage2')
    a=suspension_record(); before=suspension_record(atime=NOW+SECOND)
    after=suspension_record(False,18,NOW+SECOND)
    intent,result=phase('rig-resume',s)
    e=dict(action='rig-resume',before=before,after=after,intent=intent,result=result)
    assert s.chain(a,[e],after,'/fixture',read_account=w.suspension_read_equal)==after['pin']
    with pytest.raises(RuntimeError):s.chain(a,[e,e],after,'/fixture',read_account=w.suspension_read_equal)
    bad=copy.deepcopy(e);bad['after']['pin']['metadata']['inode']=17
    with pytest.raises(RuntimeError,match='atomic'):s.chain(a,[bad],bad['after'],'/fixture',read_account=w.suspension_read_equal)
    s.step(a,before,'rig-suspend',read_account=w.suspension_read_equal)
    with pytest.raises(RuntimeError):s.step(a,before,'rig-suspend')
    bad=copy.deepcopy(e);bad['result']['cleanup']['unexpected_survivors']=[1]
    with pytest.raises(RuntimeError):s.chain(a,[bad],after,'/fixture',read_account=w.suspension_read_equal)


def clock(second):
    def sample(n):return dict(boot='fixture-boot',real_ns=NOW+n,
        boot_before_ns=n,boot_after_ns=n)
    return dict(start=sample(second*SECOND),end=sample(second*SECOND+1))


def route_rows(r):
    rows={}
    for _,root in r.RIGS:
        raw=r.expected_routes(root)
        rows[root]=dict(content=raw,sha256=hashlib.sha256(raw.encode()).hexdigest(),
            parent=meta(),metadata=meta(stat.S_IFREG,mode=0o644,size=len(raw)))
    return rows


def route_snapshot(rows,second,chain=()):
    city='/home/loucmane/gascity/city'
    return dict(generated_routes=copy.deepcopy(rows),generated_route_chain=list(chain),
        cache_access_clock=clock(second),directories=dict(
            city={'.beads':copy.deepcopy(rows[city]['parent'])},
            runtime_children={'.beads':{'routes.jsonl':copy.deepcopy(rows[city]['metadata'])}}))


def test_real_route_projection_gap_and_mirror_refusals(generated,runtime):
    w,_,_=runtime;r=load(generated['restore-r9-routes-r3.py'],'routes')
    c=load(generated['route-chain-r1.py'],'route_chain');p=load(generated['cache-atime-policy-r1.py'],'clock')
    rows=route_rows(r);a=route_snapshot(rows,0)
    rows[str(w.CITY)]['parent']['atime_ns']=NOW+SECOND;z=route_snapshot(rows,5)
    with pytest.raises(RuntimeError):c.project(a,z,{},r,p,[],[])
    first,last,proof=c.project(a,z,{},r,p,[],[],read_account=w.route_read_account)
    assert first['directories']==last['directories'] and not proof['reloads']
    bad=copy.deepcopy(z);bad['directories']['city']['.beads']['inode']+=1
    with pytest.raises(RuntimeError,match='mirror'):c.project(a,bad,{},r,p,[],[],read_account=w.route_read_account)
    for root in [r.RIGS[1][1],str(w.CITY)]:
        badrows=copy.deepcopy(rows);badrows[root]['metadata']['inode']+=1
        with pytest.raises(RuntimeError):c.project(a,route_snapshot(badrows,5),{},r,p,[],[],read_account=w.route_read_account)
    badrows=copy.deepcopy(rows);badrows[r.RIGS[1][1]]['parent']['atime_ns']=NOW+SECOND
    with pytest.raises(RuntimeError):c.project(a,route_snapshot(badrows,5),{},r,p,[],[],read_account=w.route_read_account)


def test_source_wiring_preserves_clock_and_loaded_order(generated):
    base=generated['window-base-r11.py'].decode();wrapper=generated['window-r11.py'].decode()
    assert base.index('def read_time_policy')<base.index("if __name__=='__main__'")
    assert wrapper.count('read_account=w.route_read_account')==3
    assert 'read_window=accounting[\'window\']' in wrapper
    assert 'p.bounds(read_start,read_end)' in wrapper
    helper=ast.parse(generated['read-time-accounting.py'])
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                   and n.func.attr in {'utime','chmod','chown','write_text','write_bytes','run'}
                   for n in ast.walk(helper))


def reload_event(r, first, second):
    argv=['gc','reload','--json'];revision='new'
    cleanup=dict(direct_child_reaped=True,owned_process_group_gone=True,
                 failures=[],unexpected_survivors=[])
    ack=dict(ok=True,async_=False,soft=False,outcome='applied',revision=revision)
    ack['async']=ack.pop('async_')
    cycle=dict(controller_pid=2800348,config_revision=revision,completion_status='completed',
               fields=dict(active_template_count=0),seq=1,
               ts=datetime.fromtimestamp((NOW+2*SECOND)/SECOND,timezone.utc).isoformat())
    phase=dict(phase='stage-reload',argv=argv,cwd='/fixture',exit_code=0,
               timed_out=False,primary_error=None,cleanup=cleanup,stdout=json.dumps(ack))
    trace=dict(phase,phase='stage-reload-trace-0',
               argv=['gc','trace','show','--type','cycle_result','--since','2m','--json'],
               stdout=json.dumps(dict(records=[cycle])))
    event=dict(name='stage-reload',phase=phase,trace=trace,accepted=dict(ack=ack,cycle=cycle),
               before=first,after=second,before_clock=clock(1),after_clock=clock(3),
               observed_at_ns=NOW+3*SECOND)
    return event,argv


def test_real_route_native_regeneration_retains_all_proofs(generated,runtime):
    w,_,_=runtime;r=load(generated['restore-r9-routes-r3.py'],'native_routes')
    c=load(generated['route-chain-r1.py'],'native_chain');p=load(generated['cache-atime-policy-r1.py'],'native_clock')
    first=route_rows(r);second=copy.deepcopy(first)
    for row in second.values():
        row['metadata']['inode']+=1
        for key in ('mtime_ns','ctime_ns'):row['parent'][key]=NOW+2*SECOND
    second[str(w.CITY)]['parent']['atime_ns']=NOW+2*SECOND
    e,argv=reload_event(r,first,second)
    a=route_snapshot(first,0);z=route_snapshot(second,5,['stage-reload'])
    x,y,proof=c.project(a,z,{'stage-reload':e},r,p,['old','new'],argv,
                         read_account=w.route_read_account)
    assert len(proof['changes'])==5 and x['directories']==y['directories']
    mutations=[lambda v:v['accepted']['cycle'].update(controller_pid=1),
               lambda v:v['phase']['cleanup'].update(unexpected_survivors=[1]),
               lambda v:v['after'][str(w.CITY)]['metadata'].update(inode=17),
               lambda v:v['after'][str(w.CITY)]['metadata'].update(mode=0o666),
               lambda v:v['after'][str(w.CITY)].update(content='forged'),
               lambda v:v['after'][r.RIGS[1][1]]['parent'].update(atime_ns=NOW+SECOND)]
    for mutate in mutations:
        bad=copy.deepcopy(e);mutate(bad)
        with pytest.raises(RuntimeError):
            c.validate_event(bad,'stage-reload',r,p,['old','new'],argv,
                             read_account=w.route_read_account)


def test_generated_snapshot_accounts_its_own_directory_read(generated,runtime):
    # Execute the generated function itself; host/observer inputs are synthetic.
    w,_,evidence=runtime;r=load(generated['restore-r9-routes-r3.py'],'snapshot_routes')
    p=load(generated['cache-atime-policy-r1.py'],'snapshot_clock')
    first=route_rows(r);last=copy.deepcopy(first)
    last[str(w.CITY)]['parent']['atime_ns']=NOW+SECOND
    captures=iter([first,last]);samples=iter([clock(0)['start'],clock(0)['end'],
                                          clock(2)['start'],clock(2)['end']])
    saved={};w.host=lambda o: {'host':'same'};w.provider_pins=lambda b,o: {}
    w.dependency_image=lambda x:x;w.directories=lambda o:route_snapshot(last,2)['directories']
    w.save=lambda name,value:saved.setdefault(name,value)
    route_adapter=types.SimpleNamespace(capture_routes=lambda w,o:next(captures))
    node=next(n for n in ast.parse(generated['window-r11.py']).body
              if isinstance(n,ast.FunctionDef) and n.name=='collect_snapshot')
    ns=dict(w=w,routes=route_adapter,p=p,clock_sample=lambda:next(samples),
            integrity_baseline=lambda _:dict(pins={},providers={}),reload_events=lambda:([],{}))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<generated snapshot>','exec'),ns)
    ns['collect_snapshot']('later.json',types.SimpleNamespace(CACHE='fixture',PROTECTED=[]),
        types.SimpleNamespace(tree_snapshot=lambda *args,**kwargs:{}))
    assert saved['later.json']['generated_routes']==last
    assert evidence[-1][0]=='routes' and evidence[-1][3]


def test_clock_boot_deadline_and_offset_checks_unchanged(generated):
    p=load(generated['cache-atime-policy-r1.py'],'bounded_clock')
    for bad in (clock(5*3600),clock(1)):
        if bad['start']['boot_before_ns']==SECOND:bad['end']['boot']='different'
        with pytest.raises(RuntimeError):p.bounds(clock(0),bad)
    bad=clock(2);bad['end']['real_ns']+=SECOND
    with pytest.raises(RuntimeError,match='offset'):p.bounds(clock(0),bad)
