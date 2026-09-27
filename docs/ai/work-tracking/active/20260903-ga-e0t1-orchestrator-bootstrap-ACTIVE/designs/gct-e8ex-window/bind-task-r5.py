"""The one gct-mbg6 contract binding before the window: gc.work_dir only; never route or resume.

gct-mbg6: bind-task-r5.py as reviewed for ga-x7lx and ga-3oa7, retargeted to the Template codex task. The Bead
description is the short gct-e8ex task brief (sha256 c66bab3c40693762c54c998efa8b5f8bab2813391ba15a9318a00b7b33f2ef0c): the reviewed r6 gct-e8ex brief head and tail,
verbatim, with the stop check and a pointer to six closed holders (designs/gct-e8ex-split). The task
carries no dependency edge, so `bd show` prints no embedded record.
Template window (twelfth successor): the codex agent is not in the provisioning receipt, so the Core start
preflight does not gate it and no gc.check_path stamp is written; the binding sets gc.work_dir only. There is
no info/exclude check: the codex worker cannot write the Template .git (s1 r5) and leaves its changes
uncommitted for a reviewed Template intake. No option or template override is written on the Bead (the
narrower codex choice comes from the PREP overlay). It runs as its own job BEFORE the window, so no window
root may exist yet.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-e8ex-window')
ROOT=Path('/var/tmp/gct-mbg6-bind-20260926-r2')
HELPER=HERE/'window-base-r11.py'
HELPER_SHA='eba3708e279884d7e0e8e0ff8e0eea9a05f103abac606e62c1155a6db55c506b'
WORKTREE_RESULT=Path('/var/tmp/gct-mbg6-worktree-20260926-r1/result.json')
WORKTREE_SHA='310f75d0d1e29e99a8305a03caa4245e81dd445045986b60eca50bc8bb0108aa'
DESCRIPTION_SHA='c66bab3c40693762c54c998efa8b5f8bab2813391ba15a9318a00b7b33f2ef0c'
BEAD='gct-mbg6'
TARGET='gas-city-template/codex'
WORK='/home/loucmane/gas-city-template-worktrees/gct-mbg6'

def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    raw=HELPER.read_bytes();assert hashlib.sha256(raw).hexdigest()==HELPER_SHA
    w=types.ModuleType('binding_window');w.__file__=str(HELPER)
    exec(compile(raw,str(HELPER),'exec',dont_inherit=True),w.__dict__)
    w._SOURCE_SHA=HELPER_SHA
    b,o,owned=w.load_support();w.pins()
    made=json.loads(w.read(WORKTREE_RESULT))
    assert made==dict(ok=True,worktree=WORK,admin=str(w.ADMIN),base=w.BASE,branch='codex/gct-mbg6-template-candidate-lane',clean=True,
        executor_sha256=WORKTREE_SHA),'worktree job result'
    assert not os.path.lexists(w.ROOT), 'binding must precede the window'
    w.read(w.CITY/'city.toml',w.CITY_SHA[0]);w.read(w.RECEIPT,w.RECEIPT_SHA[0])
    ROOT.mkdir(mode=0o700);w.ROOT=ROOT
    def run(name,args):return w.phase(name,args,b,owned)
    def bead(name):
        rows=json.loads(run(name,w.GC+['--rig','gas-city-template','bd','show',BEAD,'--json'])['stdout'])
        assert isinstance(rows,list) and len(rows)==1 and rows[0]['id']==BEAD
        return rows[0]
    before_host=w.host(o)
    before=bead('task-before-read');w.save('task-before.json',before)
    assert before['status']=='open' and not before.get('assignee') and not before.get('metadata')
    assert not before.get('notes'),'task has notes before the first session'
    assert hashlib.sha256(before['description'].encode()).hexdigest()==DESCRIPTION_SHA,'description is not the reviewed brief'
    assert not before.get('dependencies') and not before.get('dependents'),'unexpected Bead edge'
    assert before.get('dependency_count',0)==0 and before.get('dependent_count',0)==0 and before.get('comment_count',0)==0,'embedded records'
    metadata={'gc.work_dir':WORK}
    argv=w.GC+['--rig','gas-city-template','bd','update',BEAD]
    for key,value in metadata.items():argv+=['--set-metadata',key+'='+value]
    w.save('binding-intent.json',dict(before=before,metadata=metadata,description_sha256=DESCRIPTION_SHA,
        executor_sha256=_SOURCE_SHA,worker_launched=False))
    run('task-bind',argv)
    after=bead('task-after-read');w.save('task-after.json',after)
    assert after['metadata']==metadata
    for key in set(before)|set(after):
        if key not in ('metadata','updated_at'):
            assert before.get(key)==after.get(key),key
    assert w.host(o)==before_host
    w.save('result.json',dict(ok=True,bead=BEAD,contract_bound=True,routed=False,assigned=False,
        worker_launched=False,live_configuration_changed=False))
    print(json.dumps(w.record('result.json')))

if __name__=='__main__':main()
