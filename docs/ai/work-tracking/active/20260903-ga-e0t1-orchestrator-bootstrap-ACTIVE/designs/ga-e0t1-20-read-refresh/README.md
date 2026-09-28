# Bounded read refresh before ga-e0t1.20 S2

This is an operational preparation job, not product implementation or worker
admission. The three C1 product files remain for the Gas City worker alone.
Standing corrected-package authority applies. No additional permission check is
relaxed. In particular, S2's existing nineteen-hour age predicate stays unchanged.

## Why this is necessary

The independently reviewed 44-file common-Git exception is complete. OBSERVE r3
passed, then PREFLIGHT r2 refused before creating its window root because the
suspension file's access time was over nineteen hours old. The Linux relatime
mount does not advance an otherwise unchanged object's access time on ordinary
reads until twenty-four hours. Between those ages, repeating preflight cannot
help. This is a timing prerequisite, not an unexplained clock jump or permission
failure. Preserve both observations and the failed job.

The four exact objects are the suspension file and the city, city/.beads and
runtime/provisioning directories. `refresh.py` binds their device, inode, owner,
mode, link count, size, modification time and change time. It also binds the
suspension content digest. No provider, service, Bead, configuration, cache
content or worker workspace is modified.

## Fixed execution contract

- Run only through the existing host job runner, from one clean signed candidate
  with two independent exact-candidate SOURCE_PASS review envelopes.
- The fixed interval is 2026-09-28 14:26–16:26 CEST. Before then, do not queue or
  execute the job. All four twenty-four-hour read thresholds have elapsed by the
  opening bound, with a margin. Check actual state again; the date is not proof.
- Bind the current boot. Observe all four objects first with O_NOATIME. Refuse
  any unexpected non-access metadata or content change before ordinary reads.
- Natural access-time advances must be forward, not future, and compatible with
  the existing relatime rule. Already-young objects are not refreshed again.
- Refuse symlinks in any path component, special files, multiply-linked regular
  files, oversized content, non-relatime/read-only mounts and raced replacement.
- Write intent and observations only to the fresh, create-only root
  `/var/tmp/ga-e0t1.20-read-refresh-20260928-r1`. Never replay a consumed root.
- Ordinary bounded file reads/directory enumerations may let the kernel advance
  access times. No `utime`, chmod, chown, deletion, rename, clock change, privilege,
  service transition or timestamp restoration is performed.
- Clock accounting reuses the byte-identical reviewed S2 cache-atime policy
  SHA-256 `61c3e38e4475061c658a853036922742ab2ce69d44a4577e3f91490674047783`.
  It retains its one-second coarse-filesystem sampling allowance, ordered
  boot-clock samples and 100 ms offset-disagreement refusal. Refresh itself is
  additionally limited to sixty seconds. Reading the root-owned procfs boot ID
  requires no O_NOATIME privilege and does not read a protected timestamp object.
- Each ordinary read retains its before/after image and clock envelope. A final
  comparison proves exact non-access metadata, content and directory-name parity
  and the unchanged nineteen-hour predicate on every object.
- PASS explicitly says `full_host_admission=false` and `worker_release=false`.

## Execution order and failure disposition

Before starting, read the existing preflight-r2 result and verify the runner is
idle, the queue is empty, the failed window root is still absent and no worker
has started. Preserve the exact HALTED record using the existing runner protocol.
Do not replay completed S1, BIND, OBSERVE roots or the failed preflight job.

Run READ-REFRESH once after 14:26 CEST. Inspect its full result and log. If it
passes, run the fresh S2 OBSERVE r4 and then full PREFLIGHT r3 using the same
reviewed candidate. A read refresh alone is never sufficient for staging,
routing or resuming. Existing startup, containment, restoration, inspection and
independent product-review gates still apply. The original later C1 cache
disposition remains separately operator-bound.

Any failure preserves the evidence root and reads already performed. Do not
restore access times, replay the job, normalize drift or proceed to staging.
Determine whether any ordinary read occurred from the per-object records and
job log. A corrected successor requires understood disposition and fresh review;
ambiguous change stops under the standing grant.

## Focused evidence

Disposable fixture tests cover genuine ordinary file/directory reads; exact
non-access metadata and digest preservation; early, repeated and 19–24 hour
refusals; naturally refreshed no-ops; links and special files; read failure with
preserved intent; clock disagreement; boot mismatch; and midflight drift. The
young predicate is compared against the unchanged actual S2 function.

The first fixture run exposed coarse-time sampling precision; the second exposed
an unprivileged O_NOATIME request against procfs. Both failed runs and fixtures are
preserved. Reusing the existing clock policy and making the procfs observation
ordinary resolved these draft defects. R5 has thirty-one passing tests, no failures
or skips. These are fixture proofs, not live acceptance.
