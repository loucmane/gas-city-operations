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
                     ('/var/tmp/ga-3oa7-window', '/var/tmp/' + TASK + '-window'),
                     ('ga-3oa7-window', PACKAGE)):
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
    "    assert shown_bead.get('id')=='%(task)s','task id'\n"
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


GITATTRIBUTES_BYTES = (b'# Patch files preserve diff syntax; embedded context markers otherwise look\n'
                       b'# like whitespace errors to an outer `git diff --check`.\n'
                       b'patches/*.patch -whitespace\n')
# s1 r2 (A should_fix 3, B should_fix 1): the pinned drivers, the absent attributes file and the .gitattributes
# bytes are checked BEFORE `git worktree add`, through the common repository, so a checkout-time filter is
# refused rather than detected afterwards. The post-add DRIVERS_CHECK stays.
PRE_ADD = (
    "    # Template variant, s1 r2: before the checkout, the common config carries exactly the pinned git-lfs\n"
    "    # drivers, no repository attributes file exists, and the one tracked .gitattributes at BASE is the\n"
    "    # reviewed blob, whose bytes select no filter, diff or merge driver.\n"
    "    drivers=git('config','--includes','--get-regexp',r'^(filter|diff|merge)\\.',expected=(0,1)).stdout\n"
    "    assert hashlib.sha256(drivers).hexdigest()=='" + LFS_DRIVERS_SHA + "','Template driver config is not the git-lfs set'\n"
    "    assert not os.path.lexists(OPS/'.git'/'info'/'attributes'),'repository attributes file present'\n"
    "    assert git('rev-parse','--verify',BASE+':.gitattributes').stdout.decode().strip()=='" + GITATTRIBUTES_BLOB + "'\n"
    "    assert git('cat-file','blob','" + GITATTRIBUTES_BLOB + "').stdout==" + repr(GITATTRIBUTES_BYTES) +
    ",'.gitattributes content'\n")


def worktree(text):
    text = sub(text, "    git('worktree','add','-b',BRANCH,str(WORK),BASE)\n",
               PRE_ADD + "    git('worktree','add','-b',BRANCH,str(WORK),BASE)\n")
    text = sub(text, "It writes nothing else and refuses any existing output root.\n",
               "It writes nothing else (besides the new branch's reflog, which `worktree add -b` creates) and refuses any\n"
               "existing output root. s1 r2: the pinned drivers, the absent attributes file and the .gitattributes bytes\n"
               "are checked before the add, so no checkout-time filter can run.\n")
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


WATCH_GIT = (
    "    # The hardened form (gct-lagl HANDOFF 4.2): the candidate worktree can select no driver or hook.\n"
    "    git = list(w.HARDENED)\n"
    "    head = run('git-head', git + ['rev-parse', 'HEAD'])['stdout'].strip()\n"
    "    branch = run('git-branch', git + ['branch', '--show-current'])['stdout'].strip()\n"
    "    # -z: NUL-separated, never quoted, so every untracked path is exact.\n"
    "    status = run('git-status', git + ['status', '--porcelain=v1', '-z', '--untracked-files=all'])['stdout']\n"
    "    # Plumbing only: diff-files and diff-index never refresh or lock the worker's index, so a WATCH can\n"
    "    # never collide with the worker's own staging or signing.\n"
    "    run('git-diff', git + ['diff-files', '--patch', '--binary', '--no-textconv', '--no-ext-diff', '--exit-code'],\n"
    "        expected=(0, 1))\n"
    "    run('git-staged', git + ['diff-index', '--cached', '--patch', '--binary', '--no-textconv', '--no-ext-diff',\n"
    "                             '--exit-code', 'HEAD'], expected=(0, 1))\n"
    "    staged = run('git-staged-names', git + ['diff-index', '--cached', '--name-status', 'HEAD'])['stdout']\n")


def watch(text):
    """s1 r2 (B must_fix 2, A should_fix 2): the codex sandbox can write the Template .git (config, attributes, the
    admin directory) and the whole worktree root, so a coordinator git call against the worktree while the worker
    is live could run a driver or command the worker chose. WATCH runs no git; the worker's git state is read
    after containment by the reviewed post-window intake check."""
    text = sub(text, WATCH_GIT,
               "    # Template variant (s1 r2): no git runs against the worktree while the codex worker is live. Its\n"
               "    # sandbox can write the Template .git and the worktree root, so any coordinator git call here could\n"
               "    # run a driver or command it chose. The git state is read after containment by the reviewed\n"
               "    # post-window intake check; the task notes (READY FOR SIGNING / ESCALATED / STOPPED) are the signal.\n"
               "    head = branch = None\n"
               "    status = staged = ''\n")
    return sub(text, "- worktree HEAD, branch, full status, unstaged and staged diffs, and the staged patch;\n",
               "- no git state: the Template variant runs no git while the worker is live (s1 r2), so HEAD, branch,\n"
               "  status and diffs are recorded as empty and read after containment instead;\n")


COMMON_OBSERVE_OLD = (
    "def observe():\n"
    "    out={'config':entry(COMMON/'config')}\n"
    "    for sub in ('hooks','info'):\n"
    "        for directory,dirs,files in os.walk(COMMON/sub):\n"
    "            dirs.sort()\n"
    "            for name in sorted(files):\n"
    "                path=Path(directory)/name\n"
    "                out[str(path.relative_to(COMMON))]=entry(path)\n")
COMMON_OBSERVE_NEW = (
    "# s1 r2 (B must_fix 3, A should_fix 1): the codex sandbox can write this whole directory, so the compared set\n"
    "# is every file and link under it (config, hooks/, info/, refs/, packed-refs, logs/, objects/info/ with its\n"
    "# alternates, every worktrees/<name>/ admin file, HEAD, shallow, modules/, lfs/) except the object store, which\n"
    "# `git add` legitimately extends, and this worktree's own index, which `git add` rewrites.\n"
    "OBJECTS=Path('objects')\n"
    "MUTABLE={'worktrees/%s/index'}\n"
    "\n"
    "def observe():\n"
    "    out={}\n"
    "    for directory,dirs,files in os.walk(COMMON):\n"
    "        dirs.sort()\n"
    "        here=Path(directory).relative_to(COMMON)\n"
    "        # os.walk lists a symlinked directory in dirs and never descends it: record it as a link.\n"
    "        for name in sorted(files)+[d for d in dirs if os.path.islink(Path(directory)/d)]:\n"
    "            rel=here/name\n"
    "            if (rel.parts[:1]==OBJECTS.parts and rel.parts[:2]!=('objects','info')) or str(rel) in MUTABLE:\n"
    "                continue\n"
    "            out[str(rel)]=entry(Path(directory)/name)\n" % TASK)


def common(text):
    text = sub(text, COMMON_OBSERVE_OLD, COMMON_OBSERVE_NEW)
    text = sub(text, "config, every file under hooks/ and info/ (info/exclude as the ga-sh3w EXCLUDE job left it), and the candidate branch, which must\n"
                     "still point at BASE (the candidate delivers uncommitted work). Coordinator refs (main, the ga-e0t1 branch,\n"
                     "remote-tracking refs) legitimately move after TERMINAL and are not compared. It writes only its own output file.\n",
               "every file and link under the Template .git except the object store (objects/, but objects/info/ is\n"
               "compared) and this worktree's own index, plus the candidate branch, which must still point at BASE (the\n"
               "worker delivers staged, uncommitted work). No coordinator git runs in the Template repository during the\n"
               "window, so every ref is compared. Run `after` immediately after TERMINAL, before any other coordinator\n"
               "git call. It writes only its own output file.\n")
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
    ],
    'operator/BIND.sh': [
        ("contract binding (gc.work_dir, gc.check_path), before the window.",
         "contract binding (gc.work_dir only), before the window."),
    ],
    'route-task-r5.py': [
        ("    # %(task)s: the reviewed pre-route check (ga-6utp preroute.check) is the last step before the sling.\n",
         "    # %(task)s: the Template pre-route, built from the reviewed ga-6utp preroute pieces (preroute.check itself\n"
         "    # requires a root holding only this worktree), is the last step before the sling. pr.survey is given the\n"
         "    # worktree, not the shared Template root, whose other worktrees are not this window's.\n"),
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
         'observe-integrity-r11.py': observer_integrity, 'watch-r11.py': watch}


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
