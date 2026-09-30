# ga-mb91 R7 — exact Core shadow-label fallback

## Outcome and scope

R6 candidate 6c04152d9ca59dcc72aff34470577dce71f846b5 received HOLD from both independent Astra reviewers. Both identified the same must-fix: Core's shadow fallback uses the exact nudge label without a type, gc:nudge, metadata or owner filter. The R6 complete filtered census and original-ID absence query did not exclude an alternate Bead found by that fallback.

The adopted source is /var/tmp/ga-e0t1.22-custody-build-20260930-r1/repro-source/internal/nudgequeue/store.go lines 423–460. R7 adds exactly that unfiltered label-union count at every observation and requires zero. The pure preservation policy also rejects matching labels in the census before its owned-new-record exception. Original-ID absence, exact whole-tuple digests, complete count/list/count census, sticky failures, bounded subprocess cleanup, host integrity and all lifecycle boundaries remain unchanged.

This is operational package assembly under the existing exception, not direct product implementation. No worker was launched. R6 never executed. Fresh OBSERVE r4 and window r2 remain unconsumed, and the completed WORKTREE, PREP and BIND are unchanged.

## Evidence

- RED: /tmp/ga-mb91-r7-red.xml, SHA-256 279c92be54a49065653fd9ad81f8dd93c0b83b1c8cf06b2663f1fb34fe2475c5 — six failed assertions exposing the one fallback gap, 23 passed.
- Focused GREEN: /tmp/ga-mb91-r7-focused.xml, SHA-256 38c7dbd60159267e11c6c9a7784d1cc6b544be3215f97dee6ce743c5455f7e60 — 72 passed.
- Full package: /tmp/ga-mb91-r7-full.xml, SHA-256 f095c7fef291e79080be9b24b7e40d6b8b9a72dce34b62fcc45854e4ae66e55d — 659 passed, no failures or skips.
- R7-LABEL-CONTROLS.json records actual read-only native counts: all 25 missing-label targets return zero, a positive existing label returns one, and their mixed union returns one. These are coordinator read-only commands, not owned-phase cleanup receipts. A restricted-context transport refusal preceded the successful supported host-context reads; no store or service was started.
- Offline tests cover a census-visible alias with wrong metadata both with and without matching ownership, and native query hits independent of type, class labels and ownership. Transport/schema failure cannot establish absence.
- ASSEMBLY-REVIEW-R7-DELTA.json binds 42 mechanically regenerated outputs among the same 69-file graph. ASSEMBLY-REVIEW-R6.json and TEST-REBINDING-REVIEW-R6.json preserve the predecessor. BIND remains 028ccef1db747088c7f8552c86094ded85b5db12f1d58d890bd7678fa432adea.

These are source and adapter proofs, not live worker or provider-parity acceptance.

## Preserve the R6 review history

Both R6 native final verdicts are HOLD on the same exact candidate and request digest 8587641082327b5fff8cc0daecfc7d0e3f6b597bcbe3e70a2441630caa308428.

- /mnt/c/Users/smoki/.codex/sessions/2026/09/30/rollout-2026-09-30T14-24-15-01a0f245-cd22-7021-8318-505e976ea641.jsonl — SHA-256 0e2d26183153206aaef12d7ce97226f76f440e9265e63806fb975c6322a049ac.
- /mnt/c/Users/smoki/.codex/sessions/2026/09/30/rollout-2026-09-30T14-24-27-01a0f245-f8e9-75c2-bc26-89fede309a78.jsonl — SHA-256 c08e0a1f6fea5de120231f2c779974ad48b64f7f49a3e24c9cfa46b4d57dc002.

The coordinator sent each reviewer an additional source-anchor message. The existing exporter requires exactly one agent-message input, so export refused with "Codex review needs exactly one response_item agent_message". No envelope was fabricated, transcript rewritten or adapter weakened; no R6 job was admitted. Preserve the raw reviews and that refusal. R7 uses fresh one-shot reviews with all anchors in the initial request and no follow-up message.

## Live disposition remains exactly R6

preserve-preflight-refusal.py and PREFLIGHT-REFUSAL-R1.json are byte-unchanged from R6. The failed R5 preflight, all 39 files, the HALTED latch and original done record remain untouched. Refer to WINDOW-REVIEW-R6.md for the exact diagnostic, cleanup and protected-state proof.

After two independent SOURCE_PASS verdicts on one clean signed R7 head: archive only the exact failed latch through the reviewed helper, run fresh OBSERVE r4, require actual host and native-integrity PASS, then PREFLIGHT r2. Continue only on each real PASS through the already-reviewed bounded window and mandatory containment/restoration. No Bead or workflow writes during the quiet interval. No Fable inference, private historical payload copying, new privilege or added worker authority.
