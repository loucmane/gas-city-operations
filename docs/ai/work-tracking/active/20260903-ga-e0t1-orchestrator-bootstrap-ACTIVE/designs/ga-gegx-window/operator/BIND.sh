#!/bin/sh
# ga-gegx window bind: the one supported ga-gegx contract/enrollment patch, before the window.
# It appends the reviewed worker brief and the requested native attempt metadata to
# ga-gegx. It never routes, resumes or launches a worker.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-gegx-window/bind-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-gegx-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-gegx-window
COMMIT=${1:?usage: BIND.sh <reviewed commit>}
BIND_SHA=c7d561516dfde7fa246e46a0040ffd3d90b2fc0d49f924be87ab141a88ada003
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
{ [ ! -e /var/tmp/ga-gegx-bind-20260923-r1 ] && [ ! -L /var/tmp/ga-gegx-bind-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-gegx-bind-20260923-r1"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-gegx-window-20260925-r2 ] && [ ! -L /var/tmp/ga-gegx-window-20260925-r2 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-gegx-window-20260925-r2"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== BIND REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step bind "$C/bind-task-r3.py" "$BIND_SHA"
echo "== BIND PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
