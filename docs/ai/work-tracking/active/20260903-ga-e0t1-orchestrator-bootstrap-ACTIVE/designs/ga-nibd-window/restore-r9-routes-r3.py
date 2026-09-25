"""One restoration-only successor for the exact consumed R9 stage.

No stage, receipt write, route, resume or provider operation is exposed.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import types

HERE=Path('/tmp/ga-y49e-launch-20260920')
FAILED=HERE/'window-r9'
ROOT=HERE/'restore-r9-routes-r3'
ORIGINAL_SHA='f9af9039203cc267a0b11fe2e95a2e4da23797dfad2593b48724a9785eb81c47'
READ_OBSERVATION=HERE/'restore-r9-routes-r2/recovery-before.json'
READ_SHA='90b731a08ce9b3354ce28c26d1f65e29ebe7cbbe7a556651b72f08a59cad4c22'
SOURCE=HERE/'window-state-r9.py'
SOURCE_SHA='0252bc4072f905bb2e8e7f39efd63a3dc12be6c7742227d12efa8a01fbb905d4'
RIGS=[('ci','/home/loucmane/gascity/city'),
      ('gct','/home/loucmane/gas-city-native'),
      ('ga','/home/loucmane/gascity/city/rigs/gascity'),
      ('blog','/home/loucmane/dev/blog'),
      ('hpf','/home/loucmane/dev/hpfetcher-gc-main')]

def require(ok,message):
    if not ok: raise RuntimeError(message)

def expected_routes(root):
    return ''.join(json.dumps(dict(prefix=p,path=os.path.relpath(r,root)),separators=(',',':'))+'\n' for p,r in RIGS)

def route_authority(rows):
    require(set(rows)=={root for _,root in RIGS},'route root set')
    for _,root in RIGS:
        row=rows[root];m=row['metadata'];parent=row['parent']
        require(set(row)=={'metadata','parent','content','sha256'},'route observation shape')
        require(row['content']==expected_routes(root),'route content differs from exact registered graph')
        require(row['sha256']==hashlib.sha256(row['content'].encode()).hexdigest(),'route digest')
        require(m['type']==stat.S_IFREG and m['mode']==0o644 and m['nlink']==1
                and m['uid']==m['gid']==1000 and m['size']==len(row['content'].encode()),'route authority')
        require(parent['type']==stat.S_IFDIR and parent['uid']==parent['gid']==1000,'route parent authority')

def compare_routes(a,z,bounds):
    route_authority(a);route_authority(z)
    changes=[]
    for _,root in RIGS:
        first=a[root];last=z[root]
        require(first['content']==last['content'] and first['sha256']==last['sha256'],'route content mutation')
        for section,allowed in [('metadata',{'inode','atime_ns','mtime_ns','ctime_ns'}),
                                ('parent',{'mtime_ns','ctime_ns'})]:
            x=first[section];y=last[section]
            require(set(x)==set(y),'metadata field set changed')
            require({k:v for k,v in x.items() if k not in allowed}==
                    {k:v for k,v in y.items() if k not in allowed},'non-generated route authority drift')
            for key in allowed-{'inode'}:
                require(type(x[key]) is int and type(y[key]) is int,'timestamp type')
                if x[key]!=y[key]:
                    require(y[key]>=x[key] and bounds['earliest_ns']<=y[key]<=bounds['latest_ns'],
                            'route timestamp outside observed restoration')
            require(section!='metadata' or x['inode']!=y['inode'],'route was not atomically regenerated')
        changes.append(dict(root=root,before=first,after=last))
    return changes

def comparison_copies(before,after,route_before,route_after,bounds):
    changes=compare_routes(route_before,route_after,bounds)
    a=copy.deepcopy(before);z=copy.deepcopy(after)
    city=RIGS[0][1]
    for snapshot,routes in ((a,route_before),(z,route_after)):
        require(snapshot['directories']['runtime_children']['.beads']['routes.jsonl']==routes[city]['metadata'],
                'route inventory mirror mismatch')
        require(snapshot['directories']['city']['.beads']==routes[city]['parent'],'route parent mirror mismatch')
    # Normalize only validated identities in comparison copies. Original full
    # observations and all generated route records remain immutable evidence.
    z['directories']['runtime_children']['.beads']['routes.jsonl']['inode']=a['directories']['runtime_children']['.beads']['routes.jsonl']['inode']
    for key in ('mtime_ns','ctime_ns'):
        z['directories']['city']['.beads'][key]=a['directories']['city']['.beads'][key]
    # In particular scripts atime is NOT waived: the known post-refusal preimage
    # is bound below and must remain exact across this recovery.
    return a,z,changes

def capture_routes(w,o):
    rows={}
    for _,root in RIGS:
        path=Path(root)/'.beads/routes.jsonl'
        require(path.parent.resolve(strict=True)==path.parent,'route parent alias')
        raw=w.read(path)
        pin,second=o.read_file(str(path),collect=True)
        require(raw==second,'route read drift')
        rows[root]=dict(metadata=pin['metadata'],parent=o.metadata(path.parent.lstat()),
                        content=raw.decode(),sha256=pin['sha256'])
    route_authority(rows)
    return rows

def restore_city(w,r,b,owned,original):
    immediate=dict(start=r.clock_sample(),end=r.clock_sample())
    admission=r.p.bounds(original['cache_access_clock'],immediate)
    w.save('immediate-clock-admission.json',dict(original_sha256=ORIGINAL_SHA,
                                                clock=immediate,bounds=admission))
    w.phase('restore-city',w.confined(['inner','city','0'],'city'),b,owned)
    w.reload('restore-reload',0,b,owned)

def account_recorded_reads(before,after,bounds):
    city='/home/loucmane/gascity/city/'
    entries=[
        (('directories','city','agents'),1789895813088038603,1789982746446141410),
        (('directories','city','commands'),1789895813088038603,1789982746446141410),
        (('directories','city','doctor'),1789895813088038603,1789982746446141410),
        (('directories','city','formulas'),1789895813149874588,1789982746494140997),
        (('directories','city','pack.toml'),1789895813088038603,1789982746442141445),
        (('directories','city','packs.lock'),1789895813009713021,1789982746378141996),
        (('directories','city','template-fragments'),1789895813153996988,1789982746498140963),
        (('pins',city+'pack.toml','metadata'),1789895813088038603,1789982746442141445),
        (('pins',city+'packs.lock','metadata'),1789895813009713021,1789982746378141996),
        (('pins',city+'.gc/site.toml','metadata'),1789895813137507391,1789982746478141135),
        (('pins',city+'agents/watch-officer/prompt.template.md','metadata'),1789895813149874588,1789982746494140997),
        (('pins',city+'managed/attention-funnel.toml','metadata'),1789895813092161002,1789982746450141376),
        (('pins',city+'managed/core-signing-continuity.toml','metadata'),1789895813092161002,1789982746450141376),
        (('pins',city+'managed/rig-permissions.toml','metadata'),1789895813092161002,1789982746446141410)]
    for snapshot in (before,after):
        for name in ('pack.toml','packs.lock'):
            require(snapshot['directories']['city'][name]==snapshot['pins'][city+name]['metadata'],
                    'recorded read mirror mismatch')
        require(snapshot['directories']['runtime_children']['.gc']['site.toml']==
                snapshot['pins'][city+'.gc/site.toml']['metadata'],'recorded read mirror mismatch')
    def get(value,path):
        for part in path:value=value[part]
        return value
    adjusted=copy.deepcopy(before);changes=[]
    for path,old,new in entries:
        a=get(before,path);z=get(after,path)
        require(a['atime_ns']==old and z['atime_ns']==new,'unreviewed read endpoint')
        require({k:v for k,v in a.items() if k!='atime_ns'}==
                {k:v for k,v in z.items() if k!='atime_ns'},'recorded read authority drift')
        require(new>old and bounds['earliest_ns']<=new<=bounds['latest_ns'],'recorded read clock bounds')
        get(adjusted,path)['atime_ns']=new
        changes.append(dict(path=list(path),before_ns=old,after_ns=new))
    adjusted['directories']['runtime_children']['.gc']['site.toml']['atime_ns']=after['pins'][city+'.gc/site.toml']['metadata']['atime_ns']
    return adjusted,changes

def main():
    require(os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA'),'bound uid1000 entry')
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA,'executor source drift')
    raw=SOURCE.read_bytes();require(hashlib.sha256(raw).hexdigest()==SOURCE_SHA,'window source drift')
    r=types.ModuleType('recovery_window');r.__file__=str(SOURCE)
    exec(compile(raw,str(SOURCE),'exec',dont_inherit=True),r.__dict__)
    w=r.w;b,o,owned=w.load_support();w.pins()
    w.read(FAILED/'stage-refused.json','27187bfd6efa44a868cdec65db1e6c59e966efbbded6d8c90d214a035e33bc39')
    old=json.loads(w.read(FAILED/'stage-before-receipt.json','174a49d48cc637b3335781790b01a56ff7ce791ea8799abae44a551fb20fe53f'))
    original=json.loads(w.read(FAILED/'before.json',ORIGINAL_SHA))
    admitted=json.loads(w.read(READ_OBSERVATION,READ_SHA))
    old_clock=r.p.bounds(old['cache_access_clock'],admitted['cache_access_clock'])
    adjusted_old,read_changes=account_recorded_reads(old,admitted,old_clock)
    require(not any(FAILED.glob('restore-*')) and not (FAILED/'stage-pass.json').exists(),'unexpected prior disposition')
    require(not any(FAILED.glob('suspension-*-intent.json')),'lifecycle already occurred')
    require(not (FAILED/'stage-receipt-apply-started.json').exists(),'receipt apply attempted')
    w.complete_containment();w.verified_lifecycle(terminal=True)
    w.read(w.CITY/'city.toml',w.CITY_SHA[1]);w.read(w.RECEIPT,w.RECEIPT_SHA[0]);w.host(o)
    ROOT.mkdir(mode=0o700)
    w.ROOT=ROOT;w.__file__=str(SOURCE);w._SOURCE_SHA=SOURCE_SHA
    w.save('intent.json',dict(source_sha256=_SOURCE_SHA,failed_root=str(FAILED),
                             operation='restore-city-and-supported-reload-only'))
    w.save('recorded-read-admission.json',dict(observation_sha256=READ_SHA,
        changes=read_changes,clock=old_clock,timestamp_writes=False))
    r.preservation(adjusted_old,admitted,w.CITY_SHA[1],w.RECEIPT_SHA[0])
    w.snapshot('recovery-before.json',b,o);before=w.record('recovery-before.json')
    # Exact known post-refusal state, not an invented replacement success baseline.
    r.preservation(admitted,before,w.CITY_SHA[1],w.RECEIPT_SHA[0])
    r.p.bounds(original['cache_access_clock'],before['cache_access_clock'])
    routes_before=capture_routes(w,o);w.save('routes-before.json',routes_before)
    restore_city(w,r,b,owned,original)
    w.host(o);w.read(w.CITY/'city.toml',w.CITY_SHA[0]);w.read(w.RECEIPT,w.RECEIPT_SHA[0])
    w.snapshot('recovery-after.json',b,o);after=w.record('recovery-after.json')
    routes_after=capture_routes(w,o);w.save('routes-after.json',routes_after)
    clock=r.p.bounds(before['cache_access_clock'],after['cache_access_clock'])
    r.p.bounds(original['cache_access_clock'],after['cache_access_clock'])
    a,z,changes=comparison_copies(before,after,routes_before,routes_after,clock)
    for snapshot in (a,z): snapshot.pop('cache_access_clock')
    mounts=a.pop('cache_access_mounts')
    require(mounts==z.pop('cache_access_mounts') and mounts==r.cache_mounts(),'cache mount drift')
    accounting=r.p.compare(a['cache'],z['cache'],before['cache_access_clock'],after['cache_access_clock'])
    # Recovery does not execute a provider and must not introduce cache changes.
    require(not accounting['deltas'],'unexpected recovery cache access change')
    r.original_preservation(a,z,w.CITY_SHA[0],w.RECEIPT_SHA[0])
    w.complete_containment()
    w.ROOT=FAILED
    try: w.verified_lifecycle(terminal=True)
    finally: w.ROOT=ROOT
    w.save('result.json',dict(ok=True,configuration_receipt_coherent=True,
        historical_route_byte_equality_proven=False,old_route_inode_restored=False,
        generated_routes=changes,clock=clock,cache_accounting=accounting,
        before_sha256=hashlib.sha256(w.read(ROOT/'recovery-before.json')).hexdigest(),
        after_sha256=hashlib.sha256(w.read(ROOT/'recovery-after.json')).hexdigest(),
        worker_launched=False,receipt_written=False,fresh_integrity_required=True))
    print(json.dumps(dict(ok=True,configuration_receipt_coherent=True,worker_launched=False,
                         fresh_integrity_required=True)))

if __name__=='__main__':main()
