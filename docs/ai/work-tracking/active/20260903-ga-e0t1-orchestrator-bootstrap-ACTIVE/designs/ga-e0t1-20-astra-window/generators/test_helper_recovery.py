"""Recovery-only fixtures. No production write or live launch."""
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import helper_recovery as h


@pytest.fixture
def pair(tmp_path, monkeypatch):
    origin = tmp_path / 'worker'; archive = tmp_path / 'archive'
    origin.mkdir(mode=0o700); archive.mkdir(mode=0o700)
    source = origin / 'helper'; source.write_bytes(b'preserve exactly\n'); source.chmod(0o755)
    monkeypatch.setattr(h, 'STAT', h.attrs(source))
    monkeypatch.setattr(h, 'HELPER_SHA', h.digest(source.read_bytes()))
    return source, archive / 'helper'


def test_exact_archive_preserves_inode_bytes_and_no_replay(pair):
    source, target = pair; raw=source.read_bytes(); initial=h.attrs(source)
    h.archive_exact(source, target)
    assert not source.exists() and target.read_bytes()==raw
    after=h.attrs(target)
    assert {k:v for k,v in initial.items() if k!='ctime_ns'}=={k:v for k,v in after.items() if k!='ctime_ns'}
    with pytest.raises(FileNotFoundError): h.archive_exact(source,target)


@pytest.mark.parametrize('fault', ['bytes','mode','link','inode','destination','destination-link','parent-link'])
def test_drift_never_moves_or_overwrites(pair, fault):
    source,target=pair
    if fault=='bytes':source.write_bytes(b'changed')
    elif fault=='mode':source.chmod(0o644)
    elif fault=='link':os.link(source,source.with_name('second'))
    elif fault=='inode':
        old=source.with_name('old');source.rename(old);source.write_bytes(old.read_bytes());source.chmod(0o755)
    elif fault=='destination':target.write_bytes(b'existing')
    elif fault=='destination-link':target.symlink_to(source)
    elif fault=='parent-link':
        alias=target.parent.with_name('alias');alias.symlink_to(target.parent);target=alias/target.name
    raw=source.read_bytes()
    with pytest.raises((RuntimeError,OSError)):h.archive_exact(source,target)
    assert source.read_bytes()==raw
    if fault=='destination':assert target.read_bytes()==b'existing'


def test_no_replace_race_preserves_both(pair, monkeypatch):
    source,target=pair
    real=h.ctypes.CDLL
    class Race:
        def __init__(self):self.renameat2=self
        def __call__(self,*args):
            target.write_bytes(b'racer')
            fn=real(None,use_errno=True).renameat2
            fn.argtypes=[h.ctypes.c_int,h.ctypes.c_char_p,h.ctypes.c_int,h.ctypes.c_char_p,h.ctypes.c_uint]
            return fn(*args)
    monkeypatch.setattr(h.ctypes,'CDLL',lambda *args,**kwargs:Race())
    with pytest.raises(OSError) as exc:h.archive_exact(source,target)
    assert exc.value.errno==errno.EEXIST
    assert source.exists() and target.read_bytes()==b'racer'


def test_unknown_or_unbound_apply_refuses(monkeypatch):
    monkeypatch.setattr(sys,'argv',['helper','apply'])
    with pytest.raises(RuntimeError,match='bound user'):h.main()
    monkeypatch.setattr(sys,'argv',['helper','--force'])
    with pytest.raises(RuntimeError,match='exact action'):h.main()


def test_inspection_boundary_is_read_only_with_exact_city():
    argv=h.read_only_argv(['command'],'/exact-city')
    assert argv[:4]==[h.BWRAP,'--ro-bind','/','/']
    assert argv[argv.index('--chdir')+1]=='/exact-city'
    assert '--bind' not in argv and '--unshare-net' not in argv
    assert argv[-2:]==['--','command']


def test_real_namespace_denies_child_writes_and_allows_reads(tmp_path):
    h.verify_sandbox_binary()
    path=tmp_path/'baseline';path.write_text('unchanged')
    child='import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("bad")'
    code=('import pathlib,subprocess,sys; p=pathlib.Path(sys.argv[1]); '
          'assert p.read_text()=="unchanged"; '
          'r=subprocess.run([sys.executable,"-I","-B","-c",'+repr(child)+',str(p)],capture_output=True); '
          'assert r.returncode!=0 and b"Read-only file system" in r.stderr; '
          'assert p.read_text()=="unchanged"; print("READ_ONLY_DESCENDANT_PASS")')
    result=subprocess.run(h.read_only_argv(['/usr/bin/python3','-I','-B','-c',code,str(path)],tmp_path),
                          capture_output=True,timeout=30)
    assert result.returncode==0, result.stderr.decode()
    assert result.stdout==b'READ_ONLY_DESCENDANT_PASS\n' and path.read_text()=='unchanged'


@pytest.mark.parametrize('fault', [None, 'reap', 'group', 'failures', 'survivor', 'timeout', 'error', 'exit', 'proof'])
def test_child_requires_containment_and_complete_proof(tmp_path, monkeypatch, fault):
    monkeypatch.setattr(h, 'ARCHIVE', tmp_path)
    monkeypatch.setattr(h, '_SOURCE_SHA', 'a'*64, raising=False)
    cleanup=dict(direct_child_reaped=True, owned_process_group_gone=True, failures=[], unexpected_survivors=False)
    report=dict(ok=True, read_only_mounts=True, original_entries=8036)
    result=dict(cleanup=cleanup, timed_out=False, primary_error=None, exit_code=0)
    if fault=='reap':cleanup['direct_child_reaped']=False
    if fault=='group':cleanup['owned_process_group_gone']=False
    if fault=='failures':cleanup['failures']=['injected']
    if fault=='survivor':cleanup['unexpected_survivors']=True
    if fault=='timeout':result['timed_out']=True
    if fault=='error':result['primary_error']={'error':'injected'}
    if fault=='exit':result['exit_code']=1
    if fault=='proof':report['original_entries']=8037
    result['stdout']=json.dumps(report)
    def run(**kw):
        assert kw['cwd']==tmp_path and kw['timeout']==300
        assert kw['argv'][:4]==[h.BWRAP,'--ro-bind','/','/']
        assert kw['environment']['GC_CITY']==str(tmp_path)
        return result
    owned=SimpleNamespace(_run_owned_phase=run)
    w=SimpleNamespace(LAUNCH=Path('/launch'),CITY=tmp_path,
                      load_support=lambda:(None,SimpleNamespace(ENV={}),owned))
    if fault is None:assert h.child(w,owned,'inner-before')==report
    else:
        with pytest.raises(RuntimeError):h.child(w,owned,'inner-before')
