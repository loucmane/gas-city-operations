# Exact helper recovery R2 — independent HOLDs addressed

2026-09-28 CEST. The previous signed b6fdabe5442545ff712a8d72d32d6b064a4e7238
candidate received two independent HOLD verdicts. Both native transcripts were
exported losslessly and filed in the runner's reviews directory for that exact
commit. It cannot execute. No recovery root, archive operation, worker retry or
live configuration change occurred.

## Corrected findings

1. The reused actual-host observer itself called two GC diagnostics. Its unchanged
   PID, namespace, image, listener and service checks still run on the actual host.
   A closed command adapter now routes exactly status and session list through
   the same pinned read-only namespace and owned process runner. Other GC verbs
   refuse. Actual-city cwd, GC_CITY, GC_HOME, environment scrub, optional-lock
   setting and original diagnostic output bounds are retained. All other original
   command/check implementations remain intact.
2. Historical recovered-claim admission remains necessary but is not the
   pre/post equality proof. Each inspection now returns a digest of both complete
   normalized Beads, including notes, timestamps and dependency projections.
   Those two digests must be equal after archival. Any note change now refuses.
3. The reused owned-process runner's evidence writer is bound to exclusive,
   no-follow, file-and-directory-fsynced persistence in this exact fresh archive
   root. This does not alter its process containment or timeout logic.
4. An interrupted rename is not reported as no mutation merely because the
   archive function did not return. Failure records explicitly separate function
   completion from actual source/archive presence; all partial files remain,
   result publication and automatic replay stay prohibited.

## Exact final proof

- Executor SHA-256: 0b2458d691d93a1672757314a34f9e8c1efbc97f87df42adee18b4be28aec90a
- Test source SHA-256: fde409f1620b49d4ea028e47c44940cc6db9440b074ee575c71d27ba6cdad42d
- Final suite: 26 passed, zero failures/skips. JUnit file
  `/tmp/ga-e0t1-helper-fixtures-20260928-final.xml`, SHA-256
  ea816a1af5f9f4b01cd99744c6fb5ad68f5963f7922dbb92a9ba31fe09e70aff.
- Reproducible read-only proof harness: `probe_recovery.py`, SHA-256
  506b7d797ee611e25ac5ba9f8d6a10e67b6b4ca022c849831179f9638c503fdf.
  It loaded that exact executor, proved the original host contract including
  both transitive confined diagnostics and strict runtime assets, then executed
  the exact inner-before inspection through the pinned source launcher.
- Proof root `/tmp/ga-e0t1-r7-recovery/host-proof-final`; result SHA-256
  a94216b05f28f8b6132b7ac9e94be0e22112b2c51192da7676e932829d50db3d.
  Raw phase outputs, cleanup proof and both full host/inspection observations are
  preserved. Original 8036 entries still exact, helper still present, zero sessions
  and all rigs suspended. This calls no apply and is not live recovery acceptance.

The one-file archival scope, exact identity pins, fresh destination and job id,
NOREPLACE rename, original workspace checks and no-worker restriction remain
unchanged. Only the named recovery wrapper may be approved. The R7 window as a
whole is still unreviewed for execution. After two fresh passes, use the existing
runner once under the standing authorization. Preserve all failed evidence.
