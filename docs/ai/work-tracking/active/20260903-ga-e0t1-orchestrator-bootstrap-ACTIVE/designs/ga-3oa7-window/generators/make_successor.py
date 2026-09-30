"""Eleventh successor s1: derive the ga-3oa7 Operations candidate window (ga-fsfg R4) from the reviewed ga-x7lx
window package.

  python3 -B make_successor.py <output package dir>

The ga-x7lx window (s2 5d60fc6e, two SOURCE_PASS) ran cleanly on 2026-09-26 and delivered R3, which merged as
Operations PR 392 (8f24ad71). R4's brief was split the same way (package ga-4xg9-brief-r13, r15 09ee3145, two
SOURCE_PASS): task ga-3oa7 (description 9d6b2e1a, no edges) with closed spec holders ga-elig and ga-aju4.

1. Every source is read from the ga-x7lx s2 commit object (5d60fc6e), never from a working tree.
2. Identity: ga-x7lx becomes ga-3oa7 everywhere: the task, the worktree
   /home/loucmane/gas-city-ops-candidate-worktrees/ga-3oa7, its admin directory, every output root and the
   staging directory. The branch is codex/ga-3oa7-dispatch-evidence-write. The consumed ga-x7lx worktree was
   retired (intake.py retire), so the candidate root is empty.
3. Base: Operations main 8f24ad71 (R3 merged), which the R4 brief requires ("read R3's merged form first").
4. BIND r5 and ROUTE pin the ga-3oa7 description.
5. Accepted image: the ga-x7lx TERMINAL observed-after record (59e76bbf), on the same four keys, with the P10
   provider pins. The coordinator-cache disposition, operator-approved for the R4 window on 2026-09-26, moves
   exactly the pack-cache repository's .git mtime and ctime from the ga-x7lx TERMINAL value to the value s2
   pins after the last coordinator note.
6. PREP r10 targets the ga-3oa7 worktree; the overlay (OVERLAY_NEW) is re-derived, and s2 re-pins the fresh
   PREP outputs. Everything else is unchanged from ga-x7lx.
7. Digest propagation to a fixed point.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = '5d60fc6e'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
DESIGNS = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
PREFIX = DESIGNS + 'ga-x7lx-window/'
DROP = {'README.md', 'test_successor.py'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

OPS = '/home/loucmane/gas-city-ops'
CANDIDATE_ROOT = '/home/loucmane/gas-city-ops-candidate-worktrees'
WORK = CANDIDATE_ROOT + '/ga-3oa7'
ADMIN = OPS + '/.git/worktrees/ga-3oa7'
BRANCH = 'codex/ga-3oa7-dispatch-evidence-write'
BASE_OLD, BASE = '040139d8738a025cbb5afcc8170b700292c5016e', '8f24ad7129d81bf54265b916e25c24829c622172'
TARGET = 'gascity/operations-candidate-worker'
BEAD = 'ga-3oa7'
DESCRIPTION_OLD = 'b741402ba05b7e0adc65e4399719a81be1bc2031265893cd1f808f6d8feacd9b'
DESCRIPTION_SHA = '9d6b2e1a1cd9a34fd6d9a05c5ab643fd6a324b62af31dd0bae8f545bf67fb935'
SPECS = (('ga-elig', '6c97f00c467f13bbd7e0bb06610ced7c84dea78a0d0cf31ff9a2d46e321d7d17'),
         ('ga-aju4', '015125c5f442bcefa2a971026f71782b0f1e7ca717b1029c90d0c18d8a9261f0'))
BRIEF_SHA = 'b46fbffe42f35347ce8e3aaf9c63b34e71953349a47fdeaa87a64d2a4c9a0f46'
EXCLUDE = OPS + '/.git/info/exclude'
EXCLUDE_AFTER = '4ef8e39849f5cfe486486339b37f5947d2ff77786250eeeebb7be57170a05bbd'
CHECK_PATH = ('/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f'
              '/gascity/assets/scripts/checks/build-artifact-valid.sh')

ACCEPTED_OLD = ('/var/tmp/ga-sh3w-terminal-20260926-r1/observed-after.json',
                '97df4a335f8656ace8179c61bd0af7e59d765dfef46f64f51a9cf5741c31bf37')
ACCEPTED_NEW = ('/var/tmp/ga-x7lx-terminal-20260926-r1/observed-after.json',
                '59e76bbfeb395759ec93a688ef4dfb81af89148d679eda7626a3a0e7c4f327d7')
PROVIDER = ('/var/tmp/ga-e0t1.18-p10-adoption-20260926/after.json.provider-pins',
            '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b')
CACHE_OLD = (1790415062719606803, 1790419645618740930)
# The pack-cache .git mtime and ctime in the ga-x7lx TERMINAL record; s2 pins the value after the last note.
CACHE_PREV_NS = 1790419645618740930
# s2: pinned after the last coordinator note (the s1 outcome workflow.py log, 2026-09-26 14:09:36Z). From here
# until TERMINAL no workflow.py and no bd or gc call without GIT_OPTIONAL_LOCKS=0 runs.
CACHE_PINNED_NS = 1790431776352453342
# s2: the ga-3oa7 PREP outputs (job ga-3oa7-s1-prep at ed810388, PREP PASS 2026-09-26 14:08:56Z) replace the
# ga-x7lx ones in window-base. The isolated order list is unchanged (b57082cf).
PREP_PINS = [
    ('45014c22e045447fe75b4969e0d01667bf2dab36763ae06abdf8a9c13b6f2425',
     '0e583359552b9c765ae0da5cf971397d6cf0e96b03613238721cc797aad64940'),
    ('87f41c3fae32597d73266cfd4f9322dbe23383de1f0a2d3607ccd9c6c87c20db',
     '62041d275870f6ea5d04860d9c40821c78313bd802706f22dce6a9660f50369a'),
    ('37be13bc0cb50ca487a0dc244dcdf8ed91d9140848e376b8dba8466e1855a597',
     '2a88522aea8912c454204a99942fea748807604c8a640a3612d130e6c83cb28a'),
    ('471266b9e94a2437d86085003ed5cceea461e11df5b713ca8cfaccf88f4bb0d3',
     'a99403becaec1b8255e753828f21cb806fe91642ba5290caa93805e5e567b2da'),
]
OVERLAY_OLD = '45014c22e045447fe75b4969e0d01667bf2dab36763ae06abdf8a9c13b6f2425'
# Derived read-only by the generated build_overlay from the live city.toml (4f7e170f) and the confined gc config
# and order list (2026-09-26); it differs from 45014c22 only in the header line and the candidate work_dir.
OVERLAY_NEW = '0e583359552b9c765ae0da5cf971397d6cf0e96b03613238721cc797aad64940'


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
    text = text.replace('codex/ga-x7lx-delivery-class', BRANCH)
    text = text.replace('ga-x7lx', 'ga-3oa7')
    return text.replace(BASE_OLD, BASE)


def window_base(text):
    text = sub(text, "and the candidate task ga-3oa7, admitted\nagainst the ga-sh3w TERMINAL record (tenth successor).",
               "and the candidate task ga-3oa7 (ga-fsfg R4), admitted\nagainst the ga-x7lx TERMINAL record (eleventh successor).")
    text = sub(text, "# The accepted image is the ga-sh3w TERMINAL observed-after record: this same snapshot() after RESTORE on\n",
               "# The accepted image is the ga-x7lx TERMINAL observed-after record: this same snapshot() after RESTORE on\n")
    text = sub(text, "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_OLD,
               "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % ACCEPTED_NEW)
    text = sub(text, "CACHE_PREV_NS = %d\nCACHE_PINNED_NS = %d\n" % CACHE_OLD,
               "CACHE_PREV_NS = %d\nCACHE_PINNED_NS = %s\n" % (CACHE_PREV_NS, CACHE_PINNED_NS))
    text = sub(text, "    # ga-3oa7 disposition, operator-approved 2026-09-26, for independent review: after the\n"
                     "    # ga-sh3w TERMINAL record, the coordinator recorded the ga-sh3w outcome and the brief split on ga-e0t1 through\n",
               "    # ga-3oa7 disposition, operator-approved 2026-09-26, for independent review: after the\n"
               "    # ga-x7lx TERMINAL record, the coordinator recorded the ga-x7lx outcome, the R3 intake and merge and the R4 brief on ga-e0t1 through\n")
    text = sub(text, "        # The ga-sh3w TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n",
               "        # The ga-x7lx TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n")
    # s1 reviews A 1 and B 1: the accepted record's own TERMINAL time.
    text = sub(text, "# this epoch (TERMINAL PASS 2026-09-26 10:23Z, full native integrity).",
               "# this epoch (TERMINAL PASS 2026-09-26 13:11Z, full native integrity).")
    for old, new in PREP_PINS:
        text = sub(text, "'%s'" % old, "'%s'" % new)
    return text


def observer_integrity(text):
    text = sub(text, "against the ga-sh3w TERMINAL record (ga-3oa7 window),", "against the ga-x7lx TERMINAL record (ga-3oa7 window),")
    text = sub(text, "the accepted image is the ga-sh3w TERMINAL record (window-base).",
               "the accepted image is the ga-x7lx TERMINAL record (window-base).")
    text = sub(text, "compared exactly with the ga-sh3w TERMINAL record.", "compared exactly with the ga-x7lx TERMINAL record.")
    return sub(text, "admits the live state against the ga-sh3w TERMINAL record\n",
               "admits the live state against the ga-x7lx TERMINAL record\n")


def prep(text):
    if OVERLAY_NEW is not None:
        text = sub(text, "OVERLAY_SHA = '%s'" % OVERLAY_OLD, "OVERLAY_SHA = '%s'" % OVERLAY_NEW)
        text = sub(text, "'overlay bytes differ from the derived %s'" % OVERLAY_OLD[:8],
                   "'overlay bytes differ from the derived %s'" % OVERLAY_NEW[:8])
    text = sub(text, "r9 (ga-3oa7, the tenth successor): the ga-sh3w prep retargeted to task ga-3oa7 and its candidate worktree;",
               "r9 (ga-x7lx, the tenth successor): the ga-sh3w prep retargeted to task ga-x7lx and its candidate worktree;")
    return sub(text, "the overlay header and work_dir change, nothing else.\n",
               "the overlay header and work_dir change, nothing else.\n\n"
               "r10 (ga-3oa7, ga-fsfg R4, the eleventh successor): the ga-x7lx prep retargeted to task ga-3oa7 and its\n"
               "candidate worktree; again only the overlay header and work_dir change.\n")


def bind(text):
    text = sub(text, "ga-3oa7: bind-task-r5.py replaces the ga-sh3w bind-task-r4.py. The Bead description is the short task brief\n"
                     "(sha256 %s): the reviewed r12 R3 brief head and working rules, verbatim, and a pointer to the closed\n"
                     "spec holders ga-lpo2 and ga-r2el; together they reassemble to the r12 brief." % DESCRIPTION_OLD,
               "ga-3oa7: bind-task-r5.py as reviewed for ga-x7lx, rebound to R4. The Bead description is the short task brief\n"
               "(sha256 %s): the reviewed r12 R4 brief head and working rules, verbatim, the r15 pre-window\n"
               "clarifications and a pointer to the closed spec holders ga-elig and ga-aju4; head, parts and tail reassemble\n"
               "to the r12 R4 brief." % DESCRIPTION_SHA)
    return sub(text, "DESCRIPTION_SHA='%s'" % DESCRIPTION_OLD, "DESCRIPTION_SHA='%s'" % DESCRIPTION_SHA)


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = rename(raw.decode())
        if name == 'window-base-r11.py':
            text = window_base(text)
        elif name == 'observe-integrity-r11.py':
            text = observer_integrity(text)
        elif name == 'prep-r11.py':
            text = prep(text)
        elif name == 'bind-task-r5.py':
            text = bind(text)
        elif name == 'route-task-r5.py':
            text = sub(text, "DESCRIPTION_SHA='%s'" % DESCRIPTION_OLD, "DESCRIPTION_SHA='%s'" % DESCRIPTION_SHA)
        elif name == 'operator/PREP.sh':
            text = sub(text, '# ga-3oa7 window prep r9:', '# ga-3oa7 window prep r10:')
        out[name] = text.encode()
    history = {name: {sha(raw)} for name, raw in files.items()}
    while True:
        for name, raw in out.items():
            history.setdefault(name, set()).add(sha(raw))
        renamed = {old: sha(out[n]) for n in out for old in history[n] if old != sha(out[n])}
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
