"""Hash-bound R6 plus the operator-approved cache-atime accounting only."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import types

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-f37t-window')
BASE_SHA='46a72b51324b06f872f618c80d5b3477ae1371ea1989c46f705498df65ed3056'
POLICY_SHA='61c3e38e4475061c658a853036922742ab2ce69d44a4577e3f91490674047783'

def load(path,expected,name):
    assert path.resolve(strict=True)==path
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    try:
        s=os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid==1000 and s.st_nlink==1 and s.st_size<=1024*1024
        raw=b''
        while chunk:=os.read(fd,65536):raw+=chunk
        assert os.fstat(fd)==s and len(raw)==s.st_size and hashlib.sha256(raw).hexdigest()==expected
    finally:os.close(fd)
    m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m
    exec(compile(raw,str(path),'exec',dont_inherit=True),m.__dict__)
    return m

w=load(HERE/'window-base-r11.py',BASE_SHA,'window_r7_base')
p=load(HERE/'cache-atime-policy-r1.py',POLICY_SHA,'window_r7_atime')
w.ROOT=Path('/var/tmp/ga-f37t-window-obs-20260923-r1')
original_save=w.save
original_snapshot=w.snapshot
original_preservation=w.preservation
active_snapshot=None

CACHE=Path('/home/loucmane/gascity/home/cache/repos')

def cache_mounts(text=None):
    rows=[]
    for line in (Path('/proc/self/mountinfo').read_text() if text is None else text).splitlines():
        fields=line.split()
        w.require(len(fields)>=10 and '-' in fields,'mountinfo shape')
        path=w.re.sub(r'\\([0-7]{3})',lambda m:chr(int(m[1],8)),fields[4])
        w.require('\\' not in path,'mount path escape')
        options=set(fields[5].split(','))
        rows.append(dict(id=fields[0],parent=fields[1],device=fields[2],root=fields[3],
            path=path,options=sorted(options),tail=fields[fields.index('-')+1:]))
    covering=[x for x in rows if x['path']=='/' or str(CACHE)==x['path'] or str(CACHE).startswith(x['path']+'/')]
    w.require(bool(covering),'cache covering mount absent')
    longest=max(len(x['path']) for x in covering)
    top=[x for x in covering if len(x['path'])==longest]
    w.require(len(top)==1,'ambiguous cache covering mount')
    selected=top+[x for x in rows if x['path'].startswith(str(CACHE)+'/')]
    w.require(len({x['path'] for x in selected})==len(selected),'ambiguous nested cache mounts')
    for row in selected:
        opts=set(row['options'])
        w.require(len(opts & {'noatime','relatime'})==1 and not (opts & {'strictatime','nodiratime'}),
            'unsupported cache access-time mount policy')
    return sorted(selected,key=lambda x:x['path'])

def clock_sample():
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    first=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    real=time.time_ns()
    last=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    return dict(boot=boot,real_ns=real,boot_before_ns=first,boot_after_ns=last)

def save(name,value):
    if active_snapshot is not None and name==active_snapshot['name']:
        w.require('cache_access_clock' not in value,'unexpected observation clock')
        mounts=cache_mounts()
        w.require(mounts==active_snapshot['mounts'],'cache mount changed during observation')
        value=dict(value,cache_access_clock=dict(start=active_snapshot['start'],end=clock_sample()),
            cache_access_mounts=mounts)
    original_save(name,value)

def snapshot(name,b,o):
    global active_snapshot
    w.require(active_snapshot is None,'nested snapshot')
    active_snapshot=dict(name=name,start=clock_sample(),mounts=cache_mounts())
    try:original_snapshot(name,b,o)
    finally:active_snapshot=None

def preservation(before,after,city_pin,receipt_pin):
    a=json.loads(json.dumps(before));z=json.loads(json.dumps(after))
    w.require('cache_access_clock' in a and 'cache_access_clock' in z,'missing prospective clock envelope')
    ac=a.pop('cache_access_clock');zc=z.pop('cache_access_clock')
    w.require('cache_access_mounts' in a and 'cache_access_mounts' in z,'missing cache mount proof')
    mounts=a.pop('cache_access_mounts')
    w.require(mounts==z.pop('cache_access_mounts') and mounts==cache_mounts(),'cache mount policy drift')
    accounting=p.compare(a['cache'],z['cache'],ac,zc)
    for delta in accounting['deltas']:
        path=str(CACHE) if delta['path']=='.' else str(CACHE/delta['path'])
        covering=[x for x in mounts if x['path']=='/' or path==x['path'] or path.startswith(x['path']+'/')]
        row=max(covering,key=lambda x:len(x['path']))
        w.require(not (set(row['options']) & {'noatime','ro'}),'atime changed on read-only/noatime cache mount')
    accounting['mounts']=mounts
    # Only the comparison copies are aligned, after exhaustive cache validation.
    # Original observations and every timestamp remain preserved, never rewritten.
    z['cache']=a['cache']
    original_preservation(a,z,city_pin,receipt_pin)
    before_sha=w.digest(json.dumps(before,sort_keys=True,separators=(',',':')).encode())
    after_sha=w.digest(json.dumps(after,sort_keys=True,separators=(',',':')).encode())
    result=dict(accounting,before_observation_sha256=before_sha,after_observation_sha256=after_sha,
        base_source_sha256=BASE_SHA,policy_sha256=POLICY_SHA)
    name='cache-atime-'+before_sha+'-'+after_sha+'.json'
    if os.path.lexists(w.ROOT/name):
        w.require(w.record(name)==result,'access accounting collision')
    else:original_save(name,result)

w.save=save
w.snapshot=snapshot
w.preservation=preservation

if __name__=='__main__':
    w.require(globals().get('_SOURCE_SHA'),'bound source launcher required')
    # Inner confined invocations must re-enter this exact wrapper, not bare R6.
    w.__file__=__file__
    w._SOURCE_SHA=_SOURCE_SHA
    w.main()
