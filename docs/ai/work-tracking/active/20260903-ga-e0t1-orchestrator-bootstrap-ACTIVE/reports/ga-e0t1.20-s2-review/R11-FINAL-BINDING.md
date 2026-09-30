# R11 final source binding — 2026-09-29 CEST

The supported workflow verification passed all six checks at 02:33:41 UTC.
The R11 outcome note was read back as verified through the existing journal.
The first sandboxed log refused at the read-only lock before mutation; the same
supported logger then succeeded with the authorized filesystem access. No bypass
or alternate logger was used.

All coordinator workflow and Bead mutations finished before the fresh actual-host
capture in /tmp/ga-e0t1-20-readonly-baseline-20260929-r16. The create-only script
checked the exact restored R10 terminal image, stable host epoch, provider pins,
8048-entry worker workspace, cache and protected inventory. Result digest:
189e088bf73941567b4d89752d078e4f22c12d24cc6dacefeed722d6e9f1db6e.

Only the reviewed cache directory mtime and ctime changed, both from
1790640982604952235 to 1790649221451394669. No provider or other non-atime delta.
The generator binds the fresh observed image SHA256
2c5300a9ce628e8ca617f1016ec9d7a153ea274a951ff7e9328e6f011b75870b and both runtime
timestamp constants equal the new exact value. No on-disk metadata normalization
or acceptance of a value range occurs. Actual OBSERVE remains mandatory.

The final 135 materialized files match assembly.json exactly; its digest is
25faae1f8b21f1ffbb2db3388450e1217c46a54d92a192d5ae3c2d1b8b96a8e3.
Final full corpus: 1141 PASS, two opt-in fixture skips, six disclosed historical
live-baseline positives deselected, with current positives and negatives retained.
/tmp/ga-e0t1-r11-final-binding-tests-20260929.xml digest:
ef731003e5ddd238769f0d001960105ade7262976ced7f9fbe93d0848a6fc8bd.
Materialized contract: 42 PASS in /tmp/ga-e0t1-r11-final-contract-20260929.xml,
digest 3de244b57a94ef72f9ce8ad2c77ca1697e25a84da37a148972ffef62d20a44a3.
The separate reviewed real service-lifetime proof is reused unchanged.

This is source-only. No new window or worker has run. The successful preparation
halt remains preserved. Independent exact-candidate review must pass twice before
admission through the existing runner. During the frozen window, defer Bead and
workflow logging to terminal disposition; capture each job result in its native
create-only evidence and adjudicate before the next distinct job. Preserve R10 and
its old closed-session pending nudge without maintenance. The product repair and
full bidirectional handover remain unfinished.
