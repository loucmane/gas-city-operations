"""Prospective, bounded cache access-time accounting; never writes timestamps."""
from pathlib import PurePosixPath

MAX_WINDOW_NS=4*3600*10**9
REALTIME_SLACK_NS=10**9
MAX_OFFSET_SPREAD_NS=100_000_000

def require(ok,message):
    if not ok:raise RuntimeError(message)

def integer(value):
    require(type(value) is int and value>=0,'invalid nonnegative timestamp')
    return value

def bounds(before,after):
    require(set(before)==set(after)=={'start','end'},'clock envelope shape')
    samples=[before['start'],before['end'],after['start'],after['end']]
    low=[];high=[];previous=None;boot=None
    for s in samples:
        require(set(s)=={'boot','real_ns','boot_before_ns','boot_after_ns'},'clock sample shape')
        require(isinstance(s['boot'],str) and bool(s['boot']),'boot identifier')
        if boot is None:boot=s['boot']
        require(s['boot']==boot,'clock boot drift')
        a=integer(s['boot_before_ns']);z=integer(s['boot_after_ns']);r=integer(s['real_ns'])
        require(a<=z and z-a<=MAX_OFFSET_SPREAD_NS,'ambiguous clock sample')
        require(previous is None or a>=previous,'clock samples not ordered')
        previous=z;low.append(r-z);high.append(r-a)
    # Conservative interval union includes sampling uncertainty. This detects
    # bounded observed disagreement, not a transient step reversed between samples.
    require(max(high)-min(low)<=MAX_OFFSET_SPREAD_NS,'clock offset disagreement')
    require(samples[-1]['boot_after_ns']-samples[0]['boot_before_ns']<=MAX_WINDOW_NS,
            'fixed four-hour window expired')
    return dict(boot=boot,earliest_ns=max(0,samples[0]['real_ns']-REALTIME_SLACK_NS),
        latest_ns=samples[-1]['real_ns']+REALTIME_SLACK_NS,
        elapsed_ns=samples[-1]['boot_after_ns']-samples[0]['boot_before_ns'],
        offset_spread_ns=max(high)-min(low),realtime_slack_ns=REALTIME_SLACK_NS)

def compare(before,after,before_clock,after_clock):
    window=bounds(before_clock,after_clock)
    require(set(before)==set(after)=={'sha256','inventory','entries','file_bytes'},'cache image shape')
    require({k:v for k,v in before.items() if k!='inventory'}==
            {k:v for k,v in after.items() if k!='inventory'},'cache content/count drift')
    a=before['inventory'];z=after['inventory']
    require(isinstance(a,dict) and isinstance(z,dict) and set(a)==set(z),'cache inventory drift')
    deltas=[]
    for path in sorted(a):
        require(isinstance(path,str) and (path=='.' or (path and
            not path.startswith('/') and '..' not in PurePosixPath(path).parts
            and str(PurePosixPath(path))==path)),'cache path alias')
        first=a[path];last=z[path]
        require(isinstance(first,dict) and isinstance(last,dict) and
                'atime_ns' in first and 'atime_ns' in last,'missing cache access timestamp')
        require({k:v for k,v in first.items() if k!='atime_ns'}==
                {k:v for k,v in last.items() if k!='atime_ns'},'non-atime cache metadata drift: '+path)
        old=integer(first['atime_ns']);new=integer(last['atime_ns'])
        if old==new:continue
        require(new>old and window['earliest_ns']<=new<=window['latest_ns'],
                'cache atime outside approved window: '+path)
        deltas.append(dict(path=path,before_ns=old,after_ns=new))
    return dict(schema='gc.cache-access-time-accounting.v1',window=window,deltas=deltas,
        attribution='read-compatible only; no individual process or syscall attribution')
