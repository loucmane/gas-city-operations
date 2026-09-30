"""Read-only actual-host process contract for the existing Codex 0.153.4 lane.

This does not launch, signal, authorize commands or widen a sandbox. A code-mode
host is required by the preceding causal native denial. One configured, pinned
MCP stdio helper is allowed, not arbitrary Node or arbitrary descendants.
"""
import hashlib
import os
from pathlib import Path
import stat

PROC = Path('/proc')
CODEX = '/home/loucmane/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex'
HOST = str(Path(CODEX).with_name('codex-code-mode-host'))
PLUGIN = '/home/loucmane/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.10-13ceeea1f599'
PINS = {
    CODEX: (1000,0o755,'56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da'),
    HOST: (1000,0o755,'3e85d67471825f73d02ff5f7e047ca1f6ca8caa3f59e4c6e8d9ca6ca7302cb45'),
    '/usr/bin/node': (0,0o755,'8071ae0fca095a272ad698a90c7061801a86fb6392ddb81e922b68a91a4374b9'),
    PLUGIN+'/.mcp.json': (1000,0o644,'faac52c49b4b48eae27c54b79f419ed5441414484bed3c9b78e2a521ac69fb26'),
    PLUGIN+'/mcp/server.cjs': (1000,0o644,'eff59c6085d2ab6b6153c80a03749e764e160f8c6711da8433f7bd6762e1db66'),
}


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def fingerprint(s):
    return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,
            s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def root_binary(path, limit=256 << 20):
    """Separate reader; never relax the existing user-owned artifact reader.

    O_NOATIME requires owner privilege for root's Node. Reading it normally is
    allowed; atime is not authority. Exact inode, content, mode and owner stay
    bound. No other root-owned path is accepted by this special reader.
    """
    path = Path(path)
    require(str(path) == '/usr/bin/node' and path.resolve(strict=True)==path, 'root binary path')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        s=os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid==s.st_gid==0 and s.st_nlink==1
                and stat.S_IMODE(s.st_mode)==0o755 and s.st_size<=limit, 'root binary authority')
        chunks=[]; total=0
        while raw:=os.read(fd,65536):
            total+=len(raw); require(total<=limit, 'root binary size bound'); chunks.append(raw)
        require(fingerprint(s)==fingerprint(os.fstat(fd))==fingerprint(path.lstat())
                and total==s.st_size, 'root binary changed')
        return b''.join(chunks)
    finally:
        os.close(fd)


def verify_assets(read):
    for name,(owner,mode,digest) in PINS.items():
        path=Path(name); s=path.lstat()
        require(path.resolve(strict=True)==path and stat.S_ISREG(s.st_mode)
                and s.st_uid==s.st_gid==owner and s.st_nlink==1
                and stat.S_IMODE(s.st_mode)==mode, 'helper asset authority')
        raw=root_binary(path) if owner==0 else read(path,256<<20)
        require(fingerprint(s)==fingerprint(path.lstat()) and hashlib.sha256(raw).hexdigest()==digest,
                'helper asset bytes or identity changed')


def process_table():
    rows={}
    for path in PROC.iterdir():
        if not path.name.isdigit(): continue
        try:
            s=path.stat(); fields=(path/'stat').read_text().rsplit(') ',1)[1].split()
            rows[int(path.name)]=dict(ppid=int(fields[1]),start=fields[19],state=fields[0],uid=s.st_uid,gid=s.st_gid)
        except (FileNotFoundError,ProcessLookupError): continue
    return rows


def proc_bytes(path, limit):
    with path.open('rb') as f: raw=f.read(limit+1)
    require(len(raw)<=limit, 'process input bound')
    return raw


def node(pid, row):
    require(row.get('uid')==row.get('gid')==1000 and row['state'] not in ('Z','X'),
            'process owner or state')
    p=PROC/str(pid); raw=proc_bytes(p/'cmdline',1<<20)
    require(raw.endswith(b'\0') and raw != b'\0', 'process argv encoding')
    argv=raw[:-1].decode('utf-8','strict').split('\0')
    group=proc_bytes(p/'cgroup',4096).decode('utf-8','strict')
    require(group.startswith('0::/') and group.endswith('\n') and group.count('\n')==1, 'process cgroup')
    return dict(pid=pid,ppid=row['ppid'],start=row['start'],exe=os.readlink(p/'exe'),
                cwd=os.readlink(p/'cwd'),argv=argv,cgroup=group)


def graph(pane, rows, v):
    require(pane in rows, 'pane process absent')
    root=node(pane,rows[pane])
    require(root['exe']==CODEX==v.CODEX and root['cwd']==v.WORK, 'pane is not the pinned Codex')
    args=v.process_arguments(root['argv'])
    children=sorted(pid for pid,row in rows.items() if row['ppid']==pane)
    require(1<=len(children)<=2, 'worker child count')
    require(not any(row['ppid'] in children for row in rows.values()), 'nested worker descendant')
    nodes=[root]; kinds=[]
    for pid in children:
        n=node(pid,rows[pid])
        require(n['cgroup']==root['cgroup'], 'helper cgroup differs')
        if n['exe']==HOST:
            require(n['cwd']==v.WORK and n['argv']==[HOST], 'code-mode helper shape')
            kinds.append('code-mode')
        elif n['exe']=='/usr/bin/node':
            require(n['cwd']==PLUGIN and n['argv'] in (
                ['node','./mcp/server.cjs','--stdio'], ['/usr/bin/node','./mcp/server.cjs','--stdio']),
                'MCP helper shape')
            kinds.append('mcp')
        else:
            raise RuntimeError('unknown worker child')
        nodes.append(n)
    require(sorted(kinds) in (['code-mode'],['code-mode','mcp']), 'helper multiplicity')
    # Raw argv includes the prompt, and is never persisted. Its digest still
    # detects exec/argument changes even if PID and start ticks are unchanged.
    public=[dict(pid=n['pid'],ppid=n['ppid'],start=n['start'],exe=n['exe'],cwd=n['cwd'],
        cgroup=n['cgroup'],argv_sha256=hashlib.sha256(b'\0'.join(x.encode() for x in n['argv'])).hexdigest()) for n in nodes]
    return public,args


def environment(pane, session):
    raw=proc_bytes(PROC/str(pane)/'environ',1<<20)
    pairs=[x.partition(b'=') for x in raw.split(b'\0') if x]
    wanted={b'GC_SESSION_ID':session['id'].encode(),b'GC_SESSION_NAME':session['session_name'].encode(),
        b'GC_HOME':b'/home/loucmane/gascity/home',b'GIT_OPTIONAL_LOCKS':b'0',b'HOME':b'/home/loucmane'}
    for key,value in wanted.items():
        require([v for k,sep,v in pairs if k==key]==[value], 'worker environment identity differs')
    names={k for k,sep,value in pairs}
    require(not names.intersection((b'OPENAI_API_KEY',b'CODEX_API_KEY',b'OPENAI_BASE_URL',
        b'ANTHROPIC_API_KEY',b'ANTHROPIC_AUTH_TOKEN',b'ANTHROPIC_BASE_URL')), 'worker has provider override')
    require([v for k,sep,v in pairs if k==b'CODEX_HOME'] in ([],[b'/home/loucmane/.codex']), 'unexpected CODEX_HOME')


def revalidate(proof,v,read):
    verify_assets(read)
    observed,args=graph(proof['pid'],process_table(),v)
    require(observed==proof['chain'] and args==proof['argv'], 'worker exec or graph changed')
    environment(proof['pid'],proof['session_identity'])


def worker_identity(pane,session,v,read):
    verify_assets(read)
    nodes,args=graph(pane,process_table(),v)
    environment(pane,session)
    logs=set()
    for fd in (PROC/str(pane)/'fd').iterdir():
        try: target=os.readlink(fd)
        except FileNotFoundError: continue
        if target.startswith('/home/loucmane/.codex/sessions/') and target.endswith('.jsonl'): logs.add(target)
    require(len(logs)==1, 'native transcript not uniquely open by worker')
    path=Path(next(iter(logs))); key=v.transcript_key(path,session)
    native=v.denial_from_rollout(read(path,32<<20),key)
    proof=dict(pid=pane,start=nodes[0]['start'],chain=nodes,argv=args,transcript_path=str(path),
        native=native,session_identity={k:session[k] for k in ('id','session_name')})
    revalidate(proof,v,read)
    return proof
