"""Read-only proof, before ROUTE, of every gc CLI shape the in-window jobs rely on.

The installed gc binary (69d00186) documents each command's result with `--json-schema=result`, which
prints the schema and exits without acting. This proof asks the binary itself, so it does not depend on
which source commit the binary was built from:
- `session list`: sessions[] rows carry id, template, closed and session_name (WATCH, release, CLOSE);
- `session nudge`: requires ok and an outcome, and accepts --delivery immediate (release). Core source
  shows why the release uses immediate: wait-idle delivers live only when the session is idle within
  30 seconds and otherwise queues the nudge for a later dispatcher delivery (cmd/gc/cmd_nudge.go,
  internal/worker/runtime_handle.go nudgeWaitIdle), whereas immediate always types the text into the
  session's tmux pane now (RuntimeHandle.nudgeNow to the tmux provider NudgeNow) and reports delivered;
  text that lands while Claude is mid-turn waits in Claude's own input queue (tmux provider Nudge
  comment). The worker's receipt provider is claude;
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
    handle_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':internal/worker/runtime_handle.go'],
                               env=ENV, capture_output=True, text=True, timeout=60).stdout
    wait_idle = re.search(r'func \(h \*RuntimeHandle\) nudgeWaitIdle\(.*?\n}\n', handle_go, re.S)
    now = re.search(r'func \(h \*RuntimeHandle\) nudgeNow\(.*?\n}\n', handle_go, re.S)
    adapter_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':internal/runtime/tmux/adapter.go'],
                                env=ENV, capture_output=True, text=True, timeout=60).stdout
    cli_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':cmd/gc/cmd_nudge.go'],
                            env=ENV, capture_output=True, text=True, timeout=60).stdout
    receipt = json.loads(open('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json').read())
    provider = receipt['profiles'][0]['provider']
    result = dict(
        session_list=all(k in row for k in ('id', 'template', 'closed', 'session_name', 'alias', 'state')),
        nudge=set(nudge['required']) >= {'ok', 'outcome'}
        and set(nudge['properties']['outcome']['enum']) == {'delivered', 'queued'}
        and 'immediate' in nudge['properties']['delivery']['enum'] and '--delivery' in help_text('session', 'nudge'),
        close=set(close['required']) >= {'ok', 'session_id'} and close['properties']['command']['const'] == 'session close',
        drain=set(drain['required']) >= {'ok', 'status'} and drain['properties']['status']['const'] == 'draining',
        health_signals=emitted == ['city_suspended', 'controller_not_running', 'no_agents_running'],
        wait_idle_may_queue=bool(wait_idle) and 'waiter.WaitForIdle(ctx, h.sessionName, runtimeHandleWaitIdleTimeout)'
        in wait_idle.group(0) and 'if mode == nudgeDeliveryWaitIdle && !result.Delivered {' in cli_go,
        immediate_types_now=bool(now) and 'immediate.NudgeNow(h.sessionName, content)' in now.group(0)
        and 'func (p *Provider) NudgeNow(name string, content []runtime.ContentBlock) error {' in adapter_go
        and "Claude's cooperative queue will handle it at the next turn" in adapter_go,
        worker_provider_is_claude=provider.get('name') == 'claude')
    result['ok'] = all(result.values())
    result['emitted_signals'] = emitted
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
