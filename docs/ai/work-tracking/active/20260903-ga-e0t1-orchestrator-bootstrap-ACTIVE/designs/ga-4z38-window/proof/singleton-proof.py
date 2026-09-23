"""Read-only proof, before ROUTE, that the capped worker is not drained while it owns ga-4z38.

gc warns for this overlay that "max_active_sessions=1 creates a canonical singleton that drains when
scale_check returns 0" (prep-r11.py SINGLETON_WARNING). After the claim, ga-4z38 is in_progress and
assigned, so the default scale_check (ready, unassigned, routed demand) returns 0 while the worker
waits for a release. This proof checks that the session is still preserved:
1. The overlay's effective config (prep config.isolated.json) gives the worker no custom ScaleCheck or
   WorkQuery, so the default demand probe applies.
2. Core at the worker base e6366b9e (the PR 45 merge the installed gc was built from):
   - internal/config/workquery.go: the default count form "counts ready, unassigned, routed demand";
   - cmd/gc/pool_desired_state.go: new-session demand comes from scale_check, while the desired-state
     computation "only preserves sessions that already own actionable work", and its resume tier keeps
     a session whose assigned work bead is in_progress or open.
All reads are git object reads (GIT_OPTIONAL_LOCKS=0) and one prep evidence file. Nothing is written.

Usage: python3 -B singleton-proof.py   (prints one JSON object; exit 0 only if every check holds)
"""
import json
import subprocess
import sys
from pathlib import Path

CONFIG = Path('/var/tmp/ga-4z38-prep-20260923-r2/config.isolated.json')
CORE = '/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles'
BASE = 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88'
ENV = dict(PATH='/usr/local/bin:/usr/bin:/bin', HOME='/home/loucmane', GIT_OPTIONAL_LOCKS='0', LC_ALL='C.UTF-8')


def show(path):
    p = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':' + path], env=ENV, capture_output=True,
                       text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-300:]
    return p.stdout


def main():
    agents = json.loads(CONFIG.read_text())['config']['Agents']
    [worker] = [a for a in agents if a['Dir'] == 'gascity' and a['Name'] == 'implementation-worker']
    config = dict(default_demand=worker['ScaleCheck'] == '' and worker['WorkQuery'] == '',
                  capped_singleton=worker['MaxActiveSessions'] == 1 and worker['MinActiveSessions'] == 0)
    query = show('internal/config/workquery.go')
    desired = show('cmd/gc/pool_desired_state.go')
    core = dict(
        default_counts_unassigned_ready='it counts\n// ready, unassigned, routed demand' in query,
        desired_state_preserves_owners='new-session demand comes\n// from scale_check, while this function only preserves sessions that already\n// own actionable work.' in desired,
        resume_tier_keeps_in_progress='if wb.Status != "in_progress" && wb.Status != "open" {' in desired
        and 'Resume tier: actionable assigned work beads whose assignee resolves' in desired)
    result = dict(config=config, core=core)
    result['ok'] = all(v for part in (config, core) for v in part.values())
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
