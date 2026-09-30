"""Generate the ga-e0t1.15 S3 part 2 (P7) package from reviewed sources by count-checked substitutions.

  python3 -I -B make_p7.py builders      phase 1: the two diagnostic builders, rebound to Core 9faeabc2
  python3 -I -B make_p7.py scripts       phase 2: the four P7 scripts, rebound from the executed P6 chain

Every source is loaded by its reviewed digest. Every substitution names the exact text it replaces and
how many times it must occur, and generation refuses on any other count. Generated files are written
beside this generator; reviewers compare each against its source through the substitution list only.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
STAGE = Path('/home/loucmane/.local/share/gas-city-staging/ga-mutg-20260920/ga-ecwh-provisioning-successor-20260920')
P6 = HERE.parent.parent/'gct-m1wh-p6'
CORE_OLD, CORE_NEW = '796d9a7a67c42294fdc467c107bb59b76e482301', '9faeabc2892d8c7133111e13ad55af66790a2ac6'
TREE_OLD, TREE_NEW = 'f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13', 'c9f19d215d271a5dda0bce296dc72c32dfc35499'
COMPOSE_ROOT = '/var/tmp/ga-e0t1.15-compose-diagnostic-20260925'
PREFLIGHT_ROOT = '/var/tmp/ga-e0t1.15-preflight-diagnostic-20260925'


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
    data = text.encode() if isinstance(text, str) else text
    path.write_bytes(data)
    path.chmod(0o644)
    print(name, sha(data))
    return sha(data)


def builders():
    compose = source(STAGE/'prepare-compose.py', '4d8a1586993e44b82c134075dd8f6cf79ea5d178555471e6086bdc3f9474223b')
    compose = substitute(compose, [
        ("ROOT = Path('/var/tmp/ga-ecwh-compose-diagnostic-20260920-r2')", "ROOT = Path('%s')" % COMPOSE_ROOT, 1),
        # The S1 reproduction clone of the build source 9faeabc2 (tree c9f19d21), not a live repository.
        ("CORE = Path('/home/loucmane/gascity-core-worktrees/ga-ecwh-typed-worker-receipts')",
         "CORE = Path('/var/tmp/ga-e0t1.15-build-20260925/repro-source')", 1),
        ("COMMIT = '%s'" % CORE_OLD, "COMMIT = '%s'" % CORE_NEW, 1),
        ("if core_tree != '%s':" % TREE_OLD, "if core_tree != '%s':" % TREE_NEW, 1),
    ], 'prepare-compose.py')
    compose_sha = write('prepare-compose-p7.py', compose)
    preflight = source(STAGE/'prepare-preflight.py', '47cfa684dd6d0d6b021edf7f01d6f80f5c700073a59ea63426e1a66d28c5926d')
    preflight = substitute(preflight, [
        ("BUILDER = HERE/'prepare-compose.py'", "BUILDER = HERE/'prepare-compose-p7.py'", 1),
        ("EXPECTED = '4d8a1586993e44b82c134075dd8f6cf79ea5d178555471e6086bdc3f9474223b'", "EXPECTED = '%s'" % compose_sha, 1),
        ("PRIOR = Path('/var/tmp/ga-ecwh-compose-diagnostic-20260920-r2')", "PRIOR = Path('%s')" % COMPOSE_ROOT, 1),
        ("ROOT = Path('/var/tmp/ga-ecwh-preflight-diagnostic-20260920-r1')", "ROOT = Path('%s')" % PREFLIGHT_ROOT, 1),
        # Generated sources go outside the package, so the package worktree stays clean.
        ("STAGING = HERE/'preflight-generated-r1'", "STAGING = Path('/var/tmp/ga-e0t1.15-preflight-generated-20260925')", 1),
    ], 'prepare-preflight.py')
    write('prepare-preflight-p7.py', preflight)
    write('compose-main.go', source(STAGE/'compose-main.go', 'e8cb87a053b07ab8c8f93fd21a6a14c015b81919422ecdbec6c8c7a03201d8b3'))
    write('preflight-main.go', source(STAGE/'preflight-main.go', '75c897e0874404c8d2fded9302ffbfb799ba983678d5503f44041a7d8508e7c6'))


GC_OLD, GC_NEW = ('69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9',
                  'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489')
RECEIPT_P6, RECEIPT_NOW = ('01ed1bce0b99d5c6043804cdacb2b25bc725bffb00dba3450888284e570d0a8a',
                           '0b30c23f4484382fd4918f394599268f4f4005ac71118e8a7f82ca72eb9615ff')
TEMPLATE_M5, TEMPLATE_NEW = '28539934fa742056e0a65710d5638ff559a21175', 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
REVISION_NOW = 'd6ca85cd96c7aab4ea0b6a7954d2d74e5e6bb211cde0bb820f3b6f815023bd88'
VERSION_M5 = 'f36deb20efa5cc11781f1d9703b8e5e0d7897c6357260dff1045bcd86489ff34'
VERSION_NEW = 'd4e57767d03accd708ce8876580096bb17bce023d6dc6e664fffee4367ea3c57'
M6_RELEASE = 'template-pr71-core-seq14-metadata-m6-20260925'
M5_MANIFEST_FILE = '2d7eadce62c4e567697813cc9122414f1e94c3bd9d389aef92015adef7f36319'
INPUT_ROOT = '/var/tmp/ga-e0t1.15-p7-input-20260925'
P7_COMPOSE_ROOT = '/var/tmp/ga-e0t1.15-p7-compose-20260925'
READY_ROOT = '/var/tmp/ga-e0t1.15-p7-readiness-20260925'
ADOPT_ROOT = '/var/tmp/ga-e0t1.15-p7-adoption-20260925'
# Epoch of the S2 host (boot 3f1f4534): supervisor, signer and broker service identities.
EPOCH = (("'f4e38c6a-bfc9-4532-a713-0497904c5b1a'", "'3f1f4534-ea17-4cb4-b2f2-a3f8bce1a8fa'"),
         ("host['core']['MainPID'] == '3150812'", "host['core']['MainPID'] == '2940569'"),
         ("== '84619011818'", "== '123479699122'"),
         ("host['signer']['MainPID'] == '5550'", "host['signer']['MainPID'] == '2310'"),
         ("== '208267863'", "== '39660502'"),
         ("host['broker']['MainPID'] == '2862577'", "host['broker']['MainPID'] == '2940285'"),
         ("== '77125780270'", "== '123477220085'"))
POLICY_SHA = '4fa0698bc400ccc37fe9a5ac6545f114c0d4f4817ebdd41733abbf1e63bd924c'  # s3/metadata_closure.py


def docstring(text, new):
    """Replace the module docstring (from the first line to its closing quotes) with new text."""
    end = text.index('"""\n', 3) + 4
    return new + text[end:]


def input_script():
    text = source(P6/'p6-input.py', 'f0150b631196dec051dad05f40803deccad8e480ed0a638e86e61ea0db962c1c')
    header = ('''"""P7 step 1: observe the running revision and derive the receipt input. Read-only except its own records.

ga-e0t1.15 S3 part 2. Generated by make_p7.py from the executed P6 input (f0150b63); the logic is P6's.
The native cycle trace is read (`gc trace show`, a supported read). The live signing worker's `--version`
proves the dependency version it will report. The installed receipt 0b30c23f minus its three generated
fields becomes the input draft. Only these fields change, and each requires its exact predecessor:

- template_commit and member_heads[template]: 28539934 -> cfd353f3 (PR 70 and PR 71);
- member_heads[core]: 796d9a7a -> 9faeabc2, the sequence 14 build source;
- permission_revision: the traced running revision, which must differ from d6ca85cd (the new Core's
  embedded core pack changes the composed revision);
- profiles[0].provider.version: f36deb20 -> d4e57767 (the PR 71 signing-worker parser).
The argv is unchanged; its model claude-opus-5-5 is asserted.

`m6_acceptance()` verifies M6's own reviewed records at run time: a COMMIT_PASS review record with two
distinct provenance files, the committed acceptance it binds, restoration, the M6 release manifest naming
Template cfd353f3 and succeeding the M5 file 2d7eadce, and the live metadata pair byte-identical to the
accepted pair.

  python3 -I -S -B source-launch.py p7-input.py <own sha256>
"""
''')
    # Substitutions apply to the reviewed body only; the new docstring is prepended afterwards.
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('/var/tmp/gct-m1wh-p6-input-20260923-r2')", "ROOT = Path('%s')" % INPUT_ROOT, 1),
        ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC_NEW, 1),
        ("CORE = '%s'" % CORE_OLD, "CORE = '%s'" % CORE_NEW, 1),
        ("RECEIPT_OLD_SHA = '%s'" % RECEIPT_P6, "RECEIPT_OLD_SHA = '%s'" % RECEIPT_NOW, 1),
        ("TEMPLATE_OLD, TEMPLATE_NEW = 'ff683ed6506bdbc38f21f66a1a7f3ce31bdcaa7c', '%s'" % TEMPLATE_M5,
         "TEMPLATE_OLD, TEMPLATE_NEW = '%s', '%s'" % (TEMPLATE_M5, TEMPLATE_NEW), 1),
        ("REVISION_OLD = 'ebeefe97a230678b812b164096ec7fccf1c1f2516d8c96ef546c92bcd645acc1'",
         "REVISION_OLD = '%s'" % REVISION_NOW, 1),
        (VERSION_M5, VERSION_NEW, 1),
        ('b7fee4467e83c7c9d07c2c421142f20297ad1cd3de93192713400aa01d8714b0', VERSION_M5, 1),
        ("MODEL_OLD, MODEL_NEW = 'claude-opus-5', 'claude-opus-5-5'",
         "MODEL = 'claude-opus-5-5'\nCORE_OLD = '%s'" % CORE_OLD, 1),
        ("'template-pr69-opus55-metadata-m5-20260923'", "'%s'" % M6_RELEASE, 1),
        ("('template-pr69-authority', '/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority',",
         "('template-pr71-authority', '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority',", 1),
        ("R9_MANIFEST_FILE = 'a6324753cb238f8de5ed3af72eef9e3a425ab491dae62778f462849814eb1852'",
         "R9_MANIFEST_FILE = '%s'" % M5_MANIFEST_FILE, 1),
        ("    require(len(positions) == 1 and argv[positions[0] + 1] == MODEL_OLD, 'argv model predecessor')\n"
         "    argv[positions[0] + 1] = MODEL_NEW\n"
         "    require(MODEL_OLD not in argv, 'stale model token')\n",
         "    require(len(positions) == 1 and argv[positions[0] + 1] == MODEL, 'argv model unchanged')\n"
         "    cores = [h for h in draft['member_heads'] if h['name'] == 'core']\n"
         "    require(len(cores) == 1 and cores[0]['commit'] == CORE_OLD, 'core member head predecessor')\n"
         "    cores[0]['commit'] = CORE\n", 1),
        ('R9_MANIFEST_FILE', 'PREVIOUS_MANIFEST_FILE', 2),
        ('M5', 'M6', 22),
        ('m5', 'm6', 10),
        ('For later P6 steps', 'For later P7 steps', 1),
        # After the renames, so the predecessor stays named M5.
        ("the R9 canonical FILE digest.", "the M5 canonical FILE digest.", 1),
    ], 'p6-input.py')
    return write('p7-input.py', header + text)


def compose_script(input_sha, builder_sha, binary_sha):
    text = source(P6/'p6-observe-compose.py', '43b94ce677dcaa80b6937f7205362063da151f0608a99874b18b692ab8f2c8d6')
    header = ('''"""P7 step 2: one nonlaunching read-only composition observation; no receipt installation.

ga-e0t1.15 S3 part 2. Generated by make_p7.py from the executed P6 observer (43b94ce6); the logic is P6's.
Host identity is observed outside bwrap. Inside, the real filesystem is mounted read-only with fresh proc
and dev and no network. No writable production bind exists. Only these bindings change:
- a fresh root;
- the draft proven by the P7 input derivation;
- the composition diagnostic rebuilt at Core 9faeabc2 (tree c9f19d21) by the P7 builder, because the new
  Core's embedded core pack changes the composed permission revision;
- the installed gc b2760ea4, the S2 host epoch (boot 3f1f4534), and the M6 metadata pair;
- the S3 access-time neutral policy (operator decision 2026-09-25), installed on every observer load from
  the reviewed M6 closure module, so before and after snapshots compare everything except atime.
"""
''')
    # Substitutions apply to the reviewed body only; the new docstring is prepended afterwards.
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('/var/tmp/gct-m1wh-p6-compose-20260923-r2')", "ROOT = Path('%s')" % P7_COMPOSE_ROOT, 1),
        ("INPUT_SOURCE = HERE/'p6-input.py'", "INPUT_SOURCE = HERE/'p7-input.py'", 1),
        ("INPUT_SHA = 'f0150b631196dec051dad05f40803deccad8e480ed0a638e86e61ea0db962c1c'",
         "INPUT_SHA = '%s'" % input_sha, 1),
        ("BUILD = Path('/var/tmp/ga-ecwh-compose-diagnostic-20260920-r2')", "BUILD = Path('%s')" % COMPOSE_ROOT, 1),
        ("GC_SHA = '%s'\n" % GC_OLD,
         "GC_SHA = '%s'\nPOLICY = HERE.parent/'s3'/'metadata_closure.py'\nPOLICY_SHA = '%s'\nOLD_IMAGE = '%s'\n"
         % (GC_NEW, POLICY_SHA, GC_OLD), 1),
        ("BINARY_SHA = '9f837c831919cd440089ac2207c6e32ca005709b51a72e430a48f76006f2edd3'",
         "BINARY_SHA = '%s'" % binary_sha, 1),
        ("    value.GC_SHA = GC_SHA  # exact installed successor, no change to observer logic\n    return value\n",
         "    value.GC_SHA = GC_SHA  # exact installed successor, no change to observer logic\n"
         "    module(POLICY, POLICY_SHA).install_policy(value, types.SimpleNamespace(), OLD_IMAGE)\n"
         "    return value\n", 1),
        *[(old, new, 1) for old, new in EPOCH],
        ("build['builder_sha256'] != '4d8a1586993e44b82c134075dd8f6cf79ea5d178555471e6086bdc3f9474223b'",
         "build['builder_sha256'] != '%s'" % builder_sha, 1),
        ('M5', 'M6', 1),
        ('m5', 'm6', 4),
    ], 'p6-observe-compose.py')
    return write('p7-observe-compose.py', header + text)


def readiness_script(compose_sha, preflight_builder_sha, binary_sha, extraction_sha):
    text = source(P6/'p6-readiness.py', '7b28b3e551e86818a2cdda3e53ed90c7072781e0a9354bd1ebf5d9425d579133')
    header = ('''"""P7 step 3: one native receipt-compatibility/readiness observation; no worker or install.

ga-e0t1.15 S3 part 2. Generated by make_p7.py from the executed P6 readiness (7b28b3e5); the logic is P6's.
Provider version/auth executables and one managed signer --probe may run. There is no inference, signature,
route, resume, or credential refresh. Only these bindings change: the P7 observer and composition, and the
preflight diagnostic rebuilt at Core 9faeabc2 by the P7 builders. The 2.1.280 CLI 1e08503d, the provisioner
64425a72 and the canary runner 3beeedb2 are unchanged.
"""
''')
    # Substitutions apply to the reviewed body only; the new docstring is prepended afterwards.
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT=Path('/var/tmp/gct-m1wh-p6-readiness-20260923-r2')", "ROOT=Path('%s')" % READY_ROOT, 1),
        ("BUILD=Path('/var/tmp/ga-ecwh-preflight-diagnostic-20260920-r1')", "BUILD=Path('%s')" % PREFLIGHT_ROOT, 1),
        ("BASE=HERE/'p6-observe-compose.py'", "BASE=HERE/'p7-observe-compose.py'", 1),
        ("BASE_SHA='43b94ce677dcaa80b6937f7205362063da151f0608a99874b18b692ab8f2c8d6'", "BASE_SHA='%s'" % compose_sha, 1),
        ("SUCCESSOR=Path('/home/loucmane/.local/share/gas-city-staging/ga-mutg-20260920/"
         "ga-ecwh-provisioning-successor-20260920')", "SUCCESSOR=HERE", 1),
        ("BINARY_SHA='edbc0fa11d3ebae15f678179725203d9da3434ec0cf8883c536398d5f97426bf'", "BINARY_SHA='%s'" % binary_sha, 1),
        ("COMPOSITION=Path('/var/tmp/gct-m1wh-p6-compose-20260923-r2/composition.json')",
         "COMPOSITION=Path('%s/composition.json')" % P7_COMPOSE_ROOT, 1),
        ("base.read(SUCCESSOR/'prepare-preflight.py','47cfa684dd6d0d6b021edf7f01d6f80f5c700073a59ea63426e1a66d28c5926d')",
         "base.read(SUCCESSOR/'prepare-preflight-p7.py','%s')" % preflight_builder_sha, 1),
        ("'4dc42f8bcfb6efbe9150ef4beaa3c0e0ada0cf9d0ad1d4cb57ee29920af5ff45'", "'%s'" % extraction_sha, 1),
        ('# The P6 composition', '# The P7 composition', 1),
    ], 'p6-readiness.py')
    return write('p7-readiness.py', header + text)


def adopt_script(readiness_sha, evidence_sha):
    text = source(P6/'p6-adopt.py', '64879d2a4f8109750323da3d91af6d46667d4ea6eccbfd0086e453ccc521c399')
    header = ('''"""P7 step 4: one receipt-only transaction through the unchanged reviewed provisioner.

ga-e0t1.15 S3 part 2. Generated by make_p7.py from the executed P6 adoption (64879d2a); the logic is P6's.
No worker, inference, signing, reload, service transition or root operation. Readiness is reused only while
its input closure still matches. Every live phase uses the existing owned-group runner and a read-only
filesystem except the existing provisioning directory; its runner subdirectory stays read-only. Only these
bindings change: the P7 readiness, the old receipt 0b30c23f, the Core consumer (gc b2760ea4, commit 9faeabc2,
tree c9f19d21), the S1 reviewed-build evidence of b2760ea4, the running supervisor 2940569, and the M6
accepted-deployment evidence and platform self digests. The readiness-derived constants stay None until
readiness has passed; they are filled before the two adoption reviews, and the script refuses until then.
"""
''')
    # Substitutions apply to the reviewed body only; the new docstring is prepended afterwards.
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT=Path('/var/tmp/gct-m1wh-p6-adoption-20260923-r2')", "ROOT=Path('%s')" % ADOPT_ROOT, 1),
        ("READY=Path('/var/tmp/gct-m1wh-p6-readiness-20260923-r2')", "READY=Path('%s')" % READY_ROOT, 1),
        ("READY_SOURCE=HERE/'p6-readiness.py'", "READY_SOURCE=HERE/'p7-readiness.py'", 1),
        ("READY_SHA='7b28b3e551e86818a2cdda3e53ed90c7072781e0a9354bd1ebf5d9425d579133'", "READY_SHA='%s'" % readiness_sha, 1),
        ("OLD_SHA='%s'" % RECEIPT_P6, "OLD_SHA='%s'" % RECEIPT_NOW, 1),
        ("# Filled from the passed -r2 readiness evidence before the adoption reviews. The -r1 evidence\n"
         "# (12:06Z) went stale when a coordinator gc Bead note touched the pack cache repo at 12:10:54Z.\n"
         "NEW_SHA='0b30c23f4484382fd4918f394599268f4f4005ac71118e8a7f82ca72eb9615ff'\n"
         "NEW_SELF='c635e8ee0547ebc8c4caec6577d65103b9d17436ff17a18f66687f0ea3f1957f'\n"
         "READY_RESULT_SHA='a6cac0b99822e8432fa8b01b2a0c87bb212ff141c165d13d4921b2b75f8c8ee7'\n"
         "READY_BEFORE_SHA='c668ed0fbf17111d337dafdda113963a4ed66bb439ef9fbbf2aefa940610bf70'\n"
         "READY_PINS_SHA='a5f7f8c11a95b48d01f910c5c4668828d61a587a5942545f27d403ebadfeac8f'\n",
         "# Filled from the passed P7 readiness evidence before the adoption reviews.\n"
         "NEW_SHA=None\nNEW_SELF=None\nREADY_RESULT_SHA=None\nREADY_BEFORE_SHA=None\nREADY_PINS_SHA=None\n", 1),
        ("CORE='%s'" % CORE_OLD, "CORE='%s'" % CORE_NEW, 1),
        ("('reviewed-build','/var/tmp/ga-mutg-custody-build-20260920/artifact-verification.json',"
         "'fd1317440274f995aa52bebea565bba511912fdcb7a36b52b67105a673ee23ee')",
         "('reviewed-build','/var/tmp/ga-e0t1.15-build-20260925/artifact-verification.json','%s')" % evidence_sha, 1),
        ("tree='%s'" % TREE_OLD, "tree='%s'" % TREE_NEW, 1),
        ("latest['controller_pid']==3150812", "latest['controller_pid']==2940569", 1),
        ('m5', 'm6', 6),
    ], 'p6-adopt.py')
    return write('p7-adopt.py', header + text)


def build_record(root, builder_sha):
    import json
    record = json.loads(Path(root, 'build-result.json').read_bytes())
    if record['builder_sha256'] != builder_sha or sha(Path(root, 'compose').read_bytes()) != record['binary_sha256']:
        raise SystemExit('build record does not bind the reviewed builder and its binary: ' + root)
    return record


def scripts():
    compose_builder = sha((HERE/'prepare-compose-p7.py').read_bytes())
    preflight_builder = sha((HERE/'prepare-preflight-p7.py').read_bytes())
    compose_build = build_record(COMPOSE_ROOT, compose_builder)
    preflight_build = build_record(PREFLIGHT_ROOT, compose_builder)
    if compose_build['core_commit'] != CORE_NEW or compose_build['core_tree'] != TREE_NEW:
        raise SystemExit('compose build is not Core 9faeabc2')
    extraction = sha(Path(PREFLIGHT_ROOT, 'extraction.json').read_bytes())
    input_sha = input_script()
    compose_sha = compose_script(input_sha, compose_builder, compose_build['binary_sha256'])
    readiness_sha = readiness_script(compose_sha, preflight_builder, preflight_build['binary_sha256'], extraction)
    evidence = sha(Path('/var/tmp/ga-e0t1.15-build-20260925/artifact-verification.json').read_bytes())
    adopt_script(readiness_sha, evidence)
    write('source-launch.py', source(P6/'source-launch.py', '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'))
    write('typed-interoperability.json',
          source(P6/'typed-interoperability.json', '315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563'))


if __name__ == '__main__':
    if sys.argv[1:] == ['builders']:
        builders()
    elif sys.argv[1:] == ['scripts']:
        scripts()
    else:
        raise SystemExit(__doc__)
