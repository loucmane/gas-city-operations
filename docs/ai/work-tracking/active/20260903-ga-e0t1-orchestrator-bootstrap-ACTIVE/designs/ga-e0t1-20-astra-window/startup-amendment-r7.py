"""One reviewed task-note append before the worker-window freeze, never route/claim."""
import hashlib
import json
import os
from pathlib import Path
import sys
import types

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
ROOT=Path('/var/tmp/ga-e0t1.20-startup-amendment-20260928-r7')
WINDOW=Path('/var/tmp/ga-e0t1.20-window-20260928-r7')
BASE_SHA='7d0ed613bde7dbee7639e328e9fae58f91038bc2744faebb2d854a2daf84d830'
LEGACY_SHA='0daa6bf64e8342d04a9992f327db2f2835c88c4a4ccfca0e2bae09b6b76e2520'
CONTRACT_SHA='85963b400979ba14561bc70e6a6d03b189fb641db5650788bd2a0a5906f77ca9'
AMENDMENT_SHA='010322f79a02f5b74a9c15fe17d97c755910b556e7349eecf06cab98cb1988a6'


def load(path,pin):
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pin,'amendment source binding'
    m=types.ModuleType(path.stem);m.__file__=str(path)
    exec(compile(raw,str(path),'exec',dont_inherit=True),m.__dict__)
    return m


def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    w=load(HERE/'window-base-r11.py',BASE_SHA);w._SOURCE_SHA=BASE_SHA
    b,o,owned=w.load_support();w.pins()
    assert not os.path.lexists(WINDOW),'amendment must precede window'
    w.read(w.CITY/'city.toml',w.CITY_SHA[0]);w.read(w.RECEIPT,w.RECEIPT_SHA[0])
    before_host=w.host(o)
    legacy=w.module(HERE/'legacy-continuation-r4.py',LEGACY_SHA)
    exact=w.module(HERE/'startup-amendment-contract-r5.py',CONTRACT_SHA)
    amendment=json.loads(w.read(HERE/'startup-amendment-r7.json',AMENDMENT_SHA))
    completed={p:json.loads(w.read(p,pin)) for p,pin in legacy.PINS.items()}
    done=completed[legacy.COMPLETED/'result.json']
    assert done['ok'] is True and done['sole_target_ready'] is True
    assert done['parent_prerequisites_preserved'] is True and done['existing_route_preserved'] is True
    assert done['worker_launched'] is False
    ROOT.mkdir(mode=0o700);w.ROOT=ROOT
    before=legacy.pair(w,b,owned,'before')
    prior=w.module(HERE/'recovered-claim-r7.py','54b9cf8cd493f3abfabc087231605b7900210c7d9007005a64411d718073e22a')
    prior.verify(w,before,legacy.normalized,legacy.compare_pair)
    w.save('before.json',before)
    assert before['task']['notes']==amendment['before_note'],'append preimage'
    assert before['task']['status']=='open' and not before['task'].get('assignee')
    w.save('intent.json',dict(executor_sha256=_SOURCE_SHA,amendment_sha256=AMENDMENT_SHA,
                             before_pair_sha256=exact.pair_sha(before),replay=False))
    w.phase('append-startup-note',w.GC+['--rig','gascity','bd','update',exact.TASK,
        '--append-notes',amendment['append_note']],b,owned,timeout=45)
    after=legacy.pair(w,b,owned,'after');w.save('after.json',after)
    pins=exact.delta(before,after,amendment,legacy.compare_pair)
    w.contract().validate_task(after['task'],'routed')
    legacy.compare_pair(legacy.pair(w,b,owned,'repeat'),after)
    assert w.host(o)==before_host,'amendment host drift'
    w.read(w.CITY/'city.toml',w.CITY_SHA[0]);w.read(w.RECEIPT,w.RECEIPT_SHA[0])
    w.complete_containment()
    w.save('result.json',dict(pins,ok=True,task=exact.TASK,only_startup_note_appended=True,
                             route_preserved=True,assigned=False,worker_launched=False))
    print(json.dumps(w.record('result.json')))


if __name__=='__main__':main()
