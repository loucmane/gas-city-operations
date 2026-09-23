#!/bin/sh
# P6 read-only steps (ga-0t04, gct-m1wh-p6 RUNBOOK steps 1-3). Nothing here installs a receipt or
# launches a worker. It runs, in order:
#   p6-input.py         derive the receipt input, prove M5 from its records, trace the revision
#   p6-observe-compose  the network-isolated composition in bwrap; before and after preserved
#   p6-readiness        normalize, finalize, discover, negative old-PATH, subscription, preflight
# Each step is `systemd-run --user -p UMask=0022` in the supervisor namespaces, with its reviewed
# digest pinned here. Before each step the wrapper checks that the package worktree is clean at the
# reviewed commit, and it stops at the first refusal. The output roots under /var/tmp are
# single-use; never re-run a refused step. Output goes to p6-readonly-<timestamp>.txt in $S.
#
# While this runs, nobody runs gc: the composition and readiness snapshots compare the pack cache.
S=/home/loucmane/.local/share/gas-city-staging/gct-m1wh-p6
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
P=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-p6
COMMIT=${1:?usage: sh P6-READONLY.sh <reviewed package commit>}
INPUT_SHA=f0150b631196dec051dad05f40803deccad8e480ed0a638e86e61ea0db962c1c
COMPOSE_SHA=43b94ce677dcaa80b6937f7205362063da151f0608a99874b18b692ab8f2c8d6
READY_SHA=7b28b3e551e86818a2cdda3e53ed90c7072781e0a9354bd1ebf5d9425d579133
LOG="$S/p6-readonly-$(date -u +%Y%m%dT%H%M%SZ).txt"
stage() {
  head=$(git -C "$W" rev-parse HEAD) || head=unreadable
  status=$(git -C "$W" --no-optional-locks status --porcelain) || status=unreadable
  if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
    echo "== STOP before $1: package worktree head=$head not clean or not the reviewed commit"; return 1
  fi
  echo "== step $1 $(date -u +%H:%M:%SZ)"
  systemd-run --user --wait --collect --pipe --quiet -p UMask=0022 \
    /usr/bin/python3 -I -S -B "$P/source-launch.py" "$P/$1" "$2"
  rc=$?
  [ "$rc" = 0 ] && return 0
  echo "== REFUSED at $1 rc=$rc $(date -u +%H:%M:%SZ)"; return 1
}
run() {
  stage p6-input.py "$INPUT_SHA" \
  && stage p6-observe-compose.py "$COMPOSE_SHA" \
  && stage p6-readiness.py "$READY_SHA" \
  && echo "== READ-ONLY STEPS PASSED: the coordinator fills the adoption constants next"
  echo "== end $(date -u +%H:%M:%SZ)"
}
run 2>&1 | tee "$LOG"
