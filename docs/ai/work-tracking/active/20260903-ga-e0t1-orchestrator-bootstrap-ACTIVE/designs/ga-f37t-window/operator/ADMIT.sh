#!/bin/sh
# ga-f37t window admit: the read-only restore admission (full preservation check, terminal lifecycle,
# quiescent host) after CONTAIN and the session close. RESTORE.sh requires its pass.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-f37t-window/admit-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-f37t-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-f37t-window
COMMIT=${1:?usage: ADMIT.sh <reviewed commit>}
ADMIT_SHA=4a206c15652f6b6acc19af33ba97ec117573ec98c9a2feba4e5c3b508a7fabdf
BUDGET_SHA=2a54e840fd644dd56b65bb695a58f498a40412dd15d29234f62d66aa57d5b3e8
CLOSE_SHA=df8e0413fd810512daf533a394c382f7a82e32a2e0507cc2c6c971bac0d10740
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
[ -e /var/tmp/ga-f37t-window-20260925-r2/stage-consumed.json ] && [ ! -e /var/tmp/ga-f37t-window-20260925-r2/restore-consumed.json ] || { echo "== STOP: no owned window or restore already consumed"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-f37t-window-20260925-r2/restore-admission.json ] && [ ! -L /var/tmp/ga-f37t-window-20260925-r2/restore-admission.json ]; } || { echo "== STOP: output root already used: /var/tmp/ga-f37t-window-20260925-r2/restore-admission.json"; echo "== end"; exit 1; }
find /var/tmp -maxdepth 2 -user 1000 -path "/var/tmp/ga-f37t-close-*/result.json" -exec grep -l '"ok": true' {} + | xargs -r grep -l "$CLOSE_SHA" | grep -q . || { echo "== STOP: CLOSE has not passed"; echo "== end"; exit 1; }
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
