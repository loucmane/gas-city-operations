# gct-oak5 C1 window — design (d7)

C1 is the first segment of the gct-oak5 handover (accepted plan `designs/gct-oak5-handover/PLAN.md`, r18). It routes the
open step **gct-9s1c** to the Template Claude candidate lane `gas-city-template/gc.implementation-worker` in the new
handover worktree. This document fixes *what* the window package does before it is generated. d2 answered the d1
reviews of `32e95862`, d3 answered the d2 reviews of `9b8f22ad`, d4 answered the d3 reviews of `cc51beed`, d5 answered the d4 reviews of `e8bbc592`, d6 answered the d5 reviews of `84bfeac4`, and d7 answers the d6 reviews of `7d2d7b84` (A and B HOLD) with code: the next-job rule is `slots/slots.py`, tested in `slots/test_slots.py`; see §9 to §14.

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
- **Every other lane literal** is an asserted replacement, including `window-r11.py`'s RESTORE armed-template literal
  (`window-r11.py:260-262`) and CLOSE's `TEMPLATE` (`close-r11.py:51`).

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
   scope. The nudge row is outside the projection (`INVENTORY.md:72`), so CLOSE and TERMINAL check it **explicitly on
   the raw city exports**: rows labelled `gc:nudge` with `agent:gas-city-template/gc.implementation-worker` created
   after BIND-before number at most one. The dedup (`nudge-on-route.sh:130-150`) records a pair only after a nudge
   succeeds and prunes it after 1 h, so a failed first nudge or more than an hour between C1 updates can produce a
   second row in a well-behaved run; that refuses (fail closed) and is stated. The same holds for the other paths the
   script can take: a nudge to a not-running session takes Core's queue-and-wake path (`cmd_nudge.go:771-778,
   848-858, 887-932`), which writes a row and the session Bead; with no active member the script nudges the pool base
   (`nudge-on-route.sh:64-81`); and the last-seen time is refreshed on every re-observed pair (`nudge-on-route.sh:133-137`),
   so pruning needs an hour without a C1 update inside the lookback. At ROUTE the rig is suspended, so the early runs
   can take the queue path. s1 pins from `cmd_nudge.go:762-845` whether a queued nudge counts as a success for the
   dedup, and tests the count on the gct-mbg6 records (one row observed); if the source allows a second row in a normal
   window, the rule stays fail closed and the refusal is a stated stop, not a gap. It also checks that no chained-scope row has the route-recovery shape
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
     - **The lane's pane scope and session name.** Each tick reads the lane's open session Bead from the city store
       (its `session_name`) and runs `tmux -S /tmp/tmux-1000/city list-panes -a -F '#{session_name} #{pane_pid}'`,
       mapping the lane session's pane pid to its cgroup scope, in the same observation as the census. The operator
       keeps no tmux pane on the city socket during the window (the ga-6utp constraint, `ga-6utp-activation-r10/PLAN.md`
       "operator panes"). Any other pane on that socket is a trigger; tmux servers on other sockets are outside the
       census. The tmux 3.4 answers for a server with no session ("no current target", `close-r11.py:14-20`) and for no
       server read as an empty pane list, not as a failed call; any other non-zero answer is a failed call (a bound).
     - **The controller cgroup** may hold only: the members of the ga-6utp process record (the controller, the dolt
       watchdog and dolt, `ga-6utp-activation-r10/PLAN.md:363, 400-402`); the one city tmux server, identified by
       SO_PEERCRED on `/tmp/tmux-1000/city` (it daemonizes, so it is not a descendant, `PLAN.md:380-385`); and
       descendants of the controller pid 2800348 (the order executions: `nudge-on-route.sh` and its gc and bd calls).
       Every admitted pid is bound to its `/proc/<pid>/stat` start time. A pane process in the controller cgroup (a
       failed scope move, `PLAN.md:377-379, 412-413`) is a trigger.
     - **Stated gap:** a worker can move a process into another cgroup it owns under `user@1000`, which the census does
       not see. That is the accepted semi-trusted worker model (reviewed windows, two-reviewer diffs, CI), not a
       control this window claims.
     - **The startup phase.** From the lane pane's first appearance until the first tick that observes the exec'd
       provider (below), the scope may hold only the pane's initial process chain and the launch wrapper (first
       `/bin/sh` running `bin/gct-claude-template-candidate-worker`, which execs `/usr/bin/python3.12` on
       `lib/gct_claude_template_candidate_worker.py` in the same pid, `bin/gct-claude-template-candidate-worker:13-14`),
       plus at most one `claude … auth status --json` child of the wrapper (`gct_claude_subscription.py:267-283`, 30 s).
       The pane chain's shape is pinned at s1 from Core's tmux launch and the ga-3oa7 evidence; at the first tick that
       sees the pane, WATCH-LOOP records the chain's **pid set**, each pid with its start time, and only those
       (pid, start time) pairs are admitted as the chain for the rest of the window. The startup phase ends at the silent-start bound at the latest.
     - **The lane provider process** is the **wrapper's own pid** after its exec: the pid recorded as the wrapper, once
       its `/proc/<pid>/exe` resolves to the realpath of `/home/loucmane/gascity/bin/claude` (sha256 pinned at s1). The
       `auth status` child is a different pid and never counts as the provider; it is identified by its parent (the
       wrapper pid) and its argv (`gct_claude_subscription.py:268-276`). The provider's argv must equal the
       wrapper-validated argv pinned at s1 (the directory grant, `--permission-mode dontAsk`, `--effort max`,
       `--model claude-opus-5-5`, `--setting-sources ''`, the policy file), with the positional startup prompt and an
       optional `--resume <id>` matched by the boundary's own shape rules (`gct_claude_signing_worker.py:259-269,
       293-297, 322-323`), which s1 reuses as code rather than restating.
     - **After the provider is first observed**, every other process in the lane's pane scope must be a descendant of
       it (the worker's tools and any subprocess it starts, including further `claude` executables), apart from the
       recorded pane-chain pids; a process that is not is a trigger. The provider pid gone while the session Bead is
       open and C1 is claimed and not closed is a trigger.
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
       snapshot exports, 30 minutes), minus a 15-minute margin. The wrapper budgets become: TERMINAL 20 minutes (from 8,
       for the settle pair and its exports); RESTORE 60 (from 45: its worst case, the 20-minute trace wait plus the
       reload, transition and snapshots, about 37 minutes, plus TERMINAL's 20 and a margin; s1 lists each RESTORE
       phase's timeout from `window-r11.py` and the test sums them rather than trusting the estimate); ADMIT 75 (from 60, at
       least RESTORE + 15); CLOSE gains a budget gate of 105 (ADMIT's 75 plus its own 30). The deadline is therefore
       PREFLIGHT + 4 h − 75 − 30 − 15 min = **PREFLIGHT + 2 h 00 min**. WATCH-LOOP computes it itself from the window
       `before.json` `cache_access_clock.start` (CLOCK_BOOTTIME, with the boot-id check of `budget-r11.py`) and refuses
       to start if fewer than 30 minutes of worker time remain before it. A test pins the chain: RESTORE ≥ its worst
       case + TERMINAL, ADMIT ≥ RESTORE + 15, CLOSE ≥ ADMIT + 30, and the deadline sum;
     - an operator stop file `~/.local/share/gas-city-staging/gct-oak5-handover/STOP-C1` is a trigger.
     The abnormal branch (a containment at the deadline, CLOSE's full wait and the gaps between jobs) is covered only by
     the margin. If ADMIT then refuses on its budget, the overlay and receipt image stay installed until a reviewed
     successor exists; that is a stated stop, not a gap.
     Every exception in the loop, and SIGTERM (a handler turns it into an exception), runs the containment in a
     `finally`. The operator stops the loop only with `STOP-C1`, never with `systemctl stop`: the unit's default stop
     timeout SIGKILLs the whole cgroup about 90 s after SIGTERM, and the containment pair can take up to about
     7 minutes (a 120 s phase and a 90 s barrier per action), so a `systemctl stop` normally strands at HOLD-1. The
     runner itself sets no time limit (`TimeoutStartSec=infinity`). The `finally` never starts a containment when any
     **containment record** already exists (a `city-suspend` or `rig-suspend` intent, started, event, failure or
     refused-after record in the window root); `lifecycle()` also refuses on existing outputs and on any failure or
     refused-after record of any action (`window-base-r11.py:644-655`).
     The containment runs at most once per process: an in-process "containment attempted" flag, set before the
     first lifecycle call, stops the `finally` from trying again after a step that refused before its intent. The
     exit status is informational only; the next-job rule never reads it (§6.5 fallback slots). Every watcher writes
     its final observation (`final-observation.json`: C1 closed, session Bead closed in a drain-ack end state, empty
     census, orphan decision) in its own root before it exits.
     **Stated gap:** the runner halts after every job, so between RESUME's end and WATCH-LOOP's first tick the city is
     resumed and the worker can start unwatched for the minutes the coordinator takes to clear and queue. Nothing is
     lost to detection: WATCH-LOOP's first tick checks every session Bead and census member since RESUME, not since
     its own start, and any trigger contains at once.
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
     - at most one session row whose `name` and `qualified_name` both equal the lane session's `session_name`, read
       from its open session Bead in the same observation (as on gct-mbg6: `codex-ci-sg37g`, scope `city`).

     The relaxation applies only to the `city-suspend` and `rig-suspend` actions; the resume actions keep the existing
     check. The health signal set gains exactly the value `gc status` reports with this one worker running, pinned at
     s1 from the gct-mbg6 status record.

     `summary.running_agents` must equal the number of running rows, `summary.active_sessions` must be at most 1, and the
     census must show at most one lane pane scope. Anything else refuses. Tests pin it with the gct-mbg6 codex shape
     (`/var/tmp/gct-mbg6-window-20260926-r2/city-suspend-status-0-phase.json`: the rows `codex-ci-sg37g` and
     `gas-city-template/codex`, 2 running, 1 active session), with this lane's shape and the zero-row shape of ga-3oa7,
     and with two session rows, which refuses. The s5 gct-mbg6 stranded-lifecycle
     admission, pinned to gct-mbg6's records by digest, is **dropped**. The s3 never-resumed CLOSE branch stays: it
     applies if the window stops before RESUME.
   - **Fallback slots: the next-job rule is code.** `slots/slots.py` `select()` is the one rule. The coordinator runs it
     (read-only, no gc, bd or git call) after RESUME and after every WATCH-LOOP, fallback and hold job. Every job's own
     admission is `select()` on its own fresh records equal to its own name, and it refuses before any mutation
     otherwise. Inputs: the window root's lifecycle records per action (absent, complete, incomplete, failed); which
     jobs have a runner done record (used, whatever the exit status); whether a hold passed; and the last watcher's
     final observation (missing reads as not quiet). The rule, first match wins:
     1. a passing hold: **CLOSE**, whose inherited admission accepts it (`close-r11.py:103-105`) and whose teardown
        (drain, session close, residue proof) handles a live worker;
     2. any incomplete or failed record, or a completed-action sequence the permitted order cannot produce: the first
        unused of **HOLD-1, HOLD-2**, else **STOP** (the operator is told);
     3. never resumed, or a completed rig suspend: **CLOSE** (its held predicate);
     4. the rig resumed and not suspended, with the city never resumed (a partial RESUME), already suspended, or at the
        quiet end: **CONTAIN-2** (by events: city-suspend if resumed and absent, rig-suspend if resumed and absent;
        the permitted order allows rig-suspend straight after rig-resume), else a hold;
     5. otherwise a worker may be live: the first unused of **WATCH-LOOP, WATCH-LOOP-2**, else a hold.

     The tests prove over every combination of records, used jobs, hold result and observation that `select()` never
     picks a used job, picks CLOSE only when CLOSE's held predicate holds, stops only after both holds, holds on every
     stranded record, and never leaves a possibly live worker without a watcher or a hold. A model of every job's
     possible effects (each lifecycle step completing, failing, being killed or refusing before its intent; each
     admission refusing) driven from every RESUME outcome ends only at CLOSE or STOP, and no job ever asks to repeat an
     action. HOLD is kept in two slots, as in gct-e8ex, and the generated hold's admission replaces `stranded()` with
     `select()`. The generated operator set is exactly the main-path jobs plus WATCH-LOOP-2, CONTAIN-2, HOLD-1 and
     HOLD-2 (no WATCH-n, CONTAIN-1 or CLOSE-2); a test pins the file set.

     A stranded containment for C1 stops the handover: a hold suspends the city and rig, CLOSE tears down, and the
     operator is told. There is no
     stranded-lifecycle admission for C1. Dropping the s5 admission means `verified_lifecycle` then refuses, so ADMIT,
     RESTORE and TERMINAL are unreachable, and the overlay and receipt image stay installed until a reviewed
     successor exists.
6. **CLOSE:** besides the gct-e8ex CLOSE:
   - **Never pre-empts the drain-ack teardown.** Before any coordinator drain or session close, CLOSE waits up to 10
     minutes for the lane session Bead to close. A session Bead that carries `state_reason=drain-ack-stop-pending` is
     not drained or closed by the coordinator while the bound runs. At the bound the run is no longer normal: CLOSE
     then uses the inherited `gc runtime drain` and `gc session close` (`close-r11.py:124-152`) and records a **failed
     segment**. On the drift or trigger path, where the worker may still hold an `in_progress` claim, CLOSE uses the
     same inherited commands at once (as gct-mbg6's CLOSE-1 did). The **decisive residue proof is the cgroup census**:
     the lane scope found by the path WATCH-LOOP recorded (the pane is gone after `gc session close`, so not by
     `list-panes`), accepted only as a `tmux-spawn-*.scope` directly under the pinned `user@1000` app slice, where a
     missing scope (ENOENT, removed once empty) reads as empty; every other `tmux-spawn-*.scope` empty (ga-6utp's
     clean-city rule, `PLAN.md:385`); and the controller cgroup holding only its admitted members (above). The inherited `/proc` argv and cwd scan
     (`close-r11.py:72-89, 171-175`) stays as an extra check only (ga-6utp says such a scan is never the control,
     `ga-6utp-activation-r10/PLAN.md:370-376`). A lane process that survives is a **standing stop** (the operator is
     told; a reviewed successor follows). No new process control is added: the ga-6utp cgroup control is detection
     only, and CLOSE signals no process itself; its one inherited server action is `tmux kill-server` on an empty
     city server (`close-r11.py:166-169`);
   - **CLOSE's budget gate** runs **after** the drain, the session close and the residue proof, and gates only the
     image and snapshot exports, so a budget refusal never skips the teardown of a possibly live worker. It requires
     ADMIT's 75 plus the export budget of 15, so 90 minutes; the test counts the containment (about 7) and CLOSE's
     wait, drain, close and residue steps (about 14) against the deadline's 15-minute margin plus CLOSE's 30. A refusal
     leaves the overlay installed until a reviewed successor exists, a stated stop as for ADMIT;
   - the rule 6 audit; the probe target empty; the A2 audit that no default-choice codex route targets the candidate
     root; `common-snapshot-r1.py after` (no change);
   - **image 1:** `image_tool.py export --runtime claude` (after the session Bead's end state and a zero-process
     census), then `compare --step C1 --prev image0 --next image1`;
   - **the image 1 record** (`image1-record.json`): the image tool's `image.json` digest; the Bead-state part the plan
     requires (for `gct-oak5`, C1, X, C2 and H2: status, assignee, description digest, notes digest and every metadata
     key; H2 empty); and the common-snapshot `after` digest.
7. **ADMIT, RESTORE, TERMINAL** as in gct-e8ex. **TERMINAL** also:
   - takes the store **CLOSE-after** settle pair (§5.2): snapshots 5 minutes apart, at most three, inside TERMINAL's
     own 20-minute budget. Two consecutive identical snapshots settle it; otherwise TERMINAL refuses (a stop). The
     arithmetic test counts the 10 minutes of spacing plus the pinned export and inherited-check timeouts against the
     20. Whether a baseline order re-enabled by RESTORE can write a Template-store row is pinned at s1 from the order
     set and the gct-mbg6 TERMINAL records; if one can, the settle refuses (fail closed) and that is a stated stop;
   - checks the within-window allowlist, so ADMIT's and RESTORE's writes, if any, are inside the compared window. For an
     accepted segment it also checks the drain-ack end state. For a failed segment (a silent start, a non-drain-ack
     end, drift or a coordinator close) it records the failed outcome instead, and still restores and observes. The
     claim release that `gc session close` makes on that path (`close-r11.py:27-31`: C1 open and unassigned) is
     admitted by the allowlist **only** under the failed outcome, never for an accepted segment. s1 pins from Core
     source and the gct-e8ex records that Core's task-attempt block (`close-r11.py:27-31`) also keeps the restored
     Claude lane from scheduling that open, still-routed C1 after RESTORE; if it does not, TERMINAL refuses on a failed
     segment until the route is cleared by a reviewed step. C1's leftover route
     then stays as Core left it, and the handover stops for an operator decision;
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

1. The design (this document, d7) and `slots/`, two reviews.
2. s1: the generated package and image tool r3, two reviews. Jobs: WORKTREE (with image 0 and the common `before`),
   then PREP.
3. s2: PREP pins and, with the operator's cache-disposition approval, `CACHE_PINNED_NS`; two reviews.
4. Window: BIND, OBSERVE, PREFLIGHT, STAGE, ROUTE, RESUME, WATCH-LOOP (probe, normal end, containment), CLOSE
   (image 1), ADMIT, RESTORE, TERMINAL (CLOSE-after), then H1. The fallbacks (WATCH-LOOP-2, CONTAIN-2, HOLD-1,
   HOLD-2) are reviewed with the package and run only when `slots.select()` names them.

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

## 12. d5 (answers the d4 reviews of `e8bbc592`: A and B HOLD)

- **Both must_fix: TEARDOWN-1 had no reviewed mechanism.** It is dropped. The ga-6utp cgroup control is detection
  only. At CLOSE's bound, and on the drift or trigger path, CLOSE uses the inherited `gc runtime drain` and
  `gc session close`, as gct-mbg6's CLOSE-1 did. A surviving lane process is a standing stop, found by the inherited
  zero-residue proof.
- **B must_fix 1: the fallback rules.** They are chosen by containment records only (the suspend actions, not
  RESUME's), first match wins. The city-suspended, rig-not-suspended state goes to CONTAIN-2, which acts by events.
  WATCH-LOOP-2 contains at once on a decision without an outcome.
- **B must_fix 3: the nudge check.** It is an explicit count on the raw city exports at CLOSE and TERMINAL, with the
  dedup caveat stated.
- **A must_fix 2: the RESTORE budget.** RESTORE is 60 and ADMIT 75; CLOSE gains a gate of 105. The test pins the whole
  chain.
- **A must_fix 3: the startup phase.** The process rules apply after the exec'd provider is first observed. Before
  that, only the pinned pane chain, the wrapper and one `auth status` child are admitted, up to the silent-start
  bound.
- **Should_fix taken:**
  - the session name read from the session Bead and the pane scope from `tmux list-panes`, in the same observation;
    the status relaxation for the suspend actions only; the health signal pinned (A 1, B 3);
  - "containment records" defined (A 2);
  - `STOP-C1` as the only operator stop, and the `systemctl stop` consequence stated (A 3, B 1);
  - the abnormal branch's budget consequence stated, with the CLOSE budget gate (A 4, B 2);
  - WATCH-LOOP's own deadline computation and its 30-minute minimum (A 5, B 2);
  - the dedup semantics (A 6);
  - the two lane literals (A 7);
  - the operator-pane constraint (A 8);
  - TERMINAL on a failed segment (B 4);
  - the settle retries (B 5);
  - the stale text, and plan r20 on the derivation source and on TEARDOWN (B 6).
- **Next:** the generated package, where the tests pin these rules as code (the procedure-as-code rule: four design
  rounds found gaps in prose, so the s1 code and its tests carry the precise semantics from here on).

## 13. d6 (answers the d5 reviews of `84bfeac4`: A and B HOLD)

- **(Superseded by §14.)** **Both must_fix 1: the state with no slot.** It is closed by rule 4: WATCH-LOOP-2 is the exact complement of the
  quiet end within the no-record branch and contains at once on a closed session that is not the quiet end.
- **Both must_fix 2: HOLD-1 not reached.** Rule 1 now uses the full `stranded()` predicate: incomplete, failure and
  refused-after records of any action (RESUME's included), non-zero done records of the new jobs, and a slot already
  used. WATCH-LOOP's exit status is defined, so a completed containment is not misread as stranded, and rule 0 sends
  a completed pair to CLOSE.
- **Should_fix taken:**
  - the provider is the wrapper's own pid after exec, the `auth status` child is excluded by pid, parent and argv, the
    `/bin/sh` stage is admitted, and the prompt and `--resume` shapes reuse the boundary's rules (A 3, B 1);
  - the pane chain is admitted by its recorded pid set (B 2);
  - the census scope: the controller cgroup rule, only the city socket, the tmux empty answers, and the stated
    cgroup-move gap (A 4, B 3);
  - the cgroup census as the decisive residue proof, found by the recorded path, with `tmux kill-server` named, and a
    pane left in the controller cgroup as a trigger (A 5, B 4);
  - CLOSE's budget gate after the teardown (A 2);
  - CONTAIN-2's precondition as the union, each slot once, then re-evaluation (A 6, B 7);
  - the generated operator set pinned (A 7);
  - the claim release admitted only under the failed outcome (A 8);
  - RESTORE's phase timeouts summed by the test (A 9);
  - the nudge paths named, with the queued-nudge dedup pinned from source at s1 (A 10, B 5);
  - TERMINAL's settle arithmetic and the re-enabled order question pinned at s1 (B 6);
  - RESUME refusing and RESUME's stranded records (A 1).
- **Next:** the generated package with tests (the procedure-as-code rule).

## 14. d7 (answers the d6 reviews of `7d2d7b84`: A and B HOLD)

- **Both must_fix 1: rule 1 shadowed rules 2 to 4.** The rule no longer reads exit statuses. `slots.select()` uses
  only records, used jobs, a passing hold and the last final observation; a died WATCH-LOOP now reaches WATCH-LOOP-2
  or CONTAIN-2, and a passing hold leads to CLOSE's teardown (B's option b as well).
- **Both must_fix 2: the partial RESUME.** A completed rig-resume with the city never resumed selects CONTAIN-2,
  which runs rig-suspend only (permitted from `('rig-resume',)`), and a completed rig suspend then selects CLOSE,
  whose held predicate accepts it. RESUME refusing before rig-resume's intent selects CLOSE's never-resumed branch.
  The rule runs after RESUME too.
- **A must_fix 3: the controller cgroup.** It admits the ga-6utp record members and the city tmux server by
  SO_PEERCRED, each pid bound to its start time.
- **Should_fix taken:** CLOSE's gate at 90 with the arithmetic (A 1); the pid and start time (A 2); the residue path
  validation, ENOENT and every tmux-spawn scope (A 3, B 4); partial-RESUME containment accepted by CLOSE (A 4); the
  intent named (A 5); two hold slots and the hold admission by `select()` (B 1, B 2); the in-process containment flag
  (B 3); the task-attempt block pinned at s1 (B 5); the RESUME to WATCH-LOOP gap stated (B 6).
