#!/bin/sh
# gct-oak5 handover inventory probes A and B (Claude lane, declared lower bound; see probe/probe_ab.py).
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# One Claude print-mode session in a GitHub clone's scratch linked worktree; nothing touches the
# canonical Template, the live city or any Bead store.
# Log: ~/.local/share/gas-city-staging/gct-oak5-handover/probe-ab-<timestamp>.txt; evidence in the
# stage directory named below. Exits with the probe's result, or 1 on a refused precondition.
S=/home/loucmane/.local/share/gas-city-staging/gct-oak5-handover
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/gct-oak5-handover/probe
STAGE=$S/probe-ab-r2
COMMIT=${1:?usage: PROBE-AB.sh <reviewed commit>}
PROBE_SHA=95c6b1751542363597029006e04a488429076dd6eeb65621fb070882138829da
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/probe-ab-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$STAGE" ] && [ ! -L "$STAGE" ]; } || { echo "== STOP: stage already used: $STAGE"; echo "== end"; exit 1; }
echo "== probe $(date -u +%H:%M:%SZ)"
/usr/bin/python3.12 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/probe_ab.py" "$PROBE_SHA" "$STAGE"
rc=$?
echo "== probe rc=$rc"
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
