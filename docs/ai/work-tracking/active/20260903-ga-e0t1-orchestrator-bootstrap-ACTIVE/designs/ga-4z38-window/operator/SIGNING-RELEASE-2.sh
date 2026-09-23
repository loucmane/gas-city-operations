#!/bin/sh
# ga-4z38 window signing release: validate the coordinator signing release against the live
# worker session and the staged index, post it once, read it back and nudge.
# Repeatable: a run after the post only verifies and nudges again.
# Slot 2 of 3: the job runner starts each wrapper path once per commit.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-4z38-window/signing-release-2-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-4z38-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-4z38-window
COMMIT=${1:?usage: SIGNING-RELEASE-2.sh <reviewed commit>}
RELEASE_SHA=eaeff286bb466b8d8324280575e1efae8eac2fae02d8d6a2fc10063e98ee51b3
BUDGET_SHA=f987f8c36b6fd7639c739c06bbffb223105a25814841f2518559fa1045fc8dd0
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/signing-release-2-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
[ -e /var/tmp/ga-4z38-source-release.posted ] || { echo "== STOP: no source release posted"; echo "== end"; exit 1; }
step() {
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== SIGNING-RELEASE-2 REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}
step budget "$C/budget-r11.py" "$BUDGET_SHA" 85
step signing-release "$C/release-r11.py" "$RELEASE_SHA" signing
echo "== SIGNING-RELEASE-2 PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
