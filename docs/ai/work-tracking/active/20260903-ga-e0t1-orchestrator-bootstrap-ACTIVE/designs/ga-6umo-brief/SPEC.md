# ga-6umo: Core launch-parameter hardening (specification r5, the narrow fix)

The coordinator writes this under the operator's coordinator-fix exception (2026-09-26). The implementation goes
to Core `main` (`f3856bd1`): red first, two aegis-reviewer passes on the commit, then PR, CI and merge.
Deployment is a separate reviewed package together with ga-bebv.

## Scope (r4)

Three review rounds (r1 `6fd6a904`, r2 `85bf1585`, r3 `9ddeb5f1`) showed the root cause: Core has no
authorization boundary between workers and the operator. Workers run `gc` and `bd` with the operator's
authority, so they can rewrite any session Bead field and create sessions of any template with
`gc session new`. Closing that needs a Core authorization model, and whether to build it now is an open
operator decision.

r4 specifies only the fixes that either decision needs: the ones that stop a single worker-written field on a
work, trigger or session Bead from widening an existing session's launch. It does not claim to stop a worker
that rewrites a session's identity or creates a new session. That is the declared residual below.

The operator chose this narrow fix on 2026-09-26. r5 answers the r4 reviews (`d5c228cc`, A and B HOLD, the same
missed site), adds the mechanical guarantee below, and closes the definition gaps.

## Mechanical guarantee (r5)

Site lists kept missing sites. So every read of a launch-relevant session or work Bead metadata key goes through
guarded accessors in one package (`internal/session/launchmeta`):
- `command`, `resume_command`, `resume_flag`, `resume_style`;
- `template_overrides` and `opt_*`;
- `work_dir`, `gc.work_dir`, `worker_dir`;
- `session_key`, `gc.brain_parent_sid`.

A source-scan test (`launchmeta_scan_test.go`) parses every non-test Go file of the module. It fails if any code
outside that package, and outside an explicit allow-list of display-only and write sites (each entry named with a
reason), reads one of those keys from a metadata map by literal or constant. A missed launch site therefore fails
CI instead of shipping.

## Rule

Worker-writable metadata may select among declared non-security choices. It may never add a security-bearing
flag, relocate a session outside its allowed roots, or replace the config-derived command. Input that fails the
rule is ignored, never fatal. The configured value is used, and one deduplicated, bounded event is recorded.

## 1. Option overrides: one guard, default deny

- **Where.** `config.FilterMetadataOptionOverrides(resolved, overrides, source) (allowed, rejected)`, applied at
  every site that turns metadata into option overrides, and silently in the drift-hash path so a rejected
  override causes no restart loop:
  - `session_reconciler.go:5542-5601` (the work and trigger Beads);
  - `session_lifecycle_parallel.go:984-988` and `:1264-1295` (session `template_overrides`);
  - `cmd_session.go:1545-1555`;
  - `internal/api/session_runtime.go:369-373`, `:391-396` and `:492-496` (the worker-runtime resume, missed in
    r4);
  - `worker_handle.go:582-588` and `:671-677`;
  - `session_hash.go:14-18` → `session_reconciler.go:5160-5186`;
  - the dashboard options view (`internal/api/handler_sessions.go:161-176`), which shows only the filtered
    overrides;
  - the create paths, which refuse a security-bearing choice at create time: the Huma agent and provider create
    (`huma_handlers_sessions_command.go:76-86`, `:116`, `:255-268`, `:297-306`) and the legacy handlers
    (`handler_session_create.go:101-117`, `:280-299`, `:338`, `:355`).
- **Not options.** `initial_message` and every other key of `template_overrides` that is not in the provider's
  options schema passes unchanged. The filter touches only schema option keys.
- **Inheritance.** `overridable_options` and `allow_security_option_overrides` are inherited along a
  `base = "provider:…"` chain, and a child that sets either replaces the inherited value.
- **Allow-list.** Only keys in the provider's `overridable_options` pass. The built-in default when it is unset
  is `["model", "effort"]`. Within an allowed key, a choice passes only when every element of its `flag_args` is
  in the benign set:
  - `--model`/`-m` with a value;
  - `--effort` with a value;
  - `-c`/`--config` whose value starts with `model_reasoning_effort=` or `model=`.

  Everything else is security-bearing and is refused unless the provider sets
  `allow_security_option_overrides = true`, which has no default. Codex effort (`-c model_reasoning_effort=…`)
  and claude and codex model and effort therefore keep working (the ga-1mj flow).
- **API endpoints.** The permission-mode endpoint (`huma_handlers_sessions_command.go:647-658`) and create with
  options (`handler_session_create.go:163`, `:355`) refuse a security-bearing choice without the opt-in. This is
  a stated behaviour change: codex `attended` through the API then needs the opt-in.

## 2. Working directory: one guard, per-agent subtree

- **Guard.** `validateSessionWorkDir(cityPath, agent, instance, candidate, source)`:
  - it runs after every fallback, before the pre_start retarget and the stale-key probe
    (`session_lifecycle_parallel.go:1029-1040`);
  - it covers `work_dir`, `gc.work_dir` and `worker_dir`, both resolvers (`session_reconciler.go:5464-5497` and
    `:5610-5640`, where a rejected task Bead is skipped and the next one considered), and the resume, wake and
    attach paths: `worker_handle.go:574-578` (MCP gets the guarded directory), `session_runtime.go:353` and
    `:500-503`, `chat.go:363-365` and `:498-500` (through an injected validator), and `cmd_session.go:1528`,
    `:1586` and `:1622`.
- **Empty input.** An empty or unresolvable candidate yields the configured work_dir, never a city-root fallback
  for an agent session.
- **Nil agent.** A provider-kind session is created in the city root (`handler_session_create.go:317`), so it
  accepts only the exact city root, never a descendant, and refuses anything else.
- **Accept.** The candidate and every accepted base (the configured work_dir, the subtree and `work_dir_roots`
  entries) are resolved the same way: symlinks on the longest existing prefix. Containment is by path component,
  never a string prefix, so `/root-evil` is not under `/root`. Any `.git` component rejects, compared
  case-insensitively. Accepted are:
  - the configured work_dir;
  - its descendants, except when it is the city root, where only the exact root is accepted;
  - a descendant of the per-agent worktree subtree, defined as the expansion of the agent's configured
    `work_dir` template when that template lies under `workdir.WorktreesRoot(cityPath)`, taken up to and
    including its first per-instance component. The per-instance variables are `{{.Agent}}` and `{{.AgentBase}}`
    (the pool instance or named identity), expanded from the session's config-derived instance. A template with
    no per-instance component gets no subtree beyond its exact expansion and its descendants. A sibling agent's or
    rig's subtree is rejected, with a negative test;
  - a descendant of an agent `work_dir_roots` entry (built-in default: empty).
- **Pool packs.** `gc.pack` must be a single clean segment (no `/`, `\`, `..` or NUL, not empty). A pack sibling
  workspace needs a `work_dir_roots` entry.

## 3. Stored commands and resume keys

- **Never reused.** A stored `command`, `resume_command`, `resume_flag` or `resume_style` on a session Bead is
  never used for a launch. Every path rebuilds from the resolved provider plus guarded overrides:
  - `worker_handle.go:582`, `:649-650` and `:664-727` (including the claude `--settings` rule);
  - `session_runtime.go:363-367`, `:383-443` (including the error branches), `:491` and `:505-506`;
  - `manager.go:2067-2100`;
  - `handle_lifecycle.go:433-472`;
  - `cmd_session.go:1525-1625`, including the stored-command resume at `:1526-1528`;
  - `session_runtime.go:349-353`, the nil-provider stored resume;
  - `chat.go:125-136` (`freshStartCommandFromMetadata`) and `:167-210` (`retryFreshStartAfterStaleKey`). The
    stale-key retry strips the resume form using the resolved provider's `ResumeFlag` and `ResumeStyle`, never
    Bead metadata, and §5 re-runs on the retry command.
- **Rebuild parity.** A rebuild goes through the same builder the create path uses (`template_resolve.go:200-218`,
  including the claude settings projection and provider hook arguments), so nothing the create path adds is lost.
- **No resolved provider.** The session refuses with a recorded reason.

## 4. Session keys

- **Grammar.** `session_key` and `gc.brain_parent_sid` must match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`. The
  check runs at every splice site: `session_reconciler.go:5992-6021`, `manager.go:2070` and `:2093-2098`,
  `handle_lifecycle.go:454`, and the fork form.
  - A failing `session_key` is ignored and recorded, and the session starts fresh.
  - A failing `gc.brain_parent_sid` refuses the fork loudly, keeping the fork invariant
    (`session_lifecycle_parallel.go:1991-2035`: never silently degrade a fork to fresh).
  - The grammar check runs before the stale-key probe (`session_lifecycle_parallel.go:1055-1057`).
- **Post-splice check.** The baseline is the config-derived command plus the provider's own resume, session-id
  and fork forms (`--resume`, `--session-id`, `--fork-session`, the `resume` subcommand) as the resolved provider
  declares them. After splicing, the final command may contain no other flag outside the §1 benign set that the
  baseline does not already contain.

## 5. Managed-policy check

**What it refuses.** Independently of `EmitsPermissionWarning`, a managed launch or resume command is refused if
its argv contains an unrestricted-mode encoding from a closed list, unless the provider sets
`allow_security_option_overrides = true`. The list, with each form also matched as `--flag=value`:
- any flag containing `dangerously`;
- `--yolo`;
- `--approval-mode yolo`;
- `--permission-mode bypassPermissions`;
- `--sandbox danger-full-access`.

The check runs on the final spliced command, including the stale-key retry.

**Definitions.** A managed launch is any session start, wake, attach or resume that Core builds for an agent or
provider session. `gc` never checks a command an operator runs by hand.

**Behaviour change, stated.**
- The builtin claude and codex default is `permission_mode=unrestricted`. A city that relies on it stops
  launching until it sets the opt-in or a narrower default.
- The live city overrides the default for every provider, so it is unaffected.
- `template_resolve_phase2_test.go:61` and `:73` are updated by name.

## 6. Recording and the read-only print

- **Events.** Dedupe per (session, source Bead, key) is kept in a bounded LRU of at most 4096 entries in the
  controller runtime directory, persisted across restarts.
  - The file is parsed with a size bound. A corrupt or oversized file is discarded, never trusted.
  - Events raised outside the controller (`gc session attach`, the API) dedupe per process only.
  - Event values are truncated to 256 bytes with control characters escaped, and a controller log line mirrors
    each event.
- **Print.** `gc config show --providers` adds `resolved_providers`:
  - the base chain;
  - `options_schema`, with each choice marked benign or security-bearing;
  - `option_defaults`;
  - `overridable_options`;
  - `allow_security_option_overrides`.

  It also prints each agent's `work_dir`, derived worktree subtree and `work_dir_roots`.

## Tests (red first; each fails at f3856bd1)

- **Options.** On each site above:
  - codex and claude `permission_mode=unrestricted`, `worktree_access`, `worklog_access` and
    `managed_worktree_access` are ignored;
  - codex and claude `opt_model` and `opt_effort` apply;
  - the benign-set table covers `=` and clustered forms;
  - a rejected override causes no drift or restart across ticks;
  - the API endpoints refuse.
- **Working directory.**
  - Each key, both resolvers and each resume path are covered.
  - Rejected: symlink escape, a `.git` component, a sibling agent's subtree and `gc.pack=../x`.
  - A nonexistent candidate is handled; an empty candidate gives the configured work_dir; a nil agent fails
    closed; a rejected task Bead is skipped.
  - Accepted: the configured work_dir, a descendant, the per-agent subtree and a `work_dir_roots` entry.
- **Stored.** On each path, including a provider without `resume_command` and the API error branch, a stored
  command or resume key is never used. A config-less session refuses.
- **Keys.** A leading dash, `;`, whitespace and over-length values are rejected for `session_key` and
  `brain_parent_sid`, followed by the post-splice re-check.
- **Managed.** Codex `--dangerously-bypass-approvals-and-sandbox` and claude
  `--allow-dangerously-skip-permissions` are refused without the opt-in.
- **Events.** One per (session, Bead, key) across ticks and a controller restart, bounded.
- **r5 additions:**
  - `session_runtime.go:492-496` with a `worktree_access` or `worklog_access` override is filtered;
  - the stale-key retry ignores a stored `resume_flag` of `--settings <path> --resume` and never uses a stored
    `command`;
  - the nil-provider resume refuses;
  - an invalid `brain_parent_sid` refuses the fork;
  - `/root-evil` and `.GIT` are rejected;
  - the dashboard view shows filtered overrides;
  - `initial_message` survives the filter;
  - the closed unrestricted list, including `=` forms;
  - the source-scan test itself, with a planted direct read that must fail it.
- **Existing tests** that encode the old behaviour are updated by name, with the reason in the commit:
  `template_resolve_phase2_test.go:61` and `:73`, `cmd_session_test.go:1068-1086`,
  `session_reconciler_test.go:11255-11324` and `session_reasoning_effort_test.go`. The rest of the suite stays
  green.

## Declared residual (the operator's narrow-fix decision; not closed by r5)

A worker that can run `gc` and `bd` can still:
- rewrite a session Bead's identity fields (`template`, `provider`, `session_kind`, `agent_name`, `alias`,
  `session_name`, `transport`, `mcp_identity`, `mcp_servers_snapshot`) to make an existing session resolve a more
  privileged config;
- create a session of any configured template with `gc session new`, or through manual-origin rediscovery;
- route a Bead to a more privileged pool with `gc.routed_to`;
- substitute another session's valid `session_key` or `brain_parent_sid` to resume or fork its transcript;
- reach the controller API, if it is reachable from its sandbox;
- race a symlink swap between the check and the launch;
- write fields outside the launch-flag class that reach another session's first start without widening it:
  `template_overrides.initial_message` and `wake_mode`, and `worker_dir`, which drives auto-prune of clean trees
  under `.gc/worktrees`.

Closing these needs a Core authorization model (controller-attested session identity and an operator-only
creation channel), tracked as its own Bead. Until then Gas City workers are semi-trusted: they are routed only
inside reviewed windows, and the reviewed diff plus CI is the control.

## Out of scope

city.toml, packs and live state. ga-bebv carries the replace-mode schemas, `work_dir_roots`,
`overridable_options` and the deployment. r5 creates no identity field, so it needs no session-Bead upgrade
step.
