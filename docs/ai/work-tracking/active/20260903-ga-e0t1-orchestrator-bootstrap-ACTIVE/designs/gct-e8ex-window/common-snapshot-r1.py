"""Read-only proof that the worker left the Template common git directory unchanged (s1 r3).

  common-snapshot-r1.py before <out-json>
  common-snapshot-r1.py after <before-json> <before-sha256> <out-json>

The codex sandbox can write the whole Template .git, so this tool runs no git at all: it reads files only.
- control: every file, link and directory under the .git outside objects/ is compared exactly (type, mode, owner,
  size, sha256 or link target), except this worktree's own index, which `git add` rewrites. That covers config,
  hooks/, info/, refs/, packed-refs, logs/, every worktrees/<name>/ admin file, HEAD, shallow, modules/ and lfs/.
- objects: every entry that exists under objects/ in `before` (loose objects, packs, indexes, objects/info/ with
  its alternates, and every directory) must be unchanged in `after`. The only allowed differences are new
  loose-object directories and NEW loose objects (regular single-link files) whose zlib content hashes to their
  own name, which is what `git add` writes: a new object can never shadow an existing id. A new pack, index or
  multi-pack-index, an overwritten or removed object, and a directory replaced by a link all refuse.
- every directory is recorded (type and mode) and any walk error raises, so an unlistable directory cannot hide
  files; every read is bounded (1 GiB), and the excluded index must stay a plain single-link file.
- the candidate branch is resolved from the ref bytes (the loose ref file, else packed-refs), never through git,
  and must still point at BASE (the worker delivers staged, uncommitted work).
- the .git directory itself is recorded; accepted additions must belong to the operator and not be
  world-writable; a loose object with trailing bytes after its zlib stream refuses.
- `before` refuses a baseline carrying a hook other than git's samples and the four pinned git-lfs hooks,
  info/grafts, shallow, refs/replace/ or alternates.
Known fail-closed cases: `git add` of a file over core.bigFileThreshold (512 MiB) writes a pack, and any file over
1 GiB exceeds the read bound; a worker contained mid-add leaves index.lock or objects/xx/tmp_obj_*. All refuse and
are investigated, not treated as tampering by default.
Run `after` immediately after TERMINAL, before any other coordinator git call. Another Template worktree's index
rewritten during the window (a `git status` there with optional locks) also refuses: it fails closed and is
investigated. It writes only its own output file.
"""
import hashlib
import json
import os
import re
import stat
import sys
import zlib
from pathlib import Path

COMMON=Path('/home/loucmane/gas-city-template/.git')
BASE='cfd353f30f465cdf67bbd41fab48812fe5b9617e'
BRANCH='refs/heads/codex/gct-mbg6-template-candidate-lane'
MUTABLE={'worktrees/gct-mbg6/index'}
LOOSE_DIR=re.compile(r'objects/[0-9a-f]{2}')
LOOSE=re.compile(r'objects/[0-9a-f]{2}/[0-9a-f]{38}')
LIMIT=1<<30

def entry(path):
    s=os.lstat(path)
    value=dict(mode=stat.S_IMODE(s.st_mode),type=stat.S_IFMT(s.st_mode),uid=s.st_uid)
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

def branch_target():
    loose=COMMON/BRANCH
    if os.path.lexists(loose):
        s=os.lstat(loose)
        assert stat.S_ISREG(s.st_mode),'candidate branch ref is not a regular file'
        return loose.read_text().strip()
    packed=COMMON/'packed-refs'
    if os.path.lexists(packed):
        s=os.lstat(packed)
        assert stat.S_ISREG(s.st_mode) and s.st_size<=LIMIT,'packed-refs is not a plain bounded file'
        for line in packed.read_text().splitlines():
            parts=line.split(' ')
            if len(parts)==2 and parts[1]==BRANCH:return parts[0]
    raise AssertionError('candidate branch not found')

def observe():
    everything=walk()
    control={k:v for k,v in everything.items() if k!='objects' and not k.startswith('objects/') and k not in MUTABLE}
    objects={k:v for k,v in everything.items() if k=='objects' or k.startswith('objects/')}
    return dict(control=control,objects=objects,candidate_branch=branch_target())

def loose_ok(rel):
    """A new loose object must hash to its own name, so it can never shadow an existing object id."""
    inflate=zlib.decompressobj()
    try:
        raw=inflate.decompress((COMMON/rel).read_bytes(),LIMIT)
    except zlib.error:
        return False
    if inflate.unconsumed_tail or inflate.unused_data or not inflate.eof:return False
    head,_,body=raw.partition(b'\0')
    kind,_,size=head.partition(b' ')
    return kind in (b'blob',b'tree',b'commit',b'tag') and size.isdigit() and int(size)==len(body) \
        and hashlib.sha1(raw).hexdigest()==rel[8:10]+rel[11:]

def mutable_ok(after):
    """The excluded index must still be a plain, single-link file of the operator."""
    for rel in MUTABLE:
        path=COMMON/rel
        if not os.path.lexists(path):return False
        s=os.lstat(path)
        if not (stat.S_ISREG(s.st_mode) and s.st_uid==1000 and s.st_nlink==1 and s.st_size<=LIMIT):return False
    return True

def compare(before,after):
    changed=sorted(k for k in set(before['control'])|set(after['control'])
        if before['control'].get(k)!=after['control'].get(k))
    for k,v in before['objects'].items():
        if after['objects'].get(k)!=v:changed.append(k)
    for k,v in after['objects'].items():
        if k in before['objects']:continue
        # An accepted addition belongs to the operator and is not world-writable. Group write is allowed: the
        # group is the operator's private group, and a worker under the user manager's umask 0002 makes 0775
        # object directories.
        if v['uid']!=1000 or v['mode']&0o002:
            changed.append(k);continue
        if v['type']==stat.S_IFDIR and LOOSE_DIR.fullmatch(k):continue
        if v['type']==stat.S_IFREG and v['nlink']==1 and LOOSE.fullmatch(k) and loose_ok(k):continue
        changed.append(k)
    if after['candidate_branch']!=BASE:changed.append('candidate_branch')
    if not mutable_ok(after):changed.append('mutable-index')
    return sorted(set(changed))

def write(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=1)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw)
    return hashlib.sha256(raw).hexdigest()

# The four stock git-lfs hooks the Template repository has carried since 2026-07-30, pinned by content. Every
# coordinator git call in this package disables hooks anyway (core.hooksPath=/dev/null).
LFS_HOOKS={'hooks/post-checkout':'791471b4ff472aab844a4fceaa48bbb0a12193616f971e8e940625498b4938a6',
    'hooks/post-commit':'21e961572bb3f43a5f2fbafc1cc764d86046cc2e5f0bbecebfe9684a0b73b664',
    'hooks/post-merge':'75da0da66a803b4b030ad50801ba57062c6196105eb1d2251590d100edb9390b',
    'hooks/pre-push':'df5417b2daa3aa144c19681d1e997df7ebfe144fb7e3e05138bd80ae998008e4'}

def baseline_problems(value):
    """s1 r4 (r3 review B should_fix 9): the recorded baseline itself must carry no hook other than git's samples
    and the pinned git-lfs hooks, no grafts, no replace refs and no alternates, since the later signing step
    relies on it."""
    problems=[k for k,v in value['control'].items() if k.startswith('hooks/') and v['type']!=stat.S_IFDIR
        and not k.endswith('.sample') and not (v['type']==stat.S_IFREG and LFS_HOOKS.get(k)==v.get('sha256'))]
    problems+=[k for k in value['control'] if k in ('info/grafts','shallow') or k.startswith('refs/replace/')]
    problems+=[k for k in value['objects'] if k in ('objects/info/alternates','objects/info/http-alternates')]
    return problems

def main(argv):
    if len(argv)==2 and argv[0]=='before':
        value=observe();assert value['candidate_branch']==BASE,'candidate branch is not BASE'
        assert not baseline_problems(value),('baseline carries',baseline_problems(value))
        print(json.dumps(dict(ok=True,control=len(value['control']),objects=len(value['objects']),
            sha256=write(argv[1],value))));return 0
    assert len(argv)==4 and argv[0]=='after','usage: see docstring'
    raw=Path(argv[1]).read_bytes();assert hashlib.sha256(raw).hexdigest()==argv[2],'before record digest'
    before=json.loads(raw);after=observe()
    changed=compare(before,after)
    added=sorted(set(after['objects'])-set(before['objects']))
    result=dict(ok=not changed,changed=changed,added_objects=len(added),candidate_branch=after['candidate_branch'])
    print(json.dumps(dict(result,sha256=write(argv[3],dict(result,after=after,added=added)))))
    return 0 if not changed else 1

if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
