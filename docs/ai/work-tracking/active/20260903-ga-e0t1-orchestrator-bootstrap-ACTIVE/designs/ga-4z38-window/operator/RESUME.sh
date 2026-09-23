#!/bin/sh
# ga-4z38 window resume: rig-resume, the read-only queue audit, then city-resume, once each.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-4z38-window/resume-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-4z38-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-4z38-window
COMMIT=${1:?usage: RESUME.sh <reviewed commit>}
WINDOW_SHA=1accf5c9859cc57dc7e7a5ded83cdf1218c2a1f043de0294ba15042d67168f4f
AUDIT_SHA=1fe311cbb51f0858daca941ee9b811e67152ab85fab9073e3f74e7f8ab20761c
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/resume-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-4z38-audit-resume-20260923-r1 ] && [ ! -L /var/tmp/ga-4z38-audit-resume-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-4z38-audit-resume-20260923-r1"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-4z38-window-20260923-r1/rig-resume-started.json ] && [ ! -L /var/tmp/ga-4z38-window-20260923-r1/rig-resume-started.json ]; } || { echo "== STOP: output root already used: /var/tmp/ga-4z38-window-20260923-r1/rig-resume-started.json"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== RESUME REFUSED at $label rc=$rc: read this log and the named roots; run nothing else"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step rig-resume "$C/window-r11.py" "$WINDOW_SHA" lifecycle rig-resume
step audit-resume "$C/audit-queue-r3.py" "$AUDIT_SHA" resume
step city-resume "$C/window-r11.py" "$WINDOW_SHA" lifecycle city-resume
echo "== RESUME PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
