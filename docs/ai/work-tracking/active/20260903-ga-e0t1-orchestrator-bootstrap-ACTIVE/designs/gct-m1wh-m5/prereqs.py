"""Live M5 prerequisites, one guarded step per invocation (operator decision 2026-09-23).

Order: inputs, cli, city, checkout, render, authority. Each step proves its
exact precondition, performs one bounded change, proves the postcondition and
writes one exclusive record under reports/m5-inputs. A step never repeats: an
existing record or an unexpected state refuses. `rollback` restores the four
live files and the canonical checkout while the installed platform manifest is
still the R9 predecessor. No lifecycle, timer, worker, signer or Bead action.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

HERE = Path(__file__).parent
p = HERE/'manifest_candidate.py'
m = types.ModuleType('m5_candidate'); m.__file__ = str(p)
exec(compile(p.read_bytes(), str(p), 'exec', dont_inherit=True), m.__dict__)

INPUTS = Path(m.O + '/reports/m5-inputs')
CITY = Path('/home/loucmane/gascity/city')
CLI = Path('/home/loucmane/gascity/bin/claude')
CLI_BACKUP = Path('/home/loucmane/gascity/bin/claude.gct-m1wh-before-2.1.280')
STAGED = Path('/home/loucmane/.local/share/gas-city-staging/gct-er3h/claude-2.1.280')
CITY_BACKUP = Path(m.O + '/reports/r5/i/00')
RIG = CITY/'managed/rig-permissions.toml'
RIG_BACKUP = INPUTS/'rig-permissions.toml.before'
TEMPLATE = Path(m.TEMPLATE)
OLD_COMMIT = '51440da2d0ff12912ff7d2ec26d239849e3bc342'
RENDERER_SHA = '20dc4146d52250e63f2d782e62a56612ce28506e469a09891de3cb85c215bcd4'
UNTRACKED = '?? deploy/\n?? gas_city_template.egg-info/\n'
INSTALLED = CITY/'.gc/platform/install-manifest.json'
GIT_ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/home/loucmane', 'LANG': 'C', 'GIT_CONFIG_NOSYSTEM': '1'}
CITY_ENV = {'PATH': '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/loucmane',
            'LANG': 'C', 'GC_HOME': '/home/loucmane/gascity/home'}
EDITS = {21: ('model = "opus-5"\n', 'model = "opus-5-5"\n'),
         28: ('default = "opus-5"\n', 'default = "opus-5-5"\n'),
         31: ('value = "opus-5"\n', 'value = "opus-5-5"\n'),
         32: ('label = "Claude Opus 5"\n', 'label = "Claude Opus 5.5"\n'),
         33: ('flag_args = ["--model", "claude-opus-5"]\n', 'flag_args = ["--model", "claude-opus-5-5"]\n'),
         236: ('model = "opus-5"\n', 'model = "opus-5-5"\n')}
STEPS = ('inputs', 'cli', 'city', 'checkout', 'render', 'authority')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(path):
    st = os.lstat(path)
    return dict(sha256=sha(path) if stat.S_ISREG(st.st_mode) else None, mode=stat.S_IMODE(st.st_mode),
                uid=st.st_uid, gid=st.st_gid, nlink=st.st_nlink, regular=stat.S_ISREG(st.st_mode))


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_exclusive(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_dir(Path(path).parent)


def replace_atomic(path, data, mode):
    tmp = Path(path).parent/('.' + Path(path).name + '.gct-m1wh-m5.tmp')
    write_exclusive(tmp, data, mode)
    os.replace(tmp, path)
    fsync_dir(Path(path).parent)


def run(argv, env, cwd='/'):
    result = subprocess.run(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=120, check=False)
    return dict(argv=argv, returncode=result.returncode,
                stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace'))


def git(repo, *args):
    return run(['/usr/bin/git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                '-c', 'core.hooksPath=/dev/null', '-c', 'core.untrackedCache=false', '-C', str(repo), *args],
               GIT_ENV)


def record(step, value):
    value = dict(value, step=step, bead='ga-0t04', live_mutation=step != 'inputs')
    write_exclusive(INPUTS/('prereq-' + step + '.json'),
                    (json.dumps(value, sort_keys=True, indent=1) + '\n').encode(), 0o600)
    print(json.dumps(dict(step=step, ok=True, record=str(INPUTS/('prereq-' + step + '.json')))))


def previous_done(step):
    index = STEPS.index(step)
    require(not os.path.lexists(INPUTS/('prereq-' + step + '.json')), 'step already consumed: ' + step)
    for earlier in STEPS[:index]:
        require(os.path.lexists(INPUTS/('prereq-' + earlier + '.json')), 'earlier step missing: ' + earlier)
    require(sha(INSTALLED) == m.OLD_MANIFEST_SHA, 'installed platform manifest is not the R9 predecessor')


def new_city_bytes():
    raw = CITY_BACKUP.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == m.CITY_OLD, 'city backup bytes')
    lines = raw.decode().splitlines(True)
    for number, (before, after) in EDITS.items():
        require(lines[number-1] == before, 'city line %d' % number)
        lines[number-1] = after
    data = ''.join(lines).encode()
    require(hashlib.sha256(data).hexdigest() == m.CITY_NEW, 'derived city bytes')
    return data


def step_inputs():
    require(not os.path.lexists(INPUTS), 'inputs directory already exists')
    require(sha(INSTALLED) == m.OLD_MANIFEST_SHA, 'installed platform manifest is not the R9 predecessor')
    require(sha(RIG) == m.RIGPERM_OLD and sha(CITY/'city.toml') == m.CITY_OLD, 'live predecessor bytes')
    os.mkdir(INPUTS, 0o700)
    fsync_dir(INPUTS.parent)
    write_exclusive(m.CITY_SOURCE, new_city_bytes(), 0o644)
    write_exclusive(RIG_BACKUP, RIG.read_bytes(), 0o644)
    require(sha(m.CITY_SOURCE) == m.CITY_NEW and sha(RIG_BACKUP) == m.RIGPERM_OLD, 'inputs readback')
    record('inputs', dict(city_source=identity(m.CITY_SOURCE), rig_backup=identity(RIG_BACKUP)))


def step_cli():
    previous_done('cli')
    require(identity(CLI) == dict(sha256=m.CLI_OLD, mode=0o755, uid=1000, gid=1000, nlink=1, regular=True),
            'live CLI predecessor identity')
    require(sha(STAGED) == m.CLI_NEW, 'staged CLI bytes')
    require(not os.path.lexists(CLI_BACKUP), 'CLI backup already exists')
    write_exclusive(CLI_BACKUP, CLI.read_bytes(), 0o755)
    require(sha(CLI_BACKUP) == m.CLI_OLD, 'CLI backup readback')
    replace_atomic(CLI, STAGED.read_bytes(), 0o755)
    after = identity(CLI)
    require(after == dict(sha256=m.CLI_NEW, mode=0o755, uid=1000, gid=1000, nlink=1, regular=True),
            'installed CLI identity')
    version = run([str(CLI), '--version'], dict(CITY_ENV, DISABLE_AUTOUPDATER='1'))
    require(version['returncode'] == 0 and version['stdout'].strip() == m.NATIVE_VERSION_NEW, 'CLI version')
    record('cli', dict(before_sha256=m.CLI_OLD, after=after, backup=identity(CLI_BACKUP), version=version))


def step_city():
    previous_done('city')
    path = CITY/'city.toml'
    require(identity(path) == dict(sha256=m.CITY_OLD, mode=0o644, uid=1000, gid=1000, nlink=1, regular=True),
            'live city predecessor identity')
    data = Path(m.CITY_SOURCE).read_bytes()
    require(hashlib.sha256(data).hexdigest() == m.CITY_NEW and data == new_city_bytes(), 'city source bytes')
    replace_atomic(path, data, 0o644)
    after = identity(path)
    require(after == dict(sha256=m.CITY_NEW, mode=0o644, uid=1000, gid=1000, nlink=1, regular=True),
            'installed city identity')
    record('city', dict(before_sha256=m.CITY_OLD, after=after))


def checkout_state():
    head = git(TEMPLATE, 'rev-parse', 'HEAD')
    symbolic = git(TEMPLATE, 'symbolic-ref', '-q', 'HEAD')
    status = git(TEMPLATE, 'status', '--porcelain', '--untracked-files=normal')
    return head, symbolic, status


def step_checkout():
    previous_done('checkout')
    head, symbolic, status = checkout_state()
    require(head['stdout'].strip() == OLD_COMMIT and symbolic['returncode'] == 1
            and status['returncode'] == 0 and status['stdout'] == UNTRACKED, 'canonical checkout predecessor')
    exists = git(TEMPLATE, 'cat-file', '-e', m.TEMPLATE_COMMIT + '^{commit}')
    require(exists['returncode'] == 0, 'target commit absent')
    moved = git(TEMPLATE, 'checkout', '--detach', m.TEMPLATE_COMMIT)
    require(moved['returncode'] == 0, 'checkout failed: ' + moved['stderr'])
    head, symbolic, status = checkout_state()
    require(head['stdout'].strip() == m.TEMPLATE_COMMIT and symbolic['returncode'] == 1
            and status['stdout'] == UNTRACKED, 'canonical checkout successor')
    parser = m.CHANGED_INPUTS[0]
    require(sha(parser[0]) == parser[2], 'successor signing worker bytes')
    require(sha(TEMPLATE/'bin/gct-managed-rig-permissions') == RENDERER_SHA, 'successor renderer bytes')
    record('checkout', dict(before=OLD_COMMIT, after=m.TEMPLATE_COMMIT, command=moved, status=status['stdout']))


def step_render():
    previous_done('render')
    require(checkout_state()[0]['stdout'].strip() == m.TEMPLATE_COMMIT, 'canonical checkout not advanced')
    require(sha(RIG) == m.RIGPERM_OLD and sha(RIG_BACKUP) == m.RIGPERM_OLD, 'rig permissions predecessor')
    require(sha(TEMPLATE/'bin/gct-managed-rig-permissions') == RENDERER_SHA, 'renderer bytes')
    result = run(['/usr/bin/python3.12', '-I', '-B', str(TEMPLATE/'bin/gct-managed-rig-permissions'),
                  '--apply', '--json', '--city', str(CITY)], CITY_ENV)
    require(result['returncode'] == 0, 'render failed: ' + result['stderr'])
    report = json.loads(result['stdout'])
    require(report['ok'] is True and report['state'] == 'conformant' and report['changed'] is True
            and report['expected_sha256'] == report['actual_sha256'] == m.RIGPERM_NEW, 'render report')
    after = identity(RIG)
    require(after == dict(sha256=m.RIGPERM_NEW, mode=0o644, uid=1000, gid=1000, nlink=1, regular=True),
            'rendered rig permissions identity')
    record('render', dict(before_sha256=m.RIGPERM_OLD, after=after, command=result, report=report))


def step_authority():
    previous_done('authority')
    auth = Path(m.AUTHORITY)
    admin = TEMPLATE/'.git/worktrees'/auth.name
    require(not os.path.lexists(auth) and not os.path.lexists(admin), 'authority already exists')
    added = git(TEMPLATE, 'worktree', 'add', '--detach', str(auth), m.TEMPLATE_COMMIT)
    require(added['returncode'] == 0, 'worktree add failed: ' + added['stderr'])
    head = git(auth, 'rev-parse', 'HEAD')
    status = git(auth, 'status', '--porcelain', '--untracked-files=normal')
    require(head['stdout'].strip() == m.TEMPLATE_COMMIT and status['returncode'] == 0
            and status['stdout'] == '', 'authority HEAD/clean')
    files = {}
    for relative, digest, mode in m.AUTH_INPUTS:
        files[relative] = identity(auth/relative)
        require(files[relative] == dict(sha256=digest, mode=mode, uid=1000, gid=1000, nlink=1, regular=True),
                'authority file: ' + relative)
    for relative, target in m.AUTH_LINKS:
        require(os.path.islink(auth/relative) and os.readlink(auth/relative) == target, 'authority link')
    for relative in m.AUTH_TREES:
        st = os.lstat(auth/relative)
        require(stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o755, 'authority tree root')
    require(sorted(os.listdir(auth)) == sorted({r.split('/')[0] for r, _, _ in m.AUTH_INPUTS} |
            {r.split('/')[0] for r in m.AUTH_TREES} | {r.split('/')[0] for r, _ in m.AUTH_LINKS}),
            'authority root entries')
    record('authority', dict(command=added, head=m.TEMPLATE_COMMIT, clean=True, files=files))


def rollback():
    require(sha(INSTALLED) == m.OLD_MANIFEST_SHA, 'successor may be installed; rollback refused')
    require(not os.path.lexists(INPUTS/'rollback.json'), 'rollback already consumed')
    actions = []
    if sha(RIG) == m.RIGPERM_NEW:
        require(sha(RIG_BACKUP) == m.RIGPERM_OLD, 'rig backup bytes')
        replace_atomic(RIG, RIG_BACKUP.read_bytes(), 0o644); actions.append('rig-permissions')
    if checkout_state()[0]['stdout'].strip() == m.TEMPLATE_COMMIT:
        moved = git(TEMPLATE, 'checkout', '--detach', OLD_COMMIT)
        require(moved['returncode'] == 0, 'checkout rollback failed'); actions.append('checkout')
    if sha(CITY/'city.toml') == m.CITY_NEW:
        replace_atomic(CITY/'city.toml', CITY_BACKUP.read_bytes(), 0o644); actions.append('city')
    if sha(CLI) == m.CLI_NEW:
        require(sha(CLI_BACKUP) == m.CLI_OLD, 'CLI backup bytes')
        replace_atomic(CLI, CLI_BACKUP.read_bytes(), 0o755); actions.append('cli')
    head, _, status = checkout_state()
    require(sha(RIG) == m.RIGPERM_OLD and sha(CITY/'city.toml') == m.CITY_OLD and sha(CLI) == m.CLI_OLD
            and head['stdout'].strip() == OLD_COMMIT and status['stdout'] == UNTRACKED, 'rollback postcondition')
    write_exclusive(INPUTS/'rollback.json', (json.dumps(dict(actions=actions), sort_keys=True) + '\n').encode(), 0o600)
    print(json.dumps(dict(rollback=actions, ok=True)))


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    require(len(sys.argv) == 2 and sys.argv[1] in STEPS + ('rollback',), 'usage: prereqs.py <step>|rollback')
    os.umask(0o022)
    dict(inputs=step_inputs, cli=step_cli, city=step_city, checkout=step_checkout, render=step_render,
         authority=step_authority, rollback=rollback)[sys.argv[1]]()


if __name__ == '__main__':
    main()
