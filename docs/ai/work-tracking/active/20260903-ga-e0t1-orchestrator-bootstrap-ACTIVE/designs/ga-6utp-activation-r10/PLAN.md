# ga-6utp: activate the Operations candidate lane (gct-lagl) — r12

(The directory keeps its r10 name; it holds r12. Earlier rounds follow, newest first.)

## r12 (2026-09-26): answers both reviews of r11 `59ca1a0f` (both HOLD, the same must_fix)

**Both reviews, must_fix 1.** `scope = "city"` is Core's cross-store switch.
- Core's `AgentIsCrossStoreEligible` and `AgentReachesWorkflowStore` in internal/agentutil/resolve.go let such
  an agent discover, be routed and claim work in every rig store, and in HQ.
- The r10 V1 block had no scope. The candidate lane must stay bound to the gascity rig.
- The fix: `agent_toml` carries no `scope`, and validation requires the resolved `Scope` to be empty.
  - Identity and session placement come from `dir = "gascity"`.
  - A city-root agent is not expanded per rig, so this is still one agent.
  - The `agent.toml` pin is now `ba01f223`.
- The package's validation against the real gc passed: `/var/tmp/ga-6utp-r12-dryrun-20260926`, the agent
  resolved with no scope, and no shadow was left.

**Should-fixes taken:**
- **Staging.** It cleans up its own partial directory when a write fails (A 2, B 5).
- **Rollback.** It now clears this package's own crash leftovers, but only in their exact shape (B 1):
  - a staging directory holding only `agent.toml` and the prompt as regular files;
  - a `.city.gct-validate.lagl-*` shadow whose entries are symlinks plus one real `agents/` of copied agent
    directories.
  Anything else still blocks for a human, and the record lists what was cleared. So no crash window needs a
  hand removal.
- **Shadow side effects are documented.** The shadow's gc config loads may rewrite Core's own runtime assets in
  the live `.gc`: the same bytes every quiet `gc status` writes, and what the Template renderer's shadow already
  does (A 1, B 2).
- **The fake gc** skips symlinked agent entries as Core does (A 4).
- **New tests:**
  - resolution mismatch;
  - live city entries unchanged by the shadow;
  - a symlinked agent being invisible;
  - rollback clearing exact-shape leftovers and still refusing foreign ones.
- **Tests and pins.** There are 213 tests. `pins.json` is `50b4220a`.
- **Checked live.** The hand-restored `city.toml`, registry and fragment are 0644, uid 1000 and nlink 1, as the
  steps require (B 4).
- **Titles and docstring are updated** (A 5, B 6).

**Carried, not changed.**
- The render step still validates fragment plus agent only inside the renderer's `--apply`, after its intent
  (B 3). A refusal there writes nothing, and rollback recovers.

**Process note.** The r12 edits were made while review B of r11 was still reading. From now on, no edits are
made in a package worktree while a review of it is running.

The Template source is delivered: PR 70 merged as `e6195b10`, whose tree equals the reviewed head
`53a98b3f`. This package is the activation package required by gct-lagl DECISIONS 14. It runs only
after the ga-4z38 window's TERMINAL, because that window pins `city.toml`, the managed fragment and
the Template checkout.

r2 answers both reviews of r1 (`e945e30b`, both HOLD). The main changes:

- **Fixtures follow Core's real interfaces.**
  - `gc agent list --json` returns an object whose `agents` items carry `pool`. There is no
    `max_active_sessions` field.
  - `gc reload --json` returns lifecycle JSON with `outcome` and `revision`.
  - `gc status --json` can come back `partial`.
  - The renderer report keys are real, and the renderer uses the real `candidate-provider.toml`.
  - r1's fake returned shapes Core never emits, so its reload proof could not have passed live.
- **`activate.py`.**
  - Every intent and record binds the reviewed pins digest (a command-line argument) and the
    executor digest.
  - The quiet check is strict: it refuses a partial observation and a missing key, and binds the
    controller pid and the suspension-state digest.
  - Checkout requires a clean canonical checkout and runs with hooks and fsmonitor off. It proves
    every lane file (renderer, wrappers, boundary, subscription, policies and provider templates)
    against its blob, before and after.
  - Predecessor identities are proven before the intent.
  - Render requires drift against the live registry and the provider-template digest, and proves
    the fragment key by key: other tables, existing patches and providers, the provider body, every
    option, and the candidate patch's `option_defaults` and `env`.
  - Reload requires applied or no_change plus a revision, has a 420 s timeout, and proves the
    identity, provider, suspension, cap and prompt bytes.
  - Rollback refuses foreign state, restores atomically, uses fresh moved-aside names, reloads, and
    proves the agent is gone.
- **`intake.py`.**
  - `apply` is bound to the reviewed manifest digest.
  - The export directory and the fresh worktree must lie outside the candidate root and every
    sandbox-writable location.
  - Links, modes and binary changes come from `git diff --raw` and `--numstat`, never from a later
    lstat.
  - Parents are checked with no-follow semantics, and untracked keys are validated.
  - Stop paths apply to ignored files too.
  - A walk error refuses.
  - A process scan runs before and after export.
  - The replay covers the untracked files.
  - Retirement goes to `candidate-archive/<bead>/`, or locks the worktree in place if the move fails.
- **`preroute.py`.**
  - It takes uids from `/proc/<pid>/status`, and an unreadable link counts as a hold.
  - Hidden processes are caught. Under `hidepid=2`, a non-dumpable same-uid process is invisible in
    `/proc`, so the check reads user-manager cgroup membership, with a reviewed allowlist of
    `init.scope` and `gpg-agent.service`.
  - It records the digest of the routed Bead's description.

## r11 (2026-09-26): the candidate is a PackV2 agent directory; city.toml is never written

**What happened to r10.** r10 `f850f035` had two SOURCE_PASS verdicts. Its live run, rooted in operator staging
`~/.local/share/gas-city-staging/ga-6utp-activation-20260926` (review B should_fix 1), went as follows:
- `host`, `inputs`, `root`, `checkout` (proof only) and `registry` passed.
- `city` wrote its reviewed postimages. Its agent proof then refused with "gc agent list failed": the deployed
  Core rejects PackV1 `[[agent]]` tables ("move each agent to agents/<name>/agent.toml").
- `gc status` failed the same way, so the reviewed rollback could not pass its quiet check.
- With operator approval, the rollback's exact writes were applied by hand from the digest-verified backups
  (record `records/manual-restore.json`):
  - `city.toml` back to `4f7e170f`;
  - `rig-permissions.json` back to `d22cf4c1`;
  - the prompt moved aside to `managed/operations-candidate-prompt.template.md.rolled-back.20260926T063519Z`;
  - the fragment untouched at `cba75f87`.
- Afterwards `gc status` works (controller 995924, suspended), and the M7 inspector reports ok with zero drifts.
  The empty candidate root that `root` created remains.

**Changes (`activate.py`):**
- **The city step.**
  - It writes the city-pack agent directory `agents/operations-candidate-worker/` with `agent.toml` and
    `prompt.template.md`. The agent carries `dir = "gascity"` (the identity the fragment patch and the
    registry record name), `scope = "city"`, `provider = "claude"`, `max_active_sessions = 1` and
    `suspended = true`.
  - It stages that directory under a dot name, `agents/.operations-candidate-worker.tmp.gct-lagl.N`, which
    Core's discovery skips (agent_discovery.go: names starting `.` or `_`).
  - It then proves Core accepts it. A throwaway shadow beside the city symlinks every city entry, and its
    `agents/` holds real copies of the agent directories plus the staged one, because Core ignores symlinked
    agent entries. `gc config show --validate` must pass, and `--json` must resolve exactly one gascity-bound,
    suspended, cap-1, city-scope agent.
  - Only then does it write the intent and rename the staged directory into place.
  - A validation refusal removes the staged directory and leaves nothing live changed.
  - A leftover staging directory or shadow matches the leftover guard and blocks the next step.
- **`city.toml`** is required to stay `4f7e170f` in every step, in resume and in rollback.
- **Rollback** refuses a foreign `city.toml` or a foreign agent directory. It moves the agent directory aside to
  `agents/.operations-candidate-worker.rolled-back.gct-lagl.N`, a dot name, never deleted.
- **`root`** adopts an existing candidate root only when it is exactly the postcondition (empty,
  operator-owned, 0755). This covers the root the r10 run created.
- **Pins.** `make_pins.py` pins `agent.toml` `cc7dc70d` instead of a new `city.toml`. `pins.json` is
  `676bc1d8`.

**Tests.** 209 pass. The fake gc now:
- rejects a PackV1 `[[agent]]` table, as Core does (the r10 failure, reproduced);
- discovers `agents/*/agent.toml`, skipping dot names;
- answers `config show --validate` and `--json`.

New tests cover:
- `city.toml` untouched, the agent directory exact, and no leftovers;
- a config gc rejects, refusing before any live write;
- the staged directory being invisible, and a leftover blocking the next step;
- rollback refusals on a foreign `city.toml` or agent directory, and the move-aside;
- `root` adoption and its refusals.

**Live dry runs (read-only).**
- The first scratch prototype (`/var/tmp/ga-6utp-v2-proto-20260926`) resolved the agent as
  `gascity/operations-candidate-worker`, Dir gascity, Scope city, Suspended, MaxActiveSessions 1.
- The package's own validation against the real gc passed: `/var/tmp/ga-6utp-r11-dryrun-20260926`, with the
  staged directory under `/var/tmp` and the shadow removed.
- The first attempt, kept as `...r11-dryrun-20260926.refused-symlink-shadow`, showed why the shadow needs
  copies: symlinked agent directories are invisible to Core.

**M8 scope, updated.** `city.toml` no longer changes. M8 adopts the registry (`1225b7c5`) and the rendered
fragment. It may also pin the new agent directory files and the candidate-lane Template files (review B of r10,
should_fix 5). A P9 receipt refresh follows if the traced revision moves.

**Run order.** A fresh operator-staging package root, `ga-6utp-activation-r11-20260926`, holding a copy of
`pins.json`. The steps are `host`, `inputs`, `root` (adopts the empty root), `checkout` (proof only),
`registry`, `city`, `render` and `reload`.

## r10 (2026-09-26, ga-e0t1.18): re-pinned to the deployed state

r9 was accepted with the first-window package at `2067a406`, a double SOURCE_PASS, on the ga-6utp branch.
Its files are copied unchanged into `designs/ga-6utp-activation-r10` on the ga-e0t1 branch. The ga-6utp
worktree's workflow runtime is stale, so it is not a coordination target. Since r9, the live state has moved:
- ga-e0t1.15 S3 checked the canonical Template out at `cfd353f3`, which contains PR 70 `e6195b10` and PR 71;
- Core is `fce2e9a0` (deefb98b);
- the platform metadata is M7 (`4bec5ef1`);
- the worker receipt is `23eeb222`.

The operator decision of 2026-09-26 ("Activate, then M8") answers a contradiction neither plan covered. M7
pins exactly the files this activation rewrites:
- `city.toml` (the managed file city-config, and an input, `4f7e170f`);
- `managed/rig-permissions.json` (`d22cf4c1`);
- `managed/rig-permissions.toml` (`cba75f87`).

**Changes:**
- **`make_pins.py`.** `TEMPLATE_BEFORE` and `TEMPLATE_COMMIT` are both `cfd353f3`, so the reviewed change set is
  empty. The regenerated `pins.json` is `4c5d2a10`. The live predecessors are unchanged since r9: `city.toml`
  `4f7e170f`, registry `d22cf4c1`, fragment `cba75f87`, and renderer `bb97950c` at `cfd353f3`. The `city.toml`
  postimage is still `c07f2cad`, and the registry postimage is `1225b7c5`.
- **`activate.py` `step_checkout`.** When the base equals the target, the step proves everything it proved
  before: the clean pinned status, ancestry, the renderer blob, the empty change set, filter-free attributes
  and every lane file against its blob. It runs no `git checkout`, so the Template Git directory that M7 pins
  is not touched. `rollback` already skips the checkout when the head is the base.
- **`preroute.py` `member_role`.** The live dry run of `host` refused with "controller cgroup member 2852 has no
  reviewed role: /home/loucmane/gascity/bin/gc (deleted)".
  - The managed dolt watchdog survived broker sequences 14 and 15. It maps the replaced image `69d00186`, as
    M7 records in its `WATCHDOG_IMAGE`.
  - The watchdog role now also admits an executable reported as `<gc> (deleted)`, but only when the mapped
    image's sha256 is exactly in `SURVIVING_WATCHDOG_IMAGES = {69d00186}`.
  - The image is read only for that case, never for the controller or dolt. Every other role rule (argv,
    `Seccomp` 0, `NoNewPrivs` 0, namespaces, parentage) is unchanged. The recorded exe string, including
    "(deleted)", is what later identity checks compare.
- **Tests.** Three `test_activate.py` tests cover the checkout at the target (it proves without moving, a
  rollback restores the files without a checkout, and a lane-file drift refuses). One `test_candidate_tools.py`
  test covers the surviving-watchdog role. There are 201 tests, all passing.

**Live dry run (2026-09-26, r10, throwaway root `/var/tmp/ga-6utp-r10-dryrun2-20260926`).** `host` and
`inputs` passed against the real machine: the controller 995924, the surviving watchdog and dolt roles, the
hidden-process scan and the PATH chains. The first dry-run root, `-dryrun-`, holds the refusal that led to the
role fix.

**Run order after two reviews.** The package root is a fresh `/var/tmp/ga-6utp-activation-20260926` holding a
copy of `pins.json`, so the worktree stays clean. The steps are `host`, `inputs`, `root`, `checkout` (proof
only), `registry`, `city`, `render` and `reload`, one invocation each.

**What follows:**
- **M8.** A reviewed metadata successor adopts the three changed city files (city-config
  `previous_sha256` 4f7e170f with a pinned backup of the pre-activation bytes, and the registry and fragment
  inputs) and the new prompt file.
- **Possible P9.** The reload adds an agent to the composition, so the permission revision will probably move
  from `2113693e`. The signing-lane receipt `23eeb222` pins that revision, so a P9 receipt refresh follows if
  the traced revision changed.
- **Then** the first candidate window (ga-cw-first-window, re-pinned).

## r9 (the r8 non-blocking follow-ups; r8 `92cfb185` passed both reviews)

- **Checks.**
  - Every check re-proves each member's `Seccomp`/`NoNewPrivs` state, as well as its exe, start time and
    namespaces.
  - The record refuses a member whose `/proc` cgroup is no longer the controller's, which catches a pid
    reused between the two reads.
  - The `time` namespace is compared too.
- **Tests.**
  - On the check path: the controller's sandbox state, a member's start time, namespaces, seccomp and
    `no_new_privs`, and a member pid reused only after the clean read.
  - Sandboxed controller and watchdog role shapes, an nnp-only server, and a member that left the
    controller cgroup at record time.
  - The misnamed test is renamed.
- **Precondition wording.** On 2026-09-24 the operator declined both in-sandbox probing and
  additional monitoring tooling. The `preroute.py` docstring now states the precondition as a documented
  assumption about Claude Code's sandbox. The checks that run are the city control and intake review.
  The `activate.py` docstring, the HANDOFF coverage table and "After this package" match. The vault
  inventory becomes an automated read-only coordinator step in the first window.
- **Tests.** 197 pass, including real time-namespace value changes at record time and on the check path. One run of five failed once on the known host-timing flake in the consistency
  scan.

## r8 (answers both reviews of r7 `9eb95a7b`, both HOLD)

**Roles cannot be taken by a sandboxed process** (A must-fix 1, B must-fix 1).
- **The attack.** A leftover in the controller cgroup could exec the reviewed gc or dolt binary with the
  reviewed argv into a vacant role at a refresh.
- **Why it now fails.** A sandboxed process keeps its seccomp filter and `no_new_privs` for life, across
  exec. So a role now also requires:
  - `Seccomp: 0` and `NoNewPrivs: 0`;
  - namespace inodes (mnt, net, pid, user, cgroup, ipc, uts) equal to the controller's;
  - for the watchdog, the controller's parent, which is the user manager;
  - for dolt, the recorded watchdog as its parent.
- **Parentage alone would not do.** Live, the watchdog's parent is the user manager (2288), not the
  controller, and orphans are adopted by that same user manager. Parentage alone therefore cannot tell a
  double-forked leftover from the watchdog; the sandbox state and namespaces can.
- **Live values.** All three members show `Seccomp: 0`, `NoNewPrivs: 0`, identical namespaces and
  parents 2288, 2288 and 2852.
- **Checks.** Every check re-proves each member's exe, start time and namespaces, and the controller's
  sandbox state.

**ptrace is a checked host fact** (A must-fix 2).
- Yama `ptrace_scope` is 1 on this host. A process may then ptrace or `process_vm_writev` only its
  descendants, and the tmux server, controller and dolt are never a pane's descendants.
- The record requires `ptrace_scope >= 1` and stores it, and every check re-reads it.
- The precondition also lists the first-window proofs:
  - no ptrace, `process_vm_writev` or `/proc/<pid>/mem` write outside the sandbox;
  - no tmux server state change through pane output: `set-clipboard`, `allow-passthrough` and
    `allow-rename` are off;
  - the city tmux server is in the controller's cgroup for every candidate session, and it is never
    started from an operator shell (B should-fix 2).

**Also in r8.**
- **Server and identities.** The city tmux server is re-derived on every read. It must be unsandboxed
  tmux in the controller cgroup, judged by membership. Every identity is re-proven after the clean read,
  so a pid reused during the rereads is caught (A and B should-fix 1).
- **Record hygiene.** The record verifies the controller's identity before reading its environment, and
  refuses hidden pids outside the reviewed cgroups at refresh time too.
- **gc output.** `gc agent list` must carry a string `city_name`.
- **Tests.**
  - Sandboxed role holders are refused, for each seccomp and `no_new_privs` combination.
  - The record refuses a dolt with the wrong parent, a member with foreign namespaces, and a watchdog
    started differently from the controller.
  - Yama is required by the record and by every check; unreviewed hidden pids are refused at record
    time.
  - An unobservable or sandboxed server is refused.
  - The server is re-derived per read, and a member pid reused during the rereads is caught.
  - A socket that cannot be read is refused.
  - The consistency recheck drops transient findings and keeps persistent ones.
  - Rollback refuses a city that changed across its reload.
- **Live read-only run.** The record is exact (controller, watchdog and dolt with their roles),
  `ptrace_scope` is 1, and the city is clean.
- 184 tests pass, three consecutive runs.

## r7 (answers both reviews of r6 `02298f8f`, both HOLD)

**The precondition is now explicit** (A must-fix 1 and 3, B must-fix 1).
- **Findings.** The reviews found escapes that no process check can see:
  - tmux timers, hooks and `run-shell` jobs left in the long-lived city tmux server (Core sets
    `exit-empty off`);
  - a leftover listening on the city socket path;
  - WSL interop (`cmd.exe`, `powershell.exe`), which runs outside every Linux cgroup;
  - the user and system buses;
  - a localhost sshd.
- **What they share.** Every one of them needs an `AF_UNIX` socket, the host network, a user namespace,
  a write outside the worktree, or an interop exec. A seccomp filter and namespaces are inherited by
  every descendant, so the same limits bind leftovers.
- **First-window proofs.** The first candidate window must prove each limit before any routing, and each
  is a stop condition:
  - sandboxed commands, and anything they start, cannot create or connect `AF_UNIX` sockets;
  - they cannot reach the host network, localhost included;
  - they cannot create user namespaces;
  - they cannot write outside the worktree (`/tmp/tmux-<uid>` included);
  - they cannot run an interop binary;
  - the lane's commands excluded from the sandbox (`bd close/show/update`, `gc hook --claim`,
    `gc runtime drain-ack`) cannot run candidate-controlled code.
- **Where it is stated.** The `preroute.py` docstring states that the control does not hold without these
  proofs.
- **Server identity.** A running city tmux server must also be `/usr/bin/tmux` by kernel exe. Its cgroup
  comes from the membership map, not `/proc`, so a hidden server is judged too, and a non-tmux listener
  on the socket path is refused.

**Role-bound members** (A must-fix 2, B must-fix 2).
- **Roles.** Every controller-cgroup member is recorded as `{pid, role, exe, start}`. There are three
  reviewed roles, matched by kernel exe plus exact arguments against the live shapes:
  - `controller`: `gc supervisor run`;
  - `dolt-watchdog`: `gc __gc-managed-dolt-scope-watchdog <cfg> <log> <city>`;
  - `dolt`: `dolt sql-server --config <cfg>`.
- **Recording and refresh.** Recording and every refresh accept exactly one controller, at most one
  watchdog and at most one dolt. Anything else refuses. A leftover can therefore not be laundered into
  the record, including by an operator refresh.
- **Every check.** `city_problems` re-proves each recorded member's exe and start time, which catches a
  reused pid. A missing member is computed inside the controller cgroup only.
- **Pane scopes.** They match on any path component (sub-cgroups included).

**The record derives its own socket and re-runs the host checks** (A must-fix 2).
- `preroute.observe_city(slice, controller, city)` derives `/tmp/tmux-<uid>/<workspace.name or directory
  name>` itself.
- It refuses `[session] socket`, a non-tmux `[session] provider`, and `TMUX_TMPDIR`, `GC_AGENT_SLICE` or
  `GC_SESSION` in the controller's environment.
- `preroute.py record <uid> <controller-pid> <city> <out>` has no socket argument, writes exclusively and
  refuses a uid other than the caller's.
- `host` cross-checks the derived name against `gc agent list`.
- **Coverage limit.** Socket overrides in packs or fragments are not composed. A server on another path
  still puts its panes in `tmux-spawn` scopes, so it fails closed.
- **Refresh procedure.** Core keeps the city tmux server alive (`exit-empty off`), so a refresh needs that
  server stopped first. The role binding is what makes that safe.

**Also in r7.**
- The candidate city agent may not carry a `session` key.
- The privileged agent-file patterns match case-insensitively.
- Rollback requires its post-reload quiet observation to equal the one taken before.
- The consistency scan confirms a finding by re-examining the same pid once. This is needed because busy
  hosts show processes that are unreadable for a moment, which made two tests flaky.
- **Host step after a failure.** `host` writes records only. If it fails after writing the process
  record, the package cannot resume `host`; a fresh package directory is used instead. Nothing live was
  written.
- **Tests.**
  - Refusal reasons are pinned in every remaining test, found by running a scratch copy with
    `match="@@@"`.
  - New tests cover: roles, reused pids, missing members in other cgroups, sub-cgroup panes, server exe
    and cgroup, a non-socket path, socket and backend overrides, environment overrides, the workspace
    name, exclusive `record` main, the ignored bound, and the gc city-name cross-check.
- **Live read-only run.** The record for pid 2331 lists 2331 `controller`, 2852 `dolt-watchdog` and 2867
  `dolt`, with socket `/tmp/tmux-1000/city`. The city is clean and the survey is empty.
- 172 tests pass, six consecutive runs.

## r6 (answers both reviews of r5 `94e7e85a`, both HOLD): a deterministic process control

Both r5 reviews held on the same class. A process-hold scan can be evaded by timing: hiding for a single
read, or releasing every hold during the scan and reopening by path afterwards. That second evasion shows
a hold scan can never be the security control. Both reviews also found that the r5 premise "workers
descend from the controller" was wrong: Core starts workers as tmux panes.

**Security control (new, `preroute.city_problems`).**
- **Why cgroup membership.** `cgroup.procs` lists every member whatever `/proc` shows, and a process
  cannot leave its cgroup without a cgroupfs write or a user-bus call.
- **Where candidate processes live.** The host's tmux is 3.4, linked against libsystemd, so every pane
  moves into its own `tmux-spawn-*.scope`. Core's `agent_slice.go` documents this, and it follows the
  tmux sources. If that move fails, the pane stays in the tmux server's cgroup.
- **A clean city therefore means all four of these hold:**
  - the controller is the recorded process, by pid, exe, start time and cgroup;
  - a running city tmux server is inside the controller's cgroup (its pid comes from `SO_PEERCRED` on the
    city socket, so the check works even when `/proc` hides it);
  - the controller's cgroup holds exactly the recorded members plus that server;
  - no `tmux-spawn-*.scope` in the user slice has a member.
- **Rereads are sound.** Membership cannot be hidden, so a single clean read proves the city was clean at
  that instant. Up to five reads, 0.2 s apart, tolerate transient controller children.
- **Where it runs.** `preroute.check` and intake export, before and after, run it first.
- **The city process record.**
  - `host` writes it to `records/process-record.json`, with its digest in the host record.
  - `preroute.py record` refreshes it read-only, after a controller, dolt or gpg-agent restart. Each
    refresh and its digest are recorded on the Bead.
  - It refuses while a city tmux server runs or a pane scope has members.
- **Socket and environment checks at `host`.**
  - The socket is `/tmp/tmux-<uid>/<city_name>`, with `city_name` taken from `gc agent list`.
  - `city.toml` must not override the socket.
  - The controller environment must not set `TMUX_TMPDIR` or `GC_AGENT_SLICE`. Either one would move the
    socket or the panes.
- **Live read-only run.**
  - Controller `gascity-supervisor-home-42adab5d.service`, pid 2331, start 3970, exe
    `/home/loucmane/gascity/bin/gc`.
  - Members 2331 (the controller), 2852 (the dolt watchdog) and 2867 (dolt).
  - Socket `/tmp/tmux-1000/city`, with no server running.
  - Neither variable set; the city is clean and the survey is empty.
- **Operator constraint.** Candidate panes cannot be told apart from an operator's own tmux panes. So no
  operator tmux pane may exist during pre-route or export; the check stops on one.

**First-window stop-condition proofs, added.**
- A sandboxed candidate command cannot reach the user bus: connecting to `/run/user/<uid>/bus` or
  `/run/user/<uid>/systemd/private` fails, and `systemd-run --user` fails. Otherwise a candidate could
  start a unit outside every watched cgroup.
- Every candidate session's processes are in a `tmux-spawn-*.scope`, or in the controller's cgroup when
  the move failed, and the city tmux server is in the controller's cgroup.
- The sandbox cannot create user namespaces (from r5).

**Consistency checks, relabelled.**
- The hold scan and the hidden-set comparison stay in place and still fail closed on what they see:
  - a member missing from `/proc` at any entry, status, stat, link, task-list or per-task-link read is
    reported, unless it is a recorded hidden pid;
  - an exiting process counts as exited, not as a hold.
- Their timing evasions are accepted by design, because the control above does not depend on them.
- Per-thread fd tables are not read. A thread can drop an fd for the scan anyway.

**Also in r6.**
- **Privileged flag.** Any dot component (`.claude/`, `.codex/`, `.github/` ...) and any `*CLAUDE*.md`,
  `*AGENTS*.md` (including `AGENTS.override.md`), `*GEMINI*.md` or `*SKILL.md` is privileged, wherever it
  is.
- **Export bounds.** At most 10000 ignored files. The untracked count, the changed-file size and the
  ignored count are checked before the patch is built. The 32 MiB untracked-bytes bound is checked while
  copying, after the patch; this corrects r5's wording. The git listings themselves are bounded only by
  the 120 s git timeout, so an oversized listing can at worst crash the coordinator's read-only export,
  which fails closed.
- **Executor pin.** It covers `intake.py` too. A test asserts that the committed `pins.json` equals the
  digests of the committed executors.
- **Rollback.**
  - A post-reload quiet observation is required and recorded.
  - Wording corrected: validations run before the first write. A refusal after the writes (checkout move,
    final proofs, reload, quiet) leaves a partial restore with no record, and rerunning rollback over it is
    idempotent.
- **Tests.** Refusal reasons are pinned for the pre-route cases, the host facts and the render lane
  re-proof. City tests cover:
  - pane members, unrecorded and missing controller members, and transient rereads;
  - the tmux server cgroup, using a real listening socket and `SO_PEERCRED`, plus a stale socket;
  - controller mismatch by comm, exe, start time, cgroup and `..`;
  - real `/proc` parsing, and record shape and digest.
- 152 tests pass, five consecutive runs.

## r5 (answers both reviews of r4 `c7060b2d`, both HOLD)

- **Visibility toggle** (A must-fix 1).
  - r4 still let a cgroup member drop out of the holds scan by turning itself non-dumpable, and come back
    before the hidden check.
  - `process_holds` now reports any member that is missing from `/proc` at any point of its examination,
    unless it is one of the exact recorded hidden pids. A real exit mid-scan fails closed, and the survey is
    rerun.
  - The r4 test never ran its churn code. It is replaced by a toggle test that returns `[]` against r4 and
    reports the pid on r5.
- **Controller slice** (B must-fix 2).
  - The survey's process list is authoritative only if every worker is in the user slice.
  - Workers descend from the controller, so `host` proves the controller is `gc` inside the slice and
    records its cgroup. `preroute.py` and `intake.py export` re-prove this for the current controller pid,
    which is a new argument.
  - Leaving the slice needs a cgroupfs write, which is outside the sandbox.
  - Operator processes are legitimately outside the slice (the WSL session is in `/init.scope`), so a
    blanket refusal of candidate-uid processes outside the slice would always refuse.
  - Live read-only run: the controller is `user@1000.service/app.slice/gascity-supervisor-home-42adab5d.service`,
    and the survey with the recorded hidden set is empty.
- **The privileged flag is an allowlist** (B must-fix 1).
  - Only prose under `docs/` (`.md`, `.txt`, `.rst`) is ordinary. Work-tracking records and `CLAUDE*`/`AGENTS`
    files are never ordinary.
  - Everything else is flagged: code, tests, packaging, root-level modules and `.pth` files, readiness records
    and design executors.
- **Tests fail for their own reason** (A must-fix 2). Resume city keeps the postimage `city.toml`, has Core
  report the agent unsuspended, and matches `not suspended`.
- **Rollback.**
  - Quiet city, no renderer leftovers, the checkout (the predecessor or the reviewed target, with lane files)
    and every live file and the prompt are all validated before the first write. A refused rollback changes
    nothing.
  - After the writes, the clean predecessor checkout is proven again.
  - Rollback no longer proceeds in a city that is not quiet.
- **Binding.**
  - The executor digest now covers `activate.py`, `preroute.py` and `candidate_git.py`, and must equal the
    reviewed `executor` pin.
  - Render and `resume render` re-prove the checkout and every lane file right before the renderer runs.
  - `resume render` checks the backup against `fragment_before`.
- **Intake.**
  - Export bounds: 1000 untracked files, 32 MiB of untracked bytes, 16 MiB of changed files, checked before
    the patch is built.
  - Gitlinks in the base tree are refused at export, pre-route and apply.
  - `apply` binds the manifest's worktree and admin to its own root and common directory.
  - Retirement names the stage that failed: verify, archive-target, move or lock.
- **Threads.** `process_holds` also reads every thread's `cwd` and `root` under `task/`.
- **Corrections to earlier text.**
  - Core emits `summary.active_sessions` with `omitempty`, so an absent key is exactly zero. The r2 claim
    that quiet "refuses a missing key" was wrong for that key only, and the code keeps the default.
  - The threat-scope item on namespace creation holds only if the candidate sandbox forbids nested user
    namespaces. That is now a first-window stop-condition proof.
- **Re-activation after rollback.** Rollback leaves the candidate root in place, by design, and a new
  package's `root` step refuses it. Re-activation needs a human to inspect the root and retire or move it
  through the reviewed intake `retire` path first. There is no automatic removal.
- Tests: 132 pass.

## r4 (answers both reviews of r3 `ba552a2a`, both HOLD)

- **Resume.**
  - `resume render` now records `fragment_sha256` and re-proves the structure from the backup, so
    reload and rollback can follow it (review A: the deadlock had moved one step later).
  - Each resume proves at least what its step proves:
    - city: the postimages, and the agent suspended in the composition;
    - render: the predecessors;
    - reload: the predecessors and the recorded fragment;
    - checkout: the lane files at the target.
  - Tests: resume render, then reload; resume render, then rollback; resume city refusing an
    unsuspended agent.
- **Process survey** (review B must-fix 1).
  - Cgroup membership across the whole user slice is the authoritative process list. Hold checks run on
    it together with every visible `/proc` entry.
  - A member missing from `/proc` counts as hidden, never as exited.
  - The recorded hidden set must match exactly, so a stale record is itself a stop.
  - The survey runs twice, and both passes must be clean. A process that toggles `PR_SET_DUMPABLE`
    between checks is therefore still seen.
  - The expected-hidden file is bound by digest.
- **Rollback over an interrupted checkout** (review B must-fix 2).
  - After every rollback path, the Template checkout must be the clean predecessor, with its lane files
    proven. Otherwise rollback refuses and writes no record.
  - Restoring a mixed tree would need force, restore or reset, which are not used here; a human
    inspects instead.
- **Intake.**
  - The manifest facts are re-derived after the patch is generated, and must be equal.
  - The fresh worktree must be named `<candidate>-intake`.
  - Retirement reports accurately which stage failed.
  - The privileged list covers every path the coordinator, its tooling or CI later executes or
    trusts: `.github`, `scripts`, `templates`, `conftest.py`, packaging files, `.envrc` and others.
  - The docstring states that a refused fresh worktree is discarded, and that reviewed code runs under
    coordinator authority after review, by design.
- **Activate.**
  - The prompt is written atomically.
  - The renderer's own temporaries and validation shadows count as leftovers.
  - The Template's `info/attributes` must be absent.
  - A refused render never blocks its retry: fresh scratch names, nothing deleted.
- **Tests:** a non-agent patch table; a registry that is not the postimage; lane-file mode and byte
  mismatches; filter attributes; local attributes. Each is pinned to its own refusal reason.

### Threat-model scope (decision, r4)

The process checks in `preroute.py` and `intake.py` are defence in depth against **leftover candidate
processes**, meaning processes started inside the worker's sandbox that outlived the session. The
primary controls are the sandbox itself and the first window's stop-condition proofs, which include:
- session end reaps every descendant;
- writes outside the worktree are refused;
- the common directory is unwritable;
- gct-1ldk: no MCP server processes;
- (added in r5) the sandbox refuses to create a user namespace.

A same-uid process that has **escaped** the sandbox already holds the operator's full authority. It can
write `~/.bashrc`, the coordinator's worktrees and the signing inputs directly. Techniques available
only to such a process are therefore out of scope for these checks:
- writing to cgroupfs to move processes mid-scan;
- creating user or mount namespaces to hide paths;
- signalling gpg-agent to farm a recorded pid.

Their answer is the sandbox proofs, not a stronger scanner. The checks still fail closed on everything
they can observe.

## r3 (answers both reviews of r2 `fc1571a2`, both HOLD)

- **Render.**
  - The fragment is rendered into a package-local scratch city and proven key by key before anything
    live is written.
  - The live `--check` must predict exactly those bytes, against the reviewed registry and provider
    template. The intent records them.
  - Resume and rollback recognise them, so a render that dies after `--apply` can be resumed or rolled
    back. This fixes the rollback deadlock both reviews found.
  - Duplicate agent patches and changed non-agent patch tables refuse.
- **Predecessors.**
  - Render and reload prove that the registry, `city.toml` and prompt are their reviewed postimages.
  - Reload also proves the fragment is the recorded render.
  - The city step proves, through `gc agent list`, that the agent is suspended while it still composes
    on the base provider.
- **Checkout.**
  - It pins the exact reviewed change set (23 paths) and proves no filter attribute exists at either
    commit. Attributes and the attributes file are neutralized; the Template's local config defines a
    git-lfs filter.
  - It proves every lane file present at the base (bytes and executable bit) and the absence of the
    rest. r2 read candidate-lane files that do not exist at the base, so its checkout could not pass
    live.
  - A live read-only run of these proofs passes on the real Template.
- **Reload and rollback.**
  - Core always emits `pool`, so the cap must be exactly `{min: 0, max: 1}`.
  - The reload timeout is 480 s, above Core's own client bound of 430 s.
  - Rollback requires something recorded, requires a strict reload acknowledgement, and proves the
    agent is absent.
- **Hidden processes (`preroute.py`, shared by `intake.py`).**
  - Anything hidden in the second scan is judged, which catches pid churn and cgroup flapping.
  - The reviewed cgroups must hold exactly the pid sets the `host` step recorded, so a process that
    moves itself into `init.scope` or `gpg-agent.service` changes the set and is refused.
  - Walk errors refuse, and the whole `user-<uid>.slice` is scanned.
- **Intake.**
  - Reads and writes walk directory descriptors without following links.
  - The base commit is bound at export, pre-route and apply.
  - Apply re-derives every fact (modes, binary, stop paths, changed set, privileged set, untracked set
    and bytes) from the applied index; a test uses a genuine git-emitted raced mode change.
  - The fresh worktree must be a verified linked worktree directly under `gas-city-ops-worktrees`, with
    its drivers checked.
  - Untracked files containing NUL bytes need review.
  - Retirement locks the worktree in place on any error.
- **`preroute.py`** also binds the coordinator-authored description digest.

Tests: 85 pass. The live read-only runs of `host`, `inputs` and the checkout proofs all pass. The host
record captures exactly the reviewed hidden set: gpg-agent, plus the systemd user manager's pids in
`init.scope`.

## Live dry run (2026-09-24, r2, read-only)

`host` and `inputs` passed against the real machine in a throwaway package:
- `gc status` passes the strict quiet check: controller 2331, four rigs suspended, and the
  suspension state `823e4e21`, the same value M5 pinned.
- Eleven user-scope MCP servers are recorded.
- The hidden-process scan of the real user manager is empty.

## HANDOFF coverage

| HANDOFF | Where |
| --- | --- |
| 2.1 canonical checkout, render root | `checkout`, `render` |
| 2.2 candidate root before render | `root` |
| 2.3 review-only registration of the root | **Not needed, by decision.** Intake applies every candidate in a fresh coordinator worktree under the already registered `gas-city-ops-worktrees`, and reviewers bind `candidate=<commit>` in the Operations repository. No reviewer ever binds a candidate worktree. |
| 2.4 merge only the candidate record | `inputs`, `registry` |
| 2.5 python pin | `inputs` (live `e50d468e`) |
| 2.5 claude 2.1.280 pin | **Deferred, gated.** The first candidate window's typed receipt must pin the CLI digest (the wrapper's `--version` binds it). That window refuses without it. |
| 2.6 cap, render, live PATH check | `city`, `render`, `host` |
| 2.7 identity proof | `reload` |
| 2.8 receipt | **Deferred to the first candidate window.** |
| 2.9 host checks: managed settings, MCP trust, managed MCP | `host` |
| 2.9 vault mirrors inventory | **Deferred to the first candidate window:** `vault_inventory.py`, an automated read-only inventory before the first routing, recorded on the Bead. A hard link into the vault, or a same-named directory holding at least five of its files, is a stop. Its limits (skipped trees, other filesystems, unreadable directories, renamed or partial copies) are recorded, and they stay under the documented assumption. |
| 2.10 pre-route check | `preroute.py` |
| 2.10 never resume a pre-existing session | Satisfied by construction: this package creates the agent suspended, and no candidate session can exist before the first window. |
| 3 live proofs | **Superseded by operator decision (2026-09-24).** These items are a documented assumption about Claude Code's sandbox, not proven by any package. The checks that run are the ga-6utp city control (a clean city before routing and around export, which, under the documented assumption, shows nothing outlived a session) and intake review of every changed byte. gct-1ldk (MCP server processes) stays an open follow-up. |
| 4 intake | `intake.py` |

## After this package

The first candidate window has its own reviewed package, covering:
- the typed candidate receipt, with the claude pin;
- the automated vault-mirror inventory;
- unsuspending the agent;
- the first routed candidate (ga-fsfg R3) through `preroute.py`, then `intake.py`.

The r4 threat-model scope, the r5 corrections, and the r6 to r8 sections above describe the sandbox
and first-window stop-condition proofs as live controls. The r9 operator decision supersedes all of
them: the precondition is a documented assumption, and no package proves it.
