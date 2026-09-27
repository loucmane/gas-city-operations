# gct-oak5 prerequisite: the Template-candidate codex worklog choice (A2)

## Operator decision (2026-09-27, about 12:35 CEST)

The operator chose "New codex choice". The gct-oak5 handover runs C1 (Claude), X (Template codex) and C2 (Claude) in one worktree, but no live worktree root is writable by both lanes:
- The Claude candidate lane edits only under `/home/loucmane/gas-city-template-candidate-worktrees`.
- The Template codex lane writes only under `/home/loucmane/gas-city-template-worktrees`.

The fix is one new codex `worklog_access` choice whose roots are the GasCity vault and the Template candidate root, with no Git metadata. It is activated by a reviewed package, then an M12 metadata successor and a P13 receipt revision refresh. Each stage needs two independent reviews.

The operator also chose to adapt the acceptance:
- the handover images cover HEAD, unstaged and untracked work, and Bead evidence;
- staged work is recorded as not provable under the no-`.git`-write lanes;
- after C2, the coordinator's reviewed intake signs.

## The change (exactly two city.toml edits)

1. **The choice.** Directly after `classified-vault-and-template-worktrees` (the choice the gct-mbg6 window used), this block is inserted:
   ```toml
   [[providers.codex.options_schema.choices]]
   value = "classified-vault-and-template-candidate-worktrees"
   label = "Classified GasCity vault and Template candidate worktrees"
   flag_args = ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.writable_roots=[\"/home/loucmane/vaults/main/GasCity\",\"/home/loucmane/gas-city-template-candidate-worktrees\"]"]
   ```
2. **The codex `work_dir_roots` patch.** The Template codex patch becomes `["/home/loucmane/gas-city-template-worktrees", "/home/loucmane/gas-city-template-candidate-worktrees"]`. Without it, the ga-6umo `work_dir` guard refuses a task worktree under the candidate root.

`new_city` asserts the change at the TOML level:
- the choice list is the predecessor with exactly one insert;
- the codex provider is otherwise unchanged;
- the option header and its default `classified-vault` are unchanged;
- every other provider, agent patch, patch table, rig and top-level table is unchanged.

The codex agent default stays `classified-vault-template-worktrees-and-git-metadata`, so nothing selects the new choice until a reviewed window does.

City.toml `b0eeb168` (the r1 city step, adopted by M11) becomes `bdcec254`. The pins are `cb52e986`.

## Executor

`activate_codex.py` has three steps: `inputs`, `city` and `reload`, with `resume city|reload` and `rollback`. Its discipline is the reviewed r1 `activate.py`'s:
- a quiet city before and after each step (no running agent or session, every rig suspended);
- one intent before one change, and one exclusive record;
- after an intent, only `resume`;
- `city` first validates a throwaway shadow city (`gc config show --validate`, plus the composed codex agent);
- `reload` requires an applied or `no_change` synchronous acknowledgement, the composed codex agent with both roots, its unchanged default and cap 1, and the live choice with exactly its flag_args.

`rollback` does four things:
- restores city.toml from the digest-verified backup, only if the live file is exactly the reviewed postimage;
- reloads;
- proves that the codex agent is back on its predecessor roots;
- proves that the choice is gone.

It imports the r1 `activate.py` helpers. The pins include the digests of `activate_codex.py`, `activate.py`, `preroute.py` and `candidate_git.py`.

## Evidence (2026-09-27, read-only)

- **Dry run.** A staging shadow at `~/.local/share/gas-city-staging/gct-oak5-codex-dry` holds the postimage city.toml and symlinks for everything else. On it, `gc config show --validate` reports "Config valid." The composed Template codex agent is:
  - provider codex;
  - OptionDefaults `{worklog_access: classified-vault-template-worktrees-and-git-metadata}`;
  - WorkDirRoots `[gas-city-template-worktrees, gas-city-template-candidate-worktrees]`;
  - MaxActiveSessions 1.
- **Tests.** `test_activate_codex.py` passes 14 tests:
  - the pinned postimage;
  - exactly the two edits (line multiset);
  - a new choice without Git metadata, and the default unchanged;
  - predecessor refusals, including an unrelated drift caught by the pin;
  - a non-idempotent `new_city`;
  - the step order, intent guard and resume guard;
  - apply then rollback, and rollback refusing a foreign city.toml;
  - quiet-drift refusal.

  The r1 `test_activate.py` still passes 35.

## Run order

Each step runs once, as `python3 -I -B <pkg>/activate_codex.py <pkg> <pins-sha256> <step>` from a real terminal, in the order `inputs`, `city`, `reload`. This comes after two SOURCE_PASS reviews. Stop on any refusal or drift.

## After A2

- **M12.** M12 adopts city.toml `bdcec254`. It is the M11 pattern, with city.toml as the only moved input, and it is its own reviewed package.
- **P13.** P13 re-pins the receipt `permission_revision` to the revision the controller traces after `reload`. It is the P12 pattern with one leaf.
- **No worker launches from `city` until P13.** The receipt revision mismatch makes Core's start preflight refuse, so this fails closed.
- **The handover window package.** It selects the new choice for the X segment only.
