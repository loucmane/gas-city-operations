"""Sixth successor s1: derive the ga-nibd window package from the reviewed ga-gegx package (s3 275b1fa8).

  python3 -B make_successor.py <output package dir>

The ga-gegx window (s2 r9 cb949793) ran on 2026-09-25 to RESUME. Its worker ci-ki0gd went active at an empty
prompt and was reaped unclaimed. Core's nudge-on-route order never matched: gc events wraps bead.updated as
.payload.bead, and the pack script filters the flat .payload.metadata. RESTORE then refused on Core's
ten-minute auto trace arm, and the reviewed RECOVER-3 (s3 275b1fa8) finished the restore. ga-nibd is the sixth
successor, with a fresh worktree at Core e6366b9e.

1. Every source is read from the s3 commit object (git blobs), never from a working tree.
2. Dropped: README.md, the tests and the generator (this package's own replace them), and RECOVER-3 with its
   wrapper (they belong to the ga-gegx window).
3. RECONCILE is retargeted: it holds ga-gegx (consumed attempt, session ci-ki0gd, state stale-session);
   ga-f37t (already blocked) is the unrelated predecessor that must stay exact; ga-nibd must be pristine.
4. The admission (window-base approved_recovery_image) takes its pins from the ga-gegx RECOVER-3 result,
   pinned by digest; OBSERVE sets RECOVERY to it.
5. PREP derives the overlay from the ga-gegx r5 overlay (work dir and header only); a new PREP root.
6. RESTORE's trace wait (window-r11 reload) waits out Core's auto trace arm on the worker template instead of
   refusing, up to 20 minutes for RESTORE; RESTORE's budget becomes 45 minutes.
7. New: KICK (kick-r1.py and operator/KICK-1..3.sh), one immediate, dialog-checked nudge that tells the active
   worker to claim its routed task.
8. Identity: paths, roots, worktree, branch, evidence path, Bead id. History comments that describe ga-gegx
   events stay attributed to ga-gegx (KEEP), and the ga-gegx RECOVER-3 root is kept.
9. ROUTE's BIND_SHA follows the new bind-task digest (BIND runs again for ga-nibd).
10. Digest propagation to a fixed point; the KICK wrappers pin the final kick-r1.py.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = '275b1fa8126ac5254ccbb21d8e4ba54f9ba571c9'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-gegx-window/'
HERE = Path(__file__).resolve().parent
DROP = {'README.md', 'test_successor.py', 'recover-restore-r1.py', 'operator/RECOVER-3.sh'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

RECOVER3_ROOT = '/var/tmp/ga-gegx-recover-20260925-r3'
RECOVER3_RESULT_SHA = 'b6ad8162b8eec1a26a07b63a3e6f0238e1dad116533b31ed0e7cf494b641c02e'
STOPPED_BASELINE_SHA = '771107c0d53eed26780fe63f4f2311849b54a1d373e9d12770633e2348d4c137'
KEEP = [RECOVER3_ROOT,
        '# ga-gegx s2: ', '# ga-gegx s2 r2: ', 'r4 (ga-gegx, ', 'r5 (ga-gegx)', '(ga-gegx r4)',
        '# ga-gegx r5: ', '(ga-gegx) in keeping', '# ga-gegx: keep Core', '# ga-gegx: every order',
        '# ga-gegx: the visible pane']

IDENTITY = [
    ('/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles',
     '/home/loucmane/gascity-core-worktrees/ga-nibd-typed-route-cycles'),
    ('codex/ga-gegx-typed-route-cycles', 'codex/ga-nibd-typed-route-cycles'),
    ('/designs/ga-gegx-window', '/designs/ga-nibd-window'),
    ('gas-city-staging/ga-gegx-window', 'gas-city-staging/ga-nibd-window'),
    ('/var/tmp/ga-gegx-prep-20260925-r3', '/var/tmp/ga-nibd-prep-20260925-r1'),
    ('/var/tmp/ga-gegx-', '/var/tmp/ga-nibd-'),
    ('ga-gegx', 'ga-nibd'),
    ('TestGagegxCapabilityProbeNoTests', 'TestGanibdCapabilityProbeNoTests'),
]

# RECONCILE: hold ga-gegx, keep ga-f37t exact, ga-nibd pristine.
RECONCILE_NOTE = re.compile(r"NOTE=\('Failed-attempt hold .*?'\)\n", re.S)
NEW_NOTE = ("NOTE=('Failed-attempt hold 2026-09-25: session ci-ki0gd woke on 2026-09-25 and never '\n"
            "      'claimed (Core nudge-on-route never matched the routed event); Core closed it '\n"
            "      'stale and its native attempt remains permanently consumed. Fresh successor '\n"
            "      'ga-nibd owns the task. This reviewed status-only reconciliation follows the '\n"
            "      'ga-y49e precedent; no route, claim, session or lifecycle change.')\n")

# window-base: the RECOVER-3 admission comment (the logic is unchanged).
RECOVERY_COMMENT = re.compile(r"    # ga-gegx disposition, for independent review:.*?\n    root = Path\(root\)\n", re.S)
NEW_RECOVERY_COMMENT = (
    "    # ga-nibd disposition, for independent review: the ga-gegx window stopped in RESTORE (Core's auto trace\n"
    "    # arm refused its trace wait after the accepted city.toml was written), and the reviewed ga-gegx\n"
    "    # RECOVER-3 job restored the accepted receipt (new inode and times); the window's city-suspend and\n"
    "    # rig-suspend left the suspension state fully suspended with a new updated_at. OBSERVE sets RECOVERY to\n"
    "    # that job's root and its pinned result digest. Only the city.toml, receipt and suspension-state pin\n"
    "    # entries are replaced, with the ones the result recorded: the two files must keep the accepted content\n"
    "    # digest, and the suspension state must decode to the accepted suspension image apart from updated_at.\n"
    "    # Every other pin, the cache, the protected trees and the host stay compared as before. Never reuse\n"
    "    # this for fresh drift.\n"
    "    root = Path(root)\n")

RELOAD_OLD = (
    "    deadline=time.monotonic()+120;index=0\n"
    "    while True:\n"
    "        remaining=deadline-time.monotonic()\n"
    "        w.require(remaining>0,'revision observation timeout; no mutation replay')\n"
    "        result=w.phase(name+'-trace-'+str(index),w.GC+[\n"
    "            'trace','show','--type','cycle_result','--since','2m','--json'],\n"
    "            b,owned,timeout=min(90,remaining))\n"
    "        rows=json.loads(result['stdout'])['records']\n"
    "        newest=max(rows,key=lambda row:row['seq']) if rows else None\n"
    "        if newest:\n"
    "            observed=time.time_ns()\n"
    "            age=observed/10**9-datetime.fromisoformat(newest['ts'].replace('Z','+00:00')).timestamp()\n"
    "            w.require(newest['controller_pid']==2331 and 0<=age<=120\n"
    "                and newest['fields']['active_template_count']==0,'stale/active controller revision')\n"
    "            if newest['config_revision']==w.REVISION[i] and newest['completion_status']=='completed':break\n"
    "        index+=1\n"
    "        time.sleep(min(1,max(0,deadline-time.monotonic())))\n")
RELOAD_NEW = (
    "    # ga-nibd: after a worker session ran, Core keeps an auto trace arm on the worker template for about ten\n"
    "    # minutes (gc trace status: source auto, trigger start), and every cycle then counts that template as\n"
    "    # active. The ga-gegx RESTORE refused on exactly that. A cycle whose only active template is the armed\n"
    "    # worker template, with no decisions or mutations, is waited out; anything else active still refuses.\n"
    "    # RESTORE (direction 0) waits up to 20 minutes, reading every 15 seconds; STAGE keeps 120 seconds.\n"
    "    deadline=time.monotonic()+(120 if i else 1200);index=0\n"
    "    while True:\n"
    "        remaining=deadline-time.monotonic()\n"
    "        w.require(remaining>0,'revision observation timeout; no mutation replay')\n"
    "        result=w.phase(name+'-trace-'+str(index),w.GC+[\n"
    "            'trace','show','--type','cycle_result','--since','2m','--json'],\n"
    "            b,owned,timeout=min(90,remaining))\n"
    "        rows=json.loads(result['stdout'])['records']\n"
    "        newest=max(rows,key=lambda row:row['seq']) if rows else None\n"
    "        if newest:\n"
    "            observed=time.time_ns()\n"
    "            age=observed/10**9-datetime.fromisoformat(newest['ts'].replace('Z','+00:00')).timestamp()\n"
    "            w.require(newest['controller_pid']==2331 and 0<=age<=120,'stale/active controller revision')\n"
    "            fields=newest['fields']\n"
    "            armed=(fields['active_template_count']==1\n"
    "                and fields.get('templates_touched')==['gascity/gc.implementation-worker']\n"
    "                and not fields.get('decision_counts') and not fields.get('mutation_counts'))\n"
    "            w.require(fields['active_template_count']==0 or armed,'stale/active controller revision')\n"
    "            if (newest['config_revision']==w.REVISION[i] and newest['completion_status']=='completed'\n"
    "                    and fields['active_template_count']==0):break\n"
    "        index+=1\n"
    "        time.sleep(min(1 if i else 15,max(0,deadline-time.monotonic())))\n")

PREP_OVERLAY = Path('/var/tmp/ga-gegx-prep-20260925-r3/city.isolated.toml')
PREP_OVERLAY_SHA = 'e6e24bd75d374a1e69719a9a9d2aa95060569d692d8ae8d63888fd05438c9540'
KICK_SLOTS = 3
# s2: window-base pins the ga-nibd PREP r6 outputs (job ga-nibd-s1-prep, 2026-09-25 12:40:01Z) in place of
# the ga-gegx PREP r5 outputs it inherited.
PREP_PINS = [
    ('e6e24bd75d374a1e69719a9a9d2aa95060569d692d8ae8d63888fd05438c9540',
     'c38c6cb43b6c1124529d66e1a10e1d69fc8cb3b21d4f1f12255de16dd991f5e9'),
    ('9c5765b8588e1aec3a5fa3ffe31d170d4cfdc23052f7ac90a780da819cd587f6',
     '77cd84868bf5bf4dc5490a579b5c1cfb5d3d1492728ad96f0c9957dffed2bbd5'),
    ('56f39eb270cbe057d5f9fc313eca21c24cc469bcc18676bf38dd7c66a95b6363',
     '42e67fba14e666e44de66d3bf12a49dd66f1ffeef5977cbe7aea358a74ce8a44'),
    ('22e16a70309343f7abc6ebe976257a69c629d859306a291cbbe8c5f9eaebde58',
     'dff7cad90face39def59c500f569893f1f4ec8ea6a6dc318a783291908f9bddc'),
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


def successor_overlay():
    raw = PREP_OVERLAY.read_bytes()
    assert sha(raw) == PREP_OVERLAY_SHA
    text = raw.decode()
    for old, new in (('ga-gegx-typed-route-cycles', 'ga-nibd-typed-route-cycles'),
                     ('# ga-gegx bounded one-worker window', '# ga-nibd bounded one-worker window')):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text.encode()


def sub(text, old, new, count=1):
    assert text.count(old) == count, old[:70]
    return text.replace(old, new)


def rename(text):
    for index, phrase in enumerate(KEEP):
        text = text.replace(phrase, '\x00KEEP%d\x00' % index)
    for old, new in IDENTITY:
        text = text.replace(old, new)
    for index, phrase in enumerate(KEEP):
        text = text.replace('\x00KEEP%d\x00' % index, phrase)
    return text


def reconcile(text):
    text = text.replace('ga-gegx', '\x00NEW\x00').replace('ga-f37t', 'ga-gegx').replace('ga-4z38', 'ga-f37t')
    text = text.replace('\x00NEW\x00', 'ga-nibd').replace('ci-yauk5', 'ci-ki0gd')
    text = sub(text, 'for the fifth successor it', 'for the sixth successor it')
    text, found = RECONCILE_NOTE.subn(NEW_NOTE, text)
    assert found == 1
    return text


def kick_wrapper(slot, wrapper):
    text = wrapper
    for old, new in (('source release: validate the coordinator source release against the live\n'
                      '# worker session, post it once to the ga-nibd notes, read it back and nudge.\n'
                      '# Repeatable: a run after the post only verifies and nudges again.\n',
                      'kick: one immediate, dialog-checked nudge that tells the live worker to claim\n'
                      '# its routed task (kick-r1.py). Refuses without a nudge once the task is claimed.\n'),
                     ('source-release-1-', 'kick-%d-' % slot),
                     ('SOURCE-RELEASE-1', 'KICK-%d' % slot),
                     ('Slot 1 of 3', 'Slot %d of %d' % (slot, KICK_SLOTS)),
                     ('RELEASE_SHA', 'KICK_SHA'),
                     ('step budget "$C/budget-r11.py" "$BUDGET_SHA" 100\n',
                      'step budget "$C/budget-r11.py" "$BUDGET_SHA" 100\n'),
                     ('step source-release "$C/release-r11.py" "$KICK_SHA" source\n',
                      'step kick "$C/kick-r1.py" "$KICK_SHA"\n')):
        assert old in text, old[:60]
        text = text.replace(old, new)
    assert 'release' not in text.lower().replace('release-r11', ''), 'leftover release wording'
    return text


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = raw.decode()
        if name == 'reconcile-predecessor-r3.py':
            out[name] = reconcile(text).encode()
            continue
        if name == 'window-base-r11.py':
            # The new comment describes ga-gegx history; protect it from the identity rename.
            text, found = RECOVERY_COMMENT.subn(NEW_RECOVERY_COMMENT.replace('ga-gegx', '\x00G\x00'), text)
            assert found == 1
        text = rename(text).replace('\x00G\x00', 'ga-gegx')
        if name == 'window-r11.py':
            text = sub(text, RELOAD_OLD, RELOAD_NEW)
        if name == 'window-base-r11.py':
            for old, new in PREP_PINS:
                text = sub(text, "'%s'" % old, "'%s'" % new)
        if name == 'operator/RESTORE.sh':
            text = sub(text, 'step budget "$C/budget-r11.py" "$BUDGET_SHA" 25\n',
                       'step budget "$C/budget-r11.py" "$BUDGET_SHA" 45\n')
        if name == 'operator/ADMIT.sh':
            # ADMIT must still leave RESTORE its own budget (45) plus the earlier 15-minute margin.
            text = sub(text, 'step budget "$C/budget-r11.py" "$BUDGET_SHA" 40\n',
                       'step budget "$C/budget-r11.py" "$BUDGET_SHA" 60\n')
        if name == 'operator/RECONCILE.sh':
            text = sub(text, 'consumed fourth-successor task', 'consumed fifth-successor task')
        if name == 'worker-brief.md':
            text = sub(text, 'ga-y49e, ga-4z38 and ga-f37t attempts', 'ga-y49e, ga-4z38, ga-f37t and ga-gegx attempts')
        if name == 'prep-r11.py':
            overlay = sha(successor_overlay())
            text = sub(text, "OVERLAY_SHA = '%s'" % PREP_OVERLAY_SHA, "OVERLAY_SHA = '%s'" % overlay)
            text = sub(text, "'overlay bytes differ from the derived %s'" % PREP_OVERLAY_SHA[:8],
                       "'overlay bytes differ from the derived %s'" % overlay[:8])
            text = sub(text, "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n",
                       "\nr6 (ga-nibd): the ga-gegx prep, rebound to the ga-nibd worktree and header; nothing else\n"
                       "changes. The overlay is the ga-gegx r5 overlay with only the work dir and header lines\n"
                       "replaced.\n"
                       "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n")
        if name == 'operator/PREP.sh':
            text = sub(text, '# ga-nibd window prep r5:', '# ga-nibd window prep r6:')
            text = sub(text, '# staging log below. It is the reviewed ga-f37t prep, rebound to ga-nibd with\n',
                       '# staging log below. It is the reviewed ga-gegx prep, rebound to ga-nibd, with\n')
        if name == 'observe-integrity-r11.py':
            text, found = re.subn(r"^RECOVER_ROOT='[^']*'\nRECOVER_SHA='[0-9a-f]{64}'\n",
                                  "RECOVER_ROOT='%s'\nRECOVER_SHA='%s'\n" % (RECOVER3_ROOT, RECOVER3_RESULT_SHA),
                                  text, flags=re.M)
            assert found == 1
        out[name] = text.encode()
    # New: KICK, carrying ga-gegx-era digests that the propagation below rebinds.
    out['kick-r1.py'] = (HERE / 'kick-r1.template').read_bytes()
    for slot in range(1, KICK_SLOTS + 1):
        out['operator/KICK-%d.sh' % slot] = kick_wrapper(slot, out['operator/SOURCE-RELEASE-1.sh'].decode()).encode()
    # BIND runs again for ga-nibd, so ROUTE binds the new bind-task digest.
    route = out['route-task-r5.py'].decode()
    [ran] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", route, re.M)
    out['route-task-r5.py'] = route.replace("BIND_SHA='%s'" % ran, "BIND_SHA='%s'" % sha(out['bind-task-r3.py'])).encode()
    keep = {'observe-integrity-r11.py': {RECOVER3_RESULT_SHA}, 'window-base-r11.py': {STOPPED_BASELINE_SHA}}
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
            kept = keep.get(name, set())
            new = DIGEST.sub(lambda m: m.group(0) if m.group(0) in kept else renamed.get(m.group(0), m.group(0)), text)
            if new != text:
                out[name] = new.encode()
                changed = True
        if not changed:
            break
    # The KICK wrappers pin the final kick script (it is not in any earlier history).
    kick = sha(out['kick-r1.py'])
    for slot in range(1, KICK_SLOTS + 1):
        name = 'operator/KICK-%d.sh' % slot
        text, found = re.subn(r'^KICK_SHA=[0-9a-f]{64}$', 'KICK_SHA=' + kick, out[name].decode(), flags=re.M)
        assert found == 1
        out[name] = text.encode()
    return out


def main(output):
    out = rebind(sources())
    root = Path(output)
    for name, data in sorted(out.items()):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(len(out), 'files written to', root)


if __name__ == '__main__':
    main(*sys.argv[1:])
