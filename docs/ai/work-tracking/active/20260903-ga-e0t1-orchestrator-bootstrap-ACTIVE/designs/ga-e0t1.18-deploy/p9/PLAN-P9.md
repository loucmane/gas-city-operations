# P9: the worker receipt refresh for the revision the lane activation moved

The ga-6utp r12 activation reload composed the candidate agent and the `claude-candidate` provider. That moved
the controller's permission revision from `2113693e` to `83c41af6` (the activation's reload record). The live
signing-lane receipt `23eeb222` (from P8) pins `2113693e`, so signing launches and Core's managed dispatch gate
refuse until the receipt names the running revision. M8 (manifest file `63820eac`) is accepted and the M8
inspector reports zero drift.

**What P9 changes.** Exactly one leaf: `permission_revision` moves from `2113693e` to the traced running
revision. The traced value must differ from the old one and must be well-formed 64-character hex. Everything
else is asserted unchanged:
- the core member head `deefb98b`;
- the Template `cfd353f3`;
- the provider version `d4e57767`;
- the model `claude-opus-5-5`;
- the single signing profile.

The candidate lane's typed receipt belongs to the first candidate window. Before any receipt carries a candidate
profile, its wrapper must be pinned in the platform providers (M8 review A should_fix 1).

**Package.** `make_p9.py` rebinds the executed P8 chain (input `30f5e510`, observer `31444d33`, readiness
`d440a6c0`, adopt `f75be251`) by count-checked substitution. The bindings that change:
- fresh roots;
- the old receipt `23eeb222`;
- the derivation, which moves the revision and keeps the core head;
- `m8_acceptance()` over `reports/m8/q`, the M8 release, and succession from the M7 file `4bec5ef1`;
- the adoption constants, reset to None.

The Core image is unchanged, so P9 reuses P8's reviewed diagnostic builds (compose `e123ee37`, preflight
`73d4e14c`). Its readiness reads the pinned generator sources from the P8 package directory
(`SUCCESSOR=HERE.parent/'p8'`). The host epoch, closure policy and surviving watchdog image are unchanged.

**Tests.** `test_p9.py` has 18 tests:
- the exact one-leaf delta;
- refusals on every predecessor and on an unmoved or malformed revision;
- the activation's recorded revision;
- `m8_acceptance()` on the real records;
- the reviewed provisioner accepting the draft;
- byte-exact regeneration;
- the reused builds;
- the adoption constants, which run once they are filled.

## Run order

This is P8's order, with absolute paths and one invocation each, as
`systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 /usr/bin/python3 -I -S -B <p9>/source-launch.py
<p9>/<script> <sha256>`:
1. `p9-input.py`.
2. `p9-observe-compose.py`.
3. `p9-readiness.py`.
4. Fill the five adoption constants. Commit, then get two reviews.
5. `p9-adopt.py`.
6. Get two adoption readback reviews.

**Quiescence** runs from step 1 until the adoption log. There is no gc except the scripts' own reads, no
`workflow.py`, and no Bead write. Nothing may unsuspend the candidate agent.

**Stop conditions.** Stop on any of these, and never re-run into a consumed root:
- any refusal;
- host epoch drift;
- a traced revision equal to `2113693e`;
- composition drift from the draft;
- an authentication posture other than subscription;
- a pinentry prompt;
- drift outside the receipt.
