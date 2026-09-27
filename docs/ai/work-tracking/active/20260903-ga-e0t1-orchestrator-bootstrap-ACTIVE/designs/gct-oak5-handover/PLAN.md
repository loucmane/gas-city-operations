# gct-oak5 handover: C1 (Claude) → X (Template codex) → C2 (Claude) in one worktree — plan r10

This is the design for goal step 4 (gct-oak5; gct-13ku and gct-10pg are its closed prerequisites). It is reviewed before any window package is built. Every window, tool and Bead text named here is its own reviewed package later. r2 to r9 answered the r1 to r8 reviews. r9 (`54553f79`) was accepted with two SOURCE_PASS. r10 applies the inventory (`INVENTORY.md`, `inventory-data.json`) where it contradicts or completes r9; see the last section.

## Decisions this plan relies on

- **2026-09-24, handover admission (a).** One Template Bead scope, without Core's one-start attempt stamp. One worker at a time is proven as follows:
  - **Within a lane:** by the claim and `max_active_sessions = 1`.
  - **Across the two agents:** by the window gates only, namely the suspension overlay and the session and cgroup census. The per-agent cap cannot exclude a concurrent Claude and codex session, so the gates are the cross-agent proof.
- **2026-09-27, "New codex choice".** The Template codex agent gets `classified-vault-and-template-candidate-worktrees`. Its write roots are the vault and the whole candidate root, with no `.git`. A2, M12 and P13 are live.
- **2026-09-27, "Close as obsolete".** Before C1 the coordinator closes the stale August `do-work` workflow: its root `gct-wn1m` and every live member. `gct-af6u` was open, unassigned, ready and routed to the Claude lane.
  - **Scope.** The split package enumerates the members live first:
    - parent-child children;
    - every row with `gc.root_bead_id=gct-wn1m`, ephemeral and wisp steps included;
    - any convoy or molecule tracking it;
    - its dependency edges.

    The members known today are `gct-af6u`, `gct-20mc`, `gct-svpm`, `gct-dh6u` and `gct-v7yb`; `gct-zkfz` is already closed.
  - **Conditions.** All closures happen in one step, with every rig suspended and no session running.
  - **Order.** Controls are every member whose `gc.kind` is in Core's control-kind set: retry, ralph, check, retry-eval, fanout, drain, scope-check and workflow-finalize (`internal/dispatch/runtime.go:172-189`). Today that is `gct-20mc` and `gct-dh6u`. They close first, then the work steps, then the root if it is still open.
    - Closing a control does not dispatch: `ProcessControl` returns for a non-open control, and it runs only in a `gc convoy control --serve` dispatcher session (`runtime.go:154-167`, `cmd/gc/cmd_convoy_dispatch.go:138-169`).
  - **Core auto-close.** On every close, Core's controller runs molecule, wisp and convoy auto-close, even with the rigs suspended (`cmd/gc/api_state.go:575-625`, `molecule_autoclose.go`, `wisp_autoclose.go`). It may therefore close the root, attempt subtrees or convoys itself, with its own close reason.
    - The package does not fight this.
    - For each member it records who closed it: the coordinator with `gc.work_outcome=abandoned` and a close reason naming this decision, or Core's auto-close with Core's fields.
    - It verifies the end state: every enumerated member closed, and nothing new created.
  - **Audit.** The pre-route queue audit then confirms that both lanes' eligible sets are empty.
- **2026-09-27, "Keep, C1 only".** The second-route negative runs in C1's window only. There is no fallback. If it cannot run cleanly, it is recorded as unproven.
- **2026-09-27, "Adapt acceptance".**
  - The handover images cover HEAD, unstaged and untracked work, and Bead evidence.
  - Staged work is recorded as not provable, because neither lane can write `.git`.
  - After C2, the coordinator's reviewed intake signs, then the PR, CI and merge follow.
  - No provider-parity claim is made beyond this evidence.
- **Live state.**
  - The Claude lane is `gas-city-template/gc.implementation-worker`:
    - provider `claude-template-candidate`;
    - policy Edit on `candidate-root/*/**`, `.git` denied, unsandboxed `bd close|show|update`;
    - `work_dir_roots` the candidate root, cap 1;
    - receipt profile `2341a9a0`.
  - The codex lane is `gas-city-template/codex`, cap 1, with `work_dir_roots` both Template roots. Its live default choice is still `classified-vault-template-worktrees-and-git-metadata`.
  - M12 file `114b4a00`, P13 receipt `7185414e`, revision `a61666b3`.

## Beads

**Root.** `gct-oak5` stays the root and carries the acceptance. It is never routed.

**Steps.** Three step Beads, `C1`, `X` and `C2`, are created in `gas-city-template` with label `handover`.
- **Edges:**
  - each step `relates-to` the root, never parent-child, because bd 1.2.2 hides children of an open parent from `bd ready`;
  - C1 `blocks` X and X `blocks` C2, so a later step is neither ready nor claimable while its predecessor is open.
- **Holders.** Each step description is short and points to closed holder Beads, per the split pattern: every plain view stays under about 9,000 bytes.

**Image holders.** The split package pre-creates two closed, empty placeholder Beads, `H1` and `H2`, so the X and C2 step descriptions can name them by id. After a window's TERMINAL, the coordinator writes the image into the placeholder's description (H1 after C1, H2 after X). The following window's PREP pins the holder's description digest. Until it is written, each CLOSE checks that the placeholder is still empty and unchanged. A holder is never part of its own image.

**Stop contract.** Each step's acceptance is its stop point:
- the worker records its evidence note;
- it closes only its own step Bead;
- it never touches `gct-oak5`, another step or a holder.

This rests on the brief, and each CLOSE verifies it (see Windows).

**Step contracts** (declared paths are fixed in the split package):

| Step | Contract |
| --- | --- |
| C1 | Implement the first half of a small bounded Template change: a documented helper module plus its test file. It must end with exactly the declared set: one modified tracked file `M1` and one new untracked file `A1`. It runs no tests and creates no cache files. |
| X | First verify the worktree against H1's per-path digests; on mismatch, note `IMAGE MISMATCH` and stop. Do not redo C1's edits. Add exactly one modified tracked file `M2` and one new untracked file `A2`; run no tests and create no caches. Then record the note. Only after that, run the negative probes. Then close X. The vault worklog the codex prompt asks for is waived for this segment: X writes nothing in the vault. |
| C2 | Verify H2 the same way. Finish the change in `M1`, `M2`, `A1` and `A2` only. Record the per-path sha256 of `M1`, `M2`, `A1` and `A2` in a note before the test. Then run the pinned test command sandboxed and record the result. Run the negative probe. Close C2. |

**The X brief overrides the codex prompt explicitly** on four points:
- "stage and verify the reviewed tree": X does not stage;
- "escalate instead of invoking direct `git commit`": X runs exactly the listed `git commit` probe, once, as an expected refusal;
- "a permission refusal is a stop": the listed probes are expected refusals and do not stop the segment;
- close only X.

**Negative probes** run after the edits and the note. Each expected refusal is pinned exactly, and each probe's outcome is recorded on the step:
- **X, `git -C <worktree> commit --allow-empty -m probe`.** Expected: the refusal to create the index or `HEAD` lock in the canonical `.git/worktrees/gct-oak5/` with EROFS or EACCES. "Nothing to commit" does not count as a refusal.
- **X and C2, a write outside every write root of the lane.** The target is `/home/loucmane/.local/share/gas-city-staging/gct-oak5-handover/probe-target/<step>`, an empty operator directory. It is outside:
  - the vault;
  - both Template roots;
  - `/tmp`, TMPDIR and the cwd;
  - the Claude policy's Edit grant.

  Expected: X is refused by the sandbox; C2 is refused by the policy or the sandbox. The window checks that the target directory stays empty.

No step stages, commits, pushes, signs or touches git state, apart from the one expected-refusal `git commit` probe in X.

**The C2 test command** is pinned by the inventory, not chosen by the worker:
- the interpreter and virtual environment, never the canonical `.venv`, which carries a stale editable `.pth` and coverage `.pth` files;
- `PYTHONDONTWRITEBYTECODE=1`, pytest `-p no:cacheprovider`, no coverage, and no network;
- **Temporary paths.** Two distinct subdirectories under the declared `<worktree>/.oak5-c2-tmp/`, both inside the lane's existing write root, so no policy or receipt change is needed:
  - `.oak5-c2-tmp/tmp` for `TMPDIR`;
  - `.oak5-c2-tmp/basetemp` for pytest `--basetemp`, which pytest removes and recreates.

  C2 creates both before running the command, so Python's `tempfile` never falls back to `/tmp`. The inventory confirms the path is neither tracked nor ignored at BASE, and that pytest's default `norecursedirs` skips it.
- **The inventory runs the exact command,** including its env-variable form, under the live lane policy and sandbox, and proves it is permitted.
- **Cleanup.** After the test and before its note, C2 deletes `.oak5-c2-tmp/`.

**Checks on the test run.**
- CLOSE's final export (rules 2 to 4 and 6) must show that `.oak5-c2-tmp/` is gone and that `M1`, `A1`, `M2` and `A2` hold exactly the digests C2 recorded before the test.
- The test run executes code X wrote, and under this policy its sandbox can write the whole candidate root. Any file it plants or rewrites is caught by that export check, not prevented.
- The inventory proves that the tests import the worktree's code.
- The sandbox has no network allowlist. Test code runs as a child of the sandboxed command, so it stays sandboxed.
- The five excluded commands are `gc hook --claim --json`, `gc runtime drain-ack`, and `bd close`, `bd show` and `bd update`. They run unsandboxed only when the agent invokes them directly.
- Files the tests plant in the worktree could still influence those later unsandboxed `bd` calls, through cwd discovery of a `.beads/` directory or config, or a nested `CLAUDE.md` or `.claude/`. This is a stated known limit. It is detected afterwards by the final export (rules 2 to 4) and the store diff (rule 5), not prevented.
- The inventory checks the effective pytest `norecursedirs`, from the Template's pytest configuration and not just the default. It also proves that deleting `.oak5-c2-tmp/`, including read-only files pytest may leave under `basetemp`, is permitted under the live policy and sandbox.

## The worktree

One linked worktree of the canonical Template: `/home/loucmane/gas-city-template-candidate-worktrees/gct-oak5` on `codex/gct-oak5-handover-proof`, at BASE `3474abfa` (Template origin/main, the M11/M12 pinned commit).

**Created by** a reviewed WORKTREE job. It is the gct-mbg6 `worktree-task-r1` retargeted to the candidate root, with the pre-add driver, attributes and gitlink checks. The candidate root must hold exactly this worktree during the handover.

**Canonical `HEAD` stays at `3474abfa`.** Adding the worktree changes the metadata-pinned Template `.git` tree:
- dispatch is not refused, because `InspectIntegrity` does not examine metadata trees;
- **M13**, the next metadata successor, must admit that change as an exact pair.

**Lifecycle.**
- The worktree is kept, unchanged, from C1 until the intake has signed and the PR has merged.
- A reviewed retire job then archives and locks it (the ga-x7lx pattern) or removes it.
- M13 runs after that and before any other metadata successor or Template window. It admits the Template `.git` pair left by WORKTREE and retire.

## Handover images and the route gate

**The tool** is `intake_template.py export`, generalised in a reviewed package:
- **Output location.** The candidate root and the probe-target directory `…/gct-oak5-handover/probe-target` (not its parent) join `FORBIDDEN_ROOTS`. The GitHub-only bare BASE clone, every image, every scratch mirror and every export live under `~/.local/share/gas-city-staging/gct-oak5-handover/`, outside every lane write root. `outside()` checks the clone and every scratch path, not only the output directory.
- **Nested `.git`.** Any path component named `.git`, case-insensitively, below the top level refuses.
- **Ignored entries.** They are no longer summarised as a path list. Each is recorded with its type, mode, size and sha256, and links, hard links and special files among them refuse.
- **Limits.** Empty directories and group or other mode bits are not recorded. This is stated as a limit of the byte-exact claim.
- **Runtime entries** (inventory section 8). A lane session start writes a fixed, per-lane set of entries into the worktree. The tool classifies these as `RUNTIME`, separately from the contract delta. They are never delivered by the intake. Every other path under `.gc/`, `.claude/`, `.agents/` or `.codex/` that is not tracked at BASE refuses.
  - **Both lanes:**
    - `.gc/settings.json`, a regular file 0644, byte-equal to the live city `.gc/settings.json` pinned by the window;
    - `.gc/scripts/mol-dog-stale-db.sh`, a regular file 0755, byte-equal to the city `.gc/scripts/` copy pinned by the window.
  - **Claude lane:**
    - `.gc/tmp/skill-catalog-gas-city-template_gc.implementation-worker.b64`, a regular file 0600;
    - the sink `.claude/skills/`: `.gc-skill-ownership.json` (0644) and one symlink per name in it.
  - **Codex lane:**
    - `.gc/tmp/skill-catalog-gas-city-template_codex.b64` (0600);
    - the sink `.agents/skills/`: the ownership file and its links;
    - `.codex/hooks.json`, a regular file 0644, byte-equal to the bytes the X window pins.
  - **Sink rules:**
    - the ownership file is `{"targets":{name:target}}`;
    - the link names equal its keys exactly;
    - each link's target string equals its value and lies under a pinned pack-cache root (`…/cache/repos/69fe9a2e…/internal/bootstrap/packs/core/skills/` or `…/cache/repos/954ed149…/gascity/skills/`);
    - the catalog file decodes to JSON whose `Entries` have exactly those names and sources;
    - the tool records links by their lstat target string and never follows them.
  - **Pinning.** The Claude lane's exact name set, and its ownership and catalog bytes, are pinned by image 1, the first Claude write. The codex lane's are pinned by image 2. From then on they must stay byte-equal and target-equal:
    - C2's restart may rewrite them only with identical bytes;
    - X must not touch the Claude entries;
    - C2 must not touch the codex entries.
  - **Refused:**
    - any `skill-catalog-*.tmp`;
    - any `__pycache__` or `.pytest_cache`;
    - a non-empty `.claude/.cc-writes/`;
    - a change to any BASE-tracked `.claude/**` entry.
  - The `.gc/` entries are ignored at BASE. The sink files and `.codex/hooks.json` are untracked.

**Image *n*** is the export manifest (every changed, added, deleted and ignored path against BASE, with mode, blob id, sha256 and size) plus the following, read as files and not with git:
- the worktree `.git` gitfile bytes;
- the admin `HEAD`, `gitdir` and `commondir`;
- the branch ref;
- the canonical `HEAD`;
- the full state of `gct-oak5`, of all three steps and of the other holder: status, assignee, description digest, notes digest and every metadata key. The image never includes the holder it is written into. At X's ROUTE the other holder, H2, must still be empty;
- the chained common-snapshot digest (see Windows).

**The route gate** is ROUTE's pre-check for X and for C2, done by the coordinator. It refuses unless all of the following hold:
1. **Unchanged since the image, apart from an expected delta.**
   - The holder's description equals the recorded image digest.
   - The next step differs from the image only by the BIND keys (`gc.work_dir` and, for C2, `gc.check_path`), with their pinned values.
   - Everything else in the recomputed image is byte-equal to the recorded one.
2. **The delta is exactly the contract.**
   - Image 1 minus BASE is exactly {`M1` modified, `A1` added}, apart from the Claude `RUNTIME` entries.
   - Image 2 minus image 1 is exactly {`M2` modified, `A2` added}, with `M1` and `A1` unchanged, apart from the codex `RUNTIME` entries.
   - There are no deletions and no other paths. `RUNTIME` entries are checked by their own rules, not as part of the delta.
3. **No agent-control path is added, changed or deleted relative to BASE,** other than admitted runtime entries equal to their pinned bytes. BASE itself tracks `AGENTS.md`, `CLAUDE.md`, `.claude/**`, `.codex/config.toml`, `.codex/rules/*` and `tests/conftest.py`, and those must stay byte-equal to BASE. Refused paths:
   - anything under `.codex/`, `.agents/` or `.claude/`;
   - any file named `AGENTS*.md`, `CLAUDE*.md`, `.mcp.json`, `conftest.py`, `sitecustomize.py` or `*.pth`;
   - the stop names.

   `.codex/hooks.json` and `.agents/**` must be absent in image 1, because no codex session has run there yet.
4. **No ignored entries** in images 1 and 2, and in the final export, other than the `.gc/` `RUNTIME` entries admitted above. C1 and X run no tests and create no caches. C2's temporary directory `.oak5-c2-tmp/` must be deleted by C2 and absent from the final export.
5. **Bead state is as expected.**
   - `gct-oak5` and the non-current steps are unchanged.
   - The previous step was closed by its own worker. The evidence comes from WATCH:
     - the closed record keeps its assignee: a worker's own `bd close` does not clear it (inventory section 2). It must equal the claim's `gc.session_name` and match `gc.session_id`, and so must the assignee in the last WATCH tick before the close. A cleared assignee means Core's orphan release ran, and it refuses;
     - the close happened while that session was the only live worker, per the census;
     - the coordinator issued no close.

     `bd history` records no actor (committer `beads`), so no actor check is possible. That is stated as a limit.
   - **The store diff, scoped and chained.** The chained scope is:
     - the full Template rig store;
     - a projection of every other store the lanes can reach (the city store and every rig store). The projection holds every row that is routed to, assigned to, or has `gc.run_target` equal to a target or identity of either lane, and every session Bead of either lane template.

     **Snapshots.**
     - Each snapshot includes issues, ephemeral and wisp rows, dependencies, labels, comments and metadata.
     - The inventory pins the method, its completeness (wisps and events included) and its normalisation of volatile fields and ordering, and proves it deterministic on two consecutive reads.
     - **The anchor** is the chain's first snapshot. The split package's verification snapshot is the first of the settle pair, so the anchor's rows for `gct-oak5`, C1, X, C2, H1, H2, their edges and the closed `gct-wn1m` members equal the package's verified end state.
     - **A pre-package versus post-settle diff** of the chained scope must map every changed row to one of:
       - a package write;
       - a Core auto-close reaction from a named member (`wisp_autoclose.go:92-108, 165-198`; `molecule_autoclose.go:206-218`). This is controller code, not an order.

       Anything else refuses, so nothing lands in the anchor unexplained.
     - **No orders run across the chain** (inventory section 4). The city is suspended, and a suspended city dispatches no orders: none but `nudge-on-route` has run since 13:49 CEST (11:49Z) on 2026-09-12. Inside a window the overlay skips every order except `nudge-on-route`. So:
       - the city stays suspended from the anchor to C2's CLOSE-after, except inside windows;
       - each window's PREP asserts the overlay's order skip;
       - each gate checks `gc order history` for every order: no run since the anchor other than `nudge-on-route` inside a window;
       - **no maintenance write is admitted.** Any reaper, wisp-compact, orphan-sweep or other order write in the chained scope refuses.
     - **Settled** means two identical snapshots taken at least 5 minutes apart, together with that order-history check.
     - **Orphan release** (Core's reset of an `in_progress` step whose session died) is not admitted either. It fails closed.
     - Each window then takes BIND-before. It takes CLOSE-after only once:
       - CLOSE's session close is done;
       - the session Bead is in its inventory-pinned final state;
       - two identical snapshots have been taken a pinned interval apart.
     - **Comparison.** It is set equality over row ids, plus field equality. A row that enters or leaves the projection between snapshots is therefore a change, and is caught.
     - **The projection** is one fixed function. Its identity set is the union of every target and identity pinned so far: the lane names and aliases, the deterministic session names, and the census session ids once known.
       - Every snapshot also retains the raw rows of every reachable store, so the function can be re-applied.
       - At each gate the comparison uses the identity set known then.
       - At C2's CLOSE-after, every chain comparison is re-run from the raw snapshots with the final identity set.

     **Between snapshots**, the next snapshot must equal the previous one, except for coordinator writes in a between-window ledger. The ledger is exhaustive for the chained scope. Each entry pins:
     - the Bead id;
     - the pre-image: the previous snapshot's row, or "absent" for a created row, whose id comes from the create output;
     - the exact field delta.

     The Bead must otherwise equal its pre-image, so a concurrent change by anyone else is not absorbed. Several entries on one Bead within one interval compose in order: each entry's pre-image is the previous entry's post-image. The expected ledger entries are:
     - the holder writes;
     - any review-verdict note on `gct-oak5`.

     The split package itself precedes the anchor.

     Operations-store notes (`workflow.py`) are outside the chained scope.

     **Outside activity.**
     - **Inside the chained scope.** No other Template rig work runs from the anchor to C2's CLOSE-after. Any other change in the chained scope stops the handover, fail-closed.
     - **Enforcement.** The city and the Template rig stay suspended outside the windows. Every other Template agent (run-operator, codex on its default choice) stays suspended. Orders are covered by the rule above.
     - **Outside the chained scope.** Activity by others, and worker-originated writes, are admitted and stated as a limit. For example, a worker's unsandboxed `bd update` on unrelated rows in other rig stores is not detected here. When another lane later resumes, its own pre-route queue audit applies.

     **Within a window**, CLOSE-after minus BIND-before shows only the allowlist below. Every key and value is pinned; a diff cannot tell who wrote a key.
     - **The current step:**
       - BIND's `gc.work_dir` in every window, and `gc.check_path` in C1 and C2 only, with their pinned values. X's BIND stamps `gc.work_dir` only;
       - ROUTE's `gc.routed_to`, the lane identity;
       - the claim's `gc.session_id` and `gc.session_name`, and `gc.work_branch` when Core resolves a branch, whose value must be `codex/gct-oak5-handover-proof`. That is the exact claim key set (inventory section 2), and the session values must match the census;
       - status open to in_progress to closed, with the assignee set by the claim and **kept** on close;
       - the close fields `closed_at` and `updated_at`, and `close_reason` when the worker gives one. There is no `closed_by_session` in bd 1.2.2. `gc.continuation_group` and `gc.session_affinity`, the orphan-release keys, refuse;
       - appended notes by the worker;
       - the step Beads never gain `gc.work_outcome`, `gc.outcome` or other work-record keys. Neither lane prompt sets them unless a Bead asks for close metadata, and the briefs ask for none. The Claude prompt's failure keys (`gc.outcome=fail`, `gc.failure_class`) mean a failed step and refuse.
       - **Core's progress-stall attention.** The live city sets `progress_stall_timeout = "5m"` (`city.toml:363-365`). When a session holding a claim is quiet for longer than that, `markProgressStalledClaimedWorkNeedsOperator` writes to the claimed `in_progress` Bead (`cmd/gc/session_reconciler.go:2498-2513, 3990-4049`). The write is admitted on the current step only and pinned as exactly as Core allows:
         - the `needs/operator` label;
         - `gc.failure_owner=gc.session-reconciler` and `gc.failure_reason=progress_stall`, as literals;
         - `gc.failure_subject` equal to the census session Bead id;
         - `gc.progress_last_observed_at`, a timestamp;
         - `gc.progress_attention_signature`, recomputed from the values at write time (`session_reconciler.go:4016-4023`), which must match. The final closed row cannot supply them, so they come from:
           - the session id: `gc.failure_subject`;
           - the Bead id;
           - the status: the literal `in_progress`;
           - the assignee: the claim's session name from the last WATCH tick;
           - the last progress: `gc.progress_last_observed_at`, in RFC3339Nano.
         - `gc.controller_error`, matching Core's fixed template (`4029-4033`), whose embedded session name must equal the census session name.
         - A mark can be re-armed after progress resumes. Only the last values survive, so the relay may send one mail per signature.

         It is recorded as a declared result, as ga-4z38 did.
         - **Automation does act on `needs/operator`.** The city's `orchestrator-attention-relay` order fires on `bead.updated`, with a one-minute retry order. It picks up any non-closed rig Bead carrying the label, deduplicates on `gc.progress_attention_signature`, and sends durable mail to `watch-officer`. `watch-officer-mail-wake` then wakes the watch-officer, which routes to rig orchestrators; the city declares a rig-scoped on-demand `orchestrator` named session for every rig, gas-city-template included.
           - Inside a window, the reused PREP overlay suspends every city and Template agent except the routed target, so the watch-officer and the Template orchestrator cannot start. Each window's PREP asserts this for exactly those two, and the census would detect a start.
           - Between windows no step is claimed, so no mark can be written.
           - The relay's city-store mail and its runtime state file are outside the chained scope and are recorded as a limit.
           - The mark's other use, the provider-command failure path (`build_desired_state.go:3067-3081`), is refused by rule 5 if it fires.
         - Claim-holder recycling is off, because `claim_holder_stall_timeout` is unset (`config.go:1716-1718`).
         - The fixed ~60 s poll cadence makes the mark unlikely during C1's wait, but it is not relied on.
         - A worker could forge these keys or pre-write a matching signature. Nothing proven depends on them; the mark only informs the operator.
       - **`gc.last_heartbeat_at`** is a worker write, through `gc bd heartbeat` (`cmd/gc/cmd_bd.go:22-28, 206-214`), not Core attention. It is forbidden by the briefs and refused unless the inventory shows a lane prompt calling heartbeat. In that case it is admitted on the current step only, never on the root, a holder or another step, with a timestamp shape.
     - **The session Bead:** exactly one new session Bead per window for the lane template in the city store (type `session`, label `gc:session`). Its key set is not fixed per lifecycle, because optional keys depend on events. So:
       - the metadata keys must be a subset of the lane template's observed union in `inventory-data.json`;
       - the identity keys listed there are pinned by value;
       - its end state is the lane's source-window teardown state: Claude `drained` with the reconciler drain reason, codex `awake` and closed with no reason;
       - the same applies through the agent-level hold and the rig suspend and resume the windows use. The default `on_death` and `on_boot` hooks (`internal/config/workquery.go:603-662`) act on work Beads, not the session Bead. `on_death` selects in_progress rows assigned to the qualified name, not the session-name claim assignee, so it is expected to be a no-op. The inventory pins that. It also confirms that Core creates a new session Bead per start for this pool lane, not a reused slot Bead. Its name and id values, not only its key set, equal the census and the claim's `gc.session_name` and `gc.session_id`. A second session Bead, a foreign-template session, or a reused or reopened existing session Bead refuses. The same inventory pins any other city-store bookkeeping a session lifecycle and a controller poke write.
     - **The second-route negative (C1's window only):** one same-value `gc.routed_to` write on C1, with its `updated_at` and event row. The coordinator's exact `PROBE DONE` or `PROBE SKIPPED` note on C1 is the only non-worker note.
     - **The next step (at X's and C2's ROUTE):** its BIND stamps, with pinned values.
     - **The holder:** the coordinator's image write.
     - **Accompanying:** the `updated_at` and event rows of the above.

     Any other change refuses. In particular, any `opt_*` or `template_override*` key on any step, holder or the root refuses.
   - **Queue: the lane-eligible set.** This follows Core's claim scope (`cmd/gc/cmd_hook_claim.go:216-344, 1205-1225`; identities from `cmd/gc/cmd_hook.go:445-468`).

     **Stores.** The set is computed over the lane's exact hook store list: `gc hook --claim` for a rig-scoped agent queries the rig store, then the agent's work-dir store, then the city store (`cmd/gc/cmd_hook.go:412-424`, `hook_cross_store.go:89-121`), and every rig store if the agent is cross-store eligible (`hook_cross_store.go:39-47`).
     - `rigScopedHookRig` keys on `agentForQuery`, which in a session is `GC_ALIAS`, then `GC_SESSION_NAME`, then `GC_AGENT` (`hook_cross_store.go:131-145`; `cmd_hook.go:368-376`). So the inventory pins the store list per lane from a real session environment.
     - The route targets include `RoutedToIdentity`, the qualified name and `GC_TEMPLATE` (`cmd_hook.go:468, 650-652`).

     **Members.** Over those stores, the set is the union of:
     - open or in_progress rows (including ephemeral) whose `gc.routed_to` is a route target of the lane, meaning its qualified name, pool name or any alias;
     - `gc.kind=workflow` rows with an empty `gc.routed_to` whose `gc.run_target` is a route target;
     - open or in_progress non-message rows assigned to any identity candidate of the lane: the deterministic session name (`internal/agent/session_name.go:53-59`), session ids of the census, aliases and the agent name.

     Before ROUTE this set is empty. After ROUTE it is exactly the step; this is the step exception, as in `audit-queue-r3.py:61-63`. Closed rows that keep `gc.routed_to` are not in the set.

     The concrete target, alias and identity sets are pinned per lane in each window package:
     - the Claude lane, `gas-city-template/gc.implementation-worker`, and its session-name form;
     - the codex lane, as in the gct-e8ex s3 audit.

     `gct-oak5` and the holders are unrouted, unassigned or closed, so they are not in the set. `hookCandidateClaimable` requires an empty assignee and a route match.

     **Further claim-path conditions:**
     - the step Beads carry no `gc.root_bead_id` or continuation-group key, so continuation-group pre-assignment (`cmd_hook_claim.go:438-465`) does not apply;
     - the legacy control-dispatcher alias expansion (`cmd_hook_claim.go:1237-1266`) does not apply to these lanes;
     - the claim's own write is exactly the claim key set above. The empty `gc.continuation_group` and `gc.session_affinity` on gct-mbg6 came from Core's orphan release when that session closed while still holding the claim, not from the claim;
     - each lane's hook store list is {the Template rig store, the city store} (inventory section 1).
6. **The candidate root is clean.** An lstat-only audit, with no git, requires:
   - the candidate root is operator-owned, mode 0755, and holds exactly `gct-oak5`;
   - no `CLAUDE*.md` or `AGENTS*.md` in any directory above the worktree that a lane can write;
   - `verify_linked` holds on the worktree.

   This audit runs at ROUTE and again immediately before RESUME, the last point before a session starts. The remaining gap, from RESUME to the session reading its files, is stated as a known limit.

**Exactly once.** The final acceptance repeats rules 2 to 4 and 6 on the final export: `M1`, `A1`, `M2` and `A2` are each present once with the C2 content, and no step note is duplicated.

**Tamper negative, with a positive control.** On a copy outside every write root:
- the unchanged copy must verify, after normalising the manifest's `worktree` field;
- the same copy with one byte of `A1` changed must refuse.

A tool test also covers a changed ignored file, a planted `.codex/hooks.json` and a nested `.git`.

## Windows

Each segment is one reviewed window. Each is a successor package generated with asserted replacements from the last window that ran on the same lane, and rebased onto M12 and P13:

| Window | Derived from | Routes | Notes |
| --- | --- | --- | --- |
| C1 | ga-3oa7 (last Claude candidate-lane window), retargeted to the Template rig and Claude lane as the gct-e8ex window retargeted ga-3oa7 to Template codex | step `C1` | |
| C2 | C1's package, rebased | step `C2` | adds the image-2 route gate |
| X | the gct-e8ex window s3 (last Template codex window) | step `X` | adds the image-1 route gate |

**X's PREP overlay** narrows the composed codex schema to `worklog_access` ∈ {`classified-vault`, `classified-vault-and-template-candidate-worktrees`}. It selects the latter and binds `work_dir` to the handover worktree. A composed-schema assertion checks this, as in `test_successor.py` of the gct-e8ex window.

**Every window:**
- **ROUTE** uses exactly `gc sling <lane> <step> --no-formula --no-convoy --json`, target first, with no `--nudge` and no `--reassign`. With `relates-to` edges, no `gc.root_bead_id` and no convoy, a step close then triggers no Core auto-close cascade (`cmd_convoy.go:1854-1880`; `molecule_autoclose.go:142-166`).
- **BIND** stamps `gc.work_dir` (the handover worktree). For C1 and C2 it also stamps `gc.check_path`, the Template launch check pinned in P12/P13 (the pack `build-artifact-valid.sh`). A missing stamp refuses; Core's start preflight requires it.
- **Common snapshot.** It uses the gct-e8ex `common-snapshot-r1.py` (the full Template `.git` walk, not ga-3oa7's narrower one), chained: each window's `before` must equal the previous window's `after`.
  - One admitted change: the linked worktree's admin `index` may be rewritten by a session's own startup git. That would be the Claude harness or the codex harness, unsandboxed, for example Claude Code's git context. It is admitted only if:
    - the index stays a regular, single-link, operator-owned file;
    - the header, version and entry count are equal;
    - every entry's path, mode, blob id and flags are equal, including the v3/v4 extended flags (skip-worktree and intent-to-add), and only stat data moved;
    - every extension (TREE, UNTR, FSMN, EOIE, IEOT and link) is byte-equal;
    - no new file appears in the admin directory, such as a `sharedindex.*`.

    Anything else refuses. If the inventory shows a harness rewriting an extension, the rule is re-reviewed before C1.
  - The inventory runs the real wrapper and provider argv in a scratch linked worktree of a throwaway clone, never the canonical Template. If it cannot reproduce the managed lane, its result is recorded as a lower bound.
  - The chain's first `before` is taken after WORKTREE and before C1's BIND.
  - **No git reads.** No gate, reviewer or intake step relies on `git status` or `git diff` in the handover worktree, because a stat-only rewrite could make a racy-clean entry hide a content change. The images and the export read files only.
  - **Scope.** The common snapshot covers the Template `.git` only. The candidate-root audit (rule 6), the image, and the stated vault and `/tmp` scope are the complementary parts.
- **WATCH** records, on every tick, the routing (`gc.routed_to`) and assignee of the non-current steps, the holders and the root. Any change triggers CONTAIN at once.
  - When WATCH first observes the current step closed, it holds the lane at the agent level before anything else.
  - A worker with unsandboxed `bd update` could route a later step before closing its own, and the reconciler could start a session inside one tick. That tick-bounded gap is stated as a known limit, and it is detected by the store-wide diff and fails closed.
- **CLOSE:**
  - runs `verify_linked` on the worktree;
  - runs the rule 6 audit of the candidate root;
  - checks that the probe target stays empty;
  - verifies `gct-oak5`, the non-current steps and the holders are unchanged;
  - takes the rule 5 store diff since BIND, which must show exactly its allowlist and nothing else;
  - re-runs the audit that no default-choice codex route targets the candidate root (from A2).
- **Cache disposition.** It needs the operator's approval per window.

**Second-route negative (C1 only, operator decision).** During C1's WATCH, a guarded re-sling of the live step is issued only when all three hold:
- C1 is `in_progress`;
- its assignee equals its `gc.session_name`;
- no agent-level hold is in place.

**The release.** The C1 brief tells the worker to wait before closing, polling its step at a fixed cadence of about once every 60 seconds, for at most 20 minutes, for exactly one of two coordinator notes:
- `PROBE DONE gct-oak5 C1`, written after the sling and its evidence;
- `PROBE SKIPPED gct-oak5 C1`, written if the preconditions do not hold.

Each note is written by one pinned command (`bd update <C1> --append-notes '<text>'`) in the window's guarded environment, with `GIT_OPTIONAL_LOCKS=0`, under the window's cache disposition. It is admitted by rule 5 as the only non-worker note. If 20 minutes pass without either note, the brief says to continue and close.

A worker that releases itself early, by writing the text itself, can only make the negative unproven; it cannot fake it.
- **The proof depends only on the coordinator's own records:** the precondition read, the sling JSON, C1's state read right after the sling returns, and the census. It never depends on a note being present.
- A duplicated or worker-written `PROBE` text is recorded as worker self-release.

**Outcomes:**
- The sling ran with the preconditions held: the negative is proven or refused on its pinned evidence.
- Preconditions unmet, a timeout, or C1 closed first: the negative is recorded as unproven. There is no fallback.
- **The race.** If C1 closes between the precondition check and the sling, Core sees `gc.routed_to` equal to the target with an empty assignee and takes the convoy-recovery or idempotent branch (`internal/sling/sling_attachment.go:417-430, 454-458`). That is recorded as the race and as unproven, not as drift.
- **Drift.** C1's status is read after the sling returns. A close that lands inside the sling, after `CheckBeadStateWithOptions` has read the Bead, takes the idempotent `NoConvoy` path (`sling_attachment.go:346-349, 454-457`) and counts as the race. Only these count as configuration or Core drift, and stop the window:
  - an idempotent result while the post-sling read still shows C1 `in_progress` and assigned;
  - an assignee equal to the target identity.

**Preconditions, from the inventory:** the lane has no custom `sling_query`, and the default `session_template` applies. Otherwise both the warning path and the session-name argument below differ. The command:

`gc sling gas-city-template/gc.implementation-worker <C1> --no-formula --no-convoy --json`

It uses the reviewed target-first argument order, and never `--nudge` or `--reassign`.

**Core behaviour (f45a6262), as the source shows it:**
- **Not idempotent.** A claimed step's assignee is the session name, set by `gc hook --claim` at `cmd/gc/cmd_hook.go:445-448`. Session names contain no `/` (`internal/agent/session_name.go:53-59`), so the assignee never equals the target identity. `CheckBeadStateWithOptions` (`internal/sling/sling_attachment.go:454-461`) therefore returns only the warning "routed to X but assigned to Y", and `resolveIdempotentShortCircuit` (`internal/sling/sling_core.go:178-213`) returns false.
- **The call path.** The CLI enters through `doSlingBatchWithJSON`, then `ExpandConvoy`, then `DoSlingBatch`, then `DoSling` for a non-container Bead (`cmd/gc/cmd_sling.go:547, 984-999`; `internal/sling/sling.go:353-367`; `sling_core.go:1413-1474`).
- **The dispatch gate runs first.** It is the managed-product `DispatchGate` (`VerifyProfile`; `cmd_sling.go:502-507`, `sling_core.go:1417-1422, 60-65`). It reads the receipts, runs `InspectIntegrity`, including git with `--no-optional-locks` on the pinned repositories, and records an event only on refusal (`managed_product_dispatch_gate.go:51-70, 135-146`).
- **The plain route runs.** `slingPlainBead`, then `finalize`, then `cliBeadRouter.Route` (`internal/sling/sling_core.go:605-713`, `cmd/gc/cmd_sling.go:770-776`) rewrite `gc.routed_to` with the same value. That bumps `updated_at` and may add an event row. `finalize` pokes the controller (`sling_core.go:703-706`).
- **The JSON.** It reports `"routed": true` (`cmd_sling.go:1106, 1144`), with the bead warning in `"warnings"` (`cmd_sling.go:1110, 1162-1176`).
- **The claim cannot move.** `stampHookClaimIdentity` compares before writing and skips unchanged keys (`cmd/gc/cmd_hook_claim.go:513-552`).
- **What it does not do.** With no `--reassign` there is no reopen and no assignee clear (`sling_core.go:144-148, 341-343`). `--no-convoy` creates no convoy, and `--no-formula` attaches nothing. No nudge is signalled, because a nudge is honoured only with `--nudge`.

**Evidence, each pinned:**
- the sling JSON with `"routed": true` and the "routed … but assigned to …" warning in `"warnings"`;
- the dispatch gate passed, with no `ManagedProductDispatchRefused` event. The sling is a second gc invocation in the window, so the window's guarded environment and cache disposition cover it;
- C1's status, assignee, `gc.routed_to`, `gc.work_dir` and `gc.check_path` values unchanged. Only `updated_at` and the event row move, and rule 5 and CLOSE admit exactly these;
- no new session Bead;
- no start or refusal event after the poke;
- the census still shows one session and one worker cgroup through the rest of WATCH.

**What it proves:** a second route issued against the live segment neither moves the claim nor starts a second worker. The controller reconcile that the route triggers leaves exactly one session.

**What it does not prove:** that the route itself is refused; Core accepts the same-value write. The cap proof is the composed `MaxActiveSessions = 1` together with this reconcile and the census. Cross-agent exclusion rests on the gates.

## After C2: intake, signing and delivery

The gct-mbg6 intake runs unchanged in method:
1. export from the handover worktree, with no git there, and rules 1 to 5 on the final state;
2. the reviewed tree id in a scratch index outside every write root;
3. the exported bytes committed to the Operations worktree for two aegis-reviewer passes;
4. signing in a standalone Template clone from GitHub at BASE;
5. the tree id must equal the reviewed one;
6. then the signed commit, push, Template PR, required-green CI, merge, and close of the steps and `gct-oak5`.

**The canonical checkout is not moved by delivery.** It stays at `3474abfa` until a later reviewed metadata successor moves it.

## Acceptance as adapted (recorded on gct-oak5)

- **One registered worktree.** C1, X and C2 ran in one registered worktree on one branch, under one root Bead with three step Beads.
- **One worker and claim at a time.**
  - Within a lane: the claim and the cap, with the same-lane negative.
  - Across agents: the suspension gates and the census.
  - Zero session and process residue after each window.
- **Images and single deltas.**
  - Images 1 and 2 are byte-exact at each switch: HEAD, unstaged, untracked and ignored content, the gitfile and admin files, Bead state and the chained common snapshot.
  - Each segment's delta is exactly its contract, and each is present exactly once at the end.
  - Staged work is not provable under the no-`.git`-write lanes, as the operator decided on 2026-09-27.
  - Empty directories and group or other mode bits are outside the image.
- **Negatives refused:**
  - writes outside each lane's write roots (X and C2);
  - a codex `git commit`, with the pinned lock refusal;
  - a second route issued against the live C1 segment: the same-value route write is accepted, but it neither moves the claim nor starts a second worker, as described above. If it cannot run cleanly in C1, it is recorded as unproven, per the operator decision;
  - an image mismatch on a tampered copy, with a positive control.

  Containment inside the candidate root rests on the rule 6 audit at ROUTE and RESUME and at CLOSE, not on the sandbox.
- **Known limits, stated on gct-oak5:**
  - **The RESUME gap.** Between the last rule 6 audit before RESUME and the session reading its files.
  - **The root directory.** Containment of the candidate root directory itself, as well as of entries inside it, rests on the rule 6 audits at ROUTE, RESUME and CLOSE. X's write roots include the whole root.
  - **The close-then-route tick.** A worker's unsandboxed `bd update` can route a later step before its own close. The gap is bounded by one WATCH tick, detected and fail-closed.
  - **The negative's controller poke.** The second-route negative's same-value route write triggers one controller reconcile during C1's window. This is expected and recorded.
  - **`/tmp`.** X's `/tmp` is the host `/tmp`, so a survivor could plant files there. The C2 tests use a declared temp inside the worktree, which C2 deletes and the final export checks. ROUTE's `city_problems` checks the tmux socket, as in the gct-e8ex Known scope.
  - **Core git through a redirected gitfile.** Core runs plain git in worktrees, as the operator, during a window. A gitfile redirected by X is detected only after X's window, by the gitfile bytes and `verify_linked`.
  - **The vault.** It is an X write root. No Claude lane, intake or later window reads it, and X is told to write nothing there. Any vault write X makes is recorded, not prevented.
  - **Claim scope.** Whether `gc hook --claim` can take ready but unrouted work in the rig is confirmed from Core source before C1. WATCH detects any claim other than the routed step, and that is a stop.
- **Delivery.** Coordinator intake signature, signed PR, required-green CI and merge.
- **No provider-parity claim** beyond this evidence.

## Order of packages

1. This plan, then two reviews.
2. **Inventories:**
   - the gc runtime files per lane;
   - Claude and codex startup git in a scratch linked worktree of a throwaway clone, never the canonical Template, using the real wrapper and provider argv;
   - the pinned Template test command offline;
   - the claim scope of `gc hook --claim`, from Core source;
   - whether the bd close event's actor records the session identity or the OS user, in each lane;
   - the exact field set that a real `bd close` and a real claim write in bd 1.2.2;
   - that neither lane has a custom `sling_query`, and that the default `session_template` applies;
   - that `.oak5-c2-tmp/` is neither tracked nor ignored at BASE; that the exact pinned C2 test command, env-variable form included, runs under the live lane policy and sandbox; that deleting the directory is permitted; and the effective `norecursedirs`;
   - the city-store writes of one real lane session lifecycle, `on_death` and `on_boot` included, and of a controller poke;
   - Core's progress-stall attention write set on a claimed Bead, and whether any lane prompt calls `gc bd heartbeat`;
   - the claimless idle case: `sessionProgressStalled` is suppressed while a claim is held, so there is no restart during C1's PROBE wait or C2's test. After the close, the 5-minute threshold is measured from the worker's last provider activity, not from the close (`cmd/gc/session_progress.go:66-74`; `session_reconciler.go:2525-2535`). So WATCH's agent-level hold must land less than 5 minutes after the worker's last provider activity; in practice, on the first tick after the observed close. A restart refuses as off the pinned session sequence;
   - the attention chain: the `orchestrator-attention-relay` order and its retry order, `watch-officer-mail-wake`, and the watch-officer and per-rig `orchestrator` named sessions. Each window's overlay must hold both named sessions;
   - the Core maintenance thresholds (wisp-compact, reaper) and orphan-sweep, from the deployed pack scripts;
   - the Core orders and patrols that can write the Template rig store, and their cadence;
   - each lane's exact hook store list and route targets;
   - the Bead-store snapshot method, its completeness and its determinism;
   - the live members of `gct-wn1m` (children, `gc.root_bead_id` rows, convoys, molecules, edges);
   - whether either lane prompt sets `gc.work_outcome` or other work-record keys before close.
3. The split package (steps, holders, the empty `H1` and `H2` placeholders, `blocks` and `relates-to` edges), then two reviews, then applied. The same package closes `gct-wn1m` and its members as obsolete in one quiet step, per the operator decision, and verifies the end state including Core's auto-close. It records the pre-route queue audit showing both lanes' eligible sets empty.
4. **The chain anchor**, the first settled Bead-store snapshot, after the split package.
5. The image tool, then two reviews.
6. WORKTREE, as part of C1.
7. The C1 window, then two reviews, then run.
8. H1.
9. The X window, then two reviews, then run.
10. H2.
11. The C2 window, then two reviews, then run.
12. The intake, signing and delivery.
13. The retire job, then M13.
14. Terminal evidence on gct-oak5.

Codex quota for X is re-checked immediately before X's ROUTE. If it is short, that is the standing stop condition.

## r2 (answers the r1 reviews of `8b7bb3ae`: A and B HOLD)

- **Must_fix: planted control files (A 2, B 1).** The route gate now checks the delta's shape and refuses agent-control paths. Runtime entries are admitted only with pinned bytes per lane, `.codex/hooks.json` must be absent before X, and ignored entries must be empty (Handover images and the route gate).
- **Must_fix: out-of-worktree negatives (A 1, B 3).**
  - Each probe target sits outside every lane write root.
  - The acceptance says "outside the lane's write roots".
  - Containment inside the candidate root rests on the per-window top-level audit.
- **Must_fix: second-route negative (B 2, A should_fix 3).**
  - The cross-agent sling is dropped.
  - A same-lane probe uses an exact sling form and a full-snapshot restore.
  - The proofs are restated consistently.
- **Should_fix taken:**
  - the `gc.check_path` stamp is fixed in BIND (A 1, B 6);
  - image holders with description re-pins (A 2);
  - the full chained common snapshot with the admin-index rule (A 4, B 4);
  - `verify_linked` and the top-level audit after every window (A 5);
  - CLOSE verifies Bead state (A 6, B 3);
  - codex prompt overrides and pinned probe errors (A 7, B 5);
  - a positive control for the tamper test (A 8);
  - ignored content hashed (A 9, B 1);
  - BASE clone and outputs outside every root (A 10);
  - `blocks` edges (A 11);
  - worktree lifecycle and M13 (A 12);
  - schema wording (A 13);
  - nested `.git` (B 2);
  - cross-agent proof stated (B 7);
  - the image limits stated (B 8).

## r3 (answers the r2 reviews of `78883895`: A and B HOLD)

- **A must_fix 1 and B must_fix 2: the probe Bead.** It is gone. The negative is now an idempotent re-sling of the live, claimed C1 step:
  - the reviewed argument order, with no `--nudge`;
  - issued only after C1's assignee equals the live session;
  - Core's short-circuit (quoted) mutates nothing.

  It proves a refused second route with no residue. The cap and the cross-agent exclusion are proven separately and are stated as such.
- **A must_fix 2: rule 1 could never pass.**
  - A holder is excluded from its own image.
  - Rule 1 admits exactly the holder description and the next step's pinned BIND keys.
- **B must_fix 1: planted instructions above the worktree.** Rule 6 is a lstat-only audit of the candidate root and of `CLAUDE*.md` and `AGENTS*.md` above the worktree, run at ROUTE and immediately before RESUME. The remaining gap is stated.
- **Should_fix taken:**
  - the fourth codex override, direct `git commit` (A 1);
  - rule 3 made relative to BASE, which tracks control paths (A 2);
  - runtime entries sit outside the delta and are never delivered, and `.agents/**` must be absent in image 1 (A 3);
  - the admin-index rule is fully defined, and the inventory uses the real argv (A 4, B 6);
  - the probe-target path is exact (A 5);
  - WATCH records the non-current steps each tick, with an immediate CONTAIN (A 6);
  - the closer's identity comes from the close event's actor (A 7);
  - the pinned test command, private temp and rule 4 on the final export (A 8, B 1, B 8);
  - the first `before` taken after WORKTREE (A 9);
  - the vault worklog waived (A 10, B 3);
  - `/tmp`, redirected-gitfile and vault scope stated (B 1-3);
  - a store-wide Template Bead diff and a queue-exactly-the-step check (B 4);
  - claim scope confirmed from source (B 5);
  - holder wording (B 7);
  - chained-snapshot scope wording (B 9).

## r4 (answers the r3 reviews of `02d53871`: A and B HOLD)

- **A must_fix 1 and B must_fix 1: the re-sling is not idempotent after the claim.** Both reviewers read the f45a6262 source correctly: a claimed step's assignee is a session name, so the re-sling takes the plain route. It writes the same `gc.routed_to` and pokes the controller. It never reassigns, reopens, attaches or nudges.
  - The negative now pins that real effect, with exact source lines.
  - The rules and CLOSE admit exactly the `updated_at` bump and the event row.
  - It is restated as proving that the claim does not move and that no second worker starts, not that the route is refused.
- **A must_fix 2 and B should_fix 1: the C2 temp directory.** The staging `c2-tmp` is gone. The temp is at the declared `<worktree>/.oak5-c2-tmp/`, inside the lane's existing write root, so no policy or receipt change is needed. C2 deletes it, and CLOSE's final export proves it is gone.
- **Should_fix taken:**
  - **The test run's write reach.** It is stated, the post-test export check is explicit, and the network and excluded-command reach is named (B 2).
  - **Git reads.** No gate relies on git reads, and the v3/v4 flags are included (B 3).
  - **Harmlessness claims.** The "wake only with `--nudge`" claim is dropped, `--reassign` is forbidden, and the controller poke is a stated limit (B 4, A 5).
  - **The root directory.** Its containment rests on rule 6 (B 5).
  - **WATCH timing.** WATCH holds the lane at the agent level on the observed close, the tick gap is stated, and `opt_*` and `template_override*` keys refuse (A 1).
  - **Rule 5's terms.** They are pinned:
    - the allowlist;
    - the close evidence, with the actor as an inventory item;
    - the queue as routed set and ready set, before and after ROUTE (A 2, A 3).
  - **The other holder.** H2 must be empty at X's ROUTE (A 4).

## r5 (answers the r4 reviews of `6cb8cf18`: A HOLD, B SOURCE_PASS)

- **A must_fix 1: the whole-rig ready set.** This could never hold: `gct-oak5` and about 109 other open Template Beads are ready. The queue term is now the lane-eligible set:
  - the Beads routed to the lane are none before ROUTE and exactly the step after it;
  - the s3 per-row stop conditions hold, for the aliases of both lanes;
  - `gct-oak5` and other unrouted Beads are stated as not claimable, tied to the claim-scope inventory.
- **Should_fix taken from A:**
  - the negative's same-value write is in the allowlist, and CLOSE uses the same list (A 1);
  - the stale rule 4 sentence is fixed (A 2);
  - C2 records digests before the test (A 3);
  - the negative's race and fallback outcomes are pinned (A 4);
  - JSON field names (A 5);
  - the full call path and the dispatch gate are cited (A 6).
- **Should_fix taken from B:**
  - the allowlist is pinned key by key and value by value, including BIND stamps, claim keys, close fields and the next step's BIND (B 1);
  - the store diff covers every store `bd` can reach, and the test-code reach is corrected (B 2);
  - the negative's preconditions, the `PROBE DONE` wait and the fallback are set (B 3);
  - the dispatch gate is part of the evidence (B 4);
  - distinct pre-created temp subdirectories, with the exact command proven by the inventory (B 5);
  - both stale temp lines are fixed (B 6);
  - the close evidence is read from the last tick and cross-checked with `gc.session_*` (B 7);
  - the `sling_query` and `session_template` preconditions (B 8).

## r6 (answers the r5 reviews of `11523ead`: A and B HOLD; operator decisions of 2026-09-27)

- **A must_fix 1: the live stale workflow.** The operator chose "Close as obsolete".
  - The split package closes `gct-wn1m` (`gct-af6u`, `gct-20mc`, `gct-svpm`, `gct-dh6u`, `gct-v7yb`) with notes, before C1.
  - The lane-eligible set and its pinned target, alias and identity sets are checked before each ROUTE.
- **A must_fix 2 and B must_fix 1: legitimate writes the store diff refused.**
  - Exactly one session Bead lifecycle per window is admitted, with the inventory-pinned key set, state sequence and bookkeeping.
  - The store diff is now chained per window.
  - Coordinator writes between windows are admitted only by id and digest in a between-window ledger.
- **A must_fix 3 and B must_fix 2: the C2 fallback.** It is removed by the operator decision "Keep, C1 only".
  - The negative has a bounded wait and `PROBE DONE` / `PROBE SKIPPED` release notes with pinned text and command.
  - The race outcome is separated from drift.
  - Unproven is an allowed recorded outcome.
- **Should_fix taken:**
  - "routed" means open or in_progress rows, closed rows excluded; the step exception after ROUTE; per-lane alias and identity sets (A 1-3);
  - the `PROBE` notes are pinned in text, author, command, environment and place (A 4, B 2);
  - the wait is bounded, with its timeout outcome and self-release handling (A 5, B 3);
  - temp deletion is proven by the inventory (A 6);
  - X's BIND is `gc.work_dir` only (A 7);
  - the claim-scope branches, workflow `gc.run_target` rows and identity-assigned rows including the deterministic session name, are in the eligible set (B 1);
  - the race versus drift distinction (B 4);
  - `gc.work_outcome` is forbidden or pinned (B 5);
  - the excluded commands are named, and the planted-file influence on unsandboxed `bd` is a stated limit (B 6);
  - the effective `norecursedirs` is checked (B 7).

## r7 (answers the r6 reviews of `a9dcf9c6`: A and B HOLD)

- **A must_fix 1: Core's progress-stall attention.** The allowlist admits this write set on the current step, pinned by shape and recorded as a declared result, and it is an inventory item. The poll cadence is a fixed ~60 s.
- **B must_fix 1: the city-wide chained snapshot.**
  - The chain covers the Template rig store plus a projection of lane-relevant rows and lane session Beads elsewhere. Outside activity is admitted as a limit.
  - The snapshot method, completeness and determinism are inventory items.
  - The anchor is taken before the split package.
  - Ledger entries are pre-image plus delta, and the ledger is exhaustive for the chained scope.
  - CLOSE-after comes after the session close, the postflight and the recovery hooks.
- **B must_fix 2: the eligible set's stores.** The set is computed over the lane's exact hook store list, with `RoutedToIdentity`, the qualified name and `GC_TEMPLATE` as targets.
- **Should_fix taken:**
  - the `gct-wn1m` closure: live enumeration, one quiet step, controls first, root last, `gc.work_outcome=abandoned`, both lanes audited (A 1, B 1);
  - the anchor and the ledger's exhaustiveness (A 2);
  - the drift observation time and the race path (A 3);
  - the session close before CLOSE-after (A 4, B 2);
  - the fixed poll cadence (A 5);
  - reused or reopened sessions refuse, and values are compared (B 3);
  - the probe proof rests only on coordinator records (B 4);
  - continuation-group and legacy alias conditions (B 5).

## r8 (answers the r7 reviews of `930ae89e`: A SOURCE_PASS, B HOLD)

- **B must_fix 1: Core's auto-close during the `gct-wn1m` closure.** The chain anchor moves to after the split package and its closures have settled, so Core's auto-close writes land before the chain begins. The package records who closed each member (coordinator or Core) and verifies the end state. Controls are classified by `gc.kind` over Core's full control-kind set. The source shows no dispatch risk.
- **Should_fix taken:**
  - `gc.last_heartbeat_at` attributed to the worker (A 1, B 1);
  - stall attention pinned exactly where Core allows: literals, a recomputed signature and the error template (A 2, B 2);
  - `on_death` and `on_boot` scoped to work Beads, and a new session Bead per start confirmed (A 3, A 9);
  - an observable completion test for CLOSE-after and the anchor settle, with the order and patrol cadence in the inventory (A 4, B 3);
  - Core writes on member close are absorbed before the anchor (A 5, B must_fix);
  - a fixed projection function with ids learned later applied back, and set equality over row ids (A 6, B 4);
  - the hold and the suspend and resume included in the bookkeeping inventory (A 7);
  - the duplicate "4." numbering removed (A 8);
  - the claimless idle restart bounded by CONTAIN and stated (B 2);
  - Template rig quiet enforcement named (B 3);
  - worker writes outside the chained scope named as a limit, with other lanes' own pre-route audits (B 4);
  - ledger composition, and an absent pre-image for creates (B 5);
  - the hook store list pinned from a real session's `agentForQuery` (B 6);
  - control classification by `gc.kind` (B 7).

## r9 (answers the r8 reviews of `4cbef00f`: A SOURCE_PASS, B HOLD)

- **B must_fix 1: automation acts on `needs/operator`.** The claim that none did is corrected.
  - The attention relay, its retry, the mail wake and the watch-officer and Template orchestrator named sessions are in the inventory.
  - Each window's overlay must hold both sessions, and PREP asserts it.
  - Between windows no mark can arise.
  - The relay's mail and state file are a stated limit outside the chained scope.
- **Should_fix taken from B:**
  - Core maintenance acts on row age, so its writes are admitted by recomputed pinned thresholds, never on the root, the steps or the holders (B 1);
  - the anchor equals the package's verified end state, plus a pre-package versus post-settle diff that maps every changed row (B 2, A 3, A 4);
  - raw snapshots are retained, with a final re-run under the final identity set (B 3, A 7);
  - the signature's write-time inputs and the embedded session name (B 4, A 1);
  - the restart bound runs from the last provider activity (B 5, A 5);
  - orphan-sweep is named (B 6).
- **Should_fix taken from A:**
  - the ROUTE sling form `--no-formula --no-convoy` is pinned for every window. With `relates-to` edges, no `gc.root_bead_id` and no convoy, a step close triggers no Core auto-close cascade (A 2; see Windows);
  - settle versus held orders: nothing is held by config, and maintenance is admitted by rule (A 6);
  - heartbeat on the current step only (A 8).

## r10 (applies the inventory to the accepted r9)

The inventory (`INVENTORY.md`, `inventory-data.json`) contradicted or completed r9 in six places:
- **Runtime entries.** A lane start writes a fixed per-lane set into the worktree: `.gc/` files, a skill sink of links with an ownership file, a catalog snapshot, and, for codex, `.codex/hooks.json`. The tool now classifies these as `RUNTIME`, pinned by bytes, mode and link target. Rules 2 and 4 admit them explicitly, and every other control-path entry still refuses.
- **The close keeps the assignee.** r9 said Core clears it on close, but it does not. A cleared assignee is Core's orphan release, which now refuses. `bd history` records no actor.
- **The claim key set** is `gc.work_branch`, `gc.session_id` and `gc.session_name`. The two empty keys seen on gct-mbg6 were orphan-release writes, not claim writes.
- **Session Beads** have event-dependent optional keys. They are admitted as a subset of the lane's observed key union, with the identity keys pinned by value and the end state per lane.
- **Orders do not run.** The city is suspended, and no order but `nudge-on-route` has run since 2026-09-12. The recomputed maintenance admission is replaced by refusal plus an order-history check, and the settle interval becomes 5 minutes.
- **The hook store list** is {Template rig store, city store} for both lanes.

Two inventory items remain as live probes before the C1 window package: startup git (probe A) and the C2 test command (probe B), in a scratch clone.
