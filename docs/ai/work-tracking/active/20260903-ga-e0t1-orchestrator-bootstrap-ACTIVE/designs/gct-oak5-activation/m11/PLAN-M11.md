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
| suspension record | `6d89f537` | `a3306567` | the gct-mbg6 window lifecycle rewrote `updated_at`; everything is still suspended |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M10 | fresh, `reports/m11` | the M6–M10 pattern |

Everything else is unchanged: the core image and writer, the managed files other than city-config, the repositories
(the last authority stays PR 71 at `cfd353f3`), every other tree and link, and the cache. There is no new broker
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

**Counts and frame.** 692 inputs, 50 trees, 23 links, 5 providers. The synthetic build's bound is 130,358 of
131,072 bytes, leaving 714 spare. `FRAME_FLOOR` is 256; only the fresh parents' device and inode vary at
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

## Stop conditions

Stop on any of these:
- any refusal;
- host epoch drift;
- drift outside the admitted changes;
- an ambiguous result;
- new privilege;
- a pinentry prompt.

The executor recoveries are unchanged.
