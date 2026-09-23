"""Read-only proof, before ROUTE, of every gc CLI shape the in-window jobs rely on.

The installed gc binary (69d00186) documents each command's result with `--json-schema=result`, which
prints the schema and exits without acting. This proof asks the binary itself, so it does not depend on
which source commit the binary was built from:
- `session list`: sessions[] rows carry id, template, closed and session_name (WATCH, release, CLOSE);
- `session nudge`: requires ok, outcome delivered or queued, and accepts --delivery wait-idle (release);
- `session close`: requires ok and session_id (CLOSE);
- `runtime drain`: requires ok and status draining (CLOSE);
- `status`: the health object the lifecycle suspension check reads. Core at the worker base e6366b9e
  emits exactly three health signals: city_suspended, controller_not_running and no_agents_running
  (cmd/gc/city_status_snapshot.go). The window allows the first and third, and requires the
  controller running, so a live worker cannot add an unexpected signal.
The release transport posts to ga-4z38's own notes in the rig store and the worker reads them with the
same `bd show ga-4z38 --json` it uses for its claim, so no cross-store message read is involved.
Nothing is written.

Usage: python3 -B cli-proof.py   (prints one JSON object; exit 0 only if every check holds)
"""
import json
import re
import subprocess
import sys

GC = ['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city']
ENV = dict(HOME='/home/loucmane', GC_HOME='/home/loucmane/gascity/home', GIT_OPTIONAL_LOCKS='0',
           BD_DISABLE_METRICS='1', PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', LC_ALL='C.UTF-8')
CORE = '/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles'
BASE = 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88'


def schema(*command):
    p = subprocess.run(GC + list(command) + ['--json-schema=result'], env=ENV, capture_output=True, text=True,
                       timeout=60, stdin=subprocess.DEVNULL)
    return json.loads(p.stdout)


def help_text(*command):
    p = subprocess.run(GC + list(command) + ['--help'], env=ENV, capture_output=True, text=True, timeout=60,
                       stdin=subprocess.DEVNULL)
    return p.stdout


def main():
    listing = schema('session', 'list')
    row = listing['properties']['sessions']['items']['properties']
    nudge = schema('session', 'nudge')
    close = schema('session', 'close')
    drain = schema('runtime', 'drain')
    status_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':cmd/gc/city_status_snapshot.go'],
                               env=ENV, capture_output=True, text=True, timeout=60).stdout
    emitted = sorted(set(re.findall(r'signals = append\(signals, "([a-z_]+)"\)', status_go)))
    result = dict(
        session_list=all(k in row for k in ('id', 'template', 'closed', 'session_name', 'alias', 'state')),
        nudge=set(nudge['required']) >= {'ok', 'outcome'}
        and set(nudge['properties']['outcome']['enum']) == {'delivered', 'queued'}
        and 'wait-idle' in nudge['properties']['delivery']['enum'] and '--delivery' in help_text('session', 'nudge'),
        close=set(close['required']) >= {'ok', 'session_id'} and close['properties']['command']['const'] == 'session close',
        drain=set(drain['required']) >= {'ok', 'status'} and drain['properties']['status']['const'] == 'draining',
        health_signals=emitted == ['city_suspended', 'controller_not_running', 'no_agents_running'])
    result['ok'] = all(result.values())
    result['emitted_signals'] = emitted
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
