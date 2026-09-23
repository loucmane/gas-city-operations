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

## Round 1 (this commit): prep

`prep-r11.py` is a merged rebind of the reviewed ga-y49e `prepare-isolation.py` and
`prepare-receipt.py`. Their logic is kept, and the overlay generator is factored out as
`build_overlay()`. It is read-only and writes only `/var/tmp/ga-4z38-prep-20260923-r1`.

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
