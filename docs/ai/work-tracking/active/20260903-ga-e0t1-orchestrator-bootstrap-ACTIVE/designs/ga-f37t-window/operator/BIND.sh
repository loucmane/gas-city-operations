#!/bin/sh
# ga-f37t window bind: the one supported ga-f37t contract/enrollment patch, before the window.
# It appends the reviewed worker brief and the requested native attempt metadata to
# ga-f37t. It never routes, resumes or launches a worker.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-f37t-window/bind-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-f37t-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-f37t-window
COMMIT=${1:?usage: BIND.sh <reviewed commit>}
BIND_SHA=159452692546d4d08512d2b1a11a2b479bc1438e40e83fe009d05427a110417a
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
{ [ ! -e /var/tmp/ga-f37t-bind-20260923-r1 ] && [ ! -L /var/tmp/ga-f37t-bind-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-f37t-bind-20260923-r1"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-f37t-window-20260923-r1 ] && [ ! -L /var/tmp/ga-f37t-window-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-f37t-window-20260923-r1"; echo "== end"; exit 1; }
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
