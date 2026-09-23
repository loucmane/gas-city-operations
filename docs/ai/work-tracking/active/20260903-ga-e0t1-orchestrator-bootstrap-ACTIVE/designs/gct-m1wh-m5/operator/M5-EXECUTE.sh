#!/bin/sh
# M5 executor transaction (ga-0t04, LAYOUT.md live sequence step 5). This MUTATES live state:
# it pauses the reconciler timer and adopts the metadata successor.
#
# Start it ONCE, from a real WSL terminal, as its own detached user unit:
#   systemd-run --user --unit=gct-m1wh-m5-execute --collect -p UMask=0022 \
#     sh <PKG>/operator/M5-EXECUTE.sh <reviewed binding commit> <source-pins sha256>
# That returns at once. The unit runs in the supervisor namespaces with umask 0022. All output goes
# to execute-<timestamp>.txt in the staging directory $S, never into the package. No stage
# depends on the terminal.
#
# Order:
#   prepare -> [SOURCE_PASS record] -> pause -> observe -> [PAIRING_PASS record]
#   -> paired -> verify -> [COMMIT_PASS record] -> restore-accepted
#
# The coordinator writes each review record, and the executor re-verifies every record. A file
# $S/HOLD-<record name> (for example HOLD-source-pass.json) makes the matching wait stop. Before
# prepare, the script refuses if any HOLD marker is left over or reports/m5 already exists.
# During the transaction, NOTHING may write into the package checkout T: no commit, no aegis
# or workflow log, no draft. Any tracked or unignored change stops the next stage. The
# script never replays a stage and never runs a recovery on its own. On any refusal, HOLD, timeout
# or too-short window it stops, and prints the one recovery command that fits that point.
#
# Time limits. The executor's own checks remain authoritative; these gates only stop early,
# while a clean recovery still applies.
# - Window: prepare's pause intent fixes a 900 s window (metadata_window.build). A native phase
#   writes <phase>-consumed.json BEFORE admit() reserves its 66 s. A refusal after that is not
#   terminal, and restore-preapply then refuses. So observe starts only with more than 180 s of
#   window left, and paired only above its derived gate. The
#   remaining window is computed exactly as admit() does: the minimum of the monotonic deadline,
#   the boot-time deadline, and the renewal horizon minus 10 s.
#   The SOURCE_PASS wait ends at 660 s of window left and the PAIRING_PASS wait at 300 s. The
#   paired gate is derived from the measured pause, and is at least 300 s. Waits count wall-clock time.
# - Horizon: restore-accepted still needs the exact cache metadata, atimes included, so it must
#   run before the renewal horizon (oldest frozen atime plus 24 h). The gate before prepare
#   reserves 900 + 10 + 1800 (COMMIT_PASS reviews and restoration) + 300 s of slack. The
#   COMMIT_PASS wait ends 310 s before the horizon.
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

# Fails closed: a failed git status counts as dirty.
clean() {
  head=$(git -C "$W" rev-parse HEAD) || head=unreadable
  status=$(git -C "$W" --no-optional-locks status --porcelain) || status=unreadable
  [ "$head" = "$COMMIT" ] && [ -z "$status" ] && return 0
  echo "== STOP: package worktree head=$head status=$(printf '%s' "$status" | wc -l) lines"; return 1
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
# Waits for q/<name> or $S/HOLD-<name>, for at most $2 seconds.
await() {
  echo "== waiting for $1, at most $2 s, from $(date -u +%H:%M:%SZ)"
  end=$(( $(date +%s) + $2 ))
  while [ "$(date +%s)" -lt "$end" ]; do
    [ -f "$Q/$1" ] && { echo "== found $1 $(date -u +%H:%M:%SZ)"; return 0; }
    [ -f "$S/HOLD-$1" ] && { echo "== HOLD marker for $1 $(date -u +%H:%M:%SZ)"; return 1; }
    sleep 2
  done
  echo "== TIMEOUT waiting for $1 $(date -u +%H:%M:%SZ)"; return 1
}
sha() { sha256sum "$1" | cut -c1-64; }
recovery() {
  echo "== RECOVERY (only when the coordinator confirms), as its own unit:"
  echo "   systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 /usr/bin/python3 -I -B $P/launch.py --expect-sources $EXPECT $*"
}
preparation_recovery() {
  if [ -f "$Q/preparation-pause-command.json" ] && /usr/bin/python3 -I -B -c "
import json, sys
sys.exit(0 if json.load(open('$Q/preparation-pause-command.json')).get('returncode') == 0 else 1)"; then
    recovery recover-preparation "$(sha "$Q/preparation-pause-intent.json")"
  else
    echo "== NO successful stop record: recover-preparation would refuse. Confirm the timer state by hand, as LAYOUT.md requires for an interrupted preparation."
  fi
}
# Seconds to the cache-renewal horizon of the pinned baseline (min atime + 86400 s). BASELINE_PATH is
# parsed from manifest_candidate.py as text; no package code runs here.
horizon_left() {
  /usr/bin/python3 -I -B -c "
import json, re, time
text = open('$P/manifest_candidate.py').read()
o = re.search(r\"^O = '([^']+)'\$\", text, re.M).group(1)
rel = re.search(r\"^BASELINE_PATH = O \+ '([^']+)'\$\", text, re.M).group(1)
inv = json.load(open(o + rel))['closure']['cache']['inventory']
print(int(min(v['atime_ns'] for v in inv.values()) / 1e9 + 86400 - time.time()))"
}
# Seconds of window left as metadata_window.admit computes it, from the recorded deadline. The
# sample span (under 1 s) is ignored, and the gates below have far larger margins.
window_left() {
  /usr/bin/python3 -I -B -c "
import json, time
d = json.load(open('$Q/preparation-paused.json'))['deadline']
mono, boot, wall = time.monotonic_ns(), time.clock_gettime_ns(time.CLOCK_BOOTTIME), time.time_ns()
print(int(min(d['mono_deadline'] - mono, d['boot_deadline'] - boot, d['renewal'] - 10 * 10**9 - wall) / 10**9))"
}
budget() { b=$(( $(window_left) - $1 )); [ "$b" -gt 0 ] && echo "$b" || echo 0; }

run() {
  echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
  [ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; return; }
  clean || return
  [ ! -e "$W/reports/m5" ] || { echo "== STOP: reports/m5 already exists; this attempt root is consumed"; return; }
  for marker in "$S"/HOLD-*; do
    [ -e "$marker" ] && { echo "== STOP: leftover HOLD marker $marker"; return; }
  done
  left=$(horizon_left) || { echo "== STOP: horizon unreadable"; return; }
  echo "== horizon in $left s; prepare needs more than $((900 + 10 + 1800 + 300)) s"
  [ "$left" -gt $((900 + 10 + 1800 + 300)) ] || { echo "== STOP before prepare: horizon too near; recapture instead"; return; }
  echo "== apt history tail (informational)"; tail -4 /var/log/apt/history.log
  stage prepare || { [ -f "$Q/preparation-pause-intent.json" ] && preparation_recovery; return; }
  X=$(sha "$Q/prepared.json"); echo "== prepared $X; window left $(window_left) s"
  if ! await source-pass.json "$(budget 660)"; then preparation_recovery; return; fi
  t0=$(date +%s)
  stage pause "$X" || {
    if [ -f "$Q/window.json" ]; then recovery restore-preapply "$X"
    elif [ -f "$Q/pause-consumed.json" ]; then recovery recover-pause "$X"
    else preparation_recovery; fi
    return; }
  pause_s=$(( $(date +%s) - t0 )); echo "== pause took $pause_s s"
  w=$(window_left); echo "== window left $w s before observe"
  [ "$w" -gt 180 ] || { echo "== STOP: window too short to start observe"; recovery restore-preapply "$X"; return; }
  stage observe "$X" || {
    if [ -f "$Q/observe-consumed.json" ] && [ ! -f "$Q/observe-result.json" ]; then
      echo "== observe consumed without a terminal result: run NOTHING; the coordinator must inspect"
    else recovery restore-preapply "$X"; fi
    return; }
  if ! await pairing-pass.json "$(budget 300)"; then recovery restore-preapply "$X"; return; fi
  w=$(window_left); echo "== window left $w s before paired"
  # Probe 1 up to 65 s, probe 2 up to 36 s, and the commit admission reserve of 66 s. On top of
  # that, the three current() snapshots in paired, bounded by twice the measured pause (which takes
  # the same kind of snapshots), plus 30 s. Never below 300 s.
  need=$(( 167 + 2 * pause_s + 30 )); [ "$need" -ge 300 ] || need=300
  [ "$w" -gt "$need" ] || { echo "== STOP: window $w s is not above $need s for paired"; recovery restore-preapply "$X"; return; }
  stage paired "$X" || { echo "== paired refused: run NOTHING; the coordinator must inspect the probe and commit records first"; return; }
  stage verify "$X" || { echo "== verify refused: run NOTHING; the coordinator must inspect first"; return; }
  c=$(( $(horizon_left) - 10 - 300 )); [ "$c" -gt 0 ] || c=0
  if ! await commit-pass.json "$c"; then echo "== no COMMIT_PASS before the horizon margin: the timer stays paused; the coordinator decides"; return; fi
  h=$(horizon_left); [ "$h" -gt 70 ] || { echo "== STOP: horizon $h s is too near for restore-accepted; the coordinator decides"; return; }
  stage restore-accepted "$X" || { echo "== restore-accepted refused: the coordinator must inspect"; return; }
  echo "== ACCEPTED"
}
run
echo "== end $(date -u +%H:%M:%SZ)"
