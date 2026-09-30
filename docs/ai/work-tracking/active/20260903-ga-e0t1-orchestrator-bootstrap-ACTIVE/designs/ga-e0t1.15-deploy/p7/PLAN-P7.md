# ga-e0t1.15 S3, part 2: the P7 worker provisioning receipt refresh

M6 (S3 part 1) is accepted. The live platform is:
- release `template-pr71-core-seq14-metadata-m6-20260925`;
- manifest file `7f335ad8` (self digest `3076e67e`);
- receipt file `123a0181` (self digest `14b17cd5`);
- acceptance `df7db3fa` under `reports/m6/q`.

The canonical Template is at `cfd353f3`. Signing launches still refuse, because the worker
provisioning receipt `0b30c23f` names Template `28539934`, provider version `f36deb20`, Core member
head `796d9a7a` and permission revision `d6ca85cd`. P7 re-pins exactly those four things, through the
unchanged reviewed provisioner `64425a72`, exactly as P6 did on 2026-09-23.

## Why the diagnostics are rebuilt

The P6 composition and preflight diagnostics were compiled from Core `796d9a7a`. Two facts were
measured on 2026-09-25:
- Run read-only in bwrap, the old compose diagnostic still yields revision `d6ca85cd`.
- The live controller, now at `9faeabc2`, traces revision `2113693e`, from cycle records by PID 2940569.

The new Core's embedded core pack changes the composed revision, so the old diagnostic can no longer
reproduce the live composition. The reviewed builders (`prepare-compose.py` `4d8a1586` and
`prepare-preflight.py` `47cfa684`, in durable staging) are rebound by count-checked substitution:
- the Core commit becomes `9faeabc2`, tree `c9f19d21`;
- the source is the S1 reproduction clone `/var/tmp/ga-e0t1.15-build-20260925/repro-source`, not a
  live repository;
- the output roots are fresh, and the preflight's generated sources go under `/var/tmp`.

They produced:
- compose `e123ee37` in `/var/tmp/ga-e0t1.15-compose-diagnostic-20260925`;
- preflight `510f4d72` in `/var/tmp/ga-e0t1.15-preflight-diagnostic-20260925`, with extraction
  `93da115b`;
- the unchanged phase runner `eddf5e11`.

Run read-only in bwrap, the rebuilt compose diagnostic yields revision `2113693e`, which equals the
live trace. It also yields the unchanged argv (model `claude-opus-5-5`) and environment.

## Package (`designs/ga-e0t1.15-deploy/p7`)

`make_p7.py` generates everything from reviewed bytes loaded by digest. `builders` makes the two
diagnostic builders. `scripts` rebinds the executed P6 chain, which is input `f0150b63`, compose
`43b94ce6`, readiness `7b28b3e5` and adopt `64879d2a`. Each substitution states its exact old text and
count. The module docstrings are replaced, and the P6 bodies are otherwise changed only by:

| Script | Rebinding |
| --- | --- |
| `p7-input.py` | See below. |
| `p7-observe-compose.py` | See below. |
| `p7-readiness.py` | Fresh root. The P7 observer and composition. The preflight diagnostic `510f4d72`, its extraction `93da115b`, and its pinned generator sources in this directory (`preflight-main.go` `75c897e0`, `prepare-preflight-p7.py`). |
| `p7-adopt.py` | Fresh root. The P7 readiness. The old receipt `0b30c23f`. The readiness constants reset to None. `CORE` `9faeabc2`. The consumer tree `c9f19d21`. The reviewed-build evidence (`/var/tmp/ga-e0t1.15-build-20260925/artifact-verification.json` `e78516c5`). The traced controller PID 2940569. `m5` renamed to `m6`. |

**`p7-input.py`:**
- a fresh root;
- `GC_SHA` `b2760ea4` and `CORE` `9faeabc2`;
- the old receipt `0b30c23f`;
- Template `28539934` → `cfd353f3`;
- `REVISION_OLD` `d6ca85cd`;
- versions `f36deb20` → `d4e57767`;
- `derive()` now asserts that the argv model `claude-opus-5-5` is unchanged, and moves
  `member_heads[core]` `796d9a7a` → `9faeabc2` from its exact predecessor;
- `m5_acceptance` becomes `m6_acceptance` over `reports/m6/q`, requiring the M6 release, the PR 71
  authority, and succession from the M5 file `2d7eadce`.

**`p7-observe-compose.py`:**
- a fresh root, and the P7 input pinned by digest;
- the compose diagnostic `e123ee37`;
- `GC_SHA` `b2760ea4`;
- the host epoch: boot `3f1f4534`, supervisor 2940569/123479699122, signer 2310/39660502, broker
  2940285/123477220085;
- the builder digest check against the P7 compose builder;
- the S3 access-time neutral policy, installed on every observer load. It is loaded from the reviewed
  `s3/metadata_closure.py` `4fa0698b`, so the before and after snapshots compare everything except
  atime.

Copied unchanged: `source-launch.py` `31bdeea8`, `typed-interoperability.json` `315dd410`,
`compose-main.go` `e8cb87a0` and `preflight-main.go` `75c897e0`. The typed-interoperability
evidence's three test sources and the provisioner are byte-identical at `cfd353f3` (checked
2026-09-25). The Core diff `796d9a7a..9faeabc2` touches only `internal/sling/cycle.go`, the core pack
`nudge-on-route.sh`, `.gitignore` and their tests. The receipt decoder the interop test exercises is
unchanged, so the evidence still applies.

`test_p7.py` has 15 tests:
- the exact derivation delta against the live receipt: exactly five leaves change, plus the three
  generated fields;
- refusals on every predecessor;
- `m6_acceptance()` on the real records;
- the reviewed provisioner's `load_prototype` accepting the draft;
- byte-exact regeneration of all ten generated files;
- the digest chain;
- the build records.

## Read-only run and adoption binding (r2, 2026-09-25)

`f72173dc` received two independent SOURCE_PASS verdicts with no must_fix.

Before step 1, a read-only rehearsal ran the provisioner's `gc version --json` corroboration in bwrap
(read-only, no network, the adopt environment). It returned commit `9faeabc2` with `ok: true`, and the
city shim stayed `a7bcaa7c` (review B should_fix 4). The reviewed-build evidence file is mode 0644 with
nlink 1.

Steps 1 to 3 then ran once, each passing, at the reviewed commit:
- **input:** result `6c415b4b`, draft `c047b4d9`, traced revision `2113693e`.
- **compose:** ok. The composition equals the draft, before equals after, and nothing was installed.
- **readiness:** ok, all six phases, unchanged.
  - Preflight is OK on all 12 checks, including `provider_readiness` and `signer`.
  - The subscription is claude.ai, max, logged in.
  - The old PATH refused at `worker_profile_sha256`.
  - Discovery bound `1e08503d`.
  - The finalized receipt `7cf59ab9` has self digest `ee4400af`. It names Template `cfd353f3`, Core
    `9faeabc2`, revision `2113693e` and version `d4e57767`.

r2 fills only the five adoption constants:
- `NEW_SHA` `7cf59ab9` and `NEW_SELF` `ee4400af`;
- `READY_RESULT_SHA` `a6cac0b9`, `READY_BEFORE_SHA` `1d9b0e35` and `READY_PINS_SHA` `82a4a70c`.

The `p7-adopt.py` digest is then `697116dd`. `test_adoption_constants_bind_the_readiness_evidence`
binds each constant to its evidence file. The generator test normalizes exactly these five lines back
to `None`, so it still proves every other byte. There are 16 tests.

## Run order

Every step runs as `systemd-run --user --wait --collect --pipe --quiet -p UMask=0022
/usr/bin/python3 -I -S -B p7/source-launch.py p7/<script> <sha256>`. Before each step, the package
worktree must be clean at the reviewed commit.

1. `p7-input.py`: writes the draft, the preserved old receipt, the traced revision and the result.
2. `p7-observe-compose.py`: the network-isolated composition in bwrap. It must equal the draft (argv,
   environment, revision `2113693e`), with before equal to after.
3. `p7-readiness.py`: normalize, finalize, discover, the negative old-PATH case, subscription
   `auth status`, and preflight, including the signer `--probe`. No inference and no signing.
4. Fill the five adoption constants from the readiness evidence. Commit, then get two independent
   reviews of the readiness evidence and the adoption package.
5. `p7-adopt.py`: a receipt-only transaction through the unchanged provisioner. `--check` must find
   only `receipt.sha256`; then `--apply`, then verify. Exact rollback on failure.
6. Get two reviews of the adoption evidence, then the S4 acceptance window.

**Quiescence.** From step 1 until the adoption log ends, nobody runs gc except the scripts' own trace
reads (which use `GIT_OPTIONAL_LOCKS=0`), nobody runs `workflow.py`, and nobody writes a Bead note. The
snapshots compare the pack cache and the platform files exactly.

**Stop conditions.** Stop on any of these, and never re-run into a consumed root:
- any refusal;
- host epoch drift;
- composition drift from the draft;
- an authentication posture other than subscription;
- a pinentry prompt;
- drift outside the receipt;
- any reload or lifecycle need.
