# ga-goo5 OBSERVE R1 — preserved pre-execution refusal

At 03:37:44 CEST on 30 September, the read-only observer refused before invoking
the platform inspector. No PREFLIGHT root, installation, route, resume, claim or
worker exists. BIND completed earlier and must never be repeated. Its result is
42eb79daae25d4da8673ad7aa15623016eed07d97626cab5bf918ca0fb69b685.

Consumed R1 package is preserved by signed commit
a5e924eb7c9a406b6b2475970d75e8a5730f818a and an exact package backup at
/tmp/ga-goo5-window-r1-preserved-20260930. All consumed evidence remains in place.
Failed job done SHA256 f84a76360aa6f6e808ba57cb1018db0a74ba7dd5d4d289a098a8a1ac41850b7d.
HALTED SHA256 adf44ab9cbfe0d53582bedfa69a03513ab0cf616933463f9a472710362821a0b.
Failed observation SHA256 3f97554b5355ffd1bb5469b8388a1c17f334ebd874844aecba2757e8c34fe625.
The root contains only intent and refused observation, before any owned subprocess.

## Diagnosis

Compared with the final frozen capture, historical dependency comparison differs
only in the equal cache Git-directory mtime and ctime:
1790730658268014507 -> 1790731796031801386.
All bytes, ownership, modes, inodes, provider configuration and service identities
match. Five forward access-time differences are excluded only by the pre-existing
historical dependency_image rule, not by a new waiver.

The new timestamp falls at 03:29:56 CEST during workflow verification.
The coordinator omitted GIT_OPTIONAL_LOCKS=0 on that invocation. Operations
workflow_common.managed_environment inherits the caller environment without
supplying this field. Core pack_include.defaultRunRepoCacheGit calls status
without --no-optional-locks; pack_include_test.go documents the temporary
index.lock causing exactly this directory-only timestamp change. This explains
the stale pin; no Core change or broadened exception is needed.

## Bounded correction under standing authority

Use GIT_OPTIONAL_LOCKS=0 for every workflow call reaching gc or bd as already
required. Finish log, ledger and workflow verification before the last capture.
Prove the corrected verification preserves the cache directory timestamps.
Capture a fresh read-only baseline afterward, then regenerate exact package
bindings, test, sign and independently review without another live-ledger call.
OBSERVE uses fresh integrity root r2. All unconsumed window roots remain r1.
Preserve completed BIND bytes and its receipt; exclude BIND from the new review
and execution list. WORKTREE and PREP are not repeated.

The new exact refusal-latch helper must be independently reviewed. It admits only
this failed job, exact two-file refusal root, inactive unit and no window/route.
No failed job is replayed; OBSERVE r2 is the safe successor. The 44-file exception
and all safety predicates remain unchanged. Product work stays with Gas City.
No live acceptance or parity is claimed.
