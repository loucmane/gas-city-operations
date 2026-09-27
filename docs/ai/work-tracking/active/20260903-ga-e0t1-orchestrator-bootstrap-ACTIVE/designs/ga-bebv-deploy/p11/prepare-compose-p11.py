"""Prepare an isolated exact-source build, retaining all generated evidence.

P11: the reviewed P8 builder (56f3ca48) with the Core source moved to the sequence 16 reproduction clone
at f45a6262 (tree f1011ada) and a fresh root (ga-bebv-deploy/p11/make_p11.py).

No live config reads, namespace launch, receipt writes, or provider invocation.
The process containment implementation is extracted byte-for-byte from the
existing digest-pinned Template interoperability test, not reimplemented.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import types
import stat

HERE = Path(__file__).parent
ROOT = Path('/var/tmp/ga-bebv-p11-compose-diagnostic-20260927')
CORE = Path('/var/tmp/ga-bebv-build-20260927/repro-source')
COMMIT = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TEST = Path('/home/loucmane/gas-city-template/tests/test_managed_worker_canary_provisioning.py')
TEST_SHA = 'c7988ea1574464b370ddeb8455a8cccaecb37657fa01e146b0377709c8a85d23'
GO = '/home/loucmane/.local/share/go/1.26.7/bin/go'
FUNCTIONS = ('_write_phase_evidence', '_owned_process_group_exists',
 '_wait_for_owned_process_group_exit', '_exception_record', '_subprocess_text', '_run_owned_phase')
ENV_FUNCTIONS = ('providerProcessPassthroughEnv', 'passthroughEnv', 'expandEnvMap', 'mergeEnv')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def successful(record):
    if (record['exit_code'] != 0 or record['timed_out'] or record['primary_error'] is not None
            or not record['cleanup']['direct_child_reaped']
            or record['cleanup']['owned_process_group_gone'] is not True
            or record['cleanup']['failures'] or record['cleanup']['unexpected_survivors']):
        raise RuntimeError('phase did not complete cleanly: '+record['phase'])

def verify_archive(source, inventory, diagnostic=False):
    expected = {}
    for row in inventory.split('\0'):
        if not row:
            continue
        header, path = row.split('\t', 1)
        mode, kind, oid = header.split()
        if kind != 'blob' or mode not in ('100644', '100755', '120000'):
            raise RuntimeError('unsupported Git object mode: '+path)
        expected[path] = (mode, oid)
    observed = set()
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in list(dirs):
            if (Path(directory)/name).is_symlink():
                files.append(name)
                dirs.remove(name)
        for name in files:
            path = Path(directory)/name
            relative = path.relative_to(source).as_posix()
            if diagnostic and relative in ('cmd/receipt-compose-diagnostic/main.go',
                                           'cmd/receipt-compose-diagnostic/environment.go'):
                continue
            if relative not in expected:
                raise RuntimeError('untracked archive input: '+relative)
            mode, oid = expected[relative]
            info = path.lstat()
            if mode == '120000':
                if not stat.S_ISLNK(info.st_mode):
                    raise RuntimeError('archive link type: '+relative)
                raw = os.fsencode(os.readlink(path))
            else:
                if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != int(mode[-3:],8):
                    raise RuntimeError('archive file mode: '+relative)
                raw = path.read_bytes()
            actual = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if actual != oid:
                raise RuntimeError('archive blob drift: '+relative)
            observed.add(relative)
    if observed != set(expected):
        raise RuntimeError('archive file inventory mismatch')
    return len(observed)

def main():
    go_sha = sha(Path(GO).read_bytes())
    if go_sha != '182d1dc98119d61a6241590e1aaca180d771dbcb1133b9846684aee82d457362':
        raise RuntimeError('Go executable drift')
    builder_sha = sha(Path(__file__).read_bytes())
    test = TEST.read_bytes()
    if sha(test) != TEST_SHA:
        raise RuntimeError('Template phase-runner source drift')
    tree = ast.parse(test, filename=str(TEST))
    functions = {node.name: ast.get_source_segment(test.decode(), node)
                 for node in tree.body if isinstance(node, ast.FunctionDef)}
    runner = ('from __future__ import annotations\nimport os, json, time, signal, subprocess\n'
              'from pathlib import Path\n\n' + '\n\n'.join(functions[n] for n in FUNCTIONS) + '\n')
    module = types.ModuleType('frozen_phase_runner')
    exec(compile(runner, str(TEST), 'exec'), module.__dict__)
    environment = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane',
        PATH='/home/loucmane/.local/share/go/1.26.7/bin:/usr/bin:/bin',
        GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', GOTOOLCHAIN='local',
        GOENV='off', GOWORK='off', GOPROXY='off', GOSUMDB='off',
        GOFLAGS='-mod=readonly', TMPDIR='/var/tmp', GOTMPDIR='/var/tmp',
        LC_ALL='C.UTF-8', CGO_ENABLED='0', GODEBUG='containermaxprocs=0')
    # Exclusive fresh root: previous attempts are never overwritten or replayed.
    ROOT.mkdir(mode=0o700)
    (ROOT / 'phase_runner.py').write_text(runner)
    record = module._run_owned_phase(name='tree', argv=['/usr/bin/git', '-C', str(CORE),
        'rev-parse', COMMIT+'^{tree}'], cwd=ROOT, environment=environment,
        timeout=30, evidence_path=ROOT/'tree.json')
    successful(record)
    core_tree = record['stdout'].strip()
    if core_tree != 'f1011adaf673937fbda1d254a53c8f0eadf17c5c':
        raise RuntimeError('Core tree binding mismatch')
    record = module._run_owned_phase(name='inventory', argv=['/usr/bin/git', '-C', str(CORE),
        'ls-tree', '-rz', COMMIT], cwd=ROOT, environment=environment,
        timeout=30, evidence_path=ROOT/'inventory.json')
    successful(record)
    inventory = record['stdout']
    archive = ROOT / 'core.tar'
    record = module._run_owned_phase(name='archive', argv=['/usr/bin/git', '-C', str(CORE),
        'archive', '--format=tar', '--output='+str(archive), COMMIT], cwd=ROOT,
        environment=environment, timeout=60, evidence_path=ROOT/'archive.json')
    successful(record)
    source = ROOT / 'source'
    source.mkdir()
    record = module._run_owned_phase(name='extract', argv=['/usr/bin/tar', '--extract',
        '--file='+str(archive), '--directory='+str(source), '--no-same-owner'], cwd=ROOT,
        environment=environment, timeout=60, evidence_path=ROOT/'extract.json')
    successful(record)
    file_count = verify_archive(source, inventory)
    text = (source / 'cmd/gc/cmd_start.go').read_text()
    segments = []
    for name in ENV_FUNCTIONS:
        start = text.index('func '+name+'(')
        end = text.index('\n}\n', start)+3
        segments.append(text[start:end])
    package = source / 'cmd/receipt-compose-diagnostic'
    package.mkdir()
    main_source = (HERE/'compose-main.go').read_bytes()
    (package/'main.go').write_bytes(main_source)
    env_source = ('package main\nimport ("os"; "strings"; '
        '"github.com/gastownhall/gascity/internal/processenv")\n\n'+'\n'.join(segments)).encode()
    (package/'environment.go').write_bytes(env_source)
    manifest = dict(schema='gct.private-compose-build.v1', core_commit=COMMIT,
        core_tree=core_tree, verified_core_files=file_count, template_source_sha256=TEST_SHA,
        phase_functions=list(FUNCTIONS), environment_functions=list(ENV_FUNCTIONS),
        phase_runner_sha256=sha(runner.encode()), main_sha256=sha(main_source),
        environment_sha256=sha(env_source), archive_sha256=sha(archive.read_bytes()),
        go_executable_sha256=go_sha, builder_sha256=builder_sha, build_environment=environment,
        installed=False, worker_launch=False, preserved_root=str(ROOT))
    (ROOT/'build-inputs.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    record = module._run_owned_phase(name='compile', argv=[GO, 'build', '-trimpath',
        '-o', str(ROOT/'compose'), './cmd/receipt-compose-diagnostic'], cwd=source,
        environment=environment, timeout=180, evidence_path=ROOT/'compile.json')
    successful(record)
    verify_archive(source, inventory, diagnostic=True)
    if (package/'main.go').read_bytes() != main_source or (package/'environment.go').read_bytes() != env_source:
        raise RuntimeError('diagnostic source drift during build')
    if sha(Path(GO).read_bytes()) != go_sha or sha(Path(__file__).read_bytes()) != builder_sha:
        raise RuntimeError('build executor drift')
    manifest['binary_sha256'] = sha((ROOT/'compose').read_bytes())
    (ROOT/'build-result.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(ok=True, root=str(ROOT), binary_sha256=manifest['binary_sha256'])))

if __name__ == '__main__':
    main()
