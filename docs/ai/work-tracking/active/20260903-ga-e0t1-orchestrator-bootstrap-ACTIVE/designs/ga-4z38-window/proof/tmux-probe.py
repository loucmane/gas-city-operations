"""Proof, before ROUTE, of the host tmux answers CLOSE relies on, on a throwaway socket (never `city`).

CLOSE reads the city server with `list-sessions` and ends an empty server with `kill-server`. This
starts a private server on the socket ga4z38-tmux-probe, with exit-empty off as Core sets it, and
records the answers of `list-sessions` and `list-panes -a` with one session, with none, and after
`kill-server`. It then removes its own socket file. Nothing else is touched.

Expected on this host (tmux 3.4): an empty live server answers `list-sessions` with exit 0 and no
output, and `list-panes -a` with exit 1 and "no current target" (Core internal/runtime/tmux wrapError
reads that answer as a live empty server). After `kill-server`, both answer "no server running".

Usage: python3 -B tmux-probe.py   (prints one JSON object; exit 0 only if every answer is as expected)
"""
import json
import os
import stat
import subprocess
import sys

SOCKET = 'ga4z38-tmux-probe'
PATH = '/tmp/tmux-%d/%s' % (os.getuid(), SOCKET)
TMUX = ['/usr/bin/tmux', '-u', '-f', '/dev/null', '-L', SOCKET]


def run(*args):
    p = subprocess.run(TMUX + list(args), capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL,
                       env=dict(PATH='/usr/bin:/bin', HOME=os.environ.get('HOME', '/tmp'), LC_ALL='C.UTF-8'))
    return dict(exit=p.returncode, stdout=p.stdout, stderr=p.stderr.strip())


def main():
    if os.path.lexists(PATH):
        print(json.dumps(dict(ok=False, error='probe socket already exists: ' + PATH)))
        return 1
    seen = {}
    try:
        seen['create'] = run('new-session', '-d', '-s', 'probe', '-c', '/tmp', 'sleep 300')
        seen['exit_empty_off'] = run('set-option', '-g', 'exit-empty', 'off')
        seen['one_sessions'] = run('list-sessions', '-F', '#{session_name}')
        seen['kill_session'] = run('kill-session', '-t', 'probe')
        seen['empty_sessions'] = run('list-sessions', '-F', '#{session_name}')
        seen['empty_panes'] = run('list-panes', '-a', '-F', '#{session_name} #{pane_pid}')
    finally:
        seen['kill_server'] = run('kill-server')
        seen['after_sessions'] = run('list-sessions', '-F', '#{session_name}')
        try:
            s = os.lstat(PATH)
            if stat.S_ISSOCK(s.st_mode) and s.st_uid == os.getuid():
                os.unlink(PATH)
        except FileNotFoundError:
            pass
    version = subprocess.run(['/usr/bin/tmux', '-V'], capture_output=True, text=True).stdout.strip()
    result = dict(
        version=version,
        one_session_listed=seen['one_sessions'] == dict(exit=0, stdout='probe\n', stderr=''),
        empty_server_lists_no_session=seen['empty_sessions'] == dict(exit=0, stdout='', stderr=''),
        empty_server_panes_no_current_target=seen['empty_panes']['exit'] == 1
        and seen['empty_panes']['stderr'] == 'no current target',
        killed=seen['kill_server']['exit'] == 0,
        after_kill_no_server=seen['after_sessions']['exit'] == 1
        and 'no server running' in seen['after_sessions']['stderr'],
        socket_removed=not os.path.lexists(PATH))
    result['ok'] = all(v for k, v in result.items() if k != 'version')
    result['seen'] = seen
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
