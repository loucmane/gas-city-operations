#!/bin/sh
# Gas City job runner. The operator decided on 2026-09-23 to automate the live pastes.
#
# Start it ONCE from a real WSL terminal. It keeps running until it is stopped or WSL restarts:
#   systemd-run --user --unit=gas-city-jobrunner --collect -p UMask=0022 sh <J>/operator/JOBRUNNER.sh <reviewed commit>
# Stop:   systemctl --user stop gas-city-jobrunner   (a job already running keeps its own gc-job-* unit)
# Pause:  touch ~/.local/share/gas-city-staging/jobs/PAUSE   (resume: rm that file)
# Status: cat ~/.local/share/gas-city-staging/jobs/state/runner.json
#         tail ~/.local/share/gas-city-staging/jobs/runner.log
S=/home/loucmane/.local/share/gas-city-staging/jobs
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
J=$D/gct-jobrunner
COMMIT=${1:?usage: JOBRUNNER.sh <reviewed commit>}
RUNNER_SHA=d55d14e685d6e475b9897f5f292700179e2fc2519c3a9e05cc4652c1a31413de
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
chmod 700 "$S"
exec >>"$S/runner.log" 2>&1 </dev/null
echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) start umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) commit=$COMMIT"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; exit 1; }
head=$(git -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: worktree head=$head not clean or not the reviewed commit"; exit 1
fi
# The P6 package's source-launch.py (31bdeea8) executes jobrunner.py only if its bytes match RUNNER_SHA.
# The running code stays fixed even when the worktree moves on to later commits.
exec /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$J/jobrunner.py" "$RUNNER_SHA"
