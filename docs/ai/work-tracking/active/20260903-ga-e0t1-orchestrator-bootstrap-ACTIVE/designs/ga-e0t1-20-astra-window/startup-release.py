"""One same-session source release after real startup evidence. No worker launch.

Any refusal leaves the worker waiting for supported containment. A consumed
nudge intent is never replayed, even if its response was lost.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import select
import sys
import types

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
BASE_SHA = '8db3ba6e11239d6f0d3ff7827c6b59c8d39ac0a9f9e601f6d4175650b802d499'
VALIDATOR_SHA = 'baf895aed138c3dae71a458703c3bba961250b46a94d91d1efc358bacd5b7edc'
PROBE_SHA = '7c97d1fcfae3b87ddf76a54a449c34232befb0096b77efde07eb8758b6382de3'
INSPECT_SHA = 'ce8ed3521d453bfa8ef8da353dac354ff374f61c5d88066a351e3168fdaf1bdf'
COMMON_SHA = '1647eee642bdb9b38e5c422958f0118e914aa01c5cddf5037de2b8f4854ae24c'
ROOT = Path('/var/tmp/ga-e0t1.20-startup-release-20260927-r1')
WINDOW = Path('/var/tmp/ga-e0t1.20-window-20260927-r1')
ROUTE = Path('/var/tmp/ga-e0t1.20-route-20260927-r1')
CLIENT_INPUTS = tuple(Path(p) for p in (
    '/home/loucmane/.codex/config.toml', '/home/loucmane/.codex/hooks.json',
    '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy',
    '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy.json'))


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def load_base():
    raw = (HERE/'window-base-r11.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BASE_SHA, 'base source binding')
    w = types.ModuleType('startup_release_base');w.__file__ = str(HERE/'window-base-r11.py')
    exec(compile(raw,w.__file__,'exec',dont_inherit=True),w.__dict__)
    return w


def process_table():
    rows = {}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if p.stat().st_uid != 1000:continue
            fields=(p/'stat').read_text().rsplit(') ',1)[1].split()
            rows[int(p.name)] = dict(ppid=int(fields[1]),start=fields[19],state=fields[0])
        except (FileNotFoundError,ProcessLookupError):continue
    return rows


def worker_identity(pane, session, validator, read):
    rows=process_table()
    require(pane in rows,'pane process absent')
    chain, current = [], pane
    while True:
        require(current in rows and rows[current]['state'] not in ('Z','X') and len(chain)<8,
                'dead or excessive pane process chain')
        chain.append(current)
        children=[pid for pid,row in rows.items() if row['ppid']==current]
        require(len(children)<=1,'extra worker descendant')
        if not children:break
        current=children[0]
    proc=Path('/proc')/str(current)
    require(os.readlink(proc/'exe')==validator.CODEX,'leaf is not the pinned Codex binary')
    argv=(proc/'cmdline').read_bytes().rstrip(b'\0').decode('utf-8','strict').split('\0')
    args=validator.process_arguments(argv)
    require(os.readlink(proc/'cwd')==validator.WORK,'worker process cwd differs')
    # Only expected non-secret identity fields and override presence are retained.
    pairs=[entry.partition(b'=') for entry in (proc/'environ').read_bytes().split(b'\0') if entry]
    wanted={b'GC_SESSION_ID':session['id'].encode(),b'GC_SESSION_NAME':session['session_name'].encode(),
        b'GC_HOME':b'/home/loucmane/gascity/home',b'GIT_OPTIONAL_LOCKS':b'0',b'HOME':b'/home/loucmane'}
    names=[name for name,sep,value in pairs]
    for key,value in wanted.items():
        require([v for k,sep,v in pairs if k==key]==[value], 'worker environment identity differs')
    require(not any(name in names for name in (b'OPENAI_API_KEY',b'CODEX_API_KEY',b'OPENAI_BASE_URL',
        b'ANTHROPIC_API_KEY',b'ANTHROPIC_AUTH_TOKEN',b'ANTHROPIC_BASE_URL')), 'worker has provider override')
    require([v for k,sep,v in pairs if k==b'CODEX_HOME'] in ([],[b'/home/loucmane/.codex']), 'unexpected CODEX_HOME')
    require(hashlib.sha256(read(Path(validator.CODEX),256<<20)).hexdigest()==
        '56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da','worker image bytes differ')
    logs=set()
    for fd in (proc/'fd').iterdir():
        try:target=os.readlink(fd)
        except FileNotFoundError:continue
        if target.startswith('/home/loucmane/.codex/sessions/') and target.endswith('.jsonl'):
            logs.add(target)
    require(len(logs)==1,'native transcript not uniquely open by worker')
    path=Path(next(iter(logs)))
    key=validator.transcript_key(path,session)
    raw=read(path,32<<20)
    proof=validator.denial_from_rollout(raw,key)
    now=process_table()
    require(all(validator.same_process(rows[pid],now.get(pid)) for pid in chain), 'worker process identity changed')
    require({pid for pid,row in now.items() if row['ppid'] in chain}==set(chain[1:]),
            'worker descendants changed')
    return dict(pid=current,start=rows[current]['start'],chain=[dict(pid=p,**rows[p]) for p in chain],
        argv=args,transcript_path=str(path),native=proof)


def main():
    require(globals().get('_SOURCE_SHA') and os.getuid()==os.geteuid()==1000,'bound user invocation')
    require(sys.argv[1:]==[],'no release parameters are accepted')
    require(not os.path.lexists(ROOT),'startup release already consumed')
    w=load_base();w.read(Path(__file__),_SOURCE_SHA)
    v=w.module(HERE/'startup-validation.py',VALIDATOR_SHA)
    probe=w.module(HERE/'worker-startup.py',PROBE_SHA)
    inspector=w.module(HERE/'candidate-inspect.py',INSPECT_SHA)
    common=w.module(HERE/'common-snapshot-r1.py',COMMON_SHA)
    b,o,owned=w.load_support()
    w.active_epoch(o)
    require(w.record('stage-pass.json')==dict(ok=True,worker_launched=False),'window not staged')
    require((WINDOW/'suspension-city-resume-event.json').exists()
        and not list(WINDOW.glob('suspension-*-suspend-intent.json')), 'window not released or already containing')
    before=w.record('workspace-before.json');client_before=w.record('client-inputs-before.json')
    common_before=w.record('common-before.json')
    require(not common.compare(common_before,common.observe()),'shared Git changed before startup release')
    ROOT.mkdir(mode=0o700);w.ROOT=ROOT
    w.save('inspection-intent.json',dict(source_sha256=_SOURCE_SHA,source_released=False))
    def phase(name,args):return w.phase(name,args,b,owned,timeout=90)
    def epoch():
        w.ROOT=WINDOW
        try:w.active_epoch(o)
        finally:w.ROOT=ROOT
    def census(name):return v.session_row(json.loads(phase(name,w.GC+['session','list','--json'])['stdout']))
    s=census('sessions-before')
    [task]=json.loads(phase('task-before',w.GC+['--rig','gascity','bd','show',v.TASK,'--json'])['stdout'])
    panes=phase('pane-chain',['/usr/bin/tmux','-u','-L','city','list-panes','-a','-F',
                            '#{session_name}\t#{pane_pid}\t#{pane_dead}'])['stdout'].splitlines()
    require(len(panes)==1,'expected exactly one pane')
    fields=panes[0].split('\t')
    require(len(fields)==3 and fields[0]==s['session_name'] and fields[1].isdigit() and fields[2]=='0',
            'pane identity differs')
    proof=worker_identity(int(fields[1]),s,v,inspector.file_bytes)
    raw=inspector.file_bytes(Path(v.WORK)/v.EVIDENCE/'startup.json')
    value=json.loads(raw);v.report(value,s,probe)
    sha=hashlib.sha256(raw).hexdigest()
    routed=json.loads(w.read(ROUTE/'task-after.json'))
    v.live_task(task,routed,s,w.contract(),sha)
    require(not os.path.lexists(probe.FOREIGN/'unexpected-write'),'sandbox negative left a marker')
    for rel,pin in probe.RULES.items():require(hashlib.sha256(inspector.file_bytes(Path(v.WORK)/rel)).hexdigest()==pin,
                                              'local permission input drift')
    require(hashlib.sha256(inspector.file_bytes(probe.DEFAULT)).hexdigest()==probe.DEFAULT_SHA,'default rule drift')
    client_after={str(path):hashlib.sha256(inspector.file_bytes(path)).hexdigest() for path in CLIENT_INPUTS}
    require(client_before==client_after,'client config or global hook source changed')
    require(not os.path.lexists(Path(v.WORK)/'.codex/hooks.json'),'unexpected project hook')
    after=v.workspace_image(Path(v.WORK),inspector.file_bytes)
    v.pristine_startup(before,after,sha,w.contract().RUNTIME_IMAGE)
    w.save('proof.json',dict(session=s,worker=proof,report_sha256=sha,
        workspace_pristine=True,client_inputs=client_after,common_git_unchanged=True))
    epoch()
    s2=census('sessions-immediate')
    for key in ('id','session_name','template','rig','provider','work_dir','worker_dir','created_at','closed'):
        require(s2.get(key)==s.get(key),'same-session release binding changed')
    v.transcript_key(proof['transcript_path'],s2)
    [task2]=json.loads(phase('task-immediate',w.GC+['--rig','gascity','bd','show',v.TASK,'--json'])['stdout'])
    require(task2==task,'claim or task changed before release')
    immediate=process_table()
    require(all(v.same_process(row,immediate.get(row['pid'])) for row in proof['chain']),
            'worker chain changed before release')
    chain=[row['pid'] for row in proof['chain']]
    require({pid for pid,row in immediate.items() if row['ppid'] in chain}==set(chain[1:]),
            'extra descendant before release')
    pidfd=os.pidfd_open(proof['pid'])
    try:
        poll=select.poll();poll.register(pidfd,select.POLLIN);require(not poll.poll(0),'worker exited')
        message='SOURCE RELEASE: '+v.TASK+' session='+s['id']+' report_sha256='+sha+' probe_sha256='+PROBE_SHA
        w.save('nudge-intent.json',dict(session_id=s['id'],pid=proof['pid'],start=proof['start'],message=message))
        # One supported session nudge. Intent persists before the only mutation.
        phase('source-release',w.GC+['session','nudge',s['id'],message])
        require(not poll.poll(0),'worker exited during source release')
    finally:os.close(pidfd)
    epoch();w.complete_containment()
    w.save('result.json',dict(ok=True,session_id=s['id'],source_release_sent=True,
        report_sha256=sha,worker_launched=False,worker_result_unproven=True,retry=False))
    print(json.dumps(dict(ok=True,session_id=s['id'],source_release_sent=True,root=str(ROOT))))


if __name__=='__main__':main()
