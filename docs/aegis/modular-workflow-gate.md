# Modular Aegis Workflow Gate

Bead: `ga-iqbd`

## Outcome

Aegis has one adapter-neutral workflow authorization engine. Claude and Codex
transport adapters no longer own readiness or mutation policy. They translate
client payloads into the canonical runtime and render its decision.

The compatibility files remain managed for one migration window:

- `.claude/scripts/readiness.sh` is a thin launcher for `aegis gate readiness`;
- `.claude/scripts/gate_lib.py` is a thin fail-closed loader for the modular hook
  package.

Neither compatibility file contains workflow policy. New hook execution reaches
the canonical Python modules directly. Removing a wrapper later is an installer
inventory change, not another policy rewrite.

## Ownership Boundaries

| Module | Sole responsibility |
| --- | --- |
| `gate/models.py` | Stable readiness result types and status constants |
| `gate/state.py` | Read-only Git, JSON, pointer, plan, and tracker primitives |
| `gate/workflow.py` | Task, bead, observation, source-closeout, and current-work authorization |
| `gate/render.py` | Bounded human and one-line machine output |
| `gate/readiness.py` | Public readiness façade and CLI argument translation |
| `gate/repo_structure.py` | Shared repository-structure configuration for workflow scripts |
| `gate/bead_scaffold.py` | Beads-native scaffold checks for the shared evidence layout |
| `gate/session_authority.py` | Read-only parity for tracked daily sessions and the logging envelope |
| `gate/session_transition.py` | Bounded daily-session transaction with surviving before/after images |
| `gate/session_reconciliation.py` | Exact-plan reconciliation of one stale source-session envelope |
| `gate/hooks/contracts.py` | Hook payload and policy data contracts |
| `gate/hooks/payloads.py` | Payload parsing, paths, MCP classification, and apply-patch parsing |
| `gate/hooks/hard_policy.py` | Non-overridable Git, governance, and synthesis policy |
| `gate/hooks/shell_policy.py` | Shell read-only/mutation and sanctioned-workflow classification |
| `gate/hooks/runtime_state.py` | Read-only current-work, pending, and degraded-state access |
| `gate/hooks/evidence.py` | Evidence extraction and pending-tracking classification |
| `gate/hooks/decisions.py` | Enforcement mode, recovery contract, audit, and allow/block decisions |
| `gate/hooks/pretool.py` | Ordered pre-tool policy pipeline and degraded fail-safe |
| `gate/hooks/permission_modes.py` | Explicit plan-mode mutation/delegation refusal before workflow exemptions and degraded allowances |
| `gate/hooks/tracking.py` | Post-tool, ledger, scope, and capsule event capture |
| `gate/hooks/lifecycle.py` | Session-start, stop, and configuration-change boundaries |
| `gate/hooks/loaders.py` | Script directory and ledger/brief helper module loading |
| `gate/hooks/delegation.py` | Managed-project identity and provider-native delegation policy |
| `gate/hooks/reviewer.py` | Read-only `aegis-reviewer` grammar and registered-worktree candidate binding |
| `gate/hooks/orchestrator.py` | Closed, non-executing pre-kickoff command contracts |
| `gate/hooks/native_permissions.py` | Opt-in command profile, registered and review projects, and native approvals |
| `gate/hooks/coordination.py` | Stationary seat binding to one explicit workflow target |
| `gate/hooks/coordination_runtime.py` | Canonical runtime byte verification and registered-target runtime shadows |
| `gate/hooks/entrypoint.py` | Phase dispatch only |

State readers never mutate. Classifiers do not write evidence. Decision code is
the only policy verdict owner. Adapter entrypoints do not know bead, Taskmaster,
plan, tracker, or shell-policy semantics.

## Stable Public Contract

```text
aegis gate readiness [--target-dir PATH] [--quick|--verbose|--all]
```

Exit `0` means `READY` or `WARN`; exit `2` means `BLOCKED`. `--quick` remains a
single bounded status line. `--adapter` changes only the full-output heading.

Pre-tool authorization remains fail closed in strict mode. Advisory mode may
record and allow workflow-ceremony blocks, but it never weakens destructive Git,
repository governance, parser ambiguity, protected-path, or observation
boundaries. Break-glass remains one-shot and limited to its existing workflow
state reason classes.

## Runtime And Upgrade Model

Installed projects call their project-local `.aegis/bin/aegis` dispatcher. Every
managed install also carries a narrow, checksummed Python snapshot at
`.aegis/runtime/python` containing only the gate engine and its package metadata.
Hooks and readiness therefore remain available when the source checkout is
missing, moved, unmounted, or mid-update. The snapshot is part of the manifest,
strict verification, managed update, doctor, and rollback inventories.

The reviewed `runtime.env` still selects the active full Aegis source/runtime for
CLI operations outside the gate. A managed upgrade replaces the local gate
snapshot before the thin launchers, then advances the source pointer. This gives
every project a stable fail-closed authorization boundary without freezing the
rest of Aegis into each repository.

`aegis runtime update` remains pointer-only by design and never silently swaps
authorization policy. Gate changes use the normal reviewed managed-update path,
which plans, hashes, verifies, and rolls back the snapshot and launchers as one
unit. Runtime status lists snapshot changes among the cases that require that
managed update.

The hook compatibility loader prefers the target-local gate snapshot, then the
reviewed source pointer, and fails closed for mutation-capable phases when neither
canonical runtime is available. Passive evidence phases remain fail-open only
under their existing degraded contract.

## Migration And Rollback

1. Characterization tests freeze the legacy behavior.
2. Canonical modules run behind the old commands.
3. Claude and Codex hook paths call the canonical readiness evaluator directly.
4. The installer copies a manifest-bound local gate snapshot and proves hooks keep
   working after the recorded source path becomes unavailable.
5. Cross-project install/update tests prove source, Blog-like, HPFetcher-like,
   Claude-only, Codex-only, and multi-agent shapes.
6. Compatibility launchers remain for one release and are separately removable.

Rollback restores the prior managed `readiness.sh` and `gate_lib.py` assets and
the previous runtime pointer. Workflow evidence, current-work state, plans,
sessions, trackers, beads, and Taskmaster compatibility data are never migrated or
deleted by this change.

## Maintainability Rules

- Adapter launchers target at most 80 nonblank lines and contain no policy tables.
- Orchestrators target 250 lines; ordinary domain modules target 500 lines.
- Parser/classifier modules may reach 700 lines when splitting would obscure one
  grammar, but require focused adversarial tests.
- A policy must have one canonical implementation and differential adapter tests.
- Adding a supported client creates an adapter, not a copy of workflow logic.
- Taskmaster remains a compatibility integration only when current-work declares
  it required; beads remain the primary authority for Gas City work.
