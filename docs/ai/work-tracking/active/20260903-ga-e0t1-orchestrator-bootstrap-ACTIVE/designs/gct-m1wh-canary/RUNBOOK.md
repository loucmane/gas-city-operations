# gct-m1wh platform canary (ga-0t04, M5 LAYOUT.md step 7)

This package runs `gc platform canary` once, after M5 (accepted 2026-09-23 11:50:01Z) and the P6
receipt adoption (12:36:00Z, two SOURCE_PASS evidence reviews).

Why it is needed:
- The Template's managed-worker-provisioning.md, step 7, says to run the platform canary and resume
  product work only from its PASS receipt.
- The P6 plan launches no worker before the canary passes.

## What Core does

The source is Core `796d9a7a`, the commit the live gc `69d00186` was built from:
`cmd/gc/cmd_platform_canary.go` and `internal/managedworker/canary{,_run,_profile}.go`.

1. **Load and pin.** It loads the live provisioning receipt and observes the live environment through
   the managed-product dispatch gate. It requires `--runner` and `--runner-sha256` to equal the
   receipt's `canary_runner`, and verifies the runner bytes.
2. **Select the profile.** It selects the typed profile explicitly: `--profile
   gascity/gc.implementation-worker --profile-kind signing`. The receipt carries `profile_kind` and a
   `control_policy`, so an unscoped canary is refused. It verifies the control policy before and
   after every scenario.
3. **Run the scenarios.** It runs `RequiredCanaryScenariosFor(signing)` under one wall-clock bound.
   These are the nine scenarios: clean-launcher, validator-absent, detached-head, unreadable-mail,
   denied-subprocess-socket, stale-session-killed-tmux, missing-provider, publisher-failed-finalize
   and publisher-success-noop. Each is one runner process that receives the selected profile in
   `GCT_CANARY_WORKER_PROFILE_JSON`.
4. **Publish.** Only if every scenario passes does it publish a v2 receipt. It writes
   `.gc/runtime/canary/profiles/<sha256(profile)>.json` and the immutable
   `.gc/runtime/canary/history/<receipt_sha256>.json`. A failed or partial run publishes nothing, and
   the prior receipts stay byte-identical.

## What the runner does

The runner is `gct-managed-worker-canary` `3beeedb2`, VERSION 3, pinned in the provisioning receipt.

- **Scratch isolation.** Every scenario uses `SCRATCH/RUN_ID/<scenario>`, with:
  - a `git clone --no-local` of the launcher source at the base commit;
  - its own `GC_HOME`, scratch city and scratch supervisor (`gc supervisor run` with the scratch
    `GC_HOME`);
  - tmux socket `canary-<run-id>`.
- **Teardown.** It runs `gc stop` and `gc supervisor stop`, both with the scratch `GC_HOME`, then
  reaps the exact tmux server bound to that socket.
- **No inference, no real signer.** The worker is the runner's own `--worker` mode, registered as
  scratch provider `canary`. It signs with an ed25519 key it generates under `<scenario>/signing`.
  It performs no model inference, never reaches the real signer, and has no pinentry path.
- **Toolchain check.** The clean-launcher worker verifies the pinned Go toolchain (`go1.26.7`,
  `182d1dc9`) with a network-free build, using `GOCACHE` in scratch.
- **Fault scenarios.** Two of the fault scenarios use `unshare --user --map-current-user --net`. The
  kill scenario kills only a session on the scratch socket.
- **Live reads.**
  - The controller gate reads the live provisioning receipt.
  - It runs the pinned `build-artifact-valid.sh` from the live pack cache, with the scratch `GC_HOME`.
  - One polling call, `gc --city <scratch city> bd show`, inherits the caller's `GC_HOME` (live).
    The scratch city imports the public packs at `3b3b89f2` and the bundled packs at `f895c0ff`.
    The 2026-08-28 canary already filled those live cache slots.
  - `canary-run.py` reports any cache-slot change as a note.
- **Global lock.** The runner holds `/tmp/gct-managed-worker-canary.lock`.

The 2026-08-28 canary (runner `09b50333`, v1 receipt `ff10fbe7`) passed all nine scenarios in about
6 minutes. This is the first native run of runner v3. `--max-wall-time` stays at the 30m default.

## Inputs (all pinned in `canary-run.py`)

| Input | Value |
| --- | --- |
| gc | `/home/loucmane/gascity/bin/gc` `69d00186` (install-manifest core; activation commit `796d9a7a`) |
| runner | `.gc/runtime/provisioning/bin/gct-managed-worker-canary` `3beeedb2` |
| provisioning receipt | `0b30c23f`, self `c635e8ee` |
| install pair | manifest `2d7eadce`, receipt `9342b33e` |
| profile | `gascity/gc.implementation-worker`, signing, `218675da`, control policy `16022d04` |
| launcher source | `/tmp/ga-mutg-build-20260919/repro-source`, clean at base `796d9a7a`; the reviewed ga-mutg build input. The August canary likewise cloned the Core build tree at its gc binary commit. |
| scratch root | `/home/loucmane/gascity/canary-evidence` (existing, not a Git worktree) |
| run id | `m1wh-20260923-r1`; the longest scratch supervisor socket is 102 of 107 bytes |
| evidence root | `/var/tmp/gct-m1wh-canary-20260923-r1` (fresh) |
| legacy receipt | `receipt.json` and `history/ad9c3eeb….json`, both `ff10fbe7`, must stay unchanged |

The process environment is fixed. It mirrors the live supervisor's locale, `SHELL`,
`GC_DISABLE_USAGE_METRICS` and `GIT_OPTIONAL_LOCKS`, and sets:

- `GC_HOME`: live;
- `GC_BIN`: the runner requires it, and `gc platform canary` does not export it;
- `PATH`: `/home/loucmane/gascity/bin` first, for `bd` and `dolt`.

It deliberately excludes the following:

- every `GCT_*` variable, because those are the runner's inline and targeted test switches;
- `GC_SUPERVISOR_PRESERVE_SESSIONS_ON_SIGNAL`, which would keep scratch sessions alive past teardown;
- `SSH_AUTH_SOCK`.

## Order

1. **Reviews.** Two independent reviews of this package commit.
2. **Operator start.** From a real WSL terminal, the operator runs once:
   `systemd-run --user --unit=gct-m1wh-canary --collect -p UMask=0022 sh $C/operator/CANARY.sh <commit>`.
   `C` is this directory. The output goes to
   `~/.local/share/gas-city-staging/gct-m1wh-canary/canary-<ts>.txt`.
3. **What the run checks.** `canary-run.py` performs these steps:
   - **Precheck:**
     - umask;
     - the live supervisor identity (3150812, start 8461901), and that it shares the supervisor's
       mount namespace;
     - every pin;
     - that the provisioning receipt declares the pinned profile and runner;
     - that the profile receipt slot, the run root and the evidence root are all absent;
     - that the launcher is clean at the base;
     - the socket budget, the tools, and that no process references the run root.
   - **Run:** `before.json`, then the canary, then `after.json`.
   - **Verify on PASS:**
     - the exact stdout pass line and receipt path;
     - that the live canary tree gained exactly `profiles/`, the profile receipt and its history copy,
       with modes 0700/0600/0600, and changed nothing else;
     - that the history bytes equal the profile receipt bytes;
     - the v2 receipt fields: profile, kind, digest, runner, gc `796d9a7a`/`69d00186`, Template,
       revision, provisioning self digest, nine passing scenarios with attention latency ≤ 1;
     - that the pins and the supervisor are unchanged;
     - that each scenario has `scenario.json` and no `teardown-error.txt`;
     - that no scratch process survives, after polling for up to 30 s while scratch dolt and tmux
       exit.
4. **Evidence reviews.** Two reviews of the evidence. Then the first worker window (goal step 3):
   the ga-5ot6 successor, routed through `gc sling`.

Nobody runs gc from the start of the unit until its log ends. The canary compares no cache
timestamps, but a quiet run keeps the evidence unambiguous.

## Stop conditions

Stop on any of these:
- any precheck refusal;
- a canary exit other than 0;
- a verify refusal;
- a changed legacy receipt;
- a live change outside the two receipt files;
- a supervisor restart;
- a surviving scratch process;
- a pinentry prompt;
- any need to widen network policy or `PATH`.

A refused canary has published nothing. Its scratch tree and evidence stay in place for diagnosis.
Never retry into a used run id or evidence root: a retry takes a new run id, a new root and a new
review.
