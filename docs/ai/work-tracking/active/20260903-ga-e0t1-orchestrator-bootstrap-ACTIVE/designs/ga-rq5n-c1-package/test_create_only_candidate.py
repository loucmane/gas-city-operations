"""Offline create-only candidate tests. All writes and Git commands use tmp_path."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import types
import pytest

HERE=Path(__file__).parent

def module(name):
    m=types.ModuleType(name)
    m.__file__=str(HERE/name)
    exec(compile((HERE/name).read_bytes(),m.__file__,'exec'),m.__dict__)
    return m

c=module('contract.py')
v=module('startup-validation.py')
p=module('create-only-patch.py')
probe=module('worker-startup.py')
ws=module('fresh-workspace.py')
a=module('window-assembly.py')

def image():
    before={'preserved.txt':dict(mode=0o644,type=stat.S_IFREG,size=4,sha256='a'*64)}
    after=copy.deepcopy(before)
    after.update({path:dict(mode=mode,type=stat.S_IFREG,size=10,sha256='b'*64)
                  for path,mode in c.SOURCE_MODES.items()})
    after.update({path:dict(mode=0o755,type=stat.S_IFDIR) for path in v.SOURCE_DIRECTORIES})
    return before,after

def test_frozen_scope_exact_modes_and_all_files_required():
    scope=json.loads((HERE/'FILE-SCOPE.json').read_bytes())
    assert scope['task']==c.TASK and scope['base']==c.BASE
    expected={scope['root']+'/'+n:0o755 if n.startswith('operator/') else 0o644 for n in scope['new_files']}
    assert c.SOURCE_MODES==v.SOURCE_MODES==expected and len(expected)==52
    assert c.MAX_PRODUCT_BYTES==v.MAX_PRODUCT_BYTES==scope['maximum_new_product_bytes']
    before,after=image()
    v.workspace_delta(before,after,{},c.SOURCE_PATHS)
    for paths in (c.SOURCE_PATHS[:-1],c.SOURCE_PATHS+('outside',),c.SOURCE_PATHS+(c.SOURCE_PATHS[0],)):
        with pytest.raises(RuntimeError):c.require_source_scope(paths)

@pytest.mark.parametrize('defect',['preexisting','missing','wrong-mode','symlink','hard-directory','extra-file',
    'extra-dir','parent-mode','parent-file','old-mutated','old-deleted','byte-overflow','sum-overflow','unknown-source'])
def test_create_only_workspace_refusals(defect):
    before,after=image()
    path=c.SOURCE_PATHS[0]
    selected=c.SOURCE_PATHS
    if defect=='preexisting':before[path]=copy.deepcopy(after[path])
    elif defect=='missing':del after[path]
    elif defect=='wrong-mode':after[path]['mode']=0o755
    elif defect=='symlink':after[path]['type']=stat.S_IFLNK
    elif defect=='hard-directory':after[path]['type']=stat.S_IFDIR
    elif defect=='extra-file':after[c.SCOPE_ROOT+'extra.py']=copy.deepcopy(after[path])
    elif defect=='extra-dir':after[c.SCOPE_ROOT+'extra']=dict(mode=0o755,type=stat.S_IFDIR)
    elif defect=='parent-mode':after[next(iter(v.SOURCE_DIRECTORIES))]['mode']=0o777
    elif defect=='parent-file':after[next(iter(v.SOURCE_DIRECTORIES))]['type']=stat.S_IFREG
    elif defect=='old-mutated':after['preserved.txt']['sha256']='c'*64
    elif defect=='old-deleted':del after['preserved.txt']
    elif defect=='byte-overflow':after[path]['size']=c.MAX_PRODUCT_BYTES+1
    elif defect=='sum-overflow':
        for path in c.SOURCE_PATHS:after[path]['size']=c.MAX_PRODUCT_BYTES
    elif defect=='unknown-source':selected=('unknown.py',)
    with pytest.raises(RuntimeError):v.workspace_delta(before,after,{},selected)

def test_no_product_file_or_new_parent_before_release():
    before,after=image()
    with pytest.raises(RuntimeError):v.workspace_delta(before,after,{})
    for path in v.SOURCE_DIRECTORIES:
        with pytest.raises(RuntimeError):v.workspace_delta(before,dict(before,**{path:after[path]}),{})

def test_actual_probe_report_requires_both_pinned_reads():
    session=dict(id='ci-fixture')
    report=dict(schema='ga-rq5n.worker-startup.v1',task=c.TASK,session_id=session['id'],
        worktree=c.WORK,base=c.BASE,branch=c.BRANCH,subscription='ChatGPT',provider_overrides_absent=True,
        credential_values_exported=False,codex_sha256=probe.CODEX_SHA,local_rules=probe.RULES,
        default_rules_sha256=probe.DEFAULT_SHA,workspace_write=True,source_edit_released=False,
        foreign_write=dict(denied=True,errno=13,path=str(probe.FOREIGN/'unexpected-write')),
        predecessor_read=dict(commit=probe.PREDECESSOR,blobs=dict(probe.PREDECESSOR_INPUTS),read_only=True))
    v.report(report,session,probe)
    for defect in ('missing','commit','blob','additional','not-read-only'):
        value=copy.deepcopy(report)
        if defect=='missing':del value['predecessor_read']
        elif defect=='commit':value['predecessor_read']['commit']='0'*40
        elif defect=='blob':value['predecessor_read']['blobs']['window-r11.py']='0'*64
        elif defect=='additional':value['predecessor_read']['blobs']['other']='a'*64
        else:value['predecessor_read']['read_only']=False
        with pytest.raises(RuntimeError):v.report(value,session,probe)

@pytest.mark.parametrize('raw',[b'',b'a',b'a\n',b'one\ntwo',b'\n',b'\n\n',b'\r\n',
                              'Å Swedish UTF8\n'.encode(),b'---\n+++\n@@\n'])
@pytest.mark.parametrize('mode',[0o644,0o755])
def test_real_git_patch_roundtrip_without_staging(tmp_path,raw,mode):
    # No hooks/config/repository outside the fresh fixture are used.
    env={'PATH':'/usr/bin:/bin','HOME':str(tmp_path),'GIT_CONFIG_NOSYSTEM':'1',
         'GIT_CONFIG_GLOBAL':'/dev/null','GIT_OPTIONAL_LOCKS':'0','LC_ALL':'C'}
    repo=tmp_path/'repo';repo.mkdir()
    subprocess.run(['/usr/bin/git','init','--quiet',str(repo)],env=env,check=True,capture_output=True)
    files={'nested/candidate.py':raw}
    patch=p.encode(files,{'nested/candidate.py':mode})
    assert patch==p.encode(files,{'nested/candidate.py':mode})
    for extra in (['--check'],[]):
        result=subprocess.run(['/usr/bin/git','-c','core.hooksPath=/dev/null','-C',str(repo),
            'apply',*extra,'--whitespace=nowarn','-'],input=patch,env=env,capture_output=True)
        assert result.returncode==0,result.stderr
    target=repo/'nested/candidate.py'
    assert target.read_bytes()==raw and stat.S_IMODE(target.stat().st_mode)==mode
    assert not (repo/'.git/index').exists()

@pytest.mark.parametrize('defect',['absolute','parent','newline','space','nul','invalid-utf8',
    'bad-mode','boolean-mode','mismatch','empty','bound','sum-bound'])
def test_patch_encoder_refusals(defect):
    files={'a.py':b'pass\n'};modes={'a.py':0o644};maximum=2<<20
    if defect in ('absolute','parent','newline','space'):
        key={'absolute':'/absolute','parent':'a/../b','newline':'a\nb','space':'a b'}[defect]
        files={key:b'x'};modes={key:0o644}
    elif defect=='nul':files['a.py']=b'x\0y'
    elif defect=='invalid-utf8':files['a.py']=b'\xff'
    elif defect=='bad-mode':modes['a.py']=0o777
    elif defect=='boolean-mode':modes['a.py']=True
    elif defect=='mismatch':modes['other.py']=0o644
    elif defect=='empty':files={};modes={}
    elif defect=='bound':maximum=0
    elif defect=='sum-bound':maximum=1
    with pytest.raises((RuntimeError,UnicodeDecodeError)):p.encode(files,modes,maximum)

def test_assembly_binds_inspector_patch_helper_and_preserves_safety():
    _,out=a.assemble(observation='/tmp/ga-rq5n-readonly-baseline-20260929-r1/observed.json',
                    observation_sha='a'*64,cache_ns=1)
    text=out['candidate-inspect.py'].decode()
    assert hashlib.sha256(out['create-only-patch.py']).hexdigest() in text
    assert 'encoder.encode(payload,w.contract().SOURCE_MODES,w.contract().MAX_PRODUCT_BYTES)' in text
    assert "patch = git(" not in text
    for anchor in ("terminal.get('ok')", "not close.processes(w.WORK)", "common.compare(before, after)",
                   "whole==validator.workspace_image", "'candidate evidence or source changed'",
                   "'candidate generated hook differs'"):
        assert anchor in text
    # Immutable prepared prompt/probe/brief/scope remain byte-identical.
    for name in ('FILE-SCOPE.json','PRECLAIM.md','WORKER-BRIEF.md','worker-startup.py'):
        assert out[name]==(HERE/name).read_bytes()

def test_fresh_workspace_refuses_any_existing_product_path():
    current={path:dict(mode=0o644,type=stat.S_IFREG,sha256=digest) for path,digest in ws.PINS.items()}
    current.update({path:dict(mode=0o644,type=stat.S_IFREG,sha256=digest) for path,digest in c.RULES.items()})
    w=types.SimpleNamespace(contract=lambda:c,require=c.require)
    ws.verify(w,current,c.RUNTIME_IMAGE)
    for path in c.SOURCE_PATHS:
        changed=dict(current,**{path:dict(mode=0o644,type=stat.S_IFREG,sha256='a'*64)})
        with pytest.raises(RuntimeError):ws.verify(w,changed,c.RUNTIME_IMAGE)
