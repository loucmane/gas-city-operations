# R4 brief r13: a readable split, plus the pre-window clarifications

This package prepares the ga-fsfg R4 candidate brief (dispatch and evidence-write) for its window.
`split_r4.py` renders the three Bead texts. `test_split_r4.py` (5 tests) proves:
- the split is verbatim;
- every part is readable inline;
- the pointer uses the exempt bd path;
- every r12 review item is answered;
- clarification 9 matches the recorded ga-x7lx deltas.

## Why

**The size.** `bd show ga-4xg9 --json` is about 39.6K characters: the 21.7K description, 1.3K of notes, and
the embedded related ga-fsfg record. That is over the candidate's inline read limit, which is exactly how the
first R3 attempt (ga-sh3w) failed. For R3 the operator chose, on 2026-09-26, a short task Bead plus closed spec
holders, with no dependency edge. R4 uses the same shape:
- **task:** the r12 head (role, goal, where the mechanisms live), the pointer, the r13 clarifications and the
  r12 working rules;
- **spec part 1:** the `dispatch` section;
- **spec part 2:** the `evidence-write` section and the acceptance list.

**The notes.** The notes on ga-4xg9 require that, before the R4 window, the r12 review items are resolved in the
brief with their own two reviews. The ga-4z38 route and claim observations must also be compared with the
brief's accepted deltas. `CLARIFICATIONS` in `split_r4.py` does both.
- **Items 1 to 8** answer the should_fix items of the two r12 reviews of `2067a406`:
  - the `request()` sites;
  - the wording for a pending dispatch;
  - the `bd ready` output cap;
  - the Bash timeout;
  - the `COMMANDS` set and `_profile` errors;
  - the stuck-state note;
  - the reconcile wording;
  - the residual double route.
- **Item 1 reflects R3 as merged** (Operations PR 392, `72c888e3`). The `pretool.py` site is None-safe. The
  `tracking.py` site sends every request-less target to the delivery recorder, so evidence-write needs its own
  branch there.
- **Item 9 corrects the accepted claim delta.** The ga-4z38 worker never claimed, so the first live claim was
  ga-x7lx, on 2026-09-26. Besides `status`, `assignee` and `updated_at`, a claim sets `started_at`,
  `gc.session_id`, `gc.session_name` and `gc.work_branch`. The route delta matched the brief.

## Run order

1. Two reviews of this package.
2. After R3 is merged, create the task and spec Beads:
   - create the spec holders, render with their ids, then create the task Bead;
   - close the holders;
   - measure every view.
3. Generate the R4 successor window from the ga-x7lx package at the post-merge `main`, with the same cache
   disposition class. That class needs the operator's approval, since each window's value is new drift.
4. ga-4xg9 stays open as the umbrella until R4 is delivered, then it is closed and superseded.
