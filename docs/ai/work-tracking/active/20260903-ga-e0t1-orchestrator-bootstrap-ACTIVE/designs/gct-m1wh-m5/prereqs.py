"""Live M5 prerequisites, one guarded step per invocation (operator decision 2026-09-23).

  python3 -I -B prereqs.py <manifest_candidate.py sha256> <step>
  python3 -I -B prereqs.py <manifest_candidate.py sha256> rollback

Steps run in this order: inputs, cli, city-transition, checkout, registry,
render, city-final, authority.

Every step does the following:
- binds the reviewed candidate bytes;
- proves the quiet host (supervisor identity, empty supervisor scope, no city
  tmux, unchanged suspension record) and its exact predecessor state;
- performs one bounded change and proves the postcondition;
- writes one exclusive record under reports/m5-inputs.

A step never repeats. Every composed city configuration it leaves offers each
model value it references. The transitional city.toml adds the opus-5-5 choice
before anything selects it, and the final city.toml removes opus-5 only after
nothing selects it.

`rollback` restores every changed live file from verified backups and the
canonical checkout. It works only while the installed platform manifest is still
the R9 predecessor and no M5 package root exists.

No lifecycle, timer, worker, signer or Bead action.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tomllib
import types

HERE = Path(__file__).parent
TEMPLATE = Path('/home/loucmane/gas-city-template')
CITY = Path('/home/loucmane/gascity/city')
CLI = Path('/home/loucmane/gascity/bin/claude')
CLI_BACKUP = Path('/home/loucmane/gascity/bin/claude.gct-m1wh-before-2.1.280')
STAGED = Path('/home/loucmane/.local/share/gas-city-staging/gct-er3h/claude-2.1.280')
RIG = CITY/'managed/rig-permissions.toml'
REGISTRY = CITY/'managed/rig-permissions.json'
INSTALLED = CITY/'.gc/platform/install-manifest.json'
SUSPENSION = CITY/'.gc/runtime/suspension-state.json'
SUSPENSION_SHA = '823e4e2115043aa494e1ed0a69cdbb9659bd321651db8469ed13bdcea82077b8'
RUNTIME_SHA = '2585357a808d8f36604d4bf45a39a5363ba87c8d719413ba42d9fd0fac71973f'
OLD_COMMIT = '51440da2d0ff12912ff7d2ec26d239849e3bc342'
RENDERER_SHA = '20dc4146d52250e63f2d782e62a56612ce28506e469a09891de3cb85c215bcd4'
CITY_TRANSITION = '8e148efa7335cc55cb80b651a2ad506ecc8e7a9c535f4573fb6df30171a5efab'
UNTRACKED = '?? deploy/\n?? gas_city_template.egg-info/\n'
GIT_ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/home/loucmane', 'LANG': 'C', 'GIT_CONFIG_NOSYSTEM': '1'}
CITY_ENV = {'PATH': '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/loucmane',
            'LANG': 'C', 'GC_HOME': '/home/loucmane/gascity/home'}
EDITS = {21: ('model = "opus-5"\n', 'model = "opus-5-5"\n'),
         28: ('default = "opus-5"\n', 'default = "opus-5-5"\n'),
         31: ('value = "opus-5"\n', 'value = "opus-5-5"\n'),
         32: ('label = "Claude Opus 5"\n', 'label = "Claude Opus 5.5"\n'),
         33: ('flag_args = ["--model", "claude-opus-5"]\n', 'flag_args = ["--model", "claude-opus-5-5"]\n'),
         236: ('model = "opus-5"\n', 'model = "opus-5-5"\n')}
TRANSITION_AFTER = 34
TRANSITION_BLOCK = ('[[providers.claude.options_schema.choices]]\n', 'value = "opus-5-5"\n',
                    'label = "Claude Opus 5.5"\n', 'flag_args = ["--model", "claude-opus-5-5"]\n', '\n')
# The registry records the installed CLI; the edit moves exactly its digest and version.
REGISTRY_EDITS = (('26d020351e8112f4006790f3cfce43b4c9df0c1bb1d0e542364d64151b81d5ba',
                   '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'),
                  ('"2.1.263 (Claude Code)"', '"2.1.280 (Claude Code)"'))
STEPS = ('inputs', 'cli', 'city-transition', 'checkout', 'registry', 'render', 'city-final', 'authority')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_candidate(expected):
    path = HERE/'manifest_candidate.py'
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'candidate source differs from the reviewed digest')
    module = types.ModuleType('m5_candidate'); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def legacy():
    raw = (HERE/'source_runtime.py').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == RUNTIME_SHA, 'source loader drift')
    r = types.ModuleType('pinned_runtime'); r.__file__ = str(HERE/'source_runtime.py')
    exec(compile(raw, r.__file__, 'exec', dont_inherit=True), r.__dict__)
    graph = r.legacy()
    return graph['observe_recovery'], graph['recovery_state']


def identity(path):
    st = os.lstat(path)
    return dict(sha256=sha(path) if stat.S_ISREG(st.st_mode) else None, mode=stat.S_IMODE(st.st_mode),
                uid=st.st_uid, gid=st.st_gid, nlink=st.st_nlink, regular=stat.S_ISREG(st.st_mode))


def owned(digest, mode):
    return dict(sha256=digest, mode=mode, uid=1000, gid=1000, nlink=1, regular=True)


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


def replace_atomic(path, data, mode, operation):
    tmp = Path(path).parent/('.' + Path(path).name + '.gct-m1wh-m5.' + operation + '.tmp')
    require(not os.path.lexists(tmp), 'leftover temporary file needs inspection: ' + str(tmp))
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


def checkout_state():
    head = git(TEMPLATE, 'rev-parse', 'HEAD')
    symbolic = git(TEMPLATE, 'symbolic-ref', '-q', 'HEAD')
    status = git(TEMPLATE, 'status', '--porcelain', '--untracked-files=normal')
    return head['stdout'].strip(), symbolic['returncode'], status['stdout']


def model_consistency():
    return models((CITY/'city.toml').read_text(), RIG.read_text())


def models(city_text, rig_text):
    """Every model value a claude-family selection names must be offered by the claude picker."""
    city = tomllib.loads(city_text)
    rig = tomllib.loads(rig_text)
    providers = dict(city.get('providers', {}))
    providers.update(rig.get('providers', {}))

    def claude_family(name):
        seen = set()
        while name not in seen:
            seen.add(name)
            if name == 'claude':
                return True
            base = providers.get(name, {}).get('base', '')
            if not base.startswith('provider:'):
                return False
            name = base[len('provider:'):]
        return False

    claude = city['providers']['claude']
    schema = [o for o in claude['options_schema'] if o['key'] == 'model']
    require(len(schema) == 1, 'claude model schema cardinality')
    offered = [c['value'] for c in schema[0]['choices']]
    require(len(offered) == len(set(offered)), 'duplicate model choice')
    selected = {'providers.claude.option_defaults': claude['option_defaults']['model'],
                'providers.claude.options_schema.default': schema[0]['default']}
    for rig_row in city.get('rigs', []):
        for index, override in enumerate(rig_row.get('overrides', [])):
            model = override.get('option_defaults', {}).get('model')
            if model is not None and claude_family(override.get('provider', '')):
                selected['rigs.%s.overrides.%d' % (rig_row['name'], index)] = model
    for index, patch in enumerate(rig.get('patches', {}).get('agent', [])):
        model = patch.get('option_defaults', {}).get('model')
        if model is not None and claude_family(patch.get('provider', '')):
            selected['patches.agent.%d' % index] = model
    require(any(k.startswith('patches.agent.') for k in selected), 'claude-signing patch not found')
    missing = {k: v for k, v in selected.items() if v not in offered}
    require(not missing, 'composed city selects a model it does not offer: ' + json.dumps(missing))
    return dict(offered=offered, selected=selected)


class Context:
    def __init__(self, expected):
        self.m = load_candidate(expected)
        self.expected = expected
        self.inputs = Path(self.m.O + '/reports/m5-inputs')
        require(REGISTRY_EDITS[0] == (self.m.CLI_OLD, self.m.CLI_NEW), 'registry CLI edit binding')
        self.o, self.s = legacy()
        self.o.GC_SHA = self.m.NEW

    def quiet(self):
        host = self.o.host_observation()
        scope = self.s.quiet_scope(host)
        require(sha(SUSPENSION) == SUSPENSION_SHA, 'suspension record drift')
        return dict(host=host, scope=scope, suspension_sha256=SUSPENSION_SHA)

    def begin(self, step):
        require(sha(INSTALLED) == self.m.OLD_MANIFEST_SHA, 'installed platform manifest is not the R9 predecessor')
        require(not os.path.lexists(self.m.ROOT), 'M5 package root already exists')
        require(not os.path.lexists(self.inputs/'rollback.json'), 'rollback consumed; start a new package')
        require(not os.path.lexists(self.inputs/('prereq-' + step + '.json')), 'step already consumed: ' + step)
        for earlier in STEPS[:STEPS.index(step)]:
            require(os.path.lexists(self.inputs/('prereq-' + earlier + '.json')), 'earlier step missing: ' + earlier)
        return self.quiet()

    def finish(self, step, before, value):
        after = self.quiet()
        require(after['host'] == before['host'], 'host identity changed during the step')
        value = dict(value, step=step, bead='ga-0t04', candidate_sha256=self.expected,
                     live_mutation=step != 'inputs', quiet_before=before, quiet_after=after)
        write_exclusive(self.inputs/('prereq-' + step + '.json'),
                        (json.dumps(value, sort_keys=True, indent=1) + '\n').encode(), 0o600)
        print(json.dumps(dict(step=step, ok=True, record=str(self.inputs/('prereq-' + step + '.json')))))

    def city_bytes(self):
        raw = Path(self.m.O + '/reports/r5/i/00').read_bytes()
        require(hashlib.sha256(raw).hexdigest() == self.m.CITY_OLD, 'city backup bytes')
        lines = raw.decode().splitlines(True)
        final = list(lines)
        for number, (before, after) in EDITS.items():
            require(final[number-1] == before, 'city line %d' % number)
            final[number-1] = after
        require(lines[TRANSITION_AFTER-1] == '\n', 'transition anchor')
        transition = ''.join(lines[:TRANSITION_AFTER] + list(TRANSITION_BLOCK) + lines[TRANSITION_AFTER:]).encode()
        final = ''.join(final).encode()
        require(hashlib.sha256(transition).hexdigest() == CITY_TRANSITION
                and hashlib.sha256(final).hexdigest() == self.m.CITY_NEW, 'derived city bytes')
        return raw, transition, final

    def registry_bytes(self, raw):
        require(hashlib.sha256(raw).hexdigest() == self.m.REGISTRY_OLD, 'registry predecessor bytes')
        text = raw.decode()
        for before, after in REGISTRY_EDITS:
            require(text.count(before) == 1, 'registry edit anchor')
            text = text.replace(before, after)
        new = text.encode()
        require(hashlib.sha256(new).hexdigest() == self.m.REGISTRY_NEW, 'derived registry bytes')
        return new


def step_inputs(c):
    before = c.begin('inputs')
    require(not os.path.lexists(c.inputs), 'inputs directory already exists')
    require(sha(RIG) == c.m.RIGPERM_OLD and sha(CITY/'city.toml') == c.m.CITY_OLD
            and sha(REGISTRY) == c.m.REGISTRY_OLD, 'live predecessor bytes')
    city_old, transition, final = c.city_bytes()
    registry_old = REGISTRY.read_bytes()
    registry_new = c.registry_bytes(registry_old)
    rig_old = RIG.read_bytes()
    # Everything is derived and verified before the directory is consumed.
    os.mkdir(c.inputs, 0o700)
    fsync_dir(c.inputs.parent)
    for name, data in (('city.toml', final), ('city.toml.transition', transition),
                       ('rig-permissions.json.new', registry_new), ('rig-permissions.json.before', registry_old),
                       ('rig-permissions.toml.before', rig_old)):
        write_exclusive(c.inputs/name, data, 0o644)
    require(Path(c.m.CITY_SOURCE) == c.inputs/'city.toml' and sha(c.m.CITY_SOURCE) == c.m.CITY_NEW, 'city source')
    c.finish('inputs', before, dict(files={n: identity(c.inputs/n) for n in sorted(os.listdir(c.inputs))}))


def step_cli(c):
    before = c.begin('cli')
    require(identity(CLI) == owned(c.m.CLI_OLD, 0o755), 'live CLI predecessor identity')
    require(sha(STAGED) == c.m.CLI_NEW, 'staged CLI bytes')
    require(not os.path.lexists(CLI_BACKUP), 'CLI backup already exists')
    write_exclusive(CLI_BACKUP, CLI.read_bytes(), 0o755)
    require(sha(CLI_BACKUP) == c.m.CLI_OLD, 'CLI backup readback')
    replace_atomic(CLI, STAGED.read_bytes(), 0o755, 'forward')
    require(identity(CLI) == owned(c.m.CLI_NEW, 0o755), 'installed CLI identity')
    version = run([str(CLI), '--version'], dict(CITY_ENV, DISABLE_AUTOUPDATER='1'))
    require(version['returncode'] == 0 and version['stdout'].strip() == c.m.NATIVE_VERSION_NEW, 'CLI version')
    c.finish('cli', before, dict(after=identity(CLI), backup=identity(CLI_BACKUP), version=version))


def replace_city(c, step, before_sha, source, after_sha):
    before = c.begin(step)
    path = CITY/'city.toml'
    require(identity(path) == owned(before_sha, 0o644), 'live city predecessor identity')
    consistent_before = model_consistency()
    data = Path(source).read_bytes()
    require(hashlib.sha256(data).hexdigest() == after_sha, 'city source bytes')
    replace_atomic(path, data, 0o644, 'forward')
    require(identity(path) == owned(after_sha, 0o644), 'installed city identity')
    c.finish(step, before, dict(before_sha256=before_sha, after=identity(path),
                                models_before=consistent_before, models_after=model_consistency()))


def step_city_transition(c):
    replace_city(c, 'city-transition', c.m.CITY_OLD, c.inputs/'city.toml.transition', CITY_TRANSITION)


def step_checkout(c):
    before = c.begin('checkout')
    head, symbolic, status = checkout_state()
    require(head == OLD_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout predecessor')
    require(git(TEMPLATE, 'cat-file', '-e', c.m.TEMPLATE_COMMIT + '^{commit}')['returncode'] == 0,
            'target commit absent')
    moved = git(TEMPLATE, 'checkout', '--detach', c.m.TEMPLATE_COMMIT)
    require(moved['returncode'] == 0, 'checkout failed: ' + moved['stderr'])
    head, symbolic, status = checkout_state()
    require(head == c.m.TEMPLATE_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout successor')
    require(sha(c.m.CHANGED_INPUTS[0][0]) == c.m.CHANGED_INPUTS[0][2], 'successor signing worker bytes')
    require(sha(TEMPLATE/'bin/gct-managed-rig-permissions') == RENDERER_SHA, 'successor renderer bytes')
    for path, digest in c.m.RETAINED_TEMPLATE_PINS.items():
        require(sha(path) == digest, 'retained Template bytes: ' + path)
    c.finish('checkout', before, dict(before_commit=OLD_COMMIT, after_commit=c.m.TEMPLATE_COMMIT,
                                      command=moved, status=status))


def step_registry(c):
    before = c.begin('registry')
    require(identity(REGISTRY) == owned(c.m.REGISTRY_OLD, 0o644), 'live registry predecessor identity')
    data = (c.inputs/'rig-permissions.json.new').read_bytes()
    require(hashlib.sha256(data).hexdigest() == c.m.REGISTRY_NEW, 'registry source bytes')
    replace_atomic(REGISTRY, data, 0o644, 'forward')
    require(identity(REGISTRY) == owned(c.m.REGISTRY_NEW, 0o644), 'installed registry identity')
    c.finish('registry', before, dict(before_sha256=c.m.REGISTRY_OLD, after=identity(REGISTRY)))


def step_render(c):
    before = c.begin('render')
    require(checkout_state()[0] == c.m.TEMPLATE_COMMIT, 'canonical checkout not advanced')
    require(identity(RIG) == owned(c.m.RIGPERM_OLD, 0o644) and sha(REGISTRY) == c.m.REGISTRY_NEW,
            'render predecessor')
    require(sha(TEMPLATE/'bin/gct-managed-rig-permissions') == RENDERER_SHA, 'renderer bytes')
    argv = ['/usr/bin/python3.12', '-I', '-B', str(TEMPLATE/'bin/gct-managed-rig-permissions'), '--json',
            '--city', str(CITY)]
    checked = run(argv[:4] + ['--check'] + argv[4:], CITY_ENV)
    report = json.loads(checked['stdout'])
    require(checked['returncode'] == 4 and report['ok'] is False and report['state'] == 'drift'
            and report['expected_sha256'] == c.m.RIGPERM_NEW and report['actual_sha256'] == c.m.RIGPERM_OLD,
            'render check does not predict the reviewed bytes; nothing written')
    applied = run(argv[:4] + ['--apply'] + argv[4:], CITY_ENV)
    require(applied['returncode'] == 0, 'render failed: ' + applied['stderr'])
    report = json.loads(applied['stdout'])
    require(report['ok'] is True and report['state'] == 'conformant' and report['changed'] is True
            and report['expected_sha256'] == report['actual_sha256'] == c.m.RIGPERM_NEW, 'render report')
    require(identity(RIG) == owned(c.m.RIGPERM_NEW, 0o644), 'rendered rig permissions identity')
    c.finish('render', before, dict(check=checked, apply=applied, after=identity(RIG), models=model_consistency()))


def step_city_final(c):
    replace_city(c, 'city-final', CITY_TRANSITION, c.m.CITY_SOURCE, c.m.CITY_NEW)


def step_authority(c):
    before = c.begin('authority')
    auth = Path(c.m.AUTHORITY)
    admin = TEMPLATE/'.git/worktrees'/auth.name
    require(not os.path.lexists(auth) and not os.path.lexists(admin), 'authority already exists')
    added = git(TEMPLATE, 'worktree', 'add', '--detach', str(auth), c.m.TEMPLATE_COMMIT)
    require(added['returncode'] == 0, 'worktree add failed: ' + added['stderr'])
    head = git(auth, 'rev-parse', 'HEAD')
    status = git(auth, 'status', '--porcelain', '--untracked-files=normal')
    require(head['stdout'].strip() == c.m.TEMPLATE_COMMIT and status['returncode'] == 0
            and status['stdout'] == '', 'authority HEAD/clean')
    files = {}
    for relative, digest, mode in c.m.AUTH_INPUTS:
        files[relative] = identity(auth/relative)
        require(files[relative] == owned(digest, mode), 'authority file: ' + relative)
    for relative, target in c.m.AUTH_LINKS:
        require(os.path.islink(auth/relative) and os.readlink(auth/relative) == target, 'authority link')
    for relative in c.m.AUTH_TREES:
        st = os.lstat(auth/relative)
        require(stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o755, 'authority tree root')
    require(sorted(os.listdir(auth)) == sorted({r.split('/')[0] for r, _, _ in c.m.AUTH_INPUTS} |
            {r.split('/')[0] for r in c.m.AUTH_TREES} | {r.split('/')[0] for r, _ in c.m.AUTH_LINKS}),
            'authority root entries')
    c.finish('authority', before, dict(command=added, head=c.m.TEMPLATE_COMMIT, clean=True, files=files))


def rollback(c):
    require(sha(INSTALLED) == c.m.OLD_MANIFEST_SHA, 'successor may be installed; rollback refused')
    require(not os.path.lexists(c.m.ROOT), 'M5 package root exists; use the executor recovery, not rollback')
    require(os.path.isdir(c.inputs) and not os.path.lexists(c.inputs/'rollback.json'), 'rollback state')
    actions = []
    restores = ((CITY/'city.toml', Path(c.m.O + '/reports/r5/i/00'), c.m.CITY_OLD, 0o644),
                (RIG, c.inputs/'rig-permissions.toml.before', c.m.RIGPERM_OLD, 0o644),
                (REGISTRY, c.inputs/'rig-permissions.json.before', c.m.REGISTRY_OLD, 0o644),
                (CLI, CLI_BACKUP, c.m.CLI_OLD, 0o755))
    for live, backup, digest, mode in restores:
        if sha(live) != digest:
            require(sha(backup) == digest, 'backup bytes differ: ' + str(backup))
            replace_atomic(live, backup.read_bytes(), mode, 'rollback')
            actions.append(str(live))
    if checkout_state()[0] != OLD_COMMIT:
        moved = git(TEMPLATE, 'checkout', '--detach', OLD_COMMIT)
        require(moved['returncode'] == 0, 'checkout rollback failed: ' + moved['stderr'])
        actions.append('checkout')
    head, _, status = checkout_state()
    require(all(identity(live) == owned(digest, mode) for live, _, digest, mode in restores)
            and head == OLD_COMMIT and status == UNTRACKED, 'rollback postcondition')
    write_exclusive(c.inputs/'rollback.json', (json.dumps(dict(actions=actions, candidate_sha256=c.expected),
                    sort_keys=True) + '\n').encode(), 0o600)
    print(json.dumps(dict(rollback=actions, ok=True)))


ACTIONS = {'inputs': step_inputs, 'cli': step_cli, 'city-transition': step_city_transition,
           'checkout': step_checkout, 'registry': step_registry, 'render': step_render,
           'city-final': step_city_final, 'authority': step_authority, 'rollback': rollback}


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    args = sys.argv[1:]
    require(len(args) == 2 and len(args[0]) == 64 and args[1] in ACTIONS,
            'usage: prereqs.py <candidate sha256> <step>|rollback')
    os.umask(0o022)
    ACTIONS[args[1]](Context(args[0]))


if __name__ == '__main__':
    main()
