# gct-oak5 handover: C1 (Claude) → X (Template codex) → C2 (Claude) in one worktree — plan r4

This is the design for goal step 4 (gct-oak5; gct-13ku and gct-10pg are its closed prerequisites). It is reviewed before any window package is built. Every window, tool and Bead text named here is its own reviewed package later. r2 and r3 answered the r1 and r2 reviews, and r4 answers the r3 reviews of `02d53871` (A and B HOLD); see the last three sections.

## Decisions this plan relies on

- **2026-09-24, handover admission (a).** One Template Bead scope, without Core's one-start attempt stamp. One worker at a time is proven as follows:
  - **Within a lane:** by the claim and `max_active_sessions = 1`.
  - **Across the two agents:** by the window gates only, namely the suspension overlay and the session and cgroup census. The per-agent cap cannot exclude a concurrent Claude and codex session, so the gates are the cross-agent proof.
- **2026-09-27, "New codex choice".** The Template codex agent gets `classified-vault-and-template-candidate-worktrees`. Its write roots are the vault and the whole candidate root, with no `.git`. A2, M12 and P13 are live.
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
| C2 | Verify H2 the same way. Finish the change in `M1`, `M2`, `A1` and `A2` only. Run the pinned test command sandboxed and record the result. Run the negative probe. Close C2. |

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
- `TMPDIR` and pytest `--basetemp` at the declared path `<worktree>/.oak5-c2-tmp/`, inside the lane's existing write root, so no policy or receipt change is needed. The inventory confirms the path is neither tracked nor ignored at BASE.
- After the test and before its note, C2 deletes `.oak5-c2-tmp/`.

**Checks on the test run.**
- CLOSE's final export (rules 2 to 4 and 6) must show that `.oak5-c2-tmp/` is gone and that `M1`, `A1`, `M2` and `A2` hold exactly what C2 recorded after its edits.
- The test run executes code X wrote, and under this policy its sandbox can write the whole candidate root. Any file it plants or rewrites is caught by that export check, not prevented.
- The inventory proves that the tests import the worktree's code.
- The sandbox has no network allowlist. Test code could still invoke the five excluded unsandboxed commands (`gc hook --claim`, `gc runtime drain-ack`, `bd close|show|update`). Any Bead change they make is caught by the store-wide diff (rule 5).

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
- **Runtime entries.** `RUNTIME` is decided per lane by an inventory before the tool's review:
  - what gc writes into a worktree at a Claude session start and at a codex session start, and whether it overwrites, merges or skips an existing file;
  - each admitted runtime entry is pinned with its exact expected bytes per lane;
  - runtime entries sit outside the contract delta and are never delivered by the intake.

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
   - Image 1 minus BASE is exactly {`M1` modified, `A1` added}.
   - Image 2 minus image 1 is exactly {`M2` modified, `A2` added}, with `M1` and `A1` unchanged.
   - There are no deletions and no other paths.
3. **No agent-control path is added, changed or deleted relative to BASE,** other than admitted runtime entries equal to their pinned bytes. BASE itself tracks `AGENTS.md`, `CLAUDE.md`, `.claude/**`, `.codex/config.toml`, `.codex/rules/*` and `tests/conftest.py`, and those must stay byte-equal to BASE. Refused paths:
   - anything under `.codex/`, `.agents/` or `.claude/`;
   - any file named `AGENTS*.md`, `CLAUDE*.md`, `.mcp.json`, `conftest.py`, `sitecustomize.py` or `*.pth`;
   - the stop names.

   `.codex/hooks.json` and `.agents/**` must be absent in image 1, unless an entry is a pinned Claude-lane runtime entry: no codex session has run there yet.
4. **No ignored entries at all** in images 1 and 2, and in the final export. C1 and X run no tests and create no caches, and C2's temporary files live outside the worktree.
5. **Bead state is as expected.**
   - `gct-oak5` and the non-current steps are unchanged.
   - The previous step was closed by its own worker. The evidence comes from WATCH:
     - the step's assignee at close equals the session that held the claim;
     - the close happened while that session was the only live worker, per the census;
     - the coordinator issued no close.

     If the inventory shows that the bd close event's actor records the session identity, that actor is also required to match.
   - A store-wide diff of Template Beads since the previous window's BIND shows only the allowlisted changes:
     - on the current step: status, assignee, appended notes, and `gc.*` routing and claim keys, set only by BIND, ROUTE and the claim;
     - on the holder: the coordinator's image write;
     - `updated_at` and event rows accompanying these.

     Any `opt_*` or `template_override*` key on any step, holder or the root refuses.
   - **Queue.** Before ROUTE, the lane's routed set (Beads with `gc.routed_to` equal to the lane) is empty, and the rig's ready set holds exactly the step about to be routed. After ROUTE, the routed set is exactly that step (the s3 pre-route and post-route queue audits, for both lanes).
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
  - takes a store-wide diff of Template Beads since BIND, which must show only the expected changes;
  - re-runs the audit that no default-choice codex route targets the candidate root (from A2).
- **Cache disposition.** It needs the operator's approval per window.

**Second-route negative.** During C1's WATCH, once C1's assignee equals the live session, a guarded re-sling of the live step is issued:

`gc sling gas-city-template/gc.implementation-worker <C1> --no-formula --no-convoy --json`

It uses the reviewed target-first argument order, and never `--nudge` or `--reassign`.

**Core behaviour (f45a6262), as the source shows it:**
- **Not idempotent.** A claimed step's assignee is the session name, set by `gc hook --claim` at `cmd/gc/cmd_hook.go:445-448`. Session names contain no `/` (`internal/agent/session_name.go:53-59`), so the assignee never equals the target identity. `CheckBeadStateWithOptions` (`internal/sling/sling_attachment.go:454-461`) therefore returns only the warning "routed to X but assigned to Y", and `resolveIdempotentShortCircuit` (`internal/sling/sling_core.go:178-213`) returns false.
- **The plain route runs.** `slingPlainBead`, then `finalize`, then `cliBeadRouter.Route` (`internal/sling/sling_core.go:605-713`, `cmd/gc/cmd_sling.go:770-776`) rewrite `gc.routed_to` with the same value. That bumps `updated_at` and may add an event row. `finalize` pokes the controller (`sling_core.go:703-706`), and the JSON reports `Routed: true`.
- **What it does not do.** With no `--reassign` there is no reopen and no assignee clear (`sling_core.go:144-148, 341-343`). `--no-convoy` creates no convoy, and `--no-formula` attaches nothing. No nudge is signalled, because a nudge is honoured only with `--nudge`.

**Evidence, each pinned:**
- the sling JSON with `Routed: true` and the "routed … but assigned to …" warning;
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
  - a second route issued against the live segment: the same-value route write is accepted, but it neither moves the claim nor starts a second worker, as described above;
  - an image mismatch on a tampered copy, with a positive control.

  Containment inside the candidate root rests on the rule 6 audit at ROUTE and RESUME and at CLOSE, not on the sandbox.
- **Known limits, stated on gct-oak5:**
  - **The RESUME gap.** Between the last rule 6 audit before RESUME and the session reading its files.
  - **The root directory.** Containment of the candidate root directory itself, as well as of entries inside it, rests on the rule 6 audits at ROUTE, RESUME and CLOSE. X's write roots include the whole root.
  - **The close-then-route tick.** A worker's unsandboxed `bd update` can route a later step before its own close. The gap is bounded by one WATCH tick, detected and fail-closed.
  - **The negative's controller poke.** The second-route negative's same-value route write triggers one controller reconcile during C1's window. This is expected and recorded.
  - **`/tmp`.** X's `/tmp` is the host `/tmp`, so a survivor could plant files there. The C2 tests use a private staging temp, and ROUTE's `city_problems` checks the tmux socket, as in the gct-e8ex Known scope.
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
   - that `.oak5-c2-tmp/` is neither tracked nor ignored at BASE.
3. The split package (steps, holders, the empty `H1` and `H2` placeholders, `blocks` and `relates-to` edges), then two reviews, then applied.
4. The image tool, then two reviews.
5. WORKTREE, as part of C1.
6. The C1 window, then two reviews, then run.
7. H1.
8. The X window, then two reviews, then run.
9. H2.
10. The C2 window, then two reviews, then run.
11. The intake, signing and delivery.
12. The retire job, then M13.
13. Terminal evidence on gct-oak5.

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
