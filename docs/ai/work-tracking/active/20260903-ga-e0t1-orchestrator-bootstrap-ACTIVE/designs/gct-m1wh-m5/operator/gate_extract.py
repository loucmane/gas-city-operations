"""Read-only in-window gate extract for the M5 executor reviews (ga-0t04).

  gate_extract.py SOURCE_PASS | PAIRING_PASS | COMMIT_PASS

Writes gate-<kind>-<utc>.json into the staging directory OUT_DIR, never into the package (O_EXCL) and prints its path and digest. It holds:
- every checklist fact from M5-WINDOW-REVIEWS.md, computed from reports/m5/q;
- the exact bindings from the committed record_review.py.
Reviewers must confirm the decisive facts against the originals, so this is a claim, not evidence.
It touches no timer, city, native CLI or Bead.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
PKG = Path(O + '/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-m5')
Q = Path(O + '/reports/m5/q')
# Never inside the package: a new file there would dirty the worktree and stop the executor wrapper.
OUT_DIR = Path('/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922')


def module(path, name):
    value = types.ModuleType(name); value.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), value.__dict__)
    return value


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    return json.loads((Q/name).read_bytes())


recorder = module(PKG/'record_review.py', 'record_review')
runtime = module(PKG/'source_runtime.py', 'source_runtime')
candidate = module(PKG/'manifest_candidate.py', 'manifest_candidate')
o = recorder.observer()
kind = sys.argv[1]
facts = dict(kind=kind, bindings=recorder.bindings(o, kind), package_sha256=sha(Q/'prepared.json'))

if kind == 'SOURCE_PASS':
    p = load('prepared.json')
    expected_sources = {str(runtime.LEGACY/(name + '.py')): digest for name, digest in runtime.PINS.items()}
    pins = json.loads((PKG/'source-pins.json').read_bytes())
    expected_sources.update({str(PKG/name): digest for name, digest in pins.items()})
    m = load('manifest.json')
    inputs = {i['path']: i['sha256'] for i in m['metadata']['inputs']}
    paused = load('preparation-paused.json')
    facts.update(
        flags={k: p.get(k) for k in ('preparation_only', 'live_acceptance', 'timer_paused', 'native_launched')},
        accepted_recovery_sha256=p['accepted_recovery_sha256'], baseline_pin=candidate.BASELINE_SHA,
        broker_receipt_sha256=p['broker_receipt_sha256'], candidate_receipt_sha=candidate.RECEIPT_SHA,
        timing=p['timing'], sources_count=len(p['sources']), sources_equal_expected=p['sources'] == expected_sources,
        source_mismatches=sorted(set(p['sources'].items()) ^ set(expected_sources.items())),
        manifest_file_sha256=sha(Q/'manifest.json'), prepared_manifest_file_sha256=p['manifest_file_sha256'],
        release_id=m['release_id'], previous_manifest=m['previous_metadata']['manifest_sha256'],
        last_repository=m['integrity']['repositories'][-1],
        counts={k: len(m['metadata'][k]) for k in ('inputs', 'trees', 'links')},
        changed_inputs={path: inputs.get(path) == new for path, _, new in candidate.CHANGED_INPUTS},
        python_test_inputs=sum(path.startswith(candidate.TEST_PREFIX) for path in inputs),
        evidence=m['metadata']['evidence'],
        closure_exists=(Q/'preparation-closure.json').exists(),
        paused_binds_closure=paused['closure_sha256'] == sha(Q/'preparation-closure.json'),
        paused_binds_intent=paused['intent_sha256'] == sha(Q/'preparation-pause-intent.json'),
        paused_binds_command=paused['command_sha256'] == sha(Q/'preparation-pause-command.json'),
        stop_returncode=load('preparation-pause-command.json')['returncode'],
        deadline=paused['deadline'])
elif kind == 'PAIRING_PASS':
    r = load('observe-result.json')
    lines = r['stdout'].splitlines()
    steps = [line.split(None, 3) for line in lines if re.match(r'^\d\d (CHECK|MUTATE) \S+ path=', line)]
    unparsed = [line for line in lines[1:] if not re.match(r'^\d\d (CHECK|MUTATE) \S+ path=', line)]
    mutate = [s for s in steps if s[1] == 'MUTATE']
    platform = '/home/loucmane/gascity/city/.gc/platform/'
    # Exactly these four MUTATE actions, each once, each on its own target, and nothing else.
    expected_mutations = {
        'write-previous-manifest-backup': O + '/reports/m5/b/install-manifest.before.json',
        'write-previous-receipt-backup': O + '/reports/m5/b/install-receipt.before.json',
        'publish-manifest': platform + 'install-manifest.json',
        'write-activation-receipt': platform + 'install-receipt.json',
    }
    observed_mutations = {s[2]: s[3].split()[0][len('path='):] for s in mutate}
    window = load('window.json')
    paused = load('preparation-paused.json')
    facts.update(
        observe={k: r[k] for k in ('phase', 'exit_code', 'terminal_pidfd', 'errors', 'record_error', 'stderr', 'argv')},
        plan_header=r['stdout'].splitlines()[0] if r['stdout'] else None,
        step_count=len(steps), mutate_steps=[' '.join(s) for s in mutate],
        mutate_only_allowed=len(mutate) == 4 and observed_mutations == expected_mutations,
        unparsed_plan_lines=unparsed,
        check_actions=sorted({s[2] for s in steps if s[1] == 'CHECK'}),
        after_observation=load('after-observation.json'),
        after_matches=load('after-observation.json') == dict(
            ok=True, observation_result_sha256=sha(Q/'observe-result.json'),
            window_sha256=sha(Q/'window.json'), complete_preservation=True),
        observe_baseline_is_window=r.get('baseline_sha256') == sha(Q/'window.json'),
        window_deadline_equals_prepared=window.get('deadline') == paused['deadline'],
        window_closure_equals_preparation=window.get('closure') == load('preparation-closure.json'),
        no_later_records=not any((Q/(ph + sfx)).exists() for ph in ('probe', 'probe2', 'commit')
                                 for sfx in ('-consumed.json', '-result.json')))
elif kind == 'COMMIT_PASS':
    a = load('committed-acceptance.json')
    c = load('commit-result.json')
    city = Path('/home/loucmane/gascity/city/.gc/platform')
    facts.update(
        acceptance={k: a[k] for k in a if k not in ('binding',)},
        acceptance_package_is_prepared=a['package_sha256'] == sha(Q/'prepared.json'),
        acceptance_binds_commit_result=a['commit_result_sha256'] == sha(Q/'commit-result.json'),
        commit_result={k: c.get(k) for k in ('phase', 'exit_code', 'terminal_pidfd', 'errors', 'record_error',
                                              'stderr', 'argv')},
        live_manifest_file=sha(city/'install-manifest.json'), live_receipt_file=sha(city/'install-receipt.json'),
        live_manifest_equals_q_manifest=json.loads((city/'install-manifest.json').read_bytes()) == load('manifest.json'),
        restore_absent=not any((Q/n).exists() for n in ('restore-consumed.json', 'restored.json')))
else:
    raise SystemExit(__doc__)

stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out = OUT_DIR/('gate-%s-%s.json' % (kind.lower().replace('_', '-'), stamp))
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
with os.fdopen(fd, 'w') as stream:
    json.dump(facts, stream, indent=1, sort_keys=True, default=str)
    stream.write('\n')
print(out, sha(out))
