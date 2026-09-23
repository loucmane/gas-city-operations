"""Gas City operator job runner (the operator's decision of 2026-09-23: automate the live pastes).

The operator starts it once, from a real WSL terminal, as the transient user service
`gas-city-jobrunner`. That puts it under the user manager in the supervisor mount namespace. It polls
a staging queue and runs at most one reviewed operator wrapper at a time, each as its own
`systemd-run --user --wait --collect -p UMask=0022` unit. It never runs anything else.

A queued job runs only when all of these hold. Every refusal is recorded, and nothing is retried.

Before any job, re-checked every time:
- The operator's PAUSE file is absent. The coordinator never touches it.
- The runner's HALTED latch is absent.
- No earlier job has a started record without a final or resolved record.
- The job is the only file in the queue.

The job file:
- a small regular file owned by the operator;
- strict JSON with exactly the known keys;
- its job id has never been seen before.

The commit:
- it is the ga-e0t1 worktree HEAD;
- the worktree is clean;
- it carries a good signature from the operator's key.

The wrapper:
- a tracked `designs/<package>/operator/<NAME>.sh`, outside this package;
- its committed blob, its working file and the job's digest all agree;
- it has never run at that commit.

The reviews:
- Two reviewer subagent transcripts are filed for the commit.
- The first prompt line of each is `candidate=<commit>`, and each names the wrapper.
- Each has exactly one SubagentHandback report, and that report's first line is
  `SOURCE_PASS <commit>`.
- The two come from different reviewers.
- Every transcript filed for the commit passes it.

Before launching, the runner writes and fsyncs the started record and removes the queue file, so a crash
can never replay a job. Jobs run as oneshot units: a job stopped with SIGTERM fails rather than reading
as a clean exit.

HALTED is set after EVERY job, whatever its exit code, and on any runner error. A wrapper's exit code is
not its verdict; the outcome lives in the wrapper's own log. So nothing further runs until the
coordinator has read that log, recorded the outcome on the Bead, and cleared HALTED.
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
    'bus': '/run/user/1000/bus',
    'cgroup': '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gas-city-jobrunner.service',
}
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
WRAPPER = re.compile(re.escape(PREFIX) + r'(?!gct-jobrunner/)[a-z0-9][a-z0-9-]{0,63}/operator/[A-Z0-9][A-Z0-9-]{0,63}\.sh')
JOB_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,47}')
AGENT_ID = re.compile(r'[a-z0-9]{8,64}')
HEX40 = re.compile(r'[0-9a-f]{40}')
HEX64 = re.compile(r'[0-9a-f]{64}')
KEYS = {'job_id', 'commit', 'wrapper', 'wrapper_sha256', 'reviews'}
JOB_LIMIT = 64 * 1024
TRANSCRIPT_LIMIT = 64 * 1024 * 1024
# Environment of the runner's own git and systemd-run client calls. A launched job unit inherits the
# user manager's environment, exactly as the operator's hand-pasted systemd-run did.
ENV = {
    'HOME': '/home/loucmane', 'USER': 'loucmane', 'LOGNAME': 'loucmane',
    'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'PATH': '/usr/local/bin:/usr/bin:/bin',
    'XDG_RUNTIME_DIR': '/run/user/1000', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus',
    'GIT_OPTIONAL_LOCKS': '0',
}
# Repository config cannot choose the fsmonitor, hooks or signature-verification programs of the runner's
# git calls. Clean and smudge filter drivers from repository config are not neutralized; the worktree is
# coordinator-controlled, and that is within the stated trust model.
GIT_SAFE = ['-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-c', 'gpg.program=/usr/bin/gpg',
            '-c', 'gpg.ssh.program=/usr/bin/ssh-keygen', '-c', 'gpg.x509.program=/usr/bin/gpgsm']
RECORD_LIMIT = 1024 * 1024


class Refuse(Exception):
    pass


def paths(cfg):
    stage = cfg['stage']
    found = {name: os.path.join(stage, name) for name in ('queue', 'done', 'reviews', 'state')}
    found['pause'] = os.path.join(stage, 'PAUSE')
    found['halted'] = os.path.join(stage, 'state', 'HALTED')
    return found


def git(cfg, *args, binary=False):
    done = subprocess.run(['git', *GIT_SAFE, '-C', cfg['worktree'], '--no-optional-locks', *args],
                          capture_output=True, timeout=60, env=ENV, stdin=subprocess.DEVNULL)
    out = done.stdout if binary else done.stdout.decode(errors='replace')
    return done.returncode, out, done.stderr.decode(errors='replace')


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


def real_blob_sha(cfg, commit, rel):
    """SHA-256 of the committed regular-file blob at rel, or None."""
    code, out, _ = git(cfg, 'ls-tree', commit, '--', rel)
    meta, _, name = out.rstrip('\n').partition('\t')
    fields = meta.split()
    if code or name != rel or len(fields) != 3 or fields[0] not in ('100644', '100755') or fields[1] != 'blob':
        return None
    code, raw, _ = git(cfg, 'cat-file', 'blob', fields[2], binary=True)
    return None if code else hashlib.sha256(raw).hexdigest()


REAL = {'head': real_head, 'clean': real_clean, 'signed': real_signed, 'blob_sha': real_blob_sha}


def sha(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def read_owned(path, uid, limit, name):
    """Open without following links or blocking on a FIFO, then check the opened file itself."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        raise Refuse('%s cannot be opened safely: %s: %s' % (name, path, exc))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1 or info.st_size > limit:
            raise Refuse('%s is not a small regular file owned by the operator: %s' % (name, path))
        chunks = []
        while chunk := os.read(fd, 1 << 20):
            chunks.append(chunk)
        return b''.join(chunks)
    finally:
        os.close(fd)


def unit_state(unit):
    """ActiveState of a user unit. A collected or unknown unit reads as inactive."""
    done = subprocess.run(['systemctl', '--user', 'show', '-p', 'ActiveState', '--value', unit], capture_output=True,
                          timeout=30, env=ENV, stdin=subprocess.DEVNULL)
    return done.stdout.decode(errors='replace').strip() if done.returncode == 0 else 'unknown'


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


def read_review(path, commit, uid):
    """Parse one reviewer transcript. Returns (agent id, first prompt, first report line) or refuses."""
    raw = read_owned(path, uid, TRANSCRIPT_LIMIT, 'review')
    try:
        records = [strict_json(line) for line in raw.splitlines() if line.strip()]
    except Refuse as exc:
        raise Refuse('review %s is not a strict JSONL transcript: %s' % (path, exc))
    if not records or not all(isinstance(record, dict) for record in records):
        raise Refuse('review %s has no transcript records' % path)
    first = records[0]
    agent = first.get('agentId')
    if first.get('type') != 'user' or first.get('isSidechain') is not True or not isinstance(agent, str) \
            or not AGENT_ID.fullmatch(agent):
        raise Refuse('review %s does not start as a reviewer subagent transcript' % path)
    if any(record.get('agentId') != agent or record.get('isSidechain') is not True for record in records):
        raise Refuse('review %s mixes transcripts' % path)
    if os.path.basename(path) != 'agent-%s.jsonl' % agent:
        raise Refuse('review %s is not named after its agent id' % path)
    prompt = (first.get('message') or {}).get('content')
    if not isinstance(prompt, str) or prompt.splitlines()[:1] != ['candidate=' + commit] or prompt.count('candidate=') != 1:
        raise Refuse('review %s was not bound to the commit as its only candidate' % path)
    reports = []
    for record in records:
        if record.get('type') != 'assistant':
            continue
        for item in (record.get('message') or {}).get('content') or []:
            if isinstance(item, dict) and item.get('type') == 'tool_use' and item.get('name') == 'SubagentHandback':
                reports.append((item.get('input') or {}).get('message'))
    if len(reports) != 1 or not isinstance(reports[0], str) or not reports[0].strip():
        raise Refuse('review %s has %d handback reports, want exactly one' % (path, len(reports)))
    return agent, prompt, reports[0].splitlines()[0].strip()


def check_reviews(cfg, commit, wrapper, reviews):
    if not isinstance(reviews, list) or len(reviews) != 2 or not all(isinstance(item, str) for item in reviews):
        raise Refuse('reviews must list exactly two transcript copies')
    directory = os.path.join(paths(cfg)['reviews'], commit)
    filed = {os.path.join(directory, name): read_review(os.path.join(directory, name), commit, cfg['uid'])
             for name in sorted(os.listdir(directory))}
    failing = [path for path, (_, _, verdict) in filed.items() if verdict != 'SOURCE_PASS ' + commit]
    if failing:
        raise Refuse('a filed review does not pass the commit: %s' % failing)
    agents = set()
    for path in reviews:
        if os.path.realpath(path) != path or path not in filed:
            raise Refuse('review %s is not a file filed directly under %s' % (path, directory))
        agent, prompt, _ = filed[path]
        if 'Wrapper: ' + wrapper not in [line.strip() for line in prompt.splitlines()]:
            raise Refuse('review %s has no exact "Wrapper: %s" line' % (path, wrapper))
        agents.add(agent)
    if len(agents) != 2:
        raise Refuse('the two reviews come from the same reviewer')


def done_records(cfg):
    done = paths(cfg)['done']
    records = {}
    for entry in os.listdir(done):
        if entry.endswith('.started.json'):
            raw = read_owned(os.path.join(done, entry), cfg['uid'], RECORD_LIMIT, 'started record')
            records[entry[:-len('.started.json')]] = strict_json(raw)
    return records


def already_ran(cfg, commit, wrapper):
    for job_id, record in done_records(cfg).items():
        job = record.get('job') or {}
        if job.get('commit') == commit and job.get('wrapper') == wrapper:
            return job_id
    return None


def resolved(cfg, job_id, state=unit_state):
    """A coordinator resolution counts only when its unit is gone and the record states the outcome."""
    path = os.path.join(paths(cfg)['done'], job_id + '.resolved.json')
    if not os.path.lexists(path):
        return False
    record = strict_json(read_owned(path, cfg['uid'], RECORD_LIMIT, 'resolution record'))
    if not isinstance(record, dict) or record.get('job_id') != job_id or not record.get('outcome') \
            or not record.get('evidence'):
        raise Refuse('resolution record for %s must state job_id, outcome and evidence' % job_id)
    return state('gc-job-%s.service' % job_id) in ('inactive', 'failed')


def unfinished(cfg, state=unit_state):
    """Started jobs with neither a final record nor a valid coordinator resolution."""
    done = paths(cfg)['done']
    return sorted(job_id for job_id in done_records(cfg)
                  if not os.path.lexists(os.path.join(done, job_id + '.json')) and not resolved(cfg, job_id, state))


def admit(cfg, job_path, deps=REAL):
    """Return the validated job, or raise Refuse naming the first failed condition."""
    job = strict_json(read_owned(job_path, cfg['uid'], JOB_LIMIT, 'job file'))
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
    if not isinstance(wrapper, str) or not WRAPPER.fullmatch(wrapper):
        raise Refuse('wrapper must be a designs/<package>/operator/<NAME>.sh path outside gct-jobrunner')
    if deps['head'](cfg) != commit:
        raise Refuse('commit is not the worktree HEAD')
    if not deps['clean'](cfg):
        raise Refuse('worktree is not clean')
    if not deps['signed'](cfg, commit):
        raise Refuse('commit lacks a good signature from %s' % cfg['signer'])
    if deps['blob_sha'](cfg, commit, wrapper) != digest:
        raise Refuse('the committed wrapper blob does not match the job digest')
    absolute = os.path.join(cfg['worktree'], wrapper)
    if os.path.realpath(absolute) != absolute:
        raise Refuse('wrapper path resolves elsewhere')
    if hashlib.sha256(read_owned(absolute, cfg['uid'], 1024 * 1024, 'wrapper')).hexdigest() != digest:
        raise Refuse('the working wrapper differs from the job digest')
    previous = already_ran(cfg, commit, wrapper)
    if previous:
        raise Refuse('this wrapper already ran at this commit as job %s' % previous)
    check_reviews(cfg, commit, wrapper, job['reviews'])
    return job


def launch_argv(cfg, job):
    # oneshot: SIGTERM from `systemctl --user stop` is a failure, not the clean exit it is for a simple
    # service, and oneshot units have no start timeout.
    return ['systemd-run', '--user', '--wait', '--collect', '--quiet', '--service-type=oneshot',
            '--unit=gc-job-' + job['job_id'], '-p', 'UMask=0022', '-p', 'TimeoutStartSec=infinity',
            '/bin/sh', os.path.join(cfg['worktree'], job['wrapper']), job['commit']]


def real_launch(argv):
    try:
        done = subprocess.run(argv, env=ENV, stdin=subprocess.DEVNULL, capture_output=True)
    except OSError as exc:
        return 'launch-error', '', str(exc)
    return done.returncode, done.stdout.decode(errors='replace')[-4000:], done.stderr.decode(errors='replace')[-4000:]


def remove(cfg, path, safe):
    """Take a queue entry out of the queue whatever it is, so nothing is ever processed twice."""
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            os.rename(path, os.path.join(paths(cfg)['done'], '%s.rejected-%d' % (safe, time.time_ns())))
        else:
            os.unlink(path)
    except FileNotFoundError:
        pass


def write_new(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(json.dumps(value, indent=1, sort_keys=True) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    sync_dir(os.path.dirname(path))


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def log(cfg, text):
    # operator/JOBRUNNER.sh sends stdout and stderr to jobs/runner.log, tracebacks included.
    print('%s %s' % (stamp(), text), flush=True)


def halt(cfg, reason):
    path = paths(cfg)['halted']
    if not os.path.lexists(path):
        write_new(path, {'at': stamp(), 'reason': reason})


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
        log(cfg, 'refused %s: %s' % (name, exc))
        write_new(os.path.join(where['done'], '%s.refused-%d.json' % (safe, time.time_ns())), record)
        remove(cfg, job_path, safe)
        return record
    if os.path.lexists(where['pause']):
        # Admission can take a while; the operator may have paused meanwhile. The job stays queued.
        return 'paused'
    if not stat.S_ISSOCK(os.stat(cfg['bus']).st_mode if os.path.exists(cfg['bus']) else 0):
        # systemd-run --wait talks to the manager over the user bus. Without it the launch would fail
        # after the started record and burn the reviewed (commit, wrapper) pair, so wait instead.
        return 'no user bus'
    argv = launch_argv(cfg, job)
    record.update(admitted=True, job=job, argv=argv, started=stamp())
    write_new(os.path.join(where['done'], job['job_id'] + '.started.json'), record)
    remove(cfg, job_path, safe)
    sync_dir(where['queue'])
    log(cfg, 'started %s: %s at %s' % (job['job_id'], job['wrapper'].rsplit('/', 3)[-3], job['commit'][:8]))
    code, out, err = launch(argv)
    # Log the exit before anything that could fail, so it can never be lost. Every job halts the runner:
    # the exit code is not the verdict, and the coordinator reads the wrapper's log before clearing.
    log(cfg, 'finished %s: exit %s; HALTED until the coordinator records the outcome' % (job['job_id'], code))
    halt(cfg, 'job %s finished with exit %s; read its log, record the outcome, then clear' % (job['job_id'], code))
    record.update(ended=stamp(), exit=code, stdout=out, stderr=err)
    write_new(os.path.join(where['done'], job['job_id'] + '.json'), record)
    return record


def cycle(cfg, deps=REAL, launch=real_launch, state=unit_state):
    """One poll. Every precondition that could hold a job back is checked here, right before it runs."""
    where = paths(cfg)
    if os.path.lexists(where['pause']):
        return 'paused'
    if os.path.lexists(where['halted']):
        return 'halted'
    open_jobs = unfinished(cfg, state)
    if open_jobs:
        return 'unfinished ' + ','.join(open_jobs)
    names = sorted(os.listdir(where['queue']))
    if not names:
        return 'idle'
    if len(names) > 1:
        return 'multiple'
    return process(cfg, os.path.join(where['queue'], names[0]), deps, launch)


def heartbeat(cfg, started, state):
    # last_poll is not refreshed while a job runs, because the runner is inside `systemd-run --wait`.
    path = os.path.join(paths(cfg)['state'], 'runner.json')
    temp = path + '.tmp'
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump({'pid': os.getpid(), 'started': started, 'last_poll': stamp(), 'state': state,
                   'source_sha256': globals().get('_SOURCE_SHA')}, handle, sort_keys=True)
    os.replace(temp, path)


def own_unit(cfg, cgroup_text, environ):
    """Mistake guard, not a proof of identity: this process sits in the gas-city-jobrunner unit.

    A transient unit without sandboxing runs in the manager's mount namespace. The manager's own
    /proc/<pid>/ns link is deliberately not read: systemd 255 keeps capabilities in the manager, so a
    ptrace-mode read from an unprivileged child can fail. A deliberate uid-1000 process could move itself
    into this cgroup; the trust model does not defend against that.
    """
    if cgroup_text.strip() != cfg['cgroup']:
        return 'cgroup is %r, want exactly %s' % (cgroup_text.strip()[:200], cfg['cgroup'])
    if not environ.get('INVOCATION_ID'):
        return 'INVOCATION_ID is unset, so this is not a systemd unit'
    return None


def main():
    cfg = CONFIG
    where = paths(cfg)
    for name in ('queue', 'done', 'reviews', 'state'):
        os.makedirs(where[name], mode=0o700, exist_ok=True)
    with open('/proc/self/cgroup') as handle:
        problem = own_unit(cfg, handle.read(), os.environ)
    if problem:
        print('job runner refused to start: %s' % problem, flush=True)
        return 2
    lock = os.open(os.path.join(where['state'], 'runner.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('job runner refused to start: another runner holds the lock', flush=True)
        return 2
    started = stamp()
    log(cfg, 'runner up pid %d source %s' % (os.getpid(), globals().get('_SOURCE_SHA')))
    last = 'starting'
    while True:
        heartbeat(cfg, started, last if isinstance(last, str) else 'ran')
        try:
            state = cycle(cfg)
        except Exception as exc:  # noqa: BLE001 - never crash, never loop on a broken job
            state = 'error'
            try:
                halt(cfg, '%s: %s' % (type(exc).__name__, exc))
                log(cfg, 'ERROR, HALTED: %s: %s' % (type(exc).__name__, exc))
            except OSError:
                return 3
        if isinstance(state, str) and state != last and state != 'idle':
            log(cfg, 'state %s' % state)
        last = state
        time.sleep(cfg['poll'])


if __name__ == '__main__':
    sys.exit(main())
