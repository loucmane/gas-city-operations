# Exact exception accepted; separate read-time gate — 2026-09-28 CEST

The original provider-independent execution and handover goal remains active
and incomplete. This is a pre-window refusal, not worker failure or parity.

## Completed outcome

The explicitly authorized 44-file common-Git exception was implemented in the
operational generator, tested and signed as
`3db9fe8dfa6952a57f3f5d276b13c3e8205c0958`, tree
`1746d070ebea714c35b873a752078f940f538859`, parent
`f1946126242042f07261ccd623c5c86f98b43b4c`. All 226 operational tests passed.
The manifest remains exactly
`5b2f7a167ffadb8879d859121b4a4cfbc44e79d1a5615950df0bdf73ed65e8b2`.
No filesystem permissions, worker grants or other checks changed.

Two one-shot independent native Astra reviews returned SOURCE_PASS for that
exact head, with no must-fix or should-fix findings. Their complete native
transcripts were exported without trimming, validated and filed through the
existing runner protocol. Identities:

- `01a0e62f-1a38-73e3-8a0c-f4de927d44e6`
- `01a0e630-59a9-71e3-b2dc-e0c956501ea3`

Frozen request and envelopes are in
`/tmp/ga-e0t1-20-s2-reviews-20260928-r7`; request SHA256
`aadd43a0373d686aeedaa52be66c4b85c0c9df44c7265c006efe146b18c3a3c7`.
All reviews are also filed under the signed head in the runner review ledger.

OBSERVE r3 ran through the actual host runner from 06:12:04 to 06:12:50 CEST.
It passed genuine host inspection with Drifts null, cache write protection,
preservation and zero surviving subprocesses. No worker launched.
Result: `/var/tmp/ga-e0t1.20-integrity-20260928-r3/result.json`, SHA256
`b0ec06cb5037c2ca6095e816f57b7a93aa16517ade64db3c4df4673bec1ccdd6`.
Job record SHA256
`684fd06392fcfda50776c41934f6cca3bb060f15109be1c8ccf6091878246942`.
The old failed preflight and successful observation HALTED records were moved
byte-exactly into their corresponding done records, never deleted.

## New refusal and proven scope

`ga-e0t1-20-s2-preflight-r2` stopped at 06:13:46 CEST, exit 1, in the
unchanged `stable_read_times()` call, before window-root creation. The exact
message names the suspension-state file's access time. The guard requires
atime newer than mtime/ctime and less than 19 hours old on a relatime mount.
The first condition holds; the suspension atime is about 20.5 hours old.
This is expected age, not evidence of a new clock jump or content drift.
The common-Git exception was therefore not reached in this live preflight.

- Job: `jobs/done/ga-e0t1-20-s2-preflight-r2.json`, SHA256
  `61a4326f57e2cfb074acfe02927413508f5961bc003f0b39f413f7c721f33c11`.
- Full log: `ga-e0t1-20-astra-window/preflight-20260928T041346Z.txt`
  under the existing staging root, SHA256
  `7f966356c95e0938914dfe51dec540a817622b791bd368a077a6a0e4032f99ca`.
- Current HALTED SHA256
  `222c8ffe51c8b404b2f50d094f168dfb86c9360f76204dbfc0bd04ae90615045`.
- `/var/tmp/ga-e0t1.20-window-20260928-r2` remains absent.
- No STAGE, ROUTE, RESUME or worker happened. No rollback is applicable.

Host readback at 06:17:15 CEST confirmed no active or unfinished runner jobs,
an empty queue, expected HALTED record, unchanged boot and service epochs,
zero restarts, the six historical fixtures inactive/disabled, and exact
suspension SHA256
`a3306567b3cf77e6371a870e6df239194574fab8f2dc3090ea55a5eeb14b4817`.
Core PID 2800348, signer 2310, broker 2940285 and runner 2812303 are unchanged.
The quiet window ended with this pre-mutation refusal; outcome recording is
now allowed. Do not queue later steps or replay the failed job.

## Mechanism reassessment and unchanged-policy forecast

The prior complete common-Git/client-input audit was not a timeless guarantee
of time-dependent prerequisites. Its scope must not be overstated: the 19-hour
gate expired during preparation and independent review. Source PASS cannot
satisfy this live gate. The exact exception authorization does not waive it.

Ordinary reads cannot advance a relatime atime already newer than mtime/ctime
until its 24-hour boundary. Do not write timestamps, chmod files, alter clocks,
cycle services, or weaken the check to manufacture admission. The old FRESHEN
package explicitly documents the same limitation and is bound to another run;
it is not permission to execute that historical package here.

Read-only forecast at 06:17 CEST, assuming no intervening material changes:

| Object | Exact observed atime ns | 19-hour expiry CEST | Read-refresh eligible CEST |
| --- | --- | --- | --- |
| suspension-state.json | 1790495272344466584 | 04:47:52 | 09:47:54 |
| city root | 1790508410441985211 | 08:26:50 | 13:26:52 |
| city .beads | 1790511942017316467 | 09:25:42 | 14:25:44 |
| provisioning directory | 1790511942021316465 | 09:25:42 | 14:25:44 |

There is no overlapping unchanged-policy opening before approximately
14:26 CEST today: the other objects expire before the suspension file becomes
refreshable. This is a forecast, not launch permission or a health guarantee.
At that time a bounded, independently reviewed read-only refresh and exact
before/after verification can precede fresh admission. Recheck all four objects
and the host before preparing another package. Record their latest safe start
before spending review or execution work. Preserve the failed attempt, use a
new job ID, and do not repeat completed S1, BIND or OBSERVE roots. Coordinator
outcome recording may change the known cache directory times; any successor
must observe and bind those real values before fresh exact-head review.

Changing this separate timing/preservation mechanism is an explicit architecture
decision outside the latest 44-file exception. No such change has been made or
silently inferred. Do not start another open-ended wrapper-repair campaign.
The worker task, C1 proof, bidirectional handover and terminal evidence remain
outstanding. Protected HPFetcher/Blog work and unrelated services are untouched.
