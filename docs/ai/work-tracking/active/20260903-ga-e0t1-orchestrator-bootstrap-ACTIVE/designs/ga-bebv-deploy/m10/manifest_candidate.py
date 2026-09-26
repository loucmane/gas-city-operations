"""Pure M10 metadata successor (ga-bebv S3): the sequence 16 Core and the replace-mode city.toml over M9.

The predecessor is the installed M9 manifest (file 5a29dc59, reports/m9/q/manifest.json). M10 combines the
M7 Core pattern with the M5/M6 city-config pattern, and changes nothing else:

Core (M7 pattern). Sequence 16 (ga-bebv S2, accepted 2026-09-27) replaced gc fce2e9a0 with 207a78e2, built from
f45a6262 (tree f1011ada, Core PR 49 merge 0b63856a, the ga-6umo hotfix; receipt 1108b724). Core's
validateSuccessor requires previous_sha256 to equal the predecessor's core.sha256 and activation.previous_commit
to equal its expected_commit. M9's core is fce2e9a0 from deefb98b, and M8 and M9 already carry exactly those
values (previous_sha256 fce2e9a0 with the ga-e0t1.18 gc-b backup, previous_commit deefb98b), so they stay. What
moves: core.source and core.sha256 (the sequence 16 build source gc-a, 207a78e2), the writer and the installed gc
input (207a78e2), activation.expected_commit (f45a6262, the build's `gc version` commit), and the input that
pinned M9's build source, which moves in place to the new gc-a (0755; SUPERSEDED_INPUTS below).

City config (M5/M6 pattern). The reviewed prerequisite (prereqs_m10.py) installs the city.toml that
make_city.py derives from the installed bytes (4f7e170f -> e5b68c40): the claude and codex providers switch to
replace-mode option schemas, and eight [[patches.agent]] entries set work_dir_roots. Metadata-only adoption
needs the managed file already installed and its previous bytes backed up. So city-config takes source
reports/m10-inputs/city.toml and sha256 e5b68c40. It keeps previous_sha256 4f7e170f (M9's own sha256, which
Core's successor rule requires) and the backup reports/m6-inputs/city.toml.before, which already holds exactly
those bytes and is already an input. The live city.toml input moves to e5b68c40, and the input that pinned
M9's source (reports/m5-inputs/city.toml) moves in place to the new source (0644).

Tree: rigs/gascity/.git/objects takes the digest the sequence 16 closure accepted (98e871c4 -> aed766a6; the
S1 build source fetch). The cache is unchanged (sequence 16 admitted no cache key).

Suspension: the record the sequence 16 closure accepted (6d89f537). WATCHDOG_IMAGE stays 69d00186: the dolt
watchdog that survived sequences 14 to 16 still maps that image (checked 2026-09-27).

Every new digest is a build, receipt, closure or generator value. Nothing here reads the host except the pinned
baseline and the root-custodied broker receipt.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/m9'
ROOT = O + '/reports/m10'
OLD_MANIFEST_SHA = '5a29dc596af192e0f314391453d25d6be548695a0defd64bdfc2fa76554e4993'
OLD_RECEIPT_SHA = '4c19802fc60f12695ec4080497b195278943185c4e8758f41feeac50e5b16092'
OLD_RELEASE_ID = 'ops-candidate-provider-metadata-m9-20260926'
BASELINE_PATH = O + '/reports/m10-capture/baseline.json'
# Frozen by the capture after the city prerequisite, then reviewed. Until then build() refuses.
BASELINE_SHA = None
SUSPENSION_SHA = '6d89f53738fbae8a2f07c7026de61207704ed44bbde79c0fc1f3a1d18b166ee0'
TEMPLATE = '/home/loucmane/gas-city-template'
TEMPLATE_COMMIT = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
AUTHORITY_NAME = 'template-pr71-authority'
RELEASE_ID = 'ga-bebv-core-seq16-city-metadata-m10-20260927'

# Core (the M7 pattern).
GC = '/home/loucmane/gascity/bin/gc'
OLD_SOURCE = '/var/tmp/ga-e0t1.18-build-20260926/gc-a'
BACKUP = '/var/tmp/ga-e0t1.18-build-20260926/gc-b'
ARTIFACT = '/var/tmp/ga-bebv-build-20260927/gc-a'
OLD = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
OLD_SIZE = 134062284
NEW = '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f'
NEW_SIZE = 134146157
OLD_COMMIT = 'deefb98b2aed07875df31351d081fbac195cb1cd'
COMMIT = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
VERSION = 'dev'
# The surviving dolt watchdog's image (started before sequence 14); see metadata_closure.configure.
WATCHDOG_IMAGE = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'

# City config (the M5/M6 pattern). make_city.py derives CITY_NEW from CITY_OLD.
CITY = '/home/loucmane/gascity/city'
CITY_TOML = CITY + '/city.toml'
CITY_OLD = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
CITY_NEW = 'e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077'
CITY_OLD_SOURCE = O + '/reports/m5-inputs/city.toml'
CITY_SOURCE = O + '/reports/m10-inputs/city.toml'
CITY_CONFIG_BACKUP = O + '/reports/m6-inputs/city.toml.before'

# The pins M10 moves or adds, as (path, sha256, mode). The executor's gate extract reads this name.
NEW_INPUTS = ((GC, NEW, 0o755), (ARTIFACT, NEW, 0o755), (CITY_TOML, CITY_NEW, 0o644), (CITY_SOURCE, CITY_NEW, 0o644))

# Unchanged since M9; asserted so a stale predecessor refuses.
NATIVE_CLI = '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
NATIVE_VERSION = '2.1.280 (Claude Code)'
PROVIDER_NAMES = ['claude-native', 'codex', 'claude', 'claude']
CANDIDATE_WRAPPER = TEMPLATE + '/bin/gct-claude-candidate-worker'
CANDIDATE_WRAPPER_SHA = 'e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3'

# Trees. The Core rig object tree takes the sequence 16 accepted digest; the cache is unchanged.
ODB = CITY + '/rigs/gascity/.git/objects'
CACHE = '/home/loucmane/gascity/home/cache/repos'
EXACT_TREES = {
    ODB: ('98e871c4255084b7e8c7cd41021935193431a17a63933ba2826d2e0f1adcc07f',
          'aed766a6c27497b46b55380011ec4e345e1259d737ed7f1ce64490ded44bedc8'),
}
CACHE_SHA = '4b284f6741eb8a4e2273fe94bd7e5d24b8ae318ca862170b80c6fd75f37f72be'
# Two M9 inputs pinned files that M10 no longer references: M9's core.source (the ga-e0t1.18 gc-a) and M9's
# city-config source (reports/m5-inputs/city.toml). Each such row moves in place to its M10 successor (the
# sequence 16 gc-a, reports/m10-inputs/city.toml) instead of a new row being appended. Appending both left only
# 274 spare frame bytes; moving them keeps M9's counts. The two superseded files stay on disk, unchanged.
SUPERSEDED_INPUTS = ((OLD_SOURCE, ARTIFACT), (CITY_OLD_SOURCE, CITY_SOURCE))
# M9 counts 696 inputs, 49 trees, 23 links, 4 providers; M10 keeps them.
INPUT_COUNT = 696
TREE_COUNT = 49
LINK_COUNT = 23
PROVIDER_COUNT = 4
# M9's floor. Only the fresh parents' device and inode vary at prepare, at most 72 bytes wider than the
# test's synthetic values.
FRAME_FLOOR = 512

# The sequence 16 broker receipt (ga-bebv S2).
REQUEST = '8beebd04f5bcc680d90d49df4292febb79505bbab87c4413e06ed559ae10b322'
RECEIPT_SHA = '1108b72494102cee3cde5df32a4b465f3121240c2cd9d43ad262f3407578904f'
RECEIPT_SIZE = 1235

P = Path(O + '/reports/ga-mutg-metadata-quiet-r9-20260920/manifest_candidate.py')
raw = P.read_bytes()
if hashlib.sha256(raw).hexdigest() != '8a9145f50f48254fbf82938b6a6137d7e78ea0ceb5586d6b09579a1954d8a72e':
    raise RuntimeError('reviewed predecessor helper drift')
prior = types.ModuleType('reviewed_predecessor'); prior.__file__ = str(P)
exec(compile(raw, str(P), 'exec', dont_inherit=True), prior.__dict__)
r7, b, require = prior.r7, prior.b, prior.require


def _one(rows, key, value, reason):
    found = [row for row in rows if row[key] == value]
    require(len(found) == 1, reason)
    return found[0]


def assemble(old, closure, host, parents, transaction, attempt):
    """Pure construction from the installed M9 predecessor and a frozen closure."""
    require(b.finalized(old) == old and host == closure['host'], 'manifest/host binding')
    require(old['release_id'] == OLD_RELEASE_ID, 'installed release is not M9')
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

    # Core: the M7 pattern. previous_sha256, backup_path and previous_commit already name the M9 core.
    require(out['core'] == dict(name='gc', source=OLD_SOURCE, destination=GC, sha256=OLD, mode=0o755)
            and md['writer'] == dict(name='', path=GC, sha256=OLD, mode=0o755), 'exact installed Core predecessor')
    require(out['previous_sha256'] == OLD and out['backup_path'] == BACKUP, 'exact M9 previous image and backup')
    require(out['activation'] == dict(expected_commit=OLD_COMMIT, expected_version=VERSION,
                                      previous_commit=OLD_COMMIT, previous_version=VERSION),
            'exact predecessor activation')
    require(pins[GC]['sha256'] == NEW and pins[GC]['size'] == NEW_SIZE and pins[GC]['mode'] == 0o755,
            'installed sequence 16 image')
    require(pins[ARTIFACT]['sha256'] == NEW and pins[ARTIFACT]['size'] == NEW_SIZE and pins[ARTIFACT]['mode'] == 0o755,
            'sequence 16 build source')
    require(pins[BACKUP]['sha256'] == OLD and pins[BACKUP]['size'] == OLD_SIZE and pins[BACKUP]['mode'] == 0o755,
            'previous image backup')
    require(_one(md['inputs'], 'path', BACKUP, 'backup input cardinality') == dict(
        name='', path=BACKUP, sha256=OLD, mode=0o755), 'backup input')
    require(not any(p['path'] == ARTIFACT for p in md['inputs']), 'build source already present')
    out['core'].update(source=ARTIFACT, sha256=NEW)
    # Core's successor rule: previous_commit is the predecessor's expected_commit, which stays deefb98b.
    out['activation']['expected_commit'] = COMMIT
    md['writer']['sha256'] = NEW
    _one(md['inputs'], 'path', GC, 'installed Core input cardinality')['sha256'] = NEW
    # The input that pinned M9's core.source moves, in place, to M10's (see SUPERSEDED_INPUTS).
    source_input = _one(md['inputs'], 'path', OLD_SOURCE, 'predecessor build source input cardinality')
    require(source_input == dict(name='', path=OLD_SOURCE, sha256=OLD, mode=0o755), 'predecessor build source input')
    source_input.update(path=ARTIFACT, sha256=NEW)

    out['release_id'] = RELEASE_ID
    # The native wire uses predecessor struct order, not caller dictionary order.
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt, parents=copy.deepcopy(parents), evidence=ROOT+'/t')

    # City config: the M5/M6 pattern, with the M6 backup of the predecessor bytes reused.
    config = _one(out['managed_files'], 'name', 'city-config', 'city config managed file')
    require(config == dict(name='city-config', source=CITY_OLD_SOURCE, destination=CITY_TOML, sha256=CITY_OLD,
                           mode=0o644, previous_sha256=CITY_OLD, backup_path=CITY_CONFIG_BACKUP),
            'exact predecessor city config')
    require(all(f['previous_sha256'] == f['sha256'] for f in out['managed_files']),
            'every managed file already carries its own baseline')
    require(pins[CITY_TOML]['sha256'] == CITY_NEW and pins[CITY_TOML]['mode'] == 0o644, 'installed city config')
    require(pins[CITY_SOURCE]['sha256'] == CITY_NEW and pins[CITY_SOURCE]['mode'] == 0o644, 'city config source')
    require(pins[CITY_CONFIG_BACKUP]['sha256'] == CITY_OLD and pins[CITY_CONFIG_BACKUP]['mode'] == 0o644,
            'city config backup bytes')
    require(_one(md['inputs'], 'path', CITY_CONFIG_BACKUP, 'city backup input cardinality')['sha256'] == CITY_OLD,
            'city backup input')
    require(not any(p['path'] == CITY_SOURCE for p in md['inputs']), 'city source already present')
    config.update(source=CITY_SOURCE, sha256=CITY_NEW)
    city_input = _one(md['inputs'], 'path', CITY_TOML, 'installed city input cardinality')
    require(city_input == dict(name='', path=CITY_TOML, sha256=CITY_OLD, mode=0o644), 'installed city input')
    city_input['sha256'] = CITY_NEW
    # The input that pinned M9's city-config source moves, in place, to M10's (see SUPERSEDED_INPUTS).
    old_source_input = _one(md['inputs'], 'path', CITY_OLD_SOURCE, 'predecessor city source input cardinality')
    require(old_source_input == dict(name='', path=CITY_OLD_SOURCE, sha256=CITY_OLD, mode=0o644),
            'predecessor city source input')
    old_source_input.update(path=CITY_SOURCE, sha256=CITY_NEW)

    providers = out['integrity']['providers']
    require([p['name'] for p in providers] == PROVIDER_NAMES and len(providers) == PROVIDER_COUNT,
            'exact M9 provider list')
    native = _one(providers, 'name', 'claude-native', 'native provider')
    require(native['sha256'] == NATIVE_CLI and native['version'] == NATIVE_VERSION, 'unchanged native provider')
    candidate = _one(providers, 'path', CANDIDATE_WRAPPER, 'candidate provider')
    require(candidate['sha256'] == CANDIDATE_WRAPPER_SHA, 'unchanged candidate provider')
    repos = out['integrity']['repositories']
    require(repos[-1] == dict(name=AUTHORITY_NAME, path=AUTHORITY, commit=TEMPLATE_COMMIT), 'unchanged last authority')

    for path, (before, after) in EXACT_TREES.items():
        pin = _one(md['trees'], 'path', path, 'exact tree cardinality: ' + path)
        require(pin['sha256'] == before and trees[path]['sha256'] == after, 'sequence 16 accepted tree: ' + path)
        pin['sha256'] = after
    require(md['cache_sha256'] == CACHE_SHA and trees[CACHE]['sha256'] == CACHE_SHA, 'unchanged cache digest')

    for kind, digest in (('manifest', OLD_MANIFEST_SHA), ('receipt', OLD_RECEIPT_SHA)):
        name = 'install-' + kind + '.before.json'
        previous = out['previous_metadata'][kind+'_backup_path']
        require(previous == OLD_ROOT+'/b/'+name, 'previous backup binding')
        out['previous_metadata'][kind+'_sha256'] = digest
        out['previous_metadata'][kind+'_backup_path'] = ROOT+'/b/'+name
        live = [p for p in md['preimages'] if p['path'] == CITY + '/.gc/platform/install-'+kind+'.json']
        prior_backup = [p for p in md['preimages'] if p['path'] == previous]
        require(len(live) == len(prior_backup) == 1 and set(prior_backup[0]) == {'path'}, 'preimage cardinality')
        live[0]['sha256'] = digest; prior_backup[0]['path'] = ROOT+'/b/'+name
    require(len(md['inputs']) == INPUT_COUNT and len(md['trees']) == TREE_COUNT
            and len(md['links']) == LINK_COUNT, 'coverage cardinality drift')
    require(len({p['path'] for p in md['inputs']}) == INPUT_COUNT
            and len({p['path'] for p in md['trees']}) == TREE_COUNT
            and len({p['path'] for p in md['links']}) == LINK_COUNT, 'duplicate pin path')
    # Every pin the successor names, carried or changed, must equal the frozen baseline, so a stale carried
    # digest refuses here rather than inside a consumed native window.
    for p in md['inputs']:
        require(pins[p['path']]['sha256'] == p['sha256'] and pins[p['path']]['mode'] == p['mode'],
                'input differs from the baseline: ' + p['path'])
    for p in md['trees']:
        require(trees[p['path']]['sha256'] == p['sha256'], 'tree differs from the baseline: ' + p['path'])
    for p in md['links']:
        require(links.get(p['path']) == p['target'], 'link differs from the baseline: ' + p['path'])
    for f in out['integrity']['files']:
        require(pins[f['path']]['sha256'] == f['sha256'] and pins[f['path']]['mode'] == f['mode'],
                'integrity file differs from the baseline: ' + f['path'])
    out = b.finalized(out); frame = b.frame_bound(out)
    require(frame['remaining_bytes'] > FRAME_FLOOR, 'frame margin below the M10 floor')
    return out, dict(preparation_only=True, live_acceptance=False, frame=frame, input_count=INPUT_COUNT,
                     tree_count=TREE_COUNT, link_count=LINK_COUNT, runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed M9 manifest drift')
    require(BASELINE_SHA is not None, 'baseline not yet frozen and reviewed')
    require(hashlib.sha256(baseline_bytes).hexdigest() == BASELINE_SHA, 'current baseline drift')
    old = json.loads(old_bytes); closure = json.loads(baseline_bytes)['closure']
    return assemble(old, closure, host, parents, transaction, attempt)


def receipt():
    """Read only the exact root-custodied sequence 16 receipt, never submit a request."""
    path = Path('/var/lib/gas-city-provisioning/receipts') / (REQUEST + '.json')
    pin = r7.c.s.pin(path, {})
    require(pin == dict(uid=0, gid=986, mode=0o640, size=RECEIPT_SIZE, sha256=RECEIPT_SHA),
            'seq16 receipt custody/digest')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        data = os.read(fd, 65537)
        require(before == os.fstat(fd) and len(data) == before.st_size == RECEIPT_SIZE, 'receipt read race')
    finally:
        os.close(fd)
    require(hashlib.sha256(data).hexdigest() == RECEIPT_SHA, 'receipt byte drift')
    value = json.loads(data)
    require(value['request_id'] == REQUEST and value['sequence'] == 16
            and value['result'] == 'pass' and value['rollback'] == 'not-needed'
            and value['operation'] == 'replace-gas-city-control-plane.v1'
            and value['before']['sha256'] == OLD and value['after']['sha256'] == NEW
            and value['source']['commit'] == COMMIT, 'seq16 receipt binding')
    return value
