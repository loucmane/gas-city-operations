"""Create-only fresh startup preparation after fully restored R10."""
import ast
import json
from pathlib import Path
import sys
import build

BASE='30a844f398de06b5ad421e0a74d30e4d421612e4'
ROOT='/var/tmp/ga-e0t1.20-prompt-prep-20260929-r11'
EVIDENCE='.gc/worker-evidence/ga-e0t1.20/r11'
CLOSE='/var/tmp/ga-e0t1.20-r10-close-20260929T005551Z/result.json'
CLOSE_SHA='9c4c4e2537c1c12276b4730cbfd909c606a366880580806f1bed290be1ff6aa9'
CLOSE_EXECUTOR='9362df9405236b9a11277b4ddcab363632c988933d1e5fe83ae2d429038e46a9'
HERE=Path(__file__).parent
sha=build.sha

def frozen(name):
    manifest=json.loads(build.git('show',BASE+':'+build.NEW+'/assembly.json'))
    raw=build.git('show',BASE+':'+build.NEW+'/'+name)
    assert sha(raw)==manifest['files'][name],'frozen R10 source drift: '+name
    return raw

def components():
    old=frozen('worker-startup-r10.py')
    probe=build.once(old.decode(),"OUT = WORK/'.gc/worker-evidence/ga-e0t1.20/r10'",'OUT = WORK/'+repr(EVIDENCE)).encode()
    prompt=frozen('PRECLAIM-R10.md')
    assert prompt.count(sha(old).encode())==3
    prompt=prompt.replace(sha(old).encode(),sha(probe).encode()).replace(b'worker-startup-r10.py',b'worker-startup-r11.py')
    prompt=prompt.replace(b'.gc/worker-evidence/ga-e0t1.20/r10',EVIDENCE.encode())
    prompt=prompt.replace(b'ga-e0t1.20 r10',b'ga-e0t1.20 r11').replace(b'exact r10 amendment',b'exact r11 amendment')
    guard=(HERE/'permissions_baseline_r11.py').read_bytes()
    text=frozen('prompt-prep-r10.py').decode()
    replacements=(
        ('ga-e0t1.20-prompt-prep-20260929-r10',ROOT.rsplit('/',1)[1]),
        ('PRECLAIM-R10.md','PRECLAIM-R11.md'),(sha(frozen('PRECLAIM-R10.md')),sha(prompt)),
        ('worker-startup-r10.py','worker-startup-r11.py'),(sha(old),sha(probe)),
        ('/var/tmp/ga-e0t1.20-terminal-20260929-r9/result.json','/var/tmp/ga-e0t1.20-terminal-20260929-r10/result.json'),
        ('/var/tmp/ga-e0t1.20-r9-close-20260928T233159Z/result.json',CLOSE),
        ('9ea049d563c686da1a37ff7ce7aa754415bcb493a3e3340addf4b86fde2ccdc2',CLOSE_SHA),
        ("closed_session='ci-g12rt'","closed_session='ci-9dp7z'"),
        ('83c3cf184a477e255328071b61698da6a31931d3abdee68ca2acbd2a8dc22b72',CLOSE_EXECUTOR),
        ('completed R9 window','completed R10 window'),
        ('permissions-baseline-r10.py','permissions-baseline-r11.py'),(sha(frozen('permissions-baseline-r10.py')),sha(guard)),
        ('preserved_r9_transcript_sha256','preserved_r10_transcript_sha256'),
    )
    for a,z in replacements:
        assert a in text,a
        text=text.replace(a,z)
    old_guard="""    for name in ('proof.json','nudge-intent.json','result.json'):
        assert not Path('/var/tmp/ga-e0t1.20-startup-release-20260929-r9',name).exists()
"""
    new_guard="""    # R10 enqueued once but did not deliver. Preserve exact consumed evidence.
    for name,pin in {
        'proof.json':'f2074a8659d377f3be6a5a1c997b4fdf3ab9b0184b44ccc2d59979fb6216e473',
        'nudge-intent.json':'5e3313c93f996c7608bbb456eea6b4b068485438e00f13926b89304b37ce175d',
        'result.json':'e07d5763534d37507a0b5972cd10712a7ffcb92dfd4ca220b9a0eab77d2d781a',
    }.items():
        old.read(Path('/var/tmp/ga-e0t1.20-startup-release-20260929-r10',name),pin)
"""
    text=build.once(text,old_guard,new_guard)
    executor=text.encode()
    raw=frozen('operator/PROMPT-PREP-R10.sh').decode()
    consumed='#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'
    assert raw.startswith(consumed)
    wrapper='#!/bin/sh\n'+raw[len(consumed):]
    wrapper=wrapper.replace('R10','R11').replace('r10','r11')
    wrapper=build.once(wrapper,sha(frozen('prompt-prep-r10.py')),sha(executor))
    out={'PRECLAIM-R11.md':prompt,'worker-startup-r11.py':probe,'permissions-baseline-r11.py':guard,
         'prompt-prep-r11.py':executor,'operator/PROMPT-PREP-R11.sh':wrapper.encode()}
    for n,raw in out.items():
        if n.endswith('.py'):ast.parse(raw,filename=n)
    return out

def main(output):
    root=Path(output);assert not root.exists(),'create-only R11 preparation'
    out=components();root.mkdir(mode=0o700)
    for n,raw in out.items():
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
        p.chmod(0o755 if n.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.delivery-r11-preparation.v1',predecessor=BASE,
        prior_close_sha256=CLOSE_SHA,files={n:sha(raw) for n,raw in out.items()},
        authoring_files={n:sha((HERE/n).read_bytes()) for n in ('startup_r11.py','permissions_baseline_r11.py')},
        preparation_only=True,worker_launch_included=False,execution_admitted=False)
    with (root/'prompt-prep-r11-manifest.json').open('x') as f:json.dump(manifest,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),worker_launch_included=False)))

if __name__=='__main__':main(*sys.argv[1:])
