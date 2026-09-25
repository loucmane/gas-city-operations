"""One receipt-only transaction through the unchanged reviewed provisioner.

No worker, inference, signing, reload, service transition or root operation.
Readiness is reused only while its input closure still matches. Every live
phase uses the existing owned-group runner and a read-only filesystem except
the existing provisioning directory; its runner subdirectory stays read-only.

P6 rebind of the reviewed 09-20 adoption `4d9857fc`. The logic is unchanged, and so is
the provisioner `64425a72`. Only these bindings change:
- the P6 readiness;
- the old receipt `01ed1bce`;
- the draft path and revision, proven by the reviewed derivation;
- the accepted-deployment evidence and the witness platform self digests, both from `m5_acceptance()`.

The readiness-derived constants stay None until readiness has passed. They are filled
before the two adoption reviews, and the script refuses until then.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

HERE=Path(__file__).parent
ROOT=Path('/var/tmp/gct-m1wh-p6-adoption-20260923-r2')
READY=Path('/var/tmp/gct-m1wh-p6-readiness-20260923-r2')
READY_SOURCE=HERE/'p6-readiness.py'
READY_SHA='7b28b3e551e86818a2cdda3e53ed90c7072781e0a9354bd1ebf5d9425d579133'
OLD_SHA='01ed1bce0b99d5c6043804cdacb2b25bc725bffb00dba3450888284e570d0a8a'
# Filled from the passed -r2 readiness evidence before the adoption reviews. The -r1 evidence
# (12:06Z) went stale when a coordinator gc Bead note touched the pack cache repo at 12:10:54Z.
NEW_SHA='0b30c23f4484382fd4918f394599268f4f4005ac71118e8a7f82ca72eb9615ff'
NEW_SELF='c635e8ee0547ebc8c4caec6577d65103b9d17436ff17a18f66687f0ea3f1957f'
READY_RESULT_SHA='a6cac0b99822e8432fa8b01b2a0c87bb212ff141c165d13d4921b2b75f8c8ee7'
READY_BEFORE_SHA='c668ed0fbf17111d337dafdda113963a4ed66bb439ef9fbbf2aefa940610bf70'
READY_PINS_SHA='a5f7f8c11a95b48d01f910c5c4668828d61a587a5942545f27d403ebadfeac8f'
CORE='796d9a7a67c42294fdc467c107bb59b76e482301'
EVIDENCE=[
 ('reviewed-build','/var/tmp/ga-mutg-custody-build-20260920/artifact-verification.json','fd1317440274f995aa52bebea565bba511912fdcb7a36b52b67105a673ee23ee'),
 ('typed-interoperability',str(HERE/'typed-interoperability.json'),'315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563'),
]

def require(ok,message):
    if not ok:raise RuntimeError(message)

def load():
    raw=READY_SOURCE.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==READY_SHA,'readiness source drift')
    r=types.ModuleType('reviewed_readiness');r.__file__=str(READY_SOURCE)
    r.__dict__['_SOURCE_SHA']=READY_SHA
    exec(compile(raw,str(READY_SOURCE),'exec',dont_inherit=True),r.__dict__)
    b=r.load_base();b.ROOT=ROOT;r.ROOT=ROOT
    require(None not in (NEW_SHA,NEW_SELF,READY_RESULT_SHA,READY_BEFORE_SHA,READY_PINS_SHA),'readiness bindings not yet filled')
    r.pin_inputs(b)
    b.read(Path(__file__),_SOURCE_SHA)
    b.read(READY/'receipt.final.json',NEW_SHA)
    b.read(READY/'result.json',READY_RESULT_SHA)
    b.read(READY/'before.json',READY_BEFORE_SHA)
    b.read(READY/'before.json.provider-pins',READY_PINS_SHA)
    return r,b

def draft(b):
    return b.recorded_draft()

def provisioner(r,b):
    raw=b.read(r.PROVISIONER,r.PROVISIONER_SHA)
    p=types.ModuleType('reviewed_provisioner');p.__file__=str(r.PROVISIONER)
    sys.modules[p.__name__]=p
    exec(compile(raw,str(r.PROVISIONER),'exec',dont_inherit=True),p.__dict__)
    return p

def bytes_out(path,raw,mode=0o600):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,mode)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    parent=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(parent)
    finally:os.close(parent)

def dependency_image(value):
    # Read access timestamps are observations, not content/version inputs.
    # This is ONLY used to reuse prior evidence; immediate before/after checks
    # below retain all metadata, including atime, outside the replaced receipt.
    if isinstance(value,dict):return {k:dependency_image(v) for k,v in value.items() if k!='atime_ns'}
    if isinstance(value,list):return [dependency_image(v) for v in value]
    return value

def directory_state(r,b):
    o=b.observe_module();tree=o.tree_snapshot(b.RECEIPT.parent,protected=True)
    require(set(tree['inventory'])=={'.','receipt.json','bin','bin/gct-managed-worker-canary'},'unexpected provisioning entry')
    return dict(tree=tree,runner=o.read_file(str(r.RUNNER))[0])

def capture(r,b,name):
    if name=='before.json':
        r.snapshot(b,name);b.write(name+'.directory',directory_state(r,b));return
    before=json.loads(b.read(ROOT/'before.json'));o=b.observe_module()
    host=o.host_observation()
    pins={path:o.read_file(path)[0] for path in before['pins']}
    cache=o.tree_snapshot(b.CACHE,cache=True)
    protected={str(path):o.tree_snapshot(path,protected=True) for path in b.PROTECTED}
    require(host==o.host_observation(),'host changed during snapshot')
    b.write(name,dict(host=host,pins=pins,cache=cache,protected=protected))
    b.write(name+'.provider-pins',dict(worker=o.read_file(str(r.WORKER_NATIVE))[0],
        api_package=r.native_package_pair(b),subscription=o.read_file(str(r.SUBSCRIPTION))[0],
        provisioner=o.read_file(str(r.PROVISIONER))[0],runner=o.read_file(str(r.RUNNER))[0],
        api_link=dict(target=os.readlink(r.NATIVE_LINK),metadata=o.metadata(r.NATIVE_LINK.lstat()))))
    b.write(name+'.directory',directory_state(r,b))

def verify_snapshot(r,b,name,expected):
    before=json.loads(b.read(ROOT/'before.json'));after=json.loads(b.read(ROOT/name))
    got=after['pins'].pop(str(b.RECEIPT));before['pins'].pop(str(b.RECEIPT))
    require(before==after,'unrelated host/config/cache/protected drift')
    require(b.read(ROOT/'before.json.provider-pins')==b.read(ROOT/(name+'.provider-pins')),'provider/runner drift')
    require(got['sha256']==expected,'receipt bytes mismatch')
    m=got['metadata']
    require((m['uid'],m['gid'],m['mode'],m['type'],m['nlink'])==(1000,1000,0o600,stat.S_IFREG,1),'receipt authority mismatch')
    prior=json.loads(b.read(ROOT/'before.json.directory'));current=json.loads(b.read(ROOT/(name+'.directory')))
    require(prior['runner']==current['runner'],'runner directory content drift')
    a=prior['tree']['inventory'];z=current['tree']['inventory']
    require(set(a)==set(z),'provisioning entry drift')
    a.pop('receipt.json');z.pop('receipt.json')
    for key in ('mtime_ns','ctime_ns'):a['.'].pop(key);z['.'].pop(key)
    require(a==z,'unrelated provisioning directory metadata drift')

def witness_bytes(r,b,p):
    m5=b.input_module().m5_acceptance()
    items=[]
    for role,path,digest in [('accepted-deployment',m5['acceptance_path'],m5['acceptance_sha256']),*EVIDENCE]:
        b.read(Path(path),digest);items.append(dict(role=role,path=path,sha256=digest))
    document=dict(schema='gct.core-typed-support.v1',city_path=str(b.CITY),
        platform_manifest_sha256=m5['manifest_sha256'],
        platform_receipt_sha256=m5['receipt_sha256'],
        consumer=dict(path='/home/loucmane/gascity/bin/gc',sha256=b.GC_SHA,commit=CORE,tree='f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13'),evidence=items)
    return p.canonical_json(document)

def assert_mounts(b,writable):
    import re
    rows=[]
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        f=line.split();mount=re.sub(r'\\([0-7]{3})',lambda m:chr(int(m[1],8)),f[4])
        require('\\' not in mount,'mount escape');rows.append((mount,f[5].split(',')))
    target=str(b.RECEIPT.parent);proof={}
    for path in (str(b.CACHE),*(str(p) for p in b.PROTECTED),str(b.CITY),str(ROOT),str(b.RECEIPT.parent/'bin'),target):
        cover=max(((m,o) for m,o in rows if m=='/' or path==m or path.startswith(m+'/')),key=lambda x:len(x[0]))
        expected='rw' if writable and path==target else 'ro'
        require(expected in cover[1],'mount authority '+path)
        for m,opts in rows:
            if m.startswith(path+'/') and 'rw' in opts:
                require(writable and m==target,'unexpected writable descendant '+m)
        proof[path]=cover
    return proof

def inner(r,b,mode):
    require(mode in ('check','apply','verify','rollback'),'invalid inner mode')
    proof=assert_mounts(b,mode in ('apply','rollback'));p=provisioner(r,b)
    before=json.loads(b.read(ROOT/'before.json'));o=b.observe_module()
    for path,pin in before['pins'].items():
        if path==str(b.RECEIPT):continue
        require(dependency_image(o.read_file(path)[0])==dependency_image(pin),'input drift '+path)
    old=b.read(b.RECEIPT)
    expected=NEW_SHA if mode in ('rollback','verify') else OLD_SHA
    require(hashlib.sha256(old).hexdigest()==expected,'receipt state does not authorize this operation')
    if mode=='rollback':
        backup=b.read(ROOT/'receipt.before.json',OLD_SHA)
        p.restore_snapshot(b.RECEIPT,p.FileSnapshot(True,backup,0o600))
        require(b.read(b.RECEIPT)==backup,'rollback byte mismatch')
        print(json.dumps(dict(ok=True,rollback='exact-old-bytes',mounts=proof)));return
    expected_wire=b.read(READY/'receipt.final.json',NEW_SHA)
    normalized=p.load_prototype(draft(b)['path'],dict(path=str(r.RUNNER),sha256=r.RUNNER_SHA))
    require(p.canonical_json(normalized)==expected_wire,'finalized candidate drift')
    require(p.RUNNER_ASSET.read_bytes()==b.read(r.RUNNER,r.RUNNER_SHA),'runner asset drift')
    wit=b.read(ROOT/'typed-support.json')
    require(wit==witness_bytes(r,b,p),'reviewed witness binding drift')
    witsha=hashlib.sha256(wit).hexdigest()
    argv=['/usr/bin/python3','-I','-S','-B',str(r.PROVISIONER),'--city',str(b.CITY),
        '--receipt-input',str(draft(b)['path']),'--consumer-witness',str(ROOT/'typed-support.json'),
        '--consumer-witness-sha256',witsha,'--'+('check' if mode=='verify' else mode),'--json']
    run=subprocess.run(argv,env=b.ENV,capture_output=True,text=True,stdin=subprocess.DEVNULL,check=False)
    report=json.loads(run.stdout)
    if mode=='check':require(run.returncode==1 and report['drift']==['receipt.sha256'] and not report['ok'],'check must find only receipt SHA drift')
    else:require(run.returncode==0 and report['ok'] and report['drift']==[],'provisioner apply refused')
    require(report['receipt_sha256']==NEW_SELF and report['runner_sha256']==r.RUNNER_SHA,'provisioner result binding')
    print(json.dumps(dict(ok=True,report=report,mounts=proof)))

def main():
    require(globals().get('_SOURCE_SHA'),'source-bound entry required')
    r,b=load()
    if len(sys.argv)==3 and sys.argv[1]=='snapshot':capture(r,b,sys.argv[2]);return
    if len(sys.argv)==3 and sys.argv[1]=='inner':inner(r,b,sys.argv[2]);return
    require(len(sys.argv)==1,'invalid invocation')
    ROOT.mkdir(mode=0o700)
    runner=b.module(r.BUILD/'phase_runner.py','eddf5e1174a7b275abe280e91ea5c8ea0762600d38524ba9631f53fb4874cdf3')
    started=[]
    def invoke(*args):return ['/usr/bin/python3','-I','-S','-B',str(r.LAUNCH),__file__,_SOURCE_SHA,*args]
    def phase(name,argv,timeout=120):
        started.append(name)
        result=runner._run_owned_phase(name=name,argv=argv,cwd=ROOT,environment=b.ENV,timeout=timeout,evidence_path=ROOT/(name+'-phase.json'))
        require(b.successful(result),'phase refusal '+name);return result
    def confined(mode):
        argv=['/usr/bin/bwrap','--ro-bind','/','/']
        if mode in ('apply','rollback'):argv+=['--bind',str(b.RECEIPT.parent),str(b.RECEIPT.parent),'--ro-bind',str(b.RECEIPT.parent/'bin'),str(b.RECEIPT.parent/'bin')]
        return argv+['--unshare-net','--unshare-pid','--new-session','--die-with-parent','--proc','/proc','--dev','/dev','--',*invoke('inner',mode)]
    p=provisioner(r,b);wit=witness_bytes(r,b,p);witsha=hashlib.sha256(wit).hexdigest()
    bytes_out(ROOT/'typed-support.json',wit)
    phase('before',invoke('snapshot','before.json'))
    for name in ('before.json','before.json.provider-pins'):
        require(dependency_image(json.loads(b.read(ROOT/name)))==dependency_image(json.loads(b.read(READY/name))),'readiness evidence input drift')
    old=b.read(b.RECEIPT,OLD_SHA);bytes_out(ROOT/'receipt.before.json',old)
    b.write('backup-metadata.json',b.observe_module().read_file(str(b.RECEIPT))[0])
    check=phase('check',confined('check'),60);b.write('check.json',json.loads(check['stdout']))
    trace=phase('revision',['/home/loucmane/gascity/bin/gc','--city',str(b.CITY),'trace','show','--type','cycle_result','--since','2m','--json'],30)
    records=json.loads(trace['stdout'])['records'];latest=max(records,key=lambda item:item['seq'])
    require(latest['controller_pid']==3150812 and latest['gc_commit']==CORE and latest['config_revision']==draft(b)['revision'] and latest['completion_status']=='completed','live revision drift')
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(latest['ts'].replace('Z','+00:00'))).total_seconds()
    require(0<=age<=120 and latest['fields']['active_template_count']==0,'stale or active controller cycle')
    b.write('revision.json',latest)
    require(b.observe_module().host_observation()==json.loads(b.read(ROOT/'before.json'))['host'],'preapply host drift')
    error=None;rollback='not-needed'
    try:
        result=phase('apply',confined('apply'),60);b.write('apply.json',json.loads(result['stdout']))
        verified=phase('verify',confined('verify'),60);b.write('verify.json',json.loads(verified['stdout']))
        phase('after',invoke('snapshot','after.json'));verify_snapshot(r,b,'after.json',NEW_SHA)
    except BaseException as exc:
        error=exc
        # Never replay apply. Restore only the exact known postimage and only
        # after clean owned-process containment; unknown images remain untouched.
        for name in started:
            record=json.loads(b.read(ROOT/(name+'-phase.json')))
            cleanup=record['cleanup']
            clean=(cleanup['direct_child_reaped'] is True and cleanup['owned_process_group_gone'] is True
                and not cleanup['unexpected_survivors'] and not cleanup['failures'])
            require(clean,'ambiguous phase containment; no automatic rollback: '+name)
        current=hashlib.sha256(b.read(b.RECEIPT)).hexdigest()
        if current==NEW_SHA:
            require(b.observe_module().host_observation()==json.loads(b.read(ROOT/'before.json'))['host'],'host drift; no automatic rollback')
            restored=phase('rollback',confined('rollback'),60);b.write('rollback.json',json.loads(restored['stdout']));rollback='restored'
        else:require(current==OLD_SHA,'unknown partial receipt; no automatic rollback');rollback='already-old'
        phase('restored',invoke('snapshot','restored.json'));verify_snapshot(r,b,'restored.json',OLD_SHA)
    b.write('result.json',dict(ok=error is None,error=None if error is None else str(error),rollback=rollback,
        witness_sha256=witsha,receipt_sha256=NEW_SHA if error is None else OLD_SHA,worker_launched=False,service_transition=False))
    if error:raise RuntimeError('receipt adoption failed; preserved and stopped') from error
    print(json.dumps(dict(ok=True,root=str(ROOT),receipt_installed=True,worker_launched=False)))

if __name__=='__main__':main()
