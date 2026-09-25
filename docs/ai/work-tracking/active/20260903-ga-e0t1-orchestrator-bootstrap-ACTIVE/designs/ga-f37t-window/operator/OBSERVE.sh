#!/bin/sh
# ga-f37t window observe: the fresh accepted-state admission plus a full native integrity read,
# immediately before PREFLIGHT.sh. It writes only its root and the log, installs nothing
# and launches no worker. Outside the read-only sandbox it runs gc status, gc session
# list and the provisioner go-version probe; the pinned inspector runs in read-only bwrap.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-f37t-window/observe-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-f37t-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-f37t-window
COMMIT=${1:?usage: OBSERVE.sh <reviewed commit>}
OBSERVE_SHA=c1fa4f27f9c1c4e83f5842e2c34c29cd4a0f579f0e09399a916f905cea22abfa
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/observe-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-f37t-integrity-20260925-r5 ] && [ ! -L /var/tmp/ga-f37t-integrity-20260925-r5 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-f37t-integrity-20260925-r5"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== OBSERVE REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step observe "$C/observe-integrity-r11.py" "$OBSERVE_SHA"
echo "== OBSERVE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
