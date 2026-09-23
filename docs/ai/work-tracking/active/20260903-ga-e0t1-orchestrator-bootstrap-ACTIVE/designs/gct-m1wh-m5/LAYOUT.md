# M5 metadata successor: layout proof and activation plan

Bead `ga-0t04` (Operations) for Template Bead `gct-m1wh`, together with the Opus 5.5 scope of
`gct-er3h`. Target: Template main `28539934fa742056e0a65710d5638ff559a21175`
(PR 69 merge; tree `cfe24ca7`, equal to the reviewed branch head `0db4d800`).

## Operator decisions (2026-09-23, recorded on gct-m1wh)

- The layout is **V1**:
  - a fresh, clean Template authority worktree;
  - the `python3.12/test` pins dropped, a narrowing the operator accepts.
- The upgrade of the shared Claude Code CLI to 2.1.280 is accepted for every role. The Fable
  roles stay unprobed.
- The m1wh and er3h activations are combined. The canonical checkout advance to `28539934`
  carries both.
- Once two independent reviewers pass this layout proof, the coordinator may run the live
  sequence below without asking again. It stops at the first refusal or at anything unexpected.

## Why M3 refused, and what M5 changes

The confined writer W mounts only declared inputs, trees and links. M3 declared the canonical
checkout as the Template authority but mounted only `.git` plus 5 of its 258 tracked files. Inside
W, `git status` therefore saw 253 tracked paths deleted, and the result was
`repositories[template-pr67-authority].clean expected true, actual false`. The untracked
`deploy/` and egg-info directories were never mounted and were not the cause.

M5 names a **fresh linked worktree** as the authority:

- path: `/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority`;
- detached at `28539934`;
- declared with complete explicit coverage of all 277 tracked paths.

The canonical checkout stays the executed worker path. It is not a repository entry, so its
untracked user data is left alone and never needs to be clean.

## Complete authority coverage

The layout follows the rule from `LAYOUT-DECISION.md`: maximal link-free subtrees, individual
regular files, and explicit links.

| Kind | Count | Members |
| --- | --- | --- |
| Inputs | 12 | 7 root files, 3 `plans/*.md`, `sessions/state.json`, and the `.git` pointer file |
| Trees | 20 | 19 root directories plus `sessions/2026` (mode 0755) |
| Links | 2 | `plans/current`, `sessions/current` |

- Input digests are the SHA-256 of the Git blob content. `.gitattributes` has no eol or filter
  conversion.
- The `.git` pointer file content is `gitdir: <template>/.git/worktrees/gct-m1wh-pr69-authority\n`.
- No tree contains a link.
- Both link targets resolve to covered regular files:
  - one is a `plans` input;
  - the other lies inside the `sessions/2026` tree.
- The worktree admin directory lies inside the already-pinned Template `.git` tree.

`test_authority_coverage_is_complete_and_exact` proves from Git objects that every tracked path is
covered exactly once.

## Frame

The frame is measured with the reviewed `build_manifest.frame_bound`, the maximal-binding upper
bound against 131,072 bytes. Placeholder digests have the real fixed length. Host, parent and
version fields are the same length as the real values, give or take a few digits.

| Manifest | Upper bound (bytes) | Spare (bytes) |
| --- | --- | --- |
| R9 installed | 130,177 | 895 |
| M3 (refused) | 130,420 | 652 |
| M5 without dropping the test pins | 136,985 | **−5,913** |
| **M5 (this package)** | **128,071** | **3,001** |

The lossless `reports/r5/i` compaction was measured at about 4 KB more spare. It is **not used**,
for three reasons:

- it would put the managed-file backups `r5/i/00` (city-config) and `r5/i/15` inside a tree;
- it depends on unverified bwrap stacking of the retained `r5/i/20` setup input;
- M5 fits without it.

## Complete old-to-new pin map

The builder computes this map, and `test_exact_coverage_map` fixes every entry of it.

- **Inputs, removed (57):** all of `/usr/lib/python3.12/test/**`, as the operator decided. The
  worker's traced `--version` closure loads 63 stdlib files, none of them under `test/`. The
  external quiet-window closure still observes these 57 files during the transaction, because
  they remain in the carried-forward baseline pins. After apply, the platform no longer verifies
  them.
- **Inputs, re-pinned (4):** the predecessor digest must match exactly, and the successor digest
  is a reviewed constant.

  | Path | R9 digest | M5 digest | Source of the M5 digest |
  | --- | --- | --- | --- |
  | `gas-city-template/lib/gct_claude_signing_worker.py` | `bac4df82` | `4e28d5b8` | Git blob at `28539934` (`MODEL = "claude-opus-5-5"`) |
  | `gascity/bin/claude` | `26d02035` | `1e08503d` | staged 2.1.280 bytes |
  | `gascity/city/city.toml` | `6594ee77` | `4f7e170f` | exact 6-line edit of the R9 backup `r5/i/00` |
  | `gascity/city/managed/rig-permissions.toml` | `c7c11b8a` | `a5ff5a58` | line 95 → `opus-5-5`, the reviewed 28539934 renderer output at the canonical path |

- **Inputs, added (14):**
  - the `gc-b` Core backup, as in M3;
  - the new city-config source `reports/m5-inputs/city.toml` (`4f7e170f`, mode 0644);
  - the 12 authority inputs.
- **Trees, re-pinned from the frozen capture (2):**
  - the Template `.git`, changed by the fetch of `28539934`, the checkout advance and the new
    worktree admin directory;
  - `reports/r5/r`, whose index was rewritten on 2026-09-23 01:39 with HEAD `7e354226`
    unchanged. That authority is still clean.

  The builder refuses if either digest is unchanged.
- **Trees, added (20):** the authority trees. Their digests come only from the frozen capture.
- **Links, added (2):** the authority links.
- **Repositories, added (1):** `template-pr69-authority` at `28539934`. All six historical
  authorities are retained.
- **Providers:**
  - `claude-native`: `26d02035` / `2.1.263` → `1e08503d` / `2.1.280 (Claude Code)`;
  - `claude` (signing wrapper) version: `dependencies_sha256` `b7fee446` → `f36deb20`. The
    derivation method reproduces the reviewed M3 value `8b8b3f76` first.
- **Integrity files:** `rig-permissions.toml` `c7c11b8a` → `a5ff5a58`.
- **Managed file `city-config`:**
  - `sha256` → `4f7e170f`, and `source` → `reports/m5-inputs/city.toml`;
  - `previous_sha256` stays `6594ee77`, with the existing backup `r5/i/00` holding exactly those
    bytes.

  Core's metadata-only preflight therefore sees the file as already installed and reuses the
  backup, so there is no mutation (`installer.go` 468-492, `metadata_adopt.go` 61-84).
- **Scalars:**
  - successor identity, exactly as reviewed in M3;
  - `release_id`, `manifest_sha256`, transaction and attempt;
  - evidence, parents and preimages under the fresh root `reports/m5`.
- **Unchanged:** Core, runtime, writer, protected trees, absent entries, `cache_sha256`,
  `imports_sha256` and every other pin. `imports_sha256` does not change, because the city.toml
  edit touches only provider model values, not imports.

## Protection argument

- **Narrower (operator-approved):** the 57 test-suite pins listed above.
- **Equal:**
  - every other R9 pin is retained;
  - each changed pin moves to exact reviewed successor bytes and requires the exact predecessor;
  - the two re-pinned trees keep their tree semantics.
- **Stronger:**
  - W's clean check now sees the complete tracked authority, including its links;
  - after the provisioning receipt refresh, the dispatch gate can bind `template_commit` to a
    pinned, clean `28539934`;
  - the builder refuses any authority file, tree, link, backup or source whose bytes differ from
    the reviewed constants.

## Live sequence

Every step below must run as UID 1000 **in the supervisor host namespaces**. See the blocker
section.

1. **Preconditions:**
   - every rig is suspended;
   - there are zero sessions and no `city` tmux server;
   - the installed manifest is `a6324753` and the receipt `482b5daf`;
   - no other writer touches any Template worktree or `reports/r5/r` from here until restoration.
     This is the quiescent-window rule.
2. **Live prerequisites.** Run `python3 -I -B prereqs.py <step>` for each step, in order. Each
   step writes an exclusive record under `reports/m5-inputs`.
   - `inputs`: create the city-config source and a copy of the current rig-permissions file.
   - `cli`: back up to `bin/claude.gct-m1wh-before-2.1.280`, then atomically install 2.1.280.
     `--version` must print `2.1.280 (Claude Code)`.
   - `city`: atomically write the edited city.toml.
   - `checkout`: `git checkout --detach 28539934` in the canonical checkout, with hooks disabled
     and the untracked set unchanged.
   - `render`: `gct-managed-rig-permissions --apply` from the canonical 28539934 renderer. It must
     report conformant and `a5ff5a58`.
   - `authority`: `git worktree add --detach` for the authority, then prove it clean at HEAD
     `28539934` with every file, link and tree root checked.

   The render comes after the checkout advance. The renderer embeds its own root path, and only
   the 28539934 renderer emits `opus-5-5`. Between the checkout and render steps, the live
   signing worker would refuse the old `claude-opus-5` argv. Every rig is suspended, so nothing
   launches in that gap.
3. **Capture.** Run `capture.py audit`, then `complete`, `settle` and `freeze`. Each stage binds
   the previous stage's digest.
   - The audit refuses on any drift other than the two re-pinned trees.
   - `complete` carries forward every infrastructure pin of the M3 baseline and records each
     change.
   - `settle` warms cache access times with ordinary reads only, as the reviewed M1 settle did.
4. **Pin the baseline:**
   - set `BASELINE_SHA`;
   - run the tests, including a build against the real baseline;
   - write `source-pins.json` for the six launcher sources and commit.
5. **Transaction.** This is the unchanged reviewed M3 executor.
   1. `launch.py --expect-sources <inventory> prepare`. This starts the 15-minute window and
      pauses only the reconciler timer.
   2. Two SOURCE_PASS reviews.
   3. `pause`.
   4. `observe`: the native metadata-only dry-run.
   5. Two PAIRING_PASS reviews.
   6. `paired`: probes, then one apply.
   7. `verify`.
   8. Two COMMIT_PASS reviews.
   9. `restore-accepted`.

   Any refusal preserves the evidence and restores the timer. Nothing is replayed.
6. **Provisioning receipt refresh.** This is a separate reviewed package, because the receipt
   must name `28539934`.
7. **Canary:** run `gc platform canary`.

The Opus probe is reused, not repeated. The gct-er3h preflight ran on the byte-exact 2.1.280
binary and got `OK` from:

- `claude-opus-5-5`;
- `claude-haiku-4-5-20251001`;
- `claude-sonnet-5`.

After the city edit, no live role selects `claude-opus-5`. Fable is not probed.

## Rollback

`prereqs.py rollback` is allowed only while the installed manifest is still `a6324753`. It
restores, in reverse order:

1. rig-permissions, from its copy;
2. the canonical checkout to `51440da2`;
3. city.toml, from `r5/i/00`;
4. the CLI, from its backup.

It then proves every predecessor digest and the untracked set. The authority worktree is left in
place; it is clean and unreferenced. After apply, rollback is the native successor path only. It
is never a hand edit of the platform metadata.

## Blocker: executor namespaces

The reviewed `host_observation` requires the observer to share the supervisor's namespaces.
From the canonical Claude seat session, commands run in mount namespace `4026532229`, while the
supervisor (PID 3150812) runs in `4026532219`. The observation refuses with
`observer is not in supervisor host namespaces`, and running unsandboxed was refused by the
session's permission classifier.

The live prerequisites, the capture and the transaction therefore need an executor that runs in
the supervisor's namespaces. That can be the operator's host shell or a Gas City coordinator
session, as Codex ran R9 and M1 through M3. It must not be a weakened check.

## Dependencies outside this package

This package loads helpers from the following locations. Each one is digest-pinned at load time,
and each has a byte-identical durable copy under
`~/.local/share/gas-city-staging/{ga-mutg-20260920,gct-m1wh-metadata-20260922}`.

- The legacy recovery sources under the ga-e0t1 tracker `reports/`.
- The R9 helper chain:
  - `reports/ga-mutg-metadata-quiet-r9-20260920/manifest_candidate.py`;
  - `/tmp/ga-mutg-adoption-20260920-r{3,4,7}`;
  - `/tmp/ga-mutg-adoption-20260920`.
- The M3 baseline.

If `/tmp` is cleaned, restore those files byte-for-byte from the durable copies before running.
