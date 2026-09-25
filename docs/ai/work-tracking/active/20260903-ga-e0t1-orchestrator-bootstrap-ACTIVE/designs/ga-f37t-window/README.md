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

## Phases

1. **s1 (`912e4d48`):** its two reviews named only `operator/PREP.sh`, so the job runner admitted only PREP. PREP
   wrote the ga-f37t overlay and receipt image to `/var/tmp/ga-f37t-prep-20260923-r2`.
2. **s2 (after PREP):** re-pin the PREP outputs in `window-base-r11.py`; add repeated worker-pane capture to the
   first minutes after RESUME, so a silent start can be diagnosed before Core reaps the session; two reviews
   naming RECONCILE, BIND and the window wrappers.
3. **Window:** RECONCILE (ga-4z38 to blocked) and BIND ran at s2 r2. FRESHEN through TERMINAL run in a FRESHEN
   opening from the access-time forecast recomputed just before FRESHEN-1 (lstat of every FRESHEN object; an
   opening is a time with no non-refreshable atime in the last 19 to 24 hours). The run record on ga-e0t1 holds
   the forecast actually used.

The ga-4z38 package's README holds the full design and its review history; it applies here unchanged except
for the points above.
