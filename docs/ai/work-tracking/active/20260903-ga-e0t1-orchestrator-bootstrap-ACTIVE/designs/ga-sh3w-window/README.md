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

### The coordinator-cache disposition (s2, operator approval requested)

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

1. **s1 (this commit).**
   - Two SOURCE_PASS reviews naming the wrappers `operator/WORKTREE.sh` and `operator/PREP.sh`.
   - Then the WORKTREE job, then the PREP job.
2. **s2.** Pin the PREP outputs (overlay, receipt image, isolated revision, result and order list) and
   `CACHE_PINNED_NS`, then two reviews naming the window wrappers. A live precondition: the process record
   is still accurate. The dolt watchdog, dolt server and gpg-agent must be the recorded processes;
   otherwise refresh the record with `preroute.py record` while the city tmux server is stopped.
3. **Window.**
   - BIND, the read-only start gates, OBSERVE, PREFLIGHT and STAGE.
   - ROUTE, with PRE-ROUTE as its first step and then the queue audit.
   - WATCH-1, then RESUME only if WATCH-1 records `routes_unchanged_since_stage` true.
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
