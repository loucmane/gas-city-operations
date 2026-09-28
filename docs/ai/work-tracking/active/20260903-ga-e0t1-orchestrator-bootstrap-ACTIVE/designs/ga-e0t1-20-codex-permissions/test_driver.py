"""Driver contracts with fake proc and disposable filesystem only."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import permissions as p

spec=importlib.util.spec_from_file_location('migration',Path(__file__).with_name('apply.py'))
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


def proc(tmp_path,pid,state='S',exe='/usr/bin/editor',env=b''):
    base=tmp_path/str(pid);base.mkdir()
    fields=[state]+['0']*18+['12345']
    (base/'stat').write_text(str(pid)+' (name) '+' '.join(fields))
    (base/'comm').write_text(Path(exe).name)
    (base/'exe').symlink_to(exe)
    (base/'environ').write_bytes(env)
    (base/'fd').mkdir()
    return base


@pytest.mark.parametrize('code_home',[b'/home/loucmane/.codex',None])
def test_affected_live_native_client_refuses(tmp_path,code_home):
    env=b'HOME=/home/loucmane\0'
    if code_home:env+=b'CODEX_HOME='+code_home+b'\0'
    proc(tmp_path,900001,exe='/usr/bin/codex',env=env)
    with pytest.raises(RuntimeError,match='affected live'):d.clients(tmp_path)


def test_unaffected_client_uses_separate_home_and_does_not_emit_secret(tmp_path):
    home=tmp_path/'separate';home.mkdir()
    env=b'HOME=/home/loucmane\0CODEX_HOME='+os.fsencode(home)+b'\0SECRET=never-record-this\0'
    proc(tmp_path,900001,exe='/usr/bin/codex',env=env)
    out=d.clients(tmp_path)
    assert out['unaffected_codex_clients'][0]['code_home']==str(home)
    assert 'never-record' not in json.dumps(out)


def test_unrelated_program_with_open_target_is_refused(tmp_path):
    base=proc(tmp_path,900001)
    (base/'fd/3').symlink_to(d.HOME/'rules/default.rules')
    with pytest.raises(RuntimeError,match='affected open'):d.clients(tmp_path)


def test_zombie_exclusion_is_narrow(tmp_path):
    base=proc(tmp_path,900001,state='Z')
    (base/'fd').rmdir();(base/'exe').unlink()
    out=d.clients(tmp_path)
    assert out['exited_no_file_table']==[dict(pid=900001,start='12345',state='Z')]
    (base/'stat').write_text('900001 (name) '+' '.join(['S']+['0']*18+['12345']))
    with pytest.raises(RuntimeError,match='incomplete live'):d.clients(tmp_path)


def test_live_unreadable_process_refuses(tmp_path,monkeypatch):
    base=proc(tmp_path,900001)
    original=Path.iterdir
    def denied(path):
        if path==base/'fd':raise PermissionError('denied')
        return original(path)
    monkeypatch.setattr(Path,'iterdir',denied)
    with pytest.raises(PermissionError):d.clients(tmp_path)


def test_creation_proof_uses_actual_installed_acl_on_disposable_mirrors(tmp_path,monkeypatch):
    target=tmp_path/'live-fixture';target.mkdir();os.setxattr(target,p.DEFAULT,p.PRIVATE)
    root=tmp_path/'output';root.mkdir(mode=0o700);monkeypatch.setattr(d,'ROOT',root)
    fd=p.open_exact(target,True);old=p.image(fd)
    try:
        out=d.creation_proof(p,{str(target):fd})
        assert out['cases']==6 and out['all_private']
        assert p.image(fd)==old and not list(target.iterdir())
    finally:os.close(fd)


def test_bound_entry_and_unknown_actions_refuse(monkeypatch):
    monkeypatch.setattr(d.sys,'argv',['apply.py','apply'])
    with pytest.raises(RuntimeError,match='bound source'):d.main()
    monkeypatch.setattr(d,'_SOURCE_SHA','test',raising=False)
    monkeypatch.setattr(d,'read',lambda *a: b'')
    monkeypatch.setattr(d.sys,'argv',['apply.py','--force'])
    with pytest.raises(RuntimeError,match='unknown operation'):d.main()


def test_scope_is_exact_six_targets_and_no_transcripts():
    value=json.loads(Path(__file__).with_name('preimage.json').read_text())
    assert set(value)=={str(d.HOME/n) for n in ('rules','rules/default.rules','sessions','sessions/2026','sessions/2026/09','sessions/2026/09/28')}
    assert sum('sha256' in x for x in value.values())==1
    assert all(not x['xattrs'] for x in value.values())
    assert value[str(d.HOME/'rules/default.rules')]['sha256']=='3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516'


def test_source_chain_pins_exact_package_bytes():
    root=Path(__file__).parent
    assert hashlib.sha256((root/'permissions.py').read_bytes()).hexdigest()==d.POLICY_SHA
    assert hashlib.sha256((root/'preimage.json').read_bytes()).hexdigest()==d.PREIMAGE_SHA
    assert hashlib.sha256((root/'apply.py').read_bytes()).hexdigest() in (root/'operator/APPLY.sh').read_text()


def support_fixture(monkeypatch,action):
    events=[]
    h=SimpleNamespace()
    def host_check():
        events.append('host_binary_check')
        raise RuntimeError('root ownership unavailable inside child namespace')
    h.verify_sandbox_binary=host_check
    w=SimpleNamespace(load_support=lambda:('b','o','owned'))
    def read(path,pin=None):
        if Path(path).name=='assembly.json':return b'{"files":{"window-base-r11.py":"pin"}}'
        return b''
    monkeypatch.setattr(d,'read',read)
    monkeypatch.setattr(d,'load',lambda path,pin,name: w if name=='bound_window' else h)
    monkeypatch.setattr(d,'_SOURCE_SHA','test',raising=False)
    monkeypatch.setattr(d.sys,'argv',['apply.py',action])
    monkeypatch.setattr(d,'context',lambda:events.append('host_context'))
    monkeypatch.setattr(d,'tree_proof',lambda *a:events.append('readonly_tree_proof') or {'ok':True})
    return events


def test_inner_uses_readonly_proof_not_impossible_host_uid_check(monkeypatch,capsys):
    events=support_fixture(monkeypatch,'inner')
    d.main()
    assert events==['readonly_tree_proof']
    assert json.loads(capsys.readouterr().out)=={'ok':True}


def test_apply_checks_host_context_then_real_host_binary(monkeypatch):
    events=support_fixture(monkeypatch,'apply')
    with pytest.raises(RuntimeError,match='root ownership'):d.main()
    assert events==['host_context','host_binary_check']


def test_inner_writable_mount_refuses_before_inventory(monkeypatch):
    def refuse(paths):raise RuntimeError('writable mount refused')
    def no_read(*a):raise AssertionError('inventory read before readonly proof')
    monkeypatch.setattr(d,'read',no_read)
    w=SimpleNamespace(CITY='city',WORK='work',ADMIN='admin')
    b=SimpleNamespace(CACHE='cache',PROTECTED=['assets','backups'])
    with pytest.raises(RuntimeError,match='writable mount'):
        d.tree_proof(w,SimpleNamespace(prove_read_only=refuse),b,object())


CACHE_KEY='954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git'
OLD_NS=1790604770227789531
NEW_NS=1790621288720671640


def tree_fixture(monkeypatch):
    prior=dict(cache=dict(inventory={CACHE_KEY:dict(
        atime_ns=1790523123135207314,ctime_ns=OLD_NS,mtime_ns=OLD_NS,
        device=2096,gid=1000,inode=4111724,mode=493,nlink=8,size=4096,type=16384,uid=1000),
        'other-file':dict(sha256='unchanged',mode=420)}),
        protected={'assets':{'inventory':{'asset':{'sha256':'asset'}}},
                   'backups':{'inventory':{'backup':{'sha256':'backup'}}}})
    current=json.loads(json.dumps(prior))
    for key in ('mtime_ns','ctime_ns'):current['cache']['inventory'][CACHE_KEY][key]=NEW_NS
    def image(value):
        if isinstance(value,dict):return {k:image(v) for k,v in value.items() if k!='atime_ns'}
        return value
    w=SimpleNamespace(CITY='city',WORK='work',ADMIN='admin',dependency_image=image)
    b=SimpleNamespace(CACHE=Path('cache'),PROTECTED=['assets','backups'])
    calls=[]
    h=SimpleNamespace(prove_read_only=lambda paths:calls.append(paths))
    o=SimpleNamespace(tree_snapshot=lambda path,**kw: current['cache'] if path==Path('cache') else current['protected'][path])
    def frozen_read(path,pin=None):
        assert path==d.TERMINAL and pin==d.TERMINAL_SHA
        return json.dumps(prior).encode()
    monkeypatch.setattr(d,'read',frozen_read)
    return prior,current,w,h,b,o,calls


def test_exact_approved_cache_delta_passes_without_rewriting_observations(monkeypatch):
    prior,current,w,h,b,o,calls=tree_fixture(monkeypatch)
    before=json.dumps([prior,current],sort_keys=True)
    result=d.tree_proof(w,h,b,o)
    assert result['ok'] and result['readonly'] and len(result['sha256'])==64
    assert calls==[[Path('cache'),'assets','backups','city','work','admin']]
    assert result['cache_disposition']==dict(path='cache/'+CACHE_KEY,
        fields=['mtime_ns','ctime_ns'],before_ns=OLD_NS,approved_ns=NEW_NS,
        prior_observation_sha256=d.TERMINAL_SHA)
    assert json.dumps([prior,current],sort_keys=True)==before


@pytest.mark.parametrize('field',['ctime_ns','mtime_ns','device','gid','inode','mode','nlink','size','type','uid'])
def test_cache_exception_refuses_every_other_directory_change(monkeypatch,field):
    prior,current,w,h,b,o,_=tree_fixture(monkeypatch)
    current['cache']['inventory'][CACHE_KEY][field]+=1
    with pytest.raises(RuntimeError,match='restored cache drift'):d.tree_proof(w,h,b,o)


@pytest.mark.parametrize('surface',['unapproved_old_times','cache_file','cache_extra','cache_missing','assets','backups'])
def test_cache_exception_cannot_hide_content_inventory_or_protected_tree_drift(monkeypatch,surface):
    prior,current,w,h,b,o,_=tree_fixture(monkeypatch)
    if surface=='unapproved_old_times':
        for key in ('mtime_ns','ctime_ns'):current['cache']['inventory'][CACHE_KEY][key]=OLD_NS
    elif surface=='cache_file':current['cache']['inventory']['other-file']['sha256']='changed'
    elif surface=='cache_extra':current['cache']['inventory']['new']={'sha256':'new'}
    elif surface=='cache_missing':del current['cache']['inventory']['other-file']
    else:current['protected'][surface]['inventory']['extra']={'sha256':'new'}
    with pytest.raises(RuntimeError,match='restored (cache|protected) drift'):d.tree_proof(w,h,b,o)


@pytest.mark.parametrize('field',['mtime_ns','ctime_ns'])
def test_cache_exception_requires_exact_preserved_preimage(monkeypatch,field):
    prior,current,w,h,b,o,_=tree_fixture(monkeypatch)
    prior['cache']['inventory'][CACHE_KEY][field]+=1
    with pytest.raises(RuntimeError,match='cache disposition preimage'):d.tree_proof(w,h,b,o)
