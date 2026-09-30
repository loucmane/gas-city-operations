# Exact common-Git baseline exception — 2026-09-28 CEST

## Explicit operator authorization

> I authorize replacing the operational common-Git blanket permission check with the exact 44-file baseline exception bound to manifest SHA-256 5b2f7a167ffadb8879d859121b4a4cfbc44e79d1a5615950df0bdf73ed65e8b2. This supersedes the earlier no-weakened-checks restriction only for this exception. Preserve all other checks, exact owner/mode/content verification and worker write protection. Require independent review before execution, then continue under standing authorization.

The earlier rejected edits and preparation are preserved in
CONFIG-EXCEPTION-PREPARATION.md and signed f1946126. That rejection was not
bypassed. The explicit new operator message is the authority for this delta.

## Bounded operational change

- The generator hash-verifies the exact 44-file manifest and embeds its pins
  into the generated common-Git observer. No live sidecar can change the list.
- Only exact relative paths qualify. UID/GID remain strictly 1000. Each
  exception must match full type, mode, size, link count and content digest.
  Missing exceptions refuse, as do changed contents, stricter/different modes,
  new group-writable paths, world-write, links, special files and owner drift.
- All other paths retain the blanket non-group/world-writable requirement.
  O_NOFOLLOW/O_NOATIME, bounded reads, race checks, full inventory, hook/branch
  validation and exact before/after comparison remain unchanged. Worker Git
  write protection and all other startup/release/containment gates are intact.
- No chmod, ACL, trust, sandbox or provider permission changes occur.
- The consumed first preflight window is preserved. Every successor window
  reference uses `/var/tmp/ga-e0t1.20-window-20260928-r2`. Observation has fresh
  root `/var/tmp/ga-e0t1.20-integrity-20260928-r3`. Original S1 and BIND receipt
  roots and the consumed BIND executor remain exact and must not run again.

The complete read-only baseline audit found no other failing common-Git,
workspace or remaining client-input predicate. Its 7972-entry common inventory,
44 empty regular configuration files and 8015-entry workspace are documented in
the preparation report. This is neither fresh worker evidence nor live admission.

## Regression evidence and delivery

The preserved RED corpus at
`/tmp/ga-e0t1-20-common-red-20260928-r1.xml` has 3 expected failures and 17 passes.
Two assertions reach the same old authority refusal; the third proves fresh
window roots are required. No claim of three independent defects is made.

Focused GREEN: 77 passes in
`/tmp/ga-e0t1-20-common-green-20260928-r1.xml`.
Full nine-module operational corpus: 226 passes, zero skips/failures in
`/tmp/ga-e0t1-20-s2-final-tests-20260928-r10.xml`. Tests use disposable fixtures;
the original consumed-binding records are read-only regression inputs.

Before execution, regenerate deterministic package bytes, bind a fresh final
read-only host/cache observation, verify the exact signed clean candidate and
obtain two fresh independent request-bound Astra verdicts covering all admitted
wrappers. Preserve the failed preflight HALTED record before clearing it for an
admitted successor. Do not replay completed BIND or any consumed output root.
Disagreement or a must-fix is HOLD. No worker implementation, C1 execution or
provider-parity acceptance is implied by this operational correction.

Final read-only host binding is saved in
`/tmp/ga-e0t1-20-readonly-baseline-20260928-r7`: observed SHA256
41738a4334862812de6a90bf8530a5f3814ea75f806aa1063ca653c08ff93e5e.
Only the known cache-directory mtime/ctime pair differs from accepted P13,
now 1790567947546740632. No provider differences or protected host differences
occurred, and the workspace still hashes to 9ac54bc065f8407cae1d0e5e21befdb4bc99ee43a87e157c7e1501d8bf6b8994.
This prospective S2 pair remains under standing corrected-package authority,
not the later separate C1 cache decision. No filesystem timestamp was written.
Final assembled-candidate regression is preserved in
`/tmp/ga-e0t1-20-s2-final-tests-20260928-r11.xml`.
