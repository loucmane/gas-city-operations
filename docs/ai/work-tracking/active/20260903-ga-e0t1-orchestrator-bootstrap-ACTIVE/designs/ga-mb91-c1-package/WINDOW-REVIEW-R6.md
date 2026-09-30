# ga-mb91 R6 — preserve exact historical DEAD-shadow absence

## Outcome and exact failed operation

R5 signed candidate 60bfdcc0761767f1e81a692e19f43e068efae009 received two independent Astra SOURCE_PASS verdicts. OBSERVE r3 passed actual host verification and full native integrity, result b0ec06cb5037c2ca6095e816f57b7a93aa16517ade64db3c4df4673bec1ccdd6.

PREFLIGHT r1 ran 13:46:06–13:46:46 CEST on September 30 and failed at queue-preservation.baseline with queue backing Bead missing. It never created preflight-pass, stage-consumed, a route root, or a rig-resume intent. Every bounded phase exited normally with its process group gone. The failed root and all 39 files are preserved at /var/tmp/ga-mb91-window-20260930-r1. PREFLIGHT-REFUSAL-R1.json binds every file hash and mode.

Done digest daa1866e4ffb6243900ae06caf84e945facc29e2b2c2ee5f991698a9293c4992.
HALTED digest e58f67a159f23102c3e5748333d6b33c204b1e5af4373fe0f155ebdc62cdf3ee.
No live stage, routing, worker, or authority change occurred.

## Diagnosis and unchanged authority

The queue contains 27 records: 26 DEAD and one pending. Twenty-five exact historical DEAD records reference absent shadow Beads. The adopted Core treats the queue as authority and Beads as optional observability shadows; its missing-shadow terminalization is a no-op. Core sources internal/nudgequeue/store.go, store_test.go and scope.go in the adopted custody source establish this; no Core repair or history recreation is required.

Read-only diagnostic r3 proved every exact missing ID through native show: exit 1, the specific JSON no-issues error and matching stderr, not a transport failure. Its result digest is ac4d8a2b030746985e2182d6f72a09f681bc1bddbf88857cc3f3111e0256d159. Native count confirms 50 shadows; list limit 0 and 4097 both returned those 50. No alternate metadata.nudge_id mapping exists among them.

Diagnostic r4 proves the exact count adapter: absent-ID union gives 0, one existing ID gives 1, and their union gives 1. Result digest 3fe78efb4d66cad3ecb117f8dcd60376c405cc62df659f5a211599279feec289. Both diagnostic runs verified unchanged protected non-atime host state and no surviving owned processes. They neither cleared the latch nor launched work. Earlier diagnostic r1 failed before queries because of four wrapper-only annotation keys; r2 compared the shared protected fields and passed. All roots remain preserved.

## Narrow operational change

historical-shadow-absence.json binds only each exact nudge ID, original Bead ID, DEAD bucket and SHA-256 of the full canonical tuple. It does NOT copy private historical messages or project paths. The original complete records remain in their existing evidence root. A proposed full-record copy was refused by safety review before writing; the digest-only representation respects that boundary without reducing equality coverage.

queue-preservation.py records this exact map in a v2 preservation baseline. It requires the entire observed tuple to match its digest, its original DEAD bucket and Bead identity. Every other missing backing Bead still refuses. No age rule, generic missing exception, lookup-error exception, queue sweep, cleanup or history rewrite is introduced.

At every checkpoint queue-guard.py obtains count/list/count with identical native shadow filters and requires equal exact cardinality. It additionally performs an unfiltered native exact-ID count for the 25 original shadow IDs, requiring zero, so changed-label or changed-type recreation cannot hide. All commands retain owned process cleanup and bounded timeouts. Count schema failures, query failures, truncation and races refuse. The complete shadow census rules out alternate nudge_id mappings. Pure preservation checks this absence before any owned-new-record exception, so even the current session cannot recreate or remap those shadows.

The two observations, full foreign-record preservation, exact config/orders, session/epoch/poller checks, process/cgroup authority, sticky failure and containment semantics remain. Counts can conservatively refuse concurrent cardinality changes; they never infer absence from a failed read.

OBSERVE advances to r4 and the window to r2. WORKTREE, PREP and BIND remain exact and are never replayed. Route/terminal roots remain the unstarted r1 roots. The BIND executor remains 028ccef1db747088c7f8552c86094ded85b5db12f1d58d890bd7678fa432adea and its wrapper stays disabled.

The 69-output assembly graph is regenerated from its pinned inputs, not hand-patched. ASSEMBLY-REVIEW-R6-DELTA.json enumerates changes. R5 manifests are archived. No worker input, permission, runtime adoption, 44-file Git exception or implementation scope changes.

## Failure disposition and tests

preserve-preflight-refusal.py admits only the exact failed R5 job, signed clean current candidate, exact 39-file inventory, normal phase cleanup, diagnostic preservation receipts, inactive unit, empty runner queue, absent successor and route roots, and unchanged completed BIND receipt. It preserves the original HALTED inode by no-replace rename and fsync. It never queues a job. The success-only helper separately admits fresh observe-r4 and preflight-r2.

The new RED corpus initially reported 21 failures due to the missing API and manifest. These are not 21 independent defects; the real failing production operation above is the causal reproduction. Focused iteration had 71 PASS and one expected generated-digest mismatch before regeneration. Final full operational package: 654 PASS, zero failures/errors/skips, 4.49 seconds.

Evidence:
- /tmp/ga-mb91-r6-red.xml — 64f8e48df35bc4a4b37f9ee5309fd2f0fa7f868d704f513308bf6cf51caf358e
- /tmp/ga-mb91-r6-focused.xml — 8dd0d72a08362d9ff841b7db922a622962109458ac359c19695a973fd0617ad9
- /tmp/ga-mb91-r6-full.xml — 697b5a7aee7a45c3e687f0abfa1d327202612a0d3d262fb7a2c610ec05b7cc5a

These are offline package proofs, not live worker or provider-parity acceptance. Failure-helper tests inspect its bound contract; no archival is claimed yet.

A redundant workflow resume refused because the original repair dependencies remain open; no dependency was changed. Supported workflow verify subsequently passed all six checks including live ownership, readiness and source tracking. The existing context remains the only coordinator context.

## Execution after two independent SOURCE_PASS verdicts

Under the existing standing grant, archive only the exact failed preflight latch with the reviewed helper; submit fresh OBSERVE r4 once; on actual host/native-integrity PASS run PREFLIGHT r2. Only then follow the already-reviewed staged route, bounded worker window, containment, restoration, TERMINAL and inspection. Read each runner result and preserve each consumed root. No workflow or Bead writes during the quiet interval. No Fable inference or private-content export.

This is an operational successor, not product implementation. The candidate-only worker still owes its own source output and review; full goal acceptance remains open.

