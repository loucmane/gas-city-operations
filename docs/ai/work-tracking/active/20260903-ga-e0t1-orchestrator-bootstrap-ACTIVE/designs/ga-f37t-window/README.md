# ga-f37t worker window (goal step 3, fourth successor)

ga-f37t is the fourth successor for the ga-5ot6 routing work. The ga-4z38 window (package
`designs/ga-4z38-window`, round 2b r14 `69cdc6b6`) reached TERMINAL cleanly on 2026-09-24, but its one-shot
attempt was consumed: session `ci-gi0lh` woke at 21:12:02Z, never claimed, and Core closed it stale at
21:17:49Z. The cause is undetermined because no pane capture existed; the main-repository trust entry was
true. The window restored exactly (TERMINAL 21:54:18Z). ga-4z38 is now open, routed, with a consumed
attempt, and is the only ready routed task.

The fresh worktree `/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles` (branch
`codex/ga-f37t-typed-route-cycles`) was created by the coordinator on 2026-09-25 at Core `e6366b9e`, tree
`f2c120a5`, clean, with common directory `/home/loucmane/gascity/city/rigs/gascity/.git`, exactly as the
ga-4z38 worktree was.

## Derivation (s1)

`generators/make_successor.py` derives every file from the reviewed r14 blobs; `test_successor.py` proves the
package equals its output.
- **RECONCILE** holds ga-4z38 instead of ga-y49e: attempt session `ci-gi0lh`, session state `stale-session`,
  work dir the ga-4z38 worktree, a new hold note. ga-y49e (already blocked) is the unrelated predecessor that
  must stay exact, and ga-f37t must be pristine.
- **Identity:** the package path, the staging path, the worktree, the branch, the `/var/tmp` roots
  (`ga-4z38-*` becomes `ga-f37t-*`) and the Bead id. The rebuilt inspector path
  `/var/tmp/ga-4z38-platform-inspector-20260924-r1` is kept.
- **Dropped:** the ga-4z38 README, its tests and generators (their provenance chains are ga-4z38-specific), and
  the inspector builder and wrapper (the inspector is built).
- **Digests** propagate to a fixed point. ROUTE's `BIND_SHA` is the one provenance pin kept (see s3 r2).

## s2: PREP outputs, pane capture, history

- **PREP ran** at s1 (`912e4d48`, two SOURCE_PASS job reviews filed) as job `ga-f37t-prep`, PASS 2026-09-24
  22:05:00Z, root `/var/tmp/ga-f37t-prep-20260923-r2`. Its overlay equals the derived `9774a569`, its
  receipt image is `0876abb8`, its composition revision `758aa29b`, and its `result.json` is `0c071f7c`.
  `window-base-r11.py` now pins those four (the unchanged pins stay: city `4f7e170f`, receipt `0b30c23f`,
  revision `d6ca85cd`, P6 input `24c1ca75`).
- **Pane capture.** WATCH now captures each live session's visible pane with the release job's exact
  read-only form (`tmux -u -L city capture-pane -p -t <session_name>`), one phase per session, exit 1
  recorded. Operating rule for this window: run WATCH slots about one minute apart for the first five
  minutes after RESUME, so a silent start leaves its screen as evidence before Core reaps the session.
- **History.** ga-4z38 events in comments stay attributed to ga-4z38; the PREP and RECONCILE wrapper headers
  are reworded; the brief lists ga-4z38 among the consumed attempts and names its compile probe
  `TestGaf37tCapabilityProbeNoTests`; `proof/` is dropped (it never runs in a job).
- `test_successor.py` checks the whole derivation, the allowed ga-4z38 mentions, the PREP pin, the PREP
  output pins against the live PREP root, and the pane capture. The overlay derivation itself is proven
  live by PREP's in-job digest check, which passed.

## s2 r2 (after both reviews of 0705cc0a held)

- **ROUTE binds the BIND that runs.** `route-task-r5.py` pinned `BIND_SHA` 591cf9b5, the ga-4z38 r12
  bind-task digest that r13 and r14 kept as a provenance pin; ROUTE would have refused the ga-f37t BIND after
  STAGE. At s2 r2 the generator mapped that digest to the then-current bind-task digest (15945269), which is
  the digest BIND ran with. s3 r2 replaces this mapping; see below.
- **Twelve WATCH slots.** WATCH-9..12 are WATCH-8 with only the slot number changed (a test proves the
  twelve differ in nothing else). Allocation: 1 zero-pane baseline after ROUTE and before RESUME; 5 early
  captures at about +1, +2, +3, +4 and +5 minutes after RESUME (the first also observes the session and its
  claim); 1 each after the startup proof, the candidate and the managed signature; 1 after CLOSE; 2 spare.
- **Pane capture** records a listed session without a string `session_name` in `pane-unnamed.json` instead of
  refusing, and its comment attributes the silent worker to ga-4z38.
- **Tests** check every wrapper pin and the script-to-script pins, not only PREP.
- **FRESHEN.** RESTORE replaced `city.toml` and the receipt at about 21:53Z on 2026-09-24, and TERMINAL read
  them. Plan the three FRESHEN slots against the forecast and each refusal's `old.json`.

## s3 (after OBSERVE refused at s2 r2)

s2 r2 (`36b4158d`) passed two job reviews. RECONCILE passed at 2026-09-24 22:22:22Z (ga-4z38 blocked) and
BIND at 22:22:48Z (ga-f37t bound, attempt requested). The FRESHEN opening was already free, so FRESHEN-1
passed at 22:23:38Z. OBSERVE then refused at 22:24:14Z with "accepted baseline drift".
- **Cause.** The ga-4z38 window's rig-suspend step (21:50:20Z) wrote a new `suspension-state.json`, and its
  RESTORE (21:53:20Z) rewrote `city.toml` and `receipt.json` with their accepted content (new inode and
  times). TERMINAL (21:54:18Z) wrote only its own record, which holds all three entries. The P6
  accepted image therefore cannot match any city that a window has restored. The refused observation equals
  the reviewed ga-4z38 TERMINAL record exactly in pins, cache, protected trees and host (atime aside); only
  those three pins differ from P6.
- **Disposition.** `approved_restore_image()` in `window-base-r11.py` takes exactly those three pin entries
  from the TERMINAL record (`/var/tmp/ga-4z38-terminal-20260923-r1/observed-after.json`, pinned
  `04ad8d3e`). `city.toml` and `receipt.json` must keep their accepted content digest, and the suspension
  state must be the one TERMINAL recorded (`a4bcfdc3`; the ga-4z38 window's reviewed rig-suspend step wrote it
  at 21:50:20Z, before RESTORE, and TERMINAL recorded it after checking the terminal lineage). Everything else is compared as before. A test
  replays the refused observation (it passes with the disposition and fails without it); others prove that
  a changed content digest, another expected suspension state, a pin missing from the prior image and a changed
  pin shape refuse, and that another inode on `city.toml` or on one other pin makes the admitted image differ
  from the live one. The tests that read `/var/tmp` evidence skip when it is absent (they run on this host).
- **Fresh root.** The refused OBSERVE created `/var/tmp/ga-f37t-integrity-20260924-r2`, so s3 uses
  `/var/tmp/ga-f37t-integrity-20260925-r3`. RECONCILE and BIND have run and are not repeated; their wrappers
  are left out of the s3 job reviews.

## s3 r2 (ROUTE keeps the BIND that ran)

- s3 changed `window-base-r11.py`, which `bind-task-r3.py` pins, so propagation would have moved ROUTE's
  `BIND_SHA` to the new bind-task digest. BIND ran once, at s2 r2 (`36b4158d`), and never runs again (its output
  root exists, so BIND.sh refuses). ROUTE's `BIND_SHA` is therefore a provenance pin to `15945269`, the
  `executor_sha256` in `/var/tmp/ga-f37t-bind-20260923-r1/binding-intent.json`, and is kept out of propagation.
  BIND.sh and `bind-task-r3.py` carry the propagated digests; the test checks ROUTE against the record, not
  against BIND.sh.

## s3 r3 (review hold on the documentation)

- Documentation only, plus tests: the corrections above, the refusal-branch tests and a direct test that both
  observers pin `window-obs-r11.py`. The corrected comment in `window-base-r11.py` changes its digest, so every
  propagated digest moves (FRESHEN, window, window-obs, OBSERVE, ROUTE and the wrappers). No FRESHEN or other
  result from an earlier commit is accepted, which is intended.

## s3 r4 (second documentation hold)

- The Cause above now credits each file to the step that wrote it (rig-suspend, RESTORE) and TERMINAL only with
  recording them; the same in the generator comment. The Phases list no longer calls s1 "this commit"; the
  generator docstring no longer calls s2 "this derivation". The `observe-integrity-r11.py` comments name all
  three dispositions (`approved_historical_image`, `approved_epoch_image`, `approved_restore_image`); that
  comment change moves the OBSERVE digests. No logic changes.
- **ga-f37t stays unwritten until ROUTE.** ROUTE requires the live Bead to equal the BIND record
  (`task-after.json`: notes, `comment_count` 0, `updated_at` 2026-09-24T22:22:41Z). No note, comment or label
  goes to ga-f37t before ROUTE; outcomes are recorded on ga-e0t1. Check `updated_at` read-only before the
  window.
- **WATCH cadence is best-effort.** Every job sets the runner latch, which the coordinator records and clears,
  and a WATCH runs up to about 15 phases. The +1..+5 minute captures after RESUME are therefore as close to one
  minute apart as the runner allows.

## s4 (after OBSERVE refused at s3 r4)

s3 r4 (`9bf8e544`) passed two job reviews. FRESHEN-1 passed at 2026-09-24 22:50:09Z; OBSERVE refused at
22:50:43Z with "accepted baseline drift".
- **Cause.** At 22:39:03Z the coordinator ran the canonical `workflow.py coordinate --action note` on ga-e0t1.
  It refused ("external source workflow refuses native control metadata", `workflow_ownership.py:72`), but its
  ownership check had first read the Bead through bd without `GIT_OPTIONAL_LOCKS=0`. That advanced only the
  pack cache repo's `.git` directory mtime and ctime, from `1790178703592685769` to `1790289546179167691`
  (22:39:06.179Z). The refused observation equals the full s3 chain in every other cache, pin, protected-tree
  and host value; the coordinator's env-prefixed gc calls at 22:37, 22:41 and 22:48Z changed nothing.
- **Disposition (operator-approved).** `approved_coordinator_cache_image()` in `window-base-r11.py`, chained
  last, requires exactly the historical value and replaces only those two fields with the recorded ones. Tests
  prove the r3 refusal is admitted by the full chain, that the s2 r2 refusal equals the chain without it (so
  nothing else changed between the two), and that any other preimage refuses.
- **Fresh root.** The refused OBSERVE consumed `/var/tmp/ga-f37t-integrity-20260925-r3`, so s4 uses
  `/var/tmp/ga-f37t-integrity-20260925-r4`.
- **Operating rule (s4 r2).** The disposition admits one exact value, so the cache must stay untouched from the s3
  r4 refusal (2026-09-24 22:50:43Z) until TERMINAL. In that span no `workflow.py` call of any verb runs (including
  the post-commit `log` and `discharge` the stationary flow prescribes), and no bd or gc call runs without
  `GIT_OPTIONAL_LOCKS=0`; outcomes are recorded only with the env-prefixed gc form. Just before FRESHEN-1 a
  read-only lstat of the cache repo `954ed149…/.git` must show `mtime_ns` and `ctime_ns` both equal to
  `1790289546179167691` (true at 2026-09-25 03:58Z); otherwise the window does not start.
- **Tests (s4 r2).** The r3 refusal is admitted by the full chain and differs without the cache, restore or epoch
  step; without the historical step the cache step refuses its preimage. Another preimage in either field refuses,
  both fields end at the recorded value, and nothing else changes. PREFLIGHT's `FRESHEN_SHA` is tested directly.

## s5 (operator chose read-time accounting over waiting for a FRESHEN opening)

The FRESHEN rule could not pass until 2026-09-26 00:23 CEST. Exact access-time comparisons made the window
depend on every compared object being refreshed beforehand, and the recorded access times left no gap. The
operator chose to account reads instead of waiting.
- **Disposition.** `account_read_times()` in `window-base-r11.py` runs in both preservation layers
  (`window-r11.py` and `window-obs-r11.py`), right after the reviewed cache access-time policy and before the
  exact comparison. It applies the same rule outside the cache. For a metadata record whose other fields are
  all equal, a changed `atime_ns` must:
  - move forward;
  - lie inside the comparison's observed clock window;
  - be a change Linux relatime can write (the old access time was not newer than mtime and ctime, or the new
    one is at least 24 hours later).

  Only the comparison copy is aligned. Both observations keep every timestamp, and the changes are recorded as
  `read_time_changes` in the accounting evidence. After the first lifecycle transition, the suspension state is
  left to the suspension lineage. Content, mtime, ctime, inode, size, mode, ownership and every other field
  are still compared exactly, and the P6 admission is unchanged (it already excluded access times).
- **PREFLIGHT** no longer requires a FRESHEN pass. FRESHEN-1..3 remain in the package but are not part of this
  run. The four-hour window bound from the cache policy (budget and bounds checks) is unchanged.
- **Tests** cover:
  - admitted forward reads, and refusal of relatime-impossible, backward or out-of-window changes;
  - no alignment when any other field changed;
  - cache and clock keys never touched;
  - the suspension rule before and after a lifecycle transition;
  - both call sites;
  - the removal of the FRESHEN gate.
- **Operating rule** from s4 r2 still applies: no `workflow.py` call and no bd or gc call without
  `GIT_OPTIONAL_LOCKS=0` until TERMINAL. The read-only cache lstat check now runs before OBSERVE, not before
  FRESHEN-1.

## s5 r2 (both reviews of 25abb9bd held on the same gap)

- **Exact access-time checks outside the accounting.** These still compare access times exactly, and
  snapshot alignment does not reach them:
  - the suspension lineage compares the PREFLIGHT baseline record (`suspension-lineage.py:101,106`) until the
    first transition, and RESTORE, its admission and TERMINAL re-verify that chain;
  - the route projection compares the city `.beads` directory mirror and each event's preimage
    (`route-chain-r1.py:58-64`);
  - `directory_preservation` compares the city root and the provisioning directory.
- **Start gate (s5 r3: before the window root).** `stable_read_times()` runs first in the PREFLIGHT action,
  before the window root is created, so a gate refusal consumes nothing. It requires the suspension state, the
  city root, city `.beads` and the provisioning directory each to sit on a relatime mount and to have an access
  time newer than their mtime and ctime and under 19 hours old (FRESHEN's margin).
  - Relatime then cannot rewrite the suspension state before its first transition, or the three directories
    before STAGE renames city.toml and the receipt and reloads the routes, within the four-hour bound.
  - At 2026-09-25 09:46 CEST all four passed and all four were on relatime mounts. They keep passing until
    **18:50 CEST** (suspension state) and 19:23 CEST (the three directories), so PREFLIGHT must run before
    18:50 CEST.
  - RESUME's lineage check is not clock-bounded itself. It must run well inside the bound; the suspension state
    stays stable until 23:50 CEST.
- **Not covered by the gate (s5 r3 correction).** The package's own record (`freshen-r11.py:24-28`) says FRESHEN
  never held these either. After STAGE's renames and the reload, the directories' modification times move past
  their access times, so relatime may rewrite those access times on a later ordinary directory listing:
  - `directory_preservation` then compares the city root and provisioning directory access times exactly;
  - `account_read_times` refuses the city `.beads` advance, because it checks relatime against the earlier
    mtime and ctime;
  - the route chain compares the parent access time exactly.

  This behaviour is unchanged from the ga-4z38 window, which passed. It fails closed, and ADMIT checks it before
  RESTORE is consumed. It does, however, spend the worker attempt if it happens after RESUME. The operator
  accepts this residual explicitly for this run; the gate's acceptance criterion is not met for these three
  objects after STAGE.
- **Also not gated: the five route files and the four rig `.beads` directories (s5 r4 correction).** The route
  chain compares their full capture exactly, file and parent metadata including access times
  (`restore-r9-routes-r3.py:82-93`, `route-chain-r1.py:62-70`), and does so before `account_read_times`:
  - From PREFLIGHT to the stage reload, a change refuses in STAGE, before RESUME, so no attempt is spent.
  - The stage reload regenerates every route file atomically (new inode), which moves each parent `.beads`
    directory's mtime past its access time. From then until ADMIT, the route cursor (`cursor==last`) compares
    them exactly. A listing of a rig `.beads` directory, or a read of a route file, that relatime turns into an
    access-time write after RESUME refuses ADMIT and spends the worker attempt.

  This is the same class as the residual above, it is unchanged from the ga-4z38 window, and it is part of the
  residual the operator is asked to accept for this run.
- **If ADMIT refuses on a residual,** RESTORE is not consumed and the city stays in the staged overlay (suspended
  or in its last lifecycle state). Returning it to the accepted image then needs a separately reviewed recovery
  successor. No automatic restore runs.
- **If RESTORE refuses after ADMIT passed** (a residual that appeared between them), RESTORE is consumed
  (`restore-consumed.json` is written first). Its restore-immediate preservation and the restore reload repeat
  the exact route and directory comparisons. A refusal after `restore-city` has replaced city.toml leaves a
  half-restored city, and a separately reviewed recovery successor must also take it from there. Both residuals
  therefore apply to "ADMIT or RESTORE".
- **Which reads matter.** "Stray" understates them. A route file regenerated by the reload probably starts with an
  access time at or below its mtime, so the first ordinary read writes its access time. That includes WATCH's
  own `gc bd show` and `gc bd list` and the worker's bd calls. The ga-4z38 window's ADMIT passed under the same
  conditions, which is empirical evidence (not proof) that those reads do not touch the route files or their
  directories.
- **Operating rule: WATCH-1 before RESUME (s5 r5).** WATCH-1 runs after STAGE and ROUTE, before RESUME, and
  records `routes_unchanged_since_stage` (`watch-r11.py:81-94`). This is close to the route check ADMIT applies,
  though ADMIT also runs `route_authority` and the city `.beads` mirror check.
  - If the value is anything but `true` (a difference list, or a `refused: ...` string from a read error), a
    route-capture residual has already happened. Do not run RESUME. Stop with the city staged and still fully
    suspended (the suspension baseline is fully suspended) and ga-f37t routed but unclaimed.
  - Do not run CONTAIN, CLOSE, ADMIT or RESTORE. CLOSE refuses on a window that never resumed
    (`close-r11.py:98-101`; HOLD needs a stranded lifecycle), and ADMIT would refuse the same route difference,
    so RESTORE could never run. Returning to the accepted image needs a separately reviewed recovery successor.
    No worker attempt is spent.
  - WATCH-1 makes its own `gc bd` reads (`watch-r11.py:204-208`) before its route check, so it can detect a
    residual it caused itself. A `true` proves the state only up to its own reads, and every later WATCH with
    gc or bd calls stays inside residual (2).
  - WATCH's `directories_pass_admission_check` does not apply the read accounting and is advisory only.
  - The rule is enforced by procedure only. RESUME.sh requires ROUTE and the route audit, not WATCH-1's value.
    Residual (1) has no check before RESUME other than that advisory directory check. The coordinator reads
    WATCH-1's record and records the decision on ga-e0t1 before queuing RESUME.
- **Runner note.** "A gate refusal consumes nothing" refers to the window root. The job runner still runs each
  (commit, wrapper) pair once, so a PREFLIGHT refusal needs a new reviewed commit, which can reuse the same
  window root.
- **Suspension alignment switch.** `account_read_times` stops aligning the suspension pin as soon as a
  `suspension-*-intent.json` exists. `lifecycle()` writes that file before the transition command runs. This is
  slightly earlier than "after the first transition", and just as safe.
- **Runtime children** are no longer walked. R6 compares them by identity only, as before s5.
- **Residual risks, unchanged from earlier packages:**
  - the directory access times after the renames and the reload, and the five route files and four rig
    `.beads` directories after the reload (both above; either can spend the attempt after RESUME);
  - OBSERVE and TERMINAL still require zero pack-cache access-time changes;
  - lists inside observations are not walked, which fails closed;
  - WATCH's ADMIT prediction (`watch-r11.py`) does not apply the read accounting, so it may predict a refusal
    where ADMIT passes. It is advisory only.
- In TERMINAL, `ROOT` is the terminal root and holds no lifecycle intents, so the suspension pin is aligned
  there. That is safe: the terminal endpoint is stable, and the lineage is verified separately.
- **Tests** add the start gate, the 24-hour boundary, the runtime-children and cache-mount exclusions, and two
  checks:
  - a changed mtime, ctime, size or mode blocks alignment;
  - a content change stays visible, because the digest sits beside the metadata record and is still compared.

## s6 (after STAGE refused at s5 r5; operator chose recovery plus fix)

s5 r5 (`817b29c6`) passed two job reviews. OBSERVE passed at 2026-09-25 08:34:35Z and PREFLIGHT at 08:35:15Z (the
start gate held). STAGE refused at 08:36:05Z with "reload acknowledgement".
- **Cause.** STAGE's `stage-city` phase replaced city.toml with the staged overlay at 08:35:56Z. The controller
  applied the change by itself, so the window's `gc reload` (08:35:56-08:36:05Z) answered outcome `no_change` at
  the expected staged revision `758aa29b` (ok, synchronous, not soft), and `window-r11.py` accepted only
  `applied`. The route files were regenerated at 08:36:04Z, inside that reload phase. The receipt was never
  applied, no lifecycle ran, ga-f37t was not routed and no worker attempt was spent. The city was left with the
  staged city.toml (`9774a569`), the accepted receipt (`0b30c23f`) and the controller at the staged revision.
- **Fix.** The window's reload now accepts `applied` or `no_change` at the expected revision. Its trace wait
  still requires the controller to report that revision completed. The route preimage and its clock are now
  captured in `transition` before the city write, not at the start of the reload, so the route event brackets a
  regeneration by the controller's own apply. `route-chain-r1.py validate_event` accepts the same two outcomes.
- **Recovery (`recover-stage-r1.py`, `operator/RECOVER.sh`, once).**
  - It checks the refused root's exact file list and pinned records, the staged city.toml, the accepted
    receipt, an unchanged suspension state (access time aside) and unchanged route content.
  - It restores city.toml with the reviewed confined atomic replace (window-base `inner city 0`), reloads
    (`applied` or `no_change` at the accepted revision `d6ca85cd`), and waits for the trace to report that
    revision completed.
  - It records the recovered city.toml pin, and makes ordinary reads of the four start-gate objects so that
    relatime refreshes whatever it may.
  - It never writes the receipt, the suspension state or a Bead, and never starts a worker. It writes no route
    itself; the controller regenerates the five route files after the city write (new inodes, new parent
    `.beads` times). The script checks their content and route authority (`capture_routes`: exact graph,
    mode, type, nlink, owner, size), not the regeneration itself. It then makes ordinary reads of the five
    route files and their `.beads` directories (s6 r4), so relatime moves their access times past the new
    modification times and they stay stable for the window. Its
    wrapper refuses if a city tmux server is running.
- **Admission.** `approved_recovery_image()` in window-base replaces only the city.toml pin entry, with the
  one the recovery recorded. That entry must keep the accepted content digest and shape. The disposition
  applies only when OBSERVE sets `RECOVERY` to the recovery root and the recovery executor digest it pins. The
  root must be the job's 0700 directory, its intent must name that executor, and its result must be ok with no
  receipt write and no worker. The recovery script pins window-base, and OBSERVE pins the recovery script, so
  the digests have no cycle.
- **Fresh roots.** The window root moves to `/var/tmp/ga-f37t-window-20260925-r2` (r1 holds the refused
  STAGE, which the recovery reads) and the integrity root to `/var/tmp/ga-f37t-integrity-20260925-r5` (r4 was
  consumed by the s5 r5 OBSERVE).
- **Run order.**
  1. The cache lstat check, then RECOVER.
  2. The start-gate forecast. The recovery's reads refresh what relatime allows. The suspension state and the
     provisioning directory stay gated by their own access times: under 19 hours until 18:50 and 19:23 CEST,
     then refreshable by a read after 23:50 CEST and 00:23 CEST. RECOVER's own reads are the only reviewed
     reads in this plan and it runs once, so either PREFLIGHT runs before 18:50 CEST on 2026-09-25, or RECOVER
     is deferred until after 00:23 CEST on 2026-09-26 so its reads refresh both. Between those times the gate
     check fails closed and nothing at this commit can pass it.
  3. Before OBSERVE (read-only, by the coordinator): RECOVER's `result.json` must show `read_errors` empty and,
     in `gate_after`, every route file and `.beads` directory with an access time newer than its mtime and
     ctime; otherwise stop, because PREFLIGHT's route mirror could refuse after creating window root r2.
     Then the cache lstat check again (RECOVER ran gc reload and trace).
  4. OBSERVE, PREFLIGHT, STAGE and ROUTE.
  5. WATCH-1 and the RESUME decision, as in s5 r2.
- The two operator-accepted residuals and the operating rules from s5 are unchanged. Route access times
  between RECOVER and the stage reload, by span (s6 r4):
  - RECOVER to OBSERVE's observed-after: nothing refuses. OBSERVE does not observe the rig route files; it sees
    the city route file only as a runtime child (identity only), and compares the city `.beads` entry under
    the read accounting.
  - OBSERVE to PREFLIGHT: PREFLIGHT's route mirror (`route-chain-r1.py:58-60`) compares the city route file
    and city `.beads` exactly, before the read accounting. A relatime write there refuses PREFLIGHT after
    it has created window root r2, so r2 is consumed but no attempt is spent. RECOVER's final ordinary
    reads make this unlikely, because they leave those access times newer than the modification times.
  - PREFLIGHT to the stage reload: STAGE refuses (`route-chain-r1.py:64,70`), before RESUME, with r2
    consumed.
  The ga-4z38 run suggests the observers' gc status and session list do not touch the route files. The
  gate comment in `window-base-r11.py` ("refuses in STAGE") is the same statement without the PREFLIGHT
  span.

## Phases

1. **s1 (`912e4d48`):** its two reviews named only `operator/PREP.sh`, so the job runner admitted only PREP. PREP
   wrote the ga-f37t overlay and receipt image to `/var/tmp/ga-f37t-prep-20260923-r2`.
2. **s2 (after PREP):** re-pin the PREP outputs in `window-base-r11.py`; add repeated worker-pane capture to the
   first minutes after RESUME, so a silent start can be diagnosed before Core reaps the session; two reviews
   naming RECONCILE, BIND and the window wrappers.
3. **Window:** RECONCILE (ga-4z38 to blocked) and BIND ran at s2 r2. Since s5 there is no FRESHEN step:
   - since s6: the cache lstat check, then RECOVER (it must pass; OBSERVE refuses the staged city without it);
   - the start-gate check (read-only), and the cache lstat check again, right before OBSERVE (RECOVER ran gc);
   - OBSERVE, PREFLIGHT (with its start gate), STAGE and ROUTE;
   - WATCH-1, then RESUME only if WATCH-1 recorded `routes_unchanged_since_stage` true (otherwise stop; see
     the WATCH-1 rule in s5 r2);
   - the early WATCH captures;
   - then the release, signing, contain, hold, close, ADMIT, RESTORE and TERMINAL steps.
   Timing follows the s6 run order: PREFLIGHT before 18:50 CEST on 2026-09-25, or RECOVER deferred past
   00:23 CEST on 2026-09-26 and PREFLIGHT within the 19-hour gate after it. (`freshen-r11.py` and the FRESHEN wrappers still
   describe the old rule; they are not part of this run.)

The ga-4z38 package's README holds the full design and its review history; it applies here unchanged except
for the points above.
