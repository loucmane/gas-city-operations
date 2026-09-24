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
- **Digests** propagate to a fixed point. BIND runs again for ga-f37t, so no provenance pin is kept.

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

## Phases

1. **s1 (this commit):** its two reviews name only `operator/PREP.sh`, so the job runner admits only PREP. PREP
   writes the ga-f37t overlay and receipt image to `/var/tmp/ga-f37t-prep-20260923-r2`.
2. **s2 (after PREP):** re-pin the PREP outputs in `window-base-r11.py`; add repeated worker-pane capture to the
   first minutes after RESUME, so a silent start can be diagnosed before Core reaps the session; two reviews
   naming RECONCILE, BIND and the window wrappers.
3. **Window:** RECONCILE (ga-4z38 to blocked), BIND, then FRESHEN through TERMINAL at the next FRESHEN opening
   (Friday 2026-09-25 from 22:27 CEST, per the access-time forecast).

The ga-4z38 package's README holds the full design and its review history; it applies here unchanged except
for the points above.
