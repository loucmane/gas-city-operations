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
  - Releases arrive as lines in ga-4z38's own notes (from r6), which the worker reads with the
    policy-allowed `bd show ga-4z38 --json`. The control policy `16022d04` allows no `gc mail`.
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

### Round 2b r4 (after both 387fecdd reviews held)

Both reviews of `387fecdd` held, and both transcripts are filed. r4 answers every must-fix:
- **FRESHEN could never run.** It read `w.CACHE`, which the base does not define. It now takes the
  cache path from the support module (`b.CACHE`). `test_round2b.py` runs `objects()` offline over the
  real P6 and provider files, so this class of error is tested.
- **FRESHEN missed the API symlink** (`p6-readiness` NATIVE_LINK), whose atime the provider pins
  compare exactly. Now:
  - it is in the set;
  - symlinks are refreshed with readlink and must end young like everything else;
  - objects on noatime or read-only mounts are recorded instead of required young;
  - no P6 pin may lie under the cache;
  - the city is listed through an O_NOATIME descriptor, so `objects()` itself changes nothing.
- **Probe 6 did not prove a write.** It is now `git update-index --refresh --force-write-index`, which
  always writes the index, and `git hash-object -w <fixture>`, which writes one object. Both targets
  are in the shared Git common directory.
- **The worker environment had not been shown to inherit GIT_OPTIONAL_LOCKS=0.** New
  `proof/worker-env-proof.py` (read-only, in the tests) checks every link:
  - the live supervisor carries it (one entry, tested by name);
  - Core at the worker base `e6366b9e` never sets or unsets it in non-test code; its only mention is
    the docsync test of the supervisor's cache-readonly systemd drop-in that sets it;
  - the tmux executor runs `tmux` with no custom environment, so the city tmux server inherits the
    supervisor's;
  - a new session unsets only empty-valued keys;
  - the signing wrapper removes only ANTHROPIC_API_KEY.

  WATCH still records the worker process's own value in-window.

Should-fixes taken:
- **HOLD.**
  - It also treats a lifecycle intent without its event, and any started phase without its phase
    record, as stranded.
  - It is best-effort: it records the active-epoch check and the initial status without requiring
    them, and attempts each needed suspend with any exit status even if the other refused.
  - Only the final `gc status` decides.
- **PREFLIGHT** requires a FRESHEN pass from the last 45 minutes.
- **WATCH.**
  - It uses `git diff-files` and `git diff-index` plumbing, which never refreshes or locks the
    worker's index.
  - It parses NUL-separated status, and records lstat failures instead of crashing.
- **The hold moves to T0 plus 2 h 45 min.** CONTAIN, the close, WATCH, ADMIT, RESTORE and TERMINAL
  then have about 75 minutes before the four-hour bound.

**Operator precondition.** The host must stay awake with no clock change from FRESHEN until TERMINAL,
roughly 21:30 to 01:45 CEST tonight. Every bound check requires the realtime-to-boottime offset to
stay within 100 ms from T0 (`cache-atime-policy-r1.py`), and a WSL sleep or resume steps the clock.

**Known stop conditions** (each keeps its evidence and needs a reviewed successor):
- A STAGE failure before its reload event.
- A post-reload STAGE failure: ADMIT requires the staged city and receipt.
- An audit-route refusal after the single sling, which leaves ga-4z38 routed.
- A drain of the singleton while it waits for a release.
- Host-epoch drift, when only manual containment remains.
- Any drift ADMIT reports after drain and close. Those two have not run against a live session before.

Operational limits:
- No WATCH between SIGNING_RELEASE and SIGNED_CANDIDATE_READY.
- No log or commit into the ga-e0t1 worktree until TERMINAL has passed; every job, CONTAIN and HOLD
  included, requires it clean at the package commit.
- No Bead notes between PREFLIGHT and STAGE, while the route files are compared exactly.

The rig `.beads` directories and route files are regenerated by the STAGE reload and bound by the
route-event chain from then on. Two of those stores are the protected blog and hpfetcher checkouts,
which FRESHEN never reads.

### Round 2b r5 (after the 4934c9d8 review HOLD)

`4934c9d8` got a SOURCE_PASS from reviewer A and a HOLD from reviewer B. Both transcripts are filed.
r5 answers the three must-fix items:
1. **Every in-window mutation is now a reviewed job.**
   - `release-r11.py` backs `SOURCE-RELEASE.sh` and `SIGNING-RELEASE.sh`. It reads the coordinator's
     release body from staging as untrusted input, and validates it against the live state:
     - exactly the named session is live for the template;
     - ga-4z38 is in_progress and assigned to it;
     - source release: the startup-proof digest matches, and the `.gitignore` entries are exactly the
       untracked paths;
     - signing release: HEAD is unchanged, and only allowed paths are staged, with nothing unstaged or
       untracked.

     It then sends exactly one gc mail from the human mailbox to the template lane. It reads the
     message Bead back and requires the exact body in one field; an earlier release mail kept its body
     verbatim in `description`. Each release has a fixed root, so it is never sent twice.
   - `close-r11.py` (`CLOSE.sh`) runs after CONTAIN:
     - a best-effort `gc runtime drain`, then up to 60 s of polling;
     - a required `gc session close`;
     - up to 120 s until there is no open template session, no city tmux pane for it, and no
       worktree process.

     This is the sequence gct-m1wh attempt7 used. It sends no signals and never touches tmux itself.
   - Every job uses the support environment (GIT_OPTIONAL_LOCKS=0) and the active-epoch check. No
     live step runs outside a reviewed job any more.
2. **Time-left gate.** New `budget-r11.py` reads the window `before.json` clock start and the kernel
   boot clock, and refuses unless enough of the four-hour bound remains:
   - `ADMIT.sh` needs 40 minutes;
   - `RESTORE.sh` needs 25 minutes, checked before RESTORE consumes itself;
   - `TERMINAL.sh` needs 8 minutes.
3. **The singleton is not drained while it owns ga-4z38.** New `proof/singleton-proof.py` (read-only,
   in the tests) shows it from source:
   - the overlay gives the worker no custom ScaleCheck or WorkQuery, so the default applies;
   - the default demand counts only ready, unassigned, routed work;
   - `cmd/gc/pool_desired_state.go` at `e6366b9e` takes new-session demand from scale_check but "only
     preserves sessions that already own actionable work", and its resume tier keeps a session whose
     assigned bead is in_progress or open.

   So after the claim, the worker session is kept even though scale_check returns 0.

Should-fixes taken:
- **HOLD.** It also acts after a `CONTAIN.sh` job ended non-zero in the runner's done records, because
  a lifecycle refusal before any intent writes nothing in the window root. Its stranded detection is a
  tested function, and it requires the final status `ok`.
- **FRESHEN.** It now requires every object to be on a writable relatime mount, and refuses otherwise;
  there are no more exemptions. It records its executor digest, and its docstring is corrected (45
  minutes, symlinks read). `PREFLIGHT.sh` accepts only a FRESHEN `result.json` that says `ok`.
- **Environment proof.** It reads the wrapper module with O_NOATIME, and its wording is exact about a
  name search.
- **Brief.** Keep output small: an automatic compaction runs the handoff hook, and a cycled session
  cannot be replaced inside this window.
- **Wrappers.** The refusal line now says "before any further step", since FRESHEN is meant to be
  rerun.

Reviewer B's route-file concern is settled by R10's evidence. In R10 the regenerated route files had
atime no newer than mtime, yet the restore reload's before-capture equaled the stage-reload
after-capture exactly, across a resume, a session create and a suspend. Direct `ga-`/`ci-` Bead
prefixes resolve without the route file. In-window Bead calls use direct prefixes only.

**Residue.** Probe 6's `git hash-object -w` and the worker's `git add` leave loose objects in the Core
object store. The managed commit makes the staged ones reachable. The probe blob stays unreachable
until git's own gc, and it is declared here.

### Round 2b r6 (after both f68b0f3d reviews held)

Both reviews of `f68b0f3d` held, and both transcripts are filed. r6 answers them:
- **The runner starts a wrapper path at most once per commit** (gct-jobrunner A4). Its "already ran"
  key is the pair of commit and wrapper path. Steps that may run more than once now get numbered,
  separately pinned wrapper slots, each an identical step:
  - `FRESHEN-1..3`;
  - `WATCH-1..8`;
  - `SOURCE-RELEASE-1..2`;
  - `SIGNING-RELEASE-1..2`;
  - `CLOSE-1..2`.
- **Release transport.** A release is one line appended to ga-4z38's own notes:
  `SOURCE_RELEASE ga-4z38 <json>` or `SIGNING_RELEASE ga-4z38 <json>`. The worker reads it with the
  same `bd show ga-4z38 --json` it uses for its claim, so it never reads another store and never
  resolves a route file. A `gc session nudge --delivery wait-idle` only wakes the worker.
  - All validation runs in a fresh timestamped root. The exclusive marker
    `/var/tmp/ga-4z38-<mode>-release.posted` is taken right before the single append, and a readback
    follows.
  - A later slot, once the marker exists, only verifies the posted line and nudges again. A refusal
    before the marker consumes nothing.
  - The accepted assignee forms follow Core `cmd/gc/cmd_hook.go`: the claim writes the first
    non-empty of session name, session id, alias, agent and template.
- **CLOSE is repeatable.** The drain runs at most once, behind the exclusive marker
  `/var/tmp/ga-4z38-close-drain.requested`, and is wrapped so a drain failure still reaches the close.
  The close runs only while the session is still open. Each run gets a fresh root. CLOSE also accepts a
  passing HOLD in place of CONTAIN, and a tmux exit 1 counts only as "no server".
- **ADMIT requires a passing CLOSE.** PREFLIGHT requires a FRESHEN result that says `ok` and carries
  the pinned FRESHEN digest.
- **New `proof/cli-proof.py`** (read-only, in the tests) asks the installed binary for the result
  schemas of `session list`, `session nudge`, `session close` and `runtime drain`. It also shows from
  Core source that `gc status` emits only three health signals: city_suspended,
  controller_not_running and no_agents_running. The window allows the first and third and requires
  the controller running, so a live worker cannot add a signal the suspend check refuses.

**Dispositions.** Every refusal keeps its evidence and never replays a mutation.
- Release before its marker: fix the staged input, run the next slot.
- Release after its marker with a failed nudge: run the next slot, which only nudges.
- Release whose append is ambiguous (marker taken, line absent): stop, as an ambiguous mutation.
- CLOSE: run the next slot.
- FRESHEN: run the next slot after the times in `old.json`.
- A budget refusal: the window stays contained, and restoring needs a reviewed successor.
- A lifecycle strand: run HOLD, then CLOSE; restoring needs a reviewed successor.

### Round 2b r7 (after both 4da50bdf reviews held)

Both reviews of `4da50bdf` held, and both transcripts are filed. r7 answers them:
- **A later release slot only verifies and nudges.** The release job now has two checks:
  - `validate_live` checks the release shape, that `gc status` shows the city resumed, the one named
    live session, and its claim. It runs on every slot.
  - `validate_worktree` checks the startup-proof digest, the untracked set, and HEAD with the staged
    paths and the staged-patch digest. It runs only before the post.

  Before the post, no line with the release prefix may exist. After it, the posted line must be the
  LAST line with that prefix. bd joins appended notes with one newline, as seen in these notes. That
  last line is the one the worker takes. The signing release also requires the source release line.
- **The nudge wakes the worker for certain.** `--delivery immediate` is used, and only the outcome
  `delivered` passes.
  - Immediate types the text into the session's tmux pane now (tmux provider NudgeNow). An idle
    Claude session gets a new prompt; a busy one keeps the text in Claude's own input queue.
  - `wait-idle` would queue the nudge for a later dispatcher delivery whenever the session is not idle
    within 30 seconds.
  - `proof/cli-proof.py` now checks both paths in Core source.
  - The nudge text no longer starts with the release prefix.
- **CLOSE requires zero panes in the city tmux server.** Every other agent stays suspended in this
  window. Exit 1 is accepted only when tmux says no server is running or it cannot connect. The drain
  poll is wrapped, and exactly one open session is required before the close. The result records its
  executor digest, and ADMIT requires a passing CLOSE result carrying the pinned CLOSE digest.
- **Slots and gates.**
  - `HOLD-1..2` are slots now, and HOLD polls its final status for up to 30 seconds.
  - There are three slots per release.
  - `SOURCE-RELEASE` needs 100 minutes left and `SIGNING-RELEASE` needs 85, so the signature has at
    least 10 minutes before the T0 + 2 h 45 min hold.
- **The signing release carries the staged-patch digest** that the candidate reviews saw. The job
  recomputes it from `git diff-index --cached --patch HEAD`.
- **Git calls on the worker worktree** from release and WATCH pass
  `-c core.fsmonitor=false -c core.hooksPath=/dev/null`.

**In-window review binding.** The startup and candidate reviews happen before the worker's change
exists as a commit. They are bound to this package commit, the only valid candidate there, and they
are NEVER filed with the job runner. The runner refuses every job at a commit that has any filed
non-PASS review, so filing an in-window HOLD would block CONTAIN through TERMINAL. Their verdicts go
to the ga-4z38 and ga-e0t1 records and into the release `reviews` field. Only job-admission reviews
are filed. The delivery review of the signed commit binds to the Core worktree with a `worktree=`
token.

### Round 2b r8 (after both e3b01b2c reviews held)

Both reviews of `e3b01b2c` held on the staged-patch digest contract, and both transcripts are filed. r8:
- **One patch definition.** The worker and the signing release job both write the staged patch with
  `git diff-index --cached --patch --output=<file> HEAD` and hash the file's bytes. The worker also
  writes `candidate.json` with head, tree and patch digest. The signing release must equal it, and
  the job derives all three again from the live index.
- **Whole-document JSON.** `gc status --json` prints one indented document over many lines. r7 parsed
  only the last line, which would have failed. The release job now parses every gc JSON output as one
  document.
- **The worker session must be active before a post.** The nudge gives a managed session that is not
  running a queued wake instead of an immediate delivery (Core `shouldQueueManagedNudgeWake`). The
  session list reports a running session as `active`, because Core `normalizeInfoState` maps the
  reconciler's `awake` to `active`. city.toml has no `[api]` section, so the list takes the direct
  store path with one-line rows. `proof/cli-proof.py` checks all three in Core source and in
  city.toml, and passes live.
- **The nudge text names the absolute bd path** that the brief uses.
- **`CONTAIN-1..2` are slots.** If CONTAIN refuses before any lifecycle intent (umask, HEAD or epoch),
  the second slot retries it. HOLD counts a non-zero run of either slot as stranded.
- **WATCH compares the route files** with the STAGE reload's after-capture, which ADMIT later requires
  exactly, and records any field that differs. It only records, as an early warning of an ADMIT
  refusal. The route files' atimes have equalled their mtimes since 10:45 CEST today, through the
  day's gc and bd calls, so ordinary calls do not read them.
- **CLOSE** accepts tmux exit 1 only for "no server running", or for a connect error with "No such file
  or directory" or "Connection refused".
- **The PREFLIGHT and ADMIT gates** only accept results owned by uid 1000.
- **Erratum to the r7 CLOSE bullet above**, which says "exactly one open session is required before
  the close". The job requires at most one, and closes it only if it is still open.
- **No nudge over a permission dialog.** The worker runs with `--permission-mode auto` (Core builtin
  claude profile auto-edit), and nothing proves it never shows an approval dialog. The immediate
  nudge ends with Enter, which would answer one.
  - The release job captures the worker's visible pane the way Core does,
    `tmux -L city capture-pane -p -t <session_name>`. It refuses while the pane shows a Claude
    permission dialog, Core's own approval markers, or a `1. Yes` choice line.
  - The check runs after the live validation, before the post, and again right before the nudge. A
    refusal before the post consumes nothing, and a later slot retries.
- **The city tmux socket is `city`.** Core names it after the city unless `[session] socket` is set.
  city.toml sets no socket, and `gc status` reports `city_name` city. `proof/cli-proof.py` checks
  this, together with Core's capture form.

**Operating limits.**
- **Budget refusal.** A budget refusal while the worker is live never ends the window without
  containment. Contain at once with `CONTAIN-1.sh`, or `CONTAIN-2.sh` if the first refused before
  any intent, then CLOSE. A release slot past its cutoff can neither post nor nudge again.
- **RESUME refusal.** A RESUME refusal before its first intent is a stop, because nothing was resumed.
  CONTAIN has nothing to suspend, and CLOSE requires a suspension record. The staged city stays
  suspended, which is safe, and its restoration needs a reviewed successor. After a partial RESUME,
  CONTAIN suspends whatever resumed.
- **Queued nudge.** If a nudge comes back queued, the release job fails after its post, and the posted
  line stands. A WATCH shows the session state, and the next slot nudges again once the session is
  active. With no slot or budget left, contain.
- **Review binding is policy-only.** The startup and candidate reviews bind to this package commit.
  Their prompts carry no `Wrapper:` lines, so they can never admit a job, and they are never filed.
  The release job checks only that two non-empty review records are named. The verdicts are recorded
  on ga-4z38 and ga-e0t1.
- **Core worktree.** No operator shell, editor or other process may use the Core worktree during the
  window. WATCH lists every process whose argv or cwd names it, and CLOSE refuses while any remains.
- **WATCH baselines.** One WATCH slot runs after ROUTE and before RESUME, as the baseline with zero
  panes on the city tmux server. The first WATCH after RESUME must show the worker pane under
  `tmux -L city`.

### Round 2b r9 (after both 4a81d704 reviews held)

Both reviews of `4a81d704` held, and both transcripts are filed. Both named the same defect, and
review B named a second. r9 fixes them, and each fix now has a test that runs the real code.
- **The release job ran two phases under one name.** The base refuses a phase name used twice in one
  root. So every release would have failed after its post, before the nudge, and every later slot
  would have failed the same way. The two captures are now `pane-before-post` and
  `pane-before-nudge`.
  - A new test runs release `main()` against the real `window-base-r11.py`, with only the owned-phase
    runner faked. It covers a refusal on a dialog, both slots of both modes, one post per mode, and a
    tree refusal.
- **WATCH reused a variable name.** The route check overwrote `staged`, so every WATCH after STAGE
  would have crashed. The check is now its own function, `routes_since_stage`, with a test. A second
  test runs WATCH `main()` on the real base, both before and after STAGE.
- **Mutation check.** Each new `main()` test fails on its exact r8 defect, applied to a temporary copy
  of the r9 package:
  - one phase name used twice fails with `phase already consumed`;
  - CLOSE without the kill fails with `residue remains ... processes=1`;
  - the reused WATCH variable fails with an AttributeError on `splitlines`.
- **The city tmux server outlives the worker session.** Core sets exit-empty off on every session
  create. The server started by the worker's `new-session -c <worktree>` keeps the worktree in its
  argv, so CLOSE would count it as residue forever. The ga-5ot6 R10 restore needed a manual
  `kill-server` for exactly this.
  - When no open session remains and the city server has no pane, CLOSE now runs
    `tmux -u -L city kill-server`, at most once per run. Core's own `gc stop` ends the server the same
    way (`TeardownServer`).
  - A test runs CLOSE `main()`. It kills an empty server exactly once, and it never kills a server that
    still has a pane.
- **The tree is derived, read-only.** The signing release's tree must list exactly the staged index:
  `git ls-tree -r -z --full-tree <tree>` must equal `git ls-files -s -z`, all at stage 0.
  - A test checks this in a real temporary repository.
  - **Erratum** to the r8 "One patch definition" bullet above: r8 compared the tree only with the
    worker's `candidate.json`. It did not derive it, as that bullet claimed.
- **Full object names in the patch.** Worker and job both pass `--binary --full-index`. A test shows
  the patch bytes are identical with an empty HOME, with a HOME that sets noprefix, patience,
  context 9, abbrev 4 and color always, and with the job's `-c` overrides.
- **The pane check.**
  - It uses Core's exact form, `tmux -u -L city capture-pane -p -t <session_name>`.
  - It also refuses a selection cursor on any numbered option, which covers AskUserQuestion and the
    usage-limit menu.
  - A capture that exits 0 proves the session's pane is running.
  - Residual gaps:
    - a dialog can still appear between the capture and the nudge's Enter;
    - a dialog drawn without these markers is not seen;
    - a persistent false positive would use up the release slots, and would then be recorded as a stop.
- **CLOSE parses `gc session close --json` as JSONL.** Exactly one record must name the session.
- **Worker-written files are read only as regular files of at most 1 MiB.**
- **`proof/cli-proof.py` now proves three more facts, and passes live:**
  - the Core source it checks is the binary's source: gc 69d00186 was built from signed 796d9a7a,
    recorded on ga-mutg, and the worker base e6366b9e has the same tree, f2c120a5;
  - the overlay city.toml the window runs (5f3b60e1) has no `[api]` section, no `[session]` socket
    and no workspace name;
  - Core keeps the tmux server alive between sessions.
- **Erratum** to the Jobs list: after HOLD, CLOSE still runs, because it accepts a passing HOLD. The
  window then stops before ADMIT, and restoring needs a reviewed successor. The Dispositions line
  "run HOLD, then CLOSE" was right.
- The job runner README now records the in-window review exception.

### Round 2b r10 (after the 3c4b0975 review A HOLD)

Review A of `3c4b0975` held, and its transcript is filed. The r9 kill-server branch could never run.
- **The cause.** CLOSE decided emptiness with `list-panes -a`. A live server with no session answers
  that with exit 1, "no current target". CLOSE refused that answer as a failed listing, so both slots
  would have refused and ADMIT could never pass.
  - Tonight's probe on a throwaway socket confirmed the answer on this host (tmux 3.4).
  - Core's own `wrapError` reads this answer as a live empty server.
  - The r9 test's fake answered an empty server with exit 0, which is not how tmux behaves.
- **The fix.** CLOSE now reads the city server with `list-sessions -F '#{session_name}'`. A live server
  answers that with exit 0 even when it holds no session. With no open template session and no tmux
  session, CLOSE runs `kill-server` once. Exit 1 counts only for Core's no-server answers: no server
  running, error connecting (no such file or connection refused), and server exited unexpectedly.
- **New `proof/tmux-probe.py`, run in the tests.** It starts a private server on the throwaway socket
  ga4z38-tmux-probe, never `city`, with exit-empty off. It records the answers with one session, with
  none, and after `kill-server`, then removes its own socket. It passes. The CLOSE test now uses these
  real answers: a live empty server (killed once), a server that still holds a session (refused as
  residue, never killed), and no server (nothing to kill).
- **`session close --json` is proven to be one line.** `writeSessionActionJSON` writes through
  `writeCLIJSONLine`, a `json.Encoder` without indentation.
- **The tree derivation is proven on the real repository.** `ls-tree -r -z --full-tree` of the base
  tree f2c120a5, about 0.5 MB, equals `ls-files -s -z` of the worker worktree's index. The owned-phase
  runner captures stdout with `communicate()`, which does not truncate.
- **Worker-written files are bounded on the open descriptor** (regular, uid 1000, one link, at most
  1 MiB), in both the release job and WATCH. WATCH records an oversized file without its digest.
  **Erratum** to the r9 bullet "Worker-written files are read only as regular files of at most
  1 MiB": in r9 that held only in the release job, and it was checked with lstat before the read.
- **WATCH's route check** records any exception, not only RuntimeError.
- **HOLD `main()` now has a real-base test.** HOLD suspends a stranded window in order (city, then
  rig), writes nothing in the window root, and refuses a window that is not stranded.
- **Erratum** to the r9 cli-proof bullet: the proof checks the installed gc digest and that 796d9a7a
  and e6366b9e have the same tree. That the binary was built from signed 796d9a7a is recorded on
  ga-mutg; the proof does not check it.
- The release docstring no longer claims that an exit-0 capture proves the pane is running. A dead pane
  kept by remain-on-exit would still capture; the active state and the nudge outcome cover that case.

### Round 2b r10, continued (after the 3c4b0975 review B HOLD)

Review B of `3c4b0975` also held, and its transcript is filed. Its must-fix: nothing proved the worker
session survives its idle waits. Any runtime restart ends the attempt, because BIND stamps the task
attempt and Core never starts an attempt twice.
- **`proof/singleton-proof.py` now proves the session survives.** From the pinned overlay config
  (config.isolated.json 6c4b44c4) and Core source:
  - the worker has no idle_timeout, no max_session_age and no sleep_after_idle;
  - the gascity rig's and the workspace's session_sleep defaults are empty, so Core resolves sleep to
    off;
  - claim_holder_stall_timeout is unset.
  The city's progress_stall_timeout (5m) restarts only a claim-less session. For a claim holder, Core
  only adds the needs/operator label and progress-stall metadata to the claimed work, never its status
  or assignee. The managed signer reads no Bead label, status or assignee. The proof passes live.
- **The brief tells the worker to claim at once** (it was already the first command), and says why.
  It also says the needs/operator mark during a long wait is expected, not a stop. **Declared
  consequence:** after a review wait of more than five minutes, ga-4z38 carries that label and
  metadata. The coordinator clears them in the closeout.
- **CLOSE releases the task.** `gc session close` releases the work assigned to the closed session, so
  ga-4z38 ends open, unassigned and still routed. Its attempt is started, so no new session can start
  for it. The delivery closeout closes it after the merge. Before any later window, the audit would
  stop on it, as it did on ga-y49e. This is declared in the CLOSE docstring.
- **RESUME stops before resuming if the city tmux server already holds a session.** This is a
  read-only `list-sessions` gate in the wrapper. CLOSE can end only an empty server.
- **The tmux socket directory is proven.** The supervisor has no TMUX_TMPDIR and no TMUX, checked by
  name. The jobs' fixed support environment names neither, so both sides use /tmp/tmux-1000.
- **WATCH redacts tmux `-e KEY=VALUE` values** in recorded argv. The city tmux server keeps Core's
  new-session argv, which carries the session environment.
- **Rig stores.** `gc session close` opens every rig's native store. Tonight's `gc status` calls, which
  open every rig store, left all five route files at their 10:45 CEST atime, equal to their mtime. So
  opening a store does not read `routes.jsonl`. The post-CLOSE WATCH repeats the route comparison
  before ADMIT.
- **After CLOSE's kill-server**, the next listing may answer "server exited unexpectedly"; this is
  accepted as no server. Or it may still list an empty server, and then the loop waits for the process
  to go.
- **The mutation check is a committed test.** `test_main_tests_fail_on_each_defect_they_guard` copies
  the package and applies each r8/r9 defect. It requires the guarding `main()` test to fail with the
  named symptom. The CLOSE row includes the r9 `list-panes` defect.

### Round 2b r11 (after the 6f344788 review A HOLD)

Review A of `6f344788` held, and its transcript is filed.
- **Erratum to the r10 brief claim.** The r10 section says the brief tells the worker to claim at once
  and that the needs/operator mark is expected. The r10 package brief did not contain that text: only
  the scratch copy was edited. r11 carries the text; a test pins it before the first command, and
  BIND's BRIEF_SHA to the brief. `regen.py` now copies every scratch-owned source (the brief, the
  operator generator, cli-proof and tmux-probe) into the package on every run.
- **`bounded_read` opens with O_NONBLOCK.** A FIFO planted at a worker file no longer blocks the open;
  fstat refuses it. A test plants one.
- **The RESUME gate fails closed.** Only an empty listing, "no server running on …" or "error
  connecting to …" passes. Any other answer stops. It runs tmux with TMUX_TMPDIR and TMUX removed, so
  the socket directory is Core's default whatever the user manager's environment holds. A test runs
  the exact gate text against a throwaway tmux server in all three states: no server, a live session,
  and a live empty server.
- **The CLOSE test uses the probe's answers.** The no-server answer is "no server running on …" (the
  stale socket file remains). A live empty server answers `list-panes` with "no current target". So
  the mutation row for the r9 defect now fails with `tmux listing failed`, the real symptom.
- **WATCH redacts every KEY=VALUE token** in recorded argv, including assignments inside a pane
  command string such as `exec env KEY=VALUE …`.
- **cli-proof runs the window's pinned owned-phase runner** on the full base listing, and its stdout
  must equal the direct listing byte for byte.
- **The singleton proof states exactly what it checks for the signer.** The signer treats the Bead only
  as an identity string checked against its policy prefix. Both signer files import only the standard
  library and name no bd or gc executable. They reference no assignee, label, needs/operator,
  progress_stall or controller_error. `[chat_sessions] idle_timeout` is unset.
- The CLOSE result key `city_panes` is now `city_tmux_sessions`.

### Round 2b r11, continued (after the 6f344788 review B HOLD)

Review B of `6f344788` also held, and its transcript is filed. Its must-fix was the same missing brief
text, which r11 adds. Its should-fixes:
- **The mark does not end the session.** `proof/singleton-proof.py` checks that the resume tier, which
  keeps a claim holder's session, filters its work only by status, assignee and route, never by label
  or metadata. It also checks that no non-test Core code reads needs/operator except the
  provider-failure writer's own de-duplication. The signer check now also excludes any `failure_` key.
- **The tmux binary.** Core runs `tmux` through the supervisor's PATH. `proof/worker-env-proof.py`
  checks that this PATH resolves it to /usr/bin/tmux, the binary the jobs name. It reads only the PATH
  value.
- **A process left in the worktree.** The brief forbids background and detached processes.
  **Disposition:** if both CLOSE slots refuse on a remaining worktree process, the window stops there.
  CLOSE never signals a process, so restoring needs a reviewed successor, as after HOLD.
- **The occupied-server check comes first.** PREFLIGHT, before anything is consumed, carries the same
  fail-closed tmux gate as RESUME. A test pins that the text is identical.
- **The worker's hooks.** Each release nudge runs the worker's UserPromptSubmit hooks (`gc hook run`
  with nudge drain and mail check). They run already at its first prompt, as its SessionStart hook
  does, so a release adds nothing new in kind. ADMIT compares only the names and identities of the
  city's `.gc` and `.beads` direct children. Every WATCH now compares them with PREFLIGHT's
  `before.json` (`runtime_children_unchanged_since_preflight`). The routes.jsonl inode is left to the
  route check. So the first WATCH after the worker starts shows whether ADMIT can still pass.
  **Declared residual:** if it cannot, the window still contains and closes, and the restore needs a
  reviewed successor.
- **Declared and not fixable in this package:** an automatic context compaction runs the PreCompact
  handoff, which ends the attempt. The brief keeps output short for that reason.

### Round 2b r12 (after the 8d45c6b4 review A HOLD)

Review A of `8d45c6b4` held, and its transcript is filed.
- **The r11 redaction weakened r10's.** It ended a value at the first space or quote, so `K=a b` in an
  `-e` element and `K='v w'` in a command string kept part or all of the value.
  - Now the element after `-e`, an `-eKEY=VALUE` element and any element that is itself `KEY=VALUE`
    lose everything after the first `=`.
  - Inside any other element, each `KEY=` loses its value up to the next unquoted whitespace, quoted
    runs included.
  - The test covers spaced, quoted, mixed and missing values.
  - **Erratum** to the r11 WATCH bullet: its "every KEY=VALUE token" did not hold for quoted or spaced
    values.
- **The tmux gate now stops on any running city server, empty or not.** The worker's pane must inherit
  the supervisor's environment (proof/worker-env-proof.py). A server that is already running would
  hand it that server's environment instead, and CLOSE can end only an empty server.
  - Only the no-server answers that CLOSE also accepts pass: "no server running on …", or "error
    connecting to …" with no such file or connection refused.
  - The test runs the exact gate text on a throwaway socket with:
    - no socket;
    - a live session, with and without TMUX_TMPDIR in the environment;
    - a live empty server;
    - a stale socket after kill-server;
    - a stand-in tmux printing unknown errors.
  - Tonight's read-only check, the same command: no server is running on the city socket.
- **The singleton proof** now also requires that no cmd/gc code reads the mark's metadata keys except
  the stall-signature de-duplication. Its stdlib-import check also sees indented imports.
- **Wording.**
  - **Erratum** to the r11 hooks bullet: a WATCH comparison of the runtime children is an early
    warning only, since children created later by a release nudge, the drain or the close are not
    forecast. The WATCH after CLOSE is the one that matters for ADMIT.
  - **Erratum** to the r11 tmux-binary bullet: worker-env-proof reads the supervisor's whole environ,
    but records only key names and PATH-derived booleans.
  - cli-proof writes a phase record into a temporary directory.
  - The CLOSE wrapper title says tmux-session residue.

### Round 2b r12, continued (review B of 8d45c6b4 passed it)

Review B of `8d45c6b4` returned SOURCE_PASS, and its transcript is filed. Review A held that commit, so
it is not admitted. r12 also takes review B's should-fixes:
- **The tmux gate uses Core's own rule** for a socket a session may be created on
  (server_socket_probe.go observeNamedSocket). Either the path is absent, and tmux answers "error
  connecting to … (No such file or directory)". Or it is this user's unix socket, not a symlink, that
  no server answers ("no server running on …").
  - Anything else stops: a regular file at the path, an unknown answer, or a running server.
  - The passing state is logged.
  - The test adds the regular-file case.
  - Tonight's read-only run of both gates: "stale city socket, no server" and "no process names the
    Core worktree".
- **A worktree-process gate in PREFLIGHT and RESUME.** CLOSE refuses on a process of this user whose
  argv names the Core worktree, or whose cwd is inside it, and never signals one. Both wrappers now
  stop on such a process before their step. The test runs the exact gate text against a real process
  with its cwd inside, then one naming the path in argv.
- **WATCH runs ADMIT's directory check.** It applies the base `directory_preservation`, which ADMIT's
  preservation applies. It first makes the one alignment the route chain makes for STAGE's reload:
  the routes.jsonl inode, and `.beads` mtime and ctime. This covers the full metadata of every city
  child, the provisioning inventory, and the runtime child names and identities. It is recorded as
  `directories_pass_admission_check`. The test uses the real base function.
- **The singleton proof** also pins the actionable-work collector that feeds the resume tier. It lists
  in_progress work by status, and keeps it by assignee only.
- **Wording.** **Erratum** to the r11 bullet "PREFLIGHT, before anything is consumed": RECONCILE and
  BIND have written their Beads by then, so "before STAGE" is accurate.

### Round 2b r13 (epoch rebind after the 2026-09-24 reboot)

r12 (`f8c4dde9`) had two SOURCE_PASS reviews, both filed. RECONCILE and BIND passed on 2026-09-23 at
21:49Z (ga-y49e blocked; ga-4z38 bound, attempt requested). The host then rebooted before FRESHEN (up
2026-09-24 09:16 CEST), so nothing was staged, routed or launched. r12 is bound to the old host epoch,
so every job from OBSERVE on would refuse on boot drift. RECONCILE and BIND stay valid.
- **Post-reboot state, read-only.**
  - The city and all four rigs are suspended, 0 agents are running, and there is no city tmux socket.
  - The same gc binary (69d00186) runs as the supervisor: `.local/bin/gc` is a symlink to
    `gascity/bin/gc`.
  - The job runner restarted on its reviewed source 0c493db2.
  - The round 2a admission forecast (`proof/admission-forecast.py`, all but the host block) still
    shows zero differences from P6. Providers are equal, directories are clean, and all five route
    stores are captured.
- **The new epoch.** Observed from the supervisor's own PID namespace (pid:[4026532223], shared with
  init):
  - boot 3f1f4534;
  - core `gascity-supervisor-home-42adab5d.service` PID 2331, start 39708112;
  - signer PID 2310, start 39660502;
  - controller PID 2331.
  - The broker (`gas-city-privileged-provision.service`) is socket-activated and **inactive** in this
    boot. Nothing in the window uses it (only the epoch check reads its unit), so its epoch is the
    inactive one, PID 0 and start 0. Waking it would need a signed, sequenced envelope. Any activation
    during the window refuses as epoch drift, like any other.
- **`generators/make_epoch_r13.py`.** The reboot also cleared /tmp, which held the reviewed upstream
  sources that the round 1 and 2 generators read. So r13 derives from the r12 blobs in git instead.
  - It changes the six old-epoch sites, each count-asserted: in window-base-r11.py the host() boot and
    service epochs, and the controller PID in the suspension status and the reload trace; the reload
    trace in window-r11.py; and the reload event in route-chain-r1.py.
  - It then propagates each changed file's digest into every .py and .sh pin, to a fixed point. It
    leaves README.md and the historical generators alone.
  - Every other file keeps its r12 bytes.
- **Tests.**
  - `EpochRebind` proves that every package file is its r12 blob, or the epoch rebind of it, or one of
    five named hand-edited r13 files.
  - It proves that the only lines changed in the three executors are old-epoch or digest lines.
  - The r1 and r2 regeneration tests now prove r12 provenance against the r12 blobs, and skip while
    their /tmp upstream is gone.
- **`proof/worker-env-proof.py`** takes the supervisor identity from the rebound host() core epoch,
  and requires the core unit to report the same MainPID and start live. It passes.
- **Cleanup.** My own test residue was moved out of /var/tmp before any window job:
  - a fake CLOSE root;
  - a fake release root;
  - a drain marker for a fake session ci-1.

  The r9 mutation check had written them by running older job copies that hardcoded /var/tmp. They
  are kept in `~/.local/share/gas-city-staging/ga-4z38-window/test-residue-20260923`. The drain
  marker would otherwise have made CLOSE skip its drain.
- **The window runs from FRESHEN on,** with the same job order and roots. RECONCILE and BIND are not
  repeated.

### Round 2b r13, continued (after both 7d98c05d reviews held)

Both reviews of `7d98c05d` held, and both transcripts are filed.
- **ROUTE would have refused on BIND provenance.** Digest propagation had re-pinned ROUTE's `BIND_SHA`.
  BIND ran at r12 and recorded the r12 `bind-task-r3.py` digest (591cf9b5) in its root, and ROUTE
  requires that value exactly.
  - The generator now keeps this one provenance pin at its r12 value (`PROVENANCE`).
  - A test pins it to the r12 blob, and another reads the live BIND record and compares it.
  - The r13 `bind-task-r3.py` and `BIND.sh` bytes are never executed, since BIND is not repeated.
  - RECONCILE's root is not checked by digest anywhere.
- **OBSERVE and PREFLIGHT would have refused with "accepted baseline drift".** `snapshot()` compared the
  live host block with the P6 host block, which was recorded on the old boot.
  - A bounded disposition, `approved_epoch_image()`, replaces the P6 host block with the live one. It
    does so only after `host()` has required the rebound epoch, and only when both blocks have exactly
    the same shape.
  - Pins, cache and protected trees stay compared exactly as before.
  - A test covers the replacement and the shape refusal.
  - The r13 admission forecast had reused P6's host block, so it never tested this. **Erratum:** its
    "zero differences" covers everything except the host block.
- **The generator never writes the hand-edited files.** One r13 run had rewritten them to their r12
  bytes before the commit, and they were written back from the r13 commit object.
- **Errata to the Jobs text.** "All jobs run at one reviewed commit" no longer holds: RECONCILE and
  BIND ran at `f8c4dde9`, and every later job runs at the r13 commit. The "Read-only forecasts,
  2026-09-23" block below predates the reboot.
- **The broker.** Something outside the window could connect to
  `gas-city-privileged-provision.socket` and start the broker. That would refuse the next epoch check
  as broker drift: before STAGE with nothing consumed, after STAGE with the usual CONTAIN, HOLD and
  CLOSE containment. Nothing on the host is scheduled to use it.

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
3. `FRESHEN-1..3.sh`: one slot per try, until it passes. The ~22-hour group passes its 24-hour mark around
   19:30Z, which is 21:30 CEST. PREFLIGHT must follow within 45 minutes.
4. `OBSERVE.sh`.
5. `PREFLIGHT.sh`: T0, the start of the four-hour cache-atime window.
6. `STAGE.sh`.
7. `ROUTE.sh`.
8. A `WATCH` slot (the zero-pane baseline), then `RESUME.sh`.
9. In-window, with the remaining `WATCH-1..8.sh`, one slot per observation (none between SIGNING_RELEASE
   and SIGNED_CANDIDATE_READY):
   1. Observe one session, active, with its claim and its pane under `tmux -L city`.
   2. Startup review.
   3. `SOURCE-RELEASE-1.sh`, or the next slot (at least 100 minutes left).
   4. Candidate review.
   5. `SIGNING-RELEASE-1.sh`, or the next slot (at least 85 minutes left).
   6. The worker's managed signature.
10. `CONTAIN-1.sh` (or `CONTAIN-2.sh` after a refusal before any intent); if the lifecycle is stranded,
    `HOLD-1.sh` (or `HOLD-2.sh`) instead, then `CLOSE`, and the window stops before ADMIT.
11. `CLOSE-1.sh`, or the next slot, then a `WATCH` slot.
12. `ADMIT.sh`: a passing CLOSE, and at least 40 minutes left.
13. `RESTORE.sh`: at least 25 minutes left.
14. `TERMINAL.sh`: at least 8 minutes left.
15. Delivery of the signed branch.

**Deadline.** At T0 plus 2 h 45 min, the coordinator contains regardless of the worker's progress.

## Round 2b r14: the rebuilt inspector and a fresh integrity root

On 2026-09-24 at r13 (`28693e8c`), FRESHEN-1 passed at 20:27:32Z and OBSERVE refused at 20:28:45Z with
"manifest bytes drift". The observers ran the 09-20 inspector
(`/var/tmp/ga-y49e-platform-inspector-20260920-r1`, binary `77685c66`), whose Go entrypoint compiles in
the pre-M5 manifest pin `a6324753`. M5 legitimately changed the live manifest to `2d7eadce` on 2026-09-23,
and the script rebinds could not reach a compiled constant. Preservation held; nothing was changed. The
09-20 builder lived in `/tmp` and was lost in the 09-24 reboot.

- **Builder** (commit `b780161f`, two reviews plus two job reviews): `inspector/inspector-build-r1.py`
  repeats the recorded 09-20 steps offline (Core `796d9a7a`, tree `f2c120a5`, Go `182d1dc9`, the same
  environment) with `inspector/platform-inspect-main.go`, identical to the 09-20 entrypoint except the pin
  (`2d7eadce`). Job `ga-4z38-inspector-build` (`operator/INSPECTOR-BUILD.sh`) passed at 20:58:21Z:
  binary `b8ebcde3`, `build-result.json` `39bfcea5`, in `/var/tmp/ga-4z38-platform-inspector-20260924-r1`.
  It installs and runs nothing it builds.
- **Rebind** (`generators/make_epoch_r14.py`, from the r13 blobs): both observers use the new build (path,
  binary, build-result and entrypoint digests); `window-r11.py` pins the new binary; the integrity root is
  `/var/tmp/ga-4z38-integrity-20260924-r2` everywhere, because OBSERVE created the r13 one. Digests propagate
  to a fixed point as in r13, and ROUTE keeps the BIND digest recorded at r12.
- **Jobs.** BIND, RECONCILE and INSPECTOR-BUILD have run and are not part of the r14 job plan; the r14
  reviews name every other wrapper. The window restarts at FRESHEN-1.

## Quiet window

From RECONCILE until TERMINAL has passed, the ga-e0t1 worktree stays clean at the package commit.
Records go to Bead notes, always with `GIT_OPTIONAL_LOCKS=0`, and to staging. Between BIND and ROUTE,
no notes go to ga-4z38. Between PREFLIGHT and STAGE, no Bead notes go anywhere. A plain gc call changes the pack-cache `.git` mtime; that was verified
2026-09-23.
