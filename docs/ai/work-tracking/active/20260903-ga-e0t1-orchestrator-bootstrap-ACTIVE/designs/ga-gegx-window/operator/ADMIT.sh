#!/bin/sh
# ga-gegx window admit: the read-only restore admission (full preservation check, terminal lifecycle,
# quiescent host) after CONTAIN and the session close. RESTORE.sh requires its pass.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-gegx-window/admit-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-gegx-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-gegx-window
COMMIT=${1:?usage: ADMIT.sh <reviewed commit>}
ADMIT_SHA=217927a83697b5d00f62082a90c67fa48c323494b8eed8b2d68296a59e60073d
BUDGET_SHA=0a749a0355b1ed7a1150031323d7f0f392e69417f30d5ed0f02892ca7887a578
CLOSE_SHA=0c23bb5eb56b7347da2c48162a87f88f8f498316cce61c613d1aaaa6b5a1c7be
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/admit-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
[ -e /var/tmp/ga-gegx-window-20260925-r2/stage-consumed.json ] && [ ! -e /var/tmp/ga-gegx-window-20260925-r2/restore-consumed.json ] || { echo "== STOP: no owned window or restore already consumed"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-gegx-window-20260925-r2/restore-admission.json ] && [ ! -L /var/tmp/ga-gegx-window-20260925-r2/restore-admission.json ]; } || { echo "== STOP: output root already used: /var/tmp/ga-gegx-window-20260925-r2/restore-admission.json"; echo "== end"; exit 1; }
find /var/tmp -maxdepth 2 -user 1000 -path "/var/tmp/ga-gegx-close-*/result.json" -exec grep -l '"ok": true' {} + | xargs -r grep -l "$CLOSE_SHA" | grep -q . || { echo "== STOP: CLOSE has not passed"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== ADMIT REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step budget "$C/budget-r11.py" "$BUDGET_SHA" 40
step admit "$C/restore-admission-r3.py" "$ADMIT_SHA"
echo "== ADMIT PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
