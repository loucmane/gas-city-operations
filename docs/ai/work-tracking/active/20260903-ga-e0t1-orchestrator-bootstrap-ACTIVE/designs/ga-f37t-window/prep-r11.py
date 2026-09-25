"""ga-f37t window prep: the isolation overlay and its receipt image. Read-only; installs nothing.

Merged rebind of two reviewed ga-y49e scripts, keeping their logic:
- prepare-isolation.py (isolation-candidate-r2);
- prepare-receipt.py (receipt-candidate-r1).

What changes from the originals:
- The baseline is the M5 city 4f7e170f with revision d6ca85cd, and the provisioning receipt 0b30c23f
  adopted by P6.
- The task and worktree are ga-f37t.
- The effective-config and order baselines are observed live at the start of this run, instead of
  being read from an older observation root.
- The prior receipt input is P6's reviewed input draft.
- Outputs go to one fresh root, ROOT, created exclusively outside every repository.
- All gc and compose calls use a fixed minimal ENV (with GIT_OPTIONAL_LOCKS=0) instead of the
  caller's environment. The running revision is still pinned (d6ca85cd).
- The old verified.json gate between the two original scripts becomes the in-run overlay revision.
  That value is used only after every isolation proof has passed.

r2 (after job ga-4z38-prep refused fail-closed at 16:06:01Z; root -r1 preserved):
- `gc config show` reports one more advisory validation warning under the overlay: the bound
  worker's max_active_sessions=1 makes it a canonical singleton. The expected effective config now
  includes exactly that pinned warning string, in sorted position. Every Agents, Workspace and
  Orders field was already exact.
- The overlay bytes are pinned in-job (OVERLAY_SHA), not only in the test.
- The normalize child is re-launched through the digest-checked source launcher.
- The root is -r2.

r3 (after review HOLD of r2 f0234f73, which never ran; root -r2 was never created):
- The launcher self-check runs first in main(), before the root is created.
- The expected effective config is a function, expected_config(), replayed by a test against the r1
  evidence.
- The two receipt phases are a function, receipt_image(). The normalize child takes its input
  directory as an argument (the job passes ROOT), so proof/prep-proof.py runs the exact child path
  offline on a scratch directory.

What it does, all in read-only, network-isolated bwrap namespaces:
1. It generates the one-worker overlay:
   - workspace cap 1;
   - every order skipped;
   - every city and gascity agent suspended, except gascity/implementation-worker, which is bound
     to the ga-f37t worktree with sessions 0..1.
2. It proves the exact effective-config delta with `gc config show`, and that effectively no orders
   remain.
3. It takes the overlay's permission revision from the reviewed Core compose diagnostic. The
   provider composition must stay unchanged apart from that revision.
4. It normalizes (Template load_prototype) and finalizes (Core preflight diagnostic `finalize`)
   the P6 input draft with that revision.
5. It requires the final receipt to differ from the live receipt ONLY in permission_revision and
   receipt_sha256.
6. It proves the live city.toml, the receipt and the effective config are unchanged at the end.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tomllib
import types

ROOT = Path('/var/tmp/ga-f37t-prep-20260923-r2')
CITY = Path('/home/loucmane/gascity/city')
RECEIPT = CITY/'.gc/runtime/provisioning/receipt.json'
WORK = '/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles'
GC = Path('/home/loucmane/gascity/bin/gc')
GC_SHA = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'
COMPOSE = Path('/var/tmp/ga-ecwh-compose-diagnostic-20260920-r2/compose')
COMPOSE_SHA = '9f837c831919cd440089ac2207c6e32ca005709b51a72e430a48f76006f2edd3'
BUILD = Path('/var/tmp/ga-ecwh-preflight-diagnostic-20260920-r1')
FINALIZE_SHA = 'edbc0fa11d3ebae15f678179725203d9da3434ec0cf8883c536398d5f97426bf'
RUNNER_PHASE_SHA = 'eddf5e1174a7b275abe280e91ea5c8ea0762600d38524ba9631f53fb4874cdf3'
PROVISIONER = Path('/home/loucmane/gas-city-template/bin/gct-managed-worker-provision')
PROVISIONER_SHA = '64425a728fc06a082865f2d53afcc6e4793974f5aadab49492d95f5e0a9f4a35'
CANARY = CITY/'.gc/runtime/provisioning/bin/gct-managed-worker-canary'
CANARY_SHA = '3beeedb2e5ce0723e5f745a05f1e2fdfa3ec27bee468284860e587e63c63e2e2'
PRIOR = Path('/var/tmp/gct-m1wh-p6-input-20260923-r2/receipt.input.draft.json')
PRIOR_SHA = '24c1ca751303d5cab12a1605599d13cb5e5a152c977088fbb6869c7a052095ec'
CITY_SHA = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
RECEIPT_SHA = '0b30c23f4484382fd4918f394599268f4f4005ac71118e8a7f82ca72eb9615ff'
REVISION = 'd6ca85cd96c7aab4ea0b6a7954d2d74e5e6bb211cde0bb820f3b6f815023bd88'
ORDER_COUNT = 34
HEADER = '\n# ga-f37t bounded one-worker window; restore exact preserved baseline.\n'
OVERLAY_SHA = '9774a5692ec5537713b212bc3fef5c88edc34c82cb6fdcc11e949e7eefc8343e'
LAUNCH = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
              '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-p6/source-launch.py')
LAUNCH_SHA = '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'
# Advisory validation warning gc adds when the overlay caps the bound worker at one session.
SINGLETON_WARNING = ('agent "gascity/gc.implementation-worker": max_active_sessions=1 creates a canonical '
                     'singleton that drains when scale_check returns 0; declare [[named_session]] only if '
                     'you need a session that survives empty-demand windows')
ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane', LANG='C.UTF-8',
           GC_HOME='/home/loucmane/gascity/home', GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1',
           PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path, digest=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode) and s.st_uid == 1000 and s.st_nlink == 1, str(path)
        with os.fdopen(os.dup(fd), 'rb') as handle:
            data = handle.read()
        assert os.fstat(fd) == s and Path(path).lstat() == s, 'read drift: %s' % path
    finally:
        os.close(fd)
    assert digest is None or sha(data) == digest, 'digest: %s' % path
    return data


def module(path, digest, name):
    raw = read(path, digest)
    m = types.ModuleType(name)
    m.__file__ = str(path)
    sys.modules[name] = m
    exec(compile(raw, str(path), 'exec', dont_inherit=True), m.__dict__)
    return m


def write(name, data, root=None):
    if not isinstance(data, bytes):
        data = (json.dumps(data, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open((ROOT if root is None else root)/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def run(argv):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
    if p.returncode:
        raise RuntimeError('rc=%s: %s' % (p.returncode, p.stderr[-2000:]))
    return json.loads(p.stdout)


def confined(command, isolated=False):
    argv = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--new-session',
            '--die-with-parent', '--proc', '/proc', '--dev', '/dev']
    if isolated:
        argv += ['--ro-bind', str(ROOT/'city.isolated.toml'), str(CITY/'city.toml')]
    return run([*argv, '--', *command])


def config(isolated=False):
    return confined([str(GC), '--city', str(CITY), 'config', 'show', '--json'], isolated)


def normalize_main(root):
    p = module(PROVISIONER, PROVISIONER_SHA, 'pinned_provisioner')
    read(CANARY, CANARY_SHA)
    r = p.load_prototype(root/'receipt.input.json', dict(path=str(CANARY), sha256=CANARY_SHA))
    sys.stdout.buffer.write(p.canonical_json(r))


def expected_config(baseline, selected, target, names):
    """The exact effective config `gc config show` must report under the overlay."""
    expected = copy.deepcopy(baseline)
    for i in selected:
        expected['config']['Agents'][i]['Suspended'] = i != target
        if i == target:
            expected['config']['Agents'][i].update(WorkDir=WORK, MinActiveSessions=0, MaxActiveSessions=1)
    expected['config']['Workspace']['MaxActiveSessions'] = 1
    expected['config']['Orders']['Skip'] = names
    assert SINGLETON_WARNING not in baseline['validation']['warnings']
    expected['validation']['warnings'] = sorted(baseline['validation']['warnings'] + [SINGLETON_WARNING])
    return expected


def receipt_image(owned, source_path, source_sha, root):
    """Normalize and finalize root/receipt.input.json in owned, confined children; return the final bytes.

    The normalize child is this file, run again through the digest-checked source launcher.
    """
    normalize = ['/usr/bin/python3', '-I', '-S', '-B', str(LAUNCH), str(source_path), source_sha, 'normalize', str(root)]
    for name, command in [('normalize', normalize),
                          ('finalize', [str(BUILD/'compose'), 'finalize', str(root/'receipt.normalized.json')])]:
        argv = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--unshare-pid', '--die-with-parent',
                '--new-session', '--proc', '/proc', '--dev', '/dev', '--', *command]
        result = owned._run_owned_phase(name=name, argv=argv, cwd=root, environment=ENV, timeout=45,
                                        evidence_path=root/(name + '-phase.json'))
        c = result['cleanup']
        assert result['exit_code'] == 0 and not result['timed_out'] and not result['primary_error'], name
        assert c['direct_child_reaped'] and c['owned_process_group_gone'] and not c['failures'] \
            and not c['unexpected_survivors'], name
        wire = result['stdout'].encode()
        json.loads(wire)
        write('receipt.normalized.json' if name == 'normalize' else 'receipt.final.json', wire, root)
    return read(root/'receipt.final.json')


def build_overlay(city, baseline, orders):
    """The reviewed ga-y49e overlay generation, unchanged except for WORK and HEADER."""
    cfg = baseline['config']
    assert 'orders' not in tomllib.loads(city.decode())
    assert city.count(b'max_active_sessions = 16\n') == 1
    agents = cfg['Agents']
    identities = [(a['Dir'], a['Name']) for a in agents]
    assert len(identities) == len(set(identities)), 'ambiguous display agent identity'
    target = identities.index(('gascity', 'implementation-worker'))
    assert agents[target]['Provider'] == 'claude-signing'
    selected = [i for i, a in enumerate(agents) if a['Dir'] in ('', 'gascity')]
    names = sorted(set(o['name'] for o in orders['orders']))
    assert names and len(names) == ORDER_COUNT, 'order inventory size %d' % len(names)
    patches = []
    for i in selected:
        a = agents[i]
        patch = dict(dir=a['Dir'], name=a['Name'], suspended=i != target)
        if i == target:
            patch.update(work_dir=WORK, min_active_sessions=0, max_active_sessions=1)
        patches.append(patch)
    parts = [HEADER, '[orders]\n', 'skip = ' + json.dumps(names) + '\n']
    for patch in patches:
        parts.append('\n[[patches.agent]]\n')
        for key, value in patch.items():
            parts.append(key + ' = ' + json.dumps(value) + '\n')
    candidate = city.replace(b'max_active_sessions = 16\n', b'max_active_sessions = 1\n', 1) + ''.join(parts).encode()
    tomllib.loads(candidate.decode())
    return candidate, patches, names, target, selected


def main():
    assert os.getuid() == os.geteuid() == 1000
    # First, before the root exists: this run and its normalize child must come from the launcher.
    read(LAUNCH, LAUNCH_SHA)
    source_sha = globals().get('_SOURCE_SHA')
    assert source_sha and sha(read(Path(sys.argv[0]))) == source_sha, 'prep must run under the source launcher'
    read(GC, GC_SHA)
    read(COMPOSE, COMPOSE_SHA)
    city = read(CITY/'city.toml', CITY_SHA)
    before_receipt = read(RECEIPT, RECEIPT_SHA)
    prior = read(PRIOR, PRIOR_SHA)
    ROOT.mkdir(mode=0o700)
    # Live baselines, observed now through the same confined gc.
    baseline = config()
    orders = confined([str(GC), '--city', str(CITY), 'order', 'list', '--json'])
    write('config.baseline.json', baseline)
    write('orders.baseline.json', orders)
    candidate, patches, names, target, selected = build_overlay(city, baseline, orders)
    assert sha(candidate) == OVERLAY_SHA, 'overlay bytes differ from the derived 9774a569'
    write('city.baseline.toml', city)
    write('city.isolated.toml', candidate)
    write('declared-delta.json', dict(patches=patches, order_skip=names, workspace_cap=1))
    before = confined([str(COMPOSE)])
    after = confined([str(COMPOSE)], True)
    write('composition.before.json', before)
    write('composition.after.json', after)
    for key in set(before) | set(after):
        if key != 'permission_revision':
            assert before.get(key) == after.get(key), 'provider composition changed: ' + key
    assert before['permission_revision'] == REVISION, 'running composition revision drift'
    assert after['permission_revision'] != before['permission_revision']
    observed = config(True)
    write('config.isolated.json', observed)
    assert observed == expected_config(baseline, selected, target, names), 'unexpected effective configuration delta'
    empty = confined([str(GC), '--city', str(CITY), 'order', 'list', '--json'], True)
    write('orders.isolated.json', empty)
    assert empty['orders'] == [] and empty['summary']['count'] == 0
    # Receipt image for the overlay revision: the prior input with only the revision replaced.
    candidate_input = json.loads(prior)
    candidate_input['permission_revision'] = after['permission_revision']
    owned = module(BUILD/'phase_runner.py', RUNNER_PHASE_SHA, 'owned_phase')
    read(BUILD/'compose', FINALIZE_SHA)
    write('receipt.before.json', before_receipt)
    write('receipt.input.json', candidate_input)
    old = json.loads(before_receipt)
    new = json.loads(receipt_image(owned, Path(sys.argv[0]), source_sha, ROOT))
    differences = sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))
    assert differences == ['permission_revision', 'receipt_sha256'], differences
    assert new['permission_revision'] == after['permission_revision']
    # Nothing live changed.
    assert read(CITY/'city.toml') == city and read(RECEIPT) == before_receipt and config() == baseline, \
        'production input changed'
    result = dict(ok=True, installed=False, worker_launched=False,
                  city_before_sha256=sha(city), city_after_sha256=sha(candidate),
                  revision_before=before['permission_revision'], revision_after=after['permission_revision'],
                  receipt_before_sha256=sha(before_receipt), receipt_after_sha256=sha(read(ROOT/'receipt.final.json')),
                  receipt_self_sha256=new['receipt_sha256'], changed_receipt_fields=differences,
                  effective_orders=0, only_unsuspended_city_core_agent='gascity/gc.implementation-worker',
                  workspace_capacity=1, prior_input_sha256=sha(prior))
    write('result.json', result)
    print(json.dumps(result, indent=1, sort_keys=True))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'normalize':
        normalize_main(Path(sys.argv[2]))
    else:
        assert len(sys.argv) == 1
        main()
