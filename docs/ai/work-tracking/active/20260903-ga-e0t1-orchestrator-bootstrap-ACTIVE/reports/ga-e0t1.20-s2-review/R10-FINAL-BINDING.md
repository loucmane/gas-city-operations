# R10 final binding — 2026-09-29 CEST

All coordinator notes, tracking and verification finished before the final native
read-only capture. Workflow verification at 02:16:22 CEST passed all six checks;
the journal was ready with no pending intent. No workflow or Beads operation has
run after that freeze. No R10 worker is running and the completed prompt preparation
halt is preserved. Product implementation remains solely assigned to Gas City.

## Exact final observation

Root `/tmp/ga-e0t1-20-readonly-baseline-20260929-r15`:

- `result.json`: `50feeeb7c0f17adff3c2674b22a4fe3d1309812553fd1bee5025a7ce39fc17db`
- `observed.json`: `bb9d8baae2afa0fec6b7d19fb5d9d39a6868e8285b274ed22746519591163b7f`
- `workspace.json`: `d0d2333b69bcc6851560edec42fd180b5dc88d288968c7deaa81248106754d9a`

The complete comparison to R9's accepted terminal endpoint permits precisely the
cache directory mtime and ctime change from 1790637004449701379 to
1790640982604952235. The named directory is
`/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git`.
Both timestamp constants in the materialized runtime equal the latter exact value.
No timestamp was written or normalized. Provider deltas are empty; all8045 worker
workspace entries satisfy the strict preserved-history proof. A fresh metadata
reread after the final tests still matches this exact pair.

## Final source validation

- `/tmp/ga-e0t1-r10-final-full-20260929.xml`:
  1010 passed, four disclosed stale historical actual-workspace positives
  deselected; SHA-256 `a657324f445c5f48daeac325596af3511bb0d9617d1b4bdba58454a3a96a4d58`.
- `/tmp/ga-e0t1-r10-final-materialized-20260929.xml`:
  42 passed; SHA-256 `dc5804ae7e5529fef2c31f84866c91c5202f5823ce88fc322052a60a1d8a149c`.
- All122 generated files match assembly SHA and intended modes. Shell wrappers
  are0755 and other generated files0644. No negative test is omitted.
- Final `assembly.json` SHA-256:
  `58cd3aaf0384037fb48085560c76f09c4f24785f5bac79175ddc053fbb4d62e5`.

The four historical positives are test_prior_workspace_bytes_preserved_and_new_evidence_separated,
test_actual_preserved_workspace_and_immutable_prior_evidence,
test_current_r9_workspace_has_exact_r8_history and
test_workspace_proof_reuses_strict_preserved_r8_validator. Their old fixtures
predate the preserved R9 evidence. Current R10 exact-workspace positive and eight
prior-file tamper negatives replace no security assertion and remain included.

## Next controlled transition

Sign this clean operational candidate, obtain two independent Astra SOURCE_PASS
verdicts and file both genuine native envelopes. Preserve the successful preparation
halt without replacement after exact done-record verification. Then AMEND-R10,
OBSERVE, PREFLIGHT, STAGE and RESUME through the reviewed job runner only. Independently
review actual startup evidence before RELEASE. On any refusal, use the admitted
containment/restoration path and preserve the result. Do not repeat original S1,
WORKTREE, BIND, ROUTE, prompt preparation or consumed amendments.

This is final source/test evidence, not live launch, worker success, intake,
provider parity, handover or goal completion. The full original goal stays active.
