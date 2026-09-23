"""Successor closure: all accepted pins retained, named metadata pair separate.

Only the installed image/epoch already accepted by R7 is used as predecessor.
The native FINAL verifier alone accepts the two metadata outputs after commit.
"""
import os
from pathlib import Path
import stat


def configure(graph, candidate):
    o, s = graph['observe_recovery'], graph['recovery_state']
    accepted_path = Path(candidate.BASELINE_PATH)
    accepted_record = s.read(accepted_path, candidate.BASELINE_SHA)
    accepted = accepted_record['closure']
    expected_runtime = accepted_record['runtime']
    expected_mount = accepted_record['mount']
    o.GC_SHA = candidate.NEW
    s.ROOT = Path(candidate.ROOT)
    s.RECORDS = s.ROOT / 'q'
    s.SUSPENSION_SHA = '823e4e2115043aa494e1ed0a69cdbb9659bd321651db8469ed13bdcea82077b8'

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
