# ga-6umo: Core launch-control hardening (specification r2)

Coordinator-written under the operator's coordinator-fix exception (2026-09-26). The implementation goes to Core
`main` (`f3856bd1`), red first, two aegis-reviewer passes on the commit, PR, CI and merge. Deployment is a separate
reviewed package together with ga-bebv. This specification answers the two HOLD reviews of the r1 brief
(`6fd6a904`).

## Threat

Every Gas City worker can write Beads: its own task, other Beads, session Beads. At `f3856bd1`, Core takes launch
parameters from worker-writable metadata when it starts, wakes, attaches or resumes a session. A worker can
therefore widen the next session: remove the sandbox (`opt_permission_mode=unrestricted`, `--dangerously-*`), add
write roots (`opt_worktree_access`, `opt_worklog_access`, `managed_worktree_access`) or relocate the working
directory, which codex `workspace-write` and Claude's workdir make writable.

## Rule

**Worker-writable metadata may narrow or select among declared non-security choices. It may never widen a
session.** Input that fails the rule is ignored, never fatal. The session launches with the configured value, and
Core records one event naming the session, the source Bead id, the key and the reason, plus a controller log line.
Ignoring rather than refusing keeps a worker from blocking another template's launches by stamping a Bead
assigned to it.

## 1. Option overrides: one guard, deny by default

- **Where.** Add `config.FilterMetadataOptionOverrides(resolved *ResolvedProvider, overrides map[string]string,
  source string) (allowed map[string]string, rejected []RejectedOverride)` in `internal/config`. Every site that
  turns Bead or session metadata into option overrides calls it before building a command:
  - `workBeadOptionOverrides` and the trigger resolver (`cmd/gc/session_reconciler.go`, ~5542-5601);
  - session `template_overrides` at start (`cmd/gc/session_lifecycle_parallel.go` ~984-988) and
    `applySchemaOptionOverridesForLaunch` (~1264);
  - `buildResumeCommand` (`cmd/gc/cmd_session.go` ~1525-1625);
  - API resume (`internal/api/session_runtime.go` ~349-445);
  - the worker handle (`cmd/gc/worker_handle.go` ~560-735: `BuildProviderResumeCommand`,
    `BuildProviderLaunchCommand`).
- **Allow-list.** Only keys in the provider's new `overridable_options` list pass. If `overridable_options` is not
  set, the built-in default is `["model", "effort"]`, intersected with the resolved schema. That keeps ga-1mj and
  routed-unassigned `opt_model` and `opt_effort` working with no city change.
- **Security keys** are rejected even when listed, unless the provider sets `allow_security_option_overrides =
  true`, which has no default and is never set by ga-bebv. A key is a security key when:
  - it is one of `permission_mode`, `sandbox`, `worklog_access`, `worktree_access` or `managed_worktree_access`; or
  - any of its choices' `flag_args` contains a classified flag: `--sandbox`, `-s`, `--ask-for-approval`, `-a`,
    `--full-auto`, any `--dangerously-*`, `--permission-mode`, `--approval-mode`, `--add-dir`, `--settings`,
    `-c` or `--config`.

  The classifier is a function with its own table test.
- **Values** must still be valid schema choices (the existing `ResolveExplicitOptions` check).
- **Not options.** `initial_message` and the other non-schema `template_overrides` keys are not options; they
  pass through unchanged.
- **Operator paths** (`gc session new` flags, `gc sling` options) go through the same guard. An operator who
  needs a security option sets it in config, not on a Bead.

## 2. Working directory: one guard

- **Where.** Add `validateSessionWorkDir(cityPath string, agent *config.Agent, candidate, source string) (string,
  *RejectedWorkDir)` in `cmd/gc`. It is called at the final chokepoint after `session_lifecycle_parallel.go`
  ~1029-1034 (covering `resolveTaskWorkDir`, `newAssignedTaskWorkDirResolver` and the session Bead's
  `work_dir`), and on every resume, wake and attach path:
  - `cmd/gc/worker_handle.go` ~574;
  - `internal/api/session_runtime.go` ~353 and ~500;
  - `internal/session/chat.go` ~363 and ~498, where the check is passed in as a validator so `internal/session`
    does not import `cmd/gc`;
  - `cmd/gc/cmd_session.go` ~1528, ~1586 and ~1622.
- **Keys.** All three work-directory keys are held to it: `work_dir`, `gc.work_dir` and `worker_dir`.
- **Accept rule.** Resolve symlinks on both sides. A candidate is accepted when it equals the configured
  `work_dir` or lies under one of the allowed roots:
  - the configured `work_dir` itself (its descendants);
  - the Core-derived worktree root `<city>/.gc/worktrees/<rig>/<agent>/`;
  - each entry of a new optional agent key `work_dir_roots`, whose built-in default is empty.

  ga-bebv adds the lanes' external worktree roots there.
- **Otherwise** the configured `work_dir` is used, and the rejection is recorded.
- **Pool triggers.** `poolTriggerWorkDir` (`cmd/gc/build_desired_state.go` ~3203-3243) accepts `gc.pack` only
  as a single clean path segment (no `/`, `\`, `..` or NUL, not empty), exactly as the workspace slug already is.
  The joined result must still pass the guard.

## 3. Stored session commands

- **Rule.** A stored `command` or `resume_command` on a session Bead is never preserved when it differs from the
  config-derived command:
  - `shouldPreserveStoredRuntimeCommand` and `shouldPreserveStoredRuntimeCommandForTransport`
    (`worker_handle.go` ~680-727, which includes the claude `--settings` rule);
  - the API equivalents (`internal/api/session_runtime.go` ~383-443);
  - `internal/session/manager.go` `BuildResumeCommand` (~2067-2100);
  - `internal/worker/handle_lifecycle.go` `startCommand` (~433-472).

  Each rebuilds from config plus guarded overrides instead.
- **No provider.** When no provider resolves, the session does not start from a stored command. It refuses with
  a recorded reason: a session with no configured provider has no policy to hold it to.
- **Quoting.** `session_key` is quoted with the shell quoter when it is spliced into a command.
- `ValidateManagedLaunchPermissionPolicy` (`internal/config/launch_command.go` ~63-100) additionally refuses a
  managed command that contains any `--dangerously-*` flag unless the provider sets
  `allow_security_option_overrides = true`.

## 4. Read-only resolved schema print

`gc config show --providers` adds `resolved_providers`: for each provider, `name`, `base` chain, `options_schema`
(keys, choices, values, flag_args), `option_defaults`, `overridable_options` and
`allow_security_option_overrides`. It is read-only. ga-bebv and the windows use it as the proof, not a TOML
parse.

## Tests (red first, one per path)

Each test must fail at `f3856bd1` and pass after the fix:
- options: `opt_permission_mode=unrestricted`, `opt_worktree_access`, `opt_worklog_access` and
  `managed_worktree_access` are rejected through a work Bead, a trigger Bead, a session `template_overrides`, CLI
  resume, API resume and the worker-handle attach; `opt_model` and `opt_effort` still apply (the ga-1mj flow); a
  listed security key is rejected without the opt-in; the classifier table.
- work_dir: rejected outside the roots through each of the three keys, both resolvers, the session Bead, resume,
  wake and attach; a symlink inside a root pointing outside is rejected; the configured work_dir, a descendant, a
  Core-derived worktree and a `work_dir_roots` entry are accepted; `gc.pack=../x` is rejected.
- stored commands: a stored command carrying extra flags is rebuilt, never kept, through worker-handle attach and
  API resume; no provider refuses; `session_key` is quoted.
- managed policy: a `--dangerously-*` flag is refused without the opt-in.
- the new `config show --providers` output for a by_key codex over builtin shows the builtin choices, which is the
  ga-bebv proof.
- Every rejection writes exactly one event naming the Bead id.
- The existing suite stays green.

## Known residual paths (follow-up Beads, not closed here)

A worker can still:
- create a session Bead (`session_origin=manual`) for any configured template;
- route an open Bead to a more privileged pool through `gc.routed_to`;
- set `gc.brain_parent_sid` to fork another session's transcript;
- use the controller API if reachable from its sandbox.

Each gets its own Bead. Until they are closed, routing a worker stays inside reviewed windows, and ga-bebv does
not lift that restriction.

## Out of scope

city.toml, packs and live state: ga-bebv carries the replace-mode schemas for codex and claude, the
`work_dir_roots` and any `overridable_options`, and the deployment.
