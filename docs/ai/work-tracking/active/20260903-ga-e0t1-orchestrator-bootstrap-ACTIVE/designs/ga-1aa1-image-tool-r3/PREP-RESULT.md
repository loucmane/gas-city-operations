# ga-1aa1 PREP r1 — PASS, uninstalled

Executed once through the existing job runner on 2026-09-29 from
09:40:05 to 09:40:08 CEST. No worker launch, receipt installation, rig transition
or product implementation occurred. Do not replay this consumed root or job.

- Exact signed G package: `1648bfdf6115ec52dbdde09d7214b71fdc7925b9`.
- Job `ga-1aa1-prep-r1`: admitted true, exit 0, final unit inactive.
- Wrapper `operator/PREP.sh` SHA
  `a5ca6d8083c170c8c2fafd1672309559e6f49beba662ba5ae5609db32c4d14ac`.
- Both independent Astra reviewers returned SOURCE_PASS with no must-fix.
  Native identities `01a0ec17-bb53-7902-817e-667c845fabde` and
  `01a0ec17-dd89-7cb1-bb81-9b48d4cf368d`.
- Request `/tmp/ga-1aa1-prep-review-20260929-r1/request.txt`, SHA
  `035f45c83f5c38c1340ea84f1cd82956022f12d467469cc27f6e28c802bd3aaf`.
  Both lossless native review envelopes were filed before admission; all
  requests, rollouts and review evidence remain preserved.

## Measured outputs and non-interference

Root `/var/tmp/ga-1aa1-prep-20260929-r1` is consumed and preserved.

- Result SHA `9d2f728c09901014528b6760c8fa4fcbeedb80eb295b723fd82330dce742a898`.
- Isolated city image SHA `edaa6cf49669dfa559d10e0e5a11e92c34c4bb2ea9f5163a0fe2211b78d1bce8`.
- Isolated permission revision `8b9a6d11729b97b8174ac6f208613a6b2b1996cdbcb5fa30f8173d59e2570582`.
- Uninstalled receipt SHA `0c76e7b24b55d66d5875c263d25d9a8f2e65a9975af16e6087c44602fca65eca`.
- Receipt internal hash `bca9b245be0a513f0f239eded94467743ddfad0852d92d7e413cea7ee6bd26c3`.
- Complete receipt delta is exactly permission_revision plus receipt_sha256.
  All three typed profiles remain identical.
- Native configuration comparison passed: capacity one, the intended
  gascity/codex target and new workspace/prompt; only nudge-on-route is retained.
- Actual host runtime assets and exact protected history passed before PREP
  and before result publication. No host claim came from the normalize namespace.
- Normalize and finalize each exited zero, no timeout/primary error, direct
  child reaped, owned process group gone, no unexpected survivor, no signals sent.
- Live city SHA remains `bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1`.
- Live receipt SHA remains `7185414ebade17a1fdd7d485564e85f6ad8d7e0230983c21bf917f1ed27fb0ba`.
- Suspended-rig state remains `8ef1a8d6ecfb72d79e70d6fbe0ff5968c2ba9714a558ac9f44af14bcc14fe6b6`.
- Runner remains PID 2812303, monotonic start 301336188076, NRestarts 0.

The authoritative result.json has the correctly rebound gascity/codex identity
and added evidence bindings. The inherited S5 stdout prints its pre-decoration
dictionary, including the obsolete gas-city-template/codex label. This logging
limitation is not a different resolved configuration: use result.json and
config.isolated.json, never that inherited stdout label, for successor bindings.

## Evidence and next deliverable

- Job record `jobs/done/ga-1aa1-prep-r1.json` SHA
  `4214da6faf8e13dfe67c0f289e57bb33c832f0a044445e7c5614cc59f878fb72`.
- Wrapper log `ga-1aa1-image-tool-r3/prep-r1-20260929T074005Z.txt` SHA
  `51aec64c495525d0054038d31dbf4641e0bd58f101a4f04892f85e232778690e`.
  Both paths are under `/home/loucmane/.local/share/gas-city-staging`.
- Prior normal halt preserved at `jobs/state/HALTED.ga-1aa1-worktree-r1`, SHA
  `1cae9f3d3b076d1e718e48069169e3e5f864c5bb9ec2c209b8ac23f775210251`.
- The runner halted normally after PREP; no successor is queued.
- The first local commit invocation had an invalid gpg.program command-string
  setting and failed before invoking GPG or creating a commit. It was corrected
  to the unchanged configured signing path after cached readiness passed; no
  credentials, persistent configuration or candidate bytes changed.

ga-1aa1 remains open, unassigned and unrouted. Next: fresh bounded worker-window
assembly using these measured outputs and the successful R11 controls, with
fresh BIND rather than replaying the prior task's amendments or claims. Preserve
WORKTREE and PREP as completed operations. The full implementation, live startup
and release proof, two-file candidate review/intake, C1 and provider handover
remain unfinished. No acceptance criterion is closed by preparation alone.
