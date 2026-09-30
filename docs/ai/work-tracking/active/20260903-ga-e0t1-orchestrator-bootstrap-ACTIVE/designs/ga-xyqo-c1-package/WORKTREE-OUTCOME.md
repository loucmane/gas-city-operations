# ga-xyqo WORKTREE PASS

Completed once on 2026-09-29 at 21:08:58 CEST through the approved persistent
jobrunner. Signed candidate 4af58e77d44686bbb9472c42654bea13833559b8 received
SOURCE_PASS from two independent read-only Astra aegis-reviewers before the job.
Both native review envelopes were exported and filed through the supported
admission path. No wrapper was executed from the coordinator shell.

Native reviewer IDs:

- 01a0ee8e-6524-7121-a163-82b2e6f352d9, request SHA-256
  cf86c832b48a937d42211e906755fc7c1444a89712632b882d9cc2af28e9111d
- 01a0ee8e-87bf-7940-bd50-81d5bee8f1ac, request SHA-256
  9cab28d6725e44197fb0cc7601e19580afa1430fe9afaa9010d0cdbe7842cfcc

Both had no must-fix findings. Reviewer A accurately noted that the wrapper is
committed 0644 whereas the predecessor was 0755, so the earlier prose claim of
unchanged mode was too broad. This is nonblocking: the runner explicitly invokes
the wrapper through /bin/sh. Executable content and effective behavior are only
identity and digest rebound. The wrapper mode is not claimed byte-identical.

## Exact execution evidence

- Job ga-xyqo-worktree-r1: admitted, exit zero, unit inactive afterward.
- Result /var/tmp/ga-xyqo-worktree-20260929-r1/result.json SHA-256
  7258fd9a9c4b781fd26e770d0294d8bc89279d28a7f7d5ce21c013028d17c58c
- Runner final record SHA-256
  ec85b2a3cf82208afe9e86936e536519627ca8a7e14934a448a5abc6374fe3d4
- New HALTED SHA-256
  61b61ddc763be7455691d5e3e29b5d358c6d6d8c89b819401378c60e1ab2ce9a
- Wrapper log: /home/loucmane/.local/share/gas-city-staging/ga-xyqo-c1-package/worktree-20260929T190856Z.txt

The fresh candidate workspace is clean at exact signed base
801a5a9d5b0d72f665c949a86573357f02c9f1ac on codex/ga-xyqo-c1-package.
Two exact local rules were installed with existing confinement; global rules and
managed binaries were verified unchanged. No worker, claim, route, rig
transition or product activation occurred. ga-xyqo remains open and unassigned;
the preparation PASS note was appended through supported Beads and read back.

The previous completed terminal latch was preserved through no-replace archival
as HALTED.ga-rq5n-terminal-r2.before-ga-xyqo-worktree after exact latch, terminal,
runner final record, inactive unit and clean-candidate checks. Its SHA-256 remains
f8657f977b4fbcbe478aeb1f7755f5d7994f4a9bd62f283de8db9f9b2bfc416b.
No previous operation was repeated or evidence removed.

Next is fresh uninstalled PREP with exact historical permission preservation,
completed-workspace and terminal bindings, followed by independent package
review. Then the full worker window requires new reviewed bindings to the
corrected release transport. Standing authorization covers those steps. This
PASS is preparation only, not worker delivery, C1 acceptance or handover.
