#!/bin/sh
# ga-mb91 window contain: hold scheduling. city-suspend (only if the city was resumed), then
# rig-suspend, once each, through the reviewed lifecycle.
# Slot 2 of 2: the job runner starts each wrapper path once per commit.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-mb91-c1-package/contain-2-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-mb91-c1-package
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-mb91-c1-package
COMMIT=${1:?usage: CONTAIN-2.sh <reviewed commit>}
WINDOW_SHA=d203fb72d696ff97fe85c72104fa61edee1a0f7eebd046e14d2c81bd932fc3c4
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/contain-2-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
[ -e /var/tmp/ga-mb91-window-20260930-r2/stage-pass.json ] || { echo "== STOP: no staged window"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== CONTAIN-2 REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
if [ -e /var/tmp/ga-mb91-window-20260930-r2/suspension-city-resume-event.json ] && [ ! -e /var/tmp/ga-mb91-window-20260930-r2/suspension-city-suspend-event.json ]; then
  step city-suspend "$C/window.py" "$WINDOW_SHA" lifecycle city-suspend
fi
if [ -e /var/tmp/ga-mb91-window-20260930-r2/suspension-rig-resume-event.json ] && [ ! -e /var/tmp/ga-mb91-window-20260930-r2/suspension-rig-suspend-event.json ]; then
  step rig-suspend "$C/window.py" "$WINDOW_SHA" lifecycle rig-suspend
fi
echo "== CONTAIN-2 PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
