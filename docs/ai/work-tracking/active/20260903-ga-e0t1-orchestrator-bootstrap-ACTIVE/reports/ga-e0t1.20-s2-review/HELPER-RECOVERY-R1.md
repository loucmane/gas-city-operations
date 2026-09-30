# ga-e0t1.20 exact helper recovery R1

Prepared 2026-09-28 after the operator approved the recorded archival disposition,
diagnostic correction, restoration proof and independent review. This is not
product implementation, another baseline exception or a worker launch.

## Exact operation

The stopped read-only inspection materialized only
`.gc/scripts/gc-beads-bd.sh` in the preserved worker workspace. Its 312 bytes,
SHA-256 a7bcaa7cce9261b987bb766fba19db46cc7f4ae8d8b22b6d8059bb884d8788d2,
uid/gid 1000, mode 0755, single link, device 2096, inode 8934271 and exact
mtime/ctime are frozen in the executor. The archive root is fresh and create-only:
`/var/tmp/ga-e0t1.20-helper-archive-20260928-r1`.

Only that file is renamed, using anchored directory descriptors and Linux
renameat2 NOREPLACE. Its inode, bytes, mode, ownership and mtime remain exact.
The rename necessarily changes its ctime and its source directory times; those
are not falsely claimed unchanged. Nothing is deleted and no destination is
overwritten. A partial disposition stops with source/archive presence recorded.
There is no automatic inverse operation, repeat or failure-to-success relabeling.

## Diagnostic correction

The deployed Core source establishes eager pack discovery before explicit city
flag parsing. The precise individual incident syscall was not traced. Corrected
reads run with cwd and GC_CITY set to the actual city and with the entire host
filesystem mounted read-only in an existing bubblewrap namespace. The protected
workspace, Git administration, city and pack cache mounts and descendants must
be read-only. Actual host runtime and service identity are checked outside the
namespace; root authority is not inferred from remapped ownership.

The inspection is bounded by the already-pinned owned-process runner. Exit,
timeout, errors, child reap, group disappearance and unexpected survivors all
gate continuation. The archive executor itself can run only in the exact
`gc-job-ga-e0t1-20-helper-recover-r1.service` job. The runner is expected to be
executing this job, not HALTED during it; it halts again after completion.

## Fresh verification

- 21 focused tests pass on the actual host, JUnit
  `/tmp/ga-e0t1-helper-fixtures-20260928-r4.xml`, SHA-256
  a4362f4f6e8d05d6022ec52e58ce4f96189f4e4f37895aec1f59c71a6c32fbb9.
- Real disposable namespace proves reads succeed and child writes fail with
  EROFS. Drift and overwrite tests preserve both files; replay refuses.
- Fresh production read-only pre-inspection passes: 8037 entries including the
  one helper; all original 8036 entries exact; workspace unchanged by inspection;
  zero sessions; city and every rig suspended. No archive operation occurred.
- Preserved fixture intermediates include the root-ownership namespace mismatch
  and the quoting error, followed by their corrected passing tests. Those are not
  live mutations and are not reported as successes.
- Existing workflow verification passes all six gates. An unnecessary resume
  attempt refused because it re-enters kickoff with open repair dependencies.
  Existing ready journal ownership already permits those attached repairs; no
  dependency or ownership was changed to bypass that refusal.

## Review and execution boundary

Review only `operator/RECOVER-HELPER-R7.sh`, its exact pinned generator and tests.
The same commit preserves the assembled full R7 window, but this review must not
approve its other wrappers. Full R7 acceptance remains separately required.
No completed PREP, BIND, ROUTE or R6 operation may replay.

After two independent SOURCE_PASS verdicts on the signed clean candidate,
queue exactly job `ga-e0t1-20-helper-recover-r1` through the installed runner.
The original helper baseline and source checks are strict after recovery: all
8036 entries, exact recovered claim history, HEAD, task status, suspended state
and unchanged host epochs must pass. Keep the resulting archive and failed
evidence. Only then rerun the strict R7 workspace check and the complete
operational package tests and reviews. No product task acceptance is claimed.
