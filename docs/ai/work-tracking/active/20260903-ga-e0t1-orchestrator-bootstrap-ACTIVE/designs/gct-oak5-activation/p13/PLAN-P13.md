# P13: worker receipt revision refresh after the A2 codex choice (gct-oak5)

## Why

The installed worker receipt `7125be84` (P12) pins `permission_revision` `06076790`. The reviewed A2 codex-choice activation (`cdcdaccd`, applied `f17c55a9`) changed city.toml. The controller now reports revision `a61666b3…f58f`; that is the A2 reload acknowledgement, which P13's input re-traces live. M12 adopted that city.toml, with manifest file `114b4a00`.

Until P13 is installed, every Claude worker start refuses on the revision mismatch, which fails closed.

## Delta

Exactly one leaf changes: `permission_revision` moves `06076790` → `a61666b3`.

Everything else is asserted unchanged:
- all three profiles: Template candidate `2341a9a0`, signing `ad0c695b` and Operations candidate `e641dc17`;
- Core `f45a6262` and the Template `3474abfa`;
- the pack, the rules and the canary runner.

The installed receipt is sorted by name. `derive()` therefore takes the profiles by name and returns them in the P12 input order: signing, Operations candidate, Template. The observer and readiness compare index by index in that order, and the provisioner sorts again.

## Package

`make_p13.py` generates the package from the executed P12 chain by count-checked substitutions. `make_p12.py` is pinned by digest, because its `DERIVE_P12` is the text P13 replaces.

- **`p13-input.py`:**
  - the new `derive`;
  - `m12_acceptance()` over `reports/m12/q`, with release `gct-oak5-codex-candidate-choice-metadata-m12-20260927`, predecessor file `9f60c3bf`, and the unchanged canonical Template authority;
  - a fresh root.
- **`p13-observe-compose.py`, `p13-readiness.py` and `p13-adopt.py`:** rebound to fresh roots, the P13 input, the M12 acceptance and the M12 copy of `metadata_closure.py` (byte-identical, `ce310593`).
- **Reused diagnostics:** no diagnostic is rebuilt. The P11 signing, Operations candidate and preflight builds and the P12 Template build are reused by digest, and a test checks every constant against P12.
- **Adoption constants:** the five readiness constants stay `None` until readiness passes.

## Dry proof (2026-09-27, read-only)

`test_p13.py` passes 22, with 1 skipped until readiness:
- the exact delta, including the reorder;
- the profile constants equal P12's;
- 11 predecessor refusals and 2 revision refusals;
- the provisioner keeps all three digests and changes only the revision and the receipt self digest;
- all three compositions run in `bwrap --ro-bind / / --unshare-net` at revision `a61666b3`, each equal to its draft profile;
- the reused diagnostics are P12's;
- the adoption witness;
- `m12_acceptance()` on the real records;
- byte-exact regeneration.

## Run order

Each step runs once, as `systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 /usr/bin/python3 -I -S -B <p13>/source-launch.py <p13>/<script> <sha256>`:
1. Two SOURCE_PASS reviews of this package.
2. `p13-input.py`.
3. `p13-observe-compose.py`.
4. `p13-readiness.py`.
5. Fill the five adoption constants. Commit, then get two reviews.
6. `p13-adopt.py`.
7. Two adoption readback reviews.

**Quiescence** runs from step 2 until the adoption log: no gc except the scripts' own reads, no `workflow.py`, no Bead write, and nothing routes to or unsuspends an agent.

**Stop conditions.** Stop on any of these, and never re-run into a consumed root:
- any refusal;
- host epoch drift;
- a revision other than `a61666b3`;
- a controller pid other than 2800348;
- composition drift;
- a preflight or negative result other than P12's pattern;
- an authentication posture other than subscription;
- a pinentry prompt;
- drift outside the receipt.

**Rollback.** `p13-adopt.py` restores the exact old bytes `7125be84` automatically, and only after clean containment.

## Read-only run and adoption binding (2026-09-27)

Source reviews: two independent SOURCE_PASS of `b723b246`, no must_fix. The should_fix items are follow-ups:
- a duplicate-name refusal test;
- refusal tests should assert `RuntimeError` with its reason;
- wording: the signing profile and the canary runner are bound by the receipt digest and the provisioner runner pin, not field by field in `derive()`;
- `m12_acceptance()` reads `restored.json` and `manifest.json` without a digest. This is inherited, and the manifest digest is cross-checked against the acceptance.

Runs, at about 14:05 CEST (12:05 UTC), each once:
- **Input:** result `2873fc7b`, draft `7b8472f6`, revision `a61666b3`.
- **Composition:** ok and unchanged at `/var/tmp/gct-oak5-p13-compose-20260927`.
- **Readiness:** ok and unchanged, with all ten phases done.
  - The signing, Operations candidate and Template preflights passed all twelve checks.
  - The three negatives stop at `worker_profile_sha256 mismatch` after exactly four checks.
  - The auth posture is subscription, claude.ai max.

Finalized receipt: file `7185414e`, self `c78b3a24`. Its profiles are Template `2341a9a0`, signing `ad0c695b` and Operations candidate `e641dc17`, all unchanged.

Adoption constants:

| Constant | Value |
| --- | --- |
| `NEW_SHA` | `7185414e` |
| `NEW_SELF` | `c78b3a24` |
| `READY_RESULT_SHA` | `eaabc9f3` |
| `READY_BEFORE_SHA` | `432559c3` |
| `READY_PINS_SHA` | `82a4a70c` |

`READY_RESULT_SHA` is byte-identical to P12's; see the note after the adoption record.

## Adoption (2026-09-27)

Adoption-binding reviews: two independent SOURCE_PASS verdicts of `64a0981f`. `git diff --stat b723b246 64a0981f` shows only `p13-adopt.py` (five constants) and this plan changed. The committed `p13-adopt.py` hashes to `059e4086`, the digest the run was launched with.

`p13-adopt.py` ran once at about 14:10 CEST (12:10 UTC). It returned ok, rollback not-needed and worker_launched false.
- **Receipt:** `7125be84` became `7185414e`, self `c78b3a24`, mode 0600, one link.
- **Provisioner:** check found drift exactly `receipt.sha256`; apply and verify returned ok with drift [], runner `3beeedb2`.
- **Witness:** `c284a9f4` binds the M12 acceptance `fc841bf3` (manifest `3f3b51eb`, receipt `8b89ec30`) and gc `207a78e2` at `f45a6262`, tree `f1011ada`.
- **Revision:** `a61666b3`, controller 2800348.
- **Snapshots:** with the receipt pin removed, before and after are equal. The coordinator recomputed this, and the provider pins are byte-equal.

Readback: two independent ADOPT_PASS verdicts of `64a0981f`, no must_fix.

Note on `READY_RESULT_SHA`: `result.json` holds no root or digest that differs between the two runs. `READY_PINS_SHA` is also unchanged, because the provider pins carry no atime.
