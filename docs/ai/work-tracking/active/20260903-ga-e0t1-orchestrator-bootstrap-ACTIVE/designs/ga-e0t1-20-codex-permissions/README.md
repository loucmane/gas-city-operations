# ga-e0t1.20 scoped Codex creation-permissions recovery

Operator approval September 28 is recorded on ga-e0t1. This is metadata-only
operational recovery, not C1 product implementation. No worker launch. Two
independent Astra reviews of the signed candidate precede the host job.

R7 passed startup but RELEASE refused its 0664 transcript. The existing 0664
shared default.rules is the next strict-reader blocker. This package changes no
verifier, provider command, model, service, credential, historical transcript,
or Windows CODEX_HOME. The rejected per-provider shell/umask idea is not used.

## Exact six targets

preimage.json binds device, inode, uid, gid, mode, nlink, size, mtime, ctime,
xattr absence, and the one file content digest. Under /home/loucmane/.codex:

- rules becomes 0700 with owner-only default ACL.
- rules/default.rules becomes 0600, bytes unchanged.
- sessions, sessions/2026, sessions/2026/09, sessions/2026/09/28 become 0700
  with owner-only default ACLs. Existing descendants are not rewritten.

The minimal Linux default ACL is owner rwx, group none, other none. Future
directories inherit 0700 and files requested as 0666 or 0600 inherit 0600 under
umask 0002, 0022 or 0077. No group or other access is added. Home ACLs remain
unchanged. No package installation is required.

## Transaction and boundaries

Successor job ga-e0t1-20-permissions-r2; one fresh output root
/var/tmp/ga-e0t1.20-codex-permissions-20260928-r2. Existing jobrunner admission
requires signed exact HEAD, clean worktree, wrapper binding and both reviews.
Apply also checks its job cgroup/invocation, actual supervisor namespaces,
Core/broker/signer/runner epochs, restored R7 pins, suspended city/four rigs and
zero native sessions. GC diagnostics and protected-tree scans run in owned
read-only child mounts; they cannot write cache or platform assets/backups.

Inspect live uid1000 clients and affected open handles before each metadata
operation and around proof. Unreadable live processes refuse. An exited zombie
has no file table; the observed zombie is not a potential writer. The two live
desktop Codex clients use a separate Windows home. Never kill or alter them.
Metadata inventory preserves all 675 observed session entries and two rules
entries except the exact authorized target mode/ctime changes.

This is not an atomic global reservation or confinement against a malicious
same-uid process. Other affected creators must remain quiescent for this short
job. Observed concurrent changes stop it without overwriting them. Defaults are
creation policy, not a substitute for future strict authority checks. Rename-in,
chmod and ACL replacement must still be detected by the next launch contract.

Retain a byte-exact 0600 rules backup, complete metadata/ACL preimage, historical
inventory, and create-only per-syscall intents/results. Only six held, identity
checked O_NOFOLLOW descriptors receive chmod or default-ACL operations. No link
ancestor is allowed. After a handled exception/signal, classify the last atomic
syscall from its actual before/allowed-after image and reverse only proven
operations while every target and unrelated descendant remains exact. Restore
the original modes and ACL absence; ctimes necessarily advance and are recorded.
The approved rollback restores preexisting group-write bits only to this exact
frozen preimage while quiescent, never wider. No timestamp falsification.

Completed steps use stable step keys so interruption between recording a step
and clearing its pending marker cannot record the same operation twice. Final
rollback verification rereads every held descriptor and its path identity.

After all postimages and proofs pass, write commit-intent then cross the commit
boundary before writing result.json. An interruption after that boundary never
rolls permissions back behind a possibly published success receipt. It records
commit-interrupted with rollback forbidden and requires exact readback, without
replay. A receipt alone is not acceptance when the wrapper exited unsuccessfully
or interruption evidence exists. Earlier handled failures retain exact rollback.

New descendants, file changes, unexpected postimages or rollback failure produce
an ambiguous stop. Do not rewrite newly inherited descendants or replay the root.
SIGKILL/power loss cannot be caught; preserve intents for reviewed recovery.

Read the actual installed ACL into retained disposable mirrors and prove all
six umask/request combinations through new year/month/day directories. Verify
the unchanged strict rules reader, exact final target images, stable host/pins
and protected-tree preservation. PASS proves only this migration and kernel
creation behavior, not actual worker creation, product delivery or provider parity.

## Follow-through and evidence

After PASS, record exact postimages on the Bead and prepare a new worker window
whose preflight binds these permissions and default ACLs. Never replay R7 or
repair its historical transcript. A fresh real worker must pass strict transcript,
workspace and process checks before release. Source work remains with Gas City.

The first signed package b333bca8 had one HOLD and one SOURCE_PASS. Both verdicts
are filed and the package was never executed. Three focused fault injections
reproduced duplicate rollback bookkeeping, stale rollback readback, and a success
receipt surviving compensation. The duplicate ACL removal happened to succeed
on this kernel, so no syscall failure is claimed for that reproduction. Earlier
test harness corrections and all RED artifacts remain preserved in /tmp.

The immediate read-only preflight also caught rounding of five directory time
values in the original manifest. The coordinator had carried nanosecond integers
through JavaScript numbers. Regeneration carries Python JSON as raw text, never
numeric JavaScript objects. All other fields match exactly; the ten changed
mtime/ctime values differ by at most 164 ns and map to the same binary64 values.
No live timestamp changed. The original signed manifest remains in b333bca8.
The driver still requires exact integer equality, not a tolerance or rounding.

Focused disposable tests cover drift, links, partial
syscall failure, rollback failure, all-step interrupts, future creation and
client inventory. Preserve the failed root-ancestor O_NOATIME diagnostic; it
was fixed with O_PATH traversal, not a removed authority check. Full adapter/meta
suites and source guard remain mandatory before delivery. Live apply NOT RUN.

## Corrected candidate verification September 28

- Focused final package: 39 PASS in /tmp/ga-e0t1-permissions-green-r7.xml.
- Full adapter/meta surface: 3962 PASS and 21 existing skips in
  /tmp/ga-e0t1-permissions-full-r2.xml. Four are opt-in certification/wheel
  checks and seventeen require the unavailable historical Taskmaster CLI.
- The restricted attempt is preserved in /tmp/ga-e0t1-permissions-full-r1.xml:
  2183 PASS, two dependency-download failures, one skip, then an interrupted
  MCP client hang. Only its exact identified pytest and fixture-server processes
  were stopped gracefully. The unchanged invocation module passed all eight
  tests with required network/IPC access before the full parallel rerun.
- The successful run uses the repository-supported loadgroup parallel mode.
  Dependency virtual environments and the pip cache remain under /tmp.
- Managed-update goldens and S:W:H:E source guard PASS. No unrelated tracked
  source changes. Full-suite inputs were unchanged by the separate package edits.
- Exact six-object host preimage and affected-client quiescence PASS after the
  timestamp correction. The two Windows-home Codex clients are unaffected.
- No live recovery job queued, no permissions applied, no worker released.

The signed R1 HOLD stays filed. This corrected successor requires two fresh
independent reviews and all immediate preflights; no verdict is inherited.

## First live job and bounded successor

Both R2 source reviews passed 84afc149. The first host job was admitted but
stopped in its before-trees read-only child, before transaction preimage or any
permission syscall. Exact live reread proved all six targets unchanged. Its
consumed root, backup, intent, three phases and job record remain preserved.

Cause: the parent correctly verifies the root-owned bwrap binary. The child
repeated that host-ownership check after entering a user namespace, where root
files appear as overflow uid/gid 65534. An exact-shape read-only probe confirmed
the same 0755 binary, size 72160, digest e318903862396f96de3df57264e0158682b952fd3fb53ac23d876413e7b30f71,
with only ownership mapping different. The host view remains root-owned.

The successor checks host context first and retains the exact host binary check
before launching its children. Inner only performs source-bound read-only tree proof:
mandatory mount validation remains first and writable mounts still refuse. It
does not launch bwrap, run metadata changes, or inherit authority from its argv.
The predecessor job/phase digests and exact pre-transaction root inventory are
required; the original manifest must still match every target before writing.
No binary authority check is relaxed in the host or mutation path. The original
job/root cannot replay. New driver regression tests preserve the live RED.

## Exact timestamp-only disposition approved September 28

Following the preserved PERMISSIONS-RECOVERY-HOLD report, the operator approved
only mtime_ns and ctime_ns on cache directory
954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git:
both 1790604770227789531 to exactly 1790621288720671640. The source-bound
terminal observation remains unchanged. The comparison copies that observation
and changes only those two expected integers. Live values must equal the exact
new integers, not a tolerance. Every other field, path, file byte and protected
tree keeps the existing comparison. Nothing writes cache metadata. Immediate
before/after proofs still hash the full actual snapshots including access times.

The earlier diagnostic with approval_granted false remains historical evidence;
this approval and the exact values are recorded append-forward on ga-e0t1.
The read-only child proof emits the disposition and preserved observation digest.
This exception is local to this fresh permissions job and does not authorize a
future worker window or broader timestamp normalization.

The new RED has one refused approved-positive case and two missing-specific-guard
assertions, not three distinct safety defects. Disposable negatives cover every
other directory field, wrong or old timestamps, file content, inventory additions
and removals, both protected trees, and changed historical preimage. Reviewers may
read source and evidence and run these disposable tests only. No live gc or bd,
service probes, escalation, or configuration inspection during source review.

Current successor evidence: 61 focused PASS at
/tmp/ga-e0t1-permissions-green-r10.xml and a successful actual read-only tree
rehearsal. The failed green-r9 command named a nonexistent module and ran no
tests; preserve it as a command error. See PERMISSIONS-RECOVERY-R3.md for the
operator binding, unchanged full-suite inputs and required fresh review.
