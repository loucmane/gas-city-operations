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
# s1 r7: the overlay also removes the four wider codex choices (REMOVED_CHOICES); a confined `gc config show` on it
# validates and is identical to the r5 overlay's, so the narrowing is proven by these bytes and Core f3856bd1's
# schema check on opt_ values, not by config show.
# s1 r8: recomputed by the same build_overlay from the M10 city.toml e5b68c40 (replace-mode codex, the same four
# removed choice blocks) and the confined gc config and order list of 2026-09-27.
OVERLAY_NEW = '1dc5c539982656be664b447d6e9ade344c0975cf0625b185e60df2c2ece69b40'
# The provider pins the observers compare: s1 r8, the P11 adoption record's (byte-identical to P10's).
PROVIDER = ('/var/tmp/ga-bebv-p11-adoption-20260927/after.json.provider-pins',
            '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b')
# The split (designs/gct-e8ex-split r10 at 0e4b6708): holder ids in position order; gct-i852 replaced gct-icv2.
SPLIT_COMMIT = '0e4b67080b7816d703f81d9559124b256f22fe1f'
HOLDERS = ('gct-v1nl', 'gct-q6a4', 'gct-t54b', 'gct-2fax', 'gct-ilmv', 'gct-i852')
# s2: the gct-mbg6 PREP outputs replace the ga-3oa7 ones in window-base (empty until PREP has run).
# s2 (2026-09-27): job mbg6-r8-prep passed at 354221e3; /var/tmp/gct-mbg6-prep-20260926-r1. orders.isolated.json
# is byte-identical to ga-3oa7's (b57082cf) and the nudge-on-route script is unchanged (7f49bf8b), so those stay.
PREP_PINS = [
    ('0e583359552b9c765ae0da5cf971397d6cf0e96b03613238721cc797aad64940',   # city.isolated.toml (the overlay)
     '1dc5c539982656be664b447d6e9ade344c0975cf0625b185e60df2c2ece69b40'),
    ('62041d275870f6ea5d04860d9c40821c78313bd802706f22dce6a9660f50369a',   # receipt.final.json (self 815ffa23)
     '7a1e2ed1df4a652fe31fe361d3fcf017e71c32f539d5e2b4a62b1e802ba3f06c'),
    ('2a88522aea8912c454204a99942fea748807604c8a640a3612d130e6c83cb28a',   # the overlay revision
     '480c2dd891073a3a798b2747961e68a94d5717a950ef1e219c11b15acb1efab6'),
    ('a99403becaec1b8255e753828f21cb806fe91642ba5290caa93805e5e567b2da',   # PREP result.json
     '983e77f482732c4545dc3a7d0e4b425f11e8f2d9c386d0f570670812e53b9a2f'),
]


# s1 r7: the four codex choice blocks (TOML bytes of the pinned city.toml 4f7e170f) that grant more than the window's
# choice: the attended approval policy, the Blog worktrees and the Template and HPFetcher .git roots.
REMOVED_CHOICES = (
    b'[[providers.codex.options_schema.choices]]\nvalue = "attended"\nlabel = "Attended approvals"\nflag_args = ["--ask-for-approval", "on-request"]\n\n',
    b'[[providers.codex.options_schema.choices]]\nvalue = "classified-vault-and-blog-worktrees"\nlabel = "Classified GasCity vault and Blog worktrees"\nflag_args = ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.writable_roots=[\\"/home/loucmane/vaults/main/GasCity\\",\\"/home/loucmane/dev/blog-worktrees\\"]"]\n\n',
    b'[[providers.codex.options_schema.choices]]\nvalue = "classified-vault-template-worktrees-and-git-metadata"\nlabel = "Classified vault, template worktrees, and template Git metadata"\nflag_args = ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.writable_roots=[\\"/home/loucmane/vaults/main/GasCity\\",\\"/home/loucmane/gas-city-template-worktrees\\",\\"/home/loucmane/gas-city-template/.git\\"]"]\n\n',
    b'[[providers.codex.options_schema.choices]]\nvalue = "classified-vault-hpfetcher-worktrees-and-git-metadata"\nlabel = "Classified vault, HPFetcher worktrees, and HPFetcher Git metadata"\nflag_args = ["--sandbox", "workspace-write", "-c", \'sandbox_workspace_write.writable_roots=["/home/loucmane/vaults/main/GasCity","/home/loucmane/dev/hpfetcher-worktrees","/home/loucmane/dev/hpfetcher/.git"]\']\n\n',
)
REMOVED_CHOICES_SRC = repr(REMOVED_CHOICES)


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
    # s1 r7 (r6 review B must_fix 1): Core f3856bd1 applies an opt_<key> choice from any in-progress Bead assigned
    # to the session and skips values not in the resolved provider schema (session_reconciler.go
    # workBeadOptionOverrides). The overlay therefore removes every codex choice wider than the window's: the
    # Template and HPFetcher .git choices, the Blog worktrees choice and the attended approval policy. Each block
    # must exist exactly once in the pinned city.toml.
    text = sub(text, "    candidate = city.replace(b'max_active_sessions = 16\\n', b'max_active_sessions = 1\\n', 1) + ''.join(parts).encode()\n",
               "    narrowed = city.replace(b'max_active_sessions = 16\\n', b'max_active_sessions = 1\\n', 1)\n"
               "    for block in REMOVED_CHOICES:\n"
               "        assert narrowed.count(block) == 1, ('codex choice block', block[:120])\n"
               "        narrowed = narrowed.replace(block, b'')\n"
               "    candidate = narrowed + ''.join(parts).encode()\n")
    text = sub(text, "OVERLAY_SHA = '%s'" % OVERLAY_NEW,
               "# s1 r7: the codex option choices the overlay removes from providers.codex.options_schema, byte-exact.\n"
               "REMOVED_CHOICES = " + REMOVED_CHOICES_SRC + "\n"
               "OVERLAY_SHA = '%s'" % OVERLAY_NEW)
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
# s1 r8: the ga-bebv deployment (sequence 16, M10, P11) moved the host epoch, gc, the city.toml, the platform
# pair and the worker receipt after the ga-3oa7 TERMINAL. As ga-sh3w did after P10, the first window on the new
# baseline is admitted against the adoption's own after-snapshot: the P11 adoption after.json (two readback
# reviews, 2026-09-27), taken by the same observer on the sequence 16 epoch.
ACCEPTED_P11 = ('/var/tmp/ga-bebv-p11-adoption-20260927/after.json',
                '3ea63446ab88f4c2e262fcce2770d37cf320f7b4dd2de233a0a7f9ba562d6a3c')
# s4: the s2 window was restored at s3 (TERMINAL PASS 06:07Z, zero drift); the rerun is admitted against that
# TERMINAL observed-after record, as each successor after ga-x7lx was.
ACCEPTED_NEW = ('/var/tmp/gct-mbg6-terminal-20260926-r1/observed-after.json',
                '959767c4dd0648bf882ac39b1ddb19330bfe8e6f94f69003a97f1908d888684a')
# The pack-cache .git mtime and ctime in the P11 after-snapshot; s2 pins the value after the last note.
CACHE_OLD = (1790419645618740930, 1790431776352453342)
CACHE_PREV_NS = 1790470648629115669  # s4: the cache value in the gct-mbg6 TERMINAL record
# s2 pinned 1790470648629115669 (approved 2026-09-27). s4 is a new window: the operator approved its one-field
# disposition again on 2026-09-27 (about 08:45 CEST); the value is the live one after the last note (06:43:45Z).
CACHE_PINNED_NS = 1790491430741191162


def window_base(text):
    """Applied after the rename, so the P11 accepted path is inserted literally."""
    text = sub(text, "against the ga-x7lx TERMINAL record (eleventh successor).",
               "against the gct-mbg6 s3 TERMINAL record (twelfth successor s4, the first Template codex window,\n"
               "on the ga-bebv baseline: gc 207a78e2, M10 metadata, receipt 06a3f58a).")
    text = sub(text, "# The accepted image is the ga-x7lx TERMINAL observed-after record: this same snapshot() after RESTORE on\n"
                     "# this epoch (TERMINAL PASS 2026-09-26 13:11Z, full native integrity).",
               "# The accepted image is the gct-mbg6 s3 TERMINAL observed-after record: this same snapshot() after RESTORE on\n"
               "# this epoch (TERMINAL PASS 2026-09-27 06:07Z, full native integrity, window never resumed).")
    text = sub(text, "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_OLD,
               "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_NEW)
    for old, new in PREP_PINS:
        text = sub(text, "'%s'" % old, "'%s'" % new)
    text = sub(text, "CACHE_PREV_NS = %d\nCACHE_PINNED_NS = %d\n" % CACHE_OLD,
               "CACHE_PREV_NS = %d\nCACHE_PINNED_NS = %s\n" % (CACHE_PREV_NS, CACHE_PINNED_NS))
    text = sub(text, "    # ga-x7lx TERMINAL record, the coordinator recorded the ga-x7lx outcome, the R3 intake and merge and the R4 brief on ga-e0t1 through\n",
               "    # gct-mbg6 TERMINAL record, the coordinator recorded the window outcome and the stale-Bead closures on ga-e0t1 through\n")
    return sub(text, "        # The ga-x7lx TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n",
               "        # The gct-mbg6 TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n")


# s1 r8: every other binding the ga-bebv deployment moved, per file, each asserted with its exact count.
PROCESS_RECORD = ('/home/loucmane/.local/share/gas-city-staging/ga-bebv-process-record-20260927/process-record.json',
                  'df765fd0e357925bab51891c72019018bb43b65fcd6e97addf0582c9bdf5e5d7')
GC_OLD, GC_NEW = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b', '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f'
REBASE = {
    'window-base-r11.py': [
        ("post-P10 baseline (M9 metadata, receipt c833908f, gc fce2e9a0) and the Template codex task",
         "post-P11 baseline (M10 metadata, receipt 06a3f58a, gc 207a78e2) and the Template codex task", 1),
        ("WITNESS = Path('/var/tmp/ga-e0t1.18-p10-adoption-20260926/typed-support.json')\n"
         "WITNESS_SHA = '53dd45539fad45816d62ecd9d4ee26bba380f5fedc1c4d363435471a9c201d30'\n",
         "WITNESS = Path('/var/tmp/ga-bebv-p11-adoption-20260927/typed-support.json')\n"
         "WITNESS_SHA = 'a2016797ca0c91dadaa770b9496dc93c919ebffd4f22290da0309087f0c9c675'\n", 1),
        ("CITY_SHA = ('4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591',",
         "CITY_SHA = ('e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077',", 1),
        ("RECEIPT_SHA = ('c833908fe89ab180e57ef7164d687f01ae2052f8667360f04b73c5423902f0a4',",
         "RECEIPT_SHA = ('06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5',", 1),
        ("REVISION = ('83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add',",
         "REVISION = ('03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712',", 1),
        ("INPUT = (Path('/var/tmp/ga-e0t1.18-p10-input-20260926/receipt.input.draft.json'), PREP/'receipt.input.json')\n"
         "INPUT_SHA = ('c6674ba5f494faeb8179b6e6d49a904e8fe5761a7bfa491ffb3c9d97c9b5ffe7',",
         "INPUT = (Path('/var/tmp/ga-bebv-p11-input-20260927/receipt.input.draft.json'), PREP/'receipt.input.json')\n"
         "INPUT_SHA = ('68fb232e0c940140db9f5a41bf62652eca19115240a18a1b118698f5884611c1',", 1),
        ("# directories) are not part of the compared image; the provider pins stay the P10 adoption record's.\n",
         "# directories) are not part of the compared image; the provider pins are the P11 adoption record's\n"
         "# (byte-identical to P10's).\n", 1),
        ("PROVIDER = Path('/var/tmp/ga-e0t1.18-p10-adoption-20260926/after.json.provider-pins')",
         "PROVIDER = Path('/var/tmp/ga-bebv-p11-adoption-20260927/after.json.provider-pins')", 1),
        ("    # The sequence 15 supervisor epoch; the broker and the signer are unchanged since S2.\n"
         "    for name, pid, start in [('core','995924','163987392096'),",
         "    # The sequence 16 supervisor epoch (ga-bebv S2); the broker and the signer are unchanged.\n"
         "    for name, pid, start in [('core','2800348','229642910742'),", 1),
        ("value['controller']['pid']==995924", "value['controller']['pid']==2800348", 1),
        ("newest['controller_pid']==995924", "newest['controller_pid']==2800348", 1),
        (GC_OLD, GC_NEW, 1),
        # s2 wording (r8 reviews A and B should_fix): this window's disposition was approved on 2026-09-27.
        ("# gct-mbg6 disposition, operator-approved 2026-09-26, for independent review: after the",
         "# gct-mbg6 disposition, operator-approved 2026-09-27, for independent review: after the", 1),
    ],
    'window-r11.py': [("newest['controller_pid']==995924", "newest['controller_pid']==2800348", 1),
                      ("INSPECTOR_SHA='9e29e45dd465dd0397525c5a2d8aa929e65a32bffa7a69787842a23c99a55549'",
                       "INSPECTOR_SHA='e1bb4fc9ac4884b4ad96710b05006c1148349781e826976d3bfef868752beac8'", 1)],
    'route-chain-r1.py': [("cycle['controller_pid']==995924", "cycle['controller_pid']==2800348", 1)],
    'route-task-r5.py': [
        ("RECORD=Path('/home/loucmane/.local/share/gas-city-staging/ga-6utp-activation-r12-20260926/records/process-record.json')\n"
         "RECORD_SHA='a6aa4b4c3a33dd08ee46b27c7059201cc529eab1d99eb67af9ab05acc195a278'\n",
         "# s1 r8: the reviewed preroute.py record refresh after the sequence 16 controller restart (pid 2800348).\n"
         "RECORD=Path('%s')\nRECORD_SHA='%s'\n" % PROCESS_RECORD, 1),
    ],
    'prep-r11.py': [
        ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC_NEW, 1),
        ("COMPOSE = Path('/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926/compose')\n"
         "COMPOSE_SHA = '53450168ef90fd8698688d25fb031e96b3295ff54132441cda72c593611f3111'\n"
         "BUILD = Path('/var/tmp/ga-e0t1.18-p10-preflight-diagnostic-20260926')\n"
         "FINALIZE_SHA = 'c6dd9ebbee33bc40579fc9b7f0af7e7a9c69500566870910f5361eb4b0e12824'\n",
         "# s1 r8: the P11 diagnostics, built from Core f45a6262 (ga-bebv-deploy/p11).\n"
         "COMPOSE = Path('/var/tmp/ga-bebv-p11-candidate-compose-diagnostic-20260927/compose')\n"
         "COMPOSE_SHA = '8cb667dc8a65a858c9df2708a5e42ece79f59ce10a1372b817b8e656aa3ae207'\n"
         "BUILD = Path('/var/tmp/ga-bebv-p11-preflight-diagnostic-20260927')\n"
         "FINALIZE_SHA = '85a2cc6b575ff3fd4660e41241031a813f1264486b6d82084f93c7c9fddc96f5'\n", 1),
        ("PRIOR = Path('/var/tmp/ga-e0t1.18-p10-input-20260926/receipt.input.draft.json')\n"
         "PRIOR_SHA = 'c6674ba5f494faeb8179b6e6d49a904e8fe5761a7bfa491ffb3c9d97c9b5ffe7'\n"
         "CITY_SHA = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'\n"
         "RECEIPT_SHA = 'c833908fe89ab180e57ef7164d687f01ae2052f8667360f04b73c5423902f0a4'\n"
         "REVISION = '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add'\n",
         "# s1 r8: the ga-bebv baseline: the P11 input draft, the M10 city.toml, the P11 receipt and its revision.\n"
         "PRIOR = Path('/var/tmp/ga-bebv-p11-input-20260927/receipt.input.draft.json')\n"
         "PRIOR_SHA = '68fb232e0c940140db9f5a41bf62652eca19115240a18a1b118698f5884611c1'\n"
         "CITY_SHA = 'e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077'\n"
         "RECEIPT_SHA = '06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5'\n"
         "REVISION = '03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712'\n", 1),
    ],
}
for _name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
    REBASE[_name] = [
        ("BUILD=Path('/var/tmp/ga-e0t1.18-platform-inspector-m9-20260926')\n",
         "BUILD=Path('/var/tmp/ga-bebv-platform-inspector-m10-20260927')\n", 1),
        ("BINARY_SHA='9e29e45dd465dd0397525c5a2d8aa929e65a32bffa7a69787842a23c99a55549'",
         "BINARY_SHA='e1bb4fc9ac4884b4ad96710b05006c1148349781e826976d3bfef868752beac8'", 1),
        ("w.read(BUILD/'build-result.json','87e12b94b8f60d729826e7d8dd7ce96932e337a9f668ea686517339af0939e3a')",
         "w.read(BUILD/'build-result.json','ab96575ef37b03e514c3c098a292dac8d7183946f5221b091cfa9cdc97a8bc62')", 1),
        ("MANIFEST_SHA='5a29dc596af192e0f314391453d25d6be548695a0defd64bdfc2fa76554e4993'",
         "MANIFEST_SHA='2b902a83577acf71f9dd93a97d43d8478f7c4b291b0992e8ba5a5e44fe66f7f2'", 1),
        ("result['core_commit']=='deefb98b2aed07875df31351d081fbac195cb1cd'\n"
         "        and result['core_tree']=='af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'\n"
         "        and result['entrypoint_sha256']=='1fa212cead41bbdb998ec24146d119b69edb9c5a446f8a9ac1ea9ad50af7b3a5'",
         "result['core_commit']=='f45a626213dc5b8d0b52f097d978cca56e506df0'\n"
         "        and result['core_tree']=='f1011adaf673937fbda1d254a53c8f0eadf17c5c'\n"
         "        and result['entrypoint_sha256']=='1f87b7b86afc322c385aed0dbc22491b511b6704f07bb5e9078f342aff7d0e3a'", 1),
        ("# M9 (manifest file 5a29dc59) pins the candidate wrapper as a second claude provider, keyed by path.",
         "# M9 pinned the candidate wrapper as a second claude provider, keyed by path; M10 (file 2b902a83) keeps it.", 1),
    ]


REBASE['observe-integrity-r11.py'].insert(0, ("post-P10 baseline (M9)", "post-P11 baseline (M10)", 1))
REBASE['observe-integrity-r11.py'].append(("    # (four keys) and the P10 provider pins, through approved_candidate_cache_image only.",
                                          "    # (four keys) and the P11 provider pins, through approved_candidate_cache_image only.", 1))


# s3 (2026-09-27): the s2 window stopped after ROUTE (its post-route queue audit refused on four stale routed
# Beads) with the overlay staged and no worker ever resumed. CONTAIN is then a no-op (no resume event), HOLD
# refuses (nothing is stranded), and CLOSE refused because scheduling was never released: it only knew a
# CONTAIN rig-suspend event or a passing HOLD. CLOSE now also accepts a window that was staged and never took a
# lifecycle step, and then proves with the reviewed lineage (terminal) that the suspension state is still the
# fully suspended baseline, before it runs anything.
REBASE['close-r11.py'] = [
    ("    held = (WINDOW/'suspension-rig-suspend-event.json').exists()\n",
     "    held = (WINDOW/'suspension-rig-suspend-event.json').exists()\n"
     "    # s3: a staged window that never took a lifecycle step never released scheduling (see below).\n"
     "    never_resumed = ((WINDOW/'stage-pass.json').exists() and not list(WINDOW.glob('suspension-*-intent.json'))\n"
     "                     and not list(WINDOW.glob('suspension-*-event.json')))\n"
     "    held = held or never_resumed\n", 1),
    ("    w.require(held, 'scheduling is not held (no CONTAIN rig-suspend event and no passing HOLD)')\n"
     "    w.ROOT = WINDOW\n"
     "    w.active_epoch(o)\n",
     "    w.require(held, 'scheduling is not held (no CONTAIN rig-suspend event, no passing HOLD, and the window resumed)')\n"
     "    w.ROOT = WINDOW\n"
     "    if never_resumed:\n"
     "        # The reviewed lineage with zero transitions: the live suspension state must be the baseline record.\n"
     "        w.verified_lifecycle(terminal=True)\n"
     "    w.active_epoch(o)\n", 1),
]


# s4: every window output root the s2 run consumed moves to -r2. PREP (-r1) and WORKTREE (-r1) are reused: the
# worktree is unchanged and clean, and PREP's read-only outputs describe the same city (restored exactly at s3).
FRESH_ROOTS = ('window-obs', 'window', 'bind', 'route', 'integrity', 'terminal', 'audit-route', 'audit-resume',
               # s4 r2: audit-queue-r3.py names its root through MODE ('audit-%s'), which the literal forms missed.
               'audit-%s')
# Every form must be replaced somewhere in the package (asserted after generation, like sub()'s counts).
FRESH_COUNTS = dict.fromkeys(FRESH_ROOTS, 0)
# s4 r3: the s4 ROUTE refused before its sling (07:01Z) because the reviewed preroute.survey flagged five
# cgroup members that exited mid-scan (hidden-during-scan:entry), and its r2 root now exists. The live window
# (window, bind, integrity roots at -r2) stays; only the route and audit roots, which no live record binds, move
# to -r3 so ROUTE can run once more.
GENERATION = {'route': 'r3', 'audit-route': 'r3', 'audit-resume': 'r3', 'audit-%s': 'r3'}
# preroute.survey's own contract: a member that exits mid-scan "fails closed and the survey is simply rerun".
# ROUTE reruns it at most five times, two seconds apart, saves every attempt, and still requires the last to be
# clean; a process that really holds the worktree is flagged on every attempt.
REBASE.setdefault('route-task-r5.py', []).extend([
    ("import stat\n", "import stat\nimport time\n", 1),
    ("    problems=pr.survey(work,1000,slice_root,record['hidden'])\n",
     "    attempts=[]\n"
     "    for _ in range(5):\n"
     "        problems=pr.survey(work,1000,slice_root,record['hidden'])\n"
     "        attempts.append(problems)\n"
     "        if not problems:\n"
     "            break\n"
     "        time.sleep(2)\n"
     "    w.save('survey-attempts.json',dict(attempts=attempts))\n", 1),
])

# s5: the s4 recovery. CONTAIN-1 (07:47Z) ran `gc suspend --json` cleanly, then its observation refused ('unexpected
# live worker': gc status listed the one worker twice, as the rig agent gas-city-template/codex and as the session row
# codex-ci-sg37g). The lifecycle then recorded failure and refused-after and forbids every further action. The
# reviewed HOLD-1 suspended the gas-city-template rig without writing the window root, and CLOSE-1 closed the session.
# Every consumer of verified_lifecycle (ADMIT, RESTORE, TERMINAL) would refuse the city-suspend intent without an
# event. This admits exactly that stranded state, terminal check only, with every record pinned by digest.
STRANDED_LIFECYCLE = (
    "def verified_lifecycle(terminal=False):\n"
    "    s=module(HERE/'suspension-lineage.py',LINEAGE_SHA)\n"
    "    b,o,owned=load_support()\n"
    "    current=suspension_record(o)\n"
    "    return s.chain(record('suspension-baseline.json'),lifecycle_records(s),current,str(ROOT),terminal)\n")
STRANDED_RECORDS = (
    ('suspension-city-suspend-intent.json', '34a521cf4312b843bf9923ae68e5481f33ef75d349854f256a3e26ccdd2094a7'),
    ('suspension-city-suspend-failure.json', '4838aecf94ee7a160b5d39fd24dfbd7ae100f235c554d1d652ab438057a61a1a'),
    ('suspension-city-suspend-refused-after.json', 'cb8028e59ecde50855c391aae94b138010a95f12c4aba4b5c70cd1b5523ff0af'),
    ('city-suspend-started.json', 'be90d5aa1acd882e41df98a76683526dba0b4eba920f92b53bf483aa54b16369'),
    ('city-suspend-phase.json', '2af0215a6e65b99531669ec30bf9e7033945ce8f2756d96b73b114bd52356be3'),
)
OBSERVED_EXECUTOR = 'f8a163b00f87b199f6678582832cdeb1c0d7ee93740ca309ea3328c0cfd006ff'
STRANDED_HOLD = ('/var/tmp/gct-mbg6-hold-20260927T074745Z/result.json',
                 'd141fae3fb8a1b6d40ecb906e47b644a62c3fbadded933a90cd30af7e8ef71dd')
REBASE.setdefault('window-base-r11.py', []).append((STRANDED_LIFECYCLE,
    "# s5 disposition (gct-mbg6 s4 CONTAIN-1 recovery, 2026-09-27), for independent review. CONTAIN-1's city-suspend\n"
    "# command applied cleanly; its observation then refused because gc status listed the one worker twice (the rig\n"
    "# agent and its session row), so the lifecycle saved failure and refused-after and forbids every further action.\n"
    "# HOLD-1 then suspended the gas-city-template rig without writing this root. A window root holding any failure\n"
    "# or refused-after record is admitted only here: the terminal check, exactly those five records by digest, the\n"
    "# passing HOLD result by digest, the two completed transitions through the reviewed chain, the city-suspend\n"
    "# command and its one-field step, HOLD's one-field rig-suspend step to the live record, and the fully\n"
    "# suspended baseline. Anything else refuses; lifecycle() still forbids every further action.\n"
    "STRANDED_RECORDS = %r\n"
    "STRANDED_HOLD = (Path(%r), %r)\n"
    "\n"
    "def verified_lifecycle(terminal=False):\n"
    "    s=module(HERE/'suspension-lineage.py',LINEAGE_SHA)\n"
    "    b,o,owned=load_support()\n"
    "    current=suspension_record(o)\n"
    "    failures=sorted(p.name for p in ROOT.glob('suspension-*-failure.json'))\n"
    "    refusals=sorted(p.name for p in ROOT.glob('suspension-*-refused-after.json'))\n"
    "    if not failures and not refusals:\n"
    "        return s.chain(record('suspension-baseline.json'),lifecycle_records(s),current,str(ROOT),terminal)\n"
    "    require(terminal,'a stranded lifecycle admits only the terminal check')\n"
    "    require(failures==['suspension-city-suspend-failure.json']\n"
    "        and refusals==['suspension-city-suspend-refused-after.json'],'unreviewed stranded lifecycle')\n"
    "    for name,sha in STRANDED_RECORDS:\n"
    "        read(ROOT/name,sha)\n"
    "    intents={p.name[len('suspension-'):-len('-intent.json')] for p in ROOT.glob('suspension-*-intent.json')}\n"
    "    events={p.name[len('suspension-'):-len('-event.json')] for p in ROOT.glob('suspension-*-event.json')}\n"
    "    require(intents=={'rig-resume','city-resume','city-suspend'} and events=={'rig-resume','city-resume'}\n"
    "        and not list(ROOT.glob('rig-suspend-*')),'stranded lifecycle shape')\n"
    "    records=[]\n"
    "    for action in ('rig-resume','city-resume'):\n"
    "        e=record('suspension-'+action+'-event.json')\n"
    "        intent=record('suspension-'+action+'-intent.json')\n"
    "        require(intent == dict(action=action,before=e['before'],before_sha256=e['before']['pin']['sha256']),\n"
    "            'suspension pre-command binding')\n"
    "        require(e['intent'] == record(action+'-started.json') and e['result'] == record(action+'-phase.json'),\n"
    "            'suspension phase record binding')\n"
    "        records.append(e)\n"
    "    previous=records[-1]['after']\n"
    "    s.chain(record('suspension-baseline.json'),records,previous,str(ROOT))\n"
    "    require(record('suspension-city-suspend-intent.json')==dict(action='city-suspend',before=previous,\n"
    "        before_sha256=previous['pin']['sha256']),'stranded pre-command binding')\n"
    "    s.phase(record('city-suspend-started.json'),record('city-suspend-phase.json'),'city-suspend',str(ROOT))\n"
    "    refused=record('suspension-city-suspend-refused-after.json')\n"
    "    s.step(previous,refused,'city-suspend')\n"
    "    hold=json.loads(read(*STRANDED_HOLD))\n"
    "    require(hold['ok'] is True and hold['window_root_written'] is False and hold['city_suspended'] is True\n"
    "        and hold['gascity_rig_suspended'] is True,'stranded hold result')\n"
    "    s.step(refused,current,'rig-suspend')\n"
    "    z=s.image(current);expected=json.loads(json.dumps(s.image(record('suspension-baseline.json'))))\n"
    "    expected['updated_at']=z['updated_at']\n"
    "    require(z==expected,'suspension baseline not restored')\n"
    "    return current['pin']\n" % ((STRANDED_RECORDS,) + STRANDED_HOLD), 1))


def fresh_roots(text):
    # The accepted image is the r1 TERMINAL record itself; it keeps its path.
    keep = ACCEPTED_NEW[0]
    assert text.count('\0') == 0
    text = text.replace(keep, '\0')
    for root in FRESH_ROOTS:
        old = '/var/tmp/%s-%s-20260926-r1' % (TASK, root)
        FRESH_COUNTS[root] += text.count(old)
        text = text.replace(old, '/var/tmp/%s-%s-20260926-%s' % (TASK, root, GENERATION.get(root, 'r2')))
    text = text.replace('\0', keep)
    # Nothing else of this task may still name a -r1 root except PREP, WORKTREE and the accepted record.
    for found in re.findall(r"/var/tmp/%s-[A-Za-z%%-]+-20260926-r1[^'\" ]*" % TASK, text):
        assert found.startswith(('/var/tmp/%s-prep-' % TASK, '/var/tmp/%s-worktree-' % TASK, keep)), found
    return text


def rebase(name, text):
    for old, new, count in REBASE.get(name, ()):
        text = sub(text, old, new, count)
    return text


def observer_integrity(text):
    for old in ("against the ga-x7lx TERMINAL record (%s window)," % TASK,
                "the accepted image is the ga-x7lx TERMINAL record (window-base).",
                "compared exactly with the ga-x7lx TERMINAL record.",
                "admits the live state against the ga-x7lx TERMINAL record\n"):
        # s4: the admission is the s3 TERMINAL record (window-base ACCEPTED_NEW).
        text = sub(text, old, old.replace('the ga-x7lx TERMINAL record', 'the gct-mbg6 s3 TERMINAL record'))
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
    # s1 r6 (r5 review B must_fix 1): record, unredacted for this one key only, the sandbox write roots each
    # worktree process carries, and every opt_/template_override key on the task and on the template's session
    # Beads, so a relaunch that restored the Template .git write root is visible.
    text = sub(text, "                processes.append(dict(pid=int(proc.name), cwd=cwd, git_optional_locks_zero=locks,\n",
               "                roots = [arg.split(b'=', 1)[1].decode(errors='replace') for arg in argv\n"
               "                         if arg.startswith(b'sandbox_workspace_write.writable_roots=')]\n"
               "                processes.append(dict(pid=int(proc.name), cwd=cwd, git_optional_locks_zero=locks, writable_roots=roots,\n")
    text = sub(text, WATCH_GIT,
               "    # Template variant (s1 r2): no git runs against the worktree while the codex worker is live. Its\n"
               "    # sandbox can write the worktree root, and a relaunch through an opt_ override could restore the\n"
               "    # Template .git, so any coordinator git call here could run a driver or command it chose. The\n"
               "    # task notes (READY FOR SIGNING / ESCALATED / STOPPED) are the signal.\n"
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
    text = sub(text, "    notes = bead.get('notes') or ''\n",
               "    def meta(v):\n"
               "        return v.get('metadata') if isinstance(v.get('metadata'), dict) else {}\n"
               "    def overrides(metadata):\n"
               "        if not isinstance(metadata, dict):\n"
               "            return ['<metadata is not an object>']\n"
               "        return sorted(k for k in metadata if k.startswith('opt_') or k.startswith('template_override'))\n"
               "    override_keys = dict(task=overrides(bead.get('metadata')),\n"
               "                         sessions={str(v.get('id')): overrides(v.get('metadata')) for v in census if isinstance(v, dict)\n"
               "                                   if overrides(v.get('metadata')) and (meta(v).get('template') == TEMPLATE\n"
               "                                   or meta(v).get('gc.work_dir') == str(w.WORK))})\n"
               "    process_roots = sorted({root for p in processes for root in p['writable_roots']})\n"
               "    notes = bead.get('notes') or ''\n")
    text = sub(text, "                  template_git_config_sha256=template_config,\n",
               "                  template_git_config_sha256=template_config, override_keys=override_keys,\n"
               "                  process_writable_roots=process_roots,\n")
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
COMMON_TOOL = r'''"""Read-only proof that nothing changed the Template common git directory during the window (s1 r6).

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

COMMON=Path('%(repo)s/.git')
BASE='%(base)s'
BRANCH='refs/heads/%(branch)s'
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
        text = rebase(name, text)
        text = fresh_roots(text)
        if name == 'window-r11.py':
            # s5: the live integrity record (OBSERVE at s4 r2) names the observer that actually ran; the regenerated
            # observer has a new digest, so RESTORE keeps checking the recorded executor.
            text, n = re.subn(r"^OBSERVER_SHA='[0-9a-f]{64}'$", "OBSERVER_SHA='%s'" % OBSERVED_EXECUTOR, text,
                              flags=re.M)
            assert n == 1
        out[name] = text.encode()
    assert all(FRESH_COUNTS.values()), FRESH_COUNTS
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
