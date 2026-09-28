"""Generate a recovery-only successor of the signed r3 window.

This is an append-forward terminal disposition, not a fresh worker attempt.
Only ADMIT, RESTORE and TERMINAL wrappers can run. Original r3 files and all
live attempt records remain preserved at signed cdf7e378 and consumed roots.
"""
import ast
import functools
import hashlib
import json
from pathlib import Path
import sys

import build

HERE = Path(__file__).parent
PARENT = 'cdf7e3784d18358e099c444b48bf43387f9175a7'
COMPLETED_CLOSE_SHA = 'fab5bf6d06a261b326de253b52f39bbf12dad0d0c059b6c4e4fb3ff0a9396f58'
COMPLETED_OBSERVER_SHA = '091457e1027f2115b5321f894278fcbe3d8dc57639f871f0d9486ffc243651ed'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@functools.cache
def frozen_predecessor():
    # Recovery authenticates a completed attempt, never current authoring inputs.
    prefix = PARENT+':'+build.NEW+'/'
    manifest = json.loads(build.git('show', prefix+'assembly.json'))
    previous = {name: build.git('show', prefix+name) for name in manifest['files']}
    assert {name: sha(raw) for name, raw in previous.items()} == manifest['files']
    return previous


def assemble():
    previous = dict(frozen_predecessor())
    out = dict(previous)
    out['stranded-recovery.py'] = (HERE/'stranded-recovery.py').read_bytes()
    text = out['window-base-r11.py'].decode()
    old = """    require(not list(ROOT.glob('suspension-*-failure.json'))
        and not list(ROOT.glob('suspension-*-refused-after.json')), 'unreviewed stranded lifecycle')
    return s.chain(record('suspension-baseline.json'),lifecycle_records(s),
        suspension_record(o),str(ROOT),terminal,read_account=suspension_read_equal)
"""
    new = """    recovery=module(HERE/'stranded-recovery.py','STRANDED_SOURCE_SHA')
    return recovery.verify(types.SimpleNamespace(**globals()),s,suspension_record(o),terminal=terminal)
"""
    text = build.once(text, old, new)
    text = build.once(text, 'def main():\n', 'def main():\n'
        "    require(sys.argv[1:]==['restore'] or (len(sys.argv)==4 and sys.argv[1]=='inner'),\n"
        "        'recovery-only package cannot preflight stage or resume')\n")
    out['window-base-r11.py'] = text.encode()
    for name in out:
        if name.startswith('operator/') and name not in (
                'operator/ADMIT.sh', 'operator/RESTORE.sh', 'operator/TERMINAL.sh'):
            out[name] = build.once(out[name].decode(), '#!/bin/sh\n',
                '#!/bin/sh\necho "RECOVERY ONLY - this operation is prohibited" >&2\nexit 125\n').encode()
    out['operator/ADMIT.sh'] = build.once(out['operator/ADMIT.sh'].decode(),
        'CLOSE_SHA='+COMPLETED_CLOSE_SHA, 'CLOSE_SHA=COMPLETED_CLOSE_PIN').encode()
    history = {name: {sha(raw)} for name, raw in previous.items()}
    for _ in range(40):
        for name, raw in out.items():
            history.setdefault(name, set()).add(sha(raw))
        mapping = {old: sha(out[name]) for name, hashes in history.items()
                   for old in hashes if old != sha(out[name])}
        newer = {}
        for name, raw in out.items():
            # All pins in the new recovery module bind preserved evidence, not
            # regenerated code. Never rewrite those historical digest values.
            if name.endswith(('.py', '.sh')) and name != 'stranded-recovery.py':
                text = raw.decode().replace('STRANDED_SOURCE_SHA', sha(out['stranded-recovery.py']))
                if name == 'window-r11.py':
                    # This field authenticates completed OBSERVE evidence. It
                    # is not a future source invocation. Keep the original pin
                    # while hashing this file's final bytes into its consumers.
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
    manifest = dict(schema='ga-e0t1.20.recovery-only.v1', predecessor_commit=PARENT,
        predecessor_files={name: sha(raw) for name, raw in previous.items()},
        files={name: sha(raw) for name, raw in out.items()},
        worker_retry=False, completed_operations_replayed=False, execution_admitted=False,
        wrappers=['ADMIT', 'RESTORE', 'TERMINAL'])
    with (root/'assembly.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(root=str(root), files=len(out), worker_retry=False)))


if __name__ == '__main__':
    main(sys.argv[1])
