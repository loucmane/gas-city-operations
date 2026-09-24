# ga-f37t — one actual Claude Core implementation/signing worker

This is a scoped infrastructure task through Gas City, not product dispatch or
full provider-handover acceptance. No native Agent/Task delegation, other provider,
or coordinator implementation/signing fallback. The failed ga-5ot6, ga-e0t1.14 and
ga-y49e attempts, their artifacts and worktrees remain historical evidence, never
retry targets.

## Exact identity

- City /home/loucmane/gascity/city; rig gascity; task ga-f37t.
- Template gascity/gc.implementation-worker; provider claude-signing, Opus 5.5.
- Worktree /home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles.
- Branch codex/ga-f37t-typed-route-cycles.
- Initial HEAD e6366b9ececd3a4ceab2bcaa264a5e317e6eab88.
- Initial tree f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13.
- Git common directory /home/loucmane/gascity/city/rigs/gascity/.git.
- Evidence only under .gc/worker-evidence/ga-f37t/ in this worktree (`.gc/` is
  already ignored by the tracked .gitignore).
- Allowed source: internal/sling/cycle.go, internal/sling/cycle_test.go,
  internal/sling/sling_core_test.go and the exact .gitignore addition named in
  the source release.
- Negative native target /home/loucmane/gascity/.ga-f37t-denied-native-write.
- Negative shell target /home/loucmane/gascity/.ga-f37t-denied-shell-write.
  Both must initially be absent; attempt only `ga-f37t harmless negative probe`.

## Time budget

The window that hosts this session must restore within four hours of its
preflight, so the coordinator holds scheduling at preflight plus two hours and
forty-five minutes whatever the progress. Work steadily: startup proof first, then the implementation
as soon as the source release arrives. If scheduling is held before you finish,
stop at the current safe point and preserve everything; unfinished work is
evidence, not a reason to hurry past a check. Keep command output short (focused
test runs, -q flags, head or tail on long logs, evidence in files rather than in
the conversation): an automatic context compaction runs the handoff hook, and a
cycled session cannot be replaced inside this window.

## Claim and capability proof, before any source edit

Claim at once. Core restarts a session that holds no claim and shows no activity
for five minutes, and a restart ends this attempt. Once you hold the claim,
waiting is safe. During a long wait, Core may add the needs/operator label and
progress-stall metadata to ga-f37t. That is expected: leave it in place, and do
not treat it as a stop.

Start no background or detached process (no `&`, nohup, setsid, disown, screen
or tmux). Every command must finish before the next one. The closeout proves that
no process remains in this worktree, and a leftover process blocks it.

First standalone Bash command:
`/home/loucmane/gascity/bin/gc hook --claim --json`
Then separately `/home/loucmane/gascity/bin/bd show ga-f37t --json`.
Verify exact task, actual ci-* identity, in_progress status, matching assignee,
route and cwd. No env prefix, compound command, alias or alternate control path.
An actual drain response requires standalone
`/home/loucmane/gascity/bin/gc runtime drain-ack`, then exit. Unexpected work or
claim/identity mismatch means stop; do not select or reassign another task.

Read AGENTS.md, CLAUDE.md and TESTING.md. Verify branch, HEAD, tree, common Git
directory and empty tracked/index diffs. Record only named non-secret
GC_SESSION_ID, GC_SESSION_NAME, GC_ALIAS, GC_TEMPLATE, GC_SESSION, GC_AGENT,
GC_WORK_DIR, GC_RIG_ROOT, GC_BEAD_ID, GC_STORE_PATH and GIT_OPTIONAL_LOCKS if
present. Never dump
environment or credentials. The coordinator independently proves the native
session/claim and Core store identity; locating a Bead alone is insufficient.

1. Native Write/Read positive fixture inside the evidence directory.
2. Exactly one native Write to the reserved outside target: require real refusal
   and absence, not abstention.
3. Exactly one ordinary sandboxed Bash write to the outside shell target: require
   refusal and absence. No unsandboxed request. Any success stops immediately;
   preserve the unexpected file, never remove it.
4. Standalone `git config --get user.email`: require explicit deny. Do not work
   around it with an alias, path, -C, wrapper or composition.
5. Record Go/Python versions, then standalone
   `go test ./internal/sling -run '^TestGa4z38CapabilityProbeNoTests$'`.
   This is compile-only, not suite PASS. The reviewed policy already supplies
   GOPROXY=off, GOSUMDB=off, GOFLAGS=-mod=readonly and the profile supplies
   GOTOOLCHAIN=local. Do not add leading environment assignments: that command
   shape is denied. No network/install, cache clearing, GOCACHE override or /tmp
   Go cache.
6. Standalone `git update-index --refresh --force-write-index`, then standalone
   `git hash-object -w .gc/worker-evidence/ga-f37t/<the step-1 fixture file>`: require
   success of both. The first always rewrites this worktree's index and the second
   writes one blob into the object store, both inside the shared Git common
   directory, so together they prove the sandbox lets you stage before any source
   edit. A refusal of either is a stop.

## Generated startup artifacts

Before startup the fresh worktree was clean with no untracked paths. The runtime
may materialize generated paths under `.claude/` at session start (earlier
runtimes created `.claude/skills/.gc-skill-ownership.json` and skill symlinks).
Inventory every untracked path exactly: path, kind, mode, owner, size, SHA256 for
regular files, link target for symlinks. Tracked .claude/skills/gascity-docs is
existing source and stays untouched. Any untracked path outside `.claude/` or
`.gc/` is a stop.

A Claude sandbox may present /dev/null character-device masks as extra untracked
dotfiles inside Bash. Such observations are NOT a host clean-tree proof. Record
actual kind/device and leave mounts untouched; never ignore/delete them. The
coordinator corroborates the real host's full unfiltered status and the artifact
inventory before each release.

Write startup-proof.json with the exact observations and outputs. Report
STARTUP_PROOF_READY and wait for the source release. Do not busy-poll. A failure is
evidence, not permission to repair policy or proceed.

## Releases

Each release is one line the coordinator appends to this task's notes,
`SOURCE_RELEASE ga-f37t <json>` or `SIGNING_RELEASE ga-f37t <json>`, announced by a
short coordinator note typed into your session. Read it with the same standalone
`/home/loucmane/gascity/bin/bd show ga-f37t --json` you use for the claim; the
latest line that starts with that release name is authoritative. Its JSON is one
object. Verify that it names this task, your exact ci-* session and the base, plus:
- source release: the SHA256 of your startup-proof.json and the exact root-anchored
  .gitignore entries for the observed generated artifacts;
- signing release: your inspected HEAD, your `git write-tree` value and the SHA256 of
  candidate.patch (below).
Write the JSON bytes verbatim to source-release.json or signing-release.json in
the evidence directory. A missing, truncated or mismatched release is a stop; wait
for the coordinator, never proceed on a partial message.

After the source release only, append exactly the named entries to the root
.gitignore, preserving every original byte. No wildcard, directory-wide ignore,
local config, shared exclude, artifact edit/removal or forced add. Prove in an
isolated Git fixture under evidence that each new rule matches its exact path but
not near-name/nested distractors. Preserve the generated artifacts throughout;
ignored is not absent. Real host untracked status must be empty before signing.

## Worker-owned implementation and tests

Collect union-reachable nodes through execution and hierarchy edges, then detect
cycles independently within those two families. Execution types: blocks,
waits-for, conditional-blocks and legacy empty type. Hierarchy: parent-child.
Keep informational edges excluded, dependency-read failures fail-closed,
diagnostics deterministic and genuine-cycle refusals before routing mutation.
No dry-run/force change, Bead graph edit or other routing/policy change.

Focused RED first, then GREEN:
- Valid parent-waits-child plus child-parent and longer mixed graphs accepted.
- Direct/indirect/self execution cycles across every execution type refused.
- Direct/indirect/self hierarchy cycles refused.
- Real cycles reachable only through the opposite family still refused.
- Mixed graph plus a real cycle refused.
- Informational edges, acyclic diamonds and read failures preserved.
- Integration: refusal before mutation, unchanged dry-run and force behavior.

Run relevant complete `go test ./internal/sling ./internal/beads`, corresponding
`go vet ./internal/sling ./internal/beads` and `git diff --check`. Preserve RED and
failed attempts. No unrelated broad suites or network fallback. Capture checkpoint
with exact identity, base, patch digest, changed paths, tests and limitations.
Read back this Bead before handoff. Do not modify parent plans or other Beads.

## Artifact and managed signing contract

Use receipt-pinned build-artifact-valid.sh, never a checkout substitute. Emit
.gc/worker-evidence/ga-f37t/implementation-summary.md as
gc.build.implementation-summary.v1; read the actual schema under the receipt pack.
Required YAML: schema, workflow.id/formula, methodology.pack/name,
producer.formula/stage/attempt (integer 1), supported status, trace.upstream and
trace.coverage. Use truthful raw-task descriptions, not invented formula runs.
Include Summary, Intended Behavior, Changed Files, Verification, Remaining Risks.
Any coverage IDs require matching coverage rows. Controller runs the real checker.

After all tests, stage ONLY the three allowed source paths and .gitignore, with no
other staged paths or unstaged tracked changes. Write the staged patch with exactly
`git diff-index --cached --patch --binary --full-index --output=.gc/worker-evidence/ga-f37t/candidate.patch HEAD`
(plumbing with full object names, so no diff, color or abbreviation configuration changes
the bytes). Capture HEAD and
`git write-tree`, and write candidate.json in the evidence directory as
{"head": ..., "tree": ..., "staged_patch_sha256": <SHA256 of candidate.patch>}; the
coordinator hashes the same command's output and compares all three. Reverify
generated artifacts and record sandbox masks separately. Report
CANDIDATE_REVIEW_READY and wait for independent candidate
review plus the signing release. This hold prevents source PASS being mistaken
for authorization to sign changed bytes.

After the signing release, exactly one standalone invocation, with literal
observed values:
`/usr/local/libexec/gas-city/managed-git-commit --policy gascity-core --worktree /home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles --bead ga-f37t --session <actual-ci-id> --expected-head <inspected-head> --expected-tree <inspected-tree> --message 'fix: distinguish routing dependency and hierarchy cycles'`
No git commit, gpg, keys, sudo, wrapper, other signing path or retry. Record commit,
tree, transaction and signer-owned receipt. Recheck parent/HEAD/tree/cleanliness.
Any refusal or ambiguous output stops pending exact state reconciliation.

Update only this task's bounded gc.work_commit, gc.work_verification, artifact path
and candidate evidence. Report SIGNED_CANDIDATE_READY. Do not push/merge/adopt or
close PASS; required CI and delivery remain. Keep the claim until the controller
holds scheduling and sends the supported drain. Never invent claim release, close
to force a drain or take another task. On failure preserve everything and await
containment.
