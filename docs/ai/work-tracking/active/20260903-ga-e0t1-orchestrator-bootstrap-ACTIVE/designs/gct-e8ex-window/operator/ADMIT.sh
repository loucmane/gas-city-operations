#!/bin/sh
# gct-mbg6 window admit: the read-only restore admission (full preservation check, terminal lifecycle,
# quiescent host) after CONTAIN and the session close. RESTORE.sh requires its pass.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/gct-e8ex-window/admit-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/gct-e8ex-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/gct-mbg6-window
COMMIT=${1:?usage: ADMIT.sh <reviewed commit>}
ADMIT_SHA=be07f5ab9dcd9b934d88ba5dd8b5b66dde87959708d850dbe14698b660ab5ded
BUDGET_SHA=b4ca4dc896dd138d15433574cdaba7faf101fc27ef47344f854137b399628d96
CLOSE_SHA=a4bfc5c977d70273f1b7f3bfc4982f75587f02b645f95bfd01f0e2836f08f191
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
[ -e /var/tmp/gct-mbg6-window-20260926-r1/stage-consumed.json ] && [ ! -e /var/tmp/gct-mbg6-window-20260926-r1/restore-consumed.json ] || { echo "== STOP: no owned window or restore already consumed"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/gct-mbg6-window-20260926-r1/restore-admission.json ] && [ ! -L /var/tmp/gct-mbg6-window-20260926-r1/restore-admission.json ]; } || { echo "== STOP: output root already used: /var/tmp/gct-mbg6-window-20260926-r1/restore-admission.json"; echo "== end"; exit 1; }
find /var/tmp -maxdepth 2 -user 1000 -path "/var/tmp/gct-mbg6-close-*/result.json" -exec grep -l '"ok": true' {} + | xargs -r grep -l "$CLOSE_SHA" | grep -q . || { echo "== STOP: CLOSE has not passed"; echo "== end"; exit 1; }
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
step budget "$C/budget-r11.py" "$BUDGET_SHA" 60
step admit "$C/restore-admission-r3.py" "$ADMIT_SHA"
echo "== ADMIT PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
