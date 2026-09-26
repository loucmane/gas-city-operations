"""Pure M8 metadata successor: adopt the Operations candidate lane activation (ga-6utp r12) over M7.

The predecessor is the installed M7 manifest (file 4bec5ef1, reports/m7/q/manifest.json). The ga-6utp r12
activation (operator decision 2026-09-26, "Activate, then M8") rewrote two files M7 pins, both as integrity
files and as inputs:
- managed/rig-permissions.json: d22cf4c1 -> 1225b7c5 (the candidate registry record appended);
- managed/rig-permissions.toml: cba75f87 -> df688a29 (the claude-candidate provider and agent patch rendered).
It also added the city-pack agent directory agents/operations-candidate-worker, which M7 does not cover; M8
pins its two files as inputs (agent.toml ba01f223 carries `suspended = true` and no scope, so a later edit is
integrity drift). city.toml is unchanged (4f7e170f), and so is everything else M7 pins.

The Core image is unchanged (fce2e9a0). Core's validateSuccessor still requires previous_sha256 to equal the
predecessor core and activation.previous_commit its expected_commit, so both move to the M7 values:
previous_sha256 fce2e9a0 with the second reproducible build /var/tmp/ga-e0t1.18-build-20260926/gc-b as its
backup (a new input), and previous_commit deefb98b. Metadata-only adoption with an installed image equal to
core.sha256 is the path M6 and M7 took.

WATCHDOG_IMAGE stays 69d00186: the dolt watchdog that survived sequences 14 and 15 still maps that image.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/m7'
ROOT = O + '/reports/m8'
OLD_MANIFEST_SHA = '4bec5ef14bd81f6dc1830ada48fc502937ff91a531981dfff3fde5aaa92a9759'
OLD_RECEIPT_SHA = '3be61bf580649ebcb7b5ac7a33a8b3c12413c633035f61ee7c2b205e16441fef'
OLD_RELEASE_ID = 'template-pr71-core-seq15-metadata-m7-20260926'
BASELINE_PATH = O + '/reports/m8-capture/baseline.json'
BASELINE_SHA = None
SUSPENSION_SHA = '5c98be4aee73acff8ee390afbe368ba6c58addb7d7ebf136b172dde239df0326'
TEMPLATE_COMMIT = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
AUTHORITY_NAME = 'template-pr71-authority'
RELEASE_ID = 'ops-candidate-lane-metadata-m8-20260926'

GC = '/home/loucmane/gascity/bin/gc'
ARTIFACT = '/var/tmp/ga-e0t1.18-build-20260926/gc-a'
OLD_BACKUP = '/var/tmp/ga-e0t1.15-build-20260925/gc-b'
BACKUP = '/var/tmp/ga-e0t1.18-build-20260926/gc-b'
OLDER = 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'
OLD = NEW = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
NEW_SIZE = 134062284
OLDER_COMMIT = '9faeabc2892d8c7133111e13ad55af66790a2ac6'
COMMIT = 'deefb98b2aed07875df31351d081fbac195cb1cd'
VERSION = 'dev'
WATCHDOG_IMAGE = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'

CITY = '/home/loucmane/gascity/city'
REGISTRY = CITY + '/managed/rig-permissions.json'
FRAGMENT = CITY + '/managed/rig-permissions.toml'
# (path, M7 sha256, activation postimage sha256); modes are unchanged (0644).
CHANGED_INPUTS = (
    (REGISTRY, 'd22cf4c14650e465b6b530e17d16b601079aa1e7dd52b1b76403cc58299c8adf',
     '1225b7c57ae69fd068ea35117431ae05e09ee493c01bc11a46ac45b77b950c8e'),
    (FRAGMENT, 'cba75f87a373a078c11832609c274bd7eaa592b435545ef203ba6211f4f86725',
     'df688a29446cb381b734847ec9a255e470c710498cbfe2b713a9e85b052575a5'),
)
SUCCESSOR_SIZES = {}
AGENT_DIR = CITY + '/agents/operations-candidate-worker'
AGENT_FILES = ((AGENT_DIR + '/agent.toml', 'ba01f223e724e904ae276fe6237c051e34c13de4f5a4d5d631cf5cb8979edcc4'),
               (AGENT_DIR + '/prompt.template.md', '9c27418c6354cb4e983ceaba6811a52bd03b8cc1b144da5fc157939616ffbcbf'))
CACHE = '/home/loucmane/gascity/home/cache/repos'
CACHE_SHA = '4b284f6741eb8a4e2273fe94bd7e5d24b8ae318ca862170b80c6fd75f37f72be'
CITY_CONFIG_SHA = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
CITY_CONFIG_BACKUP = O + '/reports/m6-inputs/city.toml.before'
# M7 counts 689 inputs, 49 trees, 23 links. M8 adds the new backup and the two agent files.
INPUT_COUNT = 689 + 3
TREE_COUNT = 49
LINK_COUNT = 23
# The M8 frame margin floor. M7 left 2263 spare bytes; three new inputs cost about 520.
FRAME_FLOOR = 1024

# There is no new broker receipt: the Core image did not change. The sequence 15 receipt still binds it.
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
    """Pure construction from the installed M7 predecessor and a frozen closure."""
    require(b.finalized(old) == old and host == closure['host'], 'manifest/host binding')
    require(old['release_id'] == OLD_RELEASE_ID, 'installed release is not M7')
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

    # Core: unchanged image; the previous image and commit move to the M7 values (validateSuccessor).
    require(out['core'] == dict(name='gc', source=ARTIFACT, destination=GC, sha256=NEW, mode=0o755)
            and md['writer'] == dict(name='', path=GC, sha256=NEW, mode=0o755), 'exact installed Core predecessor')
    require(out['previous_sha256'] == OLDER and out['backup_path'] == OLD_BACKUP, 'exact M7 previous image and backup')
    require(out['activation'] == dict(expected_commit=COMMIT, expected_version=VERSION,
                                      previous_commit=OLDER_COMMIT, previous_version=VERSION),
            'exact predecessor activation')
    require(pins[GC]['sha256'] == NEW and pins[GC]['size'] == NEW_SIZE and pins[GC]['mode'] == 0o755,
            'installed image')
    require(pins[BACKUP]['sha256'] == NEW and pins[BACKUP]['size'] == NEW_SIZE and pins[BACKUP]['mode'] == 0o755,
            'previous image backup')
    require(not any(p['path'] == BACKUP for p in md['inputs']), 'backup already present')
    out['previous_sha256'] = NEW
    out['backup_path'] = BACKUP
    out['activation']['previous_commit'] = COMMIT
    md['inputs'].append(dict(name='', path=BACKUP, sha256=NEW, mode=0o755))

    out['release_id'] = RELEASE_ID
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt, parents=copy.deepcopy(parents), evidence=ROOT+'/t')

    # The activation's two rewritten files, in both places M7 pins them.
    for path, before, after in CHANGED_INPUTS:
        pin = _one(md['inputs'], 'path', path, 'changed input cardinality: ' + path)
        integrity = _one(out['integrity']['files'], 'path', path, 'changed integrity file cardinality: ' + path)
        require(pin['sha256'] == before and integrity['sha256'] == before, 'exact M7 predecessor: ' + path)
        require(pins[path]['sha256'] == after and pins[path]['mode'] == pin['mode'] == integrity['mode'],
                'activation postimage: ' + path)
        pin['sha256'] = after
        integrity['sha256'] = after
    for path, digest in AGENT_FILES:
        require(not any(p['path'] == path for p in md['inputs']), 'agent file already pinned: ' + path)
        require(pins[path]['sha256'] == digest and pins[path]['mode'] == 0o644, 'agent file bytes: ' + path)
        md['inputs'].append(dict(name='', path=path, sha256=digest, mode=0o644))

    config = _one(out['managed_files'], 'name', 'city-config', 'city config managed file')
    require(config['sha256'] == config['previous_sha256'] == CITY_CONFIG_SHA and config['backup_path'] == CITY_CONFIG_BACKUP
            and pins[CITY_CONFIG_BACKUP]['sha256'] == CITY_CONFIG_SHA
            and pins[CITY + '/city.toml']['sha256'] == CITY_CONFIG_SHA, 'unchanged city config and its backup')
    require(all(f['previous_sha256'] == f['sha256'] for f in out['managed_files']),
            'every managed file already carries its own baseline')
    repos = out['integrity']['repositories']
    require(repos[-1] == dict(name=AUTHORITY_NAME, path=AUTHORITY, commit=TEMPLATE_COMMIT), 'unchanged last authority')
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
    require(frame['remaining_bytes'] > FRAME_FLOOR, 'frame margin below the M8 floor')
    return out, dict(preparation_only=True, live_acceptance=False, frame=frame, input_count=INPUT_COUNT,
                     tree_count=TREE_COUNT, link_count=LINK_COUNT, runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed M7 manifest drift')
    require(BASELINE_SHA is not None, 'baseline not yet frozen and reviewed')
    require(hashlib.sha256(baseline_bytes).hexdigest() == BASELINE_SHA, 'current baseline drift')
    old = json.loads(old_bytes); closure = json.loads(baseline_bytes)['closure']
    return assemble(old, closure, host, parents, transaction, attempt)


def receipt():
    """Read only the exact root-custodied sequence 15 receipt; the Core image is unchanged since."""
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
            and value['after']['sha256'] == NEW and value['source']['commit'] == COMMIT, 'seq15 receipt binding')
    return value
