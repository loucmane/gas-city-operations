"""Exact append-forward startup-note admission; no execution or writes."""
import copy
from datetime import datetime
import hashlib
import json

TASK='ga-e0t1.20'
PARENT='ga-e0t1'


def require(ok,why):
    if not ok:raise RuntimeError(why)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def pair_sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def timestamp(old,new):
    require(isinstance(old,str) and isinstance(new,str),'update timestamp type')
    a=datetime.fromisoformat(old);z=datetime.fromisoformat(new)
    require(a.tzinfo is not None and z.tzinfo is not None and z>=a,'update timestamp regression')


def delta(before,after,amendment,compare):
    require(set(before)==set(after)=={'task','parent'},'amendment pair shape')
    require(before['task'].get('id')==TASK and before['parent'].get('id')==PARENT,'amendment identity')
    require(amendment['after_note']==amendment['before_note']+'\n'+amendment['append_note'],
            'not a single exact append')
    require(before['task'].get('notes')==amendment['before_note'],'startup preimage drift')
    require(after['task'].get('notes')==amendment['after_note'],'startup postimage drift')
    timestamp(before['task']['updated_at'],after['task']['updated_at'])
    expected=copy.deepcopy(before)
    for key in ('notes','updated_at'):
        expected['task'][key]=after['task'][key]
        rows=expected['parent'].get('dependencies',[])
        matches=[r for r in rows if r.get('id')==TASK]
        require(len(matches)==1,'unique task projection')
        require(matches[0].get(key)==before['task'][key],'old task projection drift')
        matches[0][key]=after['task'][key]
    compare(after,expected)
    return dict(before_pair_sha256=pair_sha(before),after_pair_sha256=pair_sha(after),
                task_note_before_sha256=hashlib.sha256(amendment['before_note'].encode()).hexdigest(),
                task_note_after_sha256=hashlib.sha256(amendment['after_note'].encode()).hexdigest())


def accepted(before,after,result,amendment,compare):
    pins=delta(before,after,amendment,compare)
    require(result==dict(pins,ok=True,task=TASK,only_startup_note_appended=True,
                        route_preserved=True,assigned=False,worker_launched=False),'amendment result differs')
    return after
