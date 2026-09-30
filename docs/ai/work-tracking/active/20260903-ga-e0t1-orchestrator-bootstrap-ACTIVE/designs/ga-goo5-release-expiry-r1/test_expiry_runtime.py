"""Execute the real adapter with fixture-only commands, reads and clock values."""
import copy
import json
from types import SimpleNamespace

import pytest
import release_delivery_r12 as d
import release_runtime_r12 as r
from test_runtime import harness
from test_expiry import fixture, T, BASE, OBS


@pytest.mark.parametrize('existing', [False, True])
def test_adapter_captures_brackets_and_saves_transition_before_ack(monkeypatch, existing):
    run, calls, saved = harness(monkeypatch, existing=existing)
    original = r.execute
    before, done = fixture(True, True)
    def wrapped(w, phase, inspector, runtime, delivery, *args):
        native_read = inspector.file_bytes
        reads = 0
        def read(path, limit):
            nonlocal reads
            if path == r.CITY / '.gc/nudges/state.json':
                reads += 1
                return json.dumps(before if reads == 1 else done['queue']).encode()
            return native_read(path, limit)
        ticks = iter(BASE + OBS)
        monkeypatch.setattr(r.time, 'time_ns', lambda: next(ticks))
        return original(w, phase, SimpleNamespace(file_bytes=read), runtime, delivery, *args)
    monkeypatch.setattr(r, 'execute', wrapped)
    result = run()
    assert result['delivered']
    assert saved['delivery-baseline.json']['baseline_window_ns'] == BASE
    observations = [v for k, v in saved.items() if k.startswith('delivery-observation-')]
    evidence = [v for k, v in saved.items() if k.startswith('delivery-history-expiry-')]
    assert len(observations) == len(evidence) == 1
    assert observations[0]['observed_window_ns'] == OBS
    assert evidence[0] == result['historical_expirations']
    names = list(saved)
    assert next(i for i, k in enumerate(names) if k.startswith('delivery-history-expiry-')) < names.index('delivery-acknowledged.json')
    assert sum(c[3:5] == ['session', 'nudge'] for c in calls) == 1
    assert all(c[3:5] not in (['nudge', 'status'], ['nudge', 'poll'], ['nudge', 'drain']) for c in calls)


@pytest.mark.parametrize('fault', ['baseline-reversed', 'observation-reversed', 'recorder'])
def test_capture_and_recording_failures_never_pass_or_reenqueue(monkeypatch, fault):
    run, calls, saved = harness(monkeypatch)
    original = r.execute
    before, done = fixture(True, True)
    def wrapped(w, phase, inspector, runtime, delivery, *args):
        native_read = inspector.file_bytes
        reads = 0
        def read(path, limit):
            nonlocal reads
            if path == r.CITY / '.gc/nudges/state.json':
                reads += 1
                return json.dumps(before if reads == 1 else done['queue']).encode()
            return native_read(path, limit)
        ticks = iter(([T + 100, T] if fault == 'baseline-reversed' else BASE)
                     + ([T + 400, T + 200] if fault == 'observation-reversed' else OBS))
        monkeypatch.setattr(r.time, 'time_ns', lambda: next(ticks))
        original_save = w.save
        def save(name, value):
            if fault == 'recorder' and name.startswith('delivery-history-expiry-'):
                raise OSError('fixture save failure')
            return original_save(name, value)
        w.save = save
        return original(w, phase, SimpleNamespace(file_bytes=read), runtime, delivery, *args)
    monkeypatch.setattr(r, 'execute', wrapped)
    with pytest.raises((RuntimeError, OSError)):
        run()
    assert sum(c[3:5] == ['session', 'nudge'] for c in calls) == (0 if fault == 'baseline-reversed' else 1)
    assert 'delivery-acknowledged.json' not in saved


def test_existing_regression_files_are_byte_identical_to_frozen_predecessor():
    from pathlib import Path
    here = Path(__file__).parent
    for name in ('test_delivery_regression.py', 'test_runtime.py'):
        assert (here / name).read_bytes() == (here.parent / 'ga-goo5-c1-package' / name).read_bytes()


def test_source_diff_preserves_unrelated_authority_functions():
    import ast
    from pathlib import Path
    here = Path(__file__).parent
    old = here.parent / 'ga-goo5-c1-package'
    def functions(path):
        return {n.name: ast.dump(n, include_attributes=False)
                for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}
    predecessor = functions(old / 'release-delivery-r12.py')
    current = functions(here / 'release-delivery-r13.py')
    for name in predecessor:
        if name not in ('acknowledged', 'wait'):
            assert current[name] == predecessor[name], name
    predecessor = functions(old / 'release-runtime-r12.py')
    current = functions(here / 'release-runtime-r13.py')
    for name in predecessor:
        if name != 'execute':
            assert current[name] == predecessor[name], name
