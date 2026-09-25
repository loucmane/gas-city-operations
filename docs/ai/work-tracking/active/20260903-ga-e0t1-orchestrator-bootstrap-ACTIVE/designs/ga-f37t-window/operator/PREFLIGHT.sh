#!/bin/sh
# ga-f37t window preflight: read-only admission of the window against the fresh integrity
# observation (OBSERVE.sh). It creates the window root and stages nothing.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-f37t-window/preflight-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-f37t-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-f37t-window
COMMIT=${1:?usage: PREFLIGHT.sh <reviewed commit>}
WINDOW_SHA=25561ceaf2333f831067773dbd7c0f4a1d2edb31aafffc9d50b0e6ac33b016ec
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/preflight-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-f37t-window-20260925-r2 ] && [ ! -L /var/tmp/ga-f37t-window-20260925-r2 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-f37t-window-20260925-r2"; echo "== end"; exit 1; }
# s5: the window accounts read-only access-time changes (window-base account_read_times), so no
# FRESHEN pass is required before PREFLIGHT.
tmux_out=$(/usr/bin/env -u TMUX_TMPDIR -u TMUX /usr/bin/tmux -u -L city list-sessions -F "#{session_name}" 2>&1); tmux_rc=$?
tmux_sock=/tmp/tmux-$(id -u)/city
if [ "$tmux_rc" = 0 ]; then
  echo "== STOP: a city tmux server is already running"; echo "== end"; exit 1
elif [ ! -e "$tmux_sock" ] && [ ! -L "$tmux_sock" ]; then
  case "$tmux_out" in
    *"error connecting to "*"(No such file or directory)"*) echo "== tmux gate: no city socket" ;;
    *) echo "== STOP: unrecognised city tmux answer"; echo "== end"; exit 1 ;;
  esac
elif [ -S "$tmux_sock" ] && [ ! -L "$tmux_sock" ] && [ "$(stat -c %u "$tmux_sock")" = "$(id -u)" ]; then
  case "$tmux_out" in
    *"no server running on "*) echo "== tmux gate: stale city socket, no server" ;;
    *) echo "== STOP: unrecognised city tmux answer"; echo "== end"; exit 1 ;;
  esac
else
  echo "== STOP: the city tmux socket path is not a stale socket of this user"; echo "== end"; exit 1
fi
work=/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles
for proc in /proc/[0-9]*; do
  [ -O "$proc" ] && [ "${proc#/proc/}" != "$$" ] || continue
  cwd=$(readlink "$proc/cwd" 2>/dev/null) || cwd=
  named=
  case "$cwd" in "$work"|"$work"/*) named=cwd ;; esac
  [ -n "$named" ] || { tr "\000" "\n" < "$proc/cmdline" 2>/dev/null | grep -qF -- "$work" && named=argv; }
  if [ -n "$named" ]; then
    echo "== STOP: process ${proc#/proc/} names the Core worktree ($named)"; echo "== end"; exit 1
  fi
done
echo "== worktree gate: no process names the Core worktree"
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== PREFLIGHT REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step preflight "$C/window-r11.py" "$WINDOW_SHA" preflight
echo "== PREFLIGHT PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
