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
    result=dict(cleanup=cleanup, timed_out=False, primary_error=None, exit_code=0, stderr='')
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


def test_transitive_host_gc_calls_confined_other_checks_unchanged(tmp_path, monkeypatch):
    gc=['/exact/gc','--city',str(tmp_path)]
    calls=[]
    def original(argv, timeout=30):
        assert argv[0]!='/exact/gc'
        calls.append(('host',argv,timeout));return b'service'
    o=SimpleNamespace(command=original,GC='/exact/gc')
    def host(observer):
        assert observer is o
        assert observer.command(['/usr/bin/systemctl','show','fixed.service'])==b'service'
        assert observer.command(gc+['status','--json'])==b'status'
        assert observer.command(gc+['session','list','--json'])==b'sessions'
        with pytest.raises(RuntimeError):observer.command(gc+['resume'])
        return 'host-process-checks-retained'
    def isolated(w,owned,name,argv,timeout):
        calls.append(('confined',argv,timeout))
        assert timeout==30 and name in ('before-status','before-sessions')
        return name.split('-')[-1]
    monkeypatch.setattr(h,'isolated',isolated)
    w=SimpleNamespace(GC=gc,host=host)
    assert h.confined_host_observation(w,o,object(),'before')=='host-process-checks-retained'
    assert o.command is original and [x[0] for x in calls]==['host','confined','confined']


def test_phase_persistence_is_exclusive_no_follow_and_durable(tmp_path, monkeypatch):
    monkeypatch.setattr(h,'ARCHIVE',tmp_path)
    path=tmp_path/'before-status-phase.json'
    h.persist_phase(path,{'ok':True})
    saved=path.read_bytes()
    with pytest.raises(FileExistsError):h.persist_phase(path,{'ok':False})
    assert path.read_bytes()==saved
    link=tmp_path/'after-status-phase.json';link.symlink_to(path)
    with pytest.raises(FileExistsError):h.persist_phase(link,{'ok':False})
    assert path.read_bytes()==saved
    with pytest.raises(RuntimeError):h.persist_phase(tmp_path.parent/'escape-phase.json',{})


@pytest.mark.parametrize('fault',[None,'bead-note-drift','interrupt-after-rename'])
def test_main_success_or_preserved_partial_never_replays(pair, tmp_path, monkeypatch, fault):
    source,unused=pair
    destination=tmp_path/'fresh-evidence'
    monkeypatch.setattr(h,'ARCHIVE',destination)
    monkeypatch.setattr(h,'REL',source.name)
    monkeypatch.setattr(h,'_SOURCE_SHA',h.digest(h.read(Path(h.__file__))),raising=False)
    monkeypatch.setattr(sys,'argv',['helper','apply'])
    monkeypatch.setattr(h,'verify_sandbox_binary',lambda:None)
    w=SimpleNamespace(WORK=source.parent,load_support=lambda:(None,None,None))
    monkeypatch.setattr(h,'load_package',lambda:(w,None))
    monkeypatch.setattr(h,'job_context',lambda value:None)
    monkeypatch.setattr(h,'host_state',lambda *args:{'exact_host':'same'})
    def child(*args):
        mode=args[-1]
        return dict(ok=True,pair_sha256='b'*64 if fault=='bead-note-drift' and mode=='inner-after' else 'a'*64)
    monkeypatch.setattr(h,'child',child)
    if fault=='interrupt-after-rename':
        archive=h.archive_exact
        def interrupted(*args):archive(*args);raise KeyboardInterrupt('fixture after rename')
        monkeypatch.setattr(h,'archive_exact',interrupted)
    if fault is None:
        h.main()
        assert json.loads((destination/'result.json').read_text())['ok']
    else:
        with pytest.raises((RuntimeError,KeyboardInterrupt)):h.main()
        failed=json.loads((destination/'failure.json').read_text())
        assert failed['source_exists'] is False and failed['archive_exists'] is True
        assert failed['retry'] is False and not (destination/'result.json').exists()
    assert not source.exists() and (destination/'gc-beads-bd.sh').read_bytes()==b'preserve exactly\n'
    with pytest.raises(FileNotFoundError):h.main()
