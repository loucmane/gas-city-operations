# Gas City job runner

On 2026-09-23 the operator chose to stop pasting a command for every live step. Live platform scripts
must run in the Gas City supervisor's mount namespace. The Claude session is sandboxed in a different
one, and the operator declined giving it unsandboxed access. Until now each reviewed wrapper therefore
needed a human `systemd-run --user` paste. That paste was a namespace workaround, not a review: the
operator had already authorized live steps after two reviewer SOURCE_PASS verdicts.

The runner replaces those pastes with one start command.

## What it does

`operator/JOBRUNNER.sh`, started once as the transient user service `gas-city-jobrunner`, execs
`jobrunner.py` through the reviewed `source-launch.py`, pinned by digest. The runner then works as
follows:
- It polls `~/.local/share/gas-city-staging/jobs/queue/` every 5 s and handles one job at a time.
- For each `<job_id>.json` it runs `admit()`. Every refusal is recorded in `done/` and dequeued, and
  nothing is retried.
- It writes `done/<job_id>.started.json`, removes the queue file, and only then launches
  `systemd-run --user --wait --collect --quiet --unit=gc-job-<job_id> -p UMask=0022 /bin/sh <wrapper> <commit>`.
  So a crash can never replay a job.
- It records the exit in `done/<job_id>.json`. The wrappers keep their own logs and evidence roots, as
  before.

`admit()` requires all of these:
1. **Job file.** A regular, single-link file owned by uid 1000, at most 64 KiB, in strict JSON with
   exactly the keys `job_id`, `commit`, `wrapper`, `wrapper_sha256` and `reviews`. Its name is
   `<job_id>.json`, and the id has never appeared in `done/`.
2. **Commit.** It is the HEAD of the ga-e0t1 worktree, the worktree is clean (untracked files
   included), and `git verify-commit` reports VALIDSIG from primary key
   `7720D1FE503A88EDECA61A6F0C7D823543E01875`.
3. **Wrapper.** It matches `designs/<package>/operator/<NAME>.sh`, is tracked at that commit, is not a
   symlink, and its bytes equal `wrapper_sha256`.
4. **Reviews.** There are two distinct transcript copies, directly under `reviews/<commit>/`. Each
   contains `candidate=<commit>` and `SOURCE_PASS <commit>`, and neither contains `HOLD <commit>`.
5. **Pause.** `PAUSE` is absent. While it exists, jobs simply wait.

The coordinator queues jobs with `submit_job.py`, which does three things:
- copies the reviewer transcripts;
- dry-runs the same `admit()` against the real git state;
- renames the job into the queue in one atomic step.

## Trust model, stated plainly

This guards against mistakes: an unreviewed or dirty commit, a wrong wrapper, a stale digest, a
replay, a held review. It does not guard against a compromised coordinator. The coordinator writes the
packages, commits them (the signing key is available to the session) and files the transcripts. The
real gate is the pair of independent reviewers and the standing stop conditions, which the
coordinator still honors.

The runner adds no new capability beyond what the operator's pastes already did. It runs the same
reviewed wrappers, in the same namespace, the same way. It narrows what can run to tracked operator
wrappers at a signed clean commit.

## Operator controls

| Action | Command |
| --- | --- |
| Start (once per WSL boot) | `systemd-run --user --unit=gas-city-jobrunner --collect -p UMask=0022 sh <J>/operator/JOBRUNNER.sh <reviewed commit>` |
| Pause new jobs | `touch ~/.local/share/gas-city-staging/jobs/PAUSE` |
| Resume | `rm ~/.local/share/gas-city-staging/jobs/PAUSE` |
| Stop the runner | `systemctl --user stop gas-city-jobrunner` (a running job keeps its own `gc-job-*` unit) |
| Stop a running job | `systemctl --user stop gc-job-<job_id>` |
| Status | `cat ~/.local/share/gas-city-staging/jobs/state/runner.json`, `tail ~/.local/share/gas-city-staging/jobs/runner.log` |

`<J>` is this directory. The runner's code is fixed at start. Updating it requires a new reviewed
commit and a restart.
