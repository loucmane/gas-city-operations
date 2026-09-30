# Managed worker provisioning

Managed workers use a three-part, versioned contract. The contract is designed
to survive reboots and upgrades without relying on an interactive shell's
`PATH`, `HOME`, or inherited process environment.

1. `managed/profiles/<rig>-codex.json` is source authority for the worker's
   exact environment and toolchain executable pins.
2. `gct-managed-rig-permissions` renders that profile into the managed city
   fragment, including `[patches.agent.env]`.
3. `gct-managed-worker-provision` independently validates the executable path,
   resolved path, bytes, and version output before atomically publishing the
   v2 provisioning receipt and canary runner.

The provider selector is part of the least-privilege contract. Use
`codex-managed` for workers that need only their sibling-worktree root and the
protected checkout's `.git` common directory. Use `codex-managed-worklog` only
when the worker also owns a classified worklog; it adds exactly the Gas City
vault as a third root through a derived provider whose schema survives root
configuration composition. Never recreate either shape as a hand-written
`city.toml` choice.

The controller rechecks the receipt immediately before every managed worker
start. It compares the resolved provider argv, controlled environment, writable
roots, task check, permission revision, provider bytes, toolchain bytes and
version, provider readiness, and the explicit no-sign signer readiness probe.
Any mismatch is a launch refusal rather than a degraded worker.

The platform canary receives the same verified implementation-worker profile.
Before it creates a signed candidate, its worker process runs every pinned
version command and performs a real, network-free Go build in disposable state.
The command transcript and built-artifact digest are preserved with the canary
evidence.

## Candidate-only workers

A candidate-only worker delivers an uncommitted candidate and never publishes.
It is a distinct profile kind, not a signing worker with signing switched off.

- `profile_kind` is an opt-in v2 receipt selector. Omitting it keeps the legacy
  signing contract and the receipt byte-identical. Declaring it commits to a
  valid string: an explicit `null`, boolean or container is refused, because a
  declaration the provisioner cannot honour must not read as an omission.
- A `candidate` profile must carry `signer_identity: "none"`, and a signing
  profile may not borrow that sentinel. Both directions refuse.
- A record may set `git_metadata: false` under
  `gc.managed-rig-permissions.v2`. That grants no common Git directory at all:
  the path reaches no writable root, no flag and no label.
- One rig may carry several disjoint records under v2 only. Under v1 a
  duplicate rig name is still refused. In both schemas one qualified agent may
  be patched exactly once.
- A `claude` record with `git_metadata: false` may bind a `control_policy`:
  a template-relative `source` plus its `sha256`. The renderer verifies those
  exact bytes, requires the file to declare
  `gc.candidate-control-policy.v1` with `profile_kind: "candidate"`, and emits
  `--settings <policy>` into the rendered launch flags. A record that still
  grants Git metadata may not select it, and a non-`claude` provider may not
  either.

The candidate canary is `--scenario candidate-launcher`. It builds no signing
authority, places no key or allowed-signers file in the worker environment, and
leaves the candidate uncommitted at the explicit base.

The kind a run executes as is decided by the complete profile Core selected and
placed in `GCT_CANARY_WORKER_PROFILE_JSON`, not by the caller. The controller
passes no `--profile-kind`, so a run that only checked the flag would have been
unchecked in exactly the invocation that matters. The runner validates:

1. the kind the profile declares, with omission accepted only as the legacy
   signing contract;
2. the signer posture that kind requires — a candidate must carry
   `signer_identity: "none"`, a signing profile may not borrow it;
3. `--profile-kind`, if supplied, checked against the profile rather than
   trusted in its place;
4. the pinned control policy and complete `worker_profile_sha256`; and
5. the exact qualified `name` Core supplied, without adding or removing an
   import alias.

Those checks are settled before the scenario directory, launcher clone,
scratch city or any key exists. The canary fixtures are built from the rendered
record rather than from a literal written beside it.

That string is a patch selector, not a resolved identity. Core resolves an
agent as `Dir/BindingName.Name`, and `BindingName` is set by the import that
binds the agent and declared `toml:"-" json:"-"`, so it cannot be recovered
from a raw agent record. Measured against the real composer, one spelling
resolves three ways:

| composition | resolved identity | equals the selector? |
| --- | --- | --- |
| unbound | `gascity/operations-candidate-worker` | yes |
| import aliased `gc` | `gascity/gc.operations-candidate-worker` | no |
| import aliased `ops` | `gascity/ops.operations-candidate-worker` | no |

So do not prefix a namespace onto a selector to make it look resolved: which
alias a city uses is not observable from a registry record. Note that the
prefixed spelling is not inert — it is how an *imported* agent is addressed.
`AgentMatchesIdentity` compares the patch target against `QualifiedName()`
first, and only falls back to a bare `Dir`+`Name` comparison when
`BindingName` is empty, so a city-level `[[patches.agent]]` naming
`gc.<agent>` is exactly what reaches an agent bound under the `gc` import,
while the bare `<agent>` spelling does *not* reach it. The reverse holds for
an unbound agent. Which spelling matches therefore depends on where the agent
is bound, which is the fact a registry record does not carry. When a real
identity is needed, ask `gc agent list --json`, which emits the composed
`QualifiedName`. Both launcher scenarios retain the exact name in Core's
selected profile; neither owns a hard-coded role suffix.

`tests/fixtures/agent-identity-resolution-fixtures/` reproduces the table above
from three isolated local-pack cities, and its runner fails closed: a composer
that errors, times out, or returns unparsable, ill-typed, missing, duplicated
or unexpected identities exits nonzero rather than reporting a green
observation. The table demonstrates the identity *rule*. It is not evidence
that any rendered fragment has been installed or applied to a city, and no
equality it shows should be read that way. Which identity a particular city
resolves remains a property of that composed city; the runner does not guess it.

The candidate worker runs no Git command at all. Adding a linked worktree and
refreshing an index both write to the repository's common Git directory, which
`git_metadata: false` does not grant. The coordinator prepares the worktree and
verifies afterwards that the delivered candidate is uncommitted at the base;
the command trace records which side ran each command, so coordinator fixture
setup is never read as worker capability.

Rendering a policy file and publishing a receipt are source proofs. They are not
a permission receipt: actual effective permissions and fresh-session behaviour
are proven separately against a live client.

### Template candidate lane

The Template rig uses a second closed Claude candidate wrapper. The source
record is `managed/profiles/gas-city-template-candidate-claude.json`; its sole
record names `gas-city-template`, bare `implementation-worker`, the protected
checkout `/home/loucmane/gas-city-template`, and the disjoint root
`/home/loucmane/gas-city-template-candidate-worktrees`. It declares
`git_metadata: false`, a PATH-only environment, the measured Python 3.12 pin,
and `templates/claude/template-candidate-control-policy.json` with its exact
digest.

The renderer maps candidate sources by their literal declared string, without
normalization. The Operations source selects `claude-candidate`; the Template
source selects `claude-template-candidate`; a copied policy, `./` spelling, or
any other candidate source is refused even if its `_gc` marker and digest are
otherwise valid. Signing remains selected by the signing profile kind. Existing
Core signing and Operations candidate inputs therefore retain their providers
and rendered bytes.

The Template wrapper loads no ambient setting sources and removes the generated
shared settings argument. Its only settings file is the Template policy and its
only `--add-dir` is the dedicated candidate root. At launch it requires a
physical direct child whose regular `.git` file names one worktree admin
directory under `/home/loucmane/gas-city-template/.git/worktrees/`; the admin
`gitdir` must point back to the child and `commondir` must be `../..`. The root
grant spans all children, so this is not isolation between Beads. The worker
delivers uncommitted files; a coordinator outside this lane creates and checks
the worktree, stages, signs, pushes, opens the PR, and merges.

Activation is a separate reviewed coordinator package after merge. It must:

1. create and validate the dedicated root and linked worktree before any
   coordinator Git operation;
2. inspect the imported role prompt/formulas at the pinned pack commit and
   supply a lane-specific prompt, or record why no incompatible Git/PR action
   remains;
3. install the policy as a stable regular file with no group/world write bit,
   remeasure the Python executable, and publish the typed `candidate` receipt
   with `signer_identity: "none"`;
4. pin the Template launch-check script in the receipt and stamp every routed
   Template Bead's `gc.check_path` to that exact profile check path;
5. remove the live `[[rigs.overrides]]` entry that rewrites
   `implementation-worker` to plain `claude`, `auto-edit`, and
   `template-worktrees-and-git-metadata`; then read the composed configuration
   and refuse unless the worker resolves to `claude-template-candidate` with
   `full-auto`; and
6. preserve the unrelated `run-operator` override unchanged.

The override check is a boundary condition, not cleanup: pack-rig overrides are
applied after city-level agent patches, so a surviving override silently puts
the worker back on generic Claude with shared settings and broad grants. The
closed wrapper never runs in that state and therefore cannot refuse it.

Core readiness recognizes the built-in provider name, so the receipt keeps
`provider.name = "claude"` while pinning the Template wrapper's own path,
resolved path, digest, and version. Core currently also indexes its platform
provider manifest by name. Two different Claude wrappers in one receipt make
the whole-environment check and platform canary refuse; do not borrow the Core
signing wrapper's pin. No live rig sets `managed_product`, so this does not
block live routing or the profile-scoped launch Preflight. The limitation is
tracked by Core Bead `ga-qcwl`. There is no new canary scenario: use the
existing `candidate-launcher` for the composed Template identity. Publishing a
new receipt invalidates previous profile-scoped canary receipts, and no
platform canary should be claimed green until the duplicate-name Core limit is
resolved.

### Typed receipt publication

`gct-managed-worker-provision` publishes candidate and explicit-signing typed
profiles only when the explicit city's installed Core is bound to the accepted
platform deployment and an externally reviewed typed-support witness. Supply
the witness file and its independently delivered complete-file digest:

```text
--consumer-witness /absolute/path/to/core-typed-support.json
--consumer-witness-sha256 <sha256-of-the-exact-witness-file>
```

The strict `gct.core-typed-support.v1` witness contains exactly `city_path`,
the validated embedded SELF-digests for the canonical platform manifest and
accepted install receipt, a `consumer` object with `path`, `sha256`, `commit`,
and `tree`, and three exact-file evidence pins whose roles are
`accepted-deployment`, `reviewed-build`, and `typed-interoperability`. The
provisioner resolves
`.gc/platform/install-manifest.json` and `.gc/platform/install-receipt.json`
from `--city`; validates both files' embedded SELF-digests; requires their
release, artifact, and activation commit/version to agree; derives the Core
destination and mode from the manifest; and requires the witness consumer to
match that installed executable exactly. All authority and evidence files must
be stable regular non-symlink files without group/world write permission.
The validation report keeps the SELF-digests under
`platform_manifest_sha256` and `platform_receipt_sha256`, and separately pins
the exact observed file bytes as `platform_manifest_file_sha256` and
`platform_receipt_file_sha256`; these digest domains are deliberately not
interchangeable.

Authority documents and evidence retain the 16 MiB size limit. The installed
Core executable is hashed in bounded 64 KiB streaming reads under a separate
384 MiB artifact limit, matching the control-plane broker. Its path, regular
non-symlink type, ownership-visible identity, exact mode, size, timestamps and
SHA-256 must remain stable across each hash and across the fixed version
corroboration call. The executable is never buffered as one in-memory value.

The fixed `version --json` call remains a corroborating readback: it must report
the same activation commit, but a responder that merely prints a matching
version is not compatibility evidence and cannot replace the manifest/receipt
and reviewed witness binding. A caller-selected witness path and digest do not
authenticate their own review; the digest must be delivered by the coordinator
from an already accepted execution/deployment package outside worker-controlled
declarations. The actual live-deployment witness is produced only after the
source and interoperability review, never by this provisioner or its tests.
Missing, partial, mismatched, replaced, unsafe, or unparsable evidence exits 3
before publication. The complete binding is re-read immediately before each
of the two possible writes; drift before the first writes nothing, and drift
between them restores the exact prior runner bytes and mode.

After Core supplies the selected complete profile to the runner, the runner
finds exactly one receipt profile with the same exact name and compares the
complete canonical profile. It does not read `profiles[0]`, apply a role suffix,
or reconstruct a binding alias. Reordered receipts and nonstandard composed
identities therefore preserve Core's selection; duplicate, absent or merely
similar records refuse.

The two installed files are one rollback unit. The provisioner snapshots exact
pre-existing bytes and modes, writes only drifted targets, and restores both
snapshots if the second write fails. Reapplying identical inputs performs no
replacement, preserving bytes, modes and modification times. Legacy untyped
receipts retain their historical bytes and do not require the new consumer
arguments.

The remaining activation evidence is live witnessed behaviour: use the
reviewed installed policy path, inspect a fresh client's actual settings and
argv, and run the scoped denial and claim canary. Source tests and successful
receipt decoding do not establish those live facts.

The actual-Core interoperability test has two mandatory, portable inputs:
`GCT_CORE_SOURCE` names an absolute checkout of the reviewed Core repository,
and `GCT_CORE_COMMIT` names one full lowercase commit that must resolve exactly
in that checkout. Missing or mismatched inputs fail rather than skip. The test
archives only that commit into its disposable fixture and invokes Core's real
`LoadProvisioningReceipt`, `WorkerProfileDigest`, and `SelectCanaryProfile`
implementations. Hosted CI checks out the same immutable commit in a hidden
auxiliary directory, prepares its locked Go modules, and runs the interop test
offline; local workers do not download dependencies.

### Claude subscription preflight helper

`lib/gct_claude_subscription.py` is a narrow library for a durable caller. Call
`subscription_environment(parent_env)` before copying credential values: it
removes `ANTHROPIC_API_KEY` by key name, preserves the rest of the parent
environment (including `GC_*`, `BEADS_*`, `BD_*` and `DOLT_*` identity), and
refuses any remaining provider, auth, billing or helper override, even when its
value is empty. Pass the returned mapping unchanged to
`authenticate_subscription`.

Before authentication, pass every explicit Claude settings file to
`inspect_settings_files`. It accepts only stable, non-symlink, owner-controlled
regular files and rejects settings that contain auth, credential, billing or
helper overrides. `authenticate_subscription` executes only the fixed
`claude --setting-sources <sources> auth status --json` operation in the
caller's exact working directory and environment, and accepts only a
first-party `claude.ai` subscription posture whose `apiKeySource` field is
present and null, plus an allowed subscription type. An omitted field is not
evidence of no API-key source. It never launches a model, accepts an arbitrary
command, or includes subprocess output or credential values in errors.
Separate explicit-file inspection and `auth status` calls constrain those two
observations; they do not prove every effective setting or that a real worker
can execute successfully. That remains a fresh-session, witnessed runtime fact.

## Upgrade procedure

Toolchain upgrades are normal reviewed profile changes:

1. Install the candidate toolchain outside the managed profile.
2. Record its clean absolute path, resolved path, SHA-256, version arguments,
   and exact version output in the source-owned v2 profile.
3. Pin the exact compatible `gc` executable bytes and build commit, then run
   the renderer and provisioner in check mode against staging inputs.
4. Merge the reviewed source changes.
5. Render the managed fragment and publish the v2 receipt while rigs remain
   suspended.
6. Upgrade privileged installed components only through the fixed-operation
   broker.
7. Run the platform canary. Resume product work only from its PASS receipt.

The receipt producer is idempotent. Reapplying identical inputs leaves the
runner and receipt byte-, mode-, and mtime-identical. A version, digest,
symlink-resolution, consumer-compatibility, or configuration drift refuses
before replacing a previously valid receipt; a write failure restores both
installed files to their exact preceding bytes and modes.

Do not fix toolchain failures by widening the network policy, prepending an
operator `$PATH`, downloading from a worker, or hashing an entire toolchain
tree. The executable identity and a real build are the reviewed security and
functionality boundaries.
