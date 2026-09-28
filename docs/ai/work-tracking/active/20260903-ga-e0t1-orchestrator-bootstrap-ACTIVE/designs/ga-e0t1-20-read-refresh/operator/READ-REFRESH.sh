#!/bin/sh
# Reviewed host-runner operator job. Ordinary reads, no timestamp-setting operation.
# This does not admit a worker or substitute for OBSERVE and full PREFLIGHT.
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-read-refresh
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-read-refresh
COMMIT=${1:?usage: READ-REFRESH.sh reviewed-commit}
REFRESH_SHA=b81fb7fab8a7bb8ef0d176d176f5946a304bdd50aeb51399bec88f6416fc9c70
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
[ "$#" = 1 ] || exit 1
[ "$(umask)" = 0022 ] || exit 1
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/read-refresh-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
head=$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "STOP package head or cleanliness mismatch"
  exit 1
fi
echo "BEGIN read refresh $(date -u +%Y%m%dT%H%M%SZ) worker_release=false"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/refresh.py" "$REFRESH_SHA"
rc=$?
echo "END read refresh rc=$rc worker_release=false"
exit "$rc"
