# M5 metadata successor: layout proof and activation plan (r3)

This package serves Bead `ga-0t04` (Operations) for Template Bead `gct-m1wh`, together with the
Opus 5.5 scope of `gct-er3h`.

- Target: Template main `28539934fa742056e0a65710d5638ff559a21175`, the PR 69 merge.
- Its tree `cfe24ca7` is identical to the reviewed branch head `0db4d800`.

Revision history:
- r2 answered the two HOLD reviews of r1 (`fb7f01cf`).
- r3 answers the two reviews of r2 (`c3a49e55`). The manifest-lens run returned SOURCE_PASS
  with should-fix items; the live-safety run returned HOLD.

The tables at the end map every finding of both rounds to its disposition.

## Operator decisions (2026-09-23, recorded on gct-m1wh)

- **Layout V1:**
  - a fresh, clean Template authority worktree;
  - the `python3.12/test` pins dropped, a narrowing the operator accepted.
- **Shared Claude Code CLI:** the upgrade to 2.1.280 is accepted for every role, and the Fable
  roles stay unprobed.
- **Combined activation:** m1wh and er3h activate together.
- **Live sequence:** once two independent reviewers pass the package, the live sequence runs
  without further asking and stops at the first refusal.
- **Executor:** the operator runs each live command from a terminal on the machine that shares the
  supervisor's namespaces. This session cannot reach those namespaces, and while the operator is
  connected remotely, `!` output does not reach the session. A read-only probe must succeed first.
- **Still needed:** an explicit operator acknowledgement of the libexpat re-pin. It is a
  distribution security update, not part of the 2026-09-23 decisions.

## Why M3 refused, and what M5 changes

The confined writer W mounts only declared inputs, trees and links. M3 declared the canonical
checkout as the Template authority but mounted only `.git` plus 5 of its 258 tracked files. Inside
W, `git status` therefore saw 253 tracked paths deleted, which produced
`repositories[template-pr67-authority].clean expected true, actual false`.

M5 instead names a **fresh linked worktree** as the authority:

- path: `/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority`;
- detached at `28539934`;
- with complete explicit coverage of all 277 tracked paths.

The canonical checkout stays the executed worker path. It is not a repository entry, so its
untracked `deploy/` and egg-info are left alone.

## Complete authority coverage

The authority is covered by maximal link-free subtrees, individual regular files and explicit
links.

| Kind | Count | Members |
| --- | --- | --- |
| Inputs | 12 | 7 root files, 3 `plans/*.md`, `sessions/state.json`, and the `.git` pointer file |
| Trees | 20 | 19 root directories plus `sessions/2026` (mode 0755) |
| Links | 2 | `plans/current`, `sessions/current` |

- Input digests are Git blob SHA-256s. `.gitattributes` has no eol or filter rule.
- No tree contains a link, and both link targets resolve to covered regular files.
- The worktree admin directory lies inside the already-pinned Template `.git` tree.
- `test_authority_coverage_is_complete_and_exact` proves from Git objects that every tracked path is
  covered exactly once. It also re-derives the inputs with `derive_expected.coverage()`.

## Frame

The frame is the reviewed `build_manifest.frame_bound`, a maximal-binding upper bound checked
against 131,072 bytes.

| Manifest | Upper bound (bytes) | Spare (bytes) |
| --- | --- | --- |
| R9 installed | 130,177 | 895 |
| M3 (refused) | 130,420 | 652 |
| M5 without dropping the test pins | 136,985 | −5,913 |
| **M5 r2** | **128,071** | **3,001** |

The real build enforces the limit, so a placeholder-length difference cannot slip through. The
lossless `r5/i` compaction is not used, for two reasons:

- it would put the managed-file backups `r5/i/00` and `r5/i/15` inside a tree;
- it relies on unverified bwrap stacking.

## Complete old-to-new pin map (`test_exact_coverage_map` fixes every entry)

- **Inputs, removed (57):** `/usr/lib/python3.12/test/**`. The external quiet-window closure still
  observes them through the carried-forward baseline pins. After apply, the platform no longer
  verifies them.
- **Inputs, re-pinned (6).** Each requires its exact predecessor.

  | Path | R9 | M5 | Source of the M5 bytes |
  | --- | --- | --- | --- |
  | `gas-city-template/lib/gct_claude_signing_worker.py` | `bac4df82` | `4e28d5b8` | Git blob at 28539934 (`MODEL = "claude-opus-5-5"`) |
  | `gascity/bin/claude` | `26d02035` | `1e08503d` | staged 2.1.280 bytes (the gct-er3h preflight) |
  | `gascity/city/city.toml` | `6594ee77` | `4f7e170f` | exact 6-line edit of the R9 backup `r5/i/00` |
  | `gascity/city/managed/rig-permissions.json` | `7fb9a741` | `d22cf4c1` | the registry synced to the 28539934 profiles: only the gascity claude toolchain digest and version change, and the blog rig is untouched |
  | `gascity/city/managed/rig-permissions.toml` | `c7c11b8a` | `cba75f87` | reviewed 28539934 renderer output for the synced registry: `registry_sha256`, the `managed-<digest>` choice name, and `model = "opus-5-5"` |
  | `/usr/lib/x86_64-linux-gnu/libexpat.so.1.9.1` | `c42ff317` | `ec6c12d3` | Ubuntu security update `libexpat1` 2.6.1-2ubuntu0.4 → 0.5 by `unattended-upgrade` at 2026-09-23 06:55:34 |

  - The render method is checked first. The same renderer reproduces the live `c7c11b8a` file
    from the live registry, apart from the model line.
  - For libexpat, `dpkg --verify` is clean and the MD5 `f0cbf5c6` equals the package record.
- **Inputs, added (14):**
  - the `gc-b` Core backup, as in M3;
  - the city-config source `reports/m5-inputs/city.toml` (`4f7e170f`, mode 0644);
  - the 12 authority inputs.
- **Inputs, retained and asserted:** four canonical Template files that 28539934 leaves
  byte-identical.
  - `bin/gct-claude-signing-worker` (`9df9ea34`), which is also the provider SHA;
  - `lib/gct_claude_subscription.py` (`3b92bc92`);
  - `templates/claude/signing-provider.toml` (`f820690b`);
  - `core-signing-control-policy.json` (`16022d04`).

  Each equals its blob at both `51440da2` and `28539934`.
- **Trees, re-pinned from the frozen capture (2):** `capture.py audit` bounds both against the
  reviewed M1 audit inventories, ignoring access times.
  - `reports/r5/r`: only `.git/index` may change.
  - Template `.git`:
    - may change only objects, refs, logs, worktree admin, LFS locks, workflow transactions,
      HEAD, index, FETCH_HEAD, ORIG_HEAD, COMMIT_EDITMSG and config;
    - its non-branch config must equal the reviewed set;
    - hooks, info and description must be unchanged.

  Today both are inside their bounds: `r5/r` shows 2 changed entries, and `.git` shows 83 changed
  and 92 added, none outside the allowed set.

  The cause is identified. At 2026-09-23 01:39, a plain `git status` without
  `--no-optional-locks`, run by the read-only M4 investigation, rewrote the `r5/r` index and five
  linked-worktree indexes inside the Template `.git`. HEAD did not change. Every git command the
  package runs at runtime (prereqs, capture, derivation) uses `--no-optional-locks`. The test
  files only read Git objects. The quiescent window forbids any other reader.

  Both bounds are anchored and asserted (`test_capture.py`):
  - the `r5/r` M1 baseline is the R9 pin `ad25084c`;
  - the Template `.git` M1 baseline is M3's reviewed `cbe4982a`.

  For the Template `.git`:
  - additions, changes and removals are allowed only in objects, refs, logs, worktree admin, LFS
    locks, rerere and workflow transactions, plus HEAD, index, FETCH_HEAD, ORIG_HEAD,
    COMMIT_EDITMSG and config;
  - no `config.worktree` may exist anywhere;
  - every config key except `branch.<name>.remote|merge` must equal the reviewed set exactly
    (`git config --list`).
- **Trees, added (20):** the authority trees, from the capture.
- **Links, added (2):** the authority links.
- **Repositories, added (1):** `template-pr69-authority` at 28539934. All six historical
  authorities are retained.
- **Providers:**
  - `claude-native`: `26d02035` / `2.1.263` → `1e08503d` / `2.1.280 (Claude Code)`;
  - `claude`: the version `dependencies_sha256` moves `b7fee446` → `f36deb20`. The same derivation
    first reproduces the reviewed M3 value `8b8b3f76`.
- **Integrity files:**
  - `rig-permissions.toml`: `c7c11b8a` → `cba75f87`;
  - `rig-permissions.json`: `7fb9a741` → `d22cf4c1`.
- **Managed file `city-config`:**
  - `sha256` → `4f7e170f`, and `source` moves from `r5/i/07`, which is asserted, to
    `reports/m5-inputs/city.toml`;
  - `previous_sha256` stays `6594ee77`, with the backup `r5/i/00` holding those bytes.

  Core then treats the file as already installed and reuses the backup, so there is no mutation
  (`installer.go` 468-492, `metadata_adopt.go` 61-84).
- **Scalars:**
  - successor identity, exactly as in M3;
  - `release_id`, `manifest_sha256`, transaction and attempt;
  - evidence, parents and preimages under `reports/m5`.
- **Unchanged:** Core, runtime, writer, protected trees, absent entries, `cache_sha256` and
  `imports_sha256`. Host and namespaces stay unchanged as long as the supervisor is not restarted;
  the builder copies the captured host, and every stage requires it to be stable.

## Protection argument

- **Narrower (operator-approved):** only the 57 test-suite pins.
- **Equal:** every other R9 pin. Six inputs and two trees move to exact reviewed successor bytes,
  and each requires its exact predecessor.
- **Stronger:**
  - W's clean check sees the complete tracked authority;
  - after the receipt refresh, the dispatch gate can bind `template_commit` to a pinned, clean
    28539934;
  - the builder refuses a wrong authority file, tree or link, and a wrong backup, source or
    retained Template byte. It also refuses an overlapping ancestor or descendant pin.

## Config validity during the live sequence

The supervisor reloads config on file change (`cmd/gc/controller.go` 727-806). When a load fails,
it logs "keeping old config" and continues without a restart (`cmd/gc/city_runtime.go` 1756-1778).

Load validation checks provider option defaults against their choices
(`internal/config/compose.go` 725 calls `resolved_cache.go` 28-119). Agent patch values are resolved only at session
launch, and every rig is suspended.

`gc config show --validate` is weak evidence. It accepts even a bogus agent model, and it accepts
the unordered state. The package therefore adds its own semantic check, `prereqs.models`: every
claude-family selection must name an offered model. Its scope:
- providers.claude defaults;
- city rig overrides;
- `[[patches.agent]]` in city.toml and in the rig fragment;
- every `agents/*/agent.toml` option default, resolving each provider through its `base` chain.

The two other included fragments select no model. The check is a pure function and is unit
tested: it refuses the unordered state and a probe agent that selects `opus-5`.
`validate_states.py` runs both checks on every state, and it runs only before the sequence,
because `gc` reads the pack cache:

| State | `gc` validate | Semantic check |
| --- | --- | --- |
| predecessor | accepted | accepted |
| after `city-transition` | accepted | accepted |
| after `render` | accepted | accepted |
| after `city-final` | accepted | accepted |
| unordered (final city + old fragment) | accepted | **refused** (`patches.agent.1: "opus-5"`) |

The live order therefore:

1. first adds the `opus-5-5` choice to city.toml;
2. then syncs the registry and renders the fragment, which selects `opus-5-5`;
3. last, removes `opus-5` and moves the defaults.

Every intermediate composed config offers every model it selects.
- Before writing, each city step checks the model consistency of both the current and the
  candidate city.toml.
- `city-final` also requires the fragment and registry to be at their successor digests.
- `render` requires the transitional city.toml.
- The check runs again after every config change.

## Live sequence

All steps run as UID 1000 in the supervisor namespaces, executed by the operator from a host
terminal. Before each command, verify that the package worktree is clean at the reviewed commit.
Pass the reviewed `manifest_candidate.py` SHA-256 to every `prereqs.py` and `capture.py` call.

**Reconciler quiet slot.** The Obsidian reconciler oneshot runs for about 8 s, about every 65 s,
from an enabled timer. Nothing may pause that timer outside the executor window. Each quiet check
therefore first waits, by natural drain only, until the oneshot is idle and the timer's next
elapse is at least 40 s away. The timer's `NextElapseUSecMonotonic` is read through `busctl`. The
bound is 180 s, and the timer is never started, stopped or signalled. `capture.py complete` waits
for the same slot before its scope check.

**Intent and resume.** Each step writes `prereq-<step>.intent.json` just before its mutation.
- If the step is interrupted afterwards (for example, a quiet check fails in `finish`), the same
  step refuses to run again.
- `prereqs.py <candidate> resume <step>` then proves the exact reviewed postcondition and a quiet
  host, and writes the missing record with `resumed: true`. It never repeats the mutation.
- If the postcondition does not hold, only `rollback` remains.
- A refusal before the intent is benign; nothing was changed.

1. **Preconditions.** `prereqs.py` checks these before and after every step:
   - supervisor identity through `host_observation`;
   - an empty supervisor scope and no city tmux server (`quiet_scope`);
   - suspension record `823e4e21`;
   - installed manifest `a6324753`;
   - no `reports/m5` root and no rollback record.

   The host must be the same before and after each step. No other writer may touch any Template
   worktree or `reports/r5/r` until restoration. Check `/var/log/apt/history.log` first: an
   unattended upgrade of a pinned library during the window refuses preservation. That is safe,
   but it consumes the attempt.
2. **Live prerequisites.** Run `prereqs.py <candidate> <step>` for each step, in order. Each step
   writes an exclusive record.
   1. `inputs`: derive and verify every byte before creating `reports/m5-inputs`, which holds:
      - the final and transitional city.toml;
      - the new registry;
      - backups of the registry and fragment.
   2. `cli`: back up to `bin/claude.gct-m1wh-before-2.1.280`, atomically install 2.1.280, then
      require `--version` to print `2.1.280 (Claude Code)`.
   3. `city-transition`: city.toml `6594ee77` → `8e148efa`, which adds the `opus-5-5` choice.
   4. `checkout`: before the checkout moves, the renderer, signing-worker and retained-pin
      digests are proved from the 28539934 Git objects. Then `git checkout --detach 28539934`
      runs with hooks off and no optional locks. The untracked set and every on-disk digest are
      asserted.
   5. `registry`: `7fb9a741` → `d22cf4c1`.
   6. `render`:
      - require the transitional city.toml and the synced registry;
      - run `--check` first; it must exit 4 and predict `cba75f87` from `c7c11b8a`, and nothing
        is written otherwise;
      - then run `--apply`.

      `--apply` stages a `.city.gct-validate.*` shadow beside the city, symlinks every other city
      entry into it, runs `gc config show --validate` against it, and removes it. That reads the
      pack cache, which is why the capture settles cache access times.
   7. `city-final`: `8e148efa` → `4f7e170f`.
   8. `authority`: `git worktree add --detach`. The worktree must be clean at 28539934, with
      every file, link and tree root proved and the exact root entry set.
3. **Capture.** Run `capture.py <candidate> audit`, then `complete`, then `settle`, then
   `freeze`. Each stage binds the previous stage's digest.
   - `audit` refuses on any file, tree, protected, repository, canonical, config, link, absent or
     host drift, and on any re-pinned tree change outside its bound.
   - `complete`:
     - requires a stable audit host;
     - carries forward every infrastructure pin of the M3 baseline;
     - refuses any carried-forward pin that changed other than the six reviewed inputs at their
       exact successor digests;
     - waits for the reconciler quiet slot before its scope check.
   - `settle` uses ordinary reads only.
4. **Pin the baseline:**
   - set `BASELINE_SHA`;
   - run the three test files; `test_build_against_frozen_baseline` builds from the real file;
   - write `source-pins.json`;
   - commit, and have the binding reviewed.
5. **Transaction.** This is the unchanged reviewed M3 executor.
   1. `launch.py prepare`. This starts the 15-minute window and pauses the reconciler timer.
   2. Two SOURCE_PASS reviews.
   3. `pause`.
   4. `observe`: the native metadata-only dry-run. This is also the first proof that 2.1.280
      `--version` runs inside W, and it fails closed if not.
   5. Two PAIRING_PASS reviews.
   6. `paired`.
   7. `verify`.
   8. Two COMMIT_PASS reviews.
   9. `restore-accepted`.

   Nothing is replayed.
6. **Provisioning receipt refresh.** This is a separate reviewed package naming 28539934. It reads
   the synced registry, so M5 already pins the registry and fragment it needs.
7. **Canary:** run `gc platform canary`.

The Opus probe is reused. The gct-er3h preflight on the byte-exact 2.1.280 answered `OK` for
`claude-opus-5-5`, `claude-haiku-4-5-20251001` and `claude-sonnet-5`. After the city edit, no live
role selects `claude-opus-5`. Fable is not probed.

## Rollback

`prereqs.py <candidate> rollback` runs only while all of the following hold:

- the installed manifest is `a6324753`;
- no M5 executor window is open: either `reports/m5` does not exist, or its `q/restored.json`
  records a completed timer restoration and no `commit-consumed.json` exists. The executor's own
  recovery restores only the reconciler timer; it never reverts the live prerequisites;
- no rollback has already run.

Rollback first verifies the digest of every backup it will need. It waits for the reconciler slot
and records the quiet-host result. That result is recorded but not required, so that restoration
stays possible. Rollback then restores, in an order that never composes the inverse unordered
state:

1. the transitional city.toml, if the final one is installed;
2. the fragment and the registry, from their `m5-inputs` copies;
3. the predecessor city.toml, from `r5/i/00`;
4. the CLI, from its backup;
5. the canonical checkout, to `51440da2`.

It runs the model check after each config write and at the end, and it proves every predecessor
digest and the untracked set. This covers an unreviewed render too. It uses a temp-file name
distinct from the forward steps.

The record lists any leftover temp files and renderer shadow directories. They are reported and
never deleted. The record also states whether the authority worktree remains; it is left in
place, clean and unreferenced.

After a rollback, no forward step can run.

`test_prereqs.py` covers:

- the full forward sequence;
- a `finish` refusal followed by `resume`;
- resume without the postcondition;
- the Git-object check before the checkout moves;
- both render refusal paths and an apply mismatch;
- the executor-window gate;
- rollback from every partial state through consistent configs;
- a corrupt backup;
- leftovers;
- host change;
- the candidate binding.

## Dependencies outside this package

Each dependency is digest-pinned at load time and has a byte-identical durable copy under
`~/.local/share/gas-city-staging/{ga-mutg-20260920,gct-m1wh-metadata-20260922}`.

- The legacy recovery sources in the ga-e0t1 tracker `reports/`.
- The R9 helper `reports/ga-mutg-metadata-quiet-r9-20260920/manifest_candidate.py`.
- The `/tmp` chain it loads:
  - `/tmp/ga-mutg-adoption-20260920`;
  - `/tmp/ga-mutg-adoption-20260920-r3`, `-r4`, `-r6` and `-r7`;
  - `/tmp/ga-mutg-metadata-quiet-20260920-r9`.
- The M1 audit and the M3 baseline in the durable staging directory.

If `/tmp` is cleaned, restore those paths byte for byte before running.

## Review dispositions for r2 (c3a49e55: one SOURCE_PASS, one HOLD)

| Finding | Disposition |
| --- | --- |
| `finish` quiet check refuses while the reconciler runs, which strands a mutated step (must-fix) | Reconciler quiet slot before every quiet check (natural drain, bounded, tested with a fake clock), plus intent records and a verify-only `resume` (tested). |
| RENDERER_SHA untested and checked only after the checkout moved | Proved from the Git object before the checkout (tested); also tested against the blob in `test_manifest.py`. |
| Template `.git` config bound narrower than documented | Full `git config --list` check; only `branch.<name>.remote/merge` vary. No `config.worktree` anywhere. Tested with include, credential, gpg and extensions entries. |
| Rollback restores city before the fragment (inverse unordered state) | Transitional city first, model check after each write (tested from every partial state). |
| Re-pinned tree predecessors not asserted | `REPINNED_TREE_PREDECESSORS` asserted in the builder (tested). The bound baselines are asserted against the reviewed digests. |
| Many refusal branches untested | 15 more builder refusal cases and the prerequisite refusal paths added, each asserting its reason. |
| libexpat successor not derived by a test | The test checks the live SHA-256, the dpkg MD5 record and the R9 predecessor. Operator acknowledgement requested. |
| `models()` unordered refusal not unit-tested | Unit test, including a probe agent. |
| Docs inaccurate (no-optional-locks, registry.json, host) | Corrected. |
| `derive_expected` uses `assert` | Replaced by `require`, which `-O` cannot disable. |
| `inputs` re-reads the fragment after checking | It writes the exact bytes it checked. |
| `validate_states` could break the cache closure | Documented: run only before the sequence. |
| Render parses before checking the exit code | The exit code is checked first (tested with rc 3). |
| Rollback refused after the executor window, although executor recovery only restores the timer | Allowed once `restored.json` exists and no apply started (tested). |
| Rollback has no quiet check or leftover detection; authority left in place | Slot waited for, quiet result recorded, leftovers reported, authority presence recorded. |
| Semantic check only after the write; `city-final` and `render` do not assert their companions | Checked before writing; companions asserted (tested). |
| `models()` scope | Extended to agent definitions and city patches. The scope is documented. |
| `quiet()` fully stubbed in tests | `quiet_slot` tested directly. The host observation itself runs only in the supervisor namespaces and is stated as such. |
| `capture.py` untested | `test_capture.py`: tree bounds, config check, bound baselines, pin-change guard, candidate binding. |
| `complete()` never refuses pin drift | Refuses any change except the six reviewed successors (tested). |
| Bound baseline not asserted | Asserted (tested). |
| Bound too strict for rerere and removals | `rr-cache` added; removals allowed inside the allowed Git-state set only. |

## Review dispositions for r1 (fb7f01cf, two HOLD verdicts)

| Finding | Disposition |
| --- | --- |
| Registry still pins 2.1.263 (must-fix) | Registry sync step. Both the registry and fragment are re-pinned, derived from the 28539934 profiles and renderer. |
| `render` writes before checking; rollback cannot undo a wrong render (must-fix) | `--check` must predict `cba75f87` before `--apply`. Rollback restores any non-predecessor fragment from its verified copy (tested). |
| Invalid-config window starts at `city` (must-fix) | Transitional city.toml ordering, plus the semantic model check before and after each config step. The supervisor reload behaviour is documented. |
| Retained Template pins not checked offline | `RETAINED_TEMPLATE_PINS`, asserted in the builder and at checkout, and tested against both commits. |
| `RIGPERM_NEW` not derived by a test | Derived with the real renderer and a method check, in `derive_expected.py` and the tests. |
| Suspension digest checked late | Checked in every `prereqs.py` step. |
| Untested branches; reasons not asserted | Every negative case uses `assertRaisesRegex` with its reason; the missing branches were added. |
| Predecessor digest not asserted | `test_predecessor_is_installed_r9`. |
| No real-baseline build test | `test_build_against_frozen_baseline` (refuses before the freeze, builds after it). |
| Re-pinned trees accept any digest | Bounded diffs in the audit. |
| Ancestor overlap unchecked | The guard now covers ancestors, and it is tested. |
| `derive_expected` docs inaccurate | Rewritten. |
| City-config source predecessor unasserted | Asserted as `r5/i/07`. |
| CLI 2.1.280 never run inside W | Stated. The `observe` dry-run is the first proof and fails closed. |
| Preconditions not checked in code | Quiet-host, suspension, installed-manifest and package-root checks run in every step. |
| No tests of the live code | `test_prereqs.py` (13 tests in r2, 20 in r3). |
| Rollback restores city without verification | Every restore verifies its backup digest. |
| Rollback while the package root exists | Refused (tested). |
| Steps can run after a rollback | Refused (tested). |
| `inputs` consumes its directory before validating | It validates first (tested). |
| Candidate not digest-pinned | Both scripts require the reviewed candidate SHA-256. |
| `complete` does not check host stability | It requires `host == host_after`. |
| `/tmp` list incomplete | The list is complete, including `-r6`. |
| Render side effects undocumented | Documented in step 2.6. |
| `r5/r` index rewriter unidentified | Identified, and bounded. |
| Shared temp-file name | Forward and rollback use distinct names, and a leftover refuses. |
