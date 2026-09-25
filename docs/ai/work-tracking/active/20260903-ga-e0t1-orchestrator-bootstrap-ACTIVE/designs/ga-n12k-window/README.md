# ga-n12k worker window (ga-qcwl continuation, eighth successor, no KICK)

## Why this window exists

The ga-e0t1.15 S4 window ran on 2026-09-25 (package ga-qcwl-window, s2 `20e9ba1e`, from 22:22 to 22:59 CEST).
- It passed every job from BIND to TERMINAL, and the city was restored.
- Its worker, `ci-bfdvp`, claimed by itself with no KICK. It implemented most of ga-qcwl.
- At 20:43 UTC the worker stopped at a checkpoint, saying its context budget was exhausted. It had staged
  nothing and written no candidate.

The operator chose to continue from that checkpoint in a new Bead and a fresh worktree.

## What was set up

**Bead ga-n12k:**
- It is discovered-from ga-qcwl.
- Delivering it also closes ga-qcwl.
- ga-qcwl was unrouted (`gc.routed_to` removed). The queue audit therefore sees ga-n12k as the only routed task.

**Worktree:**
- Path `/home/loucmane/gascity-core-worktrees/ga-n12k-provider-pins-finish`, branch
  `codex/ga-n12k-provider-pins-finish`.
- It was created with `git worktree add` at `b6843d3f` (tree `c9f19d21`) and is clean.

**Checkpoint input (read-only):** `~/.local/share/gas-city-staging/ga-qcwl-window/checkpoint-20260925/`. It holds:
- `worker-unstaged.patch` (`01f8b8af`, 324 lines);
- `progress.md`;
- the RED evidence files;
- the test logs.

The old ga-qcwl worktree keeps its unstaged edits as evidence. The brief forbids the worker to touch it.

## Derivation (s1)

`generators/make_successor.py` rebinds the reviewed ga-qcwl s2 package (`20e9ba1e`) to ga-n12k.

**Unchanged from S4:**
- the host epoch;
- the accepted P7 image;
- the receipt staging;
- the integrity binding;
- base `b6843d3f`;
- the 21-path allowed set.

S4's TERMINAL verified that epoch and image at 22:59 CEST.

**Changed:**
- **Identity.** All ga-qcwl paths and names become ga-n12k. The worktree becomes `ga-n12k-provider-pins-finish`.
- **PREP r8.** The ga-qcwl PREP overlay (`449346e3`) with only the work directory and header replaced. The
  window's PREP pins stay at the ga-qcwl outputs until s2 and fail closed until then.
- **Brief.** The task section is rewritten, and it adds a rule to spend context sparingly. The task is:
  1. Re-apply the patch with native edits.
  2. Write the missing dispatch-gate RED.
  3. Classify the two platforminstall metadata failures against the base.
  4. Run the required suites, then write the checkpoint, candidate and signing.
- **History line.** It now names the ga-nibd and ga-qcwl attempts, and forbids editing the ga-qcwl worktree.

`test_successor.py` has 11 tests.

## Phases

1. **s1 (this commit).** Two SOURCE_PASS reviews that name only `operator/PREP.sh`, then the PREP job.
2. **s2.**
   - Re-pin the PREP outputs in the generator (`PREP_PINS`, plus the order list if it changed), with tests.
   - Two reviews that name the 33 window wrappers.
3. **Window.** As in S4:
   - BIND, the lstat start gate and the `~/.claude.json` snapshot;
   - OBSERVE, PREFLIGHT, STAGE, ROUTE, WATCH-1, then RESUME;
   - WATCH, then the source and signing releases with their in-window reviews;
   - CONTAIN, CLOSE, ADMIT, RESTORE and TERMINAL;
   - record the outcome on ga-n12k and ga-qcwl.

The window has no KICK. If the worker never claims, that is a stop.
