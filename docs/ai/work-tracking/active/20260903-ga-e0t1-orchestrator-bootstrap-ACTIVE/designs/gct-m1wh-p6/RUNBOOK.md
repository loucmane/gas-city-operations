# P6 receipt refresh (ga-0t04, LAYOUT.md step 6)

This package sits in `designs/gct-m1wh-p6` of the ga-e0t1 worktree and is reviewed per commit. It runs
only after M5 has recorded `restore-accepted` with COMMIT_PASS, which happened on 2026-09-23 at
11:50:01Z. The P6 runtime check `m5_acceptance()` accepts those real records: package 090c89ba,
acceptance 7c064544, live pair 2d7eadce/9342b33e. Every script is a P6 rebind of the reviewed 09-20 chain. The only
new file is `p6-input.py`.

## Sources

| File | SHA-256 | Base |
| --- | --- | --- |
| `p6-input.py` | `88f1ec2f` | new: derivation, M5 record proof, trace selection |
| `p6-observe-compose.py` | `b83e5fd0` | `observe-compose.py` `be8461f4` |
| `p6-readiness.py` | `649ffa11` | `run-readiness.py` `6ac87f25` |
| `p6-adopt.py` | `7750f350` | `adopt-receipt.py` `4d9857fc` (readiness constants None) |
| `source-launch.py` | `31bdeea8` | unchanged |
| `typed-interoperability.json` | `315dd410` | unchanged; the three test sources are identical at 28539934 |
| `test_p6.py` | `edfbd7b1` | 17 tests |

Reused unchanged by digest:

- the compose diagnostic `9f837c83` and the preflight diagnostic `edbc0fa1`, both built from Core `796d9a7a`;
- `phase_runner.py` `eddf5e11`;
- `preflight-main.go` `75c897e0` and `prepare-preflight.py` `47cfa684`;
- the provisioner `64425a72`, runner `3beeedb2`, subscription library `3b92bc92` and reviewed-build evidence `fd131744`.

## Binding delta (the whole change)

- **Receipt input:** the installed receipt `01ed1bce`, minus `canary_runner`, `receipt_sha256` and
  `worker_profile_sha256`. Five leaves change, and each requires its predecessor:
  - `template_commit` and `member_heads[template]`: `ff683ed6` → `28539934`;
  - `permission_revision`: the traced running revision, which must differ from `ebeefe97`;
  - `provider.version`: `b7fee446` → `f36deb20`;
  - `argv[6]`: `claude-opus-5` → `claude-opus-5-5`.
- **Toolchains:** unchanged, go only. The receipt profile toolchains are independent of the registry
  rig toolchains. The registry already listed claude 26d02035 while the accepted receipt listed only go.
- **M5 metadata:** no constants. `m5_acceptance()` proves the committed pair from:
  - `reports/m5/q/commit-pass.json`, with two distinct provenance files;
  - `committed-acceptance.json`, the digest the review binds;
  - `restored.json`, accepted;
  - the `manifest.json` release `template-pr69-opus55-metadata-m5-20260923`, whose
    `previous_metadata.manifest_sha256` is the R9 file `a6324753` and whose last repository is
    `template-pr69-authority` at `28539934`. The top-level `previous_sha256` is the previous Core
    binary, not a manifest link; corrected 2026-09-23 after the real-baseline build;
  - the live pair bytes.
- **CLI:** worker `/home/loucmane/gascity/bin/claude` `26d02035` → `1e08503d` (M5 `cli` step). API
  package `claude.exe` and its alias, `1e08503d`, inode 3576768, size 233709640, 2 links; re-verified at
  run time.
- **Host epoch:** unchanged. Supervisor 3150812/84619011818, signer 5550/208267863, broker
  2862577/77125780270, boot f4e38c6a. Checked 2026-09-23.

## Order (host terminal, supervisor namespaces)

`P` is this directory. Steps 1-3 run from a real WSL terminal as one wrapper:
`sh $P/operator/P6-READONLY.sh <reviewed commit>`.
- The wrapper runs each step as `systemd-run --user --wait --collect --pipe --quiet -p UMask=0022
  /usr/bin/python3 -I -S -B $P/source-launch.py $P/<file> <pinned sha256>`.
- Before each step it checks that the worktree is clean at the reviewed commit, and it stops at the
  first refusal.
- WSL terminal sessions sit outside the supervisor mount namespace, and user-manager children
  otherwise inherit umask 0002; see the M5 executor-entry finding of 2026-09-23.
- Nobody runs gc while these steps run, because the composition and readiness snapshots compare the
  pack cache. A gc Bead call touches the pack cache repo.

1. `p6-input.py 88f1ec2f…`: writes the draft, the preserved old receipt, the revision and the result
   under `/var/tmp/gct-m1wh-p6-input-20260923-r1`. Read-only otherwise.
2. `p6-observe-compose.py b83e5fd0…`: the network-isolated composition. The actual argv, environment and
   revision must equal the proven draft. The cache and protected trees are preserved.
3. `p6-readiness.py 649ffa11…`, in this order:
   - normalize, then finalize (Template and Core must agree);
   - discover (1e08503d);
   - the negative old-PATH refusal;
   - subscription `auth status`;
   - preflight, including the signer `--probe`. No inference and no signing.
4. Fill the five adoption constants from the readiness evidence:
   - `NEW_SHA`: `receipt.final.json`;
   - `NEW_SELF`: its `receipt_sha256`;
   - `READY_RESULT_SHA`, `READY_BEFORE_SHA` and `READY_PINS_SHA`.
   Then two independent reviews of the readiness evidence and the adoption package.
5. `p6-adopt.py <sha>`: a receipt-only transaction through the unchanged provisioner (`--check` finds
   only `receipt.sha256`, then `--apply`, then verify). Exact rollback on failure.
6. Two reviews of the adoption evidence, then `gc platform canary`.

## Run record and adoption binding (r2)

The package commit `a1759c01` received two independent SOURCE_PASS reviews with no must-fix. The
operator then ran `operator/P6-READONLY.sh a1759c01…` once, from 12:04:26Z to 12:07:47Z:
- **input:** result `060565e1`, draft `24c1ca75`, running revision `d6ca85cd`.
- **compose:** ok, under `/var/tmp/gct-m1wh-p6-compose-20260923-r1`. The actual argv, environment
  and revision equal the draft, before equals after, and nothing was installed.
- **readiness:** ok, under `/var/tmp/gct-m1wh-p6-readiness-20260923-r1`. All six phases completed
  and the run was unchanged; no inference, no signing, no worker.
  - normalize equals finalize: Template and Core agree.
  - discover bound `1e08503d`.
  - The old path refused at `worker_profile_sha256`.
  - The subscription is claude.ai, max, logged in.
  - Preflight OK on all 12 checks, including provider_readiness and signer.
  - The finalized receipt `receipt.final.json` is `0b30c23f`, with self digest `c635e8ee`. It names
    Template 28539934, revision d6ca85cd, provider version f36deb20, model claude-opus-5-5 and
    toolchain go.

r2 fills only `p6-adopt.py`:
- `NEW_SHA` 0b30c23f and `NEW_SELF` c635e8ee;
- `READY_RESULT_SHA` a6cac0b9, `READY_BEFORE_SHA` af7ef094, `READY_PINS_SHA` a5f7f8c1.

Its digest becomes `917c1635`. The three scripts that ran stay byte-identical: adoption loads them by
digest. The test now binds the constants to the readiness files. `operator/P6-ADOPT.sh` runs the
adoption detached, as its own user unit with output to a file. It checks the reviewed clean commit,
pins `917c1635` and requires a fresh adoption root.

Start it, after the two reviews of this evidence and package, with
`systemd-run --user --unit=gct-m1wh-p6-adopt --collect -p UMask=0022 sh $P/operator/P6-ADOPT.sh <commit>`.
Nobody runs gc until its log ends.

## Stop conditions

Stop on any of these:

- any refusal;
- a host epoch change;
- composition drift from the draft;
- an authentication posture other than subscription;
- a pinentry prompt;
- drift outside the receipt;
- any reload or lifecycle need;
- a typed-interoperability change.

Never retry into a consumed root. A retry uses a new root name and a new review.
