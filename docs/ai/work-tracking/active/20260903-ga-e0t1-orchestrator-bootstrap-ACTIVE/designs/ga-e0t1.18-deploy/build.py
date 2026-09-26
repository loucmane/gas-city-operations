"""Offline reproducible custody build of Core main f3856bd1 (ga-e0t1.18); no installation or live operation.

Same seven-setting single-commit-stamp profile as the sequence 13 custody build
(ga-mutg-custody-build-20260920.py, which produced the live gc 69d00186 from 796d9a7a):
go 1.26.7, -mod=readonly -trimpath -buildvcs=false, -ldflags=-X main.commit=<HEAD>, CGO off, GOPROXY off.

Source: the locally signed build-source commit deefb98b, whose tree af5c3f04 is byte-identical to the
GitHub merge commit f3856bd1 (Core PR 48 on b6843d3f, the live build tree c9f19d21). Two fresh
no-hardlink clones are built independently and must produce identical bytes. The effective-input
audit is the retained ga-mutg audit_inputs.py function (sha e35ce80d), executed with only its
constants replaced, before and after the builds; any drift refuses.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/var/tmp/ga-e0t1.18-build-20260926')
RIG = Path('/home/loucmane/gascity/city/rigs/gascity')
AUDIT = Path('/home/loucmane/.local/share/gas-city-staging/ga-mutg-20260920/ga-mutg-build-20260919/audit_inputs.py')
AUDIT_SHA = 'e35ce80d832b7cc3a8dba8b7e8986aac4b67aa89a98a1096341f42ecb930b03d'
GO = '/home/loucmane/.local/share/go/1.26.7/bin/go'
HEAD = 'deefb98b2aed07875df31351d081fbac195cb1cd'
TREE = 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'
MAIN = 'f3856bd146995305c0c2b5f958390b3760b01e21'
ENV = {
    'HOME': '/home/loucmane', 'USER': 'loucmane', 'LOGNAME': 'loucmane',
    'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
    'GOENV': 'off', 'GOFLAGS': '', 'GOTOOLCHAIN': 'local',
    'GOPROXY': 'off', 'GOSUMDB': 'off', 'CGO_ENABLED': '0',
    'GOOS': 'linux', 'GOARCH': 'amd64', 'GOAMD64': 'v1',
    'GIT_OPTIONAL_LOCKS': '0', 'TMPDIR': str(ROOT / 'tmp'),
    'GOTMPDIR': str(ROOT / 'tmp'),
}
SOURCES = [('a', 'repro-source'), ('b', 'repro-source-b')]
# ga-e0t1.18: the gc version probe must never see the operator HOME or GC_HOME: with them its config
# load repairs the registered live city's runtime assets (ga-e0t1.15 PLAN.md S1 correction r3).
PROBE_ENV = dict(ENV, HOME=str(ROOT / 'probe-home'), GC_HOME=str(ROOT / 'probe-gc-home'),
                 DO_NOT_TRACK='1', GC_DISABLE_USAGE_METRICS='1')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, data):
    with (ROOT / name).open('xb') as stream:
        stream.write(data)


def run(name, argv, cwd, env=ENV):
    save(name + '.request.json', json.dumps({'argv': argv, 'cwd': str(cwd), 'environment': env},
                                            indent=2).encode())
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True)
    save(name + '.stdout', result.stdout)
    save(name + '.stderr', result.stderr)
    save(name + '.exit', str(result.returncode).encode())
    if result.returncode:
        raise RuntimeError(f'{name} failed rc={result.returncode}; preserved evidence')
    return result.stdout


def audit_function():
    source = AUDIT.read_bytes()
    assert sha(source) == AUDIT_SHA, 'audit_inputs.py drift'
    body = source.decode().split('\na, count_a = audit(')[0]
    for old, new in [("HEAD = '796d9a7a67c42294fdc467c107bb59b76e482301'", f"HEAD = '{HEAD}'"),
                     ("TREE = 'f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13'", f"TREE = '{TREE}'")]:
        assert body.count(old) == 1, old
        body = body.replace(old, new)
    scope = {'__name__': 'input_audit_functions'}
    exec(compile(body, str(AUDIT), 'exec'), scope)
    scope['ENV'] = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    return scope['audit']


def input_audit(label, audit):
    records = []
    for tag, source in SOURCES:
        graph = run(f'graph-{label}-{tag}', [GO, 'list', '-mod=readonly', '-trimpath', '-buildvcs=false',
                                             '-deps', '-json', './cmd/gc'], ROOT / source)
        graph_path = ROOT / f'graph-{label}-{tag}.stdout'
        assert graph_path.read_bytes() == graph
        records.append(audit(ROOT / source, graph_path))
    assert records[0] == records[1], 'clone input sets differ'
    inputs, local = records[0]
    return {'input_count': len(inputs), 'git_bound_input_count': local,
            'inputs_sha256': sha(json.dumps(inputs, sort_keys=True).encode()), 'inputs': inputs}


def main():
    if os.geteuid() != 1000:
        raise RuntimeError('requires unprivileged operator identity')
    ROOT.mkdir(mode=0o700)
    (ROOT / 'tmp').mkdir(mode=0o700)
    (ROOT / 'probe-home').mkdir(mode=0o700)
    (ROOT / 'probe-gc-home').mkdir(mode=0o700)
    save('executor.py', Path(__file__).read_bytes())
    git = ['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false']
    assert run('rig-main', git + ['-C', str(RIG), 'rev-parse', 'origin/main'], ROOT).decode().strip() == MAIN
    assert run('rig-main-tree', git + ['-C', str(RIG), 'rev-parse', MAIN + '^{tree}'],
               ROOT).decode().strip() == TREE
    assert run('rig-head-tree', git + ['-C', str(RIG), 'rev-parse', HEAD + '^{tree}'],
               ROOT).decode().strip() == TREE
    run('verify-head', git + ['-C', str(RIG), 'verify-commit', HEAD], ROOT)
    for tag, source in SOURCES:
        run(f'clone-{tag}', git + ['clone', '--quiet', '--no-hardlinks', '--no-checkout', str(RIG),
                                   str(ROOT / source)], ROOT)
        run(f'checkout-{tag}', git + ['-C', str(ROOT / source), 'checkout', '--quiet', '--detach', HEAD], ROOT)
    audit = audit_function()
    before = input_audit('before', audit)
    results = []
    for tag, source in SOURCES:
        output = ROOT / ('gc-' + tag)
        run('build-' + tag, [GO, 'build', '-mod=readonly', '-trimpath', '-buildvcs=false',
                             '-ldflags=-X main.commit=' + HEAD, '-o', str(output), './cmd/gc'], ROOT / source)
        run('buildinfo-' + tag, [GO, 'version', '-m', str(output)], ROOT)
        parsed = json.loads(run('version-' + tag, [str(output), 'version', '--json'], ROOT, PROBE_ENV))
        assert parsed['commit'] == HEAD and parsed['version'] == 'dev' and parsed['date'] == 'unknown', parsed
        data = output.read_bytes()
        results.append({'path': str(output), 'sha256': sha(data), 'size': len(data),
                        'mode': oct(output.stat().st_mode & 0o777), 'version': parsed})
    assert results[0]['sha256'] == results[1]['sha256'], 'non-reproducible result'
    after = input_audit('after', audit)
    assert after == before, 'input drift'
    tools = {rel: sha((Path(GO).parents[1] / rel).read_bytes())
             for rel in ('bin/go', 'pkg/tool/linux_amd64/compile', 'pkg/tool/linux_amd64/link',
                         'pkg/tool/linux_amd64/asm')}
    save('input-audit.json', json.dumps(before, indent=2).encode())
    save('result.json', json.dumps({
        'ok': True, 'schema': 'ga-e0t1.18.build.v1', 'head': HEAD, 'tree': TREE, 'main': MAIN,
        'input_count': before['input_count'], 'git_bound_input_count': before['git_bound_input_count'],
        'inputs_sha256': before['inputs_sha256'], 'tools': tools, 'artifacts': results,
        'profile': 'sequence 13 custody profile: go 1.26.7, -mod=readonly -trimpath -buildvcs=false, '
                   '-X main.commit only, CGO off, GOPROXY off',
        'live_adoption': False, 'custody_validator_acceptance': 'still required'}, indent=2).encode())
    print((ROOT / 'result.json').read_text())


if __name__ == '__main__':
    main()
