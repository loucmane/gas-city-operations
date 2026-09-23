#!/bin/sh
# gct-m1wh platform canary (ga-0t04, M5 LAYOUT.md step 7). canary-run.py does the following:
# - checks the live pins;
# - runs `gc platform canary` once for the signing profile gascity/gc.implementation-worker;
# - verifies the published receipt.
# Its only intended live writes are the two receipt files Core publishes on PASS. The nine scenarios
# run in disposable scratch cities, with no inference and no real signer.
#
# r2 runs as a job of the host job runner (designs/gct-jobrunner), which starts it as
#   systemd-run --user --wait --collect --unit=gc-job-<id> -p UMask=0022 /bin/sh <this file> <reviewed commit>
# Started by hand instead, it is:
#   systemd-run --user --unit=gct-m1wh-canary-r2 --collect -p UMask=0022 sh <C>/operator/CANARY.sh <reviewed commit>
# All output goes to canary-<timestamp>.txt in $S. When the unit ends, systemd reaps anything left
# in its cgroup.
S=/home/loucmane/.local/share/gas-city-staging/gct-m1wh-canary
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/gct-m1wh-canary
COMMIT=${1:?usage: CANARY.sh <reviewed commit>}
RUN_SHA=5cab29ad50834b1b4b2d466d804d2dce8e77901d08906310db75d8dcac470c27
PATH=/usr/local/bin:/usr/bin:/bin
export PATH XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
mkdir -p "$S" || exit 1
LOG="$S/canary-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/gct-m1wh-canary-20260923-r2 ] && [ ! -L /var/tmp/gct-m1wh-canary-20260923-r2 ]; } \
  || { echo "== STOP: evidence root already used"; echo "== end"; exit 1; }
echo "== canary $(date -u +%H:%M:%SZ)"
# The P6 package's source-launch.py (31bdeea8) runs canary-run.py only if its bytes match RUN_SHA.
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/canary-run.py" "$RUN_SHA"
rc=$?
if [ "$rc" = 0 ]; then echo "== CANARY PASS"; else echo "== CANARY NOT PASSED rc=$rc: read this log, result.json in /var/tmp/gct-m1wh-canary-20260923-r2 and the scenario evidence; run nothing else"; fi
echo "== end $(date -u +%H:%M:%SZ)"
# Exit with the canary result, so a refused canary halts the job runner instead of reading as success.
exit "$rc"
