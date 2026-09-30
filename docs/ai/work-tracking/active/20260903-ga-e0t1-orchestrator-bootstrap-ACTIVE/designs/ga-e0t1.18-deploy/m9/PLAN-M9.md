# M9: pin the Operations candidate provider wrapper in the platform metadata

This is the first step of the first candidate window's RECEIPT stage (ga-cw-first-window PLAN step 2, gct-lagl
HANDOFF 2.8). The typed candidate receipt profile (P10) names the provider the resolved
`gascity/operations-candidate-worker` identity runs. That is the `claude-candidate` provider, which executes
`/home/loucmane/gas-city-template/bin/gct-claude-candidate-worker`.

Core `deefb98b` checks every provisioning-receipt profile's provider against `integrity.providers`, keyed by
(name, path), in two places:
- the managed dispatch gate;
- its live-environment observer, which loops over *all* receipt profiles.

So a receipt that carries the candidate profile before its wrapper is pinned would put the signing lane's
observation at risk too. M8 review A (should_fix 1) required this pin first. The dispatch gate is not active
for the `gascity` rig today, because no `managed_product` is set, so M9 is ordering discipline, not an unblock.

**Wider blast radius once pinned (r1 review B should_fix 3).** After M9, any drift in the four candidate files
or the wrapper's version line makes `InspectIntegrity` report drift for the whole manifest. That blocks the
dispatch gate's live observation for every profile, the signing lane included, as any pinned file already
does. It also blocks the next metadata successor's writer. Drift labels are `providers[claude].*` for both
`claude` pins, so tell the two apart by the Expected value (sha256 or version line) (r1 review B should_fix 1).

## The complete delta (M8 → M9)

| Field | M8 | M9 | Why |
| --- | --- | --- | --- |
| `integrity.providers`, appended | claude-native, codex, `claude` (signing wrapper `9df9ea34`) | plus `claude` at `bin/gct-claude-candidate-worker` `e4442971`, `version_args ["--version"]`, version `gct-claude-candidate-worker 1 dependencies_sha256=a35dd413…` | P10 needs the candidate profile's provider pinned. Core keys pins by (name, path), so the two `claude` wrappers coexist (the f3856bd1 provider-pin fix). |
| `metadata.inputs`, appended | none | `bin/gct-claude-candidate-worker` `e4442971` (0755), `lib/gct_claude_candidate_worker.py` `97554586`, `templates/claude/candidate-control-policy.json` `a3eda916` and `templates/claude/candidate-provider.toml` `dea301a4` (0644) | the signing wrapper's bin, lib, control policy and provider.toml are pinned the same way, and the confined writer can only read inputs (below) |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M8 | fresh, `reports/m9` | the M6 to M8 pattern |

Everything else is unchanged:
- the Core image, the writer, `previous_sha256` (`fce2e9a0`), `backup_path` (the ga-e0t1.18 `gc-b`) and the
  activation. These already carry the values Core's `validateSuccessor` requires;
- every integrity file, repository, tree and link, and the managed files;
- the cache.

**Every version dependency is an input (r2, answering r1 review B must_fix 1).** The wrapper's version line is
the digest of seven files:
- the claude CLI;
- the candidate control policy;
- the candidate bin and lib;
- the signing boundary lib;
- the subscription lib;
- `candidate-provider.toml`.

Core runs each provider's `--version` inside the confined metadata writer, after `--clearenv`, and the writer
mounts only the exact inputs and trees. r1 pinned only the bin and lib. The policy and `candidate-provider.toml`
would then have been unreadable in the writer, which would have refused at PREPARE with provider version drift.
r2 pins all four candidate files. The other three dependencies and `/usr/bin/python3.12` are already M8 inputs.
`test_every_version_dependency_is_visible_in_the_confined_writer` reads the dependency set from the wrapper's own
launch configuration and checks it against the built inputs. The `--version` test also runs with an empty
environment and must finish in under 2.5 s; Core allows 5 s.

**Counts and frame.** 696 inputs, 49 trees, 23 links and 4 providers. The frame is 130,439 of 131,072 bytes,
with 633 spare: M8 left 1,763, and M9's additions cost 1,130. `FRAME_FLOOR` is 512; M8's floor was 1,024.
Relaxing the local floor is recorded for review (r1 review A should_fix 6). Core's 131,072 limit is
unchanged. The capture fixes the host fields to the M8 epoch, so their width cannot grow at prepare. There is no
new broker receipt: the Core image did not change, so the sequence 15 receipt `1cca491d` still binds it.

## The capture

`capture_m9.py` is `capture_m8.py` with each successor name moved by one. Its reference is the frozen M8
baseline (`reports/m8-capture/baseline.json` `36ec0b4e`, 763 pins, 49 trees), which the M8 executor accepted.

`pin_changes` admits exactly one reviewed pair since that baseline: the P9 worker receipt
`.gc/runtime/provisioning/receipt.json`, `23eeb222` to `6bf20a71`. Its mode, uid and gid must be unchanged.
`target()` adds the four wrapper inputs. The bodies of `pin_changes`, `cache_drift` and `tree_drift` are M8's,
and a test checks that.

The executor sources are byte-identical to M7 (`../s3`) and M8 (`../m8`). The recorder, the gate extract and the gate prompts are
rebound to `reports/m9`. The SOURCE_PASS extract also reports the providers and whether the candidate pin is
exact.

**Read-only dry probe (2026-09-26, scratchpad `m9_dry_probe.py`).**
- The host and scope equal the M8 baseline.
- There is no target file drift and no tree drift.
- `pin_changes` found exactly the P9 receipt, with no problems.
- The protected trees and the suspension are equal.
- The cache shows only the known `954ed149…/.git` bookkeeping entry.

**Tests.** `test_m9.py` has 32 tests, 30 of which run before the capture. They cover:
- the live bytes and modes;
- the wrapper's live `--version` line, in an empty environment too, and its timing;
- every version dependency being an exact input;
- the rendered `claude-candidate` provider naming this wrapper;
- Core's (name, path) keying;
- the successor rules;
- the exact delta;
- the counts and frame;
- the drift refusals and predecessor refusals, including:
  - a second candidate pin;
  - a changed signing pin;
  - a pre-pinned wrapper input or policy;
  - a codex pin repointed at the wrapper;
- the pin-change and cache rules;
- source identity with M8, and every M9 name in the capture's `main()`.

## Run order and quiescence

This is M8's order, unchanged:
1. **Capture.** Run `capture_m9.py C`.
2. **Binding.** Pin `BASELINE_SHA`, write `source-pins.json`, then get two binding reviews.
3. **Executor.** Run `prepare`, then SOURCE_PASS ×2, then `pause`, then `observe`, then PAIRING_PASS ×2,
   then `paired`, then `verify`, then COMMIT_PASS ×2, then `restore-accepted`.
4. **Inspector.** Rebuild the pinned platform inspector against the M9 manifest and require zero drift, as
   after M8.

From the capture until `restore-accepted`:
- no gc, no `workflow.py`, no Bead write, and no git in pinned repositories;
- no edit of the package worktree while a review runs;
- nothing resumes or unsuspends `operations-candidate-worker`, creates a worktree under the candidate root,
  or reruns provisioning.

**Then P10.** This is the typed candidate receipt profile under the resolved identity
`gascity/operations-candidate-worker`, as a separate reviewed package over P9's receipt.

## Review history

- **r1 `95b73ca1`.** Review A gave SOURCE_PASS with should_fix items. Review B held on must_fix 1: two version
  dependencies were not visible to the confined writer.
- **r2** answers both reviews:
  - B must_fix 1: the two added inputs and the dependency-visibility test;
  - A should_fix 1: the unreachable key-collision check is removed, and the remaining check is tested;
  - A should_fix 2: explicit M9 names in `main()`;
  - A should_fix 3 and 5: wording;
  - A should_fix 4: timing;
  - B should_fix 1 and 3: drift labels and blast radius;
  - B should_fix 2: the frame is recomputed.
- **B should_fix 4.** The reviewers cite Core from `/var/tmp/ga-e0t1.18-build-20260926/repro-source` at
  `deefb98b`. The rig checkout is not at that commit, and its tree is not evidence for the deployed Core.

## Binding step (r3, 2026-09-26): live results

r2 `9e5eb6aa` received two independent SOURCE_PASS verdicts with no must_fix. The capture then ran once in the
supervisor namespaces with candidate `C` = `0510e94d` at `9e5eb6aa`, from a clean worktree:
- **Baseline.** `reports/m9-capture/baseline.json` is `15d39514`, with zero drifts and 767 pins.
- **Pin changes.** Exactly the P9 receipt.
- **Cache.** The only bookkeeping entry is the known `954ed149…/.git` (mtime and ctime).
- **The four new wrapper pins.** Each is uid and gid 1000 with the reviewed digest and mode: 0755 for the bin
  and 0644 for the rest (r2 review B should_fix 2, checked by hand).

The r3 changes:
- `manifest_candidate.py` pins `BASELINE_SHA`, and its frame comment now carries the r2 figures (r2 A 1, B 1).
  Its digest moves from `0510e94d` to `09a0b16f`.
- `source-pins.json` is new, at `ddad8b1f`.
- `test_m9.py` gains a comment on the shared `/bin/sh` and stdlib coverage (r2 A 3, B 3).
- All 32 tests pass, including the build against the frozen baseline.

`capture_m9.py` ran as reviewed, so its docstring keeps the r2 wording "the candidate wrapper and its launch
module" (r2 A 2); its `target()` pins all four files. The writer's added `--version` hashing time is
informational: M8 observe took 18.5 s against a 36 s probe limit (r2 B 4).

Before the capture, the P10 diagnostics were built into their final roots, so nothing runs git during the
quiescence:
- the candidate composition `53450168`, reproduced exactly;
- the preflight `c6dd9ebb`, with extraction `a30af307`.

## Accepted (2026-09-26)

The executor ran from `a53dc219`, with two independent reviews at each gate:
- **prepare.** Package `808c7fe5`, with 619 spare frame bytes.
- **SOURCE_PASS.**
- **pause.** Window `7af77a6c`.
- **observe.** The dry run passed, including the candidate wrapper's version check inside the confined writer.
- **PAIRING_PASS.**
- **paired.** `result=installed`, manifest self digest `7f7c5dbe`.
- **verify.**
- **COMMIT_PASS.**
- **restore-accepted.** The timer was restored.

The accepted pair is:
- the live manifest file `5a29dc59`;
- the receipt file `4c19802f`, self `5ad49de0`;
- the acceptance `959e3137`.

`inspector/make_inspector_m9.py` rebinds the M8 inspector: the manifest pin moves from `63820eac` to `5a29dc59`,
and the root is fresh. It was built offline as `9e29e45d`, and one read-only live run returned ok with zero
drifts.

## Stop conditions

Stop on any of these:
- any refusal;
- host epoch drift;
- drift outside the one allowed pin change;
- a wrapper version other than the pinned line;
- an ambiguous result;
- new privilege;
- a pinentry prompt.

The executor recoveries are unchanged.
