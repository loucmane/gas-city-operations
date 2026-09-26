"""Generate the P10 typed candidate receipt refresh from the executed P8/P9 chain by count-checked substitutions.

  python3 -I -B make_p10.py diagnostics   # the two diagnostic sources and their builders
  python3 -I -B make_p10.py scripts       # the chain, after the diagnostics are built and their digests pinned

P10 adds one typed candidate profile to the installed P9 worker receipt (6bf20a71), under the identity the ga-6utp
r12 activation resolved, gascity/operations-candidate-worker (gct-lagl HANDOFF 2.8). The signing profile, the
revision (83c41af6), the core member head (deefb98b), the Template (cfd353f3) and every other receipt field are
asserted unchanged. The platform metadata predecessor is M9 (reports/m9/q), which pins the candidate wrapper.

Core's start preflight gates every session whose identity is in the receipt, comparing the exact composed
argv and environment. So P10 proves the candidate profile against Core's own composition before installing
it, as P8 did for the signing profile:
- compose-main.go is the P8 composition diagnostic (e8cb87a0) with the target moved to the candidate identity,
  the claude-candidate provider and its one agent override (PATH);
- preflight-main.go is the P8 preflight diagnostic (75c897e0) accepting a receipt of one or more profiles and
  taking the environment key set from the named profile. Its negative appends a PATH entry;
- both are built by the reviewed P8 exact-source builder (56f3ca48), unchanged, into fresh roots.
The observer runs both composition diagnostics (the signing one e123ee37 and the candidate one); readiness runs
the negative and the preflight for both profiles.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
P8 = HERE.parent/'p8'
P9 = HERE.parent/'p9'
RECEIPT_P9_OLD, RECEIPT_P9 = ('23eeb222d6d5c0afcf8dc8c01a99dfc7b57fbecfdbc0a1f7ca83d3319181d78e',
                              '6bf20a712ef78be16a0e4e79bd495da12e573fdbd9637508803997ebd23e6bc0')
REVISION_OLD = '2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2'
REVISION = '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add'
M8_RELEASE, M9_RELEASE = 'ops-candidate-lane-metadata-m8-20260926', 'ops-candidate-provider-metadata-m9-20260926'
M7_FILE, M8_FILE = ('4bec5ef14bd81f6dc1830ada48fc502937ff91a531981dfff3fde5aaa92a9759',
                    '63820eacf37a46ec6d6d97cfe0434189a2a41a27c6650462b992d1034da183b8')
INPUT_OLD, INPUT_ROOT = '/var/tmp/ga-e0t1.18-p9-input-20260926', '/var/tmp/ga-e0t1.18-p10-input-20260926'
COMPOSE_OLD, COMPOSE_ROOT = '/var/tmp/ga-e0t1.18-p9-compose-20260926', '/var/tmp/ga-e0t1.18-p10-compose-20260926'
READY_OLD, READY_ROOT = '/var/tmp/ga-e0t1.18-p9-readiness-20260926', '/var/tmp/ga-e0t1.18-p10-readiness-20260926'
ADOPT_OLD, ADOPT_ROOT = '/var/tmp/ga-e0t1.18-p9-adoption-20260926', '/var/tmp/ga-e0t1.18-p10-adoption-20260926'
CANDIDATE_BUILD = '/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926'
PREFLIGHT_OLD, PREFLIGHT_BUILD = ('/var/tmp/ga-e0t1.18-preflight-diagnostic-20260926',
                                  '/var/tmp/ga-e0t1.18-p10-preflight-diagnostic-20260926')
# Pinned after the diagnostics are built by the reviewed builders (make_p10.py diagnostics, then the builders).
CANDIDATE_COMPOSE_SHA = '53450168ef90fd8698688d25fb031e96b3295ff54132441cda72c593611f3111'
PREFLIGHT_SHA = 'c6dd9ebbee33bc40579fc9b7f0af7e7a9c69500566870910f5361eb4b0e12824'
EXTRACTION_SHA = 'a30af30748f8c498a72a0edb1fa4837c677839943eedb9486ea6c046934f4941'


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


def docstring(text, new):
    end = text.index('"""\n', 3) + 4
    return new + text[end:]


# ---------------------------------------------------------------------------------------------------------------
# Diagnostics


def compose_source():
    text = source(P8/'compose-main.go', 'e8cb87a053b07ab8c8f93fd21a6a14c015b81919422ecdbec6c8c7a03201d8b3')
    text = substitute(text, [
        ('// Private diagnostic: configuration composition only; never installed or dispatched.\n',
         '// Private diagnostic: configuration composition only; never installed or dispatched.\n'
         '// P10: the P8 composition for the Operations candidate identity (PATH is its only agent override).\n', 1),
        ('const target = "gascity/gc.implementation-worker"', 'const target = "gascity/operations-candidate-worker"', 1),
        ('p.Name != "claude-signing"', 'p.Name != "claude-candidate"', 1),
        ('[]string{"GOROOT", "GOTOOLCHAIN", "PATH"}', '[]string{"PATH"}', 2),
    ], 'compose-main.go')
    return write('compose-main.go', text)


def preflight_source():
    text = source(P8/'preflight-main.go', '75c897e0874404c8d2fded9302ffbfb799ba983678d5503f44041a7d8508e7c6')
    text = substitute(text, [
        ('// Private receipt preparation: actual native probes, no routed-task assertion.\n',
         '// Private receipt preparation: actual native probes, no routed-task assertion.\n'
         '// P10: the P8 preflight for the one profile the composition names, in a receipt of one or more\n'
         "// profiles. The environment key set is that profile's own, not the signing profile's three keys.\n", 1),
        (' if len(receipt.Profiles)!=1{return fmt.Errorf("exactly one profile required")}\n',
         ' if len(receipt.Profiles)<1{return fmt.Errorf("at least one profile required")}\n', 1),
        (' if len(expected.Environment)!=3 || len(obs.Environment)!=3{return fmt.Errorf("environment key set changed")}\n'
         ' for _,key:=range []string{"GOROOT","GOTOOLCHAIN","PATH"}{if obs.Environment[key]==""{return fmt.Errorf("missing composition environment")}}\n',
         ' if len(expected.Environment)==0 || len(obs.Environment)!=len(expected.Environment){return fmt.Errorf("environment key set changed")}\n'
         ' for key:=range expected.Environment{if obs.Environment[key]==""{return fmt.Errorf("missing composition environment")}}\n', 1),
        ('  observed.Environment["PATH"]="/home/loucmane/.local/share/go/1.26.7/bin:/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin"\n',
         '  observed.Environment["PATH"]=obs.Environment["PATH"]+":/nonexistent-negative"\n', 1),
    ], 'preflight-main.go')
    return write('preflight-main.go', text)


COMPOSE_BUILDER = '''"""P10 candidate composition diagnostic: the reviewed P8 exact-source builder, unchanged, into a fresh root.

Only the root and the composition source change. compose-main.go is the P8 source (e8cb87a0) with the target
moved to gascity/operations-candidate-worker, the claude-candidate provider and its PATH override (make_p10.py).
The builder records the Core commit, tree, archive, Go executable and the source digest in build-result.json.
"""
import hashlib
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILDER = HERE.parent/'p8'/'prepare-compose-p8.py'
EXPECTED = '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4'
ROOT = Path('%(root)s')
MAIN_SHA = '%(main)s'


def main():
    raw = BUILDER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('reviewed builder drift')
    if hashlib.sha256((HERE/'compose-main.go').read_bytes()).hexdigest() != MAIN_SHA:
        raise RuntimeError('candidate composition source drift')
    builder = types.ModuleType('reviewed_exact_builder'); builder.__file__ = str(BUILDER)
    exec(compile(raw, str(BUILDER), 'exec', dont_inherit=True), builder.__dict__)
    builder.ROOT = ROOT
    builder.HERE = HERE
    builder.main()


if __name__ == '__main__':
    main()
'''


def compose_builder(main_sha):
    return write('prepare-compose-p10.py', COMPOSE_BUILDER % dict(root=CANDIDATE_BUILD, main=main_sha))


def preflight_builder():
    text = source(P8/'prepare-preflight-p8.py', '277901e3df5634b109e309f5589ed74f4680a085b6dcb53594a27855cebc1bd1')
    text = substitute(text, [
        ('"""Reuse reviewed exact-source builder, adding unchanged production probes.\n',
         '"""Reuse reviewed exact-source builder, adding unchanged production probes.\n\n'
         'P10: the P8 preflight builder (277901e3) with fresh roots and the P10 preflight-main.go (make_p10.py).\n', 1),
        ("BUILDER = HERE/'prepare-compose-p8.py'", "BUILDER = HERE.parent/'p8'/'prepare-compose-p8.py'", 1),
        ("ROOT = Path('%s')" % PREFLIGHT_OLD, "ROOT = Path('%s')" % PREFLIGHT_BUILD, 1),
        ("STAGING = Path('/var/tmp/ga-e0t1.18-preflight-generated-20260926')",
         "STAGING = Path('/var/tmp/ga-e0t1.18-p10-preflight-generated-20260926')", 1),
    ], 'prepare-preflight-p8.py')
    return write('prepare-preflight-p10.py', text)


def diagnostics():
    compose_builder(compose_source())
    preflight_source()
    preflight_builder()


# ---------------------------------------------------------------------------------------------------------------
# Chain

CANDIDATE_CONSTANTS = '''MODEL = 'claude-opus-5-5'
# The typed candidate profile, under the identity the ga-6utp r12 reload resolved. Its argv and PATH are Core's
# own composition (observed by compose-main.go and re-proven by the observer); its check path is the signing
# lane's; its provider is the M9-pinned wrapper; its toolchain is the reviewed registry record's python pin.
CANDIDATE_WORKER = Path('/home/loucmane/gas-city-template/bin/gct-claude-candidate-worker')
CANDIDATE_POLICY = '/home/loucmane/gas-city-template/templates/claude/candidate-control-policy.json'
CANDIDATE_ROOT = '/home/loucmane/gas-city-ops-candidate-worktrees'
CANDIDATE = {
    'approval_policy': 'dontAsk',
    'argv': [str(CANDIDATE_WORKER), '--permission-mode', 'dontAsk', '--effort', 'max', '--model', MODEL,
             '--settings', CANDIDATE_POLICY, '--add-dir', CANDIDATE_ROOT,
             '--settings', '/home/loucmane/gascity/city/.gc/settings.json'],
    'check_path': {
        'path': '/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f'
                '/gascity/assets/scripts/checks/build-artifact-valid.sh',
        'sha256': '71f17450e127055c8304a3cb44ce87b2439abe04ba41f225c7b386be3dc73911'},
    'control_policy': {'path': CANDIDATE_POLICY,
                       'sha256': 'a3eda9160871c0f25bbd5f1b6680fbc932692d6cee2c4f7dc702ad355954ae49'},
    'environment': {'PATH': '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin'},
    'name': 'gascity/operations-candidate-worker',
    'network_policy': 'no-explicit-egress-denial',
    'profile_kind': 'candidate',
    'provider': {'name': 'claude', 'path': str(CANDIDATE_WORKER), 'resolved_path': str(CANDIDATE_WORKER),
                 'sha256': 'e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3',
                 'version_args': ['--version'],
                 'version': 'gct-claude-candidate-worker 1 '
                            'dependencies_sha256=a35dd4131ed3baa3875b9866aa86e39192d1f96f3f4dd55d8a10d12921eea446'},
    'sandbox_mode': 'claude-native-required-with-five-command-exclusions',
    'signer_identity': 'none',
    'toolchains': [{'name': 'python', 'executable': {
        'path': '/usr/bin/python3.12', 'resolved_path': '/usr/bin/python3.12',
        'sha256': 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f',
        'version_args': ['--version'], 'version': 'Python 3.12.3'}}],
    'writable_roots': [CANDIDATE_ROOT],
}
'''
DERIVE_P9 = (
    "    # The ga-6utp r12 activation reload composed the candidate agent and provider, which moved the revision.\n"
    "    require(draft['permission_revision'] == REVISION_OLD and revision != REVISION_OLD\n"
    "            and len(revision) == 64 and all(c in '0123456789abcdef' for c in revision), 'revision predecessor')\n"
    "    draft['permission_revision'] = revision\n")
DERIVE_P10 = (
    "    # A receipt profile is not composed configuration, so the running revision must be unchanged.\n"
    "    require(draft['permission_revision'] == REVISION and revision == REVISION, 'revision unchanged')\n")
RETURN_P9 = "    return draft\n"
RETURN_P10 = (
    "    # The one change: the typed candidate profile, on the signing lane's check path.\n"
    "    require(profile['name'] == 'gascity/gc.implementation-worker' and profile['profile_kind'] == 'signing',\n"
    "            'signing profile predecessor')\n"
    "    require(profile['check_path'] == CANDIDATE['check_path'], 'candidate check path is the signing lane check')\n"
    "    draft['profiles'].append(copy.deepcopy(CANDIDATE))\n"
    "    return draft\n")
VERSION_P9 = "    require(version.returncode == 0 and version.stdout.strip() == VERSION, 'live worker dependency version')\n"
VERSION_P10 = VERSION_P9 + (
    "    candidate = subprocess.run([str(CANDIDATE_WORKER), '--version'], env=ENV, cwd='/', stdin=subprocess.DEVNULL,\n"
    "                               capture_output=True, text=True, timeout=60, check=False)\n"
    "    require(candidate.returncode == 0 and candidate.stdout.strip() == CANDIDATE['provider']['version'],\n"
    "            'live candidate worker dependency version')\n")


def input_script():
    text = source(P9/'p9-input.py', '357400766b0ff8bccdf3618955a6f708cd6f49403e5b80a20050efc3509b1601')
    header = ('''"""P10 step 1: observe the running revision and derive the receipt input. Read-only except its own records.

ga-e0t1.18 first candidate window, RECEIPT. Generated by make_p10.py from the executed P9 input; the logic is P9's.
The installed receipt 6bf20a71 minus its generated fields becomes the input draft. Exactly one change: the typed
candidate profile gascity/operations-candidate-worker is appended. The running revision must still be 83c41af6,
and the signing profile, the core member head deefb98b, the Template cfd353f3, the provider version d4e57767
and the argv model claude-opus-5-5 are asserted unchanged. The live candidate wrapper must report its pinned
version. `m9_acceptance()` verifies M9's reviewed records and that the live metadata pair is the accepted M9
pair succeeding the M8 file 63820eac.

  python3 -I -S -B source-launch.py p10-input.py <own sha256>
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('%s')" % INPUT_OLD, "ROOT = Path('%s')" % INPUT_ROOT, 1),
        ("RECEIPT_OLD_SHA = '%s'" % RECEIPT_P9_OLD, "RECEIPT_OLD_SHA = '%s'" % RECEIPT_P9, 1),
        ("REVISION_OLD = '%s'" % REVISION_OLD, "REVISION = '%s'" % REVISION, 1),
        ("MODEL = 'claude-opus-5-5'\n", CANDIDATE_CONSTANTS, 1),
        (DERIVE_P9, DERIVE_P10, 1),
        (RETURN_P9, RETURN_P10, 1),
        (VERSION_P9, VERSION_P10, 1),
        ("worker_version=version.stdout.strip(),",
         "worker_version=version.stdout.strip(),\n                  candidate_worker_version=candidate.stdout.strip(),", 1),
        ("'%s'" % M8_RELEASE, "'%s'" % M9_RELEASE, 1),
        ("PREVIOUS_MANIFEST_FILE = '%s'" % M7_FILE, "PREVIOUS_MANIFEST_FILE = '%s'" % M8_FILE, 1),
        ('M8', 'M9', 22),
        ('m8', 'm9', 10),
        ("the M7 canonical FILE digest.", "the M8 canonical FILE digest.", 1),
        ('For later P9 steps', 'For later P10 steps', 1),
    ], 'p9-input.py')
    return write('p10-input.py', header + text)


def compose_script(input_sha):
    text = source(P9/'p9-observe-compose.py', 'ace67882bad047ab4dffd4e210723b8293bbe6797d72bd1741089447ca9ba0a5')
    header = ('''"""P10 step 2: one nonlaunching read-only composition observation of both profiles; no receipt installation.

ga-e0t1.18 first candidate window, RECEIPT. Generated by make_p10.py from the executed P9 observer; the logic is
P9's, run for two identities. In one read-only namespace it runs the signing composition diagnostic (e123ee37)
and the candidate one, and each observation must equal the draft profile of the same name: the argv, the
environment and the revision. Also changed: a fresh root, the P10 input, the M9 metadata pair, and the candidate
wrapper and policy among the snapshot pins.
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('%s')" % COMPOSE_OLD, "ROOT = Path('%s')" % COMPOSE_ROOT, 1),
        ("INPUT_SOURCE = HERE/'p9-input.py'", "INPUT_SOURCE = HERE/'p10-input.py'", 1),
        ("INPUT_SHA = '357400766b0ff8bccdf3618955a6f708cd6f49403e5b80a20050efc3509b1601'", "INPUT_SHA = '%s'" % input_sha, 1),
        ("BINARY_SHA = 'e123ee37c020b3c1aae703f2956f7b59a322fd4814cea7fe2e5a96dc6c920a76'\n",
         "BINARY_SHA = 'e123ee37c020b3c1aae703f2956f7b59a322fd4814cea7fe2e5a96dc6c920a76'\n"
         "CANDIDATE_BUILD = Path('%s')\n"
         "CANDIDATE_BINARY_SHA = '%s'\n" % (CANDIDATE_BUILD, CANDIDATE_COMPOSE_SHA), 1),
        ("        Path('/home/loucmane/gas-city-template/templates/claude/core-signing-control-policy.json')]\n",
         "        Path('/home/loucmane/gas-city-template/templates/claude/core-signing-control-policy.json'),\n"
         "        Path('/home/loucmane/gas-city-template/bin/gct-claude-candidate-worker'),\n"
         "        Path('/home/loucmane/gas-city-template/lib/gct_claude_candidate_worker.py'),\n"
         "        Path('/home/loucmane/gas-city-template/templates/claude/candidate-control-policy.json'),\n"
         "        Path('/home/loucmane/gas-city-template/templates/claude/candidate-provider.toml')]\n", 1),
        ("    for path in (str(CACHE), *(str(p) for p in PROTECTED), str(CITY), str(BUILD)):\n",
         "    for path in (str(CACHE), *(str(p) for p in PROTECTED), str(CITY), str(BUILD), str(CANDIDATE_BUILD)):\n", 1),
        ("""    read(BUILD/'compose', BINARY_SHA)
    # Parent owns the finite process-group bound; this child does not detach.
    result = subprocess.run([str(BUILD/'compose')], env=ENV, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError('composition refused: '+result.stderr)
    print(json.dumps(dict(mounts=proofs, observation=json.loads(result.stdout),
                         host_verification='outside-namespace', worker_launched=False)))
""", """    observations = []
    for build, digest in ((BUILD, BINARY_SHA), (CANDIDATE_BUILD, CANDIDATE_BINARY_SHA)):
        read(build/'compose', digest)
        # Parent owns the finite process-group bound; this child does not detach.
        result = subprocess.run([str(build/'compose')], env=ENV, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError('composition refused: '+result.stderr)
        observations.append(json.loads(result.stdout))
    print(json.dumps(dict(mounts=proofs, observation=observations[0], candidate_observation=observations[1],
                         host_verification='outside-namespace', worker_launched=False)))
""", 1),
        ("""    read(BUILD/'compose', BINARY_SHA)
    build = json.loads(read(BUILD/'build-result.json'))
    if build['builder_sha256'] != '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4' or build['binary_sha256'] != BINARY_SHA:
        raise RuntimeError('reviewed build binding mismatch')
""", """    for root, digest in ((BUILD, BINARY_SHA), (CANDIDATE_BUILD, CANDIDATE_BINARY_SHA)):
        read(root/'compose', digest)
        build = json.loads(read(root/'build-result.json'))
        if build['builder_sha256'] != '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4' or build['binary_sha256'] != digest:
            raise RuntimeError('reviewed build binding mismatch')
""", 1),
        ("""        observation = json.loads(result['stdout'])
        actual = observation['observation']
        expected = draft['profiles'][0]
        if (actual['profile'] != expected['name'] or actual['argv'] != expected['argv']
            or actual['environment'] != expected['environment']
            or actual['permission_revision'] != draft['permission_revision']
            or actual['task_observed'] or actual['worker_launched']):
            raise RuntimeError('actual composition differs from draft')
""", """        observation = json.loads(result['stdout'])
        names = [p['name'] for p in draft['profiles']]
        if names != ['gascity/gc.implementation-worker', 'gascity/operations-candidate-worker']:
            raise RuntimeError('draft profile set differs')
        for key, expected in (('observation', draft['profiles'][0]), ('candidate_observation', draft['profiles'][1])):
            actual = observation[key]
            if (actual['profile'] != expected['name'] or actual['argv'] != expected['argv']
                or actual['environment'] != expected['environment']
                or actual['permission_revision'] != draft['permission_revision']
                or actual['task_observed'] or actual['worker_launched']):
                raise RuntimeError('actual composition differs from draft: '+expected['name'])
""", 1),
        ("        write('composition.json', observation)\n",
         "        write('composition.json', observation)\n"
         "        write('composition-candidate.json', dict(observation=observation['candidate_observation']))\n", 1),
        ('M8', 'M9', 1),
        ('m8', 'm9', 4),
    ], 'p9-observe-compose.py')
    return write('p10-observe-compose.py', header + text)


def readiness_script(compose_sha):
    text = source(P9/'p9-readiness.py', '3ef9d90d2a850fec561241551efb743f17e7e4e0a17a5fb4e2c6dcf6bf762bcd')
    header = ('''"""P10 step 3: one native receipt-compatibility/readiness observation of both profiles; no worker or install.

ga-e0t1.18 first candidate window, RECEIPT. Generated by make_p10.py from the executed P9 readiness; the logic is
P9's. The normalized and finalized receipt carries both profiles. The P10 preflight diagnostic runs Core's own
start preflight, and its exact-profile negative, for the signing profile against its composition and for the
candidate profile against the candidate composition. Also changed: a fresh root, the P10 observer and
compositions, the P10 preflight build and its sources, and the candidate policy in the settings inspection.
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT=Path('%s')" % READY_OLD, "ROOT=Path('%s')" % READY_ROOT, 1),
        ("BUILD=Path('%s')" % PREFLIGHT_OLD, "BUILD=Path('%s')" % PREFLIGHT_BUILD, 1),
        ("BASE=HERE/'p9-observe-compose.py'", "BASE=HERE/'p10-observe-compose.py'", 1),
        ("BASE_SHA='ace67882bad047ab4dffd4e210723b8293bbe6797d72bd1741089447ca9ba0a5'", "BASE_SHA='%s'" % compose_sha, 1),
        ("SUCCESSOR=HERE.parent/'p8'\n", "SUCCESSOR=HERE\n", 1),
        ("BINARY_SHA='73d4e14c1817893479b226212b1cf16fd0e31afdeafd28aa4da46bc7d58e8d89'", "BINARY_SHA='%s'" % PREFLIGHT_SHA, 1),
        ("COMPOSITION=Path('%s/composition.json')\n" % COMPOSE_OLD,
         "COMPOSITION=Path('%s/composition.json')\n"
         "CANDIDATE_COMPOSITION=Path('%s/composition-candidate.json')\n" % (COMPOSE_ROOT, COMPOSE_ROOT), 1),
        ("POLICY=Path('/home/loucmane/gas-city-template/templates/claude/core-signing-control-policy.json')\n",
         "POLICY=Path('/home/loucmane/gas-city-template/templates/claude/core-signing-control-policy.json')\n"
         "CANDIDATE_POLICY=Path('/home/loucmane/gas-city-template/templates/claude/candidate-control-policy.json')\n", 1),
        ("""    draft=json.loads(base.recorded_draft()['raw']);expected=draft['profiles'][0]
    if (actual['profile']!=expected['name'] or actual['argv']!=expected['argv']
        or actual['environment']!=expected['environment']
        or actual['permission_revision']!=draft['permission_revision']
        or actual['task_observed'] or actual['worker_launched']):
        raise RuntimeError('composition differs from the proven draft')
""", """    draft=json.loads(base.recorded_draft()['raw'])
    candidate=json.loads(base.read(CANDIDATE_COMPOSITION))['observation']
    if candidate!=json.loads(base.read(COMPOSITION))['candidate_observation']:
        raise RuntimeError('candidate composition record differs')
    for actual,expected in ((actual,draft['profiles'][0]),(candidate,draft['profiles'][1])):
        if (actual['profile']!=expected['name'] or actual['argv']!=expected['argv']
            or actual['environment']!=expected['environment']
            or actual['permission_revision']!=draft['permission_revision']
            or actual['task_observed'] or actual['worker_launched']):
            raise RuntimeError('composition differs from the proven draft: '+expected['name'])
""", 1),
        ("    base.read(SUCCESSOR/'preflight-main.go','75c897e0874404c8d2fded9302ffbfb799ba983678d5503f44041a7d8508e7c6')\n"
         "    base.read(SUCCESSOR/'prepare-preflight-p8.py','277901e3df5634b109e309f5589ed74f4680a085b6dcb53594a27855cebc1bd1')\n"
         "    base.read(BUILD/'extraction.json','e32de6fbc7c9cd49b5e30bbed0fa8d5236dcff119fe56d516acf9e6be158f88f')\n",
         "    base.read(SUCCESSOR/'preflight-main.go','%s')\n"
         "    base.read(SUCCESSOR/'prepare-preflight-p10.py','%s')\n"
         "    base.read(BUILD/'extraction.json','%s')\n"
         % (sha((HERE/'preflight-main.go').read_bytes()), sha((HERE/'prepare-preflight-p10.py').read_bytes()),
            EXTRACTION_SHA), 1),
        ("        subscription.inspect_settings_files([POLICY])\n",
         "        subscription.inspect_settings_files([POLICY,CANDIDATE_POLICY])\n", 1),
        ("""    elif mode in ('negative-old-path','preflight'):
        argv += [mode,str(ROOT/'receipt.final.json'),str(COMPOSITION),NATIVE_SHA]
""", """    elif mode in ('negative-old-path','preflight'):
        argv += [mode,str(ROOT/'receipt.final.json'),str(COMPOSITION),NATIVE_SHA]
    elif mode in ('negative-candidate','preflight-candidate'):
        binary={'negative-candidate':'negative-old-path','preflight-candidate':'preflight'}[mode]
        argv += [binary,str(ROOT/'receipt.final.json'),str(CANDIDATE_COMPOSITION),NATIVE_SHA]
""", 1),
        ("        for mode in ('normalize','finalize','discover','negative-old-path','subscription','preflight'):\n",
         "        for mode in ('normalize','finalize','discover','negative-old-path','negative-candidate','subscription',\n"
         "                     'preflight','preflight-candidate'):\n", 1),
        ('# The P9 composition is accepted', '# The P10 compositions are accepted', 1),
    ], 'p9-readiness.py')
    return write('p10-readiness.py', header + text)


def adopt_script(readiness_sha):
    text = source(P9/'p9-adopt.py', 'b03e485674292613c604b5afc7ce1d6215c2748c4207904e654a826e72c44c39')
    header = ('''"""P10 step 4: one receipt-only transaction through the unchanged reviewed provisioner.

ga-e0t1.18 first candidate window, RECEIPT. Generated by make_p10.py from the executed P9 adoption; the logic is
P9's. Only these bindings change: the P10 readiness, the old receipt 6bf20a71, and the M9 accepted-deployment
evidence and platform self digests in the typed-support witness. The Core consumer, build evidence and
controller are unchanged. The readiness-derived constants stay None until readiness has passed.
"""
''')
    text = docstring(text, '')
    text = substitute(text, [
        ("NEW_SHA='6bf20a712ef78be16a0e4e79bd495da12e573fdbd9637508803997ebd23e6bc0'\n"
         "NEW_SELF='781dd46da7dc0ccf484be134edeb53040b46747fc3cfb4ac3362a91b4f4cdeb6'\n"
         "READY_RESULT_SHA='a6cac0b99822e8432fa8b01b2a0c87bb212ff141c165d13d4921b2b75f8c8ee7'\n"
         "READY_BEFORE_SHA='2840a80e8e14f2f39d5ca533c99100523a846a9d0e2c7f13cdd0c1be5f8e9ad0'\n"
         "READY_PINS_SHA='82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n",
         "NEW_SHA=None\nNEW_SELF=None\nREADY_RESULT_SHA=None\nREADY_BEFORE_SHA=None\nREADY_PINS_SHA=None\n", 1),
        ("ROOT=Path('%s')" % ADOPT_OLD, "ROOT=Path('%s')" % ADOPT_ROOT, 1),
        ("READY=Path('%s')" % READY_OLD, "READY=Path('%s')" % READY_ROOT, 1),
        ("READY_SOURCE=HERE/'p9-readiness.py'", "READY_SOURCE=HERE/'p10-readiness.py'", 1),
        ("READY_SHA='3ef9d90d2a850fec561241551efb743f17e7e4e0a17a5fb4e2c6dcf6bf762bcd'", "READY_SHA='%s'" % readiness_sha, 1),
        ("OLD_SHA='%s'" % RECEIPT_P9_OLD, "OLD_SHA='%s'" % RECEIPT_P9, 1),
        ("# Filled from the passed P9 readiness evidence", "# Filled from the passed P10 readiness evidence", 1),
        ('m8', 'm9', 6),
    ], 'p9-adopt.py')
    return write('p10-adopt.py', header + text)


def scripts():
    if None in (CANDIDATE_COMPOSE_SHA, PREFLIGHT_SHA, EXTRACTION_SHA):
        raise SystemExit('build the diagnostics and pin their digests first')
    input_sha = input_script()
    compose_sha = compose_script(input_sha)
    readiness_sha = readiness_script(compose_sha)
    adopt_script(readiness_sha)
    write('source-launch.py', source(P9/'source-launch.py', '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'))
    write('typed-interoperability.json',
          source(P9/'typed-interoperability.json', '315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563'))


if __name__ == '__main__':
    if sys.argv[1:] == ['diagnostics']:
        diagnostics()
    elif sys.argv[1:] == ['scripts']:
        scripts()
    else:
        raise SystemExit(__doc__)
