## Summary

This adds `docs/gas-city-operations-runbook.md`, the step 5 cold-start and recovery runbook. It is written from
the live 2026-09-30 provider handover proof on Bead gct-yt3e, which ran Claude, then Codex, then Claude on one
Bead and one worktree and was delivered as Template PR 73. It covers:

- the normal-operations Template configuration;
- the provisioning-receipt refresh after any `city.toml` change;
- running a task on a worker lane;
- the handover procedure;
- recovery.

It also includes the ga-e0t1 tracking evidence for the day and a signed merge of `origin/main` (PR 395).
