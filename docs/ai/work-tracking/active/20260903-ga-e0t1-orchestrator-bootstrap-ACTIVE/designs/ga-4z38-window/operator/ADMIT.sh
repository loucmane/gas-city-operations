#!/bin/sh
# ga-4z38 window admit: the read-only restore admission (full preservation check, terminal lifecycle,
# quiescent host) after CONTAIN and the session close. RESTORE.sh requires its pass.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-4z38-window/admit-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-4z38-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-4z38-window
COMMIT=${1:?usage: ADMIT.sh <reviewed commit>}
ADMIT_SHA=80f453e582dcff4a63d3734c55dcacd65114c0b19e6cb73d38b8f371d624067e
BUDGET_SHA=f987f8c36b6fd7639c739c06bbffb223105a25814841f2518559fa1045fc8dd0
CLOSE_SHA=6ba2034247007f223d30c92bf2aea36a66742d746bdb8aa16203d92bca42bb4f
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
[ -e /var/tmp/ga-4z38-window-20260923-r1/stage-consumed.json ] && [ ! -e /var/tmp/ga-4z38-window-20260923-r1/restore-consumed.json ] || { echo "== STOP: no owned window or restore already consumed"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-4z38-window-20260923-r1/restore-admission.json ] && [ ! -L /var/tmp/ga-4z38-window-20260923-r1/restore-admission.json ]; } || { echo "== STOP: output root already used: /var/tmp/ga-4z38-window-20260923-r1/restore-admission.json"; echo "== end"; exit 1; }
find /var/tmp -maxdepth 2 -user 1000 -path "/var/tmp/ga-4z38-close-*/result.json" -exec grep -l '"ok": true' {} + | xargs -r grep -l "$CLOSE_SHA" | grep -q . || { echo "== STOP: CLOSE has not passed"; echo "== end"; exit 1; }
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
