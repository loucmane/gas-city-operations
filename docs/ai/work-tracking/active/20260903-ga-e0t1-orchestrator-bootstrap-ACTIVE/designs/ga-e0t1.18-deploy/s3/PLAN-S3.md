# ga-e0t1.18 S3, part 1: the M7 metadata successor

S2 (broker sequence 15) is accepted. Core `gc` `fce2e9a0` (build source `deefb98b`, Core PR 48, the
ga-qcwl provider-pin fix) runs at a fresh epoch as supervisor PID 995924. Receipt `1cca491d`; the live
readback review passed at `295b0d9b`. S3 part 1 publishes platform metadata for that host. Part 2 (P8, a
separate package) then refreshes the worker provisioning receipt.

## Why M7 is small

A read-only probe on 2026-09-26 found exactly two differences between the installed M6 manifest `7f335ad8`
and the live host (scratchpad `m7_drift_probe.py`):
- `gc` is `fce2e9a0` instead of `b2760ea4`;
- the Core rig object tree is `98e871c4` instead of `ae95c30c`. S1 fetched PR 48's objects into the rig,
  and the sequence 15 closure accepted that digest exactly.

Everything else M6 pins is unchanged: the Template (still `cfd353f3`, with the reviewed untracked set), the
providers, libexpat and every library, the cache, the links, the protected trees and the authorities. So M7
needs no fetch, checkout, authority or `inventory` prerequisite: the capture is the only step before binding.

## The complete delta (M6 `7f335ad8` → M7)

| Field | M6 | M7 | Source |
| --- | --- | --- | --- |
| `core.source` / `core.sha256` | ga-e0t1.15 `gc-a` / `b2760ea4` | `/var/tmp/ga-e0t1.18-build-20260926/gc-a` / `fce2e9a0` | S1 build, receipt seq 15 |
| `previous_sha256` / `backup_path` | `69d00186` / mutg custody `gc-b` | `b2760ea4` / `/var/tmp/ga-e0t1.15-build-20260925/gc-b` | Core `validateSuccessor` (installer.go 381-416 at `deefb98b`): previous_sha256 must equal the predecessor core |
| `activation.expected_commit` / `previous_commit` | `9faeabc2` / `796d9a7a` | `deefb98b` / `9faeabc2` | the build's `gc version` commit; previous must equal the predecessor's expected |
| writer, installed `gc` input | `b2760ea4` | `fce2e9a0` | R9 pattern |
| inputs, appended | — | build source `gc-a` (`fce2e9a0`, 0755) and backup `gc-b` (`b2760ea4`, 0755) | R9 pattern |
| tree `rigs/gascity/.git/objects` | `ae95c30c` | `98e871c4` | sequence 15 accepted closure (exact) |
| release, transaction, attempt, parents, evidence, host, namespaces, previous metadata | M6 | fresh, `reports/m7` | M6 pattern |

Counts: 689 inputs, 49 trees, 23 links. Frame 128,795 of 131,072 bytes (2,277 spare; the test requires
more than 2,048). `city-config` keeps `previous_sha256` = `sha256` = `4f7e170f` with its M6 backup
`reports/m6-inputs/city.toml.before`, which must stay byte-exact at 0644 while M6 or M7 is installed.

## Two corrections the M6 sources needed

- **Watchdog image.** `metadata_closure.configure` admitted a surviving dolt watchdog only when it maps
  `candidate.OLD`. The watchdog (PID 2852) has survived sequences 14 and 15 and still maps `69d00186`, while
  M7's `OLD` is `b2760ea4`. M7 adds `WATCHDOG_IMAGE = 69d00186` and `configure` uses it; that is the only
  code change in `metadata_closure.py` (plus two comment lines).
- **Cache bookkeeping.** The dry probe found one cache inventory difference from the sequence 15 record:
  the mtime and ctime of one cache repository's `.git` entry moved to 04:58:00Z, the second of the
  coordinator's `workflow.py coordinate` note on ga-e0t1 (a `gc bd` call). Content, entries and the tree
  digest are unchanged. `capture_m7.cache_drift` admits exactly that class (only mtime/ctime, only on a
  `<key>/.git` entry or below) and refuses everything else. The capture then binds the live inventory
  exactly, so from the capture on the usual quiescence applies.

## Package (`designs/ga-e0t1.18-deploy/s3`)

| File | Role |
| --- | --- |
| `manifest_candidate.py` | Pure builder, from the M6 builder. The R9 helper `8a9145f5` supplies `b`, `r7` and `require`. The seq 15 receipt is `3183ed20…`, sha `1cca491d`, 1234 bytes, uid 0, gid 986, mode 0640. |
| `capture_m7.py` | The single-stage capture of `reports/m7-capture/baseline.json`. It reuses the reviewed M6 helpers (`prereqs_m6.py` `a36824b8` for the quiet slot, read-only git and exclusive writes; `capture_m6.py` `702d42a5` for `config_drift`), both loaded by digest. |
| `metadata_closure.py` | M6 bytes, except `configure` passes `WATCHDOG_IMAGE`. |
| `source_runtime.py`, `launch.py`, `metadata_executor.py`, `metadata_window.py` | Byte-identical to M6. |
| `record_review.py` | The M6 recorder with its two paths moved to `reports/m7/q` and `reports/m7-reviews`. |
| `operator/gate_extract.py`, `operator/GATE-PROMPTS.md` | The M6 gate extract and prompts, rebound to M7. |
| `test_s3.py` | 28 tests (26 run before the capture; the frozen-baseline build and the source inventory run at the binding step). |

## Live run order

Every command runs as `systemd-run --user --wait --collect --pipe --quiet -p UMask=0022
/usr/bin/python3 -I -B <file> …`, which places it in the supervisor namespaces. Before each command the
package worktree must be clean at the reviewed commit. `C` is the SHA-256 of `manifest_candidate.py` as
committed.

1. **Capture.** `capture_m7.py C` writes `reports/m7-capture/baseline.json`.
2. **Binding step.** Pin `BASELINE_SHA`, write `source-pins.json` (the six executor sources), commit, and get
   two independent binding reviews.
3. **Executor.** M5's unchanged stage grammar: `launch.py --expect-sources <pins> prepare`, then two
   SOURCE_PASS reviews, then `pause`, then `observe`, then two PAIRING_PASS reviews, then `paired`, then
   `verify`, then two COMMIT_PASS reviews, then `restore-accepted`. `prepare` pauses the Obsidian timer and
   `restore-*` restores it. Start `observe` only with more than 180 s of window left and `paired` only with
   more than 300 s; the executor's own deadlines are authoritative.
4. **P8.** The receipt refresh, as a separate reviewed package.

**Quiescence.** From the capture until `restore-accepted`: no gc, no `workflow.py`, no Bead note (notes wait
in staging), and no git in the canonical Template, its linked worktrees, the Core rig, the codex authorities
or the packs repository.

## Binding step (r2, 2026-09-26): live results

r1 `7d86f441` received two independent SOURCE_PASS verdicts with no must_fix. The capture then ran once,
in the supervisor namespaces, with candidate `C` = `5bdd4129` at `7d86f441`, clean:
- `reports/m7-capture/baseline.json` `28d65524`, zero drifts: 760 pins, 49 trees, 23 links, scope
  (core 995924 plus the dolt pair, watchdog deleted-old), suspension `5c98be4a`, cache `4b284f67`.
- One admitted cache bookkeeping entry: `954ed149…/.git` (mtime and ctime only), now at 05:09:13Z, the
  second of the coordinator's `workflow.py log` call. That is the same `gc bd` cause the dry probe found
  at 04:58:00Z; the capture binds the live value exactly.
- The executor's predecessor file `reports/m6/q/manifest.json` was checked by hand before the capture:
  `7f335ad8` (review B should_fix 1).

The r2 changes:
- `manifest_candidate.py` pins `BASELINE_SHA`, which changes its digest from `5bdd4129` to `b3644e84`.
- `source-pins.json` is new (`cc067c45`) and lists the six executor sources.
- `test_native_successor_rules` reads `installer.go` from the S1 reproduction clone instead of the Core rig,
  so no test runs git in a pinned repository inside the quiescent window (review A should_fix 2). All 28
  tests pass, including the build against the frozen baseline (frame margin over 2048) and the source
  inventory.

The next step is the executor, `launch.py --expect-sources cc067c45… prepare`, after the two binding reviews.

## Review dispositions for r1 (`7d86f441`: two SOURCE_PASS verdicts)

| Finding | Disposition |
| --- | --- |
| A 1: the prompt said the Core rig is checked out at `deefb98b` | Prompt error only; the package reads the rig's objects, never its checkout. The rig HEAD is unchanged, consistent with only its object tree moving. |
| A 2: a test runs git in the Core rig, which quiescence forbids after the capture | Fixed in r2 (the S1 reproduction clone). |
| A 3, B 5: refusal branches without a negative test (managed files, providers, last authority, previous backup binding, parents, receipt; nested cache `.git` keys, gate extract) | Follow-up coverage. Every branch fails closed, and the positive paths are pinned. |
| A 4: "two paths" versus the five differing recorder lines | The recorder moves two paths; the other three differing lines are its docstring. |
| A 5: frame and closure counts not independently computed | The tests assert the frame margin; the capture refuses on a count mismatch and passed. |
| B 1: the capture does not check the executor's predecessor file | Checked by hand before the capture (`7f335ad8`); `prepare` refuses on drift, at worst consuming the package root without any live change. |
| B 2: the capture docstring claims the seq 15 links are compared | The executor's snapshot requires links equal to the baseline, which the capture took from the live host; the docstring overstates the capture itself. Wording follow-up. |
| B 3: no reconciler recheck at the end of the capture | Inherited from M6. Any reconciler effect fails closed at the executor's exact snapshot. |
| B 4: `cache_drift` is not tied to one event | Accepted as bounded: content, size, inode, device, owner and nlink stay exact. The one admitted entry is listed above for the binding reviewers. |
| B 6: the `install_policy` docstring still says "the replaced image" | Wording; changing it would re-pin `metadata_closure.py`. |
| B 7: the capture does not check the receipt epoch | The executor checks it before creating the package root. |

## Stop conditions

Any refusal, host epoch drift, drift outside the bounds, an ambiguous result, new privilege or a pinentry
prompt. The executor's recoveries are unchanged from M5: `recover-preparation`, `recover-pause` and
`restore-preapply`. A refused capture keeps its record; a retry needs a new reviewed package root.
