"""Twelfth successor s1: the first Template-rig codex window, derived from the reviewed ga-3oa7 window package.

  python3 -B make_successor.py <output package dir>

Step 4 of the goal needs the Template Claude candidate lane (gct-e8ex) before the Claude<->Codex handover proof
(gct-oak5). The only worker scoped to build it is the Template rig's `codex` agent (gas-city-native prompt;
provider codex, gpt-5.6-sol, max_active_sessions 1), whose Codex quota returned on 2026-09-26. Its brief is split
for readability (designs/gct-e8ex-split r10): task gct-mbg6 (TASK below) plus six closed holders.

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
   not gate it and needs no gc.check_path stamp. There is no info/exclude check: since s1 r5 the codex worker
   cannot write the Template .git and leaves its changes uncommitted; a reviewed Template intake exports them.
5. PREP: the overlay suspends every Template agent except codex (Dir '' and 'gas-city-template'), binds codex to
   the worktree with sessions 0..1 and (s1 r5) the classified-vault-and-template-worktrees choice, which has no
   Template .git write root; the codex singleton warning is already in the baseline.
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
DESCRIPTION_SHA = 'c66bab3c40693762c54c998efa8b5f8bab2813391ba15a9318a00b7b33f2ef0c'
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
               "no info/exclude check: the codex worker cannot write the Template .git (s1 r5) and leaves its changes\n"
               "uncommitted for a reviewed Template intake. No option or template override is written on the Bead (the\n"
               "narrower codex choice comes from the PREP overlay). It runs as its own job BEFORE the window, so no window\n"
               "root may exist yet.\n")
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
    ",'.gitattributes content'\n"
    # s1 r3 (B should_fix 4-5, A should_fix 5-6): no include directive can make the add's child see other
    # config, BASE carries exactly one .gitattributes, no gitlink and no .gitmodules, and all of it is checked
    # before the output root is consumed.
    "    assert git('config','--get-regexp',r'^include',expected=(1,)).returncode==1,'config include directive'\n"
    "    tree=git('ls-tree','-r','-z','--full-tree',BASE).stdout.split(b'\\0')\n"
    "    assert [e for e in tree if e.rsplit(b'\\t',1)[-1].rsplit(b'/',1)[-1]==b'.gitattributes']==[b'100644 blob "
    + GITATTRIBUTES_BLOB + "\\t.gitattributes'],'BASE attributes files'\n"
    "    assert not [e for e in tree if e.startswith(b'160000 ')],'BASE gitlink'\n"
    "    assert not [e for e in tree if e.rsplit(b'\\t',1)[-1]==b'.gitmodules'],'BASE .gitmodules'\n")


def worktree(text):
    text = sub(text, "    ROOT.mkdir(mode=0o700)\n", PRE_ADD + "    ROOT.mkdir(mode=0o700)\n")
    text = sub(text, "It writes nothing else and refuses any existing output root.\n",
               "It writes nothing else (besides the new branch's reflog, which `worktree add -b` creates) and refuses any\n"
               "existing output root. s1 r2/r3: the pinned drivers, no config include directive, the absent attributes\n"
               "file, the .gitattributes bytes, and BASE's single .gitattributes with no gitlink or .gitmodules are\n"
               "checked before the output root is created and before the add, so no checkout-time filter can run and a\n"
               "refusal there consumes nothing.\n")
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
# sessions 0..1), 33 order skips. s1 r5: the codex patch also sets option_defaults worklog_access to the narrower
# classified-vault-and-template-worktrees choice (no Template .git); a confined `gc config show` on this overlay
# reports exactly that OptionDefaults for gas-city-template/codex.
OVERLAY_NEW = '7c3cfc4d5ae185cdc863860c17433cd6d802d916e150fd9b6102cccec7a0cdf8'
# The P10 provider pins the observers compare (unchanged from ga-3oa7).
PROVIDER = ('/var/tmp/ga-e0t1.18-p10-adoption-20260926/after.json.provider-pins',
            '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b')
# The split (designs/gct-e8ex-split r10 at 0e4b6708): holder ids in position order; gct-i852 replaced gct-icv2.
SPLIT_COMMIT = '0e4b67080b7816d703f81d9559124b256f22fe1f'
HOLDERS = ('gct-v1nl', 'gct-q6a4', 'gct-t54b', 'gct-2fax', 'gct-ilmv', 'gct-i852')
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
               "    # Its deployed default includes the Template .git in the sandbox write roots. s1 r5 (operator decision\n"
               "    # 2026-09-26): the overlay gives it the narrower choice instead, so the worker cannot write git state.\n"
               "    # city.toml, which defines both choices, is pinned by digest.\n"
               "    assert agents[target]['OptionDefaults'] == {'worklog_access': 'classified-vault-template-worktrees-and-git-metadata'}\n")
    text = sub(text, "    selected = [i for i, a in enumerate(agents) if a['Dir'] in ('', 'gascity')]\n",
               "    selected = [i for i, a in enumerate(agents) if a['Dir'] in ('', 'gas-city-template')]\n")
    # s1 r5: the codex patch carries option_defaults with the narrower choice, written as a TOML subtable.
    text = sub(text, "            patch.update(work_dir=WORK, min_active_sessions=0, max_active_sessions=1)\n",
               "            patch.update(work_dir=WORK, min_active_sessions=0, max_active_sessions=1,\n"
               "                         option_defaults=dict(worklog_access=NARROW_ACCESS))\n")
    text = sub(text, "        for key, value in patch.items():\n"
                     "            parts.append(key + ' = ' + json.dumps(value) + '\\n')\n",
               "        for key, value in patch.items():\n"
               "            if not isinstance(value, dict):\n"
               "                parts.append(key + ' = ' + json.dumps(value) + '\\n')\n"
               "        for key, value in patch.items():\n"
               "            if isinstance(value, dict):\n"
               "                parts.append('[patches.agent.' + key + ']\\n')\n"
               "                for inner, item in value.items():\n"
               "                    parts.append(inner + ' = ' + json.dumps(item) + '\\n')\n")
    text = sub(text, "            expected['config']['Agents'][i].update(WorkDir=WORK, MinActiveSessions=0, MaxActiveSessions=1)\n",
               "            expected['config']['Agents'][i].update(WorkDir=WORK, MinActiveSessions=0, MaxActiveSessions=1,\n"
               "                                                   OptionDefaults=dict(worklog_access=NARROW_ACCESS))\n")
    text = sub(text, "OVERLAY_SHA = '%s'" % OVERLAY_NEW,
               "OVERLAY_SHA = '%s'\n"
               "# s1 r5: the codex choice without the Template .git (vault and Template worktrees only).\n"
               "NARROW_ACCESS = 'classified-vault-and-template-worktrees'" % OVERLAY_NEW)
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
    # s1 r3 (B should_fix 3): no evidence walk (the codex worker writes no .gc/worker-evidence, and is_dir() would
    # follow a worker-made link); (A should_fix 1) the note markers are surfaced; the Template .git/config digest
    # is recorded as early evidence of a sandbox write into it (read only, never acted on here).
    text = sub(text, "    inventory = dict(untracked=[entry(w, w.WORK/path) for path in untracked], evidence=[])\n"
                     "    evidence = w.WORK/EVIDENCE\n"
                     "    if evidence.is_dir() and not evidence.is_symlink():\n"
                     "        for dirpath, dirnames, filenames in os.walk(evidence):\n"
                     "            dirnames.sort()\n"
                     "            for name in sorted(filenames):\n"
                     "                inventory['evidence'].append(entry(w, Path(dirpath)/name))\n",
               "    inventory = dict(untracked=[], evidence=[])\n")
    text = sub(text, "    result = dict(ok=True, mutation=False, head=head, branch=branch,\n",
               "    notes = bead.get('notes') or ''\n"
               "    markers = [line[:300] for line in notes.splitlines()\n"
               "               if 'READY FOR SIGNING:' in line or 'ESCALATED:' in line or 'STOPPED:' in line][-5:]\n"
               # s1 r4 (r3 review A must_fix 1): a worker-planted FIFO must not block the open, and only a plain,
               # single-link operator file of at most 1 MiB is read, in full.
               "    try:\n"
               "        fd = os.open('" + TEMPLATE_REPO + "/.git/config',\n"
               "                     os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC | os.O_NONBLOCK)\n"
               "        try:\n"
               "            s = os.fstat(fd)\n"
               "            if not (stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1 and s.st_size <= 1 << 20):\n"
               "                template_config = 'not a plain file: mode %o nlink %d size %d' % (s.st_mode, s.st_nlink, s.st_size)\n"
               "            else:\n"
               "                data = b''\n"
               "                while len(data) <= 1 << 20 and (chunk := os.read(fd, 65536)):\n"
               "                    data += chunk\n"
               "                template_config = hashlib.sha256(data).hexdigest() if len(data) == s.st_size else 'size changed'\n"
               "        finally:\n"
               "            os.close(fd)\n"
               "    except OSError as exc:\n"
               "        template_config = 'unreadable: %s' % exc.__class__.__name__\n"
               "    result = dict(ok=True, mutation=False, head=head, branch=branch, note_markers=markers,\n"
               "                  template_git_config_sha256=template_config,\n")
    # s1 r4 (r3 review B should_fix 7): the docstring matches the Template variant.
    text = sub(text, "Runs as a job of the host job runner (operator/WATCH.sh), in the supervisor namespaces, so its git,\n"
                     "process and tmux reads see the real host rather than a sandbox view.",
               "Runs as a job of the host job runner (operator/WATCH.sh), in the supervisor namespaces, so its process\n"
               "and tmux reads see the real host rather than a sandbox view.")
    text = sub(text, "- an inventory of every untracked path and every evidence file (kind, mode, owner, size, SHA256,\n"
                     "  link target);\n",
               "- an empty inventory (the Template variant walks no worktree path), the task note markers and the\n"
               "  Template .git/config digest (a non-blocking, bounded read of a plain file only);\n")
    return sub(text, "- worktree HEAD, branch, full status, unstaged and staged diffs, and the staged patch;\n",
               "- no git state: the Template variant runs no git while the worker is live (s1 r2), so HEAD, branch,\n"
               "  status and diffs are recorded as empty and read after containment instead;\n")


# s1 r3 (reviews of 709fcb33: A must_fix 1, B must_fix 1-2, B should_fix 1-3): the Template common-snapshot
# tool is written whole. It runs no git, compares every entry outside objects/ exactly, keeps every existing
# object entry and allows only new loose objects that hash to their own name, records directories, raises on
# any walk error and bounds every read. The ga-3oa7 tool is asserted as the source it replaces.
COMMON_TOOL = r'''"""Read-only proof that the worker left the Template common git directory unchanged (s1 r3).

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
- the .git directory itself is recorded, with every entry's owner and group; accepted additions must belong to
  the operator's user and group and not be world-writable; a loose object with trailing bytes after its zlib
  stream refuses.
Since s1 r5 the codex worker has no write root in this .git at all, so this tool is defence in depth. It runs
after CLOSE and TERMINAL.
- `before` refuses a baseline carrying a hook other than git's samples and the four pinned git-lfs hooks,
  info/grafts, shallow, refs/replace/ (loose or in packed-refs) or alternates.
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

COMMON=Path('%(repo)s/.git')
BASE='%(base)s'
BRANCH='refs/heads/%(branch)s'
MUTABLE={'worktrees/%(task)s/index'}
LOOSE_DIR=re.compile(r'objects/[0-9a-f]{2}')
LOOSE=re.compile(r'objects/[0-9a-f]{2}/[0-9a-f]{38}')
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
        if v['uid']!=1000 or v['gid']!=1000 or v['mode']&0o002:
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
    # s1 r5 (r4 reviews A should_fix 2, B should_fix 1): a replace ref may also sit in packed-refs.
    packed=COMMON/'packed-refs'
    if 'packed-refs' in value['control']:
        for line in packed.read_text().splitlines():
            parts=line.split(' ')
            if len(parts)==2 and parts[1].startswith('refs/replace/'):problems.append('packed-refs: '+parts[1])
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
'''


def common(text):
    for needle in ("COMMON=Path('/home/loucmane/gas-city-ops/.git')", 'def observe():', 'def main(argv):'):
        assert text.count(needle) == 1, needle
    return COMMON_TOOL % dict(repo=TEMPLATE_REPO, base=BASE, branch=BRANCH, task=TASK)


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
