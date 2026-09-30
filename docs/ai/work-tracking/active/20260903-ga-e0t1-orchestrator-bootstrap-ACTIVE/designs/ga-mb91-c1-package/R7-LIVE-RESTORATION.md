# R7 live window and exact restoration — 2026-09-30

Candidate: `309c0ecdd252c1a837ad26736a79526292c2937c`.
Two independent native Astra SOURCE_PASS reviews preceded execution. The full
goal remains active. This is recovery evidence, not worker or handover acceptance.

## Outcomes — Stockholm time

- OBSERVE r4 passed at 14:47 with actual-host verification and protected cache.
- PREFLIGHT r2 passed at 14:48 and STAGE r1 passed at 14:51.
- ROUTE r1 refused at 14:53 before dry-run, route intent, sling or rig resume.
  The pinned September 27 process record named PID 2800348 and start 22964291;
  the already accepted live supervisor is PID 466463 and start 51763309.
  This is stale package input, not an observed supervisor restart.
- Two independent reviewers passed the exact recovery helper SHA-256
  `85608ef58b36373d56ecb09bb53e5762a2413e4ed7f8d256d3441687020ac1a9`.
  It archived only the exact failed runner latch after proving pre-route failure.
- CLOSE-1 passed at 15:05 with zero sessions, city tmux sessions and worktree
  processes. No session was closed, no server killed and no signal sent.
- ADMIT passed at 15:10. RESTORE passed at 15:14:04.
- TERMINAL passed at 15:15:45 with actual-host verification, accepted restoration,
  read-only root-cache protection and terminal suspension binding.

## Bound evidence

All failed roots and their six route observation files remain untouched.
The active window was `/var/tmp/ga-mb91-window-20260930-r2`.

| Evidence | SHA-256 |
|---|---|
| ROUTE done | `2d9d454ba91e1e7378f2f8ed1f4413096e654df03fa0088e71c135305458b932` |
| CLOSE-1 done | `933492ff0357fcd0b2b3135a8a40d418f4bc98cf2a5a2336682605fcfb431fba` |
| ADMIT pass | `a4f45076de000cb1d0abf6f3993eb5d1b9bfde3581aab68e3227f0d882e64e11` |
| RESTORE done | `a7d69a90a0c6819420b5852bf05cfa2d64af939f01dd610ab78c5945a1d43321` |
| TERMINAL result | `dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8` |
| TERMINAL done | `3201f5ee5a18528d761c34db3f562b324c8a6d81e379114dbae16bde9949288d` |

Terminal result: `/var/tmp/ga-mb91-terminal-20260930-r1/result.json`.
Close result: `/var/tmp/ga-mb91-r1-close-20260930T130514Z/result.json`.
Runner records remain under the existing staging jobs directory, with all
successful latches archived by the reviewed preserve helper.

Original city bytes read back as
`bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1`;
suspension bytes read back as
`222da22682b755d2ddf4bc64a855ec9c906e38666c4fd17ea22d895419a34ff5`.
All rigs stayed suspended. No worker launched or candidate content changed.

## Narrow successor

Refresh the process record through the existing reviewed host recorder. Bind
its exact digest and accepted supervisor epoch into package generation, then
verify that same record before staging as well as before routing. Preserve
identity checks, namespace/cgroup checks, the common-Git exception and queue
protections. Use fresh consumed-root names; do not repeat WORKTREE, PREP, BIND
or Core delivery. Focused regression must reproduce the stale-record failure
before the correction. Independent review precedes any successor execution.

Nonblocking R7 review note: hidden-label test cases share the same count-return
mock. Separate fixtures may improve diagnostic clarity; no guard was relaxed.
