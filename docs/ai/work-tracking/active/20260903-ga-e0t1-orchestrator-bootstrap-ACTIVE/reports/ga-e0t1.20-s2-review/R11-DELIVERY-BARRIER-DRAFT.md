# R11 bounded native delivery barrier — draft checkpoint

2026-09-29, Stockholm time. Same goal and ga-e0t1.20. All rigs remain suspended.
No live window or worker was started. The product's three-file CLOSE repair
remains worker-only and unchanged.

## Narrow operational change

Keep the RELEASE oneshot alive for at most 90 seconds after one native enqueue.
Require both a closed/injected native shadow receipt with the provider return
boundary and the exact fresh user-message ingress in the same worker transcript.
Require a live, unchanged native poller in this exact oneshot cgroup with pinned
executable, arguments, PID and start ticks. Failure never resends. Native unit
teardown, not a coordinator signal, owns helper cleanup.

The I/O adapter has no new delivery mechanism. It uses one native session nudge
with queue delivery and JSON response, supported session/shadow Bead reads, and
bounded non-following no-atime reads of the queue and transcript. Queue history
is exact and preserved, including the old release fenced to the closed R10
session. Neither queue status maintenance nor drain is invoked. The public
enqueue response contains no nudge ID; the native receipt supplies it.

These five authoring files are unwired, not runner-admitted or activated:

- generators/release_delivery_r11.py — pure predicates and bounded wait
- generators/release_runtime_r11.py — one-enqueue I/O adapter
- generators/test_release_delivery_r11.py — predicates and recorded R10 regression
- generators/test_release_runtime_r11.py — exact native command and failure contracts
- generators/test_release_service_lifetime_r11.py — opt-in isolated user-unit proof

## Evidence and next executable proof

Focused offline run: 70 passed, zero failures, two explicitly skipped live
fixtures. JUnit is `/tmp/ga-e0t1-r11-delivery-focused-r4-20260929.xml`.
This is not runtime success or product acceptance.

Before running the fixture, independent reviewers must inspect the exact signed
candidate and this boundary. The opt-in creates precisely two short-lived
synthetic user units named `ga-release-fixture-<random>`, each with a 15-second
start limit, 5-second stop limit and native control-group teardown. They run only
this test's Python fixture in preserved `/tmp/ga-e0t1-r11-lifetime-*` roots. The
negative parent exits after enqueue-equivalent setup; its detached helper must
not reach its acknowledgement. The positive parent stays alive until the helper
acknowledges. Both must finish with the exact child and unit cgroup absent.
No Gas City command, rig, worker, provider, credential, production file or service
is part of this fixture. No manual signal, cleanup, new privilege or installation.

Approved-shape invocation after independent review:

```text
GC_RELEASE_LIFETIME_PROOF=1 /usr/bin/python3.12 -B -m pytest -q -p no:cacheprovider --basetemp=/tmp/ga-e0t1-r11-lifetime-proof-20260929 --junitxml=/tmp/ga-e0t1-r11-lifetime-proof-20260929.xml test_release_service_lifetime_r11.py
```

Only after that proof may the full fresh R11 successor be assembled and receive
its normal exact-candidate two-review admission. Preserve R10, its consumed
roots, pending fenced message and complete restoration evidence. Do not replay
WORKTREE, BIND, ROUTE or any consumed R10 job. Reuse the actual startup proof as
historical evidence but require the fresh worker's own identity and startup.
This draft grants no worker execution and cannot replace runner admission.
