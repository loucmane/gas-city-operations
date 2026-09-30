"""Live M6 prerequisites (ga-e0t1.15 S3), one guarded step per invocation.

  python3 -I -B prereqs_m6.py <manifest_candidate.py sha256> <step>
  python3 -I -B prereqs_m6.py <manifest_candidate.py sha256> resume <step>
  python3 -I -B prereqs_m6.py <manifest_candidate.py sha256> rollback

Steps run in this order:
- inventory: no live change. Proves the S2-accepted predecessor (canonical checkout at 28539934, the M5
  metadata pair, and the Template common Git directory at the S2-accepted digest cac98745) and records
  that directory's full access-time-free inventory; capture_m6.py bounds the later Git changes by it. It
  also writes reports/m6-inputs/city.toml.before, the exact installed city.toml bytes (4f7e170f), which M6
  names as the city-config backup.
- fetch: `git fetch --no-tags origin` in the canonical Template, after `ls-remote` shows main at
  cfd353f3. Automatic gc and maintenance are disabled for the call. Afterwards origin/main is cfd353f3,
  its tree is the reviewed 5a9d18aa, and 28539934 is its ancestor.
- checkout: `git checkout --detach cfd353f3` with hooks off and no optional locks, after every byte the
  metadata pins is proved from the fetched Git objects. The untracked set and on-disk digests are
  asserted, and the signing worker must report the derived dependency version.
- authority: `git worktree add --detach` of the PR 71 authority, which must be clean with no ignored
  or untracked file and exactly the derived coverage.

Every step binds the reviewed candidate bytes, waits for a natural reconciler quiet slot (never starting,
stopping or signalling the timer), proves the quiet host (the dolt-aware S2 scope, no city tmux, the
S2 suspension record) and its exact predecessor, writes an intent, performs one bounded change, and
records the exact postcondition under reports/m6-inputs. An interrupted step can only `resume`, which
proves the postcondition and never repeats the change.

`rollback` returns the canonical checkout to 28539934 (a forced detach, which also repairs an interrupted
checkout's tracked files; it deletes no untracked file but overwrites one at a path 28539934 tracks). It runs only while the installed manifest is still M5 and no M6 executor window
may hold the timer paused or may have launched an apply. The fetched objects and refs and the authority
worktree stay; the record lists them. Residual limits, as in M5: a left-over index.lock, or untracked files
a partial checkout added, need manual recovery; and a `prepare` that wrote its pause intent but crashed
before recording the timer stop keeps rollback refused until the operator confirms the timer by hand.

No lifecycle, timer, worker, signer or Bead action. The Obsidian reconciler timer is never touched.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import types

HERE = Path(__file__).parent
TEMPLATE = Path('/home/loucmane/gas-city-template')
CITY = Path('/home/loucmane/gascity/city')
INSTALLED = CITY/'.gc/platform/install-manifest.json'
INSTALLED_RECEIPT = CITY/'.gc/platform/install-receipt.json'
SUSPENSION = CITY/'.gc/runtime/suspension-state.json'
RUNTIME_SHA = '2585357a808d8f36604d4bf45a39a5363ba87c8d719413ba42d9fd0fac71973f'
CLOSURE_SHA = '4fa0698bc400ccc37fe9a5ac6545f114c0d4f4817ebdd41733abbf1e63bd924c'  # s3/metadata_closure.py
TARGET_TREE = '5a9d18aa4fcfc25d35b3be594d16a68170ea8bdd'
S2_OBSERVATION = Path('/var/tmp/ga-e0t1.15-seq14-recovery-20260925/observation-2.json')
S2_OBSERVATION_SHA = '74a04a2697cc8dcedfd0672a5c1db486879486033fd45477cd4ad0ace30f6022'
UNTRACKED = '?? deploy/\n?? gas_city_template.egg-info/\n'
RECONCILER = 'aegis-obsidian-reconcile.service'
RECONCILER_TIMER_OBJECT = '/org/freedesktop/systemd1/unit/aegis_2dobsidian_2dreconcile_2etimer'
SLOT_US = 40_000_000
SLOT_DEADLINE_S = 180
GIT_ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/home/loucmane', 'LANG': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_TERMINAL_PROMPT': '0'}
# PR 70 changes the renderer; its cfd353f3 blob is pinned, and it reproduces the live fragment (PLAN-S3.md).
RENDERER_SHA = 'bb97950c604d4bdb0e1adc35d3559e9b3a93a555080bdfca9008423d4d1c7ebe'
CITY_ENV = {'PATH': '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/loucmane',
            'LANG': 'C.UTF-8', 'GC_HOME': '/home/loucmane/gascity/home', 'GIT_OPTIONAL_LOCKS': '0'}
BUS_ENV = dict(CITY_ENV, USER='loucmane', LOGNAME='loucmane', XDG_RUNTIME_DIR='/run/user/1000',
               DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
STEPS = ('inventory', 'fetch', 'checkout', 'authority')
# Disable every automatic writer a fetch or checkout could start inside the Template common directory.
GIT_QUIET = ('-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-c', 'core.untrackedCache=false',
             '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'fetch.writeCommitGraph=false',
             '-c', 'fetch.prune=false')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def load_source(name, expected, module_name):
    path = HERE/name
    raw = path.read_bytes()
    require(expected is not None and digest(raw) == expected, name + ' differs from the reviewed digest')
    module = types.ModuleType(module_name); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def legacy(old_image):
    """The reviewed legacy observer and state modules with the S3 policy installed."""
    r = load_source('source_runtime.py', RUNTIME_SHA, 'pinned_runtime')
    graph = r.legacy()
    o, s = graph['observe_recovery'], graph['recovery_state']
    load_source('metadata_closure.py', CLOSURE_SHA, 'm6_closure').install_policy(o, s, old_image)
    return o, s


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


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


def run(argv, env, cwd='/', timeout=120):
    result = subprocess.run(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=timeout, check=False)
    return dict(argv=argv, returncode=result.returncode,
                stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace'))


def git(repo, *args, timeout=120):
    return run(['/usr/bin/git', '--no-optional-locks', *GIT_QUIET, '-C', str(repo), *args], GIT_ENV, timeout=timeout)


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
    require(head['returncode'] == 0 and status['returncode'] == 0, 'canonical checkout state unreadable')
    return head['stdout'].strip(), symbolic['returncode'], status['stdout']


def reconciler_state():
    shown = run(['/usr/bin/systemctl', '--user', 'show', RECONCILER, '-p', 'ActiveState',
                 '-p', 'ExecMainStartTimestampMonotonic'], BUS_ENV, timeout=10)
    timer = run(['/usr/bin/systemctl', '--user', 'show', RECONCILER.replace('.service', '.timer'),
                 '-p', 'ActiveState'], BUS_ENV, timeout=10)
    elapse = run(['/usr/bin/busctl', '--user', 'get-property', 'org.freedesktop.systemd1', RECONCILER_TIMER_OBJECT,
                  'org.freedesktop.systemd1.Timer', 'NextElapseUSecMonotonic'], BUS_ENV, timeout=10)
    require(shown['returncode'] == timer['returncode'] == elapse['returncode'] == 0, 'reconciler observation')
    fields = dict(line.split('=', 1) for line in shown['stdout'].splitlines())
    timer_fields = dict(line.split('=', 1) for line in timer['stdout'].splitlines())
    parts = elapse['stdout'].split()
    require(set(fields) == {'ActiveState', 'ExecMainStartTimestampMonotonic'}
            and fields['ExecMainStartTimestampMonotonic'].isdigit() and set(timer_fields) == {'ActiveState'}
            and len(parts) == 2 and parts[0] == 't' and parts[1].isdigit(), 'reconciler observation fields')
    return dict(active=fields['ActiveState'], started_us=int(fields['ExecMainStartTimestampMonotonic']),
                timer=timer_fields['ActiveState'], next_us=int(parts[1]))


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


class Context:
    def __init__(self, expected):
        self.m = load_source('manifest_candidate.py', expected, 'm6_candidate')
        self.expected = expected
        self.inputs = Path(self.m.O + '/reports/m6-inputs')
        self.o, self.s = legacy(self.m.OLD)
        self.o.GC_SHA = self.m.NEW
        raw = S2_OBSERVATION.read_bytes()
        require(digest(raw) == S2_OBSERVATION_SHA, 'S2-accepted observation drift')
        self.s2 = json.loads(raw)['closure']

    def quiet(self):
        slot = quiet_slot()
        host = self.o.host_observation()
        require(host['host'] == self.s2['host']['host'], 'host is not the S2-accepted epoch')
        scope = self.s.quiet_scope(host)
        require(sha(SUSPENSION) == self.m.SUSPENSION_SHA, 'suspension record drift')
        return dict(host=host, scope=scope, suspension_sha256=self.m.SUSPENSION_SHA, reconciler=slot)

    def executor_closed(self):
        """False while an M6 executor window may hold the timer paused or may have launched an apply."""
        root = Path(self.m.ROOT)
        if not os.path.lexists(root):
            return True
        q = root/'q'
        if os.path.lexists(q/'commit-consumed.json'):
            return False
        if os.path.lexists(q/'restored.json'):
            return True
        return not os.path.lexists(q/'preparation-pause-intent.json')

    def record_path(self, step, suffix=''):
        return self.inputs/('prereq-' + step + suffix + '.json')

    def common(self, step):
        require(sha(INSTALLED) == self.m.OLD_MANIFEST_SHA and sha(INSTALLED_RECEIPT) == self.m.OLD_RECEIPT_SHA,
                'installed platform metadata is not the M5 pair')
        require(not os.path.lexists(self.m.ROOT), 'M6 package root already exists')
        require(os.path.isdir(self.inputs) and not os.path.islink(self.inputs), 'reports/m6-inputs missing')
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
        write_exclusive(self.record_path(step, '.intent'), encoded(dict(
            step=step, candidate_sha256=self.expected, quiet_before=before)), 0o600)

    def finish(self, step, before, value, resumed=False):
        after = self.quiet()
        require(after['host'] == before['host'], 'host identity changed during the step')
        value = dict(value, step=step, bead='ga-e0t1.15', candidate_sha256=self.expected, resumed=resumed,
                     live_mutation=step != 'inventory', quiet_before=before, quiet_after=after)
        write_exclusive(self.record_path(step), encoded(value), 0o600)
        print(json.dumps(dict(step=step, ok=True, resumed=resumed, record=str(self.record_path(step)))))


def git_config_and_replace(c):
    """The reviewed M5 Template .git configuration set, and no replace ref (loose or packed)."""
    listing = git(TEMPLATE, 'config', '--file', str(TEMPLATE/'.git/config'), '--list')
    replaced = git(TEMPLATE, 'for-each-ref', 'refs/replace')
    require(listing['returncode'] == 0 and replaced['returncode'] == 0 and replaced['stdout'] == '',
            'Template config or replace refs')
    return listing['stdout']


def inventory_records(c):
    """Write, or verify if already written, the two inventory records. They are not live state, so an
    interruption anywhere in the step is recoverable by `resume inventory` (review B should_fix 1)."""
    tree = c.o.tree_snapshot(str(TEMPLATE/'.git'))
    require(tree['sha256'] == c.m.TEMPLATE_GIT_S2 and c.s2['trees'][str(TEMPLATE/'.git')]['sha256'] == tree['sha256'],
            'Template Git directory is not the S2-accepted tree')
    # The city-config backup M6 names: exactly the installed city.toml bytes, which are also M5's source.
    city = (CITY/'city.toml').read_bytes()
    require(identity(CITY/'city.toml') == owned(c.m.CITY_CONFIG_SHA, 0o644) and digest(city) == c.m.CITY_CONFIG_SHA
            and sha(c.m.CITY_CONFIG_SOURCE) == c.m.CITY_CONFIG_SHA, 'installed city config is not the M5 bytes')
    for name, data, mode in (('template-git-before.json', encoded(tree), 0o600), ('city.toml.before', city, 0o644)):
        path = c.inputs/name
        if not os.path.lexists(path):
            write_exclusive(path, data, mode)
        elif identity(path) != owned(digest(data), mode):
            # Only reachable through `resume inventory` after an interrupted write: the record is this step's
            # own, not live state, so it is replaced atomically by the freshly proved bytes (review B r2
            # should_fix 2). A symlink or non-regular entry is never replaced.
            require(stat.S_ISREG(os.lstat(path).st_mode) and os.path.lexists(c.record_path('inventory', '.intent'))
                    and not os.path.lexists(c.record_path('inventory')), 'inventory record differs: ' + name)
            tmp = path.parent/('.' + name + '.resume.tmp')
            require(not os.path.lexists(tmp), 'leftover inventory temporary; inspect ' + str(tmp))
            write_exclusive(tmp, data, mode)
            os.replace(tmp, path)
            fsync_dir(path.parent)
            require(identity(path) == owned(digest(data), mode), 'inventory record replacement')


def post_inventory(c):
    head, symbolic, status = checkout_state()
    require(head == c.m.M5_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout predecessor')
    inventory_records(c)
    record = c.inputs/'template-git-before.json'
    tree = json.loads(record.read_bytes())
    require(tree['sha256'] == c.m.TEMPLATE_GIT_S2, 'recorded inventory is not the S2-accepted digest')
    require(Path(c.m.CITY_CONFIG_BACKUP) == c.inputs/'city.toml.before'
            and identity(c.m.CITY_CONFIG_BACKUP) == owned(c.m.CITY_CONFIG_SHA, 0o644), 'city config backup identity')
    return dict(inventory=str(record), inventory_file_sha256=sha(record), template_git=tree['sha256'],
                entries=tree['entries'], city_config_backup=identity(c.m.CITY_CONFIG_BACKUP))


def post_fetch(c):
    remote = git(TEMPLATE, 'rev-parse', 'refs/remotes/origin/main')
    tree = git(TEMPLATE, 'rev-parse', c.m.TEMPLATE_COMMIT + '^{tree}')
    ancestor = git(TEMPLATE, 'merge-base', '--is-ancestor', c.m.M5_COMMIT, c.m.TEMPLATE_COMMIT)
    require(remote['stdout'].strip() == c.m.TEMPLATE_COMMIT and tree['stdout'].strip() == TARGET_TREE
            and ancestor['returncode'] == 0, 'fetched target commit, tree or ancestry')
    head, symbolic, status = checkout_state()
    require(head == c.m.M5_COMMIT and symbolic == 1 and status == UNTRACKED, 'fetch moved the checkout')
    return dict(origin_main=c.m.TEMPLATE_COMMIT, tree=TARGET_TREE, config=git_config_and_replace(c))


def post_checkout(c):
    head, symbolic, status = checkout_state()
    require(head == c.m.TEMPLATE_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout successor')
    path, _, after = c.m.CHANGED_INPUTS[0]
    require(identity(path) == owned(after, 0o644), 'successor signing worker bytes')
    for pinned, value in c.m.RETAINED_TEMPLATE_PINS.items():
        require(sha(pinned) == value, 'retained Template bytes: ' + pinned)
    require(sha(TEMPLATE/'bin/gct-managed-rig-permissions') == RENDERER_SHA, 'successor renderer bytes')
    version = run([str(TEMPLATE/'bin/gct-claude-signing-worker'), '--version'], CITY_ENV, timeout=60)
    require(version['returncode'] == 0 and version['stdout'].strip() == c.m.VERSION_NEW,
            'signing worker dependency version')
    return dict(after_commit=head, status=status, version=version)


def post_authority(c):
    auth = Path(c.m.AUTHORITY)
    head = git(auth, 'rev-parse', 'HEAD')
    status = git(auth, 'status', '--porcelain', '--ignored', '--untracked-files=all')
    require(head['stdout'].strip() == c.m.TEMPLATE_COMMIT and status['returncode'] == 0
            and status['stdout'] == '', 'authority HEAD/clean, no ignored or untracked file')
    require((auth/'.git').read_bytes() == c.m.authority_pointer(), 'authority pointer bytes')
    files = {}
    for relative, value, mode in c.m.auth_inputs():
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


POST = {'inventory': post_inventory, 'fetch': post_fetch, 'checkout': post_checkout, 'authority': post_authority}


def step_inventory(c):
    # The package gates run before anything is created (review B should_fix 2).
    require(sha(INSTALLED) == c.m.OLD_MANIFEST_SHA and sha(INSTALLED_RECEIPT) == c.m.OLD_RECEIPT_SHA,
            'installed platform metadata is not the M5 pair')
    require(not os.path.lexists(c.m.ROOT), 'M6 package root already exists')
    # An empty, owner-only, real directory is what an interruption between mkdir and the intent leaves.
    if os.path.lexists(c.inputs):
        require(os.path.isdir(c.inputs) and not os.path.islink(c.inputs) and os.listdir(c.inputs) == []
                and stat.S_IMODE(os.lstat(c.inputs).st_mode) == 0o700, 'inputs directory is not fresh')
    else:
        os.mkdir(c.inputs, 0o700)
    before = c.begin('inventory')
    head, symbolic, status = checkout_state()
    require(head == c.m.M5_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout predecessor')
    config = git_config_and_replace(c)
    c.intent('inventory', before)
    c.finish('inventory', before, dict(post_inventory(c), config=config))


def step_fetch(c):
    before = c.begin('fetch')
    head, symbolic, status = checkout_state()
    require(head == c.m.M5_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout predecessor')
    remote = git(TEMPLATE, 'ls-remote', 'origin', 'refs/heads/main', timeout=60)
    require(remote['returncode'] == 0 and remote['stdout'] == c.m.TEMPLATE_COMMIT + '\trefs/heads/main\n',
            'remote main is not the reviewed target')
    for name in ('index.lock', 'shallow', 'objects/info/alternates', 'gc.pid'):
        require(not os.path.lexists(TEMPLATE/'.git'/name), 'Template .git state: ' + name)
    c.intent('fetch', before)
    fetched = git(TEMPLATE, 'fetch', '--no-tags', 'origin', timeout=300)
    require(fetched['returncode'] == 0, 'fetch failed: ' + fetched['stderr'])
    c.finish('fetch', before, dict(post_fetch(c), ls_remote=remote, command=fetched))


def step_checkout(c):
    before = c.begin('checkout')
    head, symbolic, status = checkout_state()
    require(head == c.m.M5_COMMIT and symbolic == 1 and status == UNTRACKED, 'canonical checkout predecessor')
    require(not os.path.lexists(TEMPLATE/'.git/index.lock'), 'canonical checkout index is locked')
    # Prove every byte the metadata pins from Git objects before the checkout moves.
    prefix = str(TEMPLATE) + '/'
    path, _, after = c.m.CHANGED_INPUTS[0]
    require(blob_digest(c.m.TEMPLATE_COMMIT, path[len(prefix):]) == after, 'target signing worker blob')
    for pinned, value in c.m.RETAINED_TEMPLATE_PINS.items():
        require(blob_digest(c.m.TEMPLATE_COMMIT, pinned[len(prefix):]) == value, 'target retained blob: ' + pinned)
    renderer = blob_digest(c.m.TEMPLATE_COMMIT, 'bin/gct-managed-rig-permissions')
    require(renderer == RENDERER_SHA, 'target renderer blob')
    c.intent('checkout', before)
    moved = git(TEMPLATE, 'checkout', '--detach', c.m.TEMPLATE_COMMIT)
    require(moved['returncode'] == 0, 'checkout failed: ' + moved['stderr'])
    c.finish('checkout', before, dict(post_checkout(c), before_commit=c.m.M5_COMMIT, renderer_blob=renderer,
                                      command=moved))


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
    verified = POST[step](c)
    c.finish(step, recorded['quiet_before'], dict(verified, resumed_from_intent=str(intent)), resumed=True)


def rollback(c):
    require(sha(INSTALLED) == c.m.OLD_MANIFEST_SHA, 'successor may be installed; rollback refused')
    require(c.executor_closed(), 'M6 executor window is open; restore it through the executor first')
    require(os.path.isdir(c.inputs) and not os.path.lexists(c.inputs/'rollback.json'), 'rollback state')
    try:
        observed = c.quiet()
    except Exception as exc:  # restoration must remain possible; record why the host was not quiet
        observed = dict(error=type(exc).__name__, reason=str(exc))
    actions = []
    head, _, status = checkout_state()
    if head != c.m.M5_COMMIT or status != UNTRACKED:
        # Also covers an interrupted checkout that left HEAD at either commit with a partly updated tree
        # (review B should_fix 3). A forced detach discards every change to tracked files. It deletes no
        # untracked file, but overwrites one that collides with a path 28539934 tracks; deploy/ and the
        # egg-info do not collide.
        require(head in (c.m.M5_COMMIT, c.m.TEMPLATE_COMMIT), 'unknown canonical checkout; inspect by hand')
        require(not os.path.lexists(TEMPLATE/'.git/index.lock'), 'canonical checkout index is locked; inspect by hand')
        moved = git(TEMPLATE, 'checkout', '-f', '--detach', c.m.M5_COMMIT)
        require(moved['returncode'] == 0, 'checkout rollback failed: ' + moved['stderr'])
        actions.append('checkout')
    head, symbolic, status = checkout_state()
    # Files the target added may remain untracked after a partial checkout; they are listed, never deleted.
    require(head == c.m.M5_COMMIT and symbolic == 1 and status == UNTRACKED,
            'rollback postcondition; recover by hand, remaining status: ' + status)
    for pinned, value in c.m.RETAINED_TEMPLATE_PINS.items():
        require(sha(pinned) == value, 'retained Template bytes after rollback: ' + pinned)
    require(sha(c.m.CHANGED_INPUTS[0][0]) == c.m.CHANGED_INPUTS[0][1], 'predecessor signing worker bytes')
    value = dict(actions=actions, candidate_sha256=c.expected, quiet=observed,
                 fetched_objects_and_refs_left_in_place=True,
                 authority_left_in_place=os.path.lexists(c.m.AUTHORITY))
    write_exclusive(c.inputs/'rollback.json', encoded(value), 0o600)
    print(json.dumps(dict(rollback=actions, ok=True)))


ACTIONS = {'inventory': step_inventory, 'fetch': step_fetch, 'checkout': step_checkout,
           'authority': step_authority, 'rollback': rollback}


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    args = sys.argv[1:]
    require(len(args) in (2, 3) and len(args[0]) == 64
            and ((len(args) == 2 and args[1] in ACTIONS) or (len(args) == 3 and args[1] == 'resume'
                                                            and args[2] in STEPS)),
            'usage: prereqs_m6.py <candidate sha256> <step>|resume <step>|rollback')
    os.umask(0o022)
    context = Context(args[0])
    if args[1] == 'resume':
        resume(context, args[2])
    else:
        ACTIONS[args[1]](context)


if __name__ == '__main__':
    main()
