"""Ninth successor s1: derive the first Operations candidate window (ga-sh3w, ga-fsfg R3) from the reviewed
ga-qcwl window package.

  python3 -B make_successor.py <output package dir>

The accepted plan is ga-cw-first-window PLAN r12 (2067a406): the window is generated from the reviewed
window stack with the target, Bead, worktree root and pins changed, and it routes ga-sh3w to
gascity/operations-candidate-worker. Its prerequisites are live and recorded on ga-e0t1:
- the ga-6utp r12 lane activation (agent.toml suspended, provider claude-candidate);
- M9, pinning the candidate wrapper (manifest file 5a29dc59);
- P10, the typed candidate receipt profile (receipt c833908f, revision 83c41af6);
- the clean vault inventory (ae607077).

1. Every source is read from the ga-qcwl s2 commit object (20e9ba1e), never from a working tree.
2. Dropped:
   - README.md, the tests and the generator, which this package replaces;
   - the source and signing releases (release-r11.py and operator/SOURCE-RELEASE-*, SIGNING-RELEASE-*).
     A candidate delivers uncommitted and never signs; INTAKE (the reviewed ga-6utp intake.py) takes its
     place after TERMINAL.
3. Identity:
   - ga-qcwl becomes ga-sh3w;
   - the target gascity/gc.implementation-worker becomes gascity/operations-candidate-worker, and the
     provider claude-signing becomes claude-candidate;
   - the worktree is /home/loucmane/gas-city-ops-candidate-worktrees/ga-sh3w, a linked worktree of the
     Operations repository, at the Operations main head BASE on branch codex/ga-sh3w-delivery-class;
   - roots and staging move to ga-sh3w with the 20260926 date.
4. Host epoch after sequence 15: the supervisor and controller are PID 995924 (start 163987392096); the
   broker (2940285) and the signer (2310) are unchanged. The Core image is gc fce2e9a0 (Core deefb98b).
5. Accepted image: the P10 adoption snapshot after.json (aaeb7d8f) and its provider pins (82a4a70c), with
   two readback reviews. The coordinator-cache disposition admits exactly the pack-cache repository's .git
   mtime and ctime, from the P10 value to the value pinned at s2 (see window_base()).
6. Receipt staging: the P10 witness (53dd4553), the P10 input draft (c6674ba5), receipt c833908f and
   revision 83c41af6 are the baseline side. The isolated side is re-pinned by s2 from a fresh PREP run.
7. PREP targets the candidate: the overlay unsuspends only gascity/operations-candidate-worker (its
   agent.toml keeps suspended = true; a city.toml patch overrides it for the window). It uses the P10
   diagnostics: the candidate composition (53450168) and the N-profile preflight's finalize (c6dd9ebb).
   Its expected configuration adds no singleton warning, because the candidate's max_active_sessions = 1
   already produces it.
8. Integrity: the observers use the M9 platform inspector (9e29e45d, record 87e12b94, entrypoint 1fa212ce)
   pinned to the M9 manifest file 5a29dc59.
9. Every coordinator git read of the candidate worktree uses the hardened form of gct-lagl HANDOFF 4.2: no
   system or global config, an explicit admin git-dir and work-tree, hooks and fsmonitor off, and no
   textconv or external diff.
10. New scripts: worktree-task-r1.py (the WORKTREE job) creates the candidate worktree; bind-task-r4.py
    binds gc.work_dir and gc.check_path only (the description already is the reviewed R3 brief); the
    ROUTE job runs the reviewed preroute.check immediately before the sling.
11. Digest propagation to a fixed point.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = '20e9ba1e'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-qcwl-window/'
HERE = Path(__file__).resolve().parent
DROP = {'README.md', 'test_successor.py', 'release-r11.py', 'bind-task-r3.py', 'operator/BIND.sh',
        'operator/SOURCE-RELEASE-1.sh', 'operator/SOURCE-RELEASE-2.sh', 'operator/SOURCE-RELEASE-3.sh',
        'operator/SIGNING-RELEASE-1.sh', 'operator/SIGNING-RELEASE-2.sh', 'operator/SIGNING-RELEASE-3.sh',
        'worker-brief.md'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

OPS = '/home/loucmane/gas-city-ops'
CANDIDATE_ROOT = '/home/loucmane/gas-city-ops-candidate-worktrees'
WORK = CANDIDATE_ROOT + '/ga-sh3w'
ADMIN = OPS + '/.git/worktrees/ga-sh3w'
BRANCH = 'codex/ga-sh3w-delivery-class'
# The Operations main head the worktree is created at (canonical seat, includes R1 and R2).
BASE_NEW = '040139d8738a025cbb5afcc8170b700292c5016e'
TARGET_OLD, TARGET_NEW = 'gascity/gc.implementation-worker', 'gascity/operations-candidate-worker'
DESCRIPTION_SHA = '5cbf64f179cca878e2ecfc2898c44a6b465ffa84cfaae558b2fcb0377b65c942'
CHECK_PATH = ('/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f'
              '/gascity/assets/scripts/checks/build-artifact-valid.sh')

IDENTITY = [
    ('/home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins', WORK),
    ('codex/ga-qcwl-provider-pins', BRANCH),
    ('/designs/ga-qcwl-window', '/designs/ga-sh3w-window'),
    ('gas-city-staging/ga-qcwl-window', 'gas-city-staging/ga-sh3w-window'),
    (TARGET_OLD, TARGET_NEW),
    ('ga-qcwl', 'ga-sh3w'),
]
# Every output root, including the %s-formatted audit roots (s1 review B must_fix 1), moves to one fresh date.
ROOT_DATE = re.compile(r"(/var/tmp/ga-sh3w-[a-z0-9%-]+?)-202609\d\d-r\d")

GC_OLD, GC_NEW = ('b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489',
                  'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b')
PID_OLD, PID_NEW = '2940569', '995924'
START_OLD, START_NEW = '123479699122', '163987392096'
BASE_OLD = 'b6843d3f539eeebaf9d9c12e7d095d25cdee585d'
M6_FILE, M9_FILE = ('7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb',
                    '5a29dc596af192e0f314391453d25d6be548695a0defd64bdfc2fa76554e4993')
RECEIPT_OLD, RECEIPT_NEW = ('7cf59ab9e5a43fd7bca97028e7faaa2b2f9bfb927a663b4588c66e846e4e425d',
                            'c833908fe89ab180e57ef7164d687f01ae2052f8667360f04b73c5423902f0a4')
REVISION_OLD, REVISION_NEW = ('2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2',
                              '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add')
INPUT_OLD = ('/var/tmp/ga-e0t1.15-p7-input-20260925/receipt.input.draft.json',
             'c047b4d909095406d359808fecca6a417905435d6c4a3c9a270d5d0b941cd9bb')
INPUT_NEW = ('/var/tmp/ga-e0t1.18-p10-input-20260926/receipt.input.draft.json',
             'c6674ba5f494faeb8179b6e6d49a904e8fe5761a7bfa491ffb3c9d97c9b5ffe7')
WITNESS_OLD = ('/var/tmp/ga-e0t1.15-p7-adoption-20260925/typed-support.json',
               'afe4969df9076ffe139af41ba4626ed374a3c0e4c224efd9762e02036066a71f')
WITNESS_NEW = ('/var/tmp/ga-e0t1.18-p10-adoption-20260926/typed-support.json',
               '53dd45539fad45816d62ecd9d4ee26bba380f5fedc1c4d363435471a9c201d30')
ACCEPTED_OLD = ('/var/tmp/ga-e0t1.15-p7-adoption-20260925/after.json',
                '7e008d9be0abd067270cf43fc1236cab7fab543a7339486f05422bb62002c56d')
ACCEPTED_NEW = ('/var/tmp/ga-e0t1.18-p10-adoption-20260926/after.json',
                'aaeb7d8f5277102bc020e61aeebba5a8d38f74de500148ee3fb1a7b79c02dd23')
INSPECTOR_OLD = ('/var/tmp/ga-e0t1.15-platform-inspector-20260925',
                 '334cc3c912858d84582cf980cf7f270ebb6e5250ac3a62dbdf4e720dc0a2564f',
                 '145a48417718adf62cf607e74424147884b6247f44ff7f33dfa8971767ec1dc4',
                 '585e0d376d90a26cab57d6e676d4aa3567df53b4c8b10816e8fac8071901a7f7')
INSPECTOR_NEW = ('/var/tmp/ga-e0t1.18-platform-inspector-m9-20260926',
                 '9e29e45dd465dd0397525c5a2d8aa929e65a32bffa7a69787842a23c99a55549',
                 '87e12b94b8f60d729826e7d8dd7ce96932e337a9f668ea686517339af0939e3a',
                 '1fa212cead41bbdb998ec24146d119b69edb9c5a446f8a9ac1ea9ad50af7b3a5')
CORE_OLD, CORE_NEW = '9faeabc2892d8c7133111e13ad55af66790a2ac6', 'deefb98b2aed07875df31351d081fbac195cb1cd'
TREE_OLD, TREE_NEW = 'c9f19d215d271a5dda0bce296dc72c32dfc35499', 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'
COMPOSE_OLD = ('/var/tmp/ga-e0t1.15-compose-diagnostic-20260925/compose',
               'e123ee37c020b3c1aae703f2956f7b59a322fd4814cea7fe2e5a96dc6c920a76')
COMPOSE_NEW = ('/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926/compose',
               '53450168ef90fd8698688d25fb031e96b3295ff54132441cda72c593611f3111')
FINALIZE_OLD = ('/var/tmp/ga-e0t1.15-preflight-diagnostic-20260925',
                '510f4d728472e9500beabab0515a1a4e87d30a7c168c7f723f0c53a28f908619')
FINALIZE_NEW = ('/var/tmp/ga-e0t1.18-p10-preflight-diagnostic-20260926',
                'c6dd9ebbee33bc40579fc9b7f0af7e7a9c69500566870910f5361eb4b0e12824')
# The coordinator-cache disposition: the P10 snapshot's pack-cache .git times and the value s2 pins after the
# last coordinator note before the window. s1 carries None; window-base refuses a None pin (s2 binds it).
# The candidate overlay PREP must generate, computed read-only from the live city.toml (4f7e170f), the confined
# `gc config show` and `gc order list` by the generated build_overlay (scratch sh3w_overlay.py, 2026-09-26).
OVERLAY_OLD = '449346e33f73c1882dfd52e3caa0dfc8066ddfdb6eb4ef6c422603be60e817ac'
OVERLAY_NEW = '8b039657aa28ab5edc10ab50fcd26cea1a3ed15abf65ddae69fdca3c568ca50f'
CACHE_P10_NS = 1790411960644198389
# s2: pinned after the last coordinator note (the s1 outcome workflow.py log, 2026-09-26 09:31:02Z); the
# operator approved this disposition on 2026-09-26. No workflow.py and no unguarded gc until TERMINAL.
CACHE_PINNED_NS = 1790415062719606803
# s2: the ga-sh3w PREP outputs (job ga-sh3w-s1-prep at 6009a6b3, PREP PASS 2026-09-26 09:29:43Z) replace the
# ga-qcwl ones: the isolated overlay, the final receipt image, the isolated revision and the result record. The
# isolated order list is unchanged (b57082cf): the same core pack nudge-on-route order and env.
PREP_PINS = [
    ('449346e33f73c1882dfd52e3caa0dfc8066ddfdb6eb4ef6c422603be60e817ac',
     '8b039657aa28ab5edc10ab50fcd26cea1a3ed15abf65ddae69fdca3c568ca50f'),
    ('c1761144d7ab3b1d557e097902d681325b647324957df56eff4ee8afa77f78eb',
     '3b4e022d958279078155a03e2aafd346a3a322a99cdbe9c712f955a45316c21c'),
    ('2de85e1eb06c2b4898aa49896d0683bdd22b77597b8402311dcd956850d93348',
     'e0ed64ff77370ef18428546003660397b3ac0ad3ad77747eab695561cd00055e'),
    ('9d59a0b4c2c3ce2d12668039559b0b11eb60f45e625a98996185573816744c92',
     '2b1762c8b389af9f52adbcdf6d94419edb6f7d9dd5c3e69f94f655099a05f747'),
]


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
    for old, new in IDENTITY:
        text = text.replace(old, new)
    return ROOT_DATE.sub(lambda m: m.group(1) + '-20260926-r1', text)


# The hardened git prefix for every coordinator read of the candidate worktree (gct-lagl HANDOFF 4.2).
HARDENED = ("['/usr/bin/env','GIT_CONFIG_NOSYSTEM=1','GIT_CONFIG_GLOBAL=/dev/null','GIT_ATTR_NOSYSTEM=1',"
            "'HOME=/nonexistent','/usr/bin/git','--no-optional-locks','--git-dir=%s','--work-tree=%s',"
            "'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','core.attributesFile=/dev/null']"
            % (ADMIN, WORK))


def window_base(text):
    text = sub(text, "BASE = '%s'" % BASE_OLD, "BASE = '%s'\nADMIN = Path('%s')\nHARDENED = %s"
               % (BASE_NEW, ADMIN, HARDENED))
    text = sub(text, "WITNESS = Path('%s')\nWITNESS_SHA = '%s'\n" % WITNESS_OLD,
               "WITNESS = Path('%s')\nWITNESS_SHA = '%s'\n" % WITNESS_NEW)
    text = sub(text, "RECEIPT_SHA = ('%s'," % RECEIPT_OLD, "RECEIPT_SHA = ('%s'," % RECEIPT_NEW)
    text = sub(text, "REVISION = ('%s'," % REVISION_OLD, "REVISION = ('%s'," % REVISION_NEW)
    text = sub(text, "INPUT = (Path('%s'), PREP/'receipt.input.json')\nINPUT_SHA = ('%s',\n" % INPUT_OLD,
               "INPUT = (Path('%s'), PREP/'receipt.input.json')\nINPUT_SHA = ('%s',\n" % INPUT_NEW)
    text = sub(text, "# S4: the accepted image is the P7 adoption snapshot on the post-S2/S3 host (two LIVE_PASS readbacks).\n"
                     "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_OLD,
               "# The accepted image is the P10 adoption snapshot on the post-sequence-15 host (two readback reviews).\n"
               "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_NEW)
    text = sub(text, "    # S4: the S2 supervisor epoch; the broker has stayed active since the sequence 14 install.\n"
                     "    for name, pid, start in [('core','%s','%s'), ('signer','2310','39660502'),\n"
               % (PID_OLD, START_OLD),
               "    # The sequence 15 supervisor epoch; the broker and the signer are unchanged since S2.\n"
               "    for name, pid, start in [('core','%s','%s'), ('signer','2310','39660502'),\n" % (PID_NEW, START_NEW))
    text = sub(text, "    return '%s'\n" % GC_OLD, "    return '%s'\n" % GC_NEW)
    text = sub(text, "value['controller']['pid']==%s," % PID_OLD, "value['controller']['pid']==%s," % PID_NEW)
    text = sub(text, "require(newest['controller_pid']==%s, 'controller trace epoch drift')" % PID_OLD,
               "require(newest['controller_pid']==%s, 'controller trace epoch drift')" % PID_NEW)
    # The accepted image, admitted through exactly one disposition: the coordinator's Bead notes after P10.
    text = sub(text, "        # S4: the P7 snapshot was taken on this epoch after S2 and S3; no P6-era disposition applies.\n"
                     "        require(RECOVERY is None, 'no recovery admission in S4')\n"
                     "        image = prior\n",
               "        # The P10 snapshot was taken on this epoch after sequence 15; only the coordinator-cache\n"
               "        # disposition of this window applies (approved_candidate_cache_image).\n"
               "        require(RECOVERY is None, 'no recovery admission in this window')\n"
               "        image = approved_candidate_cache_image(prior)\n")
    text = sub(text, "def account_read_times(a, z, window):\n",
               "CACHE_P10_NS = %d\n"
               "CACHE_PINNED_NS = %s\n\n"
               "def approved_candidate_cache_image(prior):\n"
               "    # ga-sh3w disposition, for operator approval and independent review: after the P10 adoption\n"
               "    # snapshot, the coordinator recorded M9, P10 and the vault inventory on ga-e0t1 through the canonical\n"
               "    # workflow.py, whose Bead reads run bd without GIT_OPTIONAL_LOCKS=0. That advances only the pack\n"
               "    # cache repository's .git directory mtime and ctime. s2 pins the value after the last such note;\n"
               "    # from then until TERMINAL no workflow.py call of any verb and no bd or gc call without\n"
               "    # GIT_OPTIONAL_LOCKS=0 runs. Every other cache, pin, protected-tree and host value stays exact.\n"
               "    # Never reuse this for fresh drift.\n"
               "    require(CACHE_PINNED_NS is not None, 'coordinator cache value not yet pinned (s2)')\n"
               "    value=json.loads(json.dumps(prior))\n"
               "    entry=value['cache']['inventory'][CACHE_DIRECTORY]\n"
               "    for key in ('mtime_ns','ctime_ns'):\n"
               "        require(entry[key] == CACHE_P10_NS, 'coordinator cache exception preimage')\n"
               "        entry[key] = CACHE_PINNED_NS\n"
               "    return value\n\n"
               "def account_read_times(a, z, window):\n" % (CACHE_P10_NS, CACHE_PINNED_NS))
    # The running-agent identity in status observations (renamed with the target).
    sub(text, "all(a['qualified_name']=='%s' for a in running)" % TARGET_NEW, '')
    # The worker base and cleanliness, read with the hardened form (no candidate-selected drivers).
    text = sub(text, "        result=phase('git-head',['/usr/bin/git','-C',str(WORK),'rev-parse','HEAD'],b,owned)\n",
               "        result=phase('git-head',HARDENED+['rev-parse','--verify','HEAD^{commit}'],b,owned)\n")
    text = sub(text, "        result=phase('git-status',['/usr/bin/git','-C',str(WORK),'status','--porcelain=v1','--untracked-files=all'],b,owned)\n",
               "        result=phase('git-status',HARDENED+['status','--porcelain=v1','--ignored','--untracked-files=all'],b,owned)\n")
    for old, new in PREP_PINS:
        text = sub(text, "'%s'" % old, "'%s'" % new)
    text = sub(text, "ga-sh3w r11: a rebind of the reviewed ga-y49e base window-state-r6-read-safe.py (b10a3810) onto the\n"
                     "post-S3 baseline (M6 metadata, receipt 7cf59ab9, gc b2760ea4) and task ga-sh3w.",
               "ga-sh3w r11: a rebind of the reviewed ga-y49e base window-state-r6-read-safe.py (b10a3810) onto the\n"
               "post-P10 baseline (M9 metadata, receipt c833908f, gc fce2e9a0) and the candidate task ga-sh3w.")
    return text


def prep(text):
    for old, new in (
            ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC_NEW),
            ("COMPOSE = Path('%s')\nCOMPOSE_SHA = '%s'\n" % COMPOSE_OLD,
             "COMPOSE = Path('%s')\nCOMPOSE_SHA = '%s'\n" % COMPOSE_NEW),
            ("BUILD = Path('%s')\nFINALIZE_SHA = '%s'\n" % FINALIZE_OLD,
             "BUILD = Path('%s')\nFINALIZE_SHA = '%s'\n" % FINALIZE_NEW),
            ("PRIOR = Path('%s')\nPRIOR_SHA = '%s'\n" % INPUT_OLD, "PRIOR = Path('%s')\nPRIOR_SHA = '%s'\n" % INPUT_NEW),
            ("RECEIPT_SHA = '%s'" % RECEIPT_OLD, "RECEIPT_SHA = '%s'" % RECEIPT_NEW),
            ("REVISION = '%s'" % REVISION_OLD, "REVISION = '%s'" % REVISION_NEW),
            # The candidate is the one unsuspended agent; its identity and provider.
            ("    target = identities.index(('gascity', 'implementation-worker'))\n"
             "    assert agents[target]['Provider'] == 'claude-signing'\n",
             "    target = identities.index(('gascity', 'operations-candidate-worker'))\n"
             "    assert agents[target]['Provider'] == 'claude-candidate' and agents[target]['Suspended'] is True\n"
             "    assert agents[target]['MaxActiveSessions'] == 1\n"),
            # The candidate's own max_active_sessions = 1 already produces the singleton warning (renamed above).
            ("    assert SINGLETON_WARNING not in baseline['validation']['warnings']\n"
             "    expected['validation']['warnings'] = sorted(baseline['validation']['warnings'] + [SINGLETON_WARNING])\n",
             "    # The candidate agent already declares max_active_sessions = 1, so the warning is already present.\n"
             "    assert SINGLETON_WARNING in baseline['validation']['warnings']\n"),
):
        text = sub(text, old, new)
    text = sub(text, "OVERLAY_SHA = '%s'" % OVERLAY_OLD, "OVERLAY_SHA = '%s'" % OVERLAY_NEW)
    text = sub(text, "'overlay bytes differ from the derived %s'" % OVERLAY_OLD[:8],
               "'overlay bytes differ from the derived %s'" % OVERLAY_NEW[:8])
    # History: r7 describes the ga-qcwl prep, which the identity rename would otherwise relabel.
    text = sub(text, "r7 (ga-sh3w, ga-e0t1.15 S4): the ga-nibd prep", "r7 (ga-qcwl, ga-e0t1.15 S4): the ga-nibd prep")
    text = sub(text, "   - every city and gascity agent suspended, except gascity/implementation-worker, which is bound\n"
                     "     to the ga-sh3w worktree with sessions 0..1.\n",
               "   - every city and gascity agent suspended, except gascity/operations-candidate-worker, which is\n"
               "     unsuspended and bound to the ga-sh3w candidate worktree with sessions 0..1.\n")
    text = sub(text, "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n",
               "\nr8 (ga-sh3w, the first Operations candidate window): the ga-qcwl prep on the post-P10 host: gc fce2e9a0,\n"
               "receipt c833908f, revision 83c41af6, the P10 input draft, the P10 candidate composition diagnostic\n"
               "(53450168) and the P10 N-profile preflight's finalize (c6dd9ebb). The one unsuspended agent is\n"
               "gascity/operations-candidate-worker (provider claude-candidate), bound to the candidate worktree; its\n"
               "own max_active_sessions = 1 already produces the singleton warning, so none is added.\n"
               "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n")
    return text


def observer(text, name):
    root, binary, record, entry = INSPECTOR_NEW
    text = sub(text, "BUILD=Path('%s')" % INSPECTOR_OLD[0], "BUILD=Path('%s')" % root)
    text = sub(text, "BINARY_SHA='%s'" % INSPECTOR_OLD[1], "BINARY_SHA='%s'" % binary)
    text = sub(text, "MANIFEST_SHA='%s'" % M6_FILE, "MANIFEST_SHA='%s'" % M9_FILE)
    text = sub(text, "'%s'" % INSPECTOR_OLD[2], "'%s'" % record)
    text = sub(text, "result['core_commit']=='%s'" % CORE_OLD, "result['core_commit']=='%s'" % CORE_NEW)
    text = sub(text, "result['core_tree']=='%s'" % TREE_OLD, "result['core_tree']=='%s'" % TREE_NEW)
    text = sub(text, "result['entrypoint_sha256']=='%s'" % INSPECTOR_OLD[3], "result['entrypoint_sha256']=='%s'" % entry)
    if name == 'observe-integrity-r11.py':
        text = sub(text, 'admitted_against_p7_snapshot=True', 'admitted_against_p10_snapshot=True')
        text = sub(text, 'post-S3 baseline (M6). It admits the live state against the P7 adoption snapshot (ga-e0t1.15 S4),\n',
                   'post-P10 baseline (M9). It admits the live state against the P10 adoption snapshot (ga-sh3w window),\n')
        text = sub(text, "    # S4: no recovery admission; the accepted image is the P7 snapshot (window-base).\n",
                   "    # No recovery admission; the accepted image is the P10 snapshot (window-base).\n")
        text = sub(text, "    # snapshot below and compared exactly with the P7 adoption snapshot.\n",
                   "    # snapshot below and compared exactly with the P10 adoption snapshot.\n")
        text = sub(text, "    # The base snapshot named before.json admits the live state against the P7 adoption snapshot\n"
                         "    # (two LIVE_PASS readbacks) and its provider pins; no P6-era disposition applies.\n",
                   "    # The base snapshot named before.json admits the live state against the P10 adoption snapshot\n"
                   "    # (two readback reviews) and its provider pins, through approved_candidate_cache_image only.\n")
    return text


def audit(text):
    # The assignee forms Core can use for this target: the qualified name; the pool session name, which is
    # the target basename with "." encoded as "__" (targetBasename, SanitizeQualifiedNameForSession; this
    # basename has no dot) plus "-<token>"; and the no-session-bead fallback SessionNameFor, with "/" encoded as
    # "--" (s1 review B should_fix 2). The "ci-" and "s-" prefixes cover session ids.
    text = sub(text, "ALIASES = {TARGET, 'gc.implementation-worker', 'gc__implementation-worker'}",
               "ALIASES = {TARGET, 'operations-candidate-worker', 'gascity--operations-candidate-worker'}")
    text = sub(text, "a.startswith(('ci-', TARGET+'-', 'gc.implementation-worker-', 'gc__implementation-worker-'))",
               "a.startswith(('ci-', 's-', TARGET+'-', 'operations-candidate-worker-',\n"
               "                                               'gascity--operations-candidate-worker-'))")
    return text


def watch(text):
    text = sub(text, "    git = ['/usr/bin/git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(w.WORK)]\n",
               "    # The hardened form (gct-lagl HANDOFF 4.2): the candidate worktree can select no driver or hook.\n"
               "    git = list(w.HARDENED)\n")
    text = sub(text, "    run('git-diff', git + ['diff-files', '--patch', '--exit-code'], expected=(0, 1))\n"
                     "    run('git-staged', git + ['diff-index', '--cached', '--patch', '--exit-code', 'HEAD'], expected=(0, 1))\n",
               "    run('git-diff', git + ['diff-files', '--patch', '--binary', '--no-textconv', '--no-ext-diff', '--exit-code'],\n"
               "        expected=(0, 1))\n"
               "    run('git-staged', git + ['diff-index', '--cached', '--patch', '--binary', '--no-textconv', '--no-ext-diff',\n"
               "                             '--exit-code', 'HEAD'], expected=(0, 1))\n")
    return text


BIND_TASK = '''"""The one ga-sh3w contract binding before the window: gc.work_dir and gc.check_path; never route or resume.

ga-sh3w: replaces the ga-qcwl bind-task-r3.py. The Bead description already is the reviewed R3 brief
(ga-cw-first-window r12, 2067a406, sha256 %(description)s), so nothing is appended. The binding sets
exactly two metadata keys:
- gc.work_dir: the candidate worktree the WORKTREE job created;
- gc.check_path: the check the P10 candidate receipt profile pins. Core's start preflight requires this stamp
  on the driving Bead; the path is executed only by formula (ralph) steps, and ROUTE uses --no-formula.
No option override (opt_*) and no template override is written, since either would change the launch argv the
receipt pins. It runs as its own job BEFORE the window, so no window root may exist yet.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE=Path('%(here)s')
ROOT=Path('/var/tmp/ga-sh3w-bind-20260926-r1')
HELPER=HERE/'window-base-r11.py'
HELPER_SHA='%(helper)s'
WORKTREE_RESULT=Path('/var/tmp/ga-sh3w-worktree-20260926-r1/result.json')
WORKTREE_SHA='%(worktree)s'
DESCRIPTION_SHA='%(description)s'
BEAD='ga-sh3w'
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
    assert [d.get('dependency_type') for d in before.get('dependencies') or []]==['related'],'unexpected Bead edge'
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


WORKTREE_TASK = '''"""WORKTREE: create the one ga-sh3w candidate worktree before the window; never route or resume.

ga-sh3w (ga-cw-first-window PLAN r12 step 4, gct-lagl HANDOFF 2.10). The coordinator creates the routed
worktree after the previous candidate session drained:
- the candidate root must exist, be a real directory owned by the operator, and be empty;
- the Operations repository's main head must be BASE and the new branch must not exist;
- `git worktree add -b %(branch)s %(work)s BASE` runs from the canonical repository with no system or global
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

ROOT=Path('/var/tmp/ga-sh3w-worktree-20260926-r1')
OPS=Path('%(ops)s')
CANDIDATE_ROOT=Path('%(root)s')
WORK=Path('%(work)s')
ADMIN=Path('%(admin)s')
BASE='%(base)s'
BRANCH='%(branch)s'
TOOLS=Path('%(tools)s')
TOOLS_SHA='%(tools_sha)s'
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
        sort_keys=True)+'\\n')
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
    (ROOT/'result.json').write_text(json.dumps(result,sort_keys=True)+'\\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
'''


PREROUTE_BLOCK = '''    # ga-sh3w: the reviewed pre-route check (ga-6utp preroute.check) is the last step before the sling.
    shown=run('preroute-bead',w.GC+['--rig','gascity','bd','show','ga-sh3w','--json'])['stdout']
    bead_json=ROOT/'preroute-bead.json'
    fd=os.open(bead_json,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:out.write(shown)
    raw=PREROUTE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PREROUTE_SHA
    tools=CANDIDATE_GIT.read_bytes();assert hashlib.sha256(tools).hexdigest()==CANDIDATE_GIT_SHA
    cg=types.ModuleType('candidate_git');cg.__file__=str(CANDIDATE_GIT);sys.modules['candidate_git']=cg
    exec(compile(tools,str(CANDIDATE_GIT),'exec',dont_inherit=True),cg.__dict__)
    pr=types.ModuleType('preroute');pr.__file__=str(PREROUTE);sys.modules['preroute']=pr
    exec(compile(raw,str(PREROUTE),'exec',dont_inherit=True),pr.__dict__)
    checked=pr.check(Path('%(root)s'),Path('%(ops)s/.git'),'ga-sh3w',bead_json,1000,
        pr.load_record(RECORD,RECORD_SHA),w.BASE,DESCRIPTION_SHA)
    assert checked['ok'] is True and checked['worktree']=='%(work)s'
    w.save('preroute.json',checked)
'''


def route(text, bind_sha):
    text = sub(text, "import stat\nimport types\n", "import stat\nimport sys\nimport types\n")
    text = sub(text, "BRIEF_SHA='8c43eaf4104c647d4efc24ccb88051f6740a7f4f18c7534cc5aa129df32f57a9'\n",
               "DESCRIPTION_SHA='%s'\n"
               "PREROUTE=Path('%s')\nPREROUTE_SHA='%s'\n"
               "CANDIDATE_GIT=Path('%s')\nCANDIDATE_GIT_SHA='%s'\n"
               "RECORD=Path('%s')\nRECORD_SHA='%s'\n"
               % (DESCRIPTION_SHA, PREROUTE[0], PREROUTE[1], CANDIDATE_GIT[0], CANDIDATE_GIT[1], RECORD[0], RECORD[1]))
    text = sub(text, "    assert intent['executor_sha256']==BIND_SHA and intent['brief_sha256']==BRIEF_SHA\n",
               "    assert intent['executor_sha256']==BIND_SHA and intent['description_sha256']==DESCRIPTION_SHA\n")
    text = sub(text, "    assert result==dict(ok=True,bead='ga-sh3w',contract_bound=True,attempt_state='requested',\n"
                     "        routed=False,assigned=False,worker_launched=False,live_configuration_changed=False)\n",
               "    assert result==dict(ok=True,bead='ga-sh3w',contract_bound=True,routed=False,assigned=False,\n"
               "        worker_launched=False,live_configuration_changed=False)\n")
    text = sub(text, "    argv=w.GC+['--rig','gascity','sling',TARGET,'ga-sh3w','--no-formula','--no-convoy','--json']\n",
               PREROUTE_BLOCK % dict(root=CANDIDATE_ROOT, ops=OPS, work=WORK)
               + "    argv=w.GC+['--rig','gascity','sling',TARGET,'ga-sh3w','--no-formula','--no-convoy','--json']\n")
    [old] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", text, re.M)
    return text.replace("BIND_SHA='%s'" % old, "BIND_SHA='%s'" % bind_sha)


# Reviewed ga-6utp r12 tools (21039a1c) and the activation's city process record.
ACTIVATION = ('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
              '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-6utp-activation-r10')
PREROUTE = (ACTIVATION + '/preroute.py', None)
CANDIDATE_GIT = (ACTIVATION + '/candidate_git.py', None)
RECORD = ('/home/loucmane/.local/share/gas-city-staging/ga-6utp-activation-r12-20260926/records/process-record.json', None)


def pinned(path):
    return (path, sha(Path(path).read_bytes()))


def operator_script(name, text):
    text = sub(text, 'no process names the Core worktree', 'no process names the candidate worktree',
               1 if name in ('operator/PREFLIGHT.sh', 'operator/RESUME.sh') else 0)
    text = sub(text, 'names the Core worktree ($named)', 'names the candidate worktree ($named)',
               1 if name in ('operator/PREFLIGHT.sh', 'operator/RESUME.sh') else 0)
    return text


JOB = '''#!/bin/sh
# ga-sh3w window %(label)s: %(what)s
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-sh3w-window/%(slug)s-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-sh3w-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-sh3w-window
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


def job(label, what, slug, script, file, out, step_sha):
    return JOB % dict(label=label, what=what, slug=slug, script=script, file=file, out=out, step_sha=step_sha,
                      upper=slug.upper())


def rebind(files):
    global PREROUTE, CANDIDATE_GIT, RECORD
    PREROUTE, CANDIDATE_GIT, RECORD = pinned(PREROUTE[0]), pinned(CANDIDATE_GIT[0]), pinned(RECORD[0])
    out = {}
    for name, raw in files.items():
        text = rename(raw.decode())
        if name == 'window-base-r11.py':
            text = window_base(text)
        elif name == 'window-r11.py':
            text = sub(text, "w.require(newest['controller_pid']==%s and 0<=age<=120,'stale/active controller revision')" % PID_OLD,
                       "w.require(newest['controller_pid']==%s and 0<=age<=120,'stale/active controller revision')" % PID_NEW)
            text = sub(text, "INSPECTOR_SHA='%s'" % INSPECTOR_OLD[1], "INSPECTOR_SHA='%s'" % INSPECTOR_NEW[1])
            text = sub(text, 'admitted_against_p7_snapshot=True,', 'admitted_against_p10_snapshot=True,')
        elif name == 'route-chain-r1.py':
            text = sub(text, "cycle['controller_pid']==%s" % PID_OLD, "cycle['controller_pid']==%s" % PID_NEW)
        elif name == 'prep-r11.py':
            text = prep(text)
        elif name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
            text = observer(text, name)
        elif name == 'watch-r11.py':
            text = watch(text)
        elif name == 'audit-queue-r3.py':
            text = audit(text)
        elif name.startswith('operator/'):
            text = operator_script(name, text)
            if name == 'operator/PREP.sh':
                text = sub(text, '# ga-sh3w window prep r7:', '# ga-sh3w window prep r8:')
                text = sub(text, '# staging log below. It is the reviewed ga-nibd prep (the ga-gegx prep) on the post-S3 host,\n'
                                 '# rebound to ga-sh3w, with\n',
                           '# staging log below. It is the reviewed ga-qcwl prep on the post-P10 host, retargeted to the\n'
                           '# Operations candidate (ga-sh3w), with\n')
        out[name] = text.encode()
    here = WORKTREE + '/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-sh3w-window'
    out['worktree-task-r1.py'] = (WORKTREE_TASK % dict(ops=OPS, root=CANDIDATE_ROOT, work=WORK, admin=ADMIN,
                                                       base=BASE_NEW, branch=BRANCH, tools=CANDIDATE_GIT[0],
                                                       tools_sha=CANDIDATE_GIT[1])).encode()
    out['bind-task-r4.py'] = (BIND_TASK % dict(here=here, helper=sha(out['window-base-r11.py']),
                                               worktree=sha(out['worktree-task-r1.py']), description=DESCRIPTION_SHA,
                                               target=TARGET_NEW, work=WORK, check=CHECK_PATH,
                                               branch=BRANCH)).encode()
    out['route-task-r5.py'] = route(out['route-task-r5.py'].decode(), sha(out['bind-task-r4.py'])).encode()
    out['operator/WORKTREE.sh'] = job('worktree', 'create the one candidate worktree before the window.', 'worktree',
                                      'WORKTREE.sh', 'worktree-task-r1.py', '/var/tmp/ga-sh3w-worktree-20260926-r1',
                                      sha(out['worktree-task-r1.py'])).encode()
    out['operator/BIND.sh'] = job('bind', 'the one ga-sh3w contract binding (gc.work_dir, gc.check_path), before the window.',
                                  'bind', 'BIND.sh', 'bind-task-r4.py', '/var/tmp/ga-sh3w-bind-20260926-r1',
                                  sha(out['bind-task-r4.py'])).encode()
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
