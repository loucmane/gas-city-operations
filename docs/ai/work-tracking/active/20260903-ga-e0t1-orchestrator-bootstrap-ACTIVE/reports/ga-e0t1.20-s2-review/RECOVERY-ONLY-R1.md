# ga-e0t1.20 recovery-only successor R1

Prepared 2026-09-28 Stockholm time after the operator's explicit recovery-only
authorization. Source/test evidence only until independent review and host
execution complete. No worker retry is authorized in this recovery.

## Exact disposition and authority

Original signed package: cdf7e3784d18358e099c444b48bf43387f9175a7.
The operator approved preparing a recovery-only successor, preserving that
package, obtaining two independent Astra reviews, then restoring and verifying
the baseline. This narrowly overrides the in-window source freeze; it does not
override the runtime quiet window, protected cache or any verification check.

Preserved stopped-state audit:
/tmp/ga-e0t1-20-window-r3-recovery-stop-20260928.md
SHA-256 57c0803c1ef9a1affe130deadabd779ef01b819ac9b1c252d548c4793aa4fc1f.
The audit records the earlier source-write refusal honestly. No denied action
was bypassed; the explicit operator grant preceded this successor.

## Completed operations, not to replay

- 10:23 CEST OBSERVE r5 passed actual-host integrity.
- 10:25 CEST PREFLIGHT r4 passed.
- 10:27 CEST STAGE r3 installed and verified the temporary city and receipt.
- 10:28 CEST RESUME r3 applied rig resume then refused active session count.
  City resume never ran. Core omits zero active_sessions from status summary;
  its independent census was sessions empty and summary.active zero.
- 10:30 CEST HOLD r3 suspended gascity using the supported native command.
- 10:31 CEST CLOSE r3 proved zero sessions, tmux sessions and worktree processes.
  No worker ran; no signal or server kill occurred.

Current known disposition is fully suspended and quiescent, with temporary
staged city and receipt still installed. Only the existing owned restore writer
may restore them. Fresh host verification remains required.

## Candidate scope

generators/stranded-recovery.py verifies one exact terminal lineage from the
preserved files. Fourteen complete evidence files are digest-bound. Native
command argv, cwd, successful completion and reaping, the actual suspension
transitions, exact final non-access metadata and zero-residue close result are
checked. Ordinary read-atime accounting remains unchanged. No failed event is
removed, rewritten, promoted to success or replaced with a fabricated event.

generators/recovery.py overlays the unchanged deterministic predecessor. It
disables every wrapper except ADMIT, RESTORE and TERMINAL, rejects non-recovery
base entry points, and deterministically propagates source hashes. The already
completed CLOSE executor pin remains its historical digest, not a regenerated
digest. The manifest includes all 57 predecessor file digests and 58 successor
file digests. Original product files, worker brief, startup probe, status parser,
lineage implementation and permission exception remain byte-identical.

The zero-session status bug is intentionally not repaired here. A future worker
retry requires its own corrected, fixture-proven package. Recovery PASS would
not imply worker success, C1 completion or provider parity.

## Tests and limits

- Full generator corpus: 405 passed, zero skipped/failures.
  /tmp/ga-e0t1-20-recovery-final.xml
- Generated contract corpus: 42 passed, zero skipped/failures.
  /tmp/ga-e0t1-20-recovery-generated-final.xml
- git diff --check passed.
- New recovery module: 35 tests cover exact terminal disposition; nonterminal
  rejection; modified evidence, endpoints, metadata, command identities,
  extra lifecycle operations and residue; inert wrappers; digest graph and
  historical CLOSE pin; the actual generated main and lifecycle functions.
- Fixtures copy pinned evidence into disposable test directories and exercise
  the changed verifier. They do not run production commands or constitute live
  restoration proof. Existing read-atime and writer tests remain unchanged.
- Reviewers must inspect source and tests independently. No verdict presumed.

## Execution after two independent reviews

Use the existing host runner and exact signed clean candidate, one job at a time.
Only these wrappers are admitted by this review request:
operator/ADMIT.sh, operator/RESTORE.sh, operator/TERMINAL.sh.
Read each wrapper result and preserve its HALTED latch before the next job.

ADMIT performs fresh host preservation and terminal lineage verification;
RESTORE uses existing backed-up city and receipt plus bounded writer sandbox;
TERMINAL proves the restored baseline and full native platform integrity.

No workflow.py, Bead writes, source edit or unguarded gc until the terminal
result. All outcomes are temporarily recorded in runner logs and immutable
window artifacts, then appended to Bead/Aegis after restoration. Preserve every
old evidence root and failure. Stop on refusal, drift or ambiguous mutation.

## R2 correction after independent HOLDs

Both independent reviews of signed 45a177710908c8abd4afa795d3b4893991952ec8
held the same defect before execution. The generator rewrote OBSERVER_SHA in
window-r11.py, although that field authenticates the already-completed OBSERVE
record rather than a future executable. Both native review envelopes are
preserved and filed under that rejected head in the runner review archive.
Neither ADMIT nor any other recovery job ran on the held candidate.

The generator now preserves the exact historical observer digest
091457e1027f2115b5321f894278fcbe3d8dc57639f871f0d9486ffc243651ed
while computing the final recovery file hashes for their consumers. Historical
CLOSE protection and all other checks remain unchanged. No original evidence
was rewritten or replayed. The preserved OBSERVE intent has SHA-256
094798c315d19e964c2278ae5b12e5df718e57860ae5d4a738a47bee37be6446
and the original integrity binding has SHA-256
2f3e2279280dee6bbe3d91310b8cc6f123ed4893bf3c9865ad511f0860a7fdc2.

Three new tests execute the actual generated integrity_baseline function on
byte-exact completed observation data copied to disposable fixtures. Only the
fixture directory in the binding is translated. They prove the positive path
and refusal on altered executor or postimage binding. The first RED produced
the same integrity executor refusal before live execution. A fixture-only
missing os import was corrected, with all intermediate failures preserved.

Final source evidence: 408 generator tests and 42 generated contract tests
passed, zero failures or skips. Files are
/tmp/ga-e0t1-20-recovery-r2-confirmed.xml and
/tmp/ga-e0t1-20-recovery-r2-generated.xml.
RED and intermediate results remain at the recovery-r2-red, green and final
JUnit paths. Fresh exact-head independent reviews are required for R2. This
correction does not authorize a worker retry or imply live restoration.
