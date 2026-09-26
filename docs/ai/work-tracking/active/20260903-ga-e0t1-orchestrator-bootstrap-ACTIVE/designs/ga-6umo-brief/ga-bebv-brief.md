# Live city: codex providers must not inherit the builtin unrestricted choice

Coordinator deployment Bead (a reviewed platform package, not a worker task). Found by the gct-mbg6 window
reviews on 2026-09-26 and recorded on ga-e0t1.

## Problem

`/home/loucmane/gascity/city/city.toml` declares `[providers.codex]` with `base = "builtin:codex"` and
`options_schema_merge = "by_key"`. At Core f3856bd1 the resolved codex schema therefore keeps the builtin
`permission_mode` choices `suggest`, `auto-edit` and `unrestricted` (`--dangerously-bypass-approvals-and-sandbox`),
the builtin `sandbox` key and extra model choices. Core applies an `opt_permission_mode` override from any
in-progress Bead assigned to a worker, so every codex lane (Template, HPFetcher, Blog) can relaunch without a
sandbox. `codex-evidence` and the other codex-based providers inherit the same way.

## Goal

- Every codex-based provider resolves to exactly the city's declared choices (replace mode), with every agent
  and rig default still a valid choice. Prove it with Core's resolved schema (the read-only print from the Core
  Bead, or a pinned Core resolve), not by parsing TOML.
- Deploy together with the Core launch-parameter fix, as one reviewed metadata successor: city.toml, the
  receipt refresh and the new permission revision, with the usual two reviews, preflight and postflight, and
  rollback.
- Until it lands, route no codex lane outside a reviewed window.

## Acceptance

The resolved schema proof, the successor's postflights, and a record on ga-e0t1.
