"""One nonlaunching read-only composition observation; no receipt installation.

Host identity is observed outside bwrap. Inside, the real filesystem is mounted
read-only with fresh proc/dev and no network. No writable production bind exists.
All process phases use the already-reviewed Template owned-group runner.

P6 rebind of the reviewed 09-20 observer `be8461f4`. The logic is unchanged; only the
bindings below differ:
- a fresh root;
- the draft proven by the reviewed `p6-input.py` derivation, not a pinned digest;
- the installed receipt `01ed1bce`;
- the M5 metadata pair from `m5_acceptance()`, replacing R9.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import sys
import types

HERE = Path(__file__).parent
ROOT = Path('/var/tmp/gct-m1wh-p6-compose-20260923-r1')
INPUT_SOURCE = HERE/'p6-input.py'
INPUT_SHA = '88f1ec2f6e5fbffddc8865ba77a052a7ce6f80b33236758abb8665063e0dfdc2'
BUILD = Path('/var/tmp/ga-ecwh-compose-diagnostic-20260920-r2')
OBS = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/reports/ga-e0t1.14-rollout-r1/package-r4/resume-r4b/recovery-source-r2/observe_recovery.py')
CACHE = Path('/home/loucmane/gascity/home/cache/repos')
CITY = Path('/home/loucmane/gascity/city')
PROTECTED = (CITY/'.gc/platform/assets', CITY/'.gc/platform/backups')
RECEIPT = CITY/'.gc/runtime/provisioning/receipt.json'
GC_SHA = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'
BINARY_SHA = '9f837c831919cd440089ac2207c6e32ca005709b51a72e430a48f76006f2edd3'
LAUNCHER_SHA = '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'
ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane',
    PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin',
    XDG_RUNTIME_DIR='/run/user/1000', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',
    GC_HOME='/home/loucmane/gascity/home', GIT_OPTIONAL_LOCKS='0',
    GIT_NO_REPLACE_OBJECTS='1', LC_ALL='C.UTF-8', PYTHONDONTWRITEBYTECODE='1',
    GODEBUG='containermaxprocs=0', DO_NOT_TRACK='1')

def read(path, expected=None):
    path = Path(path)
    if path.resolve(strict=True) != path:
        raise RuntimeError('source alias: '+str(path))
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != 1000 or before.st_nlink != 1:
            raise RuntimeError('file authority: '+str(path))
        chunks = []
        while chunk := os.read(fd, 1048576):
            chunks.append(chunk)
        raw = b''.join(chunks)
        if before != os.fstat(fd) or len(raw) != before.st_size:
            raise RuntimeError('file changed during read')
    finally:
        os.close(fd)
    if expected and hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError('digest drift: '+str(path))
    return raw

def module(path, expected):
    raw = read(path, expected)
    value = types.ModuleType(Path(path).stem)
    value.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), value.__dict__)
    return value

def input_module():
    return module(INPUT_SOURCE, INPUT_SHA)

def recorded_draft():
    """The recorded receipt input, proven to be the reviewed derivation."""
    return input_module().proven_draft()

def observe_module():
    value = module(OBS, 'f5357d222f0a2f7ceb9e1a830533f20a4868fe5f3beb247de335843b730bdd78')
    value.GC_SHA = GC_SHA  # exact installed successor, no change to observer logic
    return value

def write(name, value):
    with (ROOT/name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')

def snapshot(name):
    o = observe_module()
    host = o.host_observation()
    o.require(host['host']['boot'] == 'f4e38c6a-bfc9-4532-a713-0497904c5b1a'
        and host['core']['MainPID'] == '3150812'
        and host['core']['ExecMainStartTimestampMonotonic'] == '84619011818'
        and host['signer']['MainPID'] == '5550'
        and host['signer']['ExecMainStartTimestampMonotonic'] == '208267863'
        and host['broker']['MainPID'] == '2862577'
        and host['broker']['ExecMainStartTimestampMonotonic'] == '77125780270', 'host epoch drift')
    paths = [CITY/'city.toml', CITY/'pack.toml', CITY/'.gc/settings.json',
        CITY/'packs.lock', CITY/'.gc/site.toml',
        CITY/'managed/attention-funnel.toml', CITY/'managed/core-signing-continuity.toml',
        CITY/'managed/rig-permissions.json', CITY/'managed/rig-permissions.toml',
        CITY/'agents/watch-officer/prompt.template.md',
        CITY/'.gc/platform/install-manifest.json', CITY/'.gc/platform/install-receipt.json',
        CITY/'.gc/runtime/suspension-state.json', RECEIPT,
        Path('/home/loucmane/gas-city-template/bin/gct-claude-signing-worker'),
        Path('/home/loucmane/gas-city-template/templates/claude/core-signing-control-policy.json')]
    pins = {str(path): o.read_file(str(path))[0] for path in paths}
    p = input_module()
    m5 = p.m5_acceptance()
    o.require(pins[str(RECEIPT)]['sha256'] == p.RECEIPT_OLD_SHA, 'installed receipt drift')
    o.require(pins[str(CITY/'.gc/platform/install-manifest.json')]['sha256'] == m5['canonical_file_sha256']
        and pins[str(CITY/'.gc/platform/install-receipt.json')]['sha256'] == m5['receipt_file_sha256'], 'M5 metadata drift')
    lock = CACHE/'.packman-cache.lock'
    o.require(stat.S_ISREG(lock.lstat().st_mode), 'cache lock must already exist')
    cache = o.tree_snapshot(CACHE, cache=True)
    protected = {str(path):o.tree_snapshot(path, protected=True) for path in PROTECTED}
    o.require(host == o.host_observation(), 'host changed during snapshot')
    result = dict(host=host, pins=pins, cache=cache, protected=protected)
    write(name, result)
    print(json.dumps(dict(ok=True, snapshot=name, cache_entries=cache['entries'])))

def inner():
    # Inspect effective mount flags, not merely the intended bwrap argv.
    lines = Path('/proc/self/mountinfo').read_text().splitlines()
    mounts = []
    for line in lines:
        fields = line.split()
        mount = re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1],8)), fields[4])
        if '\\' in mount:
            raise RuntimeError('unrecognized mount path escape')
        mounts.append((mount, fields[5].split(',')))
    proofs = {}
    for path in (str(CACHE), *(str(p) for p in PROTECTED), str(CITY), str(BUILD)):
        candidates = [(m,opts) for m,opts in mounts if m == '/' or path == m or path.startswith(m+'/')]
        mount, options = max(candidates, key=lambda pair:len(pair[0]))
        if 'ro' not in options:
            raise RuntimeError('effective writable mount: '+path)
        descendants = [(m,opts) for m,opts in mounts if m.startswith(path+'/')]
        if any('ro' not in opts for m,opts in descendants):
            raise RuntimeError('writable descendant mount: '+path)
        proofs[path] = dict(mount=mount, options=options, descendants=descendants)
    read(BUILD/'compose', BINARY_SHA)
    # Parent owns the finite process-group bound; this child does not detach.
    result = subprocess.run([str(BUILD/'compose')], env=ENV, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError('composition refused: '+result.stderr)
    print(json.dumps(dict(mounts=proofs, observation=json.loads(result.stdout),
                         host_verification='outside-namespace', worker_launched=False)))

def successful(record):
    c = record['cleanup']
    return (record['exit_code'] == 0 and not record['timed_out'] and record['primary_error'] is None
            and c['direct_child_reaped'] and c['owned_process_group_gone'] is True
            and not c['failures'] and not c['unexpected_survivors'])

def main():
    if not globals().get('_SOURCE_SHA') or read(Path(__file__), _SOURCE_SHA) is None:
        raise RuntimeError('source-bound launcher required')
    read(HERE/'source-launch.py', LAUNCHER_SHA)
    if len(sys.argv) == 2 and sys.argv[1] == 'inner':
        inner(); return
    if len(sys.argv) == 3 and sys.argv[1] == 'snapshot' and sys.argv[2] in ('before.json','after.json'):
        snapshot(sys.argv[2]); return
    if len(sys.argv) != 1:
        raise RuntimeError('unknown invocation')
    runner = module(BUILD/'phase_runner.py', 'eddf5e1174a7b275abe280e91ea5c8ea0762600d38524ba9631f53fb4874cdf3')
    read(BUILD/'compose', BINARY_SHA)
    build = json.loads(read(BUILD/'build-result.json'))
    if build['builder_sha256'] != '4d8a1586993e44b82c134075dd8f6cf79ea5d178555471e6086bdc3f9474223b' or build['binary_sha256'] != BINARY_SHA:
        raise RuntimeError('reviewed build binding mismatch')
    draft = json.loads(recorded_draft()['raw'])
    ROOT.mkdir(mode=0o700)
    def phase(name, argv, timeout):
        return runner._run_owned_phase(name=name, argv=argv, cwd=ROOT,
            environment=ENV, timeout=timeout, evidence_path=ROOT/(name+'-phase.json'))
    def invocation(*args):
        read(HERE/'source-launch.py', LAUNCHER_SHA)
        return ['/usr/bin/python3','-I','-S','-B',str(HERE/'source-launch.py'),
                __file__, _SOURCE_SHA, *args]
    before = phase('before', invocation('snapshot','before.json'), 120)
    if not successful(before):
        raise RuntimeError('preflight snapshot refused; no namespace launched')
    error = None
    try:
        result = phase('compose', ['/usr/bin/bwrap','--ro-bind','/','/',
            '--unshare-net','--unshare-pid','--new-session','--die-with-parent','--proc','/proc','--dev','/dev',
            '--', *invocation('inner')], 60)
        if not successful(result):
            raise RuntimeError('composition phase refused')
        observation = json.loads(result['stdout'])
        actual = observation['observation']
        expected = draft['profiles'][0]
        if (actual['profile'] != expected['name'] or actual['argv'] != expected['argv']
            or actual['environment'] != expected['environment']
            or actual['permission_revision'] != draft['permission_revision']
            or actual['task_observed'] or actual['worker_launched']):
            raise RuntimeError('actual composition differs from draft')
        write('composition.json', observation)
    except BaseException as failure:
        error = failure
    after = phase('after', invocation('snapshot','after.json'), 120)
    if not successful(after):
        raise RuntimeError('postflight snapshot refused; stop and preserve') from error
    unchanged = read(ROOT/'before.json') == read(ROOT/'after.json')
    write('result.json', dict(ok=error is None and unchanged, unchanged=unchanged,
        error=None if error is None else str(error), receipt_installed=False,
        worker_launched=False, authentication_proven=False, task_claim_proven=False))
    if error or not unchanged:
        raise RuntimeError('composition or preservation failed; do not retry') from error
    print(json.dumps(dict(ok=True, evidence=str(ROOT), receipt_installed=False)))

if __name__ == '__main__':
    main()
