"""gct-m1wh platform canary (ga-0t04, M5 LAYOUT.md step 7).

Runs `gc platform canary` once for the signing profile gascity/gc.implementation-worker:
- It checks the exact live pins, then records a before state.
- It runs the canary and then verifies the receipt that Core publishes.
- It compares, before and after, only these: the live canary tree, the pinned files, the supervisor
  identity and the pack-cache slot names. Nothing else in the live city is compared.

Its only intended live writes are the two files Core publishes, and only on PASS:
- .gc/runtime/canary/profiles/<sha256(profile)>.json
- .gc/runtime/canary/history/<receipt_sha256>.json

How the nine scenarios run:
- They run in disposable scratch cities under SCRATCH/RUN_ID.
- Each scratch city has its own GC_HOME, supervisor and tmux socket.
- The worker is the runner's own scripted --worker mode.
- It signs with a throwaway ed25519 key made in scratch.
So nothing performs inference and nothing reaches the real signer.

Evidence goes to OUT. If gc itself fails, Core publishes nothing. If this script refuses after gc
passed, Core has already published the receipt. It stays in place, no work is routed to the profile,
and the coordinator stops and reports; this script never deletes it.

r2 difference: GC_STORE_PATH is set to the clean-launcher scratch rig store. Runner v3's controller
gate omits it (gct-7np4), but the pinned pack check requires it, and Core supplies exactly this value:
the store the bead was found in, i.e. the rig subtree.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time

CITY = '/home/loucmane/gascity/city'
GC = '/home/loucmane/gascity/bin/gc'
GC_SHA = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'
GC_HOME = '/home/loucmane/gascity/home'
RUNNER = CITY + '/.gc/runtime/provisioning/bin/gct-managed-worker-canary'
RUNNER_SHA = '3beeedb2e5ce0723e5f745a05f1e2fdfa3ec27bee468284860e587e63c63e2e2'
PROVISIONING = CITY + '/.gc/runtime/provisioning/receipt.json'
PROVISIONING_SHA = '0b30c23f4484382fd4918f394599268f4f4005ac71118e8a7f82ca72eb9615ff'
PROVISIONING_SELF = 'c635e8ee0547ebc8c4caec6577d65103b9d17436ff17a18f66687f0ea3f1957f'
MANIFEST = CITY + '/.gc/platform/install-manifest.json'
MANIFEST_SHA = '2d7eadce62c4e567697813cc9122414f1e94c3bd9d389aef92015adef7f36319'
INSTALL_RECEIPT = CITY + '/.gc/platform/install-receipt.json'
INSTALL_RECEIPT_SHA = '9342b33eb7b0fd4e68a34c8cee3b8a89b9011a091d7121d249b88c84378fed94'
CANARY_DIR = CITY + '/.gc/runtime/canary'
# The 2026-08-28 legacy v1 receipt and its history copy. Both must survive byte-identical.
LEGACY = CANARY_DIR + '/receipt.json'
LEGACY_SHA = 'ff10fbe7d5a380b385fd4a0b10dd13c9a88d17f77f94602d88ed2796066e9250'
LEGACY_HISTORY = CANARY_DIR + '/history/ad9c3eebb029929438d89f843676490451481e7b3e0bb878b8ed110b7a3ce4b2.json'
PROFILE = 'gascity/gc.implementation-worker'
PROFILE_KIND = 'signing'
PROFILE_SHA = '218675dad146d48b11abce71157ba26a9090600e13676f7bbbf1625e589f3c59'
CONTROL_POLICY = '/home/loucmane/gas-city-template/templates/claude/core-signing-control-policy.json'
CONTROL_POLICY_SHA = '16022d04533e3d6366cfc25b3ad76a3af2d7bd5da2ad7412d76b93fe4d3c1225'
TEMPLATE_COMMIT = '28539934fa742056e0a65710d5638ff559a21175'
PERMISSION_REVISION = 'd6ca85cd96c7aab4ea0b6a7954d2d74e5e6bb211cde0bb820f3b6f815023bd88'
PROFILE_RECEIPT = CANARY_DIR + '/profiles/' + hashlib.sha256(PROFILE.encode()).hexdigest() + '.json'
# The reviewed ga-mutg build input: the clean Core source at the commit the live gc was built from.
# The 2026-08-28 canary likewise cloned the Core build tree at its gc binary commit.
LAUNCHER = '/tmp/ga-mutg-build-20260919/repro-source'
BASE = '796d9a7a67c42294fdc467c107bb59b76e482301'
SCRATCH = '/home/loucmane/gascity/canary-evidence'
RUN_ID = 'm1wh-20260923-r2'
RUN_ROOT = SCRATCH + '/' + RUN_ID
OUT = '/var/tmp/gct-m1wh-canary-20260923-r2'
# Core's convergence env passes GC_STORE_PATH as the store the bead lives in: the rig subtree, here the
# clean-launcher scratch launcher clone. Only the clean-launcher controller gate consumes it.
STORE_PATH = RUN_ROOT + '/clean-launcher/launcher'
MAX_WALL = '30m0s'
TIMEOUT = 2400
SUPERVISOR_PID = 3150812
SUPERVISOR_START = 8461901
CACHE_REPOS = GC_HOME + '/cache/repos'
# The live cache slots the scratch city's pack imports resolve to. The one live-GC_HOME call in the
# runner (bd show) must find them present, never fetch them.
CACHE_SLOTS = ['a21cc0a2fbf22c14fbe59cf508d05bcc230774f5c0d9cd386215369d43a2410a',
               'af5bc8992ed2965413edcc17674aafcc9b5c28c53f8b4178f8e63316d044af38',
               'c5f076a22b07b5049e4c8fecf630b4e83c74d660a106e63873292034af699252']
# RequiredCanaryScenariosFor(signing) in Core 796d9a7a internal/managedworker, in its order.
SCENARIOS = ['clean-launcher', 'validator-absent', 'detached-head', 'unreadable-mail',
             'denied-subprocess-socket', 'stale-session-killed-tmux', 'missing-provider',
             'publisher-failed-finalize', 'publisher-success-noop']
TOOLS = ['bd', 'dolt', 'git', 'ssh-keygen', 'tmux', 'unshare']
PATH = '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin'


class Stop(Exception):
    pass


def sha(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def strict_json(raw, name):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise Stop('%s has a duplicate key %r' % (name, key))
            seen[key] = value
        return seen
    try:
        return json.loads(raw, object_pairs_hook=pairs)
    except ValueError as exc:
        raise Stop('%s is not valid JSON: %s' % (name, exc))


def pinned(path, digest, name, executable=False):
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode):
        raise Stop('%s is not a regular file: %s' % (name, path))
    if executable and not info.st_mode & 0o111:
        raise Stop('%s is not executable: %s' % (name, path))
    actual = sha(path)
    if actual != digest:
        raise Stop('%s digest %s, want %s' % (name, actual, digest))
    return {'path': path, 'sha256': actual, 'mode': oct(stat.S_IMODE(info.st_mode))}


def child_env():
    # A fixed environment, mirroring the live supervisor's locale and Git settings. Several
    # inherited variables are deliberately left out:
    # - GCT_*: the runner's test switches;
    # - GC_SUPERVISOR_PRESERVE_SESSIONS_ON_SIGNAL: it would keep scratch sessions on teardown;
    # - SSH_AUTH_SOCK: the real agent.
    return {
        'HOME': '/home/loucmane', 'USER': 'loucmane', 'LOGNAME': 'loucmane', 'SHELL': '/usr/bin/zsh',
        'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'LC_CTYPE': 'C.UTF-8',
        'PATH': PATH,
        'XDG_RUNTIME_DIR': '/run/user/1000',
        'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus',
        'GC_HOME': GC_HOME, 'GC_BIN': GC,
        'GC_DISABLE_USAGE_METRICS': '1', 'GIT_OPTIONAL_LOCKS': '0',
        'GC_STORE_PATH': STORE_PATH,
    }


def canary_argv():
    return [GC, '--city', CITY, 'platform', 'canary',
            '--run-id', RUN_ID,
            '--runner', RUNNER, '--runner-sha256', RUNNER_SHA,
            '--launcher-source', LAUNCHER, '--base-commit', BASE,
            '--scratch-root', SCRATCH,
            '--profile', PROFILE, '--profile-kind', PROFILE_KIND,
            '--max-wall-time', MAX_WALL]


def socket_lengths():
    return {name: len(os.fsencode('%s/%s/home/supervisor.sock' % (RUN_ROOT, name))) for name in SCENARIOS}


def supervisor_identity():
    with open('/proc/%d/stat' % SUPERVISOR_PID) as handle:
        text = handle.read()
    fields = text[text.rindex(')') + 2:].split()
    return {'pid': SUPERVISOR_PID, 'starttime': int(fields[19]),
            'mnt': os.readlink('/proc/%d/ns/mnt' % SUPERVISOR_PID)}


def git(repo, *args):
    done = subprocess.run(['git', '-C', repo, '--no-optional-locks', *args], capture_output=True,
                          text=True, timeout=60, env=child_env(), stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise Stop('git %s in %s failed: %s' % (' '.join(args), repo, done.stderr.strip()[:300]))
    return done.stdout


def tree(root):
    """Map every path under root to its type, mode and (for files) size and digest."""
    found = {}
    for current, dirs, files in os.walk(root):
        dirs.sort()
        for name in dirs + sorted(files):
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root)
            info = os.lstat(path)
            mode = oct(stat.S_IMODE(info.st_mode))
            if stat.S_ISDIR(info.st_mode):
                found[rel] = {'type': 'dir', 'mode': mode}
            elif stat.S_ISREG(info.st_mode):
                found[rel] = {'type': 'file', 'mode': mode, 'size': info.st_size, 'sha256': sha(path)}
            else:
                found[rel] = {'type': 'other', 'mode': mode}
    return found


def tree_delta(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(key for key in set(before) & set(after) if before[key] != after[key])
    return added, removed, changed


def expected_additions(receipt_sha):
    rel = os.path.relpath(PROFILE_RECEIPT, CANARY_DIR)
    return sorted(['profiles', rel, 'history/%s.json' % receipt_sha])


def process_table(proc='/proc'):
    rows = []
    for entry in os.listdir(proc):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        try:
            with open('%s/%s/cmdline' % (proc, entry), 'rb') as handle:
                argv = [part.decode(errors='replace') for part in handle.read().split(b'\0') if part]
        except OSError:
            continue
        try:
            cwd = os.readlink('%s/%s/cwd' % (proc, entry))
        except OSError:
            cwd = ''
        rows.append((int(entry), argv, cwd))
    return rows


def leftovers(rows):
    """Processes that still reference this run's scratch root, tmux socket or runner."""
    marks = (RUN_ROOT, 'canary-' + RUN_ID, RUNNER)
    hits = []
    for pid, argv, cwd in rows:
        if cwd == RUN_ROOT or cwd.startswith(RUN_ROOT + '/') or cwd == LAUNCHER \
                or any(mark in arg for arg in argv for mark in marks):
            hits.append({'pid': pid, 'argv': argv[:8], 'cwd': cwd})
    return hits


def parse_stdout(text):
    line = re.compile(r'platform canary result=pass run_id="%s" receipt_sha256=([0-9a-f]{64}) receipt=(\S+)'
                      % re.escape(RUN_ID))
    lines = text.splitlines()
    if len(lines) != 1:
        raise Stop('canary stdout has %d lines, want exactly one' % len(lines))
    match = line.fullmatch(lines[0])
    if not match:
        raise Stop('canary stdout is not the pass line: %r' % lines[0][:300])
    if match.group(2) != PROFILE_RECEIPT:
        raise Stop('canary receipt path %s, want %s' % (match.group(2), PROFILE_RECEIPT))
    return match.group(1)


def verify_receipt(receipt, receipt_sha):
    """Check the published v2 receipt certifies exactly the pinned profile, runner and environment."""
    checks = [
        ('schema', receipt.get('schema'), 'gc.canary-receipt.v2'),
        ('canary_run_id', receipt.get('canary_run_id'), RUN_ID),
        ('result', receipt.get('result'), 'pass'),
        ('receipt_sha256', receipt.get('receipt_sha256'), receipt_sha),
        ('profile', receipt.get('profile'), {'name': PROFILE, 'profile_kind': PROFILE_KIND, 'sha256': PROFILE_SHA}),
        ('runner', receipt.get('runner'), {'path': RUNNER, 'sha256': RUNNER_SHA}),
    ]
    environment = receipt.get('environment') or {}
    embedded = receipt.get('provisioning_receipt') or {}
    checks += [
        ('environment.provisioning_receipt_sha256', environment.get('provisioning_receipt_sha256'), PROVISIONING_SELF),
        ('environment.gc_binary', environment.get('gc_binary'), {'commit': BASE, 'sha256': GC_SHA}),
        ('environment.template_commit', environment.get('template_commit'), TEMPLATE_COMMIT),
        ('environment.permission_revision', environment.get('permission_revision'), PERMISSION_REVISION),
        ('environment.profiles', environment.get('profiles'), [{'name': PROFILE, 'sha256': PROFILE_SHA}]),
        ('provisioning_receipt.receipt_sha256', embedded.get('receipt_sha256'), PROVISIONING_SELF),
        ('provisioning_receipt.template_commit', embedded.get('template_commit'), TEMPLATE_COMMIT),
    ]
    for name, actual, want in checks:
        if actual != want:
            raise Stop('receipt %s is %r, want %r' % (name, actual, want))
    scenarios = receipt.get('scenarios')
    names = [item.get('name') for item in scenarios or []]
    if names != sorted(SCENARIOS):
        raise Stop('receipt scenarios %r, want %r' % (names, sorted(SCENARIOS)))
    for item in scenarios:
        if item.get('outcome') != 'pass' or not isinstance(item.get('attention_latency_cycles'), int) \
                or not 0 <= item['attention_latency_cycles'] <= 1:
            raise Stop('receipt scenario %r is not a bounded pass' % item)
    return {item['name']: item['attention_latency_cycles'] for item in scenarios}


def pins():
    return {
        'gc': pinned(GC, GC_SHA, 'gc binary', executable=True),
        'runner': pinned(RUNNER, RUNNER_SHA, 'canary runner', executable=True),
        'provisioning': pinned(PROVISIONING, PROVISIONING_SHA, 'provisioning receipt'),
        'manifest': pinned(MANIFEST, MANIFEST_SHA, 'install manifest'),
        'install_receipt': pinned(INSTALL_RECEIPT, INSTALL_RECEIPT_SHA, 'install receipt'),
        'legacy': pinned(LEGACY, LEGACY_SHA, 'legacy canary receipt'),
        'legacy_history': pinned(LEGACY_HISTORY, LEGACY_SHA, 'legacy canary history'),
        'control_policy': pinned(CONTROL_POLICY, CONTROL_POLICY_SHA, 'signing control policy'),
    }


def precheck():
    if os.umask(0o022) != 0o022:
        raise Stop('umask is not 0022')
    identity = supervisor_identity()
    if identity['starttime'] != SUPERVISOR_START:
        raise Stop('supervisor %d start time %d, want %d' % (SUPERVISOR_PID, identity['starttime'], SUPERVISOR_START))
    if os.readlink('/proc/self/ns/mnt') != identity['mnt']:
        raise Stop('not in the supervisor mount namespace; start through systemd-run --user')
    state = pins()
    provisioning = strict_json(open(PROVISIONING, 'rb').read(), 'provisioning receipt')
    if provisioning.get('receipt_sha256') != PROVISIONING_SELF:
        raise Stop('provisioning receipt self digest drift')
    if provisioning.get('canary_runner') != {'path': RUNNER, 'sha256': RUNNER_SHA}:
        raise Stop('provisioning receipt does not bind the pinned runner')
    profiles = [item for item in provisioning.get('profiles', []) if item.get('name') == PROFILE]
    if len(profiles) != 1 or profiles[0].get('profile_kind') != PROFILE_KIND \
            or profiles[0].get('worker_profile_sha256') != PROFILE_SHA \
            or profiles[0].get('control_policy') != {'path': CONTROL_POLICY, 'sha256': CONTROL_POLICY_SHA}:
        raise Stop('provisioning receipt does not declare the pinned signing profile')
    for path in (PROFILE_RECEIPT, os.path.dirname(PROFILE_RECEIPT), RUN_ROOT):
        if os.path.lexists(path):
            raise Stop('already exists: %s' % path)
    missing_slots = [slot for slot in CACHE_SLOTS if not os.path.isdir(os.path.join(CACHE_REPOS, slot))]
    if missing_slots:
        raise Stop('live pack-cache slots missing (the runner would fetch into the live cache): %r' % missing_slots)
    if not os.path.isdir(SCRATCH) or os.path.islink(SCRATCH):
        raise Stop('scratch root is not a directory: %s' % SCRATCH)
    if git(LAUNCHER, 'rev-parse', 'HEAD').strip() != BASE:
        raise Stop('launcher source is not at %s' % BASE)
    if git(LAUNCHER, 'status', '--porcelain'):
        raise Stop('launcher source is not clean')
    long_sockets = {name: size for name, size in socket_lengths().items() if size > 107}
    if long_sockets:
        raise Stop('scratch supervisor socket paths exceed 107 bytes: %r' % long_sockets)
    missing = [tool for tool in TOOLS if not shutil.which(tool, path=PATH)]
    if missing or not os.access('/usr/bin/python3', os.X_OK):
        raise Stop('missing tools: %r' % (missing or ['/usr/bin/python3']))
    if leftovers(process_table()):
        raise Stop('processes already reference %s' % RUN_ROOT)
    return {'supervisor': identity, 'pins': state, 'canary_tree': tree(CANARY_DIR),
            'cache_repos': sorted(os.listdir(CACHE_REPOS)), 'sockets': socket_lengths()}


def write(name, value):
    path = os.path.join(OUT, name)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, 'w') as handle:
        handle.write(value if isinstance(value, str) else json.dumps(value, indent=1, sort_keys=True) + '\n')


def say(text):
    print('== %s %s' % (time.strftime('%H:%M:%SZ', time.gmtime()), text), flush=True)


def settled_leftovers(bound=30):
    # Scratch dolt and tmux may still be exiting when gc returns, so poll briefly before judging.
    deadline = time.monotonic() + bound
    while True:
        hits = leftovers(process_table())
        if not hits or time.monotonic() >= deadline:
            return hits
        time.sleep(1)


def after_state():
    return {'supervisor': supervisor_identity(), 'leftovers': settled_leftovers(),
            'canary_tree': tree(CANARY_DIR), 'cache_repos': sorted(os.listdir(CACHE_REPOS))}


def main():
    if os.path.lexists(OUT):
        say('STOP: evidence root already used: %s' % OUT)
        return 1
    os.mkdir(OUT, 0o700)
    result = {'ok': False, 'stage': 'precheck', 'error': None, 'run_id': RUN_ID}
    try:
        before = precheck()
        write('before.json', before)
        write('argv.json', {'argv': canary_argv(), 'env': child_env(), 'cwd': OUT, 'timeout': TIMEOUT})
        say('precheck ok; canary %s starting' % RUN_ID)
        result['stage'] = 'canary'
        started = time.time()
        try:
            done = subprocess.run(canary_argv(), env=child_env(), cwd=OUT, stdin=subprocess.DEVNULL,
                                  capture_output=True, timeout=TIMEOUT)
            rc = done.returncode
            stdout, stderr = done.stdout.decode(errors='replace'), done.stderr.decode(errors='replace')
        except subprocess.TimeoutExpired as exc:
            rc = 'timeout'
            stdout = exc.stdout.decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
            stderr = exc.stderr.decode(errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
        result['seconds'] = round(time.time() - started, 1)
        write('canary.stdout', stdout)
        write('canary.stderr', stderr)
        write('canary.exit', '%s\n' % rc)
        say('canary exit %s after %ss' % (rc, result['seconds']))
        result['stage'] = 'verify'
        after = after_state()
        try:
            after['pins'] = pins()
        except (Stop, OSError) as exc:
            after['pins_error'] = str(exc)
        write('after.json', after)
        if 'pins_error' in after:
            raise Stop('pinned file drift after the run: %s' % after['pins_error'])
        added, removed, changed = tree_delta(before['canary_tree'], after['canary_tree'])
        result.update(canary_added=added, canary_removed=removed, canary_changed=changed,
                      cache_added=sorted(set(after['cache_repos']) - set(before['cache_repos'])),
                      cache_removed=sorted(set(before['cache_repos']) - set(after['cache_repos'])),
                      leftovers=after['leftovers'])
        if after['supervisor'] != before['supervisor']:
            raise Stop('live supervisor identity changed: %r' % after['supervisor'])
        if removed or changed:
            raise Stop('existing canary files changed: removed %r changed %r' % (removed, changed))
        if rc != 0:
            if added:
                raise Stop('canary exit %s but live canary files appeared: %r' % (rc, added))
            raise Stop('canary did not pass (exit %s); nothing was published: %s' % (rc, stderr.strip()[-1500:]))
        receipt_sha = parse_stdout(stdout)
        if added != expected_additions(receipt_sha):
            raise Stop('live canary additions %r, want %r' % (added, expected_additions(receipt_sha)))
        raw = open(PROFILE_RECEIPT, 'rb').read()
        history = CANARY_DIR + '/history/%s.json' % receipt_sha
        if open(history, 'rb').read() != raw:
            raise Stop('history receipt bytes differ from the current profile receipt')
        for path, mode in ((PROFILE_RECEIPT, 0o600), (history, 0o600), (os.path.dirname(PROFILE_RECEIPT), 0o700)):
            if stat.S_IMODE(os.lstat(path).st_mode) != mode:
                raise Stop('%s mode is not %o' % (path, mode))
        result['latencies'] = verify_receipt(strict_json(raw, 'profile canary receipt'), receipt_sha)
        result['receipt'] = {'path': PROFILE_RECEIPT, 'sha256': hashlib.sha256(raw).hexdigest(),
                             'receipt_sha256': receipt_sha, 'history': history}
        teardown = sorted(name for name in SCENARIOS
                          if os.path.lexists('%s/%s/evidence/teardown-error.txt' % (RUN_ROOT, name)))
        missing = sorted(name for name in SCENARIOS
                         if not os.path.isfile('%s/%s/evidence/scenario.json' % (RUN_ROOT, name)))
        if teardown or missing:
            raise Stop('scenario evidence: teardown errors %r, missing scenario.json %r' % (teardown, missing))
        if after['leftovers']:
            raise Stop('scratch processes survived the canary: %r' % after['leftovers'])
        result.update(ok=True, stage='done')
        say('PASS receipt %s (self %s)' % (result['receipt']['sha256'], receipt_sha))
    except Stop as exc:
        result['error'] = str(exc)
        say('STOP at %s: %s' % (result['stage'], exc))
    except Exception as exc:  # noqa: BLE001 - every failure is recorded, never retried
        result['error'] = '%s: %s' % (type(exc).__name__, exc)
        say('ERROR at %s: %s' % (result['stage'], result['error']))
    write('result.json', result)
    if result.get('cache_added') or result.get('cache_removed'):
        say('note: live pack cache entries added %r removed %r' % (result['cache_added'], result['cache_removed']))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
