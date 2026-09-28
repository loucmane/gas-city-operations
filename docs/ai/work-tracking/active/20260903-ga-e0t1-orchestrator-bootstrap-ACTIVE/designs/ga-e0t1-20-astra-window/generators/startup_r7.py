"""Create-only R7 operational preparation. No live installation or launch."""
import ast
import hashlib
import json
from pathlib import Path
import sys

import build
import protocol_r7 as protocol

ROOT='/var/tmp/ga-e0t1.20-prompt-prep-20260928-r7'
RECOVERY='/var/tmp/ga-e0t1.20-terminal-20260928-r6/result.json'
RECOVERY_SHA='dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
CLOSE='/var/tmp/ga-e0t1.20-r6-close-20260928T144139Z/result.json'
CLOSE_SHA='220f7b66a298fd8a48adf355db429f6d0eec259ba0cbb5257e9c474e615f42cf'
HERE=Path(__file__).parent


def sha(raw): return hashlib.sha256(raw).hexdigest()


def components():
    probe=protocol.worker_probe()
    old_probe=protocol.frozen('worker-startup-r6.py')
    old_prompt=protocol.frozen('PRECLAIM-R6.md')
    assert old_prompt.count(sha(old_probe).encode())==2
    prompt=old_prompt.replace(sha(old_probe).encode(),sha(probe).encode())
    prompt=prompt.replace(b'worker-startup-r6.py',b'worker-startup-r7.py').replace(b' r6 ',b' r7 ')
    prompt=prompt.replace(b'.gc/worker-evidence/ga-e0t1.20',protocol.EVIDENCE.encode())
    text=protocol.frozen('prompt-prep-r6.py').decode()
    text=text.replace('ga-e0t1.20-prompt-prep-20260928-r6',ROOT.split('/')[-1])
    text=text.replace('PRECLAIM-R6.md','PRECLAIM-R7.md')
    text=build.once(text,sha(old_prompt),sha(prompt))
    text=build.once(text,"RECOVERY=Path('/var/tmp/ga-e0t1.20-terminal-20260928-r5/result.json')",'RECOVERY=Path('+repr(RECOVERY)+')')
    text=text.replace('/var/tmp/ga-e0t1.20-r5-close-20260928T130452Z/result.json',CLOSE)
    text=text.replace('53b7501005e7f48722f022e023995ba6c9c8b83f3e7adcfa4c6d9e6089da46ea',CLOSE_SHA)
    text=build.once(text,"closed_session='ci-rks41'","closed_session='ci-6gwp8'")
    text=build.once(text,'33f22aafa01ac42f7589c6f856e3bae06baaec93a60233ee3f167ffc3adaff40',
                    '6bcc5636e6d43989d64e18f43ec745980fb5b9d742883b2eae0c47805e3148f2')
    text=build.once(text,"assert not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r5/proof.json').exists()",
        "for name in ('proof.json','nudge-intent.json','result.json'):\n"
        "        assert not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r6',name).exists()")
    text=text.replace('completed R5 window','completed R6 window')
    runtime=(HERE/'runtime_process_r7.py').read_bytes()
    text=build.once(text,'    old.ROOT=ROOT',
        "    runtime=old.module(HERE/'runtime-process-r7.py',"+repr(sha(runtime))+",'runtime_process_r7')\n"
        "    probe=old.module(HERE/'worker-startup-r7.py',"+repr(sha(probe))+",'worker_probe_r7')\n"
        "    runtime.verify_assets(probe.read_regular)\n"
        '    old.ROOT=ROOT')
    executor=text.encode()
    original=protocol.frozen('operator/PROMPT-PREP-R6.sh').decode()
    consumed='#!/bin/sh\necho "COMPLETED PREPARATION - replay prohibited" >&2\nexit 125\n'
    assert original.startswith(consumed)
    wrapper='#!/bin/sh\n'+original[len(consumed):]
    wrapper=wrapper.replace('PROMPT-PREP-R6','PROMPT-PREP-R7').replace('prompt-prep-r6','prompt-prep-r7')
    wrapper=wrapper.replace('20260928-r6','20260928-r7')
    wrapper=build.once(wrapper,sha(protocol.frozen('prompt-prep-r6.py')),sha(executor))
    wrapper=wrapper.replace('# R5 PROMPT PREP:','# R7 PROMPT PREP:')
    out={'worker-startup-r7.py':probe,'PRECLAIM-R7.md':prompt,'prompt-prep-r7.py':executor,
         'operator/PROMPT-PREP-R7.sh':wrapper.encode(),'runtime-process-r7.py':runtime,
         'startup-validation-r7.py':protocol.validator_source().encode(),
         'startup-release-r7-draft.py':protocol.release_source(sha(runtime)).encode()}
    # No release wrapper here: the complete successor must later bind native
    # PREP output, R6 close history, all guards, fresh roots and runtime inputs.
    for name,raw in out.items():
        if name.endswith('.py'): ast.parse(raw,filename=name)
    return out


def main(output):
    root=Path(output); assert not root.exists(),'create-only R7 preparation'
    out=components(); root.mkdir(mode=0o700)
    for name,raw in out.items():
        p=root/name; p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f: f.write(raw)
        p.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.runtime-compatibility-r7-preparation.v1',predecessor=protocol.R6,
        recovery_result_sha256=RECOVERY_SHA,prior_close_sha256=CLOSE_SHA,
        authoring_files={n:sha((HERE/n).read_bytes()) for n in ('protocol_r7.py','runtime_process_r7.py','startup_r7.py')},
        files={n:sha(raw) for n,raw in out.items()},preparation_only=True,
        worker_launch_included=False,execution_admitted=False)
    with (root/'prompt-prep-r7-manifest.json').open('x') as f:
        json.dump(manifest,f,sort_keys=True,indent=2); f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),worker_launch_included=False)))


if __name__=='__main__': main(*sys.argv[1:])
