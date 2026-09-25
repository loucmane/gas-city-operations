"""M6 baseline capture (ga-e0t1.15 S3). Read-only except its own record under reports/m6-capture.

  python3 -I -B capture_m6.py <manifest_candidate.py sha256>

Runs in the supervisor host namespaces as UID 1000, after the four prerequisite records and before any
M6 preparation. One stage replaces M5's audit, complete, settle and freeze: every inventory is access-time
neutral (the operator's S2 decision of 2026-09-25), so there is nothing to settle and no renewal horizon.

It proves, and records as baseline.json in the shape metadata_closure.py consumes:
- the S2-accepted closure still holds: all 741 S2 pins are unchanged except the signing-worker parser at
  its exact successor (libexpat was already at its successor in S2 and must stay there), all 29 S2 trees
  are unchanged except the Template common Git directory, and the
  host epoch, suspension record and links are the S2 ones;
- the Template common Git directory changed only inside the reviewed M5 bound (objects, refs, logs,
  worktree admin and the other Git bookkeeping; never replace refs, alternates, grafts, shallow, a
  worktree info/ directory, a redirected commondir or gitdir, or a changed config.worktree), measured
  against the inventory the `inventory` prerequisite recorded at the S2-accepted digest;
- every M6 target pin, tree root, link, protected tree, repository and the authority are exact;
- the quiet host: reconciler slot, dolt-aware scope, no city tmux, and a stable host across the capture.
From capture until restore-accepted nobody runs gc: not the coordinator, not the operator, no Bead note.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

HERE = Path(__file__).parent
PREREQS_SHA = 'a36824b89d6feb23a6d9a7ade26127c4848e71df6e4a0f525e308b0f02bd006e'  # s3/prereqs_m6.py
GIT_EXACT = {'.', 'HEAD', 'index', 'FETCH_HEAD', 'ORIG_HEAD', 'COMMIT_EDITMSG', 'config', 'packed-refs',
             'objects', 'refs', 'logs', 'worktrees', 'lfs', 'lfs/cache', 'gas-city-workflow', 'rr-cache'}
GIT_PREFIXES = ('objects/', 'refs/', 'logs/', 'worktrees/', 'lfs/cache/locks/', 'gas-city-workflow/', 'rr-cache/')
GIT_DENIED = {'objects/info/alternates', 'objects/info/http-alternates', 'objects/info/grafts', 'refs/replace',
              'shallow', 'info/grafts'}
GIT_DENIED_PREFIXES = ('refs/replace/',)
CONFIG_EXPECTED = (
    'core.repositoryformatversion=0', 'core.filemode=true', 'core.bare=false', 'core.logallrefupdates=true',
    'remote.origin.url=https://github.com/loucmane/gas-city-template.git',
    'remote.origin.fetch=+refs/heads/main:refs/remotes/origin/main', 'lfs.repositoryformatversion=0',
    'filter.lfs.clean=git-lfs clean -- %f', 'filter.lfs.smudge=git-lfs smudge -- %f',
    'filter.lfs.process=git-lfs filter-process', 'filter.lfs.required=true',
    'lfs.https://github.com/loucmane/gas-city-template.git/info/lfs.access=basic',
    'user.signingkey=FD5585922F5335BC378AD8D42ECF4432C7E7982D!')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def classify(before, now):
    """The reviewed M5 Template .git bound (capture.py classify 'git'), over access-time-free inventories."""
    changed = sorted(k for k in set(before) & set(now) if before[k] != now[k])
    added, removed = sorted(set(now) - set(before)), sorted(set(before) - set(now))

    def allowed(k):
        parts = k.split('/')
        if not (k in GIT_EXACT or k.startswith(GIT_PREFIXES)) or k.startswith(GIT_DENIED_PREFIXES):
            return False
        if k in GIT_DENIED or parts[-1] == 'config.worktree':
            return False
        if parts[0] == 'worktrees' and len(parts) >= 3 and parts[2] == 'info':
            return False
        return True
    outside = [k for k in changed + added + removed if not allowed(k)]
    outside += [k for k in changed if k.split('/')[0] == 'worktrees' and k.rsplit('/', 1)[-1]
                in ('commondir', 'gitdir') and k not in outside]
    outside += [k for k in now if k.rsplit('/', 1)[-1] == 'config.worktree' and k not in outside
                and (k not in before or before[k] != now[k] or now[k].get('size') != 0)]
    outside += [k for k in now if (k in GIT_DENIED or k.startswith(GIT_DENIED_PREFIXES)) and k not in outside]
    return dict(changed=changed, added=added, removed=removed, outside_allowed=outside)


def config_drift(listing):
    lines = [line for line in listing.splitlines() if line]
    branch = [line for line in lines if line.startswith('branch.')]
    other = tuple(line for line in lines if not line.startswith('branch.'))
    return dict(unexpected=[line for line in other if line not in CONFIG_EXPECTED],
                missing=[line for line in CONFIG_EXPECTED if line not in other],
                duplicate=len(other) != len(set(other)),
                bad_branch_keys=[line for line in branch if not line.split('=', 1)[0].endswith(('.remote', '.merge'))])


def carried_changes(s2_pins, live_pins, changed_inputs, successor_sizes):
    """Pure: which S2-accepted pins changed, and which of those changes are not reviewed.

    A reviewed changed input found at its predecessor in S2 must now be exactly its successor pin: the
    reviewed digest and byte size, with mode, uid and gid unchanged. One S2 already recorded at its successor
    (libexpat, updated before S2) must be unchanged; any other S2 digest for it is refused. Every other S2
    pin must be unchanged (review B of dc5c46b5 must_fix 1; review A of f8fcb751 must_fix 1).
    """
    reviewed = {path: (before, after) for path, before, after in changed_inputs}
    changes, problems = [], []
    for path, before in s2_pins.items():
        now = live_pins[path]
        if path in reviewed:
            old, new = reviewed[path]
            if before['sha256'] == old:
                if path not in successor_sizes or now != dict(before, sha256=new, size=successor_sizes[path]):
                    problems.append(path)
            elif before['sha256'] != new or now != before:
                problems.append(path)
        elif now != before:
            problems.append(path)
        if now != before:
            changes.append(dict(path=path, before=before, after=now))
    return changes, problems


def target(m, manifest):
    """The exact M6 pins, tree paths and links the successor manifest names, derived from the M5 manifest."""
    md = manifest['metadata']
    under = lambda path: path == m.M5_AUTHORITY or path.startswith(m.M5_AUTHORITY + '/')
    changed = {path: after for path, _, after in m.CHANGED_INPUTS}
    changed[m.GC] = m.NEW
    rows = [p for p in md['inputs'] if not under(p['path'])] + md['runtime'] + [md['writer']]
    rows += manifest['integrity']['files']
    rows += [dict(path=f['destination'], sha256=f['sha256'], mode=f['mode'])
             for f in [manifest['core']] + manifest['managed_files']]
    expected = {row['path']: dict(sha256=changed.get(row['path'], row['sha256']), mode=row['mode']) for row in rows}
    expected[m.ARTIFACT] = dict(sha256=m.NEW, mode=0o755)
    expected[m.CITY_CONFIG_BACKUP] = dict(sha256=m.CITY_CONFIG_SHA, mode=0o644)
    for relative, value, mode in m.auth_inputs():
        expected[m.AUTHORITY + '/' + relative] = dict(sha256=value, mode=mode)
    trees = {p['path']: p['mode'] for p in md['trees'] if not under(p['path'])}
    trees.update({m.AUTHORITY + '/' + r: 0o755 for r in m.AUTH_TREES})
    links = {p['path']: p['target'] for p in md['links'] if not under(p['path'])}
    links.update({m.AUTHORITY + '/' + r: t for r, t in m.AUTH_LINKS})
    return expected, trees, links


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    require(len(sys.argv) == 2 and len(sys.argv[1]) == 64, 'usage: capture_m6.py <candidate sha256>')
    raw = (HERE/'prereqs_m6.py').read_bytes()
    require(PREREQS_SHA is not None and digest(raw) == PREREQS_SHA, 'prereqs source differs from the reviewed digest')
    p = types.ModuleType('m6_prereqs'); p.__file__ = str(HERE/'prereqs_m6.py')
    exec(compile(raw, p.__file__, 'exec', dont_inherit=True), p.__dict__)
    c = p.Context(sys.argv[1])
    m, o, s = c.m, c.o, c.s
    out = Path(m.O + '/reports/m6-capture')
    for step in p.STEPS:
        record = c.record_path(step)
        require(os.path.lexists(record) and json.loads(record.read_text()).get('candidate_sha256') == c.expected,
                'live prerequisite missing or bound to another candidate: ' + step)
    require(not os.path.lexists(out) and not os.path.lexists(m.ROOT)
            and not os.path.lexists(c.inputs/'rollback.json'), 'capture, package or rollback consumed')
    manifest = s.read(p.INSTALLED, m.OLD_MANIFEST_SHA)
    s.read(p.INSTALLED_RECEIPT, m.OLD_RECEIPT_SHA)
    md = manifest['metadata']
    quiet = c.quiet()
    host = quiet['host']
    expected, tree_paths, links = target(m, manifest)
    drifts = []
    for path, link_target in links.items():
        if not (os.path.islink(path) and os.readlink(path) == link_target):
            drifts.append(dict(kind='link', path=path))
    # Pins: the M6 targets, plus every S2-accepted pin carried forward.
    require(len(c.s2['pins']) == 741 and len(c.s2['trees']) == 29, 'S2-accepted closure cardinality')
    pins = {}
    for path in sorted(set(expected) | set(c.s2['pins'])):
        pins[path] = s.pin(path, links)
    for path, want in expected.items():
        if pins[path]['sha256'] != want['sha256'] or pins[path]['mode'] != want['mode']:
            drifts.append(dict(kind='file', path=path, expected=want, actual=pins[path]))
    changes, unexpected = carried_changes(c.s2['pins'], pins, m.CHANGED_INPUTS, m.SUCCESSOR_SIZES)
    if unexpected:
        drifts.append(dict(kind='carried-forward-pins', unexpected=unexpected, changed=[x['path'] for x in changes]))
    # Trees: the S2 trees exactly, the Template Git directory within its bound, and every root mode.
    cache_path = str(Path(md['gc_home'])/'cache/repos')
    trees, cache = {}, None
    for path, mode in tree_paths.items():
        actual = o.tree_snapshot(path, cache=path == cache_path)
        trees[path] = {k: actual[k] for k in ('sha256', 'entries', 'file_bytes')}
        if path == cache_path:
            cache = actual
        if actual['inventory']['.']['mode'] != mode:
            drifts.append(dict(kind='tree-root-mode', path=path))
        if path == m.TEMPLATE_GIT:
            before = json.loads((c.inputs/'template-git-before.json').read_bytes())
            bound = classify(before['inventory'], actual['inventory'])
            if bound['outside_allowed'] or actual['sha256'] in (m.TEMPLATE_GIT_OLD, m.TEMPLATE_GIT_S2):
                drifts.append(dict(kind='template-git-bound', outside=bound['outside_allowed'][:50]))
        elif path in c.s2['trees'] and trees[path] != c.s2['trees'][path]:
            drifts.append(dict(kind='s2-tree', path=path, expected=c.s2['trees'][path], actual=trees[path]))
    require(set(c.s2['trees']) <= set(trees), 'an S2-accepted tree is not an M6 tree')
    protected = {}
    for item in md['protected_trees']:
        path = item['pin']['path']
        actual = o.tree_snapshot(path, protected=True)
        protected[path] = actual
        meta = actual['inventory']['.']
        if (actual['sha256'] != item['pin']['sha256'] or meta['mode'] != item['pin']['mode']
                or any(meta[k] != item[k] for k in ('device', 'inode', 'uid', 'gid'))):
            drifts.append(dict(kind='protected', path=path))
    absent = {path: not os.path.lexists(path) for path in md['absent']}
    repositories = {}
    repos = [r for r in manifest['integrity']['repositories'] if r['name'] != m.M5_AUTHORITY_NAME]
    for repo in repos + [dict(name=m.AUTHORITY_NAME, path=m.AUTHORITY, commit=m.TEMPLATE_COMMIT)]:
        head = p.git(repo['path'], 'rev-parse', 'HEAD')
        status = p.git(repo['path'], 'status', '--porcelain', '--untracked-files=normal')
        repositories[repo['name']] = dict(head=head, status=status)
        if head['stdout'].strip() != repo['commit'] or status['returncode'] != 0 or status['stdout']:
            drifts.append(dict(kind='repository', name=repo['name']))
    ignored = p.git(m.AUTHORITY, 'status', '--porcelain', '--ignored', '--untracked-files=all')
    if ignored['returncode'] != 0 or ignored['stdout']:
        drifts.append(dict(kind='authority-ignored-or-untracked', actual=ignored))
    config = p.git(p.TEMPLATE, 'config', '--file', str(p.TEMPLATE/'.git/config'), '--list')
    replaced = p.git(p.TEMPLATE, 'for-each-ref', 'refs/replace')
    config_check = config_drift(config['stdout'])
    if config['returncode'] != 0 or any(config_check[k] for k in config_check) or replaced['stdout']:
        drifts.append(dict(kind='template-git-config', check=config_check, replaced=replaced))
    canonical = p.checkout_state()
    if canonical[0] != m.TEMPLATE_COMMIT or canonical[1] != 1 or canonical[2] != p.UNTRACKED:
        drifts.append(dict(kind='canonical-checkout', actual=canonical))
    runtime = m.r7.c.runtime_readiness()
    mount = m.r7.r6.r4.current_mount()
    after_host = o.host_observation()
    scope = s.quiet_scope(after_host)
    suspension = s.pin(p.SUSPENSION, links)
    require(after_host == host and scope == quiet['scope'] and suspension['sha256'] == m.SUSPENSION_SHA,
            'host, scope or suspension changed during the capture')
    if not all(absent.values()):
        drifts.append(dict(kind='absent', paths=[k for k, v in absent.items() if not v]))
    closure = dict(host=host, pins=pins, suspension=suspension, trees=trees, cache=cache, protected=protected,
                   links=links, scope=scope)
    result = dict(schema='ga-e0t1.15.m6-baseline.v1', closure=closure, runtime=runtime, mount=mount,
                  pin_changes=changes, drifts=drifts, repositories=repositories, canonical_checkout=canonical,
                  template_git_config=config, s2_observation_sha256=p.S2_OBSERVATION_SHA,
                  prerequisites={step: digest(c.record_path(step).read_bytes()) for step in p.STEPS},
                  candidate_sha256=c.expected, preparation_only=True, live_acceptance=False, worker_release=False)
    os.mkdir(out, 0o700)
    name = 'baseline.json' if not drifts else 'refused.json'
    data = (json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n').encode()
    p.write_exclusive(out/name, data, 0o600)
    print(json.dumps(dict(evidence=str(out/name), sha256=digest(data), drifts=drifts[:20],
                          pin_changes=[x['path'] for x in changes], worker_release=False)))
    require(not drifts, 'capture refused; record kept')


if __name__ == '__main__':
    main()
