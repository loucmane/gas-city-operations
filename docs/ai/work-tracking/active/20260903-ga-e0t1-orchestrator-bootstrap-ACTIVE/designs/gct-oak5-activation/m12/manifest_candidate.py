"""Pure M12 metadata successor: adopt the Template-candidate codex worklog choice (gct-oak5 A2) over M11.

The predecessor is the installed M11 manifest (file 9f60c3bf, reports/m11/q/manifest.json). The reviewed A2
activation (operator decision 2026-09-27, "New codex choice"; package cdcdaccd, two reviews; applied f17c55a9)
changed exactly one M11 pin: city.toml b0eeb168 -> bdcec254 (one new codex worklog_access choice and the
candidate root in the Template codex work_dir_roots). The M11 inspector reports exactly that as drift
(managed_files[city-config]).

M12 is the M10 city-config pattern alone:
- the city-config managed file moves to the new source reports/m12-inputs/city.toml (bdcec254); its
  previous_sha256 becomes M11's sha256 (b0eeb168) and its backup_path the M11 source reports/m11-inputs/city.toml,
  which holds exactly those bytes and is already an input;
- the installed city.toml input moves to bdcec254;
- the new source takes over, in place, the input row of the superseded M10 source reports/m10-inputs/city.toml
  (e5b68c40), which after M12 is referenced nowhere else. The file stays on disk, unchanged.
Everything else is unchanged and asserted: the Core image, writer, previous image and activation (already at the
successor values since M11), every other managed file, input, tree, link, provider and repository (the canonical
Template authority stays 3474abfa, allow_dirty), the cache and the counts. Release, transaction, attempt, parents,
evidence, host, namespaces and previous metadata are fresh (reports/m12), the M6-M11 pattern. There is no new broker
receipt: sequence 16's 1108b724 still binds the image.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/m11'
ROOT = O + '/reports/m12'
OLD_MANIFEST_SHA = '9f60c3bf69a64e3483b2a069fd542ae4ddefee5c0e63f1bc06a388ab7f59a1be'
OLD_RECEIPT_SHA = '746644c7229b07c037839fd48a54e2f7a1e9d956db061e2fa69016ae2e901307'
OLD_RELEASE_ID = 'gct-oak5-template-candidate-lane-metadata-m11-20260927'
BASELINE_PATH = O + '/reports/m12-capture/baseline.json'
# Frozen by the 2026-09-27 capture (candidate 15570e72 at 572f3c7d, after prereqs_m12.py; zero drifts, exactly the two
# admitted pin changes and the known cache Git bookkeeping). Nobody runs gc, workflow.py, a Bead write or git in a
# pinned repository until restore-accepted.
BASELINE_SHA = '98f31719bbc02986e3d165a614149411ae9d689c00a6f98f2932097d1fe5e369'
SUSPENSION_SHA = 'a3306567b3cf77e6371a870e6df239194574fab8f2dc3090ea55a5eeb14b4817'
TEMPLATE = '/home/loucmane/gas-city-template'
TEMPLATE_COMMIT = '3474abfaec255f7ea4266ce8aa35218afcfc89b0'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
RELEASE_ID = 'gct-oak5-codex-candidate-choice-metadata-m12-20260927'
TEMPLATE_AUTHORITY = dict(name='template-pr72-canonical', path=TEMPLATE, commit=TEMPLATE_COMMIT, allow_dirty=True)

GC = '/home/loucmane/gascity/bin/gc'
ARTIFACT = '/var/tmp/ga-bebv-build-20260927/gc-a'
BACKUP = '/var/tmp/ga-bebv-build-20260927/gc-b'
OLD = NEW = '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f'
NEW_SIZE = 134146157
COMMIT = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
VERSION = 'dev'
WATCHDOG_IMAGE = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'

CITY = '/home/loucmane/gascity/city'
CITY_TOML = CITY + '/city.toml'
CITY_OLDER = 'e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077'
CITY_OLD = 'b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b'
CITY_NEW = 'bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1'
CITY_OLD_SOURCE = O + '/reports/m11-inputs/city.toml'
CITY_SOURCE = O + '/reports/m12-inputs/city.toml'
CITY_OLD_BACKUP = O + '/reports/m10-inputs/city.toml'
# The Template wrapper provider (M11), asserted unchanged; the gate extract names it.
WRAPPER = TEMPLATE + '/bin/gct-claude-template-candidate-worker'

# Names the capture and the gate extract read. M12 removes no input, adds no tree and changes no integrity file.
REMOVED_INPUTS = ()
CHANGED_INPUTS = ()
NEW_TREES = ()
EXACT_TREES = {}
SUPERSEDED_INPUTS = ((CITY_OLD_BACKUP, CITY_SOURCE),)
NEW_INPUTS = ((CITY_TOML, CITY_NEW, 0o644), (CITY_SOURCE, CITY_NEW, 0o644))
CACHE = '/home/loucmane/gascity/home/cache/repos'
CACHE_SHA = '4b284f6741eb8a4e2273fe94bd7e5d24b8ae318ca862170b80c6fd75f37f72be'
INPUT_COUNT = 692
TREE_COUNT = 50
LINK_COUNT = 23
PROVIDER_COUNT = 5
REPOSITORY_COUNT = 8
FRAME_FLOOR = 256

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
    """Pure construction from the installed M11 predecessor and a frozen closure."""
    require(b.finalized(old) == old and host == closure['host'], 'manifest/host binding')
    require(old['release_id'] == OLD_RELEASE_ID, 'installed release is not M11')
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

    # Core: unchanged image, previous image and activation (M11 already carries the successor values).
    require(out['core'] == dict(name='gc', source=ARTIFACT, destination=GC, sha256=NEW, mode=0o755)
            and md['writer'] == dict(name='', path=GC, sha256=NEW, mode=0o755), 'exact installed Core predecessor')
    require(out['previous_sha256'] == NEW and out['backup_path'] == BACKUP, 'exact M11 previous image and backup')
    require(out['activation'] == dict(expected_commit=COMMIT, expected_version=VERSION,
                                      previous_commit=COMMIT, previous_version=VERSION), 'exact M11 activation')
    require(pins[GC]['sha256'] == NEW and pins[GC]['size'] == NEW_SIZE and pins[GC]['mode'] == 0o755, 'installed image')
    require(pins[BACKUP]['sha256'] == NEW and pins[BACKUP]['size'] == NEW_SIZE and pins[BACKUP]['mode'] == 0o755,
            'previous image backup')

    out['release_id'] = RELEASE_ID
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt, parents=copy.deepcopy(parents), evidence=ROOT+'/t')

    # The superseded M10 city source row moves in place to the new source; it must be referenced nowhere else in
    # the untouched predecessor except as the city-config backup M12 itself replaces.
    referenced = ({old['core']['source'], old['backup_path']} | {f['source'] for f in old['managed_files']}
                  | {f['backup_path'] for f in old['managed_files']} | {f['path'] for f in old['integrity']['files']}
                  | {p['path'] for p in old['integrity']['providers']} | {r['path'] for r in old['integrity']['repositories']})
    for old_path, new_path in SUPERSEDED_INPUTS:
        row = _one(md['inputs'], 'path', old_path, 'superseded input cardinality: ' + old_path)
        require(row == dict(name='', path=old_path, sha256=CITY_OLDER, mode=0o644), 'exact superseded row: ' + old_path)
        require(old_path not in referenced - {CITY_OLD_BACKUP}, 'superseded input still referenced: ' + old_path)
        require(not any(p['path'] == new_path for p in md['inputs']), 'successor already present: ' + new_path)
        require(pins[new_path]['sha256'] == CITY_NEW and pins[new_path]['mode'] == 0o644, 'successor bytes: ' + new_path)
        row.update(path=new_path, sha256=CITY_NEW, mode=0o644)

    # City config (the M10 pattern): the M11 source holds exactly the predecessor bytes and becomes the backup.
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

    # Unchanged since M11: providers, repositories (the canonical Template authority last) and the cache.
    providers = out['integrity']['providers']
    require(len(providers) == PROVIDER_COUNT and providers == old['integrity']['providers']
            and _one(providers, 'path', WRAPPER, 'Template provider')['name'] == 'claude', 'exact M11 providers')
    repos = out['integrity']['repositories']
    require(len(repos) == REPOSITORY_COUNT and repos[-1] == TEMPLATE_AUTHORITY, 'exact M11 repositories')
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
    require(frame['remaining_bytes'] > FRAME_FLOOR, 'frame margin below the M12 floor')
    return out, dict(preparation_only=True, live_acceptance=False, frame=frame, input_count=INPUT_COUNT,
                     tree_count=TREE_COUNT, link_count=LINK_COUNT, runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed M11 manifest drift')
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
