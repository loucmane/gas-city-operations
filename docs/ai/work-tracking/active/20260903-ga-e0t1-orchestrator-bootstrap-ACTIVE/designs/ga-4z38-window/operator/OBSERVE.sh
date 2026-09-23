#!/bin/sh
# ga-4z38 window round 2a: fresh accepted-state admission plus a full native integrity read. Read-only:
# installs nothing, launches no worker. It writes its fresh evidence root
# /var/tmp/ga-4z38-integrity-20260923-r1 plus the staging log below.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-4z38-window/observe-<timestamp>.txt. Exits with the observer
# result.
S=/home/loucmane/.local/share/gas-city-staging/ga-4z38-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-4z38-window
COMMIT=${1:?usage: OBSERVE.sh <reviewed commit>}
OBSERVE_SHA=305efd6e276062a7a7095c3f055d027c1a9665f3668cdfd603b3f36e5009904d
OUT=/var/tmp/ga-4z38-integrity-20260923-r1
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/observe-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$OUT" ] && [ ! -L "$OUT" ]; } || { echo "== STOP: evidence root already used: $OUT"; echo "== end"; exit 1; }
echo "== observe $(date -u +%H:%M:%SZ)"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/observe-integrity-r11.py" "$OBSERVE_SHA"
rc=$?
if [ "$rc" = 0 ]; then echo "== OBSERVE PASS"; else echo "== OBSERVE REFUSED rc=$rc: read this log and $OUT; run nothing else"; fi
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
