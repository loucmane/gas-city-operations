# R5 prompt preparation — completed without live installation

2026-09-28 14:24 CEST. Original goal remains active at step 4.
Task ga-e0t1.20 remains unfulfilled. No worker or product acceptance is claimed.

## Reviewed candidate and job

Signed candidate 481e97df3621e570b105d00b63f884e608254770.
Two independent native Astra source passes, no findings:
- 01a0e7f2-3e93-7e10-ad46-8ff3546cd3db
- 01a0e7f2-6666-7e71-a497-5c7facf99d9d

Frozen request /tmp/ga-e0t1-20-r5-prompt-prep-reviews-20260928/request.md
SHA-256 432e274e7855e2622e64d288d09013cbc8ded77e517516a532223828fa717df2.
Both actual native rollouts were exported and filed under the exact candidate
in the existing runner review store, not synthesized from coordinator prose.

The job ga-e0t1-20-prompt-prep-r5-r1 ran only PROMPT-PREP-R5.sh through the
existing reviewed jobrunner at 14:22:34–14:22:35 CEST. Exit zero, unit inactive.
The prior successful terminal latch was preserved by guarded rename to
state/HALTED.ga-e0t1-20-r4-recovery-terminal-r1.before-prompt-prep-r5.
The new preparation HALTED latch stays present. Queue is empty.

## Actual results

Fresh root /var/tmp/ga-e0t1.20-prompt-prep-20260928-r5.
result.json SHA-256 1e027be4b46422ebeab0f9988b99bd57cdb803554a881f4f2b56704eb00a4a14.
New uninstalled city image SHA-256
982ee2ada6a9ee566de53f862408a752f53f9c539f21262e12959a9a0f20a6bd.
New native-finalized receipt SHA-256
8796c947c5ebbf2435b1c83af55c3fc3d17b21ce6b2dfbb426d0855d3c896f3e.
New permission revision
070da10b3bdb60691701d02dac5c627764c8aa38779da0635d5261724dac279f.

Only the prompt field differs from the prior isolated effective configuration.
The native receipt changes only permission_revision and receipt_sha256; all
three profile records remain exact. Native normalize and finalize both exit
zero with direct child reaped, owned group gone, no survivors or cleanup errors.

Independent post-readback confirms installed city remains
bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1
and installed provisioning receipt remains
7185414ebade17a1fdd7d485564e85f6ad8d7e0230983c21bf917f1ed27fb0ba.
The real receipt path is .gc/runtime/provisioning/receipt.json, not
.gc/platform/receipt.json; the latter read returned absent without mutation.

Host runner remains MainPID 2812303, start-monotonic 301336188076,
NRestarts zero. Pre-job actual city status: suspended, all four rigs suspended,
zero running agents, no city tmux server. Independent native session list
before and after preparation: total/active/suspended/closed all zero.

## Honest evidence details

The saved result.json is authoritative and correctly identifies gascity/codex,
supplemental_prompt_preparation true, preparation_only true, installed false,
worker_launched false, and execution_authorized_by_this_result false.
The inherited executor's stdout prints its pre-decoration dictionary and still
labels gas-city-template/codex. This is a reporting inconsistency only: the
saved result and exact config equality both name gascity/codex. Preserve it;
do not rerun completed preparation merely to change that printed label.

One signed-commit attempt selected a nonexistent helper path and refused
before writing a commit. HEAD and staged bytes remained exact. Readback proved
the repository's configured signer is /usr/bin/gpg; the normal signed commit
then succeeded using the already-cached key. No config/key change or unlock.
The failed attempt remains in the native transcript.

## Next action — no completed operation replay

Complete the fresh R5 worker-window assembly from immutable failed-r4 bytes,
using the above actual PREP outputs, exact preserved runtime/hook inventory,
preclaim body and exact task-note amendment. Preserve historical notes,
routing and failed attempts. No S1 PREP, BIND or ROUTE replay. Bind the new
cache observation after evidence recording. Test the whole startup-to-closeout
contract and obtain two exact-candidate reviews before any worker launch.
The operational successor is still incomplete; no implicit release exists.
