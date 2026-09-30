"""WORKTREE: create the one ga-3oa7 candidate worktree before the window; never route or resume.

ga-3oa7 (ga-cw-first-window PLAN r12 step 4, gct-lagl HANDOFF 2.10). The coordinator creates the routed
worktree after the previous candidate session drained:
- the candidate root must exist, be a real directory owned by the operator, and be empty;
- the Operations repository's main head must be BASE and the new branch must not exist;
- `git worktree add -b codex/ga-3oa7-dispatch-evidence-write /home/loucmane/gas-city-ops-candidate-worktrees/ga-3oa7 BASE` runs from the canonical repository with no system or global
  config, hooks and fsmonitor off, and a minimal environment;
- afterwards the root holds exactly the worktree, the reviewed candidate_git.verify_linked accepts its gitfile,
  admin directory, back-pointer and commondir, HEAD is BASE, no driver or gitlink applies, and the status with
  ignored files is empty.
It writes nothing else and refuses any existing output root.

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

ROOT=Path('/var/tmp/ga-3oa7-worktree-20260926-r1')
OPS=Path('/home/loucmane/gas-city-ops')
CANDIDATE_ROOT=Path('/home/loucmane/gas-city-ops-candidate-worktrees')
WORK=Path('/home/loucmane/gas-city-ops-candidate-worktrees/ga-3oa7')
ADMIN=Path('/home/loucmane/gas-city-ops/.git/worktrees/ga-3oa7')
BASE='8f24ad7129d81bf54265b916e25c24829c622172'
BRANCH='codex/ga-3oa7-dispatch-evidence-write'
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
    assert os.listdir(CANDIDATE_ROOT)==[],'candidate root is not empty'
    assert git('rev-parse','--verify','refs/heads/main^{commit}').stdout.decode().strip()==BASE,'Operations main is not BASE'
    assert git('rev-parse','--verify','--quiet','refs/heads/'+BRANCH,expected=(1,)).returncode==1,'branch already exists'
    assert not os.path.lexists(ADMIN),'admin directory already exists'
    ROOT.mkdir(mode=0o700)
    (ROOT/'intent.json').write_text(json.dumps(dict(work=str(WORK),base=BASE,branch=BRANCH,executor_sha256=_SOURCE_SHA),
        sort_keys=True)+'\n')
    git('worktree','add','-b',BRANCH,str(WORK),BASE)
    assert os.listdir(CANDIDATE_ROOT)==[WORK.name],'candidate root does not hold exactly the worktree'
    admin=cg.verify_linked(CANDIDATE_ROOT,OPS/'.git',WORK,WORK.name)
    assert admin==ADMIN,'admin directory'
    cg.no_drivers(admin,WORK)
    head=cg.git(admin,WORK,'rev-parse','--verify','HEAD^{commit}').decode().strip()
    assert head==BASE,'worktree HEAD'
    cg.no_gitlinks(admin,WORK,head)
    assert cg.git(admin,WORK,'status','--porcelain','--ignored','-z','--untracked-files=all')==b'','worktree not clean'
    result=dict(ok=True,worktree=str(WORK),admin=str(ADMIN),base=BASE,branch=BRANCH,clean=True,executor_sha256=_SOURCE_SHA)
    (ROOT/'result.json').write_text(json.dumps(result,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
