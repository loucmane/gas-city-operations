"""Read-only proof that the worker left the Template common git directory unchanged (s1 review A 7).

  common-snapshot-r1.py before <out-json>
  common-snapshot-r1.py after <before-json> <before-sha256> <out-json>

The compared set is the common directory's control surface that a sandbox escape could use against the coordinator:
every file and link under the Template .git except the object store (objects/, but objects/info/ is
compared) and this worktree's own index, plus the candidate branch, which must still point at BASE (the
worker delivers staged, uncommitted work). No coordinator git runs in the Template repository during the
window, so every ref is compared. Run `after` immediately after TERMINAL, before any other coordinator
git call. It writes only its own output file.
"""
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

COMMON=Path('/home/loucmane/gas-city-template/.git')
BASE='cfd353f30f465cdf67bbd41fab48812fe5b9617e'
BRANCH='refs/heads/codex/gct-mbg6-template-candidate-lane'
ENV=dict(HOME='/nonexistent',LANG='C.UTF-8',PATH='/usr/bin:/bin',GIT_CONFIG_NOSYSTEM='1',
         GIT_CONFIG_GLOBAL='/dev/null',GIT_OPTIONAL_LOCKS='0')

def entry(path):
    s=os.lstat(path)
    value=dict(mode=stat.S_IMODE(s.st_mode),type=stat.S_IFMT(s.st_mode),uid=s.st_uid,size=s.st_size)
    if stat.S_ISREG(s.st_mode):value['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    elif stat.S_ISLNK(s.st_mode):value['target']=os.readlink(path)
    return value

# s1 r2 (B must_fix 3, A should_fix 1): the codex sandbox can write this whole directory, so the compared set
# is every file and link under it (config, hooks/, info/, refs/, packed-refs, logs/, objects/info/ with its
# alternates, every worktrees/<name>/ admin file, HEAD, shallow, modules/, lfs/) except the object store, which
# `git add` legitimately extends, and this worktree's own index, which `git add` rewrites.
OBJECTS=Path('objects')
MUTABLE={'worktrees/gct-mbg6/index'}

def observe():
    out={}
    for directory,dirs,files in os.walk(COMMON):
        dirs.sort()
        here=Path(directory).relative_to(COMMON)
        # os.walk lists a symlinked directory in dirs and never descends it: record it as a link.
        for name in sorted(files)+[d for d in dirs if os.path.islink(Path(directory)/d)]:
            rel=here/name
            if (rel.parts[:1]==OBJECTS.parts and rel.parts[:2]!=('objects','info')) or str(rel) in MUTABLE:
                continue
            out[str(rel)]=entry(Path(directory)/name)
    r=subprocess.run(['/usr/bin/git','--no-optional-locks','--git-dir='+str(COMMON),'rev-parse','--verify',BRANCH+'^{commit}'],
        env=ENV,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=60)
    assert r.returncode==0,r.stderr
    out['candidate_branch']=r.stdout.strip()
    return out

def write(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=1)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw)
    return hashlib.sha256(raw).hexdigest()

def main(argv):
    if len(argv)==2 and argv[0]=='before':
        value=observe();assert value['candidate_branch']==BASE,'candidate branch is not BASE'
        print(json.dumps(dict(ok=True,entries=len(value),sha256=write(argv[1],value))));return 0
    assert len(argv)==4 and argv[0]=='after','usage: see docstring'
    raw=Path(argv[1]).read_bytes();assert hashlib.sha256(raw).hexdigest()==argv[2],'before record digest'
    before=json.loads(raw);after=observe()
    changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
    result=dict(ok=not changed,changed=changed,candidate_branch=after['candidate_branch'])
    print(json.dumps(dict(result,sha256=write(argv[3],dict(result,after=after)))))
    return 0 if not changed else 1

if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
