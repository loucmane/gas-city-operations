# ga-sh3w window: the first Operations candidate window (ga-fsfg R3, ninth successor)

This window routes **ga-sh3w** (ga-fsfg R3, the `delivery` command class) to
`gascity/operations-candidate-worker`. That worker runs on the `claude-candidate` provider, which never signs.
It is the first run of the Operations candidate lane, and it follows the accepted plan ga-cw-first-window
PLAN r12 (`2067a406`).

## Prerequisites

Every prerequisite is live and recorded on ga-e0t1:

| Step | Live value |
| --- | --- |
| ACTIVATE (ga-6utp r12) | `agents/operations-candidate-worker/agent.toml` `ba01f223`, with `suspended = true` and `max_active_sessions = 1`; the provider is `claude-candidate`, and the candidate root is empty |
| M9 | the platform manifest file `5a29dc59` pins the candidate wrapper `e4442971` and its launch inputs; inspector `9e29e45d` shows zero drift |
| RECEIPT (P10) | worker receipt `c833908f` (revision `83c41af6`): the signing profile `ad0c695b` plus the typed candidate profile `e641dc17` |
| VAULT-INVENTORY | clean: no hard links and no mirrors (`ae607077`) |

The Bead: ga-sh3w is in the `gascity` rig store. It is open and unassigned, has no metadata, and has one
`related` edge to ga-fsfg, so readiness does not block it. Its description is byte-for-byte the reviewed
R3 brief (`5cbf64f1`).

## Derivation (s1)

`generators/make_successor.py` derives the package from the reviewed ga-qcwl s2 blobs (`20e9ba1e`).
`test_successor.py` proves that the package equals its output. The generator docstring has the full list.
In short:

- **Dropped:**
  - the source and signing releases (`release-r11.py`, `SOURCE-RELEASE-*`, `SIGNING-RELEASE-*`);
  - the ga-qcwl brief and bind step.

  A candidate delivers uncommitted work. INTAKE takes the place of the releases, after TERMINAL.
- **Identity:**
  - the target is `gascity/operations-candidate-worker` and the provider is `claude-candidate`;
  - the worktree is `/home/loucmane/gas-city-ops-candidate-worktrees/ga-sh3w`, on branch
    `codex/ga-sh3w-delivery-class`, at Operations main `040139d8`;
  - the audit's assignee aliases are Core's session forms for that target: the basename has no dot, so
    they are `gascity/operations-candidate-worker` and `operations-candidate-worker`, each optionally with
    a `-` suffix.
- **Host epoch after sequence 15:**
  - supervisor and controller 995924, start 163987392096;
  - broker 2940285 and signer 2310, unchanged;
  - gc `fce2e9a0` (Core `deefb98b`).
- **Accepted image:** the P10 adoption `after.json` (`aaeb7d8f`) and its provider pins (`82a4a70c`),
  admitted through exactly one disposition, `approved_candidate_cache_image` (below).
- **Receipt staging:** the P10 witness `53dd4553`, the input draft `c6674ba5`, the receipt `c833908f` and
  the revision `83c41af6`.
- **PREP (r8):** the overlay unsuspends only the candidate agent and binds it to the worktree.
  - Every other city and gascity agent stays suspended, and the workspace cap is 1.
  - Only nudge-on-route stays, with the 45m/2h env.
  - The agent keeps `suspended = true` in its M9-pinned `agent.toml`; a `city.toml` patch overrides it
    for the window only.
  - PREP uses the P10 candidate composition diagnostic (`53450168`) and the P10 N-profile preflight's
    finalize (`c6dd9ebb`).
  - The candidate's own `max_active_sessions = 1` already produces the singleton warning, so the expected
    configuration adds none.
  - The overlay is `8b039657`: 43 agent patches, 33 skipped orders.
  - A read-only dry run on 2026-09-26 (scratchpad `sh3w_prep_dry.py`) found:
    - the effective config under the overlay equals `expected_config` exactly;
    - the candidate composition is unchanged apart from the revision (`83c41af6` to `e0ed64ff`);
    - exactly nudge-on-route remains.
- **Integrity:** the observers use the M9 inspector (`9e29e45d`, record `87e12b94`, entrypoint
  `1fa212ce`), with the manifest pin `5a29dc59`.
- **Candidate git.** Every coordinator read of the candidate worktree uses the hardened form of
  gct-lagl HANDOFF 4.2:
  - `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null`;
  - an explicit admin `--git-dir` and `--work-tree`;
  - hooks and fsmonitor off;
  - `--no-textconv --no-ext-diff` on every diff.

  This applies to PREFLIGHT's base and clean checks and to every WATCH read. A candidate `.gitattributes`
  therefore cannot select the operator's git-lfs filter or any other driver.

### The new steps

- **WORKTREE (`worktree-task-r1.py`)** runs from the canonical repository with no system or global config
  and with hooks and fsmonitor off. Its preconditions:
  - the candidate root is empty and owned by the operator;
  - main is exactly `BASE`;
  - neither the branch nor the admin directory exists.

  It then runs `git worktree add -b codex/ga-sh3w-delivery-class <worktree> BASE`, and requires:
  - the root holds only the worktree;
  - the reviewed `candidate_git.verify_linked` accepts the gitfile, back-pointer and commondir;
  - HEAD is `BASE`;
  - no driver or gitlink applies;
  - the status, ignored files included, is empty.

  It runs before PREP, so that the overlay's `work_dir` already exists when PREP validates it.
- **BIND (`bind-task-r4.py`)** sets exactly two metadata keys:
  - `gc.work_dir`: the worktree;
  - `gc.check_path`: the check the P10 candidate profile pins. Core's start preflight requires this stamp
    on the driving Bead. Core executes this path only in formula (ralph) steps, and ROUTE uses
    `--no-formula`, so no artifact metadata is needed.

  Nothing is appended to the notes, because the description already is the brief. BIND writes no
  `opt_*` key and no template override, since either would change the launch argv the receipt pins
  (P10 review B, window requirement (a)).
- **PRE-ROUTE.** The ROUTE job runs the reviewed `preroute.check` (ga-6utp r12) immediately before the
  sling, with:
  - the `gascity` store's `bd show` of ga-sh3w;
  - the activation's city process record (controller 995924);
  - `BASE`;
  - the description digest `5cbf64f1`.

  It checks that:
  - the city is quiet;
  - the root holds exactly the worktree;
  - the worktree is linked, clean at `BASE` and without drivers;
  - no process holds the root;
  - `gc.work_dir` is right;
  - the description is the reviewed brief.

  Deviation from the plan's wording, recorded for review: plan step 6 places PRE-ROUTE "after the reload
  and the rig resume". This package keeps the reviewed qcwl order instead: STAGE (overlay reload), then
  ROUTE, then WATCH-1, then RESUME. The check therefore runs immediately before routing, with every rig
  still suspended, which is a quieter city than the plan assumed. RESUME then brings the candidate up.

### The coordinator-cache disposition (operator-approved 2026-09-26)

After the P10 snapshot, the coordinator recorded M9, P10 and the vault inventory on ga-e0t1 through the
canonical `workflow.py`. Its Bead reads run bd without `GIT_OPTIONAL_LOCKS=0`, which advances only the pack
cache repository's `.git` mtime and ctime. The P10 value is `1790411960644198389`; the live value on
2026-09-26 at 08:59:23Z was `1790413163079970630`.

`approved_candidate_cache_image` admits exactly that one entry, moving it from the P10 value to a value that
s2 pins after the last coordinator note. Until then, window-base refuses, because the pin is still None. The
same class of disposition was operator-approved for ga-f37t s4.

From the s2 pin until TERMINAL, no `workflow.py` call of any verb and no bd or gc call without
`GIT_OPTIONAL_LOCKS=0` runs. Notes wait in staging.

## Phases

1. **s1.**
   - Two SOURCE_PASS reviews naming the wrappers `operator/WORKTREE.sh` and `operator/PREP.sh`.
   - Then the WORKTREE job, then the PREP job.
2. **s2.** Pin the PREP outputs (overlay, receipt image, isolated revision, result and order list) and
   `CACHE_PINNED_NS`, then two reviews naming the window wrappers. A live precondition: the process record
   is still accurate. The dolt watchdog, dolt server and gpg-agent must be the recorded processes;
   otherwise refresh the record with `preroute.py record` while the city tmux server is stopped.
3. **Window.**
   - BIND, the read-only start gates, OBSERVE, PREFLIGHT and STAGE.
   - ROUTE, with PRE-ROUTE as its first step and then the queue audit.
   - WATCH-1, then RESUME only if WATCH-1 records `routes_unchanged_since_stage` true. The coordinator
     checks this in the WATCH-1 result before queuing RESUME; RESUME.sh itself requires only the ROUTE
     and audit results, as in ga-qcwl.
   - The WATCH captures, which must show Core's nudge, then the candidate's own claim, then its
     uncommitted work in the worktree.
   - CONTAIN and CLOSE (HOLD only for a stranded lifecycle), then ADMIT, RESTORE and TERMINAL.
4. **INTAKE (after TERMINAL, coordinator).**
   - `intake.py export`, then a review of the exported bytes by two aegis-reviewer runs, then
     `intake.py apply` into a fresh `ga-sh3w-intake` coordinator worktree.
   - The coordinator then runs the tests and pre-commit and makes the signed commit, and delivery follows
     the normal PR path.
   - `intake.py retire` runs on every outcome.
   - The outcome is recorded on ga-sh3w, ga-fsfg and ga-e0t1.

**Stops.** Stop on any of these, and preserve everything:
- any refusal;
- a silent start;
- a claim by anyone but the candidate;
- a write outside the worktree;
- a signing attempt;
- residue after CLOSE.

Operating rules carried from ga-qcwl:
- no `workflow.py` from the s2 pin to TERMINAL;
- `gc` only with the env prefix;
- no coordinator Bead write, `gc` call or directory walk from PREFLIGHT to TERMINAL, apart from the reviewed
  jobs and read-only checks.

## Review history

- **s1 `604f9502`.** Review A gave SOURCE_PASS. Review B held on must_fix 1: the `%s`-formatted audit root
  kept the old qcwl date (`-20260923-r1`), while ROUTE and RESUME look for `-20260926-r1`, so every RESUME
  after a successful ROUTE would have refused. Both transcripts are filed under `604f9502`.
- **s1 r2** answers both reviews:
  - B must_fix 1: the root date rewrite matches `%s` roots, and `test_every_output_root_has_one_date` asserts
    one date for every root and that the audit, ROUTE and RESUME agree.
  - A should_fix 1 and 8, and B should_fix 4: the hardened candidate git and the WORKTREE git now also set
    `GIT_ATTR_NOSYSTEM=1`, `HOME=/nonexistent` and `core.attributesFile=/dev/null`, as `candidate_git` does.
    The branch probe goes through the timed, hardened helper (A 2).
  - A should_fix 3: the WORKTREE docstring states the partial-failure disposition. BIND refuses without the
    exact result; recovery (worktree remove, branch delete, new commit and root) is a recorded coordinator
    decision.
  - B should_fix 2: the audit aliases add Core's no-session-bead fallback `gascity--operations-candidate-worker`
    and the `s-` id prefix.
  - A should_fix 6: the PREP wrapper's history label is r8.
  - A should_fix 5: the P10 preflight directory's `phase_runner.py` is `eddf5e11`, checked live.
- **Carried to s2:**
  - the window PREP pins are qcwl placeholders until s2 re-pins them, and they fail closed (B 1);
  - the audit covers the gascity rig and city stores, while a candidate-routed Bead in another rig would only
    cost the attempt (B 3);
  - check the worker-start trust key for the linked worktree, which is keyed by the main repository path
    (B 5);
  - have TERMINAL or INTAKE prove that the shared common directory's config, hooks, `info/attributes` and
    non-candidate refs are unchanged (A 7);
  - the IDENTITY and digest rewrites are global, and the leftover-token test compensates for that (A 4).

## s2 (the window binding)

**s1 jobs.** Both ran at `6009a6b3` after two SOURCE_PASS reviews:
- **WORKTREE** passed at 11:29:30 CEST (09:29:30 UTC). The candidate worktree
  `/home/loucmane/gas-city-ops-candidate-worktrees/ga-sh3w` was created at `040139d8` on
  `codex/ga-sh3w-delivery-class`. It is clean, and `verify_linked` accepts it; admin
  `/home/loucmane/gas-city-ops/.git/worktrees/ga-sh3w`.
- **PREP** passed at 11:29:43 CEST (09:29:43 UTC), read-only:
  - overlay `8b039657`;
  - window receipt `3b4e022d` (self `0bf87e7b`), differing from `c833908f` only in `permission_revision`
    and `receipt_sha256`;
  - isolated revision `e0ed64ff`;
  - result `2b1762c8`;
  - only nudge-on-route, with the order list unchanged at `b57082cf`;
  - the only unsuspended agent is the candidate.

**s2 pins.** It pins those outputs in window-base, replacing the qcwl placeholders.

It also pins `CACHE_PINNED_NS` `1790415062719606803`. That is the pack-cache `.git` time after the last
coordinator note (the s1 outcome `workflow.py` log, 2026-09-26 at 09:31:02Z). The operator approved this
disposition on 2026-09-26, and nothing has moved it since. From this pin until TERMINAL, no `workflow.py`
runs; outcomes go to `~/.local/share/gas-city-staging/ga-sh3w-window/outcomes.md` and reach the Bead after
TERMINAL.

**Live preconditions**, checked read-only on 2026-09-26 at 11:32 CEST:
- **Process record.** The r12 activation record is exact:
  - the controller cgroup holds 2852 (dolt watchdog), 2867 (dolt) and 995924, with the recorded start times;
  - the hidden-by-design pids are exactly the recorded 20162 (gpg-agent) and 2288/2294 (`init.scope`).
- **Trust.** `~/.claude.json` trusts `/home/loucmane/gas-city-ops`, which is the key for its linked
  worktrees. No project MCP server is enabled (`enabledMcpjsonServers` is empty and
  `enableAllProjectMcpServers` is unset).
- **Queue.** In the gascity rig and city stores, no open or in-progress Bead has a `ci-`/`s-` or candidate
  assignee, or is routed to the candidate.
- **Common directory.** A snapshot of the Operations common git directory's control surface (config, hooks,
  `info/`, `packed-refs`, and every ref except the candidate branch) is in staging as `common-before.json`:
  25 entries, `6c2fdb6e`, taken with scratchpad `common_snapshot.py`. INTAKE repeats it and requires
  equality (s1 review A should_fix 7).

**Tests.** 16 in total: 15 pass and 1 skips, because WORKTREE has run. They add:
- the PREP pins;
- `pins()` against the live PREP;
- the cache pin against the live value;
- the disposition changing only that entry.

**The window jobs, in order, all from this commit.** Each job needs the previous PASS.
1. BIND.
2. OBSERVE.
3. PREFLIGHT.
4. STAGE.
5. ROUTE.
6. WATCH-1.
7. RESUME, only if WATCH-1 records `routes_unchanged_since_stage` true.
8. WATCH-2 to WATCH-12, as needed.
9. CONTAIN-1/2, then CLOSE-1/2 (HOLD-1/2 only for a stranded lifecycle).
10. ADMIT.
11. RESTORE.
12. TERMINAL.

## s2 r2 (answers the s2 reviews of `e9567ebb`)

Review A gave SOURCE_PASS. Review B held on two must_fix items, and both transcripts are filed under `e9567ebb`.

- **B must_fix 1: OBSERVE would refuse.** Both observers required the pre-M9 provider list. The live M9
  manifest has four entries: claude-native, codex, the signing `claude` and the candidate `claude`. Both
  observers now require exactly that list, with the two `claude` paths and the candidate digest `e4442971`.
  Their per-provider checks of bytes, owner and mode 0755 are unchanged. Test:
  `test_observers_pin_the_m9_providers`, against the live manifest.
- **B must_fix 2: INTAKE would refuse Core skill links.**
  - The problem: when the session work dir is not the scope root, Core materializes the pack skill catalog
    into it. That means `.gc/tmp/skill-catalog-*.b64` (already ignored by `/.gc/`) plus symlinks under
    `.claude/skills/`. `intake.py export` refuses untracked symlinks.
  - The new **EXCLUDE** job (`exclude-task-r1.py`) runs before BIND. It appends exactly
    `**/.claude/skills/` to the Operations common `info/exclude`, preimage `321dffcb`, postimage `4ef8e398`.
    That file already lists the other Claude runtime paths, and `.gitignore` already ignores the Codex
    equivalent `.codex/skills/`.
  - How it writes: atomically, keeping mode and owner.
  - Its post-check: the hardened git in the candidate worktree must report the probe path as ignored by
    exactly that line. This was checked on a scratch linked worktree on 2026-09-26.
  - The effect: the links land in intake's recorded ignored listing and are never imported. BIND now also
    requires the exact EXCLUDE result.
  - The window job order is: EXCLUDE, BIND, OBSERVE, PREFLIGHT, STAGE, ROUTE, WATCH-1, RESUME, and so on.
- **The common-directory proof is a package tool** (`common-snapshot-r1.py`; s1 A 7, s2 A 3, s2 B 3).
  - Compared set: `config`, every file under `hooks/` and `info/`, and the candidate branch, which must still
    point at BASE.
  - Coordinator refs move after TERMINAL, so they are not compared.
  - The coordinator runs `before` after EXCLUDE and before BIND, and `after` at INTAKE; any change stops
    intake.
  - The scratch snapshot `6c2fdb6e` taken at s2 is superseded.
- **Worktree files written by Core, not the candidate** (s2 B 4): `.gc/tmp/skill-catalog-*.b64` and
  `.claude/skills/*`. Both are ignored, WATCH records them, and they are not a stop.
- **Skill instructions** (s2 B 5): the materialized core skills (gc-dispatch, gc-mail and others) are
  instructions only. The candidate control policy still allows only `gc hook --claim`,
  `gc runtime drain-ack` and `bd show/update/close` unsandboxed, so no skill grants a capability.
- **CLOSE** (s2 B should_fix 1): its docstring describes the signing lane. For the candidate, the worker
  closes ga-sh3w itself when it hands off (see the candidate prompt). The CLOSE code handles both states.
- **Wording:** the approved disposition label; the RESUME gate, which the coordinator checks in WATCH-1;
  the generator names in docstrings are unchanged (s2 A 4).
