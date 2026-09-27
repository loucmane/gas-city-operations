# gct-oak5 handover: C1 (Claude) → X (Template codex) → C2 (Claude) in one worktree — plan r1

This is the design for goal step 4 (gct-oak5; gct-13ku and gct-10pg are its closed prerequisites). It is reviewed before any window package is built. Every window, tool and Bead text named here is its own reviewed package later.

## Decisions this plan relies on

- **2026-09-24, handover admission (a).** One Template Bead scope, without Core's one-start attempt stamp. One worker at a time is proven by:
  - the claim;
  - `max_active_sessions = 1`;
  - the window gates.
- **2026-09-27, "New codex choice".** The Template codex agent gets `classified-vault-and-template-candidate-worktrees`. It writes the vault and the candidate root, and no `.git`. A2, M12 and P13 are live.
- **2026-09-27, "Adapt acceptance".**
  - The handover images cover HEAD, unstaged and untracked work, and Bead evidence.
  - Staged work is recorded as not provable, because neither lane can write `.git`.
  - After C2, the coordinator's reviewed intake signs, then the PR, CI and merge follow.
  - No provider-parity claim is made beyond this evidence.
- **Live state.**
  - The Claude lane is `gas-city-template/gc.implementation-worker`: provider `claude-template-candidate`, `work_dir_roots` the candidate root, cap 1. Its receipt profile is `2341a9a0`.
  - The codex lane is `gas-city-template/codex`, cap 1, with `work_dir_roots` both Template roots.
  - M12 file `114b4a00`, P13 receipt `7185414e`, revision `a61666b3`.

## Beads

**Root.** `gct-oak5` stays the root and carries the acceptance. It is never routed.

**Steps.** Three step Beads carry the segments: `C1`, `X` and `C2`, created in `gas-city-template` with label `handover`.
- Their edge to `gct-oak5` is `relates-to`, never parent-child: bd 1.2.2 hides children of an open parent from `bd ready`.
- Each step Bead's description is a short task that points to closed holder Beads for the long text. Every plain view stays under about 9,000 bytes. This is the R3/R4 and gct-e8ex split pattern, a reviewed `split` package.

**The Claude implementation-worker prompt** (pack `cc9e72b2`) executes and closes the claimed Bead. The codex prompt closes the claimed item after its acceptance evidence. So each step's acceptance is its stop point:
- the worker records its evidence note;
- it closes only its own step Bead;
- it never touches `gct-oak5` or another step.

**Step contracts:**

| Step | Contract |
| --- | --- |
| C1 | Implement the first half of a small bounded Template change: a documented helper module plus its test file. Leave exactly one modified tracked file and one new untracked file. Note the paths and digests, then close C1. |
| X | Verify the C1 image, a digest list given in the brief, against the worktree before any edit; on mismatch, note `IMAGE MISMATCH` and stop without edits. Do not redo C1's edits. Add one more modified tracked file and one more untracked file, then close X. Negative probes, each expected to be refused, with the refusal text recorded: a `git commit` (no `.git` write root), and a write to a sibling path outside the worktree (sandbox). |
| C2 | Verify the X image the same way. Finish the change, run the tests and record the result, then close C2. Negative probe: a write outside the candidate root, refused by the policy. |

No step stages, commits, pushes, signs or touches git state. The briefs forbid it. For Claude, the policy denies `.git` edits and git publication; for codex, the write roots exclude every `.git`.

## The worktree

One linked worktree of the canonical Template: `/home/loucmane/gas-city-template-candidate-worktrees/gct-oak5` on branch `codex/gct-oak5-handover-proof`, at BASE `3474abfa` (Template origin/main, the M11/M12 pinned commit).

**Created by** a reviewed WORKTREE job before C1. It is the gct-mbg6 `worktree-task-r1` retargeted to the candidate root. The job runs the pre-add driver, attributes and gitlink checks.

**Canonical `HEAD` stays at `3474abfa`.** Moving it would refuse managed dispatch. Adding a linked worktree changes the Template `.git` tree, which the metadata pins as a tree. Two facts about this:
- `InspectIntegrity` does not examine metadata trees, so dispatch is not refused.
- The next metadata successor must admit the `.git` change as an exact pair, as M11 did.

## Handover images

**The tool** is `intake_template.py export`, generalised. It walks the worktree with no git and no links. It compares every regular file with BASE, read from a GitHub-only bare clone, and writes a manifest: every changed, added and deleted path with mode, blob id, sha256 and size, plus the ignored count and digest.

**Changes to generalise it:**
- the candidate root joins `FORBIDDEN_ROOTS`, as an output location;
- the Claude runtime entries join `RUNTIME`, after a read-only inventory of what a Claude session writes into a worktree.

**Image contents.** Image *n* is that manifest (the unstaged and untracked delta against BASE) plus:
- the worktree `.git` gitfile bytes and the branch ref, read as files, not with git;
- the canonical `HEAD` bytes;
- the step Bead's notes digest and claim state;
- the root Bead's notes digest.

**How an image is used:**
1. The coordinator takes image 1 after C1's window reaches TERMINAL.
2. Before X's ROUTE, the X window recomputes the image and refuses unless it is byte-equal to image 1 (the ROUTE pre-check).
3. X's brief carries image 1's per-path digests, so the worker's own check is a second, independent gate.
4. Image 2 is taken the same way after X, and C2 is gated on it.

**Exactly once.** The acceptance check proves each earlier delta is present exactly once:
- C1's paths and digests are in image 2 unchanged, unless X was told to change them, which it is not;
- X's are in the final image;
- no step note is duplicated.

**Tamper negative.** Verifying a copy of the worktree with one byte changed must refuse. This runs as a tool test and once live on a copy outside every write root, never on the real worktree.

## Windows

Each segment is one reviewed window. Each is a successor package generated with asserted replacements from the last window that ran on the same lane:
- **C1 and C2** derive from ga-3oa7, the last Claude candidate-lane window. They are retargeted to the Template rig and the Template Claude lane the way the gct-e8ex window retargeted ga-3oa7 to Template codex. They are rebased onto M12 and P13.
  - C1 routes step `C1`.
  - C2 is C1's package rebased to step `C2` with the image-2 gate.
- **X** derives from the gct-e8ex window (s3, the last Template codex window). It is rebased onto M12 and P13. Its PREP overlay selects `classified-vault-and-template-candidate-worktrees`, the only codex choice left in the narrowed schema besides `classified-vault`, and binds `work_dir` to the handover worktree.

**Carried from the A2 reviews:**
- every window pins `work_dir` and audits that no default-choice codex route targets the candidate root;
- X's close step runs `verify_linked` and a new-top-level-entry audit of the candidate root before any git runs.

**Every window keeps the reviewed discipline:**
- quiescent and suspended city;
- one route, then WATCH, RESUME, CONTAIN and CLOSE;
- cgroup residue census;
- ADMIT, RESTORE and TERMINAL;
- a coordinator-cache disposition that needs the operator's approval per window.

**One claim at a time.** It is proven per window by:
- the census before and after;
- the claim trace;
- `max_active_sessions = 1`;
- only one step Bead routed per window.

**Negative: a second route while live.** During C1's WATCH, a guarded `gc sling` of step `X` to `gas-city-template/codex` is issued while the codex rig lane is suspended by the overlay. It must not start a session. That is proven by the census, and the X step returns to open and unassigned in CLOSE.

## After C2: intake, signing and delivery

The gct-mbg6 intake runs unchanged in method:
1. export from the handover worktree, with no git there;
2. the reviewed tree id in a scratch index outside every write root;
3. the exported bytes committed to the Operations worktree for two aegis-reviewer passes;
4. signing in a standalone Template clone from GitHub at BASE;
5. the tree id must equal the reviewed one;
6. then the signed commit, push, Template PR, required-green CI, merge, and close of the steps and `gct-oak5`.

**The canonical checkout is not moved by delivery.** After merge the Template main moves, but the canonical `HEAD` stays at `3474abfa` until a later reviewed metadata successor moves it.

## Acceptance as adapted (recorded on gct-oak5)

- **One registered worktree.** C1, X and C2 ran in one registered worktree on one branch, under one root Bead.
- **One worker and claim.** Exactly one worker and claim was live per window, and there was zero session or process residue after each.
- **Images and single deltas.**
  - Images 1 and 2 are byte-exact at each switch: HEAD, unstaged, untracked, gitfile and notes.
  - Each earlier delta is present exactly once.
  - Staged work is not provable under the no-`.git`-write lanes, as the operator decided on 2026-09-27.
- **Negatives refused:**
  - a second route while live;
  - a codex `git commit`;
  - out-of-worktree writes by X and C2;
  - an image mismatch on a tampered copy.
- **Delivery.** Coordinator intake signature, signed PR, required-green CI and merge.
- **No provider-parity claim** beyond this evidence.

## Order of packages

1. This plan, then two reviews.
2. The split package: step Beads and holders, then two reviews, then applied.
3. The image tool (`intake_template.py` generalised), then two reviews.
4. The C1 window, then two reviews, then run.
5. Image 1.
6. The X window, then two reviews, then run.
7. Image 2.
8. The C2 window, then two reviews, then run.
9. The intake, signing and delivery.
10. Terminal evidence on gct-oak5.

Codex quota for X is re-checked immediately before X's ROUTE. If it is short, that is the standing stop condition.

## Open items for review

- Whether ROUTE should stamp `gc.check_path` on the Template Claude step Beads. The P12 profile check path is the Operations candidate's, under the same gc pack import. The first live proof is C1's start.
- Whether the Claude lane writes runtime files into the worktree, as codex writes `.codex/hooks.json`. The read-only inventory at the image tool's review decides `RUNTIME`.
- The C2 brief's test command. It uses the Template's own test runner, sandboxed, and must not need network.
