"""Reviewer-requested Node reader regressions; synthetic ownership, no root writes."""
import importlib.util
import os
from pathlib import Path
import types

import pytest

MODULE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/runtime-process-r7.py')


@pytest.mark.parametrize('change',[None,'fd-replaced','path-replaced','size','mode','owner','link','oversize'])
def test_root_reader_closed_success_and_races(tmp_path,monkeypatch,change):
    spec=importlib.util.spec_from_file_location('tested_root_reader',MODULE)
    r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
    actual=tmp_path/'node'; actual.write_bytes(b'exact synthetic image'); actual.chmod(0o755)
    real_fstat=os.fstat
    fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
    calls=[]
    def info(s,phase):
        d={k:getattr(s,k) for k in fields}; d.update(st_uid=0,st_gid=0)
        if change=='fd-replaced' and phase=='after': d['st_ino']+=1
        elif change=='path-replaced' and phase=='path': d['st_ino']+=1
        elif change=='size' and phase=='after': d['st_size']+=1
        elif change=='mode': d['st_mode']=0o100777
        elif change=='owner': d['st_uid']=1000
        elif change=='link': d['st_nlink']=2
        elif change=='oversize': d['st_size']=257<<20
        return types.SimpleNamespace(**d)
    def observed(fd):
        calls.append(fd)
        return info(real_fstat(fd),'before' if len(calls)==1 else 'after')
    class FixturePath:
        def __init__(self,value): assert value=='/usr/bin/node'
        def __str__(self): return '/usr/bin/node'
        def __fspath__(self): return str(actual)
        def resolve(self,strict): return self
        def lstat(self): return info(actual.lstat(),'path')
    monkeypatch.setattr(r,'Path',FixturePath)
    monkeypatch.setattr(r.os,'fstat',observed)
    if change is None:
        assert r.root_binary('/usr/bin/node')==b'exact synthetic image'
        assert len(calls)==2
    else:
        with pytest.raises(RuntimeError): r.root_binary('/usr/bin/node')
