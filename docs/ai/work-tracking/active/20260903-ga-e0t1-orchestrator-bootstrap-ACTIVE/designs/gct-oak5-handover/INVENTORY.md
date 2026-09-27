# gct-oak5 handover — inventory (for plan r9 `54553f79`)

Read-only inventory taken on 2026-09-27 between 15:15 and 15:35 CEST (13:15–13:35Z), from the canonical Operations seat. Sources:
- deployed Core `f45a6262`, read with `git show` in the Core rig checkout;
- the deployed core pack at cache `69fe9a2e…` (`internal/bootstrap/packs/core`, `examples/bd/dolt`), and the city's own `orders/`;
- the live stores, through `gc … bd list|export|show|history` in the AGENTS.md environment with `GIT_OPTIONAL_LOCKS=0`;
- `gc order list|show|check|history`, `gc status`, `gc rig list`;
- lstat and file reads of past lane worktrees (`gas-city-template-worktrees/gct-mbg6`) and the ga-3oa7 intake manifest. There was no git in any Template worktree.

Items marked **PENDING** need a live probe, which is described at the end.

## 1. Routing configuration

- No `sling_query`, `session_template` or `work_query` exists in `city.toml`, `managed/*.toml`, `pack.toml`, or the pack's `implementation-worker/agent.toml`. That file sets only `description`, `scope = "rig"` and `fallback = true`. So the defaults apply to both lanes: the plan's second-route preconditions hold.
- **Hook store list** (`cmd/gc/hook_cross_store.go:39-145`). Both lanes are rig-scoped, and their session alias is `gas-city-template/<name>`, so `rigScopedHookRig` returns `gas-city-template`.
  - The claim queries the Template rig store first, then the agent's own (rig-scoped) work-query store, which is also the Template store. The city store comes last.
  - `appendRigHookStores`, the all-rig federation, applies only to city-scoped agents, so it does not apply here.
  - **Per-lane store set:** {Template rig store, city store}. The plan's snapshot still covers every reachable store for the projection.

## 2. Claim, close and release writes (bd 1.2.2, Core `f45a6262`)

- **The claim** (`cmd_hook_claim.go:513-552`, compare-and-skip):
  - the assignee, which is the session name, and status `in_progress`;
  - `gc.work_branch`, only when `ResolveWorkBranch` returns a branch that differs from the Bead's value;
  - `gc.session_id` and `gc.session_name`.

  Nothing else. The ga-3oa7 closed row confirms it: `gc.session_id=ci-yi6m4`, `gc.session_name=operations-candidate-worker-ci-yi6m4`, `gc.work_branch` set.
- **The worker's own `bd close`** writes:
  - `status=closed`, `closed_at` and `updated_at`;
  - `close_reason`, only with `--reason`.

  **It keeps the assignee and every claim key.** On ga-3oa7, the closed row still has `assignee=operations-candidate-worker-ci-yi6m4` after the session was drained. `closed_by_session` does not exist in either export's key set.
- **The orphan release** (`pool_session_name.go:670-780`, `releasePoolAssignment*`) is what clears the assignee. It runs when the session dies while the Bead is still `in_progress`. It writes:
  - `status=open` and `assignee=""`;
  - empty `gc.continuation_group` and `gc.session_affinity` (from `clearedSessionAffinityMetadata`).

  That is how gct-mbg6's row came to hold those two empty keys at 07:49:23Z, the moment session `ci-sg37g` closed. They do not come from the claim.
- **History.** `bd history <id> --json` returns whole-row versions with `Committer: "beads"` and no actor. So the close actor is **not recordable**, and the plan's conditional "if the actor records the session identity" does not apply.
- **The lane prompts:**
  - The Claude lane's prompt source, per `gc config explain`, is `8b0f193e…/gascity/roles/agents/implementation-worker/prompt.template.md`, from pack commit `cc9e72b2`. The same source gives `provider = claude-template-candidate` and `max_active_sessions = 1`. The codex lane's prompt is `/home/loucmane/gas-city-native/agents/codex/prompt.template.md`.
  - The Claude pack prompt sets `gc.outcome=pass` only "for a bead that asks for close metadata". On an unrecoverable failure it sets `gc.outcome=fail` and `gc.failure_class`.
  - The codex prompt closes with `gc bd close <id> [--reason …]` and no metadata.
  - Neither calls `gc bd heartbeat`, and neither sets `gc.work_outcome`.
  - The step briefs ask for no close metadata. So `gc.outcome` is absent on success, and the failure keys mean a failed step.

## 3. Session Beads (city store)

- Every pool start creates a new session Bead: 16 for `gas-city-template/codex` and 4 for `gas-city-template/gc.implementation-worker`, with no reuse. Each has labels `agent:<template>` and `gc:session`, and `session_origin=ephemeral`, `pool_managed=true`.
- **The key set is not fixed per lifecycle.** Optional keys depend on events, for example `idle_claim_nudge_*`, `held_until`, `pin_awake`, `last_nudge_delivered_at`, `drain_at` and `core_hash_breakdown`. The union over each lane template's rows is the admissible superset: codex 70 keys over 16 rows; Claude Template lane 55 keys over 4 rows, with the Ops candidate lane at 56 over 3.
- **Identity keys, pinned by value:** `template`, `alias`, `agent_name`, `canonical_instance_name`, `session_name`, `work_dir`, `gc.work_dir`, `gc.trigger_bead_id`, `gc.trigger_bead_store_ref=rig:gas-city-template`, `currently_processing_bead_id`, `provider`, and the labels.
- **End states observed:**
  - **Claude lane**, the ga-3oa7 teardown: `closed`, `state=drained`, `state_reason=drain-ack-stop-pending`, `close_reason="session drained: pool slot retired by reconciler"`.
  - **Codex lane**, the gct-mbg6 teardown: `closed`, `state=awake`, `state_reason=creation_complete`, no `close_reason`.

  Each lane's final state is pinned from its source window's teardown path.
- **Per window, one nudge row** is created in the city store by nudge-on-route: `gc:nudge`, `agent:<template>`, with metadata `agent`/`session_id`/`nudge_id`. On gct-mbg6 it was `ci-wisp-8l6m`. It carries no assignee, `gc.routed_to` or `gc.run_target`, so it is outside the projection.
- **Worker mail.** Workers send mail to `mayor`: gct-mbg6 sent `READY FOR SIGNING`. These are city-store messages with `assignee=mayor`, outside the projection.
  - No open message is addressed to either lane: all 9 open rows mentioning the codex lane are its own sent mail.
  - The codex and Claude hooks run `mail check --inject`, which finds nothing for the lane.

## 4. Orders and patrols

- `gc order list --rig gas-city-template` shows 34 orders. Sources are the core pack `69fe9a2e…/internal/bootstrap/packs/core/orders/*` (15), `69fe9a2e…/examples/bd/dolt/orders/*` (6), and `city/orders/*` (13).
- **No order has executed since 2026-09-12 13:49 CEST (11:49Z), except `nudge-on-route`.** `gc order check` reports every cooldown order due, with about 361 h elapsed.
  - The reason is `gc status`: the city is **Suspended: yes**, so the controller dispatches no orders.
  - Inside a window, the reused overlay skips every order except `nudge-on-route`. Its last run was at 09:42 CEST (07:42Z) on 2026-09-27, during the gct-mbg6 window.
  - **Consequence:** reaper, wisp-compact, orphan-sweep, prune-branches, cross-rig-deps, gate-sweep, order-tracking-sweep, nudge-mail-sweep, the dolt/mol-dog orders and the attention and mail-wake chain all do not run across the chain, as long as the city stays suspended between windows and each window keeps the overlay.
- **Row writers, if any did run:**
  - reaper and wisp-compact (row age);
  - orphan-sweep (resets orphaned `in_progress` rows);
  - cross-rig-deps (only `external:` deps; the Template store has none);
  - gate-sweep (gates; the Template store has none);
  - order-tracking-sweep and nudge-mail-sweep (city store only).
- `prune-branches` runs `git fetch --prune origin` and deletes only merged or orphaned `gc/*` branches, in each rig path. The Template rig path is `/home/loucmane/gas-city-native`, not the canonical Template. The handover branch `codex/gct-oak5-handover-proof` is not `gc/*`.
- **The Template store** has no ephemeral rows, `gc:` labels, order-tracking rows, gates or `external:` deps. Its dependency types are `tracks` 171, `blocks` 167, `discovered-from` 2, `related` 1 and `parent-child` 1.

## 5. Snapshot method

- `bd export --all` per store is deterministic: two consecutive Template exports were byte-identical (`a5c44757…`, 261 rows).
- It includes labels, dependencies, comments and metadata. In the city store it covers exactly the rows of `bd list --all --include-infra --limit 0` (2648 = 2648), including 253 ephemeral rows and 1972 session Beads.
- **Normalisation:** none is needed for a static store. Rows are compared by id with full field equality.

## 6. The stale workflow `gct-wn1m`

- **Live members:** `gct-wn1m` (open workflow, routed `gc.run-operator`), `gct-20mc` (open, ralph, control-dispatcher), `gct-af6u` (open, routed `gas-city-template/gc.implementation-worker`, unassigned), `gct-svpm` (open, run-operator), `gct-dh6u` (open, workflow-finalize, control-dispatcher) and `gct-v7yb` (open spec). `gct-zkfz` is already closed.
- **Lane queues now:**
  - the Claude lane's eligible set is {`gct-af6u`}, which is why the operator chose to close it;
  - the codex lane's is empty;
  - no non-closed Template row carries `needs/operator`.

## 7. The C2 test command

- BASE ignores only `.gc/`, `.beads/*` except `!.beads/identity.toml`, `.beads/proxieddb/`, `.beads-credential-key`, `.dolt/`, `*.db`, `__pycache__/` and `*.py[cod]`. So `.oak5-c2-tmp/` is neither tracked nor ignored.
- BASE has no `pyproject.toml`, `pytest.ini`, `setup.cfg` or `tox.ini`. So pytest's default `norecursedirs` applies, and it contains `.*`, which skips `.oak5-c2-tmp/`.
- CI runs `python -m pytest -q` on Python 3.12. Locally, `/usr/bin/python3.12` has pytest 7.4.4 from `dist-packages`. The canonical `.venv` is 3.11 and is not used.
- **PENDING (probe B):**
  - the exact command under the live lane policy and sandbox;
  - that the tests import the worktree's code;
  - that deleting the temp directory, including read-only files under `basetemp`, is permitted.

## 8. Runtime entries a lane session writes into its worktree

**Sources in Core `f45a6262`:**
- `.gc/settings.json` is the city's `.gc/settings.json`, projected into the workdir (`cmd/gc/cmd_start.go:1208-1290`). On gct-mbg6 it is byte-equal to the live city file (`fdd32781…`).
- `.gc/scripts/mol-dog-stale-db.sh` (0755) is byte-equal to the city's `.gc/scripts/` copy (`f201cd28…`).
- `.gc/tmp/skill-catalog-<qualified name with / as _>.b64` (0600) is the base64 skill-catalog snapshot, overwritten on every spawn (`cmd/gc/skill_integration.go:403-460`). A leftover `skill-catalog-*.tmp` means an interrupted write.
- **The skill sink** is `.claude/skills` for the Claude family and `.agents/skills` for codex (`internal/materialize/skills.go:73-79`). It holds one symlink per effective skill into the pinned pack cache, plus `.gc-skill-ownership.json` (`{"targets":{name:target}}`).
  - The materializer replaces or removes only symlinks it owns.
  - It leaves regular files and directories alone (`skills.go:543-675`), apart from exact v0.15.0 `gc-<topic>` stub directories.
  - BASE's tracked `.claude/skills/` entries are the obsidian, defuddle and json-canvas skills and `LICENSE-obsidian-skills`. None is a `gc-*` stub, so none is touched.
- **Codex only:** `.codex/hooks.json` (0644), written by the codex overlay and finalised by `FinalizeProjectedCodexHooks` (`internal/hooks/hooks.go:199-240, 655-700`). On gct-mbg6 it is 1238 bytes, `55e21a9d…`, with the city path and `gc` binary path baked in.
- **The Claude family** installs its hooks at city level only (`installClaude(fs, cityDir)`). It writes nothing else into the workdir.
- **Claude Code** leaves an empty `.claude/.cc-writes/` directory, mode 0700. Empty directories are outside the image.

**Observed sets:**

| Lane | Entry | Type and mode | Tracked or ignored at BASE |
| --- | --- | --- | --- |
| both | `.gc/settings.json` | file 0644, city bytes | ignored (`.gc/`) |
| both | `.gc/scripts/mol-dog-stale-db.sh` | file 0755, city bytes | ignored |
| Claude | `.gc/tmp/skill-catalog-gas-city-template_gc.implementation-worker.b64` | file 0600 | ignored |
| codex | `.gc/tmp/skill-catalog-gas-city-template_codex.b64` | file 0600 | ignored |
| Claude | `.claude/skills/.gc-skill-ownership.json` | file 0644 | **untracked** |
| Claude | `.claude/skills/core.gc-{agents,city,dashboard,dispatch,mail,rigs,work}`, `.claude/skills/gascity.mayor` | symlinks into `69fe9a2e…/internal/bootstrap/packs/core/skills/gc-*` and `954ed149…/gascity/skills/mayor` | **untracked** |
| codex | `.agents/skills/.gc-skill-ownership.json` and the same eight links under `.agents/skills/` | as above | **untracked** |
| codex | `.codex/hooks.json` | file 0644, pinned bytes | **untracked** |

The Claude rows come from the ga-3oa7 intake manifest (the Ops candidate lane, the same Claude family and pack), and the codex rows from gct-mbg6. The Template Claude lane's exact set is pinned when C1 first writes it; see r10.

**Consequence for the plan:**
- rule 3 allowed "admitted runtime entries", but rule 2 ("no other paths") and rule 4 ("no ignored entries at all") did not;
- the image tool refuses links;
- the claim that `.claude/scripts/__pycache__` does not arise holds for the Template, because BASE tracks no `.claude/scripts/`.

This is resolved by plan r10.

## 9. PENDING live probes

- **Probe A: startup git.** The real Claude wrapper argv and the real codex argv, each started once in a scratch linked worktree of a throwaway clone (never the canonical Template), with the admin `index` hashed before and after. This decides whether a harness rewrites index extensions. The claim's `ResolveWorkBranch` also runs git in the worktree unsandboxed.
- **Probe B: the C2 test command.** Under the live Claude lane policy and sandbox in the same scratch clone: the exact env-variable form, the import of the worktree's code, and deletion of `.oak5-c2-tmp/`.

Both need a reviewed job, because they launch provider sessions: Claude cost, and Codex quota for probe A. They run before the C1 window package is reviewed.
