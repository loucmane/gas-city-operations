"""M5 quiet baseline capture: audit, complete, settle, freeze. Read-only except its own records.

Mirrors the reviewed M1 sequence (audit.py, complete-baseline.py,
settle-cache.py, freeze-baseline.py) over the M5 target coverage instead of the
installed R9 coverage. Must run in the supervisor host namespaces as UID 1000,
after every live prerequisite record exists and before any M5 preparation.
Each stage binds the previous stage by exact digest and writes one exclusive
record under reports/m5-capture-r3. No timer, lifecycle, worker, signer or Bead action.
The second root, reports/m5-capture-r2 (baseline 68cbee54, 10:49Z), was invalidated at 10:51:26Z by a
coordinator gc Bead call, which touched the pack cache repo .git directory. It is preserved unmodified.
From freeze until restore-accepted, nobody may run gc: not the coordinator, not the operator.
The first capture root, reports/m5-capture (frozen baseline 8f980d2e, 2026-09-23 08:51Z), expired
unused at its cache-renewal horizon. It is preserved unmodified and is never written again.

  python3 -I -B capture.py <candidate sha256> audit
  python3 -I -B capture.py <candidate sha256> complete <audit.json sha256>
  python3 -I -B capture.py <candidate sha256> settle <baseline-audit.json sha256>
  python3 -I -B capture.py <candidate sha256> freeze <baseline-audit.json sha256> <settle-result.json sha256>

The two re-pinned trees are bounded against the reviewed M1 audit inventories,
ignoring access times:
- r5/r may differ only in .git/index. Its M1 digest is the R9 pin ad25084c.
- The Template .git may add, change or remove only Git object, ref, log,
  worktree-admin, LFS lock, rerere and workflow-transaction state, plus HEAD,
  index, FETCH_HEAD, ORIG_HEAD, COMMIT_EDITMSG, packed-refs and config. Its M1
  digest is the M3-reviewed cbe4982a.
- Never admitted, even inside those prefixes: refs/replace, object alternates
  and grafts, shallow, a worktree info/ directory, and a change to an existing
  worktree's commondir or gitdir.
- The only config.worktree files admitted are the pre-existing, unchanged, empty ones; Git ignores
  them because extensions.worktreeConfig is unset. Any added, changed, removed or non-empty one
  refuses, and so does any replace ref, whether loose or packed (for-each-ref refs/replace).
- gc and repack are stricter than needed: they may write info/refs, gc.pid or gc.log, which fall
  outside the bound and refuse, closed. The quiet window forbids them.
- Every config key other than branch.<name>.remote and branch.<name>.merge must
  equal the reviewed set exactly.
- No hook, info or description entry may change.

`complete` refuses any carried-forward M3 pin that changed, except the six
reviewed CHANGED_INPUTS, each at its exact successor digest. It waits for the
same natural reconciler quiet slot as prereqs.py before its scope check.
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
m = None
OUT = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m5-capture-r3')
M1_AUDIT = Path('/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922/'
                'gct-m1wh-metadata-20260922-r1/audit.json')
M1_AUDIT_SHA = '942583964ff1bac9bd9bb9e343b7c5323f7d986edf9b71a40df3e2bb2bec2930'
GIT_EXACT = {'.', 'HEAD', 'index', 'FETCH_HEAD', 'ORIG_HEAD', 'COMMIT_EDITMSG', 'config', 'packed-refs',
             'objects', 'refs', 'logs', 'worktrees', 'lfs', 'lfs/cache', 'gas-city-workflow', 'rr-cache'}
GIT_PREFIXES = ('objects/', 'refs/', 'logs/', 'worktrees/', 'lfs/cache/locks/', 'gas-city-workflow/', 'rr-cache/')
# Entries that change how objects or refs resolve are never admitted, even inside an allowed prefix.
GIT_DENIED = {'objects/info/alternates', 'objects/info/http-alternates', 'objects/info/grafts', 'refs/replace',
              'shallow', 'info/grafts'}
GIT_DENIED_PREFIXES = ('refs/replace/',)
M1_TREE_DIGESTS = {
    '/home/loucmane/gas-city-template/.git': 'cbe4982a3117d7212de86092031a81586b20667a4437fcb143a7ad3f78578c9b',
    '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/r5/r':
        'ad25084c3dd633191232369d5325bb44b994f3f67d8917711047e56dd6e17ce0',
}
CONFIG_EXPECTED = (
    'core.repositoryformatversion=0', 'core.filemode=true', 'core.bare=false', 'core.logallrefupdates=true',
    'remote.origin.url=https://github.com/loucmane/gas-city-template.git',
    'remote.origin.fetch=+refs/heads/main:refs/remotes/origin/main', 'lfs.repositoryformatversion=0',
    'filter.lfs.clean=git-lfs clean -- %f', 'filter.lfs.smudge=git-lfs smudge -- %f',
    'filter.lfs.process=git-lfs filter-process', 'filter.lfs.required=true',
    'lfs.https://github.com/loucmane/gas-city-template.git/info/lfs.access=basic',
    'user.signingkey=FD5585922F5335BC378AD8D42ECF4432C7E7982D!')


CANDIDATE_SHA = None
# prereqs.py supplies the reconciler quiet slot; its reviewed bytes are pinned here and by test_capture.py.
PREREQS_SHA = '6d97fd4094ea2e6b1b7d7ee9b1701128d350744161adc22633648283d7745784'


def load_candidate(expected):
    global m, CANDIDATE_SHA
    path = HERE/'manifest_candidate.py'
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'candidate source differs from the reviewed digest')
    m = types.ModuleType('m5_candidate'); m.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), m.__dict__)
    require(Path(m.O + '/reports/m5-capture-r3') == OUT, 'capture root binding')
    CANDIDATE_SHA = expected


def load_prereqs():
    path = HERE/'prereqs.py'
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PREREQS_SHA, 'prereqs source differs from the reviewed digest')
    module = types.ModuleType('m5_prereqs'); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


PREREQS = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m5-inputs')
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


def load_source(filename, name):
    path = HERE/filename
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


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


def classify(kind, before, now):
    """Pure bound on a re-pinned tree: every change must lie inside the allowed set for its kind."""
    strip = lambda v: {k: x for k, x in v.items() if k != 'atime_ns'}
    changed = sorted(k for k in set(before) & set(now) if strip(before[k]) != strip(now[k]))
    added, removed = sorted(set(now) - set(before)), sorted(set(before) - set(now))
    if kind == 'r5r':
        outside = [k for k in changed if k not in ('.git', '.git/index')] + added + removed
    else:
        def allowed(k):
            parts = k.split('/')
            if not (k in GIT_EXACT or k.startswith(GIT_PREFIXES)) or k.startswith(GIT_DENIED_PREFIXES):
                return False
            if k in GIT_DENIED or parts[-1] == 'config.worktree':
                return False
            # A linked worktree admin directory may gain entries, but never info/ or a redirected common dir.
            if parts[0] == 'worktrees' and len(parts) >= 3 and parts[2] == 'info':
                return False
            return True
        outside = [k for k in changed + added + removed if not allowed(k)]
        outside += [k for k in changed if k.split('/')[0] == 'worktrees' and k.rsplit('/', 1)[-1]
                    in ('commondir', 'gitdir') and k not in outside]
        # The reviewed tree already holds empty config.worktree files that Git ignores (no
        # extensions.worktreeConfig). Only those, unchanged and empty, are admitted.
        outside += [k for k in now if k.rsplit('/', 1)[-1] == 'config.worktree' and k not in outside
                    and (k not in before or strip(before[k]) != strip(now[k]) or now[k].get('size') != 0)]
        outside += [k for k in now if (k in GIT_DENIED or k.startswith(GIT_DENIED_PREFIXES)) and k not in outside]
    return dict(changed=changed, added=added, removed=removed, outside_allowed=outside)


def bounded_tree_diff(path, now):
    """Changes since the reviewed M1 inventory, ignoring access times, within the allowed set."""
    raw = M1_AUDIT.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == M1_AUDIT_SHA, 'M1 audit drift')
    tree = json.loads(raw)['trees'][path]
    require(tree['sha256'] == M1_TREE_DIGESTS[path], 'M1 bound baseline is not the reviewed digest')
    return classify('r5r' if path == m.R5R else 'git', tree['inventory'], now)


def unexpected_changes(changes, successors):
    """Carried-forward pins may change only to the exact reviewed successor digests."""
    return [x['path'] for x in changes
            if x['path'] not in successors or x['after']['sha256'] != successors[x['path']]]


def config_drift(listing):
    """Every key except branch.<name>.remote/merge must equal the reviewed set; returns the differences."""
    lines = [line for line in listing.splitlines() if line]
    branch = [line for line in lines if line.startswith('branch.')]
    other = tuple(line for line in lines if not line.startswith('branch.'))
    bad_branch = [line for line in branch if not line.split('=', 1)[0].endswith(('.remote', '.merge'))]
    return dict(unexpected=[line for line in other if line not in CONFIG_EXPECTED],
                missing=[line for line in CONFIG_EXPECTED if line not in other],
                duplicate=len(other) != len(set(other)), bad_branch_keys=bad_branch)


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
    for step in ('inputs', 'cli', 'city-transition', 'checkout', 'registry', 'render', 'city-final',
                 'authority'):
        record = PREREQS/('prereq-' + step + '.json')
        require(os.path.lexists(record), 'live prerequisite missing: ' + step)
        require(json.loads(record.read_text()).get('candidate_sha256') == CANDIDATE_SHA,
                'live prerequisite ran with another candidate: ' + step)
    require(not os.path.lexists(OUT) and not os.path.lexists(m.ROOT)
            and not os.path.lexists(PREREQS/'rollback.json'), 'capture, package or rollback consumed')
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
    ignored = git(o, m.AUTHORITY, 'status', '--porcelain', '--ignored', '--untracked-files=all')
    repositories[m.AUTHORITY_NAME]['ignored_and_untracked'] = ignored
    if ignored['returncode'] != 0 or ignored['stdout']:
        drifts.append(dict(kind='authority-ignored-or-untracked', actual=ignored))
    bounds = {path: bounded_tree_diff(path, trees[path]['inventory']) for path in m.REPINNED_TREES}
    for path, diff in bounds.items():
        if diff['outside_allowed']:
            drifts.append(dict(kind='repinned-tree-bound', path=path, outside=diff['outside_allowed'][:50]))
    replaced = git(o, m.TEMPLATE, 'for-each-ref', 'refs/replace')
    if replaced['returncode'] != 0 or replaced['stdout']:
        drifts.append(dict(kind='template-replace-refs', actual=replaced))
    config = git(o, m.TEMPLATE, 'config', '--file', m.TEMPLATE + '/.git/config', '--list')
    config_check = config_drift(config['stdout'])
    if config['returncode'] != 0 or any(config_check[k] for k in config_check):
        drifts.append(dict(kind='template-git-config', check=config_check))
    canonical = dict(head=git(o, m.TEMPLATE, 'rev-parse', 'HEAD'),
                     status=git(o, m.TEMPLATE, 'status', '--porcelain', '--untracked-files=normal'))
    if canonical['head']['stdout'].strip() != m.TEMPLATE_COMMIT or canonical['status']['stdout'] != UNTRACKED:
        drifts.append(dict(kind='canonical-checkout', actual=canonical))
    after_host = o.host_observation()
    # Re-pinned trees carry no expected digest, so any tree drift left for them is a root-mode change.
    unexpected = list(drifts)
    result = dict(schema='gct.m5-capture-audit.v1', preparation_only=True, live_acceptance=False,
                  worker_release=False, manifest=manifest, receipt=receipt, host=host, host_after=after_host,
                  pins=pins, trees=trees, protected=protected, links=links, absent=absent, drifts=drifts,
                  unexpected_drifts=unexpected, repositories=repositories, canonical_checkout=canonical,
                  repinned_tree_bounds=bounds, template_git_config=config, template_git_config_check=config_check,
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
    require(not a['unexpected_drifts'] and a['host'] == a['host_after'], 'audit carries drift or host change')
    prior = s.read(M3_BASELINE, M3_BASELINE_SHA)
    pins = dict(a['pins']); changes = []
    for path, before in prior['closure']['pins'].items():
        if path not in pins:
            pins[path] = s.pin(path, a['links'])
        if pins[path] != before:
            changes.append(dict(path=path, before=before, after=pins[path]))
    unexpected = unexpected_changes(changes, {path: after for path, _, after in m.CHANGED_INPUTS})
    require(not unexpected, 'carried-forward pins changed outside the reviewed set: ' + json.dumps(unexpected))
    runtime = c.runtime_readiness()
    mount = m.r7.r6.r4.current_mount()
    host = o.host_observation()
    require(host == a['host'] and runtime == prior['runtime'] and mount == prior['mount'],
            'host/runtime/mount changed')
    slot = load_prereqs().quiet_slot()
    scope = s.quiet_scope(host)
    trees = {path: {k: v[k] for k in ('sha256', 'entries', 'file_bytes')} for path, v in a['trees'].items()}
    closure = dict(host=host, pins=pins, suspension=a['suspension'], trees=trees,
                   cache=a['trees']['/home/loucmane/gascity/home/cache/repos'], protected=a['protected'],
                   links=a['links'], scope=scope)
    result = dict(closure=closure, runtime=runtime, mount=mount, pin_changes=changes, reconciler_slot=slot,
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
    require(len(args) >= 2 and args[1] in ('audit', 'complete', 'settle', 'freeze'), 'usage: see module docstring')
    load_candidate(args[0])
    arity = dict(audit=2, complete=3, settle=3, freeze=4)[args[1]]
    require(len(args) == arity and all(m.b.hex64(x) for x in args[2:]), 'exact digest arguments required')
    dict(audit=audit, complete=complete, settle=settle, freeze=freeze)[args[1]](*args[2:])


if __name__ == '__main__':
    main()
