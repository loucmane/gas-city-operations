# ga-nibd worker window (goal step 3, sixth successor)

ga-nibd is the sixth successor for the ga-5ot6 routing work. It was created on 2026-09-25, after the ga-gegx
window (package `designs/ga-gegx-window`). Its Core worktree is
`/home/loucmane/gascity-core-worktrees/ga-nibd-typed-route-cycles` (branch `codex/ga-nibd-typed-route-cycles`),
at Core `e6366b9e`, tree `f2c120a5`, clean.

## What happened to ga-gegx

The ga-gegx window (s2 r9 `cb949793`) ran on 2026-09-25 in the order OBSERVE, PREFLIGHT, STAGE, ROUTE, WATCH-1,
RESUME. Times are CEST.

- **Silent start.** Worker `ci-ki0gd` went active at 14:04:49 in the right worktree. It had dontAsk, and no
  dialog appeared. It sat at an empty prompt, and Core reaped it as `stale-session` by 14:11. The attempt is
  consumed.
- **Why nobody nudged it.** Core's `nudge-on-route` order fired five times and saw the routed `bead.updated`
  (14:05:13), but it never nudged. This was reproduced read-only:
  - `gc events` answers through the supervisor API, which wraps each payload as `.payload.bead.{id,metadata}`.
  - The live pack script (Core `c43feb6b0`) filters the flat `.payload.metadata`, so jq matches nothing, and
    the script exits 0 without a word.
  - With the nested path, the same output yields exactly `ga-gegx -> gascity/gc.implementation-worker`.
  - The same bug explains the ga-f37t silent start. It is recorded on ga-e0t1 for a Core follow-up.
- **Wind-down.**
  - CONTAIN-1 passed (the ga-gegx s2 r2 barrier fix held).
  - HOLD-1 refused by design, because the lifecycle was not stranded.
  - CLOSE-1 and ADMIT passed.
  - RESTORE wrote the accepted city.toml, and the reload answered `no_change` at `d6ca85cd`. It then refused
    its trace wait.
- **Why RESTORE refused.** Core had auto-armed detailed tracing for the worker template when the session
  started (`gc trace status`: source `auto`, trigger `start`, expiring ten minutes after the last extension).
  Every cycle counted that template as active, and `reload()` required zero on every read.
- **Recovery.** The reviewed ga-gegx RECOVER-3 (s3 `275b1fa8`) waited for a settled cycle, then restored the
  receipt at 12:27:23Z. The city is back at its accepted image: city.toml `4f7e170f`, receipt `0b30c23f`,
  controller at `d6ca85cd`, fully suspended, no worker. Its record is
  `/var/tmp/ga-gegx-recover-20260925-r3/result.json` (`b6ad8162`).
- **Dialogs.** The `~/.claude.json` comparison after the window was identical to the pre-window snapshot, so no
  startup menu was accepted.

## Derivation (s1)

`generators/make_successor.py` derives every file from the reviewed ga-gegx s3 blobs, and `test_successor.py`
proves that the package equals its output.

- **Dropped:** the ga-gegx README, tests and generator, and RECOVER-3 with its wrapper.
- **Identity:** `ga-gegx` becomes `ga-nibd` in paths, `/var/tmp` roots, worktree, branch, staging path,
  evidence path, probe test name and Bead id. History comments that describe ga-gegx events stay attributed
  to ga-gegx, and so does the RECOVER-3 root.
- **RECONCILE:**
  - it holds ga-gegx (attempt `started`, session `ci-ki0gd`, state `stale-session`, the ga-gegx worktree);
  - ga-f37t (already blocked) is the unrelated predecessor that must stay exact;
  - ga-nibd must be pristine.

  These preconditions were checked read-only on 2026-09-25, and the rig-scoped routed-ready query returned
  exactly `{ga-gegx}`.
- **Admission:** OBSERVE binds `RECOVER_ROOT`/`RECOVER_SHA` to the ga-gegx RECOVER-3 result. The
  `approved_recovery_image` logic is unchanged; only its comment describes the new history. A test replays it
  on the real RECOVER-3 record:
  - the pins are replaced;
  - the rest of the image is unchanged;
  - a wrong digest, a changed receipt or a launched worker refuses.
- **PREP (r6):** the ga-gegx prep, rebound to the ga-nibd worktree and header. The overlay is the ga-gegx r5
  overlay with exactly two lines replaced, the work dir and the header, and `OVERLAY_SHA` pins the result.
  The new PREP root is `/var/tmp/ga-nibd-prep-20260925-r1`.
- **RESTORE trace wait (`window-r11.py` `reload()`):**
  - a cycle whose only active template is the armed worker template, with no decisions or mutations, is waited
    out instead of refused;
  - any other active template still refuses;
  - acceptance still needs the accepted revision, `completed`, and zero active templates;
  - RESTORE (direction 0) waits up to 20 minutes, reading every 15 seconds. STAGE keeps its 120 seconds.

  RESTORE's budget gate rises from 25 to 45 minutes, and ADMIT's from 40 to 60, so ADMIT still leaves RESTORE its
  budget plus the earlier 15-minute margin (a test enforces the order). The same predicate also applies to
  STAGE's reload, where no worker has run yet. A test evaluates the new predicate on the ga-gegx
  RESTORE's own refused read.
- **ROUTE** binds the new bind-task digest, because BIND runs again for ga-nibd.

## KICK (new)

`kick-r1.py`, run by `operator/KICK-1.sh`, `KICK-2.sh` or `KICK-3.sh` (budget gate 100 minutes, the same as the source release), is a reviewed
job that tells the live worker to claim its routed task. It relies on neither `gc sling` nor Core's broken
order.

Preconditions, all read-only and checked before the one pane write:
- the window is live (city-resume recorded, no city-suspend intent), and the host epoch is live;
- `gc status` shows the city resumed;
- exactly one open session exists for `gascity/gc.implementation-worker`, in state `active`;
- ga-nibd is `open`, unassigned and routed to that template, that is, not yet claimed;
- the worker's visible pane shows no permission dialog or numbered menu. This check uses the release job's
  own dialog rules (`dialog_showing`), with `release-r11.py` loaded by digest;
- the same capture shows Claude's empty input prompt: a line that is only the prompt glyph (`prompt_ready`).
  So the text lands in a ready prompt, not in a TUI that is still starting. The capture is kept as the
  `pane-before-kick` phase evidence. A test checks the rule against the ga-gegx WATCH capture of an idle
  worker, and against a menu row, a typed line and a loading screen.

Action: one `gc session nudge <session id> <MESSAGE> --delivery immediate --json`. Only an outcome of
`delivered` passes. The message tells the worker to run `/home/loucmane/gascity/bin/gc hook --claim --json` as
a standalone command, then read `/home/loucmane/gascity/bin/bd show ga-nibd --json` and follow the task notes.
It contains no digit and starts with no `!`, `/` or `#`. KICK writes no Bead, route or lifecycle, and nothing
outside its fresh root `/var/tmp/ga-nibd-kick-<UTC>`.

A later slot refuses without a nudge once the task is claimed.

## Phases

1. **s1 (`1004f5b6`):** two SOURCE_PASS reviews naming only `operator/PREP.sh`. PREP r6 passed on 2026-09-25
   at 12:40:01Z (job `ga-nibd-s1-prep`). Its outputs are overlay `c38c6cb4`, receipt image `77cd8486`,
   revision `42e67fba` and result `dff7cad9`.
2. **s2 (this commit):**
   - `window-base-r11.py` pins the PREP r6 outputs; a test checks each pin against the r6 result fields;
   - KICK also requires a ready empty prompt;
   - its two reviews name the 37 window wrappers: every wrapper except PREP, including KICK-1..3.
3. **Window:**
   - RECONCILE and BIND;
   - the read-only cache lstat and start-gate checks, and a fresh `~/.claude.json` snapshot;
   - OBSERVE, PREFLIGHT, STAGE and ROUTE;
   - WATCH-1, then RESUME only if WATCH-1 records `routes_unchanged_since_stage` true;
   - WATCH-2 until a WATCH shows the worker session `active` at an empty prompt with no menu, then KICK-1 at
     once. Core reaps an unclaimed, inactive session after about five minutes, so the kick must land well
     inside that;
   - WATCH captures, which must show the claim;
   - the source and signing releases after their in-window reviews;
   - CONTAIN, CLOSE (HOLD only for a stranded lifecycle), ADMIT, RESTORE, TERMINAL;
   - after TERMINAL, the `~/.claude.json` comparison and the Bead record.

Operating rules carried from ga-gegx:
- no `workflow.py` from OBSERVE to TERMINAL;
- env-prefixed `gc` only;
- no coordinator Bead writes, `gc` calls or directory walks from PREFLIGHT to TERMINAL, apart from the
  reviewed jobs and the read-only checks the ga-gegx README names;
- the dialog analysis and the snapshot procedure of the ga-gegx README (s2 r9), unchanged.
