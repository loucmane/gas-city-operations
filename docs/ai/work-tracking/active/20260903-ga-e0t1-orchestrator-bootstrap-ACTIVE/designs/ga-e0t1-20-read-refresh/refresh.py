"""Bounded ordinary reads before S2. Never writes a production timestamp.

This is not host or worker admission. The unchanged S2 stable_read_times and
full preflight still run afterward. Only four fixed objects may be read.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import types

ROOT = Path('/var/tmp/ga-e0t1.20-read-refresh-20260928-r1')
WINDOW = Path('/var/tmp/ga-e0t1.20-window-20260928-r2')
NOT_BEFORE_NS = 1790598360000000000  # 2026-09-28 14:26 CEST
HOUR = 3600 * 10**9
NOT_AFTER_NS = NOT_BEFORE_NS + 2 * HOUR
BOOT = '3f1f4534-ea17-4cb4-b2f2-a3f8bce1a8fa'
POLICY = Path(__file__).parent.parent / 'ga-e0t1-20-astra-window/cache-atime-policy-r1.py'
POLICY_SHA = '61c3e38e4475061c658a853036922742ab2ce69d44a4577e3f91490674047783'
PINS = {
    '/home/loucmane/gascity/city/.gc/runtime/suspension-state.json':
        dict(uid=1000, gid=1000, mode=33188, device=2096, inode=2914321,
             nlink=1, size=503, mtime_ns=1790495272296466592,
             ctime_ns=1790495272296466592, atime_ns=1790495272344466584,
             sha256='a3306567b3cf77e6371a870e6df239194574fab8f2dc3090ea55a5eeb14b4817'),
    '/home/loucmane/gascity/city':
        dict(uid=1000, gid=1000, mode=16877, device=2096, inode=4443121,
             nlink=24, size=4096, mtime_ns=1790508397325987451,
             ctime_ns=1790508397325987451, atime_ns=1790508410441985211),
    '/home/loucmane/gascity/city/.beads':
        dict(uid=1000, gid=1000, mode=16832, device=2096, inode=4453291,
             nlink=5, size=4096, mtime_ns=1790508403669986340,
             ctime_ns=1790508403669986340, atime_ns=1790511942017316467),
    '/home/loucmane/gascity/city/.gc/runtime/provisioning':
        dict(uid=1000, gid=1000, mode=16877, device=2096, inode=2193170,
             nlink=3, size=4096, mtime_ns=1790511053865486937,
             ctime_ns=1790511053865486937, atime_ns=1790511942021316465),
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def metadata(s):
    return dict(uid=s.st_uid, gid=s.st_gid, mode=s.st_mode, device=s.st_dev,
                inode=s.st_ino, nlink=s.st_nlink, size=s.st_size,
                mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, atime_ns=s.st_atime_ns)


def without_atime(value):
    return {key: item for key, item in value.items() if key != 'atime_ns'}


def young(value, now):
    return (value['atime_ns'] > max(value['mtime_ns'], value['ctime_ns'])
            and 0 <= now - value['atime_ns'] < 19 * HOUR)


def eligible(value, now):
    return (young(value, now) or value['atime_ns'] <= max(value['mtime_ns'], value['ctime_ns'])
            or now - value['atime_ns'] >= 24 * HOUR + 2 * 10**9)


def nofollow_open(path, flags):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'absolute fixed path required')
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for name in path.parts[1:-1]:
            newer = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=fd)
            os.close(fd)
            fd = newer
        return os.open(path.name, flags | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                       dir_fd=fd)
    finally:
        os.close(fd)


def capture(path, *, ordinary=False):
    fd = nofollow_open(path, os.O_RDONLY | (0 if ordinary else os.O_NOATIME))
    try:
        before = metadata(os.fstat(fd))
        mount = os.fstatvfs(fd).f_flag
        require(mount & os.ST_RELATIME and not mount & (os.ST_NOATIME | os.ST_RDONLY),
                'not a writable relatime mount')
        if stat.S_ISREG(before['mode']):
            require(before['nlink'] == 1 and before['size'] <= 4096, 'regular-file bounds')
            raw = os.read(fd, 4097)
            require(len(raw) == before['size'] and not os.read(fd, 1), 'file changed or oversized')
            contents = dict(sha256=hashlib.sha256(raw).hexdigest())
        else:
            require(stat.S_ISDIR(before['mode']), 'special file refused')
            names = sorted(os.listdir(fd))
            require(len(names) <= 256 and all(len(os.fsencode(n)) <= 255 for n in names),
                    'directory bounds')
            contents = dict(names=names)
        after = metadata(os.fstat(fd))
        require(without_atime(before) == without_atime(after), 'object changed while reading')
        if not ordinary:
            require(before == after, 'no-atime observation changed')
        require(metadata(os.lstat(path)) == after, 'path replaced while reading')
        return dict(before=before, after=after, **contents)
    finally:
        os.close(fd)


def load_policy():
    fd = nofollow_open(POLICY, os.O_RDONLY | os.O_NOATIME)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 1000
                and before.st_nlink == 1 and before.st_size <= 16384, 'policy authority')
        raw = os.read(fd, 16385)
        require(before == os.fstat(fd) and len(raw) == before.st_size
                and hashlib.sha256(raw).hexdigest() == POLICY_SHA, 'policy bytes drift')
    finally:
        os.close(fd)
    policy = types.ModuleType('reviewed_read_time_policy')
    exec(compile(raw, str(POLICY), 'exec', dont_inherit=True), policy.__dict__)
    return policy


def clock_sample():
    # This root-owned procfs observation is not a protected timestamp object.
    # O_NOATIME would require privilege that the operator process does not have.
    fd = nofollow_open('/proc/sys/kernel/random/boot_id', os.O_RDONLY)
    try:
        boot = os.read(fd, 128).decode('ascii').strip()
    finally:
        os.close(fd)
    require(boot == BOOT, 'boot drift')
    a = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    real = time.time_ns()
    z = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    return dict(boot=boot, real_ns=real, boot_before_ns=a, boot_after_ns=z)


def clock_envelope():
    return dict(start=clock_sample(), end=clock_sample())


def validate_pin(observed, pin, now):
    actual = observed['after']
    expected = {k: v for k, v in pin.items() if k != 'sha256'}
    require(without_atime(actual) == without_atime(expected), 'non-access metadata drift')
    if 'sha256' in pin:
        require(observed.get('sha256') == pin['sha256'], 'suspension content drift')
    old, new = expected['atime_ns'], actual['atime_ns']
    require(old <= new <= now, 'access time backward or future')
    if old != new:
        # Same natural-read shape already used by S2 account_read_times.
        # Both actual observations are retained; no field is rewritten.
        require(old <= max(expected['mtime_ns'], expected['ctime_ns'])
                or new // 10**9 - old // 10**9 >= 24 * 3600,
                'access time advance is not relatime-compatible')
    require(eligible(actual, now), 'read-time eligibility not reached')


def save(root, name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def run(pins, root, *, now=time.time_ns,
        raw_clock=lambda: time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)):
    started, raw_started = now(), raw_clock()
    require(NOT_BEFORE_NS <= started < NOT_AFTER_NS, 'outside reviewed refresh time window')
    require(not os.path.lexists(root), 'refresh root already consumed')
    policy = load_policy()
    before_clock = clock_envelope()
    before = {path: capture(path) for path in pins}
    # Check ALL objects before any ordinary read or evidence mutation.
    for path, pin in pins.items():
        validate_pin(before[path], pin, started)
    root.mkdir(mode=0o700)
    save(root, 'intent.json', dict(started_ns=started, executor_sha256=globals().get('_SOURCE_SHA'),
                                  paths=list(pins), worker_release=False))
    save(root, 'before.json', before)
    actions = {}
    for index, path in enumerate(pins):
        immediate = capture(path)
        require(immediate == before[path], 'object drift before ordinary read')
        if young(immediate['after'], now()):
            actions[path] = 'already-young-no-refresh'
        else:
            read_clock = clock_envelope()
            policy.bounds(before_clock, read_clock)
            save(root, 'read-%d-intent.json' % index, dict(path=path, clock=read_clock))
            result = capture(path, ordinary=True)
            after_read_clock = clock_envelope()
            bound = policy.bounds(read_clock, after_read_clock)
            save(root, 'read-%d.json' % index,
                 dict(observation=result, clock_before=read_clock, clock_after=after_read_clock, bounds=bound))
            require(result['before'] == immediate['after'], 'read preimage drift')
            require(without_atime(result['before']) == without_atime(result['after']),
                    'non-access metadata changed during refresh')
            require(bound['earliest_ns'] <= result['after']['atime_ns'] <= bound['latest_ns']
                    and result['after']['atime_ns'] > result['before']['atime_ns'],
                    'ordinary read did not yield bounded access-time advance')
            actions[path] = 'ordinary-read'
    after = {path: capture(path) for path in pins}
    ended, raw_elapsed = now(), raw_clock() - raw_started
    after_clock = clock_envelope()
    bound = policy.bounds(before_clock, after_clock)
    save(root, 'after.json', dict(ended_ns=ended, objects=after, actions=actions,
                                 clock_before=before_clock, clock_after=after_clock, bounds=bound))
    require(0 <= ended - started <= 60 * 10**9 and 0 <= raw_elapsed <= 60 * 10**9,
            'refresh exceeded bounded clock window')
    for path in pins:
        a, z = before[path], after[path]
        require(without_atime(a['after']) == without_atime(z['after']), 'final metadata drift')
        require({k: v for k, v in a.items() if k not in ('before', 'after')}
                == {k: v for k, v in z.items() if k not in ('before', 'after')},
                'content or directory listing drift')
        require(young(z['after'], ended), 'unchanged nineteen-hour predicate does not pass')
    result = dict(ok=True, objects=len(pins), actions=actions, timestamp_writes=False,
                  unchanged_age_gate_passed=True, full_host_admission=False, worker_release=False)
    save(root, 'result.json', result)
    return result


def main():
    require(globals().get('_SOURCE_SHA') and len(sys.argv) == 1, 'fixed source-bound invocation required')
    require(os.getuid() == os.geteuid() == 1000, 'operator UID required')
    require(not os.path.lexists(WINDOW), 'window already created')
    print(json.dumps(run(PINS, ROOT), sort_keys=True))


if __name__ == '__main__':
    main()
