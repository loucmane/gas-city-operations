#!/bin/sh
# One reviewed ledger relationship correction. No route, resume, or worker.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: RECONCILE-LINK.sh reviewed-commit}
STEP_SHA=730e46cab83f4314cdd0972fbf4b0dab2c4b8c90f4e5c2bccf35267a4ad14254
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/reconcile-link-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || exit 1
head=$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD) || exit 1
status=$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" status --porcelain --untracked-files=all) || exit 1
[ "$head" = "$COMMIT" ] && [ -z "$status" ] || { echo 'STOP package not clean at reviewed head'; exit 1; }
{ [ ! -e /var/tmp/ga-e0t1.20-link-reconciliation-20260928-r1 ] && [ ! -L /var/tmp/ga-e0t1.20-link-reconciliation-20260928-r1 ]; } || { echo 'STOP consumed root'; exit 1; }
launcher=$(sha256sum "$D/gct-m1wh-p6/source-launch.py") || exit 1
[ "${launcher%% *}" = 31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea ] || exit 1
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/reconcile-task-link.py" "$STEP_SHA"
rc=$?
echo "== RECONCILE-LINK exit=$rc"
echo "== end $(date -u +%Y%m%dT%H%M%SZ)"
exit "$rc"
