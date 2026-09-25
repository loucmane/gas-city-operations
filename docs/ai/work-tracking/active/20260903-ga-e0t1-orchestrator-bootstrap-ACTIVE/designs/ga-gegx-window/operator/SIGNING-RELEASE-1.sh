#!/bin/sh
# ga-gegx window signing release: validate the coordinator signing release against the live
# worker session and the staged index, post it once, read it back and nudge.
# Repeatable: a run after the post only verifies and nudges again.
# Slot 1 of 3: the job runner starts each wrapper path once per commit.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-gegx-window/signing-release-1-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-gegx-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-gegx-window
COMMIT=${1:?usage: SIGNING-RELEASE-1.sh <reviewed commit>}
RELEASE_SHA=2ef90e68a3a907bb8978748f4f3eec65a24941e61dfda5653bf766de368e1141
BUDGET_SHA=0a749a0355b1ed7a1150031323d7f0f392e69417f30d5ed0f02892ca7887a578
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/signing-release-1-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
[ -e /var/tmp/ga-gegx-source-release.posted ] || { echo "== STOP: no source release posted"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== SIGNING-RELEASE-1 REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step budget "$C/budget-r11.py" "$BUDGET_SHA" 85
step signing-release "$C/release-r11.py" "$RELEASE_SHA" signing
echo "== SIGNING-RELEASE-1 PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
