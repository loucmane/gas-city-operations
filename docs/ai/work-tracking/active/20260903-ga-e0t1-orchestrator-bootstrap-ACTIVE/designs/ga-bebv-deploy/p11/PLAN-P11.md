# P11: refresh the worker receipt for Core f45a6262 and the M10 revision (ga-bebv S3)

M10 is accepted (manifest file `2b902a83`, receipt file `c0853ca3`, acceptance `8354675b`). The installed worker
provisioning receipt `c833908f` (P10, self `6bb7ca5b`) is now stale in exactly two leaves:
- `member_heads[core]` is `deefb98b`, but the live gc `207a78e2` was built from `f45a6262` (sequence 16);
- `permission_revision` is `83c41af6`, but M10's city.toml `e5b68c40` moved the composed revision. The
  controller's cycles since M10 report `config_revision` `03f16ea2`, `gc_commit` `f45a6262`, controller pid
  `2800348`, completed, with no active template.

Core's start preflight compares the receipt's revision with the running one, so until P11 every managed launch
of either lane would fail closed.

## The delta (P10 receipt → P11)

Exactly two leaves change, through the unchanged reviewed provisioner `64425a72`:

| Field | P10 | P11 | Source |
| --- | --- | --- | --- |
| `member_heads[core]` | `deefb98b` | `f45a6262` | sequence 16 build and receipt `1108b724` |
| `permission_revision` | `83c41af6` | `03f16ea2` | the live controller trace, pinned exactly |

Everything else is asserted unchanged:
- both profiles: the signing lane `ad0c695b` and the candidate `e641dc17`;
- the Template `cfd353f3`, the pack, the rules and the canary runner;
- the provider versions and the model.

## Diagnostics, rebuilt from Core f45a6262

The compositions and the preflight must be Core's own code at the running commit. Three builders run offline:
- **`prepare-compose-p11.py`.** This is the reviewed P8 exact-source builder (`56f3ca48`) with four bindings
  moved: the Core source is the sequence 16 reproduction clone
  `/var/tmp/ga-bebv-build-20260927/repro-source`, the commit is f45a6262, the tree is f1011ada, and the root is
  fresh. It builds the unchanged P8 signing composition `compose-main.go` (`e8cb87a0`) to `8fb47061`.
- **`prepare-compose-candidate-p11.py`.** This runs the same builder over `candidate/compose-main.go`, the
  unchanged P10 candidate composition (`5040c196`), and builds it to `8cb667dc`.
- **`prepare-preflight-p11.py`.** This is the P10 preflight builder over the P11 builder and signing root, with
  the unchanged `preflight-main.go` (`cb55f252`). It builds to `85a2cc6b`, with extraction `8160f4ec`.

The Core diff deefb98b..f45a6262 does not touch the extracted functions. The only change in `cmd/gc/cmd_start.go`
is in `resolveConfiguredWorkDir`, outside the four environment functions.

## The chain

`make_p11.py scripts` generates the chain from the executed P10 chain by count-checked substitution:

| File | Change from P10 |
| --- | --- |
| `p11-input.py` | Old receipt `c833908f`, `GC_SHA` `207a78e2`, and `CORE_OLD` → `CORE`. `derive()` pops both profile digests and asserts both profiles unchanged (the candidate equal to P10's `CANDIDATE`). It moves the revision from `83c41af6` to exactly `03f16ea2`, and the Core member head from `deefb98b` to `f45a6262`. `m10_acceptance()` binds `reports/m10/q`, the M10 release and succession from the M9 file `5a29dc59`. The controller cycle must report `gc_commit` f45a6262. |
| `p11-observe-compose.py` | Fresh root and the P11 input. It uses both P11 compositions, the P11 builder digest, gc `207a78e2`, the sequence 16 core epoch (2800348 / 229642910742; signer and broker unchanged) and the M10 pair. The policy module is `m10/metadata_closure.py`, the same bytes `ce310593`. |
| `p11-readiness.py` | Fresh root, the P11 observer and compositions, and the P11 preflight build, builder and extraction. |
| `p11-adopt.py` | Fresh root and the P11 readiness, with its constants reset to None. The old receipt is `c833908f`. The witness names Core f45a6262 with tree f1011ada, the sequence 16 build verification (`b37088d9`) and the M10 acceptance. The traced controller pid is 2800348. |

`source-launch.py` and `typed-interoperability.json` are byte-identical to P10's.

**Read-only dry proof (2026-09-27, scratchpad `p11dev/dry_preflight.py`).** Every native step ran in
`bwrap --ro-bind / / --unshare-net`. The steps:
1. Derive the draft from the live receipt.
2. Normalize it with the reviewed provisioner. Both profile digests are unchanged.
3. Finalize it with the P11 diagnostic; the result equals the normalized receipt.
4. Run Core's preflight for both profiles:
   - signing passed every check through `signer`;
   - candidate passed every check through `no_signer`;
   - both negatives stopped exactly at `worker_profile_sha256 mismatch` after `check_path_stamp`.

These are P10's results.

**Tests.** `test_p11.py` has 23 tests; 22 run before readiness. They cover:
- the exact two-leaf delta;
- that the candidate constant equals P10's;
- predecessor refusals, and refusal of any revision other than `03f16ea2`;
- the provisioner keeping both profile digests;
- both compositions, run read-only against the draft;
- the build records against the sources and the builder;
- the builder's diff from P8;
- the adoption witness bindings;
- `m10_acceptance()` on the real records;
- byte-exact regeneration of all twelve files, and compilation of every script;
- the adoption constants, once readiness has passed.

## Run order

Use P10's order, each step once, as
`systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 /usr/bin/python3 -I -S -B <p11>/source-launch.py <p11>/<script> <sha256>`:
1. Get two SOURCE_PASS reviews of this package.
2. Run `p11-input.py`.
3. Run `p11-observe-compose.py`.
4. Run `p11-readiness.py`.
5. Fill the five adoption constants. Commit, then get two reviews.
6. Run `p11-adopt.py`.
7. Get two adoption readback reviews.

**Quiescence** runs from step 2 until the adoption log:
- no gc except the scripts' own reads;
- no `workflow.py`;
- no Bead write;
- nothing unsuspends an agent.

**Stop conditions.** Stop on any of these, and never re-run into a consumed root:
- any refusal;
- host epoch drift;
- a revision other than `03f16ea2`;
- a controller pid other than 2800348;
- composition drift from the draft for either profile;
- a preflight or negative result other than the dry proof's;
- an authentication posture other than subscription;
- a pinentry prompt;
- drift outside the receipt.

## Read-only run and adoption binding (r2, 2026-09-27)

r1 `ccd1eec0` received two SOURCE_PASS verdicts with no must_fix. Steps 2 to 4 then ran once each, all passing,
at the reviewed commit:
- **input:** result `7ccb7b82`, draft `68fb232e`, and the traced revision is `03f16ea2`.
- **compose:** ok and unchanged. Both profiles' observed argv, environment and revision equal the draft.
- **readiness:** ok and unchanged, with no inference, signing or worker. All eight modes completed:
  - the finalized receipt is `06a3f58a`, self `7363291e`, with revision `03f16ea2` and core `f45a6262`;
  - the profile digests are still `ad0c695b` and `e641dc17`;
  - Core preflight passed for signing (ending in `signer`) and for the candidate (ending in `no_signer`);
  - both negatives stopped at `worker_profile_sha256 mismatch` after `check_path_stamp`;
  - subscription posture: claude.ai, max.
  These are exactly the dry proof's results.

r2 fills the five adoption constants:
- `NEW_SHA` `06a3f58a` and `NEW_SELF` `7363291e`;
- `READY_RESULT_SHA` `ebccc145`, `READY_BEFORE_SHA` `71473463` and `READY_PINS_SHA` `82a4a70c`.

**Review notes carried (no must_fix):**
- **Profiles (A 1, A 2, B 2).** "Both profiles unchanged" holds by construction: `RECEIPT_OLD_SHA` pins the
  input bytes, `derive()` leaves the signing profile untouched and compares the candidate in full, and
  readiness shows both digests unchanged. The scripts do not re-assert the signing check path or the two
  digests at run time; the adoption reviews check them in the evidence.
- **Interop evidence (A 3, B 4).** `typed-interoperability.json` is historical wire-compatibility evidence at
  Core 796d9a7a, carried forward as in P8 to P10. The live wire proof at f45a6262 is the readiness finalize.
- **Core diff (A 4).** The claim that the extracted functions did not change is backed by the extraction's eight
  function digests and the `environment_sha256` `f17f520f`, both identical to P10's build.
- **Tests (A 5, B 3).** The builder-diff test is by set membership; byte-exact regeneration covers order. The
  unchanged boot, signer and broker pins were checked by hand against the sequence 16 postflight.
- **Canary receipts (B 1).** P11 changes the revision and the receipt digest, so every existing canary receipt
  goes stale. Any managed-product dispatch needs a canary minted after P11.
- **Composition equivalence (B 5).** The diagnostic builds the argv with `BuildProviderLaunchCommand`; production
  uses the resolved command plus default and settings args. They agree while neither wrapper provider carries
  schema flags in its base command, as today.

**Carried from P10.** The receipt is bound to the config revision, so any later city.toml change makes it
stale again. This includes the `title_model` follow-up from M10, which will need its own receipt refresh. The
adoption pins controller pid 2800348 and fails closed on a supervisor restart.
