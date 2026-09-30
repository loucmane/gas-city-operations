"""Build the exact M15 observer from adopted Core in a fresh private root.

No live installation or inspector execution. Offline existing dependencies only.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path('/var/tmp/ga-mb91-platform-inspector-m15-20260930-r1')
CORE = '/var/tmp/ga-e0t1.22-custody-build-20260930-r1/repro-source'
CORE_COMMIT = '53f2e232da03a1e176cf64cf4fe1aa9c3f3beb6b'
CORE_TREE = '2a253aabadc432c3c9f8953961b7a0db96291191'
GO = '/home/loucmane/.local/share/go/1.26.7/bin/go'
GO_SHA = '182d1dc98119d61a6241590e1aaca180d771dbcb1133b9846684aee82d457362'
ENTRY = Path(__file__).resolve().parent / 'platform-inspect-main.go'
CMD = 'cmd/ga-y49e-platform-inspect'
ENV = {'CGO_ENABLED': '0', 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_OPTIONAL_LOCKS': '0',
       'GODEBUG': 'containermaxprocs=0', 'GOENV': 'off', 'GOFLAGS': '-mod=readonly', 'GOPROXY': 'off',
       'GOSUMDB': 'off', 'GOTMPDIR': '/var/tmp', 'GOTOOLCHAIN': 'local', 'GOWORK': 'off',
       'HOME': '/home/loucmane', 'LC_ALL': 'C.UTF-8', 'LOGNAME': 'loucmane',
       'PATH': '/home/loucmane/.local/share/go/1.26.7/bin:/usr/bin:/bin', 'TMPDIR': '/var/tmp',
       'USER': 'loucmane', 'GOCACHE': str(ROOT / 'go-cache')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def run(argv, cwd, timeout):
    result = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True, timeout=timeout)
    require(result.returncode == 0, 'command refused: %s: %s' % (argv[:3], result.stderr.decode()[-400:]))
    return result.stdout.decode()


def main(argv):
    require(len(argv) == 1, 'usage: inspector-build-r1.py <entrypoint-sha256>')
    require(os.getuid() == os.geteuid() == 1000, 'wrong user')
    require(sha(ENTRY) == argv[0], 'entrypoint digest drift')
    require(sha(GO) == GO_SHA, 'go toolchain drift')
    require(not os.path.lexists(ROOT), 'build root already exists')
    ROOT.mkdir(mode=0o700)
    tree = run(['/usr/bin/git', '-C', CORE, 'rev-parse', CORE_COMMIT + '^{tree}'], ROOT, 60).strip()
    require(tree == CORE_TREE, 'core tree drift')
    run(['/usr/bin/git', '-C', CORE, 'archive', '--format=tar', '--output=' + str(ROOT / 'core.tar'),
         CORE_COMMIT], ROOT, 300)
    source = ROOT / 'source'
    source.mkdir(mode=0o700)
    # The same extraction the 09-20 build recorded (extract.json); the Core tree holds relative symlinks.
    run(['/usr/bin/tar', '--extract', '--file=' + str(ROOT / 'core.tar'), '--directory=' + str(source),
         '--no-same-owner'], ROOT, 300)
    target = source / CMD / 'main.go'
    require(not os.path.lexists(target.parent), 'entrypoint directory already in the core tree')
    target.parent.mkdir(parents=True)
    target.write_bytes(ENTRY.read_bytes())
    run([GO, 'build', '-trimpath', '-o', str(ROOT / 'platform-inspect'), './' + CMD], source, 180)
    result = dict(binary_sha256=sha(ROOT / 'platform-inspect'), core_commit=CORE_COMMIT, core_tree=CORE_TREE,
                  entrypoint_sha256=argv[0], builder_sha256=sha(__file__), go_sha256=GO_SHA, environment=ENV,
                  manifest_sha256='d02a3adbd044ebaf4f1dd4606c0af5dea50bcab4bca5efb2f3da5aab14e68481',
                  executed=False, installed=False)
    (ROOT / 'build-result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main(sys.argv[1:])
