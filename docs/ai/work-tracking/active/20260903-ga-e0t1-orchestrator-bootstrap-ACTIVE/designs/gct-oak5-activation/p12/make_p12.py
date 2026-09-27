"""Generate the P12 worker receipt refresh (gct-oak5) from the executed P11 chain by count-checked substitutions.

  python3 -I -B make_p12.py diagnostics   # the Template composition source and its builder
  python3 -I -B make_p12.py scripts       # the chain, after the Template diagnostic is built and its digest pinned

The installed worker receipt 06a3f58a (P11) carries two profiles, the signing lane gascity/gc.implementation-worker
and the Operations candidate gascity/operations-candidate-worker, with permission revision 03f16ea2 and Template
member head cfd353f3. Since then:
- the gct-oak5 activation rendered the Template candidate lane (provider claude-template-candidate, agent
  gas-city-template/gc.implementation-worker, work_dir_roots at the Template candidate root, max_active_sessions 1)
  and reloaded the controller; the 2026-09-27 cycles report config_revision 06076790 (controller 2800348,
  gc_commit f45a6262, unchanged);
- M11 moved the platform metadata's Template authority to the canonical checkout at 3474abfa (Template PR 72).
P12 moves three leaves (permission_revision 03f16ea2 -> 06076790, template_commit and member_heads[template]
cfd353f3 -> 3474abfa) and appends one typed candidate profile for the Template lane, through the unchanged reviewed
provisioner 64425a72. The signing and Operations candidate profiles, Core f45a6262, the pack and the canary runner
are asserted unchanged. Core is unchanged since P11, so the P11 signing and Operations candidate compositions and
the P11 preflight diagnostic are reused as built. One diagnostic is new:
- template/compose-main.go is the P11 candidate composition source (5040c196) with only the target identity and the
  provider name substituted; prepare-compose-template-p12.py loads the reviewed P11 exact-source builder (ba9be1f6)
  in place, by digest, into a fresh root.
The chain is the executed P11 chain, rebound: the input appends the Template profile and moves three leaves, the
platform predecessor is M11 (reports/m11/q), the observer and readiness gain a third profile, and the adoption
witness names the M11 acceptance.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
P11 = HERE.parent.parent/'ga-bebv-deploy'/'p11'

P11_BUILDER = P11/'prepare-compose-p11.py'
P11_BUILDER_SHA = 'ba9be1f66c6a49060f73aa885e2c1c84ddb913a0985b0b5bca8bf52368560130'
P11_CANDIDATE_MAIN_SHA = '5040c19623eddd137b48865e0406bfae2c57a2b7933780363c48fe124093f363'
TEMPLATE_BUILD = '/var/tmp/gct-oak5-p12-template-compose-diagnostic-20260927'

# Pinned after the Template diagnostic is built (make_p12.py diagnostics, then prepare-compose-template-p12.py).
TEMPLATE_COMPOSE_SHA = 'acfb64314590b4e722f9a9394e5be46d4e41647b17ef859136818b7ebb03955b'


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

TEMPLATE_BUILDER = '''"""P12 Template candidate composition diagnostic: the reviewed P11 exact-source builder, in place, into a fresh root.

The builder is loaded from ga-bebv-deploy/p11 by digest and runs unchanged, so build-result.json records the same
builder_sha256 as the P11 signing and Operations candidate diagnostics. Only the root and the composition source
directory change. template/compose-main.go is the P11 candidate composition source (5040c196) with the target
identity and the provider name substituted (make_p12.py).
"""
import hashlib
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILDER = HERE.parent.parent/'ga-bebv-deploy'/'p11'/'prepare-compose-p11.py'
EXPECTED = '%(builder)s'
ROOT = Path('%(root)s')
MAIN_SHA = '%(main)s'


def main():
    raw = BUILDER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('reviewed builder drift')
    if hashlib.sha256((HERE/'template'/'compose-main.go').read_bytes()).hexdigest() != MAIN_SHA:
        raise RuntimeError('Template composition source drift')
    builder = types.ModuleType('reviewed_exact_builder'); builder.__file__ = str(BUILDER)
    exec(compile(raw, str(BUILDER), 'exec', dont_inherit=True), builder.__dict__)
    builder.ROOT = ROOT
    builder.HERE = HERE/'template'
    builder.main()


if __name__ == '__main__':
    main()
'''


def template_main():
    text = source(P11/'candidate'/'compose-main.go', P11_CANDIDATE_MAIN_SHA)
    return substitute(text, [
        ('// P10: the P8 composition for the Operations candidate identity (PATH is its only agent override).\n',
         '// P10: the P8 composition for the Operations candidate identity (PATH is its only agent override).\n'
         '// P12: the same composition for the Template candidate identity and provider (make_p12.py).\n', 1),
        ('const target = "gascity/operations-candidate-worker"',
         'const target = "gas-city-template/gc.implementation-worker"', 1),
        ('p.Name != "claude-candidate"', 'p.Name != "claude-template-candidate"', 1),
    ], 'candidate/compose-main.go')


def diagnostics():
    main_sha = write('template/compose-main.go', template_main())
    write('prepare-compose-template-p12.py',
          TEMPLATE_BUILDER % dict(builder=P11_BUILDER_SHA, root=TEMPLATE_BUILD, main=main_sha))


# ---------------------------------------------------------------------------------------------------------------
# Chain

P11_INPUT_SHA = '3fb16bda2ba3719a6d2fd05f0cb3aa2807c4608706515dd5a43dc0ab77db5b61'
P11_COMPOSE_SHA = '26c7cafe37281a3b1f459aa78aecf799d385d9be9278eab966c7216cd971412e'
P11_READY_SHA = '7370cf11030009888caa439ed402a7f29af743a1012ac369e7ebb78bed8d6fd4'
P11_ADOPT_SHA = 'd0e3355a0d91742fef7106d67e57520dec518569e6ad33aef588216ae659b384'
LAUNCHER_SHA = '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'
TYPED_SHA = '315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563'

RECEIPT_P11 = '06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5'
RECEIPT_P10 = 'c833908fe89ab180e57ef7164d687f01ae2052f8667360f04b73c5423902f0a4'
REVISION_P10 = '83c41af65776eaa90f93b57158e8ad57141e19347a592ce509a19f56c2667add'
REVISION_P11 = '03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712'
REVISION = '06076790c31448212545edc1e741f592ed5b23ac54debbefb5e6da847143d753'
TEMPLATE_OLD = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
TEMPLATE = '3474abfaec255f7ea4266ce8aa35218afcfc89b0'
M9_FILE, M10_FILE = ('5a29dc596af192e0f314391453d25d6be548695a0defd64bdfc2fa76554e4993',
                     '2b902a83577acf71f9dd93a97d43d8478f7c4b291b0992e8ba5a5e44fe66f7f2')

INPUT_OLD, INPUT_ROOT = '/var/tmp/ga-bebv-p11-input-20260927', '/var/tmp/gct-oak5-p12-input-20260927'
COMPOSE_OLD, COMPOSE_ROOT = '/var/tmp/ga-bebv-p11-compose-20260927', '/var/tmp/gct-oak5-p12-compose-20260927'
READY_OLD, READY_ROOT = '/var/tmp/ga-bebv-p11-readiness-20260927', '/var/tmp/gct-oak5-p12-readiness-20260927'
ADOPT_OLD, ADOPT_ROOT = '/var/tmp/ga-bebv-p11-adoption-20260927', '/var/tmp/gct-oak5-p12-adoption-20260927'

TEMPLATE_CANDIDATE = '''# The typed Template candidate profile, under the identity the gct-oak5 activation reload resolved. Its argv and
# PATH are Core's own composition (template/compose-main.go, re-proven by the observer). Its check path is the
# Operations candidate's, the signing lane check: the Template rig imports the same gc pack at the same version.
# Its provider is the M11-pinned wrapper; its policy has the same five sandbox exclusions as the Operations
# candidate policy; its toolchain is the Operations candidate's python pin.
TEMPLATE_WORKER = Path('/home/loucmane/gas-city-template/bin/gct-claude-template-candidate-worker')
TEMPLATE_POLICY = '/home/loucmane/gas-city-template/templates/claude/template-candidate-control-policy.json'
TEMPLATE_ROOT = '/home/loucmane/gas-city-template-candidate-worktrees'
TEMPLATE_CANDIDATE = {
    'approval_policy': 'dontAsk',
    'argv': [str(TEMPLATE_WORKER), '--permission-mode', 'dontAsk', '--effort', 'max', '--model', MODEL,
             '--settings', TEMPLATE_POLICY, '--add-dir', TEMPLATE_ROOT,
             '--settings', '/home/loucmane/gascity/city/.gc/settings.json'],
    'check_path': copy.deepcopy(CANDIDATE['check_path']),
    'control_policy': {'path': TEMPLATE_POLICY,
                       'sha256': '6b2f160d4999781db17ddf117b482a9c20432032c1162fed453a06ba7376fec1'},
    'environment': {'PATH': '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin'},
    'name': 'gas-city-template/gc.implementation-worker',
    'network_policy': 'no-explicit-egress-denial',
    'profile_kind': 'candidate',
    'provider': {'name': 'claude', 'path': str(TEMPLATE_WORKER), 'resolved_path': str(TEMPLATE_WORKER),
                 'sha256': '229d33557326abc8bafceadb06ae12ba2a2d9189e137ff0e1378d35dcf69491c',
                 'version_args': ['--version'],
                 'version': 'gct-claude-template-candidate-worker 1 '
                            'dependencies_sha256=3cd85706cd98a25bd50ef12c5dfa59e34054396db81913cd4692728e6ca7ffb3'},
    'sandbox_mode': 'claude-native-required-with-five-command-exclusions',
    'signer_identity': 'none',
    'toolchains': copy.deepcopy(CANDIDATE['toolchains']),
    'writable_roots': [TEMPLATE_ROOT],
}
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
DERIVE_P12 = '''def derive(receipt, revision):
    """Pure: the receipt input for the M11 state, with every predecessor asserted."""
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
    require(profile['provider']['version'] == VERSION, 'provider version unchanged')
    argv = profile['argv']
    positions = [i for i, token in enumerate(argv) if token == '--model']
    require(len(positions) == 1 and argv[positions[0] + 1] == MODEL, 'argv model unchanged')
    cores = [h for h in draft['member_heads'] if h['name'] == 'core']
    require(len(cores) == 1 and cores[0]['commit'] == CORE, 'core member head unchanged')
    # The changes. The gct-oak5 activation rendered the Template candidate lane, which moved the composed
    # revision to the exact value the controller traced on 2026-09-27; M11 moved the Template authority to the
    # canonical checkout at 3474abfa (Template PR 72); the lane's typed profile is appended.
    require(draft['permission_revision'] == REVISION_OLD and revision == REVISION, 'revision predecessor')
    draft['permission_revision'] = revision
    require(draft['template_commit'] == TEMPLATE_OLD, 'template predecessor')
    draft['template_commit'] = TEMPLATE
    heads = [h for h in draft['member_heads'] if h['name'] == 'template']
    require(len(heads) == 1 and heads[0]['commit'] == TEMPLATE_OLD, 'template member head predecessor')
    heads[0]['commit'] = TEMPLATE
    require(TEMPLATE_CANDIDATE['check_path'] == CANDIDATE['check_path'], 'Template check path is the candidate check')
    require(all(each['name'] != TEMPLATE_CANDIDATE['name'] for each in draft['profiles']), 'Template profile absent')
    draft['profiles'].append(copy.deepcopy(TEMPLATE_CANDIDATE))
    return draft
'''


def input_script():
    text = source(P11/'p11-input.py', P11_INPUT_SHA)
    header = '''"""P12 step 1: observe the running revision and derive the receipt input. Read-only except its own records.

gct-oak5 RECEIPT. Generated by make_p12.py from the executed P11 input; the logic is P11's. The installed receipt
06a3f58a minus its generated fields becomes the input draft. Three leaves change: the permission revision
03f16ea2 -> 06076790 (the activated Template candidate lane, traced live from the controller) and the
template_commit and Template member head cfd353f3 -> 3474abfa (Template PR 72, the M11 authority). One typed
profile is appended: gas-city-template/gc.implementation-worker on the claude-template-candidate provider. The
signing and Operations candidate profiles, Core f45a6262, the signing provider version d4e57767 and the argv model
claude-opus-5-5 are asserted unchanged, and all three live wrappers must report their pinned versions.
`m11_acceptance()` verifies M11's reviewed records and that the live metadata pair is the accepted M11 pair
succeeding the M10 file 2b902a83.

  python3 -I -S -B source-launch.py p12-input.py <own sha256>
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('%s')" % INPUT_OLD, "ROOT = Path('%s')" % INPUT_ROOT, 1),
        ("CORE_OLD = 'deefb98b2aed07875df31351d081fbac195cb1cd'\n", '', 1),
        ("RECEIPT_OLD_SHA = '%s'" % RECEIPT_P10, "RECEIPT_OLD_SHA = '%s'" % RECEIPT_P11, 1),
        ("TEMPLATE = '%s'" % TEMPLATE_OLD, "TEMPLATE_OLD = '%s'\nTEMPLATE = '%s'" % (TEMPLATE_OLD, TEMPLATE), 1),
        ("REVISION_OLD = '%s'\nREVISION = '%s'" % (REVISION_P10, REVISION_P11),
         "REVISION_OLD = '%s'\nREVISION = '%s'" % (REVISION_P11, REVISION), 1),
        ("M10 = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m10/q')\n",
         TEMPLATE_CANDIDATE +
         "M11 = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m11/q')\n", 1),
        ("M10_RELEASE = 'ga-bebv-core-seq16-city-metadata-m10-20260927'",
         "M11_RELEASE = 'gct-oak5-template-candidate-lane-metadata-m11-20260927'", 1),
        ("M10_AUTHORITY = ('template-pr71-authority', '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority',\n"
         "                TEMPLATE)",
         "M11_AUTHORITY = ('template-pr72-canonical', '/home/loucmane/gas-city-template', TEMPLATE)", 1),
        ("PREVIOUS_MANIFEST_FILE = '%s'" % M9_FILE, "PREVIOUS_MANIFEST_FILE = '%s'" % M10_FILE, 1),
        (DERIVE_P11, DERIVE_P12, 1),
        ("    require(candidate.returncode == 0 and candidate.stdout.strip() == CANDIDATE['provider']['version'],\n"
         "            'live candidate worker dependency version')\n",
         "    require(candidate.returncode == 0 and candidate.stdout.strip() == CANDIDATE['provider']['version'],\n"
         "            'live candidate worker dependency version')\n"
         "    template = subprocess.run([str(TEMPLATE_WORKER), '--version'], env=ENV, cwd='/', stdin=subprocess.DEVNULL,\n"
         "                              capture_output=True, text=True, timeout=60, check=False)\n"
         "    require(template.returncode == 0 and template.stdout.strip() == TEMPLATE_CANDIDATE['provider']['version'],\n"
         "            'live Template candidate worker dependency version')\n", 1),
        ("                  candidate_worker_version=candidate.stdout.strip(),\n",
         "                  candidate_worker_version=candidate.stdout.strip(),\n"
         "                  template_candidate_worker_version=template.stdout.strip(),\n", 1),
        ('For later P11 steps', 'For later P12 steps', 1),
        ('M10', 'M11', 18),
        ('m10', 'm11', 9),
        # After the renames: the succession link names M10's file.
        ("# The succession link is previous_metadata.manifest_sha256, the M9 canonical FILE digest.",
         "# The succession link is previous_metadata.manifest_sha256, the M10 canonical FILE digest.", 1),
    ], 'p11-input.py')
    # M10 stays named only in the succession comment above (checked by test_p12.py).
    stale(text, 'p12-input.py', ('m10', 'M10_', 'P11', 'deefb98b', 'CORE_OLD', RECEIPT_P10, REVISION_P10))
    return write('p12-input.py', header + text)


def compose_script(input_sha):
    text = source(P11/'p11-observe-compose.py', P11_COMPOSE_SHA)
    header = '''"""P12 step 2: one nonlaunching read-only composition observation of three profiles; no receipt installation.

gct-oak5 RECEIPT. Generated by make_p12.py from the executed P11 observer; the logic is P11's. In one read-only
namespace it runs the signing and the Operations candidate composition diagnostics built for P11 and the Template
candidate diagnostic built for P12, all from Core f45a6262 by the same P11 builder, and each observation must equal
the draft profile of the same name: the argv, the environment and the revision. Also changed: a fresh root, the
P12 input, the M11 metadata pair, the policy module path (the byte-identical M11 copy of metadata_closure.py) and
the four Template candidate files in the pinned inputs.
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT = Path('%s')" % COMPOSE_OLD, "ROOT = Path('%s')" % COMPOSE_ROOT, 1),
        ("INPUT_SOURCE = HERE/'p11-input.py'", "INPUT_SOURCE = HERE/'p12-input.py'", 1),
        ("INPUT_SHA = '%s'" % P11_INPUT_SHA, "INPUT_SHA = '%s'" % input_sha, 1),
        ("POLICY = HERE.parent/'m10'/'metadata_closure.py'", "POLICY = HERE.parent/'m11'/'metadata_closure.py'", 1),
        ("CANDIDATE_BINARY_SHA = '8cb667dc8a65a858c9df2708a5e42ece79f59ce10a1372b817b8e656aa3ae207'\n",
         "CANDIDATE_BINARY_SHA = '8cb667dc8a65a858c9df2708a5e42ece79f59ce10a1372b817b8e656aa3ae207'\n"
         "TEMPLATE_BUILD = Path('%s')\nTEMPLATE_BINARY_SHA = '%s'\n" % (TEMPLATE_BUILD, TEMPLATE_COMPOSE_SHA), 1),
        ("  # prepare-compose-p11.py; both diagnostics record it",
         "  # ga-bebv-deploy/p11/prepare-compose-p11.py; all three diagnostics record it", 1),
        ("        Path('/home/loucmane/gas-city-template/templates/claude/candidate-provider.toml')]\n",
         "        Path('/home/loucmane/gas-city-template/templates/claude/candidate-provider.toml'),\n"
         "        Path('/home/loucmane/gas-city-template/bin/gct-claude-template-candidate-worker'),\n"
         "        Path('/home/loucmane/gas-city-template/lib/gct_claude_template_candidate_worker.py'),\n"
         "        Path('/home/loucmane/gas-city-template/templates/claude/template-candidate-control-policy.json'),\n"
         "        Path('/home/loucmane/gas-city-template/templates/claude/template-candidate-provider.toml')]\n", 1),
        ("str(BUILD), str(CANDIDATE_BUILD)):", "str(BUILD), str(CANDIDATE_BUILD), str(TEMPLATE_BUILD)):", 1),
        ("    for build, digest in ((BUILD, BINARY_SHA), (CANDIDATE_BUILD, CANDIDATE_BINARY_SHA)):\n",
         "    for build, digest in ((BUILD, BINARY_SHA), (CANDIDATE_BUILD, CANDIDATE_BINARY_SHA),\n"
         "                          (TEMPLATE_BUILD, TEMPLATE_BINARY_SHA)):\n", 1),
        ("candidate_observation=observations[1],\n",
         "candidate_observation=observations[1],\n                         template_observation=observations[2],\n", 1),
        ("    for root, digest in ((BUILD, BINARY_SHA), (CANDIDATE_BUILD, CANDIDATE_BINARY_SHA)):\n",
         "    for root, digest in ((BUILD, BINARY_SHA), (CANDIDATE_BUILD, CANDIDATE_BINARY_SHA),\n"
         "                         (TEMPLATE_BUILD, TEMPLATE_BINARY_SHA)):\n", 1),
        ("if names != ['gascity/gc.implementation-worker', 'gascity/operations-candidate-worker']:",
         "if names != ['gascity/gc.implementation-worker', 'gascity/operations-candidate-worker',\n"
         "                     'gas-city-template/gc.implementation-worker']:", 1),
        ("for key, expected in (('observation', draft['profiles'][0]), ('candidate_observation', draft['profiles'][1])):",
         "for key, expected in (('observation', draft['profiles'][0]), ('candidate_observation', draft['profiles'][1]),\n"
         "                              ('template_observation', draft['profiles'][2])):", 1),
        ("        write('composition-candidate.json', dict(observation=observation['candidate_observation']))\n",
         "        write('composition-candidate.json', dict(observation=observation['candidate_observation']))\n"
         "        write('composition-template.json', dict(observation=observation['template_observation']))\n", 1),
        ('M10', 'M11', 1),
        ('m10', 'm11', 4),
    ], 'p11-observe-compose.py')
    stale(text, 'p12-observe-compose.py', ('m10', 'M10', 'p11-input', 'p11-compose-20260927'))
    return write('p12-observe-compose.py', header + text)


def readiness_script(compose_sha):
    text = source(P11/'p11-readiness.py', P11_READY_SHA)
    header = '''"""P12 step 3: one native receipt-compatibility/readiness observation of three profiles; no worker or install.

gct-oak5 RECEIPT. Generated by make_p12.py from the executed P11 readiness; the logic is P11's. The normalized and
finalized receipt carries the three profiles with the three moved leaves. The P11 preflight diagnostic (Core
f45a6262, unchanged) runs Core's own start preflight and its exact-profile negative for each profile against its
composition. Also changed: a fresh root, the P12 observer and compositions, the Template candidate policy in the
subscription settings inspection, and the reused P11 preflight sources, read from ga-bebv-deploy/p11.
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("ROOT=Path('%s')" % READY_OLD, "ROOT=Path('%s')" % READY_ROOT, 1),
        ("BASE=HERE/'p11-observe-compose.py'", "BASE=HERE/'p12-observe-compose.py'", 1),
        ("BASE_SHA='%s'" % P11_COMPOSE_SHA, "BASE_SHA='%s'" % compose_sha, 1),
        ("SUCCESSOR=HERE\n", "SUCCESSOR=HERE.parent.parent/'ga-bebv-deploy'/'p11'  # the reused P11 preflight sources\n", 1),
        ("COMPOSITION=Path('%s/composition.json')" % COMPOSE_OLD, "COMPOSITION=Path('%s/composition.json')" % COMPOSE_ROOT, 1),
        ("CANDIDATE_COMPOSITION=Path('%s/composition-candidate.json')\n" % COMPOSE_OLD,
         "CANDIDATE_COMPOSITION=Path('%s/composition-candidate.json')\n"
         "TEMPLATE_COMPOSITION=Path('%s/composition-template.json')\n" % (COMPOSE_ROOT, COMPOSE_ROOT), 1),
        ("CANDIDATE_POLICY=Path('/home/loucmane/gas-city-template/templates/claude/candidate-control-policy.json')\n",
         "CANDIDATE_POLICY=Path('/home/loucmane/gas-city-template/templates/claude/candidate-control-policy.json')\n"
         "TEMPLATE_POLICY=Path('/home/loucmane/gas-city-template/templates/claude/template-candidate-control-policy.json')\n", 1),
        ("        raise RuntimeError('candidate composition record differs')\n"
         "    for actual,expected in ((actual,draft['profiles'][0]),(candidate,draft['profiles'][1])):\n",
         "        raise RuntimeError('candidate composition record differs')\n"
         "    template=json.loads(base.read(TEMPLATE_COMPOSITION))['observation']\n"
         "    if template!=json.loads(base.read(COMPOSITION))['template_observation']:\n"
         "        raise RuntimeError('Template composition record differs')\n"
         "    if len(draft['profiles'])!=3:raise RuntimeError('draft profile cardinality')\n"
         "    for actual,expected in ((actual,draft['profiles'][0]),(candidate,draft['profiles'][1]),\n"
         "                            (template,draft['profiles'][2])):\n", 1),
        ('# The P11 compositions are accepted', '# The P12 compositions are accepted', 1),
        ("subscription.inspect_settings_files([POLICY,CANDIDATE_POLICY])",
         "subscription.inspect_settings_files([POLICY,CANDIDATE_POLICY,TEMPLATE_POLICY])", 1),
        ("        argv += [binary,str(ROOT/'receipt.final.json'),str(CANDIDATE_COMPOSITION),NATIVE_SHA]\n",
         "        argv += [binary,str(ROOT/'receipt.final.json'),str(CANDIDATE_COMPOSITION),NATIVE_SHA]\n"
         "    elif mode in ('negative-template','preflight-template'):\n"
         "        binary={'negative-template':'negative-old-path','preflight-template':'preflight'}[mode]\n"
         "        argv += [binary,str(ROOT/'receipt.final.json'),str(TEMPLATE_COMPOSITION),NATIVE_SHA]\n", 1),
        ("        for mode in ('normalize','finalize','discover','negative-old-path','negative-candidate','subscription',\n"
         "                     'preflight','preflight-candidate'):\n",
         "        for mode in ('normalize','finalize','discover','negative-old-path','negative-candidate',\n"
         "                     'negative-template','subscription','preflight','preflight-candidate','preflight-template'):\n", 1),
    ], 'p11-readiness.py')
    stale(text, 'p12-readiness.py', ('m10', 'M10', 'p11-observe', 'p11-compose-20260927', 'p11-readiness', 'P11 comp'))
    return write('p12-readiness.py', header + text)


def adopt_script(readiness_sha):
    text = source(P11/'p11-adopt.py', P11_ADOPT_SHA)
    header = '''"""P12 step 4: one receipt-only transaction through the unchanged reviewed provisioner.

gct-oak5 RECEIPT. Generated by make_p12.py from the executed P11 adoption; the logic is P11's. These bindings
change: the P12 readiness, the old receipt 06a3f58a, and the M11 accepted-deployment evidence and platform self
digests in the typed-support witness. The Core consumer (gc 207a78e2 from f45a6262, tree f1011ada), the sequence 16
build verification and the traced controller 2800348 are unchanged since P11. The readiness-derived constants stay
None until readiness has passed.
"""
'''
    text = docstring(text, '')
    text = substitute(text, [
        ("NEW_SHA='06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5'\n"
         "NEW_SELF='7363291ef5eae71e3bf422570bb27e69863d37349b9640f52a9e7d2b8f3af487'\n"
         "READY_RESULT_SHA='ebccc14524d7aee8d4002b27f929f05212a7aec429ea6a9a87de3dcfb5af83c7'\n"
         "READY_BEFORE_SHA='71473463cc99906cf0aa6c2255e383c54c6e564a56e4d483998a3b3d1d1b9086'\n"
         "READY_PINS_SHA='82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n",
         "NEW_SHA=None\nNEW_SELF=None\nREADY_RESULT_SHA=None\nREADY_BEFORE_SHA=None\nREADY_PINS_SHA=None\n", 1),
        ("ROOT=Path('%s')" % ADOPT_OLD, "ROOT=Path('%s')" % ADOPT_ROOT, 1),
        ("READY=Path('%s')" % READY_OLD, "READY=Path('%s')" % READY_ROOT, 1),
        ("READY_SOURCE=HERE/'p11-readiness.py'", "READY_SOURCE=HERE/'p12-readiness.py'", 1),
        ("READY_SHA='%s'" % P11_READY_SHA, "READY_SHA='%s'" % readiness_sha, 1),
        ("OLD_SHA='%s'" % RECEIPT_P10, "OLD_SHA='%s'" % RECEIPT_P11, 1),
        ("# Filled from the passed P11 readiness evidence", "# Filled from the passed P12 readiness evidence", 1),
        ('m10', 'm11', 6),
    ], 'p11-adopt.py')
    stale(text, 'p12-adopt.py', ('m10', 'M10', 'p11-', 'P11', RECEIPT_P10))
    return write('p12-adopt.py', header + text)


def scripts():
    if TEMPLATE_COMPOSE_SHA is None:
        raise SystemExit('build the Template diagnostic and pin its digest first')
    input_sha = input_script()
    compose_sha = compose_script(input_sha)
    readiness_sha = readiness_script(compose_sha)
    adopt_script(readiness_sha)
    write('source-launch.py', source(P11/'source-launch.py', LAUNCHER_SHA))
    write('typed-interoperability.json', source(P11/'typed-interoperability.json', TYPED_SHA))


if __name__ == '__main__':
    if sys.argv[1:] == ['diagnostics']:
        diagnostics()
    elif sys.argv[1:] == ['scripts']:
        scripts()
    else:
        raise SystemExit(__doc__)
