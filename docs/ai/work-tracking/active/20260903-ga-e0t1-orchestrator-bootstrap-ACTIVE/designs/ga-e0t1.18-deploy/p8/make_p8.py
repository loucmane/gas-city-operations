"""Generate the ga-e0t1.18 S3 part 2 (P8) package from the executed P7 chain by count-checked substitutions.

  python3 -I -B make_p8.py builders      phase 1: the two diagnostic builders, rebound to Core deefb98b
  python3 -I -B make_p8.py scripts       phase 2: the four P8 scripts, rebound from the executed P7 chain

Every source is loaded by its reviewed digest. Every substitution names the exact text it replaces and how
many times it must occur, and generation refuses on any other count. Generated files are written beside this
generator; reviewers compare each against its source through the substitution list only.

P8 changes one receipt leaf: member_heads[core] 9faeabc2 -> deefb98b. The Template (cfd353f3), the provider
version (d4e57767), the model and the permission revision (2113693e: S1's provenance shows no embedded pack
path changed between 9faeabc2 and deefb98b) are asserted unchanged.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
P7 = HERE.parent.parent/'ga-e0t1.15-deploy/p7'
CORE_OLD, CORE_NEW = '9faeabc2892d8c7133111e13ad55af66790a2ac6', 'deefb98b2aed07875df31351d081fbac195cb1cd'
TREE_OLD, TREE_NEW = 'c9f19d215d271a5dda0bce296dc72c32dfc35499', 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'
COMPOSE_OLD, COMPOSE_ROOT = '/var/tmp/ga-e0t1.15-compose-diagnostic-20260925', '/var/tmp/ga-e0t1.18-compose-diagnostic-20260926'
PREFLIGHT_OLD, PREFLIGHT_ROOT = ('/var/tmp/ga-e0t1.15-preflight-diagnostic-20260925',
                                 '/var/tmp/ga-e0t1.18-preflight-diagnostic-20260926')
GENERATED_OLD, GENERATED_NEW = ('/var/tmp/ga-e0t1.15-preflight-generated-20260925',
                                '/var/tmp/ga-e0t1.18-preflight-generated-20260926')
REPRO_OLD, REPRO_NEW = '/var/tmp/ga-e0t1.15-build-20260925/repro-source', '/var/tmp/ga-e0t1.18-build-20260926/repro-source'


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
    compose = source(P7/'prepare-compose-p7.py', '4fda9c3425a474075b48cffc1b32c7db8e710e4b45a769c2be46a29893686052')
    compose = substitute(compose, [
        ("ROOT = Path('%s')" % COMPOSE_OLD, "ROOT = Path('%s')" % COMPOSE_ROOT, 1),
        # The S1 reproduction clone of the build source deefb98b (tree af5c3f04), not a live repository.
        ("CORE = Path('%s')" % REPRO_OLD, "CORE = Path('%s')" % REPRO_NEW, 1),
        ("COMMIT = '%s'" % CORE_OLD, "COMMIT = '%s'" % CORE_NEW, 1),
        ("if core_tree != '%s':" % TREE_OLD, "if core_tree != '%s':" % TREE_NEW, 1),
    ], 'prepare-compose-p7.py')
    compose_sha = write('prepare-compose-p8.py', compose)
    preflight = source(P7/'prepare-preflight-p7.py', 'aa0bf8fd4c559e54a0b53fe1c9e2bac2e0ee41d0459decb0b9f00466f9a91179')
    preflight = substitute(preflight, [
        ("BUILDER = HERE/'prepare-compose-p7.py'", "BUILDER = HERE/'prepare-compose-p8.py'", 1),
        ("EXPECTED = '4fda9c3425a474075b48cffc1b32c7db8e710e4b45a769c2be46a29893686052'", "EXPECTED = '%s'" % compose_sha, 1),
        ("PRIOR = Path('%s')" % COMPOSE_OLD, "PRIOR = Path('%s')" % COMPOSE_ROOT, 1),
        ("ROOT = Path('%s')" % PREFLIGHT_OLD, "ROOT = Path('%s')" % PREFLIGHT_ROOT, 1),
        ("STAGING = Path('%s')" % GENERATED_OLD, "STAGING = Path('%s')" % GENERATED_NEW, 1),
    ], 'prepare-preflight-p7.py')
    write('prepare-preflight-p8.py', preflight)
    write('compose-main.go', source(P7/'compose-main.go', 'e8cb87a053b07ab8c8f93fd21a6a14c015b81919422ecdbec6c8c7a03201d8b3'))
    write('preflight-main.go', source(P7/'preflight-main.go', '75c897e0874404c8d2fded9302ffbfb799ba983678d5503f44041a7d8508e7c6'))


GC_OLD, GC_NEW = ('b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489',
                  'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b')
RECEIPT_P6, RECEIPT_NOW = ('0b30c23f4484382fd4918f394599268f4f4005ac71118e8a7f82ca72eb9615ff',
                           '7cf59ab9e5a43fd7bca97028e7faaa2b2f9bfb927a663b4588c66e846e4e425d')
TEMPLATE = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
REVISION = '2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2'  # the live receipt 7cf59ab9
M7_RELEASE = 'template-pr71-core-seq15-metadata-m7-20260926'
M6_RELEASE = 'template-pr71-core-seq14-metadata-m6-20260925'
M6_MANIFEST_FILE = '7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb'
M5_MANIFEST_FILE = '2d7eadce62c4e567697813cc9122414f1e94c3bd9d389aef92015adef7f36319'
INPUT_ROOT = '/var/tmp/ga-e0t1.18-p8-input-20260926'
P8_COMPOSE_ROOT = '/var/tmp/ga-e0t1.18-p8-compose-20260926'
READY_ROOT = '/var/tmp/ga-e0t1.18-p8-readiness-20260926'
ADOPT_ROOT = '/var/tmp/ga-e0t1.18-p8-adoption-20260926'
# Sequence 15 moved only the supervisor; the boot, signer and broker are unchanged.
EPOCH = (("host['core']['MainPID'] == '2940569'", "host['core']['MainPID'] == '995924'"),
         ("== '123479699122'", "== '163987392096'"))
POLICY_OLD = '4fa0698bc400ccc37fe9a5ac6545f114c0d4f4817ebdd41733abbf1e63bd924c'
POLICY_SHA = 'ce310593418e30b89f08645824c6cdd5b700fcff60b12f688fffc3d42d31d5d8'  # s3/metadata_closure.py (M7)


def docstring(text, new):
    """Replace the module docstring (from the first line to its closing quotes) with new text."""
    end = text.index('"""\n', 3) + 4
    return new + text[end:]


DERIVE_P7 = (
    "    require(draft['template_commit'] == TEMPLATE_OLD, 'template predecessor')\n"
    "    draft['template_commit'] = TEMPLATE_NEW\n"
    "    heads = [h for h in draft['member_heads'] if h['name'] == 'template']\n"
    "    require(len(heads) == 1 and heads[0]['commit'] == TEMPLATE_OLD, 'template member head predecessor')\n"
    "    heads[0]['commit'] = TEMPLATE_NEW\n"
    "    require(draft['permission_revision'] == REVISION_OLD and revision != REVISION_OLD\n"
    "            and len(revision) == 64 and all(c in '0123456789abcdef' for c in revision), 'revision predecessor')\n"
    "    draft['permission_revision'] = revision\n"
    "    require(profile['provider']['version'] == VERSION_OLD, 'provider version predecessor')\n"
    "    profile['provider']['version'] = VERSION_NEW\n")
DERIVE_P8 = (
    "    require(draft['template_commit'] == TEMPLATE, 'template unchanged')\n"
    "    heads = [h for h in draft['member_heads'] if h['name'] == 'template']\n"
    "    require(len(heads) == 1 and heads[0]['commit'] == TEMPLATE, 'template member head unchanged')\n"
    "    # Sequence 15 changed no embedded pack path, so the composed revision must be unchanged.\n"
    "    require(draft['permission_revision'] == REVISION and revision == REVISION, 'revision unchanged')\n"
    "    require(profile['provider']['version'] == VERSION, 'provider version unchanged')\n")


def input_script():
    text = source(P7/'p7-input.py', '9b711394b82e9b8b64f895bcf0c444e7fab5a02ada0d45654cae72a4a4497e91')
    header = ('''"""P8 step 1: observe the running revision and derive the receipt input. Read-only except its own records.

ga-e0t1.18 S3 part 2. Generated by make_p8.py from the executed P7 input (9b711394); the logic is P7's.
The native cycle trace is read (`gc trace show`, a supported read). The live signing worker's `--version`
proves the dependency version it will report. The installed receipt 7cf59ab9 minus its three generated
fields becomes the input draft. Exactly one field changes, from its exact predecessor:

- member_heads[core]: 9faeabc2 -> deefb98b, the sequence 15 build source (Core PR 48).
The Template cfd353f3, the permission revision 2113693e (the traced running revision must equal it: no
embedded pack path changed), the provider version d4e57767 and the argv model claude-opus-5-5 are asserted
unchanged.

`m7_acceptance()` verifies M7's own reviewed records at run time: a COMMIT_PASS review record with two
distinct provenance files, the committed acceptance it binds, restoration, the M7 release manifest naming
Template cfd353f3 and succeeding the M6 file 7f335ad8, and the live metadata pair byte-identical to the
accepted pair.

  python3 -I -S -B source-launch.py p8-input.py <own sha256>
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('/var/tmp/ga-e0t1.15-p7-input-20260925')", "ROOT = Path('%s')" % INPUT_ROOT, 1),
        ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC_NEW, 1),
        ("CORE = '%s'" % CORE_OLD, "CORE = '%s'" % CORE_NEW, 1),
        ("RECEIPT_OLD_SHA = '%s'" % RECEIPT_P6, "RECEIPT_OLD_SHA = '%s'" % RECEIPT_NOW, 1),
        ("TEMPLATE_OLD, TEMPLATE_NEW = '28539934fa742056e0a65710d5638ff559a21175', '%s'\n" % TEMPLATE,
         "TEMPLATE = '%s'\n" % TEMPLATE, 1),
        ("REVISION_OLD = 'd6ca85cd96c7aab4ea0b6a7954d2d74e5e6bb211cde0bb820f3b6f815023bd88'\n",
         "REVISION = '%s'\n" % REVISION, 1),
        ("VERSION_OLD = 'gct-claude-signing-worker 1 dependencies_sha256="
         "f36deb20efa5cc11781f1d9703b8e5e0d7897c6357260dff1045bcd86489ff34'\n", "", 1),
        ("VERSION_NEW = 'gct", "VERSION = 'gct", 1),
        ("CORE_OLD = '796d9a7a67c42294fdc467c107bb59b76e482301'", "CORE_OLD = '%s'" % CORE_OLD, 1),
        ("'%s'" % M6_RELEASE, "'%s'" % M7_RELEASE, 1),
        ("                TEMPLATE_NEW)", "                TEMPLATE)", 1),
        ("PREVIOUS_MANIFEST_FILE = '%s'" % M5_MANIFEST_FILE, "PREVIOUS_MANIFEST_FILE = '%s'" % M6_MANIFEST_FILE, 1),
        (DERIVE_P7, DERIVE_P8, 1),
        ("version.stdout.strip() == VERSION_NEW", "version.stdout.strip() == VERSION", 1),
        ('M6', 'M7', 22),
        ('m6', 'm7', 10),
        ('For later P7 steps', 'For later P8 steps', 1),
        # After the renames, so the predecessor stays named M6.
        ("the M5 canonical FILE digest.", "the M6 canonical FILE digest.", 1),
        ("previous Core binary (gc 69d00186)", "previous Core binary (gc b2760ea4)", 1),
    ], 'p7-input.py')
    return write('p8-input.py', header + text)


def compose_script(input_sha, builder_sha, binary_sha):
    text = source(P7/'p7-observe-compose.py', '7aadb805fd53455c4a87f92155e647388bc972423b985fa09d7793b12208149a')
    header = ('''"""P8 step 2: one nonlaunching read-only composition observation; no receipt installation.

ga-e0t1.18 S3 part 2. Generated by make_p8.py from the executed P7 observer (7aadb805); the logic is P7's.
Host identity is observed outside bwrap. Inside, the real filesystem is mounted read-only with fresh proc
and dev and no network. No writable production bind exists. Only these bindings change:
- a fresh root;
- the draft proven by the P8 input derivation;
- the composition diagnostic rebuilt at Core deefb98b (tree af5c3f04) by the P8 builder;
- the installed gc fce2e9a0, the sequence 15 supervisor epoch (PID 995924; boot, signer and broker
  unchanged), and the M7 metadata pair;
- the access-time neutral policy, loaded from the reviewed M7 closure module (ce310593). The admitted
  surviving dolt watchdog image stays 69d00186 (OLD_IMAGE), which is the image that watchdog maps.
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('/var/tmp/ga-e0t1.15-p7-compose-20260925')", "ROOT = Path('%s')" % P8_COMPOSE_ROOT, 1),
        ("INPUT_SOURCE = HERE/'p7-input.py'", "INPUT_SOURCE = HERE/'p8-input.py'", 1),
        ("INPUT_SHA = '9b711394b82e9b8b64f895bcf0c444e7fab5a02ada0d45654cae72a4a4497e91'", "INPUT_SHA = '%s'" % input_sha, 1),
        ("BUILD = Path('%s')" % COMPOSE_OLD, "BUILD = Path('%s')" % COMPOSE_ROOT, 1),
        ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC_NEW, 1),
        ("POLICY_SHA = '%s'" % POLICY_OLD, "POLICY_SHA = '%s'" % POLICY_SHA, 1),
        ("BINARY_SHA = 'e123ee37c020b3c1aae703f2956f7b59a322fd4814cea7fe2e5a96dc6c920a76'", "BINARY_SHA = '%s'" % binary_sha, 1),
        *[(old, new, 1) for old, new in EPOCH],
        ("build['builder_sha256'] != '4fda9c3425a474075b48cffc1b32c7db8e710e4b45a769c2be46a29893686052'",
         "build['builder_sha256'] != '%s'" % builder_sha, 1),
        ('M6', 'M7', 1),
        ('m6', 'm7', 4),
    ], 'p7-observe-compose.py')
    return write('p8-observe-compose.py', header + text)


def readiness_script(compose_sha, preflight_builder_sha, binary_sha, extraction_sha):
    text = source(P7/'p7-readiness.py', 'ef43c6203c5e4e3efd183089e1e82556e56180cdeb1f0f9df19bab82f7db6576')
    header = ('''"""P8 step 3: one native receipt-compatibility/readiness observation; no worker or install.

ga-e0t1.18 S3 part 2. Generated by make_p8.py from the executed P7 readiness (ef43c620); the logic is P7's.
Provider version/auth executables and one managed signer --probe may run. There is no inference, signature,
route, resume, or credential refresh. Only these bindings change: the P8 observer and composition, and the
preflight diagnostic rebuilt at Core deefb98b by the P8 builders. The 2.1.280 CLI 1e08503d, the provisioner
64425a72 and the canary runner 3beeedb2 are unchanged.
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT=Path('/var/tmp/ga-e0t1.15-p7-readiness-20260925')", "ROOT=Path('%s')" % READY_ROOT, 1),
        ("BUILD=Path('%s')" % PREFLIGHT_OLD, "BUILD=Path('%s')" % PREFLIGHT_ROOT, 1),
        ("BASE=HERE/'p7-observe-compose.py'", "BASE=HERE/'p8-observe-compose.py'", 1),
        ("BASE_SHA='7aadb805fd53455c4a87f92155e647388bc972423b985fa09d7793b12208149a'", "BASE_SHA='%s'" % compose_sha, 1),
        ("BINARY_SHA='510f4d728472e9500beabab0515a1a4e87d30a7c168c7f723f0c53a28f908619'", "BINARY_SHA='%s'" % binary_sha, 1),
        ("COMPOSITION=Path('/var/tmp/ga-e0t1.15-p7-compose-20260925/composition.json')",
         "COMPOSITION=Path('%s/composition.json')" % P8_COMPOSE_ROOT, 1),
        ("base.read(SUCCESSOR/'prepare-preflight-p7.py','aa0bf8fd4c559e54a0b53fe1c9e2bac2e0ee41d0459decb0b9f00466f9a91179')",
         "base.read(SUCCESSOR/'prepare-preflight-p8.py','%s')" % preflight_builder_sha, 1),
        ("'93da115bd13eae223a5832f39b7daec548124a3f465d8ace2321376fd1d138a8'", "'%s'" % extraction_sha, 1),
        ('# The P7 composition', '# The P8 composition', 1),
    ], 'p7-readiness.py')
    return write('p8-readiness.py', header + text)


def adopt_script(readiness_sha, evidence_sha):
    text = source(P7/'p7-adopt.py', '697116dd621c492c36b798fcab13efba874b2b43ded0232bf89a7ff230d3c1ef')
    header = ('''"""P8 step 4: one receipt-only transaction through the unchanged reviewed provisioner.

ga-e0t1.18 S3 part 2. Generated by make_p8.py from the executed P7 adoption (697116dd); the logic is P7's.
No worker, inference, signing, reload, service transition or root operation. Readiness is reused only while
its input closure still matches. Every live phase uses the existing owned-group runner and a read-only
filesystem except the existing provisioning directory; its runner subdirectory stays read-only. Only these
bindings change: the P8 readiness, the old receipt 7cf59ab9, the Core consumer (gc fce2e9a0, commit deefb98b,
tree af5c3f04), the S1 reviewed-build evidence of fce2e9a0, the running supervisor 995924, and the M7
accepted-deployment evidence and platform self digests. The readiness-derived constants stay None until
readiness has passed; they are filled before the two adoption reviews, and the script refuses until then.
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT=Path('/var/tmp/ga-e0t1.15-p7-adoption-20260925')", "ROOT=Path('%s')" % ADOPT_ROOT, 1),
        ("READY=Path('/var/tmp/ga-e0t1.15-p7-readiness-20260925')", "READY=Path('%s')" % READY_ROOT, 1),
        ("READY_SOURCE=HERE/'p7-readiness.py'", "READY_SOURCE=HERE/'p8-readiness.py'", 1),
        ("READY_SHA='ef43c6203c5e4e3efd183089e1e82556e56180cdeb1f0f9df19bab82f7db6576'", "READY_SHA='%s'" % readiness_sha, 1),
        ("OLD_SHA='%s'" % RECEIPT_P6, "OLD_SHA='%s'" % RECEIPT_NOW, 1),
        ("# Filled from the passed P7 readiness evidence", "# Filled from the passed P8 readiness evidence", 1),
        ("NEW_SHA='7cf59ab9e5a43fd7bca97028e7faaa2b2f9bfb927a663b4588c66e846e4e425d'\n"
         "NEW_SELF='ee4400af626cccfbdf595b092b02a948e14f907fcd104c4500c93429ab4523f8'\n"
         "READY_RESULT_SHA='a6cac0b99822e8432fa8b01b2a0c87bb212ff141c165d13d4921b2b75f8c8ee7'\n"
         "READY_BEFORE_SHA='1d9b0e3550e2baa1563a6db5b57789dc85cf2fc1e3fa661efa127122a5661120'\n"
         "READY_PINS_SHA='82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n",
         "NEW_SHA=None\nNEW_SELF=None\nREADY_RESULT_SHA=None\nREADY_BEFORE_SHA=None\nREADY_PINS_SHA=None\n", 1),
        ("CORE='%s'" % CORE_OLD, "CORE='%s'" % CORE_NEW, 1),
        ("('reviewed-build','/var/tmp/ga-e0t1.15-build-20260925/artifact-verification.json',"
         "'e78516c570c85accccdb869fceed3b9616c54be827af73b4acc072fb90880551')",
         "('reviewed-build','/var/tmp/ga-e0t1.18-build-20260926/artifact-verification.json','%s')" % evidence_sha, 1),
        ("tree='%s'" % TREE_OLD, "tree='%s'" % TREE_NEW, 1),
        ("latest['controller_pid']==2940569", "latest['controller_pid']==995924", 1),
        ('m6', 'm7', 6),
    ], 'p7-adopt.py')
    return write('p8-adopt.py', header + text)


def build_record(root, builder_sha):
    import json
    record = json.loads(Path(root, 'build-result.json').read_bytes())
    if record['builder_sha256'] != builder_sha or sha(Path(root, 'compose').read_bytes()) != record['binary_sha256']:
        raise SystemExit('build record does not bind the reviewed builder and its binary: ' + root)
    return record


def scripts():
    compose_builder = sha((HERE/'prepare-compose-p8.py').read_bytes())
    preflight_builder = sha((HERE/'prepare-preflight-p8.py').read_bytes())
    compose_build = build_record(COMPOSE_ROOT, compose_builder)
    preflight_build = build_record(PREFLIGHT_ROOT, compose_builder)
    if compose_build['core_commit'] != CORE_NEW or compose_build['core_tree'] != TREE_NEW:
        raise SystemExit('compose build is not Core deefb98b')
    extraction = sha(Path(PREFLIGHT_ROOT, 'extraction.json').read_bytes())
    input_sha = input_script()
    compose_sha = compose_script(input_sha, compose_builder, compose_build['binary_sha256'])
    readiness_sha = readiness_script(compose_sha, preflight_builder, preflight_build['binary_sha256'], extraction)
    evidence = sha(Path('/var/tmp/ga-e0t1.18-build-20260926/artifact-verification.json').read_bytes())
    adopt_script(readiness_sha, evidence)
    write('source-launch.py', source(P7/'source-launch.py', '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'))
    write('typed-interoperability.json',
          source(P7/'typed-interoperability.json', '315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563'))


if __name__ == '__main__':
    if sys.argv[1:] == ['builders']:
        builders()
    elif sys.argv[1:] == ['scripts']:
        scripts()
    else:
        raise SystemExit(__doc__)
