#!/bin/sh
# ga-gegx window stage: the single-worker overlay city and its native-finalized receipt, through
# the confined writers and one observed reload. Every rig stays suspended.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-gegx-window/stage-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-gegx-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-gegx-window
COMMIT=${1:?usage: STAGE.sh <reviewed commit>}
WINDOW_SHA=b306609639f43ec7a9da9af8825c9e7efb94d1860f52a2a9f94374340ef80451
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/stage-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
[ -e /var/tmp/ga-gegx-window-20260925-r2/preflight-pass.json ] && [ ! -e /var/tmp/ga-gegx-window-20260925-r2/stage-consumed.json ] || { echo "== STOP: window not preflighted or stage already consumed"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== STAGE REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step stage "$C/window-r11.py" "$WINDOW_SHA" stage
echo "== STAGE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
