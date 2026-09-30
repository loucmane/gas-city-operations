# R9 — admit every fixed output root before the first observation

## Preserved live outcome and recovery

Signed R8 `6cc92974400e54e9cbfd9c74c8bca8ba82dc7f5c` received two independent
SOURCE_PASS reviews. OBSERVE r5 and PREFLIGHT r3 passed. STAGE r2 then refused
at the audit helper's exclusive mkdir of the already-consumed
`/var/tmp/ga-mb91-audit-stage-20260930-r1`. The stage entrypoint never ran:
there was no stage-consumed record, route, resume or worker launch.

Failure log SHA-256
`681e90c44385f413c0898ee105c87794d05a8285b617255232df483778bb0d30`;
done-record SHA-256
`599d4e7a98280301bcd2b434d92765bf7c2ceb779eb8915d0dbbfaa6c8739fee`.
Their full paths and the unchanged R8 manifest are preserved in the delta file
and `ASSEMBLY-REVIEW-R8.json`.

Exact recovery helper `/tmp/ga-mb91-prestage-refusal-20260930-r3.py`, SHA-256
`9618afc4b41179f0011edb9522feef30567e0ef2cb39751c5e21e6779b216a65`,
passed independent reviewers aegis_mb91_prestage_a and aegis_mb91_prestage_b.
It reverified the real host and process identities, suspended zero-session
state, and exact bytes and ALL metadata fields of city, receipt and suspension.
It exclusively wrote the proof and no-replace archived only the failed latch.
No job was queued or retried and no service changed. The proof at
`/tmp/ga-mb91-prestage-refusal-20260930-r3.json` has SHA-256
`88b7d242043ef80966f2185f57c81ff7a617e208481e2b457c5fac05298bad8d`.
All failed roots remain untouched. The no-live-transition window is ended.

Recovery r1's read-only check passed but review questioned unbounded atime
omission. R2 used a closed policy on two unsupported paths and both review and
its read-only check refused. Neither was applied. R3 instead compares every
metadata field exactly, with no exemption; its check and apply both passed.
R1 and R2 source and review history remain preserved. During recovery a
workflow log --help query ran read-only before terminal disposition; it made
no state change but is recorded as a quiet-window procedure deviation, not
precedent for workflow calls in a future live window.

## Narrow operational correction

- Fresh OBSERVE r6 and window r4 preserve the consumed r5/r3 evidence.
- All three audit modes and their wrapper consumers bind audit r2, including
  the parameterized `%s` output family that R8 missed.
- The assembler derives all nine fixed create-only output roots from the
  generated source AST. Missing, duplicate, nonliteral or out-of-scope roots
  refuse assembly. The first OBSERVE wrapper checks the whole inventory for
  existing objects or dangling symlinks before executing the observer.
- WORKTREE, PREP and BIND remain completed, unchanged and unreplayed. Historical
  restoration evidence is not classified as fresh output. Timestamped
  WATCH/HOLD/CLOSE roots retain their own exclusive creation checks; the inert
  legacy restore helper remains excluded from runnable wrappers.
- This early check does not replace any later exclusive creation, identity,
  source, permission, snapshot or lifecycle check. It grants no new write root.
- The signed-parent delta changes 45 of 69 generated files, predominantly
  transitive digests and exact root bindings. Native process validation,
  the 44-file exception, candidate scope, provider, worker prompt and prepared
  receipts stay unchanged. No product implementation occurred in this repair.

## Test evidence

- RED `/tmp/ga-mb91-r9-red.xml`, SHA-256
  `ee275517f7c3d0dcb9d0882e9e742c0a052cb220fb9ab76dbbc6a4ae755de230`:
  15 failures primarily from missing guard/inventory, not 15 distinct defects.
- Focused `/tmp/ga-mb91-r9-focused.xml`, SHA-256
  `5d3a767cb71fb06f1e66d44190ca977fe5a8f0bc290b49f22813da367d024b07`:
  14 pass, one materialization comparison deliberately deselected until generation.
- Full `/tmp/ga-mb91-r9-full.xml`, SHA-256
  `86675a9e2015be706407e79fb5bc0ba60f4b829192a1b45e115313abb17f9c9e`:
  **684 pass, zero failures or skips**.

The guard tests execute only its extracted shell block with every path replaced
by a disposable fixture path. A marker proves positive reachability and absence
after each directory, regular-file and dangling-symlink collision. They never
execute a generated wrapper, native gc, service or live worker. Existing tests
retain assertions and update only exact successor path expectations.

## Continuation

After clean signing and two independent reviews, execute OBSERVE r6,
PREFLIGHT r4, STAGE r3, then the unconsumed ROUTE r2 and bounded worker sequence.
Use only actual PASS results; preserve all failures. Required containment,
close, restoration and terminal proof remain unchanged. Do not repeat completed
setup. No source or ledger mutation inside the next quiet window. ASTRA only.
The standing grant covers this understood pre-mutation successor; a new digest
is not a new operator-approval requirement. No usable-worker/parity PASS yet.
