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
6190f4479288d7929d65622e6f6d76488cc3767948c147584c93e7a14bbe3400.
Full inherited plus retry corpus: 367 passed, no failures or skips, 1.44 seconds.
JUnit /tmp/ga-rq5n-window-r2-full-20260929-r1.xml SHA256
89298b77480e4a4f068e84d2cbcd1f0eeb614132c8253f3bfd52a6dcc80cd748.
