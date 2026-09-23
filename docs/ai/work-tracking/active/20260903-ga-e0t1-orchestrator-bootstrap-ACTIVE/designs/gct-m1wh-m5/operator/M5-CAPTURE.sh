#!/bin/sh
# M5 recapture (ga-0t04, LAYOUT.md live sequence step 3, second capture root). Read-only except its
# own records under reports/m5-capture-r2. It runs capture.py audit, complete, settle and freeze in
# order. Each stage gets the SHA-256 of the record the previous stage wrote exclusively. Before each
# stage it verifies that the package worktree is clean at the reviewed commit. Each stage runs as
# its own `systemd-run --user -p UMask=0022` unit. The script stops at the first refusal. Never
# re-run a refused stage.
#
# Timing, on 2026-09-23:
# - It starts only from 10:44:00Z (12:44 Stockholm), so the settle reads refresh yesterday's 09:29
#   and 10:42 cache-access clusters. The horizon then becomes the 13:33:50Z cluster plus 24 h.
# - It starts only until 12:30:00Z (14:30 Stockholm). A later settle would come too near that
#   horizon: between about 13:18:40Z and 13:33:50Z the settle renewal check refuses and consumes
#   the root, and a capture that late leaves no time for the binding review and the executor.
# It prints the horizon and the latest executor start that operator/M5-EXECUTE.sh will accept.
# Output goes to capture-<timestamp>.txt in the staging directory $S.
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
low = min(v['atime_ns'] for v in inv.values()) / 1e9
at = lambda s: datetime.datetime.fromtimestamp(s, datetime.timezone.utc).isoformat()
print('== horizon', at(low + 86400), 'latest executor start (window, margin, commit review, slack)',
      at(low + 86400 - 900 - 10 - 1800 - 300))"
}
run() {
  now=$(date -u +%Y%m%d%H%M%S)
  if [ "$now" -lt 20260923104400 ] || [ "$now" -gt 20260923123000 ]; then
    echo "== STOP: start only from 10:44:00Z to 12:30:00Z (12:44 to 14:30 Stockholm) on 2026-09-23"; return
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
