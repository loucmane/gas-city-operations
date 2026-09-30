"""Eighth successor s1: derive the ga-n12k window package from the reviewed ga-qcwl package.

  python3 -B make_successor.py <output package dir>

ga-n12k continues ga-qcwl from the checkpoint of the S4 worker ci-bfdvp (operator decision 2026-09-25:
continue from checkpoint in a new Bead and a fresh worktree). The S4 window (ga-qcwl-window s2 20e9ba1e) ran
clean BIND through TERMINAL on the same host epoch and image, so the package is that window rebound to the new
task:

1. Every source is read from the ga-qcwl s2 commit object (20e9ba1e), never from a working tree.
2. Dropped: README.md, the tests and the generator (this package's own replace them).
3. Identity: ga-qcwl becomes ga-n12k in paths, roots, worktree (ga-n12k-provider-pins-finish), branch, staging
   path, evidence path, probe test and Bead id. The r7 history note in prep stays attributed (KEEP).
4. Host epoch, accepted image (P7 snapshot), receipt staging, integrity binding, base b6843d3f and the source
   release's allowed set (21 paths) are unchanged: TERMINAL of the S4 window verified the same epoch and image.
5. PREP r8: the ga-qcwl PREP overlay (449346e3) with only the work dir and header replaced. The window's PREP
   pins stay at the ga-qcwl outputs until s2 re-pins them from a fresh PREP run (they fail closed until then).
6. The brief's task section is replaced: re-apply the preserved checkpoint with native edits, add the missing
   dispatch gate RED, classify the two platforminstall metadata failures against the base, then the usual
   checkpoint, candidate and signing. It also asks the worker to spend context sparingly.
7. Digest propagation to a fixed point.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = '20e9ba1eeb434bdf92dfbee2c94c70ee919dbf28'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-qcwl-window/'
DROP = {'README.md', 'test_successor.py'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

KEEP = ['r7 (ga-qcwl, ga-e0t1.15 S4)']

IDENTITY = [
    ('/home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins',
     '/home/loucmane/gascity-core-worktrees/ga-n12k-provider-pins-finish'),
    ('codex/ga-qcwl-provider-pins', 'codex/ga-n12k-provider-pins-finish'),
    ('/designs/ga-qcwl-window', '/designs/ga-n12k-window'),
    ('gas-city-staging/ga-qcwl-window', 'gas-city-staging/ga-n12k-window'),
    ('/var/tmp/ga-qcwl-', '/var/tmp/ga-n12k-'),
    ('TestGaqcwlCapabilityProbeNoTests', 'TestGan12kCapabilityProbeNoTests'),
    ('ga-qcwl', 'ga-n12k'),
]

PREP_OVERLAY = Path('/var/tmp/ga-qcwl-prep-20260925-r1/city.isolated.toml')
PREP_OVERLAY_SHA = '449346e33f73c1882dfd52e3caa0dfc8066ddfdb6eb4ef6c422603be60e817ac'
CHECKPOINT = '/home/loucmane/.local/share/gas-city-staging/ga-qcwl-window/checkpoint-20260925'
CHECKPOINT_PATCH_SHA = '01f8b8af486ebc9a024a5247a3a580a54e5685a00b1fb4ca50f422edcef60caa'
# s2: the ga-n12k PREP outputs (job ga-n12k-s1-prep at ac340176, PREP PASS 2026-09-25 21:13Z) replace the ga-qcwl
# ones in window-base: the isolated overlay, the final receipt image, the isolated revision and the result record.
# The isolated order list is byte-identical (b57082cf), so the nudge pins in pins() stay.
PREP_ROOT = Path('/var/tmp/ga-n12k-prep-20260925-r1')
PREP_PINS = [
    ('449346e33f73c1882dfd52e3caa0dfc8066ddfdb6eb4ef6c422603be60e817ac',
     '25026cfdd312016ac8d883c5c0b75148ea9dca6f17e40a4abaac7ab9f3d1243c'),
    ('c1761144d7ab3b1d557e097902d681325b647324957df56eff4ee8afa77f78eb',
     '58973d2e24328a1539c53196ff6dcd7e69f9ae2ca8e575557be35eb069827134'),
    ('2de85e1eb06c2b4898aa49896d0683bdd22b77597b8402311dcd956850d93348',
     '5ca6886cb8877386e62c98bf972846a5f04136658e556588ea913e4bbbb1aecd'),
    ('9d59a0b4c2c3ce2d12668039559b0b11eb60f45e625a98996185573816744c92',
     'd6cbdf3e5705ff585ff1c94c3f6f64a0544751d0f3df24bdf6fd43cb1ec7f97e'),
]
ORDERS_SHA = 'b57082cf8c065a460e4b8414c380c4fdedde6cc83a3b5426206aa4f73f0d02a1'
# s2 r2: the accepted image is the S4 window's TERMINAL observed-after record (see window_base_accepted).
ACCEPTED_TERMINAL = '/var/tmp/ga-qcwl-terminal-20260923-r1/observed-after.json'
ACCEPTED_TERMINAL_SHA = 'a7cdb0f8577f71a68b65efc5a1b993427e97a3c49a88a65818bc5714f3de7012'


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
    for old, new in (('ga-qcwl-provider-pins', 'ga-n12k-provider-pins-finish'),
                     ('# ga-qcwl bounded one-worker window', '# ga-n12k bounded one-worker window')):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text.encode()


def sub(text, old, new, count=1):
    assert text.count(old) == count, (old[:70], text.count(old))
    return text.replace(old, new)


def rename(text):
    for index, phrase in enumerate(KEEP):
        text = text.replace(phrase, '\x00KEEP%d\x00' % index)
    for old, new in IDENTITY:
        text = text.replace(old, new)
    for index, phrase in enumerate(KEEP):
        text = text.replace('\x00KEEP%d\x00' % index, phrase)
    return text


def prep(text):
    overlay = sha(successor_overlay())
    text = sub(text, "OVERLAY_SHA = '%s'" % PREP_OVERLAY_SHA, "OVERLAY_SHA = '%s'" % overlay)
    text = sub(text, "'overlay bytes differ from the derived %s'" % PREP_OVERLAY_SHA[:8],
               "'overlay bytes differ from the derived %s'" % overlay[:8])
    text = sub(text, "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n",
               "\nr8 (ga-n12k, the ga-qcwl continuation): the r7 prep unchanged except the identity; the overlay is the\n"
               "ga-qcwl PREP overlay (449346e3) with only the work dir and header lines replaced.\n"
               "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n")
    return text


def window_base_accepted(text):
    """s2 r2: admit against the S4 window's TERMINAL record, not the P7 snapshot (both s2 reviews held).

    The S4 window's STAGE and RESTORE replaced city.toml and the receipt by atomic rename (new inodes and times,
    same content) and its lifecycle rewrote suspension-state.json, so the live pins no longer equal the P7 image.
    The TERMINAL observed-after record was taken by this same snapshot() right after RESTORE, and a read-only
    comparison on 2026-09-25 23:30 CEST found the live image equal to it (atime dropped) and the providers equal.
    Its extra keys (providers, directories, cache access records) are not part of the compared image.
    """
    text = sub(text, "# S4: the accepted image is the P7 adoption snapshot on the post-S2/S3 host (two LIVE_PASS readbacks).\n"
                     "ACCEPTED = Path('/var/tmp/ga-e0t1.15-p7-adoption-20260925/after.json')\n"
                     "ACCEPTED_SHA = '7e008d9be0abd067270cf43fc1236cab7fab543a7339486f05422bb62002c56d'\n"
                     "PROVIDER_SHA = '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n",
               "# The accepted image is the previous window's TERMINAL record: the S4 window (ga-qcwl-window s2 20e9ba1e)\n"
               "# restored city.toml and the receipt by atomic rename and rewrote the suspension state, so the P7\n"
               "# adoption snapshot no longer matches the pins. The provider pins are unchanged since P7.\n"
               "ACCEPTED = Path('%s')\n"
               "ACCEPTED_SHA = '%s'\n"
               "ACCEPTED_KEYS = ('cache', 'host', 'pins', 'protected')\n"
               "PROVIDER = Path('/var/tmp/ga-e0t1.15-p7-adoption-20260925/after.json.provider-pins')\n"
               "PROVIDER_SHA = '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n"
               % (ACCEPTED_TERMINAL, ACCEPTED_TERMINAL_SHA))
    text = sub(text, "        # S4: the P7 snapshot was taken on this epoch after S2 and S3; no P6-era disposition applies.\n"
                     "        require(RECOVERY is None, 'no recovery admission in S4')\n"
                     "        image = prior\n",
               "        # The S4 TERMINAL record was taken by this snapshot() after RESTORE on this epoch; its extra\n"
               "        # keys (providers, directories, cache access records) are not part of the compared image.\n"
               "        require(RECOVERY is None, 'no recovery admission')\n"
               "        image = {key: prior[key] for key in ACCEPTED_KEYS}\n")
    text = sub(text, "    accepted_provider=json.loads(read(Path(str(ACCEPTED)+'.provider-pins'),PROVIDER_SHA))\n",
               "    accepted_provider=json.loads(read(PROVIDER,PROVIDER_SHA))\n")
    return text


BRIEF_TASK = '''## Worker-owned implementation and tests

This Bead (ga-n12k) continues ga-qcwl: Core platform provider pins are keyed by provider name only, so two
closed Claude wrappers cannot share one receipt (read this Bead with standalone
`/home/loucmane/gascity/bin/bd show ga-n12k --json`; the checkpoint below carries everything needed from
ga-qcwl, so do not read or touch ga-qcwl or its worktree). A previous worker implemented most of it and stopped at a checkpoint when its
context ran out; nothing was staged. Its checkpoint is preserved read-only in
%(checkpoint)s:
- worker-unstaged.patch (sha256 %(patch)s): the full diff against this base, 7 files;
- progress.md: its design and status; red-integrity.txt and red-canary.txt: its RED evidence;
- tests-required.txt and tests-triage.txt: its test runs and the two unexplained failures.

The design keys provider pins by (name, path) through platforminstall.ProviderPinKey and ProviderPinLess, in
integrity.go (validateIntegritySpec), canary.go (sort and uniqueness), canary_profile.go (provider inventory)
and the dispatch gate (observeLiveEnvironment helpers). Readiness stays family-name based.

Do, in order, and spend context sparingly (read files by line ranges, never dump whole large files or
full test logs, never re-read what you already have):
1. Verify the patch with standalone `sha256sum <checkpoint>/worker-unstaged.patch` against the digest above
   (a mismatch is a stop), then read progress.md and the patch.
2. Before any source edit, classify the two platforminstall failures at the unchanged base, each as its own
   standalone command:
   `go test ./internal/platforminstall -count=1 -run '^TestMetadataParentsRefuseUnrelatedEntriesAndHardLinks$/^valid$'`
   `go test ./internal/platforminstall -count=1 -run '^TestMetadataProtectedSiblingParentContract$/^valid$'`
   If they fail identically at the base, record them as a pre-existing sandbox limitation. If they pass at the
   base, the patch breaks them and they are yours to fix; if that fix needs a file outside the allowed set,
   stop at a checkpoint instead.
3. Re-apply every hunk of the patch except the two dispatch gate files, with native Edit/Write, file by file.
   Do not run git apply or any shell write. Record which hunks you applied and any you changed. Carry the
   recorded integrity and canary RED forward by citing the preserved files.
4. The dispatch gate has no RED yet: write its test first (from the patch's gate test, or a whole-environment
   fixture through observeLiveEnvironment if one is cheap), show it failing against the unchanged gate code,
   then apply the gate hunk and show it GREEN. The patch's gate test calls helpers that exist only in the gate
   hunk, so its RED is a compile failure; record it as such, and prefer a behavioural RED only if it is cheap.
   Do not create a copy of any source file.
   As soon as steps 3 and 4 are done, write progress.md and a checkpoint (changed paths, RED and GREEN
   evidence) in the evidence directory before the long suite runs, so a lost context loses nothing.
5. Keep every existing single-wrapper behaviour, every refusal of an unpinned, drifted or ambiguous provider,
   and the fail-closed reads. No live change, no Template or Operations change, no receipt or manifest edit
   on disk. Change only the allowed source files listed above and put new tests in the listed _test.go
   files, because SIGNING-RELEASE refuses any other staged path, including a new file.

Required runs: the complete `go test ./internal/managedworker ./internal/api ./internal/platforminstall`, the
focused `go test ./cmd/gc -run 'ManagedProduct|PlatformCanary|DispatchGate'`, the corresponding `go vet` of
those packages and `git diff --check`. Preserve RED and failed attempts. No unrelated broad suites or network
fallback. If the budget or your context runs short, write the checkpoint first (exact identity, base, patch
digest, changed paths, tests and limitations) and say so; a checkpoint beats an unreviewed shortcut. Read back
this Bead before handoff. Do not modify parent plans or other Beads.
''' % dict(checkpoint=CHECKPOINT, patch=CHECKPOINT_PATCH_SHA)


def brief(text):
    text = sub(text, '# ga-n12k — one actual Claude Core implementation/signing worker (ga-e0t1.15 S4, no KICK)',
               '# ga-n12k — one actual Claude Core implementation/signing worker (ga-qcwl continuation, no KICK)')
    text = sub(text, 'ga-y49e, ga-4z38, ga-f37t and ga-gegx attempts, their artifacts and worktrees remain historical evidence,\n'
                     'never retry targets.\n',
               'ga-y49e, ga-4z38, ga-f37t, ga-gegx and ga-nibd attempts and the ga-qcwl S4 attempt, their artifacts and\n'
               'worktrees remain historical evidence, never retry targets. In particular never edit, stage in or run\n'
               'git against /home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins; its preserved checkpoint copy\n'
               '(below) is your only input from it.\n')
    text, found = re.subn(r'## Worker-owned implementation and tests\n.*?(?=\n## Artifact and managed signing contract\n)',
                          BRIEF_TASK.rstrip('\n') + '\n', text, flags=re.S)
    assert found == 1
    return text


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = rename(raw.decode())
        if name == 'prep-r11.py':
            text = prep(text)
        elif name == 'window-base-r11.py':
            for old, new in PREP_PINS:
                text = sub(text, "'%s'" % old, "'%s'" % new)
            # Assertion only: the nudge-order pin must still be present exactly once.
            sub(text, "orders = json.loads(read(PREP/'orders.isolated.json', '%s'))" % ORDERS_SHA, '')
            text = window_base_accepted(text)
        elif name == 'worker-brief.md':
            text = brief(text)
        elif name == 'observe-integrity-r11.py':
            text = sub(text, 'post-S3 baseline (M6). It admits the live state against the P7 adoption snapshot (ga-e0t1.15 S4),\n',
                       'post-S3 baseline (M6). It admits the live state against the S4 window TERMINAL record (s2 r2),\n')
            text = sub(text, '    # S4: no recovery admission; the accepted image is the P7 snapshot (window-base).\n',
                       '    # No recovery admission; the accepted image is the S4 TERMINAL record (window-base).\n')
            text = sub(text, '    # snapshot below and compared exactly with the P7 adoption snapshot.\n',
                       '    # snapshot below and compared exactly with the S4 TERMINAL record.\n')
            text = sub(text, '    # The base snapshot named before.json admits the live state against the P7 adoption snapshot\n'
                             '    # (two LIVE_PASS readbacks) and its provider pins; no P6-era disposition applies.\n',
                       '    # The base snapshot named before.json admits the live state against the S4 TERMINAL record and\n'
                       '    # the P7 provider pins; no disposition applies.\n')
            text = sub(text, 'admitted_against_p7_snapshot=True', 'admitted_against_previous_terminal=True')
        elif name == 'window-r11.py':
            text = sub(text, 'admitted_against_p7_snapshot=True', 'admitted_against_previous_terminal=True')
        elif name == 'operator/PREP.sh':
            text = sub(text, '# ga-n12k window prep r7:', '# ga-n12k window prep r8:')
        out[name] = text.encode()
    # BIND runs for ga-n12k, so ROUTE binds the new bind-task digest.
    route = out['route-task-r5.py'].decode()
    [ran] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", route, re.M)
    out['route-task-r5.py'] = route.replace("BIND_SHA='%s'" % ran, "BIND_SHA='%s'" % sha(out['bind-task-r3.py'])).encode()
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
        target.chmod(0o644)  # the job runner starts wrappers with /bin/sh; the sources are all 100644
    print(len(out), 'files written to', root)


if __name__ == '__main__':
    main(*sys.argv[1:])
