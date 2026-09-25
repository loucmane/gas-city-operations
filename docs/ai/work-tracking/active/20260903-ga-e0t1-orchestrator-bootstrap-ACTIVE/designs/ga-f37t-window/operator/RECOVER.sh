#!/bin/sh
# ga-f37t s6 recovery: return the city to its accepted image after the refused s5 r5 STAGE (city.toml
# restored, reload). Once; never writes the receipt, the suspension state or a Bead (the controller
# regenerates the route files after the city write; their content is checked unchanged).
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-f37t-window/recover-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-f37t-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-f37t-window
COMMIT=${1:?usage: RECOVER.sh <reviewed commit>}
RECOVER_SHA=94c4bf6fd68c76743574f90a5f5fa9a4c3d88bb44e76f64f61d4f029aaadab0d
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/recover-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-f37t-recover-20260925-r1 ] && [ ! -L /var/tmp/ga-f37t-recover-20260925-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-f37t-recover-20260925-r1"; echo "== end"; exit 1; }
[ -f /var/tmp/ga-f37t-window-20260923-r1/stage-refused.json ] || { echo "== STOP: no refused STAGE to recover"; echo "== end"; exit 1; }
tmux_out=$(/usr/bin/env -u TMUX_TMPDIR -u TMUX /usr/bin/tmux -u -L city list-sessions -F "#{session_name}" 2>&1); tmux_rc=$?
if [ "$tmux_rc" = 0 ]; then
  echo "== STOP: a city tmux server is running"; echo "== end"; exit 1
fi
case "$tmux_out" in
  *"no server running on "*|*"error connecting to "*"(No such file or directory)"*) echo "== tmux gate: no city server" ;;
  *) echo "== STOP: unrecognised city tmux answer"; echo "== end"; exit 1 ;;
esac
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== RECOVER REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step recover "$C/recover-stage-r1.py" "$RECOVER_SHA"
echo "== RECOVER PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
