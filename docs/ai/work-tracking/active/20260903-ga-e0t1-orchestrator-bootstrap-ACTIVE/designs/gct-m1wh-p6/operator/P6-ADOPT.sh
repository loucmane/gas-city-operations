#!/bin/sh
# P6 receipt adoption (ga-0t04, gct-m1wh-p6 RUNBOOK step 5). This MUTATES exactly one live file: the
# provisioning receipt, through the unchanged reviewed provisioner. p6-adopt.py:
# - writes its typed-support witness;
# - takes a before snapshot;
# - runs `--check`, which must find only receipt.sha256 drift;
# - traces the running revision;
# - runs `--apply` and verify;
# - takes an after snapshot and compares it.
# On failure it rolls back to the exact old bytes, and only after clean containment.
#
# Start it ONCE, from a real WSL terminal, as its own detached user unit:
#   systemd-run --user --unit=gct-m1wh-p6-adopt --collect -p UMask=0022 \
#     sh <P>/operator/P6-ADOPT.sh <reviewed commit>
# All output goes to p6-adopt-<timestamp>.txt in $S. Nobody runs gc until the log ends.
S=/home/loucmane/.local/share/gas-city-staging/gct-m1wh-p6
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
P=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-p6
COMMIT=${1:?usage: P6-ADOPT.sh <reviewed commit>}
ADOPT_SHA=64879d2a4f8109750323da3d91af6d46667d4ea6eccbfd0086e453ccc521c399
PATH=/usr/local/bin:/usr/bin:/bin
export PATH XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
LOG="$S/p6-adopt-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -C "$W" --no-optional-locks status --porcelain) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/gct-m1wh-p6-adoption-20260923-r2 ] && [ ! -L /var/tmp/gct-m1wh-p6-adoption-20260923-r2 ]; } \
  || { echo "== STOP: adoption root already used"; echo "== end"; exit 1; }
# Deadline: the adoption compares its before and after cache snapshots with atimes included, and the
# pack cache's 2026-09-22 13:33:50Z access cluster turns 24 h old at 2026-09-23 13:33:50Z. So it starts
# only until 13:20:00Z, which leaves 13 minutes for the whole transaction.
now=$(date -u +%Y%m%d%H%M%S)
case "$now" in (*[!0-9]*|'') echo "== STOP: clock unreadable"; echo "== end"; exit 1;; esac
[ "$now" -le 20260923132000 ] || { echo "== STOP: past the 13:20:00Z start deadline; the pack-cache atime boundary is 13:33:50Z"; echo "== end"; exit 1; }
echo "== adopt $(date -u +%H:%M:%SZ)"
/usr/bin/python3 -I -S -B "$P/source-launch.py" "$P/p6-adopt.py" "$ADOPT_SHA"
rc=$?
if [ "$rc" = 0 ]; then echo "== ADOPTED"; else echo "== REFUSED rc=$rc: read this log (traceback), the *-phase.json files and any result.json or rollback.json in the adoption root; run nothing else"; fi
echo "== end $(date -u +%H:%M:%SZ)"
