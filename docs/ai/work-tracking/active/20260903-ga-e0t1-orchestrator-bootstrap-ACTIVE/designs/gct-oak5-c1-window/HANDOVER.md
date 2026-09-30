# gct-oak5 C1 window: handover checkpoint (2026-09-27)

## State at handover
- The C1 design **d10** is at the commit that adds this file; its parent `4c165590` is d10 itself. Nothing live has
  changed since the image tool r2 was accepted (`30573fb5`): no window has run, no job is queued, no Bead write is
  pending, and the worktree is clean.
- **d10 has not been reviewed yet.** d9 (`492be80c`) got review A SOURCE_PASS and review B HOLD. d10 answers B's
  two must_fix items and every should_fix from both reviews. See `DESIGN.md` §17.
- The next-job rule is code: `slots/slots.py` with `slots/test_slots.py` (18 tests). Run them with
  `/usr/bin/python3.12 -B -m pytest -q -p no:cacheprovider --basetemp=<scratch> test_slots.py` from `slots/`.

## Next steps, in order
1. Two independent aegis-reviewer runs on the d10 commit. Each prompt has `candidate=<sha>` on line 1 and asks for
   `SOURCE_PASS <sha>` or `HOLD <sha>` on line 1. HOLD only for code, safety or live-state defects. Reviewer
   disagreement is HOLD.
2. On a double pass, generate the C1 package (s1). Derive it from the gct-e8ex window s5 (`1df3d47e`), retargeted
   per `DESIGN.md`. Include image tool r3 (§7) and the s1 pins the design names:
   - Core child shapes;
   - the lane sandbox AF_UNIX denial;
   - the tmux hooks baseline;
   - the pane chain;
   - the respawn and double-fork evidence;
   - the RESTORE phase timeouts;
   - the queued-nudge dedup;
   - the task-attempt block;
   - the lane scope placement.
   The package gets tests and two reviews. The reviewers' remaining should_fix items are listed in the d9 hand-backs
   summarised in §17.
3. Jobs: WORKTREE, then PREP.
4. s2: pin the PREP values. This step needs **the operator's approval of this window's one-field cache disposition**;
   ask the user.
5. The C1 window, then H1. After that: X (check the Codex quota first), H2, C2, intake, retire, M13, then step 5's
   terminal evidence.

## Standing constraints (see memory and CLAUDE.md)
- Gas City workers implement. Only aegis-reviewer subagents review, and there are no native worker agents.
- Never run `sed -i` or `rm -rf`.
- Commits and PRs carry no co-author or session lines. Signed commits only.
- `GIT_OPTIONAL_LOCKS=0` on gc and bd calls; `--no-optional-locks` on read-only git.
- One literal command per workflow.py call, with no semicolons, parentheses, paths or HH:MM in `--text`.
- From PREFLIGHT to TERMINAL: no workflow.py, Bead writes or unguarded gc. No coordinator git in Template worktrees
  before intake. No operator tmux pane on any socket from PREP to TERMINAL.
