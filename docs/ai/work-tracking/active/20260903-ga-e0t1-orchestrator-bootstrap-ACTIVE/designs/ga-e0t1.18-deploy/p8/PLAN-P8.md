# ga-e0t1.18 S3, part 2: the P8 worker provisioning receipt refresh

M7 (S3 part 1) is accepted. The live platform is:
- release `template-pr71-core-seq15-metadata-m7-20260926`;
- manifest file `4bec5ef1` (self digest `8f9d1be1`);
- receipt file `3be61bf5` (self digest `bd9c25d4`);
- acceptance `a803f84c` under `reports/m7/q`.

The worker provisioning receipt `7cf59ab9` (P7) still names Core member head `9faeabc2`. P8 re-pins exactly
that one leaf to `deefb98b`, the sequence 15 build source, through the unchanged reviewed provisioner
`64425a72`. Everything else is asserted unchanged:
- the Template `cfd353f3`;
- the permission revision `2113693e`;
- the provider version `d4e57767`;
- the model `claude-opus-5-5`.

The revision stays the same because S1's provenance shows no embedded pack path changed between `9faeabc2`
and `deefb98b`. The input step still traces it live and refuses any other value.

## Diagnostics

The P7 builders (`prepare-compose-p7.py` `4fda9c34`, `prepare-preflight-p7.py` `aa0bf8fd`) are rebound by
count-checked substitution:
- the Core commit becomes `deefb98b`, tree `af5c3f04`;
- the source is the S1 reproduction clone `/var/tmp/ga-e0t1.18-build-20260926/repro-source`;
- the roots are fresh.

They ran on 2026-09-26 and produced:
- **Compose diagnostic `e123ee37`,** byte-identical to P7's, in `/var/tmp/ga-e0t1.18-compose-diagnostic-20260926`.
  This agrees with an unchanged composition and revision.
- **Preflight `73d4e14c`, extraction `e32de6fb`,** in `/var/tmp/ga-e0t1.18-preflight-diagnostic-20260926`.
  This one changed, as expected: PR 48 changed `internal/managedworker`.

## Package (`designs/ga-e0t1.18-deploy/p8`)

`make_p8.py` generates everything from the executed P7 chain, loaded by digest:
- input `9b711394`;
- observer `7aadb805`;
- readiness `ef43c620`;
- adopt `697116dd`.

Each substitution states its exact old text and count. The bindings that change are:

| Script | Rebinding |
| --- | --- |
| `p8-input.py` | Fresh root, `GC_SHA` `fce2e9a0`, `CORE` `deefb98b` over `CORE_OLD` `9faeabc2`, and the old receipt `7cf59ab9`. `derive()` asserts the Template, revision and version unchanged and moves only `member_heads[core]`. `m7_acceptance()` covers `reports/m7/q`, the M7 release, and succession from the M6 file `7f335ad8`. |
| `p8-observe-compose.py` | Fresh root, the P8 input and compose diagnostic, and `GC_SHA` `fce2e9a0`. The supervisor epoch is 995924/163987392096; the boot, signer and broker are unchanged, as observed live. The policy module is the M7 `s3/metadata_closure.py` `ce310593`. `OLD_IMAGE` stays `69d00186`, the image the surviving dolt watchdog maps. |
| `p8-readiness.py` | Fresh root, the P8 observer and composition, and the preflight diagnostic `73d4e14c` with its extraction `e32de6fb`. |
| `p8-adopt.py` | Fresh root and the P8 readiness. The readiness constants are reset to None. The old receipt is `7cf59ab9`. `CORE` is `deefb98b`, tree `af5c3f04`. The reviewed-build evidence is `/var/tmp/ga-e0t1.18-build-20260926/artifact-verification.json`. The traced controller PID is 995924. `m6` is renamed to `m7`. |

Copied unchanged: `source-launch.py` `31bdeea8`, `typed-interoperability.json` `315dd410`, `compose-main.go`
`e8cb87a0` and `preflight-main.go` `75c897e0`.

`test_p8.py` has 19 tests:
- the exact one-leaf delta against the live receipt;
- refusals on every predecessor and on any other revision;
- `m7_acceptance()` on the real records;
- the reviewed provisioner accepting the draft;
- byte-exact regeneration of all ten generated files;
- the watchdog image and policy binding;
- the digest chain and the build records.

## Read-only run and adoption binding (r2, 2026-09-26)

r1 `cb3257f6` received two independent SOURCE_PASS verdicts with no must_fix. Steps 1 to 3 then ran once
each, at that commit and passing, with absolute paths (review B should_fix 4):
- **input:** result `e030b19e`, draft `f2b3f4ce`, traced revision `2113693e`, unchanged as required.
- **compose:** ok. The composition equals the draft, before equals after, and nothing was installed.
- **readiness:** ok and unchanged. No inference, signing or worker.
  - The finalized receipt `23eeb222` has self digest `076fff66`. It names core head `deefb98b`, Template
    `cfd353f3`, revision `2113693e` and version `d4e57767`.

r2 changes:
- The stale "P7" comment in `p8-adopt.py` becomes "P8" through a new counted substitution in `make_p8.py`
  (review A should_fix 1, review B should_fix 5). Regeneration changes only `p8-adopt.py`.
- The five adoption constants are filled:
  - `NEW_SHA` `23eeb222` and `NEW_SELF` `076fff66`;
  - `READY_RESULT_SHA` `a6cac0b9`, `READY_BEFORE_SHA` `70572871` and `READY_PINS_SHA` `82a4a70c`.
  `p8-adopt.py` is then `f75be251`.
- `test_adoption_constants_bind_the_readiness_evidence` binds each constant to its evidence file. There are
  20 tests.

Review notes carried as follow-ups:
- As in P7, the observer installs the closure policy on a throwaway namespace. So `OLD_IMAGE` and the
  dolt-scope check are inert in P8, and only the access-time neutral overrides apply (review B should_fix 1).
- The host observation also runs `gc status` and `gc session list` (review B should_fix 2).

## Run order

Every step runs as `systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 /usr/bin/python3 -I -S -B
p8/source-launch.py p8/<script> <sha256>`. Before each step, the package worktree must be clean at the reviewed
commit.

1. `p8-input.py`.
2. `p8-observe-compose.py`.
3. `p8-readiness.py`, which includes the signer `--probe`, with no inference and no signing.
4. Fill the five adoption constants from the readiness evidence. Commit, then get two reviews.
5. `p8-adopt.py`: `--check` must find only `receipt.sha256`, then `--apply`, then `verify`.
6. Get two reviews of the adoption evidence.

**Quiescence.** From step 1 until the adoption log ends: no gc except the scripts' own trace reads, no
`workflow.py`, and no Bead note.

**Stop conditions.** Stop on any of these, and never re-run into a consumed root:
- any refusal;
- host epoch drift;
- composition drift from the draft;
- a revision other than `2113693e`;
- an authentication posture other than subscription;
- a pinentry prompt;
- drift outside the receipt;
- any reload or lifecycle need.
