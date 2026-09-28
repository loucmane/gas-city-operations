"""Create-only recovery successor for the consumed r4 window; no worker retry."""
import ast
import functools
import json
from pathlib import Path
import sys

import build

HERE = Path(__file__).parent
PARENT = '78152f1d1400961978b35db610db5eef66babd71'
COMPLETED_CLOSE_SHA = 'dbe568f3c63708a13c3b5c9336af2967148f952c06580c7b9850af1f8cde5f2b'
COMPLETED_OBSERVER_SHA = '3c44fae8d318378eb20f0f2cbdb358ea775a60626805155f3f3fe4fd38e9c304'
VERIFIER = 'stranded-r4-recovery.py'
WRAPPERS = ('operator/ADMIT.sh', 'operator/RESTORE.sh', 'operator/TERMINAL.sh')


@functools.cache
def frozen_predecessor():
    prefix = PARENT+':'+build.NEW+'/'
    manifest = json.loads(build.git('show', prefix+'assembly.json'))
    files = {name: build.git('show', prefix+name) for name in manifest['files']}
    assert {name: build.sha(raw) for name, raw in files.items()} == manifest['files']
    return files


def assemble():
    previous = dict(frozen_predecessor())
    out = dict(previous)
    out[VERIFIER] = (HERE/VERIFIER).read_bytes()
    text = out['window-base-r11.py'].decode()
    old = """    require(not list(ROOT.glob('suspension-*-failure.json'))
        and not list(ROOT.glob('suspension-*-refused-after.json')), 'unreviewed stranded lifecycle')
    return s.chain(record('suspension-baseline.json'),lifecycle_records(s),
        suspension_record(o),str(ROOT),terminal,read_account=suspension_read_equal)
"""
    new = """    recovery=module(HERE/'stranded-r4-recovery.py','STRANDED_R4_SHA')
    return recovery.verify(types.SimpleNamespace(**globals()),s,suspension_record(o),terminal=terminal)
"""
    text = build.once(text, old, new)
    text = build.once(text, 'def main():\n', 'def main():\n'
        "    require(sys.argv[1:]==['restore'] or (len(sys.argv)==4 and sys.argv[1]=='inner'\n"
        "        and sys.argv[3]=='0'), 'recovery-only package cannot preflight stage or resume')\n")
    out['window-base-r11.py'] = text.encode()
    for name in out:
        if name.startswith('operator/') and name not in WRAPPERS:
            out[name] = build.once(out[name].decode(), '#!/bin/sh\n',
                '#!/bin/sh\necho "RECOVERY ONLY - this operation is prohibited" >&2\nexit 125\n').encode()
    # worker_launched=False describes this observer, not the entire recovered window.
    # Explicit history prevents a misleading no-worker-ever interpretation.
    text = out['observe-terminal-r11.py'].decode()
    text = build.once(text, 'terminal_suspension_endpoint_bound=True,accepted_restoration_bound=True))',
        'terminal_suspension_endpoint_bound=True,accepted_restoration_bound=True,\n'
        '        worker_started_in_window=True,source_release_sent=False,open_sessions=0))')
    text = build.once(text, 'worker_launched=False,full_native_integrity=True)))',
        'worker_launched=False,full_native_integrity=True,\n'
        '        worker_started_in_window=True,source_release_sent=False,open_sessions=0)))')
    out['observe-terminal-r11.py'] = text.encode()
    out['operator/ADMIT.sh'] = build.once(out['operator/ADMIT.sh'].decode(),
        'CLOSE_SHA='+COMPLETED_CLOSE_SHA, 'CLOSE_SHA=COMPLETED_CLOSE_PIN').encode()
    history = {name: {build.sha(raw)} for name, raw in previous.items()}
    for _ in range(40):
        for name, raw in out.items():
            history.setdefault(name, set()).add(build.sha(raw))
        mapping = {old: build.sha(out[name]) for name, hashes in history.items()
                   for old in hashes if old != build.sha(out[name])}
        newer = {}
        for name, raw in out.items():
            # Pins in both historical recovery modules are immutable evidence.
            if name.endswith(('.py', '.sh')) and name not in (VERIFIER, 'stranded-recovery.py'):
                text = raw.decode().replace('STRANDED_R4_SHA', build.sha(out[VERIFIER]))
                if name == 'window-r11.py':
                    text = build.once(text, "OBSERVER_SHA='"+COMPLETED_OBSERVER_SHA+"'",
                                      "OBSERVER_SHA='COMPLETED_OBSERVER_PIN'")
                raw = build.HEX.sub(lambda m: mapping.get(m[0], m[0]), text).encode()
                if name == 'window-r11.py':
                    raw = raw.replace(b'COMPLETED_OBSERVER_PIN', COMPLETED_OBSERVER_SHA.encode())
            newer[name] = raw
        if newer == out:
            break
        out = newer
    else:
        raise RuntimeError('recovery hash graph did not settle')
    out['operator/ADMIT.sh'] = out['operator/ADMIT.sh'].replace(
        b'COMPLETED_CLOSE_PIN', COMPLETED_CLOSE_SHA.encode())
    for name, raw in out.items():
        if name.endswith('.py'):
            ast.parse(raw, filename=name)
    return previous, out


def main(output):
    root = Path(output)
    assert not root.exists(), 'create-only recovery output'
    previous, out = assemble()
    root.mkdir(mode=0o700)
    for name, raw in out.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest = dict(schema='ga-e0t1.20.recovery-only.v2', predecessor_commit=PARENT,
        predecessor_files={name: build.sha(raw) for name, raw in previous.items()},
        files={name: build.sha(raw) for name, raw in out.items()},
        worker_retry=False, completed_operations_replayed=False, execution_admitted=False,
        worker_started_in_window=True, source_release_sent=False,
        wrappers=['ADMIT', 'RESTORE', 'TERMINAL'])
    with (root/'assembly.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(root=str(root), files=len(out), worker_retry=False)))


if __name__ == '__main__':
    main(sys.argv[1])
