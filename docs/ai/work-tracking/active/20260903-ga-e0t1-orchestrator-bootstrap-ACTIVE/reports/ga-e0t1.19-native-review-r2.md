# ga-e0t1.19 — independent review correction

2026-09-27 CEST. Source-only successor; no installed runner change, queued job,
worker, rig lifecycle, or Claude inference.

## Preserved independent review

Both independent Astra aegis-reviewer agents returned HOLD for signed candidate
`0ae76afc00127f8705c6a2efb2416da0fdae1178`. They identified the same defect: the
native task content was checked only as a nonempty list, permitting malformed or
non-NEW_TASK content despite the documented one-shot task contract. Neither review
reported another must-fix or should-fix. Their native source transcripts remain at
the recorded Codex session paths, and create-only lossless exports remain in
`/tmp/ga-e0t1.19-native-review-exports-20260927/`:

- `codex-01a0e405-c112-7fd2-9262-3de7d57bd5be.json`, SHA-256
  `f7f06d42c0f178123cfd8bed42cba37d6038280211237a0659db8a4eba1d92b7`.
- `codex-01a0e405-ef15-73f3-b046-8535a9980322.json`, SHA-256
  `d447aa9bb8953dd0b6e9f57aa00e651444670a32a7eb89d259aaee029c2788c4`.

The HOLDs are not withdrawn or relabeled. The successor requires new independent
verdicts bound to its own signed commit.

## Narrow correction and proof

The native task must now have exactly two content objects in order: the exact
NEW_TASK header bound to the validated parent and recipient, then a closed-shape
encrypted-content object containing a nonblank string. This checks structure only;
it neither decrypts ciphertext nor claims to prove the plaintext request. The
explicit native final-answer request-digest acknowledgment remains the binding.
All other parser, existing Claude, delivery, execution and safety gates are intact.
Only the runner, its two digest pins and the focused tests change in production.

The regression covers null and empty objects, MESSAGE rather than NEW_TASK, wrong
task name and sender, missing/empty/non-string ciphertext, extra content and reversed
order. Before the fix the new test failed because malformed content was admitted.
After the fix all 16 native tests and all 57 runner tests pass.

Exact reports preserved here and at their original `/tmp/` paths:

- `ga-e0t1.19-review-r2-red-20260927.xml`: 1 failed, 15 deselected;
  SHA-256 `68c6f4fc064c5dd062a55a6c68c42f297780a2d2b7626bd705412464b8c11b0a`.
- `ga-e0t1.19-review-r2-green-20260927.xml`: 16 passed;
  SHA-256 `e25a35830f1cdfa7781e837211239c2df471a7dd604b00a7101ff5b928d417d6`.
- `ga-e0t1.19-review-r2-regression-20260927.xml`: 57 passed;
  SHA-256 `39c243f9abbe85dea1014e54f16796925317187638870e5923471144b563e588`.

New runner SHA-256:
`b5cdfeefb79f982f52bb0deee20729c4772bdc75f39950911a4eeb71e793199f`.
The shared adapter/meta inputs remain unchanged from the 3962-pass, 21-skip full
regression recorded in the preceding report; the focused 57-test run covers this
new runner delta. No source result is being counted as live acceptance.

Next: verify and freeze the signed successor, obtain two independent Astra delta
reviews, validate the genuine exports offline, then retain the standing delivery
and independently reviewed activation boundaries. The separate C1 CLOSE defect and
provider handover acceptance remain open.
