"""Isolated source-byte entrypoint; argv is source path, expected digest, mode."""
import hashlib
import os
import stat
import sys

path, expected = sys.argv[1:3]
fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
try:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_uid != 1000 or before.st_nlink != 1 or before.st_size > 1024*1024:
        raise RuntimeError('source authority')
    raw = b''
    while chunk := os.read(fd, 65536):
        raw += chunk
        if len(raw) > 1024*1024:
            raise RuntimeError('source size bound')
    if before != os.fstat(fd) or len(raw) != before.st_size or hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError('source identity/digest drift')
finally:
    os.close(fd)
sys.argv = [path] + sys.argv[3:]
exec(compile(raw, path, 'exec', dont_inherit=True),
     {'__name__':'__main__', '__file__':path, '_SOURCE_SHA':expected})
