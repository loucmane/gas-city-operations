# ga-e0t1.20 r4 terminal recovery — source candidate

Prepared 2026-09-28 CEST under the operator's latest continuation approval,
standing corrected-successor authority and bounded operational-package exception.
This is restoration only, not worker retry or product implementation. The quiet
window still prohibits workflow commands, Bead mutations and unrelated source
changes. Only this separately signed recovery package is prepared; logging to
the existing Bead/Aegis surfaces follows terminal restoration.

## Observed outcome and preserved history

Signed failed window: 78152f1d1400961978b35db610db5eef66babd71.
PREFLIGHT, STAGE and both RESUME phases passed. One Astra session ci-72ehy
started but failed its database/control-command startup before claim or SOURCE
RELEASE. The task was open and unassigned on the captured WATCH. No release
root exists. No unchanged worker retry is permitted.

CONTAIN-1 applied city suspend, then refused an active-session-count mismatch:
status said one active while direct census was empty. Preserve that failure
exactly; it is not promoted to a successful lifecycle event. HOLD-1 observed
city already suspended, applied only gascity rig suspend and verified epochs.
CLOSE-1 then proved zero open sessions, city tmux sessions and workspace
processes. It closed the empty tmux server without sending any process signal.

Exact preserved roots:
- /var/tmp/ga-e0t1.20-window-20260928-r4
- /var/tmp/ga-e0t1.20-r4-watch-20260928T105300Z
- /var/tmp/ga-e0t1.20-r4-hold-20260928T105616Z
- /var/tmp/ga-e0t1.20-r4-close-20260928T105721Z

Current state: fully suspended and contained, but temporary city and receipt
remain staged. The runner remains halted until two independent source reviews.
No restoration success, provider parity, C1 completion or goal completion is claimed.

## Small bounded delta

New generators/recovery_r4.py starts from the immutable signed failed package.
New generators/stranded-r4-recovery.py pins 24 preserved evidence files and
validates the two completed resume events, the exact failed city-suspend
command and postimage, the separate HOLD rig-suspend command, final suspension
identity and zero-residue CLOSE. The consumed release root must remain absent.
Both the original parser and the original failure remain unchanged.

Only ADMIT, RESTORE and TERMINAL wrappers can execute. Every other wrapper is
inert. The base entry rejects lifecycle/preflight/stage and inner staging.
Existing actual-host, full-preservation, protected-cache, bounded-writer,
read-time, fixed-operation receipt and terminal integrity checks remain.
The digest graph changes references only; completed OBSERVE and CLOSE evidence
keep their original executor hashes, as does the historical unused r3 verifier.

Terminal reporting distinguishes observer worker_launched false from actual
window history: worker_started_in_window true, source_release_sent false and
open_sessions zero. Source non-interference is not inferred from no release;
it must be independently checked after restoration.

No product source, worker capability/profile, allowlist, runtime policy, other
rig, source-release machinery, privilege or installed tool is repaired here.

## Verification

- Focused recovery fixtures: 56 passed.
  /tmp/ga-e0t1-20-r4-recovery-tests-20260928.xml
  SHA-256 89a8029016b7196fd493a0a6c38843ffa506b3f94fd3a27dbd2114fccd83dee6
- Full operational generator corpus: 512 passed, no skips or failures.
  /tmp/ga-e0t1-20-r4-recovery-all-tests-20260928.xml
  SHA-256 4428e237e866e8574ab015a3fe2eb37177428bff67206afe07e34e86d47a7b4c
- Materialized contract: 42 passed.
  /tmp/ga-e0t1-20-r4-recovery-generated-tests-20260928.xml
  SHA-256 12fe2e3244e54203aec685f2baa045ce93aadf8e577a825786815d6a57ad2283
- Assembly manifest SHA-256
  a8a29882d4982b6fdd9c582b23f1e2ae74c5233c089b5971401bd9b1c2db8361.
  59 generated files, all mechanically matched to the create-only output
  /tmp/ga-e0t1-20-r4-recovery-assembled-20260928.
- Shell syntax and exact generated digest wiring checked by the corpus.
- Existing adapter/meta source inputs are unchanged since their final 3983-test
  verification recorded in ZERO-SESSION-R1-VERIFIED.md. This operational-only
  successor reuses that evidence rather than claiming a new broad-suite run.
- No fixture result is live restoration evidence. Independent review and actual
  host admission must pass before the existing restore writer is invoked.

## Reviewed execution request

Exactly ADMIT then RESTORE then TERMINAL through the installed host job runner,
one job at a time with two genuine independent Astra verdicts bound to this
signed clean candidate. Read each actual result before the next operation and
preserve every HALTED latch. Never replay BIND, ROUTE, RESUME, CONTAIN, HOLD,
CLOSE or SOURCE RELEASE. Stop on any refusal, drift or ambiguous mutation.

After terminal PASS, record this failed startup and successful recovery
separately on the authoritative Bead. Inspect source non-interference and the
failed worker's exact command transcript before proposing any new worker
attempt. Do not repair a permission boundary by silently broadening authority.
