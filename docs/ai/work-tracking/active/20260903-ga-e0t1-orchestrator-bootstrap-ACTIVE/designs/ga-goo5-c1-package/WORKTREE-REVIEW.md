# ga-goo5 preparation-only WORKTREE review

Review only this signed candidate and operator/WORKTREE.sh. No other live action
is admitted. The predecessor worktree.py is digest
cdc478ec200218f58aeb3bc66e7e7d8762b625abb6c0fff972e46e535aa31d22.
The new executor changes only ga-5uc9 to ga-goo5 in task-owned identities.
The signed source base, managed provider, global rules, local deny-only policies,
ownership/path checks, non-replay and failure preservation are unchanged.

The wrapper is mechanically rebound from predecessor digest
fe239942848a4d7d50ef63d6c1b64f02c494435f1486394fca8d9710c2c2549a
with only task identity and resulting executor digest changed.
The halt helper admits only the successful ga-5uc9-terminal-r1 receipt at
f43f07d716aff5d937dff4f10db1cbd1fa13e4d5. It retains signed clean-candidate proof,
inactive service, halted runner, exact receipt and no-clobber archival checks.

Review acceptance:
1. Exact unchanged executable behavior except new task-owned paths and wrapper hash.
2. The real terminal predecessor is bound, never the failed release job.
3. Create-only workspace/rules, no global policy writes or product edits.
4. Standalone open task and informational relation; genuine blockers remain.
5. Tests prove exact rebinding, namespace-independent safety and no lifecycle.
6. No production job may run before two independent SOURCE_PASS verdicts.
