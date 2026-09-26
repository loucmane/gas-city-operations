# Claude orchestrator command permissions

A successful Aegis PreToolUse check is normally a silent exit zero. Claude then
applies its native permissions; in `dontAsk` mode an unapproved command is refused.
The ga-e0t1 live probe established this exact split: both hooks passed, then Claude
refused `project_context.py --check` before the shell executed it.

## Opt-in profile, not a wildcard Bash grant

`.claude/orchestrator-command-profile.json` is a project-local, protected opt-in.
The profile knows five command classes, each a closed grammar. Operations enables the
first four; the fifth, `delivery` (ga-fsfg R3, below), needs its own explicit opt-in:

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
- `delivery`: push a signed Operations branch, open its pull request into `main` and
  merge that pull request, one fixed-environment `/usr/bin/git` or `/usr/bin/gh` command
  per call. See "Delivery (ga-fsfg R3)".

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
and name roots distinct from the seat's own. A registry record without
`worktree_root` is compared against the plugin's derived default,
`<canonical_root>-worktrees` (ga-4p6f); this applies to both lists, so a registered
record may rely on it too. The profile registers only the gascity Core rig, which
shares the seat's `gascity` rig. A direct child of a registered
`worktree_root` is then a valid stationary target for `attach`, `checkpoint`,
`verify`, `coordinate`, `log`, `discharge`, `compact-journal` and `publish`.

`review_projects` (ga-4p6f) is a second optional list with the same record shape and
the same registry validation. It may not repeat a registered `id` or `worktree_root`.
A review project's worktrees can only bind an `aegis-reviewer` candidate (see below).
They are never coordination targets from this seat. The gate's and the executor's own
code write nothing into them when invoked here. The workflow plugin's registry still
lists the Template for its own `begin` and context commands. The gate runs only the
bounded reviewer Git inspection there. That inspection can still start filter drivers
defined by Git configuration (the Template's own config sets a required `git-lfs`
process filter), and such a driver may itself write, for example objects under
`.git/lfs`. See Limits.

The Template is a review project. Sanctioned Bead reads and ledger-only writes for
review projects are follow-up ga-2smi.

Both lists are validated whenever the profile loads. A drifted `review_projects`
record therefore also disables Core coordination and every native approval until it
is fixed. This fails closed.

A registered target carries no Operations policy or runtime of its own, so the
checks differ from an Operations worktree in three ways and nowhere else:

- identity comes from the seat's tracked profile and registry, and the target's
  journal spec must match the registered `id`, `rig`, `canonical_root` and
  `worktree_root`; the ownership binding is derived from that spec, the shared
  city and the registered canonical root, exactly as the plugin wrote it;
- the canonical executor is verified as before, and the target must carry no
  Operations runtime tree, installed runtime or Python startup hook that could
  shadow it. `aegis_foundation`, `plugins/gas-city-workflow` and `.claude/scripts`
  are refused as whole trees. Since ga-4p6f the target may also carry no file of the
  canonical runtime inventory, which lists every file tracked at the canonical HEAD
  under `scripts`, `aegis_foundation`, `.claude/scripts` and
  `plugins/gas-city-workflow/scripts`. Under `scripts/` this is file by file; the
  Core rig's own unrelated `scripts/` files stay allowed. That covers
  `scripts/codex-task` and
  `scripts/codex-guard`, which `workflow.py checkpoint`, `verify` and `finish` would
  otherwise run from the target, and `scripts/_source_workflow_state.py`, which the
  installer would execute during a stationary `log`;
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

**Known gaps for registered coordination (pre-existing since R2, follow-up ga-vomb).**
These are why the Template is review-only rather than registered. The `codex-task`
part of the fix is Codex-owned:

- The gate appends its decision record under the target root, and the executor's
  plan sync writes `<target>/.plan_state/sync.log`. Both follow a symlink the target
  tracks at those paths.
- The executor's Git calls use the registered repository's own configuration, for
  example filters during `diff --check` and `status`, and `gpg.program` during
  `publish`'s `verify-commit`.

## Read-only reviewer delegation (ga-fsfg)

Independent review used to require a human-run reviewer because the managed-project
delegation rule blocked every `Agent` request. The rule now distinguishes a reviewer
from a worker with a closed grammar:

- Claude's own `Agent` tool (the exact tool name, so an MCP tool whose name merely
  normalizes to `agent` does not qualify) with `subagent_type` in the allowlist
  (`aegis-reviewer`);
- the agent definition `.claude/agents/<type>.md` tracked at HEAD, byte-identical to the
  working tree, named for its type, carrying only the `name`, `description`, `tools`,
  `model` and `color` frontmatter fields (no `hooks`, `permissionMode`, `mcpServers`
  or `memory`), and declaring `tools:` as a non-empty subset of Read, Grep and Glob,
  so the reviewer cannot edit, run, route or delegate even in advisory mode;
- a prompt naming exactly one `candidate=<40-hex>` commit that exists in the
  repository, bounded in size, and no `isolation`, `model` or other options; the
  model comes from the tracked definition alone.

A registered or review project's commits are not in the Operations repository, so the
prompt may bind the review to that project's worktree (ga-4p6f).

**Token grammar.**
- The token is exactly one `worktree=<absolute path>`, standing alone: it starts the prompt or follows whitespace.
- The path uses only `A-Za-z0-9._/-`.
- The path must be followed by a space, tab, newline or the end of the prompt.
- Every other occurrence of `worktree` followed by an equals sign is refused. This covers any case, any whitespace before the sign, the full-width sign, and the token glued to preceding text such as `(worktree=` or `git_worktree=`. It applies to prompts without a binding too, so a stray `worktree=` in prose now refuses a request that the Operations path used to accept.
- A spelling that the mention pattern does not match is not a binding. Examples: no equals sign (`worktree: /path`), look-alike equals signs such as U+FE66, U+207C or U+208C, or look-alike letters that case-insensitive matching does not fold. The Kelvin sign U+212A folds to `k`, so `worKtree=` is a mention and is refused. Such a request takes the Operations path. Only the audit reason `read_only_registered_reviewer_delegation` proves that a binding was checked, so the orchestrator records that reason with the verdict.

**Checks.** The definition checks above run first. The binding is then accepted only when the path:

- is a direct child of a `worktree_root` in the seat's validated `registered_projects` or `review_projects`. This is a pure path comparison, made before the path is touched;
- exists, is a directory and resolves to itself (no symlink indirection);
- is that record's linked worktree:
  - its Git common directory is `<canonical_root>/.git`;
  - its private Git directory sits under `<canonical_root>/.git/worktrees/`;
  - it is its own top level;
  - that directory's `gitdir` file links back to exactly `<path>/.git`. The file is opened only after the path checks above, with `O_NONBLOCK|O_NOFOLLOW`; it must be a regular file of at most 4096 bytes. Worktrees that record relative paths (`worktree.useRelativePaths`) are therefore refused;
- has HEAD equal to the candidate, checked both before and after the status call;
- has no index entry flagged assume-unchanged or skip-worktree; and
- shows no tracked, untracked or submodule changes to `git status`. The status call pins `core.checkStat=default`, `core.trustctime=true`, `core.ignoreCase=false`, `core.fileMode=true` and `core.untrackedCache=false`, and passes `--ignore-submodules=none`.

Every foreign Git call (against the named worktree) uses `/usr/bin/git` with a 10 second timeout, `--no-replace-objects`, `--no-optional-locks` and `core.fsmonitor=false`. Inherited `GIT_*` variables are dropped, and output is decoded without raising. A replace ref therefore cannot make HEAD name the candidate while Git reads a different tree. The seat's own reads (the profile and the reviewer definition) still use `delegation._git` against the trusted Operations checkout.

**Failure handling.** Every failure refuses, including unexpected ones: a symlink loop, undecodable output, a timeout, a missing or broken `reviewer.py`. No failure reaches the degraded fallback. A policy refusal raised inside the profile loader keeps that loader's own reason code, such as `claude_command_profile_invalid` for a profile whose bytes differ from HEAD. A `ValueError` or `OSError` from the loader is refused as `native_delegation_reviewer_invalid`. Independently, the degraded fallback hard-blocks provider-native delegation in a managed project before anything else can fail, as it does coordination. A project whose context cannot be resolved counts as managed.

An allowed binding is audited as `read_only_registered_reviewer_delegation`.

**Limits.** `git status` is not an integrity manifest (compare `coordination_runtime.py`). The binding proves the named worktree was at the candidate with nothing Git reports as changed when the gate ran. It does not cover:

- ignored or excluded files, including `.git/info/exclude` and `core.excludesFile`;
- clean or process filter drivers that Git configuration may run, and that may write, during status. That includes the foreign repository's config and the user's global and system config, since only `GIT_*` variables are removed. An example is a required `git-lfs` process filter writing objects under `.git/lfs`;
- uninitialised submodule directories, flags or ignore rules inside submodules, and replace refs inside a populated submodule (Git clears `GIT_NO_REPLACE_OBJECTS` for submodule children);
- a hook-level timeout: each foreign call is bounded at 10 seconds, but the seven calls together can take about 70 seconds. The seat's own Git reads have no timeout, and the client's handling of a timed-out hook is outside the gate. A binding that did not finish leaves no `read_only_registered_reviewer_delegation` record;
- tracked symlinks that point outside the worktree;
- untracked files inside directories Git cannot read, and nested `.git` directories below the top level;
- an index whose stat data was forged to match modified files;
- changes made after the check.

The binding also does not confine what the reviewer reads. A prompt can still direct it to other paths, which is why the orchestrator records the audit reason with the verdict. The reviewer is still read-only in every case.

**Known gap in the definition check (pre-existing since ga-fsfg, follow-up ga-sv7v, P1).**

- The frontmatter check splits lines with Python `splitlines()`, which also splits on Unicode line separators, and reads `key: value` pairs naively. A YAML parser could read the same bytes differently, for example with no `tools` key at all.
- The definition is bound to the HEAD of the gate's project root, not to the canonical copy.
- Another agent definition declaring the same name could shadow it.

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
arbitrary Bead mutation CLI, dispatch, lifecycle, file-write or privileged access. Push
and merge are granted only through the `delivery` class's closed grammar below.
It does not prove Claude implementation-worker capabilities.

## Delivery (ga-fsfg R3)

The `delivery` class lets the canonical seat deliver a signed branch of an Operations
worktree `<W>` without a human at the keyboard: push the branch, open its pull request
into `main`, and merge that pull request. Reading the checks is already remote
observation (R1). Each step is one closed command, and each approval is audited on
`<W>` as `native_permission:delivery`.

### Opt-in and profile fields

The profile opts in by listing `delivery` in `commands` together with every field
below. All are top-level. `_profile()` validates them whenever the profile loads. A
missing or invalid field refuses the class, and, exactly as a drifted
`review_projects` record does, every other class too until it is fixed. Fields
present without `delivery` in `commands` grant nothing.

| Field | Value |
| --- | --- |
| `repository` | `owner/name`, today `loucmane/gas-city-operations` |
| `default_branch` | `main`; `git check-ref-format --branch` must accept it and it never starts with `-` |
| `remote_url` | the one accepted push and fetch URL, today `https://github.com/loucmane/gas-city-operations.git` |
| `signing_key` | the fingerprint git reports as `%GF` for the reviewed key, uppercase hex, today `FD5585922F5335BC378AD8D42ECF4432C7E7982D` |
| `required_checks` | non-empty list of check names, copied by the coordinator from the repository's branch protection |
| `delivery_path` | the exact `PATH` of every delivery command and gate read, today `/usr/local/bin:/usr/bin:/bin` |
| `delivery_home` | the fixed `HOME` of every delivery command and gate read, today `/home/loucmane` |
| `credential_helpers` | the exact `credential.*` entries, in order, as `{"key": ..., "value": ...}` objects copied from the live global configuration |

Today the credential entries are `credential.https://github.com.helper` with the
values `` (empty) and `!/usr/bin/gh auth git-credential`, and the same pair for
`https://gist.github.com`:

```json
"credential_helpers": [
  {"key": "credential.https://github.com.helper", "value": ""},
  {"key": "credential.https://github.com.helper", "value": "!/usr/bin/gh auth git-credential"},
  {"key": "credential.https://gist.github.com.helper", "value": ""},
  {"key": "credential.https://gist.github.com.helper", "value": "!/usr/bin/gh auth git-credential"}
]
```

### Closed grammar

These are the only forms `delivery` approves. Each starts with the literal prefix
`/usr/bin/env -i HOME=<delivery_home> PATH=<delivery_path>`, so the command runs with
exactly that environment and nothing inherited:

```bash
/usr/bin/env -i HOME=/home/loucmane PATH=/usr/local/bin:/usr/bin:/bin /usr/bin/git -C /home/loucmane/gas-city-ops-worktrees/ga-x-slug push origin codex/ga-x-slug
/usr/bin/env -i HOME=/home/loucmane PATH=/usr/local/bin:/usr/bin:/bin /usr/bin/gh pr create --repo github.com/loucmane/gas-city-operations --base main --head codex/ga-x-slug --title 'feat(ga-x): the change' --body-file /home/loucmane/gas-city-ops-worktrees/ga-x-slug/docs/pr-body.md
/usr/bin/env -i HOME=/home/loucmane PATH=/usr/local/bin:/usr/bin:/bin /usr/bin/gh pr merge 123 --repo github.com/loucmane/gas-city-operations --merge --match-head-commit 0123456789abcdef0123456789abcdef01234567
```

- **Canonical quoting.** The command must be exactly Python's `shlex.join` of its
  words: single spaces, and a word in single quotes only when it holds a character
  outside `A-Za-z0-9_@%+=:,./-`. The shell and the gate therefore always see the same
  words, and no unquoted word can be expanded (a glob in a title or body-file path
  would otherwise let the shell choose another file). Double quotes refuse.
- No shell syntax anywhere, even quoted: `;`, `&`, `|`, `<`, `>`, `$`, a backquote,
  CR or LF. One operation per call. `run_in_background` refuses.
- The prefix is exact: any other `HOME` or `PATH`, an extra assignment, `env` without
  its absolute path, `env -u`, another order or a wrapper refuses. A form such as
  `env -i ... /usr/bin/git ...` that is not one of the three commands refuses too.
  Everywhere else an `env -i` prefix still reads as untrusted: `strip_shell_prefixes`
  and `ORCHESTRATOR_ENVIRONMENT` are unchanged.
- Push: `/usr/bin/git`, then `-C <W>` and no other Git global option (no `-c`,
  `--config-env`, `--exec-path`, `--git-dir`, `--work-tree` or `--namespace`), then
  exactly `push origin <branch>`. Every flag refuses (`-f`, `--force*`, `--delete`,
  `-d`, `--mirror`, `--all`, `--tags`, `--prune`, `-o`, `--push-option`,
  `--receive-pack`, `--exec`, `--no-verify`, `-u`), as does a refspec with `:` or `+`,
  a remote other than `origin`, or a URL or path in its place.
- Pull request: `--repo`, `--base`, `--head`, `--title` and `--body-file` in that
  order and nothing else. `--title` is printable and never starts with `-`; the body
  file is a canonical absolute path.
- Merge: `<number>` is decimal digits without a leading zero, `<sha>` is exactly 40
  lowercase hex characters, and every other option refuses (`--admin`,
  `--delete-branch`, `-d`, `--auto`, `--squash`, `--rebase`).
- `<branch>` is a plain branch name: characters `A-Za-z0-9._/-`, never starting with
  `-`, `refs/`, `heads/`, `tags/` or `remotes/`, never `HEAD` or any name ending in
  `HEAD`, never `default_branch`, and accepted by `git check-ref-format --branch`.

### What every approval checks

Delivery is stationary, like the coordination verbs. The canonical seat stays on
`main`, where readiness is BLOCKED by design; no readiness exemption is added. The
gate selects `<W>` as the target and evaluates readiness, observation, pending events
and advisory handling there. Plan mode, observation, protected paths, native
delegation and hard policy keep their precedence (hard policy still refuses a force
push before the class is consulted). The evaluation runs once per PreToolUse; the
second `target_for` call reuses it. In order:

1. **Call identity.** The HEAD-bound profile lists `delivery`; the seat is the
   canonical root and the payload's `cwd`; the permission mode is a known non-plan
   mode; the payload carries a `tool_use_id` and a session id.
2. **Find `<W>` by file reads only.** For the push, `-C <W>`. For the pull request, the
   unique direct child of the Operations `worktree_root` whose administrative `HEAD`
   names `--head`. For the merge, the unique direct child whose `HEAD` resolves to
   `<sha>` through a loose ref or `packed-refs` (a `reftable` store refuses). None or
   several refuse. `<W>` must be a canonical absolute path without a symlink
   component, a direct child of the Operations `worktree_root` (so registered Core and
   review-project worktrees refuse), and a verified linked worktree of the canonical
   repository: its gitfile, the back-pointer and `commondir` agree. For the push, its
   current branch is `<branch>`.
3. **Workflow state.** `<W>` is not advisory (an advisory target refuses delivery,
   because `decisions.py` returns before `native_permission` for it and no binding
   could be written); neither the seat nor `<W>` is in observation or has an
   unresolved pending event; no unexpired binding holds `<W>`.
4. **Coordinate's target validation of `<W>`:** a journal in phase `ready`, verified
   external ownership of its Bead, and a `codex/<bead>-<slug>` branch. A clean signed
   worktree that the seat does not own never qualifies. Then the canonical runtime
   tree check (the `git status` part of the reused runtime check), bounded by the
   deadline.
5. **Configuration**, for `<W>` and for the canonical root (where gh runs git). Nothing
   else runs if it refuses. See the allowlist below.
6. **Everything else:** the first `git` on `delivery_path` is `/usr/bin/git`;
   `gh config get http_unix_socket` and `gh config get -h github.com
   http_unix_socket` are empty; the hooks directories, attributes and origin URL of
   `<W>` and of the canonical root; no history rewriting; the branch rules; the remote
   `main`; every signature; a clean tree; then the operation's own checks.

Every Git read the gate makes for delivery runs as
`/usr/bin/git --no-optional-locks --no-replace-objects -c core.commitGraph=false -c core.hooksPath=/dev/null -c core.fsmonitor=false -c core.attributesFile=/dev/null -c gpg.program=/usr/bin/gpg -c gpg.ssh.program=/bin/false -c gpg.x509.program=/bin/false`
with exactly the environment `HOME=<delivery_home>`, `PATH=<delivery_path>`,
`GIT_NO_REPLACE_OBJECTS=1` and `GIT_ATTR_NOSYSTEM=1`, so the configuration it judges
is the one the push will use. The configuration listing
(`git config --list --show-scope --null`) runs without the `-c` entries, so the gate's
own command-scope values never appear in what is judged. The gh reads run with
exactly `HOME` and `PATH`, in the canonical root. Any failed or late read refuses.

**Worktree and history rules.**
- Every commit in `<remote-main>..HEAD` carries an OpenPGP signature (its `gpgsig`
  header begins `-----BEGIN PGP SIGNATURE-----`) that is good by exactly
  `signing_key`: `%G?` is `G` and `%GF` equals the key. SSH and X.509 signatures
  refuse, and so do unsigned, foreign-signed, badly signed and unknown-validity (`U`)
  commits. `<remote-main>` is the object `git ls-remote origin
  refs/heads/<default_branch>` returns in exactly one line; it must exist locally
  and be an ancestor of `HEAD`, so a local `main` ahead of the remote cannot hide
  commits.
- Nothing may rewrite history for the walk: `git for-each-ref refs/replace/` is empty
  (loose, packed or reftable), there is no `info/grafts` and no `shallow` file, and
  the reads use `--no-replace-objects` and `core.commitGraph=false`, so a forged
  commit-graph cannot supply false parents.
- The tracked tree is clean and the index matches `HEAD` (`git status
  --untracked-files=no` with Git's default change detection pinned); every index entry
  is tagged `H` in `git ls-files -v`, so no assume-unchanged or skip-worktree bit hides
  a change. Untracked files are allowed.
- The branch resolves only as `refs/heads/<branch>`: no tag, remote-tracking ref,
  `refs/<branch>` or pseudo-ref file of the same name.

**Configuration allowlist.** Within `remote.*`, `url.*`, `push.*`, `credential.*`,
`http.*`, `protocol.*`, `gpg.*`, `filter.*`, `diff.*`, `merge.*`, `submodule.*`,
`hook.*` and the keys `core.sshCommand`, `core.askPass`, `core.hooksPath`,
`core.gitProxy`, `core.fsmonitor`, `core.alternateRefsCommand` and
`core.attributesFile`, only these entries may appear:
- exactly one `remote.origin.url` equal to `remote_url`, and
  `git remote get-url --push --all origin` returns exactly that one line;
- exactly one `remote.origin.fetch = +refs/heads/*:refs/remotes/origin/*`;
- exactly the `credential.*` entries of `credential_helpers`, in order;
- `push.autoSetupRemote = true`;
- `gpg.program = /usr/bin/gpg` (no `gpg.format`, `gpg.ssh.*` or `gpg.x509.*`);
- the four global git-lfs entries exactly as they are live:
  `filter.lfs.clean = git-lfs clean -- %f`, `filter.lfs.smudge = git-lfs smudge -- %f`,
  `filter.lfs.process = git-lfs filter-process` and `filter.lfs.required = true`.

Everything else in those namespaces refuses: `pushurl`, a second URL,
`remote.origin.push`, `mirror`, `vcs`, `receivepack`, `uploadpack`, any other remote,
any `insteadOf` or `pushInsteadOf`, any other `push.*` (including `push.default`), any
`http.*` or `protocol.*`, every program-running key and every other driver,
`submodule.*` or `hook.*` key. The list is strict on purpose: a harmless key such as
`merge.conflictStyle` or gh's `remote.origin.gh-resolved` refuses too.

Nothing may select a driver, which keeps the lfs filter inert. No `.gitattributes` at
`HEAD`, in the index or in the work tree (untracked and ignored files included) may
carry `filter=`, `diff=` or `merge=`; there may be no `info/attributes` in the common
or administrative directory, no `core.attributesFile`, and no global attributes file
at `<delivery_home>/.config/git/attributes` or `$XDG_CONFIG_HOME/git/attributes`.
System attributes are never read (`GIT_ATTR_NOSYSTEM=1`). No gitlink (mode 160000) may
be in `HEAD`'s tree. Neither the common `hooks/` nor the administrative `hooks/`
directory may hold any entry, judged by `lstat` so that symlinks count, other than
git's regular `*.sample` files. All of this is checked in `<W>` and in the canonical
root.

**Operation checks.**
- Pull request: `git ls-remote origin refs/heads/<branch>` returns exactly one line
  naming exactly that ref, whose object is `<W>`'s `HEAD`. The body file is a regular,
  singly linked file of at most 64 KiB inside `<W>`, with no symlink component, tracked
  at `HEAD` as a regular blob, and its bytes equal that blob (`git hash-object
  --no-filters`), so no untracked, ignored or uncommitted text becomes a public PR body.
- Merge: `<W>`'s `HEAD` is `<sha>`, and `gh pr view <number> --repo
  github.com/<repository> --json
  state,baseRefName,headRefName,headRefOid,isCrossRepository,statusCheckRollup`
  shows `state` `OPEN`, `isCrossRepository` false, base `default_branch`, head
  `<W>`'s branch and head commit `<sha>`. Every rollup entry is green (a `CheckRun`
  concluded `SUCCESS`, a `StatusContext` in state `SUCCESS`), every
  `required_checks` name is present, and a rollup of 100 or more entries refuses
  rather than being judged on a partial page.

### Tracking, bindings and discharge

Pending events come one at a time: `target_for` refuses a delivery while any pending
event is unresolved at the seat or at `<W>`. So the order is push, `discharge`,
`pr create`, `discharge`, merge, `discharge`, each discharge being
`workflow.py discharge --root <W> --pending-id <id> --note <text>`. `discharge` does
not rewrite tracked S:W:H:E files, so the tree stays clean between the steps; any
`log` that records evidence precedes the commit, which precedes the push.

The shared classifiers never trust the `env -i` prefix, so the event kind comes from a
binding. After every check passes, `native_permission()` writes one create-only JSON
record (at most 4 KiB) under `<canonical>/.aegis/state/delivery-bindings/`. It names
`<W>` and the operation, and its file name is the sha256 of the session id, the hook's
`tool_use_id` and the request digest, never the raw ids. The directory and file are
opened without following a symlink (`O_CREAT|O_EXCL|O_NOFOLLOW`, component by
component), and a symlinked directory or file refuses. The count and the write happen
under an exclusive lock: at most 16 unexpired bindings exist, and at most one per
`<W>`, so a second call for the same `<W>` refuses while one is in flight. A binding
never approves anything; nothing reads one to decide an approval. There are exactly two
write points: the approval return and the advisory-seat audit return. If anything after
the write blocks the call, for example the audit append failing, the binding is removed
before the refusal returns.

PostToolUse looks up its own call's binding, re-derives `<W>` and the operation from
its own command (the push's `-C <W>`, the worktree whose branch is `--head`, or the
binding's `<W>` whose `HEAD` must be `<sha>`, all by file reads) and requires both to
match. It rechecks only `<W>`'s identity (direct child, verified linked worktree,
`ready` journal, verified ownership, branch form), never the delivery preconditions,
because after a merge the pull request is no longer `OPEN` and the remote `main` is a
new merge commit. It then records one `delivery` event on `<W>` and consumes the
binding. A binding rewritten by a same-uid process therefore cannot retarget an event;
`O_EXCL` only guards creation. A PostToolUse with no binding for its call, a binding
for another call, or a binding whose `<W>` fails the recheck keeps today's behaviour: a
recorded block and exit 2. If PostToolUse runs after a command that exited non-zero,
it still records the event; `discharge` resolves it and the journal keeps the outcome.

A failed Bash call fires `PostToolUseFailure`. A synchronous handler (the
`deliveryfailure` sub-command of `.claude/scripts/gate_lib.py`, separate from the
async ledger recorder) removes that call's binding and records no event, so a retry is
a new call with its own binding. Unconsumed bindings (an interrupted call, or an
advisory prompt the operator declined) expire after 30 minutes, the Bash tool's
10-minute maximum plus a margin, and are pruned by the next PreToolUse. The documented
recovery from a stale binding is to wait for its expiry.

An advisory seat's delivery is validated and audited on `<W>` as
`advisory_delivery_no_native_approval` and gets no native approval, but its binding is
written, so a delivery the operator approves by hand is still tracked on `<W>`.

### Deadline

The PreToolUse hook entry in `.claude/settings.json` carries an explicit `timeout` of
120 seconds. A delivery evaluation has a gate-side deadline of 60 seconds measured by a
monotonic clock from hook entry, so the reads that run before it (hard policy's
`delivery_default_branch`, the profile loads, target validation) count against it.
Every delivery read's timeout is `min(30 s, time left)`, the deadline is checked once
more immediately before the approval return, and running out of time refuses that
delivery. Refusals for every other tool and class are unchanged. Readiness
(`evaluate_readiness`) and some reused reads are unbounded or self-bounded
(`delivery_default_branch` runs `git symbolic-ref` with no timeout), so the 60-second
deadline is best-effort for them and the 120-second hook timeout is the real backstop.

### Limits

- **The push is not pinned to the verified commit.** A commit made in `<W>` between
  the approval and the push would be pushed unchecked. `main` stays protected, because
  the merge re-verifies every commit and `--match-head-commit` pins the head.
- **The base race is accepted.** `--match-head-commit` makes GitHub refuse if the head
  moves after the check, but the base can still change between the check and the merge.
- **A merge refuses whenever `main` has moved** since the branch was last updated,
  because the remote `main` must be an ancestor of `HEAD`. Bring the branch up to date,
  re-sign it and push it first.
- **The signing key is the only review boundary** on what reaches `main` through this
  class, including changes to the gate and to the profile: delivery deliberately does
  not require `<W>`'s runtime or profile to equal the canonical copies. That is
  acceptable because the key lives only with the host signer, which no worker or
  Claude session can use, and the coordinator signs only changes that passed two
  independent reviews. Readiness at `<W>` may import `<W>`'s tracked helpers; the clean
  and signature checks run first, so those are signed bytes.
- **Shell startup files are trusted.** The Bash tool's shell runs its startup files
  before the command. The prefix removes every variable they set, but a shell function
  or alias defined there could still shadow the command itself. The startup files are
  part of the trusted operator setup, as the sandbox is.
- **A call that outlives its binding**, such as an advisory prompt answered after 30
  minutes, reaches PostToolUse with no binding: exit 2 and no event. The coordinator
  reconciles.
- **Effect without success leaves no event.** A delivery that took effect but reported
  failure (for example a Bash timeout after the remote merge) fires
  `PostToolUseFailure`, which records nothing. The coordinator reconciles by reading
  the remote state.
- The gate's signature reads run with no `TMPDIR`, so Git writes the signature it
  verifies under `/tmp`, which must be writable where the hook runs.
- **A runtime-changing branch cannot be discharged from the seat.** Delivery itself
  does not compare `<W>`'s runtime with the canonical copy, but the stationary
  `discharge` is a coordination verb, and coordinate's reviewed-runtime check refuses a
  target whose `scripts`, `aegis_foundation`, `.claude/scripts` or
  `plugins/gas-city-workflow/scripts` differ from the canonical checkout, or whose
  profile or descriptor differs. After such a branch's push its delivery event stays
  pending on `<W>` and the next delivery step refuses; reconcile it outside this class.

### Live preflight before the first real delivery

Fixtures cannot show these live preconditions, so the coordinator runs this read-only
preflight first:

- `%G?` is `G` for a commit signed by `signing_key` under `HOME=<delivery_home>` with
  the gate's read environment (it is `U` unless the key has full or ultimate validity
  in that keyring).
- Live PreToolUse, PostToolUse and PostToolUseFailure payloads for Bash carry a
  `tool_use_id` and a session id, and PreToolUse and PostToolUse carry an identical
  `tool_input` (the binding key depends on both). The first real delivery observes
  this and fails closed if either differs.
- `gh auth status` and `git ls-remote origin` succeed under the exact fixed-environment
  prefix. They fail if the gh token lives in a keyring that needs DBus, or if the
  network is reachable only through a proxy variable the prefix removes.
- A recorded inventory of the live global, canonical and `<W>` configuration shows no
  key the allowlist refuses.
- The session runs with the PreToolUse `timeout` of 120 and the synchronous
  `PostToolUseFailure` `deliveryfailure` entry in `.claude/settings.json`.

## Identity and preservation

The profile must be a regular, unaliased, size-bounded JSON object with unique
keys, exact schema and a nonempty subset of the five known command classes.
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
