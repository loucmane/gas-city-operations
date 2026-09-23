#!/bin/sh
# ga-4z38 window prep, round 1: the isolation overlay and its receipt image. Read-only: installs
# nothing, launches no worker, writes only its fresh evidence root /var/tmp/ga-4z38-prep-20260923-r1.
#
# Runs as a job of the host job runner (designs/gct-jobrunner). The runner starts it as
#   systemd-run --user --wait --collect --quiet --service-type=oneshot --unit=gc-job-<id> \
#     -p UMask=0022 -p TimeoutStartSec=infinity /bin/sh <this file> <reviewed commit>
# Log: ~/.local/share/gas-city-staging/ga-4z38-window/prep-<timestamp>.txt. Exits with the prep result.
S=/home/loucmane/.local/share/gas-city-staging/ga-4z38-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-4z38-window
COMMIT=${1:?usage: PREP.sh <reviewed commit>}
PREP_SHA=3ebf7006de0f68f7e9ee9a23292518c32a1a766b4b77174d49f80834fd43b432
OUT=/var/tmp/ga-4z38-prep-20260923-r1
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
