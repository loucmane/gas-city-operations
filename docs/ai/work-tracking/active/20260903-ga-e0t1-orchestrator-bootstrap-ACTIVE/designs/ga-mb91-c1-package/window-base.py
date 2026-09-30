"""ga-mb91 bounded Astra candidate window, rebound from signed S5.

S1 WORKTREE and PREP are completed. The accepted platform is P13; the current
source contains no reusable historical lifecycle exception. This package is
not C1 or handover acceptance and introduces no Claude invocation.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import time
import types

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-mb91-c1-package')
ROOT = Path('/var/tmp/ga-mb91-window-20260930-r3')
PREP = Path('/var/tmp/ga-mb91-prep-20260930-r1')
SUSPENSION = '/home/loucmane/gascity/city/.gc/runtime/suspension-state.json'
LINEAGE_SHA = '26acf7ebd1ca9e1832db64b1ede34b3e7858c548463d3bde9581b1900d50cd90'
SUPPORT = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-p6')
LAUNCH = SUPPORT/'source-launch.py'
CITY = Path('/home/loucmane/gascity/city')
RECEIPT = CITY/'.gc/runtime/provisioning/receipt.json'
WORK = Path('/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91')
BASE = '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
ADMIN = Path('/home/loucmane/gas-city-ops/.git/worktrees/ga-mb91')
HARDENED = ['/usr/bin/env','GIT_CONFIG_NOSYSTEM=1','GIT_CONFIG_GLOBAL=/dev/null','GIT_ATTR_NOSYSTEM=1','HOME=/nonexistent','/usr/bin/git','--no-optional-locks','--git-dir=/home/loucmane/gas-city-ops/.git/worktrees/ga-mb91','--work-tree=/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','core.attributesFile=/dev/null']
GC = ['/home/loucmane/gascity/bin/gc', '--city', str(CITY)]
PROVISIONER = Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
WITNESS = Path('/var/tmp/ga-e0t1.22-p14-adoption-20260930/typed-support.json')
WITNESS_SHA = 'c61c2384493674139d8a1265f8c5963d36fc5b9f6d728b3c038feaa5689bf442'
CITY_SHA = ('bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1',
            'b090821569aacef87d0efa910cc08bd4f1c62142e197f6ff570cc835d3d03273')
RECEIPT_SHA = ('2607e90522b5571a5180d882e3d21882bafbc42423e0855f11fae7ec00bdf980',
               'a6048ea44699972c0aff3672f11acb2b6427e46b1667bd909a23c1bd962e01dc')
REVISION = ('a61666b33528c1cb8b497f55d9c6b8b37df2ce74ed9853345de8d7321e18f58f',
            'b63a013042945f00fc507ddaeca21ff8b2f71da4e8b120b680a5ab467487f160')
INPUT = (Path('/var/tmp/ga-e0t1.22-p14-input-20260930/receipt.input.draft.json'), PREP/'receipt.input.json')
INPUT_SHA = ('9d2cb1b2b21150594d9ccd3bec35d69ed092c6074e51b774e018fb9debcc53b4',
             None)  # The isolated input is compared to the exact native-finalized wire below.
RUNNER = Path('/var/tmp/ga-ecwh-preflight-diagnostic-20260920-r1/phase_runner.py')
# Accepted restored TERMINAL observation; all host, pin and protected fields remain exact.
ACCEPTED = Path('/var/tmp/ga-mb91-terminal-20260930-r1/observed-after.json')
ACCEPTED_SHA = '5481ac1d2b37c678c9d261a05cc2207aecca882c5637db13473392ecb8e0c813'
ACCEPTED_KEYS = ('cache', 'host', 'pins', 'protected')
PROVIDER = Path('/var/tmp/ga-e0t1.22-p14-adoption-20260930/after.json.provider-pins')
PROVIDER_SHA = '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'
CACHE_DIRECTORY = '954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git'

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path, pin=None):
    path = Path(path)
    require(path.resolve(strict=True) == path, 'path alias: '+str(path))
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1,
                'file authority: '+str(path))
        chunks = []
        while block := os.read(fd, 1048576):
            chunks.append(block)
        raw = b''.join(chunks)
        require(s == os.fstat(fd) and len(raw) == s.st_size, 'file read drift')
    finally:
        os.close(fd)
    require(pin is None or digest(raw) == pin, 'digest: '+str(path))
    return raw

def module(path, pin):
    raw = read(path, pin)
    m = types.ModuleType(Path(path).stem)
    m.__file__ = str(path)
    sys.modules[m.__name__] = m
    exec(compile(raw, str(path), 'exec', dont_inherit=True), m.__dict__)
    return m

def durable(path, raw, mode=0o600):
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'wb') as f:
        os.fchmod(f.fileno(), mode)
        s = os.fstat(f.fileno())
        require(stat.S_IMODE(s.st_mode) == mode and s.st_uid == s.st_gid == 1000
                and s.st_nlink == 1, 'new file authority')
        f.write(raw); f.flush(); os.fsync(f.fileno())
    d = os.open(Path(path).parent, os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(d)
    finally:
        os.close(d)

def save(name, value):
    durable(ROOT/name, (json.dumps(value, sort_keys=True, indent=2)+'\n').encode())

def record(name):
    return json.loads(read(ROOT/name))

def contract():
    return module(HERE/'contract.py', '39da13666f69e3566b1c23b46c13a1ad12504ce6bbc65297d72cc29c3cb92239')


def load_support():
    b = module(SUPPORT/'p6-observe-compose.py', '43b94ce677dcaa80b6937f7205362063da151f0608a99874b18b692ab8f2c8d6')
    o = b.observe_module()
    # S4: the reused P6 observer pins the pre-S2 image; rebind it to the running Core (b_gc_sha).
    o.GC_SHA = b_gc_sha()
    o.ENV = dict(o.ENV, BD_DISABLE_METRICS='1')
    owned = module(RUNNER, 'eddf5e1174a7b275abe280e91ea5c8ea0762600d38524ba9631f53fb4874cdf3')
    return b, o, owned

def pins():
    previous=json.loads(read(Path('/var/tmp/ga-mb91-terminal-20260930-r1/result.json'),
        'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'))
    require(previous['ok'] is True and previous['accepted_restoration_bound'] is True
        and previous['actual_host_verified'] is True and previous['worker_launched'] is False
        and previous['root_cache_protected_read_only'] is True
        and previous['terminal_suspension_endpoint_bound'] is True,
        'previous window was not proven restored')
    closed=json.loads(read(Path('/var/tmp/ga-mb91-r1-close-20260930T130514Z/result.json'),
        '64597781748525f5aa60b95334e372f6392bca9b020a3553f895deb1acba5540'))
    require(closed['ok'] is True and closed['closed_session'] is None
        and closed['open_sessions']==0 and closed['city_tmux_sessions']==0
        and closed['worktree_processes']==0, 'prior close lacks zero residue')
    # The R9-era diagnostic pins are not evidence for this window; its evidence is the prep root.
    read(PREP/'result.json', '74e69f6f1f43098f236cb89d0b35709fd15b6b05ea76460249769d1d428310d7')
    read(LAUNCH, '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea')
    read(PROVISIONER, '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35')
    read(WITNESS, WITNESS_SHA)
    read(PREP/'city.baseline.toml', CITY_SHA[0])
    read(PREP/'city.isolated.toml', CITY_SHA[1])
    read(PREP/'receipt.final.json', RECEIPT_SHA[1])
    # s2: the only effective order is the ga-odny nudge-on-route of the post-S2 core pack.
    orders = json.loads(read(PREP/'orders.isolated.json', 'b57082cf8c065a460e4b8414c380c4fdedde6cc83a3b5426206aa4f73f0d02a1'))
    require([(x['name'], x['source'], x['exec']) for x in orders['orders']] == [('nudge-on-route',
            '/home/loucmane/gascity/home/cache/repos/69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f/internal/bootstrap/packs/core/orders/nudge-on-route.toml', '$PACK_DIR/assets/scripts/nudge-on-route.sh')],
            'nudge-on-route is not the post-S2 core pack order')
    read(Path('/home/loucmane/gascity/home/cache/repos/69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f/internal/bootstrap/packs/core/assets/scripts/nudge-on-route.sh'), '7f49bf8b51b5d293bb0a62e82cf1dc2814c1e8cd888251d18c138e456324cc68')
    read(INPUT[0], INPUT_SHA[0])
    p = module(PROVISIONER, '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35')
    runner_path = RECEIPT.parent/'bin/gct-managed-worker-canary'
    runner_sha = '3beeedb2e5ce0723e5f745a05f1e2fdfa3ec27bee468284860e587e63c63e2e2'
    read(runner_path, runner_sha)
    for i in (0, 1):
        normalized = p.load_prototype(INPUT[i], dict(path=str(runner_path), sha256=runner_sha))
        require(digest(p.canonical_json(normalized)) == RECEIPT_SHA[i], 'receipt normalization drift')
        for profile in normalized['profiles']:
            argv = profile['argv']
            require(argv.count('--model') == 1 and argv[argv.index('--model')+1] == 'claude-opus-5-5', 'Opus-only selection')
    return p

def provider_pins(b, o):
    sha = '7b28b3e551e86818a2cdda3e53ed90c7072781e0a9354bd1ebf5d9425d579133'
    r = module(SUPPORT/'p6-readiness.py', sha)
    r._SOURCE_SHA = sha
    r.pin_inputs(b)
    return dict(worker=o.read_file(str(r.WORKER_NATIVE))[0],
        api_package=r.native_package_pair(b), subscription=o.read_file(str(r.SUBSCRIPTION))[0],
        provisioner=o.read_file(str(r.PROVISIONER))[0], runner=o.read_file(str(r.RUNNER))[0],
        api_link=dict(target=os.readlink(r.NATIVE_LINK),metadata=o.metadata(r.NATIVE_LINK.lstat())))

def dependency_image(value):
    # Historical reuse alone excludes read timestamps. Immediate preservation compares every
    # metadata field; access times only as account_read_times admits (s5).
    if isinstance(value, dict):
        return {k:dependency_image(v) for k,v in value.items() if k != 'atime_ns'}
    if isinstance(value, list):
        return [dependency_image(v) for v in value]
    return value

def approved_historical_image(prior):
    raise RuntimeError('historical disposition is not authority for this window')

def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    return type(value).__name__

def approved_epoch_image(prior, h):
    raise RuntimeError('historical disposition is not authority for this window')

RESTORED_PINS = {
    '/home/loucmane/gascity/city/city.toml': 'same-content',
    '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json': 'same-content',
    '/home/loucmane/gascity/city/.gc/runtime/suspension-state.json':
        'a4bcfdc35d60960fe22dfd3b58b6af8f37f09dcd444167c23779157ae3a31056'}

def approved_restore_image(prior):
    raise RuntimeError('historical disposition is not authority for this window')

def approved_coordinator_cache_image(prior):
    raise RuntimeError('historical disposition is not authority for this window')

CACHE_PREV_NS = 1790766204990519059
CACHE_PINNED_NS = 1790766204990519059
# Recovered r3 observation 9c2cf3244c5b922c9845c1a06d56e6ed9ef87e2ce8fcaacce67ee2ec566541ed. Fresh OBSERVE remains mandatory.

def approved_candidate_cache_image(prior):
    require(CACHE_PINNED_NS is not None, 'S2 cache disposition is not approved or pinned')
    value=json.loads(json.dumps(prior))
    entry=value['cache']['inventory'][CACHE_DIRECTORY]
    for key in ('mtime_ns','ctime_ns'):
        require(entry[key] == CACHE_PREV_NS, 'cache disposition preimage')
        entry[key] = CACHE_PINNED_NS
    return value

def account_read_times(a, z, window):
    # ga-f37t s5 disposition, operator-approved 2026-09-25 in place of FRESHEN, for independent review:
    # a read may advance an access time and nothing else. For every metadata record outside the cache
    # (cache-atime-policy-r1 accounts that) whose other fields are all equal, a changed atime_ns must
    # move forward, lie inside this comparison's observed clock window, and be a change Linux relatime
    # can write: the old access time was not newer than the modification or change time, or the new one
    # is at least 24 hours later. Only the comparison copy is aligned; both observations keep every
    # timestamp and the changes are returned as evidence. Once a lifecycle transition exists, the
    # suspension state stays governed by the suspension lineage and is not aligned here. Every other
    # field is still compared exactly.
    lifecycle = bool(list(ROOT.glob('suspension-*-intent.json')))
    changes = []
    def walk(x, y, path):
        if not (isinstance(x, dict) and isinstance(y, dict)):
            return
        if 'atime_ns' in x and 'atime_ns' in y:
            old, new = x['atime_ns'], y['atime_ns']
            require(type(old) is int and type(new) is int, 'access timestamp type')
            rest = {k: v for k, v in x.items() if k != 'atime_ns'}
            if old != new and rest == {k: v for k, v in y.items() if k != 'atime_ns'}:
                where = '/'.join(path)
                require(new > old and window['earliest_ns'] <= new <= window['latest_ns'],
                        'access time outside the observed window: ' + where)
                require(old <= max(x['mtime_ns'], x['ctime_ns'])
                        or new // 10**9 - old // 10**9 >= 24 * 3600,
                        'access time change relatime cannot write: ' + where)
                y['atime_ns'] = old
                changes.append(dict(path=list(path), before_ns=old, after_ns=new))
            return
        for key in x:
            if key not in y or (not path and key in ('cache', 'cache_access_clock', 'cache_access_mounts')):
                continue
            if lifecycle and path == ('pins',) and key == str(SUSPENSION):
                continue
            # R6 compares runtime children by identity only (directory_preservation); leave them alone.
            if path == ('directories',) and key == 'runtime_children':
                continue
            walk(x[key], y[key], path + (key,))
    walk(a, z, ())
    return changes

def stable_read_times(paths=None, now_ns=None):
    # Operator-authorized four-object accounting replaces the 19-hour scheduling
    # assumption. Reads remain relatime-bound; every actual delta is checked and
    # recorded at preservation, route and suspension comparison boundaries.
    now_ns = time.time_ns() if now_ns is None else now_ns
    for path in stable_read_paths() if paths is None else paths:
        flags = os.statvfs(path).f_flag
        require(flags & os.ST_RELATIME and not flags & os.ST_NOATIME,
                'access-time mount policy is not relatime: ' + str(path))
        s = os.lstat(path)
        require(all(type(v) is int and 0 <= v <= now_ns for v in
                    (s.st_atime_ns, s.st_mtime_ns, s.st_ctime_ns)),
                'invalid or future read metadata: ' + str(path))

def stable_read_paths():
    return (SUSPENSION, CITY, CITY/'.beads', RECEIPT.parent)

RECOVERY = None

def approved_recovery_image(prior, root, result_sha):
    raise RuntimeError('historical disposition is not authority for this window')

def directories(o):
    fd = os.open(CITY, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        names = sorted(os.listdir(fd))
        city = {'.':o.metadata(os.fstat(fd))}
        for name in names:
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(not stat.S_ISLNK(s.st_mode), 'city child symlink: '+name)
            city[name] = o.metadata(s)
        require(names == sorted(os.listdir(fd)), 'city entries changed during observation')
    finally:
        os.close(fd)
    provision = o.tree_snapshot(RECEIPT.parent, protected=True)['inventory']
    require(set(provision) == {'.','receipt.json','bin','bin/gct-managed-worker-canary'},
            'unexpected provisioning entry')
    runtime_children={}
    for name in ('.gc','.beads'):
        fd=os.open(CITY/name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
        try:
            names=sorted(os.listdir(fd))
            runtime_children[name]={child:o.metadata(os.stat(child,dir_fd=fd,follow_symlinks=False)) for child in names}
            require(names==sorted(os.listdir(fd)),'runtime children changed during observation')
        finally:os.close(fd)
    return dict(city=city, provision=provision, runtime_children=runtime_children)

def directory_preservation(before, after, *, read_window=None):
    a=json.loads(json.dumps(before)); z=json.loads(json.dumps(after))
    # Runtime children legitimately receive writes. Bind names and identity,
    # retaining full metadata in evidence; root metadata remains exact below.
    x=a.pop('runtime_children');y=z.pop('runtime_children')
    require(set(x)==set(y)=={'.gc','.beads'},'runtime inventory roots')
    for name in x:
        require(set(x[name])==set(y[name]),'runtime direct-child change')
        for child in x[name]:
            for key in ('device','inode','type','uid','gid','mode'):
                require(x[name][child][key]==y[name][child][key],'runtime child identity/authority drift')
    if read_window is not None:
        changes = []
        for section, key, path, renamed in (
            ('city', '.', str(CITY), True),
            ('provision', '.', str(RECEIPT.parent), True),
            ('city', '.beads', str(CITY/'.beads'), False)):
            aligned, delta = read_time_policy().metadata(path, a[section][key],
                z[section][key], read_window, renamed=renamed)
            z[section][key] = aligned
            changes.extend(delta)
        read_time_evidence('directories', before, after, changes, read_window)
    for section, target in [('city','city.toml'),('provision','receipt.json')]:
        require(set(a[section]) == set(z[section]), 'writable directory entry drift')
        a[section].pop(target); z[section].pop(target)
        # Atomic rename changes the parent directory's time only.
        for key in ('mtime_ns','ctime_ns'):
            a[section]['.'].pop(key); z[section]['.'].pop(key)
    require(a == z, 'unrelated writable directory authority drift')

def host(o):
    h = o.host_observation()
    require(h['host']['boot'] == '3f1f4534-ea17-4cb4-b2f2-a3f8bce1a8fa', 'boot drift')
    # The sequence 16 supervisor epoch (ga-bebv S2); the broker and the signer are unchanged.
    for name, pid, start in [('core','466463','517633096016'), ('signer','2310','39660502'),
                             ('broker','2940285','123477220085')]:
        require(h[name]['MainPID'] == pid and h[name]['ExecMainStartTimestampMonotonic'] == start, name+' epoch drift')
    return h

def snapshot(name, b, o):
    prior = json.loads(read(ACCEPTED, ACCEPTED_SHA))
    h = host(o)
    files = {path: o.read_file(path)[0] for path in prior['pins']}
    value = dict(host=h, pins=files, cache=o.tree_snapshot(b.CACHE, cache=True),
                 protected={str(p): o.tree_snapshot(p, protected=True) for p in b.PROTECTED})
    require(h == host(o), 'host changed during snapshot')
    if name == 'before.json':
        # Compare against the completed restored window with this package's exact cache-directory time pair only.
        require(RECOVERY is None, 'no recovery admission in this window')
        image = approved_candidate_cache_image({key: prior[key] for key in ACCEPTED_KEYS})
        if dependency_image(image) != dependency_image(value):
            save('before-refused-observation.json',value)
            raise RuntimeError('accepted baseline drift')
    value['providers'] = provider_pins(b,o)
    accepted_provider=json.loads(read(PROVIDER,PROVIDER_SHA))
    require(dependency_image(value['providers']) == dependency_image(accepted_provider), 'accepted provider drift')
    value['directories'] = directories(o)
    save(name, value)

def preservation(before, after, city_pin, receipt_pin, *, read_window=None):
    a = json.loads(json.dumps(before)); z = json.loads(json.dumps(after))
    if list(ROOT.glob('suspension-*-intent.json')):
        endpoint = verified_lifecycle(terminal=True)
        require(suspension_pin_equal(a['pins'][SUSPENSION],record('suspension-baseline.json')['pin']), 'suspension original binding')
        require(suspension_pin_equal(z['pins'][SUSPENSION],endpoint), 'suspension final binding')
        z['pins'][SUSPENSION] = endpoint
        a['pins'][SUSPENSION] = endpoint
    directory_preservation(a.pop('directories'),z.pop('directories'),read_window=read_window)
    for path, expected, mode in [(str(CITY/'city.toml'),city_pin,0o644), (str(RECEIPT),receipt_pin,0o600)]:
        first = a['pins'].pop(path); current = z['pins'].pop(path)
        require(current['sha256'] == expected, 'postimage '+path)
        for key in ('uid','gid','mode','type','nlink'):
            require(first['metadata'][key] == current['metadata'][key], 'authority changed '+path)
        require(current['metadata']['mode'] == mode, 'postimage mode')
    require(a == z, 'unrelated snapshot drift')

def suspension_record(o):
    pin,raw = o.read_file(SUSPENSION,collect=True)
    return dict(pin=pin,raw=raw.decode('utf-8'))

def lifecycle_records(s):
    intents={p.name[len('suspension-'):-len('-intent.json')] for p in ROOT.glob('suspension-*-intent.json')}
    events={p.name[len('suspension-'):-len('-event.json')] for p in ROOT.glob('suspension-*-event.json')}
    require(intents == events and intents <= set(s.ACTIONS), 'incomplete/unreviewed suspension transition')
    records=[]
    for action in s.ACTIONS:
        if action not in events:continue
        e=record('suspension-'+action+'-event.json')
        intent=record('suspension-'+action+'-intent.json')
        require(intent == dict(action=action,before=e['before'],before_sha256=e['before']['pin']['sha256']),
            'suspension pre-command binding')
        require(e['intent'] == record(action+'-started.json') and e['result'] == record(action+'-phase.json'),
            'suspension phase record binding')
        records.append(e)
    return records

def verified_lifecycle(terminal=False):
    s=module(HERE/'suspension-lineage.py',LINEAGE_SHA)
    b,o,owned=load_support()
    require(not list(ROOT.glob('suspension-*-failure.json'))
        and not list(ROOT.glob('suspension-*-refused-after.json')), 'unreviewed stranded lifecycle')
    return s.chain(record('suspension-baseline.json'),lifecycle_records(s),
        suspension_record(o),str(ROOT),terminal,read_account=suspension_read_equal)

def active_epoch(o):
    # Lifecycle observations cannot use the quiescent observer while the one
    # authorized worker is active. Keep actual process and namespace identity.
    expected=record('before.json')['host']
    pid=expected['host']['pid']; proc=Path('/proc')/str(pid)
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected['host']['boot'],'lifecycle boot drift')
    fd=os.pidfd_open(pid)
    try:
        poll=select.poll();poll.register(fd,select.POLLIN)
        require(not poll.poll(0) and proc.stat().st_uid==1000,'supervisor no longer live')
        fields=(proc/'stat').read_text().rsplit(') ',1)[1].split()
        require(fields[0] not in ('Z','X') and fields[19]==expected['host']['start'],'supervisor process drift')
        spaces={key:os.readlink(proc/'ns'/key) for key in o.SPACES}
        require(spaces==expected['namespaces']=={key:os.readlink('/proc/self/ns/'+key) for key in o.SPACES},'lifecycle not actual host')
        require(o.process_image(pid,o.GC)==b_gc_sha(),'supervisor image drift')
        for key,unit,user in [('core',o.SERVICE,True),('signer','gas-city-managed-git-signerd.service',False),
                             ('broker','gas-city-privileged-provision.service',False)]:
            require(o.service(unit,user)==expected[key],'lifecycle service drift '+key)
        require(not poll.poll(0),'supervisor terminated')
    finally:os.close(fd)

def b_gc_sha():
    return '5802a35645280790f1cda16dff3c71445be7146e42021f3be5fd481e79138444'

def suspension_atime_stable(flags, metadata, now_ns):
    require(flags & (os.ST_NOATIME|os.ST_RELATIME), 'strict/unknown atime policy')
    if flags & os.ST_NOATIME:
        return True
    # Linux relatime updates on atime <= mtime/ctime or age >= 24h. Require
    # strict freshness and a consumed endpoint; keep exact atime comparisons.
    return (metadata['atime_ns'] > max(metadata['mtime_ns'],metadata['ctime_ns'])
        and 0 <= now_ns-metadata['atime_ns'] < 3600*10**9)

RUNTIME_PROBE_PARTIAL = ['runtime status probe incomplete; non-running agent rows are unknown']

def runtime_probe_partial(value):
    # ga-gegx s2 r2: the one partial gc status Core reports when only its runtime (tmux) probe timed out.
    return value.get('partial') is True and value.get('partial_errors') == RUNTIME_PROBE_PARTIAL

def suspension_status_matches(value, expected, probe_partial=False, *, census, action):
    # probe_partial admits exactly the runtime-probe partial status and nothing else incomplete.
    require(value.get('ok') is True and value.get('city_path')==str(CITY)
        and value.get('running') is True
        and ((probe_partial and runtime_probe_partial(value))
             or (not value.get('partial') and not value.get('partial_errors')))
        and value['controller']['running'] is True and value['controller']['pid']==466463,
        'incomplete/wrong-controller suspension observation')
    rows=value['rigs']; rigs={r['name']:r['suspended'] for r in rows}
    require(len(rows)==len(rigs)==4 and set(rigs)=={'gascity','gas-city-template','hpfetcher','blog'}
        and all(type(v) is bool for v in rigs.values()) and type(value['suspended']) is bool,
        'rig suspension observation schema')
    running=contract().running_rows(value,census,action)
    signals=value['health'].get('signals',[])
    require(isinstance(signals,list) and set(signals)<= {'city_suspended','no_agents_running'}
        and ('city_suspended' not in signals or value['suspended'])
        and ('no_agents_running' not in signals or not running),'unexpected city health signal')
    return (value['suspended']==expected['city']['suspended']
        and all(v==expected['rigs'][name]['suspended'] for name,v in rigs.items()))

BARRIER_SECONDS = 90
PROBE_LATE = 25

def observed_suspension_endpoint(action,b,o,owned):
    s=module(HERE/'suspension-lineage.py',LINEAGE_SHA)
    flags=os.statvfs(SUSPENSION).f_flag
    require(flags & (os.ST_NOATIME|os.ST_RELATIME),'strict/unknown atime policy')
    first=suspension_record(o)
    save('suspension-'+action+'-barrier-initial.json',first)
    expected=s.image(first)
    # ga-gegx s2 r2: a status whose only gap is the runtime probe is not yet an observation. It is
    # recorded and polled again. A suspend (city-suspend, rig-suspend) accepts it only in the last
    # PROBE_LATE seconds of the deadline, with every other check unchanged. The window's later CLOSE
    # proves the process state without this status: no session in gc session list, no session on the
    # city tmux server, and no process whose argv or cwd names the worktree. A resume never accepts it.
    deadline=time.monotonic()+BARRIER_SECONDS;index=0
    while True:
        remaining=deadline-time.monotonic()
        require(remaining>0,'suspension observation timeout; no lifecycle retry')
        r=phase(action+'-status-'+str(index),GC+['status','--json'],b,owned,timeout=min(15,remaining))
        current=suspension_record(o)
        save('suspension-'+action+'-barrier-observed-'+str(index)+'.json',current)
        # A normal supported controller read may advance only access time.
        require(suspension_read_equal(first,current),'suspension changed during controller observation')
        status=json.loads(r['stdout'])
        census=json.loads(phase(action+'-sessions-'+str(index),GC+['session','list','--json'],
            b,owned,timeout=min(15,max(1,deadline-time.monotonic())))['stdout'])
        launch=module(HERE/'launch-contract.py','96560832152e6f653e305ddb2f95b5fcc43f73f6a22b05f01695dfb37016d489')
        if launch.retry_status(status,census,action):
            save('suspension-'+action+'-torn-read-'+str(index)+'.json',dict(status=status,census=census))
            index+=1
            time.sleep(min(1,max(0,deadline-time.monotonic())))
            continue
        probe=runtime_probe_partial(status)
        late=deadline-time.monotonic()<PROBE_LATE
        if probe:
            save('suspension-'+action+'-barrier-partial-'+str(index)+'.json',
                 dict(partial_errors=status.get('partial_errors'),late=late))
        if probe and not (late and action.endswith('-suspend')):
            index+=1
            time.sleep(min(1,max(0,deadline-time.monotonic())))
            continue
        if (suspension_status_matches(status,expected,probe,census=census,action=action)
                and suspension_atime_stable(flags,current['pin']['metadata'],time.time_ns())):
            active_epoch(o)
            require(current==suspension_record(o),'suspension endpoint not stable')
            if probe:
                save('suspension-'+action+'-partial-accepted.json',dict(index=index,status=status))
            return current
        index+=1
        time.sleep(min(1,max(0,deadline-time.monotonic())))

def lifecycle(action,b,o,owned):
    # The enclosing reviewed runbook owes the fresh sole-task queue proof before
    # invoking resume. This helper records operations, not dispatch authorization.
    s=module(HERE/'suspension-lineage.py',LINEAGE_SHA)
    require(action in s.ACTIONS,'unknown lifecycle action')
    require(not list(ROOT.glob('restore-*')) and not (ROOT/'restored.json').exists()
        and not (ROOT/'stage-refused.json').exists()
        and not list(ROOT.glob('suspension-*-failure.json'))
        and not list(ROOT.glob('suspension-*-refused-after.json')),
        'window terminal/refusal state forbids lifecycle')
    outputs=[action+'-started.json',action+'-phase.json']+[
        'suspension-'+action+suffix for suffix in ('-intent.json','-event.json',
            '-after-observation.json','-failure.json','-refused-after.json')]
    require(all(not os.path.lexists(ROOT/name) for name in outputs),'lifecycle output already exists')
    require(not list(ROOT.glob(action+'-status-*'))
        and not list(ROOT.glob('suspension-'+action+'-barrier-*')),
        'lifecycle status/barrier output already exists')
    require(record('stage-pass.json')==dict(ok=True,worker_launched=False),'window not staged')
    read(CITY/'city.toml',CITY_SHA[1]);read(RECEIPT,RECEIPT_SHA[1])
    active_epoch(o)
    previous=lifecycle_records(s);seen=[r['action'] for r in previous]
    permitted={():['rig-resume'],('rig-resume',):['city-resume','rig-suspend'],
        ('rig-resume','city-resume'):['city-suspend'],
        ('rig-resume','city-resume','city-suspend'):['rig-suspend']}
    require(action in permitted.get(tuple(seen),[]),'lifecycle operation order')
    before=suspension_record(o)
    s.chain(record('suspension-baseline.json'),previous,before,str(ROOT),read_account=suspension_read_equal)
    if action.endswith('resume'):foreign_queue(action+'-before',b,o,owned)
    save('suspension-'+action+'-intent.json',dict(action=action,before=before,before_sha256=before['pin']['sha256']))
    try:
        result=phase(action,s.ACTIONS[action][2],b,owned)
        after=observed_suspension_endpoint(action,b,o,owned)
    except BaseException as exc:
        save('suspension-'+action+'-failure.json',dict(error=str(exc),automatic_replay=False))
        complete_containment()
        save('suspension-'+action+'-refused-after.json',suspension_record(o))
        raise
    save('suspension-'+action+'-after-observation.json',after)
    e=dict(action=action,before=before,after=after,intent=record(action+'-started.json'),result=result)
    s.chain(record('suspension-baseline.json'),previous+[e],after,str(ROOT),read_account=suspension_read_equal)
    active_epoch(o)
    save('suspension-'+action+'-event.json',e)
    foreign_queue(action+'-after',b,o,owned,fatal=action.endswith('resume'))
    print(json.dumps(dict(ok=True,action=action,phase_only=True)))

def phase(name, argv, b, owned, expected=(0,), timeout=120):
    require(not (ROOT/(name+'-phase.json')).exists(), 'phase already consumed')
    save(name+'-started.json',dict(phase=name,argv=argv,cwd=str(ROOT)))
    r = owned._run_owned_phase(name=name, argv=argv, cwd=ROOT,
        environment=dict(b.ENV, BD_DISABLE_METRICS='1'), timeout=timeout,
        evidence_path=ROOT/(name+'-phase.json'))
    c = r['cleanup']
    require(c['direct_child_reaped'] and c['owned_process_group_gone'] and not c['failures'] and not c['unexpected_survivors'], 'ambiguous containment '+name)
    require(not r['timed_out'] and not r['primary_error'] and r['exit_code'] in expected, 'command refused '+name)
    return r

def complete_containment():
    starts={p.name[:-len('-started.json')]:p for p in ROOT.glob('*-started.json')}
    terminals={p.name[:-len('-phase.json')]:p for p in ROOT.glob('*-phase.json')}
    require(set(starts) == set(terminals), 'missing phase containment evidence')
    for name,path in terminals.items():
        intent=json.loads(read(starts[name])); r=json.loads(read(path)); c=r['cleanup']
        require(intent == dict(phase=r['phase'],argv=r['argv'],cwd=r['cwd']), 'phase evidence identity drift')
        require(c['direct_child_reaped'] and c['owned_process_group_gone'] and not c['failures']
                and not c['unexpected_survivors'], 'ambiguous prior containment')

def invocation(*args):
    return ['/usr/bin/python3','-I','-S','-B',str(LAUNCH),__file__,_SOURCE_SHA,*args]

def city_entries():
    fd=os.open(CITY,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        require(CITY.lstat()==before,'city directory identity changed')
        names=sorted(os.listdir(fd))
        entries={name:os.stat(name,dir_fd=fd,follow_symlinks=False) for name in names}
        require(not any(stat.S_ISLNK(s.st_mode) for s in entries.values()),'city child symlink requires review')
        require(sorted(os.listdir(fd))==names,'city directory entry set changed')
        require(entries=={name:os.stat(name,dir_fd=fd,follow_symlinks=False) for name in names},
                'city child metadata changed')
        require(os.fstat(fd)==before and CITY.lstat()==before,'city directory changed')
        return tuple(CITY/name for name in names)
    finally:os.close(fd)

def confined(args, writable=None):
    argv = ['/usr/bin/bwrap','--ro-bind','/','/']
    if writable == 'receipt':
        argv += ['--bind',str(RECEIPT.parent),str(RECEIPT.parent),
                 '--ro-bind',str(RECEIPT.parent/'bin'),str(RECEIPT.parent/'bin')]
    elif writable == 'city':
        argv += ['--bind',str(CITY),str(CITY)]
        for entry in city_entries():
            require(not entry.is_symlink(), 'city child symlink requires review: '+entry.name)
            if entry.name != 'city.toml':
                argv += ['--ro-bind',str(entry),str(entry)]
    return argv+['--unshare-net','--unshare-pid','--new-session','--die-with-parent',
                 '--proc','/proc','--dev','/dev','--',*invocation(*args)]

def mount_proof(writable):
    rows = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        f = line.split()
        p = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1],8)), f[4])
        require('\\' not in p, 'mount escape')
        rows.append((p,f[5].split(',')))
    def flags(path):
        return max(((p,v) for p,v in rows if p=='/' or str(path)==p or str(path).startswith(p+'/')), key=lambda x:len(x[0]))[1]
    for path in [Path('/home/loucmane/gascity/home/cache/repos'),CITY/'.gc/platform/assets',CITY/'.gc/platform/backups',ROOT]:
        require('ro' in flags(path), 'protected writable '+str(path))
        require(not any('rw' in v for p,v in rows if p.startswith(str(path)+'/')), 'protected writable descendant')
    if writable == 'city':
        require('rw' in flags(CITY) and 'rw' in flags(CITY/'city.toml'), 'city not writable')
        for p in city_entries():
            if p.name != 'city.toml':
                require('ro' in flags(p), 'other city child writable')
    elif writable == 'receipt':
        require('rw' in flags(RECEIPT.parent) and 'ro' in flags(RECEIPT.parent/'bin'), 'receipt mount')
    else:
        require('ro' in flags(CITY) and 'ro' in flags(RECEIPT), 'read-only phase mounts')

def atomic_replace(path, raw, expected, mode, suffix):
    require(digest(read(path)) == expected, 'atomic preimage drift')
    s = path.lstat()
    require(s.st_uid == s.st_gid == 1000 and stat.S_IMODE(s.st_mode) == mode, 'atomic authority')
    temp = path.parent/('.ga-mb91-'+suffix+'.tmp')
    durable(temp, raw, mode)
    t = temp.lstat()
    require(t.st_uid == s.st_uid and t.st_gid == s.st_gid and t.st_nlink == 1
            and stat.S_ISREG(t.st_mode) and stat.S_IMODE(t.st_mode) == mode
            and read(temp) == raw, 'atomic staged authority')
    require(path.lstat() == s and digest(read(path)) == expected, 'atomic recheck drift')
    os.replace(temp, path)
    d = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(d)
    finally:
        os.close(d)
    require(read(path) == raw and stat.S_IMODE(path.stat().st_mode) == mode, 'atomic postimage')

def inner(kind, direction, b):
    require(direction in ('0','1'), 'direction')
    i = int(direction)
    p = pins()
    if kind == 'city':
        mount_proof('city')
        source = PREP/('city.isolated.toml' if i else 'city.baseline.toml')
        atomic_replace(CITY/'city.toml', read(source, CITY_SHA[i]), CITY_SHA[1-i], 0o644, 'stage' if i else 'restore')
        print(json.dumps(dict(ok=True, city_sha256=CITY_SHA[i])))
        return
    require(kind in ('check','apply','verify'), 'inner kind')
    mount_proof('receipt' if kind == 'apply' else None)
    expected = RECEIPT_SHA[i] if kind == 'verify' else RECEIPT_SHA[1-i]
    read(RECEIPT, expected)
    argv = ['/usr/bin/python3','-I','-S','-B',str(PROVISIONER),'--city',str(CITY),
            '--receipt-input',str(INPUT[i]),'--consumer-witness',str(WITNESS),
            '--consumer-witness-sha256',WITNESS_SHA,'--'+('apply' if kind=='apply' else 'check'),'--json']
    r = subprocess.run(argv, env=b.ENV, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
    value = json.loads(r.stdout)
    require(value['schema']=='gc.managed-worker-provision-check.v1', 'provision schema')
    if kind == 'check':
        require(r.returncode==1 and value['ok'] is False and value['drift']==['receipt.sha256'], 'preflight difference')
    else:
        require(r.returncode==0 and value['ok'] is True and value['drift']==[], 'provision refusal')
        read(RECEIPT, RECEIPT_SHA[i])
    print(json.dumps(dict(ok=True, report=value)))

def reload(name, i, b, owned):
    save(name+'-intent.json',dict(revision=REVISION[i]))
    result = phase(name,GC+['reload','--json'],b,owned)
    v = json.loads(result['stdout'])
    require(v['ok'] and not v['async'] and not v['soft'] and v['outcome'] in ('applied','no_change') and v['revision']==REVISION[i], 'reload acknowledgement')
    deadline=time.monotonic()+30
    index=0
    while True:
        remaining=deadline-time.monotonic()
        require(remaining>0, 'controller revision observation timed out; do not repeat reload')
        trace = phase(name+'-trace-'+str(index),GC+['trace','show','--type','cycle_result','--since','2m','--json'],b,owned,timeout=min(15,remaining))
        rows = json.loads(trace['stdout'])['records']
        newest = max(rows,key=lambda x:x['seq']) if rows else None
        if newest:
            require(newest['controller_pid']==466463, 'controller trace epoch drift')
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(newest['ts'].replace('Z','+00:00'))).total_seconds()
            require(0<=age<=120 and newest['fields']['active_template_count']==0, 'stale/active revision')
            if newest['config_revision']==REVISION[i] and newest['completion_status']=='completed':
                break
        index+=1
        # This existing black-box trace command has no completion subscription.
        time.sleep(min(1,max(0,deadline-time.monotonic())))
    save(name+'-accepted.json',dict(ack=v,cycle=newest))

def transition(i, b, o, owned, prefix):
    host(o)
    current_city = digest(read(CITY/'city.toml'))
    require(current_city in CITY_SHA, 'unknown city image')
    current_receipt = digest(read(RECEIPT))
    require(current_receipt in RECEIPT_SHA, 'unknown receipt image')
    snapshot(prefix+'-immediate.json',b,o)
    preservation(record('before.json'),record(prefix+'-immediate.json'),current_city,current_receipt)
    if current_city != CITY_SHA[i]:
        save(prefix+'-city-intent.json',dict(before=current_city,after=CITY_SHA[i]))
        phase(prefix+'-city',confined(['inner','city',str(i)],'city'),b,owned)
    reload(prefix+'-reload',i,b,owned)
    host(o)
    if current_receipt != RECEIPT_SHA[i]:
        phase(prefix+'-receipt-check',confined(['inner','check',str(i)]),b,owned)
        snapshot(prefix+'-before-receipt.json',b,o)
        preservation(record('before.json'),record(prefix+'-before-receipt.json'),CITY_SHA[i],current_receipt)
        save(prefix+'-receipt-intent.json',dict(before=current_receipt,after=RECEIPT_SHA[i]))
        phase(prefix+'-receipt-apply',confined(['inner','apply',str(i)],'receipt'),b,owned)
    phase(prefix+'-receipt-verify',confined(['inner','verify',str(i)]),b,owned)
    host(o)

def verify_prelaunch_permissions():
    guard=module(HERE/'permissions-baseline.py','c1c30b227a6e65dd900e9a54aae5e67821aa771b9a7e9285aff99aa4f22e47d9')
    guard.verify(read,lambda path,pin,name:module(path,pin))



def verify_process_record(o):
    # The recorder does not grant authority. Bind it to the separately accepted
    # host epoch and retain every native city identity and quiescence check.
    module(Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-6utp-activation-r10/candidate_git.py'),
           'd2894e829618ad1fdcb5640b47b99baa3c783173acccb4f7f5918c958823bebe')
    pr=module(Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-6utp-activation-r10/preroute.py'),
           'd52e09214381fb6ce92becc2aed72fd1318821fd327ad3fb07e4974b57a3f4c6')
    value=json.loads(read(Path('/tmp/ga-mb91-process-record-20260930-r1.json'),'10b956a5458bb88443789cf3fbde1c1abdf99dbcaabc542fa92369db0679e086'))
    require(isinstance(value,dict) and set(value)==pr.RECORD_KEYS,'process record shape')
    before=host(o)
    core=before['core']
    require(value['controller']['pid']==int(core['MainPID'])
        and value['controller']['start']==int(core['ExecMainStartTimestampMonotonic'])*os.sysconf('SC_CLK_TCK')//1000000,
        'process record disagrees with accepted host epoch')
    problems=pr.city_problems(pr.user_slice(1000),value)
    require(not problems,'process record or city quiescence drift: '+str(problems))
    require(host(o)==before,'host changed during process record validation')

def main():
    require(globals().get('_SOURCE_SHA') and os.getuid()==os.geteuid()==1000, 'bound user entry')
    read(Path(__file__),_SOURCE_SHA)
    b,o,owned = load_support()
    pins()
    read(HERE/'suspension-lineage.py',LINEAGE_SHA)
    if len(sys.argv)==4 and sys.argv[1]=='inner':
        inner(sys.argv[2],sys.argv[3],b); return
    if len(sys.argv)==3 and sys.argv[1]=='lifecycle':
        lifecycle(sys.argv[2],b,o,owned);return
    require(len(sys.argv)==2 and sys.argv[1] in ('preflight','stage','restore'), 'unknown action')
    action=sys.argv[1]
    if action=='preflight':
        verify_process_record(o)
        verify_prelaunch_permissions()
        stable_read_times()
        ROOT.mkdir(mode=0o700)
        save('preflight-intent.json',dict(executor_sha256=_SOURCE_SHA))
        host(o)
        module(HERE/'fresh-admission.py','3c252f11156542cb92907e1b791ce172917692a3f2ae6501f512a4bf9e9ee7ae').admit(types.SimpleNamespace(**globals()),b,owned)
        read(CITY/'city.toml',CITY_SHA[0]); read(RECEIPT,RECEIPT_SHA[0])
        durable(ROOT/'city.before.toml',read(CITY/'city.toml'),0o644)
        durable(ROOT/'receipt.before.json',read(RECEIPT))
        # Build bwrap arguments now so unsupported child layouts refuse before staging.
        confined(['inner','city','1'],'city')
        result=phase('git-head',HARDENED+['rev-parse','--verify','HEAD^{commit}'],b,owned)
        require(result['stdout'].strip()==BASE,'worker base drift')
        result=phase('git-status',HARDENED+['status','--porcelain=v1','--ignored','--untracked-files=all','-z'],b,owned)
        contract().validate_rule_status(result['stdout'].encode())
        snapshot('before.json',b,o)
        baseline=suspension_record(o)
        module(HERE/'suspension-lineage.py',LINEAGE_SHA).image(baseline)
        require(suspension_pin_equal(record('before.json')['pins'][SUSPENSION],baseline['pin']),'suspension baseline drift')
        save('suspension-baseline.json',baseline)
        common=module(HERE/'common-snapshot-r1.py','34ce775b59318acc01499e3cc27e9d09c4d39d8bb64d723b7970fc6dcf8b6301')
        common_before=common.observe()
        require(common_before['candidate_branch']==BASE and not common.baseline_problems(common_before),
            'candidate common Git baseline')
        require(not common.compare(common_before,common.observe()),'common Git changed during baseline')
        save('common-before.json',common_before)
        validator=module(HERE/'startup-validation.py','41f41ebba0bc7f74dbb5221d68472e274c6dc482d7564a72ec828b75851d44e3')
        # No circular imports: this reader is the existing bounded worker probe.
        probe=module(HERE/'worker-startup.py','327d9928b4167642d67a1899f64dafca36ba460012a6ea7e03dfb04bbb86d0e1')
        workspace_before=validator.workspace_image(WORK,probe.read_regular)
        # Fresh workspace has no Core hook yet. The worker probe and
        # independent source-release check verify it after materialization.
        launch=module(HERE/'launch-contract.py','96560832152e6f653e305ddb2f95b5fcc43f73f6a22b05f01695dfb37016d489')
        module(HERE/'fresh-workspace.py','5b2dde047fcf7123ef3304ea057f20ca79d26222a360ee617e5415aaf43f0812').verify(types.SimpleNamespace(**globals()),workspace_before,contract().RUNTIME_IMAGE)
        require(workspace_before==validator.workspace_image(WORK,probe.read_regular),'workspace baseline drift')
        save('workspace-before.json',workspace_before)
        claim_branch=phase('claim-store-branch',['/usr/bin/git','--no-optional-locks','-C',
            '/home/loucmane/gascity/city/rigs/gascity','symbolic-ref','--short','HEAD'],b,owned)
        require(claim_branch['stdout'].strip()==validator.CLAIM_BRANCH,'claim store branch drift')
        client_paths=('/home/loucmane/.codex/config.toml','/home/loucmane/.codex/hooks.json',
            '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy',
            '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy.json')
        save('client-inputs-before.json',{path:digest(probe.read_regular(Path(path))) for path in client_paths})
        foreign_queue('preflight',b,o,owned,capture=True,scoped=False)
        save('preflight-pass.json',dict(ok=True,executor_sha256=_SOURCE_SHA,worker_launched=False))
    elif action=='stage':
        verify_process_record(o)
        verify_prelaunch_permissions()
        require(record('preflight-pass.json')['executor_sha256']==_SOURCE_SHA,'preflight binding')
        module(HERE/'fresh-admission.py','3c252f11156542cb92907e1b791ce172917692a3f2ae6501f512a4bf9e9ee7ae').recheck(types.SimpleNamespace(**globals()),b,owned)
        foreign_queue('stage-before',b,o,owned,scoped=False)
        save('stage-consumed.json',dict(executor_sha256=_SOURCE_SHA))
        try:
            transition(1,b,o,owned,'stage')
            snapshot('staged.json',b,o)
            preservation(record('before.json'),record('staged.json'),CITY_SHA[1],RECEIPT_SHA[1])
            foreign_queue('stage-after',b,o,owned)
            save('stage-pass.json',dict(ok=True,worker_launched=False))
        except BaseException as exc:
            save('stage-refused.json',dict(error=str(exc),automatic_replay=False))
            raise
    else:
        require((ROOT/'stage-consumed.json').exists(),'no owned window to restore')
        foreign_queue('restore-before',b,o,owned)
        save('restore-consumed.json',dict(executor_sha256=_SOURCE_SHA))
        # Restoration is explicit, not an exception handler that guesses whether
        # a timed-out mutation completed. The coordinator must inspect disposition.
        complete_containment()
        verified_lifecycle(terminal=True)
        transition(0,b,o,owned,'restore')
        snapshot('restored.json',b,o)
        preservation(record('before.json'),record('restored.json'),CITY_SHA[0],RECEIPT_SHA[0])
        foreign_queue('restore-after',b,o,owned,scoped=False)
        save('restore-pass.json',dict(ok=True,full_platform_integrity_still_required=True))
    print(json.dumps(dict(ok=True,action=action,worker_launched=False)))

"""Source-included operational adapters for the exact four-object exception."""


def read_time_policy():
    return module(HERE/'read-time-accounting.py', '47b97861d19cf4c8e14687bb2428f9b70863815ce32c5e1c1e3b1d6bd0a7a22c')


def read_time_bounds(baseline_clock=None):
    policy = module(HERE/'cache-atime-policy-r1.py',
        '61c3e38e4475061c658a853036922742ab2ce69d44a4577e3f91490674047783')
    def sample():
        first = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        real = time.time_ns()
        last = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        return dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            real_ns=real, boot_before_ns=first, boot_after_ns=last)
    if baseline_clock is None:
        baseline_clock = record('before.json')['cache_access_clock']
    return policy.bounds(baseline_clock,
                         dict(start=sample(), end=sample()))


def read_time_evidence(kind, before, after, changes, window):
    if not changes:
        return
    require(kind in ('suspension', 'directories', 'routes'), 'read-time evidence kind')
    value = dict(schema='ga-mb91.four-object-read-times.v1', kind=kind,
        before=before, after=after, changes=changes, window=window,
        timestamp_writes=False, worker_authority_changed=False)
    pin = digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    name = 'read-times-'+kind+'-'+pin+'.json'
    if os.path.lexists(ROOT/name):
        require(record(name) == value, 'read-time accounting collision')
    else:
        save(name, value)


def suspension_read_equal(before, after):
    window = read_time_bounds()
    aligned, changes = read_time_policy().suspension(before, after, window)
    require(before == aligned, 'unrecorded suspension mutation')
    read_time_evidence('suspension', before, after, changes, window)
    return True


def suspension_pin_equal(before, after):
    window = read_time_bounds()
    require(set(before) == set(after) == {'sha256', 'metadata'}
        and before['sha256'] == after['sha256'], 'suspension pin content changed')
    aligned, changes = read_time_policy().metadata(str(SUSPENSION),
        before['metadata'], after['metadata'], window)
    require(before['metadata'] == aligned, 'suspension pin metadata changed')
    read_time_evidence('suspension', before, after, changes, window)
    return True


def route_read_account(before, after, window, *, regenerated=False):
    # Only the city .beads parent participates. Route-file metadata, content,
    # other rigs and native regeneration proofs remain the caller's exact checks.
    require(str(CITY) in before and str(CITY) in after, 'city route mirror absent')
    aligned, changes = read_time_policy().metadata(str(CITY/'.beads'),
        before[str(CITY)]['parent'], after[str(CITY)]['parent'], window,
        renamed=regenerated)
    result = json.loads(json.dumps(after))
    result[str(CITY)]['parent'] = aligned
    read_time_evidence('routes', before, after, changes, window)
    return result




def foreign_queue(label,b,o,owned,**kwargs):
    guard=module(HERE/'queue-guard.py','b5b5688c8e8277188fd2437e65751ce952012f57efeee03a516d05aabd641582')
    return guard.checkpoint(types.SimpleNamespace(**globals()),label,b,o,owned,**kwargs)

if __name__=='__main__':
    main()
