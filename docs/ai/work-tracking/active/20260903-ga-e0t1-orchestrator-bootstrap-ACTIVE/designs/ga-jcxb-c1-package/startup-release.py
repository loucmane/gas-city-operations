"""One same-session source release after real startup evidence. No worker launch.

Any refusal leaves the worker waiting for supported containment. A consumed
nudge intent is never replayed, even if its response was lost.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import select
import sys
import types

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-jcxb-c1-package')
BASE_SHA = '27fca2a81bab86b96443ac2527fcddf27da1524d72c844b8891455c1073fa125'
VALIDATOR_SHA = 'fd50ed3cc1e0c9bd42790f8fc8a05bba5c56f7f6461dd20e6fa7d1cde139414b'
PROBE_SHA = 'bf10646d757d512d100bbaddaacb81c4c8f75ef520b467048603ee0e3d190ecc'
INSPECT_SHA = 'e2eec537f9108e287a5e36b0e3dcaf5f43ba480d72923b78db65a015969c76cc'
COMMON_SHA = 'b038123e92898a724f0a5cf94f4f4ec1c90b2d41fd62c30cb8e193ad225aceee'
ROOT = Path('/var/tmp/ga-jcxb-startup-release-20260930-r1')
WINDOW = Path('/var/tmp/ga-jcxb-window-20260930-r1')
ROUTE = Path('/var/tmp/ga-jcxb-route-20260930-r1')
CLIENT_INPUTS = tuple(Path(p) for p in (
    '/home/loucmane/.codex/config.toml', '/home/loucmane/.codex/hooks.json',
    '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy',
    '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy.json'))


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def load_base():
    raw = (HERE/'window-base.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BASE_SHA, 'base source binding')
    w = types.ModuleType('startup_release_base');w.__file__ = str(HERE/'window-base.py')
    exec(compile(raw,w.__file__,'exec',dont_inherit=True),w.__dict__)
    return w


def load(path, pin, read):
    raw=read(path)
    require(hashlib.sha256(raw).hexdigest()==pin,'startup helper binding')
    value=types.ModuleType(path.stem);value.__file__=str(path)
    exec(compile(raw,str(path),'exec',dont_inherit=True),value.__dict__)
    return value


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


def worker_identity(pane, session, validator, read, runtime):
    proof=runtime.worker_identity(pane,session,validator,read)
    raw=runtime.proc_bytes(runtime.PROC/str(pane)/'cmdline',1<<20)
    require(raw.endswith(b'\0') and raw!=b'\0','prompt argv encoding')
    argv=raw[:-1].decode('utf-8','strict').split('\0')
    require(hashlib.sha256(raw[:-1]).hexdigest()==proof['chain'][0]['argv_sha256'],'prompt argv changed')
    helper=load(HERE/'launch-contract.py','9c815d86f4eb87d3eca8135530063e173e5d497a4d56bf500d6c6221da5059db',read)
    body=read(HERE/'PRECLAIM.md').decode('utf-8','strict')
    require(hashlib.sha256(body.encode()).hexdigest()=='baf8aafad93bdf717d07e5a3ed3066d212d92261df2672b05189a1545c69805a','launch prompt file drift')
    require(helper.prompt_body(argv[-1],body)=='53682c1d8952f8f6345813a1519e9ee76ce72c70145b85de2663e80540c3eae8','assigned skills suffix differs')
    runtime.revalidate(proof,validator,read)
    return proof


def main():
    require(globals().get('_SOURCE_SHA') and os.getuid()==os.geteuid()==1000,'bound user invocation')
    require(sys.argv[1:]==[],'no release parameters are accepted')
    require(not os.path.lexists(ROOT),'startup release already consumed')
    w=load_base();w.read(Path(__file__),_SOURCE_SHA)
    v=w.module(HERE/'startup-validation.py',VALIDATOR_SHA)
    probe=w.module(HERE/'worker-startup.py',PROBE_SHA)
    inspector=w.module(HERE/'candidate-inspect.py',INSPECT_SHA)
    runtime=w.module(HERE/'runtime-process-r7.py','ea63f0ffda927baa34b777aeb210bf37cd7d7b408a629a9db9abc32445d40e65')
    common=w.module(HERE/'common-snapshot-r1.py',COMMON_SHA)
    delivery=w.module(HERE/'release-delivery-r13.py','45431e2971636f814a9876992a0694751531b414d2bb5ed7ccb8a4d5ba184f99')
    transport=w.module(HERE/'release-runtime-r13.py','9acd8664a35fd120e12a6eacc92eb81dd3701dac86f134bbea33079a996e08ba')
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
    def phase(name,args,timeout=90):return w.phase(name,args,b,owned,timeout=timeout)
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
    proof=worker_identity(int(fields[1]),s,v,inspector.file_bytes,runtime)
    raw=inspector.file_bytes(Path(v.WORK)/v.EVIDENCE/'startup.json')
    value=json.loads(raw);v.report(value,s,probe)
    sha=hashlib.sha256(raw).hexdigest()
    routed=json.loads(w.read(ROUTE/'task-after.json'))
    v.live_task(task,routed,s,w.contract(),sha)
    monitoring=v.monitoring_state(task,routed,s,datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','').rstrip('0').rstrip('.')+'Z')
    waiting_raw=inspector.file_bytes(Path(proof['transcript_path']),32<<20)
    require(hashlib.sha256(waiting_raw).hexdigest()==proof['native']['rollout_sha256'],'native transcript changed during initial proof')
    waiting=v.waiting_turn(waiting_raw,s,sha,PROBE_SHA,datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','').rstrip('0').rstrip('.')+'Z')
    require(not os.path.lexists(probe.FOREIGN/'unexpected-write'),'sandbox negative left a marker')
    for rel,pin in probe.RULES.items():require(hashlib.sha256(inspector.file_bytes(Path(v.WORK)/rel)).hexdigest()==pin,
                                              'local permission input drift')
    require(hashlib.sha256(inspector.file_bytes(probe.DEFAULT)).hexdigest()==probe.DEFAULT_SHA,'default rule drift')
    client_after={str(path):hashlib.sha256(inspector.file_bytes(path)).hexdigest() for path in CLIENT_INPUTS}
    require(client_before==client_after,'client config or global hook source changed')
    probe.verified_hook()  # exact generated bytes and authority, not a trust grant
    after=v.workspace_image(Path(v.WORK),inspector.file_bytes)
    v.pristine_startup(before,after,sha,w.contract().RUNTIME_IMAGE)
    w.save('proof.json',dict(session=s,worker=proof,report_sha256=sha,
        workspace_pristine=True,client_inputs=client_after,common_git_unchanged=True,
        monitoring_adjudication=monitoring,waiting_turn=waiting))
    epoch()
    s2=census('sessions-immediate')
    for key in ('id','session_name','template','rig','provider','work_dir','worker_dir','created_at','closed'):
        require(s2.get(key)==s.get(key),'same-session release binding changed')
    v.transcript_key(proof['transcript_path'],s2)
    [task2]=json.loads(phase('task-immediate',w.GC+['--rig','gascity','bd','show',v.TASK,'--json'])['stdout'])
    v.live_task(task2,routed,s2,w.contract(),sha)
    require(task2==task,'claim or task changed before release')
    require(inspector.file_bytes(Path(proof['transcript_path']),32<<20)==waiting_raw,'native waiting transcript changed before release')
    runtime.revalidate(proof,v,inspector.file_bytes)
    pidfd=os.pidfd_open(proof['pid'])
    try:
        poll=select.poll();poll.register(pidfd,select.POLLIN);require(not poll.poll(0),'worker exited')
        message='SOURCE RELEASE: '+v.TASK+' session='+s['id']+' report_sha256='+sha+' probe_sha256='+PROBE_SHA
        w.save('nudge-intent.json',dict(session_id=s['id'],pid=proof['pid'],start=proof['start'],message=message))
        # One supported session nudge. Intent persists before the only mutation.
        delivered=transport.execute(w,phase,inspector,runtime,delivery,s,proof,message,waiting_raw,
            lambda:not poll.poll(0))
        require(delivered.get('delivered') is True,'source release not acknowledged')
        require(not poll.poll(0),'worker exited during source release')
    finally:os.close(pidfd)
    epoch();w.complete_containment()
    w.save('result.json',dict(ok=True,session_id=s['id'],source_release_sent=True,
        report_sha256=sha,source_delivery_acknowledged=True,delivery=delivered,
        worker_launched=False,worker_result_unproven=True,retry=False))
    print(json.dumps(dict(ok=True,session_id=s['id'],source_release_sent=True,root=str(ROOT))))


if __name__=='__main__':main()
