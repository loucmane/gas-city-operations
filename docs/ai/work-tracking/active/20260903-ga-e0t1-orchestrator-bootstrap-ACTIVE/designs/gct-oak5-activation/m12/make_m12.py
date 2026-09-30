"""Generate the M12 package files from the reviewed, executed M11 package by count-checked substitutions.

  python3 -I -B make_m12.py

manifest_candidate.py is written by hand (the M12 delta is the city-config pattern alone); everything else is
derived here from designs/gct-oak5-activation/m11 at its reviewed digests:
- capture_m12.py: the M11 capture against the frozen M11 baseline (4000f7f3, 773 pins, 50 trees), with exactly
  two admitted pin changes (the P12 worker receipt 06a3f58a -> 7125be84 and city.toml b0eeb168 -> bdcec254), the
  unchanged suspension record a3306567, and one rule change: a pinned repository marked allow_dirty (M11's
  canonical Template authority) is not required to have an empty status; its exact untracked set is proven by the
  canonical checkout check instead;
- prereqs_m12.py: the M11 prerequisite, rebound (writes reports/m12-inputs/city.toml from the installed bdcec254);
- record_review.py and operator/gate_extract.py: rebound to reports/m12 and staging gct-oak5-m12;
- operator/GATE-PROMPTS.md: rebound, with the SOURCE_PASS checklist rewritten for the M12 delta;
- the executor sources (source_runtime, launch, metadata_executor, metadata_window, metadata_closure): byte-identical.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
M11 = HERE.parent/'m11'
SOURCES = {
    'capture_m11.py': '57ef98293d8c4b05e699a2c9a11f0e50c2886334a34f94058958c125e81c1fd7',
    'prereqs_m11.py': '60ab61fce2f27a7bbc78f38aa325e5fa3e43f4042be9f68d573b5c9440ac42f5',
    'record_review.py': 'e53ef93134c266d3a16a61aa5d7390e35a6b2cbf28297b2fcc5342c9af53efca',
    'operator/gate_extract.py': '711453e9045561824e6c319501eb5a2879b771bc7616c980646f788c61a2608e',
    'operator/GATE-PROMPTS.md': 'dd214dde8c33ad7a82f99b33f1748db796eb8c5abb6e5ff711e6b0a8e658bb82',
}
IDENTICAL = {
    'source_runtime.py': '2585357a808d8f36604d4bf45a39a5363ba87c8d719413ba42d9fd0fac71973f',
    'launch.py': '43ad2ac9b73ac3378c38d7502ccf222c8fe36a379f2951a77b8e9ca5c3006735',
    'metadata_executor.py': '5a6694ab4e706376d4da1197a4f575961547174c3bdd7351250d909038d84125',
    'metadata_window.py': '57778022e3d9ea512ded102179d0a9a1c9d0137d70eaa20501fb21364683ec54',
    'metadata_closure.py': 'ce310593418e30b89f08645824c6cdd5b700fcff60b12f688fffc3d42d31d5d8',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source(name, digest=None):
    raw = (M11/name).read_bytes()
    if digest is not None and sha(raw) != digest:
        raise SystemExit('reviewed source drift: %s' % name)
    return raw.decode()


def substitute(text, substitutions, name):
    for old, new, count in substitutions:
        found = text.count(old)
        if found != count:
            raise SystemExit('%s: expected %d occurrence(s) of %r, found %d' % (name, count, old[:80], found))
        text = text.replace(old, new)
    return text


def stale(text, name, tokens):
    for token in tokens:
        if token in text:
            raise SystemExit('%s: stale token %r remains' % (name, token))


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


CAPTURE_DOC = '''"""M12 baseline capture (gct-oak5 codex choice). Read-only except its own record under reports/m12-capture.

  python3 -I -B capture_m12.py <manifest_candidate.py sha256>

Runs in the supervisor host namespaces as UID 1000, after the reviewed A2 codex-choice activation (cdcdaccd,
applied f17c55a9) and the M12 input prerequisite (prereqs_m12.py), and before any M12 preparation. The reference is
the frozen M11 baseline (reports/m11-capture/baseline.json 4000f7f3, 773 pins, 50 trees), which the M11 executor
accepted. Since then exactly these reviewed changes touched what it holds, each admitted only as its exact
before -> after pair:
- P12 (gct-oak5): the worker receipt .gc/runtime/provisioning/receipt.json 06a3f58a -> 7125be84;
- A2: city.toml b0eeb168 -> bdcec254.
The suspension record is unchanged (a3306567), and the city and every one of the seven rigs are still suspended.
Every other M11-baseline pin, tree, protected tree and link, the scope and the host must be exact; the cache must be
exact apart from the Git bookkeeping times cache_drift admits. Every M12 target pin (including the new city source)
is exact, the installed pair is M11, the canonical checkout is 3474abfa with exactly its two known untracked
directories, and the sequence 16 receipt is the root-custodied 1108b724. A pinned repository marked allow_dirty
(M11's canonical Template authority) is not required to have an empty status; the canonical checkout check proves
its exact untracked set. From the capture until restore-accepted nobody runs gc, workflow.py, a Bead write or git
in a pinned repository.
"""
'''


def capture():
    text = docstring(source('capture_m11.py', SOURCES['capture_m11.py']), '')
    # Generic renames first, so every specific substitution below is written in its post-rename form.
    text = substitute(text, [('M11', 'M12', 4), ('M10', 'M11', 9), ('m11', 'm12', 5), ('m10', 'm11', 4)], 'capture_m11.py')
    text = substitute(text, [
        ("REFERENCE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m11-capture/baseline.json')\n"
         "REFERENCE_SHA = 'fc9ee176706faf43e94f409a7a8df728eb6521f6e6f4d7115b1080865d333118'\n"
         "REFERENCE_TREES = 49\n"
         "REFERENCE_PINS = 769\n",
         "REFERENCE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m11-capture/baseline.json')\n"
         "REFERENCE_SHA = '4000f7f3d37a2a572fc210ba201f0b6dedb08661f0c878c896f34a0426548a97'\n"
         "REFERENCE_TREES = 50\n"
         "REFERENCE_PINS = 773\n", 1),
        ("# The exact reviewed pin changes since the M11 baseline: path -> (M11 baseline sha256, current sha256).\n"
         "CITY = '/home/loucmane/gascity/city'\n"
         "PIN_CHANGES = {\n"
         "    CITY + '/.gc/runtime/provisioning/receipt.json': ('c833908fe89ab180e57ef7164d687f01ae2052f8667360f04b73c5423902f0a4',\n"
         "                                                      '06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5'),\n"
         "    CITY + '/city.toml': ('e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077',\n"
         "                          'b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b'),\n"
         "    CITY + '/managed/rig-permissions.json': ('1225b7c57ae69fd068ea35117431ae05e09ee493c01bc11a46ac45b77b950c8e',\n"
         "                                             '0b0e6a87ee19f6e3a2e440d7389cc6abf28e1fabd1b08a892adab0f6c435df00'),\n"
         "    CITY + '/managed/rig-permissions.toml': ('df688a29446cb381b734847ec9a255e470c710498cbfe2b713a9e85b052575a5',\n"
         "                                             'df9c82d0c1b22a4b0024a912c0abb980396d6765f45c597ddb9c6b4b649c5530'),\n"
         "}\n"
         "SUSPENSION_BEFORE = '6d89f53738fbae8a2f07c7026de61207704ed44bbde79c0fc1f3a1d18b166ee0'\n",
         "# The exact reviewed pin changes since the M11 baseline: path -> (M11 baseline sha256, current sha256).\n"
         "CITY = '/home/loucmane/gascity/city'\n"
         "PIN_CHANGES = {\n"
         "    CITY + '/.gc/runtime/provisioning/receipt.json': ('06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5',\n"
         "                                                      '7125be84548a587e2d784d423a85cd6750f4b5087cfc8c4acbbc087ff1e79579'),\n"
         "    CITY + '/city.toml': ('b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b',\n"
         "                          'bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1'),\n"
         "}\n"
         "SUSPENSION_BEFORE = 'a3306567b3cf77e6371a870e6df239194574fab8f2dc3090ea55a5eeb14b4817'\n", 1),
        ("        if head['stdout'].strip() != repo['commit'] or status['returncode'] != 0 or status['stdout']:\n",
         "        # An allow_dirty authority (M11's canonical Template) may carry its known untracked directories; the\n"
         "        # canonical checkout check below proves its exact status.\n"
         "        if (head['stdout'].strip() != repo['commit'] or status['returncode'] != 0\n"
         "                or (status['stdout'] and not repo.get('allow_dirty'))):\n", 1),
        ("    require(reference['schema'] == 'ga-bebv.m11-baseline.v1' and not reference['drifts'],\n",
         "    require(reference['schema'] == 'gct-oak5.m11-baseline.v1' and not reference['drifts'],\n", 1),
    ], 'capture_m11.py')
    stale(text, 'capture_m12.py', ('m10', 'M10', 'c833908f', '6d89f537', 'fc9ee176', 'ga-bebv.m1'))
    return write('capture_m12.py', CAPTURE_DOC + text)


def prereqs():
    text = source('prereqs_m11.py', SOURCES['prereqs_m11.py'])
    text = substitute(text, [
        ('"""M11 input prerequisite', '"""M12 input prerequisite', 1),
        ('Core\'s metadata-only adoption requires the managed file already installed (the gct-oak5 activation installed\n'
         'city.toml b0eeb168)', 'Core\'s metadata-only adoption requires the managed file already installed (the A2 codex-choice\n'
         'activation installed city.toml bdcec254)', 1),
        ('This writes reports/m11-inputs/city.toml exactly\nonce (O_EXCL, 0644) from the installed bytes, after proving the '
         'installed file and the M10 source that becomes the\npredecessor backup.',
         'This writes reports/m12-inputs/city.toml exactly\nonce (O_EXCL, 0644) from the installed bytes, after proving the '
         'installed file and the M11 source that becomes the\npredecessor backup.', 1),
        ('m11-inputs already exists', 'm12-inputs already exists', 1),
        ('prereqs_m11.py', 'prereqs_m12.py', 2),
        ("'m11_candidate'", "'m12_candidate'", 1),
    ], 'prereqs_m11.py')
    stale(text, 'prereqs_m12.py', ('m10', 'M10', 'm11', 'M11 input', 'b0eeb168'))
    return write('prereqs_m12.py', text)


def recorder():
    text = source('record_review.py', SOURCES['record_review.py'])
    text = substitute(text, [
        ('"""M11 in-window review recorder (gct-oak5 Template lane): the reviewed M5-M10 recorder with only its two paths moved.',
         '"""M12 in-window review recorder (gct-oak5 codex choice): the reviewed M5-M11 recorder with only its two paths moved.', 1),
        ('reports/m11', 'reports/m12', 4),
    ], 'record_review.py')
    stale(text, 'record_review.py', ('m11', 'M11 in-window'))
    return write('record_review.py', text)


def extract():
    text = source('operator/gate_extract.py', SOURCES['operator/gate_extract.py'])
    text = substitute(text, [
        ('"""Read-only in-window gate extract for the M11 executor reviews (gct-oak5 Template lane); the M5-M10 extract, rebound.',
         '"""Read-only in-window gate extract for the M12 executor reviews (gct-oak5 codex choice); the M5-M11 extract, rebound.', 1),
        ("designs/gct-oak5-activation/m11')", "designs/gct-oak5-activation/m12')", 1),
        ('reports/m11', 'reports/m12', 4),
        ('gct-oak5-m11', 'gct-oak5-m12', 1),
    ], 'gate_extract.py')
    stale(text, 'gate_extract.py', ('m11', 'M11 executor'))
    return write('operator/gate_extract.py', text)


SOURCE_CHECKLIST_OLD_START = '   - release_id gct-oak5-template-candidate-lane-metadata-m11-20260927;\n'
SOURCE_CHECKLIST_OLD_END = '   - cache_sha256 4b284f67...;\n'
SOURCE_CHECKLIST_NEW = '''   - release_id gct-oak5-codex-candidate-choice-metadata-m12-20260927;
   - previous_manifest 9f60c3bf...;
   - last_repository template-pr72-canonical: path /home/loucmane/gas-city-template, commit
     3474abfaec255f7ea4266ce8aa35218afcfc89b0, allow_dirty true (unchanged since M11);
   - previous_image previous_sha256 207a78e2... with backup_path /var/tmp/ga-bebv-build-20260927/gc-b;
   - counts 692/50/23;
   - every changed_inputs value true (city.toml and reports/m12-inputs/city.toml bdcec254);
   - superseded_inputs_moved true for reports/m10-inputs/city.toml;
   - removed_inputs_absent, new_trees, exact_trees and integrity_files_changed empty;
   - template_provider one entry: name claude, path and resolved_path
     /home/loucmane/gas-city-template/bin/gct-claude-template-candidate-worker, sha256 229d3355... (unchanged);
   - providers claude-native, codex and the three "claude" wrappers (signing, Operations candidate, Template);
   - city_config one entry: source reports/m12-inputs/city.toml, destination /home/loucmane/gascity/city/city.toml,
     sha256 bdcec254..., previous_sha256 b0eeb168..., backup_path reports/m11-inputs/city.toml, mode 420;
   - core source /var/tmp/ga-bebv-build-20260927/gc-a with sha 207a78e2... (unchanged);
   - activation expected_commit and previous_commit both f45a6262...;
   - writer sha 207a78e2...;
   - cache_sha256 4b284f67...;
'''


def prompts():
    text = source('operator/GATE-PROMPTS.md', SOURCES['operator/GATE-PROMPTS.md'])
    start = text.index(SOURCE_CHECKLIST_OLD_START)
    end = text.index(SOURCE_CHECKLIST_OLD_END) + len(SOURCE_CHECKLIST_OLD_END)
    # The M11 checklist is cut out first; the renames run on the rest; the M12 checklist goes in last, verbatim.
    text = text[:start] + '@@CHECKLIST@@\n' + text[end:]
    text = substitute(text, [
        ('# M11 in-window gate prompts (gct-oak5 Template lane)', '# M12 in-window gate prompts (gct-oak5 codex choice)', 1),
        ('These are the M5\u2013M10 gate prompts, rebound to M11.', 'These are the M5\u2013M11 gate prompts, rebound to M12.', 1),
        ('   - Q/manifest.json has "release_id":"gct-oak5-template-candidate-lane-metadata-m11-20260927", a\n'
         '     previous_sha256 starting 207a78e2, the city-config source reports/m11-inputs/city.toml with b0eeb168, and\n',
         '   - Q/manifest.json has "release_id":"gct-oak5-codex-candidate-choice-metadata-m12-20260927", a\n'
         '     previous_sha256 starting 207a78e2, the city-config source reports/m12-inputs/city.toml with bdcec254, and\n', 1),
        ('gct-oak5-template-candidate-lane-metadata-m11-20260927', 'gct-oak5-codex-candidate-choice-metadata-m12-20260927', 1),
        ('reports/m11', 'reports/m12', 6),
        ('gct-oak5-activation/m11', 'gct-oak5-activation/m12', 2),
        ('gct-oak5-m11', 'gct-oak5-m12', 1),
        ('M11', 'M12', 5),
    ], 'GATE-PROMPTS.md')
    stale(text, 'GATE-PROMPTS.md', ('m11', 'M11', 'aff9b9b3', '2b902a83', 'b0eeb168'))
    text = substitute(text, [('@@CHECKLIST@@\n', SOURCE_CHECKLIST_NEW, 1),
                             ('M5\u2013M12 gate prompts', 'M5\u2013M11 gate prompts', 1)], 'GATE-PROMPTS.md')
    return write('operator/GATE-PROMPTS.md', text)


def main():
    for name, digest in IDENTICAL.items():
        write(name, source(name, digest))
    capture()
    prereqs()
    recorder()
    extract()
    prompts()


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    main()
