"""Pin the split package: text digests into apply_split.py, then the script digest into SPLIT.sh."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
APPLY = HERE / "apply_split.py"
WRAPPER = HERE.parent / "operator" / "SPLIT.sh"
STAGE = "split-r2"

WRAPPER_TEXT = """#!/bin/sh
# gct-oak5 split package: close the stale workflow gct-wn1m and create the handover step Beads
# (split/apply_split.py). Runs as a job of the host job runner (designs/gct-jobrunner).
# Log: ~/.local/share/gas-city-staging/gct-oak5-handover/split-<timestamp>.txt; evidence and
# record.json in the stage directory named below. Exits with the script's result, or 1 on a refused
# precondition.
S=/home/loucmane/.local/share/gas-city-staging/gct-oak5-handover
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/gct-oak5-handover/split
STAGE=$S/@STAGE@
COMMIT=${1:?usage: SPLIT.sh <reviewed commit>}
APPLY_SHA=@APPLY_SHA@
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/split-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
[ "$(umask)" = 0022 ] || { echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{ [ ! -e "$STAGE" ] && [ ! -L "$STAGE" ]; } || { echo "== STOP: stage already used: $STAGE"; echo "== end"; exit 1; }
echo "== split $(date -u +%H:%M:%SZ)"
/usr/bin/python3.12 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$C/apply_split.py" "$APPLY_SHA" "$STAGE"
rc=$?
echo "== split rc=$rc"
echo "== end $(date -u +%H:%M:%SZ)"
exit "$rc"
"""


def main():
    shas = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((HERE / "texts").iterdir())}
    text = APPLY.read_text()
    new = re.sub(r"^TEXT_SHA = .*$", "TEXT_SHA = " + json.dumps(shas, sort_keys=True), text, count=1, flags=re.M)
    assert new.count("TEXT_SHA = {") == 1
    APPLY.write_text(new)
    apply_sha = hashlib.sha256(APPLY.read_bytes()).hexdigest()
    WRAPPER.write_text(WRAPPER_TEXT.replace("@STAGE@", STAGE).replace("@APPLY_SHA@", apply_sha))
    print(json.dumps({"texts": shas, "apply_sha256": apply_sha}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
