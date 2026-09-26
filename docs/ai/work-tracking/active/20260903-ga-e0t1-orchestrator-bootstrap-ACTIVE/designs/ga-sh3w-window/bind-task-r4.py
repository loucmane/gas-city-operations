"""The one ga-sh3w contract binding before the window: gc.work_dir and gc.check_path; never route or resume.

ga-sh3w: replaces the ga-qcwl bind-task-r3.py. The Bead description already is the reviewed R3 brief
(ga-cw-first-window r12, 2067a406, sha256 5cbf64f179cca878e2ecfc2898c44a6b465ffa84cfaae558b2fcb0377b65c942), so nothing is appended. The binding sets
exactly two metadata keys:
- gc.work_dir: the candidate worktree the WORKTREE job created;
- gc.check_path: the check the P10 candidate receipt profile pins. Core's start preflight requires this stamp
  on the driving Bead; the path is executed only by formula (ralph) steps, and ROUTE uses --no-formula.
No option override (opt_*) and no template override is written, since either would change the launch argv the
receipt pins. It runs as its own job BEFORE the window, so no window root may exist yet.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-sh3w-window')
ROOT=Path('/var/tmp/ga-sh3w-bind-20260926-r1')
HELPER=HERE/'window-base-r11.py'
HELPER_SHA='2ac4d49324288e12741d4a2636620828011951c11a8616d45db8e3ffd75082b1'
WORKTREE_RESULT=Path('/var/tmp/ga-sh3w-worktree-20260926-r1/result.json')
WORKTREE_SHA='73a6bfebe19aa191f49fb5c2c53609aa986196e83d8092e771102474afb8b067'
DESCRIPTION_SHA='5cbf64f179cca878e2ecfc2898c44a6b465ffa84cfaae558b2fcb0377b65c942'
BEAD='ga-sh3w'
TARGET='gascity/operations-candidate-worker'
WORK='/home/loucmane/gas-city-ops-candidate-worktrees/ga-sh3w'
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
    assert made==dict(ok=True,worktree=WORK,admin=str(w.ADMIN),base=w.BASE,branch='codex/ga-sh3w-delivery-class',clean=True,
        executor_sha256=WORKTREE_SHA),'worktree job result'
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
    assert [d.get('dependency_type') for d in before.get('dependencies') or []]==['related'],'unexpected Bead edge'
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
