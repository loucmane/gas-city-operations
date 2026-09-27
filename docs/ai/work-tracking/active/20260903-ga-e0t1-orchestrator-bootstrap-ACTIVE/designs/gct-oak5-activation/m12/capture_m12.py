"""M12 baseline capture (gct-oak5 codex choice). Read-only except its own record under reports/m12-capture.

  python3 -I -B capture_m12.py <manifest_candidate.py sha256>

Runs in the supervisor host namespaces as UID 1000, after the reviewed A2 codex-choice activation (cdcdaccd,
applied f17c55a9) and the M12 input prerequisite (prereqs_m12.py), and before any M12 preparation. The reference is
the frozen M11 baseline (reports/m11-capture/baseline.json 4000f7f3, 773 pins, 50 trees), which the M11 executor
accepted. Since then exactly these reviewed changes touched what it holds, each admitted only as its exact
before -> after pair:
- P12 (gct-oak5): the worker receipt .gc/runtime/provisioning/receipt.json 06a3f58a -> 7125be84;
- A2: city.toml b0eeb168 -> bdcec254.
The suspension record is unchanged (a3306567), and the city and every one of the seven rigs are still suspended.
Every other M11-baseline pin, tree, protected tree and link, the scope and the host must be exact; the cache must be
exact apart from the Git bookkeeping times cache_drift admits. Every M12 target pin (including the new city source)
is exact, the installed pair is M11, the canonical checkout is 3474abfa with exactly its two known untracked
directories, and the sequence 16 receipt is the root-custodied 1108b724. A pinned repository marked allow_dirty
(M11's canonical Template authority) is not required to have an empty status; the canonical checkout check proves
its exact untracked set. From the capture until restore-accepted nobody runs gc, workflow.py, a Bead write or git
in a pinned repository.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import types

HERE = Path(__file__).parent
RUNTIME_SHA = '2585357a808d8f36604d4bf45a39a5363ba87c8d719413ba42d9fd0fac71973f'  # source_runtime.py
CLOSURE_SHA = 'ce310593418e30b89f08645824c6cdd5b700fcff60b12f688fffc3d42d31d5d8'  # metadata_closure.py (M7 bytes)
# The reviewed M6 prerequisite helpers (quiet slot, read-only git, checkout state, exclusive writes). Only
# functions are used; its Context and steps are never called.
PREREQS = HERE.parent.parent/'ga-e0t1.15-deploy/s3/prereqs_m6.py'
PREREQS_SHA = 'a36824b89d6feb23a6d9a7ade26127c4848e71df6e4a0f525e308b0f02bd006e'
CAPTURE_M6 = HERE.parent.parent/'ga-e0t1.15-deploy/s3/capture_m6.py'
CAPTURE_M6_SHA = '702d42a52aeb54efd2786807f88225fda4b61ed7a28f8ed18f53c067bb11472a'  # config_drift only
REFERENCE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m11-capture/baseline.json')
REFERENCE_SHA = '4000f7f3d37a2a572fc210ba201f0b6dedb08661f0c878c896f34a0426548a97'
REFERENCE_TREES = 50
REFERENCE_PINS = 773
# The exact reviewed pin changes since the M11 baseline: path -> (M11 baseline sha256, current sha256).
CITY = '/home/loucmane/gascity/city'
PIN_CHANGES = {
    CITY + '/.gc/runtime/provisioning/receipt.json': ('06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5',
                                                      '7125be84548a587e2d784d423a85cd6750f4b5087cfc8c4acbbc087ff1e79579'),
    CITY + '/city.toml': ('b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b',
                          'bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1'),
}
SUSPENSION_BEFORE = 'a3306567b3cf77e6371a870e6df239194574fab8f2dc3090ea55a5eeb14b4817'
RIGS = ['blog', 'gas-city-template', 'gascity', 'hpfetcher', 'taskmaster-bridge-exact', 'taskmaster-bridge-proof',
        'taskmaster-bridge-scratch']


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path, expected, name):
    raw = Path(path).read_bytes()
    require(expected is not None and digest(raw) == expected, str(path) + ' differs from the reviewed digest')
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def pin_changes(accepted_pins, live_pins, allowed):
    """Pure: reference closure pins that changed, and which are not an allowed exact before -> after pair.

    An allowed change must start at its reference digest and end at its reviewed digest with mode, uid and gid unchanged
    (the size may differ); every other pin must be identical.
    """
    changed, problems = [], []
    for path, before in accepted_pins.items():
        now = live_pins[path]
        if now == before:
            continue
        changed.append(path)
        if path not in allowed:
            problems.append(path)
            continue
        old, new = allowed[path]
        same = {k: v for k, v in before.items() if k not in ('sha256', 'size')} == {
            k: v for k, v in now.items() if k not in ('sha256', 'size')}
        if not (before['sha256'] == old and now['sha256'] == new and same):
            problems.append(path)
    for path in allowed:
        if path not in accepted_pins or live_pins[path]['sha256'] != allowed[path][1]:
            problems.append(path)
    return changed, sorted(set(problems))


def target(m, manifest):
    """The exact M12 pins, tree paths and links, derived from the installed M11 manifest."""
    md = manifest['metadata']
    rows = md['inputs'] + md['runtime'] + [md['writer']] + manifest['integrity']['files']
    rows += [dict(path=f['destination'], sha256=f['sha256'], mode=f['mode'])
             for f in [manifest['core']] + manifest['managed_files']]
    expected = {row['path']: dict(sha256=row['sha256'], mode=row['mode']) for row in rows}
    # Rows M12 removes (the templates/claude tree covers them) or moves away are no longer expected.
    for path in list(m.REMOVED_INPUTS) + [old for old, _ in m.SUPERSEDED_INPUTS]:
        expected.pop(path, None)
    for path, value, mode in m.NEW_INPUTS:
        expected[path] = dict(sha256=value, mode=mode)
    trees = {p['path']: p['mode'] for p in md['trees']}
    trees.update({path: 0o755 for path, _ in m.NEW_TREES})
    links = {p['path']: p['target'] for p in md['links']}
    return expected, trees, links


def cache_drift(live, accepted):
    """Pure: the cache against the accepted reference record. Returns (bookkeeping, problems).

    The tree record (digest, entries, bytes) must be exact. In the full inventory, only mtime_ns and ctime_ns
    may change, and only on a cache repository's own `<key>/.git` entry or below it: a `gc bd` call (such as a
    coordinator workflow.py note on ga-e0t1) touches that Git bookkeeping without changing content. Everything else is a problem. The capture binds the live inventory
    exactly, and quiescence holds from the capture until restore-accepted.
    """
    problems = [k for k in ('sha256', 'entries', 'file_bytes') if live[k] != accepted[k]]
    if set(live) != set(accepted) or set(live['inventory']) != set(accepted['inventory']):
        return [], problems + ['inventory path set']
    bookkeeping = []
    for key in sorted(live['inventory']):
        now, before = live['inventory'][key], accepted['inventory'][key]
        if now == before:
            continue
        fields = sorted(f for f in set(now) | set(before) if now.get(f) != before.get(f))
        parts = key.split('/')
        if set(fields) <= {'mtime_ns', 'ctime_ns'} and len(parts) >= 2 and parts[1] == '.git':
            bookkeeping.append(dict(path=key, fields=fields))
        else:
            problems.append(key)
    return bookkeeping, problems


def tree_drift(path, record, accepted_trees, manifest_trees, changes=None, new=None):
    """Pure: a tree the accepted reference covers must equal it exactly, unless it is an admitted exact
    before -> after change; a new M12 tree must have its pinned digest; any other keeps its manifest digest."""
    changes, new = changes or {}, new or {}
    if path in changes:
        before, after = changes[path]
        return accepted_trees.get(path, {}).get('sha256') != before or record['sha256'] != after
    if path in new:
        return path in accepted_trees or record['sha256'] != new[path]
    if path in accepted_trees:
        return record != accepted_trees[path]
    return record['sha256'] != manifest_trees[path]


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    require(len(sys.argv) == 2 and len(sys.argv[1]) == 64, 'usage: capture_m12.py <candidate sha256>')
    p = load(PREREQS, PREREQS_SHA, 'm6_prereqs_helpers')
    capture_m6 = load(CAPTURE_M6, CAPTURE_M6_SHA, 'm6_capture_helpers')
    m = load(HERE/'manifest_candidate.py', sys.argv[1], 'm12_candidate')
    graph = load(HERE/'source_runtime.py', RUNTIME_SHA, 'pinned_runtime').legacy()
    o, s = graph['observe_recovery'], graph['recovery_state']
    load(HERE/'metadata_closure.py', CLOSURE_SHA, 'm12_closure').install_policy(o, s, m.WATCHDOG_IMAGE)
    o.GC_SHA = m.NEW
    raw = REFERENCE.read_bytes()
    require(digest(raw) == REFERENCE_SHA, 'M11 baseline drift')
    reference = json.loads(raw)
    require(reference['schema'] == 'gct-oak5.m11-baseline.v1' and not reference['drifts'],
            'M11 baseline is not the accepted one')
    accepted = reference['closure']
    require(len(accepted['pins']) == REFERENCE_PINS and len(accepted['trees']) == REFERENCE_TREES,
            'M11 baseline closure cardinality')
    out = Path(m.O + '/reports/m12-capture')
    require(not os.path.lexists(out) and not os.path.lexists(m.ROOT), 'capture or package consumed')
    manifest = s.read(p.INSTALLED, m.OLD_MANIFEST_SHA)
    s.read(p.INSTALLED_RECEIPT, m.OLD_RECEIPT_SHA)
    receipt = m.receipt()
    md = manifest['metadata']
    slot = p.quiet_slot()
    host = o.host_observation()
    require(host == accepted['host'], 'host is not the M11 baseline epoch')
    scope = s.quiet_scope(host)
    require(scope == accepted['scope'], 'scope is not the M11 baseline scope')
    require(p.sha(p.SUSPENSION) == m.SUSPENSION_SHA, 'suspension record drift')
    expected, tree_paths, links = target(m, manifest)
    drifts = []
    for path, link_target in links.items():
        if not (os.path.islink(path) and os.readlink(path) == link_target):
            drifts.append(dict(kind='link', path=path))
    pins = {}
    for path in sorted(set(expected) | set(accepted['pins'])):
        pins[path] = s.pin(path, links)
    for path, want in expected.items():
        if pins[path]['sha256'] != want['sha256'] or pins[path]['mode'] != want['mode']:
            drifts.append(dict(kind='file', path=path, expected=want, actual=pins[path]))
    changed, unexpected = pin_changes(accepted['pins'], pins, PIN_CHANGES)
    if unexpected:
        drifts.append(dict(kind='m11-baseline-pins', unexpected=unexpected, changed=changed))
    cache_path = str(Path(md['gc_home'])/'cache/repos')
    manifest_trees = {t['path']: t['sha256'] for t in md['trees']}
    trees, cache = {}, None
    for path, mode in tree_paths.items():
        actual = o.tree_snapshot(path, cache=path == cache_path)
        trees[path] = {k: actual[k] for k in ('sha256', 'entries', 'file_bytes')}
        if path == cache_path:
            cache = actual
        if actual['inventory']['.']['mode'] != mode:
            drifts.append(dict(kind='tree-root-mode', path=path))
        if tree_drift(path, trees[path], accepted['trees'], manifest_trees, m.EXACT_TREES, dict(m.NEW_TREES)):
            drifts.append(dict(kind='tree', path=path, actual=trees[path]))
    require(set(accepted['trees']) <= set(trees), 'an M11 baseline tree is not an M12 tree')
    cache_bookkeeping, cache_problems = cache_drift(cache, accepted['cache'])
    if cache_problems:
        drifts.append(dict(kind='cache', problems=cache_problems[:50]))
    protected = {}
    for item in md['protected_trees']:
        path = item['pin']['path']
        actual = o.tree_snapshot(path, protected=True)
        protected[path] = actual
        meta = actual['inventory']['.']
        if (actual['sha256'] != item['pin']['sha256'] or meta['mode'] != item['pin']['mode']
                or any(meta[k] != item[k] for k in ('device', 'inode', 'uid', 'gid'))):
            drifts.append(dict(kind='protected', path=path))
    if protected != accepted['protected']:
        drifts.append(dict(kind='protected-accepted'))
    absent = {path: not os.path.lexists(path) for path in md['absent']}
    repositories = {}
    for repo in manifest['integrity']['repositories']:
        head = p.git(repo['path'], 'rev-parse', 'HEAD')
        status = p.git(repo['path'], 'status', '--porcelain', '--untracked-files=normal')
        repositories[repo['name']] = dict(head=head, status=status)
        # An allow_dirty authority (M11's canonical Template) may carry its known untracked directories; the
        # canonical checkout check below proves its exact status.
        if (head['stdout'].strip() != repo['commit'] or status['returncode'] != 0
                or (status['stdout'] and not repo.get('allow_dirty'))):
            drifts.append(dict(kind='repository', name=repo['name']))
    ignored = p.git(m.AUTHORITY, 'status', '--porcelain', '--ignored', '--untracked-files=all')
    if ignored['returncode'] != 0 or ignored['stdout']:
        drifts.append(dict(kind='authority-ignored-or-untracked', actual=ignored))
    config = p.git(p.TEMPLATE, 'config', '--file', str(p.TEMPLATE/'.git/config'), '--list')
    replaced = p.git(p.TEMPLATE, 'for-each-ref', 'refs/replace')
    config_check = capture_m6.config_drift(config['stdout'])
    if config['returncode'] != 0 or any(config_check[k] for k in config_check) or replaced['stdout']:
        drifts.append(dict(kind='template-git-config', check=config_check, replaced=replaced))
    canonical = p.checkout_state()
    if canonical[0] != m.TEMPLATE_COMMIT or canonical[1] != 1 or canonical[2] != p.UNTRACKED:
        drifts.append(dict(kind='canonical-checkout', actual=canonical))
    runtime = m.r7.c.runtime_readiness()
    mount = m.r7.r6.r4.current_mount()
    after_host = o.host_observation()
    after_scope = s.quiet_scope(after_host)
    suspension = s.pin(p.SUSPENSION, links)
    state = json.loads(Path(p.SUSPENSION).read_bytes())
    require(after_host == host and after_scope == scope and suspension['sha256'] == m.SUSPENSION_SHA
            and accepted['suspension']['sha256'] == SUSPENSION_BEFORE
            and {k: v for k, v in suspension.items() if k not in ('sha256', 'size')}
            == {k: v for k, v in accepted['suspension'].items() if k not in ('sha256', 'size')}
            and set(state) == {'city', 'rigs', 'updated_at'} and state['city'] == {'suspended': True}
            and sorted(state['rigs']) == RIGS and all(v == {'suspended': True} for v in state['rigs'].values()),
            'host, scope or suspension changed during the capture')
    if not all(absent.values()):
        drifts.append(dict(kind='absent', paths=[k for k, v in absent.items() if not v]))
    closure = dict(host=host, pins=pins, suspension=suspension, trees=trees, cache=cache, protected=protected,
                   links=links, scope=scope)
    result = dict(schema='gct-oak5.m12-baseline.v1', closure=closure, runtime=runtime, mount=mount,
                  drifts=drifts, cache_bookkeeping=cache_bookkeeping, repositories=repositories, canonical_checkout=canonical,
                  template_git_config=config, m11_baseline_sha256=REFERENCE_SHA, pin_changes=changed, seq16_receipt=receipt,
                  reconciler_slot=slot, candidate_sha256=sys.argv[1], preparation_only=True,
                  live_acceptance=False, worker_release=False)
    os.mkdir(out, 0o700)
    name = 'baseline.json' if not drifts else 'refused.json'
    data = (json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n').encode()
    p.write_exclusive(out/name, data, 0o600)
    print(json.dumps(dict(evidence=str(out/name), sha256=digest(data), drifts=drifts[:20], worker_release=False)))
    require(not drifts, 'capture refused; record kept')


if __name__ == '__main__':
    main()
