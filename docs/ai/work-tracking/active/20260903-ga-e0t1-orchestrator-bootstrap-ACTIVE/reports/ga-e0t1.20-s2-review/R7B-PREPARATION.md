# R7B preparation correction and exact R7 failure disposition

Bead ga-e0t1.20 remains the existing Gas City product-worker task. This is only
the operational preparation correction; product implementation remains a Gas
City worker operation. No Claude or Fable inference, permission widening,
installed receipt or configuration change is included.

## Preserved failure and live state

R7 candidate a27953982ab8a4321ba8e1ae3fafe61cd8e576c7 received two independent
Astra SOURCE_PASS reviews. Its PREP job failed at 17:34:25 CEST on 28 September
2026 in the isolated normalize child, before final receipt or result. Both
reviews remain preserved at /tmp/ga-e0t1-20-r7-preparation-reviews-20260928.
The failed root /var/tmp/ga-e0t1.20-prompt-prep-20260928-r7 is consumed and must
not replay. Its normalize-phase.json is pinned by SHA256
640a747000051e8aa31972418c9003de53b10a01a97e18eae93c95d5e1267d07.

The exact defect was unconditional host asset ownership verification in
configure, which also runs in the read-only namespace normalize child.
Actual host /usr/bin/node has owner/group 0; the same unchanged inode appears
as owner/group 65534 in that child. The strict authority check correctly
refused, but was being asked in a namespace unable to prove host ownership.

Post-failure host verification: exact city bytes, installed receipt and parsed
configuration unchanged. Four project rigs suspended, zero sessions, owned
normalize process reaped and group gone, queue empty, runner halted. Supervisor,
signer, broker and runner epochs unchanged with zero restarts. Evidence
ga-e0t1-r7-prep-failure-verified.json SHA256
8bb4da5de2ebc9864f00522b8d68c060b82e6514f80b2cde43f9fe03f2e7fb76.

## Narrow successor

The R7 generator, executor, wrapper, assets, validation and failed output stay
unchanged. New generator startup_r7b.py reads the exact R7 Git blobs and emits
only prompt-prep-r7b.py and operator/PROMPT-PREP-R7B.sh plus a manifest.

The actual host performs the unchanged strict helper-asset verification before
preparation, and repeats it before result publication. Shared configure only
loads the pinned source and establishes that callback. The isolated normalizer
does not make host-ownership claims: it accepts only its one literal root,
retains digest-checked source loading and native typed receipt normalization,
and writes normalized JSON to stdout. No bypass flag is added. Host ownership,
mode, content, inode/race checks and actual live worker revalidation are not
relaxed. The fresh root is /var/tmp/ga-e0t1.20-prompt-prep-20260928-r7b.

The existing receipt preparation still verifies its effective configuration,
three typed profiles and exact revision/self-hash-only receipt delta. All
installation and lifecycle surfaces remain absent.

## Evidence and tests

- 729 full operational generator tests PASS. Saved ga-e0t1-r7b-full.xml SHA256
  d5fce88138a9086de88f57dc3eaeb061cfa4e4751fcaf7ad4502dd6b83e5f1ce.
- Thirteen new executable-branch tests prove preflight order, wrong roots and
  unknown options refused, source launcher required in both branches, and
  host drift refusing before success publication. Fixture entrypoint stubs are
  explicitly not host or launch acceptance.
- Eight additional root reader tests address both reviewers' nonblocking
  request: positive bounded read, changed descriptor/path identity, size,
  ownership, mode, links and oversize. Synthetic root ownership only.
- The corrected configure plus the real native normalizer ran in the actual
  bwrap namespace against preserved R7 input. Exit zero, empty stderr, all three
  profiles present, all old input files unchanged. This did not run PREP main,
  install anything or launch a worker. ga-e0t1-r7b-normalize-proof.json SHA256
  5b2f94c0ef0e2c6ac9876dac5115ba5464ea60c71c9fc78a03a47c5d316d8ffe.
- The unchanged host asset verifier passed separately on the actual host.

## Next execution boundary

Two independent Astra source reviews of the exact signed clean successor and
PROMPT-PREP-R7B wrapper precede its one job submission. Preserve the R7 halt
with failure disposition before submitting the successor. No worker launch is
admitted by this package. Full R7 assembly, its recovery metadata and preserved
workspace evidence, fresh window roots and independent full-window review remain
required before any live worker window. No usable-workflow or parity claim yet.
