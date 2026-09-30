# Consolidated review corrections and source-only checkpoint

Recorded 2026-09-29 CEST under AUTHORIZATION.md. No new approval is requested:
the two transport modules, their tests and later packaging bindings remain the
complete direct-bootstrap exception. All rigs remain suspended and the previous
failed window remains terminated and preserved. No runtime activation occurred.

## Independent review disposition

Candidate 24198a2f3a92d8dc841d72691c6a147ef1565dac received HOLD from the two
independent Astra aegis-reviewer lanes aegis_rq5n_transport_r12_a and
aegis_rq5n_transport_r12_b. Both found receipt-list truncation could conceal an
older release behind ordinary reminders. Review A also found the absent-marker
directory chain was not checked before enqueue. Both recommended bracketing the
last executable read with a final process-table identity sample. The restricted
Core-parent ancestry model and its explicit limitations were accepted; numeric
PPID alone is not authority. These findings are preserved, not overwritten by the
successor result.

## Exact correction

- The supported Beads list help was read without mutation and documents an
  explicit limit. The adapter now queries at most 129 matching session receipts
  and refuses a malformed result or a full page. Only a list shorter than the
  requested limit is treated as complete. This same rule applies before enqueue
  and during every acknowledgement observation. No unlimited history request or
  invented pagination API is used.
- Directory validation is factored into marker_directory and required before
  branching on marker existence and again before enqueue. The existing marker
  reader retains it too. Symlinked, write-shared and missing directories refuse
  even when the marker does not exist. No directory or marker is created by this
  adapter and the only native mutation remains the one supported enqueue.
- A final process-table read follows both the final node observation and the
  second executable hash. PID, start, UID, GID, PPID and live-state must still
  match. This is bounded race detection, not a claim of atomic procfs snapshots.
- The delivery predicate module is unchanged from the first R12 candidate.

## Tests and honest limits

The additional targeted tests were first run with the previous runtime loaded:
11 failed and 38 were deselected. Receipt saturation reached the old bounded
observation exhaustion rather than refusing before enqueue; the other cases
demonstrated missing refusal. Source edits during that already-loaded run mean
pytest traceback display lines can reflect the subsequent on-disk revision.
The RED JUnit remains at /tmp/ga-rq5n-release-r3-review-red-20260929.xml.

The corrected complete focused corpus passes 134 tests in disposable fixtures:
/tmp/ga-rq5n-release-r3-focused-r2-20260929.xml. The harness now uses a fake clock,
so timeout-negative cases no longer wait 90 real seconds. New tests cover hidden
older releases, complete ordinary-reminder histories, saturation before and after
enqueue, unsafe absent-marker directories, final identity loss and mid-read
image, argv, executable-path and cgroup changes. The original 113-pass evidence
and immutable old-gate refusal reproduction remain preserved.

The additional full adapter/meta regression invocation did NOT pass: after
progress to roughly 54 percent and two failure indications, it stopped producing
output while its MCP stdio test child remained alive. The invocation-contract
test uses the SDK stdio client without a timeout; a neighboring existing test
explicitly documents this client's hang in this environment. The coordinator
interrupted only this owned test invocation. Exit was 130, no final JUnit was
produced, and read-only host inspection confirmed test PID 2079960 and its child
2179415 exited. No unrelated process was touched. The failure details were not
emitted by this interrupted run, so their causes are not claimed proven. Existing
test fixtures under /tmp/ga-rq5n-release-r3-regression-01 remain intact. No tests,
runtime or dependencies were changed to hide this result. Required downstream
publication gates remain outstanding; this checkpoint is source review only.

## Ledger resolution

The previously refused combined long note and status command remains preserved
in the live outcome. A separate supported status-only command subsequently set
ga-rq5n from open to blocked. Exact before/after readback at
/tmp/ga-rq5n-status-disposition-20260929.json shows only status and updated_at
changed. Native route, session and failure metadata were preserved; there is no
new assignment or worker. This resolves the owed status disposition, not the
failed work or the full goal.

## Next gate

Obtain two independent reviews bound to the next exact signed candidate. No
package execution or completed-job replay follows from source tests or a review
alone. Package assembly must use fresh consumed roots and reviewed bindings,
preserve the current final HALTED latch, and retain all live technical gates.
