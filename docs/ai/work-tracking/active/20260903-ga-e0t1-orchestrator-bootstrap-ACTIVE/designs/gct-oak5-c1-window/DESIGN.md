# gct-oak5 C1 window — design (d4)

C1 is the first segment of the gct-oak5 handover (accepted plan `designs/gct-oak5-handover/PLAN.md`, r18). It routes the
open step **gct-9s1c** to the Template Claude candidate lane `gas-city-template/gc.implementation-worker` in the new
handover worktree. This document fixes *what* the window package does before it is generated. d2 answered the d1
reviews of `32e95862`, d3 answered the d2 reviews of `9b8f22ad`, and d4 answers the d3 reviews of `cc51beed` (A and B HOLD); see §9 to §11.

## 1. Source and method

- **Source package:** the reviewed gct-e8ex window at `1df3d47e` (s5), the last Template window that ran live (the
  gct-mbg6 codex window, TERMINAL PASS 2026-09-27 10:03 CEST (08:03Z)). It is the ga-3oa7 Claude candidate window
  retargeted to the Template rig, with the later hardening (route survey retries, the never-resumed CLOSE, the
  stranded-lifecycle admission).
- **Method:** `generators/make_successor.py` reads the source files from git at `1df3d47e`, applies asserted
  replacements only (each with an exact count), adds the new scripts of §6 as new files, and writes the package.
  `test_successor.py` proves the package is exactly the generator output.

## 2. Identity, worktree and lane

| Item | gct-e8ex (s5) | C1 |
| --- | --- | --- |
| Task | `gct-mbg6`, description `c66bab3c…` | `gct-9s1c`, description `8a67e132…` (split-r2 `record.json`; the test binds the description to that record instead of the gct-e8ex `HOLDERS`/`SPLIT_COMMIT`) |
| Target | `gas-city-template/codex` | `gas-city-template/gc.implementation-worker` |
| Worktree | `gas-city-template-worktrees/gct-mbg6` | `gas-city-template-candidate-worktrees/gct-oak5` |
| Branch, BASE | `codex/gct-mbg6-…` at `cfd353f3` | `codex/gct-oak5-handover-proof` at `3474abfa` |
| Admin | `.git/worktrees/gct-mbg6` | `.git/worktrees/gct-oak5` |
| Output roots | `/var/tmp/gct-mbg6-*` | `/var/tmp/gct-oak5-c1-*-20260927-r1` |

- **Route targets and identities (queue audit, plan rule 5):** the qualified name `gas-city-template/gc.implementation-worker`,
  the pool name `gc.implementation-worker`, the alias `gas-city-template/gc.implementation-worker-1`, and the session
  names Core derives: `internal/agent/session_name.go:11-14, 53-59` sanitises `.` to `__`, so the forms are
  `gc__implementation-worker-*` and `gas-city-template--gc__implementation-worker-*`. The prefix
  `gc__implementation-worker-` is shared with other rigs' pool sessions; a match on a row of another rig fails closed.
  The audit matches every route target on `gc.routed_to`, the workflow `gc.run_target` form, and every identity on
  the assignee, over the Template rig store and the city store (the lane's hook store list), as
  `split/apply_split.py` does, with every historic session name and id of both lane templates from the city store
  added to the identity set. It runs **before** the sling (the eligible set must be empty) and after it (exactly C1).
  PREP runs the same audit as a dry run and records it, so a shared-prefix match on another rig's row is seen before
  the window, not at ROUTE.
- **Candidate root:** holds exactly this worktree (plan rule 6). WORKTREE requires it empty before the add and
  holding exactly `gct-oak5` after; ROUTE, RESUME and CLOSE run the rule 6 lstat audit.
- **BIND** stamps exactly two keys: `gc.work_dir` = `/home/loucmane/gas-city-template-candidate-worktrees/gct-oak5` and
  `gc.check_path` = `…/954ed149…/gascity/assets/scripts/checks/build-artifact-valid.sh` (sha `71f17450`, the P13
  receipt's check path). The Claude lane is in the receipt, so Core's start preflight requires the stamp. Before BIND
  the step must have no notes, no assignee and no metadata.
- **No info/exclude check:** the Claude skill links are RUNTIME entries admitted by the image tool.

## 3. PREP

- **Overlay:** the one unsuspended agent is `gas-city-template/gc.implementation-worker`, bound to the handover worktree,
  sessions 0..1. Every other city and Template agent is suspended, and PREP asserts it by name for
  `gas-city-template/codex`, `watch-officer` and the Template `orchestrator`. Every order except `nudge-on-route` is
  skipped. The overlay digest is derived read-only by the generated `build_overlay` from the live city.toml
  `bdcec254` and pinned at s2.
- **Target assertions:** provider `claude-template-candidate`; not suspended at the agent level (its patch has no
  `suspended`, only the rig suspension holds it); `OptionDefaults` exactly `{model: opus-5-5, permission_mode:
  full-auto, managed_worktree_access: managed-7d0dfd6c7f3b4e62}`; `work_dir_roots` the candidate root; max 1.
- **Provider options:** `claude-template-candidate` (`managed/rig-permissions.toml:131-174`, base `provider:claude`,
  `options_schema_merge = "by_key"`) is not narrowed. The lane command `bin/gct-claude-template-candidate-worker` runs
  `lib/gct_claude_template_candidate_worker.py` (`:109-125, 151-179, 212-224`: the candidate config, a linked worktree
  directly under the candidate root), which reuses the boundary `lib/gct_claude_signing_worker.py:236-324`: only the
  exact model, effort and permission pairs, the one control policy and the one directory grant are accepted. Work-Bead
  `opt_*` values pass Core's ga-6umo filter only for benign `model`/`effort` choices (`session_reconciler.go:5550-5580`,
  `launch_guard.go`), and any other value fails the launch. Any `opt_*` or `template_override*` key on a step, holder
  or the root refuses at CLOSE.
- **Also asserted at PREP:** `gc mcp list --agent gas-city-template/gc.implementation-worker` reports no projected MCP
  servers; `daemon.auto_reap_closed_bead_worktrees` is unset; no custom `sling_query` and the default
  `session_template` (the probe's preconditions, plan "Preconditions, from the inventory").

## 4. Rebase onto the current baseline

Each asserted with its count in the generator:
- city.toml `bdcec254` (A2), receipt `7185414e` and revision `a61666b3` (P13);
- the P13 input draft (`/var/tmp/gct-oak5-p13-input-20260927/receipt.input.draft.json`), the P13 provider pins
  (`/var/tmp/gct-oak5-p13-adoption-20260927/after.json.provider-pins`), the P13 witness `typed-support.json` (`c284a9f4`);
- the M12 inspector (`/var/tmp/gct-oak5-platform-inspector-m12-20260927`, binary `0da1ff14`) and manifest `114b4a00`;
- the compose diagnostic: the P12 Template candidate compose (`/var/tmp/gct-oak5-p12-template-compose-diagnostic-20260927`);
- the preflight diagnostic stays the P11 one (`/var/tmp/ga-bebv-p11-preflight-diagnostic-20260927`): it was built from
  Core `f45a6262`, which is still deployed, and P12/P13 built none;
- the controller epoch is unchanged (pid 2800348), so the ga-bebv process record stays;
- **accepted image:** the P13 adoption `after.json`, taken at about 14:11 CEST (12:11Z), before the probe runs, the
  split and the anchor. It holds no Bead store. The coordinator's notes since then move only the pack-cache `.git`
  times, which is the one-field coordinator-cache disposition, with `CACHE_PREV_NS` from that record. It needs the
  **operator's approval for this window** at s2.

## 5. Chains

1. **Common snapshot:** `common-snapshot-r1.py before` right after WORKTREE; C1's CLOSE takes `after`. C1 admits **no
   change** at all, which is stricter than the plan's stat-only index rule and fails closed (probe run 2 left the index
   identical; the claim's git is `rev-parse --abbrev-ref HEAD`, `cmd_hook_claim.go:1069-1081`, which does not touch the
   index). WORKTREE waits past the checkout's last timestamp second, refreshes the new index once with hardened git,
   and requires a second refresh to leave it byte-identical, all before `before`. No racily clean entry then remains
   for a later lock-taking git to rewrite. A false refusal here stops the handover and is reported; it is not retried.
   Git calls the reviewed ROUTE pieces make in the worktree (verify_linked, `rev-parse`, the hardened
   `status --porcelain --ignored`) run with no optional locks, before any worker session, and are not relied on for
   content; C2 does not inherit them (its route gate uses the image tool only).
2. **Store chain:** the comparison is the full Template store plus the fixed projection of every other store (rows
   routed to, assigned to, or `gc.run_target` of either lane's targets or identities, and every session Bead of either
   lane template), with every snapshot keeping the raw rows of every store (plan r9).
   - **BIND-before** must equal `anchor-r1` under that comparison, apart from between-window ledger entries (each with
     its pre-image and field delta). None is expected: until C1's TERMINAL every review verdict is recorded on
     ga-e0t1 (the Operations store, outside the chained scope), never on gct-oak5. The package asserts the ledger is
     empty.
   - **Within the window** (BIND-before to CLOSE-after), the only admitted changes are (plan rule 5):
     - on C1: BIND's two keys; ROUTE's `gc.routed_to`; the claim's assignee, status and `gc.session_id`,
       `gc.session_name` and `gc.work_branch` (= `codex/gct-oak5-handover-proof`); the close fields `closed_at`,
       `updated_at` and `close_reason`; the worker's appended notes; the one coordinator `PROBE DONE`/`PROBE SKIPPED`
       note and the probe's same-value `gc.routed_to` write; Core's progress-stall attention set on C1 exactly as
       pinned (the `needs/operator` label, the `gc.failure_*` literals, the recomputed signature, the controller error);
       `updated_at` on every admitted change;
     - in the city store: exactly one new session Bead for the lane (metadata keys within the 96-key union, identity
       values pinned, the drain-ack end state) and at most one new nudge row for it (`gc:nudge`, `agent:` the lane).
       No other row in the **projection** may change. Order-tracking rows written by the order runs below are outside the
       projection; the raw exports keep them. The inventory pins no other bookkeeping row, so any other write, including
       one a controller poke might cause, refuses (fail closed);
     - nothing else; any `opt_*`/`template_override*` key refuses.
   - **CLOSE-after** is taken inside TERMINAL (§6.7), once two identical snapshots 5 minutes apart exist under the
     chained comparison (the Template store in full, the other stores by projection). Raw city exports are kept, not
     compared, because the order-tracking retention and nudge-mail watchdogs can change them while suspended
     (`order_dispatch.go:46-55, 96-99`).
3. **Every gate** (BIND, ROUTE, CLOSE, TERMINAL) checks `gc order history`: no run since the anchor of any order
   other than `nudge-on-route`, and runs of that one only inside this window. It fires on every `bead.updated` event
   (`nudge-on-route.toml`, `internal/orders/triggers.go:370-401`), so it runs many times in a normal window; the gate
   pins its **effect** instead: at most one nudge row for the lane in the city store and no other change in the chained
   scope (its dedup, `nudge-on-route.sh:130-141`, keeps the probe's same-value re-route from nudging again). It also checks that no chained-scope row has the route-recovery shape
   (open, unassigned, kind-less, `gc.run_target` without a route).

## 6. New and changed window steps

1. **WORKTREE** (the gct-mbg6 `worktree-task-r1`, retargeted): umask 0022; the pre-add checks (drivers `a3cf4a1c`, no
   attributes file, `.gitattributes` blob `84c48ec4`, no include directive, no gitlink or `.gitmodules`); the candidate
   root empty; `git worktree add -b codex/gct-oak5-handover-proof <worktree> 3474abfa`; an empty, operator-owned,
   single-link `config.worktree` (0644) in the new admin directory; a bare GitHub clone into
   `~/.local/share/gas-city-staging/gct-oak5-handover/base.git` verified to contain `3474abfa^{commit}`, with no
   `objects/info/alternates` and no replace refs; **image 0** (`image_tool.py export --runtime none`, which must pass
   with empty entries, deleted, ignored and runtime); then `common-snapshot-r1.py before`.
2. **BIND:** the two stamps (§2), after **BIND-before** (§5.2) and the gate checks (§5.3).
3. **ROUTE:** the pre-sling queue audit (eligible set empty), the rule 6 audit, then exactly
   `gc sling gas-city-template/gc.implementation-worker gct-9s1c --no-formula --no-convoy --json` once, then the
   post-sling audit (exactly C1).
4. **RESUME:** the rule 6 audit immediately before.
5. **WATCH-LOOP (replaces the WATCH-n observers).** One job, started right after RESUME, the only mutating observer.
   - **Every tick** (15 seconds) records: C1's status, assignee, `gc.routed_to` and claim keys; the non-current steps,
     the holders and the root; the lane session Beads; the census. The census is exact cgroup membership (the
     controller cgroup and the tmux-spawn pane scopes), never a `/proc` scan. Every gc and bd call of every tick runs in
     the window's guarded environment (`GIT_OPTIONAL_LOCKS=0`, `BD_DISABLE_METRICS=1`, `LANG=C`, under the cache
     disposition).
     - **The lane provider process** is the one process in the lane's pane scope whose `/proc/<pid>/exe` resolves to
       the realpath of `/home/loucmane/gascity/bin/claude`, with that file's sha256 pinned at s1, and whose parent is
       outside the provider's own tree (the wrapper's exec). Its argv must equal the wrapper-validated argv pinned at
       s1 (the directory grant, `--permission-mode dontAsk`, `--effort max`, `--model claude-opus-5-5`,
       `--setting-sources ''`, the policy file).
     - **Every other process in the lane's pane scope** must be a descendant of the provider process (the worker's
       tools and any subprocess the provider starts, including further `claude` executables). A process in the scope
       that is not a descendant is a trigger.
     - **Zero** provider processes while the session Bead is open and C1 is claimed and not closed, or **more than
       one**, is a trigger.
   - **Containment triggers** (inline CONTAIN, then exit): any change to a non-current Bead, `gct-oak5` or a holder; a
     C1 regression (status back to open, or the assignee cleared or moved: orphan release or re-assignment); a second
     lane session Bead at any time, concurrent or sequential; a second pane scope; a provider argv other than the
     pinned one; drift in the probe (below); every bound below.
   - **Bounds:**
     - every gc, bd and census call has a timeout: 60 s, and 120 s for the sling. An expiry is a containment trigger;
     - a tick over 60 s is recorded, and three in a row are a trigger;
     - no claim within 20 minutes of RESUME (a silent start) is a trigger;
     - **the loop deadline** comes from the window `before.json` clock that PREFLIGHT starts (`budget-r11.py`): its
       four-hour bound minus ADMIT's reserve, minus CLOSE's budget (the 10-minute session wait plus the image and
       snapshot exports, 30 minutes), minus a 15-minute margin. The TERMINAL budget grows from 8 to 20 minutes for the
       settle pair and its exports, and ADMIT's reserve from 60 to 75 minutes to cover RESTORE's 45 and the new
       TERMINAL. The deadline is therefore PREFLIGHT + 4 h − 75 − 30 − 15 min = **PREFLIGHT + 2 h 00 min**, checked by
       the budget gate at WATCH-LOOP's start. A test pins the arithmetic;
     - an operator stop file `~/.local/share/gas-city-staging/gct-oak5-handover/STOP-C1` is a trigger.
     Every exception in the loop, and SIGTERM (a handler turns it into an exception), runs the containment in a
     `finally`. A SIGKILL skips it; the runner itself sets no time limit (`TimeoutStartSec=infinity`). The `finally`
     never starts a containment when any lifecycle record already exists; `lifecycle()` also refuses on existing
     outputs (`window-base-r11.py:644-655`).
   - **Directory atimes:** WATCH-LOOP runs none of WATCH's early directory checks, so no relatime refresh can trigger
     it.
   - **Second-route negative, exactly once.** Two write-once records live in the WATCH-LOOP root and are never
     rewritten; a record that exists blocks its step for good.
     - `probe-decision.json` is written **before** either branch, naming it: `sling` or `skipped`.
     - `probe-note.json` is written **before** the one `bd update`.
     - The 15-minute bound starts at the **first tick that observes the claim**. The worker's wait (20 minutes of ~60 s
       polls) starts only after its `C1 DONE` note, which comes after the claim, so a SKIPPED note written at claim + 15
       minutes lands inside the wait, and the worker sees it within one poll.
     - **Sling branch:** on the first tick where C1 is `in_progress`, its assignee equals its `gc.session_name` and no
       containment is under way, write the decision `sling`. Then issue exactly
       `gc sling gas-city-template/gc.implementation-worker gct-9s1c --no-formula --no-convoy --json` in the window's
       guarded gc environment (`GIT_OPTIONAL_LOCKS=0`, `BD_DISABLE_METRICS=1`, `LANG=C`, under the window's cache
       disposition), save its exit code, stdout and stderr, and read C1 at once. Core's dispatch gate runs its hardened
       `InspectIntegrity` git (no optional locks, fsmonitor off, no hooks) against the pinned repositories while the
       worker is live; that is the same exposure as ROUTE, and it is stated.
     - **Outcomes, a closed set:**
       - **Proven, in two stages.** The **note predicate**, checked right after the sling: exit 0; the JSON parses with
         `"routed": true` and the "routed … but assigned to …" warning; the post-sling read shows C1 `in_progress`
         with the same assignee and `gc.routed_to`, `gc.work_dir` and `gc.check_path` unchanged; no new session Bead.
         It is recorded in `probe-outcome.json`, and then the note `PROBE DONE gct-oak5 C1` is written. The **final
         classification** at CLOSE adds: one session and one cgroup for the rest of the window, from WATCH-LOOP's
         census records; and, as probe evidence only (no gate relies on event rows, plan rule 5), a `gc events` read for
         the window showing no `ManagedProductDispatchRefused` event and no session start or refusal event after the
         poke. A failed events read leaves the negative **unproven**.
       - **Race (unproven, not drift):** the post-sling read shows C1 closed, with exit 0 and the warning shape. No note
         is written, since C1 is closed and the worker has gone on.
       - **Drift:** everything else, meaning a non-zero exit, a timeout, a dispatch-gate refusal, JSON that does not
         parse, `routed: false`, a missing warning, the idempotent shape while C1 is `in_progress` and assigned, an
         assignee cleared, moved or equal to the target identity, a changed `gc.routed_to`, `gc.work_dir` or
         `gc.check_path`, or a new session Bead. Drift runs the containment and stops the window, with no note. The
         JSON field names of the warning and idempotent shapes are pinned at s1 from `cmd/gc/cmd_sling.go:1106-1176`.
     - **Skipped branch:** if the preconditions have not held by the bound and C1 is still `in_progress`, write the
       decision `skipped`, then the note `PROBE SKIPPED gct-oak5 C1`.
     - **A decision without an outcome** (`probe-decision.json` names `sling` but `probe-outcome.json` is missing,
       because WATCH-LOOP died during the sling or its read) is **drift**: WATCH-LOOP-2 and CLOSE read it, no note is
       ever written, and the window stops at its containment.
     - **Neither:** if C1 closes before the decision, there is no decision, sling or note, and the negative is recorded
       as unproven. A PROBE text on C1 that WATCH-LOOP did not write is recorded as worker self-release.
   - **Normal end (after C1 closes).** On the first tick that sees C1 closed, WATCH-LOOP polls the session Bead and the
     census every 15 seconds. When the session Bead is **closed** in a drain-ack end state (`drained` or `dead-runtime`
     with `state_reason=drain-ack-stop-pending`) **and** the census shows no lane pane scope and no lane process, it
     runs the reviewed containment (below) on a quiet city: no live worker exists, so the lifecycle's status check
     sees none. This path is reachable for this provider: the ga-3oa7 Claude-lane session `ci-yi6m4` ended `drained`
     with `drain-ack-stop-pending`, and ga-3oa7's CONTAIN ran with zero running rows
     (`/var/tmp/ga-3oa7-window-20260926-r1/city-suspend-status-0-phase.json`). If Core finds the provider already dead
     before it processes the ack, its direct-finalize branch (`session_reconciler.go:2018-2028, 2404-2421`) closes the
     Bead without the stop-pending mark; that reads as the abnormal end and fails closed.
   - **Abnormal end.** No drain-ack mark 4 minutes after C1's `closed_at` (parsed with its explicit zone and bracketed
     between the last tick that saw C1 open and the first that saw it closed, else the last open tick), or the mark
     without a closed session Bead and an empty census 8 minutes after `closed_at`, or any trigger above: it runs the
     containment with the worker possibly alive, and the segment is failed. A close whose reason starts with
     `C1 STOP` is also a failed segment, with the normal end.
   - **The containment** is exactly the reviewed CONTAIN pair, `window-r11.py lifecycle city-suspend`, then
     `window-r11.py lifecycle rig-suspend`, run through `source-launch.py` with their bound digests and CONTAIN-1.sh's
     preconditions (`operator/CONTAIN-1.sh:40-45`). Each runs with the window root as its phase cwd
     (`suspension-lineage.py:77-81`); WATCH-LOOP's own records live in its own root, outside the window root
     (`window-base-r11.py:693-701`).
   - **The status check fix** (gct-e8ex README s5 follow-up). `suspension_status_matches`
     (`window-base-r11.py:570-591`) is retargeted and gains a census input, sampled in the same observation as the
     `gc status --json` call. Over the fields the agent rows carry (`name`, `qualified_name`, `scope`, `running`,
     `suspended`, `pool`; `cmd_citystatus.go:62-69`), the running rows must be a subset of:
     - the canonical lane row, `qualified_name == 'gas-city-template/gc.implementation-worker'`;
     - at most one session row whose `name` and `qualified_name` both equal the census's one lane session name.

     `summary.running_agents` must equal the number of running rows, `summary.active_sessions` must be at most 1, and the
     census must show at most one lane pane scope. Anything else refuses. Tests pin it with the gct-mbg6 codex shape
     (`/var/tmp/gct-mbg6-window-20260926-r2/city-suspend-status-0-phase.json`: the rows `codex-ci-sg37g` and
     `gas-city-template/codex`, 2 running, 1 active session), with this lane's shape and the zero-row shape of ga-3oa7,
     and with two session rows, which refuses. The s5 gct-mbg6 stranded-lifecycle
     admission, pinned to gct-mbg6's records by digest, is **dropped**. The s3 never-resumed CLOSE branch stays: it
     applies if the window stops before RESUME.
   - **Pre-reviewed fallback slots** (the runner never reruns a job at a commit), chosen by the records present, in
     this order:
     1. **HOLD-1** whenever any lifecycle record in the window root is incomplete (an intent without its event, or a
        started phase without its phase record): the reviewed rig-level hold, extended to recognise a failed
        WATCH-LOOP, WATCH-LOOP-2 or CONTAIN-2 by its records (`hold-r11.py:41-59`);
     2. **WATCH-LOOP-2**, hold-only, if no lifecycle record exists and C1 is not yet closed, or C1 is closed but the
        session is not: no probe, decision or note. It runs only the normal or abnormal end, with the original
        WATCH-LOOP's absolute bounds (the silent-start time, the loop deadline and the stop file) and WATCH-LOOP's last
        recorded open tick for the `closed_at` bracket;
     3. **CONTAIN-2**, the plain containment, if no lifecycle record exists, C1 is closed and the session Bead is closed
        in a drain-ack end state with an empty census. CONTAIN-2 checks that precondition itself and refuses otherwise;
     4. **TEARDOWN-1**, if a lane process outlives the containment (below).

     A stranded containment for C1 is a standing stop condition: HOLD-1 holds the rig, and the operator is told. There
     is no stranded-lifecycle admission for C1. Dropping the s5 admission means `verified_lifecycle` then refuses, so
     ADMIT, RESTORE and TERMINAL are unreachable, and the overlay and receipt image stay installed until a reviewed
     successor exists.
   - **TEARDOWN-1, the bounded teardown of a lane process that outlives the containment.**
     - Core can leave a stop-pending session open with its provider alive: the async stop's confirm-dead loop gives up
       after 6 s, and the finalizer then re-queues the stop on every tick without closing the Bead
       (`session_reconciler.go:368-378, 733-737`).
     - Separately, the containment does not stop a worker that still holds an `in_progress` claim (the undesired
       drain is skipped on live assigned work, `session_reconciler.go:2046-2065`).
     - In either case TEARDOWN-1 stops the lane's pane scopes through the reviewed cgroup control (the ga-6utp r8 exact
       cgroup membership: the controller cgroup and the tmux-spawn pane scopes), proves zero members after, and records
       a **failed segment**.
     - It runs when CLOSE refuses on a session still open at its bound, or when CLOSE's zero-residue proof finds a lane
       process. CLOSE-2 then runs the rest of CLOSE.
6. **CLOSE:** besides the gct-e8ex CLOSE:
   - **Never pre-empts the drain-ack teardown.** Before any coordinator drain or session close, CLOSE waits up to 10
     minutes for the lane session Bead to close. A session Bead that carries `state_reason=drain-ack-stop-pending` is
     never drained or closed by the coordinator; if it is still open at the bound, CLOSE refuses, and TEARDOWN-1 then
     CLOSE-2 follow. On the drift or trigger path, where the worker may still hold an `in_progress` claim, CLOSE uses
     the inherited `gc runtime drain` and `gc session close`, and TEARDOWN-1 if a process survives. A session the
     coordinator had to close is recorded as a failed segment;
   - the rule 6 audit; the probe target empty; the A2 audit that no default-choice codex route targets the candidate
     root; `common-snapshot-r1.py after` (no change);
   - **image 1:** `image_tool.py export --runtime claude` (after the session Bead's end state and a zero-process
     census), then `compare --step C1 --prev image0 --next image1`;
   - **the image 1 record** (`image1-record.json`): the image tool's `image.json` digest; the Bead-state part the plan
     requires (for `gct-oak5`, C1, X, C2 and H2: status, assignee, description digest, notes digest and every metadata
     key; H2 empty); and the common-snapshot `after` digest.
7. **ADMIT, RESTORE, TERMINAL** as in gct-e8ex. **TERMINAL** also:
   - takes the store **CLOSE-after** settle pair (§5.2): two identical snapshots 5 minutes apart, inside TERMINAL's own
     20-minute budget;
   - checks the within-window allowlist and the session Bead end state, so ADMIT's and RESTORE's writes, if any, are
     inside the compared window;
   - checks that the Bead-state part of `image1-record.json` equals the CLOSE-after rows.
8. **H1 (after TERMINAL PASS, its own job):** it runs only if the segment is accepted: C1 closed by its own worker
   with the success close reason, no `C1 STOP` note, the `C1 DONE` note's two digests equal to image 1's, the closed
   row's assignee equal to the claim's `gc.session_name`, and the normal end (§6.5). It is the first between-window
   ledger entry. It writes H1 `gct-893n`'s
   description: the `image_tool.py holder --image image1 --step C1` lines, the `image1-record.json` digest and the C1
   TERMINAL PASS record digest, the TERMINAL record bound to the reviewed TERMINAL executor's digest (as ADMIT binds
   `CLOSE_SHA`). The ledger entry pins H1's pre-image (closed, empty) and the exact field delta. X's route gate requires
   the C1 TERMINAL PASS record, the image 1 record and H1 equal to this entry.

## 7. Tool fixes carried in (image tool r3)

A length-prefixed skill tree digest with modes; `.git` hashed like any name inside skill targets; `verify` pinned to
the image's settings digest; a strictly parsed `packed-refs` fallback for the branch ref; earlier walk and byte bounds;
a positive test for the empty `.claude/.cc-writes/`; tests for every remaining refusal branch; the git-scope and limit
wording (the common `.git/config`, hooks, `info/*` and the admin index are covered by the common snapshot, not the
image); `holder` checking the image's lanes.

## 8. Run order

1. d2 (this document), two reviews.
2. s1: the generated package and image tool r3, two reviews. Jobs: WORKTREE (with image 0 and the common `before`),
   then PREP.
3. s2: PREP pins and, with the operator's cache-disposition approval, `CACHE_PINNED_NS`; two reviews.
4. Window: BIND, OBSERVE, PREFLIGHT, STAGE, ROUTE, RESUME, WATCH-LOOP (probe, normal end, containment), CLOSE
   (image 1), ADMIT, RESTORE, TERMINAL (CLOSE-after), then H1. The fallbacks (HOLD-1, WATCH-LOOP-2, CONTAIN-2,
   TEARDOWN-1, CLOSE-2) are reviewed with the package and run only on the rules in §6.5 and §6.6.

## 9. d2 (answers the d1 reviews of `32e95862`: A and B HOLD)

- **A must_fix 1: no agent-level hold mechanism exists.** The hold is now the reviewed CONTAIN, run inline by the one
  WATCH-LOOP job at the drain-ack mark or the 4-minute bound (§6.5); no new mutation type.
- **A must_fix 2, B should_fix 3: the allowlist.** It now includes the worker's notes, the stall attention set, the
  session bookkeeping and nudge row, `gc.work_branch` and `updated_at` (§5.2).
- **A must_fix 3: identities.** The sanitised session forms, every route target, and a pre-sling audit (§2).
- **A must_fix 4, B must_fix 2 and 3: image 1 and H1.** The image 1 record carries the Bead state and the common
  snapshot digest; H1 is written after TERMINAL PASS as a ledger entry, and X requires C1's TERMINAL PASS (§6.6-8).
- **A must_fix 5: missing gates.** The A2 audit at CLOSE; order history and route-recovery shape at every gate (§5.3).
- **A must_fix 6, B must_fix 1: the probe.** Exactly-once intent record, the guarded environment, the 15-minute bound,
  the proven, race and drift outcomes with the pinned evidence, and the stop on drift (§6.5). The race is detected
  by the post-sling read, since a close keeps the assignee.
- **Should_fix taken:** no admin change admitted in C1 (A 1); the store-chain comparison and ledger (A 2, B 2); the
  ROUTE git calls stated (A 3); the PREP assertions (A 4); one BIND sentence (A 5, B 7); the shared prefix (A 6);
  every rebased binding named (A 7); the `closed_at` rule and the `base.git` verification (A 8, B 5); the wrapper files
  cited (B 1); image 1 after the session end state (B 4); CLOSE-after after TERMINAL (B 6); `gc mcp list --agent` at
  PREP (B 8).

## 10. d3 (answers the d2 reviews of `9b8f22ad`: A and B HOLD)

- **Both must_fix 1: the inline CONTAIN would strand** on the known gct-mbg6 status shape (one worker listed as the
  rig agent and as its session row).
  - In the normal path, WATCH-LOOP now contains only after Core's drain-ack teardown has closed the session Bead and
    the census is empty, so no live worker exists at the status check.
  - `suspension_status_matches` is retargeted and admits the one worker's two rows, with a test.
  - The gct-mbg6 stranded admission is dropped.
  - A stranded containment is a stop condition: HOLD-1 holds the rig, and the operator is told (§6.5).
- **Both must_fix 2: WATCH-LOOP bounds and failure.**
  - There are timeouts on every call and a tick budget.
  - The silent-start bound, the 3-hour loop bound and an operator stop file are added.
  - The containment runs in a `finally`.
  - Three pre-reviewed fallback slots come with the rules for when each runs (§6.5).
- **B must_fix 3: exactly-once.** A write-once decision record comes before either branch, and a write-once note
  record before the `bd update`. The fallback WATCH-LOOP-2 never slings or notes.
- **Both: the probe outcomes are a closed set.** Proven, race, and drift for everything else. Drift contains and stops,
  with no note. No note is written on a race. The JSON shapes are pinned from Core at s1.
- **Both: CLOSE never pre-empts the drain-ack teardown.** It waits for the session Bead to close, and never drains or
  closes a session carrying the stop-pending mark (§6.6).
- **B must_fix 6: the argv trigger.** A lane provider process is defined by cgroup membership and executable. Worker
  children are counted, not argv-checked (§6.5).
- **Should_fix taken:**
  - the H1 acceptance predicate (B 1);
  - the TERMINAL executor binding and the image 1 record equal to the CLOSE-after rows (B 2, A 9);
  - the dispatch gate's git and nudge dedup stated (B 3);
  - the shared-prefix dry run at PREP (B 4, A 6);
  - where the 15-minute bound starts (B 5);
  - the stranded rules (B 6);
  - the rig suspend after the session closes in the normal path, consistent with the plan (A 1);
  - the exact inline invocation (A 2);
  - the added triggers (A 3);
  - no early directory checks (A 4);
  - the named city-store rows (A 5);
  - historic session names and ids (A 6);
  - the index refresh in WORKTREE (A 7);
  - verdicts on ga-e0t1 until TERMINAL (A 8);
  - the settle pair inside TERMINAL (A 9);
  - no note re-issue and `nudge-on-route` at most once (A 10).

## 11. d4 (answers the d3 reviews of `cc51beed`: A and B HOLD)

- **Both must_fix: the time bound.** The loop deadline is derived from PREFLIGHT's clock: PREFLIGHT + 2 h 00 min. It
  reserves CLOSE's 30 minutes, ADMIT's reserve (raised to 75 minutes) and a 15-minute margin. TERMINAL's budget is
  20 minutes for the settle pair, and a test pins the arithmetic.
- **B must_fix 1: order history.** `nudge-on-route` may run any number of times inside the window. Its effect is pinned
  instead: at most one nudge row and nothing else in the chained scope. The city-store rule applies to the projection,
  and the settle pair uses the chained comparison.
- **A must_fix 2: the status check.** It is an exact predicate over the real `gc status --json` fields plus a census
  sampled in the same observation. Tests pin the gct-mbg6 codex shape, this lane's shape, ga-3oa7's zero-row shape
  and a two-session refusal.
- **A must_fix 3: a stuck teardown.** TEARDOWN-1 stops the lane's pane scopes through the reviewed cgroup control and
  records a failed segment, for a stuck stop-pending session and for a worker the containment cannot stop. CLOSE-2
  follows.
- **A must_fix 4: lane processes.** The resolved executable and its digest are pinned, exactly one provider process,
  and every other process in the scope must descend from it. Zero or more than one provider process, or a stray
  process, is a trigger.
- **Should_fix taken:**
  - fallbacks chosen by records, HOLD-1 first (A 2, B 1);
  - WATCH-LOOP-2's absolute bounds and last-open-tick bracket (A 2, B 2);
  - the SIGTERM handler, no double containment, and no runner time limit stated (A 2, B 1);
  - the guarded environment on every call (B 3);
  - the provider-process rule (B 4);
  - the index refresh past the checkout second (B 5);
  - CLOSE-after inside TERMINAL (B 6);
  - CLOSE's refusal exit (B 7);
  - `gc events` as probe evidence only (A 1, B 8);
  - a decision without an outcome is drift;
  - the note predicate split from the final classification (A 1);
  - the direct-finalize branch stated (A 3);
  - the s5 consequence stated (A 4);
  - the ga-3oa7 reachability evidence (A 5);
  - the plan wording this design supersedes recorded in plan r19 (B 9).
