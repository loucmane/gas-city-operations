"""R7 exact observed protocol correction; generation only, never provider execution."""
import ast
import hashlib
import json
from pathlib import Path
import build

R6 = 'cb4183cccaa35196ec733b427be4cfd9944cab11'
EVIDENCE = '.gc/worker-evidence/ga-e0t1.20/r7'
NATIVE_ERROR = "exec_command failed: CreateProcess { message: \"Rejected(\\\"`/usr/bin/zsh -lc 'gpg --version'` rejected: Unsigned candidate workers must not invoke GPG directly; return the candidate for approved managed delivery.\\\")\" }"
NATIVE_POSTURE = json.loads("{\"workspace_roots\":[\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20\"],\"sandbox_policy\":{\"type\":\"workspace-write\",\"network_access\":false,\"exclude_tmpdir_env_var\":false,\"exclude_slash_tmp\":false},\"permission_profile\":{\"type\":\"managed\",\"file_system\":{\"type\":\"restricted\",\"entries\":[{\"path\":{\"type\":\"special\",\"value\":{\"kind\":\"root\"}},\"access\":\"read\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20\"},\"access\":\"write\"},{\"path\":{\"type\":\"special\",\"value\":{\"kind\":\"slash_tmp\"}},\"access\":\"write\"},{\"path\":{\"type\":\"special\",\"value\":{\"kind\":\"tmpdir\"}},\"access\":\"write\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20\"},\"access\":\"write\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.git\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.agents\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.codex\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops/.git/worktrees/ga-e0t1.20\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.git\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.agents\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.codex\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"}]},\"network\":\"restricted\"},\"file_system_sandbox_policy\":{\"kind\":\"restricted\",\"entries\":[{\"path\":{\"type\":\"special\",\"value\":{\"kind\":\"root\"}},\"access\":\"read\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20\"},\"access\":\"write\"},{\"path\":{\"type\":\"special\",\"value\":{\"kind\":\"slash_tmp\"}},\"access\":\"write\"},{\"path\":{\"type\":\"special\",\"value\":{\"kind\":\"tmpdir\"}},\"access\":\"write\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20\"},\"access\":\"write\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.git\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.agents\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.codex\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops/.git/worktrees/ga-e0t1.20\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.git\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.agents\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"},{\"path\":{\"type\":\"path\",\"path\":\"/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.codex\"},\"access\":\"read\",\"missing_path_behavior\":\"skip\"}]}}")


def frozen(name):
    return build.git('show', R6+':'+build.NEW+'/'+name)


def validator_source():
    text = frozen('startup-validation.py').decode()
    text = build.once(text, "EVIDENCE = '.gc/worker-evidence/'+TASK", 'EVIDENCE = '+repr(EVIDENCE))
    # Only these two literal request spellings have the same default sandbox.
    # No JS evaluation, arbitrary canonicalization or executable parser.
    text = build.once(text, '# Runtime input pinning',
        "NEGATIVE_SCRIPTS = tuple(s+suffix for s in (NEGATIVE_SCRIPT,\n"
        "    NEGATIVE_SCRIPT.replace('\"sandbox_permissions\":\"use_default\",',''))\n"
        "    for suffix in ('','\\n'))\n"
        "NATIVE_ERROR = "+repr(NATIVE_ERROR)+"\n"
        "NATIVE_POSTURE = "+repr(NATIVE_POSTURE)+"\n"
        "# Runtime input pinning")
    replacement = '''def turn(value):
    require(value.get('cwd') == WORK and value.get('approval_policy') == 'never'
        and value.get('model') == 'gpt-6-astra' and value.get('effort') == 'high', 'native turn posture')
    policy = value.get('sandbox_policy')
    explicit = dict(type='workspace-write',writable_roots=[WORK],network_access=False)
    if policy == explicit:
        # Retain the old closed synthetic/native form. If the newer fields are
        # present they must agree too, rather than silently accepting a conflict.
        for key, expected in NATIVE_POSTURE.items():
            if key != 'sandbox_policy' and key in value:
                require(value[key] == expected, 'native permission detail drift')
    else:
        # 0.153.4 serializes the cwd write root implicitly, while retaining the
        # complete restricted permission profile. Require every observed field.
        require(all(value.get(key) == expected for key, expected in NATIVE_POSTURE.items()),
                'native sandbox posture')
'''
    text = build.replace_function(text,'turn',replacement)
    text = build.once(text, "original.get('input') != NEGATIVE_SCRIPT", "original.get('input') not in NEGATIVE_SCRIPTS")
    old = """                require(output.startswith('exec command rejected:')
                        and ('blocked by policy' in output or 'forbidden by policy' in output),
                        'not a native code-mode policy refusal')"""
    new = """                require(output == NATIVE_ERROR or (
                        output.startswith('exec command rejected:')
                        and ('blocked by policy' in output or 'forbidden by policy' in output)),
                        'not a native code-mode policy refusal')"""
    text = build.once(text,old,new)
    # Old evidence is already in the baseline. New attempt is create-only.
    text = build.once(text,"allowed = {'.gc','.gc/worker-evidence',EVIDENCE,",
        "allowed = {'.gc','.gc/worker-evidence','.gc/worker-evidence/'+TASK,EVIDENCE,")
    ast.parse(text)
    return text


def release_source(runtime_sha):
    text = frozen('startup-release.py').decode()
    text = build.replace_function(text,'worker_identity',
        "def worker_identity(pane, session, validator, read, runtime):\n"
        "    return runtime.worker_identity(pane,session,validator,read)\n")
    text = build.once(text,"    inspector=w.module(HERE/'candidate-inspect.py',INSPECT_SHA)",
        "    inspector=w.module(HERE/'candidate-inspect.py',INSPECT_SHA)\n"
        "    runtime=w.module(HERE/'runtime-process-r7.py',"+repr(runtime_sha)+")")
    text = build.once(text,"proof=worker_identity(int(fields[1]),s,v,inspector.file_bytes)",
        "proof=worker_identity(int(fields[1]),s,v,inspector.file_bytes,runtime)")
    start = "    immediate=process_table()\n"
    end = "    pidfd=os.pidfd_open(proof['pid'])"
    a=text.index(start); z=text.index(end,a)
    text=text[:a]+"    runtime.revalidate(proof,v,inspector.file_bytes)\n"+text[z:]
    ast.parse(text)
    return text


def worker_probe():
    text = frozen('worker-startup-r6.py').decode()
    return build.once(text,"OUT = WORK/'.gc/worker-evidence/ga-e0t1.20'",
                      "OUT = WORK/"+repr(EVIDENCE)).encode()
