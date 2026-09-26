# M10: adopt Core 207a78e2 and the replace-mode city.toml in the platform metadata (ga-bebv S3)

This is S3 of the ga-bebv deployment (operator decision 2026-09-27, "Prepare and apply"): a metadata successor
that switches the city claude and codex providers to replace-mode option schemas and adds work_dir_roots, over
the sequence 16 Core (S2, gc 207a78e2, the ga-6umo hotfix). Receipt refresh (P11) follows as its own package.

## Why

The ga-6umo hotfix keeps only benign metadata options (model and effort) and refuses a session or task
work_dir outside the configured work_dir, the rig session worktrees and the agent's `work_dir_roots`. The live
city.toml still merges the claude and codex providers `by_key` over the builtin schemas, and those offer
unrestricted choices:
- claude `unrestricted` (`--dangerously-skip-permissions`);
- codex `unrestricted` (`--dangerously-bypass-approvals-and-sandbox`) and the `danger-full-access` sandbox.

Every provider derived from claude or codex inherits them (claude-signing, claude-candidate, claude-attention,
codex-managed, codex-managed-worklog, codex-attention, codex-evidence). The hotfix already stops metadata from
selecting them; M10 removes them from every option schema. Known residual (r1 review B should_fix 2): the
builtin `PermissionModes` map merges additively, so Core still knows those argv as permission-mode policy
(`ValidateManagedLaunchPermissionPolicy`). No schema offers them, so nothing can select them. The task worktree roots move under
`work_dir_roots` so the guard accepts every real candidate worktree and nothing else.

## The city.toml change (make_city.py, 4f7e170f to e5b68c40)

Exactly three changes, derived from the installed bytes by count-checked edits:
1. `[providers.claude]` becomes `providers-claude.toml`: `options_schema_merge = "replace"`, with keys
   permission_mode (auto-edit `--permission-mode auto`, full-auto `dontAsk`, plan), effort (low to max),
   model (opus-5-5, fable-5, haiku-4-5, sonnet-5) and the unchanged worktree_access. The option defaults gain
   effort "max" and worktree_access "none", each equal to its schema default.
2. `[providers.codex]` becomes `providers-codex.toml`: replace mode, with keys permission_mode (fail-fast
   `--ask-for-approval never`, attended `on-request`), model (sol, luna, terra), effort (low to max) and the
   unchanged five-choice worklog_access. `[providers.codex-evidence]` is carried verbatim after it.
3. Eight `[[patches.agent]]` entries are appended, setting work_dir_roots for:
   - Template implementation-worker, run-operator and codex: `/home/loucmane/gas-city-template-worktrees`;
   - Core implementation-worker: `/home/loucmane/gascity-core-worktrees`;
   - Core operations-candidate-worker: `/home/loucmane/gas-city-ops-candidate-worktrees`;
   - Blog implementation-worker: `/home/loucmane/dev/blog-worktrees`;
   - HPFetcher implementation-worker and run-operator: `/home/loucmane/dev/hpfetcher-worktrees`.

The key order in each schema is the order the effective by_key merge produces today, so launch commands
stay byte-identical.

**Offline Core probe (2026-09-27).** `probe/zz_probe_providers_test.go.txt` ran as a throwaway test in the
ga-6umo worktree at f45a6262, then was removed. It loaded the city with `LoadWithIncludes` and resolved every
agent and named provider with `ResolveProvider` and `BuildProviderLaunchCommand`. It also dry-ran
`pathutil.GuardLaunchWorkDir` over every real worktree under each root. The results are:

| | today (`probe-current.json`) | M10 (`probe-full.json`) |
| --- | --- | --- |
| entries | 118 | 118 |
| entries offering an unrestricted choice | 113 | 0 |
| resolution errors | 0 | 0 |
| launch command or default differences | | 0 |

The guard accepted 33 Template, 35 Core, 18 Blog and 6 HPFetcher worktrees, and 0 under the operations
candidate root, which has none today. It refused only `blog-worktrees/.git`, a Git metadata directory, which
is correct.

Limits of the probe (r1 reviews A should_fix 5 and B should_fix 3): it compares the default launch command and
the effective defaults only. It does not compare resume commands (they carry no schema flags), title
arguments or `PermissionModes`, and its output records no digest of the city bytes it loaded. The binding of
`probe-full.json` to e5b68c40 rests on the run log of 2026-09-27, not on the file.

Behaviour change (r1 review B should_fix 1): the builtin claude title model is `haiku`, and replace mode drops
that choice, so title generation runs `claude -p` without `--model` (the CLI default). That is a cost and
latency change, not a safety one. Follow-up: add `title_model = "haiku-4-5"` to `[providers.claude]` in the
next city-config successor.

## The complete delta (M9 to M10)

| Field | M9 | M10 | Why |
| --- | --- | --- | --- |
| core.source, core.sha256 | ga-e0t1.18 gc-a, fce2e9a0 | ga-bebv gc-a, 207a78e2 | sequence 16 (receipt 1108b724) |
| writer, the gc input | fce2e9a0 | 207a78e2 | the installed image |
| activation.expected_commit | deefb98b | f45a6262 | the build's `gc version` commit |
| previous_sha256, backup_path, previous_commit | fce2e9a0, ga-e0t1.18 gc-b, deefb98b | unchanged | Core's validateSuccessor: they must name M9's core, which they already do |
| city-config source, sha256 | m5-inputs/city.toml, 4f7e170f | m10-inputs/city.toml, e5b68c40 | the new city.toml |
| city-config previous_sha256, backup_path | 4f7e170f, m6-inputs/city.toml.before | unchanged | Core's successor rule: previous is M9's sha256; that backup already holds those bytes |
| the city.toml input | 4f7e170f | e5b68c40 | the installed bytes |
| two superseded inputs | ga-e0t1.18 gc-a; m5-inputs/city.toml | moved in place to ga-bebv gc-a; m10-inputs/city.toml | M10 no longer references them; appending both left only 274 spare frame bytes |
| tree rigs/gascity/.git/objects | 98e871c4 | aed766a6 | the sequence 16 accepted digest (the S1 build-source fetch) |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M9 | fresh, `reports/m10` | the M6 to M9 pattern |

Everything else is unchanged:
- every other input, tree, link and integrity file;
- the providers (Core pins the wrappers, not city.toml);
- the repositories and the cache.

The superseded files stay on disk, unchanged.

**Counts and frame.** 696 inputs, 49 trees, 23 links and 4 providers, as in M9. The computed frame is 130,445
of 131,072 bytes, which leaves 627 spare; M9 computed 633. `FRAME_FLOOR` stays 512. The suspension record is
the one sequence 16 accepted (6d89f537). The watchdog image stays 69d00186: the surviving dolt watchdog still
maps it, checked on 2026-09-27.

## The prerequisite (prereqs_m10.py)

Core's metadata-only adoption refuses unless every managed file is already installed and its previous bytes
are backed up, so the new city.toml goes live first, as M5's did. There are two steps, each run once:
- **`inputs`** makes no live change. It derives the bytes and runs two checks:
  - `city_structure` requires that the new document equals the old one except for the two provider tables
    and the eight appended patches. It also refuses any unrestricted flag in the reviewed fragments.
  - `selections` requires that every option a claude- or codex-family selection names is still offered. It
    covers city.toml, the three managed fragments and every agent.toml.

  It then writes `reports/m10-inputs/city.toml` and proves the M6 backup.
- **`city`** makes the live change: a fresh temporary file in the city directory, then an atomic rename over
  city.toml.

Every step waits for a natural reconciler slot and proves that the host and dolt-aware scope equal the
sequence 16 accepted epoch and that the suspension record is unchanged. It writes an intent and records the
exact postcondition. An interrupted step can only `resume`.

`rollback` restores 4f7e170f from the M6 backup. It runs only while M9 is installed and no M10 executor window
may be open.

## The capture

`capture_m10.py` is `capture_m9.py` with the reference moved to the sequence 16 accepted closure
(`/var/tmp/ga-bebv-seq16-20260927/postflight2.json` 99905158, 741 pins, 29 trees), as M7 used sequence 15's.
- `pin_changes` admits exactly one pair: city.toml 4f7e170f to e5b68c40, with mode, uid and gid unchanged.
- `target()` adds the NEW_INPUTS.
- The bodies of `pin_changes`, `cache_drift`, `tree_drift` and `target` are M9's; a test checks that.

**Read-only dry probe (2026-09-27, before the prerequisite).** Run through `systemd-run --user`, it found:
- the host and scope equal to sequence 16;
- file drift only on city.toml, and `pin_changes` missing only city.toml, both as expected before the
  prerequisite;
- no tree drift;
- only the known `954ed149…/.git` cache bookkeeping entry;
- the protected trees and the suspension equal;
- every repository and the canonical checkout exact.

The executor sources are byte-identical to M9. The recorder, the gate extract and the gate prompts are rebound
to `reports/m10`. The SOURCE_PASS extract also reports three things: the city-config entry, the two
superseded input moves and the object tree.

## Tests

`test_m10.py` has 44 tests; 42 run before the capture. They cover:
- the predecessor, build, receipt and sequence 16 bytes;
- the generator reproducing the probed bytes;
- the structure and selection checks and their refusals;
- the work_dir_roots;
- the probe evidence;
- Core's successor and metadata-only rules, read from the f45a6262 reproduction source;
- counts, frame and the exact field delta;
- the drift and predecessor refusals;
- the capture target, pin-change and cache rules;
- source identity with M9, and the capture's M10 names.

## Run order and quiescence

1. **Review.** Get two SOURCE_PASS reviews of this package, which binds `prereqs_m10.py`, `make_city.py`,
   the fragments, the capture and the builder.
2. **Prerequisite.** Run `prereqs_m10.py C inputs`, then `prereqs_m10.py C city`, where C is the
   `manifest_candidate.py` digest.
3. **Capture.** Run `capture_m10.py C`.
4. **Binding.** Pin `BASELINE_SHA`, write `source-pins.json`, then get two binding reviews.
5. **Executor.** Run `prepare`, then SOURCE_PASS ×2, then `pause`, then `observe`, then PAIRING_PASS ×2,
   then `paired`, then `verify`, then COMMIT_PASS ×2, then `restore-accepted`.
6. **Inspector.** Rebuild the pinned platform inspector against the M10 manifest and the f45a6262 source, and
   require zero drift.

From the prerequisite until `restore-accepted`:
- no gc, no `workflow.py`, no Bead write, and no git in pinned repositories;
- no edit of the package worktree while a review runs;
- nothing resumes a city agent or reruns provisioning.

## Review and binding (2026-09-27)

**r1 `2d6646d5`** received two independent SOURCE_PASS verdicts with no must_fix. The should_fix items were:
- **Wording** (A 1, B 2, B 8). The unsafe flag names above are corrected here and in `make_city.py`.
- **Selections is stricter than Core** (A 2). `selections()` treats a by_key child key as replacing its
  parent's choice list, while Core merges the choices by value. So it can refuse falsely but never admit a
  withdrawn choice. It held against the live files.
- **Not digest-pinned** (A 3, B 7). `make_city.py` is not pinned by digest. Its output is bound twice to
  CITY_NEW.
- **Interrupted steps** (A 4, B 4, B 5).
  - An `inputs` step interrupted after its intent refuses on rerun and on resume. It touches no live state;
    recovery is by hand.
  - A `city` step interrupted between the temporary write and the rename leaves
    `.city.toml.ga-bebv-m10.forward.tmp`. Rollback lists it but does not remove it; inspect it by hand. The
    city root is neither a capture tree nor a protected tree.
- **No control-flow tests** (B 6). The prerequisite's control flow has no interruption-matrix tests.
- **Core residual** (B 9), for ga-5eix. `ContainedIn` accepts a root itself, so a Bead can name a whole
  worktree root as its work_dir. Every root already lies inside that lane's existing write grant.

The code items apply to a successor prerequisite; this one already ran as reviewed.

**Live results, all from `2d6646d5`, in the supervisor namespaces:**
- **`prereqs_m10.py 5ebd17c0 inputs`.** Record `reports/m10-inputs/prereq-inputs.json`.
- **`prereqs_m10.py 5ebd17c0 city`.** The live city.toml is e5b68c40, and no temporary file is left.
- **`capture_m10.py 5ebd17c0`.** `reports/m10-capture/baseline.json` is `fc9ee176`:
  - zero drifts and 769 pins over 49 trees;
  - pin changes exactly city.toml;
  - cache bookkeeping only the known `954ed149…/.git` entry.

The binding commit pins `BASELINE_SHA` (`manifest_candidate.py` moves from `5ebd17c0` to the digest in
`source-pins.json`), adds `source-pins.json`, and fixes the wording above. No executed code changed.

## Stop conditions

Stop on any of these:
- any refusal;
- host epoch drift;
- drift outside the one allowed pin change;
- a structure or selection refusal;
- an ambiguous result;
- new privilege;
- a pinentry prompt.

After the city step, a stop before M10 installs is answered with `rollback`. After `paired`, the executor
recoveries apply unchanged.
