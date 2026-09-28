#!/bin/sh
# One reviewed metadata-only host job. No worker or lifecycle mutation.
set -eu
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-codex-permissions
L=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-p6/source-launch.py
C=${1:?reviewed commit required}
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
[ "$#" -eq 1 ]
[ "$(umask)" = 0022 ]
[ "$(git --no-optional-locks -c core.fsmonitor=false -C "$W" rev-parse HEAD)" = "$C" ]
[ -z "$(git --no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" status --porcelain --untracked-files=all)" ]
[ "$(sha256sum "$L" | cut -d ' ' -f 1)" = 31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea ]
[ ! -e /var/tmp/ga-e0t1.20-codex-permissions-20260928-r1 ]
[ ! -L /var/tmp/ga-e0t1.20-codex-permissions-20260928-r1 ]
exec /usr/bin/python3 -I -S -B "$L" "$D/apply.py" 4618bcb8b05846e9aa6a7d6a3ae5f17ef308d5e3319d31f38417fa1f5c7a54c5 apply
