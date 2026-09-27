"""The one ga-e0t1.20 contract binding before the window: gc.work_dir only; never route or resume.

ga-e0t1.20: bind-task-r5.py as reviewed for ga-x7lx and ga-3oa7, retargeted to the Template codex task. The Bead
description is the short gct-e8ex task brief (sha256 136f2b728a6713c123dab4a79a6fb34934e578bf01cf57658603afdb46166955): the reviewed r6 gct-e8ex brief head and tail,
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

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
ROOT=Path('/var/tmp/ga-e0t1.20-bind-20260927-r1')
HELPER=HERE/'window-base-r11.py'
HELPER_SHA='889616086d8f084d5a4ff13c98c30d7d20393336e462de83c17b157e5899f261'
WORKTREE_RESULT=Path('/var/tmp/ga-e0t1.20-worktree-20260927-r1/result.json')
WORKTREE_SHA='9760bb7c2f8de075619e9c8d0b53e03f4b9d40a07aa45dc5c26380ad1cbec4af'
DESCRIPTION_SHA='136f2b728a6713c123dab4a79a6fb34934e578bf01cf57658603afdb46166955'
BEAD='ga-e0t1.20'
TARGET='gascity/codex'
WORK='/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'

def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    raw=HELPER.read_bytes();assert hashlib.sha256(raw).hexdigest()==HELPER_SHA
    w=types.ModuleType('binding_window');w.__file__=str(HELPER)
    exec(compile(raw,str(HELPER),'exec',dont_inherit=True),w.__dict__)
    w._SOURCE_SHA=HELPER_SHA
    b,o,owned=w.load_support();w.pins()
    made=json.loads(w.read(WORKTREE_RESULT,
        '9760bb7c2f8de075619e9c8d0b53e03f4b9d40a07aa45dc5c26380ad1cbec4af'))
    assert made['ok'] is True and made['worker_launched'] is False and made['tracked_clean'] is True
    assert made['worktree']==WORK and made['admin']==str(w.ADMIN) and made['base']==w.BASE
    assert made['branch']=='codex/ga-e0t1.20-c1-close-admission'
    assert made['local_rules']==w.contract().RULES and made['default_rules_unchanged'] is True
    assert not os.path.lexists(w.ROOT), 'binding must precede the window'
    w.read(w.CITY/'city.toml',w.CITY_SHA[0]);w.read(w.RECEIPT,w.RECEIPT_SHA[0])
    raise RuntimeError('DRAFT package has no execution admission')
    ROOT.mkdir(mode=0o700);w.ROOT=ROOT
    def run(name,args):return w.phase(name,args,b,owned)
    def bead(name):
        rows=json.loads(run(name,w.GC+['--rig','gascity','bd','show',BEAD,'--json'])['stdout'])
        assert isinstance(rows,list) and len(rows)==1 and rows[0]['id']==BEAD
        return rows[0]
    before_host=w.host(o)
    before=bead('task-before-read');w.save('task-before.json',before)
    w.contract().validate_task(before,'unbound')
    metadata={'gc.work_dir':WORK}
    note=w.contract().BOUND_NOTE
    (ROOT/'sandbox-negative').mkdir(mode=0o700)
    w.save('sandbox-negative-fixture.json',dict(path=str(ROOT/'sandbox-negative'),
        purpose='one new sacrificial file must be denied by the actual worker sandbox'))
    argv=w.GC+['--rig','gascity','bd','update',BEAD]
    for key,value in metadata.items():argv+=['--set-metadata',key+'='+value]
    w.save('binding-intent.json',dict(before=before,metadata=metadata,description_sha256=DESCRIPTION_SHA,
        executor_sha256=_SOURCE_SHA,worker_launched=False,note=note))
    argv += ['--append-notes',note]
    run('task-bind',argv)
    after=bead('task-after-read');w.save('task-after.json',after)
    assert after['metadata']==metadata
    assert after['notes']==note
    w.contract().validate_task(after,'bound')
    for key in set(before)|set(after):
        if key not in ('metadata','notes','updated_at'):
            assert before.get(key)==after.get(key),key
    assert w.host(o)==before_host
    w.save('result.json',dict(ok=True,bead=BEAD,contract_bound=True,routed=False,assigned=False,
        worker_launched=False,live_configuration_changed=False))
    print(json.dumps(w.record('result.json')))

if __name__=='__main__':main()
