"""Rebuild the ga-4z38 platform inspector pinned to the live M5 manifest (draft, not reviewed, not run).

  python3 -I -S -B inspector-build-r1.py <entrypoint-sha256>

Why: the reviewed ga-4z38 package (28693e8c) reuses /var/tmp/ga-y49e-platform-inspector-20260920-r1,
whose binary embeds the pre-M5 manifest pin a6324753. OBSERVE refused on 2026-09-24 20:28Z with
"manifest bytes drift". The original builder lived in /tmp and was lost in the 09-24 reboot, so this
reproduces its recorded steps (archive.json, extract.json, tree.json, compile.json, build-inputs.json
in that build directory), changing only the entrypoint's manifest pin to 2d7eadce.

Steps, each fail-closed:
1. ROOT must not exist; it is created 0700.
2. The Core worktree resolves CORE_COMMIT to CORE_TREE (git rev-parse <commit>^{tree}).
3. git archive of CORE_COMMIT into ROOT/core.tar, extracted into ROOT/source with /usr/bin/tar.
4. The entrypoint file beside this script must have the pinned digest; it is copied to
   ROOT/source/cmd/ga-y49e-platform-inspect/main.go, which must not exist in the Core tree.
5. The Go binary must have GO_SHA; go build -trimpath runs offline in ROOT/source with exactly ENV.
6. The binary digest is recorded in ROOT/build-result.json and printed. Nothing is installed or run.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path('/var/tmp/ga-4z38-platform-inspector-20260924-r1')
CORE = '/home/loucmane/gascity-core-worktrees/ga-ecwh-typed-worker-receipts'
CORE_COMMIT = '796d9a7a67c42294fdc467c107bb59b76e482301'
CORE_TREE = 'f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13'
GO = '/home/loucmane/.local/share/go/1.26.7/bin/go'
GO_SHA = '182d1dc98119d61a6241590e1aaca180d771dbcb1133b9846684aee82d457362'
ENTRY = Path(__file__).resolve().parent / 'platform-inspect-main.go'
CMD = 'cmd/ga-y49e-platform-inspect'
ENV = {'CGO_ENABLED': '0', 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_OPTIONAL_LOCKS': '0',
       'GODEBUG': 'containermaxprocs=0', 'GOENV': 'off', 'GOFLAGS': '-mod=readonly', 'GOPROXY': 'off',
       'GOSUMDB': 'off', 'GOTMPDIR': '/var/tmp', 'GOTOOLCHAIN': 'local', 'GOWORK': 'off',
       'HOME': '/home/loucmane', 'LC_ALL': 'C.UTF-8', 'LOGNAME': 'loucmane',
       'PATH': '/home/loucmane/.local/share/go/1.26.7/bin:/usr/bin:/bin', 'TMPDIR': '/var/tmp',
       'USER': 'loucmane'}


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
                  executed=False, installed=False)
    (ROOT / 'build-result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main(sys.argv[1:])
