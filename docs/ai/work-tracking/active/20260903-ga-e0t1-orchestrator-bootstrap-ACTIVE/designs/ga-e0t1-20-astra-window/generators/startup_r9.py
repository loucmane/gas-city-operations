"""Create-only R9 preparation after exact R8 restoration; never launch a worker."""
import ast
import json
from pathlib import Path
import sys

import build

BASE = 'c637868cf25442b48418234ac9f1a094ddaac163'
ROOT = '/var/tmp/ga-e0t1.20-prompt-prep-20260929-r9'
EVIDENCE = '.gc/worker-evidence/ga-e0t1.20/r9'
CLOSE = '/var/tmp/ga-e0t1.20-r8-close-20260928T212000Z/result.json'
CLOSE_SHA = '21ef1b7d95ac018b902e14b4ce6486cb16ac8820158682455e1b7a864d79cff6'
CLOSE_EXECUTOR = 'eb991994ba5f35ff3d88dd2cfa5e8fe645eafc3e0907da0ac78ef5492986f7b0'
HERE = Path(__file__).parent
sha = build.sha


def frozen(name):
    manifest = json.loads(build.git('show', BASE + ':' + build.NEW + '/assembly.json'))
    raw = build.git('show', BASE + ':' + build.NEW + '/' + name)
    assert sha(raw) == manifest['files'][name], 'frozen R8 source drift: ' + name
    return raw


def components():
    old_probe = frozen('worker-startup-r8.py')
    probe = build.once(old_probe.decode(),
        "OUT = WORK/'.gc/worker-evidence/ga-e0t1.20/r8'", 'OUT = WORK/' + repr(EVIDENCE)).encode()
    prompt = frozen('PRECLAIM-R8.md')
    assert prompt.count(sha(old_probe).encode()) == 2
    prompt = prompt.replace(sha(old_probe).encode(), sha(probe).encode())
    prompt = prompt.replace(b'worker-startup-r8.py', b'worker-startup-r9.py')
    prompt = prompt.replace(b'.gc/worker-evidence/ga-e0t1.20/r8', EVIDENCE.encode())
    prompt = prompt.replace(b'ga-e0t1.20 r7', b'ga-e0t1.20 r9').replace(b'exact r7 amendment', b'exact r9 amendment')
    text = prompt.decode()
    text = build.once(text, '   Then WAIT. Do not drain or edit product source before the coordinator',
        '   Finish this startup turn with exactly one final answer using your real session\n'
        '   and report digest substituted in this single line with no Markdown:\n'
        '   WAITING FOR SOURCE RELEASE: ga-e0t1.20 session=ACTUAL_SESSION_ID report_sha256=REPORT_DIGEST probe_sha256=' + sha(probe) + '\n'
        '   Then WAIT. Do not drain or edit product source before the coordinator')
    text = build.once(text, 'Use -B, no pytest cache, and scratch only under the owned evidence directory.',
        'Use -B, no pytest cache, and scratch only under the owned evidence directory.\n'
        'Create new evidence directories with mode 0700 and new evidence files with mode\n'
        '0600. Preserve existing modes and bytes. Only new owned evidence may be chmodded.\n'
        'Keep all output within the existing 128 file and 64 MiB evidence bounds.\n'
        'Report a scope conflict instead of editing permissions or historical evidence.')
    prompt = text.encode()
    guard = (HERE/'permissions_baseline_r9.py').read_bytes()
    text = frozen('prompt-prep-r8.py').decode()
    for old, new in (
        ('ga-e0t1.20-prompt-prep-20260928-r8', ROOT.rsplit('/', 1)[1]),
        ('PRECLAIM-R8.md', 'PRECLAIM-R9.md'),
        (sha(frozen('PRECLAIM-R8.md')), sha(prompt)),
        ('worker-startup-r8.py', 'worker-startup-r9.py'),
        (sha(old_probe), sha(probe)),
        ('/var/tmp/ga-e0t1.20-terminal-20260928-r7/result.json', '/var/tmp/ga-e0t1.20-terminal-20260928-r8/result.json'),
        ('/var/tmp/ga-e0t1.20-r7-close-20260928T174426Z/result.json', CLOSE),
        ('15a5a5911abe86bc55a7291b3cea366e8eda9a515353b26968cf8030aa6520d0', CLOSE_SHA),
        ("closed_session='ci-zcoet'", "closed_session='ci-sgd80'"),
        ('694f56ef124d7f93ee674ea376484a194a47a572413b70a2bb7c11f3eefb31ef', CLOSE_EXECUTOR),
        ('/var/tmp/ga-e0t1.20-startup-release-20260928-r7', '/var/tmp/ga-e0t1.20-startup-release-20260928-r8'),
        ('completed R7 window', 'completed R8 window'),
        ('permissions-baseline-r8.py', 'permissions-baseline-r9.py'),
        (sha(frozen('permissions-baseline-r8.py')), sha(guard)),
    ):
        assert old in text, old
        text = text.replace(old, new)
    text = build.once(text, '                permissions_postimage_sha256=permissions.POSTIMAGE_SHA,',
        '                preserved_r8_transcript_sha256=permissions.TRANSCRIPT_SHA,\n'
        '                permissions_postimage_sha256=permissions.POSTIMAGE_SHA,')
    executor = text.encode()
    original = frozen('operator/PROMPT-PREP-R8.sh').decode()
    consumed = '#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'
    assert original.startswith(consumed)
    wrapper = '#!/bin/sh\n' + original[len(consumed):]
    wrapper = wrapper.replace('R8', 'R9').replace('r8', 'r9').replace('20260928', '20260929')
    wrapper = build.once(wrapper, sha(frozen('prompt-prep-r8.py')), sha(executor))
    out = {'worker-startup-r9.py': probe, 'PRECLAIM-R9.md': prompt,
           'permissions-baseline-r9.py': guard, 'prompt-prep-r9.py': executor,
           'operator/PROMPT-PREP-R9.sh': wrapper.encode()}
    for name, raw in out.items():
        if name.endswith('.py'):
            ast.parse(raw, filename=name)
    return out


def main(output):
    root = Path(output)
    assert not root.exists(), 'create-only R9 preparation'
    out = components()
    root.mkdir(mode=0o700)
    for name, raw in out.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest = dict(schema='ga-e0t1.20.review-wait-r9-preparation.v1', predecessor=BASE,
        prior_close_sha256=CLOSE_SHA, authoring_files={n:sha((HERE/n).read_bytes()) for n in
        ('startup_r9.py', 'permissions_baseline_r9.py')}, files={n:sha(raw) for n,raw in out.items()},
        preparation_only=True, worker_launch_included=False, execution_admitted=False)
    with (root/'prompt-prep-r9-manifest.json').open('x') as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(dict(output=str(root), files=len(out), worker_launch_included=False)))


if __name__ == '__main__':
    main(*sys.argv[1:])
