"""Bounded read-only queue observer with append-only window evidence.

Never invokes nudge status or queue maintenance. It cannot restore queue data,
change Beads, start processes other than bounded read commands, or grant a
worker authority. Its sidecars do not alter the platform-observation schema.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat

WINDOW = Path('/var/tmp/ga-mb91-window-20260930-r1')
CITY = Path('/home/loucmane/gascity/city')
TASK = 'ga-mb91'
POLICY_SHA = 'e59e29fd34177936fc259bd5ef3dd11619df888a898ead8855553b863ac939a5'
CORE = '/home/loucmane/gascity/bin/gc'
CORE_CGROUP = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gascity-supervisor-home-42adab5d.service\n'


def policy(w):
    return w.module(w.HERE/'queue-preservation.py', POLICY_SHA)


def read_queue(w):
    path = CITY/'.gc/nudges/state.json'
    for parent in (CITY, CITY/'.gc', CITY/'.gc/nudges'):
        st = parent.lstat()
        w.require(parent.resolve(strict=True) == parent and stat.S_ISDIR(st.st_mode)
                  and st.st_uid == st.st_gid == 1000 and not st.st_mode & 0o022,
                  'queue parent authority')
    for attempt in range(3):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME
                         | os.O_CLOEXEC | os.O_NONBLOCK)
            try:
                st = os.fstat(fd)
                # Core's state.go writes state.json as 0644. Its separate
                # lock is 0600; never chmod either to satisfy this reader.
                w.require(stat.S_ISREG(st.st_mode) and st.st_size <= 16 << 20
                          and st.st_uid == st.st_gid == 1000 and st.st_nlink == 1
                          and stat.S_IMODE(st.st_mode) == 0o644,
                          'queue file authority or bound')
                chunks = []; remaining = st.st_size + 1
                while remaining:
                    chunk = os.read(fd, min(65536, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk); remaining -= len(chunk)
                raw = b''.join(chunks)
                w.require(st == os.fstat(fd) == path.lstat()
                          and len(raw) == st.st_size, 'file read drift')
                return raw
            finally:
                os.close(fd)
        except RuntimeError as exc:
            if str(exc) != 'file read drift' or attempt == 2:
                raise


def pollers(w, session):
    """No old/global dispatcher or foreign poller can share this window."""
    found = []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            if path.stat().st_uid != 1000:
                continue
            raw = (path/'cmdline').read_bytes()
            if not raw:
                continue
            args = raw.rstrip(b'\0').decode('utf-8', 'strict').split('\0')
            if not (len(args) >= 3 and args[1] == 'nudge'
                    and args[2] in ('poll', 'dispatch', 'dispatcher')):
                continue
            start = (path/'stat').read_text().rsplit(') ', 1)[1].split()
            w.require(session is not None and args == [CORE, 'nudge', 'poll', '--city', str(CITY),
                      '--session', session['session_name'], session['id']], 'foreign queue process')
            w.require(start[0] not in ('Z', 'X') and os.readlink(path/'exe') == CORE,
                      'queue process executable or state')
            expected = w.b_gc_sha()
            w.require(hashlib.sha256((path/'exe').read_bytes()).hexdigest() == expected,
                      'queue process image drift')
            cgroup = (path/'cgroup').read_text()
            owned_job = Path('/proc/self/cgroup').read_text()
            w.require(cgroup == CORE_CGROUP or (cgroup == owned_job and re.fullmatch(
                r'0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-[A-Za-z0-9_.-]+\.service\n', cgroup)),
                'queue process cgroup differs')
            after = (path/'stat').read_text().rsplit(') ', 1)[1].split()
            w.require(start[19] == after[19] and start[1] == after[1]
                      and raw == (path/'cmdline').read_bytes()
                      and after[0] not in ('Z', 'X'), 'queue process identity changed')
            found.append(dict(pid=int(path.name), start=start[19], argv=args, cgroup=cgroup))
        except (FileNotFoundError, ProcessLookupError):
            continue
    w.require(len(found) <= 1, 'multiple queue processes')
    return found


def checkpoint(w, label, b, o, owned_phase, *, capture=False, scoped=True, fatal=True):
    w.require(re.fullmatch(r'[a-z][a-z0-9-]{0,90}', label), 'queue checkpoint label')
    name = 'foreign-' + label
    w.require(not os.path.lexists(w.ROOT/(name+'-pass.json'))
              and not os.path.lexists(w.ROOT/(name+'-failure.json')), 'queue checkpoint consumed')
    count = 0
    p = policy(w)

    def command(kind, args):
        nonlocal count
        count += 1
        result = w.phase(name+'-'+str(count)+'-'+kind, w.GC+args, b, owned_phase, timeout=30)
        return json.loads(result['stdout'])

    def session_read():
        path = WINDOW/'foreign-owned-session.json'
        if os.path.lexists(path):
            bound = json.loads(w.read(path))
            p.bound_session(bound)
            identity = bound['id']
        else:
            census = command('sessions', ['session', 'list', '--json'])
            w.require(census.get('ok') is True and type(census.get('sessions')) is list
                      and len(census['sessions']) <= 1, 'queue census is not singleton')
            if not census['sessions']:
                return None
            row = census['sessions'][0]
            w.require(not capture and row.get('template') == 'gascity/codex'
                      and row.get('rig') == 'gascity' and row.get('provider') == 'codex-managed'
                      and row.get('work_dir') == str(w.WORK), 'queue census authority')
            identity = row['id']; bound = None
        rows = command('session-bead', ['bd', 'show', identity, '--json'])
        w.require(type(rows) is list and len(rows) == 1, 'queue session readback')
        row = rows[0]; meta = row.get('metadata', {})
        w.require(row.get('id') == identity and row.get('issue_type') == 'session'
                  and 'gc:session' in row.get('labels', [])
                  and meta.get('template') == 'gascity/codex'
                  and meta.get('provider') == 'codex-managed'
                  and meta.get('gc.trigger_bead_id') == TASK
                  and meta.get('gc.trigger_bead_store_ref') == 'rig:gascity', 'queue session authority')
        result = dict(id=identity, session_name=meta.get('session_name'),
                      continuation_epoch=meta.get('continuation_epoch'))
        p.bound_session(result)
        if bound is None:
            w.durable(path, (json.dumps(result, sort_keys=True)+'\n').encode())
        else:
            w.require(result == bound, 'queue session epoch changed')
        return result

    def observation(frozen, session):
        first = read_queue(w)
        rows = command('shadow-beads', ['bd', 'list', '--type', 'chore', '--label', 'gc:nudge',
                        '--include-infra', '--all', '--limit', str(p.LIMIT+1), '--json'])
        p.bead_records(rows)  # Full page fails; no filtered absence inference.
        last = read_queue(w)
        if frozen is None:
            w.require(first == last, 'queue changed around shadow read')
        else:
            # Owned delivery can advance while a read is in flight. Every
            # observed endpoint must preserve all frozen foreign tuples;
            # only the already-bound session may explain new records.
            p.preserve(frozen['history'], json.loads(first), rows, session)
            p.preserve(frozen['history'], json.loads(last), rows, session)
        return dict(raw_base64=base64.b64encode(last).decode('ascii'),
                    sha256=hashlib.sha256(last).hexdigest(), queue=json.loads(last), beads=rows)

    try:
        session = session_read()
        prior_pollers = pollers(w, session)
        if capture:
            w.require(session is None and not prior_pollers, 'poller existed before baseline')
        config = command('config', ['config', 'show', '--json'])
        orders = command('orders', ['order', 'list', '--json'])
        suffix = 'isolated' if scoped else 'baseline'
        expected = json.loads(w.read(w.PREP/('config.'+suffix+'.json')))
        expected_orders = json.loads(w.read(w.PREP/('orders.'+suffix+'.json')))
        if scoped:
            p.scoped_configuration(config, expected, orders, expected_orders)
        else:
            w.require(config == expected and orders == expected_orders, 'baseline config/orders drift')
        baseline_path = WINDOW/'foreign-before.json'
        frozen = None if capture else json.loads(w.read(baseline_path))
        first = observation(frozen, session); second = observation(frozen, session)
        if capture:
            w.require(first['raw_base64'] == second['raw_base64']
                      and p.bead_records(first['beads']) == p.bead_records(second['beads']),
                      'foreign observation did not stabilize')
        w.require(pollers(w, session) == prior_pollers, 'queue process changed during observation')
        w.save(name+'-observation.json', dict(second, session=session, pollers=prior_pollers))
        binding = dict(task=TASK, window=str(WINDOW), core_sha256=w.b_gc_sha(),
                       before_sha256=hashlib.sha256(w.read(WINDOW/'before.json')).hexdigest())
        if capture:
            value = dict(binding=binding, raw_base64=first['raw_base64'],
                         history=p.baseline(first['queue'], first['beads']))
            w.durable(baseline_path, (json.dumps(value, sort_keys=True)+'\n').encode())
        frozen = json.loads(w.read(baseline_path))
        w.require(frozen['binding'] == binding, 'foreign baseline binding drift')
        result = p.preserve(frozen['history'], second['queue'], second['beads'], session)
        # A transient violation may never be hidden by a later clean sample.
        w.require(not list(WINDOW.glob('foreign-*-failure.json')), 'prior foreign preservation failure')
        w.save(name+'-pass.json', dict(result, baseline_sha256=hashlib.sha256(w.read(baseline_path)).hexdigest()))
        return result
    except Exception as exc:
        evidence = dict(error=str(exc), queue_or_beads_restored=False, replay=False)
        w.save(name+'-failure.json', evidence)
        if w.ROOT != WINDOW:
            w.durable(WINDOW/(name+'-failure.json'), (json.dumps(evidence, sort_keys=True)+'\n').encode())
        # Containment must still suspend both levels. Failure remains sticky and
        # prevents restoration admission/terminal acceptance. Nothing is erased.
        if fatal:
            raise
        return dict(ok=False, containment_only=True)
