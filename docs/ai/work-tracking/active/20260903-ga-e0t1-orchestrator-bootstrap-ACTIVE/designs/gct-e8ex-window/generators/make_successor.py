"""Twelfth successor s1: the first Template-rig codex window, derived from the reviewed ga-3oa7 window package.

  python3 -B make_successor.py <output package dir>

Step 4 of the goal needs the Template Claude candidate lane (gct-e8ex) before the Claude<->Codex handover proof
(gct-oak5). The only worker scoped to build it is the Template rig's `codex` agent (gas-city-native prompt;
provider codex, gpt-5.6-sol, max_active_sessions 1), whose Codex quota returned on 2026-09-26. Its brief is split
for readability (designs/gct-e8ex-split r9): task gct-mbg6 (TASK below) plus six closed holders.

The window stack is the reviewed ga-3oa7 package (s2 c991d20c, ran live cleanly on 2026-09-26), retargeted:
1. Identity: ga-3oa7 becomes TASK; the target gascity/operations-candidate-worker becomes gas-city-template/codex;
   the rig gascity becomes gas-city-template everywhere the window resumes, suspends, audits or reads Beads.
2. Worktree: a new registered Template worktree /home/loucmane/gas-city-template-worktrees/TASK of the Template
   repository at origin/main cfd353f3 (the deployed Template; the local `main` ref has diverged and is not used),
   on branch codex/TASK-template-candidate-lane. The Template worktree root holds other worktrees, so WORKTREE
   requires only that the new path, branch and admin directory are absent.
3. Pre-route: the reviewed ga-6utp preroute.check requires the candidate root to hold exactly the worktree, which a
   Template root cannot. ROUTE calls the same reviewed pieces instead: city_problems against the process record,
   verify_linked, HEAD == BASE, no_gitlinks, the pinned git-lfs drivers (in place of no_drivers), a clean status
   with ignored files, survey of processes holding the worktree, the gc.work_dir and description checks, and (from
   the split reviews) no notes, no assignee and a JSON view under 9000 bytes.
4. BIND sets only gc.work_dir: the codex agent is not in the provisioning receipt, so Core's start preflight does
   not gate it and needs no gc.check_path stamp. There is no info/exclude check (no intake.py export: the codex
   worker stages its tree in the worktree and the coordinator signs in place).
5. PREP: the overlay suspends every Template agent except codex (Dir '' and 'gas-city-template'), binds codex to
   the worktree with sessions 0..1; the codex singleton warning is already in the baseline.
6. Accepted image: the ga-3oa7 TERMINAL observed-after record, with the same one-field coordinator-cache
   disposition class (it needs the operator's approval for this window at s2).
7. The common-directory snapshot moves to the Template repository's .git.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = 'c991d20c'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
DESIGNS = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
PREFIX = DESIGNS + 'ga-3oa7-window/'
DROP = {'README.md', 'test_successor.py'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

TASK = 'gct-mbg6'
DESCRIPTION_SHA = '381cd7a83680b4259e7a774f61876d7e9ff619d6c7f13b746fe7359feb770004'
PACKAGE = 'gct-e8ex-window'
TEMPLATE_REPO = '/home/loucmane/gas-city-template'
ROOT_DIR = '/home/loucmane/gas-city-template-worktrees'
WORK = ROOT_DIR + '/' + TASK
ADMIN = TEMPLATE_REPO + '/.git/worktrees/' + TASK
BRANCH = 'codex/' + TASK + '-template-candidate-lane'
BASE_OLD, BASE = '8f24ad7129d81bf54265b916e25c24829c622172', 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
TARGET_OLD, TARGET = 'gascity/operations-candidate-worker', 'gas-city-template/codex'
OLD_WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-3oa7'
OLD_ADMIN = '/home/loucmane/gas-city-ops/.git/worktrees/ga-3oa7'
OLD_BRANCH = 'codex/ga-3oa7-dispatch-evidence-write'
OLD_DESCRIPTION = '9d6b2e1a1cd9a34fd6d9a05c5ab643fd6a324b62af31dd0bae8f545bf67fb935'


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
    """Identity and rig retarget common to every file (longest strings first)."""
    for old, new in ((OLD_WORK, WORK), (OLD_ADMIN, ADMIN), (OLD_BRANCH, BRANCH), (BASE_OLD, BASE),
                     (OLD_DESCRIPTION, DESCRIPTION_SHA), (TARGET_OLD, TARGET),
                     ("'--rig','gascity'", "'--rig','gas-city-template'"),
                     ("'--rig', 'gascity'", "'--rig', 'gas-city-template'"),
                     ('/designs/ga-3oa7-window', '/designs/' + PACKAGE),
                     ('gas-city-staging/ga-3oa7-window', 'gas-city-staging/' + PACKAGE)):
        text = text.replace(old, new)
    return text.replace('ga-3oa7', TASK)


PREROUTE_OLD = (
    "    checked=pr.check(Path('/home/loucmane/gas-city-ops-candidate-worktrees'),Path('/home/loucmane/gas-city-ops/.git'),"
    "'%s',bead_json,1000,\n"
    "        pr.load_record(RECORD,RECORD_SHA),w.BASE,DESCRIPTION_SHA)\n"
    "    assert checked['ok'] is True and checked['worktree']=='%s'\n")
PREROUTE_NEW = (
    "    # Template variant: the reviewed preroute.check requires the candidate root to hold exactly the worktree,\n"
    "    # which a Template worktree root cannot. It calls the same reviewed pieces, in the same order.\n"
    "    record=pr.load_record(RECORD,RECORD_SHA)\n"
    "    slice_root=pr.user_slice(1000)\n"
    "    city=pr.city_problems(slice_root,record)\n"
    "    assert not city,('the city is not quiet',city)\n"
    "    root=Path('%(root)s');common=Path('%(repo)s/.git');work=root/'%(task)s'\n"
    "    admin=cg.verify_linked(root,common,work,'%(task)s')\n"
    "    cg.no_drivers(admin,work)\n"
    "    head=cg.git(admin,work,'rev-parse','--verify','HEAD^{commit}').decode().strip()\n"
    "    assert head==w.BASE,('worktree HEAD',head)\n"
    "    cg.no_gitlinks(admin,work,head)\n"
    "    assert cg.git(admin,work,'status','--porcelain','--ignored','-z','--untracked-files=all')==b'','routed worktree is not freshly clean'\n"
    "    problems=pr.survey(work,1000,slice_root,record['hidden'])\n"
    "    assert not problems,('processes hold the worktree',problems)\n"
    "    shown_bead=json.loads(shown);shown_bead=shown_bead[0] if isinstance(shown_bead,list) else shown_bead\n"
    "    assert (shown_bead.get('metadata') or {}).get('gc.work_dir')==str(work),'gc.work_dir'\n"
    "    assert hashlib.sha256(str(shown_bead.get('description','')).encode()).hexdigest()==DESCRIPTION_SHA,'description'\n"
    "    # gct-e8ex split r8/r9 reviews: the stop check reads the notes, so none may exist before the first session,\n"
    "    # and the view must still fit the split's 9000-byte cap after BIND stamped its metadata.\n"
    "    assert not shown_bead.get('notes') and not shown_bead.get('assignee'),'task has notes or an assignee before routing'\n"
    "    assert len(shown.encode() if isinstance(shown,str) else shown)<9000,'task view over the split cap'\n"
    "    checked=dict(ok=True,worktree=str(work),admin=str(admin),bead='%(task)s',base=head,controller=record['controller'],\n"
    "        variant='template-root-pieces')\n")


# The Template repository keeps the git-lfs filter drivers in its own config (not candidate-controlled) and one
# .gitattributes that selects no filter. The reviewed no_drivers refuses any driver, so the Template variant pins
# exactly these instead: the driver lines (sha256 of `config --includes --get-regexp ^(filter|diff|merge)\.` in
# the hardened environment), no repository attributes file, and the single tracked .gitattributes blob at BASE.
LFS_DRIVERS_SHA = 'a3cf4a1c62cb600373035123a48f183b55253d98337e4a430c8a483c49b7be70'
GITATTRIBUTES_BLOB = '84c48ec45d32b997de49fa694d00b7e4ba3c677e'
DRIVERS_CHECK = (
    "    # Template variant of no_drivers: exactly the pre-existing git-lfs drivers, no repository attributes file,\n"
    "    # and the one tracked .gitattributes (it selects no filter) at the reviewed blob.\n"
    "    drivers=cg.git(admin,%(w)s,'config','--includes','--get-regexp',r'^(filter|diff|merge)\\.',expected=(0,1))\n"
    "    assert hashlib.sha256(drivers).hexdigest()=='" + LFS_DRIVERS_SHA + "','Template driver config is not the git-lfs set'\n"
    "    for extra in (admin/'info'/'attributes',admin.parent.parent/'info'/'attributes'):\n"
    "        assert not os.path.lexists(extra),('repository attributes file present',str(extra))\n"
    "    attrs=[p for p in cg.split_z(cg.git(admin,%(w)s,'ls-tree','-r','-z','--name-only','--full-tree',head))\n"
    "        if p.rsplit('/',1)[-1]=='.gitattributes']\n"
    "    assert attrs==['.gitattributes'],('tracked attributes files',attrs)\n"
    "    assert cg.git(admin,%(w)s,'rev-parse','--verify',head+':.gitattributes').decode().strip()=='" + GITATTRIBUTES_BLOB + "'\n")


def route(text):
    new = PREROUTE_NEW % dict(root=ROOT_DIR, repo=TEMPLATE_REPO, task=TASK)
    new = sub(new, "    cg.no_drivers(admin,work)\n", "")
    new = sub(new, "    cg.no_gitlinks(admin,work,head)\n", "    cg.no_gitlinks(admin,work,head)\n" + DRIVERS_CHECK % dict(w='work'))
    return sub(text, PREROUTE_OLD % (TASK, WORK), new)


def bind(text):
    text = sub(text, '"""The one %s contract binding before the window: gc.work_dir and gc.check_path; never route or resume.' % TASK,
               '"""The one %s contract binding before the window: gc.work_dir only; never route or resume.' % TASK)
    text = sub(text, "No option override (opt_*) and no template override is written, since either would change the launch argv the\n"
                     "receipt pins. The ga-sh3w EXCLUDE job already appended the Core skill-link line, so the live common info/exclude\n"
                     "must be exactly its postimage. It runs as its own job BEFORE the window, so no window root may exist yet.\n",
               "Template window (twelfth successor): the codex agent is not in the provisioning receipt, so the Core start\n"
               "preflight does not gate it and no gc.check_path stamp is written; the binding sets gc.work_dir only. There is\n"
               "no info/exclude check: the codex worker stages in its worktree and the coordinator signs in place. No option\n"
               "or template override is written. It runs as its own job BEFORE the window, so no window root may exist yet.\n")
    text = sub(text, "    s=EXCLUDE.lstat()\n"
                     "    assert stat.S_ISREG(s.st_mode) and s.st_uid==1000,'exclude authority'\n"
                     "    assert hashlib.sha256(EXCLUDE.read_bytes()).hexdigest()==EXCLUDE_AFTER,'common info/exclude is not the EXCLUDE postimage'\n",
               '')
    text = sub(text, "EXCLUDE=Path('/home/loucmane/gas-city-ops/.git/info/exclude')\n"
                     "EXCLUDE_AFTER='4ef8e39849f5cfe486486339b37f5947d2ff77786250eeeebb7be57170a05bbd'\n", '')
    text = sub(text, "CHECK='/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f"
                     "/gascity/assets/scripts/checks/build-artifact-valid.sh'\n", '')
    # gct-e8ex split r8/r9 reviews: the worker's stop check reads the task notes, so none may exist.
    text = sub(text, "    assert before['status']=='open' and not before.get('assignee') and not before.get('metadata')\n",
               "    assert before['status']=='open' and not before.get('assignee') and not before.get('metadata')\n"
               "    assert not before.get('notes'),'task has notes before the first session'\n")
    return sub(text, "    metadata={'gc.work_dir':WORK,'gc.check_path':CHECK}\n", "    metadata={'gc.work_dir':WORK}\n")


def worktree(text):
    text = sub(text, "OPS=Path('/home/loucmane/gas-city-ops')\nCANDIDATE_ROOT=Path('/home/loucmane/gas-city-ops-candidate-worktrees')\n",
               "OPS=Path('%s')\nCANDIDATE_ROOT=Path('%s')\n" % (TEMPLATE_REPO, ROOT_DIR))
    text = sub(text, "    assert os.listdir(CANDIDATE_ROOT)==[],'candidate root is not empty'\n"
                     "    assert git('rev-parse','--verify','refs/heads/main^{commit}').stdout.decode().strip()==BASE,'Operations main is not BASE'\n",
               "    assert not os.path.lexists(WORK),'worktree path already exists'\n"
               "    # The Template deployed head is origin/main; the local main ref has diverged and is not used.\n"
               "    assert git('rev-parse','--verify','refs/remotes/origin/main^{commit}').stdout.decode().strip()==BASE,'Template origin/main is not BASE'\n")
    text = sub(text, "    assert os.listdir(CANDIDATE_ROOT)==[WORK.name],'candidate root does not hold exactly the worktree'\n",
               "    assert WORK.is_dir() and not WORK.is_symlink(),'worktree not created'\n")
    text = sub(text, "    cg.no_drivers(admin,WORK)\n", "")
    return sub(text, "    cg.no_gitlinks(admin,WORK,head)\n", "    cg.no_gitlinks(admin,WORK,head)\n" + DRIVERS_CHECK % dict(w='WORK'))


OVERLAY_OLD = '0e583359552b9c765ae0da5cf971397d6cf0e96b03613238721cc797aad64940'
# Derived read-only by the generated build_overlay from the live city.toml and the confined gc config and order
# list (2026-09-26): 42 agent patches, only gas-city-template/codex unsuspended (work_dir the gct-mbg6 worktree,
# sessions 0..1), 33 order skips.
OVERLAY_NEW = 'ecc53a30ebcd6bb678c9932895b313afed2ef806f79a699b2ad2643588eacb93'
# The P10 provider pins the observers compare (unchanged from ga-3oa7).
PROVIDER = ('/var/tmp/ga-e0t1.18-p10-adoption-20260926/after.json.provider-pins',
            '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b')
# The split (designs/gct-e8ex-split at e6fa8ecd): holder ids in position order.
SPLIT_COMMIT = 'e6fa8ecd5c1c0a15939ff77f11dbe364f6c68e99'
HOLDERS = ('gct-v1nl', 'gct-q6a4', 'gct-t54b', 'gct-2fax', 'gct-ilmv', 'gct-icv2')
# s2: the gct-mbg6 PREP outputs replace the ga-3oa7 ones in window-base (empty until PREP has run).
PREP_PINS = []


def prep(text):
    text = sub(text, "OVERLAY_SHA = '%s'" % OVERLAY_OLD, "OVERLAY_SHA = '%s'" % OVERLAY_NEW)
    text = sub(text, "'overlay bytes differ from the derived %s'" % OVERLAY_OLD[:8],
               "'overlay bytes differ from the derived %s'" % OVERLAY_NEW[:8])
    text = sub(text, "    target = identities.index(('gascity', 'operations-candidate-worker'))\n"
                     "    assert agents[target]['Provider'] == 'claude-candidate' and agents[target]['Suspended'] is True\n",
               "    target = identities.index(('gas-city-template', 'codex'))\n"
               "    # The Template codex agent is held only by the suspension of its rig, not at the agent level.\n"
               "    assert agents[target]['Provider'] == 'codex' and agents[target]['Suspended'] is False\n"
               "    # Its sandbox write roots include the Template .git (git add and write-tree need it); city.toml, which\n"
               "    # defines that choice, is pinned by digest.\n"
               "    assert agents[target]['OptionDefaults'] == {'worklog_access': 'classified-vault-template-worktrees-and-git-metadata'}\n")
    text = sub(text, "    selected = [i for i, a in enumerate(agents) if a['Dir'] in ('', 'gascity')]\n",
               "    selected = [i for i, a in enumerate(agents) if a['Dir'] in ('', 'gas-city-template')]\n")
    text = sub(text, "   - every city and gascity agent suspended, except gas-city-template/codex, which is\n",
               "   - every city and gas-city-template agent suspended, except gas-city-template/codex, which is\n")
    return sub(text, "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n",
               "\nr11 (%s, the first Template codex window): the ga-3oa7 prep retargeted to the gas-city-template rig. The\n"
               "one unsuspended agent is gas-city-template/codex (provider codex), bound to the Template worktree; every\n"
               "other city and Template agent is suspended; its max_active_sessions = 1 already produces the singleton\n"
               "warning.\n"
               "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n" % TASK)


def lineage(text):
    for old, new in (("GC+['rig','resume','gascity','--json']", "GC+['rig','resume','gas-city-template','--json']"),
                     ("GC+['rig','suspend','gascity','--json']", "GC+['rig','suspend','gas-city-template','--json']"),
                     ("require('gascity' in v['rigs'],'missing target rig')",
                      "require('gas-city-template' in v['rigs'],'missing target rig')"),
                     ("a['rigs']['gascity']", "a['rigs']['gas-city-template']"),
                     ("expected['rigs']['gascity']", "expected['rigs']['gas-city-template']")):
        text = sub(text, old, new)
    return text


def hold(text):
    text = sub(text, "--json`, then `gc rig suspend gascity --json`, from suspension-lineage.py ACTIONS)",
               "--json`, then `gc rig suspend gas-city-template --json`, from suspension-lineage.py ACTIONS)")
    text = sub(text, "the city and the gascity rig suspended.", "the city and the gas-city-template rig suspended.")
    text = sub(text, "[r for r in value['rigs'] if r['name'] == 'gascity']",
               "[r for r in value['rigs'] if r['name'] == 'gas-city-template']")
    return sub(text, "w.GC + ['rig', 'suspend', 'gascity', '--json']", "w.GC + ['rig', 'suspend', 'gas-city-template', '--json']")


def audit(text):
    text = sub(text, "ALIASES = {TARGET, 'operations-candidate-worker', 'gascity--operations-candidate-worker'}",
               "ALIASES = {TARGET, 'codex', 'gas-city-template--codex'}")
    text = sub(text, "for store, scope in [('core', ['--rig', 'gas-city-template']), ('city', [])]:",
               "for store, scope in [('template', ['--rig', 'gas-city-template']), ('city', [])]:")
    text = sub(text, "== (['%s'] if store=='core' else []), store+' routed'" % TASK,
               "== (['%s'] if store=='template' else []), store+' routed'" % TASK)
    text = sub(text, "            if name=='open' and store=='core' and v['id']=='%s':" % TASK,
               "            if name=='open' and store=='template' and v['id']=='%s':" % TASK)
    text = sub(text, "a.startswith(('ci-', 's-', TARGET+'-', 'operations-candidate-worker-',\n"
                     "                                               'gascity--operations-candidate-worker-'))",
               "a.startswith(('ci-', 's-', TARGET+'-', 'codex-', 'gas-city-template--codex-'))")
    text = sub(text, "the gascity rig resumed). Generated by make_round2b.py.",
               "the gas-city-template rig resumed). Generated by make_round2b.py.")
    text = sub(text, "# route mode: every rig suspended. resume mode: only the gascity rig resumed.",
               "# route mode: every rig suspended. resume mode: only the gas-city-template rig resumed.")
    return sub(text, "(MODE == 'route' or r['name'] != 'gascity')", "(MODE == 'route' or r['name'] != 'gas-city-template')")


ACCEPTED_OLD = ('/var/tmp/ga-x7lx-terminal-20260926-r1/observed-after.json',
                '59e76bbfeb395759ec93a688ef4dfb81af89148d679eda7626a3a0e7c4f327d7')
ACCEPTED_NEW = ('/var/tmp/ga-3oa7-terminal-20260926-r1/observed-after.json',
                '3059c650ff43f5a492d193432f7c467240c017f38d635df1845ea3fec5a36307')
# The pack-cache .git mtime and ctime in the ga-3oa7 TERMINAL record; s2 pins the value after the last note.
CACHE_OLD = (1790419645618740930, 1790431776352453342)
CACHE_PREV_NS = 1790431776352453342
CACHE_PINNED_NS = None


def window_base(text):
    """Applied after the rename, so the ga-3oa7 accepted path is inserted literally."""
    text = sub(text, "against the ga-x7lx TERMINAL record (eleventh successor).",
               "against the ga-3oa7 TERMINAL record (twelfth successor, the first Template codex window).")
    text = sub(text, "# The accepted image is the ga-x7lx TERMINAL observed-after record: this same snapshot() after RESTORE on\n"
                     "# this epoch (TERMINAL PASS 2026-09-26 13:11Z, full native integrity).",
               "# The accepted image is the ga-3oa7 TERMINAL observed-after record: this same snapshot() after RESTORE on\n"
               "# this epoch (TERMINAL PASS 2026-09-26 15:30Z, full native integrity).")
    text = sub(text, "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_OLD,
               "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_NEW)
    for old, new in PREP_PINS:
        text = sub(text, "'%s'" % old, "'%s'" % new)
    text = sub(text, "CACHE_PREV_NS = %d\nCACHE_PINNED_NS = %d\n" % CACHE_OLD,
               "CACHE_PREV_NS = %d\nCACHE_PINNED_NS = %s\n" % (CACHE_PREV_NS, CACHE_PINNED_NS))
    text = sub(text, "    # ga-x7lx TERMINAL record, the coordinator recorded the ga-x7lx outcome, the R3 intake and merge and the R4 brief on ga-e0t1 through\n",
               "    # ga-3oa7 TERMINAL record, the coordinator recorded the R4 intake and merge and the gct-e8ex split on ga-e0t1 through\n")
    return sub(text, "        # The ga-x7lx TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n",
               "        # The ga-3oa7 TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n")


def observer_integrity(text):
    for old in ("against the ga-x7lx TERMINAL record (%s window)," % TASK,
                "the accepted image is the ga-x7lx TERMINAL record (window-base).",
                "compared exactly with the ga-x7lx TERMINAL record.",
                "admits the live state against the ga-x7lx TERMINAL record\n"):
        text = sub(text, old, old.replace('ga-x7lx', 'ga-3oa7'))
    return text


def common(text):
    return sub(text, "COMMON=Path('/home/loucmane/gas-city-ops/.git')", "COMMON=Path('%s/.git')" % TEMPLATE_REPO)


# The global rename also rewrites history lines that name the predecessors; these restore them and state the
# Template retarget instead (applied after the per-file edits, each asserted exactly once).
FIXUPS = {
    'bind-task-r5.py': [
        ("%(task)s: bind-task-r5.py as reviewed for ga-x7lx, rebound to R4. The Bead description is the short task brief\n"
         "(sha256 %(desc)s): the reviewed r12 R4 brief head and working rules, verbatim, the r15 pre-window\n"
         "clarifications and a pointer to the closed spec holders ga-elig and ga-aju4; head, parts and tail reassemble\n"
         "to the r12 R4 brief. The task carries no dependency edge,\n"
         "so `bd show` prints no embedded record. The binding sets exactly two metadata keys:\n"
         "- gc.work_dir: the candidate worktree the WORKTREE job created;\n"
         "- gc.check_path: the check the P10 candidate receipt profile pins. Core's start preflight requires this stamp\n"
         "  on the driving Bead; the path is executed only by formula (ralph) steps, and ROUTE uses --no-formula.\n",
         "%(task)s: bind-task-r5.py as reviewed for ga-x7lx and ga-3oa7, retargeted to the Template codex task. The Bead\n"
         "description is the short gct-e8ex task brief (sha256 %(desc)s): the reviewed r6 gct-e8ex brief head and tail,\n"
         "verbatim, with the stop check and a pointer to six closed holders (designs/gct-e8ex-split). The task\n"
         "carries no dependency edge, so `bd show` prints no embedded record.\n"),
    ],
    'prep-r11.py': [
        ("gas-city-template/codex (provider claude-candidate), bound to the candidate worktree; its\n",
         "gascity/operations-candidate-worker (provider claude-candidate), bound to the candidate worktree; its\n"),
        ("r10 (%(task)s, ga-fsfg R4, the eleventh successor): the ga-x7lx prep retargeted to task %(task)s and its\n",
         "r10 (ga-3oa7, ga-fsfg R4, the eleventh successor): the ga-x7lx prep retargeted to task ga-3oa7 and its\n"),
    ],
    'worktree-task-r1.py': [
        ("%(task)s (ga-cw-first-window PLAN r12 step 4, gct-lagl HANDOFF 2.10). The coordinator creates the routed\n"
         "worktree after the previous candidate session drained:\n"
         "- the candidate root must exist, be a real directory owned by the operator, and be empty;\n"
         "- the Operations repository's main head must be BASE and the new branch must not exist;\n",
         "%(task)s (the first Template codex window; from ga-cw-first-window PLAN r12 step 4). The coordinator creates the\n"
         "routed worktree of the Template repository:\n"
         "- the worktree path must not exist (the Template worktree root holds other worktrees);\n"
         "- the Template origin/main must be BASE (the local main ref has diverged and is not used) and the new branch\n"
         "  must not exist;\n"),
        ("- afterwards the root holds exactly the worktree, the reviewed candidate_git.verify_linked accepts its gitfile,\n"
         "  admin directory, back-pointer and commondir, HEAD is BASE, no driver or gitlink applies, and the status with\n"
         "  ignored files is empty.\n",
         "- afterwards the worktree exists, the reviewed candidate_git.verify_linked accepts its gitfile, admin\n"
         "  directory, back-pointer and commondir, HEAD is BASE, no gitlink applies, the drivers are exactly the pinned\n"
         "  git-lfs set, and the status with ignored files is empty.\n"),
    ],
    'operator/PREP.sh': [
        ("# %(task)s window prep r10: the isolation overlay and its receipt image.",
         "# %(task)s window prep r11: the isolation overlay and its receipt image."),
        ("# Operations candidate (%(task)s), with\n", "# Template codex agent (%(task)s), with\n"),
    ],
    'window-base-r11.py': [
        ("candidate task %(task)s (ga-fsfg R4), admitted\n", "Template codex task %(task)s (gct-e8ex), admitted\n"),
    ],
    'common-snapshot-r1.py': [
        ('"""Read-only proof that the candidate left the Operations common git directory unchanged (s1 review A 7).',
         '"""Read-only proof that the worker left the Template common git directory unchanged (s1 review A 7).'),
        ("(info/exclude as the ga-sh3w EXCLUDE job left it)", "(info/exclude included)"),
    ],
}


def fixup(name, text):
    for old, new in FIXUPS.get(name, ()):
        values = dict(task=TASK, desc=DESCRIPTION_SHA)
        text = sub(text, old % values, new % values)
    return text


EDITS = {'route-task-r5.py': route, 'bind-task-r5.py': bind, 'worktree-task-r1.py': worktree, 'prep-r11.py': prep,
         'suspension-lineage.py': lineage, 'hold-r11.py': hold, 'audit-queue-r3.py': audit,
         'common-snapshot-r1.py': common, 'window-base-r11.py': window_base,
         'observe-integrity-r11.py': observer_integrity}


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = rename(raw.decode())
        if name in EDITS:
            text = EDITS[name](text)
        text = fixup(name, text)
        out[name] = text.encode()
    history = {name: {hashlib.sha256(raw).hexdigest()} for name, raw in files.items()}
    while True:
        for name, raw in out.items():
            history.setdefault(name, set()).add(hashlib.sha256(raw).hexdigest())
        renamed = {old: hashlib.sha256(out[n]).hexdigest() for n in out for old in history[n]
                   if old != hashlib.sha256(out[n]).hexdigest()}
        changed = False
        for name, raw in out.items():
            if not name.endswith(('.py', '.sh')):
                continue
            text = raw.decode()
            new = DIGEST.sub(lambda m: renamed.get(m.group(0), m.group(0)), text)
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
