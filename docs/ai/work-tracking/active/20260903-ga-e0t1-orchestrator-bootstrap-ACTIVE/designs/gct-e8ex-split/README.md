# gct-e8ex brief split (step 4, part 1)

This package prepares the Template candidate-lane Bead, gct-e8ex, for the Template `codex` worker. The worker
builds a closed Claude candidate lane for the Template rig, and the handover proof (gct-oak5) needs that lane
first. `split_e8ex.py` renders the Bead texts, and `test_split_e8ex.py` (5 tests) proves:
- the split is verbatim;
- the live umbrella description is the reviewed r6 brief;
- every part is small;
- the pointer uses the codex prompt's own read command.

## Why

The codex worker reads its Bead with `/home/loucmane/gascity/bin/gc bd show <id>`, the plain view its prompt
names. For gct-e8ex that view is about 41K characters: the 19.5K reviewed r6 brief plus 6.5K of notes. Codex
truncates long command output for the model, and the first R3 attempt failed on exactly this kind of unreadable
brief.

The operator chose the split for R3 on 2026-09-26, and R4 used it too. Here it produces a short task Bead and
five closed spec holders. Every part is under 5K characters and 60 lines, so each plain view prints well under
10K.

## Run order

1. **Reviews.** Two reviews of this package.
2. **Create the spec holders** in the Template rig (`gc --rig gas-city-template bd create`), then:
   - render the task with their ids;
   - create the task Bead with no edges, label `template-candidate`;
   - close the holders;
   - measure every plain view.
3. **Keep the umbrella.** gct-e8ex stays open as the umbrella, and its notes stay there: the coordinator
   activation checklist and the review guidance.
4. **Route the new task.** It goes to `gas-city-template/codex` through a reviewed Template window.
