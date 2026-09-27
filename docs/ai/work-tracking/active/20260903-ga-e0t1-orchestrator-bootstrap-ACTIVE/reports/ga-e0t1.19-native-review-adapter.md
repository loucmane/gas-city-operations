# ga-e0t1.19 — native Codex review evidence

Recorded 2026-09-27 CEST. Source candidate only; no runtime activation, queue filing,
worker model change, service transition, rig lifecycle, or worker launch.

## Authority and scope

The operator approved direct Codex implementation of this repair alone, requiring
independent Astra review before activation. The repair is attached to ga-e0t1 under
the existing external-coordinator ownership and remains in progress and unassigned.
All other implementation still belongs to Gas City workers. The C1 d10 CLOSE
admission defect is separate and is not changed here. Its independent HOLDs remain.

## Candidate

Only the existing jobrunner's review admission gains a second format. A native Codex
subagent rollout is preserved losslessly inside a versioned JSON envelope, alongside
the exact frozen request and both byte digests. Because the native task payload is
encrypted at rest, the request binding is an explicit SHA-256 acknowledgment in the
genuine native final answer, not a claimed plaintext prompt recovery. No Claude
sidechain or handback records are fabricated. Independent review must evaluate this
stated provenance contract. Existing historical reviews without the acknowledgment
are not silently upgraded to the new protocol.

The parser validates one native spawned identity and parent, approved Astra model
and effort, contiguous record ordinals, one ordered turn, the request sender and
recipient, one final answer, and its matching terminal completion. Distinct-reviewer,
any-filed-HOLD, exact candidate/wrapper, signed clean HEAD, replay, PAUSE, HALTED,
single-job, source integrity and job-execution gates remain unchanged. The exporter
is create-only and cannot file a review or queue/launch a job. Both existing runner
launch scripts pin the new source digest.

## Evidence

- Focused RED: `/tmp/ga-e0t1.19-native-review-red-20260927.xml`, 3 failures and 4 passes.
  The failures expose one missing native parser, not three independent defects.
- Initial focused GREEN: `/tmp/ga-e0t1.19-native-review-green-20260927.xml`, 7 passes.
- Exporter regression attempt: `/tmp/ga-e0t1.19-jobrunner-regression-20260927.xml`,
  51 passes and 3 failures. The exporter correctly refused; the tests expected the
  exception class of a separately loaded copy of the module. Corrected only that
  test import expectation, without weakening production refusal behavior.
- Runner and adapter regression: `/tmp/ga-e0t1.19-jobrunner-regression-green-20260927.xml`,
  54 passes. Existing Claude and execution guards are included.
- Final runner and adapter regression after native launch-context and newline-boundary checks:
  `reports/ga-e0t1.19-native-final-r2-regression-20260927.xml`, 56 passes.
- Full required adapter/meta suites: `reports/ga-e0t1.19-required-regression-20260927.xml`,
  3962 passes and 21 existing optional or legacy skips, zero failures. The shared gate,
  packaged assets and adapter/meta test inputs were unchanged during that run. The
  separate final runner suite covers the new native parser and exporter.
- Managed consumer golden parity passed without changes. `git diff --check` passed.
- Source guard initially refused inherited daily evidence. That refusal is not
  overridden. After the separately approved bounded reconciliation and supported
  plan sync, source guard and all six workflow verification checks pass.
- Staging the raw RED/intermediate JUnit reports exposed trailing whitespace in
  their captured tracebacks. The initial signed checkpoint
  `1730016a994762008582d4d23eb3e4926c0adbb2` preserves those raw bytes, as do the
  original `/tmp` reports. The repository copies now encode only trailing spaces
  and tabs as XML character references. An XML parse/serialization comparison
  proves identical decoded evidence. No production source changed for this
  formatting correction; the full candidate diff check must pass before delivery.
- Read-only parsing of the genuine prior Astra B rollout confirms its native
  Desktop identity, launch context and completion shape. It correctly refuses at
  the missing frozen-request acknowledgment, rather than converting that historical
  report into admissible evidence. Its original bytes and HOLD remain unchanged.

## Approved daily-evidence reconciliation

The inherited uncommitted handoff entry recorded at 18:48 CEST on September 27 was
appended to the September 24 session. The operator explicitly approved preserving
its complete before-image, moving only that entry into a proper September 27
continuation, and restoring September 24 to its committed bytes.

- Complete before-image: `reports/ga-e0t1.19-session-before-20260927.md`, SHA-256
  `a9ad202afd2c6e5e56c3129365483aa8a431b0293b31994799de9acd14fb59e5`.
  A second identical backup remains at `/tmp/ga-e0t1.19-session-before-20260927.md`.
- The supported `sessions continue` transaction created the September 27 continuation
  and updated the tracked pointers/state and derived current-work together, reusing
  the existing plan and tracker. No replacement task or worktree was created.
- The single uncommitted entry was relocated verbatim, with its original timestamp,
  to `sessions/2026/09/2026-09-27-001-ga-e0t1-orchestrator-bootstrap.md`.
- A byte comparison against the HEAD blob proves the September 24 file is now
  exactly committed history. No older lines were changed, even where the historical
  record already contains cross-day entries. The other four handoff surface entries
  remain intact.

## Remaining acceptance

Freeze a signed candidate, obtain two independent Astra source reviews, and validate their real
native exports in an isolated fixture. Retain standing delivery and merge gates.
Any eventual runner activation needs exact backups, quiet staging, minimum service
transition, loaded-byte proof and rollback. No activation or C1 dispatch is implied
by source PASS or by this record.
