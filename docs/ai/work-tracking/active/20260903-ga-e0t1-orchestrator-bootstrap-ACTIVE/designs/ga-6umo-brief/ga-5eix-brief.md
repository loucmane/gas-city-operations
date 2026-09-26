# Core: an authorization boundary between workers and the operator

This follows ga-6umo, the narrow launch-parameter fix. Found by the ga-6umo specification reviews on 2026-09-26
and recorded on ga-e0t1. Brief to be reviewed before routing.

## Problem

Core at f3856bd1 has no boundary between a worker's `gc` and `bd` calls and the operator's. Workers run them
with the operator's authority, so a worker can:
- rewrite a session Bead's identity fields (`template`, `provider`, `session_kind`, `agent_name`, `alias`,
  `session_name`, `transport`, `mcp_identity`, `mcp_servers_snapshot`) to make an existing session resolve a more
  privileged config;
- create a session of any configured template with `gc session new`, or through manual-origin rediscovery
  (`cmd/gc/build_desired_state.go` around 2491-2624);
- route a Bead to a more privileged pool with `gc.routed_to`;
- substitute another session's valid `session_key` or `gc.brain_parent_sid` to resume or fork its transcript;
- reach the controller API, if it is reachable from its sandbox.

In addition, a symlink swap can race the check and the launch.

## Goal

- **Identity.** Controller-attested session identity (template, instance, provider, transport, MCP identity)
  lives outside every worker's write reach. A launch resolves only from that identity, and a session without it
  never launches.
- **Creation.** An operator-only channel creates sessions. A worker-invoked `gc session new` or a
  worker-created session Bead yields no launchable session.
- **Routing.** A Bead is routed only to pools its creator may route to.
- **Session keys.** A session key is bound to its own session.
- **Proof.** Every item is proven with red-first tests.

Until this lands, Gas City workers are routed only inside reviewed windows.
