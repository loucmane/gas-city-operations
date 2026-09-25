#!/bin/sh
# ga-f37t window prep r3: the isolation overlay and its receipt image. Read-only: installs nothing
# and launches no worker. It writes its fresh evidence root /var/tmp/ga-f37t-prep-20260923-r2 plus the
# staging log below. It is the reviewed ga-f37t prep r3 rebound to ga-f37t; the r1 refusal and the r2
# HOLD belong to the ga-f37t jobs, and the -r2 root name is inherited from them.
#
# Runs as a job of the host job runner (designs/gct-jobrunner). The runner starts it as
#   systemd-run --user --wait --collect --quiet --service-type=oneshot --unit=gc-job-<id> \
#     -p UMask=0022 -p TimeoutStartSec=infinity /bin/sh <this file> <reviewed commit>
# Log: ~/.local/share/gas-city-staging/ga-f37t-window/prep-<timestamp>.txt. Exits with the prep result.
S=/home/loucmane/.local/share/gas-city-staging/ga-f37t-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-f37t-window
COMMIT=${1:?usage: PREP.sh <reviewed commit>}
PREP_SHA=234aa6fe555c9f2e5b2d2e74c7c25cde2db75f942f142d64723c10c145907a6a
OUT=/var/tmp/ga-f37t-prep-20260923-r2
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/prep-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$OUT" ] && [ ! -L "$OUT" ]; } || { echo "== STOP: evidence root already used: $OUT"; echo "== end"; exit 1; }
echo "== prep $(date -u +%H:%M:%SZ)"
# The P6 package's source-launch.py (31bdeea8) runs prep-r11.py only if its bytes match PREP_SHA.
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/prep-r11.py" "$PREP_SHA"
rc=$?
if [ "$rc" = 0 ]; then echo "== PREP PASS"; else echo "== PREP REFUSED rc=$rc: read this log and $OUT; run nothing else"; fi
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
