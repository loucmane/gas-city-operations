"""Tenth successor s1: derive the ga-x7lx Operations candidate window (ga-fsfg R3 retry) from the reviewed
ga-sh3w window package.

  python3 -B make_successor.py <output package dir>

The ga-sh3w window (14baeedf, two SOURCE_PASS) ran on 2026-09-26 and closed cleanly through TERMINAL, but the
candidate stopped before any edit with gc.failure_class bead_brief_unreadable: `bd show ga-sh3w` printed about
52K characters (the 33K description plus the embedded related ga-fsfg record), over the candidate's inline read
limit. On the operator's decision the reviewed r12 brief (5cbf64f1) was split verbatim: task ga-x7lx (a short
head, a pointer and the working rules, no dependency edge) and the closed spec holders ga-lpo2 and ga-r2el.

1. Every source is read from the ga-sh3w s2 r2 commit object (14baeedf), never from a working tree.
2. Identity: ga-sh3w becomes ga-x7lx everywhere: the task, the worktree
   /home/loucmane/gas-city-ops-candidate-worktrees/ga-x7lx, its admin directory, the branch
   codex/ga-x7lx-delivery-class, every output root and the staging directory. The consumed ga-sh3w worktree
   was retired (intake.py retire, archived and locked), so the candidate root is empty again.
3. Dropped: README.md, the tests and the generator (replaced), and the EXCLUDE job: the common info/exclude
   already carries the one line (4ef8e398) and a rerun would refuse its preimage. BIND instead requires the
   live info/exclude to be exactly that postimage.
4. BIND (bind-task-r5.py) binds gc.work_dir and gc.check_path only, as before, and requires the ga-x7lx
   description (DESCRIPTION_SHA) and no dependency edge at all.
5. Accepted image: the ga-sh3w TERMINAL observed-after record, taken by the same snapshot() after RESTORE on this
   epoch; only its cache, host, pins and protected keys are compared (the ga-n12k pattern). The provider pins
   stay the P10 adoption record's (82a4a70c). The coordinator-cache disposition, approved by the operator for
   ga-x7lx on 2026-09-26, admits exactly the pack-cache repository's .git mtime and ctime, from the TERMINAL
   value to the value s2 pins after the last coordinator note.
6. PREP targets the ga-x7lx worktree, so the overlay (OVERLAY_NEW) is re-derived; s2 re-pins the fresh PREP
   outputs. The host epoch, receipt, revision, M9 inspector and reviewed candidate tools are unchanged.
7. Digest propagation to a fixed point.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = '14baeedf'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
DESIGNS = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
PREFIX = DESIGNS + 'ga-sh3w-window/'
DROP = {'README.md', 'test_successor.py', 'exclude-task-r1.py', 'operator/EXCLUDE.sh', 'bind-task-r4.py',
        'operator/BIND.sh'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

OPS = '/home/loucmane/gas-city-ops'
CANDIDATE_ROOT = '/home/loucmane/gas-city-ops-candidate-worktrees'
WORK = CANDIDATE_ROOT + '/ga-x7lx'
ADMIN = OPS + '/.git/worktrees/ga-x7lx'
BRANCH = 'codex/ga-x7lx-delivery-class'
BASE = '040139d8738a025cbb5afcc8170b700292c5016e'
TARGET = 'gascity/operations-candidate-worker'
BEAD = 'ga-x7lx'
# The ga-x7lx description: the r12 head and working rules verbatim, with the pointer to the spec holders.
DESCRIPTION_SHA = 'acc57fd5fd1f095d8d6df6a4003313c7e53219e6cddde5dd1061ed8f7d36e610'
# The r12 R3 brief the head, both spec holders and the tail reassemble to, byte for byte.
BRIEF_SHA = '5cbf64f179cca878e2ecfc2898c44a6b465ffa84cfaae558b2fcb0377b65c942'
SPECS = (('ga-lpo2', '5e4a56c007549f8688a16a5621e2517d945677043da1a68e7095ef9636c462bf'),
         ('ga-r2el', 'e6f36bcaab0b4a8134161cffd727cb087638282ca998965fdf449560ec11cdc8'))
CHECK_PATH = ('/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f'
              '/gascity/assets/scripts/checks/build-artifact-valid.sh')
EXCLUDE = OPS + '/.git/info/exclude'
EXCLUDE_AFTER = '4ef8e39849f5cfe486486339b37f5947d2ff77786250eeeebb7be57170a05bbd'

ACCEPTED_OLD = ('/var/tmp/ga-e0t1.18-p10-adoption-20260926/after.json',
                'aaeb7d8f5277102bc020e61aeebba5a8d38f74de500148ee3fb1a7b79c02dd23')
ACCEPTED_NEW = ('/var/tmp/ga-sh3w-terminal-20260926-r1/observed-after.json',
                '97df4a335f8656ace8179c61bd0af7e59d765dfef46f64f51a9cf5741c31bf37')
PROVIDER = ('/var/tmp/ga-e0t1.18-p10-adoption-20260926/after.json.provider-pins',
            '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b')
# The pack-cache .git mtime and ctime in the ga-sh3w TERMINAL record; s2 pins the value after the last note.
CACHE_PREV_NS = 1790415062719606803
CACHE_PINNED_NS = None
OVERLAY_OLD = '8b039657aa28ab5edc10ab50fcd26cea1a3ed15abf65ddae69fdca3c568ca50f'
# Derived read-only by the generated build_overlay from the live city.toml (4f7e170f) and the confined gc config
# and order list (2026-09-26); it differs from 8b039657 only in the header line and the candidate work_dir.
OVERLAY_NEW = '45014c22e045447fe75b4969e0d01667bf2dab36763ae06abdf8a9c13b6f2425'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.run(['git', '--no-optional-locks', '-C', WORKTREE, *args], check=True,
                          capture_output=True).stdout


def sources():
    names = git('ls-tree', '-r', '--name-only', SOURCE, PREFIX).decode().split('\n')
    files = {}
    for path in names:
        if not path:
            continue
        name = path[len(PREFIX):]
        if name in DROP or name.startswith(DROP_DIRS):
            continue
        files[name] = git('show', SOURCE + ':' + path)
    return files


def sub(text, old, new, count=1):
    assert text.count(old) == count, (old[:90], text.count(old))
    return text.replace(old, new)


def rename(text):
    return text.replace('ga-sh3w', 'ga-x7lx')


def window_base(text):
    text = sub(text, "ga-x7lx r11: a rebind of the reviewed ga-y49e base window-state-r6-read-safe.py (b10a3810) onto the\n"
                     "post-P10 baseline (M9 metadata, receipt c833908f, gc fce2e9a0) and the candidate task ga-x7lx.",
               "ga-x7lx r11: a rebind of the reviewed ga-y49e base window-state-r6-read-safe.py (b10a3810) onto the\n"
               "post-P10 baseline (M9 metadata, receipt c833908f, gc fce2e9a0) and the candidate task ga-x7lx, admitted\n"
               "against the ga-sh3w TERMINAL record (tenth successor).")
    text = sub(text, "# The accepted image is the P10 adoption snapshot on the post-sequence-15 host (two readback reviews).\n"
                     "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\nPROVIDER_SHA = '%s'\n"
               % (ACCEPTED_OLD[0], ACCEPTED_OLD[1], PROVIDER[1]),
               "# The accepted image is the ga-sh3w TERMINAL observed-after record: this same snapshot() after RESTORE on\n"
               "# this epoch (TERMINAL PASS 2026-09-26 10:23Z, full native integrity). Its extra keys (providers,\n"
               "# directories) are not part of the compared image; the provider pins stay the P10 adoption record's.\n"
               "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\nACCEPTED_KEYS = ('cache', 'host', 'pins', 'protected')\n"
               "PROVIDER = Path('%s')\nPROVIDER_SHA = '%s'\n" % (ACCEPTED_NEW[0], ACCEPTED_NEW[1], PROVIDER[0], PROVIDER[1]))
    text = sub(text, "        # The P10 snapshot was taken on this epoch after sequence 15; only the coordinator-cache\n"
                     "        # disposition of this window applies (approved_candidate_cache_image).\n"
                     "        require(RECOVERY is None, 'no recovery admission in this window')\n"
                     "        image = approved_candidate_cache_image(prior)\n",
               "        # The ga-sh3w TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n"
               "        # disposition of this window applies (approved_candidate_cache_image).\n"
               "        require(RECOVERY is None, 'no recovery admission in this window')\n"
               "        image = approved_candidate_cache_image({key: prior[key] for key in ACCEPTED_KEYS})\n")
    text = sub(text, "    accepted_provider=json.loads(read(Path(str(ACCEPTED)+'.provider-pins'),PROVIDER_SHA))\n",
               "    accepted_provider=json.loads(read(PROVIDER,PROVIDER_SHA))\n")
    text = sub(text, "CACHE_P10_NS = 1790411960644198389\nCACHE_PINNED_NS = 1790415062719606803\n",
               "CACHE_PREV_NS = %d\nCACHE_PINNED_NS = %s\n" % (CACHE_PREV_NS, CACHE_PINNED_NS))
    text = sub(text, "    # ga-x7lx disposition, operator-approved 2026-09-26, for independent review: after the P10 adoption\n"
                     "    # snapshot, the coordinator recorded M9, P10 and the vault inventory on ga-e0t1 through the canonical\n"
                     "    # workflow.py, whose Bead reads run bd without GIT_OPTIONAL_LOCKS=0. That advances only the pack\n"
                     "    # cache repository's .git directory mtime and ctime. s2 pins the value after the last such note;\n",
               "    # ga-x7lx disposition, operator-approved 2026-09-26, for independent review: after the\n"
               "    # ga-sh3w TERMINAL record, the coordinator recorded the ga-sh3w outcome and the brief split on ga-e0t1 through\n"
               "    # the canonical workflow.py, whose Bead reads run bd without GIT_OPTIONAL_LOCKS=0. That advances only\n"
               "    # the pack cache repository's .git directory mtime and ctime. s2 pins the value after the last note;\n")
    text = sub(text, "        require(entry[key] == CACHE_P10_NS, 'coordinator cache exception preimage')\n",
               "        require(entry[key] == CACHE_PREV_NS, 'coordinator cache exception preimage')\n")
    return text


def prep(text):
    if OVERLAY_NEW is not None:
        text = sub(text, "OVERLAY_SHA = '%s'" % OVERLAY_OLD, "OVERLAY_SHA = '%s'" % OVERLAY_NEW)
        text = sub(text, "'overlay bytes differ from the derived %s'" % OVERLAY_OLD[:8],
                   "'overlay bytes differ from the derived %s'" % OVERLAY_NEW[:8])
    text = sub(text, "r8 (ga-x7lx, the first Operations candidate window)", "r8 (ga-sh3w, the first Operations candidate window)")
    text = sub(text, "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n",
               "\nr9 (ga-x7lx, the tenth successor): the ga-sh3w prep retargeted to task ga-x7lx and its candidate worktree;\n"
               "the overlay header and work_dir change, nothing else.\n"
               "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n")
    return text


BIND_TASK = '''"""The one ga-x7lx contract binding before the window: gc.work_dir and gc.check_path; never route or resume.

ga-x7lx: bind-task-r5.py replaces the ga-sh3w bind-task-r4.py. The Bead description is the short task brief
(sha256 %(description)s): the reviewed r12 R3 brief head and working rules, verbatim, and a pointer to the closed
spec holders ga-lpo2 and ga-r2el; together they reassemble to the r12 brief. The task carries no dependency edge,
so `bd show` prints no embedded record. The binding sets exactly two metadata keys:
- gc.work_dir: the candidate worktree the WORKTREE job created;
- gc.check_path: the check the P10 candidate receipt profile pins. Core's start preflight requires this stamp
  on the driving Bead; the path is executed only by formula (ralph) steps, and ROUTE uses --no-formula.
No option override (opt_*) and no template override is written, since either would change the launch argv the
receipt pins. The ga-sh3w EXCLUDE job already appended the Core skill-link line, so the live common info/exclude
must be exactly its postimage. It runs as its own job BEFORE the window, so no window root may exist yet.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE=Path('%(here)s')
ROOT=Path('/var/tmp/ga-x7lx-bind-20260926-r1')
HELPER=HERE/'window-base-r11.py'
HELPER_SHA='%(helper)s'
WORKTREE_RESULT=Path('/var/tmp/ga-x7lx-worktree-20260926-r1/result.json')
WORKTREE_SHA='%(worktree)s'
EXCLUDE=Path('%(exclude)s')
EXCLUDE_AFTER='%(exclude_after)s'
DESCRIPTION_SHA='%(description)s'
BEAD='%(bead)s'
TARGET='%(target)s'
WORK='%(work)s'
CHECK='%(check)s'

def main():
    assert os.getuid()==os.geteuid()==1000 and globals().get('_SOURCE_SHA')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==_SOURCE_SHA
    raw=HELPER.read_bytes();assert hashlib.sha256(raw).hexdigest()==HELPER_SHA
    w=types.ModuleType('binding_window');w.__file__=str(HELPER)
    exec(compile(raw,str(HELPER),'exec',dont_inherit=True),w.__dict__)
    w._SOURCE_SHA=HELPER_SHA
    b,o,owned=w.load_support();w.pins()
    made=json.loads(w.read(WORKTREE_RESULT))
    assert made==dict(ok=True,worktree=WORK,admin=str(w.ADMIN),base=w.BASE,branch='%(branch)s',clean=True,
        executor_sha256=WORKTREE_SHA),'worktree job result'
    s=EXCLUDE.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_uid==1000,'exclude authority'
    assert hashlib.sha256(EXCLUDE.read_bytes()).hexdigest()==EXCLUDE_AFTER,'common info/exclude is not the EXCLUDE postimage'
    assert not os.path.lexists(w.ROOT), 'binding must precede the window'
    w.read(w.CITY/'city.toml',w.CITY_SHA[0]);w.read(w.RECEIPT,w.RECEIPT_SHA[0])
    ROOT.mkdir(mode=0o700);w.ROOT=ROOT
    def run(name,args):return w.phase(name,args,b,owned)
    def bead(name):
        rows=json.loads(run(name,w.GC+['--rig','gascity','bd','show',BEAD,'--json'])['stdout'])
        assert isinstance(rows,list) and len(rows)==1 and rows[0]['id']==BEAD
        return rows[0]
    before_host=w.host(o)
    before=bead('task-before-read');w.save('task-before.json',before)
    assert before['status']=='open' and not before.get('assignee') and not before.get('metadata')
    assert hashlib.sha256(before['description'].encode()).hexdigest()==DESCRIPTION_SHA,'description is not the reviewed brief'
    assert not before.get('dependencies'),'unexpected Bead edge'
    metadata={'gc.work_dir':WORK,'gc.check_path':CHECK}
    argv=w.GC+['--rig','gascity','bd','update',BEAD]
    for key,value in metadata.items():argv+=['--set-metadata',key+'='+value]
    w.save('binding-intent.json',dict(before=before,metadata=metadata,description_sha256=DESCRIPTION_SHA,
        executor_sha256=_SOURCE_SHA,worker_launched=False))
    run('task-bind',argv)
    after=bead('task-after-read');w.save('task-after.json',after)
    assert after['metadata']==metadata
    for key in set(before)|set(after):
        if key not in ('metadata','updated_at'):
            assert before.get(key)==after.get(key),key
    assert w.host(o)==before_host
    w.save('result.json',dict(ok=True,bead=BEAD,contract_bound=True,routed=False,assigned=False,
        worker_launched=False,live_configuration_changed=False))
    print(json.dumps(w.record('result.json')))

if __name__=='__main__':main()
'''


JOB = '''#!/bin/sh
# ga-x7lx window %(label)s: %(what)s
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-x7lx-window/%(slug)s-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-x7lx-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-x7lx-window
COMMIT=${1:?usage: %(script)s <reviewed commit>}
STEP_SHA=%(step_sha)s
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/%(slug)s-$(date -u +%%Y%%m%%dT%%H%%M%%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e %(out)s ] && [ ! -L %(out)s ]; } || { echo "== STOP: output root already used: %(out)s"; echo "== end"; exit 1; }
echo "== %(slug)s $(date -u +%%H:%%M:%%SZ)"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/%(file)s" "$STEP_SHA"
rc=$?
if [ "$rc" != 0 ]; then
  echo "== %(upper)s REFUSED rc=$rc: read this log and %(out)s before any further step"
  echo "== end $(date -u +%%H:%%M:%%SZ)"; exit "$rc"
fi
echo "== %(upper)s PASS"
echo "== end $(date -u +%%H:%%M:%%SZ)"
exit 0
'''


def route(text, bind_sha):
    text = sub(text, "DESCRIPTION_SHA='%s'\n" % BRIEF_SHA, "DESCRIPTION_SHA='%s'\n" % DESCRIPTION_SHA)
    [old] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", text, re.M)
    return text.replace("BIND_SHA='%s'" % old, "BIND_SHA='%s'" % bind_sha)


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = rename(raw.decode())
        if name == 'window-base-r11.py':
            text = window_base(text)
        elif name == 'prep-r11.py':
            text = prep(text)
        elif name == 'operator/PREP.sh':
            text = sub(text, '# ga-x7lx window prep r8:', '# ga-x7lx window prep r9:')
        out[name] = text.encode()
    here = WORKTREE + '/' + DESIGNS + 'ga-x7lx-window'
    out['bind-task-r5.py'] = (BIND_TASK % dict(here=here, helper=sha(out['window-base-r11.py']),
                                               worktree=sha(out['worktree-task-r1.py']), exclude=EXCLUDE,
                                               exclude_after=EXCLUDE_AFTER, description=DESCRIPTION_SHA, bead=BEAD,
                                               target=TARGET, work=WORK, check=CHECK_PATH, branch=BRANCH)).encode()
    out['operator/BIND.sh'] = (JOB % dict(label='bind', what='the one ga-x7lx contract binding (gc.work_dir, '
                                          'gc.check_path), before the window.', slug='bind', script='BIND.sh',
                                          file='bind-task-r5.py', out='/var/tmp/ga-x7lx-bind-20260926-r1',
                                          step_sha=sha(out['bind-task-r5.py']), upper='BIND')).encode()
    out['route-task-r5.py'] = route(out['route-task-r5.py'].decode(), sha(out['bind-task-r5.py'])).encode()
    history = {name: {sha(raw)} for name, raw in files.items()}
    keep = {'window-base-r11.py': set()}
    while True:
        for name, raw in out.items():
            history.setdefault(name, set()).add(sha(raw))
        renamed = {old: sha(out[n]) for n in out for old in history[n] if old != sha(out[n])}
        changed = False
        for name, raw in out.items():
            if not name.endswith(('.py', '.sh')):
                continue
            text = raw.decode()
            kept = keep.get(name, set())
            new = DIGEST.sub(lambda m: m.group(0) if m.group(0) in kept else renamed.get(m.group(0), m.group(0)), text)
            if new != text:
                out[name] = new.encode()
                changed = True
        if not changed:
            break
    return out


def main(output):
    out = rebind(sources())
    root = Path(output)
    for name, data in sorted(out.items()):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if name.endswith('.sh') else 0o644)
    print(len(out), 'files written to', root)


if __name__ == '__main__':
    main(*sys.argv[1:])
