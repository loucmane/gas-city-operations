# Gas City Workflow Contract

## Authority layers

1. The project-local `AGENTS.md` / `CLAUDE.md` defines repository rules.
2. Gas City Beads is the sole active work ledger.
3. Aegis plans, sessions, trackers, and S:W:H:E records are evidence and readiness controls, not a second task ledger.
4. Operator authorization remains separate for lifecycle, signing, publication, privileged mutation, deployment, and destructive actions.

The plugin adds no shell allowlists, writable roots, groups, capabilities, MCP write methods, or service access. Its context command only reads files and runs read-only Git queries. Its lifecycle command uses only the caller's existing repository and ledger authority; it never treats successful orientation or a bead status as authority for routing, rig lifecycle, signing, publication, privileged mutation, or deployment.

## Cold start

Run:

```bash
python3 <PLUGIN_ROOT>/scripts/project_context.py --root /absolute/project/root
```

The result binds repository identity, exact rig, canonical checkout, approved linked-worktree root, branch/head/cleanliness, current plan/session pointers, ACTIVE trackers, adapter instructions, and literal Beads read commands. Stop if the root is not an exact Git worktree root, registry/descriptor identity is ambiguous, the current worktree is outside the approved root, or authority is not `beads`.

Before registry or descriptor resolution, the context command applies `config/root-policy.json` to
the Git common directory. `/home/loucmane/codex` is preserved historical evidence, not a source
root; its main checkout and all of its linked worktrees fail with the canonical replacement path.
The same evaluator is installed as one user-level Codex and Claude PreToolUse hook, preventing a
cold-start agent from mutating the historical root even before it remembers to run context. Project
trust is defense in depth only; the hook is the active mutation boundary. Canonical IDLE and active
task states use the same identity contract and remain valid.

## Lifecycle transitions

Run `workflow.py begin --root <canonical-root> --bead <id>` instead of remembering the
worktree/kickoff/ownership/readiness sequence. The transition journal lives under the repository's Git
common directory at `.git/gas-city-workflow/transactions/<bead>.json`, outside individual linked
worktrees. It binds the exact project, rig, branch, worktree, and starting commit and advances only
through `planned → worktree-created → scaffolded → claimed → ready`.

### Source projects without an installed Aegis runtime

The modern `beads-with-aegis-evidence` profile also supports uninstalled consumers.
Their workflow CLI uses the shared Operations Beads scaffold validator, not the
legacy numeric-task fallback. It requires the same exact Git/project identity,
live external ownership, primary plan identity, target-local session/plan pointers,
session-state parity, one ACTIVE tracker, and plan/tracker status parity. This
does not install Aegis, change profiles, or grant tool or worker permissions.
A present adapter, foundation manifest, current-work envelope, or native pending
tracking file always retains the existing adapter path, including when broken.

`verify` and `finish` use the existing target-aware plan-sync/archive commands.
Portable `log --evidence <relative-file> --note <single-line-note>` binds one existing
non-symlink file and its digest, and appends to the current daily session and six
tracker surfaces under the existing session lock/write-ahead transaction. Exact
replay is a no-op; partial replay, stale daily sessions, native pending IDs and
path escapes refuse. Byte/mode rollback and failed transaction evidence are
preserved. It does not manufacture a current-work envelope or consume native
pending events. Continue the daily session through the supported session lifecycle
before logging after rollover.

Gas City Core's central registry binds `refs/remotes/origin/main` and the existing
`/home/loucmane/gascity-core-worktrees` root explicitly; its parked canonical branch
is not the default source-work base. Recovery completes the existing journal and
ownership binding, never creates a replacement worktree or repeats ownership.

- `begin` creates or safely adopts the exact derived worktree and starts the evidence workflow.
- `resume` derives the active bead from `sessions/state.json` when `--bead` is omitted and verifies
  or completes the same transaction.
- `recover` is the explicit operator-facing synonym for append-forward recovery after a proven
  pre-mutation failure or complete rollback.
- `attach` adds one already-declared blocking dependency to the current source-work context. It
  keeps the primary Aegis session, tracker, and branch, records the dependency separately under
  `attached_bead_ids` while preserving the one-item authoritative `bead_ids` field,
  binds external source-work ownership idempotently, and journals the attachment. It refuses unrelated beads;
  do not open a second Aegis context while the parent source change is still active.
- `checkpoint`, `verify`, `publish`, and `finish` run their bounded checks and append results to
  the same transition journal.
- `coordinate` provides three closed, same-store ledger actions inside an externally owned
  task worktree: append a note, create an unassigned/unrouted P2 child, or add one blocking
  dependency and transactionally attach it. It persists intent before the supported API
  mutation; ambiguous results stop without replay. `log` records target-local evidence.
  The Operations-only Claude command profile can approve these explicit worktree targets
  from a stationary canonical conversation. It does not approve raw Beads commands, source
  writes, cross-rig access, worker dispatch, signing, or lifecycle changes. Both policy copies
  and executable helpers must match reviewed canonical source before automatic approval;
  changing workflow-runtime code remains in the explicit implementation/review lane.

### Exact pending attachment reconciliation

Attachment publishes already-verified ownership membership into its journal before
portable readiness checks plan/journal parity. A failed readiness check still leaves
the coordination intent pending; it is not a successful transaction or permission to
repeat the Bead write.

`reconcile-attachment` is a separately authorized, late-stage recovery: the one
recorded blocking edge, external ownership, plan and tracker must already be correct.
It requires `--root`, `--request-sha256`, `--expect-journal-sha256`,
`--expect-plan-sha256` and `--expect-tracker-sha256`. It never changes Beads, the plan
or tracker, and grants no native permission. It verifies the same-store request,
typed graph, exact recorded Bead fields, owner and registered worktree, preserves
a byte/mode/owner-exact journal backup, then completes only journal membership and
the original coordination intent after real readiness and repeated live readback.
Exact completed replay is checked and performs no writes.

This is not general recovery for an early or ambiguous partial. Other pending
transactions, stale pins, ownership/graph drift and unknown journal images refuse.
On technical failure, only its exact known staged journal may be restored from
the pinned preimage; an unexplained image is preserved and rollback refused.
Process termination between writes requires fresh diagnosis, not automatic replay.
The ordinary per-repository coordinator lock applies; there is no distributed
Beads transaction or cross-controller compare-and-swap guarantee.

### Inherited-context preflight and reconciliation

Modern `begin`, including dry-run, inspects the selected immutable base commit's
configured evidence layout before creating a branch, worktree or transaction.
An inherited unrelated ACTIVE context refuses; use the unfinished parent's
dependency workflow rather than allocating a second source context. Frozen
legacy behavior and the later exact scaffold/ownership checks remain unchanged.

For an older attempt that stopped at `worktree-created`, a separately authorized
coordinator may preview `workflow.py reconcile-context --root <parent-worktree>
--bead <unowned-child>`. Review its complete plan and SHA-256 before applying the
same command with `--expect-plan-sha256 <reviewed-digest>`. This is not an automatic
approval exemption or permission to run modified runtime source.

The child must be open, unassigned and unowned, with an untouched two-phase
journal, a clean registered worktree at the exact recorded base, and precisely
the unfinished parent's inherited ACTIVE context. The parent must be READY,
externally owned in the same project/store, and ancestor-related. The plan binds
both journals, worktrees, Beads, evidence, pointers, registry and helper sources.
No branch/ref move, source scaffold, worker, platform or cache operation occurs.

Apply preserves byte/mode/owner-exact original journal snapshots and creates an
append-forward recovery record. It marks only the abandoned unowned context as
retired, then uses ordinary coordinated dependency attachment to bind the child
to the existing parent. The parent remains unfinished; its plan, tracker and
journal record the attached work. Normal attachment refuses an unreconciled
standalone journal, and a retired child cannot resume as a second coordinator.

Immediate exact replay is read-only. A stop before any Bead transaction can
resume only from the pinned originals or exact retirement image. Unknown or
partially executed coordination refuses without repeating mutations; preserve
the pending record for separate diagnosis. Legitimate later source/evidence or
Bead changes invalidate replay and do not authorize refreshing its pins. The
repository lock and fresh readbacks are not a distributed Beads reservation.

The journal is evidence, not authority. A partial or contradictory filesystem, Git, bead, or
scaffold state blocks instead of being guessed away. Existing unscaffolded worktrees can only be
fast-forwarded when clean and ancestor-related; once scaffolded, their task branch is never moved
by lifecycle replay.

### External coordination versus native claims

`workflow.py` is the source coordinator's lifecycle, not a managed worker's claim protocol.
It records external activity as **in_progress with no assignee**, with the single metadata key
`workflow.external_owner` containing `external-coordinator.v1:<sha256>` of the exact project,
city, rig, canonical repository, branch, worktree and primary transaction digest. The expanded
binding is derived from the preserved journal; the CLI receives no nested JSON quoting.
Attached blocking Beads share that binding. It never
uses an OS username, `human`, or a fabricated session as a worker claim. Native workers retain
their real session-bound claim and existing orphan cleanup, unchanged. Assigned work, native
control metadata, route labels, and managed-session callers are refused by this source path.

The historical journal phase `claimed` is retained for format compatibility; new journals also
require a verified `external_ownership` record before READY. Every continuation validates fresh
ledger status and binding plus Git/project identity; local Aegis READY alone is insufficient.
Closed attached blockers remain evidence, not work to reopen. No periodic re-claim is permitted.

### Candidate publication versus terminal closeout

`publish` prepares delivery of the exact clean, signed source candidate; it does
not close a Bead or declare live acceptance complete. Its normal source-work
ownership checks permit the primary Bead's already-attached, journal-verified
repair Beads to remain in progress for acceptance that requires merged code.
Each repair must retain the same external-owner binding, valid status and no
native assignment or routing. Unattached blockers, unresolved blockers of an
attached repair, plan/journal mismatch and identity drift still refuse. These
checks run again after signature verification. All readiness, guard, clean Git,
signature and separate hosted CI/base/review requirements remain in force.

`finish` is different: every blocking dependency must be closed before closeout
is planned or applied, and that requirement is checked again after the closeout
operation. Never remove an edge or prematurely close a repair to deliver its fix.
Neither command adds native command approval, dispatch or lifecycle authority.

The CLI serializes its source transitions in the repository's Git common directory. Before/after
Bead snapshots and pending intent are recorded around one supported status/metadata patch,
preserving every unrelated field. Exact completed writes can be reconciled after interrupted
readback; unexplained deltas stop without guessing a rollback. **This is not a distributed lock
or a scheduler reservation:** the installed Beads CLI has no status/metadata compare-and-swap.
Do not concurrently route, close, or mutate ownership of the same Bead from another controller;
fresh readback detects observed races but does not eliminate that API limitation.
Upstream atomic expected-digest updates are tracked in `ga-gurw`. Until that contract
is implemented and proven, this must not be presented as concurrent scheduler ownership.

A legacy `claimed`/`ready` journal without the new binding does not silently migrate. After
diagnosis and scoped authorization, `workflow.py adopt-external --root <exact-worktree>
--expect-bead-sha256 <digest>` checks the exact fresh Bead snapshot (SHA-256 of sorted compact
UTF-8 JSON), preserved local scaffold and journal, then binds only an unassigned, unrouted open
or in-progress Bead. It cannot clear any assignee or overwrite an existing ownership binding.
It does not assert dependency readiness, grant dispatch authority, or alter historical evidence.
Attach the declared repair Bead through `workflow.py attach` after this explicit migration.

The separately opt-in `--repair-legacy-wire` recognizes only the preserved pending intent
whose actual delta is exactly the old one-extra-JSON-encoding bug. It requires the exact fresh
Bead digest, saves the old intent and full readback append-forward, and replaces only that
binding with the typed digest token. Any additional delta or unknown binding still refuses.
It is not an automatic retry, generic metadata repair, or permission to take over native work.

Projects whose canonical checkout is deliberately dirty or parked on a long-lived branch may
declare a validated `base_ref` in the registry or local descriptor. `begin` resolves the immutable
starting commit from that ref instead of canonical `HEAD`, without checking out, cleaning, or
otherwise mutating the canonical workspace. Refresh a remote-tracking ref before `begin` when the
task explicitly requires the newest remote default branch.

For `beads-with-frozen-legacy-evidence` projects only, `begin` preserves unrelated ACTIVE folders
that are tracked and byte-unchanged at the selected base commit. They remain historical inputs,
not the current task. A new or modified unrelated ACTIVE folder still blocks. Modern Aegis
profiles retain the one-ACTIVE-folder rule.

Projects without an installed Aegis foundation use the canonical Gas City Operations
`codex-task wizard kickoff --target-dir <worktree>` adapter. The executable is shared, but the
adapter validates the selected Git worktree root and writes every session, plan, tracker, and
plan-sync artifact beneath that target. Cross-project Taskmaster kickoff is forbidden. Installed
Aegis projects continue to use `aegis kickoff`.

## Workspace placement

### Repository-local evidence layout

The existing `.codex/config.toml` `[repo_structure]` table is the single layout
contract for portable Beads source workflows. Configure it in reviewed repository
source **before** kickoff when public documentation has a separate publication policy:

```toml
[repo_structure]
sessions_root = "engdocs/workflow/sessions"
plans_root = "engdocs/workflow/plans"
plan_state_dir = "engdocs/workflow/plan-state"
work_tracking_root = "engdocs/workflow/work-tracking"
```

Kickoff, project context, active-work/ownership lookup, dependency attachment,
portable readiness, evidence logging, plan sync and archive selection use the same
resolver. Default paths remain unchanged when no overrides exist. The script,
packaged Aegis asset, self-contained gate and standalone workflow-plugin mirrors are byte-parity tested;
there is no second registry layout or provider-specific override.

All configured roots must be strings naming normalized worktree-relative directories.
Absolute paths, empty/dot/parent components, `.git` components, symlink indirection,
non-directory roots, malformed tables and unknown layout keys refuse. Changing a
layout grants no write permission, Bead ownership, worker capability or lifecycle
authority, and cannot substitute a legacy pointer for the configured authority.

This is not an implicit migration. Do not change the layout under an active scaffold
and then recreate or discard evidence to regain READY. Existing scaffold relocation
requires a separately reviewed exact-inventory transaction, preserved originals and
pointer/journal history, rollback and idempotence proof. Until that migration passes,
retain the existing layout and mark the affected workflow HOLD. Do not add public-doc
exemptions, weaken tests, or generate Taskmaster records as a workaround.

The Git common directory is the source of truth for the canonical checkout. By default, linked worktrees must be direct children of a sibling `<canonical-name>-worktrees` directory. For example, `/home/loucmane/gas-city-ops` uses `/home/loucmane/gas-city-ops-worktrees`.

The central registry may declare an absolute `worktree_root` only for projects whose established layout cannot use that convention. The context capsule blocks arbitrary and legacy worktree locations before source readiness. Do not select a worktree root from remembered paths, available sandbox roots, or caller-provided convenience paths.

## Future-project onboarding

Prefer a project-local `.gas-city-workflow.json` so onboarding travels with the repository:

```json
{
  "schema": "gas-city-workflow.project.v1",
  "id": "example",
  "repository": "owner/example",
  "rig": "example",
  "workflow_authority": "beads",
  "workflow_profile": "beads-with-aegis-evidence"
}
```

Validate it against `config/project-descriptor.schema.json`, commit it through the repository’s
normal review path, register/provision the rig separately, and run the context command with
`--check`. A descriptor-only project derives its worktree root from the canonical checkout. The
host registry entry must declare the absolute `rig_root` used for Beads export; `rig_root` is
deliberately excluded from descriptor parity because repository descriptors must remain portable.
The host registry may also bind an explicit canonical root or exceptional worktree root. A
descriptor does not discover a rig, guess a store path, grant permissions, or install
infrastructure.

For Codex, onboarding is not complete until the exact generated project hooks are loaded and
trusted in the client-local trust store. Run `managed_delegation_canary.py check` and one fresh
`apply --run-id ...` from the clean canonical Gas City Operations source after any managed-hook
release. The canary uses a synthetic descriptor-managed repository, never invokes a native
delegation tool, and must prove all of the following in one transaction: exact canonical-project
trust sufficient for Codex to expose project hooks, exact Aegis hook enumeration, exact-hash
trust through the supported app-server API, a tier-C
`native_delegation_requires_gas_city` denial, unrelated local-read non-interference, and
byte/mode/owner-exact restoration of the user config. A remembered `/hooks` click or a source-only
unit test is not live enforcement evidence. Then run `trust-project --project-root <canonical>
--run-id ...` for each installed project. That transaction retains only the exact project trust
entry and exact managed-hook hashes after a denial/allow proof and a byte-identical second
application; it restores the entire starting config on any failure.

## Shared agent roles

- Codex: executing/orchestrating lane, subject to repository and operator gates.
- Fable: independent read-only reviewer by default. It consumes the same context capsule and repository instructions; it does not need broader filesystem or command permissions to review.
- Managed workers: bounded by their explicit contract and the project’s runtime policy.

Caller identity is never authorization. Frozen request content, exact paths/digests, repository state, and the operator’s scoped authority remain the decision inputs.

## Delegation authority

Managed-project delegated work is created from a Bead through a reviewed `gc sling` route. The
shared project PreToolUse gate mechanically denies Claude `Agent`/`Task` and Codex native
create/resume tools before provider work starts. `SubagentStart` is retained only for lifecycle
evidence because it cannot block creation. A route refusal or unavailable Gas City lifecycle is a
stop condition, never permission to fall back.

An exceptional native request requires `.gas-city-delegation-exceptions.json` conforming to the
installed Aegis schema. Authorization binds the exact request digest, project, adapter, normalized
tool, `codex/*` branch, Bead, and review evidence. The complete file must be tracked and clean at
HEAD and byte-identical on the project's canonical reviewed base. Session, caller,
agent identity, advisory mode, and ordinary break-glass tokens cannot satisfy or relax it.
