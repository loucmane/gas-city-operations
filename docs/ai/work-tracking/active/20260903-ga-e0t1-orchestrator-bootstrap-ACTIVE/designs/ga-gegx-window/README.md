# ga-gegx worker window (goal step 3, fifth successor)

ga-gegx is the fifth successor for the ga-5ot6 routing work. It was created on 2026-09-25 after the ga-f37t
window.

## What happened to ga-f37t

The ga-f37t window (package `designs/ga-f37t-window`, s6 r5 `01d74775`, two SOURCE_PASS) ran on 2026-09-25
through RECOVER, OBSERVE, PREFLIGHT, STAGE, ROUTE and WATCH-1, and RESUME passed at 09:42:36Z. The worker
session `ci-yauk5` started in the right worktree, with the signing wrapper and Opus 5.5.

**Silent start.** WATCH-2 to WATCH-7 captured the session idle at an empty Claude prompt, with ga-f37t never
claimed. Core closed the session as `stale-session`, and the attempt is consumed.

**Wind-down.**
- CONTAIN-1 suspended the city, but refused on a partial `gc status` observation, which stranded the
  lifecycle.
- HOLD-1 confirmed the city and the gascity rig suspended.
- CLOSE-1 left no session, tmux server or worktree process.
- The window stopped before ADMIT.

**Recovery.** The reviewed ga-f37t RECOVER-2 (s7 `e382bc15`) returned the city to its accepted image at
10:02:18Z: city.toml `4f7e170f`, receipt `0b30c23f`, controller at `d6ca85cd`, still fully suspended. Its
record is `/var/tmp/ga-f37t-recover-20260925-r2/result.json`.

**Root cause, confirmed in the Core source.** `internal/bootstrap/packs/core/orders/nudge-on-route.toml`
states that `gc sling` does not nudge warm-idle workers, and that without this order a routed bead sits
unclaimed. Every window since P6 built its isolation overlay with an `[orders] skip` list holding all Core
orders, `nudge-on-route` included, so the routed task never reached the worker session. The ga-4z38 silent
start has the same cause.

A secondary finding: the worker's `claude` process received the role prompt as its positional first prompt,
but the pane showed no conversation. The nudge queue is Core's delivery path for routed work, so this package
fixes the overlay. The positional prompt is left for a Template/Core follow-up.

## Derivation (s1)

`generators/make_successor.py` derives every file from the reviewed ga-f37t s7 blobs, and
`test_successor.py` proves the package equals its output.
- **Dropped:** the ga-f37t README, tests and generator; the two recovery jobs and their wrappers (they belong
  to the ga-f37t windows); FRESHEN (unused since ga-f37t s5).
- **PREP.** `build_overlay` removes `nudge-on-route` from the order skip list, after the inventory-size check.
  The overlay pinned in `OVERLAY_SHA` (`228e5be7`) is derived from the ga-f37t PREP overlay. It differs in
  exactly three lines: the header, the skip list without `nudge-on-route`, and the work dir. Every other Core
  order stays skipped.
- **RECONCILE.**
  - It holds ga-f37t: attempt session `ci-yauk5`, state `stale-session`, and the ga-f37t worktree.
  - ga-4z38 (already blocked) is the unrelated predecessor that must stay exact.
  - ga-gegx must be pristine.
- **Admission.** `approved_recovery_image()` in `window-base-r11.py` replaces only the city.toml, receipt and
  suspension-state pin entries with the ones the ga-f37t RECOVER-2 result recorded. OBSERVE pins that result
  by digest (`RECOVER_SHA`) and sets `RECOVERY`.
  - city.toml and the receipt must keep the accepted content digest.
  - The suspension state must decode to the accepted suspension image apart from `updated_at`. The accepted
    image is the ga-f37t window's pinned `suspension-baseline.json`, whose pin equals the admitted suspension
    pin.
  - The result must be ok, with the receipt written, no worker and no read errors.
  - Every other pin, the cache, the protected trees and the host stay compared by the earlier dispositions.
- **Identity:** paths, `/var/tmp` roots (`ga-f37t-*` becomes `ga-gegx-*`), worktree, branch, staging path,
  evidence path, probe test name and Bead id. The ga-f37t history comments and the two ga-f37t evidence
  paths are kept.
- **ROUTE** binds the new bind-task digest, because BIND runs again for ga-gegx.
- **Kept from ga-f37t:** the read-time accounting and PREFLIGHT start gate (s5), the reload fix (s6), the
  twelve WATCH slots with pane capture, and the operating rules: no `workflow.py` from OBSERVE to TERMINAL,
  env-prefixed gc only, and the WATCH-1 rule before RESUME.

The worktree `/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles` (branch
`codex/ga-gegx-typed-route-cycles`) was created at Core `e6366b9e`, tree `f2c120a5`, clean.

## Phases

1. **s1 (this commit):** its two reviews name only `operator/PREP.sh`. PREP writes the ga-gegx overlay and
   receipt image to `/var/tmp/ga-gegx-prep-20260923-r2` and must match the derived overlay.
2. **s2 (after PREP):**
   - re-pin the PREP outputs in `window-base-r11.py`: overlay, receipt image, composition revision and
     result;
   - two reviews naming RECONCILE, BIND and the window wrappers.
3. **Window:**
   - RECONCILE and BIND;
   - the cache and start-gate checks;
   - OBSERVE, PREFLIGHT, STAGE and ROUTE;
   - WATCH-1 and the RESUME decision;
   - the early WATCH captures, then release, contain, close, ADMIT, RESTORE and TERMINAL.
