# Gas City job runner

On 2026-09-23 the operator chose to stop pasting a command for every live step. Live platform scripts
must run in the Gas City supervisor's mount namespace. The Claude session is sandboxed in a different
one, and the operator declined giving it unsandboxed access. Until now each reviewed wrapper therefore
needed a human `systemd-run --user` paste. That paste was a namespace workaround, not a review: the
operator had already authorized live steps after two reviewer SOURCE_PASS verdicts.

The runner replaces those pastes with one start command.

## r2: answers to the r1 reviews (`27bb1ff5`: HOLD, HOLD)

- **Operator controls hold every job** (A1, B should-fix 1).
  - PAUSE, the HALTED latch and the single-job rule are checked in `cycle()` immediately before
    each job.
  - A non-zero exit, a failed launch or any runner error sets `state/HALTED`, and nothing runs until
    the coordinator has recorded the failure and cleared it.
  - The runner handles one queued job at a time. With more than one in the queue it runs none.
  - A started job with no final record (a crash, or a runner stopped mid-job) blocks all later jobs.
    It stays blocked until the coordinator files `done/<id>.resolved.json` after checking the
    wrapper's own log.
- **Reviews are parsed, not searched** (A2).
  - Each transcript must be a reviewer subagent's own JSONL:
    - the first record is a sidechain user record carrying an `agentId`;
    - every record has the same agent, and the file is named `agent-<agentId>.jsonl`;
    - the first prompt line is exactly `candidate=<commit>`, with no other `candidate=` token.
  - Each transcript must contain exactly one `SubagentHandback` report, and that report's first line
    is the verdict.
  - Every transcript filed under `reviews/<commit>/` must pass. One HOLD anywhere refuses the commit.
  - The two cited reviews must come from different agents.
- **Reviews bind a wrapper; the runner cannot start itself** (A3).
  - Each cited review's prompt must name the job's repo-relative wrapper path.
  - `gct-jobrunner/` wrappers are not admissible.
  - `main()` starts only inside the `gas-city-jobrunner.service` cgroup of the uid-1000 user manager.
- **No re-runs** (A4). A wrapper that already started at a commit never starts again at that commit,
  under any job id.
- **Start check that works on systemd 255** (B1).
  - Identity is proved from `/proc/self/cgroup` plus `INVOCATION_ID`, with no read of the manager's
    `/proc/<pid>/ns` link. That read needs ptrace access, and systemd 255 leaves the manager with
    capabilities, so it could fail every start.
  - A transient unit without sandboxing runs in the manager's mount namespace.
- **Hardening from the should-fixes.**
  - The committed wrapper blob (`git cat-file`), the working file and the job digest must agree.
  - The runner's git calls use `-c core.fsmonitor=false -c gpg.program=/usr/bin/gpg -c core.hooksPath=/dev/null`.
  - Job files and transcripts are opened with `O_NOFOLLOW|O_NONBLOCK` and checked with `fstat`.
  - An exit code is logged before any record is written.
  - The start wrapper checks `--untracked-files=all`.
  - `submit_job.py` does three more things: it validates the id first, refuses while the queue is
    non-empty or HALTED, and refuses to reuse a transcript copy whose bytes differ.

## What it does

`operator/JOBRUNNER.sh` starts it once as the transient user service `gas-city-jobrunner` and execs
`jobrunner.py` through the reviewed `source-launch.py`, pinned by digest. Every 5 s the runner runs
one `cycle()`:
1. Wait while any of these holds:
   - `PAUSE` exists;
   - `state/HALTED` exists;
   - a started job is unfinished;
   - the queue holds more than one job.
2. `admit()` the single queued job. A refusal is recorded in `done/<id>.refused-*.json`, the job is
   dequeued, and nothing is retried.
3. Write `done/<id>.started.json` and remove the queue file.
4. Launch `systemd-run --user --wait --collect --quiet --unit=gc-job-<id> -p UMask=0022 /bin/sh <wrapper> <commit>`.
5. Log the exit, write `done/<id>.json`, and set HALTED on anything but exit 0.

`admit()` requires all of these:
1. **The job file.** A regular, single-link file owned by uid 1000, at most 64 KiB, in strict JSON
   with exactly the keys `job_id`, `commit`, `wrapper`, `wrapper_sha256` and `reviews`. It is named
   `<job_id>.json`, and the id has never appeared in `done/`.
2. **The commit.** It is the HEAD of the ga-e0t1 worktree, the worktree is clean (untracked files
   included), and `git verify-commit` reports VALIDSIG from primary key
   `7720D1FE503A88EDECA61A6F0C7D823543E01875`.
3. **The wrapper.** It matches `designs/<package>/operator/<NAME>.sh` with the package not
   `gct-jobrunner`. It is a tracked regular blob at the commit, and the blob, the working file and
   `wrapper_sha256` agree. It is not a symlink, and it has never started at this commit.
4. **The reviews.** They satisfy the rules in r2 above.

The coordinator queues jobs with `submit_job.py`, which does the following:
- copies the reviewer transcripts;
- dry-runs the same `admit()` against the real git state;
- renames the job into the queue. The probe and queue directories sit on one filesystem, and the
  Claude sandbox sees the same one.

A reviewer prompt for a job-bound package names the wrapper with a line such as
`Wrapper: docs/ai/work-tracking/active/.../designs/<package>/operator/<NAME>.sh`.

## What an exit code means

The runner records the `systemd-run --wait` exit, which is the wrapper's exit code. It is not the
wrapper's verdict: the outcome lives in the wrapper's own log. Wrappers written from r2 on exit
non-zero on a refusal, so a failed step halts the runner.

After a crash, find the outcome in three places:
- the wrapper's staging log;
- `journalctl --user -u gc-job-<id>` (the unit is collected, so `systemctl status` shows nothing);
- the `started` and `finished` lines in `runner.log`.

`state/runner.json` keeps `last_poll` at the start of a running job, because the runner is waiting
inside `systemd-run` until the job ends.

A job unit inherits the user manager's environment, exactly as the operator's hand-pasted
`systemd-run` did. The runner's `ENV` applies only to its own git and `systemd-run` client calls.

## Trust model, stated plainly

This guards against mistakes:
- an unreviewed, held or dirty commit;
- the wrong wrapper;
- a stale digest;
- a replay or re-run;
- steps cascading after a failure.

It does not guard against a compromised coordinator. The coordinator writes the packages, commits
them (the signing key is available to the session) and files the transcripts. The real gate is the
pair of independent reviewers and the standing stop conditions, which the coordinator still honors.

The runner adds no capability beyond what the operator's pastes already did. It runs the same kind
of reviewed wrapper, in the same namespace, the same way, one step at a time, and it halts on
failure.

## Operator controls

| Action | Command |
| --- | --- |
| Start (once per WSL boot) | `systemd-run --user --unit=gas-city-jobrunner --collect -p UMask=0022 sh <J>/operator/JOBRUNNER.sh <reviewed commit>` |
| Pause before the next job | `touch ~/.local/share/gas-city-staging/jobs/PAUSE` (only the operator removes it) |
| Resume | `rm ~/.local/share/gas-city-staging/jobs/PAUSE` |
| Stop the runner | `systemctl --user stop gas-city-jobrunner` (a running job keeps its own `gc-job-*` unit, and a restart waits for it to be resolved) |
| Stop a running job | `systemctl --user stop gc-job-<id>`, which halts the runner |
| Status | `cat ~/.local/share/gas-city-staging/jobs/state/runner.json`, `tail ~/.local/share/gas-city-staging/jobs/runner.log`, `ls ~/.local/share/gas-city-staging/jobs/done` |

`<J>` is this directory. The runner's code is fixed at start. Updating it takes a new reviewed commit
and a restart.
