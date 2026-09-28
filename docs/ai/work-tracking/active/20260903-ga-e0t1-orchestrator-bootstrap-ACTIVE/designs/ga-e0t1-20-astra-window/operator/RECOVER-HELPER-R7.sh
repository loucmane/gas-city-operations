#!/bin/sh
# Exact archival recovery only. Does not admit or retry a worker window.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: RECOVER-HELPER-R7.sh reviewed-commit}
EXECUTOR_SHA=63c03b7ce73f5e467f3a0b5a7148050421daab72855739f0fd9a6d5ed00deb4a
OUT=/var/tmp/ga-e0t1.20-helper-archive-20260928-r1
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
[ -d "$S" ] && [ ! -L "$S" ] || exit 1
LOG="$S/helper-recovery-r7-$(date -u +%Y%m%dT%H%M%SZ).txt"
set -C
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP wrong umask"; exit 1; }
head=$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD) || exit 1
status=$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" status --porcelain --untracked-files=all) || exit 1
[ "$head" = "$COMMIT" ] && [ -z "$status" ] || { echo "== STOP candidate drift"; exit 1; }
{ [ ! -e "$OUT" ] && [ ! -L "$OUT" ]; } || { echo "== STOP consumed recovery root"; exit 1; }
launch_sha=$(sha256sum "$D/gct-m1wh-p6/source-launch.py") || exit 1
[ "${launch_sha%% *}" = 31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea ] || exit 1
echo "== recovery $(date -u +%H:%M:%SZ)"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/generators/helper_recovery.py" "$EXECUTOR_SHA" apply
rc=$?
if [ "$rc" = 0 ]; then echo "== EXACT ARCHIVE PASS no worker launched"; else echo "== RECOVERY HOLD rc=$rc no retry"; fi
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
