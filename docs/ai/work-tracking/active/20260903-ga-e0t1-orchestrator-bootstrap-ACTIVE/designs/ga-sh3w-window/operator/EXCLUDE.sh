#!/bin/sh
# ga-sh3w window exclude: ignore Core-materialized Claude skill links in Operations worktrees.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-sh3w-window/exclude-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-sh3w-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-sh3w-window
COMMIT=${1:?usage: EXCLUDE.sh <reviewed commit>}
STEP_SHA=e66ce751726a371cf144c4862bf7a7240987a77e83db7bff93e5bb6faf682ab9
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/exclude-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-sh3w-exclude-20260926-r1 ] && [ ! -L /var/tmp/ga-sh3w-exclude-20260926-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-sh3w-exclude-20260926-r1"; echo "== end"; exit 1; }
echo "== exclude $(date -u +%H:%M:%SZ)"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/exclude-task-r1.py" "$STEP_SHA"
rc=$?
if [ "$rc" != 0 ]; then
  echo "== EXCLUDE REFUSED rc=$rc: read this log and /var/tmp/ga-sh3w-exclude-20260926-r1 before any further step"
  echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
fi
echo "== EXCLUDE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
