# gct-oak5 C1 window — design (d1)

C1 is the first segment of the gct-oak5 handover (accepted plan `designs/gct-oak5-handover/PLAN.md`, r18). It routes the
open step **gct-9s1c** to the Template Claude candidate lane `gas-city-template/gc.implementation-worker` in the new
handover worktree. This document fixes *what* the window package does before it is generated, so the reviews can
check the approach before thousands of generated lines exist.

## 1. Source and method

- **Source package:** the reviewed gct-e8ex window at `1df3d47e` (s5), the last Template window that ran live (the
  gct-mbg6 codex window, TERMINAL PASS 2026-09-27 10:03 CEST (08:03Z), zero drift). It is itself the ga-3oa7 Claude
  candidate window retargeted to the Template rig.
- **Method:** as every successor: `generators/make_successor.py` reads the source files from git at `1df3d47e`,
  applies asserted replacements only (each with an exact count), and writes the package. `test_successor.py` proves
  the package is exactly the generator output. Nothing is hand-edited.
- **Why gct-e8ex and not ga-3oa7 directly:** gct-e8ex already carries the Template-rig retarget (rig commands, Template
  drivers and `.gitattributes`, template-root pre-route pieces, Template common snapshot, no-git WATCH) and the later
  hardening (route survey retries, never-resumed CLOSE, stranded-lifecycle admission). C1 changes only the lane back
  to a Claude lane and adds the handover gates.

## 2. Identity, worktree and lane (replacements)

| Item | gct-e8ex (s5) | C1 |
| --- | --- | --- |
| Task | `gct-mbg6`, description `c66bab3c…` | `gct-9s1c`, description `8a67e132…` (split-r2 record) |
| Target | `gas-city-template/codex` | `gas-city-template/gc.implementation-worker` |
| Worktree | `gas-city-template-worktrees/gct-mbg6` | `gas-city-template-candidate-worktrees/gct-oak5` |
| Branch | `codex/gct-mbg6-template-candidate-lane` | `codex/gct-oak5-handover-proof` |
| BASE | `cfd353f3` | `3474abfa` (Template `origin/main`, the M11/M12 pin) |
| Admin | `.git/worktrees/gct-mbg6` | `.git/worktrees/gct-oak5` |
| Audit aliases | `codex`, `gas-city-template--codex`, `codex-*` sessions | `gc.implementation-worker`, `gas-city-template/gc.implementation-worker-1`, `gas-city-template--gc.implementation-worker`, `gc__implementation-worker-*` sessions |
| Output roots | `/var/tmp/gct-mbg6-*` | `/var/tmp/gct-oak5-c1-*-20260927-r1` |

- **Candidate root:** the handover candidate root holds exactly this worktree (plan rule 6). WORKTREE requires it
  empty before the add and holding exactly `gct-oak5` after (the ga-3oa7 form), and ROUTE checks the same.
- **BIND** stamps `gc.work_dir` **and** `gc.check_path` (the ga-3oa7 form): the Claude lane is in the provisioning
  receipt (P12/P13), so Core's start preflight requires the stamp. The value is the pinned pack check
  `…/954ed149…/gascity/assets/scripts/checks/build-artifact-valid.sh`. The step must have no notes, no assignee and no
  metadata before BIND. BIND stamps exactly `gc.work_dir` = the handover worktree (byte-equal to the session
  `work_dir`, plan r16).
- **No info/exclude check:** the Claude skill links in `.claude/skills` are RUNTIME entries admitted by the image tool,
  not hidden by exclude rules.

## 3. PREP overlay

- The one unsuspended agent is `gas-city-template/gc.implementation-worker` (provider `claude-template-candidate`),
  bound to the handover worktree, sessions 0..1. Every other city and Template agent is suspended, **including**
  `gas-city-template/codex`, `watch-officer` and the Template `orchestrator` (plan: attention chain).
- **Provider options.** `claude-template-candidate` (`managed/rig-permissions.toml:131-174`, base `provider:claude`,
  `options_schema_merge = "by_key"`) defines `managed_worktree_access` (`none` or the candidate-policy grant),
  `permission_mode` (only `full-auto` = `--permission-mode dontAsk`) and `effort` (only `max`); the Template agent patch
  selects model `opus-5-5`, `full-auto` and the grant. Builtin keys the patch does not redefine (for example `model`)
  still merge in. The overlay does not narrow the schema, because the launch wrapper
  (`lib/gct_claude_signing_worker.py:236-324`) accepts only the exact expected model, effort and permission pairs, the
  one control policy and the one directory grant, and refuses any other flag. An `opt_*` or `template_override*` key on
  any step, holder or the root refuses under plan rule 5, and WATCH records the launch argv of every lane process. The
  codex choice removal of gct-e8ex is dropped, since codex stays suspended in this window.
- The same order skips (every order except `nudge-on-route`), asserted in PREP (plan r9 should_fix).
- The overlay digest is derived read-only by the generated `build_overlay` from the live city.toml `bdcec254` (A2) and
  the confined `gc config`, pinned at d2 after PREP runs, as gct-e8ex s2 did.

## 4. Rebase onto the current baseline

Every binding P12, M12, A2 and P13 moved since the gct-mbg6 TERMINAL, each asserted with its count:
- city.toml `bdcec254`, receipt `7185414e`, revision `a61666b3`, the P13 input draft, the P13 provider pins;
- the M12 platform inspector (`/var/tmp/gct-oak5-platform-inspector-m12-20260927`, binary `0da1ff14`);
- the compose diagnostic: the P12 Template candidate compose (`/var/tmp/gct-oak5-p12-template-compose-diagnostic-20260927`);
- the controller epoch is unchanged (pid 2800348), so the ga-bebv process record stays;
- **accepted image:** the P13 adoption `after.json` (`/var/tmp/gct-oak5-p13-adoption-20260927`), as gct-e8ex s1 r8
  admitted against the P11 adoption after-snapshot. The one-field coordinator-cache disposition needs the
  **operator's approval for this window** at d2/s2, as every window before.

## 5. Handover additions (from the plan)

1. **WORKTREE** (the gct-mbg6 `worktree-task-r1`, retargeted):
   - umask 0022; the pre-add checks (drivers `a3cf4a1c`, no attributes file, `.gitattributes` blob `84c48ec4`, no
     include directive, no gitlink or `.gitmodules`);
   - `git worktree add -b codex/gct-oak5-handover-proof <worktree> 3474abfa`;
   - an empty, operator-owned, single-link `config.worktree` (0644) in the new admin directory (plan r14);
   - a bare GitHub clone of the Template at BASE into `~/.local/share/gas-city-staging/gct-oak5-handover/base.git`
     (no alternates, no `--reference`), for the image tool;
   - **image 0:** `image_tool.py export --runtime none`, which must pass (empty entries, deleted, ignored, runtime).
2. **Common snapshot, chained:** `common-snapshot-r1.py before` right after WORKTREE; C1's CLOSE takes `after`. The
   only admitted change is the stat-only rewrite of the admin `index` (plan rule, probe run 1 evidence).
3. **Store chain:** BIND-before snapshots every store (`bd export --all`) and must equal the chain anchor
   `anchor-r1` exactly (no coordinator writes to the chained scope since the anchor). CLOSE-after is taken once the
   session Bead is in its drain-ack end state and two identical snapshots have been taken 5 minutes apart. CLOSE
   checks the within-window allowlist (plan rule 5): the C1 row's BIND, route, claim and close fields, the one PROBE
   note and the same-value re-route, the session Bead lifecycle (key union, identity pins, drain-ack end states),
   and nothing else.
4. **ROUTE:** `gc sling gas-city-template/gc.implementation-worker gct-9s1c --no-formula --no-convoy --json`. Before
   it: the lane-eligible set is empty; the candidate root audit (rule 6); the `.gc` MCP no-op (`gc mcp list`);
   `auto_reap_closed_bead_worktrees` unset. After it: the set is exactly C1.
5. **RESUME:** the rule 6 candidate root audit again, immediately before.
6. **WATCH:**
   - records every tick: the C1 status, assignee, `gc.routed_to`, the claim keys, and the non-current steps, holders
     and root (any change is CONTAIN at once);
   - **second-route negative (C1 only):** once C1 is `in_progress` with assignee equal to its `gc.session_name` and no
     hold, WATCH issues the pinned same-value `gc sling … --no-formula --no-convoy --json` once, records the JSON,
     reads C1 right after, then writes `PROBE DONE gct-oak5 C1` with `bd update gct-9s1c --append-notes`. If the
     preconditions do not hold within the bound, it writes `PROBE SKIPPED gct-oak5 C1`;
   - **hold on close:** on the first tick that sees C1 closed, WATCH polls the session Bead every 15 s and holds the
     lane at the agent level on `state_reason=drain-ack-stop-pending`, or 4 minutes after C1's `closed_at` (plan r12,
     r13); a STOP close reason is a failed segment.
7. **CLOSE:** besides the gct-e8ex CLOSE:
   - **image 1:** `image_tool.py export --runtime claude`, then `compare --step C1 --prev image0 --next image1`;
   - the rule 6 audit; the probe target is empty; the store allowlist; the session Bead end state;
   - **H1:** the coordinator writes `image_tool.py holder --image image1 --step C1` into H1 `gct-893n`'s description
     (the first between-window ledger entry), and records the H1 digest for X's route gate.

## 6. Tool fixes carried in (image tool r2 reviews)

The package also ships image tool r3 with the reviewers' should_fix: a length-prefixed skill tree digest with modes;
`.git` hashed like any name inside skill targets; `verify` pinned to the image's settings digest; a strictly parsed
`packed-refs` fallback for the branch ref; earlier walk and byte bounds; a positive test for the empty
`.claude/.cc-writes/`; tests for every remaining refusal branch; the git-scope and limit wording; `holder` checking the
image's lanes.

## 7. Run order

1. d1 (this document), two reviews.
2. s1: the generated package, two reviews. Jobs: WORKTREE, then PREP.
3. s2: PREP pins and, with the operator's cache-disposition approval, `CACHE_PINNED_NS`; two reviews.
4. Window: BIND (with BIND-before), OBSERVE, PREFLIGHT, STAGE, ROUTE, RESUME, WATCH (probe, hold), CONTAIN/CLOSE
   (image 1, store allowlist, H1), ADMIT, RESTORE, TERMINAL.
