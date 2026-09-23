"""M5 quiet baseline capture: audit, complete, settle, freeze. Read-only except its own records.

Mirrors the reviewed M1 sequence (audit.py, complete-baseline.py,
settle-cache.py, freeze-baseline.py) over the M5 target coverage instead of the
installed R9 coverage. Must run in the supervisor host namespaces as UID 1000,
after every live prerequisite record exists and before any M5 preparation.
Each stage binds the previous stage by exact digest and writes one exclusive
record under reports/m5-capture. No timer, lifecycle, worker, signer or Bead action.

  python3 -I -B capture.py audit
  python3 -I -B capture.py complete <audit.json sha256>
  python3 -I -B capture.py settle <baseline-audit.json sha256>
  python3 -I -B capture.py freeze <baseline-audit.json sha256> <settle-result.json sha256>
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

HERE = Path(__file__).parent
p = HERE/'manifest_candidate.py'
m = types.ModuleType('m5_candidate'); m.__file__ = str(p)
exec(compile(p.read_bytes(), str(p), 'exec', dont_inherit=True), m.__dict__)
OUT = Path(m.O + '/reports/m5-capture')
PREREQS = Path(m.O + '/reports/m5-inputs')
M3_BASELINE = Path('/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922/'
                   'gct-m1wh-metadata-20260922-r3/baseline.json')
M3_BASELINE_SHA = 'c411dc6072d3a5d29c79e70883c50c13503014fedcc819a3b6778aae2979daf6'
GIT_ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/home/loucmane', 'LANG': 'C', 'GIT_CONFIG_NOSYSTEM': '1'}
UNTRACKED = '?? deploy/\n?? gas_city_template.egg-info/\n'


def exclusive(name, raw):
    fd = os.open(OUT/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(raw)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(OUT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return hashlib.sha256(raw).hexdigest()


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def git(o, repo, *args):
    r = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                        '-c', 'core.hooksPath=/dev/null', '-c', 'core.untrackedCache=false',
                        '-C', str(repo), *args], env=GIT_ENV, cwd='/', stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=30, check=False)
    return dict(returncode=r.returncode, stdout=r.stdout.decode(errors='replace'),
                stderr=r.stderr.decode(errors='replace'))


def target(manifest):
    """The exact M5 coverage and the digest each pin must have before preparation."""
    md = manifest['metadata']
    changed = {path: after for path, _, after in m.CHANGED_INPUTS}
    expected = {}
    rows = [p for p in md['inputs'] if not p['path'].startswith(m.TEST_PREFIX)]
    rows += md['runtime'] + [md['writer']] + manifest['integrity']['files']
    rows += [dict(path=f['destination'], sha256=f['sha256'], mode=f['mode'])
             for f in [manifest['core']] + manifest['managed_files']]
    for row in rows:
        expected[row['path']] = dict(sha256=changed.get(row['path'], row['sha256']), mode=row['mode'])
    expected['/var/tmp/ga-mutg-custody-build-20260920/gc-b'] = dict(sha256=m.NEW, mode=manifest['core']['mode'])
    expected[m.CITY_SOURCE] = dict(sha256=m.CITY_NEW, mode=0o644)
    for relative, digest, mode in m.AUTH_INPUTS:
        expected[m.AUTHORITY+'/'+relative] = dict(sha256=digest, mode=mode)
    trees = {p['path']: dict(sha256=None if p['path'] in m.REPINNED_TREES else p['sha256'], mode=p['mode'])
             for p in md['trees']}
    for relative in m.AUTH_TREES:
        trees[m.AUTHORITY+'/'+relative] = dict(sha256=None, mode=0o755)
    links = {p['path']: p['target'] for p in md['links']}
    links.update({m.AUTHORITY+'/'+relative: t for relative, t in m.AUTH_LINKS})
    return expected, trees, links


def audit():
    raw = (HERE/'source_runtime.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == '2585357a808d8f36604d4bf45a39a5363ba87c8d719413ba42d9fd0fac71973f',
            'source loader drift')
    r = types.ModuleType('pinned_runtime'); r.__file__ = str(HERE/'source_runtime.py')
    exec(compile(raw, r.__file__, 'exec', dont_inherit=True), r.__dict__)
    g = r.legacy()
    o, s = g['observe_recovery'], g['recovery_state']
    o.GC_SHA = m.NEW
    for step in ('inputs', 'cli', 'city', 'checkout', 'render', 'authority'):
        require(os.path.lexists(PREREQS/('prereq-' + step + '.json')), 'live prerequisite missing: ' + step)
    require(not os.path.lexists(OUT) and not os.path.lexists(m.ROOT), 'capture or package root consumed')
    manifest = s.read(o.CITY/'.gc/platform/install-manifest.json', m.OLD_MANIFEST_SHA)
    receipt = s.read(o.CITY/'.gc/platform/install-receipt.json', m.OLD_RECEIPT_SHA)
    md = manifest['metadata']
    host = o.host_observation()
    os.mkdir(OUT, 0o700)
    expected, expected_trees, links = target(manifest)
    for path, link_target in links.items():
        require(os.path.islink(path) and os.readlink(path) == link_target, 'link drift: ' + path)
    pins, trees, protected, drifts = {}, {}, {}, []
    for path, want in expected.items():
        actual = s.pin(path, links)
        pins[path] = actual
        if actual['sha256'] != want['sha256'] or actual['mode'] != want['mode']:
            drifts.append(dict(kind='file', path=path, expected=want, actual=actual))
    cache_path = str(Path(md['gc_home']) / 'cache/repos')
    for path, want in expected_trees.items():
        actual = o.tree_snapshot(path, cache=path == cache_path)
        trees[path] = actual
        if (want['sha256'] is not None and actual['sha256'] != want['sha256']) or \
                actual['inventory']['.']['mode'] != want['mode']:
            drifts.append(dict(kind='tree', path=path, expected=want,
                               actual={k: actual[k] for k in ('sha256', 'entries', 'file_bytes')}))
    for p in md['protected_trees']:
        path = p['pin']['path']
        actual = o.tree_snapshot(path, protected=True)
        protected[path] = actual
        meta = actual['inventory']['.']
        if (actual['sha256'] != p['pin']['sha256'] or meta['mode'] != p['pin']['mode']
                or any(meta[k] != p[k] for k in ('device', 'inode', 'uid', 'gid'))):
            drifts.append(dict(kind='protected', path=path, expected=p,
                               actual=dict(sha256=actual['sha256'], root=meta)))
    absent = {path: not os.path.lexists(path) for path in md['absent']}
    repositories = {}
    for repo in manifest['integrity']['repositories'] + [dict(name=m.AUTHORITY_NAME, path=m.AUTHORITY,
                                                             commit=m.TEMPLATE_COMMIT)]:
        head = git(o, repo['path'], 'rev-parse', 'HEAD')
        status = git(o, repo['path'], 'status', '--porcelain', '--untracked-files=normal')
        repositories[repo['name']] = dict(head=head, status=status)
        if head['stdout'].strip() != repo['commit'] or status['returncode'] != 0 or status['stdout']:
            drifts.append(dict(kind='repository', name=repo['name'], expected=repo,
                               actual=repositories[repo['name']]))
    canonical = dict(head=git(o, m.TEMPLATE, 'rev-parse', 'HEAD'),
                     status=git(o, m.TEMPLATE, 'status', '--porcelain', '--untracked-files=normal'))
    if canonical['head']['stdout'].strip() != m.TEMPLATE_COMMIT or canonical['status']['stdout'] != UNTRACKED:
        drifts.append(dict(kind='canonical-checkout', actual=canonical))
    after_host = o.host_observation()
    unexpected = [d for d in drifts if not (d['kind'] == 'tree' and d['path'] in m.REPINNED_TREES)]
    result = dict(schema='gct.m5-capture-audit.v1', preparation_only=True, live_acceptance=False,
                  worker_release=False, manifest=manifest, receipt=receipt, host=host, host_after=after_host,
                  pins=pins, trees=trees, protected=protected, links=links, absent=absent, drifts=drifts,
                  unexpected_drifts=unexpected, repositories=repositories, canonical_checkout=canonical,
                  suspension=s.pin(o.CITY/'.gc/runtime/suspension-state.json', links),
                  provisioning=s.pin(o.CITY/'.gc/runtime/provisioning/receipt.json', links))
    digest = exclusive('audit.json', o.encoded(result))
    print(json.dumps(dict(evidence=str(OUT/'audit.json'), sha256=digest, unexpected_drifts=unexpected,
                          repinned={p: trees[p]['sha256'] for p in m.REPINNED_TREES},
                          host_stable=host == after_host, all_absent=all(absent.values()))))
    require(host == after_host and all(absent.values()) and not unexpected, 'audit refused; record kept')


def complete(audit_sha):
    c = m.r7.c; s = c.s; o = c.o
    o.GC_SHA = m.NEW
    a = s.read(OUT/'audit.json', audit_sha)
    require(not a['unexpected_drifts'], 'audit carries unexpected drift')
    prior = s.read(M3_BASELINE, M3_BASELINE_SHA)
    pins = dict(a['pins']); changes = []
    for path, before in prior['closure']['pins'].items():
        if path not in pins:
            pins[path] = s.pin(path, a['links'])
        if pins[path] != before:
            changes.append(dict(path=path, before=before, after=pins[path]))
    runtime = c.runtime_readiness()
    mount = m.r7.r6.r4.current_mount()
    host = o.host_observation()
    require(host == a['host'] and runtime == prior['runtime'] and mount == prior['mount'],
            'host/runtime/mount changed')
    scope = s.quiet_scope(host)
    trees = {path: {k: v[k] for k in ('sha256', 'entries', 'file_bytes')} for path, v in a['trees'].items()}
    closure = dict(host=host, pins=pins, suspension=a['suspension'], trees=trees,
                   cache=a['trees']['/home/loucmane/gascity/home/cache/repos'], protected=a['protected'],
                   links=a['links'], scope=scope)
    result = dict(closure=closure, runtime=runtime, mount=mount, pin_changes=changes,
                  audit_sha256=audit_sha, preparation_only=True, live_acceptance=False)
    digest = exclusive('baseline-audit.json', o.encoded(result))
    print(json.dumps(dict(evidence=str(OUT/'baseline-audit.json'), sha256=digest,
                          pin_changes=[x['path'] for x in changes], scope=scope, worker_release=False)))


def settle(baseline_sha):
    P = Path('/tmp/ga-mutg-adoption-20260920-r4/capture_transition.py')
    raw = P.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == '4d373634fde3b77c253eed9b36ea13db3b15cf62150617bf0a5c29e36304308f',
            'reviewed read preparation changed')
    r = types.ModuleType('reviewed_reads'); r.__file__ = str(P)
    exec(compile(raw, str(P), 'exec', dont_inherit=True), r.__dict__)
    o, s = r.c.o, r.c.s
    o.GC_SHA = m.NEW
    for name in ('settle-before.json', 'settle-after.json', 'settle-second.json', 'settle-result.json'):
        require(not os.path.lexists(OUT/name), 'read preparation consumed')
    baseline = s.read(OUT/'baseline-audit.json', baseline_sha)
    mount = r.current_mount(); host = o.host_observation()
    require(mount == baseline['mount'] and host == baseline['closure']['host'], 'host/mount drift')
    initial = o.tree_snapshot(r.CACHE, cache=True)
    delta = r.history_check(baseline['closure']['cache'], initial)
    exclusive('settle-before.json', o.encoded(dict(cache=initial, host=host, mount=mount,
              prior_atime_delta=delta, ordinary_reads_only=True, worker_release=False)))
    r.warm_reads(initial)
    after = o.tree_snapshot(r.CACHE, cache=True)
    after_sha = exclusive('settle-after.json', o.encoded(dict(cache=after)))
    changed = r.history_check(initial, after)
    r.renewal_check(after, time.time_ns())
    time.sleep(5)
    second = o.tree_snapshot(r.CACHE, cache=True)
    second_sha = exclusive('settle-second.json', o.encoded(dict(cache=second)))
    require(second == after, 'cache did not settle')
    require(r.current_mount() == mount and o.host_observation() == host, 'host/mount drift after reads')
    renewal = r.renewal_check(second, time.time_ns())
    digest = exclusive('settle-result.json', o.encoded(dict(
        ok=True, baseline_sha256=baseline_sha, before_sha256=hashlib.sha256((OUT/'settle-before.json').read_bytes()).hexdigest(),
        after_sha256=after_sha, second_sha256=second_sha, atime_delta=changed, renewal_wall_ns=renewal,
        worker_release=False, timer_action_performed=False)))
    print(json.dumps(dict(ok=True, result_sha256=digest, atime_changes=len(changed), worker_release=False)))


def freeze(baseline_sha, settle_sha):
    def read(name, expected):
        raw = (OUT/name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, 'evidence drift: ' + name)
        return json.loads(raw)
    before = read('baseline-audit.json', baseline_sha)
    proof = read('settle-result.json', settle_sha)
    require(proof['baseline_sha256'] == baseline_sha, 'settle binds another baseline')
    first = read('settle-after.json', proof['after_sha256'])
    second = read('settle-second.json', proof['second_sha256'])
    require(first == second and proof['ok'] is True and proof['worker_release'] is False,
            'settling evidence not accepted')
    old, new = copy.deepcopy(before['closure']['cache']), copy.deepcopy(second['cache'])
    for tree in (old, new):
        for item in tree['inventory'].values():
            item.pop('atime_ns')
    require(old == new, 'settling changed non-atime authority')
    out = copy.deepcopy(before)
    out['closure']['cache'] = second['cache']
    out['settling_sha256'] = settle_sha
    out['quiet_acceptance'] = False
    raw = (json.dumps(out, sort_keys=True, separators=(',', ':')) + '\n').encode()
    print(exclusive('baseline.json', raw))


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    args = sys.argv[1:]
    require(args and args[0] in ('audit', 'complete', 'settle', 'freeze'), 'usage: see module docstring')
    arity = dict(audit=1, complete=2, settle=2, freeze=3)[args[0]]
    require(len(args) == arity and all(m.b.hex64(x) for x in args[1:]), 'exact digest arguments required')
    dict(audit=audit, complete=complete, settle=settle, freeze=freeze)[args[0]](*args[1:])


if __name__ == '__main__':
    main()
