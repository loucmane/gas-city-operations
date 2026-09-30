# Gas City operations runbook: cold start, provider handover, recovery

This runbook covers the provider-independent execution goal. It is verified live on 2026-09-30: the handover proof
gct-yt3e ran Claude, then Codex, then Claude, and was delivered as Template PR 73.

Run every command below from `/home/loucmane/gas-city-ops` with this prefix, written `GC`:

```bash
GIT_OPTIONAL_LOCKS=0 /usr/bin/env GC_HOME=/home/loucmane/gascity/home \
  PATH=/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin \
  /home/loucmane/gascity/bin/gc --city /home/loucmane/gascity/city
```

## 1. Cold start: check the city

1. `GC status --json`: the controller must be running. It runs under
   `gascity-supervisor-home-42adab5d.service` as `gc supervisor run`.
2. Check the city and rig suspension flags in the same output. By default all rigs start suspended
   (`suspended_on_start = true`).
3. `GC session list`: see which worker sessions are running.
4. `GC --rig <rig> bd list --status open --json`: before resuming a rig, look for stale routed work. Any agent
   that is not suspended can pick up stale routed Beads as soon as the rig resumes.

## 2. Normal-operations configuration (Template rig)

`/home/loucmane/gascity/city/city.toml` enables exactly two Template worker lanes:

- **Claude:** `gas-city-template/gc.implementation-worker`, provider `claude-template-candidate`.
- **Codex:** `gas-city-template/codex`.

The other twelve Template pack agents, including the rig's `core.control-dispatcher`, are patched
`suspended = true`. Both lane patches set `work_dir` to the task worktree, because the Claude lane wrapper exits
with status 2 unless it starts inside a linked worktree directly under
`/home/loucmane/gas-city-template-candidate-worktrees`. The original file is kept at
`city.toml.pre-yt3e-fastpath-2026-09-30`.

## 3. Whenever city.toml changes: refresh the provisioning receipt

The provisioning receipt pins the controller's config revision. After any config change, Core refuses the managed
lanes with `permission_revision mismatch: got <new> want <old>`. To fix it:

1. Read the new revision: `GC trace show --type cycle_result --since 1m --json`, field `config_revision`.
2. Write a new receipt input. Copy `/var/tmp/ga-e0t1.22-p14-input-20260930/receipt.input.draft.json`, change only
   `permission_revision` to the new revision, and save it as `/var/tmp/<name>.receipt.input.draft.json` with mode
   0600.
3. Check, then apply:
   ```bash
   /usr/bin/python3 -I -S -B /home/loucmane/gas-city-template/bin/gct-managed-worker-provision \
     --city /home/loucmane/gascity/city --receipt-input <input> \
     --consumer-witness /var/tmp/ga-e0t1.22-p14-adoption-20260930/typed-support.json \
     --consumer-witness-sha256 c61c2384493674139d8a1265f8c5963d36fc5b9f6d728b3c038feaa5689bf442 \
     --check --json   # expect drift == ["receipt.sha256"], then rerun with --apply
   ```

Step 2 re-approves the current configuration, so the operator runs it.

## 4. Run a task on a lane

1. Create the task Bead: `GC --rig gas-city-template bd create --type task ...`, with the brief in the description.
2. Create the worktree: `git -C /home/loucmane/gas-city-template worktree add -b codex/<bead>-<slug>
   /home/loucmane/gas-city-template-candidate-worktrees/<bead> origin/main`.
3. Point the lane patch `work_dir` at that worktree (a config change, so do section 3), and set the Bead's
   `gc.work_dir`, `work_dir` and `gc.check_path`.
4. `GC rig resume gas-city-template` and, if the city is suspended, `GC resume`.
5. `GC --rig gas-city-template sling <lane> <bead> --no-formula --no-convoy --json`.
6. Watch `GC session list` and the Bead notes. To see the worker's screen:
   `tmux -S /tmp/tmux-1000/city capture-pane -p -t <session>`.

## 5. Provider handover on the same Bead and worktree

1. The current worker leaves the work uncommitted and appends a `LEG n DONE` note with `git status --short`.
2. `GC --rig gas-city-template bd update <bead> --assignee <next lane>`.
3. `GC session close <session id>`. This releases the claim, and the Bead returns to open.
4. `GC --rig gas-city-template bd update <bead> --set-metadata gc.routed_to=<next lane>`, or re-sling.
5. The next lane's worker claims the Bead with `gc hook --claim` and continues in the same worktree.

Workers never commit. The coordinator commits exactly the task paths, excluding Core's session scaffolding
(`.claude/`, `.codex/`, `.agents/`, dotfiles). Then one aegis-reviewer pass, run on a detached copy under
`/home/loucmane/gas-city-template-worktrees`, because the review gate only admits that root. Then the PR and
merge.

## 6. Recovery

- **Stop all work at once:** `GC rig suspend gas-city-template`, then `GC suspend`. Running sessions are drained.
- **A worker exits at startup:** capture its pane. Status 2 from the Claude lane means the wrong cwd, so check the
  session's WORKDIR in `GC session list`. A `permission_revision mismatch` event means the receipt is stale; see
  section 3.
- **An unexpected agent wakes up:** suspend the rig, add a `[[patches.agent]] ... suspended = true` block for it,
  refresh the receipt, then resume.
- **Roll back the config:** restore `city.toml.pre-yt3e-fastpath-2026-09-30` and refresh the receipt for the
  restored revision. Receipt `a61666b3` matched the original config.
- **Known Core issue:** a nudge poller started by a short-lived `gc session nudge` can die by SIGPIPE and leave a
  stale `.gc/nudges/pollers/*.pid`. Core reaps such markers on the next enqueue. Do not treat a marker as proof of
  a live poller.

## 7. Where the evidence is

- **Bead gct-yt3e:** leg notes, coordinator notes and the PR link.
- **Template PR 73:** the proof diff and review summary.
- **Bead ga-e0t1:** the full coordination history, including the ga-mb91 release diagnosis, the journal compaction
  fix (Operations PR 395), and the switch to this simpler path.
