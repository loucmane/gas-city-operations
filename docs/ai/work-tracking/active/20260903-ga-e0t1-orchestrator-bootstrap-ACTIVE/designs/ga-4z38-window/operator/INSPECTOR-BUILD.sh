#!/bin/sh
# ga-4z38 inspector rebuild: build the platform inspector pinned to the live M5 manifest (2d7eadce).
# OBSERVE refused on 2026-09-24 20:28Z because the reused 09-20 inspector embeds the pre-M5 pin
# a6324753. This builds a new binary into a fresh root and records its digest; it installs nothing,
# runs nothing it builds, and changes no live state. The next package revision pins the digest.
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-4z38-window/inspector-build-<timestamp>.txt. Exits with the
# builder's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-4z38-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-4z38-window
COMMIT=${1:?usage: INSPECTOR-BUILD.sh <reviewed commit>}
BUILDER_SHA=aba0868b000425df39dfbeaf48f70d15366958d532c3df264bf2cd0e69fde20a
ENTRY_SHA=e5e9872f2b57d70c9fbde8e3d152978eaf9266453af67dbd1a82a4d1886b7ca3
ROOT=/var/tmp/ga-4z38-platform-inspector-20260924-r1
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/inspector-build-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$ROOT" ] && [ ! -L "$ROOT" ]; } || { echo "== STOP: output root already used: $ROOT"; echo "== end"; exit 1; }
echo "== build $(date -u +%H:%M:%SZ)"
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/inspector/inspector-build-r1.py" "$BUILDER_SHA" "$ENTRY_SHA"
rc=$?
if [ "$rc" != 0 ]; then
  echo "== INSPECTOR-BUILD REFUSED at build rc=$rc: read this log and $ROOT before any further step"
  echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
fi
echo "== INSPECTOR-BUILD PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
