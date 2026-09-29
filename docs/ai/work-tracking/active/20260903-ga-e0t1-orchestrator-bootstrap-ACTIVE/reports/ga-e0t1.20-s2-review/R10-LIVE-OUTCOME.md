# R10 startup PASS, release enqueue-only failure, recovery PASS

Recorded 2026-09-29, Stockholm time. Same full provider-independent execution and
handover goal; no replacement goal or source-work context.

## Outcome

Exact signed operational candidate `30a844f398de06b5ad421e0a74d30e4d421612e4`
received two independent Astra SOURCE_PASS reviews. One Gas City Astra worker,
`ci-9dp7z`, completed actual workspace, subscription, foreign-write denial and
native direct-signing-denial startup checks. Independent startup review passed.
The native waiting turn completed at **02:38:13 CEST**.

RELEASE at **02:44:40–02:44:46 CEST** validated the same session, claim, entire
workspace, shared Git, process chain, policy inputs and exact waiting transcript.
It issued exactly one supported session nudge. The native response was
`Queued nudge for gascity/codex`; this proves enqueue, not delivery.
WATCH-3 still showed the exact pending nudge `nudge-02f0f513467f`. The worker's
native transcript was unchanged. No product edit or candidate was produced.
The package's `source_release_sent=true` is classified as enqueue-only evidence,
not useful execution, delivery acceptance, provider parity or goal completion.

## Exact evidence

- Startup report `e8e6fa2832cbf10fee1d24ffae3a753047d87838d38d00c7745f36efece4849d`.
- Native rollout `7368ea8e311109d97e479ab7308ea8dd9ccec11b85ca860c0fb761c0cf71ab0d`.
- Startup request `470550f73d28c46091d84d6c26a0e1bbbd2b21b25d81802e40a76a1846eac7cd`.
- Release root `/var/tmp/ga-e0t1.20-startup-release-20260929-r10`.
- Watch root `/var/tmp/ga-e0t1.20-r10-watch-20260929T004637Z`.
- Startup reviewer native rollout `/mnt/c/Users/smoki/.codex/sessions/2026/09/29/rollout-2026-09-29T02-41-09-01a0ea9b-b891-7cc0-9bfe-f6dbf7a8352f.jsonl`.
- Window reviewers and admission exports remain in `/tmp/ga-e0t1-r10-window-reviews-20260929` and the runner's exact-candidate review directory.

## Independent diagnosis and minimal correction

Read-only reviewer `aegis_r10_window_a` independently confirmed the missing
delivery check at the exact live Core commit
`f45a626213dc5b8d0b52f097d978cca56e506df0`. `ensureNudgePoller` starts a detached
process group, not a new service cgroup. The release oneshot returns immediately
after enqueue and its unit teardown contains that helper. The recorded poller
PID `3458923` was absent. Per-command evidence records no process-group TERM/KILL.
The service-lifetime explanation is high confidence, but the exact termination
cause was not recorded; early poller initialization failure remains an alternative.

The smallest correction is operational: keep the RELEASE oneshot alive after its
one enqueue until bounded native delivery acknowledgement and exact same-session
transcript ingress. Bind the helper executable, argv, PID/start and owned cgroup.
Verify cleanup after unit termination. Never resend on timeout or uncertainty.
No Core setting, native immediate-input bypass, operator tmux injection, worker
permission expansion, extra worker or new privilege is needed.

Two actual-source details prevent invented contracts:

1. The native enqueue JSON has no nudge ID. Require absence-before and then the
   unique exact message/session native nudge record; bind `metadata.nudge_id`.
   Terminal success is closed/injected with `commit_boundary=provider-nudge-return`.
   Queue disappearance alone does not prove delivery.
2. The native poller sends `formatNudgeRuntimeMessage`, beginning `Deferred reminders`;
   it does not send the provider-hook `formatNudgeInjectOutput` wrapper.

Focused tests must prove enqueue-only false success, delayed delivery, exact
session/message, early helper death, timeout, absent native acknowledgement,
duplicate-enqueue refusal and owned-cgroup cleanup. Independent review remains
required before any successor execution. This diagnosis is not execution admission.

## Recovery and readback

- CONTAIN-1 passed **02:55:00 CEST**: city and gascity rig suspended through the reviewed native lifecycle.
- CLOSE-1 passed **02:56:56 CEST**: `ci-9dp7z` closed; zero open sessions, city tmux sessions and workspace processes. No direct signal or tmux-server kill.
- Read-only restore admission passed **02:58:08 CEST**.
- RESTORE passed **03:08:17 CEST**, including the existing bounded diagnostic-arm expiry wait. No reload replay.
- TERMINAL passed **03:09:43 CEST**: actual host verified, native platform `Drifts=null`, root cache read-only, suspension endpoint bound and window preservation PASS.
- Terminal result SHA-256 `dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8`.
- Actual after-observation SHA-256 `7edacee188688e492da0d85aded75adbb788f1ef44532f088d9d6d4f54bac7e5`.
- Terminal runner result SHA-256 `f6813feeed9a6fa61698dd77c0e2bf57235d543747072df7f736f8d2bb1bde81`; job unit inactive.
- All successful runner halts were archived without deletion; no next job queued.
- Live Bead readback: `ga-e0t1.20` open, unassigned, original `started_at=2026-09-28T13:01:54Z`, route unchanged. Native closed-session and progress-stall metadata remains as history.
- Canonical project identity passes and current source readiness is `READY | task=ga-e0t1`.

All prior attempts and startup evidence remain preserved. Product source is still
reserved to the worker's three-file CLOSE repair. No Fable/Claude inference occurred.
Standing authorization continues to cover a reviewed bounded successor; no new
micro-authorization gate is introduced. Deferred workflow improvements remain deferred.

## Append-forward native queue clarification

Independent source inspection subsequently established that `gc nudge status`
runs global queue-expiry maintenance before reporting. One coordinator status
observation had been treated as read-only; its readback remained one pending and
26 historical dead items, with no delivered release. That classification was
incorrect. The successor must not invoke status or drain as a read-only check.

The pending R10 message is fenced to closed `ci-9dp7z`, with shadow Bead
`ci-wisp-lgdp`, type `chore`, label `gc:nudge`. Core will leave it pending for
ordinary expiry; it is not claimable by the new session. Preserve it, not a
fabricated retirement. The successor observes the raw queue file without write
or atime effects and binds all historical items unchanged. It obtains the new
release acknowledgement through the exact supported session-filtered shadow
Bead query. New-session epoch comes from its native session Bead, not an invented
field in the public session-list result.
