"""Pure M9 metadata successor: pin the Operations candidate provider wrapper over M8.

The predecessor is the installed M8 manifest (file 63820eac, reports/m8/q/manifest.json). Core's managed
dispatch gate and its live-environment observer key every provisioning-receipt profile's provider by
(name, path) against integrity.providers, so the typed candidate receipt profile (P10, gct-lagl HANDOFF 2.8)
needs its wrapper pinned first (M8 review A should_fix 1). M9 changes exactly that:
- integrity.providers gains one pin, name "claude" at bin/gct-claude-candidate-worker (e4442971), beside the
  signing wrapper's "claude" pin. Core deefb98b keys provider pins by (name, path), so both coexist. Its
  version string is dependencies_sha256 over the claude CLI, the candidate control policy, the candidate
  bin and lib, the signing boundary lib, the subscription lib and candidate-provider.toml;
- metadata.inputs gains the four candidate files among those, exactly as the signing wrapper's bin, lib,
  control policy and provider.toml are pinned (bin 0755, the rest 0644). Core runs every provider's
  --version inside the confined metadata writer, which mounts only exact inputs and trees, so each version
  dependency must be an input or the writer refuses with provider version drift (M9 r1 review B must_fix 1).
  test_m9 checks the whole dependency set against the built inputs.

Nothing else changes. The Core image is unchanged (fce2e9a0); previous_sha256, backup_path and
activation.previous_commit already carry the M8 values that Core's validateSuccessor requires, and stay.
The P9 worker receipt refresh (23eeb222 -> 6bf20a71) rewrote no file M8 pins as an input; the capture admits
it as its only baseline pin change.

WATCHDOG_IMAGE stays 69d00186: the dolt watchdog that survived sequences 14 and 15 still maps that image.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/m8'
ROOT = O + '/reports/m9'
OLD_MANIFEST_SHA = '63820eacf37a46ec6d6d97cfe0434189a2a41a27c6650462b992d1034da183b8'
OLD_RECEIPT_SHA = '1fdb838586d93061743e926cab324bee657d0b93cd11520c43f48419656815d0'
OLD_RELEASE_ID = 'ops-candidate-lane-metadata-m8-20260926'
BASELINE_PATH = O + '/reports/m9-capture/baseline.json'
# Frozen by the 2026-09-26 capture (candidate 0510e94d at 9e5eb6aa, zero drifts, exactly the P9 receipt pin
# change, the four wrapper pins uid/gid 1000). Nobody runs gc, workflow.py or a Bead write until restore-accepted.
BASELINE_SHA = '15d39514ae65216eb7a18f661c08feadc780f2be61df31b5bd5cbbb06965c8c7'
SUSPENSION_SHA = '5c98be4aee73acff8ee390afbe368ba6c58addb7d7ebf136b172dde239df0326'
TEMPLATE = '/home/loucmane/gas-city-template'
TEMPLATE_COMMIT = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
AUTHORITY_NAME = 'template-pr71-authority'
RELEASE_ID = 'ops-candidate-provider-metadata-m9-20260926'

GC = '/home/loucmane/gascity/bin/gc'
ARTIFACT = '/var/tmp/ga-e0t1.18-build-20260926/gc-a'
BACKUP = '/var/tmp/ga-e0t1.18-build-20260926/gc-b'
OLD = NEW = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
NEW_SIZE = 134062284
COMMIT = 'deefb98b2aed07875df31351d081fbac195cb1cd'
VERSION = 'dev'
WATCHDOG_IMAGE = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'

CITY = '/home/loucmane/gascity/city'
# M8's adopted activation files, unchanged since.
REGISTRY = CITY + '/managed/rig-permissions.json'
FRAGMENT = CITY + '/managed/rig-permissions.toml'
REGISTRY_SHA = '1225b7c57ae69fd068ea35117431ae05e09ee493c01bc11a46ac45b77b950c8e'
FRAGMENT_SHA = 'df688a29446cb381b734847ec9a255e470c710498cbfe2b713a9e85b052575a5'
AGENT_DIR = CITY + '/agents/operations-candidate-worker'
AGENT_FILES = ((AGENT_DIR + '/agent.toml', 'ba01f223e724e904ae276fe6237c051e34c13de4f5a4d5d631cf5cb8979edcc4'),
               (AGENT_DIR + '/prompt.template.md', '9c27418c6354cb4e983ceaba6811a52bd03b8cc1b144da5fc157939616ffbcbf'))

# The candidate wrapper at the canonical Template checkout (cfd353f3), as rendered into the claude-candidate
# provider. (path, sha256, mode)
WRAPPER = TEMPLATE + '/bin/gct-claude-candidate-worker'
WRAPPER_SHA = 'e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3'
WRAPPER_LIB = TEMPLATE + '/lib/gct_claude_candidate_worker.py'
WRAPPER_LIB_SHA = '975545865be0314d284ebe28883067157aa4416f45f5b1231fbb9ac4882fa2a8'
WRAPPER_POLICY = TEMPLATE + '/templates/claude/candidate-control-policy.json'
WRAPPER_POLICY_SHA = 'a3eda9160871c0f25bbd5f1b6680fbc932692d6cee2c4f7dc702ad355954ae49'
WRAPPER_PROVIDER_TOML = TEMPLATE + '/templates/claude/candidate-provider.toml'
WRAPPER_PROVIDER_TOML_SHA = 'dea301a4cc3058156c8cb2673c53dbfbe4e695a78d8c1aa2dc4b179e2a1fd06a'
NEW_INPUTS = ((WRAPPER, WRAPPER_SHA, 0o755), (WRAPPER_LIB, WRAPPER_LIB_SHA, 0o644),
              (WRAPPER_POLICY, WRAPPER_POLICY_SHA, 0o644), (WRAPPER_PROVIDER_TOML, WRAPPER_PROVIDER_TOML_SHA, 0o644))
# The exact version the wrapper reports under --version at this Template commit (observed 2026-09-26).
WRAPPER_VERSION = ('gct-claude-candidate-worker 1 '
                   'dependencies_sha256=a35dd4131ed3baa3875b9866aa86e39192d1f96f3f4dd55d8a10d12921eea446')
PROVIDER = dict(name='claude', path=WRAPPER, resolved_path=WRAPPER, sha256=WRAPPER_SHA,
                version_args=['--version'], version=WRAPPER_VERSION)
SIGNING_WRAPPER = TEMPLATE + '/bin/gct-claude-signing-worker'
SIGNING_WRAPPER_SHA = '9df9ea34e83ad7ce39328ffedc7c9b3a2aceef9abb537e7e27c4e85e884378e0'

CACHE = '/home/loucmane/gascity/home/cache/repos'
CACHE_SHA = '4b284f6741eb8a4e2273fe94bd7e5d24b8ae318ca862170b80c6fd75f37f72be'
CITY_CONFIG_SHA = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
CITY_CONFIG_BACKUP = O + '/reports/m6-inputs/city.toml.before'
# M8 counts 692 inputs, 49 trees, 23 links. M9 adds the four candidate wrapper files.
INPUT_COUNT = 692 + 4
TREE_COUNT = 49
LINK_COUNT = 23
PROVIDER_COUNT = 4
# The M9 frame margin floor. M8 left 1,763 spare bytes; the four inputs and the provider pin cost 1,130, so the
# computed M9 bound (130,439 of 131,072) leaves 633. Only the fresh parents' device and inode vary at prepare,
# at most 72 bytes wider than the test's synthetic values.
FRAME_FLOOR = 512

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
    """Pure construction from the installed M8 predecessor and a frozen closure."""
    require(b.finalized(old) == old and host == closure['host'], 'manifest/host binding')
    require(old['release_id'] == OLD_RELEASE_ID, 'installed release is not M8')
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

    # Core: unchanged image, previous image and commit already at the M8 values (validateSuccessor).
    require(out['core'] == dict(name='gc', source=ARTIFACT, destination=GC, sha256=NEW, mode=0o755)
            and md['writer'] == dict(name='', path=GC, sha256=NEW, mode=0o755), 'exact installed Core predecessor')
    require(out['previous_sha256'] == NEW and out['backup_path'] == BACKUP, 'exact M8 previous image and backup')
    require(out['activation'] == dict(expected_commit=COMMIT, expected_version=VERSION,
                                      previous_commit=COMMIT, previous_version=VERSION),
            'exact predecessor activation')
    require(pins[GC]['sha256'] == NEW and pins[GC]['size'] == NEW_SIZE and pins[GC]['mode'] == 0o755,
            'installed image')
    require(pins[BACKUP]['sha256'] == NEW and pins[BACKUP]['size'] == NEW_SIZE and pins[BACKUP]['mode'] == 0o755,
            'previous image backup')
    require(_one(md['inputs'], 'path', BACKUP, 'backup input cardinality') == dict(
        name='', path=BACKUP, sha256=NEW, mode=0o755), 'backup input')

    out['release_id'] = RELEASE_ID
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt, parents=copy.deepcopy(parents), evidence=ROOT+'/t')

    # M8's adopted activation files stay exactly as M8 pinned them.
    for path, digest in ((REGISTRY, REGISTRY_SHA), (FRAGMENT, FRAGMENT_SHA)) + AGENT_FILES:
        require(_one(md['inputs'], 'path', path, 'M8 input cardinality: ' + path)['sha256'] == digest,
                'exact M8 input: ' + path)
    for path, digest in ((REGISTRY, REGISTRY_SHA), (FRAGMENT, FRAGMENT_SHA)):
        require(_one(out['integrity']['files'], 'path', path, 'M8 integrity file: ' + path)['sha256'] == digest,
                'exact M8 integrity file: ' + path)

    # The candidate wrapper: four inputs and one provider pin.
    for path, digest, mode in NEW_INPUTS:
        require(not any(p['path'] == path for p in md['inputs']), 'wrapper input already pinned: ' + path)
        require(pins[path]['sha256'] == digest and pins[path]['mode'] == mode, 'wrapper bytes: ' + path)
        md['inputs'].append(dict(name='', path=path, sha256=digest, mode=mode))
    providers = out['integrity']['providers']
    require([p['name'] for p in providers] == ['claude-native', 'codex', 'claude'], 'exact M8 provider list')
    signing = _one(providers, 'path', SIGNING_WRAPPER, 'signing provider')
    require(signing['name'] == 'claude' and signing['resolved_path'] == SIGNING_WRAPPER
            and signing['sha256'] == SIGNING_WRAPPER_SHA, 'exact M8 signing provider')
    # With the exact name list above, this fires only if claude-native or codex points at the wrapper.
    require(not any(p['path'] == WRAPPER or p['resolved_path'] == WRAPPER for p in providers),
            'candidate provider already pinned')
    providers.append(copy.deepcopy(PROVIDER))
    require(len(providers) == PROVIDER_COUNT, 'provider count')

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
    require(frame['remaining_bytes'] > FRAME_FLOOR, 'frame margin below the M9 floor')
    return out, dict(preparation_only=True, live_acceptance=False, frame=frame, input_count=INPUT_COUNT,
                     tree_count=TREE_COUNT, link_count=LINK_COUNT, runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed M8 manifest drift')
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
