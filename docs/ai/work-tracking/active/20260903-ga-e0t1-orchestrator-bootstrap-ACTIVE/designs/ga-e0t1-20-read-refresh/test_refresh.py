"""Disposable fixtures only. No production refresh, lifecycle or provider calls."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import time

import pytest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('refresh_fixture', HERE / 'refresh.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root = tmp_path / 'objects'
    root.mkdir()
    file = root / 'state.json'
    file.write_bytes(b'{"suspended":true}\n')
    paths = [file]
    for name in ('city', 'beads', 'provisioning'):
        item = root / name
        item.mkdir()
        paths.append(item)
    old = time.time_ns() - 25 * R.HOUR
    for path in paths:
        os.utime(path, ns=(old, old))
    time.sleep(0.02)  # Fixture ctime must precede the kernel's next coarse atime.
    pins = {}
    for path in paths:
        image = R.capture(path)
        pins[str(path)] = dict(image['after'])
        if path == file:
            pins[str(path)]['sha256'] = image['sha256']
    monkeypatch.setattr(R, 'NOT_BEFORE_NS', time.time_ns() - R.HOUR)
    monkeypatch.setattr(R, 'NOT_AFTER_NS', time.time_ns() + R.HOUR)
    return paths, pins, tmp_path / 'evidence'


def test_real_ordinary_reads_preserve_non_atime(fixture):
    paths, pins, root = fixture
    result = R.run(pins, root)
    assert result['ok'] and not result['timestamp_writes'] and not result['worker_release']
    assert set(result['actions'].values()) == {'ordinary-read'}
    for path in paths:
        current = R.capture(path)
        assert R.without_atime(current['after']) == R.without_atime({k: v for k, v in pins[str(path)].items() if k != 'sha256'})
        assert R.young(current['after'], time.time_ns())
    assert json.loads((root / 'result.json').read_bytes()) == result


def test_early_refusal_is_before_any_read_or_root(fixture, monkeypatch):
    _, pins, root = fixture
    monkeypatch.setattr(R, 'NOT_BEFORE_NS', time.time_ns() + R.HOUR)
    monkeypatch.setattr(R, 'capture', lambda *a, **k: pytest.fail('early capture'))
    with pytest.raises(RuntimeError, match='time window'):
        R.run(pins, root)
    assert not root.exists()


def test_existing_root_never_replayed(fixture):
    _, pins, root = fixture
    root.mkdir()
    (root / 'preserved').write_bytes(b'failed attempt')
    with pytest.raises(RuntimeError, match='consumed'):
        R.run(pins, root)
    assert (root / 'preserved').read_bytes() == b'failed attempt'


@pytest.mark.parametrize('field', ['uid', 'gid', 'mode', 'device', 'inode', 'nlink', 'size', 'mtime_ns', 'ctime_ns', 'sha256'])
def test_every_non_atime_pin_refuses_before_mutation(fixture, field):
    paths, pins, root = fixture
    pins[str(paths[0])][field] = 'wrong' if field == 'sha256' else pins[str(paths[0])][field] + 1
    before = [os.lstat(p) for p in paths]
    with pytest.raises(RuntimeError, match='drift'):
        R.run(pins, root)
    assert before == [os.lstat(p) for p in paths]
    assert not root.exists()


def test_19_to_24_hour_gap_refuses_all_before_reads(fixture, monkeypatch):
    paths, pins, root = fixture
    stamp = time.time_ns()
    first = str(paths[0])
    pins[first]['mtime_ns'] = pins[first]['ctime_ns'] = stamp - 30 * R.HOUR
    pins[first]['atime_ns'] = stamp - 20 * R.HOUR
    original = R.capture
    def capture(path, **kwargs):
        assert not kwargs.get('ordinary')
        result = original(path)
        if str(path) == first:
            result['before'] = result['after'] = {k: v for k, v in pins[first].items() if k != 'sha256'}
        return result
    monkeypatch.setattr(R, 'capture', capture)
    with pytest.raises(RuntimeError, match='eligibility'):
        R.run(pins, root)
    assert not root.exists()


@pytest.mark.parametrize('delta', [-1, 1, 23 * 3600 * 10**9])
def test_unexplained_atime_advance_or_reversal_refuses(delta):
    stamp = time.time_ns()
    pin = dict(atime_ns=stamp-25*R.HOUR, mtime_ns=stamp-30*R.HOUR, ctime_ns=stamp-30*R.HOUR)
    seen = dict(pin, atime_ns=pin['atime_ns']+delta)
    with pytest.raises(RuntimeError):
        R.validate_pin({'after':seen}, pin, stamp)


def test_natural_24h_advance_may_already_be_young():
    stamp = time.time_ns()
    pin = dict(atime_ns=stamp-25*R.HOUR, mtime_ns=stamp-30*R.HOUR, ctime_ns=stamp-30*R.HOUR)
    R.validate_pin({'after':dict(pin, atime_ns=stamp-R.HOUR)}, pin, stamp)


@pytest.mark.parametrize('kind', ['leaf-link', 'parent-link', 'fifo', 'hardlink', 'oversize'])
def test_filesystem_refusals(tmp_path, kind):
    file = tmp_path / 'plain'
    file.write_bytes(b'x')
    target = file
    if kind == 'leaf-link':
        target = tmp_path / 'link'
        target.symlink_to(file)
    elif kind == 'parent-link':
        (tmp_path / 'alias').symlink_to(tmp_path, target_is_directory=True)
        target = tmp_path / 'alias' / 'plain'
    elif kind == 'fifo':
        target = tmp_path / 'fifo'
        os.mkfifo(target)
    elif kind == 'hardlink':
        os.link(file, tmp_path / 'second')
    else:
        file.write_bytes(b'x' * 4097)
    with pytest.raises((OSError, RuntimeError)):
        R.capture(target)


def test_production_has_no_timestamp_or_lifecycle_writes():
    tree = ast.parse((HERE / 'refresh.py').read_text())
    forbidden = {'utime', 'chmod', 'chown', 'unlink', 'remove', 'rmdir', 'rename', 'replace', 'system', 'Popen', 'run'}
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr in forbidden]
    assert len(R.PINS) == 4
    assert R.NOT_BEFORE_NS == 1790598360000000000


def test_young_agrees_with_unchanged_original_gate(monkeypatch):
    source = HERE.parent / 'ga-e0t1-20-astra-window/window-base-r11.py'
    [node] = [n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'stable_read_times']
    scope = dict(os=os, time=time, require=R.require)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), scope)
    stamp = time.time_ns()
    for age in (0, 1, 18*R.HOUR, 19*R.HOUR, 20*R.HOUR, 24*R.HOUR):
        value = dict(atime_ns=stamp-age, mtime_ns=stamp-30*R.HOUR, ctime_ns=stamp-30*R.HOUR)
        monkeypatch.setattr(os, 'lstat', lambda p: SimpleNamespace(**{'st_'+k:v for k,v in value.items()}))
        monkeypatch.setattr(os, 'statvfs', lambda p: SimpleNamespace(f_flag=os.ST_RELATIME))
        if R.young(value, stamp):
            scope['stable_read_times'](paths=['fixture'], now_ns=stamp)
        else:
            with pytest.raises(RuntimeError):
                scope['stable_read_times'](paths=['fixture'], now_ns=stamp)


def test_already_young_objects_need_no_ordinary_read(fixture, monkeypatch):
    paths, pins, root = fixture
    for path in paths:
        R.capture(path, ordinary=True)
    original = R.capture
    def capture(path, **kwargs):
        assert not kwargs.get('ordinary'), 'young objects must not be refreshed again'
        return original(path, **kwargs)
    monkeypatch.setattr(R, 'capture', capture)
    result = R.run(pins, root)
    assert set(result['actions'].values()) == {'already-young-no-refresh'}


def test_read_failure_preserves_intent_and_forbids_replay(fixture, monkeypatch):
    _, pins, root = fixture
    original = R.capture
    def capture(path, **kwargs):
        if kwargs.get('ordinary'):
            raise OSError('injected read failure')
        return original(path, **kwargs)
    monkeypatch.setattr(R, 'capture', capture)
    with pytest.raises(OSError, match='injected'):
        R.run(pins, root)
    assert (root / 'intent.json').is_file()
    assert (root / 'read-0-intent.json').is_file()
    assert not (root / 'result.json').exists()
    with pytest.raises(RuntimeError, match='consumed'):
        R.run(pins, root)


def test_clock_disagreement_refuses_before_ordinary_read(fixture, monkeypatch):
    _, pins, root = fixture
    original_clock = R.clock_envelope
    original_capture = R.capture
    calls = 0
    def clock():
        nonlocal calls
        value = original_clock()
        calls += 1
        if calls > 1:
            for sample in value.values():
                sample['real_ns'] += 2 * 10**9
        return value
    def capture(path, **kwargs):
        assert not kwargs.get('ordinary'), 'clock disagreement must precede ordinary reads'
        return original_capture(path, **kwargs)
    monkeypatch.setattr(R, 'clock_envelope', clock)
    monkeypatch.setattr(R, 'capture', capture)
    with pytest.raises(RuntimeError, match='clock offset disagreement'):
        R.run(pins, root)
    assert (root / 'intent.json').exists()
    assert not (root / 'read-0-intent.json').exists()


def test_boot_mismatch_refuses_before_root(fixture, monkeypatch):
    _, pins, root = fixture
    monkeypatch.setattr(R, 'BOOT', 'not-the-live-boot')
    with pytest.raises(RuntimeError, match='boot drift'):
        R.run(pins, root)
    assert not root.exists()


def test_midflight_directory_drift_never_reports_success(fixture, monkeypatch):
    paths, pins, root = fixture
    original = R.capture
    changed = False
    def capture(path, **kwargs):
        nonlocal changed
        result = original(path, **kwargs)
        if kwargs.get('ordinary') and not changed:
            changed = True
            (paths[-1] / 'unexpected').write_bytes(b'fixture drift')
        return result
    monkeypatch.setattr(R, 'capture', capture)
    with pytest.raises(RuntimeError, match='drift before ordinary read'):
        R.run(pins, root)
    assert (root / 'read-0.json').exists()
    assert not (root / 'result.json').exists()
    assert (paths[-1] / 'unexpected').read_bytes() == b'fixture drift'


def test_wrapper_binds_exact_source_and_is_not_worker_admission():
    text = (HERE / 'READ-REFRESH.sh').read_text()
    digest = hashlib.sha256((HERE / 'refresh.py').read_bytes()).hexdigest()
    assert 'REFRESH_SHA=' + digest in text
    assert '/usr/bin/python3 -I -S -B' in text
    assert text.count('source-launch.py') == 1
    assert 'worker_release=false' in text
    assert 'status --porcelain --untracked-files=all' in text
    assert '"$head" != "$COMMIT"' in text
    assert 'gc sling' not in text and 'rig resume' not in text
