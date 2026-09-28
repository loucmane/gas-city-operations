# ga-e0t1.20 r4 recovery live result — restored, worker task unfulfilled

Recorded September 28 2026. All times below are CEST. The original full goal
remains active at step 4. No useful-worker, handover or goal-completion claim.

## Exact reviewed delivery

Signed recovery candidate 17598e3aca0cbabd391c162f7345284f4132415c.
Source commit 92c2e8bf is preserved; the full review report was added in the
separate signed evidence commit above. No amend, reset, force or cleanup.
Assembly manifest SHA-256
a8a29882d4982b6fdd9c582b23f1e2ae74c5233c089b5971401bd9b1c2db8361.

Two independent native Astra aegis-reviewer SOURCE_PASS verdicts, no must-fix
or should-fix findings, were exported and filed before execution:
- 01a0e7ba-7ce6-7823-972e-449d42b4803e
- 01a0e7ba-c7e7-7d12-ab4e-7e70ac1fcfb5

Request /tmp/ga-e0t1-20-r4-recovery-reviews-20260928/request.md,
SHA-256 1fca518faa50fa7174930f017be650d899b57fe84b6bc3bf10756a6dbdd4b3ee.
Reviews remain in that directory and in the runner review store for the exact
candidate. Source-only verdicts did not stand in for these live results.

## Recovery outcomes

The installed runner retained MainPID 2812303, start-monotonic 301336188076,
NRestarts 0 immediately before admission. Each job below exited zero,
became inactive, and was inspected before the next job was queued.

- 13:24:48 ADMIT passed, job ga-e0t1-20-r4-recovery-admit-r1.
  Read-only full preservation and endpoint admission, not restoration.
  Pass SHA-256 a4f45076de000cb1d0abf6f3993eb5d1b9bfde3581aab68e3227f0d882e64e11.
- 13:28:00 RESTORE passed, job ga-e0t1-20-r4-recovery-restore-r1.
  Exact baseline city and receipt restored through the existing confined
  writers, reload acknowledgement and verification. No lifecycle replay.
  Restore-pass SHA-256 d81e9a1da9343e5c3bf32e17a91ecfa21ccad7f039e1e8158ded0b9820c8a958.
  Restored snapshot SHA-256 665223978993018d2d6b0f2411aac6e48563db7bf3e7062e1b555edd21f9e0ea.
- 13:30:07 TERMINAL passed, job ga-e0t1-20-r4-recovery-terminal-r1.
  Actual host verification, full native platform integrity, read-only protected
  cache, accepted restoration and exact terminal suspension endpoint verified.
  Result SHA-256 459cacbbaf67e60f741af656277ebf11161a4abe3bab49637e7407db40f16438.
  Final snapshot SHA-256 6ef3d9a90f2c52e60a939fdd5641c53fa74bb10fb7663d2516120e09db9968d5.
  Preservation SHA-256 02c43c416b8e88877865422b50aaa7f22f4dca9b620bc901b4d553e76cbac305.

Window evidence: /var/tmp/ga-e0t1.20-window-20260928-r4.
Terminal evidence: /var/tmp/ga-e0t1.20-terminal-20260928-r4.
Job ledger: /home/loucmane/.local/share/gas-city-staging/jobs/done.
Inspected intermediate HALTED latches were preserved by guarded rename;
the terminal HALTED latch remains in place. No worker retry was queued.

The terminal result explicitly says worker_started_in_window true,
source_release_sent false and open_sessions zero. Its worker_launched false
describes the observer only. Earlier CONTAIN refusal and successful separate
HOLD and CLOSE remain unchanged. All rigs are suspended and zero residue was
proven; no successful worker claim or product task is inferred.

## Post-terminal source non-interference

Read-only inspection after TERMINAL, with optional Git locks disabled:
- ga-e0t1.20 remains open, unassigned, with the same route and work directory.
- Git staged and unstaged diffs both exit zero with no tracked difference.
- Filesystem comparison against workspace-before.json checks 8015 prior
  entries: no content, mode, type or symlink target changed; none removed.
- 17 entries were added. Sixteen match the already-pinned Core runtime
  materializations under .agents/skills and .gc. The remaining file is
  .codex/hooks.json, mode 0644, size 1238, SHA-256
  55e21a9d981805afb62da110b022bc847f7ad2b9a62bada45de95dbdfa472410.
- That hooks file is the only untracked non-ignored Git entry. It is preserved,
  not removed or retroactively accepted as an approved startup output.

Thus prior task source and both policy files are unchanged. Whole-workspace
pristine startup is NOT claimed: the hooks-file addition still needs producer
provenance and an exact post-render contract before another attempt.

## Concrete startup findings and next deliverable

Worker ci-72ehy failed before claim and SOURCE RELEASE. Its native transcript:
 /home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T12-52-11-01a0e7a4-c9fb-74d1-b7c4-b3e9d4cf5269.jsonl
SHA-256 c7a0faeb98c7fd536ab631465560dca1bfbc41fdeee8345f67cd7c8abe056721.
Read-only diagnosis:
 /tmp/ga-e0t1-20-r4-startup-diagnosis-20260928.md
SHA-256 cc59bc2202b7979a8f6f01a107c240ddbb9fead152dcccdb71a9cbb12a7b29bd.

The worker used an env-prefixed gc invocation with global flags ahead of the
verb. The approved native rules expect the absolute gc binary immediately
followed by hook or bd. The task brief already contained compatible literal
commands, but it was absent from the actual launch prompt. Fetching the Bead
to discover that brief depended on the very command access that failed.
Socket operation not permitted is not evidence of a broken Dolt service.

Separately, startup-release.py requires .codex/hooks.json absent although
startup produced that file. Do not fix either mismatch by a blanket allow,
deleting the file, disabling hooks, or relaunching unchanged.

Next deliverable is one end-to-end post-render startup contract:
prove the exact prompt reaches the worker before claim, every mandatory
control command matches the effective native policy, the hooks producer and
bytes are bound, and task constraints override the generic pool completion
instructions. Validate these together offline and seek consolidated review
before any corrected worker window. No product repair by the coordinator.

## Evidence workflow

The active journal was already ready. The generic resume alias re-entered
begin and refused unresolved attached repair dependencies without mutation.
This is preserved as a diagnostic, not a reason to close dependencies, create
another workflow, weaken readiness or start a new repair campaign.
The appropriate verify operation passed all six checks at 13:33 CEST:
live Bead ownership, plan sync, readiness, guard, diff check and tracking audit.
The original goal and existing task context remain intact.

## Consolidated read-only startup audit after recovery

The installed pinned Codex binary evaluated all three existing rules files
without executing the tested commands or making an inference request.
Eight assertions passed in r4-offline-command-policy.json: the intended
absolute claim, show, note and drain shapes are allowed; the signing negative
is forbidden; the observed env-prefixed claim, global-flags-first claim and
bare gc drain have no matching rule. No matching rule is not itself a native
forbidden verdict: it leaves these calls subject to their ordinary sandbox.
This is rule-selection proof only, not fresh-client rule-loading acceptance.
Official rules documentation agrees with exact argument-prefix matching:
https://learn.chatgpt.com/docs/agent-configuration/rules

The installed Core commit f45a626213dc5b8d0b52f097d978cca56e506df0 was inspected
as Git objects, not the currently newer source checkout. Relevant producers:
- cmd/gc/template_resolve.go renders cfgAgent.PromptTemplate before launch.
- cmd/gc/prompt.go treats plain markdown as literal prompt content. The existing
  per-agent prompt_template override can therefore deliver the already-scoped
  brief before any claim; a new broad command permission is not necessary.
- internal/runtime/staging.go stages provider overlays then finalizes managed
  Codex hooks. internal/hooks/hooks.go normalizes recognized managed commands
  against the installed gc executable while preserving user entries.

There are two existing assertions to reconcile for the one generated hooks
file, not just one: worker-startup.py requires completely empty Git status,
and startup-release.py separately requires .codex/hooks.json absent. Candidate
inspection also needs the same exact post-render inventory. Do not fix only
the first assertion and burn another live attempt at the next one.

The next operational successor must bind the producer and exact generated
hook bytes and verify effective hook/trust behavior rather than assume file
presence means hooks loaded. Canonical project trust exists; absence of a
separate linked-worktree trust entry is not by itself proof of failed trust.
No trust, hook, permission rule, live prompt, client configuration or source
was changed by this audit. Full generated output, claim command, startup
probe, release and final inspection must agree before consolidated review.
