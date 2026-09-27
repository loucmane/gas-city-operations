# Primary track — a fresh Gas City 1.4.0 build, done right with the learnings

**Status: this is now the primary track.** The hardened-city campaign is
**parked** — not retired. The decision gate ran its course: G66 proved the
machinery works (correct refusals, proven fixes, live receipts), and that
proof is exactly why the operator chose to stop pouring attention into it.
The city stays suspended in its known-good state (procedure below); whether
it is ever resumed or formally retired is a later decision that nothing here
depends on.

This fresh build starts on upstream Gas City 1.4.0 — carrying the
*knowledge* from three weeks of stops, but none of the hardened components:
no locks, no manifests, no pinned images, no fork. Nothing is forced onto
it: rigs are onboarded when the city has earned them, Aegis last of all.

## Parking the hardened city (one-time, before day one)

The hardened city is already in the right state: suspended, supervisor PID 0,
sockets absent, process table empty, all evidence preserved. Parking it means
freezing that state and writing it down — nothing more:

- Leave the checkpoint branch at `a6c4f768…` (G66 head, installed on r68).
  Every executed head is on fetchable history; the lineage audit is closed.
- Leave `ags-xc3y`'s preserved claim, `ags-s5ie`, and the un-recovered
  `ags-wvfp` exactly as they are. The pending native recovery of `ags-wvfp`
  is the documented first step *if* the campaign ever resumes — do not
  perform it now; a parked city needs no recovery.
- One short handoff note in the evidence tree: current head, lock digest,
  what is suspended, what is pending (the `ags-wvfp` recovery, the trial
  retry), and the trial-stop digest `3338f5bd…`. Metadata only, as always.
- All Tier-B evidence, credentials, and rotation receipts keep their
  standing rules. Nothing is deleted, nothing is migrated.
- The six bootstrap containers are currently **running and healthy** — the
  handoff note records that actual observed state, not an assumed one.
  Leaving them running is acceptable parking state (do-not-disturb
  governs). Stopping them is an optional host action requiring its own
  authorization; if taken, the note is updated with the new observed state.

## The one mistake we are not repeating

The hardened city made every safety property a **fail-closed gate wrapped
around the entire pipeline**, then certified the whole wrapper offline. Because
a session dies at the first broken gate, each of ~15 gates could only be found
serially — one dead session per defect. Sixteen candidates, thirteen reference
builds, to walk one path end to end.

The rule for the fresh build:

> Build the working thing on native mechanisms first. Add any proof as a
> **non-blocking observer**. Promote a check to blocking only after it has
> earned it against live traffic. Never certify a wrapper in isolation.

Nothing becomes a hard gate until it has watched real sessions pass and proven
it refuses only what should be refused.

**The observer baseline is native, not custom.** Gas City 1.4 already ships
run-centered status, structured transcripts, durable usage accounting,
OpenTelemetry export, formula v2 controls, and scheduling/orders
([1.4 release](https://github.com/gastownhall/gascity/releases/tag/v1.4.0)).
Exhaust those before designing any observer of our own — a custom observer
duplicating a native surface is the authority-adapter mistake in miniature
(see the ledger's PARK table).

## Attestation: decide up front, keep it additive

Model attestation (proof that requested == observed, fallback detection) is the
one thing native gc genuinely does not provide. Decision for the fresh build:
**out of the frame.** If a specific project ever needs it, add it as a
receipt-logging sidecar on *that project only* — a post-session hook that reads
the transcript and records the observed model, non-blocking, alerting not
refusing. Promote to enforcement only if it ever actually catches a fallback.
It is never the scaffold the city is built around.

## The two real upstream bugs — fix upstream, do not fork

Both were proven present in 1.4.0 at tag `v1.4.0`. The right move is upstream
contribution, not a private patched binary to babysit.

1. **Lease race** — fixed 60s `creating` projection overrides the configured
   startup lease; slow-starting sessions die at ~60s. Analysis + patch already
   filed as
   [gastownhall/gascity#4858](https://github.com/gastownhall/gascity/issues/4858).
   **Action: turn it into a PR** against then-current upstream `main`, and
   run the first upstream release containing the fix. Until then, the
   narrow production fix plus its regression tests
   (`patches/gc-v1.4.0-pending-create-lease.patch`, applied to the exact
   `v1.4.0` base) is a *bridge*, explicitly temporary — not a
   maintained fork. Bridge and PR are separate targets: the bridge is
   pinned to the release we run; only the PR chases `main`.

2. **Credential in tmux argv** — gc projects the Dolt password into
   `tmux new-session -e`, readable via `/proc`. **Action: file it upstream**
   (they do not know; their own test suite hides the analogous lease bug).
   Until fixed: host-wide `hidepid=2`, low-value per-project Dolt passwords,
   and the operator rules below. Do not build a credential subsystem — that was
   apparatus.

## Environment fidelity is now a habit, not a machine

The deepest recurring failure was tests validated against fixtures, rehearsals,
or launch environments that did not match the real runtime — wrong umask, wrong
launch path, wrong argv shape, synthetic data. On the fresh build there is no
fixture apparatus to drift: **you run against the live city from day one and
watch it work.** If you ever add a check, prove it against a real session
before trusting it. If isolation is ever wanted: gc 1.4.0 provides discrete
runtime packs — `tmux`, `subprocess`, Kubernetes, SSH, and `exec:` — not a
generic local-Docker isolation mode. Choose one explicitly and add it one
increment at a time against a running city — never a pinned offline-verified
image set ([runtime docs](https://github.com/gastownhall/gascity/blob/v1.4.0/docs/guides/configuring-an-agent.md)).

## Layout

```
~/gascity/
  bin/gc            # upstream 1.4.0 base + bridge patch (stock once a release contains the fix)
  home/             # dedicated GC_HOME — never the machine-wide default
  city/             # the city root
```

**`GC_HOME` isolation is a hard precondition.** gc's default home is the
machine-wide `~/.gc`, whose registry and supervisor state are shared — and
1.4.0's own release notes warn that an unrelated registered city can block
startup ([supervisor paths](https://github.com/gastownhall/gascity/blob/v1.4.0/internal/supervisor/config.go),
[v1.4.0 upgrade warning](https://github.com/gastownhall/gascity/releases/tag/v1.4.0)).
Before `gc init`: set and persist `GC_HOME=~/gascity/home`, explicitly
allocate and verify a separate supervisor socket, unit, and port, and prove
the default registry is untouched (witnessed check, not assumption — the
parked hardened city's supervisor state must never be shared with this one).

Operator rules carried over as pure discipline (each earned from a live
incident, none requiring machinery):

- One rig per real project. Own bead store per rig (native gc does this; the
  per-rig-DB pain was our compose constraint, not gc's).
- Never run `systemctl status` on a credential-carrying unit — `is-active` /
  `show -p MainPID`. Treat nearby transcripts as sensitive.
- `hidepid=2` stays set host-wide.
- `GC_CITY_PATH` set correctly in any script — the orphan sweeper is
  city-scoped and relies on it.
- The native city binds `GC_BIN`, `GC_HOME`, and native-first `PATH` in
  `[workspace.env]`. Authored prompts use `~/gascity/bin/gc` and
  `~/gascity/bin/bd` explicitly because login shells can reorder `PATH`.
  The trusted city-local `.codex/config.toml` reasserts the same identity and
  native-first path for commands spawned by Codex after its shell snapshot;
  copy that file into the city root with `city.toml`.
  Install the checked-in `hooks/claude.json` as the city hook source too: gc's
  generated default prepends `~/.local/bin`, which is the parked binary here.
- Before killing "stray" tmux state, check which city/session owns it.

## Model picker — reviewed config, carried as knowledge

The carried artifact is the set of **model identities**, every one
live-preflighted during certification (including that Haiku must be requested
as its dated id or the guard rejects the alias). The menu below is that carry
plus one labeled currency update — the `max` effort entry, added from current
guidance rather than from preflight. This is native `city.toml`.

```toml
[workspace]
provider = "claude"
max_active_sessions = 4

[workspace.env]
GC_BIN = "$HOME/gascity/bin/gc"
GC_HOME = "$HOME/gascity/home"
PATH = "$HOME/gascity/bin:$PATH"

[agent_defaults]
append_fragments = ["native-command-path"]

[session]
startup_timeout = "5m"

[providers.claude]
base = "builtin:claude"
options_schema_merge = "by_key"
option_defaults = { model = "opus-5-5", permission_mode = "auto-edit" }

[[providers.claude.options_schema]]
key = "model"
label = "Model"
type = "select"
default = "opus-5-5"

[[providers.claude.options_schema.choices]]
value = "opus-5-5"
label = "Claude Opus 5.5"
flag_args = ["--model", "claude-opus-5-5"]

[[providers.claude.options_schema.choices]]
value = "fable-5"
label = "Claude Fable 5"
flag_args = ["--model", "claude-fable-5"]

[[providers.claude.options_schema.choices]]
value = "haiku-4-5"
label = "Claude Haiku 4.5"
flag_args = ["--model", "claude-haiku-4-5-20251001"]   # dated id — the alias silently canonicalizes

[[providers.claude.options_schema.choices]]
value = "sonnet-5"
label = "Claude Sonnet 5"
flag_args = ["--model", "claude-sonnet-5"]

[providers.codex]
base = "builtin:codex"
title_model = "gpt-5.6-sol"
option_defaults = { model = "gpt-5.6-sol", effort = "xhigh" }

[[providers.codex.options_schema]]
key = "model"
label = "Model"
type = "select"
default = "gpt-5.6-sol"

[[providers.codex.options_schema.choices]]
value = "gpt-5.6-sol"
label = "GPT-5.6 Sol"
flag_args = ["--model", "gpt-5.6-sol"]

[[providers.codex.options_schema.choices]]
value = "gpt-5.6-luna"
label = "GPT-5.6 Luna"
flag_args = ["--model", "gpt-5.6-luna"]

[[providers.codex.options_schema.choices]]
value = "gpt-5.6-terra"
label = "GPT-5.6 Terra"
flag_args = ["--model", "gpt-5.6-terra"]

[[providers.codex.options_schema]]
key = "effort"
label = "Reasoning effort"
type = "select"
default = "xhigh"

[[providers.codex.options_schema.choices]]
value = "low"
flag_args = ["-c", "model_reasoning_effort=low"]
[[providers.codex.options_schema.choices]]
value = "medium"
flag_args = ["-c", "model_reasoning_effort=medium"]
[[providers.codex.options_schema.choices]]
value = "high"
flag_args = ["-c", "model_reasoning_effort=high"]
[[providers.codex.options_schema.choices]]
value = "xhigh"
flag_args = ["-c", "model_reasoning_effort=xhigh"]
[[providers.codex.options_schema.choices]]
value = "max"
flag_args = ["-c", "model_reasoning_effort=max"]
```

Effort-menu currency (from the omission-pass audit): `max` is supported per
[OpenAI's GPT-5.6 guidance](https://developers.openai.com/api/docs/guides/latest-model)
and is included above. The local Codex CLI catalog (`0.146.0-alpha.3.1`)
additionally advertises `ultra` for Sol and Terra — **add `ultra` only after
a live CLI preflight**, per the dated-Haiku lesson: menu entries are added
when preflighted, not when advertised. The Claude menu was current as of this
audit (Fable 5, Opus 5, Sonnet 5, dated Haiku 4.5; Mythos is limited-access
and deliberately absent). On 2026-09-22 (gct-er3h) Opus 5.5 replaced Opus 5
outright after a live preflight: `claude-opus-5-5` answered as itself on
Claude Code 2.1.280, while the previously pinned 2.1.263 refused the model, so
the managed worker CLI pin moved with it. Sonnet 5.5 and Haiku 5.5 join the
menu only after release and the same live preflight.

### Task-to-model routing

The menu above only permits manual selection; it does not choose models for
tasks. gc supports this natively: define **named agents/pools** with
per-agent `provider` and `option_defaults`
([per-agent configuration](https://github.com/gastownhall/gascity/blob/v1.4.0/docs/guides/configuring-an-agent.md)),
then route formulas to those named agents — gc has per-agent
configuration and routing, not an abstract role primitive. Starting
split (design, revisable at will):

- `builder` — Codex `gpt-5.6-sol` @ `xhigh`: implementation beads.
- `reviewer` — Claude `fable-5`: review/analysis beads, upstream PR content.
- `sweeper` — Claude `haiku-4-5` (dated id): mechanical/low-stakes beads
  (currency checks, formatting, triage).

Route by formula, not per-dispatch memory; adjust the split from observed
results — this is exactly the kind of choice the observer loop is for.

## Rigs — one per real project

Before `rig add` or creation of a project's first native bead, record exactly
one authority choice: **migrate the complete Taskmaster history first**, using
the attended runbook in `docs/plans/workflow-draft.md`, or **start fresh** with
no import. Partial migration and later shadow import are forbidden. Migration
requires an empty target, so this is structurally an onboarding decision, not
cleanup that can be deferred.

For tagged Taskmaster stores, "complete" means the complete graph of every
tag declared authoritative at cutover. A documented non-authoritative tag may
remain frozen and unimported only after zero cross-tag references are proved
and the decision is recorded; its files are never rewritten to make the
converter accept them.

```sh
export GC_HOME=~/gascity/home   # never the machine-wide default — coexistence depends on it
GC=~/gascity/bin/gc; CITY=~/gascity/city
$GC --city $CITY rig add /home/loucmane/gas-city-native --name gas-city-template # explicit fresh start; first
# Only after hpfetcher's quiet-point migration:
$GC --city $CITY rig add /home/loucmane/dev/hpfetcher   --name hpfetcher
# Only after the blog master-tag cutover:
$GC --city $CITY rig add /home/loucmane/dev/blog        --name blog
# Only after all earlier phases, under its recorded onboarding decision:
$GC --city $CITY rig add /home/loucmane/codex           --name aegis
```

`gc rig remove` removes registration, not necessarily the backing Beads
population. A removed rig's prefix is therefore not clean by default. Before a
prefix is reused, explicitly dispose the complete retained store under an
attended operator decision or allocate a fresh prefix; never merge or delete
selected records to make the empty-target check pass.

The real Aegis repository path is `/home/loucmane/codex`; that is the project
repo, not the parked deployment or one of its managed worktrees. The real
hpfetcher path is `/home/loucmane/dev/hpfetcher`. hpfetcher remains under live
Taskmaster authority and operator activity until the operator declares its
quiet point: no rig registration, shadow beads, fetch, fast-forward, reset,
clean, or migration before then. Its exact observed local head is preserved at
`archive/pre-city-local-main`; at the 2026-08-02 observation it was 0 commits
ahead and 2 behind `origin/main`. Reconciliation and complete-history migration
happen only at the quiet point, before hpfetcher's first native bead.

The blog path is `/home/loucmane/dev/blog`. Its cutover source is the signed,
fetchable Task 43 continuation, not the stale pre-PR root checkout. Its
authoritative `master` tag migrates completely; `legacy-2025` remains frozen,
unimported historical state after a zero-cross-tag audit. The legacy
`aegis_foundation` health helper is part of that frozen workflow and is not
repaired for native onboarding.

The Obsidian vault is an output path, not a project rig. Never run
`gc rig add` against it; `bin/vault-sync` reaches only the explicitly
configured `GasCity/` subtree through its exec order.

Dispatch with native `sling` + pack formulas. "Report-style" tasks are
just a formula whose agent comments and closes the bead — no lifecycle
machinery. Obsidian projection is `bin/vault-sync` run as a native
**exec order** (mechanical work: no agent, no LLM, no work bead) — see
`docs/plans/workflow-draft.md`.

Routing an existing bead as itself is the other direction, and it has to be
explicit:

```sh
~/gascity/bin/gc sling <rig>/<agent> <bead-id> --no-formula --no-convoy
```

Without `--no-formula`, a target carrying a default sling formula (`builder`
carries `mol-do-work`, a v2 formula) instantiates it and starts a nested
workflow around the bead; without `--no-convoy` the route also mints an
auto-convoy. Both are command discipline rather than a gate — see
`docs/native-findings.md`.

## The city builds the city

After the first watched bead succeeds, the city's own remaining backlog
becomes its workload. This is deliberate: the best possible live traffic for
a young city is work you can verify by looking, whose failure costs nothing,
and which you were going to do anyway.

Bootstrap through the first watched bead is manual; do not build a machine to
do it, and do not gate bootstrap on the city working. But from bead one
onward, dispatch the rest of this plan *through* the city:

- **`gas-city-template` rig** (this native-template worktree): its explicit
  onboarding choice is fresh start. Its first bead extracts the live-proven
  Taskmaster conversion/reconciliation layer from `archive/review`, adapts the
  archived contract tests to the installed native interfaces, and completes
  the disposable scratch-rig two-pass no-op proof. This is the first watched
  bead; it does not touch a real project's task state.
- **`gascity` rig** (a clone of the upstream repo): the #4858 lease-race PR
  follows the bridge extraction — branch from then-current upstream `main`, the fix
  rebased there, an upstream-shaped test, PR text. (The bridge patch stays
  pinned to `v1.4.0`; only the PR chases `main`.) The credential-argv
  upstream filing is the second bead (sanitized: mechanism only, no
  deployment details — the standing rule).
- **`hpfetcher` rig**: its actual feature/fix backlog, only after the operator's
  quiet point and the complete-history authority cutover.
- **`blog` rig**: Phase 5's PRD-decomposition testbed, only after the complete
  authoritative `master` tag cutover. Its in-progress Task 43 continuation
  remains in progress and resumes under the migrated bead.
- **`obsidian` vault**: projected by `bin/vault-sync` via an exec order
  (no agent involved); agent-written worklogs per the workflow plan.
- Later beads: onboarding each next rig is itself a bead (add-rig command,
  first watched session, notes on anything surprising).

Two things stay out of the city's hands: anything touching the parked
hardened deployment, and any host-level change (`hidepid`, fstab, systemd).
Those are operator actions, done by hand, recorded in a note.

This is also where the observer principle gets its first exercise: watching
the city do this work *is* the verification. If a session misbehaves, you
saw it, you have the transcript, and you fix the config or file the bug —
no gate, no candidate, no allocation.

## Day one, in order

0. **Preconditions:** (a) verify the committed bridge patch at
   `patches/gc-v1.4.0-pending-create-lease.patch` — extracted from the
   fork's reviewed fix (test `08ffbba2`, fix `62a03b70`) and ported onto
   `v1.4.0`, which remains the current release. Its exact base, full source
   lineage, digest, application steps, and red/green checks are recorded in
   `patches/README.md`. The upstream PR is a
   **separate target**: prepare it against current `main` (`11119644…`,
   206 commits ahead at audit time — defect and credential projection both
   still present there, adjacent lifecycle code moved:
   [lease code](https://github.com/gastownhall/gascity/blob/11119644040a09a76f3356bae1d8e456a818f5d6/cmd/gc/session_reconcile.go#L220),
   [credential projection](https://github.com/gastownhall/gascity/blob/11119644040a09a76f3356bae1d8e456a818f5d6/internal/runtime/tmux/tmux.go#L491)).
   (b) `GC_HOME` isolation verified per the Layout section. Nothing below
   starts until both hold.
1. Install gc 1.4.0 **with the bridge patch applied**; initialize the city
   with the full explicit command (v1.4 requires `--default-provider`
   with an explicit template):
   `gc init --template gascity --providers claude,codex --default-provider claude ~/gascity/city`
   — the gascity methodology pack's requirements/planning/decomposition
   formulas are the native path Phase 5 of the workflow plan inspects
   first. The lease race is
   not optional to care about on day one: first sessions do slow
   first-run downloads, which is exactly the >60s startup profile the
   unpatched binary kills. While the patch is applied, the binary is
   *upstream 1.4.0 base plus one temporary reviewed source delta* — it
   becomes stock in the first upstream release containing the fix, and
   the patch is deleted then (a merged PR alone changes nothing we run).
2. On a new city, install the `city.toml` above, `hooks/claude.json`, and the
   trusted `.codex/config.toml`. Declare each opted-in Codex project once in
   `managed/rig-permissions.json`, then run
   `bin/gct-managed-rig-permissions --apply --json`; the versioned tool renders
   the included permission fragment atomically from the declared protected
   checkout, canonical sibling-worktree root, agent identities, and optional
   provider selector. A v1 record with no `provider` remains the byte-compatible
   Codex form. Setting `"provider": "claude"` on the same record binds those
   agents to Claude Opus 5.5 with `auto-edit` and exactly two generated
   `--add-dir` grants: the canonical worktree root and the protected checkout's
   `.git` directory. Those grants ride the derived `claude-managed` provider,
   not `[providers.claude]`: the root `city.toml` declares the reviewed Claude
   picker, and gc's include composition keeps the root's `options_schema` and
   silently discards a fragment's. `base = "provider:claude"` with
   `options_schema_merge = "by_key"` resolves the reviewed model picker and
   permission modes onto the managed option instead of competing with them.
   Setting `"provider": "codex-managed"` selects the same derived-provider
   pattern for a root city that already owns `[providers.codex]`. It pins
   GPT-5.6 Sol, xhigh effort, and fail-fast approvals, and its generated
   `worklog_access` choice contains exactly the canonical worktree root and
   protected checkout `.git` path — never the classified vault. The reviewed
   Gas City deployment record is
   `managed/profiles/gascity-codex.json`; install those bytes as the live
   instance's `managed/rig-permissions.json` before applying the renderer.
   `"codex-managed-worklog"` uses a separate derived provider for project
   workers that must also write the classified worklog. Its generated choice
   contains exactly the classified vault, canonical sibling-worktree root, and
   protected checkout `.git`; it never grants the protected checkout itself.
   `managed/profiles/blog-codex.json` is the reviewed example and also pins the
   Blog Node and pnpm runtime. These two selectors keep the root-owned
   `[providers.codex]` schema untouched while making vault access an explicit
   per-project decision rather than an accidental fleet default. The portable
   default registry remains empty, and legacy Codex records retain
   their canonical record digest and historical generated-provider bytes. A
   rig with no declaration stays on the
   classified-vault-only Codex provider default, and Claude's generated option
   stays on its explicit `none` choice. Under the v2 schema one rig may declare
   several disjoint records, so a project can carry a signing-capable worker and
   a separate candidate-only worker without either inheriting the other's
   grants; v1 still refuses a duplicate rig name, and in both schemas one
   qualified agent may be patched exactly once. A v2 record may set
   `"git_metadata": false`, which grants no common Git directory at all — the
   path reaches no writable root, no flag and no label — and a `claude` record
   that does so may bind a `control_policy` naming a template-relative policy
   file and its `sha256`. The renderer verifies those exact bytes, requires the
   file to declare `gc.candidate-control-policy.v1` with
   `profile_kind: "candidate"`, and renders `--settings <policy>` ahead of the
   `--add-dir` grants, so the candidate agent's selected choice carries its own
   narrow control set instead of inheriting the broad default. That choice is
   rendered into the dedicated `claude-candidate` provider
   (`templates/claude/candidate-provider.toml`), never the generic
   `claude-managed` one: the generic launch also loads the city's shared
   settings, and Claude Code unions permission rules across setting sources, so
   the shared file's bare `Edit`/`Write`, vault directory and sandbox escapes
   would have applied beside the policy (gct-lagl). The candidate provider
   launches `bin/gct-claude-candidate-worker`, which reuses the unchanged Core
   signing-worker boundary (exact argument vocabulary, shared settings removed,
   no ambient setting sources, subscription-only authentication) with the
   candidate policy and the dedicated candidate worktree root
   `/home/loucmane/gas-city-ops-candidate-worktrees` (disjoint from the
   coordinator's Operations worktrees), and patches the agent
   to `full-auto` (`dontAsk`). The candidate policy itself bounds the native
   file tools to `Edit(//home/loucmane/gas-city-ops-candidate-worktrees/*/**)`, denies the
   worktree `.git` link and native reads of the classified vault, and keeps
   project shell work in a fail-closed sandbox. The wrapper refuses a session
   whose working directory is not a physical direct child of that root with a
   `.git` gitfile naming one worktree admin directory of the Operations
   repository whose own `gitdir` points back at it and whose `commondir` is
   `../..`; Core starts
   the session in the routed Bead's `gc.work_dir`. The policy also denies native
   reads of the credential stores. A candidate record's environment is PATH
   only: absolute entries that resolve outside its own root (existence,
   ownership and writable entries or ancestors are checked live at
   activation). A
   record that still grants Git metadata may not select that policy, and neither
   may a non-`claude` provider. `managed/profiles/gascity-operations-candidate-claude.json`
   is the reviewed two-record example. The render report also carries
   `requested_agent_selectors`, the `<rig>/<agent>` strings the renderer writes
   into `[[patches.agent]]` and the controller rebuilds verbatim, so a consumer
   matches a produced fragment instead of rebuilding the string by hand. Read
   them as requests, not as identities: an agent's identity is
   `Dir/BindingName.Name`, `BindingName` is set by the binding import and is
   `toml:"-" json:"-"` in Core, so it cannot be recovered from a raw agent
   record and this stage cannot resolve it. The report says so in
   `agent_identity_resolution`, and `--require-resolved-agent-identities`
   refuses rather than guess. Measured against the real composer, one registry
   spelling resolves three ways — `gascity/operations-candidate-worker`
   unbound, `gascity/gc.operations-candidate-worker` under an import aliased
   `gc`, `gascity/ops.operations-candidate-worker` under one aliased `ops` — so
   an earlier revision's unconditional `<rig>/gc.<agent>` was right only under
   one alias it could not observe. `gc agent list --json` reports the composed
   identity for a real city; `tests/fixtures/agent-identity-resolution-fixtures/`
   reproduces all three from isolated local-pack cities. Rendering
   a policy proves the launch binding, not the live client's effective
   permissions. Typed candidate or signing receipts require exact compatible
   consumer proof before publication: `bin/gct-managed-worker-provision`
   resolves the explicit city's canonical platform manifest and accepted
   receipt, derives the installed Core bytes and activation commit, and binds
   them to an externally reviewed `gct.core-typed-support.v1` witness whose
   complete-file digest is independently supplied. The fixed `version --json`
   response corroborates that binding but cannot establish support by itself;
   any mismatch refuses before publication, with the whole binding revalidated
   immediately before each possible write.
   The runner preserves Core's complete selected profile and exact composed
   identity, then compares it with the unique same-name receipt profile rather
   than reading index zero or rebuilding an alias. The candidate canary worker
   runs no Git command,
   because `git_metadata: false` grants no common Git directory; its worktree is
   prepared by the coordinator and verified afterwards.
   The separate reviewed Core implementation profile is
   `managed/profiles/gascity-claude-signing.json`. It keeps the registry selector
   `provider: "claude"`, but a generic `gc.worker-control-policy.v1` policy with
   `profile_kind: "signing"` is accepted only when `git_metadata: true`; the
   existing candidate schema remains valid only with `git_metadata: false`.
   Signing records render through the new `claude-signing` derived provider,
   whose explicit `full-auto` choice resolves to `--permission-mode dontAsk`
   under the closed policy. Records with no policy retain their prior provider
   and rendered bytes; candidate records now render through `claude-candidate`
   (gct-lagl, above).

   The Template implementation worker has a separate candidate lane rather
   than sharing the Operations wrapper. Its reviewed source record is
   `managed/profiles/gas-city-template-candidate-claude.json`; it names only
   `implementation-worker`, grants no Git metadata, and binds
   `templates/claude/template-candidate-control-policy.json`. Candidate policy
   selection is an exact literal map: the Operations policy renders through
   `claude-candidate`, the Template policy through
   `claude-template-candidate`, and any other candidate source spelling is
   refused. The latter provider launches
   `bin/gct-claude-template-candidate-worker`, removes shared settings, loads
   only the Template policy, and grants one directory:
   `/home/loucmane/gas-city-template-candidate-worktrees`. Each session must
   start in a physical direct child linked to
   `/home/loucmane/gas-city-template/.git`; the coordinator's ordinary
   Template worktree root remains disjoint. This is root separation, not
   per-Bead isolation: one worker can reach another child of the candidate
   root, so intake must never assume candidate worktrees isolate Beads.

   Activation is a separate coordinator operation after merge. It creates the
   dedicated root and worktree, rechecks the `.git` gitfile plus admin
   `gitdir`/`commondir` back-pointers before every coordinator Git operation,
   installs the policy with no group/world write bit, publishes the typed
   candidate receipt, and stamps each routed Bead's `gc.check_path` to the
   receipt profile's exact check path. It must remove the live pack-rig
   `[[rigs.overrides]]` mutation that currently forces
   `implementation-worker` back to plain `claude` with `auto-edit` and the
   coordinator worktree/Git grant. Pack overrides apply after city patches, so
   a surviving override silently cancels this lane; activation must inspect
   the composed configuration and refuse unless the provider is
   `claude-template-candidate` and permission mode is `full-auto`. The
   `run-operator` override and its current grant remain unchanged. Activation
   must also inspect the imported implementation-worker prompt at the pinned
   pack commit: prompts or formulas that ask the worker to create worktrees,
   commit, push, or open PRs conflict with this uncommitted-delivery lane and
   require a lane prompt or an explicit recorded justification.

   Core currently keys provider pins by provider name while readiness accepts
   only built-in names. The Template receipt therefore correctly keeps
   `provider.name = "claude"` and pins its own wrapper path and digest, just as
   the Operations candidate does. With two distinct Claude wrappers in one
   receipt, Core's whole-environment comparison and platform canary cannot
   pass; never reuse the signing wrapper pin as a workaround. Live dispatch is
   unaffected because no live rig sets `managed_product`. This known limit is
   tracked by Core Bead `ga-qcwl`; the profile-scoped launch Preflight and
   existing `candidate-launcher` remain the applicable source proofs, while a
   new receipt digest also makes prior profile-scoped canary receipts stale.

   The `gct-claude-signing-worker` entrypoint owns both initial and resumed
   launches. It recognizes and removes the Claude-family generated shared
   settings path, selects an empty native setting-source list, and passes only
   `templates/claude/core-signing-control-policy.json`. This is necessary
   because the shared settings grant the classified vault in both
   `permissions.additionalDirectories` and `sandbox.filesystem.allowWrite`;
   adding a narrower second file does not subtract either grant. The closed
   policy repeats the reviewed native hooks but contains no vault, provider-key,
   protected-checkout, or unrelated-project grant. It binds the native file
   tools to the Core worktrees with one absolute `Edit(//...)` rule and denies
   the worktree `.git` link: a bare `Edit` or `Write` grant is unbounded, and
   Claude Code checks the Write tool against Edit rules (ga-e0t1.14,
   2026-09-17). Project shell work stays sandboxed and auto-approved; a command
   with leading variable assignments is not classified and is denied, so the
   offline Go settings travel in the policy's `env` block and the worker brief
   names its commands without assignments. The sandbox opens one path for writes
   beyond the working directory, the session temp directory and the two
   `--add-dir` grants, the Go build cache, so the compile proof can run inside
   it; the module cache stays read-only. Its six unsandboxed command patterns
   are exactly claim, drain, show, update, close, and the managed commit
   frontend fixed to policy `gascity-core` and the Core worktree root, and they
   are the only Bash patterns the policy allows by rule.

   Core's tmux prompt delivery appends one positional argument to the initial
   launch after the closed provider options; long prompts use the same single
   argument after `$(cat ...)` reconstruction, including trailing newlines.
   The worker therefore accepts at most one final non-option prompt on an
   initial launch and forwards it byte-for-byte. Empty prompts are represented
   by no positional argument, while resumed launches carry `--resume <key>`
   and no startup prompt. Extra positionals and option-like prompt values stay
   refused so this narrow transport does not become a general argument
   interface.

   The fixed shell entrypoint starts `/usr/bin/python3.12` with `-I -S -B`
   before any Python import. The worker is executed directly from source and
   loads the subscription module from a stable bounded source read, so ambient
   site hooks, Python environment/import paths, and cached bytecode cannot
   substitute executable launch code. The receipt digest uses those exact
   compiled source bytes. Before every launch the entrypoint rejects caller-owned settings, permission,
   root, session, provider, billing, and authentication overrides; removes only
   `ANTHROPIC_API_KEY` without reading its value; and uses Claude's native
   `auth status --json` to prove first-party subscription posture. The final
   `exec` preserves the validated non-settings argv, cwd, GC/Beads identity,
   environment, and stdio. Its receipt-facing version output digests the native
   Claude CLI, entrypoint, both imported Python modules, the closed policy, and
   provider template; the v2 profile also pins Claude, Python, and Go as exact
   toolchains, including the verified Python 3.12.3 artifact digest
   `e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`.
   Thus a pinned wrapper cannot hide a changed CLI or import.
   Publishing this source profile does not activate it or prove a live Claude
   inference or managed signature; those remain separate witnessed acceptance.
   An existing city is a different
   contract: never copy the template `city.toml` over an evolved city. After
   fast-forwarding the canonical source checkout to the reviewed merge, run
   `bin/gct-attention-funnel-install --plan --json`, inspect the exact managed
   inventory, run `bin/gct-attention-funnel-install --apply --json`, and finish
   with `bin/gct-attention-funnel-install --check --json`. The installer adds
   only the `managed/attention-funnel.toml` include, transactionally owns the
   attention agent, hook, order, two-prefix Codex policy, and bounded
   `.codex/config.toml` shell-environment files, validates a complete shadow
   composition before its first write, and preserves a byte-exact rollback
   bundle. It requires every project rig suspended, zero
   sessions, an unchanged supervisor epoch, and two identical native readbacks
   of the Terra/Fable named sessions, agents, event wakes, and cron retries; a
   second apply is a no-op. Run
   `bin/gct-codex-rules --apply --rig <name>` for one Codex-enabled project
   instead of copying policy files by hand. The reviewed
   profile authority is `templates/codex/rules/profiles.json`: its default
   composes the 14 native-control stanzas, while the explicit
   `gas-city-template` mapping adds only the separately reviewed signing
   overlay and pins the exact 15-stanza digest. To reconcile every discovered
   Codex rig, first run `bin/gct-codex-rules --check --all --json`, inspect the
   versioned doctor result, then run `bin/gct-codex-rules --apply --all`.
   Fleet apply performs a complete path/profile/classification preflight before
   its first write; any unknown rig or unsafe destination refuses the whole
   operation. It also invokes `bin/gct-provider-command`: the managed
   `~/gascity/bin/codex` symlink must point lexically at the updater-owned
   `~/.codex/packages/standalone/current/bin/codex` indirection, never a
   rotating release or shim directory. `--check` reports missing, unstable,
   unmanaged, or non-executable commands without writing; `--apply` repairs
   only missing or already-managed symlinks and refuses regular files.
   Repeating a green apply is byte-for-byte inert. Record
   `bin/gct-codex-rules --version` with the onboarding evidence; own-password
   local Dolt store (low-value, per-project — assume argv exposure until upstream fixes it). Re-run hook
   installation and prove every managed hook command names
   `~/gascity/bin/gc`, never bare `gc`. From a managed Codex session, also run
   the literal `command -v gc; gc version`: it must resolve the isolated
   binary and bridge version without a command-local `PATH` prefix.
3. Verify `hidepid=2` still holds **by witnessed failure**: repeat the
   non-operator `cmdline` read against a running process and observe it fail
   (ENOENT/EACCES), exactly as the original precondition receipt did.
   Re-reading mount options is a claim, not evidence — the ledger's own
   rule applies to this plan too.
4. **Operator pre-dispatch disciplines — manual, not gates.** Run
   `bin/gct-codex-rules --check --all --json` as the versioned, doctor-grade
   non-blocking fleet observer (the text form remains available for humans);
   its non-zero result is visible evidence and is not wired into dispatch until
   it earns promotion against live traffic. Record the
   vault replication/content classification before either writer uses it;
   confirm every repo input the city will run (`city.toml`, fragments,
   formulas, and `bin/vault-sync` when present) corresponds to a pushed,
   fetchable commit; and, whenever the projector changed, run
   `tests/test_vault_sync.py` green. Enumerate the rig's open/claimable beads
   and select the intended first bead before native claim selection. Inspect
   the persistent worktree for dead-session residue, preserving and
   dispositioning anything unexpected rather than cleaning blindly. Locate
   gc's native transcript and exit-state surfaces before dispatch, and make
   survival after teardown an acceptance observation of the watched run — no
   custom capture machinery. If inventory and process state ever disagree,
   `/proc` is the diagnostic evidence. If the two cities ever interact in an
   attended window, enumerate the complete quiescence set first; otherwise
   that discipline is not applicable. These are operator confirmations and
   observations, not scripted refusals.
   Managed Claude workers are non-interactive by explicit role class.
   On WSL, install both `bubblewrap` and `socat`, and pin managed-session
   `TMPDIR=/tmp`: Claude's sandbox relay requires Unix sockets and a Windows
   `/mnt/c/.../Temp` path refuses them with `ENOTSUP`. Treat these as day-one
   preconditions, not an incident-time repair.
   The open-vocabulary roles inherit `auto-edit`, which resolves to
   `--permission-mode auto`, and run with the sandbox enabled,
   `sandbox.failIfUnavailable = true`, and the unsandboxed escape hatch
   disabled. The closed-command roles must be named explicitly and may select
   `full-auto`, which resolves to `--permission-mode dontAsk`, only with the
   closed allowlist in `hooks/claude.json`. Never add `Bash(*)` to make an
   open-vocabulary role fit `dontAsk`; that erases the host boundary rather
   than widening it safely. The static linkage audit checks this pairing, and
   live acceptance uses a real imported role plus a representative
   implementation worker, not the simpler sweeper rehearsal. It also proves
   once that an unavailable sandbox refuses launch instead of falling back,
   then prove a real sandboxed command succeeds with the native WSL temp path.
   During any watched run, if no new event appears for 45–60 seconds, inspect
   the pane with `gc session peek`. A visible permission prompt is
   `waiting_for_approval`, not active work: never nudge a tool-blocked worker.
   Stop and report the role-policy or sandbox failure.
   Managed Codex workers also run in `workspace-write` with the already
   classified `/home/loucmane/vaults/main/GasCity` root added through
   `sandbox_workspace_write.writable_roots`. Keep this on the provider launch
   policy so it applies to rig-scoped sessions without broadening the user's
   global Codex configuration. The grant exists only for the ratified worklog
   contract; it does not enable network access or full-access mode.
   Keep that vault-only choice as the provider default. A project whose
   repository policy places implementation worktrees outside the rig root must
   opt in through one `managed/rig-permissions.json` record. The renderer names
   no projects: it derives an exact digest-named worklog choice and
   binding-qualified agent patches from the record while preserving the one
   Codex provider identity. The same record is the
   authority for both worktree placement and writable roots; never replace it
   with a broad parent, an approval bypass, or a second hand-authored choice.
   Verify the generated fragment and resolved launch arguments before resuming
   a claimed worker.
   Codex's network-disabled sandbox cannot perform Gas City's native claim and
   Beads control traffic: the cache lock is opened read/write and the session
   fence lives on the local Dolt control plane. The `ci-dptc` witness stopped
   at the lock, while a throwaway cache copy then lost the fence and falsely
   reported `no_work`. Do not add the cache or network to the sandbox. Instead,
   trusted project-local `.codex/rules/gas-city-native-control.rules` allows
   only the enumerated absolute `gc` and `bd` prefixes to run outside it. The
   rules are checked before live use with `codex execpolicy check`; wrapped
   commands and unrelated commands must remain non-allow decisions. There is
   no network enablement, full-access mode, user-global rule, or generic shell
   prefix.
   Managed commands inherit the pinned environment and execute one absolute
   operation so the rule engine sees the real argument vector.
   A committing worker's record grants its canonical sibling-worktree root and
   the linked-worktree Git common directory `<repository_path>/.git` beside the
   classified vault. The Git root is required because `git add` and signed
   commits for a linked worktree write its index and lock under the common
   directory; granting only the sibling worktree files produces a correct
   read-only-filesystem refusal. The renderer never grants the protected
   repository root, and it refuses `/tmp`, nested roots, duplicate records, and
   symlinked path components before writing. `--check --json` emits
   `gc.managed-rig-permissions-check.v1`; `--apply` validates a staged fragment
   with `gc config show --validate -f` before atomic rename and is byte-inert
   when already conformant. Both modes first resolve the fragment against the
   composed city rather than in isolation: a provider name any earlier layer
   already declares, or a patch selecting an option that provider does not
   carry, is refused before anything is written. A conformant fragment whose
   schema the composed city would drop is a half-applied grant, and the worker
   launches with its reviewed model and no `--add-dir` root at all.
   The sandbox intentionally cannot open GPG-agent Unix sockets. Managed
   workers therefore never receive `~/.gnupg`, private-key files, network, or
   generic `git commit` authority. A managed project worker stages and freezes
   an index,
   then calls the pinned but untrusted
   `/usr/local/libexec/gas-city/managed-git-commit` frontend with one reviewed
   policy name, literal bead and session audit identities, the exact worktree,
   parent HEAD, staged tree, and bounded subject. Environment variables are not
   an alternate identity path, so the bare helper path remains visible to the
   narrow exec-policy rule. A separate `gas-city-signer` identity reloads the
   root-owned policy, disables hostile repository configuration, independently validates
   the worktree/common directory and frozen parent/tree, writes a fsynced WAL,
   and only then returns one signed commit object. The frontend writes that
   exact object and advances the branch by compare-and-swap; signer-side
   finalization revalidates the result before writing a service-signed v2
   receipt. The root-owned v2 manifest binds separate Gas City, HPFetcher, and
   Blog worktree/common-directory roots and audit state while all three reuse
   one signer-owned key home and socket; secret bytes are never copied between
   projects. Worker bead/session values are audit claims, not authorization.
   Recovery is journal-backed and cannot synthesize a receipt from a Good
   signature alone. Direct `git commit -S`, direct `gpg`, and direct access to
   the service backend remain denied. Each project-local rules profile admits
   only its matching policy and direct-child worktree root, and startup
   recovers every manifest policy before accepting a request. The template rig
   has no signing profile;
   its former personal-key policy stays disabled until a distinct non-personal
   identity is separately designed and reviewed. See
   `docs/managed-signing-service.md` for the custody and cutover contract.
   The project-owned prompt preserves the generic pool worker's claim,
   molecule, escalation, and drain contract while spelling every native
   control operation with the isolated absolute binary. The one-session cap
   serializes the native-control acceptance bead ahead of the preserved
   journal workflow and prevents two demand records from racing through the
   same ephemeral pool. Raise it only in a separately reviewed capacity
   change after this lane is proven.
   Before resuming an existing workflow, inspect the fresh worker argv, prove
   the allowed claim and a forbidden unrelated command with
   `codex execpolicy check`, and confirm no network enablement or approval
   bypass. Retire or re-justify the rig override if per-bead claim-time option
   resolution later makes it unnecessary.
5. Record **fresh start** for `/home/loucmane/gas-city-native`, onboard it as
   `gas-city-template`, and run the Taskmaster bridge extraction as the first
   watched bead. The bead completes the adapted contract tests and disposable
   scratch-rig compatibility/no-op rehearsal before the bridge is usable on a
   real project.
6. When — and only when — the operator declares hpfetcher's quiet point,
   reconcile its fetchable branch state without touching operator-owned work,
   freeze Taskmaster, migrate complete history under the attended runbook,
   record the authority cutover, then register the rig and run one real bead
   end to end. Until then, hpfetcher waits outside the city.
7. Reconcile and onboard the blog under its per-tag decision, then use it for
   the watched Phase 5 PRD-decomposition ladder. The root PRD is a reviewed
   transformation of `.taskmaster/docs/prd.txt`, not a silent replacement.
8. Continue city-builds-city mode (section above): `gascity` rig, the
   upstream PR bead, then the rest of the backlog as beads.
9. Onboard Aegis **last**, and only when the city has run real work for the
   other rigs without surprises. Nothing about this plan forces Aegis in —
   it arrives when the city is boring and only after its own migrate-versus-
   fresh decision is recorded.

## Operator handoffs are event-driven

There is no persistent model-backed handoff session. Workers send durable
`NEEDS_OPERATOR <bead>` or `REVIEW_READY <bead>` mail to configured
`on_demand` named-session identities. Those identities reserve stable mailbox
addresses even while no provider process exists. The mechanical
`orchestrator-mail-wake` order materializes or wakes the rig-scoped Haiku
messenger only when matching unread mail exists; an unchanged or empty scan
starts no model and consumes no provider tokens. Haiku delivers an already
structured human-ready handoff and self-closes so later events cannot inherit
an ever-growing conversation. The separate controller-failure path below does
not use this rig messenger.

Hard controller failures and claimed-worker stalls enter through a separate
triage seam. Core marks the affected bead `needs/operator` with the source
session, last observed progress time, and evidence. The mechanical
`orchestrator-attention-relay` order preserves that evidence exactly once in
mail to the stable city-scoped `watch-officer` mailbox. A token-free recovery
scan covers missed events across controller restarts; stable controller
signatures prevent duplicate mail. Event-driven and one-minute mechanical
retry orders then materialize the explicit T1-to-T4 funnel without resending
the incident or starting a model for unchanged state:

1. T0 emits a strict `gc.attention.event.v1` envelope.
2. T1 `watch-officer` runs Codex Luna at low effort and either stops, advances
   the evidence to Terra, or requests human review.
3. T2 `attention-terra` runs Codex Terra at high effort only after an exact
   Luna escalation.
4. T3 `attention-fable` runs Fable only after an exact Terra escalation and
   remains advisory.
5. T4 is an explicit human authorization envelope. No model output can resolve
   a gate or authorize a mutation.

Luna and Terra use the dedicated two-prefix `attention-control` Codex policy;
their identity-checked helpers expose only inbox, bounded Bead readback, and a
closed decision command. Fable launches through `claude-attention`, whose
helper-only settings expose only its identity-checked control surface (plus the
separate rig messenger helper for that role). Direct `gc`, `bd`, arbitrary
Bash, file, skill, merge, publish, restart, and gate-resolution commands remain
unavailable. All three mailboxes are stable city-scoped `on_demand` identities
and every turn self-closes.

Provider readiness and provider execution share the canonical managed Claude
binary at `/home/loucmane/gascity/bin/claude`. The provider `path_check` and
the wrapper default must name that same executable; the transactional installer
migrates the exact retired `/home/loucmane/.local/bin/claude` predecessor but
refuses every other path. This prevents a readiness check from accepting or
rejecting a different executable than the closed wrapper actually launches.

The Luna and Terra identities select the derived `codex-attention` provider.
Its source-owned wrapper always launches Codex with `--disable hooks` and
`check_for_update_on_startup=false`, and refuses caller-owned feature, update,
profile, or bypass overrides. These report-only roles need no project hooks:
the closed exec-policy profile is their complete command authority. Keeping
hook trust and update interstitials out of this unattended path prevents either
surface from consuming the first inbox instruction without weakening ordinary
Codex sessions.
The city-local `.codex/config.toml` also applies a closed shell-environment
allowlist. It retains only ordinary shell context plus `GC_ALIAS`,
`GC_SESSION_ID`, `GC_SESSION_NAME`, `TMUX`, and `TMUX_PANE`, while Codex's
default secret-name exclusions remain active. The static `GC_BIN`, `GC_HOME`,
and `PATH` values are reasserted inside that same allowlist. This permits a
Codex tool subprocess to prove its runtime identity without inheriting
arbitrary provider or host variables; the helper still validates every
identity and treats environment as routing context, never authority.
The wake order treats `start-pending` as an intermediate state, observes
readiness for a bounded interval, and closes a timed-out materialized session
before recording the explicit provider-unavailable fallback.
Immediately before a successful attention decision closes its own supported
session, the control helper arms `exit-empty` on that session's current tmux
server. Other sessions are untouched; when the final bounded turn closes, the
empty shared server exits naturally without a PID or process-group signal.

The controller binds event, decision, downstream output, and append-only
receipt digests. It admits one decision per source message, recovers an exact
retry without duplication, and refuses divergent decisions or conflicting
downstream evidence. Provider failure is never a silent model substitution:
it records `provider_unavailable` and advances mechanically Luna to Terra,
Terra to Fable, and Fable to the human boundary. Agents never poll or watch;
empty retry scans invoke no provider.

Deployment is source-bound rather than a manual copy recipe. Use
`bin/gct-attention-funnel-install --plan --json`, then
`bin/gct-attention-funnel-install --apply --json`, and prove the result with
`bin/gct-attention-funnel-install --check --json`. The included
`managed/attention-funnel.toml` owns the derived Codex attention provider and
only the Terra and Fable named identities;
the live root retains its existing Luna/watch-officer and backward-compatible
orchestrator identities and every unrelated provider, rig, and patch. The
installer publishes the exact changed watch-officer bytes and new Terra/Fable
assets plus the bounded city-local Codex environment policy while all rigs are
suspended, so an evolved city never receives a whole-file template copy. The
project policy file is included in the installer's exact inventory, backup,
rollback, postflight, and no-op proof rather than copied by an operator.

Gas City mail is the durable record. The `operator-mail-toast` event order
turns only recent unread `NEEDS_OPERATOR` and `REVIEW_READY` human mail into a
desktop notification; that desktop notification is an ephemeral wake-up, not
authority. The controller-side `gct-desktop-notify` adapter selects
WSL/Windows, native Linux, or macOS behavior. Worker sessions may all be WSL or
may run on mixed hosts because they never invoke a desktop API: they emit the
same durable Gas City mail, and only the city controller performs the final
host-specific notification hop. On WSL, clicking the Windows toast opens the
city Mail view; native Linux and macOS notifications include the loopback URL
in their text. If the notification cannot be shown, the mail remains unread
and the order fails loudly without marking anything consumed. The dashboard's
`needs/operator` queue remains the independent durable view for failed
workflow controls.

Known sharp edges (all proven live, none blocking): duplicate dispatch is
possible — notice and close it; the credential and tmux rules above stand.
The watched bridge bead also found the native behaviors recorded in
[`docs/native-findings.md`](native-findings.md); use their explicit workdir,
suspension-verification, and prefix-disposition workarounds until upstream
changes the relevant surfaces.

A weekend, mostly first-session downloads. Every future gc update: swap the
binary, restart the supervisor. No pins, no fixtures, no reference builds —
because nothing here is a certified wrapper.

## Staying current (design choices, not earned learnings)

Moved here from the ledger under its own rule: these are forward-looking
design decisions, revisable at will, with no incident citations behind
them. The goal they serve: **current upstream, current models, current
practice — verified cheaply, forever.**

1. **Currency by construction.** Upstream-base binary (stock once a
   release contains the #4858 fix) means an upgrade is
   swap-binary-and-restart, so there is no
   reason to lag. Being in upstream's contributor flow (the #4858 PR, the
   argv filing) means learning of changes by participating, not auditing.
2. **A recurring currency bead** in the `gascity` rig (monthly, or on
   release): check the gc release feed, re-check the two upstream issues,
   check provider model lists against `city.toml`, bump what moved, run one
   watched session. Done *by the city*. This is the surviving fraction of
   the old upgrade-pipeline plan, with the radar/fixture machinery deleted.
3. **Model menu as a living artifact.** New model ships → add the entry,
   preflight it once live (the dated-id lesson applies), start using it.
   One config edit, not a certification.
4. **Observer-first as standing practice.** Shadow-mode checks promoted on
   evidence; the dogfooding loop (the city dispatching its own backlog to
   current models) continuously exercises exactly the paths that matter.

The one *earned* rule constraining all of the above lives in the ledger:
any proposed gate, pin, or certification step must cite the live incident
that earned it.

## Repository history (transition completed 2026-08-02 — nothing here to execute)

One repo: this one. `gas-city-template` is the template for the
workflow. The transition has already happened; this section is the
record, not an instruction:

- **Archive refs, read-only forever** (never rewritten, never deleted):
  `archive/hardened-main` (`109dbfe…`, pre-transition main),
  `archive/hardened-checkpoint` (`a6c4f768…`, the final installed G66
  head), `archive/review` (`b087afd…`, the ratified ledger head).
  PR #7 is closed with pointers to these refs.
- **`main` is an orphan root** (`1658c9a…`, zero shared history)
  carrying the template; the bridge patch landed at `5abba19…`.
- The optional `hardened-final`/`ledger-ratified` **tags** remain an
  operator option — tag pushes were blocked from the transition
  environment; the archive branches serve as the durable refs meanwhile.
- The parking handoff receipt is owner-only on the deployment host
  (SHA-256 `08f65c82…`).

Out of this repo, unchanged: the upstream PR lives on a fork of
`gastownhall/gascity`; rigs remain external repos the city points at.

## Coexistence with the parked hardened city

The hardened city is suspended, not gone. While it exists on the host:

- This city never touches `/home/loucmane/gas-city`, its Dolt containers,
  databases, credentials, worktrees, or its evidence trees.
- A shared-profile compatibility symlink at `~/.local/bin/gc` still resolves
  to the parked `1.3.5-aegis.1` binary. It remains untouched for resumability;
  this city uses its declared environment and absolute `~/gascity/bin/gc`
  path instead.
- The Aegis repo joins *this* city only at step 8 above, and when it does,
  the rig points at the repo — never at the hardened deployment's worktrees.
- If the hardened campaign is ever resumed, its first step is the documented
  `ags-wvfp` native recovery, and this city quiesces during its attended
  windows. If it is instead retired, retirement is its own small checklist
  (credential retirement, evidence archival) written at that time — nothing
  in this plan needs to change either way.

## Opt-in unsigned candidate control profile

The September 21 gct-m1wh startup incident distinguished an unmatched direct-GPG
command from an explicit prohibition. The existing default profile intentionally
has no direct-GPG allow rule; that alone does not satisfy an explicit-denial
contract. Do not relabel `matchedRules: []` as a refusal.

`unsigned-candidate` composes the unchanged native-control rules with a
`forbidden` rule for the reviewed bare and absolute GPG/GPG2 executable forms.
It adds no managed-signing grant. Existing profiles and rig defaults remain
unchanged. Select it explicitly for the reviewed candidate workspace:

```bash
bin/gct-codex-rules --check --work-dir /absolute/reviewed/worktree --profile unsigned-candidate
bin/gct-codex-rules --apply --work-dir /absolute/reviewed/worktree --profile unsigned-candidate
```

The profile is generated by `gct-managed-signing-projects`; regenerate and check
it through that producer, not by hand-editing its digest. The materializer checks
all six executable spellings and requires a matched forbidden rule for this
profile, while retaining unmatched-nonallow checks for existing profiles.

Live application requires the authorized merge-bound lane: preserve the exact
previous rules bytes, mode and owner, validate the source and workspace identity,
then apply, check the full effective user-plus-project rules and prove a second
application is a no-op. The installer can write before returning a policy-check
failure: such a refusal is not pre-mutation. Restore the backed-up image and
verify it before retrying; ambiguous mutation or failed rollback stops.

Static classification does not prove all interpreter/subprocess paths or key
isolation. Existing sandbox, signer isolation and independent fresh-session
acceptance remain required. Never have a running worker amend its own installed
trusted policy; provision before launch. No fleet rollout, signing grant or
worker dispatch is implied by selecting this profile.
