"""Generate the P11 worker receipt refresh (ga-bebv S3) from the executed P8/P10 chain by count-checked substitutions.

  python3 -I -B make_p11.py diagnostics   # the three diagnostic sources and their builders
  python3 -I -B make_p11.py scripts       # the chain, after the diagnostics are built and their digests pinned

The installed worker receipt c833908f (P10) carries two profiles, the signing lane gascity/gc.implementation-worker
(ad0c695b) and the candidate gascity/operations-candidate-worker (e641dc17). It still names Core member head
deefb98b and config revision 83c41af6. Since then:
- sequence 16 replaced gc with 207a78e2, built from f45a6262 (tree f1011ada), and restarted the supervisor
  (controller pid 2800348, ExecMainStartTimestampMonotonic 229642910742; signer and broker unchanged);
- M10 installed the replace-mode city.toml e5b68c40, which moved the composed revision; the controller's
  2026-09-27 cycles report gc_commit f45a6262 and config_revision 03f16ea2.
P11 re-pins exactly those two leaves (member_heads[core] deefb98b -> f45a6262, permission_revision 83c41af6 ->
03f16ea2) through the unchanged reviewed provisioner 64425a72. Both profiles, the Template cfd353f3, the pack,
the rules and the canary runner are asserted unchanged, and both compositions are re-proven against Core's own
code at f45a6262:
- prepare-compose-p11.py is the reviewed P8 exact-source builder (56f3ca48) with the Core source moved to the
  sequence 16 reproduction clone at f45a6262 (tree f1011ada) and a fresh root. It builds the P8 signing
  composition (compose-main.go e8cb87a0, unchanged) and, through prepare-compose-candidate-p11.py, the P10
  candidate composition (candidate/compose-main.go 5040c196, unchanged);
- prepare-preflight-p11.py is the P10 preflight builder (90461a4a) over the P11 builder and signing root; its
  preflight-main.go is P10's (cb55f252, unchanged).
The chain is the executed P10 chain, rebound: the input moves two leaves instead of appending a profile, the
platform predecessor is M10 (reports/m10/q), and the adoption witness names Core f45a6262, the sequence 16
build verification and controller 2800348.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
P8 = HERE.parent.parent/'ga-e0t1.18-deploy'/'p8'
P10 = HERE.parent.parent/'ga-e0t1.18-deploy'/'p10'

CORE_SOURCE_OLD, CORE_SOURCE = '/var/tmp/ga-e0t1.18-build-20260926/repro-source', '/var/tmp/ga-bebv-build-20260927/repro-source'
CORE_OLD, CORE = 'deefb98b2aed07875df31351d081fbac195cb1cd', 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE_OLD, TREE = 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99', 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'
GC_OLD, GC = ('fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b',
              '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f')
RECEIPT_P10_OLD, RECEIPT_P10 = ('6bf20a712ef78be16a0e4e79bd495da12e573fdbd9637508803997ebd23e6bc0',
                                'c833908fe89ab180e57ef7164d687f01ae2052f8667360f04b73c5423902f0a4')
REVISION_OLD = '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add'
REVISION = '03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712'
M9_RELEASE, M10_RELEASE = 'ops-candidate-provider-metadata-m9-20260926', 'ga-bebv-core-seq16-city-metadata-m10-20260927'
M8_FILE, M9_FILE = ('63820eacf37a46ec6d6d97cfe0434189a2a41a27c6650462b992d1034da183b8',
                    '5a29dc596af192e0f314391453d25d6be548695a0defd64bdfc2fa76554e4993')
BUILD_EVIDENCE_OLD = ("('reviewed-build','/var/tmp/ga-e0t1.18-build-20260926/artifact-verification.json',"
                      "'d1fea7a531aedf7bc50fbe08b800f8cb3436ba4f2c633471b9eb34c4a51554de')")
BUILD_EVIDENCE = ("('reviewed-build','/var/tmp/ga-bebv-build-20260927/artifact-verification.json',"
                  "'b37088d90b834a06127a989c657a3b9747e06478353dbcbbd4315e80fd03c331')")
BUILDER_P8 = '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4'

SIGN_OLD, SIGN_BUILD = '/var/tmp/ga-e0t1.18-compose-diagnostic-20260926', '/var/tmp/ga-bebv-p11-compose-diagnostic-20260927'
CAND_OLD, CAND_BUILD = ('/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926',
                        '/var/tmp/ga-bebv-p11-candidate-compose-diagnostic-20260927')
PREFLIGHT_OLD, PREFLIGHT_BUILD = ('/var/tmp/ga-e0t1.18-p10-preflight-diagnostic-20260926',
                                  '/var/tmp/ga-bebv-p11-preflight-diagnostic-20260927')
STAGING_OLD, STAGING = ('/var/tmp/ga-e0t1.18-p10-preflight-generated-20260926',
                        '/var/tmp/ga-bebv-p11-preflight-generated-20260927')
INPUT_OLD, INPUT_ROOT = '/var/tmp/ga-e0t1.18-p10-input-20260926', '/var/tmp/ga-bebv-p11-input-20260927'
COMPOSE_OLD, COMPOSE_ROOT = '/var/tmp/ga-e0t1.18-p10-compose-20260926', '/var/tmp/ga-bebv-p11-compose-20260927'
READY_OLD, READY_ROOT = '/var/tmp/ga-e0t1.18-p10-readiness-20260926', '/var/tmp/ga-bebv-p11-readiness-20260927'
ADOPT_OLD, ADOPT_ROOT = '/var/tmp/ga-e0t1.18-p10-adoption-20260926', '/var/tmp/ga-bebv-p11-adoption-20260927'

# Pinned after the diagnostics are built by the builders (make_p11.py diagnostics, then the three builders).
SIGN_COMPOSE_SHA = '8fb4706199132024fa37b53826ceb91f367f3c309afceef023e84d46bab3bbb2'
CANDIDATE_COMPOSE_SHA = '8cb667dc8a65a858c9df2708a5e42ece79f59ce10a1372b817b8e656aa3ae207'
PREFLIGHT_SHA = '85a2cc6b575ff3fd4660e41241031a813f1264486b6d82084f93c7c9fddc96f5'
EXTRACTION_SHA = '8160f4ec82d00169c5a32065d0389df9d7b68caa0a7fc21413436ad9de216433'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source(path, digest):
    raw = Path(path).read_bytes()
    if sha(raw) != digest:
        raise SystemExit('reviewed source drift: %s' % path)
    return raw.decode()


def substitute(text, substitutions, name):
    for old, new, count in substitutions:
        found = text.count(old)
        if found != count:
            raise SystemExit('%s: expected %d occurrence(s) of %r, found %d' % (name, count, old[:80], found))
        text = text.replace(old, new)
    return text


def write(name, text):
    path = HERE/name
    path.parent.mkdir(exist_ok=True)
    data = text.encode() if isinstance(text, str) else text
    path.write_bytes(data)
    path.chmod(0o644)
    print(name, sha(data))
    return sha(data)


def docstring(text, new):
    end = text.index('"""\n', 3) + 4
    return new + text[end:]


def stale(text, name, tokens):
    for token in tokens:
        if token in text:
            raise SystemExit('%s: stale token %r remains' % (name, token))


# ---------------------------------------------------------------------------------------------------------------
# Diagnostics


def compose_builder():
    text = source(P8/'prepare-compose-p8.py', BUILDER_P8)
    text = substitute(text, [
        ('"""Prepare an isolated exact-source build, retaining all generated evidence.\n',
         '"""Prepare an isolated exact-source build, retaining all generated evidence.\n\n'
         'P11: the reviewed P8 builder (56f3ca48) with the Core source moved to the sequence 16 reproduction clone\n'
         'at f45a6262 (tree f1011ada) and a fresh root (ga-bebv-deploy/p11/make_p11.py).\n', 1),
        ("ROOT = Path('%s')" % SIGN_OLD, "ROOT = Path('%s')" % SIGN_BUILD, 1),
        ("CORE = Path('%s')" % CORE_SOURCE_OLD, "CORE = Path('%s')" % CORE_SOURCE, 1),
        ("COMMIT = '%s'" % CORE_OLD, "COMMIT = '%s'" % CORE, 1),
        ("if core_tree != '%s':" % TREE_OLD, "if core_tree != '%s':" % TREE, 1),
    ], 'prepare-compose-p8.py')
    return write('prepare-compose-p11.py', text)


CANDIDATE_BUILDER = '''"""P11 candidate composition diagnostic: the P11 exact-source builder, unchanged, into a fresh root.

Only the root and the composition source directory change. candidate/compose-main.go is the P10 candidate
composition source (5040c196), byte for byte. The builder records the Core commit, tree, archive, Go executable
and the source digest in build-result.json.
"""
import hashlib
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILDER = HERE/'prepare-compose-p11.py'
EXPECTED = '%(builder)s'
ROOT = Path('%(root)s')
MAIN_SHA = '%(main)s'


def main():
    raw = BUILDER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('reviewed builder drift')
    if hashlib.sha256((HERE/'candidate'/'compose-main.go').read_bytes()).hexdigest() != MAIN_SHA:
        raise RuntimeError('candidate composition source drift')
    builder = types.ModuleType('reviewed_exact_builder'); builder.__file__ = str(BUILDER)
    exec(compile(raw, str(BUILDER), 'exec', dont_inherit=True), builder.__dict__)
    builder.ROOT = ROOT
    builder.HERE = HERE/'candidate'
    builder.main()


if __name__ == '__main__':
    main()
'''


def preflight_builder(builder_sha):
    text = source(P10/'prepare-preflight-p10.py', '90461a4a942efe29cb195d68d38c207da6a2bad6534e7dc0db4f9a05e681ae7b')
    text = substitute(text, [
        ('P10: the P8 preflight builder (277901e3) with fresh roots and the P10 preflight-main.go (make_p10.py).\n',
         'P10: the P8 preflight builder (277901e3) with fresh roots and the P10 preflight-main.go (make_p10.py).\n'
         'P11: the P10 builder over the P11 exact-source builder (Core f45a6262) and its signing root, fresh roots\n'
         'and the unchanged P10 preflight-main.go (ga-bebv-deploy/p11/make_p11.py).\n', 1),
        ("BUILDER = HERE.parent/'p8'/'prepare-compose-p8.py'", "BUILDER = HERE/'prepare-compose-p11.py'", 1),
        ("EXPECTED = '%s'" % BUILDER_P8, "EXPECTED = '%s'" % builder_sha, 1),
        ("PRIOR = Path('%s')" % SIGN_OLD, "PRIOR = Path('%s')" % SIGN_BUILD, 1),
        ("ROOT = Path('%s')" % PREFLIGHT_OLD, "ROOT = Path('%s')" % PREFLIGHT_BUILD, 1),
        ("STAGING = Path('%s')" % STAGING_OLD, "STAGING = Path('%s')" % STAGING, 1),
    ], 'prepare-preflight-p10.py')
    return write('prepare-preflight-p11.py', text)


def diagnostics():
    write('compose-main.go', source(P8/'compose-main.go', 'e8cb87a053b07ab8c8f93fd21a6a14c015b81919422ecdbec6c8c7a03201d8b3'))
    main_sha = write('candidate/compose-main.go',
                     source(P10/'compose-main.go', '5040c19623eddd137b48865e0406bfae2c57a2b7933780363c48fe124093f363'))
    builder_sha = compose_builder()
    write('prepare-compose-candidate-p11.py', CANDIDATE_BUILDER % dict(builder=builder_sha, root=CAND_BUILD, main=main_sha))
    write('preflight-main.go', source(P10/'preflight-main.go', 'cb55f252ec237f185ed6417a4a99143d0d3c606a8429befa413a869195200449'))
    preflight_builder(builder_sha)


# ---------------------------------------------------------------------------------------------------------------
# Chain

DERIVE_P10 = '''def derive(receipt, revision):
    """Pure: the receipt input for the M9 state, with every predecessor asserted."""
    draft = copy.deepcopy(receipt)
    for key in GENERATED:
        require(key in draft, 'generated field missing: ' + key)
        draft.pop(key)
    require(len(draft['profiles']) == 1, 'profile cardinality')
    profile = draft['profiles'][0]
    require('worker_profile_sha256' in profile, 'generated profile digest missing')
    profile.pop('worker_profile_sha256')
    require(draft['template_commit'] == TEMPLATE, 'template unchanged')
    heads = [h for h in draft['member_heads'] if h['name'] == 'template']
    require(len(heads) == 1 and heads[0]['commit'] == TEMPLATE, 'template member head unchanged')
    # A receipt profile is not composed configuration, so the running revision must be unchanged.
    require(draft['permission_revision'] == REVISION and revision == REVISION, 'revision unchanged')
    require(profile['provider']['version'] == VERSION, 'provider version unchanged')
    argv = profile['argv']
    positions = [i for i, token in enumerate(argv) if token == '--model']
    require(len(positions) == 1 and argv[positions[0] + 1] == MODEL, 'argv model unchanged')
    cores = [h for h in draft['member_heads'] if h['name'] == 'core']
    require(len(cores) == 1 and cores[0]['commit'] == CORE, 'core member head unchanged')
    # The one change: the typed candidate profile, on the signing lane's check path.
    require(profile['name'] == 'gascity/gc.implementation-worker' and profile['profile_kind'] == 'signing',
            'signing profile predecessor')
    require(profile['check_path'] == CANDIDATE['check_path'], 'candidate check path is the signing lane check')
    draft['profiles'].append(copy.deepcopy(CANDIDATE))
    return draft
'''
DERIVE_P11 = '''def derive(receipt, revision):
    """Pure: the receipt input for the M10 state, with every predecessor asserted."""
    draft = copy.deepcopy(receipt)
    for key in GENERATED:
        require(key in draft, 'generated field missing: ' + key)
        draft.pop(key)
    require(len(draft['profiles']) == 2, 'profile cardinality')
    for each in draft['profiles']:
        require('worker_profile_sha256' in each, 'generated profile digest missing')
        each.pop('worker_profile_sha256')
    profile, candidate = draft['profiles']
    require(profile['name'] == 'gascity/gc.implementation-worker' and profile['profile_kind'] == 'signing',
            'signing profile predecessor')
    require(candidate == CANDIDATE, 'candidate profile unchanged')
    require(draft['template_commit'] == TEMPLATE, 'template unchanged')
    heads = [h for h in draft['member_heads'] if h['name'] == 'template']
    require(len(heads) == 1 and heads[0]['commit'] == TEMPLATE, 'template member head unchanged')
    require(profile['provider']['version'] == VERSION, 'provider version unchanged')
    argv = profile['argv']
    positions = [i for i, token in enumerate(argv) if token == '--model']
    require(len(positions) == 1 and argv[positions[0] + 1] == MODEL, 'argv model unchanged')
    # The two changes. M10 installed the replace-mode city.toml, which moved the composed revision to the
    # exact value the controller traced on 2026-09-27; sequence 16 moved the Core member head.
    require(draft['permission_revision'] == REVISION_OLD and revision == REVISION, 'revision predecessor')
    draft['permission_revision'] = revision
    cores = [h for h in draft['member_heads'] if h['name'] == 'core']
    require(len(cores) == 1 and cores[0]['commit'] == CORE_OLD, 'core member head predecessor')
    cores[0]['commit'] = CORE
    return draft
'''


def input_script():
    text = source(P10/'p10-input.py', 'e3702537596c9deb9b7e76bda7162c346c9ee6e79f1a4b85ff92020ae75a29a0')
    header = '''"""P11 step 1: observe the running revision and derive the receipt input. Read-only except its own records.

ga-bebv S3, RECEIPT. Generated by make_p11.py from the executed P10 input; the logic is P10's. The installed
receipt c833908f minus its generated fields becomes the input draft. Exactly two leaves change: the permission
revision 83c41af6 -> 03f16ea2 (the M10 city.toml, traced live from the controller) and the Core member head
deefb98b -> f45a6262 (sequence 16). Both profiles, the Template cfd353f3, the signing provider version d4e57767
and the argv model claude-opus-5-5 are asserted unchanged, and both live wrappers must report their pinned
versions. `m10_acceptance()` verifies M10's reviewed records and that the live metadata pair is the accepted
M10 pair succeeding the M9 file 5a29dc59.

  python3 -I -S -B source-launch.py p11-input.py <own sha256>
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('%s')" % INPUT_OLD, "ROOT = Path('%s')" % INPUT_ROOT, 1),
        ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC, 1),
        ("CORE = '%s'" % CORE_OLD, "CORE_OLD = '%s'\nCORE = '%s'" % (CORE_OLD, CORE), 1),
        ("RECEIPT_OLD_SHA = '%s'" % RECEIPT_P10_OLD, "RECEIPT_OLD_SHA = '%s'" % RECEIPT_P10, 1),
        ("REVISION = '%s'" % REVISION_OLD, "REVISION_OLD = '%s'\nREVISION = '%s'" % (REVISION_OLD, REVISION), 1),
        ("M9_RELEASE = '%s'" % M9_RELEASE, "M9_RELEASE = '%s'" % M10_RELEASE, 1),
        ("PREVIOUS_MANIFEST_FILE = '%s'" % M8_FILE, "PREVIOUS_MANIFEST_FILE = '%s'" % M9_FILE, 1),
        (DERIVE_P10, DERIVE_P11, 1),
        ('M9', 'M10', 22),
        ('m9', 'm10', 10),
        ('P10', 'P11', 1),
        # After the renames: the succession link names M9's file, and M9 pinned the candidate wrapper.
        ("# The succession link is previous_metadata.manifest_sha256, the M8 canonical FILE digest.",
         "# The succession link is previous_metadata.manifest_sha256, the M9 canonical FILE digest.", 1),
        ("its provider is the M10-pinned wrapper", "its provider is the M9-pinned wrapper", 1),
    ], 'p10-input.py')
    # M9 stays named only in the two comments above (checked by test_p11.py).
    stale(text, 'p11-input.py', ('m9', 'M9_', 'p10', 'P10', 'e0t1.18-p1'))
    return write('p11-input.py', header + text)


def compose_script(input_sha):
    text = source(P10/'p10-observe-compose.py', '06c8d9f7f57cb1480d7b5a424af61e640bf6cc26a03b8f905724826e74efbb61')
    header = '''"""P11 step 2: one nonlaunching read-only composition observation of both profiles; no receipt installation.

ga-bebv S3, RECEIPT. Generated by make_p11.py from the executed P10 observer; the logic is P10's. In one read-only
namespace it runs the signing and the candidate composition diagnostics, both rebuilt from Core f45a6262, and each
observation must equal the draft profile of the same name: the argv, the environment and the revision. Also
changed: a fresh root, the P11 input, gc 207a78e2, the sequence 16 supervisor epoch, the M10 metadata pair and
the policy module path (the byte-identical M10 copy of metadata_closure.py).
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('%s')" % COMPOSE_OLD, "ROOT = Path('%s')" % COMPOSE_ROOT, 1),
        ("INPUT_SHA = 'e3702537596c9deb9b7e76bda7162c346c9ee6e79f1a4b85ff92020ae75a29a0'", "INPUT_SHA = '%s'" % input_sha, 1),
        ("BUILD = Path('%s')" % SIGN_OLD, "BUILD = Path('%s')" % SIGN_BUILD, 1),
        ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC, 1),
        ("POLICY = HERE.parent/'s3'/'metadata_closure.py'", "POLICY = HERE.parent/'m10'/'metadata_closure.py'", 1),
        ("BINARY_SHA = 'e123ee37c020b3c1aae703f2956f7b59a322fd4814cea7fe2e5a96dc6c920a76'", "BINARY_SHA = '%s'" % SIGN_COMPOSE_SHA, 1),
        ("CANDIDATE_BUILD = Path('%s')" % CAND_OLD, "CANDIDATE_BUILD = Path('%s')" % CAND_BUILD, 1),
        ("CANDIDATE_BINARY_SHA = '53450168ef90fd8698688d25fb031e96b3295ff54132441cda72c593611f3111'",
         "CANDIDATE_BINARY_SHA = '%s'" % CANDIDATE_COMPOSE_SHA, 1),
        ("host['core']['MainPID'] == '995924'", "host['core']['MainPID'] == '2800348'", 1),
        ("host['core']['ExecMainStartTimestampMonotonic'] == '163987392096'",
         "host['core']['ExecMainStartTimestampMonotonic'] == '229642910742'", 1),
        ("build['builder_sha256'] != '%s'" % BUILDER_P8, "build['builder_sha256'] != BUILDER_SHA", 1),
        ("LAUNCHER_SHA = '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'\n",
         "LAUNCHER_SHA = '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'\n"
         "BUILDER_SHA = '%s'  # prepare-compose-p11.py; both diagnostics record it\n"
         % sha((HERE/'prepare-compose-p11.py').read_bytes()), 1),
        ('M9', 'M10', 1),
        ('m9', 'm10', 4),
        ('p10', 'p11', 1),
    ], 'p10-observe-compose.py')
    stale(text, 'p11-observe-compose.py', ('m9', 'M9', 'p10', 'P10', 'e0t1.18-p1', "'s3'"))
    return write('p11-observe-compose.py', header + text)


def readiness_script(compose_sha):
    text = source(P10/'p10-readiness.py', 'fa4b69f1333380c6727f95ebc8478130338a92c471308c7b49855deee8f1513e')
    header = '''"""P11 step 3: one native receipt-compatibility/readiness observation of both profiles; no worker or install.

ga-bebv S3, RECEIPT. Generated by make_p11.py from the executed P10 readiness; the logic is P10's. The normalized
and finalized receipt carries both profiles with the two moved leaves. The P11 preflight diagnostic, rebuilt from
Core f45a6262, runs Core's own start preflight and its exact-profile negative for both profiles against their
compositions. Also changed: a fresh root, the P11 observer and compositions, and the P11 preflight build and
builder.
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT=Path('%s')" % READY_OLD, "ROOT=Path('%s')" % READY_ROOT, 1),
        ("BUILD=Path('%s')" % PREFLIGHT_OLD, "BUILD=Path('%s')" % PREFLIGHT_BUILD, 1),
        ("BASE_SHA='06c8d9f7f57cb1480d7b5a424af61e640bf6cc26a03b8f905724826e74efbb61'", "BASE_SHA='%s'" % compose_sha, 1),
        ("BINARY_SHA='c6dd9ebbee33bc40579fc9b7f0af7e7a9c69500566870910f5361eb4b0e12824'", "BINARY_SHA='%s'" % PREFLIGHT_SHA, 1),
        ("COMPOSITION=Path('%s/composition.json')" % COMPOSE_OLD, "COMPOSITION=Path('%s/composition.json')" % COMPOSE_ROOT, 1),
        ("CANDIDATE_COMPOSITION=Path('%s/composition-candidate.json')" % COMPOSE_OLD,
         "CANDIDATE_COMPOSITION=Path('%s/composition-candidate.json')" % COMPOSE_ROOT, 1),
        ("    base.read(SUCCESSOR/'prepare-preflight-p10.py','90461a4a942efe29cb195d68d38c207da6a2bad6534e7dc0db4f9a05e681ae7b')\n",
         "    base.read(SUCCESSOR/'prepare-preflight-p11.py','%s')\n" % sha((HERE/'prepare-preflight-p11.py').read_bytes()), 1),
        ("    base.read(BUILD/'extraction.json','a30af30748f8c498a72a0edb1fa4837c677839943eedb9486ea6c046934f4941')\n",
         "    base.read(BUILD/'extraction.json','%s')\n" % EXTRACTION_SHA, 1),
        ("BASE=HERE/'p10-observe-compose.py'", "BASE=HERE/'p11-observe-compose.py'", 1),
        ('# The P10 compositions are accepted', '# The P11 compositions are accepted', 1),
    ], 'p10-readiness.py')
    stale(text, 'p11-readiness.py', ('m9', 'M9', 'p10', 'P10', 'e0t1.18-p1'))
    return write('p11-readiness.py', header + text)


def adopt_script(readiness_sha):
    text = source(P10/'p10-adopt.py', '36404fd1574fb0eb477ba54b5ed1168ac1541833a926d7be62369b12a03b496d')
    header = '''"""P11 step 4: one receipt-only transaction through the unchanged reviewed provisioner.

ga-bebv S3, RECEIPT. Generated by make_p11.py from the executed P10 adoption; the logic is P10's. These bindings
change: the P11 readiness, the old receipt c833908f, the M10 accepted-deployment evidence and platform self
digests in the typed-support witness, the Core consumer (gc 207a78e2 from f45a6262, tree f1011ada), the sequence
16 build verification and the traced controller 2800348. The readiness-derived constants stay None until
readiness has passed.
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("NEW_SHA='c833908fe89ab180e57ef7164d687f01ae2052f8667360f04b73c5423902f0a4'\n"
         "NEW_SELF='6bb7ca5bf9dc84cc5e51c419f6a3d698a278cf817c7d87ef81429a9f05f52dd0'\n"
         "READY_RESULT_SHA='ebccc14524d7aee8d4002b27f929f05212a7aec429ea6a9a87de3dcfb5af83c7'\n"
         "READY_BEFORE_SHA='6dedcfa268838cb517707d8c055cb363c323653a3ef0bf1c667e840a412928ce'\n"
         "READY_PINS_SHA='82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n",
         "NEW_SHA=None\nNEW_SELF=None\nREADY_RESULT_SHA=None\nREADY_BEFORE_SHA=None\nREADY_PINS_SHA=None\n", 1),
        ("ROOT=Path('%s')" % ADOPT_OLD, "ROOT=Path('%s')" % ADOPT_ROOT, 1),
        ("READY=Path('%s')" % READY_OLD, "READY=Path('%s')" % READY_ROOT, 1),
        ("READY_SOURCE=HERE/'p10-readiness.py'", "READY_SOURCE=HERE/'p11-readiness.py'", 1),
        ("READY_SHA='fa4b69f1333380c6727f95ebc8478130338a92c471308c7b49855deee8f1513e'", "READY_SHA='%s'" % readiness_sha, 1),
        ("OLD_SHA='%s'" % RECEIPT_P10_OLD, "OLD_SHA='%s'" % RECEIPT_P10, 1),
        ("CORE='%s'" % CORE_OLD, "CORE='%s'" % CORE, 1),
        (BUILD_EVIDENCE_OLD, BUILD_EVIDENCE, 1),
        ("commit=CORE,tree='%s')" % TREE_OLD, "commit=CORE,tree='%s')" % TREE, 1),
        ("latest['controller_pid']==995924", "latest['controller_pid']==2800348", 1),
        ("# Filled from the passed P10 readiness evidence", "# Filled from the passed P11 readiness evidence", 1),
        ('m9', 'm10', 6),
    ], 'p10-adopt.py')
    stale(text, 'p11-adopt.py', ('m9', 'M9', 'p10', 'P10', 'e0t1.18-p1', '995924', CORE_OLD, TREE_OLD))
    return write('p11-adopt.py', header + text)


def scripts():
    if None in (SIGN_COMPOSE_SHA, CANDIDATE_COMPOSE_SHA, PREFLIGHT_SHA, EXTRACTION_SHA):
        raise SystemExit('build the diagnostics and pin their digests first')
    input_sha = input_script()
    compose_sha = compose_script(input_sha)
    readiness_sha = readiness_script(compose_sha)
    adopt_script(readiness_sha)
    write('source-launch.py', source(P10/'source-launch.py', '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'))
    write('typed-interoperability.json',
          source(P10/'typed-interoperability.json', '315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563'))


if __name__ == '__main__':
    if sys.argv[1:] == ['diagnostics']:
        diagnostics()
    elif sys.argv[1:] == ['scripts']:
        scripts()
    else:
        raise SystemExit(__doc__)
