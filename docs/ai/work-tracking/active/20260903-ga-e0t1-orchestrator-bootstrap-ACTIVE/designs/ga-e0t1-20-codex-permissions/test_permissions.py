"""Disposable only; no live clients, permissions, services, or worker jobs."""
import json
import inspect
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest
import permissions as p


@pytest.fixture
def case(tmp_path):
    target = tmp_path / 'sessions'; target.mkdir(mode=0o775); target.chmod(0o775)
    rules = tmp_path / 'rules'; rules.write_bytes(b'allow only exact operation\n'); rules.chmod(0o664)
    historical = target / 'old.jsonl'; historical.write_bytes(b'unchanged history\n'); historical.chmod(0o664)
    evidence = tmp_path / 'evidence'; evidence.mkdir(mode=0o700)
    paths = [target, rules]
    fds = {str(x): p.open_exact(x, x.is_dir()) for x in paths}
    initial = {x: p.image(fd) for x, fd in fds.items()}
    history = p.inventory(target)
    def guard():p.preserve_inventory(history, p.inventory(target), fds)
    try:
        yield fds, initial, evidence, guard, target, historical
    finally:
        for fd in fds.values():os.close(fd)


def test_apply_and_no_replay_without_changing_history(case):
    fds, before, evidence, guard, target, historical = case
    original = historical.read_bytes(); old = historical.stat()
    after = p.transaction(fds, before, evidence, guard, lambda _: {'fixture': True})
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert os.getxattr(target, p.DEFAULT) == p.PRIVATE
    assert all(stat.S_IMODE(v['stat']['mode']) == (0o700 if stat.S_ISDIR(v['stat']['mode']) else 0o600) for v in after.values())
    assert historical.read_bytes() == original and historical.stat() == old
    assert json.loads((evidence/'result.json').read_text())['ok']
    assert json.loads((evidence/'commit-intent.json').read_text())['postimage_sha256']==p.sha((evidence/'postimage.json').read_bytes())
    with pytest.raises(RuntimeError, match='preimage'):p.transaction(fds,before,evidence,guard,lambda _:True)


@pytest.mark.parametrize('at', [1, 2, 3])
@pytest.mark.parametrize('kind', [RuntimeError, KeyboardInterrupt])
def test_exact_rollback_after_each_step(case, at, kind):
    fds,before,evidence,guard,_,_ = case
    def fail(n):
        if n == at:raise kind('injected')
    with pytest.raises(kind):p.transaction(fds,before,evidence,guard,lambda _:True,fail)
    assert {k:p.semantic(p.image(fd)) for k,fd in fds.items()} == {k:p.semantic(v) for k,v in before.items()}
    assert json.loads((evidence/'failure.json').read_text())['rollback']=='verified'


@pytest.mark.parametrize('action', ['mode','default'])
def test_syscall_succeeds_then_raises_is_classified(case, monkeypatch, action):
    fds,before,evidence,guard,_,_ = case
    original=p.operate; fired=False
    def fail(fd,a,v):
        nonlocal fired
        original(fd,a,v)
        if a==action and not fired:
            fired=True
            raise KeyboardInterrupt('after atomic syscall')
    monkeypatch.setattr(p,'operate',fail)
    with pytest.raises(KeyboardInterrupt):p.transaction(fds,before,evidence,guard,lambda _:True)
    assert all(p.semantic(p.image(fd))==p.semantic(before[k]) for k,fd in fds.items())


@pytest.mark.parametrize('change', ['bytes','mode','rename','new-child','old-history'])
def test_ambiguous_drift_is_not_overwritten(case, change):
    fds,before,evidence,guard,target,history=case
    rules=Path(next(k for k in fds if k.endswith('/rules')))
    def race(_):
        if change=='bytes':rules.write_bytes(b'new content')
        elif change=='mode':rules.chmod(0o640)
        elif change=='rename':rules.rename(rules.with_name('preserved')); rules.write_text('replacement')
        elif change=='new-child':(target/'new').write_text('new')
        else:history.write_text('concurrent')
        raise RuntimeError('primary failure')
    with pytest.raises(p.Ambiguous):p.transaction(fds,before,evidence,guard,lambda _:True,race)
    assert (evidence/'ambiguous.json').is_file()
    assert not (evidence/'result.json').exists() and not (evidence/'failure.json').exists()
    if change=='bytes':assert rules.read_bytes()==b'new content'
    if change=='mode':assert stat.S_IMODE(rules.stat().st_mode)==0o640


def test_preflight_refuses_xattr_and_missing_guard(case):
    fds,before,evidence,guard,target,_=case
    os.setxattr(target,p.DEFAULT,p.PRIVATE)
    with pytest.raises(RuntimeError,match='preimage'):p.transaction(fds,before,evidence,guard,lambda _:True)
    assert not list(evidence.iterdir())


def test_intermediate_and_final_symlinks_refuse(tmp_path):
    directory=tmp_path/'real';directory.mkdir()
    file=directory/'file';file.write_text('x')
    link=tmp_path/'link';link.symlink_to(directory)
    for path in (link,link/'file'):
        with pytest.raises(OSError):p.open_exact(path,path.is_dir())
    other=directory/'other';other.symlink_to(file)
    with pytest.raises(OSError):p.open_exact(other)
    os.link(file,directory/'hard')
    fd=p.open_exact(file)
    try:
        with pytest.raises(RuntimeError,match='hardlink'):p.image(fd)
    finally:os.close(fd)


@pytest.mark.parametrize('mask',[0o002,0o022,0o077])
@pytest.mark.parametrize('requested',[0o666,0o600])
def test_private_creation_inherits_across_future_year_month_day(tmp_path,mask,requested):
    os.setxattr(tmp_path,p.DEFAULT,p.PRIVATE)
    code='''import json,os,pathlib,stat,sys
os.umask(int(sys.argv[1]))
path=pathlib.Path('2027/01/01');path.mkdir(parents=True,mode=0o777)
fd=os.open(path/'new.jsonl',os.O_CREAT|os.O_EXCL|os.O_WRONLY,int(sys.argv[2]));os.close(fd)
print(json.dumps({'file':stat.S_IMODE((path/'new.jsonl').stat().st_mode),
'dirs':[stat.S_IMODE(p.stat().st_mode) for p in [path,path.parent,path.parent.parent]],
'acl':os.getxattr(path,'system.posix_acl_default').hex()}))
'''
    r=subprocess.run([sys.executable,'-I','-B','-c',code,str(mask),str(requested)],cwd=tmp_path,
        env={'PATH':'/usr/bin:/bin','HOME':str(tmp_path)},capture_output=True,text=True,timeout=10,check=True)
    assert not r.stderr
    assert json.loads(r.stdout)==dict(file=0o600,dirs=[0o700]*3,acl=p.PRIVATE.hex())


def test_proof_failure_rolls_back(case):
    fds,before,evidence,guard,_,_=case
    def fail(_):raise RuntimeError('proof refused')
    with pytest.raises(RuntimeError,match='proof refused'):p.transaction(fds,before,evidence,guard,fail)
    assert all(p.semantic(p.image(fd))==p.semantic(before[k]) for k,fd in fds.items())


def test_saved_images_preserve_exact_nanosecond_integers(case):
    fds,_,evidence,_,_=case[:5]
    path=next(k for k in fds if k.endswith('/rules'))
    exact=1785761543210232905
    os.utime(path,ns=(exact,exact))
    value=p.image(fds[path])
    p.save(evidence,'exact-nanoseconds.json',value)
    loaded=json.loads((evidence/'exact-nanoseconds.json').read_text())
    assert loaded==value and loaded['stat']['mtime_ns']==exact
    assert loaded['stat']['mtime_ns']!=int(float(exact))


def test_rollback_failure_is_not_called_restored(case,monkeypatch):
    fds,before,evidence,guard,_,_=case
    original=p.operate
    def fail(fd,a,v):
        if a=='mode' and v==0o775:raise OSError('rollback failure')
        return original(fd,a,v)
    monkeypatch.setattr(p,'operate',fail)
    def injected(_):raise RuntimeError('stop')
    with pytest.raises(p.Ambiguous):p.transaction(fds,before,evidence,guard,lambda _:True,injected)
    assert (evidence/'ambiguous.json').is_file() and not (evidence/'failure.json').exists()


def test_signal_between_history_record_and_pending_clear_rolls_back_once(case):
    fds,before,evidence,guard,_,_=case
    lines,start=inspect.getsourcelines(p.transaction)
    stop_line=next(start+i for i,line in enumerate(lines)
        if line.strip()=='attempt = None' and i
        and ('history.append' in lines[i-1] or 'history[' in lines[i-1]))
    fired=False
    def trace(frame,event,arg):
        nonlocal fired
        if (frame.f_code is p.transaction.__code__ and event=='line'
                and frame.f_lineno==stop_line and frame.f_locals.get('action')=='default'
                and not fired):
            fired=True
            raise KeyboardInterrupt('between completed record and pending clear')
        return trace
    previous=sys.gettrace()
    try:
        sys.settrace(trace)
        with pytest.raises(KeyboardInterrupt):
            p.transaction(fds,before,evidence,guard,lambda _:True)
    finally:sys.settrace(previous)
    assert fired
    assert len(list(evidence.glob('rollback-*.json')))==2
    assert all(p.semantic(p.image(fd))==p.semantic(before[k]) for k,fd in fds.items())
    assert json.loads((evidence/'failure.json').read_text())['rollback']=='verified'


def test_final_rollback_rereads_already_restored_targets(case,monkeypatch):
    fds,before,evidence,guard,_,_=case
    rules=Path(next(k for k in fds if k.endswith('/rules')))
    original=p.operate
    def race(fd,action,value):
        original(fd,action,value)
        if action=='mode' and value==0o775:rules.chmod(0o640)
    monkeypatch.setattr(p,'operate',race)
    def fail(n):
        if n==3:raise RuntimeError('start rollback after all operations')
    with pytest.raises(p.Ambiguous):
        p.transaction(fds,before,evidence,guard,lambda _:True,fail)
    assert stat.S_IMODE(rules.stat().st_mode)==0o640
    assert not (evidence/'failure.json').exists()


@pytest.mark.parametrize('stage',['before','after'])
def test_success_publication_fault_never_rolls_back_committed_permissions(case,monkeypatch,stage):
    fds,before,evidence,guard,target,_=case
    original=p.save
    def fail(root,name,value):
        if name=='result.json' and stage=='before':raise KeyboardInterrupt('before result publication')
        original(root,name,value)
        if name=='result.json':raise KeyboardInterrupt('after result bytes were published')
    monkeypatch.setattr(p,'save',fail)
    with pytest.raises(BaseException) as caught:
        p.transaction(fds,before,evidence,guard,lambda _:True)
    assert isinstance(caught.value,p.Ambiguous) and 'commit' in str(caught.value)
    assert stat.S_IMODE(target.stat().st_mode)==0o700
    assert os.getxattr(target,p.DEFAULT)==p.PRIVATE
    if stage=='after':assert json.loads((evidence/'result.json').read_text())['ok']
    else:assert not (evidence/'result.json').exists()
    assert json.loads((evidence/'commit-interrupted.json').read_text())['rollback']=='forbidden'
    assert not (evidence/'failure.json').exists()
