"""Successor derivation (s1 to s5): derive the ga-f37t window package from the reviewed ga-4z38 r14 package.

  python3 -B make_successor.py <output package dir>

ga-4z38 r14 (69cdc6b6, two SOURCE_PASS) reached TERMINAL on 2026-09-24, but its one-shot attempt
(session ci-gi0lh) never claimed and is consumed. ga-f37t is the fourth successor, with a fresh worktree
/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles at Core e6366b9e.

1. Every source is read from the r14 commit object (git blobs), never from a working tree.
2. Kept: every executable, operator wrapper and the worker brief. Dropped: README.md, the tests and the
   generators (their provenance chains are ga-4z38-specific; test_successor.py replaces them), and the
   INSPECTOR-BUILD wrapper and builder (the inspector is built; its path is reused).
3. RECONCILE is retargeted first (RECONCILE_SUBS): it holds ga-4z38, whose consumed attempt is session
   ci-gi0lh (state stale-session), instead of ga-y49e; ga-y49e (already blocked) is the unrelated
   predecessor that must stay exact.
4. Global identity substitutions (IDENTITY), in order, with the rebuilt inspector path protected.
5. Digest propagation to a fixed point, as in make_epoch_r13/r14. ROUTE's BIND_SHA is the one provenance
   pin kept: since s3 r2 it is the digest of the bind-task that ran (item 8), never a propagated one.
6. s1 (912e4d48) admitted only PREP. The ga-f37t PREP job passed on 2026-09-24 at 22:05:00Z
   (root /var/tmp/ga-f37t-prep-20260923-r2); in s1 the window-base-r11.py pins still carried the ga-4z38
   PREP digests under the renamed path.
7. s2 adds, from the s1 reviews and the PREP outputs:
   - S2_PINS: window-base-r11.py pins the ga-f37t PREP outputs (overlay, receipt image, revision, result);
   - WATCH captures each live session's pane with the release job's exact read-only form, so a silent
     worker start can be diagnosed before Core reaps the session (ga-4z38 left no capture);
   - HISTORY: ga-4z38 events stay attributed to ga-4z38; PRE_SUBS reword the PREP and RECONCILE wrapper
     headers and add ga-4z38 to the brief's consumed attempts; the brief's compile-probe test name follows
     the new id; proof/ is dropped (it never runs in a job and pointed at ga-4z38 roots).
8. s3 (after OBSERVE refused at s2 r2) adds S3_SUBS, the restore disposition in window-base-r11.py, and
   the fresh integrity root S3_ROOT. s3 r2 keeps ROUTE's BIND_SHA at BIND_RAN_SHA, the bind-task digest
   BIND ran with at s2 r2 (36b4158d); BIND never runs again, while BIND.sh and bind-task-r3.py carry the
   propagated digests. s3 r3 and s3 r4 change only documentation, comments and tests (comment edits move
   digests).
9. s4 (after OBSERVE refused at s3 r4; operator chose the narrow disposition) adds
   approved_coordinator_cache_image, chained last, for the pack cache .git time change a coordinator
   workflow.py call caused at 22:39:06Z, and moves the integrity root to -20260925-r4 (r2 and r3 were
   consumed by refused OBSERVE runs).
10. s5 (operator chose it over waiting for a FRESHEN opening) adds account_read_times to window-base,
   calls it in both preservation layers (READ_TIMES_CALL), and removes PREFLIGHT's FRESHEN gate
   (PREFLIGHT_FRESHEN). s5 r2 adds the PREFLIGHT start gate stable_read_times (PREFLIGHT_GATE) for the
   access-time checks outside the accounting, and leaves runtime children unwalked.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

R14 = '69cdc6b6d5d32e61746c0b0e8f50cb66420ae882'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
DROP = ('README.md', 'test_prep.py', 'test_round2a.py', 'test_round2b.py', 'operator/INSPECTOR-BUILD.sh')
DROP_DIRS = ('generators/', 'inspector/', 'proof/')
# ga-4z38 history kept verbatim by the rename (placeholders), so no event is misattributed to ga-f37t.
HISTORY = ['r2 (after job ga-4z38-prep refused fail-closed at 16:06:01Z; root -r1 preserved):',
           '# ga-4z38 disposition, for independent review:',
           '# ga-4z38 r13 disposition, for independent review:']
# Applied to the r14 bytes before the rename.
PRE_SUBS = {
    'operator/PREP.sh': [
        ("# staging log below. r2 followed the fail-closed refusal of the r1 job (root -r1 preserved); r3 follows\n"
         "# the review HOLD of r2, which never ran (root -r2 was never created).\n",
         "# staging log below. It is the reviewed ga-4z38 prep r3 rebound to ga-f37t; the r1 refusal and the r2\n"
         "# HOLD belong to the ga-4z38 jobs, and the -r2 root name is inherited from them.\n", 1)],
    'operator/RECONCILE.sh': [
        ("the consumed predecessor ga-y49e\n", "the consumed predecessor ga-4z38-KEEP\n", 1)],
    'worker-brief.md': [
        ("The failed ga-5ot6, ga-e0t1.14 and\nga-y49e attempts, their artifacts and worktrees remain historical evidence, never\n"
         "retry targets.",
         "The failed ga-5ot6, ga-e0t1.14,\nga-y49e and ga-4z38-KEEP attempts, their artifacts and worktrees remain historical evidence,\n"
         "never retry targets.", 1),
        ("TestGa4z38CapabilityProbeNoTests", "TestGaf37tCapabilityProbeNoTests", 1)],
    'watch-r11.py': [
        ("""    run('tmux', ['/usr/bin/tmux', '-L', 'city', 'list-panes', '-a', '-F', '#{session_name} #{pane_pid} #{pane_dead}'],
        expected=(0, 1))
""",
         """    run('tmux', ['/usr/bin/tmux', '-L', 'city', 'list-panes', '-a', '-F', '#{session_name} #{pane_pid} #{pane_dead}'],
        expected=(0, 1))
    # ga-f37t: the visible pane of each live session, captured the way Core captures it (release-r11
    # pane_clear form), read-only. The ga-4z38-KEEP worker went silent and was reaped before any capture; the
    # early WATCH slots after RESUME keep the screen as evidence. Exit 1 (pane gone) is recorded, not fatal,
    # and a listed session without a string session_name is recorded, never captured.
    unnamed = []
    for index, live in enumerate(sessions.get('sessions') or []):
        name = live.get('session_name') if isinstance(live, dict) else None
        if not isinstance(name, str) or not name:
            unnamed.append(index)
            continue
        run('pane-%d' % index, ['/usr/bin/tmux', '-u', '-L', 'city', 'capture-pane', '-p', '-t', name],
            expected=(0, 1))
    w.save('pane-unnamed.json', unnamed)
""", 1)],
}
# s3: OBSERVE at s2 r2 refused 'accepted baseline drift' (2026-09-24 22:24:14Z). The ga-4z38 rig-suspend
# step (21:50:20Z) wrote a new suspension-state.json, and the ga-4z38 RESTORE (21:53:20Z) rewrote
# city.toml and receipt.json with their P6 content (new inode and times). TERMINAL (21:54:18Z) wrote only
# its own record, which holds all three entries. The P6 accepted image can never match a restored city.
# The disposition takes exactly those three pin entries from the reviewed ga-4z38 TERMINAL record, which
# equals the live pins, cache, protected trees and host except for atime (checked 22:3xZ).
TERMINAL_RECORD = '/var/tmp/ga-4z38-terminal-20260923-r1/observed-after.json'
TERMINAL_RECORD_SHA = '04ad8d3e2c3b32b43b93142190a0013ffc9f068381c63fd05a6526a975d2aa53'
RESTORE_DISPOSITION = '''
RESTORED_PINS = {
    '/home/loucmane/gascity/city/city.toml': 'same-content',
    '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json': 'same-content',
    '/home/loucmane/gascity/city/.gc/runtime/suspension-state.json':
        'a4bcfdc35d60960fe22dfd3b58b6af8f37f09dcd444167c23779157ae3a31056'}

def approved_restore_image(prior):
    # ga-f37t s3 disposition, for independent review: the ga-4z38 window restored the city exactly
    # (RESTORE 2026-09-24 21:53:20Z, TERMINAL 21:54:18Z). RESTORE rewrote city.toml and receipt.json with
    # their accepted content, so only their inode and times changed. The window's reviewed rig-suspend
    # step (21:50:20Z) wrote a new suspension-state.json, which TERMINAL recorded. The P6 image therefore
    # cannot match any restored city. These three pin entries, and only these, are taken from the reviewed TERMINAL record (pinned by digest); the two
    # rewritten files must keep exactly their accepted content digest, and the suspension state must be the
    # one TERMINAL recorded. Every other pin, the cache, the protected trees and the host stay compared as
    # before. Never reuse this for fresh drift.
    record = json.loads(read(Path(\'''' + TERMINAL_RECORD + '''\'), \'''' + TERMINAL_RECORD_SHA + '''\'))
    value = json.loads(json.dumps(prior))
    require(set(RESTORED_PINS) <= set(value['pins']) and set(RESTORED_PINS) <= set(record['pins']),
            'restore disposition pin set')
    for path, rule in RESTORED_PINS.items():
        after = record['pins'][path]
        if rule == 'same-content':
            require(after['sha256'] == value['pins'][path]['sha256'], 'restored content differs: ' + path)
        else:
            require(after['sha256'] == rule, 'restored suspension state differs')
        require(shape(after) == shape(value['pins'][path]), 'restore pin shape drift')
        value['pins'][path] = after
    return value
'''
COORDINATOR_CACHE = '''
def approved_coordinator_cache_image(prior):
    # ga-f37t s4 disposition, operator-approved 2026-09-25, for independent review: at 2026-09-24
    # 22:39:03Z the coordinator ran the canonical workflow.py coordinate note, whose ownership check read
    # the Bead through bd without GIT_OPTIONAL_LOCKS=0 before it refused. That advanced only the pack
    # cache repo's .git directory mtime and ctime (22:39:06.179Z). The s3 r4 OBSERVE refusal found every
    # other cache, pin, protected-tree and host value equal. From that refusal (22:50:43Z) until TERMINAL,
    # no workflow.py call of any verb (including post-commit log or discharge) and no bd or gc call
    # without GIT_OPTIONAL_LOCKS=0 runs, and a read-only lstat before OBSERVE confirms both times still
    # equal the recorded value. Never reuse this for fresh drift.
    value=json.loads(json.dumps(prior))
    entry=value['cache']['inventory'][CACHE_DIRECTORY]
    for key in ('mtime_ns','ctime_ns'):
        require(entry[key] == 1790178703592685769, 'coordinator cache exception preimage')
        entry[key] = 1790289546179167691
    return value
'''
S3_SUBS = {
    'window-base-r11.py': [
        ('\ndef directories(o):', RESTORE_DISPOSITION + '\ndef directories(o):'),
        ('if dependency_image(approved_epoch_image(approved_historical_image(prior), h)) != dependency_image(value):',
         'if dependency_image(approved_restore_image(approved_epoch_image(approved_historical_image(prior), h))) != dependency_image(value):'),
        # s4: the coordinator cache disposition, chained last.
        ('\ndef directories(o):', COORDINATOR_CACHE + '\ndef directories(o):'),
        ('if dependency_image(approved_restore_image(approved_epoch_image(approved_historical_image(prior), h))) != dependency_image(value):',
         'if dependency_image(approved_coordinator_cache_image(approved_restore_image(approved_epoch_image(approved_historical_image(prior), h)))) != dependency_image(value):')],
    'observe-integrity-r11.py': [
        ('M5 baseline. It admits the live state against the P6 accepted snapshot plus the reviewed disposition,',
         'M5 baseline. It admits the live state against the P6 accepted snapshot plus the reviewed dispositions,'),
        ('    # snapshot below and admitted against the P6 accepted state.',
         '    # snapshot below and admitted against the recorded TERMINAL entry (approved_restore_image).'),
        ('    # with the reviewed disposition (approved_historical_image) and the accepted provider pins.',
         '    # with the reviewed dispositions approved_historical_image, approved_epoch_image,\n'
         '    # approved_restore_image and approved_coordinator_cache_image, and the accepted provider pins.')],
}
# s5 (operator chose it over waiting for a FRESHEN opening): reads may advance access times, and the
# window accounts them instead of requiring every compared object to be refreshed beforehand.
READ_TIMES = '''
def account_read_times(a, z, window):
    # ga-f37t s5 disposition, operator-approved 2026-09-25 in place of FRESHEN, for independent review:
    # a read may advance an access time and nothing else. For every metadata record outside the cache
    # (cache-atime-policy-r1 accounts that) whose other fields are all equal, a changed atime_ns must
    # move forward, lie inside this comparison's observed clock window, and be a change Linux relatime
    # can write: the old access time was not newer than the modification or change time, or the new one
    # is at least 24 hours later. Only the comparison copy is aligned; both observations keep every
    # timestamp and the changes are returned as evidence. Once a lifecycle transition exists, the
    # suspension state stays governed by the suspension lineage and is not aligned here. Every other
    # field is still compared exactly.
    lifecycle = bool(list(ROOT.glob('suspension-*-intent.json')))
    changes = []
    def walk(x, y, path):
        if not (isinstance(x, dict) and isinstance(y, dict)):
            return
        if 'atime_ns' in x and 'atime_ns' in y:
            old, new = x['atime_ns'], y['atime_ns']
            require(type(old) is int and type(new) is int, 'access timestamp type')
            rest = {k: v for k, v in x.items() if k != 'atime_ns'}
            if old != new and rest == {k: v for k, v in y.items() if k != 'atime_ns'}:
                where = '/'.join(path)
                require(new > old and window['earliest_ns'] <= new <= window['latest_ns'],
                        'access time outside the observed window: ' + where)
                require(old <= max(x['mtime_ns'], x['ctime_ns'])
                        or new // 10**9 - old // 10**9 >= 24 * 3600,
                        'access time change relatime cannot write: ' + where)
                y['atime_ns'] = old
                changes.append(dict(path=list(path), before_ns=old, after_ns=new))
            return
        for key in x:
            if key not in y or (not path and key in ('cache', 'cache_access_clock', 'cache_access_mounts')):
                continue
            if lifecycle and path == ('pins',) and key == str(SUSPENSION):
                continue
            # R6 compares runtime children by identity only (directory_preservation); leave them alone.
            if path == ('directories',) and key == 'runtime_children':
                continue
            walk(x[key], y[key], path + (key,))
    walk(a, z, ())
    return changes

def stable_read_times(paths=None, now_ns=None):
    # ga-f37t s5 start gate, for independent review: three checks still compare access times exactly
    # outside account_read_times. The suspension lineage compares the PREFLIGHT baseline record until the
    # first transition. The route projection compares the city .beads directory mirror. And
    # directory_preservation compares the city root and provisioning directory after their renames.
    # FRESHEN used to keep those stable. Now PREFLIGHT requires each to have an access time newer than its
    # modification and change times and under 20 hours old, so Linux relatime cannot rewrite it within
    # the four-hour window bound. The gate reads metadata only.
    now_ns = time.time_ns() if now_ns is None else now_ns
    for path in (SUSPENSION, CITY, CITY/'.beads', RECEIPT.parent) if paths is None else paths:
        s = os.lstat(path)
        require(s.st_atime_ns > max(s.st_mtime_ns, s.st_ctime_ns)
                and 0 <= now_ns - s.st_atime_ns < 20 * 3600 * 10**9,
                'access time not stable for the window: ' + str(path))
'''
PREFLIGHT_GATE = ("        require(result['stdout']=='','worker not clean')\n",
                  "        require(result['stdout']=='','worker not clean')\n        stable_read_times()\n")
READ_TIMES_CALL = ("    accounting['mounts']=mounts\n",
                   "    accounting['mounts']=mounts\n"
                   "    # s5: reads may advance access times outside the cache too (window-base account_read_times).\n"
                   "    accounting['read_time_changes']=w.account_read_times(a,z,accounting['window'])\n")
S3_SUBS['window-base-r11.py'] += [
    ('\ndef directories(o):', READ_TIMES + '\ndef directories(o):'),
    ('    # Historical reuse alone excludes read timestamps. Immediate preservation\n'
     '    # still compares every metadata field, including atime.\n',
     '    # Historical reuse alone excludes read timestamps. Immediate preservation compares every\n'
     '    # metadata field; access times only as account_read_times admits (s5).\n'),
    PREFLIGHT_GATE]
S3_SUBS['window-r11.py'] = [READ_TIMES_CALL]
S3_SUBS['window-obs-r11.py'] = [READ_TIMES_CALL]
PREFLIGHT_FRESHEN = (
    '# An object already fresh at FRESHEN may be up to 19 hours old; it must stay under 24\n'
    '# hours until T0 plus four hours, so PREFLIGHT must follow a FRESHEN pass within 45 min.\n'
    'find /var/tmp -maxdepth 2 -user 1000 -path "/var/tmp/ga-f37t-freshen-*/result.json" -mmin -45 '
    '-exec grep -l \'"ok": true\' {} + | xargs -r grep -l "$FRESHEN_SHA" | grep -q . || '
    '{ echo "== STOP: no FRESHEN pass in the last 45 minutes"; echo "== end"; exit 1; }\n',
    '# s5: the window accounts read-only access-time changes (window-base account_read_times), so no\n'
    '# FRESHEN pass is required before PREFLIGHT.\n')
# The refused s2 r2 and s3 r4 OBSERVE runs consumed integrity roots r2 and r3; s4 uses a fresh r4.
S3_ROOT = ('/var/tmp/ga-f37t-integrity-20260924-r2', '/var/tmp/ga-f37t-integrity-20260925-r4')
# Applied after the rename: the ga-f37t PREP outputs (job ga-f37t-prep, 22:05:00Z).
S2_PINS = {
    'window-base-r11.py': [
        ('5f3b60e1c1e391b5a1f66de62a2e767ea226570ce7549c6dfb526cd072e6530d',
         '9774a5692ec5537713b212bc3fef5c88edc34c82cb6fdcc11e949e7eefc8343e'),
        ('392ea0b6c0a9a3c0cb88971b04c45b1326de50e9ea35c4e63c83bf1a602a3e46',
         '0876abb88879ce546502e34228a710a60a69a2b20f85791b3c9ce9f0ebce2451'),
        ('6b31d83ab039cd1cba61ac77845fe71f4d6ce8b06f8a775f07df1e42d6bfd6ba',
         '758aa29b154babfe18468c6e2f650e04c23be18f9ba0c4a2bb4ccb087553d87f'),
        ('c0d1959c4e0df67e8f02b8716f43f2adf542c9d2b358d75f4027d92f91480c03',
         '0c071f7c97706059792bdec16ce3de952bf9114159ba493b5baad62d71e5d6d1')]}
PROTECT = '/var/tmp/ga-4z38-platform-inspector-20260924-r1'
PLACEHOLDER = '\x00INSPECTOR\x00'
NOTE_OLD = ("NOTE=('Failed-attempt hold 2026-09-23: session ci-b24ev failed-create on '\n"
            "      '2026-09-21 (the positional-prompt defect, since fixed and live through M5); '\n"
            "      'its native attempt remains permanently consumed. Fresh successor ga-4z38 owns '\n"
            "      'the remaining implementation proof. This task is blocked pending successor '\n")
NOTE_NEW = ("NOTE=('Failed-attempt hold 2026-09-25: session ci-gi0lh woke on 2026-09-24 and never '\n"
            "      'claimed; Core closed it stale (cause undetermined, no pane captured); '\n"
            "      'its native attempt remains permanently consumed. Fresh successor ga-f37t owns '\n"
            "      'the remaining implementation proof. This task is blocked pending successor '\n")
# Applied to reconcile-predecessor-r3.py before the global identity substitutions. PRED is a placeholder
# for the held predecessor, so the global ga-4z38 -> ga-f37t rename cannot touch it.
PRED = '\x00PRED\x00'
RECONCILE_SUBS = [
    ("(the ga-e0t1.14 hold) to ga-y49e, whose\nconsumed attempt",
     "(the ga-e0t1.14 hold) to ga-y49e; for the fourth\nsuccessor it holds " + PRED + " instead, whose consumed attempt", 1),
    (NOTE_OLD, NOTE_NEW.replace('ga-f37t', '\x00SUCC\x00'), 1),
    ("'This reviewed status-only reconciliation follows the ga-e0t1.14 precedent; '",
     "'This reviewed status-only reconciliation follows the ga-y49e precedent; '", 1),
    ("other=bead('ga-e0t1.14')", "other=bead('ga-y49e-HOLD')", 1),
    ("otherafter=bead('ga-e0t1.14')", "otherafter=bead('ga-y49e-HOLD')", 1),
    ("'ga-y49e'", "'" + PRED + "'", None),
    ('ga-y49e has no dependency edges', PRED + ' has no dependency edges', 1),
    ('No dependency edge names ga-y49e', 'No dependency edge names ' + PRED, 1),
    ("'ci-b24ev'", "'ci-gi0lh'", None),
    ("closed[0]['metadata']['state']=='failed-create'", "closed[0]['metadata']['state']=='stale-session'", 1),
    ("'/home/loucmane/gascity-core-worktrees/ga-y49e-typed-route-cycles'",
     "'/home/loucmane/gascity-core-worktrees/" + PRED + "-typed-route-cycles'", 1),
]
IDENTITY = [
    ('/designs/ga-4z38-window', '/designs/ga-f37t-window'),
    ('/gas-city-staging/ga-4z38-window', '/gas-city-staging/ga-f37t-window'),
    ('/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles',
     '/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles'),
    ('codex/ga-4z38-typed-route-cycles', 'codex/ga-f37t-typed-route-cycles'),
    ('/var/tmp/ga-4z38-', '/var/tmp/ga-f37t-'),
    ('ga-4z38', 'ga-f37t'),
]
DIGEST = re.compile(r'[0-9a-f]{64}')
R12_BIND_SHA = '591cf9b58cfa86d8cee18af4db8fbcf03408c8932dcb79f17e6c9096969149fa'
# The bind-task digest that BIND ran with at s2 r2 (recorded as executor_sha256 in
# /var/tmp/ga-f37t-bind-20260923-r1/binding-intent.json).
BIND_RAN_SHA = '159452692546d4d08512d2b1a11a2b479bc1438e40e83fe009d05427a110417a'
# PREP pins the exact overlay it generates. The reviewed ga-4z38 overlay (5f3b60e1, written by the ga-4z38
# PREP job) differs from the ga-f37t one only in the worker's work_dir and the header comment, so the
# expected ga-f37t overlay is derived from those bytes and its digest replaces OVERLAY_SHA.
OLD_OVERLAY = Path('/var/tmp/ga-4z38-prep-20260923-r2/city.isolated.toml')
OLD_OVERLAY_SHA = '5f3b60e1c1e391b5a1f66de62a2e767ea226570ce7549c6dfb526cd072e6530d'
OVERLAY_SUBS = [
    (b'\n# ga-4z38 bounded one-worker window; restore exact preserved baseline.\n',
     b'\n# ga-f37t bounded one-worker window; restore exact preserved baseline.\n'),
    (b'work_dir = "/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles"\n',
     b'work_dir = "/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles"\n'),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def successor_overlay():
    import tomllib
    raw = OLD_OVERLAY.read_bytes()
    assert sha(raw) == OLD_OVERLAY_SHA, 'reviewed ga-4z38 overlay drift'
    for old, new in OVERLAY_SUBS:
        assert raw.count(old) == 1, old
        raw = raw.replace(old, new)
    assert b'ga-4z38' not in raw
    tomllib.loads(raw.decode())
    return raw


def git(*args):
    return subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', WORKTREE, *args],
                          capture_output=True, check=True).stdout


def sources():
    names = [p for p in git('ls-tree', '-r', '-z', '--name-only', R14, '--', PREFIX).decode().split('\0') if p]
    out = {}
    for path in names:
        name = path[len(PREFIX):]
        if name in DROP or name.startswith(DROP_DIRS):
            continue
        out[name] = git('show', R14 + ':' + path)
    return out


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = raw.decode()
        for old, new, count in PRE_SUBS.get(name, ()):
            assert text.count(old) == count, (name, old[:60])
            text = text.replace(old, new)
        for index, phrase in enumerate(HISTORY):
            text = text.replace(phrase, '\x00HISTORY%d\x00' % index)
        if name == 'reconcile-predecessor-r3.py':
            for old, new, count in RECONCILE_SUBS:
                found = text.count(old)
                assert found >= 1 and (count is None or found == count), (name, old[:60], found)
                text = text.replace(old, new)
        text = text.replace(PROTECT, PLACEHOLDER)
        for old, new in IDENTITY:
            text = text.replace(old, new)
        text = (text.replace(PLACEHOLDER, PROTECT).replace(PRED, 'ga-4z38')
                .replace('\x00SUCC\x00', 'ga-f37t').replace('ga-y49e-HOLD', 'ga-y49e')
                .replace('ga-f37t-KEEP', 'ga-4z38'))
        for index, phrase in enumerate(HISTORY):
            text = text.replace('\x00HISTORY%d\x00' % index, phrase)
        for old, new in S2_PINS.get(name, ()):
            assert text.count(old) == 1, (name, old[:12])
            text = text.replace(old, new)
        for old, new in S3_SUBS.get(name, ()):
            assert text.count(old) == 1, (name, old[:40])
            text = text.replace(old, new)
        text = text.replace(S3_ROOT[0], S3_ROOT[1])
        if name == 'operator/PREFLIGHT.sh':
            text, found = re.subn(r'^FRESHEN_SHA=[0-9a-f]{64}\n', '', text, flags=re.M)
            assert found == 1
            assert text.count(PREFLIGHT_FRESHEN[0]) == 1
            text = text.replace(*PREFLIGHT_FRESHEN)
        if name == 'prep-r11.py':
            overlay = sha(successor_overlay())
            for old, new in (("OVERLAY_SHA = '%s'" % OLD_OVERLAY_SHA, "OVERLAY_SHA = '%s'" % overlay),
                             ("'overlay bytes differ from the reviewed 5f3b60e1'",
                              "'overlay bytes differ from the derived %s'" % overlay[:8])):
                assert text.count(old) == 1, old
                text = text.replace(old, new)
        out[name] = text.encode()
    # BIND ran once for ga-f37t, at s2 r2 (36b4158d), and never runs again; its record carries the digest
    # of the bind-task that ran. ROUTE's BIND_SHA is therefore a provenance pin to that digest (as r13 and
    # r14 kept the ga-4z38 r12 one), never propagated from later bind-task bytes.
    route = out['route-task-r5.py'].decode()
    old = "BIND_SHA='%s'" % R12_BIND_SHA
    assert route.count(old) == 1
    out['route-task-r5.py'] = route.replace(old, "BIND_SHA='%s'" % BIND_RAN_SHA).encode()
    keep = {'route-task-r5.py': {BIND_RAN_SHA}}
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
            return add_watch_slots(out)


WATCH_SLOTS = 12


def add_watch_slots(out):
    """Twelve WATCH slots instead of eight: the early pane-capture cadence needs about five slots on top of
    the baseline, the startup, candidate and signature observations and the post-CLOSE WATCH. WATCH-9..12 are
    WATCH-8 with only the slot number changed; the runner pins each wrapper by its own digest in the job
    file, and no package file pins a WATCH wrapper."""
    for n in range(1, 9):
        name = 'operator/WATCH-%d.sh' % n
        text = out[name].decode()
        old = '# Slot %d of 8: ' % n
        assert text.count(old) == 1, name
        out[name] = text.replace(old, '# Slot %d of %d: ' % (n, WATCH_SLOTS)).encode()
    base = out['operator/WATCH-8.sh'].decode()
    for n in range(9, WATCH_SLOTS + 1):
        text = base
        for old, new in (('# Slot 8 of %d: ' % WATCH_SLOTS, '# Slot %d of %d: ' % (n, WATCH_SLOTS)),
                         ('WATCH-8.sh <reviewed commit>', 'WATCH-%d.sh <reviewed commit>' % n),
                         ('/watch-8-<timestamp>.txt', '/watch-%d-<timestamp>.txt' % n),
                         ('LOG="$S/watch-8-', 'LOG="$S/watch-%d-' % n),
                         ('== WATCH-8 REFUSED', '== WATCH-%d REFUSED' % n),
                         ('== WATCH-8 PASS', '== WATCH-%d PASS' % n)):
            assert text.count(old) == 1, (n, old)
            text = text.replace(old, new)
        out['operator/WATCH-%d.sh' % n] = text.encode()
    return out


def main(output):
    files = sources()
    out = rebind(files)
    root = Path(output)
    for name, data in sorted(out.items()):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(len(out), 'files written to', root)


if __name__ == '__main__':
    main(*sys.argv[1:])
