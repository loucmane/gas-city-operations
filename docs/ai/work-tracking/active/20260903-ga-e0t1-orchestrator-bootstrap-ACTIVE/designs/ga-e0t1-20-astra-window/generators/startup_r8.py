"""Fresh create-only uninstalled preparation; no lifecycle or product edits."""
import ast
import json
from pathlib import Path
import sys

import build

BASE = '1c4608709f51097767394573aff719682fa0e8b0'
ROOT = '/var/tmp/ga-e0t1.20-prompt-prep-20260928-r8'
EVIDENCE = '.gc/worker-evidence/ga-e0t1.20/r8'
CLOSE = '/var/tmp/ga-e0t1.20-r7-close-20260928T174426Z/result.json'
CLOSE_SHA = '15a5a5911abe86bc55a7291b3cea366e8eda9a515353b26968cf8030aa6520d0'
CLOSE_EXECUTOR = '694f56ef124d7f93ee674ea376484a194a47a572413b70a2bb7c11f3eefb31ef'
HERE = Path(__file__).parent
PINS = {
    'prompt-prep-r7b.py': '102a87679ac8a24bd487a6a1b5bf2cc8574f870a88f0c555a5d60fc42950423d',
    'operator/PROMPT-PREP-R7B.sh': 'ea44cfa0406c7d0fa9e0310c08555e053aa8527018c1a1a60d9252856b52427d',
    'worker-startup-r7.py': '1cee785ea7a7fcdad4ef3f2b93fbbed13dc6fa0d55278d33857a65203db6aa47',
    'PRECLAIM-R7.md': 'f6faecf0750a5b7c641d8734290d8d4516ecb9480db4cbca2738c9867df902cf',
}
sha = build.sha


def frozen(name):
    raw = build.git('show', BASE + ':' + build.NEW + '/' + name)
    assert sha(raw) == PINS[name], 'frozen R7 source drift: ' + name
    return raw


def components():
    probe = build.once(frozen('worker-startup-r7.py').decode(),
        "OUT = WORK/'.gc/worker-evidence/ga-e0t1.20/r7'", 'OUT = WORK/' + repr(EVIDENCE)).encode()
    prompt = frozen('PRECLAIM-R7.md')
    assert prompt.count(PINS['worker-startup-r7.py'].encode()) == 2
    prompt = prompt.replace(PINS['worker-startup-r7.py'].encode(), sha(probe).encode())
    prompt = prompt.replace(b'worker-startup-r7.py', b'worker-startup-r8.py')
    prompt = prompt.replace(b'.gc/worker-evidence/ga-e0t1.20/r7', EVIDENCE.encode())
    guard = (HERE/'permissions_baseline_r8.py').read_bytes()
    text = frozen('prompt-prep-r7b.py').decode()
    text = text.replace('ga-e0t1.20-prompt-prep-20260928-r7b', ROOT.rsplit('/', 1)[1])
    text = text.replace('PRECLAIM-R7.md', 'PRECLAIM-R8.md')
    text = text.replace(PINS['PRECLAIM-R7.md'], sha(prompt))
    text = text.replace('worker-startup-r7.py', 'worker-startup-r8.py')
    text = text.replace(PINS['worker-startup-r7.py'], sha(probe))
    text = text.replace('/var/tmp/ga-e0t1.20-terminal-20260928-r6/result.json',
                        '/var/tmp/ga-e0t1.20-terminal-20260928-r7/result.json')
    text = text.replace('/var/tmp/ga-e0t1.20-r6-close-20260928T144139Z/result.json', CLOSE)
    text = text.replace('220f7b66a298fd8a48adf355db429f6d0eec259ba0cbb5257e9c474e615f42cf', CLOSE_SHA)
    text = build.once(text, "closed_session='ci-6gwp8'", "closed_session='ci-zcoet'")
    text = text.replace('6bcc5636e6d43989d64e18f43ec745980fb5b9d742883b2eae0c47805e3148f2', CLOSE_EXECUTOR)
    text = text.replace('/var/tmp/ga-e0t1.20-startup-release-20260928-r6',
                        '/var/tmp/ga-e0t1.20-startup-release-20260928-r7')
    text = text.replace('completed R6 window', 'completed R7 window')
    text = build.once(text, '    old._verify_host_assets=lambda: runtime.verify_assets(probe.read_regular)',
        "    permissions=old.module(HERE/'permissions-baseline-r8.py',"+repr(sha(guard))+",'permission_baseline_r8')\n"
        "    def verify_host_assets():\n"
        "        runtime.verify_assets(probe.read_regular)\n"
        "        permissions.verify(old.read,old.module)\n"
        "    old._verify_host_assets=verify_host_assets")
    text = build.once(text, '                supplemental_prompt_preparation=True,',
        "                permissions_postimage_sha256=permissions.POSTIMAGE_SHA,\n"
        "                permissions_result_sha256=permissions.RESULT_SHA,\n"
        "                supplemental_prompt_preparation=True,")
    executor = text.encode()
    original = frozen('operator/PROMPT-PREP-R7B.sh').decode()
    consumed = '#!/bin/sh\necho "COMPLETED OPERATION - replay prohibited" >&2\nexit 125\n'
    assert original.startswith(consumed)
    wrapper = '#!/bin/sh\n' + original[len(consumed):]
    wrapper = wrapper.replace('R7B', 'R8').replace('r7b', 'r8')
    wrapper = build.once(wrapper, PINS['prompt-prep-r7b.py'], sha(executor))
    out = {'worker-startup-r8.py':probe, 'PRECLAIM-R8.md':prompt,
           'permissions-baseline-r8.py':guard, 'prompt-prep-r8.py':executor,
           'operator/PROMPT-PREP-R8.sh':wrapper.encode()}
    for name, raw in out.items():
        if name.endswith('.py'): ast.parse(raw, filename=name)
    return out


def main(output):
    root = Path(output); assert not root.exists(), 'create-only R8 preparation'
    out = components(); root.mkdir(mode=0o700)
    for name, raw in out.items():
        p = root/name; p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f: f.write(raw)
        p.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest = dict(schema='ga-e0t1.20.private-creation-r8-preparation.v1', predecessor=BASE,
        prior_close_sha256=CLOSE_SHA, authoring_files={n:sha((HERE/n).read_bytes()) for n in
        ('startup_r8.py','permissions_baseline_r8.py')}, files={n:sha(raw) for n,raw in out.items()},
        preparation_only=True, worker_launch_included=False, execution_admitted=False)
    with (root/'prompt-prep-r8-manifest.json').open('x') as f:
        json.dump(manifest, f, sort_keys=True, indent=2); f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),worker_launch_included=False)))


if __name__ == '__main__': main(*sys.argv[1:])
