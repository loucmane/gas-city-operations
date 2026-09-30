# R9 actual restored-baseline correction

2026-09-29 CEST. Candidate 3487a5c91b046edd2fa29f78e4977697089a1e41
received two independent Astra SOURCE_PASS verdicts. Both genuine native exports
are preserved and filed. The coordinator nevertheless held execution after a
direct pure-function check against the pinned actual R8 terminal observation
found a stale preimage constant. No R9 window job was queued or run.

The accepted observation already contains cache directory mtime and ctime
1790621288720671640. The assembled function still demanded the older R7 value
1790604770227789531 before copying in the R8 value. PREFLIGHT would therefore
refuse. This was an assembly error, not new filesystem drift or missing authority.

The operational correction changes only CACHE_PREV_NS to the exact already
accepted value. CACHE_PINNED_NS remains unchanged and both are now equal.
The original function and all its strict checks remain byte-identical; it now
validates and copies the exact current image without any metadata normalization.
No old timestamp, range, alternate image or new disposition is accepted.
The generator's dependent source/wrapper hashes are mechanically regenerated.

The new positive regression reads the actual digest-bound R8 terminal observation
and proves the comparison returns a byte-equivalent image without mutating its
input. Four negatives alter either timestamp by one nanosecond and must refuse.
The RED result is one failure and four passes at
/tmp/ga-e0t1-r9-cache-red-20260929.xml. Focused corrected assembly is 28 PASS
at /tmp/ga-e0t1-r9-cache-green-20260929.xml. The final full corpus is 958 PASS
and two disclosed historical deselections at
/tmp/ga-e0t1-r9-full-final-r2-20260929.xml. The materialized 42-case contract bytes are
unchanged, so its existing evidence remains valid.

Corrected assembly SHA-256:
45bee083a3c569b12c5b7ba1164f5140c54c432cf6ab26e9818ba09f2ce3778d.
Corrected generator SHA-256:
95dbae53916aaa1136ef7ac6d6a78d07afed3c174e894fd3a5506f0a8082b2f6.
These supersede only the source assembly bindings in R9-WINDOW.md. Every live
preparation, restoration, ownership, transcript, permission and workspace pin
is unchanged. The earlier package and reviews remain preserved as historical
source evidence, not live success. Fresh independent reviews of the exact
successor are required before execution. All rigs remain suspended.
