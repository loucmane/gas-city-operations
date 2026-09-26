# ga-6umo: Core launch-parameter hardening (specification r6: one launch gate)

The coordinator writes this under the operator's coordinator-fix exception (2026-09-26). The implementation goes
to Core `main` (`f3856bd1`): red first, two aegis-reviewer passes on the commit, then PR, CI and merge.
Deployment is a separate reviewed package with ga-bebv.

**Scope.** Narrow, by operator decision: stop any single worker-written field on a work, trigger or session Bead
from widening an existing session's launch. Identity rewrite, session creation, routing, session-key substitution,
API reach and the symlink race stay the declared residual (ga-5eix).

## Why r6 changes shape

Five spec rounds each found launch sites that the previous list missed. In r5, the metadata reaches launch code
through the `session.Info` codec (`internal/session/info_store.go:38-40`, `info_codec.go`) and the worker factory
(`internal/worker/factory.go:165-192`). A source scan cannot see those paths, and whenever the provider does not
resolve, the stored `command`, `work_dir` and resume fields reach the launch unchecked.

r6 therefore puts the security control at the one boundary every launch crosses: `runtime.Provider.Start(ctx,
name, cfg)`. It is enforced by a gate that wraps the provider at the single construction seam,
`resolveSessionTransportProvider` (`cmd/gc/providers.go:260-292`). The CLI, the controller and its in-process API
all build their session provider there. Whatever path the metadata took, the final argv and working directory are
checked against config. The upstream fixes stay as defence in depth. They are listed below but are not the
guarantee.

## 1. The launch gate (the guarantee)

`launchGate` wraps the provider returned by `resolveSessionTransportProvider`: the auto, acp and base providers
alike. Every other provider method delegates unchanged.

On `Start(ctx, name, cfg)`, the gate:
1. **Resolves the session identity** by runtime session name from the session store: template (agent) or
   provider name. Trusting the Bead for identity is the declared residual. With no session Bead, or with an
   identity that does not resolve in the current config, the start is refused.
2. **Computes the baseline from config only:**
   - the resolved provider's command and args;
   - the flag_args of the agent's effective option defaults;
   - the provider's declared resume, session-id and fork forms (`resume_flag`, `resume_style`,
     `resume_command`, `session_id_flag`, `--fork-session`).
3. **Classifies the final argv** (`shellquote.Split(cfg.Command)`, and for ACP the resolved ACP command). Every
   flag outside the benign set is security-bearing:
   - the benign set is `--model`/`-m` with a value, `--effort` with a value, and `-c`/`--config` whose value starts
     with `model_reasoning_effort=` or `model=`;
   - forms are recognised as `--flag value`, `--flag=value` and clustered short flags;
   - the session key or parent id in a provider-declared resume or fork position is not a flag.
4. **Refuses the start** if any of these holds:
   - a security-bearing flag and value pair is present in the argv but absent from the baseline. Adding flags
     widens; dropping baseline flags counts too, because removing `--settings`, `--sandbox` or
     `--ask-for-approval` widens a launch just as adding them does. The flag and value pairs of the baseline and
     the argv must be equal;
   - the argv's executable differs from the baseline's;
   - `cfg.WorkDir` fails the §2 guard;
   - the argv carries an unrestricted-mode encoding from the closed list without the provider's
     `allow_security_option_overrides = true`: any flag containing `dangerously`, `--yolo`, `-y`,
     `--approval-mode yolo`, `--permission-mode bypassPermissions`, `--sandbox`/`-s danger-full-access`, or `-c`
     with a value starting `sandbox_mode=` and containing `danger-full-access`, each also as `--flag=value`.

A refusal returns an error the caller already handles as a failed start, and records one event.
`EmitsPermissionWarning` does not matter here.

**Stated behaviour change.** Builtin provider profiles whose base args carry `--yolo` or `--dangerously-allow-all`
(`internal/worker/builtin/profiles.go:392`, `:404`, `:473`, `:506`), and the builtin claude and codex default
`permission_mode=unrestricted`, stop launching without the opt-in. The live city overrides every such default and
uses none of those profiles, so it is unaffected.

**Opt-in.** `allow_security_option_overrides = true` on a provider lets the gate accept security flags that
differ from the baseline. It has no default and is never set by ga-bebv.

**Pre-start.** `cfg.PreStart` and `cfg.SessionLive` come from config through template resolution. The gate checks
that each command matches the config-derived list for the identity, after work-dir retargeting. It refuses
otherwise.

## 2. Working-directory guard

`validateSessionWorkDir(cityPath, agent, instance, candidate)`, used by the gate and by the upstream fixes.

- **Resolution.** The candidate and every accepted base are resolved the same way: symlinks on the longest
  existing prefix, then containment by path component (never a string prefix). Any `.git` component rejects,
  compared case-insensitively.
- **Accepted:**
  - the configured work_dir and its descendants, except when it is the city root, where only the exact root is
    accepted;
  - the per-agent worktree subtree: the agent's `work_dir` template under `workdir.WorktreesRoot(cityPath)`,
    expanded up to and including the path components produced by its first `{{.Agent}}` or `{{.AgentBase}}`
    variable (a qualified `rig/name` spans two components, and both are included), from the session's instance. A
    template without such a variable gets its exact expansion and descendants;
  - a descendant of an agent `work_dir_roots` entry (built-in default: empty).
- **Nil agent.** A provider-kind session (the API creates these in the city root, `handler_session_create.go:317`)
  accepts only the exact city root. A session whose config identity is an agent but whose metadata claims
  provider kind (`real_world_app_session_kind=provider`) is refused, because its identity no longer matches.
- **Pool packs.** `gc.pack` and `gc.pack_workspace` (`build_desired_state.go:1694-1705`, `:3203-3222`) must each
  be a single clean segment, and a pack sibling workspace needs a `work_dir_roots` entry.

## 3. Defence in depth upstream (not the guarantee)

These make the common paths do the right thing, so the gate refuses rarely:
- **Option guard.** `config.FilterMetadataOptionOverrides` is used wherever metadata becomes option overrides.
  The default allow-list is `overridable_options = ["model","effort"]`, inherited along `provider:` chains and
  replaced by a child. Security-bearing choices need the opt-in, and non-option keys such as `initial_message`
  pass. It covers:
  - `session_reconciler.go:5542-5601`;
  - `session_lifecycle_parallel.go:984-988` and `:1264-1295`;
  - `worker_handle.go:582-588` and `:671-677`;
  - `session_runtime.go:369-373`, `:391-396` and `:492-496`;
  - the drift hash, `session_hash.go:14-18` → `session_reconciler.go:5160-5186`, filtered silently so there is no
    restart loop;
  - the dashboard options view, `handler_sessions.go:161-176`;
  - the create endpoints, which refuse security-bearing choices.
- **Nil provider.** The worker factory refuses to start a session whose provider does not resolve: `factory.go:
  165-192`, `session_runtime.go:476-479`, `worker_handle.go:557-563`. It does not fall back to the stored
  `Info.Command`, `WorkDir` or `Resume*` values.
- **Stored commands.** The existing preservation of a stored command (`worker_handle.go:698-727`,
  `session_runtime.go:383-443`; issue #799, which keeps the claude `--settings` form) is left as it is. The gate is
  the control: a preserved command whose security flags equal the baseline passes, and a widened one is refused.
  The stale-key retry (`internal/session/chat.go:167-210`) is checked the same way at the gate.
- **Session keys.** `session_key` and `gc.brain_parent_sid` must match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$` at
  every splice site. The check runs before the stale-key probe. An invalid key starts the session fresh; an
  invalid parent id refuses the fork loudly.
- **Work dir.** The §2 guard runs where `Info.WorkDir` and task Beads are resolved: both resolvers (a rejected task
  Bead is skipped) and the resume resolvers `session_runtime.go:634-682` and `worker_handle.go:552-578`.
- **Stated as residual.** Transport inferred from a stored command is part of the declared transport residual.

## 4. Recording and the read-only print

- **Events.** Each refusal or ignored input writes one event naming the session, the source Bead id when known,
  the key or flag and the reason.
  - Values are truncated to 256 bytes with control characters escaped.
  - Controller events dedupe per (session, source, key) in a bounded LRU of 4096 entries, persisted in the
    runtime directory. The file is parsed with a size bound, and a corrupt file is discarded.
  - CLI and API events dedupe per process.
- **Print.** `gc config show --providers` adds `resolved_providers`: the base chain, the schema with each choice
  marked benign or security-bearing, the option defaults, `overridable_options` and
  `allow_security_option_overrides`. It also prints each agent's `work_dir`, subtree and `work_dir_roots`.

## Tests (red first; each fails at f3856bd1)

**Gate.** A table over every `Start` caller constructed through the seam: the reconciler start, the pool start,
the worker-handle attach and resume, the API resume, `gc session` wake and the stale-key retry.

- Each caller, fed a worker-written field, must be refused at the gate:
  - `template_overrides` with `permission_mode=unrestricted`, `worklog_access` or `worktree_access` on codex and
    claude;
  - a stored `command` with extra flags, and a stored `command` whose provider no longer resolves;
  - a stored `resume_flag` of `--settings <p> --resume`;
  - a `resume_command` on a provider without one;
  - a `work_dir` outside the roots (`/root-evil`, `.GIT`, a sibling agent);
  - `gc.pack=../x`;
  - a `session_key` of `--add-dir=/`.
- Must launch: `opt_model` and `opt_effort` on codex and claude, and each live lane's legitimate worktree with the
  ga-bebv roots.

**Other tests:**
- **Baseline equality:** a missing baseline `--settings` or `--sandbox` refuses.
- **Closed list:** the unrestricted list with every encoding.
- **Nil provider:** the factory refuses.
- **Keys:** the grammar, and an invalid parent id refusing the fork.
- **Events:** dedupe and bounds, and a corrupt LRU file.
- **Upstream:** the option-filter sites, the drift loop, the dashboard view, `initial_message`, and the create
  endpoints.
- **Gate coverage:** a test proves the seam wraps every provider kind (base, auto, acp), so no construction
  bypasses it. A source check asserts `resolveSessionTransportProvider` is the only place cmd/gc builds a session
  provider for starts.
- **Existing tests** that encode old behaviour are updated by name, with reasons:
  `template_resolve_phase2_test.go:61` and `:73`, `cmd_session_test.go:1068-1086`,
  `session_reconciler_test.go:11255-11324` and `session_reasoning_effort_test.go`. The rest of the suite stays
  green.

## Declared residual (operator's narrow-fix decision)

A worker running `gc`/`bd` can still:
- rewrite a session Bead's identity (`template`, `provider`, `real_world_app_session_kind`, `session_origin`, the
  named-session marker, `agent_name`, `alias`, `session_name`, `transport`, `mcp_identity`,
  `mcp_servers_snapshot`), so the gate checks against the wrong config;
- create sessions (`gc session new`, manual-origin rediscovery);
- route a Bead through `gc.routed_to`;
- substitute another session's valid `session_key` or `brain_parent_sid`;
- reach the controller API;
- race a symlink swap;
- write `template_overrides.initial_message`, `wake_mode` or `worker_dir` (auto-prune under `.gc/worktrees`), none
  of which widens a launch;
- change env or MCP servers through identity (covered by the identity residual).

These are tracked as ga-5eix. Until then workers are routed only inside reviewed windows, and the reviewed diff
plus CI is the control.

## Out of scope

city.toml, packs and live state, which ga-bebv carries.
