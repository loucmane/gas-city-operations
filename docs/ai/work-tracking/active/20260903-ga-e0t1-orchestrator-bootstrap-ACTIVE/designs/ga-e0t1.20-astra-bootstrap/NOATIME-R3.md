# S1 WORKTREE r3 — pre-mutation observation correction

At 22:50:07 CEST on 2026-09-27, job ga-e0t1-20-s1-worktree-r2 exited 1.
The source and wrapper were admitted and the live job executed its preflight.
The first protected policy read updated that file's access time and its strict
full-stat equality check refused. No intent root, linked worktree, branch, rules
or worker was created. The job unit is inactive and its result and wrapper log
are preserved. HALTED remains set until the outcome is recorded and acknowledged.

The observed default-rules atime is exactly the failing job time. Its mtime and
ctime remain September 9, and its digest still equals the pinned value. The
disposable regression reproduces the old failure on a stale-atime file, then
proves the successor leaves every stat field unchanged. Symlink and wrong-digest
negatives still refuse. S5 PREP already uses O_NOATIME, so it needs no change.

The successor executor is a preserved copy with exactly two additions of
O_NOATIME: the bounded file reader and provider-binary reader. No comparison is
removed or relaxed. The original code, source candidate and failed job stay
untouched. The new WORKTREE-R3 entry differs only in executor filename and digest.
Fresh independent review of the signed successor is required before admission.

The whole pre-mutation main path is also checked without creation: write is
replaced by a hard refusal, Git is restricted to the four read-only verbs used
by preflight, and the first output-root mkdir raises a diagnostic completion
sentinel. This diagnostic is not a job or a substitute for live execution.
It prevents repeating partial checks while overlooking a later precondition.

Only the documented metadata-read side effect occurred. The source digest,
mtime, ctime, ownership and permission state are unchanged. No persistent task
mutation occurred, so the standing safe-retry grant covers this corrected job.
