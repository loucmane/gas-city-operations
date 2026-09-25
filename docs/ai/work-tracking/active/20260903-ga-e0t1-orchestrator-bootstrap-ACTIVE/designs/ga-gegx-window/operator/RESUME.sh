#!/bin/sh
# ga-gegx window resume: rig-resume, the read-only queue audit, then city-resume, once each.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-gegx-window/resume-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-gegx-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-gegx-window
COMMIT=${1:?usage: RESUME.sh <reviewed commit>}
WINDOW_SHA=b306609639f43ec7a9da9af8825c9e7efb94d1860f52a2a9f94374340ef80451
AUDIT_SHA=2df5ba8d9a4769c0b185a84e43a919a5bcc84ab1b446afb2b97c4f721a84e5c8
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
[ -e /var/tmp/ga-gegx-route-20260923-r1/result.json ] && [ -e /var/tmp/ga-gegx-audit-route-20260923-r1/result.json ] || { echo "== STOP: ROUTE has not passed"; echo "== end"; exit 1; }
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
work=/home/loucmane/gascity-core-worktrees/ga-gegx-typed-route-cycles
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
{ [ ! -e /var/tmp/ga-gegx-audit-resume-20260923-r1 ] && [ ! -L /var/tmp/ga-gegx-audit-resume-20260923-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-gegx-audit-resume-20260923-r1"; echo "== end"; exit 1; }
{ [ ! -e /var/tmp/ga-gegx-window-20260925-r2/rig-resume-started.json ] && [ ! -L /var/tmp/ga-gegx-window-20260925-r2/rig-resume-started.json ]; } || { echo "== STOP: output root already used: /var/tmp/ga-gegx-window-20260925-r2/rig-resume-started.json"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== RESUME REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step rig-resume "$C/window-r11.py" "$WINDOW_SHA" lifecycle rig-resume
step audit-resume "$C/audit-queue-r3.py" "$AUDIT_SHA" resume
step city-resume "$C/window-r11.py" "$WINDOW_SHA" lifecycle city-resume
echo "== RESUME PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
