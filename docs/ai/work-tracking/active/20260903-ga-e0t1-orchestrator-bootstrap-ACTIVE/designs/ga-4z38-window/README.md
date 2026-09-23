# ga-4z38 worker window (goal step 3)

ga-4z38 is the third successor for the ga-5ot6 routing work. Its predecessors' attempts are consumed and
never refunded:
- ga-5ot6 died at the trust dialog;
- ga-e0t1.14 exposed the native-write policy gap, later fixed;
- ga-y49e was rejected by the positional prompt, since fixed and live via M5.

This package delivers one reviewed window. It routes `gascity/gc.implementation-worker` (Claude
signing worker, Opus 5.5) through `gc sling` onto ga-4z38. The rest follows ga-y49e's reviewed
contract:
- one claim;
- startup capability proofs, including the negative permission cases;
- RED/GREEN implementation of the route-cycle separation;
- the implementation summary artifact;
- one managed signature after independent candidate review;
- delivery, closeout, exact restoration, and zero residue.

Every live step runs as a job of the persistent host job runner (`designs/gct-jobrunner`).

## Round 1: prep

`prep-r11.py` is a merged rebind of the reviewed ga-y49e `prepare-isolation.py` and
`prepare-receipt.py`. Their logic is kept, and the overlay generator is factored out as
`build_overlay()`. It is read-only and writes only its fresh root (`-r1` for this round's job; now
`-r2`, see below).

It produces the single-worker isolation overlay of the live M5 city (`4f7e170f`):
- workspace cap 1;
- all 34 orders skipped;
- all 40 city and gascity agents suspended, except `gascity/implementation-worker`, which is bound to
  the ga-4z38 worktree with sessions 0..1.

It proves the exact effective-config delta and zero effective orders. It takes the overlay's
permission revision from the reviewed Core compose diagnostic (`9f837c83`). It normalizes (Template
provisioner `64425a72`) and finalizes (Core preflight diagnostic `edbc0fa1`) P6's reviewed input draft
(`24c1ca75`) with that revision. The final receipt must differ from the live receipt `0b30c23f` only
in `permission_revision` and `receipt_sha256`.

**Rebind map from the reviewed originals:**
- city `6594ee77` becomes `4f7e170f`;
- revision `ebeefe97` becomes `d6ca85cd`;
- receipt `01ed1bce` becomes `0b30c23f`;
- the prior input (the R9 draft) becomes P6's draft;
- the task and worktree ga-y49e become ga-4z38;
- the old observation root becomes a live observation made in the same run;
- the two output roots become one fresh root.

The overlay was derived twice by the coordinator, from a text transform of the reviewed ga-y49e
overlay and from this generator over live config. Both gave `5f3b60e1`, and a test pins that. The
M5 city equals the old R9 baseline except for its Opus 5 to 5.5 model lines.

**Job.** Job `ga-4z38-prep` runs `operator/PREP.sh` at this commit. It writes its log to
`~/.local/share/gas-city-staging/ga-4z38-window/prep-*.txt` and exits with the prep result.

### Round 1 r2 (after the r1 job refused)

Job `ga-4z38-prep` at `7ae90892` (two SOURCE_PASS reviews) ran at 16:06Z and refused fail-closed at
the effective-config assertion. The only difference was one additional advisory entry in
`gc config show` `validation.warnings`: the bound worker's `max_active_sessions=1` makes it a
canonical singleton. The observed list equals the sorted baseline plus exactly that string, and every
Agents, Workspace and Orders field matched. The compose checks had already passed: before
`d6ca85cd`, overlay revision different. Root `-r1` is consumed and preserved.

r2 does the following:
- it expects exactly that pinned warning, `SINGLETON_WARNING`;
- it pins the overlay `5f3b60e1` in-job, not just in the test, as both r1 reviewers suggested;
- it re-launches the normalize child through the digest-checked source launcher;
- it declares the fixed ENV and the in-run revision gate in the docstring;
- it uses root `-r2`.

A test binds the pinned warning to the r1 evidence.

### Round 1 r3 (after the r2 review HOLD)

r2 `f0234f73` got one SOURCE_PASS and one HOLD, so it never ran and root `-r2` was never created.
The HOLD named two checks that no test or job had yet reached:
- the receipt difference check, which depends on `worker_profile_sha256` excluding the revision;
- the empty-orders check, since gc might print `null` for an empty list.

`proof/prep-proof.py` now runs both offline and read-only, with the committed code and a scratch
root:
- The confined `gc order list --json` against the pinned overlay bytes returns `"orders": []` with
  count 0. `gc config show` equals both the r1 observation and `expected_config()`.
- `receipt_image()` runs the exact job child path: normalize through the source launcher
  (`-I -S -B`), then Core `compose finalize`. Each runs in bwrap with `--unshare-pid --new-session`
  under the Core owned-phase runner, and cleanup is clean.
  - With the live revision `d6ca85cd`, the result is byte-identical to the live receipt `0b30c23f`.
  - With the r1 overlay revision `6b31d83a`, only `permission_revision` and `receipt_sha256`
    differ (final `392ea0b6`).

r3 also makes these changes:
- the launcher self-check comes first in `main()`, before the root exists;
- `expected_config()` is factored out and replayed against the r1 evidence by a test;
- a test pins the r1 overlay bytes;
- the normalize child takes its input directory as an argument;
- `test_prep.py` runs the proof.

Root `-r2` is still fresh and is used as is.

## Round 2 (next commit): the window

Round 2 rebinds the reviewed ga-y49e R10 window stack onto this baseline and task:
- `window-state-r6-read-safe.py` and `window-state-r10.py`: preflight, stage, restore, lifecycle,
  confined writers, cache-atime policy, integrity binding;
- route and audit, bind, the integrity observer, and the worker brief.

It pins the round-1 outputs. Its jobs run in this order:
1. fresh baseline;
2. preflight;
3. stage;
4. bind and route;
5. resume;
6. in-window reviews, from the coordinator sandbox with `GIT_OPTIONAL_LOCKS=0`: startup, source
   release, candidate, signing release;
7. containment;
8. restore;
9. terminal integrity;
10. delivery.

## Quiet window

From the round-2 baseline until restore has started, the ga-e0t1 worktree stays clean at the
package commit. Records go to Bead notes, always with `GIT_OPTIONAL_LOCKS=0`, and to staging. A
plain gc call changes the pack-cache `.git` mtime; that was verified 2026-09-23.
