# Independent review of the corrected release transport

Recorded 2026-09-29 CEST under AUTHORIZATION.md and the standing completion
grant. No new permission boundary is introduced by this source checkpoint.

## Frozen candidate

- Commit: 01cff54c2ef0f467e2c590afdcc3ebd1d1e24717
- Tree: ca47bb029c41a9009c6b86c04ee7503002503a78
- Parent: 24198a2f3a92d8dc841d72691c6a147ef1565dac
- Runtime SHA-256: b6795e8471a124dfb29812393edad9f42e0d5a699b87403891740f0c950b72ab
- Delivery SHA-256: 3a466bab3a97c23f5c5454d26f6d9da332c000c75001ad9781afeb652f6fb45c

The coordinator independently verified the signed commit cryptographically and
read back a clean worktree. Source review is not package admission, execution,
publication, provider parity, or completion of the original goal.

## Reviewer A

Independent Astra reviewer /root/aegis_rq5n_r12_delta_a returned:

    SOURCE_PASS 01cff54c2ef0f467e2c590afdcc3ebd1d1e24717

No must-fix defect. Committed blobs were inspected without running tests or live
code. Verified bounded complete receipt history, absent-marker directory checks
before enqueue, final process identity bracketing, restricted Core ancestry plus
image and cgroup authority, immutable prebound helper identity, one enqueue with
no internal replay, and receipt AND transcript acknowledgement. The incomplete
earlier full regression run remains honestly preserved in REVIEW-R2.md.

Optional coverage improvement: directly test malformed receipt top-level output
and the accepted 128 versus refused 129 boundary. This is not a demonstrated
defect; the source explicitly refuses non-lists and counts at least 129. It does
not invalidate the source PASS or create an additional blocking prerequisite.

## Reviewer B

Independent Astra reviewer /root/aegis_rq5n_r12_delta_b returned SOURCE_PASS for
the same exact candidate with no must-fix defect. A supplemental read-only source
review resolved its native-query completeness question and withdrew that
should-fix evidence gap. No tests, live inspection or mutations were performed
by that reviewer.

The installed managed bd reports 1.2.2 at 6c124203e771 and has SHA-256
912f2a0afaa9a14fd06f09851a39326724c2e91454a78930d0cc434502f39bce.
Cached module metadata identifies source commit
6c124203e771433a3550c348771a5b5e27fd3c21. The version correspondence is identity
evidence, not a reproducible binary build proof. Operational packages must retain
their separate exact installed-binary checks.

Source root: /home/loucmane/go/pkg/mod/github.com/steveyegge/beads@v1.2.2.
The independent read established the direct-Dolt query chain:

- cmd/bd/list_input.go lines 249 to 264 and 304 to 315: explicit limit 129
  overrides all and piped-output defaults.
- cmd/bd/list_filter.go lines 310 to 312 and
  internal/storage/sqlbuild/filter.go lines 232 to 264: metadata becomes a SQL
  WHERE condition, not a filter applied after truncation.
- internal/storage/issueops/search_counts.go lines 46 to 120 and 148 to 153,
  plus internal/storage/sqlbuild/counts.go lines 94 to 110: matching issue and
  wisp identities are combined before the global limit; metadata is not dropped
  afterward.
- cmd/bd/list.go lines 42 to 46 and 522 to 552: the CLI requests one extra
  result internally, sorts and caps JSON output at 129. A saturated query cannot
  become falsely short through post-query metadata filtering.

Bound supplemental source hashes:

- cmd/bd/list.go: 32133f500c1716d5a28524fb886842de19de547c4f9dd03f35ba1b71f834fe1d
- internal/storage/sqlbuild/filter.go: 48c4c5ba2e81f460145d8e5d40d4107f15e00f0a26232a72a0893ce05607b56f
- module cache v1.2.2.info: 426c185a60536f4e3acb285c971c03b0ee77bbc7a239a17385044134268d5fab

## Regression disposition and next gate

The unchanged invocation-contract module passed eight tests in the already
authorized normal execution context using disposable temporary dependencies.
JUnit: /tmp/ga-rq5n-release-r3-invocation-02.xml. This is distinct from the
interrupted sandboxed run; its fixtures and incomplete evidence remain intact.
The complete adapter/meta suite is running under the same supported context.
Its terminal result will be appended separately, never inferred from progress.

The next executable candidate must bind a fresh task, workspace and consumed
roots, retain the reviewed transport semantics, and receive two independent
package reviews before guarded runner admission. No previous WORKTREE, PREP,
BIND or live-window operation is to be replayed. The final HALTED latch remains
untouched until that separately validated successor is admitted. The failed
ga-rq5n route and held ga-9olv product remain preserved.
