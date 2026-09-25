"""Fifth successor s1: derive the ga-gegx window package from the reviewed ga-f37t package (s7 e382bc15).

  python3 -B make_successor.py <output package dir>

ga-f37t s6 r5 (01d74775) ran its window on 2026-09-25 to RESUME. The worker session ci-yauk5 started in the
right worktree but never received its task and Core reaped it: the window overlay skipped the Core
nudge-on-route order, and gc sling does not nudge warm-idle workers (Core orders/nudge-on-route.toml). The
attempt is consumed. The window stopped at HOLD and CLOSE, and the reviewed RECOVER-2 (s7 e382bc15) returned
the city to its accepted image. ga-gegx is the fifth successor, with a fresh worktree at Core e6366b9e.

1. Every source is read from the s7 commit object (git blobs), never from a working tree.
2. Dropped: README.md, the tests and the generator (test_successor.py replaces them), the two recovery jobs
   and their wrappers (they belong to the ga-f37t windows), and FRESHEN (unused since s5).
3. RECONCILE is retargeted (RECONCILE_SUBS): it holds ga-f37t, whose consumed attempt is session ci-yauk5
   (state stale-session); ga-4z38 (already blocked) is the unrelated predecessor that must stay exact, and
   ga-gegx must be pristine.
4. The admission (window-base approved_recovery_image) now takes the city.toml, receipt and suspension-state
   pins from the ga-f37t RECOVER-2 result, pinned by digest; OBSERVE sets RECOVERY to it.
5. PREP keeps nudge-on-route out of the overlay's order skip list; its OVERLAY_SHA is the derived overlay.
6. Identity: paths, roots, worktree, branch, evidence path, Bead id. History comments that describe ga-f37t
   events stay attributed to ga-f37t (HISTORY), and the evidence roots of the ga-f37t windows are kept.
7. ROUTE's BIND_SHA follows the new bind-task digest (BIND runs again for ga-gegx).
8. Digest propagation to a fixed point.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = 'e382bc1544349f4ac666bc8cd5b64135d9fb8fa1'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-f37t-window/'
DROP = {'README.md', 'test_successor.py', 'recover-stage-r1.py', 'recover-window-r2.py', 'operator/RECOVER.sh',
        'operator/RECOVER-2.sh', 'freshen-r11.py', 'operator/FRESHEN-1.sh', 'operator/FRESHEN-2.sh',
        'operator/FRESHEN-3.sh'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

# Evidence of the ga-f37t windows that the new package reads, and history that stays attributed.
RECOVER2_ROOT = '/var/tmp/ga-f37t-recover-20260925-r2'
RECOVER2_RESULT_SHA = '23e796d7849add2b722536554e60dc79ee8f31507192ecc35b7359a47c4bc736'
STOPPED_BASELINE = '/var/tmp/ga-f37t-window-20260925-r2/suspension-baseline.json'
STOPPED_BASELINE_SHA = '771107c0d53eed26780fe63f4f2311849b54a1d373e9d12770633e2348d4c137'
KEEP = [RECOVER2_ROOT, STOPPED_BASELINE,
        '# ga-f37t s3 disposition, for independent review:',
        '# ga-f37t s4 disposition, operator-approved 2026-09-25, for independent review:',
        '# ga-f37t s5 disposition, operator-approved 2026-09-25 in place of FRESHEN, for independent review:',
        '# ga-f37t s5 start gate, for independent review.']

# The ga-f37t s6 recovery disposition is replaced by the RECOVER-2 disposition.
OLD_RECOVERY_START = '\nRECOVERY = None\n'
OLD_RECOVERY_END = '\ndef directories(o):'
NEW_RECOVERY = '''
RECOVERY = None

def approved_recovery_image(prior, root, result_sha):
    # ga-gegx disposition, for independent review: the ga-f37t window stopped at HOLD and CLOSE, and the
    # reviewed ga-f37t RECOVER-2 job returned city.toml and the receipt to their accepted content (new inodes
    # and times); the window's city-suspend and rig-suspend left the suspension state fully suspended with a
    # new updated_at. OBSERVE sets RECOVERY to that job's root and its pinned result digest. Only the
    # city.toml, receipt and suspension-state pin entries are replaced, with the ones the result recorded:
    # the two files must keep the accepted content digest, and the suspension state must decode to the
    # accepted suspension image apart from updated_at. Every other pin, the cache, the protected trees and
    # the host stay compared as before. Never reuse this for fresh drift.
    root = Path(root)
    s = root.lstat()
    require(stat.S_ISDIR(s.st_mode) and s.st_uid == 1000 and stat.S_IMODE(s.st_mode) == 0o700,
            'recovery root authority')
    result = json.loads(read(root/'result.json', result_sha))
    require(result.get('ok') is True and result.get('receipt_written') is True
            and result.get('worker_launched') is False and result.get('read_errors') == {}, 'recovery result')
    value = json.loads(json.dumps(prior))
    for path, pin in ((str(CITY/'city.toml'), result['city_pin']), (str(RECEIPT), result['receipt_pin'])):
        require(pin['sha256'] == value['pins'][path]['sha256'], 'recovered content differs: ' + path)
        require(shape(pin) == shape(value['pins'][path]), 'recovered pin shape: ' + path)
        value['pins'][path] = pin
    lineage = module(HERE/'suspension-lineage.py', LINEAGE_SHA)
    accepted = json.loads(read(Path('STOPPED_BASELINE_PATH'), 'STOPPED_BASELINE_DIGEST'))
    require(accepted['pin']['sha256'] == value['pins'][SUSPENSION]['sha256'], 'accepted suspension binding')
    record = result['suspension']
    image = lineage.image(record)
    expected = json.loads(json.dumps(lineage.image(accepted)))
    expected['updated_at'] = image['updated_at']
    require(image == expected, 'recovered suspension state differs')
    require(shape(record['pin']) == shape(value['pins'][SUSPENSION]), 'recovered suspension pin shape')
    value['pins'][SUSPENSION] = record['pin']
    return value
'''.replace('STOPPED_BASELINE_PATH', STOPPED_BASELINE).replace('STOPPED_BASELINE_DIGEST', STOPPED_BASELINE_SHA)

RECONCILE_SUBS = [
    ("ga-f37t r11: a rebind of the reviewed reconcile-predecessor.py (the ga-e0t1.14 hold) to ga-y49e; for the fourth\n"
     "successor it holds ga-4z38 instead, whose consumed attempt still routes it to the worker template.",
     "ga-gegx: a rebind of the reviewed reconcile-predecessor.py (the ga-e0t1.14 hold); for the fifth successor it\n"
     "holds ga-f37t, whose consumed attempt still routes it to the worker template."),
    ("before=bead('ga-4z38');other=bead('ga-y49e');new=bead('ga-f37t')",
     "before=bead('ga-f37t');other=bead('ga-4z38');new=bead('ga-gegx')"),
    ("ci-gi0lh", "ci-yauk5"),
    ("/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles",
     "/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles"),
    ("{'ga-4z38'}", "{'ga-f37t'}"),
    ("'ga-4z38' not in json.dumps", "'ga-f37t' not in json.dumps"),
    ("bead('ga-4z38')==before", "bead('ga-f37t')==before"),
    ("task='ga-4z38'", "task='ga-f37t'"),
    ("'bd','update','ga-4z38'", "'bd','update','ga-f37t'"),
    ("after=bead('ga-4z38')", "after=bead('ga-f37t')"),
    ("otherafter=bead('ga-y49e')", "otherafter=bead('ga-4z38')"),
    ("assert bead('ga-f37t')==new", "assert bead('ga-gegx')==new"),
    ("# No dependency edge names ga-4z38", "# No dependency edge names ga-f37t"),
    ("# ga-4z38 has no dependency edges", "# ga-f37t has no dependency edges"),
    ("/var/tmp/ga-f37t-reconcile-20260923-r1", "/var/tmp/ga-gegx-reconcile-20260925-r1"),
]
RECONCILE_NOTE = re.compile(r"NOTE=\('Failed-attempt hold .*?'\)\n", re.S)
NEW_NOTE = ("NOTE=('Failed-attempt hold 2026-09-25: session ci-yauk5 woke on 2026-09-25 and never '\n"
            "      'claimed (the window overlay skipped nudge-on-route); Core closed it stale and '\n"
            "      'its native attempt remains permanently consumed. Fresh successor ga-gegx owns '\n"
            "      'the task. This reviewed status-only reconciliation follows the ga-y49e precedent; '\n"
            "      'no route, claim, session or lifecycle change.')\n")

IDENTITY = [
    ('/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles',
     '/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles'),
    ('codex/ga-f37t-typed-route-cycles', 'codex/ga-gegx-typed-route-cycles'),
    ('/designs/ga-f37t-window', '/designs/ga-gegx-window'),
    ('gas-city-staging/ga-f37t-window', 'gas-city-staging/ga-gegx-window'),
    ('/var/tmp/ga-f37t-', '/var/tmp/ga-gegx-'),
    ('ga-f37t', 'ga-gegx'),
    ('TestGaf37tCapabilityProbeNoTests', 'TestGagegxCapabilityProbeNoTests'),
]

PREP_SUBS = [
    ("    names = sorted(set(o['name'] for o in orders['orders']))\n"
     "    assert names and len(names) == ORDER_COUNT, 'order inventory size %d' % len(names)\n",
     "    names = sorted(set(o['name'] for o in orders['orders']))\n"
     "    assert names and len(names) == ORDER_COUNT, 'order inventory size %d' % len(names)\n"
     "    # ga-gegx: keep Core's nudge-on-route order running. gc sling does not nudge warm-idle workers, so\n"
     "    # without it the routed task never reaches the worker session (the ga-4z38 and ga-f37t silent starts).\n"
     "    assert 'nudge-on-route' in names, 'nudge-on-route order missing'\n"
     "    names = [name for name in names if name != 'nudge-on-route']\n"),
]
OLD_OVERLAY = Path('/var/tmp/ga-f37t-prep-20260923-r2/city.isolated.toml')
OLD_OVERLAY_SHA = '9774a5692ec5537713b212bc3fef5c88edc34c82cb6fdcc11e949e7eefc8343e'


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
    raw = OLD_OVERLAY.read_bytes()
    assert sha(raw) == OLD_OVERLAY_SHA
    text = raw.decode()
    for old, new, count in (('ga-f37t-typed-route-cycles', 'ga-gegx-typed-route-cycles', 1),
                            ('# ga-f37t bounded one-worker window', '# ga-gegx bounded one-worker window', 1),
                            ('"nudge-on-route", ', '', 1)):
        assert text.count(old) == count, old
        text = text.replace(old, new)
    return text.encode()


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = raw.decode()
        if name == 'window-base-r11.py':
            start = text.index(OLD_RECOVERY_START)
            end = text.index(OLD_RECOVERY_END)
            assert text.count(OLD_RECOVERY_START) == 1 and start < end
            text = text[:start] + NEW_RECOVERY + text[end:]
        if name == 'reconcile-predecessor-r3.py':
            for old, new in RECONCILE_SUBS:
                assert text.count(old) >= 1, old[:60]
                text = text.replace(old, new)
            text, found = RECONCILE_NOTE.subn(NEW_NOTE, text)
            assert found == 1
            out[name] = text.encode()
            continue
        for index, phrase in enumerate(KEEP):
            text = text.replace(phrase, '\x00KEEP%d\x00' % index)
        for old, new in IDENTITY:
            text = text.replace(old, new)
        for index, phrase in enumerate(KEEP):
            text = text.replace('\x00KEEP%d\x00' % index, phrase)
        if name == 'prep-r11.py':
            for old, new in PREP_SUBS:
                assert text.count(old) == 1, old[:60]
                text = text.replace(old, new)
            overlay = sha(successor_overlay())
            for old, new in (("OVERLAY_SHA = '%s'" % OLD_OVERLAY_SHA, "OVERLAY_SHA = '%s'" % overlay),
                             ("'overlay bytes differ from the derived 9774a569'",
                              "'overlay bytes differ from the derived %s'" % overlay[:8])):
                assert text.count(old) == 1, old
                text = text.replace(old, new)
        if name == 'worker-brief.md':
            old = 'ga-y49e and ga-4z38 attempts'
            assert text.count(old) == 1
            text = text.replace(old, 'ga-y49e, ga-4z38 and ga-f37t attempts')
        if name == 'operator/PREP.sh':
            text, found = re.subn(r'# staging log below\. It is the reviewed .*?inherited from them\.\n',
                                  '# staging log below. It is the reviewed ga-f37t prep, rebound to ga-gegx with\n'
                                  '# nudge-on-route kept out of the order skip list.\n', text, flags=re.S)
            assert found == 1
        if name == 'observe-integrity-r11.py':
            text, found = re.subn(r"^RECOVER_ROOT='[^']*'\nRECOVER_SHA='[0-9a-f]{64}'\n",
                                  "RECOVER_ROOT='%s'\nRECOVER_SHA='%s'\n" % (RECOVER2_ROOT, RECOVER2_RESULT_SHA),
                                  text, flags=re.M)
            assert found == 1
        out[name] = text.encode()
    # BIND runs again for ga-gegx, so ROUTE binds the new bind-task digest (propagated below).
    route = out['route-task-r5.py'].decode()
    [ran] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", route, re.M)
    out['route-task-r5.py'] = route.replace("BIND_SHA='%s'" % ran,
                                            "BIND_SHA='%s'" % sha(out['bind-task-r3.py'])).encode()
    # The recovery result digest is evidence, never propagated.
    keep = {'observe-integrity-r11.py': {RECOVER2_RESULT_SHA}, 'window-base-r11.py': {STOPPED_BASELINE_SHA}}
    history = {name: {sha(raw)} for name, raw in files.items()}
    while True:
        for name, raw in out.items():
            history[name].add(sha(raw))
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
