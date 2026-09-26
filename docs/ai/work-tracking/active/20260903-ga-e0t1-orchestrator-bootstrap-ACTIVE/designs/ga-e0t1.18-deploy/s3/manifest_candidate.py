"""Pure M7 metadata successor: the sequence 15 Core only (ga-e0t1.18 S3).

The predecessor is the installed M6 manifest 7f335ad8 (reports/m6/q/manifest.json holds the same bytes). M7
is the R9 Core pattern and nothing else. Sequence 15 (S2, accepted 2026-09-26) replaced gc b2760ea4 with
fce2e9a0, built from deefb98b (Core PR 48, the ga-qcwl provider-pin fix). The Template, the providers, the
cache, the libraries and every other pin are unchanged since M6; the read-only probe of 2026-09-26 found only
gc and the Core rig object tree changed.

Unlike M6, the previous image moves. M6 could keep previous_sha256 69d00186 because that was M5's core. Core's
validateSuccessor (installer.go at deefb98b, lines 381-416) requires previous_sha256 to equal the predecessor's
core.sha256 and activation.previous_commit to equal its expected_commit. So M7 names b2760ea4 and its custody
backup /var/tmp/ga-e0t1.15-build-20260925/gc-b (the second reproducible build of 9faeabc2, pinned as a new
input like R9's gc-b), and previous_commit 9faeabc2.

Changed fields:
- core.source and core.sha256: the sequence 15 build source gc-a and fce2e9a0 (receipt 1cca491d);
- previous_sha256 and backup_path: b2760ea4 and the ga-e0t1.15 gc-b;
- activation: expected_commit deefb98b (the build's `gc version` commit), previous_commit 9faeabc2;
- the writer and the installed gc input: fce2e9a0;
- inputs appended: the build source gc-a (fce2e9a0) and the backup gc-b (b2760ea4), both 0755;
- tree rigs/gascity/.git/objects: ae95c30c to 98e871c4, the digest the sequence 15 closure accepted;
- release, transaction, attempt, parents, evidence, host, namespaces and previous metadata: fresh, reports/m7.

The dolt watchdog that survived sequences 14 and 15 still maps 69d00186, so the scope policy admits that image
through WATCHDOG_IMAGE, not through OLD (metadata_closure.configure).

Every new digest is a build, receipt or closure value. Nothing here reads the host except the pinned baseline
and the root-custodied broker receipt.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/m6'
ROOT = O + '/reports/m7'
OLD_MANIFEST_SHA = '7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb'
OLD_RECEIPT_SHA = '123a01818b86f977ceabab1207c57795a3780261e39599019aa37f7609febaac'
OLD_RELEASE_ID = 'template-pr71-core-seq14-metadata-m6-20260925'
BASELINE_PATH = O + '/reports/m7-capture/baseline.json'
BASELINE_SHA = None
SUSPENSION_SHA = '5c98be4aee73acff8ee390afbe368ba6c58addb7d7ebf136b172dde239df0326'
TEMPLATE = '/home/loucmane/gas-city-template'
TEMPLATE_COMMIT = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
AUTHORITY_NAME = 'template-pr71-authority'
RELEASE_ID = 'template-pr71-core-seq15-metadata-m7-20260926'

# Core (the R9 pattern).
GC = '/home/loucmane/gascity/bin/gc'
OLD_SOURCE = '/var/tmp/ga-e0t1.15-build-20260925/gc-a'
OLD_BACKUP = '/var/tmp/ga-mutg-custody-build-20260920/gc-b'
BACKUP = '/var/tmp/ga-e0t1.15-build-20260925/gc-b'
ARTIFACT = '/var/tmp/ga-e0t1.18-build-20260926/gc-a'
OLDER = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'
OLD = 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'
OLD_SIZE = 134052980
NEW = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
NEW_SIZE = 134062284
OLDER_COMMIT = '796d9a7a67c42294fdc467c107bb59b76e482301'
OLD_COMMIT = '9faeabc2892d8c7133111e13ad55af66790a2ac6'
COMMIT = 'deefb98b2aed07875df31351d081fbac195cb1cd'
VERSION = 'dev'
# The surviving dolt watchdog's image (started before sequence 14); see metadata_closure.configure.
WATCHDOG_IMAGE = OLDER

# No input bytes change besides gc: the executor's gate extract reads these two names.
CHANGED_INPUTS = ()
SUCCESSOR_SIZES = {}

NATIVE_CLI = '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
NATIVE_VERSION = '2.1.280 (Claude Code)'
WORKER_VERSION = ('gct-claude-signing-worker 1 dependencies_sha256='
                  'd4e57767d03accd708ce8876580096bb17bce023d6dc6e664fffee4367ea3c57')

# Trees. The Core rig object tree takes the sequence 15 accepted digest (the S1 build-source branch fetched
# PR 48's objects into the rig); the cache is unchanged (sequence 15 admitted no cache key).
ODB = '/home/loucmane/gascity/city/rigs/gascity/.git/objects'
CACHE = '/home/loucmane/gascity/home/cache/repos'
EXACT_TREES = {
    ODB: ('ae95c30c08375b9c2e5351e164c1c6a8895444f5a23b2de3c2d95366fd644520',
          '98e871c4255084b7e8c7cd41021935193431a17a63933ba2826d2e0f1adcc07f'),
}
CACHE_SHA = '4b284f6741eb8a4e2273fe94bd7e5d24b8ae318ca862170b80c6fd75f37f72be'

# Managed file city-config: M6 already carries its own sha256 as previous_sha256, with the pinned backup
# reports/m6-inputs/city.toml.before, so M7 keeps it (and Core's successor rule holds unchanged).
CITY_CONFIG_SHA = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
CITY_CONFIG_BACKUP = O + '/reports/m6-inputs/city.toml.before'
# M6 counts 687 inputs, 49 trees, 23 links. M7 adds the build source and the new backup.
INPUT_COUNT = 687 + 2
TREE_COUNT = 49
LINK_COUNT = 23

REQUEST = '3183ed20113fb64e149061360f29c189d3ee094031e3d5e7d0462697af01f2e2'
RECEIPT_SHA = '1cca491d96990d6a525f4052bd12705e5169f71d4dc7d65441f10923baba0350'
RECEIPT_SIZE = 1234

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
    """Pure construction from the installed M6 predecessor and a frozen closure."""
    require(b.finalized(old) == old and host == closure['host'], 'manifest/host binding')
    require(old['release_id'] == OLD_RELEASE_ID, 'installed release is not M6')
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

    # Core: the R9 pattern, with the previous image moving to the image sequence 15 replaced.
    require(out['core'] == dict(name='gc', source=OLD_SOURCE, destination=GC, sha256=OLD, mode=0o755)
            and md['writer'] == dict(name='', path=GC, sha256=OLD, mode=0o755), 'exact installed Core predecessor')
    require(out['previous_sha256'] == OLDER and out['backup_path'] == OLD_BACKUP, 'exact M6 previous image and backup')
    require(out['activation'] == dict(expected_commit=OLD_COMMIT, expected_version=VERSION,
                                      previous_commit=OLDER_COMMIT, previous_version=VERSION),
            'exact predecessor activation')
    require(pins[GC]['sha256'] == NEW and pins[GC]['size'] == NEW_SIZE and pins[GC]['mode'] == 0o755,
            'installed sequence 15 image')
    require(pins[ARTIFACT]['sha256'] == NEW and pins[ARTIFACT]['size'] == NEW_SIZE and pins[ARTIFACT]['mode'] == 0o755,
            'sequence 15 build source')
    require(pins[BACKUP]['sha256'] == OLD and pins[BACKUP]['size'] == OLD_SIZE and pins[BACKUP]['mode'] == 0o755,
            'previous image backup')
    require(not any(p['path'] in (ARTIFACT, BACKUP) for p in md['inputs']), 'build source or backup already present')
    out['core'].update(source=ARTIFACT, sha256=NEW)
    out['previous_sha256'] = OLD
    out['backup_path'] = BACKUP
    # Core's successor rule: previous_commit is the predecessor's expected_commit.
    out['activation'].update(expected_commit=COMMIT, previous_commit=OLD_COMMIT)
    md['writer']['sha256'] = NEW
    _one(md['inputs'], 'path', GC, 'installed Core input cardinality')['sha256'] = NEW
    md['inputs'].append(dict(name='', path=ARTIFACT, sha256=NEW, mode=0o755))
    md['inputs'].append(dict(name='', path=BACKUP, sha256=OLD, mode=0o755))

    out['release_id'] = RELEASE_ID
    # The native wire uses predecessor struct order, not caller dictionary order.
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt, parents=copy.deepcopy(parents), evidence=ROOT+'/t')

    config = _one(out['managed_files'], 'name', 'city-config', 'city config managed file')
    require(config['sha256'] == config['previous_sha256'] == CITY_CONFIG_SHA and config['backup_path'] == CITY_CONFIG_BACKUP
            and pins[CITY_CONFIG_BACKUP]['sha256'] == CITY_CONFIG_SHA, 'unchanged city config and its backup')
    require(all(f['previous_sha256'] == f['sha256'] for f in out['managed_files']),
            'every managed file already carries its own baseline')
    native = _one(out['integrity']['providers'], 'name', 'claude-native', 'native provider')
    require(native['sha256'] == NATIVE_CLI and native['version'] == NATIVE_VERSION, 'unchanged native provider')
    worker = _one(out['integrity']['providers'], 'name', 'claude', 'signing provider')
    require(worker['version'] == WORKER_VERSION, 'unchanged signing provider')
    repos = out['integrity']['repositories']
    require(repos[-1] == dict(name=AUTHORITY_NAME, path=AUTHORITY, commit=TEMPLATE_COMMIT), 'unchanged last authority')

    for path, (before, after) in EXACT_TREES.items():
        pin = _one(md['trees'], 'path', path, 'exact tree cardinality: ' + path)
        require(pin['sha256'] == before and trees[path]['sha256'] == after, 'sequence 15 accepted tree: ' + path)
        pin['sha256'] = after
    require(md['cache_sha256'] == CACHE_SHA and trees[CACHE]['sha256'] == CACHE_SHA, 'unchanged cache digest')

    for kind, digest in (('manifest', OLD_MANIFEST_SHA), ('receipt', OLD_RECEIPT_SHA)):
        name = 'install-' + kind + '.before.json'
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
    # Every pin the successor names, carried or changed, must equal the frozen baseline, so a stale carried
    # digest refuses here rather than inside a consumed native window.
    for p in md['inputs']:
        require(pins[p['path']]['sha256'] == p['sha256'] and pins[p['path']]['mode'] == p['mode'],
                'input differs from the baseline: ' + p['path'])
    for p in md['trees']:
        require(trees[p['path']]['sha256'] == p['sha256'], 'tree differs from the baseline: ' + p['path'])
    for p in md['links']:
        require(links.get(p['path']) == p['target'], 'link differs from the baseline: ' + p['path'])
    out = b.finalized(out); frame = b.frame_bound(out)
    return out, dict(preparation_only=True, live_acceptance=False, frame=frame, input_count=INPUT_COUNT,
                     tree_count=TREE_COUNT, link_count=LINK_COUNT, runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed M6 manifest drift')
    require(BASELINE_SHA is not None, 'baseline not yet frozen and reviewed')
    require(hashlib.sha256(baseline_bytes).hexdigest() == BASELINE_SHA, 'current baseline drift')
    old = json.loads(old_bytes); closure = json.loads(baseline_bytes)['closure']
    return assemble(old, closure, host, parents, transaction, attempt)


def receipt():
    """Read only the exact root-custodied sequence 15 receipt, never submit a request."""
    path = Path('/var/lib/gas-city-provisioning/receipts') / (REQUEST + '.json')
    pin = r7.c.s.pin(path, {})
    require(pin == dict(uid=0, gid=986, mode=0o640, size=RECEIPT_SIZE, sha256=RECEIPT_SHA),
            'seq15 receipt custody/digest')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        data = os.read(fd, 65537)
        require(before == os.fstat(fd) and len(data) == before.st_size == RECEIPT_SIZE, 'receipt read race')
    finally:
        os.close(fd)
    require(hashlib.sha256(data).hexdigest() == RECEIPT_SHA, 'receipt byte drift')
    value = json.loads(data)
    require(value['request_id'] == REQUEST and value['sequence'] == 15
            and value['result'] == 'pass' and value['rollback'] == 'not-needed'
            and value['operation'] == 'replace-gas-city-control-plane.v1'
            and value['before']['sha256'] == OLD and value['after']['sha256'] == NEW
            and value['source']['commit'] == COMMIT, 'seq15 receipt binding')
    return value
