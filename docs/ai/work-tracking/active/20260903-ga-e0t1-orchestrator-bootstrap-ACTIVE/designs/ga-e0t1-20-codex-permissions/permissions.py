"""Exact metadata-only recovery; never writes transcripts or changes lifecycle."""
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

DEFAULT = 'system.posix_acl_default'
PRIVATE = struct.pack('<I', 2) + b''.join(
    struct.pack('<HHI', tag, perm, 0xFFFFFFFF)
    for tag, perm in ((1, 7), (4, 0), (32, 0)))
FIELDS = ('dev', 'ino', 'uid', 'gid', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def open_exact(path, directory=False):
    """No symlink traversal, including intermediate components."""
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'noncanonical path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for index, part in enumerate(path.parts[1:]):
            intermediate = index < len(path.parts) - 2
            flags = os.O_NOFOLLOW | os.O_CLOEXEC
            flags |= os.O_PATH if intermediate else (os.O_RDONLY | os.O_NONBLOCK | os.O_NOATIME)
            if directory or intermediate:
                flags |= os.O_DIRECTORY
            nxt = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = nxt
        require(os.fstat(fd) == path.lstat(), 'path identity drift')
        return fd
    except BaseException:
        os.close(fd)
        raise


def image(fd):
    before = os.fstat(fd)
    require(before.st_uid == before.st_gid == os.getuid() == 1000, 'target owner')
    is_dir = stat.S_ISDIR(before.st_mode)
    require(is_dir or stat.S_ISREG(before.st_mode), 'target type')
    require(is_dir or before.st_nlink == 1, 'target hardlink')
    attrs = {key: os.getxattr(fd, key).hex() for key in os.listxattr(fd)}
    result = dict(stat={key: getattr(before, 'st_' + key) for key in FIELDS}, xattrs=attrs)
    if not is_dir:
        require(before.st_size <= 1 << 20, 'rules size bound')
        os.lseek(fd, 0, os.SEEK_SET)
        raw = os.read(fd, (1 << 20) + 1)
        require(len(raw) == before.st_size, 'rules read size')
        result['sha256'] = sha(raw)
    require(before == os.fstat(fd), 'target changed during read')
    return result


def semantic(value):
    result = json.loads(json.dumps(value))
    result['stat'].pop('ctime_ns')
    return result


def stable_identity(path, fd):
    require(Path(path).resolve(strict=True) == Path(path), 'target ancestor alias')
    require(Path(path).lstat() == os.fstat(fd), 'target renamed or replaced')


def inventory(root):
    """Metadata only: no historical transcript contents are read or written."""
    root = Path(root)
    out = {}
    def visit(path, depth):
        require(depth <= 8 and len(out) < 100000, 'inventory bound')
        fd = open_exact(path, directory=True)
        try:
            before = os.fstat(fd)
            out[str(path)] = {k: getattr(before, 'st_' + k) for k in FIELDS}
            names = sorted(os.listdir(fd))
            for name in names:
                child = path / name
                s = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(not stat.S_ISLNK(s.st_mode), 'inventory symlink')
                if stat.S_ISDIR(s.st_mode):
                    visit(child, depth + 1)
                else:
                    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'inventory special file')
                    out[str(child)] = {k: getattr(s, 'st_' + k) for k in FIELDS}
                require(len(out) <= 100000, 'inventory entry bound')
            require(before == os.fstat(fd) and names == sorted(os.listdir(fd)), 'inventory race')
            stable_identity(path, fd)
        finally:
            os.close(fd)
    visit(root, 0)
    return out


def preserve_inventory(before, after, allowed):
    require(set(before) == set(after), 'new or missing descendant')
    for path, old in before.items():
        new = after[path]
        if path in allowed:
            old = {k: v for k, v in old.items() if k in ('dev', 'ino', 'uid', 'gid', 'nlink', 'size', 'mtime_ns')}
            new = {k: v for k, v in new.items() if k in old}
        require(old == new, 'historical or unrelated entry changed: ' + path)


def save(root, name, value):
    require('/' not in name, 'evidence basename')
    fd = os.open(Path(root) / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    parent = open_exact(root, directory=True)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


class Ambiguous(RuntimeError):
    pass


def operate(fd, action, value):
    if action == 'mode':
        os.fchmod(fd, value)
    elif action == 'default':
        if value is None:
            os.removexattr(fd, DEFAULT)
        else:
            os.setxattr(fd, DEFAULT, bytes.fromhex(value))
    else:
        raise RuntimeError('unknown metadata action')
    os.fsync(fd)


def expected_image(old, action, value):
    new = json.loads(json.dumps(old))
    if action == 'mode':
        new['stat']['mode'] = stat.S_IFMT(new['stat']['mode']) | value
    elif action == 'default':
        if value is None:
            new['xattrs'].pop(DEFAULT, None)
        else:
            new['xattrs'][DEFAULT] = value
    else:
        raise RuntimeError('unknown metadata action')
    return new


def transaction(entries, expected, evidence, guard, prove, after_step=lambda _: None):
    """Compensate only exact postimages while quiescent. Ctimes stay honest.

    One operator-approved recovery, not a reusable recursive chmod operation.
    A fault after a syscall is classified by rereading, not by its return code.
    """
    current = {p: image(fd) for p, fd in entries.items()}
    require(current == expected, 'reviewed preimage drift')
    for p, fd in entries.items():
        stable_identity(p, fd)
        require(not current[p]['xattrs'], 'unexpected preexisting xattr')
    guard()
    save(evidence, 'preimage.json', current)
    history = []
    attempt = None
    try:
        for p, fd in entries.items():
            is_dir = stat.S_ISDIR(current[p]['stat']['mode'])
            actions = [('mode', 0o700 if is_dir else 0o600)]
            if is_dir:
                actions.append(('default', PRIVATE.hex()))
            for action, value in actions:
                guard()
                stable_identity(p, fd)
                require(image(fd) == current[p], 'metadata drift before operation')
                old = current[p]
                wanted = expected_image(old, action, value)
                attempt = (p, fd, action, old, wanted)
                save(evidence, f'{len(history):02d}-intent.json', dict(path=p, action=action,
                     before=old, expected_after=semantic(wanted)))
                operate(fd, action, value)
                observed = image(fd)
                require(semantic(observed) == semantic(wanted), 'unexpected operation postimage')
                current[p] = observed
                history.append(attempt)
                attempt = None
                save(evidence, f'{len(history):02d}-applied.json', dict(path=p, after=observed))
                after_step(len(history))
        guard()
        for p, fd in entries.items():
            stable_identity(p, fd)
            require(image(fd) == current[p], 'final metadata drift')
        proof = prove(current)
        guard()
        for p, fd in entries.items():
            stable_identity(p, fd)
            require(image(fd) == current[p], 'metadata drift during proof')
        save(evidence, 'postimage.json', current)
        save(evidence, 'result.json', dict(ok=True, creation_proof=proof, worker_release=False,
             historical_transcripts_modified=False, ctime_changes_preserved=True))
        return current
    except BaseException as primary:
        try:
            guard()
            if attempt is not None:
                p, fd, action, old, wanted = attempt
                stable_identity(p, fd)
                observed = image(fd)
                if semantic(observed) == semantic(wanted):
                    current[p] = observed
                    history.append(attempt)
                elif observed != old:
                    raise Ambiguous('unclassified attempted mutation')
            for p, fd in entries.items():
                stable_identity(p, fd)
                require(image(fd) == current[p], 'rollback postimage drift')
            for number, (p, fd, action, old, wanted) in enumerate(reversed(history)):
                guard()
                stable_identity(p, fd)
                require(image(fd) == current[p], 'rollback target drift')
                prior = stat.S_IMODE(old['stat']['mode']) if action == 'mode' else old['xattrs'].get(DEFAULT)
                operate(fd, action, prior)
                observed = image(fd)
                require(semantic(observed) == semantic(old), 'rollback verification failed')
                current[p] = observed
                save(evidence, f'rollback-{number:02d}.json', dict(path=p, after=observed))
            guard()
            require(all(semantic(current[p]) == semantic(expected[p]) for p in entries),
                    'rollback incomplete')
            save(evidence, 'failure.json', dict(error=repr(primary), rollback='verified',
                 restored=current, retry=False, worker_release=False))
        except BaseException as recovery:
            save(evidence, 'ambiguous.json', dict(error=repr(primary), recovery_error=repr(recovery),
                 retry=False, worker_release=False))
            raise Ambiguous('stop: partial mutation or rollback not proven') from recovery
        raise
