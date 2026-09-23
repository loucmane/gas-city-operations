"""Pure M5 metadata successor for Template 28539934 (gct-m1wh plus gct-er3h).

Successor fields follow the reviewed M3 correction. The data changes are the
operator-approved V1 layout of 2026-09-23: a fresh clean Template authority
worktree with complete explicit coverage, the unused python3.12/test pins
dropped, the exact re-pins that the live prerequisites produce (including the
rig registry synced to the 28539934 gascity profile), and the distribution
security update of libexpat installed by unattended-upgrade on 2026-09-23.
Every new digest is either a constant derived from Git objects, staged or
distribution bytes, or live bytes before the change (see derive_expected.py
and LAYOUT.md), or a tree digest taken from the frozen baseline. Nothing here
reads the host except the pinned baseline.
"""
import copy
import hashlib
import json
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/r9'
ROOT = O + '/reports/m5'
OLD_MANIFEST_SHA = 'a6324753cb238f8de5ed3af72eef9e3a425ab491dae62778f462849814eb1852'
OLD_RECEIPT_SHA = '482b5daf642881e268b33eba3b0814c4148d040a9d3bc3480819e3c9a5b0212b'
BASELINE_PATH = O + '/reports/m5-capture/baseline.json'
# Filled only after the quiet capture; the reviewed build refuses until then.
BASELINE_SHA = None
TEMPLATE = '/home/loucmane/gas-city-template'
TEMPLATE_COMMIT = '28539934fa742056e0a65710d5638ff559a21175'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority'
AUTHORITY_NAME = 'template-pr69-authority'
RELEASE_ID = 'template-pr69-opus55-metadata-m5-20260923'
CITY_SOURCE = O + '/reports/m5-inputs/city.toml'
R5R = O + '/reports/r5/r'
TEST_PREFIX = '/usr/lib/python3.12/test/'
TEST_PIN_COUNT = 57

# (path, predecessor sha256, successor sha256) for inputs whose bytes the live
# prerequisites change. Modes are unchanged and checked against the baseline.
CHANGED_INPUTS = (
    (TEMPLATE + '/lib/gct_claude_signing_worker.py',
     'bac4df82f58459973d383a0467c1238e27e9dbc405ac37acf6719d05111c13e1',
     '4e28d5b826a7471dec27e66ee3536233bbaa2ebc6ece162b4d3ca8cccd0970bd'),
    ('/home/loucmane/gascity/bin/claude',
     '26d020351e8112f4006790f3cfce43b4c9df0c1bb1d0e542364d64151b81d5ba',
     '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'),
    ('/home/loucmane/gascity/city/city.toml',
     '6594ee77b3efc30cd2f4cfa412541a5a1076fb324118fb8aec3df1d29b81528b',
     '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'),
    ('/home/loucmane/gascity/city/managed/rig-permissions.toml',
     'c7c11b8aa544ad40a82daea5232d2718790eeff8754bc3c50a7aa622dfa1f04e',
     'cba75f87a373a078c11832609c274bd7eaa592b435545ef203ba6211f4f86725'),
    ('/home/loucmane/gascity/city/managed/rig-permissions.json',
     '7fb9a74179d58c02abb33369b4f2b5a7f7a35522619ee48374e1de1e6cfc8265',
     'd22cf4c14650e465b6b530e17d16b601079aa1e7dd52b1b76403cc58299c8adf'),
    # libexpat1 2.6.1-2ubuntu0.4 -> 0.5, unattended-upgrade 2026-09-23 06:55:34;
    # dpkg --verify clean, md5 f0cbf5c6 equals the package record.
    ('/usr/lib/x86_64-linux-gnu/libexpat.so.1.9.1',
     'c42ff317838b4b4639e2ea801905f0317177c6df7e31b2f0d0240e3c3ac0cfde',
     'ec6c12d33bb8f9d0e90804121adf19930f36b1b2a4aeb6e1a454b89c7a50c801'),
)
CITY_OLD, CITY_NEW = CHANGED_INPUTS[2][1:]
RIGPERM_OLD, RIGPERM_NEW = CHANGED_INPUTS[3][1:]
REGISTRY_OLD, REGISTRY_NEW = CHANGED_INPUTS[4][1:]
CLI_OLD, CLI_NEW = CHANGED_INPUTS[1][1:]
CITY_SOURCE_OLD = O + '/reports/r5/i/07'
# Canonical Template files that 28539934 leaves byte-identical; the predecessor
# pins must already equal the 28539934 blobs (proved in test_manifest.py).
RETAINED_TEMPLATE_PINS = {
    TEMPLATE + '/bin/gct-claude-signing-worker':
        '9df9ea34e83ad7ce39328ffedc7c9b3a2aceef9abb537e7e27c4e85e884378e0',
    TEMPLATE + '/lib/gct_claude_subscription.py':
        '3b92bc92f3bc05a762c0008738550d8c48c0998fad6b4807578552643529639b',
    TEMPLATE + '/templates/claude/signing-provider.toml':
        'f820690b032fac347b75ac4c0bcf0e46f572a04be9063a5c63b754c4c74d2dc9',
    TEMPLATE + '/templates/claude/core-signing-control-policy.json':
        '16022d04533e3d6366cfc25b3ad76a3af2d7bd5da2ad7412d76b93fe4d3c1225',
}
NATIVE_VERSION_OLD = '2.1.263 (Claude Code)'
NATIVE_VERSION_NEW = '2.1.280 (Claude Code)'
VERSION_OLD = ('gct-claude-signing-worker 1 dependencies_sha256='
               'b7fee4467e83c7c9d07c2c421142f20297ad1cd3de93192713400aa01d8714b0')
VERSION_NEW = ('gct-claude-signing-worker 1 dependencies_sha256='
               'f36deb20efa5cc11781f1d9703b8e5e0d7897c6357260dff1045bcd86489ff34')
# Trees re-pinned from the frozen baseline: the Template common Git directory
# (fetch of 28539934, checkout advance, new linked worktree) and the r5/r
# authority clone. Its index, and five linked-worktree indexes inside the
# Template .git, were rewritten at 2026-09-23 01:39 by a plain git status of
# the read-only M4 investigation. HEAD is unchanged. capture.py bounds both diffs.
REPINNED_TREES = (TEMPLATE + '/.git', R5R)

# Complete coverage of the 277 tracked paths of Template 28539934: maximal
# link-free subtrees, individual regular files, and the two tracked links. No
# tree has a link below it, and both link targets are covered. The .git entry
# is the linked-worktree pointer file; its admin directory lies inside the
# already pinned Template .git tree.
AUTH_INPUTS = (
    ('.gitattributes', 'f921dd0588045145ee5b9e4b63f8fda5827a9bb9a57a4546f236b789e4f1b9c5', 420),
    ('.gitignore', 'b9061aa9177970cc802c6b247419689c31679d8f078049634a037329fe30761b', 420),
    ('AGENTS.md', 'f80441cf2c87c816b276c9726fcbe3d19a2ef1b32fa9a10215a59ce9efe5536e', 420),
    ('CLAUDE.md', '79e858c23bfd3680da5c52b70dbe2ae55c3d2b3287ca2a3eccac8c3e409e8fad', 420),
    ('README.md', '5d057f20ccf7c6d91ed99657f5d275a1c184289b60ff5cb8dc2f4aa10bbd042f', 420),
    ('city.toml', '31435a49f52c8a532f3390f9c70b2ac98c5e5f3215c820aedccffad4824965b9', 420),
    ('plans/2026-09-22-gct-er3h-opus-5-5-worker-profiles.md',
     '6224e472c0d3d8b7e57bc653a8af8c64ed37c1e781d1c2759ff8781c49bf2351', 420),
    ('plans/2026-09-22-gct-m1wh.1-native-prompt-delivery.md',
     '6de4efc460393a2a5a512e05ab4d8f63119c98e01726a02f2a6a36e91fb9ddc8', 420),
    ('plans/2026-09-22-gct-ovxn-forbid-direct-gpg-in-the-unsigned-candidate-worker-profile.md',
     '6b9064d19e41703b552433fc5f5a0541ab9e5121cd59a63756725860328ab4c0', 420),
    ('sessions/state.json', 'e0e26f0a530049a61fd01d2243ecfc902578023caff89dc9ad3d43a0d5e39dae', 420),
    ('taskmaster_beads.py', '33937f4f4427dd05b89bb3c4a7a4050f95fa62d51153d310e728a43ee09ff837', 420),
    ('.git', 'deabdafaba7ec87b78d650608707d26b80bfc5f44549a54e5488cdd52ac574be', 420),
)
AUTH_TREES = ('.beads', '.claude', '.codex', '.github', '.plan_state', 'agents', 'assets',
              'bin', 'docs', 'formulas', 'hooks', 'lib', 'managed', 'orders', 'patches',
              'schemas', 'sessions/2026', 'template-fragments', 'templates', 'tests')
AUTH_LINKS = (
    ('plans/current', '2026-09-22-gct-er3h-opus-5-5-worker-profiles.md'),
    ('sessions/current', '2026/09/2026-09-22-003-gct-er3h-opus-5-5-worker-profiles.md'),
)
INPUT_COUNT = 728 - TEST_PIN_COUNT + 2 + len(AUTH_INPUTS)
TREE_COUNT = 29 + len(AUTH_TREES)
LINK_COUNT = 21 + len(AUTH_LINKS)

P = Path(O + '/reports/ga-mutg-metadata-quiet-r9-20260920/manifest_candidate.py')
raw = P.read_bytes()
if hashlib.sha256(raw).hexdigest() != '8a9145f50f48254fbf82938b6a6137d7e78ea0ceb5586d6b09579a1954d8a72e':
    raise RuntimeError('reviewed predecessor helper drift')
prior = types.ModuleType('reviewed_predecessor'); prior.__file__ = str(P)
exec(compile(raw, str(P), 'exec', dont_inherit=True), prior.__dict__)
r7, b, require = prior.r7, prior.b, prior.require
NEW, RECEIPT_SHA, receipt = prior.NEW, prior.RECEIPT_SHA, prior.receipt


def _one(rows, key, value, reason):
    found = [row for row in rows if row[key] == value]
    require(len(found) == 1, reason)
    return found[0]


def _keyed(manifest):
    """Project every pin list onto path/name keys for a complete old/new map."""
    md = manifest['metadata']
    return {
        'inputs': {p['path']: p for p in md['inputs']},
        'trees': {p['path']: p for p in md['trees']},
        'links': {p['path']: p for p in md['links']},
        'repositories': {p['name']: p for p in manifest['integrity']['repositories']},
        'providers': {p['name']: p for p in manifest['integrity']['providers']},
        'files': {p['name']: p for p in manifest['integrity']['files']},
        'managed_files': {p['name']: p for p in manifest['managed_files']},
    }


def coverage_map(old, new):
    before, after = _keyed(old), _keyed(new)
    out = {}
    for kind in before:
        added = sorted(set(after[kind]) - set(before[kind]))
        removed = sorted(set(before[kind]) - set(after[kind]))
        changed = sorted(k for k in set(before[kind]) & set(after[kind])
                         if before[kind][k] != after[kind][k])
        out[kind] = dict(added=added, removed=removed,
                         changed={k: dict(before=before[kind][k], after=after[kind][k]) for k in changed})
    scalars = []
    for key in sorted(set(old) | set(new)):
        if key in ('metadata', 'integrity', 'managed_files'):
            continue
        if old.get(key) != new.get(key):
            scalars.append(dict(field='/' + key, before=old.get(key), after=new.get(key)))
    for key in sorted(set(old['metadata']) | set(new['metadata'])):
        if key in ('inputs', 'trees', 'links'):
            continue
        if old['metadata'].get(key) != new['metadata'].get(key):
            scalars.append(dict(field='/metadata/' + key, before=old['metadata'].get(key),
                                after=new['metadata'].get(key)))
    out['scalars'] = scalars
    return out


def assemble(old, closure, host, parents, transaction, attempt):
    """Pure construction from the installed predecessor and a frozen closure."""
    require(b.finalized(old) == old and host == closure['host'], 'manifest/host binding')
    require(b.hex64(transaction) and b.hex64(attempt) and transaction != attempt
        and transaction != old['metadata']['transaction'] and attempt != old['metadata']['attempt'],
        'fresh distinct transaction and attempt required')
    require(len(parents) == 3 and parents[0] == old['metadata']['parents'][0], 'platform parent drift')
    for parent, name in zip(parents[1:], ('b', 't')):
        require(set(parent) == set(parents[0]) and parent['path'] == ROOT+'/'+name
            and parent['uid'] == parent['gid'] == 1000 and parent['mode'] == 0o700
            and parent['entries'] == [] and type(parent['device']) is int and parent['device'] > 0
            and type(parent['inode']) is int and parent['inode'] > 0, 'fresh output parent identity')
    require(len({(p['device'], p['inode']) for p in parents}) == 3
        and not ({(p['device'], p['inode']) for p in parents[1:]} &
                 {(p['device'], p['inode']) for p in old['metadata']['parents']}), 'output alias/reuse')
    pins, trees, links = closure['pins'], closure['trees'], closure['links']
    out = copy.deepcopy(old); md = out['metadata']
    require(out['core']['sha256'] == md['writer']['sha256'] == NEW, 'unchanged installed Core binding')
    # Successor identity, exactly as reviewed for M3: follow the installed release.
    out['previous_sha256'] = old['core']['sha256']
    out['activation']['previous_commit'] = old['activation']['expected_commit']
    out['activation']['previous_version'] = old['activation']['expected_version']
    out['backup_path'] = '/var/tmp/ga-mutg-custody-build-20260920/gc-b'
    backup = pins[out['backup_path']]
    require(backup['sha256'] == NEW and backup['mode'] == out['core']['mode']
        and backup['uid'] == backup['gid'] == 1000, 'exact existing Core backup binding')
    require(out['backup_path'] not in {out['core']['source'], out['core']['destination']}
        and not any(p['path'] == out['backup_path'] for p in md['inputs']), 'backup alias or duplicate')
    md['inputs'].append(dict(name='', path=out['backup_path'], sha256=NEW, mode=backup['mode']))
    out['release_id'] = RELEASE_ID
    # The native wire uses predecessor struct order, not caller dictionary order.
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt,
        parents=copy.deepcopy(parents), evidence=ROOT+'/t')
    # Operator-approved narrowing: the signing worker never loads these files.
    dropped = [p for p in md['inputs'] if p['path'].startswith(TEST_PREFIX)]
    require(len(dropped) == TEST_PIN_COUNT, 'unused stdlib test pin cardinality')
    md['inputs'] = [p for p in md['inputs'] if not p['path'].startswith(TEST_PREFIX)]
    for path, before, after in CHANGED_INPUTS:
        pin = _one(md['inputs'], 'path', path, 'changed input cardinality: ' + path)
        require(pin['sha256'] == before, 'exact predecessor input: ' + path)
        require(pins[path]['sha256'] == after and pins[path]['mode'] == pin['mode'],
            'reviewed successor input: ' + path)
        pin['sha256'] = after
    for path, digest in RETAINED_TEMPLATE_PINS.items():
        pin = _one(md['inputs'], 'path', path, 'retained Template input: ' + path)
        require(pin['sha256'] == digest and pins[path]['sha256'] == digest, 'retained Template bytes: ' + path)
    for name, before, after in (('rig-permissions.toml', RIGPERM_OLD, RIGPERM_NEW),
                                ('rig-permissions.json', REGISTRY_OLD, REGISTRY_NEW)):
        files = _one(out['integrity']['files'], 'name', name, 'integrity file: ' + name)
        require(files['sha256'] == before, 'exact predecessor integrity file: ' + name)
        files['sha256'] = after
    native = _one(out['integrity']['providers'], 'name', 'claude-native', 'native provider')
    require(native['sha256'] == CLI_OLD and native['version'] == NATIVE_VERSION_OLD
        and native['path'] == native['resolved_path'] == '/home/loucmane/gascity/bin/claude',
        'exact predecessor native provider')
    native.update(sha256=CLI_NEW, version=NATIVE_VERSION_NEW)
    worker = _one(out['integrity']['providers'], 'name', 'claude', 'signing provider')
    require(worker['version'] == VERSION_OLD
        and worker['path'] == worker['resolved_path'] == TEMPLATE + '/bin/gct-claude-signing-worker'
        and worker['sha256'] == RETAINED_TEMPLATE_PINS[worker['path']], 'exact predecessor worker')
    worker['version'] = VERSION_NEW
    config = _one(out['managed_files'], 'name', 'city-config', 'city config managed file')
    require(config['sha256'] == config['previous_sha256'] == CITY_OLD
        and config['destination'] == '/home/loucmane/gascity/city/city.toml'
        and config['backup_path'] == O + '/reports/r5/i/00'
        and config['source'] == CITY_SOURCE_OLD, 'exact predecessor city config')
    # Already installed out of band; the unchanged backup proves the predecessor
    # bytes, so the native metadata-only path reuses it and mutates nothing.
    require(pins[config['backup_path']]['sha256'] == CITY_OLD, 'city config backup bytes')
    require(pins[CITY_SOURCE]['sha256'] == CITY_NEW and pins[CITY_SOURCE]['mode'] == 0o644,
        'city config successor source bytes')
    require(not any(p['path'] == CITY_SOURCE for p in md['inputs']), 'city source duplicate')
    config.update(sha256=CITY_NEW, source=CITY_SOURCE)
    md['inputs'].append(dict(name='', path=CITY_SOURCE, sha256=CITY_NEW, mode=0o644))
    for path in REPINNED_TREES:
        pin = _one(md['trees'], 'path', path, 'repinned tree cardinality: ' + path)
        require(trees[path]['sha256'] != pin['sha256'], 'repinned tree unexpectedly unchanged: ' + path)
        pin['sha256'] = trees[path]['sha256']
    repos = out['integrity']['repositories']
    require(not any(p['path'] == AUTHORITY or p['name'] == AUTHORITY_NAME
                    or p['commit'] == TEMPLATE_COMMIT for p in repos), 'authority already present')
    repos.append(dict(name=AUTHORITY_NAME, path=AUTHORITY, commit=TEMPLATE_COMMIT))
    existing = {p['path'] for p in md['inputs']} | {p['path'] for p in md['trees']} | {
        p['path'] for p in md['links']}
    require(not any(x == AUTHORITY or x.startswith(AUTHORITY + '/') or AUTHORITY.startswith(x + '/')
                    for x in existing), 'authority coverage overlaps an existing pin')
    for relative, digest, mode in AUTH_INPUTS:
        path = AUTHORITY + '/' + relative
        require(pins[path]['sha256'] == digest and pins[path]['mode'] == mode, 'authority file: ' + path)
        md['inputs'].append(dict(name='', path=path, sha256=digest, mode=mode))
    for relative in AUTH_TREES:
        path = AUTHORITY + '/' + relative
        require(path in trees and b.hex64(trees[path]['sha256']), 'authority tree: ' + path)
        md['trees'].append(dict(name='', path=path, sha256=trees[path]['sha256'], mode=0o755))
    for relative, target in AUTH_LINKS:
        path = AUTHORITY + '/' + relative
        require(links.get(path) == target, 'authority link: ' + path)
        md['links'].append(dict(path=path, target=target))
    for kind, digest in (('manifest', OLD_MANIFEST_SHA), ('receipt', OLD_RECEIPT_SHA)):
        name = 'install-'+kind+'.before.json'
        previous = out['previous_metadata'][kind+'_backup_path']
        require(previous == OLD_ROOT+'/b/'+name, 'previous backup binding')
        out['previous_metadata'][kind+'_sha256'] = digest
        out['previous_metadata'][kind+'_backup_path'] = ROOT+'/b/'+name
        live = [p for p in md['preimages'] if p['path'] == '/home/loucmane/gascity/city/.gc/platform/install-'+kind+'.json']
        prior_backup = [p for p in md['preimages'] if p['path'] == previous]
        require(len(live) == len(prior_backup) == 1 and set(prior_backup[0]) == {'path'}, 'preimage cardinality')
        live[0]['sha256'] = digest; prior_backup[0]['path'] = ROOT+'/b/'+name
    require(len(md['inputs']) == INPUT_COUNT and len(md['trees']) == TREE_COUNT
        and len(md['links']) == LINK_COUNT, 'coverage cardinality drift')
    require(len({p['path'] for p in md['inputs']}) == INPUT_COUNT
        and len({p['path'] for p in md['trees']}) == TREE_COUNT
        and len({p['path'] for p in md['links']}) == LINK_COUNT, 'duplicate pin path')
    out = b.finalized(out); frame = b.frame_bound(out)
    return out, dict(preparation_only=True, live_acceptance=False, coverage_map=coverage_map(old, out),
        dropped_test_pins=sorted(p['path'] for p in dropped), frame=frame, input_count=INPUT_COUNT,
        tree_count=TREE_COUNT, link_count=LINK_COUNT, runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed R9 manifest drift')
    require(BASELINE_SHA is not None, 'baseline not yet frozen and reviewed')
    require(hashlib.sha256(baseline_bytes).hexdigest() == BASELINE_SHA, 'current baseline drift')
    old = json.loads(old_bytes); closure = json.loads(baseline_bytes)['closure']
    return assemble(old, closure, host, parents, transaction, attempt)
