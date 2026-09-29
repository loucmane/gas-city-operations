# Release transport R12 — consolidated source review

Task: ga-e0t1 coordinating the ga-rq5n release-gate bootstrap exception.
Authorization: AUTHORIZATION.md in this directory. The original full goal is
unchanged. This is a source candidate, not permission or evidence of live release.

## Frozen source scope

- release-runtime-r12.py: append-forward successor of consumed R2
  release-runtime-r11.py, whose SHA256 is
  baf4f1c1a8ac4c2a32ec51427cb39ec430795a5d68ab4ac8bbda62db5fd3b936.
- release-delivery-r12.py: successor of consumed R2 release-delivery-r11.py,
  SHA256 370bd378c1d57246a7b20e3f7628e8234e2eea1e8bf29482f0a841bef56eec3d.
- conftest.py and test_runtime.py, test_marker.py, test_delivery_regression.py.
- No consumed operational source, installed runtime, Core source, worker content,
  policy, queue, session, service or receipt was changed.
- Packaging must put these reviewed bytes into a fresh successor, rebind all
  digest references and consumed-root admissions, and receive its own normal
  package review before execution. Neither module has a live CLI entrypoint.

## Defect and correction

The old adapter refuses any existing session poller marker. The actual native
Core supports reusing its matching poller, which can remain after an ordinary
startup reminder. The companion predicate incorrectly required that poller to
belong to the later RELEASE oneshot.

The successor preserves the exact caller oneshot requirement. An absent marker
retains the new release-owned helper branch. An existing marker instead requires
a read-only, identity-bracketed process observation: PID/start ticks, parent PID,
UID/GID, exact executable path and hash, exact session argv and exact reviewed
Core service cgroup. It binds that identity before enqueue and requires it
unchanged through acknowledgement. It also binds the marker inode, mode, owner,
link count, size, times and digest; no symlink, hardlink or write-shared file or
parent is admitted. Read errors, stale processes and ambiguity refuse.

Core itself is bound to the already-reviewed PID 2800348, start ticks 22964291,
exact argv and native image digest, and the exact service cgroup. These pins are
part of this host-window contract, not general host discovery. A changed epoch
requires normal reviewed package rebinding, never silent acceptance.

Existing-poller ancestry is restricted to Core's PID or Core's current parent
PID. This supports native detached children reparented after the CLI exits.
The latter numeric relationship does NOT independently authenticate the parent's
executable or prove live provenance; authority rests additionally on the exact
Core unit cgroup, native image and session argv, with stable Core/poller identity.
This limitation is explicit for review. Unknown intermediate ancestry refuses.

The existing single enqueue, exact session epoch, preserved historical queue,
native receipt AND transcript ingress, bounded wait and no-replay semantics are
unchanged. No direct tmux delivery, poller start, deletion or signalling is added.

## Evidence and limits

Focused suite: 113 passes, zero failures, in the disposable fixture run at
/tmp/ga-rq5n-release-r3-focused-20260929.xml. It includes the exact preserved
R11 module refusing the existing-poller fixture, while R12 reaches native-shaped
receipt plus transcript acknowledgement. Tests replace command/process
observations; they do not prove a real provider received a release.

Real temporary files exercise marker integrity. The copied pure delivery corpus
retains its immutable R10 enqueue-only evidence test. No new service-lifetime
synthetic run has occurred. The inherited real new-helper lifetime evidence is
unchanged, and does not prove existing-poller adoption.

Full adapter/meta regression result is recorded separately after completion.
A noninteractive signing-readiness proof succeeded using the configured key
with pinentry disabled, without credential changes.

## Review questions

1. Is the dual admission model correctly bounded and its authority explicit,
   including ancestry and host-service identity limitations?
2. Are pre-enqueue identity and marker races, post-enqueue PID reuse, Core drift,
   and unsafe paths fail-closed without mutation, resend or cleanup?
3. Does one enqueue still require exact native receipt AND transcript ingress,
   with epoch, historical queue, timeout and no-replay checks retained?
4. Do the tests expose the actual old defect and preserve the negative cases,
   without counting fixtures as live acceptance?
5. Is the candidate scope limited to the operator-approved bootstrap exception?

Request SOURCE_PASS or HOLD for the one exact signed commit named by the review
prompt. Cite must-fix defects separately from optional hardening. Do not execute
code, rerun tests, edit, delegate, route or touch live state.
