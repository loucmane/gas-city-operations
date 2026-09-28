"""Read-only in-window observation of the ga-e0t1.20 worker; one fresh root per run, never mutates.

Runs as a job of the host job runner (operator/WATCH.sh), in the supervisor namespaces, so its process
and tmux reads see the real host rather than a sandbox view. Adapted from the ga-y49e
observe-worker-create-r2.py observation (native sessions, task, trace, git, tmux, processes), over
window-base-r11.py. Each run creates /var/tmp/ga-e0t1.20-r4-watch-<UTC>/ exclusively and records:
- native sessions, the task Bead and every session Bead of the template or task;
- the template trace for the last 30 minutes;
- no git state: the Template variant runs no git while the worker is live (s1 r2), so HEAD, branch,
  status and diffs are recorded as empty and read after containment instead;
- an empty inventory (the Template variant walks no worktree path), the task note markers and the
  Template .git/config digest (a non-blocking, bounded read of a plain file only);
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
            '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/window-base-r11.py')
BASE_SHA = '4f5ceea3159f1f9a70a615ad543dc1a441dda7076e5362ebeb9821d43926cecb'
TASK = 'ga-e0t1.20'
WINDOW = Path('/var/tmp/ga-e0t1.20-window-20260928-r4')
VAR = Path('/var/tmp')
TEMPLATE = 'gascity/codex'
EVIDENCE = '.gc/worker-evidence/ga-e0t1.20'
# ga-gegx s2: nudge-on-route evidence. The order records each (bead, routed_to) pair it nudged in its
# pack state file; Core keeps a nudge it could not deliver at once in the flock'd queue file.
ORDER_STATE = Path('/home/loucmane/gascity/city/.gc/runtime/packs/core/nudge-on-route-state.json')
ORDER_KEY = TASK + '|' + TEMPLATE
NUDGE_QUEUE = Path('/home/loucmane/gascity/city/.gc/nudges/state.json')
EVIDENCE_LIMIT = 1 << 20


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
        bound = w.read_time_bounds(json.loads(w.read(WINDOW/'before.json'))['cache_access_clock'])
        w.save('read-route-observation.json',dict(before=after,after=now,window=bound))
        now = w.route_read_account(after,now,bound)
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
        baseline = json.loads(w.read(before_path))
        bound = w.read_time_bounds(baseline['cache_access_clock'])
        raw = json.loads(json.dumps(dict(before=a,after=z,window=bound)))
        w.save('read-directory-observation.json',raw)
        # Check read eligibility against the real post-reload parent times,
        # before the existing diagnostic-only route normalization below.
        z['city']['.beads'], parent_reads = w.read_time_policy().metadata(
            str(w.CITY/'.beads'),a['city']['.beads'],z['city']['.beads'],bound,renamed=True)
        routes = z['runtime_children'].get('.beads', {}).get('routes.jsonl')
        if routes is not None and 'routes.jsonl' in a['runtime_children'].get('.beads', {}):
            routes['inode'] = a['runtime_children']['.beads']['routes.jsonl']['inode']
        for key in ('mtime_ns', 'ctime_ns'):
            z['city']['.beads'][key] = a['city']['.beads'][key]
        reads = w.account_read_times(dict(directories=a),dict(directories=z),bound)
        w.read_time_evidence('directories',raw['before'],raw['after'],parent_reads+reads,bound)
        w.directory_preservation(a, z, read_window=bound)
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


def evidence_file(path, attempts=3):
    """One read-only evidence file: (decoded JSON or None, 'ok' | 'absent' | the error text).

    bounded_read checks the open descriptor (regular, uid 1000, one link, at most EVIDENCE_LIMIT bytes,
    unchanged while read) and never touches the access time. Both writers replace their file by rename, so a
    read that races a rename sees an unlinked or changed inode and is tried again, up to `attempts` times.
    """
    error = None
    for _ in range(attempts):
        try:
            return json.loads(bounded_read(path, EVIDENCE_LIMIT)), 'ok'
        except FileNotFoundError:
            return None, 'absent'
        except (OSError, RuntimeError, ValueError) as exc:
            error = '%s: %s' % (type(exc).__name__, exc)
    return None, error


def nudge_evidence():
    """Read-only nudge-on-route evidence: the order's recorded pair for the task and Core's queued nudges.

    Evidence only. Every read or decode error is recorded, and nothing here refuses a WATCH.
    """
    value = dict(order_pair=None, order_state=None, queue=None, queued=None, pending=[], in_flight=[], dead=None)
    state, value['order_state'] = evidence_file(ORDER_STATE)
    if isinstance(state, dict):
        value['order_pair'] = state.get(ORDER_KEY)
    elif value['order_state'] == 'ok':
        value['order_state'] = 'unexpected shape: ' + type(state).__name__
    queue, value['queue'] = evidence_file(NUDGE_QUEUE)
    if isinstance(queue, dict):
        try:
            for kind in ('pending', 'in_flight'):
                value[kind] = [dict(id=i.get('id'), agent=i.get('agent'), session_id=i.get('session_id'),
                                    source=i.get('source'), message=i.get('message'),
                                    deliver_after=i.get('deliver_after'), attempts=i.get('attempts'))
                               for i in queue.get(kind) or []]
            value['dead'] = len(queue.get('dead') or [])
            value['queued'] = len(value['pending']) + len(value['in_flight'])
        except (AttributeError, TypeError) as exc:
            value.update(queue='unexpected shape: %s' % exc, pending=[], in_flight=[], queued=None, dead=None)
    elif value['queue'] == 'ok':
        value['queue'] = 'unexpected shape: ' + type(queue).__name__
    return value


def main():
    w = load()
    w.require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound source launcher required')
    w.read(Path(__file__), _SOURCE_SHA)
    b, o, owned = w.load_support()
    root = VAR/('ga-e0t1.20-r4-watch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))

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
    # Template variant (s1 r2): no git runs against the worktree while the codex worker is live. Its
    # sandbox can write the worktree root, and a relaunch through an opt_ override could restore the
    # Template .git, so any coordinator git call here could run a driver or command it chose. The
    # task notes (READY FOR SIGNING / ESCALATED / STOPPED) are the signal.
    head = branch = None
    status = staged = ''
    run('tmux', ['/usr/bin/tmux', '-L', 'city', 'list-panes', '-a', '-F', '#{session_name} #{pane_pid} #{pane_dead}'],
        expected=(0, 1))
    # ga-gegx: the visible pane of each live session, captured the way Core captures it (release-r11
    # pane_clear form), read-only. The ga-4z38 worker went silent and was reaped before any capture; the
    # early WATCH slots after RESUME keep the screen as evidence. Exit 1 (pane gone) is recorded, not fatal,
    # and a listed session without a string session_name is recorded, never captured.
    unnamed = []
    for index, live in enumerate(sessions.get('sessions') or []):
        name = live.get('session_name') if isinstance(live, dict) else None
        if not isinstance(name, str) or not name:
            unnamed.append(index)
            continue
        run('pane-%d' % index, ['/usr/bin/tmux', '-u', '-L', 'city', 'capture-pane', '-p', '-t', name],
            expected=(0, 1))
    w.save('pane-unnamed.json', unnamed)
    nudge = nudge_evidence()
    w.save('nudge.json', nudge)
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
                roots = [arg.split(b'=', 1)[1].decode(errors='replace') for arg in argv
                         if arg.startswith(b'sandbox_workspace_write.writable_roots=')]
                processes.append(dict(pid=int(proc.name), cwd=cwd, git_optional_locks_zero=locks, writable_roots=roots,
                                      argv=redacted([arg.decode(errors='replace') for arg in argv if arg])))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    records = [r for r in status.split('\0') if r]
    untracked = [r[3:] for r in records if r.startswith('?? ')]
    inventory = dict(untracked=[], evidence=[])
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
    def meta(v):
        return v.get('metadata') if isinstance(v.get('metadata'), dict) else {}
    def overrides(metadata):
        if not isinstance(metadata, dict):
            return ['<metadata is not an object>']
        return sorted(k for k in metadata if k.startswith('opt_') or k.startswith('template_override'))
    override_keys = dict(task=overrides(bead.get('metadata')),
                         sessions={str(v.get('id')): overrides(v.get('metadata')) for v in census if isinstance(v, dict)
                                   if overrides(v.get('metadata')) and (meta(v).get('template') == TEMPLATE
                                   or meta(v).get('gc.work_dir') == str(w.WORK))})
    process_roots = sorted({root for p in processes for root in p['writable_roots']})
    notes = bead.get('notes') or ''
    markers = [line[:300] for line in notes.splitlines()
               if 'READY FOR SIGNING:' in line or 'ESCALATED:' in line or 'STOPPED:' in line][-5:]
    try:
        fd = os.open('/home/loucmane/gas-city-ops/.git/config',
                     os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC | os.O_NONBLOCK)
        try:
            s = os.fstat(fd)
            if not (stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1 and s.st_size <= 1 << 20):
                template_config = 'not a plain file: mode %o nlink %d size %d' % (s.st_mode, s.st_nlink, s.st_size)
            else:
                data = b''
                while len(data) <= 1 << 20 and (chunk := os.read(fd, 65536)):
                    data += chunk
                template_config = hashlib.sha256(data).hexdigest() if len(data) == s.st_size else 'size changed'
        finally:
            os.close(fd)
    except OSError as exc:
        template_config = 'unreadable: %s' % exc.__class__.__name__
    result = dict(ok=True, mutation=False, head=head, branch=branch, note_markers=markers,
                  template_git_config_sha256=template_config, override_keys=override_keys,
                  process_writable_roots=process_roots,
                  status_records=records, staged=staged.splitlines(),
                  live_sessions=sessions.get('sessions'), related_session_beads=related,
                  task=dict(status=bead['status'], assignee=bead.get('assignee'),
                            metadata=bead.get('metadata') or {}),
                  matching_processes=len(processes), routes_unchanged_since_stage=routes_unchanged,
                  runtime_children_unchanged_since_preflight=children_unchanged,
                  directories_pass_admission_check=directories_unchanged,
                  order_nudge_recorded=nudge['order_pair'] is not None, queued_nudges=nudge['queued'])
    w.save('result.json', result)
    print(json.dumps(dict(ok=True, root=str(root), head=head, status_records=len(records),
                          live_sessions=len(result['live_sessions'] or []), matching_processes=len(processes),
                          routes_unchanged_since_stage=routes_unchanged,
                          runtime_children_unchanged_since_preflight=children_unchanged,
                          directories_pass_admission_check=directories_unchanged,
                          order_nudge_recorded=result['order_nudge_recorded'], queued_nudges=nudge['queued'])))


if __name__ == '__main__':
    main()
