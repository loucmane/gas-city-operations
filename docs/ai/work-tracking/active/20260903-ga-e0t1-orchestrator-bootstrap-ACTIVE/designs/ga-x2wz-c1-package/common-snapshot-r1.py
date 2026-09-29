"""Read-only proof that nothing changed the Operations common Git directory during the window (s1 r6).

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
BASE='bf369ae41cf512f5f5563f842cadff394457da4c'
BRANCH='refs/heads/codex/ga-x2wz-c1-package'
LIMIT=1<<30

# Operator-approved exact baseline only. No permission is changed.
CONFIG_EXCEPTIONS = {'config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ci-0x17-evidence-prompt-port/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-25cw-evidence-reviewer-isolation/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-2mfo-source-closeout-recovery/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-2mfo-workflow-identity/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-357r-unify-hierarchical-bead-ids/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-35mj-exclude-closed-work-from-continuity-current-view/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-35mj-terminal-closeout-canonical/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-35mj-terminal-closeout/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-3oa7/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-6utp-ops-candidate-activation/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-c8al-support-hierarchical-bead-ids-in-transactional-workflow-lifecycl/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-e0t1-orchestrator-bootstrap/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-e0t1.3-stationary-target-a/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ejrm-closeout/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-fjoi.1-stationary-pending-id/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-hd6c-source-closeout-recovery/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-iebz-workflow-transitions/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-jdp7-evidence-hook-trust/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-k0ry-evidence-workflow-v1/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ob3l-obsidian-cycle-consistency/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-sh3w/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c-4-parent-audit-worktree/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c-6-2-source-closeout-continuation/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.1-continuity-status-auditor/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.2-canonical-root-lifecycle-parity/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.3-continuously-reconcile-every-registered-project-into-obsidian/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.4-enforce-gas-city-delegation-in-managed-projects/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.4.1-project-trust-bootstrap/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.4.1-transactionally-prove-managed-codex-delegation-denial/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.4.2-delegation-test-lint/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.5-attention-funnel/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.6.2-source-closeout-continuation/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.6.3-source-closeout-continuation/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.6.4-obsidian-cycle-stability/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.6.5-runtime-residue/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.6.6-desktop-retest/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.6.7-obsidian-check-serialization/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ur1c.7-canonical-root-audit/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-ve57-bind-obsidian-exports-to-explicit-rig-roots-and-exact-rollback/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-wwmw-evidence-reviewer-policy/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-x7lx-intake/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/ga-x7lx/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}, 'worktrees/gco-ga-ob3l-closeout-20260901/config.worktree': {'gid': 1000, 'mode': 436, 'nlink': 1, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'type': 32768, 'uid': 1000}}

def entry(path):
    path=Path(path)
    s=path.lstat()
    value=dict(mode=stat.S_IMODE(s.st_mode),type=stat.S_IFMT(s.st_mode),uid=s.st_uid,gid=s.st_gid)
    assert s.st_uid==s.st_gid==1000, 'common Git authority'
    try:relative=str(path.relative_to(COMMON))
    except ValueError:relative=None
    exception=CONFIG_EXCEPTIONS.get(relative)
    if exception is None:
        assert not s.st_mode&0o022, 'common Git authority'
    else:
        assert value=={key:exception[key] for key in value}, 'common Git exception metadata'
    if stat.S_ISREG(s.st_mode):
        assert s.st_size<=LIMIT and s.st_nlink==1, 'common Git file bound or links'
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_NOATIME|os.O_CLOEXEC)
        try:
            assert os.fstat(fd)==s, 'common Git open race'
            h=hashlib.sha256();size=0
            while block:=os.read(fd,1048576):
                size+=len(block);assert size<=LIMIT, 'common Git read overflow';h.update(block)
            assert os.fstat(fd)==s and path.lstat()==s and size==s.st_size, 'common Git changed during read'
        finally:os.close(fd)
        value.update(size=size,nlink=s.st_nlink,sha256=h.hexdigest())
    elif stat.S_ISLNK(s.st_mode):
        raise AssertionError('common Git symlink requires review')
    else:assert stat.S_ISDIR(s.st_mode), 'common Git special file'
    if exception is not None:assert value==exception, 'common Git exception content or links'
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
    assert CONFIG_EXCEPTIONS.keys()<=out.keys(), 'common Git exception missing'
    return out

def plain(path):
    if not os.path.lexists(path):return None
    s=path.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_size<=LIMIT and s.st_nlink==1, 'common Git plain input'
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_NOATIME|os.O_CLOEXEC)
    try:
        assert os.fstat(fd)==s
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(LIMIT+1)
        assert len(raw)==s.st_size and os.fstat(fd)==s and path.lstat()==s
    finally:os.close(fd)
    return raw.decode('utf-8','strict')

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
