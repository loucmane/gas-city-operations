"""One native receipt-compatibility/readiness observation; no worker or install.

Reuse the accepted host/cache snapshot, isolated source loader and owned-phase
runner. Provider version/auth executables and one managed signer --probe may
run. There is no inference, signature, route, resume, or credential refresh.

P6 rebind of the reviewed 09-20 readiness `6ac87f25`. The logic and the compiled Core
796d9a7a diagnostic `edbc0fa1` are unchanged. Only these bindings change:
- the P6 observer;
- the P6 composition, proven at run time against the derived draft;
- the 2.1.280 CLI `1e08503d`, for both the worker and the API package, with the new inode and size.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import types

HERE=Path(__file__).parent
ROOT=Path('/var/tmp/gct-m1wh-p6-readiness-20260923-r2')
BUILD=Path('/var/tmp/ga-ecwh-preflight-diagnostic-20260920-r1')
BASE=HERE/'p6-observe-compose.py'
BASE_SHA='43b94ce677dcaa80b6937f7205362063da151f0608a99874b18b692ab8f2c8d6'
SUCCESSOR=Path('/home/loucmane/.local/share/gas-city-staging/ga-mutg-20260920/ga-ecwh-provisioning-successor-20260920')
LAUNCH=HERE/'source-launch.py'
LAUNCH_SHA='31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'
BINARY_SHA='edbc0fa11d3ebae15f678179725203d9da3434ec0cf8883c536398d5f97426bf'
COMPOSITION=Path('/var/tmp/gct-m1wh-p6-compose-20260923-r2/composition.json')
NATIVE=Path('/home/loucmane/.local/share/fnm/node-versions/v22.16.0/installation/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe')
NATIVE_LINK=Path('/home/loucmane/.local/share/fnm/node-versions/v22.16.0/installation/bin/claude')
NATIVE_SHA='1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
NATIVE_IDENTITY=(1000,1000,2,2096,3576768,233709640)
NATIVE_ALIAS=Path('/home/loucmane/.local/share/fnm/node-versions/v22.16.0/installation/lib/node_modules/@anthropic-ai/claude-code/node_modules/@anthropic-ai/claude-code-linux-x64/claude')
WORKER_NATIVE=Path('/home/loucmane/gascity/bin/claude')
WORKER_NATIVE_SHA='1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
SUBSCRIPTION=Path('/home/loucmane/gas-city-template/lib/gct_claude_subscription.py')
SUBSCRIPTION_SHA='3b92bc92f3bc05a762c0008738550d8c48c0998fad6b4807578552643529639b'
POLICY=Path('/home/loucmane/gas-city-template/templates/claude/core-signing-control-policy.json')
PROVISIONER=Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
PROVISIONER_SHA='64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
RUNNER=Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/bin/gct-managed-worker-canary')
RUNNER_SHA='3beeedb2e5ce0723e5f745a05f1e2fdfa3ec27bee468284860e587e63c63e2e2'

def load_base():
    raw=BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA:raise RuntimeError('observer source drift')
    value=types.ModuleType('reviewed_compose_observer');value.__file__=str(BASE)
    exec(compile(raw,str(BASE),'exec',dont_inherit=True),value.__dict__)
    value.ROOT=ROOT
    return value

def native_package_pair(base):
    # The installed npm package exposes exactly two hard links to one ELF.
    # Bind both existing names/inode; source/helper single-link rules stay intact.
    observer=base.observe_module()
    proofs={}
    for path in (NATIVE,NATIVE_ALIAS):
        if path.resolve(strict=True)!=path:raise RuntimeError('native package alias/symlink drift')
        before=path.lstat()
        if (not stat.S_ISREG(before.st_mode) or stat.S_IMODE(before.st_mode)!=0o755
            or (before.st_uid,before.st_gid,before.st_nlink,before.st_dev,before.st_ino,before.st_size)
                !=NATIVE_IDENTITY):
            raise RuntimeError('native package hard-link authority drift')
        proof=observer.read_file(str(path))[0]
        if proof['sha256']!=NATIVE_SHA or before!=path.lstat():raise RuntimeError('native package bytes changed')
        proofs[str(path)]=proof
    return proofs

def composition(base):
    # The P6 composition is accepted only as recorded: ok, preserved, and equal to the proven draft.
    root=COMPOSITION.parent
    result=json.loads(base.read(root/'result.json'))
    if not (result['ok'] is True and result['unchanged'] is True and result['error'] is None
            and base.read(root/'before.json')==base.read(root/'after.json')):
        raise RuntimeError('composition evidence not accepted')
    actual=json.loads(base.read(COMPOSITION))['observation']
    draft=json.loads(base.recorded_draft()['raw']);expected=draft['profiles'][0]
    if (actual['profile']!=expected['name'] or actual['argv']!=expected['argv']
        or actual['environment']!=expected['environment']
        or actual['permission_revision']!=draft['permission_revision']
        or actual['task_observed'] or actual['worker_launched']):
        raise RuntimeError('composition differs from the proven draft')
    return base.read(root/'after.json')

def pin_inputs(base):
    base.read(Path(__file__),_SOURCE_SHA)
    base.read(LAUNCH,LAUNCH_SHA)
    base.read(BUILD/'compose',BINARY_SHA)
    composition(base)
    base.read(SUCCESSOR/'preflight-main.go','75c897e0874404c8d2fded9302ffbfb799ba983678d5503f44041a7d8508e7c6')
    base.read(SUCCESSOR/'prepare-preflight.py','47cfa684dd6d0d6b021edf7f01d6f80f5c700073a59ea63426e1a66d28c5926d')
    base.read(BUILD/'extraction.json','4dc42f8bcfb6efbe9150ef4beaa3c0e0ada0cf9d0ad1d4cb57ee29920af5ff45')
    native_package_pair(base)
    base.read(WORKER_NATIVE,WORKER_NATIVE_SHA)
    base.read(SUBSCRIPTION,SUBSCRIPTION_SHA)
    base.read(PROVISIONER,PROVISIONER_SHA)
    base.read(RUNNER,RUNNER_SHA)
    if NATIVE_LINK.resolve(strict=True)!=NATIVE:raise RuntimeError('API native link drift')

def mounts(base):
    rows=[]
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields=line.split()
        mount=re.sub(r'\\([0-7]{3})',lambda m:chr(int(m[1],8)),fields[4])
        if '\\' in mount:raise RuntimeError('unknown mount escape')
        rows.append((mount,fields[5].split(',')))
    proof={}
    for path in (base.CACHE,*base.PROTECTED,base.CITY,BUILD,ROOT,Path('/home/loucmane/.claude'),Path('/home/loucmane/.local/share/fnm')):
        path=str(path)
        covering=max(((m,o) for m,o in rows if m=='/' or path==m or path.startswith(m+'/')),key=lambda row:len(row[0]))
        descendants=[(m,o) for m,o in rows if m.startswith(path+'/')]
        if 'ro' not in covering[1] or any('ro' not in o for m,o in descendants):raise RuntimeError('writable mount: '+path)
        proof[path]=dict(covering=covering,descendants=descendants)
    return proof

def inner(base,mode):
    proof=mounts(base)
    pin_inputs(base)
    if mode=='normalize':
        raw=base.read(PROVISIONER,PROVISIONER_SHA)
        provisioner=types.ModuleType('reviewed_provisioner');provisioner.__file__=str(PROVISIONER)
        sys.modules[provisioner.__name__]=provisioner
        exec(compile(raw,str(PROVISIONER),'exec',dont_inherit=True),provisioner.__dict__)
        receipt=provisioner.load_prototype(base.recorded_draft()['path'],dict(path=str(RUNNER),sha256=RUNNER_SHA))
        wire=provisioner.canonical_json(receipt).decode('utf-8')
        print(json.dumps(dict(mounts=proof,result=receipt,wire=wire)))
        return
    if mode=='subscription':
        subscription=base.module(SUBSCRIPTION,SUBSCRIPTION_SHA)
        env=subscription.subscription_environment(base.ENV)
        subscription.inspect_settings_files([POLICY])
        posture=subscription.authenticate_subscription(WORKER_NATIVE,cwd=ROOT,
            environment=env,setting_sources='',timeout_seconds=30)
        print(json.dumps(dict(mounts=proof,subscription=posture,inference=False)))
        return
    argv=[str(BUILD/'compose')]
    if mode=='finalize':argv+=['finalize',str(ROOT/'receipt.normalized.json')]
    elif mode=='discover':argv+=['discover']
    elif mode in ('negative-old-path','preflight'):
        argv += [mode,str(ROOT/'receipt.final.json'),str(COMPOSITION),NATIVE_SHA]
    else:raise RuntimeError('unknown native phase')
    result=subprocess.run(argv,env=base.ENV,stdin=subprocess.DEVNULL,capture_output=True,text=True,check=False)
    if result.returncode:
        # Readiness returns only filtered errors; no raw auth response is emitted.
        raise RuntimeError('native '+mode+' refusal: '+result.stderr)
    output=json.loads(result.stdout)
    print(json.dumps(dict(mounts=proof,result=output,wire=result.stdout if mode=='finalize' else None)))

def snapshot(base,name):
    pin_inputs(base)
    base.snapshot(name)
    o=base.observe_module()
    base.write(name+'.provider-pins',dict(
        worker=o.read_file(str(WORKER_NATIVE))[0], api_package=native_package_pair(base),
        subscription=o.read_file(str(SUBSCRIPTION))[0],
        provisioner=o.read_file(str(PROVISIONER))[0],runner=o.read_file(str(RUNNER))[0],
        api_link=dict(target=os.readlink(NATIVE_LINK),metadata=o.metadata(NATIVE_LINK.lstat()))))

def main():
    if not globals().get('_SOURCE_SHA'):raise RuntimeError('source-bound entrypoint required')
    base=load_base()
    pin_inputs(base)
    if len(sys.argv)==3 and sys.argv[1]=='snapshot' and sys.argv[2] in ('before.json','after.json'):
        snapshot(base,sys.argv[2]);return
    if len(sys.argv)==3 and sys.argv[1]=='inner':inner(base,sys.argv[2]);return
    if len(sys.argv)!=1:raise RuntimeError('invalid invocation')
    runner=base.module(BUILD/'phase_runner.py','eddf5e1174a7b275abe280e91ea5c8ea0762600d38524ba9631f53fb4874cdf3')
    ROOT.mkdir(mode=0o700)
    def invoke(*args):return ['/usr/bin/python3','-I','-S','-B',str(LAUNCH),__file__,_SOURCE_SHA,*args]
    def phase(name,argv,timeout):
        result=runner._run_owned_phase(name=name,argv=argv,cwd=ROOT,environment=base.ENV,
            timeout=timeout,evidence_path=ROOT/(name+'-phase.json'))
        if not base.successful(result):raise RuntimeError('terminal phase refusal: '+name)
        return result
    phase('before',invoke('snapshot','before.json'),120)
    if base.read(ROOT/'before.json')!=composition(base):
        raise RuntimeError('composition evidence invalidated by current input/host drift; no native probes')
    error=None
    completed=[]
    try:
        for mode in ('normalize','finalize','discover','negative-old-path','subscription','preflight'):
            result=phase(mode,['/usr/bin/bwrap','--ro-bind','/','/','--unshare-net','--unshare-pid',
                '--new-session','--die-with-parent','--proc','/proc','--dev','/dev','--',*invoke('inner',mode)],60)
            envelope=json.loads(result['stdout'])
            base.write(mode+'.json',envelope)
            if mode in ('normalize','finalize'):
                name='receipt.normalized.json' if mode=='normalize' else 'receipt.final.json'
                with (ROOT/name).open('xb') as stream:stream.write(envelope['wire'].encode('utf-8'))
                if mode=='finalize' and envelope['result']!=json.loads(base.read(ROOT/'receipt.normalized.json')):
                    raise RuntimeError('Template and native receipt finalization disagree')
            if mode=='discover' and envelope['result']!=dict(path=str(NATIVE_LINK),resolved_path=str(NATIVE),sha256=NATIVE_SHA,provider_invoked=False):
                raise RuntimeError('native discovery does not match bound executable')
            completed.append(mode)
    except BaseException as failure:error=failure
    phase('after',invoke('snapshot','after.json'),120)
    unchanged=(base.read(ROOT/'before.json')==base.read(ROOT/'after.json') and
               base.read(ROOT/'before.json.provider-pins')==base.read(ROOT/'after.json.provider-pins'))
    base.write('result.json',dict(ok=error is None and unchanged,completed=completed,unchanged=unchanged,
        error=None if error is None else str(error),receipt_installed=False,worker_launched=False,
        task_claim_proven=False,check_path_basis='receipt-input-not-routed-bead',inference=False,signing=False,
        signer_probe_may_log_externally=True))
    if error or not unchanged:raise RuntimeError('readiness or preservation refused; stop') from error
    print(json.dumps(dict(ok=True,root=str(ROOT),receipt_installed=False)))

if __name__=='__main__':main()
