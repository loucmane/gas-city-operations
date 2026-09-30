#!/bin/sh
# ga-jcxb window route: one raw route of the bound task while every rig is suspended, then the
# read-only sole-task queue audit.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-jcxb-c1-package/route-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-jcxb-c1-package
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-jcxb-c1-package
COMMIT=${1:?usage: ROUTE.sh <reviewed commit>}
ROUTE_SHA=c794e417f9dbfa909f1a1d4307401dc9a5fb211e1974e3bb2f94bfbb11444f01
AUDIT_SHA=a5a8f35d1cab1370af9a4da626e64f69558867e7e45db9ab1ee4405c5cad49d3
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/route-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-jcxb-route-20260930-r1 ] && [ ! -L /var/tmp/ga-jcxb-route-20260930-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-jcxb-route-20260930-r1"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-jcxb-audit-route-20260930-r1 ] && [ ! -L /var/tmp/ga-jcxb-audit-route-20260930-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-jcxb-audit-route-20260930-r1"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== ROUTE REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step route "$C/route-task.py" "$ROUTE_SHA"
step audit-route "$C/audit-queue-r3.py" "$AUDIT_SHA" route
echo "== ROUTE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
