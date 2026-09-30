## Summary

The ga-e0t1 coordinator journal reached 1,080,824 bytes, over the stationary gate's 1 MiB bound, so every
`workflow.py coordinate` write refused. Notes, create, depend and dispatch were all blocked. `compact-journal` returned
`unchanged` because it only moved coordination-record snapshots. The bulk is the inline before/after Bead pair
kept for every verified `external_ownership` record; ga-e0t1.19 alone holds 272 KB.

The fix is commit `3b644e8b`:
- `compact-journal` now also moves verified ownership `before`/`after` snapshots into the existing
  content-addressed store beside the journal, and reports `ownership_snapshots`.
- Pending ownership intents keep their inline preimage.
- The gate and every ownership check read only `state` and `binding`. The one direct comparison of an ownership
  snapshot, in context recovery, now resolves through `resolve_snapshot`. Attachment reconcile already did.
- Simulated on a copy of the live journal, compaction moves 28 snapshots and leaves about 501 KB.

This is a coordinator-fix exception granted by the operator on 2026-09-30. The bug blocks the Bead writes that
routing a worker would need.

## Other commits on this branch since main

- `b0944b5b` commits unchanged the tracking lines Codex appended at its 2026-09-30 handoff. They are evidence only.
- `863e2bfb` is a signed merge of `origin/main` (PR 394), which touches no file changed here.
- The branch's earlier commits are the signed ga-e0t1 design and work-tracking history, as in PRs 390 and 391.

## Verification

- A new regression test, `test_compact_journal_moves_verified_ownership_snapshots_and_coordination_still_works`,
  failed against the old code (`unchanged`) and passes now.
- `tests/meta_workflow_guard` and `tests/claude_adapter/test_stationary_orchestrator.py`: 2244 passed, 4 skipped.
- Two independent aegis-reviewer passes on `3b644e8b`: SOURCE_PASS and SOURCE_PASS, with no must_fix items.
  Their should_fix items are follow-ups: more reader tests, workflow-contract wording, and a snapshot directory
  lstat check.
