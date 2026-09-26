# Live city: no provider inherits a builtin choice wider than the city declares

Coordinator deployment Bead: a reviewed platform package, not a worker task. Found by the gct-mbg6 window and
ga-6umo reviews on 2026-09-26, and recorded on ga-e0t1 (r3 of this brief).

## Problem

`/home/loucmane/gascity/city/city.toml` layers providers over builtin profiles with
`options_schema_merge = "by_key"`, so the resolved schemas at Core f3856bd1 keep every builtin choice:
- `[providers.claude]` (`base = "builtin:claude"`) keeps `permission_mode = unrestricted`
  (`--dangerously-skip-permissions`). `claude-attention` inherits it. The claude-family providers `claude-signing`
  and `claude-candidate` (in `managed/rig-permissions.toml`) inherit `worktree_access`, whose choices add
  `--add-dir` for `.git` roots.
- `[providers.codex]` (`base = "builtin:codex"`) keeps `permission_mode = unrestricted`
  (`--dangerously-bypass-approvals-and-sandbox`), the builtin `sandbox` key and extra model choices.
  `codex-evidence` and `codex-managed-worklog` inherit them.

Core applies an `opt_<key>` value from any in-progress Bead assigned to a worker, so every lane can widen itself
today.

## Goal

This package deploys together with the merged ga-6umo Core fix, as one reviewed metadata successor.
- **Replace mode.** Every provider over a builtin (`claude`, `codex`) switches to replace mode. Every derived
  provider (`claude-attention`, `claude-signing`, `claude-candidate`, `codex-evidence`, `codex-managed-worklog` and
  any other the resolved print shows) is listed by name and resolves to exactly the declared choices.
- **Defaults still resolve.** Every agent, rig and provider default, including builtin defaults the providers
  inherited (claude `effort` and `permission_mode`, codex's), is listed by name and is a declared choice in replace
  mode. Otherwise a launch fails with an unknown option.
- **The proof** is ga-6umo's `gc config show --providers` on the new city: no resolved choice carries a
  `--dangerously-*` or `--yolo` flag, and every default resolves.
- **work_dir_roots** lists worktree roots only, never a `.git` root, for each lane whose worker creates worktrees
  outside `<city>/.gc/worktrees`: the Template, HPFetcher, Blog and Core worktree roots, and the Operations
  candidate root `/home/loucmane/gas-city-ops-candidate-worktrees`. A dry run of the guard over each lane's real
  task `work_dir` values proves each is accepted.
- **overridable_options** stays at the ga-6umo default (`model`, `effort`) unless a named flow needs more.
- **Deployment preconditions and discipline.**
  - The city is suspended, and no session Bead is open: every session is recreated under the new Core, because
    ga-6umo needs a creation-time `gc.launch_identity`.
  - The receipt is refreshed with the new permission revision.
  - Two reviews, preflight, postflight and rollback.

## Interim and after

Until this and ga-6umo land, route no Gas City worker outside a reviewed window. The restriction stays after
they land too, until the ga-6umo known residual paths have their own fixes: worker-created session Beads,
`gc.routed_to` to privileged pools, controller API reach and the symlink race.

## Acceptance

The resolved-schema proof, the `work_dir` dry run, the successor's postflights and a record on ga-e0t1.
