"""Pure exact-route regeneration accounting; no mutation or timestamp writes."""
import copy
from datetime import datetime
import json

ORDER=('stage-reload','restore-reload')

def require(ok,message):
    if not ok:raise RuntimeError(message)

def valid_chain(chain):
    require(type(chain) is list and chain==list(ORDER[:len(chain)]) and len(chain)<=2,
            'route chain order')

def validate_event(event,name,r,p,revisions,argv):
    require(event['name']==name and name in ORDER,'reload identity')
    phase=event['phase'];cleanup=phase['cleanup'];accepted=event['accepted']
    require(phase['phase']==name and phase['argv']==argv,'reload command identity')
    require(phase['exit_code']==0 and not phase['timed_out'] and not phase['primary_error']
        and cleanup['direct_child_reaped'] and cleanup['owned_process_group_gone']
        and not cleanup['failures'] and not cleanup['unexpected_survivors'],
        'reload containment/success')
    ack=accepted['ack'];cycle=accepted['cycle']
    revision=revisions[1 if name=='stage-reload' else 0]
    require(json.loads(phase['stdout'])==ack and ack['ok'] is True
        and ack['async'] is False and ack['soft'] is False
        and ack['outcome']=='applied' and ack['revision']==revision,'reload acknowledgement')
    require(cycle['controller_pid']==3150812 and cycle['config_revision']==revision
        and cycle['completion_status']=='completed' and cycle['fields']['active_template_count']==0,
        'reload cycle identity')
    trace=event['trace'];cleanup=trace['cleanup']
    suffix=trace['phase'].removeprefix(name+'-trace-')
    require(trace['phase'].startswith(name+'-trace-') and suffix.isascii() and suffix.isdigit()
        and trace['argv']==argv[:-2]+['trace','show','--type','cycle_result','--since','2m','--json']
        and trace['cwd']==phase['cwd'],'trace command identity')
    require(trace['exit_code']==0 and not trace['timed_out'] and not trace['primary_error']
        and cleanup['direct_child_reaped'] and cleanup['owned_process_group_gone']
        and not cleanup['failures'] and not cleanup['unexpected_survivors'],'trace containment/success')
    rows=json.loads(trace['stdout'])['records']
    require(rows and max(rows,key=lambda row:row['seq'])==cycle,'accepted cycle trace membership')
    bounds=p.bounds(event['before_clock'],event['after_clock'])
    observed=event['observed_at_ns']
    require(type(observed) is int and bounds['earliest_ns']<=observed<=bounds['latest_ns'],
        'cycle observation clock binding')
    stamp=datetime.fromisoformat(cycle['ts'].replace('Z','+00:00'))
    require(stamp.tzinfo is not None and 0<=observed-int(stamp.timestamp()*10**9)<=120*10**9,
        'recorded cycle freshness')
    return r.compare_routes(event['before'],event['after'],bounds)

def project(before,after,events,r,p,revisions,argv):
    a=copy.deepcopy(before);z=copy.deepcopy(after)
    first=a.pop('generated_routes');last=z.pop('generated_routes')
    start=a.pop('generated_route_chain');end=z.pop('generated_route_chain')
    valid_chain(start);valid_chain(end)
    require(end[:len(start)]==start and len(end)>=len(start),'route chain prefix')
    r.route_authority(first);r.route_authority(last)
    city=r.RIGS[0][1]
    for snapshot,rows in ((a,first),(z,last)):
        require(snapshot['directories']['runtime_children']['.beads']['routes.jsonl']==rows[city]['metadata']
            and snapshot['directories']['city']['.beads']==rows[city]['parent'],'route snapshot mirror')
    cursor=first;previous_clock=before['cache_access_clock'];proof=[]
    for name in end[len(start):]:
        event=events[name]
        require(event['before']==cursor,'route event preimage gap')
        p.bounds(previous_clock,event['before_clock'])
        changes=validate_event(event,name,r,p,revisions,argv)
        p.bounds(before['cache_access_clock'],event['after_clock'])
        cursor=event['after'];previous_clock=event['after_clock'];proof.extend(changes)
    p.bounds(previous_clock,after['cache_access_clock'])
    require(cursor==last,'unobserved generated route mutation')
    # Only identities validated through successful, byte-preserving native
    # reloads are aligned in copies. Root atime and all unrelated data remain.
    if proof:
        z['directories']['runtime_children']['.beads']['routes.jsonl']['inode']=a['directories']['runtime_children']['.beads']['routes.jsonl']['inode']
        for key in ('mtime_ns','ctime_ns'):
            z['directories']['city']['.beads'][key]=a['directories']['city']['.beads'][key]
        # R6 intentionally ignores route-file timestamps in runtime_children.
        # Do not introduce any additional normalization here.
    return a,z,dict(reloads=end[len(start):],changes=proof)
