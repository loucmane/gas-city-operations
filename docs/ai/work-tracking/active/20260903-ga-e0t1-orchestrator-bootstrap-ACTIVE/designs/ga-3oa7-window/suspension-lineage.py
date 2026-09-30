"""Validate only this window's supported suspension operations; no live writes."""
import copy
import hashlib
import json
import re
import stat

CITY='/home/loucmane/gascity/city'
GC=['/home/loucmane/gascity/bin/gc','--city',CITY]
ACTIONS={
    'rig-resume':('rig',False,GC+['rig','resume','gascity','--json']),
    'city-resume':('city',False,GC+['resume','--json']),
    'city-suspend':('city',True,GC+['suspend','--json']),
    'rig-suspend':('rig',True,GC+['rig','suspend','gascity','--json']),
}

def require(ok,message):
    if not ok:raise RuntimeError(message)

def unique(pairs):
    out={}
    for k,v in pairs:
        require(k not in out,'duplicate suspension key')
        out[k]=v
    return out

def decode(raw):
    v=json.loads(raw,object_pairs_hook=unique)
    require(isinstance(v,dict) and {'city','rigs','updated_at'} <= set(v)
        and set(v) <= {'city','rigs','agents','updated_at'},'suspension schema')
    require(isinstance(v['updated_at'],str) and re.fullmatch(
        r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,9})?Z',v['updated_at']),
        'suspension timestamp shape')
    def override(o):
        require(isinstance(o,dict) and set(o)=={'suspended'}
            and type(o['suspended']) is bool,'unreviewed suspension preference')
    override(v['city'])
    for scope in ('rigs','agents'):
        if scope in v:
            require(isinstance(v[scope],dict) and bool(v[scope]),'empty/null suspension map')
            for name,o in v[scope].items():
                require(isinstance(name,str) and name,'suspension name')
                override(o)
    require('gascity' in v['rigs'],'missing target rig')
    return v

def image(record):
    require(set(record)=={'raw','pin'},'suspension record shape')
    raw=record['raw'].encode('utf-8'); pin=record['pin']; m=pin['metadata']
    require(set(pin)=={'sha256','metadata'} and pin['sha256']==hashlib.sha256(raw).hexdigest(),
        'suspension raw digest')
    require(set(m)=={'device','inode','uid','gid','mode','type','nlink','size',
        'mtime_ns','ctime_ns','atime_ns'},'suspension metadata fields')
    require(all(type(x) is int for x in m.values()),'suspension metadata types')
    require(m['uid']==m['gid']==1000 and m['mode']==0o644 and m['type']==stat.S_IFREG
        and m['nlink']==1 and m['size']==len(raw),'suspension authority')
    return decode(raw)

def step(before,after,action):
    require(action in ACTIONS,'unreviewed suspension operation')
    a=image(before); z=image(after)
    scope,want,_=ACTIONS[action]
    current=a['city'] if scope=='city' else a['rigs']['gascity']
    if current['suspended']==want:
        require(before==after,'suspension no-op changed')
        return
    expected=copy.deepcopy(a)
    target=expected['city'] if scope=='city' else expected['rigs']['gascity']
    target['suspended']=want
    expected['updated_at']=z['updated_at']
    require(expected==z,'unrelated suspension preference changed')
    x=before['pin']['metadata']; y=after['pin']['metadata']
    for k in ('device','uid','gid','mode','type','nlink'):
        require(x[k]==y[k],'suspension authority changed')
    require(x['inode']!=y['inode'],'suspension write not atomic replacement')

def phase(intent,result,action,cwd):
    argv=ACTIONS[action][2]
    require(intent==dict(phase=action,argv=argv,cwd=cwd),'suspension intent binding')
    require(all(result.get(k)==intent[k] for k in ('phase','argv','cwd')),
        'suspension command binding')
    c=result['cleanup']
    require(result['exit_code']==0 and not result['timed_out'] and not result['primary_error']
        and result['stderr']=='' and c['direct_child_reaped'] and c['owned_process_group_gone']
        and not c['failures'] and not c['unexpected_survivors'],'suspension command failure')

def chain(baseline,records,current,cwd,terminal=False):
    b=image(baseline)
    require(b['city']['suspended'] and all(x['suspended'] for x in b['rigs'].values()),
        'baseline not fully suspended')
    previous=baseline; seen=[]
    for record in records:
        require(set(record)=={'action','before','after','intent','result'},'suspension event shape')
        action=record['action']
        require(action in ACTIONS and action not in seen,'repeated/unreviewed suspension action')
        allowed=(['rig-resume'] if not seen else
                 ['city-resume','rig-suspend'] if seen==['rig-resume'] else
                 ['city-suspend'] if seen==['rig-resume','city-resume'] else
                 ['rig-suspend'] if seen==['rig-resume','city-resume','city-suspend'] else [])
        require(action in allowed,'suspension operation order')
        require(record['before']==previous,'suspension predecessor drift')
        phase(record['intent'],record['result'],action,cwd)
        step(record['before'],record['after'],action)
        previous=record['after'];seen.append(action)
    image(current)
    require(previous==current,'unrecorded suspension mutation')
    if terminal:
        z=image(current); expected=copy.deepcopy(b); expected['updated_at']=z['updated_at']
        require(z==expected,'suspension baseline not restored')
    return current['pin']
