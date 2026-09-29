#!/bin/sh
# ga-e0t1.20 window terminal: the full native integrity observation of the restored baseline,
# bound to the terminal suspension endpoint and the accepted restoration.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-e0t1-20-astra-window/terminal-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: TERMINAL.sh <reviewed commit>}
TERMINAL_SHA=575a834cde936e45b1b0a05385ce6a802cb287fad73f961746be6dec74bce90c
BUDGET_SHA=342a001025052053df743fba49609c1a204d2b30e5f0eac2b690890bde7c210d
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/terminal-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-e0t1.20-terminal-20260929-r10 ] && [ ! -L /var/tmp/ga-e0t1.20-terminal-20260929-r10 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-e0t1.20-terminal-20260929-r10"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== TERMINAL REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step budget "$C/budget-r11.py" "$BUDGET_SHA" 8
step terminal "$C/observe-terminal-r11.py" "$TERMINAL_SHA"
echo "== TERMINAL PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
