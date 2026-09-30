"""Exact one-file archival recovery; no lifecycle, source repair, or admission."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import types

HERE = Path(__file__).parent
PACKAGE = HERE.parent
MANIFEST_SHA = '561f1622013e564cce073c1da0235abaa7cb4a9eb503b49baeee74da46a7cb6a'
REL = '.gc/scripts/gc-beads-bd.sh'
HELPER_SHA = 'a7bcaa7cce9261b987bb766fba19db46cc7f4ae8d8b22b6d8059bb884d8788d2'
ARCHIVE = Path('/var/tmp/ga-e0t1.20-helper-archive-20260928-r1')
JOB = 'ga-e0t1-20-helper-recover-r1'
STAT = dict(uid=1000, gid=1000, mode=0o100755, nlink=1, size=312,
            dev=2096, ino=8934271, mtime_ns=1790611811858457751,
            ctime_ns=1790611811858457751)
BWRAP = '/usr/bin/bwrap'
BWRAP_SHA = 'e318903862396f96de3df57264e0158682b952fd3fb53ac23d876413e7b30f71'


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def read(path):
    path = Path(path)
    require(path.resolve(strict=True) == path, 'path alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'file type or links')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read()
        require(s == os.fstat(fd) and path.lstat() == s, 'file changed while read')
        return raw
    finally:
        os.close(fd)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_sandbox_binary():
    path = Path(BWRAP)
    require(path.resolve(strict=True) == path, 'sandbox alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == s.st_gid == 0
                and stat.S_IMODE(s.st_mode) == 0o755 and s.st_nlink == 1
                and s.st_size < 1 << 20, 'sandbox binary authority')
        raw = os.read(fd, (1 << 20) + 1)
        keys = tuple(STAT)
        fp = lambda value: tuple(getattr(value, 'st_' + key) for key in keys)
        require(fp(s) == fp(os.fstat(fd)) == fp(path.lstat()) and len(raw) == s.st_size
                and digest(raw) == BWRAP_SHA, 'sandbox binary drift')
    finally:
        os.close(fd)


def attrs(path):
    s = Path(path).lstat()
    return {key: getattr(s, 'st_' + key) for key in STAT}


def verify_helper(path, *, archived=False):
    observed = attrs(path)
    expected = dict(STAT)
    if archived:
        expected.pop('ctime_ns')
        observed.pop('ctime_ns')
    require(observed == expected, 'helper filesystem identity drift')
    require(digest(read(path)) == HELPER_SHA, 'helper byte drift')


def load_package():
    raw = read(PACKAGE / 'assembly.json')
    require(digest(raw) == MANIFEST_SHA, 'assembly drift')
    pins = json.loads(raw)['files']
    for name, pin in pins.items():
        require(digest(read(PACKAGE / name)) == pin, 'package drift ' + name)
    def load(name):
        raw = read(PACKAGE / name)
        require(digest(raw) == pins[name], 'module drift')
        value = types.ModuleType(name)
        value.__file__ = str(PACKAGE / name)
        exec(compile(raw, value.__file__, 'exec', dont_inherit=True), value.__dict__)
        return value
    w = load('window-base-r11.py')
    w.HERE = PACKAGE
    return w, load


def read_only_argv(command, city):
    return [BWRAP, '--ro-bind', '/', '/', '--unshare-pid', '--new-session',
            '--die-with-parent', '--proc', '/proc', '--dev', '/dev',
            '--chdir', str(city), '--', *command]


def prove_read_only(paths):
    rows = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        f = line.split()
        require('\\' not in f[4], 'unexpected escaped mount')
        rows.append((f[4], f[5].split(',')))
    for path in map(str, paths):
        match = max(((p, flags) for p, flags in rows
                     if p == '/' or path == p or path.startswith(p + '/')),
                    key=lambda item: len(item[0]))
        require('ro' in match[1], 'writable inspection mount ' + path)
        require(not any('rw' in flags for p, flags in rows if p.startswith(path + '/')),
                'writable inspection descendant ' + path)


def inspect(before_archive):
    w, load = load_package()
    prove_read_only([w.WORK, w.ADMIN, w.CITY, '/home/loucmane/gascity/home/cache/repos'])
    c = load('contract.py')
    v = load('startup-validation.py')
    i = load('candidate-inspect.py')
    workspace = load('workspace-r7.py')
    image = v.workspace_image(w.WORK, i.file_bytes)
    expected = dict(image)
    if before_archive:
        verify_helper(w.WORK / REL)
        require(REL in expected, 'helper absent before recovery')
        expected.pop(REL)
    workspace.verify(w, expected, c.RUNTIME_IMAGE)
    b, o, owned = w.load_support()
    env = dict(o.ENV, GC_HOME='/home/loucmane/gascity/home', GC_CITY=str(w.CITY),
               GIT_OPTIONAL_LOCKS='0', BD_DISABLE_METRICS='1')
    for key in list(env):
        if key.startswith('BEADS_'):
            del env[key]
    def run(argv):
        result = subprocess.run(argv, cwd=w.CITY, env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=90, check=False)
        require(result.returncode == 0, 'inspection refused ' + repr(argv) + ' ' + result.stderr.decode())
        return result.stdout
    pair = {key: json.loads(run(w.GC + ['--rig', 'gascity', 'bd', 'show', bead, '--json']))[0]
            for key, bead in [('task', 'ga-e0t1.20'), ('parent', 'ga-e0t1')]}
    legacy = load('legacy-continuation-r4.py')
    load('recovered-claim-r7.py').verify(w, pair, legacy.normalized, legacy.compare_pair)
    require(json.loads(run(w.GC + ['session', 'list', '--json']))['sessions'] == [], 'open sessions')
    status = json.loads(run(w.GC + ['status', '--json']))
    require(status['suspended'] and all(r['suspended'] for r in status['rigs']), 'rig active')
    require(run(w.HARDENED + ['rev-parse', '--verify', 'HEAD^{commit}']).decode().strip() == w.BASE,
            'worker HEAD drift')
    if not before_archive:
        c.validate_rule_status(run(w.HARDENED + ['status', '--porcelain=v1', '--ignored',
                                                '--untracked-files=all', '-z']))
    require(image == v.workspace_image(w.WORK, i.file_bytes), 'inspection workspace mutation')
    return dict(ok=True, before_archive=before_archive, entries=len(image),
                original_entries=len(expected), zero_sessions=True, all_rigs_suspended=True,
                read_only_mounts=True, workspace_unchanged=True,
                pair_sha256=digest(json.dumps({k:legacy.normalized(v) for k,v in pair.items()},
                                              sort_keys=True, separators=(',', ':')).encode()))


def job_context(w):
    jobs = Path('/home/loucmane/.local/share/gas-city-staging/jobs')
    # Admission clears HALTED before launching this one exact reviewed job.
    # Requiring HALTED inside the job would make the supported route impossible.
    group = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-' + JOB + '.service\n'
    require(Path('/proc/self/cgroup').read_text() == group
            and re.fullmatch('[0-9a-f]{32}', os.environ.get('INVOCATION_ID', '')),
            'not the reviewed recovery job')
    require(not list((jobs / 'queue').iterdir())
            and (jobs / 'done' / (JOB + '.started.json')).is_file()
            and not (jobs / 'done' / (JOB + '.json')).exists(), 'recovery job state')
    require(not w.ROOT.exists(), 'window already entered')


def confined_host_observation(w, o, owned, prefix):
    original = o.command
    def guarded(argv, timeout=30):
        if argv and argv[0] == o.GC:
            shapes = {tuple(w.GC + ['status', '--json']): 'status',
                      tuple(w.GC + ['session', 'list', '--json']): 'sessions'}
            require(tuple(argv) in shapes, 'unexpected host diagnostic')
            return isolated(w, owned, prefix + '-' + shapes[tuple(argv)], argv,
                            min(timeout, 90)).encode()
        return original(argv, timeout=timeout)
    # All original actual-host PID, image, namespace, listener and service checks
    # remain in place. Only its two closed GC diagnostic calls are confined.
    o.command = guarded
    try:
        return w.host(o)
    finally:
        o.command = original


def host_state(w, load, prefix):
    job_context(w)
    b, o, owned = w.load_support()
    host = confined_host_observation(w, o, owned, prefix)
    for name in ('core', 'broker', 'signer'):
        require(host[name]['NRestarts'] == '0', 'service restarted')
    load('runtime-process-r7.py').verify_assets(load('worker-startup-r7.py').read_regular)
    pins = {str(p): digest(w.read(p)) for p in (w.CITY / 'city.toml', w.RECEIPT, Path(w.SUSPENSION))}
    require(pins[str(w.CITY / 'city.toml')] == w.CITY_SHA[0], 'city bytes drift')
    require(pins[str(w.RECEIPT)] == w.RECEIPT_SHA[0], 'receipt drift')
    suspension = json.loads(w.read(Path(w.SUSPENSION)))
    require(suspension['city']['suspended'] and all(v['suspended'] for v in suspension['rigs'].values()),
            'suspension drift')
    return dict(host=host, pins=pins)


def persist_phase(path, record):
    require(path.parent == ARCHIVE and re.fullmatch(r'[a-z-]+-phase\.json', path.name), 'phase evidence path')
    save(ARCHIVE, path.name, record)


def isolated(w, owned, name, command, timeout):
    evidence = ARCHIVE / (name + '-phase.json')
    require(not os.path.lexists(evidence), 'inspection already consumed')
    owned._write_phase_evidence = persist_phase
    env = dict(w.load_support()[1].ENV, GC_HOME='/home/loucmane/gascity/home',
               GC_CITY=str(w.CITY), GIT_OPTIONAL_LOCKS='0', BD_DISABLE_METRICS='1')
    for key in list(env):
        if key.startswith('BEADS_'):del env[key]
    result = owned._run_owned_phase(name=name, argv=read_only_argv(command, w.CITY),
        cwd=w.CITY, environment=env, timeout=timeout, evidence_path=evidence)
    cleanup = result['cleanup']
    require(cleanup['direct_child_reaped'] and cleanup['owned_process_group_gone']
            and not cleanup['failures'] and not cleanup['unexpected_survivors'], 'inspection containment')
    require(not result['timed_out'] and not result['primary_error'] and result['exit_code'] == 0,
            'read-only child refused ' + name)
    require(len(result['stdout'].encode()) <= 4*1024*1024
            and len(result['stderr'].encode()) <= 1024*1024, 'diagnostic output bound')
    return result['stdout']


def child(w, owned, mode):
    require(mode in ('inner-before', 'inner-after'), 'unknown inspection')
    command = ['/usr/bin/python3', '-I', '-S', '-B', str(w.LAUNCH), __file__, _SOURCE_SHA, mode]
    report = json.loads(isolated(w, owned, mode, command, 300))
    require(report['ok'] and report['read_only_mounts'] and report['original_entries'] == 8036,
            'child proof incomplete')
    return report


def save(root, name, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:os.fsync(parent)
    finally:os.close(parent)


def archive_exact(source, destination):
    verify_helper(source)
    require(not os.path.lexists(destination), 'archive destination occupied')
    for parent in (source.parent, destination.parent):
        require(parent.resolve(strict=True) == parent, 'parent alias')
        s = parent.lstat()
        require(stat.S_ISDIR(s.st_mode) and s.st_uid == 1000 and not s.st_mode & 0o022,
                'untrusted parent')
    sf = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    df = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        require(os.fstat(sf).st_dev == os.fstat(df).st_dev == STAT['dev'], 'archive filesystem')
        verify_helper(source)
        rename = ctypes.CDLL(None, use_errno=True).renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(sf, os.fsencode(source.name), df, os.fsencode(destination.name), 1) != 0:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))
        os.fsync(sf)
        os.fsync(df)
        require(not os.path.lexists(source), 'source still present')
        verify_helper(destination, archived=True)
    finally:
        os.close(sf)
        os.close(df)


def main():
    if sys.argv[1:] in (['inner-before'], ['inner-after']):
        print(json.dumps(inspect(sys.argv[1] == 'inner-before'), sort_keys=True))
        return
    require(sys.argv[1:] == ['apply'], 'exact action required')
    require(os.getuid() == os.geteuid() == 1000 and globals().get('_SOURCE_SHA'), 'bound user entry')
    require(digest(read(Path(__file__))) == _SOURCE_SHA, 'recovery source drift')
    verify_sandbox_binary()
    w, load = load_package()
    job_context(w)
    verify_helper(w.WORK / REL)
    require(not os.path.lexists(ARCHIVE), 'consumed archive root')
    ARCHIVE.mkdir(mode=0o700)
    save(ARCHIVE, 'intent.json', dict(source=str(w.WORK / REL), source_stat=STAT,
         source_sha256=HELPER_SHA, executor_sha256=_SOURCE_SHA,
         worker_launched=False, replay=False))
    owned = w.load_support()[2]
    moved = False
    try:
        before = host_state(w, load, 'before')
        save(ARCHIVE, 'host-before.json', before)
        first = child(w, owned, 'inner-before')
        require(before == host_state(w, load, 'pre-archive'), 'pre-archive host drift')
        save(ARCHIVE, 'rename-intent.json', dict(source_stat=attrs(w.WORK / REL), destination='gc-beads-bd.sh'))
        archive_exact(w.WORK / REL, ARCHIVE / 'gc-beads-bd.sh')
        moved = True
        second = child(w, owned, 'inner-after')
        require(first['pair_sha256'] == second['pair_sha256'], 'bead pair changed during archive')
        require(before == host_state(w, load, 'after'), 'post-archive host drift')
        save(ARCHIVE, 'result.json', dict(ok=True, source_absent=True, archived_stat=attrs(ARCHIVE / 'gc-beads-bd.sh'),
             helper_sha256=HELPER_SHA, original_workspace_restored=True, before=first, after=second,
             actual_host_verified=True, host_unchanged=True, worker_launched=False))
        print(json.dumps(dict(ok=True, archive=str(ARCHIVE), original_workspace_restored=True, worker_launched=False)))
    except BaseException as exc:
        save(ARCHIVE, 'failure.json', dict(error=str(exc), archive_call_completed=moved, retry=False,
             source_exists=os.path.lexists(w.WORK / REL), archive_exists=os.path.lexists(ARCHIVE / 'gc-beads-bd.sh')))
        raise


if __name__ == '__main__':
    main()
