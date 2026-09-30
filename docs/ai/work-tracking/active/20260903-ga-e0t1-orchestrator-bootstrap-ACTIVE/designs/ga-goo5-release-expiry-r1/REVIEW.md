# ga-goo5 release-observer R13 — source-only candidate

## Outcome and authority
The actual ga-goo5 worker passed startup. RELEASE enqueued once, then refused
Core's native expiry of one older foreign pending message. No product source
was written. Supported containment and restoration passed with zero residue.
The consumed attempt and final successful runner latch remain preserved.
See ../ga-goo5-c1-package/LIVE-OUTCOME.md for exact bindings and the outstanding
child ledger status update. No future rig resume may ignore that stale route.

The standing broad completion grant and narrow direct-bootstrap exception in
../ga-rq5n-release-transport-r3/AUTHORIZATION.md cover this source correction,
its offline tests and deterministic packaging. Product implementation remains
Gas City worker-only. No Fable use, live enqueue, Core change, policy weakening
or new lifecycle operation occurs in this candidate.

## Narrow correction
Exact whole-item equality remains the default. R13 separately accounts only a
pending-to-dead transition of a nonempty foreign session entry whose expiry
already elapsed before the captured baseline lower time. The entire expected
item is constructed from the original item. Only dead_at and Core's conditional
empty last_error to expired assignment may differ.

The native behavior is in Core f45a626213dc5b8d0b52f097d978cca56e506df0,
cmd/gc/cmd_nudge.go at 2058–2067 and 2385–2407. Native enqueue performs global
expiry maintenance. Retained-dead deletion at 2494 is NOT exempted.

The adapter captures integer wall-clock nanosecond brackets around the baseline
and each observation. Timestamps parse RFC3339 with up to nine fraction digits
without floating-point rounding. Reversed intervals and timestamps outside the
captured bounds refuse. The first accepted expired tuple is pinned through every
later observation. Its evidence must persist before acknowledgement can pass.

No removal, in-flight transition, resurrection, additional changed field, altered
message/claim/lease/attempt/source/identity, or unexpired/current-session expiry
is admitted. Queue duplicates and unexpected new IDs still refuse. The original
receipt-plus-native-transcript, exact helper process and session, single enqueue,
bounded wait and no-replay requirements remain.

All consumed R12 files are unchanged. The R13 runtime still names ga-goo5 as a
source fixture, not as a runnable retry. A fresh reviewed package must bind a new
task, state and consumed-root successor before any live attempt. This source
review does not admit any operator wrapper or remove the runner latch.

## Offline evidence
1. Exact preserved RED against R12: one expected historical-queue refusal.
   /tmp/ga-goo5-expiry-red-20260930/results.xml
   SHA256 aa01d71917191824cf0c72ad750b07ee35a393e988c83e58ef35f14b15004f1b.
2. First R13 corpus: 182 passed, one malformed timezone test failed. Python's
   datetime accepts an offset minute of 60. Explicit RFC3339 offset bounds fixed
   this; no assertion removed.
   /tmp/ga-goo5-expiry-r13-first.xml
   SHA256 a9002cc73fc67298429dc7b767f1b2bad7c69b1f74e429b840d0451a3f217a57.
3. Final source corpus: 190 passed, zero failures/skips.
   /tmp/ga-goo5-expiry-r13-green.xml
   SHA256 4693b3cb77dbedd409130b50254dbbdf43287d3e9c86b3514fc3c73e8e14548b.
4. Entire preserved operational R2 package regression: 510 passed, zero failures
   or skips. This proves predecessor preservation, not execution of R13 in R2.
   /tmp/ga-goo5-expiry-predecessor-regression.xml
   SHA256 bf83fbd3c61591126663ece8b4d37fc902c0de9c8e2ebe19b28d981f5b675c60.

conftest.py intentionally aliases the new R13 modules to R12 import names to
replay two byte-identical predecessor test files. New tests cover exact Core
expiry, omitted/empty/nonempty error handling, nanosecond bounds, full-object
mutation, identity, queue deletion/duplicates, immutable accepted history,
recording failure, clock reversal and real adapter wiring with mock-only I/O.

R12 did NOT capture wall-clock brackets. The incident replay uses digest-pinned
real queue/receipt contents and explicitly synthetic time inputs. Its expected
result is pending, never PASS. Without new time evidence the old attempt still
refuses. No retroactive live success or fabricated historical capture is claimed.

## Consolidated independent review
Inspect manifest.json, both R13 modules, conftest and all four test modules.
Compare to the unchanged R12 modules and tests in ../ga-goo5-c1-package.
Verify native Core transformation against the pinned source above. Review the
exact correction, mutation/time/state negatives, unchanged authority functions
and the offline/live distinction. HOLD for concrete safety, correctness, binding
or live-state defects; this is not a request to redesign Core or permissions.

Only after independent source review can a fresh deterministic package be built
and independently reviewed for its actual execution bindings. Child disposition,
fresh state capture, signed candidate and every standing technical gate remain
prerequisites; no new routine operator approval is required within the grant.
