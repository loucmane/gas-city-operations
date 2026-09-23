"""Read-only in-window observation of the ga-4z38 worker; one fresh root per run, never mutates.

Runs as a job of the host job runner (operator/WATCH.sh), in the supervisor namespaces, so its git,
process and tmux reads see the real host rather than a sandbox view. Adapted from the ga-y49e
observe-worker-create-r2.py observation (native sessions, task, trace, git, tmux, processes), over
window-base-r11.py. Each run creates /var/tmp/ga-4z38-watch-<UTC>/ exclusively and records:
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
import stat
import types

BASE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-4z38-window/window-base-r11.py')
BASE_SHA = 'cad1d660b872a352bce7e8c3c5bffda5ca7ac663a732575f48a3b7a9847926cd'
TASK = 'ga-4z38'
WINDOW = Path('/var/tmp/ga-4z38-window-20260923-r1')
TEMPLATE = 'gascity/gc.implementation-worker'
EVIDENCE = '.gc/worker-evidence/ga-4z38'


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


def entry(w, path):
    s = path.lstat()
    row = dict(path=str(path), mode=oct(stat.S_IMODE(s.st_mode)), uid=s.st_uid, gid=s.st_gid, size=s.st_size)
    if stat.S_ISLNK(s.st_mode):
        row.update(kind='symlink', target=os.readlink(path))
    elif stat.S_ISREG(s.st_mode):
        row['kind'] = 'file'
        try:
            row['sha256'] = w.digest(w.read(path))
        except Exception as exc:  # recorded, not fatal: this is an observation
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
    root = Path('/var/tmp/ga-4z38-watch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))

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
    git = ['/usr/bin/git', '-C', str(w.WORK)]
    head = run('git-head', git + ['rev-parse', 'HEAD'])['stdout'].strip()
    branch = run('git-branch', git + ['branch', '--show-current'])['stdout'].strip()
    status = run('git-status', git + ['status', '--porcelain=v1', '--untracked-files=all'])['stdout']
    run('git-diff', git + ['diff', '--exit-code'], expected=(0, 1))
    run('git-staged', git + ['diff', '--cached', '--exit-code'], expected=(0, 1))
    staged = run('git-staged-names', git + ['diff', '--cached', '--name-status'])['stdout']
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
                                      argv=[arg.decode(errors='replace') for arg in argv if arg]))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    untracked = [line[3:] for line in status.splitlines() if line.startswith('?? ')]
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
    w.complete_containment()
    related = [dict(id=v['id'], status=v['status'], state=(v.get('metadata') or {}).get('state'),
                    template=(v.get('metadata') or {}).get('template'))
               for v in census
               if (v.get('metadata') or {}).get('template') == TEMPLATE
               or (v.get('metadata') or {}).get('gc.trigger_bead_id') == TASK
               or (v.get('metadata') or {}).get('gc.work_dir') == str(w.WORK)]
    [bead] = task
    result = dict(ok=True, mutation=False, head=head, branch=branch,
                  status_lines=status.splitlines(), staged=staged.splitlines(),
                  live_sessions=sessions.get('sessions'), related_session_beads=related,
                  task=dict(status=bead['status'], assignee=bead.get('assignee'),
                            metadata=bead.get('metadata') or {}),
                  matching_processes=len(processes))
    w.save('result.json', result)
    print(json.dumps(dict(ok=True, root=str(root), head=head, status_lines=len(result['status_lines']),
                          live_sessions=len(result['live_sessions'] or []), matching_processes=len(processes))))


if __name__ == '__main__':
    main()
