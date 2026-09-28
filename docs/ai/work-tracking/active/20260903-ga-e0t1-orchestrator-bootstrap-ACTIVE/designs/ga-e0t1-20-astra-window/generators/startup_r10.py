"""Create-only R10 prompt correction; no live mutation, launch or product source."""
import ast
import json
from pathlib import Path
import sys

import build

BASE='c9da0cb9cef8223fe7af45acf5d6ebc33edde158'
ROOT='/var/tmp/ga-e0t1.20-prompt-prep-20260929-r10'
EVIDENCE='.gc/worker-evidence/ga-e0t1.20/r10'
CLOSE='/var/tmp/ga-e0t1.20-r9-close-20260928T233159Z/result.json'
CLOSE_SHA='9ea049d563c686da1a37ff7ce7aa754415bcb493a3e3340addf4b86fde2ccdc2'
CLOSE_EXECUTOR='83c3cf184a477e255328071b61698da6a31931d3abdee68ca2acbd2a8dc22b72'
HERE=Path(__file__).parent
sha=build.sha


def frozen(name):
    manifest=json.loads(build.git('show',BASE+':'+build.NEW+'/assembly.json'))
    raw=build.git('show',BASE+':'+build.NEW+'/'+name)
    assert sha(raw)==manifest['files'][name],'frozen R9 source drift: '+name
    return raw


def components():
    old=frozen('worker-startup-r9.py')
    probe=build.once(old.decode(),"OUT = WORK/'.gc/worker-evidence/ga-e0t1.20/r9'",'OUT = WORK/'+repr(EVIDENCE)).encode()
    prompt=frozen('PRECLAIM-R9.md')
    assert prompt.count(sha(old).encode())==3
    prompt=prompt.replace(sha(old).encode(),sha(probe).encode()).replace(b'worker-startup-r9.py',b'worker-startup-r10.py')
    prompt=prompt.replace(b'.gc/worker-evidence/ga-e0t1.20/r9',EVIDENCE.encode())
    prompt=prompt.replace(b'ga-e0t1.20 r9',b'ga-e0t1.20 r10').replace(b'exact r9 amendment',b'exact r10 amendment')
    prompt=build.once(prompt.decode(),'"sandbox_permissions":"use_default",','').encode()
    guard=(HERE/'permissions_baseline_r10.py').read_bytes()
    text=frozen('prompt-prep-r9.py').decode()
    replacements=(
        ('ga-e0t1.20-prompt-prep-20260929-r9',ROOT.rsplit('/',1)[1]),
        ('PRECLAIM-R9.md','PRECLAIM-R10.md'),(sha(frozen('PRECLAIM-R9.md')),sha(prompt)),
        ('worker-startup-r9.py','worker-startup-r10.py'),(sha(old),sha(probe)),
        ('/var/tmp/ga-e0t1.20-terminal-20260928-r8/result.json','/var/tmp/ga-e0t1.20-terminal-20260929-r9/result.json'),
        ('/var/tmp/ga-e0t1.20-r8-close-20260928T212000Z/result.json',CLOSE),
        ('21ef1b7d95ac018b902e14b4ce6486cb16ac8820158682455e1b7a864d79cff6',CLOSE_SHA),
        ("closed_session='ci-sgd80'","closed_session='ci-g12rt'"),
        ('eb991994ba5f35ff3d88dd2cfa5e8fe645eafc3e0907da0ac78ef5492986f7b0',CLOSE_EXECUTOR),
        ('/var/tmp/ga-e0t1.20-startup-release-20260928-r8','/var/tmp/ga-e0t1.20-startup-release-20260929-r9'),
        ('completed R8 window','completed R9 window'),
        ('permissions-baseline-r9.py','permissions-baseline-r10.py'),(sha(frozen('permissions-baseline-r9.py')),sha(guard)),
        ('preserved_r8_transcript_sha256','preserved_r9_transcript_sha256'),
    )
    for a,z in replacements:
        assert a in text,a
        text=text.replace(a,z)
    executor=text.encode()
    raw=frozen('operator/PROMPT-PREP-R9.sh').decode()
    consumed='#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'
    assert raw.startswith(consumed)
    wrapper='#!/bin/sh\n'+raw[len(consumed):]
    wrapper=wrapper.replace('R9','R10').replace('r9','r10')
    wrapper=build.once(wrapper,sha(frozen('prompt-prep-r9.py')),sha(executor))
    out={'PRECLAIM-R10.md':prompt,'worker-startup-r10.py':probe,'permissions-baseline-r10.py':guard,
         'prompt-prep-r10.py':executor,'operator/PROMPT-PREP-R10.sh':wrapper.encode()}
    for n,raw in out.items():
        if n.endswith('.py'):ast.parse(raw,filename=n)
    return out


def main(output):
    root=Path(output);assert not root.exists(),'create-only R10 preparation'
    out=components();root.mkdir(mode=0o700)
    for n,raw in out.items():
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        p.chmod(0o755 if n.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.native-default-r10-preparation.v1',predecessor=BASE,
        prior_close_sha256=CLOSE_SHA,files={n:sha(raw) for n,raw in out.items()},
        authoring_files={n:sha((HERE/n).read_bytes()) for n in ('startup_r10.py','permissions_baseline_r10.py')},
        preparation_only=True,worker_launch_included=False,execution_admitted=False)
    with (root/'prompt-prep-r10-manifest.json').open('x') as f:json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),worker_launch_included=False)))


if __name__=='__main__':main(*sys.argv[1:])
