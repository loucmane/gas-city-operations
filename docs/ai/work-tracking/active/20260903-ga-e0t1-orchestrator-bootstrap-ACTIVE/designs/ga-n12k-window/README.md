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
- It continues ga-qcwl. The lineage is recorded in its description and notes. The discovered-from edge was removed
  in s2 (see Phases).
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
- the receipt staging;
- the integrity binding;
- base `b6843d3f`;
- the 21-path allowed set.

The accepted image did change, which s1 claimed wrongly; s2 r2 corrects it. S4's STAGE and RESTORE replaced
city.toml and the receipt by atomic rename, giving them new inodes and times with the same content, and its
lifecycle rewrote the suspension state. The live pins therefore no longer match the P7 snapshot. S4's TERMINAL
admitted against its own restoration record, not against P7.

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

1. **s1 (`ac340176`).** Two SOURCE_PASS reviews that named only `operator/PREP.sh`, then the PREP job.
   - Job `ga-n12k-s1-prep` ran and passed at 23:13 CEST (21:13 UTC).
   - Result `d6cbdf3e`:
     - overlay `25026cfd`;
     - receipt `7cf59ab9` changed to `58973d2e`, touching only `permission_revision` and `receipt_sha256`;
     - revision `5ca6886c`;
     - orders `b57082cf`, unchanged;
     - the worker was not launched.
2. **s2 r2 (this commit).** Both reviews of s2 `0612b2fc` held: OBSERVE would refuse with "accepted baseline drift",
   and BIND, which runs first, would already have spent the Bead. Both HOLDs are filed.
   - The accepted image is now the S4 window's TERMINAL `observed-after.json` (`a7cdb0f8`), taken by the same
     `snapshot()` right after RESTORE. Only its cache, host, pins and protected keys are compared. Its city.toml and
     receipt pins carry the window baseline digests `4f7e170f` and `7cf59ab9`.
   - The provider pins stay the P7 ones, now read from an explicit `PROVIDER` path.
   - The result key is renamed `admitted_against_previous_terminal`.
   - A read-only check at 23:35 CEST, run in the supervisor namespaces through `systemd-run --user`, passed:
     - the live image equals the TERMINAL record, with atime dropped;
     - the provider pins are equal;
     - `pins()` passes;
     - the start gate passes. The three city directories had been refreshed with one listing each, because
       S4's RESTORE had moved their mtime and ctime.
   - Any later successor admits against its predecessor's TERMINAL record in the same way.
   - Brief changes:
     - no `bd show ga-qcwl`, since its output names the old worktree;
     - the gate RED is a compile failure, and is recorded as one;
     - write progress and a checkpoint as soon as the edits are re-applied, before the long suites.
   - The old ga-qcwl worktree remains a residual risk. The policy lets native Write create files anywhere under
     the core worktrees, so the only safeguards are mode 0444 on its seven files, the brief, and the coordinator's
     digest comparison after TERMINAL.
   - Tests: 13.

   Earlier s2 `0612b2fc`, whose content is kept:
   - `PREP_PINS` re-pins window-base to those outputs. The nudge-order pins stay, because the order list is
     byte-identical.
   - Brief fixes from the s1 reviews:
     - The worker first checks the patch digest.
     - Before any edit, it classifies the two metadata failures at the base, using exact `-run` subtest patterns.
     - It re-applies every hunk except the dispatch-gate ones.
     - It writes the gate RED against the unchanged gate code, then applies the gate hunk.
     - The "base copy" option is gone, so no copy of any source file is made.
     - `bd` reads use the absolute path.
     - A fix that would need a file outside the allowed set ends at a checkpoint.
   - Setup outside the package, done after the s1 reviews:
     - The discovered-from edge from ga-n12k to ga-qcwl was removed, because BIND requires a task with no
       dependencies (`bind-task-r3.py:50`). The lineage stays in the Bead description and notes.
     - ga-qcwl was confirmed to have no assignee and no `gc.routed_to` or `gc.run_target`, so the queue audit accepts
       it.
     - The seven edited files in the old ga-qcwl worktree were set to mode 0444, so a native Edit there fails.
     - Before the window, its diff digest is `01f8b8af` and its status digest is `2d733147`. The coordinator
       compares both after TERMINAL.
   - Tests: 12 at 0612b2fc.
   - The two reviews name the 33 window wrappers.
3. **Window.** As in S4:
   - BIND, the lstat start gate and the `~/.claude.json` snapshot;
   - OBSERVE, PREFLIGHT, STAGE, ROUTE, WATCH-1, then RESUME;
   - WATCH, then the source and signing releases with their in-window reviews;
   - CONTAIN, CLOSE, ADMIT, RESTORE and TERMINAL;
   - record the outcome on ga-n12k and ga-qcwl.

The window has no KICK. If the worker never claims, that is a stop.
