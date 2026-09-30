"""Create-only R6 subscription-output preparation, not a worker launch."""
import ast
import hashlib
import json
from pathlib import Path
import sys

import auth_probe_r6 as auth
import build

R5 = auth.R5
R5_PREP = '481e97df3621e570b105d00b63f884e608254770'
ROOT = '/var/tmp/ga-e0t1.20-prompt-prep-20260928-r6'
RECOVERY = '/var/tmp/ga-e0t1.20-terminal-20260928-r5/result.json'
RECOVERY_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
CLOSE = '/var/tmp/ga-e0t1.20-r5-close-20260928T130452Z/result.json'
CLOSE_SHA = '53b7501005e7f48722f022e023995ba6c9c8b83f3e7adcfa4c6d9e6089da46ea'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def frozen(name, commit=R5):
    return build.git('show', commit+':'+build.NEW+'/'+name)


def components():
    old_probe, probe = auth.worker_probe()
    old_prompt = frozen('PRECLAIM-R5.md')
    prompt = old_prompt.replace(sha(old_probe).encode(), sha(probe).encode())
    prompt = prompt.replace(b'worker-startup.py', b'worker-startup-r6.py')
    prompt = prompt.replace(b' r5 ', b' r6 ')
    assert old_prompt.count(sha(old_probe).encode()) == 2
    text = frozen('prompt-prep-r5.py').decode()
    text = text.replace('ga-e0t1.20-prompt-prep-20260928-r5', ROOT.split('/')[-1])
    text = text.replace('PRECLAIM-R5.md', 'PRECLAIM-R6.md')
    text = build.once(text, "PROMPT_SHA='"+sha(old_prompt)+"'", "PROMPT_SHA='"+sha(prompt)+"'")
    text = build.once(text, "RECOVERY=Path('/var/tmp/ga-e0t1.20-terminal-20260928-r4/result.json')",
                      'RECOVERY=Path('+repr(RECOVERY)+')')
    text = build.once(text, "RECOVERY_SHA='459cacbbaf67e60f741af656277ebf11161a4abe3bab49637e7407db40f16438'",
                      'RECOVERY_SHA='+repr(RECOVERY_SHA))
    old = "    assert recovered['worker_started_in_window'] is True and recovered['source_release_sent'] is False\n" \
          "    assert recovered['open_sessions']==0"
    new = "    closed=json.loads(old.read(Path("+repr(CLOSE)+"),"+repr(CLOSE_SHA)+"))\n" \
          "    assert closed == dict(ok=True,closed_session='ci-rks41',open_sessions=0,\n" \
          "        city_tmux_sessions=0,worktree_processes=0,tmux_server_killed=False,signals_sent=False,\n" \
          "        executor_sha256='33f22aafa01ac42f7589c6f856e3bae06baaec93a60233ee3f167ffc3adaff40')\n" \
          "    assert not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r5/proof.json').exists()\n" \
          "    # The terminal observer launched none; its result is not relabeled\n" \
          "    # as proof that the completed R5 window had no worker."
    text = build.once(text, old, new)
    text = build.once(text, "recovery_result_sha256=RECOVERY_SHA,supplemental_prompt_preparation=True,",
        "recovery_result_sha256=RECOVERY_SHA,prior_close_sha256="+repr(CLOSE_SHA)+",\n"
        "                supplemental_prompt_preparation=True,")
    executor = text.encode()
    wrapper = frozen('operator/PROMPT-PREP-R5.sh', R5_PREP).decode()
    wrapper = wrapper.replace('PROMPT-PREP-R5.sh', 'PROMPT-PREP-R6.sh')
    wrapper = wrapper.replace('/prompt-prep-r5.py', '/prompt-prep-r6.py')
    wrapper = wrapper.replace('ga-e0t1.20-prompt-prep-20260928-r5', ROOT.split('/')[-1])
    wrapper = wrapper.replace('prompt-prep-r5-', 'prompt-prep-r6-')
    wrapper = build.once(wrapper, sha(frozen('prompt-prep-r5.py', R5_PREP)), sha(executor))
    out = {'worker-startup-r6.py':probe, 'PRECLAIM-R6.md':prompt,
           'prompt-prep-r6.py':executor, 'operator/PROMPT-PREP-R6.sh':wrapper.encode()}
    for name, raw in out.items():
        if name.endswith('.py'):
            ast.parse(raw, filename=name)
    return out


def main(output):
    root = Path(output)
    assert not root.exists(), 'create-only R6 preparation'
    out = components()
    root.mkdir(mode=0o700)
    for name, raw in out.items():
        p = root/name
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as f:
            f.write(raw)
        p.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest = dict(schema='ga-e0t1.20.auth-status-r6-preparation.v1', predecessor=R5,
        recovery_result_sha256=RECOVERY_SHA, prior_close_sha256=CLOSE_SHA,
        authoring_files={name:sha((Path(__file__).parent/name).read_bytes()) for name in
            ('auth_status_r6.py','auth_probe_r6.py','startup_r6.py')},
        files={name:sha(raw) for name,raw in out.items()},
        preparation_only=True, worker_launch_included=False, execution_admitted=False)
    with (root/'prompt-prep-r6-manifest.json').open('x') as f:
        json.dump(manifest,f,indent=2,sort_keys=True)
        f.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),worker_launch_included=False)))


if __name__ == '__main__':
    main(*sys.argv[1:])
