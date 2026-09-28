"""Create-only operational successor; never replay completed BIND or ROUTE.

The inherited builder and its historical regression corpus remain unchanged.
This bounded overlay changes only continuation admission and attempt identities.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

import build

HERE = Path(__file__).parent
# Refreshed once after supported recording, before final assembly/review.
CACHE_NS = 1790582919791915505
ROOTS = {
    'ga-e0t1.20-window-20260928-r2': 'ga-e0t1.20-window-20260928-r3',
    'ga-e0t1.20-window-obs-20260927-r1': 'ga-e0t1.20-window-obs-20260928-r3',
    'ga-e0t1.20-integrity-20260928-r4': 'ga-e0t1.20-integrity-20260928-r5',
    'ga-e0t1.20-audit-%s-20260927-r1': 'ga-e0t1.20-audit-%s-20260928-r3',
    'ga-e0t1.20-audit-route-20260927-r1': 'ga-e0t1.20-audit-route-20260928-r3',
    'ga-e0t1.20-audit-resume-20260927-r1': 'ga-e0t1.20-audit-resume-20260928-r3',
    'ga-e0t1.20-terminal-20260927-r1': 'ga-e0t1.20-terminal-20260928-r3',
    'ga-e0t1.20-candidate-inspection-20260927-r1': 'ga-e0t1.20-candidate-inspection-20260928-r3',
    'ga-e0t1.20-startup-release-20260927-r1': 'ga-e0t1.20-startup-release-20260928-r3',
    'ga-e0t1.20-close-session.json': 'ga-e0t1.20-r3-close-session.json',
    'ga-e0t1.20-close-drain.requested': 'ga-e0t1.20-r3-close-drain.requested',
    'ga-e0t1.20-close-': 'ga-e0t1.20-r3-close-',
    'ga-e0t1.20-hold-': 'ga-e0t1.20-r3-hold-',
    'ga-e0t1.20-watch-': 'ga-e0t1.20-r3-watch-',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def assemble():
    sources, previous = build.assemble(final=True)
    out = {}
    for name, raw in previous.items():
        text = raw.decode()
        for old, new in ROOTS.items():
            text = text.replace(old, new)
        out[name] = text.encode()
    # These consumed wrappers remain visible, but cannot execute under this successor.
    for name in ('operator/BIND.sh', 'operator/ROUTE.sh'):
        out[name] = build.once(out[name].decode(), '#!/bin/sh\n',
            '#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n').encode()
    text = out['contract.py'].decode()
    text = build.once(text, "value.get('id') == TASK and value.get('parent') == PARENT",
        "value.get('id') == TASK and ('parent' not in value if phase == 'routed' else value.get('parent') == PARENT)")
    text = build.once(text, "(PARENT, 'parent-child')", "(PARENT, 'relates-to' if phase == 'routed' else 'parent-child')")
    text = build.once(text, "value.get('dependent_count', 0) == 0",
        "value.get('dependent_count', 0) == (1 if phase == 'routed' else 0)")
    text = text.replace('the exact known nonblocking edge', 'the exact phase-bound association')
    text = text.replace('not the declared nonblocking parent edge', 'not the declared phase-bound association')
    out['contract.py'] = text.encode()
    out['test_contract.py'] = build.once(out['test_contract.py'].decode(),
        "    task['metadata']['gc.routed_to'] = c.TARGET\n",
        "    task['metadata']['gc.routed_to'] = c.TARGET\n"
        "    task.pop('parent')\n"
        "    task['dependencies'][0]['dependency_type'] = 'relates-to'\n"
        "    task['dependent_count'] = 1\n").encode()
    out['continuation-admission.py'] = (HERE/'continuation-admission.py').read_bytes()
    text = out['window-base-r11.py'].decode()
    text = build.once(text, "ACCEPTED = Path('/var/tmp/gct-oak5-p13-adoption-20260927/after.json')",
        "ACCEPTED = Path('/var/tmp/ga-e0t1.20-terminal-20260927-r1/observed-after.json')")
    text = build.once(text, "ACCEPTED_SHA = 'ab3da79af311190c682d5f1e1146a5c73dd9a66014ca33951d4d38f8ce2331b6'",
        "ACCEPTED_SHA = '32bb73640151244d73e3ef6227702f5ac5ec879a00f976989139216cd763717e'")
    text = build.once(text, 'CACHE_PREV_NS = 1790510685769555369',
        'CACHE_PREV_NS = 1790575978569227372')
    text = build.once(text, 'def pins():\n', 'def pins():\n'
        "    previous=json.loads(read(Path('/var/tmp/ga-e0t1.20-terminal-20260927-r1/result.json'),\n"
        "        'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'))\n"
        "    require(previous['ok'] is True and previous['accepted_restoration_bound'] is True\n"
        "        and previous['actual_host_verified'] is True and previous['worker_launched'] is False,\n"
        "        'previous window was not proven restored')\n")
    text = build.once(text, 'CACHE_PINNED_NS = '+str(build.FINAL_CACHE_NS), 'CACHE_PINNED_NS = '+str(CACHE_NS))
    text = build.once(text, '# Read-only observation SHA-256 '+build.FINAL_OBSERVATION_SHA,
        '# Successor read-only observation 49a7405a6e17c25c69ec9fbfba9b75d7e83c2c2fdde5bb42b1fea98ef726d926. Fresh OBSERVE remains mandatory.')
    text = text.replace('Accepted P13 observation', 'Accepted restored TERMINAL observation')
    text = text.replace('Compare against P13', 'Compare against the completed restored window')
    text = build.once(text, "        host(o)\n", "        host(o)\n        module(HERE/'continuation-admission.py','CONTINUATION_SHA').admit(sys.modules[__name__],b,owned)\n")
    # sys.modules is not guaranteed by every source-only loader; pass the current
    # module interface explicitly without changing those reviewed loaders.
    text = text.replace('admit(sys.modules[__name__],b,owned)', 'admit(types.SimpleNamespace(**globals()),b,owned)')
    text = build.once(text, "        save('stage-consumed.json',dict(executor_sha256=_SOURCE_SHA))",
        "        module(HERE/'continuation-admission.py','CONTINUATION_SHA').recheck(types.SimpleNamespace(**globals()),b,owned)\n"
        "        save('stage-consumed.json',dict(executor_sha256=_SOURCE_SHA))")
    out['window-base-r11.py'] = text.encode()
    text = out['startup-release.py'].decode()
    text = build.once(text, "routed=json.loads(w.read(ROUTE/'task-after.json'))",
        "routed=json.loads(w.read(WINDOW/'admitted-task.json'))")
    out['startup-release.py'] = text.encode()
    # The complete queue audit now precedes the first live configuration write.
    text = out['operator/STAGE.sh'].decode()
    text = build.once(text, 'PATH=/usr/local/bin:/usr/bin:/bin\n',
        'AUDIT_SHA=SUCCESSOR_AUDIT_SHA\nPATH=/usr/local/bin:/usr/bin:/bin\n')
    text = build.once(text, 'step stage "$C/window-r11.py" "$WINDOW_SHA" stage',
        'step audit-route "$C/audit-queue-r3.py" "$AUDIT_SHA" route\n'
        'step stage "$C/window-r11.py" "$WINDOW_SHA" stage')
    out['operator/STAGE.sh'] = text.encode()
    # Rebind only the executable DAG, retaining completed-evidence digest pins.
    history = {name: {sha(raw)} for name, raw in previous.items()}
    for _ in range(40):
        for name, raw in out.items():
            history.setdefault(name, set()).add(sha(raw))
        mapping = {old: sha(out[name]) for name, hashes in history.items()
                   for old in hashes if old != sha(out[name])}
        newer = {}
        for name, raw in out.items():
            if name.endswith(('.py', '.sh')):
                text = raw.decode().replace('CONTINUATION_SHA', sha(out['continuation-admission.py']))
                text = text.replace('SUCCESSOR_AUDIT_SHA', sha(out['audit-queue-r3.py']))
                raw = build.HEX.sub(lambda m: mapping.get(m[0], m[0]), text).encode()
            newer[name] = raw
        if newer == out:
            break
        out = newer
    else:
        raise RuntimeError('successor binding graph did not settle')
    for name, raw in out.items():
        if name.endswith('.py'):
            ast.parse(raw, filename=name)
    for name in ('WORKER-BRIEF.md', 'worker-startup.py'):
        assert out[name] == previous[name], 'worker instruction drift'
    return sources, previous, out


def main(output):
    root = Path(output)
    assert not root.exists(), 'create-only successor output'
    sources, previous, out = assemble()
    root.mkdir(mode=0o700)
    for name, raw in out.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest = dict(schema='ga-e0t1.20.successor-window.v1', source_commit=build.SOURCE,
        predecessor_commit='ff98005b91886526ea1d05bb449987646e0283df',
        source_files={name: sha(raw) for name, raw in sources.items()},
        predecessor_files={name: sha(raw) for name, raw in previous.items()},
        files={name: sha(raw) for name, raw in out.items()}, cache_pin_ns=CACHE_NS,
        execution_admitted=False, completed_operations_replayed=False,
        remaining=['two independent exact-head reviews', 'fresh OBSERVE', 'PREFLIGHT', 'live acceptance'])
    with (root/'assembly.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(output=str(root), files=len(out), execution_admitted=False)))


if __name__ == '__main__':
    main(*sys.argv[1:])
