# P10: the typed candidate receipt profile

This is step 2 of the first Operations candidate window, RECEIPT (ga-cw-first-window PLAN; gct-lagl HANDOFF 2.8:
"Add a typed candidate receipt profile under the identity actually resolved, then provision"). It follows:
- M9, which pins the candidate wrapper in the platform providers;
- P9, the installed worker receipt `6bf20a71`, which carries the signing profile only.

**Why it matters at launch.** Core's start preflight (`cmd/gc/managed_worker_preflight.go`) classifies a
session as managed by receipt membership alone. For every identity in the receipt it compares:
- the exact launch argv Core composed;
- the check-path stamp on the driving Bead;
- the environment;
- the provider pin;
- the toolchains;
- the control policy;
- the provider readiness.

A signing profile also needs the signer; a candidate profile explicitly needs no signer. Without P10 the
candidate would launch unmanaged, with none of these checks. With a P10 profile that is wrong, every candidate
launch would fail closed at preflight. So P10 proves the profile against Core's own composition and preflight
before anything is installed.

## The complete delta (P9 receipt → P10)

One profile is appended. Every other field, including the signing profile, is asserted unchanged:
- the revision `83c41af6`, which must still be the running one;
- the core `deefb98b`;
- the Template `cfd353f3`;
- the rules;
- the pack;
- the canary runner.

The signing profile's `worker_profile_sha256` stays `ad0c695b`.

| Field | Candidate profile | Source |
| --- | --- | --- |
| `name` | `gascity/operations-candidate-worker` | the r12 reload's resolved `qualified_name` |
| `profile_kind` / `signer_identity` | `candidate` / `none` | the typed no-sign contract (Core and the provisioner refuse any other pairing) |
| `argv` | wrapper, `--permission-mode dontAsk --effort max --model claude-opus-5-5 --settings <candidate policy> --add-dir /home/loucmane/gas-city-ops-candidate-worktrees --settings <city settings>` | Core's own composition (below) |
| `environment` | `PATH=/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin` | Core's composition; equal to the reviewed registry record |
| `control_policy` | `templates/claude/candidate-control-policy.json` `a3eda916` | the registry record; exactly once in argv, outside the writable root |
| `provider` | `claude` at `bin/gct-claude-candidate-worker` `e4442971`, version `…a35dd413` | equal to the M9 pin |
| `toolchains` | python `/usr/bin/python3.12` `e50d468e`, `Python 3.12.3` | the registry record (gct-lagl HANDOFF 2.5's refreshed pin) |
| `check_path` | the signing lane's `build-artifact-valid.sh` `71f17450` | the stamp the window's bind step writes as `gc.check_path` |
| `writable_roots` | `/home/loucmane/gas-city-ops-candidate-worktrees` | the registry `worktree_root` |
| `approval_policy`, `network_policy`, `sandbox_mode` | `dontAsk`, `no-explicit-egress-denial`, `claude-native-required-with-five-command-exclusions` | the argv, and the candidate policy's five excluded commands |

The claude CLI is not a separate toolchain. The registry record does not list it, and the provider version
line hashes it, together with the policy and the launch sources.

## Diagnostics (built before review, like P8's)

The reviewed P8 exact-source builder `prepare-compose-p8.py` (`56f3ca48`) runs unchanged from Core `deefb98b`,
into fresh roots:
- **`compose-main.go` `5040c196`.** The P8 composition diagnostic with four substitutions: the target
  identity, the `claude-candidate` provider, and `PATH` as the only override. It builds to `53450168` in
  `/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926`. A scratch probe build earlier gave the same bytes.
- **`preflight-main.go` `cb55f252`.** The P8 preflight diagnostic, changed in three ways:
  - it accepts one or more receipt profiles;
  - it takes the environment key set from the named profile;
  - its negative appends a PATH entry instead of the signing lane's old PATH order.
  It builds to `c6dd9ebb`, with extraction `a30af307`, in `/var/tmp/ga-e0t1.18-p10-preflight-diagnostic-20260926`.

`make_p10.py diagnostics` generates both sources and the builders `prepare-compose-p10.py` and
`prepare-preflight-p10.py`. The builders only rebind roots.

**Read-only dry proof (2026-09-26, scratchpad `p10dev/dry_preflight.py`).** Every native step ran in
`bwrap --ro-bind / / --unshare-net`. The steps:
1. Derive the draft from the live receipt.
2. Normalize it with the reviewed provisioner.
3. Finalize it with the diagnostic; the result equals the normalized receipt.
4. Run both compositions: the candidate composition equals the draft profile.
5. Run Core's preflight:
   - signing passed every check, the signer included;
   - candidate passed every check, ending in `no_signer`;
   - both negatives stopped exactly at `worker_profile_sha256 mismatch` after `check_path_stamp`.

## The chain

`make_p10.py scripts` generates the chain from the executed P9 chain by count-checked substitution:

| File | Change from P9 |
| --- | --- |
| `p10-input.py` | Old receipt `6bf20a71`. `derive()` asserts the unchanged revision and appends `CANDIDATE`, asserting the signing profile's name, kind and check path. The live candidate wrapper must report its pinned version. `m9_acceptance()` binds M9, succeeding the M8 file `63820eac`. |
| `p10-observe-compose.py` | Runs the signing (`e123ee37`) and the candidate (`53450168`) composition in one read-only namespace. Each must equal its draft profile. Writes `composition.json` and `composition-candidate.json`. The snapshot pins add the four candidate files. |
| `p10-readiness.py` | The P10 preflight build. Modes: normalize, finalize, discover, the negative for each profile, subscription (both policies inspected), then the preflight for each profile. |
| `p10-adopt.py` | Old receipt `6bf20a71`, the P10 readiness, and the M9 acceptance in the typed-support witness. The five constants are None until readiness passes. |

`source-launch.py` and `typed-interoperability.json` are byte-identical to P9's.

**Tests.** `test_p10.py` has 22 tests. They cover:
- the exact delta;
- the candidate profile's typed and bound fields against the live files, the registry record and the M9 pin;
- predecessor and revision refusals;
- the provisioner accepting both profiles with the signing digest unchanged, and refusing a candidate with a
  signer;
- Core's composition for both identities, run read-only;
- the build records against the sources;
- byte-exact regeneration of all ten files;
- compilation of every script;
- `m9_acceptance()` and the adoption constants, each once its evidence exists.

## Run order

Run after M9 is accepted. Use P9's order, each step once, as
`systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 /usr/bin/python3 -I -S -B <p10>/source-launch.py <p10>/<script> <sha256>`:
1. `p10-input.py`.
2. `p10-observe-compose.py`.
3. `p10-readiness.py`.
4. Fill the five adoption constants. Commit, then get two reviews.
5. `p10-adopt.py`.
6. Get two adoption readback reviews.

**Quiescence** runs from step 1 until the adoption log:
- no gc except the scripts' own reads;
- no `workflow.py`;
- no Bead write;
- nothing unsuspends the candidate agent or creates a worktree under the candidate root.

**Stop conditions.** Stop on any of these, and never re-run into a consumed root:
- any refusal;
- host epoch drift;
- a revision other than `83c41af6`;
- composition drift from the draft for either profile;
- a preflight or negative result other than the dry proof's;
- an authentication posture other than subscription;
- a pinentry prompt;
- drift outside the receipt.
