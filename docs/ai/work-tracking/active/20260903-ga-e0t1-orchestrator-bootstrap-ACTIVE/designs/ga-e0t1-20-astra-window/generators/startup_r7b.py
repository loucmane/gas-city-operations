"""R7B: host ownership is checked on the host, not in a remapped child.

Create-only operational preparation, frozen from the consumed R7 candidate.
No product implementation, installed receipt, worker or permission change.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

W=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap')
REL='docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/'
BASE='a27953982ab8a4321ba8e1ae3fafe61cd8e576c7'
ROOT='/var/tmp/ga-e0t1.20-prompt-prep-20260928-r7b'
PINS={'prompt-prep-r7.py':'e1b1b42926d76fe39c5f2bfd3efc9018d4368208563713286ee3b537758c824b',
      'operator/PROMPT-PREP-R7.sh':'2e32a660bb52bad6d0f54631c40064f9a1d2a94666754da107ecf6973a166291'}


def sha(raw): return hashlib.sha256(raw).hexdigest()


def frozen(name):
    raw=subprocess.run(['git','--no-optional-locks','-C',str(W),'show',BASE+':'+REL+name],
                       check=True,capture_output=True).stdout
    assert sha(raw)==PINS[name], 'frozen predecessor changed'
    return raw


def once(text, old, new):
    assert text.count(old)==1, old
    return text.replace(old,new,1)


def components():
    text=frozen('prompt-prep-r7.py').decode()
    text=once(text,"ROOT=Path('/var/tmp/ga-e0t1.20-prompt-prep-20260928-r7')",'ROOT=Path('+repr(ROOT)+')')
    text=once(text,'    runtime.verify_assets(probe.read_regular)\n',
        '    # configure is shared with the read-only namespace child. Root ownership\n'
        '    # there is remapped. Never assert host authority from that namespace.\n'
        '    old._verify_host_assets=lambda: runtime.verify_assets(probe.read_regular)\n')
    text=once(text,"        if name=='result.json':\n",
        "        if name=='result.json':\n"
        '            # Recheck actual host assets before publishing success.\n'
        '            old._verify_host_assets()\n')
    text=once(text,"    if len(sys.argv)==3 and sys.argv[1]=='normalize':old.normalize_main(Path(sys.argv[2]))\n",
        "    if len(sys.argv)==3 and sys.argv[1]=='normalize':\n"
        "        assert sys.argv[2]==str(ROOT), 'wrong normalize root'\n"
        '        # No host claim or installation here; only normalized JSON to stdout.\n'
        '        old.normalize_main(ROOT)\n')
    text=once(text,'        old.main()\n',
        '        old._verify_host_assets()\n        old.main()\n')
    executor=text.encode(); ast.parse(executor)
    wrapper=frozen('operator/PROMPT-PREP-R7.sh').decode()
    wrapper=wrapper.replace('PROMPT-PREP-R7','PROMPT-PREP-R7B').replace('prompt-prep-r7','prompt-prep-r7b')
    wrapper=once(wrapper,'20260928-r7\n','20260928-r7b\n')
    wrapper=once(wrapper,PINS['prompt-prep-r7.py'],sha(executor))
    wrapper=wrapper.replace('# R7 PROMPT PREP:','# R7B PROMPT PREP:')
    return {'prompt-prep-r7b.py':executor,'operator/PROMPT-PREP-R7B.sh':wrapper.encode()}


def main(output):
    root=Path(output); assert not root.exists(), 'create-only successor'
    out=components(); root.mkdir(mode=0o700)
    for name,raw in out.items():
        p=root/name; p.parent.mkdir(exist_ok=True,parents=True)
        with p.open('xb') as f: f.write(raw)
        p.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.prompt-prep-r7b.v1',predecessor=BASE,
        consumed_root='/var/tmp/ga-e0t1.20-prompt-prep-20260928-r7',fresh_root=ROOT,
        files={n:sha(raw) for n,raw in out.items()},authoring_sha256=sha(Path(__file__).read_bytes()),
        assets_unchanged=True,preparation_only=True,execution_admitted=False,
        worker_launch_included=False)
    with (root/'prompt-prep-r7b-manifest.json').open('x') as f:
        json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(manifest,sort_keys=True))


if __name__=='__main__': main(*sys.argv[1:])
