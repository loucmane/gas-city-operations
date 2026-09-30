"""Pure bounded create-only Git patch encoding. No I/O or subprocesses."""
import hashlib
import re


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def encode(files, modes, maximum=2 << 20):
    require(isinstance(files, dict) and isinstance(modes, dict)
            and files and set(files)==set(modes), 'exact candidate file inventory')
    require(type(maximum) is int and 0<maximum<=2<<20, 'product bound')
    require(all(isinstance(path,str) and re.fullmatch(r'[A-Za-z0-9_.\/-]+',path)
                and not path.startswith('/') and all(p not in ('','.','..') for p in path.split('/'))
                for path in files), 'unsafe candidate patch path')
    require(all(type(mode) is int and mode in (0o644,0o755) for mode in modes.values()),
            'candidate patch mode')
    require(all(isinstance(raw,bytes) and b'\0' not in raw for raw in files.values()),
            'binary candidate is outside this text-only contract')
    require(sum(map(len,files.values()))<=maximum,'total candidate bytes')
    parts=[]
    for path in sorted(files):
        raw=files[path]
        raw.decode('utf-8','strict')
        # Git hashes authenticate no permission here; SHA256 remains the evidence binding.
        oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        header=(f'diff --git a/{path} b/{path}\nnew file mode {0o100000|modes[path]:06o}\n'
                f'index {"0"*40}..{oid}\n').encode()
        if raw:
            lines=raw.split(b'\n')
            ended=lines[-1]==b''
            if ended:lines.pop()
            header+=(f'--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n').encode()
            header+=b''.join(b'+'+line+b'\n' for line in lines)
            if not ended:header+=b'\\ No newline at end of file\n'
        parts.append(header)
    patch=b''.join(parts)
    require(0<len(patch)<=4<<20,'encoded patch bound')
    return patch
