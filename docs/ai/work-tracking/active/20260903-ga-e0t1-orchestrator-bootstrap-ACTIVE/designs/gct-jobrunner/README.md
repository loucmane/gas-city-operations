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

## r3: answers to review A of `c0a9797c` (HOLD)

**The must-fix: a stopped job read as success.**
- `systemctl --user stop gc-job-<id>` kills the wrapper with SIGTERM. For a simple service, systemd
  counts SIGTERM as a clean exit, so `systemd-run --wait` returned 0 and the next queued job could run.
- Jobs now run as `--service-type=oneshot -p TimeoutStartSec=infinity`, where SIGTERM is a failure.
- More fundamentally, the runner now halts after EVERY job, whatever its exit code. The exit code is not
  the verdict, so the coordinator reads the wrapper's log, records the outcome on the Bead, and only then
  clears `state/HALTED`.

**Should-fixes taken:**
- PAUSE is re-checked after admission, right before the started record. A job paused during admission
  stays queued.
- The started record and the queue directory are fsynced before launch.
- A cited review must contain an exact `Wrapper: <path>` line, not merely mention the path.
- Transcripts are parsed with the strict duplicate-key hook, and every record must carry the same
  `agentId` and `isSidechain: true`.
- Started records, resolution records, the heartbeat, the lock and `runner.log` are all opened without
  following links. JOBRUNNER.sh refuses a symlinked stage directory or log.
- The runner's git calls also pin `gpg.ssh.program` and `gpg.x509.program`. Filter drivers are not
  neutralized, and the comment says so.
- `own_unit()` requires the full cgroup line. It is documented as a mistake guard, not an identity
  proof.
- A resolution record must be a strict JSON object naming `job_id`, `outcome` and `evidence`. It
  counts only once `gc-job-<id>.service` is inactive or failed.
- `submit_job.py` refuses while any job is unfinished.

**From review B of `c0a9797c` (SOURCE_PASS):**
- The runner and JOBRUNNER.sh require the user D-Bus socket. Before a launch, a missing bus leaves the
  job queued instead of burning the reviewed (commit, wrapper) pair.
- `submit_job.py` validates each transcript before filing it.
- The first heartbeat says `starting`.

**Quiet window (coordinator policy).** The worktree must stay at the job's commit and clean from
`submit_job.py` until the wrapper's own HEAD check has passed; for CANARY.sh, the `== canary` line in
its log. A commit or `aegis log` in that window makes the job refuse and burns the pair. So the
coordinator neither commits nor logs in the worktree until the job's wrapper log shows it has
started, and records the outcome only after the job ends.

**Policy-only.** The any-HOLD rule sees only transcripts the coordinator files; a HOLD that is never
filed is invisible to the runner. Filing every review of a job-bound commit is coordinator policy.

## r4: a persistent service with visible status (operator request, 2026-09-23)

The operator asked for something longer-lived than the transient runner, and one they could see.

**Install once, then it survives restarts.**
- From a real WSL terminal, run `sh <J>/operator/INSTALL.sh <reviewed commit>`. The installer:
  - checks that the worktree is clean at that commit and that the commit is signed by 7720D1FE;
  - copies `jobrunner.py`, `source-launch.py` and `gcjobs` out of the commit's git objects into
    read-only `~/.local/share/gas-city-jobrunner/<commit>/`, each digest-pinned;
  - stops the transient runner;
  - writes `~/.config/systemd/user/gas-city-jobrunner.service` (`Slice=app.slice`, `UMask=0022`,
    `Restart=on-failure` with `RestartSec=30`, `RestartPreventExitStatus=2 3`, enabled for
    `default.target`);
  - installs `~/.local/bin/gcjobs`;
  - runs enable --now.
- The operator has linger, so the service starts at every WSL boot. It executes the pinned copies, so
  later commits in the worktree never change the running code. Upgrading means running INSTALL.sh
  again with a new reviewed commit.
- Uninstall: `systemctl --user disable --now gas-city-jobrunner`, remove the unit file and
  `~/.local/bin/gcjobs`, then `systemctl --user daemon-reload`.

**See it.**
- `gcjobs` shows one screen: service state, runner state, PAUSE and HALTED, the queue, recent jobs with
  exit codes, and the log tail. Times are in local time.
- `journalctl --user -u gas-city-jobrunner -f` follows the live log. The runner also appends to
  `jobs/runner.log`, which is what the coordinator reads.

**Hardening from the reviews of `5cfcf172` (both SOURCE_PASS):**
- **Reviews come first.** `check_reviews()` runs before any host git call, so an unreviewed job never
  makes the runner run git in the worktree.
- **Earlier units must be finished.** Before any launch, every earlier gc-job unit must be provably
  inactive or failed. An unreadable state counts as active. Every final record stores
  `unit_state_after`.
- **Resolutions need real text.** `outcome` and `evidence` must be non-empty strings.
- **Transcripts parse strictly.** Lines split on `\n` only, and a record whose `message` is not an
  object is refused, never a crash.
- **No writing through planted links.** The heartbeat removes and recreates its temp file with
  `O_EXCL`, and the log file copy is skipped unless it is a single-link regular file. The stage
  directories must be real directories owned by the operator.
- **HOLDs can be filed.** `submit_job.py file <transcript>` files any strictly parsed review, a HOLD
  included. Coordinator policy is to file EVERY review of a job-bound commit that way.
- **The capability claim is honest now.** The runner adds no privilege the operator's pastes lacked,
  but it does remove the human step, and admission runs host git (after the reviews pass).

**Long-term replacement.** A native, supervisor-executed reviewed-operation type is tracked as ga-lzvy.
A Gas City worker builds it after the first successful worker window.

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
4. Launch `systemd-run --user --wait --collect --quiet --service-type=oneshot --unit=gc-job-<id> -p UMask=0022 -p TimeoutStartSec=infinity /bin/sh <wrapper> <commit>`.
5. Log the exit, set HALTED (after every job), and write `done/<id>.json`.

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

The runner holds no privilege the operator's pastes lacked: it runs the same kind of reviewed
wrapper, in the same namespace, the same way, one step at a time, and it halts after every job. It
differs from the pastes in two ways. It removes the human step. And it runs host git during
admission, after the reviews pass, to check HEAD, cleanliness, signature and blob.

## Operator controls

| Action | Command |
| --- | --- |
| Start (once per WSL boot) | `systemd-run --user --unit=gas-city-jobrunner --collect -p UMask=0022 sh <J>/operator/JOBRUNNER.sh <reviewed commit>` |
| Pause before the next job | `touch ~/.local/share/gas-city-staging/jobs/PAUSE` (only the operator removes it) |
| Resume | `rm ~/.local/share/gas-city-staging/jobs/PAUSE` |
| Stop the runner | `systemctl --user stop gas-city-jobrunner` (a running job keeps its own `gc-job-*` unit, and a restart waits for it to be resolved) |
| Stop a running job | `systemctl --user stop gc-job-<id>` (the oneshot unit fails, and the runner is halted after every job anyway) |
| Status | `cat ~/.local/share/gas-city-staging/jobs/state/runner.json`, `tail ~/.local/share/gas-city-staging/jobs/runner.log`, `ls ~/.local/share/gas-city-staging/jobs/done` |

`<J>` is this directory. The runner's code is fixed at start. Updating it takes a new reviewed commit
and a restart.
