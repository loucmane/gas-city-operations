# ga-1aa1 WORKTREE preparation package r1

## Outcome and permitted effect

Create only the fresh candidate workspace and its two exact local deny/unsigned
policy files. This package does not route ga-1aa1, claim it, launch a provider,
resume a rig, install a receipt, change city configuration or implement product
code. A successful result is preparation only.

Wrapper:
`docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-1aa1-image-tool-r3/operator/WORKTREE.sh`

Execute once through the existing Gas City job runner, only on the exact clean
signed package commit after two independent bound SOURCE_PASS reviews.

## Frozen bindings and provenance

- Bead ga-1aa1 is open, unassigned and unrouted in the gascity store.
- Worker base: signed `5b981444bf7d687c0367da4ee3d111ff4b443ead`.
- New branch: `codex/ga-1aa1-handover-image-r3`.
- New worktree: `/home/loucmane/gas-city-ops-candidate-worktrees/ga-1aa1`.
- New admin: `/home/loucmane/gas-city-ops/.git/worktrees/ga-1aa1`.
- Create-only result root: `/var/tmp/ga-1aa1-worktree-20260929-r1`.
- Executor SHA-256:
  `5ed81a4aa9e73268f2c4128077d1c2f1e88018ec6ba02516f1da4a995a1546ea`.
- Input container SHA-256:
  `f5ef43f27142f1571c9f7a314d98f6e34b524769b0932bd55cdc1310d31bde52`.

`worktree.py` is the exact previous no-atime workspace creator
(`ga-e0t1.20-astra-bootstrap/worktree-noatime.py`,
SHA-256 `21a3e4270ab05c68cf1ae9795f42e2302ed3c9fa5bd839c6467de879d941ec6f`)
with only task, output-root, base and branch rebinding. No function body or check
changes beyond those literal identities. The wrapper is the prior accepted
`ga-e0t1-20-astra-entry/operator/WORKTREE-R3.sh`
(SHA-256 `da48f232fe1a9cdcfd37ad08ece818fdc963547eb0512babe34bb73b7d8fefae`)
with package, output root, executor filename and executor digest rebound.
Tests enforce byte-exact reconstruction of both predecessors.

The input container contains only the one consumed deny-only policy. Its decoded
bytes remain exactly `ea2645785163d3f9b6d5ddfe8a08c5ff40b97a8cb1739bca94dd4b2844f15773`.
The historical task name in its comment is retained to preserve those bytes; it
grants no authority. Old city/configuration snapshots are not copied into this
preparation-only container.

## Preserved safeguards

Fresh root, branch, worktree and admin required; exact verified base signature;
no Git links, attributes or content drivers; registered linked-worktree validation;
exact managed Codex and installer/policy assets; no-atime protected file reads;
installer confined with read-only host and writable new rules/owned scratch only;
exact two-file inventory; unchanged global default rules and provider/installer
postchecks; create-only intent/result evidence. Nothing weakens the separately
authorized common-Git baseline exception or worker write protection.

The wrapper keeps exact signed clean HEAD admission through the runner and its
own HEAD/clean check, no stdin, required umask, source-only launcher and consumed
root refusal. Existing job-runner and source-launch bytes are not modified.

## Failure disposition

Any refusal stops. A failure after intent creation may leave the worktree/branch
and local rules partially materialized; preserve them and classify from exact
evidence. Do not replay this root or remove/reset anything. A zero wrapper exit
is not sufficient: inspect result.json, wrapper log and runner final record.
The runner halts after the job. No subsequent job is implied.

## Offline verification on 2026-09-29

- New package module: 15 passed, no skips.
- Inherited no-atime and entry modules: 8 passed, no skips.
- Shell syntax checked without execution.
- Exact live policy, installer and managed Codex bytes matched read-only.
- Root, worktree and admin absent on the preparatory read.
- Worker base signature G; whitespace check clean.
- These are preparation/source proofs, not host/runtime worker acceptance.
- No full adapter suite repeated: no adapter/runtime/gate product bytes changed,
  and the executor/wrapper are exact mechanically rebound reviewed copies.

Commands used:
```text
/usr/bin/python3.12 -B -m pytest -q -p no:cacheprovider --basetemp=/tmp/ga-1aa1-worktree-tests-20260929-r1 test_worktree_package.py
/usr/bin/python3.12 -B -m pytest -q -p no:cacheprovider --basetemp=/tmp/ga-1aa1-inherited-worktree-tests-20260929-r1 <old-bootstrap>/test_noatime.py <old-entry>/test_entry.py
```

## Next after successful preparation

Prepare and review the fresh uninstalled PREP and bounded worker-window package,
reusing corrected R11 startup/control behavior without its obsolete failed-claim
prerequisites. The worker alone implements the two image-tool files from
WORKER-BRIEF.md. Independent product review and terminal zero-residue inspection
precede intake. Actual C1 execution and Claude↔Codex parity remain unproven.
