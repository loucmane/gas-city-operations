"""Offline expectation of the synthetic bundled-pack cache the new Core creates (ga-e0t1.15 S2 input).

Runs cache_expect_test.go.txt in two fresh no-hardlink clones: the live source 796d9a7a (Core gc
69d00186) and the new source 9faeabc2 (b2760ea4). The live run must reproduce the synthetic cache
directories and marker content_hash that exist today (read-only comparison), which validates the
method. The new run gives the exact directory names, marker and file manifest the S2 postflight
must admit, and nothing else. No live cache, city or broker is touched.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/var/tmp/ga-e0t1.15-cache-expect-20260925')
RIG = Path('/home/loucmane/gascity/city/rigs/gascity')
CACHE = Path('/home/loucmane/gascity/home/cache/repos')
PROBE = Path(__file__).with_name('cache_expect_test.go.txt')
GO = '/home/loucmane/.local/share/go/1.26.7/bin/go'
SOURCES = {'live': '796d9a7a67c42294fdc467c107bb59b76e482301',
           'new': '9faeabc2892d8c7133111e13ad55af66790a2ac6'}
ENV = {
    'HOME': str(ROOT / 'home'), 'USER': 'loucmane', 'LOGNAME': 'loucmane',
    'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
    'GOENV': 'off', 'GOFLAGS': '-mod=readonly', 'GOTOOLCHAIN': 'local',
    'GOPROXY': 'off', 'GOSUMDB': 'off', 'CGO_ENABLED': '0',
    'GOCACHE': '/home/loucmane/.cache/go-build', 'GOMODCACHE': '/home/loucmane/go/pkg/mod',
    'GIT_OPTIONAL_LOCKS': '0', 'TMPDIR': str(ROOT / 'tmp'), 'GOTMPDIR': str(ROOT / 'tmp'),
    'DO_NOT_TRACK': '1', 'GC_DISABLE_USAGE_METRICS': '1',
}


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
        raise RuntimeError(f'{name} failed rc={result.returncode}')
    return result.stdout


def live_marker(key):
    marker = CACHE / key / '.gc-bundled-pack-cache.toml'
    if not marker.is_file():
        return None
    fields = dict(line.split(' = ', 1) for line in marker.read_text().splitlines() if ' = ' in line)
    return {k: v.strip('"') for k, v in fields.items()}


def main():
    ROOT.mkdir(mode=0o700)
    for sub in ('tmp', 'home'):
        (ROOT / sub).mkdir(mode=0o700)
    save('executor.py', Path(__file__).read_bytes())
    save('probe.go', PROBE.read_bytes())
    git = ['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false']
    results = {}
    for label, commit in SOURCES.items():
        clone = ROOT / ('src-' + label)
        run('clone-' + label, git + ['clone', '--quiet', '--no-hardlinks', '--no-checkout', str(RIG), str(clone)], ROOT)
        run('checkout-' + label, git + ['-C', str(clone), 'checkout', '--quiet', '--detach', commit], ROOT)
        (clone / 'internal/config/zz_cache_expect_test.go').write_bytes(PROBE.read_bytes())
        out = ROOT / (label + '-expectation.json')
        run('probe-' + label, [GO, 'test', '-count=1', '-run', '^TestGaE0t115CacheExpectation$',
                               './internal/config'], clone, dict(ENV, GA_E0T115_OUT=str(out)))
        results[label] = json.loads(out.read_text())
    live, new = results['live'], results['new']
    # A canonical pin is in use when the live binary's synthetic directory for it exists today. Pins the
    # city never imports (no directory) are not materialized by the new Core either.
    used = set()
    for k in live['keys']:
        marker = live_marker(k['Key'])
        if marker is None:
            continue
        assert marker['commit'] == k['Commit'] and marker['content_hash'] == live['content_hash'], (k, marker)
        used.add((k['Source'], k['Commit']))
    assert {c for _, c in used} == {'f895c0ff47d6ee9334ed282a416387eb5b084d24',
                                    '3b3b89f2011e06d84459aa7bea1552382f13930a'}, used
    assert new['content_hash'] != live['content_hash'], 'pack content unchanged; S2 would add no cache'
    new['keys'] = [k for k in new['keys'] if (k['Source'], k['Commit']) in used]
    new_dirs = sorted({k['Key'] for k in new['keys']})
    assert not any((CACHE / key).exists() for key in new_dirs), 'new cache directory already exists'
    changed = sorted(
        {f['Path'] for f in new['materialized_files']} ^ {f['Path'] for f in live['materialized_files']}
        | {n['Path'] for n in new['materialized_files'] for o in live['materialized_files']
           if n['Path'] == o['Path'] and n != o})
    save('expectation.json', json.dumps({
        'ok': True, 'schema': 'ga-e0t1.15.cache-expectation.v1',
        'live': {'content_hash': live['content_hash'], 'keys': live['keys']},
        'new': {'content_hash': new['content_hash'], 'keys': new['keys'],
                'marker_commit_by_key': {k['Key']: k['Commit'] for k in new['keys']},
                'materialized_files': new['materialized_files']},
        'materialized_diff_paths': changed,
        'live_cache_touched': False}, indent=2).encode())
    print(json.dumps({'live_hash': live['content_hash'], 'new_hash': new['content_hash'],
                      'new_dirs': new_dirs, 'diff': changed,
                      'files': len(new['materialized_files'])}, indent=2))
    print(hashlib.sha256((ROOT / 'expectation.json').read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
