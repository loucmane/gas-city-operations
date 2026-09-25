"""Isolated source-only launcher. Exact external source-inventory hash required."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import types

ROOT = Path(__file__).parent
RUNTIME_SHA = '2585357a808d8f36604d4bf45a39a5363ba87c8d719413ba42d9fd0fac71973f'
NAMES = {'source_runtime.py', 'manifest_candidate.py', 'metadata_window.py',
         'metadata_closure.py', 'metadata_executor.py', 'launch.py'}
STAGES = {'prepare', 'pause', 'observe', 'paired', 'verify', 'restore-preapply',
          'restore-accepted', 'recover-pause', 'recover-preparation'}


def main():
    if not (sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
            and os.getuid() == os.geteuid() == 1000):
        raise RuntimeError('requires isolated source-only UID1000 invocation')
    args = sys.argv[1:]
    if not (len(args) in (3, 4) and args[0] == '--expect-sources' and args[2] in STAGES
            and ((args[2] == 'prepare') == (len(args) == 3))):
        raise RuntimeError('exact source digest, stage and prepared digest required')
    expected, stage = args[1:3]
    raw = (ROOT/'source_runtime.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != RUNTIME_SHA:
        raise RuntimeError('source loader digest drift')
    runtime = types.ModuleType('pinned_source_runtime')
    runtime.__file__ = str(ROOT/'source_runtime.py')
    exec(compile(raw, runtime.__file__, 'exec', dont_inherit=True, optimize=0), runtime.__dict__)
    runtime.source(ROOT/'source_runtime.py', RUNTIME_SHA)
    inventory_raw, _ = runtime.source(ROOT/'source-pins.json', expected)
    pins = json.loads(inventory_raw)
    if set(pins) != NAMES:
        raise RuntimeError('source inventory cardinality')
    for name, digest in pins.items():
        runtime.source(ROOT/name, digest)
    candidate = runtime.module('successor_manifest', ROOT/'manifest_candidate.py', pins['manifest_candidate.py'])
    window = runtime.module('successor_window', ROOT/'metadata_window.py', pins['metadata_window.py'])
    closure = runtime.module('successor_closure', ROOT/'metadata_closure.py', pins['metadata_closure.py'])
    executor = runtime.module('successor_executor', ROOT/'metadata_executor.py', pins['metadata_executor.py'])
    graph = executor.assemble(runtime, candidate, window, closure)
    c, s, o = (graph[name] for name in ('recovery_controller', 'recovery_state', 'observe_recovery'))
    try:
        if stage == 'prepare':
            result = c.prepare()
        elif stage == 'recover-preparation':
            result = c.recover_preparation(args[3])
        else:
            package, manifest = c.package(args[3])
            if stage.startswith('restore-'):
                result = c.restore(args[3], package, manifest, accepted=stage == 'restore-accepted')
            else:
                action = {'pause':c.pause, 'observe':c.observe, 'paired':c.paired,
                          'verify':c.verify, 'recover-pause':c.recover_pause}[stage]
                result = action(args[3], package, manifest)
        print(o.encoded(result).decode(), flush=True)
    except BaseException as exc:
        failure = dict(stage=stage, error_type=type(exc).__name__, reason=str(exc),
                       no_automatic_retry=True, source_inventory_sha256=expected)
        if s.RECORDS.is_dir():
            try:
                s.record(stage+'-failure-'+secrets.token_hex(12)+'.json', failure)
            except BaseException as recording_error:
                failure['record_error'] = repr(recording_error)
        print(o.encoded(failure).decode(), file=sys.stderr, flush=True)
        raise


if __name__ == '__main__':
    main()
