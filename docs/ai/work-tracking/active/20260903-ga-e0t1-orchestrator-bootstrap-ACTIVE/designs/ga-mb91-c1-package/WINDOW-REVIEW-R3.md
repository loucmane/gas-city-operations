# ga-mb91 window R3 — native receipt metadata and close are separate writes

R2 signed d13bb386e21df87fc235369eb6c2d759d7a86d66 remains preserved.
Both independent Astra reviewers identified the same remaining must-fix and no
other should-fix. Both HOLDs were exported and filed before changing the candidate:
/tmp/ga-mb91-window-reviews-20260930-r2/codex-01a0f1eb-bb2b-74f2-b96a-ae03900b271f.json
and codex-01a0f1eb-f218-7172-91d6-b691aee8c588.json. Frozen request digest:
13ad894ffe8f611996cdcdfd3f2d29b3328793af6c9ce62254e40126f81a71e7.

## Reassessment against the complete native producer

Read pinned Core 91079846eba2375d8c1acb367ede30ba1a21fd87,
internal/nudgequeue/store.go Save and Terminalize. Save creates a queued/open
shadow. Terminalize validates scope, stamps injected metadata with
SetMetadataBatch, then calls Close separately. An injected/open observation is
therefore a real intermediate state, not evidence of a failed transport.
The existing mechanism remains appropriate; this is an adapter state-model
correction, not another native platform prerequisite or infrastructure repair.

## Exact delta

- Exact authority-validated injected/open ordinary and release receipts are
  pending only. Agent, session, epoch, nudge ID, message, source, terminal reason,
  last error and provider-nudge-return boundary checks remain enforced.
- Only injected/closed receipts count toward delivery. The native receipt AND
  exact transcript requirement remains; queued is never delivered.
- Before enqueue, an ordinary ingress/close race gets a bounded read-only settle
  loop: 15 seconds maximum, 16 observations maximum, no mutation. Unknown text
  and premature release still refuse. Permanent-open timeout spends no enqueue.
- After enqueue the existing 90-second observation bound is unchanged. Permanent
  open receipts never PASS, and the single enqueue is never replayed.
- The ordinary receipt labels must be an actual list, matching native Beads.

No native receipt is modified by this adapter. Foreign queue and complete shadow
records, the fixed pre-poller baseline, exact file-mode reader, both containment
steps, claim/session checks, worker write protection and restoration are unchanged.
No completed WORKTREE/PREP or Core adoption was replayed. No live window ran.
Only release-delivery-r13.py and release-runtime-r13.py changed behavior; two
dependent source hashes were rebound. ASSEMBLY-REVIEW-R2.json preserves the prior
68-output map; ASSEMBLY-REVIEW-R3-DELTA.json records the four changed outputs.

## Evidence

RED: four failures reproduce release, ordinary, combined and pre-enqueue close
transitions. /tmp/ga-mb91-r3-close-red-20260930.xml,
9b7e47778453afc9dce84e6db739eb453424335334b3103450910e667564a449.

Final full offline suite: **618 passed**, zero failures/errors/skips, 2.25 seconds.
/tmp/ga-mb91-window-tests-20260930-r3-final.xml,
383f0e7bd5b37c20765e5aaa8810bc9402ba1a04220723ee0431ea49e9e275e1.
Includes injected/open to closed progress for release and ordinary receipts,
both together, permanent-open timeout, invalid terminal-authority negatives,
and actual adapter preparation settling with exactly one or zero enqueues.
All subprocesses and native mutations in these tests are fixtures, not live proof.

## Independent review and unchanged execution order

Review this complete candidate with WINDOW-REVIEW-R2.md and WINDOW-REVIEW.md.
Check native producer/consumer state compatibility rather than relying on tests;
verify no open receipt can complete delivery, no unknown state becomes pending,
no duplicate enqueue can occur, all 68 hashes match, and unchanged containment
and restoration remain reachable. No additional test rerun requested.

After two fresh SOURCE_PASS verdicts, proceed through the existing runner and
ordered BIND to TERMINAL runbook under standing authority. No new hash-based
operator approval. No Fable, product direct-coding fallback or provider-parity
claim. This remains the preparation of one candidate-only Astra worker window.
