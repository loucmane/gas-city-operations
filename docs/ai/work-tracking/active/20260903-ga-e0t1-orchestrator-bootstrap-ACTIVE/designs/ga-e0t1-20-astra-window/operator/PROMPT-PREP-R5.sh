#!/bin/sh
echo "COMPLETED PREPARATION - replay prohibited" >&2
exit 125
# R5 PROMPT PREP: read-only host observation and uninstalled image. No worker launch.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: PROMPT-PREP-R5.sh <reviewed commit>}
PREP_SHA=bbb119c111d0675688d58e295ab20387f79b801403b8331b0f2137ed5acb7acd
OUT=/var/tmp/ga-e0t1.20-prompt-prep-20260928-r5
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/prompt-prep-r5-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$OUT" ] && [ ! -L "$OUT" ]; } || { echo "== STOP: evidence root already used: $OUT"; echo "== end"; exit 1; }
echo "== prep $(date -u +%H:%M:%SZ)"
# The P6 package's source-launch.py (31bdeea8) runs prepare.py only if its bytes match PREP_SHA.
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/prompt-prep-r5.py" "$PREP_SHA"
rc=$?
if [ "$rc" = 0 ]; then echo "== PREP PASS"; else echo "== PREP REFUSED rc=$rc: read this log and $OUT; run nothing else"; fi
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
