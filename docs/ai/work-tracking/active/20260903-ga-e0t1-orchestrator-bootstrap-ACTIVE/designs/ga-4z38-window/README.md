# ga-4z38 worker window (goal step 3)

ga-4z38 is the third successor for the ga-5ot6 routing work. Its predecessors' attempts are consumed and
never refunded:
- ga-5ot6 died at the trust dialog;
- ga-e0t1.14 exposed the native-write policy gap, later fixed;
- ga-y49e was rejected by the positional prompt, since fixed and live via M5.

This package delivers one reviewed window. It routes `gascity/gc.implementation-worker` (Claude
signing worker, Opus 5.5) through `gc sling` onto ga-4z38. The rest follows ga-y49e's reviewed
contract:
- one claim;
- startup capability proofs, including the negative permission cases;
- RED/GREEN implementation of the route-cycle separation;
- the implementation summary artifact;
- one managed signature after independent candidate review;
- delivery, closeout, exact restoration, and zero residue.

Every live step runs as a job of the persistent host job runner (`designs/gct-jobrunner`).

## Round 1: prep

`prep-r11.py` is a merged rebind of the reviewed ga-y49e `prepare-isolation.py` and
`prepare-receipt.py`. Their logic is kept, and the overlay generator is factored out as
`build_overlay()`. It is read-only and writes only its fresh root (`-r1` for this round's job; now
`-r2`, see below).

It produces the single-worker isolation overlay of the live M5 city (`4f7e170f`):
- workspace cap 1;
- all 34 orders skipped;
- 40 city and gascity agents patched: 39 suspended, and `gascity/implementation-worker` bound to
  the ga-4z38 worktree with sessions 0..1.

It proves the exact effective-config delta and zero effective orders. It takes the overlay's
permission revision from the reviewed Core compose diagnostic (`9f837c83`). It normalizes (Template
provisioner `64425a72`) and finalizes (Core preflight diagnostic `edbc0fa1`) P6's reviewed input draft
(`24c1ca75`) with that revision. The final receipt must differ from the live receipt `0b30c23f` only
in `permission_revision` and `receipt_sha256`.

**Rebind map from the reviewed originals:**
- city `6594ee77` becomes `4f7e170f`;
- revision `ebeefe97` becomes `d6ca85cd`;
- receipt `01ed1bce` becomes `0b30c23f`;
- the prior input (the R9 draft) becomes P6's draft;
- the task and worktree ga-y49e become ga-4z38;
- the old observation root becomes a live observation made in the same run;
- the two output roots become one fresh root.

The overlay was derived twice by the coordinator, from a text transform of the reviewed ga-y49e
overlay and from this generator over live config. Both gave `5f3b60e1`, and a test pins that. The
M5 city equals the old R9 baseline except for its Opus 5 to 5.5 model lines.

**Job.** Job `ga-4z38-prep` runs `operator/PREP.sh` at this commit. It writes its log to
`~/.local/share/gas-city-staging/ga-4z38-window/prep-*.txt` and exits with the prep result.

### Round 1 r2 (after the r1 job refused)

Job `ga-4z38-prep` at `7ae90892` (two SOURCE_PASS reviews) ran at 16:06Z and refused fail-closed at
the effective-config assertion. The only difference was one additional advisory entry in
`gc config show` `validation.warnings`: the bound worker's `max_active_sessions=1` makes it a
canonical singleton. The observed list equals the sorted baseline plus exactly that string, and every
Agents, Workspace and Orders field matched. The compose checks had already passed: before
`d6ca85cd`, overlay revision different. Root `-r1` is consumed and preserved.

r2 does the following:
- it expects exactly that pinned warning, `SINGLETON_WARNING`;
- it pins the overlay `5f3b60e1` in-job, not just in the test, as both r1 reviewers suggested;
- it re-launches the normalize child through the digest-checked source launcher;
- it declares the fixed ENV and the in-run revision gate in the docstring;
- it uses root `-r2`.

A test binds the pinned warning to the r1 evidence.

### Round 1 r3 (after the r2 review HOLD)

r2 `f0234f73` got one SOURCE_PASS and one HOLD, so it never ran and root `-r2` was never created.
The HOLD named two checks that no test or job had yet reached:
- the receipt difference check, which depends on `worker_profile_sha256` excluding the revision;
- the empty-orders check, since gc might print `null` for an empty list.

`proof/prep-proof.py` now runs both read-only outside any job (it reads the live city, and its gc
calls are network-isolated), with the committed code and a scratch
root:
- The confined `gc order list --json` against the pinned overlay bytes returns `"orders": []` with
  count 0. `gc config show` equals both the r1 observation and `expected_config()`.
- `receipt_image()` runs the exact job child path: normalize through the source launcher
  (`-I -S -B`), then Core `compose finalize`. Each runs in bwrap with `--unshare-pid --new-session`
  under the Core owned-phase runner, and cleanup is clean.
  - With the live revision `d6ca85cd`, the result is byte-identical to the live receipt `0b30c23f`.
  - With the r1 overlay revision `6b31d83a`, only `permission_revision` and `receipt_sha256`
    differ (final `392ea0b6`).

r3 also makes these changes:
- the launcher self-check comes first in `main()`, before the root exists;
- `expected_config()` is factored out and replayed against the r1 evidence by a test;
- a test pins the r1 overlay bytes;
- the normalize child takes its input directory as an argument;
- `test_prep.py` runs the proof.

Root `-r2` is still fresh and is used as is.

**Outcome.** Job `ga-4z38-prep-r3` at `e508fe84` (two SOURCE_PASS reviews) ran 16:37:01Z to
16:37:03Z and exited 0 with PREP PASS. Root `-r2` holds `result.json` `c0d1959c`:
- overlay `5f3b60e1`;
- revision `d6ca85cd` to `6b31d83a`;
- receipt image `392ea0b6`, from `0b30c23f`, with only `permission_revision` and `receipt_sha256`
  changed;
- receipt input `b54d45ac`;
- zero effective orders.

Nothing was installed and no worker launched.

## Round 2a: base rebind and the fresh accepted-state observation

All three sources are generated by the committed `generators/`, and every replacement is asserted.
`test_round2a.py` regenerates them and requires byte equality.
- `window-base-r11.py` (from the reviewed ga-y49e `window-state-r6-read-safe.py`, `b10a3810`):
  - the M5 baseline `4f7e170f`, `0b30c23f`, `d6ca85cd`, with the prep outputs as the window image;
  - task ga-4z38;
  - the P6 support modules and launcher;
  - Opus 5.5;
  - the P6 accepted snapshot `1c025ef9` with its provider pins `a5f7f8c1`, and the typed-support
    witness `5a630443`.

  The R9-era diagnostic pins are dropped. `approved_historical_image` holds exactly one disposition:
  the pack-cache repo `.git` directory mtime and ctime moved from `1790165454882697018` to
  `1790178703592685769`. The cause was coordinator `gc bd` calls without `GIT_OPTIONAL_LOCKS=0`,
  the last at 15:51:43Z; every call since sets the variable.
- `window-obs-r11.py`: the reviewed `window-state-r9.py` layer (base plus the cache-atime envelope)
  over the new base.
- `observe-integrity-r11.py`: the reviewed `observe-platform-integrity-r2.py` for a fresh window.
  - It admits live state through the base `before.json` check: P6 plus the disposition, plus the
    provider pins.
  - It runs the pinned native platform inspector (`77685c66`, Core `796d9a7a`) in read-only mounts.
  - It proves before/after preservation with zero cache atime deltas.
  - The ga-y49e lifecycle and restoration comparisons are removed, since no prior window exists.
    The result claims `admitted_against_p6_with_disposition` instead of the ga-y49e comparator note.
- `cache-atime-policy-r1.py` and `suspension-lineage.py`: byte-identical copies.

`proof/admission-forecast.py` runs the generated base's `pins()` and the `before.json` admission
comparison read-only, over the live cache, pins and protected trees. It finds zero differences and
equal provider pins. The host block needs the supervisor namespaces, so only the job checks it.

**Review outcome.** Round 2a at `d12ac92b` got one HOLD and one SOURCE_PASS. The HOLD: the generator
checked its two ga-y49e sources only against themselves. The PASS added should-fixes:
- set the observer root before the inner mount proof;
- add `directories()` to the forecast;
- log all six namespaces;
- make the OBSERVE header precise.

All of these are folded into round 2b, which is reviewed and run as one commit. The observer job runs
at that commit, immediately before preflight. Its output root is
`/var/tmp/ga-4z38-integrity-20260923-r1`, which `window-r11.py` binds by provenance.

## Round 2b: the window stack, the brief and the wrappers

Round 2b is committed together with the round-2a fixes:
- `make_round2a.py` pins its two sources to their reviewed ga-y49e digests:
  - `window-state-r9.py` `0252bc40` (atime-final-review-and-bindings-r2.md);
  - `observe-platform-integrity-r2.py` `050cb878` (native-integrity-r2-review.md).
- The base pins the prep `result.json` `c0d1959c`.
- Both observers set their own root before the inner mount proof.
- The forecast also runs `directories()`.

These fixes move every round-2a digest. `test_round2a.py` and `test_round2b.py` regenerate every
output and wrapper and require byte equality.

**Generated by `generators/make_round2b.py`.** Every source is pinned to its reviewed digest, and every
replacement is asserted.
- `window-r11.py`: from `window-state-r10.py` (`e51b5fa8`), over `window-base-r11.py`. It keeps the
  R10 route-regeneration chain, the cache-atime accounting and the reload observation unchanged.
  One change: the fresh integrity observation is bound by **provenance**, not by reviewed output
  digests. The observer runs as the job immediately before preflight, with no review round between
  them. `integrity_baseline()` requires:
  - the observer root to be 0700, owned by uid 1000;
  - its `intent.json` to name the reviewed observer digest and the inspector digest;
  - no `primary-failure.json`;
  - the exact result and preservation records.

  It records the result and `observed-after.json` digests once, in `integrity-binding.json` at
  `before.json`, and every later snapshot requires the same bytes.
- `reconcile-predecessor-r3.py`: from `reconcile-predecessor.py` (`4a66d443`), the reviewed
  status-only hold that moved ga-e0t1.14 to `blocked`. It is rebound to ga-y49e, which is still open
  and routed to the worker template, so the sole-task audit would refuse. The consumed attempt,
  route, metadata and evidence are preserved.
- `bind-task-r3.py`: from `bind-task-r2.py` (`17ce31a4`). It binds ga-4z38 before the window: the
  window root must not exist yet.
- `route-task-r5.py`: from `route-task-r4.py` (`2f6ec34b`), over `window-r11.py`. It binds the
  binding outputs by provenance: the executor and brief digests in `binding-intent.json`, the exact
  result, and matching metadata.
- `audit-queue-r3.py`: from `audit-routed-queue-r2.py` (`280d86ca`). Mode `route` requires every rig
  suspended. Mode `resume` runs after rig-resume and before city-resume, and requires only the
  gascity rig resumed.
- `observe-terminal-r11.py`: from `observe-platform-integrity-r2.py` (`050cb878`). It verifies the
  terminal suspension lineage in the window root and admits the window's accepted restoration
  (`restored.json`, bound by the window executor digest and `restore-pass.json`). The cache clock
  stays bounded from the window `before.json`.
- `restore-r9-routes-r3.py` (`8d041af7`) and `route-chain-r1.py` (`e408e2dd`): byte copies.

**Written for this window.**
- `worker-brief.md`: the reviewed ga-y49e brief, rebound to ga-4z38 and Opus 5.5.
  - Releases arrive as gc mail beads, which the worker reads with the policy-allowed `bd show`. The
    control policy `16022d04` allows no `gc mail`.
  - The runtime's generated artifacts are inventoried instead of predicted, and the source release
    names the exact `.gitignore` entries.
  - The four-hour budget is stated.
- `watch-r11.py`: a read-only in-window observation in the supervisor namespaces, repeatable with a
  fresh root per run.
- `generators/make_operators.py`: generates every wrapper with its digests pinned.

### Round 2b r3 (after the a4f6d410 review HOLD)

`a4f6d410` got a SOURCE_PASS from reviewer A (rebind fidelity) and a HOLD from reviewer B (live
sequence). Both transcripts are filed with the runner. The four must-fix items are settled as follows.

1. **WATCH used the quiescent host observer, which refuses while the worker runs.** `watch-r11.py` now
   uses the base `active_epoch()` check, the identity check the lifecycle already uses while a worker
   is live, bound to the window `before.json`. It also matches the worker by its cwd inside the
   worktree. For each matching process it records one boolean, whether GIT_OPTIONAL_LOCKS=0 is in its
   environment; nothing else from the environment is read into evidence.
2. **A real worker can drift what RESTORE compares.** Three sources:
   - **Pack-cache `.git` times.** Every gc config load runs `git status --porcelain` in the pack cache
     (Core `internal/config/pack_include.go` validateLockedRemoteCache), with the caller's
     environment passed through.
     - The supervisor's environment carries GIT_OPTIONAL_LOCKS=0, checked by name only, never
       printed.
     - The signing-worker wrapper passes its parent environment through, removing only
       ANTHROPIC_API_KEY (Template `lib/gct_claude_subscription.py` subscription_environment).
     - The R10 window ran resume, session creation, suspend and a passing restore over half an hour,
       and kept all four cache `.git` directories exact.
     - In the window, WATCH records the worker's own GIT_OPTIONAL_LOCKS, and the brief asks the
       worker to record it.
   - **Exact atime on the compared objects.** Relatime refreshes an atime only when it is not newer
     than mtime or ctime, or is older than 24 hours. On 2026-09-23 about 70 compared objects carried
     atimes about 22 hours old: the protected platform trees, half the city children and the
     provisioning tree. They would go stale mid-window, and the R9 restore already needed a reviewed
     accounting of exactly such reads.
     - New `freshen-r11.py` (`FRESHEN.sh`) runs before OBSERVE and before any window root exists, and
       is repeatable with a fresh root per run. It reads one byte of each file and lists each
       directory. It requires that nothing but atime changed, and that every object ends fresh and
       younger than 19 hours. Otherwise it refuses and lists when each old object passes its
       24-hour mark, so a rerun after that time refreshes it.
     - The city root and the provisioning directory get new mtimes at the atomic renames, so no
       freshening can hold them. ADMIT checks them.
   - **Route files.** The route chain already binds route-file metadata between reloads. ADMIT checks
     it before RESTORE is consumed.

   New `restore-admission-r3.py` (`ADMIT.sh`) is the R10 `restore-admission-r1.py` (`90328ee7`),
   rebound to `window-r11.py`. R10 ran it before its passing restore. It is read-only:
   - complete containment and the terminal lifecycle;
   - the quiescent host, meaning city and rigs suspended and zero sessions;
   - a full `restore-admission.json` snapshot with the window preservation check.

   `RESTORE.sh` now requires `restore-admission-pass.json`. So a drift refuses before RESTORE is
   consumed, with the evidence kept for a reviewed successor.
3. **A failed lifecycle step strands containment.** New `hold-r11.py` (`HOLD.sh`) acts only when a
   `suspension-*-failure.json` or `-refused-after.json` exists:
   - it runs the same supported `gc suspend --json` and `gc rig suspend gascity --json`, only for
     whatever is still resumed;
   - it checks `gc status` before and after, and uses the active-epoch identity check;
   - it writes nothing in the window root.

   `CONTAIN.sh` now runs each suspend only after its resume event exists and only while its own
   event is absent.
4. **Sandboxed `git add`.** Refuted.
   - The worker starts with `--add-dir /home/loucmane/gascity/city/rigs/gascity/.git` (receipt
     `profiles[0].argv`).
   - The Claude Code sandbox docs say sandboxed commands may write to `--add-dir` directories.
   - Separately: "when the working directory is a linked git worktree, the sandbox also allows writes
     to the main repository's shared `.git` directory so commands such as `git commit` can update refs
     and the index. Writes to `hooks/` and `config` inside that directory remain denied."
   - The Template's own finding (docs/native-findings.md) is why that directory is a writable root.
   - The brief adds startup probe 6, a standalone `git update-index --refresh`, which proves index
     writes before any source edit.

Should-fixes taken:
- `RESUME.sh` requires the ROUTE and route-audit results.
- `route-task-r5.py` checks the BIND root authority (0700, uid 1000).
- The reconcile script asserts, before its write, that no dependency or dependent of ga-e0t1.14 or
  ga-4z38 names ga-y49e.
- The generators assert full digests for every P6, prep and module input.
- The forecast also runs `capture_routes` over the five route stores.
- The brief states the three-hour hold.
- WATCH records evidence; the coordinator judges residue.

Should-fixes checked instead of changed:
- `pin_inputs` pins only recorded P6 evidence and binaries, never the live city or receipt
  (`p6-readiness.py` composition, and `p6-input.py` proven_draft "Independent of the live
  receipt"). So the staged snapshots cannot refuse on it.
- Claude trust for the Core worktree resolves through the trusted main repository
  `/home/loucmane/gascity/city/rigs/gascity`.

Known stop conditions that stay stops:
- A STAGE failure before its reload event.
- An audit-route refusal after the single sling. ga-4z38 stays routed, and there is a disposition.
- A drain of the singleton while it waits for a release.

**Read-only forecasts, 2026-09-23** (with GIT_OPTIONAL_LOCKS=0; the pack-cache `.git` times are
unchanged throughout):
- Admission: zero differences from P6 plus the disposition, providers equal, `directories()` clean,
  and all five route stores captured and stable.
- Audit rules in both stores: the only stop row is ga-y49e, which RECONCILE handles.
- All 1504 template session Beads are closed.
- The ready queue is exactly ga-y49e.
- No dependency edge names ga-y49e.

**Jobs, in order.** All jobs run at one reviewed commit. The ga-e0t1 worktree stays clean at that
commit from RECONCILE until TERMINAL; every job, CONTAIN and HOLD included, checks this.
1. `RECONCILE.sh`: ga-y49e to `blocked`.
2. `BIND.sh`: the brief and the requested attempt metadata on ga-4z38. From here until ROUTE, no
   coordinator note goes to ga-4z38.
3. `FRESHEN.sh`: repeat until it passes. The ~22-hour group passes its 24-hour mark around
   19:30Z, which is 21:30 CEST.
4. `OBSERVE.sh`.
5. `PREFLIGHT.sh`: T0, the start of the four-hour cache-atime window.
6. `STAGE.sh`.
7. `ROUTE.sh`.
8. `RESUME.sh`.
9. In-window, with repeated `WATCH.sh`:
   1. Observe one session and its claim.
   2. Startup review.
   3. SOURCE_RELEASE by gc mail.
   4. Candidate review.
   5. SIGNING_RELEASE.
   6. The worker's managed signature.
10. `CONTAIN.sh`; if the lifecycle is stranded, `HOLD.sh` instead, and the window stops there.
11. The supported `gc runtime drain` and `gc session close` of the one session, then a `WATCH.sh`.
12. `ADMIT.sh`.
13. `RESTORE.sh`.
14. `TERMINAL.sh`.
15. Delivery of the signed branch.

**Deadline.** At T0 plus three hours, the coordinator contains regardless of the worker's progress.

## Quiet window

From RECONCILE until TERMINAL has passed, the ga-e0t1 worktree stays clean at the package commit.
Records go to Bead notes, always with `GIT_OPTIONAL_LOCKS=0`, and to staging. Between BIND and ROUTE,
no notes go to ga-4z38. A plain gc call changes the pack-cache `.git` mtime; that was verified
2026-09-23.
