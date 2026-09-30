"""M8 baseline capture (ga-e0t1.18, Operations lane adoption). Read-only except its own record under reports/m8-capture.

  python3 -I -B capture_m8.py <manifest_candidate.py sha256>

Runs in the supervisor host namespaces as UID 1000, before any M8 preparation. The reference is the frozen M7
baseline (reports/m7-capture/baseline.json 28d65524), which the M7 executor accepted. Since then exactly three
reviewed changes touched pins it holds, each admitted only as its exact before -> after pair:
- the P8 worker receipt refresh: .gc/runtime/provisioning/receipt.json 7cf59ab9 -> 23eeb222;
- the ga-6utp r12 activation: managed/rig-permissions.json d22cf4c1 -> 1225b7c5 and
  managed/rig-permissions.toml cba75f87 -> df688a29.
Every other M7-baseline pin, tree, protected tree, link, the scope, the suspension record and the host must be
exact; the cache content must be exact with only the Git bookkeeping times cache_drift admits. Every M8 target
pin (including the new backup and the two agent files) and repository is exact, the installed pair is M7,
and the sequence 15 receipt is unchanged. From the capture until restore-accepted nobody runs gc, workflow.py
or a Bead write.
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
M7_BASELINE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m7-capture/baseline.json')
M7_BASELINE_SHA = '28d655241ab6b5282000d79be9c5abfefaa3369f23ee9ea1abc95a4433bb700b'
M7_TREES = 49
M7_PINS = 760
# The exact reviewed pin changes since the M7 baseline: path -> (M7 sha256, current sha256).
RECEIPT_PATH = '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json'
PIN_CHANGES = {
    RECEIPT_PATH: ('7cf59ab9e5a43fd7bca97028e7faaa2b2f9bfb927a663b4588c66e846e4e425d',
                   '23eeb222d6d5c0afcf8dc8c01a99dfc7b57fbecfdbc0a1f7ca83d3319181d78e'),
    '/home/loucmane/gascity/city/managed/rig-permissions.json': (
        'd22cf4c14650e465b6b530e17d16b601079aa1e7dd52b1b76403cc58299c8adf',
        '1225b7c57ae69fd068ea35117431ae05e09ee493c01bc11a46ac45b77b950c8e'),
    '/home/loucmane/gascity/city/managed/rig-permissions.toml': (
        'cba75f87a373a078c11832609c274bd7eaa592b435545ef203ba6211f4f86725',
        'df688a29446cb381b734847ec9a255e470c710498cbfe2b713a9e85b052575a5'),
}


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
    """Pure: M7-baseline pins that changed, and which of those are not an allowed exact before -> after pair.

    An allowed change must start at its M7 digest and end at its reviewed digest with mode, uid and gid unchanged
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
    """The exact M8 pins, tree paths and links, derived from the installed M7 manifest."""
    md = manifest['metadata']
    rows = md['inputs'] + md['runtime'] + [md['writer']] + manifest['integrity']['files']
    rows += [dict(path=f['destination'], sha256=f['sha256'], mode=f['mode'])
             for f in [manifest['core']] + manifest['managed_files']]
    expected = {row['path']: dict(sha256=row['sha256'], mode=row['mode']) for row in rows}
    for path, _, after in m.CHANGED_INPUTS:
        expected[path] = dict(expected[path], sha256=after)
    expected[m.BACKUP] = dict(sha256=m.NEW, mode=0o755)
    for path, value in m.AGENT_FILES:
        expected[path] = dict(sha256=value, mode=0o644)
    trees = {p['path']: p['mode'] for p in md['trees']}
    links = {p['path']: p['target'] for p in md['links']}
    return expected, trees, links


def cache_drift(live, accepted):
    """Pure: the cache against the accepted reference record. Returns (bookkeeping, problems).

    The tree record (digest, entries, bytes) must be exact. In the full inventory, only mtime_ns and ctime_ns
    may change, and only on a cache repository's own `<key>/.git` entry or below it: a `gc bd` call (the
    coordinator's 2026-09-26 04:58:00Z workflow.py note on ga-e0t1, after sequence 15) touches that Git
    bookkeeping without changing content. Everything else is a problem. The capture binds the live inventory
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


def tree_drift(path, record, accepted_trees, manifest_trees):
    """Pure: a tree the accepted reference covers must equal it exactly; any other must keep its manifest digest."""
    if path in accepted_trees:
        return record != accepted_trees[path]
    return record['sha256'] != manifest_trees[path]


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    require(len(sys.argv) == 2 and len(sys.argv[1]) == 64, 'usage: capture_m8.py <candidate sha256>')
    p = load(PREREQS, PREREQS_SHA, 'm6_prereqs_helpers')
    capture_m6 = load(CAPTURE_M6, CAPTURE_M6_SHA, 'm6_capture_helpers')
    m = load(HERE/'manifest_candidate.py', sys.argv[1], 'm8_candidate')
    graph = load(HERE/'source_runtime.py', RUNTIME_SHA, 'pinned_runtime').legacy()
    o, s = graph['observe_recovery'], graph['recovery_state']
    load(HERE/'metadata_closure.py', CLOSURE_SHA, 'm8_closure').install_policy(o, s, m.WATCHDOG_IMAGE)
    o.GC_SHA = m.NEW
    raw = M7_BASELINE.read_bytes()
    require(digest(raw) == M7_BASELINE_SHA, 'M7 accepted baseline drift')
    reference = json.loads(raw)
    require(reference['drifts'] == [], 'M7 baseline is not an accepted capture')
    accepted = reference['closure']
    require(len(accepted['pins']) == M7_PINS and len(accepted['trees']) == M7_TREES, 'M7 baseline cardinality')
    out = Path(m.O + '/reports/m8-capture')
    require(not os.path.lexists(out) and not os.path.lexists(m.ROOT), 'capture or package consumed')
    manifest = s.read(p.INSTALLED, m.OLD_MANIFEST_SHA)
    s.read(p.INSTALLED_RECEIPT, m.OLD_RECEIPT_SHA)
    receipt = m.receipt()
    md = manifest['metadata']
    slot = p.quiet_slot()
    host = o.host_observation()
    require(host == accepted['host'], 'host is not the M7 accepted epoch')
    scope = s.quiet_scope(host)
    require(scope == accepted['scope'], 'scope is not the M7 accepted scope')
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
        drifts.append(dict(kind='m7-baseline-pins', unexpected=unexpected, changed=changed))
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
        if tree_drift(path, trees[path], accepted['trees'], manifest_trees):
            drifts.append(dict(kind='tree', path=path, actual=trees[path]))
    require(set(accepted['trees']) <= set(trees), 'an M7 baseline tree is not an M8 tree')
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
        if head['stdout'].strip() != repo['commit'] or status['returncode'] != 0 or status['stdout']:
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
    require(after_host == host and after_scope == scope and suspension == accepted['suspension']
            and suspension['sha256'] == m.SUSPENSION_SHA, 'host, scope or suspension changed during the capture')
    if not all(absent.values()):
        drifts.append(dict(kind='absent', paths=[k for k, v in absent.items() if not v]))
    closure = dict(host=host, pins=pins, suspension=suspension, trees=trees, cache=cache, protected=protected,
                   links=links, scope=scope)
    result = dict(schema='ga-e0t1.18.m8-baseline.v1', closure=closure, runtime=runtime, mount=mount,
                  drifts=drifts, cache_bookkeeping=cache_bookkeeping, repositories=repositories, canonical_checkout=canonical,
                  template_git_config=config, m7_baseline_sha256=M7_BASELINE_SHA, pin_changes=changed, seq15_receipt=receipt,
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
