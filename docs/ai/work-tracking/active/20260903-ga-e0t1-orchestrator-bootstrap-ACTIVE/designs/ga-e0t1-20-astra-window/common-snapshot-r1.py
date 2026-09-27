"""Read-only proof that nothing changed the Template common git directory during the window (s1 r6).

  common-snapshot-r1.py before <out-json>
  common-snapshot-r1.py after <before-json> <before-sha256> <out-json>

Since s1 r5 the codex worker has no write root in the Template .git (it gets the
classified-vault-and-template-worktrees choice) and never stages. Nothing in the window may therefore change this
directory, and any change refuses: no addition is accepted, not even a loose object or an index rewrite.
- Every file, link and directory under the .git, the .git itself included, is compared exactly: type, mode,
  owner, group, size, sha256 or link target. That covers config, hooks/, info/, refs/, packed-refs, logs/, the
  object store (loose objects, packs, indexes, objects/info/ and its alternates), every worktrees/<name>/ admin
  file with its index, HEAD, shallow, modules/ and lfs/.
- It runs no git. Every directory is recorded, any walk error raises, so an unlistable directory cannot hide
  files, and every read is bounded (1 GiB).
- The candidate branch is resolved from the ref bytes (the loose ref file, else packed-refs, each a plain bounded
  file), never through git, and must still point at BASE.
- `before` refuses a baseline carrying a hook other than git's samples and the four pinned git-lfs hooks,
  info/grafts, shallow, refs/replace/ (loose or in packed-refs) or alternates.
Run `before` after WORKTREE and before BIND, and `after` after CLOSE and TERMINAL, before any other coordinator git
call. A `git status` with optional locks in any Template worktree during the window rewrites an index and refuses:
that fails closed and is investigated. It writes only its own output file.
"""
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

COMMON=Path('/home/loucmane/gas-city-ops/.git')
BASE='c6b789bbe6ff677dd04336803dbf2c2e017812ba'
BRANCH='refs/heads/codex/ga-e0t1.20-c1-close-admission'
LIMIT=1<<30

def entry(path):
    s=os.lstat(path)
    value=dict(mode=stat.S_IMODE(s.st_mode),type=stat.S_IFMT(s.st_mode),uid=s.st_uid,gid=s.st_gid)
    if stat.S_ISREG(s.st_mode):
        assert s.st_size<=LIMIT,('file over the read bound',str(path))
        value['size']=s.st_size
        value['nlink']=s.st_nlink
        value['sha256']=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    elif stat.S_ISLNK(s.st_mode):value['target']=os.readlink(path)
    return value

def walk():
    """Every entry under COMMON (directories included, and COMMON itself as '.'), never following a link."""
    out={'.':entry(COMMON)}
    def refuse(error):raise error
    for directory,dirs,files in os.walk(COMMON,onerror=refuse):
        dirs.sort()
        here=Path(directory).relative_to(COMMON)
        for name in sorted(dirs)+sorted(files):
            out[str(here/name)]=entry(Path(directory)/name)
    return out

def plain(path):
    """A plain bounded file's text, or None when absent; anything else refuses."""
    if not os.path.lexists(path):return None
    s=os.lstat(path)
    assert stat.S_ISREG(s.st_mode) and s.st_size<=LIMIT,('not a plain bounded file',str(path))
    return Path(path).read_text()

def branch_target():
    loose=plain(COMMON/BRANCH)
    if loose is not None:return loose.strip()
    for line in (plain(COMMON/'packed-refs') or '').splitlines():
        parts=line.split(' ')
        if len(parts)==2 and parts[1]==BRANCH:return parts[0]
    raise AssertionError('candidate branch not found')

def observe():
    return dict(entries=walk(),candidate_branch=branch_target())

def compare(before,after):
    keys=set(before['entries'])|set(after['entries'])
    changed=[k for k in keys if before['entries'].get(k)!=after['entries'].get(k)]
    if after['candidate_branch']!=BASE:changed.append('candidate_branch')
    return sorted(set(changed))

# The four stock git-lfs hooks the Template repository has carried since 2026-07-30, pinned by content. Every
# coordinator git call in this package disables hooks anyway (core.hooksPath=/dev/null).
LFS_HOOKS={'hooks/post-checkout':'791471b4ff472aab844a4fceaa48bbb0a12193616f971e8e940625498b4938a6',
    'hooks/post-commit':'21e961572bb3f43a5f2fbafc1cc764d86046cc2e5f0bbecebfe9684a0b73b664',
    'hooks/post-merge':'75da0da66a803b4b030ad50801ba57062c6196105eb1d2251590d100edb9390b',
    'hooks/pre-push':'df5417b2daa3aa144c19681d1e997df7ebfe144fb7e3e05138bd80ae998008e4'}

def baseline_problems(value):
    """The recorded baseline itself must carry no hook other than git's samples and the pinned git-lfs hooks, no
    grafts, no shallow, no replace refs (loose or packed) and no alternates, since the later signing relies on it."""
    entries=value['entries']
    problems=[k for k,v in entries.items() if k.startswith('hooks/') and v['type']!=stat.S_IFDIR
        and not k.endswith('.sample') and not (v['type']==stat.S_IFREG and LFS_HOOKS.get(k)==v.get('sha256'))]
    problems+=[k for k in entries if k in ('info/grafts','shallow','objects/info/alternates',
        'objects/info/http-alternates') or k.startswith('refs/replace/')]
    for line in (plain(COMMON/'packed-refs') or '').splitlines():
        parts=line.split(' ')
        if len(parts)==2 and parts[1].startswith('refs/replace/'):problems.append('packed-refs: '+parts[1])
    return problems

def write(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=1)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw)
    return hashlib.sha256(raw).hexdigest()

def main(argv):
    if len(argv)==2 and argv[0]=='before':
        value=observe();assert value['candidate_branch']==BASE,'candidate branch is not BASE'
        assert not baseline_problems(value),('baseline carries',baseline_problems(value))
        print(json.dumps(dict(ok=True,entries=len(value['entries']),sha256=write(argv[1],value))));return 0
    assert len(argv)==4 and argv[0]=='after','usage: see docstring'
    raw=Path(argv[1]).read_bytes();assert hashlib.sha256(raw).hexdigest()==argv[2],'before record digest'
    before=json.loads(raw);after=observe()
    changed=compare(before,after)
    result=dict(ok=not changed,changed=changed,candidate_branch=after['candidate_branch'])
    print(json.dumps(dict(result,sha256=write(argv[3],dict(result,after=after)))))
    return 0 if not changed else 1

if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
