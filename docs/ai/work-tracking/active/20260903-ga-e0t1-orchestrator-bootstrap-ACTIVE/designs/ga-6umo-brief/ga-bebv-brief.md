# Live city: no provider inherits a builtin choice wider than the city declares

Coordinator deployment Bead: a reviewed platform package, not a worker task. Found by the gct-mbg6 window and
ga-6umo brief reviews on 2026-09-26, and recorded on ga-e0t1 (r2 of this brief).

## Problem

`/home/loucmane/gascity/city/city.toml` layers two providers over builtin profiles with
`options_schema_merge = "by_key"`, so the resolved schemas at Core f3856bd1 keep every builtin choice:
- `[providers.claude]` (`base = "builtin:claude"`) keeps `permission_mode = unrestricted`
  (`--dangerously-skip-permissions`). `claude-attention` (`base = "provider:claude"`) inherits it, and the
  city's claude-family providers inherit `worktree_access`, whose choices add `--add-dir` for the Template
  `.git`: `claude-signing` and `claude-candidate` from `managed/rig-permissions.toml`.
- `[providers.codex]` (`base = "builtin:codex"`) keeps `permission_mode = unrestricted`
  (`--dangerously-bypass-approvals-and-sandbox`), the builtin `sandbox` key and extra model choices.
  `codex-evidence` (`base = "provider:codex"`, by_key) inherits them.

Core applies an `opt_<key>` value from any in-progress Bead assigned to a worker, so every lane can widen itself
today.

## Goal

This package deploys together with the merged ga-6umo Core fix, as one reviewed metadata successor:
- **Replace mode.** Every provider over a builtin (`claude`, `codex`) switches to replace mode. Every derived
  provider (`claude-attention`, `claude-signing`, `claude-candidate`, `codex-evidence` and any other found by the
  resolved print) is listed by name and resolves to exactly the declared choices. Every agent and rig default,
  listed by name, stays a valid choice.
- **The proof** is ga-6umo's `gc config show --providers` on the new city, not a TOML parse. No resolved choice
  may carry a `--dangerously-*` flag.
- **work_dir_roots** is set for each lane whose worker creates worktrees outside `<city>/.gc/worktrees`: the
  Template, HPFetcher, Blog and Core worktree roots, each equal to that lane's existing write root.
- **overridable_options** is left at the ga-6umo default (`model`, `effort`) unless a named flow needs more.
- **Deployment discipline.** The receipt is refreshed with the new permission revision. The package gets two
  reviews, preflight and postflight, and rollback.

## Interim and after

Until this and ga-6umo land, route no Gas City worker outside a reviewed window. The restriction stays after
they land too, until the ga-6umo known residual paths have their own fixes: manual session Beads,
`gc.routed_to` to privileged pools, `gc.brain_parent_sid` and controller API reach.

## Acceptance

The resolved-schema proof, the successor's postflights and a record on ga-e0t1.
