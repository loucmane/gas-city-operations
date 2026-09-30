# ga-5uc9 window R2 — preserve PREP and correct the unused fixture binding

The signed candidate ac203c440858bba17b370902e7a1b20f1015bf98 received two
independent HOLD verdicts for one concrete defect: the prepared worker probe
requires the frozen sandbox-negative fixture under ga-5uc9-bind-20260929-r1,
but the unexecuted BIND producer and ROUTE receipt consumer used 20260930-r1.
No BIND, operational wrapper, route, lifecycle or worker ran.

Both native reports remain in /tmp/ga-5uc9-window-review-20260930-r1 and the
original native rollouts. Reviewer B envelope is filed as HOLD in the runner.
Reviewer A's native record contains an extra parent message notifying it of B's
finding, so the strict single-message exporter refused it. Preserve that
transcript as additional review evidence, not an admissible runner envelope.
No reviewer record is edited or converted. The old candidate is blocked.

## Exact correction

Keep the completed PREP, probe, prompt, brief, all receipt images and hashes
byte-identical. Align the NOT YET CONSUMED BIND evidence root and all consumers
to the exact frozen probe path /var/tmp/ga-5uc9-bind-20260929-r1.
The directory suffix is a frozen identity, not a claim about execution time.
Fresh absence and no-symlink checks still precede its one creation; operation
timestamps will report the actual execution time. No old directory is reused,
renamed or deleted. Every other fresh operation root remains September 30.
The assembler's two explicit literals produce the correction. Its dependency
hash graph propagates exact pins; no module is hand-rebound.
All permission and negative-probe checks remain unchanged.

## Regression and review

test_probe_fixture_binding.py checks the actual assembled BIND producer,
ROUTE consumer, prepared worker FOREIGN path and wrapper collision gate.
Preserved RED: one failed cross-component invariant and four negative controls
passed at /tmp/ga-5uc9-fixture-bind-red-20260930-r1.xml.
The correction has a fresh actual-host baseline r2, final full package suite
at /tmp/ga-5uc9-window-final-20260930-r2.xml and two new single-turn independent
Astra reviews. It does not replay WORKTREE or PREP.
The initial package evidence and failed output remain unchanged.

The standing grant covers this understood pre-mutation correction. The original
goal remains active and neither source review nor this package proves parity.

## Final candidate evidence

- Full corrected package: 497 passed in 2.06 seconds, zero skips or failures.
  JUnit SHA256 4dfd5f17c885f8b7897338f5bea04fb26fdeddff26f720126879fe190732e737.
- Fresh baseline result SHA256 ab9e6d663f372da92614eabd0fff937415c9b225848b5857eb91dd73c698c804.
  Observation SHA256 ec6a56a55a29b10022dc7417a9061d6c24f86614bb54cc356dbf71af821b9373.
  Only authorized equal cache mtime and ctime advanced to 1790725858876922072.
  Provider differences empty. Strict workspace image unchanged.
- Assembly SHA256 86dbf349abaa9b12847f79c018c91a0ddffaf5f5ec2d2b740b14c76c6c8e76cd.
- Both unused BIND directory spellings were absent before review. The frozen
  September 29 spelling is the sole corrected producer and consumer identity.
- Supported workflow verification passed all six checks before final capture.
  No completed operation was replayed, no worker or live configuration changed.
