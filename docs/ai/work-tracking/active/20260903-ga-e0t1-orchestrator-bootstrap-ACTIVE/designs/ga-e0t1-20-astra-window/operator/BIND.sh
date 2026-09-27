#!/bin/sh
# ga-e0t1.20 window bind: the one ga-e0t1.20 contract binding (gc.work_dir only), before the window.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-e0t1-20-astra-window/bind-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: BIND.sh <reviewed commit>}
STEP_SHA=1496103fb888d7ac5df1686a5f510dddd47e67d000fd5b483452716c84b7ec35
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/bind-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-e0t1.20-bind-20260927-r1 ] && [ ! -L /var/tmp/ga-e0t1.20-bind-20260927-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-e0t1.20-bind-20260927-r1"; echo "== end"; exit 1; }
echo "== bind $(date -u +%H:%M:%SZ)"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/bind-task-r5.py" "$STEP_SHA"
rc=$?
if [ "$rc" != 0 ]; then
  echo "== BIND REFUSED rc=$rc: read this log and /var/tmp/ga-e0t1.20-bind-20260927-r1 before any further step"
  echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
fi
echo "== BIND PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
