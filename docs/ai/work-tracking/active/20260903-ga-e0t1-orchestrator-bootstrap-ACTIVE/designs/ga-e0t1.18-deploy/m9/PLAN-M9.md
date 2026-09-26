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

## The complete delta (M8 → M9)

| Field | M8 | M9 | Why |
| --- | --- | --- | --- |
| `integrity.providers`, appended | claude-native, codex, `claude` (signing wrapper `9df9ea34`) | plus `claude` at `bin/gct-claude-candidate-worker` `e4442971`, `version_args ["--version"]`, version `gct-claude-candidate-worker 1 dependencies_sha256=a35dd413…` | P10 needs the candidate profile's provider pinned. Core keys pins by (name, path), so the two `claude` wrappers coexist (the f3856bd1 provider-pin fix). |
| `metadata.inputs`, appended | none | `bin/gct-claude-candidate-worker` `e4442971` (0755) and `lib/gct_claude_candidate_worker.py` `97554586` (0644) | the signing wrapper's bin and lib are pinned the same way |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M8 | fresh, `reports/m9` | the M6 to M8 pattern |

Everything else is unchanged:
- the Core image, the writer, `previous_sha256` (`fce2e9a0`), `backup_path` (the ga-e0t1.18 `gc-b`) and the
  activation. These already carry the values Core's `validateSuccessor` requires;
- every integrity file, repository, tree and link, and the managed files;
- the cache.

**Why the version pin covers more than the wrapper.** The wrapper's version line is the digest of its launch
dependencies: the pinned claude CLI, the candidate control policy (`a3eda916`) and the executed launch
sources. Core's provider inspection runs `--version` and compares the whole line, so those bytes are
covered transitively.

**Counts and frame.** 694 inputs, 49 trees, 23 links and 4 providers. The frame is 130,069 of 131,072 bytes,
with 1,003 spare (M8 left 1,763, and M9's additions cost 760). `FRAME_FLOOR` is 512. There is no new broker
receipt: the Core image did not change, so the sequence 15 receipt `1cca491d` still binds it.

## The capture

`capture_m9.py` is `capture_m8.py` with each successor name moved by one. Its reference is the frozen M8
baseline (`reports/m8-capture/baseline.json` `36ec0b4e`, 763 pins, 49 trees), which the M8 executor accepted.

`pin_changes` admits exactly one reviewed pair since that baseline: the P9 worker receipt
`.gc/runtime/provisioning/receipt.json`, `23eeb222` to `6bf20a71`. Its mode, uid and gid must be unchanged.
`target()` adds the two wrapper inputs. The bodies of `pin_changes`, `cache_drift` and `tree_drift` are M8's,
and a test checks that.

The executor sources are byte-identical to M7 and M8. The recorder, the gate extract and the gate prompts are
rebound to `reports/m9`. The SOURCE_PASS extract also reports the providers and whether the candidate pin is
exact.

**Read-only dry probe (2026-09-26, scratchpad `m9_dry_probe.py`).**
- The host and scope equal the M8 baseline.
- There is no target file drift and no tree drift.
- `pin_changes` found exactly the P9 receipt, with no problems.
- The protected trees and the suspension are equal.
- The cache shows only the known `954ed149…/.git` bookkeeping entry.

**Tests.** `test_m9.py` has 29 tests, 27 of which run before the capture. They cover:
- the live bytes and modes;
- the wrapper's live `--version` line;
- the rendered `claude-candidate` provider naming this wrapper;
- Core's (name, path) keying;
- the successor rules;
- the exact delta;
- the counts and frame;
- the drift refusals and predecessor refusals, including a second candidate pin, a changed signing pin and
  a pre-pinned wrapper input;
- the pin-change and cache rules;
- source identity with M8.

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
