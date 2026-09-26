# ga-6umo: Core launch-control hardening (specification r3)

Coordinator-written under the operator's coordinator-fix exception (2026-09-26). The implementation goes to Core
`main` (`f3856bd1`) red first, then two aegis-reviewer passes on the commit, PR, CI and merge. Deployment is a
separate reviewed package together with ga-bebv. r3 answers the two HOLD reviews of r2 (`85bf1585`). Instead of
guarding keys one by one, it inverts the rule.

## Threat

Every Gas City worker can write Beads: its own task, other Beads and session Beads. At `f3856bd1`, Core takes
launch identity and parameters from that metadata when it starts, wakes, attaches or resumes a session. A worker
can therefore widen or redirect the next session.

## The rule (r3)

**Config is the only source of launch identity and launch parameters.** For every start, wake, attach and resume
path (the reconciler, the pool, `gc session` CLI, the API, the worker handle and `internal/session`), Core
resolves:
- the agent or template;
- the provider and its chain;
- the transport;
- the command;
- `resume_command`, `resume_flag` and `resume_style`;
- env, MCP servers and MCP identity;
- pre_start and session_live.

It resolves each of these **from config only**, keyed by the session's config identity.

**Config identity** is fixed at session creation from config:
- a reconciler- or pool-created session: the template that created it;
- an operator-created session (`gc session new`, API create): the template or provider the operator named, which
  is checked against config then.

It is stored in a new creation-time field (`gc.launch_identity`: template or provider name, plus a digest of the
config it resolved to). The same guard below refuses a later change of the Bead's `template`, `provider`,
`session_kind`, `agent_name`, `session_origin`, `transport`, `mcp_identity` or `mcp_servers_snapshot`: the
metadata value is ignored for launch, and the config value is used. If the identity no longer resolves in config,
the session does not launch. It refuses with a recorded reason, and a stored command is never a fallback.

Metadata may supply only the three inputs below. Everything else Core used to read from session or work Bead
metadata for a launch is ignored for the launch. Stored copies stay display-only.

## Input 1: option overrides

- **Where.** One guard in `internal/config`: `FilterMetadataOptionOverrides(resolved, overrides, source)
  (allowed, rejected)`. Every site that turns metadata into option overrides applies it:
  - the work Bead, the trigger Bead and session `template_overrides` at start, CLI resume, API resume and the
    worker handle;
  - the config-drift hash path, `sessionCoreConfigForHashInfo` → `applyTemplateOverridesToConfigInfo`
    (`cmd/gc/session_hash.go`, `session_reconciler.go` ~5160-5186 and its callers), which filters **silently**,
    so a rejected override causes no drift and no restart loop.
- **Allow-list.** Only keys in the provider's `overridable_options` pass. The built-in default when that is unset
  is `["model", "effort"]`, intersected with the resolved schema.
- **Security choices.** Classification is per choice, by the flags it emits. A choice is security-bearing when
  its `flag_args` contain, in any form (`--flag`, `--flag=value`, clustered short flags):
  - `--sandbox`/`-s`, `--ask-for-approval`/`-a`, `--full-auto`, any `--dangerously-*`, `--yolo`;
  - `--permission-mode`, `--approval-mode`, `--add-dir`, `--include-directories`, `-C`/`--cd`, `--profile`;
  - `--settings`, `--setting-sources`, `--mcp-config`, `--allowedTools`/`--allowed-tools`, `--plugin-dir`,
    `--append-system-prompt`;
  - a `-c`/`--config` whose key is not exactly `model_reasoning_effort` or `model`.

  A metadata override may select a security-bearing choice only if the provider sets
  `allow_security_option_overrides = true`. That has no default, and ga-bebv never sets it. Codex
  `-c model_reasoning_effort=<v>` stays an ordinary choice, so codex `opt_effort` keeps working.
- **Values** must also be valid schema choices. `initial_message` is not an option and passes.
- The API permission-mode endpoint (`internal/api/huma_handlers_sessions_command.go` ~647-658) and session create
  with options (`handler_session_create.go` ~163 and ~355) refuse a security-bearing choice without the opt-in,
  instead of storing an override that would be ignored.

## Input 2: the working directory

- **Guard.** `validateSessionWorkDir(cityPath, agent, candidate, source)`. With a nil agent (a provider-kind
  session) it fails closed: the configured provider session directory, never a metadata value.
- **Where it runs.**
  - Start: at one point after every fallback and before the pre_start retarget and the stale-key probe (before
    `session_lifecycle_parallel.go` ~1040), for `work_dir`, `gc.work_dir` and `worker_dir`.
  - Resolvers: both `resolveTaskWorkDir` and `newAssignedTaskWorkDirResolver`. A rejected task Bead is skipped
    and the next one considered.
  - Resume, wake and attach: `worker_handle.go` ~574 (the MCP resolver gets the guarded directory),
    `session_runtime.go` ~353 and ~500-503, `chat.go` ~363 and ~498 (through an injected validator), and
    `cmd_session.go` ~1528, ~1586 and ~1622.
- **Empty or unresolvable input** yields the configured work_dir, never the city root by fallback.
- **Accept rule.** Resolve symlinks on the longest existing prefix. Accept only:
  - the configured work_dir, as expanded by the existing template expansion;
  - a descendant of it (**unless** the configured work_dir is the city root, in which case only the exact root is
    accepted);
  - a descendant of `workdir.WorktreesRoot(...)` for this rig and agent (the pool instance's template name);
  - a descendant of an entry of the agent's `work_dir_roots` (built-in default: empty).

  Any path with a `.git` component is rejected. The check-to-launch race (a symlink swapped after the check) is a
  stated residual.
- **Pool packs.** `gc.pack` must be a single clean segment (no `/`, `\`, `..` or NUL, not empty). A pack
  workspace is a sibling of the base, so it is accepted only when a `work_dir_roots` entry covers it.

## Input 3: session keys

`session_key` and `gc.brain_parent_sid` must match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`: no leading `-`, no
whitespace or shell metacharacters, bounded length. Every splice site checks this:
- `session_reconciler.go` ~5992-6021;
- `manager.go` ~2070 and ~2093-2098;
- `handle_lifecycle.go` ~454;
- the fork form.

A failing value is ignored and recorded: the session starts fresh, without resume or fork. After splicing, the
final command is re-checked by the classifier: no security-bearing flag may appear that the config-derived
command did not already have.

## Managed-policy check

Independently of `EmitsPermissionWarning`, a managed launch or resume command containing a `--dangerously-*` or
`--yolo` flag is refused unless the provider sets `allow_security_option_overrides = true`.
`ValidateManagedLaunchPermissionPolicy` gains this check. It runs on the final spliced command.

## Recording

Each ignored input writes one event, deduplicated per (session, source Bead, key) across patrol ticks. The event
carries the session, the source Bead id, the key and a reason. Field values are truncated to 256 bytes and
control characters escaped. A controller log line mirrors it.

## Read-only resolved print

`gc config show --providers` adds `resolved_providers`. For each provider:
- the name and its base chain;
- `options_schema` (keys, choices, values, flag_args, and whether each choice is security-bearing);
- `option_defaults`;
- `overridable_options`;
- `allow_security_option_overrides`.

It also prints each agent's `work_dir` and `work_dir_roots`. ga-bebv and the windows use it as proof.

## Tests (red first)

Each fails at `f3856bd1` and passes after, per path (start, CLI resume, API resume, worker-handle attach, wake,
`chat.go`):
- **Identity:**
  - a changed `template`, `provider`, `session_kind`, `agent_name`, `transport`, `mcp_identity` or
    `mcp_servers_snapshot` is ignored;
  - a stored `command` or `resume_command` is never used, including on a provider without `resume_command` and
    through the API error branch;
  - a config-less session refuses.
- **Options:**
  - codex and claude `opt_permission_mode=unrestricted`, `opt_worktree_access`, `opt_worklog_access` and
    `managed_worktree_access` are ignored;
  - codex and claude `opt_effort` and `opt_model` apply (the ga-1mj flow);
  - the classifier table, including the `=` and clustered forms;
  - a rejected override causes no config drift or restart across ticks;
  - the API endpoints refuse.
- **work_dir:**
  - each of the three keys and both resolvers are covered;
  - symlink escape, a `.git` component and `gc.pack=../x` are rejected;
  - a nonexistent candidate is handled;
  - an empty value gives the configured work_dir, never the city root;
  - nil-agent fail-closed;
  - a rejected task Bead is skipped for the next one;
  - accepted: the configured directory, a descendant, `WorktreesRoot` and `work_dir_roots`.
- **Keys:** leading dash, `;`, whitespace and length for `session_key` and `brain_parent_sid`; the post-splice
  re-check.
- **Managed policy:** codex `--dangerously-bypass-approvals-and-sandbox` is refused without the opt-in.
- **Events:** one per (session, Bead, key) across ticks, bounded.
- **Existing tests** that encode the old behaviour are updated by name, with the reason in the commit:
  `template_resolve_phase2_test.go:73`, `cmd_session_test.go:1068-1086`, `session_reconciler_test.go:11255-11324`
  and `session_reasoning_effort_test.go`. The rest of the suite stays green.

## Known residual paths (follow-up Beads, not closed here)

- A worker creating a new session Bead: it gets a config identity only through the operator create path. A
  worker-created session Bead with no creation-time `gc.launch_identity` refuses to launch here, but this Bead
  does not audit every creation path.
- An open Bead routed through `gc.routed_to` to a more privileged pool.
- Controller API reach from a sandbox.
- The check-to-launch symlink race.

Workers stay inside reviewed windows until these are closed.

## Upgrade

A session Bead created before this change has no `gc.launch_identity`, and trusting its metadata to supply one
would reopen the hole. The deployment precondition (ga-bebv) is therefore: the city is suspended, and no session
Bead is open. Every session is recreated under the new Core. A test proves that a session without
`gc.launch_identity` refuses.

## Out of scope

city.toml, packs and live state. ga-bebv carries the replace-mode schemas, `work_dir_roots`, any
`overridable_options` and the deployment.
