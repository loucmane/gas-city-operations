"""Post one coordinator release to the live ga-f37t worker, as a reviewed job; repeatable, posted once.

Transport: the release is appended as one line to ga-f37t's own notes (`<MODE>_RELEASE ga-f37t <json>`),
in the gascity rig store the worker already reads for its claim (`bd show ga-f37t --json`, allowed by
the control policy), so the worker never reads another store. A short `gc session nudge --delivery
immediate` then wakes the waiting worker, and only an outcome of delivered passes. Immediate types the
text into the session's tmux pane now (tmux provider NudgeNow), which submits a new prompt to an idle
session and waits in Claude's own input queue if it is mid-turn; wait-idle would instead queue the
nudge for a later dispatcher delivery whenever the session is not idle within 30 seconds (Core
cmd/gc/cmd_nudge.go). proof/cli-proof.py checks both paths. The nudge text does not start with the
release prefix; the note, not the nudge, carries the release.

Input: the coordinator writes the release body, after its in-window reviews, to
~/.local/share/gas-city-staging/ga-f37t-window/release/<mode>-release.json. It is untrusted input and is
validated against the live state before anything is posted:
- source: {schema ga-f37t.source-release.v1, task, session, base, startup_proof_sha256,
  gitignore_entries, reviews}; the startup proof digest must equal the worker's evidence file, and
  the .gitignore entries must be exactly the untracked paths git reports (root-anchored);
- signing: {schema ga-f37t.signing-release.v1, task, session, base, head, tree, staged_patch_sha256,
  reviews}; head, tree and patch digest must equal the worker's candidate.json checkpoint; HEAD must be
  unchanged, the index must stage only allowed paths with no unstaged or
  untracked change, the tree must list exactly the staged index (`git ls-tree -r -z --full-tree
  <tree>` equals `git ls-files -s -z`, all at stage 0; both only read), and the staged patch must have
  the digest the candidate reviews saw. Worker and job produce the patch with the same plumbing
  command, `git diff-index --cached --patch --binary --full-index --output=<file> HEAD` (plumbing
  ignores diff.* and color config, and full object names do not depend on core.abbrev), and both hash
  the file's raw bytes. The signer independently re-verifies the tree. Worker-written files are read
  only as regular files of at most 1 MiB, checked on the open descriptor. The owned-phase runner
  captures stdout with communicate(), without truncation, so the full-tree listings arrive whole;
  proof/cli-proof.py runs the same derivation over the base tree and the worker worktree's index.
In both modes: `gc status` shows the city resumed; exactly one open session exists for the template
and it is the named session, in state active (a managed session that is not running would get a
queued wake instead of an immediate delivery, Core cmd/gc/cmd_nudge.go shouldQueueManagedNudgeWake; the
session list reports the reconciler's running states awake and active both as active, Core
internal/session normalizeInfoState); ga-f37t is in_progress and assigned to that session. The signing release
also requires the source release line to be present in the notes. The worker's visible tmux pane must
show no permission dialog or numbered menu, both before the post and right before the nudge, because
the nudge's Enter would answer one. The two captures are separate phases (pane-before-post and
pane-before-nudge). A capture that exits 0 proves the session's tmux pane exists; a dead pane kept by
remain-on-exit would still capture, and the active state and the nudge outcome cover a stopped worker.

Once and only once: before the post, no line with this release's prefix may exist in the notes. An
exclusive marker /var/tmp/ga-f37t-<mode>-release.posted is created right before the single notes append,
and the readback requires the posted line to be the LAST line with that prefix (bd joins appended notes
with one newline, and the JSON line has none), which is the line the worker takes as authoritative.
Every run uses a fresh timestamped evidence root, so a refusal before the marker leaves nothing
consumed and the job can run again after the input is fixed.

After the marker exists, a later slot posts nothing and reads no worktree state: it checks only that
the input still gives the posted line's digest, that the named session is live and holds the claim,
and that the posted line is still the last one with its prefix; then it nudges again. A failed nudge
is therefore recoverable even after the worker has started changing its worktree.

Every gc and git call runs through the owned-phase runner with the support environment
(GIT_OPTIONAL_LOCKS=0). Identity is the base active_epoch() check, valid while the worker is live.

Usage (through the source launcher): release-r11.py source|signing
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-f37t-window/window-base-r11.py')
BASE_SHA = 'f071467f5093e44002da517a534b2b1dd050812ef0c1e306ab842454eefd6129'
WINDOW = Path('/var/tmp/ga-f37t-window-20260923-r1')
INPUT = Path('/home/loucmane/.local/share/gas-city-staging/ga-f37t-window/release')
TASK = 'ga-f37t'
TEMPLATE = 'gascity/gc.implementation-worker'
BASE_COMMIT = 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88'
VAR = Path('/var/tmp')
WORKER_FILE_LIMIT = 1 << 20
ALLOWED = {'internal/sling/cycle.go', 'internal/sling/cycle_test.go', 'internal/sling/sling_core_test.go', '.gitignore'}
# Claude Code permission dialogs, plus the two markers Core's own tmux approval parser reads
# (internal/runtime/tmux/interaction.go requiresApprovalRe). The immediate nudge ends with Enter, which
# would answer a visible dialog, so a release never nudges over one.
DIALOG_MARKERS = ('Do you want to proceed?', 'Do you want to make this edit', 'Do you want to create',
                  'This command requires approval', 'Approve edits?')
# A `1. Yes` choice line, or a selection cursor on any numbered option (AskUserQuestion, the usage-limit
# menu): Enter would choose it.
CHOICE_LINES = (r'\s*[\u276f\u203a>]?\s*1\. Yes\b', r'\s*[\u276f\u203a]\s*\d+\.\s')
KEYS = dict(source={'schema', 'task', 'session', 'base', 'startup_proof_sha256', 'gitignore_entries', 'reviews'},
            signing={'schema', 'task', 'session', 'base', 'head', 'tree', 'staged_patch_sha256', 'reviews'})


def load():
    fd = os.open(BASE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1
        raw = b''
        while chunk := os.read(fd, 65536):
            raw += chunk
        assert os.fstat(fd) == s and hashlib.sha256(raw).hexdigest() == BASE_SHA, 'base source drift'
    finally:
        os.close(fd)
    w = types.ModuleType('release_base')
    w.__file__ = str(BASE)
    exec(compile(raw, str(BASE), 'exec', dont_inherit=True), w.__dict__)
    return w


def hexdigest(value, size):
    return isinstance(value, str) and len(value) == size and all(c in '0123456789abcdef' for c in value)


def line_for(mode, release):
    return '%s_RELEASE %s %s' % (mode.upper(), TASK, json.dumps(release, sort_keys=True, separators=(',', ':')))


def document(stdout):
    """One JSON document from a gc --json command: status prints it indented over many lines."""
    return json.loads(stdout)


def dialog_showing(pane):
    """True when the visible pane shows a permission dialog or its first choice line."""
    lines = pane.splitlines()
    return any(m in line for line in lines for m in DIALOG_MARKERS) or any(
        re.match(pattern, line) for line in lines for pattern in CHOICE_LINES)


def pane_clear(w, run, session, name):
    """The worker's visible pane, captured the way Core captures it (tmux -u -L <city> capture-pane -p -t
    <session_name>, internal/runtime/tmux/tmux.go runCtx and CapturePane), shows no dialog. Read-only.
    Each call is its own phase: the base refuses a phase name twice in one root."""
    pane = run(name, ['/usr/bin/tmux', '-u', '-L', 'city', 'capture-pane', '-p', '-t', session['session_name']])['stdout']
    w.require(not dialog_showing(pane), 'the worker pane shows a permission dialog or menu')


def bounded_read(path, limit):
    """A worker-written file: regular, uid 1000, one link and at most `limit` bytes, checked on the open
    descriptor (no lstat-then-open race), read without touching its atime. Raises OSError or RuntimeError."""
    # O_NONBLOCK: a FIFO planted at the path must not block the open; fstat then refuses it.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        if not (stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1 and s.st_size <= limit):
            raise RuntimeError('worker file shape or size: ' + Path(path).name)
        raw = os.read(fd, limit + 1)
        if len(raw) != s.st_size or os.fstat(fd) != s:
            raise RuntimeError('worker file changed while read: ' + Path(path).name)
    finally:
        os.close(fd)
    return raw


def worker_file(w, path):
    return bounded_read(path, WORKER_FILE_LIMIT)


def tree_entries(listing):
    """`git ls-tree -r -z` records as a set of (mode, object, path)."""
    rows = set()
    for record in listing.split('\0'):
        if record:
            meta, path = record.split('\t', 1)
            mode, _kind, name = meta.split(' ')
            rows.add((mode, name, path))
    return rows


def index_entries(listing):
    """`git ls-files -s -z` records as a set of (mode, object, path); None if any entry is unmerged."""
    rows = set()
    for record in listing.split('\0'):
        if record:
            meta, path = record.split('\t', 1)
            mode, name, number = meta.split(' ')
            if number != '0':
                return None
            rows.add((mode, name, path))
    return rows


def release_lines(notes, mode):
    return [line for line in (notes or '').split('\n') if line.startswith('%s_RELEASE %s ' % (mode.upper(), TASK))]


def validate_live(w, mode, release, run):
    """Release shape, resumed city, the one named live session and its claim. Returns (session, task)."""
    w.require(isinstance(release, dict) and set(release) == KEYS[mode], 'release fields')
    w.require(release['schema'] == 'ga-f37t.%s-release.v1' % mode and release['task'] == TASK
              and release['base'] == BASE_COMMIT, 'release identity')
    w.require(isinstance(release['reviews'], list) and len(release['reviews']) == 2
              and all(isinstance(r, str) and r for r in release['reviews']), 'release reviews')
    status = document(run('status', w.GC + ['status', '--json'])['stdout'])
    w.require(status.get('ok') is True and status.get('suspended') is False, 'city is not resumed')
    sessions = document(run('sessions', w.GC + ['session', 'list', '--json'])['stdout'])['sessions'] or []
    live = [s for s in sessions if s.get('template') == TEMPLATE and not s.get('closed')]
    w.require(len(live) == 1 and live[0]['id'] == release['session'], 'exactly the named worker session is live')
    w.require(live[0].get('state') == 'active', 'the worker session is not active')
    # gc hook --claim writes the first non-empty of session name, session id, alias, agent and template
    # (Core cmd/gc/cmd_hook.go at e6366b9e); with exactly one live session, each form names it.
    identities = ({live[0].get(k) for k in ('id', 'alias', 'name', 'session_name', 'agent_name')} | {TEMPLATE}) - {None, ''}
    [task] = json.loads(run('task', w.GC + ['--rig', 'gascity', 'bd', 'show', TASK, '--json'])['stdout'])
    w.require(task['status'] == 'in_progress' and task.get('assignee') in identities, 'task claimed by the session')
    return live[0], task


def validate_worktree(w, mode, release, run, root):
    """The worker's evidence and git state, checked only before the post."""
    git = ['/usr/bin/git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(w.WORK)]
    status = run('git-status', git + ['status', '--porcelain=v1', '-z', '--untracked-files=all'])['stdout']
    records = [r for r in status.split('\0') if r]
    if mode == 'source':
        proof = worker_file(w, w.WORK/'.gc/worker-evidence/ga-f37t/startup-proof.json')
        w.require(w.digest(proof) == release['startup_proof_sha256'], 'startup proof digest')
        w.require([r for r in records if not r.startswith('?? ')] == [], 'tracked change before source release')
        untracked = sorted('/' + r[3:] for r in records)
        entries = release['gitignore_entries']
        w.require(isinstance(entries, list) and sorted(entries) == untracked
                  and all(e.startswith('/.claude/') for e in entries), 'gitignore entries are exactly the untracked paths')
    else:
        head = run('git-head', git + ['rev-parse', 'HEAD'])['stdout'].strip()
        w.require(head == release['head'] == BASE_COMMIT and hexdigest(release['tree'], 40), 'signing head and tree')
        staged = run('git-staged-names', git + ['diff-index', '--cached', '--name-only', 'HEAD'])['stdout'].split()
        w.require(staged and set(staged) <= ALLOWED, 'staged paths')
        w.require(all(r[1] == ' ' and r[0] in 'MA' and r[3:] in ALLOWED for r in records), 'clean apart from staged paths')
        checkpoint = json.loads(worker_file(w, w.WORK/'.gc/worker-evidence/ga-f37t/candidate.json'))
        w.require(checkpoint.get('head') == release['head'] and checkpoint.get('tree') == release['tree']
                  and checkpoint.get('staged_patch_sha256') == release['staged_patch_sha256'],
                  'release differs from the worker candidate checkpoint')
        # Read-only tree derivation: the named tree lists exactly the staged index.
        listed = tree_entries(run('git-tree', git + ['ls-tree', '-r', '-z', '--full-tree', release['tree']])['stdout'])
        staged_index = index_entries(run('git-index', git + ['ls-files', '-s', '-z'])['stdout'])
        w.require(staged_index is not None and listed == staged_index, 'release tree differs from the staged index')
        run('git-staged-patch', git + ['diff-index', '--cached', '--patch', '--binary', '--full-index', '--output=' + str(root/'staged.patch'), 'HEAD'])
        patch = w.read(root/'staged.patch')
        w.require(hexdigest(release['staged_patch_sha256'], 64)
                  and w.digest(patch) == release['staged_patch_sha256'], 'staged patch digest')


def main():
    w = load()
    w.require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound source launcher required')
    w.read(Path(__file__), _SOURCE_SHA)
    w.require(len(sys.argv) == 2 and sys.argv[1] in KEYS, 'mode: source or signing')
    mode = sys.argv[1]
    marker = VAR/('ga-f37t-%s-release.posted' % mode)
    if mode == 'signing':
        w.require((VAR/'ga-f37t-source-release.posted').exists(), 'no source release posted')
    b, o, owned = w.load_support()
    w.require((WINDOW/'suspension-city-resume-event.json').exists()
              and not (WINDOW/'suspension-city-suspend-intent.json').exists(), 'window is not live')
    w.ROOT = WINDOW
    w.active_epoch(o)
    w.require((INPUT/(mode + '-release.json')).lstat().st_size < 8192, 'release input size')
    raw = w.read(INPUT/(mode + '-release.json'))
    release = json.loads(raw)
    root = VAR/('ga-f37t-%s-release-%s' % (mode, datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    root.mkdir(mode=0o700)
    w.ROOT = root
    w.save('input.json', dict(mode=mode, release=release))

    def run(name, args, expected=(0,)):
        return w.phase(name, args, b, owned, expected=expected, timeout=90)
    session, task = validate_live(w, mode, release, run)
    pane_clear(w, run, session, 'pane-before-post')
    line = line_for(mode, release)
    if mode == 'signing':
        w.require(release_lines(task.get('notes'), 'source'), 'source release line absent from the notes')
    if marker.exists():
        # Already posted: no worktree read, no post; verify the posted line, then only nudge again.
        w.require(json.loads(w.read(marker))['line_sha256'] == w.digest(line.encode()), 'posted release differs')
        posted = False
    else:
        validate_worktree(w, mode, release, run, root)
        w.require(not release_lines(task.get('notes'), mode), 'a %s release line already exists' % mode)
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(dict(root=str(root), line_sha256=w.digest(line.encode())), out)
            out.flush()
            os.fsync(out.fileno())
        run('post', w.GC + ['--rig', 'gascity', 'bd', 'update', TASK, '--append-notes', line])
        posted = True
    [task] = json.loads(run('readback', w.GC + ['--rig', 'gascity', 'bd', 'show', TASK, '--json'])['stdout'])
    lines = release_lines(task.get('notes'), mode)
    w.require(lines and lines[-1] == line, 'the release line is the last one with its prefix')
    pane_clear(w, run, session, 'pane-before-nudge')
    nudge = document(run('nudge', w.GC + ['session', 'nudge', session['id'],
                                            'Coordinator note for ga-f37t: a new %s release line is in the task notes. '
                                            'Read the latest %s_RELEASE line with /home/loucmane/gascity/bin/bd show %s --json.'
                                            % (mode, mode.upper(), TASK),
                                            '--delivery', 'immediate', '--json'])['stdout'])
    w.require(nudge.get('ok') is True and nudge.get('outcome') == 'delivered', 'nudge not delivered')
    w.ROOT = WINDOW
    w.active_epoch(o)
    w.ROOT = root
    w.complete_containment()
    result = dict(ok=True, mode=mode, posted_now=posted, session=session['id'], nudge=nudge.get('outcome'),
                  line_sha256=w.digest(line.encode()))
    w.save('result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
