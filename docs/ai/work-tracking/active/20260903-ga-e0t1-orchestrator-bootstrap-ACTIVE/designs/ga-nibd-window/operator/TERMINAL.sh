#!/bin/sh
# ga-nibd window terminal: the full native integrity observation of the restored baseline,
# bound to the terminal suspension endpoint and the accepted restoration.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-nibd-window/terminal-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-nibd-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-nibd-window
COMMIT=${1:?usage: TERMINAL.sh <reviewed commit>}
TERMINAL_SHA=71f50558e9f608979e7ad4ee090bc443e53079453e4bce1a8bfe42733f011d8a
BUDGET_SHA=e2ce8513728ea6850e7ce19817e656d3dc8aca84eeecb7aeca4978c06fb9bf1d
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
{ [ ! -e /var/tmp/ga-nibd-terminal-20260923-r1 ] && [ ! -L /var/tmp/ga-nibd-terminal-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-nibd-terminal-20260923-r1"; echo "== end"; exit 1; }
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
