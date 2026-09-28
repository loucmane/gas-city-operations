"""Actual-host read-only pre-mutation proof. Never calls an executor main."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

root=Path(sys.argv[1]);manifest=json.loads((root/'assembly.json').read_bytes())
for name,pin in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin,name
def load(name):
    raw=(root/name).read_bytes();m=types.ModuleType(name);m.__file__=str(root/name)
    exec(compile(raw,m.__file__,'exec',dont_inherit=True),m.__dict__)
    return m
w=load('window-base-r11.py');w.HERE=root
c=load('contract.py');v=load('startup-validation.py');i=load('candidate-inspect.py')
p=load('worker-startup-r7.py');recovery=load('recovered-claim-r7.py')
legacy=load('legacy-continuation-r4.py');workspace=load('workspace-r7.py')
w.pins()
load('runtime-process-r7.py').verify_assets(p.read_regular)
b,o,owned=w.load_support();host=w.host(o)
env=dict(o.ENV,GC_HOME='/home/loucmane/gascity/home',GIT_OPTIONAL_LOCKS='0',BD_DISABLE_METRICS='1')
for name in list(env):
    if name.startswith('BEADS_'):del env[name]
def run(argv):
    r=subprocess.run(argv,env=env,cwd=w.WORK,capture_output=True,timeout=90)
    assert r.returncode==0,(argv,r.returncode,r.stderr.decode())
    return r.stdout
pair={name:json.loads(run(w.GC+['--rig','gascity','bd','show',bead,'--json']))[0]
      for name,bead in [('task','ga-e0t1.20'),('parent','ga-e0t1')]}
recovery.verify(w,pair,legacy.normalized,legacy.compare_pair)
amendment=json.loads((root/'startup-amendment-r7.json').read_bytes())
assert pair['task']['notes']==amendment['before_note']
projected=json.loads(json.dumps(pair['task']));projected['notes']=amendment['after_note']
c.validate_task(projected,'routed')
census=json.loads(run(w.GC+['session','list','--json']));assert census['sessions']==[]
status=json.loads(run(w.GC+['status','--json']))
assert status['suspended'] and all(x['suspended'] for x in status['rigs'])
head=run(w.HARDENED+['rev-parse','--verify','HEAD^{commit}']).decode().strip();assert head==w.BASE
raw_status=run(w.HARDENED+['status','--porcelain=v1','--ignored','--untracked-files=all','-z'])
c.validate_rule_status(raw_status)
before=v.workspace_image(w.WORK,i.file_bytes)
workspace.verify(w,before,c.RUNTIME_IMAGE)
assert before==v.workspace_image(w.WORK,i.file_bytes)
assert not w.ROOT.exists()
print(json.dumps(dict(ok=True,phase='readonly-pre-mutation',native_claim_history_bound=True,
    exact_future_amendment_admitted=True,workspace_entries=len(before),workspace_unchanged=True,
    status_sha256=hashlib.sha256(raw_status).hexdigest(),base=head,
    zero_sessions=True,all_rigs_suspended=True,actual_host_assets_verified=True,
    source_release_sent=False,worker_launched=False,host=host),sort_keys=True))
