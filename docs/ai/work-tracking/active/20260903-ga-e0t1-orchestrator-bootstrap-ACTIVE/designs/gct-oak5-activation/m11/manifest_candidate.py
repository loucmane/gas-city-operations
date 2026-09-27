"""Pure M11 metadata successor: adopt the Template Claude candidate lane activation (gct-oak5) over M10.

The predecessor is the installed M10 manifest (file 2b902a83, reports/m10/q/manifest.json). The gct-oak5
activation (operator decision 2026-09-27, "Prepare and apply"; package 9936810e, two reviews) changed what M10
pins:
- city.toml e5b68c40 -> b0eeb168 (the Template implementation-worker override removed, its work_dir_roots moved
  to the candidate root, cap 1): the city-config managed file and the installed input, the M10 pattern;
- managed/rig-permissions.json 1225b7c5 -> 0b0e6a87 and managed/rig-permissions.toml df688a29 -> df9c82d0 (the
  Template registry record and the claude-template-candidate provider and patch): integrity files and inputs,
  the M8 pattern;
- the canonical Template checkout cfd353f3 -> 3474abfa (Template PR 72): the pinned tree
  /home/loucmane/gas-city-template/.git moves to the captured digest.
The M10 inspector reports exactly the first three as drift.

The Template wrapper becomes a third "claude" platform provider (the M9 pattern), so the P12 typed candidate
receipt profile can match it by (name, path). The confined metadata writer mounts only pinned inputs and trees
(Core internal/platforminstall/metadata_sandbox_linux.go ro-binds Inputs then Trees), and the wrapper's --version
hashes seven dependencies, so every one must be mounted:
- the Claude CLI, the signing boundary and the subscription library are already M10 inputs;
- the wrapper and its library are new inputs;
- the Template policy and provider template live in templates/claude. One tree pin of that directory (seven
  regular files, nothing generated) replaces its four M10 inputs (the signing and Operations candidate policies
  and provider templates) and also covers the two new files. Pinning the directory is stricter than the four
  files: an added file there is drift.
Frame: M10 left 613 spare bytes; the provider row alone costs about 580. So no input row is appended (r2 appends one
repository row, below): the two new inputs take over, in place, the two M10 rows that pin superseded ga-e0t1.15 Core images (b2760ea4, no longer any
backup or source since M8), the new city source takes over the superseded M6 city backup row, and the new Core
backup takes over the superseded ga-e0t1.18 backup row. The superseded files stay on disk, unchanged.

The Core image is unchanged (207a78e2). Core's validateSuccessor requires previous_sha256 to equal the
predecessor core and activation.previous_commit its expected_commit: previous_sha256 207a78e2 with the second
reproducible sequence 16 build /var/tmp/ga-bebv-build-20260927/gc-b as its backup, previous_commit f45a6262.
There is no new broker receipt: sequence 16's 1108b724 still binds the image.

The suspension record moves to the captured one (the gct-mbg6 window lifecycle rewrote updated_at; the capture
proves the image equals M10's otherwise). WATCHDOG_IMAGE stays 69d00186.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/m10'
ROOT = O + '/reports/m11'
OLD_MANIFEST_SHA = '2b902a83577acf71f9dd93a97d43d8478f7c4b291b0992e8ba5a5e44fe66f7f2'
OLD_RECEIPT_SHA = 'c0853ca321bd56fdead3443ff8a529a4b3b1a88ed52eca70e5fe5a4327bc0e6a'
OLD_RELEASE_ID = 'ga-bebv-core-seq16-city-metadata-m10-20260927'
BASELINE_PATH = O + '/reports/m11-capture/baseline.json'
# Frozen by the 2026-09-27 capture (candidate 44786b31 at 04ec50be, after prereqs_m11.py; zero drifts, exactly the four
# admitted pin changes, the Template .git pair and the known cache Git bookkeeping). Nobody runs gc, workflow.py, a Bead
# write or git in a pinned repository until restore-accepted.
BASELINE_SHA = '4000f7f3d37a2a572fc210ba201f0b6dedb08661f0c878c896f34a0426548a97'
SUSPENSION_SHA = 'a3306567b3cf77e6371a870e6df239194574fab8f2dc3090ea55a5eeb14b4817'
TEMPLATE = '/home/loucmane/gas-city-template'
TEMPLATE_COMMIT = '3474abfaec255f7ea4266ce8aa35218afcfc89b0'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
AUTHORITY_NAME = 'template-pr71-authority'
AUTHORITY_COMMIT = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
RELEASE_ID = 'gct-oak5-template-candidate-lane-metadata-m11-20260927'
# r2 (review B must_fix 1): P12 moves the receipt's template_commit to 3474abfa, and Core's dispatch gate and
# `gc platform canary` (cmd/gc/managed_product_dispatch_gate.go containsRepositoryCommit) refuse unless some pinned
# repository carries exactly that commit. The canonical checkout is that authority: HEAD is pinned exactly and its
# .git is a pinned tree; allow_dirty only skips the status check, because the checkout carries the two known
# untracked directories (deploy/, gas_city_template.egg-info/). r2 binding (review B should_fix 1): allow_dirty is
# required whatever the host checkout looks like, because inside the confined writer the working tree is not mounted
# (only .git, templates/claude and the pinned bin/lib inputs), so `git status` there would list every other tracked
# file as deleted. It skips the status check entirely, so a modified tracked file elsewhere in the checkout is not
# detected by this pin; the executed lane bytes are covered by the provider pins and the wrapper's dependency
# digest. A clean separate authority worktree would need about twenty more tree rows, which the frame cannot hold.
TEMPLATE_AUTHORITY = dict(name='template-pr72-canonical', path=TEMPLATE, commit=TEMPLATE_COMMIT, allow_dirty=True)

GC = '/home/loucmane/gascity/bin/gc'
ARTIFACT = '/var/tmp/ga-bebv-build-20260927/gc-a'
OLD_BACKUP = '/var/tmp/ga-e0t1.18-build-20260926/gc-b'
BACKUP = '/var/tmp/ga-bebv-build-20260927/gc-b'
OLDER = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
OLD = NEW = '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f'
NEW_SIZE = 134146157
OLDER_COMMIT = 'deefb98b2aed07875df31351d081fbac195cb1cd'
COMMIT = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
VERSION = 'dev'
WATCHDOG_IMAGE = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'

CITY = '/home/loucmane/gascity/city'
CITY_TOML = CITY + '/city.toml'
CITY_OLDER = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
CITY_OLD = 'e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077'
CITY_NEW = 'b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b'
CITY_OLD_SOURCE = O + '/reports/m10-inputs/city.toml'
CITY_SOURCE = O + '/reports/m11-inputs/city.toml'
CITY_OLD_BACKUP = O + '/reports/m6-inputs/city.toml.before'
REGISTRY = CITY + '/managed/rig-permissions.json'
FRAGMENT = CITY + '/managed/rig-permissions.toml'
# (path, M10 sha256, activation postimage sha256); modes are unchanged (0644). Integrity files and inputs.
CHANGED_INPUTS = (
    (REGISTRY, '1225b7c57ae69fd068ea35117431ae05e09ee493c01bc11a46ac45b77b950c8e',
     '0b0e6a87ee19f6e3a2e440d7389cc6abf28e1fabd1b08a892adab0f6c435df00'),
    (FRAGMENT, 'df688a29446cb381b734847ec9a255e470c710498cbfe2b713a9e85b052575a5',
     'df9c82d0c1b22a4b0024a912c0abb980396d6765f45c597ddb9c6b4b649c5530'),
)

# The Template candidate lane (Template 3474abfa).
WRAPPER = TEMPLATE + '/bin/gct-claude-template-candidate-worker'
WRAPPER_SHA = '229d33557326abc8bafceadb06ae12ba2a2d9189e137ff0e1378d35dcf69491c'
WRAPPER_LIB = TEMPLATE + '/lib/gct_claude_template_candidate_worker.py'
WRAPPER_LIB_SHA = '17f54bcac39fb64bf9dfde066470709742ff117a94e37814ea637be961ed23ca'
# The exact version the wrapper reports under --version at 3474abfa (observed 2026-09-27).
WRAPPER_VERSION = ('gct-claude-template-candidate-worker 1 '
                   'dependencies_sha256=3cd85706cd98a25bd50ef12c5dfa59e34054396db81913cd4692728e6ca7ffb3')
PROVIDER = dict(name='claude', path=WRAPPER, resolved_path=WRAPPER, sha256=WRAPPER_SHA,
                version_args=['--version'], version=WRAPPER_VERSION)
SIGNING_WRAPPER = TEMPLATE + '/bin/gct-claude-signing-worker'
SIGNING_WRAPPER_SHA = '9df9ea34e83ad7ce39328ffedc7c9b3a2aceef9abb537e7e27c4e85e884378e0'
CANDIDATE_WRAPPER = TEMPLATE + '/bin/gct-claude-candidate-worker'
CANDIDATE_WRAPPER_SHA = 'e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3'
POLICY_DIR = TEMPLATE + '/templates/claude'
# The four M10 inputs the templates/claude tree replaces.
REMOVED_INPUTS = (POLICY_DIR + '/core-signing-control-policy.json', POLICY_DIR + '/signing-provider.toml',
                  POLICY_DIR + '/candidate-control-policy.json', POLICY_DIR + '/candidate-provider.toml')

# Rows that move in place, as (superseded M10 path, successor path); assemble() sets each successor's digest and mode.
SUPERSEDED_INPUTS = ((OLD_BACKUP, BACKUP), (CITY_OLD_BACKUP, CITY_SOURCE),
                     ('/var/tmp/ga-e0t1.15-build-20260925/gc-a', WRAPPER),
                     ('/var/tmp/ga-e0t1.15-build-20260925/gc-b', WRAPPER_LIB))

ODB_TEMPLATE = TEMPLATE + '/.git'
# (M10 digest, live digest measured read-only on 2026-09-27 with the executor's own tree_snapshot, after the
# activation's fetch and checkout; 6877 entries). The capture must reproduce it.
EXACT_TREES = {ODB_TEMPLATE: ('06ebb42bd7ed7d4ef7b2749f613a7a4e9af1ab003369eb208da920a159c194b8',
                              '9b74eda46ae495bed2e276d281599b523a505ca11d51d76fe11d0002747cf6cb')}
# templates/claude at 3474abfa: 8 entries (the directory and seven regular files), 17943 bytes.
NEW_TREES = ((POLICY_DIR, 'aff9b9b3a2ebd9a185d6faa8b41f00d475fb1db91c02b00fbbf6b937b125e6fe'),)
CACHE = '/home/loucmane/gascity/home/cache/repos'
CACHE_SHA = '4b284f6741eb8a4e2273fe94bd7e5d24b8ae318ca862170b80c6fd75f37f72be'
# The pins M11 moves or adds, as (path, sha256, mode). The executor's gate extract and the capture read this name.
NEW_INPUTS = ((CITY_TOML, CITY_NEW, 0o644), (CITY_SOURCE, CITY_NEW, 0o644), (BACKUP, NEW, 0o755),
              (REGISTRY, CHANGED_INPUTS[0][2], 0o644), (FRAGMENT, CHANGED_INPUTS[1][2], 0o644),
              (WRAPPER, WRAPPER_SHA, 0o755), (WRAPPER_LIB, WRAPPER_LIB_SHA, 0o644))
# M10 counts 696 inputs, 49 trees, 23 links, 4 providers. M11: four inputs removed (the tree covers them), one tree
# added, one provider added, every other row moved in place.
INPUT_COUNT = 696 - 4
TREE_COUNT = 49 + 1
LINK_COUNT = 23
PROVIDER_COUNT = 5
# Only the fresh parents' device and inode vary at prepare, at most 72 bytes wider than the test's values.
FRAME_FLOOR = 256

# There is no new broker receipt: the Core image did not change. The sequence 16 receipt still binds it.
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
    """Pure construction from the installed M10 predecessor and a frozen closure."""
    require(None not in (WRAPPER_SHA, WRAPPER_LIB_SHA, EXACT_TREES[ODB_TEMPLATE][1], NEW_TREES[0][1]),
            'captured digests not yet pinned')
    require(b.finalized(old) == old and host == closure['host'], 'manifest/host binding')
    require(old['release_id'] == OLD_RELEASE_ID, 'installed release is not M10')
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

    # Core: unchanged image; the previous image and commit move to the M10 values (validateSuccessor).
    require(out['core'] == dict(name='gc', source=ARTIFACT, destination=GC, sha256=NEW, mode=0o755)
            and md['writer'] == dict(name='', path=GC, sha256=NEW, mode=0o755), 'exact installed Core predecessor')
    require(out['previous_sha256'] == OLDER and out['backup_path'] == OLD_BACKUP, 'exact M10 previous image and backup')
    require(out['activation'] == dict(expected_commit=COMMIT, expected_version=VERSION,
                                      previous_commit=OLDER_COMMIT, previous_version=VERSION),
            'exact predecessor activation')
    require(pins[GC]['sha256'] == NEW and pins[GC]['size'] == NEW_SIZE and pins[GC]['mode'] == 0o755, 'installed image')
    require(pins[BACKUP]['sha256'] == NEW and pins[BACKUP]['size'] == NEW_SIZE and pins[BACKUP]['mode'] == 0o755,
            'previous image backup')
    out['previous_sha256'] = NEW
    out['backup_path'] = BACKUP
    out['activation']['previous_commit'] = COMMIT

    out['release_id'] = RELEASE_ID
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt, parents=copy.deepcopy(parents), evidence=ROOT+'/t')

    # Superseded rows move in place (see SUPERSEDED_INPUTS); each old path must be referenced nowhere else in the
    # predecessor (r2, review A should_fix 1: computed from the untouched predecessor, including every managed-file
    # backup and integrity file), except the two predecessor backups M11 itself replaces.
    referenced = ({old['core']['source'], old['backup_path']} | {f['source'] for f in old['managed_files']}
                  | {f['backup_path'] for f in old['managed_files']} | {f['path'] for f in old['integrity']['files']}
                  | {p['path'] for p in old['integrity']['providers']} | {r['path'] for r in old['integrity']['repositories']})
    successors = {BACKUP: (NEW, 0o755), CITY_SOURCE: (CITY_NEW, 0o644), WRAPPER: (WRAPPER_SHA, 0o755),
                  WRAPPER_LIB: (WRAPPER_LIB_SHA, 0o644)}
    for old_path, new_path in SUPERSEDED_INPUTS:
        row = _one(md['inputs'], 'path', old_path, 'superseded input cardinality: ' + old_path)
        require(old_path not in referenced - {OLD_BACKUP, CITY_OLD_BACKUP}, 'superseded input still referenced: ' + old_path)
        require(not any(p['path'] == new_path for p in md['inputs']), 'successor already present: ' + new_path)
        digest, mode = successors[new_path]
        require(pins[new_path]['sha256'] == digest and pins[new_path]['mode'] == mode, 'successor bytes: ' + new_path)
        row.update(path=new_path, sha256=digest, mode=mode)

    # The activation's two rewritten files, in both places M10 pins them (the M8 pattern).
    for path, before, after in CHANGED_INPUTS:
        pin = _one(md['inputs'], 'path', path, 'changed input cardinality: ' + path)
        integrity = _one(out['integrity']['files'], 'path', path, 'changed integrity file cardinality: ' + path)
        require(pin['sha256'] == before and integrity['sha256'] == before, 'exact M10 predecessor: ' + path)
        require(pins[path]['sha256'] == after and pins[path]['mode'] == pin['mode'] == integrity['mode'],
                'activation postimage: ' + path)
        pin['sha256'] = after
        integrity['sha256'] = after

    # City config (the M10 pattern): the M10 source holds exactly the predecessor bytes and becomes the backup.
    config = _one(out['managed_files'], 'name', 'city-config', 'city config managed file')
    require(config == dict(name='city-config', source=CITY_OLD_SOURCE, destination=CITY_TOML, sha256=CITY_OLD,
                           mode=0o644, previous_sha256=CITY_OLDER, backup_path=CITY_OLD_BACKUP),
            'exact predecessor city config')
    require(all(f['previous_sha256'] == f['sha256'] for f in out['managed_files'] if f['name'] != 'city-config'),
            'every other managed file already carries its own baseline')
    require(pins[CITY_TOML]['sha256'] == CITY_NEW and pins[CITY_TOML]['mode'] == 0o644, 'installed city config')
    require(pins[CITY_OLD_SOURCE]['sha256'] == CITY_OLD and pins[CITY_OLD_SOURCE]['mode'] == 0o644,
            'city config backup bytes')
    require(_one(md['inputs'], 'path', CITY_OLD_SOURCE, 'city backup input cardinality')['sha256'] == CITY_OLD,
            'city backup input')
    config.update(source=CITY_SOURCE, sha256=CITY_NEW, previous_sha256=CITY_OLD, backup_path=CITY_OLD_SOURCE)
    city_input = _one(md['inputs'], 'path', CITY_TOML, 'installed city input cardinality')
    require(city_input == dict(name='', path=CITY_TOML, sha256=CITY_OLD, mode=0o644), 'installed city input')
    city_input['sha256'] = CITY_NEW

    # The Template lane: the templates/claude tree replaces its four inputs; the wrapper is a platform provider.
    for path in REMOVED_INPUTS:
        _one(md['inputs'], 'path', path, 'removed input cardinality: ' + path)
    md['inputs'] = [p for p in md['inputs'] if p['path'] not in REMOVED_INPUTS]
    for path, digest in NEW_TREES:
        require(not any(t['path'] == path for t in md['trees']) and trees[path]['sha256'] == digest,
                'new tree: ' + path)
        md['trees'].append(dict(name='', path=path, sha256=digest, mode=0o755))
    providers = out['integrity']['providers']
    require([p['name'] for p in providers] == ['claude-native', 'codex', 'claude', 'claude']
            and _one(providers, 'path', SIGNING_WRAPPER, 'signing provider')['sha256'] == SIGNING_WRAPPER_SHA
            and _one(providers, 'path', CANDIDATE_WRAPPER, 'candidate provider')['sha256'] == CANDIDATE_WRAPPER_SHA,
            'exact M10 provider list')
    require(not any(p['path'] == WRAPPER or p['resolved_path'] == WRAPPER for p in providers), 'wrapper already pinned')
    providers.append(copy.deepcopy(PROVIDER))
    require(len(providers) == PROVIDER_COUNT, 'provider count')

    repos = out['integrity']['repositories']
    require(repos[-1] == dict(name=AUTHORITY_NAME, path=AUTHORITY, commit=AUTHORITY_COMMIT), 'unchanged last authority')
    require(not any(r['path'] == TEMPLATE or r['commit'] == TEMPLATE_COMMIT for r in repos), 'authority already pinned')
    repos.append(dict(TEMPLATE_AUTHORITY))
    for path, (before, after) in EXACT_TREES.items():
        pin = _one(md['trees'], 'path', path, 'exact tree cardinality: ' + path)
        require(pin['sha256'] == before and trees[path]['sha256'] == after, 'captured tree: ' + path)
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
    require(frame['remaining_bytes'] > FRAME_FLOOR, 'frame margin below the M11 floor')
    return out, dict(preparation_only=True, live_acceptance=False, frame=frame, input_count=INPUT_COUNT,
                     tree_count=TREE_COUNT, link_count=LINK_COUNT, runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed M10 manifest drift')
    require(BASELINE_SHA is not None, 'baseline not yet frozen and reviewed')
    require(hashlib.sha256(baseline_bytes).hexdigest() == BASELINE_SHA, 'current baseline drift')
    old = json.loads(old_bytes); closure = json.loads(baseline_bytes)['closure']
    return assemble(old, closure, host, parents, transaction, attempt)


def receipt():
    """Read only the exact root-custodied sequence 16 receipt; the Core image is unchanged since."""
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
            and value['after']['sha256'] == NEW and value['source']['commit'] == COMMIT, 'seq16 receipt binding')
    return value
