"""Successor closure: all accepted pins retained, named metadata pair separate.

Only the installed image/epoch already accepted by R7 is used as predecessor.
The native FINAL verifier alone accepts the two metadata outputs after commit.
"""
import hashlib
import os
from pathlib import Path
import stat
import subprocess

GC_BIN = '/home/loucmane/gascity/bin/gc'
DOLT_BIN = '/home/loucmane/gascity/bin/dolt'
DOLT_CFG = '/home/loucmane/gascity/city/.gc/runtime/packs/dolt/dolt-config.yaml'
DOLT_LOG = '/home/loucmane/gascity/city/.gc/runtime/packs/dolt/dolt.log'
CITY = '/home/loucmane/gascity/city'


def install_policy(o, s, old_image):
    """ga-e0t1.15 S3: the two reviewed S2 policies, installed before any observation (PLAN-S3.md).

    1. Access-time neutral inventories (operator decision 2026-09-25, "Relax it"; S2 overrides block 0).
       Every metadata record and tree inventory omits atime_ns. Path set, type, mode, uid, gid, size,
       inode, device, nlink, mtime, ctime and content digests stay exact. An unprivileged process can
       only backdate an atime with utimensat, which also changes ctime, and ctime is still exact.
    2. Dolt-aware quiet scope (S2 overrides block 2). Since the 2026-09-24 boot the managed dolt
       watchdog and server run inside the supervisor unit's cgroup. Exactly these two members are
       admitted, by exact argv and executable; a surviving watchdog may map the replaced image only
       when that image is exactly old_image.
    """
    base_metadata, base_tree = o.metadata, o.tree_snapshot

    def metadata(value, include_atime=True):
        return base_metadata(value, False)

    def tree_snapshot(root, cache=False, protected=False):
        value = base_tree(root, cache=cache, protected=protected)
        value['inventory'] = {k: {f: v for f, v in m.items() if f != 'atime_ns'}
                              for k, m in value['inventory'].items()}
        return value

    def proc(pid):
        argv = Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')[:-1]
        return [a.decode() for a in argv], os.readlink('/proc/' + str(pid) + '/exe')

    def quiet_scope(host):
        pid = host['host']['pid']
        first = {n: s.members(n) for n in (o.SERVICE, o.RECONCILER)}
        table = s.process_table()
        o.require(first[o.RECONCILER] == set(), 'reconciler scope residue')
        others = sorted(first[o.SERVICE] - {pid})
        o.require(pid in first[o.SERVICE] and len(others) == 2, 'supervisor scope membership')
        ident = {p: proc(p) for p in others}
        watchdog = [p for p, (argv, _) in ident.items() if argv[:2] == [GC_BIN, '__gc-managed-dolt-scope-watchdog']]
        server = [p for p, (argv, _) in ident.items() if argv[:2] == ['dolt', 'sql-server']]
        o.require(len(watchdog) == 1 and len(server) == 1, 'dolt scope members')
        w, sv = watchdog[0], server[0]
        w_argv, w_exe = ident[w]
        o.require(w_argv == [GC_BIN, '__gc-managed-dolt-scope-watchdog', DOLT_CFG, DOLT_LOG, CITY],
                  'dolt watchdog argv')
        if w_exe == GC_BIN:
            image = 'live'
        else:
            o.require(w_exe == GC_BIN + ' (deleted)', 'dolt watchdog executable')
            o.require(hashlib.sha256(Path('/proc/' + str(w) + '/exe').read_bytes()).hexdigest() == old_image,
                      'surviving watchdog image is not the replaced image')
            image = 'deleted-old'
        o.require(ident[sv] == (['dolt', 'sql-server', '--config', DOLT_CFG], DOLT_BIN), 'dolt server identity')
        o.require(table[sv][0] == w, 'dolt server parent')
        o.require(s.descendants(table, {pid}) == {pid}, 'supervisor descendant residue')
        o.require(s.descendants(table, {w}) == {w, sv}, 'dolt descendant residue')
        second = s.process_table()
        o.require(all(table.get(p) == second.get(p) for p in (pid, w, sv))
                  and first == {n: s.members(n) for n in first}, 'scope changed during observation')
        tmux = subprocess.run(['/usr/bin/tmux', '-L', 'city', 'list-sessions'], env=o.ENV, cwd='/',
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False)
        o.require(tmux.returncode == 1 and not tmux.stdout and
                  (b'no server running' in tmux.stderr or
                   (b'error connecting to' in tmux.stderr and b'No such file or directory' in tmux.stderr)),
                  'city tmux residue or unexplained refusal')
        return dict(core_members=[pid],
                    dolt_members=dict(watchdog=w, server=sv, watchdog_image=image,
                                      watchdog_proc=list(table[w]), server_proc=list(table[sv])),
                    reconciler_members=[], descendants=[], city_tmux_absent=True)

    o.metadata, o.tree_snapshot, s.quiet_scope = metadata, tree_snapshot, quiet_scope


def configure(graph, candidate):
    o, s = graph['observe_recovery'], graph['recovery_state']
    install_policy(o, s, candidate.OLD)
    accepted_path = Path(candidate.BASELINE_PATH)
    accepted_record = s.read(accepted_path, candidate.BASELINE_SHA)
    accepted = accepted_record['closure']
    expected_runtime = accepted_record['runtime']
    expected_mount = accepted_record['mount']
    o.GC_SHA = candidate.NEW
    s.ROOT = Path(candidate.ROOT)
    s.RECORDS = s.ROOT / 'q'
    s.SUSPENSION_SHA = candidate.SUSPENSION_SHA

    def snapshot(manifest):
        md = manifest['metadata']
        mount = candidate.r7.r6.r4.current_mount()
        o.require(mount == expected_mount, 'accepted cache mount policy drift')
        runtime = candidate.r7.c.runtime_readiness()
        o.require(runtime == expected_runtime, 'accepted initialized runtime drift')
        host = o.host_observation()
        o.require(host == accepted['host'] and host['host'] == md['host']
                  and host['namespaces'] == md['namespaces'], 'exact accepted host/receipt epoch drift')
        links = {p['path']: p['target'] for p in md['links']}
        o.require(len(links) == len(md['links']) and links == accepted['links'], 'link contract drift')
        for path, target in links.items():
            o.require(stat.S_ISLNK(os.lstat(path).st_mode) and os.readlink(path) == target, 'link drift')
        expected_pins = md['inputs'] + md['runtime'] + [md['writer']] + manifest['integrity']['files']
        pins = {p['path']: s.pin(p['path'], links) for p in expected_pins}
        for p in [manifest['core']] + manifest['managed_files']:
            pins[p['destination']] = s.pin(p['destination'], links)
        outputs = {p['path'] for p in md['preimages']}
        for path in accepted['pins']:
            if path not in outputs:
                pins[path] = s.pin(path, links)
        suspension = s.pin(o.CITY / '.gc/runtime/suspension-state.json', links)
        cache_path = str(Path(md['gc_home']) / 'cache/repos')
        trees, cache = {}, None
        for p in md['trees']:
            actual = o.tree_snapshot(p['path'], cache=p['path'] == cache_path)
            o.require(actual['inventory']['.']['mode'] == p['mode'], 'tree root mode')
            trees[p['path']] = {k: actual[k] for k in ('sha256', 'entries', 'file_bytes')}
            if p['path'] == cache_path:
                cache = actual
        protected = {p['pin']['path']: o.tree_snapshot(p['pin']['path'], protected=True)
                     for p in md['protected_trees']}
        absent = {p: not os.path.lexists(p) for p in md['absent']}
        scope = s.quiet_scope(host)
        after_host = o.host_observation()
        after_mount = candidate.r7.r6.r4.current_mount()
        after_runtime = candidate.r7.c.runtime_readiness()
        result = dict(host=host, pins=pins, suspension=suspension, trees=trees,
                      cache=cache, protected=protected, links=links, scope=scope,
                      mount=mount, runtime=runtime)
        # Persist the full actual closure before equality assertions. Records are
        # append-only and outside every native writable output parent.
        if s.RECORDS.is_dir():
            import secrets
            s.record('closure-observation-' + secrets.token_hex(12) + '.json',
                     dict(closure=result, host_after=after_host, absent=absent,
                          mount_after=after_mount, runtime_after=after_runtime))
        for p in expected_pins:
            actual = pins[p['path']]
            o.require(actual['sha256'] == p['sha256'] and actual['mode'] == p['mode'],
                      'input digest/mode drift: ' + p['path'])
        for p in [manifest['core']] + manifest['managed_files']:
            actual = pins[p['destination']]
            o.require(actual['sha256'] == p['sha256'] and actual['mode'] == p['mode'], 'managed image drift')
        for path, expected in accepted['pins'].items():
            if path not in outputs:
                o.require(pins[path] == expected, 'accepted infrastructure pin drift: ' + path)
        o.require(suspension == accepted['suspension'] and suspension['sha256'] == s.SUSPENSION_SHA,
                  'suspension record drift')
        o.require(trees == accepted['trees'] and len(trees) == len(md['trees']), 'accepted tree drift')
        for p in md['trees']:
            o.require(trees[p['path']]['sha256'] == p['sha256'], 'manifest tree digest')
        o.require(cache == accepted['cache'] and cache['sha256'] == md['cache_sha256'],
                  'cache full metadata/content drift')
        o.require(protected == accepted['protected'] and len(protected) == len(md['protected_trees']),
                  'protected full metadata/content drift')
        for p in md['protected_trees']:
            actual = protected[p['pin']['path']]
            info = actual['inventory']['.']
            o.require(actual['sha256'] == p['pin']['sha256'] and info['mode'] == p['pin']['mode']
                      and all(info[k] == p[k] for k in ('device', 'inode', 'uid', 'gid')),
                      'protected root identity')
        o.require(all(absent.values()) and scope == accepted['scope'], 'absence/scope drift')
        o.require(after_host == host, 'host changed across closure')
        o.require(after_mount == mount and after_runtime == runtime, 'mount/runtime changed across closure')
        return result

    s.snapshot = snapshot
    return accepted
