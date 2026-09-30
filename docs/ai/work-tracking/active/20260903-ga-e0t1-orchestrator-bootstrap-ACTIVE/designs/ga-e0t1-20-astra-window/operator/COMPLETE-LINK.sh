#!/bin/sh
# One exact append-forward completion, never replay the removed edge.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: COMPLETE-LINK.sh reviewed-commit}
STEP_SHA=a5c31038307485995ec06365d9c9391d1b70159619148bdc95db1268393c2b52
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/complete-link-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || exit 1
head=$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD) || exit 1
status=$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" status --porcelain --untracked-files=all) || exit 1
[ "$head" = "$COMMIT" ] && [ -z "$status" ] || { echo 'STOP package not clean at reviewed head'; exit 1; }
{ [ ! -e /var/tmp/ga-e0t1.20-link-completion-20260928-r2 ] && [ ! -L /var/tmp/ga-e0t1.20-link-completion-20260928-r2 ]; } || { echo 'STOP consumed root'; exit 1; }
launcher=$(sha256sum "$D/gct-m1wh-p6/source-launch.py") || exit 1
[ "${launcher%% *}" = 31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea ] || exit 1
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/complete-task-link.py" "$STEP_SHA"
rc=$?
echo "== COMPLETE-LINK exit=$rc"
echo "== end $(date -u +%Y%m%dT%H%M%SZ)"
exit "$rc"
