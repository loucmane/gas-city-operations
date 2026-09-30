"""Real no-follow reader fixtures; no native queue or host mutation."""
import os
from pathlib import Path
import types
import pytest

HERE=Path(__file__).parent
def load(name):
    m=types.ModuleType(name);m.__file__=str(HERE/name)
    exec(compile((HERE/name).read_bytes(),m.__file__,'exec'),m.__dict__)
    return m

def fixture(tmp_path,monkeypatch):
    g=load('queue-guard.py');w=load('window-base.py')
    city=tmp_path/'city';d=city/'.gc/nudges';d.mkdir(parents=True)
    p=d/'state.json';p.write_bytes(b'{"dead":[]}\n');p.chmod(0o644)
    monkeypatch.setattr(g,'CITY',city)
    return g,w,p

def test_native_core_0644_contract_is_readable_without_permission_change(tmp_path,monkeypatch):
    g,w,p=fixture(tmp_path,monkeypatch)
    before=p.stat()
    assert g.read_queue(w)==b'{"dead":[]}\n'
    after=p.stat()
    assert before==after

@pytest.mark.parametrize('mode',[0o600,0o664,0o666,0o777,0o444])
def test_only_exact_native_mode_is_accepted(tmp_path,monkeypatch,mode):
    g,w,p=fixture(tmp_path,monkeypatch);p.chmod(mode)
    with pytest.raises(RuntimeError):g.read_queue(w)

@pytest.mark.parametrize('kind',['symlink','hardlink','parent-writable','oversize','fifo'])
def test_actual_reader_rejects_aliases_bounds_and_unsafe_nodes(tmp_path,monkeypatch,kind):
    g,w,p=fixture(tmp_path,monkeypatch)
    if kind=='hardlink':os.link(p,p.with_name('alias'))
    elif kind=='parent-writable':p.parent.chmod(0o777)
    elif kind=='oversize':
        with p.open('r+b') as f:f.truncate((16<<20)+1)
    else:
        p.rename(p.with_name('preserved'))
        if kind=='symlink':p.symlink_to(p.with_name('preserved'))
        else:os.mkfifo(p,0o644)
    with pytest.raises((RuntimeError,OSError)):g.read_queue(w)
