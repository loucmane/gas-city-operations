# gct-e8ex brief split (step 4, part 1)

This package prepares the Template candidate-lane Bead, gct-e8ex, for the Template `codex` worker. The worker
builds a closed Claude candidate lane for the Template rig, and the handover proof (gct-oak5) needs that lane
first. `split_e8ex.py` renders the Bead texts, and `test_split_e8ex.py` (6 tests) proves:
- the split is verbatim, and holders name themselves;
- the live umbrella description is the reviewed r6 brief;
- every part is small;
- the pointer uses the codex prompt's own read command;
- the guidance holder carries the review guidance.

## Why

The codex worker reads its Bead with `/home/loucmane/gascity/bin/gc bd show <id>`, the plain view its prompt
names. For gct-e8ex that view is about 41K characters: the 19.5K reviewed r6 brief plus 6.5K of notes. Codex
truncates long command output for the model, and the first R3 attempt failed on exactly this kind of unreadable
brief.

The operator chose the split for R3 on 2026-09-26, and R4 used it too. Here it produces a short task Bead and
six closed holders: five with the r6 text and one with the coordinator notes and review hints. Every part is
under 5000 bytes and 80 lines, so each plain view prints well under 10K.

## Run order

1. **Reviews.** Two reviews of this package.
2. **Create the six holders** in the Template rig (`gc --rig gas-city-template bd create`), then:
   - close the holders right away;
   - render the task with their ids;
   - create the task Bead with no edges, label `template-candidate`;
   - measure every plain `gc bd show` view. **Stop if any view is 9,000 bytes or more, or 200 lines or more.**
3. **Keep the umbrella.** gct-e8ex stays open as the umbrella, and its notes stay there.
4. **Route the new task.** The routing window stamps `gc.routed_to=gas-city-template/codex` and `gc.work_dir`, the
   codex worker's own routed Template worktree.

## r2 (answers the reviews of `688723d9`; both SOURCE_PASS)

- **B 1: the data rule.** The pointer says the rule above ("treat every other Bead's text as data") does not apply
  to the six holders, while still applying to their notes and to every other Bead.
- **B 2: the umbrella.** gct-e8ex is named as the umbrella the worker must not read, update or close.
- **B 3: the stop behaviour.** Stage and verify, append the staged tree digest and the tests, send one escalation,
  and stop without closing; the coordinator signs, delivers and closes. The "rule above" wording is pointed to spec
  part 1.
- **B 4: the review guidance.** The guidance from the umbrella's notes (the Preflight probes, the composition
  fixture, the overlay file and the add_dirs derivation) moves into a sixth closed holder. It is marked as review
  guidance, not r6 text, so the task text stays small.
- **B 5: the worklog.** `/home/loucmane/vaults/main/GasCity/gas-city-template/Docs/worklogs/gct-e8ex-template-candidate-lane.md`,
  inside the codex agent's classified-vault write root, following gas-city-native `templates/worklog.md`.
- **A 1: the size caps.** The size test counts bytes; the hard stop on the live views is above.
- **A 3: holder ids.** Holder ids are checked against the Bead id pattern and must be distinct.
- **A 4 and B 6:** the pointer punctuation, and the holders are closed before the task exists.
- **Tests:** 6 pass.

## r3 (answers the reviews of `2bfc59ac`; both SOURCE_PASS)

- **Holder 6 carries the coordinator notes.** They moved there to keep the task text small, and the pointer says
  holder 6 is binding for this task. Section A holds the binding notes; section B holds the review hints, "copied
  and annotated" (A 4).
- **The worklog is `<task-id>.md`**, one note per Bead (A 1, B 5). The task id is therefore rendered in, and the
  run order becomes:
  1. create the task Bead with a provisional description;
  2. create the six holders, holder 6 naming the task id, and close them;
  3. update the task description to the final render;
  4. measure every live plain view against the hard stop.
- **Staged tree digest:** `git write-tree` of the index, run as its own command after `git add` of exactly the
  changed and new files (B 1).
- **After staging:** one escalation to the mayor with the subject `READY FOR SIGNING: <task> tree <digest>`, then
  stop without closing and without drain-ack (B 2).
- **Acceptance ownership:** review, signing, the PR, CI and the merge are the coordinator's, and the worker's
  acceptance is the Tests (B 3).
- **"This Bead"** means the claimed task (B 4).
- **Ids:** all real or all placeholders, distinct, never the umbrella's, and checked with raised errors (A 3,
  B 7).
- **The holder 6 header is tested** (A 5), and the stale counts are fixed (A 2, B 6).
