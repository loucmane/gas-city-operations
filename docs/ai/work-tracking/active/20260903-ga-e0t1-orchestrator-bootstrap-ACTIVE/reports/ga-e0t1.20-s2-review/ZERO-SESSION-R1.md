# ga-e0t1.20 zero-session parser correction — source only

2026-09-28 CEST. Continue the existing goal and operational-package authoring
scope. The successful recovery-only package and all consumed roots remain
untouched. No worker retry, routing, lifecycle mutation or runtime activation.

## Current baseline and exact blocked operation

Recovery TERMINAL completed at 11:08:21 CEST on signed
524f1a3da16b60cc1a036f9e0f681cd3157b2d25. Its result digest remains
dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8.
The runner remains HALTED, no job queued. The task is still open and unassigned.
The three worker C1 product files remain untouched.

The failed rig-resume r3 postcondition observed no worker but refused
active session count. The installed Core source declares ActiveSessions as
an integer with JSON omitempty at cmd/gc/cmd_citystatus.go:91. Zero therefore
does not appear in that status summary. The independent session list explicitly
reports sessions empty and all four summary counts zero.

Preserved phase evidence:
- /var/tmp/ga-e0t1.20-window-20260928-r3/rig-resume-status-0-phase.json
  SHA-256 2b2209ffa582b161ccbc8f22080d31c3549a4aa5d5a15dc7327d5fd6a5c2933a.
- /var/tmp/ga-e0t1.20-window-20260928-r3/rig-resume-sessions-0-phase.json
  SHA-256 9790fd84b806440314e1533f2a398b413037e5c51e0077a11068a2a820c7c754.

The two portable fixtures under generators/fixtures contain those stdout JSON
objects with a single final newline. Status fixture SHA-256
1e2fd34b98762a8dfe8f723a019c854961bc79072c2a4c39be7d525f25d59ef3;
census fixture SHA-256
3a89d53bf39493b960e32561aa14a4ae1d62ec6562a901f4acd300dabba0b4b3.
No product content or authentication data is included.

## Source contract

Only a missing active_sessions field receives the Core omitted-zero treatment.
A present null, Boolean, string, float, negative or extra count still refuses.
Admission of omission requires no running rows and independently typed exact
census totals: active and closed zero, total and suspended equal to the open
row count. A lone suspended row must explicitly say suspended and satisfy all
existing worker identity, workspace, provider and native session checks.
Unknown state, missing counts, wrong identity, extra sessions and any running
worker refuse omission. Explicit active count also cannot exceed the actual
census row count. Existing duplicate-display restriction to suspension remains.

No input JSON is rewritten. The generated lifecycle matcher is exercised on
the real failed status/census pair, with a wrong-rig-suspension negative.

## Historical assembly preservation

A full regression run exposed an authoring dependency: recovery.assemble rebuilt
its completed predecessor from current successor inputs. Changing the parser
therefore changed historical CLOSE source hashes and correctly tripped the
old exact-pin assertion. Do not refresh that historical pin.

Recovery assembly now reads its exact existing PARENT Git commit and manifest,
checks all predecessor file digests and copies that immutable input. Tests prove
every one of the 58 recovery outputs remains byte-identical to the reviewed
524f1a3d package. The generated recovery package, wrappers, historical evidence,
44-file common-Git exception and runtime checks have not been edited.
The current source parser change is not installed in a live execution package.

## Regression evidence and honest limits

Initial RED: 9 failed and 26 passed at
/tmp/ga-e0t1-20-zero-session-red-20260928.xml.
Eight failures reproduce zero omission across empty and suspended fixtures;
one reveals the previously accepted count-one versus empty census mismatch.

Intermediate focused run: 1 failed and 90 passed. The negative integration test
incorrectly expected an exception; the existing matcher returns false for rig
suspension disagreement. The corrected assertion preserves that real contract.
The intermediate full run records 6 failures and 33 setup errors caused by this
assertion and the historical assembly dependency above, with 405 passing.
All intermediate JUnit files and fixture roots are preserved.

Final operational corpus:
444 passed, zero failures or skips, at
/tmp/ga-e0t1-20-zero-session-confirmed-20260928.xml.
Managed-update golden parity and git diff --check PASS.
Required full adapter/meta suites are running separately; their final outcome
must be read back before publication, not inferred from this source result.

An initial file creation hit the chat filesystem boundary before mutation.
Normal scoped approval permitted the authoring edit. A command-classifier
parse refusal on an unmatched apostrophe in a comment was corrected without
changing checks or using another authority path. No denied live action ran.

## Next boundary

Obtain two independent Astra source reviews of the exact signed candidate.
This source PASS would not authorize replay of any consumed package, clear the
runner latch, launch a worker, prove C1 repair or finish provider handover.
A fresh execution package still needs current baseline pins, distinct attempt
roots, its complete tests and independent exact-head reviews. Preserve completed
WORKTREE, PREP, BIND and ROUTE; never repeat them to obtain a new attempt.
The recovery-only grant itself contains no worker retry.
