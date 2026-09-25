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
  Every other Core order stays skipped. In s1 r2 the overlay (`228e5be7`) differed from the ga-f37t PREP
  overlay in exactly three lines: the header, the skip list and the work dir. s1 r3 adds the order override
  block described under "Nudge delivery (s1 r3)", and `OVERLAY_SHA` is now `e6e24bd7`.
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

## Nudge delivery (s1 r3)

The s1 r2 reviews (both SOURCE_PASS) asked whether `nudge-on-route` would actually reach the worker. PREP r4
ran from s1 r2 on 2026-09-25 at 10:22:56Z and passed (root `/var/tmp/ga-gegx-prep-20260923-r2`, overlay
`228e5be7`, one effective order). That root is superseded by r5 below and is kept as evidence only.

**What the ga-f37t window shows.** This is from the city event log, `city/.gc/events.jsonl`, seq 1344032 to
1344049, in local time:
- ROUTE wrote ga-f37t at 11:40:55 while the city was suspended, and no event was emitted then.
- The city resumed at 11:42:27.
- Session `ci-yauk5` was created at 11:42:44, went `active` at 11:42:47, and then emitted two `awake` updates.
- The routed task's `bead.updated` event, carrying `gc.routed_to`, came from the controller's cache
  reconcile only at 11:43:03, after RESUME and 16 seconds after the worker went active.

**Why the order would find the worker.** It lists members with `gc session list --state active --template
<routed target>`. The session template is `gascity/gc.implementation-worker`, which is the routed target,
and `awake` normalizes to `active` (Core `internal/session/manager.go` `normalizeInfoState`). Its event
trigger is cursor based, so every later `bead.updated` makes it run again (`internal/orders/triggers.go`
`checkEvent`).

**The remaining risk, and the fix.** The script only looks back `GC_NUDGE_ON_ROUTE_LOOKBACK`, 2 minutes by
default. The routed event can arrive before the worker is active. If the worker then takes longer than 2
minutes to start, no later run sees the event, and nothing nudges the worker.

PREP r5 therefore adds one order override to the overlay:
`[[orders.overrides]] name = "nudge-on-route"` with `env = {GC_NUDGE_ON_ROUTE_LOOKBACK = "45m",
GC_NUDGE_ON_ROUTE_RETENTION = "2h"}`.
- The override `env` reaches the exec child (Core `cmd/gc/order_store.go`, the `[order.env]` loop, after
  every controller key; only dispatch-time vars, which an event order has none of, come later).
- Neither key is controller-reserved (`internal/orders/env.go`).
- Retention stays above the lookback, so a nudged pair is never pruned and nudged again.
- These Core paths are unchanged between the adopted `728178bf` and the ga-gegx worktree.

PREP r5 requires three things. The effective config must show exactly that override. The isolated order
list must be the baseline `nudge-on-route` entry plus that `env`. The overlay must equal the r4 overlay
with only the override block inserted after the skip line (`test_successor.py` checks that against the r4
evidence). The new PREP root is `/var/tmp/ga-gegx-prep-20260925-r3`.

**Order side effects in the window, for s2.** Each run can create an order-tracking bead, run `gc events` and
`gc session list`, send `gc session nudge`, and rewrite
`city/.gc/runtime/packs/core/nudge-on-route-state.json`. Its lookback also sees the RECONCILE update of
ga-f37t, which still carries `gc.routed_to`, so the worker may receive a second "check for assigned work"
nudge. ga-f37t is held, so it is not ready work. s2 must admit or confine these writes in the window
checks.

The worktree `/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles` (branch
`codex/ga-gegx-typed-route-cycles`) was created at Core `e6366b9e`, tree `f2c120a5`, clean.

## Phases

1. **s1 r3:** two SOURCE_PASS reviews naming only `operator/PREP.sh`. PREP r5 passed on 2026-09-25 at
   10:38:03Z (job `ga-gegx-s1r3-prep`), root `/var/tmp/ga-gegx-prep-20260925-r3`.
2. **s2 (this commit):** see "s2" below. Its two reviews name RECONCILE, BIND and the window wrappers.
3. **Window:**
   - RECONCILE and BIND;
   - the cache and start-gate checks;
   - OBSERVE, PREFLIGHT, STAGE and ROUTE;
   - WATCH-1 and the RESUME decision;
   - the early WATCH captures, then release, contain, close, ADMIT, RESTORE and TERMINAL.

## s2

**PREP r5 pins.** `window-base-r11.py` now pins the PREP r5 outputs in place of the ga-f37t ones it
inherited:
- city overlay `e6e24bd7` (`CITY_SHA[1]`, equal to `city_after_sha256`);
- receipt image `9c5765b8` (`RECEIPT_SHA[1]`, equal to `receipt_after_sha256`);
- composition revision `56f39eb2` (`REVISION[1]`, equal to `revision_after`);
- `result.json` `22e16a70`.

The ga-f37t pins map to the same fields of the ga-f37t PREP result, so the mapping is unchanged. A test
checks each pin against the r5 evidence.

**The routed event, corrected.** The s1 r3 account above is right about timing, but the event's source
needs a correction. ga-f37t's last write was the controller's native attempt stamp (`updated_at`
09:42:46Z, just before the worker went active). That is the change cache reconcile reported at 11:43:03.

Writes made with bd while the city was suspended emitted no event at all:
- ROUTE of ga-f37t at 11:40:55;
- the ga-f37t window's RECONCILE of ga-4z38, on 2026-09-25 at 00:22.

The ga-4z38 window shows the same pattern: its task's only event (seq 1344024, 2026-09-24 23:12:24) came
22 seconds after RESUME.

So in this window the order sees one routed pair, `ga-gegx|gascity/gc.implementation-worker`, reported
when the controller stamps the worker's attempt. RECONCILE's update of ga-f37t is written while suspended
and so is not expected to produce a second pair. The worker's later ga-gegx updates reach the order as
the same pair, which only refreshes its dedup entry. With the quiescent-window rule (no Bead writes or gc
calls by the coordinator between PREFLIGHT and postflight-2), the order has no second pair to nudge. Its
2h retention prunes an entry only on a run that sees some pair, and that run refreshes the ga-gegx entry
first, so the pair is not nudged again.

**Why a nudge cannot approve anything.** Core's order nudge uses `wait-idle` delivery. It types its text
and presses Enter once the pane shows the `❯ ` prompt, and a queued nudge is delivered by the poller once
the session has been quiet long enough. Neither checks for a dialog (Core `cmd/gc/cmd_nudge.go`,
`internal/runtime/tmux/tmux.go` `WaitForIdle`).

The worker profile runs Claude with `--permission-mode dontAsk` (PREP r5 `receipt.final.json`). In that
mode Claude denies every tool call that is not pre-allowed and never shows a permission dialog, so there
is no approval for an Enter to answer. The only dialog left is the startup workspace trust prompt:
- the ga-f37t worker started at an empty prompt;
- the early WATCH pane captures record whether one appears.

**WATCH nudge evidence.** Each WATCH now reads two files once, read-only, through the base `read()` (with
O_NOATIME and no lock):
- the order's pack state file, `city/.gc/runtime/packs/core/nudge-on-route-state.json`;
- Core's nudge queue, `city/.gc/nudges/state.json`.

It records whether the ga-gegx pair has been nudged (`order_nudge_recorded`) and every pending or
in-flight queued nudge (`queued_nudges`) in `nudge.json` and the result. This is evidence only and refuses
nothing.

Operating rule: a WATCH after RESUME is expected to show `order_nudge_recorded` true and the worker
claiming. If it shows the pair recorded but a queued nudge still pending while the pane shows a dialog,
the coordinator treats it as a stop and contains. Before 2026-09-25 the queue file held 26 dead items and
nothing pending, and the order state file held one entry from 2026-08-20.

**What the order writes during the window, and why the window checks admit it.**
- Order-tracking beads and their cursor labels go into the city store. No window check counts ledger
  beads. The audits run before the city resumes, and orders do not dispatch while the city is suspended.
- The order's state file is rewritten by `mktemp` and rename under `.gc/runtime/packs/core`. That is below
  `.gc/runtime`, and `directory_preservation` compares `.gc` direct children by name and identity only.
  The state file is not a pinned file.
- The order reads the pack cache (`nudge-on-route.sh`, `_bd_trace.sh`). Cache access times inside the
  window are already accounted for by `cache-atime-policy-r1.py`.
- The order's children (`bash`, `jq`, `gc`) run in the controller cgroup for a few seconds per run and
  only while the city runs. CONTAIN suspends the city before CLOSE observes processes.
