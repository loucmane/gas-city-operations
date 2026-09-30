# Native claim-time correction — 2026-09-28 CEST

Candidate 0db1a66ed3d990ed0016f658af6dca209340af7f received one SOURCE_PASS and
one HOLD. Both lossless native envelopes were filed before edits. Requests and
envelopes are preserved in /tmp/ga-e0t1-20-s2-reviews-20260928-r3. No job ran.

The HOLD identified a real compatibility defect: the native claim introduces
started_at, absent from the unclaimed snapshot. The bound infrastructure task
record at /var/tmp/gct-mbg6-watch-20260927T073050Z/task-phase.json has start
2026-09-27T07:10:24Z and update 2026-09-27T07:10:25Z; its native session was
created at 2026-09-27T07:09:55Z. The validator incorrectly treated that normal
claim field as an unrelated mutation. No product source repair is involved.

RED adds started_at to the existing native claim fixture and fails for exactly
that field: /tmp/ga-e0t1-20-started-at-red-20260928-r1.xml. The correction admits
only an absent-to-valid-UTC first start time, ordered after task creation,
routing and session creation, and before the current task update. Nanosecond
ordering is preserved. Missing, malformed, already-present and out-of-order
start times refuse; all other task fields, exact owner and session metadata,
notes, policy, source and native denial checks remain mandatory.

The nonblocking active-session polling regression is also included: an ID
replacement during drain polling receives neither drain nor close. The stale
package README test-module count is corrected from five to six.

Focused GREEN: 158 passed, zero failures/skips, 1.89 seconds, preserved at
/tmp/ga-e0t1-20-started-at-green-20260928-r1.xml. Fixtures remain isolated; this
is not live worker or provider-parity evidence. Fresh signed-candidate reviews
and unchanged live preconditions are required before any S2 job. Completed S1
WORKTREE and PREP must not be repeated. The long goal and three-file worker
scope remain unchanged.

Final workflow verification passed all six checks at 01:34:22 CEST. The r4
read-only baseline follows all coordinator recording. It observes the same
8015-entry workspace image, no provider differences and only the declared
cache directory timestamp pair. The exact pair is 1790552062805742810 and
observation SHA-256 is
7f8dd40546a23fc460d190ba08d9a22953c91b4c2ce875c38dccbddbdd97e7d7.
The preserved r3 observation and held head are not overwritten or reused.
