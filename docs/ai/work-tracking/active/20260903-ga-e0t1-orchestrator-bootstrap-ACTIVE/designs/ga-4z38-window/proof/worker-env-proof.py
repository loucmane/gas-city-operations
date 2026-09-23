"""Read-only proof, before ROUTE, that the worker's gc calls inherit GIT_OPTIONAL_LOCKS=0.

Every gc config load runs `git status --porcelain` in the pack cache (Core
internal/config/pack_include.go validateLockedRemoteCache), and without GIT_OPTIONAL_LOCKS=0 that can
rewrite the cache index and move the cache .git times the window compares exactly. The worker calls gc
from its hooks, its claim and its drain-ack. This proof checks each link of the inheritance chain:
1. The live supervisor (the P6 accepted host pid) carries GIT_OPTIONAL_LOCKS=0. Only that one entry is
   tested; nothing else from its environment is read into the result.
2. Core at the worker base e6366b9e (the PR 45 merge the installed gc 69d00186 was built from):
   - no non-test Go source names GIT_OPTIONAL_LOCKS (the only mention is the docsync test of the
     supervisor's cache-readonly systemd drop-in that sets it), so nothing sets or unsets it by name;
     the tmux paths below show the session environment is not rebuilt from scratch;
   - the tmux executor runs `tmux` without a custom environment, so the city tmux server inherits the
     supervisor's environment;
   - a new session unsets only keys whose composed value is empty, so an inherited key the session
     map never names stays in the pane environment.
3. The Template signing wrapper builds the Claude environment from its parent's, removing only
   ANTHROPIC_API_KEY.
All reads are git object reads (GIT_OPTIONAL_LOCKS=0) and O_NOATIME file reads, so running it changes no
compared access time. The live pane environment is observed in-window by WATCH (one boolean).
Nothing is written.

Usage: python3 -B worker-env-proof.py   (prints one JSON object; exit 0 only if every link holds)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

P6_AFTER = Path('/var/tmp/gct-m1wh-p6-adoption-20260923-r2/after.json')
CORE = '/home/loucmane/gascity-core-worktrees/ga-4z38-typed-route-cycles'
BASE = 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88'
WRAPPER = Path('/home/loucmane/gas-city-template/lib/gct_claude_subscription.py')
ENV = dict(PATH='/usr/local/bin:/usr/bin:/bin', HOME='/home/loucmane', GIT_OPTIONAL_LOCKS='0', LC_ALL='C.UTF-8')


def git(*args, ok=(0,)):
    p = subprocess.run(['/usr/bin/git', '-C', CORE, *args], env=ENV, capture_output=True, text=True, timeout=60)
    assert p.returncode in ok, (args, p.stderr[-300:])
    return p


def main():
    host = json.loads(P6_AFTER.read_text())['host']['host']
    pid = host['pid']
    environ = Path('/proc/%d/environ' % pid).read_bytes().split(b'\0')
    stat = Path('/proc/%d/stat' % pid).read_text().rsplit(') ', 1)[1].split()
    supervisor = dict(pid=pid, start_matches=stat[19] == host['start'],
                      git_optional_locks_zero=b'GIT_OPTIONAL_LOCKS=0' in environ)
    grep = git('grep', '-n', 'GIT_OPTIONAL_LOCKS', BASE, '--', '*.go', ':(exclude)*_test.go', ok=(0, 1))
    dropin = git('grep', '-n', 'Environment=GIT_OPTIONAL_LOCKS=0', BASE, '--', 'test/docsync/cache_readonly_dropin_test.go',
                 ok=(0, 1))
    tmux = git('show', BASE + ':internal/runtime/tmux/tmux.go').stdout
    executor = re.search(r'func \(realExecutor\) executeCtx\(.*?\n}\n', tmux, re.S)
    session = re.search(r'func \(t \*Tmux\) NewSessionWithCommandAndEnv\(.*?\n}\n', tmux, re.S)
    core = dict(no_go_source_mentions=grep.returncode == 1, supervisor_dropin_is_documented=dropin.returncode == 0,
                executor_inherits=bool(executor) and 'exec.CommandContext(ctx, "tmux", args...)' in executor.group(0)
                and '.Env' not in executor.group(0),
                session_unsets_only_empty=bool(session) and 'if env[k] == "" {' in session.group(0)
                and session.group(0).count('unsetKeys = append(') == 1)
    fd = os.open(WRAPPER, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        text = os.read(fd, 1 << 20).decode()
    finally:
        os.close(fd)
    function = re.search(r'def subscription_environment\(.*?\n    return child\n', text, re.S)
    wrapper = dict(removes_only_api_key=bool(function) and 'REMOVED_CREDENTIAL = "ANTHROPIC_API_KEY"' in text
                   and 'if name == REMOVED_CREDENTIAL:\n            continue' in function.group(0)
                   and 'child[name] = value' in function.group(0))
    result = dict(supervisor=supervisor, core=core, wrapper=wrapper)
    result['ok'] = all(v for part in result.values() for v in part.values() if isinstance(v, bool))
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
