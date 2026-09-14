# Claude orchestrator command permissions

A successful Aegis PreToolUse check is normally a silent exit zero. Claude then
applies its native permissions; in `dontAsk` mode an unapproved command is refused.
The ga-e0t1 live probe established this exact split: both hooks passed, then Claude
refused `project_context.py --check` before the shell executed it.

## Opt-in profile, not a wildcard Bash grant

`.claude/orchestrator-command-profile.json` is a project-local, protected opt-in.
Operations enables four command classes, using closed grammars:

- `project-context`: the unchanged canonical `project_context.py`, current root,
  and `--check` only.
- `beads-read`: the managed absolute `gc`, exact city and descriptor-matching rig,
  followed by `bd show`, `list`, or `ready` and their closed read-only flags.
- `workflow-begin`: the unchanged canonical `workflow.py begin`, targeting the
  canonical checkout, with its existing Bead/slug/goal/dry-run grammar. Internal
  project, Bead, worktree, ownership, journal and readiness checks remain in force.
- `workflow-coordinate`: canonical `workflow.py attach/checkpoint/verify/coordinate/log/
  discharge/compact-journal/publish`, targeting one explicit registered linked worktree
  with verified journal/ownership. See the stationary-orchestration examples in `CLAUDE.md`.
  Its narrow ledger actions are note append, unassigned/unrouted P2 child creation, and
  dependency plus transactional attach. It does not approve raw Beads mutations or
  cross-rig work.

## Remote observation and journal-bound discharge (ga-fsfg R1)

Three defects kept a hooked seat from finishing delivery on its own. Each fix is a
closed grammar with its own regression corpus.

- **Remote reads are inspection.** `gh pr view|list|checks|diff|status`, `gh run
  list|view|watch`, `gh issue view|list`, `gh repo view`, `gh release list|view`,
  `gh auth status`, a refspec-free `git fetch` and a `git ls-remote` naming a
  configured remote with plain ref patterns are classified read-only, so a BLOCKED
  seat can watch CI and remote refs. `--web` in any spelling (`--web=...`, a short
  cluster such as `-wq`), `--show-token`, `gh api`, `gh pr create|merge|comment`,
  reruns, any fetch carrying a refspec or non-listed flag, and any `ls-remote` flag,
  path, URL or `ext::` helper that could run a program (`--upload-pack`, `-u`,
  `--exec`, `-o`/`--server-option`) stay hookable mutations.
- **Journals stay bounded.** Coordination records reference Bead snapshots by content
  digest (`{"$snapshot": sha256}`) stored beside the journal in
  `<bead>.snapshots/`; every reader resolves through `workflow_snapshots.py`, so legacy
  inline records keep working. `workflow.py compact-journal --root <worktree>` moves
  verified inline snapshots out-of-line idempotently and records a lifecycle event. It
  is the one verb the gate accepts for a journal over the 1 MiB bound; every other verb
  keeps the bound.
- **Delivery-class events discharge into the journal.** `git commit`, `git push` and
  `gh pr create|ready|merge` enqueue pending events tagged `kind: delivery`.
  `workflow.py discharge --root <worktree> --pending-id <12-hex> --note <text>` records
  head, tree, handler and evidence into the journal and removes exactly that event
  without touching tracked S:W:H:E files, so a commit no longer re-dirties the tree
  it just cleaned. PreToolUse exempts only an exact single-id discharge naming one
  delivery-class event; PostToolUse fails closed if the event is still queued and
  never enqueues the discharge itself. Edits and every other mutation still log
  through `aegis log`. The stationary seat runs `discharge` for a registered target
  with the same exact-id semantics as `log --pending-id`.

## Registered projects (ga-fsfg R2)

The profile may carry `registered_projects`: up to sixteen records of `id`,
`repository`, `canonical_root`, `worktree_root` and `rig`. Each record must agree
field for field with the tracked canonical registry
`plugins/gas-city-workflow/config/projects.json`, use absolute symlink-free roots,
and name roots distinct from the seat's own. A direct child of a registered
`worktree_root` is then a valid stationary target for `attach`, `checkpoint`,
`verify`, `coordinate`, `log`, `discharge`, `compact-journal` and `publish`.

A registered target carries no Operations policy or runtime of its own, so the
checks differ from an Operations worktree in three ways and nowhere else:

- identity comes from the seat's tracked profile and registry, and the target's
  journal spec must match the registered `id`, `rig`, `canonical_root` and
  `worktree_root`; the ownership binding is derived from that spec, the shared
  city and the registered canonical root, exactly as the plugin wrote it;
- the canonical executor is verified as before, and the target must carry no
  Operations runtime tree, installed runtime or Python startup hook that could
  shadow it;
- readiness uses the portable Bead-scaffold checks the plugin applies to
  registered projects, resolved through the target's own repository layout,
  because the generic readiness recognizes Bead identity only inside an Aegis
  source checkout.

Advisory enforcement at the seat or the target no longer refuses coordination.
The request is validated the same way and the target keeps the audit record: an
advisory target records its ordinary advisory allow, and an advisory seat
coordinating a strict target records `advisory_coordination_no_native_approval`
on that target. The seat receives no native approval either way, so Claude's
ordinary permissions decide. Observation state still refuses.

## Read-only reviewer delegation (ga-fsfg)

Independent review used to require a human-run reviewer because the managed-project
delegation rule blocked every `Agent` request. The rule now distinguishes a reviewer
from a worker with a closed grammar:

- the Claude `Agent` tool with `subagent_type` in the allowlist (`aegis-reviewer`);
- the agent definition `.claude/agents/<type>.md` tracked at HEAD, byte-identical to the
  working tree, named for its type, carrying only the `name`, `description`, `tools`,
  `model` and `color` frontmatter fields (no `hooks`, `permissionMode`, `mcpServers`
  or `memory`), and declaring `tools:` as a non-empty subset of Read, Grep and Glob,
  so the reviewer cannot edit, run, route or delegate even in advisory mode;
- a prompt naming exactly one `candidate=<40-hex>` commit that exists in the
  repository, bounded in size, and no `isolation`, `model` or other options; the
  model comes from the tracked definition alone.

The gate appends an `allow` decision carrying the request digest; the orchestrator
records the returned verdict on the Bead with the candidate binding. Malformed
reviewer requests fail closed as `native_delegation_reviewer_invalid`. Worker
delegation, other agent types and the Codex delegation tools are unchanged.

Only after the applicable strict gate checks succeed, the bridge records a
payload-digest decision and emits Claude's `hookSpecificOutput.permissionDecision`
as `allow`. It does **not** return early from the existing gate. Observation,
pending tracking, protected paths, hard policy and native-delegation restrictions
retain precedence. Advisory success and degraded fallbacks never issue this approval.
Unknown or missing permission modes never receive a bootstrap mutation approval.
Explicit native deny/ask rules and other hooks' denials are not overridden.

Plan mode has a separate hard boundary: hookable mutations and provider-native
delegation are explicitly refused before bootstrap, readiness, or delegation
exceptions can return success. The same refusal runs before the degraded advisory
fallback. Read-only inspection keeps the existing classifier and permission
checks. Plan-file writes, real kickoff, tracking logs, and repair/apply commands
have no exemption. Unclassifiable plan-mode hookable requests fail closed; an
unavailable audit sink cannot convert denial into permission. This does not grant
new rights to normal, missing, or unknown modes.

The R4 real-client test demonstrated why this is necessary: withholding an
`allow` message still let Claude execute `workflow.py begin` in plan mode. A
negative acceptance must prove exit/refusal plus zero requested mutation, not
merely the absence of approval JSON. Gate-owned denial audit records are expected;
they do not permit the requested command to run.

The profile is permission policy, not operator task authorization. A supported
command remains subject to the operator's stated scope. It grants no signing,
push/merge, arbitrary Bead mutation CLI, dispatch, lifecycle, file-write or privileged access.
It does not prove Claude implementation-worker capabilities.

## Identity and preservation

The profile must be a regular, unaliased, size-bounded JSON object with unique
keys, exact schema and a nonempty subset of the four known command classes.
Both task and canonical copies must equal their tracked HEAD bytes **and each
other**. A task branch cannot opt itself in or expand the canonical grant. The
managed descriptor, Git remote/common-directory identity, current hook cwd, city,
rig and direct-child worktree placement must agree. Exceptional worktree layouts
are not supported by this profile version and receive no implicit exemption.

Python entrypoints must come from the canonical checkout. Dirty or untracked
runtime source under the shared scripts/package roots blocks native approval;
testing an uncommitted runtime is not an unattended production permission grant.
Profile drift and approval-audit failure refuse before emitting an approval.
No profile means existing behavior. Unknown commands defer to existing native
permissions; the profile is not a replacement for the rest of the permission policy.

Stationary coordination leaves the conversation's canonical directory unchanged.
The requested target must be a direct-child worktree of the same canonical Git
repository with matching reviewed descriptor/profile, exact branch and journal
spec, ready phase, and derived external-owner binding. This local evidence never
substitutes for the executor's fresh scoped Bead readback. The existing workflow
lock serializes operations, but remains **not** a distributed Beads lease.

Target selection happens after plan-mode/delegation/hard-policy checks and before
target readiness, observation, and tracking checks. The original payload is not
rewritten. Approvals are digest-audited at the target, and PostToolUse tracking is
target-local. A target `log` can discharge target tracking, not canonical pending
work. Its evidence form and exact pending-event form are mutually exclusive. The
pending form requires one literal 12-character lowercase hexadecimal event ID that
exists exactly once in the selected target's required queue; ambiguous sentinels,
wrong-target IDs and mixed evidence/ID requests refuse. Resolution delegates to the
existing canonical Aegis pending-event implementation rather than expanding raw
`--target-dir` access. PreToolUse requires that exact event once; successful
PostToolUse requires it to be absent, so a no-op or incomplete resolution fails
closed. Invalid bindings are tier-C refusals in strict, advisory and degraded modes.

Because existing verification imports target workflow helpers, their executable
trees must remain byte-identical to canonical reviewed source. Unreviewed helper
edits/imports or divergent installed-runtime bindings refuse before target code is
loaded. This deliberately does not confer unattended permission to run arbitrary
candidate tests. Ordinary non-executor source changes do not block coordination.
An Operations runtime repair still uses the explicit implementation/review lane.

The hook launcher (including its packaged copy) and direct workflow CLI establish
source-only Python loading before project-runtime imports: bytecode writes are
disabled and the cache prefix is the platform null device, which cannot be a
cache directory. Fixed helper children inherit the same environment. Disabling
writes alone is insufficient: Python would still read a valid poisoned cache.
Executable tests exercise both shipped launchers, CLI imports and helper children,
with positive poison controls and byte-identical cache preservation.

Before any stationary runtime inventory or target import, the verifier requires
both in-process loading controls and both inherited environment values, plus the
real, unaliased Linux `/dev/null` character device (major 1, minor 3). A missing or
altered control refuses even on an otherwise clean checkout. The reviewed path
does not use sourceless loaders or reset these controls in helper children.

Only size-bounded regular tagged `__pycache__/*.pyc` files with a corresponding
reviewed source file may remain as inert evidence. Python's dotless cache naming
for extensionless scripts is accepted only for an exact same-directory tracked
regular source (Git mode `100644` or `100755`): interpreter loading does not
require an executable bit. Orphan and untracked-source caches still refuse;
the actual source bytes and executable mode must still match their Git object.
Cache payloads are not parsed,
compiled, compared, or trusted; stale, malformed, and poisoned caches cannot
supply executed code under this loading policy. Source Git-object bytes/modes,
untracked import refusal, symlink/special-file rejection, inventory bounds, and
all permission/ownership checks remain in force. No cache cleanup occurs.
This is not an OS sandbox or protection from a hostile same-UID process changing
files concurrently. The stationary runtime remains source-only; installed-runtime
overlays require a separately reviewed binding. Review and merge-bound live
acceptance are still required before activation/PASS.

Ledger operations persist intent before mutation and retain exact before/after
readbacks. Only a verified exact replay is a no-op; an uncertain response is not
retried. No failed intent, created child, or evidence is deleted automatically.

The new opt-in is Operations-only. It is not copied into the generic installer,
HPFetcher or Blog. Activation is a reviewed, merge-bound canonical fast-forward:
capture old HEAD and config hashes, verify clean canonical state, advance to the
exact reviewed merge, then verify module/profile bytes and fresh-session behavior.
Do not reset history or overwrite user settings for rollback. An activation
failure stops for an evidenced append-forward correction; no broad permission or
mode fallback is allowed. User/project settings, MCP configuration, hooks and
permission arrays are unchanged by this profile.

## Acceptance before PASS

Run the full adapter and meta-workflow suites, managed-asset parity/goldens and
source guard. Then use a compatible, already-installed Claude client in a fresh
session with normal hooks loaded. A unit test of exit zero is insufficient.
Require actual shell execution for context and scoped ledger reads, and prove
native explicit deny/ask precedence. In an isolated synthetic managed-project
fixture, prove real transactional begin with a bounded acceptance Bead, followed
by fresh-session task-worktree behavior. File-write capability is a separate
native permission and must not be smuggled into this command profile. Re-prove
observation/stop and adversarial refusals. Preserve all failed attempts and do not
close ga-e0t1 based only on parser or hook simulation results.

The opt-in remains task-scoped under the operator's standing authorization: normal
implementation steps and understood safe retries do not require renewed approval
for each command. A genuinely new access, disclosure, privileged, destructive, or
task boundary still needs authority. Independent review and actual live acceptance
are checkpoints, not requests to reauthorize the same edit/test cycle.

Protocol references: [Claude permissions](https://code.claude.com/docs/en/permissions)
and [PreToolUse hook decisions](https://code.claude.com/docs/en/hooks).
# Literal evidence text and hard policy

Quoted evidence may contain the words `source` and `eval` without being a shell
evaluator. The hard-policy check retains its raw sensitive-family preclassification,
then uses the existing shell parser to distinguish quoted data from executable
command names. Actual evaluator commands (including quoted names and the `.`
builtin), nested shell bodies, and malformed sensitive commands still refuse.
Raw substitution, redirection-synthesis, and Python `-c` checks remain conservative;
this is not a general-purpose shell interpreter or a new Beads-write allowance.
Passing hard policy still leaves readiness, ownership, native permissions, and the
operator's scope in force.
