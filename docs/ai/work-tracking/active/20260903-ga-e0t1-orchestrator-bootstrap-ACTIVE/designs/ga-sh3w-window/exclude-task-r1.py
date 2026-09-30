"""EXCLUDE: ignore Core's materialized Claude skill links in Operations worktrees; before the window.

ga-sh3w s2 r2 (review B must_fix 2). For a tmux session whose work_dir is not its scope root, Core writes a skill
catalog under <worktree>/.gc/tmp (already ignored by /.gc/) and runs `gc internal materialize-skills`, which
creates symlinks under <worktree>/.claude/skills. Unignored, they would be untracked symlinks, and intake.py export
refuses those. The Operations repository already ignores the Codex equivalent (.codex/skills/ in .gitignore) and
Claude runtime paths in its common info/exclude. This job appends exactly one line, `**/.claude/skills/`, to that
info/exclude, so the links land in intake's recorded ignored listing and are never imported. Nothing else changes:
- the file must hold the pinned preimage and end with a newline; mode and owner are kept;
- the write is atomic (temporary file in the same directory, fsync, rename);
- the postimage digest is pinned, and the hardened git in the candidate worktree must report
  `.claude/skills/core.gc-probe` as ignored by exactly that line.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT=Path('/var/tmp/ga-sh3w-exclude-20260926-r1')
EXCLUDE=Path('/home/loucmane/gas-city-ops/.git/info/exclude')
BEFORE_SHA='321dffcb77a68a6c079d35da12944866b895b4cc9fb3b1fae72fe9468c7eafeb'
AFTER_SHA='4ef8e39849f5cfe486486339b37f5947d2ff77786250eeeebb7be57170a05bbd'
LINE=b'**/.claude/skills/\n'
WORK='/home/loucmane/gas-city-ops-candidate-worktrees/ga-sh3w'
ADMIN='/home/loucmane/gas-city-ops/.git/worktrees/ga-sh3w'
ENV=dict(HOME='/nonexistent',LANG='C.UTF-8',PATH='/usr/bin:/bin',GIT_CONFIG_NOSYSTEM='1',
         GIT_CONFIG_GLOBAL='/dev/null',GIT_ATTR_NOSYSTEM='1',GIT_OPTIONAL_LOCKS='0')

def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    assert not os.path.lexists(ROOT),'exclude root consumed'
    s=EXCLUDE.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_uid==1000 and s.st_nlink==1,'exclude authority'
    before=EXCLUDE.read_bytes()
    assert hashlib.sha256(before).hexdigest()==BEFORE_SHA and before.endswith(b'\n'),'exclude preimage'
    after=before+LINE
    assert hashlib.sha256(after).hexdigest()==AFTER_SHA,'exclude postimage'
    ROOT.mkdir(mode=0o700)
    (ROOT/'intent.json').write_text(json.dumps(dict(before=BEFORE_SHA,after=AFTER_SHA,executor_sha256=_SOURCE_SHA),
        sort_keys=True)+'\n')
    tmp=EXCLUDE.with_name('.exclude.ga-sh3w.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,stat.S_IMODE(s.st_mode))
    with os.fdopen(fd,'wb') as out:
        out.write(after);out.flush();os.fsync(out.fileno())
    os.rename(tmp,EXCLUDE)
    assert hashlib.sha256(EXCLUDE.read_bytes()).hexdigest()==AFTER_SHA and stat.S_IMODE(EXCLUDE.lstat().st_mode)==stat.S_IMODE(s.st_mode)
    r=subprocess.run(['/usr/bin/git','--no-optional-locks','--git-dir='+ADMIN,'--work-tree='+WORK,'-c','core.hooksPath=/dev/null',
        '-c','core.fsmonitor=false','-c','core.attributesFile=/dev/null','check-ignore','-v','--no-index',
        '.claude/skills/core.gc-probe'],cwd=WORK,env=ENV,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=60)
    assert r.returncode==0 and r.stdout.strip().endswith('**/.claude/skills/\t.claude/skills/core.gc-probe'),r.stdout+r.stderr
    result=dict(ok=True,exclude_before=BEFORE_SHA,exclude_after=AFTER_SHA,ignored_by=r.stdout.strip(),executor_sha256=_SOURCE_SHA)
    (ROOT/'result.json').write_text(json.dumps(result,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
