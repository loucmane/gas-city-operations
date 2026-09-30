# ga-rq5n operational R2: pre-staging refusal and exact retry

## What happened and why a fresh operational root is safe

R1 BIND, OBSERVE and PREFLIGHT passed. STAGE refused at its first read-only
queue audit because held predecessor ga-9olv still had open status and route
metadata. No stage intent or lifecycle mutation occurred. Full disposition and
hashes are in PRESTAGE-REFUSAL.md. R1 failed roots and HALTED remain preserved.
Completed WORKTREE PREP and BIND must never run again.

A supported status-only update now makes ga-9olv blocked. A fresh supported
ready query returned an empty eligible queue. Only status and updated_at changed;
all other projected fields, source and HOLD remain exact. The frozen readback is
held-predecessor-disposition.json SHA256
794b7dae9abaab30c11560e02875f2e193ad5ffea97620c653af0417b0da7e51.

This retry remains ga-rq5n in its already prepared workspace. Its own fields,
binding, prepared city image, launch receipt, brief, probe, file scope and rules
are unchanged. It has never been routed, claimed or launched.

## Bounded executable change

The actual R1 route-task continued_task still expected one dependency and would
have refused the fresh two-edge contract. test_retry.py reproduces this using
the genuine BIND readback, then calls the actual generated R2 comparator.

R2 checks the exact digest-bound supported predecessor disposition, proves only
open to blocked and updated_at changed, requires its before projection to match
the genuine immutable BIND receipt, and compares current state through the
existing digest-checked fresh-admission two-edge function. It neither rewrites
history nor admits other drift. Parent append-only audit remains the only
previously allowed moving field. Actual route main calls this function before
the route preview or mutation.

The pure assembler verifies every R1 manifest byte first, retargets operational
roots only, rebinds the exact hash graph, and leaves eleven prepared worker
inputs byte-identical. It omits the consumed BIND executor and wrapper; WORKTREE
and PREP were already omitted. Output is 65 files and 28 one-use wrappers.

preserve-halt.py only archives the adjudicated latch using no-replace rename.
It verifies clean signed candidate and its own committed bytes. Its sole failed
job exception is the exact R1 STAGE done and halt digests, exact disposition,
absent stage markers, and unchanged city and receipt bytes. R2 success cases
still require exit zero and inactive unit. It never queues or runs a job.

## Tests and review boundary

43 focused fixture tests pass in 0.32 seconds with cache disabled.
Evidence /tmp/ga-rq5n-r2-focused-20260929-r2.xml.
Cases cover exact route main integration, immutable BIND, admitted parent audit,
reordered relations, all other task and predecessor drift, missing duplicate
extra or blocking edges, malformed disposition, hash failure, fresh root
constraints, exact worker input preservation and latch refusal cases.
The inherited full 324-test package corpus will run on the final materialization.
These are source/fixture proofs, not worker or provider-parity acceptance.

Two independent Astra read-only reviews of the signed clean candidate are
required before execution. No Fable or Claude inference. All review verdicts
are preserved. Product remains HOLD and will be changed only by the single
released Gas City Astra worker, never the coordinator.

## Execution after two SOURCE_PASS verdicts

Preserve the adjudicated failed R1 latch. Run fresh R2 OBSERVE then PREFLIGHT
then STAGE then ROUTE then RESUME. Validate actual startup evidence and claim
before RELEASE. Bounded WATCH, CONTAIN, CLOSE, ADMIT, RESTORE and TERMINAL follow
the inherited reviewed protocol, with INSPECT afterward. HOLD is only the
inherited recovery disposition, not an unconditional normal step.
Inspect each job outcome before the next; preserve every latch and root.

Keep this candidate clean while jobs run. No workflow or Bead write, unguarded
gc, operator tmux pane or coordinator Git in the worker workspace during the
live interval. Same suspension, process, namespace, protected-cache, exact
44-file exception, negative permissions, single worker, budgets, rollback and
zero-residue controls remain. No original goal milestone is claimed by this
candidate-only task. Stop on the standing excluded boundaries.

## Frozen final pins

Supported workflow verification passed all six checks at 18:53:41 CEST.
No subsequent workflow or Bead command ran after the final capture.
Final baseline /tmp/ga-rq5n-readonly-baseline-20260929-r3/result.json
SHA256 c28f77526b1a7e1fc552dc7d0955af8eb19f83d0ded751db0396cfdced17c288.
Observation SHA256 cdfa5061975d05775badc707685579ce04842be7e7ad3bea0d7bee0b8a15953c.
Cache mtime and ctime 1790700821105650609. No other non-atime or provider drift.
All 8624 workspace entries match prior SHA256
9da345d5bc5761199ef1ee0549a698097198dba08056db3dfd63949bc874765f.

All 65 materialized files match pure assembly byte for byte. Manifest SHA256
f11bc73c0f12810329a801dc11320bd06e328b275271fd3d050f9d5c9dbf672e.
Full inherited plus retry corpus: 367 passed, no failures or skips, 1.44 seconds.
JUnit /tmp/ga-rq5n-window-r2-full-20260929-r1.xml SHA256
89298b77480e4a4f068e84d2cbcd1f0eeb614132c8253f3bfd52a6dcc80cd748.

Pre-review append-forward housekeeping removed one extra EOF blank line in
preserve-halt.py after the staged diff check flagged it. The earlier signed
commit remains preserved. No executable behavior or generated window byte
changed; only that review-input digest and this manifest reference changed.
Final materialized rerun also passed 367 tests in 1.39 seconds with no skips.

## Review correction before any R2 execution

Both independent reviewers held signed candidate
c647c67c03b294dbe11ed3832c5d78679497507c. Both genuine native envelopes
are filed against that candidate under the runner. No R2 job was queued.
A export SHA256 c96aaf59547ee39afcae9b494f4518e068e703b39a55f6f4c1972df1e51c9def.
B export SHA256 4d34b8eae4bd57a31bc7afe853499fc73dfaa1c7e8abc1a949b0beb0ded7b89e.
B's verdict line has a shortened hash typo; its untouched request and envelope
bind the actual candidate and its disposition is HOLD, never an execution grant.

Must-fix one: unrestricted package-name substitution also changed the prepared
branch in common Git observation and candidate inspection. Retargeting now
matches only package/staging path prefixes. The exact prepared branch remains.
Must-fix two: CLOSE constructed its release proof from VAR and a relative R1
fragment. Retargeting now covers absolute and constructed operational roots,
while retaining only completed WORKTREE PREP and BIND R1 references.

The actual common branch consumer and actual CLOSE binding snippet reproduce
three failing assertions before the fix. RED evidence
/tmp/ga-rq5n-r2-review-red-20260929.xml SHA256
320fb0a889a7ec5699f401e9f8a85aa3fc5e38c6a545d1e26e76ef8a10445864.
Matching and mismatched current-release sessions now pass their respective
positive and refusal cases. No preexisting assertion was weakened.
All 46 focused tests pass. Full 370-test corpus passes in 1.43 seconds with
zero failures or skips at /tmp/ga-rq5n-r2-corrected-full-20260929.xml SHA256
32d5a67b8529cb0ca502adc4a89afb949e47824aff794d4ef8b03a878422dd3f.

This supersedes only the earlier R2 candidate manifest with current SHA256
c0e21b91c682612fdfab848ebb7493f082a5f0c7eb73faaefe82346f25a686be.
All 65 generated files match the corrected pure assembler. All eleven prepared
inputs and the held predecessor disposition remain byte-identical. The final
baseline and all consumed artifacts remain valid and unchanged. No workflow or
Bead call occurred after capture. Two fresh independent reviews remain required.
