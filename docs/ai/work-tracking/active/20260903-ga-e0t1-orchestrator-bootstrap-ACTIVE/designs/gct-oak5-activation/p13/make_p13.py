"""Generate the P13 worker receipt revision refresh (gct-oak5) from the executed P12 chain by count-checked substitutions.

  python3 -I -B make_p13.py

The installed worker receipt 7125be84 (P12) carries three profiles and permission revision 06076790. The reviewed A2
codex-choice activation (cdcdaccd, applied f17c55a9) changed city.toml, and the controller now traces revision
a61666b3 (the A2 reload acknowledgement). M12 adopted that city.toml into the platform metadata (file 114b4a00).
P13 moves exactly one leaf, permission_revision 06076790 -> a61666b3, through the unchanged reviewed provisioner.
Every profile, Core f45a6262, the Template 3474abfa, the pack, the rules and the canary runner are asserted
unchanged, and all three compositions are re-proven live. No diagnostic is rebuilt: the P11 signing, Operations
candidate and preflight builds and the P12 Template build are reused by digest.

The installed receipt lists its profiles sorted by name (the provisioner sorts), so derive() takes them by name and
returns them in the P12 input order (signing, Operations candidate, Template); the observer and readiness compare
index by index in that order, and the provisioner sorts again.
"""
import hashlib
import sys
import types
from pathlib import Path

HERE = Path(__file__).parent
P12 = HERE.parent/'p12'

P12_INPUT_SHA = 'a9d514edfe9983b01ef32d774280e75c04daac25428b15700b0fde4d6706c77d'
P12_COMPOSE_SHA = 'b9ef1cd0429c6d2519d3aafe911655382bcc76ee395796fe1816cd19f2093cce'
P12_READY_SHA = 'bcef93bfc9030bc8c52bece12a88fd5644aa97b41780f44c1446d17a6cdc1cc6'
P12_ADOPT_SHA = '935c155f5326f507ae7315a57c9aacc30e052a0dfc94204521321c1c3972db5b'
P12_MAKE_SHA = '67cc8af33eb86f0bd2a2117935f7e5a4e0fa274dced5e0a6d57eb43f48845bf8'  # the committed make_p12.py (its DERIVE_P12 is the text P13 replaces)
LAUNCHER_SHA = '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'
TYPED_SHA = '315dd4109310c13038c7fbcc4cc17f8b791721fbc343133d286dc21ee5776563'

RECEIPT_P11 = '06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5'
RECEIPT_P12 = '7125be84548a587e2d784d423a85cd6750f4b5087cfc8c4acbbc087ff1e79579'
REVISION_P11 = '03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712'
REVISION_P12 = '06076790c31448212545edc1e741f592ed5b23ac54debbefb5e6da847143d753'
REVISION = 'a61666b33528c1cb8b497f55d9c6b8b37df2ce74ed9853345de8d7321e18f58f'
TEMPLATE_OLD = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
TEMPLATE = '3474abfaec255f7ea4266ce8aa35218afcfc89b0'
M10_FILE, M11_FILE = ('2b902a83577acf71f9dd93a97d43d8478f7c4b291b0992e8ba5a5e44fe66f7f2',
                      '9f60c3bf69a64e3483b2a069fd542ae4ddefee5c0e63f1bc06a388ab7f59a1be')

READY_P12 = ("NEW_SHA='7125be84548a587e2d784d423a85cd6750f4b5087cfc8c4acbbc087ff1e79579'\n"
             "NEW_SELF='4204aef000474e1d877cc197e477fe34175e94b342fe055a0d6ae24ebe322175'\n"
             "READY_RESULT_SHA='eaabc9f35dddb5a634e982441284010f8b6ebc1ac807b1c6ab20cee741ad11b7'\n"
             "READY_BEFORE_SHA='ffecfc13d9762e83c627087f47f7eaf740045590be53898294d453c2635b2a26'\n"
             "READY_PINS_SHA='82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n")


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


def stale(text, name, tokens):
    for token in tokens:
        if token in text:
            raise SystemExit('%s: stale token %r remains' % (name, token))


def p12_generator():
    raw = source(P12/'make_p12.py', P12_MAKE_SHA).encode()
    module = types.ModuleType('make_p12'); module.__file__ = str(P12/'make_p12.py')
    exec(compile(raw, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module


DERIVE_P13 = '''def derive(receipt, revision):
    """Pure: the receipt input for the M12 state, with every predecessor asserted."""
    draft = copy.deepcopy(receipt)
    for key in GENERATED:
        require(key in draft, 'generated field missing: ' + key)
        draft.pop(key)
    require(len(draft['profiles']) == 3, 'profile cardinality')
    for each in draft['profiles']:
        require('worker_profile_sha256' in each, 'generated profile digest missing')
        each.pop('worker_profile_sha256')
    # The installed receipt is sorted by name; take the profiles by name.
    by_name = {each['name']: each for each in draft['profiles']}
    require(len(by_name) == 3, 'profile names')
    profile = by_name.get('gascity/gc.implementation-worker')
    require(profile is not None and profile['profile_kind'] == 'signing', 'signing profile predecessor')
    require(by_name.get(CANDIDATE['name']) == CANDIDATE, 'candidate profile unchanged')
    require(by_name.get(TEMPLATE_CANDIDATE['name']) == TEMPLATE_CANDIDATE, 'Template profile unchanged')
    require(profile['provider']['version'] == VERSION, 'provider version unchanged')
    argv = profile['argv']
    positions = [i for i, token in enumerate(argv) if token == '--model']
    require(len(positions) == 1 and argv[positions[0] + 1] == MODEL, 'argv model unchanged')
    cores = [h for h in draft['member_heads'] if h['name'] == 'core']
    require(len(cores) == 1 and cores[0]['commit'] == CORE, 'core member head unchanged')
    require(draft['template_commit'] == TEMPLATE, 'template unchanged')
    heads = [h for h in draft['member_heads'] if h['name'] == 'template']
    require(len(heads) == 1 and heads[0]['commit'] == TEMPLATE, 'template member head unchanged')
    # The one change. The A2 codex-choice activation moved the composed revision to the exact value the controller
    # traced on 2026-09-27 (M12 adopted the city.toml).
    require(draft['permission_revision'] == REVISION_OLD and revision == REVISION, 'revision predecessor')
    draft['permission_revision'] = revision
    # The P12 input order; the provisioner sorts by name again.
    draft['profiles'] = [profile, by_name[CANDIDATE['name']], by_name[TEMPLATE_CANDIDATE['name']]]
    return draft
'''

INPUT_DOC = '''"""P13 step 1: observe the running revision and derive the receipt input. Read-only except its own records.

gct-oak5 RECEIPT. Generated by make_p13.py from the executed P12 input; the logic is P12's. The installed receipt
7125be84 minus its generated fields becomes the input draft. Exactly one leaf changes: the permission revision
06076790 -> a61666b3 (the A2 codex-choice activation, traced live from the controller). All three profiles (taken by
name from the sorted receipt and returned in the P12 input order), Core f45a6262, the Template 3474abfa, the
signing provider version d4e57767 and the argv model claude-opus-5-5 are asserted unchanged, and all three live
wrappers must report their pinned versions. `m12_acceptance()` verifies M12's reviewed records and that the live
metadata pair is the accepted M12 pair succeeding the M11 file 9f60c3bf.

  python3 -I -S -B source-launch.py p13-input.py <own sha256>
"""
'''


def input_script():
    derive_p12 = p12_generator().DERIVE_P12
    text = docstring(source(P12/'p12-input.py', P12_INPUT_SHA), '')
    text = substitute(text, [(derive_p12, DERIVE_P13, 1)], 'p12-input.py')
    # Generic renames first; every fix-up below is written in its post-rename form.
    text = substitute(text, [('M11', 'M12', 22), ('m11', 'm12', 11)], 'p12-input.py')
    text = substitute(text, [
        ("ROOT = Path('/var/tmp/gct-oak5-p12-input-20260927')", "ROOT = Path('/var/tmp/gct-oak5-p13-input-20260927')", 1),
        ("RECEIPT_OLD_SHA = '%s'" % RECEIPT_P11, "RECEIPT_OLD_SHA = '%s'" % RECEIPT_P12, 1),
        ("TEMPLATE_OLD = '%s'\nTEMPLATE = '%s'" % (TEMPLATE_OLD, TEMPLATE), "TEMPLATE = '%s'" % TEMPLATE, 1),
        ("REVISION_OLD = '%s'\nREVISION = '%s'" % (REVISION_P11, REVISION_P12),
         "REVISION_OLD = '%s'\nREVISION = '%s'" % (REVISION_P12, REVISION), 1),
        ("M12_RELEASE = 'gct-oak5-template-candidate-lane-metadata-m12-20260927'",
         "M12_RELEASE = 'gct-oak5-codex-candidate-choice-metadata-m12-20260927'", 1),
        ("# Its provider is the M12-pinned wrapper", "# Its provider is the M11-pinned wrapper", 1),
        ("# The succession link is previous_metadata.manifest_sha256, the M10 canonical FILE digest.",
         "# The succession link is previous_metadata.manifest_sha256, the M11 canonical FILE digest.", 1),
        ("PREVIOUS_MANIFEST_FILE = '%s'" % M10_FILE, "PREVIOUS_MANIFEST_FILE = '%s'" % M11_FILE, 1),
        ('For later P12 steps', 'For later P13 steps', 1),
    ], 'p12-input.py')
    stale(text, 'p13-input.py', ('m11', 'M11_', 'M10', 'P12 steps', 'p12', TEMPLATE_OLD, RECEIPT_P11, REVISION_P11, M10_FILE))
    return write('p13-input.py', INPUT_DOC + text)


COMPOSE_DOC = '''"""P13 step 2: one nonlaunching read-only composition observation of three profiles; no receipt installation.

gct-oak5 RECEIPT. Generated by make_p13.py from the executed P12 observer; the logic is P12's. In one read-only
namespace it runs the reused signing, Operations candidate and Template composition diagnostics (Core f45a6262), and
each observation must equal the draft profile of the same name: the argv, the environment and the revision. Also
changed: a fresh root, the P13 input, the M12 metadata pair and the policy module path (the byte-identical M12 copy
of metadata_closure.py).
"""
'''


def compose_script(input_sha):
    text = docstring(source(P12/'p12-observe-compose.py', P12_COMPOSE_SHA), '')
    text = substitute(text, [
        ("ROOT = Path('/var/tmp/gct-oak5-p12-compose-20260927')", "ROOT = Path('/var/tmp/gct-oak5-p13-compose-20260927')", 1),
        ("INPUT_SOURCE = HERE/'p12-input.py'", "INPUT_SOURCE = HERE/'p13-input.py'", 1),
        ("INPUT_SHA = '%s'" % P12_INPUT_SHA, "INPUT_SHA = '%s'" % input_sha, 1),
        ('M11', 'M12', 1),
        ('m11', 'm12', 5),
    ], 'p12-observe-compose.py')
    stale(text, 'p13-observe-compose.py', ('m11', 'M11', 'p12-input', 'p12-compose-2'))
    return write('p13-observe-compose.py', COMPOSE_DOC + text)


READY_DOC = '''"""P13 step 3: one native receipt-compatibility/readiness observation of three profiles; no worker or install.

gct-oak5 RECEIPT. Generated by make_p13.py from the executed P12 readiness; the logic is P12's. The normalized and
finalized receipt carries the three unchanged profiles with the one moved leaf. The reused P11 preflight diagnostic
(Core f45a6262) runs Core's own start preflight and its exact-profile negative for each profile against its
composition. Also changed: a fresh root and the P13 observer and compositions.
"""
'''


def readiness_script(compose_sha):
    text = docstring(source(P12/'p12-readiness.py', P12_READY_SHA), '')
    text = substitute(text, [
        ("BASE_SHA='%s'" % P12_COMPOSE_SHA, "BASE_SHA='%s'" % compose_sha, 1),
        ('p12', 'p13', 5),
        ('# The P12 compositions are accepted', '# The P13 compositions are accepted', 1),
    ], 'p12-readiness.py')
    stale(text, 'p13-readiness.py', ('p12', 'P12', 'm11'))
    return write('p13-readiness.py', READY_DOC + text)


ADOPT_DOC = '''"""P13 step 4: one receipt-only transaction through the unchanged reviewed provisioner.

gct-oak5 RECEIPT. Generated by make_p13.py from the executed P12 adoption; the logic is P12's. These bindings change:
the P13 readiness, the old receipt 7125be84, and the M12 accepted-deployment evidence and platform self digests in
the typed-support witness. The Core consumer (gc 207a78e2 from f45a6262, tree f1011ada), the sequence 16 build
verification and the traced controller 2800348 are unchanged. The readiness-derived constants stay None until
readiness has passed.
"""
'''


def adopt_script(readiness_sha):
    text = docstring(source(P12/'p12-adopt.py', P12_ADOPT_SHA), '')
    text = substitute(text, [
        (READY_P12, "NEW_SHA=None\nNEW_SELF=None\nREADY_RESULT_SHA=None\nREADY_BEFORE_SHA=None\nREADY_PINS_SHA=None\n", 1),
        ("READY_SHA='%s'" % P12_READY_SHA, "READY_SHA='%s'" % readiness_sha, 1),
        ("OLD_SHA='%s'" % RECEIPT_P11, "OLD_SHA='%s'" % RECEIPT_P12, 1),
        ('p12', 'p13', 3),
        ('# Filled from the passed P12 readiness evidence', '# Filled from the passed P13 readiness evidence', 1),
        ('m11', 'm12', 6),
    ], 'p12-adopt.py')
    stale(text, 'p13-adopt.py', ('p12', 'P12', 'm11', RECEIPT_P11))
    return write('p13-adopt.py', ADOPT_DOC + text)


def main():
    input_sha = input_script()
    compose_sha = compose_script(input_sha)
    readiness_sha = readiness_script(compose_sha)
    adopt_script(readiness_sha)
    write('source-launch.py', source(P12/'source-launch.py', LAUNCHER_SHA))
    write('typed-interoperability.json', source(P12/'typed-interoperability.json', TYPED_SHA))


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    main()
