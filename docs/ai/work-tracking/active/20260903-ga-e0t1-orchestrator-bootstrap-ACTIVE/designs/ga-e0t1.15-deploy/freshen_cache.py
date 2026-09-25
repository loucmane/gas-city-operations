"""Cache FRESHEN for ga-e0t1.15 S2 (broker sequence 14). Reads only; the only effect is relatime atime.

The sequence 13 deadlines window (deadlines.py build_window) requires every entry of the pack cache
/home/loucmane/gascity/home/cache/repos to have atime > max(mtime, ctime), and requires the oldest
atime plus 24 h to lie beyond the window's start plus 900 s plus the margin. The accepted predecessor
pins those exact atimes, so no refresh may happen between the accept phase and prepare. This job
therefore runs once, immediately before accept.

It is the method of the reviewed ga-4z38 freshen-r11.py, applied to the cache that freshen-r11
deliberately excluded:
- enumerate with O_NOATIME directory listings;
- lstat every entry before;
- touch each entry once: list a directory, read one byte of a regular file, readlink a symlink;
- lstat after, and require that nothing but atime changed.
Every entry must end with atime > max(mtime, ctime) and an age below YOUNG_HOURS. Under relatime a
read refreshes only atimes older than 24 h (or not newer than mtime/ctime). An entry aged between
YOUNG_HOURS and 24 h therefore cannot be refreshed; the job refuses and lists when each becomes
refreshable. The lstat forecast chooses a time when no entry is in that band.

YOUNG_HOURS 20 leaves 23.73 - 20 = 3.7 h from this job to prepare's window start. That time holds
accept, its review, the regeneration and its review.

One fresh root per run. The job refuses once the accept root or the sequence 14 phase outputs exist.
It never runs gc, never signs, and never touches anything outside the cache.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

CACHE = Path('/home/loucmane/gascity/home/cache/repos')
YOUNG_HOURS = 20
ACCEPT_ROOT = Path('/var/tmp/ga-e0t1.15-predecessor-20260925-r2')
SEQ14_ROOT = Path('/var/tmp/ga-e0t1.15-seq14-20260925')
MAX_ENTRIES = 100000


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def image(path):
    s = os.lstat(path)
    return dict(mode=s.st_mode, uid=s.st_uid, gid=s.st_gid, inode=s.st_ino, device=s.st_dev,
                nlink=s.st_nlink, size=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns,
                atime_ns=s.st_atime_ns)


def listdir_noatime(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOATIME | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        return sorted(os.listdir(fd))
    finally:
        os.close(fd)


def enumerate_cache():
    paths, pending = [str(CACHE)], [str(CACHE)]
    while pending:
        current = pending.pop()
        for name in listdir_noatime(current):
            path = os.path.join(current, name)
            paths.append(path)
            require(len(paths) <= MAX_ENTRIES, 'cache entry bound')
            if stat.S_ISDIR(os.lstat(path).st_mode):
                pending.append(path)
    return sorted(paths)


def touch(path):
    s = os.lstat(path)
    if stat.S_ISDIR(s.st_mode):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            os.listdir(fd)
        finally:
            os.close(fd)
        return 'listed'
    if stat.S_ISREG(s.st_mode):
        # O_NONBLOCK: an entry swapped for a FIFO after the lstat cannot hang the job (review should_fix).
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            require(stat.S_ISREG(os.fstat(fd).st_mode), 'cache entry changed type ' + path)
            os.read(fd, 1)
        finally:
            os.close(fd)
        return 'read'
    if stat.S_ISLNK(s.st_mode):
        os.readlink(path)
        return 'readlink'
    require(False, 'special cache entry ' + path)


def relatime():
    flags = os.statvfs(CACHE).f_flag
    return bool(flags & os.ST_RELATIME) and not flags & (os.ST_NOATIME | os.ST_RDONLY)


def save(root, name, value):
    data = json.dumps(value, indent=1, sort_keys=True).encode()
    fd = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            require(n > 0, 'short write')
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(data).hexdigest()


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'use python3 -I -B as uid 1000')
    require(not os.path.lexists(ACCEPT_ROOT), 'accept already ran; no FRESHEN may follow it')
    for name in ('preflight.json', 'prepare-start.json', 'terminal.json'):
        require(not os.path.lexists(SEQ14_ROOT / name), 'sequence 14 phases already started')
    require(relatime(), 'cache is not on a writable relatime mount')
    root = Path('/var/tmp/ga-e0t1.15-freshen-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir(mode=0o700)
    save(root, 'start.json', dict(executor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                  started=datetime.now(timezone.utc).isoformat()))
    paths = enumerate_cache()
    before = {p: image(p) for p in paths}
    save(root, 'before.json', before)
    actions = {p: touch(p) for p in paths}
    after = {p: image(p) for p in paths}
    require(enumerate_cache() == paths, 'cache entry set changed during freshen')
    save(root, 'after.json', dict(objects=after, actions=actions))
    changed = []
    for p in paths:
        a, z = dict(before[p]), dict(after[p])
        a.pop('atime_ns')
        z.pop('atime_ns')
        require(a == z, 'non-atime change during freshen: ' + p)
        if before[p]['atime_ns'] != after[p]['atime_ns']:
            changed.append(p)
    now = datetime.now(timezone.utc).timestamp() * 10**9
    old = []
    for p in paths:
        z = after[p]
        age = (now - z['atime_ns']) / 3.6e12
        if not z['atime_ns'] > max(z['mtime_ns'], z['ctime_ns']) or age >= YOUNG_HOURS:
            mark = datetime.fromtimestamp(z['atime_ns'] / 10**9 + 24 * 3600, timezone.utc).isoformat()
            old.append(dict(path=p, age_hours=round(age, 2), refreshable_after=mark))
    save(root, 'old.json', old)
    require(not old, '%d cache entries not young enough; see old.json' % len(old))
    oldest = min(z['atime_ns'] for z in after.values())
    result = dict(ok=True, root=str(root), entries=len(paths), atime_refreshed=len(changed),
                  young_hours=YOUNG_HOURS, oldest_atime_ns=oldest,
                  prepare_deadline_utc=datetime.fromtimestamp(oldest / 10**9 + 23.73 * 3600, timezone.utc).isoformat())
    save(root, 'result.json', result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
