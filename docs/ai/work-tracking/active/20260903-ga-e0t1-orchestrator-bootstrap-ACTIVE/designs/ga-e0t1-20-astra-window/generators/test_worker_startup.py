"""Offline probe tests, never a substitute for the actual worker's sandbox."""
import errno
import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('startup',Path(__file__).with_name('worker-startup.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


@pytest.mark.parametrize('code',[errno.EACCES,errno.EPERM,errno.EROFS])
def test_foreign_probe_accepts_only_denial(tmp_path,monkeypatch,code):
    def denied(path,raw): raise OSError(code,'synthetic permission denial')
    monkeypatch.setattr(p,'exclusive',denied)
    result=p.foreign_probe(tmp_path)
    assert result['denied'] and result['errno']==code
    assert not (tmp_path/'unexpected-write').exists()


@pytest.mark.parametrize('code',[errno.ENOENT,errno.ENOSPC,errno.EIO])
def test_unrelated_io_failure_is_not_a_sandbox_pass(tmp_path,monkeypatch,code):
    def failed(path,raw): raise OSError(code,'synthetic failure')
    monkeypatch.setattr(p,'exclusive',failed)
    with pytest.raises(RuntimeError,match='not a sandbox refusal'): p.foreign_probe(tmp_path)


def test_broken_sandbox_preserves_successful_negative_marker(tmp_path):
    with pytest.raises(RuntimeError,match='allowed an out-of-workspace write'): p.foreign_probe(tmp_path)
    assert (tmp_path/'unexpected-write').read_bytes().startswith(b'Unexpected sandbox write')
    with pytest.raises(RuntimeError,match='already consumed'): p.foreign_probe(tmp_path)


def test_refusal_after_partial_write_is_not_pass(tmp_path,monkeypatch):
    def partial(path,raw):
        path.write_bytes(raw)
        raise OSError(errno.EPERM,'failure after partial write')
    monkeypatch.setattr(p,'exclusive',partial)
    with pytest.raises(RuntimeError,match='ambiguous result'): p.foreign_probe(tmp_path)
    assert (tmp_path/'unexpected-write').exists()


def test_symlink_parent_refuses_without_touching_target(tmp_path):
    real=tmp_path/'real';real.mkdir()
    alias=tmp_path/'alias';alias.symlink_to(real,target_is_directory=True)
    with pytest.raises(RuntimeError,match='directory authority'): p.foreign_probe(alias)
    assert list(real.iterdir())==[]


def test_group_writable_parent_refuses(tmp_path):
    tmp_path.chmod(0o777)
    with pytest.raises(RuntimeError,match='directory authority'): p.foreign_probe(tmp_path)


def test_exclusive_evidence_never_overwrites(tmp_path):
    path=tmp_path/'evidence';p.exclusive(path,b'first')
    with pytest.raises(FileExistsError):p.exclusive(path,b'second')
    assert path.read_bytes()==b'first' and path.stat().st_mode&0o777==0o600


def test_source_is_inert_on_import_and_denies_coordinator_context(monkeypatch):
    monkeypatch.setattr(p.Path,'cwd',lambda:Path('/tmp'))
    with pytest.raises(RuntimeError,match='worker context'):p.main('ci-example')


def test_probe_does_not_claim_native_permission_or_source_release():
    text=Path(p.__file__).read_text()
    assert 'source_edit_released=False' in text
    assert "['gpg'" not in text and 'gpg --version' not in text
    assert "auth.returncode == 0 and lines == 'Logged in using ChatGPT'" in text
    assert 'credential_values_exported=False' in text
    assert 'os.environ.get(name)' not in text
