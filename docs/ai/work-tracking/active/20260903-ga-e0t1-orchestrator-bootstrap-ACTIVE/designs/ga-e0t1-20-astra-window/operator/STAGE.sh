#!/bin/sh
# ga-e0t1.20 window stage: the single-worker overlay city and its native-finalized receipt, through
# the confined writers and one observed reload. Every rig stays suspended.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-e0t1-20-astra-window/stage-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: STAGE.sh <reviewed commit>}
WINDOW_SHA=08fac369eb12ccd88d58ada8cd58c282e4f5f311a28dc5a3f9f024f713c1a413
AUDIT_SHA=7da24bf769f96d77f6400e861c38e5a6c1324a47955402ecce7acf030f36d7fd
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
[ -e /var/tmp/ga-e0t1.20-window-20260929-r9/preflight-pass.json ] && [ ! -e /var/tmp/ga-e0t1.20-window-20260929-r9/stage-consumed.json ] || { echo "== STOP: window not preflighted or stage already consumed"; echo "== end"; exit 1; }
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
step audit-route "$C/audit-queue-r3.py" "$AUDIT_SHA" route
step stage "$C/window-r11.py" "$WINDOW_SHA" stage
echo "== STAGE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
