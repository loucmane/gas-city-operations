"""The one ga-x7lx contract binding before the window: gc.work_dir and gc.check_path; never route or resume.

ga-x7lx: bind-task-r5.py replaces the ga-sh3w bind-task-r4.py. The Bead description is the short task brief
(sha256 acc57fd5fd1f095d8d6df6a4003313c7e53219e6cddde5dd1061ed8f7d36e610): the reviewed r12 R3 brief head and working rules, verbatim, and a pointer to the closed
spec holders ga-lpo2 and ga-r2el; together they reassemble to the r12 brief. The task carries no dependency edge,
so `bd show` prints no embedded record. The binding sets exactly two metadata keys:
- gc.work_dir: the candidate worktree the WORKTREE job created;
- gc.check_path: the check the P10 candidate receipt profile pins. Core's start preflight requires this stamp
  on the driving Bead; the path is executed only by formula (ralph) steps, and ROUTE uses --no-formula.
No option override (opt_*) and no template override is written, since either would change the launch argv the
receipt pins. The ga-sh3w EXCLUDE job already appended the Core skill-link line, so the live common info/exclude
must be exactly its postimage. It runs as its own job BEFORE the window, so no window root may exist yet.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-x7lx-window')
ROOT=Path('/var/tmp/ga-x7lx-bind-20260926-r1')
HELPER=HERE/'window-base-r11.py'
HELPER_SHA='328004a1da28c3cba3c693facafc395a2656b6d92c39fc0ca7e3453f17b9e54f'
WORKTREE_RESULT=Path('/var/tmp/ga-x7lx-worktree-20260926-r1/result.json')
WORKTREE_SHA='6b2255540aa95639a4c9311fe2c493f69daf5db7388c6123670cd43bf12a8a4a'
EXCLUDE=Path('/home/loucmane/gas-city-ops/.git/info/exclude')
EXCLUDE_AFTER='4ef8e39849f5cfe486486339b37f5947d2ff77786250eeeebb7be57170a05bbd'
DESCRIPTION_SHA='acc57fd5fd1f095d8d6df6a4003313c7e53219e6cddde5dd1061ed8f7d36e610'
BEAD='ga-x7lx'
TARGET='gascity/operations-candidate-worker'
WORK='/home/loucmane/gas-city-ops-candidate-worktrees/ga-x7lx'
CHECK='/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/gascity/assets/scripts/checks/build-artifact-valid.sh'

def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    raw=HELPER.read_bytes();assert hashlib.sha256(raw).hexdigest()==HELPER_SHA
    w=types.ModuleType('binding_window');w.__file__=str(HELPER)
    exec(compile(raw,str(HELPER),'exec',dont_inherit=True),w.__dict__)
    w._SOURCE_SHA=HELPER_SHA
    b,o,owned=w.load_support();w.pins()
    made=json.loads(w.read(WORKTREE_RESULT))
    assert made==dict(ok=True,worktree=WORK,admin=str(w.ADMIN),base=w.BASE,branch='codex/ga-x7lx-delivery-class',clean=True,
        executor_sha256=WORKTREE_SHA),'worktree job result'
    s=EXCLUDE.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_uid==1000,'exclude authority'
    assert hashlib.sha256(EXCLUDE.read_bytes()).hexdigest()==EXCLUDE_AFTER,'common info/exclude is not the EXCLUDE postimage'
    assert not os.path.lexists(w.ROOT), 'binding must precede the window'
    w.read(w.CITY/'city.toml',w.CITY_SHA[0]);w.read(w.RECEIPT,w.RECEIPT_SHA[0])
    ROOT.mkdir(mode=0o700);w.ROOT=ROOT
    def run(name,args):return w.phase(name,args,b,owned)
    def bead(name):
        rows=json.loads(run(name,w.GC+['--rig','gascity','bd','show',BEAD,'--json'])['stdout'])
        assert isinstance(rows,list) and len(rows)==1 and rows[0]['id']==BEAD
        return rows[0]
    before_host=w.host(o)
    before=bead('task-before-read');w.save('task-before.json',before)
    assert before['status']=='open' and not before.get('assignee') and not before.get('metadata')
    assert hashlib.sha256(before['description'].encode()).hexdigest()==DESCRIPTION_SHA,'description is not the reviewed brief'
    assert not before.get('dependencies'),'unexpected Bead edge'
    metadata={'gc.work_dir':WORK,'gc.check_path':CHECK}
    argv=w.GC+['--rig','gascity','bd','update',BEAD]
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
