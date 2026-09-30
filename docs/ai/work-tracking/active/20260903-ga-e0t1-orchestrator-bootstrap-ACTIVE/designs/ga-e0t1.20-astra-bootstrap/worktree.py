"""S1 WORKTREE: one exact registered unsigned workspace; no worker, route, or lifecycle.

Derived from S5 WORKTREE and the existing candidate_git verifier. Unlike S5's
Template checkout, Operations has no attributes or content drivers. Partial
failure preserves intent, workspace and branch; no remove/reset/replay path.
"""
import hashlib
import base64
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

HERE = Path(__file__).parent
ROOT = Path('/var/tmp/ga-e0t1.20-worktree-20260927-r1')
OPS = Path('/home/loucmane/gas-city-ops')
CANDIDATE_ROOT = Path('/home/loucmane/gas-city-ops-candidate-worktrees')
WORK = CANDIDATE_ROOT/'ga-e0t1.20'
ADMIN = OPS/'.git/worktrees/ga-e0t1.20'
BASE = 'c6b789bbe6ff677dd04336803dbf2c2e017812ba'
BRANCH = 'codex/ga-e0t1.20-c1-close-admission'
PRIMARY = '7720D1FE503A88EDECA61A6F0C7D823543E01875'
TEMPLATE = Path('/home/loucmane/gas-city-template')
TOOLS = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-6utp-activation-r10/candidate_git.py')
TOOLS_SHA = 'd2894e829618ad1fdcb5640b47b99baa3c783173acccb4f7f5918c958823bebe'
DEFAULT = Path('/home/loucmane/.codex/rules/default.rules')
DEFAULT_SHA = '3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516'
RESTRICTION_SHA = 'ea2645785163d3f9b6d5ddfe8a08c5ff40b97a8cb1739bca94dd4b2844f15773'
RULES_SHA = '0a2c32485d71ef31875010ea810deffb0f2936e8c89bb5da2f7f2aeed5044123'
ASSETS = {
    'bin/gct-codex-rules': '607b5d27d1028898cf7c5a00e2490fb3f11bf8484a1930dbef3b423e09802b8f',
    'bin/gct-provider-command': 'e8e630a10c6813977b66bfe102c865be651c452556eb88e3d5416b1754690748',
    'templates/codex/rules/profiles.json': '903f0a272f9002444702bdf6a8f4e9feab3db1e5fa17a7fda433b6e76a76fb62',
    'templates/codex/rules/gas-city-native-control.rules': '77af2666ef5fb80714c1d6500bcfee056055e9b54787ea4800cad97a13852ff6',
    'templates/codex/rules/overlays/unsigned-candidate.rules': '183a4209de90525e74c9b44a47d6aeaea1faeceaa475771728d23fb8ef3db836',
}
CODEX = Path('/home/loucmane/gascity/bin/codex')
CODEX_SHA = '56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da'
ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane', LANG='C.UTF-8',
           PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin',
           GC_HOME='/home/loucmane/gascity/home', GIT_CONFIG_NOSYSTEM='1',
           GIT_CONFIG_GLOBAL='/dev/null', GIT_ATTR_NOSYSTEM='1', GIT_OPTIONAL_LOCKS='0',
           GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1')


def read(path, expected):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_uid == 1000 and before.st_nlink == 1
        assert before.st_size <= 4*1024*1024
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(4*1024*1024+1)
        assert before == os.fstat(fd) and before == path.lstat() and len(raw) == before.st_size
    finally:
        os.close(fd)
    assert hashlib.sha256(raw).hexdigest() == expected, str(path)
    return raw


def write(path, data, mode=0o600):
    raw = data if isinstance(data, bytes) else (json.dumps(data, sort_keys=True, indent=2)+'\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def codex_identity():
    path = CODEX.resolve(strict=True)
    assert str(path).startswith('/home/loucmane/.codex/packages/standalone/'), 'unmanaged Codex path'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_uid == 1000 and before.st_nlink == 1
        assert 0 < before.st_size < 512*1024*1024
        digest = hashlib.sha256()
        count = 0
        while chunk := os.read(fd, 1024*1024):
            count += len(chunk)
            assert count <= before.st_size, 'provider grew during read'
            digest.update(chunk)
        assert before == os.fstat(fd) and before == path.lstat() and count == before.st_size
        assert CODEX.resolve(strict=True) == path and digest.hexdigest() == CODEX_SHA
    finally:
        os.close(fd)
    return str(path)


def git(*args, expected=(0,)):
    result = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', str(OPS),
        '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-c', 'core.attributesFile=/dev/null',
        '-c', 'gpg.program=/usr/bin/gpg', '-c', 'gpg.format=openpgp', *args], env=ENV,
        capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
    assert result.returncode in expected, (args, result.returncode, result.stderr[-2000:])
    return result


def source_tree(tree):
    entries = [e for e in tree.split(b'\0') if e]
    assert not [e for e in entries if e.startswith(b'160000 ')], 'gitlink'
    paths = [e.split(b'\t', 1)[1] for e in entries]
    assert not [p for p in paths if p.rsplit(b'/', 1)[-1] in (b'.gitattributes', b'.gitmodules')]
    assert not [p for p in paths if p.startswith(b'.codex/rules/')], 'pre-existing rules'


def rule_inventory():
    folder = WORK/'.codex/rules'
    expected = {'gas-city-native-control.rules': RULES_SHA, 'window-restrictions.rules': RESTRICTION_SHA}
    assert sorted(p.name for p in folder.iterdir()) == sorted(expected), 'unexpected policy file'
    for name, digest in expected.items():
        read(folder/name, digest)
        assert stat.S_IMODE((folder/name).lstat().st_mode) == 0o644
    return {'.codex/rules/'+name: digest for name, digest in expected.items()}


def main():
    assert os.getuid() == os.geteuid() == 1000 and globals().get('_SOURCE_SHA')
    read(Path(__file__), _SOURCE_SHA)
    raw = read(TOOLS, TOOLS_SHA)
    cg = types.ModuleType('candidate_git'); cg.__file__ = str(TOOLS)
    exec(compile(raw, str(TOOLS), 'exec', dont_inherit=True), cg.__dict__)
    # Exact bytes preserved inside the signed lossless input container.
    container = HERE/'inputs.json'
    container_stat = container.lstat()
    assert stat.S_ISREG(container_stat.st_mode) and container_stat.st_size < 4*1024*1024
    restriction = base64.b64decode(json.loads(container.read_bytes())['window-restrictions.rules'], validate=True)
    assert hashlib.sha256(restriction).hexdigest() == RESTRICTION_SHA
    read(DEFAULT, DEFAULT_SHA)
    codex = codex_identity()
    for path, digest in ASSETS.items():
        read(TEMPLATE/path, digest)
    assert not os.path.lexists(ROOT) and not os.path.lexists(WORK) and not os.path.lexists(ADMIN)
    assert CANDIDATE_ROOT.resolve() == CANDIDATE_ROOT
    state = CANDIDATE_ROOT.lstat()
    assert stat.S_ISDIR(state.st_mode) and state.st_uid == 1000 and not state.st_mode & 0o022
    assert git('rev-parse', '--verify', BASE+'^{commit}').stdout.decode().strip() == BASE
    signature = git('verify-commit', '--raw', BASE).stderr.decode()
    assert any(line.startswith('[GNUPG:] VALIDSIG ') and line.split()[-1] == PRIMARY
               for line in signature.splitlines()), 'unverified source signature'
    assert git('rev-parse', '--verify', '--quiet', 'refs/heads/'+BRANCH, expected=(1,)).returncode == 1
    assert git('config', '--get-regexp', '^include', expected=(1,)).returncode == 1
    assert git('config', '--includes', '--get-regexp', r'^(filter|diff|merge)\.', expected=(1,)).returncode == 1
    assert not os.path.lexists(OPS/'.git/info/attributes')
    source_tree(git('ls-tree', '-r', '-z', '--full-tree', BASE).stdout)
    ROOT.mkdir(mode=0o700)
    write(ROOT/'intent.json', dict(base=BASE, worktree=str(WORK), branch=BRANCH, executor_sha256=_SOURCE_SHA))
    git('worktree', 'add', '-b', BRANCH, str(WORK), BASE)
    assert cg.verify_linked(CANDIDATE_ROOT, OPS/'.git', WORK, WORK.name) == ADMIN
    assert cg.git(ADMIN, WORK, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == BASE
    cg.no_drivers(ADMIN, WORK)
    cg.no_gitlinks(ADMIN, WORK, BASE)
    assert cg.git(ADMIN, WORK, 'status', '--porcelain', '--ignored', '-z', '--untracked-files=all') == b''
    rules = WORK/'.codex/rules'
    assert not os.path.lexists(rules)
    rules.mkdir(mode=0o755)
    # Existing installer, confined to this new local rules directory and its owned temporary directory.
    (ROOT/'tmp').mkdir(mode=0o700)
    args = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--unshare-pid', '--die-with-parent', '--new-session',
            '--proc', '/proc', '--dev', '/dev', '--bind', str(rules), str(rules),
            '--bind', str(ROOT/'tmp'), '/tmp', '--', str(TEMPLATE/'bin/gct-codex-rules'),
            '--apply', '--json', '--work-dir', str(WORK), '--profile', 'unsigned-candidate']
    result = subprocess.run(args, env=ENV, cwd='/', capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
    write(ROOT/'installer.stdout', result.stdout)
    write(ROOT/'installer.stderr', result.stderr)
    assert result.returncode == 0, 'confined installer refused'
    report = json.loads(result.stdout)
    assert report['ok'] is True and report['provider_command']['changed'] is False
    assert len(report['rigs']) == 1 and report['rigs'][0]['profile'] == 'unsigned-candidate'
    assert report['rigs'][0]['actual_sha256'] == RULES_SHA
    write(rules/'window-restrictions.rules', restriction, mode=0o644)
    inventory = rule_inventory()
    # Only the two exact generated rules may appear as ignored/untracked output.
    status = cg.git(ADMIN, WORK, 'status', '--porcelain', '--ignored', '-z', '--untracked-files=all')
    assert set(status.split(b'\0')) == {b'', *(b'!! '+p.encode() for p in inventory)}, status
    read(DEFAULT, DEFAULT_SHA)
    assert codex_identity() == codex
    for path, digest in ASSETS.items():
        read(TEMPLATE/path, digest)
    write(ROOT/'result.json', dict(ok=True, base=BASE, branch=BRANCH, worktree=str(WORK), admin=str(ADMIN),
        tracked_clean=True, local_rules=inventory, default_rules_unchanged=True, worker_launched=False,
        execution_authorized_by_this_result=False, executor_sha256=_SOURCE_SHA))
    print(json.dumps(dict(ok=True, worktree=str(WORK), worker_launched=False, preparation_only=True)))


if __name__ == '__main__':
    assert len(sys.argv) == 1
    main()
