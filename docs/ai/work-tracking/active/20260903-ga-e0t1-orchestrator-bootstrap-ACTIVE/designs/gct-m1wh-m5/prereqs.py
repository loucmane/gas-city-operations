"""Live M5 prerequisites, one guarded step per invocation (operator decision 2026-09-23).

  python3 -I -B prereqs.py <manifest_candidate.py sha256> <step>
  python3 -I -B prereqs.py <manifest_candidate.py sha256> resume <step>
  python3 -I -B prereqs.py <manifest_candidate.py sha256> rollback

Steps run in this order: inputs, cli, city-transition, checkout, registry,
render, city-final, authority.

Every step:
1. binds the reviewed candidate bytes;
2. waits for a natural quiet slot of the Obsidian reconciler timer, never
   starting, stopping or signalling it;
3. proves the quiet host (supervisor identity, empty supervisor scope, no city
   tmux, unchanged suspension record) and its exact predecessor state;
4. writes an intent record;
5. performs one bounded change;
6. proves the exact postcondition and writes one exclusive record under
   reports/m5-inputs.

If a step is interrupted after its intent, it can only `resume`. A resume
proves the same exact postcondition and a quiet host before it writes the
missing record. It never repeats the mutation.

Every composed city configuration the forward order leaves offers every model
that a claude-family selection names. The transitional city.toml adds
opus-5-5 before anything selects it, and the final city.toml removes opus-5
only after nothing selects it.

`rollback` restores every changed live file from digest-verified bytes. It
goes through the transitional city first, so it never composes the inverse
unordered state, and it returns the canonical checkout.
- It runs only while the installed platform manifest is still the R9
  predecessor, and only while no M5 executor window may hold the reconciler
  timer paused or may have launched an apply.
- Its quiet observation is recorded but never required.
- Each attempt writes through a fresh temporary name, so a crash inside a
  restore never blocks the next attempt.

No lifecycle, timer, worker, signer or Bead action.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
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
RECONCILER = 'aegis-obsidian-reconcile.service'
RECONCILER_TIMER_OBJECT = '/org/freedesktop/systemd1/unit/aegis_2dobsidian_2dreconcile_2etimer'
SLOT_US = 40_000_000
SLOT_DEADLINE_S = 180
GIT_ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/home/loucmane', 'LANG': 'C', 'GIT_CONFIG_NOSYSTEM': '1'}
CITY_ENV = {'PATH': '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/loucmane',
            'LANG': 'C', 'GC_HOME': '/home/loucmane/gascity/home'}
# systemctl --user and busctl --user need the user bus, exactly as the reviewed legacy observe_recovery.ENV sets it.
BUS_ENV = dict(CITY_ENV, USER='loucmane', LOGNAME='loucmane', XDG_RUNTIME_DIR='/run/user/1000',
               DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
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


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def load_candidate(expected):
    path = HERE/'manifest_candidate.py'
    raw = path.read_bytes()
    require(digest(raw) == expected, 'candidate source differs from the reviewed digest')
    module = types.ModuleType('m5_candidate'); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def legacy():
    raw = (HERE/'source_runtime.py').read_bytes()
    require(digest(raw) == RUNTIME_SHA, 'source loader drift')
    r = types.ModuleType('pinned_runtime'); r.__file__ = str(HERE/'source_runtime.py')
    exec(compile(raw, r.__file__, 'exec', dont_inherit=True), r.__dict__)
    graph = r.legacy()
    return graph['observe_recovery'], graph['recovery_state']


def identity(path):
    st = os.lstat(path)
    return dict(sha256=sha(path) if stat.S_ISREG(st.st_mode) else None, mode=stat.S_IMODE(st.st_mode),
                uid=st.st_uid, gid=st.st_gid, nlink=st.st_nlink, regular=stat.S_ISREG(st.st_mode))


def owned(expected, mode):
    return dict(sha256=expected, mode=mode, uid=1000, gid=1000, nlink=1, regular=True)


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


def temporary(path, operation):
    return Path(path).parent/('.' + Path(path).name + '.gct-m1wh-m5.' + operation + '.tmp')


def rollback_temporary(path):
    for attempt in range(1, 10):
        tmp = temporary(path, 'rollback.%d' % attempt)
        if not os.path.lexists(tmp):
            return tmp
    raise RuntimeError('nine rollback attempts left temporaries; inspect ' + str(path))


def replace_atomic(path, data, mode, operation):
    tmp = rollback_temporary(path) if operation == 'rollback' else temporary(path, operation)
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


def blob_digest(commit, relative):
    shown = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', str(TEMPLATE), 'cat-file', 'blob',
                            commit + ':' + relative], env=GIT_ENV, cwd='/', stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=60, check=False)
    require(shown.returncode == 0, 'target blob unreadable: ' + relative)
    return digest(shown.stdout)


def checkout_state():
    head = git(TEMPLATE, 'rev-parse', 'HEAD')
    symbolic = git(TEMPLATE, 'symbolic-ref', '-q', 'HEAD')
    status = git(TEMPLATE, 'status', '--porcelain', '--untracked-files=normal')
    return head['stdout'].strip(), symbolic['returncode'], status['stdout']


def reconciler_state():
    shown = run(['/usr/bin/systemctl', '--user', 'show', RECONCILER, '-p', 'ActiveState',
                 '-p', 'ExecMainStartTimestampMonotonic'], BUS_ENV)
    fields = dict(line.split('=', 1) for line in shown['stdout'].splitlines() if '=' in line)
    timer = run(['/usr/bin/systemctl', '--user', 'show', RECONCILER.replace('.service', '.timer'),
                 '-p', 'ActiveState'], BUS_ENV)
    elapse = run(['/usr/bin/busctl', '--user', 'get-property', 'org.freedesktop.systemd1', RECONCILER_TIMER_OBJECT,
                  'org.freedesktop.systemd1.Timer', 'NextElapseUSecMonotonic'], BUS_ENV)
    parts = elapse['stdout'].split()
    require(shown['returncode'] == timer['returncode'] == elapse['returncode'] == 0
            and len(parts) == 2 and parts[0] == 't' and parts[1].isdigit(), 'reconciler observation')
    return dict(active=fields.get('ActiveState'), started_us=int(fields.get('ExecMainStartTimestampMonotonic') or 0),
                timer=timer['stdout'].strip().split('=', 1)[-1], next_us=int(parts[1]))


def quiet_slot(clock=time.monotonic_ns, sleep=time.sleep, observe=None):
    """Wait, by natural drain only, until the reconciler is idle with SLOT_US before its next run."""
    observe = observe or reconciler_state
    deadline = clock() + SLOT_DEADLINE_S * 1_000_000_000
    while True:
        state = observe()
        now_us = clock() // 1000
        idle = state['active'] not in ('activating', 'active', 'deactivating', 'reloading')
        unscheduled = state['timer'] != 'active' or state['next_us'] == 0
        if idle and (unscheduled or state['next_us'] - now_us >= SLOT_US):
            return dict(state, now_us=now_us)
        require(clock() < deadline, 'no natural reconciler quiet slot within the bound')
        sleep(0.5)


def fragment_texts():
    return {str(p): p.read_text() for p in sorted((CITY/'agents').glob('*/agent.toml'))}


def model_consistency(city_text=None, rig_text=None):
    return models((CITY/'city.toml').read_text() if city_text is None else city_text,
                  RIG.read_text() if rig_text is None else rig_text, fragment_texts())


def models(city_text, rig_text, agent_texts=None):
    """Every model value a claude-family selection names must be offered by the claude picker.

    Scope: providers.claude defaults, city rig overrides, [[patches.agent]] in
    city.toml and in the rig fragment, and agent.toml option_defaults. A
    selection without a provider inherits workspace.provider. The two other
    included fragments select no model. Pack-imported agent defaults are out of
    scope; the live packs set no model.
    """
    city = tomllib.loads(city_text)
    rig = tomllib.loads(rig_text)
    providers = dict(city.get('providers', {}))
    providers.update(rig.get('providers', {}))
    default_provider = city.get('workspace', {}).get('provider', '')

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
            if model is not None and claude_family(override.get('provider', default_provider)):
                selected['rigs.%s.overrides.%d' % (rig_row['name'], index)] = model
    for origin, document in (('city', city), ('fragment', rig)):
        for index, patch in enumerate(document.get('patches', {}).get('agent', [])):
            model = patch.get('option_defaults', {}).get('model')
            if model is not None and claude_family(patch.get('provider', default_provider)):
                selected['%s.patches.agent.%d' % (origin, index)] = model
    for path, text in sorted((agent_texts or {}).items()):
        agent = tomllib.loads(text)
        model = agent.get('option_defaults', {}).get('model')
        if model is not None and claude_family(agent.get('provider', default_provider)):
            selected[path] = model
    require(any(k.startswith('fragment.patches.agent.') for k in selected), 'claude-signing patch not found')
    missing = {k: v for k, v in selected.items() if v not in offered}
    require(not missing, 'composed city selects a model it does not offer: ' + json.dumps(missing))
    return dict(offered=offered, selected=selected)


class Context:
    def __init__(self, expected):
        self.m = load_candidate(expected)
        require(REGISTRY_EDITS[0] == (self.m.CLI_OLD, self.m.CLI_NEW), 'registry CLI edit binding')
        self.expected = expected
        self.inputs = Path(self.m.O + '/reports/m5-inputs')
        self.o, self.s = legacy()
        self.o.GC_SHA = self.m.NEW

    def slot(self):
        return quiet_slot()

    def quiet(self):
        slot = self.slot()
        host = self.o.host_observation()
        scope = self.s.quiet_scope(host)
        require(sha(SUSPENSION) == SUSPENSION_SHA, 'suspension record drift')
        return dict(host=host, scope=scope, suspension_sha256=SUSPENSION_SHA, reconciler=slot)

    def executor_closed(self):
        """False while an M5 executor window may hold the timer paused or may have launched an apply."""
        root = Path(self.m.ROOT)
        if not os.path.lexists(root):
            return True
        q = root/'q'
        if os.path.lexists(q/'commit-consumed.json'):
            return False
        if os.path.lexists(q/'restored.json'):
            return True
        # prepare can refuse before its pause intent; then the timer was never touched.
        return not os.path.lexists(q/'preparation-pause-intent.json')

    def record_path(self, step, suffix=''):
        return self.inputs/('prereq-' + step + suffix + '.json')

    def common(self, step):
        require(sha(INSTALLED) == self.m.OLD_MANIFEST_SHA, 'installed platform manifest is not the R9 predecessor')
        require(not os.path.lexists(self.m.ROOT), 'M5 package root already exists')
        require(not os.path.lexists(self.inputs/'rollback.json'), 'rollback consumed; start a new package')
        require(not os.path.lexists(self.record_path(step)), 'step already consumed: ' + step)
        for earlier in STEPS[:STEPS.index(step)]:
            require(os.path.lexists(self.record_path(earlier)), 'earlier step missing: ' + earlier)

    def begin(self, step):
        self.common(step)
        require(not os.path.lexists(self.record_path(step, '.intent')),
                'step interrupted after its intent; use resume ' + step)
        return self.quiet()

    def intent(self, step, before):
        write_exclusive(self.record_path(step, '.intent'), (json.dumps(dict(
            step=step, candidate_sha256=self.expected, quiet_before=before), sort_keys=True) + '\n').encode(), 0o600)

    def finish(self, step, before, value, resumed=False):
        after = self.quiet()
        require(after['host'] == before['host'], 'host identity changed during the step')
        value = dict(value, step=step, bead='ga-0t04', candidate_sha256=self.expected, resumed=resumed,
                     live_mutation=step != 'inputs', quiet_before=before, quiet_after=after)
        write_exclusive(self.record_path(step), (json.dumps(value, sort_keys=True, indent=1) + '\n').encode(), 0o600)
        print(json.dumps(dict(step=step, ok=True, resumed=resumed, record=str(self.record_path(step)))))

    def city_bytes(self):
        raw = Path(self.m.O + '/reports/r5/i/00').read_bytes()
        require(digest(raw) == self.m.CITY_OLD, 'city backup bytes')
        lines = raw.decode().splitlines(True)
        final = list(lines)
        for number, (before, after) in EDITS.items():
            require(final[number-1] == before, 'city line %d' % number)
            final[number-1] = after
        require(lines[TRANSITION_AFTER-1] == '\n', 'transition anchor')
        transition = ''.join(lines[:TRANSITION_AFTER] + list(TRANSITION_BLOCK) + lines[TRANSITION_AFTER:]).encode()
        final = ''.join(final).encode()
        require(digest(transition) == CITY_TRANSITION and digest(final) == self.m.CITY_NEW, 'derived city bytes')
        return raw, transition, final

    def registry_bytes(self, raw):
        require(digest(raw) == self.m.REGISTRY_OLD, 'registry predecessor bytes')
        text = raw.decode()
        for before, after in REGISTRY_EDITS:
            require(text.count(before) == 1, 'registry edit anchor')
            text = text.replace(before, after)
        new = text.encode()
        require(digest(new) == self.m.REGISTRY_NEW, 'derived registry bytes')
        return new


def post_inputs(c):
    expected = {'city.toml': c.m.CITY_NEW, 'city.toml.transition': CITY_TRANSITION,
                'rig-permissions.json.new': c.m.REGISTRY_NEW, 'rig-permissions.json.before': c.m.REGISTRY_OLD,
                'rig-permissions.toml.before': c.m.RIGPERM_OLD}
    files = {}
    for name, value in expected.items():
        files[name] = identity(c.inputs/name)
        require(files[name] == owned(value, 0o644), 'inputs file: ' + name)
    require(Path(c.m.CITY_SOURCE) == c.inputs/'city.toml', 'city source binding')
    return dict(files=files)


def post_cli(c):
    require(identity(CLI) == owned(c.m.CLI_NEW, 0o755), 'installed CLI identity')
    require(identity(CLI_BACKUP) == owned(c.m.CLI_OLD, 0o755), 'CLI backup identity')
    version = run([str(CLI), '--version'], dict(CITY_ENV, DISABLE_AUTOUPDATER='1'))
    require(version['returncode'] == 0 and version['stdout'].strip() == c.m.NATIVE_VERSION_NEW, 'CLI version')
    return dict(after=identity(CLI), backup=identity(CLI_BACKUP), version=version)


def post_city(c, expected):
    require(identity(CITY/'city.toml') == owned(expected, 0o644), 'installed city identity')
    return dict(after=identity(CITY/'city.toml'), models=model_consistency())


def post_checkout(c):
    head, symbolic, status = checkout_state()
    require(head == c.m.TEMPLATE_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout successor')
    require(sha(c.m.CHANGED_INPUTS[0][0]) == c.m.CHANGED_INPUTS[0][2], 'successor signing worker bytes')
    require(sha(TEMPLATE/'bin/gct-managed-rig-permissions') == RENDERER_SHA, 'successor renderer bytes')
    for path, value in c.m.RETAINED_TEMPLATE_PINS.items():
        require(sha(path) == value, 'retained Template bytes: ' + path)
    return dict(after_commit=head, status=status)


def post_registry(c):
    require(identity(REGISTRY) == owned(c.m.REGISTRY_NEW, 0o644), 'installed registry identity')
    return dict(after=identity(REGISTRY))


def post_render(c):
    require(identity(RIG) == owned(c.m.RIGPERM_NEW, 0o644), 'rendered rig permissions identity')
    return dict(after=identity(RIG), models=model_consistency())


def post_authority(c):
    auth = Path(c.m.AUTHORITY)
    head = git(auth, 'rev-parse', 'HEAD')
    status = git(auth, 'status', '--porcelain', '--ignored', '--untracked-files=all')
    require(head['stdout'].strip() == c.m.TEMPLATE_COMMIT and status['returncode'] == 0
            and status['stdout'] == '', 'authority HEAD/clean, no ignored or untracked file')
    files = {}
    for relative, value, mode in c.m.AUTH_INPUTS:
        files[relative] = identity(auth/relative)
        require(files[relative] == owned(value, mode), 'authority file: ' + relative)
    for relative, target in c.m.AUTH_LINKS:
        require(os.path.islink(auth/relative) and os.readlink(auth/relative) == target, 'authority link')
    for relative in c.m.AUTH_TREES:
        st = os.lstat(auth/relative)
        require(stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o755, 'authority tree root')
    require(sorted(os.listdir(auth)) == sorted({r.split('/')[0] for r, _, _ in c.m.AUTH_INPUTS} |
            {r.split('/')[0] for r in c.m.AUTH_TREES} | {r.split('/')[0] for r, _ in c.m.AUTH_LINKS}),
            'authority root entries')
    return dict(head=c.m.TEMPLATE_COMMIT, clean=True, files=files)


POST = {'inputs': post_inputs, 'cli': post_cli,
        'city-transition': lambda c: post_city(c, CITY_TRANSITION), 'checkout': post_checkout,
        'registry': post_registry, 'render': post_render,
        'city-final': lambda c: post_city(c, c.m.CITY_NEW), 'authority': post_authority}


def no_forward_temporary(*paths):
    for path in paths:
        require(not os.path.lexists(temporary(path, 'forward')),
                'leftover temporary file needs inspection: ' + str(temporary(path, 'forward')))


def step_inputs(c):
    c.common('inputs')
    # An empty directory is what an interruption between mkdir and the intent leaves; nothing else is accepted.
    require(not os.path.lexists(c.inputs) or (c.inputs.is_dir() and not any(c.inputs.iterdir())),
            'inputs directory already exists')
    registry_old, rig_old = REGISTRY.read_bytes(), RIG.read_bytes()
    require(digest(rig_old) == c.m.RIGPERM_OLD and sha(CITY/'city.toml') == c.m.CITY_OLD
            and digest(registry_old) == c.m.REGISTRY_OLD, 'live predecessor bytes')
    _, transition, final = c.city_bytes()
    registry_new = c.registry_bytes(registry_old)
    before = c.quiet()
    # Every byte is derived and verified before the directory is consumed.
    if not os.path.lexists(c.inputs):
        os.mkdir(c.inputs, 0o700)
        fsync_dir(c.inputs.parent)
    c.intent('inputs', before)
    for name, data in (('city.toml', final), ('city.toml.transition', transition),
                       ('rig-permissions.json.new', registry_new), ('rig-permissions.json.before', registry_old),
                       ('rig-permissions.toml.before', rig_old)):
        write_exclusive(c.inputs/name, data, 0o644)
    c.finish('inputs', before, post_inputs(c))


def step_cli(c):
    before = c.begin('cli')
    require(identity(CLI) == owned(c.m.CLI_OLD, 0o755), 'live CLI predecessor identity')
    staged = STAGED.read_bytes()
    require(digest(staged) == c.m.CLI_NEW, 'staged CLI bytes')
    require(not os.path.lexists(CLI_BACKUP), 'CLI backup already exists')
    no_forward_temporary(CLI)
    current = CLI.read_bytes()
    require(digest(current) == c.m.CLI_OLD, 'live CLI predecessor bytes')
    c.intent('cli', before)
    write_exclusive(CLI_BACKUP, current, 0o755)
    replace_atomic(CLI, staged, 0o755, 'forward')
    c.finish('cli', before, post_cli(c))


def replace_city(c, step, before_sha, source, after_sha, fragment_sha, registry_sha):
    before = c.begin(step)
    path = CITY/'city.toml'
    require(identity(path) == owned(before_sha, 0o644), 'live city predecessor identity')
    require(sha(RIG) == fragment_sha and sha(REGISTRY) == registry_sha, 'city step fragment/registry predecessor')
    data = Path(source).read_bytes()
    require(digest(data) == after_sha, 'city source bytes')
    models_before = model_consistency()
    models_candidate = model_consistency(city_text=data.decode())
    no_forward_temporary(path)
    c.intent(step, before)
    replace_atomic(path, data, 0o644, 'forward')
    c.finish(step, before, dict(post_city(c, after_sha), before_sha256=before_sha, models_before=models_before,
                                models_candidate=models_candidate))


def step_city_transition(c):
    replace_city(c, 'city-transition', c.m.CITY_OLD, c.inputs/'city.toml.transition', CITY_TRANSITION,
                 c.m.RIGPERM_OLD, c.m.REGISTRY_OLD)


def step_checkout(c):
    before = c.begin('checkout')
    head, symbolic, status = checkout_state()
    require(head == OLD_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout predecessor')
    require(git(TEMPLATE, 'cat-file', '-e', c.m.TEMPLATE_COMMIT + '^{commit}')['returncode'] == 0,
            'target commit absent')
    # Prove every byte the step depends on from Git objects before the checkout moves.
    prefix = str(TEMPLATE) + '/'
    require(blob_digest(c.m.TEMPLATE_COMMIT, 'bin/gct-managed-rig-permissions') == RENDERER_SHA,
            'target renderer blob')
    parser = c.m.CHANGED_INPUTS[0]
    require(blob_digest(c.m.TEMPLATE_COMMIT, parser[0][len(prefix):]) == parser[2], 'target signing worker blob')
    for path, value in c.m.RETAINED_TEMPLATE_PINS.items():
        require(blob_digest(c.m.TEMPLATE_COMMIT, path[len(prefix):]) == value, 'target retained blob: ' + path)
    c.intent('checkout', before)
    moved = git(TEMPLATE, 'checkout', '--detach', c.m.TEMPLATE_COMMIT)
    require(moved['returncode'] == 0, 'checkout failed: ' + moved['stderr'])
    c.finish('checkout', before, dict(post_checkout(c), before_commit=OLD_COMMIT, command=moved))


def step_registry(c):
    before = c.begin('registry')
    require(identity(REGISTRY) == owned(c.m.REGISTRY_OLD, 0o644), 'live registry predecessor identity')
    data = (c.inputs/'rig-permissions.json.new').read_bytes()
    require(digest(data) == c.m.REGISTRY_NEW, 'registry source bytes')
    no_forward_temporary(REGISTRY)
    c.intent('registry', before)
    replace_atomic(REGISTRY, data, 0o644, 'forward')
    c.finish('registry', before, dict(post_registry(c), before_sha256=c.m.REGISTRY_OLD))


def step_render(c):
    before = c.begin('render')
    require(checkout_state()[0] == c.m.TEMPLATE_COMMIT, 'canonical checkout not advanced')
    require(identity(RIG) == owned(c.m.RIGPERM_OLD, 0o644) and sha(REGISTRY) == c.m.REGISTRY_NEW
            and sha(CITY/'city.toml') == CITY_TRANSITION, 'render predecessor')
    require(sha(TEMPLATE/'bin/gct-managed-rig-permissions') == RENDERER_SHA, 'renderer bytes')
    argv = ['/usr/bin/python3.12', '-I', '-B', str(TEMPLATE/'bin/gct-managed-rig-permissions')]
    tail = ['--json', '--city', str(CITY)]
    checked = run(argv + ['--check'] + tail, CITY_ENV)
    require(checked['returncode'] == 4, 'render check exit status; nothing written: ' + checked['stderr'])
    report = json.loads(checked['stdout'])
    require(report['ok'] is False and report['state'] == 'drift' and report['expected_sha256'] == c.m.RIGPERM_NEW
            and report['actual_sha256'] == c.m.RIGPERM_OLD,
            'render check does not predict the reviewed bytes; nothing written')
    c.intent('render', before)
    applied = run(argv + ['--apply'] + tail, CITY_ENV)
    require(applied['returncode'] == 0, 'render failed: ' + applied['stderr'])
    report = json.loads(applied['stdout'])
    require(report['ok'] is True and report['state'] == 'conformant' and report['changed'] is True
            and report['expected_sha256'] == report['actual_sha256'] == c.m.RIGPERM_NEW, 'render report')
    c.finish('render', before, dict(post_render(c), check=checked, apply=applied))


def step_city_final(c):
    replace_city(c, 'city-final', CITY_TRANSITION, c.m.CITY_SOURCE, c.m.CITY_NEW, c.m.RIGPERM_NEW,
                 c.m.REGISTRY_NEW)


def step_authority(c):
    before = c.begin('authority')
    auth = Path(c.m.AUTHORITY)
    admin = TEMPLATE/'.git/worktrees'/auth.name
    require(not os.path.lexists(auth) and not os.path.lexists(admin), 'authority already exists')
    c.intent('authority', before)
    added = git(TEMPLATE, 'worktree', 'add', '--detach', str(auth), c.m.TEMPLATE_COMMIT)
    require(added['returncode'] == 0, 'worktree add failed: ' + added['stderr'])
    c.finish('authority', before, dict(post_authority(c), command=added))


def resume(c, step):
    """Record an interrupted step only when its exact reviewed postcondition already holds."""
    require(step in STEPS, 'unknown step')
    c.common(step)
    intent = c.record_path(step, '.intent')
    require(os.path.lexists(intent), 'no interrupted intent for ' + step)
    recorded = json.loads(intent.read_text())
    require(recorded.get('step') == step and recorded.get('candidate_sha256') == c.expected,
            'intent belongs to another step or candidate')
    before = recorded['quiet_before']
    verified = POST[step](c)
    c.finish(step, before, dict(verified, resumed_from_intent=str(intent)), resumed=True)


def leftovers():
    found = []
    for directory in (CITY, CITY/'managed', CLI.parent):
        found += sorted(str(p) for p in directory.glob('.*.gct-m1wh-m5.*.tmp'))
    found += sorted(str(p) for p in (CITY/'managed').glob('.rig-permissions.toml.tmp.*'))
    found += sorted(str(p) for p in CITY.parent.glob('.' + CITY.name + '.gct-validate.*'))
    if os.path.lexists(CLI_BACKUP):
        found.append(str(CLI_BACKUP))
    return found


def rollback(c):
    require(sha(INSTALLED) == c.m.OLD_MANIFEST_SHA, 'successor may be installed; rollback refused')
    require(c.executor_closed(), 'M5 executor window is open; restore it through the executor first')
    require(os.path.isdir(c.inputs) and not os.path.lexists(c.inputs/'rollback.json'), 'rollback state')
    try:
        observed = c.quiet()
    except Exception as exc:  # restoration must remain possible; record why the host was not quiet
        observed = dict(error=type(exc).__name__, reason=str(exc))
    backups = {'city': Path(c.m.O + '/reports/r5/i/00'), 'transition': c.inputs/'city.toml.transition',
               'rig': c.inputs/'rig-permissions.toml.before', 'registry': c.inputs/'rig-permissions.json.before',
               'cli': CLI_BACKUP}
    wanted = {'city': c.m.CITY_OLD, 'transition': CITY_TRANSITION, 'rig': c.m.RIGPERM_OLD,
              'registry': c.m.REGISTRY_OLD, 'cli': c.m.CLI_OLD}
    needed = {'city': sha(CITY/'city.toml') != c.m.CITY_OLD, 'transition': sha(CITY/'city.toml') == c.m.CITY_NEW,
              'rig': sha(RIG) != c.m.RIGPERM_OLD, 'registry': sha(REGISTRY) != c.m.REGISTRY_OLD,
              'cli': sha(CLI) != c.m.CLI_OLD}
    for name, path in backups.items():
        if needed[name]:
            require(os.path.lexists(path) and sha(path) == wanted[name], 'backup bytes differ: ' + str(path))
    actions, models_seen = [], []

    def restore(live, source, mode, label, expected):
        data = Path(source).read_bytes()
        require(digest(data) == expected, 'backup bytes differ: ' + str(source))
        replace_atomic(live, data, mode, 'rollback')
        actions.append(label)
        try:
            models_seen.append(dict(after=label, models=model_consistency()))
        except RuntimeError as exc:
            models_seen.append(dict(after=label, refused=str(exc)))

    # Reverse order through consistent states: transition city, fragment, registry, predecessor city.
    if needed['transition']:
        restore(CITY/'city.toml', backups['transition'], 0o644, 'city-transition', CITY_TRANSITION)
    if needed['rig']:
        restore(RIG, backups['rig'], 0o644, 'rig-permissions.toml', c.m.RIGPERM_OLD)
    if needed['registry']:
        restore(REGISTRY, backups['registry'], 0o644, 'rig-permissions.json', c.m.REGISTRY_OLD)
    if sha(CITY/'city.toml') != c.m.CITY_OLD:
        restore(CITY/'city.toml', backups['city'], 0o644, 'city.toml', c.m.CITY_OLD)
    if needed['cli']:
        data = CLI_BACKUP.read_bytes()
        require(digest(data) == c.m.CLI_OLD, 'backup bytes differ: ' + str(CLI_BACKUP))
        replace_atomic(CLI, data, 0o755, 'rollback')
        actions.append('cli')
    if checkout_state()[0] != OLD_COMMIT:
        moved = git(TEMPLATE, 'checkout', '--detach', OLD_COMMIT)
        require(moved['returncode'] == 0, 'checkout rollback failed: ' + moved['stderr'])
        actions.append('checkout')
    head, _, status = checkout_state()
    final = model_consistency()
    require(identity(CITY/'city.toml') == owned(c.m.CITY_OLD, 0o644)
            and identity(RIG) == owned(c.m.RIGPERM_OLD, 0o644)
            and identity(REGISTRY) == owned(c.m.REGISTRY_OLD, 0o644)
            and identity(CLI) == owned(c.m.CLI_OLD, 0o755)
            and head == OLD_COMMIT and status == UNTRACKED, 'rollback postcondition')
    value = dict(actions=actions, candidate_sha256=c.expected, quiet=observed,
                 models_after_each=models_seen, models_final=final, leftovers=leftovers(),
                 authority_left_in_place=os.path.lexists(c.m.AUTHORITY))
    write_exclusive(c.inputs/'rollback.json', (json.dumps(value, sort_keys=True, indent=1) + '\n').encode(), 0o600)
    print(json.dumps(dict(rollback=actions, ok=True, leftovers=value['leftovers'])))


ACTIONS = {'inputs': step_inputs, 'cli': step_cli, 'city-transition': step_city_transition,
           'checkout': step_checkout, 'registry': step_registry, 'render': step_render,
           'city-final': step_city_final, 'authority': step_authority, 'rollback': rollback}


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    args = sys.argv[1:]
    require(len(args) in (2, 3) and len(args[0]) == 64
            and ((len(args) == 2 and args[1] in ACTIONS) or (len(args) == 3 and args[1] == 'resume'
                                                            and args[2] in STEPS)),
            'usage: prereqs.py <candidate sha256> <step>|resume <step>|rollback')
    os.umask(0o022)
    context = Context(args[0])
    if args[1] == 'resume':
        resume(context, args[2])
    else:
        ACTIONS[args[1]](context)


if __name__ == '__main__':
    main()
