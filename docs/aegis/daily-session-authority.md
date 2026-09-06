# Daily-session authority and bounded recovery

Normal Bead continuation uses `scripts/codex-task sessions continue`. It holds the
same worktree-directory lock as logging, updates the tracked pointers/state and the
derived current-work envelope in one write-ahead transaction, and preserves prior
session content. Logging and readiness refuse contradictory active-work authority.

## Repairing an old stale envelope

For an **uninstalled source checkout only**, inspect the bounded recovery plan:

```sh
python3 scripts/codex-task sessions reconcile-current --bead ACTUAL_PRIMARY_BEAD
```

The default is read-only. It derives authority from the existing Bead-scoped branch,
plan, tracker, session pointer and session state; it permits only an older session
path in a valid recovered envelope. Identity, other envelope fields, original
fingerprint, missing history, symlink components, pending transactions and writer
ownership mismatches are refusals, not repair candidates.

After reviewing the exact current plan under the operator's existing scope:

```sh
python3 scripts/codex-task sessions reconcile-current --bead ACTUAL_PRIMARY_BEAD --expect-plan-id EXACT_REVIEWED_DIGEST
```

The plan binds the root, Bead, HEAD, branch, executor bytes and exact file/link
images (bytes, mode and ownership, rather than timestamp metadata). It is regenerated
before apply; any drift refuses. The only changed target is the derived current-work
envelope's session path and its deterministic recovery fingerprint. Original
timestamps and unrelated fields are preserved. The session transaction retains
both images and the exact plan; an immediate matching replay is a verified no-op.

This command **does not** relocate historical entries, mark a session or task
complete, write Beads, update pointers, install code, grant native permissions or
authorize a provider launch. Historical-data reconciliation requires its own
bounded before/after proof. Do not use the generic pointer-repair action to replace
correct new-day pointers with an old envelope's stale path.

## Failures and platform limits

Known failed writes restore their exact before-image and retain rollback evidence.
Unknown concurrent bytes or a pending crash journal remain HOLD; no automatic
destructive replay is provided. Do not delete the journal or envelope to force
recovery. Cooperating writers must share the directory lock. Avoid nested logger
or readiness calls while already holding the exclusive continuation lock.

The lock is POSIX-only and requires verified local-filesystem flock semantics.
The currently scoped WSL activation is on ext4 with matching uid/gid; this is not
proof for drvfs, NFS, shared-owner or symlink-directory installations. Transaction
archives remain Git-ignored evidence and must not be pruned during this workflow.

The recovery command receives no automatic Claude approval. Trusted runtime changes
still require independent review and the normal delivery/activation boundaries.
