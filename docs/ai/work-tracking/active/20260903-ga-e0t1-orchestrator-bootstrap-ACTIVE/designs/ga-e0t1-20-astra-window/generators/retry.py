"""Create-only r4 worker-window assembly after the proven r3 restoration.

This authoring overlay does not execute a package, clear a latch or repeat a
completed operation. Historical r3 and recovery packages stay reproducible.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys

import build
import successor

PARSER_REVIEW = '04408abe73d844a5731724fd1561a1e264865197'
CONSUMED_ATTEMPT = 'cdf7e3784d18358e099c444b48bf43387f9175a7'
RECOVERY = '524f1a3da16b60cc1a036f9e0f681cd3157b2d25'
PRIOR_TERMINAL = '/var/tmp/ga-e0t1.20-terminal-20260928-r3'
PRIOR_OBSERVATION_SHA = '9c2cf3244c5b922c9845c1a06d56e6ed9ef87e2ce8fcaacce67ee2ec566541ed'
PRIOR_RESULT_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
ROOTS = {
    'ga-e0t1.20-window-20260928-r3': 'ga-e0t1.20-window-20260928-r4',
    'ga-e0t1.20-window-obs-20260928-r3': 'ga-e0t1.20-window-obs-20260928-r4',
    'ga-e0t1.20-integrity-20260928-r5': 'ga-e0t1.20-integrity-20260928-r6',
    'ga-e0t1.20-audit-%s-20260928-r3': 'ga-e0t1.20-audit-%s-20260928-r4',
    'ga-e0t1.20-audit-route-20260928-r3': 'ga-e0t1.20-audit-route-20260928-r4',
    'ga-e0t1.20-audit-resume-20260928-r3': 'ga-e0t1.20-audit-resume-20260928-r4',
    'ga-e0t1.20-terminal-20260928-r3': 'ga-e0t1.20-terminal-20260928-r4',
    'ga-e0t1.20-candidate-inspection-20260928-r3': 'ga-e0t1.20-candidate-inspection-20260928-r4',
    'ga-e0t1.20-startup-release-20260928-r3': 'ga-e0t1.20-startup-release-20260928-r4',
    'ga-e0t1.20-r3-close-session.json': 'ga-e0t1.20-r4-close-session.json',
    'ga-e0t1.20-r3-close-drain.requested': 'ga-e0t1.20-r4-close-drain.requested',
    'ga-e0t1.20-r3-close-': 'ga-e0t1.20-r4-close-',
    'ga-e0t1.20-r3-hold-': 'ga-e0t1.20-r4-hold-',
    'ga-e0t1.20-r3-watch-': 'ga-e0t1.20-r4-watch-',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def assemble(cache_ns):
    assert type(cache_ns) is int and cache_ns >= successor.CACHE_NS, 'cache pin'
    reviewed = build.git('show', PARSER_REVIEW + ':' + build.NEW + '/generators/contract.py')
    assert (build.HERE/'contract.py').read_bytes() == reviewed, 'reviewed parser source drift'
    sources, _, previous = successor.assemble()
    out = {}
    for name, raw in previous.items():
        text = raw.decode()
        for old, new in ROOTS.items():
            text = text.replace(old, new)
        out[name] = text.encode()
    text = out['window-base-r11.py'].decode()
    text = build.once(text,
        "ACCEPTED = Path('/var/tmp/ga-e0t1.20-terminal-20260927-r1/observed-after.json')",
        "ACCEPTED = Path('" + PRIOR_TERMINAL + "/observed-after.json')")
    text = build.once(text,
        "ACCEPTED_SHA = '32bb73640151244d73e3ef6227702f5ac5ec879a00f976989139216cd763717e'",
        "ACCEPTED_SHA = '" + PRIOR_OBSERVATION_SHA + "'")
    text = build.once(text,
        "Path('/var/tmp/ga-e0t1.20-terminal-20260927-r1/result.json')",
        "Path('" + PRIOR_TERMINAL + "/result.json')")
    text = build.once(text, 'CACHE_PREV_NS = 1790575978569227372',
        'CACHE_PREV_NS = ' + str(successor.CACHE_NS))
    text = build.once(text, 'CACHE_PINNED_NS = ' + str(successor.CACHE_NS),
        'CACHE_PINNED_NS = ' + str(cache_ns))
    text = build.once(text,
        '# Successor read-only observation 49a7405a6e17c25c69ec9fbfba9b75d7e83c2c2fdde5bb42b1fea98ef726d926. Fresh OBSERVE remains mandatory.',
        '# Recovered r3 observation ' + PRIOR_OBSERVATION_SHA + '. Fresh OBSERVE remains mandatory.')
    assert PRIOR_RESULT_SHA in text
    out['window-base-r11.py'] = text.encode()
    history = {name: {sha(raw)} for name, raw in previous.items()}
    for _ in range(40):
        for name, raw in out.items():
            history.setdefault(name, set()).add(sha(raw))
        mapping = {old: sha(out[name]) for name, hashes in history.items()
                   for old in hashes if old != sha(out[name])}
        newer = {}
        for name, raw in out.items():
            if name.endswith(('.py', '.sh')):
                raw = build.HEX.sub(lambda m: mapping.get(m[0], m[0]), raw.decode()).encode()
            newer[name] = raw
        if newer == out:
            break
        out = newer
    else:
        raise RuntimeError('r4 binding graph did not settle')
    # Preserve the historical recovery artifact as unused evidence, byte-exact.
    out['stranded-recovery.py'] = build.git('show', RECOVERY + ':' + build.NEW + '/stranded-recovery.py')
    for name, raw in out.items():
        if name.endswith('.py'):
            ast.parse(raw, filename=name)
    for name in ('WORKER-BRIEF.md', 'worker-startup.py',
                 'common-snapshot-r1.py', 'read-time-accounting.py',
                 'continuation-admission.py'):
        assert out[name] == previous[name], name
    return sources, previous, out


def main(output, cache_ns):
    cache_ns = int(cache_ns)
    root = Path(output)
    assert not root.exists(), 'create-only r4 output'
    sources, previous, out = assemble(cache_ns)
    root.mkdir(mode=0o700)
    for name, raw in out.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest = dict(schema='ga-e0t1.20.restored-successor-window.v1',
        parser_review_commit=PARSER_REVIEW,
        recovered_attempt_commit=CONSUMED_ATTEMPT,
        recovery_commit=RECOVERY,
        accepted_observation_sha256=PRIOR_OBSERVATION_SHA,
        accepted_result_sha256=PRIOR_RESULT_SHA,
        source_files={name: sha(raw) for name, raw in sources.items()},
        intermediate_files={name: sha(raw) for name, raw in previous.items()},
        consumed_attempt_files=json.loads(build.git('show', CONSUMED_ATTEMPT + ':' + build.NEW + '/assembly.json'))['files'],
        completed_recovery_files=json.loads(build.git('show', RECOVERY + ':' + build.NEW + '/assembly.json'))['files'],
        authoring_files={name: sha((build.HERE/name).read_bytes()) for name in
                         ('retry.py', 'successor.py', 'build.py', 'contract.py')},
        files={name: sha(raw) for name, raw in out.items()},
        cache_pin_ns=cache_ns, execution_admitted=False,
        completed_operations_replayed=False)
    with (root/'assembly.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(output=str(root), files=len(out), execution_admitted=False)))


if __name__ == '__main__':
    main(*sys.argv[1:])
