"""Refresh relatime access times before the window, so no read during it can change them. Reads only.

The city and home filesystems are mounted relatime: a read updates an object's atime only when that
atime is not newer than its mtime or ctime, or is older than 24 hours. The window compares exact atime
on the P6 pinned files, the protected platform trees, the provider files, the city root and its direct
children, and the provisioning tree. On 2026-09-23 about 70 of those carried access times about 22
hours old, so the first runtime read after their 24-hour mark would change them mid-window and the
exact comparisons before restore would refuse. The R9 restore needed a reviewed accounting of exactly
such reads (restore-r9-routes-r3.py account_recorded_reads).

A read cannot refresh an atime that is still younger than 24 hours, so reading alone is not enough:
this job requires every object to END young, not only fresh. It runs before OBSERVE and before any
window root exists, and is repeatable (one fresh timestamped root per run). For each object it reads one
byte of a regular file, lists a directory, or reads a symlink. It records lstat before and
after, requires that nothing but atime changed, and requires every object to end with an atime newer than
its mtime and ctime and younger than YOUNG_HOURS, which leaves the four-hour window a margin before the
24-hour mark. If any object is still too old, it refuses and lists each one with the UTC time at which
its 24-hour mark passes; after that time a rerun refreshes it. The pack cache is excluded: the reviewed
cache-atime policy accounts for its access times, and no P6 pin may lie under it. Symlinks (the API
link) are refreshed with readlink, which updates a symlink's atime under the same rule. Every object
must sit on a relatime mount that is neither noatime nor read-only (as the base requires of the city);
anything else refuses, because this strategy is only valid under relatime.

Objects this job cannot hold, all checked by the read-only ADMIT job before RESTORE is consumed:
- the city root and provisioning directory, whose mtimes the window's atomic renames change;
- the five generated route files and their store directories, which the STAGE reload regenerates (the
  route-chain event model binds them from then on). Two of those stores are the protected blog and
  hpfetcher checkouts, which this job never reads.

Pass order: PREFLIGHT.sh requires a FRESHEN pass (result.json with ok) from the last 45 minutes,
because an object that was already fresh (not refreshable) may be up to YOUNG_HOURS old and must stay
under 24 hours until the window's T0 plus four hours: 19 h + 45 min + 4 h < 24 h.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-f37t-window/window-base-r11.py')
BASE_SHA = 'ea03593f4e764a6e4667b80d62a65f4af73b8dca82f4c9f411c705cb3d58430e'
YOUNG_HOURS = 19
WINDOW = Path('/var/tmp/ga-f37t-window-20260925-r2')
INTEGRITY = Path('/var/tmp/ga-f37t-integrity-20260925-r5')


def load():
    fd = os.open(BASE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1
        raw = b''
        while chunk := os.read(fd, 65536):
            raw += chunk
        assert os.fstat(fd) == s and hashlib.sha256(raw).hexdigest() == BASE_SHA, 'base source drift'
    finally:
        os.close(fd)
    w = types.ModuleType('freshen_base')
    w.__file__ = str(BASE)
    exec(compile(raw, str(BASE), 'exec', dont_inherit=True), w.__dict__)
    return w


def image(path):
    s = os.lstat(path)
    return dict(mode=s.st_mode, uid=s.st_uid, gid=s.st_gid, inode=s.st_ino, device=s.st_dev, nlink=s.st_nlink,
                size=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, atime_ns=s.st_atime_ns)


def objects(w, b):
    """Every exact-atime object of the window snapshots. Reads with O_NOATIME only; changes nothing."""
    accepted = json.loads(w.read(w.ACCEPTED, w.ACCEPTED_SHA))
    providers = json.loads(w.read(Path(str(w.ACCEPTED) + '.provider-pins'), w.PROVIDER_SHA))
    r = w.module(w.SUPPORT/'p6-readiness.py', '7b28b3e551e86818a2cdda3e53ed90c7072781e0a9354bd1ebf5d9425d579133')
    paths = list(accepted['pins'])
    for root, tree in accepted['protected'].items():
        paths += [root if rel == '.' else root + '/' + rel for rel in tree['inventory']]
    paths += [str(r.WORKER_NATIVE), str(r.SUBSCRIPTION), str(r.PROVISIONER), str(r.RUNNER), str(r.NATIVE_LINK)]
    w.require(isinstance(providers['api_package'], dict) and len(providers['api_package']) == 2, 'api package shape')
    paths += sorted(providers['api_package'])
    fd = os.open(w.CITY, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        children = sorted(os.listdir(fd))
    finally:
        os.close(fd)
    paths += [str(w.CITY)] + [str(w.CITY/name) for name in children]
    provisioning = w.RECEIPT.parent
    paths += [str(provisioning), str(w.RECEIPT), str(provisioning/'bin'), str(provisioning/'bin/gct-managed-worker-canary')]
    cache = str(b.CACHE)
    w.require(not [p for p in accepted['pins'] if p == cache or p.startswith(cache + '/')], 'P6 pin under the cache')
    unique = []
    for path in paths:
        if path not in unique and not (path == cache or path.startswith(cache + '/')):
            unique.append(path)
    return unique


def touch(path):
    s = os.lstat(path)
    if stat.S_ISDIR(s.st_mode):
        os.listdir(path)
        return 'listed'
    if stat.S_ISREG(s.st_mode):
        with open(path, 'rb') as handle:
            handle.read(1)
        return 'read'
    if stat.S_ISLNK(s.st_mode):
        os.readlink(path)
        return 'readlink'
    return 'recorded'


def relatime(path):
    """True when the object's mount is relatime and neither noatime nor read-only."""
    target = path if not os.path.islink(path) else os.path.dirname(path)
    flags = os.statvfs(target).f_flag
    return bool(flags & os.ST_RELATIME) and not flags & (os.ST_NOATIME | os.ST_RDONLY)


def main():
    w = load()
    w.require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound source launcher required')
    w.read(Path(__file__), _SOURCE_SHA)
    w.require(not os.path.lexists(WINDOW) and not os.path.lexists(INTEGRITY), 'freshen precedes OBSERVE and the window')
    w.read(w.CITY/'city.toml', w.CITY_SHA[0])
    w.read(w.RECEIPT, w.RECEIPT_SHA[0])
    root = Path('/var/tmp/ga-f37t-freshen-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    root.mkdir(mode=0o700)
    w.ROOT = root
    b, o, owned = w.load_support()
    paths = objects(w, b)
    other = [path for path in paths if not relatime(path)]
    w.require(not other, 'objects not on a writable relatime mount: ' + ', '.join(other[:10]))
    before = {path: image(path) for path in paths}
    w.save('before.json', dict(started=datetime.now(timezone.utc).isoformat(), objects=before))
    actions = {path: touch(path) for path in paths}
    after = {path: image(path) for path in paths}
    w.save('after.json', dict(finished=datetime.now(timezone.utc).isoformat(), objects=after, actions=actions))
    changed = []
    for path in paths:
        a = dict(before[path]); z = dict(after[path])
        a.pop('atime_ns'); z.pop('atime_ns')
        w.require(a == z, 'non-atime change during freshen: ' + path)
        if before[path]['atime_ns'] != after[path]['atime_ns']:
            changed.append(path)
    now = datetime.now(timezone.utc).timestamp() * 10**9
    old = []
    for path in paths:
        z = after[path]
        age = (now - z['atime_ns']) / 3.6e12
        if not z['atime_ns'] > max(z['mtime_ns'], z['ctime_ns']) or age >= YOUNG_HOURS:
            mark = datetime.fromtimestamp(z['atime_ns'] / 10**9 + 24 * 3600, timezone.utc).isoformat()
            old.append(dict(path=path, age_hours=round(age, 2), stale_after=mark))
    w.save('old.json', old)
    w.require(not old, '%d objects not young enough; rerun after the stale_after times in old.json' % len(old))
    result = dict(ok=True, objects=len(paths), atime_refreshed=len(changed), content_changed=False,
                  cache_excluded=True, window_started=False, young_hours=YOUNG_HOURS,
                  executor_sha256=_SOURCE_SHA)
    w.save('result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
