"""One reviewed host-job permissions migration; all diagnostics are read-only.

This is operational recovery, not a provider wrapper or worker source change.
The two live trees receive metadata operations only on six pinned descriptors.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import types

HERE = Path(__file__).parent
WINDOW = HERE.parent / 'ga-e0t1-20-astra-window'
ROOT = Path('/var/tmp/ga-e0t1.20-codex-permissions-20260928-r2')
HOME = Path('/home/loucmane/.codex')
JOB = 'ga-e0t1-20-permissions-r2'
PRIOR_ROOT = Path('/var/tmp/ga-e0t1.20-codex-permissions-20260928-r1')
PRIOR_JOB_SHA = '0c214abca997edc0e94d003b9fb3637226b7b7108aca3ec72ae70142ecd11e02'
PRIOR_PHASE_SHA = 'ad34e618652735fe00a0049aaffdb7438a31a192467317e51b36b3262d95d6ed'
TERMINAL = Path('/var/tmp/ga-e0t1.20-terminal-20260928-r7/observed-after.json')
TERMINAL_SHA = 'd86e7fb9bca8e2abe6bf6732c236d92686e3398a261f7a198a2e87c6f881e3cd'
ASSEMBLY_SHA = '30955869bd18d74ee5543cfa7a545a8664b1ba54e6cee463323aec152143ce0c'
HELPER_SHA = '0b2458d691d93a1672757314a34f9e8c1efbc97f87df42adee18b4be28aec90a'
# Filled from the tested candidate before signed review; never supplied by CLI.
POLICY_SHA = 'b560e231944f54533e6dfa7150e791769d3f29996221a4b1e86362f052e0f442'
PREIMAGE_SHA = '5da959c67576133e0df8423b1ff49ef3641cd836f9fc54a87a8e9269c76aad24'
# Operator approved this exact two-field disposition on September 28 after
# PERMISSIONS-RECOVERY-HOLD. This applies only to this fresh recovery job.
# Never change the actual tree or the preserved terminal observation.
CACHE_DIRECTORY = '954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git'
CACHE_BEFORE_NS = 1790604770227789531
CACHE_APPROVED_NS = 1790621288720671640


def require(ok, reason):
    if not ok:raise RuntimeError(reason)


def read(path, pin=None):
    path = Path(path)
    require(path.resolve(strict=True) == path, 'source alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == s.st_gid == 1000 and s.st_nlink == 1
                and not s.st_mode & 0o022 and s.st_size <= 16 << 20, 'source authority')
        chunks = []
        while chunk := os.read(fd, 65536):chunks.append(chunk)
        raw = b''.join(chunks)
        require(s == os.fstat(fd) == path.lstat() and len(raw) == s.st_size, 'source read drift')
        require(pin is None or hashlib.sha256(raw).hexdigest() == pin, 'source digest drift')
        return raw
    finally:os.close(fd)


def load(path, pin, name):
    module = types.ModuleType(name); module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(read(path, pin), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def support(*, host=True):
    assembly = json.loads(read(WINDOW / 'assembly.json', ASSEMBLY_SHA))
    for name, pin in assembly['files'].items():read(WINDOW / name, pin)
    w = load(WINDOW/'window-base-r11.py', assembly['files']['window-base-r11.py'], 'bound_window')
    h = load(WINDOW/'generators/helper_recovery.py', HELPER_SHA, 'read_only_helpers')
    # Reuse only sandbox validation, owned read-only phases and host observation.
    # The historical helper archive, its entrypoint and old bindings never run.
    h.ARCHIVE = ROOT
    # Root ownership is authoritative only in the parent host namespace.
    # The confined child never launches bwrap and must instead prove its
    # actual mounts read-only before inspecting any protected tree.
    if host:h.verify_sandbox_binary()
    b, o, owned = w.load_support()
    return w, h, b, o, owned


def affected(target):
    return any(target == str(HOME/n) or target.startswith(str(HOME/n)+'/')
               for n in ('rules', 'sessions'))


def clients(proc_root=Path('/proc')):
    """Inspect same-user clients and open handles; never emit credentials.

    Zombie processes have exited and cannot hold an open file table. Every live
    unreadable same-user process refuses. Only HOME/CODEX_HOME are retained from
    native Codex environment reads; no authentication values are recorded.
    """
    safe, exited = [], []
    for proc in proc_root.iterdir():
        if not proc.name.isdecimal() or int(proc.name) == os.getpid():continue
        try:
            if proc.stat().st_uid != 1000:continue
            start = (proc/'stat').read_text().rsplit(') ', 1)[1].split()
            if start[0] in ('Z', 'X'):
                exited.append(dict(pid=int(proc.name), start=start[19], state=start[0]))
                continue
            exe = os.readlink(proc/'exe')
            for fd in (proc/'fd').iterdir():
                try:target=os.readlink(fd)
                except FileNotFoundError:continue
                require(not affected(target), 'affected open handle at pid '+proc.name)
            comm = (proc/'comm').read_text().strip()
            if 'codex' in Path(exe).name.lower() or 'codex' in comm.lower():
                raw = (proc/'environ').read_bytes()
                require(len(raw) <= 1 << 20, 'client environment bound')
                environment = dict(item.split(b'=',1) for item in raw.split(b'\0')
                                   if item.startswith((b'HOME=',b'CODEX_HOME=')))
                home = environment.get(b'CODEX_HOME') or environment.get(b'HOME', b'') + b'/.codex'
                require(home and os.fsdecode(home) != str(HOME)
                        and Path(os.fsdecode(home)).resolve(strict=True) != HOME, 'affected live Codex client')
                safe.append(dict(pid=int(proc.name), start=start[19], code_home=os.fsdecode(home)))
            end = (proc/'stat').read_text().rsplit(') ',1)[1].split()
            require(start[19] == end[19], 'process identity race')
        except (FileNotFoundError, ProcessLookupError):
            # A vanished process cannot be an affected writer. A still-live
            # process with inaccessible/missing fields is not treated as gone.
            require(not proc.exists() or (proc/'stat').read_text().rsplit(') ',1)[1].split()[0] in ('Z','X'),
                    'incomplete live process observation')
    return dict(unaffected_codex_clients=safe, exited_no_file_table=exited)


def context():
    require(os.getuid() == os.geteuid() == 1000 and globals().get('_SOURCE_SHA'), 'bound uid1000 entry')
    read(Path(__file__), _SOURCE_SHA)
    group = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-'+JOB+'.service\n'
    require(Path('/proc/self/cgroup').read_text() == group
            and re.fullmatch('[0-9a-f]{32}',os.environ.get('INVOCATION_ID','')), 'not reviewed host job')
    jobs=Path('/home/loucmane/.local/share/gas-city-staging/jobs')
    require(not list((jobs/'queue').iterdir()) and (jobs/'done'/(JOB+'.started.json')).is_file()
            and not (jobs/'done'/(JOB+'.json')).exists(), 'job not exclusive or already consumed')
    prior=json.loads(read(jobs/'done/ga-e0t1-20-permissions-r1.json',PRIOR_JOB_SHA))
    phase=json.loads(read(PRIOR_ROOT/'before-trees-phase.json',PRIOR_PHASE_SHA))
    require(prior['exit']==1 and prior['unit_state_after']=='inactive'
            and phase['exit_code']==1 and not phase['timed_out']
            and phase['cleanup']['owned_process_group_gone']
            and not phase['cleanup']['unexpected_survivors'], 'prior refusal not contained')
    require({x.name for x in PRIOR_ROOT.iterdir()}=={
        'intent.json','default.rules.backup','before-sessions-phase.json',
        'before-status-phase.json','before-trees-phase.json'}, 'prior transaction may have started')


def approved_cache_image(prior):
    expected=json.loads(json.dumps(prior))
    entry=expected['cache']['inventory'][CACHE_DIRECTORY]
    for key in ('mtime_ns','ctime_ns'):
        require(type(entry[key]) is int and entry[key]==CACHE_BEFORE_NS,
                'cache disposition preimage')
        entry[key]=CACHE_APPROVED_NS
    return expected


def tree_proof(w, h, b, o):
    h.prove_read_only([b.CACHE, *b.PROTECTED, w.CITY, w.WORK, w.ADMIN])
    prior=json.loads(read(TERMINAL,TERMINAL_SHA))
    expected=approved_cache_image(prior)
    snapshot=dict(cache=o.tree_snapshot(b.CACHE,cache=True),
                  protected={str(p):o.tree_snapshot(p,protected=True) for p in b.PROTECTED})
    for k in snapshot:
        require(w.dependency_image(snapshot[k]) == w.dependency_image(expected[k]), 'restored '+k+' drift')
    # Full actual metadata, including access times, is hashed for immediate
    # before/after preservation. Historical reuse alone excludes access times.
    return dict(ok=True, readonly=True, cache_disposition=dict(
        path=str(b.CACHE / CACHE_DIRECTORY), fields=['mtime_ns','ctime_ns'],
        before_ns=CACHE_BEFORE_NS, approved_ns=CACHE_APPROVED_NS,
        prior_observation_sha256=TERMINAL_SHA), sha256=hashlib.sha256(
        json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest())


def state(w,h,b,o,owned,label):
    host=h.confined_host_observation(w,o,owned,label)
    require(host == json.loads(read(TERMINAL,TERMINAL_SHA))['host'], 'host or service drift')
    runner=o.service('gas-city-jobrunner.service',True)
    require(runner['MainPID']=='2812303' and runner['ExecMainStartTimestampMonotonic']=='301336188076'
            and runner['NRestarts']=='0' and runner['ActiveState']=='active'
            and runner['SubState']=='running' and runner['Result']=='success', 'runner epoch drift')
    prior=json.loads(read(TERMINAL,TERMINAL_SHA))
    pins={name:o.read_file(name)[0] for name in prior['pins']}
    require(w.dependency_image(pins)==w.dependency_image(prior['pins']), 'protected pin drift')
    command=['/usr/bin/python3','-I','-S','-B',str(w.LAUNCH),__file__,_SOURCE_SHA,'inner']
    tree=json.loads(h.isolated(w,owned,label+'-trees',command,300))
    require(tree.get('ok') is True and tree.get('readonly') is True, 'tree proof missing')
    return dict(host=host,runner=runner,pins=pins,trees=tree)


def creation_proof(p, entries):
    root=ROOT/'creation-proof';root.mkdir(mode=0o700)
    rows=[]
    oldmask=os.umask(0o077)
    try:
        for number,(name,fd) in enumerate(entries.items()):
            if not stat.S_ISDIR(os.fstat(fd).st_mode):continue
            acl=os.getxattr(fd,p.DEFAULT)
            require(acl==p.PRIVATE,'installed ACL drift')
            for mask in (0o002,0o022,0o077):
                for requested in (0o666,0o600):
                    mirror=root/f'{number}-{mask}-{requested}';mirror.mkdir(mode=0o700)
                    os.setxattr(mirror,p.DEFAULT,acl)
                    os.umask(mask)
                    day=mirror/'2027/01/01';day.mkdir(parents=True,mode=0o777)
                    file=day/'synthetic.jsonl'
                    created=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,requested)
                    os.write(created,b'{"synthetic":true}\n');os.close(created)
                    require(stat.S_IMODE(file.stat().st_mode)==0o600
                        and all(stat.S_IMODE(x.stat().st_mode)==0o700 for x in (day,day.parent,day.parent.parent))
                        and os.getxattr(day,p.DEFAULT)==acl,'creation proof refused')
                    rows.append(dict(target=name,umask=mask,requested=requested,file_mode=0o600,directory_mode=0o700))
                    os.umask(0o077)
    finally:os.umask(oldmask)
    p.save(ROOT,'creation-proof.json',rows)
    return dict(cases=len(rows),all_private=True,scope='kernel creation on retained disposable mirrors not worker acceptance')


def main():
    require(globals().get('_SOURCE_SHA'), 'bound source entry')
    read(Path(__file__),_SOURCE_SHA)
    require(sys.argv[1:] in (['apply'],['inner']),'unknown operation')
    inner=sys.argv[1:]==['inner']
    if not inner:context()
    w,h,b,o,owned=support(host=not inner)
    if inner:
        print(json.dumps(tree_proof(w,h,b,o),sort_keys=True));return
    p=load(HERE/'permissions.py',POLICY_SHA,'permissions_policy')
    expected=json.loads(read(HERE/'preimage.json',PREIMAGE_SHA))
    allowed={str(HOME/n) for n in ('rules','rules/default.rules','sessions','sessions/2026','sessions/2026/09','sessions/2026/09/28')}
    require(set(expected)==allowed,'target scope')
    require(not os.path.lexists(ROOT),'consumed evidence root')
    initial_clients=clients()
    entries={}
    try:
        for name in sorted(expected):
            entries[name]=p.open_exact(name,stat.S_ISDIR(expected[name]['stat']['mode']))
        require({n:p.image(fd) for n,fd in entries.items()}==expected,'reviewed target drift')
        ROOT.mkdir(mode=0o700)
        p.save(ROOT,'intent.json',dict(executor_sha256=_SOURCE_SHA,targets=sorted(allowed),
             initial_clients=initial_clients,worker_release=False,rollback='exact preimage except unavoidable ctime'))
        # Byte-exact backup of the only existing file whose metadata may change.
        rules=entries[str(HOME/'rules/default.rules')];os.lseek(rules,0,os.SEEK_SET)
        raw=os.read(rules,1048577)
        require(p.sha(raw)==expected[str(HOME/'rules/default.rules')]['sha256'],'rules backup drift')
        backup=os.open(ROOT/'default.rules.backup',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(backup,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        before=state(w,h,b,o,owned,'before');p.save(ROOT,'host-before.json',before)
        inventories={n:p.inventory(HOME/n) for n in ('sessions','rules')}
        p.save(ROOT,'historical-inventory.json',inventories)
        anchors={str(a):dict(identity=(a.stat().st_dev,a.stat().st_ino,a.stat().st_uid,a.stat().st_gid,a.stat().st_mode),
                   xattrs={k:os.getxattr(a,k).hex() for k in os.listxattr(a)}) for a in (HOME,HOME.parent)}
        def guard():
            clients()
            for name,original in inventories.items():p.preserve_inventory(original,p.inventory(HOME/name),allowed)
            for name,old in anchors.items():
                a=Path(name);s=a.lstat()
                require((s.st_dev,s.st_ino,s.st_uid,s.st_gid,s.st_mode)==old['identity']
                    and {k:os.getxattr(a,k).hex() for k in os.listxattr(a)}==old['xattrs'],'parent authority drift')
        def prove(current):
            proof=creation_proof(p,entries)
            assembly=json.loads(read(WINDOW/'assembly.json',ASSEMBLY_SHA))
            inspector=load(WINDOW/'candidate-inspect.py',assembly['files']['candidate-inspect.py'],'unchanged_inspector')
            require(p.sha(inspector.file_bytes(HOME/'rules/default.rules'))==expected[str(HOME/'rules/default.rules')]['sha256'],
                    'unchanged strict reader refuses repaired rules')
            proof['unchanged_strict_rules_reader_pass']=True
            after=state(w,h,b,o,owned,'after');p.save(ROOT,'host-after.json',after)
            require(before==after,'immediate host or protected state drift')
            return proof
        def interrupted(signum,frame):raise InterruptedError('handled signal '+str(signum))
        for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,interrupted)
        p.transaction(entries,expected,ROOT,guard,prove)
        print(json.dumps(dict(ok=True,root=str(ROOT),worker_release=False)))
    finally:
        for fd in entries.values():os.close(fd)


if __name__=='__main__':main()
