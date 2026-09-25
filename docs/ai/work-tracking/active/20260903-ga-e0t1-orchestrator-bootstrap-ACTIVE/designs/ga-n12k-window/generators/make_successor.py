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


BRIEF_TASK = '''## Worker-owned implementation and tests

This Bead (ga-n12k) continues ga-qcwl: Core platform provider pins are keyed by provider name only, so two
closed Claude wrappers cannot share one receipt (read both with `bd show ga-n12k --json` and
`bd show ga-qcwl --json`). A previous worker implemented most of it and stopped at a checkpoint when its
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
1. Read progress.md and the patch. Re-apply the patch to this worktree with native Edit/Write, file by file.
   Do not run git apply or any shell write. Record which hunks you applied and any you changed.
2. Carry the recorded RED evidence forward (cite the preserved files). The dispatch gate has no RED: write its
   test first against a base copy of the gate code (or show the new test failing before the gate hunk is
   applied), then GREEN. Prefer a whole-environment fixture through observeLiveEnvironment if one is cheap.
3. Classify the two platforminstall failures (TestMetadataParentsRefuseUnrelatedEntriesAndHardLinks/valid,
   TestMetadataProtectedSiblingParentContract/valid): run exactly those two with `-run` at the base state
   (before step 1, or with the integrity hunks not yet applied). If they fail identically at the base, record
   them as a pre-existing sandbox limitation; if they pass at the base, they are yours to fix.
4. Keep every existing single-wrapper behaviour, every refusal of an unpinned, drifted or ambiguous provider,
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
        elif name == 'worker-brief.md':
            text = brief(text)
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
