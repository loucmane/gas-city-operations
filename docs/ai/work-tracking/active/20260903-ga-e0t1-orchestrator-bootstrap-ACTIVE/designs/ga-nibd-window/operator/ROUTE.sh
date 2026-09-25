#!/bin/sh
# ga-nibd window route: one raw route of the bound task while every rig is suspended, then the
# read-only sole-task queue audit.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-nibd-window/route-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-nibd-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-nibd-window
COMMIT=${1:?usage: ROUTE.sh <reviewed commit>}
ROUTE_SHA=629fb08ffbdd36476138160758d27d0ddb762a8313a67725109b0ae22936137a
AUDIT_SHA=dad3e007383700ca84c881ae8f4f2fd719ad69bc42155ddca70f41261f3b9254
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
{ [ ! -e /var/tmp/ga-nibd-route-20260923-r1 ] && [ ! -L /var/tmp/ga-nibd-route-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-nibd-route-20260923-r1"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-nibd-audit-route-20260923-r1 ] && [ ! -L /var/tmp/ga-nibd-audit-route-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-nibd-audit-route-20260923-r1"; echo "== end"; exit 1; }
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
step route "$C/route-task-r5.py" "$ROUTE_SHA"
step audit-route "$C/audit-queue-r3.py" "$AUDIT_SHA" route
echo "== ROUTE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
