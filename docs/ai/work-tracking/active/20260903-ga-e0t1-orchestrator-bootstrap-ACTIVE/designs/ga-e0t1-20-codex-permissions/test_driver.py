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
