# ga-e0t1.15: deploy the silent-start fixes

Operator approval (2026-09-25, about 17:25 CEST): "i approve and i want it prepared asap". It
answered the request to prepare the reviewed deployment of both silent-start fixes. It covers
preparing this package and applying it through the reviewed path. Any new privilege or scope
found while preparing is reported before the live apply.

## What changes live

| Fix | Merged source | Live effect |
| --- | --- | --- |
| ga-odny: nudge-on-route accepts the supervisor API `{bead}` payload | Core PR 47, merge `b6843d3f` | routed workers are nudged without a coordinator KICK |
| ga-nibd: typed routing cycle detection | Core PR 46, merge `728b9687` | valid parent-waits-child graphs route; real cycles still refused |
| gct-jkgf: `--add-dir` grants before the role prompt | Template PR 71, merge `cfd353f3` | the role prompt reaches the signing and candidate workers |

Scope check:
- The live Core `gc` `69d00186` was built from `796d9a7a`, whose tree `f2c120a5` equals the tree of
  `e6366b9e`.
- `git diff 796d9a7a b6843d3f` touches exactly `internal/sling/cycle.go`, the core pack
  `nudge-on-route.sh`, `.gitignore` and their tests. Nothing else in Core changes.
- On the Template side, e6195b10..cfd353f3 is PR 71 only.

## Stages

Each stage has its own reviewed commit and live evidence, and needs the one before it.

### S1: offline custody build (done, offline)

`build.py` makes two independent no-hardlink clones of the locally signed build-source `9faeabc2`.
Its tree `c9f19d21` is byte-identical to the GitHub merge `b6843d3f`; the GitHub web-flow signature
cannot be verified locally, and the custody audit requires `verify-commit`. The build uses the
sequence 13 custody profile.

Result `/var/tmp/ga-e0t1.15-build-20260925`:
- Artifact `b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489`, 134052980 bytes, 0755.
- Reproducible across both clones.
- 7120 audited inputs, 1541 of them Git-bound; the input set is identical before and after the builds.
- result.json sha `ef023196`.

`verify.py` runs the byte-identical production validator `validateMetadataCustodyBuild` (`87e6855e`,
unchanged in the new source):
- it accepts the live `69d00186` and both new artifacts;
- it refuses the preserved incompatible `83d098fc`.

### S2: Core binary adoption, broker sequence 14 (live)

The successor of the sequence 13 custody adoption (staging
`ga-mutg-20260920/ga-mutg-custody-adoption-20260920`):
- the fixed broker operation `replace-gas-city-control-plane.v1`;
- Bead `ga-ecwh`;
- `69d00186` → `b2760ea4`;
- the same capture, recheck and submit mechanism and the same postflight pair.

Changes from sequence 13:
1. The reviewed chain sources (r8 → r4 → r3 → base) are re-homed from the wiped `/tmp` roots to
   their retained staging copies, each proven by its reviewed digest.
2. The accepted predecessor is a fresh, reviewed read-only closure of the current accepted image,
   the R7 `observe.py` successor. The old R7 `second.json` predates M5, P6 and the worker windows,
   so it cannot be reused.
3. Postflight waits for city initialization before its exact comparison, the sequence 13 lesson
   (its first postflight refused while initialization was pending). The corrected singleton
   cgroup-member transition from the sequence 13 recovery is carried forward.

It runs from a real terminal under `systemd-run --user -p UMask=0022` (memory m5-executor-entry). The
reconcile timer is paused and restored as in sequence 13. All rigs stay suspended.

### S3: metadata and receipt refresh (live)

A successor of M5 and P6:
- The platform metadata release moves the Template authority to `cfd353f3`.
- The worker provisioning receipt re-pins:
  - `template_commit` and `member_heads[template]` to `cfd353f3`;
  - `provider.version`, whose `dependency_version` hashes the changed boundary module;
  - the Core `gc` digest to `b2760ea4`.
- The candidate lane receipt is re-pinned the same way before its first window.
- The canonical Template checkout is fast-forwarded to `cfd353f3` only inside this stage's reviewed
  window, never before. With a fast-forward alone, the receipts would no longer match.

### S4: acceptance

One worker window, the successor of ga-nibd, re-pinned to the new images:
- no KICK;
- the worker claims from the routed nudge;
- the role prompt arrives as the first message.
Its package drops the KICK phase. Evidence goes on ga-e0t1.15.

## Stop conditions

These apply unchanged:
- any drift from a reviewed digest;
- an ambiguous broker result;
- a postflight refusal (preserve and inspect; no retry or rollback without review);
- new privilege;
- an interactive signing prompt.

No sequence number, envelope or window root is ever reused.
