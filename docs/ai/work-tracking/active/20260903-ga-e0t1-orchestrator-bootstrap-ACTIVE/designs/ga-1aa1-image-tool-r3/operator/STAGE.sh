#!/bin/sh
# ga-1aa1 window stage: the single-worker overlay city and its native-finalized receipt, through
# the confined writers and one observed reload. Every rig stays suspended.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-1aa1-image-tool-r3/stage-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-1aa1-image-tool-r3
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-1aa1-image-tool-r3
COMMIT=${1:?usage: STAGE.sh <reviewed commit>}
WINDOW_SHA=1c5541b922bc2eee7b40fbb88265c83ea4cae776a1aee965f4fc7ef90aa8af7a
AUDIT_SHA=4fdbd867c34e92b6ff17b5e61c8f0e1f4146ecb35bd662740c86dd6718ed3870
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/stage-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
[ -e /var/tmp/ga-1aa1-window-20260929-r1/preflight-pass.json ] && [ ! -e /var/tmp/ga-1aa1-window-20260929-r1/stage-consumed.json ] || { echo "== STOP: window not preflighted or stage already consumed"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== STAGE REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step audit-stage "$C/audit-queue-r3.py" "$AUDIT_SHA" stage
step stage "$C/window.py" "$WINDOW_SHA" stage
echo "== STAGE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
