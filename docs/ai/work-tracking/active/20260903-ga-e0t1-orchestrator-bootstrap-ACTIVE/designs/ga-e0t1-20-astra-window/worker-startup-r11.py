"""One worker-side capability probe, before any product edit.

This is an operational fixture, not an implementation worker or a launcher.
Run only inside the already admitted Gas City worker's ordinary sandbox. It
must never be run by the coordinator and presented as worker evidence.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

WORK = Path('/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20')
OUT = WORK/'.gc/worker-evidence/ga-e0t1.20/r11'
FOREIGN = Path('/var/tmp/ga-e0t1.20-bind-20260927-r1/sandbox-negative')
BASE = 'c6b789bbe6ff677dd04336803dbf2c2e017812ba'
BRANCH = 'codex/ga-e0t1.20-c1-close-admission'
CODEX = Path('/home/loucmane/gascity/bin/codex')
CODEX_SHA = '56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da'
RULES = {
    '.codex/rules/gas-city-native-control.rules': '0a2c32485d71ef31875010ea810deffb0f2936e8c89bb5da2f7f2aeed5044123',
    '.codex/rules/window-restrictions.rules': 'ea2645785163d3f9b6d5ddfe8a08c5ff40b97a8cb1739bca94dd4b2844f15773',
}
DEFAULT = Path('/home/loucmane/.codex/rules/default.rules')
DEFAULT_SHA = '3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516'
OVERRIDES = ('OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL',
             'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read_regular(path, limit=32 << 20):
    path = Path(path)
    require(path.resolve(strict=True) == path, 'input path alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                and before.st_nlink == 1 and before.st_size <= limit, 'input authority or size')
        chunks = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
        raw = b''.join(chunks)
        require(before == os.fstat(fd) and len(raw) == before.st_size, 'input changed')
        return raw
    finally:
        os.close(fd)


def pin(path, digest, limit=32 << 20):
    require(hashlib.sha256(read_regular(path, limit)).hexdigest() == digest, 'pinned input drift')


def directory(path, create=False):
    path = Path(path)
    if create:
        path.mkdir(mode=0o700)
    s = path.lstat()
    require(path.resolve(strict=True) == path and stat.S_ISDIR(s.st_mode)
            and s.st_uid == os.getuid() and not s.st_mode & 0o022, 'directory authority')


def exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def foreign_probe(root):
    """Attempt only a NEW file in the coordinator-created sacrificial directory.

    If a broken sandbox permits it, retain that exact file and fail. No existing
    file, credential, configuration, Git metadata or product source is touched.
    """
    directory(root)
    marker = root/'unexpected-write'
    require(not os.path.lexists(marker), 'foreign probe was already consumed')
    try:
        exclusive(marker, b'Unexpected sandbox write. Preserve as failure evidence.\n')
    except OSError as exc:
        require(exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS), 'not a sandbox refusal')
        require(not os.path.lexists(marker), 'foreign write left an ambiguous result')
        return dict(denied=True, errno=exc.errno, path=str(marker))
    raise RuntimeError('sandbox allowed an out-of-workspace write; marker preserved')


def capture(argv, timeout=30):
    r = subprocess.run(argv, cwd=WORK, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    require(len(r.stdout) + len(r.stderr) <= 1 << 20, 'probe output exceeded bound')
    return r


def launch_contract():
    path = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/launch-contract-r5.py')
    data = read_regular(path)
    require(hashlib.sha256(data).hexdigest() == 'cfd2467d3ce7c8600eb635d28a97249ccdc7bfa055386a423506d3f8e60edc7e', 'launch contract digest')
    import types
    m=types.ModuleType('bound_launch_contract');m.__file__=str(path)
    exec(compile(data,str(path),'exec',dont_inherit=True),m.__dict__)
    return m


def verified_hook():
    helper=launch_contract();path=WORK/helper.HOOK
    raw=read_regular(path);s=path.lstat()
    helper.hook_image(raw,dict(uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink,
        type=stat.S_IFMT(s.st_mode),mode=stat.S_IMODE(s.st_mode),size=s.st_size,
        sha256=hashlib.sha256(raw).hexdigest()))
    return helper


IDENTITY = 'Logged in using ChatGPT'

PATH_ALIAS_WARNING = ('WARNING: proceeding, even though we could not create PATH aliases: '
                      'Read-only file system (os error 30)')

def subscription_status(returncode, stdout, stderr):
    """Admit success plus only the exact local warning observed under protection.

    Unknown diagnostics, API identities, duplicate identities, failed commands
    and malformed bytes still refuse. Never include raw output in an exception.
    The caller retains its pinned executable and provider-override checks.
    """
    if type(returncode) is not int or returncode != 0:
        raise RuntimeError('subscription status command failed')
    if type(stdout) is not bytes or type(stderr) is not bytes or len(stdout) + len(stderr) > 1 << 20:
        raise RuntimeError('subscription status output bound')
    raw = stdout + stderr
    try:
        lines = raw.decode('utf-8', 'strict').strip().splitlines()
    except UnicodeError:
        raise RuntimeError('subscription status encoding') from None
    if lines not in ([IDENTITY], [PATH_ALIAS_WARNING, IDENTITY]):
        raise RuntimeError('subscription identity unproven')
    return dict(subscription_only=True, path_alias_warning=len(lines) == 2,
                status_output_sha256=hashlib.sha256(raw).hexdigest())


def main(session_id):
    require(os.getuid() == os.geteuid() == 1000 and Path.cwd() == WORK, 'worker context')
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{1,127}', session_id) is not None, 'session ID')
    require(os.environ.get('GC_SESSION_ID') == session_id, 'managed session identity differs')
    require(sys.version_info[:3] == (3, 12, 3), 'interpreter version drift')
    # Names/presence only; never persist a credential value.
    require(not any(name in os.environ for name in OVERRIDES), 'API/provider override is present')
    require(os.environ.get('GIT_OPTIONAL_LOCKS') == '0', 'optional locks are not disabled')
    for rel, digest in RULES.items():
        pin(WORK/rel, digest)
    pin(DEFAULT, DEFAULT_SHA)
    resolved = CODEX.resolve(strict=True)
    require(resolved == Path('/home/loucmane/.codex/packages/standalone/releases/'
                            '0.153.4-x86_64-unknown-linux-musl/bin/codex'), 'Codex resolution')
    pin(resolved, CODEX_SHA, 256 << 20)
    for args, expected in ((['rev-parse', 'HEAD'], BASE), (['branch', '--show-current'], BRANCH)):
        r = capture(['/usr/bin/git', '--no-optional-locks', *args])
        require(r.returncode == 0 and r.stdout.decode().strip() == expected, 'worker Git identity')
    r = capture(['/usr/bin/git', '--no-optional-locks', 'status', '--porcelain=v1', '--untracked-files=all', '-z'])
    require(r.returncode == 0, 'worker Git status failed')
    verified_hook().startup_status(r.stdout)
    auth = capture([str(CODEX), 'login', 'status'])
    subscription_status(auth.returncode, auth.stdout, auth.stderr)
    # No auth output, credentials or environment values go into evidence.
    for path in (WORK/'.gc', WORK/'.gc/worker-evidence'):
        if path.exists():
            directory(path)
        else:
            directory(path, create=True)
    directory(OUT, create=True)
    exclusive(OUT/'positive-write.txt', b'Owned workspace write proof.\n')
    negative = foreign_probe(FOREIGN)
    report = dict(schema='ga-e0t1.20.worker-startup.v1', task='ga-e0t1.20',
                  session_id=session_id, worktree=str(WORK), base=BASE, branch=BRANCH,
                  subscription='ChatGPT', provider_overrides_absent=True, credential_values_exported=False,
                  codex_sha256=CODEX_SHA, local_rules=RULES, default_rules_sha256=DEFAULT_SHA,
                  workspace_write=True, foreign_write=negative, source_edit_released=False)
    exclusive(OUT/'startup.json', (json.dumps(report, indent=2, sort_keys=True)+'\n').encode())
    print(json.dumps(dict(ok=True, task='ga-e0t1.20', report=str(OUT/'startup.json'),
                          source_edit_released=False)))


if __name__ == '__main__':
    require(len(sys.argv) == 2, 'exactly one real session ID is required')
    main(sys.argv[1])
