# ga-xyqo full window R2 — ROUTE carry-forward correction

The original candidate 57e753735f0ad3f08446a0a1cdde048ca8400399 is HOLD.
Both independent native Astra reviews agree on the one must-fix: the generated
ROUTE main still called a one-edge predecessor predicate while this fresh task
has exactly two informational relationships. No operational job from that
candidate ran. Completed WORKTREE and PREP are not repeated.

Preserved review envelopes, filed in the existing jobrunner ledger:
- /tmp/ga-xyqo-window-review-20260929-r1/codex-01a0eeb2-c985-70f0-bd32-2c928f49535d.json
- /tmp/ga-xyqo-window-review-20260929-r1/codex-01a0eeb2-fd20-7432-b822-fc6dd8f413fa.json

## Exact repair

task-assembly.py replaces the obsolete ROUTE predicate with the hash-bound
fresh-admission.py continued_task validator already reviewed for this package.
window-assembly.py supplies its exact digest. The generated ROUTE main passes
the loaded window to that consumer; the wrapper and manifest are regenerated.
No admission semantics are broadened: both task snapshots satisfy the exact
bound contract, own fields are equal, both relationships are required, the held
ga-9olv projection is immutable, and only append-only parent audit text with
nondecreasing timezone-aware time may advance. Hash checks are retained.

Only route-task.py and operator/ROUTE.sh change among the 66 runtime files.
The admission helper, transport, worker inputs, PREP receipts, all other
executors, observed baseline, protected paths and epochs remain unchanged.
Current assembly.json SHA-256:
b7dbd10aca9a96a87d04f265a07f5e18715e7bc40431abcd083c4a837f02276b.

## Executed regression evidence

The test now executes the actual generated ROUTE main through its bound-task
predicate, stopping with a fixture sentinel before loading host preroute code.
It permits an unchanged correct two-edge task and permitted parent audit
advancement; eight drift cases refuse before route intent. Dependencies and
control I/O are explicit disposable fixture doubles. No real routing occurs.

- First RED fixture: 4 failures, 6 passes. One genuine one-edge refusal and
  three fixture setup errors due to abbreviated relationship projections.
  /tmp/ga-xyqo-route-r2-red.xml SHA-256
  cd41fcde218431fe6109c5b7bd5553e9f43e54a8abac16c6f1acc230d87cd24d
- Corrected RED fixture with native-shaped audit projections: 2 failures,
  8 passes. Both positive cases fail the old one-edge guard as expected.
  /tmp/ga-xyqo-route-r2-red2.xml SHA-256
  d943c553607544be098e35e857774806cc9a5a71eefaba9711bbba62106b93f4
- Focused GREEN: 30 passes.
  /tmp/ga-xyqo-route-r2-green.xml SHA-256
  e42566b45d8da48b52a281d257fa3a72a5104064f3067ec1f71e1838f3ed9308
- Complete current package: 472 passes, zero failures/errors/skips.
  /tmp/ga-xyqo-window-tests-r2.xml SHA-256
  c28374f7c96dfbe52a5595c277c73de3d2e449e1b905897b40476c3d16fb62aa

The unchanged 3962-pass full adapter/meta regression remains reusable; this is
package wiring, not product implementation or a transport semantics change.
WINDOW-REVIEW.md remains the preserved R1 scope/evidence report; this document
supersedes only its old manifest/test totals and the incomplete task-assembly
claim. All predecessor artifacts and failures are retained.

## Authority and next action

The operator's standing broad completion approval and narrow direct transport
and packaging-bootstrap approval cover this safe source-only correction.
A new hash or review checkpoint is not another operator approval boundary.
Independent review, signed clean HEAD and exact one-job submission remain
mandatory. Two fresh independent SOURCE_PASS verdicts are required before
preserving the completed PREP latch and starting BIND. Disagreement is HOLD.

No new privilege, lifecycle expansion, Fable inference, product source edit,
runtime activation or worker retry occurred while preparing this correction.
No workflow or Bead call has occurred since the exact final read-only baseline.
The original goal remains active; preparation and source review are not live
acceptance or provider parity.
