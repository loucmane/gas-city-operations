# ga-mb91 window R2 — both independent HOLDs corrected before launch

## Unchanged scope

The standing authorization and WINDOW-REVIEW.md apply. No window, bind, route,
resume or worker has run. Completed WORKTREE/PREP, Core PR50, sequence17, M15
and P14 are reused, not replayed. No live permission, queue, configuration,
receipt, service or rig change occurred. This is an operational package, not
coordinator implementation of the C1 product. No Fable inference or parity claim.

## Review provenance and exact correction

R1 signed candidate b3c0e019b0de2caa7e6cbd4f90877c3ecd578976 is preserved.
Both independent Astra verdicts were HOLD and were filed with the runner before
any candidate change. Request SHA256:
40a23320ad0c306b6032aa4ee5b84f80bf8b93c135c6eb1e4207ebc159c530cf.
Native exports are in /tmp/ga-mb91-window-reviews-20260930-r1:
codex-01a0f1d5-876b-7d83-9226-f3b637cfd972.json and
codex-01a0f1d6-5da1-7d91-9547-e219f2a398f9.json.

A found that the adapter confused native state.json mode 0644 with lock mode
0600. queue-guard.py now verifies the opened descriptor, exact native 0644,
uid/gid1000, single regular file, trusted parent chain and 16MiB maximum.
No-follow, nonblocking, no-atime, bounded reads are bracketed by descriptor and
path identity. Only observed atomic-replacement drift has three bounded retries.
Nothing changes live mode or accepts arbitrary read/write modes. Native source
authority is Core 91079846eba2375d8c1acb367ede30ba1a21fd87,
internal/nudgequeue/state.go WriteFileAtomic state mode 0644.

B found that allowed current-session reminders could be misclassified as the
single release after enqueue. The pre-poller foreign baseline remains exact.
Before enqueue, and again immediately before spending it, new owned records
must be receipt-backed, current-session/current-epoch gascity/codex, source
session, and exactly the native nudge-on-route text `check for assigned work`.
An unknown reminder, missing shadow or premature release refuses before enqueue.
Native single and batched transcript messages must match the exact pinned Core
formatter, with only that ordinary text and the exact release. Ordinary ingress
also requires injected receipts; a receipt-close race waits without false PASS.
An already-injected ordinary message before enqueue is explicitly reconciled.
Release still requires exactly one enqueue, one exact release ingress, and its
own injected native receipt. No substring-based acceptance or arbitrary message
allowance. Foreign buckets and full queue/shadow records remain unchanged.

Complete actual generated lifecycle bodies now execute in offline fixtures with
the real failing preservation guard. Both supported suspension phases are reached;
failure evidence stays sticky and restore admission refuses. Native commands and
lineage observations are fixtures, not a live containment claim.

## Rebinding and tests

ASSEMBLY-REVIEW-R1.json and TEST-REBINDING-REVIEW-R1.json preserve the old maps.
ASSEMBLY-REVIEW-R2-DELTA.json records the 45 changed source/digest dependents.
assembly.json still binds 68 outputs. Only three operational source modules
changed behavior; remaining operational differences are exact digest rebinding.
No completed wrapper or worker input was changed.

Final offline suite: **610 passed**, zero errors, failures or skips, 2.78 seconds.
/tmp/ga-mb91-window-tests-20260930-r2-final.xml
SHA256 1ee440fea85b4a523961d2e8f3d3aa7a935a1c40b5c3f45e67d1ed2b2a47708a.

Preserved RED and intermediate evidence:

- Native-reader RED: 2 failed, 9 passed. Both failures expose the inverted mode
  contract. /tmp/ga-mb91-native-reader-red-20260930.xml,
  f7ff4087fced2b04ad631095afcc87ca9f90a50e0f817f40bf95184023c8ab8e.
- Release RED: 10 failed, 5 passed. One directly reproduces the ordinary/release
  confusion; remaining failures bind missing new APIs and dependent assertions.
  /tmp/ga-mb91-release-red-20260930.xml,
  0aa356caaa10800d383344d3ec6491cebf5cac2da025ad3d50e64685d52d5fef.
- Adapter RED: 4 failed. Three initially reused a foreign fixture ID and correctly
  refused; fixed by choosing a distinct owned ID. The fourth demonstrated the
  pre-enqueue ordinary-ingress case. /tmp/ga-mb91-r2-adapter-red-20260930.xml,
  c903e72ffb22c95f4d9bf9b88b8f84709111045da62ac3778215fb1c5117454d.
- Before mechanical rebinding: 156 passed, one expected stale generated guard
  digest failed. /tmp/ga-mb91-r2-focused-b-20260930.xml,
  7238be8137b6b372cd16494e7d1c1b7b64b9d5ab0e1e7d459e19d0c358edd10e.

## Consolidated review and execution

Verify both findings against actual native modes, receipt fields and batch
formatter, including pending ordinary reminders and unknown-message negatives.
Verify complete generated containment execution, exact manifest regeneration,
and every unchanged release, write-protection, claim/session and restoration
gate. Review the complete R2 candidate, not only the diff. No test rerun requested.
Only after two independent SOURCE_PASS verdicts: follow the unchanged ordered
runbook in WINDOW-REVIEW.md. Record outcomes under the standing grant without
another package-hash approval. Every actual preflight still applies.
