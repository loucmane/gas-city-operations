"""Pure M6 metadata successor: sequence 14 Core plus Template cfd353f3 (ga-e0t1.15 S3).

The predecessor is the installed M5 manifest 2d7eadce (reports/m5/q/manifest.json holds the same
bytes). M6 combines two reviewed successor patterns and nothing else:
- R9 (reports/ga-mutg-metadata-quiet-r9-20260920/manifest_candidate.py), the last Core change: core
  source and digest, activation.expected_commit, the writer, the installed gc input, the appended
  build source, and the Core rig object tree. previous_sha256 and backup_path already name the image
  being replaced (69d00186 and gc-b), exactly as R9 left them for its own predecessor.
- M5 (designs/gct-m1wh-m5/manifest_candidate.py), the last Template change: the signing-worker parser,
  the provider version, the Template common Git directory, and a fresh clean authority worktree with
  complete explicit coverage.
Two more exact re-pins come from the sequence 14 install (S2), whose accepted recovery closure
(/var/tmp/ga-e0t1.15-seq14-recovery-20260925/observation-2.json) recorded them: the pack cache (the new
synthetic core-pack directory) and the Core rig object tree. And one distribution security update:
libexpat1 2.6.1-2ubuntu0.5 -> 0.6, installed by unattended-upgrade on 2026-09-25 at 06:25:40
(dpkg --verify clean, md5 22f36128 equals the package record), the same class as M5's libexpat re-pin.

The managed file city-config takes its own sha256 as previous_sha256, with a fresh pinned backup of those
bytes, as Core's successor rule requires (see CITY_CONFIG_* below).

The PR 69 authority's coverage is REPLACED by the PR 71 authority's, not kept beside it: M5 left 3001
spare frame bytes and a second 34-pin authority needs about 5.5 KB. The PR 69 worktree stays on disk,
clean and unreferenced. This is the one narrowing; PLAN-S3.md records it for review.

Every new digest is a constant derived from Git objects (derive_m6.py), live distribution or build bytes,
or a tree digest from the frozen baseline. Nothing here reads the host except the pinned baseline and the
root-custodied broker receipt.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
OLD_ROOT = O + '/reports/m5'
ROOT = O + '/reports/m6'
OLD_MANIFEST_SHA = '2d7eadce62c4e567697813cc9122414f1e94c3bd9d389aef92015adef7f36319'
OLD_RECEIPT_SHA = '9342b33eb7b0fd4e68a34c8cee3b8a89b9011a091d7121d249b88c84378fed94'
BASELINE_PATH = O + '/reports/m6-capture/baseline.json'
BASELINE_SHA = None  # pinned by the binding step after the capture, then reviewed
SUSPENSION_SHA = 'c30776de4fdb359a0083ecf9efc20e56595ede9472de3d93e69f47c55439dcb5'
TEMPLATE = '/home/loucmane/gas-city-template'
M5_COMMIT = '28539934fa742056e0a65710d5638ff559a21175'
TEMPLATE_COMMIT = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
M5_AUTHORITY = '/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority'
M5_AUTHORITY_NAME = 'template-pr69-authority'
AUTHORITY = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
AUTHORITY_NAME = 'template-pr71-authority'
RELEASE_ID = 'template-pr71-core-seq14-metadata-m6-20260925'

# Core (the R9 pattern).
GC = '/home/loucmane/gascity/bin/gc'
OLD_SOURCE = '/var/tmp/ga-mutg-custody-build-20260920/gc-a'
BACKUP = '/var/tmp/ga-mutg-custody-build-20260920/gc-b'
ARTIFACT = '/var/tmp/ga-e0t1.15-build-20260925/gc-a'
OLD = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'
NEW = 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'
NEW_SIZE = 134052980
OLD_COMMIT = '796d9a7a67c42294fdc467c107bb59b76e482301'
COMMIT = '9faeabc2892d8c7133111e13ad55af66790a2ac6'
VERSION = 'dev'

# (path, predecessor sha256, successor sha256) for inputs whose bytes changed. Modes are unchanged.
CHANGED_INPUTS = (
    (TEMPLATE + '/lib/gct_claude_signing_worker.py',
     '4e28d5b826a7471dec27e66ee3536233bbaa2ebc6ece162b4d3ca8cccd0970bd',
     'a216552b7ae8be327cacbef9e22bc4e190d383dad4ab808ee56b984f38414394'),
    ('/usr/lib/x86_64-linux-gnu/libexpat.so.1.9.1',
     'ec6c12d33bb8f9d0e90804121adf19930f36b1b2a4aeb6e1a454b89c7a50c801',
     '286682ecbc5e59a638963b1a4e6351e65eb32fcf4bdcb9cb7569b6a61fe06a8d'),
)
# Exact successor byte sizes of the changed inputs the live prerequisites move (the cfd353f3 blob). The S2
# closure pins size too, so the capture binds the whole successor pin (review A of f8fcb751, must_fix 1).
# libexpat is absent: it was already at its successor in the S2 closure and must stay unchanged.
SUCCESSOR_SIZES = {TEMPLATE + '/lib/gct_claude_signing_worker.py': 14668}
# Canonical Template files that cfd353f3 leaves byte-identical (derive_m6.py proves it from Git objects).
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
NATIVE_CLI = '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
NATIVE_VERSION = '2.1.280 (Claude Code)'
VERSION_OLD = ('gct-claude-signing-worker 1 dependencies_sha256='
               'f36deb20efa5cc11781f1d9703b8e5e0d7897c6357260dff1045bcd86489ff34')
VERSION_NEW = ('gct-claude-signing-worker 1 dependencies_sha256='
               'd4e57767d03accd708ce8876580096bb17bce023d6dc6e664fffee4367ea3c57')

# Trees. The object tree and cache must equal the S2-accepted digests exactly; the Template common Git
# directory (fetch of cfd353f3, checkout advance, new linked worktree) takes the bounded baseline digest.
TEMPLATE_GIT = TEMPLATE + '/.git'
ODB = '/home/loucmane/gascity/city/rigs/gascity/.git/objects'
CACHE = '/home/loucmane/gascity/home/cache/repos'
EXACT_TREES = {
    ODB: ('361e500a6f42fee7340614957a1598ff3fff509490e1e9640c67738ed4903617',
          'ae95c30c08375b9c2e5351e164c1c6a8895444f5a23b2de3c2d95366fd644520'),
    CACHE: ('e5e959dd7766d032360bd54548ace93c38e46e78764fe3386524552e5606faaa',
            '4b284f6741eb8a4e2273fe94bd7e5d24b8ae318ca862170b80c6fd75f37f72be'),
}
TEMPLATE_GIT_OLD = '33bd60d3a60b0d66c05ccbbdb640544753b6798afc19a2250327ca5668d146ab'
TEMPLATE_GIT_S2 = 'cac98745456b778aa6fb0d2b22f9cdd75c7d9ca1ed05c1b28a6fef3937f7d96b'

# Complete coverage of the 294 tracked paths of cfd353f3 (derive_m6.py, the unchanged M5 method).
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
    ('.git', None, 420),
)
AUTH_TREES = ('.beads', '.claude', '.codex', '.github', '.plan_state', 'agents', 'assets',
              'bin', 'docs', 'formulas', 'hooks', 'lib', 'managed', 'orders', 'patches',
              'schemas', 'sessions/2026', 'template-fragments', 'templates', 'tests')
AUTH_LINKS = (
    ('plans/current', '2026-09-22-gct-er3h-opus-5-5-worker-profiles.md'),
    ('sessions/current', '2026/09/2026-09-22-003-gct-er3h-opus-5-5-worker-profiles.md'),
)
# Managed file city-config. M5 moved its sha256 to 4f7e170f and kept previous_sha256 6594ee77 with backup
# r5/i/00 (M5 LAYOUT.md 187-193). Core's validateSuccessor (installer.go 405-413) requires every candidate
# managed file's previous_sha256 to equal the previous manifest's sha256, and metadata-only adoption requires
# an existing backup holding those bytes (metadata_adopt.go 73-77). M6 therefore sets previous_sha256 to
# 4f7e170f with a fresh pinned backup of exactly those bytes, written by the `inventory` prerequisite from
# the live file (review A of dc5c46b5, must_fix 1). The five other managed files already have
# previous_sha256 == sha256 and stay unchanged.
CITY_CONFIG_SOURCE = O + '/reports/m5-inputs/city.toml'
CITY_CONFIG_SHA = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
CITY_CONFIG_OLD_PREVIOUS = '6594ee77b3efc30cd2f4cfa412541a5a1076fb324118fb8aec3df1d29b81528b'
CITY_CONFIG_OLD_BACKUP = O + '/reports/r5/i/00'
CITY_CONFIG_BACKUP = O + '/reports/m6-inputs/city.toml.before'
# M5 counts 685 inputs, 49 trees, 23 links. M6 adds the build source and the city-config backup, and swaps
# two equal-shape authorities.
INPUT_COUNT = 685 + 2
TREE_COUNT = 49
LINK_COUNT = 23

REQUEST = 'f04c12405243322dee599d5398dbb4abd586b6e8e6556348dcbb779447b104e0'
RECEIPT_SHA = 'f55fed69645eea86e05e4fef804cbd1b4c254cc34f52dcc02e30ea1cc2b460a1'
RECEIPT_SIZE = 1229

P = Path(O + '/reports/ga-mutg-metadata-quiet-r9-20260920/manifest_candidate.py')
raw = P.read_bytes()
if hashlib.sha256(raw).hexdigest() != '8a9145f50f48254fbf82938b6a6137d7e78ea0ceb5586d6b09579a1954d8a72e':
    raise RuntimeError('reviewed predecessor helper drift')
prior = types.ModuleType('reviewed_predecessor'); prior.__file__ = str(P)
exec(compile(raw, str(P), 'exec', dont_inherit=True), prior.__dict__)
r7, b, require = prior.r7, prior.b, prior.require


def authority_pointer():
    """The linked-worktree .git pointer file bytes, exactly as `git worktree add` writes them."""
    return ('gitdir: ' + TEMPLATE + '/.git/worktrees/' + Path(AUTHORITY).name + '\n').encode()


def auth_inputs():
    pointer = hashlib.sha256(authority_pointer()).hexdigest()
    return tuple((relative, pointer if digest is None else digest, mode) for relative, digest, mode in AUTH_INPUTS)


def _one(rows, key, value, reason):
    found = [row for row in rows if row[key] == value]
    require(len(found) == 1, reason)
    return found[0]


def _under(path, root):
    return path == root or path.startswith(root + '/')


def assemble(old, closure, host, parents, transaction, attempt):
    """Pure construction from the installed M5 predecessor and a frozen closure."""
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

    # Core: the R9 pattern. The image being replaced is already the recorded previous image and backup.
    require(out['core']['source'] == OLD_SOURCE and out['core']['sha256'] == OLD
            and out['core']['destination'] == GC and md['writer']['path'] == GC
            and md['writer']['sha256'] == OLD, 'exact installed Core predecessor')
    require(out['previous_sha256'] == OLD and out['backup_path'] == BACKUP
            and pins[BACKUP]['sha256'] == OLD and pins[BACKUP]['mode'] == out['core']['mode'],
            'exact previous image and backup')
    require(out['activation'] == dict(expected_commit=OLD_COMMIT, expected_version=VERSION,
                                      previous_commit=OLD_COMMIT, previous_version=VERSION),
            'exact predecessor activation')
    require(pins[GC]['sha256'] == NEW and pins[GC]['size'] == NEW_SIZE and pins[GC]['mode'] == 0o755,
            'installed sequence 14 image')
    require(pins[ARTIFACT]['sha256'] == NEW and pins[ARTIFACT]['mode'] == 0o755, 'sequence 14 build source')
    require(not any(p['path'] == ARTIFACT for p in md['inputs']), 'build source already present')
    out['core'].update(source=ARTIFACT, sha256=NEW)
    # previous_commit already equals the M5 expected_commit, which the native installer requires.
    out['activation']['expected_commit'] = COMMIT
    md['writer']['sha256'] = NEW
    _one(md['inputs'], 'path', GC, 'installed Core input cardinality')['sha256'] = NEW
    md['inputs'].append(dict(name='', path=ARTIFACT, sha256=NEW, mode=0o755))

    out['release_id'] = RELEASE_ID
    # The native wire uses predecessor struct order, not caller dictionary order.
    md['host'].update(host['host'])
    md['namespaces'].update(host['namespaces'])
    md.update(transaction=transaction, attempt=attempt, parents=copy.deepcopy(parents), evidence=ROOT+'/t')

    for path, before, after in CHANGED_INPUTS:
        pin = _one(md['inputs'], 'path', path, 'changed input cardinality: ' + path)
        require(pin['sha256'] == before, 'exact predecessor input: ' + path)
        require(pins[path]['sha256'] == after and pins[path]['mode'] == pin['mode'], 'reviewed successor input: ' + path)
        pin['sha256'] = after
    for path, digest in RETAINED_TEMPLATE_PINS.items():
        pin = _one(md['inputs'], 'path', path, 'retained Template input: ' + path)
        require(pin['sha256'] == digest and pins[path]['sha256'] == digest, 'retained Template bytes: ' + path)
    config = _one(out['managed_files'], 'name', 'city-config', 'city config managed file')
    require(config == dict(name='city-config', source=CITY_CONFIG_SOURCE, destination='/home/loucmane/gascity/city/city.toml',
                           sha256=CITY_CONFIG_SHA, mode=0o644, previous_sha256=CITY_CONFIG_OLD_PREVIOUS,
                           backup_path=CITY_CONFIG_OLD_BACKUP), 'exact predecessor city config')
    require(all(f['previous_sha256'] == f['sha256'] for f in out['managed_files'] if f['name'] != 'city-config'),
            'other managed files already carry their own baseline')
    require(pins[CITY_CONFIG_BACKUP]['sha256'] == CITY_CONFIG_SHA and pins[CITY_CONFIG_BACKUP]['mode'] == 0o644
            and pins['/home/loucmane/gascity/city/city.toml']['sha256'] == CITY_CONFIG_SHA, 'city config backup bytes')
    require(not any(p['path'] == CITY_CONFIG_BACKUP for p in md['inputs']), 'city config backup duplicate')
    config.update(previous_sha256=CITY_CONFIG_SHA, backup_path=CITY_CONFIG_BACKUP)
    md['inputs'].append(dict(name='', path=CITY_CONFIG_BACKUP, sha256=CITY_CONFIG_SHA, mode=0o644))
    native = _one(out['integrity']['providers'], 'name', 'claude-native', 'native provider')
    require(native['sha256'] == NATIVE_CLI and native['version'] == NATIVE_VERSION, 'unchanged native provider')
    worker = _one(out['integrity']['providers'], 'name', 'claude', 'signing provider')
    require(worker['version'] == VERSION_OLD
            and worker['path'] == worker['resolved_path'] == TEMPLATE + '/bin/gct-claude-signing-worker'
            and worker['sha256'] == RETAINED_TEMPLATE_PINS[worker['path']], 'exact predecessor worker')
    worker['version'] = VERSION_NEW

    for path, (before, after) in EXACT_TREES.items():
        pin = _one(md['trees'], 'path', path, 'exact tree cardinality: ' + path)
        require(pin['sha256'] == before and trees[path]['sha256'] == after, 'S2-accepted tree: ' + path)
        pin['sha256'] = after
    require(md['cache_sha256'] == EXACT_TREES[CACHE][0], 'cache digest predecessor')
    md['cache_sha256'] = EXACT_TREES[CACHE][1]
    pin = _one(md['trees'], 'path', TEMPLATE_GIT, 'Template Git tree cardinality')
    require(pin['sha256'] == TEMPLATE_GIT_OLD and trees[TEMPLATE_GIT]['sha256'] not in (TEMPLATE_GIT_OLD, TEMPLATE_GIT_S2),
            'Template Git tree predecessor and bounded successor')
    pin['sha256'] = trees[TEMPLATE_GIT]['sha256']

    # Authority: replace the PR 69 coverage and repository with the PR 71 ones.
    repos = out['integrity']['repositories']
    m5_repo = _one(repos, 'name', M5_AUTHORITY_NAME, 'M5 authority repository')
    require(m5_repo == dict(name=M5_AUTHORITY_NAME, path=M5_AUTHORITY, commit=M5_COMMIT) and repos[-1] == m5_repo,
            'M5 authority is the last repository')
    require(not any(p['path'] == AUTHORITY or p['name'] == AUTHORITY_NAME or p['commit'] == TEMPLATE_COMMIT
                    for p in repos), 'authority already present')
    removed = dict(inputs=[p for p in md['inputs'] if _under(p['path'], M5_AUTHORITY)],
                   trees=[p for p in md['trees'] if _under(p['path'], M5_AUTHORITY)],
                   links=[p for p in md['links'] if _under(p['path'], M5_AUTHORITY)])
    require((len(removed['inputs']), len(removed['trees']), len(removed['links'])) == (12, 20, 2),
            'M5 authority coverage cardinality')
    md['inputs'] = [p for p in md['inputs'] if not _under(p['path'], M5_AUTHORITY)]
    md['trees'] = [p for p in md['trees'] if not _under(p['path'], M5_AUTHORITY)]
    md['links'] = [p for p in md['links'] if not _under(p['path'], M5_AUTHORITY)]
    repos.remove(m5_repo)
    repos.append(dict(name=AUTHORITY_NAME, path=AUTHORITY, commit=TEMPLATE_COMMIT))
    existing = {p['path'] for p in md['inputs']} | {p['path'] for p in md['trees']} | {p['path'] for p in md['links']}
    require(not any(_under(x, AUTHORITY) or AUTHORITY.startswith(x + '/') for x in existing),
            'authority coverage overlaps an existing pin')
    for relative, digest, mode in auth_inputs():
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
    # Every pin the successor names, carried or changed, must equal the frozen baseline (review A should_fix 4),
    # so a stale carried digest refuses here rather than inside a consumed native window.
    for p in md['inputs']:
        require(pins[p['path']]['sha256'] == p['sha256'] and pins[p['path']]['mode'] == p['mode'],
                'input differs from the baseline: ' + p['path'])
    for p in md['trees']:
        require(trees[p['path']]['sha256'] == p['sha256'], 'tree differs from the baseline: ' + p['path'])
    for p in md['links']:
        require(links.get(p['path']) == p['target'], 'link differs from the baseline: ' + p['path'])
    out = b.finalized(out); frame = b.frame_bound(out)
    return out, dict(preparation_only=True, live_acceptance=False, removed_m5_authority=removed,
                     frame=frame, input_count=INPUT_COUNT, tree_count=TREE_COUNT, link_count=LINK_COUNT,
                     runtime_count=len(md['runtime']))


def build(old_bytes, baseline_bytes, host, parents, transaction, attempt):
    require(hashlib.sha256(old_bytes).hexdigest() == OLD_MANIFEST_SHA, 'installed M5 manifest drift')
    require(BASELINE_SHA is not None, 'baseline not yet frozen and reviewed')
    require(hashlib.sha256(baseline_bytes).hexdigest() == BASELINE_SHA, 'current baseline drift')
    old = json.loads(old_bytes); closure = json.loads(baseline_bytes)['closure']
    return assemble(old, closure, host, parents, transaction, attempt)


def receipt():
    """Read only the exact root-custodied sequence 14 receipt, never submit a request."""
    path = Path('/var/lib/gas-city-provisioning/receipts') / (REQUEST + '.json')
    pin = r7.c.s.pin(path, {})
    require(pin == dict(uid=0, gid=986, mode=0o640, size=RECEIPT_SIZE, sha256=RECEIPT_SHA),
            'seq14 receipt custody/digest')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        data = os.read(fd, 65537)
        require(before == os.fstat(fd) and len(data) == before.st_size == RECEIPT_SIZE, 'receipt read race')
    finally:
        os.close(fd)
    require(hashlib.sha256(data).hexdigest() == RECEIPT_SHA, 'receipt byte drift')
    value = json.loads(data)
    require(value['request_id'] == REQUEST and value['sequence'] == 14
            and value['result'] == 'pass' and value['rollback'] == 'not-needed'
            and value['operation'] == 'replace-gas-city-control-plane.v1'
            and value['before']['sha256'] == OLD and value['after']['sha256'] == NEW
            and value['source']['commit'] == COMMIT, 'seq14 receipt binding')
    return value
