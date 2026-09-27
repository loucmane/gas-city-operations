# M11: adopt the Template Claude candidate lane into the platform metadata (gct-oak5)

On 2026-09-27 the operator decided "Prepare and apply" for the Template lane. The gct-oak5 activation
(`9936810e`, two reviews) is live. The M10 inspector (`e1bb4fc9`), run read-only after it, reports exactly three
drifts:
- `files[rig-permissions.json]`: `1225b7c5` → `0b0e6a87`;
- `files[rig-permissions.toml]`: `df688a29` → `df9c82d0`;
- `managed_files[city-config]`: `e5b68c40` → `b0eeb168`.

M11 is the M8 pattern (adopting a lane activation with the Core unchanged) combined with the M10 city-config pattern
and the M9 provider pattern, over the installed M10 manifest (`2b902a83`).

## The complete delta (M10 → M11)

| Field | M10 | M11 | Why |
| --- | --- | --- | --- |
| integrity files and inputs `rig-permissions.json` / `.toml` | `1225b7c5` / `df688a29` | `0b0e6a87` / `df9c82d0` | activation postimages (M8 pattern) |
| city-config source, sha256 | `m10-inputs/city.toml`, `e5b68c40` | `m11-inputs/city.toml`, `b0eeb168` | the installed city.toml |
| city-config previous_sha256, backup_path | `4f7e170f`, `m6-inputs/city.toml.before` | `e5b68c40`, `m10-inputs/city.toml` | Core's successor rule: previous is M10's sha256; the M10 source holds exactly those bytes and is already an input |
| the installed city.toml input | `e5b68c40` | `b0eeb168` | |
| `previous_sha256` / `backup_path` | `fce2e9a0` / ga-e0t1.18 `gc-b` | `207a78e2` / ga-bebv `gc-b` | Core `validateSuccessor`: previous must equal the predecessor core (the image is unchanged) |
| `activation.previous_commit` | `deefb98b` | `f45a6262` | must equal the predecessor's `expected_commit` |
| tree `/home/loucmane/gas-city-template/.git` | `06ebb42b` | `9b74eda4` | the gct-mbg6 worktree registration, the PR 72 fetch and the checkout |
| tree `/home/loucmane/gas-city-template/templates/claude` | none | `aff9b9b3` (8 entries) | covers the Template policy and provider template (see below) |
| four `templates/claude/*` inputs (signing and Operations candidate policy and provider) | pinned | removed | the tree covers them, strictly |
| inputs: the Template wrapper `229d3355` (0755) and library `17f54bca` (0644) | none | moved in place into the two superseded ga-e0t1.15 `b2760ea4` image rows | the provider's version dependencies must be mounted |
| integrity providers | 4 | 5: `claude` at `bin/gct-claude-template-candidate-worker`, `229d3355`, version `…dependencies_sha256=3cd85706…` | P12's typed Template candidate receipt profile matches by (name, path) (M9 pattern) |
| integrity repositories | 7 | 8: `template-pr72-canonical` at `/home/loucmane/gas-city-template`, `3474abfa`, `allow_dirty` | r2: P12's `template_commit` must be a pinned repository commit |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M10 | fresh, `reports/m11` | the M6–M10 pattern |

Everything else is unchanged: the core image and writer, the managed files other than city-config, the existing
repositories (PR 71 stays pinned at `cfd353f3`), every other tree and link, and the cache. The suspension record is not a
manifest field: the capture and the executor bind it through `SUSPENSION_SHA` (`6d89f537` → `a3306567`; the window
lifecycle rewrote `updated_at`, and everything is still suspended). There is no new broker
receipt; sequence 16's `1108b724` still binds the image.

**Why a tree for `templates/claude`.** The Template wrapper's `--version` hashes seven dependencies:
- the Claude CLI, the policy, the wrapper, its library, the signing boundary, the subscription library and the
  provider template;
- Core's confined metadata writer mounts only pinned inputs and trees (`metadata_sandbox_linux.go` ro-binds
  `Inputs` then `Trees` at their own paths; a test asserts the source lines).

Four new inputs plus the provider row did not fit the 128 KiB request frame: M10 left 613 spare bytes and the
provider row alone costs about 580. One tree pin of `templates/claude` (seven regular files, nothing generated)
replaces the four existing inputs there and covers the two new files. It is also stricter: a file added in that
directory is drift. The wrapper and its library take over the two superseded ga-e0t1.15 image rows, which are
referenced nowhere else (a test checks). The same two libraries import only the stdlib modules M9 already pins.

**Counts and frame.** 692 inputs, 50 trees, 23 links, 5 providers, 8 repositories. The synthetic build's bound is
130,506 of 131,072 bytes, leaving 566 spare. `FRAME_FLOOR` is 256; only the fresh parents' device and inode vary at
`prepare`, by at most 72 bytes.

## The prerequisite and the capture

**`prereqs_m11.py C`.** It writes `reports/m11-inputs/city.toml` exactly once (O_EXCL, 0644) from the installed
`b0eeb168`, after proving the installed file and the M10 source. It makes no live change.

**`capture_m11.py C`.** It is generated from the reviewed `capture_m10.py` by count-asserted substitutions:
- **Reference.** The frozen M10 baseline (`reports/m10-capture/baseline.json` `fc9ee176`, 769 pins, 49 trees).
- **`pin_changes`.** Exactly four reviewed pairs:
  - the P11 receipt `c833908f` → `06a3f58a`;
  - `city.toml`;
  - the registry;
  - the fragment.
- **`tree_drift`.** It admits the Template `.git` change as an exact pair. It requires the new tree's pinned
  digest and every other tree exact.
- **Suspension.** The record may change only in `updated_at`: owner, group and mode are unchanged, and the city
  and all seven rigs are suspended.
- **Unchanged bodies.** `pin_changes` and `cache_drift` are M10's, byte for byte; a test checks.

**Read-only dry probe (2026-09-27, scratchpad `m11_dry_probe.py`, supervisor namespaces):**
- the host and scope equal the M10 baseline;
- pin changes are exactly the four pairs above;
- tree drift is only the Template `.git` (`06ebb42b` → `9b74eda4`);
- the cache shows only the known `954ed149…/.git` bookkeeping;
- the protected trees are equal, and there is no repository drift;
- the canonical checkout is at `3474abfa`.

The executor sources (`source_runtime`, `launch`, `metadata_executor`, `metadata_window`, `metadata_closure`) are
byte-identical to M10. The recorder, the gate extract and the gate prompts are rebound to `reports/m11` and
staging `gct-oak5-m11`. The extract adds `new_trees`, `removed_inputs_absent`, `template_provider` and
`integrity_files_changed`.

## Tests

`test_m11.py` has 26 cases passing and 2 skipped until the capture and the binding. They cover:
- the predecessor and live bytes;
- the Template lane files and the wrapper's live `--version`;
- the sequence 16 receipt;
- Core's successor, metadata-only and writer-mount rules, read from the `f45a6262` source;
- counts, frame and identity;
- the exact delta, including that every unchanged field is unchanged;
- that the superseded rows are unreferenced;
- eleven drift refusals and three predecessor refusals;
- the capture target, pin-change and tree rules;
- the capture's diff against M10;
- source identity and rebinding;
- the prerequisite.

## Run order and quiescence

1. **Review.** Get two SOURCE_PASS reviews of this package.
2. **Prerequisite.** Run `prereqs_m11.py C`, where C is the `manifest_candidate.py` digest.
3. **Capture.** Run `capture_m11.py C`.
4. **Binding.** Pin `BASELINE_SHA`, write `source-pins.json`, then get two binding reviews.
5. **Executor.** Run `prepare`, then SOURCE_PASS ×2, then `pause`, then `observe`, then PAIRING_PASS ×2, then
   `paired`, then `verify`, then COMMIT_PASS ×2, then `restore-accepted`.
6. **Inspector.** Rebind the M10 inspector to the M11 manifest and require zero drift.

**Quiescence** holds from the prerequisite until `restore-accepted`:
- no gc, no `workflow.py`, no Bead write;
- no git in any pinned repository (including the canonical Template and `gas-city-native`);
- no edit of the package worktree while a review runs;
- nothing resumes a rig, routes a Template Bead, or creates a worktree under the candidate root.

**Then P12**, bound to M11. It refreshes the worker receipt: `template_commit` and `member_heads[template]` move to
`3474abfa`, the permission revision moves to the activation's, and it publishes the typed Template candidate profile
(`signer_identity: "none"`, the Template launch-check path).

## r2 (answers the r1 reviews of `ce109302`: A SOURCE_PASS, B HOLD)

**B must_fix 1: the Template authority.**
- **The problem.** P12 moves the receipt's `template_commit` to `3474abfa`. Core's dispatch gate and
  `gc platform canary` refuse unless a pinned repository carries exactly that commit (`containsRepositoryCommit`).
  r1 kept only PR 71 at `cfd353f3`.
- **The fix.** M11 appends `{template-pr72-canonical, /home/loucmane/gas-city-template, 3474abfa,
  allow_dirty: true}`.
  - `HEAD` is inspected exactly, and the `.git` is a pinned tree.
  - `allow_dirty` only skips the status check, because of the two known untracked directories.
- **Why not a clean authority worktree.** A separate clean worktree would be stronger, but its tree rows do not fit
  the frame.
- **The test.** A test binds this authority to the P12 commit and to the Core source lines.

**Should_fix taken:**
- **The reference guard** (A 1). `assemble()` now computes it from the untouched predecessor. It includes every
  managed-file backup, integrity file and repository path, and exempts only the two predecessor backups M11
  replaces.
- **The wrapper's `--version` test** (A 2, B 1) runs in the writer's environment (`HOME=/nonexistent`,
  `PATH=/usr/bin:/bin`) and reports the pinned version.
  - All seven dependencies are mounted in the confined writer.
  - The first in-sandbox proof is `prepare`'s pinned-integrity inspection. A mismatch there fails closed before any
    mutation, but it consumes that window.
- **Wording** (A 3-4, B 3-4).
  - The suspension record is a capture binding, not a manifest field.
  - The moved rows are the ga-e0t1.18 `gc-b`, the M6 city backup and the two ga-e0t1.15 images.
  - The inspector (`InspectIntegrity`) does not examine metadata trees or inputs. The Template `.git` change and the
    input-to-tree swap are proven by the capture and the writer only, so "zero drift" after the inspector rebind
    does not cover them.
- **Carried.** The tree root mode stays 0755 in two places (B 2); the capture and the executor both check it
  live.

`test_m11.py`: 27 pass and 2 are skipped until the capture and the binding.

## Binding (2026-09-27)

**r2 `04ec50be` received two SOURCE_PASS verdicts with no must_fix.** Then, from a clean worktree, in the supervisor
namespaces, with candidate C = `44786b31`:
- **`prereqs_m11.py C`.** It wrote `reports/m11-inputs/city.toml` (`b0eeb168`, 0644). Quiescence began.
- **`capture_m11.py C`.** `reports/m11-capture/baseline.json` is `4000f7f3`:
  - zero drifts;
  - pin changes exactly the four admitted pairs;
  - cache bookkeeping only the known `954ed149…/.git` entry.
- **Frame.** The build against the frozen baseline leaves 566 spare bytes, the same as the synthetic build.

**The binding commit:**
- `manifest_candidate.py` pins `BASELINE_SHA`, which moves its digest from `44786b31` to `f933ca57`.
- `source-pins.json` is added.
- It applies the r2 wording items below.
- All 29 tests pass, including the frozen-baseline build and the source inventory.

**r2 review items taken into the binding (no must_fix):**
- **`allow_dirty` is required in the writer** (B 1). The working tree is not mounted in the confined writer, so
  `git status` there would list every unmounted tracked file as deleted. It must never be turned off to "tighten"
  the pin. It skips the status check entirely (A 2): a modified tracked file elsewhere in the canonical checkout is
  not detected by this pin. The executed lane bytes are covered by the provider pins and the wrapper's dependency
  digest.
- **The checkout is now coupled to the metadata** (A 1, B 4). Core's dispatch gate runs the full integrity
  inspection on every managed-product route and canary. So from M11 on, any HEAD move in
  `/home/loucmane/gas-city-template` refuses all managed dispatch until a new metadata successor is installed. This
  fails closed. A later Template merge therefore needs its own successor, as this one does. The P12 and handover
  packages must not move the canonical checkout.
- **Tests and quiescence** (A 3, B 2). The two tests that run read-only git in the canonical Template skip those
  calls once `BASELINE_SHA` is pinned. The capture's `checkout_state` is the quiescent proof of HEAD `3474abfa`.
- **Capture coverage of the new pin** (A 4). The capture iterates the installed M10 repositories. The new canonical
  pin is covered by `checkout_state`: HEAD `3474abfa` and the exact untracked set.
- **Wording** (B 3). The docstring now says r2 appends one repository row.

## Stop conditions

Stop on any of these:
- any refusal;
- host epoch drift;
- drift outside the admitted changes;
- an ambiguous result;
- new privilege;
- a pinentry prompt.

The executor recoveries are unchanged.
