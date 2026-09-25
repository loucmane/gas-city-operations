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
  input, 20 tree and 2 link pins, and adds the PR 71 ones. At r3 the frame is 128,505 bytes, with 2567
  spare (the test requires more than 2048). The PR 69 worktree stays on disk, clean and unreferenced. It is superseded: after P7, the
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
| managed file `city-config` | `previous_sha256` `6594ee77`, backup `reports/r5/i/00` | `previous_sha256` `4f7e170f`, backup `reports/m6-inputs/city.toml.before` (new pinned input, written by `inventory` from the live file) | Core `validateSuccessor` (`installer.go` 405-413) and metadata-only backup reuse (`metadata_adopt.go` 73-77) |
| authority | `template-pr69-authority` `28539934` | `template-pr71-authority` `cfd353f3` at `/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority` | `derive_m6.py` coverage: 12 inputs, 20 trees, 2 links over 294 tracked paths |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M5 | fresh, `reports/m6` | M5 pattern |

Everything else is carried unchanged and asserted, including:
- runtime, protected trees, `absent`, `imports_sha256`, `gc_home`, the five other managed files (each
  already has `previous_sha256` equal to `sha256`) and integrity files;
- every input, tree and link the successor names, compared at build time with the frozen baseline;
- the four retained canonical Template pins;
- the native provider `1e08503d` (2.1.280);
- every other tree and link.

Counts: 687 inputs, 49 trees, 23 links.

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
| `test_s3.py` | 30 tests. The derivation test needs a repository that holds `cfd353f3`. |
| `operator/gate_extract.py`, `operator/GATE-PROMPTS.md` | The M5 in-window gate extract and prompts, rebound to `reports/m6/q` and the M6 facts. |

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
- **No retry into the same package.** After a rollback, or once fetch, checkout or authority has
  changed the Template `.git` away from `cac98745`, the `inventory` step can no longer pass. Any retry
  needs a new, reviewed package that binds the new predecessor.
- **Keep the city-config backup.** `reports/m6-inputs/city.toml.before` is in the gitignored
  `reports/`. Core's `InspectIntegrity` checks managed backups, so the file must stay byte-exact at mode
  0644 for as long as M6 is installed, as `reports/r5/i/00` did for M5.
- A torn intent record from `inventory` needs manual cleanup. Torn `inventory` data records are
  replaced by `resume inventory`.
- Stop on any of these, and never retry into a consumed root:
  - any refusal;
  - host epoch drift;
  - drift outside the bounds;
  - an ambiguous result;
  - new privilege;
  - a pinentry prompt.

## Binding step (r4, 2026-09-25): live results

r3 `dc34612e` received two independent SOURCE_PASS verdicts with no must_fix. The remaining
should_fixes are follow-ups, per the operator's rule that only code, safety or live-state defects hold:
- a pre-mutation size check;
- earlier-record parsing in `common`;
- a pre-mutation config check;
- the inventory record digest check in the capture;
- documentation of the fetch race, a consumed commit and the resume temporary file.

Live run, all in the supervisor namespaces, with candidate `C` = `12b536be` at `dc34612e`, clean:
- `inventory`, `fetch`, `checkout` and `authority` all passed, unresumed, with records under
  `reports/m6-inputs`.
- Between `fetch` and `checkout`, the derivation and successor-size tests passed against the fetched
  canonical objects. That covers the r3 review A size should_fix before the mutation.
- `checkout` proved every blob first. The worker then reported `d4e57767`.
- The capture passed with zero drifts. Exactly one S2 pin changed: the parser, at its exact successor.
  The baseline is `reports/m6-capture/baseline.json`, `b2360cf7`.

The r4 changes:
- `manifest_candidate.py` pins `BASELINE_SHA`, which changes its digest from `12b536be` to `bdc189e0`.
  The prerequisite records bind `12b536be`; they are only read by the capture, which has run.
- `source-pins.json` is new (`3b98da18`) and lists the six executor sources.
- `test_build_against_frozen_baseline` builds M6 from the real baseline: 687/49/23, frame margin over
  2048, the authority last, and the Template `.git` at a new bounded digest. There are 32 tests.

The next step is the executor, `launch.py --expect-sources 3b98da18… prepare`, after the binding
reviews. There must be no gc call, `workflow.py` call or Bead write until `restore-accepted`.

## Review dispositions for r1 (`dc5c46b5`: two HOLD verdicts)

| Finding | Disposition |
| --- | --- |
| A must_fix: `city-config` kept `previous_sha256` `6594ee77`, so Core's successor rule would refuse inside the consumed window | Fixed. `previous_sha256` is now `4f7e170f`, with the pinned backup `reports/m6-inputs/city.toml.before` written by `inventory` from the live bytes. `test_native_successor_rules` restates `validateSuccessor` over the build. |
| B must_fix: the carried-forward check required libexpat to change, but S2 already had it at `286682ec`, so every live capture would refuse after the Template move | Fixed. `carried_changes()` is a tested pure function: a reviewed input at its predecessor in S2 must move to its successor; one already at its successor must stay there; anything else refuses. It is tested against the real S2 closure. |
| A should_fix: frame margin, pointer method check, 294 tracked paths, carried pins bound to the baseline, more refusal tests, receipt digest | All taken. The frame margin must exceed 2048. `derive_m6` reproduces M5's pointer `deabdafa` and asserts the 12/20/2/294 target shape. The builder compares every named input, tree and link with the baseline. There are four more refusal cases. The installed receipt digest is tested. |
| B should_fix 1 and 2: `inventory` not resumable, and `mkdir` before the gates | Fixed. The records are written or verified in the postcondition, so `resume inventory` recovers any interruption, and the package gates run before `mkdir`. |
| B should_fix 3: an interrupted checkout | `rollback` now does a forced detach to `28539934`, which restores tracked files. Untracked leftovers are listed for manual recovery, never deleted. |
| B should_fix 4: `GIT_TERMINAL_PROMPT` | Set to `0`. |
| B should_fix 5 and 6: counts, and root modes | Taken. 741 S2 pins and 29 S2 trees are asserted, and every tree root mode is checked in the capture. |
| B should_fix 7: renderer blob | Pinned as `bb97950c` and required before the checkout. |
| B should_fix 8: rollback blocked by a crashed `prepare` | Documented as the inherited M5 residual limit (`prereqs_m6.py` docstring). |
| B should_fix 9: tests | Added: `carried_changes` against the real S2 closure, and the policy on the real legacy observer. `resume` and `rollback` live paths remain covered by their postcondition code, and the capture `main` by the live run. |

## Review dispositions for r2 (`f8fcb751`: two HOLD verdicts, same must_fix)

| Finding | Disposition |
| --- | --- |
| A and B must_fix: pins include `size`, and PR 71 grows the parser from 14178 to 14668 bytes, so `carried_changes` still refused | Fixed. `SUCCESSOR_SIZES` binds the exact cfd353f3 blob size. `carried_changes` requires the whole successor pin (digest, size, unchanged mode, uid and gid). The test uses the real successor size and refuses the old size or a mode change. `test_successor_size_matches_the_target_blob` checks the size against the blob. |
| A should_fix: frame figure, full distinct-path restatement, resume branch test, backup retention | Frame recorded (128505). The path test now includes `receipt_path`, the default manifest path and both previous-metadata backups. Backup retention is stated above. The resume branch is below. |
| B should_fix 1: `-f` wording | Corrected: it deletes no untracked file but overwrites one at a path 28539934 tracks. |
| B should_fix 2: torn inventory records | `resume inventory` replaces its own torn data records atomically, only while the intent exists and the record does not. A torn intent needs manual cleanup (stated above). |
| B should_fix 3: renderer bytes on disk | `post_checkout` now checks the on-disk renderer against `RENDERER_SHA`. |
| B should_fix 4: retry after rollback | Stated above: a retry needs a new reviewed package. |
| B should_fix 5: digest pins | `test_source_pins` asserts them; the r3 test run is recorded in the commit. |
