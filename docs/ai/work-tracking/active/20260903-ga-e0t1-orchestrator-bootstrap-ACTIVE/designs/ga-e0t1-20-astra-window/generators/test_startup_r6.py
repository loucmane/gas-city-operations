"""Pure supplemental-preparation bindings, no native preparation execution."""
import hashlib
import json
import subprocess

import pytest

import auth_probe_r6 as auth
import startup_r6 as s


def test_r5_immutable_and_r6_probe_prompt_bound():
    out=s.components()
    assert out['worker-startup-r6.py']==auth.worker_probe()[1]
    assert out['PRECLAIM-R6.md'].count(s.sha(out['worker-startup-r6.py']).encode())==2
    assert auth.PROBE_SHA.encode() not in out['PRECLAIM-R6.md']
    assert b'/worker-startup-r6.py' in out['PRECLAIM-R6.md']
    assert b'new ordinary source root' not in out['PRECLAIM-R6.md']
    assert b'No additional capability' in out['PRECLAIM-R6.md']
    assert set(out)=={'worker-startup-r6.py','PRECLAIM-R6.md','prompt-prep-r6.py','operator/PROMPT-PREP-R6.sh'}


def test_native_preparation_preserves_receipt_and_profile_logic():
    out=s.components()
    executor=out['prompt-prep-r6.py'].decode()
    wrapper=out['operator/PROMPT-PREP-R6.sh'].decode()
    assert 'ROOT=Path('+repr(s.ROOT)+')' in executor
    assert s.RECOVERY_SHA in executor and s.CLOSE_SHA in executor
    assert "closed_session='ci-rks41'" in executor
    assert 'RECOVERY_SHA='+repr(s.RECOVERY_SHA) in executor
    assert "HELPER_SHA='cfd2467d3ce7c8600eb635d28a97249ccdc7bfa055386a423506d3f8e60edc7e'" in executor
    assert s.sha(out['PRECLAIM-R6.md']) in executor
    assert s.sha(out['prompt-prep-r6.py']) in wrapper
    assert s.ROOT in wrapper
    assert "final['profiles']==before['profiles']" in executor
    assert 'native_receipt_image(*args)' in executor
    assert 'helper.config_delta(value,changed,str(PROMPT))' in executor
    assert s.sha(s.frozen('prompt-prep-r5.py',s.R5_PREP)) not in wrapper
    r=subprocess.run(['/bin/sh','-n'],input=wrapper.encode(),capture_output=True)
    assert r.returncode==0


def test_create_only_outputs_and_frozen_authoring_hashes(tmp_path):
    root=tmp_path/'r6'
    s.main(str(root))
    manifest=json.loads((root/'prompt-prep-r6-manifest.json').read_text())
    assert manifest['worker_launch_included'] is False
    for name,pin in manifest['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin
    with pytest.raises(AssertionError,match='create-only'):
        s.main(str(root))
