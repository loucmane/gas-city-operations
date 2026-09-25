# ga-e0t1.15 S3, part 1: the M6 metadata successor

S2 (broker sequence 14) is accepted: Core `gc` `b2760ea4` (build source `9faeabc2`) runs at a fresh
epoch, supervisor PID 2940569. The acceptance came from the reviewed read-only recovery at `5019e607`,
with SOURCE_PASS and LIVE_PASS; the root is `/var/tmp/ga-e0t1.15-seq14-recovery-20260925`.
S3 part 1 publishes platform metadata that describes that host and the Template move. Part 2 (P7,
a separate package) then refreshes the worker provisioning receipt.

## Corrections to PLAN.md and operator decisions

- **Scope.** The live canonical Template checkout is at `28539934` (PR 69), not `e6195b10` as
  PLAN.md's S3 section states. Moving it to `cfd353f3` therefore ships PR 70 (gct-lagl, the
  operations candidate lane) as well as PR 71. The operator chose that scope on 2026-09-25 at about
  20:00 CEST ("a").
- **No registry or render step.** PR 70 changes the renderer `bin/gct-managed-rig-permissions`.
  Rendered in memory against the live registry, the `cfd353f3` renderer reproduces the live
  fragment `cba75f87` byte for byte once its own root path is the canonical checkout. The only
  difference was the root path embedded in `--settings`.
- **Order: metadata before the receipt.** The receipt provisioner
  (`gct-managed-worker-provision` `64425a72`, lines 1030-1050) refuses a consumer witness whose
  Core digest differs from the platform manifest's `core.sha256`. Live `gc` is `b2760ea4`, while M5
  still names `69d00186`. So P7 needs M6 first. Signing launches check the receipt, not the
  platform manifest: the ga-nibd worker signed at 15:01 CEST today with libexpat already drifted.
  So worker launches stay blocked only by the receipt version, which fails closed.
- **Access-time neutral**, carrying forward the operator's S2 decision of 2026-09-25 ("Relax it").
  `metadata_closure.install_policy` wraps the legacy observer so that metadata and tree inventories
  omit `atime_ns`. Everything else stays exact: path set, type, mode, uid, gid, size, inode,
  device, nlink, mtime, ctime and content digests. `metadata_window.build` binds no cache atime;
  its renewal is start plus one day and `max_atime` is 1. The 900 s window and 66 s admission are
  unchanged. So there is no settle step, no freeze step and no 24 h horizon.
- **libexpat re-pin.** `ec6c12d3` → `286682ec` (libexpat1 2.6.1-2ubuntu0.5 → 0.6). It was installed
  by unattended-upgrade at 2026-09-25 06:25:40. `dpkg --verify` is clean, and the MD5 `22f36128`
  equals the package record. This is the same class as the M5 re-pin the operator accepted on
  2026-09-23.
- **One narrowing: the PR 69 authority is replaced, not kept.** M5's frame had 3001 spare bytes, and
  a second 34-pin authority needs about 5.5 KB. The trial build with both would overflow the
  131,072-byte native frame. M6 therefore drops the PR 69 authority, its repository entry and its 12
  input, 20 tree and 2 link pins, and adds the PR 71 ones. The frame is then 128,272 bytes, with 2800
  spare. The PR 69 worktree stays on disk, clean and unreferenced. It is superseded: after P7, the
  receipt names `cfd353f3`.

## The complete delta (M5 `2d7eadce` → M6)

| Field | M5 | M6 | Source |
| --- | --- | --- | --- |
| `core.source` / `core.sha256` | custody `gc-a` / `69d00186` | `/var/tmp/ga-e0t1.15-build-20260925/gc-a` / `b2760ea4` | S1 build, broker receipt seq 14 |
| `activation.expected_commit` | `796d9a7a` | `9faeabc2` | supervisor `/health` `build_id` (`version` stays `dev`) |
| `previous_sha256`, `backup_path`, `previous_commit` | `69d00186`, custody `gc-b`, `796d9a7a` | unchanged | these already name the replaced image, as in R9 |
| writer, installed `gc` input | `69d00186` | `b2760ea4` | R9 pattern |
| inputs, appended | — | the build source `gc-a` (`b2760ea4`, 0755) | R9 pattern |
| `lib/gct_claude_signing_worker.py` | `4e28d5b8` | `a216552b` | Git blob at `cfd353f3` (PR 71) |
| libexpat | `ec6c12d3` | `286682ec` | distribution security update |
| provider `claude` version | `dependencies_sha256=f36deb20` | `d4e57767` | `derive_m6.py`, the M5 method, which first reproduces `f36deb20` |
| tree `rigs/gascity/.git/objects` | `361e500a` | `ae95c30c` | S2-accepted closure (exact) |
| tree `cache/repos`, `cache_sha256` | `e5e959dd` | `4b284f67` | S2-accepted closure (exact; new synthetic core-pack directory) |
| tree Template `.git` | `33bd60d3` | bounded capture digest | fetch, checkout, `worktree add` |
| authority | `template-pr69-authority` `28539934` | `template-pr71-authority` `cfd353f3` at `/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority` | `derive_m6.py` coverage: 12 inputs, 20 trees, 2 links over 294 tracked paths |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M5 | fresh, `reports/m6` | M5 pattern |

Everything else is carried unchanged and asserted, including:
- runtime, protected trees, `absent`, `imports_sha256`, `gc_home`, managed files and integrity files;
- the four retained canonical Template pins;
- the native provider `1e08503d` (2.1.280);
- every other tree and link.

Counts: 686 inputs, 49 trees, 23 links.

## Package (`designs/ga-e0t1.15-deploy/s3`)

| File | Role |
| --- | --- |
| `manifest_candidate.py` | Pure builder. It loads the reviewed R9 helper `8a9145f5` for `b`, `r7` and `require`, like M5. The seq 14 receipt is `f04c1240…`, sha `f55fed69`, 1229 bytes, uid 0, gid 986, mode 0640. |
| `derive_m6.py` | Derivation of the constants from Git objects. It first runs the method checks against M5. |
| `prereqs_m6.py` | Live steps `inventory`, `fetch`, `checkout`, `authority`, plus `resume` and `rollback`. |
| `capture_m6.py` | The single-stage capture of `reports/m6-capture/baseline.json`. |
| `metadata_window.py` | M5 bytes, except `build()`, which is access-time neutral. |
| `metadata_closure.py` | M5 bytes, plus `install_policy`: the S2 access-time and dolt-scope policies, and the suspension record from the candidate (`c30776de`, which S2 left). |
| `source_runtime.py`, `launch.py`, `metadata_executor.py` | Byte-identical to M5 (`2585357a`, `43ad2ac9`, `5a6694ab`). |
| `record_review.py` | The M5 recorder, with its two paths moved to `reports/m6/q` and `reports/m6-reviews`. |
| `test_s3.py` | 23 tests. The derivation test needs a repository that holds `cfd353f3`. |

External reviewed dependencies:
- the legacy chain in the tracker `reports/…/recovery-source-r2`;
- the R9 helper;
- `/tmp/ga-mutg-adoption-20260920{,-r3,-r4,-r6,-r7}`. On 2026-09-25 the cleaned `-r6` and `-r7`
  files were restored byte for byte from `~/.local/share/gas-city-staging/ga-mutg-20260920`:
  `capture_transition.py` `e25dae98`, `deadlines.py` `1486dbbc`, `observe.py` `1b28f56a`;
- the S2-accepted observation `observation-2.json` `74a04a26`.

## Live run order

Every command runs as `systemd-run --user --wait --collect --pipe --quiet -p UMask=0022
/usr/bin/python3 -I -B <file> …`, which places it in the supervisor namespaces. Before each command,
the package worktree must be clean at the reviewed commit.
`C` is the SHA-256 of `manifest_candidate.py` as committed.

0. **Read-only probe.** Done 2026-09-25 against the uncommitted package: the host is the S2 epoch,
   the dolt-aware scope passes, suspension is `c30776de`, the Template `.git` is `cac98745`, and the
   checkout is at `28539934`, detached, with the reviewed untracked set.
1. **Prerequisites.** Run `prereqs_m6.py C inventory`, then `fetch`, then `checkout`, then
   `authority`.
   - From `checkout` onward, the signing worker reports version `d4e57767` while the receipt still
     names `f36deb20`. Every signing launch then refuses, which fails closed.
   - No worker launches until P7 is adopted. The city and rigs stay suspended throughout.
2. **Capture.** `capture_m6.py C` writes `reports/m6-capture/baseline.json`.
3. **Binding step.**
   - pin `BASELINE_SHA`;
   - write `source-pins.json` (the six executor sources);
   - commit;
   - get two independent binding reviews.
   The prerequisite records bind `C`, and the rebuilt candidate after the pin is reviewed as the
   binding. This follows M5 r6 through r11.
4. **Executor.** This is M5's unchanged stage grammar:
   `launch.py --expect-sources <pins> prepare`, then two SOURCE_PASS reviews, then `pause`, then
   `observe`, then two PAIRING_PASS reviews, then `paired`, then `verify`, then two COMMIT_PASS
   reviews, then `restore-accepted`.
   - `prepare` pauses the Obsidian timer and `restore-*` restores it.
   - The executor's own deadlines are authoritative. Start `observe` only with more than 180 s of
     window left, and `paired` only with more than 300 s.
   - A late gate stops at `restore-preapply`, which is valid.
5. **P7.** The receipt refresh, as a separate reviewed package.

**Quiescence.** From the capture until `restore-accepted`, nobody runs gc or `workflow.py`, and
nobody writes a Bead note. Notes wait in staging, under the quiescent-window rule.

## Rollback and stop conditions

- `prereqs_m6.py C rollback` returns the canonical checkout to `28539934`. It runs only while the
  installed manifest is M5 and no M6 executor window may be open. The fetched objects and refs and
  the authority worktree stay.
- The executor's recoveries are unchanged from M5: `recover-preparation`, `recover-pause` and
  `restore-preapply`.
- Stop on any of these, and never retry into a consumed root:
  - any refusal;
  - host epoch drift;
  - drift outside the bounds;
  - an ambiguous result;
  - new privilege;
  - a pinentry prompt.
