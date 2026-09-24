"""Read-only in-window observation of the ga-f37t worker; one fresh root per run, never mutates.

Runs as a job of the host job runner (operator/WATCH.sh), in the supervisor namespaces, so its git,
process and tmux reads see the real host rather than a sandbox view. Adapted from the ga-y49e
observe-worker-create-r2.py observation (native sessions, task, trace, git, tmux, processes), over
window-base-r11.py. Each run creates /var/tmp/ga-f37t-watch-<UTC>/ exclusively and records:
- native sessions, the task Bead and every session Bead of the template or task;
- the template trace for the last 30 minutes;
- worktree HEAD, branch, full status, unstaged and staged diffs, and the staged patch;
- an inventory of every untracked path and every evidence file (kind, mode, owner, size, SHA256,
  link target);
- city tmux panes and the processes whose argv names the worktree or whose cwd is inside it, each with
  one boolean: whether its environment carries GIT_OPTIONAL_LOCKS=0 (nothing else from the environment is
  read into evidence);
- the live host identity through the base active_epoch() check, which is the lifecycle check made for a
  running worker (the quiescent host observer refuses while the worker is live), bound to the window
  before.json.
Every command runs through the owned-phase runner with the support environment (GIT_OPTIONAL_LOCKS=0).
It asserts only containment and the active epoch; everything else is evidence for the coordinator.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-f37t-window/window-base-r11.py')
BASE_SHA = 'fb9dd9fa93d57337c784af773520f8ec888d9c073ff452e6bf3688a012d9a23a'
TASK = 'ga-f37t'
WINDOW = Path('/var/tmp/ga-f37t-window-20260923-r1')
VAR = Path('/var/tmp')
TEMPLATE = 'gascity/gc.implementation-worker'
EVIDENCE = '.gc/worker-evidence/ga-f37t'


def load():
    fd = os.open(BASE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1
        raw = b''
        while chunk := os.read(fd, 65536):
            raw += chunk
        assert os.fstat(fd) == s and hashlib.sha256(raw).hexdigest() == BASE_SHA, 'base source drift'
    finally:
        os.close(fd)
    w = types.ModuleType('watch_base')
    w.__file__ = str(BASE)
    exec(compile(raw, str(BASE), 'exec', dont_inherit=True), w.__dict__)
    return w


KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
# Inside a command string: KEY= then a value made of quoted and unquoted runs up to unquoted whitespace.
ASSIGNMENT = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=(?:\'[^\']*\'?|"[^"]*"?|[^\s\'"]+)*')


def redacted(argv):
    """argv with every assigned value removed; only key names stay. Core writes each tmux -e element as
    one argv entry KEY=VALUE whatever VALUE holds (tmux.go new-session), and expects `exec env KEY=VALUE`
    in the pane command string. So: the element after -e, an -eKEY=VALUE element and any element that is
    itself KEY=VALUE lose everything after the first '='; inside any other element, each KEY= loses its
    value up to the next unquoted whitespace, quoted runs included."""
    out, value_next = [], False
    for arg in argv:
        whole = KEY.match(arg)
        if value_next or (whole and arg[whole.end():whole.end() + 1] == '='):
            out.append(arg.split('=', 1)[0] + '=<redacted>' if '=' in arg else '<redacted>')
        elif arg.startswith('-e') and '=' in arg:
            out.append(arg.split('=', 1)[0] + '=<redacted>')
        else:
            out.append(ASSIGNMENT.sub(lambda m: m.group(1) + '=<redacted>', arg))
        value_next = arg == '-e'
    return out


def routes_since_stage(w, o, routes, stage_event):
    """None before STAGE; True when the route files still equal the stage-reload after-capture (what
    ADMIT requires exactly, route-chain-r1); otherwise the sorted differing fields, or the refusal."""
    if not stage_event.exists():
        return None
    try:
        now = routes.capture_routes(w, o)
        after = json.loads(w.read(stage_event))['after']
        return now == after or sorted(
            '%s %s.%s' % (root, section, key) for root in after for section in ('metadata', 'parent')
            for key in set(after[root][section]) | set(now[root][section])
            if after[root][section].get(key) != now[root][section].get(key))
    except Exception as exc:  # any refusal or read error is recorded, since WATCH only observes
        return 'refused: ' + str(exc)


def bounded_read(path, limit):
    """A worker-written file: regular, uid 1000, one link and at most `limit` bytes, checked on the open
    descriptor (no lstat-then-open race), read without touching its atime. Raises OSError or RuntimeError."""
    # O_NONBLOCK: a FIFO planted at the path must not block the open; fstat then refuses it.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        if not (stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1 and s.st_size <= limit):
            raise RuntimeError('worker file shape or size: ' + Path(path).name)
        raw = os.read(fd, limit + 1)
        if len(raw) != s.st_size or os.fstat(fd) != s:
            raise RuntimeError('worker file changed while read: ' + Path(path).name)
    finally:
        os.close(fd)
    return raw


IDENTITY = ('device', 'inode', 'type', 'uid', 'gid', 'mode')


def runtime_children_since_before(w, o, before_path):
    """None before PREFLIGHT's before.json; True when the city .gc and .beads direct children keep the
    names and identities ADMIT requires (window-base-r11 directory_preservation); otherwise the sorted
    differences, or the refusal. The routes.jsonl inode is left to the route check, since STAGE's reload
    regenerates that file and the route chain accounts for it."""
    if not before_path.exists():
        return None
    try:
        before = json.loads(w.read(before_path))['directories']['runtime_children']
        now = w.directories(o)['runtime_children']
        found = []
        for name in ('.gc', '.beads'):
            then, current = before.get(name, {}), now.get(name, {})
            found += ['%s/%s %s' % (name, child, 'added' if child in current else 'removed')
                      for child in sorted(set(then) ^ set(current))]
            found += ['%s/%s %s' % (name, child, key) for child in sorted(set(then) & set(current)) for key in IDENTITY
                      if then[child].get(key) != current[child].get(key)
                      and not (name == '.beads' and child == 'routes.jsonl' and key == 'inode')]
        return not found or found
    except Exception as exc:  # any refusal or read error is recorded, since WATCH only observes
        return 'refused: ' + str(exc)


def directories_since_before(w, o, before_path):
    """None before PREFLIGHT's before.json; True when the city directories pass the base
    directory_preservation that ADMIT's preservation applies (full metadata of every city child, the
    provisioning inventory, runtime child names and identities), after the one alignment the route chain
    makes for STAGE's reload (routes.jsonl inode, .beads mtime and ctime; route-chain-r1 project);
    otherwise the refusal. Evidence only: the WATCH after CLOSE is the one that matters for ADMIT."""
    if not before_path.exists():
        return None
    try:
        a = json.loads(json.dumps(json.loads(w.read(before_path))['directories']))
        z = json.loads(json.dumps(w.directories(o)))
        routes = z['runtime_children'].get('.beads', {}).get('routes.jsonl')
        if routes is not None and 'routes.jsonl' in a['runtime_children'].get('.beads', {}):
            routes['inode'] = a['runtime_children']['.beads']['routes.jsonl']['inode']
        for key in ('mtime_ns', 'ctime_ns'):
            z['city']['.beads'][key] = a['city']['.beads'][key]
        w.directory_preservation(a, z)
        return True
    except Exception as exc:  # any refusal or read error is recorded, since WATCH only observes
        return 'refused: ' + str(exc)


def entry(w, path):
    try:
        s = path.lstat()
    except OSError as exc:
        return dict(path=str(path), lstat_error=str(exc))
    row = dict(path=str(path), mode=oct(stat.S_IMODE(s.st_mode)), uid=s.st_uid, gid=s.st_gid, size=s.st_size)
    if stat.S_ISLNK(s.st_mode):
        row.update(kind='symlink', target=os.readlink(path))
    elif stat.S_ISREG(s.st_mode):
        row['kind'] = 'file'
        try:
            row['sha256'] = w.digest(bounded_read(path, 1 << 20))
        except Exception as exc:  # recorded, not fatal: this is an observation (too large included)
            row['read_error'] = str(exc)
    elif stat.S_ISDIR(s.st_mode):
        row['kind'] = 'directory'
    else:
        row.update(kind='other', device=s.st_rdev)
    return row


def main():
    w = load()
    w.require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound source launcher required')
    w.read(Path(__file__), _SOURCE_SHA)
    b, o, owned = w.load_support()
    root = VAR/('ga-f37t-watch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))

    def epoch():
        # active_epoch() reads the window before.json through the base ROOT.
        w.ROOT = WINDOW
        try:
            w.active_epoch(o)
        finally:
            w.ROOT = root
    w.require((WINDOW/'preflight-pass.json').exists(), 'watch observes a preflighted window only')
    root.mkdir(mode=0o700)
    epoch()

    def run(name, args, expected=(0,)):
        return w.phase(name, args, b, owned, expected=expected, timeout=90)

    sessions = json.loads(run('sessions', w.GC + ['session', 'list', '--json'])['stdout'])
    task = json.loads(run('task', w.GC + ['--rig', 'gascity', 'bd', 'show', TASK, '--json'])['stdout'])
    census = json.loads(run('session-beads', w.GC + ['bd', 'list', '--type', 'session', '--include-infra', '--all',
                                                    '--json', '--limit', '0'])['stdout'])
    run('trace', w.GC + ['trace', 'show', '--template', TEMPLATE, '--since', '30m', '--json'])
    git = ['/usr/bin/git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(w.WORK)]
    head = run('git-head', git + ['rev-parse', 'HEAD'])['stdout'].strip()
    branch = run('git-branch', git + ['branch', '--show-current'])['stdout'].strip()
    # -z: NUL-separated, never quoted, so every untracked path is exact.
    status = run('git-status', git + ['status', '--porcelain=v1', '-z', '--untracked-files=all'])['stdout']
    # Plumbing only: diff-files and diff-index never refresh or lock the worker's index, so a WATCH can
    # never collide with the worker's own staging or signing.
    run('git-diff', git + ['diff-files', '--patch', '--exit-code'], expected=(0, 1))
    run('git-staged', git + ['diff-index', '--cached', '--patch', '--exit-code', 'HEAD'], expected=(0, 1))
    staged = run('git-staged-names', git + ['diff-index', '--cached', '--name-status', 'HEAD'])['stdout']
    run('tmux', ['/usr/bin/tmux', '-L', 'city', 'list-panes', '-a', '-F', '#{session_name} #{pane_pid} #{pane_dead}'],
        expected=(0, 1))
    processes = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != 1000:
                continue
            argv = (proc/'cmdline').read_bytes().split(b'\0')
            try:
                cwd = os.readlink(proc/'cwd')
            except OSError:
                cwd = ''
            # The worktree path only: this observer's own argv names the package, not the worktree.
            if any(str(w.WORK).encode() in arg for arg in argv) or cwd == str(w.WORK) \
                    or cwd.startswith(str(w.WORK) + '/'):
                try:
                    locks = b'GIT_OPTIONAL_LOCKS=0' in (proc/'environ').read_bytes().split(b'\0')
                except OSError:
                    locks = None
                processes.append(dict(pid=int(proc.name), cwd=cwd, git_optional_locks_zero=locks,
                                      argv=redacted([arg.decode(errors='replace') for arg in argv if arg])))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    records = [r for r in status.split('\0') if r]
    untracked = [r[3:] for r in records if r.startswith('?? ')]
    inventory = dict(untracked=[entry(w, w.WORK/path) for path in untracked], evidence=[])
    evidence = w.WORK/EVIDENCE
    if evidence.is_dir() and not evidence.is_symlink():
        for dirpath, dirnames, filenames in os.walk(evidence):
            dirnames.sort()
            for name in sorted(filenames):
                inventory['evidence'].append(entry(w, Path(dirpath)/name))
    w.save('processes.json', processes)
    w.save('inventory.json', inventory)
    epoch()
    # Early warning for ADMIT: the route files must still equal the stage-reload after-capture
    # (route-chain-r1 compares them exactly). Evidence only; O_NOATIME reads.
    routes = w.module(BASE.parent/'restore-r9-routes-r3.py', '8d041af74297b44c0bedecdbcaa776ac92f433eba801afa0ee0a89a71eecc7c2')
    routes_unchanged = routes_since_stage(w, o, routes, WINDOW/'stage-reload-generated-routes.json')
    children_unchanged = runtime_children_since_before(w, o, WINDOW/'before.json')
    directories_unchanged = directories_since_before(w, o, WINDOW/'before.json')
    w.complete_containment()
    related = [dict(id=v['id'], status=v['status'], state=(v.get('metadata') or {}).get('state'),
                    template=(v.get('metadata') or {}).get('template'))
               for v in census
               if (v.get('metadata') or {}).get('template') == TEMPLATE
               or (v.get('metadata') or {}).get('gc.trigger_bead_id') == TASK
               or (v.get('metadata') or {}).get('gc.work_dir') == str(w.WORK)]
    [bead] = task
    result = dict(ok=True, mutation=False, head=head, branch=branch,
                  status_records=records, staged=staged.splitlines(),
                  live_sessions=sessions.get('sessions'), related_session_beads=related,
                  task=dict(status=bead['status'], assignee=bead.get('assignee'),
                            metadata=bead.get('metadata') or {}),
                  matching_processes=len(processes), routes_unchanged_since_stage=routes_unchanged,
                  runtime_children_unchanged_since_preflight=children_unchanged,
                  directories_pass_admission_check=directories_unchanged)
    w.save('result.json', result)
    print(json.dumps(dict(ok=True, root=str(root), head=head, status_records=len(records),
                          live_sessions=len(result['live_sessions'] or []), matching_processes=len(processes),
                          routes_unchanged_since_stage=routes_unchanged,
                          runtime_children_unchanged_since_preflight=children_unchanged,
                          directories_pass_admission_check=directories_unchanged)))


if __name__ == '__main__':
    main()
