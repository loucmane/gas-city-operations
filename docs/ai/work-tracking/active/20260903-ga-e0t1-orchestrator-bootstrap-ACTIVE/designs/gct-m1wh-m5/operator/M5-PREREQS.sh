#!/bin/sh
# M5 live prerequisites (ga-0t04, LAYOUT.md live sequence step 2). This MUTATES live state.
# It runs the eight reviewed prereqs.py steps in order. Before each step it verifies that the
# package worktree is clean at the reviewed commit. Each step runs as its own
# `systemd-run --user -p UMask=0022` unit in the supervisor namespaces, and the script stops at
# the first refusal. Never re-run a refused step: report it, and use only resume or rollback as
# LAYOUT.md directs. Output is saved beside this script as prereqs-<timestamp>.txt.
S=/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
P=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-m5
C=29cee9919a9977323637728da84719b80ad9f58c62c0742fe7c313c957e433c4
LOG="$S/prereqs-$(date -u +%Y%m%dT%H%M%SZ).txt"
run() {
echo "== apt history tail"
tail -4 /var/log/apt/history.log
for step in inputs cli city-transition checkout registry render city-final authority; do
  head=$(git -C "$W" rev-parse HEAD)
  dirty=$(git -C "$W" --no-optional-locks status --porcelain | wc -l)
  if [ "$head" != ae61f6960ba05bee34df5b500ebdc6d41abb8768 ] || [ "$dirty" != 0 ]; then
    echo "== STOP before $step: package worktree head=$head dirty=$dirty"; break
  fi
  echo "== step $step $(date -u +%H:%M:%SZ)"
  systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 \
    /usr/bin/python3 -I -B "$P/prereqs.py" "$C" "$step"
  rc=$?
  if [ "$rc" != 0 ]; then echo "== REFUSED at $step rc=$rc"; break; fi
done
echo "== end $(date -u +%H:%M:%SZ)"
}
run 2>&1 | tee "$LOG"
