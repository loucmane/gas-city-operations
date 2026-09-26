# M8: adopt the Operations candidate lane into the platform metadata

On 2026-09-26 the operator decided "Activate, then M8". The ga-6utp r12 activation (`21039a1c`, two reviews)
is live. It rewrote two files that the installed M7 manifest (`4bec5ef1`) pins as both integrity files and
inputs:
- **`managed/rig-permissions.json`:** `d22cf4c1` becomes `1225b7c5`, with the candidate registry record appended;
- **`managed/rig-permissions.toml`:** `cba75f87` becomes `df688a29`, with the `claude-candidate` provider and the
  agent patch.

The M7 inspector (`578c7fb2`) reports exactly these two drifts. Until M8 is installed, Core's managed dispatch
gate refuses, which fails closed. The activation also added `agents/operations-candidate-worker/`
(`agent.toml` `ba01f223`, `prompt.template.md` `9c27418c`). M7 does not cover it, and M8 pins both files.
`city.toml` is unchanged (`4f7e170f`).

## The complete delta (M7 → M8)

| Field | M7 | M8 | Why |
| --- | --- | --- | --- |
| integrity files and inputs `rig-permissions.json` | `d22cf4c1` | `1225b7c5` | activation postimage |
| integrity files and inputs `rig-permissions.toml` | `cba75f87` | `df688a29` | activation postimage |
| inputs, appended | none | `agents/operations-candidate-worker/agent.toml` `ba01f223` and `prompt.template.md` `9c27418c`, both 0644 | an edit to the suspended, unscoped agent definition becomes integrity drift |
| `previous_sha256` / `backup_path` | `b2760ea4` / ga-e0t1.15 `gc-b` | `fce2e9a0` / `/var/tmp/ga-e0t1.18-build-20260926/gc-b` (a new input) | Core `validateSuccessor`: `previous_sha256` must equal the predecessor core |
| `activation.previous_commit` | `9faeabc2` | `deefb98b` | must equal the predecessor's `expected_commit` |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M7 | fresh, `reports/m8` | the M6 and M7 pattern |

The core image, the writer, the providers, the repositories, every tree and link, the managed files and the
cache are unchanged. Counts: 692 inputs, 49 trees, 23 links. The frame is 129,309 of 131,072 bytes, with 1,763
spare. `FRAME_FLOOR` is 1,024 (M6 and M7 used 2,048). The bound is computed exactly, and the three new inputs
cost about 520 bytes. There is no new broker receipt: the Core image did not change, so the sequence 15 receipt
`1cca491d` still binds it.

## The capture

`capture_m8.py` is `capture_m7.py` with one change: its reference is the frozen M7 baseline
(`reports/m7-capture/baseline.json` `28d65524`, 760 pins, 49 trees), which the M7 executor accepted.

`pin_changes` admits exactly three reviewed before-to-after pairs since that baseline. Mode, uid and gid must
be unchanged; the size may change:
- the P8 worker receipt `.gc/runtime/provisioning/receipt.json`, `7cf59ab9` to `23eeb222`;
- the registry, `d22cf4c1` to `1225b7c5`;
- the fragment, `cba75f87` to `df688a29`.

Each allowed change must actually have happened. Every other M7-baseline pin, tree, protected tree and link,
the scope, the suspension record `5c98be4a` and the host epoch must be exact. The cache must be exact apart
from the Git bookkeeping times that `cache_drift` admits.

The executor sources are byte-identical to M7, including `metadata_closure.py` with `WATCHDOG_IMAGE` 69d00186.
The recorder and the gate prompts are rebound to `reports/m8`.

**Read-only dry probe (2026-09-26, scratchpad `m8_dry_probe.py`).** The host and scope equal the M7 baseline.
There is no target file drift. `pin_changes` found exactly the three allowed pairs, with no problems. There is
no tree drift, the protected trees and suspension are equal, and the cache shows only the known
`954ed149…/.git` bookkeeping entry.

## Run order and quiescence

This is M7's order, unchanged:
1. **Capture.** Run `capture_m8.py C`.
2. **Binding.** Pin `BASELINE_SHA`, write `source-pins.json`, then get two binding reviews.
3. **Executor.** Run `prepare`, then SOURCE_PASS ×2, then `pause`, then `observe`, then PAIRING_PASS ×2,
   then `paired`, then `verify`, then COMMIT_PASS ×2, then `restore-accepted`.

From the capture until `restore-accepted`: no gc, no `workflow.py`, no Bead write, no git in pinned
repositories, and no edit of the package worktree while a review runs.

**Then P9.** The activation reload moved the permission revision from `2113693e` to `83c41af6`. The signing-lane
receipt `23eeb222` pins the old revision, so a P9 refresh follows, bound to M8.

## Stop conditions

Stop on any of these:
- any refusal;
- host epoch drift;
- drift outside the three allowed pin changes;
- an ambiguous result;
- new privilege;
- a pinentry prompt.

The executor recoveries are unchanged.
