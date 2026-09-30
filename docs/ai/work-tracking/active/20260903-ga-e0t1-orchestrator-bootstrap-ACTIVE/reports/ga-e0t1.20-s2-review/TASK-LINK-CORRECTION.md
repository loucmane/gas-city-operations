# Exact task-link correction, not a readiness exemption

2026-09-28 CEST. This is the bounded operational package correction selected
after the preserved route-audit failure and proven terminal recovery. The
investigation reached a concrete cause and decision before its ninety-minute
limit. It does not introduce a new worker profile or change product source.

## Why this edge is wrong

The task's only edge, ga-e0t1.20 parent-child ga-e0t1, was explicitly intended
and reviewed as nonblocking. Installed Beads 1.2.2 inherits the parent's blocked
state through that edge. Live blocked readback names ga-e0t1 as the only blocker.
The child is an independent three-file candidate repair, not work requiring all
of the parent's remaining live acceptance to finish before it can begin.

Correct only that edge to the supported informational `related` type. Do not
change the parent's five outstanding blocks edges, close any prerequisite,
change derived blocked state directly, add a ready exemption, or reroute. Keep
the same task ID, status, notes, metadata, worktree and existing completed route.

## Executable contract

The new reconcile-task-link.py and operator/RECONCILE-LINK.sh are the only new
operational executor and wrapper. They bind the prior successful TERMINAL and
ROUTE task image by exact digests, use the pinned existing host observer and
owned-phase runner, require the actual stable host and all four rigs suspended
with zero native sessions, and verify exact restored configuration and receipt.

The supported API refuses changing an existing edge's type in place. Therefore
the executor writes a durable intent, removes only that exact edge, verifies
the complete expected child and parent images, then writes another intent and
adds the same pair with type related. Every command is store-scoped. All issue
fields including timestamps must remain exact; only the computed parent field,
dependency edge and corresponding counts may change. The parent prerequisite
records remain exact. All command results and containment evidence are kept.

This is explicitly not an atomic database transaction. If either write fails,
times out, loses containment or produces any unexpected readback, execution
stops with the consumed root and intents preserved. There is no automatic
retry, guessed rollback, SQL fallback or lifecycle action. In particular, a
known intermediate without an edge is not a PASS and cannot release a worker.
Any recovery needs its own exact reviewed disposition under the standing grant.

Final acceptance requires the normal routed-ready query to return exactly
ga-e0t1.20, the child to disappear from blocked results, every other reported
blocking relationship to remain unchanged, and final exact task/parent/host
readbacks. This is readiness evidence only. A later window still requires an
append-forward package binding that consumes this receipt without changing or
replaying original BIND/ROUTE evidence. No old window or wrapper may be reused.

## Tests and review boundary

The 34 focused offline tests pass in
/tmp/ga-e0t1-20-link-tests-20260928-r1.xml. They execute the real transition
function against a fake supported API, cover exact before/intermediate/after
images, preservation of parent prerequisites and child identity, refusal of a
real blocks edge or other edge shape, write-ahead ordering, every phase's
failure without replay, immediate drift, and the four-rig/zero-session guard.
They are not live API, host or worker proof. Full operational regression and
two independent exact signed-head reviews remain delivery gates.

Final full operational regression: 304 passed, zero failed or skipped, in
/tmp/ga-e0t1-20-link-full-20260928-r1.xml. The previous 270 tests remain intact.
No shared runtime or worker product source changed; this is an additional
one-shot operational reconciliation job and its tests.

Review must decide whether this corrects the documented nonblocking intent
without removing a real prerequisite, whether both complete ledger images and
partial-failure handling are sound, and whether retained native readiness and
host checks are sufficient. A SOURCE_PASS only admits this one ledger job. It
does not admit any old worker wrapper or grant source editing to the coordinator.
