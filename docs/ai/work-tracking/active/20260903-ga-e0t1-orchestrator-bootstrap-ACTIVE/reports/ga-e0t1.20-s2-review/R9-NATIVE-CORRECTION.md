# R9 preparation successor after independent native-format HOLD

2026-09-29 CEST. Original goal and ga-e0t1.20 remain active and incomplete.
No worker or package job was launched. R8 remains fully restored and the runner
HALTED latch remains unchanged. No permission, service or product source changed.

## Preserved review and demonstrated defects

Signed candidate 83c2875764608ec779b0039cadfb421fdb90412e received one
SOURCE_PASS and one HOLD. Both genuine native reviews are exported under
`/tmp/ga-e0t1-r9-preparation-reviews-20260929` and filed with the runner.
Request digest 99389a0da56b7583d722a8dfa893f25078dc52c08fe47b4b0208128ab6742f1c.
The held candidate cannot execute and is not replayed or relabeled.

The HOLD found two inert waiting-helper defects. Native completion includes a
token_usage_record between final answer and completion. Native timestamps also
retain zero fractional suffixes, unlike Core RFC3339Nano canonical strings.
The captured R8 transcript is bound at SHA-256
606cc6668ac00b1655cb9a648ece40cba296848bc461f78a02b3776d208c9147.
The new positive fixture preserves its full native ordering and accounting,
substituting only the final response text and completion text with the future
waiting marker. This is a synthetic format regression, not live waiting proof.
The initial run has six failures demonstrating the two defects:
`/tmp/ga-e0t1-r9-native-red-20260929.xml`.

## Exact correction

Only generators/review_wait_r9.py and its existing test module change executable
behavior. Native final, completion and accounting timestamps may retain decimal
zero suffixes; UTC format, calendar, nanosecond precision and chronology remain
strict. Core chronology and signature strings retain the original canonical rule.

Native usage records may occur between the final response and completion only
with the exact closed record and payload shapes, nonnegative integer counters,
the native session and completed-turn identity, and bounded chronological position.
Unexpected activity, unknown record types, extra payload fields, foreign identity,
malformed counters and timing still refuse. The original token_count classification
is unchanged. These additional checks do not authenticate or grant release.

All prior full-task, ownership, route, metadata, source, workspace, permissions,
double validation, exact immediate race and transcript-stability checks remain.
The five materialized preparation payloads, their manifest and authoring generators
are byte-identical to the reviewed preparation. No output root is consumed.

## Verification and next action

- Focused corrected modules: 99 PASS, zero skips or failures, at
  `/tmp/ga-e0t1-r9-native-green-20260929.xml`.
- Final applicable host operational corpus: 930 PASS and the same two disclosed
  historical-baseline deselections, at
  `/tmp/ga-e0t1-r9-final-generators-host-r2-20260929.xml`.
- Existing 42-case materialized contract evidence remains valid because its
  exact inputs and executable files are unchanged.
- Preparation-manifest payload parity and whitespace checks pass.
- Primary Bead note records both reviews and the understood correction through
  the supported coordination operation. No worker Bead or claim was changed.

Obtain two new independent Astra reviews binding the exact signed successor.
Only the unchanged create-only PROMPT-PREP-R9 wrapper is proposed for admission.
Full R9 window assembly and its independent review remain separate afterward.
No operator microapproval is required for this safely pre-execution correction
under the standing grant. Product implementation remains Gas City worker-only.
