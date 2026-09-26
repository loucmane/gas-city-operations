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
- **Item 1 reflects R3 as it stands under merge** (Operations PR 392, head `72c888e3`; `main` is still
  `040139d8`). The `pretool.py` site is None-safe. The `tracking.py` site sends every request-less target to the
  delivery recorder, so evidence-write needs its own branch there. The degraded fallback also needs an
  evidence-write hard block.
- **Item 9 corrects the accepted claim delta.** The ga-4z38 worker never claimed, so the first live claim was
  ga-x7lx, on 2026-09-26. Besides `status`, `assignee` and `updated_at`, a claim sets `started_at`,
  `gc.session_id`, `gc.session_name` and `gc.work_branch`. The route delta matched the brief.

## r14 (answers both reviews of `b080cb47`, both SOURCE_PASS)

- **Item 9** now names the acceptance bullet it amends. It says the observation was made on a window-prepared
  Bead, and that any other key on a real dispatch child leaves the record pending, with the first live dispatch
  watched.
- **Spec holders:** the header says the task's clarifications amend the text and win.
- **Item 4:**
  - it counts five timed gc calls, including the readback, and notes the untimed ownership reads;
  - it defers to item 8's residual.
- **Item 5:**
  - it covers any exception from `_profile()`, including `OSError`;
  - it derives the canonical root from the runtime it runs from and checks it against `canonical_root`.
- **Item 3:**
  - it names the reverse-dependency read;
  - it adds 1 MiB caps on the `bd show`, `agent list` and sling outputs.
- **Item 1:**
  - it asks the worker to confirm against its base;
  - it adds the degraded-fallback hard block.
- **Pinning:** the r12 digest is pinned in full.
- **Tests:** 6 pass. The delta test is evidence-bound, because it reads the ga-x7lx window roots under
  `/var/tmp`.

## Run order

1. Two reviews of this package.
2. After R3 is merged:
   - Re-check item 1 against the merged `tracking.py` and `pretool.py`.
   - Create the task and spec Beads:
     - create the spec holders, render with their ids, then create the task Bead;
     - no edge of any kind to ga-4xg9 or ga-fsfg, since bd 1.2.2 keeps children of a blocked parent out of
       `bd ready`, and any edge embeds the other record;
     - close the holders;
     - measure every view.
3. Generate the R4 successor window from the ga-x7lx package at the post-merge `main`, with the same cache
   disposition class. That class needs the operator's approval, since each window's value is new drift.
4. ga-4xg9 stays open as the umbrella until R4 is delivered, then it is closed and superseded.
