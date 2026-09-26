"""WORKTREE: create the one gct-mbg6 candidate worktree before the window; never route or resume.

gct-mbg6 (the first Template codex window; from ga-cw-first-window PLAN r12 step 4). The coordinator creates the
routed worktree of the Template repository:
- the worktree path must not exist (the Template worktree root holds other worktrees);
- the Template origin/main must be BASE (the local main ref has diverged and is not used) and the new branch
  must not exist;
- `git worktree add -b codex/gct-mbg6-template-candidate-lane /home/loucmane/gas-city-template-worktrees/gct-mbg6 BASE` runs from the canonical repository with no system or global
  config, hooks and fsmonitor off, and a minimal environment;
- afterwards the worktree exists, the reviewed candidate_git.verify_linked accepts its gitfile, admin
  directory, back-pointer and commondir, HEAD is BASE, no gitlink applies, the drivers are exactly the pinned
  git-lfs set, and the status with ignored files is empty.
It writes nothing else (besides the new branch's reflog, which `worktree add -b` creates) and refuses any
existing output root. s1 r2/r3: the pinned drivers, no config include directive, the absent attributes
file, the .gitattributes bytes, and BASE's single .gitattributes with no gitlink or .gitmodules are
checked before the output root is created and before the add, so no checkout-time filter can run and a
refusal there consumes nothing.

Partial failure: if `git worktree add` succeeds and a post-check refuses, the worktree, its admin directory and
the branch stay, and ROOT holds only intent.json. BIND refuses without this job's exact result.json, so nothing
can be routed. Recovery is a coordinator decision recorded on the Bead: inspect, then `git worktree remove` and
delete the branch, and rerun from a new reviewed commit with a new output root (-r1 is consumed).
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

ROOT=Path('/var/tmp/gct-mbg6-worktree-20260926-r1')
OPS=Path('/home/loucmane/gas-city-template')
CANDIDATE_ROOT=Path('/home/loucmane/gas-city-template-worktrees')
WORK=Path('/home/loucmane/gas-city-template-worktrees/gct-mbg6')
ADMIN=Path('/home/loucmane/gas-city-template/.git/worktrees/gct-mbg6')
BASE='cfd353f30f465cdf67bbd41fab48812fe5b9617e'
BRANCH='codex/gct-mbg6-template-candidate-lane'
TOOLS=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-6utp-activation-r10/candidate_git.py')
TOOLS_SHA='d2894e829618ad1fdcb5640b47b99baa3c783173acccb4f7f5918c958823bebe'
ENV=dict(HOME='/nonexistent',USER='loucmane',LOGNAME='loucmane',LANG='C.UTF-8',PATH='/usr/bin:/bin',
         GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_ATTR_NOSYSTEM='1',GIT_OPTIONAL_LOCKS='0')

def git(*args,expected=(0,)):
    r=subprocess.run(['/usr/bin/git','--no-optional-locks','-C',str(OPS),'-c','core.hooksPath=/dev/null',
        '-c','core.fsmonitor=false','-c','core.attributesFile=/dev/null',*args],env=ENV,stdin=subprocess.DEVNULL,
        capture_output=True,timeout=120)
    assert r.returncode in expected,(args,r.returncode,r.stderr[-2000:])
    return r

def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    raw=TOOLS.read_bytes();assert hashlib.sha256(raw).hexdigest()==TOOLS_SHA
    cg=types.ModuleType('candidate_git');cg.__file__=str(TOOLS);sys.modules['candidate_git']=cg
    exec(compile(raw,str(TOOLS),'exec',dont_inherit=True),cg.__dict__)
    assert not os.path.lexists(ROOT),'worktree root consumed'
    s=CANDIDATE_ROOT.lstat()
    assert stat.S_ISDIR(s.st_mode) and s.st_uid==1000 and not stat.S_IMODE(s.st_mode)&0o022,'candidate root authority'
    assert not os.path.lexists(WORK),'worktree path already exists'
    # The Template deployed head is origin/main; the local main ref has diverged and is not used.
    assert git('rev-parse','--verify','refs/remotes/origin/main^{commit}').stdout.decode().strip()==BASE,'Template origin/main is not BASE'
    assert git('rev-parse','--verify','--quiet','refs/heads/'+BRANCH,expected=(1,)).returncode==1,'branch already exists'
    assert not os.path.lexists(ADMIN),'admin directory already exists'
    # Template variant, s1 r2: before the checkout, the common config carries exactly the pinned git-lfs
    # drivers, no repository attributes file exists, and the one tracked .gitattributes at BASE is the
    # reviewed blob, whose bytes select no filter, diff or merge driver.
    drivers=git('config','--includes','--get-regexp',r'^(filter|diff|merge)\.',expected=(0,1)).stdout
    assert hashlib.sha256(drivers).hexdigest()=='a3cf4a1c62cb600373035123a48f183b55253d98337e4a430c8a483c49b7be70','Template driver config is not the git-lfs set'
    assert not os.path.lexists(OPS/'.git'/'info'/'attributes'),'repository attributes file present'
    assert git('rev-parse','--verify',BASE+':.gitattributes').stdout.decode().strip()=='84c48ec45d32b997de49fa694d00b7e4ba3c677e'
    assert git('cat-file','blob','84c48ec45d32b997de49fa694d00b7e4ba3c677e').stdout==b'# Patch files preserve diff syntax; embedded context markers otherwise look\n# like whitespace errors to an outer `git diff --check`.\npatches/*.patch -whitespace\n','.gitattributes content'
    assert git('config','--get-regexp',r'^include',expected=(1,)).returncode==1,'config include directive'
    tree=git('ls-tree','-r','-z','--full-tree',BASE).stdout.split(b'\0')
    assert [e for e in tree if e.rsplit(b'\t',1)[-1].rsplit(b'/',1)[-1]==b'.gitattributes']==[b'100644 blob 84c48ec45d32b997de49fa694d00b7e4ba3c677e\t.gitattributes'],'BASE attributes files'
    assert not [e for e in tree if e.startswith(b'160000 ')],'BASE gitlink'
    assert not [e for e in tree if e.rsplit(b'\t',1)[-1]==b'.gitmodules'],'BASE .gitmodules'
    ROOT.mkdir(mode=0o700)
    (ROOT/'intent.json').write_text(json.dumps(dict(work=str(WORK),base=BASE,branch=BRANCH,executor_sha256=_SOURCE_SHA),
        sort_keys=True)+'\n')
    git('worktree','add','-b',BRANCH,str(WORK),BASE)
    assert WORK.is_dir() and not WORK.is_symlink(),'worktree not created'
    admin=cg.verify_linked(CANDIDATE_ROOT,OPS/'.git',WORK,WORK.name)
    assert admin==ADMIN,'admin directory'
    head=cg.git(admin,WORK,'rev-parse','--verify','HEAD^{commit}').decode().strip()
    assert head==BASE,'worktree HEAD'
    cg.no_gitlinks(admin,WORK,head)
    # Template variant of no_drivers: exactly the pre-existing git-lfs drivers, no repository attributes file,
    # and the one tracked .gitattributes (it selects no filter) at the reviewed blob.
    drivers=cg.git(admin,WORK,'config','--includes','--get-regexp',r'^(filter|diff|merge)\.',expected=(0,1))
    assert hashlib.sha256(drivers).hexdigest()=='a3cf4a1c62cb600373035123a48f183b55253d98337e4a430c8a483c49b7be70','Template driver config is not the git-lfs set'
    for extra in (admin/'info'/'attributes',admin.parent.parent/'info'/'attributes'):
        assert not os.path.lexists(extra),('repository attributes file present',str(extra))
    attrs=[p for p in cg.split_z(cg.git(admin,WORK,'ls-tree','-r','-z','--name-only','--full-tree',head))
        if p.rsplit('/',1)[-1]=='.gitattributes']
    assert attrs==['.gitattributes'],('tracked attributes files',attrs)
    assert cg.git(admin,WORK,'rev-parse','--verify',head+':.gitattributes').decode().strip()=='84c48ec45d32b997de49fa694d00b7e4ba3c677e'
    assert cg.git(admin,WORK,'status','--porcelain','--ignored','-z','--untracked-files=all')==b'','worktree not clean'
    result=dict(ok=True,worktree=str(WORK),admin=str(ADMIN),base=BASE,branch=BRANCH,clean=True,executor_sha256=_SOURCE_SHA)
    (ROOT/'result.json').write_text(json.dumps(result,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
