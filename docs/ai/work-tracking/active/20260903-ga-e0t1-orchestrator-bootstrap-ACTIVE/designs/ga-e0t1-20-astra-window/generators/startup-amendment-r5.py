"""One reviewed task-note append before the worker-window freeze, never route/claim."""
import hashlib
import json
import os
from pathlib import Path
import sys
import types

HERE=Path('PACKAGE')
ROOT=Path('/var/tmp/ga-e0t1.20-startup-amendment-20260928-r5')
WINDOW=Path('/var/tmp/ga-e0t1.20-window-20260928-r5')
BASE_SHA='WINDOW_BASE_SHA'
LEGACY_SHA='LEGACY_CONTINUATION_SHA'
CONTRACT_SHA='AMENDMENT_CONTRACT_SHA'
AMENDMENT_SHA='AMENDMENT_DATA_SHA'


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
    amendment=json.loads(w.read(HERE/'startup-amendment-r5.json',AMENDMENT_SHA))
    completed={p:json.loads(w.read(p,pin)) for p,pin in legacy.PINS.items()}
    done=completed[legacy.COMPLETED/'result.json']
    assert done['ok'] is True and done['sole_target_ready'] is True
    assert done['parent_prerequisites_preserved'] is True and done['existing_route_preserved'] is True
    assert done['worker_launched'] is False
    ROOT.mkdir(mode=0o700);w.ROOT=ROOT
    before=legacy.pair(w,b,owned,'before')
    legacy.compare_pair(before,completed[legacy.COMPLETED/'final.json'],parent_audit=True)
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
