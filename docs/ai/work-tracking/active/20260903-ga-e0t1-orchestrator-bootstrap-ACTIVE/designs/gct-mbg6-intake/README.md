# gct-mbg6 Template intake

This package is the reviewed intake of the gct-mbg6 codex worker's change, from the gct-e8ex-window run order
step 6. The window ran as follows:
- s4 at `8398b685` / `4540e054` ran the worker, which set `READY FOR SIGNING: gct-mbg6 worktree`.
- s5 at `1df3d47e` restored the city. TERMINAL passed with full native integrity.
- The common snapshot after TERMINAL was unchanged (`437be143`).

## Contents

| Path | Role |
| --- | --- |
| `intake_template.py` | `export`, `tree` and `stage` (see its docstring) |
| `test_intake_template.py` | Fixture tests: round trip against plain `git add`, refusals, forbidden roots, nested ignore markers |
| `export/manifest.json` | Every exported path with status, mode, blob id, sha256 and size; deletions, excluded runtime entries, admitted nested ignore markers, ignored count and digest |
| `export/files/` | The exact exported bytes |
| `export/tree.json` | BASE, the reviewed tree id, the manifest digest and the diff digest |
| `export/review.diff` | `git diff BASE <tree>`, with no textconv and no external diff |
| `task-gct-mbg6.json` | The task view after CLOSE: the brief, acceptance and the worker's notes |

## Run record (2026-09-27)

**BASE clone.** `~/.local/share/gas-city-staging/gct-mbg6-intake/base.git` is a bare clone taken from GitHub with
`--no-local`. It has no alternates and no replace refs.

**Export.** It walked `/home/loucmane/gas-city-template-worktrees/gct-mbg6` without running git there.
- Manifest `3a75eaff2a48914bbff70c2e91d5b55d202c6929c3753fe9b1280520b52635e0`.
- 15 exported paths: 4 modified and 11 added. Nothing was deleted.
- 10 excluded runtime entries: the gc skills sink under `.agents/skills/` and the gc codex session hooks
  `.codex/hooks.json`.
- One admitted nested ignore marker, pytest's `.pytest_cache/.gitignore` (`*`).
- 57 ignored cache files.

**Tree.** The reviewed tree is `23b062479ed6f4cbb3c6c9093572fdcd1c6b4e86` (tree.json `2eb281c6…`).

**Coordinator error.** At 08:05Z the coordinator ran hardened, read-only `git status` and `git diff --stat` in the
worker's worktree. The window README forbids this before the intake has signed.
- It was harmless: a rerun of `common-snapshot-r1.py after` returned `437be143`, unchanged, and the cgroup city
  check was clean.
- It is recorded here and on ga-e0t1.
- The export does not depend on those reads.

## Signing and PR (2026-09-27)

**Signed commit.** Two independent SOURCE_PASS reviews of `a82f541a` are filed. `stage` in a fresh clone from
GitHub at BASE gave tree `23b06247`, equal to the reviewed tree. The signed commit is `37586267`: good signature,
key `2ECF4432C7E7982D`. It is pushed as `codex/gct-mbg6-template-candidate-lane`, and Template PR #72 is open.

**CI timeout.** The CI tests all passed (795 passed, 61 skipped in 9m29s). The job was still cancelled by its
10-minute `timeout-minutes`.

**Timeout fix.** The operator approved a coordinator fix on 2026-09-27: one signed commit on PR #72 that changes
only `timeout-minutes` from 10 to 20.
- It is `68ffb689` (tree `55d7a9df`), recorded as `ci-timeout.patch`, with both commits' identities in
  `ci-timeout-commits.txt`.
- Two reviews bind to the Operations commit that carries this record.

## Next

1. Two aegis-reviewer runs bind to the Operations commit that carries this package.
2. `stage` runs in a fresh standalone clone from GitHub at BASE, outside every codex write root. Its
   `write-tree` must equal `23b06247`.
3. A signed commit on `codex/gct-mbg6-template-candidate-lane` follows, then the push, the Template PR, CI and
   the merge. gct-mbg6 is closed after that.
