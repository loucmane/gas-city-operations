#!/bin/sh
# M5 recapture (ga-0t04, LAYOUT.md live sequence step 3, second capture root). Read-only except its
# own records under reports/m5-capture-r2. It runs capture.py audit, complete, settle and freeze in
# order. Each stage gets the SHA-256 of the record the previous stage wrote exclusively. Before each
# stage it verifies that the package worktree is clean at the reviewed commit. Each stage runs as
# its own `systemd-run --user -p UMask=0022` unit. The script stops at the first refusal. Never
# re-run a refused stage.
#
# Timing: the settle reads must refresh yesterday's 09:29 and 10:42 cache-access clusters, so the
# script refuses to start before 10:44:00Z on 2026-09-23. The resulting horizon is the 13:33
# cluster plus 24 h; freeze prints it. Output is saved beside this script as capture-<timestamp>.txt.
S=/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
P=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-m5
R=$W/reports/m5-capture-r2
C=29cee9919a9977323637728da84719b80ad9f58c62c0742fe7c313c957e433c4
COMMIT=${1:?usage: sh M5-CAPTURE.sh <reviewed package commit>}
LOG="$S/capture-$(date -u +%Y%m%dT%H%M%SZ).txt"
stage() {
  head=$(git -C "$W" rev-parse HEAD)
  dirty=$(git -C "$W" --no-optional-locks status --porcelain | wc -l)
  if [ "$head" != "$COMMIT" ] || [ "$dirty" != 0 ]; then
    echo "== STOP before $1: package worktree head=$head dirty=$dirty"; return 1
  fi
  echo "== stage $* $(date -u +%H:%M:%SZ)"
  systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 \
    /usr/bin/python3 -I -B "$P/capture.py" "$C" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then echo "== REFUSED at $1 rc=$rc"; return 1; fi
}
sha() { sha256sum "$R/$1" | cut -c1-64; }
horizon() {
  /usr/bin/python3 -I -B -c "
import json, datetime
inv = json.load(open('$R/baseline.json'))['closure']['cache']['inventory']
low = min(v['atime_ns'] for v in inv.values())
print('== horizon', datetime.datetime.fromtimestamp(low / 1e9 + 86400, datetime.timezone.utc).isoformat(),
      'latest prepare start', datetime.datetime.fromtimestamp(low / 1e9 + 86400 - 910, datetime.timezone.utc).isoformat())"
}
run() {
  if [ "$(date -u +%Y%m%d%H%M%S)" -lt 20260923104400 ]; then
    echo "== STOP: too early; start at or after 10:44:00Z so the 09:29 and 10:42 clusters refresh"; return
  fi
  echo "== apt history tail"
  tail -4 /var/log/apt/history.log
  stage audit \
  && stage complete "$(sha audit.json)" \
  && B=$(sha baseline-audit.json) && stage settle "$B" \
  && stage freeze "$B" "$(sha settle-result.json)" \
  && echo "== baseline.json $(sha baseline.json)" && horizon
  echo "== end $(date -u +%H:%M:%SZ)"
}
run 2>&1 | tee "$LOG"
