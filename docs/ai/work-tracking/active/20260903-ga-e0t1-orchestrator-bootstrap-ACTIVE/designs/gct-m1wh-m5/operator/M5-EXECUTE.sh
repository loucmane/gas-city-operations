#!/bin/sh
# M5 executor transaction (ga-0t04, LAYOUT.md live sequence step 5). This MUTATES live state:
# it pauses the reconciler timer and adopts the metadata successor.
#
# Start it ONCE, from a real WSL terminal, as its own detached user unit:
#   systemd-run --user --unit=gct-m1wh-m5-execute --collect -p UMask=0022 \
#     sh <PKG>/operator/M5-EXECUTE.sh <reviewed binding commit> <source-pins sha256>
# That returns at once. The unit runs in the supervisor namespaces with umask 0022, and all output
# goes to execute-<timestamp>.txt beside this script. No stage depends on the terminal, so closing
# it cannot interrupt a stage or break a stage's output (binding review A, should-fix 3).
#
# Order:
#   prepare -> [SOURCE_PASS record] -> pause -> observe -> [PAIRING_PASS record]
#   -> paired -> verify -> [COMMIT_PASS record] -> restore-accepted
#
# The coordinator writes each review record, and the executor itself re-verifies every record.
# The script never replays a stage and never runs a recovery on its own. On any refusal, a HOLD
# marker or a timeout, it stops and prints the one recovery command that LAYOUT allows there.
S=/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
P=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-m5
Q=$W/reports/m5/q
COMMIT=${1:?usage: M5-EXECUTE.sh <reviewed binding commit> <source-pins sha256>}
EXPECT=${2:?usage: M5-EXECUTE.sh <reviewed binding commit> <source-pins sha256>}
PATH=/usr/local/bin:/usr/bin:/bin
export PATH XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
LOG="$S/execute-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null

clean() {
  head=$(git -C "$W" rev-parse HEAD)
  dirty=$(git -C "$W" --no-optional-locks status --porcelain | wc -l)
  [ "$head" = "$COMMIT" ] && [ "$dirty" = 0 ] && return 0
  echo "== STOP: package worktree head=$head dirty=$dirty"; return 1
}
stage() {
  clean || return 1
  echo "== stage $* $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -B "$P/launch.py" --expect-sources "$EXPECT" "$@"
  rc=$?
  echo
  [ "$rc" = 0 ] && return 0
  echo "== REFUSED at $1 rc=$rc $(date -u +%H:%M:%SZ)"; return 1
}
# Waits for q/<name> or a HOLD-<name> marker in staging, for at most $2 seconds.
await() {
  echo "== waiting for $1 $(date -u +%H:%M:%SZ)"
  n=0
  while [ "$n" -lt "$2" ]; do
    [ -f "$Q/$1" ] && { echo "== found $1 $(date -u +%H:%M:%SZ)"; return 0; }
    [ -f "$S/HOLD-$1" ] && { echo "== HOLD marker for $1 $(date -u +%H:%M:%SZ)"; return 1; }
    sleep 2; n=$((n + 2))
  done
  echo "== TIMEOUT waiting for $1 $(date -u +%H:%M:%SZ)"; return 1
}
sha() { sha256sum "$1" | cut -c1-64; }
recovery() {
  echo "== RECOVERY (only when the coordinator confirms), as its own unit:"
  echo "   systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 /usr/bin/python3 -I -B $P/launch.py --expect-sources $EXPECT $*"
}

# Binding review B must-fix: the window's renewal horizon is the oldest frozen cache atime plus 24 h
# (metadata_window.build), and a late prepare consumes the package root. Refuse unless the full
# 900 s window, the 10 s margin and 300 s of slack still fit before the horizon.
horizon_ok() {
  /usr/bin/python3 -I -B -c "
import json, sys, time
namespace = {'__file__': '$P/manifest_candidate.py', '__name__': 'manifest_candidate'}
exec(compile(open('$P/manifest_candidate.py', 'rb').read(), 'manifest_candidate', 'exec'), namespace)
inv = json.load(open(namespace['BASELINE_PATH']))['closure']['cache']['inventory']
renewal = min(v['atime_ns'] for v in inv.values()) / 1e9 + 86400
left = renewal - time.time() - 900 - 10
print('== horizon %.0f s after the full window' % left)
sys.exit(0 if left > 300 else 1)"
}

run() {
  echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
  [ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; return; }
  horizon_ok || { echo "== STOP before prepare: cache renewal horizon too near; recapture instead"; return; }
  echo "== apt history tail"; tail -4 /var/log/apt/history.log
  stage prepare || {
    [ -f "$Q/preparation-pause-intent.json" ] && recovery recover-preparation "$(sha "$Q/preparation-pause-intent.json")"
    return; }
  X=$(sha "$Q/prepared.json"); echo "== prepared $X"
  if ! await source-pass.json 690; then recovery recover-preparation "$(sha "$Q/preparation-pause-intent.json")"; return; fi
  stage pause "$X" || { recovery recover-pause "$X"; return; }
  stage observe "$X" || { recovery restore-preapply "$X"; return; }
  if ! await pairing-pass.json 480; then recovery restore-preapply "$X"; return; fi
  stage paired "$X" || { echo "== paired refused: run NOTHING; the coordinator must inspect the commit records first"; return; }
  stage verify "$X" || { echo "== verify refused: run NOTHING; the coordinator must inspect first"; return; }
  if ! await commit-pass.json 3600; then echo "== no COMMIT_PASS yet: the timer stays paused; the coordinator decides"; return; fi
  stage restore-accepted "$X" || { echo "== restore-accepted refused: the coordinator must inspect"; return; }
  echo "== ACCEPTED"
}
run
echo "== end $(date -u +%H:%M:%SZ)"
