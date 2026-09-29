"""Real temporary-file marker checks; no runtime directory or process is touched."""
import hashlib
from pathlib import Path
import types

import pytest
import release_runtime_r12 as r
import release_delivery_r12 as d


@pytest.fixture
def marker(tmp_path, monkeypatch):
    city = tmp_path / 'city'
    parent = city / '.gc/nudges/pollers'
    parent.mkdir(parents=True, mode=0o700)
    path = parent / 'fixture.pid'
    path.write_bytes(b'123\n')
    path.chmod(0o600)
    monkeypatch.setattr(r, 'CITY', city)
    source = Path(__file__).parent.parent / 'ga-rq5n-c1-window-r2/candidate-inspect.py'
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'c7a0d85eaa99209705bf55962d6aa6e62c9b85dbd8c3a6f5245c6ca1cd6dcf30'
    inspector = types.ModuleType('pinned_reader')
    exec(compile(raw, str(source), 'exec'), inspector.__dict__)
    return path, inspector


def test_real_marker_reader_is_stable(marker):
    path, inspector = marker
    first = r.marker_identity(path, inspector, d.require)
    assert first == r.marker_identity(path, inspector, d.require)
    assert first[0] == 123 and first[1]['metadata']['nlink'] == 1
    assert first[1]['sha256'] == hashlib.sha256(b'123\n').hexdigest()


@pytest.mark.parametrize('raw', [b'', b'0', b'-1', b' 123', b'123\n\n', b'123 ', b'123\r\n', b'9'*65])
def test_malformed_marker_refuses(marker, raw):
    path, inspector = marker
    path.write_bytes(raw)
    with pytest.raises(RuntimeError): r.marker_identity(path, inspector, d.require)


@pytest.mark.parametrize('mode', [0o622, 0o666, 0o677])
def test_write_shared_marker_refuses(marker, mode):
    path, inspector = marker
    path.chmod(mode)
    with pytest.raises(RuntimeError): r.marker_identity(path, inspector, d.require)


def test_symlink_marker_refuses_without_following(marker):
    path, inspector = marker
    link = path.with_name('alias.pid')
    link.symlink_to(path)
    with pytest.raises(RuntimeError): r.marker_identity(link, inspector, d.require)


def test_hardlink_marker_refuses(marker):
    path, inspector = marker
    link = path.with_name('hardlink.pid')
    link.hardlink_to(path)
    with pytest.raises(RuntimeError): r.marker_identity(path, inspector, d.require)


def test_write_shared_parent_refuses(marker):
    path, inspector = marker
    path.parent.chmod(0o777)
    with pytest.raises(RuntimeError, match='directory authority'):
        r.marker_identity(path, inspector, d.require)
