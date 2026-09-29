"""Bind only the Operations candidate workspace and exact startup contract.

The existing nonblocking parent-child edge is verified, not removed. No receipt,
claim, route, runtime configuration or worker implementation is created here.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-21-c1-package')
ROOT=Path('/var/tmp/ga-e0t1.21-bind-20260929-r1')
HELPER=HERE/'window-base.py'
HELPER_SHA='1162d4a87d75594520ee3b9e21f8958ebddebc55cb0b9b9729747b67b7ef5cd4'
WORKTREE_RESULT=Path('/var/tmp/ga-e0t1.21-worktree-20260929-r1/result.json')
WORKTREE_SHA='704e6cf021d19a081182b9768f7e07f31635a73c9639ce7c40bfff8ba0452b16'
DESCRIPTION_SHA='06d328b873c9c46622dd24ac6a9af6ce56c5701f790f5cd5c33db49e891eb7f8'
BEAD='ga-e0t1.21'
TARGET='gascity/codex'
WORK='/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.21'

def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    raw=HELPER.read_bytes();assert hashlib.sha256(raw).hexdigest()==HELPER_SHA
    w=types.ModuleType('binding_window');w.__file__=str(HELPER)
    exec(compile(raw,str(HELPER),'exec',dont_inherit=True),w.__dict__)
    w._SOURCE_SHA=HELPER_SHA
    b,o,owned=w.load_support();w.pins()
    made=json.loads(w.read(WORKTREE_RESULT,
        '704e6cf021d19a081182b9768f7e07f31635a73c9639ce7c40bfff8ba0452b16'))
    assert made['ok'] is True and made['worker_launched'] is False and made['tracked_clean'] is True
    assert made['worktree']==WORK and made['admin']==str(w.ADMIN) and made['base']==w.BASE
    assert made['branch']=='codex/ga-e0t1.21-c1-package'
    assert made['local_rules']==w.contract().RULES and made['default_rules_unchanged'] is True
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
    w.contract().validate_task(before,'unbound')
    metadata={'gc.work_dir':WORK}
    note=w.contract().BIND_NOTE
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
    assert after['notes']==w.contract().BOUND_NOTE
    w.contract().validate_task(after,'bound')
    w.contract().validate_binding_delta(before,after)
    assert w.host(o)==before_host
    w.save('result.json',dict(ok=True,bead=BEAD,contract_bound=True,routed=False,assigned=False,
        worker_launched=False,live_configuration_changed=False))
    print(json.dumps(w.record('result.json')))

if __name__=='__main__':main()
