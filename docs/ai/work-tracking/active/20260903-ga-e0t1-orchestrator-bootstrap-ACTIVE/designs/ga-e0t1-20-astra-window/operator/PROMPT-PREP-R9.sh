#!/bin/sh
# R9 PROMPT PREP: read-only host observation and uninstalled image. No worker launch.
S=/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-e0t1-20-astra-window
COMMIT=${1:?usage: PROMPT-PREP-R9.sh <reviewed commit>}
PREP_SHA=e938b45ec652270e2869a8c9e665bd907cff242c934249b5266e05e74221ac82
OUT=/var/tmp/ga-e0t1.20-prompt-prep-20260929-r9
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/prompt-prep-r9-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) mnt=$(readlink /proc/self/ns/mnt) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$OUT" ] && [ ! -L "$OUT" ]; } || { echo "== STOP: evidence root already used: $OUT"; echo "== end"; exit 1; }
# Same signer policy as the required runner, checked again at the wrapper.
signature=$(/usr/bin/git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -c gpg.program=/usr/bin/gpg -c gpg.ssh.program=/usr/bin/false -c gpg.x509.program=/usr/bin/false -C "$W" verify-commit --raw "$COMMIT" 2>&1) || { echo "== STOP: signature verification failed"; exit 1; }
printf '%s\n' "$signature" | /usr/bin/awk '$1 == "[GNUPG:]" && $2 == "VALIDSIG" && $NF == "7720D1FE503A88EDECA61A6F0C7D823543E01875" { valid=1 } END { exit !valid }' || { echo "== STOP: signer mismatch"; exit 1; }
echo "== prep $(date -u +%H:%M:%SZ)"
# The P6 package's source-launch.py (31bdeea8) runs prepare.py only if its bytes match PREP_SHA.
/usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/prompt-prep-r9.py" "$PREP_SHA"
rc=$?
if [ "$rc" = 0 ]; then echo "== PREP PASS"; else echo "== PREP REFUSED rc=$rc: read this log and $OUT; run nothing else"; fi
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
