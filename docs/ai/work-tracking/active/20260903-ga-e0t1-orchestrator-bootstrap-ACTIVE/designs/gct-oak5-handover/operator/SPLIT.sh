#!/bin/sh
# gct-oak5 split package: close the stale workflow gct-wn1m and create the handover step Beads
# (split/apply_split.py). Runs as a job of the host job runner (designs/gct-jobrunner).
# Log: ~/.local/share/gas-city-staging/gct-oak5-handover/split-<timestamp>.txt; evidence and
# record.json in the stage directory named below. Exits with the script's result, or 1 on a refused
# precondition.
S=/home/loucmane/.local/share/gas-city-staging/gct-oak5-handover
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/gct-oak5-handover/split
STAGE=$S/split-r2
COMMIT=${1:?usage: SPLIT.sh <reviewed commit>}
APPLY_SHA=e9ca41f4ad7867280ed177bee65e0f6883e61d01588453d42faa47104b6616f7
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/split-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$STAGE" ] && [ ! -L "$STAGE" ]; } || { echo "== STOP: stage already used: $STAGE"; echo "== end"; exit 1; }
echo "== split $(date -u +%H:%M:%SZ)"
/usr/bin/python3.12 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/apply_split.py" "$APPLY_SHA" "$STAGE"
rc=$?
echo "== split rc=$rc"
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
