# ga-rq5n R1 pre-staging refusal

Signed candidate 5117ef67925d7489b2f2bc7fb5d9ae076dfaaefd received two
independent SOURCE_PASS reviews. BIND OBSERVE and PREFLIGHT passed. STAGE
stopped at its first read-only queue audit at 18:32:09 CEST on 2026-09-29.
The held predecessor ga-9olv was still open unassigned and routed. The queue
correctly refused to permit another eligible task. This was a coordinator
ledger omission rather than a reason to filter or weaken the queue check.

No stage intent or mutation was entered. City configuration and receipt bytes
equal their exact preflight preimages. The actual host and workspace were
re-observed without unexplained drift. Every audit subprocess was reaped with
no signal and no residue. No worker launched and no rig was resumed.
The logical attempt is ended as a pre-staging refusal with no rollback needed.
Completed BIND WORKTREE and PREP will not be replayed. The old window and audit
roots plus HALTED remain preserved. No live window is open.

Evidence:
- stage log SHA256 f4c7f11ca829f59281c21f08aa88978485ef51be02461b5d08f76062229187f7
- stage done SHA256 2de86612ca1d637e0508606d075abe21a1d7a32c12e2a6a977dbc8c7d60a128a
- HALTED SHA256 babb489e079572081261a95d8086886b66602a477e3d8e4319c9ecac903f95c4
- disposition /tmp/ga-rq5n-prestage-stop-20260929-r1/prestage-disposition.json
  SHA256 bf2bff017ecbfb107b5da3194aa3c78081d2d21d3788a1b63e7c1f7b34ad9caa
- host capture result SHA256 7e6099d1830087d92dbdb5e580e1f1f969e1e20227a5974c47d19942ff0c5200

The supported literal status-only update marked ga-9olv blocked. Readback
proves only status and updated_at changed; notes route metadata and all other
projected fields remain exact. No PASS closeout is claimed. The exact before
and after projection is /tmp/ga-rq5n-held-predecessor-disposition-20260929.json
SHA256 794b7dae9abaab30c11560e02875f2e193ad5ffea97620c653af0417b0da7e51.
Two earlier composed or verbose-note updates were parser-refused before
execution. The documented status-only command succeeded without a gate change.
One sandboxed readback could not reach Dolt; the authorized host readback passed.

Review of downstream routing also found that its inherited inline comparator
still assumed one edge while the new task has two. R2 must exercise the real
route comparator and use the already-reviewed exact two-edge comparison.
It must account for only the frozen blocked-status disposition above and
continue to reject every unrecorded dependency or own-field change.

R2 is a fresh operational attempt on the same untouched worker workspace and
same task. It requires fresh host admission and two independent reviews.
Original product HOLDs and all source candidates stay preserved. No product
implementation or native worker fallback occurs in this coordinator lane.
