"""Pure, four-object read-compatible accounting; never writes timestamps."""
import copy
import stat

CITY = '/home/loucmane/gascity/city'
SUSPENSION = CITY + '/.gc/runtime/suspension-state.json'
DIRECTORIES = {CITY, CITY + '/.beads', CITY + '/.gc/runtime/provisioning'}
PATHS = DIRECTORIES | {SUSPENSION}
FIELDS = {'device', 'inode', 'uid', 'gid', 'mode', 'type', 'nlink', 'size',
          'mtime_ns', 'ctime_ns', 'atime_ns'}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def metadata(path, before, after, window, *, renamed=False):
    require(path in PATHS, 'unapproved read-time path')
    require(type(renamed) is bool and (not renamed or path in DIRECTORIES),
            'read-time rename scope')
    require(set(before) == set(after) == FIELDS, 'read-time metadata fields')
    require(all(type(v) is int and v >= 0 for m in (before, after) for v in m.values()),
            'read-time metadata type')
    kind = stat.S_IFREG if path == SUSPENSION else stat.S_IFDIR
    require(before['type'] == after['type'] == kind, 'read-time object type')
    require(before['uid'] == before['gid'] == after['uid'] == after['gid'] == 1000,
            'read-time object owner')
    ignored = {'atime_ns'} | ({'mtime_ns', 'ctime_ns'} if renamed else set())
    require({k: v for k, v in before.items() if k not in ignored} ==
            {k: v for k, v in after.items() if k not in ignored},
            'non-access metadata changed')
    low, high = window['earliest_ns'], window['latest_ns']
    require(type(low) is int and type(high) is int and 0 <= low <= high,
            'read-time clock bounds')
    # These are the SAME parent times already allowed by the native atomic-
    # replacement proof. This function does not authorize an operation or
    # erase those times; its caller must retain the existing rename proof.
    if renamed:
        for key in ('mtime_ns', 'ctime_ns'):
            if before[key] != after[key]:
                require(after[key] >= before[key] and low <= after[key] <= high,
                        'directory replacement time outside window')
    old, new = before['atime_ns'], after['atime_ns']
    result = copy.deepcopy(after)
    if old == new:
        return result, []
    require(new > old and low <= new <= high, 'access time outside observed window')
    eligible = old <= max(before['mtime_ns'], before['ctime_ns'])
    eligible |= new // 10**9 - old // 10**9 >= 24 * 3600
    if renamed:
        eligible |= old <= max(after['mtime_ns'], after['ctime_ns'])
    require(eligible, 'access time change is not relatime-compatible')
    result['atime_ns'] = old
    return result, [dict(path=path, before_ns=old, after_ns=new,
                         attribution='read-compatible, not process attribution')]


def suspension(before, after, window):
    require(set(before) == set(after) == {'raw', 'pin'}, 'suspension read shape')
    require(set(before['pin']) == set(after['pin']) == {'sha256', 'metadata'},
            'suspension pin shape')
    require(before['raw'] == after['raw'] and
            before['pin']['sha256'] == after['pin']['sha256'],
            'suspension read content changed')
    aligned, changes = metadata(SUSPENSION, before['pin']['metadata'],
                                after['pin']['metadata'], window)
    result = copy.deepcopy(after)
    result['pin']['metadata'] = aligned
    return result, changes
