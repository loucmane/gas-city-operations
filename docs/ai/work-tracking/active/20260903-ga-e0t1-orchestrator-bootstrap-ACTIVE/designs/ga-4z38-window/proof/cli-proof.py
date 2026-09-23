"""Read-only proof, before ROUTE, of every gc CLI shape the in-window jobs rely on.

The installed gc binary (69d00186) documents each command's result with `--json-schema=result`, which
prints the schema and exits without acting. This proof asks the binary itself, so it does not depend on
which source commit the binary was built from:
- `session list`: sessions[] rows carry id, template, closed, session_name and state (WATCH, release,
  CLOSE). city.toml has no [api] section, so with the controller socket alive gc takes the direct-store
  path (cmd/gc/apiroute.go standaloneControllerClient returns nil), whose one-line rows carry the
  normalized state: the reconciler's running state awake is reported as active
  (internal/session/manager.go normalizeInfoState);
- `session nudge`: requires ok and an outcome, and accepts --delivery immediate (release). Core source
  shows why the release uses immediate: wait-idle delivers live only when the session is idle within
  30 seconds and otherwise queues the nudge for a later dispatcher delivery (cmd/gc/cmd_nudge.go,
  internal/worker/runtime_handle.go nudgeWaitIdle), whereas immediate always types the text into the
  session's tmux pane now (RuntimeHandle.nudgeNow to the tmux provider NudgeNow) and reports delivered,
  provided the session is running (a managed session that is not running gets a queued wake instead,
  shouldQueueManagedNudgeWake, which is why the release job requires the session active before it posts);
  text that lands while Claude is mid-turn waits in Claude's own input queue (tmux provider Nudge
  comment). The worker's receipt provider is claude;
- the city tmux socket is `city`: Core names it from [session] socket, else the city name
  (cmd/gc/providers.go tmuxConfigFromSession), city.toml sets no socket, and `gc status --json` reports
  city_name city. Core captures a pane with `tmux -L <socket> capture-pane -p -t <session_name>`
  (internal/runtime/tmux/tmux.go), the form CLOSE, WATCH and the release pane check use;
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
import os
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
    fd = os.open('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json',
                 os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        receipt = json.loads(os.read(fd, 1 << 20))
    finally:
        os.close(fd)
    provider = receipt['profiles'][0]['provider']
    manager_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':internal/session/manager.go'],
                                env=ENV, capture_output=True, text=True, timeout=60).stdout
    apiroute_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':cmd/gc/apiroute.go'],
                                 env=ENV, capture_output=True, text=True, timeout=60).stdout
    fd = os.open('/home/loucmane/gascity/city/city.toml', os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        city_toml = b''
        while chunk := os.read(fd, 65536):
            city_toml += chunk
    finally:
        os.close(fd)
    normalize = re.search(r'func normalizeInfoState\(state State\) State \{.*?\n}\n', manager_go, re.S)
    providers_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':cmd/gc/providers.go'],
                                  env=ENV, capture_output=True, text=True, timeout=60).stdout
    tmux_go = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':internal/runtime/tmux/tmux.go'],
                             env=ENV, capture_output=True, text=True, timeout=60).stdout
    session_section = city_toml.split(b'\n[session]\n', 1)[1].split(b'\n[', 1)[0]
    status = json.loads(subprocess.run(GC + ['status', '--json'], env=ENV, capture_output=True, text=True, timeout=60,
                                       stdin=subprocess.DEVNULL).stdout)
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
        worker_provider_is_claude=provider.get('name') == 'claude',
        running_state_is_active=bool(normalize) and 'case "awake":\n\t\treturn StateActive' in normalize.group(0)
        and '\tStateActive State = "active"\n' in manager_go,
        list_takes_direct_store_path=not any(line.strip().startswith(b'[api') for line in city_toml.splitlines())
        and 'if err != nil || cfg.API.Port <= 0 {\n\t\treturn nil\n\t}' in apiroute_go
        and '\t\treturn standaloneControllerClient(cityPath)\n' in apiroute_go,
        not_running_gets_a_queued_wake='\treturn !obs.Running, nil\n' in cli_go,
        tmux_socket_is_city='\tsocketName := sc.Socket\n\tif socketName == "" {\n\t\tsocketName = cityName\n\t}' in providers_go
        and not any(line.strip().startswith(b'socket') for line in session_section.splitlines())
        and status.get('city_name') == 'city' and status.get('city_path') == '/home/loucmane/gascity/city'
        and 'allArgs = append(allArgs, "-L", t.cfg.SocketName)' in tmux_go
        and 't.run("capture-pane", "-p", "-t", session, "-S"' in tmux_go)
    result['ok'] = all(result.values())
    result['emitted_signals'] = emitted
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
