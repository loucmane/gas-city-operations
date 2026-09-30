# gct-oak5 prerequisite: activate the Template Claude candidate lane (r1)

**Operator decision (2026-09-27, about 10:50 CEST):** "Prepare and apply". The deployment is approved with two
independent aegis-reviewer SOURCE_PASS verdicts per stage, stopping on any refusal or drift. The lane is Template
PR 72, merged as `3474abfa`: tree `55d7a9df`, gct-mbg6, the reviewed intake plus the reviewed CI-timeout commit.

## Stages

1. **A: activation (this package).** Live `activate.py` steps, one invocation each:
   `host`, `inputs`, `root`, `checkout`, `registry`, `render`, `city`, `reload`.
2. **M11: metadata successor.** It adopts:
   - the changed `city.toml` (`e5b68c40` → `b0eeb168`);
   - the registry (`1225b7c5` → `0b0e6a87`);
   - the fragment (the recorded render);
   - the Template authority `cfd353f3` → `3474abfa`.

   It follows the M10 pattern and is its own reviewed package.
3. **P12: receipt refresh.** It re-pins `template_commit` and `member_heads[template]` to `3474abfa`. It also
   publishes the typed Template candidate profile (`signer_identity: "none"`) with the Template launch-check
   path, per the merged docs' activation items 3–4. It follows the P11 pattern and is its own reviewed package.

Until P12, the worker receipt pins `cfd353f3`, so every signing launch refuses on the version mismatch (fail
closed). No worker launches between `checkout` and P12. Then the gct-oak5 handover window runs
(C1 Claude → X Template codex → C2 Claude).

## The merged docs' activation contract, item by item

1. **Dedicated root and linked worktree.** `root` creates `/home/loucmane/gas-city-template-candidate-worktrees`
   (operator, 0755, empty). The handover worktree itself is created and checked by the gct-oak5 window package,
   before any coordinator git there.
2. **Role prompt.** The pinned pack `cc9e72b2` `implementation-worker` prompt was read in full: pack cache
   `8b0f193e…/gascity/roles/agents/implementation-worker/prompt.template.md`, 4977 bytes.
   - It runs only the claim protocol (`gc hook --claim --json`, `bd show`, `gc runtime drain-ack`) and executes
     and closes the claimed Bead.
   - It asks for no worktree creation, commit, push or pull request.
   - So no lane prompt is needed, and this justification is the record. The handover step Beads carry their own
     stop contract.
3. **Policy install, Python and receipt.**
   - **Policy.** It is served from the canonical checkout at `3474abfa` as a regular file. `checkout` and
     `render` refuse any lane file with a group or world write bit.
   - **Python.** `/usr/bin/python3.12` still measures `e50d468e`, the profile's pin; `make_pins` refuses
     otherwise.
   - **Receipt.** The typed candidate receipt is P12's.
4. **Launch check.** P12 pins the Template launch-check script in the receipt. The handover window stamps each
   routed Template Bead's `gc.check_path`.
5. **The override.** `city` removes the Template `[[rigs.overrides]]` entry for `implementation-worker` (plain
   `claude`, `auto-edit`, `template-worktrees-and-git-metadata`).
   - It then reads the composed configuration and refuses unless the worker resolves to
     `claude-template-candidate` with `full-auto`.
   - The same step moves the worker's `work_dir_roots` to the candidate root, the only root the wrapper admits.
   - It also caps the worker at `max_active_sessions = 1`, from the handover decision of 2026-09-24.
6. **`run-operator`.** Its override stays byte-identical; `new_city` and the composed proof both assert it.

## Live facts (read-only, 2026-09-27)

- **Canonical Template checkout.** Detached at `cfd353f3`. Its status is only `?? deploy/` and
  `?? gas_city_template.egg-info/`.
  - A refspec-free `git fetch origin` (about 10:55 CEST) brought `3474abfa`. The repository is private, so the
    fetch used the operator's credentials; the executor's own git is credential-free.
  - The change set is the 16 reviewed paths.
- **Live files.** `city.toml` `e5b68c40`, registry `1225b7c5`, fragment `df688a29`. These are the M10 manifest
  and receipt state.
- **Real Core dry run.** A shadow at `~/.local/share/gas-city-staging/gct-oak5-dry` used the postimage
  `city.toml` and a fragment rendered from the merge.
  - `gc config show --validate` passed.
  - `--json` resolved `implementation-worker` to `claude-template-candidate` with `full-auto`, the grant,
    `WorkDirRoots` = the candidate root and `MaxActiveSessions` = 1.
  - `run-operator` stayed `claude`, `haiku-4-5`, `auto-edit`, `template-worktrees-and-git-metadata`.
- **Live dry run of `host` and `inputs`** (`/var/tmp/gct-oak5-activation-dryrun-20260927`):
  - `host` passed; the hidden cgroups were only `init.scope` and `gpg-agent.service`.
  - `inputs` derived the pinned postimages. Its closing quiet check once saw a transient `partial` status.
    `resume inputs` then proved the postcondition and passed, which is the designed path for that case.
- **Pins.** `pins.json` is `7ec0f7b10763397199c4fb6e9326383f5c9ee9407066e9fb392501fd51c6ec16`, with inputs
  registry `0b0e6a87` and `city.toml` `b0eeb168`.

## Differences from ga-6utp r12

The executor, discipline, resume and rollback are the reviewed ga-6utp r12 design. `preroute.py` and
`candidate_git.py` are byte-identical copies, which a test asserts.
- **`checkout` really moves** `cfd353f3` → `3474abfa` (detached; hooks, fsmonitor and attributes off). It also
  requires the target tree to equal the reviewed `55d7a9df`.
- **Order:** `render` precedes `city`, so the composed postimage in the shadow already has the new provider.
- **`city` writes `city.toml`** (PackV2 allows `[[rigs.overrides]]` and `[[patches.agent]]`; only `[[agent]]` is
  refused).
  - The text edits have asserted counts and are then proven at the TOML level: nothing else changes.
  - The shadow symlinks every city entry except a copied postimage `city.toml`.
  - The composed proof comes from `gc config show --json`: provider, `OptionDefaults`, `WorkDirRoots`,
    `MaxActiveSessions`, `Scope`, and `run-operator` unchanged.
- **`reload`** proves the same composition live, plus `gc agent list` (provider, pool `{0,1}`).
- **`rollback`** restores `city.toml`, the fragment and the registry, then the checkout, then reloads. It proves
  the worker is back on plain `claude` with the old `work_dir_roots`. The candidate root stays.
- **Lane files** add the Template wrapper, library, policy, provider template and profile. A lane file may not be
  group- or world-writable.

## Tests

`test_activate.py` has 35 cases, all passing:
- the full sequence;
- binding and quiet refusals;
- the `new_city` edits and five predecessor refusals;
- candidate-record and registry refusals;
- checkout: moves, dirty tree, change set, tree, group-writable lane file;
- three wrong renders refused before any write;
- city: Core rejection and a wrong resolution refused before writing, and the shadow proof recorded;
- leftover-shadow blocking and exact-shape clearing;
- `resume city`, and `resume` without an intent;
- rollback from five stop points;
- a foreign `city.toml` refused;
- the live pins and helper identity.

## Run record (2026-09-27, applied)

**Reviews.** Two SOURCE_PASS reviews of `9936810e` are filed.

**Should_fix dispositions before the live run:**
- **Render middle state** (A 1, B 7). The real Core ran `gc config show --validate` in a staging shadow with the
  live `city.toml`, override still in place, plus the new fragment: "Config valid". In that state the worker
  composes as plain `claude` with `auto-edit`, because the override wins, so the middle state changes nothing
  effective.
- **Checkout hardening** (B 3), as read-only operator pre-checks:
  - no `core.worktree`, include, submodule, autocrlf/eol, sparse checkout, extensions, promisor or `hook.*` keys;
  - the only working-tree `.gitattributes` is the tracked root one;
  - `check-attr` shows no attribute on the 16 changed paths;
  - no `index.lock`;
  - git 2.43.
- **Python** (A 2, B 5). It was measured again at `e50d468e` by the `make_pins` recheck, whose reproduced pins
  equal `7ec0f7b1`.
- **Pre-P12 barrier** (A 3, B 4). The claim that signing launches fail was the wrong mechanism for this lane.
  - The real barriers are every rig suspended, nothing routed, and the empty candidate root: the wrapper refuses
    any directory that is not a linked Template worktree directly under it.
  - M11 and P12 must assert the Template rig is suspended and no Template Bead is routed to the worker.
- **Crash temporaries and a controller restart** (A 5, B 1-2). These are the hand procedure.
  - A `.<name>.tmp.gct-oak5.N` beside a live file, or a half-moved checkout, is inspected by hand before `resume`
    or `rollback`.
  - A controller restart inside a step leaves only `rollback`.
  - None occurred.

**Live steps**, all first attempt, package root `~/.local/share/gas-city-staging/gct-oak5-activation-r1`:

| Step | Result |
| --- | --- |
| host | pass |
| inputs | pass |
| root | `/home/loucmane/gas-city-template-candidate-worktrees`, operator, 0755 |
| checkout | canonical Template at `3474abfa`; the linked `gas-city-native` is untouched at `68d00588` |
| registry | `0b0e6a87` |
| render | fragment `df9c82d0` |
| city | `b0eeb168`, with the shadow proof recorded |
| reload | `no_change`, revision `06076790` |

**Composed live.** `gas-city-template/gc.implementation-worker` is on `claude-template-candidate` with `opus-5-5`,
`full-auto` and grant `managed-7d0dfd6c7f3b4e62`. Its `WorkDirRoots` is the candidate root, `MaxActiveSessions` is
1 and its pool is `{0,1}`. `run-operator` is unchanged.

Recorded on ga-e0t1 at 09:10Z.

## Run order after two reviews

- **Root.** A fresh operator-staging package root, `~/.local/share/gas-city-staging/gct-oak5-activation-r1`,
  holding a copy of `pins.json`.
- **Invocation.** One step per `systemd-run --user --wait --collect --pipe -q -p UMask=0022 /usr/bin/python3 -I
  -B activate.py <root> 7ec0f7b1… <step>`.
- **Steps:** `host`, `inputs`, `root`, `checkout`, `registry`, `render`, `city`, `reload`.
- **On an interrupted step:** inspect it, then `resume <step>`, or `rollback`.
- **Before `host`:** confirm the pins still match (`make_pins` output equal) and that no other gc actor is
  running.
