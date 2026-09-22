# Claude Runtime Adapter

This repo uses Claude as a gated participant in the portable Codex foundation. The adapter is a runtime system, not a reminder document: readiness, PreToolUse/PostToolUse/Stop hooks, tests, and work-tracking evidence define whether Claude may mutate project state.

## Beads Migration Status

Gas City beads are authoritative for all new work; see `AGENTS.md`. Do not create or mutate a
Taskmaster task to duplicate a bead or merely to satisfy this adapter.

The strict Claude/Aegis readiness implementation supports bead-native work in this uninstalled
source checkout and retains Taskmaster as a compatibility path for historical numeric tasks.
Bead-native readiness requires a `codex/<bead-id>-...` branch, matching `Bead IDs` and branch
policy in the current plan, a matching current session, and exactly one matching ACTIVE tracker.
It does not read or mutate the historical Taskmaster graph.

## First Rule
Before Claude performs any persistent mutation, readiness must be `READY`.

```bash
python3 -m aegis_foundation.cli gate readiness --target-dir .
```

`BLOCKED` means no file edits, Bash mutations, work-ledger mutations, memory writes, Git writes, GitHub writes, or MCP mutations. Fix the workflow state first by using the kickoff/session/plan/work-tracking flow. Read-only inspection is allowed. Taskmaster MCP is intentionally not registered in this beads-first repository; historical Taskmaster files may be inspected read-only only for legacy evidence.

### Pre-kickoff orchestration

Readiness does not need to be READY to inspect the explicitly scoped managed Beads
`show <id>`, `list`, or `ready` commands. The classifier accepts only the reviewed
managed executable paths and closed flag set (`--json`, `--readonly`; additionally
`list --all --limit <integer> --no-pager`). It does not authorize mutations or prove
the selected store, executable installation, sandbox connectivity, or operator scope.
Use the exact environment and city/rig selection in `AGENTS.md`.

For new work, the primary supported entrypoint is the transactional workflow:

```bash
python3 plugins/gas-city-workflow/scripts/workflow.py begin \
  --root . --bead <bead-id> --goal '<authorized outcome>'
```

This is a **trusted bootstrap mutation**, not read-only inspection. It keeps the
workflow's Bead, project registration, worktree placement, journal, ownership, and
readiness checks. The gate requires the current project as the target and rejects
alternate registries, repeated identity flags, shell composition, and force options.
The existing `scripts/codex-task wizard kickoff` compatibility path is limited to
Bead-native invocations with explicit Bead, slug and title; a shared-source invocation
must also explicitly target the current project. Do not hand-assemble the scaffold.

Pre-kickoff Write/Edit (including plan files) remain blocked. A completed historical
plan is not permission to rewrite archives: inspect the supported recovery preview,
and apply only a reviewed bounded recovery. If no safe repair is offered, preserve
the record and use the authorized workflow transition or report the contradiction.

Strict readiness denials record a reason and payload digest in the existing decision
ledger; raw commands/content and free-form readiness output are not copied into the
new denial records. Failure to record a denial never makes the operation permissible.

Hook success alone is not Claude-native command approval. Operations explicitly
opts into the four-class command profile documented in
`docs/aegis/claude-orchestrator-permissions.md`. Only the exact scoped context,
Beads reads, canonical `workflow.py begin` and, with the `workflow-coordinate` opt-in
below, the stationary coordination verbs receive audited native approvals after all
applicable strict checks. No broad Bash allowlist, file-write grant,
plan-mode mutation, signing or lifecycle authority follows from this profile.

### Stationary canonical-root orchestration

With the explicit `workflow-coordinate` profile opt-in, keep the conversation at
the canonical project. Do not change `CLAUDE_PROJECT_DIR`, use `cd` to evade a gate,
or reopen the client for each task. Name the registered linked worktree on each
canonical `workflow.py` command. `attach`, `checkpoint`, `verify`, `coordinate`, `log`,
`discharge`, `compact-journal` and `publish` validate that target; other commands retain
their existing boundaries.

Use the canonical runtime path, literal arguments, and one operation per call:

```bash
python3 /home/loucmane/gas-city-ops/plugins/gas-city-workflow/scripts/workflow.py coordinate --root /absolute/registered/task-worktree --bead ga-primary --action note --text 'Evidence-backed progress'
python3 /home/loucmane/gas-city-ops/plugins/gas-city-workflow/scripts/workflow.py coordinate --root /absolute/registered/task-worktree --bead ga-primary --action create --title 'Bounded follow-up' --description 'Scope and constraints' --acceptance 'Observable proof'
python3 /home/loucmane/gas-city-ops/plugins/gas-city-workflow/scripts/workflow.py coordinate --root /absolute/registered/task-worktree --bead ga-primary --action depend --blocker ga-prerequisite
python3 /home/loucmane/gas-city-ops/plugins/gas-city-workflow/scripts/workflow.py log --root /absolute/registered/task-worktree --evidence 'path/to/proof' --note 'Completed the bounded operation'
python3 /home/loucmane/gas-city-ops/plugins/gas-city-workflow/scripts/workflow.py log --root /absolute/registered/task-worktree --pending-id 0123456789ab --note 'Recorded the pending mutation evidence'
python3 /home/loucmane/gas-city-ops/plugins/gas-city-workflow/scripts/workflow.py discharge --root /absolute/registered/task-worktree --pending-id 0123456789ab --note 'Recorded the signed commit into the journal'
python3 /home/loucmane/gas-city-ops/plugins/gas-city-workflow/scripts/workflow.py compact-journal --root /absolute/registered/task-worktree
```

The profile's `registered_projects` records make direct children of another
registered project's worktree root valid targets too, currently only the gascity Core
rig under `/home/loucmane/gascity-core-worktrees`; their readiness comes from the
portable Bead-scaffold checks and their identity from the seat's tracked registry.
`review_projects` records (the Template under `/home/loucmane/gas-city-template-worktrees`)
only let the reviewer bind a candidate; they are never coordination targets.
`discharge` resolves one delivery-class pending event (a commit, push or PR
operation) into the workflow journal without rewriting tracked S:W:H:E files;
every other mutation still needs `log`. `compact-journal` moves verified Bead
snapshots beside the journal and is the only verb accepted for a journal over the
1 MiB coordination bound. Remote observation (`gh pr view|list|checks|diff|status`,
`gh run list|view|watch`, `gh issue view|list`, `gh repo view`, `gh release list|view`,
`gh auth status`, refspec-free `git fetch`, and `git ls-remote` naming a configured
remote with plain ref patterns) is read-only inspection and needs no readiness.
`--web` in any form, `--show-token`, `gh api`, and any `git ls-remote` flag, path, URL
or helper that could run a program stay hookable mutations.

Replace example identities with the actual registered worktree and owned Bead.
`create` produces one unassigned, unrouted P2 task with a **nonblocking parent-child**
edge. `depend` adds a **blocks** prerequisite to the primary Bead, then invokes the
existing transactional `attach`; these relationships are not interchangeable.
`note` changes only notes on a primary or attached owned Bead. Exact completed
requests replay as no-ops; a pending/ambiguous intent requires reconciliation.

The two `log` forms are mutually exclusive. Use `--pending-id` only with the exact
12-character lowercase hexadecimal ID reported by the selected target; stationary
coordination deliberately rejects `current` and `latest` sentinels. Readiness and
pending tracking belong to the selected target; decision records
retain the original request digest and session identity. Observation state at the seat
or target refuses this opt-in; an advisory seat or target still validates and audits
the request but receives no native approval. Use target `log` to clear target
tracking. No general raw `bd` mutation approval, cross-rig grant, source edit,
dispatch, signing, publication, lifecycle, or plan-mode exemption is added.

The target's executable workflow helpers must match reviewed canonical bytes.
Ordinary candidate source edits are permitted, but edited workflow executors cannot
receive automatic approval to execute themselves. Such a runtime repair stays in
the explicit implementation/review lane until merge-bound activation; do not work
around the refusal. Gate approval validates local bindings, while execution still
rechecks **live** Bead ownership under the repository lock. A journal is not authority.

The PreToolUse dispatcher in `.claude/scripts/pretooluse-gate.sh` enforces this for hookable Claude file tools and tested Bash mutation patterns. After a successful mutation, `.claude/scripts/posttooluse-tracking.sh` records pending S:W:H:E tracking and `.claude/scripts/tracking-stop-gate.sh` blocks session stop until `aegis log` has updated the session, tracker, implementation log, changelog, handoff, and plan evidence.

In Gas City managed projects, the same PreToolUse dispatcher blocks Claude `Agent` and `Task`
delegation. Delegated work must have a Bead and a reviewed `gc sling` route. A routing refusal or
failure is a stop condition, never permission to fall back to a provider-native worker. The only
exception is an exact request record whose tracked bytes also exist on its declared remote review
ref; caller, session, and agent identity never authorize it.

A read-only reviewer is not a worker. The `aegis-reviewer` agent, whose tracked and clean
definition in `.claude/agents/` may declare only Read, Grep and Glob and only the name,
description, tools, model and color fields, may be delegated one review of exactly one
`candidate=<commit>` that exists in the repository, with no isolation, model or other
options, requested through Claude's own `Agent` tool. A registered or review-only
project's candidate is reviewed in its own worktree: add exactly one standalone
`worktree=<absolute path>` token (at the start of the prompt or after whitespace; path
characters `A-Za-z0-9._/-`; ended by a space, tab, newline or the end of the prompt)
naming a clean linked worktree that is a direct child of a registered or review-only
worktree root and whose HEAD is the candidate. Any other `worktree=` form, in any case, is refused.
Every binding failure refuses, in advisory mode too. Only the audit reason
`read_only_registered_reviewer_delegation` proves a binding was checked, so record it with
the verdict. The gate records the request digest; the orchestrator records the verdict on
the Bead. Any other
agent type, tool set, frontmatter field, option or candidate binding stays blocked.

## Required Workflow State
Claude mutations require all of these to align:
- current branch contains the active bead ID or compatibility Taskmaster task ID;
- bead-native source work has matching `Bead IDs` and branch policy, while compatibility task work has an in-progress Taskmaster/Aegis authority;
- `sessions/current` points to the active session for that work;
- `plans/current` points to the active plan for that work;
- exactly one ACTIVE work-tracking folder exists for that work;
- `TRACKER.md` and the active plan agree on plan-step status;
- `python3 -m aegis_foundation.cli gate readiness --quick --target-dir .` exits `0`.

## Operating Loop
1. Run readiness and stop on `BLOCKED`.
2. Read `sessions/current`, `plans/current`, and the active `HANDOFF.md`.
3. Review the authoritative Gas City bead for new work; consult Taskmaster only for an explicitly historical numeric-task compatibility flow.
4. Work one subtask at a time.
5. For every meaningful step, run `aegis log` or `./.aegis/bin/aegis log` before attempting the next mutation. The log must update the active session, tracker, implementation log, changelog, handoff, and current plan evidence; add `--surface findings` or `--surface decisions` when the mutation captured one of those records.
6. Capture command evidence under the active work-tracking `reports/` folder.
7. Run focused tests, `python3 scripts/codex-task plan sync`, `python3 scripts/codex-task work-tracking audit`, `python3 scripts/codex-guard validate --include-untracked`, `git diff --check`, and pre-commit before checkpointing.

## Claude-Owned Paths
Claude adapter work may edit:
- `CLAUDE.md`
- `.claude/**`
- `tests/claude_adapter/**`
- task/session/plan/work-tracking files for the active task

## Codex-Owned Paths
Claude must not edit these paths from this task:
- `CODEX.md`
- `templates/**`
- `scripts/codex-*`
- `scripts/template-*`
- `.codex/**`

The PreToolUse gate blocks direct file edits and tested Bash bypasses against these paths. If a change is needed there, document it in `DECISIONS.md` and create a Codex-led follow-up.

## Multimodal Scope
This workflow is not text-only. Treat the same state discipline as mandatory for:
- Claude file tools;
- Bash commands;
- Gas City bead CLI and Aegis MCP;
- Serena and Claude memory stores;
- Git and GitHub operations;
- sub-agents;
- future tool surfaces that can perform persistent mutations.

Every enforcement claim must be backed by a passing test or labeled policy-only in the active task's `DECISIONS.md` and `HANDOFF.md`.

## Slash Commands
Claude project commands live under `.claude/commands/`.

Core runtime commands:
- `/readiness` -> canonical `aegis gate readiness` evaluation
- New managed work -> transactional `workflow.py begin` above; `/kickoff` retains
  the bounded Bead-native `scripts/codex-task wizard kickoff` compatibility path.
- `/guard` -> `python3 scripts/codex-guard validate --include-untracked`
- `/plan-sync` -> `python3 scripts/codex-task plan sync`
- `/work-tracking-audit` -> `python3 scripts/codex-task work-tracking audit`
- `/sessions-update` -> `python3 scripts/codex-task sessions update`
- `/work-tracking-update` -> `python3 scripts/codex-task work-tracking update`
- `/scanner-run` -> `python3 scripts/codex-task scanner run`

Historical Taskmaster command files under `.claude/commands/tm/` are archival compatibility references, not an active mutable workflow surface.

## Supporting References
- Runtime contract: `.claude/engine/runtime-contract.md`
- Readiness spec: `.claude/engine/claude-readiness.md`
- Tool mapping: `.claude/engine/tool-mapping.md`
- Agent catalog: `.claude/AGENTS.md`
- Historical Taskmaster integration reference (read-only): `@./.taskmaster/CLAUDE.md`
