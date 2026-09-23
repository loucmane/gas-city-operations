"""Gas City operator job runner (the operator's decision of 2026-09-23: automate the live pastes).

The operator starts it once, from a real WSL terminal, as a transient `systemd-run --user` service,
so it lives under the user manager in the supervisor mount namespace. It polls a staging queue and
runs one reviewed operator wrapper at a time, each as its own
`systemd-run --user --wait --collect -p UMask=0022` unit. It never runs anything else.

A queued job runs only when all of these hold. Every refusal is recorded, and nothing is retried.
- The job file is a small regular file owned by the operator, in strict JSON with exactly the known
  keys. Its job id has never been seen before.
- The commit is the ga-e0t1 worktree HEAD, the worktree is clean, and the commit carries a good
  signature from the operator's key.
- The wrapper is a tracked `designs/<package>/operator/<NAME>.sh` whose bytes match the pinned digest.
- Two distinct reviewer transcript copies are stored for that commit. Each names it as the candidate
  and passes it, and neither holds it.
- The PAUSE file is absent. While it exists, jobs wait in the queue.

The started record is created, and the queue file removed, before the wrapper launches. So a crash
can never replay a job.
"""
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time

CONFIG = {
    'stage': '/home/loucmane/.local/share/gas-city-staging/jobs',
    'worktree': '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap',
    'signer': '7720D1FE503A88EDECA61A6F0C7D823543E01875',
    'uid': 1000,
    'poll': 5,
}
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
WRAPPER = re.compile(re.escape(PREFIX) + r'[a-z0-9][a-z0-9-]{0,63}/operator/[A-Z0-9][A-Z0-9-]{0,63}\.sh')
JOB_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,47}')
HEX40 = re.compile(r'[0-9a-f]{40}')
HEX64 = re.compile(r'[0-9a-f]{64}')
KEYS = {'job_id', 'commit', 'wrapper', 'wrapper_sha256', 'reviews'}
JOB_LIMIT = 64 * 1024
TRANSCRIPT_LIMIT = 64 * 1024 * 1024
ENV = {
    'HOME': '/home/loucmane', 'USER': 'loucmane', 'LOGNAME': 'loucmane',
    'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'PATH': '/usr/local/bin:/usr/bin:/bin',
    'XDG_RUNTIME_DIR': '/run/user/1000', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus',
    'GIT_OPTIONAL_LOCKS': '0',
}


class Refuse(Exception):
    pass


def paths(cfg):
    stage = cfg['stage']
    return {name: os.path.join(stage, name) for name in ('queue', 'done', 'reviews', 'state')} | {
        'pause': os.path.join(stage, 'PAUSE')}


def git(cfg, *args):
    done = subprocess.run(['git', '-C', cfg['worktree'], '--no-optional-locks', *args], capture_output=True,
                          text=True, timeout=60, env=ENV, stdin=subprocess.DEVNULL)
    return done.returncode, done.stdout, done.stderr


def real_head(cfg):
    code, out, err = git(cfg, 'rev-parse', 'HEAD')
    if code:
        raise Refuse('cannot read worktree HEAD: ' + err.strip()[:200])
    return out.strip()


def real_clean(cfg):
    code, out, err = git(cfg, 'status', '--porcelain', '--untracked-files=all')
    if code:
        raise Refuse('cannot read worktree status: ' + err.strip()[:200])
    return out == ''


def real_signed(cfg, commit):
    code, _, err = git(cfg, 'verify-commit', '--raw', commit)
    if code:
        return False
    for line in err.splitlines():
        fields = line.split()
        if fields[:2] == ['[GNUPG:]', 'VALIDSIG'] and fields[-1] == cfg['signer']:
            return True
    return False


def real_tracked(cfg, commit, rel):
    code, out, _ = git(cfg, 'ls-tree', '--name-only', commit, '--', rel)
    return code == 0 and out.strip() == rel


REAL = {'head': real_head, 'clean': real_clean, 'signed': real_signed, 'tracked': real_tracked}


def sha(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def owned_regular(path, uid, limit, name):
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1 or info.st_size > limit:
        raise Refuse('%s is not a small regular file owned by the operator: %s' % (name, path))
    return info


def strict_json(raw):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise Refuse('duplicate key %r' % key)
            seen[key] = value
        return seen
    try:
        return json.loads(raw, object_pairs_hook=pairs)
    except ValueError as exc:
        raise Refuse('job is not valid JSON: %s' % exc)


def check_reviews(cfg, commit, reviews):
    if not isinstance(reviews, list) or len(reviews) != 2 or not all(isinstance(item, str) for item in reviews):
        raise Refuse('reviews must list exactly two transcript copies')
    base = os.path.join(paths(cfg)['reviews'], commit) + os.sep
    digests = set()
    for path in reviews:
        if os.path.realpath(path) != path or os.path.dirname(path) + os.sep != base:
            raise Refuse('review %s is not a direct file under %s' % (path, base))
        owned_regular(path, cfg['uid'], TRANSCRIPT_LIMIT, 'review')
        with open(path, 'rb') as handle:
            raw = handle.read()
        if b'candidate=' + commit.encode() not in raw:
            raise Refuse('review %s does not name the commit as its candidate' % path)
        if b'SOURCE_PASS ' + commit.encode() not in raw:
            raise Refuse('review %s does not pass the commit' % path)
        if b'HOLD ' + commit.encode() in raw:
            raise Refuse('review %s holds the commit' % path)
        digests.add(hashlib.sha256(raw).hexdigest())
    if len(digests) != 2:
        raise Refuse('the two reviews are the same transcript')


def admit(cfg, job_path, deps=REAL):
    """Return the validated job, or raise Refuse naming the first failed condition."""
    owned_regular(job_path, cfg['uid'], JOB_LIMIT, 'job file')
    with open(job_path, 'rb') as handle:
        job = strict_json(handle.read())
    if not isinstance(job, dict) or set(job) != KEYS:
        raise Refuse('job keys must be exactly %s' % sorted(KEYS))
    job_id, commit, wrapper, digest = job['job_id'], job['commit'], job['wrapper'], job['wrapper_sha256']
    if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
        raise Refuse('job_id must match %s' % JOB_ID.pattern)
    if os.path.basename(job_path) != job_id + '.json':
        raise Refuse('job file name must be <job_id>.json')
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise Refuse('commit must be a full lowercase commit')
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        raise Refuse('wrapper_sha256 must be a lowercase SHA-256')
    if not isinstance(wrapper, str) or not WRAPPER.fullmatch(wrapper) or '..' in wrapper.split('/'):
        raise Refuse('wrapper must be a designs/<package>/operator/<NAME>.sh path')
    if deps['head'](cfg) != commit:
        raise Refuse('commit is not the worktree HEAD')
    if not deps['clean'](cfg):
        raise Refuse('worktree is not clean')
    if not deps['signed'](cfg, commit):
        raise Refuse('commit lacks a good signature from %s' % cfg['signer'])
    if not deps['tracked'](cfg, commit, wrapper):
        raise Refuse('wrapper is not tracked at the commit')
    absolute = os.path.join(cfg['worktree'], wrapper)
    if os.path.realpath(absolute) != absolute:
        raise Refuse('wrapper path resolves elsewhere')
    owned_regular(absolute, cfg['uid'], 1024 * 1024, 'wrapper')
    if sha(absolute) != digest:
        raise Refuse('wrapper digest differs from the job')
    check_reviews(cfg, commit, job['reviews'])
    return job


def launch_argv(cfg, job):
    return ['systemd-run', '--user', '--wait', '--collect', '--quiet', '--unit=gc-job-' + job['job_id'],
            '-p', 'UMask=0022', '/bin/sh', os.path.join(cfg['worktree'], job['wrapper']), job['commit']]


def real_launch(argv):
    try:
        done = subprocess.run(argv, env=ENV, stdin=subprocess.DEVNULL, capture_output=True)
    except OSError as exc:
        return 'launch-error', '', str(exc)
    text = lambda raw: raw.decode(errors='replace')[-4000:]
    return done.returncode, text(done.stdout), text(done.stderr)


def remove(cfg, path, safe):
    """Take a queue entry out of the queue whatever it is, so nothing is ever processed twice."""
    if os.path.isdir(path) and not os.path.islink(path):
        os.rename(path, os.path.join(paths(cfg)['done'], '%s.rejected-%d' % (safe, time.time_ns())))
    else:
        os.unlink(path)


def write_new(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(json.dumps(value, indent=1, sort_keys=True) + '\n')


def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def log(cfg, text):
    # operator/JOBRUNNER.sh sends stdout and stderr to jobs/runner.log, tracebacks included.
    print('%s %s' % (stamp(), text), flush=True)


def process(cfg, job_path, deps=REAL, launch=real_launch):
    """Handle one queue file. Returns the record written to done/."""
    where = paths(cfg)
    name = os.path.basename(job_path)
    stem = name[:-5] if name.endswith('.json') else name
    safe = stem if JOB_ID.fullmatch(stem) else 'invalid-%d' % time.time_ns()
    seen = [entry for entry in os.listdir(where['done']) if entry.split('.')[0] == safe]
    record = {'job_file': name, 'received': stamp()}
    try:
        if seen:
            raise Refuse('job id already used: %s' % sorted(seen))
        job = admit(cfg, job_path, deps)
    except Exception as exc:  # noqa: BLE001 - every admission failure is a recorded refusal
        record.update(admitted=False, refusal='%s: %s' % (type(exc).__name__, exc))
        write_new(os.path.join(where['done'], '%s.refused-%d.json' % (safe, time.time_ns())), record)
        remove(cfg, job_path, safe)
        log(cfg, 'refused %s: %s' % (name, exc))
        return record
    argv = launch_argv(cfg, job)
    record.update(admitted=True, job=job, argv=argv, started=stamp())
    write_new(os.path.join(where['done'], job['job_id'] + '.started.json'), record)
    os.unlink(job_path)
    log(cfg, 'started %s: %s at %s' % (job['job_id'], job['wrapper'].rsplit('/', 3)[-3], job['commit'][:8]))
    code, out, err = launch(argv)
    record.update(ended=stamp(), exit=code, stdout=out, stderr=err)
    write_new(os.path.join(where['done'], job['job_id'] + '.json'), record)
    log(cfg, 'finished %s: exit %s' % (job['job_id'], code))
    return record


def heartbeat(cfg, started, current):
    path = os.path.join(paths(cfg)['state'], 'runner.json')
    temp = path + '.tmp'
    with open(temp, 'w') as handle:
        json.dump({'pid': os.getpid(), 'started': started, 'last_poll': stamp(), 'current': current,
                   'source_sha256': globals().get('_SOURCE_SHA'), 'mnt': os.readlink('/proc/self/ns/mnt')},
                  handle, sort_keys=True)
    os.replace(temp, path)


def main():
    cfg = CONFIG
    where = paths(cfg)
    for name in ('queue', 'done', 'reviews', 'state'):
        os.makedirs(where[name], mode=0o700, exist_ok=True)
    manager = os.environ.get('MANAGERPID') or str(os.getppid())
    try:
        with open('/proc/%s/comm' % manager) as handle:
            comm = handle.read().strip()
        same = os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/%s/ns/mnt' % manager)
    except OSError:
        comm, same = '', False
    if not manager.isdigit() or comm != 'systemd' or not same:
        print('job runner must run as a systemd --user service in the manager mount namespace', flush=True)
        return 2
    lock = open(os.path.join(where['state'], 'runner.lock'), 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('another job runner holds the lock', flush=True)
        return 2
    started = stamp()
    log(cfg, 'runner up pid %d source %s' % (os.getpid(), globals().get('_SOURCE_SHA')))
    broken = set()
    while True:
        heartbeat(cfg, started, None)
        if not os.path.lexists(where['pause']):
            # Names starting with a dot are in-flight submissions (written, then renamed into place).
            for name in sorted(os.listdir(where['queue'])):
                if name.startswith('.') or name in broken:
                    continue
                heartbeat(cfg, started, name)
                try:
                    process(cfg, os.path.join(where['queue'], name))
                except Exception as exc:  # noqa: BLE001 - never crash, never hot-loop on one file
                    broken.add(name)
                    log(cfg, 'ERROR handling %s, skipped until restart: %s: %s' % (name, type(exc).__name__, exc))
                heartbeat(cfg, started, None)
        time.sleep(cfg['poll'])


if __name__ == '__main__':
    sys.exit(main())
