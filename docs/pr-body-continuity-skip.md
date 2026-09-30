## Summary

Continuity capture read every `*.json` in `.git/gas-city-workflow/transactions` as a journal. Context recovery keeps
two other kinds of file there:
- its plan, `<child>.context-recovery.json`, which has no `spec`;
- pre-recovery backups, `*.before.json`. The attachment reconcile writes the same kind of backup.

On the live `gascity` rig, `ga-tmgr.context-recovery.json` made every Obsidian reconcile cycle fail with
"workflow transaction has no spec". The backups would also have been listed as duplicate journals.

Commit `4ecdf243` makes `_transactions` read only `<bead>.json` journals. Bead ids only ever take `.<digits>`
after a dot, so no real journal name can end in the skipped suffixes.

## Verification

- The new test `test_transactions_skip_context_recovery_plans_and_backups` failed red first. The continuity
  module now passes 45 of 45.
- Against the live rig, the scanner returns only `ga-ecwh` and `ga-tmgr`.
- One aegis-reviewer SOURCE_PASS, with no must_fix items. Follow-ups:
  - report context-recovery plans whose state is not `completed`;
  - mention attachment backups in the code comment;
  - add a fail-closed test for a spec-less `<bead>.json`.

This PR also carries the ga-e0t1 tracking evidence for the day.
