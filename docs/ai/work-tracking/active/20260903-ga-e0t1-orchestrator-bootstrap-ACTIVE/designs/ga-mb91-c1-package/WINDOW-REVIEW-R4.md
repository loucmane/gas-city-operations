# ga-mb91 R4 — preserve BIND and supersede the pre-mutation observation

R3 signed 022495898d995d5311cd4921b04a35273ca3e7ed received two
independent Astra SOURCE_PASS verdicts. BIND then completed PASS.
OBSERVE r1 refused at its initial baseline comparison before native integrity,
configuration staging, routing, resumption or any worker launch.

## Exact cause and disposition

The coordinator's post-BIND workflow note omitted GIT_OPTIONAL_LOCKS=0.
The process environment lacked that variable; workflow_common.managed_environment
preserves inherited values. Core packman.cachedRepoDirty invokes git status.
The cache .git directory mtime and ctime advanced at 13:03:24.990519059 CEST,
coincident with that note. This is the already-documented coordinator optional
Git-lock effect, not permission to ignore arbitrary metadata drift.

Full non-atime comparison between accepted baseline and refused observation:
only cache inventory
954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git
mtime_ns and ctime_ns changed from 1790761620278169157 to
1790766204990519059. Every other compared field remained exact.
The subsequent corrected ledger note used GIT_OPTIONAL_LOCKS=0.
Fresh actual-host capture afterward is byte-identical to the refused observation.
Provider pins remain exact. No timestamps or cache objects were written by recovery.

Evidence:
- Refusal root /var/tmp/ga-mb91-integrity-20260930-r1 contains exactly intent.json
  6840d428b0c808cf9ca857270668b95cce24c87e5d4abd24b586c03582260ebb
  and before-refused-observation.json
  339e7ab62a5f2a1aa06af1ef4bc72441de18512edd2d36016e2c8308a61afbc4.
- Job ga-mb91-observe-r1 finished exit 1, unit inactive.
  Done d1a5573f66de311be6437a2fad176c76aea40b0747f6e9b2c0fd304693d93e2e.
  HALTED 5fbfed47127e3779f7c996e041764194b28a2af335936d5233b0389b772cf9e3.
- Fresh /tmp/ga-mb91-readonly-baseline-20260930-r2/observed.json has the same
  339e7ab6 digest. Its result.json proves zero additional non-atime/provider
  differences. Capture source /tmp/ga-mb91-readonly-baseline-r2-20260930.py
  9b34800afd7e378b3fe85b148b610097824858ac3c80347be0b57da25340bca2.
- Completed BIND result remains
  02cedf2952f9839e88b9599414f3ba4eb58751cbc026753ebc2b4f668fe0a25d.

## Bounded successor

The full baseline checks remain exact against the newly observed, digest-bound
baseline. Only OBSERVE's output root and its consumer references advance to r2.
All unstarted worker-window roots remain r1. WORKTREE/PREP/BIND are not replayed.
The original BIND executor remains byte-exact
028ccef1db747088c7f8552c86094ded85b5db12f1d58d890bd7678fa432adea,
and ROUTE retains that historical executor binding. BIND.sh now exits 125 before
any command, making completed-operation non-replay structural.

preserve-observe-refusal.py is an exact retarget of the earlier reviewed
ga-goo5 helper. It checks the failed job's commit, exit 1, inactive unit,
exact two-file refusal inventory and digests, absent window/route roots,
completed BIND digest, clean signed current candidate, empty queue and no PAUSE.
It only archives the exact HALTED inode using no-replace rename and fsync.
It never queues a job or grants a PASS to the failed observation.
Its SHA256 is ec0725ce82d83199b4e94052e31e5fe9e4c5f2b349d19e955745e001a1a5f3b8.
The ordinary successful-latch helper adds only ga-mb91-observe-r2.

R3 manifests remain in ASSEMBLY-REVIEW-R3.json and TEST-REBINDING-REVIEW-R3.json.
ASSEMBLY-REVIEW-R4-DELTA.json records every regenerated digest.
No product implementation, runtime configuration, privilege or check relaxation.
Standing completion authority covers the reviewed corrected successor.

## Verification and execution

Focused assembly: 40 PASS. Final full offline package suite: 621 PASS, no failures,
errors or skips, 2.27 seconds. JUnit /tmp/ga-mb91-r4-final-20260930.xml,
2bdc9d3942e72a583fba67cd2ca5d812ba3cc00716361b858b66d82b31e12ca1.
Three added cases prove exact completed binding, real BIND-wrapper refusal and
the exact failure-latch predicate. All other previously reviewed queue/release/
containment/restoration tests remain green. This is source proof only.

After two independent SOURCE_PASS reviews: archive only the diagnosed failed
latch, submit ga-mb91-observe-r2, then PREFLIGHT through TERMINAL and INSPECT.
No BIND, WORKTREE or PREP replay. No workflow or Bead command between observation
freeze and TERMINAL, including outcome notes; the runner results preserve each
outcome, then one consolidated terminal ledger entry records them.
Every coordinator gc/bd/workflow command outside that interval carries
GIT_OPTIONAL_LOCKS=0. No Fable inference. One expected Astra worker only.
Any additional unexplained drift remains a stop, not another automatic re-pin.
