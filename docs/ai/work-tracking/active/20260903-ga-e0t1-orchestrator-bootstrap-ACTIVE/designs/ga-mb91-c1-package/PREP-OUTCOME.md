# ga-mb91 PREP outcome

30 September 2026 at 11:44:24 CEST. PASS, uninstalled preparation only.

Signed candidate `160cbd9e450fad22b22e5b254840abfab5e74c54` received two
independent Astra SOURCE_PASS reviews. Native envelopes are preserved under
`/tmp/ga-mb91-prep-reviews-20260930-r1` and filed with the runner. Review A is
`01a0f1aa-cd74-7ee3-901a-fd3547ed7eff`; B is
`01a0f1aa-ece5-78a0-8f31-c1e8f82f970f`. Neither reported a must-fix.

The completed WORKTREE latch was preserved through its exact reviewed helper.
`ga-mb91-prep-r1` then ran once, exited zero and its transient unit became
inactive. The runner halted afterward as designed. No worker launched and no
live configuration or receipt was installed.

- Result `/var/tmp/ga-mb91-prep-20260930-r1/result.json` SHA256
  `74e69f6f1f43098f236cb89d0b35709fd15b6b05ea76460249769d1d428310d7`.
- Runner done record SHA256
  `932eb87cbd299be61b74a30693d76666e64f53fa50d63c0dc6423725499970f5`.
- Uninstalled city image SHA256
  `b090821569aacef87d0efa910cc08bd4f1c62142e197f6ff570cc835d3d03273`.
- Uninstalled receipt SHA256
  `a6048ea44699972c0aff3672f11acb2b6427e46b1667bd909a23c1bd962e01dc`,
  self digest `76b0ae852fd85abbf69c06c890136e2b2982c51fd0a6c1dac277cbfa65f08a92`.
- Native configuration JSON explicitly reports
  `config.Session.NudgeQueueScope=session-epoch`. Configuration SHA256
  `91f5a94a6e95899d2b156d41a2accc9d8e0dbe30a6577e775b8e7511e2ab3bf1`.
- Both normalization and finalization returned zero with no timeout/error;
  direct children were reaped, owned groups gone, no unexpected survivors and
  no signals sent. Evidence is in the two phase JSON files, not inferred from
  the wrapper exit code alone.
- The native receipt changed only permission_revision and receipt_sha256;
  all three typed profiles were preserved. Retained Claude profile records do
  not represent Claude or Fable inference; the next source worker is Astra.
- Live city SHA256 remains
  `bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1`;
  live P14 receipt remains
  `2607e90522b5571a5180d882e3d21882bafbc42423e0855f11fae7ec00bdf980`.
- Supervisor remains PID 466463, start 517633096016, zero restarts,
  active/running. Rig suspension SHA256 remains
  `222da22682b755d2ddf4bc64a855ec9c906e38666c4fd17ea22d895419a34ff5`.

The console's inherited intermediate summary names gas-city-template/codex;
the successor's final result correctly names gascity/codex. Admission is bound
to the final result and native configuration, not that intermediate text.

Next: assemble the full window against these exact outputs, with foreign queue
and backing-Bead preservation captured before any poller-capable transition.
The existing Core delivery and M15/P14 adoption are complete and must not be
replayed. Full handover acceptance remains open. Preparation is not provider
parity or permission to skip the full-window independent reviews.
