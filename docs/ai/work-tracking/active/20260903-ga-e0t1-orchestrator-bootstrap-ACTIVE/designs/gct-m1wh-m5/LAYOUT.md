# M5 metadata successor: layout proof and activation plan (r9)

This package serves Bead `ga-0t04` (Operations) for Template Bead `gct-m1wh`, together with the
Opus 5.5 scope of `gct-er3h`.

- Target: Template main `28539934fa742056e0a65710d5638ff559a21175`, the PR 69 merge.
- Its tree `cfe24ca7` is identical to the reviewed branch head `0db4d800`.

Revision history:
- r2 answered the two HOLD reviews of r1 (`fb7f01cf`).
- r3 answered the two reviews of r2 (`c3a49e55`). The manifest-lens run returned SOURCE_PASS
  with should-fix items; the live-safety run returned HOLD.
- r4 answered the two HOLD reviews of r3 (`47c490ed`). Both found the same must-fix: the
  reconciler observer ran without the user-bus environment.
- r5 answers the reviews of r4 (`56a84aff`). The live-safety lens returned SOURCE_PASS; the
  manifest lens returned HOLD. Its must-fix: the r3 "no `config.worktree` anywhere" rule refused
  the 93 pre-existing empty `config.worktree` files in the live Template `.git`.
- r6 (`310dfa54`) pinned the first live capture. Its binding review returned one SOURCE_PASS and
  one HOLD, because the pinned baseline had already reached its cache-renewal horizon. r7 answers
  that review; see "Binding step" below.

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
- **libexpat re-pin:** the operator accepted it on 2026-09-23. It is a distribution security
  update and was not part of the earlier decisions.

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
| **M5 r5** | **128,071** | **3,001** |

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
    - may change only objects, refs, logs, worktree admin, LFS locks, rerere and workflow
      transactions, plus HEAD, index, FETCH_HEAD, ORIG_HEAD, COMMIT_EDITMSG, packed-refs and
      config;
    - its non-branch config must equal the reviewed set;
    - hooks, info and description must be unchanged.

  Rerun under the r5 rules on 2026-09-23, before commit, against the live trees, both are inside
  their bounds:
  - `r5/r`: 2 changed entries, 0 outside;
  - `.git`: 83 changed, 92 added, 0 removed, 0 outside, with its 93 pre-existing empty
    `config.worktree` files admitted.

  Also clean on that run:
  - the Git config (no drift);
  - replace refs (none);
  - the pinned `prereqs.py` load;
  - the real reconciler observer.

  `test_bound_accepts_the_real_reviewed_inventory` applies the bound to the real M1 inventory.

  The cause is identified. At 2026-09-23 01:39, a plain `git status` without
  `--no-optional-locks`, run by the read-only M4 investigation, rewrote the `r5/r` index and five
  linked-worktree indexes inside the Template `.git`. HEAD did not change. Every git command the
  package runs at runtime (prereqs, capture, derivation) uses `--no-optional-locks`. The test
  files read Git objects, the Template `.git/config`, the live city files and agent definitions,
  and the user bus. None of those reads can change a pin, because pins exclude access times, and
  the tests run before the capture. The quiescent window forbids any other reader.

  Both bounds are anchored and asserted (`test_capture.py`):
  - the `r5/r` M1 baseline is the R9 pin `ad25084c`;
  - the Template `.git` M1 baseline is M3's reviewed `cbe4982a`.

  For the Template `.git`:
  - additions, changes and removals are allowed only in objects, refs, logs, worktree admin, LFS
    locks, rerere and workflow transactions, plus HEAD, index, FETCH_HEAD, ORIG_HEAD,
    COMMIT_EDITMSG, packed-refs and config;
  - the following are never admitted, even inside those prefixes:
    - `refs/replace`;
    - object alternates and grafts;
    - `shallow`;
    - a worktree `info/` directory;
    - a change to an existing worktree's `commondir` or `gitdir`;
  - `config.worktree` files are admitted only as they already are: pre-existing, unchanged
    and empty. Git ignores them, because `extensions.worktreeConfig` is unset and the config
    check refuses any `extensions.*`. An added, changed, removed or non-empty one refuses;
  - any replace ref, loose or packed (`git for-each-ref refs/replace`), refuses;
  - `gc` and `repack` are stricter than needed. They may write `info/refs`, `gc.pid` or
    `gc.log`, which fall outside the bound and refuse closed, and the quiet window forbids them;
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
claude-family selection must name an offered model. A selection without a provider inherits
`workspace.provider`. Its scope:
- providers.claude defaults;
- city rig overrides;
- `[[patches.agent]]` in city.toml and in the rig fragment;
- every `agents/*/agent.toml` option default, resolving each provider through its `base` chain.

The two other included fragments select no model, and pack-imported agent defaults are out of
scope; the live packs set no model. The check is a pure function and is unit tested. It refuses
the unordered state, a probe agent that selects `opus-5`, and an agent without a provider that
selects `opus-5`.
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
elapse is at least 40 s away.
- The observer uses `systemctl --user` and `busctl --user` (the timer's
  `NextElapseUSecMonotonic`).
- It sets the user-bus environment (`XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`), exactly as
  the reviewed legacy `observe_recovery.ENV` does.
- A test calls the real observer against the user bus.
- The wait is bounded at about 180 s: the deadline is checked after each observation, and an
  observation is three calls of at most 10 s each. The timer is never started, stopped or
  signalled.
- The observer requires the exact property sets, so a missing field never reads as idle.
- `capture.py complete` waits for the same slot before its scope check, and loads `prereqs.py`
  only at its pinned digest.

**Intent and resume.** Each step writes `prereq-<step>.intent.json` just before its mutation,
after every precondition check, including the absence of a leftover forward temporary file.
- If the step is interrupted afterwards (for example, a quiet check fails in `finish`), the same
  step refuses to run again.
- `prereqs.py <candidate> resume <step>` binds the intent's step and candidate. It then proves
  the exact reviewed postcondition and a quiet host, and writes the missing record with
  `resumed: true`. It never repeats the mutation.
- `inputs` accepts an existing empty `m5-inputs` directory, which is what an interruption between
  its `mkdir` and its intent leaves.
- If the postcondition does not hold, only `rollback` remains.
- A refusal before the intent is benign; nothing was changed.

0. **Preflight (read-only, on the host terminal):**
   - run the read-only probe;
   - verify that the package worktree is clean at the reviewed commit;
   - run the three test files. They include the live-host user-bus test and the `PREREQS_SHA`
     pin test, so any environment or pin mismatch shows before step 1 consumes anything.
1. **Preconditions.**
   - `prereqs.py` checks these before every step:
     - supervisor identity through `host_observation`;
     - an empty supervisor scope and no city tmux server (`quiet_scope`);
     - suspension record `823e4e21`;
     - installed manifest `a6324753`;
     - no `reports/m5` root and no rollback record.
   - After every step it re-checks the quiet host: identity, scope and suspension.

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
   8. `authority`: `git worktree add --detach`. The worktree must be clean at 28539934, with no
      ignored or untracked file anywhere (`status --ignored --untracked-files=all`). Every file,
      link and tree root is proved, and the exact root entry set.
3. **Capture.** Run `capture.py <candidate> audit`, then `complete`, then `settle`, then
   `freeze`. Each stage binds the previous stage's digest.
   - `audit` requires every prerequisite record to carry the capture's candidate digest. It
     refuses on any of these:
     - file, tree, protected, repository, canonical, config, link, absent or host drift;
     - a re-pinned tree root-mode change;
     - an ignored or untracked file in the authority;
     - any re-pinned tree change outside its bound.
   - `complete`:
     - requires a stable audit host;
     - carries forward every infrastructure pin of the M3 baseline;
     - refuses any carried-forward pin that changed other than the six reviewed inputs at their
       exact successor digests;
     - waits for the reconciler quiet slot before its scope check.
   - `settle` uses ordinary reads only.
4. **Pin the baseline:**
   - set `BASELINE_SHA`;
   - run the four test files: 17 manifest, 38 prerequisite, 9 capture and 9 recorder tests, 73 in
     all. `test_build_against_frozen_baseline` builds from the real file;
   - confirm the renewal horizon: the oldest frozen cache atime plus 24 h must leave the full
     900 s window, the 10 s margin and the review time. `operator/M5-EXECUTE.sh` refuses before
     `prepare` otherwise;
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
- no M5 executor window may hold the reconciler timer paused or may have launched an apply. The
  window counts as open when `q/commit-consumed.json` exists, or when
  `q/preparation-pause-intent.json` exists without `q/restored.json`. A `prepare` that refused
  before its pause intent never touched the timer. The executor's own recovery restores only the
  timer; it never reverts the live prerequisites;
- no rollback has already run.

Rollback first attempts the quiet-host observation, including the reconciler slot, and records
the result. That result is never required, so restoration stays possible even if the user bus or
the reconciler misbehaves (tested). It then verifies the digest of every backup it will need
before any write.

Model checks during rollback are recorded, not required. The predecessor bytes are proved
directly. A malformed agent definition therefore never stops a restoration (tested).

Rollback loads the candidate, and the candidate loads the R9 helper chain, which includes `/tmp`
files. If `/tmp` has been cleaned, restore those files byte for byte from the durable copies
(see below) before running rollback.

Each restore writes exactly the bytes whose digest it has just verified, through a fresh per-attempt
temporary name. A crash inside a restore therefore never blocks the next rollback attempt; the
earlier temporary is reported, not deleted.

Rollback restores in an order that never composes the inverse unordered state:

1. the transitional city.toml, if the final one is installed;
2. the fragment and the registry, from their `m5-inputs` copies;
3. the predecessor city.toml, from `r5/i/00`;
4. the CLI, from its backup;
5. the canonical checkout, to `51440da2`.

It runs the model check after each config write and at the end, and it proves every predecessor
digest and the untracked set. This covers an unreviewed render too. It uses a temp-file name
distinct from the forward steps.

The record lists leftovers, which are reported and never deleted:
- temp files;
- renderer shadow directories;
- the retained CLI backup. A successor package's `cli` step refuses while that backup exists.

The record also states whether the authority worktree remains; it is left in place, clean and
unreferenced.

Residual limits:
- `checkout` refuses a pre-existing `index.lock` before its intent. An interrupted `git
  checkout` that leaves `index.lock` or a half-updated tree is repaired neither by `resume` nor
  by `rollback`. Its postcondition refuses, and the operator must recover it by hand.
- Suppose the executor's `prepare` writes its pause intent and then refuses or crashes before
  recording the stop command. Rollback then stays refused. This is deliberately conservative: a
  crash between the stop and its record cannot be told apart from one before the stop. The
  operator must first confirm the reconciler timer state by hand.
- Rollback does not restore the Template `.git` tree to its R9 pin, and does not remove the
  authority worktree. Neither matters while the installed manifest is still R9, because the M5
  pins exist only in the M5 package.

After a rollback, no forward step can run.

`test_prereqs.py` (38 tests) covers:

- the full forward sequence;
- a `finish` refusal followed by `resume`;
- resume without the postcondition;
- the Git-object check before the checkout moves;
- both render refusal paths and an apply mismatch;
- the executor-window gate, including a `prepare` that never paused;
- rollback refused once the successor is installed;
- the user-bus environment and argv of the reconciler observer, and a call to the real user bus;
- the composition of `quiet()`;
- the companion checks before `city-transition` and `render`;
- the worker and retained-blob checks before the checkout moves;
- a backup written but not yet replaced;
- a forward temporary that refuses before the intent;
- rollback re-entry after a crash inside a restore;
- resume binding its intent;
- `inputs` reusing only an empty directory;
- workspace-provider inheritance;
- a failing quiet observation during rollback;
- a broken agent definition during rollback;
- an ignored or untracked authority file;
- a symlinked or open `inputs` directory;
- a locked index before the checkout;
- missing reconciler observation fields;
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

## Binding step (r6, 2026-09-23): live results and executor entry

r6 (`310dfa54`) changed no reviewed logic. It changed:
- `manifest_candidate.py`: `BASELINE_SHA` and a two-line comment, and nothing else (digest
  `29cee991` → `9f293b9c`);
- `source-pins.json` (new);
- `record_review.py` and `test_record_review.py` (new).

The other four launch modules and `launch.py` were byte-identical to r5.

**r6 dispositions and r7.** Review A returned SOURCE_PASS with no must-fix. Review B returned HOLD.

The must-fix, confirmed in `metadata_window.build`:
- the window's renewal horizon is the oldest frozen cache atime plus 24 h;
- that atime was 2026-09-22 09:29:24Z, so `prepare` had to start before 09:14:14Z;
- `prepare` checks the horizon only after it has created `reports/m5` and written two records, so
  a late start consumes the package root;
- after 09:29Z, relatime renews those atimes on the next read, so the baseline expires anyway.

The executor was never started. `reports/m5` does not exist and the timer was never touched. The
expired first capture root `reports/m5-capture` (baseline `8f980d2e`) is preserved unmodified.

r7 changes:
- `manifest_candidate.py` returns to the exact r5 bytes (`29cee991`, `BASELINE_SHA = None`). The
  eight prerequisite records bind that digest, and `capture.py audit` requires it.
- `capture.py` writes a fresh root, `reports/m5-capture-r2`, and binds it the same way. That is the
  only change.
- `record_review.py`:
  - publishes every file atomically: a temporary name, fsync, then `link()`, which never
    overwrites and leaves no partial record (B should-fix 3);
  - uses the executor float `36.0` (B should-fix 2).
- Its tests are no longer circular:
  - `source_review` runs as the real consumer;
  - the PAIRING bindings carry the executor float;
  - the AST key sets match `source_review`, `paired` and `restore`;
  - atomicity is tested.
  There are now 9 recorder tests (B should-fix 2 and 5).
- `operator/` holds the exact live wrappers for review:
  - `M5-PREREQS.sh`, already run;
  - `M5-CAPTURE.sh`, which refuses before 10:44:00Z and prints the horizon;
  - `M5-EXECUTE.sh`, which runs detached as its own user unit with all output to a file (A
    should-fix 3, B should-fix 4). It has a hard horizon gate before `prepare` (B must-fix), and
    it waits for each review record and stops on any refusal, HOLD marker or timeout;
  - `gate_extract.py` and `GATE-PROMPTS.md` for the in-window gates.

**Recapture schedule.** Yesterday's cache atimes cluster at 09:29 (1994 entries), 10:42 (177) and
13:33 (13191). A capture at 10:44:00Z or later refreshes the first two clusters on its settle
reads. That puts the horizon at 13:33:50Z. r9 then pins `BASELINE_PATH`
(`reports/m5-capture-r2/baseline.json`) and `BASELINE_SHA`, regenerates `source-pins.json`, fills
`{BASELINE}` in `operator/GATE-PROMPTS.md`, and gets its binding reviewed.

**r7 dispositions and r8.** Both r7 reviews returned HOLD on the in-window tooling. Neither found
a defect in the recapture path. They agreed on three must-fixes. One review added a fourth:
- **The window gates.** `observe` and `paired` started without checking the remaining window. A
  native phase writes `<phase>-consumed.json` before `admit()` reserves its 66 s. If admission
  then refuses, the result is not terminal and `restore-preapply` refuses.
- **The fix.** `operator/M5-EXECUTE.sh` computes the remaining window exactly as `admit()` does,
  from the recorded deadline: the minimum of the monotonic deadline, the boot-time deadline, and
  the renewal horizon minus 10 s. It then:
  - starts `observe` only with more than 180 s left, and `paired` only with more than 300 s;
  - bounds the SOURCE_PASS wait at 540 s of window left and the PAIRING_PASS wait at 300 s.
  Stopping at a gate leaves `restore-preapply` valid.

The review's should-fixes are also taken:
- `horizon_left` parses `BASELINE_PATH` as text, so no package code runs before the clean check;
- `gate_extract.py` checks the exact four MUTATE actions and targets, and lists every unparsed plan
  line;
- a missing stop record points to the manual timer check;
- `GATE-PROMPTS.md` documents the HOLD marker convention. r8 changes only `operator/`, `record_review.py`'s docstring and this
file. `manifest_candidate.py` stays at the r5 bytes `29cee991`.
- **Must-fix: extract location.** `gate_extract.py` wrote into `operator/`, which is not ignored.
  The new file dirtied the worktree, so `pause`'s clean check would stop the run. It now writes
  only into the staging directory.
- **Must-fix: pause recovery.** A `pause` failure printed `recover-pause` even before
  `pause-consumed.json` existed, where `recover_pause` refuses. The wrapper now prints
  `recover-pause` only when that file exists, and `recover-preparation` with the intent digest
  otherwise.
- **Must-fix: the COMMIT_PASS deadline.** `restore-accepted` has no window deadline, but it still
  needs the exact cache metadata. Snapshot reads refresh atimes older than 24 h, so it must run
  before the renewal horizon. Both limits changed:
  - The gate before `prepare` now requires the horizon to leave the window (900 s), its margin
    (10 s), 1800 s for the COMMIT_PASS reviews and restoration, and 300 s of slack: 3010 s in
    all. It runs after the clean check (should-fix).
  - The COMMIT_PASS wait ends 310 s before the horizon.
- **Should-fixes answered.**
  - `GATE-PROMPTS.md` takes the pinned baseline as `{BASELINE}` and no longer names `8f980d2e`.
  - `M5-CAPTURE.sh` refuses outside 10:44:00Z–12:30:00Z. A settle near the horizon would refuse
    and consume the root. It prints the latest executor start with the same 3010 s reserve.
  - Log locations are stated as the staging directory.
  - The review waits end at 540 s and 300 s of window left (see the window gates above). The
    executor's own deadline checks remain authoritative.
- **With a 13:33:50Z horizon,** the executor wrapper accepts `prepare` until about 12:43Z (14:43
  Stockholm).

**r8 dispositions and r9 (the binding step).** Both r8 reviews returned SOURCE_PASS with no
must-fix. The recapture then ran once, from 10:46:58Z to 10:49:14Z, as the operator entry
`operator/M5-CAPTURE.sh cc3c52c7…`:
- audit `cef3d4ad`, with no unexpected drift and a stable host;
- complete `7a7a56d0`: exactly the six `CHANGED_INPUTS` changed, over a clean scope with no city
  tmux server;
- settle `1d06ca72`;
- freeze `baseline.json` `68cbee54`;
- horizon 13:33:50Z, so the latest executor start the wrapper accepts is 12:43:40Z.

r9 changes:
- `manifest_candidate.py` pins `BASELINE_PATH = reports/m5-capture-r2/baseline.json` and
  `BASELINE_SHA = 68cbee54`, with a comment. Its digest is `1362860d`.
- `source-pins.json` is regenerated (`c3cded5a`).
- The operator wrappers take the r8 should-fixes:
  - a git status failure counts as dirty;
  - before `prepare`, the wrapper refuses if a HOLD marker is left over or `reports/m5` exists;
  - `recover-preparation` is suggested only after a successful stop record;
  - a pause failure with `window.json` present gets `restore-preapply`;
  - an observe that is consumed without a result gets "inspect";
  - the SOURCE_PASS wait ends at 660 s of window left, so the PAIRING_PASS reviews keep time;
  - the paired gate is derived from the measured pause (167 s plus twice the pause plus 30 s, and
    at least 300 s);
  - waits count wall-clock time;
  - the horizon is rechecked before `restore-accepted`;
  - `GATE-PROMPTS.md` puts drafts in staging and forbids checkout writes and gc calls during the
    transaction.

Checks at r9:
- 73 tests pass;
- the launch.py loader replay passes for `c3cded5a` and all six sources;
- the real-baseline build gives 685 inputs, 49 trees and 23 links, frame 128071 of 131072, and the
  authority last at `28539934`.

**Rollback digest (A should-fix 2).** `prereqs.py <digest> rollback` needs the digest of the
current `manifest_candidate.py` bytes: `29cee991` at r7 and r8, and the r9 digest after the pin.
`rollback()` reads no step or intent record, so any digest mismatch refuses cleanly and consumes
nothing.

**Launcher loader (A should-fix 4).** On 2026-09-23 the coordinator replayed launch.py's
source-inventory checks outside any stage. `source-pins.json` `7656a92f` and all six sources
passed: digest, mode 0644, uid/gid 1000 and nlink 1. r9 regenerates `source-pins.json` and
repeats that check.

**Executor entry, found live.** "Host terminal" in the live sequence means this exact form, typed in
a real WSL terminal:
`systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 <command>`
- Every WSL terminal session, `!` commands included, is in mount namespace 4026532229. The
  supervisor and all systemd units are in 4026532219, so `host_observation` refuses from a terminal.
  A transient `app.slice` unit under `user@1000` is in the supervisor namespaces.
- User-manager children inherit umask 0002 (the supervisor shows Umask 0002). Without
  `-p UMask=0022`, git would write 0664 and 0775 modes against the pinned 0644 and 0755 ones. Four
  prerequisite tests failed exactly that way until the property was added. With it, 38 of 38 pass.
- The staged wrappers `M5-PREREQS.sh` and `M5-CAPTURE.sh` apply this form to every step. Before
  each step they check that the package worktree is clean at the reviewed commit, and they stop at
  the first refusal.

**Live results.**
- **Preconditions.** From 08:32Z the host probe passed under that form: same namespaces, city and
  four rigs suspended, zero sessions, signer 5550.
- **Prerequisites.** All eight ran once, unresumed, 08:38–08:47Z, all bound to candidate `29cee991`.
  Readback:
  - the worker CLI is `1e08503d` (2.1.280);
  - city.toml is `4f7e170f`, the registry `d22cf4c1`, the fragment `cba75f87`;
  - the Template checkout and the authority are at `28539934`;
  - the installed manifest is still `a6324753`;
  - the supervisor, still 3150812, reloaded to revision `d6ca85cd`.
- **Capture,** 08:49–08:51Z:
  - audit `1041f0d0`, with no unexpected drifts and a stable host (the absent list is empty);
  - complete `ca35f7ff`, where exactly the six `CHANGED_INPUTS` changed, over a clean scope;
  - settle `fda048e0`, with one atime change;
  - freeze: `baseline.json` `8f980d2e`.
- **Real build.** The real-baseline build gives:
  - 685 inputs, 49 trees and 23 links;
  - frame 128071 of 131072;
  - no python3.12 test input;
  - the authority last, at `28539934`;
  - `previous_metadata.manifest_sha256` = `a6324753`.

**In-window recorder.** `record_review.py bindings <KIND>` prints the exact bindings that the
executor demands from `q/`:
- the package digest, which is `sha256(prepared.json)`;
- for PAIRING_PASS, the probe limit of 36.

`record_review.py record <KIND> <draft> <draft>` then writes:
- both provenance files, as `reports/m5-reviews/<kind>-<reviewer id>.json`;
- `q/<kind>.json`.

All writes are O_EXCL, in the executor canonical encoding. Both provenance paths are checked
before either is written. It then rechecks the record with the controller rules. Its test runs the
real `recovery_controller.review()` (`dcc78e45`) against the records it writes.

## Review dispositions for r4 (56a84aff: one HOLD, one SOURCE_PASS)

| Finding | Disposition |
| --- | --- |
| "No `config.worktree` anywhere" refuses the 93 pre-existing empty files in the live Template `.git` after all eight mutations (must-fix) | Pre-existing, unchanged, empty files are admitted; added, changed, removed or non-empty ones refuse (tested). The bound is tested on the real M1 inventory and was rerun on the live trees before commit: 0 outside. |
| `load_prereqs` hashes one read and executes another | It executes the verified bytes. |
| Replace refs can arrive through `packed-refs` | The audit refuses on any `git for-each-ref refs/replace` output. |
| The rollback path where the quiet observation fails is untested | Tested: rollback completes and records the error. |
| Untested branches (`gitdir` change, denied entry present but unchanged, `info/grafts`, authority ignored file) | All tested. |
| Stale allowed list | Includes `rr-cache` and `packed-refs`. |
| `reconciler_state` does not require exact fields | Exact property sets required (tested). |
| Slot wait can exceed 180 s | Per-call timeout of 10 s; the bound is documented as approximate. |
| `gc`/`repack` strictness | Documented as fail-closed under quiescence. |
| Host-dependent test | Named as a live-host test; the preflight runs it on the host first. |
| Authority tree digests are captured, not derived | Accepted. Content is proved by clean `git status --ignored --untracked-files=all`, HEAD, the exact root entry set, the file digests and the frozen tree digests. |
| Executor residual: pause intent without a stop record | Documented as a conservative residual limit. |
| Tests run only after `capture audit` | Preflight step 0 runs all three test files on the host first. |
| Rollback docs order | Corrected: observe, then verify, then restore. |
| Statement about what the tests read | Corrected. |
| Rollback model checks narrow; final check unguarded | Every model check during rollback is recorded, never required (tested with a broken agent file). |
| `inputs` accepts a symlinked empty directory | `lstat`: must be a real directory with mode 0700, owned by the user, and empty (tested). |
| Rollback depends on the `/tmp` chain | Stated in the Rollback section. |
| No `index.lock` check before the checkout intent | Checked before the intent (tested). |

## Review dispositions for r3 (47c490ed: two HOLD verdicts)

| Finding | Disposition |
| --- | --- |
| Reconciler observer runs `systemctl --user` and `busctl --user` without the user-bus environment, so every quiet check, rollback and `complete` refuses (must-fix, both lenses) | `BUS_ENV` adds `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS`, as the reviewed legacy environment does. The failure was reproduced (`Failed to connect to bus: No medium found`) and the fix verified. Tests assert the environment and argv and call the real user bus. |
| Rollback requires the slot, contrary to the docs | The whole quiet observation, slot included, is recorded and never required (tested through the stubbed context). |
| Re-pinned tree root-mode drift filtered out of the audit | The filter is removed; any drift left for a re-pinned tree refuses. |
| `.git` bound admits `refs/replace`, alternates, grafts and worktree files | Denied: `refs/replace`, `objects/info/{alternates,http-alternates,grafts}`, `shallow`, worktree `info/`, and changes to an existing `commondir` or `gitdir` (tested). |
| `packed-refs` undocumented | Documented in `capture.py` and here. |
| `capture.py` loads `prereqs.py` unpinned; prerequisite records not bound to the candidate | `PREREQS_SHA` is pinned and tested for consistency. `audit` requires each record's `candidate_sha256`. |
| Ignored files under authority trees unchecked | `status --ignored --untracked-files=all` must be empty, in both the `authority` step and the audit. |
| Untested branches | Added: `config.worktree` present but unchanged; Template `.git` predecessor tree; worker and retained-blob refusals; `complete` is covered through its pure guards. |
| Stale wording; M3 candidate read unpinned in a test | Fixed; the M3 candidate digest `cc918038` is asserted. |
| Crash inside a rollback write blocks every later rollback | Per-attempt rollback temporary names (tested). |
| `executor_closed` refuses when `prepare` never paused | The window is open only with a pause intent and no restoration, or with an apply consumed (tested, four cases). |
| Precondition checks after the intent (leftover temporaries); `inputs` directory before its intent | Forward temporaries are checked before the intent (tested). `inputs` reuses only an empty directory (tested). |
| CLI backup left behind and unreported | Reported in leftovers. The successor package's `cli` refusal is documented. |
| `resume` trusts the intent file | It binds the intent's step and candidate (tested). |
| Rollback verifies a backup, then re-reads it | It writes exactly the bytes it verified. |
| `models()`: a missing provider is treated as not claude | A selection without a provider inherits `workspace.provider` (tested). Pack-imported defaults are documented out of scope. |
| Docs: pre-step and post-step checks; interrupted checkout; Template `.git` pin and authority after rollback | Corrected and documented as residual limits. |
| Test gaps: the real observer, `quiet()` composition, the `city-transition` and `render` companions, the rollback INSTALLED gate, backup written but not replaced | All added. |

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
