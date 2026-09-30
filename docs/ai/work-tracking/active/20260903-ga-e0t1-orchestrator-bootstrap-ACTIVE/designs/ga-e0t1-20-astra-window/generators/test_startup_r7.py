"""R7 create-only package closure and no-installation contract."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

HERE=Path(__file__).parent
sys.path.insert(0,'/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/generators')
import startup_r7 as s


def test_exact_new_probe_prompt_and_closed_wrapper():
    out=s.components(); prompt=out['PRECLAIM-R7.md']
    assert prompt.count(s.sha(out['worker-startup-r7.py']).encode())==2
    assert b'worker-startup-r6.py' not in prompt
    assert b'.gc/worker-evidence/ga-e0t1.20/startup.json' not in prompt
    assert b'.gc/worker-evidence/ga-e0t1.20/r7/startup.json' in prompt
    wrapper=out['operator/PROMPT-PREP-R7.sh']
    assert s.sha(out['prompt-prep-r7.py']).encode() in wrapper
    assert b'COMPLETED PREPARATION' not in wrapper
    assert b'PROMPT-PREP-R6.sh' not in wrapper
    assert subprocess.run(['/bin/sh','-n'],input=wrapper,capture_output=True).returncode==0


def test_preparation_preserves_actual_host_receipt_and_noninterference_checks():
    out=s.components(); src=out['prompt-prep-r7.py'].decode()
    assert 'RECOVERY=Path('+repr(s.RECOVERY)+')' in src
    assert s.CLOSE in src and s.CLOSE_SHA in src
    assert "closed_session='ci-6gwp8'" in src
    assert "('proof.json','nudge-intent.json','result.json')" in src
    assert "final['profiles']==before['profiles']" in src
    assert 'native_receipt_image(*args)' in src
    assert 'helper.config_delta(value,changed,str(PROMPT))' in src
    assert 'runtime.verify_assets(probe.read_regular)' in src
    assert s.sha(out['runtime-process-r7.py']) in src
    assert s.sha(out['runtime-process-r7.py']).encode() in out['startup-release-r7-draft.py']
    assert not any('RELEASE' in n for n in out if n.startswith('operator/'))


def test_create_only_digests_and_never_replay(tmp_path):
    root=tmp_path/'out'; s.main(str(root))
    m=json.loads((root/'prompt-prep-r7-manifest.json').read_bytes())
    assert m['execution_admitted'] is False and m['worker_launch_included'] is False
    for n,pin in m['files'].items(): assert hashlib.sha256((root/n).read_bytes()).hexdigest()==pin
    with pytest.raises(AssertionError,match='create-only'): s.main(str(root))


def test_source_predecessor_is_exact_and_never_rewritten():
    assert s.protocol.R6=='cb4183cccaa35196ec733b427be4cfd9944cab11'
    assert s.sha(s.protocol.frozen('startup-release.py'))=='9b27d7433501720f127cf414b92894b6a9ff632ab32e1509c15f55944d3a0496'
    assert s.sha(s.protocol.frozen('startup-validation.py'))=='2c7fcef75391ae0507c085428c117088131d1f1695884d5ef0200f1df115630a'
