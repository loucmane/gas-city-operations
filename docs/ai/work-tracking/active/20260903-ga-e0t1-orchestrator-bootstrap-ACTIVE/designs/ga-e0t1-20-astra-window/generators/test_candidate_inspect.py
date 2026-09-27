"""Disposable file fixtures only. No host lifecycle or worker proof claims."""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import types

import pytest

HERE = Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE/(name+'.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_bounded_read_and_exact_inventory(tmp_path):
    m = load('candidate-inspect')
    root=tmp_path/'evidence';root.mkdir(mode=0o700)
    path=root/'red.json';path.write_bytes(b'{}\n');path.chmod(0o600)
    assert m.file_bytes(path)==b'{}\n'
    result=m.inventory(root,['red.json'])
    assert result=={'red.json':dict(size=3,sha256=hashlib.sha256(b'{}\n').hexdigest(),mode=0o600)}
    with pytest.raises(RuntimeError,match='inventory differ'):m.inventory(root,[])


@pytest.mark.parametrize('kind',['link','hardlink','fifo','shared','large'])
def test_untrusted_file_shapes_refuse(tmp_path,kind):
    m=load('candidate-inspect');path=tmp_path/'input'
    if kind=='link':
        target=tmp_path/'real';target.write_bytes(b'x');path.symlink_to(target)
    elif kind=='hardlink':
        target=tmp_path/'real';target.write_bytes(b'x');os.link(target,path)
    elif kind=='fifo':os.mkfifo(path)
    else:
        path.write_bytes(b'abc')
        if kind=='shared':path.chmod(0o666)
    with pytest.raises(RuntimeError):m.file_bytes(path,limit=2 if kind=='large' else 32)


def test_inventory_refuses_extra_and_nested_alias(tmp_path):
    m=load('candidate-inspect');root=tmp_path/'root';root.mkdir()
    (root/'ok').write_text('ok')
    (root/'extra').write_text('extra')
    with pytest.raises(RuntimeError):m.inventory(root,['ok'])
    (root/'link').symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(RuntimeError):m.inventory(root,['ok','extra','link'])


def test_common_git_file_read_and_special_refusals(tmp_path):
    g=load('build');_,new=g.assemble()
    m=types.ModuleType('common_fixture')
    exec(compile(new['common-snapshot-r1.py'],'common-fixture','exec'),m.__dict__)
    path=tmp_path/'object';path.write_bytes(b'object');path.chmod(0o444)
    before=path.stat().st_atime_ns
    assert m.entry(path)['sha256']==hashlib.sha256(b'object').hexdigest()
    assert path.stat().st_atime_ns==before
    assert m.plain(path)=='object'
    link=tmp_path/'link';link.symlink_to(path)
    with pytest.raises(AssertionError):m.entry(link)
    pipe=tmp_path/'pipe';os.mkfifo(pipe)
    with pytest.raises(AssertionError):m.entry(pipe)


def test_common_comparison_refuses_every_delta(tmp_path):
    g=load('build');_,new=g.assemble()
    m=types.ModuleType('common_compare')
    exec(compile(new['common-snapshot-r1.py'],'common-fixture','exec'),m.__dict__)
    before=dict(candidate_branch=m.BASE,entries={'index':dict(mode=0o644,type=stat.S_IFREG,
        uid=1000,gid=1000,size=1,nlink=1,sha256='a'*64)})
    import copy
    assert m.compare(before,copy.deepcopy(before))==[]
    for key,value in [('mode',0o600),('type',stat.S_IFLNK),('uid',0),('gid',0),
                      ('size',2),('nlink',2),('sha256','b'*64)]:
        after=copy.deepcopy(before);after['entries']['index'][key]=value
        assert m.compare(before,after)==['index']
    after=copy.deepcopy(before);after['candidate_branch']='b'*40
    assert m.compare(before,after)==['candidate_branch']
