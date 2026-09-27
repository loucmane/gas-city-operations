#!/bin/sh
# S1 WORKTREE: create only the exact unsigned Operations workspace and local rules.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1.20-astra-bootstrap
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1.20-astra-bootstrap
COMMIT=${1:?usage: WORKTREE.sh <reviewed commit>}
STEP_SHA=ec7847c77089f11d774f6d96691faf708b669ea174b6c8377865d7804f7506aa
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/worktree-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e /var/tmp/ga-e0t1.20-worktree-20260927-r1 ] && [ ! -L /var/tmp/ga-e0t1.20-worktree-20260927-r1 ]; } || { echo "== STOP: output root already used: /var/tmp/ga-e0t1.20-worktree-20260927-r1"; echo "== end"; exit 1; }
echo "== worktree $(date -u +%H:%M:%SZ)"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/worktree.py" "$STEP_SHA"
rc=$?
if [ "$rc" != 0 ]; then
  echo "== WORKTREE REFUSED rc=$rc: read this log and /var/tmp/ga-e0t1.20-worktree-20260927-r1 before any further step"
  echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
fi
echo "== WORKTREE PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
