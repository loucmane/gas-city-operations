"""Executable entrypoint semantics; fixture stubs are not live host proof."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest
import startup_r7b as s


def body():
    tree=ast.parse(s.components()['prompt-prep-r7b.py'])
    return compile(ast.Module(body=[tree.body[-1]],type_ignores=[]),'entry','exec')


def entry(argv, *, drift=False, source=True):
    calls=[]
    def verify():
        calls.append('host_assets')
        if drift: raise RuntimeError('host asset drift')
    old=types.SimpleNamespace(_SOURCE_SHA='exact' if source else None,
        read=lambda *args: calls.append('source') or b'exact',
        _verify_host_assets=verify,main=lambda: calls.append('main'),
        normalize_main=lambda p: calls.append(('normalize',str(p))))
    ns=dict(__name__='__main__',__file__='exact.py',configure=lambda: old,
        sys=types.SimpleNamespace(argv=argv),Path=Path,ROOT=Path(s.ROOT))
    exec(body(),ns)
    return calls


def test_host_path_cannot_reach_preparation_before_asset_check():
    assert entry(['exact.py'])==['source','host_assets','main']
    with pytest.raises(RuntimeError,match='host asset drift'): entry(['exact.py'],drift=True)


def test_confined_normalizer_has_no_host_claim():
    assert entry(['exact.py','normalize',s.ROOT],drift=True)==['source',('normalize',s.ROOT)]


@pytest.mark.parametrize('argv',[
    ['exact.py','normalize','/tmp/wrong'],['exact.py','normalize'],
    ['exact.py','--skip-host'],['exact.py','normalize',s.ROOT,'extra']])
def test_no_general_skip_or_alternate_root(argv):
    with pytest.raises(AssertionError): entry(argv)


@pytest.mark.parametrize('argv',[['exact.py'],['exact.py','normalize',s.ROOT]])
def test_source_launcher_mandatory_in_both_branches(argv):
    with pytest.raises(AssertionError): entry(argv,source=False)


def configured():
    src=s.components()['prompt-prep-r7b.py']
    ns=dict(__name__='fixture',__file__='fixture.py')
    exec(compile(src,'fixture.py','exec'),ns)
    return ns['configure']()


def test_configure_does_not_assert_host_asset_authority():
    # Actual frozen imports read only; this also runs in the Codex remapped sandbox.
    assert callable(configured()._verify_host_assets)


def test_asset_drift_blocks_result_publication(tmp_path):
    old=configured(); old.ROOT=tmp_path
    def drift(): raise RuntimeError('host asset drift')
    old._verify_host_assets=drift
    with pytest.raises(RuntimeError,match='host asset drift'): old.write('result.json',{'ok':True})
    assert not (tmp_path/'result.json').exists()


def test_positive_publication_rechecks_first(tmp_path):
    old=configured(); old.ROOT=tmp_path; calls=[]
    old._verify_host_assets=lambda: calls.append('host_assets')
    old.write('result.json',{'ok':True})
    assert calls==['host_assets'] and json.loads((tmp_path/'result.json').read_bytes())['ok']


def test_only_narrow_frozen_delta_and_wrapper_binding():
    out=s.components(); text=out['prompt-prep-r7b.py'].decode()
    assert 'runtime.verify_assets(probe.read_regular)' in text
    assert text.count('old._verify_host_assets()')==2
    assert "native_receipt_image(*args)" in text
    assert "final['profiles']==before['profiles']" in text
    assert "helper.config_delta(value,changed,str(PROMPT))" in text
    assert s.PINS['prompt-prep-r7.py']==hashlib.sha256(s.frozen('prompt-prep-r7.py')).hexdigest()
    wrapper=out['operator/PROMPT-PREP-R7B.sh']
    assert s.sha(out['prompt-prep-r7b.py']).encode() in wrapper
    assert s.ROOT.encode() in wrapper
    assert subprocess.run(['/bin/sh','-n'],input=wrapper,capture_output=True).returncode==0


def test_create_only_successor(tmp_path):
    root=tmp_path/'new';s.main(str(root))
    m=json.loads((root/'prompt-prep-r7b-manifest.json').read_bytes())
    assert not m['execution_admitted'] and not m['worker_launch_included']
    for name,pin in m['files'].items(): assert s.sha((root/name).read_bytes())==pin
    with pytest.raises(AssertionError,match='create-only'): s.main(str(root))
