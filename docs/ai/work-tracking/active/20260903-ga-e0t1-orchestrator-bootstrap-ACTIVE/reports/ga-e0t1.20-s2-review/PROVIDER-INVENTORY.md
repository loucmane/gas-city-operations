# S2 BIND PASS and read-only OBSERVE refusal — 2026-09-28 CEST

Signed candidate 3c9931721fc8cdd204c8d7debd0c47c739064ccd obtained two fresh
request-bound Astra SOURCE_PASS verdicts. Both are filed in the runner ledger
and preserved under /tmp/ga-e0t1-20-s2-reviews-20260928-r4.

Job ga-e0t1-20-s2-bind-r1 completed BIND PASS at 01:45:11 CEST. The exact
workspace metadata and startup note were read back. The child remains
unassigned and unrouted. Result:
/var/tmp/ga-e0t1.20-bind-20260927-r1/result.json.
The completed operation MUST NOT repeat, including under a successor commit.

Job ga-e0t1-20-s2-observe-r1 refused at 01:46:07 CEST, before creating its
output directory and before invoking the inspector or changing live state.
Its job result, log and HALTED latch are retained. Unit is inactive with PID 0.
The exact failed operation was observe-integrity-r11.py provider_pins: the
hardcoded inventory still had four M10 providers although the unchanged,
digest-bound M12 manifest contains five. The fifth is the already-installed
Template candidate wrapper. This is a package compatibility defect, not
unexplained live provider drift. No route, stage, resume or worker occurred.

The unchanged manifest SHA-256 is
114b4a000471ee145d494732db361521ea237b3e4857607b06720b7b105327b9.
Both preflight and terminal observer guards need the same exact five-entry
inventory. The generated successor adds only the fifth exact path/hash and
retains the full manifest hash, order, resolution, installed byte/mode/owner
checks and version-only probes. No provider configuration changes or model
inference is introduced. The new fixture copies only this infrastructure
manifest's provider inventory, not credentials or project data.

25 focused tests execute both actual generated guards. They reproduce the
old signed candidate's refusal, accept the exact M12 fixture, reject missing,
extra, reordered, renamed, wrong-path/hash/arguments/bytes/mode/resolution
inputs, and prove the already-recorded BIND note remains byte-identical.
Evidence: /tmp/ga-e0t1-20-provider-tests-20260928-r1.xml.
The successor uses fresh observation root
/var/tmp/ga-e0t1.20-integrity-20260928-r2. It starts at OBSERVE, never BIND.

This was the first live S2 observation attempt. Its understood, pre-mutation
failure permits a reviewed corrected successor under standing authority.
After that attempt, reassess any further mechanism failure rather than
silently replaying it. Keep all failed and completed evidence.

All seven focused modules now pass 183 tests with zero failures/skips:
/tmp/ga-e0t1-20-provider-full-20260928-r1.xml. Workflow verification passed
six checks at 01:50:55 CEST. The following r5 read-only baseline verifies no
unexplained host/protected/provider drift and the unchanged 8015-entry worker
workspace. Only the explicitly bound cache directory time pair differs from
P13: 1790553055537553535. Observation SHA-256:
74704997acff2a47c46f66b7eef2c3d0a20f06d1fee2a1735d6014eff31f4d79.
The new evidence root is /tmp/ga-e0t1-20-readonly-baseline-20260928-r5.
This is not admission, and no failed step is replayed.
